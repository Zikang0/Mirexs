"""
系统指标模块

提供系统性能指标收集、计算和分析工具
"""

import psutil
import platform
import time
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


class CPUMetrics:
    """CPU指标"""
    
    @staticmethod
    def get_cpu_metrics() -> Dict[str, Any]:
        """获取CPU指标"""
        metrics = {
            'timestamp': time.time(),
            'percent': psutil.cpu_percent(interval=0.1),
            'per_cpu': psutil.cpu_percent(interval=0.1, percpu=True),
            'count': {
                'physical': psutil.cpu_count(logical=False),
                'logical': psutil.cpu_count(logical=True)
            }
        }
        
        # CPU频率
        freq = psutil.cpu_freq()
        if freq:
            metrics['frequency'] = {
                'current': freq.current,
                'min': freq.min,
                'max': freq.max
            }
        
        # CPU时间
        times = psutil.cpu_times()
        metrics['times'] = {
            'user': times.user,
            'system': times.system,
            'idle': times.idle,
            'iowait': getattr(times, 'iowait', 0),
            'irq': getattr(times, 'irq', 0),
            'softirq': getattr(times, 'softirq', 0),
            'steal': getattr(times, 'steal', 0),
            'guest': getattr(times, 'guest', 0)
        }
        
        # CPU统计
        stats = psutil.cpu_stats()
        metrics['stats'] = {
            'ctx_switches': stats.ctx_switches,
            'interrupts': stats.interrupts,
            'soft_interrupts': stats.soft_interrupts,
            'syscalls': stats.syscalls
        }
        
        return metrics
    
    @staticmethod
    def calculate_cpu_score(metrics: Dict[str, Any]) -> float:
        """计算CPU性能分数"""
        # 基于CPU使用率和频率计算
        cpu_score = 100 - metrics['percent']
        
        # 频率因子
        freq_factor = 1.0
        if 'frequency' in metrics:
            freq_factor = metrics['frequency']['current'] / 2000  # 假设2GHz为基准
        
        return cpu_score * freq_factor


class MemoryMetrics:
    """内存指标"""
    
    @staticmethod
    def get_memory_metrics() -> Dict[str, Any]:
        """获取内存指标"""
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        metrics = {
            'timestamp': time.time(),
            'virtual': {
                'total': virtual.total,
                'available': virtual.available,
                'used': virtual.used,
                'free': virtual.free,
                'percent': virtual.percent,
                'active': getattr(virtual, 'active', 0),
                'inactive': getattr(virtual, 'inactive', 0),
                'buffers': getattr(virtual, 'buffers', 0),
                'cached': getattr(virtual, 'cached', 0),
                'shared': getattr(virtual, 'shared', 0),
                'slab': getattr(virtual, 'slab', 0)
            },
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent,
                'sin': swap.sin,
                'sout': swap.sout
            }
        }
        
        return metrics
    
    @staticmethod
    def calculate_memory_score(metrics: Dict[str, Any]) -> float:
        """计算内存性能分数"""
        virtual = metrics['virtual']
        return 100 - virtual['percent']


class DiskMetrics:
    """磁盘指标"""
    
    @staticmethod
    def get_disk_metrics() -> Dict[str, Any]:
        """获取磁盘指标"""
        metrics = {
            'timestamp': time.time(),
            'partitions': [],
            'io': {}
        }
        
        # 分区使用情况
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                metrics['partitions'].append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'fstype': part.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent
                })
            except PermissionError:
                continue
        
        # IO统计
        io_counters = psutil.disk_io_counters(perdisk=True)
        if io_counters:
            for disk, io in io_counters.items():
                metrics['io'][disk] = {
                    'read_count': io.read_count,
                    'write_count': io.write_count,
                    'read_bytes': io.read_bytes,
                    'write_bytes': io.write_bytes,
                    'read_time': io.read_time,
                    'write_time': io.write_time,
                    'read_merged_count': getattr(io, 'read_merged_count', 0),
                    'write_merged_count': getattr(io, 'write_merged_count', 0),
                    'busy_time': getattr(io, 'busy_time', 0)
                }
        
        return metrics
    
    @staticmethod
    def calculate_disk_score(metrics: Dict[str, Any]) -> float:
        """计算磁盘性能分数"""
        if not metrics['partitions']:
            return 100
        
        # 计算平均使用率
        avg_usage = sum(p['percent'] for p in metrics['partitions']) / len(metrics['partitions'])
        return 100 - avg_usage


class NetworkMetrics:
    """网络指标"""
    
    @staticmethod
    def get_network_metrics() -> Dict[str, Any]:
        """获取网络指标"""
        metrics = {
            'timestamp': time.time(),
            'io': {},
            'connections': len(psutil.net_connections()),
            'stats': {}
        }
        
        # IO统计
        io_counters = psutil.net_io_counters(pernic=True)
        for nic, io in io_counters.items():
            metrics['io'][nic] = {
                'bytes_sent': io.bytes_sent,
                'bytes_recv': io.bytes_recv,
                'packets_sent': io.packets_sent,
                'packets_recv': io.packets_recv,
                'errin': io.errin,
                'errout': io.errout,
                'dropin': io.dropin,
                'dropout': io.dropout
            }
        
        # 接口统计
        stats = psutil.net_if_stats()
        for nic, stat in stats.items():
            metrics['stats'][nic] = {
                'isup': stat.isup,
                'duplex': stat.duplex,
                'speed': stat.speed,
                'mtu': stat.mtu
            }
        
        return metrics
    
    @staticmethod
    def calculate_network_score(metrics: Dict[str, Any]) -> float:
        """计算网络性能分数"""
        # 基于连接数和错误率计算
        error_rate = 0
        total_packets = 0
        
        for nic, io in metrics['io'].items():
            packets = io['packets_sent'] + io['packets_recv']
            errors = io['errin'] + io['errout'] + io['dropin'] + io['dropout']
            
            total_packets += packets
            error_rate += errors
        
        if total_packets > 0:
            error_rate = error_rate / total_packets * 100
        else:
            error_rate = 0
        
        return 100 - error_rate


class ProcessMetrics:
    """进程指标"""
    
    @staticmethod
    def get_process_metrics(pid: Optional[int] = None) -> Dict[str, Any]:
        """获取进程指标"""
        if pid is None:
            pid = os.getpid()
        
        try:
            proc = psutil.Process(pid)
            
            metrics = {
                'pid': proc.pid,
                'name': proc.name(),
                'exe': proc.exe(),
                'cmdline': ' '.join(proc.cmdline()),
                'status': proc.status(),
                'create_time': proc.create_time(),
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_percent': proc.memory_percent(),
                'memory_info': dict(proc.memory_info()._asdict()),
                'num_threads': proc.num_threads(),
                'connections': len(proc.connections()),
                'open_files': len(proc.open_files())
            }
            
            # IO统计
            try:
                io_counters = proc.io_counters()
                metrics['io'] = {
                    'read_count': io_counters.read_count,
                    'write_count': io_counters.write_count,
                    'read_bytes': io_counters.read_bytes,
                    'write_bytes': io_counters.write_bytes,
                    'read_chars': getattr(io_counters, 'read_chars', 0),
                    'write_chars': getattr(io_counters, 'write_chars', 0)
                }
            except (psutil.AccessDenied, AttributeError):
                metrics['io'] = {}
            
            return metrics
            
        except psutil.NoSuchProcess:
            logger.error(f"进程 {pid} 不存在")
            return {}
        except psutil.AccessDenied:
            logger.error(f"无法访问进程 {pid}")
            return {}
    
    @staticmethod
    def get_top_processes(limit: int = 10, sort_by: str = 'cpu') -> List[Dict[str, Any]]:
        """获取资源占用最高的进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                proc_info = proc.info
                if sort_by == 'cpu' and proc_info['cpu_percent'] > 0:
                    processes.append(proc_info)
                elif sort_by == 'memory' and proc_info['memory_percent'] > 0:
                    processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if sort_by == 'cpu':
            return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
        else:
            return sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]


class SystemMetricsCollector:
    """系统指标收集器"""
    
    def __init__(self, history_size: int = 3600):
        """初始化系统指标收集器
        
        Args:
            history_size: 历史数据大小
        """
        self.history_size = history_size
        self.collecting = False
        self.collector_thread = None
        self.metrics_history = deque(maxlen=history_size)
        self.lock = threading.Lock()
    
    def start_collecting(self, interval: float = 5.0):
        """开始收集指标
        
        Args:
            interval: 收集间隔
        """
        if self.collecting:
            return
        
        self.collecting = True
        self.collector_thread = threading.Thread(
            target=self._collect_loop,
            args=(interval,),
            daemon=True
        )
        self.collector_thread.start()
        logger.info(f"系统指标收集已启动，间隔: {interval}秒")
    
    def stop_collecting(self):
        """停止收集指标"""
        self.collecting = False
        if self.collector_thread:
            self.collector_thread.join(timeout=2)
        logger.info("系统指标收集已停止")
    
    def _collect_loop(self, interval: float):
        """收集循环"""
        while self.collecting:
            try:
                metrics = self.collect_current_metrics()
                with self.lock:
                    self.metrics_history.append(metrics)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"指标收集错误: {e}")
                time.sleep(interval)
    
    def collect_current_metrics(self) -> Dict[str, Any]:
        """收集当前指标"""
        return {
            'timestamp': time.time(),
            'cpu': CPUMetrics.get_cpu_metrics(),
            'memory': MemoryMetrics.get_memory_metrics(),
            'disk': DiskMetrics.get_disk_metrics(),
            'network': NetworkMetrics.get_network_metrics(),
            'process': ProcessMetrics.get_top_processes(5)
        }
    
    def get_metrics_history(self, minutes: int = 5) -> Dict[str, Any]:
        """获取指标历史"""
        with self.lock:
            samples_needed = int(minutes * 60 / 5)  # 假设5秒一个样本
            recent = list(self.metrics_history)[-samples_needed:]
            
            if not recent:
                return {}
            
            return {
                'timestamps': [m['timestamp'] for m in recent],
                'cpu_percent': [m['cpu']['percent'] for m in recent],
                'memory_percent': [m['memory']['virtual']['percent'] for m in recent],
                'disk_used': [sum(p['used'] for p in m['disk']['partitions']) / (1024**3) for m in recent],
                'network_bytes_sent': [sum(n['io'][nic]['bytes_sent'] for nic in n['io']) / (1024**2) for n in recent],
                'network_bytes_recv': [sum(n['io'][nic]['bytes_recv'] for nic in n['io']) / (1024**2) for n in recent],
                'process_count': [len(psutil.pids()) for _ in recent]
            }
    
    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """获取指标摘要"""
        history = self.get_metrics_history(minutes)
        
        if not history:
            return {}
        
        return {
            'timestamp': time.time(),
            'duration_minutes': minutes,
            'samples': len(history['timestamps']),
            'cpu': {
                'avg': sum(history['cpu_percent']) / len(history['cpu_percent']),
                'max': max(history['cpu_percent']),
                'min': min(history['cpu_percent']),
                'current': history['cpu_percent'][-1] if history['cpu_percent'] else 0
            },
            'memory': {
                'avg': sum(history['memory_percent']) / len(history['memory_percent']),
                'max': max(history['memory_percent']),
                'min': min(history['memory_percent']),
                'current': history['memory_percent'][-1] if history['memory_percent'] else 0
            },
            'disk': {
                'avg_used_gb': sum(history['disk_used']) / len(history['disk_used'])
            },
            'network': {
                'avg_sent_mbps': sum(history['network_bytes_sent']) / len(history['network_bytes_sent']),
                'avg_recv_mbps': sum(history['network_bytes_recv']) / len(history['network_bytes_recv'])
            }
        }
    
    def calculate_system_score(self) -> Dict[str, Any]:
        """计算系统综合评分"""
        current = self.collect_current_metrics()
        
        # 计算各组件分数
        cpu_score = CPUMetrics.calculate_cpu_score(current['cpu'])
        memory_score = MemoryMetrics.calculate_memory_score(current['memory'])
        disk_score = DiskMetrics.calculate_disk_score(current['disk'])
        network_score = NetworkMetrics.calculate_network_score(current['network'])
        
        # 综合分数
        overall_score = (cpu_score * 0.3 + memory_score * 0.3 + 
                        disk_score * 0.2 + network_score * 0.2)
        
        # 确定瓶颈
        scores = {
            'cpu': cpu_score,
            'memory': memory_score,
            'disk': disk_score,
            'network': network_score
        }
        bottleneck = min(scores, key=scores.get)
        
        return {
            'timestamp': time.time(),
            'overall_score': overall_score,
            'component_scores': scores,
            'bottleneck': bottleneck,
            'grade': self._get_grade(overall_score)
        }
    
    def _get_grade(self, score: float) -> str:
        """获取等级"""
        if score >= 90:
            return '优秀'
        elif score >= 75:
            return '良好'
        elif score >= 60:
            return '中等'
        elif score >= 40:
            return '较差'
        else:
            return '极差'


class MetricsReporter:
    """指标报告器"""
    
    def __init__(self, collector: SystemMetricsCollector):
        """初始化指标报告器
        
        Args:
            collector: 指标收集器
        """
        self.collector = collector
    
    def generate_report(self, format: str = 'text') -> Union[str, Dict[str, Any]]:
        """生成报告
        
        Args:
            format: 报告格式 ('text', 'json', 'html')
            
        Returns:
            报告内容
        """
        current = self.collector.collect_current_metrics()
        summary = self.collector.get_metrics_summary(5)
        score = self.collector.calculate_system_score()
        
        if format == 'json':
            return {
                'current': current,
                'summary': summary,
                'score': score,
                'timestamp': time.time()
            }
        
        elif format == 'html':
            return self._generate_html_report(current, summary, score)
        
        else:  # text
            return self._generate_text_report(current, summary, score)
    
    def _generate_text_report(self, current: Dict, summary: Dict, score: Dict) -> str:
        """生成文本报告"""
        report = []
        report.append("=" * 60)
        report.append("系统性能报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # CPU信息
        report.append("CPU 信息:")
        report.append(f"  使用率: {current['cpu']['percent']:.1f}%")
        report.append(f"  物理核心: {current['cpu']['count']['physical']}")
        report.append(f"  逻辑核心: {current['cpu']['count']['logical']}")
        report.append("")
        
        # 内存信息
        mem = current['memory']['virtual']
        report.append("内存信息:")
        report.append(f"  使用率: {mem['percent']:.1f}%")
        report.append(f"  总计: {mem['total'] / (1024**3):.2f} GB")
        report.append(f"  已用: {mem['used'] / (1024**3):.2f} GB")
        report.append(f"  可用: {mem['available'] / (1024**3):.2f} GB")
        report.append("")
        
        # 磁盘信息
        report.append("磁盘信息:")
        for part in current['disk']['partitions'][:3]:
            report.append(f"  {part['mountpoint']}: {part['percent']:.1f}%")
        report.append("")
        
        # 系统评分
        report.append("系统评分:")
        report.append(f"  综合评分: {score['overall_score']:.1f} ({score['grade']})")
        report.append(f"  瓶颈组件: {score['bottleneck']}")
        report.append("")
        
        # 摘要
        report.append("5分钟摘要:")
        report.append(f"  平均CPU: {summary['cpu']['avg']:.1f}%")
        report.append(f"  平均内存: {summary['memory']['avg']:.1f}%")
        
        return "\n".join(report)
    
    def _generate_html_report(self, current: Dict, summary: Dict, score: Dict) -> str:
        """生成HTML报告"""
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("    <title>系统性能报告</title>")
        html.append("    <style>")
        html.append("        body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append("        h1 { color: #333; }")
        html.append("        .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }")
        html.append("        .metric { margin: 5px 0; }")
        html.append("        .good { color: green; }")
        html.append("        .warning { color: orange; }")
        html.append("        .critical { color: red; }")
        html.append("        table { border-collapse: collapse; width: 100%; }")
        html.append("        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html.append("        th { background-color: #f2f2f2; }")
        html.append("    </style>")
        html.append("</head>")
        html.append("<body>")
        
        html.append(f"<h1>系统性能报告</h1>")
        html.append(f"<p>生成时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}</p>")
        
        # 系统评分
        html.append("<div class='section'>")
        html.append("<h2>系统评分</h2>")
        score_class = 'good' if score['overall_score'] >= 80 else 'warning' if score['overall_score'] >= 60 else 'critical'
        html.append(f"<div class='metric {score_class}'>综合评分: {score['overall_score']:.1f} ({score['grade']})</div>")
        html.append(f"<div class='metric'>瓶颈组件: {score['bottleneck']}</div>")
        html.append("</div>")
        
        # CPU信息
        html.append("<div class='section'>")
        html.append("<h2>CPU信息</h2>")
        html.append(f"<div class='metric'>使用率: {current['cpu']['percent']:.1f}%</div>")
        html.append(f"<div class='metric'>物理核心: {current['cpu']['count']['physical']}</div>")
        html.append(f"<div class='metric'>逻辑核心: {current['cpu']['count']['logical']}</div>")
        html.append("</div>")
        
        # 内存信息
        html.append("<div class='section'>")
        html.append("<h2>内存信息</h2>")
        mem = current['memory']['virtual']
        html.append(f"<div class='metric'>使用率: {mem['percent']:.1f}%</div>")
        html.append(f"<div class='metric'>总计: {mem['total'] / (1024**3):.2f} GB</div>")
        html.append(f"<div class='metric'>已用: {mem['used'] / (1024**3):.2f} GB</div>")
        html.append(f"<div class='metric'>可用: {mem['available'] / (1024**3):.2f} GB</div>")
        html.append("</div>")
        
        # 磁盘信息
        html.append("<div class='section'>")
        html.append("<h2>磁盘信息</h2>")
        html.append("<table>")
        html.append("<tr><th>挂载点</th><th>使用率</th><th>总计(GB)</th><th>已用(GB)</th><th>可用(GB)</th></tr>")
        for part in current['disk']['partitions'][:5]:
            html.append(f"<tr>")
            html.append(f"<td>{part['mountpoint']}</td>")
            html.append(f"<td>{part['percent']:.1f}%</td>")
            html.append(f"<td>{part['total'] / (1024**3):.2f}</td>")
            html.append(f"<td>{part['used'] / (1024**3):.2f}</td>")
            html.append(f"<td>{part['free'] / (1024**3):.2f}</td>")
            html.append(f"</tr>")
        html.append("</table>")
        html.append("</div>")
        
        # 摘要
        html.append("<div class='section'>")
        html.append("<h2>5分钟摘要</h2>")
        html.append(f"<div class='metric'>平均CPU: {summary['cpu']['avg']:.1f}%</div>")
        html.append(f"<div class='metric'>平均内存: {summary['memory']['avg']:.1f}%</div>")
        html.append(f"<div class='metric'>平均磁盘使用: {summary['disk']['avg_used_gb']:.2f} GB</div>")
        html.append("</div>")
        
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)
    
    def save_report(self, filepath: str, format: str = 'text'):
        """保存报告"""
        report = self.generate_report(format)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(report, dict):
                json.dump(report, f, indent=2, ensure_ascii=False)
            else:
                f.write(report)
        
        logger.info(f"报告已保存到 {filepath}")


def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    collector = SystemMetricsCollector()
    current = collector.collect_current_metrics()
    
    health = {
        'timestamp': time.time(),
        'status': 'healthy',
        'checks': {}
    }
    
    # CPU检查
    cpu_percent = current['cpu']['percent']
    health['checks']['cpu'] = {
        'status': 'warning' if cpu_percent > 80 else 'critical' if cpu_percent > 95 else 'healthy',
        'value': f"{cpu_percent:.1f}%",
        'threshold': '80% / 95%'
    }
    
    # 内存检查
    mem_percent = current['memory']['virtual']['percent']
    health['checks']['memory'] = {
        'status': 'warning' if mem_percent > 85 else 'critical' if mem_percent > 95 else 'healthy',
        'value': f"{mem_percent:.1f}%",
        'threshold': '85% / 95%'
    }
    
    # 磁盘检查
    for part in current['disk']['partitions']:
        if part['mountpoint'] == '/':
            disk_percent = part['percent']
            health['checks']['disk'] = {
                'status': 'warning' if disk_percent > 85 else 'critical' if disk_percent > 95 else 'healthy',
                'value': f"{disk_percent:.1f}%",
                'threshold': '85% / 95%'
            }
            break
    
    # 确定整体状态
    if any(c['status'] == 'critical' for c in health['checks'].values()):
        health['status'] = 'critical'
    elif any(c['status'] == 'warning' for c in health['checks'].values()):
        health['status'] = 'warning'
    
    return health