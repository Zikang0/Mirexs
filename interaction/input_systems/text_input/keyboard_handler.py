"""
键盘处理模块：处理键盘输入事件，支持跨平台键盘事件监听和映射
"""

import threading
import time
import json
from enum import Enum
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
import logging

# 根据平台导入相应的键盘库
import sys
if sys.platform == 'win32':
    import pyWinhook as hook_manager
    import pythoncom
elif sys.platform == 'darwin':
    import Quartz
    import Cocoa
    from AppKit import NSEvent
elif sys.platform.startswith('linux'):
    import Xlib
    from Xlib import display, X
    import xinput

from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager

logger = logging.getLogger(__name__)


class KeyEventType(Enum):
    """键盘事件类型枚举"""
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    KEY_PRESS = "key_press"
    KEY_HOLD = "key_hold"


@dataclass
class KeyEvent:
    """键盘事件数据类"""
    event_type: KeyEventType
    key_code: int
    scan_code: int
    key_name: str
    modifiers: List[str]
    timestamp: float
    window_info: Optional[Dict[str, Any]] = None
    unicode_char: Optional[str] = None
    is_repeated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_type": self.event_type.value,
            "key_code": self.key_code,
            "scan_code": self.scan_code,
            "key_name": self.key_name,
            "modifiers": self.modifiers,
            "timestamp": self.timestamp,
            "window_info": self.window_info,
            "unicode_char": self.unicode_char,
            "is_repeated": self.is_repeated
        }


class KeyboardHandler:
    """键盘处理器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化键盘处理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        self.is_running = False
        self.hook_thread = None
        self.key_handlers = []
        self.keyboard_layout = "us"  # 默认美式键盘
        self.modifier_keys = {
            'ctrl': False,
            'shift': False,
            'alt': False,
            'win': False,
            'cmd': False,
            'option': False
        }
        
        # 加载配置
        self.load_config()
        
        # 键码映射表
        self.key_mappings = self.load_key_mappings()
        
        # 事件缓冲区
        self.event_buffer = []
        self.buffer_lock = threading.Lock()
        
        # 宏记录相关
        self.is_recording_macro = False
        self.macro_sequence = []
        
        logger.info("KeyboardHandler initialized")
    
    def load_config(self) -> None:
        """加载键盘配置"""
        try:
            config = self.config_manager.get_config("input_config")
            self.keyboard_layout = config.get("keyboard_layout", "us")
            self.enable_key_logging = config.get("enable_key_logging", False)
            self.enable_macro_recording = config.get("enable_macro_recording", True)
            
            # 加载快捷键配置
            shortcuts_config = self.config_manager.get_config("shortcuts")
            self.system_shortcuts = shortcuts_config.get("system_shortcuts", {})
            
            logger.debug(f"Keyboard config loaded: layout={self.keyboard_layout}")
        except Exception as e:
            logger.error(f"Failed to load keyboard config: {e}")
    
    def load_key_mappings(self) -> Dict[str, str]:
        """加载键码映射表"""
        mappings = {}
        
        # 加载键盘布局映射文件
        try:
            layout_file = f"config/keyboard_layouts/{self.keyboard_layout}.json"
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
                mappings = layout_data.get("mappings", {})
        except FileNotFoundError:
            logger.warning(f"Keyboard layout file for {self.keyboard_layout} not found, using default")
            # 使用默认美式布局
            mappings = self._get_default_key_mappings()
        except Exception as e:
            logger.error(f"Failed to load key mappings: {e}")
            mappings = self._get_default_key_mappings()
        
        return mappings
    
    def _get_default_key_mappings(self) -> Dict[str, str]:
        """获取默认键码映射"""
        return {
            "8": "backspace",
            "9": "tab",
            "13": "enter",
            "16": "shift",
            "17": "ctrl",
            "18": "alt",
            "20": "capslock",
            "27": "esc",
            "32": "space",
            "37": "left",
            "38": "up",
            "39": "right",
            "40": "down",
            "46": "delete",
            "91": "win",
            "93": "menu",
            "112": "f1",
            "113": "f2",
            "114": "f3",
            "115": "f4",
            "116": "f5",
            "117": "f6",
            "118": "f7",
            "119": "f8",
            "120": "f9",
            "121": "f10",
            "122": "f11",
            "123": "f12",
            "144": "numlock",
            "145": "scrolllock",
        }
    
    def start_listening(self) -> bool:
        """
        开始监听键盘事件
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_running:
            logger.warning("Keyboard listener is already running")
            return False
        
        try:
            self.is_running = True
            self.hook_thread = threading.Thread(
                target=self._keyboard_listener,
                daemon=True,
                name="KeyboardListener"
            )
            self.hook_thread.start()
            
            # 注册消息处理器
            self.message_bus.subscribe("keyboard_event", self._handle_keyboard_message)
            
            logger.info("Keyboard listener started")
            return True
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
            self.is_running = False
            return False
    
    def stop_listening(self) -> None:
        """停止监听键盘事件"""
        self.is_running = False
        if self.hook_thread:
            self.hook_thread.join(timeout=2.0)
        self.message_bus.unsubscribe("keyboard_event", self._handle_keyboard_message)
        logger.info("Keyboard listener stopped")
    
    def _keyboard_listener(self) -> None:
        """键盘监听线程"""
        if sys.platform == 'win32':
            self._windows_keyboard_listener()
        elif sys.platform == 'darwin':
            self._macos_keyboard_listener()
        elif sys.platform.startswith('linux'):
            self._linux_keyboard_listener()
    
    def _windows_keyboard_listener(self) -> None:
        """Windows平台键盘监听"""
        def on_keyboard_event(event):
            """键盘事件回调"""
            if not self.is_running:
                return False
            
            try:
                # 解析事件
                key_event = self._parse_windows_event(event)
                if key_event:
                    # 处理事件
                    self._process_key_event(key_event)
                    
                    # 检查系统快捷键
                    if self._check_system_shortcut(key_event):
                        return False  # 阻止事件传播
            except Exception as e:
                logger.error(f"Error processing keyboard event: {e}")
            
            return True
        
        try:
            # 创建钩子管理器
            hm = hook_manager.HookManager()
            hm.KeyDown = on_keyboard_event
            hm.KeyUp = on_keyboard_event
            hm.HookKeyboard()
            
            # 运行消息循环
            while self.is_running:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.01)
            
            # 卸载钩子
            hm.UnhookKeyboard()
        except Exception as e:
            logger.error(f"Windows keyboard listener error: {e}")
    
    def _macos_keyboard_listener(self) -> None:
        """macOS平台键盘监听"""
        logger.warning("macOS keyboard listener not implemented yet")
        # TODO: 实现macOS键盘监听
    
    def _linux_keyboard_listener(self) -> None:
        """Linux平台键盘监听"""
        logger.warning("Linux keyboard listener not implemented yet")
        # TODO: 实现Linux键盘监听
    
    def _parse_windows_event(self, event) -> Optional[KeyEvent]:
        """解析Windows键盘事件"""
        try:
            # 获取事件类型
            event_type = KeyEventType.KEY_DOWN if event.MessageName == 'key down' else KeyEventType.KEY_UP
            
            # 获取键码和扫描码
            key_code = event.KeyID
            scan_code = event.ScanCode
            
            # 获取键名
            key_name = self.key_mappings.get(str(key_code), f"key_{key_code}")
            
            # 获取修饰键状态
            modifiers = []
            if event.Alt:
                modifiers.append("alt")
            if event.Ctrl:
                modifiers.append("ctrl")
            if event.Shift:
                modifiers.append("shift")
            
            # 获取窗口信息
            window_info = {
                "window_handle": event.Window,
                "window_name": event.WindowName
            }
            
            # 创建键盘事件
            key_event = KeyEvent(
                event_type=event_type,
                key_code=key_code,
                scan_code=scan_code,
                key_name=key_name,
                modifiers=modifiers,
                timestamp=time.time(),
                window_info=window_info,
                is_repeated=event.IsExtended
            )
            
            return key_event
        except Exception as e:
            logger.error(f"Failed to parse Windows event: {e}")
            return None
    
    def _process_key_event(self, key_event: KeyEvent) -> None:
        """处理键盘事件"""
        # 更新修饰键状态
        self._update_modifier_state(key_event)
        
        # 记录到缓冲区
        with self.buffer_lock:
            self.event_buffer.append(key_event)
            # 限制缓冲区大小
            if len(self.event_buffer) > 1000:
                self.event_buffer = self.event_buffer[-500:]
        
        # 处理宏录制
        if self.is_recording_macro and self.enable_macro_recording:
            self.macro_sequence.append(key_event)
        
        # 发布到消息总线
        self.message_bus.publish("keyboard_event", key_event.to_dict())
        
        # 触发注册的回调函数
        for handler in self.key_handlers:
            try:
                handler(key_event)
            except Exception as e:
                logger.error(f"Error in key handler: {e}")
        
        # 记录日志（如果启用）
        if self.enable_key_logging:
            self._log_key_event(key_event)
    
    def _update_modifier_state(self, key_event: KeyEvent) -> None:
        """更新修饰键状态"""
        key_name = key_event.key_name.lower()
        
        if key_event.event_type == KeyEventType.KEY_DOWN:
            if key_name in ['ctrl', 'control']:
                self.modifier_keys['ctrl'] = True
            elif key_name == 'shift':
                self.modifier_keys['shift'] = True
            elif key_name == 'alt':
                self.modifier_keys['alt'] = True
            elif key_name in ['win', 'cmd']:
                self.modifier_keys['win'] = True
        elif key_event.event_type == KeyEventType.KEY_UP:
            if key_name in ['ctrl', 'control']:
                self.modifier_keys['ctrl'] = False
            elif key_name == 'shift':
                self.modifier_keys['shift'] = False
            elif key_name == 'alt':
                self.modifier_keys['alt'] = False
            elif key_name in ['win', 'cmd']:
                self.modifier_keys['win'] = False
    
    def _check_system_shortcut(self, key_event: KeyEvent) -> bool:
        """检查系统快捷键"""
        if key_event.event_type != KeyEventType.KEY_DOWN:
            return False
        
        # 构建快捷键字符串
        shortcut_parts = []
        if self.modifier_keys['ctrl']:
            shortcut_parts.append("ctrl")
        if self.modifier_keys['alt']:
            shortcut_parts.append("alt")
        if self.modifier_keys['shift']:
            shortcut_parts.append("shift")
        if self.modifier_keys['win']:
            shortcut_parts.append("win")
        
        shortcut_parts.append(key_event.key_name.lower())
        shortcut = "+".join(shortcut_parts)
        
        # 检查是否是系统快捷键
        if shortcut in self.system_shortcuts:
            action = self.system_shortcuts[shortcut]
            self._execute_system_action(action)
            return True
        
        return False
    
    def _execute_system_action(self, action: str) -> None:
        """执行系统动作"""
        logger.info(f"Executing system action: {action}")
        
        # 发布系统动作消息
        self.message_bus.publish("system_action", {
            "action": action,
            "timestamp": time.time()
        })
    
    def _handle_keyboard_message(self, message: Dict[str, Any]) -> None:
        """处理键盘相关消息"""
        action = message.get("action")
        
        if action == "start_macro_recording":
            self.start_macro_recording()
        elif action == "stop_macro_recording":
            self.stop_macro_recording()
        elif action == "execute_macro":
            macro_name = message.get("macro_name")
            self.execute_macro(macro_name)
    
    def _log_key_event(self, key_event: KeyEvent) -> None:
        """记录键盘事件日志"""
        log_entry = {
            "timestamp": key_event.timestamp,
            "event": key_event.event_type.value,
            "key": key_event.key_name,
            "modifiers": key_event.modifiers,
            "window": key_event.window_info.get("window_name", "unknown") if key_event.window_info else "unknown"
        }
        
        # 将日志发送到日志系统
        self.message_bus.publish("log_entry", {
            "level": "INFO",
            "source": "keyboard_handler",
            "message": "Key event",
            "data": log_entry
        })
    
    def register_key_handler(self, handler: Callable[[KeyEvent], None]) -> None:
        """
        注册键盘事件处理器
        
        Args:
            handler: 事件处理函数
        """
        self.key_handlers.append(handler)
        logger.debug(f"Registered key handler: {handler.__name__}")
    
    def unregister_key_handler(self, handler: Callable[[KeyEvent], None]) -> None:
        """
        注销键盘事件处理器
        
        Args:
            handler: 要注销的事件处理函数
        """
        if handler in self.key_handlers:
            self.key_handlers.remove(handler)
            logger.debug(f"Unregistered key handler: {handler.__name__}")
    
    def get_modifier_state(self) -> Dict[str, bool]:
        """
        获取当前修饰键状态
        
        Returns:
            Dict[str, bool]: 修饰键状态字典
        """
        return self.modifier_keys.copy()
    
    def start_macro_recording(self) -> None:
        """开始录制宏"""
        if self.is_recording_macro:
            logger.warning("Macro recording is already in progress")
            return
        
        self.is_recording_macro = True
        self.macro_sequence = []
        logger.info("Started macro recording")
        
        # 通知其他组件
        self.message_bus.publish("macro_recording_status", {
            "status": "started",
            "timestamp": time.time()
        })
    
    def stop_macro_recording(self) -> Dict[str, Any]:
        """
        停止录制宏并返回宏数据
        
        Returns:
            Dict[str, Any]: 宏数据
        """
        if not self.is_recording_macro:
            logger.warning("No macro recording in progress")
            return {}
        
        self.is_recording_macro = False
        
        macro_data = {
            "name": f"macro_{int(time.time())}",
            "sequence": [event.to_dict() for event in self.macro_sequence],
            "created_at": time.time(),
            "duration": time.time() - (self.macro_sequence[0].timestamp if self.macro_sequence else time.time())
        }
        
        logger.info(f"Stopped macro recording. Sequence length: {len(self.macro_sequence)}")
        
        # 通知其他组件
        self.message_bus.publish("macro_recording_status", {
            "status": "stopped",
            "macro_data": macro_data,
            "timestamp": time.time()
        })
        
        return macro_data
    
    def execute_macro(self, macro_name: str) -> bool:
        """
        执行指定的宏
        
        Args:
            macro_name: 宏名称
            
        Returns:
            bool: 是否成功执行
        """
        # TODO: 从存储中加载宏并执行
        logger.info(f"Executing macro: {macro_name}")
        return False
    
    def simulate_keypress(self, key_sequence: List[Dict[str, Any]]) -> bool:
        """
        模拟按键序列
        
        Args:
            key_sequence: 按键序列
            
        Returns:
            bool: 是否成功模拟
        """
        logger.info(f"Simulating key sequence of length: {len(key_sequence)}")
        
        # TODO: 实现按键模拟
        # 这通常需要平台特定的代码
        
        return False
    
    def get_event_buffer(self, clear: bool = False) -> List[Dict[str, Any]]:
        """
        获取事件缓冲区内容
        
        Args:
            clear: 是否清空缓冲区
            
        Returns:
            List[Dict[str, Any]]: 事件列表
        """
        with self.buffer_lock:
            events = [event.to_dict() for event in self.event_buffer]
            if clear:
                self.event_buffer = []
        
        return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取键盘统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "is_running": self.is_running,
            "is_recording_macro": self.is_recording_macro,
            "modifier_states": self.modifier_keys,
            "event_buffer_size": len(self.event_buffer),
            "keyboard_layout": self.keyboard_layout,
            "handlers_count": len(self.key_handlers)
        }

        
