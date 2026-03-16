"""
视线系统：控制视线方向和焦点
负责3D虚拟猫咪的视线跟踪、焦点管理和眼动控制
"""

import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio
import random

class GazeTargetType(Enum):
    """视线目标类型"""
    USER = "user"  # 用户
    OBJECT = "object"  # 物体
    POINT = "point"  # 空间点
    RANDOM = "random"  # 随机
    FOLLOW = "follow"  # 跟随

class GazeBehavior(Enum):
    """视线行为模式"""
    DIRECT = "direct"  # 直接注视
    GLANCING = "glancing"  # 扫视
    AVOIDING = "avoiding"  # 回避
    TRACKING = "tracking"  # 跟踪
    EXPLORING = "exploring"  # 探索
    THINKING = "thinking"  # 思考

@dataclass
class GazeTarget:
    """视线目标"""
    target_id: str
    target_type: GazeTargetType
    position: Tuple[float, float, float]  # 3D位置
    importance: float  # 重要性 0.0-1.0
    duration: float  # 建议注视时长
    movement_speed: float  # 移动速度

@dataclass
class GazeState:
    """视线状态"""
    current_target: Optional[GazeTarget]
    gaze_direction: Tuple[float, float, float]  # 视线方向向量
    focus_intensity: float  # 专注强度 0.0-1.0
    behavior_mode: GazeBehavior
    blink_rate: float  # 眨眼频率（每秒）
    last_blink_time: float  # 上次眨眼时间

class GazeSystem:
    """视线系统：控制视线方向和焦点"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 视线状态
        self.current_gaze_state = GazeState(
            current_target=None,
            gaze_direction=(0, 0, 1),  # 默认向前看
            focus_intensity=0.5,
            behavior_mode=GazeBehavior.DIRECT,
            blink_rate=0.2,  # 默认眨眼频率
            last_blink_time=0.0
        )
        
        # 视线目标管理
        self.available_targets: Dict[str, GazeTarget] = {}
        self.target_priorities: Dict[str, float] = {}
        
        # 眼动参数
        self.eye_movement_params = {
            "saccade_speed": 5.0,  # 扫视速度
            "smooth_pursuit_speed": 2.0,  # 平滑追随速度
            "max_eye_angle": 30.0,  # 最大眼球转动角度
            "min_focus_duration": 0.5,  # 最小注视时长
            "max_focus_duration": 3.0,  # 最大注视时长
            "blink_duration": 0.1  # 眨眼持续时间
        }
        
        # 视线历史
        self.gaze_history: List[Tuple[float, GazeTarget, GazeBehavior]] = []  # (时间, 目标, 行为)
        
        # 情感影响参数
        self.emotional_influence = {
            "happy": {"blink_rate": 0.3, "exploration_rate": 0.7},
            "sad": {"blink_rate": 0.1, "exploration_rate": 0.2},
            "angry": {"blink_rate": 0.4, "exploration_rate": 0.3},
            "surprised": {"blink_rate": 0.5, "exploration_rate": 0.8},
            "neutral": {"blink_rate": 0.2, "exploration_rate": 0.5}
        }
        
        # 内部状态
        self.current_emotion = "neutral"
        self.is_blinking = False
        self.blink_start_time = 0.0
        self.last_gaze_update = 0.0
        
        self.logger.info("视线系统初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("GazeSystem")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def add_gaze_target(self, target: GazeTarget) -> bool:
        """
        添加视线目标
        
        Args:
            target: 视线目标
            
        Returns:
            是否添加成功
        """
        try:
            self.available_targets[target.target_id] = target
            self.target_priorities[target.target_id] = target.importance
            
            self.logger.info(f"视线目标添加成功: {target.target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加视线目标失败: {e}")
            return False
    
    def remove_gaze_target(self, target_id: str) -> bool:
        """
        移除视线目标
        
        Args:
            target_id: 目标ID
            
        Returns:
            是否移除成功
        """
        if target_id not in self.available_targets:
            return False
        
        try:
            del self.available_targets[target_id]
            if target_id in self.target_priorities:
                del self.target_priorities[target_id]
            
            # 如果移除的是当前目标，选择新目标
            if (self.current_gaze_state.current_target and 
                self.current_gaze_state.current_target.target_id == target_id):
                self._select_new_target()
            
            self.logger.info(f"视线目标移除成功: {target_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"移除视线目标失败: {e}")
            return False
    
    def set_primary_target(self, target_id: str) -> bool:
        """
        设置主要视线目标
        
        Args:
            target_id: 目标ID
            
        Returns:
            是否设置成功
        """
        if target_id not in self.available_targets:
            self.logger.warning(f"视线目标不存在: {target_id}")
            return False
        
        target = self.available_targets[target_id]
        self.current_gaze_state.current_target = target
        
        # 更新视线方向
        self._update_gaze_direction(target.position)
        
        self.logger.info(f"主要视线目标设置为: {target_id}")
        return True
    
    def set_gaze_behavior(self, behavior: GazeBehavior, intensity: float = 0.5):
        """
        设置视线行为模式
        
        Args:
            behavior: 视线行为
            intensity: 行为强度
        """
        self.current_gaze_state.behavior_mode = behavior
        self.current_gaze_state.focus_intensity = intensity
        
        # 根据行为模式调整参数
        if behavior == GazeBehavior.GLANCING:
            self.eye_movement_params["saccade_speed"] = 8.0
        elif behavior == GazeBehavior.TRACKING:
            self.eye_movement_params["smooth_pursuit_speed"] = 1.5
        elif behavior == GazeBehavior.THINKING:
            self.eye_movement_params["saccade_speed"] = 3.0
        
        self.logger.info(f"视线行为模式设置为: {behavior.value}")
    
    def update_emotional_influence(self, emotion: str, intensity: float):
        """
        更新情感影响
        
        Args:
            emotion: 情感状态
            intensity: 情感强度
        """
        self.current_emotion = emotion
        
        if emotion in self.emotional_influence:
            influence = self.emotional_influence[emotion]
            
            # 调整眨眼频率
            base_blink_rate = influence["blink_rate"]
            self.current_gaze_state.blink_rate = base_blink_rate * (0.5 + intensity * 0.5)
            
            # 调整探索率
            exploration_rate = influence["exploration_rate"]
            if exploration_rate > 0.6 and random.random() < intensity:
                self.set_gaze_behavior(GazeBehavior.EXPLORING, intensity)
        
        self.logger.debug(f"情感影响更新: {emotion} (强度: {intensity})")
    
    async def update(self, delta_time: float, head_position: Tuple[float, float, float], 
                   head_rotation: Tuple[float, float, float, float]):
        """
        更新视线系统
        
        Args:
            delta_time: 时间增量
            head_position: 头部位置
            head_rotation: 头部旋转（四元数）
        """
        current_time = asyncio.get_event_loop().time()
        self.last_gaze_update = current_time
        
        # 处理眨眼
        await self._update_blinking(current_time, delta_time)
        
        # 根据行为模式更新视线
        if self.current_gaze_state.behavior_mode == GazeBehavior.DIRECT:
            await self._update_direct_gaze(delta_time, head_position, head_rotation)
        elif self.current_gaze_state.behavior_mode == GazeBehavior.GLANCING:
            await self._update_glancing_gaze(delta_time, head_position, head_rotation)
        elif self.current_gaze_state.behavior_mode == GazeBehavior.TRACKING:
            await self._update_tracking_gaze(delta_time, head_position, head_rotation)
        elif self.current_gaze_state.behavior_mode == GazeBehavior.EXPLORING:
            await self._update_exploring_gaze(delta_time, head_position, head_rotation)
        elif self.current_gaze_state.behavior_mode == GazeBehavior.THINKING:
            await self._update_thinking_gaze(delta_time, head_position, head_rotation)
        elif self.current_gaze_state.behavior_mode == GazeBehavior.AVOIDING:
            await self._update_avoiding_gaze(delta_time, head_position, head_rotation)
        
        # 记录视线历史
        if self.current_gaze_state.current_target:
            self.gaze_history.append((
                current_time,
                self.current_gaze_state.current_target,
                self.current_gaze_state.behavior_mode
            ))
            
            # 保持历史记录长度
            if len(self.gaze_history) > 1000:
                self.gaze_history = self.gaze_history[-1000:]
    
    async def _update_blinking(self, current_time: float, delta_time: float):
        """更新眨眼状态"""
        if self.is_blinking:
            # 正在眨眼
            blink_elapsed = current_time - self.blink_start_time
            if blink_elapsed >= self.eye_movement_params["blink_duration"]:
                self.is_blinking = False
        else:
            # 检查是否需要眨眼
            if current_time - self.current_gaze_state.last_blink_time >= 1.0 / self.current_gaze_state.blink_rate:
                self.is_blinking = True
                self.blink_start_time = current_time
                self.current_gaze_state.last_blink_time = current_time
    
    async def _update_direct_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                head_rotation: Tuple[float, float, float, float]):
        """更新直接注视模式"""
        if not self.current_gaze_state.current_target:
            self._select_new_target()
            return
        
        target = self.current_gaze_state.current_target
        self._update_gaze_direction(target.position)
    
    async def _update_glancing_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                  head_rotation: Tuple[float, float, float, float]):
        """更新扫视模式"""
        # 扫视模式会快速在不同目标间切换
        current_time = asyncio.get_event_loop().time()
        
        if self.current_gaze_state.current_target:
            # 检查是否需要切换目标
            target_duration = current_time - self._get_last_target_change_time()
            if target_duration > random.uniform(0.5, 2.0):
                self._select_random_target()
        else:
            self._select_random_target()
    
    async def _update_tracking_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                  head_rotation: Tuple[float, float, float, float]):
        """更新跟踪模式"""
        if not self.current_gaze_state.current_target:
            return
        
        # 平滑跟踪目标
        target = self.current_gaze_state.current_target
        current_direction = np.array(self.current_gaze_state.gaze_direction)
        target_direction = self._calculate_target_direction(head_position, target.position)
        
        # 平滑插值
        smooth_factor = self.eye_movement_params["smooth_pursuit_speed"] * delta_time
        new_direction = current_direction * (1 - smooth_factor) + target_direction * smooth_factor
        
        # 归一化
        new_direction = new_direction / np.linalg.norm(new_direction)
        
        self.current_gaze_state.gaze_direction = tuple(new_direction)
    
    async def _update_exploring_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                   head_rotation: Tuple[float, float, float, float]):
        """更新探索模式"""
        # 探索模式会随机查看周围环境
        current_time = asyncio.get_event_loop().time()
        
        if (not self.current_gaze_state.current_target or 
            current_time - self._get_last_target_change_time() > random.uniform(1.0, 4.0)):
            
            # 选择随机方向
            random_direction = self._generate_random_direction()
            self.current_gaze_state.gaze_direction = random_direction
            
            # 创建临时目标点
            temp_target = GazeTarget(
                target_id=f"explore_{current_time}",
                target_type=GazeTargetType.POINT,
                position=self._calculate_target_position(head_position, random_direction, 2.0),
                importance=0.1,
                duration=1.0,
                movement_speed=0.0
            )
            
            self.current_gaze_state.current_target = temp_target
    
    async def _update_thinking_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                  head_rotation: Tuple[float, float, float, float]):
        """更新思考模式"""
        # 思考模式会有特定的视线模式（如向上看、向左看等）
        current_time = asyncio.get_event_loop().time()
        
        if not self.current_gaze_state.current_target:
            # 选择思考方向的视线目标
            thinking_directions = [
                (0.2, 0.5, 0.8),   # 右上
                (-0.2, 0.5, 0.8),  # 左上
                (0, 0.3, 0.9),     # 正上
                (0, -0.2, 0.9)     # 正前偏下
            ]
            
            thinking_direction = random.choice(thinking_directions)
            self.current_gaze_state.gaze_direction = thinking_direction
            
            # 创建临时目标
            temp_target = GazeTarget(
                target_id=f"think_{current_time}",
                target_type=GazeTargetType.POINT,
                position=self._calculate_target_position(head_position, thinking_direction, 3.0),
                importance=0.2,
                duration=2.0,
                movement_speed=0.0
            )
            
            self.current_gaze_state.current_target = temp_target
        
        # 偶尔的快速扫视
        if random.random() < 0.1 * delta_time:
            quick_glance = self._generate_random_direction()
            quick_direction = np.array(self.current_gaze_state.gaze_direction) * 0.7 + np.array(quick_glance) * 0.3
            quick_direction = quick_direction / np.linalg.norm(quick_direction)
            self.current_gaze_state.gaze_direction = tuple(quick_direction)
    
    async def _update_avoiding_gaze(self, delta_time: float, head_position: Tuple[float, float, float], 
                                  head_rotation: Tuple[float, float, float, float]):
        """更新回避模式"""
        # 回避模式会避免注视特定目标
        if self.current_gaze_state.current_target:
            # 如果当前目标是要回避的，选择新目标
            if self.current_gaze_state.current_target.target_type == GazeTargetType.USER:
                self._select_avoidance_target()
        else:
            self._select_avoidance_target()
    
    def _select_new_target(self):
        """选择新的视线目标"""
        if not self.available_targets:
            # 没有可用目标，看向随机方向
            random_direction = self._generate_random_direction()
            self.current_gaze_state.gaze_direction = random_direction
            return
        
        # 基于优先级选择目标
        candidates = []
        for target_id, target in self.available_targets.items():
            priority = self.target_priorities.get(target_id, 0.5)
            candidates.append((target, priority))
        
        # 按优先级排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 选择最高优先级的目标
        if candidates:
            selected_target = candidates[0][0]
            self.current_gaze_state.current_target = selected_target
            self._update_gaze_direction(selected_target.position)
    
    def _select_random_target(self):
        """随机选择视线目标"""
        if not self.available_targets:
            return
        
        target_ids = list(self.available_targets.keys())
        random_target_id = random.choice(target_ids)
        random_target = self.available_targets[random_target_id]
        
        self.current_gaze_state.current_target = random_target
        self._update_gaze_direction(random_target.position)
    
    def _select_avoidance_target(self):
        """选择回避目标（看向非用户目标）"""
        non_user_targets = []
        
        for target in self.available_targets.values():
            if target.target_type != GazeTargetType.USER:
                non_user_targets.append(target)
        
        if non_user_targets:
            avoidance_target = random.choice(non_user_targets)
            self.current_gaze_state.current_target = avoidance_target
            self._update_gaze_direction(avoidance_target.position)
        else:
            # 没有非用户目标，看向随机方向
            random_direction = self._generate_random_direction()
            self.current_gaze_state.gaze_direction = random_direction
    
    def _update_gaze_direction(self, target_position: Tuple[float, float, float]):
        """更新视线方向指向目标位置"""
        # 简化实现：直接计算方向向量
        # 实际实现应该考虑头部位置和旋转
        direction = np.array(target_position) - np.array([0, 0, 0])  # 简化：假设头部在原点
        direction = direction / np.linalg.norm(direction)
        
        self.current_gaze_state.gaze_direction = tuple(direction)
    
    def _calculate_target_direction(self, head_position: Tuple[float, float, float], 
                                  target_position: Tuple[float, float, float]) -> np.ndarray:
        """计算从头部到目标的方向向量"""
        head_pos = np.array(head_position)
        target_pos = np.array(target_position)
        
        direction = target_pos - head_pos
        return direction / np.linalg.norm(direction)
    
    def _calculate_target_position(self, head_position: Tuple[float, float, float], 
                                 direction: Tuple[float, float, float], distance: float) -> Tuple[float, float, float]:
        """计算视线方向上的目标位置"""
        head_pos = np.array(head_position)
        dir_vec = np.array(direction)
        
        target_pos = head_pos + dir_vec * distance
        return tuple(target_pos)
    
    def _generate_random_direction(self) -> Tuple[float, float, float]:
        """生成随机视线方向"""
        # 生成在半球内的随机方向（主要向前）
        theta = random.uniform(0, 2 * math.pi)  # 水平角度
        phi = random.uniform(0, math.pi / 4)    # 垂直角度（限制在45度内）
        
        x = math.sin(phi) * math.cos(theta)
        y = math.sin(phi) * math.sin(theta)
        z = math.cos(phi)
        
        return (x, y, z)
    
    def _get_last_target_change_time(self) -> float:
        """获取上次目标变更时间"""
        if not self.gaze_history:
            return 0.0
        
        return self.gaze_history[-1][0]
    
    def get_current_gaze_info(self) -> Dict[str, Any]:
        """获取当前视线信息"""
        target_info = None
        if self.current_gaze_state.current_target:
            target_info = {
                "target_id": self.current_gaze_state.current_target.target_id,
                "target_type": self.current_gaze_state.current_target.target_type.value,
                "importance": self.current_gaze_state.current_target.importance
            }
        
        return {
            "gaze_direction": self.current_gaze_state.gaze_direction,
            "focus_intensity": self.current_gaze_state.focus_intensity,
            "behavior_mode": self.current_gaze_state.behavior_mode.value,
            "is_blinking": self.is_blinking,
            "blink_rate": self.current_gaze_state.blink_rate,
            "current_target": target_info,
            "available_targets_count": len(self.available_targets)
        }
    
    def get_gaze_history_summary(self, time_window: float = 60.0) -> Dict[str, Any]:
        """
        获取视线历史摘要
        
        Args:
            time_window: 时间窗口（秒）
            
        Returns:
            视线历史摘要
        """
        current_time = asyncio.get_event_loop().time()
        cutoff_time = current_time - time_window
        
        # 过滤时间窗口内的记录
        recent_history = [record for record in self.gaze_history if record[0] >= cutoff_time]
        
        if not recent_history:
            return {"total_gaze_changes": 0, "behavior_distribution": {}}
        
        # 分析行为分布
        behavior_counts = {}
        for _, _, behavior in recent_history:
            behavior_str = behavior.value
            behavior_counts[behavior_str] = behavior_counts.get(behavior_str, 0) + 1
        
        # 计算目标分布
        target_counts = {}
        for _, target, _ in recent_history:
            target_type = target.target_type.value
            target_counts[target_type] = target_counts.get(target_type, 0) + 1
        
        return {
            "total_gaze_changes": len(recent_history),
            "changes_per_minute": len(recent_history) / (time_window / 60.0),
            "behavior_distribution": behavior_counts,
            "target_distribution": target_counts,
            "time_window": time_window
        }

# 全局视线系统实例
_global_gaze_system: Optional[GazeSystem] = None

def get_gaze_system() -> GazeSystem:
    """获取全局视线系统实例"""
    global _global_gaze_system
    if _global_gaze_system is None:
        _global_gaze_system = GazeSystem()
    return _global_gaze_system
