"""
视觉反馈指标（Visual Metrics）

用于记录视觉反馈子系统的运行指标：
- 渲染次数与平均耗时
- 通知数量
- 进度更新次数
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
import time


@dataclass
class VisualMetricEvent:
    event_type: str
    duration_s: float = 0.0
    timestamp: float = 0.0
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VisualMetricsCollector:
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.history: List[VisualMetricEvent] = []

        self.counters = {
            "render": 0,
            "notification": 0,
            "expression": 0,
            "progress": 0,
            "status": 0,
        }

    def record(self, event_type: str, duration_s: float = 0.0, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.counters[event_type] = self.counters.get(event_type, 0) + 1
        self.history.append(
            VisualMetricEvent(
                event_type=event_type,
                duration_s=float(duration_s),
                timestamp=time.time(),
                metadata=metadata or {},
            )
        )
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def summary(self) -> Dict[str, Any]:
        renders = [e.duration_s for e in self.history if e.event_type == "render"]
        avg_render = sum(renders) / len(renders) if renders else 0.0
        return {
            "counters": dict(self.counters),
            "avg_render_time_s": float(avg_render),
            "events": len(self.history),
        }


