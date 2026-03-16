"""
网络管理器：管理网络连接和通信
负责网络连接状态监控、连接管理和网络配置
"""

import asyncio
import socket
import psutil
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import aiohttp

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"

@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    ip_address: str
    netmask: str
    mac_address: str
    is_up: bool
    speed: int  # Mbps

@dataclass
class ConnectionInfo:
    """连接信息"""
    connection_id: str
    endpoint: str
    protocol: str
    status: ConnectionStatus
    established_at: Optional[datetime]
    last_activity: Optional[datetime]
    latency: Optional[float]  # ms

class NetworkManager:
    """网络管理器"""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionInfo] = {}
        self.network_interfaces: Dict[str, NetworkInterface] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.initialized = False
        
    async def initialize(self):
        """初始化网络管理器"""
        if self.initialized:
            return
            
        logging.info("初始化网络管理器...")
        
        # 扫描网络接口
        await self._scan_network_interfaces()
        
        # 创建HTTP会话
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # 启动网络监控
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        self.initialized = True
        logging.info("网络管理器初始化完成")
    
    async def _scan_network_interfaces(self):
        """扫描网络接口"""
        try:
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface_name, addresses in interfaces.items():
                ip_address = ""
                netmask = ""
                mac_address = ""
                
                for addr in addresses:
                    if addr.family == socket.AF_INET:  # IPv4
                        ip_address = addr.address
                        netmask = addr.netmask
                    elif addr.family == psutil.AF_LINK:  # MAC地址
                        mac_address = addr.address
                
                interface_stats = stats.get(interface_name)
                is_up = interface_stats.isup if interface_stats else False
                speed = interface_stats.speed if interface_stats else 0
                
                self.network_interfaces[interface_name] = NetworkInterface(
                    name=interface_name,
                    ip_address=ip_address,
                    netmask=netmask,
                    mac_address=mac_address,
                    is_up=is_up,
                    speed=speed
                )
                
                logging.debug(f"发现网络接口: {interface_name} - {ip_address}")
                
        except Exception as e:
            logging.error(f"网络接口扫描失败: {e}")
    
    async def _monitoring_worker(self):
        """网络监控工作线程"""
        while True:
            try:
                await asyncio.sleep(10)  # 每10秒监控一次
                await self._update_network_status()
                await self._check_connections()
                
            except Exception as e:
                logging.error(f"网络监控错误: {e}")
    
    async def _update_network_status(self):
        """更新网络状态"""
        # 更新接口状态
        await self._scan_network_interfaces()
        
        # 更新连接状态
        for connection_id, connection in list(self.connections.items()):
            if connection.status == ConnectionStatus.CONNECTED:
                # 检查连接是否仍然有效
                is_alive = await self._check_connection_health(connection)
                if not is_alive:
                    connection.status = ConnectionStatus.RECONNECTING
                    logging.warning(f"连接断开: {connection.endpoint}")
    
    async def _check_connection_health(self, connection: ConnectionInfo) -> bool:
        """检查连接健康状态"""
        try:
            if connection.protocol.startswith("http"):
                async with self.http_session.get(connection.endpoint, timeout=5) as response:
                    return response.status < 400
            else:
                # 对于其他协议，尝试建立连接
                reader, writer = await asyncio.open_connection(
                    connection.endpoint.split(":")[0],
                    int(connection.endpoint.split(":")[1])
                )
                writer.close()
                await writer.wait_closed()
                return True
                
        except Exception:
            return False
    
    async def _check_connections(self):
        """检查所有连接"""
        for connection in self.connections.values():
            if connection.status in [ConnectionStatus.CONNECTING, ConnectionStatus.RECONNECTING]:
                await self._attempt_reconnect(connection)
    
    async def _attempt_reconnect(self, connection: ConnectionInfo):
        """尝试重新连接"""
        try:
            is_connected = await self._check_connection_health(connection)
            if is_connected:
                connection.status = ConnectionStatus.CONNECTED
                connection.established_at = datetime.now()
                logging.info(f"重新连接成功: {connection.endpoint}")
            else:
                connection.status = ConnectionStatus.ERROR
                
        except Exception as e:
            logging.error(f"重新连接失败 {connection.endpoint}: {e}")
            connection.status = ConnectionStatus.ERROR
    
    async def create_connection(self, endpoint: str, protocol: str = "http") -> str:
        """创建连接"""
        connection_id = f"conn_{len(self.connections) + 1}"
        
        connection = ConnectionInfo(
            connection_id=connection_id,
            endpoint=endpoint,
            protocol=protocol,
            status=ConnectionStatus.CONNECTING,
            established_at=None,
            last_activity=None,
            latency=None
        )
        
        self.connections[connection_id] = connection
        
        # 测试连接
        is_connected = await self._check_connection_health(connection)
        if is_connected:
            connection.status = ConnectionStatus.CONNECTED
            connection.established_at = datetime.now()
            logging.info(f"连接创建成功: {endpoint}")
        else:
            connection.status = ConnectionStatus.ERROR
            logging.error(f"连接创建失败: {endpoint}")
        
        return connection_id
    
    async def close_connection(self, connection_id: str):
        """关闭连接"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.status = ConnectionStatus.DISCONNECTED
            del self.connections[connection_id]
            logging.info(f"连接关闭: {connection.endpoint}")
    
    async def send_request(self, connection_id: str, method: str = "GET",
                         path: str = "", data: Dict = None, headers: Dict = None) -> Dict:
        """发送网络请求"""
        if connection_id not in self.connections:
            raise ValueError(f"连接不存在: {connection_id}")
        
        connection = self.connections[connection_id]
        
        if connection.status != ConnectionStatus.CONNECTED:
            raise ConnectionError(f"连接不可用: {connection_id}")
        
        try:
            url = f"{connection.endpoint}{path}"
            
            if connection.protocol.startswith("http"):
                async with self.http_session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers
                ) as response:
                    result = {
                        "status": response.status,
                        "headers": dict(response.headers),
                        "data": await response.json() if response.content_type == 'application/json' else await response.text()
                    }
                    
                    # 更新连接活动时间
                    connection.last_activity = datetime.now()
                    
                    return result
            else:
                # 其他协议的处理
                raise NotImplementedError(f"协议未实现: {connection.protocol}")
                
        except Exception as e:
            logging.error(f"网络请求失败: {e}")
            connection.status = ConnectionStatus.ERROR
            raise
    
    async def measure_latency(self, connection_id: str) -> float:
        """测量连接延迟"""
        if connection_id not in self.connections:
            return -1
        
        connection = self.connections[connection_id]
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            if connection.protocol.startswith("http"):
                async with self.http_session.get(connection.endpoint, timeout=5) as response:
                    end_time = asyncio.get_event_loop().time()
                    latency = (end_time - start_time) * 1000  # 转换为毫秒
                    
                    connection.latency = latency
                    return latency
            else:
                # 其他协议的延迟测量
                return -1
                
        except Exception as e:
            logging.error(f"延迟测量失败: {e}")
            return -1
    
    def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        total_connections = len(self.connections)
        connected_count = sum(1 for conn in self.connections.values() 
                            if conn.status == ConnectionStatus.CONNECTED)
        
        interface_stats = {}
        for name, interface in self.network_interfaces.items():
            interface_stats[name] = {
                "ip_address": interface.ip_address,
                "is_up": interface.is_up,
                "speed": interface.speed
            }
        
        return {
            "total_interfaces": len(self.network_interfaces),
            "active_interfaces": sum(1 for iface in self.network_interfaces.values() if iface.is_up),
            "total_connections": total_connections,
            "connected_connections": connected_count,
            "interfaces": interface_stats,
            "connections": [
                {
                    "id": conn.connection_id,
                    "endpoint": conn.endpoint,
                    "protocol": conn.protocol,
                    "status": conn.status.value,
                    "latency": conn.latency
                }
                for conn in self.connections.values()
            ]
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

# 全局网络管理器实例
network_manager = NetworkManager()
