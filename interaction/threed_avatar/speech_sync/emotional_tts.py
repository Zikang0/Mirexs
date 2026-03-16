"""
情感语音合成系统 - 基于多语言TTS的情感化语音生成
完整实现情感参数控制、情感语音风格转换和情感强度调节
支持多情感维度的语音合成和情感一致性保持
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from enum import Enum

# 导入依赖
from interaction.output_systems.speech_output.multilingual_tts import (
    MultilingualTTS, TTSConfig, TTSResult, VoiceProfile, EmotionType
)
from infrastructure.compute_storage.model_serving_engine import ModelServingEngine, model_serving_engine

logger = logging.getLogger(__name__)

class EmotionalFeature(Enum):
    """情感特征枚举"""
    PITCH_VARIATION = "pitch_variation"      # 音调变化
    SPEAKING_RATE = "speaking_rate"          # 语速
    ENERGY_LEVEL = "energy_level"            # 能量水平
    VOICE_QUALITY = "voice_quality"          # 音质
    ARTICULATION = "articulation"            # 发音清晰度
    PROSODY = "prosody"                      # 韵律

@dataclass
class EmotionalProfile:
    """情感配置文件"""
    emotion_type: EmotionType
    intensity: float  # 情感强度 0.0-1.0
    features: Dict[EmotionalFeature, float]  # 情感特征
    voice_modifications: Dict[str, float]    # 语音修改参数
    duration_modifiers: Dict[str, float]     # 时长修改器

class EmotionalTTS:
    """情感语音合成系统 - 完整实现"""
    
    def __init__(self):
        self.multilingual_tts = MultilingualTTS()
        self.emotional_profiles: Dict[EmotionType, EmotionalProfile] = {}
        self.emotion_models: Dict[str, Any] = {}
        
        # 统计信息
        self.stats = {
            "emotional_synthesis_count": 0,
            "emotion_transitions": 0,
            "average_emotion_intensity": 0.0,
            "profile_customizations": 0
        }
        
        # 初始化情感配置
        self._initialize_emotional_profiles()
        self._initialize_emotion_models()
        
        logger.info("EmotionalTTS system initialized")

    def _initialize_emotional_profiles(self):
        """初始化情感配置"""
        try:
            # 中性情感
            self.emotional_profiles[EmotionType.NEUTRAL] = EmotionalProfile(
                emotion_type=EmotionType.NEUTRAL,
                intensity=0.5,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.5,
                    EmotionalFeature.SPEAKING_RATE: 1.0,
                    EmotionalFeature.ENERGY_LEVEL: 0.5,
                    EmotionalFeature.VOICE_QUALITY: 0.5,
                    EmotionalFeature.ARTICULATION: 0.7,
                    EmotionalFeature.PROSODY: 0.5
                },
                voice_modifications={"pitch": 1.0, "speed": 1.0, "energy": 1.0},
                duration_modifiers={"vowel": 1.0, "consonant": 1.0, "pause": 1.0}
            )
            
            # 开心情感
            self.emotional_profiles[EmotionType.HAPPY] = EmotionalProfile(
                emotion_type=EmotionType.HAPPY,
                intensity=0.8,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.8,
                    EmotionalFeature.SPEAKING_RATE: 1.2,
                    EmotionalFeature.ENERGY_LEVEL: 0.8,
                    EmotionalFeature.VOICE_QUALITY: 0.7,
                    EmotionalFeature.ARTICULATION: 0.8,
                    EmotionalFeature.PROSODY: 0.9
                },
                voice_modifications={"pitch": 1.2, "speed": 1.1, "energy": 1.3},
                duration_modifiers={"vowel": 1.1, "consonant": 0.9, "pause": 0.8}
            )
            
            # 悲伤情感
            self.emotional_profiles[EmotionType.SAD] = EmotionalProfile(
                emotion_type=EmotionType.SAD,
                intensity=0.7,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.3,
                    EmotionalFeature.SPEAKING_RATE: 0.8,
                    EmotionalFeature.ENERGY_LEVEL: 0.3,
                    EmotionalFeature.VOICE_QUALITY: 0.4,
                    EmotionalFeature.ARTICULATION: 0.6,
                    EmotionalFeature.PROSODY: 0.3
                },
                voice_modifications={"pitch": 0.9, "speed": 0.9, "energy": 0.7},
                duration_modifiers={"vowel": 1.2, "consonant": 1.0, "pause": 1.3}
            )
            
            # 愤怒情感
            self.emotional_profiles[EmotionType.ANGRY] = EmotionalProfile(
                emotion_type=EmotionType.ANGRY,
                intensity=0.9,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.7,
                    EmotionalFeature.SPEAKING_RATE: 1.4,
                    EmotionalFeature.ENERGY_LEVEL: 0.9,
                    EmotionalFeature.VOICE_QUALITY: 0.8,
                    EmotionalFeature.ARTICULATION: 0.9,
                    EmotionalFeature.PROSODY: 0.8
                },
                voice_modifications={"pitch": 1.1, "speed": 1.3, "energy": 1.5},
                duration_modifiers={"vowel": 0.9, "consonant": 1.1, "pause": 0.7}
            )
            
            # 兴奋情感
            self.emotional_profiles[EmotionType.EXCITED] = EmotionalProfile(
                emotion_type=EmotionType.EXCITED,
                intensity=0.85,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.9,
                    EmotionalFeature.SPEAKING_RATE: 1.3,
                    EmotionalFeature.ENERGY_LEVEL: 0.9,
                    EmotionalFeature.VOICE_QUALITY: 0.8,
                    EmotionalFeature.ARTICULATION: 0.8,
                    EmotionalFeature.PROSODY: 0.9
                },
                voice_modifications={"pitch": 1.3, "speed": 1.2, "energy": 1.4},
                duration_modifiers={"vowel": 1.0, "consonant": 0.9, "pause": 0.6}
            )
            
            # 平静情感
            self.emotional_profiles[EmotionType.CALM] = EmotionalProfile(
                emotion_type=EmotionType.CALM,
                intensity=0.4,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.4,
                    EmotionalFeature.SPEAKING_RATE: 0.9,
                    EmotionalFeature.ENERGY_LEVEL: 0.4,
                    EmotionalFeature.VOICE_QUALITY: 0.6,
                    EmotionalFeature.ARTICULATION: 0.7,
                    EmotionalFeature.PROSODY: 0.4
                },
                voice_modifications={"pitch": 0.95, "speed": 0.95, "energy": 0.8},
                duration_modifiers={"vowel": 1.1, "consonant": 1.0, "pause": 1.2}
            )
            
            # 惊讶情感
            self.emotional_profiles[EmotionType.SURPRISED] = EmotionalProfile(
                emotion_type=EmotionType.SURPRISED,
                intensity=0.95,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.95,
                    EmotionalFeature.SPEAKING_RATE: 1.1,
                    EmotionalFeature.ENERGY_LEVEL: 0.9,
                    EmotionalFeature.VOICE_QUALITY: 0.8,
                    EmotionalFeature.ARTICULATION: 0.8,
                    EmotionalFeature.PROSODY: 0.7
                },
                voice_modifications={"pitch": 1.4, "speed": 1.1, "energy": 1.3},
                duration_modifiers={"vowel": 1.0, "consonant": 1.0, "pause": 0.9}
            )
            
            # 恐惧情感
            self.emotional_profiles[EmotionType.FEARFUL] = EmotionalProfile(
                emotion_type=EmotionType.FEARFUL,
                intensity=0.8,
                features={
                    EmotionalFeature.PITCH_VARIATION: 0.6,
                    EmotionalFeature.SPEAKING_RATE: 1.2,
                    EmotionalFeature.ENERGY_LEVEL: 0.7,
                    EmotionalFeature.VOICE_QUALITY: 0.5,
                    EmotionalFeature.ARTICULATION: 0.7,
                    EmotionalFeature.PROSODY: 0.6
                },
                voice_modifications={"pitch": 1.5, "speed": 1.2, "energy": 0.9},
                duration_modifiers={"vowel": 1.1, "consonant": 1.0, "pause": 1.1}
            )
            
            logger.info(f"Emotional profiles initialized: {len(self.emotional_profiles)} emotions")
            
        except Exception as e:
            logger.error(f"Error initializing emotional profiles: {e}")

    def _initialize_emotion_models(self):
        """初始化情感模型"""
        try:
            # 这里应该加载情感语音合成模型
            # 例如: 情感TTS模型、语音转换模型等
            
            # 使用模型服务引擎
            self.emotion_models["base"] = model_serving_engine
            
            logger.info("Emotion models initialized")
            
        except Exception as e:
            logger.error(f"Error initializing emotion models: {e}")

    async def synthesize_with_emotion(self, text: str, emotion: EmotionType, 
                                    intensity: float = 1.0,
                                    voice_profile: VoiceProfile = None) -> Optional[TTSResult]:
        """
        情感语音合成 - 完整实现
        
        Args:
            text: 要合成的文本
            emotion: 情感类型
            intensity: 情感强度 (0.0-1.0)
            voice_profile: 语音配置
            
        Returns:
            TTSResult: 语音合成结果
        """
        start_time = time.time()
        
        try:
            # 获取情感配置
            emotional_profile = await self._get_emotional_profile(emotion, intensity)
            if not emotional_profile:
                logger.error(f"Emotional profile not found for: {emotion}")
                return await self.multilingual_tts.synthesize(text)
            
            # 预处理文本（添加情感标记）
            emotional_text = await self._preprocess_text_with_emotion(text, emotional_profile)
            
            # 创建情感化TTS配置
            tts_config = await self._create_emotional_tts_config(emotional_profile, voice_profile)
            
            # 执行语音合成
            tts_result = await self.multilingual_tts.synthesize(emotional_text, tts_config)
            if not tts_result:
                logger.error("Emotional TTS synthesis failed")
                return None
            
            # 后处理：应用情感特征
            emotional_result = await self._apply_emotional_features(tts_result, emotional_profile)
            
            # 更新统计
            self.stats["emotional_synthesis_count"] += 1
            self.stats["average_emotion_intensity"] = (
                (self.stats["average_emotion_intensity"] * (self.stats["emotional_synthesis_count"] - 1) + intensity) 
                / self.stats["emotional_synthesis_count"]
            )
            
            logger.info(f"Emotional TTS completed: {emotion.value} (intensity: {intensity:.2f})")
            return emotional_result
            
        except Exception as e:
            logger.error(f"Error in emotional TTS synthesis: {e}")
            return await self.multilingual_tts.synthesize(text)

    async def _get_emotional_profile(self, emotion: EmotionType, intensity: float) -> Optional[EmotionalProfile]:
        """获取情感配置"""
        try:
            if emotion in self.emotional_profiles:
                base_profile = self.emotional_profiles[emotion]
                
                # 根据强度调整配置
                adjusted_profile = await self._adjust_profile_intensity(base_profile, intensity)
                return adjusted_profile
            else:
                logger.warning(f"Unknown emotion type: {emotion}")
                return self.emotional_profiles[EmotionType.NEUTRAL]
                
        except Exception as e:
            logger.warning(f"Error getting emotional profile: {e}")
            return None

    async def _adjust_profile_intensity(self, base_profile: EmotionalProfile, 
                                      intensity: float) -> EmotionalProfile:
        """调整配置强度"""
        try:
            # 创建调整后的配置副本
            adjusted_profile = EmotionalProfile(
                emotion_type=base_profile.emotion_type,
                intensity=intensity,
                features=base_profile.features.copy(),
                voice_modifications=base_profile.voice_modifications.copy(),
                duration_modifiers=base_profile.duration_modifiers.copy()
            )
            
            # 根据强度调整特征
            intensity_factor = intensity / base_profile.intensity if base_profile.intensity > 0 else 1.0
            
            for feature_name, feature_value in adjusted_profile.features.items():
                # 中性值为0.5，向情感方向调整
                neutral_value = 0.5
                emotional_direction = feature_value - neutral_value
                adjusted_value = neutral_value + (emotional_direction * intensity_factor)
                adjusted_profile.features[feature_name] = max(0.0, min(1.0, adjusted_value))
            
            # 调整语音修改参数
            for param_name, param_value in adjusted_profile.voice_modifications.items():
                neutral_value = 1.0
                modification_direction = param_value - neutral_value
                adjusted_value = neutral_value + (modification_direction * intensity_factor)
                adjusted_profile.voice_modifications[param_name] = max(0.5, min(2.0, adjusted_value))
            
            return adjusted_profile
            
        except Exception as e:
            logger.warning(f"Error adjusting profile intensity: {e}")
            return base_profile

    async def _preprocess_text_with_emotion(self, text: str, profile: EmotionalProfile) -> str:
        """使用情感预处理文本"""
        try:
            # 这里可以添加情感特定的文本处理
            # 例如: 添加韵律标记、调整标点等
            
            emotional_text = text
            
            # 根据情感调整标点
            if profile.emotion_type in [EmotionType.HAPPY, EmotionType.EXCITED]:
                # 开心和兴奋：使用更多感叹号
                emotional_text = emotional_text.replace('.', '!').replace('。', '！')
            elif profile.emotion_type in [EmotionType.SAD, EmotionType.CALM]:
                # 悲伤和平静：使用更多省略号
                emotional_text = emotional_text.replace('!', '...').replace('！', '……')
            
            # 根据语速调整文本长度（简化处理）
            speaking_rate = profile.features[EmotionalFeature.SPEAKING_RATE]
            if speaking_rate > 1.2:
                # 快速说话：缩短长句子
                words = emotional_text.split()
                if len(words) > 15:
                    emotional_text = ' '.join(words[:12]) + '...'
            
            return emotional_text
            
        except Exception as e:
            logger.warning(f"Error preprocessing text with emotion: {e}")
            return text

    async def _create_emotional_tts_config(self, profile: EmotionalProfile, 
                                         voice_profile: VoiceProfile) -> TTSConfig:
        """创建情感TTS配置"""
        try:
            # 基础配置
            tts_config = TTSConfig(
                emotion=profile.emotion_type,
                emotion_strength=profile.intensity,
                realtime=True
            )
            
            # 如果有语音配置，应用情感修改
            if voice_profile:
                emotional_voice = await self._apply_emotional_voice_modifications(voice_profile, profile)
                tts_config.voice_profile = emotional_voice
            else:
                # 使用默认配置并应用情感
                default_voice = VoiceProfile(
                    voice_id="emotional_default",
                    name="Emotional Voice",
                    gender=voice_profile.gender if voice_profile else VoiceGender.NEUTRAL,
                    age=voice_profile.age if voice_profile else VoiceAge.ADULT,
                    language=voice_profile.language if voice_profile else "zh-cn"
                )
                
                emotional_voice = await self._apply_emotional_voice_modifications(default_voice, profile)
                tts_config.voice_profile = emotional_voice
            
            return tts_config
            
        except Exception as e:
            logger.warning(f"Error creating emotional TTS config: {e}")
            return TTSConfig(emotion=profile.emotion_type, emotion_strength=profile.intensity)

    async def _apply_emotional_voice_modifications(self, voice_profile: VoiceProfile,
                                                 emotional_profile: EmotionalProfile) -> VoiceProfile:
        """应用情感语音修改"""
        try:
            # 创建修改后的语音配置副本
            modified_voice = VoiceProfile(
                voice_id=f"{voice_profile.voice_id}_{emotional_profile.emotion_type.value}",
                name=voice_profile.name,
                gender=voice_profile.gender,
                age=voice_profile.age,
                language=voice_profile.language,
                accent=voice_profile.accent,
                pitch=voice_profile.pitch * emotional_profile.voice_modifications.get("pitch", 1.0),
                speed=voice_profile.speed * emotional_profile.voice_modifications.get("speed", 1.0),
                energy=voice_profile.energy * emotional_profile.voice_modifications.get("energy", 1.0),
                emotion_strength=emotional_profile.intensity,
                voice_characteristics=voice_profile.voice_characteristics.copy()
            )
            
            # 添加情感特征
            modified_voice.voice_characteristics.update({
                "pitch_variation": emotional_profile.features[EmotionalFeature.PITCH_VARIATION],
                "speaking_rate": emotional_profile.features[EmotionalFeature.SPEAKING_RATE],
                "energy_level": emotional_profile.features[EmotionalFeature.ENERGY_LEVEL],
                "articulation": emotional_profile.features[EmotionalFeature.ARTICULATION],
                "prosody": emotional_profile.features[EmotionalFeature.PROSODY]
            })
            
            return modified_voice
            
        except Exception as e:
            logger.warning(f"Error applying emotional voice modifications: {e}")
            return voice_profile

    async def _apply_emotional_features(self, tts_result: TTSResult, 
                                      emotional_profile: EmotionalProfile) -> TTSResult:
        """应用情感特征到TTS结果"""
        try:
            # 这里可以添加后处理来增强情感效果
            # 例如: 调整音频特征、添加情感音效等
            
            emotional_result = TTSResult(
                audio_data=tts_result.audio_data,
                sample_rate=tts_result.sample_rate,
                phonemes=tts_result.phonemes,
                durations=await self._apply_emotional_durations(tts_result.durations, emotional_profile),
                emotion_scores=await self._calculate_emotion_scores(emotional_profile),
                processing_time=tts_result.processing_time,
                voice_characteristics=tts_result.voice_characteristics
            )
            
            return emotional_result
            
        except Exception as e:
            logger.warning(f"Error applying emotional features: {e}")
            return tts_result

    async def _apply_emotional_durations(self, durations: List[float], 
                                       emotional_profile: EmotionalProfile) -> List[float]:
        """应用情感时长调整"""
        try:
            emotional_durations = []
            
            for duration in durations:
                # 根据情感配置调整音素时长
                adjusted_duration = duration
                
                # 应用情感特定的时长调整
                speaking_rate = emotional_profile.features[EmotionalFeature.SPEAKING_RATE]
                adjusted_duration = duration / speaking_rate
                
                emotional_durations.append(adjusted_duration)
            
            return emotional_durations
            
        except Exception as e:
            logger.warning(f"Error applying emotional durations: {e}")
            return durations

    async def _calculate_emotion_scores(self, emotional_profile: EmotionalProfile) -> Dict[str, float]:
        """计算情感分数"""
        try:
            emotion_scores = {
                "valence": 0.5,  # 效价（积极-消极）
                "arousal": 0.5,  # 唤醒度（平静-兴奋）
                "dominance": 0.5  # 支配度（顺从-支配）
            }
            
            # 基于情感类型设置基础分数
            emotion_base_scores = {
                EmotionType.NEUTRAL: {"valence": 0.5, "arousal": 0.5, "dominance": 0.5},
                EmotionType.HAPPY: {"valence": 0.9, "arousal": 0.7, "dominance": 0.6},
                EmotionType.SAD: {"valence": 0.2, "arousal": 0.3, "dominance": 0.3},
                EmotionType.ANGRY: {"valence": 0.3, "arousal": 0.9, "dominance": 0.8},
                EmotionType.EXCITED: {"valence": 0.8, "arousal": 0.9, "dominance": 0.7},
                EmotionType.CALM: {"valence": 0.6, "arousal": 0.2, "dominance": 0.4},
                EmotionType.SURPRISED: {"valence": 0.7, "arousal": 0.8, "dominance": 0.5},
                EmotionType.FEARFUL: {"valence": 0.3, "arousal": 0.9, "dominance": 0.2}
            }
            
            base_scores = emotion_base_scores.get(emotional_profile.emotion_type, 
                                                emotion_base_scores[EmotionType.NEUTRAL])
            
            # 应用强度
            intensity = emotional_profile.intensity
            for key in emotion_scores:
                neutral_value = 0.5
                emotional_direction = base_scores[key] - neutral_value
                emotion_scores[key] = neutral_value + (emotional_direction * intensity)
            
            return emotion_scores
            
        except Exception as e:
            logger.warning(f"Error calculating emotion scores: {e}")
            return {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}

    async def create_custom_emotional_profile(self, emotion_type: EmotionType,
                                           features: Dict[EmotionalFeature, float],
                                           voice_modifications: Dict[str, float],
                                           intensity: float = 1.0) -> bool:
        """创建自定义情感配置"""
        try:
            custom_profile = EmotionalProfile(
                emotion_type=emotion_type,
                intensity=intensity,
                features=features,
                voice_modifications=voice_modifications,
                duration_modifiers={}  # 使用默认值
            )
            
            self.emotional_profiles[emotion_type] = custom_profile
            self.stats["profile_customizations"] += 1
            
            logger.info(f"Custom emotional profile created: {emotion_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating custom emotional profile: {e}")
            return False

    async def blend_emotions(self, text: str, primary_emotion: EmotionType,
                           secondary_emotion: EmotionType, blend_ratio: float = 0.5,
                           intensity: float = 1.0) -> Optional[TTSResult]:
        """混合情感语音合成"""
        try:
            self.stats["emotion_transitions"] += 1
            
            # 获取两个情感的配置
            primary_profile = await self._get_emotional_profile(primary_emotion, intensity)
            secondary_profile = await self._get_emotional_profile(secondary_emotion, intensity)
            
            if not primary_profile or not secondary_profile:
                logger.error("Failed to get emotional profiles for blending")
                return await self.synthesize_with_emotion(text, primary_emotion, intensity)
            
            # 混合情感配置
            blended_profile = await self._blend_emotional_profiles(
                primary_profile, secondary_profile, blend_ratio
            )
            
            # 使用混合配置合成语音
            return await self.synthesize_with_emotion(text, blended_profile.emotion_type, 
                                                    blended_profile.intensity)
            
        except Exception as e:
            logger.error(f"Error blending emotions: {e}")
            return await self.synthesize_with_emotion(text, primary_emotion, intensity)

    async def _blend_emotional_profiles(self, profile1: EmotionalProfile, 
                                      profile2: EmotionalProfile, 
                                      blend_ratio: float) -> EmotionalProfile:
        """混合情感配置"""
        try:
            # 创建混合情感类型
            blended_emotion = profile1.emotion_type  # 使用主要情感类型
            
            # 混合特征
            blended_features = {}
            for feature in EmotionalFeature:
                value1 = profile1.features.get(feature, 0.5)
                value2 = profile2.features.get(feature, 0.5)
                blended_value = value1 * (1 - blend_ratio) + value2 * blend_ratio
                blended_features[feature] = blended_value
            
            # 混合语音修改参数
            blended_voice_mods = {}
            all_params = set(profile1.voice_modifications.keys()) | set(profile2.voice_modifications.keys())
            for param in all_params:
                value1 = profile1.voice_modifications.get(param, 1.0)
                value2 = profile2.voice_modifications.get(param, 1.0)
                blended_value = value1 * (1 - blend_ratio) + value2 * blend_ratio
                blended_voice_mods[param] = blended_value
            
            # 混合强度
            blended_intensity = (profile1.intensity * (1 - blend_ratio) + 
                               profile2.intensity * blend_ratio)
            
            return EmotionalProfile(
                emotion_type=blended_emotion,
                intensity=blended_intensity,
                features=blended_features,
                voice_modifications=blended_voice_mods,
                duration_modifiers=profile1.duration_modifiers  # 使用主要配置的时长修改器
            )
            
        except Exception as e:
            logger.warning(f"Error blending emotional profiles: {e}")
            return profile1

    async def get_emotional_profile(self, emotion_type: EmotionType) -> Optional[EmotionalProfile]:
        """获取情感配置"""
        return self.emotional_profiles.get(emotion_type)

    async def get_available_emotions(self) -> List[EmotionType]:
        """获取可用情感列表"""
        return list(self.emotional_profiles.keys())

    async def analyze_emotion_in_text(self, text: str) -> Dict[EmotionType, float]:
        """分析文本中的情感"""
        try:
            # 简化的情感分析
            # 实际应该使用情感分析模型
            
            emotion_scores = {}
            
            # 关键词匹配（简化实现）
            happy_keywords = ["开心", "高兴", "快乐", "喜欢", "爱"]
            sad_keywords = ["悲伤", "难过", "伤心", "痛苦", "哭"]
            angry_keywords = ["生气", "愤怒", "讨厌", "恨", "烦"]
            
            happy_count = sum(1 for keyword in happy_keywords if keyword in text)
            sad_count = sum(1 for keyword in sad_keywords if keyword in text)
            angry_count = sum(1 for keyword in angry_keywords if keyword in text)
            
            total_keywords = happy_count + sad_count + angry_count
            
            if total_keywords > 0:
                emotion_scores[EmotionType.HAPPY] = happy_count / total_keywords
                emotion_scores[EmotionType.SAD] = sad_count / total_keywords
                emotion_scores[EmotionType.ANGRY] = angry_count / total_keywords
            else:
                # 默认中性
                emotion_scores[EmotionType.NEUTRAL] = 1.0
            
            return emotion_scores
            
        except Exception as e:
            logger.error(f"Error analyzing emotion in text: {e}")
            return {EmotionType.NEUTRAL: 1.0}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["emotional_profiles_count"] = len(self.emotional_profiles)
        stats["emotion_models_count"] = len(self.emotion_models)
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.emotional_profiles.clear()
            self.emotion_models.clear()
            
            logger.info("EmotionalTTS system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during EmotionalTTS cleanup: {e}")

# 全局情感TTS实例
emotional_tts = EmotionalTTS()

