"""
生命周期管理器

负责管理插件的完整生命周期，包括初始化、激活、停用、卸载等状态转换。
提供状态持久化和事件通知功能。

Author: AI Assistant
Date: 2025-11-05
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


class PluginState(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    UNLOADING = "unloading"


class LifecycleEvent(Enum):
    """生命周期事件枚举"""
    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_INITIALIZED = "plugin_initialized"
    PLUGIN_ACTIVATED = "plugin_activated"
    PLUGIN_DEACTIVATED = "plugin_deactivated"
    PLUGIN_ERROR = "plugin_error"
    PLUGIN_UNLOADED = "plugin_unloaded"
    STATE_CHANGED = "state_changed"


@dataclass
class LifecycleEventData:
    """生命周期事件数据"""
    plugin_name: str
    event_type: LifecycleEvent
    timestamp: datetime
    previous_state: Optional[PluginState] = None
    current_state: Optional[PluginState] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginLifecycleInfo:
    """插件生命周期信息"""
    plugin_name: str
    current_state: PluginState
    created_at: datetime
    last_modified: datetime
    activation_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class LifecycleManager:
    """插件生命周期管理器"""
    
    def __init__(self):
        """初始化生命周期管理器"""
        self.logger = logging.getLogger(__name__)
        self._plugin_states: Dict[str, PluginLifecycleInfo] = {}
        self._event_handlers: Dict[LifecycleEvent, List[Callable]] = defaultdict(list)
        self._state_history: Dict[str, List[LifecycleEventData]] = defaultdict(list)
        
    def register_event_handler(self, event_type: LifecycleEvent, handler: Callable) -> None:
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理器函数
        """
        self._event_handlers[event_type].append(handler)
        self.logger.info(f"注册事件处理器: {event_type.value}")
    
    def unregister_event_handler(self, event_type: LifecycleEvent, handler: Callable) -> bool:
        """
        注销事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理器函数
            
        Returns:
            bool: 注销成功返回True，否则返回False
        """
        try:
            if handler in self._event_handlers[event_type]:
                self._event_handlers[event_type].remove(handler)
                self.logger.info(f"注销事件处理器: {event_type.value}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"注销事件处理器失败: {str(e)}")
            return False
    
    def load_plugin(self, plugin_name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        加载插件
        
        Args:
            plugin_name: 插件名称
            metadata: 插件元数据
            
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            self.logger.info(f"加载插件: {plugin_name}")
            
            if plugin_name in self._plugin_states:
                self.logger.warning(f"插件已存在: {plugin_name}")
                return False
            
            # 创建生命周期信息
            lifecycle_info = PluginLifecycleInfo(
                plugin_name=plugin_name,
                current_state=PluginState.LOADED,
                created_at=datetime.now(),
                last_modified=datetime.now(),
                metadata=metadata or {}
            )
            
            self._plugin_states[plugin_name] = lifecycle_info
            
            # 触发事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_LOADED,
                timestamp=datetime.now(),
                current_state=PluginState.LOADED,
                metadata=metadata or {}
            ))
            
            self.logger.info(f"插件加载成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件加载失败 {plugin_name}: {str(e)}")
            self._set_error_state(plugin_name, str(e))
            return False
    
    def initialize_plugin(self, plugin_name: str) -> bool:
        """
        初始化插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 初始化成功返回True，否则返回False
        """
        try:
            self.logger.info(f"初始化插件: {plugin_name}")
            
            if plugin_name not in self._plugin_states:
                self.logger.error(f"插件不存在: {plugin_name}")
                return False
            
            lifecycle_info = self._plugin_states[plugin_name]
            previous_state = lifecycle_info.current_state
            
            # 检查状态转换是否合法
            if not self._is_valid_transition(previous_state, PluginState.INITIALIZED):
                self.logger.error(f"非法状态转换: {previous_state.value} -> INITIALIZED")
                return False
            
            # TODO: 执行实际的插件初始化逻辑
            time.sleep(0.1)  # 模拟初始化过程
            
            # 更新状态
            lifecycle_info.current_state = PluginState.INITIALIZED
            lifecycle_info.last_modified = datetime.now()
            
            # 触发事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_INITIALIZED,
                timestamp=datetime.now(),
                previous_state=previous_state,
                current_state=PluginState.INITIALIZED
            ))
            
            self.logger.info(f"插件初始化成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件初始化失败 {plugin_name}: {str(e)}")
            self._set_error_state(plugin_name, str(e))
            return False
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """
        激活插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 激活成功返回True，否则返回False
        """
        try:
            self.logger.info(f"激活插件: {plugin_name}")
            
            if plugin_name not in self._plugin_states:
                self.logger.error(f"插件不存在: {plugin_name}")
                return False
            
            lifecycle_info = self._plugin_states[plugin_name]
            previous_state = lifecycle_info.current_state
            
            # 检查状态转换是否合法
            if not self._is_valid_transition(previous_state, PluginState.ACTIVE):
                self.logger.error(f"非法状态转换: {previous_state.value} -> ACTIVE")
                return False
            
            # TODO: 执行实际的插件激活逻辑
            time.sleep(0.1)  # 模拟激活过程
            
            # 更新状态
            lifecycle_info.current_state = PluginState.ACTIVE
            lifecycle_info.last_modified = datetime.now()
            lifecycle_info.activation_count += 1
            
            # 触发事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_ACTIVATED,
                timestamp=datetime.now(),
                previous_state=previous_state,
                current_state=PluginState.ACTIVE
            ))
            
            self.logger.info(f"插件激活成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件激活失败 {plugin_name}: {str(e)}")
            self._set_error_state(plugin_name, str(e))
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        停用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 停用成功返回True，否则返回False
        """
        try:
            self.logger.info(f"停用插件: {plugin_name}")
            
            if plugin_name not in self._plugin_states:
                self.logger.error(f"插件不存在: {plugin_name}")
                return False
            
            lifecycle_info = self._plugin_states[plugin_name]
            previous_state = lifecycle_info.current_state
            
            # 检查状态转换是否合法
            if not self._is_valid_transition(previous_state, PluginState.INACTIVE):
                self.logger.error(f"非法状态转换: {previous_state.value} -> INACTIVE")
                return False
            
            # TODO: 执行实际的插件停用逻辑
            time.sleep(0.1)  # 模拟停用过程
            
            # 更新状态
            lifecycle_info.current_state = PluginState.INACTIVE
            lifecycle_info.last_modified = datetime.now()
            
            # 触发事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_DEACTIVATED,
                timestamp=datetime.now(),
                previous_state=previous_state,
                current_state=PluginState.INACTIVE
            ))
            
            self.logger.info(f"插件停用成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件停用失败 {plugin_name}: {str(e)}")
            self._set_error_state(plugin_name, str(e))
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 卸载成功返回True，否则返回False
        """
        try:
            self.logger.info(f"卸载插件: {plugin_name}")
            
            if plugin_name not in self._plugin_states:
                self.logger.error(f"插件不存在: {plugin_name}")
                return False
            
            lifecycle_info = self._plugin_states[plugin_name]
            previous_state = lifecycle_info.current_state
            
            # 设置为卸载中状态
            lifecycle_info.current_state = PluginState.UNLOADING
            lifecycle_info.last_modified = datetime.now()
            
            # TODO: 执行实际的插件卸载逻辑
            time.sleep(0.1)  # 模拟卸载过程
            
            # 移除插件
            del self._plugin_states[plugin_name]
            
            # 触发事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_UNLOADED,
                timestamp=datetime.now(),
                previous_state=previous_state,
                current_state=PluginState.UNLOADED
            ))
            
            self.logger.info(f"插件卸载成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件卸载失败 {plugin_name}: {str(e)}")
            self._set_error_state(plugin_name, str(e))
            return False
    
    def get_plugin_state(self, plugin_name: str) -> Optional[PluginState]:
        """
        获取插件状态
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[PluginState]: 插件状态，如果不存在返回None
        """
        if plugin_name in self._plugin_states:
            return self._plugin_states[plugin_name].current_state
        return None
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginLifecycleInfo]:
        """
        获取插件生命周期信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[PluginLifecycleInfo]: 插件生命周期信息，如果不存在返回None
        """
        return self._plugin_states.get(plugin_name)
    
    def list_plugins(self, state: Optional[PluginState] = None) -> List[str]:
        """
        列出插件
        
        Args:
            state: 插件状态过滤
            
        Returns:
            List[str]: 插件名称列表
        """
        if state is None:
            return list(self._plugin_states.keys())
        else:
            return [name for name, info in self._plugin_states.items() 
                   if info.current_state == state]
    
    def get_state_history(self, plugin_name: str, limit: int = 10) -> List[LifecycleEventData]:
        """
        获取状态历史
        
        Args:
            plugin_name: 插件名称
            limit: 返回记录数量限制
            
        Returns:
            List[LifecycleEventData]: 状态历史记录
        """
        history = self._state_history.get(plugin_name, [])
        return history[-limit:] if limit > 0 else history
    
    def _is_valid_transition(self, from_state: PluginState, to_state: PluginState) -> bool:
        """
        检查状态转换是否合法
        
        Args:
            from_state: 源状态
            to_state: 目标状态
            
        Returns:
            bool: 合法返回True，否则返回False
        """
        valid_transitions = {
            PluginState.UNLOADED: [PluginState.LOADED],
            PluginState.LOADED: [PluginState.INITIALIZED, PluginState.UNLOADED],
            PluginState.INITIALIZED: [PluginState.ACTIVE, PluginState.UNLOADED],
            PluginState.ACTIVE: [PluginState.INACTIVE, PluginState.ERROR],
            PluginState.INACTIVE: [PluginState.ACTIVE, PluginState.UNLOADED],
            PluginState.ERROR: [PluginState.LOADED, PluginState.UNLOADED],
            PluginState.UNLOADING: [PluginState.UNLOADED]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _set_error_state(self, plugin_name: str, error_message: str) -> None:
        """
        设置错误状态
        
        Args:
            plugin_name: 插件名称
            error_message: 错误信息
        """
        if plugin_name in self._plugin_states:
            lifecycle_info = self._plugin_states[plugin_name]
            previous_state = lifecycle_info.current_state
            
            lifecycle_info.current_state = PluginState.ERROR
            lifecycle_info.last_modified = datetime.now()
            lifecycle_info.error_count += 1
            
            # 触发错误事件
            self._trigger_event(LifecycleEventData(
                plugin_name=plugin_name,
                event_type=LifecycleEvent.PLUGIN_ERROR,
                timestamp=datetime.now(),
                previous_state=previous_state,
                current_state=PluginState.ERROR,
                error_message=error_message
            ))
    
    def _trigger_event(self, event_data: LifecycleEventData) -> None:
        """
        触发事件
        
        Args:
            event_data: 事件数据
        """
        # 记录到历史
        self._state_history[event_data.plugin_name].append(event_data)
        
        # 限制历史记录数量
        if len(self._state_history[event_data.plugin_name]) > 100:
            self._state_history[event_data.plugin_name] = self._state_history[event_data.plugin_name][-100:]
        
        # 调用事件处理器
        handlers = self._event_handlers.get(event_data.event_type, [])
        for handler in handlers:
            try:
                handler(event_data)
            except Exception as e:
                self.logger.error(f"事件处理器执行失败: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取生命周期统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            "total_plugins": len(self._plugin_states),
            "state_distribution": {},
            "total_activations": sum(info.activation_count for info in self._plugin_states.values()),
            "total_errors": sum(info.error_count for info in self._plugin_states.values())
        }
        
        # 统计状态分布
        for state in PluginState:
            count = len(self.list_plugins(state))
            stats["state_distribution"][state.value] = count
        
        return stats