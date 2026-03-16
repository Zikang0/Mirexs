"""
进度指示器（Progress Indicator）

为任务执行提供进度展示：适用于任务分解/执行监控场景。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import time
import uuid

from .ui_renderer import UIRenderer
from .visual_metrics import VisualMetricsCollector


class ProgressStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressTask:
    task_id: str
    label: str
    total: Optional[float] = None
    current: float = 0.0
    status: ProgressStatus = ProgressStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def percent(self) -> float:
        if not self.total or self.total <= 0:
            return 0.0
        return max(0.0, min(100.0, (self.current / self.total) * 100.0))


class ProgressIndicator:
    def __init__(self, renderer: Optional[UIRenderer] = None, metrics: Optional[VisualMetricsCollector] = None):
        self.renderer = renderer or UIRenderer()
        self.metrics = metrics or VisualMetricsCollector()
        self.tasks: Dict[str, ProgressTask] = {}

    def start(self, label: str, total: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        task_id = str(uuid.uuid4())
        task = ProgressTask(task_id=task_id, label=label, total=total, status=ProgressStatus.RUNNING, metadata=metadata or {})
        self.tasks[task_id] = task
        self._render(task)
        return task_id

    def update(
        self,
        task_id: str,
        current: Optional[float] = None,
        total: Optional[float] = None,
        status: Optional[ProgressStatus] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False

        if current is not None:
            task.current = float(current)
        if total is not None:
            task.total = float(total)
        if status is not None:
            task.status = status
        if message is not None:
            task.message = message
        if metadata:
            task.metadata.update(metadata)

        task.updated_at = time.time()
        self._render(task)
        return True

    def finish(self, task_id: str, success: bool = True, message: str = "") -> bool:
        status = ProgressStatus.COMPLETED if success else ProgressStatus.FAILED
        return self.update(task_id, status=status, message=message)

    def get(self, task_id: str) -> Optional[ProgressTask]:
        return self.tasks.get(task_id)

    def _render(self, task: ProgressTask) -> None:
        self.metrics.record("progress")
        result = self.renderer.render_progress(task.label, task.percent(), status=task.status.value)
        self.metrics.record("render", duration_s=result.render_time_s, metadata={"type": "progress"})


