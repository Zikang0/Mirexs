"""
system/main_config.yaml 的加载与校验入口（v2）。

说明：
- 历史代码中存在 `from config.system.main_config import load_system_config` 的调用习惯；
  v2 起用该模块作为稳定入口，底层仍从 YAML 读取配置。
"""

from __future__ import annotations

from typing import Any, Dict

from . import ConfigError, config_manager


def load_system_config(reload: bool = False) -> Dict[str, Any]:
    """
    加载系统主配置（`config/system/main_config.yaml`）。

    Args:
        reload: 是否强制重新加载（绕过缓存）

    Returns:
        Dict[str, Any]: 主配置字典（已做 v2 最小校验）
    """

    return config_manager.get_system_config(reload=reload)


__all__ = ["load_system_config", "ConfigError"]

