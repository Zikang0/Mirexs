"""
个性化设置模块 - 管理用户界面、行为和功能的个性化定制
"""

import logging
import json
import uuid
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class ColorScheme(Enum):
    """颜色方案枚举"""
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    ORANGE = "orange"
    PINK = "pink"
    CUSTOM = "custom"

class LayoutStyle(Enum):
    """布局风格枚举"""
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"
    CUSTOM = "custom"

class AnimationStyle(Enum):
    """动画风格枚举"""
    SMOOTH = "smooth"
    BOUNCY = "bouncy"
    MINIMAL = "minimal"
    NONE = "none"

@dataclass
class ColorCustomization:
    """颜色定制数据类"""
    primary_color: str = "#3B82F6"  # 主色调
    secondary_color: str = "#10B981"  # 辅助色
    accent_color: str = "#8B5CF6"  # 强调色
    background_color: str = "#FFFFFF"  # 背景色
    surface_color: str = "#F8FAFC"  # 表面色
    text_primary: str = "#1E293B"  # 主要文字
    text_secondary: str = "#64748B"  # 次要文字
    error_color: str = "#EF4444"  # 错误色
    warning_color: str = "#F59E0B"  # 警告色
    success_color: str = "#10B981"  # 成功色

@dataclass
class LayoutCustomization:
    """布局定制数据类"""
    layout_style: LayoutStyle = LayoutStyle.COMFORTABLE
    sidebar_width: int = 280  # 侧边栏宽度
    header_height: int = 64  # 头部高度
    card_padding: int = 16  # 卡片内边距
    border_radius: int = 8  # 边框圆角
    font_size_base: int = 14  # 基础字体大小
    line_height: float = 1.5  # 行高
    spacing_unit: int = 8  # 间距单位

@dataclass
class AnimationCustomization:
    """动画定制数据类"""
    animation_style: AnimationStyle = AnimationStyle.SMOOTH
    duration_short: int = 200  # 短动画时长（毫秒）
    duration_medium: int = 300  # 中等动画时长
    duration_long: int = 500  # 长动画时长
    enable_animations: bool = True  # 启用动画
    reduce_motion: bool = False  # 减少动画
    hover_effects: bool = True  # 悬停效果

@dataclass
class BehaviorCustomization:
    """行为定制数据类"""
    auto_save: bool = True  # 自动保存
    confirm_before_exit: bool = True  # 退出前确认
    show_tooltips: bool = True  # 显示工具提示
    keyboard_shortcuts: Dict[str, str] = field(default_factory=dict)  # 键盘快捷键
    gesture_controls: Dict[str, str] = field(default_factory=dict)  # 手势控制
    voice_commands: Dict[str, str] = field(default_factory=dict)  # 语音命令
    smart_suggestions: bool = True  # 智能建议
    predictive_loading: bool = True  # 预测加载

@dataclass
class ContentCustomization:
    """内容定制数据类"""
    language: str = "zh-CN"  # 界面语言
    date_format: str = "YYYY-MM-DD"  # 日期格式
    time_format: str = "24h"  # 时间格式（12h/24h）
    number_format: str = "comma"  # 数字格式（comma/dot）
    temperature_unit: str = "celsius"  # 温度单位
    distance_unit: str = "metric"  # 距离单位
    content_filter: str = "moderate"  # 内容过滤
    font_family: str = "system"  # 字体家族

@dataclass
class AccessibilityCustomization:
    """无障碍定制数据类"""
    high_contrast: bool = False  # 高对比度
    large_text: bool = False  # 大文字
    screen_reader: bool = False  # 屏幕阅读器支持
    color_blind_mode: str = "none"  # 色盲模式
    cursor_size: str = "normal"  # 光标大小
    keyboard_navigation: bool = True  # 键盘导航
    focus_indicators: bool = True  # 焦点指示器

@dataclass
class WorkspaceCustomization:
    """工作区定制数据类"""
    workspace_name: str
    layout_config: Dict[str, Any]
    widget_positions: Dict[str, Dict[str, int]]
    panel_visibility: Dict[str, bool]
    quick_actions: List[str]
    theme_settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class UserCustomization:
    """用户个性化设置数据类"""
    user_id: str
    color_scheme: ColorCustomization
    layout: LayoutCustomization
    animations: AnimationCustomization
    behavior: BehaviorCustomization
    content: ContentCustomization
    accessibility: AccessibilityCustomization
    workspaces: Dict[str, WorkspaceCustomization]
    active_workspace: str
    created_at: datetime
    updated_at: datetime
    version: str

class CustomizationManager:
    """个性化设置管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化个性化设置管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.customization_table = config.get('customization_table', 'user_customization')
        self.workspaces_table = config.get('workspaces_table', 'user_workspaces')
        
        # 缓存配置
        self.cache_size = config.get('cache_size', 100)
        self._customization_cache = {}
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化个性化设置相关表"""
        try:
            # 用户个性化设置表
            customization_schema = {
                'user_id': 'VARCHAR(100) PRIMARY KEY',
                'color_scheme': 'TEXT NOT NULL',
                'layout': 'TEXT NOT NULL',
                'animations': 'TEXT NOT NULL',
                'behavior': 'TEXT NOT NULL',
                'content': 'TEXT NOT NULL',
                'accessibility': 'TEXT NOT NULL',
                'workspaces': 'TEXT NOT NULL',
                'active_workspace': 'VARCHAR(100) NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'version': 'VARCHAR(20) DEFAULT "1.0"'
            }
            
            constraints = [
                'FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.customization_table, customization_schema, constraints)
            
            # 工作区设置表
            workspaces_schema = {
                'workspace_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'workspace_name': 'VARCHAR(200) NOT NULL',
                'layout_config': 'TEXT NOT NULL',
                'widget_positions': 'TEXT NOT NULL',
                'panel_visibility': 'TEXT NOT NULL',
                'quick_actions': 'TEXT NOT NULL',
                'theme_settings': 'TEXT NOT NULL',
                'created_at': 'TIMESTAMP NOT NULL',
                'updated_at': 'TIMESTAMP NOT NULL'
            }
            
            constraints = [
                'FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.workspaces_table, workspaces_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.customization_table, 'user_id')
            self.db.create_index(self.workspaces_table, 'user_id')
            self.db.create_index(self.workspaces_table, 'workspace_name')
            
            self.logger.info("Customization tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize customization tables: {str(e)}")
            raise
    
    def initialize_default_customization(self, user_id: str) -> bool:
        """
        初始化默认个性化设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            current_time = datetime.now()
            
            # 创建默认个性化设置
            customization = UserCustomization(
                user_id=user_id,
                color_scheme=ColorCustomization(),
                layout=LayoutCustomization(),
                animations=AnimationCustomization(),
                behavior=BehaviorCustomization(),
                content=ContentCustomization(),
                accessibility=AccessibilityCustomization(),
                workspaces={},
                active_workspace="default",
                created_at=current_time,
                updated_at=current_time,
                version="1.0"
            )
            
            # 创建默认工作区
            default_workspace = self._create_default_workspace(user_id, "default")
            customization.workspaces["default"] = default_workspace
            
            # 准备数据库数据
            db_data = {
                'user_id': customization.user_id,
                'color_scheme': json.dumps(asdict(customization.color_scheme)),
                'layout': json.dumps(asdict(customization.layout)),
                'animations': json.dumps(asdict(customization.animations)),
                'behavior': json.dumps(asdict(customization.behavior)),
                'content': json.dumps(asdict(customization.content)),
                'accessibility': json.dumps(asdict(customization.accessibility)),
                'workspaces': json.dumps({
                    name: asdict(workspace) for name, workspace in customization.workspaces.items()
                }),
                'active_workspace': customization.active_workspace,
                'created_at': customization.created_at,
                'updated_at': customization.updated_at,
                'version': customization.version
            }
            
            # 插入数据库
            self.db.execute_insert(self.customization_table, db_data)
            
            # 保存工作区设置
            self._save_workspace(default_workspace)
            
            # 添加到缓存
            self._customization_cache[user_id] = customization
            
            self.logger.info(f"Default customization initialized for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize default customization: {str(e)}")
            return False
    
    def get_user_customization(self, user_id: str) -> Optional[UserCustomization]:
        """
        获取用户个性化设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            UserCustomization: 个性化设置，如果不存在返回None
        """
        # 先检查缓存
        if user_id in self._customization_cache:
            return self._customization_cache[user_id]
        
        try:
            query = f"SELECT * FROM {self.customization_table} WHERE user_id = %s"
            results = self.db.execute_query(query, (user_id,))
            
            if not results:
                # 如果没有找到个性化设置，初始化默认设置
                if self.initialize_default_customization(user_id):
                    return self.get_user_customization(user_id)
                else:
                    return None
            
            cust_data = results[0]
            
            # 解析各个定制组件
            color_scheme = ColorCustomization(**json.loads(cust_data['color_scheme']))
            layout = LayoutCustomization(**json.loads(cust_data['layout']))
            animations = AnimationCustomization(**json.loads(cust_data['animations']))
            behavior = BehaviorCustomization(**json.loads(cust_data['behavior']))
            content = ContentCustomization(**json.loads(cust_data['content']))
            accessibility = AccessibilityCustomization(**json.loads(cust_data['accessibility']))
            
            # 解析工作区
            workspaces_data = json.loads(cust_data['workspaces'])
            workspaces = {}
            for name, workspace_data in workspaces_data.items():
                # 处理时间戳
                if isinstance(workspace_data['created_at'], str):
                    workspace_data['created_at'] = datetime.fromisoformat(workspace_data['created_at'])
                if isinstance(workspace_data['updated_at'], str):
                    workspace_data['updated_at'] = datetime.fromisoformat(workspace_data['updated_at'])
                
                workspaces[name] = WorkspaceCustomization(**workspace_data)
            
            # 构建个性化设置对象
            customization = UserCustomization(
                user_id=cust_data['user_id'],
                color_scheme=color_scheme,
                layout=layout,
                animations=animations,
                behavior=behavior,
                content=content,
                accessibility=accessibility,
                workspaces=workspaces,
                active_workspace=cust_data['active_workspace'],
                created_at=cust_data['created_at'],
                updated_at=cust_data['updated_at'],
                version=cust_data['version']
            )
            
            # 添加到缓存
            if len(self._customization_cache) >= self.cache_size:
                # 移除最旧的设置
                oldest_user = min(self._customization_cache.keys(), 
                                key=lambda k: self._customization_cache[k].updated_at)
                del self._customization_cache[oldest_user]
            
            self._customization_cache[user_id] = customization
            
            return customization
            
        except Exception as e:
            self.logger.error(f"Failed to get user customization: {str(e)}")
            return None
    
    def update_customization(self, user_id: str, category: str, 
                           updates: Dict[str, Any]) -> bool:
        """
        更新个性化设置
        
        Args:
            user_id: 用户ID
            category: 设置类别 (color, layout, animations, behavior, content, accessibility)
            updates: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取现有设置
            customization = self.get_user_customization(user_id)
            if not customization:
                self.logger.warning(f"Customization not found for user: {user_id}")
                return False
            
            # 准备更新数据
            update_data = {
                'updated_at': datetime.now()
            }
            
            # 根据类别更新相应的设置
            if category == 'color':
                current_color = asdict(customization.color_scheme)
                current_color.update(updates)
                update_data['color_scheme'] = json.dumps(current_color)
                
            elif category == 'layout':
                current_layout = asdict(customization.layout)
                current_layout.update(updates)
                update_data['layout'] = json.dumps(current_layout)
                
            elif category == 'animations':
                current_animations = asdict(customization.animations)
                current_animations.update(updates)
                update_data['animations'] = json.dumps(current_animations)
                
            elif category == 'behavior':
                current_behavior = asdict(customization.behavior)
                current_behavior.update(updates)
                update_data['behavior'] = json.dumps(current_behavior)
                
            elif category == 'content':
                current_content = asdict(customization.content)
                current_content.update(updates)
                update_data['content'] = json.dumps(current_content)
                
            elif category == 'accessibility':
                current_accessibility = asdict(customization.accessibility)
                current_accessibility.update(updates)
                update_data['accessibility'] = json.dumps(current_accessibility)
                
            else:
                self.logger.error(f"Invalid customization category: {category}")
                return False
            
            # 执行更新
            affected = self.db.execute_update(
                self.customization_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                # 更新缓存
                if user_id in self._customization_cache:
                    del self._customization_cache[user_id]
                
                self.logger.info(f"Customization updated: {user_id} - {category}")
                return True
            else:
                self.logger.warning(f"Customization not found for update: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update customization: {str(e)}")
            return False
    
    def create_workspace(self, user_id: str, workspace_name: str, 
                        base_on: str = "default") -> str:
        """
        创建工作区
        
        Args:
            user_id: 用户ID
            workspace_name: 工作区名称
            base_on: 基于哪个工作区创建
            
        Returns:
            str: 工作区ID
        """
        try:
            customization = self.get_user_customization(user_id)
            if not customization:
                self.logger.error(f"Customization not found for user: {user_id}")
                return None
            
            # 检查工作区名称是否已存在
            if workspace_name in customization.workspaces:
                self.logger.warning(f"Workspace already exists: {workspace_name}")
                return customization.workspaces[workspace_name].workspace_name
            
            workspace_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 基于现有工作区创建新工作区
            if base_on in customization.workspaces:
                base_workspace = customization.workspaces[base_on]
                new_workspace = WorkspaceCustomization(
                    workspace_name=workspace_name,
                    layout_config=base_workspace.layout_config.copy(),
                    widget_positions=base_workspace.widget_positions.copy(),
                    panel_visibility=base_workspace.panel_visibility.copy(),
                    quick_actions=base_workspace.quick_actions.copy(),
                    theme_settings=base_workspace.theme_settings.copy(),
                    created_at=current_time,
                    updated_at=current_time
                )
            else:
                # 创建默认工作区
                new_workspace = self._create_default_workspace(user_id, workspace_name)
            
            # 添加到个性化设置
            customization.workspaces[workspace_name] = new_workspace
            
            # 更新数据库
            update_data = {
                'workspaces': json.dumps({
                    name: asdict(workspace) for name, workspace in customization.workspaces.items()
                }),
                'updated_at': current_time
            }
            
            affected = self.db.execute_update(
                self.customization_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                # 保存工作区到独立表
                self._save_workspace(new_workspace)
                
                # 清除缓存
                if user_id in self._customization_cache:
                    del self._customization_cache[user_id]
                
                self.logger.info(f"Workspace created: {workspace_name} for user {user_id}")
                return workspace_name
            else:
                self.logger.error(f"Failed to create workspace in database: {workspace_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create workspace: {str(e)}")
            return None
    
    def switch_workspace(self, user_id: str, workspace_name: str) -> bool:
        """
        切换工作区
        
        Args:
            user_id: 用户ID
            workspace_name: 工作区名称
            
        Returns:
            bool: 切换是否成功
        """
        try:
            customization = self.get_user_customization(user_id)
            if not customization:
                self.logger.error(f"Customization not found for user: {user_id}")
                return False
            
            if workspace_name not in customization.workspaces:
                self.logger.warning(f"Workspace not found: {workspace_name}")
                return False
            
            # 更新当前工作区
            update_data = {
                'active_workspace': workspace_name,
                'updated_at': datetime.now()
            }
            
            affected = self.db.execute_update(
                self.customization_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                # 清除缓存
                if user_id in self._customization_cache:
                    del self._customization_cache[user_id]
                
                self.logger.info(f"Workspace switched: {user_id} -> {workspace_name}")
                return True
            else:
                self.logger.warning(f"Failed to switch workspace: {user_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to switch workspace: {str(e)}")
            return False
    
    def update_workspace(self, user_id: str, workspace_name: str,
                        updates: Dict[str, Any]) -> bool:
        """
        更新工作区设置
        
        Args:
            user_id: 用户ID
            workspace_name: 工作区名称
            updates: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            customization = self.get_user_customization(user_id)
            if not customization:
                self.logger.error(f"Customization not found for user: {user_id}")
                return False
            
            if workspace_name not in customization.workspaces:
                self.logger.warning(f"Workspace not found: {workspace_name}")
                return False
            
            workspace = customization.workspaces[workspace_name]
            workspace.updated_at = datetime.now()
            
            # 应用更新
            for key, value in updates.items():
                if hasattr(workspace, key):
                    setattr(workspace, key, value)
                else:
                    self.logger.warning(f"Invalid workspace attribute: {key}")
            
            # 更新数据库
            update_data = {
                'workspaces': json.dumps({
                    name: asdict(ws) for name, ws in customization.workspaces.items()
                }),
                'updated_at': datetime.now()
            }
            
            affected = self.db.execute_update(
                self.customization_table,
                update_data,
                "user_id = %s",
                (user_id,)
            )
            
            if affected > 0:
                # 更新工作区表
                self._save_workspace(workspace)
                
                # 清除缓存
                if user_id in self._customization_cache:
                    del self._customization_cache[user_id]
                
                self.logger.info(f"Workspace updated: {workspace_name} for user {user_id}")
                return True
            else:
                self.logger.warning(f"Failed to update workspace: {workspace_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update workspace: {str(e)}")
            return False
    
    def export_customization(self, user_id: str) -> Dict[str, Any]:
        """
        导出个性化设置
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 导出的设置数据
        """
        try:
            customization = self.get_user_customization(user_id)
            if not customization:
                return {'error': 'Customization not found'}
            
            export_data = {
                'user_id': customization.user_id,
                'color_scheme': asdict(customization.color_scheme),
                'layout': asdict(customization.layout),
                'animations': asdict(customization.animations),
                'behavior': asdict(customization.behavior),
                'content': asdict(customization.content),
                'accessibility': asdict(customization.accessibility),
                'workspaces': {
                    name: asdict(workspace) for name, workspace in customization.workspaces.items()
                },
                'active_workspace': customization.active_workspace,
                'version': customization.version,
                'exported_at': datetime.now().isoformat()
            }
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Failed to export customization: {str(e)}")
            return {'error': str(e)}
    
    def import_customization(self, user_id: str, import_data: Dict[str, Any]) -> bool:
        """
        导入个性化设置
        
        Args:
            user_id: 用户ID
            import_data: 导入数据
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 验证导入数据
            required_sections = [
                'color_scheme', 'layout', 'animations', 'behavior', 
                'content', 'accessibility', 'workspaces'
            ]
            
            for section in required_sections:
                if section not in import_data:
                    self.logger.error(f"Missing required section in import data: {section}")
                    return False
            
            # 应用导入的设置
            updates_applied = 0
            for section in required_sections:
                success = self.update_customization(user_id, section, import_data[section])
                if success:
                    updates_applied += 1
                else:
                    self.logger.error(f"Failed to import {section} settings")
            
            # 设置活动工作区
            if 'active_workspace' in import_data:
                self.switch_workspace(user_id, import_data['active_workspace'])
            
            self.logger.info(f"Customization imported for user {user_id}: {updates_applied}/{len(required_sections)} sections applied")
            return updates_applied == len(required_sections)
            
        except Exception as e:
            self.logger.error(f"Failed to import customization: {str(e)}")
            return False
    
    def reset_customization(self, user_id: str, category: str = None) -> bool:
        """
        重置个性化设置
        
        Args:
            user_id: 用户ID
            category: 重置的类别（为空则重置所有）
            
        Returns:
            bool: 重置是否成功
        """
        try:
            if category is None:
                # 重置所有设置
                return self.initialize_default_customization(user_id)
            else:
                # 重置特定类别
                default_customization = UserCustomization(
                    user_id=user_id,
                    color_scheme=ColorCustomization(),
                    layout=LayoutCustomization(),
                    animations=AnimationCustomization(),
                    behavior=BehaviorCustomization(),
                    content=ContentCustomization(),
                    accessibility=AccessibilityCustomization(),
                    workspaces={},
                    active_workspace="default",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    version="1.0"
                )
                
                if category == 'color':
                    default_data = asdict(default_customization.color_scheme)
                elif category == 'layout':
                    default_data = asdict(default_customization.layout)
                elif category == 'animations':
                    default_data = asdict(default_customization.animations)
                elif category == 'behavior':
                    default_data = asdict(default_customization.behavior)
                elif category == 'content':
                    default_data = asdict(default_customization.content)
                elif category == 'accessibility':
                    default_data = asdict(default_customization.accessibility)
                else:
                    self.logger.error(f"Invalid customization category for reset: {category}")
                    return False
                
                return self.update_customization(user_id, category, default_data)
                
        except Exception as e:
            self.logger.error(f"Failed to reset customization: {str(e)}")
            return False
    
    def get_customization_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取个性化设置摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 设置摘要
        """
        try:
            customization = self.get_user_customization(user_id)
            if not customization:
                return {'error': 'Customization not found'}
            
            summary = {
                'user_id': user_id,
                'active_workspace': customization.active_workspace,
                'workspace_count': len(customization.workspaces),
                'color_scheme': customization.color_scheme.primary_color,
                'layout_style': customization.layout.layout_style.value,
                'animation_style': customization.animations.animation_style.value,
                'language': customization.content.language,
                'accessibility_features': {
                    'high_contrast': customization.accessibility.high_contrast,
                    'large_text': customization.accessibility.large_text,
                    'screen_reader': customization.accessibility.screen_reader
                },
                'keyboard_shortcuts': len(customization.behavior.keyboard_shortcuts),
                'last_updated': customization.updated_at.isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get customization summary: {str(e)}")
            return {'error': str(e)}
    
    def _create_default_workspace(self, user_id: str, workspace_name: str) -> WorkspaceCustomization:
        """创建默认工作区"""
        current_time = datetime.now()
        
        return WorkspaceCustomization(
            workspace_name=workspace_name,
            layout_config={
                'sidebar_position': 'left',
                'header_visible': True,
                'footer_visible': True,
                'main_area_columns': 2
            },
            widget_positions={
                'chat_widget': {'x': 100, 'y': 100, 'width': 300, 'height': 400},
                'notes_widget': {'x': 420, 'y': 100, 'width': 300, 'height': 300},
                'calendar_widget': {'x': 100, 'y': 520, 'width': 300, 'height': 200}
            },
            panel_visibility={
                'left_panel': True,
                'right_panel': False,
                'bottom_panel': True
            },
            quick_actions=['new_chat', 'search', 'settings'],
            theme_settings={
                'background_image': None,
                'custom_css': '',
                'icon_style': 'outline'
            },
            created_at=current_time,
            updated_at=current_time
        )
    
    def _save_workspace(self, workspace: WorkspaceCustomization):
        """保存工作区到独立表"""
        try:
            workspace_data = {
                'workspace_id': str(uuid.uuid4()),
                'user_id': workspace.workspace_name,  # 简化处理，实际应关联用户ID
                'workspace_name': workspace.workspace_name,
                'layout_config': json.dumps(workspace.layout_config),
                'widget_positions': json.dumps(workspace.widget_positions),
                'panel_visibility': json.dumps(workspace.panel_visibility),
                'quick_actions': json.dumps(workspace.quick_actions),
                'theme_settings': json.dumps(workspace.theme_settings),
                'created_at': workspace.created_at,
                'updated_at': workspace.updated_at
            }
            
            # 检查工作区是否已存在
            query = f"SELECT COUNT(*) as count FROM {self.workspaces_table} WHERE workspace_name = %s"
            results = self.db.execute_query(query, (workspace.workspace_name,))
            
            if results and results[0]['count'] > 0:
                # 更新现有工作区
                self.db.execute_update(
                    self.workspaces_table,
                    workspace_data,
                    "workspace_name = %s",
                    (workspace.workspace_name,)
                )
            else:
                # 插入新工作区
                self.db.execute_insert(self.workspaces_table, workspace_data)
                
        except Exception as e:
            self.logger.error(f"Failed to save workspace: {str(e)}")

