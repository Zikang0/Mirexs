"""
模型注册表（Model Registry）

职责：
1) 读取并校验 `model_configs.yaml`（模型画像/元数据）。
2) 提供按任务画像与硬件画像筛选候选模型的能力。
3) 作为路由层与模型管理层之间的“事实来源”（source of truth）。

注意：
- 该模块不负责实际模型加载/推理，仅管理“画像/元数据”。
- YAML Schema 以 `docs/architecture/multi_model_routing.md` 为主，允许兼容简化写法。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


class ModelConfigError(Exception):
    """模型配置文件错误（格式/字段/类型不符合约定）。"""


@dataclass(frozen=True)
class ModelProfile:
    """模型画像（稳定 Schema）。"""

    model_id: str
    family: str
    quant: str
    vram_est_gb: float
    ctx_len: int
    backend: str

    # 性能/能力指标（可选）
    tps_chat: float = 0.0
    tps_reason: float = 0.0
    capability_tags: List[str] = field(default_factory=list)
    modalities: List[str] = field(default_factory=lambda: ["text"])

    # 位置/分发（可选）
    path: Optional[str] = None  # 相对/绝对路径（优先级高）
    url: Optional[str] = None
    sha256: Optional[str] = None
    size_mb: Optional[float] = None

    # 控制字段
    enabled: bool = True
    is_cloud: bool = False  # restricted 场景需要禁用

    def supports_modalities(self, required: Iterable[str]) -> bool:
        req = {m.lower() for m in required}
        sup = {m.lower() for m in (self.modalities or ["text"])}
        # 兼容：某些配置可能只写 capability_tags
        tags = {t.lower() for t in (self.capability_tags or [])}
        sup = sup.union(tags)
        return req.issubset(sup)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "family": self.family,
            "quant": self.quant,
            "vram_est_gb": self.vram_est_gb,
            "ctx_len": self.ctx_len,
            "backend": self.backend,
            "tps_chat": self.tps_chat,
            "tps_reason": self.tps_reason,
            "capability_tags": list(self.capability_tags),
            "modalities": list(self.modalities),
            "path": self.path,
            "url": self.url,
            "sha256": self.sha256,
            "size_mb": self.size_mb,
            "enabled": self.enabled,
            "is_cloud": self.is_cloud,
        }


def _repo_root() -> Path:
    # infrastructure/model_hub -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]


class ModelRegistry:
    """模型注册表：加载配置并提供候选筛选。"""

    def __init__(
        self,
        config_path: Optional[os.PathLike] = None,
        *,
        models_dir: Optional[os.PathLike] = None,
    ):
        self.config_path = Path(config_path) if config_path else Path(__file__).with_name("model_configs.yaml")
        self.models_dir = Path(models_dir) if models_dir else Path(
            os.environ.get("MIREXS_MODELS_DIR", str(_repo_root() / "data" / "models"))
        )
        self._models: Dict[str, ModelProfile] = {}
        self.reload()

    def reload(self) -> None:
        """重新加载并校验配置文件。"""
        if not self.config_path.exists():
            raise ModelConfigError(f"模型配置文件不存在: {self.config_path}")

        try:
            import yaml  # type: ignore
        except Exception as e:
            raise ModelConfigError("缺少依赖：请安装 pyyaml 以解析 model_configs.yaml") from e

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            raise ModelConfigError(f"解析模型配置失败: {self.config_path}") from e

        models_raw: Any
        if isinstance(data, list):
            # 兼容：简化写法直接是列表
            models_raw = data
        elif isinstance(data, dict):
            models_raw = data.get("models", [])
        else:
            raise ModelConfigError("model_configs.yaml 顶层必须为 dict 或 list")

        if not isinstance(models_raw, list):
            raise ModelConfigError("model_configs.yaml: `models` 必须为列表")

        models: Dict[str, ModelProfile] = {}
        for idx, item in enumerate(models_raw):
            if not isinstance(item, dict):
                raise ModelConfigError(f"models[{idx}] 必须为 dict")
            profile = self._parse_model_profile(item, idx=idx)
            if profile.model_id in models:
                raise ModelConfigError(f"模型 ID 重复: {profile.model_id}")
            models[profile.model_id] = profile

        self._models = models

    def list_models(self, *, enabled_only: bool = True) -> List[ModelProfile]:
        models = list(self._models.values())
        if enabled_only:
            models = [m for m in models if m.enabled]
        return models

    def get_model(self, model_id: str) -> ModelProfile:
        if model_id not in self._models:
            raise KeyError(f"模型未注册: {model_id}")
        return self._models[model_id]

    def get_candidates(
        self,
        task: Any,
        hw: Any,
        *,
        vram_overcommit_ratio: float = 1.15,
    ) -> List[ModelProfile]:
        """
        根据任务画像与硬件画像筛选候选模型。

        过滤规则（MVP 可执行口径）：
        - enabled == True
        - 安全限制：task.security_level == restricted 时禁用 is_cloud 模型
        - 模态限制：task.modalities 必须被模型支持
        - 显存限制：vram_free >= vram_est * vram_overcommit_ratio（若无法获取 vram_free 则放宽）
        - 上下文限制：ctx_len >= 预计 token（超长则放宽但降低候选优先级，由 Policy 打分处理）
        """
        security_level = str(getattr(task, "security_level", "normal")).lower()
        restricted = security_level in {"restricted", "high", "private"}

        required_modalities = list(getattr(task, "modalities", ["text"]) or ["text"])
        required_modalities = [m.lower() for m in required_modalities]

        est_input = int(getattr(task, "estimated_input_tokens", 0) or 0)
        est_output = int(getattr(task, "estimated_output_tokens", 0) or 0)
        est_total_tokens = max(0, est_input) + max(0, est_output)

        vram_free = float(getattr(hw, "vram_free_gb", 0.0) or 0.0)
        vram_total = float(getattr(hw, "vram_total_gb", 0.0) or 0.0)

        candidates: List[ModelProfile] = []
        for model in self.list_models(enabled_only=True):
            if restricted and model.is_cloud:
                continue
            if not model.supports_modalities(required_modalities):
                continue

            # VRAM 约束：拿不到 vram_free 时不强制过滤（允许 CPU/未知环境继续运行）
            if vram_free > 0 and model.vram_est_gb > 0:
                if vram_free < (model.vram_est_gb * float(vram_overcommit_ratio)):
                    continue
            else:
                # 若无 GPU，总显存为 0：依然允许 llama.cpp/transformers(可 CPU) 进入候选
                if vram_total <= 0 and model.backend.lower() in {"vllm"}:
                    # vLLM 通常强依赖 GPU，不在 CPU 环境候选
                    continue

            # ctx_len 过滤：不做硬过滤，交给 Policy 评分；但极端小 ctx_len 且明显不足时可过滤
            if model.ctx_len > 0 and est_total_tokens > 0:
                if model.ctx_len < min(4096, est_total_tokens // 4):
                    # 过小上下文窗口通常不可用（保守过滤）
                    continue

            candidates.append(model)

        return candidates

    def resolve_model_path(self, model: ModelProfile) -> Path:
        """
        解析模型权重路径（不保证存在）。

        优先级：
        1) model.path（可为绝对或相对）
        2) models_dir / family / model_id
        """
        if model.path:
            p = Path(model.path)
            return p if p.is_absolute() else (_repo_root() / p)
        return self.models_dir / model.family / model.model_id

    def _parse_model_profile(self, item: Dict[str, Any], *, idx: int) -> ModelProfile:
        # 兼容字段：id/model_id
        model_id = item.get("model_id", item.get("id"))
        if not model_id or not isinstance(model_id, str):
            raise ModelConfigError(f"models[{idx}].id/model_id 缺失或非法")

        family = item.get("family", item.get("model_family", "unknown"))
        quant = item.get("quant", item.get("quantization", "unknown"))
        backend = item.get("backend", item.get("engine", "llama_cpp"))

        def _float(v: Any, default: float = 0.0) -> float:
            try:
                return float(v)
            except Exception:
                return float(default)

        def _int(v: Any, default: int = 0) -> int:
            try:
                return int(v)
            except Exception:
                return int(default)

        vram_est_gb = _float(item.get("vram_est_gb", item.get("vram_requirement_gb", 0.0)))
        ctx_len = _int(item.get("ctx_len", item.get("context_window", 0)))

        tps_chat = _float(item.get("tps_chat", 0.0))
        tps_reason = _float(item.get("tps_reason", 0.0))
        tags = item.get("capability_tags", item.get("tags", [])) or []
        if not isinstance(tags, list):
            raise ModelConfigError(f"models[{idx}].capability_tags/tags 必须为列表")
        tags = [str(t) for t in tags]

        modalities = item.get("modalities", ["text"]) or ["text"]
        if isinstance(modalities, str):
            modalities = [modalities]
        if not isinstance(modalities, list):
            modalities = ["text"]
        modalities = [str(m).lower() for m in modalities]

        # is_cloud：兼容写法 deployment: cloud/local
        is_cloud = bool(item.get("is_cloud", False))
        deployment = str(item.get("deployment", "") or "").lower()
        if deployment in {"cloud", "remote"}:
            is_cloud = True
        elif deployment in {"local", "on_device", "on-prem"}:
            is_cloud = False

        enabled = bool(item.get("enabled", True))

        return ModelProfile(
            model_id=model_id,
            family=str(family),
            quant=str(quant),
            vram_est_gb=float(vram_est_gb),
            ctx_len=int(ctx_len),
            backend=str(backend),
            tps_chat=float(tps_chat),
            tps_reason=float(tps_reason),
            capability_tags=tags,
            modalities=modalities,
            path=item.get("path"),
            url=item.get("url"),
            sha256=item.get("sha256"),
            size_mb=item.get("size_mb"),
            enabled=enabled,
            is_cloud=is_cloud,
        )

