"""
Windows客户端实现 - Mirexs桌面应用程序

为Windows平台提供原生客户端实现，包括：
1. Windows特定的窗口样式和交互
2. 注册表集成
3. Windows API调用封装
4. 任务栏和开始菜单集成
5. Windows通知系统集成
"""

import os
import sys
import ctypes
import logging
import platform
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

# 尝试导入Windows特定模块
try:
    import winreg
    import win32gui
    import win32con
    import win32api
    import win32process
    from win32com.client import Dispatch
    WINDOWS_SPECIFIC_AVAILABLE = True
except ImportError:
    WINDOWS_SPECIFIC_AVAILABLE = False
    logging.warning("Windows-specific modules not available. Some features will be limited.")

from ..main_window import MainWindow
from ..taskbar_integration import TaskbarIntegration
from ..system_tray import SystemTray
from ..window_manager import WindowManager
from ..theme_selector import ThemeSelector
from ..shortcut_handler import ShortcutHandler
from ..desktop_metrics import DesktopMetrics

logger = logging.getLogger(__name__)

class WindowsVersion(Enum):
    """Windows版本枚举"""
    UNKNOWN = "unknown"
    WIN7 = "windows_7"
    WIN8 = "windows_8"
    WIN81 = "windows_8.1"
    WIN10 = "windows_10"
    WIN11 = "windows_11"
    WIN_SERVER = "windows_server"

@dataclass
class WindowsClientConfig:
    """Windows客户端配置"""
    # 窗口配置
    window_title: str = "Mirexs - 弥尔思数字生命体"
    initial_width: int = 1200
    initial_height: int = 800
    min_width: int = 800
    min_height: int = 600
    
    # 启动配置
    auto_start: bool = False
    start_minimized: bool = False
    start_in_tray: bool = True
    
    # 集成配置
    enable_taskbar_integration: bool = True
    enable_system_tray: bool = True
    enable_notifications: bool = True
    enable_registry_integration: bool = True
    
    # 性能配置
    enable_gpu_acceleration: bool = True
    enable_background_mode: bool = True
    low_memory_mode: bool = False
    
    # 高级配置
    use_dark_title_bar: bool = True
    enable_transparency: bool = False
    acrylic_effect: bool = False  # Windows 10/11 亚克力效果
    
    # 文件路径
    config_file: str = "windows_client_config.json"
    data_dir: str = "data/windows_client/"

class WindowsClient:
    """
    Windows客户端主类
    
    负责Windows平台客户端的完整生命周期管理，包括：
    - 窗口创建和管理
    - 系统集成（任务栏、托盘、注册表）
    - Windows特定功能（API调用、通知）
    - 性能监控和优化
    - 配置持久化
    """
    
    def __init__(self, config: Optional[WindowsClientConfig] = None):
        """
        初始化Windows客户端
        
        Args:
            config: 客户端配置，如不提供则使用默认配置
        """
        self.config = config or WindowsClientConfig()
        self.platform = platform.system()
        self.windows_version = self._detect_windows_version()
        
        # 组件实例
        self.main_window: Optional[MainWindow] = None
        self.taskbar_integration: Optional[TaskbarIntegration] = None
        self.system_tray: Optional[SystemTray] = None
        self.window_manager: Optional[WindowManager] = None
        self.theme_selector: Optional[ThemeSelector] = None
        self.shortcut_handler: Optional[ShortcutHandler] = None
        self.metrics_collector: Optional[DesktopMetrics] = None
        
        # 状态变量
        self.is_running = False
        self.is_minimized = False
        self.is_tray_only = False
        self.background_mode = False
        
        # 回调注册表
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载配置
        self._load_config()
        
        logger.info(f"WindowsClient initialized on {self.platform} ({self.windows_version.value})")
    
    def _detect_windows_version(self) -> WindowsVersion:
        """检测当前Windows版本"""
        if not WINDOWS_SPECIFIC_AVAILABLE:
            return WindowsVersion.UNKNOWN
        
        try:
            version = platform.version()
            release = platform.release()
            
            if release == "7":
                return WindowsVersion.WIN7
            elif release == "8":
                return WindowsVersion.WIN8
            elif release == "8.1":
                return WindowsVersion.WIN81
            elif release == "10":
                return WindowsVersion.WIN10
            elif release == "11":
                return WindowsVersion.WIN11
            elif "2008" in version or "2012" in version or "2016" in version or "2019" in version or "2022" in version:
                return WindowsVersion.WIN_SERVER
            else:
                return WindowsVersion.UNKNOWN
        except Exception as e:
            logger.error(f"Error detecting Windows version: {e}")
            return WindowsVersion.UNKNOWN
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_config(self):
        """从文件加载配置"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 更新配置
                    for key, value in loaded_config.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
                logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
    
    def _save_config(self):
        """保存配置到文件"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.__dict__, f, indent=2, default=str)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def initialize(self) -> bool:
        """
        初始化客户端所有组件
        
        Returns:
            初始化是否成功
        """
        logger.info("Initializing WindowsClient components...")
        
        try:
            # 初始化指标收集器
            self.metrics_collector = DesktopMetrics()
            self.metrics_collector.start_collection()
            
            # 初始化窗口管理器
            self.window_manager = WindowManager()
            
            # 初始化主题选择器
            self.theme_selector = ThemeSelector()
            
            # 初始化主窗口
            self.main_window = MainWindow(
                title=self.config.window_title,
                width=self.config.initial_width,
                height=self.config.initial_height,
                min_width=self.config.min_width,
                min_height=self.config.min_height,
                use_dark_title_bar=self.config.use_dark_title_bar,
                enable_transparency=self.config.enable_transparency,
                acrylic_effect=self.config.acrylic_effect and self.windows_version in [WindowsVersion.WIN10, WindowsVersion.WIN11]
            )
            
            # 设置窗口事件回调
            self.main_window.on_close = self._on_window_close
            self.main_window.on_minimize = self._on_window_minimize
            self.main_window.on_restore = self._on_window_restore
            self.main_window.on_resize = self._on_window_resize
            self.main_window.on_move = self._on_window_move
            
            # 初始化任务栏集成
            if self.config.enable_taskbar_integration:
                self.taskbar_integration = TaskbarIntegration(self.main_window)
                self.taskbar_integration.initialize()
            
            # 初始化系统托盘
            if self.config.enable_system_tray:
                self.system_tray = SystemTray()
                self.system_tray.on_show_window = self._on_tray_show
                self.system_tray.on_hide_window = self._on_tray_hide
                self.system_tray.on_exit = self._on_tray_exit
                self.system_tray.initialize()
            
            # 初始化快捷键处理器
            self.shortcut_handler = ShortcutHandler()
            self._register_default_shortcuts()
            
            # 应用主题
            if self.theme_selector:
                current_theme = self.theme_selector.get_current_theme()
                self.apply_theme(current_theme)
            
            # Windows特定初始化
            if WINDOWS_SPECIFIC_AVAILABLE:
                self._init_windows_specific()
            
            # 注册到注册表（自动启动）
            if self.config.auto_start and self.config.enable_registry_integration:
                self._set_auto_start(True)
            
            logger.info("WindowsClient initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing WindowsClient: {e}", exc_info=True)
            return False
    
    def _init_windows_specific(self):
        """执行Windows特定的初始化"""
        try:
            # 设置DPI感知
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                pass
            
            # 设置电源管理（防止睡眠）
            if self.config.enable_background_mode:
                self._set_thread_execution_state()
            
            logger.debug("Windows-specific initialization completed")
        except Exception as e:
            logger.error(f"Error in Windows-specific initialization: {e}")
    
    def _set_thread_execution_state(self):
        """设置线程执行状态，防止系统睡眠"""
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        except Exception as e:
            logger.error(f"Error setting thread execution state: {e}")
    
    def _register_default_shortcuts(self):
        """注册默认快捷键"""
        if not self.shortcut_handler:
            return
        
        shortcuts = [
            ("Ctrl+Shift+M", "show_main_window", "显示主窗口"),
            ("Ctrl+Shift+H", "hide_main_window", "隐藏主窗口"),
            ("Ctrl+Shift+Q", "quit_application", "退出应用"),
            ("Ctrl+Shift+T", "toggle_theme", "切换主题"),
            ("Ctrl+Shift+S", "toggle_screenshot", "截屏"),
            ("Ctrl+Shift+V", "toggle_voice_input", "切换语音输入"),
        ]
        
        for key_combo, action, description in shortcuts:
            self.shortcut_handler.register_shortcut(key_combo, action, description)
        
        # 设置回调
        self.shortcut_handler.on_shortcut_triggered = self._on_shortcut_triggered
    
    def _on_shortcut_triggered(self, action: str):
        """快捷键触发回调"""
        logger.debug(f"Shortcut triggered: {action}")
        
        if action == "show_main_window":
            self.show_window()
        elif action == "hide_main_window":
            self.hide_window()
        elif action == "quit_application":
            self.shutdown()
        elif action == "toggle_theme":
            if self.theme_selector:
                self.theme_selector.toggle_theme()
                current_theme = self.theme_selector.get_current_theme()
                self.apply_theme(current_theme)
        elif action == "toggle_screenshot":
            self._trigger_event("screenshot_requested")
        elif action == "toggle_voice_input":
            self._trigger_event("voice_input_toggle")
    
    def _on_window_close(self):
        """窗口关闭事件回调"""
        logger.info("Window close event triggered")
        if self.config.start_in_tray and self.system_tray:
            # 隐藏到托盘而不是退出
            self.hide_to_tray()
        else:
            self.shutdown()
    
    def _on_window_minimize(self):
        """窗口最小化事件回调"""
        self.is_minimized = True
        logger.debug("Window minimized")
        self._trigger_event("window_minimized")
    
    def _on_window_restore(self):
        """窗口恢复事件回调"""
        self.is_minimized = False
        logger.debug("Window restored")
        self._trigger_event("window_restored")
    
    def _on_window_resize(self, width: int, height: int):
        """窗口大小改变事件回调"""
        logger.debug(f"Window resized to {width}x{height}")
        if self.metrics_collector:
            self.metrics_collector.record_window_resize(width, height)
    
    def _on_window_move(self, x: int, y: int):
        """窗口移动事件回调"""
        logger.debug(f"Window moved to ({x}, {y})")
    
    def _on_tray_show(self):
        """托盘显示窗口回调"""
        self.show_window()
    
    def _on_tray_hide(self):
        """托盘隐藏窗口回调"""
        self.hide_window()
    
    def _on_tray_exit(self):
        """托盘退出回调"""
        self.shutdown()
    
    def _set_auto_start(self, enable: bool):
        """
        设置开机自动启动
        
        Args:
            enable: 是否启用自动启动
        """
        if not WINDOWS_SPECIFIC_AVAILABLE:
            logger.warning("Cannot set auto start: Windows modules not available")
            return
        
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "Mirexs"
            executable_path = sys.executable
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enable:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, executable_path)
                    logger.info("Auto start enabled")
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                        logger.info("Auto start disabled")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            logger.error(f"Error setting auto start: {e}")
    
    def show_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()
            self.is_tray_only = False
            logger.info("Main window shown")
    
    def hide_window(self):
        """隐藏主窗口"""
        if self.main_window:
            self.main_window.hide()
            logger.info("Main window hidden")
    
    def hide_to_tray(self):
        """隐藏到系统托盘"""
        self.hide_window()
        self.is_tray_only = True
        if self.system_tray:
            self.system_tray.show_notification(
                "Mirexs 仍在运行",
                "应用程序已最小化到系统托盘"
            )
        logger.info("Application hidden to system tray")
    
    def apply_theme(self, theme_name: str):
        """
        应用主题
        
        Args:
            theme_name: 主题名称
        """
        if not self.main_window or not self.theme_selector:
            return
        
        theme = self.theme_selector.get_theme(theme_name)
        if theme:
            self.main_window.apply_theme(theme)
            if self.taskbar_integration:
                self.taskbar_integration.update_theme(theme)
            logger.info(f"Theme applied: {theme_name}")
    
    def register_event_handler(self, event: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        logger.debug(f"Event handler registered for {event}")
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """触发事件"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event handler for {event}: {e}")
    
    def run(self):
        """运行客户端主循环"""
        if not self.is_running:
            self.is_running = True
            
            # 根据配置显示或隐藏窗口
            if self.config.start_minimized or self.config.start_in_tray:
                if self.config.start_in_tray:
                    self.hide_to_tray()
                else:
                    self.hide_window()
            else:
                self.show_window()
            
            logger.info("WindowsClient started")
            
            # 进入消息循环（由底层GUI框架处理）
            # 这里假设底层框架会处理事件循环
    
    def shutdown(self):
        """关闭客户端"""
        logger.info("Shutting down WindowsClient...")
        
        self.is_running = False
        
        # 保存配置
        self._save_config()
        
        # 清理资源
        if self.system_tray:
            self.system_tray.shutdown()
        
        if self.taskbar_integration:
            self.taskbar_integration.shutdown()
        
        if self.main_window:
            self.main_window.close()
        
        if self.metrics_collector:
            self.metrics_collector.stop_collection()
            report = self.metrics_collector.generate_report()
            logger.info(f"Desktop metrics report: {report}")
        
        # 恢复电源设置
        if WINDOWS_SPECIFIC_AVAILABLE:
            try:
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            except:
                pass
        
        logger.info("WindowsClient shutdown completed")
        self._trigger_event("shutdown")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Returns:
            状态字典
        """
        return {
            "platform": self.platform,
            "windows_version": self.windows_version.value,
            "is_running": self.is_running,
            "is_minimized": self.is_minimized,
            "is_tray_only": self.is_tray_only,
            "background_mode": self.background_mode,
            "main_window_visible": self.main_window.is_visible() if self.main_window else False,
            "config": self.config.__dict__,
            "metrics": self.metrics_collector.get_latest_metrics() if self.metrics_collector else {}
        }

# 单例模式实现
_windows_client_instance: Optional[WindowsClient] = None

def get_windows_client(config: Optional[WindowsClientConfig] = None) -> WindowsClient:
    """
    获取Windows客户端单例
    
    Args:
        config: 客户端配置
    
    Returns:
        Windows客户端实例
    """
    global _windows_client_instance
    if _windows_client_instance is None:
        _windows_client_instance = WindowsClient(config)
    return _windows_client_instance

def create_windows_client(config: Optional[WindowsClientConfig] = None) -> WindowsClient:
    """
    创建新的Windows客户端实例（非单例）
    
    Args:
        config: 客户端配置
    
    Returns:
        Windows客户端实例
    """
    return WindowsClient(config)


