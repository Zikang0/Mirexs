"""
窗口管理模块 - Mirexs桌面应用程序

提供窗口管理功能，包括：
1. 多窗口创建和管理
2. 窗口布局和排列
3. 窗口状态持久化
4. 窗口间通信
5. 窗口焦点管理
"""

import os
import sys
import logging
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class WindowType(Enum):
    """窗口类型枚举"""
    MAIN = "main"
    SETTINGS = "settings"
    CHAT = "chat"
    TASK = "task"
    CREATIVE = "creative"
    HELP = "help"
    ABOUT = "about"
    CUSTOM = "custom"

class WindowLayout(Enum):
    """窗口布局枚举"""
    CASCADE = "cascade"  # 层叠
    TILE = "tile"        # 平铺
    GRID = "grid"        # 网格
    FULLSCREEN = "fullscreen"  # 全屏
    MAXIMIZED = "maximized"    # 最大化

@dataclass
class WindowInfo:
    """窗口信息"""
    id: str
    type: WindowType
    title: str
    x: int = 100
    y: int = 100
    width: int = 800
    height: int = 600
    minimized: bool = False
    maximized: bool = False
    fullscreen: bool = False
    visible: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WindowManagerConfig:
    """窗口管理器配置"""
    save_layout: bool = True
    restore_on_start: bool = True
    auto_tile_threshold: int = 3  # 自动平铺的窗口数量阈值
    cascade_offset: int = 30  # 层叠偏移量
    config_file: str = "window_layout.json"
    data_dir: str = "data/window_manager/"

class WindowManager:
    """
    窗口管理器类
    
    负责管理应用程序的所有窗口，提供窗口创建、销毁、布局等功能。
    """
    
    def __init__(self, config: Optional[WindowManagerConfig] = None):
        """
        初始化窗口管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config or WindowManagerConfig()
        
        # 窗口存储
        self.windows: Dict[str, WindowInfo] = {}
        self.window_instances: Dict[str, Any] = {}  # 存储实际窗口对象
        
        # 主窗口ID
        self.main_window_id: Optional[str] = None
        
        # 当前活动窗口
        self.active_window_id: Optional[str] = None
        
        # 布局设置
        self.current_layout: WindowLayout = WindowLayout.CASCADE
        
        # 回调函数
        self.on_window_created: Optional[Callable[[str], None]] = None
        self.on_window_closed: Optional[Callable[[str], None]] = None
        self.on_window_activated: Optional[Callable[[str], None]] = None
        self.on_layout_changed: Optional[Callable[[WindowLayout], None]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        logger.info("WindowManager initialized")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_layout(self):
        """从文件加载窗口布局"""
        layout_path = os.path.join(self.config.data_dir, self.config.config_file)
        if os.path.exists(layout_path):
            try:
                with open(layout_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 恢复窗口信息
                    for win_data in data.get("windows", []):
                        win_data["created_at"] = datetime.fromisoformat(win_data["created_at"])
                        win_data["last_active"] = datetime.fromisoformat(win_data["last_active"])
                        win_data["type"] = WindowType(win_data["type"])
                        
                        window_info = WindowInfo(**win_data)
                        self.windows[window_info.id] = window_info
                    
                    # 恢复布局
                    layout_name = data.get("layout", "cascade")
                    self.current_layout = WindowLayout(layout_name)
                    
                    # 恢复主窗口ID
                    self.main_window_id = data.get("main_window_id")
                    
                logger.info(f"Window layout loaded from {layout_path}")
            except Exception as e:
                logger.error(f"Error loading window layout: {e}")
    
    def _save_layout(self):
        """保存窗口布局到文件"""
        if not self.config.save_layout:
            return
        
        layout_path = os.path.join(self.config.data_dir, self.config.config_file)
        try:
            data = {
                "windows": [],
                "layout": self.current_layout.value,
                "main_window_id": self.main_window_id,
                "saved_at": datetime.now().isoformat()
            }
            
            for win_id, win_info in self.windows.items():
                win_data = {
                    "id": win_info.id,
                    "type": win_info.type.value,
                    "title": win_info.title,
                    "x": win_info.x,
                    "y": win_info.y,
                    "width": win_info.width,
                    "height": win_info.height,
                    "minimized": win_info.minimized,
                    "maximized": win_info.maximized,
                    "fullscreen": win_info.fullscreen,
                    "visible": win_info.visible,
                    "created_at": win_info.created_at.isoformat(),
                    "last_active": win_info.last_active.isoformat(),
                    "data": win_info.data
                }
                data["windows"].append(win_data)
            
            with open(layout_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Window layout saved to {layout_path}")
            
        except Exception as e:
            logger.error(f"Error saving window layout: {e}")
    
    def create_window(self, window_type: WindowType, title: str, 
                     width: int = 800, height: int = 600,
                     data: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新窗口
        
        Args:
            window_type: 窗口类型
            title: 窗口标题
            width: 窗口宽度
            height: 窗口高度
            data: 附加数据
        
        Returns:
            窗口ID
        """
        window_id = str(uuid.uuid4())
        
        # 计算窗口位置（层叠）
        x, y = self._calculate_window_position()
        
        window_info = WindowInfo(
            id=window_id,
            type=window_type,
            title=title,
            x=x,
            y=y,
            width=width,
            height=height,
            data=data or {}
        )
        
        self.windows[window_id] = window_info
        
        # 如果是第一个窗口，设为主窗口
        if len(self.windows) == 1:
            self.main_window_id = window_id
        
        logger.info(f"Window created: {window_id} ({window_type.value})")
        
        if self.on_window_created:
            self.on_window_created(window_id)
        
        return window_id
    
    def register_window_instance(self, window_id: str, instance: Any):
        """
        注册窗口实例
        
        Args:
            window_id: 窗口ID
            instance: 窗口实例对象
        """
        if window_id in self.windows:
            self.window_instances[window_id] = instance
            logger.debug(f"Window instance registered: {window_id}")
    
    def close_window(self, window_id: str):
        """
        关闭窗口
        
        Args:
            window_id: 窗口ID
        """
        if window_id not in self.windows:
            logger.warning(f"Window not found: {window_id}")
            return
        
        # 关闭实际窗口
        if window_id in self.window_instances:
            instance = self.window_instances[window_id]
            if hasattr(instance, 'close'):
                instance.close()
            del self.window_instances[window_id]
        
        # 从记录中移除
        del self.windows[window_id]
        
        # 如果是主窗口，更新主窗口ID
        if window_id == self.main_window_id:
            if self.windows:
                self.main_window_id = next(iter(self.windows.keys()))
            else:
                self.main_window_id = None
        
        logger.info(f"Window closed: {window_id}")
        
        if self.on_window_closed:
            self.on_window_closed(window_id)
    
    def get_window(self, window_id: str) -> Optional[WindowInfo]:
        """
        获取窗口信息
        
        Args:
            window_id: 窗口ID
        
        Returns:
            窗口信息
        """
        return self.windows.get(window_id)
    
    def get_window_instance(self, window_id: str) -> Optional[Any]:
        """
        获取窗口实例
        
        Args:
            window_id: 窗口ID
        
        Returns:
            窗口实例
        """
        return self.window_instances.get(window_id)
    
    def get_windows_by_type(self, window_type: WindowType) -> List[str]:
        """
        获取指定类型的所有窗口ID
        
        Args:
            window_type: 窗口类型
        
        Returns:
            窗口ID列表
        """
        return [
            win_id for win_id, win_info in self.windows.items()
            if win_info.type == window_type
        ]
    
    def activate_window(self, window_id: str):
        """
        激活窗口
        
        Args:
            window_id: 窗口ID
        """
        if window_id not in self.windows:
            logger.warning(f"Window not found: {window_id}")
            return
        
        # 更新活动时间
        self.windows[window_id].last_active = datetime.now()
        
        # 激活实际窗口
        if window_id in self.window_instances:
            instance = self.window_instances[window_id]
            if hasattr(instance, 'activate'):
                instance.activate()
            elif hasattr(instance, 'raise_'):
                instance.raise_()
            elif hasattr(instance, 'show'):
                instance.show()
        
        old_active = self.active_window_id
        self.active_window_id = window_id
        
        logger.debug(f"Window activated: {window_id}")
        
        if self.on_window_activated and old_active != window_id:
            self.on_window_activated(window_id)
    
    def update_window_info(self, window_id: str, **kwargs):
        """
        更新窗口信息
        
        Args:
            window_id: 窗口ID
            **kwargs: 要更新的字段
        """
        if window_id not in self.windows:
            logger.warning(f"Window not found: {window_id}")
            return
        
        window_info = self.windows[window_id]
        for key, value in kwargs.items():
            if hasattr(window_info, key):
                setattr(window_info, key, value)
        
        # 更新活动时间
        window_info.last_active = datetime.now()
        
        logger.debug(f"Window info updated: {window_id}")
    
    def _calculate_window_position(self) -> tuple[int, int]:
        """计算新窗口位置（层叠）"""
        if not self.windows:
            return 100, 100
        
        # 基于最后一个窗口计算偏移
        last_window = list(self.windows.values())[-1]
        x = last_window.x + self.config.cascade_offset
        y = last_window.y + self.config.cascade_offset
        
        # 防止跑出屏幕
        if x > 400:
            x = 100
        if y > 300:
            y = 100
        
        return x, y
    
    def arrange_windows(self, layout: Optional[WindowLayout] = None):
        """
        排列窗口
        
        Args:
            layout: 布局类型，None表示使用当前布局
        """
        if layout:
            self.current_layout = layout
        
        if not self.windows:
            return
        
        if self.current_layout == WindowLayout.CASCADE:
            self._arrange_cascade()
        elif self.current_layout == WindowLayout.TILE:
            self._arrange_tile()
        elif self.current_layout == WindowLayout.GRID:
            self._arrange_grid()
        elif self.current_layout == WindowLayout.FULLSCREEN:
            self._arrange_fullscreen()
        elif self.current_layout == WindowLayout.MAXIMIZED:
            self._arrange_maximized()
        
        if self.on_layout_changed:
            self.on_layout_changed(self.current_layout)
    
    def _arrange_cascade(self):
        """层叠排列"""
        x, y = 50, 50
        for win_id, win_info in self.windows.items():
            if not win_info.minimized and win_info.visible:
                win_info.x = x
                win_info.y = y
                
                # 更新实际窗口
                if win_id in self.window_instances:
                    instance = self.window_instances[win_id]
                    if hasattr(instance, 'move'):
                        instance.move(x, y)
                
                x += self.config.cascade_offset
                y += self.config.cascade_offset
    
    def _arrange_tile(self):
        """平铺排列"""
        visible_windows = [
            (win_id, win_info) for win_id, win_info in self.windows.items()
            if not win_info.minimized and win_info.visible
        ]
        
        if not visible_windows:
            return
        
        # 获取屏幕尺寸（简化处理）
        screen_width = 1920
        screen_height = 1080
        
        count = len(visible_windows)
        cols = int(count ** 0.5)
        rows = (count + cols - 1) // cols
        
        tile_width = screen_width // cols
        tile_height = screen_height // rows
        
        for i, (win_id, win_info) in enumerate(visible_windows):
            col = i % cols
            row = i // cols
            
            win_info.x = col * tile_width
            win_info.y = row * tile_height
            win_info.width = tile_width
            win_info.height = tile_height
            
            # 更新实际窗口
            if win_id in self.window_instances:
                instance = self.window_instances[win_id]
                if hasattr(instance, 'setGeometry'):
                    instance.setGeometry(win_info.x, win_info.y, 
                                        win_info.width, win_info.height)
    
    def _arrange_grid(self):
        """网格排列"""
        # 类似平铺但保持固定大小
        self._arrange_tile()
    
    def _arrange_fullscreen(self):
        """全屏排列"""
        for win_id, win_info in self.windows.items():
            if win_id == self.active_window_id:
                # 活动窗口全屏
                win_info.fullscreen = True
                # 更新实际窗口
                if win_id in self.window_instances:
                    instance = self.window_instances[win_id]
                    if hasattr(instance, 'showFullScreen'):
                        instance.showFullScreen()
            else:
                # 其他窗口隐藏或最小化
                if win_id in self.window_instances:
                    instance = self.window_instances[win_id]
                    if hasattr(instance, 'hide'):
                        instance.hide()
    
    def _arrange_maximized(self):
        """最大化排列"""
        for win_id, win_info in self.windows.items():
            win_info.maximized = True
            # 更新实际窗口
            if win_id in self.window_instances:
                instance = self.window_instances[win_id]
                if hasattr(instance, 'showMaximized'):
                    instance.showMaximized()
    
    def minimize_all(self):
        """最小化所有窗口"""
        for win_id, win_info in self.windows.items():
            win_info.minimized = True
            if win_id in self.window_instances:
                instance = self.window_instances[win_id]
                if hasattr(instance, 'showMinimized'):
                    instance.showMinimized()
    
    def restore_all(self):
        """恢复所有窗口"""
        for win_id, win_info in self.windows.items():
            win_info.minimized = False
            win_info.maximized = False
            win_info.fullscreen = False
            if win_id in self.window_instances:
                instance = self.window_instances[win_id]
                if hasattr(instance, 'showNormal'):
                    instance.showNormal()
    
    def send_message(self, from_window: str, to_window: str, message: Any):
        """
        窗口间发送消息
        
        Args:
            from_window: 源窗口ID
            to_window: 目标窗口ID
            message: 消息内容
        """
        if to_window not in self.window_instances:
            logger.warning(f"Target window not found: {to_window}")
            return
        
        instance = self.window_instances[to_window]
        if hasattr(instance, 'handle_message'):
            instance.handle_message(from_window, message)
        
        logger.debug(f"Message sent from {from_window} to {to_window}")
    
    def broadcast_message(self, from_window: str, message: Any, 
                         exclude_self: bool = True):
        """
        广播消息给所有窗口
        
        Args:
            from_window: 源窗口ID
            message: 消息内容
            exclude_self: 是否排除源窗口
        """
        for win_id, instance in self.window_instances.items():
            if exclude_self and win_id == from_window:
                continue
            
            if hasattr(instance, 'handle_message'):
                instance.handle_message(from_window, message)
        
        logger.debug(f"Message broadcast from {from_window}")
    
    def get_all_windows(self) -> List[Dict[str, Any]]:
        """
        获取所有窗口信息
        
        Returns:
            窗口信息列表
        """
        return [
            {
                "id": win_id,
                "info": win_info.__dict__,
                "has_instance": win_id in self.window_instances
            }
            for win_id, win_info in self.windows.items()
        ]
    
    def shutdown(self):
        """关闭窗口管理器"""
        logger.info("Shutting down WindowManager...")
        
        # 保存布局
        self._save_layout()
        
        # 关闭所有窗口
        for win_id in list(self.windows.keys()):
            self.close_window(win_id)
        
        logger.info("WindowManager shutdown completed")

