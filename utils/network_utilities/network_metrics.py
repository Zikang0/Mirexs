"""
网络度量工具模块

提供网络性能监控、带宽测试、延迟分析、吞吐量计算等功能
"""

import time
import socket
import threading
import statistics
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import subprocess
import platform
import json
import csv
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not installed, some features may be limited")

try:
    import ping3
    PING3_AVAILABLE = True
except ImportError:
    PING3_AVAILABLE = False
    print("ping3 not installed, using system ping instead")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("numpy not installed, statistical features may be limited")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NetworkBandwidthTester:
    """网络带宽测试器"""
    
    def __init__(self):
        self.test_results = {}
    
    def test_download_speed(self, test_url: str = None, 
                           duration: int = 10,
                           chunk_size: int = 8192) -> Dict[str, Any]:
        """测试下载速度"""
        import requests
        
        if test_url is None:
            test_url = "http://speedtest.ftp.otenet.gr/files/test1Mb.db"
        
        results = {
            'test_url': test_url,
            'duration': duration,
            'total_bytes': 0,
            'average_speed_bps': 0,
            'average_speed_mbps': 0,
            'peak_speed_bps': 0,
            'peak_speed_mbps': 0,
            'success': False,
            'error': None,
            'timestamp': time.time()
        }
        
        speeds = []
        start_time = time.time()
        
        try:
            session = requests.Session()
            response = session.get(test_url, stream=True, timeout=30)
            response.raise_for_status()
            
            chunk_times = []
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    chunk_start = time.time()
                    results['total_bytes'] += len(chunk)
                    chunk_end = time.time()
                    
                    chunk_time = chunk_end - chunk_start
                    if chunk_time > 0:
                        chunk_speed = len(chunk) * 8 / chunk_time  # bits per second
                        speeds.append(chunk_speed)
                        chunk_times.append(chunk_time)
                    
                    if time.time() - start_time > duration:
                        break
            
            if speeds:
                results['average_speed_bps'] = sum(speeds) / len(speeds)
                results['average_speed_mbps'] = results['average_speed_bps'] / (1024 * 1024)
                results['peak_speed_bps'] = max(speeds)
                results['peak_speed_mbps'] = results['peak_speed_bps'] / (1024 * 1024)
                
                if NUMPY_AVAILABLE:
                    results['speed_std_bps'] = float(np.std(speeds))
                    results['speed_std_mbps'] = results['speed_std_bps'] / (1024 * 1024)
                    results['speed_percentile_95'] = float(np.percentile(speeds, 95)) / (1024 * 1024)
            
            results['success'] = True
            results['actual_duration'] = time.time() - start_time
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"下载速度测试失败: {e}")
        
        return results
    
    def test_upload_speed(self, test_url: str = None,
                         data_size_mb: int = 1,
                         duration: int = 10) -> Dict[str, Any]:
        """测试上传速度"""
        import requests
        
        if test_url is None:
            test_url = "https://httpbin.org/post"
        
        # 生成测试数据
        data = b'x' * (data_size_mb * 1024 * 1024)
        
        results = {
            'test_url': test_url,
            'data_size_mb': data_size_mb,
            'duration': duration,
            'total_bytes': 0,
            'average_speed_bps': 0,
            'average_speed_mbps': 0,
            'peak_speed_bps': 0,
            'peak_speed_mbps': 0,
            'success': False,
            'error': None,
            'timestamp': time.time()
        }
        
        speeds = []
        start_time = time.time()
        
        try:
            # 分块上传
            chunk_size = 64 * 1024  # 64KB chunks
            chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
            
            session = requests.Session()
            
            for chunk in chunks:
                if time.time() - start_time > duration:
                    break
                
                chunk_start = time.time()
                response = session.post(test_url, data=chunk)
                chunk_end = time.time()
                
                if response.status_code == 200:
                    results['total_bytes'] += len(chunk)
                    chunk_time = chunk_end - chunk_start
                    if chunk_time > 0:
                        chunk_speed = len(chunk) * 8 / chunk_time
                        speeds.append(chunk_speed)
            
            if speeds:
                results['average_speed_bps'] = sum(speeds) / len(speeds)
                results['average_speed_mbps'] = results['average_speed_bps'] / (1024 * 1024)
                results['peak_speed_bps'] = max(speeds)
                results['peak_speed_mbps'] = results['peak_speed_bps'] / (1024 * 1024)
            
            results['success'] = True
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"上传速度测试失败: {e}")
        
        return results
    
    def test_latency(self, host: str, count: int = 10) -> Dict[str, Any]:
        """测试延迟"""
        from .dns_utils import DNSTool
        
        dns_tool = DNSTool()
        results = {
            'host': host,
            'count': count,
            'successful': 0,
            'failed': 0,
            'times': [],
            'min_ms': None,
            'max_ms': None,
            'avg_ms': None,
            'jitter_ms': None,
            'packet_loss': 0,
            'timestamp': time.time()
        }
        
        for i in range(count):
            ping_result = dns_tool.ping_host(host, count=1)
            if ping_result['successful_pings'] > 0 and ping_result['times']:
                results['times'].extend(ping_result['times'])
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        if results['times']:
            results['min_ms'] = min(results['times'])
            results['max_ms'] = max(results['times'])
            results['avg_ms'] = sum(results['times']) / len(results['times'])
            
            if len(results['times']) > 1:
                # 计算抖动（延迟变化）
                diffs = [abs(results['times'][i] - results['times'][i-1]) 
                        for i in range(1, len(results['times']))]
                results['jitter_ms'] = sum(diffs) / len(diffs)
        
        results['packet_loss'] = (results['failed'] / count) * 100
        
        return results


class NetworkLatencyAnalyzer:
    """网络延迟分析器"""
    
    def __init__(self):
        self.latency_history = {}
    
    def analyze_route_latency(self, target: str, max_hops: int = 30) -> Dict[str, Any]:
        """分析路由延迟"""
        import subprocess
        import re
        
        results = {
            'target': target,
            'hops': [],
            'total_hops': 0,
            'average_latency': 0,
            'max_latency': 0,
            'min_latency': 0,
            'timestamp': time.time()
        }
        
        latencies = []
        
        try:
            # 使用 traceroute/tracert
            if platform.system().lower() == 'windows':
                cmd = ['tracert', '-h', str(max_hops), target]
            else:
                cmd = ['traceroute', '-m', str(max_hops), target]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=60)
            
            for line in stdout.split('\n'):
                hop_info = self._parse_traceroute_line(line)
                if hop_info:
                    results['hops'].append(hop_info)
                    if hop_info['avg_latency']:
                        latencies.append(hop_info['avg_latency'])
            
            if latencies:
                results['total_hops'] = len(results['hops'])
                results['average_latency'] = sum(latencies) / len(latencies)
                results['max_latency'] = max(latencies)
                results['min_latency'] = min(latencies)
                
        except Exception as e:
            logger.error(f"路由延迟分析失败: {e}")
            results['error'] = str(e)
        
        return results
    
    def _parse_traceroute_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析traceroute输出行"""
        import re
        
        # 匹配跳数
        hop_match = re.match(r'\s*(\d+)\s+', line)
        if not hop_match:
            return None
        
        hop_num = int(hop_match.group(1))
        
        # 提取IP和延迟
        ip_matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)', line)
        time_matches = re.findall(r'(\d+\.?\d*)\s*ms', line)
        
        ip = ip_matches[0] if ip_matches else None
        times = [float(t) for t in time_matches]
        
        return {
            'hop': hop_num,
            'ip': ip,
            'times': times,
            'avg_latency': sum(times) / len(times) if times else None,
            'min_latency': min(times) if times else None,
            'max_latency': max(times) if times else None,
            'packet_loss': (3 - len(times)) * 33.33 if times else 100  # 近似丢包率
        }
    
    def track_latency_over_time(self, host: str, interval: int = 60, 
                               duration: int = 3600) -> Dict[str, Any]:
        """跟踪延迟随时间变化"""
        from .dns_utils import DNSTool
        
        dns_tool = DNSTool()
        timestamps = []
        latencies = []
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            result = dns_tool.ping_host(host, count=3)
            
            timestamp = datetime.now()
            timestamps.append(timestamp)
            
            if result['avg_time']:
                latencies.append(result['avg_time'])
            else:
                latencies.append(None)
            
            time.sleep(interval)
        
        stats = {}
        if latencies and any(l is not None for l in latencies):
            valid_latencies = [l for l in latencies if l is not None]
            if NUMPY_AVAILABLE:
                stats = {
                    'mean': float(np.mean(valid_latencies)),
                    'std': float(np.std(valid_latencies)),
                    'min': float(np.min(valid_latencies)),
                    'max': float(np.max(valid_latencies)),
                    'p95': float(np.percentile(valid_latencies, 95)),
                    'p99': float(np.percentile(valid_latencies, 99))
                }
            else:
                stats = {
                    'mean': sum(valid_latencies) / len(valid_latencies),
                    'min': min(valid_latencies),
                    'max': max(valid_latencies)
                }
        
        return {
            'host': host,
            'interval': interval,
            'duration': duration,
            'timestamps': [t.isoformat() for t in timestamps],
            'latencies': latencies,
            'statistics': stats
        }


class NetworkQualityAnalyzer:
    """网络质量分析器"""
    
    def __init__(self):
        self.quality_scores = {}
    
    def calculate_network_score(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """计算网络质量分数"""
        
        scores = {}
        weights = {
            'latency': 0.3,
            'jitter': 0.2,
            'packet_loss': 0.3,
            'bandwidth': 0.2
        }
        
        # 延迟评分（越低越好）
        if 'latency' in metrics:
            latency = metrics['latency']
            if latency < 50:
                scores['latency'] = 100
            elif latency < 100:
                scores['latency'] = 80
            elif latency < 200:
                scores['latency'] = 60
            elif latency < 300:
                scores['latency'] = 40
            else:
                scores['latency'] = 20
        
        # 抖动评分（越低越好）
        if 'jitter' in metrics:
            jitter = metrics['jitter']
            if jitter < 10:
                scores['jitter'] = 100
            elif jitter < 30:
                scores['jitter'] = 80
            elif jitter < 50:
                scores['jitter'] = 60
            elif jitter < 80:
                scores['jitter'] = 40
            else:
                scores['jitter'] = 20
        
        # 丢包率评分（越低越好）
        if 'packet_loss' in metrics:
            loss = metrics['packet_loss']
            if loss < 0.1:
                scores['packet_loss'] = 100
            elif loss < 1:
                scores['packet_loss'] = 80
            elif loss < 3:
                scores['packet_loss'] = 60
            elif loss < 5:
                scores['packet_loss'] = 40
            else:
                scores['packet_loss'] = 20
        
        # 带宽评分（越高越好）
        if 'bandwidth' in metrics:
            bandwidth = metrics['bandwidth']
            if bandwidth > 100:
                scores['bandwidth'] = 100
            elif bandwidth > 50:
                scores['bandwidth'] = 80
            elif bandwidth > 20:
                scores['bandwidth'] = 60
            elif bandwidth > 10:
                scores['bandwidth'] = 40
            else:
                scores['bandwidth'] = 20
        
        # 计算加权总分
        total_score = 0
        total_weight = 0
        
        for metric, score in scores.items():
            if metric in weights:
                total_score += score * weights[metric]
                total_weight += weights[metric]
        
        overall_score = total_score / total_weight if total_weight > 0 else 0
        
        # 质量等级
        if overall_score >= 90:
            grade = '优秀'
        elif overall_score >= 75:
            grade = '良好'
        elif overall_score >= 60:
            grade = '中等'
        elif overall_score >= 40:
            grade = '较差'
        else:
            grade = '极差'
        
        return {
            'overall_score': overall_score,
            'grade': grade,
            'scores': scores,
            'weights': weights
        }
    
    def analyze_network_stability(self, latency_history: List[float]) -> Dict[str, Any]:
        """分析网络稳定性"""
        if not latency_history:
            return {}
        
        if NUMPY_AVAILABLE:
            latencies = np.array(latency_history)
            std_dev = float(np.std(latencies))
            variance = float(np.var(latencies))
            coefficient_of_variation = std_dev / np.mean(latencies) if np.mean(latencies) > 0 else 0
        else:
            mean = sum(latency_history) / len(latency_history)
            variance = sum((x - mean) ** 2 for x in latency_history) / len(latency_history)
            std_dev = variance ** 0.5
            coefficient_of_variation = std_dev / mean if mean > 0 else 0
        
        # 稳定性评分
        if coefficient_of_variation < 0.1:
            stability = '非常稳定'
            stability_score = 100
        elif coefficient_of_variation < 0.2:
            stability = '稳定'
            stability_score = 80
        elif coefficient_of_variation < 0.3:
            stability = '一般'
            stability_score = 60
        elif coefficient_of_variation < 0.5:
            stability = '不稳定'
            stability_score = 40
        else:
            stability = '极不稳定'
            stability_score = 20
        
        return {
            'stability': stability,
            'stability_score': stability_score,
            'coefficient_of_variation': coefficient_of_variation,
            'std_dev': std_dev,
            'variance': variance,
            'samples': len(latency_history)
        }


class NetworkMetrics:
    """综合网络度量工具"""
    
    def __init__(self):
        self.bandwidth_tester = NetworkBandwidthTester()
        self.latency_analyzer = NetworkLatencyAnalyzer()
        self.quality_analyzer = NetworkQualityAnalyzer()
        self.monitoring_data = {}
        self.metrics_history = []
    
    def ping_host(self, host: str, count: int = 4) -> Dict[str, Any]:
        """Ping主机"""
        from .dns_utils import DNSTool
        
        dns_tool = DNSTool()
        return dns_tool.ping_host(host, count)
    
    def measure_latency(self, host: str, count: int = 10) -> Dict[str, Any]:
        """测量延迟"""
        return self.bandwidth_tester.test_latency(host, count)
    
    def test_bandwidth(self, test_type: str = 'download', **kwargs) -> Dict[str, Any]:
        """测试带宽"""
        if test_type == 'download':
            return self.bandwidth_tester.test_download_speed(**kwargs)
        elif test_type == 'upload':
            return self.bandwidth_tester.test_upload_speed(**kwargs)
        else:
            raise ValueError(f"不支持的测试类型: {test_type}")
    
    def analyze_route(self, target: str) -> Dict[str, Any]:
        """分析路由"""
        return self.latency_analyzer.analyze_route_latency(target)
    
    def track_latency(self, host: str, interval: int = 60, 
                     duration: int = 3600) -> Dict[str, Any]:
        """跟踪延迟"""
        return self.latency_analyzer.track_latency_over_time(host, interval, duration)
    
    def calculate_quality_score(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """计算质量分数"""
        return self.quality_analyzer.calculate_network_score(metrics)
    
    def analyze_stability(self, latency_history: List[float]) -> Dict[str, Any]:
        """分析稳定性"""
        return self.quality_analyzer.analyze_network_stability(latency_history)
    
    def get_network_stats(self) -> Dict[str, Any]:
        """获取网络统计"""
        if not PSUTIL_AVAILABLE:
            return {'error': 'psutil not installed'}
        
        import psutil
        
        stats = {
            'timestamp': time.time(),
            'network_io': {},
            'connections': [],
            'interfaces': {}
        }
        
        # 网络IO统计
        net_io = psutil.net_io_counters()
        stats['network_io'] = {
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errin': net_io.errin,
            'errout': net_io.errout,
            'dropin': net_io.dropin,
            'dropout': net_io.dropout
        }
        
        # 接口统计
        net_if_stats = psutil.net_if_stats()
        net_if_addrs = psutil.net_if_addrs()
        
        for interface in net_if_stats:
            stats['interfaces'][interface] = {
                'is_up': net_if_stats[interface].isup,
                'speed': net_if_stats[interface].speed,
                'mtu': net_if_stats[interface].mtu,
                'addresses': []
            }
            
            if interface in net_if_addrs:
                for addr in net_if_addrs[interface]:
                    stats['interfaces'][interface]['addresses'].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
        
        # 连接统计
        try:
            connections = psutil.net_connections()
            stats['connections'] = [
                {
                    'fd': conn.fd,
                    'family': conn.family,
                    'type': conn.type,
                    'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status,
                    'pid': conn.pid
                }
                for conn in connections[:100]  # 限制数量
            ]
        except:
            pass
        
        return stats
    
    def save_metric(self, name: str, value: Any) -> None:
        """保存指标"""
        self.metrics_history.append({
            'name': name,
            'value': value,
            'timestamp': time.time()
        })
        
        # 限制历史记录大小
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def get_metrics_history(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if name:
            return [m for m in self.metrics_history if m['name'] == name]
        return self.metrics_history
    
    def export_metrics(self, filename: str, format: str = 'json') -> bool:
        """导出指标"""
        try:
            if format == 'json':
                with open(filename, 'w') as f:
                    json.dump({
                        'metrics_history': self.metrics_history,
                        'export_time': time.time()
                    }, f, indent=2)
            elif format == 'csv':
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'name', 'value'])
                    for m in self.metrics_history:
                        writer.writerow([m['timestamp'], m['name'], m['value']])
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
            
            logger.info(f"指标已导出到 {filename}")
            return True
            
        except Exception as e:
            logger.error(f"导出指标失败: {e}")
            return False


def benchmark_network_performance(hosts: List[str], 
                                 test_duration: int = 60,
                                 include_bandwidth: bool = True) -> Dict[str, Any]:
    """网络性能基准测试"""
    
    metrics = NetworkMetrics()
    results = {
        'hosts': hosts,
        'test_duration': test_duration,
        'timestamp': time.time(),
        'ping_results': {},
        'latency_results': {},
        'bandwidth_results': {},
        'route_analysis': {},
        'summary': {}
    }
    
    for host in hosts:
        # Ping测试
        ping_result = metrics.ping_host(host, count=5)
        results['ping_results'][host] = ping_result
        
        # 延迟测试
        latency_result = metrics.measure_latency(host, count=10)
        results['latency_results'][host] = latency_result
        
        # 路由分析
        try:
            route_result = metrics.analyze_route(host)
            results['route_analysis'][host] = route_result
        except:
            pass
        
        # 保存指标
        if ping_result.get('avg_time'):
            metrics.save_metric(f'{host}_latency', ping_result['avg_time'])
    
    # 带宽测试（可选，可能耗时较长）
    if include_bandwidth:
        for host in hosts[:3]:  # 只测试前3个主机
            download_result = metrics.test_bandwidth('download', duration=10)
            results['bandwidth_results'][host] = download_result
            
            if download_result.get('average_speed_mbps'):
                metrics.save_metric(f'{host}_bandwidth', download_result['average_speed_mbps'])
    
    # 计算汇总统计
    latencies = [r.get('avg_time', 0) for r in results['ping_results'].values() if r.get('avg_time')]
    packet_losses = [r.get('packet_loss', 0) for r in results['ping_results'].values()]
    
    if latencies:
        if NUMPY_AVAILABLE:
            results['summary'] = {
                'average_latency': float(np.mean(latencies)),
                'median_latency': float(np.median(latencies)),
                'min_latency': float(np.min(latencies)),
                'max_latency': float(np.max(latencies)),
                'std_latency': float(np.std(latencies)),
                'average_packet_loss': float(np.mean(packet_losses)),
                'hosts_tested': len(hosts)
            }
        else:
            results['summary'] = {
                'average_latency': sum(latencies) / len(latencies),
                'min_latency': min(latencies),
                'max_latency': max(latencies),
                'average_packet_loss': sum(packet_losses) / len(packet_losses),
                'hosts_tested': len(hosts)
            }
    
    return results