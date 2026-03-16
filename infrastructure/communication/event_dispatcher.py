"""
事件分发器：事件的注册和分发
负责系统事件的注册、分发和生命周期管理
"""

import asyncio
import weakref
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

class EventType(Enum):
    """事件类型枚举"""
    SYSTEM_INITIALIZED = "system.initialized"
    SYSTEM_ERROR = "system.error"
    USER_SESSION_START = "user.session.start"
    USER_SESSION_END = "user.session.end"
    MODEL_LOAD_START = "model.load.start"
    MODEL_LOAD_COMPLETE = "model.load.complete"
    TASK_EXECUTION_START = "task.execution.start"
    TASK_EXECUTION_COMPLETE = "task.execution.complete"
    MEMORY_UPDATED = "memory.updated"
    DEVICE_STATE_CHANGED = "device.state.changed"
    NETWORK_CONNECTION_LOST = "network.connection.lost"
    NETWORK_CONNECTION_RESTORED = "network.connection.restored"

@dataclass
class Event:
    """事件对象"""
    event_type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    event_id: str

class EventHandler:
    """事件处理器"""
    
    def __init__(self, callback: Callable, priority: int = 0, 
                 is_async: bool = False, filter_condition: Optional[Callable] = None):
        self.callback = callback
        self.priority = priority
        self.is_async = is_async
        self.filter_condition = filter_condition
        self.call_count = 0
        self.last_called: Optional[datetime] = None
    
    async def execute(self, event: Event) -> bool:
        """执行事件处理"""
        try:
            # 检查过滤条件
            if self.filter_condition and not self.filter_condition(event):
                return False
            
            # 执行回调
            if self.is_async:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(event)
                else:
                    # 将同步函数包装为异步
                    self.callback(event)
            else:
                self.callback(event)
            
            # 更新统计
            self.call_count += 1
            self.last_called = datetime.now()
            
            return True
            
        except Exception as e:
            logging.error(f"事件处理执行错误: {e}")
            return False

class EventDispatcher:
    """事件分发器"""
    
    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = {}
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        self.initialized = False
        
    async def initialize(self):
        """初始化事件分发器"""
        if self.initialized:
            return
            
        logging.info("初始化事件分发器...")
        self.initialized = True
        logging.info("事件分发器初始化完成")
    
    def register_handler(self, event_type: EventType, callback: Callable, 
                        priority: int = 0, filter_condition: Optional[Callable] = None):
        """注册事件处理器"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        
        is_async = asyncio.iscoroutinefunction(callback)
        handler = EventHandler(callback, priority, is_async, filter_condition)
        
        self.handlers[event_type].append(handler)
        # 按优先级排序
        self.handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        
        logging.debug(f"注册事件处理器: {event_type.value}, 优先级: {priority}")
    
    def unregister_handler(self, event_type: EventType, callback: Callable):
        """取消注册事件处理器"""
        if event_type not in self.handlers:
            return
        
        self.handlers[event_type] = [
            handler for handler in self.handlers[event_type]
            if handler.callback != callback
        ]
        
        logging.debug(f"取消注册事件处理器: {event_type.value}")
    
    async def dispatch_event(self, event_type: EventType, source: str, 
                           data: Dict[str, Any] = None) -> str:
        """分发事件"""
        if data is None:
            data = {}
        
        event = Event(
            event_type=event_type,
            source=source,
            timestamp=datetime.now(),
            data=data,
            event_id=str(uuid.uuid4())
        )
        
        # 保存到历史记录
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        # 分发给处理器
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    await handler.execute(event)
                except Exception as e:
                    logging.error(f"事件分发错误: {e}")
        
        logging.debug(f"事件分发完成: {event_type.value} from {source}")
        return event.event_id
    
    async def dispatch_event_async(self, event_type: EventType, source: str,
                                 data: Dict[str, Any] = None):
        """异步分发事件（不等待完成）"""
        asyncio.create_task(self.dispatch_event(event_type, source, data))
    
    def get_handler_stats(self, event_type: EventType = None) -> Dict[str, Any]:
        """获取处理器统计"""
        if event_type:
            handlers = self.handlers.get(event_type, [])
            return {
                "total_handlers": len(handlers),
                "handlers": [
                    {
                        "priority": handler.priority,
                        "is_async": handler.is_async,
                        "call_count": handler.call_count,
                        "last_called": handler.last_called.isoformat() if handler.last_called else None
                    }
                    for handler in handlers
                ]
            }
        else:
            stats = {}
            for evt_type, handlers in self.handlers.items():
                stats[evt_type.value] = {
                    "total_handlers": len(handlers),
                    "total_calls": sum(h.call_count for h in handlers)
                }
            return stats
    
    def get_event_stats(self) -> Dict[str, Any]:
        """获取事件统计"""
        event_counts = {}
        for event in self.event_history:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        return {
            "total_events": len(self.event_history),
            "event_distribution": event_counts,
            "recent_events": [
                {
                    "event_type": event.event_type.value,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat()
                }
                for event in self.event_history[-10:]  # 最近10个事件
            ]
        }
    
    def clear_history(self):
        """清空事件历史"""
        self.event_history.clear()
        logging.info("事件历史已清空")

# 全局事件分发器实例
event_dispatcher = EventDispatcher()

# 导入uuid用于生成事件ID
import uuid