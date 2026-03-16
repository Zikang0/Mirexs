"""
WebSocket适配器模块 - Mirexs协议适配器

提供WebSocket协议支持，包括：
1. WebSocket客户端管理
2. 连接管理
3. 消息收发
4. 心跳检测
5. 自动重连
6. 多协议支持
"""

import logging
import time
import json
import threading
import ssl
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

# 尝试导入WebSocket库
try:
    import websocket
    WEBSOCKET_CLIENT_AVAILABLE = True
except ImportError:
    WEBSOCKET_CLIENT_AVAILABLE = False
    logger.warning("websocket-client not available. WebSocket functionality will be limited.")

try:
    import aiohttp
    from aiohttp import web
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available. WebSocket server functionality will be limited.")

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"
    RECONNECTING = "reconnecting"

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"

@dataclass
class WSConnection:
    """WebSocket连接信息"""
    id: str
    url: str
    status: ConnectionStatus
    connected_at: Optional[float] = None
    last_heartbeat: Optional[float] = None
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WSMessage:
    """WebSocket消息"""
    id: str
    type: MessageType
    data: Any
    timestamp: float = field(default_factory=time.time)
    connection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebSocketAdapterConfig:
    """WebSocket适配器配置"""
    # 连接配置
    url: str = "ws://localhost:8080"
    protocols: List[str] = field(default_factory=list)
    timeout: int = 10  # 秒
    
    # 心跳配置
    enable_heartbeat: bool = True
    heartbeat_interval: int = 30  # 秒
    heartbeat_timeout: int = 10  # 秒
    heartbeat_payload: str = "ping"
    
    # 重连配置
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 10
    reconnect_delay: int = 1  # 秒
    max_reconnect_delay: int = 60  # 秒
    reconnect_backoff: float = 2.0
    
    # 消息配置
    max_message_size: int = 1024 * 1024  # 1MB
    message_queue_size: int = 1000
    compression: bool = False
    
    # 安全配置
    use_ssl: bool = False
    verify_ssl: bool = True
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    
    # 代理配置
    proxy_type: Optional[str] = None  # http, socks5
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_auth: Optional[tuple] = None
    
    # 头部信息
    headers: Dict[str, str] = field(default_factory=dict)
    
    # Cookie
    cookies: Dict[str, str] = field(default_factory=dict)

class WebSocketAdapter:
    """
    WebSocket适配器
    
    负责WebSocket协议的客户端连接和消息收发。
    """
    
    def __init__(self, config: Optional[WebSocketAdapterConfig] = None):
        """
        初始化WebSocket适配器
        
        Args:
            config: WebSocket配置
        """
        self.config = config or WebSocketAdapterConfig()
        
        # WebSocket客户端
        self.ws: Optional[websocket.WebSocketApp] = None
        self._init_client()
        
        # 连接信息
        self.connection = WSConnection(
            id=str(uuid.uuid4()),
            url=self.config.url,
            status=ConnectionStatus.DISCONNECTED
        )
        
        # 重连管理
        self.reconnect_attempts = 0
        self._reconnect_timer: Optional[threading.Timer] = None
        self._stop_reconnect = threading.Event()
        
        # 心跳管理
        self._heartbeat_timer: Optional[threading.Timer] = None
        self._last_pong: Optional[float] = None
        
        # 消息队列
        self.send_queue: List[WSMessage] = []
        self.receive_queue: List[WSMessage] = []
        self._send_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 消息处理器
        self.message_handlers: Dict[str, List[Callable]] = {
            "text": [],
            "binary": [],
            "ping": [],
            "pong": [],
            "close": []
        }
        
        # 回调函数
        self.on_connecting: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message: Optional[Callable[[WSMessage], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_reconnecting: Optional[Callable[[int], None]] = None
        self.on_heartbeat: Optional[Callable] = None
        
        # 统计
        self.stats = {
            "connect_count": 0,
            "disconnect_count": 0,
            "reconnect_count": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "heartbeats_sent": 0,
            "heartbeats_received": 0,
            "errors": 0
        }
        
        logger.info(f"WebSocketAdapter initialized for {self.config.url}")
    
    def _init_client(self):
        """初始化WebSocket客户端"""
        if not WEBSOCKET_CLIENT_AVAILABLE:
            logger.warning("websocket-client not available")
            return
        
        try:
            # 创建SSL上下文
            sslopt = {}
            if self.config.use_ssl:
                sslopt = {
                    "cert_reqs": ssl.CERT_REQUIRED if self.config.verify_ssl else ssl.CERT_NONE
                }
                if self.config.ssl_ca_certs:
                    sslopt["ca_certs"] = self.config.ssl_ca_certs
                if self.config.ssl_certfile:
                    sslopt["certfile"] = self.config.ssl_certfile
                if self.config.ssl_keyfile:
                    sslopt["keyfile"] = self.config.ssl_keyfile
            
            # 创建WebSocketApp
            self.ws = websocket.WebSocketApp(
                self.config.url,
                header=[f"{k}: {v}" for k, v in self.config.headers.items()],
                cookie="; ".join([f"{k}={v}" for k, v in self.config.cookies.items()]),
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_ping=self._on_ping,
                on_pong=self._on_pong
            )
            
            logger.debug("WebSocket client initialized")
            
        except Exception as e:
            logger.error(f"Error initializing WebSocket client: {e}")
            self.ws = None
    
    def _on_open(self, ws):
        """连接打开回调"""
        self.connection.status = ConnectionStatus.CONNECTED
        self.connection.connected_at = time.time()
        self.connection.last_heartbeat = time.time()
        self.reconnect_attempts = 0
        self.stats["connect_count"] += 1
        
        logger.info(f"WebSocket connected to {self.config.url}")
        
        # 启动心跳
        if self.config.enable_heartbeat:
            self._start_heartbeat()
        
        # 启动发送线程
        self._start_send_thread()
        
        if self.on_connected:
            self.on_connected()
    
    def _on_message(self, ws, message):
        """消息接收回调"""
        try:
            # 确定消息类型
            if isinstance(message, bytes):
                msg_type = MessageType.BINARY
                data = message
            else:
                msg_type = MessageType.TEXT
                try:
                    # 尝试解析JSON
                    data = json.loads(message)
                except:
                    data = message
            
            ws_message = WSMessage(
                id=str(uuid.uuid4()),
                type=msg_type,
                data=data,
                connection_id=self.connection.id
            )
            
            self.stats["messages_received"] += 1
            if isinstance(message, bytes):
                self.stats["bytes_received"] += len(message)
            else:
                self.stats["bytes_received"] += len(message.encode())
            
            # 放入接收队列
            self.receive_queue.append(ws_message)
            if len(self.receive_queue) > self.config.message_queue_size:
                self.receive_queue.pop(0)
            
            logger.debug(f"Message received: {ws_message.id} ({msg_type.value})")
            
            # 调用通用处理器
            if self.on_message:
                self.on_message(ws_message)
            
            # 调用特定类型处理器
            if msg_type.value in self.message_handlers:
                for handler in self.message_handlers[msg_type.value]:
                    try:
                        handler(ws_message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self.stats["errors"] += 1
    
    def _on_error(self, ws, error):
        """错误回调"""
        error_msg = str(error)
        logger.error(f"WebSocket error: {error_msg}")
        
        self.connection.status = ConnectionStatus.ERROR
        self.stats["errors"] += 1
        
        if self.on_error:
            self.on_error(error_msg)
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭回调"""
        self.connection.status = ConnectionStatus.DISCONNECTED
        self.stats["disconnect_count"] += 1
        
        logger.info(f"WebSocket disconnected (code: {close_status_code}, msg: {close_msg})")
        
        # 停止心跳
        self._stop_heartbeat()
        
        if self.on_disconnected:
            self.on_disconnected()
        
        # 自动重连
        if self.config.auto_reconnect and not self._stop_reconnect.is_set():
            self._schedule_reconnect()
    
    def _on_ping(self, ws, message):
        """Ping回调"""
        logger.debug(f"Ping received: {message}")
        self.connection.last_heartbeat = time.time()
        self.stats["heartbeats_received"] += 1
        
        # 自动响应pong
        if self.ws and self.ws.sock:
            self.ws.sock.pong(message)
    
    def _on_pong(self, ws, message):
        """Pong回调"""
        logger.debug(f"Pong received: {message}")
        self.connection.last_heartbeat = time.time()
        self._last_pong = time.time()
        self.stats["heartbeats_received"] += 1
        
        if self.on_heartbeat:
            self.on_heartbeat()
    
    def _start_heartbeat(self):
        """启动心跳检测"""
        def heartbeat_loop():
            while not self._stop_event.is_set() and self.connection.status == ConnectionStatus.CONNECTED:
                try:
                    # 发送ping
                    if self.ws and self.ws.sock:
                        self.ws.sock.ping(self.config.heartbeat_payload)
                        self.stats["heartbeats_sent"] += 1
                        logger.debug("Heartbeat sent")
                    
                    # 检查超时
                    if self._last_pong:
                        elapsed = time.time() - self._last_pong
                        if elapsed > self.config.heartbeat_timeout:
                            logger.warning(f"Heartbeat timeout after {elapsed:.1f}s")
                            # 触发重连
                            self._schedule_reconnect()
                            break
                    
                    self._stop_event.wait(self.config.heartbeat_interval)
                    
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                    break
        
        self._heartbeat_timer = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_timer.start()
        logger.debug("Heartbeat started")
    
    def _stop_heartbeat(self):
        """停止心跳检测"""
        if self._heartbeat_timer and self._heartbeat_timer.is_alive():
            self._stop_event.set()
            self._heartbeat_timer.join(timeout=2)
    
    def _start_send_thread(self):
        """启动发送线程"""
        def send_loop():
            while not self._stop_event.is_set() and self.connection.status == ConnectionStatus.CONNECTED:
                try:
                    if self.send_queue and self.ws and self.ws.sock:
                        message = self.send_queue.pop(0)
                        self._send_message(message)
                    
                    self._stop_event.wait(0.1)
                    
                except Exception as e:
                    logger.error(f"Send loop error: {e}")
        
        self._send_thread = threading.Thread(target=send_loop, daemon=True)
        self._send_thread.start()
        logger.debug("Send thread started")
    
    def _send_message(self, message: WSMessage):
        """发送单个消息"""
        try:
            if message.type == MessageType.TEXT:
                if isinstance(message.data, (dict, list)):
                    data = json.dumps(message.data)
                else:
                    data = str(message.data)
                self.ws.send(data)
                self.stats["bytes_sent"] += len(data.encode())
            elif message.type == MessageType.BINARY:
                if isinstance(message.data, str):
                    data = message.data.encode()
                else:
                    data = bytes(message.data)
                self.ws.send(data, websocket.ABNF.OPCODE_BINARY)
                self.stats["bytes_sent"] += len(data)
            
            self.stats["messages_sent"] += 1
            logger.debug(f"Message sent: {message.id}")
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.stats["errors"] += 1
            # 重新入队
            self.send_queue.insert(0, message)
    
    def _schedule_reconnect(self):
        """调度重连"""
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = min(
            self.config.reconnect_delay * (self.config.reconnect_backoff ** (self.reconnect_attempts - 1)),
            self.config.max_reconnect_delay
        )
        
        logger.info(f"Scheduling reconnect in {delay:.1f}s (attempt {self.reconnect_attempts})")
        
        if self.on_reconnecting:
            self.on_reconnecting(self.reconnect_attempts)
        
        def reconnect():
            if not self._stop_reconnect.is_set():
                self.connection.status = ConnectionStatus.RECONNECTING
                self.stats["reconnect_count"] += 1
                self.connect()
        
        self._reconnect_timer = threading.Timer(delay, reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
    
    def connect(self) -> bool:
        """
        连接WebSocket服务器
        
        Returns:
            是否成功启动连接
        """
        if not self.ws:
            logger.error("WebSocket client not initialized")
            return False
        
        if self.connection.status == ConnectionStatus.CONNECTED:
            logger.warning("Already connected")
            return False
        
        logger.info(f"Connecting to {self.config.url}...")
        
        self.connection.status = ConnectionStatus.CONNECTING
        
        if self.on_connecting:
            self.on_connecting()
        
        try:
            # 在独立线程中运行WebSocket
            def run_ws():
                self.ws.run_forever(
                    ping_interval=self.config.heartbeat_interval if self.config.enable_heartbeat else None,
                    ping_timeout=self.config.heartbeat_timeout if self.config.enable_heartbeat else None,
                    ping_payload=self.config.heartbeat_payload if self.config.enable_heartbeat else None
                )
            
            thread = threading.Thread(target=run_ws, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection.status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
            return False
    
    def disconnect(self):
        """断开连接"""
        if not self.ws:
            return
        
        if self.connection.status != ConnectionStatus.CONNECTED:
            logger.warning("Not connected")
            return
        
        logger.info("Disconnecting...")
        
        self.connection.status = ConnectionStatus.DISCONNECTING
        
        try:
            self.ws.close()
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
    def send(self, data: Any, msg_type: MessageType = MessageType.TEXT) -> str:
        """
        发送消息
        
        Args:
            data: 消息数据
            msg_type: 消息类型
        
        Returns:
            消息ID
        """
        if self.connection.status != ConnectionStatus.CONNECTED:
            logger.warning("Not connected, message queued")
        
        message = WSMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            data=data,
            connection_id=self.connection.id
        )
        
        self.send_queue.append(message)
        
        # 限制队列大小
        if len(self.send_queue) > self.config.message_queue_size:
            self.send_queue.pop(0)
        
        logger.debug(f"Message queued: {message.id}")
        
        return message.id
    
    def send_text(self, text: str) -> str:
        """
        发送文本消息
        
        Args:
            text: 文本内容
        
        Returns:
            消息ID
        """
        return self.send(text, MessageType.TEXT)
    
    def send_json(self, data: Dict[str, Any]) -> str:
        """
        发送JSON消息
        
        Args:
            data: JSON数据
        
        Returns:
            消息ID
        """
        return self.send(data, MessageType.TEXT)
    
    def send_binary(self, data: bytes) -> str:
        """
        发送二进制消息
        
        Args:
            data: 二进制数据
        
        Returns:
            消息ID
        """
        return self.send(data, MessageType.BINARY)
    
    def add_message_handler(self, msg_type: str, handler: Callable[[WSMessage], None]):
        """
        添加消息处理器
        
        Args:
            msg_type: 消息类型 (text, binary, ping, pong, close)
            handler: 处理函数
        """
        if msg_type in self.message_handlers:
            self.message_handlers[msg_type].append(handler)
            logger.debug(f"Message handler added for {msg_type}")
    
    def remove_message_handler(self, msg_type: str, handler: Callable):
        """
        移除消息处理器
        
        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        if msg_type in self.message_handlers and handler in self.message_handlers[msg_type]:
            self.message_handlers[msg_type].remove(handler)
    
    def get_received_messages(self, count: int = 10) -> List[WSMessage]:
        """
        获取接收到的消息
        
        Args:
            count: 返回数量
        
        Returns:
            消息列表
        """
        return self.receive_queue[-count:]
    
    def get_sent_messages(self, count: int = 10) -> List[WSMessage]:
        """
        获取已发送的消息
        
        Args:
            count: 返回数量
        
        Returns:
            消息列表
        """
        return self.send_queue[-count:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取WebSocket适配器状态
        
        Returns:
            状态字典
        """
        return {
            "available": WEBSOCKET_CLIENT_AVAILABLE,
            "connection": {
                "id": self.connection.id,
                "url": self.connection.url,
                "status": self.connection.status.value,
                "connected_at": self.connection.connected_at,
                "last_heartbeat": self.connection.last_heartbeat
            },
            "queues": {
                "send": len(self.send_queue),
                "receive": len(self.receive_queue)
            },
            "reconnect": {
                "attempts": self.reconnect_attempts,
                "max_attempts": self.config.max_reconnect_attempts
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭WebSocket适配器"""
        logger.info("Shutting down WebSocketAdapter...")
        
        # 停止重连
        self._stop_reconnect.set()
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
        
        # 断开连接
        self.disconnect()
        
        # 停止事件循环
        self._stop_event.set()
        
        # 等待线程结束
        if self._send_thread and self._send_thread.is_alive():
            self._send_thread.join(timeout=2)
        
        if self._heartbeat_timer and self._heartbeat_timer.is_alive():
            self._heartbeat_timer.join(timeout=2)
        
        # 清空队列
        self.send_queue.clear()
        self.receive_queue.clear()
        self.message_handlers.clear()
        
        logger.info("WebSocketAdapter shutdown completed")

# 单例模式实现
_websocket_adapter_instance: Optional[WebSocketAdapter] = None

def get_websocket_adapter(config: Optional[WebSocketAdapterConfig] = None) -> WebSocketAdapter:
    """
    获取WebSocket适配器单例
    
    Args:
        config: WebSocket配置
    
    Returns:
        WebSocket适配器实例
    """
    global _websocket_adapter_instance
    if _websocket_adapter_instance is None:
        _websocket_adapter_instance = WebSocketAdapter(config)
    return _websocket_adapter_instance

