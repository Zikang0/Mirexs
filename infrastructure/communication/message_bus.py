"""
消息总线：模块间的异步消息传递
负责系统内部模块之间的异步消息传递和事件通知
"""

import asyncio
import json
import uuid
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

class MessageTopic(Enum):
    """消息主题枚举"""
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    USER_INPUT = "user.input"
    AI_RESPONSE = "ai.response"
    TASK_START = "task.start"
    TASK_COMPLETE = "task.complete"
    TASK_ERROR = "task.error"
    MEMORY_UPDATE = "memory.update"
    MODEL_LOADED = "model.loaded"
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"

@dataclass
class Message:
    """消息对象"""
    id: str
    topic: MessageTopic
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "topic": self.topic.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建"""
        return cls(
            id=data["id"],
            topic=MessageTopic(data["topic"]),
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to")
        )

class MessageBus:
    """消息总线"""
    
    def __init__(self):
        self.subscribers: Dict[MessageTopic, List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.message_history: List[Message] = []
        self.max_history_size = 1000
        self.initialized = False
        
    async def initialize(self):
        """初始化消息总线"""
        if self.initialized:
            return
            
        logging.info("初始化消息总线...")
        
        # 启动消息处理任务
        self.processing_task = asyncio.create_task(self._message_processor())
        
        self.initialized = True
        logging.info("消息总线初始化完成")
    
    async def publish(self, topic: MessageTopic, payload: Dict[str, Any], 
                     source: str = "system", correlation_id: Optional[str] = None,
                     reply_to: Optional[str] = None) -> str:
        """发布消息"""
        message = Message(
            id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id,
            reply_to=reply_to
        )
        
        await self.message_queue.put(message)
        logging.debug(f"消息发布: {topic.value} from {source}")
        
        return message.id
    
    def subscribe(self, topic: MessageTopic, callback: Callable[[Message], None]):
        """订阅消息"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(callback)
        logging.debug(f"消息订阅: {topic.value}")
    
    def unsubscribe(self, topic: MessageTopic, callback: Callable[[Message], None]):
        """取消订阅"""
        if topic in self.subscribers and callback in self.subscribers[topic]:
            self.subscribers[topic].remove(callback)
            logging.debug(f"取消订阅: {topic.value}")
    
    async def _message_processor(self):
        """消息处理循环"""
        while True:
            try:
                message = await self.message_queue.get()
                await self._dispatch_message(message)
                self.message_queue.task_done()
                
            except Exception as e:
                logging.error(f"消息处理错误: {e}")
    
    async def _dispatch_message(self, message: Message):
        """分发消息给订阅者"""
        # 保存到历史记录
        self.message_history.append(message)
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)
        
        # 分发给订阅者
        if message.topic in self.subscribers:
            for callback in self.subscribers[message.topic]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logging.error(f"消息回调错误: {e}")
        
        logging.debug(f"消息分发完成: {message.topic.value}")
    
    async def request_response(self, topic: MessageTopic, payload: Dict[str, Any],
                             timeout: float = 30.0) -> Optional[Message]:
        """请求-响应模式"""
        correlation_id = str(uuid.uuid4())
        response_queue = asyncio.Queue()
        
        def response_handler(message: Message):
            if (message.correlation_id == correlation_id and 
                message.topic == MessageTopic.AI_RESPONSE):
                asyncio.create_task(response_queue.put(message))
        
        # 订阅响应
        self.subscribe(MessageTopic.AI_RESPONSE, response_handler)
        
        try:
            # 发送请求
            await self.publish(
                topic=topic,
                payload=payload,
                correlation_id=correlation_id
            )
            
            # 等待响应
            try:
                response = await asyncio.wait_for(response_queue.get(), timeout)
                return response
            except asyncio.TimeoutError:
                logging.warning(f"请求响应超时: {topic.value}")
                return None
                
        finally:
            # 取消订阅
            self.unsubscribe(MessageTopic.AI_RESPONSE, response_handler)
    
    def get_message_stats(self) -> Dict[str, Any]:
        """获取消息统计"""
        topic_counts = {}
        for message in self.message_history:
            topic = message.topic.value
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        return {
            "total_messages": len(self.message_history),
            "queue_size": self.message_queue.qsize(),
            "topic_distribution": topic_counts,
            "subscriber_counts": {
                topic.value: len(callbacks) 
                for topic, callbacks in self.subscribers.items()
            }
        }

# 全局消息总线实例
message_bus = MessageBus()