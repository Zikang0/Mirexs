"""
TCP工具模块

提供TCP协议相关的工具函数，包括连接管理、数据流控制、拥塞控制等
"""

import socket
import struct
import time
import threading
from typing import Dict, List, Any, Optional, Union, Callable
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TCPConnection:
    """TCP连接类"""
    
    def __init__(self, sock: socket.socket, address: tuple):
        self.sock = sock
        self.address = address
        self.connected = True
        self.bytes_sent = 0
        self.bytes_received = 0
        self.start_time = time.time()
        self.last_activity = time.time()
    
    def send(self, data: bytes) -> int:
        """发送数据"""
        try:
            sent = self.sock.send(data)
            self.bytes_sent += sent
            self.last_activity = time.time()
            return sent
        except Exception as e:
            logger.error(f"发送失败: {e}")
            return 0
    
    def receive(self, buffer_size: int = 4096) -> Optional[bytes]:
        """接收数据"""
        try:
            data = self.sock.recv(buffer_size)
            if data:
                self.bytes_received += len(data)
                self.last_activity = time.time()
            return data
        except Exception as e:
            logger.error(f"接收失败: {e}")
            return None
    
    def close(self) -> None:
        """关闭连接"""
        try:
            self.sock.close()
        except:
            pass
        self.connected = False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = time.time() - self.start_time
        return {
            'address': self.address,
            'connected': self.connected,
            'duration': duration,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'send_rate': self.bytes_sent / duration if duration > 0 else 0,
            'receive_rate': self.bytes_received / duration if duration > 0 else 0,
            'last_activity': self.last_activity,
            'idle_time': time.time() - self.last_activity
        }


class TCPConnectionPool:
    """TCP连接池"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connections = {}
        self.lock = threading.Lock()
    
    def add_connection(self, conn_id: str, connection: TCPConnection) -> bool:
        """添加连接"""
        with self.lock:
            if len(self.connections) >= self.max_connections:
                return False
            self.connections[conn_id] = connection
            return True
    
    def get_connection(self, conn_id: str) -> Optional[TCPConnection]:
        """获取连接"""
        with self.lock:
            return self.connections.get(conn_id)
    
    def remove_connection(self, conn_id: str) -> bool:
        """移除连接"""
        with self.lock:
            if conn_id in self.connections:
                self.connections[conn_id].close()
                del self.connections[conn_id]
                return True
            return False
    
    def get_all_connections(self) -> List[TCPConnection]:
        """获取所有连接"""
        with self.lock:
            return list(self.connections.values())
    
    def cleanup_idle_connections(self, max_idle_time: float = 300) -> int:
        """清理空闲连接"""
        cleaned = 0
        current_time = time.time()
        
        with self.lock:
            for conn_id, conn in list(self.connections.items()):
                if current_time - conn.last_activity > max_idle_time:
                    conn.close()
                    del self.connections[conn_id]
                    cleaned += 1
        
        return cleaned
    
    def get_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        with self.lock:
            return {
                'total_connections': len(self.connections),
                'max_connections': self.max_connections,
                'utilization': len(self.connections) / self.max_connections * 100,
                'active_connections': sum(1 for c in self.connections.values() if c.connected)
            }


class TCPStream:
    """TCP数据流"""
    
    def __init__(self, connection: TCPConnection):
        self.connection = connection
        self.buffer = b''
        self.total_bytes = 0
        self.packet_count = 0
    
    def write(self, data: bytes) -> int:
        """写入数据"""
        sent = self.connection.send(data)
        if sent > 0:
            self.total_bytes += sent
            self.packet_count += 1
        return sent
    
    def read(self, size: int = -1) -> Optional[bytes]:
        """读取数据"""
        if size < 0:
            # 读取所有可用数据
            data = self.connection.receive(65536)
            if data:
                self.buffer += data
            result = self.buffer
            self.buffer = b''
            return result
        else:
            # 读取指定大小
            while len(self.buffer) < size:
                data = self.connection.receive(4096)
                if not data:
                    break
                self.buffer += data
            
            if len(self.buffer) >= size:
                result = self.buffer[:size]
                self.buffer = self.buffer[size:]
                return result
            else:
                result = self.buffer
                self.buffer = b''
                return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取流统计信息"""
        return {
            'total_bytes': self.total_bytes,
            'packet_count': self.packet_count,
            'average_packet_size': self.total_bytes / self.packet_count if self.packet_count > 0 else 0,
            'buffer_size': len(self.buffer)
        }