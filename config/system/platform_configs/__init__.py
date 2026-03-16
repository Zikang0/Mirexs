# config/system/platform_configs/__init__.py
"""
平台配置模块
管理不同平台的特定配置
"""

import os
import sys
import platform
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass

from .. import config_manager


class PlatformType(Enum):
    """平台类型枚举"""
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    MOBILE = "mobile"
    CROSS_PLATFORM = "cross_platform"


@dataclass
class PlatformInfo:
    """平台信息"""
    name: str
    version: str
    architecture: str
    distribution: Optional[str] = None
    desktop_environment: Optional[str] = None

    @classmethod
    def detect(cls) -> 'PlatformInfo':
        """检测当前平台信息"""
        system = platform.system()
        version = platform.version()
        arch = platform.machine()

        if system == "Windows":
            return cls(
                name="Windows",
                version=platform.win32_ver()[0],
                architecture=arch,
                distribution=None,
                desktop_environment=None
            )
        elif system == "Linux":
            import distro
            dist = distro.id()
            version = distro.version()

            # 检测桌面环境
            de = os.environ.get('XDG_CURRENT_DESKTOP',
                                os.environ.get('DESKTOP_SESSION', 'unknown'))

            return cls(
                name="Linux",
                version=version,
                architecture=arch,
                distribution=dist,
                desktop_environment=de
            )
        elif system == "Darwin":
            return cls(
                name="macOS",
                version=platform.mac_ver()[0],
                architecture=arch,
                distribution=None,
                desktop_environment=None
            )
        else:
            return cls(
                name=system,
                version=version,
                architecture=arch,
                distribution=None,
                desktop_environment=None
            )


class PlatformConfig:
    """平台配置管理器"""

    def __init__(self):
        self.platform_info = PlatformInfo.detect()
        self.platform_name = self._get_platform_name()

        # 加载平台配置
        self.platform_config = self.load_platform_config()
        self.cross_platform_config = config_manager.get_platform_config()

    def _get_platform_name(self) -> str:
        """获取平台配置名称"""
        system = platform.system().lower()

        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "macos"
        else:
            return "cross_platform"

    def load_platform_config(self) -> Dict:
        """加载当前平台配置"""
        try:
            return config_manager.get_platform_config(self.platform_name)
        except Exception as e:
            print(f"加载平台配置失败: {e}")
            return {}

    def get_platform_specific(self, key: str, default=None):
        """获取平台特定配置"""
        # 先尝试平台特定配置
        value = self.platform_config.get(key)
        if value is not None:
            return value

        # 然后尝试跨平台配置
        value = self.cross_platform_config.get(key)
        if value is not None:
            return value

        return default

    def get_path(self, key: str) -> str:
        """获取平台特定路径"""
        paths = self.get_platform_specific('paths', {})
        return paths.get(key, '')

    def is_mobile(self) -> bool:
        """是否移动平台"""
        return self.platform_name == "mobile"

    def is_desktop(self) -> bool:
        """是否桌面平台"""
        return self.platform_name in ["windows", "linux", "macos"]

    def get_graphics_backend(self) -> str:
        """获取图形后端"""
        if self.platform_name == "windows":
            return "directx"
        elif self.platform_name == "macos":
            return "metal"
        else:
            return "opengl"

    def get_audio_backend(self) -> str:
        """获取音频后端"""
        if self.platform_name == "windows":
            return "wasapi"
        elif self.platform_name == "macos":
            return "coreaudio"
        else:
            return "pulseaudio"


# 全局平台配置实例
platform_config = PlatformConfig()

__all__ = [
    'PlatformType',
    'PlatformInfo',
    'PlatformConfig',
    'platform_config'
]
