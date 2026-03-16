"""
MQTT适配器模块 - Mirexs协议适配器

提供MQTT协议支持，包括：
1. MQTT客户端管理
2. 发布/订阅
3. QoS支持
4. 遗嘱消息
5. 持久化会话
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 尝试导入MQTT库
try:
    import paho.mqtt.client as mqtt
    PAHO_MQTT_AVAILABLE = True
except ImportError:
    PAHO_MQTT_AVAILABLE = False
    logger.warning("paho-mqtt not available. MQTT functionality will be limited.")

class QoS(Enum):
    """MQTT服务质量枚举"""
    AT_MOST_ONCE = 0  # 最多一次
    AT_LEAST_ONCE = 1  # 至少一次
    EXACTLY_ONCE = 2   # 恰好一次

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"

@dataclass
class MQTTMessage:
    """MQTT消息"""
    topic: str
    payload: Any
    qos: QoS = QoS.AT_MOST_ONCE
    retain: bool = False
    timestamp: float = field(default_factory=time.time)
    properties: Optional[Dict[str, Any]] = None

@dataclass
class MQTTConfig:
    """MQTT配置"""
    # 连接配置
    host: str = "localhost"
    port: int = 1883
    keepalive: int = 60
    clean_session: bool = True
    
    # 认证配置
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    
    # TLS配置
    use_tls: bool = False
    ca_certs: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    
    # 遗嘱消息
    will_topic: Optional[str] = None
    will_payload: Optional[str] = None
    will_qos: QoS = QoS.AT_MOST_ONCE
    will_retain: bool = False
    
    # 重连配置
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    max_reconnect_delay: int = 60
    
    # 订阅配置
    subscriptions: List[str] = field(default_factory=list)
    qos_subscriptions: Dict[str, QoS] = field(default_factory=dict)

class MQTTAdapter:
    """
    MQTT适配器
    
    负责MQTT协议的消息发布和订阅。
    """
    
    def __init__(self, config: Optional[MQTTConfig] = None):
        """
        初始化MQTT适配器
        
        Args:
            config: MQTT配置
        """
        self.config = config or MQTTConfig()
        
        # MQTT客户端
        self.client: Optional[mqtt.Client] = None
        self._init_client()
        
        # 连接状态
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.reconnect_attempts = 0
        
        # 订阅管理
        self.subscriptions: Dict[str, QoS] = {}
        self.message_handlers: Dict[str, List[Callable]] = {}
        
        # 消息队列
        self.message_queue: List[MQTTMessage] = []
        
        # 回调函数
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_message: Optional[Callable[[MQTTMessage], None]] = None
        self.on_subscribe: Optional[Callable[[str, QoS], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "connect_count": 0,
            "reconnect_count": 0,
            "errors": 0
        }
        
        logger.info(f"MQTTAdapter initialized for {self.config.host}:{self.config.port}")
    
    def _init_client(self):
        """初始化MQTT客户端"""
        if not PAHO_MQTT_AVAILABLE:
            logger.warning("paho-mqtt not available, MQTT client disabled")
            return
        
        try:
            # 创建客户端
            client_id = self.config.client_id or f"mirexs_{int(time.time())}"
            self.client = mqtt.Client(
                client_id=client_id,
                clean_session=self.config.clean_session
            )
            
            # 设置认证
            if self.config.username and self.config.password:
                self.client.username_pw_set(
                    self.config.username,
                    self.config.password
                )
            
            # 设置TLS
            if self.config.use_tls:
                self.client.tls_set(
                    ca_certs=self.config.ca_certs,
                    certfile=self.config.certfile,
                    keyfile=self.config.keyfile
                )
            
            # 设置遗嘱
            if self.config.will_topic:
                self.client.will_set(
                    self.config.will_topic,
                    self.config.will_payload,
                    qos=self.config.will_qos.value,
                    retain=self.config.will_retain
                )
            
            # 设置回调
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            self.client.on_subscribe = self._on_subscribe
            self.client.on_unsubscribe = self._on_unsubscribe
            
            logger.debug("MQTT client initialized")
            
        except Exception as e:
            logger.error(f"Error initializing MQTT client: {e}")
            self.client = None
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connection_status = ConnectionStatus.CONNECTED
            self.reconnect_attempts = 0
            self.stats["connect_count"] += 1
            
            logger.info(f"Connected to MQTT broker at {self.config.host}:{self.config.port}")
            
            # 重新订阅
            self._resubscribe()
            
            if self.on_connect:
                self.on_connect()
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error = error_messages.get(rc, f"Unknown error ({rc})")
            logger.error(f"Connection failed: {error}")
            self.connection_status = ConnectionStatus.ERROR
            
            if self.on_error:
                self.on_error(error)
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connection_status = ConnectionStatus.DISCONNECTED
        logger.info(f"Disconnected from MQTT broker (rc: {rc})")
        
        if self.on_disconnect:
            self.on_disconnect()
        
        # 自动重连
        if self.config.auto_reconnect and rc != 0:
            self._schedule_reconnect()
    
    def _on_message(self, client, userdata, msg):
        """消息回调"""
        try:
            # 解析消息
            payload = msg.payload
            try:
                # 尝试解析JSON
                payload = json.loads(payload)
            except:
                pass  # 保持原样
            
            message = MQTTMessage(
                topic=msg.topic,
                payload=payload,
                qos=QoS(msg.qos),
                retain=msg.retain
            )
            
            self.stats["messages_received"] += 1
            self.stats["bytes_received"] += len(msg.payload)
            
            logger.debug(f"Message received on {msg.topic}")
            
            # 调用通用处理器
            if self.on_message:
                self.on_message(message)
            
            # 调用特定主题处理器
            if msg.topic in self.message_handlers:
                for handler in self.message_handlers[msg.topic]:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")
            
            # 调用通配符处理器
            for pattern, handlers in self.message_handlers.items():
                if self._topic_matches(pattern, msg.topic):
                    for handler in handlers:
                        try:
                            handler(message)
                        except Exception as e:
                            logger.error(f"Error in message handler: {e}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """发布回调"""
        logger.debug(f"Message published (mid: {mid})")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """订阅回调"""
        logger.debug(f"Subscribed (mid: {mid}, qos: {granted_qos})")
        
        if self.on_subscribe:
            self.on_subscribe("", QoS(granted_qos[0]) if granted_qos else QoS.AT_MOST_ONCE)
    
    def _on_unsubscribe(self, client, userdata, mid):
        """取消订阅回调"""
        logger.debug(f"Unsubscribed (mid: {mid})")
    
    def _topic_matches(self, subscription: str, topic: str) -> bool:
        """
        检查主题是否匹配订阅
        
        Args:
            subscription: 订阅主题（可能包含通配符）
            topic: 实际主题
        
        Returns:
            是否匹配
        """
        # 简化实现
        if subscription == topic:
            return True
        
        if subscription.endswith('/#'):
            return topic.startswith(subscription[:-2])
        
        return False
    
    def _resubscribe(self):
        """重新订阅所有主题"""
        for topic, qos in self.subscriptions.items():
            self.subscribe(topic, qos)
    
    def _schedule_reconnect(self):
        """调度重连"""
        self.reconnect_attempts += 1
        delay = min(
            self.config.reconnect_delay * (2 ** self.reconnect_attempts),
            self.config.max_reconnect_delay
        )
        
        logger.info(f"Scheduling reconnect in {delay}s (attempt {self.reconnect_attempts})")
        
        def reconnect():
            if self.connection_status != ConnectionStatus.CONNECTED:
                self.connect()
                self.stats["reconnect_count"] += 1
        
        timer = threading.Timer(delay, reconnect)
        timer.daemon = True
        timer.start()
    
    def connect(self) -> bool:
        """
        连接到MQTT代理
        
        Returns:
            是否成功启动连接
        """
        if not self.client:
            logger.error("MQTT client not initialized")
            return False
        
        if self.connection_status == ConnectionStatus.CONNECTED:
            logger.warning("Already connected")
            return False
        
        logger.info(f"Connecting to MQTT broker at {self.config.host}:{self.config.port}...")
        
        self.connection_status = ConnectionStatus.CONNECTING
        
        try:
            self.client.connect(
                self.config.host,
                self.config.port,
                self.config.keepalive
            )
            
            # 启动网络循环
            self.client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
            return False
    
    def disconnect(self):
        """断开连接"""
        if not self.client:
            return
        
        if self.connection_status != ConnectionStatus.CONNECTED:
            logger.warning("Not connected")
            return
        
        logger.info("Disconnecting from MQTT broker...")
        
        self.connection_status = ConnectionStatus.DISCONNECTING
        
        try:
            self.client.loop_stop()
            self.client.disconnect()
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
    def publish(self, topic: str, payload: Any, qos: QoS = QoS.AT_MOST_ONCE,
               retain: bool = False) -> bool:
        """
        发布消息
        
        Args:
            topic: 主题
            payload: 消息内容
            qos: 服务质量
            retain: 是否保留
        
        Returns:
            是否成功
        """
        if not self.client or self.connection_status != ConnectionStatus.CONNECTED:
            logger.warning("Not connected to broker")
            return False
        
        try:
            # 序列化payload
            if isinstance(payload, (dict, list)):
                payload = json.dumps(payload)
            elif not isinstance(payload, (str, bytes)):
                payload = str(payload)
            
            result = self.client.publish(
                topic,
                payload,
                qos=qos.value,
                retain=retain
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.stats["messages_sent"] += 1
                if isinstance(payload, str):
                    self.stats["bytes_sent"] += len(payload.encode())
                elif isinstance(payload, bytes):
                    self.stats["bytes_sent"] += len(payload)
                
                logger.debug(f"Message published to {topic}")
                return True
            else:
                logger.error(f"Publish failed: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False
    
    def subscribe(self, topic: str, qos: QoS = QoS.AT_MOST_ONCE) -> bool:
        """
        订阅主题
        
        Args:
            topic: 主题
            qos: 服务质量
        
        Returns:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            result = self.client.subscribe(topic, qos.value)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscriptions[topic] = qos
                logger.info(f"Subscribed to {topic} (QoS {qos.value})")
                return True
            else:
                logger.error(f"Subscribe failed: {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """
        取消订阅
        
        Args:
            topic: 主题
        
        Returns:
            是否成功
        """
        if not self.client:
            return False
        
        try:
            result = self.client.unsubscribe(topic)
            
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscriptions:
                    del self.subscriptions[topic]
                logger.info(f"Unsubscribed from {topic}")
                return True
            else:
                logger.error(f"Unsubscribe failed: {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
            return False
    
    def add_message_handler(self, topic: str, handler: Callable[[MQTTMessage], None]):
        """
        添加消息处理器
        
        Args:
            topic: 主题
            handler: 处理函数
        """
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        self.message_handlers[topic].append(handler)
        logger.debug(f"Message handler added for {topic}")
    
    def remove_message_handler(self, topic: str, handler: Callable):
        """
        移除消息处理器
        
        Args:
            topic: 主题
            handler: 处理函数
        """
        if topic in self.message_handlers and handler in self.message_handlers[topic]:
            self.message_handlers[topic].remove(handler)
    
    def get_subscriptions(self) -> List[str]:
        """
        获取订阅列表
        
        Returns:
            订阅主题列表
        """
        return list(self.subscriptions.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取MQTT适配器状态
        
        Returns:
            状态字典
        """
        return {
            "available": PAHO_MQTT_AVAILABLE,
            "connection": {
                "host": self.config.host,
                "port": self.config.port,
                "status": self.connection_status.value,
                "reconnect_attempts": self.reconnect_attempts
            },
            "subscriptions": {
                "count": len(self.subscriptions),
                "topics": list(self.subscriptions.keys())
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭MQTT适配器"""
        logger.info("Shutting down MQTTAdapter...")
        
        self.disconnect()
        
        self.message_handlers.clear()
        self.subscriptions.clear()
        
        if self.client:
            self.client.loop_stop()
        
        logger.info("MQTTAdapter shutdown completed")

# 单例模式实现
_mqtt_adapter_instance: Optional[MQTTAdapter] = None

def get_mqtt_adapter(config: Optional[MQTTConfig] = None) -> MQTTAdapter:
    """
    获取MQTT适配器单例
    
    Args:
        config: MQTT配置
    
    Returns:
        MQTT适配器实例
    """
    global _mqtt_adapter_instance
    if _mqtt_adapter_instance is None:
        _mqtt_adapter_instance = MQTTAdapter(config)
    return _mqtt_adapter_instance

