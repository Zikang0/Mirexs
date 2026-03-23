"""
兼容入口：smart_router.py

历史原因：部分文档/代码可能使用 `infrastructure.model_hub.smart_router` 作为路由入口。
当前推荐统一使用 `infrastructure.model_hub.smart_model_router`。
"""

from .smart_model_router import (
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

