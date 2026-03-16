"""
快捷键管理器：管理全局和应用程序特定的快捷键
"""

import threading
import time
import json
from typing import Dict, List, Optional, Any, Callable, Set
import logging
from dataclasses import dataclass, field
from collections import defaultdict

from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager
from interaction.input_systems.text_input.keyboard_handler import KeyboardHandler, KeyEvent

logger = logging.getLogger(__name__)


@dataclass
class Shortcut:
    """快捷键定义"""
    id: str
    name: str
    description: str
    default_keys: List[str]  # 例如 ["ctrl", "c"]
    current_keys: List[str]
    category: str  # system, application, custom, etc.
    enabled: bool = True
    context: Optional[str] = None  # 上下文限制
    application: Optional[str] = None  # 应用程序限制
    handler: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_keys": self.default_keys,
            "current_keys": self.current_keys,
            "category": self.category,
            "enabled": self.enabled,
            "context": self.context,
            "application": self.application
        }
    
    def get_key_string(self) -> str:
        """获取快捷键字符串表示"""
        return "+".join(self.current_keys).lower()


class ShortcutManager:
    """快捷键管理器"""
    
    def __init__(self, config_manager: ConfigManager, keyboard_handler: KeyboardHandler):
        """
        初始化快捷键管理器
        
        Args:
            config_manager: 配置管理器
            keyboard_handler: 键盘处理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        self.keyboard_handler = keyboard_handler
        
        # 快捷键注册表
        self.shortcuts = {}  # id -> Shortcut
        self.key_to_shortcut = defaultdict(list)  # key_string -> List[Shortcut]
        
        # 上下文状态
        self.current_context = "global"
        self.current_application = None
        self.context_stack = []
        
        # 配置
        self.enable_shortcuts = True
        self.enable_conflict_detection = True
        self.conflict_resolution = "priority"  # priority, disable, warn
        
        # 统计
        self.shortcut_usage = defaultdict(int)
        self.conflicts_detected = []
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 加载配置
        self.load_config()
        
        # 加载系统快捷键
        self.load_system_shortcuts()
        
        # 加载用户快捷键
        self.load_user_shortcuts()
        
        # 注册键盘事件处理器
        self.keyboard_handler.register_key_handler(self._handle_key_event)
        
        logger.info("ShortcutManager initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("shortcuts_config")
            
            # 基本配置
            self.enable_shortcuts = config.get("enable_shortcuts", True)
            self.enable_conflict_detection = config.get("enable_conflict_detection", True)
            self.conflict_resolution = config.get("conflict_resolution", "priority")
            self.auto_save = config.get("auto_save", True)
            self.save_interval = config.get("save_interval", 300)  # 5分钟
            
            # 冲突检测配置
            conflict_config = config.get("conflict_detection", {})
            self.detection_threshold = conflict_config.get("detection_threshold", 0.8)
            self.auto_resolve = conflict_config.get("auto_resolve", False)
            
            logger.debug("Shortcut config loaded")
        except Exception as e:
            logger.error(f"Failed to load shortcut config: {e}")
    
    def load_system_shortcuts(self) -> None:
        """加载系统快捷键"""
        try:
            # 从配置文件加载
            shortcuts_file = "config/shortcuts/system_shortcuts.json"
            if os.path.exists(shortcuts_file):
                with open(shortcuts_file, 'r', encoding='utf-8') as f:
                    shortcuts_data = json.load(f)
                
                for shortcut_data in shortcuts_data:
                    self._register_shortcut_from_dict(shortcut_data, "system")
            
            # 添加默认系统快捷键
            self._add_default_system_shortcuts()
            
            logger.info(f"Loaded {len([s for s in self.shortcuts.values() if s.category == 'system'])} system shortcuts")
        except Exception as e:
            logger.error(f"Failed to load system shortcuts: {e}")
    
    def _add_default_system_shortcuts(self) -> None:
        """添加默认系统快捷键"""
        default_shortcuts = [
            # 全局快捷键
            Shortcut(
                id="show_hide_mirexs",
                name="显示/隐藏弥尔思",
                description="显示或隐藏弥尔思窗口",
                default_keys=["ctrl", "alt", "m"],
                current_keys=["ctrl", "alt", "m"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="voice_input_toggle",
                name="语音输入开关",
                description="开始或停止语音输入",
                default_keys=["ctrl", "alt", "v"],
                current_keys=["ctrl", "alt", "v"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="screenshot",
                name="截屏",
                description="截取屏幕截图",
                default_keys=["ctrl", "alt", "s"],
                current_keys=["ctrl", "alt", "s"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="quick_note",
                name="快速笔记",
                description="打开快速笔记",
                default_keys=["ctrl", "alt", "n"],
                current_keys=["ctrl", "alt", "n"],
                category="system",
                context="global"
            ),
            
            # 文本编辑快捷键
            Shortcut(
                id="copy",
                name="复制",
                description="复制选中内容",
                default_keys=["ctrl", "c"],
                current_keys=["ctrl", "c"],
                category="system",
                context="text_edit"
            ),
            Shortcut(
                id="paste",
                name="粘贴",
                description="粘贴内容",
                default_keys=["ctrl", "v"],
                current_keys=["ctrl", "v"],
                category="system",
                context="text_edit"
            ),
            Shortcut(
                id="cut",
                name="剪切",
                description="剪切选中内容",
                default_keys=["ctrl", "x"],
                current_keys=["ctrl", "x"],
                category="system",
                context="text_edit"
            ),
            Shortcut(
                id="undo",
                name="撤销",
                description="撤销上一步操作",
                default_keys=["ctrl", "z"],
                current_keys=["ctrl", "z"],
                category="system",
                context="text_edit"
            ),
            Shortcut(
                id="redo",
                name="重做",
                description="重做上一步操作",
                default_keys=["ctrl", "y"],
                current_keys=["ctrl", "y"],
                category="system",
                context="text_edit"
            ),
            Shortcut(
                id="select_all",
                name="全选",
                description="选择所有内容",
                default_keys=["ctrl", "a"],
                current_keys=["ctrl", "a"],
                category="system",
                context="text_edit"
            ),
            
            # 窗口管理快捷键
            Shortcut(
                id="minimize_window",
                name="最小化窗口",
                description="最小化当前窗口",
                default_keys=["ctrl", "m"],
                current_keys=["ctrl", "m"],
                category="system",
                context="window"
            ),
            Shortcut(
                id="close_window",
                name="关闭窗口",
                description="关闭当前窗口",
                default_keys=["ctrl", "w"],
                current_keys=["ctrl", "w"],
                category="system",
                context="window"
            ),
            Shortcut(
                id="switch_window",
                name="切换窗口",
                description="切换到下一个窗口",
                default_keys=["alt", "tab"],
                current_keys=["alt", "tab"],
                category="system",
                context="global"
            ),
            
            # 媒体控制快捷键
            Shortcut(
                id="play_pause",
                name="播放/暂停",
                description="播放或暂停媒体",
                default_keys=["ctrl", "alt", "p"],
                current_keys=["ctrl", "alt", "p"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="next_track",
                name="下一曲",
                description="播放下一曲",
                default_keys=["ctrl", "alt", "right"],
                current_keys=["ctrl", "alt", "right"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="previous_track",
                name="上一曲",
                description="播放上一曲",
                default_keys=["ctrl", "alt", "left"],
                current_keys=["ctrl", "alt", "left"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="volume_up",
                name="音量增加",
                description="增加音量",
                default_keys=["ctrl", "alt", "up"],
                current_keys=["ctrl", "alt", "up"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="volume_down",
                name="音量减少",
                description="减少音量",
                default_keys=["ctrl", "alt", "down"],
                current_keys=["ctrl", "alt", "down"],
                category="system",
                context="global"
            ),
            Shortcut(
                id="mute",
                name="静音",
                description="切换静音状态",
                default_keys=["ctrl", "alt", "m"],
                current_keys=["ctrl", "alt", "m"],
                category="system",
                context="global"
            ),
        ]
        
        for shortcut in default_shortcuts:
            self.register_shortcut(shortcut)
    
    def load_user_shortcuts(self) -> None:
        """加载用户快捷键"""
        try:
            user_shortcuts_file = "data/user_data/shortcuts/user_shortcuts.json"
            if os.path.exists(user_shortcuts_file):
                with open(user_shortcuts_file, 'r', encoding='utf-8') as f:
                    user_shortcuts = json.load(f)
                
                for shortcut_data in user_shortcuts:
                    self._register_shortcut_from_dict(shortcut_data, "user")
            
            logger.info(f"Loaded {len([s for s in self.shortcuts.values() if s.category == 'user'])} user shortcuts")
        except Exception as e:
            logger.error(f"Failed to load user shortcuts: {e}")
    
    def _register_shortcut_from_dict(self, shortcut_data: Dict[str, Any], category: str) -> None:
        """从字典注册快捷键"""
        try:
            shortcut = Shortcut(
                id=shortcut_data["id"],
                name=shortcut_data["name"],
                description=shortcut_data.get("description", ""),
                default_keys=shortcut_data.get("default_keys", []),
                current_keys=shortcut_data.get("current_keys", shortcut_data.get("default_keys", [])),
                category=category,
                enabled=shortcut_data.get("enabled", True),
                context=shortcut_data.get("context"),
                application=shortcut_data.get("application")
            )
            
            # 如果有处理器信息，需要特殊处理
            # 在实际应用中，可能需要动态加载处理器函数
            
            self.register_shortcut(shortcut)
            
        except Exception as e:
            logger.error(f"Failed to register shortcut from dict: {e}")
    
    def register_shortcut(self, shortcut: Shortcut) -> bool:
        """
        注册快捷键
        
        Args:
            shortcut: 快捷键对象
            
        Returns:
            bool: 是否注册成功
        """
        with self.lock:
            # 检查ID是否已存在
            if shortcut.id in self.shortcuts:
                logger.warning(f"Shortcut ID already exists: {shortcut.id}")
                return False
            
            # 检查快捷键冲突
            key_string = shortcut.get_key_string()
            conflicting_shortcuts = self._find_conflicts(shortcut)
            
            if conflicting_shortcuts and self.enable_conflict_detection:
                if not self._resolve_conflict(shortcut, conflicting_shortcuts):
                    logger.warning(f"Shortcut conflict not resolved: {shortcut.id}")
                    return False
            
            # 注册快捷键
            self.shortcuts[shortcut.id] = shortcut
            
            # 添加到键映射
            if shortcut.enabled:
                self.key_to_shortcut[key_string].append(shortcut)
                # 按优先级排序（系统 > 应用 > 用户 > 自定义）
                self.key_to_shortcut[key_string].sort(key=self._get_shortcut_priority, reverse=True)
            
            logger.debug(f"Registered shortcut: {shortcut.id} ({key_string})")
            return True
    
    def _find_conflicts(self, shortcut: Shortcut) -> List[Shortcut]:
        """查找冲突的快捷键"""
        key_string = shortcut.get_key_string()
        conflicts = []
        
        if key_string in self.key_to_shortcut:
            existing_shortcuts = self.key_to_shortcut[key_string]
            
            for existing_shortcut in existing_shortcuts:
                # 检查上下文是否冲突
                if self._contexts_conflict(shortcut.context, existing_shortcut.context):
                    # 检查应用程序是否冲突
                    if self._applications_conflict(shortcut.application, existing_shortcut.application):
                        conflicts.append(existing_shortcut)
        
        return conflicts
    
    def _contexts_conflict(self, context1: Optional[str], context2: Optional[str]) -> bool:
        """检查上下文是否冲突"""
        if context1 is None or context2 is None:
            return True  # 全局上下文与任何上下文都冲突
        
        return context1 == context2 or context1 == "global" or context2 == "global"
    
    def _applications_conflict(self, app1: Optional[str], app2: Optional[str]) -> bool:
        """检查应用程序是否冲突"""
        if app1 is None or app2 is None:
            return True  # 全局应用程序与任何应用程序都冲突
        
        return app1 == app2
    
    def _resolve_conflict(self, new_shortcut: Shortcut, conflicts: List[Shortcut]) -> bool:
        """解决快捷键冲突"""
        logger.warning(f"Shortcut conflict detected: {new_shortcut.id} conflicts with {[c.id for c in conflicts]}")
        
        # 记录冲突
        conflict_record = {
            "new_shortcut": new_shortcut.id,
            "conflicting_shortcuts": [c.id for c in conflicts],
            "key_string": new_shortcut.get_key_string(),
            "timestamp": time.time()
        }
        self.conflicts_detected.append(conflict_record)
        
        # 根据配置解决冲突
        if self.conflict_resolution == "priority":
            return self._resolve_by_priority(new_shortcut, conflicts)
        elif self.conflict_resolution == "disable":
            return self._resolve_by_disabling(new_shortcut, conflicts)
        elif self.conflict_resolution == "warn":
            # 只警告，不自动解决
            self._notify_conflict(new_shortcut, conflicts)
            return True  # 仍然允许注册
        else:
            return False
    
    def _resolve_by_priority(self, new_shortcut: Shortcut, conflicts: List[Shortcut]) -> bool:
        """通过优先级解决冲突"""
        # 计算新快捷键的优先级
        new_priority = self._get_shortcut_priority(new_shortcut)
        
        for conflict in conflicts:
            conflict_priority = self._get_shortcut_priority(conflict)
            
            if new_priority > conflict_priority:
                # 新快捷键优先级更高，禁用冲突的快捷键
                self.disable_shortcut(conflict.id)
                logger.info(f"Disabled lower priority shortcut: {conflict.id}")
            elif new_priority < conflict_priority:
                # 冲突快捷键优先级更高，拒绝新快捷键
                logger.warning(f"New shortcut has lower priority: {new_shortcut.id}")
                return False
            else:
                # 优先级相同，根据其他规则决定
                # 这里可以添加更多规则，如最近使用频率等
                pass
        
        return True
    
    def _get_shortcut_priority(self, shortcut: Shortcut) -> int:
        """获取快捷键优先级"""
        priority_map = {
            "system": 100,
            "application": 80,
            "user": 60,
            "custom": 40
        }
        return priority_map.get(shortcut.category, 50)
    
    def _resolve_by_disabling(self, new_shortcut: Shortcut, conflicts: List[Shortcut]) -> bool:
        """通过禁用解决冲突"""
        # 禁用所有冲突的快捷键
        for conflict in conflicts:
            self.disable_shortcut(conflict.id)
            logger.info(f"Disabled conflicting shortcut: {conflict.id}")
        
        return True
    
    def _notify_conflict(self, new_shortcut: Shortcut, conflicts: List[Shortcut]) -> None:
        """通知用户冲突"""
        conflict_info = {
            "new_shortcut": new_shortcut.to_dict(),
            "conflicting_shortcuts": [c.to_dict() for c in conflicts],
            "timestamp": time.time()
        }
        
        # 发布冲突通知
        self.message_bus.publish("shortcut_conflict", conflict_info)
    
    def _handle_key_event(self, key_event: KeyEvent) -> None:
        """处理键盘事件"""
        if not self.enable_shortcuts or key_event.event_type != "key_down":
            return
        
        # 获取当前修饰键状态
        modifier_state = self.keyboard_handler.get_modifier_state()
        
        # 构建按键字符串
        key_parts = []
        
        # 添加修饰键
        if modifier_state.get('ctrl'):
            key_parts.append("ctrl")
        if modifier_state.get('alt'):
            key_parts.append("alt")
        if modifier_state.get('shift'):
            key_parts.append("shift")
        if modifier_state.get('win'):
            key_parts.append("win")
        
        # 添加主键
        key_parts.append(key_event.key_name.lower())
        
        key_string = "+".join(key_parts)
        
        # 查找匹配的快捷键
        matched_shortcuts = self._find_matching_shortcuts(key_string)
        
        if matched_shortcuts:
            # 执行最高优先级的快捷键
            shortcut = matched_shortcuts[0]
            self._execute_shortcut(shortcut)
    
    def _find_matching_shortcuts(self, key_string: str) -> List[Shortcut]:
        """查找匹配的快捷键"""
        matching_shortcuts = []
        
        if key_string in self.key_to_shortcut:
            for shortcut in self.key_to_shortcut[key_string]:
                # 检查上下文是否匹配
                if self._check_context_match(shortcut):
                    # 检查应用程序是否匹配
                    if self._check_application_match(shortcut):
                        matching_shortcuts.append(shortcut)
        
        return matching_shortcuts
    
    def _check_context_match(self, shortcut: Shortcut) -> bool:
        """检查上下文匹配"""
        if shortcut.context is None:
            return True  # 全局上下文
        
        # 检查当前上下文
        if shortcut.context == self.current_context:
            return True
        
        # 检查上下文栈
        if shortcut.context in self.context_stack:
            return True
        
        return False
    
    def _check_application_match(self, shortcut: Shortcut) -> bool:
        """检查应用程序匹配"""
        if shortcut.application is None:
            return True  # 全局应用程序
        
        if self.current_application == shortcut.application:
            return True
        
        return False
    
    def _execute_shortcut(self, shortcut: Shortcut) -> None:
        """执行快捷键"""
        try:
            # 更新使用统计
            self.shortcut_usage[shortcut.id] += 1
            
            # 如果有处理器，调用处理器
            if shortcut.handler:
                shortcut.handler()
            else:
                # 发布快捷键事件
                self.message_bus.publish("shortcut_triggered", {
                    "shortcut_id": shortcut.id,
                    "shortcut_name": shortcut.name,
                    "key_string": shortcut.get_key_string(),
                    "context": self.current_context,
                    "application": self.current_application,
                    "timestamp": time.time()
                })
            
            logger.debug(f"Executed shortcut: {shortcut.id}")
            
        except Exception as e:
            logger.error(f"Failed to execute shortcut {shortcut.id}: {e}")
    
    def register_handler(self, shortcut_id: str, handler: Callable) -> bool:
        """
        为快捷键注册处理器
        
        Args:
            shortcut_id: 快捷键ID
            handler: 处理器函数
            
        Returns:
            bool: 是否注册成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                logger.error(f"Shortcut not found: {shortcut_id}")
                return False
            
            self.shortcuts[shortcut_id].handler = handler
            logger.debug(f"Registered handler for shortcut: {shortcut_id}")
            return True
    
    def unregister_shortcut(self, shortcut_id: str) -> bool:
        """
        注销快捷键
        
        Args:
            shortcut_id: 快捷键ID
            
        Returns:
            bool: 是否注销成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                return False
            
            shortcut = self.shortcuts[shortcut_id]
            key_string = shortcut.get_key_string()
            
            # 从键映射中移除
            if key_string in self.key_to_shortcut:
                self.key_to_shortcut[key_string] = [
                    s for s in self.key_to_shortcut[key_string]
                    if s.id != shortcut_id
                ]
                
                # 如果列表为空，删除键
                if not self.key_to_shortcut[key_string]:
                    del self.key_to_shortcut[key_string]
            
            # 从注册表中移除
            del self.shortcuts[shortcut_id]
            
            logger.info(f"Unregistered shortcut: {shortcut_id}")
            return True
    
    def enable_shortcut(self, shortcut_id: str) -> bool:
        """
        启用快捷键
        
        Args:
            shortcut_id: 快捷键ID
            
        Returns:
            bool: 是否启用成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                return False
            
            shortcut = self.shortcuts[shortcut_id]
            if shortcut.enabled:
                return True
            
            shortcut.enabled = True
            key_string = shortcut.get_key_string()
            
            # 添加到键映射
            self.key_to_shortcut[key_string].append(shortcut)
            self.key_to_shortcut[key_string].sort(key=self._get_shortcut_priority, reverse=True)
            
            # 检查冲突
            if self.enable_conflict_detection:
                conflicts = self._find_conflicts(shortcut)
                if conflicts:
                    self._resolve_conflict(shortcut, conflicts)
            
            logger.info(f"Enabled shortcut: {shortcut_id}")
            return True
    
    def disable_shortcut(self, shortcut_id: str) -> bool:
        """
        禁用快捷键
        
        Args:
            shortcut_id: 快捷键ID
            
        Returns:
            bool: 是否禁用成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                return False
            
            shortcut = self.shortcuts[shortcut_id]
            if not shortcut.enabled:
                return True
            
            shortcut.enabled = False
            key_string = shortcut.get_key_string()
            
            # 从键映射中移除
            if key_string in self.key_to_shortcut:
                self.key_to_shortcut[key_string] = [
                    s for s in self.key_to_shortcut[key_string]
                    if s.id != shortcut_id
                ]
                
                # 如果列表为空，删除键
                if not self.key_to_shortcut[key_string]:
                    del self.key_to_shortcut[key_string]
            
            logger.info(f"Disabled shortcut: {shortcut_id}")
            return True
    
    def update_shortcut_keys(self, shortcut_id: str, new_keys: List[str]) -> bool:
        """
        更新快捷键按键
        
        Args:
            shortcut_id: 快捷键ID
            new_keys: 新的按键列表
            
        Returns:
            bool: 是否更新成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                return False
            
            shortcut = self.shortcuts[shortcut_id]
            old_key_string = shortcut.get_key_string()
            
            # 从旧键映射中移除
            if old_key_string in self.key_to_shortcut:
                self.key_to_shortcut[old_key_string] = [
                    s for s in self.key_to_shortcut[old_key_string]
                    if s.id != shortcut_id
                ]
                
                if not self.key_to_shortcut[old_key_string]:
                    del self.key_to_shortcut[old_key_string]
            
            # 更新按键
            shortcut.current_keys = new_keys.copy()
            
            # 检查冲突
            new_key_string = shortcut.get_key_string()
            if shortcut.enabled:
                conflicts = self._find_conflicts(shortcut)
                if conflicts and self.enable_conflict_detection:
                    if not self._resolve_conflict(shortcut, conflicts):
                        # 冲突未解决，恢复旧按键
                        shortcut.current_keys = old_key_string.split("+")
                        return False
                
                # 添加到新键映射
                self.key_to_shortcut[new_key_string].append(shortcut)
                self.key_to_shortcut[new_key_string].sort(key=self._get_shortcut_priority, reverse=True)
            
            logger.info(f"Updated shortcut keys: {shortcut_id} -> {new_key_string}")
            return True
    
    def reset_to_default(self, shortcut_id: str) -> bool:
        """
        重置快捷键为默认值
        
        Args:
            shortcut_id: 快捷键ID
            
        Returns:
            bool: 是否重置成功
        """
        with self.lock:
            if shortcut_id not in self.shortcuts:
                return False
            
            shortcut = self.shortcuts[shortcut_id]
            return self.update_shortcut_keys(shortcut_id, shortcut.default_keys.copy())
    
    def set_context(self, context: str) -> None:
        """
        设置当前上下文
        
        Args:
            context: 上下文名称
        """
        self.current_context = context
        logger.debug(f"Context set to: {context}")
    
    def push_context(self, context: str) -> None:
        """
        推入上下文到栈
        
        Args:
            context: 上下文名称
        """
        self.context_stack.append(context)
        logger.debug(f"Pushed context: {context}")
    
    def pop_context(self) -> Optional[str]:
        """
        从栈中弹出上下文
        
        Returns:
            str: 弹出的上下文，如果栈为空则返回None
        """
        if self.context_stack:
            context = self.context_stack.pop()
            logger.debug(f"Popped context: {context}")
            return context
        return None
    
    def set_application(self, application: str) -> None:
        """
        设置当前应用程序
        
        Args:
            application: 应用程序名称
        """
        self.current_application = application
        logger.debug(f"Application set to: {application}")
    
    def get_shortcut_list(self, category: Optional[str] = None, 
                         enabled_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取快捷键列表
        
        Args:
            category: 类别筛选（可选）
            enabled_only: 是否只返回启用的快捷键
            
        Returns:
            List[Dict[str, Any]]: 快捷键信息列表
        """
        with self.lock:
            shortcuts = []
            
            for shortcut in self.shortcuts.values():
                if category and shortcut.category != category:
                    continue
                
                if enabled_only and not shortcut.enabled:
                    continue
                
                shortcut_dict = shortcut.to_dict()
                
                # 添加上下文匹配信息
                shortcut_dict["context_matches"] = self._check_context_match(shortcut)
                shortcut_dict["application_matches"] = self._check_application_match(shortcut)
                
                # 添加使用统计
                shortcut_dict["usage_count"] = self.shortcut_usage.get(shortcut.id, 0)
                
                shortcuts.append(shortcut_dict)
            
            return shortcuts
    
    def find_shortcut_by_keys(self, keys: List[str]) -> Optional[Dict[str, Any]]:
        """
        根据按键查找快捷键
        
        Args:
            keys: 按键列表
            
        Returns:
            Dict[str, Any]: 快捷键信息，如果未找到则返回None
        """
        key_string = "+".join(k.lower() for k in keys)
        
        if key_string in self.key_to_shortcut:
            shortcuts = self.key_to_shortcut[key_string]
            for shortcut in shortcuts:
                if self._check_context_match(shortcut) and self._check_application_match(shortcut):
                    shortcut_dict = shortcut.to_dict()
                    shortcut_dict["context_matches"] = True
                    shortcut_dict["application_matches"] = True
                    shortcut_dict["usage_count"] = self.shortcut_usage.get(shortcut.id, 0)
                    return shortcut_dict
        
        return None
    
    def save_user_shortcuts(self) -> bool:
        """
        保存用户快捷键到磁盘
        
        Returns:
            bool: 是否保存成功
        """
        try:
            user_shortcuts = []
            
            for shortcut in self.shortcuts.values():
                if shortcut.category in ["user", "custom"]:
                    user_shortcuts.append(shortcut.to_dict())
            
            user_shortcuts_file = "data/user_data/shortcuts/user_shortcuts.json"
            os.makedirs(os.path.dirname(user_shortcuts_file), exist_ok=True)
            
            with open(user_shortcuts_file, 'w', encoding='utf-8') as f:
                json.dump(user_shortcuts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(user_shortcuts)} user shortcuts")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user shortcuts: {e}")
            return False
    
    def export_shortcuts(self, file_path: str, categories: Optional[List[str]] = None) -> bool:
        """
        导出快捷键配置
        
        Args:
            file_path: 导出文件路径
            categories: 要导出的类别列表（None表示全部）
            
        Returns:
            bool: 是否导出成功
        """
        try:
            shortcuts_to_export = []
            
            for shortcut in self.shortcuts.values():
                if categories and shortcut.category not in categories:
                    continue
                
                shortcuts_to_export.append(shortcut.to_dict())
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(shortcuts_to_export, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(shortcuts_to_export)} shortcuts to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export shortcuts: {e}")
            return False
    
    def import_shortcuts(self, file_path: str, merge: bool = True, 
                        category: str = "imported") -> bool:
        """
        导入快捷键配置
        
        Args:
            file_path: 导入文件路径
            merge: 是否合并（否则替换）
            category: 导入的快捷键类别
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Import file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                shortcuts_data = json.load(f)
            
            imported_count = 0
            failed_count = 0
            
            # 如果不是合并模式，先清理当前用户快捷键
            if not merge:
                user_shortcut_ids = [
                    sid for sid, s in self.shortcuts.items()
                    if s.category in ["user", "custom"]
                ]
                for shortcut_id in user_shortcut_ids:
                    self.unregister_shortcut(shortcut_id)
            
            # 导入快捷键
            for shortcut_data in shortcuts_data:
                # 更新类别
                shortcut_data["category"] = category
                
                # 确保有ID
                if "id" not in shortcut_data:
                    shortcut_data["id"] = f"imported_{time.time()}_{imported_count}"
                
                # 注册快捷键
                if self._register_shortcut_from_dict(shortcut_data, category):
                    imported_count += 1
                else:
                    failed_count += 1
            
            logger.info(f"Imported {imported_count} shortcuts, {failed_count} failed")
            return imported_count > 0
            
        except Exception as e:
            logger.error(f"Failed to import shortcuts: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取快捷键管理器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            total_shortcuts = len(self.shortcuts)
            enabled_shortcuts = len([s for s in self.shortcuts.values() if s.enabled])
            
            category_counts = {}
            for shortcut in self.shortcuts.values():
                category = shortcut.category
                category_counts[category] = category_counts.get(category, 0) + 1
            
            # 计算最常用的快捷键
            top_shortcuts = sorted(
                self.shortcut_usage.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                "total_shortcuts": total_shortcuts,
                "enabled_shortcuts": enabled_shortcuts,
                "category_counts": category_counts,
                "conflicts_detected": len(self.conflicts_detected),
                "current_context": self.current_context,
                "current_application": self.current_application,
                "context_stack_size": len(self.context_stack),
                "top_shortcuts": top_shortcuts
            }
            

