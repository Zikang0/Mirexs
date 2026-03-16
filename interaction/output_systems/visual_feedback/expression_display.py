"""
表情反馈显示（Expression Display）

该模块负责将“情绪/表情”以可视化方式反馈给用户。
在当前代码库尚未接入完整前端的情况下：
- 默认输出到控制台（通过 UIRenderer）
- 可选尝试与 3D 虚拟猫咪系统对接（若可导入）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import logging
import time

from .ui_renderer import UIRenderer
from .visual_metrics import VisualMetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class ExpressionState:
    expression: str
    intensity: float = 1.0
    timestamp: float = 0.0
    source: str = "system"
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expression": self.expression,
            "intensity": float(self.intensity),
            "timestamp": float(self.timestamp),
            "source": self.source,
            "metadata": dict(self.metadata or {}),
        }


class ExpressionDisplay:
    def __init__(self, renderer: Optional[UIRenderer] = None, metrics: Optional[VisualMetricsCollector] = None):
        self.renderer = renderer or UIRenderer()
        self.metrics = metrics or VisualMetricsCollector()
        self.current: Optional[ExpressionState] = None

        # 可选接入 3D 虚拟猫咪系统
        self._avatar_system = None
        self._try_attach_avatar_system()

    def _try_attach_avatar_system(self) -> None:
        try:
            # 这里不强依赖；若 3D 系统可用，可在外部注入/接入
            from interaction.threed_avatar import ThreeDAvatarSystem

            self._avatar_system = ThreeDAvatarSystem()
        except Exception:
            self._avatar_system = None

    def set_expression(self, expression: str, intensity: float = 1.0, source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> ExpressionState:
        state = ExpressionState(
            expression=expression,
            intensity=max(0.0, min(2.0, float(intensity))),
            timestamp=time.time(),
            source=source,
            metadata=metadata or {},
        )
        self.current = state

        # 渲染到 UI
        result = self.renderer.render_expression(expression=state.expression, intensity=state.intensity)
        self.metrics.record("expression")
        self.metrics.record("render", duration_s=result.render_time_s, metadata={"type": "expression"})

        # 可选：驱动 3D 系统（如果已接入且初始化成功）
        if self._avatar_system and getattr(self._avatar_system, "is_initialized", False):
            try:
                # 统一使用字符串表达，具体映射由 3D 系统内部处理/扩展
                if hasattr(self._avatar_system, "emotion_engine") and self._avatar_system.emotion_engine:
                    self._avatar_system.emotion_engine.set_emotion(expression, intensity)
            except Exception as e:
                logger.debug(f"Avatar expression update skipped: {e}")

        return state

    def get_current(self) -> Optional[ExpressionState]:
        return self.current


