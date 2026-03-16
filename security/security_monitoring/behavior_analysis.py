"""
行为分析模块 - 分析用户行为模式
基于机器学习分析用户行为，检测异常活动
"""

import logging
import time
import json
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.session_manager import SessionManager, get_session_manager
from ...utils.data_processing.data_analysis import DataAnalyzer

logger = logging.getLogger(__name__)


class BehaviorPattern(Enum):
    """行为模式枚举"""
    LOGIN_PATTERN = "login_pattern"  # 登录模式
    ACCESS_PATTERN = "access_pattern"  # 访问模式
    TIME_PATTERN = "time_pattern"  # 时间模式
    LOCATION_PATTERN = "location_pattern"  # 位置模式
    DEVICE_PATTERN = "device_pattern"  # 设备模式
    API_PATTERN = "api_pattern"  # API调用模式
    DATA_PATTERN = "data_pattern"  # 数据访问模式


class AnomalyScore(Enum):
    """异常分数枚举"""
    NORMAL = "normal"  # 正常 (0-0.3)
    SUSPICIOUS = "suspicious"  # 可疑 (0.3-0.7)
    ABNORMAL = "abnormal"  # 异常 (0.7-0.9)
    CRITICAL = "critical"  # 严重异常 (0.9-1.0)


@dataclass
class UserBehaviorProfile:
    """用户行为画像"""
    user_id: str
    first_seen: float
    last_seen: float
    total_sessions: int = 0
    total_actions: int = 0
    login_times: List[float] = field(default_factory=list)
    access_patterns: Dict[str, int] = field(default_factory=dict)
    locations: Set[str] = field(default_factory=set)
    devices: Set[str] = field(default_factory=set)
    preferred_hours: Set[int] = field(default_factory=set)
    api_usage: Dict[str, int] = field(default_factory=dict)
    data_access: Dict[str, int] = field(default_factory=dict)
    anomaly_history: List[Dict[str, Any]] = field(default_factory=list)
    behavior_vector: Optional[np.ndarray] = None


@dataclass
class BehaviorAnomaly:
    """行为异常"""
    anomaly_id: str
    user_id: str
    pattern: BehaviorPattern
    score: float
    level: AnomalyScore
    detected_at: float
    description: str
    expected_behavior: Any
    actual_behavior: Any
    resolved: bool = False
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BehaviorAnalysis:
    """
    行为分析器 - 分析用户行为模式
    基于历史行为建立基线，检测异常行为
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化行为分析器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 用户行为画像
        self.user_profiles: Dict[str, UserBehaviorProfile] = {}
        
        # 行为异常记录
        self.anomalies: Dict[str, BehaviorAnomaly] = {}
        
        # 最近行为记录
        self.recent_behavior: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.session_manager = get_session_manager()
        self.data_analyzer = DataAnalyzer()
        
        # 机器学习模型（简化实现）
        self.models: Dict[str, Any] = {}
        
        # 行为阈值
        self.thresholds = self.config.get("thresholds", {})
        
        logger.info("行为分析器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "learning_period_days": 30,  # 学习周期
            "min_samples_for_baseline": 100,  # 建立基线所需最小样本数
            "anomaly_thresholds": {
                "login_time": 0.7,  # 登录时间异常阈值
                "location": 0.8,  # 位置异常阈值
                "frequency": 0.6,  # 频率异常阈值
                "data_volume": 0.7,  # 数据量异常阈值
                "api_pattern": 0.65  # API模式异常阈值
            },
            "enable_ml_detection": True,
            "enable_real_time_analysis": True,
            "max_profile_history": 10000,
            "feature_weights": {
                "login_hour": 0.2,
                "location": 0.25,
                "device": 0.15,
                "action_frequency": 0.2,
                "data_sensitivity": 0.2
            }
        }
    
    async def analyze_behavior(
        self,
        user_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> Optional[BehaviorAnomaly]:
        """
        分析用户行为，检测异常
        
        Args:
            user_id: 用户ID
            action: 执行的操作
            context: 上下文信息
        
        Returns:
            检测到的异常，如果没有则返回None
        """
        # 获取或创建用户画像
        profile = self._get_or_create_profile(user_id)
        
        # 记录行为
        self._record_behavior(user_id, action, context)
        
        # 更新画像
        self._update_profile(profile, action, context)
        
        anomalies = []
        
        # 1. 分析登录时间异常
        login_anomaly = self._analyze_login_time(profile, context)
        if login_anomaly:
            anomalies.append(login_anomaly)
        
        # 2. 分析位置异常
        location_anomaly = self._analyze_location(profile, context)
        if location_anomaly:
            anomalies.append(location_anomaly)
        
        # 3. 分析设备异常
        device_anomaly = self._analyze_device(profile, context)
        if device_anomaly:
            anomalies.append(device_anomaly)
        
        # 4. 分析访问频率异常
        frequency_anomaly = self._analyze_frequency(user_id, action, context)
        if frequency_anomaly:
            anomalies.append(frequency_anomaly)
        
        # 5. 分析数据访问异常
        data_anomaly = self._analyze_data_access(profile, action, context)
        if data_anomaly:
            anomalies.append(data_anomaly)
        
        # 6. 机器学习模型检测
        if self.config["enable_ml_detection"]:
            ml_anomaly = await self._ml_detection(profile, action, context)
            if ml_anomaly:
                anomalies.append(ml_anomaly)
        
        # 处理检测到的异常
        for anomaly in anomalies:
            await self._handle_anomaly(anomaly)
        
        return anomalies[0] if anomalies else None
    
    def _get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """获取或创建用户画像"""
        if user_id not in self.user_profiles:
            profile = UserBehaviorProfile(
                user_id=user_id,
                first_seen=time.time(),
                last_seen=time.time()
            )
            self.user_profiles[user_id] = profile
            return profile
        
        return self.user_profiles[user_id]
    
    def _record_behavior(self, user_id: str, action: str, context: Dict[str, Any]):
        """记录行为"""
        key = f"{user_id}:{action}"
        self.recent_behavior[key].append({
            "timestamp": time.time(),
            "context": context
        })
    
    def _update_profile(self, profile: UserBehaviorProfile, action: str, context: Dict[str, Any]):
        """更新用户画像"""
        profile.last_seen = time.time()
        profile.total_actions += 1
        
        # 记录登录时间
        if action == "login":
            profile.login_times.append(time.time())
            # 记录偏好时段
            hour = datetime.fromtimestamp(time.time()).hour
            profile.preferred_hours.add(hour)
        
        # 记录位置
        location = context.get("location")
        if location:
            profile.locations.add(location)
        
        # 记录设备
        device = context.get("device_id") or context.get("user_agent")
        if device:
            profile.devices.add(device)
        
        # 记录API使用
        if action.startswith("api:"):
            profile.api_usage[action] = profile.api_usage.get(action, 0) + 1
        
        # 记录数据访问
        resource = context.get("resource")
        if resource and "data" in resource:
            profile.data_access[resource] = profile.data_access.get(resource, 0) + 1
        
        # 更新行为向量（用于机器学习）
        self._update_behavior_vector(profile)
    
    def _update_behavior_vector(self, profile: UserBehaviorProfile):
        """更新行为向量"""
        # 构建特征向量
        features = []
        
        # 特征1: 平均登录时间
        if profile.login_times:
            avg_hour = np.mean([datetime.fromtimestamp(t).hour for t in profile.login_times[-100:]])
            features.append(avg_hour / 24)  # 归一化
        
        # 特征2: 位置多样性
        features.append(len(profile.locations) / 10)  # 归一化
        
        # 特征3: 设备多样性
        features.append(len(profile.devices) / 5)  # 归一化
        
        # 特征4: 行为频率
        if profile.last_seen > profile.first_seen:
            days_active = (profile.last_seen - profile.first_seen) / (24 * 3600)
            if days_active > 0:
                freq = profile.total_actions / days_active
                features.append(min(freq / 100, 1.0))  # 归一化
        
        # 特征5: API多样性
        features.append(len(profile.api_usage) / 20)  # 归一化
        
        # 确保有5个特征
        while len(features) < 5:
            features.append(0.0)
        
        profile.behavior_vector = np.array(features[:5])
    
    def _analyze_login_time(self, profile: UserBehaviorProfile, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """分析登录时间异常"""
        if len(profile.login_times) < self.config["min_samples_for_baseline"]:
            return None
        
        current_hour = datetime.fromtimestamp(time.time()).hour
        
        # 计算历史登录时段的分布
        hours = [datetime.fromtimestamp(t).hour for t in profile.login_times[-100:]]
        hour_freq = np.bincount(hours, minlength=24)
        total = len(hours)
        
        if total == 0:
            return None
        
        # 计算当前时段的概率
        prob = hour_freq[current_hour] / total
        
        # 如果概率很低，可能是异常
        threshold = self.config["anomaly_thresholds"]["login_time"]
        
        if prob < threshold:
            # 计算异常分数
            score = 1.0 - prob
            
            # 确定异常级别
            if score > 0.9:
                level = AnomalyScore.CRITICAL
            elif score > 0.7:
                level = AnomalyScore.ABNORMAL
            elif score > 0.3:
                level = AnomalyScore.SUSPICIOUS
            else:
                level = AnomalyScore.NORMAL
            
            if level != AnomalyScore.NORMAL:
                anomaly = BehaviorAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    user_id=profile.user_id,
                    pattern=BehaviorPattern.TIME_PATTERN,
                    score=score,
                    level=level,
                    detected_at=time.time(),
                    description=f"异常登录时间: 用户通常在时段 {self._get_peak_hours(hour_freq)} 登录，当前在 {current_hour} 点",
                    expected_behavior=self._get_peak_hours(hour_freq),
                    actual_behavior=f"{current_hour}点",
                    metadata={
                        "current_hour": current_hour,
                        "probability": prob,
                        "threshold": threshold
                    }
                )
                return anomaly
        
        return None
    
    def _analyze_location(self, profile: UserBehaviorProfile, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """分析位置异常"""
        if len(profile.locations) < 2:  # 至少有两个位置才能判断异常
            return None
        
        current_location = context.get("location")
        if not current_location:
            return None
        
        # 如果当前位置不在历史位置中，可能是异常
        if current_location not in profile.locations:
            # 检查时间窗口（短时间内出现在两个不同位置）
            last_location_time = self._get_last_location_time(profile.user_id)
            if last_location_time:
                time_diff = time.time() - last_location_time
                if time_diff < 3600:  # 1小时内出现在不同位置
                    score = 0.9
                    level = AnomalyScore.CRITICAL
                else:
                    score = 0.7
                    level = AnomalyScore.ABNORMAL
            else:
                score = 0.6
                level = AnomalyScore.SUSPICIOUS
            
            anomaly = BehaviorAnomaly(
                anomaly_id=self._generate_anomaly_id(),
                user_id=profile.user_id,
                pattern=BehaviorPattern.LOCATION_PATTERN,
                score=score,
                level=level,
                detected_at=time.time(),
                description=f"异常位置: 用户从未在 {current_location} 登录过",
                expected_behavior=list(profile.locations),
                actual_behavior=current_location,
                metadata={
                    "current_location": current_location,
                    "known_locations": list(profile.locations)
                }
            )
            return anomaly
        
        return None
    
    def _analyze_device(self, profile: UserBehaviorProfile, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """分析设备异常"""
        if len(profile.devices) < 2:
            return None
        
        current_device = context.get("device_id") or context.get("user_agent")
        if not current_device:
            return None
        
        # 如果当前设备不在历史设备中，可能是异常
        if current_device not in profile.devices:
            score = 0.6
            level = AnomalyScore.SUSPICIOUS
            
            anomaly = BehaviorAnomaly(
                anomaly_id=self._generate_anomaly_id(),
                user_id=profile.user_id,
                pattern=BehaviorPattern.DEVICE_PATTERN,
                score=score,
                level=level,
                detected_at=time.time(),
                description=f"新设备登录: 用户使用新设备 {current_device[:50]}...",
                expected_behavior=list(profile.devices),
                actual_behavior=current_device,
                metadata={
                    "current_device": current_device,
                    "known_devices": list(profile.devices)
                }
            )
            return anomaly
        
        return None
    
    def _analyze_frequency(self, user_id: str, action: str, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """分析访问频率异常"""
        key = f"{user_id}:{action}"
        recent = self.recent_behavior.get(key, [])
        
        if len(recent) < 10:
            return None
        
        # 计算平均间隔
        timestamps = [r["timestamp"] for r in recent]
        intervals = np.diff(timestamps)
        
        if len(intervals) == 0:
            return None
        
        avg_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # 计算当前频率
        if len(timestamps) > 1:
            last_interval = timestamps[-1] - timestamps[-2]
            
            # 如果当前间隔远小于平均值（频率突然变高）
            if last_interval < avg_interval - 2 * std_interval:
                score = min(0.9, 1.0 - last_interval / avg_interval)
                
                if score > 0.7:
                    level = AnomalyScore.ABNORMAL
                else:
                    level = AnomalyScore.SUSPICIOUS
                
                anomaly = BehaviorAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    user_id=user_id,
                    pattern=BehaviorPattern.ACCESS_PATTERN,
                    score=score,
                    level=level,
                    detected_at=time.time(),
                    description=f"异常访问频率: 操作 {action} 的频率突然增加",
                    expected_behavior=f"平均间隔 {avg_interval:.1f}秒",
                    actual_behavior=f"当前间隔 {last_interval:.1f}秒",
                    metadata={
                        "action": action,
                        "avg_interval": float(avg_interval),
                        "std_interval": float(std_interval),
                        "last_interval": float(last_interval)
                    }
                )
                return anomaly
        
        return None
    
    def _analyze_data_access(self, profile: UserBehaviorProfile, action: str, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """分析数据访问异常"""
        resource = context.get("resource")
        if not resource or "sensitive" not in resource:
            return None
        
        # 检查用户是否经常访问敏感数据
        sensitive_access_count = profile.data_access.get(resource, 0)
        
        if sensitive_access_count < 5 and profile.total_actions > 100:
            # 用户很少访问这个敏感数据
            score = 0.6
            level = AnomalyScore.SUSPICIOUS
            
            anomaly = BehaviorAnomaly(
                anomaly_id=self._generate_anomaly_id(),
                user_id=profile.user_id,
                pattern=BehaviorPattern.DATA_PATTERN,
                score=score,
                level=level,
                detected_at=time.time(),
                description=f"异常数据访问: 用户访问不常访问的敏感数据 {resource}",
                expected_behavior=f"之前访问过 {sensitive_access_count} 次",
                actual_behavior="当前访问",
                metadata={
                    "resource": resource,
                    "historical_count": sensitive_access_count,
                    "total_actions": profile.total_actions
                }
            )
            return anomaly
        
        return None
    
    async def _ml_detection(self, profile: UserBehaviorProfile, action: str, context: Dict[str, Any]) -> Optional[BehaviorAnomaly]:
        """机器学习模型检测"""
        if profile.behavior_vector is None:
            return None
        
        # 简化实现：使用简单的距离计算
        # 实际应用中可以训练一个隔离森林或自编码器
        
        # 计算与历史行为的欧氏距离
        historical_vectors = []
        for other_profile in self.user_profiles.values():
            if other_profile.behavior_vector is not None:
                historical_vectors.append(other_profile.behavior_vector)
        
        if not historical_vectors:
            return None
        
        # 计算平均距离
        distances = []
        for vec in historical_vectors[-100:]:  # 使用最近100个
            dist = np.linalg.norm(profile.behavior_vector - vec)
            distances.append(dist)
        
        avg_distance = np.mean(distances)
        std_distance = np.std(distances)
        
        # 计算当前向量的距离
        current_distances = []
        for vec in historical_vectors[-10:]:
            dist = np.linalg.norm(profile.behavior_vector - vec)
            current_distances.append(dist)
        
        current_avg = np.mean(current_distances)
        
        # 如果当前距离显著大于平均距离
        if current_avg > avg_distance + 2 * std_distance:
            score = min(0.95, current_avg / (avg_distance + 0.1))
            
            if score > 0.8:
                level = AnomalyScore.CRITICAL
            elif score > 0.6:
                level = AnomalyScore.ABNORMAL
            else:
                level = AnomalyScore.SUSPICIOUS
            
            anomaly = BehaviorAnomaly(
                anomaly_id=self._generate_anomaly_id(),
                user_id=profile.user_id,
                pattern=BehaviorPattern.ACCESS_PATTERN,
                score=score,
                level=level,
                detected_at=time.time(),
                description="机器学习模型检测到异常行为模式",
                expected_behavior=f"平均距离 {avg_distance:.3f}",
                actual_behavior=f"当前距离 {current_avg:.3f}",
                metadata={
                    "avg_distance": float(avg_distance),
                    "std_distance": float(std_distance),
                    "current_distance": float(current_avg),
                    "behavior_vector": profile.behavior_vector.tolist()
                }
            )
            return anomaly
        
        return None
    
    def _get_peak_hours(self, hour_freq: np.ndarray) -> str:
        """获取峰值时段"""
        peak_hours = np.where(hour_freq > np.mean(hour_freq))[0]
        if len(peak_hours) > 0:
            return f"{min(peak_hours)}-{max(peak_hours)}点"
        return "未知"
    
    def _get_last_location_time(self, user_id: str) -> Optional[float]:
        """获取上次位置时间"""
        if user_id not in self.recent_behavior:
            return None
        
        for record in reversed(list(self.recent_behavior[user_id])):
            if "location" in record.get("context", {}):
                return record["timestamp"]
        
        return None
    
    async def _handle_anomaly(self, anomaly: BehaviorAnomaly) -> None:
        """处理检测到的异常"""
        # 存储异常
        self.anomalies[anomaly.anomaly_id] = anomaly
        
        # 更新用户画像中的异常历史
        if anomaly.user_id in self.user_profiles:
            profile = self.user_profiles[anomaly.user_id]
            profile.anomaly_history.append({
                "anomaly_id": anomaly.anomaly_id,
                "pattern": anomaly.pattern.value,
                "score": anomaly.score,
                "level": anomaly.level.value,
                "detected_at": anomaly.detected_at
            })
            
            # 限制历史大小
            if len(profile.anomaly_history) > 100:
                profile.anomaly_history = profile.anomaly_history[-100:]
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=anomaly.user_id,
            event_type=f"BEHAVIOR_ANOMALY_{anomaly.pattern.value}",
            severity=anomaly.level.value,
            details={
                "anomaly_id": anomaly.anomaly_id,
                "score": anomaly.score,
                "description": anomaly.description,
                "expected": str(anomaly.expected_behavior),
                "actual": str(anomaly.actual_behavior)
            }
        )
        
        # 如果是严重异常，发送告警
        if anomaly.level in [AnomalyScore.ABNORMAL, AnomalyScore.CRITICAL]:
            from .alert_manager import get_alert_manager
            alert_manager = get_alert_manager()
            
            await alert_manager.send_alert(
                alert_type=f"behavior_anomaly_{anomaly.pattern.value}",
                severity=anomaly.level.value,
                message=anomaly.description,
                details={
                    "user_id": anomaly.user_id,
                    "anomaly_id": anomaly.anomaly_id,
                    "score": anomaly.score
                }
            )
        
        logger.info(f"检测到行为异常 [{anomaly.level.value}]: {anomaly.description}")
    
    def _generate_anomaly_id(self) -> str:
        """生成异常ID"""
        import secrets
        return f"anom_{int(time.time())}_{secrets.token_hex(4)}"
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        if user_id not in self.user_profiles:
            return None
        
        profile = self.user_profiles[user_id]
        return {
            "user_id": profile.user_id,
            "first_seen": profile.first_seen,
            "last_seen": profile.last_seen,
            "total_sessions": profile.total_sessions,
            "total_actions": profile.total_actions,
            "login_count": len(profile.login_times),
            "locations": list(profile.locations),
            "devices": list(profile.devices),
            "preferred_hours": sorted(profile.preferred_hours),
            "api_count": len(profile.api_usage),
            "data_access_count": len(profile.data_access),
            "anomaly_count": len(profile.anomaly_history),
            "behavior_vector": profile.behavior_vector.tolist() if profile.behavior_vector is not None else None
        }
    
    def get_anomalies(
        self,
        user_id: Optional[str] = None,
        level: Optional[AnomalyScore] = None,
        pattern: Optional[BehaviorPattern] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取异常记录
        
        Args:
            user_id: 用户ID
            level: 异常级别
            pattern: 行为模式
            limit: 返回数量限制
        
        Returns:
            异常列表
        """
        anomalies = list(self.anomalies.values())
        
        if user_id:
            anomalies = [a for a in anomalies if a.user_id == user_id]
        if level:
            anomalies = [a for a in anomalies if a.level == level]
        if pattern:
            anomalies = [a for a in anomalies if a.pattern == pattern]
        
        anomalies.sort(key=lambda a: a.detected_at, reverse=True)
        
        return [
            {
                "anomaly_id": a.anomaly_id,
                "user_id": a.user_id,
                "pattern": a.pattern.value,
                "score": a.score,
                "level": a.level.value,
                "detected_at": a.detected_at,
                "description": a.description,
                "resolved": a.resolved
            }
            for a in anomalies[:limit]
        ]
    
    def resolve_anomaly(self, anomaly_id: str, resolution: str) -> bool:
        """
        解决异常
        
        Args:
            anomaly_id: 异常ID
            resolution: 解决方案
        
        Returns:
            是否成功
        """
        if anomaly_id not in self.anomalies:
            return False
        
        anomaly = self.anomalies[anomaly_id]
        anomaly.resolved = True
        anomaly.resolved_at = time.time()
        anomaly.metadata["resolution"] = resolution
        
        logger.info(f"异常 {anomaly_id} 已解决: {resolution}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_anomalies = len(self.anomalies)
        resolved_anomalies = sum(1 for a in self.anomalies.values() if a.resolved)
        
        level_dist = {}
        pattern_dist = {}
        
        for anomaly in self.anomalies.values():
            level_dist[anomaly.level.value] = level_dist.get(anomaly.level.value, 0) + 1
            pattern_dist[anomaly.pattern.value] = pattern_dist.get(anomaly.pattern.value, 0) + 1
        
        return {
            "total_users": len(self.user_profiles),
            "total_anomalies": total_anomalies,
            "resolved_anomalies": resolved_anomalies,
            "resolution_rate": resolved_anomalies / total_anomalies if total_anomalies > 0 else 0,
            "level_distribution": level_dist,
            "pattern_distribution": pattern_dist,
            "learning_period_days": self.config["learning_period_days"],
            "ml_detection_enabled": self.config["enable_ml_detection"]
        }


# 单例实例
_behavior_analysis_instance = None


def get_behavior_analysis() -> BehaviorAnalysis:
    """获取行为分析器单例实例"""
    global _behavior_analysis_instance
    if _behavior_analysis_instance is None:
        _behavior_analysis_instance = BehaviorAnalysis()
    return _behavior_analysis_instance

