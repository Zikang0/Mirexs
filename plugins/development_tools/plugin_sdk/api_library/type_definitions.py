"""
类型定义模块

提供插件开发所需的数据类型定义，包括：
- 基础类型定义
- 插件相关类型
- 事件相关类型
- 配置相关类型

Author: AI Assistant
Date: 2025-11-05
"""

from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class PluginStatus(Enum):
    """插件状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    LOADING = "loading"
    UNLOADING = "unloading"


class EventType(Enum):
    """事件类型枚举"""
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"
    PLUGIN_ACTIVATED = "plugin_activated"
    PLUGIN_DEACTIVATED = "plugin_deactivated"
    CONFIG_CHANGED = "config_changed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class PluginMetadata:
    """插件元数据"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    dependencies: List[str]
    permissions: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class PluginConfig:
    """插件配置"""
    plugin_id: str
    settings: Dict[str, Any]
    enabled: bool = True
    auto_start: bool = False


@dataclass
class EventData:
    """事件数据"""
    event_type: EventType
    source: str
    data: Any
    timestamp: datetime
    metadata: Dict[str, Any] = None


class TypeDefinitions:
    """类型定义类"""
    
    # 基础类型别名
    PluginID = str
    PluginName = str
    PluginVersion = str
    ConfigKey = str
    ConfigValue = Any
    EventHandler = Callable[[EventData], None]
    
    # 复合类型
    PluginList = List[PluginMetadata]
    ConfigDict = Dict[str, ConfigValue]
    EventHandlerList = List[EventHandler]
    
    @staticmethod
    def validate_plugin_metadata(metadata: Dict[str, Any]) -> bool:
        """验证插件元数据"""
        required_fields = ['id', 'name', 'version', 'description', 'author']
        return all(field in metadata for field in required_fields)
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """验证配置数据"""
        return isinstance(config, dict)
    
    @staticmethod
    def create_plugin_metadata(**kwargs) -> PluginMetadata:
        """创建插件元数据"""
        return PluginMetadata(**kwargs)
    
    @staticmethod
    def create_plugin_config(plugin_id: str, settings: Dict[str, Any]) -> PluginConfig:
        """创建插件配置"""
        return PluginConfig(plugin_id=plugin_id, settings=settings)