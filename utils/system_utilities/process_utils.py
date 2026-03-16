"""
进程工具模块

提供进程管理和监控工具。
"""

import os
import sys
import psutil
import subprocess
import signal
import time
from typing import Dict, List, Optional, Union, Any
from multiprocessing import cpu_count
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


class ProcessManager:
    """进程管理器"""
    
    @staticmethod
    def get_current_process() -> psutil.Process:
        """获取当前进程
        
        Returns:
            当前进程对象
        """
        return psutil.Process()
    
    @staticmethod
    def get_process_by_id(pid: int) -> Optional[psutil.Process]:
        """根据PID获取进程
        
        Args:
            pid: 进程ID
            
        Returns:
            进程对象，如果进程不存在返回None
        """
        try:
            return psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    @staticmethod
    def get_all_processes() -> List[Dict[str, Any]]:
        """获取所有进程信息
        
        Returns:
            进程信息列表
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    @staticmethod
    def get_process_tree(pid: int = None) -> Dict[str, Any]:
        """获取进程树
        
        Args:
            pid: 根进程ID，默认为当前进程
            
        Returns:
            进程树信息
        """
        if pid is None:
            pid = os.getpid()
        
        try:
            proc = psutil.Process(pid)
            tree = {
                'pid': proc.pid,
                'name': proc.name(),
                'status': proc.status(),
                'cpu_percent': proc.cpu_percent(),
                'memory_percent': proc.memory_percent(),
                'create_time': proc.create_time(),
                'children': []
            }
            
            for child in proc.children(recursive=False):
                child_info = ProcessManager.get_process_tree(child.pid)
                tree['children'].append(child_info)
            
            return tree
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}
    
    @staticmethod
    def kill_process(pid: int, force: bool = False) -> bool:
        """终止进程
        
        Args:
            pid: 进程ID
            force: 是否强制终止
            
        Returns:
            是否成功终止
        """
        try:
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            
            # 等待进程结束
            proc.wait(timeout=5)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            return False
    
    @staticmethod
    def suspend_process(pid: int) -> bool:
        """暂停进程
        
        Args:
            pid: 进程ID
            
        Returns:
            是否成功暂停
        """
        try:
            proc = psutil.Process(pid)
            proc.suspend()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    @staticmethod
    def resume_process(pid: int) -> bool:
        """恢复进程
        
        Args:
            pid: 进程ID
            
        Returns:
            是否成功恢复
        """
        try:
            proc = psutil.Process(pid)
            proc.resume()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    @staticmethod
    def get_process_cpu_usage(pid: int) -> Optional[float]:
        """获取进程CPU使用率
        
        Args:
            pid: 进程ID
            
        Returns:
            CPU使用率百分比
        """
        try:
            proc = psutil.Process(pid)
            return proc.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    @staticmethod
    def get_process_memory_usage(pid: int) -> Optional[Dict[str, float]]:
        """获取进程内存使用情况
        
        Args:
            pid: 进程ID
            
        Returns:
            内存使用信息字典
        """
        try:
            proc = psutil.Process(pid)
            memory_info = proc.memory_info()
            return {
                'rss': memory_info.rss,  # 物理内存
                'vms': memory_info.vms,  # 虚拟内存
                'percent': proc.memory_percent(),  # 内存使用率
                'available': psutil.virtual_memory().available  # 系统可用内存
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    @staticmethod
    def get_process_io_usage(pid: int) -> Optional[Dict[str, int]]:
        """获取进程IO使用情况
        
        Args:
            pid: 进程ID
            
        Returns:
            IO使用信息字典
        """
        try:
            proc = psutil.Process(pid)
            io_info = proc.io_counters()
            return {
                'read_count': io_info.read_count,
                'write_count': io_info.write_count,
                'read_bytes': io_info.read_bytes,
                'write_bytes': io_info.write_bytes
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            return None
    
    @staticmethod
    def get_process_open_files(pid: int) -> List[Dict[str, str]]:
        """获取进程打开的文件
        
        Args:
            pid: 进程ID
            
        Returns:
            打开的文件列表
        """
        try:
            proc = psutil.Process(pid)
            files = []
            for file_info in proc.open_files():
                files.append({
                    'path': file_info.path,
                    'fd': file_info.fd
                })
            return files
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []
    
    @staticmethod
    def get_process_network_connections(pid: int) -> List[Dict[str, Any]]:
        """获取进程网络连接
        
        Args:
            pid: 进程ID
            
        Returns:
            网络连接列表
        """
        try:
            proc = psutil.Process(pid)
            connections = []
            for conn in proc.connections():
                connections.append({
                    'family': conn.family,
                    'type': conn.type,
                    'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                    'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                    'status': conn.status
                })
            return connections
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []


class SystemMonitor:
    """系统监控器"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """获取系统信息
        
        Returns:
            系统信息字典
        """
        return {
            'platform': sys.platform,
            'architecture': os.architecture(),
            'processor': os.processor(),
            'cpu_count': cpu_count(),
            'boot_time': psutil.boot_time(),
            'hostname': os.uname().nodename if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'Unknown')
        }
    
    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """获取CPU信息
        
        Returns:
            CPU信息字典
        """
        return {
            'count': cpu_count(),
            'count_logical': psutil.cpu_count(logical=True),
            'usage_per_cpu': psutil.cpu_percent(percpu=True, interval=1),
            'total_usage': psutil.cpu_percent(interval=1),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
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
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'free': memory.free,
            'percent': memory.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_free': swap.free,
            'swap_percent': swap.percent
        }
    
    @staticmethod
    def get_disk_info() -> List[Dict[str, Any]]:
        """获取磁盘信息
        
        Returns:
            磁盘信息列表
        """
        disk_info = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'file_system': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100
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
        network_io = psutil.net_io_counters()
        network_stats = psutil.net_if_stats()
        
        return {
            'bytes_sent': network_io.bytes_sent,
            'bytes_recv': network_io.bytes_recv,
            'packets_sent': network_io.packets_sent,
            'packets_recv': network_io.packets_recv,
            'interfaces': {
                name: {
                    'is_up': stats.isup,
                    'mtu': stats.mtu,
                    'speed': stats.speed
                }
                for name, stats in network_stats.items()
            }
        }
    
    @staticmethod
    def get_process_list(sort_by: str = 'cpu_percent', limit: int = 10) -> List[Dict[str, Any]]:
        """获取进程列表
        
        Args:
            sort_by: 排序字段 ('cpu_percent', 'memory_percent', 'name', 'pid')
            limit: 返回数量限制
            
        Returns:
            进程列表
        """
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 排序
        if sort_by in processes[0] if processes else False:
            processes.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        
        return processes[:limit]


class ProcessExecutor:
    """进程执行器"""
    
    def __init__(self, max_workers: int = None):
        """初始化进程执行器
        
        Args:
            max_workers: 最大工作进程数
        """
        self.max_workers = max_workers or cpu_count()
        self.executor = None
    
    def __enter__(self):
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.executor:
            self.executor.shutdown(wait=True)
    
    def submit(self, func, *args, **kwargs):
        """提交任务
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        if not self.executor:
            raise RuntimeError("进程执行器未启动")
        return self.executor.submit(func, *args, **kwargs)
    
    def map(self, func, iterable):
        """批量执行任务
        
        Args:
            func: 要执行的函数
            iterable: 可迭代对象
            
        Returns:
            结果迭代器
        """
        if not self.executor:
            raise RuntimeError("进程执行器未启动")
        return self.executor.map(func, iterable)


class ThreadMonitor:
    """线程监控器"""
    
    @staticmethod
    def get_current_threads() -> List[Dict[str, Any]]:
        """获取当前进程的所有线程
        
        Returns:
            线程信息列表
        """
        current_proc = psutil.Process()
        threads = []
        
        for thread in current_proc.threads():
            threads.append({
                'id': thread.id,
                'user_time': thread.user_time,
                'system_time': thread.system_time
            })
        
        return threads
    
    @staticmethod
    def monitor_thread_usage(interval: float = 1.0, duration: float = 10.0) -> Dict[str, Any]:
        """监控线程使用情况
        
        Args:
            interval: 监控间隔（秒）
            duration: 监控持续时间（秒）
            
        Returns:
            监控结果
        """
        start_time = time.time()
        thread_counts = []
        
        while time.time() - start_time < duration:
            thread_count = threading.active_count()
            thread_counts.append({
                'timestamp': time.time(),
                'thread_count': thread_count
            })
            time.sleep(interval)
        
        return {
            'interval': interval,
            'duration': duration,
            'samples': len(thread_counts),
            'thread_counts': thread_counts,
            'min_threads': min(tc['thread_count'] for tc in thread_counts),
            'max_threads': max(tc['thread_count'] for tc in thread_counts),
            'avg_threads': sum(tc['thread_count'] for tc in thread_counts) / len(thread_counts)
        }


def start_process(command: Union[str, List[str]], 
                 cwd: str = None, 
                 env: Dict[str, str] = None,
                 shell: bool = True) -> subprocess.Popen:
    """启动进程
    
    Args:
        command: 要执行的命令
        cwd: 工作目录
        env: 环境变量
        shell: 是否使用shell
        
    Returns:
        进程对象
    """
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )


def run_command(command: Union[str, List[str]], 
               timeout: int = 30,
               cwd: str = None,
               env: Dict[str, str] = None) -> Dict[str, Any]:
    """运行命令并等待完成
    
    Args:
        command: 要执行的命令
        timeout: 超时时间（秒）
        cwd: 工作目录
        env: 环境变量
        
    Returns:
        命令执行结果
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Command timed out',
            'success': False
        }


def kill_process_tree(pid: int, timeout: int = 5) -> bool:
    """终止进程树
    
    Args:
        pid: 根进程ID
        timeout: 超时时间（秒）
        
    Returns:
        是否成功终止
    """
    try:
        proc = psutil.Process(pid)
        
        # 先尝试优雅终止
        proc.terminate()
        
        # 等待子进程
        children = proc.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 等待进程结束
        gone, alive = psutil.wait_procs([proc], timeout=timeout)
        
        # 如果还有进程存活，强制杀死
        if proc in alive:
            proc.kill()
            for child in children:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_process_children(pid: int) -> List[int]:
    """获取子进程ID列表
    
    Args:
        pid: 父进程ID
        
    Returns:
        子进程ID列表
    """
    try:
        proc = psutil.Process(pid)
        return [child.pid for child in proc.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []