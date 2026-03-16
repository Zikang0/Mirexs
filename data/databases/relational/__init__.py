"""
关系数据库模块 - 提供关系型数据库的完整集成和管理功能

模块组成:
- sqlite_integration: SQLite数据库集成
- postgresql_integration: PostgreSQL数据库集成  
- schema_manager: 数据库模式管理
- migration_tool: 数据库迁移工具
- user_profiles: 用户画像管理
- system_config: 系统配置管理
- skill_registry: 技能注册管理
"""

from .sqlite_integration import SQLiteIntegration
from .postgresql_integration import PostgreSQLIntegration
from .schema_manager import SchemaManager, SchemaChangeType
from .migration_tool import MigrationTool
from .user_profiles import UserProfiles, UserProfile, UserPreference, UserPreferenceCategory, LearningStyle
from .system_config import SystemConfiguration, SystemConfig, ConfigCategory, ConfigDataType
from .skill_registry import SkillRegistry, RegisteredSkill, SkillParameter, SkillMetadata, SkillCategory, SkillStatus

__all__ = [
    # 数据库集成
    'SQLiteIntegration',
    'PostgreSQLIntegration',
    
    # 模式管理
    'SchemaManager',
    'SchemaChangeType',
    
    # 迁移工具
    'MigrationTool',
    
    # 用户画像
    'UserProfiles',
    'UserProfile', 
    'UserPreference',
    'UserPreferenceCategory',
    'LearningStyle',
    
    # 系统配置
    'SystemConfiguration',
    'SystemConfig',
    'ConfigCategory',
    'ConfigDataType',
    
    # 技能注册
    'SkillRegistry',
    'RegisteredSkill',
    'SkillParameter',
    'SkillMetadata', 
    'SkillCategory',
    'SkillStatus'
]

__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "关系数据库模块 - 提供完整的关系型数据库存储、管理和迁移功能"
