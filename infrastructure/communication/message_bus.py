"""
消息总线：模块间的同步/异步兼容消息传递。

设计目标：
- 兼容现有同步调用：`message_bus.publish("topic", payload)`
- 兼容现有异步调用：`await message_bus.publish(MessageTopic.USER_INPUT, payload)`
- 允许枚举主题与任意字符串主题并存，避免上层模块因为“只支持枚举”而失效
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


logger = logging.getLogger(__name__)


class MessageTopic(Enum):
    """消息主题枚举。"""

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


TopicType = Union[MessageTopic, str]


@dataclass
class Message:
    """消息对象。"""

    id: str
    topic: TopicType
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

    @property
    def topic_name(self) -> str:
        """统一返回可序列化的主题名称。"""
        if isinstance(self.topic, MessageTopic):
            return self.topic.value
        return str(self.topic)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "topic": self.topic_name,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典恢复消息。"""
        topic_value = data["topic"]
        try:
            topic: TopicType = MessageTopic(topic_value)
        except ValueError:
            topic = topic_value

        return cls(
            id=data["id"],
            topic=topic,
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
        )


class _AsyncPublishHandle:
    """让同步/异步调用共享同一套 publish 接口。"""

    def __init__(self, task: "asyncio.Task[str]"):
        self._task = task

    def __await__(self):
        return self._task.__await__()


class MessageBus:
    """消息总线。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.subscribers: Dict[str, List[Callable[[Message], Any]]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.message_history: List[Message] = []
        self.max_history_size = int(self.config.get("max_history_size", 1000))
        self.initialized = False

    async def initialize(self) -> None:
        """初始化消息总线。"""
        if self.initialized:
            return
        self.initialized = True
        logger.info("消息总线初始化完成")

    def subscribe(self, topic: TopicType, callback: Callable[[Message], Any]) -> None:
        """订阅消息。"""
        topic_key = self._normalize_topic(topic)
        if topic_key not in self.subscribers:
            self.subscribers[topic_key] = []
        self.subscribers[topic_key].append(callback)
        logger.debug("消息订阅: %s", topic_key)

    def unsubscribe(self, topic: TopicType, callback: Callable[[Message], Any]) -> None:
        """取消订阅。"""
        topic_key = self._normalize_topic(topic)
        callbacks = self.subscribers.get(topic_key)
        if callbacks and callback in callbacks:
            callbacks.remove(callback)
            logger.debug("取消订阅: %s", topic_key)

    def publish(
        self,
        topic: TopicType,
        payload: Dict[str, Any],
        source: str = "system",
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Union[str, _AsyncPublishHandle]:
        """
        发布消息。

        - 同步上下文：直接执行并返回 message_id
        - 异步上下文：调度任务并返回可 await 对象
        """
        operation = self._publish_async(
            topic=topic,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
            reply_to=reply_to,
        )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(operation)

        return _AsyncPublishHandle(loop.create_task(operation))

    def send_message(
        self,
        topic: TopicType,
        payload: Dict[str, Any],
        source: str = "system",
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> Union[str, _AsyncPublishHandle]:
        """兼容上层 `send_message` 风格调用。"""
        return self.publish(
            topic=topic,
            payload=payload,
            source=source,
            correlation_id=correlation_id,
            reply_to=reply_to,
        )

    async def request_response(
        self,
        topic: TopicType,
        payload: Dict[str, Any],
        timeout: float = 30.0,
        response_topic: TopicType = MessageTopic.AI_RESPONSE,
    ) -> Optional[Message]:
        """请求-响应模式。"""
        correlation_id = str(uuid.uuid4())
        response_queue: asyncio.Queue = asyncio.Queue()

        async def response_handler(message: Message) -> None:
            if message.correlation_id == correlation_id:
                await response_queue.put(message)

        self.subscribe(response_topic, response_handler)

        try:
            await self.publish(
                topic=topic,
                payload=payload,
                correlation_id=correlation_id,
            )
            try:
                return await asyncio.wait_for(response_queue.get(), timeout)
            except asyncio.TimeoutError:
                logger.warning("请求响应超时: %s", self._normalize_topic(topic))
                return None
        finally:
            self.unsubscribe(response_topic, response_handler)

    def get_message_stats(self) -> Dict[str, Any]:
        """获取消息统计。"""
        topic_counts: Dict[str, int] = {}
        for message in self.message_history:
            topic_name = message.topic_name
            topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1

        return {
            "total_messages": len(self.message_history),
            "queue_size": self.message_queue.qsize(),
            "topic_distribution": topic_counts,
            "subscriber_counts": {
                topic_name: len(callbacks)
                for topic_name, callbacks in self.subscribers.items()
            },
        }

    async def _publish_async(
        self,
        topic: TopicType,
        payload: Dict[str, Any],
        source: str = "system",
        correlation_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> str:
        if not self.initialized:
            await self.initialize()

        message = Message(
            id=str(uuid.uuid4()),
            topic=topic,
            payload=payload,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id,
            reply_to=reply_to,
        )

        await self.message_queue.put(message)
        self.message_queue.get_nowait()
        self.message_queue.task_done()

        self.message_history.append(message)
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)

        await self._dispatch_message(message)
        logger.debug("消息发布: %s from %s", message.topic_name, source)
        return message.id

    async def _dispatch_message(self, message: Message) -> None:
        """分发消息给订阅者。"""
        callbacks = list(self.subscribers.get(message.topic_name, []))
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    result = callback(message)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as exc:
                logger.error("消息回调错误 [%s]: %s", message.topic_name, exc)

    def _normalize_topic(self, topic: TopicType) -> str:
        if isinstance(topic, MessageTopic):
            return topic.value
        return str(topic)


message_bus = MessageBus()
