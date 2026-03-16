"""
用户偏好模块 - 管理用户个性化设置和偏好配置
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ThemePreference(Enum):
    """主题偏好枚举"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"

class LanguagePreference(Enum):
    """语言偏好枚举"""
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"

class NotificationPreference(Enum):
    """通知偏好枚举"""
    ALL = "all"
    IMPORTANT = "important"
    NONE = "none"

@dataclass
class UIPreferences:
    """界面偏好设置"""
    theme: ThemePreference = ThemePreference.LIGHT
    language: LanguagePreference = LanguagePreference.ZH_CN
    font_size: str = "medium"  # small, medium, large
    density: str = "comfortable"  # compact, comfortable, spacious
    animations: bool = True
    reduce_motion: bool = False
    high_contrast: bool = False

@dataclass
class InteractionPreferences:
    """交互偏好设置"""
    voice_interaction: bool = True
    gesture_controls: bool = False
    keyboard_shortcuts: bool = True
    auto_complete: bool = True
    confirm_actions: bool = True
    timeout_duration: int = 300  # 秒

@dataclass
class ContentPreferences:
    """内容偏好设置"""
    content_filter: str = "moderate"  # strict, moderate, lenient
    preferred_topics: List[str] = None
    excluded_topics: List[str] = None
    content_depth: str = "balanced"  # basic, balanced, detailed
    learning_style: str = "interactive"  # interactive, demonstrative, exploratory

@dataclass
class PrivacyPreferences:
    """隐私偏好设置"""
    data_collection: bool = True
    personalized_ads: bool = False
    analytics_tracking: bool = True
    data_retention: str = "standard"  # minimal, standard, extended
    third_party_sharing: bool = False

@dataclass
class UserPreferences:
    """完整用户偏好数据类"""
    user_id: str
    ui_preferences: UIPreferences
    interaction_preferences: InteractionPreferences
    content_preferences: ContentPreferences
    privacy_preferences: PrivacyPreferences
    notification_preferences: Dict[str, NotificationPreference]
    custom_shortcuts: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    version: str

class UserPreferencesManager:
    """用户偏好管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化用户偏好管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.preferences_table = config.get('preferences_table', 'user_preferences')
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化用户偏好相关表"""
        try:
            preferences_schema = {
                'user_id': 'VARCHAR(100) PRIMARY KEY',
                'ui_preferences': 'TEXT NOT NULL',
                'interaction_preferences': 'TEXT NOT NULL',
                'content_preferences': 'TEXT NOT NULL',
                'privacy_preferences': 'TEXT NOT NULL',
                'notification_preferences': 'TEXT NOT NULL',
                'custom_shortcuts': 'TEXT NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'version': 'VARCHAR(20) DEFAULT "1.0"'
            }
            
            constraints = [
                'FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.preferences_table, preferences_schema, constraints)
            
            self.logger.info("User preferences table initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user preferences table: {str(e)}")
            raise
    
    def initialize_default_preferences(self, user_id: str) -> bool:
        """
        初始化默认用户偏好
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 创建默认偏好设置
            preferences = UserPreferences(
                user_id=user_id,
                ui_preferences=UIPreferences(),
                interaction_preferences=InteractionPreferences(),
                content_preferences=ContentPreferences(),
                privacy_preferences=PrivacyPreferences(),
                notification_preferences={
                    'system': NotificationPreference.IMPORTANT,
                    'updates': NotificationPreference.ALL,
                    'recommendations': NotificationPreference.IMPORTANT,
                    'security': NotificationPreference.ALL
                },
                custom_shortcuts={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
                version="1.0"
            )
            
            # 准备数据库数据
            db_data = {
                'user_id': preferences.user_id,
                'ui_preferences': json.dumps(asdict(preferences.ui_preferences)),
                'interaction_preferences': json.dumps(asdict(preferences.interaction_preferences)),
                'content_preferences': json.dumps(asdict(preferences.content_preferences)),
                'privacy_preferences': json.dumps(asdict(preferences.privacy_preferences)),
                'notification_preferences': json.dumps(
                    {k: v.value for k, v in preferences.notification_preferences.items()}
                ),
                'custom_shortcuts': json.dumps(preferences.custom_shortcuts),
                'created_at': preferences.created_at,
                'updated_at': preferences.updated_at,
                'version': preferences.version
            }
            
            # 插入数据库
            self.db.execute_insert(self.preferences_table, db_data)
            
            self.logger.info(f"Default preferences initialized for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default preferences: {str(e)}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        获取用户偏好设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            UserPreferences: 用户偏好设置，如果不存在返回None
        """
        try:
            query = f"SELECT * FROM {self.preferences_table} WHERE user_id = %s"
            results = self.db.execute_query(query, (user_id,))
            
            if not results:
                # 如果没有找到偏好设置，初始化默认设置
                if self.initialize_default_preferences(user_id):
                    return self.get_user_preferences(user_id)
                else:
                    return None
            
            pref_data = results[0]
            
            # 转换为UserPreferences对象
            return UserPreferences(
                user_id=pref_data['user_id'],
                ui_preferences=UIPreferences(**json.loads(pref_data['ui_preferences'])),
                interaction_preferences=InteractionPreferences(**json.loads(pref_data['interaction_preferences'])),
                content_preferences=ContentPreferences(**json.loads(pref_data['content_preferences'])),
                privacy_preferences=PrivacyPreferences(**json.loads(pref_data['privacy_preferences'])),
                notification_preferences={
                    k: NotificationPreference(v) 
                    for k, v in json.loads(pref_data['notification_preferences']).items()
                },
                custom_shortcuts=json.loads(pref_data['custom_shortcuts']),
                created_at=pref_data['created_at'],
                updated_at=pref_data['updated_at'],
                version=pref_data['version']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get user preferences: {str(e)}")
            return None
    
    def update_preferences(self, user_id: str, category: str, 
                         updates: Dict[str, Any]) -> bool:
        """
        更新用户偏好设置
        
        Args:
            user_id: 用户ID
            category: 偏好类别 (ui, interaction, content, privacy, notifications, shortcuts)
            updates: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取现有偏好设置
            existing_prefs = self.get_user_preferences(user_id)
            if not existing_prefs:
                self.logger.warning(f"User preferences not found: {user_id}")
                return False
            
            # 准备更新数据
            update_data = {
                'updated_at': datetime.now()
            }
            
            # 根据类别更新相应的偏好设置
            if category == 'ui':
                current_ui = asdict(existing_prefs.ui_preferences)
                current_ui.update(updates)
                update_data['ui_preferences'] = json.dumps(current_ui)
                
            elif category == 'interaction':
                current_interaction = asdict(existing_prefs.interaction_preferences)
                current_interaction.update(updates)
                update_data['interaction_preferences'] = json.dumps(current_interaction)
                
            elif category == 'content':
                current_content = asdict(existing_prefs.content_preferences)
                current_content.update(updates)
                update_data['content_preferences'] = json.dumps(current_content)
                
            elif category == 'privacy':
                current_privacy = asdict(existing_prefs.privacy_preferences)
                current_privacy.update(updates)
                update_data['privacy_preferences'] = json.dumps(current_privacy)
                
            elif category == 'notifications':
                current_notifications = {
                    k: v.value for k, v in existing_prefs.notification_preferences.items()
                }
                current_notifications.update(updates)
                update_data['notification_preferences'] = json.dumps(current_notifications)
                
            elif category == 'shortcuts':
                current_shortcuts = existing_prefs.custom_shortcuts.copy()
                current_shortcuts.update(updates)
                update_data['custom_shortcuts'] = json.dumps(current_shortcuts)
                
            else:
                self.logger.error(f"Invalid preference category: {category}")
                return False
            
            # 执行更新
            affected = self.db.execute_update(
                self.preferences_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                self.logger.info(f"User preferences updated: {user_id} - {category}")
                return True
            else:
                self.logger.warning(f"User preferences not found for update: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update user preferences: {str(e)}")
            return False
    
    def get_preference_value(self, user_id: str, category: str, 
                           key: str, default: Any = None) -> Any:
        """
        获取特定偏好值
        
        Args:
            user_id: 用户ID
            category: 偏好类别
            key: 偏好键
            default: 默认值
            
        Returns:
            Any: 偏好值
        """
        try:
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                return default
            
            if category == 'ui':
                return getattr(preferences.ui_preferences, key, default)
            elif category == 'interaction':
                return getattr(preferences.interaction_preferences, key, default)
            elif category == 'content':
                return getattr(preferences.content_preferences, key, default)
            elif category == 'privacy':
                return getattr(preferences.privacy_preferences, key, default)
            elif category == 'notifications':
                return preferences.notification_preferences.get(key, default)
            elif category == 'shortcuts':
                return preferences.custom_shortcuts.get(key, default)
            else:
                return default
                
        except Exception as e:
            self.logger.error(f"Failed to get preference value: {str(e)}")
            return default
    
    def set_preference_value(self, user_id: str, category: str, 
                           key: str, value: Any) -> bool:
        """
        设置特定偏好值
        
        Args:
            user_id: 用户ID
            category: 偏好类别
            key: 偏好键
            value: 偏好值
            
        Returns:
            bool: 设置是否成功
        """
        return self.update_preferences(user_id, category, {key: value})
    
    def export_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        导出用户偏好设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 导出的偏好设置
        """
        try:
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                return {'error': 'Preferences not found'}
            
            # 转换为可序列化格式
            export_data = {
                'user_id': preferences.user_id,
                'ui_preferences': asdict(preferences.ui_preferences),
                'interaction_preferences': asdict(preferences.interaction_preferences),
                'content_preferences': asdict(preferences.content_preferences),
                'privacy_preferences': asdict(preferences.privacy_preferences),
                'notification_preferences': {
                    k: v.value for k, v in preferences.notification_preferences.items()
                },
                'custom_shortcuts': preferences.custom_shortcuts,
                'version': preferences.version,
                'exported_at': datetime.now().isoformat()
            }
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Failed to export preferences: {str(e)}")
            return {'error': str(e)}
    
    def import_preferences(self, user_id: str, import_data: Dict[str, Any]) -> bool:
        """
        导入用户偏好设置
        
        Args:
            user_id: 用户ID
            import_data: 导入数据
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 验证导入数据
            required_categories = [
                'ui_preferences', 'interaction_preferences', 
                'content_preferences', 'privacy_preferences'
            ]
            
            for category in required_categories:
                if category not in import_data:
                    self.logger.error(f"Missing required category in import data: {category}")
                    return False
            
            # 更新所有偏好设置
            updates = {
                'ui_preferences': import_data['ui_preferences'],
                'interaction_preferences': import_data['interaction_preferences'],
                'content_preferences': import_data['content_preferences'],
                'privacy_preferences': import_data['privacy_preferences']
            }
            
            if 'notification_preferences' in import_data:
                updates['notification_preferences'] = import_data['notification_preferences']
            
            if 'custom_shortcuts' in import_data:
                updates['shortcuts'] = import_data['custom_shortcuts']
            
            # 执行更新
            for category, data in updates.items():
                if category == 'shortcuts':
                    category = 'shortcuts'
                success = self.update_preferences(user_id, category, data)
                if not success:
                    self.logger.error(f"Failed to import {category} preferences")
                    return False
            
            self.logger.info(f"Preferences imported for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import preferences: {str(e)}")
            return False
    
    def reset_preferences(self, user_id: str, category: str = None) -> bool:
        """
        重置用户偏好设置
        
        Args:
            user_id: 用户ID
            category: 重置的类别（为空则重置所有）
            
        Returns:
            bool: 重置是否成功
        """
        try:
            if category is None:
                # 重置所有偏好设置
                return self.initialize_default_preferences(user_id)
            else:
                # 重置特定类别
                default_prefs = UserPreferences(
                    user_id=user_id,
                    ui_preferences=UIPreferences(),
                    interaction_preferences=InteractionPreferences(),
                    content_preferences=ContentPreferences(),
                    privacy_preferences=PrivacyPreferences(),
                    notification_preferences={},
                    custom_shortcuts={},
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    version="1.0"
                )
                
                if category == 'ui':
                    default_data = asdict(default_prefs.ui_preferences)
                elif category == 'interaction':
                    default_data = asdict(default_prefs.interaction_preferences)
                elif category == 'content':
                    default_data = asdict(default_prefs.content_preferences)
                elif category == 'privacy':
                    default_data = asdict(default_prefs.privacy_preferences)
                elif category == 'notifications':
                    default_data = {k: v.value for k, v in default_prefs.notification_preferences.items()}
                elif category == 'shortcuts':
                    default_data = default_prefs.custom_shortcuts
                else:
                    self.logger.error(f"Invalid preference category for reset: {category}")
                    return False
                
                return self.update_preferences(user_id, category, default_data)
                
        except Exception as e:
            self.logger.error(f"Failed to reset preferences: {str(e)}")
            return False
    
    def get_preferences_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取偏好设置摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 偏好设置摘要
        """
        try:
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                return {'error': 'Preferences not found'}
            
            summary = {
                'user_id': user_id,
                'theme': preferences.ui_preferences.theme.value,
                'language': preferences.ui_preferences.language.value,
                'voice_interaction': preferences.interaction_preferences.voice_interaction,
                'content_depth': preferences.content_preferences.content_depth,
                'data_collection': preferences.privacy_preferences.data_collection,
                'notification_levels': len(preferences.notification_preferences),
                'custom_shortcuts_count': len(preferences.custom_shortcuts),
                'last_updated': preferences.updated_at.isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get preferences summary: {str(e)}")
            return {'error': str(e)}
    
    def migrate_preferences(self, user_id: str, from_version: str, to_version: str) -> bool:
        """
        迁移用户偏好设置
        
        Args:
            user_id: 用户ID
            from_version: 原版本
            to_version: 目标版本
            
        Returns:
            bool: 迁移是否成功
        """
        try:
            preferences = self.get_user_preferences(user_id)
            if not preferences:
                return False
            
            # 版本迁移逻辑
            migration_actions = []
            
            if from_version == "1.0" and to_version == "1.1":
                # 在1.1版本中添加了新功能
                migration_actions.append(("interaction", "auto_save", True))
                migration_actions.append(("ui", "reduce_motion", False))
            
            elif from_version == "1.1" and to_version == "1.2":
                # 在1.2版本中更新了隐私设置
                migration_actions.append(("privacy", "data_retention", "standard"))
                migration_actions.append(("notifications", "analytics", "important"))
            
            # 执行迁移操作
            for category, key, value in migration_actions:
                self.set_preference_value(user_id, category, key, value)
            
            # 更新版本号
            update_data = {
                'version': to_version,
                'updated_at': datetime.now()
            }
            
            self.db.execute_update(
                self.preferences_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            self.logger.info(f"Preferences migrated from {from_version} to {to_version} for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate preferences: {str(e)}")
            return False
