"""
情境感知：感知环境情境
负责3D虚拟猫咪的环境感知、情境理解和上下文构建
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json

class EnvironmentType(Enum):
    """环境类型枚举"""
    HOME_INDOOR = "home_indoor"  # 家庭室内
    HOME_OUTDOOR = "home_outdoor"  # 家庭室外
    OFFICE = "office"  # 办公室
    PUBLIC_SPACE = "public_space"  # 公共空间
    UNKNOWN = "unknown"  # 未知环境

class TimeContext(Enum):
    """时间上下文枚举"""
    MORNING = "morning"  # 早晨
    DAYTIME = "daytime"  # 白天
    EVENING = "evening"  # 傍晚
    NIGHT = "night"  # 夜晚
    LATE_NIGHT = "late_night"  # 深夜

class SocialContext(Enum):
    """社交上下文枚举"""
    ALONE = "alone"  # 独自
    WITH_OWNER = "with_owner"  # 与主人一起
    WITH_FAMILY = "with_family"  # 与家人一起
    WITH_STRANGERS = "with_strangers"  # 与陌生人一起
    WITH_OTHER_PETS = "with_other_pets"  # 与其他宠物一起

@dataclass
class EnvironmentalStimulus:
    """环境刺激"""
    stimulus_type: str  # 刺激类型
    intensity: float  # 刺激强度
    position: Tuple[float, float, float]  # 位置
    duration: float  # 持续时间
    novelty: float  # 新颖度

@dataclass
class SituationContext:
    """情境上下文"""
    environment_type: EnvironmentType
    time_context: TimeContext
    social_context: SocialContext
    emotional_atmosphere: str  # 情感氛围
    activity_level: float  # 活动水平
    safety_level: float  # 安全水平

class ContextAwareness:
    """情境感知：感知环境情境"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 情境状态
        self.current_situation: Optional[SituationContext] = None
        self.environmental_stimuli: List[EnvironmentalStimulus] = []
        
        # 环境模型
        self.environment_model: Dict[str, Any] = {
            "familiar_locations": [],
            "known_objects": [],
            "preferred_spots": [],
            "avoidance_zones": []
        }
        
        # 时间跟踪
        self.time_tracker = TimeTracker()
        
        # 社交感知
        self.social_awareness = SocialAwareness()
        
        # 环境特征
        self.environment_features: Dict[str, Any] = {
            "light_level": 0.7,
            "noise_level": 0.3,
            "temperature": 22.0,
            "space_size": 1.0,
            "clutter_level": 0.4
        }
        
        # 情境历史
        self.situation_history: List[Tuple[float, SituationContext]] = []
        self.max_history_size = 1000
        
        # 初始化情境感知
        self._initialize_context_awareness()
        
        self.logger.info("情境感知系统初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("ContextAwareness")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_context_awareness(self):
        """初始化情境感知"""
        # 设置初始情境
        self.current_situation = SituationContext(
            environment_type=EnvironmentType.HOME_INDOOR,
            time_context=self.time_tracker.get_current_time_context(),
            social_context=SocialContext.ALONE,
            emotional_atmosphere="calm",
            activity_level=0.3,
            safety_level=0.9
        )
    
    async def update_environmental_data(self, sensor_data: Dict[str, Any]):
        """
        更新环境数据
        
        Args:
            sensor_data: 传感器数据
        """
        try:
            # 更新环境特征
            if "light_level" in sensor_data:
                self.environment_features["light_level"] = sensor_data["light_level"]
            if "noise_level" in sensor_data:
                self.environment_features["noise_level"] = sensor_data["noise_level"]
            if "temperature" in sensor_data:
                self.environment_features["temperature"] = sensor_data["temperature"]
            
            # 检测环境刺激
            await self._detect_environmental_stimuli(sensor_data)
            
            # 更新环境类型识别
            await self._update_environment_type(sensor_data)
            
            # 更新情境理解
            await self._update_situation_understanding()
            
            self.logger.debug("环境数据更新完成")
            
        except Exception as e:
            self.logger.error(f"更新环境数据失败: {e}")
    
    async def _detect_environmental_stimuli(self, sensor_data: Dict[str, Any]):
        """检测环境刺激"""
        current_time = time.time()
        new_stimuli = []
        
        # 检测视觉刺激
        if "visual_objects" in sensor_data:
            for obj in sensor_data["visual_objects"]:
                stimulus = EnvironmentalStimulus(
                    stimulus_type="visual_object",
                    intensity=obj.get("saliency", 0.5),
                    position=obj.get("position", (0, 0, 0)),
                    duration=0.0,
                    novelty=self._calculate_novelty(obj.get("object_id", "unknown"))
                )
                new_stimuli.append(stimulus)
        
        # 检测声音刺激
        if "sounds" in sensor_data:
            for sound in sensor_data["sounds"]:
                stimulus = EnvironmentalStimulus(
                    stimulus_type="sound",
                    intensity=sound.get("volume", 0.5),
                    position=sound.get("position", (0, 0, 0)),
                    duration=sound.get("duration", 1.0),
                    novelty=self._calculate_novelty(sound.get("sound_type", "unknown"))
                )
                new_stimuli.append(stimulus)
        
        # 检测运动刺激
        if "movements" in sensor_data:
            for movement in sensor_data["movements"]:
                stimulus = EnvironmentalStimulus(
                    stimulus_type="movement",
                    intensity=movement.get("speed", 0.5),
                    position=movement.get("position", (0, 0, 0)),
                    duration=movement.get("duration", 1.0),
                    novelty=0.7  # 运动通常具有较高新颖度
                )
                new_stimuli.append(stimulus)
        
        # 更新刺激列表
        self.environmental_stimuli.extend(new_stimuli)
        
        # 移除过期的刺激
        self.environmental_stimuli = [
            stimulus for stimulus in self.environmental_stimuli
            if current_time - stimulus.duration < 30.0  # 保留30秒内的刺激
        ]
        
        if new_stimuli:
            self.logger.debug(f"检测到 {len(new_stimuli)} 个新环境刺激")
    
    def _calculate_novelty(self, stimulus_id: str) -> float:
        """计算刺激新颖度"""
        # 简化实现：基于刺激ID的出现频率
        # 实际实现应该基于学习历史
        known_stimuli = self.environment_model.get("known_stimuli", {})
        
        if stimulus_id in known_stimuli:
            encounter_count = known_stimuli[stimulus_id]
            novelty = 1.0 / (1.0 + encounter_count * 0.1)  # 随遇到次数降低新颖度
            return novelty
        else:
            return 1.0  # 新刺激具有最高新颖度
    
    async def _update_environment_type(self, sensor_data: Dict[str, Any]):
        """更新环境类型识别"""
        # 基于环境特征识别环境类型
        light_level = self.environment_features["light_level"]
        noise_level = self.environment_features["noise_level"]
        space_size = self.environment_features["space_size"]
        
        # 环境类型识别逻辑
        if light_level > 0.8 and noise_level < 0.3:
            new_env_type = EnvironmentType.HOME_INDOOR
        elif light_level > 0.9 and noise_level > 0.6:
            new_env_type = EnvironmentType.PUBLIC_SPACE
        elif space_size > 2.0 and noise_level < 0.4:
            new_env_type = EnvironmentType.OFFICE
        else:
            new_env_type = EnvironmentType.UNKNOWN
        
        if (self.current_situation and 
            self.current_situation.environment_type != new_env_type):
            self.current_situation.environment_type = new_env_type
            self.logger.info(f"环境类型更新: {new_env_type.value}")
    
    async def _update_situation_understanding(self):
        """更新情境理解"""
        if not self.current_situation:
            return
        
        # 更新时间上下文
        new_time_context = self.time_tracker.get_current_time_context()
        if self.current_situation.time_context != new_time_context:
            self.current_situation.time_context = new_time_context
        
        # 更新社交上下文
        new_social_context = await self.social_awareness.get_current_social_context()
        if self.current_situation.social_context != new_social_context:
            self.current_situation.social_context = new_social_context
        
        # 更新情感氛围
        emotional_atmosphere = self._assess_emotional_atmosphere()
        if self.current_situation.emotional_atmosphere != emotional_atmosphere:
            self.current_situation.emotional_atmosphere = emotional_atmosphere
        
        # 更新活动水平
        activity_level = self._calculate_activity_level()
        self.current_situation.activity_level = activity_level
        
        # 更新安全水平
        safety_level = self._assess_safety_level()
        self.current_situation.safety_level = safety_level
        
        # 记录情境历史
        self._record_situation_history()
    
    def _assess_emotional_atmosphere(self) -> str:
        """评估情感氛围"""
        # 基于环境刺激和特征评估情感氛围
        noise_level = self.environment_features["noise_level"]
        light_level = self.environment_features["light_level"]
        
        if noise_level < 0.2 and light_level > 0.7:
            return "calm"
        elif noise_level > 0.6:
            return "energetic"
        elif light_level < 0.3:
            return "serious"
        else:
            return "neutral"
    
    def _calculate_activity_level(self) -> float:
        """计算活动水平"""
        # 基于环境刺激的数量和强度计算活动水平
        if not self.environmental_stimuli:
            return 0.1
        
        total_intensity = sum(stimulus.intensity for stimulus in self.environmental_stimuli)
        avg_intensity = total_intensity / len(self.environmental_stimuli)
        
        # 考虑刺激数量
        stimulus_count_factor = min(len(self.environmental_stimuli) / 10.0, 1.0)
        
        activity_level = avg_intensity * 0.7 + stimulus_count_factor * 0.3
        return min(1.0, max(0.0, activity_level))
    
    def _assess_safety_level(self) -> float:
        """评估安全水平"""
        base_safety = 0.8
        
        # 环境类型影响
        env_safety = {
            EnvironmentType.HOME_INDOOR: 0.9,
            EnvironmentType.HOME_OUTDOOR: 0.7,
            EnvironmentType.OFFICE: 0.8,
            EnvironmentType.PUBLIC_SPACE: 0.5,
            EnvironmentType.UNKNOWN: 0.4
        }
        
        env_factor = env_safety.get(self.current_situation.environment_type, 0.5)
        
        # 噪音水平影响（突然的巨响可能表示危险）
        noise_safety = 1.0 - min(self.environment_features["noise_level"] * 2, 1.0)
        
        # 社交上下文影响
        social_safety = {
            SocialContext.ALONE: 0.7,
            SocialContext.WITH_OWNER: 0.9,
            SocialContext.WITH_FAMILY: 0.8,
            SocialContext.WITH_STRANGERS: 0.4,
            SocialContext.WITH_OTHER_PETS: 0.6
        }
        
        social_factor = social_safety.get(self.current_situation.social_context, 0.5)
        
        # 综合安全水平
        safety_level = (env_factor * 0.4 + noise_safety * 0.3 + social_factor * 0.3)
        return safety_level
    
    def _record_situation_history(self):
        """记录情境历史"""
        if self.current_situation:
            timestamp = time.time()
            self.situation_history.append((timestamp, self.current_situation))
            
            # 限制历史记录大小
            if len(self.situation_history) > self.max_history_size:
                self.situation_history = self.situation_history[-self.max_history_size:]
    
    async def update_social_context(self, social_data: Dict[str, Any]):
        """
        更新社交上下文
        
        Args:
            social_data: 社交数据
        """
        await self.social_awareness.update_social_data(social_data)
    
    def get_current_context(self) -> Dict[str, Any]:
        """获取当前上下文"""
        if not self.current_situation:
            return {}
        
        return {
            "situation": {
                "environment_type": self.current_situation.environment_type.value,
                "time_context": self.current_situation.time_context.value,
                "social_context": self.current_situation.social_context.value,
                "emotional_atmosphere": self.current_situation.emotional_atmosphere,
                "activity_level": self.current_situation.activity_level,
                "safety_level": self.current_situation.safety_level
            },
            "environment_features": self.environment_features.copy(),
            "active_stimuli_count": len(self.environmental_stimuli),
            "dominant_stimulus": self._get_dominant_stimulus()
        }
    
    def _get_dominant_stimulus(self) -> Optional[Dict[str, Any]]:
        """获取主导刺激"""
        if not self.environmental_stimuli:
            return None
        
        # 找到强度最高的刺激
        dominant = max(self.environmental_stimuli, key=lambda s: s.intensity)
        
        return {
            "type": dominant.stimulus_type,
            "intensity": dominant.intensity,
            "novelty": dominant.novelty
        }
    
    def get_context_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        if not self.current_situation:
            return {"status": "no_context_data"}
        
        # 分析情境稳定性
        stability = self._analyze_situation_stability()
        
        # 获取环境熟悉度
        familiarity = self._calculate_environment_familiarity()
        
        return {
            "current_situation": self.current_situation.__dict__,
            "situation_stability": stability,
            "environment_familiarity": familiarity,
            "total_stimuli_detected": len(self.environmental_stimuli),
            "context_confidence": self._calculate_context_confidence()
        }
    
    def _analyze_situation_stability(self) -> str:
        """分析情境稳定性"""
        if len(self.situation_history) < 5:
            return "unknown"
        
        # 检查最近情境变化
        recent_situations = self.situation_history[-5:]
        situation_changes = 0
        
        for i in range(1, len(recent_situations)):
            prev_situation = recent_situations[i-1][1]
            curr_situation = recent_situations[i][1]
            
            if (prev_situation.environment_type != curr_situation.environment_type or
                prev_situation.social_context != curr_situation.social_context):
                situation_changes += 1
        
        change_ratio = situation_changes / (len(recent_situations) - 1)
        
        if change_ratio < 0.2:
            return "stable"
        elif change_ratio < 0.5:
            return "moderately_stable"
        else:
            return "unstable"
    
    def _calculate_environment_familiarity(self) -> float:
        """计算环境熟悉度"""
        # 基于在当前环境中的时间和历史记录计算熟悉度
        env_type = self.current_situation.environment_type
        
        # 统计在该环境中的时间
        env_duration = 0.0
        for timestamp, situation in self.situation_history:
            if situation.environment_type == env_type:
                env_duration += 1.0  # 简化：每次记录算1个单位时间
        
        # 计算熟悉度（基于持续时间）
        familiarity = min(env_duration / 100.0, 1.0)  # 100个单位时间达到完全熟悉
        
        return familiarity
    
    def _calculate_context_confidence(self) -> float:
        """计算上下文置信度"""
        confidence = 0.5  # 基础置信度
        
        # 环境类型识别置信度
        if self.current_situation.environment_type != EnvironmentType.UNKNOWN:
            confidence += 0.2
        
        # 数据充足性置信度
        if len(self.situation_history) > 10:
            confidence += 0.2
        
        # 情境稳定性置信度
        stability = self._analyze_situation_stability()
        if stability == "stable":
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def learn_environment(self, location_data: Dict[str, Any]):
        """
        学习环境
        
        Args:
            location_data: 位置数据
        """
        location_id = location_data.get("location_id")
        if not location_id:
            return
        
        # 添加到熟悉位置
        if location_id not in self.environment_model["familiar_locations"]:
            self.environment_model["familiar_locations"].append(location_id)
        
        # 学习环境特征
        if "preferred" in location_data and location_data["preferred"]:
            if location_id not in self.environment_model["preferred_spots"]:
                self.environment_model["preferred_spots"].append(location_id)
        
        if "avoid" in location_data and location_data["avoid"]:
            if location_id not in self.environment_model["avoidance_zones"]:
                self.environment_model["avoidance_zones"].append(location_id)
        
        self.logger.info(f"环境学习完成: {location_id}")

class TimeTracker:
    """时间跟踪器"""
    
    def get_current_time_context(self) -> TimeContext:
        """获取当前时间上下文"""
        import datetime
        
        current_hour = datetime.datetime.now().hour
        
        if 5 <= current_hour < 9:
            return TimeContext.MORNING
        elif 9 <= current_hour < 17:
            return TimeContext.DAYTIME
        elif 17 <= current_hour < 21:
            return TimeContext.EVENING
        elif 21 <= current_hour < 24:
            return TimeContext.NIGHT
        else:  # 0-5点
            return TimeContext.LATE_NIGHT

class SocialAwareness:
    """社交感知"""
    
    def __init__(self):
        self.known_individuals: Dict[str, Dict[str, Any]] = {}
        self.current_social_context = SocialContext.ALONE
        self.interaction_history: List[Dict[str, Any]] = []
    
    async def update_social_data(self, social_data: Dict[str, Any]):
        """
        更新社交数据
        
        Args:
            social_data: 社交数据
        """
        # 检测在场个体
        present_individuals = social_data.get("present_individuals", [])
        
        # 更新社交上下文
        if not present_individuals:
            self.current_social_context = SocialContext.ALONE
        else:
            # 分析在场个体类型
            owners_present = any(ind.get("is_owner", False) for ind in present_individuals)
            family_present = any(ind.get("is_family", False) for ind in present_individuals)
            strangers_present = any(ind.get("is_stranger", True) for ind in present_individuals)
            pets_present = any(ind.get("is_pet", False) for ind in present_individuals)
            
            if owners_present:
                self.current_social_context = SocialContext.WITH_OWNER
            elif family_present:
                self.current_social_context = SocialContext.WITH_FAMILY
            elif pets_present:
                self.current_social_context = SocialContext.WITH_OTHER_PETS
            elif strangers_present:
                self.current_social_context = SocialContext.WITH_STRANGERS
            else:
                self.current_social_context = SocialContext.ALONE
        
        # 记录交互历史
        interaction_record = {
            "timestamp": time.time(),
            "social_context": self.current_social_context.value,
            "individuals_count": len(present_individuals),
            "interaction_type": social_data.get("interaction_type", "observation")
        }
        self.interaction_history.append(interaction_record)
    
    async def get_current_social_context(self) -> SocialContext:
        """获取当前社交上下文"""
        return self.current_social_context

# 全局情境感知实例
_global_context_awareness: Optional[ContextAwareness] = None

def get_context_awareness() -> ContextAwareness:
    """获取全局情境感知实例"""
    global _global_context_awareness
    if _global_context_awareness is None:
        _global_context_awareness = ContextAwareness()
    return _global_context_awareness