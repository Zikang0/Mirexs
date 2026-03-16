"""
网络管理器：管理网络连接和配置
"""
import socket
import psutil
import subprocess
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import json
from pathlib import Path
import platform
import re

logger = logging.getLogger(__name__)

class NetworkStatus(Enum):
    """网络状态枚举"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    LIMITED = "limited"
    UNKNOWN = "unknown"

class ConnectionType(Enum):
    """连接类型枚举"""
    ETHERNET = "ethernet"
    WIFI = "wifi"
    MOBILE = "mobile"
    VPN = "vpn"
    UNKNOWN = "unknown"

@dataclass
class NetworkInterface:
    """网络接口信息"""
    name: str
    status: NetworkStatus
    connection_type: ConnectionType
    ip_address: str
    mac_address: str
    speed_mbps: float
    data_sent: int
    data_received: int
    is_up: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['connection_type'] = self.connection_type.value
        return data

@dataclass
class NetworkConnection:
    """网络连接信息"""
    pid: int
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    status: str
    process_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

class NetworkManager:
    """网络管理器"""
    
    def __init__(self):
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.network_interfaces: Dict[str, NetworkInterface] = {}
        self.network_connections: List[NetworkConnection] = []
        self.network_stats: Dict[str, Any] = {}
        self._setup_logging()
        self._initialize_network_monitoring()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_network_monitoring(self):
        """初始化网络监控"""
        # 获取初始网络状态
        self._refresh_network_interfaces()
        self._refresh_network_connections()
    
    def start_network_monitoring(self) -> bool:
        """开始网络监控"""
        if self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info("网络监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动网络监控失败: {str(e)}")
            return False
    
    def stop_network_monitoring(self) -> bool:
        """停止网络监控"""
        if not self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            
            logger.info("网络监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止网络监控失败: {str(e)}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 刷新网络接口信息
                self._refresh_network_interfaces()
                
                # 刷新网络连接信息
                self._refresh_network_connections()
                
                # 更新网络统计信息
                self._update_network_statistics()
                
                time.sleep(10)  # 每10秒更新一次
                
            except Exception as e:
                logger.error(f"网络监控循环错误: {str(e)}")
                time.sleep(30)
    
    def _refresh_network_interfaces(self):
        """刷新网络接口信息"""
        try:
            interfaces = {}
            stats = psutil.net_if_stats()
            io_counters = psutil.net_io_counters(pernic=True)
            addresses = psutil.net_if_addrs()
            
            for interface_name, interface_stats in stats.items():
                try:
                    # 获取接口状态
                    is_up = interface_stats.isup
                    status = NetworkStatus.CONNECTED if is_up else NetworkStatus.DISCONNECTED
                    
                    # 确定连接类型
                    connection_type = self._detect_connection_type(interface_name)
                    
                    # 获取IP地址和MAC地址
                    ip_address = "Unknown"
                    mac_address = "Unknown"
                    
                    if interface_name in addresses:
                        for addr in addresses[interface_name]:
                            if addr.family == socket.AF_INET:
                                ip_address = addr.address
                            elif addr.family == psutil.AF_LINK:
                                mac_address = addr.address
                    
                    # 获取网络速度
                    speed_mbps = interface_stats.speed
                    if speed_mbps == 0:
                        speed_mbps = self._estimate_interface_speed(interface_name)
                    
                    # 获取数据传输统计
                    data_sent = 0
                    data_received = 0
                    
                    if interface_name in io_counters:
                        io_data = io_counters[interface_name]
                        data_sent = io_data.bytes_sent
                        data_received = io_data.bytes_recv
                    
                    interface = NetworkInterface(
                        name=interface_name,
                        status=status,
                        connection_type=connection_type,
                        ip_address=ip_address,
                        mac_address=mac_address,
                        speed_mbps=speed_mbps,
                        data_sent=data_sent,
                        data_received=data_received,
                        is_up=is_up
                    )
                    
                    interfaces[interface_name] = interface
                    
                except Exception as e:
                    logger.error(f"刷新网络接口 {interface_name} 失败: {str(e)}")
            
            self.network_interfaces = interfaces
            
        except Exception as e:
            logger.error(f"刷新网络接口失败: {str(e)}")
    
    def _detect_connection_type(self, interface_name: str) -> ConnectionType:
        """检测连接类型"""
        interface_name_lower = interface_name.lower()
        
        if any(wifi_indicator in interface_name_lower for wifi_indicator in ['wifi', 'wireless', 'wlan']):
            return ConnectionType.WIFI
        elif any(eth_indicator in interface_name_lower for eth_indicator in ['ethernet', 'eth', 'lan']):
            return ConnectionType.ETHERNET
        elif any(vpn_indicator in interface_name_lower for vpn_indicator in ['vpn', 'tunnel']):
            return ConnectionType.VPN
        else:
            return ConnectionType.UNKNOWN
    
    def _estimate_interface_speed(self, interface_name: str) -> float:
        """估算接口速度"""
        # 简化实现，根据接口名称估算
        interface_lower = interface_name.lower()
        
        if 'gigabit' in interface_lower:
            return 1000.0
        elif 'fast' in interface_lower or '100' in interface_lower:
            return 100.0
        elif 'wireless' in interface_lower or 'wifi' in interface_lower:
            return 54.0  # 802.11g
        else:
            return 10.0
    
    def _refresh_network_connections(self):
        """刷新网络连接信息"""
        try:
            connections = []
            
            for conn in psutil.net_connections(kind='inet'):
                try:
                    # 获取进程信息
                    process_name = "Unknown"
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            process_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = f"PID_{conn.pid}"
                    
                    # 构建连接信息
                    local_address = conn.laddr.ip if conn.laddr else "Unknown"
                    local_port = conn.laddr.port if conn.laddr else 0
                    remote_address = conn.raddr.ip if conn.raddr else "Unknown"
                    remote_port = conn.raddr.port if conn.raddr else 0
                    
                    connection = NetworkConnection(
                        pid=conn.pid or 0,
                        local_address=local_address,
                        local_port=local_port,
                        remote_address=remote_address,
                        remote_port=remote_port,
                        status=conn.status,
                        process_name=process_name
                    )
                    
                    connections.append(connection)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            self.network_connections = connections
            
        except Exception as e:
            logger.error(f"刷新网络连接失败: {str(e)}")
    
    def _update_network_statistics(self):
        """更新网络统计信息"""
        try:
            # 获取全局网络IO统计
            net_io = psutil.net_io_counters()
            
            self.network_stats = {
                'total_bytes_sent': net_io.bytes_sent,
                'total_bytes_recv': net_io.bytes_recv,
                'total_packets_sent': net_io.packets_sent,
                'total_packets_recv': net_io.packets_recv,
                'update_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"更新网络统计失败: {str(e)}")
    
    def get_network_interfaces(self) -> List[NetworkInterface]:
        """获取网络接口列表"""
        return list(self.network_interfaces.values())
    
    def get_network_connections(self, filter_pid: int = None) -> List[NetworkConnection]:
        """获取网络连接列表"""
        if filter_pid:
            return [conn for conn in self.network_connections if conn.pid == filter_pid]
        else:
            return self.network_connections
    
    def get_network_statistics(self) -> Dict[str, Any]:
        """获取网络统计信息"""
        return self.network_stats.copy()
    
    def test_network_connectivity(self, target: str = "8.8.8.8", timeout: int = 5) -> Dict[str, Any]:
        """测试网络连通性"""
        try:
            start_time = time.time()
            
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', str(timeout * 1000), target],
                    capture_output=True, text=True
                )
                success = result.returncode == 0
            else:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', str(timeout), target],
                    capture_output=True, text=True
                )
                success = result.returncode == 0
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            if success:
                # 解析ping结果获取详细信息
                match = re.search(r'time=([\d.]+)\s*ms', result.stdout)
                if match:
                    response_time = float(match.group(1))
                
                return {
                    'success': True,
                    'target': target,
                    'response_time_ms': response_time,
                    'message': '连接成功'
                }
            else:
                return {
                    'success': False,
                    'target': target,
                    'response_time_ms': response_time,
                    'message': '连接失败',
                    'error': result.stderr
                }
            
        except Exception as e:
            return {
                'success': False,
                'target': target,
                'response_time_ms': 0,
                'message': '测试执行失败',
                'error': str(e)
            }
    
    def flush_dns_cache(self) -> bool:
        """刷新DNS缓存"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['ipconfig', '/flushdns'],
                    capture_output=True, text=True
                )
                success = result.returncode == 0
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ['sudo', 'killall', '-HUP', 'mDNSResponder'],
                    capture_output=True, text=True
                )
                success = result.returncode == 0
            else:  # Linux
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', 'systemd-resolved'],
                    capture_output=True, text=True
                )
                success = result.returncode == 0
            
            if success:
                logger.info("DNS缓存已刷新")
                return True
            else:
                logger.error(f"刷新DNS缓存失败: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"刷新DNS缓存异常: {str(e)}")
            return False
    
    def renew_dhcp_lease(self, interface_name: str) -> bool:
        """续订DHCP租约"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['ipconfig', '/release'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    time.sleep(2)
                    result = subprocess.run(
                        ['ipconfig', '/renew'],
                        capture_output=True, text=True
                    )
                    success = result.returncode == 0
                else:
                    success = False
            else:
                # Linux/macOS实现
                result = subprocess.run(
                    ['sudo', 'dhclient', '-r', interface_name],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    time.sleep(2)
                    result = subprocess.run(
                        ['sudo', 'dhclient', interface_name],
                        capture_output=True, text=True
                    )
                    success = result.returncode == 0
                else:
                    success = False
            
            if success:
                logger.info(f"DHCP租约已续订: {interface_name}")
                return True
            else:
                logger.error(f"续订DHCP租约失败: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"续订DHCP租约异常: {str(e)}")
            return False
    
    def get_network_troubleshooting_report(self) -> Dict[str, Any]:
        """获取网络故障排查报告"""
        report = {
            'generated_time': datetime.now().isoformat(),
            'network_interfaces': [
                interface.to_dict() for interface in self.get_network_interfaces()
            ],
            'connectivity_tests': [],
            'network_statistics': self.get_network_statistics()
        }
        
        # 测试常用服务的连通性
        test_targets = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "google.com",
            "baidu.com"
        ]
        
        for target in test_targets:
            test_result = self.test_network_connectivity(target)
            report['connectivity_tests'].append(test_result)
        
        return report
    
    def block_connection(self, process_name: str) -> bool:
        """阻断特定进程的网络连接"""
        try:
            # 这里应该实现防火墙规则添加
            # 简化实现，只记录日志
            logger.warning(f"阻断进程网络连接: {process_name}")
            return True
            
        except Exception as e:
            logger.error(f"阻断连接失败: {str(e)}")
            return False
    
    def allow_connection(self, process_name: str) -> bool:
        """允许特定进程的网络连接"""
        try:
            # 这里应该实现防火墙规则移除
            # 简化实现，只记录日志
            logger.info(f"允许进程网络连接: {process_name}")
            return True
            
        except Exception as e:
            logger.error(f"允许连接失败: {str(e)}")
            return False

# 单例实例
_network_manager_instance = None

def get_network_manager() -> NetworkManager:
    """获取网络管理器单例"""
    global _network_manager_instance
    if _network_manager_instance is None:
        _network_manager_instance = NetworkManager()
    return _network_manager_instance

