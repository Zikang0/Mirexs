"""
智能模型路由（Smart Model Router）

该模块是多模型路由的“核心入口”，负责将：
- 任务画像（TaskProfile）
- 硬件画像（HardwareProfile）
- 模型画像（ModelProfile）

综合为可执行的路由决策（RoutingDecision）。

设计原则（与 docs/architecture/overview.md 对齐）：
1) **契约优先**：对外暴露稳定的数据结构与错误模型
2) **可降级**：在硬件信息缺失/配置不完整/候选为空时提供可解释的回退
3) **本地优先**：restricted 场景禁止云端模型
4) **可观测**：输出 decision_reasons 便于审计与调参
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .hardware_profile import HardwareProfile, HardwareProfiler
from .model_manager import ModelManager
from .model_registry import ModelProfile, ModelRegistry


class ModelSelectionError(Exception):
    """路由选择失败（无候选/硬约束冲突等）。"""


class TaskType(str, Enum):
    CASUAL_CHAT = "casual_chat"
    EMOTIONAL = "emotional"
    ANALYTICAL = "analytical"
    CODING = "coding"
    CREATIVE = "creative"
    MULTI_STEP = "multi_step"
    VISION = "vision"
    REALTIME = "realtime"


class SecurityLevel(str, Enum):
    NORMAL = "normal"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class TaskProfile:
    """任务画像（稳定 Schema）。"""

    task_id: str
    task_type: TaskType

    complexity: float = 0.5  # 0~1
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 512
    modalities: List[str] = field(default_factory=lambda: ["text"])
    requires_realtime: bool = False
    security_level: SecurityLevel = SecurityLevel.NORMAL

    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "TaskProfile":
        """返回归一化后的任务画像（复杂度 clamp；模态小写等）。"""
        c = float(self.complexity)
        if c < 0.0:
            c = 0.0
        if c > 1.0:
            c = 1.0
        mods = [str(m).lower() for m in (self.modalities or ["text"])]
        if not mods:
            mods = ["text"]
        return TaskProfile(
            task_id=str(self.task_id),
            task_type=TaskType(str(self.task_type.value if isinstance(self.task_type, TaskType) else self.task_type)),
            complexity=c,
            estimated_input_tokens=max(0, int(self.estimated_input_tokens or 0)),
            estimated_output_tokens=max(0, int(self.estimated_output_tokens or 0)),
            modalities=mods,
            requires_realtime=bool(self.requires_realtime),
            security_level=SecurityLevel(
                str(self.security_level.value if isinstance(self.security_level, SecurityLevel) else self.security_level)
            ),
            metadata=dict(self.metadata or {}),
        )

    @property
    def estimated_total_tokens(self) -> int:
        return max(0, int(self.estimated_input_tokens or 0)) + max(0, int(self.estimated_output_tokens or 0))


@dataclass
class RoutingDecision:
    """路由决策：主模型 + 可选副模型 + 回退模型。"""

    primary: ModelProfile
    fallback: ModelProfile
    secondary: Optional[ModelProfile] = None

    estimated_latency_ms: float = 0.0
    estimated_vram_peak_gb: float = 0.0
    decision_reasons: List[str] = field(default_factory=list)

    policy_version: str = "v2.0.1"
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass(frozen=True)
class RoutingPolicy:
    """
    路由评分策略（可配置）。

    评分以“越大越好”为统一口径，避免单位混用引入逻辑错误。
    """

    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "capability": 0.40,
            "hardware_fit": 0.25,
            "latency": 0.15,
            "context_fit": 0.10,
            "reliability": 0.10,
        }
    )
    vram_overcommit_ratio: float = 1.15

    # 不同任务类型的 P95 预算（ms），用于 latency 归一化
    latency_budget_ms: Dict[TaskType, int] = field(
        default_factory=lambda: {
            TaskType.CASUAL_CHAT: 800,
            TaskType.EMOTIONAL: 900,
            TaskType.REALTIME: 600,
            TaskType.CODING: 2500,
            TaskType.ANALYTICAL: 4500,
            TaskType.CREATIVE: 2000,
            TaskType.MULTI_STEP: 3500,
            TaskType.VISION: 5000,
        }
    )

    def score(self, model: ModelProfile, task: TaskProfile, hw: HardwareProfile) -> Tuple[float, Dict[str, float]]:
        """
        返回（总分, 分项明细）。

        分项全部归一化到 0~1。
        """
        capability = self._capability_score(model, task)
        hardware_fit = self._hardware_fit_score(model, hw)
        latency = self._latency_score(model, task)
        context_fit = self._context_fit_score(model, task)
        reliability = self._reliability_score(model)

        w = self.weights
        total = (
            w.get("capability", 0.0) * capability
            + w.get("hardware_fit", 0.0) * hardware_fit
            + w.get("latency", 0.0) * latency
            + w.get("context_fit", 0.0) * context_fit
            + w.get("reliability", 0.0) * reliability
        )
        breakdown = {
            "capability": capability,
            "hardware_fit": hardware_fit,
            "latency": latency,
            "context_fit": context_fit,
            "reliability": reliability,
            "total": total,
        }
        return float(total), breakdown

    def estimate_latency_ms(self, model: ModelProfile, task: TaskProfile) -> float:
        """粗略估算推理延迟（ms），用于决策输出与归一化。"""
        tps = self._choose_tps(model, task)
        if tps <= 0:
            tps = 5.0
        # 输出 token 占主导；输入 token 主要影响 prefill，这里用 0.2 的系数粗估
        est_tokens = float(max(0, task.estimated_output_tokens)) + float(max(0, task.estimated_input_tokens)) * 0.2
        return (est_tokens / float(tps)) * 1000.0

    def _choose_tps(self, model: ModelProfile, task: TaskProfile) -> float:
        if task.task_type in {TaskType.CASUAL_CHAT, TaskType.EMOTIONAL, TaskType.REALTIME}:
            return float(model.tps_chat or model.tps_reason or 0.0)
        return float(model.tps_reason or model.tps_chat or 0.0)

    def _capability_score(self, model: ModelProfile, task: TaskProfile) -> float:
        tags = {t.lower() for t in (model.capability_tags or [])}
        mods = {m.lower() for m in (model.modalities or ["text"])}
        tags = tags.union(mods)

        preferred = self._preferred_tags(task.task_type)
        if not preferred:
            return 0.5

        hit = sum(1 for t in preferred if t in tags)
        base = hit / float(len(preferred))

        # 复杂度越高，对“reasoning/code”等标签更敏感
        if task.complexity >= 0.75:
            if "reasoning" in tags:
                base += 0.10
            if "code" in tags or "coding" in tags or "coder" in tags:
                base += 0.10

        if base > 1.0:
            base = 1.0
        if base < 0.0:
            base = 0.0
        return float(base)

    def _preferred_tags(self, task_type: TaskType) -> List[str]:
        mapping: Dict[TaskType, List[str]] = {
            TaskType.CASUAL_CHAT: ["chat", "instruct", "general"],
            TaskType.EMOTIONAL: ["emotional", "empathetic", "chat"],
            TaskType.ANALYTICAL: ["reasoning", "analysis", "math"],
            TaskType.CODING: ["code", "coding", "coder"],
            TaskType.CREATIVE: ["creative", "writing"],
            TaskType.MULTI_STEP: ["reasoning", "planner", "tool"],
            TaskType.VISION: ["vision"],
            TaskType.REALTIME: ["fast", "realtime", "chat"],
        }
        return mapping.get(task_type, [])

    def _hardware_fit_score(self, model: ModelProfile, hw: HardwareProfile) -> float:
        vram_free = float(hw.vram_free_gb or 0.0)
        vram_est = float(model.vram_est_gb or 0.0) * float(self.vram_overcommit_ratio)

        if vram_free <= 0.0 or vram_est <= 0.0:
            # 无法评估：返回中性值，让其他维度决定优先级
            return 0.5

        safety = (vram_free - vram_est) / max(vram_free, 1e-9)
        if safety < 0.0:
            safety = 0.0
        if safety > 1.0:
            safety = 1.0
        return float(safety)

    def _latency_score(self, model: ModelProfile, task: TaskProfile) -> float:
        est = self.estimate_latency_ms(model, task)
        budget = float(self.latency_budget_ms.get(task.task_type, 4500))
        if budget <= 0:
            budget = 4500.0
        ratio = est / budget
        if ratio < 0.0:
            ratio = 0.0
        if ratio > 1.0:
            ratio = 1.0
        # 越小越好 -> 归一化为越大越好
        return float(1.0 - ratio)

    def _context_fit_score(self, model: ModelProfile, task: TaskProfile) -> float:
        ctx = int(model.ctx_len or 0)
        need = int(task.estimated_total_tokens or 0)
        if ctx <= 0 or need <= 0:
            return 0.5
        if need > ctx:
            return 0.0
        ratio = need / float(ctx)
        if ratio < 0.0:
            ratio = 0.0
        if ratio > 1.0:
            ratio = 1.0
        return float(1.0 - ratio)

    def _reliability_score(self, model: ModelProfile) -> float:
        tags = {t.lower() for t in (model.capability_tags or [])}
        if "experimental" in tags:
            return 0.4
        if "stable" in tags or "tested" in tags or "prod" in tags:
            return 1.0
        return 0.7


class SmartModelRouter:
    """智能路由器（核心入口）。"""

    def __init__(
        self,
        *,
        registry: Optional[ModelRegistry] = None,
        hardware_profiler: Optional[HardwareProfiler] = None,
        policy: Optional[RoutingPolicy] = None,
        model_manager: Optional[ModelManager] = None,
        eager_load: bool = False,
    ):
        self.registry = registry or ModelRegistry()
        self.hardware_profiler = hardware_profiler or HardwareProfiler()
        self.policy = policy or RoutingPolicy()
        self.model_manager = model_manager or ModelManager(self.registry)
        # 默认不强制加载/下载权重：仓库通常不包含权重文件，避免“仅路由就失败”
        self.eager_load = bool(eager_load)

    async def route(self, task: TaskProfile) -> RoutingDecision:
        """
        生成路由决策（异步）。

        关键保证：
        - 不因硬件信息缺失而崩溃（会进入降级逻辑）
        - restricted 场景不选择 cloud 模型
        """
        task = task.normalized()
        hw = await self.hardware_profiler.get_snapshot()

        candidates = self.registry.get_candidates(
            task,
            hw,
            vram_overcommit_ratio=float(self.policy.vram_overcommit_ratio),
        )

        reasons: List[str] = []
        reasons.append(
            f"hardware: gpu={hw.gpu_name}, vram_free={hw.vram_free_gb:.2f}GB, ram_free={hw.ram_free_gb:.2f}GB, os={hw.os}"
        )
        reasons.append(
            f"task: type={task.task_type.value}, complexity={task.complexity:.2f}, modalities={task.modalities}, security={task.security_level.value}"
        )

        if not candidates:
            # 降级：从所有 enabled 模型里选一个最省 VRAM 的，保证系统可继续运行
            all_models = self.registry.list_models(enabled_only=True)
            if not all_models:
                raise ModelSelectionError("模型注册表为空：请配置 infrastructure/model_hub/model_configs.yaml")

            # 仍然尊重 restricted 与模态约束
            filtered = []
            for m in all_models:
                if task.security_level == SecurityLevel.RESTRICTED and m.is_cloud:
                    continue
                if not m.supports_modalities(task.modalities):
                    continue
                filtered.append(m)

            if not filtered:
                raise ModelSelectionError("无可用模型：安全/模态约束导致候选为空")

            filtered.sort(key=lambda m: float(m.vram_est_gb or 0.0))
            primary = filtered[0]
            fallback = primary
            reasons.append("candidate: empty -> fallback to minimal-vram enabled model")
            decision = RoutingDecision(
                primary=primary,
                secondary=None,
                fallback=fallback,
                estimated_latency_ms=self.policy.estimate_latency_ms(primary, task),
                estimated_vram_peak_gb=float(primary.vram_est_gb) * float(self.policy.vram_overcommit_ratio),
                decision_reasons=reasons,
                policy_version="v2.0.1",
            )
            await self._ensure_loaded(decision)
            return decision

        scored: List[Tuple[float, ModelProfile, Dict[str, float]]] = []
        for m in candidates:
            s, breakdown = self.policy.score(m, task, hw)
            scored.append((s, m, breakdown))

        scored.sort(key=lambda x: x[0], reverse=True)
        primary = scored[0][1]

        # fallback：更偏“稳/省资源”
        fallback = min(candidates, key=lambda m: float(m.vram_est_gb or 0.0))
        if task.security_level == SecurityLevel.RESTRICTED and fallback.is_cloud:
            # 理论上 registry 已过滤，这里双保险
            fallback = primary

        # secondary：高复杂任务下，尝试选择一个“互补模型”
        secondary = self._choose_secondary(primary, scored, task)

        top_breakdown = scored[0][2]
        reasons.append(
            "score(primary): "
            + ", ".join([f"{k}={v:.2f}" for k, v in top_breakdown.items() if k != "total"])
            + f", total={top_breakdown.get('total', 0.0):.3f}"
        )
        reasons.append(f"selected: primary={primary.model_id}, secondary={(secondary.model_id if secondary else None)}, fallback={fallback.model_id}")
        reasons.append(f"candidate_count={len(candidates)}")

        est_latency = self.policy.estimate_latency_ms(primary, task)
        est_vram = float(primary.vram_est_gb or 0.0) * float(self.policy.vram_overcommit_ratio)
        if secondary is not None:
            est_vram += float(secondary.vram_est_gb or 0.0) * float(self.policy.vram_overcommit_ratio)

        decision = RoutingDecision(
            primary=primary,
            secondary=secondary,
            fallback=fallback,
            estimated_latency_ms=float(est_latency),
            estimated_vram_peak_gb=float(est_vram),
            decision_reasons=reasons,
            policy_version="v2.0.1",
        )
        await self._ensure_loaded(decision)
        return decision

    def _choose_secondary(
        self,
        primary: ModelProfile,
        scored: List[Tuple[float, ModelProfile, Dict[str, float]]],
        task: TaskProfile,
    ) -> Optional[ModelProfile]:
        if task.complexity < 0.85:
            return None
        if len(scored) < 2:
            return None

        primary_tags = {t.lower() for t in (primary.capability_tags or [])}

        # 示例策略：coding/analytical 优先选择 reasoning 互补；chat/emotional 不强制 secondary
        preferred_tag = None
        if task.task_type in {TaskType.CODING, TaskType.ANALYTICAL, TaskType.MULTI_STEP}:
            preferred_tag = "reasoning"

        for _, m, _ in scored[1:]:
            if m.model_id == primary.model_id:
                continue
            tags = {t.lower() for t in (m.capability_tags or [])}
            if preferred_tag and preferred_tag in tags and preferred_tag not in primary_tags:
                return m

        # 否则选择分数第二且不是 primary 的模型
        for _, m, _ in scored[1:]:
            if m.model_id != primary.model_id:
                return m
        return None

    async def _ensure_loaded(self, decision: RoutingDecision) -> None:
        """
        将“加载/下载”作为路由的副作用（可关闭/替换）。

        MVP：仅确保 primary/fallback 被标记为 loaded，便于上层执行。
        """
        if not self.eager_load:
            return

        try:
            await self.model_manager.ensure_loaded(decision.primary)
            if decision.secondary is not None:
                await self.model_manager.ensure_loaded(decision.secondary)
            if decision.fallback.model_id != decision.primary.model_id:
                await self.model_manager.ensure_loaded(decision.fallback)
        except Exception as e:
            # 路由本身不应因“权重缺失/下载失败”而不可用；将失败记录到 reasons 供审计
            try:
                decision.decision_reasons.append(f"ensure_loaded: skipped due to error: {e}")
            except Exception:
                pass
