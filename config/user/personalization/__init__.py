# config/user/personalization/__init__.py
"""
个性化设置模块
管理用户界面外观、行为、快捷键、主题和无障碍功能
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ThemeMode(Enum):
    """主题模式枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


class AnimationSpeed(Enum):
    """动画速度枚举"""
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    NONE = "none"


class UIDensity(Enum):
    """UI密度枚举"""
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


@dataclass
class AppearanceSettings:
    """外观设置"""
    theme: ThemeMode = ThemeMode.AUTO
    font_size: str = "medium"  # small, medium, large, x-large
    animation_speed: AnimationSpeed = AnimationSpeed.NORMAL
    avatar_size: str = "medium"  # small, medium, large
    ui_density: UIDensity = UIDensity.COMFORTABLE
    custom_colors: Dict[str, str] = field(default_factory=dict)
    rounded_corners: bool = True
    shadow_effects: bool = True
    transparency: bool = False

    def get_css_variables(self) -> Dict[str, str]:
        """获取CSS变量"""
        variables = {
            "--theme-mode": self.theme.value,
            "--font-size": self.font_size,
            "--animation-speed": self.animation_speed.value,
            "--ui-density": self.ui_density.value,
            "--rounded-corners": "8px" if self.rounded_corners else "0",
            "--shadow-level": "medium" if self.shadow_effects else "none",
            "--opacity-level": "0.9" if self.transparency else "1.0"
        }

        # 添加自定义颜色
        for name, color in self.custom_colors.items():
            variables[f"--color-{name}"] = color

        return variables


@dataclass
class BehaviorSettings:
    """行为设置"""
    auto_start: bool = False
    minimize_to_tray: bool = True
    confirm_exit: bool = True
    save_session: bool = True
    auto_save_interval: int = 5  # 分钟
    idle_timeout: int = 30  # 分钟
    background_operation: bool = True
    startup_delay: int = 0  # 秒

    def get_startup_command(self) -> Optional[str]:
        """获取启动命令"""
        if self.auto_start:
            command = "mirexs --start-minimized" if self.minimize_to_tray else "mirexs"
            if self.startup_delay > 0:
                return f"sleep {self.startup_delay} && {command}"
            return command
        return None


@dataclass
class ShortcutKey:
    """快捷键定义"""
    name: str
    description: str
    default_key: str
    current_key: str
    enabled: bool = True
    category: str = "general"

    def validate(self) -> bool:
        """验证快捷键"""
        # 简单的验证：检查快捷键格式
        keys = self.current_key.split('+')
        if len(keys) == 0:
            return False

        # 检查修饰键
        valid_modifiers = ['Ctrl', 'Shift', 'Alt', 'Cmd', 'Win']
        modifiers = [k for k in keys if k in valid_modifiers]

        # 至少需要一个非修饰键
        if len(modifiers) == len(keys):
            return False

        return True


@dataclass
class ShortcutSettings:
    """快捷键设置"""
    shortcuts: List[ShortcutKey] = field(default_factory=list)

    def __post_init__(self):
        if not self.shortcuts:
            self.shortcuts = self.get_default_shortcuts()

    def get_default_shortcuts(self) -> List[ShortcutKey]:
        """获取默认快捷键"""
        return [
            ShortcutKey("activate_app", "激活应用", "Ctrl+Shift+M", "Ctrl+Shift+M"),
            ShortcutKey("mute_microphone", "静音麦克风", "Ctrl+Shift+S", "Ctrl+Shift+S"),
            ShortcutKey("screenshot", "截图", "Ctrl+Shift+P", "Ctrl+Shift+P"),
            ShortcutKey("quick_note", "快速笔记", "Ctrl+Shift+N", "Ctrl+Shift+N"),
            ShortcutKey("toggle_theme", "切换主题", "Ctrl+Shift+T", "Ctrl+Shift+T"),
            ShortcutKey("search", "全局搜索", "Ctrl+K", "Ctrl+K"),
            ShortcutKey("new_chat", "新建对话", "Ctrl+N", "Ctrl+N"),
            ShortcutKey("settings", "打开设置", "Ctrl+,", "Ctrl+,"),
        ]

    def get_shortcut(self, name: str) -> Optional[ShortcutKey]:
        """获取指定快捷键"""
        for shortcut in self.shortcuts:
            if shortcut.name == name:
                return shortcut
        return None

    def update_shortcut(self, name: str, key: str, enabled: bool = True) -> bool:
        """更新快捷键"""
        shortcut = self.get_shortcut(name)
        if shortcut:
            shortcut.current_key = key
            shortcut.enabled = enabled
            return True
        return False


@dataclass
class ThemeSettings:
    """主题设置"""
    active_theme: str = "default"
    custom_themes: Dict[str, Dict] = field(default_factory=dict)
    dark_mode: str = "auto"  # auto, light, dark
    accent_color: str = "#6200EE"
    background_color: str = "#FFFFFF"
    text_color: str = "#000000"
    font_family: str = "system-ui"

    def get_theme_config(self, theme_name: Optional[str] = None) -> Dict:
        """获取主题配置"""
        theme = theme_name or self.active_theme

        if theme in self.custom_themes:
            return self.custom_themes[theme]

        # 返回默认主题
        default_themes = {
            "default": {
                "name": "默认主题",
                "colors": {
                    "primary": "#6200EE",
                    "secondary": "#03DAC6",
                    "background": "#FFFFFF",
                    "surface": "#F5F5F5",
                    "error": "#B00020",
                    "text": "#000000",
                    "text_secondary": "#666666"
                },
                "font": "system-ui"
            },
            "dark": {
                "name": "深色主题",
                "colors": {
                    "primary": "#BB86FC",
                    "secondary": "#03DAC6",
                    "background": "#121212",
                    "surface": "#1E1E1E",
                    "error": "#CF6679",
                    "text": "#FFFFFF",
                    "text_secondary": "#B0B0B0"
                },
                "font": "system-ui"
            },
            "blue": {
                "name": "蓝色主题",
                "colors": {
                    "primary": "#2196F3",
                    "secondary": "#FF9800",
                    "background": "#E3F2FD",
                    "surface": "#FFFFFF",
                    "error": "#F44336",
                    "text": "#0D47A1",
                    "text_secondary": "#546E7A"
                },
                "font": "system-ui"
            }
        }

        return default_themes.get(theme, default_themes["default"])


@dataclass
class AccessibilitySettings:
    """无障碍设置"""
    screen_reader: bool = False
    high_contrast: bool = False
    reduce_motion: bool = False
    text_to_speech: bool = False
    large_text: bool = False
    color_blind_mode: str = "none"  # none, protanopia, deuteranopia, tritanopia
    keyboard_navigation: bool = True
    focus_indicators: bool = True
    sound_cues: bool = False

    def get_accessibility_features(self) -> List[str]:
        """获取启用的无障碍功能"""
        features = []

        if self.screen_reader:
            features.append("screen_reader")
        if self.high_contrast:
            features.append("high_contrast")
        if self.reduce_motion:
            features.append("reduce_motion")
        if self.text_to_speech:
            features.append("text_to_speech")
        if self.large_text:
            features.append("large_text")
        if self.color_blind_mode != "none":
            features.append(f"color_blind_{self.color_blind_mode}")
        if self.keyboard_navigation:
            features.append("keyboard_navigation")
        if self.focus_indicators:
            features.append("focus_indicators")
        if self.sound_cues:
            features.append("sound_cues")

        return features


class PersonalizationManager:
    """个性化设置管理器"""

    def __init__(self, user_manager):
        """初始化个性化设置管理器"""
        self.user_manager = user_manager
        self.load_settings()

    def load_settings(self):
        """加载所有个性化设置"""
        # 加载外观设置
        appearance_data = self.user_manager.get_config("personalization", "appearance")
        self.appearance = AppearanceSettings(**appearance_data)

        # 加载行为设置
        behavior_data = self.user_manager.get_config("personalization", "behavior")
        self.behavior = BehaviorSettings(**behavior_data)

        # 加载快捷键设置
        shortcuts_data = self.user_manager.get_config("personalization", "shortcuts")
        self.shortcuts = ShortcutSettings(
            shortcuts=[ShortcutKey(**s) for s in shortcuts_data.get("shortcuts", [])]
        )

        # 加载主题设置
        themes_data = self.user_manager.get_config("personalization", "themes")
        self.themes = ThemeSettings(**themes_data)

        # 加载无障碍设置
        accessibility_data = self.user_manager.get_config("personalization", "accessibility")
        self.accessibility = AccessibilitySettings(**accessibility_data)

    def save_settings(self):
        """保存所有个性化设置"""
        # 保存外观设置
        self.user_manager.save_config("personalization", "appearance", self.appearance.__dict__)

        # 保存行为设置
        self.user_manager.save_config("personalization", "behavior", self.behavior.__dict__)

        # 保存快捷键设置
        shortcuts_dict = {"shortcuts": [s.__dict__ for s in self.shortcuts.shortcuts]}
        self.user_manager.save_config("personalization", "shortcuts", shortcuts_dict)

        # 保存主题设置
        self.user_manager.save_config("personalization", "themes", self.themes.__dict__)

        # 保存无障碍设置
        self.user_manager.save_config("personalization", "accessibility", self.accessibility.__dict__)

    def apply_settings(self):
        """应用个性化设置到系统"""
        # 应用外观设置
        css_variables = self.appearance.get_css_variables()
        # TODO: 应用CSS变量到UI

        # 应用行为设置
        startup_cmd = self.behavior.get_startup_command()
        if startup_cmd:
            # TODO: 配置启动项
            pass

        # 应用快捷键设置
        # TODO: 注册系统快捷键

        # 应用无障碍设置
        accessibility_features = self.accessibility.get_accessibility_features()
        # TODO: 启用无障碍功能

    def create_custom_theme(self, name: str, colors: Dict[str, str], font: str = "system-ui"):
        """创建自定义主题"""
        self.themes.custom_themes[name] = {
            "name": name,
            "colors": colors,
            "font": font
        }
        self.save_settings()

    def set_active_theme(self, theme_name: str):
        """设置活动主题"""
        self.themes.active_theme = theme_name
        self.save_settings()
        self.apply_settings()

    def get_shortcut_for_action(self, action_name: str) -> Optional[str]:
        """获取指定动作的快捷键"""
        shortcut = self.shortcuts.get_shortcut(action_name)
        if shortcut and shortcut.enabled:
            return shortcut.current_key
        return None


# 导出主要功能
__all__ = [
    'ThemeMode',
    'AnimationSpeed',
    'UIDensity',
    'AppearanceSettings',
    'BehaviorSettings',
    'ShortcutKey',
    'ShortcutSettings',
    'ThemeSettings',
    'AccessibilitySettings',
    'PersonalizationManager'
]
