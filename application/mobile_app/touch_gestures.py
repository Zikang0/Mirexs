"""
触摸手势模块 - Mirexs移动应用程序

提供触摸手势识别和处理功能，包括：
1. 基本手势识别（点击、长按、滑动）
2. 多指手势识别（双指缩放、旋转）
3. 手势冲突处理
4. 手势事件分发
5. 触觉反馈
"""

import logging
import math
import time
from typing import Optional, Dict, Any, List, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

class GestureType(Enum):
    """手势类型枚举"""
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    PAN = "pan"
    PINCH = "pinch"
    ROTATE = "rotate"
    EDGE_SWIPE = "edge_swipe"
    FORCE_PRESS = "force_press"  # 3D Touch
    CUSTOM = "custom"

class GestureState(Enum):
    """手势状态枚举"""
    POSSIBLE = "possible"
    BEGAN = "began"
    CHANGED = "changed"
    ENDED = "ended"
    CANCELLED = "cancelled"
    FAILED = "failed"

class SwipeDirection(Enum):
    """滑动方向枚举"""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"

@dataclass
class TouchPoint:
    """触摸点信息"""
    id: int
    x: float
    y: float
    force: float = 0.0  # 压力值 (0-1)
    timestamp: float = field(default_factory=time.time)
    
    def distance_to(self, other: 'TouchPoint') -> float:
        """计算到另一个触摸点的距离"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def velocity_to(self, other: 'TouchPoint') -> Tuple[float, float]:
        """计算到另一个触摸点的速度（像素/秒）"""
        dt = other.timestamp - self.timestamp
        if dt <= 0:
            return (0, 0)
        return ((other.x - self.x) / dt, (other.y - self.y) / dt)

@dataclass
class GestureEvent:
    """手势事件"""
    type: GestureType
    state: GestureState
    location: Tuple[float, float]  # 手势中心点
    translation: Tuple[float, float] = (0, 0)  # 移动偏移
    velocity: Tuple[float, float] = (0, 0)  # 移动速度
    scale: float = 1.0  # 缩放比例
    rotation: float = 0.0  # 旋转角度
    direction: Optional[SwipeDirection] = None  # 滑动方向
    touch_count: int = 1  # 触摸点数
    force: float = 0.0  # 平均压力
    target_id: Optional[str] = None  # 目标元素ID
    timestamp: float = field(default_factory=time.time)

@dataclass
class GestureConfig:
    """手势配置"""
    # 点击相关
    tap_max_duration: float = 0.3  # 秒
    tap_max_movement: float = 10  # 像素
    
    # 双击相关
    double_tap_max_interval: float = 0.3  # 秒
    
    # 长按相关
    long_press_min_duration: float = 0.5  # 秒
    
    # 滑动相关
    swipe_min_distance: float = 50  # 像素
    swipe_min_velocity: float = 100  # 像素/秒
    
    # 缩放手势
    pinch_min_scale_change: float = 0.1
    
    # 旋转手势
    rotate_min_angle_change: float = 5  # 度
    
    # 多点触摸
    max_touch_points: int = 5
    
    # 冲突检测
    gesture_recognition_timeout: float = 0.5  # 秒

class TouchGestures:
    """
    触摸手势识别器
    
    负责识别和处理各种触摸手势，包括：
    - 单指手势（点击、长按、滑动）
    - 多指手势（缩放、旋转）
    - 边缘手势
    - 手势冲突解决
    """
    
    def __init__(self, config: Optional[GestureConfig] = None):
        """
        初始化触摸手势识别器
        
        Args:
            config: 手势配置
        """
        self.config = config or GestureConfig()
        
        # 当前触摸点
        self.active_touches: Dict[int, TouchPoint] = {}
        self.touch_history: Dict[int, deque] = {}  # 触摸历史，用于计算速度
        
        # 手势状态
        self.current_gestures: Dict[GestureType, GestureState] = {}
        self.recognized_gesture: Optional[GestureEvent] = None
        
        # 手势回调
        self.gesture_handlers: Dict[GestureType, List[Callable[[GestureEvent], None]]] = {}
        
        # 手势排除（用于冲突解决）
        self.exclusive_gestures: List[GestureType] = [GestureType.PAN, GestureType.PINCH]
        
        # 手势开始时间
        self.gesture_start_time: Optional[float] = None
        
        # 手势起始点
        self.gesture_start_points: List[TouchPoint] = []
        
        logger.info("TouchGestures initialized")
    
    def handle_touch_began(self, touch_id: int, x: float, y: float, force: float = 0.0):
        """
        处理触摸开始事件
        
        Args:
            touch_id: 触摸ID
            x: X坐标
            y: Y坐标
            force: 压力值
        """
        if len(self.active_touches) >= self.config.max_touch_points:
            logger.warning(f"Max touch points reached ({self.config.max_touch_points})")
            return
        
        touch = TouchPoint(
            id=touch_id,
            x=x,
            y=y,
            force=force,
            timestamp=time.time()
        )
        
        self.active_touches[touch_id] = touch
        self.touch_history[touch_id] = deque(maxlen=10)
        self.touch_history[touch_id].append(touch)
        
        # 如果是第一个触摸点，记录手势开始
        if len(self.active_touches) == 1:
            self.gesture_start_time = touch.timestamp
            self.gesture_start_points = [touch]
        
        logger.debug(f"Touch began: id={touch_id}, ({x}, {y})")
        
        # 评估可能的手势
        self._evaluate_possible_gestures()
    
    def handle_touch_moved(self, touch_id: int, x: float, y: float, force: float = 0.0):
        """
        处理触摸移动事件
        
        Args:
            touch_id: 触摸ID
            x: X坐标
            y: Y坐标
            force: 压力值
        """
        if touch_id not in self.active_touches:
            return
        
        previous = self.active_touches[touch_id]
        touch = TouchPoint(
            id=touch_id,
            x=x,
            y=y,
            force=force,
            timestamp=time.time()
        )
        
        self.active_touches[touch_id] = touch
        if touch_id in self.touch_history:
            self.touch_history[touch_id].append(touch)
        
        # 计算移动距离
        distance = previous.distance_to(touch)
        logger.debug(f"Touch moved: id={touch_id}, distance={distance:.1f}")
        
        # 评估活动手势
        self._update_active_gestures()
    
    def handle_touch_ended(self, touch_id: int, x: float, y: float):
        """
        处理触摸结束事件
        
        Args:
            touch_id: 触摸ID
            x: X坐标
            y: Y坐标
        """
        if touch_id not in self.active_touches:
            return
        
        # 记录最后一个点
        end_touch = TouchPoint(
            id=touch_id,
            x=x,
            y=y,
            timestamp=time.time()
        )
        
        if touch_id in self.touch_history:
            self.touch_history[touch_id].append(end_touch)
        
        # 移除激活的触摸点
        del self.active_touches[touch_id]
        
        logger.debug(f"Touch ended: id={touch_id}, active_touches={len(self.active_touches)}")
        
        # 如果所有触摸都结束了，识别手势
        if len(self.active_touches) == 0:
            self._recognize_gesture()
            self._clear_state()
    
    def handle_touch_cancelled(self, touch_id: int):
        """
        处理触摸取消事件
        
        Args:
            touch_id: 触摸ID
        """
        if touch_id in self.active_touches:
            del self.active_touches[touch_id]
        
        if touch_id in self.touch_history:
            del self.touch_history[touch_id]
        
        logger.debug(f"Touch cancelled: id={touch_id}")
        
        # 取消当前手势
        if self.recognized_gesture:
            self.recognized_gesture.state = GestureState.CANCELLED
            self._dispatch_gesture(self.recognized_gesture)
            self.recognized_gesture = None
    
    def _evaluate_possible_gestures(self):
        """评估可能的手势"""
        touch_count = len(self.active_touches)
        
        # 根据触摸点数判断可能的手势
        if touch_count == 1:
            # 单指手势
            self._evaluate_single_touch_gestures()
        elif touch_count == 2:
            # 双指手势
            self._evaluate_two_finger_gestures()
    
    def _evaluate_single_touch_gestures(self):
        """评估单指手势"""
        touch = next(iter(self.active_touches.values()))
        
        # 检查是否是边缘滑动
        if self._is_edge_swipe(touch):
            self._set_gesture_possible(GestureType.EDGE_SWIPE)
        
        # 检查是否是长按
        if self.gesture_start_time and (time.time() - self.gesture_start_time) > self.config.long_press_min_duration:
            # 检查移动距离
            start_touch = self.gesture_start_points[0]
            if start_touch.distance_to(touch) < self.config.tap_max_movement:
                self._set_gesture_possible(GestureType.LONG_PRESS)
    
    def _evaluate_two_finger_gestures(self):
        """评估双指手势"""
        touches = list(self.active_touches.values())
        if len(touches) < 2:
            return
        
        touch1, touch2 = touches[0], touches[1]
        
        # 检查是否是缩放手势
        self._set_gesture_possible(GestureType.PINCH)
        
        # 检查是否是旋转手势
        self._set_gesture_possible(GestureType.ROTATE)
    
    def _set_gesture_possible(self, gesture_type: GestureType):
        """设置手势为可能状态"""
        if gesture_type not in self.current_gestures:
            self.current_gestures[gesture_type] = GestureState.POSSIBLE
            logger.debug(f"Gesture possible: {gesture_type.value}")
    
    def _update_active_gestures(self):
        """更新活动手势"""
        if not self.recognized_gesture:
            # 还没有识别出手势，检查是否应该开始某个手势
            self._try_begin_gesture()
        else:
            # 已有识别出的手势，更新它
            self._update_recognized_gesture()
    
    def _try_begin_gesture(self):
        """尝试开始手势"""
        # 按优先级检查手势
        touch_count = len(self.active_touches)
        
        if touch_count == 2:
            # 优先检查双指手势
            if self._should_begin_pinch():
                self._begin_gesture(GestureType.PINCH)
            elif self._should_begin_rotate():
                self._begin_gesture(GestureType.ROTATE)
        
        elif touch_count == 1:
            # 检查单指手势
            if self._should_begin_pan():
                self._begin_gesture(GestureType.PAN)
            elif self._should_begin_edge_swipe():
                self._begin_gesture(GestureType.EDGE_SWIPE)
    
    def _should_begin_pan(self) -> bool:
        """是否应该开始平移手势"""
        if len(self.active_touches) != 1 or not self.gesture_start_points:
            return False
        
        current_touch = next(iter(self.active_touches.values()))
        start_touch = self.gesture_start_points[0]
        
        # 如果移动距离超过点击阈值，开始平移
        distance = start_touch.distance_to(current_touch)
        return distance > self.config.tap_max_movement
    
    def _should_begin_pinch(self) -> bool:
        """是否应该开始缩放手势"""
        if len(self.active_touches) != 2:
            return False
        
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        # 检查是否有初始距离
        if len(self.gesture_start_points) >= 2:
            start1, start2 = self.gesture_start_points[0], self.gesture_start_points[1]
            start_distance = start1.distance_to(start2)
            current_distance = touch1.distance_to(touch2)
            
            # 如果距离变化超过阈值，开始缩放
            return abs(current_distance - start_distance) > self.config.pinch_min_scale_change * start_distance
        
        return False
    
    def _should_begin_rotate(self) -> bool:
        """是否应该开始旋转手势"""
        if len(self.active_touches) != 2:
            return False
        
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        # 计算角度变化
        if len(self.gesture_start_points) >= 2:
            start1, start2 = self.gesture_start_points[0], self.gesture_start_points[1]
            start_angle = math.degrees(math.atan2(start2.y - start1.y, start2.x - start1.x))
            current_angle = math.degrees(math.atan2(touch2.y - touch1.y, touch2.x - touch1.x))
            
            angle_diff = abs(current_angle - start_angle)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            return angle_diff > self.config.rotate_min_angle_change
        
        return False
    
    def _should_begin_edge_swipe(self) -> bool:
        """是否应该开始边缘滑动"""
        if len(self.active_touches) != 1:
            return False
        
        touch = next(iter(self.active_touches.values()))
        return self._is_edge_swipe(touch)
    
    def _is_edge_swipe(self, touch: TouchPoint) -> bool:
        """检查是否是边缘触摸"""
        # 检查是否在屏幕边缘（假设屏幕尺寸从外部传入）
        edge_threshold = 50  # 像素
        return (touch.x < edge_threshold or 
                touch.y < edge_threshold or 
                touch.x > (self.screen_width - edge_threshold) if hasattr(self, 'screen_width') else False)
    
    def _begin_gesture(self, gesture_type: GestureType):
        """开始手势"""
        if self.recognized_gesture:
            return
        
        gesture = GestureEvent(
            type=gesture_type,
            state=GestureState.BEGAN,
            location=self._get_gesture_center(),
            touch_count=len(self.active_touches),
            timestamp=time.time()
        )
        
        self.recognized_gesture = gesture
        
        # 取消其他可能的手势
        self.current_gestures.clear()
        
        logger.info(f"Gesture began: {gesture_type.value}")
        
        # 分发手势开始事件
        self._dispatch_gesture(gesture)
    
    def _update_recognized_gesture(self):
        """更新已识别的手势"""
        if not self.recognized_gesture:
            return
        
        gesture = self.recognized_gesture
        gesture.state = GestureState.CHANGED
        gesture.location = self._get_gesture_center()
        gesture.timestamp = time.time()
        
        # 根据手势类型更新特定属性
        if gesture.type == GestureType.PAN:
            self._update_pan_gesture(gesture)
        elif gesture.type == GestureType.PINCH:
            self._update_pinch_gesture(gesture)
        elif gesture.type == GestureType.ROTATE:
            self._update_rotate_gesture(gesture)
        
        # 分发手势更新事件
        self._dispatch_gesture(gesture)
    
    def _update_pan_gesture(self, gesture: GestureEvent):
        """更新平移手势"""
        if len(self.active_touches) != 1 or not self.gesture_start_points:
            return
        
        current_touch = next(iter(self.active_touches.values()))
        start_touch = self.gesture_start_points[0]
        
        # 计算偏移
        gesture.translation = (
            current_touch.x - start_touch.x,
            current_touch.y - start_touch.y
        )
        
        # 计算速度
        if len(self.touch_history[current_touch.id]) >= 2:
            prev = list(self.touch_history[current_touch.id])[-2]
            velocity = prev.velocity_to(current_touch)
            gesture.velocity = velocity
    
    def _update_pinch_gesture(self, gesture: GestureEvent):
        """更新缩放手势"""
        if len(self.active_touches) != 2 or len(self.gesture_start_points) < 2:
            return
        
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        start1, start2 = self.gesture_start_points[0], self.gesture_start_points[1]
        
        # 计算缩放比例
        start_distance = start1.distance_to(start2)
        current_distance = touch1.distance_to(touch2)
        
        if start_distance > 0:
            gesture.scale = current_distance / start_distance
    
    def _update_rotate_gesture(self, gesture: GestureEvent):
        """更新旋转手势"""
        if len(self.active_touches) != 2 or len(self.gesture_start_points) < 2:
            return
        
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        start1, start2 = self.gesture_start_points[0], self.gesture_start_points[1]
        
        # 计算旋转角度
        start_angle = math.degrees(math.atan2(start2.y - start1.y, start2.x - start1.x))
        current_angle = math.degrees(math.atan2(touch2.y - touch1.y, touch2.x - touch1.x))
        
        gesture.rotation = current_angle - start_angle
    
    def _get_gesture_center(self) -> Tuple[float, float]:
        """获取手势中心点"""
        if not self.active_touches:
            return (0, 0)
        
        touches = list(self.active_touches.values())
        if len(touches) == 1:
            return (touches[0].x, touches[0].y)
        
        # 多指手势的中心点是所有触摸点的平均位置
        x = sum(t.x for t in touches) / len(touches)
        y = sum(t.y for t in touches) / len(touches)
        return (x, y)
    
    def _recognize_gesture(self):
        """识别最终手势（当所有触摸结束时）"""
        if not self.recognized_gesture:
            # 没有识别出连续手势，检查点击类手势
            self._recognize_tap_gestures()
            return
        
        # 结束当前手势
        gesture = self.recognized_gesture
        gesture.state = GestureState.ENDED
        gesture.timestamp = time.time()
        
        self._dispatch_gesture(gesture)
        logger.info(f"Gesture ended: {gesture.type.value}")
    
    def _recognize_tap_gestures(self):
        """识别点击类手势"""
        if not self.gesture_start_points:
            return
        
        # 检查是否是双击
        if hasattr(self, '_last_tap_time') and self._last_tap_time:
            if time.time() - self._last_tap_time < self.config.double_tap_max_interval:
                self._create_and_dispatch_tap_gesture(GestureType.DOUBLE_TAP)
                self._last_tap_time = None
                return
        
        # 检查是否是长按
        touch_duration = time.time() - self.gesture_start_time
        if touch_duration >= self.config.long_press_min_duration:
            # 检查移动距离
            start_touch = self.gesture_start_points[0]
            if len(self.touch_history.get(start_touch.id, [])) > 0:
                last_touch = list(self.touch_history[start_touch.id])[-1]
                if start_touch.distance_to(last_touch) < self.config.tap_max_movement:
                    self._create_and_dispatch_tap_gesture(GestureType.LONG_PRESS)
                    return
        
        # 检查是否是普通点击
        if touch_duration <= self.config.tap_max_duration:
            start_touch = self.gesture_start_points[0]
            if len(self.touch_history.get(start_touch.id, [])) > 0:
                last_touch = list(self.touch_history[start_touch.id])[-1]
                if start_touch.distance_to(last_touch) < self.config.tap_max_movement:
                    self._create_and_dispatch_tap_gesture(GestureType.TAP)
                    self._last_tap_time = time.time()
                    return
    
    def _create_and_dispatch_tap_gesture(self, gesture_type: GestureType):
        """创建并分发点击手势"""
        location = self._get_gesture_center()
        
        gesture = GestureEvent(
            type=gesture_type,
            state=GestureState.ENDED,
            location=location,
            touch_count=1,
            timestamp=time.time()
        )
        
        logger.info(f"Tap gesture recognized: {gesture_type.value}")
        self._dispatch_gesture(gesture)
    
    def _dispatch_gesture(self, gesture: GestureEvent):
        """
        分发手势事件
        
        Args:
            gesture: 手势事件
        """
        if gesture.type in self.gesture_handlers:
            for handler in self.gesture_handlers[gesture.type]:
                try:
                    handler(gesture)
                except Exception as e:
                    logger.error(f"Error in gesture handler for {gesture.type}: {e}")
    
    def _clear_state(self):
        """清除状态"""
        self.active_touches.clear()
        self.touch_history.clear()
        self.current_gestures.clear()
        self.recognized_gesture = None
        self.gesture_start_time = None
        self.gesture_start_points.clear()
    
    def set_screen_dimensions(self, width: int, height: int):
        """
        设置屏幕尺寸（用于边缘检测）
        
        Args:
            width: 屏幕宽度
            height: 屏幕高度
        """
        self.screen_width = width
        self.screen_height = height
    
    def register_gesture_handler(self, gesture_type: GestureType, handler: Callable[[GestureEvent], None]):
        """
        注册手势处理器
        
        Args:
            gesture_type: 手势类型
            handler: 处理函数
        """
        if gesture_type not in self.gesture_handlers:
            self.gesture_handlers[gesture_type] = []
        self.gesture_handlers[gesture_type].append(handler)
        logger.debug(f"Gesture handler registered for {gesture_type.value}")
    
    def unregister_gesture_handler(self, gesture_type: GestureType, handler: Callable):
        """
        注销手势处理器
        
        Args:
            gesture_type: 手势类型
            handler: 处理函数
        """
        if gesture_type in self.gesture_handlers and handler in self.gesture_handlers[gesture_type]:
            self.gesture_handlers[gesture_type].remove(handler)
            logger.debug(f"Gesture handler unregistered for {gesture_type.value}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取手势识别器状态
        
        Returns:
            状态字典
        """
        return {
            "active_touches": len(self.active_touches),
            "recognized_gesture": self.recognized_gesture.type.value if self.recognized_gesture else None,
            "possible_gestures": [g.value for g in self.current_gestures.keys()],
            "touch_history_size": sum(len(h) for h in self.touch_history.values())
        }

# 单例模式实现
_touch_gestures_instance: Optional[TouchGestures] = None

def get_touch_gestures(config: Optional[GestureConfig] = None) -> TouchGestures:
    """
    获取触摸手势识别器单例
    
    Args:
        config: 手势配置
    
    Returns:
        触摸手势识别器实例
    """
    global _touch_gestures_instance
    if _touch_gestures_instance is None:
        _touch_gestures_instance = TouchGestures(config)
    return _touch_gestures_instance

