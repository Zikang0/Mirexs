"""
模型库（Model Hub）

该包负责：
- 维护模型元数据清单（model_configs.yaml）
- 设备硬件画像（HardwareProfile）与缓存快照
- 模型下载/校验/缓存（ModelDownloader）
- 模型注册、候选筛选（ModelRegistry）
- 模型生命周期（ModelManager：下载/加载/卸载/淘汰的“管理逻辑层”）
- 智能路由（SmartModelRouter：根据任务画像 + 硬件画像选择模型）

说明：
本仓库中“推理后端/具体模型加载实现”分散在 data/models/* 与 infrastructure/compute_storage/*。
Model Hub 在 v2.0 的定位是**统一的策略与管理层**：尽量不强绑定某个推理引擎，
而提供清晰可替换的接口，让上层应用/能力层决定最终如何调用具体推理实现。
"""

from .hardware_profile import HardwareProfile, HardwareProfiler
from .model_downloader import ModelDownloader, ModelDownloadError
from .model_registry import ModelProfile, ModelRegistry, ModelConfigError
from .model_manager import ModelManager, ModelManagerError
from .smart_model_router import (
    RoutingDecision,
    RoutingPolicy,
    SmartModelRouter,
    TaskProfile,
    TaskType,
    SecurityLevel,
    ModelSelectionError,
)

__all__ = [
    "HardwareProfile",
    "HardwareProfiler",
    "ModelDownloader",
    "ModelDownloadError",
    "ModelProfile",
    "ModelRegistry",
    "ModelConfigError",
    "ModelManager",
    "ModelManagerError",
    "TaskType",
    "SecurityLevel",
    "TaskProfile",
    "RoutingDecision",
    "RoutingPolicy",
    "SmartModelRouter",
    "ModelSelectionError",
]

