"""
表情控制：控制面部表情
负责3D虚拟猫咪面部表情的生成和控制
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import math

# 导入依赖模块
from data.models.three_d.blend_shapes import BlendShapeSystem

class ExpressionType(Enum):
    """表情类型枚举"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    CONTENT = "content"
    EXCITED = "excited"
    SLEEPY = "sleepy"
    CURIOUS = "curious"

@dataclass
class FacialExpression:
    """面部表情配置"""
    expression_type: ExpressionType
    blend_shape_weights: Dict[str, float]  # 混合形状权重
    duration: float  # 持续时间（秒）
    intensity: float  # 强度 0.0-1.0
    transition_time: float  # 过渡时间（秒）

class ExpressionController:
    """表情控制器：控制面部表情"""
    
    def __init__(self, blend_shape_system: BlendShapeSystem):
        self.blend_shape_system = blend_shape_system
        self.logger = self._setup_logger()
        
        # 表情状态
        self.current_expression = ExpressionType.NEUTRAL
        self.target_expression = ExpressionType.NEUTRAL
        self.expression_intensity = 0.0
        self.is_transitioning = False
        
        # 表情时间控制
        self.expression_start_time = 0.0
        self.transition_start_time = 0.0
        self.transition_duration = 0.3  # 默认过渡时间
        
        # 表情库
        self.expression_library: Dict[ExpressionType, FacialExpression] = {}
        
        # 初始化表情库
        self._initialize_expression_library()
        
        # 表情混合器
        self.expression_blend_weights: Dict[ExpressionType, float] = {}
        
        # 微表情参数
        self.micro_expression_enabled = True
        self.micro_expression_timer = 0.0
        self.micro_expression_interval = 3.0  # 微表情间隔
        
        self.logger.info("表情控制器初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("ExpressionController")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_expression_library(self):
        """初始化表情库"""
        # 中性表情
        self.expression_library[ExpressionType.NEUTRAL] = FacialExpression(
            expression_type=ExpressionType.NEUTRAL,
            blend_shape_weights={
                "brow_center_up": 0.0,
                "brow_outer_up": 0.0,
                "eye_blink_left": 0.0,
                "eye_blink_right": 0.0,
                "eye_squint_left": 0.0,
                "eye_squint_right": 0.0,
                "mouth_smile": 0.0,
                "mouth_frown": 0.0,
                "mouth_open": 0.0
            },
            duration=0.0,
            intensity=0.0,
            transition_time=0.2
        )
        
        # 高兴表情
        self.expression_library[ExpressionType.HAPPY] = FacialExpression(
            expression_type=ExpressionType.HAPPY,
            blend_shape_weights={
                "brow_center_up": 0.3,
                "brow_outer_up": 0.4,
                "eye_squint_left": 0.6,
                "eye_squint_right": 0.6,
                "mouth_smile": 0.8,
                "mouth_open": 0.1
            },
            duration=2.0,
            intensity=0.8,
            transition_time=0.3
        )
        
        # 悲伤表情
        self.expression_library[ExpressionType.SAD] = FacialExpression(
            expression_type=ExpressionType.SAD,
            blend_shape_weights={
                "brow_center_up": 0.2,
                "brow_outer_down": 0.6,
                "eye_squint_left": 0.3,
                "eye_squint_right": 0.3,
                "mouth_frown": 0.7,
                "mouth_lower_down": 0.4
            },
            duration=2.0,
            intensity=0.7,
            transition_time=0.4
        )
        
        # 生气表情
        self.expression_library[ExpressionType.ANGRY] = FacialExpression(
            expression_type=ExpressionType.ANGRY,
            blend_shape_weights={
                "brow_center_down": 0.8,
                "brow_outer_down": 0.6,
                "eye_squint_left": 0.7,
                "eye_squint_right": 0.7,
                "mouth_frown": 0.6,
                "mouth_upper_up": 0.3
            },
            duration=1.5,
            intensity=0.9,
            transition_time=0.2
        )
        
        # 惊讶表情
        self.expression_library[ExpressionType.SURPRISED] = FacialExpression(
            expression_type=ExpressionType.SURPRISED,
            blend_shape_weights={
                "brow_center_up": 0.9,
                "brow_outer_up": 0.8,
                "eye_wide_left": 0.8,
                "eye_wide_right": 0.8,
                "mouth_open": 0.7
            },
            duration=1.0,
            intensity=0.8,
            transition_time=0.1
        )
        
        # 恐惧表情
        self.expression_library[ExpressionType.FEARFUL] = FacialExpression(
            expression_type=ExpressionType.FEARFUL,
            blend_shape_weights={
                "brow_center_up": 0.7,
                "brow_outer_up": 0.5,
                "eye_wide_left": 0.6,
                "eye_wide_right": 0.6,
                "mouth_open": 0.4,
                "mouth_frown": 0.3
            },
            duration=1.5,
            intensity=0.7,
            transition_time=0.3
        )
        
        # 满足表情
        self.expression_library[ExpressionType.CONTENT] = FacialExpression(
            expression_type=ExpressionType.CONTENT,
            blend_shape_weights={
                "brow_center_up": 0.2,
                "brow_outer_up": 0.2,
                "eye_squint_left": 0.3,
                "eye_squint_right": 0.3,
                "mouth_smile": 0.5,
                "mouth_open": 0.05
            },
            duration=3.0,
            intensity=0.5,
            transition_time=0.4
        )
        
        # 兴奋表情
        self.expression_library[ExpressionType.EXCITED] = FacialExpression(
            expression_type=ExpressionType.EXCITED,
            blend_shape_weights={
                "brow_center_up": 0.6,
                "brow_outer_up": 0.7,
                "eye_wide_left": 0.5,
                "eye_wide_right": 0.5,
                "mouth_smile": 0.9,
                "mouth_open": 0.3
            },
            duration=1.5,
            intensity=0.9,
            transition_time=0.2
        )
        
        # 困倦表情
        self.expression_library[ExpressionType.SLEEPY] = FacialExpression(
            expression_type=ExpressionType.SLEEPY,
            blend_shape_weights={
                "brow_center_down": 0.3,
                "brow_outer_down": 0.4,
                "eye_blink_left": 0.8,
                "eye_blink_right": 0.8,
                "eye_squint_left": 0.6,
                "eye_squint_right": 0.6,
                "mouth_open": 0.1
            },
            duration=4.0,
            intensity=0.6,
            transition_time=0.5
        )
        
        # 好奇表情
        self.expression_library[ExpressionType.CURIOUS] = FacialExpression(
            expression_type=ExpressionType.CURIOUS,
            blend_shape_weights={
                "brow_center_up": 0.4,
                "brow_outer_up": 0.3,
                "eye_wide_left": 0.4,
                "eye_wide_right": 0.4,
                "mouth_smile": 0.2,
                "mouth_open": 0.2
            },
            duration=2.0,
            intensity=0.5,
            transition_time=0.3
        )
    
    async def set_expression(self, expression_type: ExpressionType, intensity: float = 1.0, 
                           duration: float = None, transition_time: float = None):
        """
        设置表情
        
        Args:
            expression_type: 表情类型
            intensity: 表情强度 (0.0-1.0)
            duration: 持续时间（秒），None表示使用默认值
            transition_time: 过渡时间（秒），None表示使用默认值
        """
        if expression_type not in self.expression_library:
            self.logger.warning(f"未知的表情类型: {expression_type}")
            return
        
        # 获取表情配置
        expression_config = self.expression_library[expression_type]
        
        # 更新目标表情
        self.target_expression = expression_type
        self.expression_intensity = intensity
        
        # 设置时间参数
        if duration is not None:
            expression_config.duration = duration
        if transition_time is not None:
            expression_config.transition_time = transition_time
        
        # 开始表情过渡
        self.is_transitioning = True
        self.transition_start_time = asyncio.get_event_loop().time()
        self.transition_duration = expression_config.transition_time
        
        self.logger.info(f"开始表情过渡: {self.current_expression.value} -> {expression_type.value}")
    
    async def blend_expressions(self, expression_weights: Dict[ExpressionType, float]):
        """
        混合多个表情
        
        Args:
            expression_weights: 表情权重映射
        """
        # 归一化权重
        total_weight = sum(expression_weights.values())
        if total_weight == 0:
            return
        
        normalized_weights = {
            expr: weight / total_weight 
            for expr, weight in expression_weights.items()
        }
        
        # 更新混合权重
        self.expression_blend_weights = normalized_weights
        
        # 计算混合后的混合形状权重
        blended_weights = {}
        
        for expression_type, weight in normalized_weights.items():
            if expression_type in self.expression_library:
                expression_config = self.expression_library[expression_type]
                
                for blend_shape, base_weight in expression_config.blend_shape_weights.items():
                    if blend_shape not in blended_weights:
                        blended_weights[blend_shape] = 0.0
                    blended_weights[blend_shape] += base_weight * weight
        
        # 应用混合形状权重
        for blend_shape, weight in blended_weights.items():
            self.blend_shape_system.set_weight(blend_shape, weight)
        
        self.logger.info(f"表情混合完成: {normalized_weights}")
    
    async def update(self, delta_time: float):
        """更新表情状态"""
        current_time = asyncio.get_event_loop().time()
        
        # 处理表情过渡
        if self.is_transitioning:
            transition_progress = (current_time - self.transition_start_time) / self.transition_duration
            
            if transition_progress >= 1.0:
                # 过渡完成
                self.current_expression = self.target_expression
                self.is_transitioning = False
                self.expression_start_time = current_time
                
                # 应用目标表情
                target_config = self.expression_library[self.target_expression]
                scaled_weights = self._scale_expression_weights(target_config, self.expression_intensity)
                
                for blend_shape, weight in scaled_weights.items():
                    self.blend_shape_system.set_weight(blend_shape, weight)
                
                self.logger.info(f"表情过渡完成: {self.target_expression.value}")
                
            else:
                # 在过渡中，混合当前和目标表情
                current_config = self.expression_library[self.current_expression]
                target_config = self.expression_library[self.target_expression]
                
                # 使用缓动函数计算混合权重
                ease_progress = self._ease_in_out(transition_progress)
                current_weight = 1.0 - ease_progress
                target_weight = ease_progress
                
                # 混合表情权重
                blended_weights = {}
                
                # 混合当前表情
                current_scaled = self._scale_expression_weights(current_config, self.expression_intensity)
                for blend_shape, weight in current_scaled.items():
                    blended_weights[blend_shape] = weight * current_weight
                
                # 混合目标表情
                target_scaled = self._scale_expression_weights(target_config, self.expression_intensity)
                for blend_shape, weight in target_scaled.items():
                    if blend_shape not in blended_weights:
                        blended_weights[blend_shape] = 0.0
                    blended_weights[blend_shape] += weight * target_weight
                
                # 应用混合权重
                for blend_shape, weight in blended_weights.items():
                    self.blend_shape_system.set_weight(blend_shape, weight)
        
        # 处理表情持续时间
        if not self.is_transitioning and self.current_expression != ExpressionType.NEUTRAL:
            expression_config = self.expression_library[self.current_expression]
            
            if expression_config.duration > 0:
                elapsed_time = current_time - self.expression_start_time
                
                if elapsed_time >= expression_config.duration:
                    # 表情持续时间结束，返回中性表情
                    await self.set_expression(ExpressionType.NEUTRAL, 1.0, 0.0, 0.3)
        
        # 处理微表情
        if self.micro_expression_enabled:
            self.micro_expression_timer += delta_time
            
            if self.micro_expression_timer >= self.micro_expression_interval:
                await self._trigger_micro_expression()
                self.micro_expression_timer = 0.0
    
    async def _trigger_micro_expression(self):
        """触发微表情"""
        # 随机选择微表情类型
        import random
        micro_expression_types = [
            ExpressionType.HAPPY, ExpressionType.CURIOUS, 
            ExpressionType.SURPRISED, ExpressionType.CONTENT
        ]
        
        micro_expression = random.choice(micro_expression_types)
        intensity = random.uniform(0.1, 0.3)  # 微表情强度较低
        duration = random.uniform(0.2, 0.5)   # 微表情持续时间较短
        
        # 保存当前表情状态
        original_expression = self.current_expression
        original_intensity = self.expression_intensity
        
        # 应用微表情
        await self.set_expression(micro_expression, intensity, duration, 0.1)
        
        # 设置回调，在微表情结束后恢复原表情
        async def restore_expression():
            await asyncio.sleep(duration + 0.1)  # 等待微表情完成
            if self.current_expression == micro_expression:
                await self.set_expression(original_expression, original_intensity)
        
        asyncio.create_task(restore_expression())
    
    def _scale_expression_weights(self, expression_config: FacialExpression, intensity: float) -> Dict[str, float]:
        """根据强度缩放表情权重"""
        scaled_weights = {}
        
        for blend_shape, weight in expression_config.blend_shape_weights.items():
            scaled_weights[blend_shape] = weight * intensity
        
        return scaled_weights
    
    def _ease_in_out(self, t: float) -> float:
        """缓动函数：平滑过渡"""
        return t * t * (3.0 - 2.0 * t)
    
    async def sync_with_speech(self, phonemes: List[Tuple[str, float]], speech_intensity: float = 1.0):
        """
        与语音同步口型
        
        Args:
            phonemes: 音素列表，每个元素为(音素, 持续时间)
            speech_intensity: 语音强度
        """
        # 音素到混合形状的映射
        phoneme_to_blendshape = {
            "AA": ["mouth_open", "jaw_down"],
            "AE": ["mouth_open", "jaw_down"],
            "AH": ["mouth_open", "jaw_down"],
            "AO": ["mouth_open", "mouth_round"],
            "AW": ["mouth_open", "mouth_wide"],
            "AY": ["mouth_open", "mouth_wide"],
            "B": ["mouth_close", "lips_together"],
            "CH": ["mouth_wide", "lips_together"],
            "D": ["tongue_up", "lips_part"],
            "DH": ["tongue_between_teeth", "lips_part"],
            "EH": ["mouth_open", "jaw_down"],
            "ER": ["mouth_open", "tongue_curl"],
            "EY": ["mouth_open", "mouth_wide"],
            "F": ["lips_bottom_in", "lips_top_in"],
            "G": ["tongue_back", "throat_constrict"],
            "HH": ["mouth_open", "throat_open"],
            "IH": ["mouth_open", "tongue_front"],
            "IY": ["mouth_open", "tongue_front"],
            "JH": ["mouth_wide", "lips_together"],
            "K": ["tongue_back", "throat_constrict"],
            "L": ["tongue_up", "lips_part"],
            "M": ["lips_together", "mouth_close"],
            "N": ["tongue_up", "lips_part"],
            "NG": ["tongue_back", "throat_constrict"],
            "OW": ["mouth_open", "mouth_round"],
            "OY": ["mouth_open", "mouth_round"],
            "P": ["lips_together", "mouth_close"],
            "R": ["tongue_curl", "lips_round"],
            "S": ["tongue_up", "lips_part"],
            "SH": ["mouth_wide", "lips_round"],
            "T": ["tongue_up", "lips_part"],
            "TH": ["tongue_between_teeth", "lips_part"],
            "UH": ["mouth_open", "tongue_back"],
            "UW": ["mouth_open", "lips_round"],
            "V": ["lips_bottom_in", "lips_top_in"],
            "W": ["lips_round", "mouth_round"],
            "Y": ["tongue_front", "lips_wide"],
            "Z": ["tongue_up", "lips_part"],
            "ZH": ["mouth_wide", "lips_round"]
        }
        
        for phoneme, duration in phonemes:
            if phoneme in phoneme_to_blendshape:
                blend_shapes = phoneme_to_blendshape[phoneme]
                
                for blend_shape in blend_shapes:
                    # 设置混合形状权重
                    self.blend_shape_system.set_weight(blend_shape, 0.7 * speech_intensity)
                
                # 等待音素持续时间
                await asyncio.sleep(duration * 0.8)  # 稍微提前结束以平滑过渡
                
                # 重置混合形状
                for blend_shape in blend_shapes:
                    self.blend_shape_system.set_weight(blend_shape, 0.0)
            
            else:
                # 未知音素，短暂等待
                await asyncio.sleep(duration)
    
    def get_current_expression_info(self) -> Dict[str, Any]:
        """获取当前表情信息"""
        return {
            "current_expression": self.current_expression.value,
            "target_expression": self.target_expression.value,
            "intensity": self.expression_intensity,
            "is_transitioning": self.is_transitioning,
            "blend_weights": {
                expr.value: weight 
                for expr, weight in self.expression_blend_weights.items()
            }
        }
    
    async def reset_expression(self):
        """重置为中性表情"""
        await self.set_expression(ExpressionType.NEUTRAL, 1.0, 0.0, 0.2)
        self.expression_blend_weights.clear()
        
        self.logger.info("表情已重置为中性")

# 全局表情控制器实例
_global_expression_controller: Optional[ExpressionController] = None

async def get_expression_controller(blend_shape_system: BlendShapeSystem = None) -> ExpressionController:
    """获取全局表情控制器实例"""
    global _global_expression_controller
    if _global_expression_controller is None and blend_shape_system is not None:
        _global_expression_controller = ExpressionController(blend_shape_system)
    return _global_expression_controller

