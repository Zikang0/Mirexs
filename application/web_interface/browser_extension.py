"""
浏览器扩展模块 - Mirexs Web界面

提供浏览器扩展插件功能，包括：
1. 扩展安装和更新
2. 浏览器API集成
3. 页面内容脚本
4. 后台脚本
5. 跨域请求处理
6. 浏览器存储
"""

import logging
import time
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class BrowserType(Enum):
    """浏览器类型枚举"""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    OPERA = "opera"

class ExtensionPermission(Enum):
    """扩展权限枚举"""
    STORAGE = "storage"
    TABS = "tabs"
    NOTIFICATIONS = "notifications"
    WEB_REQUEST = "webRequest"
    COOKIES = "cookies"
    ACTIVE_TAB = "activeTab"
    CONTEXT_MENUS = "contextMenus"
    CLIPBOARD_READ = "clipboardRead"
    CLIPBOARD_WRITE = "clipboardWrite"

@dataclass
class ExtensionConfig:
    """浏览器扩展配置"""
    # 扩展信息
    extension_id: str = "com.mirexs.extension"
    name: str = "Mirexs Assistant"
    version: str = "1.0.0"
    description: str = "Mirexs数字生命体浏览器助手"
    
    # 浏览器支持
    supported_browsers: List[BrowserType] = field(default_factory=lambda: [
        BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.EDGE
    ])
    
    # 权限
    permissions: List[ExtensionPermission] = field(default_factory=lambda: [
        ExtensionPermission.STORAGE,
        ExtensionPermission.TABS,
        ExtensionPermission.NOTIFICATIONS,
        ExtensionPermission.CONTEXT_MENUS
    ])
    
    # 脚本配置
    content_scripts: List[Dict[str, Any]] = field(default_factory=list)
    background_scripts: List[str] = field(default_factory=list)
    
    # UI配置
    popup_html: str = "popup.html"
    options_html: str = "options.html"
    default_icon: Dict[str, str] = field(default_factory=lambda: {
        "16": "icons/icon16.png",
        "48": "icons/icon48.png",
        "128": "icons/icon128.png"
    })

@dataclass
class TabInfo:
    """标签页信息"""
    tab_id: int
    url: str
    title: str
    favicon: Optional[str] = None
    active: bool = False
    window_id: int = 0

class BrowserExtension:
    """
    浏览器扩展主类
    
    负责浏览器插件的完整生命周期管理，包括：
    - 扩展安装和更新
    - 浏览器API调用
    - 内容脚本管理
    - 后台任务
    - 跨域通信
    """
    
    def __init__(self, config: Optional[ExtensionConfig] = None):
        """
        初始化浏览器扩展
        
        Args:
            config: 扩展配置
        """
        self.config = config or ExtensionConfig()
        self.browser_type = self._detect_browser()
        
        # 扩展状态
        self.is_installed = False
        self.is_enabled = True
        self.install_time: Optional[float] = None
        
        # 存储
        self.storage: Dict[str, Any] = {}
        
        # 标签页
        self.tabs: Dict[int, TabInfo] = {}
        self.active_tab_id: Optional[int] = None
        
        # 上下文菜单
        self.context_menu_items: Dict[str, Dict[str, Any]] = {}
        
        # 回调函数
        self.on_installed: Optional[Callable] = None
        self.on_enabled: Optional[Callable] = None
        self.on_disabled: Optional[Callable] = None
        self.on_uninstalled: Optional[Callable] = None
        self.on_tab_updated: Optional[Callable[[TabInfo], None]] = None
        self.on_tab_activated: Optional[Callable[[TabInfo], None]] = None
        
        logger.info(f"BrowserExtension initialized for {self.browser_type.value}")
    
    def _detect_browser(self) -> BrowserType:
        """检测当前浏览器"""
        # 实际实现中会通过navigator.userAgent检测
        return BrowserType.CHROME
    
    def install(self):
        """安装扩展"""
        logger.info(f"Installing extension v{self.config.version}")
        
        self.is_installed = True
        self.install_time = time.time()
        
        # 创建默认存储
        self._init_storage()
        
        # 注册上下文菜单
        self._register_context_menus()
        
        if self.on_installed:
            self.on_installed()
        
        logger.info("Extension installed successfully")
    
    def _init_storage(self):
        """初始化存储"""
        self.storage = {
            "settings": {
                "enabled": True,
                "notifications": True,
                "theme": "system"
            },
            "user_preferences": {},
            "installed_at": self.install_time
        }
        self._save_storage()
    
    def _register_context_menus(self):
        """注册上下文菜单"""
        self.create_context_menu_item(
            item_id="analyze_page",
            title="使用Mirexs分析页面",
            contexts=["page"]
        )
        
        self.create_context_menu_item(
            item_id="summarize",
            title="总结页面内容",
            contexts=["selection"]
        )
        
        self.create_context_menu_item(
            item_id="translate",
            title="翻译选中文本",
            contexts=["selection"]
        )
    
    def uninstall(self):
        """卸载扩展"""
        logger.info("Uninstalling extension")
        
        self.is_installed = False
        
        # 清理存储
        self.storage.clear()
        
        if self.on_uninstalled:
            self.on_uninstalled()
    
    def enable(self):
        """启用扩展"""
        self.is_enabled = True
        logger.info("Extension enabled")
        
        if self.on_enabled:
            self.on_enabled()
    
    def disable(self):
        """禁用扩展"""
        self.is_enabled = False
        logger.info("Extension disabled")
        
        if self.on_disabled:
            self.on_disabled()
    
    def create_context_menu_item(self, item_id: str, title: str, 
                                contexts: List[str], parent_id: Optional[str] = None):
        """
        创建上下文菜单项
        
        Args:
            item_id: 菜单项ID
            title: 显示标题
            contexts: 上下文（如["page", "selection"]）
            parent_id: 父菜单ID
        """
        self.context_menu_items[item_id] = {
            "id": item_id,
            "title": title,
            "contexts": contexts,
            "parent_id": parent_id,
            "created_at": time.time()
        }
        
        logger.info(f"Context menu item created: {item_id}")
    
    def on_context_menu_clicked(self, item_id: str, tab: TabInfo, 
                                selection: Optional[str] = None):
        """
        上下文菜单点击处理
        
        Args:
            item_id: 菜单项ID
            tab: 当前标签页
            selection: 选中的文本
        """
        logger.info(f"Context menu clicked: {item_id}")
        
        if item_id == "analyze_page":
            self._analyze_page(tab)
        elif item_id == "summarize" and selection:
            self._summarize_text(selection, tab)
        elif item_id == "translate" and selection:
            self._translate_text(selection, tab)
    
    def _analyze_page(self, tab: TabInfo):
        """分析页面"""
        logger.info(f"Analyzing page: {tab.url}")
        # 向内容脚本发送消息
        self.send_message_to_tab(tab.tab_id, {
            "action": "analyze",
            "url": tab.url
        })
    
    def _summarize_text(self, text: str, tab: TabInfo):
        """总结文本"""
        logger.info(f"Summarizing text: {text[:50]}...")
        self.send_message_to_tab(tab.tab_id, {
            "action": "show_summary",
            "text": text[:200] + "..."
        })
    
    def _translate_text(self, text: str, tab: TabInfo):
        """翻译文本"""
        logger.info(f"Translating text: {text[:50]}...")
        self.send_message_to_tab(tab.tab_id, {
            "action": "show_translation",
            "original": text,
            "translated": f"[翻译] {text}"  # 模拟翻译
        })
    
    def send_message_to_tab(self, tab_id: int, message: Dict[str, Any]):
        """
        向标签页发送消息
        
        Args:
            tab_id: 标签页ID
            message: 消息内容
        """
        logger.debug(f"Sending message to tab {tab_id}: {message}")
        # 实际实现中会调用chrome.tabs.sendMessage
    
    def send_message_to_background(self, message: Dict[str, Any]):
        """
        向后台脚本发送消息
        
        Args:
            message: 消息内容
        """
        logger.debug(f"Sending message to background: {message}")
        # 实际实现中会调用chrome.runtime.sendMessage
    
    def on_message_from_content(self, message: Dict[str, Any], tab: TabInfo):
        """
        处理来自内容脚本的消息
        
        Args:
            message: 消息内容
            tab: 来源标签页
        """
        logger.debug(f"Message from content script: {message}")
        
        action = message.get("action")
        if action == "page_loaded":
            self._handle_page_loaded(tab, message.get("data", {}))
        elif action == "user_selection":
            self._handle_user_selection(tab, message.get("text", ""))
    
    def _handle_page_loaded(self, tab: TabInfo, data: Dict[str, Any]):
        """处理页面加载事件"""
        logger.info(f"Page loaded: {tab.url}")
        
        # 更新标签页信息
        if tab.tab_id in self.tabs:
            self.tabs[tab.tab_id].title = data.get("title", tab.title)
    
    def _handle_user_selection(self, tab: TabInfo, text: str):
        """处理用户选择事件"""
        logger.debug(f"User selected text on {tab.url}: {text[:50]}...")
        
        # 如果有选中的文本，显示浮动工具栏
        if text:
            self.send_message_to_tab(tab.tab_id, {
                "action": "show_toolbar",
                "selection": text
            })
    
    def on_tab_updated(self, tab_id: int, change_info: Dict[str, Any], tab: TabInfo):
        """
        标签页更新事件
        
        Args:
            tab_id: 标签页ID
            change_info: 变更信息
            tab: 标签页信息
        """
        self.tabs[tab_id] = tab
        
        if change_info.get("status") == "complete":
            if self.on_tab_updated:
                self.on_tab_updated(tab)
    
    def on_tab_activated(self, tab_id: int, window_id: int):
        """
        标签页激活事件
        
        Args:
            tab_id: 标签页ID
            window_id: 窗口ID
        """
        if tab_id in self.tabs:
            self.active_tab_id = tab_id
            tab = self.tabs[tab_id]
            
            if self.on_tab_activated:
                self.on_tab_activated(tab)
    
    def get_storage(self, key: str, default: Any = None) -> Any:
        """
        获取存储值
        
        Args:
            key: 存储键
            default: 默认值
        
        Returns:
            存储值
        """
        return self.storage.get(key, default)
    
    def set_storage(self, key: str, value: Any):
        """
        设置存储值
        
        Args:
            key: 存储键
            value: 存储值
        """
        self.storage[key] = value
        self._save_storage()
    
    def _save_storage(self):
        """保存存储到浏览器"""
        # 实际实现中会调用chrome.storage.local.set
        logger.debug("Storage saved")
    
    def get_current_tab(self) -> Optional[TabInfo]:
        """
        获取当前标签页
        
        Returns:
            当前标签页信息
        """
        if self.active_tab_id and self.active_tab_id in self.tabs:
            return self.tabs[self.active_tab_id]
        return None
    
    def open_options_page(self):
        """打开选项页面"""
        logger.info("Opening options page")
        # 实际实现中会调用chrome.runtime.openOptionsPage
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取扩展状态
        
        Returns:
            状态字典
        """
        return {
            "name": self.config.name,
            "version": self.config.version,
            "browser": self.browser_type.value,
            "is_installed": self.is_installed,
            "is_enabled": self.is_enabled,
            "install_time": self.install_time,
            "tabs_count": len(self.tabs),
            "active_tab": self.active_tab_id,
            "context_menus": len(self.context_menu_items),
            "storage_size": len(json.dumps(self.storage))
        }
    
    def shutdown(self):
        """关闭扩展"""
        logger.info("Shutting down BrowserExtension...")
        
        # 保存存储
        self._save_storage()
        
        logger.info("BrowserExtension shutdown completed")

# 单例模式实现
_browser_extension_instance: Optional[BrowserExtension] = None

def get_browser_extension(config: Optional[ExtensionConfig] = None) -> BrowserExtension:
    """
    获取浏览器扩展单例
    
    Args:
        config: 扩展配置
    
    Returns:
        浏览器扩展实例
    """
    global _browser_extension_instance
    if _browser_extension_instance is None:
        _browser_extension_instance = BrowserExtension(config)
    return _browser_extension_instance

