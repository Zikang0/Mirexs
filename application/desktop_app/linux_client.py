"""
Linux客户端实现 - Mirexs桌面应用程序

为Linux平台提供原生客户端实现，包括：
1. Linux桌面环境集成（GNOME、KDE等）
2. 系统托盘集成
3. 窗口管理器集成
4. 通知系统集成
5. D-Bus服务集成
"""

import os
import sys
import logging
import platform
import subprocess
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json
import glob

# 尝试导入Linux特定模块
try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    from gi.repository import GLib, Gio
    LINUX_SPECIFIC_AVAILABLE = True
except ImportError:
    LINUX_SPECIFIC_AVAILABLE = False
    logging.warning("Linux-specific modules (dbus, gi) not available. Some features will be limited.")

from ..main_window import MainWindow
from ..taskbar_integration import TaskbarIntegration
from ..system_tray import SystemTray
from ..window_manager import WindowManager
from ..theme_selector import ThemeSelector
from ..shortcut_handler import ShortcutHandler
from ..desktop_metrics import DesktopMetrics

logger = logging.getLogger(__name__)

class LinuxDesktopEnv(Enum):
    """Linux桌面环境枚举"""
    UNKNOWN = "unknown"
    GNOME = "gnome"
    KDE = "kde"
    XFCE = "xfce"
    CINNAMON = "cinnamon"
    MATE = "mate"
    LXDE = "lxde"
    LXQT = "lxqt"
    UNITY = "unity"
    DEEPIN = "deepin"
    SWAY = "sway"
    I3 = "i3"

class LinuxDistro(Enum):
    """Linux发行版枚举"""
    UNKNOWN = "unknown"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    FEDORA = "fedora"
    RHEL = "rhel"
    CENTOS = "centos"
    ARCH = "arch"
    MANJARO = "manjaro"
    OPENSUSE = "opensuse"
    DEEPIN = "deepin"
    ELEMENTARY = "elementary"

@dataclass
class LinuxClientConfig:
    """Linux客户端配置"""
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
    enable_tray_icon: bool = True
    enable_notifications: bool = True
    enable_dbus_service: bool = True
    enable_mpris_integration: bool = True  # 媒体播放器集成
    enable_portal_integration: bool = True  # Flatpak/XDG Desktop Portal
    
    # 性能配置
    enable_gpu_acceleration: bool = True
    enable_background_mode: bool = True
    low_memory_mode: bool = False
    
    # 高级配置
    use_csd: bool = True  # 客户端装饰
    use_wayland: bool = False
    compositor_sync: bool = True
    
    # 文件路径
    config_file: str = "linux_client_config.json"
    data_dir: str = "data/linux_client/"

class DBusService(dbus.service.Object):
    """D-Bus服务类，用于Linux桌面集成"""
    
    def __init__(self, client: 'LinuxClient', bus_name: str, object_path: str):
        """
        初始化D-Bus服务
        
        Args:
            client: Linux客户端实例
            bus_name: D-Bus总线名称
            object_path: D-Bus对象路径
        """
        self.client = client
        bus = dbus.SessionBus()
        bus_name_obj = dbus.service.BusName(bus_name, bus=bus)
        super().__init__(bus_name_obj, object_path)
    
    @dbus.service.method('com.mirexs.Interface', in_signature='', out_signature='s')
    def GetStatus(self):
        """获取Mirexs状态"""
        import json
        return json.dumps(self.client.get_status())
    
    @dbus.service.method('com.mirexs.Interface', in_signature='', out_signature='')
    def ShowWindow(self):
        """显示主窗口"""
        self.client.show_window()
    
    @dbus.service.method('com.mirexs.Interface', in_signature='', out_signature='')
    def HideWindow(self):
        """隐藏主窗口"""
        self.client.hide_window()
    
    @dbus.service.method('com.mirexs.Interface', in_signature='s', out_signature='')
    def SendMessage(self, message: str):
        """发送消息给Mirexs"""
        self.client._trigger_event("dbus_message", message)
    
    @dbus.service.signal('com.mirexs.Interface', signature='s')
    def Notification(self, message: str):
        """发送通知信号"""
        return message

class LinuxClient:
    """
    Linux客户端主类
    
    负责Linux平台客户端的完整生命周期管理，包括：
    - 窗口创建和管理
    - 桌面环境集成（系统托盘、通知）
    - D-Bus服务集成
    - 性能监控和优化
    - 配置持久化
    """
    
    def __init__(self, config: Optional[LinuxClientConfig] = None):
        """
        初始化Linux客户端
        
        Args:
            config: 客户端配置，如不提供则使用默认配置
        """
        self.config = config or LinuxClientConfig()
        self.platform = platform.system()
        self.desktop_env = self._detect_desktop_environment()
        self.distro = self._detect_distro()
        
        # 组件实例
        self.main_window: Optional[MainWindow] = None
        self.tray_icon: Optional[SystemTray] = None
        self.window_manager: Optional[WindowManager] = None
        self.theme_selector: Optional[ThemeSelector] = None
        self.shortcut_handler: Optional[ShortcutHandler] = None
        self.metrics_collector: Optional[DesktopMetrics] = None
        self.dbus_service: Optional[DBusService] = None
        
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
        
        logger.info(f"LinuxClient initialized on {self.platform} ({self.desktop_env.value}/{self.distro.value})")
    
    def _detect_desktop_environment(self) -> LinuxDesktopEnv:
        """检测当前Linux桌面环境"""
        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        
        if 'gnome' in desktop:
            return LinuxDesktopEnv.GNOME
        elif 'kde' in desktop or 'plasma' in desktop:
            return LinuxDesktopEnv.KDE
        elif 'xfce' in desktop:
            return LinuxDesktopEnv.XFCE
        elif 'cinnamon' in desktop:
            return LinuxDesktopEnv.CINNAMON
        elif 'mate' in desktop:
            return LinuxDesktopEnv.MATE
        elif 'lxde' in desktop:
            return LinuxDesktopEnv.LXDE
        elif 'lxqt' in desktop:
            return LinuxDesktopEnv.LXQT
        elif 'unity' in desktop:
            return LinuxDesktopEnv.UNITY
        elif 'deepin' in desktop:
            return LinuxDesktopEnv.DEEPIN
        elif 'sway' in desktop:
            return LinuxDesktopEnv.SWAY
        elif 'i3' in desktop:
            return LinuxDesktopEnv.I3
        else:
            return LinuxDesktopEnv.UNKNOWN
    
    def _detect_distro(self) -> LinuxDistro:
        """检测Linux发行版"""
        try:
            # 检查 /etc/os-release
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read()
                    if 'ubuntu' in content.lower():
                        return LinuxDistro.UBUNTU
                    elif 'debian' in content.lower():
                        return LinuxDistro.DEBIAN
                    elif 'fedora' in content.lower():
                        return LinuxDistro.FEDORA
                    elif 'rhel' in content.lower() or 'red hat' in content.lower():
                        return LinuxDistro.RHEL
                    elif 'centos' in content.lower():
                        return LinuxDistro.CENTOS
                    elif 'arch' in content.lower():
                        return LinuxDistro.ARCH
                    elif 'manjaro' in content.lower():
                        return LinuxDistro.MANJARO
                    elif 'opensuse' in content.lower():
                        return LinuxDistro.OPENSUSE
                    elif 'deepin' in content.lower():
                        return LinuxDistro.DEEPIN
                    elif 'elementary' in content.lower():
                        return LinuxDistro.ELEMENTARY
        except:
            pass
        
        return LinuxDistro.UNKNOWN
    
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
        logger.info("Initializing LinuxClient components...")
        
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
                use_csd=self.config.use_csd,
                use_wayland=self.config.use_wayland
            )
            
            # 设置窗口事件回调
            self.main_window.on_close = self._on_window_close
            self.main_window.on_minimize = self._on_window_minimize
            self.main_window.on_restore = self._on_window_restore
            self.main_window.on_resize = self._on_window_resize
            self.main_window.on_move = self._on_window_move
            
            # 初始化系统托盘
            if self.config.enable_tray_icon:
                self.tray_icon = SystemTray()
                self.tray_icon.set_platform("linux")
                self.tray_icon.set_desktop_environment(self.desktop_env.value)
                self.tray_icon.on_show_window = self._on_tray_show
                self.tray_icon.on_hide_window = self._on_tray_hide
                self.tray_icon.on_exit = self._on_tray_exit
                self.tray_icon.initialize()
            
            # 初始化快捷键处理器
            self.shortcut_handler = ShortcutHandler()
            self._register_default_shortcuts()
            
            # 应用主题
            if self.theme_selector:
                current_theme = self.theme_selector.get_current_theme()
                self.apply_theme(current_theme)
            
            # Linux特定初始化
            if LINUX_SPECIFIC_AVAILABLE:
                self._init_linux_specific()
            
            # 设置自动启动
            if self.config.auto_start:
                self._set_auto_start(True)
            
            logger.info("LinuxClient initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing LinuxClient: {e}", exc_info=True)
            return False
    
    def _init_linux_specific(self):
        """执行Linux特定的初始化"""
        try:
            # 初始化D-Bus主循环
            if self.config.enable_dbus_service and LINUX_SPECIFIC_AVAILABLE:
                dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
                
                # 注册D-Bus服务
                bus_name = 'com.mirexs.Client'
                object_path = '/com/mirexs/Client'
                
                try:
                    self.dbus_service = DBusService(self, bus_name, object_path)
                    logger.info(f"D-Bus service registered: {bus_name} {object_path}")
                except Exception as e:
                    logger.error(f"Failed to register D-Bus service: {e}")
            
            # 配置Wayland支持
            if self.config.use_wayland:
                os.environ['GDK_BACKEND'] = 'wayland'
                os.environ['QT_QPA_PLATFORM'] = 'wayland'
            
            # 设置GTK主题
            self._setup_gtk_theme()
            
            logger.debug("Linux-specific initialization completed")
        except Exception as e:
            logger.error(f"Error in Linux-specific initialization: {e}")
    
    def _setup_gtk_theme(self):
        """设置GTK主题"""
        try:
            # 根据桌面环境设置GTK主题
            if self.desktop_env == LinuxDesktopEnv.GNOME:
                # 使用gsettings获取系统主题
                result = subprocess.run(
                    ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0:
                    theme = result.stdout.strip().strip("'")
                    os.environ['GTK_THEME'] = theme
            
            elif self.desktop_env == LinuxDesktopEnv.KDE:
                # KDE使用不同的配置方式
                pass
                
        except Exception as e:
            logger.error(f"Error setting up GTK theme: {e}")
    
    def _register_default_shortcuts(self):
        """注册默认快捷键（使用Ctrl/Alt/Super键）"""
        if not self.shortcut_handler:
            return
        
        shortcuts = [
            ("Ctrl+Shift+M", "show_main_window", "显示主窗口"),
            ("Ctrl+Shift+H", "hide_main_window", "隐藏主窗口"),
            ("Ctrl+Q", "quit_application", "退出应用"),
            ("Ctrl+Shift+T", "toggle_theme", "切换主题"),
            ("Ctrl+Shift+S", "toggle_screenshot", "截屏"),
            ("Ctrl+Shift+V", "toggle_voice_input", "切换语音输入"),
            ("Super+M", "show_main_window_alt", "显示主窗口（备用）"),
        ]
        
        for key_combo, action, description in shortcuts:
            self.shortcut_handler.register_shortcut(key_combo, action, description)
        
        # 设置回调
        self.shortcut_handler.on_shortcut_triggered = self._on_shortcut_triggered
    
    def _on_shortcut_triggered(self, action: str):
        """快捷键触发回调"""
        logger.debug(f"Shortcut triggered: {action}")
        
        if action in ["show_main_window", "show_main_window_alt"]:
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
        if self.config.start_in_tray and self.tray_icon:
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
        设置开机自动启动（通过desktop文件）
        
        Args:
            enable: 是否启用自动启动
        """
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            
            desktop_file_path = os.path.join(autostart_dir, "mirexs.desktop")
            
            if enable:
                # 创建desktop文件
                desktop_content = f"""[Desktop Entry]
Type=Application
Name=Mirexs
Comment=Emotional Digital Life Companion
Exec={sys.executable} -m mirexs.launch.linux
Icon=mirexs
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""
                with open(desktop_file_path, 'w') as f:
                    f.write(desktop_content)
                
                logger.info("Auto start enabled")
            else:
                # 删除desktop文件
                if os.path.exists(desktop_file_path):
                    os.remove(desktop_file_path)
                logger.info("Auto start disabled")
                
        except Exception as e:
            logger.error(f"Error setting auto start: {e}")
    
    def show_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()
            self.is_tray_only = False
            
            # 提升窗口
            if hasattr(self.main_window, 'present'):
                self.main_window.present()
            
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
        if self.tray_icon:
            self.tray_icon.show_notification(
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
            
            logger.info("LinuxClient started")
            
            # 进入主循环（由底层GUI框架处理）
    
    def shutdown(self):
        """关闭客户端"""
        logger.info("Shutting down LinuxClient...")
        
        self.is_running = False
        
        # 保存配置
        self._save_config()
        
        # 清理资源
        if self.tray_icon:
            self.tray_icon.shutdown()
        
        if self.main_window:
            self.main_window.close()
        
        if self.metrics_collector:
            self.metrics_collector.stop_collection()
            report = self.metrics_collector.generate_report()
            logger.info(f"Desktop metrics report: {report}")
        
        # 清理D-Bus服务
        self.dbus_service = None
        
        logger.info("LinuxClient shutdown completed")
        self._trigger_event("shutdown")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Returns:
            状态字典
        """
        return {
            "platform": self.platform,
            "desktop_env": self.desktop_env.value,
            "distro": self.distro.value,
            "is_running": self.is_running,
            "is_minimized": self.is_minimized,
            "is_tray_only": self.is_tray_only,
            "background_mode": self.background_mode,
            "main_window_visible": self.main_window.is_visible() if self.main_window else False,
            "config": self.config.__dict__,
            "metrics": self.metrics_collector.get_latest_metrics() if self.metrics_collector else {}
        }

# 单例模式实现
_linux_client_instance: Optional[LinuxClient] = None

def get_linux_client(config: Optional[LinuxClientConfig] = None) -> LinuxClient:
    """
    获取Linux客户端单例
    
    Args:
        config: 客户端配置
    
    Returns:
        Linux客户端实例
    """
    global _linux_client_instance
    if _linux_client_instance is None:
        _linux_client_instance = LinuxClient(config)
    return _linux_client_instance

def create_linux_client(config: Optional[LinuxClientConfig] = None) -> LinuxClient:
    """
    创建新的Linux客户端实例（非单例）
    
    Args:
        config: 客户端配置
    
    Returns:
        Linux客户端实例
    """
    return LinuxClient(config)


