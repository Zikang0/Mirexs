"""
移动通知模块 - Mirexs移动应用程序

提供移动端通知系统功能，包括：
1. 本地通知管理
2. 远程推送通知
3. 通知渠道管理（Android）
4. 通知分组和折叠
5. 通知动作按钮
6. 通知历史和统计
"""

import logging
import time
import uuid
import json
import os
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    """通知优先级枚举"""
    MIN = "min"
    LOW = "low"
    DEFAULT = "default"
    HIGH = "high"
    MAX = "max"

class NotificationImportance(Enum):
    """通知重要性枚举（Android）"""
    NONE = 0
    MIN = 1
    LOW = 2
    DEFAULT = 3
    HIGH = 4
    MAX = 5

class NotificationVisibility(Enum):
    """通知可见性枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    SECRET = "secret"

class NotificationCategory(Enum):
    """通知类别枚举"""
    ALARM = "alarm"
    CALL = "call"
    EMAIL = "email"
    ERROR = "error"
    EVENT = "event"
    MESSAGE = "message"
    PROGRESS = "progress"
    PROMO = "promo"
    RECOMMENDATION = "recommendation"
    REMINDER = "reminder"
    SERVICE = "service"
    SOCIAL = "social"
    STATUS = "status"
    SYSTEM = "system"
    TRANSPORT = "transport"

@dataclass
class NotificationAction:
    """通知动作"""
    id: str
    title: str
    icon: Optional[str] = None
    destructive: bool = False
    authentication_required: bool = False
    foreground: bool = True
    callback: Optional[Callable] = None

@dataclass
class NotificationChannel:
    """通知渠道（Android）"""
    id: str
    name: str
    description: str = ""
    importance: NotificationImportance = NotificationImportance.DEFAULT
    enable_vibration: bool = True
    vibration_pattern: List[int] = field(default_factory=lambda: [0, 500, 200, 500])
    enable_lights: bool = True
    light_color: str = "#007AFF"
    bypass_dnd: bool = False
    lockscreen_visibility: NotificationVisibility = NotificationVisibility.PUBLIC
    show_badge: bool = True
    group_id: Optional[str] = None

@dataclass
class Notification:
    """通知数据"""
    id: str
    title: str
    body: str
    channel_id: str = "default"
    priority: NotificationPriority = NotificationPriority.DEFAULT
    category: NotificationCategory = NotificationCategory.SYSTEM
    
    # 时间相关
    timestamp: float = field(default_factory=time.time)
    scheduled_time: Optional[float] = None
    timeout: Optional[int] = None  # 自动取消时间（秒）
    
    # 显示相关
    icon: Optional[str] = None
    large_icon: Optional[str] = None
    color: Optional[str] = None
    badge_count: Optional[int] = None
    progress: Optional[float] = None  # 0-100
    indeterminate: bool = False
    
    # 交互相关
    actions: List[NotificationAction] = field(default_factory=list)
    click_action: Optional[str] = None
    click_data: Optional[Dict[str, Any]] = None
    group_key: Optional[str] = None
    group_summary: bool = False
    
    # 平台特定
    android_channel_id: Optional[str] = None
    ios_category_id: Optional[str] = None
    ios_thread_id: Optional[str] = None
    
    # 扩展数据
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MobileNotificationsConfig:
    """移动通知配置"""
    # 通用配置
    enable_notifications: bool = True
    enable_sound: bool = True
    enable_vibration: bool = True
    enable_badge: bool = True
    
    # 推送配置
    use_fcm: bool = True  # Android
    use_apns: bool = True  # iOS
    push_server_url: Optional[str] = None
    
    # 通知历史
    max_history_size: int = 100
    save_history: bool = True
    
    # 文件路径
    history_file: str = "notification_history.json"
    channels_file: str = "notification_channels.json"
    data_dir: str = "data/notifications/"

class MobileNotifications:
    """
    移动通知管理器
    
    负责管理移动端的所有通知，包括：
    - 本地通知的创建、显示、取消
    - 远程推送通知处理
    - 通知渠道管理
    - 通知历史记录
    - 通知动作处理
    """
    
    def __init__(self, config: Optional[MobileNotificationsConfig] = None):
        """
        初始化移动通知管理器
        
        Args:
            config: 通知配置
        """
        self.config = config or MobileNotificationsConfig()
        
        # 通知存储
        self.notifications: Dict[str, Notification] = {}
        self.history: List[Dict[str, Any]] = []
        
        # 通知渠道（Android）
        self.channels: Dict[str, NotificationChannel] = {}
        
        # 已调度通知
        self.scheduled_notifications: Dict[str, float] = {}  # id -> trigger_time
        
        # 回调函数
        self.on_notification_received: Optional[Callable[[Notification], None]] = None
        self.on_notification_clicked: Optional[Callable[[Notification, Optional[str]], None]] = None
        self.on_notification_dismissed: Optional[Callable[[Notification], None]] = None
        self.on_action_performed: Optional[Callable[[Notification, NotificationAction], None]] = None
        
        # 创建默认渠道
        self._create_default_channels()
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载历史
        if self.config.save_history:
            self._load_history()
            self._load_channels()
        
        logger.info("MobileNotifications initialized")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _create_default_channels(self):
        """创建默认通知渠道"""
        default_channel = NotificationChannel(
            id="default",
            name="默认通知",
            description="一般通知",
            importance=NotificationImportance.DEFAULT
        )
        self.channels["default"] = default_channel
        
        important_channel = NotificationChannel(
            id="important",
            name="重要通知",
            description="重要消息和提醒",
            importance=NotificationImportance.HIGH
        )
        self.channels["important"] = important_channel
        
        silent_channel = NotificationChannel(
            id="silent",
            name="静默通知",
            description="无打扰通知",
            importance=NotificationImportance.MIN,
            enable_vibration=False,
            enable_lights=False
        )
        self.channels["silent"] = silent_channel
    
    def _load_history(self):
        """加载通知历史"""
        history_path = os.path.join(self.config.data_dir, self.config.history_file)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])
                logger.info(f"Loaded {len(self.history)} notification records")
            except Exception as e:
                logger.error(f"Error loading notification history: {e}")
    
    def _save_history(self):
        """保存通知历史"""
        if not self.config.save_history:
            return
        
        history_path = os.path.join(self.config.data_dir, self.config.history_file)
        try:
            # 限制历史大小
            if len(self.history) > self.config.max_history_size:
                self.history = self.history[-self.config.max_history_size:]
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": self.history,
                    "saved_at": datetime.now().isoformat()
                }, f, indent=2, default=str)
            
            logger.debug(f"Notification history saved to {history_path}")
        except Exception as e:
            logger.error(f"Error saving notification history: {e}")
    
    def _load_channels(self):
        """加载通知渠道"""
        channels_path = os.path.join(self.config.data_dir, self.config.channels_file)
        if os.path.exists(channels_path):
            try:
                with open(channels_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    for channel_data in data.get("channels", []):
                        channel = NotificationChannel(
                            id=channel_data["id"],
                            name=channel_data["name"],
                            description=channel_data.get("description", ""),
                            importance=NotificationImportance(channel_data.get("importance", 3)),
                            enable_vibration=channel_data.get("enable_vibration", True),
                            enable_lights=channel_data.get("enable_lights", True)
                        )
                        self.channels[channel.id] = channel
                
                logger.info(f"Loaded {len(self.channels)} notification channels")
            except Exception as e:
                logger.error(f"Error loading notification channels: {e}")
    
    def _save_channels(self):
        """保存通知渠道"""
        channels_path = os.path.join(self.config.data_dir, self.config.channels_file)
        try:
            data = {
                "channels": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "description": c.description,
                        "importance": c.importance.value,
                        "enable_vibration": c.enable_vibration,
                        "enable_lights": c.enable_lights
                    }
                    for c in self.channels.values()
                ],
                "saved_at": datetime.now().isoformat()
            }
            
            with open(channels_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Notification channels saved to {channels_path}")
        except Exception as e:
            logger.error(f"Error saving notification channels: {e}")
    
    def create_channel(self, channel: NotificationChannel):
        """
        创建通知渠道（Android）
        
        Args:
            channel: 通知渠道
        """
        self.channels[channel.id] = channel
        self._save_channels()
        logger.info(f"Notification channel created: {channel.id} ({channel.name})")
        
        # 触发平台特定创建
        self._trigger_platform_channel_creation(channel)
    
    def delete_channel(self, channel_id: str):
        """
        删除通知渠道
        
        Args:
            channel_id: 渠道ID
        """
        if channel_id in self.channels and channel_id not in ["default", "important", "silent"]:
            del self.channels[channel_id]
            self._save_channels()
            logger.info(f"Notification channel deleted: {channel_id}")
    
    def _trigger_platform_channel_creation(self, channel: NotificationChannel):
        """触发平台特定的渠道创建"""
        # 实际实现中会通过桥接调用原生代码
        logger.debug(f"Platform channel creation triggered for {channel.id}")
    
    def show_notification(self, notification: Notification) -> str:
        """
        显示通知
        
        Args:
            notification: 通知对象
        
        Returns:
            通知ID
        """
        if not self.config.enable_notifications:
            logger.warning("Notifications are disabled")
            return notification.id
        
        # 生成ID（如果未提供）
        if not notification.id:
            notification.id = str(uuid.uuid4())
        
        # 设置渠道（如果未指定）
        if not notification.channel_id:
            notification.channel_id = "default"
        
        # 存储通知
        self.notifications[notification.id] = notification
        
        # 添加到历史
        self._add_to_history(notification, "shown")
        
        logger.info(f"Notification shown: {notification.id} - {notification.title}")
        
        # 触发平台特定显示
        self._show_platform_notification(notification)
        
        # 触发回调
        if self.on_notification_received:
            self.on_notification_received(notification)
        
        # 如果设置了超时，调度自动取消
        if notification.timeout:
            self._schedule_timeout(notification.id, notification.timeout)
        
        return notification.id
    
    def _show_platform_notification(self, notification: Notification):
        """触发平台特定的通知显示"""
        # 实际实现中会通过桥接调用原生代码
        logger.debug(f"Platform notification triggered for {notification.id}")
    
    def schedule_notification(self, notification: Notification, trigger_time: datetime) -> str:
        """
        调度通知
        
        Args:
            notification: 通知对象
            trigger_time: 触发时间
        
        Returns:
            通知ID
        """
        notification.scheduled_time = trigger_time.timestamp()
        notification_id = self.show_notification(notification)
        
        self.scheduled_notifications[notification_id] = trigger_time.timestamp()
        
        logger.info(f"Notification scheduled: {notification_id} at {trigger_time}")
        
        return notification_id
    
    def cancel_notification(self, notification_id: str):
        """
        取消通知
        
        Args:
            notification_id: 通知ID
        """
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            
            # 从已调度中移除
            if notification_id in self.scheduled_notifications:
                del self.scheduled_notifications[notification_id]
            
            # 添加到历史
            self._add_to_history(notification, "cancelled")
            
            # 从激活中移除
            del self.notifications[notification_id]
            
            logger.info(f"Notification cancelled: {notification_id}")
            
            # 触发平台特定取消
            self._cancel_platform_notification(notification_id)
    
    def _cancel_platform_notification(self, notification_id: str):
        """触发平台特定的通知取消"""
        logger.debug(f"Platform notification cancelled for {notification_id}")
    
    def cancel_all(self):
        """取消所有通知"""
        for notification_id in list(self.notifications.keys()):
            self.cancel_notification(notification_id)
        
        logger.info("All notifications cancelled")
    
    def _schedule_timeout(self, notification_id: str, timeout_seconds: int):
        """调度通知超时取消"""
        def timeout_handler():
            import time
            time.sleep(timeout_seconds)
            if notification_id in self.notifications:
                self.cancel_notification(notification_id)
        
        import threading
        thread = threading.Thread(target=timeout_handler, daemon=True)
        thread.start()
    
    def _add_to_history(self, notification: Notification, action: str):
        """添加到历史记录"""
        if not self.config.save_history:
            return
        
        history_entry = {
            "id": notification.id,
            "title": notification.title,
            "body": notification.body,
            "action": action,
            "timestamp": time.time(),
            "channel_id": notification.channel_id,
            "category": notification.category.value if notification.category else None
        }
        
        self.history.append(history_entry)
        
        # 限制历史大小
        if len(self.history) > self.config.max_history_size:
            self.history = self.history[-self.config.max_history_size:]
        
        self._save_history()
    
    def handle_notification_click(self, notification_id: str, action_id: Optional[str] = None):
        """
        处理通知点击
        
        Args:
            notification_id: 通知ID
            action_id: 动作ID
        """
        if notification_id not in self.notifications:
            logger.warning(f"Notification not found: {notification_id}")
            return
        
        notification = self.notifications[notification_id]
        
        # 添加到历史
        self._add_to_history(notification, f"clicked:{action_id}" if action_id else "clicked")
        
        logger.info(f"Notification clicked: {notification_id}, action: {action_id}")
        
        # 触发回调
        if action_id:
            # 查找动作
            for action in notification.actions:
                if action.id == action_id:
                    if action.callback:
                        action.callback()
                    if self.on_action_performed:
                        self.on_action_performed(notification, action)
                    break
        else:
            # 点击通知本身
            if notification.click_action and self.on_notification_clicked:
                self.on_notification_clicked(notification, None)
    
    def handle_notification_dismiss(self, notification_id: str):
        """
        处理通知消除
        
        Args:
            notification_id: 通知ID
        """
        if notification_id in self.notifications:
            notification = self.notifications[notification_id]
            
            self._add_to_history(notification, "dismissed")
            
            if self.on_notification_dismissed:
                self.on_notification_dismissed(notification)
            
            # 从激活中移除
            del self.notifications[notification_id]
            
            logger.info(f"Notification dismissed: {notification_id}")
    
    def get_active_notifications(self) -> List[Dict[str, Any]]:
        """
        获取激活中的通知
        
        Returns:
            通知列表
        """
        return [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "channel_id": n.channel_id,
                "priority": n.priority.value,
                "timestamp": n.timestamp
            }
            for n in self.notifications.values()
        ]
    
    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取通知历史
        
        Args:
            limit: 返回条数
        
        Returns:
            历史记录列表
        """
        return self.history[-limit:]
    
    def update_badge_count(self, count: int):
        """
        更新应用图标角标
        
        Args:
            count: 角标数字
        """
        logger.info(f"Updating badge count to {count}")
        self._update_platform_badge(count)
    
    def _update_platform_badge(self, count: int):
        """更新平台特定的角标"""
        logger.debug(f"Platform badge updated to {count}")
    
    def register_push_token(self, token: str, platform: str):
        """
        注册推送令牌
        
        Args:
            token: 推送令牌
            platform: 平台 (fcm/apns)
        """
        logger.info(f"Push token registered for {platform}: {token[:16]}...")
        
        # 存储令牌
        if platform == "fcm":
            self.fcm_token = token
        elif platform == "apns":
            self.apns_token = token
        
        # 发送到服务器
        self._send_token_to_server(token, platform)
    
    def _send_token_to_server(self, token: str, platform: str):
        """发送令牌到服务器"""
        if self.config.push_server_url:
            # 实际实现中会调用API
            logger.debug(f"Sending {platform} token to server: {self.config.push_server_url}")
    
    def handle_remote_notification(self, payload: Dict[str, Any]):
        """
        处理远程推送通知
        
        Args:
            payload: 推送数据
        """
        logger.info(f"Remote notification received: {payload.get('title', 'No title')}")
        
        # 解析推送数据
        title = payload.get("title", "新消息")
        body = payload.get("body", "")
        
        notification = Notification(
            id=payload.get("notification_id", str(uuid.uuid4())),
            title=title,
            body=body,
            data=payload.get("data", {})
        )
        
        self.show_notification(notification)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取通知管理器状态
        
        Returns:
            状态字典
        """
        return {
            "enabled": self.config.enable_notifications,
            "active_count": len(self.notifications),
            "scheduled_count": len(self.scheduled_notifications),
            "channels_count": len(self.channels),
            "history_size": len(self.history),
            "has_fcm_token": hasattr(self, 'fcm_token'),
            "has_apns_token": hasattr(self, 'apns_token')
        }
    
    def shutdown(self):
        """关闭通知管理器"""
        logger.info("Shutting down MobileNotifications...")
        
        # 取消所有通知
        self.cancel_all()
        
        # 保存历史
        if self.config.save_history:
            self._save_history()
            self._save_channels()
        
        logger.info("MobileNotifications shutdown completed")

# 单例模式实现
_mobile_notifications_instance: Optional[MobileNotifications] = None

def get_mobile_notifications(config: Optional[MobileNotificationsConfig] = None) -> MobileNotifications:
    """
    获取移动通知管理器单例
    
    Args:
        config: 通知配置
    
    Returns:
        移动通知管理器实例
    """
    global _mobile_notifications_instance
    if _mobile_notifications_instance is None:
        _mobile_notifications_instance = MobileNotifications(config)
    return _mobile_notifications_instance

