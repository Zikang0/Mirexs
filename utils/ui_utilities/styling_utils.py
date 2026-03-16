"""
样式工具模块

提供UI样式和主题管理工具。
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class ColorScheme:
    """颜色方案"""
    name: str
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    border: str
    success: str
    warning: str
    error: str
    info: str


class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        """初始化主题管理器"""
        self.themes = {}
        self.current_theme = None
        self._load_default_themes()
    
    def _load_default_themes(self):
        """加载默认主题"""
        # 浅色主题
        light_theme = ColorScheme(
            name="light",
            primary="#1976D2",
            secondary="#424242",
            accent="#FF5722",
            background="#FAFAFA",
            surface="#FFFFFF",
            text_primary="#212121",
            text_secondary="#757575",
            text_disabled="#BDBDBD",
            border="#E0E0E0",
            success="#4CAF50",
            warning="#FF9800",
            error="#F44336",
            info="#2196F3"
        )
        
        # 深色主题
        dark_theme = ColorScheme(
            name="dark",
            primary="#2196F3",
            secondary="#B0BEC5",
            accent="#FF5722",
            background="#121212",
            surface="#1E1E1E",
            text_primary="#FFFFFF",
            text_secondary="#B0BEC5",
            text_disabled="#757575",
            border="#424242",
            success="#4CAF50",
            warning="#FF9800",
            error="#F44336",
            info="#2196F3"
        )
        
        # 高对比度主题
        high_contrast_theme = ColorScheme(
            name="high_contrast",
            primary="#000000",
            secondary="#FFFFFF",
            accent="#FFFF00",
            background="#FFFFFF",
            surface="#FFFFFF",
            text_primary="#000000",
            text_secondary="#000000",
            text_disabled="#808080",
            border="#000000",
            success="#008000",
            warning="#FF8000",
            error="#FF0000",
            info="#0000FF"
        )
        
        self.themes = {
            "light": light_theme,
            "dark": dark_theme,
            "high_contrast": high_contrast_theme
        }
        
        self.current_theme = "light"
    
    def add_theme(self, theme: ColorScheme):
        """添加自定义主题
        
        Args:
            theme: 颜色方案
        """
        self.themes[theme.name] = theme
    
    def set_theme(self, theme_name: str):
        """设置当前主题
        
        Args:
            theme_name: 主题名称
        """
        if theme_name in self.themes:
            self.current_theme = theme_name
    
    def get_current_theme(self) -> ColorScheme:
        """获取当前主题
        
        Returns:
            当前颜色方案
        """
        return self.themes[self.current_theme]
    
    def get_theme(self, theme_name: str) -> Optional[ColorScheme]:
        """获取指定主题
        
        Args:
            theme_name: 主题名称
            
        Returns:
            颜色方案
        """
        return self.themes.get(theme_name)
    
    def list_themes(self) -> List[str]:
        """列出所有主题名称
        
        Returns:
            主题名称列表
        """
        return list(self.themes.keys())


class StyleManager:
    """样式管理器"""
    
    def __init__(self, theme_manager: ThemeManager):
        """初始化样式管理器
        
        Args:
            theme_manager: 主题管理器
        """
        self.theme_manager = theme_manager
        self.styles = {}
        self._create_default_styles()
    
    def _create_default_styles(self):
        """创建默认样式"""
        theme = self.theme_manager.get_current_theme()
        
        # 按钮样式
        self.styles['Button'] = {
            'background': theme.primary,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (10, 5),
            'font': ('Arial', 10),
            'cursor': 'hand2'
        }
        
        # 主要按钮样式
        self.styles['Primary.TButton'] = {
            'background': theme.primary,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (12, 6),
            'font': ('Arial', 10, 'bold')
        }
        
        # 次要按钮样式
        self.styles['Secondary.TButton'] = {
            'background': theme.secondary,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (12, 6),
            'font': ('Arial', 10)
        }
        
        # 成功按钮样式
        self.styles['Success.TButton'] = {
            'background': theme.success,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (12, 6),
            'font': ('Arial', 10)
        }
        
        # 警告按钮样式
        self.styles['Warning.TButton'] = {
            'background': theme.warning,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (12, 6),
            'font': ('Arial', 10)
        }
        
        # 危险按钮样式
        self.styles['Danger.TButton'] = {
            'background': theme.error,
            'foreground': theme.surface,
            'relief': 'flat',
            'borderwidth': 0,
            'padding': (12, 6),
            'font': ('Arial', 10)
        }
        
        # 标签样式
        self.styles['Label'] = {
            'background': theme.background,
            'foreground': theme.text_primary,
            'font': ('Arial', 10)
        }
        
        # 标题标签样式
        self.styles['Title.TLabel'] = {
            'background': theme.background,
            'foreground': theme.text_primary,
            'font': ('Arial', 16, 'bold')
        }
        
        # 子标题标签样式
        self.styles['Subtitle.TLabel'] = {
            'background': theme.background,
            'foreground': theme.text_secondary,
            'font': ('Arial', 12, 'bold')
        }
        
        # 输入框样式
        self.styles['TEntry'] = {
            'fieldbackground': theme.surface,
            'foreground': theme.text_primary,
            'bordercolor': theme.border,
            'focuscolor': theme.primary,
            'insertcolor': theme.text_primary,
            'padding': (8, 5),
            'font': ('Arial', 10)
        }
        
        # 文本框样式
        self.styles['Text'] = {
            'background': theme.surface,
            'foreground': theme.text_primary,
            'insertcolor': theme.text_primary,
            'font': ('Arial', 10),
            'relief': 'solid',
            'borderwidth': 1
        }
        
        # 框架样式
        self.styles['TFrame'] = {
            'background': theme.background,
            'relief': 'flat',
            'borderwidth': 0
        }
        
        # 标签页样式
        self.styles['TNotebook'] = {
            'background': theme.background,
            'tabmargins': [2, 5, 2, 0]
        }
        
        self.styles['TNotebook.Tab'] = {
            'background': theme.surface,
            'foreground': theme.text_secondary,
            'padding': [10, 5],
            'font': ('Arial', 10)
        }
        
        # 树形控件样式
        self.styles['Treeview'] = {
            'background': theme.surface,
            'foreground': theme.text_primary,
            'fieldbackground': theme.surface,
            'selectbackground': theme.primary,
            'selectforeground': theme.surface,
            'borderwidth': 1,
            'relief': 'solid'
        }
        
        self.styles['Treeview.Heading'] = {
            'background': theme.secondary,
            'foreground': theme.surface,
            'font': ('Arial', 10, 'bold'),
            'relief': 'flat'
        }
        
        # 滚动条样式
        self.styles['TScrollbar'] = {
            'background': theme.secondary,
            'troughcolor': theme.background,
            'borderwidth': 1,
            'relief': 'flat'
        }
        
        # 复选框样式
        self.styles['TCheckbutton'] = {
            'background': theme.background,
            'foreground': theme.text_primary,
            'focuscolor': theme.primary,
            'font': ('Arial', 10)
        }
        
        # 单选按钮样式
        self.styles['TRadiobutton'] = {
            'background': theme.background,
            'foreground': theme.text_primary,
            'focuscolor': theme.primary,
            'font': ('Arial', 10)
        }
        
        # 列表框样式
        self.styles['Listbox'] = {
            'background': theme.surface,
            'foreground': theme.text_primary,
            'selectbackground': theme.primary,
            'selectforeground': theme.surface,
            'font': ('Arial', 10),
            'relief': 'solid',
            'borderwidth': 1
        }
    
    def apply_style(self, widget, style_name: str):
        """应用样式到控件
        
        Args:
            widget: 控件对象
            style_name: 样式名称
        """
        if style_name in self.styles:
            style_config = self.styles[style_name]
            widget.configure(**style_config)
    
    def update_theme(self, theme_name: str):
        """更新主题样式
        
        Args:
            theme_name: 主题名称
        """
        self.theme_manager.set_theme(theme_name)
        self._create_default_styles()
    
    def add_custom_style(self, style_name: str, style_config: Dict[str, Any]):
        """添加自定义样式
        
        Args:
            style_name: 样式名称
            style_config: 样式配置
        """
        self.styles[style_name] = style_config
    
    def get_style(self, style_name: str) -> Optional[Dict[str, Any]]:
        """获取样式配置
        
        Args:
            style_name: 样式名称
            
        Returns:
            样式配置字典
        """
        return self.styles.get(style_name)
    
    def list_styles(self) -> List[str]:
        """列出所有样式名称
        
        Returns:
            样式名称列表
        """
        return list(self.styles.keys())


class WidgetStyler:
    """控件样式器"""
    
    def __init__(self, style_manager: StyleManager):
        """初始化控件样式器
        
        Args:
            style_manager: 样式管理器
        """
        self.style_manager = style_manager
    
    def style_button(self, button: tk.Button, variant: str = 'default'):
        """样式化按钮
        
        Args:
            button: 按钮控件
            variant: 按钮变体 ('default', 'primary', 'secondary', 'success', 'warning', 'danger')
        """
        style_map = {
            'default': 'Button',
            'primary': 'Primary.TButton',
            'secondary': 'Secondary.TButton',
            'success': 'Success.TButton',
            'warning': 'Warning.TButton',
            'danger': 'Danger.TButton'
        }
        
        style_name = style_map.get(variant, 'Button')
        self.style_manager.apply_style(button, style_name)
    
    def style_label(self, label: tk.Label, variant: str = 'default'):
        """样式化标签
        
        Args:
            label: 标签控件
            variant: 标签变体 ('default', 'title', 'subtitle')
        """
        style_map = {
            'default': 'Label',
            'title': 'Title.TLabel',
            'subtitle': 'Subtitle.TLabel'
        }
        
        style_name = style_map.get(variant, 'Label')
        self.style_manager.apply_style(label, style_name)
    
    def style_entry(self, entry: tk.Entry):
        """样式化输入框
        
        Args:
            entry: 输入框控件
        """
        self.style_manager.apply_style(entry, 'TEntry')
    
    def style_text(self, text_widget: tk.Text):
        """样式化文本框
        
        Args:
            text_widget: 文本框控件
        """
        self.style_manager.apply_style(text_widget, 'Text')
    
    def style_frame(self, frame: tk.Frame):
        """样式化框架
        
        Args:
            frame: 框架控件
        """
        self.style_manager.apply_style(frame, 'TFrame')
    
    def style_listbox(self, listbox: tk.Listbox):
        """样式化列表框
        
        Args:
            listbox: 列表框控件
        """
        self.style_manager.apply_style(listbox, 'Listbox')
    
    def create_styled_button(self, parent, text: str, variant: str = 'default', 
                           command=None, **kwargs) -> tk.Button:
        """创建样式化按钮
        
        Args:
            parent: 父控件
            text: 按钮文本
            variant: 按钮变体
            command: 点击命令
            **kwargs: 其他参数
            
        Returns:
            样式化按钮控件
        """
        button = tk.Button(parent, text=text, command=command, **kwargs)
        self.style_button(button, variant)
        return button
    
    def create_styled_label(self, parent, text: str, variant: str = 'default', 
                          **kwargs) -> tk.Label:
        """创建样式化标签
        
        Args:
            parent: 父控件
            text: 标签文本
            variant: 标签变体
            **kwargs: 其他参数
            
        Returns:
            样式化标签控件
        """
        label = tk.Label(parent, text=text, **kwargs)
        self.style_label(label, variant)
        return label
    
    def create_styled_entry(self, parent, **kwargs) -> tk.Entry:
        """创建样式化输入框
        
        Args:
            parent: 父控件
            **kwargs: 其他参数
            
        Returns:
            样式化输入框控件
        """
        entry = tk.Entry(parent, **kwargs)
        self.style_entry(entry)
        return entry
    
    def create_styled_frame(self, parent, **kwargs) -> tk.Frame:
        """创建样式化框架
        
        Args:
            parent: 父控件
            **kwargs: 其他参数
            
        Returns:
            样式化框架控件
        """
        frame = tk.Frame(parent, **kwargs)
        self.style_frame(frame)
        return frame


class ResponsiveStyles:
    """响应式样式"""
    
    @staticmethod
    def get_responsive_font_size(base_size: int, screen_width: int) -> int:
        """获取响应式字体大小
        
        Args:
            base_size: 基础字体大小
            screen_width: 屏幕宽度
            
        Returns:
            响应式字体大小
        """
        if screen_width < 480:
            return max(8, base_size - 2)
        elif screen_width < 768:
            return max(9, base_size - 1)
        elif screen_width < 1024:
            return base_size
        else:
            return base_size + 1
    
    @staticmethod
    def get_responsive_padding(base_padding: int, screen_width: int) -> tuple:
        """获取响应式内边距
        
        Args:
            base_padding: 基础内边距
            screen_width: 屏幕宽度
            
        Returns:
            响应式内边距
        """
        if screen_width < 480:
            factor = 0.5
        elif screen_width < 768:
            factor = 0.75
        else:
            factor = 1.0
        
        padding = int(base_padding * factor)
        return (padding, padding // 2)
    
    @staticmethod
    def apply_responsive_style(widget, base_config: Dict[str, Any], 
                             screen_width: int):
        """应用响应式样式
        
        Args:
            widget: 控件对象
            base_config: 基础样式配置
            screen_width: 屏幕宽度
        """
        config = base_config.copy()
        
        # 响应式字体大小
        if 'font' in config and isinstance(config['font'], tuple):
            font_family, font_size = config['font'][:2]
            responsive_size = ResponsiveStyles.get_responsive_font_size(font_size, screen_width)
            config['font'] = (font_family, responsive_size) + config['font'][2:]
        
        # 响应式内边距
        if 'padding' in config and isinstance(config['padding'], tuple):
            base_pad = config['padding'][0]
            responsive_pad = ResponsiveStyles.get_responsive_padding(base_pad, screen_width)
            config['padding'] = responsive_pad
        
        widget.configure(**config)


class AnimationStyles:
    """动画样式"""
    
    @staticmethod
    def fade_in(widget, duration: int = 300, steps: int = 20):
        """淡入动画
        
        Args:
            widget: 控件对象
            duration: 动画持续时间（毫秒）
            steps: 动画步数
        """
        def step_fade(step):
            if step <= steps:
                alpha = step / steps
                # 这里可以实现真正的透明度控制
                # tkinter的原生控件不支持alpha通道，这里只是一个示例
                widget.update_idletasks()
                widget.after(duration // steps, lambda: step_fade(step + 1))
        
        step_fade(1)
    
    @staticmethod
    def fade_out(widget, duration: int = 300, steps: int = 20):
        """淡出动画
        
        Args:
            widget: 控件对象
            duration: 动画持续时间（毫秒）
            steps: 动画步数
        """
        def step_fade(step):
            if step <= steps:
                alpha = 1 - (step / steps)
                # 这里可以实现真正的透明度控制
                widget.update_idletasks()
                widget.after(duration // steps, lambda: step_fade(step + 1))
            else:
                widget.pack_forget()
        
        step_fade(1)
    
    @staticmethod
    def slide_in(widget, direction: str = 'left', duration: int = 300):
        """滑入动画
        
        Args:
            widget: 控件对象
            direction: 滑动方向 ('left', 'right', 'up', 'down')
            duration: 动画持续时间（毫秒）
        """
        # 获取控件当前位置
        widget.update_idletasks()
        
        if direction == 'left':
            # 从左侧滑入
            widget.place(x=-widget.winfo_width(), y=widget.winfo_y())
            target_x = widget.winfo_x()
            
            def animate():
                current_x = widget.winfo_x()
                if current_x < target_x:
                    new_x = current_x + 10
                    widget.place(x=new_x, y=widget.winfo_y())
                    widget.after(duration // 20, animate)
            
            animate()
    
    @staticmethod
    def bounce(widget, duration: int = 500):
        """弹跳动画
        
        Args:
            widget: 控件对象
            duration: 动画持续时间（毫秒）
        """
        widget.update_idletasks()
        original_y = widget.winfo_y()
        
        def bounce_up():
            current_y = widget.winfo_y()
            if current_y > original_y - 20:
                new_y = current_y - 5
                widget.place(y=new_y, x=widget.winfo_x())
                widget.after(duration // 20, bounce_up)
            else:
                bounce_down()
        
        def bounce_down():
            current_y = widget.winfo_y()
            if current_y < original_y:
                new_y = current_y + 2
                widget.place(y=new_y, x=widget.winfo_x())
                widget.after(duration // 20, bounce_down)
        
        bounce_up()


class StyleLoader:
    """样式加载器"""
    
    @staticmethod
    def load_theme_from_file(file_path: str) -> Optional[ColorScheme]:
        """从文件加载主题
        
        Args:
            file_path: 主题文件路径
            
        Returns:
            颜色方案对象
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            return ColorScheme(**theme_data)
        except Exception:
            return None
    
    @staticmethod
    def save_theme_to_file(theme: ColorScheme, file_path: str):
        """保存主题到文件
        
        Args:
            theme: 颜色方案对象
            file_path: 保存路径
        """
        theme_dict = {
            'name': theme.name,
            'primary': theme.primary,
            'secondary': theme.secondary,
            'accent': theme.accent,
            'background': theme.background,
            'surface': theme.surface,
            'text_primary': theme.text_primary,
            'text_secondary': theme.text_secondary,
            'text_disabled': theme.text_disabled,
            'border': theme.border,
            'success': theme.success,
            'warning': theme.warning,
            'error': theme.error,
            'info': theme.info
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(theme_dict, f, indent=2)
    
    @staticmethod
    def load_styles_from_file(file_path: str) -> Optional[Dict[str, Any]]:
        """从文件加载样式配置
        
        Args:
            file_path: 样式文件路径
            
        Returns:
            样式配置字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    @staticmethod
    def save_styles_to_file(styles: Dict[str, Any], file_path: str):
        """保存样式配置到文件
        
        Args:
            styles: 样式配置字典
            file_path: 保存路径
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(styles, f, indent=2)


# 全局主题管理器实例
_global_theme_manager = ThemeManager()
_global_style_manager = StyleManager(_global_theme_manager)
_global_widget_styler = WidgetStyler(_global_style_manager)


def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器
    
    Returns:
        主题管理器实例
    """
    return _global_theme_manager


def get_style_manager() -> StyleManager:
    """获取全局样式管理器
    
    Returns:
        样式管理器实例
    """
    return _global_style_manager


def get_widget_styler() -> WidgetStyler:
    """获取全局控件样式器
    
    Returns:
        控件样式器实例
    """
    return _global_widget_styler


def apply_theme(theme_name: str):
    """应用主题
    
    Args:
        theme_name: 主题名称
    """
    _global_theme_manager.set_theme(theme_name)
    _global_style_manager.update_theme(theme_name)


def create_themed_button(parent, text: str, variant: str = 'default', **kwargs) -> tk.Button:
    """创建主题化按钮
    
    Args:
        parent: 父控件
        text: 按钮文本
        variant: 按钮变体
        **kwargs: 其他参数
        
    Returns:
        主题化按钮控件
    """
    return _global_widget_styler.create_styled_button(parent, text, variant, **kwargs)


def create_themed_label(parent, text: str, variant: str = 'default', **kwargs) -> tk.Label:
    """创建主题化标签
    
    Args:
        parent: 父控件
        text: 标签文本
        variant: 标签变体
        **kwargs: 其他参数
        
    Returns:
        主题化标签控件
    """
    return _global_widget_styler.create_styled_label(parent, text, variant, **kwargs)


def create_themed_entry(parent, **kwargs) -> tk.Entry:
    """创建主题化输入框
    
    Args:
        parent: 父控件
        **kwargs: 其他参数
        
    Returns:
        主题化输入框控件
    """
    return _global_widget_styler.create_styled_entry(parent, **kwargs)


def create_themed_frame(parent, **kwargs) -> tk.Frame:
    """创建主题化框架
    
    Args:
        parent: 父控件
        **kwargs: 其他参数
        
    Returns:
        主题化框架控件
    """
    return _global_widget_styler.create_styled_frame(parent, **kwargs)