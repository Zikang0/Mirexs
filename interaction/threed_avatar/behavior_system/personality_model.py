"""
性格模型：定义角色性格特征
负责3D虚拟猫咪的性格特质建模和性格影响的行为调节
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json
import asyncio

class PersonalityTrait(Enum):
    """性格特质枚举"""
    OPENNESS = "openness"  # 开放性：好奇、创新 vs 传统、保守
    CONSCIENTIOUSNESS = "conscientiousness"  # 尽责性：有序、负责 vs 随意、粗心
    EXTRAVERSION = "extraversion"  # 外向性：社交、活跃 vs 内向、安静
    AGREEABLENESS = "agreeableness"  # 宜人性：合作、友善 vs 竞争、批判
    NEUROTICISM = "neuroticism"  # 神经质：敏感、焦虑 vs 稳定、冷静

class LearningStyle(Enum):
    """学习风格枚举"""
    VISUAL = "visual"  # 视觉学习
    AUDITORY = "auditory"  # 听觉学习
    KINESTHETIC = "kinesthetic"  # 动觉学习
    ANALYTICAL = "analytical"  # 分析学习
    EXPERIMENTAL = "experimental"  # 实验学习

@dataclass
class PersonalityProfile:
    """性格档案"""
    traits: Dict[PersonalityTrait, float]  # 特质得分 0.0-1.0
    learning_style: LearningStyle
    adaptability: float  # 适应能力 0.0-1.0
    curiosity_level: float  # 好奇心水平 0.0-1.0
    playfulness: float  # 玩耍倾向 0.0-1.0
    affection_level: float  # 亲密度 0.0-1.0
    independence: float  # 独立性 0.0-1.0

@dataclass
class BehavioralTendency:
    """行为倾向"""
    action_type: str
    base_probability: float  # 基础概率
    personality_modifiers: Dict[PersonalityTrait, float]  # 性格影响系数

class PersonalityModel:
    """性格模型：定义角色性格特征"""
    
    def __init__(self, config_path: str = "./data/personality"):
        self.config_path = config_path
        self.logger = self._setup_logger()
        
        # 性格档案
        self.personality_profile: Optional[PersonalityProfile] = None
        
        # 行为倾向映射
        self.behavioral_tendencies: Dict[str, BehavioralTendency] = {}
        
        # 学习历史
        self.learning_history: List[Dict[str, Any]] = []
        
        # 性格演化参数
        self.personality_evolution_rate = 0.01  # 性格演化速率
        self.learning_rate = 0.1  # 学习速率
        
        # 初始化性格模型
        self._initialize_personality_model()
        
        # 加载性格数据
        self._load_personality_data()
        
        self.logger.info("性格模型初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("PersonalityModel")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_personality_model(self):
        """初始化性格模型"""
        # 创建默认性格档案
        default_traits = {
            PersonalityTrait.OPENNESS: 0.7,
            PersonalityTrait.CONSCIENTIOUSNESS: 0.6,
            PersonalityTrait.EXTRAVERSION: 0.8,
            PersonalityTrait.AGREEABLENESS: 0.9,
            PersonalityTrait.NEUROTICISM: 0.3
        }
        
        self.personality_profile = PersonalityProfile(
            traits=default_traits,
            learning_style=LearningStyle.EXPERIMENTAL,
            adaptability=0.8,
            curiosity_level=0.7,
            playfulness=0.9,
            affection_level=0.8,
            independence=0.6
        )
        
        # 初始化行为倾向
        self._initialize_behavioral_tendencies()
    
    def _initialize_behavioral_tendencies(self):
        """初始化行为倾向"""
        # 问候行为倾向
        self.behavioral_tendencies["greeting_wave"] = BehavioralTendency(
            action_type="greeting",
            base_probability=0.3,
            personality_modifiers={
                PersonalityTrait.EXTRAVERSION: 0.4,
                PersonalityTrait.AGREEABLENESS: 0.3
            }
        )
        
        self.behavioral_tendencies["greeting_nod"] = BehavioralTendency(
            action_type="greeting",
            base_probability=0.5,
            personality_modifiers={
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2,
                PersonalityTrait.AGREEABLENESS: 0.2
            }
        )
        
        # 探索行为倾向
        self.behavioral_tendencies["explore_curious"] = BehavioralTendency(
            action_type="exploration",
            base_probability=0.4,
            personality_modifiers={
                PersonalityTrait.OPENNESS: 0.5,
                PersonalityTrait.CURIOSITY: 0.4
            }
        )
        
        self.behavioral_tendencies["explore_cautious"] = BehavioralTendency(
            action_type="exploration",
            base_probability=0.3,
            personality_modifiers={
                PersonalityTrait.NEUROTICISM: 0.3,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2
            }
        )
        
        # 玩耍行为倾向
        self.behavioral_tendencies["play_energetic"] = BehavioralTendency(
            action_type="play",
            base_probability=0.6,
            personality_modifiers={
                PersonalityTrait.EXTRAVERSION: 0.4,
                PersonalityTrait.PLAYFULNESS: 0.5
            }
        )
        
        self.behavioral_tendencies["play_gentle"] = BehavioralTendency(
            action_type="play",
            base_probability=0.4,
            personality_modifiers={
                PersonalityTrait.AGREEABLENESS: 0.3,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2
            }
        )
        
        # 学习行为倾向
        self.behavioral_tendencies["learn_observational"] = BehavioralTendency(
            action_type="learning",
            base_probability=0.5,
            personality_modifiers={
                PersonalityTrait.OPENNESS: 0.3,
                PersonalityTrait.CONSCIENTIOUSNESS: 0.2
            }
        )
        
        self.behavioral_tendencies["learn_experimental"] = BehavioralTendency(
            action_type="learning",
            base_probability=0.5,
            personality_modifiers={
                PersonalityTrait.OPENNESS: 0.4,
                PersonalityTrait.CURIOSITY: 0.3
            }
        )
        
        # 情感表达行为倾向
        self.behavioral_tendencies["express_affection"] = BehavioralTendency(
            action_type="emotional_expression",
            base_probability=0.7,
            personality_modifiers={
                PersonalityTrait.AGREEABLENESS: 0.4,
                PersonalityTrait.AFFECTION: 0.5
            }
        )
        
        self.behavioral_tendencies["express_independence"] = BehavioralTendency(
            action_type="emotional_expression",
            base_probability=0.4,
            personality_modifiers={
                PersonalityTrait.INDEPENDENCE: 0.5,
                PersonalityTrait.NEUROTICISM: 0.2
            }
        )
    
    def _load_personality_data(self):
        """加载性格数据"""
        personality_file = f"{self.config_path}/personality_profile.json"
        learning_file = f"{self.config_path}/learning_history.json"
        
        try:
            if os.path.exists(personality_file):
                with open(personality_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                # 转换数据为PersonalityProfile对象
                traits = {
                    PersonalityTrait(trait): score 
                    for trait, score in profile_data.get('traits', {}).items()
                }
                
                self.personality_profile = PersonalityProfile(
                    traits=traits,
                    learning_style=LearningStyle(profile_data.get('learning_style', 'experimental')),
                    adaptability=profile_data.get('adaptability', 0.8),
                    curiosity_level=profile_data.get('curiosity_level', 0.7),
                    playfulness=profile_data.get('playfulness', 0.9),
                    affection_level=profile_data.get('affection_level', 0.8),
                    independence=profile_data.get('independence', 0.6)
                )
            
            if os.path.exists(learning_file):
                with open(learning_file, 'r', encoding='utf-8') as f:
                    self.learning_history = json.load(f)
            
            self.logger.info("性格数据加载成功")
            
        except Exception as e:
            self.logger.error(f"加载性格数据失败: {e}")
    
    def save_personality_data(self):
        """保存性格数据"""
        os.makedirs(self.config_path, exist_ok=True)
        
        try:
            # 保存性格档案
            personality_file = f"{self.config_path}/personality_profile.json"
            profile_data = {
                'traits': {
                    trait.value: score 
                    for trait, score in self.personality_profile.traits.items()
                },
                'learning_style': self.personality_profile.learning_style.value,
                'adaptability': self.personality_profile.adaptability,
                'curiosity_level': self.personality_profile.curiosity_level,
                'playfulness': self.personality_profile.playfulness,
                'affection_level': self.personality_profile.affection_level,
                'independence': self.personality_profile.independence
            }
            
            with open(personality_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
            # 保存学习历史
            learning_file = f"{self.config_path}/learning_history.json"
            with open(learning_file, 'w', encoding='utf-8') as f:
                json.dump(self.learning_history, f, ensure_ascii=False, indent=2)
            
            self.logger.info("性格数据保存成功")
            
        except Exception as e:
            self.logger.error(f"保存性格数据失败: {e}")
    
    def get_behavior_probability(self, behavior_id: str, context: Dict[str, Any] = None) -> float:
        """
        获取行为概率
        
        Args:
            behavior_id: 行为ID
            context: 上下文信息
            
        Returns:
            行为概率 0.0-1.0
        """
        if behavior_id not in self.behavioral_tendencies:
            return 0.0
        
        tendency = self.behavioral_tendencies[behavior_id]
        base_probability = tendency.base_probability
        
        # 应用性格修正
        personality_modifier = self._calculate_personality_modifier(tendency)
        
        # 应用上下文修正
        context_modifier = self._calculate_context_modifier(context)
        
        # 计算最终概率
        final_probability = base_probability * personality_modifier * context_modifier
        
        # 限制概率范围
        return max(0.0, min(1.0, final_probability))
    
    def _calculate_personality_modifier(self, tendency: BehavioralTendency) -> float:
        """计算性格修正系数"""
        modifier = 1.0
        
        for trait, coefficient in tendency.personality_modifiers.items():
            if trait in self.personality_profile.traits:
                trait_score = self.personality_profile.traits[trait]
                modifier += trait_score * coefficient
        
        return modifier
    
    def _calculate_context_modifier(self, context: Dict[str, Any]) -> float:
        """计算上下文修正系数"""
        if not context:
            return 1.0
        
        modifier = 1.0
        
        # 环境熟悉度影响
        familiarity = context.get('familiarity', 0.5)
        modifier *= (0.5 + familiarity)  # 熟悉环境增加行为概率
        
        # 情绪状态影响
        emotion = context.get('emotion', 'neutral')
        emotion_modifiers = {
            'happy': 1.2,
            'excited': 1.3,
            'sad': 0.7,
            'angry': 0.8,
            'fearful': 0.6,
            'neutral': 1.0
        }
        modifier *= emotion_modifiers.get(emotion, 1.0)
        
        # 时间影响（白天/夜晚）
        time_of_day = context.get('time_of_day', 'day')
        if time_of_day == 'night':
            modifier *= 0.8  # 夜晚行为概率降低
        
        return modifier
    
    async def update_personality_from_experience(self, experience: Dict[str, Any]):
        """
        根据经验更新性格
        
        Args:
            experience: 经验数据
        """
        try:
            experience_type = experience.get('type')
            outcome = experience.get('outcome')  # 'positive', 'negative', 'neutral'
            intensity = experience.get('intensity', 0.5)
            learning_insight = experience.get('learning_insight', 0.0)
            
            # 记录学习历史
            learning_record = {
                'timestamp': asyncio.get_event_loop().time(),
                'experience_type': experience_type,
                'outcome': outcome,
                'intensity': intensity,
                'learning_insight': learning_insight
            }
            self.learning_history.append(learning_record)
            
            # 根据经验类型更新性格特质
            if experience_type == "social_interaction":
                await self._update_from_social_experience(experience)
            elif experience_type == "learning_task":
                await self._update_from_learning_experience(experience)
            elif experience_type == "exploration":
                await self._update_from_exploration_experience(experience)
            elif experience_type == "emotional_event":
                await self._update_from_emotional_experience(experience)
            
            # 更新学习风格
            await self._update_learning_style(experience)
            
            # 限制历史记录长度
            if len(self.learning_history) > 1000:
                self.learning_history = self.learning_history[-1000:]
            
            self.logger.info(f"性格根据经验更新: {experience_type}")
            
        except Exception as e:
            self.logger.error(f"根据经验更新性格失败: {e}")
    
    async def _update_from_social_experience(self, experience: Dict[str, Any]):
        """从社交经验更新性格"""
        outcome = experience.get('outcome')
        intensity = experience.get('intensity', 0.5)
        
        if outcome == "positive":
            # 积极社交经验增加外向性和宜人性
            self._adjust_trait(PersonalityTrait.EXTRAVERSION, intensity * 0.1)
            self._adjust_trait(PersonalityTrait.AGREEABLENESS, intensity * 0.08)
            self._adjust_trait(PersonalityTrait.NEUROTICISM, -intensity * 0.05)
            
        elif outcome == "negative":
            # 消极社交经验可能降低外向性，增加神经质
            self._adjust_trait(PersonalityTrait.EXTRAVERSION, -intensity * 0.05)
            self._adjust_trait(PersonalityTrait.NEUROTICISM, intensity * 0.08)
    
    async def _update_from_learning_experience(self, experience: Dict[str, Any]):
        """从学习经验更新性格"""
        outcome = experience.get('outcome')
        learning_insight = experience.get('learning_insight', 0.0)
        
        if outcome == "positive":
            # 成功学习经验增加开放性和好奇心
            self._adjust_trait(PersonalityTrait.OPENNESS, learning_insight * 0.1)
            self.personality_profile.curiosity_level = min(1.0, 
                self.personality_profile.curiosity_level + learning_insight * 0.08)
            
        elif outcome == "negative":
            # 学习失败可能降低开放性，但增加尽责性（更谨慎）
            self._adjust_trait(PersonalityTrait.OPENNESS, -learning_insight * 0.05)
            self._adjust_trait(PersonalityTrait.CONSCIENTIOUSNESS, learning_insight * 0.03)
    
    async def _update_from_exploration_experience(self, experience: Dict[str, Any]):
        """从探索经验更新性格"""
        outcome = experience.get('outcome')
        intensity = experience.get('intensity', 0.5)
        
        if outcome == "positive":
            # 积极探索经验增加开放性和好奇心
            self._adjust_trait(PersonalityTrait.OPENNESS, intensity * 0.12)
            self.personality_profile.curiosity_level = min(1.0,
                self.personality_profile.curiosity_level + intensity * 0.1)
            
        elif outcome == "negative":
            # 探索失败可能暂时降低开放性，但增加适应性
            self._adjust_trait(PersonalityTrait.OPENNESS, -intensity * 0.06)
            self.personality_profile.adaptability = min(1.0,
                self.personality_profile.adaptability + intensity * 0.05)
    
    async def _update_from_emotional_experience(self, experience: Dict[str, Any]):
        """从情感经验更新性格"""
        emotion_type = experience.get('emotion_type')
        intensity = experience.get('intensity', 0.5)
        
        if emotion_type in ["joy", "excitement"]:
            # 积极情感经验增加外向性和玩耍倾向
            self._adjust_trait(PersonalityTrait.EXTRAVERSION, intensity * 0.08)
            self.personality_profile.playfulness = min(1.0,
                self.personality_profile.playfulness + intensity * 0.1)
            
        elif emotion_type in ["fear", "anxiety"]:
            # 恐惧经验可能增加神经质，但通过适应降低
            self._adjust_trait(PersonalityTrait.NEUROTICISM, intensity * 0.1)
            self.personality_profile.adaptability = min(1.0,
                self.personality_profile.adaptability + intensity * 0.03)
    
    async def _update_learning_style(self, experience: Dict[str, Any]):
        """更新学习风格"""
        learning_efficiency = experience.get('learning_efficiency', 0.0)
        learning_method = experience.get('learning_method')
        
        if learning_efficiency > 0.7:  # 高效学习
            # 强化当前学习风格
            pass
        elif learning_efficiency < 0.3:  # 低效学习
            # 考虑调整学习风格
            if random.random() < 0.3:  # 30%概率尝试新风格
                new_style = random.choice(list(LearningStyle))
                self.personality_profile.learning_style = new_style
                self.logger.info(f"学习风格调整为: {new_style.value}")
    
    def _adjust_trait(self, trait: PersonalityTrait, adjustment: float):
        """调整性格特质"""
        current_value = self.personality_profile.traits[trait]
        new_value = current_value + adjustment * self.personality_evolution_rate
        
        # 限制在0-1范围内
        new_value = max(0.0, min(1.0, new_value))
        self.personality_profile.traits[trait] = new_value
    
    def get_personality_description(self) -> Dict[str, Any]:
        """获取性格描述"""
        traits = self.personality_profile.traits
        
        # 生成性格描述
        descriptions = []
        
        if traits[PersonalityTrait.OPENNESS] > 0.7:
            descriptions.append("好奇且富有创造力")
        elif traits[PersonalityTrait.OPENNESS] < 0.3:
            descriptions.append("传统且务实")
        
        if traits[PersonalityTrait.CONSCIENTIOUSNESS] > 0.7:
            descriptions.append("认真负责")
        elif traits[PersonalityTrait.CONSCIENTIOUSNESS] < 0.3:
            descriptions.append("随性自由")
        
        if traits[PersonalityTrait.EXTRAVERSION] > 0.7:
            descriptions.append("外向活泼")
        elif traits[PersonalityTrait.EXTRAVERSION] < 0.3:
            descriptions.append("内向文静")
        
        if traits[PersonalityTrait.AGREEABLENESS] > 0.7:
            descriptions.append("友善合作")
        elif traits[PersonalityTrait.AGREEABLENESS] < 0.3:
            descriptions.append("独立自主")
        
        if traits[PersonalityTrait.NEUROTICISM] > 0.7:
            descriptions.append("情感丰富")
        elif traits[PersonalityTrait.NEUROTICISM] < 0.3:
            descriptions.append("情绪稳定")
        
        return {
            "traits": {trait.value: score for trait, score in traits.items()},
            "learning_style": self.personality_profile.learning_style.value,
            "adaptability": self.personality_profile.adaptability,
            "curiosity_level": self.personality_profile.curiosity_level,
            "playfulness": self.personality_profile.playfulness,
            "affection_level": self.personality_profile.affection_level,
            "independence": self.personality_profile.independence,
            "description": "，".join(descriptions) if descriptions else "性格均衡"
        }
    
    def predict_behavior_preferences(self, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        预测行为偏好
        
        Args:
            context: 上下文信息
            
        Returns:
            行为偏好概率映射
        """
        preferences = {}
        
        for behavior_id, tendency in self.behavioral_tendencies.items():
            probability = self.get_behavior_probability(behavior_id, context)
            preferences[behavior_id] = probability
        
        return preferences
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """获取学习洞察"""
        if not self.learning_history:
            return {"total_experiences": 0, "recent_trend": "no_data"}
        
        recent_experiences = self.learning_history[-100:]  # 最近100条经验
        
        # 分析经验分布
        experience_types = {}
        outcomes = {}
        
        for experience in recent_experiences:
            exp_type = experience.get('experience_type', 'unknown')
            outcome = experience.get('outcome', 'neutral')
            
            experience_types[exp_type] = experience_types.get(exp_type, 0) + 1
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        
        # 计算学习效率
        positive_outcomes = outcomes.get('positive', 0)
        total_outcomes = sum(outcomes.values())
        learning_efficiency = positive_outcomes / total_outcomes if total_outcomes > 0 else 0.0
        
        return {
            "total_experiences": len(self.learning_history),
            "recent_experiences": len(recent_experiences),
            "experience_distribution": experience_types,
            "outcome_distribution": outcomes,
            "learning_efficiency": learning_efficiency,
            "dominant_learning_style": self.personality_profile.learning_style.value
        }
    
    async def reset_personality(self, profile: Optional[PersonalityProfile] = None):
        """
        重置性格
        
        Args:
            profile: 可选的性格档案，如果为None则使用默认
        """
        if profile:
            self.personality_profile = profile
        else:
            self._initialize_personality_model()
        
        self.learning_history.clear()
        
        self.logger.info("性格已重置")

# 全局性格模型实例
_global_personality_model: Optional[PersonalityModel] = None

def get_personality_model() -> PersonalityModel:
    """获取全局性格模型实例"""
    global _global_personality_model
    if _global_personality_model is None:
        _global_personality_model = PersonalityModel()
    return _global_personality_model

# 导入os模块
import os
