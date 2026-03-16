"""
响应式设计模块 - Mirexs Web界面

提供响应式布局功能，包括：
1. 断点管理
2. 媒体查询
3. 视口检测
4. 自适应布局
5. 设备类型检测
6. 方向变化处理
"""

import logging
import time
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class Breakpoint(Enum):
    """断点枚举"""
    XS = "xs"  # < 576px
    SM = "sm"  # ≥ 576px
    MD = "md"  # ≥ 768px
    LG = "lg"  # ≥ 992px
    XL = "xl"  # ≥ 1200px
    XXL = "xxl"  # ≥ 1400px

class DeviceType(Enum):
    """设备类型枚举"""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    TV = "tv"
    WATCH = "watch"

class Orientation(Enum):
    """屏幕方向枚举"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

@dataclass
class Viewport:
    """视口信息"""
    width: int = 0
    height: int = 0
    pixel_ratio: float = 1.0
    orientation: Orientation = Orientation.PORTRAIT
    breakpoint: Breakpoint = Breakpoint.XS
    device_type: DeviceType = DeviceType.DESKTOP

@dataclass
class ResponsiveConfig:
    """响应式设计配置"""
    # 断点阈值
    breakpoints: Dict[Breakpoint, int] = field(default_factory=lambda: {
        Breakpoint.XS: 0,
        Breakpoint.SM: 576,
        Breakpoint.MD: 768,
        Breakpoint.LG: 992,
        Breakpoint.XL: 1200,
        Breakpoint.XXL: 1400
    })
    
    # 设备检测阈值
    mobile_max_width: int = 768
    tablet_max_width: int = 992
    
    # 监听配置
    debounce_delay: int = 150  # 毫秒
    observe_orientation: bool = True
    
    # 默认值
    default_width: int = 1920
    default_height: int = 1080

class ResponsiveDesign:
    """
    响应式设计管理器
    
    负责响应式布局的管理，包括：
    - 视口检测
    - 断点管理
    - 设备类型识别
    - 布局适配
    - 事件监听
    """
    
    def __init__(self, config: Optional[ResponsiveConfig] = None):
        """
        初始化响应式设计管理器
        
        Args:
            config: 响应式配置
        """
        self.config = config or ResponsiveConfig()
        
        # 当前视口
        self.viewport = Viewport(
            width=self.config.default_width,
            height=self.config.default_height,
            pixel_ratio=1.0,
            orientation=Orientation.LANDSCAPE if self.config.default_width > self.config.default_height else Orientation.PORTRAIT,
            breakpoint=self._calculate_breakpoint(self.config.default_width),
            device_type=self._calculate_device_type(self.config.default_width)
        )
        
        # 监听器
        self._resize_listeners: List[Callable[[Viewport], None]] = []
        self._orientation_listeners: List[Callable[[Orientation], None]] = []
        self._breakpoint_listeners: List[Callable[[Breakpoint], None]] = []
        
        # 防抖计时器
        self._resize_timeout: Optional[float] = None
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        logger.info("ResponsiveDesign initialized")
    
    def _calculate_breakpoint(self, width: int) -> Breakpoint:
        """根据宽度计算断点"""
        for breakpoint, threshold in sorted(
            self.config.breakpoints.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if width >= threshold:
                return breakpoint
        return Breakpoint.XS
    
    def _calculate_device_type(self, width: int) -> DeviceType:
        """根据宽度计算设备类型"""
        if width <= self.config.mobile_max_width:
            return DeviceType.MOBILE
        elif width <= self.config.tablet_max_width:
            return DeviceType.TABLET
        else:
            return DeviceType.DESKTOP
    
    def update_viewport(self, width: int, height: int, pixel_ratio: float = 1.0):
        """
        更新视口信息
        
        Args:
            width: 宽度
            height: 高度
            pixel_ratio: 像素比
        """
        old_viewport = self.viewport
        
        # 计算方向
        orientation = Orientation.LANDSCAPE if width > height else Orientation.PORTRAIT
        
        # 计算断点
        breakpoint = self._calculate_breakpoint(width)
        
        # 计算设备类型
        device_type = self._calculate_device_type(width)
        
        self.viewport = Viewport(
            width=width,
            height=height,
            pixel_ratio=pixel_ratio,
            orientation=orientation,
            breakpoint=breakpoint,
            device_type=device_type
        )
        
        # 记录变化
        changes = []
        if old_viewport.breakpoint != breakpoint:
            changes.append(f"breakpoint: {old_viewport.breakpoint.value} -> {breakpoint.value}")
            self._notify_breakpoint_listeners(breakpoint)
        
        if old_viewport.orientation != orientation and self.config.observe_orientation:
            changes.append(f"orientation: {old_viewport.orientation.value} -> {orientation.value}")
            self._notify_orientation_listeners(orientation)
        
        if old_viewport.device_type != device_type:
            changes.append(f"device: {old_viewport.device_type.value} -> {device_type.value}")
        
        if changes:
            logger.debug(f"Viewport updated: {', '.join(changes)}")
        
        # 添加到历史
        self._add_to_history()
        
        # 通知所有监听器
        self._notify_resize_listeners(self.viewport)
    
    def handle_resize(self, width: int, height: int):
        """
        处理窗口大小变化
        
        Args:
            width: 新宽度
            height: 新高度
        """
        # 防抖处理
        current_time = time.time()
        
        if self._resize_timeout:
            # 取消之前的防抖
            pass
        
        self._resize_timeout = current_time
        
        def debounced_update():
            if self._resize_timeout == current_time:
                self.update_viewport(width, height)
        
        # 设置防抖定时器
        import threading
        timer = threading.Timer(self.config.debounce_delay / 1000, debounced_update)
        timer.daemon = True
        timer.start()
    
    def _add_to_history(self):
        """添加到历史记录"""
        self.history.append({
            "timestamp": time.time(),
            "viewport": {
                "width": self.viewport.width,
                "height": self.viewport.height,
                "breakpoint": self.viewport.breakpoint.value,
                "orientation": self.viewport.orientation.value,
                "device_type": self.viewport.device_type.value
            }
        })
        
        # 限制历史大小
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def _notify_resize_listeners(self, viewport: Viewport):
        """通知大小变化监听器"""
        for listener in self._resize_listeners:
            try:
                listener(viewport)
            except Exception as e:
                logger.error(f"Error in resize listener: {e}")
    
    def _notify_orientation_listeners(self, orientation: Orientation):
        """通知方向变化监听器"""
        for listener in self._orientation_listeners:
            try:
                listener(orientation)
            except Exception as e:
                logger.error(f"Error in orientation listener: {e}")
    
    def _notify_breakpoint_listeners(self, breakpoint: Breakpoint):
        """通知断点变化监听器"""
        for listener in self._breakpoint_listeners:
            try:
                listener(breakpoint)
            except Exception as e:
                logger.error(f"Error in breakpoint listener: {e}")
    
    def on_resize(self, listener: Callable[[Viewport], None]):
        """
        注册大小变化监听器
        
        Args:
            listener: 监听函数
        """
        self._resize_listeners.append(listener)
    
    def on_orientation_change(self, listener: Callable[[Orientation], None]):
        """
        注册方向变化监听器
        
        Args:
            listener: 监听函数
        """
        self._orientation_listeners.append(listener)
    
    def on_breakpoint_change(self, listener: Callable[[Breakpoint], None]):
        """
        注册断点变化监听器
        
        Args:
            listener: 监听函数
        """
        self._breakpoint_listeners.append(listener)
    
    def is_mobile(self) -> bool:
        """是否移动设备"""
        return self.viewport.device_type == DeviceType.MOBILE
    
    def is_tablet(self) -> bool:
        """是否平板"""
        return self.viewport.device_type == DeviceType.TABLET
    
    def is_desktop(self) -> bool:
        """是否桌面设备"""
        return self.viewport.device_type == DeviceType.DESKTOP
    
    def is_portrait(self) -> bool:
        """是否竖屏"""
        return self.viewport.orientation == Orientation.PORTRAIT
    
    def is_landscape(self) -> bool:
        """是否横屏"""
        return self.viewport.orientation == Orientation.LANDSCAPE
    
    def greater_than(self, breakpoint: Breakpoint) -> bool:
        """
        判断当前断点是否大于指定断点
        
        Args:
            breakpoint: 比较的断点
        
        Returns:
            是否大于
        """
        current_value = self.config.breakpoints.get(self.viewport.breakpoint, 0)
        compare_value = self.config.breakpoints.get(breakpoint, 0)
        return current_value >= compare_value
    
    def less_than(self, breakpoint: Breakpoint) -> bool:
        """
        判断当前断点是否小于指定断点
        
        Args:
            breakpoint: 比较的断点
        
        Returns:
            是否小于
        """
        current_value = self.config.breakpoints.get(self.viewport.breakpoint, 0)
        compare_value = self.config.breakpoints.get(breakpoint, 0)
        return current_value < compare_value
    
    def between(self, min_breakpoint: Breakpoint, max_breakpoint: Breakpoint) -> bool:
        """
        判断当前断点是否在两个断点之间
        
        Args:
            min_breakpoint: 最小断点
            max_breakpoint: 最大断点
        
        Returns:
            是否在之间
        """
        current_value = self.config.breakpoints.get(self.viewport.breakpoint, 0)
        min_value = self.config.breakpoints.get(min_breakpoint, 0)
        max_value = self.config.breakpoints.get(max_breakpoint, 0)
        return min_value <= current_value < max_value
    
    def get_responsive_value(self, values: Dict[Breakpoint, Any]) -> Any:
        """
        根据当前断点获取响应式值
        
        Args:
            values: 各断点的值字典
        
        Returns:
            对应的值
        """
        current_breakpoint = self.viewport.breakpoint
        
        # 找到最合适的值
        for breakpoint in [Breakpoint.XXL, Breakpoint.XL, Breakpoint.LG, 
                          Breakpoint.MD, Breakpoint.SM, Breakpoint.XS]:
            if breakpoint in values:
                if self.greater_than(breakpoint):
                    return values[breakpoint]
        
        # 返回默认值
        return values.get(Breakpoint.XS)
    
    def get_layout_props(self) -> Dict[str, Any]:
        """
        获取布局属性
        
        Returns:
            布局属性字典
        """
        return {
            "isMobile": self.is_mobile(),
            "isTablet": self.is_tablet(),
            "isDesktop": self.is_desktop(),
            "isPortrait": self.is_portrait(),
            "isLandscape": self.is_landscape(),
            "breakpoint": self.viewport.breakpoint.value,
            "deviceType": self.viewport.device_type.value,
            "width": self.viewport.width,
            "height": self.viewport.height,
            "pixelRatio": self.viewport.pixel_ratio
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取响应式设计管理器状态
        
        Returns:
            状态字典
        """
        return {
            "viewport": {
                "width": self.viewport.width,
                "height": self.viewport.height,
                "pixel_ratio": self.viewport.pixel_ratio,
                "orientation": self.viewport.orientation.value,
                "breakpoint": self.viewport.breakpoint.value,
                "device_type": self.viewport.device_type.value
            },
            "config": {
                "breakpoints": {k.value: v for k, v in self.config.breakpoints.items()},
                "debounce_delay": self.config.debounce_delay
            },
            "history_size": len(self.history),
            "listeners": {
                "resize": len(self._resize_listeners),
                "orientation": len(self._orientation_listeners),
                "breakpoint": len(self._breakpoint_listeners)
            }
        }
    
    def shutdown(self):
        """关闭响应式设计管理器"""
        logger.info("Shutting down ResponsiveDesign...")
        
        self._resize_listeners.clear()
        self._orientation_listeners.clear()
        self._breakpoint_listeners.clear()
        self.history.clear()
        
        logger.info("ResponsiveDesign shutdown completed")

# 单例模式实现
_responsive_design_instance: Optional[ResponsiveDesign] = None

def get_responsive_design(config: Optional[ResponsiveConfig] = None) -> ResponsiveDesign:
    """
    获取响应式设计管理器单例
    
    Args:
        config: 响应式配置
    
    Returns:
        响应式设计管理器实例
    """
    global _responsive_design_instance
    if _responsive_design_instance is None:
        _responsive_design_instance = ResponsiveDesign(config)
    return _responsive_design_instance

