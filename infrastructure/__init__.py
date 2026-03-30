"""
基础设施层统一入口。

职责：
- 对外暴露基础设施层初始化入口
- 聚合硬件探测、消息总线、资源管理、GPU 加速、模型服务等核心组件
- 保持同步/异步两种调用方式兼容
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, Union


logger = logging.getLogger(__name__)

__version__ = "2.0.0"
__all__ = ["initialize_infrastructure", "initialize_infrastructure_async"]


class _AsyncInitHandle:
    """让初始化入口同时兼容同步与异步调用。"""

    def __init__(self, task: "asyncio.Task[Dict[str, Any]]"):
        self._task = task

    def __await__(self):
        return self._task.__await__()


async def initialize_infrastructure_async(
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """异步初始化基础设施核心组件。"""
    config = config or {}

    from .communication.message_bus import MessageBus
    from .compute_storage.gpu_accelerator import GPUAccelerator
    from .compute_storage.model_serving_engine import ModelServingEngine
    from .compute_storage.resource_manager import ResourceManager
    from .platform_adapters.hardware_detector import HardwareDetector

    detector = HardwareDetector()
    hardware_info = detector.detect_all()

    message_bus = MessageBus(config.get("message_bus"))
    resource_manager = ResourceManager(config.get("resource_manager"))
    gpu_accelerator = GPUAccelerator()
    model_serving_engine = ModelServingEngine(config.get("model_serving_engine"))

    component_status: Dict[str, Dict[str, Any]] = {}

    async def _initialize_component(name: str, component: Any, **kwargs: Any) -> None:
        try:
            await component.initialize(**kwargs)
            component_status[name] = {"initialized": True, "error": None}
        except Exception as exc:
            logger.error("%s 初始化失败: %s", name, exc)
            component_status[name] = {"initialized": False, "error": str(exc)}

    await _initialize_component("message_bus", message_bus)
    await _initialize_component("resource_manager", resource_manager, hardware_info=hardware_info)
    await _initialize_component("gpu_accelerator", gpu_accelerator)
    await _initialize_component("model_serving_engine", model_serving_engine)

    return {
        "hardware_info": hardware_info,
        "components": {
            "message_bus": message_bus,
            "resource_manager": resource_manager,
            "gpu_accelerator": gpu_accelerator,
            "model_serving_engine": model_serving_engine,
        },
        "status": component_status,
    }


def initialize_infrastructure(
    config: Optional[Dict[str, Any]] = None,
) -> Union[Dict[str, Any], _AsyncInitHandle]:
    """同步/异步兼容的基础设施初始化入口。"""
    operation = initialize_infrastructure_async(config=config)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(operation)
    return _AsyncInitHandle(loop.create_task(operation))
