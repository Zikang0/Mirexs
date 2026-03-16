"""
协议适配器：支持多种通信协议
负责不同通信协议的适配和转换
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from urllib.parse import urlparse

class ProtocolType(Enum):
    """协议类型枚举"""
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    MQTT = "mqtt"
    GRPC = "grpc"
    ZMQ = "zmq"
    REDIS = "redis"

@dataclass
class ProtocolConfig:
    """协议配置"""
    protocol_type: ProtocolType
    host: str
    port: int
    timeout: int = 30
    ssl_verify: bool = True
    headers: Dict[str, str] = None
    auth: Dict[str, str] = None

class ProtocolAdapter:
    """协议适配器基类"""
    
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.is_connected = False
        self.connection = None
        
    async def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError
    
    async def disconnect(self):
        """断开连接"""
        raise NotImplementedError
    
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送数据"""
        raise NotImplementedError
    
    async def receive(self) -> Dict[str, Any]:
        """接收数据"""
        raise NotImplementedError

class HTTPAdapter(ProtocolAdapter):
    """HTTP协议适配器"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def connect(self) -> bool:
        """建立HTTP连接"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            self.is_connected = True
            logging.info(f"HTTP适配器连接成功: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logging.error(f"HTTP适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开HTTP连接"""
        if self.session:
            await self.session.close()
            self.session = None
        self.is_connected = False
        logging.info("HTTP适配器已断开")
    
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求"""
        if not self.is_connected or not self.session:
            raise ConnectionError("HTTP适配器未连接")
        
        try:
            url = f"{self.config.protocol_type.value}://{self.config.host}:{self.config.port}{data.get('path', '')}"
            method = data.get('method', 'GET')
            headers = {**(self.config.headers or {}), **data.get('headers', {})}
            body_data = data.get('body')
            
            async with self.session.request(
                method=method,
                url=url,
                json=body_data,
                headers=headers,
                ssl=self.config.ssl_verify
            ) as response:
                result = {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": await response.json() if response.content_type == 'application/json' else await response.text()
                }
                return result
                
        except Exception as e:
            logging.error(f"HTTP请求失败: {e}")
            raise

class WebSocketAdapter(ProtocolAdapter):
    """WebSocket协议适配器"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            session = aiohttp.ClientSession()
            url = f"ws://{self.config.host}:{self.config.port}"
            self.websocket = await session.ws_connect(url)
            self.is_connected = True
            logging.info(f"WebSocket适配器连接成功: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logging.error(f"WebSocket适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.is_connected = False
        logging.info("WebSocket适配器已断开")
    
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送WebSocket消息"""
        if not self.is_connected or not self.websocket:
            raise ConnectionError("WebSocket适配器未连接")
        
        try:
            message = json.dumps(data)
            await self.websocket.send_str(message)
            return {"status": "sent"}
        except Exception as e:
            logging.error(f"WebSocket发送失败: {e}")
            raise
    
    async def receive(self) -> Dict[str, Any]:
        """接收WebSocket消息"""
        if not self.is_connected or not self.websocket:
            raise ConnectionError("WebSocket适配器未连接")
        
        try:
            msg = await self.websocket.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                return json.loads(msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise ConnectionError(f"WebSocket错误: {msg.data}")
            else:
                return {"type": msg.type.name, "data": msg.data}
        except Exception as e:
            logging.error(f"WebSocket接收失败: {e}")
            raise

class MQTTAdapter(ProtocolAdapter):
    """MQTT协议适配器（模拟实现）"""
    
    def __init__(self, config: ProtocolConfig):
        super().__init__(config)
        self.subscriptions: Dict[str, Callable] = {}
        
    async def connect(self) -> bool:
        """建立MQTT连接（模拟）"""
        logging.info(f"MQTT适配器连接成功（模拟）: {self.config.host}:{self.config.port}")
        self.is_connected = True
        return True
    
    async def disconnect(self):
        """断开MQTT连接"""
        self.is_connected = False
        logging.info("MQTT适配器已断开")
    
    async def send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """发送MQTT消息（模拟）"""
        if not self.is_connected:
            raise ConnectionError("MQTT适配器未连接")
        
        topic = data.get('topic', 'default')
        message = data.get('message', {})
        
        logging.debug(f"MQTT消息发送: {topic} -> {message}")
        return {"status": "published", "topic": topic}
    
    async def subscribe(self, topic: str, callback: Callable):
        """订阅MQTT主题"""
        self.subscriptions[topic] = callback
        logging.debug(f"MQTT订阅: {topic}")
    
    async def unsubscribe(self, topic: str):
        """取消订阅MQTT主题"""
        if topic in self.subscriptions:
            del self.subscriptions[topic]
            logging.debug(f"MQTT取消订阅: {topic}")

class ProtocolAdapterFactory:
    """协议适配器工厂"""
    
    @staticmethod
    def create_adapter(config: ProtocolConfig) -> ProtocolAdapter:
        """创建协议适配器"""
        if config.protocol_type in [ProtocolType.HTTP, ProtocolType.HTTPS]:
            return HTTPAdapter(config)
        elif config.protocol_type == ProtocolType.WEBSOCKET:
            return WebSocketAdapter(config)
        elif config.protocol_type == ProtocolType.MQTT:
            return MQTTAdapter(config)
        else:
            raise ValueError(f"不支持的协议类型: {config.protocol_type}")
    
    @staticmethod
    def create_adapter_from_url(url: str, **kwargs) -> ProtocolAdapter:
        """从URL创建协议适配器"""
        parsed = urlparse(url)
        
        protocol_map = {
            'http': ProtocolType.HTTP,
            'https': ProtocolType.HTTPS,
            'ws': ProtocolType.WEBSOCKET,
            'wss': ProtocolType.WEBSOCKET,
            'mqtt': ProtocolType.MQTT
        }
        
        protocol_type = protocol_map.get(parsed.scheme)
        if not protocol_type:
            raise ValueError(f"不支持的URL协议: {parsed.scheme}")
        
        config = ProtocolConfig(
            protocol_type=protocol_type,
            host=parsed.hostname,
            port=parsed.port or (443 if protocol_type == ProtocolType.HTTPS else 80),
            **kwargs
        )
        
        return ProtocolAdapterFactory.create_adapter(config)

# 全局协议管理器
class ProtocolManager:
    """协议管理器"""
    
    def __init__(self):
        self.adapters: Dict[str, ProtocolAdapter] = {}
        
    async def create_adapter(self, name: str, config: ProtocolConfig) -> bool:
        """创建协议适配器"""
        try:
            adapter = ProtocolAdapterFactory.create_adapter(config)
            connected = await adapter.connect()
            
            if connected:
                self.adapters[name] = adapter
                return True
            return False
            
        except Exception as e:
            logging.error(f"创建协议适配器失败: {e}")
            return False
    
    def get_adapter(self, name: str) -> Optional[ProtocolAdapter]:
        """获取协议适配器"""
        return self.adapters.get(name)
    
    async def remove_adapter(self, name: str):
        """移除协议适配器"""
        if name in self.adapters:
            adapter = self.adapters[name]
            await adapter.disconnect()
            del self.adapters[name]
            logging.info(f"协议适配器已移除: {name}")
    
    def list_adapters(self) -> Dict[str, str]:
        """列出所有适配器"""
        return {
            name: adapter.config.protocol_type.value
            for name, adapter in self.adapters.items()
        }

# 全局协议管理器实例
protocol_manager = ProtocolManager()
