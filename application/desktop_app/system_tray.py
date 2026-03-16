"""
系统托盘模块 - Mirexs桌面应用程序

提供系统托盘图标和菜单功能，支持：
1. 托盘图标显示和更新
2. 托盘菜单构建和事件处理
3. 托盘通知显示
4. 多平台适配（Windows、macOS、Linux）
5. 托盘图标动画和状态提示
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass
import threading
import time

# 尝试导入托盘库
try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logging.warning("pystray not available. System tray functionality will be limited.")

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    logging.warning("plyer not available. Notifications will be limited.")

logger = logging.getLogger(__name__)

class TrayIconState(Enum):
    """托盘图标状态枚举"""
    NORMAL = "normal"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    NOTIFICATION = "notification"
    ERROR = "error"

@dataclass
class TrayMenuItem:
    """托盘菜单项"""
    id: str
    text: str
    enabled: bool = True
    checked: bool = False
    icon: Optional[str] = None
    submenu: Optional[List['TrayMenuItem']] = None
    callback: Optional[Callable] = None

class SystemTray:
    """
    系统托盘类
    
    负责系统托盘的创建、管理和事件处理，支持多平台。
    """
    
    def __init__(self):
        """初始化系统托盘"""
        self.platform = sys.platform
        self.desktop_env = "unknown"
        self.is_initialized = False
        self.is_running = False
        
        # 托盘状态
        self.icon_state: TrayIconState = TrayIconState.NORMAL
        self.tooltip: str = "Mirexs - 弥尔思数字生命体"
        
        # 菜单项
        self.menu_items: Dict[str, TrayMenuItem] = {}
        self.menu_structure: List[str] = []  # 存储菜单项ID的顺序
        
        # 图标相关
        self.icon_image = None
        self.icon_animation_thread: Optional[threading.Thread] = None
        self.animation_running = False
        
        # 托盘实例
        self._tray_icon = None
        
        # 回调函数
        self.on_show_window: Optional[Callable] = None
        self.on_hide_window: Optional[Callable] = None
        self.on_exit: Optional[Callable] = None
        
        # 默认菜单项
        self._setup_default_menu()
        
        logger.info(f"SystemTray initialized for platform: {self.platform}")
    
    def _setup_default_menu(self):
        """设置默认菜单"""
        # 显示窗口
        self.add_menu_item(TrayMenuItem(
            id="show",
            text="显示窗口",
            callback=self._on_show_clicked
        ))
        
        # 隐藏窗口
        self.add_menu_item(TrayMenuItem(
            id="hide",
            text="隐藏窗口",
            callback=self._on_hide_clicked
        ))
        
        # 分隔线
        self.add_menu_item(TrayMenuItem(
            id="separator1",
            text="---",
            enabled=False
        ))
        
        # 设置
        self.add_menu_item(TrayMenuItem(
            id="settings",
            text="设置",
            callback=self._on_settings_clicked
        ))
        
        # 关于
        self.add_menu_item(TrayMenuItem(
            id="about",
            text="关于",
            callback=self._on_about_clicked
        ))
        
        # 分隔线
        self.add_menu_item(TrayMenuItem(
            id="separator2",
            text="---",
            enabled=False
        ))
        
        # 退出
        self.add_menu_item(TrayMenuItem(
            id="exit",
            text="退出",
            callback=self._on_exit_clicked
        ))
    
    def _on_show_clicked(self):
        """显示窗口菜单项点击回调"""
        if self.on_show_window:
            self.on_show_window()
    
    def _on_hide_clicked(self):
        """隐藏窗口菜单项点击回调"""
        if self.on_hide_window:
            self.on_hide_window()
    
    def _on_settings_clicked(self):
        """设置菜单项点击回调"""
        logger.info("Settings menu clicked")
        # 触发设置事件
        self._trigger_custom_event("settings")
    
    def _on_about_clicked(self):
        """关于菜单项点击回调"""
        logger.info("About menu clicked")
        self._trigger_custom_event("about")
    
    def _on_exit_clicked(self):
        """退出菜单项点击回调"""
        if self.on_exit:
            self.on_exit()
    
    def _trigger_custom_event(self, event: str):
        """触发自定义事件"""
        # 查找菜单项的回调
        for item_id, item in self.menu_items.items():
            if item.text == event or item_id == event:
                if item.callback:
                    item.callback()
                break
    
    def initialize(self) -> bool:
        """
        初始化系统托盘
        
        Returns:
            初始化是否成功
        """
        if self.is_initialized:
            return True
        
        logger.info("Initializing SystemTray...")
        
        try:
            if not PYSTRAY_AVAILABLE:
                logger.warning("pystray not available, using fallback implementation")
                self.is_initialized = True
                return True
            
            # 创建图标
            self._create_icon_image()
            
            # 创建菜单
            menu = self._build_menu()
            
            # 创建托盘图标
            self._tray_icon = pystray.Icon(
                "mirexs",
                self.icon_image,
                self.tooltip,
                menu
            )
            
            self.is_initialized = True
            logger.info("SystemTray initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing SystemTray: {e}")
            return False
    
    def _create_icon_image(self, size: int = 64):
        """
        创建托盘图标图像
        
        Args:
            size: 图标大小
        """
        try:
            # 创建默认图标
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # 根据平台和状态绘制不同图标
            if self.platform == "darwin":
                # macOS - 绘制猫咪图标
                self._draw_macos_icon(draw, size)
            elif self.platform == "win32":
                # Windows - 绘制猫咪图标
                self._draw_windows_icon(draw, size)
            else:
                # Linux和其他平台
                self._draw_linux_icon(draw, size)
            
            # 根据状态添加指示器
            self._draw_state_indicator(draw, size)
            
            self.icon_image = image
            
        except Exception as e:
            logger.error(f"Error creating icon image: {e}")
            # 创建纯色备用图标
            image = Image.new('RGBA', (size, size), (100, 100, 255, 255))
            self.icon_image = image
    
    def _draw_macos_icon(self, draw: ImageDraw, size: int):
        """绘制macOS风格图标"""
        # 绘制猫咪脸
        margin = size // 8
        body_color = (100, 100, 255, 255)  # 浅蓝色
        
        # 绘制圆形脸
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=body_color,
            outline=(255, 255, 255, 255),
            width=2
        )
        
        # 绘制耳朵
        ear_size = size // 4
        # 左耳
        draw.polygon(
            [(margin, margin),
             (margin + ear_size, margin - ear_size // 2),
             (margin + ear_size, margin)],
            fill=body_color
        )
        # 右耳
        draw.polygon(
            [(size - margin, margin),
             (size - margin - ear_size, margin - ear_size // 2),
             (size - margin - ear_size, margin)],
            fill=body_color
        )
        
        # 绘制眼睛
        eye_offset = size // 5
        eye_size = size // 10
        # 左眼
        draw.ellipse(
            [eye_offset, eye_offset,
             eye_offset + eye_size, eye_offset + eye_size],
            fill=(255, 255, 255, 255)
        )
        draw.ellipse(
            [eye_offset + eye_size//3, eye_offset + eye_size//3,
             eye_offset + eye_size*2//3, eye_offset + eye_size*2//3],
            fill=(0, 0, 0, 255)
        )
        # 右眼
        draw.ellipse(
            [size - eye_offset - eye_size, eye_offset,
             size - eye_offset, eye_offset + eye_size],
            fill=(255, 255, 255, 255)
        )
        draw.ellipse(
            [size - eye_offset - eye_size*2//3, eye_offset + eye_size//3,
             size - eye_offset - eye_size//3, eye_offset + eye_size*2//3],
            fill=(0, 0, 0, 255)
        )
        
        # 绘制鼻子
        nose_center = size // 2
        nose_size = size // 12
        draw.polygon(
            [(nose_center - nose_size, size//2 + nose_size),
             (nose_center + nose_size, size//2 + nose_size),
             (nose_center, size//2 - nose_size)],
            fill=(255, 150, 150, 255)
        )
    
    def _draw_windows_icon(self, draw: ImageDraw, size: int):
        """绘制Windows风格图标"""
        # 类似macOS但更简洁
        self._draw_macos_icon(draw, size)
    
    def _draw_linux_icon(self, draw: ImageDraw, size: int):
        """绘制Linux风格图标"""
        # 类似macOS但使用系统主题色
        self._draw_macos_icon(draw, size)
    
    def _draw_state_indicator(self, draw: ImageDraw, size: int):
        """绘制状态指示器"""
        indicator_size = size // 8
        indicator_pos = (size - indicator_size * 2, size - indicator_size * 2)
        
        if self.icon_state == TrayIconState.ACTIVE:
            color = (0, 255, 0, 255)  # 绿色
        elif self.icon_state == TrayIconState.BUSY:
            color = (255, 165, 0, 255)  # 橙色
        elif self.icon_state == TrayIconState.NOTIFICATION:
            color = (255, 255, 0, 255)  # 黄色
        elif self.icon_state == TrayIconState.ERROR:
            color = (255, 0, 0, 255)  # 红色
        else:
            return  # 不显示指示器
        
        draw.ellipse(
            [indicator_pos[0], indicator_pos[1],
             indicator_pos[0] + indicator_size, indicator_pos[1] + indicator_size],
            fill=color
        )
    
    def _build_menu(self):
        """构建托盘菜单"""
        if not PYSTRAY_AVAILABLE:
            return None
        
        menu_items = []
        
        for item_id in self.menu_structure:
            item = self.menu_items.get(item_id)
            if not item:
                continue
            
            if item.text == "---":
                # 分隔线
                menu_items.append(pystray.Menu.SEPARATOR)
            elif item.submenu:
                # 子菜单
                sub_items = []
                for sub_item in item.submenu:
                    sub_items.append(
                        pystray.MenuItem(
                            sub_item.text,
                            lambda: sub_item.callback() if sub_item.callback else None,
                            enabled=sub_item.enabled,
                            checked=lambda: sub_item.checked
                        )
                    )
                menu_items.append(
                    pystray.MenuItem(
                        item.text,
                        pystray.Menu(*sub_items),
                        enabled=item.enabled
                    )
                )
            else:
                # 普通菜单项
                menu_items.append(
                    pystray.MenuItem(
                        item.text,
                        lambda: item.callback() if item.callback else None,
                        enabled=item.enabled,
                        checked=lambda: item.checked if hasattr(item, 'checked') else False
                    )
                )
        
        return pystray.Menu(*menu_items)
    
    def run(self):
        """运行系统托盘（阻塞）"""
        if not self.is_initialized:
            self.initialize()
        
        if not PYSTRAY_AVAILABLE or not self._tray_icon:
            logger.warning("Cannot run system tray: pystray not available")
            return
        
        self.is_running = True
        logger.info("SystemTray running")
        
        # 运行托盘图标（阻塞）
        self._tray_icon.run()
    
    def run_in_thread(self) -> Optional[threading.Thread]:
        """
        在后台线程中运行系统托盘
        
        Returns:
            托盘线程
        """
        if not self.is_initialized:
            self.initialize()
        
        if not PYSTRAY_AVAILABLE or not self._tray_icon:
            logger.warning("Cannot run system tray: pystray not available")
            return None
        
        def run_tray():
            self._tray_icon.run()
        
        thread = threading.Thread(target=run_tray, daemon=True)
        thread.start()
        
        self.is_running = True
        logger.info("SystemTray running in background thread")
        
        return thread
    
    def stop(self):
        """停止系统托盘"""
        if PYSTRAY_AVAILABLE and self._tray_icon:
            self._tray_icon.stop()
        
        self.is_running = False
        logger.info("SystemTray stopped")
    
    def update_icon(self, state: Optional[TrayIconState] = None, tooltip: Optional[str] = None):
        """
        更新托盘图标
        
        Args:
            state: 新的图标状态
            tooltip: 新的工具提示
        """
        if state:
            self.icon_state = state
        
        if tooltip:
            self.tooltip = tooltip
        
        # 重新创建图标图像
        self._create_icon_image()
        
        if PYSTRAY_AVAILABLE and self._tray_icon:
            self._tray_icon.icon = self.icon_image
            self._tray_icon.title = self.tooltip
    
    def show_notification(self, title: str, message: str, timeout: int = 5):
        """
        显示系统通知
        
        Args:
            title: 通知标题
            message: 通知内容
            timeout: 显示时间（秒）
        """
        logger.info(f"Notification: {title} - {message}")
        
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Mirexs",
                    timeout=timeout
                )
            except Exception as e:
                logger.error(f"Error showing notification: {e}")
        else:
            # 回退：打印到控制台
            print(f"\n[{title}] {message}\n")
        
        # 同时闪烁托盘图标
        self.flash_icon()
    
    def flash_icon(self, duration: float = 1.0, interval: float = 0.5):
        """
        闪烁托盘图标
        
        Args:
            duration: 闪烁持续时间
            interval: 闪烁间隔
        """
        if self.animation_running:
            return
        
        def animate():
            self.animation_running = True
            original_state = self.icon_state
            end_time = time.time() + duration
            
            while time.time() < end_time:
                self.update_icon(TrayIconState.NOTIFICATION)
                time.sleep(interval)
                self.update_icon(original_state)
                time.sleep(interval)
            
            self.animation_running = False
        
        thread = threading.Thread(target=animate, daemon=True)
        thread.start()
    
    def add_menu_item(self, item: TrayMenuItem, position: Optional[int] = None):
        """
        添加菜单项
        
        Args:
            item: 菜单项
            position: 插入位置（None表示追加）
        """
        self.menu_items[item.id] = item
        
        if position is None:
            self.menu_structure.append(item.id)
        else:
            self.menu_structure.insert(position, item.id)
        
        # 重新构建菜单
        if PYSTRAY_AVAILABLE and self._tray_icon:
            self._tray_icon.menu = self._build_menu()
    
    def remove_menu_item(self, item_id: str):
        """
        移除菜单项
        
        Args:
            item_id: 菜单项ID
        """
        if item_id in self.menu_items:
            del self.menu_items[item_id]
        
        if item_id in self.menu_structure:
            self.menu_structure.remove(item_id)
        
        # 重新构建菜单
        if PYSTRAY_AVAILABLE and self._tray_icon:
            self._tray_icon.menu = self._build_menu()
    
    def update_menu_item(self, item_id: str, **kwargs):
        """
        更新菜单项属性
        
        Args:
            item_id: 菜单项ID
            **kwargs: 要更新的属性
        """
        if item_id in self.menu_items:
            item = self.menu_items[item_id]
            for key, value in kwargs.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            # 重新构建菜单
            if PYSTRAY_AVAILABLE and self._tray_icon:
                self._tray_icon.menu = self._build_menu()
    
    def set_platform(self, platform: str):
        """设置平台"""
        self.platform = platform
    
    def set_desktop_environment(self, desktop_env: str):
        """设置桌面环境（Linux）"""
        self.desktop_env = desktop_env
    
    def shutdown(self):
        """关闭系统托盘"""
        logger.info("Shutting down SystemTray...")
        
        self.stop()
        self.is_initialized = False
        
        logger.info("SystemTray shutdown completed")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取系统托盘状态
        
        Returns:
            状态字典
        """
        return {
            "platform": self.platform,
            "desktop_env": self.desktop_env,
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "icon_state": self.icon_state.value,
            "tooltip": self.tooltip,
            "menu_items": len(self.menu_items)
        }

