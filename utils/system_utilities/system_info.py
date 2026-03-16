"""
系统信息模块

提供系统信息收集和管理工具。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import platform
import psutil
import os
import socket
import uuid
import subprocess
import json
from datetime import datetime, timedelta
import cpuinfo
import GPUtil


class SystemInfoCollector:
    """系统信息收集器"""
    
    @staticmethod
    def get_basic_info() -> Dict[str, Any]:
        """获取基本系统信息
        
        Returns:
            基本系统信息字典
        """
        return {
            'system': platform.system(),
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'processor': platform.processor(),
            'machine': platform.machine(),
            'node': platform.node(),
            'version': platform.version(),
            'python_version': platform.python_version(),
            'hostname': socket.gethostname(),
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            'uptime': str(timedelta(seconds=time.time() - psutil.boot_time()))
        }
    
    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """获取CPU信息
        
        Returns:
            CPU信息字典
        """
        try:
            cpu_info = cpuinfo.get_cpu_info()
        except:
            cpu_info = {}
        
        return {
            'brand': cpu_info.get('brand_raw', 'Unknown'),
            'vendor': cpu_info.get('vendor_id_raw', 'Unknown'),
            'family': cpu_info.get('family', 'Unknown'),
            'model': cpu_info.get('model', 'Unknown'),
            'stepping': cpu_info.get('stepping', 'Unknown'),
            'physical_cores': psutil.cpu_count(logical=False),
            'total_cores': psutil.cpu_count(logical=True),
            'max_frequency': f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else "Unknown",
            'min_frequency': f"{psutil.cpu_freq().min:.2f}Mhz" if psutil.cpu_freq() else "Unknown",
            'current_frequency': f"{psutil.cpu_freq().current:.2f}Mhz" if psutil.cpu_freq() else "Unknown",
            'usage_per_core': [f"{percentage:.1f}%" for percentage in psutil.cpu_percent(percpu=True, interval=1)],
            'total_usage': f"{psutil.cpu_percent(interval=1):.1f}%"
        }
    
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """获取内存信息
        
        Returns:
            内存信息字典
        """
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': f"{memory.total / (1024**3):.2f} GB",
            'available': f"{memory.available / (1024**3):.2f} GB",
            'used': f"{memory.used / (1024**3):.2f} GB",
            'percentage': f"{memory.percent:.1f}%",
            'free': f"{memory.free / (1024**3):.2f} GB",
            'active': f"{memory.active / (1024**3):.2f} GB",
            'inactive': f"{memory.inactive / (1024**3):.2f} GB",
            'cached': f"{memory.cached / (1024**3):.2f} GB",
            'buffers': f"{memory.buffers / (1024**3):.2f} GB",
            'swap': {
                'total': f"{swap.total / (1024**3):.2f} GB",
                'used': f"{swap.used / (1024**3):.2f} GB",
                'free': f"{swap.free / (1024**3):.2f} GB",
                'percentage': f"{swap.percent:.1f}%"
            }
        }
    
    @staticmethod
    def get_disk_info() -> List[Dict[str, Any]]:
        """获取磁盘信息
        
        Returns:
            磁盘信息列表
        """
        disk_info = []
        
        # 获取所有磁盘分区
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'file_system': partition.fstype,
                    'total': f"{partition_usage.total / (1024**3):.2f} GB",
                    'used': f"{partition_usage.used / (1024**3):.2f} GB",
                    'free': f"{partition_usage.free / (1024**3):.2f} GB",
                    'percentage': f"{(partition_usage.used / partition_usage.total * 100):.1f}%"
                })
            except PermissionError:
                continue
        
        return disk_info
    
    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        """获取网络信息
        
        Returns:
            网络信息字典
        """
        network_info = {
            'interfaces': {},
            'connections': [],
            'io_counters': {}
        }
        
        # 网络接口信息
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {
                'addresses': [],
                'is_up': interface in psutil.net_if_stats() and psutil.net_if_stats()[interface].isup
            }
            
            for addr in addrs:
                interface_info['addresses'].append({
                    'family': str(addr.family),
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast
                })
            
            network_info['interfaces'][interface] = interface_info
        
        # 网络IO统计
        io_counters = psutil.net_io_counters(pernic=True)
        for interface, counters in io_counters.items():
            network_info['io_counters'][interface] = {
                'bytes_sent': counters.bytes_sent,
                'bytes_recv': counters.bytes_recv,
                'packets_sent': counters.packets_sent,
                'packets_recv': counters.packets_recv,
                'errors_in': counters.errin,
                'errors_out': counters.errout,
                'drops_in': counters.dropin,
                'drops_out': counters.dropout
            }
        
        # 网络连接信息
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            network_info['connections'].append({
                'fd': conn.fd,
                'family': str(conn.family),
                'type': str(conn.type),
                'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                'status': conn.status,
                'pid': conn.pid
            })
        
        return network_info
    
    @staticmethod
    def get_process_info() -> List[Dict[str, Any]]:
        """获取进程信息
        
        Returns:
            进程信息列表
        """
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:20]
    
    @staticmethod
    def get_gpu_info() -> List[Dict[str, Any]]:
        """获取GPU信息
        
        Returns:
            GPU信息列表
        """
        try:
            gpus = GPUtil.getGPUs()
            gpu_info = []
            
            for gpu in gpus:
                gpu_info.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'driver': gpu.driver,
                    'memory_total': f"{gpu.memoryTotal} MB",
                    'memory_used': f"{gpu.memoryUsed} MB",
                    'memory_free': f"{gpu.memoryFree} MB",
                    'temperature': f"{gpu.temperature} °C",
                    'load': f"{gpu.load * 100:.1f}%"
                })
            
            return gpu_info
        except:
            return []
    
    @staticmethod
    def get_environment_variables() -> Dict[str, str]:
        """获取环境变量
        
        Returns:
            环境变量字典
        """
        return dict(os.environ)
    
    @staticmethod
    def get_installed_packages() -> List[Dict[str, str]]:
        """获取已安装的软件包列表
        
        Returns:
            软件包信息列表
        """
        packages = []
        
        try:
            # 尝试获取pip包
            result = subprocess.run(['pip', 'list', '--format=json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pip_packages = json.loads(result.stdout)
                for pkg in pip_packages:
                    packages.append({
                        'name': pkg['name'],
                        'version': pkg['version'],
                        'manager': 'pip'
                    })
        except:
            pass
        
        try:
            # 尝试获取conda包
            result = subprocess.run(['conda', 'list', '--json'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                conda_packages = json.loads(result.stdout)
                for pkg_name, pkg_version in conda_packages.items():
                    packages.append({
                        'name': pkg_name,
                        'version': pkg_version,
                        'manager': 'conda'
                    })
        except:
            pass
        
        return packages


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        """初始化系统监控器"""
        self.monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
    
    def start_monitoring(self, interval: int = 5):
        """开始系统监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval: int):
        """监控循环"""
        import threading
        while self.monitoring:
            try:
                # 收集系统指标
                metrics = {
                    'timestamp': datetime.now(),
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/').percent,
                    'network_io': psutil.net_io_counters()._asdict(),
                    'process_count': len(psutil.pids())
                }
                
                self.metrics_history.append(metrics)
                
                # 保持历史记录在合理范围内
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-500:]
                
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前系统指标
        
        Returns:
            当前系统指标
        """
        return {
            'timestamp': datetime.now(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
            'network_io': psutil.net_io_counters()._asdict(),
            'process_count': len(psutil.pids()),
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    
    def get_metrics_summary(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """获取指标摘要
        
        Args:
            duration_minutes: 时间范围（分钟）
            
        Returns:
            指标摘要
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_metrics = [m for m in self.metrics_history if m['timestamp'] >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        cpu_values = [m['cpu_percent'] for m in recent_metrics]
        memory_values = [m['memory_percent'] for m in recent_metrics]
        disk_values = [m['disk_usage'] for m in recent_metrics]
        
        return {
            'duration_minutes': duration_minutes,
            'data_points': len(recent_metrics),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'disk': {
                'avg': sum(disk_values) / len(disk_values),
                'max': max(disk_values),
                'min': min(disk_values)
            }
        }


class SystemDiagnostics:
    """系统诊断工具"""
    
    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """检查系统健康状态
        
        Returns:
            系统健康状态报告
        """
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # CPU检查
        cpu_percent = psutil.cpu_percent(interval=1)
        health_report['checks']['cpu'] = {
            'status': 'warning' if cpu_percent > 80 else 'healthy',
            'value': f"{cpu_percent:.1f}%",
            'threshold': '80%'
        }
        
        # 内存检查
        memory = psutil.virtual_memory()
        health_report['checks']['memory'] = {
            'status': 'warning' if memory.percent > 85 else 'healthy',
            'value': f"{memory.percent:.1f}%",
            'threshold': '85%'
        }
        
        # 磁盘检查
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        health_report['checks']['disk'] = {
            'status': 'warning' if disk_percent > 90 else 'healthy',
            'value': f"{disk_percent:.1f}%",
            'threshold': '90%'
        }
        
        # 进程检查
        process_count = len(psutil.pids())
        health_report['checks']['processes'] = {
            'status': 'warning' if process_count > 500 else 'healthy',
            'value': str(process_count),
            'threshold': '500'
        }
        
        # 网络检查
        try:
            # 尝试连接本地主机
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', 80))
            sock.close()
            
            health_report['checks']['network'] = {
                'status': 'healthy' if result == 0 else 'warning',
                'value': 'connected' if result == 0 else 'disconnected',
                'threshold': 'localhost:80'
            }
        except:
            health_report['checks']['network'] = {
                'status': 'unknown',
                'value': 'test failed',
                'threshold': 'localhost:80'
            }
        
        # 确定整体状态
        if any(check['status'] == 'critical' for check in health_report['checks'].values()):
            health_report['overall_status'] = 'critical'
        elif any(check['status'] == 'warning' for check in health_report['checks'].values()):
            health_report['overall_status'] = 'warning'
        
        return health_report
    
    @staticmethod
    def get_system_logs(log_type: str = 'system', lines: int = 100) -> List[str]:
        """获取系统日志
        
        Args:
            log_type: 日志类型 ('system', 'kernel', 'auth')
            lines: 获取行数
            
        Returns:
            日志内容列表
        """
        try:
            if platform.system() == 'Linux':
                if log_type == 'system':
                    cmd = ['journalctl', '--no-pager', '-n', str(lines)]
                elif log_type == 'kernel':
                    cmd = ['journalctl', '--no-pager', '-k', '-n', str(lines)]
                elif log_type == 'auth':
                    cmd = ['journalctl', '--no-pager', '-u', 'ssh', '-n', str(lines)]
                else:
                    cmd = ['journalctl', '--no-pager', '-n', str(lines)]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.stdout.split('\n') if result.returncode == 0 else []
            else:
                # Windows或其他系统的日志获取逻辑
                return ["日志获取功能在当前系统上不可用"]
        except Exception as e:
            return [f"获取日志失败: {e}"]
    
    @staticmethod
    def run_system_diagnostics() -> Dict[str, Any]:
        """运行系统诊断
        
        Returns:
            诊断结果报告
        """
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system_info': SystemInfoCollector.get_basic_info(),
            'health_check': SystemDiagnostics.check_system_health(),
            'performance_metrics': SystemMonitor().get_current_metrics(),
            'recent_errors': []
        }
        
        # 检查最近的错误日志
        try:
            logs = SystemDiagnostics.get_system_logs('system', 50)
            error_logs = [log for log in logs if 'error' in log.lower() or 'failed' in log.lower()]
            diagnostics['recent_errors'] = error_logs[-10:]  # 最近10个错误
        except:
            diagnostics['recent_errors'] = ["无法获取错误日志"]
        
        return diagnostics


def generate_system_report() -> str:
    """生成系统报告
    
    Returns:
        系统报告字符串
    """
    collector = SystemInfoCollector()
    monitor = SystemMonitor()
    
    report = f"""
=== 系统信息报告 ===
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== 基本信息 ===
{json.dumps(collector.get_basic_info(), indent=2, ensure_ascii=False)}

=== CPU信息 ===
{json.dumps(collector.get_cpu_info(), indent=2, ensure_ascii=False)}

=== 内存信息 ===
{json.dumps(collector.get_memory_info(), indent=2, ensure_ascii=False)}

=== 磁盘信息 ===
{json.dumps(collector.get_disk_info(), indent=2, ensure_ascii=False)}

=== 网络信息 ===
{json.dumps(collector.get_network_info(), indent=2, ensure_ascii=False)}

=== 当前性能指标 ===
{json.dumps(monitor.get_current_metrics(), indent=2, ensure_ascii=False)}

=== 系统健康状态 ===
{json.dumps(SystemDiagnostics.check_system_health(), indent=2, ensure_ascii=False)}
"""
    
    return report