"""
用户数据模块 - 管理用户个性化数据、偏好设置、交互历史等
"""

from .profiles import UserProfiles, UserProfile, UserDemographics, BehavioralPatterns, LearningProfile, UserTier, PersonalityType
from .preferences import UserPreferencesManager, UserPreferences, UIPreferences, InteractionPreferences, ContentPreferences, PrivacyPreferences, ThemePreference, LanguagePreference, NotificationPreference
from .history import InteractionHistory, InteractionRecord, InteractionType, InteractionStatus, InteractionContext, InteractionResult
from .documents import UserDocuments, UserDocument, DocumentType, DocumentStatus, DocumentMetadata, DocumentVersion, DocumentPermissions
from .conversations import ConversationManager, Conversation, ConversationType, MessageRole, ConversationStatus, Message, MessageContent, ConversationContext
from .learning_data import LearningDataManager, LearningProgress, LearningSession, LearningPath, SkillAssessment, KnowledgeComponent, LearningDomain, ProficiencyLevel, LearningStyle
from .customization import CustomizationManager, UserCustomization, ColorCustomization, LayoutCustomization, AnimationCustomization, BehaviorCustomization, ContentCustomization, AccessibilityCustomization, WorkspaceCustomization, ColorScheme, LayoutStyle, AnimationStyle
from .backup_manager import BackupManager, BackupMetadata, BackupSchedule, BackupRecord, BackupType, BackupStatus, CompressionMethod

__all__ = [
    # 用户画像
    'UserProfiles', 'UserProfile', 'UserDemographics', 'BehavioralPatterns', 
    'LearningProfile', 'UserTier', 'PersonalityType',
    
    # 用户偏好
    'UserPreferencesManager', 'UserPreferences', 'UIPreferences', 
    'InteractionPreferences', 'ContentPreferences', 'PrivacyPreferences',
    'ThemePreference', 'LanguagePreference', 'NotificationPreference',
    
    # 交互历史
    'InteractionHistory', 'InteractionRecord', 'InteractionType', 
    'InteractionStatus', 'InteractionContext', 'InteractionResult',
    
    # 用户文档
    'UserDocuments', 'UserDocument', 'DocumentType', 'DocumentStatus',
    'DocumentMetadata', 'DocumentVersion', 'DocumentPermissions',
    
    # 对话管理
    'ConversationManager', 'Conversation', 'ConversationType', 'MessageRole',
    'ConversationStatus', 'Message', 'MessageContent', 'ConversationContext',
    
    # 学习数据
    'LearningDataManager', 'LearningProgress', 'LearningSession', 'LearningPath',
    'SkillAssessment', 'KnowledgeComponent', 'LearningDomain', 'ProficiencyLevel',
    'LearningStyle',
    
    # 个性化设置
    'CustomizationManager', 'UserCustomization', 'ColorCustomization',
    'LayoutCustomization', 'AnimationCustomization', 'BehaviorCustomization',
    'ContentCustomization', 'AccessibilityCustomization', 'WorkspaceCustomization',
    'ColorScheme', 'LayoutStyle', 'AnimationStyle',
    
    # 备份管理
    'BackupManager', 'BackupMetadata', 'BackupSchedule', 'BackupRecord',
    'BackupType', 'BackupStatus', 'CompressionMethod'
]

# 模块版本
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "用户数据管理模块 - 提供完整的用户数据存储、管理和分析功能"

def initialize_module(db_integration, config: dict):
    """
    初始化用户数据模块
    
    Args:
        db_integration: 数据库集成实例
        config: 配置字典
        
    Returns:
        dict: 初始化后的管理器实例
    """
    managers = {}
    
    try:
        # 初始化用户画像管理器
        managers['profiles'] = UserProfiles(db_integration, config)
        
        # 初始化用户偏好管理器
        managers['preferences'] = UserPreferencesManager(db_integration, config)
        
        # 初始化交互历史管理器
        managers['history'] = InteractionHistory(db_integration, config)
        
        # 初始化用户文档管理器
        storage_config = config.get('storage', {})
        managers['documents'] = UserDocuments(db_integration, None, storage_config)  # 需要实际的存储管理器
        
        # 初始化对话管理器
        managers['conversations'] = ConversationManager(db_integration, config)
        
        # 初始化学习数据管理器
        cognitive_config = config.get('cognitive', {})
        managers['learning_data'] = LearningDataManager(db_integration, None, cognitive_config)  # 需要实际的认知引擎
        
        # 初始化个性化设置管理器
        managers['customization'] = CustomizationManager(db_integration, config)
        
        # 初始化备份管理器
        backup_config = config.get('backup', {})
        managers['backup'] = BackupManager(db_integration, None, backup_config)  # 需要实际的存储管理器
        
        print("用户数据模块初始化完成")
        return managers
        
    except Exception as e:
        print(f"用户数据模块初始化失败: {str(e)}")
        raise

def get_module_info():
    """
    获取模块信息
    
    Returns:
        dict: 模块信息
    """
    return {
        'name': '用户数据模块',
        'version': __version__,
        'description': __description__,
        'author': __author__,
        'components': [
            '用户画像管理',
            '用户偏好设置', 
            '交互历史记录',
            '用户文档管理',
            '对话管理',
            '学习数据管理',
            '个性化设置',
            '备份恢复管理'
        ]
    }
