"""
macOS客户端实现 - Mirexs桌面应用程序

为macOS平台提供原生客户端实现，包括：
1. macOS特定的窗口样式和交互
2. 菜单栏集成
3. Dock图标和功能
4. macOS通知中心集成
5. 系统服务集成
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
import plistlib

# 尝试导入macOS特定模块
try:
    import AppKit
    import Foundation
    import Cocoa
    import Quartz
    MACOS_SPECIFIC_AVAILABLE = True
except ImportError:
    MACOS_SPECIFIC_AVAILABLE = False
    logging.warning("macOS-specific modules (PyObjC) not available. Some features will be limited.")

from ..main_window import MainWindow
from ..taskbar_integration import TaskbarIntegration  # 在macOS中对应Dock集成
from ..system_tray import SystemTray  # 在macOS中对应菜单栏图标
from ..window_manager import WindowManager
from ..theme_selector import ThemeSelector
from ..shortcut_handler import ShortcutHandler
from ..desktop_metrics import DesktopMetrics

logger = logging.getLogger(__name__)

class MacOSVersion(Enum):
    """macOS版本枚举"""
    UNKNOWN = "unknown"
    CATALINA = "catalina"  # 10.15
    BIG_SUR = "big_sur"    # 11.0
    MONTEREY = "monterey"  # 12.0
    VENTURA = "ventura"    # 13.0
    SONOMA = "sonoma"      # 14.0

class DockBehavior(Enum):
    """Dock行为枚举"""
    NORMAL = "normal"              # 正常显示Dock图标
    MINIMIZED = "minimized"        # 最小化到Dock
    HIDDEN = "hidden"              # 隐藏Dock图标
    ONLY_INDICATOR = "indicator"   # 只显示指示器

@dataclass
class MacOSClientConfig:
    """macOS客户端配置"""
    # 窗口配置
    window_title: str = "Mirexs - 弥尔思数字生命体"
    initial_width: int = 1200
    initial_height: int = 800
    min_width: int = 800
    min_height: int = 600
    
    # 启动配置
    auto_start: bool = False
    start_minimized: bool = False
    start_in_menu_bar: bool = False
    
    # 集成配置
    enable_dock_integration: bool = True
    enable_menu_bar_icon: bool = True
    enable_notifications: bool = True
    enable_handoff: bool = True  # Handoff功能
    enable_services_menu: bool = True  # 服务菜单集成
    
    # 性能配置
    enable_gpu_acceleration: bool = True
    enable_background_mode: bool = True
    low_memory_mode: bool = False
    enable_app_nap: bool = False  # App Nap（节能）
    
    # 高级配置
    use_vibrancy: bool = True  # 毛玻璃效果
    titlebar_appearance: str = "unified"  # unified, transparent, hidden
    traffic_lights_style: str = "normal"  # normal, tinted
    
    # 文件路径
    config_file: str = "macos_client_config.json"
    data_dir: str = "data/macos_client/"

class MacOSClient:
    """
    macOS客户端主类
    
    负责macOS平台客户端的完整生命周期管理，包括：
    - 窗口创建和管理（符合macOS HIG）
    - 系统集成（Dock、菜单栏、通知中心）
    - macOS特定功能（Handoff、Services、App Nap）
    - 性能监控和优化
    - 配置持久化
    """
    
    def __init__(self, config: Optional[MacOSClientConfig] = None):
        """
        初始化macOS客户端
        
        Args:
            config: 客户端配置，如不提供则使用默认配置
        """
        self.config = config or MacOSClientConfig()
        self.platform = platform.system()
        self.macos_version = self._detect_macos_version()
        
        # 组件实例
        self.main_window: Optional[MainWindow] = None
        self.dock_integration: Optional[TaskbarIntegration] = None  # 复用TaskbarIntegration接口
        self.menu_bar_icon: Optional[SystemTray] = None  # 复用SystemTray接口
        self.window_manager: Optional[WindowManager] = None
        self.theme_selector: Optional[ThemeSelector] = None
        self.shortcut_handler: Optional[ShortcutHandler] = None
        self.metrics_collector: Optional[DesktopMetrics] = None
        
        # 状态变量
        self.is_running = False
        self.is_minimized = False
        self.is_in_menu_bar = False
        self.background_mode = False
        self.dock_behavior = DockBehavior.NORMAL
        
        # 回调注册表
        self._event_handlers: Dict[str, List[Callable]] = {}
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载配置
        self._load_config()
        
        logger.info(f"MacOSClient initialized on {self.platform} ({self.macos_version.value})")
    
    def _detect_macos_version(self) -> MacOSVersion:
        """检测当前macOS版本"""
        if not MACOS_SPECIFIC_AVAILABLE:
            return MacOSVersion.UNKNOWN
        
        try:
            version = platform.mac_ver()[0]
            major, minor = map(int, version.split('.')[:2])
            
            if major == 10 and minor == 15:
                return MacOSVersion.CATALINA
            elif major == 11:
                return MacOSVersion.BIG_SUR
            elif major == 12:
                return MacOSVersion.MONTEREY
            elif major == 13:
                return MacOSVersion.VENTURA
            elif major == 14:
                return MacOSVersion.SONOMA
            else:
                return MacOSVersion.UNKNOWN
        except Exception as e:
            logger.error(f"Error detecting macOS version: {e}")
            return MacOSVersion.UNKNOWN
    
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
        logger.info("Initializing MacOSClient components...")
        
        try:
            # 初始化指标收集器
            self.metrics_collector = DesktopMetrics()
            self.metrics_collector.start_collection()
            
            # 初始化窗口管理器
            self.window_manager = WindowManager()
            
            # 初始化主题选择器
            self.theme_selector = ThemeSelector()
            
            # 初始化主窗口（使用macOS特定配置）
            self.main_window = MainWindow(
                title=self.config.window_title,
                width=self.config.initial_width,
                height=self.config.initial_height,
                min_width=self.config.min_width,
                min_height=self.config.min_height,
                use_vibrancy=self.config.use_vibrancy,
                titlebar_appearance=self.config.titlebar_appearance,
                traffic_lights_style=self.config.traffic_lights_style
            )
            
            # 设置窗口事件回调
            self.main_window.on_close = self._on_window_close
            self.main_window.on_minimize = self._on_window_minimize
            self.main_window.on_restore = self._on_window_restore
            self.main_window.on_resize = self._on_window_resize
            self.main_window.on_move = self._on_window_move
            self.main_window.on_fullscreen = self._on_window_fullscreen
            
            # 初始化Dock集成
            if self.config.enable_dock_integration:
                self.dock_integration = TaskbarIntegration(self.main_window)
                self.dock_integration.set_platform("macos")
                self.dock_integration.initialize()
                self._setup_dock_menu()
            
            # 初始化菜单栏图标
            if self.config.enable_menu_bar_icon:
                self.menu_bar_icon = SystemTray()
                self.menu_bar_icon.set_platform("macos")
                self.menu_bar_icon.on_show_window = self._on_menu_bar_show
                self.menu_bar_icon.on_hide_window = self._on_menu_bar_hide
                self.menu_bar_icon.on_exit = self._on_menu_bar_exit
                self.menu_bar_icon.initialize()
            
            # 初始化快捷键处理器
            self.shortcut_handler = ShortcutHandler()
            self._register_default_shortcuts()
            
            # 应用主题
            if self.theme_selector:
                current_theme = self.theme_selector.get_current_theme()
                self.apply_theme(current_theme)
            
            # macOS特定初始化
            if MACOS_SPECIFIC_AVAILABLE:
                self._init_macos_specific()
            
            # 设置自动启动
            if self.config.auto_start:
                self._set_auto_start(True)
            
            # 配置App Nap
            if MACOS_SPECIFIC_AVAILABLE and not self.config.enable_app_nap:
                self._disable_app_nap()
            
            logger.info("MacOSClient initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MacOSClient: {e}", exc_info=True)
            return False
    
    def _init_macos_specific(self):
        """执行macOS特定的初始化"""
        try:
            # 设置应用程序激活策略
            if MACOS_SPECIFIC_AVAILABLE:
                AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            
            # 注册到Services菜单
            if self.config.enable_services_menu:
                self._register_services()
            
            # 启用Handoff
            if self.config.enable_handoff:
                self._enable_handoff()
            
            logger.debug("macOS-specific initialization completed")
        except Exception as e:
            logger.error(f"Error in macOS-specific initialization: {e}")
    
    def _setup_dock_menu(self):
        """设置Dock菜单"""
        if not MACOS_SPECIFIC_AVAILABLE or not self.dock_integration:
            return
        
        try:
            dock_menu = AppKit.NSMenu.alloc().init()
            
            # 添加菜单项
            show_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "显示主窗口", "showWindow:", ""
            )
            show_item.setTarget_(self)
            dock_menu.addItem_(show_item)
            
            hide_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "隐藏主窗口", "hideWindow:", ""
            )
            hide_item.setTarget_(self)
            dock_menu.addItem_(hide_item)
            
            dock_menu.addItem_(AppKit.NSMenuItem.separatorItem())
            
            new_conversation_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "新对话", "newConversation:", "n"
            )
            new_conversation_item.setTarget_(self)
            dock_menu.addItem_(new_conversation_item)
            
            dock_menu.addItem_(AppKit.NSMenuItem.separatorItem())
            
            quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "退出", "terminate:", "q"
            )
            quit_item.setTarget_(self)
            dock_menu.addItem_(quit_item)
            
            # 设置Dock菜单
            AppKit.NSApp.setDockMenu_(dock_menu)
            
        except Exception as e:
            logger.error(f"Error setting up Dock menu: {e}")
    
    def _register_services(self):
        """注册到系统服务菜单"""
        if not MACOS_SPECIFIC_AVAILABLE:
            return
        
        try:
            # 创建服务提供者
            services_provider = Foundation.NSObject.alloc().init()
            
            # 注册服务选择器
            Foundation.NSRegisterServicesProvider(services_provider, "MirexsServices")
            
            # 定义服务
            services_plist = {
                "NSServices": [
                    {
                        "NSMessage": "processText",
                        "NSPortName": "Mirexs",
                        "NSMenuItem": {"default": "使用Mirexs处理文本"},
                        "NSReturnTypes": ["NSStringPboardType"],
                        "NSSendTypes": ["NSStringPboardType"]
                    },
                    {
                        "NSMessage": "speakText",
                        "NSPortName": "Mirexs",
                        "NSMenuItem": {"default": "用Mirexs朗读文本"},
                        "NSSendTypes": ["NSStringPboardType"]
                    }
                ]
            }
            
            # 写入服务注册plist
            services_path = os.path.expanduser("~/Library/Services/Mirexs.services")
            with open(services_path, 'wb') as f:
                plistlib.dump(services_plist, f)
            
            logger.info("Services registered successfully")
            
        except Exception as e:
            logger.error(f"Error registering services: {e}")
    
    def _enable_handoff(self):
        """启用Handoff功能"""
        if not MACOS_SPECIFIC_AVAILABLE:
            return
        
        try:
            # 设置user activity类型
            user_activity_type = "com.mirexs.activity"
            
            # 创建user activity
            self.user_activity = Foundation.NSUserActivity.alloc().initWithActivityType_(user_activity_type)
            self.user_activity.setTitle_("Mirexs Activity")
            self.user_activity.setEligibleForHandoff_(True)
            self.user_activity.setEligibleForSearch_(True)
            self.user_activity.setEligibleForPublicIndexing_(False)
            
            # 设置delegate
            # self.user_activity.setDelegate_(self)
            
            logger.info("Handoff enabled")
            
        except Exception as e:
            logger.error(f"Error enabling Handoff: {e}")
    
    def _disable_app_nap(self):
        """禁用App Nap"""
        if not MACOS_SPECIFIC_AVAILABLE:
            return
        
        try:
            # 通过NSProcessInfo设置
            process_info = Foundation.NSProcessInfo.processInfo()
            process_info.setAutomaticTerminationSupportEnabled_(False)
            
            # 禁用App Nap的另一种方式
            if hasattr(process_info, 'beginActivityWithOptions_reason_'):
                activity_id = process_info.beginActivityWithOptions_reason_(
                    0x00FFFFFF,  # NSActivityLatencyCritical | NSActivityUserInitiated
                    "Mirexs需要持续运行"
                )
                self.activity_id = activity_id
            
            logger.info("App Nap disabled")
            
        except Exception as e:
            logger.error(f"Error disabling App Nap: {e}")
    
    def _register_default_shortcuts(self):
        """注册默认快捷键（使用Command键）"""
        if not self.shortcut_handler:
            return
        
        shortcuts = [
            ("Cmd+Shift+M", "show_main_window", "显示主窗口"),
            ("Cmd+Shift+H", "hide_main_window", "隐藏主窗口"),
            ("Cmd+Q", "quit_application", "退出应用"),
            ("Cmd+Shift+T", "toggle_theme", "切换主题"),
            ("Cmd+Shift+S", "toggle_screenshot", "截屏"),
            ("Cmd+Shift+V", "toggle_voice_input", "切换语音输入"),
            ("Cmd+Shift+N", "new_conversation", "新对话"),
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
        elif action == "new_conversation":
            self._trigger_event("new_conversation")
    
    def _on_window_close(self):
        """窗口关闭事件回调"""
        logger.info("Window close event triggered")
        if self.config.start_in_menu_bar and self.menu_bar_icon:
            # 隐藏到菜单栏而不是退出
            self.hide_to_menu_bar()
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
    
    def _on_window_fullscreen(self, is_fullscreen: bool):
        """窗口全屏事件回调"""
        logger.debug(f"Window fullscreen changed: {is_fullscreen}")
        self._trigger_event("window_fullscreen", is_fullscreen)
    
    def _on_window_resize(self, width: int, height: int):
        """窗口大小改变事件回调"""
        logger.debug(f"Window resized to {width}x{height}")
        if self.metrics_collector:
            self.metrics_collector.record_window_resize(width, height)
    
    def _on_window_move(self, x: int, y: int):
        """窗口移动事件回调"""
        logger.debug(f"Window moved to ({x}, {y})")
    
    def _on_menu_bar_show(self):
        """菜单栏显示窗口回调"""
        self.show_window()
    
    def _on_menu_bar_hide(self):
        """菜单栏隐藏窗口回调"""
        self.hide_window()
    
    def _on_menu_bar_exit(self):
        """菜单栏退出回调"""
        self.shutdown()
    
    def _set_auto_start(self, enable: bool):
        """
        设置开机自动启动（通过LaunchAgents）
        
        Args:
            enable: 是否启用自动启动
        """
        try:
            launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(launch_agents_dir, exist_ok=True)
            
            plist_path = os.path.join(launch_agents_dir, "com.mirexs.client.plist")
            
            if enable:
                # 创建launchd plist
                plist_data = {
                    "Label": "com.mirexs.client",
                    "ProgramArguments": [sys.executable, "-m", "mirexs.launch.macos"],
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "StandardOutPath": os.path.expanduser("~/Library/Logs/Mirexs/out.log"),
                    "StandardErrorPath": os.path.expanduser("~/Library/Logs/Mirexs/err.log"),
                }
                
                # 创建日志目录
                os.makedirs(os.path.expanduser("~/Library/Logs/Mirexs"), exist_ok=True)
                
                with open(plist_path, 'wb') as f:
                    plistlib.dump(plist_data, f)
                
                # 加载launchd服务
                subprocess.run(["launchctl", "load", plist_path], check=False)
                logger.info("Auto start enabled")
            else:
                # 卸载launchd服务
                if os.path.exists(plist_path):
                    subprocess.run(["launchctl", "unload", plist_path], check=False)
                    os.remove(plist_path)
                logger.info("Auto start disabled")
                
        except Exception as e:
            logger.error(f"Error setting auto start: {e}")
    
    def show_window(self):
        """显示主窗口"""
        if self.main_window:
            self.main_window.show()
            self.is_in_menu_bar = False
            
            # 激活应用
            if MACOS_SPECIFIC_AVAILABLE:
                AppKit.NSApp.activateIgnoringOtherApps_(True)
            
            logger.info("Main window shown")
    
    def hide_window(self):
        """隐藏主窗口"""
        if self.main_window:
            self.main_window.hide()
            logger.info("Main window hidden")
    
    def hide_to_menu_bar(self):
        """隐藏到菜单栏"""
        self.hide_window()
        self.is_in_menu_bar = True
        if self.menu_bar_icon:
            self.menu_bar_icon.show_notification(
                "Mirexs 仍在运行",
                "应用程序已最小化到菜单栏"
            )
        logger.info("Application hidden to menu bar")
    
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
            if self.dock_integration:
                self.dock_integration.update_theme(theme)
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
            if self.config.start_minimized or self.config.start_in_menu_bar:
                if self.config.start_in_menu_bar:
                    self.hide_to_menu_bar()
                else:
                    self.hide_window()
            else:
                self.show_window()
            
            logger.info("MacOSClient started")
            
            # macOS应用通常需要启动NSApp
            if MACOS_SPECIFIC_AVAILABLE:
                AppKit.NSApp.run()
    
    def shutdown(self):
        """关闭客户端"""
        logger.info("Shutting down MacOSClient...")
        
        self.is_running = False
        
        # 保存配置
        self._save_config()
        
        # 清理资源
        if self.menu_bar_icon:
            self.menu_bar_icon.shutdown()
        
        if self.dock_integration:
            self.dock_integration.shutdown()
        
        if self.main_window:
            self.main_window.close()
        
        if self.metrics_collector:
            self.metrics_collector.stop_collection()
            report = self.metrics_collector.generate_report()
            logger.info(f"Desktop metrics report: {report}")
        
        logger.info("MacOSClient shutdown completed")
        self._trigger_event("shutdown")
        
        # 退出NSApp
        if MACOS_SPECIFIC_AVAILABLE:
            AppKit.NSApp.terminate_(None)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Returns:
            状态字典
        """
        return {
            "platform": self.platform,
            "macos_version": self.macos_version.value,
            "is_running": self.is_running,
            "is_minimized": self.is_minimized,
            "is_in_menu_bar": self.is_in_menu_bar,
            "background_mode": self.background_mode,
            "dock_behavior": self.dock_behavior.value,
            "main_window_visible": self.main_window.is_visible() if self.main_window else False,
            "config": self.config.__dict__,
            "metrics": self.metrics_collector.get_latest_metrics() if self.metrics_collector else {}
        }

# 单例模式实现
_macos_client_instance: Optional[MacOSClient] = None

def get_macos_client(config: Optional[MacOSClientConfig] = None) -> MacOSClient:
    """
    获取macOS客户端单例
    
    Args:
        config: 客户端配置
    
    Returns:
        macOS客户端实例
    """
    global _macos_client_instance
    if _macos_client_instance is None:
        _macos_client_instance = MacOSClient(config)
    return _macos_client_instance

def create_macos_client(config: Optional[MacOSClientConfig] = None) -> MacOSClient:
    """
    创建新的macOS客户端实例（非单例）
    
    Args:
        config: 客户端配置
    
    Returns:
        macOS客户端实例
    """
    return MacOSClient(config)

