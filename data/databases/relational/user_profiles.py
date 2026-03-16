"""
用户画像模块 - 管理用户个人信息和偏好设置
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class UserPreferenceCategory(Enum):
    """用户偏好分类枚举"""
    APPEARANCE = "appearance"
    BEHAVIOR = "behavior"
    NOTIFICATION = "notification"
    PRIVACY = "privacy"
    ACCESSIBILITY = "accessibility"

class LearningStyle(Enum):
    """学习风格枚举"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"

@dataclass
class UserProfile:
    """用户画像数据类"""
    user_id: str
    username: str
    email: str
    full_name: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    preferences: Dict[str, Any]
    learning_style: LearningStyle
    skill_level: str  # beginner, intermediate, advanced, expert
    interests: List[str]
    usage_stats: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class UserPreference:
    """用户偏好数据类"""
    user_id: str
    category: UserPreferenceCategory
    preference_key: str
    preference_value: Any
    updated_at: datetime

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
        self.preferences_table = config.get('preferences_table', 'user_preferences')
        
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
                'full_name': 'VARCHAR(255)',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'last_login': 'TIMESTAMP',
                'preferences': 'TEXT',  # JSON格式
                'learning_style': 'VARCHAR(50)',
                'skill_level': 'VARCHAR(50)',
                'interests': 'TEXT',  # JSON格式
                'usage_stats': 'TEXT',  # JSON格式
                'metadata': 'TEXT'  # JSON格式
            }
            
            self.db.create_table(self.profiles_table, profile_schema)
            
            # 用户偏好表
            preference_schema = {
                'id': 'SERIAL PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'category': 'VARCHAR(50) NOT NULL',
                'preference_key': 'VARCHAR(100) NOT NULL',
                'preference_value': 'TEXT NOT NULL',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            constraints = [
                'FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE',
                'UNIQUE(user_id, category, preference_key)'
            ]
            
            self.db.create_table(self.preferences_table, preference_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.profiles_table, 'username', unique=True)
            self.db.create_index(self.profiles_table, 'email')
            self.db.create_index(self.preferences_table, 'user_id')
            self.db.create_index(self.preferences_table, 'category')
            
            self.logger.info("User profile tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user profile tables: {str(e)}")
            raise
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> bool:
        """
        创建用户画像
        
        Args:
            user_data: 用户数据
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 准备数据
            profile_data = {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'email': user_data.get('email'),
                'full_name': user_data.get('full_name'),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'learning_style': user_data.get('learning_style', LearningStyle.VISUAL.value),
                'skill_level': user_data.get('skill_level', 'beginner'),
                'preferences': json.dumps(user_data.get('preferences', {})),
                'interests': json.dumps(user_data.get('interests', [])),
                'usage_stats': json.dumps(user_data.get('usage_stats', {})),
                'metadata': json.dumps(user_data.get('metadata', {}))
            }
            
            # 插入数据库
            self.db.execute_insert(self.profiles_table, profile_data)
            
            # 创建默认偏好设置
            self._create_default_preferences(user_data['user_id'])
            
            self.logger.info(f"User profile created: {user_data['user_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create user profile: {str(e)}")
            return False
    
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
                full_name=profile_data['full_name'],
                created_at=profile_data['created_at'],
                updated_at=profile_data['updated_at'],
                last_login=profile_data['last_login'],
                preferences=json.loads(profile_data['preferences']),
                learning_style=LearningStyle(profile_data['learning_style']),
                skill_level=profile_data['skill_level'],
                interests=json.loads(profile_data['interests']),
                usage_stats=json.loads(profile_data['usage_stats']),
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
            # 准备更新数据
            update_data = {'updated_at': datetime.now()}
            
            # 处理JSON字段
            json_fields = ['preferences', 'interests', 'usage_stats', 'metadata']
            for field in json_fields:
                if field in updates:
                    update_data[field] = json.dumps(updates[field])
            
            # 处理其他字段
            regular_fields = ['username', 'email', 'full_name', 'learning_style', 'skill_level', 'last_login']
            for field in regular_fields:
                if field in updates:
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
                self.logger.warning(f"User profile not found: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update user profile: {str(e)}")
            return False
    
    def update_user_preference(self, user_id: str, category: UserPreferenceCategory,
                             preference_key: str, preference_value: Any) -> bool:
        """
        更新用户偏好设置
        
        Args:
            user_id: 用户ID
            category: 偏好分类
            preference_key: 偏好键
            preference_value: 偏好值
            
        Returns:
            bool: 更新是否成功
        """
        try:
            preference_data = {
                'user_id': user_id,
                'category': category.value,
                'preference_key': preference_key,
                'preference_value': json.dumps(preference_value),
                'updated_at': datetime.now()
            }
            
            # 使用UPSERT（插入或更新）
            if isinstance(self.db, PostgreSQLIntegration):
                query = f"""
                INSERT INTO {self.preferences_table} 
                (user_id, category, preference_key, preference_value, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, category, preference_key) 
                DO UPDATE SET 
                    preference_value = EXCLUDED.preference_value,
                    updated_at = EXCLUDED.updated_at
                """
            else:  # SQLite
                query = f"""
                INSERT OR REPLACE INTO {self.preferences_table} 
                (user_id, category, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """
            
            self.db.execute_query(
                query,
                (
                    user_id,
                    category.value,
                    preference_key,
                    json.dumps(preference_value),
                    datetime.now()
                )
            )
            
            self.logger.debug(f"User preference updated: {user_id}.{category.value}.{preference_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update user preference: {str(e)}")
            return False
    
    def get_user_preferences(self, user_id: str, category: UserPreferenceCategory = None) -> Dict[str, Any]:
        """
        获取用户偏好设置
        
        Args:
            user_id: 用户ID
            category: 偏好分类（可选）
            
        Returns:
            Dict: 用户偏好设置
        """
        try:
            if category:
                query = f"""
                SELECT preference_key, preference_value 
                FROM {self.preferences_table} 
                WHERE user_id = %s AND category = %s
                """
                params = (user_id, category.value)
            else:
                query = f"""
                SELECT category, preference_key, preference_value 
                FROM {self.preferences_table} 
                WHERE user_id = %s
                """
                params = (user_id,)
            
            results = self.db.execute_query(query, params)
            
            preferences = {}
            for row in results:
                if category:
                    # 单分类模式
                    key = row['preference_key']
                    value = json.loads(row['preference_value'])
                    preferences[key] = value
                else:
                    # 多分类模式
                    cat = row['category']
                    key = row['preference_key']
                    value = json.loads(row['preference_value'])
                    
                    if cat not in preferences:
                        preferences[cat] = {}
                    preferences[cat][key] = value
            
            return preferences
            
        except Exception as e:
            self.logger.error(f"Failed to get user preferences: {str(e)}")
            return {}
    
    def record_user_activity(self, user_id: str, activity_type: str, 
                           details: Dict[str, Any] = None) -> bool:
        """
        记录用户活动
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            details: 活动详情
            
        Returns:
            bool: 记录是否成功
        """
        try:
            # 获取当前使用统计
            profile = self.get_user_profile(user_id)
            if not profile:
                self.logger.warning(f"User profile not found: {user_id}")
                return False
            
            usage_stats = profile.usage_stats
            current_time = datetime.now().isoformat()
            
            # 更新活动计数
            if 'activity_counts' not in usage_stats:
                usage_stats['activity_counts'] = {}
            
            usage_stats['activity_counts'][activity_type] = \
                usage_stats['activity_counts'].get(activity_type, 0) + 1
            
            # 记录最近活动
            if 'recent_activities' not in usage_stats:
                usage_stats['recent_activities'] = []
            
            activity_record = {
                'type': activity_type,
                'timestamp': current_time,
                'details': details or {}
            }
            
            usage_stats['recent_activities'].insert(0, activity_record)
            # 保留最近100条活动记录
            usage_stats['recent_activities'] = usage_stats['recent_activities'][:100]
            
            # 更新最后活动时间
            usage_stats['last_activity'] = current_time
            usage_stats['last_activity_type'] = activity_type
            
            # 保存更新
            return self.update_user_profile(user_id, {'usage_stats': usage_stats})
            
        except Exception as e:
            self.logger.error(f"Failed to record user activity: {str(e)}")
            return False
    
    def analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """
        分析用户行为模式
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 行为分析结果
        """
        try:
            profile = self.get_user_profile(user_id)
            if not profile:
                return {'error': 'User profile not found'}
            
            analysis = {
                'user_id': user_id,
                'analysis_time': datetime.now().isoformat(),
                'usage_patterns': {},
                'preference_insights': {},
                'recommendations': []
            }
            
            usage_stats = profile.usage_stats
            
            # 分析活动模式
            activity_counts = usage_stats.get('activity_counts', {})
            total_activities = sum(activity_counts.values())
            
            if total_activities > 0:
                for activity_type, count in activity_counts.items():
                    percentage = (count / total_activities) * 100
                    analysis['usage_patterns'][activity_type] = {
                        'count': count,
                        'percentage': round(percentage, 2)
                    }
            
            # 分析学习风格适应性
            learning_style = profile.learning_style
            analysis['preference_insights']['learning_style'] = {
                'current': learning_style.value,
                'compatibility_score': self._calculate_learning_compatibility(profile)
            }
            
            # 生成个性化推荐
            analysis['recommendations'] = self._generate_recommendations(profile)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze user behavior: {str(e)}")
            return {'error': str(e)}
    
    def search_users(self, criteria: Dict[str, Any], limit: int = 100) -> List[UserProfile]:
        """
        搜索用户
        
        Args:
            criteria: 搜索条件
            limit: 返回结果限制
            
        Returns:
            List[UserProfile]: 匹配的用户列表
        """
        try:
            where_conditions = []
            params = []
            
            # 构建查询条件
            if 'username' in criteria:
                where_conditions.append("username ILIKE %s")
                params.append(f"%{criteria['username']}%")
            
            if 'email' in criteria:
                where_conditions.append("email ILIKE %s")
                params.append(f"%{criteria['email']}%")
            
            if 'skill_level' in criteria:
                where_conditions.append("skill_level = %s")
                params.append(criteria['skill_level'])
            
            if 'learning_style' in criteria:
                where_conditions.append("learning_style = %s")
                params.append(criteria['learning_style'])
            
            # 构建查询
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            query = f"SELECT * FROM {self.profiles_table} WHERE {where_clause} LIMIT %s"
            params.append(limit)
            
            results = self.db.execute_query(query, tuple(params))
            
            profiles = []
            for row in results:
                profile = UserProfile(
                    user_id=row['user_id'],
                    username=row['username'],
                    email=row['email'],
                    full_name=row['full_name'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    last_login=row['last_login'],
                    preferences=json.loads(row['preferences']),
                    learning_style=LearningStyle(row['learning_style']),
                    skill_level=row['skill_level'],
                    interests=json.loads(row['interests']),
                    usage_stats=json.loads(row['usage_stats']),
                    metadata=json.loads(row['metadata'])
                )
                profiles.append(profile)
            
            return profiles
            
        except Exception as e:
            self.logger.error(f"Failed to search users: {str(e)}")
            return []
    
    def delete_user_profile(self, user_id: str) -> bool:
        """
        删除用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 删除用户偏好（外键约束会自动处理）
            affected = self.db.execute_delete(
                self.profiles_table,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                self.logger.info(f"User profile deleted: {user_id}")
                return True
            else:
                self.logger.warning(f"User profile not found: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete user profile: {str(e)}")
            return False
    
    def _create_default_preferences(self, user_id: str):
        """创建默认偏好设置"""
        default_preferences = {
            UserPreferenceCategory.APPEARANCE: {
                'theme': 'light',
                'language': 'zh-CN',
                'font_size': 'medium'
            },
            UserPreferenceCategory.BEHAVIOR: {
                'auto_save': True,
                'confirm_actions': True,
                'keyboard_shortcuts': True
            },
            UserPreferenceCategory.NOTIFICATION: {
                'email_notifications': False,
                'push_notifications': True,
                'sound_effects': True
            },
            UserPreferenceCategory.PRIVACY: {
                'data_collection': True,
                'analytics': True,
                'personalized_ads': False
            }
        }
        
        for category, prefs in default_preferences.items():
            for key, value in prefs:
                self.update_user_preference(user_id, category, key, value)
    
    def _calculate_learning_compatibility(self, profile: UserProfile) -> float:
        """计算学习风格兼容性分数"""
        # 简化的兼容性计算
        # 实际项目中可以根据用户活动数据调整
        base_score = 0.7
        
        # 根据技能水平调整
        skill_adjustments = {
            'beginner': 0.1,
            'intermediate': 0.0,
            'advanced': -0.1,
            'expert': -0.2
        }
        
        adjustment = skill_adjustments.get(profile.skill_level, 0.0)
        return min(1.0, max(0.0, base_score + adjustment))
    
    def _generate_recommendations(self, profile: UserProfile) -> List[str]:
        """生成个性化推荐"""
        recommendations = []
        
        # 基于学习风格的推荐
        if profile.learning_style == LearningStyle.VISUAL:
            recommendations.append("尝试使用图表和可视化工具来增强学习效果")
        elif profile.learning_style == LearningStyle.AUDITORY:
            recommendations.append("使用语音交互和音频内容可能更适合您的学习风格")
        
        # 基于技能水平的推荐
        if profile.skill_level == 'beginner':
            recommendations.append("从基础教程开始，逐步建立知识体系")
        elif profile.skill_level == 'expert':
            recommendations.append("尝试挑战高级功能或参与社区贡献")
        
        # 基于使用模式的推荐
        usage_stats = profile.usage_stats
        activity_counts = usage_stats.get('activity_counts', {})
        
        if activity_counts.get('voice_interaction', 0) < 5:
            recommendations.append("尝试使用语音交互功能，可能提高效率")
        
        return recommendations

