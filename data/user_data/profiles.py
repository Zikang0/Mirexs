"""
用户画像模块 - 管理用户个性化数据和特征分析
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd

logger = logging.getLogger(__name__)

class UserTier(Enum):
    """用户等级枚举"""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class PersonalityType(Enum):
    """性格类型枚举"""
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    PRACTICAL = "practical"
    SOCIAL = "social"

@dataclass
class UserDemographics:
    """用户人口统计数据"""
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"

@dataclass
class BehavioralPatterns:
    """用户行为模式数据"""
    preferred_interaction_times: List[str] = field(default_factory=list)
    average_session_duration: float = 0.0
    interaction_frequency: str = "low"  # low, medium, high
    preferred_modalities: List[str] = field(default_factory=lambda: ["text"])
    task_completion_rate: float = 0.0
    error_rate: float = 0.0

@dataclass
class LearningProfile:
    """学习档案数据"""
    learning_style: str = "visual"  # visual, auditory, kinesthetic, reading
    pace_preference: str = "moderate"  # slow, moderate, fast
    complexity_tolerance: str = "medium"  # low, medium, high
    preferred_topics: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    skill_progression: Dict[str, float] = field(default_factory=dict)

@dataclass
class UserProfile:
    """完整用户画像数据类"""
    user_id: str
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    last_active: datetime
    tier: UserTier
    personality_type: PersonalityType
    demographics: UserDemographics
    behavioral_patterns: BehavioralPatterns
    learning_profile: LearningProfile
    preferences_summary: Dict[str, Any]
    engagement_score: float
    satisfaction_score: float
    tags: List[str]
    metadata: Dict[str, Any]

class UserProfiles:
    """用户画像管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化用户画像管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.profiles_table = config.get('profiles_table', 'user_profiles')
        self.behavior_logs_table = config.get('behavior_logs_table', 'user_behavior_logs')
        
        # 分析模型
        self.kmeans_model = None
        self.scaler = StandardScaler()
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化用户画像相关表"""
        try:
            # 用户画像表
            profile_schema = {
                'user_id': 'VARCHAR(100) PRIMARY KEY',
                'username': 'VARCHAR(100) NOT NULL',
                'email': 'VARCHAR(255)',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'last_active': 'TIMESTAMP',
                'tier': 'VARCHAR(20) DEFAULT "novice"',
                'personality_type': 'VARCHAR(20)',
                'demographics': 'TEXT',  # JSON格式
                'behavioral_patterns': 'TEXT',  # JSON格式
                'learning_profile': 'TEXT',  # JSON格式
                'preferences_summary': 'TEXT',  # JSON格式
                'engagement_score': 'FLOAT DEFAULT 0.0',
                'satisfaction_score': 'FLOAT DEFAULT 0.0',
                'tags': 'TEXT',  # JSON格式
                'metadata': 'TEXT'  # JSON格式
            }
            
            self.db.create_table(self.profiles_table, profile_schema)
            
            # 用户行为日志表
            behavior_schema = {
                'log_id': 'SERIAL PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'event_type': 'VARCHAR(50) NOT NULL',
                'event_data': 'TEXT',  # JSON格式
                'timestamp': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'session_id': 'VARCHAR(100)',
                'context': 'TEXT'  # JSON格式
            }
            
            constraints = [
                'FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.behavior_logs_table, behavior_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.profiles_table, 'username', unique=True)
            self.db.create_index(self.profiles_table, 'email')
            self.db.create_index(self.profiles_table, 'tier')
            self.db.create_index(self.profiles_table, 'personality_type')
            self.db.create_index(self.behavior_logs_table, 'user_id')
            self.db.create_index(self.behavior_logs_table, 'event_type')
            self.db.create_index(self.behavior_logs_table, 'timestamp')
            
            self.logger.info("User profile tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user profile tables: {str(e)}")
            raise
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> str:
        """
        创建用户画像
        
        Args:
            user_data: 用户数据
            
        Returns:
            str: 用户ID
        """
        try:
            user_id = user_data.get('user_id') or str(uuid.uuid4())
            current_time = datetime.now()
            
            # 构建完整用户画像
            profile = UserProfile(
                user_id=user_id,
                username=user_data['username'],
                email=user_data.get('email', ''),
                created_at=current_time,
                updated_at=current_time,
                last_active=current_time,
                tier=UserTier(user_data.get('tier', 'novice')),
                personality_type=PersonalityType(user_data.get('personality_type', 'analytical')),
                demographics=UserDemographics(**user_data.get('demographics', {})),
                behavioral_patterns=BehavioralPatterns(**user_data.get('behavioral_patterns', {})),
                learning_profile=LearningProfile(**user_data.get('learning_profile', {})),
                preferences_summary=user_data.get('preferences_summary', {}),
                engagement_score=user_data.get('engagement_score', 0.0),
                satisfaction_score=user_data.get('satisfaction_score', 0.0),
                tags=user_data.get('tags', []),
                metadata=user_data.get('metadata', {})
            )
            
            # 准备数据库数据
            db_data = {
                'user_id': profile.user_id,
                'username': profile.username,
                'email': profile.email,
                'created_at': profile.created_at,
                'updated_at': profile.updated_at,
                'last_active': profile.last_active,
                'tier': profile.tier.value,
                'personality_type': profile.personality_type.value,
                'demographics': json.dumps(asdict(profile.demographics)),
                'behavioral_patterns': json.dumps(asdict(profile.behavioral_patterns)),
                'learning_profile': json.dumps(asdict(profile.learning_profile)),
                'preferences_summary': json.dumps(profile.preferences_summary),
                'engagement_score': profile.engagement_score,
                'satisfaction_score': profile.satisfaction_score,
                'tags': json.dumps(profile.tags),
                'metadata': json.dumps(profile.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.profiles_table, db_data)
            
            self.logger.info(f"User profile created: {user_id}")
            return user_id
            
        except Exception as e:
            self.logger.error(f"Failed to create user profile: {str(e)}")
            raise
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            UserProfile: 用户画像，如果不存在返回None
        """
        try:
            query = f"SELECT * FROM {self.profiles_table} WHERE user_id = %s"
            results = self.db.execute_query(query, (user_id,))
            
            if not results:
                return None
            
            profile_data = results[0]
            
            # 转换为UserProfile对象
            return UserProfile(
                user_id=profile_data['user_id'],
                username=profile_data['username'],
                email=profile_data['email'],
                created_at=profile_data['created_at'],
                updated_at=profile_data['updated_at'],
                last_active=profile_data['last_active'],
                tier=UserTier(profile_data['tier']),
                personality_type=PersonalityType(profile_data['personality_type']),
                demographics=UserDemographics(**json.loads(profile_data['demographics'])),
                behavioral_patterns=BehavioralPatterns(**json.loads(profile_data['behavioral_patterns'])),
                learning_profile=LearningProfile(**json.loads(profile_data['learning_profile'])),
                preferences_summary=json.loads(profile_data['preferences_summary']),
                engagement_score=profile_data['engagement_score'],
                satisfaction_score=profile_data['satisfaction_score'],
                tags=json.loads(profile_data['tags']),
                metadata=json.loads(profile_data['metadata'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get user profile: {str(e)}")
            return None
    
    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新用户画像
        
        Args:
            user_id: 用户ID
            updates: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取现有画像
            existing_profile = self.get_user_profile(user_id)
            if not existing_profile:
                self.logger.warning(f"User profile not found: {user_id}")
                return False
            
            # 准备更新数据
            update_data = {
                'updated_at': datetime.now(),
                'last_active': datetime.now()
            }
            
            # 处理嵌套数据结构
            if 'demographics' in updates:
                current_demographics = asdict(existing_profile.demographics)
                current_demographics.update(updates['demographics'])
                update_data['demographics'] = json.dumps(current_demographics)
            
            if 'behavioral_patterns' in updates:
                current_behavioral = asdict(existing_profile.behavioral_patterns)
                current_behavioral.update(updates['behavioral_patterns'])
                update_data['behavioral_patterns'] = json.dumps(current_behavioral)
            
            if 'learning_profile' in updates:
                current_learning = asdict(existing_profile.learning_profile)
                current_learning.update(updates['learning_profile'])
                update_data['learning_profile'] = json.dumps(current_learning)
            
            # 处理简单字段
            simple_fields = [
                'username', 'email', 'tier', 'personality_type',
                'preferences_summary', 'engagement_score', 'satisfaction_score',
                'tags', 'metadata'
            ]
            
            for field in simple_fields:
                if field in updates:
                    if field in ['tier', 'personality_type']:
                        update_data[field] = updates[field].value
                    elif field in ['preferences_summary', 'tags', 'metadata']:
                        update_data[field] = json.dumps(updates[field])
                    else:
                        update_data[field] = updates[field]
            
            # 执行更新
            affected = self.db.execute_update(
                self.profiles_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                self.logger.info(f"User profile updated: {user_id}")
                return True
            else:
                self.logger.warning(f"User profile not found for update: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update user profile: {str(e)}")
            return False
    
    def log_user_behavior(self, user_id: str, event_type: str, 
                         event_data: Dict[str, Any] = None,
                         session_id: str = None, context: Dict[str, Any] = None) -> bool:
        """
        记录用户行为
        
        Args:
            user_id: 用户ID
            event_type: 事件类型
            event_data: 事件数据
            session_id: 会话ID
            context: 上下文信息
            
        Returns:
            bool: 记录是否成功
        """
        try:
            log_data = {
                'user_id': user_id,
                'event_type': event_type,
                'event_data': json.dumps(event_data or {}),
                'timestamp': datetime.now(),
                'session_id': session_id,
                'context': json.dumps(context or {})
            }
            
            self.db.execute_insert(self.behavior_logs_table, log_data)
            
            # 更新用户最后活跃时间
            self.update_user_profile(user_id, {})
            
            self.logger.debug(f"User behavior logged: {user_id} - {event_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to log user behavior: {str(e)}")
            return False
    
    def analyze_user_behavior(self, user_id: str, time_window_days: int = 30) -> Dict[str, Any]:
        """
        分析用户行为模式
        
        Args:
            user_id: 用户ID
            time_window_days: 时间窗口（天）
            
        Returns:
            Dict: 行为分析结果
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_window_days)
            
            # 查询行为日志
            query = f"""
            SELECT event_type, event_data, timestamp, session_id 
            FROM {self.behavior_logs_table} 
            WHERE user_id = %s AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp
            """
            
            results = self.db.execute_query(query, (user_id, start_time, end_time))
            
            if not results:
                return {'error': 'No behavior data found'}
            
            analysis = {
                'user_id': user_id,
                'analysis_period': f"{time_window_days} days",
                'total_events': len(results),
                'event_frequency': {},
                'session_analysis': {},
                'preferred_times': {},
                'behavioral_insights': []
            }
            
            # 分析事件频率
            event_counts = {}
            session_events = {}
            hour_counts = {}
            
            for row in results:
                event_type = row['event_type']
                timestamp = row['timestamp']
                session_id = row['session_id']
                
                # 事件计数
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                # 会话分析
                if session_id:
                    if session_id not in session_events:
                        session_events[session_id] = []
                    session_events[session_id].append({
                        'event_type': event_type,
                        'timestamp': timestamp
                    })
                
                # 时间段分析
                hour = timestamp.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            analysis['event_frequency'] = event_counts
            
            # 会话分析
            if session_events:
                session_durations = []
                for session_id, events in session_events.items():
                    if len(events) >= 2:
                        start_time = min(event['timestamp'] for event in events)
                        end_time = max(event['timestamp'] for event in events)
                        duration = (end_time - start_time).total_seconds()
                        session_durations.append(duration)
                
                if session_durations:
                    analysis['session_analysis'] = {
                        'total_sessions': len(session_events),
                        'average_session_duration': sum(session_durations) / len(session_durations),
                        'max_session_duration': max(session_durations),
                        'min_session_duration': min(session_durations)
                    }
            
            # 时间段分析
            if hour_counts:
                analysis['preferred_times'] = dict(sorted(hour_counts.items()))
            
            # 生成行为洞察
            insights = self._generate_behavioral_insights(analysis, results)
            analysis['behavioral_insights'] = insights
            
            # 更新用户画像中的行为模式
            self._update_behavioral_patterns(user_id, analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze user behavior: {str(e)}")
            return {'error': str(e)}
    
    def calculate_engagement_score(self, user_id: str) -> float:
        """
        计算用户参与度分数
        
        Args:
            user_id: 用户ID
            
        Returns:
            float: 参与度分数 (0-100)
        """
        try:
            # 获取最近30天的行为数据
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)
            
            query = f"""
            SELECT COUNT(*) as event_count,
                   COUNT(DISTINCT DATE(timestamp)) as active_days,
                   COUNT(DISTINCT session_id) as session_count
            FROM {self.behavior_logs_table} 
            WHERE user_id = %s AND timestamp BETWEEN %s AND %s
            """
            
            results = self.db.execute_query(query, (user_id, start_time, end_time))
            
            if not results:
                return 0.0
            
            stats = results[0]
            event_count = stats['event_count'] or 0
            active_days = stats['active_days'] or 0
            session_count = stats['session_count'] or 0
            
            # 计算参与度分数
            frequency_score = min(event_count / 100.0, 1.0) * 40  # 最多40分
            consistency_score = min(active_days / 30.0, 1.0) * 30  # 最多30分
            depth_score = min(session_count / 20.0, 1.0) * 30  # 最多30分
            
            engagement_score = frequency_score + consistency_score + depth_score
            
            # 更新用户画像
            self.update_user_profile(user_id, {'engagement_score': engagement_score})
            
            return engagement_score
            
        except Exception as e:
            self.logger.error(f"Failed to calculate engagement score: {str(e)}")
            return 0.0
    
    def cluster_users_by_behavior(self, n_clusters: int = 4) -> Dict[str, Any]:
        """
        基于行为对用户进行聚类分析
        
        Args:
            n_clusters: 聚类数量
            
        Returns:
            Dict: 聚类分析结果
        """
        try:
            # 获取所有用户的行为特征
            query = f"""
            SELECT user_id, 
                   COUNT(*) as total_events,
                   COUNT(DISTINCT DATE(timestamp)) as active_days,
                   COUNT(DISTINCT session_id) as session_count,
                   COUNT(DISTINCT event_type) as unique_event_types
            FROM {self.behavior_logs_table} 
            WHERE timestamp >= %s
            GROUP BY user_id
            HAVING total_events >= 10
            """
            
            thirty_days_ago = datetime.now() - timedelta(days=30)
            results = self.db.execute_query(query, (thirty_days_ago,))
            
            if len(results) < n_clusters:
                return {'error': f'Not enough users for clustering (need {n_clusters}, have {len(results)})'}
            
            # 准备特征数据
            user_ids = []
            features = []
            
            for row in results:
                user_ids.append(row['user_id'])
                features.append([
                    row['total_events'],
                    row['active_days'],
                    row['session_count'],
                    row['unique_event_types']
                ])
            
            # 标准化特征
            features_array = np.array(features)
            features_scaled = self.scaler.fit_transform(features_array)
            
            # 执行K-means聚类
            self.kmeans_model = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = self.kmeans_model.fit_predict(features_scaled)
            
            # 分析聚类结果
            cluster_analysis = {
                'n_clusters': n_clusters,
                'total_users': len(user_ids),
                'clusters': {}
            }
            
            for i in range(n_clusters):
                cluster_users = [user_ids[j] for j in range(len(user_ids)) if clusters[j] == i]
                cluster_features = features_array[clusters == i]
                
                if len(cluster_features) > 0:
                    cluster_analysis['clusters'][f'cluster_{i}'] = {
                        'size': len(cluster_users),
                        'user_ids': cluster_users,
                        'centroid': self.kmeans_model.cluster_centers_[i].tolist(),
                        'characteristics': {
                            'avg_events': float(np.mean(cluster_features[:, 0])),
                            'avg_active_days': float(np.mean(cluster_features[:, 1])),
                            'avg_sessions': float(np.mean(cluster_features[:, 2])),
                            'avg_event_types': float(np.mean(cluster_features[:, 3]))
                        }
                    }
            
            return cluster_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to cluster users: {str(e)}")
            return {'error': str(e)}
    
    def get_user_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户个性化推荐
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 推荐列表
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return []
            
            recommendations = []
            
            # 基于学习风格的推荐
            learning_style = profile.learning_profile.learning_style
            if learning_style == "visual":
                recommendations.append({
                    'type': 'learning_style',
                    'title': '视觉学习增强',
                    'description': '建议使用图表和可视化工具来增强学习效果',
                    'priority': 'high',
                    'reason': '检测到您偏好视觉学习风格'
                })
            elif learning_style == "auditory":
                recommendations.append({
                    'type': 'learning_style',
                    'title': '听觉学习优化',
                    'description': '尝试使用语音交互和音频内容',
                    'priority': 'high',
                    'reason': '检测到您偏好听觉学习风格'
                })
            
            # 基于技能等级的推荐
            if profile.tier == UserTier.NOVICE:
                recommendations.append({
                    'type': 'skill_development',
                    'title': '新手引导',
                    'description': '完成基础教程以快速上手系统功能',
                    'priority': 'high',
                    'reason': '检测到您是新手用户'
                })
            elif profile.tier == UserTier.EXPERT:
                recommendations.append({
                    'type': 'skill_development',
                    'title': '高级功能探索',
                    'description': '尝试使用高级功能和自定义配置',
                    'priority': 'medium',
                    'reason': '检测到您是专家级用户'
                })
            
            # 基于参与度的推荐
            if profile.engagement_score < 50:
                recommendations.append({
                    'type': 'engagement',
                    'title': '提高参与度',
                    'description': '尝试探索系统的新功能和使用场景',
                    'priority': 'medium',
                    'reason': '检测到您的参与度较低'
                })
            
            # 基于行为模式的推荐
            behavioral_patterns = profile.behavioral_patterns
            if behavioral_patterns.error_rate > 0.1:
                recommendations.append({
                    'type': 'usability',
                    'title': '错误率优化',
                    'description': '查看常见问题和使用技巧',
                    'priority': 'high',
                    'reason': f'检测到错误率较高 ({behavioral_patterns.error_rate:.1%})'
                })
            
            return recommendations[:5]  # 返回前5个推荐
            
        except Exception as e:
            self.logger.error(f"Failed to get user recommendations: {str(e)}")
            return []
    
    def _generate_behavioral_insights(self, analysis: Dict[str, Any], 
                                    behavior_data: List[Dict]) -> List[str]:
        """生成行为洞察"""
        insights = []
        
        # 分析事件频率
        event_frequency = analysis['event_frequency']
        if event_frequency:
            most_common_event = max(event_frequency.items(), key=lambda x: x[1])
            insights.append(f"最常用功能: {most_common_event[0]} (使用{most_common_event[1]}次)")
        
        # 分析时间段偏好
        preferred_times = analysis['preferred_times']
        if preferred_times:
            peak_hour = max(preferred_times.items(), key=lambda x: x[1])[0]
            if 6 <= peak_hour <= 10:
                time_period = "早晨"
            elif 11 <= peak_hour <= 13:
                time_period = "中午"
            elif 14 <= peak_hour <= 18:
                time_period = "下午"
            else:
                time_period = "晚上"
            insights.append(f"偏好使用时段: {time_period} ({peak_hour}时)")
        
        # 分析会话模式
        session_analysis = analysis.get('session_analysis', {})
        if session_analysis:
            avg_duration = session_analysis.get('average_session_duration', 0)
            if avg_duration > 600:  # 10分钟
                insights.append("会话持续时间较长，显示深度使用模式")
            elif avg_duration < 60:  # 1分钟
                insights.append("会话持续时间较短，可能为快速查询使用")
        
        return insights
    
    def _update_behavioral_patterns(self, user_id: str, analysis: Dict[str, Any]):
        """更新用户行为模式"""
        try:
            updates = {
                'behavioral_patterns': {}
            }
            
            # 更新会话时长
            session_analysis = analysis.get('session_analysis', {})
            if session_analysis:
                updates['behavioral_patterns']['average_session_duration'] = \
                    session_analysis.get('average_session_duration', 0)
            
            # 更新交互频率
            total_events = analysis.get('total_events', 0)
            if total_events > 100:
                frequency = "high"
            elif total_events > 30:
                frequency = "medium"
            else:
                frequency = "low"
            updates['behavioral_patterns']['interaction_frequency'] = frequency
            
            # 更新错误率（简化计算）
            error_events = analysis['event_frequency'].get('error', 0)
            updates['behavioral_patterns']['error_rate'] = error_events / total_events if total_events > 0 else 0
            
            # 应用更新
            self.update_user_profile(user_id, updates)
            
        except Exception as e:
            self.logger.debug(f"Failed to update behavioral patterns: {str(e)}")

