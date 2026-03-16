"""
语音动画映射系统 - 建立语音特征与动画参数的映射关系
完整实现音素到视素的映射、情感参数映射和个性化语音动画适配
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import json
from pathlib import Path
import hashlib
from enum import Enum

# 导入依赖
from interaction.output_systems.speech_output.multilingual_tts import EmotionType, VoiceProfile
from interaction.threed_avatar.character_system.skeleton_animation import BoneTransform

logger = logging.getLogger(__name__)

class MappingType(Enum):
    """映射类型枚举"""
    PHONEME_TO_VISEME = "phoneme_to_viseme"
    EMOTION_TO_EXPRESSION = "emotion_to_expression"
    VOICE_TO_ANIMATION = "voice_to_animation"
    AUDIO_TO_MOTION = "audio_to_motion"

@dataclass
class AnimationParameter:
    """动画参数"""
    bone_name: str
    parameter_type: str  # position, rotation, scale, weight
    min_value: float
    max_value: float
    default_value: float
    influence: float = 1.0

@dataclass
class VoiceAnimationMapping:
    """语音动画映射"""
    mapping_id: str
    mapping_type: MappingType
    source_parameter: str
    target_parameters: List[AnimationParameter]
    mapping_function: str  # linear, exponential, logarithmic, custom
    mapping_curve: List[Tuple[float, float]]  # 映射曲线控制点

class VoiceAnimationMap:
    """语音动画映射系统 - 完整实现"""
    
    def __init__(self, mapping_config_path: str = "config/voice_animation_mappings.json"):
        self.mappings: Dict[str, VoiceAnimationMapping] = {}
        self.mapping_cache: Dict[str, Dict[str, float]] = {}
        self.phoneme_viseme_map: Dict[str, List[str]] = {}
        self.emotion_expression_map: Dict[str, Dict[str, float]] = {}
        self.voice_animation_profiles: Dict[str, Dict[str, Any]] = {}
        
        # 统计信息
        self.stats = {
            "mapping_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "custom_mappings": 0,
            "average_mapping_time": 0.0
        }
        
        # 加载映射配置
        self._load_mapping_config(mapping_config_path)
        
        # 初始化默认映射
        self._initialize_default_mappings()
        
        logger.info("VoiceAnimationMap initialized")

    def _load_mapping_config(self, config_path: str):
        """加载映射配置"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 加载音素-视素映射
                self.phoneme_viseme_map = config_data.get("phoneme_viseme_map", {})
                
                # 加载情感-表情映射
                self.emotion_expression_map = config_data.get("emotion_expression_map", {})
                
                # 加载语音-动画配置
                self.voice_animation_profiles = config_data.get("voice_animation_profiles", {})
                
                logger.info(f"Mapping configuration loaded from {config_path}")
            else:
                logger.warning(f"Mapping config file not found: {config_path}")
                self._create_default_config(config_path)
                
        except Exception as e:
            logger.error(f"Error loading mapping config: {e}")
            self._create_default_config(config_path)

    def _create_default_config(self, config_path: str):
        """创建默认配置"""
        try:
            # 创建配置目录
            config_dir = Path(config_path).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # 默认音素-视素映射（基于国际音标）
            self.phoneme_viseme_map = {
                # 元音
                "a": ["A", "open"], "ɑ": ["A", "open"], "æ": ["A", "wide"],
                "e": ["E", "mid"], "ɛ": ["E", "mid"], "ə": ["E", "neutral"],
                "i": ["I", "close"], "ɪ": ["I", "close"],
                "o": ["O", "round"], "ɔ": ["O", "round"], 
                "u": ["U", "close_round"], "ʊ": ["U", "close_round"],
                
                # 辅音
                "p": ["P", "bilabial"], "b": ["B", "bilabial"],
                "t": ["T", "alveolar"], "d": ["D", "alveolar"],
                "k": ["K", "velar"], "g": ["G", "velar"],
                "f": ["F", "labiodental"], "v": ["V", "labiodental"],
                "s": ["S", "alveolar"], "z": ["Z", "alveolar"],
                "ʃ": ["SH", "postalveolar"], "ʒ": ["ZH", "postalveolar"],
                "m": ["M", "bilabial"], "n": ["N", "alveolar"],
                "l": ["L", "alveolar"], "r": ["R", "alveolar"],
                "w": ["W", "labiovelar"], "j": ["J", "palatal"],
                
                # 静音
                "sil": ["silence", "neutral"]
            }
            
            # 默认情感-表情映射
            self.emotion_expression_map = {
                "neutral": {
                    "brow_raise": 0.0, "brow_furrow": 0.0, "smile": 0.0,
                    "frown": 0.0, "mouth_open": 0.3, "eyes_wide": 0.0
                },
                "happy": {
                    "brow_raise": 0.2, "brow_furrow": 0.0, "smile": 0.8,
                    "frown": 0.0, "mouth_open": 0.4, "eyes_wide": 0.3
                },
                "sad": {
                    "brow_raise": 0.0, "brow_furrow": 0.6, "smile": 0.0,
                    "frown": 0.7, "mouth_open": 0.2, "eyes_wide": 0.1
                },
                "angry": {
                    "brow_raise": 0.0, "brow_furrow": 0.9, "smile": 0.0,
                    "frown": 0.8, "mouth_open": 0.5, "eyes_wide": 0.6
                },
                "excited": {
                    "brow_raise": 0.4, "brow_furrow": 0.0, "smile": 0.7,
                    "frown": 0.0, "mouth_open": 0.6, "eyes_wide": 0.8
                },
                "calm": {
                    "brow_raise": 0.1, "brow_furrow": 0.0, "smile": 0.3,
                    "frown": 0.0, "mouth_open": 0.2, "eyes_wide": 0.0
                },
                "surprised": {
                    "brow_raise": 0.8, "brow_furrow": 0.0, "smile": 0.1,
                    "frown": 0.0, "mouth_open": 0.9, "eyes_wide": 1.0
                },
                "fearful": {
                    "brow_raise": 0.6, "brow_furrow": 0.3, "smile": 0.0,
                    "frown": 0.4, "mouth_open": 0.7, "eyes_wide": 0.9
                }
            }
            
            # 保存配置
            config_data = {
                "phoneme_viseme_map": self.phoneme_viseme_map,
                "emotion_expression_map": self.emotion_expression_map,
                "voice_animation_profiles": self.voice_animation_profiles
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Default mapping configuration created at {config_path}")
            
        except Exception as e:
            logger.error(f"Error creating default mapping config: {e}")

    def _initialize_default_mappings(self):
        """初始化默认映射"""
        try:
            # 音素到视素的默认映射
            phoneme_mapping = VoiceAnimationMapping(
                mapping_id="phoneme_to_viseme_default",
                mapping_type=MappingType.PHONEME_TO_VISEME,
                source_parameter="phoneme",
                target_parameters=[
                    AnimationParameter("jaw", "position", -0.1, 0.1, 0.0, 0.8),
                    AnimationParameter("mouth_upper_lip", "position", -0.05, 0.05, 0.0, 0.6),
                    AnimationParameter("mouth_lower_lip", "position", -0.05, 0.05, 0.0, 0.7),
                    AnimationParameter("mouth_left_corner", "position", -0.1, 0.1, 0.0, 0.5),
                    AnimationParameter("mouth_right_corner", "position", -0.1, 0.1, 0.0, 0.5)
                ],
                mapping_function="linear",
                mapping_curve=[(0.0, 0.0), (1.0, 1.0)]
            )
            self.mappings[phoneme_mapping.mapping_id] = phoneme_mapping
            
            # 情感到表情的默认映射
            emotion_mapping = VoiceAnimationMapping(
                mapping_id="emotion_to_expression_default",
                mapping_type=MappingType.EMOTION_TO_EXPRESSION,
                source_parameter="emotion_intensity",
                target_parameters=[
                    AnimationParameter("brow_left", "position", -0.02, 0.02, 0.0, 0.7),
                    AnimationParameter("brow_right", "position", -0.02, 0.02, 0.0, 0.7),
                    AnimationParameter("eye_left", "scale", 0.8, 1.2, 1.0, 0.6),
                    AnimationParameter("eye_right", "scale", 0.8, 1.2, 1.0, 0.6)
                ],
                mapping_function="exponential",
                mapping_curve=[(0.0, 0.0), (0.5, 0.3), (1.0, 1.0)]
            )
            self.mappings[emotion_mapping.mapping_id] = emotion_mapping
            
            logger.info("Default mappings initialized")
            
        except Exception as e:
            logger.error(f"Error initializing default mappings: {e}")

    async def map_phoneme_to_viseme(self, phoneme: str, duration: float = 0.2, 
                                  emotion: EmotionType = EmotionType.NEUTRAL) -> Dict[str, float]:
        """映射音素到视素"""
        import time
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"phoneme_{phoneme}_duration_{duration}_emotion_{emotion.value}"
            if cache_key in self.mapping_cache:
                self.stats["cache_hits"] += 1
                return self.mapping_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            self.stats["mapping_operations"] += 1
            
            # 获取基础视素映射
            viseme_weights = await self._get_base_viseme_weights(phoneme)
            
            # 应用持续时间影响
            viseme_weights = await self._apply_duration_influence(viseme_weights, duration)
            
            # 应用情感影响
            viseme_weights = await self._apply_emotion_influence(viseme_weights, emotion)
            
            # 归一化权重
            viseme_weights = await self._normalize_weights(viseme_weights)
            
            # 缓存结果
            self.mapping_cache[cache_key] = viseme_weights
            
            # 更新统计
            mapping_time = time.time() - start_time
            self.stats["average_mapping_time"] = (
                (self.stats["average_mapping_time"] * (self.stats["mapping_operations"] - 1) + mapping_time) 
                / self.stats["mapping_operations"]
            )
            
            logger.debug(f"Phoneme '{phoneme}' mapped to viseme weights: {viseme_weights}")
            return viseme_weights
            
        except Exception as e:
            logger.error(f"Error mapping phoneme to viseme: {e}")
            return await self._get_default_viseme_weights()

    async def _get_base_viseme_weights(self, phoneme: str) -> Dict[str, float]:
        """获取基础视素权重"""
        try:
            # 从配置中获取音素对应的视素
            if phoneme in self.phoneme_viseme_map:
                viseme_types = self.phoneme_viseme_map[phoneme]
                
                # 为每个视素类型分配权重
                weights = {}
                for i, viseme_type in enumerate(viseme_types):
                    # 主要视素权重较高，次要视素权重较低
                    weight = 1.0 - (i * 0.3)
                    weights[viseme_type] = max(0.1, weight)
                
                return weights
            else:
                # 未知音素，使用中性口型
                return {"neutral": 0.5, "A": 0.3}
                
        except Exception as e:
            logger.warning(f"Error getting base viseme weights for {phoneme}: {e}")
            return {"neutral": 0.5}

    async def _apply_duration_influence(self, viseme_weights: Dict[str, float], duration: float) -> Dict[str, float]:
        """应用持续时间影响"""
        try:
            adjusted_weights = viseme_weights.copy()
            
            # 根据持续时间调整权重强度
            # 短音素：权重更集中；长音素：权重更分散
            duration_factor = min(1.0, duration / 0.3)  # 0.3秒为标准持续时间
            
            for viseme in adjusted_weights:
                if duration_factor < 0.5:
                    # 短音素：增强主要视素，减弱次要视素
                    if adjusted_weights[viseme] > 0.5:
                        adjusted_weights[viseme] = min(1.0, adjusted_weights[viseme] * (1.0 + (0.5 - duration_factor)))
                    else:
                        adjusted_weights[viseme] = max(0.0, adjusted_weights[viseme] * duration_factor)
                else:
                    # 长音素：权重更平均
                    adjusted_weights[viseme] = (adjusted_weights[viseme] + 0.3) / 1.3
            
            return adjusted_weights
            
        except Exception as e:
            logger.warning(f"Error applying duration influence: {e}")
            return viseme_weights

    async def _apply_emotion_influence(self, viseme_weights: Dict[str, float], emotion: EmotionType) -> Dict[str, float]:
        """应用情感影响"""
        try:
            if emotion == EmotionType.NEUTRAL:
                return viseme_weights
            
            adjusted_weights = viseme_weights.copy()
            emotion_key = emotion.value
            
            if emotion_key in self.emotion_expression_map:
                emotion_params = self.emotion_expression_map[emotion_key]
                
                # 根据情感调整视素权重
                for expression, intensity in emotion_params.items():
                    if expression == "smile" and intensity > 0:
                        # 微笑：增强开口类视素，减弱闭口类视素
                        for viseme in ["A", "E", "I"]:
                            if viseme in adjusted_weights:
                                adjusted_weights[viseme] = min(1.0, adjusted_weights[viseme] * (1.0 + intensity * 0.3))
                        
                        for viseme in ["M", "P", "B"]:
                            if viseme in adjusted_weights:
                                adjusted_weights[viseme] = max(0.0, adjusted_weights[viseme] * (1.0 - intensity * 0.2))
                    
                    elif expression == "frown" and intensity > 0:
                        # 皱眉：减弱开口类视素
                        for viseme in ["A", "E", "O"]:
                            if viseme in adjusted_weights:
                                adjusted_weights[viseme] = max(0.0, adjusted_weights[viseme] * (1.0 - intensity * 0.2))
            
            return adjusted_weights
            
        except Exception as e:
            logger.warning(f"Error applying emotion influence: {e}")
            return viseme_weights

    async def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """归一化权重"""
        try:
            total_weight = sum(weights.values())
            if total_weight > 0:
                normalized = {k: v / total_weight for k, v in weights.items()}
            else:
                normalized = weights.copy()
            
            # 确保至少有一个视素有权重
            if not normalized or max(normalized.values()) < 0.1:
                normalized["neutral"] = 0.5
                normalized["A"] = 0.3
            
            return normalized
            
        except Exception as e:
            logger.warning(f"Error normalizing weights: {e}")
            return weights

    async def map_emotion_to_expression(self, emotion: EmotionType, intensity: float = 1.0) -> Dict[str, float]:
        """映射情感到表情"""
        try:
            emotion_key = emotion.value
            
            if emotion_key in self.emotion_expression_map:
                base_expression = self.emotion_expression_map[emotion_key].copy()
                
                # 应用强度
                for param in base_expression:
                    base_expression[param] = base_expression[param] * intensity
                
                return base_expression
            else:
                return self.emotion_expression_map["neutral"].copy()
                
        except Exception as e:
            logger.error(f"Error mapping emotion to expression: {e}")
            return self.emotion_expression_map["neutral"].copy()

    async def map_voice_to_animation(self, voice_profile: VoiceProfile, text: str) -> Dict[str, Any]:
        """映射语音特征到动画参数"""
        try:
            animation_params = {}
            
            # 基于语音特征生成个性化动画参数
            animation_params["speaking_rate"] = voice_profile.speed
            animation_params["pitch_variation"] = voice_profile.pitch
            animation_params["energy_level"] = voice_profile.energy
            
            # 基于语音特征调整口型幅度
            amplitude_factor = voice_profile.energy * 0.5 + 0.5  # 0.5-1.5
            animation_params["amplitude_multiplier"] = amplitude_factor
            
            # 基于音调调整口型开合度
            openness_factor = 1.0 + (voice_profile.pitch - 1.0) * 0.3  # 0.85-1.15
            animation_params["openness_multiplier"] = openness_factor
            
            # 基于语速调整过渡速度
            transition_factor = 0.5 + voice_profile.speed * 0.5  # 0.5-1.5
            animation_params["transition_speed"] = transition_factor
            
            self.stats["custom_mappings"] += 1
            
            return animation_params
            
        except Exception as e:
            logger.error(f"Error mapping voice to animation: {e}")
            return {
                "amplitude_multiplier": 1.0,
                "openness_multiplier": 1.0,
                "transition_speed": 1.0
            }

    async def map_audio_to_motion(self, audio_features: Dict[str, float]) -> Dict[str, float]:
        """映射音频特征到运动参数"""
        try:
            motion_params = {}
            
            # 基于音频能量生成头部运动
            energy = audio_features.get("rms_energy", 0.0)
            motion_params["head_nod"] = min(1.0, energy * 5.0)  # 能量越大，点头幅度越大
            
            # 基于频谱重心生成头部倾斜
            spectral_centroid = audio_features.get("spectral_centroid", 0.0)
            motion_params["head_tilt"] = max(-1.0, min(1.0, (spectral_centroid - 0.5) * 2.0))
            
            # 基于过零率生成眨眼频率
            zero_crossing = audio_features.get("zero_crossing_rate", 0.0)
            motion_params["blink_frequency"] = min(1.0, zero_crossing * 3.0)
            
            return motion_params
            
        except Exception as e:
            logger.error(f"Error mapping audio to motion: {e}")
            return {
                "head_nod": 0.0,
                "head_tilt": 0.0,
                "blink_frequency": 0.2
            }

    async def create_custom_mapping(self, mapping_id: str, mapping_type: MappingType,
                                 source_parameter: str, target_parameters: List[AnimationParameter],
                                 mapping_function: str = "linear", 
                                 mapping_curve: List[Tuple[float, float]] = None) -> bool:
        """创建自定义映射"""
        try:
            if mapping_curve is None:
                mapping_curve = [(0.0, 0.0), (1.0, 1.0)]
            
            custom_mapping = VoiceAnimationMapping(
                mapping_id=mapping_id,
                mapping_type=mapping_type,
                source_parameter=source_parameter,
                target_parameters=target_parameters,
                mapping_function=mapping_function,
                mapping_curve=mapping_curve
            )
            
            self.mappings[mapping_id] = custom_mapping
            self.stats["custom_mappings"] += 1
            
            logger.info(f"Custom mapping created: {mapping_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom mapping: {e}")
            return False

    async def apply_mapping(self, mapping_id: str, input_value: float) -> Dict[str, float]:
        """应用映射"""
        try:
            if mapping_id not in self.mappings:
                logger.error(f"Mapping not found: {mapping_id}")
                return {}
            
            mapping = self.mappings[mapping_id]
            output_params = {}
            
            # 根据映射函数计算输出值
            for param in mapping.target_parameters:
                mapped_value = await self._apply_mapping_function(
                    input_value, param.min_value, param.max_value,
                    mapping.mapping_function, mapping.mapping_curve
                )
                
                output_params[param.bone_name] = mapped_value * param.influence
            
            return output_params
            
        except Exception as e:
            logger.error(f"Error applying mapping {mapping_id}: {e}")
            return {}

    async def _apply_mapping_function(self, input_value: float, min_output: float, max_output: float,
                                   mapping_function: str, mapping_curve: List[Tuple[float, float]]) -> float:
        """应用映射函数"""
        try:
            # 确保输入在0-1范围内
            normalized_input = max(0.0, min(1.0, input_value))
            
            if mapping_function == "linear":
                # 线性映射
                output = normalized_input
            elif mapping_function == "exponential":
                # 指数映射
                output = normalized_input ** 2
            elif mapping_function == "logarithmic":
                # 对数映射
                output = np.log1p(normalized_input * 9) / np.log1p(9)  # log(1 + 9x) / log(10)
            elif mapping_function == "custom":
                # 自定义曲线映射
                output = await self._apply_custom_curve(normalized_input, mapping_curve)
            else:
                output = normalized_input
            
            # 缩放到输出范围
            scaled_output = min_output + output * (max_output - min_output)
            return scaled_output
            
        except Exception as e:
            logger.warning(f"Error applying mapping function: {e}")
            return min_output

    async def _apply_custom_curve(self, input_value: float, curve_points: List[Tuple[float, float]]) -> float:
        """应用自定义曲线"""
        try:
            if len(curve_points) < 2:
                return input_value
            
            # 找到输入值所在的区间
            for i in range(len(curve_points) - 1):
                x1, y1 = curve_points[i]
                x2, y2 = curve_points[i + 1]
                
                if x1 <= input_value <= x2:
                    # 线性插值
                    t = (input_value - x1) / (x2 - x1) if x2 > x1 else 0.0
                    return y1 + t * (y2 - y1)
            
            # 如果超出范围，使用端点值
            if input_value <= curve_points[0][0]:
                return curve_points[0][1]
            else:
                return curve_points[-1][1]
                
        except Exception as e:
            logger.warning(f"Error applying custom curve: {e}")
            return input_value

    async def _get_default_viseme_weights(self) -> Dict[str, float]:
        """获取默认视素权重"""
        return {"neutral": 0.6, "A": 0.2, "E": 0.1, "O": 0.1}

    async def export_mappings(self, export_path: str) -> bool:
        """导出映射配置"""
        try:
            export_data = {
                "mappings": {},
                "phoneme_viseme_map": self.phoneme_viseme_map,
                "emotion_expression_map": self.emotion_expression_map,
                "voice_animation_profiles": self.voice_animation_profiles,
                "stats": self.stats
            }
            
            # 转换映射对象为字典
            for mapping_id, mapping in self.mappings.items():
                export_data["mappings"][mapping_id] = {
                    "mapping_type": mapping.mapping_type.value,
                    "source_parameter": mapping.source_parameter,
                    "target_parameters": [param.__dict__ for param in mapping.target_parameters],
                    "mapping_function": mapping.mapping_function,
                    "mapping_curve": mapping.mapping_curve
                }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Mappings exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting mappings: {e}")
            return False

    async def import_mappings(self, import_path: str) -> bool:
        """导入映射配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 清空现有映射
            self.mappings.clear()
            
            # 导入映射
            for mapping_id, mapping_data in import_data.get("mappings", {}).items():
                target_params = []
                for param_data in mapping_data.get("target_parameters", []):
                    target_params.append(AnimationParameter(**param_data))
                
                mapping = VoiceAnimationMapping(
                    mapping_id=mapping_id,
                    mapping_type=MappingType(mapping_data["mapping_type"]),
                    source_parameter=mapping_data["source_parameter"],
                    target_parameters=target_params,
                    mapping_function=mapping_data["mapping_function"],
                    mapping_curve=[tuple(point) for point in mapping_data["mapping_curve"]]
                )
                self.mappings[mapping_id] = mapping
            
            # 导入其他配置
            self.phoneme_viseme_map = import_data.get("phoneme_viseme_map", {})
            self.emotion_expression_map = import_data.get("emotion_expression_map", {})
            self.voice_animation_profiles = import_data.get("voice_animation_profiles", {})
            
            # 导入统计
            self.stats.update(import_data.get("stats", {}))
            
            logger.info(f"Mappings imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing mappings: {e}")
            return False

    def get_available_mappings(self) -> List[str]:
        """获取可用映射列表"""
        return list(self.mappings.keys())

    def get_mapping_info(self, mapping_id: str) -> Optional[Dict[str, Any]]:
        """获取映射信息"""
        if mapping_id in self.mappings:
            mapping = self.mappings[mapping_id]
            return {
                "mapping_id": mapping.mapping_id,
                "mapping_type": mapping.mapping_type.value,
                "source_parameter": mapping.source_parameter,
                "target_parameters_count": len(mapping.target_parameters),
                "mapping_function": mapping.mapping_function
            }
        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["total_mappings"] = len(self.mappings)
        stats["cache_size"] = len(self.mapping_cache)
        stats["phoneme_count"] = len(self.phoneme_viseme_map)
        stats["emotion_count"] = len(self.emotion_expression_map)
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.mapping_cache.clear()
            logger.info("VoiceAnimationMap cleaned up")
            
        except Exception as e:
            logger.error(f"Error during VoiceAnimationMap cleanup: {e}")

# 全局语音动画映射实例
voice_animation_map = VoiceAnimationMap()

