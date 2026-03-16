"""
进程管理器：负责管理系统进程
"""
import psutil
import os
import signal
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProcessPriority(Enum):
    """进程优先级枚举"""
    IDLE = "idle"
    BELOW_NORMAL = "below_normal"
    NORMAL = "normal"
    ABOVE_NORMAL = "above_normal"
    HIGH = "high"
    REALTIME = "realtime"

@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_usage: int  # bytes
    create_time: float
    executable_path: Optional[str] = None
    command_line: Optional[str] = None
    username: Optional[str] = None

class ProcessManager:
    """进程管理器类"""
    
    def __init__(self):
        self.process_monitor = ProcessMonitor()
        self.process_analyzer = ProcessAnalyzer()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def get_all_processes(self) -> List[ProcessInfo]:
        """获取所有进程信息"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                       'memory_percent', 'memory_info', 'create_time',
                                       'exe', 'cmdline', 'username']):
            try:
                process_info = ProcessInfo(
                    pid=proc.info['pid'],
                    name=proc.info['name'],
                    status=proc.info['status'],
                    cpu_percent=proc.info['cpu_percent'] or 0.0,
                    memory_percent=proc.info['memory_percent'] or 0.0,
                    memory_usage=proc.info['memory_info'].rss if proc.info['memory_info'] else 0,
                    create_time=proc.info['create_time'],
                    executable_path=proc.info['exe'],
                    command_line=' '.join(proc.info['cmdline']) if proc.info['cmdline'] else None,
                    username=proc.info['username']
                )
                processes.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def get_process_by_pid(self, pid: int) -> Optional[ProcessInfo]:
        """根据PID获取进程信息"""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return ProcessInfo(
                    pid=proc.pid,
                    name=proc.name(),
                    status=proc.status(),
                    cpu_percent=proc.cpu_percent(),
                    memory_percent=proc.memory_percent(),
                    memory_usage=proc.memory_info().rss,
                    create_time=proc.create_time(),
                    executable_path=proc.exe(),
                    command_line=' '.join(proc.cmdline()) if proc.cmdline() else None,
                    username=proc.username()
                )
        except psutil.NoSuchProcess:
            return None
    
    def terminate_process(self, pid: int, force: bool = False) -> bool:
        """终止进程"""
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            
            # 等待进程结束
            proc.wait(timeout=10)
            logger.info(f"成功终止进程: {pid}")
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"进程不存在: {pid}")
            return False
        except Exception as e:
            logger.error(f"终止进程失败 {pid}: {str(e)}")
            return False
    
    def set_process_priority(self, pid: int, priority: ProcessPriority) -> bool:
        """设置进程优先级"""
        try:
            proc = psutil.Process(pid)
            
            priority_map = {
                ProcessPriority.IDLE: psutil.IDLE_PRIORITY_CLASS,
                ProcessPriority.BELOW_NORMAL: psutil.BELOW_NORMAL_PRIORITY_CLASS,
                ProcessPriority.NORMAL: psutil.NORMAL_PRIORITY_CLASS,
                ProcessPriority.ABOVE_NORMAL: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                ProcessPriority.HIGH: psutil.HIGH_PRIORITY_CLASS,
                ProcessPriority.REALTIME: psutil.REALTIME_PRIORITY_CLASS
            }
            
            proc.nice(priority_map[priority])
            logger.info(f"设置进程 {pid} 优先级为: {priority.value}")
            return True
            
        except Exception as e:
            logger.error(f"设置进程优先级失败 {pid}: {str(e)}")
            return False
    
    def get_process_children(self, pid: int) -> List[ProcessInfo]:
        """获取进程的子进程"""
        try:
            proc = psutil.Process(pid)
            children = []
            for child in proc.children(recursive=True):
                children.append(self.get_process_by_pid(child.pid))
            return [child for child in children if child is not None]
        except psutil.NoSuchProcess:
            return []
    
    def get_process_resource_usage(self, pid: int) -> Dict[str, Any]:
        """获取进程资源使用情况"""
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return {
                    'cpu_percent': proc.cpu_percent(),
                    'memory_percent': proc.memory_percent(),
                    'memory_usage': proc.memory_info().rss,
                    'io_counters': proc.io_counters()._asdict() if proc.io_counters() else None,
                    'num_threads': proc.num_threads(),
                    'num_handles': proc.num_handles() if hasattr(proc, 'num_handles') else None
                }
        except psutil.NoSuchProcess:
            return {}
    
    def find_processes_by_name(self, name: str) -> List[ProcessInfo]:
        """根据进程名查找进程"""
        processes = self.get_all_processes()
        return [p for p in processes if name.lower() in p.name.lower()]
    
    def start_monitoring(self, pid: int, interval: float = 1.0) -> bool:
        """开始监控进程"""
        return self.process_monitor.start_monitoring(pid, interval)
    
    def stop_monitoring(self, pid: int) -> bool:
        """停止监控进程"""
        return self.process_monitor.stop_monitoring(pid)
    
    def get_monitoring_data(self, pid: int) -> Optional[Dict[str, Any]]:
        """获取进程监控数据"""
        return self.process_monitor.get_monitoring_data(pid)

class ProcessMonitor:
    """进程监控器"""
    
    def __init__(self):
        self.monitored_processes: Dict[int, threading.Thread] = {}
        self.monitoring_data: Dict[int, List[Dict[str, Any]]] = {}
        self._lock = threading.Lock()
    
    def start_monitoring(self, pid: int, interval: float = 1.0) -> bool:
        """开始监控进程"""
        try:
            # 检查进程是否存在
            psutil.Process(pid)
            
            with self._lock:
                if pid in self.monitored_processes:
                    return False  # 已在监控中
                
                # 启动监控线程
                monitor_thread = threading.Thread(
                    target=self._monitor_process,
                    args=(pid, interval),
                    daemon=True
                )
                self.monitored_processes[pid] = monitor_thread
                self.monitoring_data[pid] = []
                monitor_thread.start()
                
            logger.info(f"开始监控进程: {pid}")
            return True
            
        except psutil.NoSuchProcess:
            return False
    
    def stop_monitoring(self, pid: int) -> bool:
        """停止监控进程"""
        with self._lock:
            if pid in self.monitored_processes:
                # 标记停止，线程会在下次检查时退出
                del self.monitored_processes[pid]
                logger.info(f"停止监控进程: {pid}")
                return True
        return False
    
    def _monitor_process(self, pid: int, interval: float):
        """监控进程的内部方法"""
        try:
            proc = psutil.Process(pid)
            while pid in self.monitored_processes:
                try:
                    with proc.oneshot():
                        data = {
                            'timestamp': datetime.now().isoformat(),
                            'cpu_percent': proc.cpu_percent(),
                            'memory_usage': proc.memory_info().rss,
                            'memory_percent': proc.memory_percent(),
                            'num_threads': proc.num_threads(),
                            'status': proc.status()
                        }
                    
                    with self._lock:
                        if pid in self.monitoring_data:
                            self.monitoring_data[pid].append(data)
                            # 只保留最近1000条数据
                            if len(self.monitoring_data[pid]) > 1000:
                                self.monitoring_data[pid].pop(0)
                    
                    time.sleep(interval)
                    
                except psutil.NoSuchProcess:
                    break
                    
        except Exception as e:
            logger.error(f"进程监控错误 {pid}: {str(e)}")
    
    def get_monitoring_data(self, pid: int) -> Optional[Dict[str, Any]]:
        """获取进程监控数据"""
        with self._lock:
            if pid in self.monitoring_data and self.monitoring_data[pid]:
                data = self.monitoring_data[pid]
                return {
                    'current': data[-1] if data else None,
                    'history': data,
                    'summary': self._calculate_summary(data)
                }
        return None
    
    def _calculate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算监控数据摘要"""
        if not data:
            return {}
        
        cpu_values = [d['cpu_percent'] for d in data]
        memory_values = [d['memory_usage'] for d in data]
        
        return {
            'avg_cpu': sum(cpu_values) / len(cpu_values),
            'max_cpu': max(cpu_values),
            'avg_memory': sum(memory_values) / len(memory_values),
            'max_memory': max(memory_values),
            'duration_seconds': len(data)  # 假设每秒一条数据
        }

class ProcessAnalyzer:
    """进程分析器"""
    
    def analyze_process_behavior(self, pid: int, duration: int = 60) -> Dict[str, Any]:
        """分析进程行为"""
        # 这里可以实现更复杂的进程行为分析
        # 例如：CPU使用模式、内存泄漏检测、I/O模式等
        
        return {
            'stability': 'stable',  # stable, unstable, critical
            'resource_usage_trend': 'increasing',  # increasing, decreasing, stable
            'potential_issues': [],
            'recommendations': []
        }

# 单例实例
_process_manager_instance = None

def get_process_manager() -> ProcessManager:
    """获取进程管理器单例"""
    global _process_manager_instance
    if _process_manager_instance is None:
        _process_manager_instance = ProcessManager()
    return _process_manager_instance

