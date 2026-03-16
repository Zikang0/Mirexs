"""
网络监控模块

提供网络监控和诊断工具。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import socket
import subprocess
import psutil
import time
import threading
from datetime import datetime, timedelta
import json
import statistics
from dataclasses import dataclass
from enum import Enum


class NetworkStatus(Enum):
    """网络状态枚举"""
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"
    DEGRADED = "DEGRADED"


@dataclass
class NetworkMetric:
    """网络指标数据类"""
    timestamp: datetime
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int


@dataclass
class PingResult:
    """Ping结果数据类"""
    host: str
    success: bool
    response_time: float
    packet_loss: float
    timestamp: datetime


class NetworkMonitor:
    """网络监控器"""
    
    def __init__(self, interfaces: List[str] = None):
        """初始化网络监控器
        
        Args:
            interfaces: 要监控的网络接口列表，None表示监控所有接口
        """
        self.interfaces = interfaces or self._get_all_interfaces()
        self.monitoring = False
        self.metrics_history: Dict[str, List[NetworkMetric]] = {}
        self.monitor_thread = None
        
        # 初始化历史记录
        for interface in self.interfaces:
            self.metrics_history[interface] = []
    
    def _get_all_interfaces(self) -> List[str]:
        """获取所有网络接口"""
        try:
            interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                if interface != 'lo':  # 排除本地回环接口
                    interfaces.append(interface)
            return interfaces
        except Exception:
            return ['eth0', 'wlan0']  # 默认接口
    
    def get_network_stats(self, interface: str) -> Optional[NetworkMetric]:
        """获取网络接口统计信息
        
        Args:
            interface: 网络接口名
            
        Returns:
            网络统计信息
        """
        try:
            stats = psutil.net_io_counters(pernic=True)
            if interface not in stats:
                return None
            
            net_stats = stats[interface]
            return NetworkMetric(
                timestamp=datetime.now(),
                interface=interface,
                bytes_sent=net_stats.bytes_sent,
                bytes_recv=net_stats.bytes_recv,
                packets_sent=net_stats.packets_sent,
                packets_recv=net_stats.packets_recv,
                errors_in=net_stats.errin,
                errors_out=net_stats.errout,
                drops_in=net_stats.dropin,
                drops_out=net_stats.dropout
            )
        except Exception as e:
            print(f"Error getting network stats for {interface}: {e}")
            return None
    
    def calculate_network_speed(self, interface: str, duration: int = 1) -> Dict[str, float]:
        """计算网络速度
        
        Args:
            interface: 网络接口名
            duration: 测量持续时间（秒）
            
        Returns:
            网络速度信息 {upload_speed, download_speed}
        """
        # 获取初始统计
        initial_stats = self.get_network_stats(interface)
        if not initial_stats:
            return {'upload_speed': 0.0, 'download_speed': 0.0}
        
        # 等待指定时间
        time.sleep(duration)
        
        # 获取最终统计
        final_stats = self.get_network_stats(interface)
        if not final_stats:
            return {'upload_speed': 0.0, 'download_speed': 0.0}
        
        # 计算速度 (bytes per second)
        upload_speed = (final_stats.bytes_sent - initial_stats.bytes_sent) / duration
        download_speed = (final_stats.bytes_recv - initial_stats.bytes_recv) / duration
        
        return {
            'upload_speed': upload_speed,
            'download_speed': download_speed,
            'upload_speed_mbps': upload_speed * 8 / (1024 * 1024),  # 转换为Mbps
            'download_speed_mbps': download_speed * 8 / (1024 * 1024)
        }
    
    def start_monitoring(self, interval: int = 5):
        """开始网络监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"Started network monitoring on interfaces: {self.interfaces}")
    
    def stop_monitoring(self):
        """停止网络监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Stopped network monitoring")
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        while self.monitoring:
            for interface in self.interfaces:
                metric = self.get_network_stats(interface)
                if metric:
                    self.metrics_history[interface].append(metric)
                    
                    # 保持历史记录在合理范围内
                    if len(self.metrics_history[interface]) > 1000:
                        self.metrics_history[interface] = self.metrics_history[interface][-500:]
            
            time.sleep(interval)
    
    def get_interface_status(self, interface: str) -> NetworkStatus:
        """获取接口状态
        
        Args:
            interface: 网络接口名
            
        Returns:
            网络状态
        """
        try:
            stats = psutil.net_if_stats()
            if interface not in stats:
                return NetworkStatus.UNKNOWN
            
            is_up, _, _, _, _ = stats[interface]
            return NetworkStatus.UP if is_up else NetworkStatus.DOWN
        except Exception:
            return NetworkStatus.UNKNOWN
    
    def get_network_summary(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """获取网络摘要信息
        
        Args:
            duration_minutes: 时间范围（分钟）
            
        Returns:
            网络摘要信息
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        summary = {}
        
        for interface in self.interfaces:
            # 过滤时间范围内的数据
            recent_metrics = [
                metric for metric in self.metrics_history[interface]
                if metric.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                continue
            
            # 计算统计信息
            upload_speeds = []
            download_speeds = []
            
            for i in range(1, len(recent_metrics)):
                prev_metric = recent_metrics[i-1]
                curr_metric = recent_metrics[i]
                
                time_diff = (curr_metric.timestamp - prev_metric.timestamp).total_seconds()
                if time_diff > 0:
                    upload_speed = (curr_metric.bytes_sent - prev_metric.bytes_sent) / time_diff
                    download_speed = (curr_metric.bytes_recv - prev_metric.bytes_recv) / time_diff
                    upload_speeds.append(upload_speed)
                    download_speeds.append(download_speed)
            
            summary[interface] = {
                'status': self.get_interface_status(interface).value,
                'total_bytes_sent': recent_metrics[-1].bytes_sent - recent_metrics[0].bytes_sent,
                'total_bytes_recv': recent_metrics[-1].bytes_recv - recent_metrics[0].bytes_recv,
                'avg_upload_speed_mbps': statistics.mean(upload_speeds) * 8 / (1024 * 1024) if upload_speeds else 0,
                'avg_download_speed_mbps': statistics.mean(download_speeds) * 8 / (1024 * 1024) if download_speeds else 0,
                'max_upload_speed_mbps': max(upload_speeds) * 8 / (1024 * 1024) if upload_speeds else 0,
                'max_download_speed_mbps': max(download_speeds) * 8 / (1024 * 1024) if download_speeds else 0,
                'total_packets_sent': recent_metrics[-1].packets_sent - recent_metrics[0].packets_sent,
                'total_packets_recv': recent_metrics[-1].packets_recv - recent_metrics[0].packets_recv,
                'error_rate': (sum(m.errors_in + m.errors_out for m in recent_metrics) / 
                             sum(m.packets_sent + m.packets_recv for m in recent_metrics) * 100) if recent_metrics else 0
            }
        
        return summary


class NetworkDiagnostic:
    """网络诊断工具"""
    
    @staticmethod
    def ping_host(host: str, count: int = 4, timeout: int = 5) -> PingResult:
        """Ping主机
        
        Args:
            host: 目标主机
            count: Ping次数
            timeout: 超时时间（秒）
            
        Returns:
            Ping结果
        """
        try:
            if socket.gethostbyname(host) == host:
                # IPv4
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
            else:
                # IPv6
                cmd = ['ping6', '-c', str(count), '-W', str(timeout), host]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 5)
            end_time = time.time()
            
            success = result.returncode == 0
            response_time = (end_time - start_time) / count if success else 0
            
            # 计算丢包率
            packet_loss = 0.0
            if success and 'packet loss' in result.stdout:
                loss_text = [line for line in result.stdout.split('\n') if 'packet loss' in line]
                if loss_text:
                    loss_percent = loss_text[0].split('%')[0].split()[-1]
                    try:
                        packet_loss = float(loss_percent)
                    except ValueError:
                        packet_loss = 0.0
            
            return PingResult(
                host=host,
                success=success,
                response_time=response_time,
                packet_loss=packet_loss,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            return PingResult(
                host=host,
                success=False,
                response_time=0.0,
                packet_loss=100.0,
                timestamp=datetime.now()
            )
    
    @staticmethod
    def check_port_connectivity(host: str, port: int, timeout: int = 5) -> bool:
        """检查端口连通性
        
        Args:
            host: 目标主机
            port: 目标端口
            timeout: 超时时间（秒）
            
        Returns:
            是否连通
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    def get_dns_resolution(domain: str) -> Dict[str, Any]:
        """DNS解析测试
        
        Args:
            domain: 域名
            
        Returns:
            DNS解析结果
        """
        result = {
            'domain': domain,
            'resolved': False,
            'ip_addresses': [],
            'resolution_time': 0.0,
            'error': None
        }
        
        try:
            start_time = time.time()
            ip_addresses = socket.gethostbyname_ex(domain)[2]
            end_time = time.time()
            
            result['resolved'] = True
            result['ip_addresses'] = ip_addresses
            result['resolution_time'] = (end_time - start_time) * 1000  # 转换为毫秒
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def traceroute(host: str, max_hops: int = 30) -> List[Dict[str, Any]]:
        """路由跟踪
        
        Args:
            host: 目标主机
            max_hops: 最大跳数
            
        Returns:
            路由跟踪结果
        """
        results = []
        
        try:
            # 使用traceroute命令
            cmd = ['traceroute', '-m', str(max_hops), host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines[1:]:  # 跳过标题行
                    if line.strip() and not line.startswith('traceroute'):
                        parts = line.split()
                        if len(parts) >= 2:
                            hop_info = {
                                'hop': int(parts[0]) if parts[0].isdigit() else 0,
                                'host': parts[1] if len(parts) > 1 else 'Unknown',
                                'ip': parts[1] if len(parts) > 1 else 'Unknown',
                                'response_times': []
                            }
                            
                            # 提取响应时间
                            for part in parts[2:]:
                                if 'ms' in part:
                                    try:
                                        time_val = float(part.replace('ms', ''))
                                        hop_info['response_times'].append(time_val)
                                    except ValueError:
                                        pass
                            
                            results.append(hop_info)
        
        except Exception as e:
            print(f"Traceroute failed: {e}")
        
        return results
    
    @staticmethod
    def check_bandwidth(host: str, port: int = 80, duration: int = 10) -> Dict[str, Any]:
        """带宽测试
        
        Args:
            host: 目标主机
            port: 目标端口
            duration: 测试持续时间（秒）
            
        Returns:
            带宽测试结果
        """
        result = {
            'host': host,
            'port': port,
            'duration': duration,
            'bytes_transferred': 0,
            'bandwidth_mbps': 0.0,
            'success': False,
            'error': None
        }
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(duration + 5)
            sock.connect((host, port))
            
            start_time = time.time()
            bytes_transferred = 0
            end_time = start_time + duration
            
            # 发送和接收数据来测试带宽
            data = b'x' * 1024  # 1KB的数据块
            while time.time() < end_time:
                try:
                    sock.send(data)
                    response = sock.recv(1024)
                    bytes_transferred += len(response)
                except socket.timeout:
                    break
                except Exception:
                    break
            
            sock.close()
            
            actual_duration = time.time() - start_time
            if actual_duration > 0:
                bandwidth_bps = bytes_transferred / actual_duration
                result['bytes_transferred'] = bytes_transferred
                result['bandwidth_mbps'] = bandwidth_bps * 8 / (1024 * 1024)
                result['success'] = True
        
        except Exception as e:
            result['error'] = str(e)
        
        return result


class NetworkAlert:
    """网络告警管理器"""
    
    def __init__(self, thresholds: Dict[str, float]):
        """初始化告警管理器
        
        Args:
            thresholds: 告警阈值配置
        """
        self.thresholds = thresholds
        self.alerts = []
    
    def check_thresholds(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """检查告警阈值
        
        Args:
            metrics: 网络指标
            
        Returns:
            触发的告警列表
        """
        triggered_alerts = []
        
        for metric, value in metrics.items():
            if metric in self.thresholds:
                threshold = self.thresholds[metric]
                if value > threshold:
                    alert = {
                        'metric': metric,
                        'value': value,
                        'threshold': threshold,
                        'timestamp': datetime.now(),
                        'severity': 'HIGH' if value > threshold * 1.5 else 'MEDIUM'
                    }
                    triggered_alerts.append(alert)
                    self.alerts.append(alert)
        
        return triggered_alerts
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取告警历史
        
        Args:
            hours: 时间范围（小时）
            
        Returns:
            告警历史列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alerts if alert['timestamp'] >= cutoff_time]


def create_network_monitoring_config() -> Dict[str, Any]:
    """创建网络监控配置
    
    Returns:
        网络监控配置
    """
    return {
        'interfaces': ['eth0', 'wlan0'],
        'monitoring_interval': 5,  # 秒
        'alert_thresholds': {
            'packet_loss': 5.0,  # %
            'response_time': 1000.0,  # ms
            'error_rate': 1.0,  # %
            'bandwidth_utilization': 80.0  # %
        },
        'ping_targets': ['8.8.8.8', '1.1.1.1', 'google.com'],
        'port_checks': [
            {'host': '8.8.8.8', 'port': 53, 'description': 'DNS'},
            {'host': 'google.com', 'port': 80, 'description': 'HTTP'},
            {'host': 'google.com', 'port': 443, 'description': 'HTTPS'}
        ]
    }