"""
UDP工具模块

提供UDP协议相关的工具函数，包括数据报管理、广播、多播等
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


class UDPDatagram:
    """UDP数据报"""
    
    def __init__(self, data: bytes, address: tuple, timestamp: float = None):
        self.data = data
        self.address = address
        self.timestamp = timestamp or time.time()
        self.size = len(data)
    
    def __repr__(self) -> str:
        return f"UDPDatagram(from={self.address}, size={self.size}, time={self.timestamp})"


class UDPSocket:
    """UDP Socket包装器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 0):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.receive_callbacks = []
        self.stats = {
            'bytes_sent': 0,
            'bytes_received': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'start_time': None
        }
    
    def start(self) -> bool:
        """启动UDP Socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.settimeout(1.0)
            
            self.running = True
            self.stats['start_time'] = time.time()
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
            logger.info(f"UDP Socket启动: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"UDP Socket启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止UDP Socket"""
        self.running = False
        if self.sock:
            self.sock.close()
    
    def send(self, data: bytes, address: tuple) -> int:
        """发送数据"""
        try:
            sent = self.sock.sendto(data, address)
            self.stats['bytes_sent'] += sent
            self.stats['packets_sent'] += 1
            return sent
        except Exception as e:
            logger.error(f"UDP发送失败: {e}")
            return 0
    
    def broadcast(self, data: bytes, port: int) -> int:
        """广播数据"""
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sent = self.sock.sendto(data, ('<broadcast>', port))
            self.stats['bytes_sent'] += sent
            self.stats['packets_sent'] += 1
            return sent
        except Exception as e:
            logger.error(f"UDP广播失败: {e}")
            return 0
    
    def join_multicast_group(self, multicast_group: str) -> bool:
        """加入多播组"""
        try:
            group = socket.inet_aton(multicast_group)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            return True
        except Exception as e:
            logger.error(f"加入多播组失败: {e}")
            return False
    
    def leave_multicast_group(self, multicast_group: str) -> bool:
        """离开多播组"""
        try:
            group = socket.inet_aton(multicast_group)
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            return True
        except Exception as e:
            logger.error(f"离开多播组失败: {e}")
            return False
    
    def _receive_loop(self) -> None:
        """接收循环"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65536)
                if data:
                    datagram = UDPDatagram(data, addr)
                    self.stats['bytes_received'] += len(data)
                    self.stats['packets_received'] += 1
                    
                    # 触发回调
                    for callback in self.receive_callbacks:
                        try:
                            callback(datagram)
                        except Exception as e:
                            logger.error(f"UDP回调错误: {e}")
                            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP接收错误: {e}")
    
    def add_receive_callback(self, callback: Callable[[UDPDatagram], None]) -> None:
        """添加接收回调"""
        self.receive_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        duration = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        return {
            'bytes_sent': self.stats['bytes_sent'],
            'bytes_received': self.stats['bytes_received'],
            'packets_sent': self.stats['packets_sent'],
            'packets_received': self.stats['packets_received'],
            'send_rate': self.stats['bytes_sent'] / duration if duration > 0 else 0,
            'receive_rate': self.stats['bytes_received'] / duration if duration > 0 else 0,
            'average_packet_size': self.stats['bytes_received'] / self.stats['packets_received'] if self.stats['packets_received'] > 0 else 0,
            'duration': duration
        }


class MulticastManager:
    """多播管理器"""
    
    def __init__(self):
        self.groups = {}
    
    def create_multicast_socket(self, multicast_group: str, port: int) -> Optional[UDPSocket]:
        """创建多播Socket"""
        try:
            udp_socket = UDPSocket('0.0.0.0', port)
            if udp_socket.start():
                if udp_socket.join_multicast_group(multicast_group):
                    self.groups[multicast_group] = udp_socket
                    return udp_socket
                else:
                    udp_socket.stop()
            return None
        except Exception as e:
            logger.error(f"创建多播Socket失败: {e}")
            return None
    
    def send_multicast(self, multicast_group: str, data: bytes, port: int) -> bool:
        """发送多播数据"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.sendto(data, (multicast_group, port))
            sock.close()
            return True
        except Exception as e:
            logger.error(f"发送多播数据失败: {e}")
            return False
    
    def close_all(self) -> None:
        """关闭所有多播连接"""
        for group, sock in self.groups.items():
            sock.leave_multicast_group(group)
            sock.stop()
        self.groups.clear()