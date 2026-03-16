"""
视觉反馈子系统 (Visual Feedback)

该包对应 Mirexs 的多模态输出系统中的“视觉反馈”部分：
- UI 渲染（目前以 console 为默认后端）
- 通知系统
- 表情反馈
- 进度与状态展示

说明：当前实现优先保证“可运行、可替换、易集成”。未来接入真实 GUI 时，
只需替换 UIRenderer 的 backend/callback 或新增适配层即可。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import threading

from .theme_manager import ThemeManager, Theme
from .layout_engine import LayoutEngine, LayoutRect, LayoutItem
from .ui_renderer import UIRenderer, RenderBackend
from .visual_metrics import VisualMetricsCollector
from .notification_engine import NotificationEngine, NotificationLevel, Notification
from .expression_display import ExpressionDisplay, ExpressionState
from .progress_indicator import ProgressIndicator, ProgressStatus, ProgressTask
from .status_display import StatusDisplay, SystemStatus


@dataclass
class VisualFeedbackConfig:
    backend: str = "console"  # console | silent | callback
    theme: str = "light"
    notifications_enabled: bool = True
    progress_enabled: bool = True
    expression_enabled: bool = True
    status_enabled: bool = True


class VisualFeedbackManager:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = VisualFeedbackConfig()
        if config:
            for k, v in config.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)

        self.metrics = VisualMetricsCollector()

        self.theme_manager = ThemeManager()
        self.theme_manager.set_theme(self.config.theme)

        backend = RenderBackend(self.config.backend) if self.config.backend in {b.value for b in RenderBackend} else RenderBackend.CONSOLE
        self.renderer = UIRenderer(theme_manager=self.theme_manager, backend=backend)

        self.layout_engine = LayoutEngine()

        self.notification_engine = NotificationEngine(renderer=self.renderer, metrics=self.metrics)
        self.expression_display = ExpressionDisplay(renderer=self.renderer, metrics=self.metrics)
        self.progress_indicator = ProgressIndicator(renderer=self.renderer, metrics=self.metrics)
        self.status_display = StatusDisplay(renderer=self.renderer, metrics=self.metrics)

    def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        ttl_s: Optional[float] = 10.0,
        category: str = "system",
        dedupe_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.config.notifications_enabled:
            return ""
        return self.notification_engine.push(
            title=title,
            message=message,
            level=level,
            ttl_s=ttl_s,
            category=category,
            dedupe_key=dedupe_key,
            metadata=metadata,
            render=True,
        )

    def set_expression(self, expression: str, intensity: float = 1.0, source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> Optional[ExpressionState]:
        if not self.config.expression_enabled:
            return None
        return self.expression_display.set_expression(expression, intensity=intensity, source=source, metadata=metadata)

    def start_task(self, label: str, total: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        if not self.config.progress_enabled:
            return ""
        return self.progress_indicator.start(label=label, total=total, metadata=metadata)

    def update_task(self, task_id: str, **kwargs) -> bool:
        if not self.config.progress_enabled:
            return False
        return self.progress_indicator.update(task_id, **kwargs)

    def finish_task(self, task_id: str, success: bool = True, message: str = "") -> bool:
        if not self.config.progress_enabled:
            return False
        return self.progress_indicator.finish(task_id, success=success, message=message)

    def render_status(self, extra: Optional[Dict[str, Any]] = None) -> Optional[SystemStatus]:
        if not self.config.status_enabled:
            return None
        return self.status_display.render(extra=extra)

    def get_visual_status(self) -> Dict[str, Any]:
        return {
            "config": self.config.__dict__.copy(),
            "theme": self.theme_manager.get_theme().name,
            "metrics": self.metrics.summary(),
            "notifications": len(self.notification_engine.list_active()),
            "progress_tasks": len(self.progress_indicator.tasks),
            "expression": None if not self.expression_display.current else self.expression_display.current.to_dict(),
        }


_visual_feedback_manager_instance: Optional[VisualFeedbackManager] = None
_visual_feedback_manager_lock = threading.Lock()


def get_visual_feedback_manager(config: Optional[Dict[str, Any]] = None) -> VisualFeedbackManager:
    global _visual_feedback_manager_instance
    with _visual_feedback_manager_lock:
        if _visual_feedback_manager_instance is None:
            _visual_feedback_manager_instance = VisualFeedbackManager(config)
        return _visual_feedback_manager_instance


__all__ = [
    # 配置与管理器
    "VisualFeedbackConfig",
    "VisualFeedbackManager",
    "get_visual_feedback_manager",
    # 主题与布局
    "ThemeManager",
    "Theme",
    "LayoutEngine",
    "LayoutRect",
    "LayoutItem",
    # 渲染
    "UIRenderer",
    "RenderBackend",
    # 通知
    "NotificationEngine",
    "NotificationLevel",
    "Notification",
    # 表情
    "ExpressionDisplay",
    "ExpressionState",
    # 进度
    "ProgressIndicator",
    "ProgressStatus",
    "ProgressTask",
    # 状态
    "StatusDisplay",
    "SystemStatus",
    # 指标
    "VisualMetricsCollector",
]

