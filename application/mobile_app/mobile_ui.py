"""
移动UI模块 - Mirexs移动应用程序

提供移动端用户界面组件和适配功能，包括：
1. 响应式布局适配
2. 移动端UI组件
3. 主题适配（浅色/深色）
4. 屏幕方向管理
5. 手势交互基础
6. 动画效果
"""

import logging
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import threading
import time

logger = logging.getLogger(__name__)

class ScreenOrientation(Enum):
    """屏幕方向枚举"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    AUTO = "auto"
    SENSOR = "sensor"
    UNSPECIFIED = "unspecified"

class UITheme(Enum):
    """UI主题枚举"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    AMOLED = "amoled"

class DeviceType(Enum):
    """设备类型枚举"""
    PHONE = "phone"
    TABLET = "tablet"
    FOLDABLE = "foldable"
    UNKNOWN = "unknown"

@dataclass
class ScreenSize:
    """屏幕尺寸信息"""
    width: int = 0
    height: int = 0
    density: float = 1.0
    scale: float = 1.0
    status_bar_height: int = 0
    navigation_bar_height: int = 0
    safe_area_top: int = 0
    safe_area_bottom: int = 0
    safe_area_left: int = 0
    safe_area_right: int = 0

@dataclass
class UIDimensions:
    """UI尺寸定义"""
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48
    
    # 字体大小
    font_xs: int = 10
    font_sm: int = 12
    font_md: int = 14
    font_lg: int = 16
    font_xl: int = 18
    font_xxl: int = 22
    font_title: int = 24
    font_header: int = 28
    
    # 组件尺寸
    button_height: int = 48
    input_height: int = 48
    icon_size_sm: int = 16
    icon_size_md: int = 24
    icon_size_lg: int = 32
    
    # 圆角
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12
    radius_xl: int = 16
    radius_circle: int = 9999

@dataclass
class UIColorPalette:
    """颜色调色板"""
    # 主要颜色
    primary: str = "#007AFF"
    primary_dark: str = "#005BB5"
    primary_light: str = "#4DA3FF"
    
    # 次要颜色
    secondary: str = "#5856D6"
    secondary_dark: str = "#3F3D9E"
    secondary_light: str = "#7A79E0"
    
    # 功能颜色
    success: str = "#34C759"
    warning: str = "#FF9500"
    error: str = "#FF3B30"
    info: str = "#5AC8FA"
    
    # 中性色
    background: str = "#FFFFFF"
    surface: str = "#F2F2F7"
    text_primary: str = "#000000"
    text_secondary: str = "#8E8E93"
    text_disabled: str = "#C7C7CC"
    border: str = "#C6C6C8"
    
    # 暗色模式覆盖
    dark_background: str = "#000000"
    dark_surface: str = "#1C1C1E"
    dark_text_primary: str = "#FFFFFF"
    dark_text_secondary: str = "#98989E"
    dark_text_disabled: str = "#48484A"
    dark_border: str = "#38383A"

@dataclass
class MobileUIConfig:
    """移动UI配置"""
    # 主题配置
    theme: UITheme = UITheme.SYSTEM
    accent_color: str = "#007AFF"
    
    # 屏幕配置
    default_orientation: ScreenOrientation = ScreenOrientation.PORTRAIT
    allow_orientation_change: bool = True
    
    # 动画配置
    animation_duration: float = 0.3  # 秒
    enable_animations: bool = True
    enable_haptic_feedback: bool = True
    
    # 布局配置
    use_edge_to_edge: bool = True
    use_gesture_navigation: bool = True
    bottom_navigation_height: int = 56
    
    # 文件路径
    config_file: str = "mobile_ui_config.json"
    data_dir: str = "data/mobile_ui/"

class MobileUI:
    """
    移动UI管理类
    
    负责移动端用户界面的创建、管理和适配，包括：
    - 屏幕尺寸适配
    - 主题管理
    - 方向控制
    - 布局计算
    - 动画管理
    """
    
    def __init__(self, config: Optional[MobileUIConfig] = None):
        """
        初始化移动UI管理器
        
        Args:
            config: UI配置
        """
        self.config = config or MobileUIConfig()
        
        # 屏幕信息
        self.screen_size = ScreenSize()
        self.dimensions = UIDimensions()
        self.colors = UIColorPalette()
        self.device_type = DeviceType.UNKNOWN
        
        # 当前状态
        self.current_theme: UITheme = self.config.theme
        self.current_orientation: ScreenOrientation = self.config.default_orientation
        self.is_folded: bool = False  # 折叠屏状态
        
        # 回调注册表
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # 动画相关
        self._animations: Dict[str, Dict[str, Any]] = {}
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载配置
        self._load_config()
        
        logger.info("MobileUI initialized")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_config(self):
        """加载UI配置"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 更新配置
                    if "theme" in data:
                        self.config.theme = UITheme(data["theme"])
                    if "accent_color" in data:
                        self.config.accent_color = data["accent_color"]
                
                logger.info(f"UI configuration loaded from {config_path}")
            except Exception as e:
                logger.error(f"Error loading UI configuration: {e}")
    
    def _save_config(self):
        """保存UI配置"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        try:
            data = {
                "theme": self.config.theme.value,
                "accent_color": self.config.accent_color,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"UI configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving UI configuration: {e}")
    
    def update_screen_info(self, width: int, height: int, density: float,
                          safe_area: Optional[Dict[str, int]] = None):
        """
        更新屏幕信息
        
        Args:
            width: 屏幕宽度
            height: 屏幕高度
            density: 像素密度
            safe_area: 安全区域信息
        """
        self.screen_size.width = width
        self.screen_size.height = height
        self.screen_size.density = density
        
        if safe_area:
            self.screen_size.safe_area_top = safe_area.get("top", 0)
            self.screen_size.safe_area_bottom = safe_area.get("bottom", 0)
            self.screen_size.safe_area_left = safe_area.get("left", 0)
            self.screen_size.safe_area_right = safe_area.get("right", 0)
        
        # 检测设备类型
        self._detect_device_type()
        
        logger.debug(f"Screen info updated: {width}x{height} @ {density}x")
        
        # 触发事件
        self._trigger_event("screen_info_changed", self.screen_size)
    
    def _detect_device_type(self):
        """检测设备类型"""
        width = self.screen_size.width
        height = self.screen_size.height
        min_dim = min(width, height)
        max_dim = max(width, height)
        
        # 简单的设备类型判断
        if max_dim >= 1200:  # 大屏幕
            self.device_type = DeviceType.TABLET
        elif max_dim >= 900 and self.config.allow_orientation_change:
            # 可能是折叠屏展开状态
            self.device_type = DeviceType.FOLDABLE
        else:
            self.device_type = DeviceType.PHONE
    
    def set_theme(self, theme: UITheme):
        """
        设置主题
        
        Args:
            theme: 主题枚举
        """
        old_theme = self.current_theme
        self.config.theme = theme
        self.current_theme = theme
        
        # 保存配置
        self._save_config()
        
        logger.info(f"Theme changed: {old_theme.value} -> {theme.value}")
        
        # 触发事件
        self._trigger_event("theme_changed", theme.value)
    
    def get_current_theme_colors(self) -> Dict[str, str]:
        """
        获取当前主题的颜色
        
        Returns:
            颜色字典
        """
        is_dark = self.current_theme in [UITheme.DARK, UITheme.AMOLED]
        
        if is_dark:
            return {
                "background": self.colors.dark_background,
                "surface": self.colors.dark_surface,
                "text_primary": self.colors.dark_text_primary,
                "text_secondary": self.colors.dark_text_secondary,
                "text_disabled": self.colors.dark_text_disabled,
                "border": self.colors.dark_border,
                "primary": self.config.accent_color,
                "success": self.colors.success,
                "warning": self.colors.warning,
                "error": self.colors.error
            }
        else:
            return {
                "background": self.colors.background,
                "surface": self.colors.surface,
                "text_primary": self.colors.text_primary,
                "text_secondary": self.colors.text_secondary,
                "text_disabled": self.colors.text_disabled,
                "border": self.colors.border,
                "primary": self.config.accent_color,
                "success": self.colors.success,
                "warning": self.colors.warning,
                "error": self.colors.error
            }
    
    def set_orientation(self, orientation: ScreenOrientation):
        """
        设置屏幕方向
        
        Args:
            orientation: 屏幕方向
        """
        if not self.config.allow_orientation_change and orientation != self.config.default_orientation:
            logger.warning("Orientation change not allowed")
            return
        
        self.current_orientation = orientation
        logger.info(f"Orientation set to: {orientation.value}")
        
        # 触发事件
        self._trigger_event("orientation_changed", orientation.value)
    
    def get_responsive_value(self, phone_value: Any, tablet_value: Any) -> Any:
        """
        根据设备类型获取响应式值
        
        Args:
            phone_value: 手机使用的值
            tablet_value: 平板使用的值
        
        Returns:
            对应的值
        """
        if self.device_type == DeviceType.TABLET:
            return tablet_value
        return phone_value
    
    def dp(self, value: int) -> int:
        """
        将dp值转换为像素
        
        Args:
            value: dp值
        
        Returns:
            像素值
        """
        return int(value * self.screen_size.density)
    
    def sp(self, value: int) -> int:
        """
        将sp值转换为像素（用于字体）
        
        Args:
            value: sp值
        
        Returns:
            像素值
        """
        return int(value * self.screen_size.scale)
    
    def get_safe_area_insets(self) -> Dict[str, int]:
        """
        获取安全区域插入值
        
        Returns:
            安全区域字典
        """
        return {
            "top": self.screen_size.safe_area_top,
            "bottom": self.screen_size.safe_area_bottom,
            "left": self.screen_size.safe_area_left,
            "right": self.screen_size.safe_area_right
        }
    
    def get_layout_constraints(self) -> Dict[str, Any]:
        """
        获取布局约束
        
        Returns:
            布局约束字典
        """
        safe_area = self.get_safe_area_insets()
        
        return {
            "screen_width": self.screen_size.width,
            "screen_height": self.screen_size.height,
            "available_width": self.screen_size.width - safe_area["left"] - safe_area["right"],
            "available_height": self.screen_size.height - safe_area["top"] - safe_area["bottom"],
            "safe_area": safe_area,
            "orientation": self.current_orientation.value,
            "device_type": self.device_type.value
        }
    
    def create_animation(self, animation_id: str, properties: Dict[str, Any]) -> bool:
        """
        创建动画
        
        Args:
            animation_id: 动画ID
            properties: 动画属性
        
        Returns:
            是否成功
        """
        if not self.config.enable_animations:
            logger.warning("Animations are disabled")
            return False
        
        self._animations[animation_id] = {
            "properties": properties,
            "created_at": time.time(),
            "status": "created"
        }
        
        logger.debug(f"Animation created: {animation_id}")
        return True
    
    def start_animation(self, animation_id: str) -> bool:
        """
        开始动画
        
        Args:
            animation_id: 动画ID
        
        Returns:
            是否成功
        """
        if animation_id not in self._animations:
            logger.warning(f"Animation not found: {animation_id}")
            return False
        
        self._animations[animation_id]["status"] = "running"
        self._animations[animation_id]["started_at"] = time.time()
        
        # 触发事件
        self._trigger_event("animation_started", animation_id)
        
        logger.debug(f"Animation started: {animation_id}")
        return True
    
    def stop_animation(self, animation_id: str) -> bool:
        """
        停止动画
        
        Args:
            animation_id: 动画ID
        
        Returns:
            是否成功
        """
        if animation_id in self._animations:
            self._animations[animation_id]["status"] = "stopped"
            self._trigger_event("animation_stopped", animation_id)
            logger.debug(f"Animation stopped: {animation_id}")
            return True
        
        return False
    
    def register_event_handler(self, event: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        logger.debug(f"Event handler registered for {event}")
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """触发事件"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取UI状态
        
        Returns:
            状态字典
        """
        return {
            "screen": {
                "width": self.screen_size.width,
                "height": self.screen_size.height,
                "density": self.screen_size.density,
                "device_type": self.device_type.value
            },
            "theme": {
                "current": self.current_theme.value,
                "accent": self.config.accent_color
            },
            "orientation": self.current_orientation.value,
            "animations": {
                "enabled": self.config.enable_animations,
                "active": len([a for a in self._animations.values() if a["status"] == "running"])
            },
            "haptic_enabled": self.config.enable_haptic_feedback
        }
    
    def shutdown(self):
        """关闭UI管理器"""
        logger.info("Shutting down MobileUI...")
        
        # 停止所有动画
        for anim_id in list(self._animations.keys()):
            self.stop_animation(anim_id)
        
        # 保存配置
        self._save_config()
        
        logger.info("MobileUI shutdown completed")

# 单例模式实现
_mobile_ui_instance: Optional[MobileUI] = None

def get_mobile_ui(config: Optional[MobileUIConfig] = None) -> MobileUI:
    """
    获取移动UI单例
    
    Args:
        config: UI配置
    
    Returns:
        移动UI实例
    """
    global _mobile_ui_instance
    if _mobile_ui_instance is None:
        _mobile_ui_instance = MobileUI(config)
    return _mobile_ui_instance

