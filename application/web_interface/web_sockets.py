"""
WebSocket模块 - Mirexs Web界面

提供WebSocket实时通信功能，包括：
1. 连接管理
2. 消息收发
3. 心跳检测
4. 重连机制
5. 房间管理
6. 广播消息
"""

import logging
import time
import json
import uuid
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from queue import Queue

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    BINARY = "binary"
    PING = "ping"
    PONG = "pong"
    CLOSE = "close"
    ERROR = "error"

@dataclass
class WebSocketMessage:
    """WebSocket消息"""
    id: str
    type: MessageType
    data: Any
    timestamp: float = field(default_factory=time.time)
    room: Optional[str] = None
    sender: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebSocketConnection:
    """WebSocket连接"""
    id: str
    url: str
    state: ConnectionState
    connected_at: Optional[float] = None
    last_heartbeat: Optional[float] = None
    messages_sent: int = 0
    messages_received: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WebSocketConfig:
    """WebSocket配置"""
    # 连接配置
    url: str = "ws://localhost:8000/ws"
    protocols: List[str] = field(default_factory=list)
    auto_connect: bool = True
    
    # 心跳配置
    enable_heartbeat: bool = True
    heartbeat_interval: int = 30  # 秒
    heartbeat_timeout: int = 10  # 秒
    
    # 重连配置
    enable_reconnect: bool = True
    max_reconnect_attempts: int = 10
    reconnect_delay: int = 1  # 秒
    max_reconnect_delay: int = 60  # 秒
    
    # 消息配置
    max_message_size: int = 1024 * 1024  # 1MB
    message_queue_size: int = 1000

class WebSocketManager:
    """
    WebSocket管理器
    
    负责WebSocket连接的生命周期管理，包括：
    - 连接建立和关闭
    - 消息收发
    - 心跳维护
    - 自动重连
    - 房间管理
    - 广播
    """
    
    def __init__(self, config: Optional[WebSocketConfig] = None):
        """
        初始化WebSocket管理器
        
        Args:
            config: WebSocket配置
        """
        self.config = config or WebSocketConfig()
        
        # 连接状态
        self.connection = WebSocketConnection(
            id=str(uuid.uuid4()),
            url=self.config.url,
            state=ConnectionState.DISCONNECTED
        )
        
        # 消息队列
        self.send_queue: Queue = Queue(maxsize=self.config.message_queue_size)
        self.receive_queue: Queue = Queue(maxsize=self.config.message_queue_size)
        
        # 房间管理
        self.rooms: Dict[str, List[str]] = {}  # room_name -> [connection_ids]
        self.my_rooms: List[str] = []
        
        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message: Optional[Callable[[WebSocketMessage], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_room_joined: Optional[Callable[[str], None]] = None
        self.on_room_left: Optional[Callable[[str], None]] = None
        
        # 内部线程
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None
        self._send_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 统计
        self.reconnect_attempts = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0
        
        logger.info(f"WebSocketManager initialized for {self.config.url}")
    
    async def connect(self):
        """建立WebSocket连接"""
        if self.connection.state == ConnectionState.CONNECTED:
            logger.warning("Already connected")
            return
        
        logger.info(f"Connecting to {self.config.url}")
        
        self.connection.state = ConnectionState.CONNECTING
        
        try:
            # 实际实现中会创建真正的WebSocket连接
            # 这里模拟连接成功
            await self._create_connection()
            
            self.connection.state = ConnectionState.CONNECTED
            self.connection.connected_at = time.time()
            self.connection.last_heartbeat = time.time()
            
            logger.info(f"Connected to {self.config.url}")
            
            # 启动心跳
            if self.config.enable_heartbeat:
                self._start_heartbeat()
            
            # 启动收发线程
            self._start_message_threads()
            
            if self.on_connected:
                self.on_connected()
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connection.state = ConnectionState.ERROR
            
            if self.on_error:
                self.on_error(str(e))
            
            # 尝试重连
            if self.config.enable_reconnect:
                await self._schedule_reconnect()
    
    async def _create_connection(self):
        """创建实际连接"""
        # 这里应该使用websockets库创建真实连接
        # 简化实现
        self._mock_connection = True
        await self._handshake()
    
    async def _handshake(self):
        """WebSocket握手"""
        # 模拟握手
        logger.debug("WebSocket handshake completed")
    
    def _start_heartbeat(self):
        """启动心跳检测"""
        def heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    if self.connection.state == ConnectionState.CONNECTED:
                        # 发送ping
                        self._send_ping()
                        
                        # 检查上次心跳
                        if self.connection.last_heartbeat:
                            elapsed = time.time() - self.connection.last_heartbeat
                            if elapsed > self.config.heartbeat_timeout:
                                logger.warning("Heartbeat timeout")
                                # 触发重连
                                self._schedule_reconnect_async()
                    
                    self._stop_event.wait(self.config.heartbeat_interval)
                    
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
        
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.debug("Heartbeat started")
    
    def _send_ping(self):
        """发送ping消息"""
        ping_msg = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.PING,
            data="ping"
        )
        self.send_queue.put(ping_msg)
        logger.debug("Ping sent")
    
    def _start_message_threads(self):
        """启动消息收发线程"""
        # 接收线程
        def receive_loop():
            while not self._stop_event.is_set() and self.connection.state == ConnectionState.CONNECTED:
                try:
                    # 模拟接收消息
                    import random
                    if random.random() < 0.3:  # 30%概率有消息
                        msg = self._mock_receive_message()
                        if msg:
                            self.receive_queue.put(msg)
                            
                            if msg.type == MessageType.PONG:
                                self.connection.last_heartbeat = time.time()
                                logger.debug("Pong received")
                            else:
                                self.total_messages_received += 1
                                self.connection.messages_received += 1
                                
                                if self.on_message:
                                    self.on_message(msg)
                    
                    self._stop_event.wait(0.1)
                    
                except Exception as e:
                    logger.error(f"Receive error: {e}")
        
        # 发送线程
        def send_loop():
            while not self._stop_event.is_set() and self.connection.state == ConnectionState.CONNECTED:
                try:
                    if not self.send_queue.empty():
                        msg = self.send_queue.get_nowait()
                        self._send_message(msg)
                        self.total_messages_sent += 1
                        self.connection.messages_sent += 1
                    
                    self._stop_event.wait(0.1)
                    
                except Exception as e:
                    logger.error(f"Send error: {e}")
        
        self._receive_thread = threading.Thread(target=receive_loop, daemon=True)
        self._send_thread = threading.Thread(target=send_loop, daemon=True)
        self._receive_thread.start()
        self._send_thread.start()
        logger.debug("Message threads started")
    
    def _mock_receive_message(self) -> Optional[WebSocketMessage]:
        """模拟接收消息"""
        import random
        msg_types = [MessageType.TEXT, MessageType.PONG]
        msg_type = random.choice(msg_types)
        
        if msg_type == MessageType.PONG:
            return WebSocketMessage(
                id=str(uuid.uuid4()),
                type=MessageType.PONG,
                data="pong"
            )
        else:
            return WebSocketMessage(
                id=str(uuid.uuid4()),
                type=MessageType.TEXT,
                data={
                    "event": random.choice(["message", "notification", "update"]),
                    "content": f"Sample message {random.randint(1, 100)}"
                }
            )
    
    def _send_message(self, message: WebSocketMessage):
        """发送消息"""
        logger.debug(f"Sending message: {message.id} ({message.type.value})")
        # 实际实现中会通过WebSocket发送
    
    async def disconnect(self):
        """断开连接"""
        logger.info("Disconnecting...")
        
        self.connection.state = ConnectionState.DISCONNECTING
        self._stop_event.set()
        
        # 等待线程结束
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)
        
        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2)
        
        if self._send_thread and self._send_thread.is_alive():
            self._send_thread.join(timeout=2)
        
        # 清理队列
        while not self.send_queue.empty():
            try:
                self.send_queue.get_nowait()
            except:
                pass
        
        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except:
                pass
        
        self.connection.state = ConnectionState.DISCONNECTED
        
        logger.info("Disconnected")
        
        if self.on_disconnected:
            self.on_disconnected()
    
    async def _schedule_reconnect(self):
        """调度重连"""
        if not self.config.enable_reconnect:
            return
        
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        delay = min(
            self.config.reconnect_delay * (2 ** self.reconnect_attempts),
            self.config.max_reconnect_delay
        )
        
        self.reconnect_attempts += 1
        logger.info(f"Scheduling reconnect in {delay}s (attempt {self.reconnect_attempts})")
        
        self.connection.state = ConnectionState.RECONNECTING
        
        # 延迟重连
        self._stop_event.wait(delay)
        
        if self.connection.state != ConnectionState.CONNECTED:
            await self.connect()
    
    def _schedule_reconnect_async(self):
        """异步调度重连"""
        import asyncio
        asyncio.create_task(self._schedule_reconnect())
    
    async def send(self, data: Any, msg_type: MessageType = MessageType.TEXT,
                   room: Optional[str] = None):
        """
        发送消息
        
        Args:
            data: 消息数据
            msg_type: 消息类型
            room: 房间名称
        """
        if self.connection.state != ConnectionState.CONNECTED:
            logger.warning("Not connected, message queued")
        
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=msg_type,
            data=data,
            room=room
        )
        
        self.send_queue.put(message)
        logger.debug(f"Message queued: {message.id}")
    
    async def join_room(self, room: str):
        """
        加入房间
        
        Args:
            room: 房间名称
        """
        if room not in self.my_rooms:
            self.my_rooms.append(room)
            
            # 发送加入房间消息
            await self.send({
                "action": "join",
                "room": room
            })
            
            logger.info(f"Joined room: {room}")
            
            if self.on_room_joined:
                self.on_room_joined(room)
    
    async def leave_room(self, room: str):
        """
        离开房间
        
        Args:
            room: 房间名称
        """
        if room in self.my_rooms:
            self.my_rooms.remove(room)
            
            # 发送离开房间消息
            await self.send({
                "action": "leave",
                "room": room
            })
            
            logger.info(f"Left room: {room}")
            
            if self.on_room_left:
                self.on_room_left(room)
    
    async def broadcast_to_room(self, room: str, data: Any):
        """
        向房间广播消息
        
        Args:
            room: 房间名称
            data: 消息数据
        """
        await self.send(data, room=room)
        logger.debug(f"Broadcast to room {room}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取WebSocket管理器状态
        
        Returns:
            状态字典
        """
        return {
            "connection": {
                "id": self.connection.id,
                "url": self.connection.url,
                "state": self.connection.state.value,
                "connected_at": self.connection.connected_at,
                "last_heartbeat": self.connection.last_heartbeat,
                "messages_sent": self.connection.messages_sent,
                "messages_received": self.connection.messages_received
            },
            "queues": {
                "send_size": self.send_queue.qsize(),
                "receive_size": self.receive_queue.qsize()
            },
            "rooms": {
                "joined": self.my_rooms,
                "total_rooms": len(self.rooms)
            },
            "stats": {
                "total_messages_sent": self.total_messages_sent,
                "total_messages_received": self.total_messages_received,
                "reconnect_attempts": self.reconnect_attempts
            }
        }
    
    async def shutdown(self):
        """关闭WebSocket管理器"""
        logger.info("Shutting down WebSocketManager...")
        
        await self.disconnect()
        
        logger.info("WebSocketManager shutdown completed")

# 单例模式实现
_websocket_manager_instance: Optional[WebSocketManager] = None

def get_websocket_manager(config: Optional[WebSocketConfig] = None) -> WebSocketManager:
    """
    获取WebSocket管理器单例
    
    Args:
        config: WebSocket配置
    
    Returns:
        WebSocket管理器实例
    """
    global _websocket_manager_instance
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager(config)
    return _websocket_manager_instance

