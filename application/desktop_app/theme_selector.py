"""
主题选择器模块 - Mirexs桌面应用程序

提供界面主题管理和选择功能，包括：
1. 主题定义和存储
2. 主题切换和预览
3. 亮色/暗色模式支持
4. 自定义主题创建
5. 系统主题自动跟随
"""

import os
import sys
import logging
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import platform

logger = logging.getLogger(__name__)

class ThemeMode(Enum):
    """主题模式枚举"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    CUSTOM = "custom"

@dataclass
class ThemeColor:
    """主题颜色"""
    primary: str = "#3498db"
    secondary: str = "#2ecc71"
    accent: str = "#e74c3c"
    background: str = "#ffffff"
    foreground: str = "#2c3e50"
    surface: str = "#f8f9fa"
    error: str = "#c0392b"
    warning: str = "#f39c12"
    info: str = "#3498db"
    success: str = "#27ae60"

@dataclass
class ThemeFont:
    """主题字体"""
    family: str = "Microsoft YaHei"  # Windows默认
    size_small: int = 10
    size_normal: int = 12
    size_large: int = 14
    size_title: int = 18
    size_header: int = 24

@dataclass
class ThemeMetrics:
    """主题尺寸"""
    spacing_tiny: int = 4
    spacing_small: int = 8
    spacing_normal: int = 12
    spacing_large: int = 16
    spacing_xlarge: int = 24
    border_radius: int = 4
    border_width: int = 1
    shadow_opacity: float = 0.1

@dataclass
class Theme:
    """主题定义"""
    id: str
    name: str
    mode: ThemeMode
    colors: ThemeColor = field(default_factory=ThemeColor)
    fonts: ThemeFont = field(default_factory=ThemeFont)
    metrics: ThemeMetrics = field(default_factory=ThemeMetrics)
    stylesheet: str = ""
    icon_set: str = "default"
    created_at: datetime = field(default_factory=datetime.now)
    is_custom: bool = False
    file_path: Optional[str] = None

@dataclass
class ThemeSelectorConfig:
    """主题选择器配置"""
    default_theme: str = "light"
    follow_system: bool = True
    save_selection: bool = True
    allow_custom: bool = True
    themes_dir: str = "themes/"
    config_file: str = "theme_config.json"
    data_dir: str = "data/theme_selector/"

class ThemeSelector:
    """
    主题选择器类
    
    负责管理应用程序主题，提供主题切换、预览、自定义等功能。
    """
    
    def __init__(self, config: Optional[ThemeSelectorConfig] = None):
        """
        初始化主题选择器
        
        Args:
            config: 选择器配置
        """
        self.config = config or ThemeSelectorConfig()
        
        # 主题存储
        self.themes: Dict[str, Theme] = {}
        self.current_theme_id: str = self.config.default_theme
        
        # 回调函数
        self.on_theme_changed: Optional[Callable[[str], None]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载内置主题
        self._load_builtin_themes()
        
        # 加载自定义主题
        if self.config.allow_custom:
            self._load_custom_themes()
        
        # 加载用户选择
        self._load_user_selection()
        
        logger.info(f"ThemeSelector initialized with {len(self.themes)} themes")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        if self.config.allow_custom:
            os.makedirs(self.config.themes_dir, exist_ok=True)
    
    def _load_builtin_themes(self):
        """加载内置主题"""
        # 亮色主题
        light_theme = Theme(
            id="light",
            name="亮色",
            mode=ThemeMode.LIGHT,
            colors=ThemeColor(
                primary="#3498db",
                secondary="#2ecc71",
                accent="#e74c3c",
                background="#ffffff",
                foreground="#2c3e50",
                surface="#f8f9fa"
            ),
            stylesheet=self._generate_light_stylesheet()
        )
        self.themes["light"] = light_theme
        
        # 暗色主题
        dark_theme = Theme(
            id="dark",
            name="暗色",
            mode=ThemeMode.DARK,
            colors=ThemeColor(
                primary="#3498db",
                secondary="#2ecc71",
                accent="#e74c3c",
                background="#1e1e1e",
                foreground="#ecf0f1",
                surface="#2d2d2d"
            ),
            stylesheet=self._generate_dark_stylesheet()
        )
        self.themes["dark"] = dark_theme
        
        # 高对比度主题
        high_contrast_theme = Theme(
            id="high_contrast",
            name="高对比度",
            mode=ThemeMode.CUSTOM,
            colors=ThemeColor(
                primary="#0000ff",
                secondary="#00ff00",
                accent="#ff0000",
                background="#000000",
                foreground="#ffffff",
                surface="#333333"
            ),
            stylesheet=self._generate_high_contrast_stylesheet()
        )
        self.themes["high_contrast"] = high_contrast_theme
        
        # 柔光主题
        soft_light_theme = Theme(
            id="soft_light",
            name="柔光",
            mode=ThemeMode.LIGHT,
            colors=ThemeColor(
                primary="#7f8c8d",
                secondary="#95a5a6",
                accent="#bdc3c7",
                background="#f0f3f4",
                foreground="#34495e",
                surface="#ffffff"
            ),
            stylesheet=self._generate_soft_light_stylesheet()
        )
        self.themes["soft_light"] = soft_light_theme
    
    def _generate_light_stylesheet(self) -> str:
        """生成亮色样式表"""
        return """
            QMainWindow {
                background-color: #ffffff;
            }
            QWidget {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLineEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 6px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #3498db;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f8f9fa;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
        """
    
    def _generate_dark_stylesheet(self) -> str:
        """生成暗色样式表"""
        return """
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ecf0f1;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QPushButton {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QLineEdit {
                border: 1px solid #34495e;
                border-radius: 4px;
                padding: 6px;
                background-color: #2d2d2d;
                color: #ecf0f1;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QTextEdit {
                border: 1px solid #34495e;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #ecf0f1;
            }
            QListWidget {
                border: 1px solid #34495e;
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #34495e;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ecf0f1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #3498db;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #2d2d2d;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #34495e;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a5a6a;
            }
        """
    
    def _generate_high_contrast_stylesheet(self) -> str:
        """生成高对比度样式表"""
        return """
            QMainWindow {
                background-color: #000000;
            }
            QWidget {
                background-color: #000000;
                color: #ffffff;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0000ff;
                color: #ffffff;
                border: 2px solid #ffffff;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #3333ff;
            }
            QLineEdit {
                border: 2px solid #ffffff;
                padding: 6px;
                background-color: #000000;
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #00ff00;
            }
            QTextEdit {
                border: 2px solid #ffffff;
                background-color: #000000;
                color: #ffffff;
            }
            QListWidget {
                border: 2px solid #ffffff;
                background-color: #000000;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #ffffff;
                color: #000000;
            }
        """
    
    def _generate_soft_light_stylesheet(self) -> str:
        """生成柔光样式表"""
        return """
            QMainWindow {
                background-color: #f0f3f4;
            }
            QWidget {
                background-color: #f0f3f4;
                color: #34495e;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QPushButton {
                background-color: #7f8c8d;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
            QLineEdit {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                padding: 6px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #7f8c8d;
            }
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QListWidget {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #bdc3c7;
                color: #ffffff;
            }
        """
    
    def _load_custom_themes(self):
        """加载自定义主题"""
        if not os.path.exists(self.config.themes_dir):
            return
        
        for filename in os.listdir(self.config.themes_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.config.themes_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 解析主题
                    theme_id = data.get('id', filename[:-5])
                    theme = self._parse_theme_from_dict(theme_id, data)
                    theme.file_path = file_path
                    theme.is_custom = True
                    
                    self.themes[theme_id] = theme
                    logger.debug(f"Custom theme loaded: {theme_id}")
                    
                except Exception as e:
                    logger.error(f"Error loading custom theme {filename}: {e}")
    
    def _parse_theme_from_dict(self, theme_id: str, data: dict) -> Theme:
        """从字典解析主题"""
        # 解析模式
        mode_str = data.get('mode', 'custom')
        try:
            mode = ThemeMode(mode_str)
        except ValueError:
            mode = ThemeMode.CUSTOM
        
        # 解析颜色
        colors_data = data.get('colors', {})
        colors = ThemeColor(
            primary=colors_data.get('primary', '#3498db'),
            secondary=colors_data.get('secondary', '#2ecc71'),
            accent=colors_data.get('accent', '#e74c3c'),
            background=colors_data.get('background', '#ffffff'),
            foreground=colors_data.get('foreground', '#2c3e50'),
            surface=colors_data.get('surface', '#f8f9fa'),
            error=colors_data.get('error', '#c0392b'),
            warning=colors_data.get('warning', '#f39c12'),
            info=colors_data.get('info', '#3498db'),
            success=colors_data.get('success', '#27ae60')
        )
        
        # 解析字体
        fonts_data = data.get('fonts', {})
        fonts = ThemeFont(
            family=fonts_data.get('family', 'Microsoft YaHei'),
            size_small=fonts_data.get('size_small', 10),
            size_normal=fonts_data.get('size_normal', 12),
            size_large=fonts_data.get('size_large', 14),
            size_title=fonts_data.get('size_title', 18),
            size_header=fonts_data.get('size_header', 24)
        )
        
        # 解析尺寸
        metrics_data = data.get('metrics', {})
        metrics = ThemeMetrics(
            spacing_tiny=metrics_data.get('spacing_tiny', 4),
            spacing_small=metrics_data.get('spacing_small', 8),
            spacing_normal=metrics_data.get('spacing_normal', 12),
            spacing_large=metrics_data.get('spacing_large', 16),
            spacing_xlarge=metrics_data.get('spacing_xlarge', 24),
            border_radius=metrics_data.get('border_radius', 4),
            border_width=metrics_data.get('border_width', 1),
            shadow_opacity=metrics_data.get('shadow_opacity', 0.1)
        )
        
        return Theme(
            id=theme_id,
            name=data.get('name', theme_id),
            mode=mode,
            colors=colors,
            fonts=fonts,
            metrics=metrics,
            stylesheet=data.get('stylesheet', ''),
            icon_set=data.get('icon_set', 'default'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            is_custom=True
        )
    
    def _load_user_selection(self):
        """加载用户主题选择"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    theme_id = data.get('current_theme', self.config.default_theme)
                    
                    if theme_id in self.themes:
                        self.current_theme_id = theme_id
                        logger.info(f"User theme selection loaded: {theme_id}")
                    
            except Exception as e:
                logger.error(f"Error loading user theme selection: {e}")
    
    def _save_user_selection(self):
        """保存用户主题选择"""
        if not self.config.save_selection:
            return
        
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'current_theme': self.current_theme_id,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
            
            logger.debug(f"User theme selection saved: {self.current_theme_id}")
            
        except Exception as e:
            logger.error(f"Error saving user theme selection: {e}")
    
    def get_theme(self, theme_id: Optional[str] = None) -> Optional[Theme]:
        """
        获取主题
        
        Args:
            theme_id: 主题ID，None表示当前主题
        
        Returns:
            主题对象
        """
        if theme_id is None:
            theme_id = self.current_theme_id
        
        return self.themes.get(theme_id)
    
    def get_current_theme(self) -> Theme:
        """获取当前主题"""
        return self.get_theme(self.current_theme_id)
    
    def get_all_themes(self) -> List[Dict[str, Any]]:
        """
        获取所有主题信息
        
        Returns:
            主题信息列表
        """
        return [
            {
                'id': theme.id,
                'name': theme.name,
                'mode': theme.mode.value,
                'is_custom': theme.is_custom,
                'created_at': theme.created_at.isoformat()
            }
            for theme in self.themes.values()
        ]
    
    def set_theme(self, theme_id: str) -> bool:
        """
        设置当前主题
        
        Args:
            theme_id: 主题ID
        
        Returns:
            是否成功
        """
        if theme_id not in self.themes:
            logger.warning(f"Theme not found: {theme_id}")
            return False
        
        old_theme = self.current_theme_id
        self.current_theme_id = theme_id
        
        # 保存选择
        self._save_user_selection()
        
        logger.info(f"Theme changed: {old_theme} -> {theme_id}")
        
        if self.on_theme_changed:
            self.on_theme_changed(theme_id)
        
        return True
    
    def toggle_theme(self) -> str:
        """
        切换主题（亮色/暗色之间切换）
        
        Returns:
            新主题ID
        """
        if self.current_theme_id == "light":
            new_theme = "dark"
        elif self.current_theme_id == "dark":
            new_theme = "light"
        else:
            # 如果当前不是亮/暗，切换到亮色
            new_theme = "light"
        
        self.set_theme(new_theme)
        return new_theme
    
    def create_custom_theme(self, name: str, base_theme_id: Optional[str] = None,
                           colors: Optional[Dict] = None) -> Optional[str]:
        """
        创建自定义主题
        
        Args:
            name: 主题名称
            base_theme_id: 基础主题ID
            colors: 颜色覆盖
        
        Returns:
            新主题ID，失败返回None
        """
        if not self.config.allow_custom:
            logger.warning("Custom themes are not allowed")
            return None
        
        # 生成主题ID
        import uuid
        theme_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # 获取基础主题
        if base_theme_id and base_theme_id in self.themes:
            base_theme = self.themes[base_theme_id]
        else:
            base_theme = self.themes["light"]
        
        # 创建新主题
        new_theme = Theme(
            id=theme_id,
            name=name,
            mode=ThemeMode.CUSTOM,
            colors=base_theme.colors,
            fonts=base_theme.fonts,
            metrics=base_theme.metrics,
            icon_set=base_theme.icon_set,
            is_custom=True
        )
        
        # 应用颜色覆盖
        if colors:
            for key, value in colors.items():
                if hasattr(new_theme.colors, key):
                    setattr(new_theme.colors, key, value)
        
        # 生成样式表
        new_theme.stylesheet = self._generate_custom_stylesheet(new_theme)
        
        # 保存主题
        self.themes[theme_id] = new_theme
        self._save_custom_theme(new_theme)
        
        logger.info(f"Custom theme created: {theme_id} ({name})")
        
        return theme_id
    
    def _generate_custom_stylesheet(self, theme: Theme) -> str:
        """生成自定义主题样式表"""
        # 基于基础主题生成
        if theme.mode == ThemeMode.DARK:
            base = self._generate_dark_stylesheet()
        else:
            base = self._generate_light_stylesheet()
        
        # 替换颜色
        # 简化处理，实际可能需要更复杂的转换
        return base
    
    def _save_custom_theme(self, theme: Theme):
        """保存自定义主题到文件"""
        file_path = os.path.join(self.config.themes_dir, f"{theme.id}.json")
        
        data = {
            'id': theme.id,
            'name': theme.name,
            'mode': theme.mode.value,
            'colors': {
                'primary': theme.colors.primary,
                'secondary': theme.colors.secondary,
                'accent': theme.colors.accent,
                'background': theme.colors.background,
                'foreground': theme.colors.foreground,
                'surface': theme.colors.surface,
                'error': theme.colors.error,
                'warning': theme.colors.warning,
                'info': theme.colors.info,
                'success': theme.colors.success
            },
            'fonts': {
                'family': theme.fonts.family,
                'size_small': theme.fonts.size_small,
                'size_normal': theme.fonts.size_normal,
                'size_large': theme.fonts.size_large,
                'size_title': theme.fonts.size_title,
                'size_header': theme.fonts.size_header
            },
            'metrics': {
                'spacing_tiny': theme.metrics.spacing_tiny,
                'spacing_small': theme.metrics.spacing_small,
                'spacing_normal': theme.metrics.spacing_normal,
                'spacing_large': theme.metrics.spacing_large,
                'spacing_xlarge': theme.metrics.spacing_xlarge,
                'border_radius': theme.metrics.border_radius,
                'border_width': theme.metrics.border_width,
                'shadow_opacity': theme.metrics.shadow_opacity
            },
            'icon_set': theme.icon_set,
            'created_at': theme.created_at.isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            theme.file_path = file_path
            logger.debug(f"Custom theme saved: {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving custom theme: {e}")
    
    def delete_custom_theme(self, theme_id: str) -> bool:
        """
        删除自定义主题
        
        Args:
            theme_id: 主题ID
        
        Returns:
            是否成功
        """
        if theme_id not in self.themes:
            logger.warning(f"Theme not found: {theme_id}")
            return False
        
        theme = self.themes[theme_id]
        
        if not theme.is_custom:
            logger.warning(f"Cannot delete built-in theme: {theme_id}")
            return False
        
        # 删除文件
        if theme.file_path and os.path.exists(theme.file_path):
            try:
                os.remove(theme.file_path)
            except Exception as e:
                logger.error(f"Error deleting theme file: {e}")
        
        # 从内存中移除
        del self.themes[theme_id]
        
        # 如果当前主题被删除，切换到默认主题
        if self.current_theme_id == theme_id:
            self.set_theme(self.config.default_theme)
        
        logger.info(f"Custom theme deleted: {theme_id}")
        
        return True
    
    def export_theme(self, theme_id: str, file_path: str) -> bool:
        """
        导出主题到文件
        
        Args:
            theme_id: 主题ID
            file_path: 导出路径
        
        Returns:
            是否成功
        """
        if theme_id not in self.themes:
            logger.warning(f"Theme not found: {theme_id}")
            return False
        
        theme = self.themes[theme_id]
        
        data = {
            'id': theme.id,
            'name': theme.name,
            'mode': theme.mode.value,
            'colors': {
                'primary': theme.colors.primary,
                'secondary': theme.colors.secondary,
                'accent': theme.colors.accent,
                'background': theme.colors.background,
                'foreground': theme.colors.foreground,
                'surface': theme.colors.surface,
                'error': theme.colors.error,
                'warning': theme.colors.warning,
                'info': theme.colors.info,
                'success': theme.colors.success
            },
            'fonts': {
                'family': theme.fonts.family,
                'size_small': theme.fonts.size_small,
                'size_normal': theme.fonts.size_normal,
                'size_large': theme.fonts.size_large,
                'size_title': theme.fonts.size_title,
                'size_header': theme.fonts.size_header
            },
            'metrics': {
                'spacing_tiny': theme.metrics.spacing_tiny,
                'spacing_small': theme.metrics.spacing_small,
                'spacing_normal': theme.metrics.spacing_normal,
                'spacing_large': theme.metrics.spacing_large,
                'spacing_xlarge': theme.metrics.spacing_xlarge,
                'border_radius': theme.metrics.border_radius,
                'border_width': theme.metrics.border_width,
                'shadow_opacity': theme.metrics.shadow_opacity
            },
            'icon_set': theme.icon_set,
            'created_at': theme.created_at.isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Theme exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting theme: {e}")
            return False
    
    def import_theme(self, file_path: str) -> Optional[str]:
        """
        从文件导入主题
        
        Args:
            file_path: 文件路径
        
        Returns:
            主题ID，失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            theme_id = data.get('id', f"imported_{os.path.basename(file_path)[:-5]}")
            
            # 确保ID唯一
            if theme_id in self.themes:
                import uuid
                theme_id = f"{theme_id}_{uuid.uuid4().hex[:4]}"
            
            theme = self._parse_theme_from_dict(theme_id, data)
            theme.is_custom = True
            
            self.themes[theme_id] = theme
            self._save_custom_theme(theme)
            
            logger.info(f"Theme imported: {theme_id}")
            return theme_id
            
        except Exception as e:
            logger.error(f"Error importing theme: {e}")
            return None
    
    def get_system_theme(self) -> str:
        """
        获取系统主题
        
        Returns:
            "light" 或 "dark"
        """
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except:
                pass
        
        elif platform.system() == "Darwin":  # macOS
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True, text=True
                )
                return "dark" if result.returncode == 0 else "light"
            except:
                pass
        
        # 默认返回亮色
        return "light"
    
    def update_from_system(self) -> bool:
        """
        根据系统主题更新
        
        Returns:
            主题是否变化
        """
        if not self.config.follow_system:
            return False
        
        system_theme = self.get_system_theme()
        current_theme = self.get_current_theme()
        
        # 如果当前是系统跟随模式，切换主题
        if current_theme.mode == ThemeMode.SYSTEM:
            theme_id = system_theme
            if theme_id != self.current_theme_id and theme_id in self.themes:
                self.set_theme(theme_id)
                return True
        
        return False
    
    def shutdown(self):
        """关闭主题选择器"""
        logger.info("Shutting down ThemeSelector...")
        self._save_user_selection()

