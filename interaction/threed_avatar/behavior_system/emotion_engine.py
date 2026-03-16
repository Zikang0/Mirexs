"""
情感引擎：生成和表达情感
负责3D虚拟猫咪的情感状态管理和情感表达
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

# 导入依赖模块
from infrastructure.compute_storage.model_serving_engine import model_serving_engine, ModelType
from data.models.vision.emotion_recognition import EmotionRecognition
from cognitive.memory.episodic_memory import EpisodicMemory
from cognitive.memory.semantic_memory import SemanticMemory
from cognitive.learning.pattern_recognizer import PatternRecognizer

class EmotionalState(Enum):
    """情感状态枚举"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CONTENT = "content"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SURPRISED = "surprised"
    CURIOUS = "curious"
    BORED = "bored"
    TIRED = "tired"

class EmotionalDimension(Enum):
    """情感维度"""
    VALENCE = "valence"  # 效价：积极-消极
    AROUSAL = "arousal"  # 唤醒度：高-低
    DOMINANCE = "dominance"  # 支配度：控制-被控制

@dataclass
class EmotionalVector:
    """情感向量"""
    valence: float  # -1.0 到 1.0，负为消极，正为积极
    arousal: float  # 0.0 到 1.0，低到高唤醒
    dominance: float  # 0.0 到 1.0，低到高支配

@dataclass
class EmotionalEvent:
    """情感事件"""
    event_type: str
    intensity: float
    timestamp: datetime
    source: str
    description: str
    emotional_impact: EmotionalVector

class EmotionEngine:
    """情感引擎：生成和表达情感"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 初始化情感状态
        self.current_emotion = EmotionalState.NEUTRAL
        self.emotional_vector = EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)
        self.emotion_intensity = 0.5  # 情感强度 0.0-1.0
        
        # 情感历史记录
        self.emotion_history: List[Tuple[datetime, EmotionalState, float]] = []
        self.emotional_events: List[EmotionalEvent] = []
        
        # 情感模型
        self.emotion_model = None
        self.pattern_recognizer = None
        self.episodic_memory = None
        self.semantic_memory = None
        
        # 情感参数
        self.emotion_decay_rate = 0.1  # 情感衰减率
        self.mood_baseline = EmotionalVector(0.0, 0.3, 0.5)  # 基础情绪
        self.personality_traits = {
            "openness": 0.7,      # 开放性
            "conscientiousness": 0.6,  # 尽责性
            "extraversion": 0.8,  # 外向性
            "agreeableness": 0.9, # 宜人性
            "neuroticism": 0.3    # 神经质
        }
        
        # 情感触发阈值
        self.emotion_thresholds = {
            EmotionalState.HAPPY: 0.6,
            EmotionalState.SAD: 0.4,
            EmotionalState.ANGRY: 0.7,
            EmotionalState.FEARFUL: 0.6,
            EmotionalState.SURPRISED: 0.8
        }
        
        # 初始化完成标志
        self.initialized = False
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("EmotionEngine")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    async def initialize(self):
        """初始化情感引擎"""
        try:
            self.logger.info("正在初始化情感引擎...")
            
            # 初始化情感识别模型
            self.emotion_model = EmotionRecognition()
            success = self.emotion_model.load()
            if not success:
                self.logger.warning("情感识别模型加载失败，使用模拟模式")
            
            # 初始化模式识别器
            self.pattern_recognizer = PatternRecognizer()
            
            # 初始化记忆系统
            memory_config = {
                "persistent_mode": True,
                "db_path": "./data/memory"
            }
            self.episodic_memory = EpisodicMemory(memory_config)
            self.semantic_memory = SemanticMemory(memory_config)
            
            # 初始化模型服务引擎
            await model_serving_engine.initialize()
            
            self.initialized = True
            self.logger.info("情感引擎初始化完成")
            
        except Exception as e:
            self.logger.error(f"情感引擎初始化失败: {e}")
            self.initialized = False

    async def process_emotional_stimulus(self, stimulus: Dict[str, Any]) -> EmotionalState:
        """
        处理情感刺激
        
        Args:
            stimulus: 情感刺激数据
                - type: 刺激类型 (visual, auditory, textual, contextual)
                - content: 刺激内容
                - intensity: 刺激强度
                - source: 刺激来源
                - context: 上下文信息
        
        Returns:
            触发的情感状态
        """
        if not self.initialized:
            await self.initialize()
            if not self.initialized:
                return EmotionalState.NEUTRAL

        try:
            # 分析刺激的情感影响
            emotional_impact = await self._analyze_stimulus_impact(stimulus)
            
            # 记录情感事件
            event = EmotionalEvent(
                event_type=stimulus.get("type", "unknown"),
                intensity=stimulus.get("intensity", 0.5),
                timestamp=datetime.now(),
                source=stimulus.get("source", "unknown"),
                description=stimulus.get("content", ""),
                emotional_impact=emotional_impact
            )
            self.emotional_events.append(event)
            
            # 更新情感向量
            await self._update_emotional_vector(emotional_impact, stimulus.get("intensity", 0.5))
            
            # 确定情感状态
            new_emotion = self._determine_emotion_state()
            
            # 记录情感历史
            self.emotion_history.append((datetime.now(), new_emotion, self.emotion_intensity))
            
            # 保持历史记录长度
            if len(self.emotion_history) > 1000:
                self.emotion_history = self.emotion_history[-1000:]
                
            self.logger.info(f"情感状态更新: {self.current_emotion.value} -> {new_emotion.value}")
            self.current_emotion = new_emotion
            
            return new_emotion
            
        except Exception as e:
            self.logger.error(f"处理情感刺激失败: {e}")
            return EmotionalState.NEUTRAL

    async def _analyze_stimulus_impact(self, stimulus: Dict[str, Any]) -> EmotionalVector:
        """分析刺激的情感影响"""
        stimulus_type = stimulus.get("type")
        content = stimulus.get("content", "")
        intensity = stimulus.get("intensity", 0.5)
        
        # 基础情感影响
        base_impact = EmotionalVector(valence=0.0, arousal=0.0, dominance=0.0)
        
        if stimulus_type == "textual":
            # 文本情感分析
            text_impact = await self._analyze_text_emotion(content)
            base_impact.valence = text_impact.valence * intensity
            base_impact.arousal = text_impact.arousal * intensity
            
        elif stimulus_type == "visual":
            # 视觉情感分析（如图像、视频）
            visual_impact = await self._analyze_visual_emotion(content)
            base_impact.valence = visual_impact.valence * intensity
            base_impact.arousal = visual_impact.arousal * intensity
            
        elif stimulus_type == "auditory":
            # 听觉情感分析
            auditory_impact = await self._analyze_auditory_emotion(content)
            base_impact.valence = auditory_impact.valence * intensity
            base_impact.arousal = auditory_impact.arousal * intensity
            
        elif stimulus_type == "contextual":
            # 上下文情感分析
            contextual_impact = await self._analyze_contextual_emotion(content)
            base_impact.valence = contextual_impact.valence * intensity
            base_impact.arousal = contextual_impact.arousal * intensity
        
        # 应用个性特质调节
        base_impact = self._apply_personality_modifiers(base_impact)
        
        return base_impact

    async def _analyze_text_emotion(self, text: str) -> EmotionalVector:
        """分析文本情感"""
        try:
            # 使用语言模型进行情感分析
            if model_serving_engine.initialized:
                prompt = f"""
                分析以下文本的情感内容，返回一个JSON格式的情感向量：
                - valence: 情感效价，-1.0（非常负面）到1.0（非常正面）
                - arousal: 情感唤醒度，0.0（平静）到1.0（兴奋）
                - dominance: 情感支配度，0.0（被动）到1.0（主动）
                
                文本: "{text}"
                
                只返回JSON格式，不要其他内容。
                """
                
                response = await model_serving_engine.inference("llama3.1_8b", prompt)
                
                # 解析响应（简化实现）
                # 实际应该使用更复杂的解析逻辑
                if "positive" in response.lower() or "happy" in response.lower():
                    return EmotionalVector(valence=0.7, arousal=0.6, dominance=0.5)
                elif "negative" in response.lower() or "sad" in response.lower():
                    return EmotionalVector(valence=-0.6, arousal=0.4, dominance=0.3)
                else:
                    return EmotionalVector(valence=0.1, arousal=0.3, dominance=0.5)
                    
            else:
                # 模拟情感分析
                positive_words = ["好", "喜欢", "开心", "高兴", "爱", "棒", "完美", "优秀"]
                negative_words = ["坏", "讨厌", "伤心", "生气", "恨", "糟糕", "失败", "痛苦"]
                
                positive_count = sum(1 for word in positive_words if word in text)
                negative_count = sum(1 for word in negative_words if word in text)
                
                if positive_count > negative_count:
                    return EmotionalVector(valence=0.6, arousal=0.5, dominance=0.6)
                elif negative_count > positive_count:
                    return EmotionalVector(valence=-0.5, arousal=0.4, dominance=0.4)
                else:
                    return EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)
                    
        except Exception as e:
            self.logger.warning(f"文本情感分析失败: {e}")
            return EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)

    async def _analyze_visual_emotion(self, visual_data: Any) -> EmotionalVector:
        """分析视觉情感"""
        try:
            if hasattr(self.emotion_model, 'recognize'):
                # 使用情感识别模型分析视觉数据
                result = self.emotion_model.recognize(visual_data)
                
                if result['success']:
                    emotion = result['emotion']
                    confidence = result['confidence']
                    
                    # 映射情感到向量
                    emotion_mapping = {
                        'happy': EmotionalVector(0.8, 0.7, 0.6),
                        'sad': EmotionalVector(-0.7, 0.3, 0.3),
                        'angry': EmotionalVector(-0.6, 0.8, 0.7),
                        'surprise': EmotionalVector(0.3, 0.9, 0.4),
                        'fear': EmotionalVector(-0.5, 0.8, 0.2),
                        'disgust': EmotionalVector(-0.6, 0.5, 0.4),
                        'neutral': EmotionalVector(0.0, 0.3, 0.5)
                    }
                    
                    return emotion_mapping.get(emotion, EmotionalVector(0.0, 0.3, 0.5))
            
            # 模拟视觉情感分析
            return EmotionalVector(valence=0.2, arousal=0.4, dominance=0.5)
            
        except Exception as e:
            self.logger.warning(f"视觉情感分析失败: {e}")
            return EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)

    async def _analyze_auditory_emotion(self, audio_data: Any) -> EmotionalVector:
        """分析听觉情感"""
        try:
            # 使用语音情感识别
            if model_serving_engine.initialized:
                # 这里可以集成语音情感识别模型
                # 简化实现返回中性情感
                return EmotionalVector(valence=0.1, arousal=0.4, dominance=0.5)
            else:
                # 模拟听觉情感分析
                return EmotionalVector(valence=0.1, arousal=0.4, dominance=0.5)
                
        except Exception as e:
            self.logger.warning(f"听觉情感分析失败: {e}")
            return EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)

    async def _analyze_contextual_emotion(self, context: Dict[str, Any]) -> EmotionalVector:
        """分析上下文情感"""
        try:
            # 分析上下文信息的情感影响
            context_type = context.get("type", "neutral")
            context_value = context.get("value", 0.5)
            
            contextual_impact = {
                "success": EmotionalVector(0.7, 0.6, 0.7),
                "failure": EmotionalVector(-0.6, 0.4, 0.3),
                "progress": EmotionalVector(0.5, 0.5, 0.6),
                "stuck": EmotionalVector(-0.4, 0.3, 0.3),
                "social_positive": EmotionalVector(0.6, 0.5, 0.5),
                "social_negative": EmotionalVector(-0.5, 0.4, 0.4),
                "achievement": EmotionalVector(0.8, 0.7, 0.8),
                "frustration": EmotionalVector(-0.5, 0.6, 0.4)
            }
            
            impact = contextual_impact.get(context_type, EmotionalVector(0.0, 0.3, 0.5))
            
            # 根据上下文值调整强度
            impact.valence *= context_value
            impact.arousal *= context_value
            
            return impact
            
        except Exception as e:
            self.logger.warning(f"上下文情感分析失败: {e}")
            return EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)

    def _apply_personality_modifiers(self, emotional_impact: EmotionalVector) -> EmotionalVector:
        """应用个性特质调节"""
        # 外向性影响情感表达强度
        extraversion = self.personality_traits["extraversion"]
        emotional_impact.valence *= (0.5 + extraversion * 0.5)
        emotional_impact.arousal *= (0.5 + extraversion * 0.5)
        
        # 神经质影响负面情感敏感性
        neuroticism = self.personality_traits["neuroticism"]
        if emotional_impact.valence < 0:
            emotional_impact.valence *= (1.0 + neuroticism * 0.5)
            emotional_impact.arousal *= (1.0 + neuroticism * 0.3)
        
        # 宜人性影响积极情感敏感性
        agreeableness = self.personality_traits["agreeableness"]
        if emotional_impact.valence > 0:
            emotional_impact.valence *= (1.0 + agreeableness * 0.3)
        
        return emotional_impact

    async def _update_emotional_vector(self, impact: EmotionalVector, intensity: float):
        """更新情感向量"""
        # 应用情感影响
        decay_factor = 1.0 - self.emotion_decay_rate
        
        self.emotional_vector.valence = (
            self.emotional_vector.valence * decay_factor + 
            impact.valence * intensity * (1 - decay_factor)
        )
        
        self.emotional_vector.arousal = (
            self.emotional_vector.arousal * decay_factor + 
            impact.arousal * intensity * (1 - decay_factor)
        )
        
        self.emotional_vector.dominance = (
            self.emotional_vector.dominance * decay_factor + 
            impact.dominance * intensity * (1 - decay_factor)
        )
        
        # 限制向量范围
        self.emotional_vector.valence = max(-1.0, min(1.0, self.emotional_vector.valence))
        self.emotional_vector.arousal = max(0.0, min(1.0, self.emotional_vector.arousal))
        self.emotional_vector.dominance = max(0.0, min(1.0, self.emotional_vector.dominance))
        
        # 更新情感强度
        self.emotion_intensity = (
            abs(self.emotional_vector.valence) * 0.4 +
            self.emotional_vector.arousal * 0.4 +
            self.emotional_vector.dominance * 0.2
        )

    def _determine_emotion_state(self) -> EmotionalState:
        """确定情感状态"""
        valence = self.emotional_vector.valence
        arousal = self.emotional_vector.arousal
        dominance = self.emotional_vector.dominance
        intensity = self.emotion_intensity
        
        # 基于情感向量确定情感状态
        if intensity < 0.2:
            return EmotionalState.NEUTRAL
        
        if valence > 0.6 and arousal > 0.7:
            return EmotionalState.EXCITED
        elif valence > 0.4 and arousal > 0.5:
            return EmotionalState.HAPPY
        elif valence > 0.3:
            return EmotionalState.CONTENT
        elif valence < -0.5 and arousal > 0.6:
            return EmotionalState.ANGRY
        elif valence < -0.4 and arousal > 0.5:
            return EmotionalState.FEARFUL
        elif valence < -0.3:
            return EmotionalState.SAD
        elif arousal > 0.7:
            return EmotionalState.SURPRISED
        elif arousal < 0.2:
            return EmotionalState.BORED
        elif arousal < 0.3 and dominance < 0.3:
            return EmotionalState.TIRED
        else:
            return EmotionalState.CURIOUS

    async def get_emotional_expression(self) -> Dict[str, Any]:
        """获取情感表达参数"""
        emotion = self.current_emotion
        intensity = self.emotion_intensity
        
        # 情感表达映射
        expression_mapping = {
            EmotionalState.NEUTRAL: {
                "facial_expression": "neutral",
                "body_posture": "relaxed",
                "animation_speed": 1.0,
                "voice_tone": "neutral"
            },
            EmotionalState.HAPPY: {
                "facial_expression": "smile",
                "body_posture": "upright",
                "animation_speed": 1.2,
                "voice_tone": "cheerful"
            },
            EmotionalState.EXCITED: {
                "facial_expression": "big_smile",
                "body_posture": "energetic",
                "animation_speed": 1.5,
                "voice_tone": "excited"
            },
            EmotionalState.SAD: {
                "facial_expression": "frown",
                "body_posture": "slumped",
                "animation_speed": 0.7,
                "voice_tone": "soft"
            },
            EmotionalState.ANGRY: {
                "facial_expression": "angry",
                "body_posture": "tense",
                "animation_speed": 1.3,
                "voice_tone": "sharp"
            },
            EmotionalState.FEARFUL: {
                "facial_expression": "worried",
                "body_posture": "cautious",
                "animation_speed": 1.1,
                "voice_tone": "nervous"
            }
        }
        
        base_expression = expression_mapping.get(emotion, expression_mapping[EmotionalState.NEUTRAL])
        
        # 根据强度调整表达
        adjusted_expression = base_expression.copy()
        adjusted_expression["intensity"] = intensity
        adjusted_expression["emotion"] = emotion.value
        
        # 调整动画速度基于强度
        if "animation_speed" in adjusted_expression:
            speed_modifier = 0.8 + intensity * 0.4
            adjusted_expression["animation_speed"] *= speed_modifier
        
        return adjusted_expression

    def get_emotional_state(self) -> Dict[str, Any]:
        """获取当前情感状态"""
        return {
            "emotion": self.current_emotion.value,
            "intensity": self.emotion_intensity,
            "vector": {
                "valence": self.emotional_vector.valence,
                "arousal": self.emotional_vector.arousal,
                "dominance": self.emotional_vector.dominance
            },
            "personality_traits": self.personality_traits.copy()
        }

    async def update_personality(self, traits: Dict[str, float]):
        """更新个性特质"""
        for trait, value in traits.items():
            if trait in self.personality_traits:
                # 平滑更新个性特质
                current_value = self.personality_traits[trait]
                self.personality_traits[trait] = current_value * 0.7 + value * 0.3
                
        self.logger.info(f"个性特质已更新: {self.personality_traits}")

    def get_emotion_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取情感历史记录"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        history = []
        for timestamp, emotion, intensity in self.emotion_history:
            if timestamp >= cutoff_time:
                history.append({
                    "timestamp": timestamp.isoformat(),
                    "emotion": emotion.value,
                    "intensity": intensity
                })
        
        return history

    async def reset_emotion(self):
        """重置情感状态"""
        self.current_emotion = EmotionalState.NEUTRAL
        self.emotional_vector = EmotionalVector(valence=0.0, arousal=0.3, dominance=0.5)
        self.emotion_intensity = 0.5
        
        self.logger.info("情感状态已重置")

# 全局情感引擎实例
_global_emotion_engine: Optional[EmotionEngine] = None

async def get_emotion_engine() -> EmotionEngine:
    """获取全局情感引擎实例"""
    global _global_emotion_engine
    if _global_emotion_engine is None:
        _global_emotion_engine = EmotionEngine()
        await _global_emotion_engine.initialize()
    return _global_emotion_engine

