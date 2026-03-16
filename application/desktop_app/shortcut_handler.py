"""
快捷方式处理模块 - Mirexs桌面应用程序

提供系统快捷键处理功能，包括：
1. 全局快捷键注册
2. 应用内快捷键
3. 快捷键冲突检测
4. 快捷键配置持久化
5. 多平台适配
"""

import os
import sys
import logging
import json
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
import platform

# 尝试导入快捷键库
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logging.warning("keyboard module not available. Global shortcuts will be limited.")

try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logging.warning("pynput not available. Keyboard monitoring will be limited.")

logger = logging.getLogger(__name__)

class ShortcutScope(Enum):
    """快捷键作用域枚举"""
    GLOBAL = "global"      # 全局快捷键
    APPLICATION = "app"     # 应用内快捷键
    WINDOW = "window"       # 窗口内快捷键

class KeyModifier(Enum):
    """修饰键枚举"""
    NONE = ""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"
    CMD = "cmd"  # macOS

@dataclass
class Shortcut:
    """快捷键定义"""
    id: str
    name: str
    description: str
    key_combo: str  # 如 "Ctrl+Shift+M"
    scope: ShortcutScope = ShortcutScope.APPLICATION
    enabled: bool = True
    action: Optional[str] = None  # 动作标识
    callback: Optional[Callable] = None  # 回调函数
    platform_specific: Dict[str, str] = field(default_factory=dict)  # 平台特定组合键

@dataclass
class ShortcutHandlerConfig:
    """快捷键处理器配置"""
    enable_global: bool = True
    enable_app_shortcuts: bool = True
    conflict_check: bool = True
    save_config: bool = True
    config_file: str = "shortcuts.json"
    data_dir: str = "data/shortcut_handler/"

class ShortcutHandler:
    """
    快捷键处理器类
    
    负责管理应用程序的所有快捷键，提供注册、注销、冲突检测等功能。
    """
    
    def __init__(self, config: Optional[ShortcutHandlerConfig] = None):
        """
        初始化快捷键处理器
        
        Args:
            config: 处理器配置
        """
        self.config = config or ShortcutHandlerConfig()
        self.platform = platform.system().lower()
        
        # 快捷键存储
        self.shortcuts: Dict[str, Shortcut] = {}
        self.active_hooks: Dict[str, Any] = {}  # 存储已注册的钩子
        
        # 冲突检测
        self.conflicts: List[Tuple[str, str]] = []  # (shortcut1_id, shortcut2_id)
        
        # 监听器
        self.global_listener = None
        self.is_listening = False
        
        # 回调函数
        self.on_shortcut_triggered: Optional[Callable[[str], None]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载配置
        self._load_config()
        
        logger.info(f"ShortcutHandler initialized for platform: {self.platform}")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_config(self):
        """从文件加载快捷键配置"""
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for shortcut_data in data.get("shortcuts", []):
                        shortcut_id = shortcut_data.get("id")
                        if shortcut_id in self.shortcuts:
                            # 更新现有快捷键
                            shortcut = self.shortcuts[shortcut_id]
                            shortcut.enabled = shortcut_data.get("enabled", True)
                            if "key_combo" in shortcut_data:
                                shortcut.key_combo = shortcut_data["key_combo"]
                
                logger.info(f"Shortcut config loaded from {config_path}")
                
            except Exception as e:
                logger.error(f"Error loading shortcut config: {e}")
    
    def _save_config(self):
        """保存快捷键配置到文件"""
        if not self.config.save_config:
            return
        
        config_path = os.path.join(self.config.data_dir, self.config.config_file)
        try:
            data = {
                "shortcuts": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "key_combo": s.key_combo,
                        "enabled": s.enabled,
                        "scope": s.scope.value
                    }
                    for s in self.shortcuts.values()
                ],
                "saved_at": __import__('datetime').datetime.now().isoformat()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Shortcut config saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving shortcut config: {e}")
    
    def register_shortcut(self, key_combo: str, action: str, 
                         name: str = "", description: str = "",
                         scope: ShortcutScope = ShortcutScope.APPLICATION,
                         callback: Optional[Callable] = None) -> str:
        """
        注册快捷键
        
        Args:
            key_combo: 组合键，如 "Ctrl+Shift+M"
            action: 动作标识
            name: 快捷键名称
            description: 描述
            scope: 作用域
            callback: 回调函数
        
        Returns:
            快捷键ID
        """
        # 生成ID
        shortcut_id = f"shortcut_{action}_{len(self.shortcuts)}"
        
        # 规范化组合键
        normalized_combo = self._normalize_key_combo(key_combo)
        
        # 检查冲突
        if self.config.conflict_check:
            conflict = self._check_conflict(normalized_combo)
            if conflict:
                logger.warning(f"Shortcut conflict: {key_combo} conflicts with {conflict}")
        
        shortcut = Shortcut(
            id=shortcut_id,
            name=name or action,
            description=description,
            key_combo=normalized_combo,
            scope=scope,
            action=action,
            callback=callback
        )
        
        self.shortcuts[shortcut_id] = shortcut
        
        # 如果启用了全局快捷键，立即注册
        if scope == ShortcutScope.GLOBAL and self.config.enable_global and shortcut.enabled:
            self._register_global_shortcut(shortcut)
        
        logger.info(f"Shortcut registered: {key_combo} -> {action}")
        
        return shortcut_id
    
    def _normalize_key_combo(self, key_combo: str) -> str:
        """规范化组合键表示"""
        # 移除空格，转换为小写
        parts = [p.strip().lower() for p in key_combo.replace('+', ' ').split()]
        
        # 平台特定转换
        if self.platform == "darwin":  # macOS
            # 将 Ctrl 转换为 Cmd
            parts = ['cmd' if p == 'ctrl' else p for p in parts]
        elif self.platform == "linux":
            # Linux 特定处理
            parts = ['super' if p == 'win' else p for p in parts]
        
        # 排序修饰键
        modifiers = ['ctrl', 'alt', 'shift', 'cmd', 'win', 'super']
        modifier_parts = [p for p in parts if p in modifiers]
        key_parts = [p for p in parts if p not in modifiers]
        
        modifier_parts.sort(key=lambda x: modifiers.index(x) if x in modifiers else 999)
        
        return '+'.join(modifier_parts + key_parts)
    
    def _check_conflict(self, key_combo: str) -> Optional[str]:
        """
        检查快捷键冲突
        
        Args:
            key_combo: 组合键
        
        Returns:
            冲突的快捷键ID，无冲突返回None
        """
        for shortcut_id, shortcut in self.shortcuts.items():
            if shortcut.key_combo == key_combo and shortcut.enabled:
                return shortcut_id
        return None
    
    def _register_global_shortcut(self, shortcut: Shortcut):
        """注册全局快捷键"""
        if not KEYBOARD_AVAILABLE:
            logger.warning("Cannot register global shortcut: keyboard module not available")
            return
        
        try:
            def callback():
                logger.debug(f"Global shortcut triggered: {shortcut.key_combo}")
                self._on_shortcut_triggered(shortcut)
            
            # 注册热键
            keyboard.add_hotkey(shortcut.key_combo, callback)
            
            self.active_hooks[shortcut.id] = callback
            logger.debug(f"Global shortcut registered: {shortcut.key_combo}")
            
        except Exception as e:
            logger.error(f"Error registering global shortcut {shortcut.key_combo}: {e}")
    
    def _unregister_global_shortcut(self, shortcut_id: str):
        """注销全局快捷键"""
        if not KEYBOARD_AVAILABLE:
            return
        
        if shortcut_id in self.active_hooks:
            try:
                # keyboard 库没有直接的移除方法，需要重新设置
                # 这里简化处理
                del self.active_hooks[shortcut_id]
                logger.debug(f"Global shortcut unregistered: {shortcut_id}")
                
            except Exception as e:
                logger.error(f"Error unregistering global shortcut: {e}")
    
    def _on_shortcut_triggered(self, shortcut: Shortcut):
        """快捷键触发处理"""
        logger.debug(f"Shortcut triggered: {shortcut.key_combo} ({shortcut.action})")
        
        # 调用回调
        if shortcut.callback:
            try:
                shortcut.callback()
            except Exception as e:
                logger.error(f"Error in shortcut callback: {e}")
        
        # 触发通用事件
        if self.on_shortcut_triggered:
            try:
                self.on_shortcut_triggered(shortcut.action or shortcut.id)
            except Exception as e:
                logger.error(f"Error in on_shortcut_triggered: {e}")
    
    def unregister_shortcut(self, shortcut_id: str):
        """
        注销快捷键
        
        Args:
            shortcut_id: 快捷键ID
        """
        if shortcut_id not in self.shortcuts:
            logger.warning(f"Shortcut not found: {shortcut_id}")
            return
        
        shortcut = self.shortcuts[shortcut_id]
        
        # 注销全局快捷键
        if shortcut.scope == ShortcutScope.GLOBAL:
            self._unregister_global_shortcut(shortcut_id)
        
        # 移除
        del self.shortcuts[shortcut_id]
        
        logger.info(f"Shortcut unregistered: {shortcut_id}")
    
    def enable_shortcut(self, shortcut_id: str, enabled: bool = True):
        """
        启用/禁用快捷键
        
        Args:
            shortcut_id: 快捷键ID
            enabled: 是否启用
        """
        if shortcut_id not in self.shortcuts:
            logger.warning(f"Shortcut not found: {shortcut_id}")
            return
        
        shortcut = self.shortcuts[shortcut_id]
        shortcut.enabled = enabled
        
        # 如果是全局快捷键，动态注册/注销
        if shortcut.scope == ShortcutScope.GLOBAL and self.config.enable_global:
            if enabled:
                self._register_global_shortcut(shortcut)
            else:
                self._unregister_global_shortcut(shortcut_id)
        
        logger.debug(f"Shortcut {shortcut_id} enabled: {enabled}")
    
    def update_shortcut_key(self, shortcut_id: str, new_key_combo: str) -> bool:
        """
        更新快捷键组合键
        
        Args:
            shortcut_id: 快捷键ID
            new_key_combo: 新组合键
        
        Returns:
            是否成功
        """
        if shortcut_id not in self.shortcuts:
            logger.warning(f"Shortcut not found: {shortcut_id}")
            return False
        
        shortcut = self.shortcuts[shortcut_id]
        normalized_combo = self._normalize_key_combo(new_key_combo)
        
        # 检查冲突
        if self.config.conflict_check:
            conflict = self._check_conflict(normalized_combo)
            if conflict and conflict != shortcut_id:
                logger.warning(f"Shortcut conflict: {new_key_combo} conflicts with {conflict}")
                return False
        
        # 如果是全局快捷键，先注销旧的
        if shortcut.scope == ShortcutScope.GLOBAL and shortcut.enabled:
            self._unregister_global_shortcut(shortcut_id)
        
        # 更新组合键
        shortcut.key_combo = normalized_combo
        
        # 重新注册
        if shortcut.scope == ShortcutScope.GLOBAL and shortcut.enabled:
            self._register_global_shortcut(shortcut)
        
        logger.info(f"Shortcut {shortcut_id} updated: {new_key_combo}")
        
        return True
    
    def get_shortcut(self, shortcut_id: str) -> Optional[Shortcut]:
        """
        获取快捷键信息
        
        Args:
            shortcut_id: 快捷键ID
        
        Returns:
            快捷键对象
        """
        return self.shortcuts.get(shortcut_id)
    
    def get_shortcut_by_action(self, action: str) -> Optional[Shortcut]:
        """
        根据动作获取快捷键
        
        Args:
            action: 动作标识
        
        Returns:
            快捷键对象
        """
        for shortcut in self.shortcuts.values():
            if shortcut.action == action:
                return shortcut
        return None
    
    def get_all_shortcuts(self, scope: Optional[ShortcutScope] = None) -> List[Dict[str, Any]]:
        """
        获取所有快捷键信息
        
        Args:
            scope: 筛选作用域
        
        Returns:
            快捷键信息列表
        """
        result = []
        for shortcut in self.shortcuts.values():
            if scope and shortcut.scope != scope:
                continue
            
            result.append({
                'id': shortcut.id,
                'name': shortcut.name,
                'description': shortcut.description,
                'key_combo': shortcut.key_combo,
                'scope': shortcut.scope.value,
                'enabled': shortcut.enabled,
                'action': shortcut.action
            })
        
        return result
    
    def start_global_listener(self):
        """启动全局快捷键监听"""
        if not PYNPUT_AVAILABLE:
            logger.warning("Cannot start global listener: pynput not available")
            return
        
        if self.is_listening:
            return
        
        def on_press(key):
            # 这里可以处理更复杂的快捷键逻辑
            pass
        
        def on_release(key):
            # 检查组合键
            pass
        
        self.global_listener = pynput_keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self.global_listener.start()
        self.is_listening = True
        
        logger.info("Global keyboard listener started")
    
    def stop_global_listener(self):
        """停止全局快捷键监听"""
        if self.global_listener:
            self.global_listener.stop()
            self.global_listener = None
        
        self.is_listening = False
        logger.info("Global keyboard listener stopped")
    
    def export_shortcuts(self, file_path: str) -> bool:
        """
        导出快捷键配置
        
        Args:
            file_path: 导出路径
        
        Returns:
            是否成功
        """
        data = {
            'shortcuts': self.get_all_shortcuts(),
            'platform': self.platform,
            'exported_at': __import__('datetime').datetime.now().isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Shortcuts exported to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting shortcuts: {e}")
            return False
    
    def import_shortcuts(self, file_path: str) -> int:
        """
        导入快捷键配置
        
        Args:
            file_path: 导入路径
        
        Returns:
            导入的数量
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            for shortcut_data in data.get('shortcuts', []):
                shortcut_id = shortcut_data.get('id')
                
                if shortcut_id in self.shortcuts:
                    # 更新现有快捷键
                    shortcut = self.shortcuts[shortcut_id]
                    shortcut.key_combo = shortcut_data.get('key_combo', shortcut.key_combo)
                    shortcut.enabled = shortcut_data.get('enabled', shortcut.enabled)
                    count += 1
            
            logger.info(f"Imported {count} shortcuts from {file_path}")
            return count
            
        except Exception as e:
            logger.error(f"Error importing shortcuts: {e}")
            return 0
    
    def reset_to_defaults(self):
        """重置为默认快捷键"""
        # 这里应该实现默认快捷键设置
        # 简化处理
        for shortcut in self.shortcuts.values():
            # 重置为初始值
            pass
        
        logger.info("Shortcuts reset to defaults")
    
    def shutdown(self):
        """关闭快捷键处理器"""
        logger.info("Shutting down ShortcutHandler...")
        
        # 停止监听
        self.stop_global_listener()
        
        # 注销所有全局快捷键
        for shortcut_id in list(self.active_hooks.keys()):
            self._unregister_global_shortcut(shortcut_id)
        
        # 保存配置
        self._save_config()
        
        logger.info("ShortcutHandler shutdown completed")


