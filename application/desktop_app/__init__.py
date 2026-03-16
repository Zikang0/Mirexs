"""
桌面应用程序模块 - Mirexs应用接口层

提供跨平台的桌面客户端实现，包括Windows、macOS和Linux平台的客户端，
以及主窗口管理、任务栏集成、系统托盘、窗口管理、主题选择和快捷方式处理等功能。

此模块是Mirexs数字生命体在桌面端的入口点，负责：
1. 创建和管理应用程序主窗口
2. 集成系统任务栏和托盘功能
3. 处理窗口生命周期和事件
4. 管理应用程序主题和样式
5. 处理系统级快捷键
6. 收集桌面端性能指标
"""

from .windows_client import WindowsClient
from .macos_client import MacOSClient
from .linux_client import LinuxClient
from .main_window import MainWindow
from .taskbar_integration import TaskbarIntegration
from .system_tray import SystemTray
from .window_manager import WindowManager
from .theme_selector import ThemeSelector
from .shortcut_handler import ShortcutHandler
from .desktop_metrics import DesktopMetrics

__all__ = [
    'WindowsClient',
    'MacOSClient', 
    'LinuxClient',
    'MainWindow',
    'TaskbarIntegration',
    'SystemTray',
    'WindowManager',
    'ThemeSelector',
    'ShortcutHandler',
    'DesktopMetrics'
]
