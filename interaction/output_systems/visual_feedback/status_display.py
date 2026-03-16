"""
状态显示（Status Display）

输出 Mirexs 当前运行状态的简要视图：
- CPU / 内存 / 磁盘 / 网络（若 psutil 可用）
- 输出系统/输入系统等模块状态可由上层注入
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import time

from .ui_renderer import UIRenderer
from .visual_metrics import VisualMetricsCollector

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    PSUTIL_AVAILABLE = False


@dataclass
class SystemStatus:
    timestamp: float
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    net_sent_bytes: Optional[int] = None
    net_recv_bytes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StatusDisplay:
    def __init__(self, renderer: Optional[UIRenderer] = None, metrics: Optional[VisualMetricsCollector] = None):
        self.renderer = renderer or UIRenderer()
        self.metrics = metrics or VisualMetricsCollector()

    def collect(self) -> SystemStatus:
        ts = time.time()
        if not PSUTIL_AVAILABLE:
            return SystemStatus(timestamp=ts)

        cpu = float(psutil.cpu_percent(interval=None))
        mem = float(psutil.virtual_memory().percent)
        disk = float(psutil.disk_usage("/").percent)
        net = psutil.net_io_counters()

        return SystemStatus(
            timestamp=ts,
            cpu_percent=cpu,
            memory_percent=mem,
            disk_percent=disk,
            net_sent_bytes=int(net.bytes_sent),
            net_recv_bytes=int(net.bytes_recv),
        )

    def render(self, extra: Optional[Dict[str, Any]] = None) -> SystemStatus:
        status = self.collect()
        payload = status.to_dict()
        if extra:
            payload.update(extra)
        result = self.renderer.render_status(payload)
        self.metrics.record("status")
        self.metrics.record("render", duration_s=result.render_time_s, metadata={"type": "status"})
        return status


