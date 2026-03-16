"""
Webhook处理模块 - Mirexs API网关

提供Webhook处理功能，包括：
1. Webhook注册
2. 事件分发
3. 重试机制
4. 签名验证
5. 负载均衡
"""

import logging
import time
import json
import hmac
import hashlib
import threading
import requests
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class WebhookEvent(Enum):
    """Webhook事件类型枚举"""
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_STATUS_CHANGED = "device.status_changed"
    
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    
    SYNC_STARTED = "sync.started"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"
    
    ALERT_TRIGGERED = "alert.triggered"
    ALERT_RESOLVED = "alert.resolved"
    
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    CUSTOM = "custom"

class WebhookStatus(Enum):
    """Webhook状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    PENDING = "pending"

@dataclass
class WebhookSubscription:
    """Webhook订阅"""
    id: str
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None
    status: WebhookStatus = WebhookStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    last_triggered: Optional[float] = None
    last_response: Optional[int] = None
    failure_count: int = 0
    max_retries: int = 3
    timeout: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebhookDelivery:
    """Webhook投递记录"""
    id: str
    subscription_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    timestamp: float
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = False

@dataclass
class WebhookConfig:
    """Webhook配置"""
    # 服务器配置
    port: int = 8080
    host: str = "0.0.0.0"
    
    # 投递配置
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    retry_backoff: float = 2.0
    timeout: int = 10  # 秒
    
    # 队列配置
    queue_size: int = 1000
    worker_threads: int = 5
    
    # 安全配置
    require_signature: bool = True
    signature_header: str = "X-Webhook-Signature"
    allowed_ips: List[str] = field(default_factory=list)

class WebhookHandler:
    """
    Webhook处理器
    
    负责Webhook的注册、触发和投递。
    """
    
    def __init__(self, config: Optional[WebhookConfig] = None):
        """
        初始化Webhook处理器
        
        Args:
            config: Webhook配置
        """
        self.config = config or WebhookConfig()
        
        # 订阅管理
        self.subscriptions: Dict[str, WebhookSubscription] = {}
        self.events_subscriptions: Dict[WebhookEvent, List[str]] = {}
        
        # 投递队列
        self.delivery_queue: List[WebhookDelivery] = []
        self.delivery_history: List[WebhookDelivery] = []
        
        # 工作线程
        self.workers: List[threading.Thread] = []
        self.stop_workers = threading.Event()
        
        # 统计
        self.stats = {
            "total_deliveries": 0,
            "successful_deliveries": 0,
            "failed_deliveries": 0,
            "retried_deliveries": 0,
            "active_subscriptions": 0
        }
        
        # 启动工作线程
        self._start_workers()
        
        logger.info("WebhookHandler initialized")
    
    def _start_workers(self):
        """启动工作线程"""
        def worker_loop(worker_id: int):
            logger.debug(f"Webhook worker {worker_id} started")
            
            while not self.stop_workers.is_set():
                try:
                    self._process_next_delivery()
                    self.stop_workers.wait(1)
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
            
            logger.debug(f"Webhook worker {worker_id} stopped")
        
        for i in range(self.config.worker_threads):
            worker = threading.Thread(target=worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.debug(f"Started {self.config.worker_threads} webhook workers")
    
    def _process_next_delivery(self):
        """处理下一个投递"""
        if not self.delivery_queue:
            return
        
        delivery = self.delivery_queue.pop(0)
        self._deliver_webhook(delivery)
    
    def _deliver_webhook(self, delivery: WebhookDelivery):
        """投递Webhook"""
        subscription = self.subscriptions.get(delivery.subscription_id)
        
        if not subscription or subscription.status != WebhookStatus.ACTIVE:
            logger.warning(f"Subscription {delivery.subscription_id} not active")
            return
        
        start_time = time.time()
        
        try:
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mirexs-Webhook/1.0",
                **subscription.headers
            }
            
            # 添加签名
            if subscription.secret and self.config.require_signature:
                signature = self._generate_signature(
                    subscription.secret,
                    json.dumps(delivery.payload)
                )
                headers[self.config.signature_header] = signature
            
            # 发送请求
            response = requests.post(
                subscription.url,
                json=delivery.payload,
                headers=headers,
                timeout=subscription.timeout
            )
            
            delivery.response_code = response.status_code
            delivery.response_body = response.text[:1000]  # 限制大小
            delivery.duration_ms = (time.time() - start_time) * 1000
            
            if 200 <= response.status_code < 300:
                delivery.success = True
                subscription.last_response = response.status_code
                subscription.failure_count = 0
                
                self.stats["successful_deliveries"] += 1
                logger.debug(f"Webhook delivered to {subscription.url}: {response.status_code}")
            else:
                delivery.success = False
                subscription.failure_count += 1
                
                self.stats["failed_deliveries"] += 1
                logger.warning(f"Webhook failed to {subscription.url}: {response.status_code}")
                
                # 重试逻辑
                if subscription.failure_count <= subscription.max_retries:
                    self._retry_delivery(delivery, subscription)
            
        except Exception as e:
            delivery.error = str(e)
            delivery.duration_ms = (time.time() - start_time) * 1000
            delivery.success = False
            
            subscription.failure_count += 1
            
            self.stats["failed_deliveries"] += 1
            logger.error(f"Webhook error to {subscription.url}: {e}")
            
            # 重试逻辑
            if subscription.failure_count <= subscription.max_retries:
                self._retry_delivery(delivery, subscription)
        
        finally:
            # 更新订阅状态
            subscription.last_triggered = time.time()
            
            # 记录历史
            self.delivery_history.append(delivery)
            if len(self.delivery_history) > 1000:
                self.delivery_history = self.delivery_history[-1000:]
            
            self.stats["total_deliveries"] += 1
    
    def _retry_delivery(self, delivery: WebhookDelivery, subscription: WebhookSubscription):
        """重试投递"""
        delay = self.config.retry_delay * (self.config.retry_backoff ** (subscription.failure_count - 1))
        
        logger.info(f"Scheduling retry for {subscription.url} in {delay}s (attempt {subscription.failure_count})")
        
        def retry():
            time.sleep(delay)
            self.stats["retried_deliveries"] += 1
            self.trigger(delivery.event, delivery.payload, subscription.id)
        
        thread = threading.Thread(target=retry, daemon=True)
        thread.start()
    
    def _generate_signature(self, secret: str, payload: str) -> str:
        """生成签名"""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def register(self, url: str, events: List[WebhookEvent],
                secret: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None,
                metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        注册Webhook订阅
        
        Args:
            url: Webhook URL
            events: 订阅的事件列表
            secret: 签名密钥
            headers: 自定义头
            metadata: 元数据
        
        Returns:
            订阅ID
        """
        subscription_id = str(uuid.uuid4())
        
        subscription = WebhookSubscription(
            id=subscription_id,
            url=url,
            events=events,
            secret=secret or str(uuid.uuid4()),
            headers=headers or {},
            metadata=metadata or {}
        )
        
        self.subscriptions[subscription_id] = subscription
        
        # 更新事件索引
        for event in events:
            if event not in self.events_subscriptions:
                self.events_subscriptions[event] = []
            self.events_subscriptions[event].append(subscription_id)
        
        self.stats["active_subscriptions"] += 1
        
        logger.info(f"Webhook registered: {subscription_id} for {url} ({len(events)} events)")
        
        return subscription_id
    
    def unregister(self, subscription_id: str) -> bool:
        """
        注销Webhook订阅
        
        Args:
            subscription_id: 订阅ID
        
        Returns:
            是否成功
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"Subscription {subscription_id} not found")
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        # 从事件索引中移除
        for event in subscription.events:
            if event in self.events_subscriptions:
                if subscription_id in self.events_subscriptions[event]:
                    self.events_subscriptions[event].remove(subscription_id)
        
        # 删除订阅
        del self.subscriptions[subscription_id]
        self.stats["active_subscriptions"] -= 1
        
        logger.info(f"Webhook unregistered: {subscription_id}")
        
        return True
    
    def trigger(self, event: WebhookEvent, payload: Dict[str, Any],
               subscription_id: Optional[str] = None):
        """
        触发Webhook
        
        Args:
            event: 事件类型
            payload: 事件负载
            subscription_id: 指定订阅ID
        """
        if subscription_id:
            # 触发特定订阅
            if subscription_id in self.subscriptions:
                self._queue_delivery(subscription_id, event, payload)
        else:
            # 触发所有订阅该事件的订阅
            for sub_id in self.events_subscriptions.get(event, []):
                self._queue_delivery(sub_id, event, payload)
    
    def _queue_delivery(self, subscription_id: str, event: WebhookEvent,
                       payload: Dict[str, Any]):
        """加入投递队列"""
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            event=event,
            payload=payload,
            timestamp=time.time()
        )
        
        self.delivery_queue.append(delivery)
        
        # 限制队列大小
        if len(self.delivery_queue) > self.config.queue_size:
            self.delivery_queue = self.delivery_queue[-self.config.queue_size:]
    
    def get_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """获取订阅"""
        return self.subscriptions.get(subscription_id)
    
    def get_subscriptions(self, event: Optional[WebhookEvent] = None) -> List[WebhookSubscription]:
        """
        获取订阅列表
        
        Args:
            event: 事件过滤
        
        Returns:
            订阅列表
        """
        if event:
            sub_ids = self.events_subscriptions.get(event, [])
            return [self.subscriptions[sid] for sid in sub_ids if sid in self.subscriptions]
        
        return list(self.subscriptions.values())
    
    def get_delivery_history(self, subscription_id: Optional[str] = None,
                            limit: int = 100) -> List[WebhookDelivery]:
        """
        获取投递历史
        
        Args:
            subscription_id: 订阅ID
            limit: 返回数量
        
        Returns:
            投递记录
        """
        history = self.delivery_history[-limit:]
        
        if subscription_id:
            history = [d for d in history if d.subscription_id == subscription_id]
        
        return history
    
    def update_subscription(self, subscription_id: str, **kwargs) -> bool:
        """
        更新订阅
        
        Args:
            subscription_id: 订阅ID
            **kwargs: 更新字段
        
        Returns:
            是否成功
        """
        if subscription_id not in self.subscriptions:
            logger.warning(f"Subscription {subscription_id} not found")
            return False
        
        subscription = self.subscriptions[subscription_id]
        
        for key, value in kwargs.items():
            if hasattr(subscription, key):
                setattr(subscription, key, value)
        
        logger.info(f"Subscription updated: {subscription_id}")
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Webhook处理器状态
        
        Returns:
            状态字典
        """
        return {
            "subscriptions": {
                "total": len(self.subscriptions),
                "active": self.stats["active_subscriptions"]
            },
            "deliveries": {
                "queued": len(self.delivery_queue),
                "total": self.stats["total_deliveries"],
                "successful": self.stats["successful_deliveries"],
                "failed": self.stats["failed_deliveries"],
                "retried": self.stats["retried_deliveries"]
            },
            "workers": {
                "total": self.config.worker_threads,
                "active": len([w for w in self.workers if w.is_alive()])
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭Webhook处理器"""
        logger.info("Shutting down WebhookHandler...")
        
        self.stop_workers.set()
        
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2)
        
        self.subscriptions.clear()
        self.events_subscriptions.clear()
        self.delivery_queue.clear()
        self.delivery_history.clear()
        
        logger.info("WebhookHandler shutdown completed")

# 单例模式实现
_webhook_handler_instance: Optional[WebhookHandler] = None

def get_webhook_handler(config: Optional[WebhookConfig] = None) -> WebhookHandler:
    """
    获取Webhook处理器单例
    
    Args:
        config: Webhook配置
    
    Returns:
        Webhook处理器实例
    """
    global _webhook_handler_instance
    if _webhook_handler_instance is None:
        _webhook_handler_instance = WebhookHandler(config)
    return _webhook_handler_instance

