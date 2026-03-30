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
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
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


def _repo_root() -> Path:
    # infrastructure/model_hub -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RouterRuntimeConfig:
    """
    路由器运行时配置（从 `config/system/model_configs/router_config.yaml` 解析）。

    设计原则：
    - **尽量不报错**：配置缺失/解析失败时回退到默认值，避免“仅因路由策略文件损坏而系统不可用”。
    - **安全优先**：restricted 场景始终禁用 cloud 模型（即使配置中误写为允许，也不会放开）。
    """

    config_path: Optional[Path] = None

    enabled: bool = True
    eager_load: bool = False
    allow_cloud_models: bool = False
    policy_version: str = "v2.0.1"

    policy: RoutingPolicy = field(default_factory=RoutingPolicy)

    allow_empty_candidates_fallback: bool = True
    fallback_strategy: str = "local_first"  # local_first | cloud_first | static
    static_model_key: str = ""


def _resolve_config_path(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (_repo_root() / p)


def _load_yaml_dict(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _load_router_runtime_config(config_path: Optional[os.PathLike] = None) -> RouterRuntimeConfig:
    """
    加载路由器配置文件并转换为 RouterRuntimeConfig。

    解析入口优先级：
    1) 显式参数 `config_path`
    2) 环境变量 `MIREXS_ROUTER_CONFIG`
    3) 默认路径 `config/system/model_configs/router_config.yaml`
    """

    path: Optional[Path]
    if config_path is not None:
        path = _resolve_config_path(str(config_path))
    else:
        env = str(os.environ.get("MIREXS_ROUTER_CONFIG", "") or "").strip()
        if env:
            path = _resolve_config_path(env)
        else:
            path = _repo_root() / "config" / "system" / "model_configs" / "router_config.yaml"

    if not path.exists():
        return RouterRuntimeConfig(config_path=path)

    raw = _load_yaml_dict(path)
    router_raw = raw.get("router") or {}
    if not isinstance(router_raw, dict):
        return RouterRuntimeConfig(config_path=path)

    default_policy = RoutingPolicy()

    # policy
    policy_raw = router_raw.get("policy") or {}
    if not isinstance(policy_raw, dict):
        policy_raw = {}

    weights = dict(default_policy.weights)
    weights_raw = policy_raw.get("weights") or {}
    if isinstance(weights_raw, dict):
        for k, v in weights_raw.items():
            try:
                weights[str(k)] = float(v)
            except Exception:
                continue

    # 负权重没有意义，统一 clamp
    for k, v in list(weights.items()):
        try:
            fv = float(v)
        except Exception:
            fv = 0.0
        if fv < 0.0:
            fv = 0.0
        weights[k] = fv

    vram_overcommit_ratio = default_policy.vram_overcommit_ratio
    try:
        vram_overcommit_ratio = float(policy_raw.get("vram_overcommit_ratio", vram_overcommit_ratio))
    except Exception:
        vram_overcommit_ratio = default_policy.vram_overcommit_ratio
    if vram_overcommit_ratio <= 0:
        vram_overcommit_ratio = default_policy.vram_overcommit_ratio

    latency_budget_ms = dict(default_policy.latency_budget_ms)
    latency_raw = policy_raw.get("latency_budget_ms") or {}
    if isinstance(latency_raw, dict):
        for k, v in latency_raw.items():
            try:
                task_type = TaskType(str(k))
                budget = int(v)
            except Exception:
                continue
            if budget > 0:
                latency_budget_ms[task_type] = budget

    policy = RoutingPolicy(
        weights=weights,
        vram_overcommit_ratio=vram_overcommit_ratio,
        latency_budget_ms=latency_budget_ms,
    )

    enabled = bool(router_raw.get("enabled", True))
    eager_load = bool(router_raw.get("eager_load", False))
    allow_cloud_models = bool(router_raw.get("allow_cloud_models", False))

    policy_version = str(router_raw.get("policy_version") or "").strip() or "v2.0.1"

    constraints_raw = router_raw.get("constraints") or {}
    if not isinstance(constraints_raw, dict):
        constraints_raw = {}
    allow_empty_candidates_fallback = bool(constraints_raw.get("allow_empty_candidates_fallback", True))

    fallback_raw = router_raw.get("fallback") or {}
    if not isinstance(fallback_raw, dict):
        fallback_raw = {}
    fallback_strategy = str(fallback_raw.get("strategy") or "local_first").strip() or "local_first"
    static_model_key = str(fallback_raw.get("static_model_key") or "").strip()

    return RouterRuntimeConfig(
        config_path=path,
        enabled=enabled,
        eager_load=eager_load,
        allow_cloud_models=allow_cloud_models,
        policy_version=policy_version,
        policy=policy,
        allow_empty_candidates_fallback=allow_empty_candidates_fallback,
        fallback_strategy=fallback_strategy,
        static_model_key=static_model_key,
    )


class SmartModelRouter:
    """智能路由器（核心入口）。"""

    def __init__(
        self,
        *,
        registry: Optional[ModelRegistry] = None,
        hardware_profiler: Optional[HardwareProfiler] = None,
        policy: Optional[RoutingPolicy] = None,
        model_manager: Optional[ModelManager] = None,
        eager_load: Optional[bool] = None,
        router_config_path: Optional[os.PathLike] = None,
    ):
        self.router_config = _load_router_runtime_config(router_config_path)
        self.registry = registry or ModelRegistry()
        self.hardware_profiler = hardware_profiler or HardwareProfiler()
        self.policy = policy or self.router_config.policy
        self.model_manager = model_manager or ModelManager(self.registry)

        self.enabled = bool(self.router_config.enabled)
        self.allow_cloud_models = bool(self.router_config.allow_cloud_models)
        self.policy_version = str(self.router_config.policy_version or "v2.0.1")
        self.allow_empty_candidates_fallback = bool(self.router_config.allow_empty_candidates_fallback)
        self.fallback_strategy = str(self.router_config.fallback_strategy or "local_first")
        self.static_model_key = str(self.router_config.static_model_key or "")

        # 默认不强制加载/下载权重：仓库通常不包含权重文件，避免“仅路由就失败”；
        # eager_load=None 表示使用 router_config.yaml 中的配置。
        if eager_load is None:
            self.eager_load = bool(self.router_config.eager_load)
        else:
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
        reasons.append(
            "router_config: "
            + f"path={(str(self.router_config.config_path) if self.router_config.config_path else None)}, "
            + f"enabled={self.enabled}, eager_load={self.eager_load}, allow_cloud={self.allow_cloud_models}, "
            + f"policy_version={self.policy_version}"
        )

        # 全局 cloud 开关：即使非 restricted，也允许通过 router_config.yaml 关闭 cloud 模型。
        # restricted 场景仍然强制禁用 cloud（安全优先）。
        if not self.allow_cloud_models or task.security_level == SecurityLevel.RESTRICTED:
            before = len(candidates)
            candidates = [m for m in candidates if not m.is_cloud]
            if len(candidates) != before:
                reasons.append(f"candidate: cloud_filtered {before}->{len(candidates)}")

        # 若路由器被禁用：不进行 scoring，直接走 fallback 策略（仍保留候选过滤与安全约束）
        if not self.enabled:
            primary = self._choose_fallback_model(task, candidates, reasons)
            decision = RoutingDecision(
                primary=primary,
                secondary=None,
                fallback=primary,
                estimated_latency_ms=self.policy.estimate_latency_ms(primary, task),
                estimated_vram_peak_gb=float(primary.vram_est_gb) * float(self.policy.vram_overcommit_ratio),
                decision_reasons=reasons + ["router: disabled -> fallback selected"],
                policy_version=self.policy_version,
            )
            await self._ensure_loaded(decision)
            return decision

        if not candidates:
            if not self.allow_empty_candidates_fallback:
                raise ModelSelectionError("候选模型为空（allow_empty_candidates_fallback=false）")

            # 降级：从所有 enabled 模型里选一个最省 VRAM 的，保证系统可继续运行
            all_models = self.registry.list_models(enabled_only=True)
            if not all_models:
                raise ModelSelectionError("模型注册表为空：请配置 infrastructure/model_hub/model_configs.yaml")

            # 仍然尊重 restricted 与模态约束
            filtered = []
            for m in all_models:
                if (not self.allow_cloud_models or task.security_level == SecurityLevel.RESTRICTED) and m.is_cloud:
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
                policy_version=self.policy_version,
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
            policy_version=self.policy_version,
        )
        await self._ensure_loaded(decision)
        return decision

    def _choose_fallback_model(self, task: TaskProfile, candidates: List[ModelProfile], reasons: List[str]) -> ModelProfile:
        """
        根据 fallback 策略选择模型。

        该逻辑用于：
        - router 被禁用时的 primary 选择
        - 后续可能扩展到“候选为空时”的更复杂回退策略
        """
        strategy = (self.fallback_strategy or "local_first").strip().lower()

        # static：指定固定模型（更适合联调/灰度；生产需确保该模型可用且满足安全约束）
        if strategy == "static" and self.static_model_key:
            try:
                m = self.registry.get_model(self.static_model_key)
                if not m.enabled:
                    raise ValueError("static model disabled")
                if (not self.allow_cloud_models or task.security_level == SecurityLevel.RESTRICTED) and m.is_cloud:
                    raise ValueError("static model is cloud but not allowed")
                if not m.supports_modalities(task.modalities):
                    raise ValueError("static model does not support modalities")
                reasons.append(f"fallback: static model={m.model_id}")
                return m
            except Exception as e:
                reasons.append(f"fallback: static model unusable ({self.static_model_key}): {e}")

        # cloud_first：允许 cloud 时优先 cloud；否则回退 local_first
        if strategy == "cloud_first" and self.allow_cloud_models and task.security_level != SecurityLevel.RESTRICTED:
            cloud = [m for m in candidates if m.is_cloud]
            if cloud:
                chosen = min(cloud, key=lambda m: float(m.vram_est_gb or 0.0))
                reasons.append(f"fallback: cloud_first -> {chosen.model_id}")
                return chosen
            reasons.append("fallback: cloud_first but no cloud candidates -> local_first")

        # local_first（默认）：选择最省资源模型（更稳）
        if candidates:
            chosen = min(candidates, key=lambda m: float(m.vram_est_gb or 0.0))
            reasons.append(f"fallback: local_first -> {chosen.model_id}")
            return chosen

        # candidates 为空：从所有 enabled 里兜底（再过滤一次安全/模态）
        all_models = self.registry.list_models(enabled_only=True)
        filtered: List[ModelProfile] = []
        for m in all_models:
            if (not self.allow_cloud_models or task.security_level == SecurityLevel.RESTRICTED) and m.is_cloud:
                continue
            if not m.supports_modalities(task.modalities):
                continue
            filtered.append(m)

        if not filtered:
            raise ModelSelectionError("无可用模型：fallback 策略也无法选出符合约束的模型")

        chosen = min(filtered, key=lambda m: float(m.vram_est_gb or 0.0))
        reasons.append(f"fallback: all_models -> {chosen.model_id}")
        return chosen

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
