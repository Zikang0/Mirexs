"""
家庭助理模块 - Mirexs智能家居集成

提供家庭助理集成功能，包括：
1. Home Assistant API集成
2. 实体管理
3. 服务调用
4. 状态监控
5. 事件处理
6. 自动化集成
"""

import logging
import time
import json
import threading
import requests
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import hashlib
import websocket

logger = logging.getLogger(__name__)

class HassEntityDomain(Enum):
    """Home Assistant实体域枚举"""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CLIMATE = "climate"
    COVER = "cover"
    LOCK = "lock"
    MEDIA_PLAYER = "media_player"
    FAN = "fan"
    VACUUM = "vacuum"
    CAMERA = "camera"
    AUTOMATION = "automation"
    SCRIPT = "script"
    SCENE = "scene"

@dataclass
class HassEntity:
    """Home Assistant实体"""
    entity_id: str
    domain: HassEntityDomain
    state: str
    attributes: Dict[str, Any]
    last_changed: float
    last_updated: float
    friendly_name: Optional[str] = None

@dataclass
class HassService:
    """Home Assistant服务"""
    domain: str
    service: str
    description: str
    fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HassEvent:
    """Home Assistant事件"""
    event_type: str
    data: Dict[str, Any]
    origin: str
    time_fired: float
    context: Optional[Dict[str, Any]] = None

@dataclass
class HomeAssistantConfig:
    """Home Assistant配置"""
    # 连接配置
    host: str = "localhost"
    port: int = 8123
    use_ssl: bool = False
    api_password: Optional[str] = None
    access_token: Optional[str] = None
    
    # WebSocket配置
    use_websocket: bool = True
    reconnect_interval: int = 10
    
    # 同步配置
    sync_interval: int = 60  # 秒
    entity_whitelist: List[str] = field(default_factory=list)
    entity_blacklist: List[str] = field(default_factory=list)

class HomeAssistant:
    """
    Home Assistant集成管理器
    
    负责与Home Assistant实例的通信和集成。
    """
    
    def __init__(self, config: Optional[HomeAssistantConfig] = None):
        """
        初始化Home Assistant集成管理器
        
        Args:
            config: Home Assistant配置
        """
        self.config = config or HomeAssistantConfig()
        
        # 连接状态
        self.connected = False
        self.api_url = self._build_api_url()
        self.ws_url = self._build_ws_url()
        
        # 实体存储
        self.entities: Dict[str, HassEntity] = {}
        self.services: Dict[str, HassService] = {}
        
        # WebSocket连接
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        
        # 同步线程
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()
        
        # 事件监听器
        self.event_listeners: Dict[str, List[Callable]] = {}
        
        # 回调函数
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_entity_updated: Optional[Callable[[HassEntity], None]] = None
        self.on_event: Optional[Callable[[HassEvent], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "api_calls": 0,
            "ws_messages": 0,
            "entities_synced": 0,
            "services_called": 0,
            "errors": 0
        }
        
        # 尝试连接
        self.connect()
        
        logger.info(f"HomeAssistant initialized for {self.api_url}")
    
    def _build_api_url(self) -> str:
        """构建API URL"""
        protocol = "https" if self.config.use_ssl else "http"
        return f"{protocol}://{self.config.host}:{self.config.port}/api"
    
    def _build_ws_url(self) -> str:
        """构建WebSocket URL"""
        protocol = "wss" if self.config.use_ssl else "ws"
        return f"{protocol}://{self.config.host}:{self.config.port}/api/websocket"
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"
        elif self.config.api_password:
            headers["x-ha-access"] = self.config.api_password
        
        return headers
    
    def connect(self) -> bool:
        """
        连接到Home Assistant
        
        Returns:
            是否成功
        """
        if self.connected:
            logger.warning("Already connected")
            return True
        
        logger.info("Connecting to Home Assistant...")
        
        # 测试REST API连接
        try:
            response = requests.get(
                f"{self.api_url}/",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                self.connected = True
                logger.info("Connected to Home Assistant REST API")
                
                # 同步初始数据
                self._sync_states()
                
                # 连接WebSocket
                if self.config.use_websocket:
                    self._connect_websocket()
                
                if self.on_connected:
                    self.on_connected()
                
                # 启动定期同步
                self._start_sync()
                
                return True
            else:
                logger.error(f"Connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _connect_websocket(self):
        """连接WebSocket"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.stats["ws_messages"] += 1
                self._handle_ws_message(data)
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            self.stats["errors"] += 1
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket closed")
            self.connected = False
            
            if self.on_disconnected:
                self.on_disconnected()
        
        def on_open(ws):
            logger.info("WebSocket connected")
            # 认证
            auth_msg = {
                "type": "auth",
                "access_token": self.config.access_token or self.config.api_password
            }
            ws.send(json.dumps(auth_msg))
        
        def run_websocket():
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            self.ws.run_forever()
        
        self.ws_thread = threading.Thread(target=run_websocket, daemon=True)
        self.ws_thread.start()
    
    def _handle_ws_message(self, data: Dict[str, Any]):
        """处理WebSocket消息"""
        msg_type = data.get("type")
        
        if msg_type == "auth_ok":
            logger.info("WebSocket authenticated")
            # 订阅所有事件
            self._ws_subscribe_all()
        
        elif msg_type == "event":
            event_data = data.get("event", {})
            event = HassEvent(
                event_type=event_data.get("event_type", ""),
                data=event_data.get("data", {}),
                origin=event_data.get("origin", ""),
                time_fired=event_data.get("time_fired", 0),
                context=event_data.get("context")
            )
            
            # 触发事件监听器
            if event.event_type in self.event_listeners:
                for listener in self.event_listeners[event.event_type]:
                    try:
                        listener(event)
                    except Exception as e:
                        logger.error(f"Event listener error: {e}")
            
            if self.on_event:
                self.on_event(event)
    
    def _ws_subscribe_all(self):
        """订阅所有事件"""
        subscribe_msg = {
            "id": 1,
            "type": "subscribe_events"
        }
        self.ws.send(json.dumps(subscribe_msg))
    
    def _start_sync(self):
        """启动定期同步"""
        def sync_loop():
            while not self._stop_sync.is_set() and self.connected:
                try:
                    self._sync_states()
                    self._stop_sync.wait(self.config.sync_interval)
                except Exception as e:
                    logger.error(f"Sync error: {e}")
                    self.stats["errors"] += 1
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        logger.debug("Entity sync started")
    
    def _sync_states(self):
        """同步状态"""
        try:
            response = requests.get(
                f"{self.api_url}/states",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                states = response.json()
                synced_count = 0
                
                for state in states:
                    entity = self._parse_entity(state)
                    
                    # 应用黑白名单
                    if self.config.entity_whitelist:
                        if entity.entity_id not in self.config.entity_whitelist:
                            continue
                    
                    if self.config.entity_blacklist:
                        if entity.entity_id in self.config.entity_blacklist:
                            continue
                    
                    old_entity = self.entities.get(entity.entity_id)
                    self.entities[entity.entity_id] = entity
                    synced_count += 1
                    
                    if self.on_entity_updated:
                        self.on_entity_updated(entity)
                    
                    # 如果状态变化，触发更新
                    if old_entity and old_entity.state != entity.state:
                        logger.debug(f"Entity {entity.entity_id} state changed: {old_entity.state} -> {entity.state}")
                
                self.stats["entities_synced"] = synced_count
                logger.debug(f"Synced {synced_count} entities")
                
        except Exception as e:
            logger.error(f"State sync error: {e}")
            self.stats["errors"] += 1
    
    def _parse_entity(self, data: Dict[str, Any]) -> HassEntity:
        """解析实体数据"""
        entity_id = data.get("entity_id", "")
        domain_str = entity_id.split(".")[0] if "." in entity_id else ""
        
        try:
            domain = HassEntityDomain(domain_str)
        except:
            domain = HassEntityDomain.SENSOR
        
        # 解析时间戳
        last_changed = data.get("last_changed")
        if last_changed:
            import dateutil.parser
            last_changed = dateutil.parser.parse(last_changed).timestamp()
        
        last_updated = data.get("last_updated")
        if last_updated:
            import dateutil.parser
            last_updated = dateutil.parser.parse(last_updated).timestamp()
        
        attributes = data.get("attributes", {})
        friendly_name = attributes.get("friendly_name")
        
        return HassEntity(
            entity_id=entity_id,
            domain=domain,
            state=data.get("state", ""),
            attributes=attributes,
            last_changed=last_changed or 0,
            last_updated=last_updated or 0,
            friendly_name=friendly_name
        )
    
    def get_entity(self, entity_id: str) -> Optional[HassEntity]:
        """
        获取实体
        
        Args:
            entity_id: 实体ID
        
        Returns:
            实体对象
        """
        return self.entities.get(entity_id)
    
    def get_entities(self, domain: Optional[HassEntityDomain] = None) -> List[HassEntity]:
        """
        获取实体列表
        
        Args:
            domain: 实体域
        
        Returns:
            实体列表
        """
        entities = list(self.entities.values())
        
        if domain:
            entities = [e for e in entities if e.domain == domain]
        
        return entities
    
    def call_service(self, domain: str, service: str,
                    entity_id: Optional[str] = None,
                    service_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        调用服务
        
        Args:
            domain: 服务域
            service: 服务名称
            entity_id: 实体ID
            service_data: 服务数据
        
        Returns:
            是否成功
        """
        if not self.connected:
            logger.warning("Not connected to Home Assistant")
            return False
        
        url = f"{self.api_url}/services/{domain}/{service}"
        
        data = service_data or {}
        if entity_id:
            data["entity_id"] = entity_id
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            self.stats["api_calls"] += 1
            self.stats["services_called"] += 1
            
            if response.status_code == 200:
                logger.info(f"Service {domain}.{service} called for {entity_id}")
                return True
            else:
                logger.error(f"Service call failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Service call error: {e}")
            self.stats["errors"] += 1
            return False
    
    def turn_on(self, entity_id: str, **kwargs) -> bool:
        """
        打开设备
        
        Args:
            entity_id: 实体ID
            **kwargs: 额外参数
        
        Returns:
            是否成功
        """
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "turn_on", entity_id, kwargs)
    
    def turn_off(self, entity_id: str, **kwargs) -> bool:
        """
        关闭设备
        
        Args:
            entity_id: 实体ID
            **kwargs: 额外参数
        
        Returns:
            是否成功
        """
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "turn_off", entity_id, kwargs)
    
    def toggle(self, entity_id: str) -> bool:
        """
        切换设备状态
        
        Args:
            entity_id: 实体ID
        
        Returns:
            是否成功
        """
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "toggle", entity_id)
    
    def get_history(self, entity_id: str, start_time: Optional[float] = None,
                   end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        获取实体历史
        
        Args:
            entity_id: 实体ID
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            历史数据
        """
        if not self.connected:
            return []
        
        params = {
            "filter_entity_id": entity_id
        }
        
        if start_time:
            params["start_time"] = datetime.fromtimestamp(start_time).isoformat()
        
        if end_time:
            params["end_time"] = datetime.fromtimestamp(end_time).isoformat()
        
        try:
            response = requests.get(
                f"{self.api_url}/history/period",
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            
            self.stats["api_calls"] += 1
            
            if response.status_code == 200:
                return response.json()
            else:
                return []
                
        except Exception as e:
            logger.error(f"History error: {e}")
            return []
    
    def add_event_listener(self, event_type: str, listener: Callable[[HassEvent], None]):
        """
        添加事件监听器
        
        Args:
            event_type: 事件类型
            listener: 监听函数
        """
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(listener)
    
    def remove_event_listener(self, event_type: str, listener: Callable):
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            listener: 监听函数
        """
        if event_type in self.event_listeners and listener in self.event_listeners[event_type]:
            self.event_listeners[event_type].remove(listener)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Home Assistant集成状态
        
        Returns:
            状态字典
        """
        return {
            "connected": self.connected,
            "api_url": self.api_url,
            "websocket_enabled": self.config.use_websocket,
            "entities": {
                "total": len(self.entities),
                "by_domain": {d.value: len([e for e in self.entities.values() if e.domain == d]) 
                             for d in HassEntityDomain}
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭Home Assistant集成"""
        logger.info("Shutting down HomeAssistant...")
        
        self._stop_sync.set()
        
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=2)
        
        if self.ws:
            self.ws.close()
        
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)
        
        self.entities.clear()
        self.event_listeners.clear()
        self.connected = False
        
        logger.info("HomeAssistant shutdown completed")

# 单例模式实现
_home_assistant_instance: Optional[HomeAssistant] = None

def get_home_assistant(config: Optional[HomeAssistantConfig] = None) -> HomeAssistant:
    """
    获取Home Assistant集成管理器单例
    
    Args:
        config: Home Assistant配置
    
    Returns:
        Home Assistant集成管理器实例
    """
    global _home_assistant_instance
    if _home_assistant_instance is None:
        _home_assistant_instance = HomeAssistant(config)
    return _home_assistant_instance

