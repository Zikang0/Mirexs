"""
渐进式Web应用模块 - Mirexs Web界面

提供PWA功能实现，包括：
1. 应用清单(manifest.json)
2. 离线支持
3. 添加到主屏幕
4. 推送通知
5. 后台同步
6. 应用更新
"""

import logging
import time
import json
import hashlib
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class DisplayMode(Enum):
    """显示模式枚举"""
    FULLSCREEN = "fullscreen"
    STANDALONE = "standalone"
    MINIMAL_UI = "minimal-ui"
    BROWSER = "browser"

class OrientationLock(Enum):
    """屏幕方向锁定枚举"""
    ANY = "any"
    NATURAL = "natural"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    PORTRAIT_PRIMARY = "portrait-primary"
    PORTRAIT_SECONDARY = "portrait-secondary"

@dataclass
class Icon:
    """图标定义"""
    src: str
    sizes: str
    type: str
    purpose: str = "any"

@dataclass
class Screenshot:
    """截图定义"""
    src: str
    sizes: str
    type: str
    platform: Optional[str] = None
    label: Optional[str] = None

@dataclass
class RelatedApplication:
    """相关应用"""
    platform: str
    url: str
    id: Optional[str] = None

@dataclass
class PWAConfig:
    """PWA配置"""
    # 基本信息
    name: str = "Mirexs"
    short_name: str = "Mirexs"
    description: str = "情感化数字生命体伴侣"
    
    # 图标和截图
    icons: List[Icon] = field(default_factory=list)
    screenshots: List[Screenshot] = field(default_factory=list)
    
    # 主题
    theme_color: str = "#007AFF"
    background_color: str = "#FFFFFF"
    display: DisplayMode = DisplayMode.STANDALONE
    orientation: OrientationLock = OrientationLock.ANY
    
    # 启动
    start_url: str = "/"
    scope: str = "/"
    
    # 功能
    prefer_related_applications: bool = False
    related_applications: List[RelatedApplication] = field(default_factory=list)
    
    # 缓存
    cache_version: str = "1.0.0"
    cache_name: str = "mirexs-cache"
    offline_page: str = "/offline.html"
    
    # 推送
    gcm_sender_id: Optional[str] = None
    gcm_api_key: Optional[str] = None

@dataclass
class AppUpdateInfo:
    """应用更新信息"""
    version: str
    release_notes: str
    published_at: str
    update_url: str
    size: int

class ProgressiveWebApp:
    """
    渐进式Web应用管理器
    
    负责PWA的完整生命周期管理，包括：
    - 应用清单生成
    - 离线缓存
    - 应用安装
    - 版本更新
    - 推送通知
    """
    
    def __init__(self, config: Optional[PWAConfig] = None):
        """
        初始化PWA管理器
        
        Args:
            config: PWA配置
        """
        self.config = config or PWAConfig()
        
        # 添加默认图标
        self._add_default_icons()
        
        # 状态
        self.is_installed = False
        self.is_offline_ready = False
        self.install_time: Optional[float] = None
        self.current_version = config.cache_version if config else "1.0.0"
        
        # 缓存状态
        self.cached_urls: List[str] = []
        self.cache_size: int = 0
        
        # 更新信息
        self.update_available: bool = False
        self.update_info: Optional[AppUpdateInfo] = None
        
        # 订阅者
        self.push_subscribers: List[str] = []
        
        # 回调函数
        self.on_installed: Optional[Callable] = None
        self.on_update_available: Optional[Callable[[AppUpdateInfo], None]] = None
        self.on_offline_ready: Optional[Callable] = None
        self.on_push_received: Optional[Callable[[Dict[str, Any]], None]] = None
        
        logger.info("ProgressiveWebApp initialized")
    
    def _add_default_icons(self):
        """添加默认图标"""
        if not self.config.icons:
            self.config.icons = [
                Icon(src="/icons/icon-72x72.png", sizes="72x72", type="image/png"),
                Icon(src="/icons/icon-96x96.png", sizes="96x96", type="image/png"),
                Icon(src="/icons/icon-128x128.png", sizes="128x128", type="image/png"),
                Icon(src="/icons/icon-144x144.png", sizes="144x144", type="image/png"),
                Icon(src="/icons/icon-152x152.png", sizes="152x152", type="image/png"),
                Icon(src="/icons/icon-192x192.png", sizes="192x192", type="image/png"),
                Icon(src="/icons/icon-384x384.png", sizes="384x384", type="image/png"),
                Icon(src="/icons/icon-512x512.png", sizes="512x512", type="image/png"),
            ]
    
    def generate_manifest(self) -> Dict[str, Any]:
        """
        生成Web应用清单
        
        Returns:
            清单字典
        """
        manifest = {
            "name": self.config.name,
            "short_name": self.config.short_name,
            "description": self.config.description,
            "start_url": self.config.start_url,
            "scope": self.config.scope,
            "display": self.config.display.value,
            "orientation": self.config.orientation.value,
            "theme_color": self.config.theme_color,
            "background_color": self.config.background_color,
            "icons": [
                {
                    "src": icon.src,
                    "sizes": icon.sizes,
                    "type": icon.type,
                    "purpose": icon.purpose
                }
                for icon in self.config.icons
            ]
        }
        
        # 添加截图
        if self.config.screenshots:
            manifest["screenshots"] = [
                {
                    "src": ss.src,
                    "sizes": ss.sizes,
                    "type": ss.type
                }
                for ss in self.config.screenshots
            ]
        
        # 添加相关应用
        if self.config.prefer_related_applications:
            manifest["prefer_related_applications"] = True
            manifest["related_applications"] = [
                {
                    "platform": app.platform,
                    "url": app.url,
                    "id": app.id
                }
                for app in self.config.related_applications
            ]
        
        logger.debug("Manifest generated")
        return manifest
    
    async def install(self):
        """安装PWA"""
        logger.info("Installing PWA...")
        
        self.is_installed = True
        self.install_time = time.time()
        
        # 缓存核心资源
        await self._cache_core_assets()
        
        if self.on_installed:
            self.on_installed()
        
        logger.info("PWA installed successfully")
    
    async def _cache_core_assets(self):
        """缓存核心资源"""
        core_urls = [
            "/",
            "/index.html",
            "/offline.html",
            "/static/js/main.js",
            "/static/css/main.css"
        ]
        
        # 添加到图标
        for icon in self.config.icons:
            core_urls.append(icon.src)
        
        self.cached_urls = core_urls
        self.cache_size = len(core_urls) * 1024 * 100  # 模拟大小
        self.is_offline_ready = True
        
        logger.info(f"Cached {len(core_urls)} core assets")
        
        if self.on_offline_ready:
            self.on_offline_ready()
    
    async def check_for_updates(self) -> Optional[AppUpdateInfo]:
        """
        检查更新
        
        Returns:
            更新信息
        """
        logger.info("Checking for updates...")
        
        # 模拟更新检查
        # 实际实现中会从服务器获取版本信息
        latest_version = "1.1.0"
        
        if latest_version != self.current_version:
            self.update_available = True
            self.update_info = AppUpdateInfo(
                version=latest_version,
                release_notes="新功能：更好的情感交互体验",
                published_at="2025-01-15",
                update_url="/update",
                size=5242880  # 5MB
            )
            
            logger.info(f"Update available: {latest_version}")
            
            if self.on_update_available:
                self.on_update_available(self.update_info)
            
            return self.update_info
        
        logger.info("No updates available")
        return None
    
    async def apply_update(self) -> bool:
        """
        应用更新
        
        Returns:
            是否成功
        """
        if not self.update_available or not self.update_info:
            logger.warning("No update available")
            return False
        
        logger.info(f"Applying update to v{self.update_info.version}")
        
        # 更新版本
        self.current_version = self.update_info.version
        self.update_available = False
        
        # 重新缓存
        await self._cache_core_assets()
        
        logger.info("Update applied successfully")
        return True
    
    async def subscribe_push(self, subscription: Dict[str, Any]) -> bool:
        """
        订阅推送通知
        
        Args:
            subscription: 订阅信息
        
        Returns:
            是否成功
        """
        subscriber_id = hashlib.md5(
            json.dumps(subscription).encode()
        ).hexdigest()
        
        if subscriber_id not in self.push_subscribers:
            self.push_subscribers.append(subscriber_id)
            logger.info(f"Push subscriber added: {subscriber_id}")
        
        return True
    
    async def unsubscribe_push(self, subscription: Dict[str, Any]) -> bool:
        """
        取消订阅推送通知
        
        Args:
            subscription: 订阅信息
        
        Returns:
            是否成功
        """
        subscriber_id = hashlib.md5(
            json.dumps(subscription).encode()
        ).hexdigest()
        
        if subscriber_id in self.push_subscribers:
            self.push_subscribers.remove(subscriber_id)
            logger.info(f"Push subscriber removed: {subscriber_id}")
        
        return True
    
    async def send_push_notification(self, title: str, body: str, 
                                     data: Optional[Dict[str, Any]] = None):
        """
        发送推送通知
        
        Args:
            title: 通知标题
            body: 通知内容
            data: 附加数据
        """
        if not self.push_subscribers:
            logger.debug("No push subscribers")
            return
        
        logger.info(f"Sending push notification to {len(self.push_subscribers)} subscribers")
        
        # 实际实现中会调用推送服务
        notification = {
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": time.time()
        }
        
        if self.on_push_received:
            self.on_push_received(notification)
    
    def get_offline_page(self) -> str:
        """
        获取离线页面
        
        Returns:
            离线页面HTML
        """
        # 返回简单的离线页面
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.config.name} - 离线</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: {self.config.background_color};
                    color: #333;
                }}
                .offline-box {{
                    max-width: 400px;
                    margin: 0 auto;
                    padding: 30px;
                    border-radius: 10px;
                    background: white;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: {self.config.theme_color}; }}
                .icon {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="offline-box">
                <div class="icon">📡</div>
                <h1>网络连接已断开</h1>
                <p>请检查您的网络连接，然后重试。</p>
                <p>您仍然可以访问已缓存的页面。</p>
                <button onclick="window.location.reload()">重试</button>
            </div>
        </body>
        </html>
        """
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取PWA状态
        
        Returns:
            状态字典
        """
        return {
            "name": self.config.name,
            "version": self.current_version,
            "is_installed": self.is_installed,
            "install_time": self.install_time,
            "is_offline_ready": self.is_offline_ready,
            "cached_urls": len(self.cached_urls),
            "cache_size": self.cache_size,
            "update_available": self.update_available,
            "push_subscribers": len(self.push_subscribers),
            "display_mode": self.config.display.value
        }
    
    def shutdown(self):
        """关闭PWA管理器"""
        logger.info("Shutting down ProgressiveWebApp...")
        
        self.cached_urls.clear()
        self.push_subscribers.clear()
        
        logger.info("ProgressiveWebApp shutdown completed")

# 单例模式实现
_pwa_instance: Optional[ProgressiveWebApp] = None

def get_pwa(config: Optional[PWAConfig] = None) -> ProgressiveWebApp:
    """
    获取PWA单例
    
    Args:
        config: PWA配置
    
    Returns:
        PWA实例
    """
    global _pwa_instance
    if _pwa_instance is None:
        _pwa_instance = ProgressiveWebApp(config)
    return _pwa_instance

