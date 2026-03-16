"""
通知引擎（Notification Engine）

提供系统通知的生成、队列管理、过期清理与渲染派发。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional
from collections import deque
import time
import uuid

from .ui_renderer import UIRenderer
from .visual_metrics import VisualMetricsCollector


class NotificationLevel(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Notification:
    notification_id: str
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    created_at: float = field(default_factory=time.time)
    ttl_s: Optional[float] = 10.0
    category: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl_s is None:
            return False
        return (time.time() - self.created_at) >= float(self.ttl_s)

    def to_view_model(self) -> Dict[str, Any]:
        return {
            "type": "notification",
            "id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "created_at": self.created_at,
            "ttl_s": self.ttl_s,
            "category": self.category,
            "metadata": dict(self.metadata),
        }


class NotificationEngine:
    def __init__(
        self,
        renderer: Optional[UIRenderer] = None,
        metrics: Optional[VisualMetricsCollector] = None,
        max_queue: int = 50,
    ):
        self.renderer = renderer or UIRenderer()
        self.metrics = metrics or VisualMetricsCollector()
        self.max_queue = max_queue
        self.queue: Deque[Notification] = deque()
        self.subscribers: List[Callable[[Notification], None]] = []

        # 用于去重：dedupe_key -> notification_id
        self._dedupe_index: Dict[str, str] = {}

    def subscribe(self, callback: Callable[[Notification], None]) -> None:
        self.subscribers.append(callback)

    def push(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        ttl_s: Optional[float] = 10.0,
        category: str = "system",
        dedupe_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        render: bool = True,
    ) -> str:
        if dedupe_key and dedupe_key in self._dedupe_index:
            # 更新已存在通知
            existing_id = self._dedupe_index[dedupe_key]
            for n in self.queue:
                if n.notification_id == existing_id:
                    n.title = title
                    n.message = message
                    n.level = level
                    n.ttl_s = ttl_s
                    n.created_at = time.time()
                    n.metadata.update(metadata or {})
                    if render:
                        self._render(n)
                    return existing_id

        n = Notification(
            notification_id=str(uuid.uuid4()),
            title=title,
            message=message,
            level=level,
            ttl_s=ttl_s,
            category=category,
            metadata=metadata or {},
        )

        self.queue.appendleft(n)
        if dedupe_key:
            self._dedupe_index[dedupe_key] = n.notification_id

        while len(self.queue) > self.max_queue:
            dropped = self.queue.pop()
            # 清理去重索引
            for k, v in list(self._dedupe_index.items()):
                if v == dropped.notification_id:
                    del self._dedupe_index[k]

        self.metrics.record("notification")

        for cb in list(self.subscribers):
            try:
                cb(n)
            except Exception:
                pass

        if render:
            self._render(n)

        return n.notification_id

    def list_active(self) -> List[Notification]:
        self.cleanup_expired()
        return list(self.queue)

    def dismiss(self, notification_id: str) -> bool:
        for idx, n in enumerate(self.queue):
            if n.notification_id == notification_id:
                del self.queue[idx]
                for k, v in list(self._dedupe_index.items()):
                    if v == notification_id:
                        del self._dedupe_index[k]
                return True
        return False

    def cleanup_expired(self) -> int:
        removed = 0
        kept: Deque[Notification] = deque()
        for n in self.queue:
            if n.is_expired():
                removed += 1
                for k, v in list(self._dedupe_index.items()):
                    if v == n.notification_id:
                        del self._dedupe_index[k]
            else:
                kept.append(n)
        self.queue = kept
        return removed

    def _render(self, notification: Notification) -> None:
        vm = notification.to_view_model()
        title = vm.get("title", "")
        msg = vm.get("message", "")
        level = vm.get("level", "info")
        result = self.renderer.render_notification(title, msg, level=level)
        self.metrics.record("render", duration_s=result.render_time_s, metadata={"type": "notification"})


