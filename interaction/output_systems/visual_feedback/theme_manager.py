"""
主题管理（Theme Manager）

为 Mirexs 的视觉反馈子系统提供可切换主题能力。
当前实现偏“后端/渲染无关”：输出的是结构化主题信息，
具体 UI 框架（Electron/Qt/Three.js）可在上层适配。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, Optional, Union
import json
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Theme:
    name: str
    colors: Dict[str, str]
    typography: Dict[str, Any] = field(default_factory=dict)
    spacing: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ThemeManager:
    """主题管理器"""

    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.current_theme: Theme = self._create_default_themes()

    def _create_default_themes(self) -> Theme:
        light = Theme(
            name="light",
            colors={
                "background": "#FAFAFA",
                "surface": "#FFFFFF",
                "text_primary": "#212121",
                "text_secondary": "#616161",
                "primary": "#1976D2",
                "success": "#2E7D32",
                "warning": "#ED6C02",
                "error": "#D32F2F",
                "info": "#0288D1",
                "border": "#E0E0E0",
            },
            typography={"font_family": "system-ui", "font_size": 14},
            spacing={"base": 8},
        )

        dark = Theme(
            name="dark",
            colors={
                "background": "#121212",
                "surface": "#1E1E1E",
                "text_primary": "#FFFFFF",
                "text_secondary": "#B0BEC5",
                "primary": "#90CAF9",
                "success": "#81C784",
                "warning": "#FFB74D",
                "error": "#EF9A9A",
                "info": "#81D4FA",
                "border": "#424242",
            },
            typography={"font_family": "system-ui", "font_size": 14},
            spacing={"base": 8},
        )

        self.themes[light.name] = light
        self.themes[dark.name] = dark
        return light

    def register_theme(self, theme: Theme, overwrite: bool = False) -> bool:
        if (not overwrite) and theme.name in self.themes:
            return False
        self.themes[theme.name] = theme
        return True

    def set_theme(self, name: str) -> bool:
        theme = self.themes.get(name)
        if not theme:
            return False
        self.current_theme = theme
        logger.info(f"Theme set to: {name}")
        return True

    def get_theme(self, name: Optional[str] = None) -> Theme:
        if name is None:
            return self.current_theme
        return self.themes.get(name, self.current_theme)

    def export_themes(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "current": self.current_theme.name,
            "themes": {name: theme.to_dict() for name, theme in self.themes.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return path

    def import_themes(self, path: Union[str, Path], overwrite: bool = False) -> int:
        path = Path(path)
        if not path.exists():
            return 0

        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        imported = 0
        themes = payload.get("themes", {})
        for name, theme_dict in themes.items():
            try:
                theme = Theme(**theme_dict)
                if self.register_theme(theme, overwrite=overwrite):
                    imported += 1
            except Exception as e:
                logger.warning(f"Skip invalid theme '{name}': {e}")

        current = payload.get("current")
        if current:
            self.set_theme(current)

        return imported


