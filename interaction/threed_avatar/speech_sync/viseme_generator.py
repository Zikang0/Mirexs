"""
视素生成器 - 3D口型动画生成系统
完整实现音素到3D面部动画的转换、视素权重计算和面部骨骼控制
支持情感驱动的口型变化和个性化口型风格
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from enum import Enum
import json
from pathlib import Path

# 导入依赖
from interaction.threed_avatar.character_system.model_manager import ModelInstance
from interaction.threed_avatar.character_system.skeleton_animation import BoneTransform
from interaction.output_systems.speech_output.multilingual_tts import EmotionType
from interaction.threed_avatar.speech_sync.voice_animation_map import VoiceAnimationMap, voice_animation_map

logger = logging.getLogger(__name__)

class VisemeType(Enum):
    """视素类型枚举"""
    A = "A"        # 啊 - 大开口
    E = "E"        # 呃 - 中开口  
    I = "I"        # 一 - 小开口
    O = "O"        # 哦 - 圆唇
    U = "U"        # 乌 - 小圆唇
    B = "B"        # 波 - 双唇闭合
    F = "F"        # 佛 - 唇齿接触
    M = "M"        # 摸 - 双唇鼻音
    P = "P"        # 坡 - 双唇爆破
    R = "R"        # 日 - 舌尖卷起
    S = "S"        # 思 - 齿龈擦音
    T = "T"        # 特 - 舌尖接触
    W = "W"        # 我 - 圆唇近音
    TH = "TH"      # 思 - 齿间擦音
    SH = "SH"      # 师 - 卷舌擦音
    CH = "CH"      # 吃 - 塞擦音
    SILENCE = "silence"  # 静音

@dataclass
class VisemeConfig:
    """视素配置"""
    base_intensity: float = 1.0      # 基础强度
    emotion_influence: float = 0.8   # 情感影响
    personalization_factor: float = 1.0  # 个性化因子
    smooth_transitions: bool = True  # 平滑过渡
    transition_speed: float = 0.2    # 过渡速度
    max_blend_weight: float = 1.0    # 最大混合权重

@dataclass
class VisemeData:
    """视素数据"""
    viseme_type: VisemeType
    weights: Dict[str, float]  # 骨骼权重
    duration: float           # 持续时间
    intensity: float          # 强度
    emotion_modifiers: Dict[str, float]  # 情感修饰器

class VisemeGenerator:
    """视素生成器 - 完整实现"""
    
    def __init__(self, model_instance: ModelInstance):
        self.model_instance = model_instance
        self.voice_animation_map = voice_animation_map
        
        # 视素数据库
        self.viseme_database: Dict[VisemeType, VisemeData] = {}
        self.phoneme_viseme_map: Dict[str, List[VisemeType]] = {}
        
        # 配置
        self.config = VisemeConfig()
        
        # 缓存
        self.viseme_cache: Dict[str, VisemeData] = {}
        self.transition_cache: Dict[str, List[VisemeData]] = {}
        
        # 统计信息
        self.stats = {
            "visemes_generated": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "transition_calculations": 0,
            "average_generation_time": 0.0
        }
        
        # 初始化视素系统
        self._initialize_viseme_system()
        
        logger.info("VisemeGenerator initialized")

    def _initialize_viseme_system(self):
        """初始化视素系统"""
        try:
            # 加载视素数据库
            self._load_viseme_database()
            
            # 初始化音素-视素映射
            self._initialize_phoneme_viseme_mapping()
            
            # 初始化面部骨骼权重
            self._initialize_face_bone_weights()
            
            logger.info("Viseme system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing viseme system: {e}")

    def _load_viseme_database(self):
        """加载视素数据库"""
        try:
            # 基础视素定义
            self.viseme_database = {
                # 元音视素
                VisemeType.A: VisemeData(
                    viseme_type=VisemeType.A,
                    weights={
                        "jaw": 0.8, "mouth_upper_lip": 0.3, "mouth_lower_lip": 0.4,
                        "tongue": 0.2, "cheek_left": 0.1, "cheek_right": 0.1
                    },
                    duration=0.2,
                    intensity=1.0,
                    emotion_modifiers={"happy": 0.2, "angry": 0.3, "sad": -0.2}
                ),
                
                VisemeType.E: VisemeData(
                    viseme_type=VisemeType.E,
                    weights={
                        "jaw": 0.4, "mouth_upper_lip": 0.6, "mouth_lower_lip": 0.5,
                        "tongue": 0.3, "mouth_left_corner": 0.2, "mouth_right_corner": 0.2
                    },
                    duration=0.15,
                    intensity=0.8,
                    emotion_modifiers={"happy": 0.1, "surprised": 0.4}
                ),
                
                VisemeType.I: VisemeData(
                    viseme_type=VisemeType.I,
                    weights={
                        "jaw": 0.2, "mouth_upper_lip": 0.7, "mouth_lower_lip": 0.6,
                        "tongue": 0.4, "cheek_left": 0.3, "cheek_right": 0.3
                    },
                    duration=0.1,
                    intensity=0.7,
                    emotion_modifiers={"happy": 0.1, "fearful": 0.2}
                ),
                
                VisemeType.O: VisemeData(
                    viseme_type=VisemeType.O,
                    weights={
                        "jaw": 0.6, "mouth_upper_lip": 0.5, "mouth_lower_lip": 0.7,
                        "tongue": 0.3, "mouth_left_corner": 0.4, "mouth_right_corner": 0.4
                    },
                    duration=0.18,
                    intensity=0.9,
                    emotion_modifiers={"surprised": 0.3, "happy": 0.2}
                ),
                
                VisemeType.U: VisemeData(
                    viseme_type=VisemeType.U,
                    weights={
                        "jaw": 0.3, "mouth_upper_lip": 0.4, "mouth_lower_lip": 0.8,
                        "tongue": 0.5, "mouth_left_corner": 0.6, "mouth_right_corner": 0.6
                    },
                    duration=0.12,
                    intensity=0.8,
                    emotion_modifiers={"sad": 0.3, "fearful": 0.2}
                ),
                
                # 辅音视素
                VisemeType.B: VisemeData(
                    viseme_type=VisemeType.B,
                    weights={
                        "mouth_upper_lip": 0.9, "mouth_lower_lip": 0.8,
                        "jaw": 0.1, "cheek_left": 0.2, "cheek_right": 0.2
                    },
                    duration=0.08,
                    intensity=0.9,
                    emotion_modifiers={"angry": 0.4, "happy": 0.1}
                ),
                
                VisemeType.F: VisemeData(
                    viseme_type=VisemeType.F,
                    weights={
                        "mouth_upper_lip": 0.7, "mouth_lower_lip": 0.6,
                        "jaw": 0.2, "teeth_upper": 0.5, "teeth_lower": 0.4
                    },
                    duration=0.1,
                    intensity=0.7,
                    emotion_modifiers={}
                ),
                
                VisemeType.M: VisemeData(
                    viseme_type=VisemeType.M,
                    weights={
                        "mouth_upper_lip": 0.8, "mouth_lower_lip": 0.7,
                        "jaw": 0.1, "nose": 0.3
                    },
                    duration=0.15,
                    intensity=0.8,
                    emotion_modifiers={"calm": 0.2}
                ),
                
                VisemeType.P: VisemeData(
                    viseme_type=VisemeType.P,
                    weights={
                        "mouth_upper_lip": 0.9, "mouth_lower_lip": 0.8,
                        "jaw": 0.1, "cheek_left": 0.3, "cheek_right": 0.3
                    },
                    duration=0.07,
                    intensity=1.0,
                    emotion_modifiers={"angry": 0.5, "excited": 0.3}
                ),
                
                VisemeType.S: VisemeData(
                    viseme_type=VisemeType.S,
                    weights={
                        "tongue": 0.7, "mouth_upper_lip": 0.3,
                        "teeth_upper": 0.6, "teeth_lower": 0.5
                    },
                    duration=0.12,
                    intensity=0.6,
                    emotion_modifiers={}
                ),
                
                VisemeType.T: VisemeData(
                    viseme_type=VisemeType.T,
                    weights={
                        "tongue": 0.8, "mouth_upper_lip": 0.2,
                        "teeth_upper": 0.4, "teeth_lower": 0.3
                    },
                    duration=0.09,
                    intensity=0.7,
                    emotion_modifiers={}
                ),
                
                # 静音
                VisemeType.SILENCE: VisemeData(
                    viseme_type=VisemeType.SILENCE,
                    weights={},  # 所有权重为0
                    duration=0.1,
                    intensity=0.0,
                    emotion_modifiers={}
                )
            }
            
            logger.info(f"Viseme database loaded: {len(self.viseme_database)} visemes")
            
        except Exception as e:
            logger.error(f"Error loading viseme database: {e}")

    def _initialize_phoneme_viseme_mapping(self):
        """初始化音素-视素映射"""
        try:
            # 中文音素到视素映射
            self.phoneme_viseme_map = {
                # 元音
                "a": [VisemeType.A],
                "o": [VisemeType.O],
                "e": [VisemeType.E],
                "i": [VisemeType.I],
                "u": [VisemeType.U],
                "ü": [VisemeType.U, VisemeType.I],  # 组合视素
                
                # 辅音
                "b": [VisemeType.B],
                "p": [VisemeType.P],
                "m": [VisemeType.M],
                "f": [VisemeType.F],
                "d": [VisemeType.T],
                "t": [VisemeType.T],
                "n": [VisemeType.N],
                "l": [VisemeType.L],
                "g": [VisemeType.G],
                "k": [VisemeType.K],
                "h": [VisemeType.H],
                "j": [VisemeType.J],
                "q": [VisemeType.CH],
                "x": [VisemeType.SH],
                "zh": [VisemeType.CH, VisemeType.SH],
                "ch": [VisemeType.CH],
                "sh": [VisemeType.SH],
                "r": [VisemeType.R],
                "z": [VisemeType.S],
                "c": [VisemeType.T, VisemeType.S],
                "s": [VisemeType.S],
                
                # 静音
                "sil": [VisemeType.SILENCE]
            }
            
            logger.info("Phoneme-viseme mapping initialized")
            
        except Exception as e:
            logger.error(f"Error initializing phoneme-viseme mapping: {e}")

    def _initialize_face_bone_weights(self):
        """初始化面部骨骼权重"""
        try:
            # 面部骨骼基础权重
            self.face_bone_base_weights = {
                "jaw": 1.0,
                "mouth_upper_lip": 0.8,
                "mouth_lower_lip": 0.8,
                "mouth_left_corner": 0.7,
                "mouth_right_corner": 0.7,
                "tongue": 0.6,
                "cheek_left": 0.4,
                "cheek_right": 0.4,
                "nose": 0.3,
                "teeth_upper": 0.5,
                "teeth_lower": 0.5
            }
            
            logger.info("Face bone weights initialized")
            
        except Exception as e:
            logger.error(f"Error initializing face bone weights: {e}")

    async def generate_viseme(self, phoneme: str, duration: float = 0.2, 
                            emotion: EmotionType = EmotionType.NEUTRAL) -> Dict[str, float]:
        """
        生成视素权重 - 完整实现
        
        Args:
            phoneme: 音素符号
            duration: 音素持续时间
            emotion: 情感类型
            
        Returns:
            Dict[str, float]: 视素权重字典
        """
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"{phoneme}_{duration}_{emotion.value}"
            if cache_key in self.viseme_cache:
                self.stats["cache_hits"] += 1
                cached_data = self.viseme_cache[cache_key]
                return cached_data.weights
            
            self.stats["cache_misses"] += 1
            self.stats["visemes_generated"] += 1
            
            # 获取基础视素类型
            viseme_types = await self._get_viseme_types_for_phoneme(phoneme)
            if not viseme_types:
                logger.warning(f"No viseme types found for phoneme: {phoneme}")
                return await self._get_default_viseme_weights()
            
            # 生成视素权重
            viseme_weights = await self._generate_combined_viseme_weights(
                viseme_types, duration, emotion
            )
            
            # 应用个性化调整
            viseme_weights = await self._apply_personalization(viseme_weights)
            
            # 应用情感影响
            viseme_weights = await self._apply_emotion_influence(viseme_weights, emotion)
            
            # 归一化权重
            viseme_weights = await self._normalize_weights(viseme_weights)
            
            # 创建视素数据并缓存
            viseme_data = VisemeData(
                viseme_type=viseme_types[0] if viseme_types else VisemeType.SILENCE,
                weights=viseme_weights,
                duration=duration,
                intensity=1.0,
                emotion_modifiers={}
            )
            
            self.viseme_cache[cache_key] = viseme_data
            
            # 更新统计
            generation_time = time.time() - start_time
            self.stats["average_generation_time"] = (
                (self.stats["average_generation_time"] * (self.stats["visemes_generated"] - 1) + generation_time) 
                / self.stats["visemes_generated"]
            )
            
            logger.debug(f"Viseme generated for phoneme '{phoneme}': {viseme_weights}")
            return viseme_weights
            
        except Exception as e:
            logger.error(f"Error generating viseme for phoneme '{phoneme}': {e}")
            return await self._get_default_viseme_weights()

    async def _get_viseme_types_for_phoneme(self, phoneme: str) -> List[VisemeType]:
        """获取音素对应的视素类型"""
        try:
            if phoneme in self.phoneme_viseme_map:
                return self.phoneme_viseme_map[phoneme]
            else:
                # 未知音素，使用默认映射
                return await self._map_unknown_phoneme(phoneme)
                
        except Exception as e:
            logger.warning(f"Error getting viseme types for phoneme '{phoneme}': {e}")
            return [VisemeType.A]  # 默认视素

    async def _map_unknown_phoneme(self, phoneme: str) -> List[VisemeType]:
        """映射未知音素"""
        try:
            # 基于音素特征猜测视素类型
            if len(phoneme) == 0:
                return [VisemeType.SILENCE]
            
            # 根据音素特征分类
            if phoneme in "aeiouü":
                # 元音
                if phoneme in "a":
                    return [VisemeType.A]
                elif phoneme in "eo":
                    return [VisemeType.O]
                elif phoneme in "iü":
                    return [VisemeType.I, VisemeType.U]
                elif phoneme in "u":
                    return [VisemeType.U]
                else:
                    return [VisemeType.E]
            else:
                # 辅音
                if phoneme in "bp":
                    return [VisemeType.B, VisemeType.P]
                elif phoneme in "mf":
                    return [VisemeType.M, VisemeType.F]
                elif phoneme in "dt":
                    return [VisemeType.T]
                elif phoneme in "sz":
                    return [VisemeType.S]
                elif phoneme in "kg":
                    return [VisemeType.K, VisemeType.G]
                else:
                    return [VisemeType.SILENCE]
                    
        except Exception as e:
            logger.warning(f"Error mapping unknown phoneme '{phoneme}': {e}")
            return [VisemeType.A]

    async def _generate_combined_viseme_weights(self, viseme_types: List[VisemeType],
                                              duration: float, emotion: EmotionType) -> Dict[str, float]:
        """生成组合视素权重"""
        try:
            combined_weights = {}
            
            for viseme_type in viseme_types:
                if viseme_type in self.viseme_database:
                    viseme_data = self.viseme_database[viseme_type]
                    
                    # 应用持续时间影响
                    duration_factor = await self._calculate_duration_factor(
                        duration, viseme_data.duration
                    )
                    
                    # 合并权重
                    for bone, weight in viseme_data.weights.items():
                        current_weight = combined_weights.get(bone, 0.0)
                        new_weight = weight * duration_factor
                        combined_weights[bone] = max(current_weight, new_weight)
            
            # 如果没有有效的权重，使用默认值
            if not combined_weights:
                combined_weights = await self._get_default_viseme_weights()
            
            return combined_weights
            
        except Exception as e:
            logger.error(f"Error generating combined viseme weights: {e}")
            return await self._get_default_viseme_weights()

    async def _calculate_duration_factor(self, actual_duration: float, 
                                       base_duration: float) -> float:
        """计算持续时间因子"""
        try:
            # 标准化持续时间影响
            if base_duration > 0:
                ratio = actual_duration / base_duration
                # 使用sigmoid函数进行平滑
                factor = 2.0 / (1.0 + np.exp(-3.0 * (ratio - 1.0))) - 1.0
                return max(0.0, min(1.0, factor))
            else:
                return 1.0
                
        except Exception as e:
            logger.warning(f"Error calculating duration factor: {e}")
            return 1.0

    async def _apply_personalization(self, weights: Dict[str, float]) -> Dict[str, float]:
        """应用个性化调整"""
        try:
            personalized_weights = weights.copy()
            
            # 基于基础权重调整
            for bone, weight in personalized_weights.items():
                if bone in self.face_bone_base_weights:
                    base_weight = self.face_bone_base_weights[bone]
                    # 个性化因子影响
                    adjusted_weight = weight * base_weight * self.config.personalization_factor
                    personalized_weights[bone] = min(self.config.max_blend_weight, adjusted_weight)
            
            return personalized_weights
            
        except Exception as e:
            logger.warning(f"Error applying personalization: {e}")
            return weights

    async def _apply_emotion_influence(self, weights: Dict[str, float], 
                                     emotion: EmotionType) -> Dict[str, float]:
        """应用情感影响"""
        try:
            if emotion == EmotionType.NEUTRAL:
                return weights
            
            emotion_weights = weights.copy()
            emotion_key = emotion.value
            
            # 获取情感映射
            emotion_mapping = await self.voice_animation_map.map_emotion_to_expression(emotion, 1.0)
            
            # 应用情感影响
            for bone, weight in emotion_weights.items():
                emotion_factor = 1.0
                
                if "smile" in emotion_mapping and emotion_mapping["smile"] > 0:
                    # 微笑影响嘴角
                    if "corner" in bone:
                        emotion_factor += emotion_mapping["smile"] * 0.3
                
                if "frown" in emotion_mapping and emotion_mapping["frown"] > 0:
                    # 皱眉影响眉毛和嘴角
                    if "brow" in bone:
                        emotion_factor += emotion_mapping["frown"] * 0.4
                    elif "corner" in bone:
                        emotion_factor -= emotion_mapping["frown"] * 0.2
                
                if "wide" in emotion_mapping and emotion_mapping["wide"] > 0:
                    # 眼睛睁大影响眼部区域
                    if "eye" in bone:
                        emotion_factor += emotion_mapping["wide"] * 0.5
                
                # 应用情感因子
                emotion_weights[bone] = weight * emotion_factor
            
            return emotion_weights
            
        except Exception as e:
            logger.warning(f"Error applying emotion influence: {e}")
            return weights

    async def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重"""
        try:
            # 找到最大权重
            max_weight = max(weights.values()) if weights else 1.0
            
            if max_weight > 0:
                # 归一化到0-1范围
                normalized = {bone: weight / max_weight for bone, weight in weights.items()}
            else:
                normalized = weights.copy()
            
            # 确保至少有一些权重
            if not normalized or max(normalized.values()) < 0.1:
                normalized = await self._get_default_viseme_weights()
            
            return normalized
            
        except Exception as e:
            logger.warning(f"Error normalizing weights: {e}")
            return weights

    async def _get_default_viseme_weights(self) -> Dict[str, float]:
        """获取默认视素权重"""
        return {
            "jaw": 0.3,
            "mouth_upper_lip": 0.2,
            "mouth_lower_lip": 0.2,
            "mouth_left_corner": 0.1,
            "mouth_right_corner": 0.1
        }

    async def generate_viseme_transition(self, from_phoneme: str, to_phoneme: str,
                                       transition_duration: float = 0.1,
                                       emotion: EmotionType = EmotionType.NEUTRAL) -> List[Dict[str, float]]:
        """生成视素过渡序列"""
        try:
            self.stats["transition_calculations"] += 1
            
            # 检查缓存
            cache_key = f"transition_{from_phoneme}_{to_phoneme}_{transition_duration}_{emotion.value}"
            if cache_key in self.transition_cache:
                return [frame.weights for frame in self.transition_cache[cache_key]]
            
            # 获取起始和结束视素权重
            start_weights = await self.generate_viseme(from_phoneme, 0.2, emotion)
            end_weights = await self.generate_viseme(to_phoneme, 0.2, emotion)
            
            # 生成过渡帧
            transition_frames = []
            num_frames = max(2, int(transition_duration / 0.033))  # 约30fps
            
            for frame_idx in range(num_frames):
                t = frame_idx / (num_frames - 1) if num_frames > 1 else 1.0
                
                # 应用缓动函数
                eased_t = await self._apply_easing_function(t, "smooth")
                
                # 插值权重
                frame_weights = await self._interpolate_weights(start_weights, end_weights, eased_t)
                transition_frames.append(frame_weights)
            
            # 缓存过渡序列
            viseme_frames = []
            for i, weights in enumerate(transition_frames):
                frame_duration = transition_duration / len(transition_frames)
                viseme_data = VisemeData(
                    viseme_type=VisemeType.A,  # 过渡类型不重要
                    weights=weights,
                    duration=frame_duration,
                    intensity=1.0,
                    emotion_modifiers={}
                )
                viseme_frames.append(viseme_data)
            
            self.transition_cache[cache_key] = viseme_frames
            
            logger.debug(f"Generated viseme transition: {from_phoneme} -> {to_phoneme} "
                        f"({len(transition_frames)} frames)")
            
            return transition_frames
            
        except Exception as e:
            logger.error(f"Error generating viseme transition: {e}")
            # 返回简单的直接过渡
            start_weights = await self.generate_viseme(from_phoneme, 0.2, emotion)
            end_weights = await self.generate_viseme(to_phoneme, 0.2, emotion)
            return [start_weights, end_weights]

    async def _apply_easing_function(self, t: float, easing_type: str) -> float:
        """应用缓动函数"""
        try:
            if easing_type == "linear":
                return t
            elif easing_type == "smooth":
                # 平滑缓动: 3t² - 2t³
                return 3 * t * t - 2 * t * t * t
            elif easing_type == "ease_in":
                # 缓入: t²
                return t * t
            elif easing_type == "ease_out":
                # 缓出: 1 - (1-t)²
                return 1 - (1 - t) * (1 - t)
            elif easing_type == "ease_in_out":
                # 缓入缓出
                if t < 0.5:
                    return 2 * t * t
                else:
                    return -1 + (4 - 2 * t) * t
            else:
                return t
                
        except Exception as e:
            logger.warning(f"Error applying easing function: {e}")
            return t

    async def _interpolate_weights(self, start_weights: Dict[str, float], 
                                 end_weights: Dict[str, float], t: float) -> Dict[str, float]:
        """插值权重"""
        try:
            interpolated_weights = {}
            
            # 所有涉及的骨骼
            all_bones = set(start_weights.keys()) | set(end_weights.keys())
            
            for bone in all_bones:
                start_weight = start_weights.get(bone, 0.0)
                end_weight = end_weights.get(bone, 0.0)
                
                # 线性插值
                interpolated_weight = start_weight + (end_weight - start_weight) * t
                interpolated_weights[bone] = max(0.0, min(1.0, interpolated_weight))
            
            return interpolated_weights
            
        except Exception as e:
            logger.warning(f"Error interpolating weights: {e}")
            return start_weights if t < 0.5 else end_weights

    async def generate_emotional_viseme(self, phoneme: str, duration: float,
                                      emotion: EmotionType, intensity: float = 1.0) -> Dict[str, float]:
        """生成情感化视素"""
        try:
            # 获取基础视素权重
            base_weights = await self.generate_viseme(phoneme, duration, EmotionType.NEUTRAL)
            
            # 应用情感强度
            emotional_weights = {}
            for bone, weight in base_weights.items():
                # 根据情感类型和强度调整权重
                emotional_factor = await self._calculate_emotional_factor(bone, emotion, intensity)
                emotional_weights[bone] = weight * emotional_factor
            
            # 归一化
            emotional_weights = await self._normalize_weights(emotional_weights)
            
            return emotional_weights
            
        except Exception as e:
            logger.error(f"Error generating emotional viseme: {e}")
            return await self.generate_viseme(phoneme, duration, emotion)

    async def _calculate_emotional_factor(self, bone: str, emotion: EmotionType, 
                                        intensity: float) -> float:
        """计算情感因子"""
        try:
            base_factor = 1.0
            
            if emotion == EmotionType.HAPPY:
                # 开心：嘴角上扬，眼睛微眯
                if "corner" in bone:
                    base_factor += 0.3 * intensity
                elif "eye" in bone:
                    base_factor -= 0.2 * intensity
                    
            elif emotion == EmotionType.SAD:
                # 悲伤：嘴角下拉，眉毛下垂
                if "corner" in bone:
                    base_factor -= 0.3 * intensity
                elif "brow" in bone:
                    base_factor += 0.2 * intensity
                    
            elif emotion == EmotionType.ANGRY:
                # 愤怒：眉毛紧皱，嘴唇紧绷
                if "brow" in bone:
                    base_factor += 0.4 * intensity
                elif "lip" in bone:
                    base_factor += 0.2 * intensity
                    
            elif emotion == EmotionType.SURPRISED:
                # 惊讶：眼睛睁大，嘴巴张开
                if "eye" in bone:
                    base_factor += 0.5 * intensity
                elif "jaw" in bone:
                    base_factor += 0.3 * intensity
            
            return max(0.1, base_factor)  # 确保最小因子
            
        except Exception as e:
            logger.warning(f"Error calculating emotional factor: {e}")
            return 1.0

    async def create_custom_viseme(self, viseme_id: str, weights: Dict[str, float],
                                 duration: float = 0.2, intensity: float = 1.0) -> bool:
        """创建自定义视素"""
        try:
            # 创建新的视素类型
            custom_viseme_type = VisemeType(viseme_id.upper())
            
            custom_viseme = VisemeData(
                viseme_type=custom_viseme_type,
                weights=weights,
                duration=duration,
                intensity=intensity,
                emotion_modifiers={}
            )
            
            # 添加到数据库
            self.viseme_database[custom_viseme_type] = custom_viseme
            
            logger.info(f"Custom viseme created: {viseme_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom viseme: {e}")
            return False

    async def get_viseme_info(self, viseme_type: VisemeType) -> Optional[VisemeData]:
        """获取视素信息"""
        return self.viseme_database.get(viseme_type)

    async def get_available_visemes(self) -> List[VisemeType]:
        """获取可用视素列表"""
        return list(self.viseme_database.keys())

    async def export_viseme_database(self, export_path: str) -> bool:
        """导出视素数据库"""
        try:
            export_data = {}
            
            for viseme_type, viseme_data in self.viseme_database.items():
                export_data[viseme_type.value] = {
                    "weights": viseme_data.weights,
                    "duration": viseme_data.duration,
                    "intensity": viseme_data.intensity,
                    "emotion_modifiers": viseme_data.emotion_modifiers
                }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Viseme database exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting viseme database: {e}")
            return False

    async def import_viseme_database(self, import_path: str) -> bool:
        """导入视素数据库"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            for viseme_str, viseme_info in import_data.items():
                try:
                    viseme_type = VisemeType(viseme_str)
                    
                    viseme_data = VisemeData(
                        viseme_type=viseme_type,
                        weights=viseme_info.get("weights", {}),
                        duration=viseme_info.get("duration", 0.2),
                        intensity=viseme_info.get("intensity", 1.0),
                        emotion_modifiers=viseme_info.get("emotion_modifiers", {})
                    )
                    
                    self.viseme_database[viseme_type] = viseme_data
                    
                except ValueError:
                    logger.warning(f"Unknown viseme type in import: {viseme_str}")
            
            logger.info(f"Viseme database imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing viseme database: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["viseme_database_size"] = len(self.viseme_database)
        stats["phoneme_mapping_size"] = len(self.phoneme_viseme_map)
        stats["cache_size"] = len(self.viseme_cache)
        stats["transition_cache_size"] = len(self.transition_cache)
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.viseme_cache.clear()
            self.transition_cache.clear()
            
            logger.info("VisemeGenerator cleaned up")
            
        except Exception as e:
            logger.error(f"Error during VisemeGenerator cleanup: {e}")

# 全局视素生成器实例（根据需要创建）
# viseme_generator = VisemeGenerator(model_instance)