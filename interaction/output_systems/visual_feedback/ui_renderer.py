"""
UI 渲染器（UI Renderer）

本模块的定位是“可运行的最小渲染层”：
- 默认渲染到控制台（可选 rich 增强）
- 同时输出结构化 view_model，便于未来替换为 Electron/Qt/Three.js 前端
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional
import logging
import time

from .theme_manager import ThemeManager

logger = logging.getLogger(__name__)

try:
    from rich.console import Console
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except Exception:
    Console = None
    Markdown = None
    RICH_AVAILABLE = False


class RenderBackend(Enum):
    CONSOLE = "console"
    SILENT = "silent"
    CALLBACK = "callback"


@dataclass
class RenderResult:
    success: bool
    backend: str
    render_time_s: float
    error: Optional[str] = None


class UIRenderer:
    """渲染器：将 view_model 渲染到指定后端。"""

    def __init__(
        self,
        theme_manager: Optional[ThemeManager] = None,
        backend: RenderBackend = RenderBackend.CONSOLE,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.theme_manager = theme_manager or ThemeManager()
        self.backend = backend
        self.callback = callback
        self.console = Console() if (RICH_AVAILABLE and backend == RenderBackend.CONSOLE) else None

    def set_backend(self, backend: RenderBackend, callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        self.backend = backend
        self.callback = callback
        self.console = Console() if (RICH_AVAILABLE and backend == RenderBackend.CONSOLE) else None

    def render(self, view_model: Dict[str, Any]) -> RenderResult:
        start = time.time()
        try:
            if self.backend == RenderBackend.SILENT:
                return RenderResult(success=True, backend=self.backend.value, render_time_s=time.time() - start)

            if self.backend == RenderBackend.CALLBACK:
                if not self.callback:
                    return RenderResult(success=False, backend=self.backend.value, render_time_s=time.time() - start, error="No callback set")
                self.callback(view_model)
                return RenderResult(success=True, backend=self.backend.value, render_time_s=time.time() - start)

            # 默认 console 后端
            self._render_console(view_model)
            return RenderResult(success=True, backend=self.backend.value, render_time_s=time.time() - start)

        except Exception as e:
            return RenderResult(success=False, backend=self.backend.value, render_time_s=time.time() - start, error=str(e))

    def _render_console(self, view_model: Dict[str, Any]) -> None:
        vtype = view_model.get("type", "text")
        text = view_model.get("text", "")

        if self.console:
            if vtype == "markdown" and Markdown is not None:
                self.console.print(Markdown(text))
            else:
                style = view_model.get("style")
                self.console.print(text, style=style)
        else:
            # rich 不可用时降级为 print
            print(text)

    # 下面是一些便捷渲染入口（生成 view_model 并渲染）
    def render_text(self, text: str, style: Optional[str] = None) -> RenderResult:
        return self.render({"type": "text", "text": text, "style": style})

    def render_markdown(self, markdown: str) -> RenderResult:
        return self.render({"type": "markdown", "text": markdown})

    def render_notification(self, title: str, message: str, level: str = "info") -> RenderResult:
        prefix = {"info": "[INFO]", "success": "[OK]", "warning": "[WARN]", "error": "[ERR]"}.get(level, "[INFO]")
        text = f"{prefix} {title}: {message}"
        style = {"info": "cyan", "success": "green", "warning": "yellow", "error": "red"}.get(level)
        return self.render({"type": "notification", "text": text, "style": style, "level": level})

    def render_expression(self, expression: str, intensity: float = 1.0) -> RenderResult:
        text = f"[EXPR] {expression} (intensity={intensity:.2f})"
        return self.render({"type": "expression", "text": text, "style": "magenta"})

    def render_progress(self, label: str, percent: float, status: str = "running") -> RenderResult:
        percent = max(0.0, min(100.0, float(percent)))
        text = f"[PROG] {label}: {percent:.1f}% ({status})"
        style = "green" if status == "completed" else "cyan"
        return self.render({"type": "progress", "text": text, "style": style, "percent": percent, "status": status})

    def render_status(self, status: Dict[str, Any]) -> RenderResult:
        text = "[STATUS] " + ", ".join(f"{k}={v}" for k, v in status.items())
        return self.render({"type": "status", "text": text, "style": "blue"})


