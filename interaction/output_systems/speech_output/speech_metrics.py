"""
语音输出指标（Speech Metrics）

收集语音合成与后处理的核心指标，用于：
- 性能监控（延迟、实时因子）
- 音频质量粗测（峰值、RMS、削波率）
- 统计汇总与可观测性
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List
import time

import numpy as np


def _as_2d(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.ndim == 1:
        return audio.reshape(-1, 1)
    if audio.ndim == 2 and audio.shape[1] in (1, 2):
        return audio
    raise ValueError(f"Unsupported audio shape: {audio.shape}")


@dataclass
class SpeechSynthesisMetrics:
    text_length: int
    sample_rate: int
    duration_s: float
    peak: float
    rms: float
    clipping_ratio: float
    processing_time_s: float
    realtime_factor: float  # processing_time / duration
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SpeechMetricsCollector:
    """语音指标收集器"""

    def __init__(self, max_history: int = 200):
        self.max_history = max_history
        self.history: List[SpeechSynthesisMetrics] = []

    def record(self, text: str, audio: np.ndarray, sample_rate: int, processing_time_s: float) -> SpeechSynthesisMetrics:
        audio2d = _as_2d(audio)
        duration = float(audio2d.shape[0]) / float(sample_rate) if sample_rate > 0 else 0.0
        peak = float(np.max(np.abs(audio2d))) if audio2d.size else 0.0
        rms = float(np.sqrt(np.mean(audio2d**2))) if audio2d.size else 0.0
        clipping_ratio = float(np.mean(np.abs(audio2d) >= 1.0)) if audio2d.size else 0.0
        rtf = (float(processing_time_s) / duration) if duration > 1e-6 else 0.0

        metrics = SpeechSynthesisMetrics(
            text_length=len(text or ""),
            sample_rate=int(sample_rate),
            duration_s=duration,
            peak=peak,
            rms=rms,
            clipping_ratio=clipping_ratio,
            processing_time_s=float(processing_time_s),
            realtime_factor=float(rtf),
            timestamp=time.time(),
        )

        self.history.append(metrics)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        return metrics

    def summary(self) -> Dict[str, Any]:
        if not self.history:
            return {"count": 0}

        durations = np.array([m.duration_s for m in self.history], dtype=np.float32)
        latencies = np.array([m.processing_time_s for m in self.history], dtype=np.float32)
        rtfs = np.array([m.realtime_factor for m in self.history], dtype=np.float32)
        clipping = np.array([m.clipping_ratio for m in self.history], dtype=np.float32)

        return {
            "count": len(self.history),
            "avg_duration_s": float(durations.mean()),
            "avg_latency_s": float(latencies.mean()),
            "p95_latency_s": float(np.percentile(latencies, 95)),
            "avg_rtf": float(rtfs.mean()),
            "max_clipping_ratio": float(clipping.max()),
        }


