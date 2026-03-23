"""
兼容模块：compute_storage.smart_model_router

历史上项目树/部分文档将“智能模型路由”放在 compute_storage 下。
自 v2.0 起，推荐将路由策略与模型生命周期管理统一放入 `infrastructure/model_hub/`。

本文件提供向后兼容的导入路径：
`from infrastructure.compute_storage.smart_model_router import SmartModelRouter`
等价于：
`from infrastructure.model_hub.smart_model_router import SmartModelRouter`
"""

from infrastructure.model_hub.smart_model_router import (
    ModelSelectionError,
    RoutingDecision,
    RoutingPolicy,
    SecurityLevel,
    SmartModelRouter,
    TaskProfile,
    TaskType,
)

__all__ = [
    "TaskType",
    "SecurityLevel",
    "TaskProfile",
    "RoutingDecision",
    "RoutingPolicy",
    "SmartModelRouter",
    "ModelSelectionError",
]

