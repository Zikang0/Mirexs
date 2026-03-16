"""
性能工具模块

提供系统性能监控、优化和基准测试工具
"""

import time
import psutil
import platform
import os
import threading
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from collections import deque
import json
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, history_size: int = 3600):
        """初始化性能监控器
        
        Args:
            history_size: 历史数据保存大小
        """
        self.history_size = history_size
        self.monitoring = False
        self.monitor_thread = None
        self.metrics = {
            'cpu': deque(maxlen=history_size),
            'memory': deque(maxlen=history_size),
            'disk_io': deque(maxlen=history_size),
            'network_io': deque(maxlen=history_size),
            'processes': deque(maxlen=history_size // 60),  # 每分钟记录一次进程
            'timestamps': deque(maxlen=history_size)
        }
        self.lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"性能监控已启动，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("性能监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        last_cpu_times = psutil.cpu_times()
        last_disk_io = psutil.disk_io_counters()
        last_net_io = psutil.net_io_counters()
        last_time = time.time()
        
        process_counter = 0
        
        while self.monitoring:
            try:
                current_time = time.time()
                time_diff = current_time - last_time
                
                # CPU监控
                cpu_percent = psutil.cpu_percent(interval=None)
                cpu_times = psutil.cpu_times()
                cpu_stats = self._calculate_cpu_stats(last_cpu_times, cpu_times, time_diff)
                
                # 内存监控
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # 磁盘IO监控
                disk_io = psutil.disk_io_counters()
                disk_stats = self._calculate_disk_stats(last_disk_io, disk_io, time_diff)
                
                # 网络IO监控
                net_io = psutil.net_io_counters()
                net_stats = self._calculate_net_stats(last_net_io, net_io, time_diff)
                
                # 记录指标
                with self.lock:
                    self.metrics['timestamps'].append(current_time)
                    self.metrics['cpu'].append({
                        'percent': cpu_percent,
                        'times': cpu_stats
                    })
                    self.metrics['memory'].append({
                        'percent': memory.percent,
                        'used': memory.used,
                        'available': memory.available,
                        'swap_percent': swap.percent
                    })
                    self.metrics['disk_io'].append(disk_stats)
                    self.metrics['network_io'].append(net_stats)
                    
                    # 每分钟记录一次进程信息
                    process_counter += 1
                    if process_counter >= 60 / interval:
                        process_counter = 0
                        self.metrics['processes'].append({
                            'timestamp': current_time,
                            'top_cpu': self._get_top_processes('cpu', 5),
                            'top_memory': self._get_top_processes('memory', 5)
                        })
                
                # 更新上次值
                last_cpu_times = cpu_times
                last_disk_io = disk_io
                last_net_io = net_io
                last_time = current_time
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"性能监控错误: {e}")
                time.sleep(interval)
    
    def _calculate_cpu_stats(self, last_times, current_times, interval) -> Dict[str, float]:
        """计算CPU统计信息"""
        return {
            'user': (current_times.user - last_times.user) / interval * 100,
            'system': (current_times.system - last_times.system) / interval * 100,
            'idle': (current_times.idle - last_times.idle) / interval * 100,
            'iowait': (getattr(current_times, 'iowait', 0) - getattr(last_times, 'iowait', 0)) / interval * 100 if hasattr(current_times, 'iowait') else 0
        }
    
    def _calculate_disk_stats(self, last_io, current_io, interval) -> Dict[str, Any]:
        """计算磁盘IO统计信息"""
        if not last_io or not current_io:
            return {}
        
        return {
            'read_speed': (current_io.read_bytes - last_io.read_bytes) / interval,
            'write_speed': (current_io.write_bytes - last_io.write_bytes) / interval,
            'read_count_speed': (current_io.read_count - last_io.read_count) / interval,
            'write_count_speed': (current_io.write_count - last_io.write_count) / interval,
            'read_speed_mb': (current_io.read_bytes - last_io.read_bytes) / interval / (1024*1024),
            'write_speed_mb': (current_io.write_bytes - last_io.write_bytes) / interval / (1024*1024)
        }
    
    def _calculate_net_stats(self, last_io, current_io, interval) -> Dict[str, Any]:
        """计算网络IO统计信息"""
        if not last_io or not current_io:
            return {}
        
        return {
            'bytes_sent_speed': (current_io.bytes_sent - last_io.bytes_sent) / interval,
            'bytes_recv_speed': (current_io.bytes_recv - last_io.bytes_recv) / interval,
            'packets_sent_speed': (current_io.packets_sent - last_io.packets_sent) / interval,
            'packets_recv_speed': (current_io.packets_recv - last_io.packets_recv) / interval,
            'bytes_sent_speed_mb': (current_io.bytes_sent - last_io.bytes_sent) / interval / (1024*1024),
            'bytes_recv_speed_mb': (current_io.bytes_recv - last_io.bytes_recv) / interval / (1024*1024)
        }
    
    def _get_top_processes(self, sort_by: str = 'cpu', limit: int = 10) -> List[Dict[str, Any]]:
        """获取CPU或内存使用率最高的进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if sort_by == 'cpu':
                    value = proc.info['cpu_percent']
                else:
                    value = proc.info['memory_percent']
                
                if value > 0:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return sorted(processes, key=lambda x: x[f'{sort_by}_percent'], reverse=True)[:limit]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前性能指标"""
        return {
            'timestamp': time.time(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=0.1),
                'per_core': psutil.cpu_percent(interval=0.1, percpu=True),
                'stats': self._calculate_cpu_stats(
                    psutil.cpu_times(), 
                    psutil.cpu_times(), 
                    0.1
                )
            },
            'memory': {
                'virtual': dict(psutil.virtual_memory()._asdict()),
                'swap': dict(psutil.swap_memory()._asdict())
            },
            'disk': {
                'usage': self._get_all_disk_usage(),
                'io': dict(psutil.disk_io_counters()._asdict()) if psutil.disk_io_counters() else {}
            },
            'network': {
                'io': dict(psutil.net_io_counters()._asdict()),
                'connections': len(psutil.net_connections())
            },
            'processes': {
                'total': len(psutil.pids()),
                'running': len([p for p in psutil.process_iter() if p.status() == 'running'])
            }
        }
    
    def _get_all_disk_usage(self) -> Dict[str, Any]:
        """获取所有磁盘使用情况"""
        usage = {}
        for part in psutil.disk_partitions():
            try:
                usage[part.mountpoint] = dict(psutil.disk_usage(part.mountpoint)._asdict())
            except PermissionError:
                continue
        return usage
    
    def get_metrics_history(self, minutes: int = 5) -> Dict[str, Any]:
        """获取历史指标数据"""
        with self.lock:
            samples_needed = minutes * 60  # 假设每秒一个样本
            cpu_history = list(self.metrics['cpu'])[-samples_needed:]
            mem_history = list(self.metrics['memory'])[-samples_needed:]
            timestamps = list(self.metrics['timestamps'])[-samples_needed:]
            
            if not cpu_history:
                return {}
            
            return {
                'timestamps': timestamps,
                'cpu_percent': [c['percent'] for c in cpu_history],
                'memory_percent': [m['percent'] for m in mem_history],
                'disk_read_speed': [d.get('read_speed_mb', 0) for d in list(self.metrics['disk_io'])[-samples_needed:]],
                'disk_write_speed': [d.get('write_speed_mb', 0) for d in list(self.metrics['disk_io'])[-samples_needed:]],
                'net_sent_speed': [n.get('bytes_sent_speed_mb', 0) for n in list(self.metrics['network_io'])[-samples_needed:]],
                'net_recv_speed': [n.get('bytes_recv_speed_mb', 0) for n in list(self.metrics['network_io'])[-samples_needed:]]
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        current = self.get_current_metrics()
        
        # 计算系统负载
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        
        # 性能评分（简单算法）
        cpu_score = 100 - current['cpu']['percent']
        memory_score = 100 - current['memory']['virtual']['percent']
        
        # 计算IO压力
        io_pressure = 0
        if current['disk'].get('io'):
            io_pressure = min(100, current['disk']['io'].get('busy_time', 0) / 1000)
        
        overall_score = (cpu_score * 0.4 + memory_score * 0.4 + (100 - io_pressure) * 0.2)
        
        return {
            'timestamp': time.time(),
            'overall_score': overall_score,
            'scores': {
                'cpu': cpu_score,
                'memory': memory_score,
                'io': 100 - io_pressure
            },
            'load_average': {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            },
            'bottleneck': self._identify_bottleneck(current),
            'recommendations': self._generate_recommendations(current)
        }
    
    def _identify_bottleneck(self, metrics: Dict[str, Any]) -> Optional[str]:
        """识别性能瓶颈"""
        if metrics['cpu']['percent'] > 80:
            return 'CPU'
        elif metrics['memory']['virtual']['percent'] > 85:
            return 'Memory'
        elif metrics['disk'].get('io') and metrics['disk']['io'].get('busy_time', 0) > 500:
            return 'Disk IO'
        return None
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if metrics['cpu']['percent'] > 80:
            recommendations.append("CPU使用率过高，考虑升级CPU或优化CPU密集型任务")
        
        if metrics['memory']['virtual']['percent'] > 85:
            recommendations.append("内存使用率过高，建议增加内存或检查内存泄漏")
        
        if metrics['disk'].get('io') and metrics['disk']['io'].get('busy_time', 0) > 500:
            recommendations.append("磁盘IO繁忙，考虑使用SSD或优化IO操作")
        
        top_cpu = self._get_top_processes('cpu', 3)
        if top_cpu:
            high_cpu = [p['name'] for p in top_cpu if p['cpu_percent'] > 50]
            if high_cpu:
                recommendations.append(f"进程 {', '.join(high_cpu)} 占用CPU过高")
        
        return recommendations


class SystemBenchmark:
    """系统基准测试"""
    
    def __init__(self):
        self.results = {}
    
    def run_cpu_benchmark(self, duration: int = 10) -> Dict[str, Any]:
        """运行CPU基准测试"""
        import multiprocessing
        import timeit
        
        def cpu_intensive_task(n):
            result = 0
            for i in range(n):
                result += i * i
            return result
        
        # 单核性能测试
        single_start = time.time()
        for _ in range(10):
            cpu_intensive_task(1000000)
        single_time = time.time() - single_start
        
        # 多核性能测试
        cores = multiprocessing.cpu_count()
        pool = multiprocessing.Pool(cores)
        multi_start = time.time()
        pool.map(cpu_intensive_task, [1000000] * cores)
        multi_time = time.time() - multi_start
        pool.close()
        pool.join()
        
        # 计算分数
        base_score = 1000
        single_score = base_score / single_time
        multi_score = base_score * cores / multi_time
        
        return {
            'cores': cores,
            'single_core_time': single_time,
            'multi_core_time': multi_time,
            'single_core_score': single_score,
            'multi_core_score': multi_score,
            'parallel_efficiency': multi_score / (single_score * cores)
        }
    
    def run_memory_benchmark(self, size_mb: int = 100) -> Dict[str, Any]:
        """运行内存基准测试"""
        import array
        
        size = size_mb * 1024 * 1024 // 8  # 8字节每项
        
        # 写入测试
        arr = array.array('d', [0.0]) * size
        write_start = time.time()
        for i in range(size):
            arr[i] = float(i)
        write_time = time.time() - write_start
        
        # 读取测试
        read_start = time.time()
        total = 0.0
        for i in range(size):
            total += arr[i]
        read_time = time.time() - read_start
        
        # 计算带宽
        data_size = size * 8  # 字节
        write_bandwidth = data_size / write_time / (1024*1024*1024)  # GB/s
        read_bandwidth = data_size / read_time / (1024*1024*1024)  # GB/s
        
        return {
            'size_mb': size_mb,
            'write_time': write_time,
            'read_time': read_time,
            'write_bandwidth_gbps': write_bandwidth * 8,  # Gbps
            'read_bandwidth_gbps': read_bandwidth * 8,
            'write_speed_gbs': write_bandwidth,
            'read_speed_gbs': read_bandwidth
        }
    
    def run_disk_benchmark(self, file_size_mb: int = 100) -> Dict[str, Any]:
        """运行磁盘基准测试"""
        import tempfile
        import shutil
        
        test_dir = tempfile.mkdtemp()
        test_file = os.path.join(test_dir, 'disk_test.tmp')
        
        # 准备测试数据
        data = os.urandom(1024 * 1024)  # 1MB
        
        # 顺序写入测试
        write_start = time.time()
        with open(test_file, 'wb') as f:
            for _ in range(file_size_mb):
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.time() - write_start
        write_speed = (file_size_mb * 1024 * 1024) / write_time / (1024*1024)  # MB/s
        
        # 顺序读取测试
        read_start = time.time()
        with open(test_file, 'rb') as f:
            while f.read(1024 * 1024):
                pass
        read_time = time.time() - read_start
        read_speed = (file_size_mb * 1024 * 1024) / read_time / (1024*1024)  # MB/s
        
        # 清理
        shutil.rmtree(test_dir)
        
        return {
            'file_size_mb': file_size_mb,
            'write_speed_mbps': write_speed,
            'read_speed_mbps': read_speed,
            'write_time': write_time,
            'read_time': read_time
        }
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整基准测试"""
        self.results = {
            'timestamp': time.time(),
            'system_info': {
                'platform': platform.platform(),
                'processor': platform.processor(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'python_version': platform.python_version()
            },
            'cpu_benchmark': self.run_cpu_benchmark(),
            'memory_benchmark': self.run_memory_benchmark(),
            'disk_benchmark': self.run_disk_benchmark()
        }
        
        # 计算综合分数
        cpu_score = self.results['cpu_benchmark']['single_core_score']
        memory_score = self.results['memory_benchmark']['write_bandwidth_gbps'] * 10
        disk_score = self.results['disk_benchmark']['read_speed_mbps']
        
        self.results['overall_score'] = (cpu_score + memory_score + disk_score) / 3
        
        return self.results
    
    def save_results(self, filepath: str):
        """保存测试结果"""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"基准测试结果已保存到 {filepath}")


class PerformanceOptimizer:
    """性能优化器"""
    
    @staticmethod
    def set_process_priority(pid: int, priority: str) -> bool:
        """设置进程优先级"""
        priority_map = {
            'high': -20,
            'above_normal': -10,
            'normal': 0,
            'below_normal': 10,
            'idle': 19
        }
        
        try:
            if platform.system() == 'Windows':
                import win32process
                import win32con
                priority_map_win = {
                    'high': win32process.HIGH_PRIORITY_CLASS,
                    'above_normal': win32process.ABOVE_NORMAL_PRIORITY_CLASS,
                    'normal': win32process.NORMAL_PRIORITY_CLASS,
                    'below_normal': win32process.BELOW_NORMAL_PRIORITY_CLASS,
                    'idle': win32process.IDLE_PRIORITY_CLASS
                }
                handle = win32process.OpenProcess(win32con.PROCESS_SET_INFORMATION, False, pid)
                win32process.SetPriorityClass(handle, priority_map_win[priority])
                win32process.CloseHandle(handle)
                return True
            else:
                os.nice(priority_map[priority])
                return True
        except Exception as e:
            logger.error(f"设置进程优先级失败: {e}")
            return False
    
    @staticmethod
    def set_cpu_affinity(pid: int, cpus: List[int]) -> bool:
        """设置CPU亲和性"""
        try:
            if platform.system() == 'Windows':
                import win32process
                mask = 0
                for cpu in cpus:
                    mask |= 1 << cpu
                handle = win32process.OpenProcess(win32con.PROCESS_SET_INFORMATION, False, pid)
                win32process.SetProcessAffinityMask(handle, mask)
                win32process.CloseHandle(handle)
                return True
            else:
                import psutil
                proc = psutil.Process(pid)
                proc.cpu_affinity(cpus)
                return True
        except Exception as e:
            logger.error(f"设置CPU亲和性失败: {e}")
            return False
    
    @staticmethod
    def get_system_tuning_recommendations() -> List[Dict[str, Any]]:
        """获取系统调优建议"""
        recommendations = []
        
        # 检查系统参数
        if platform.system() == 'Linux':
            # 检查TCP缓冲区
            try:
                with open('/proc/sys/net/core/rmem_max', 'r') as f:
                    rmem = int(f.read().strip())
                if rmem < 16777216:
                    recommendations.append({
                        'parameter': 'net.core.rmem_max',
                        'current': rmem,
                        'recommended': 16777216,
                        'description': '增加TCP接收缓冲区大小以提高网络性能'
                    })
            except:
                pass
            
            # 检查文件描述符限制
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft < 65535:
                recommendations.append({
                    'parameter': 'RLIMIT_NOFILE',
                    'current': soft,
                    'recommended': 65535,
                    'description': '增加文件描述符限制以支持更多并发连接'
                })
        
        # 检查内存
        memory = psutil.virtual_memory()
        if memory.available < 512 * 1024 * 1024:  # 小于512MB可用内存
            recommendations.append({
                'parameter': 'available_memory',
                'current': f"{memory.available / (1024*1024):.1f}MB",
                'recommended': '>512MB',
                'description': '可用内存不足，考虑增加物理内存'
            })
        
        # 检查磁盘
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                if usage.percent > 90:
                    recommendations.append({
                        'parameter': f'disk_usage_{part.mountpoint}',
                        'current': f"{usage.percent}%",
                        'recommended': '<90%',
                        'description': f'磁盘 {part.mountpoint} 使用率过高，考虑清理或扩容'
                    })
            except:
                continue
        
        return recommendations


def monitor_performance(interval: float = 1.0, duration: int = 60) -> Dict[str, Any]:
    """监控性能一段时间"""
    monitor = PerformanceMonitor()
    monitor.start_monitoring(interval)
    time.sleep(duration)
    monitor.stop_monitoring()
    
    return {
        'summary': monitor.get_performance_summary(),
        'history': monitor.get_metrics_history(duration // 60)
    }


def benchmark_system() -> Dict[str, Any]:
    """基准测试系统性能"""
    benchmark = SystemBenchmark()
    return benchmark.run_full_benchmark()


def get_performance_score() -> Dict[str, Any]:
    """获取系统性能评分"""
    monitor = PerformanceMonitor()
    current = monitor.get_current_metrics()
    
    # 计算各项得分
    cpu_score = 100 - current['cpu']['percent']
    memory_score = 100 - current['memory']['virtual']['percent']
    
    # 计算IO得分
    io_score = 100
    if current['disk'].get('io'):
        io_score = 100 - min(100, current['disk']['io'].get('busy_time', 0) / 10)
    
    # 计算综合得分
    overall = (cpu_score * 0.4 + memory_score * 0.4 + io_score * 0.2)
    
    return {
        'overall': overall,
        'cpu_score': cpu_score,
        'memory_score': memory_score,
        'io_score': io_score,
        'timestamp': time.time()
    }