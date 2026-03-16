"""
主窗口模块 - Mirexs桌面应用程序

提供应用程序主窗口的创建、管理和生命周期控制，包括：
1. 窗口的创建和初始化
2. 窗口事件处理（打开、关闭、最小化、恢复、移动、调整大小）
3. 内容区域管理
4. 平台适配的窗口样式
5. 窗口状态持久化
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

# 尝试导入GUI框架
try:
    from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
    from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QEvent
    from PyQt5.QtGui import QIcon, QPalette, QColor
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    logging.warning("PyQt5 not available. Using fallback implementation.")

logger = logging.getLogger(__name__)

class WindowState(Enum):
    """窗口状态枚举"""
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    HIDDEN = "hidden"

@dataclass
class WindowGeometry:
    """窗口几何信息"""
    x: int = 100
    y: int = 100
    width: int = 1200
    height: int = 800
    state: WindowState = WindowState.NORMAL
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "state": self.state.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowGeometry':
        """从字典创建"""
        return cls(
            x=data.get("x", 100),
            y=data.get("y", 100),
            width=data.get("width", 1200),
            height=data.get("height", 800),
            state=WindowState(data.get("state", "normal"))
        )

@dataclass
class MainWindowConfig:
    """主窗口配置"""
    title: str = "Mirexs - 弥尔思数字生命体"
    initial_width: int = 1200
    initial_height: int = 800
    min_width: int = 800
    min_height: int = 600
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    
    # 平台特定配置
    use_dark_title_bar: bool = True
    enable_transparency: bool = False
    acrylic_effect: bool = False
    use_vibrancy: bool = False
    titlebar_appearance: str = "unified"
    traffic_lights_style: str = "normal"
    use_csd: bool = True
    use_wayland: bool = False
    
    # 行为配置
    remember_geometry: bool = True
    restore_state: bool = True
    confirm_on_close: bool = False
    
    # 文件路径
    geometry_file: str = "window_geometry.json"
    data_dir: str = "data/main_window/"

class MainWindow:
    """
    应用程序主窗口类
    
    负责主窗口的创建、管理和事件处理，支持多平台适配。
    """
    
    def __init__(self, config: Optional[MainWindowConfig] = None):
        """
        初始化主窗口
        
        Args:
            config: 窗口配置，如不提供则使用默认配置
        """
        self.config = config or MainWindowConfig()
        
        # 窗口状态
        self.geometry = WindowGeometry(
            width=self.config.initial_width,
            height=self.config.initial_height
        )
        self.state = WindowState.NORMAL
        self.is_initialized = False
        self.is_visible = False
        
        # 回调函数
        self.on_close: Optional[Callable] = None
        self.on_minimize: Optional[Callable] = None
        self.on_restore: Optional[Callable] = None
        self.on_resize: Optional[Callable[[int, int], None]] = None
        self.on_move: Optional[Callable[[int, int], None]] = None
        self.on_fullscreen: Optional[Callable[[bool], None]] = None
        
        # Qt窗口实例（如果使用Qt）
        self._qt_window: Optional[QMainWindow] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载保存的窗口几何信息
        if self.config.remember_geometry:
            self._load_geometry()
        
        logger.info(f"MainWindow initialized with title: {self.config.title}")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_geometry(self):
        """从文件加载窗口几何信息"""
        geometry_path = os.path.join(self.config.data_dir, self.config.geometry_file)
        if os.path.exists(geometry_path):
            try:
                with open(geometry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.geometry = WindowGeometry.from_dict(data)
                logger.info(f"Window geometry loaded from {geometry_path}")
            except Exception as e:
                logger.error(f"Error loading window geometry: {e}")
    
    def _save_geometry(self):
        """保存窗口几何信息到文件"""
        if not self.config.remember_geometry:
            return
        
        geometry_path = os.path.join(self.config.data_dir, self.config.geometry_file)
        try:
            with open(geometry_path, 'w', encoding='utf-8') as f:
                json.dump(self.geometry.to_dict(), f, indent=2)
            logger.debug(f"Window geometry saved to {geometry_path}")
        except Exception as e:
            logger.error(f"Error saving window geometry: {e}")
    
    def initialize(self) -> bool:
        """
        初始化窗口（创建底层窗口）
        
        Returns:
            初始化是否成功
        """
        if self.is_initialized:
            logger.warning("MainWindow already initialized")
            return True
        
        logger.info("Initializing MainWindow...")
        
        try:
            if QT_AVAILABLE:
                self._init_qt_window()
            else:
                self._init_fallback_window()
            
            self.is_initialized = True
            logger.info("MainWindow initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MainWindow: {e}", exc_info=True)
            return False
    
    def _init_qt_window(self):
        """使用PyQt5初始化窗口"""
        class MirexsMainWindow(QMainWindow):
            """Mirexs主窗口类（Qt实现）"""
            
            def __init__(self, parent_window):
                super().__init__()
                self.parent_window = parent_window
                self.setWindowTitle(parent_window.config.title)
                
                # 设置窗口大小
                self.resize(
                    parent_window.geometry.width,
                    parent_window.geometry.height
                )
                
                # 设置最小大小
                self.setMinimumSize(
                    parent_window.config.min_width,
                    parent_window.config.min_height
                )
                
                # 设置最大大小
                if parent_window.config.max_width and parent_window.config.max_height:
                    self.setMaximumSize(
                        parent_window.config.max_width,
                        parent_window.config.max_height
                    )
                
                # 设置窗口标志
                flags = Qt.Window
                if parent_window.config.use_dark_title_bar:
                    flags |= Qt.FramelessWindowHint
                
                self.setWindowFlags(flags)
                
                # 创建中央部件
                central_widget = QWidget()
                self.setCentralWidget(central_widget)
                
                # 创建布局
                layout = QVBoxLayout()
                central_widget.setLayout(layout)
                
                # 设置样式
                self._apply_style()
            
            def _apply_style(self):
                """应用样式"""
                if self.parent_window.config.use_dark_title_bar:
                    self.setStyleSheet("""
                        QMainWindow {
                            background-color: #1e1e1e;
                            color: #ffffff;
                        }
                    """)
            
            def closeEvent(self, event):
                """关闭事件"""
                if self.parent_window.on_close:
                    self.parent_window.on_close()
                event.accept()
            
            def changeEvent(self, event):
                """状态改变事件"""
                if event.type() == QEvent.WindowStateChange:
                    if self.windowState() & Qt.WindowMinimized:
                        if self.parent_window.on_minimize:
                            self.parent_window.on_minimize()
                    elif self.windowState() == Qt.WindowNoState:
                        if self.parent_window.on_restore:
                            self.parent_window.on_restore()
                
                super().changeEvent(event)
            
            def resizeEvent(self, event):
                """调整大小事件"""
                size = event.size()
                if self.parent_window.on_resize:
                    self.parent_window.on_resize(size.width(), size.height())
                super().resizeEvent(event)
            
            def moveEvent(self, event):
                """移动事件"""
                pos = self.pos()
                if self.parent_window.on_move:
                    self.parent_window.on_move(pos.x(), pos.y())
                super().moveEvent(event)
        
        self._qt_window = MirexsMainWindow(self)
    
    def _init_fallback_window(self):
        """回退实现：不创建实际窗口"""
        logger.warning("Using fallback window implementation (no GUI)")
        # 在回退模式下，只记录状态
    
    def show(self):
        """显示窗口"""
        if not self.is_initialized:
            self.initialize()
        
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.show()
            self.is_visible = True
            self.state = WindowState.NORMAL
            logger.debug("Window shown")
    
    def hide(self):
        """隐藏窗口"""
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.hide()
            self.is_visible = False
            self.state = WindowState.HIDDEN
            logger.debug("Window hidden")
    
    def close(self):
        """关闭窗口"""
        # 保存窗口几何信息
        self._update_geometry_from_window()
        self._save_geometry()
        
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.close()
        
        self.is_visible = False
        logger.info("Window closed")
    
    def minimize(self):
        """最小化窗口"""
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.showMinimized()
            self.state = WindowState.MINIMIZED
            logger.debug("Window minimized")
    
    def maximize(self):
        """最大化窗口"""
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.showMaximized()
            self.state = WindowState.MAXIMIZED
            logger.debug("Window maximized")
    
    def restore(self):
        """恢复窗口（从最小化/最大化）"""
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.showNormal()
            self.state = WindowState.NORMAL
            logger.debug("Window restored")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if QT_AVAILABLE and self._qt_window:
            if self.state == WindowState.FULLSCREEN:
                self._qt_window.showNormal()
                self.state = WindowState.NORMAL
                if self.on_fullscreen:
                    self.on_fullscreen(False)
            else:
                self._qt_window.showFullScreen()
                self.state = WindowState.FULLSCREEN
                if self.on_fullscreen:
                    self.on_fullscreen(True)
    
    def set_title(self, title: str):
        """设置窗口标题"""
        self.config.title = title
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.setWindowTitle(title)
    
    def set_geometry(self, x: int, y: int, width: int, height: int):
        """设置窗口位置和大小"""
        self.geometry.x = x
        self.geometry.y = y
        self.geometry.width = width
        self.geometry.height = height
        
        if QT_AVAILABLE and self._qt_window:
            self._qt_window.setGeometry(x, y, width, height)
    
    def center_on_screen(self):
        """将窗口居中显示"""
        if QT_AVAILABLE and self._qt_window:
            screen_geometry = QApplication.primaryScreen().availableGeometry()
            x = (screen_geometry.width() - self.geometry.width) // 2
            y = (screen_geometry.height() - self.geometry.height) // 2
            self._qt_window.move(x, y)
            self.geometry.x = x
            self.geometry.y = y
    
    def apply_theme(self, theme: Dict[str, Any]):
        """
        应用主题
        
        Args:
            theme: 主题配置字典
        """
        if not QT_AVAILABLE or not self._qt_window:
            return
        
        try:
            # 应用背景颜色
            if "background_color" in theme:
                palette = self._qt_window.palette()
                palette.setColor(
                    QPalette.Window,
                    QColor(theme["background_color"])
                )
                self._qt_window.setPalette(palette)
            
            # 应用样式表
            if "stylesheet" in theme:
                self._qt_window.setStyleSheet(theme["stylesheet"])
            
            logger.debug(f"Theme applied: {theme.get('name', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Error applying theme: {e}")
    
    def _update_geometry_from_window(self):
        """从窗口更新几何信息"""
        if QT_AVAILABLE and self._qt_window:
            geometry = self._qt_window.geometry()
            self.geometry.x = geometry.x()
            self.geometry.y = geometry.y()
            self.geometry.width = geometry.width()
            self.geometry.height = geometry.height()
            
            # 更新窗口状态
            if self._qt_window.isMinimized():
                self.state = WindowState.MINIMIZED
            elif self._qt_window.isMaximized():
                self.state = WindowState.MAXIMIZED
            elif self._qt_window.isFullScreen():
                self.state = WindowState.FULLSCREEN
            else:
                self.state = WindowState.NORMAL
    
    def get_content_widget(self):
        """
        获取内容部件，供子组件嵌入
        
        Returns:
            内容部件，如果没有Qt则返回None
        """
        if QT_AVAILABLE and self._qt_window:
            return self._qt_window.centralWidget()
        return None
    
    def is_visible(self) -> bool:
        """窗口是否可见"""
        return self.is_visible
    
    def get_state(self) -> Dict[str, Any]:
        """
        获取窗口状态
        
        Returns:
            窗口状态字典
        """
        self._update_geometry_from_window()
        
        return {
            "geometry": self.geometry.to_dict(),
            "state": self.state.value,
            "is_visible": self.is_visible,
            "is_initialized": self.is_initialized,
            "title": self.config.title
        }

# 全局主窗口实例
_main_window_instance: Optional[MainWindow] = None

def get_main_window(config: Optional[MainWindowConfig] = None) -> MainWindow:
    """
    获取主窗口单例
    
    Args:
        config: 窗口配置
    
    Returns:
        主窗口实例
    """
    global _main_window_instance
    if _main_window_instance is None:
        _main_window_instance = MainWindow(config)
    return _main_window_instance

def create_main_window(config: Optional[MainWindowConfig] = None) -> MainWindow:
    """
    创建新的主窗口实例（非单例）
    
    Args:
        config: 窗口配置
    
    Returns:
        主窗口实例
    """
    return MainWindow(config)

