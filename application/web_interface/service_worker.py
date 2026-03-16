"""
Service Worker模块 - Mirexs Web界面

提供服务工作线程功能，包括：
1. 离线缓存管理
2. 网络请求拦截
3. 后台同步
4. 推送通知处理
5. 缓存策略
6. 版本更新管理
"""

import logging
import time
import json
import hashlib
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class CacheStrategy(Enum):
    """缓存策略枚举"""
    CACHE_FIRST = "cache_first"  # 优先使用缓存，失败则网络
    NETWORK_FIRST = "network_first"  # 优先使用网络，失败则缓存
    STALE_WHILE_REVALIDATE = "stale_while_revalidate"  # 使用缓存同时更新
    NETWORK_ONLY = "network_only"  # 只使用网络
    CACHE_ONLY = "cache_only"  # 只使用缓存

class SyncStrategy(Enum):
    """同步策略枚举"""
    ON_DEMAND = "on_demand"  # 按需同步
    PERIODIC = "periodic"  # 定期同步
    ON_CONNECT = "on_connect"  # 连接时同步

@dataclass
class CacheRule:
    """缓存规则"""
    url_pattern: str
    strategy: CacheStrategy
    cache_name: str
    max_age: int = 86400  # 默认1天
    max_entries: int = 100
    version: str = "1.0.0"

@dataclass
class SyncTask:
    """同步任务"""
    id: str
    url: str
    method: str
    data: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    last_attempt: Optional[float] = None

@dataclass
class WorkerConfig:
    """Service Worker配置"""
    # 缓存配置
    cache_rules: List[CacheRule] = field(default_factory=list)
    default_cache_strategy: CacheStrategy = CacheStrategy.STALE_WHILE_REVALIDATE
    
    # 同步配置
    enable_background_sync: bool = True
    sync_strategy: SyncStrategy = SyncStrategy.PERIODIC
    sync_interval: int = 3600  # 1小时
    
    # 推送配置
    enable_push_notifications: bool = True
    push_public_key: Optional[str] = None
    
    # 版本控制
    worker_version: str = "1.0.0"
    skip_waiting: bool = True
    clients_claim: bool = True

class ServiceWorker:
    """
    Service Worker管理器
    
    负责服务工作线程的完整生命周期管理，包括：
    - 安装和激活
    - 请求拦截
    - 缓存管理
    - 后台同步
    - 推送通知
    - 版本更新
    """
    
    def __init__(self, config: Optional[WorkerConfig] = None):
        """
        初始化Service Worker管理器
        
        Args:
            config: Worker配置
        """
        self.config = config or WorkerConfig()
        
        # 状态
        self.is_installed = False
        self.is_active = False
        self.install_time: Optional[float] = None
        self.activate_time: Optional[float] = None
        self.current_version = config.worker_version if config else "1.0.0"
        
        # 缓存
        self.caches: Dict[str, Dict[str, Any]] = {}
        self._init_caches()
        
        # 同步队列
        self.sync_queue: List[SyncTask] = []
        self.is_syncing = False
        
        # 订阅者
        self.push_subscribers: List[str] = []
        
        # 回调函数
        self.on_install: Optional[Callable] = None
        self.on_activate: Optional[Callable] = None
        self.on_fetch: Optional[Callable[[str], Any]] = None
        self.on_sync: Optional[Callable] = None
        self.on_push: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # 添加默认缓存规则
        self._add_default_rules()
        
        logger.info(f"ServiceWorker initialized (v{self.current_version})")
    
    def _init_caches(self):
        """初始化缓存"""
        self.caches = {
            "static": {},
            "api": {},
            "assets": {},
            "offline": {}
        }
    
    def _add_default_rules(self):
        """添加默认缓存规则"""
        if not self.config.cache_rules:
            self.config.cache_rules = [
                # 静态资源
                CacheRule(
                    url_pattern=r"\.(js|css|png|jpg|jpeg|gif|svg|woff2?)$",
                    strategy=CacheStrategy.CACHE_FIRST,
                    cache_name="static",
                    max_age=604800  # 7天
                ),
                # API请求
                CacheRule(
                    url_pattern=r"/api/",
                    strategy=CacheStrategy.NETWORK_FIRST,
                    cache_name="api",
                    max_age=300  # 5分钟
                ),
                # 离线页面
                CacheRule(
                    url_pattern=r"/offline\.html$",
                    strategy=CacheStrategy.CACHE_ONLY,
                    cache_name="offline",
                    max_age=0
                )
            ]
    
    async def install(self):
        """安装Service Worker"""
        logger.info(f"Installing Service Worker v{self.current_version}")
        
        self.is_installed = True
        self.install_time = time.time()
        
        # 预缓存核心资源
        await self._precache_core_assets()
        
        if self.on_install:
            self.on_install()
        
        logger.info("Service Worker installed")
    
    async def _precache_core_assets(self):
        """预缓存核心资源"""
        core_assets = [
            "/",
            "/index.html",
            "/offline.html",
            "/static/js/main.js",
            "/static/css/main.css",
            "/manifest.json"
        ]
        
        for asset in core_assets:
            await self._cache_asset(asset, "static")
        
        logger.info(f"Precached {len(core_assets)} core assets")
    
    async def _cache_asset(self, url: str, cache_name: str):
        """缓存资源"""
        if cache_name not in self.caches:
            self.caches[cache_name] = {}
        
        # 模拟缓存
        self.caches[cache_name][url] = {
            "url": url,
            "cached_at": time.time(),
            "etag": hashlib.md5(url.encode()).hexdigest()[:8]
        }
    
    async def activate(self):
        """激活Service Worker"""
        logger.info(f"Activating Service Worker v{self.current_version}")
        
        self.is_active = True
        self.activate_time = time.time()
        
        # 清理旧缓存
        await self._clean_old_caches()
        
        # 接管所有客户端
        if self.config.clients_claim:
            await self._claim_clients()
        
        if self.on_activate:
            self.on_activate()
        
        logger.info("Service Worker activated")
    
    async def _clean_old_caches(self):
        """清理旧缓存"""
        # 实际实现中会删除过期缓存
        for cache_name, cache in self.caches.items():
            current_time = time.time()
            expired_keys = []
            
            for url, entry in cache.items():
                # 查找对应的缓存规则
                rule = self._find_cache_rule(url)
                if rule and rule.max_age > 0:
                    if current_time - entry.get("cached_at", 0) > rule.max_age:
                        expired_keys.append(url)
            
            for key in expired_keys:
                del cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned {len(expired_keys)} expired entries from {cache_name}")
    
    async def _claim_clients(self):
        """接管所有客户端"""
        logger.debug("Claiming all clients")
        # 实际实现中会调用 clients.claim()
    
    def _find_cache_rule(self, url: str) -> Optional[CacheRule]:
        """查找URL匹配的缓存规则"""
        import re
        for rule in self.config.cache_rules:
            if re.search(rule.url_pattern, url):
                return rule
        return None
    
    async def handle_fetch(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理fetch事件
        
        Args:
            request: 请求对象
        
        Returns:
            响应对象
        """
        url = request.get("url", "")
        method = request.get("method", "GET")
        
        logger.debug(f"Fetch intercepted: {method} {url}")
        
        # 只缓存GET请求
        if method != "GET":
            return await self._network_only(request)
        
        # 查找缓存规则
        rule = self._find_cache_rule(url)
        strategy = rule.strategy if rule else self.config.default_cache_strategy
        
        # 根据策略处理
        if strategy == CacheStrategy.CACHE_FIRST:
            return await self._cache_first(request, rule)
        elif strategy == CacheStrategy.NETWORK_FIRST:
            return await self._network_first(request, rule)
        elif strategy == CacheStrategy.STALE_WHILE_REVALIDATE:
            return await self._stale_while_revalidate(request, rule)
        elif strategy == CacheStrategy.CACHE_ONLY:
            return await self._cache_only(request, rule)
        else:  # NETWORK_ONLY
            return await self._network_only(request)
        
        if self.on_fetch:
            result = self.on_fetch(url)
            if result:
                return result
        
        return {"status": 404, "error": "Not found"}
    
    async def _cache_first(self, request: Dict[str, Any], 
                          rule: Optional[CacheRule]) -> Dict[str, Any]:
        """缓存优先策略"""
        url = request["url"]
        cache_name = rule.cache_name if rule else "default"
        
        # 检查缓存
        if cache_name in self.caches and url in self.caches[cache_name]:
            cached = self.caches[cache_name][url]
            
            # 检查是否过期
            if rule and rule.max_age > 0:
                age = time.time() - cached.get("cached_at", 0)
                if age < rule.max_age:
                    logger.debug(f"Cache hit: {url}")
                    return {
                        "status": 200,
                        "from_cache": True,
                        "url": url,
                        "cached_at": cached["cached_at"]
                    }
            
            # 缓存过期，尝试更新
            return await self._stale_while_revalidate(request, rule)
        
        # 缓存未命中，使用网络
        return await self._network_only(request)
    
    async def _network_first(self, request: Dict[str, Any],
                            rule: Optional[CacheRule]) -> Dict[str, Any]:
        """网络优先策略"""
        # 尝试网络请求
        response = await self._network_only(request)
        
        if response.get("status") == 200:
            # 请求成功，更新缓存
            await self._update_cache(request["url"], response, rule)
            return response
        
        # 网络失败，使用缓存
        return await self._cache_only(request, rule)
    
    async def _stale_while_revalidate(self, request: Dict[str, Any],
                                      rule: Optional[CacheRule]) -> Dict[str, Any]:
        """使用缓存同时更新策略"""
        url = request["url"]
        cache_name = rule.cache_name if rule else "default"
        
        # 返回缓存的版本（即使过期）
        if cache_name in self.caches and url in self.caches[cache_name]:
            # 同时触发后台更新
            await self._schedule_revalidation(url, rule)
            
            logger.debug(f"Stale cache returned: {url}")
            return {
                "status": 200,
                "from_cache": True,
                "stale": True,
                "url": url
            }
        
        # 无缓存，使用网络
        return await self._network_only(request)
    
    async def _cache_only(self, request: Dict[str, Any],
                         rule: Optional[CacheRule]) -> Dict[str, Any]:
        """只使用缓存"""
        url = request["url"]
        cache_name = rule.cache_name if rule else "default"
        
        if cache_name in self.caches and url in self.caches[cache_name]:
            return {
                "status": 200,
                "from_cache": True,
                "url": url
            }
        
        return {"status": 404, "error": "Not in cache"}
    
    async def _network_only(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """只使用网络"""
        # 模拟网络请求
        url = request["url"]
        logger.debug(f"Network request: {url}")
        
        # 这里应该实际发起网络请求
        return {"status": 200, "from_network": True, "url": url}
    
    async def _update_cache(self, url: str, response: Dict[str, Any],
                           rule: Optional[CacheRule]):
        """更新缓存"""
        if not rule:
            return
        
        cache_name = rule.cache_name
        if cache_name not in self.caches:
            self.caches[cache_name] = {}
        
        self.caches[cache_name][url] = {
            "url": url,
            "cached_at": time.time(),
            "response": response,
            "etag": hashlib.md5(url.encode()).hexdigest()[:8]
        }
        
        logger.debug(f"Cache updated: {url}")
    
    async def _schedule_revalidation(self, url: str, rule: Optional[CacheRule]):
        """调度重新验证"""
        # 后台更新任务
        task = SyncTask(
            id=f"revalidate_{int(time.time())}_{hashlib.md5(url.encode()).hexdigest()[:8]}",
            url=url,
            method="GET"
        )
        self.sync_queue.append(task)
        logger.debug(f"Revalidation scheduled: {url}")
    
    async def add_to_sync_queue(self, task: SyncTask):
        """
        添加任务到同步队列
        
        Args:
            task: 同步任务
        """
        self.sync_queue.append(task)
        logger.debug(f"Task added to sync queue: {task.id}")
        
        # 触发同步
        if self.config.enable_background_sync:
            await self.sync()
    
    async def sync(self):
        """执行同步"""
        if self.is_syncing or not self.sync_queue:
            return
        
        self.is_syncing = True
        logger.info(f"Starting sync of {len(self.sync_queue)} tasks")
        
        try:
            successful = []
            failed = []
            
            for task in self.sync_queue[:]:
                try:
                    # 执行同步请求
                    success = await self._execute_sync_task(task)
                    
                    if success:
                        successful.append(task)
                        self.sync_queue.remove(task)
                    else:
                        task.retry_count += 1
                        task.last_attempt = time.time()
                        
                        if task.retry_count >= task.max_retries:
                            failed.append(task)
                            self.sync_queue.remove(task)
                            logger.warning(f"Task {task.id} failed after {task.max_retries} attempts")
                
                except Exception as e:
                    logger.error(f"Error syncing task {task.id}: {e}")
                    task.retry_count += 1
            
            logger.info(f"Sync completed: {len(successful)} succeeded, {len(failed)} failed")
            
            if self.on_sync:
                self.on_sync()
                
        finally:
            self.is_syncing = False
    
    async def _execute_sync_task(self, task: SyncTask) -> bool:
        """执行同步任务"""
        logger.debug(f"Executing sync task: {task.id} ({task.url})")
        
        # 模拟网络请求
        import random
        time.sleep(0.5)
        return random.random() > 0.2  # 80%成功率
    
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
        
        notification = {
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": time.time()
        }
        
        if self.on_push:
            self.on_push(notification)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存信息
        """
        return {
            cache_name: {
                "size": len(cache),
                "entries": list(cache.keys())
            }
            for cache_name, cache in self.caches.items()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Service Worker状态
        
        Returns:
            状态字典
        """
        return {
            "version": self.current_version,
            "is_installed": self.is_installed,
            "is_active": self.is_active,
            "install_time": self.install_time,
            "activate_time": self.activate_time,
            "cache_rules": len(self.config.cache_rules),
            "cache_info": self.get_cache_info(),
            "sync_queue_size": len(self.sync_queue),
            "push_subscribers": len(self.push_subscribers)
        }
    
    async def skip_waiting(self):
        """跳过等待"""
        if self.config.skip_waiting:
            logger.info("Skipping waiting")
            # 实际实现中会调用 skipWaiting()
    
    async def update(self, new_version: str):
        """
        更新Service Worker
        
        Args:
            new_version: 新版本号
        """
        logger.info(f"Updating Service Worker: {self.current_version} -> {new_version}")
        
        self.current_version = new_version
        
        # 重新安装
        await self.install()
        await self.activate()
    
    async def shutdown(self):
        """关闭Service Worker"""
        logger.info("Shutting down ServiceWorker...")
        
        # 保存同步队列
        if self.sync_queue:
            logger.info(f"Preserving {len(self.sync_queue)} pending sync tasks")
        
        self.is_active = False
        logger.info("ServiceWorker shutdown completed")

# 单例模式实现
_service_worker_instance: Optional[ServiceWorker] = None

def get_service_worker(config: Optional[WorkerConfig] = None) -> ServiceWorker:
    """
    获取Service Worker单例
    
    Args:
        config: Worker配置
    
    Returns:
        Service Worker实例
    """
    global _service_worker_instance
    if _service_worker_instance is None:
        _service_worker_instance = ServiceWorker(config)
    return _service_worker_instance

