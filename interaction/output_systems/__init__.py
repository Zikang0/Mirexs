"""
输出系统集成模块
提供统一的输出系统管理接口，整合语音输出、视觉反馈和对话管理功能
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .speech_output.multilingual_tts import TTSConfig, TTSResult


def _module_available(qualified_name: str) -> bool:
    """检查模块是否可导入（不触发模块执行）。"""
    try:
        return importlib.util.find_spec(qualified_name) is not None
    except Exception:
        return False


_SPEECH_TTS_MODULE = __name__ + ".speech_output.multilingual_tts"
SPEECH_OUTPUT_AVAILABLE = _module_available(_SPEECH_TTS_MODULE)
VISUAL_FEEDBACK_AVAILABLE = _module_available(__name__ + ".visual_feedback")
DIALOGUE_MANAGER_AVAILABLE = _module_available(__name__ + ".dialogue_manager")


class OutputMode(Enum):
    """输出模式枚举"""

    SPEECH = "speech"
    VISUAL = "visual"
    DIALOGUE = "dialogue"
    MULTIMODAL = "multimodal"
    AUTOMATIC = "automatic"


@dataclass
class OutputSystemConfig:
    """输出系统配置"""

    # 子系统启用状态
    speech_enabled: bool = True
    visual_enabled: bool = True
    dialogue_enabled: bool = True

    # 输出模式配置
    default_mode: OutputMode = OutputMode.MULTIMODAL
    auto_mode_switch: bool = True

    # 性能配置
    realtime_processing: bool = True
    parallel_processing: bool = True
    max_parallel_tasks: int = 5
    output_timeout: float = 10.0  # 秒

    # 存储配置
    save_output_data: bool = False
    data_retention_days: int = 30
    auto_save_interval: int = 300  # 秒

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "speech_enabled": self.speech_enabled,
            "visual_enabled": self.visual_enabled,
            "dialogue_enabled": self.dialogue_enabled,
            "default_mode": self.default_mode.value,
            "auto_mode_switch": self.auto_mode_switch,
            "realtime_processing": self.realtime_processing,
            "parallel_processing": self.parallel_processing,
            "max_parallel_tasks": self.max_parallel_tasks,
            "output_timeout": self.output_timeout,
            "save_output_data": self.save_output_data,
            "data_retention_days": self.data_retention_days,
            "auto_save_interval": self.auto_save_interval,
        }


class OutputSystemManager:
    """输出系统管理器 - 整合所有输出子系统"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = OutputSystemConfig()
        if config:
            self._update_config(config)

        # 子系统实例（当前主要接入语音输出；其余子系统可按需扩展）
        self.speech_system = None
        self.visual_system = None
        self.dialogue_system = None

        # 状态管理
        self.is_initialized = False
        self.is_active = False
        self.current_mode = self.config.default_mode
        self.last_mode_switch_time = 0.0

        # 线程安全
        self.lock = threading.RLock()

        # 会话管理与统计
        self.output_sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session_id: Optional[str] = None
        self.performance_stats = {
            "speech_output_time": [],
            "visual_output_time": [],
            "dialogue_output_time": [],
            "total_outputs": 0,
            "successful_outputs": 0,
            "failed_outputs": 0,
        }

        logger.info("输出系统管理器初始化完成")

    def _update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        for key, value in config.items():
            if hasattr(self.config, key):
                if key == "default_mode" and isinstance(value, str):
                    try:
                        value = OutputMode(value)
                    except ValueError:
                        logger.warning(f"无效的输出模式: {value}, 使用默认值")
                        continue
                setattr(self.config, key, value)

    async def initialize(self) -> bool:
        """初始化输出系统"""
        if self.is_initialized:
            logger.warning("输出系统已初始化")
            return True

        try:
            logger.info("正在初始化输出系统...")
            subsystems_initialized = []

            # 语音输出（TTS）
            if self.config.speech_enabled and SPEECH_OUTPUT_AVAILABLE:
                try:
                    from .speech_output.multilingual_tts import multilingual_tts

                    self.speech_system = multilingual_tts
                    subsystems_initialized.append("speech")
                    logger.info("语音输出系统初始化成功")
                except Exception as e:
                    logger.error(f"语音输出系统初始化失败: {e}")

            # 视觉反馈（当前为占位模块，后续接入真实实现）
            if self.config.visual_enabled and VISUAL_FEEDBACK_AVAILABLE:
                try:
                    from . import visual_feedback

                    self.visual_system = visual_feedback
                    subsystems_initialized.append("visual")
                except Exception as e:
                    logger.error(f"视觉反馈模块导入失败: {e}")

            # 对话管理（当前为占位模块，后续接入真实实现）
            if self.config.dialogue_enabled and DIALOGUE_MANAGER_AVAILABLE:
                try:
                    from . import dialogue_manager

                    self.dialogue_system = dialogue_manager
                    subsystems_initialized.append("dialogue")
                except Exception as e:
                    logger.error(f"对话管理模块导入失败: {e}")

            if not subsystems_initialized:
                logger.error("没有子系统初始化成功")
                return False

            self.is_initialized = True
            logger.info(f"输出系统初始化完成，激活的子系统: {subsystems_initialized}")
            return True

        except Exception as e:
            logger.error(f"输出系统初始化失败: {e}")
            return False

    async def activate(self) -> bool:
        """激活输出系统"""
        if not self.is_initialized:
            if not await self.initialize():
                return False

        if self.is_active:
            logger.warning("输出系统已激活")
            return True

        self.is_active = True
        logger.info("输出系统已激活")
        return True

    async def deactivate(self) -> None:
        """停用输出系统"""
        if not self.is_active:
            return
        self.is_active = False
        logger.info("输出系统已停用")

    def set_output_mode(self, mode: Union[OutputMode, str]) -> bool:
        """设置输出模式"""
        if isinstance(mode, str):
            try:
                mode = OutputMode(mode)
            except ValueError:
                logger.error(f"无效的输出模式: {mode}")
                return False

        self.current_mode = mode
        self.last_mode_switch_time = time.time()
        logger.info(f"输出模式设置为: {mode.value}")
        return True

    async def synthesize_speech(self, text: str, config: Optional["TTSConfig"] = None) -> Optional["TTSResult"]:
        """语音合成（便捷封装）"""
        if not self.is_active:
            if not await self.activate():
                return None

        if not self.speech_system:
            logger.warning("语音输出系统未初始化或不可用")
            return None

        start_time = time.time()
        try:
            result = await self.speech_system.synthesize(text, config)
            self.performance_stats["speech_output_time"].append(time.time() - start_time)
            self.performance_stats["total_outputs"] += 1
            self.performance_stats["successful_outputs"] += 1
            return result
        except Exception as e:
            self.performance_stats["total_outputs"] += 1
            self.performance_stats["failed_outputs"] += 1
            logger.error(f"语音合成失败: {e}")
            return None

    def get_system_status(self) -> Dict[str, Any]:
        """获取输出系统状态"""
        return {
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "current_mode": self.current_mode.value,
            "subsystems": {
                "speech": bool(self.speech_system) and self.config.speech_enabled,
                "visual": bool(self.visual_system) and self.config.visual_enabled,
                "dialogue": bool(self.dialogue_system) and self.config.dialogue_enabled,
            },
            "availability": {
                "speech_output": SPEECH_OUTPUT_AVAILABLE,
                "visual_feedback": VISUAL_FEEDBACK_AVAILABLE,
                "dialogue_manager": DIALOGUE_MANAGER_AVAILABLE,
            },
            "stats": self.performance_stats,
        }

    async def shutdown(self) -> None:
        """关闭输出系统"""
        logger.info("正在关闭输出系统...")

        await self.deactivate()

        if self.speech_system and hasattr(self.speech_system, "cleanup"):
            try:
                await self.speech_system.cleanup()
            except Exception as e:
                logger.warning(f"语音输出系统清理失败: {e}")

        self.is_initialized = False
        self.output_sessions.clear()
        self.current_session_id = None
        logger.info("输出系统已关闭")


_output_system_manager_instance: Optional[OutputSystemManager] = None
_output_system_manager_lock = threading.Lock()


def get_output_system_manager(config: Optional[Dict[str, Any]] = None) -> OutputSystemManager:
    """获取输出系统管理器单例实例"""
    global _output_system_manager_instance

    with _output_system_manager_lock:
        if _output_system_manager_instance is None:
            _output_system_manager_instance = OutputSystemManager(config)
        return _output_system_manager_instance


async def initialize_output_systems(config: Optional[Dict[str, Any]] = None) -> bool:
    """初始化输出系统（便捷函数）"""
    manager = get_output_system_manager(config)
    return await manager.initialize()


async def activate_output_systems() -> bool:
    """激活输出系统（便捷函数）"""
    manager = get_output_system_manager()
    return await manager.activate()


async def deactivate_output_systems() -> None:
    """停用输出系统（便捷函数）"""
    manager = get_output_system_manager()
    await manager.deactivate()


async def synthesize_speech(text: str, config: Optional["TTSConfig"] = None) -> Optional["TTSResult"]:
    """语音合成（便捷函数）"""
    manager = get_output_system_manager()
    return await manager.synthesize_speech(text, config)


def get_output_system_status() -> Dict[str, Any]:
    """获取输出系统状态（便捷函数）"""
    manager = get_output_system_manager()
    return manager.get_system_status()


def set_output_mode(mode: Union[OutputMode, str]) -> bool:
    """设置输出模式（便捷函数）"""
    manager = get_output_system_manager()
    return manager.set_output_mode(mode)


async def shutdown_output_systems() -> None:
    """关闭输出系统（便捷函数）"""
    manager = get_output_system_manager()
    await manager.shutdown()


__all__ = [
    "OutputSystemManager",
    "OutputSystemConfig",
    "OutputMode",
    "SPEECH_OUTPUT_AVAILABLE",
    "VISUAL_FEEDBACK_AVAILABLE",
    "DIALOGUE_MANAGER_AVAILABLE",
    "get_output_system_manager",
    "initialize_output_systems",
    "activate_output_systems",
    "deactivate_output_systems",
    "synthesize_speech",
    "get_output_system_status",
    "set_output_mode",
    "shutdown_output_systems",
]

__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "Mirexs输出系统 - 集成语音输出、视觉反馈和对话管理"


def _initialize_package() -> None:
    """包初始化函数"""
    availability = {
        "语音输出": "可用" if SPEECH_OUTPUT_AVAILABLE else "不可用",
        "视觉反馈": "可用" if VISUAL_FEEDBACK_AVAILABLE else "不可用",
        "对话管理": "可用" if DIALOGUE_MANAGER_AVAILABLE else "不可用",
    }
    logger.info(f"初始化 Mirexs 输出系统 v{__version__}")
    logger.info(f"描述: {__description__}")
    logger.info(f"子系统可用性: {availability}")


_initialize_package()

