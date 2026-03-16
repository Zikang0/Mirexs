"""
CPU工具模块

提供CPU管理、监控和优化工具
"""

import os
import time
import threading
import multiprocessing
from typing import Dict, List, Any, Optional, Tuple
import logging
import psutil
import platform
from collections import deque

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CPUMonitor:
    """CPU监控器"""
    
    def __init__(self):
        """初始化CPU监控器"""
        self.monitoring = False
        self.monitor_thread = None
        self.history = deque(maxlen=3600)  # 保存1小时的数据（每秒一个样本）
        self.core_history = {}
        self.process_history = deque(maxlen=100)
        self.temp_history = deque(maxlen=3600)
        self.lock = threading.Lock()
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """获取CPU基本信息"""
        info = {
            'physical_cores': psutil.cpu_count(logical=False),
            'logical_cores': psutil.cpu_count(logical=True),
            'min_frequency': None,
            'max_frequency': None,
            'current_frequency': None,
            'architecture': platform.machine(),
            'processor': platform.processor()
        }
        
        # 获取CPU频率
        freq = psutil.cpu_freq()
        if freq:
            info['min_frequency'] = freq.min
            info['max_frequency'] = freq.max
            info['current_frequency'] = freq.current
        
        return info
    
    def get_cpu_usage(self, per_core: bool = True) -> Dict[str, Any]:
        """获取CPU使用率"""
        result = {
            'timestamp': time.time(),
            'overall': psutil.cpu_percent(interval=0.1)
        }
        
        if per_core:
            result['per_core'] = psutil.cpu_percent(interval=0.1, percpu=True)
        
        return result
    
    def get_cpu_stats(self) -> Dict[str, Any]:
        """获取CPU统计信息"""
        stats = psutil.cpu_stats()
        return {
            'ctx_switches': stats.ctx_switches,
            'interrupts': stats.interrupts,
            'soft_interrupts': stats.soft_interrupts,
            'syscalls': stats.syscalls
        }
    
    def get_cpu_times(self) -> Dict[str, float]:
        """获取CPU时间统计"""
        times = psutil.cpu_times()
        return {
            'user': times.user,
            'system': times.system,
            'idle': times.idle,
            'iowait': getattr(times, 'iowait', 0),
            'irq': getattr(times, 'irq', 0),
            'softirq': getattr(times, 'softirq', 0),
            'steal': getattr(times, 'steal', 0),
            'guest': getattr(times, 'guest', 0),
            'guest_nice': getattr(times, 'guest_nice', 0)
        }
    
    def get_cpu_times_percent(self, interval: float = 1.0) -> Dict[str, float]:
        """获取CPU时间百分比"""
        times = psutil.cpu_times_percent(interval=interval)
        return {
            'user': times.user,
            'system': times.system,
            'idle': times.idle,
            'iowait': getattr(times, 'iowait', 0),
            'irq': getattr(times, 'irq', 0),
            'softirq': getattr(times, 'softirq', 0),
            'steal': getattr(times, 'steal', 0),
            'guest': getattr(times, 'guest', 0),
            'guest_nice': getattr(times, 'guest_nice', 0)
        }
    
    def get_cpu_temperature(self) -> Optional[float]:
        """获取CPU温度"""
        try:
            if platform.system() == 'Linux':
                # 尝试读取温度文件
                thermal_zones = ['/sys/class/thermal/thermal_zone0/temp',
                                 '/sys/class/thermal/thermal_zone1/temp']
                for zone in thermal_zones:
                    if os.path.exists(zone):
                        with open(zone, 'r') as f:
                            temp = float(f.read().strip()) / 1000.0
                            return temp
            elif platform.system() == 'Windows':
                # Windows下尝试使用wmi
                import wmi
                w = wmi.WMI(namespace="root\\wmi")
                temperature_info = w.MSAcpi_ThermalZoneTemperature()
                if temperature_info:
                    return float(temperature_info[0].CurrentTemperature) / 10.0 - 273.15
            return None
        except Exception as e:
            logger.debug(f"获取CPU温度失败: {e}")
            return None
    
    def get_load_average(self) -> Dict[str, float]:
        """获取系统负载"""
        if hasattr(os, 'getloadavg'):
            load_avg = os.getloadavg()
            return {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            }
        return {}
    
    def get_top_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取CPU使用率最高的进程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                cpu_percent = proc.info['cpu_percent']
                if cpu_percent > 0:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': cpu_percent,
                        'memory_percent': proc.info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
    
    def start_monitoring(self, interval: float = 1.0):
        """开始监控CPU使用情况"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"CPU监控已启动，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("CPU监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                # 获取整体CPU使用率
                usage = self.get_cpu_usage(per_core=True)
                self.history.append(usage)
                
                # 获取每个核心的使用率
                for i, core_usage in enumerate(usage.get('per_core', [])):
                    if i not in self.core_history:
                        self.core_history[i] = deque(maxlen=3600)
                    self.core_history[i].append(core_usage)
                
                # 获取CPU温度
                temp = self.get_cpu_temperature()
                if temp is not None:
                    self.temp_history.append(temp)
                
                # 获取CPU使用率最高的进程
                top_procs = self.get_top_processes(5)
                self.process_history.append({
                    'timestamp': time.time(),
                    'processes': top_procs
                })
                
            except Exception as e:
                logger.error(f"CPU监控错误: {e}")
            
            time.sleep(interval)
    
    def get_statistics(self, minutes: int = 5) -> Dict[str, Any]:
        """获取CPU统计信息"""
        samples_needed = minutes * 60  # 假设每秒一个样本
        recent = list(self.history)[-samples_needed:]
        
        if not recent:
            return {}
        
        cpu_values = [r['overall'] for r in recent]
        
        return {
            'duration_minutes': minutes,
            'samples': len(recent),
            'average': sum(cpu_values) / len(cpu_values),
            'min': min(cpu_values),
            'max': max(cpu_values),
            'current': cpu_values[-1] if cpu_values else 0,
            'per_core_average': self._get_core_averages(recent)
        }
    
    def _get_core_averages(self, recent_data: List[Dict]) -> List[float]:
        """计算每个核心的平均使用率"""
        if not recent_data:
            return []
        
        core_count = len(recent_data[0].get('per_core', []))
        core_sums = [0] * core_count
        
        for data in recent_data:
            per_core = data.get('per_core', [])
            for i in range(min(len(per_core), core_count)):
                core_sums[i] += per_core[i]
        
        return [s / len(recent_data) for s in core_sums]
    
    def get_history(self) -> Dict[str, Any]:
        """获取历史数据"""
        return {
            'overall': [h['overall'] for h in self.history],
            'per_core': {
                core: list(values)
                for core, values in self.core_history.items()
            },
            'temperatures': list(self.temp_history),
            'top_processes': list(self.process_history)
        }


class CPUOptimizer:
    """CPU优化器"""
    
    @staticmethod
    def set_cpu_affinity(pid: int, cpus: List[int]) -> bool:
        """设置CPU亲和性"""
        try:
            proc = psutil.Process(pid)
            proc.cpu_affinity(cpus)
            return True
        except Exception as e:
            logger.error(f"设置CPU亲和性失败: {e}")
            return False
    
    @staticmethod
    def set_process_priority(pid: int, priority: str) -> bool:
        """设置进程优先级"""
        try:
            proc = psutil.Process(pid)
            
            priority_map = {
                'high': psutil.HIGH_PRIORITY_CLASS,
                'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                'normal': psutil.NORMAL_PRIORITY_CLASS,
                'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS,
                'idle': psutil.IDLE_PRIORITY_CLASS
            }
            
            if priority in priority_map:
                proc.nice(priority_map[priority])
                return True
            return False
        except Exception as e:
            logger.error(f"设置进程优先级失败: {e}")
            return False
    
    @staticmethod
    def optimize_for_workload(workload_type: str = 'balanced') -> Dict[str, Any]:
        """根据工作负载类型优化CPU"""
        result = {
            'workload_type': workload_type,
            'actions_taken': [],
            'recommendations': []
        }
        
        cpu_count = multiprocessing.cpu_count()
        
        if workload_type == 'cpu_intensive':
            # CPU密集型任务优化
            result['recommendations'].append("使用所有CPU核心")
            result['recommendations'].append("设置高进程优先级")
            result['recommendations'].append("禁用CPU节能模式")
            
        elif workload_type == 'io_intensive':
            # IO密集型任务优化
            result['recommendations'].append("使用异步IO")
            result['recommendations'].append("设置IO优先级")
            result['recommendations'].append("增加IO缓冲区大小")
            
        elif workload_type == 'balanced':
            # 平衡型任务
            result['recommendations'].append("使用默认设置")
            result['recommendations'].append("监控CPU使用率")
            result['recommendations'].append("根据负载动态调整")
        
        return result


class CPUGovernor:
    """CPU调频策略管理器"""
    
    @staticmethod
    def get_available_governors() -> List[str]:
        """获取可用的CPU调频策略"""
        try:
            if platform.system() == 'Linux':
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors', 'r') as f:
                    return f.read().strip().split()
            return []
        except Exception as e:
            logger.error(f"获取CPU调频策略失败: {e}")
            return []
    
    @staticmethod
    def set_governor(governor: str) -> bool:
        """设置CPU调频策略"""
        try:
            if platform.system() == 'Linux':
                cpu_count = multiprocessing.cpu_count()
                for i in range(cpu_count):
                    path = f'/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor'
                    if os.path.exists(path):
                        with open(path, 'w') as f:
                            f.write(governor)
                return True
            return False
        except Exception as e:
            logger.error(f"设置CPU调频策略失败: {e}")
            return False
    
    @staticmethod
    def get_current_governor() -> Optional[str]:
        """获取当前CPU调频策略"""
        try:
            if platform.system() == 'Linux':
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            logger.error(f"获取当前CPU调频策略失败: {e}")
            return None


def cpu_stress_test(duration: int = 60, workers: int = None) -> Dict[str, Any]:
    """CPU压力测试"""
    import concurrent.futures
    
    if workers is None:
        workers = multiprocessing.cpu_count()
    
    def cpu_intensive_task():
        end_time = time.time() + duration
        while time.time() < end_time:
            # 执行密集计算
            for i in range(1000000):
                i * i
    
    results = {
        'duration': duration,
        'workers': workers,
        'start_time': time.time(),
        'end_time': None,
        'cpu_usage': []
    }
    
    monitor = CPUMonitor()
    monitor.start_monitoring(interval=0.5)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(cpu_intensive_task) for _ in range(workers)]
        concurrent.futures.wait(futures)
    
    monitor.stop_monitoring()
    results['end_time'] = time.time()
    
    # 收集统计信息
    history = monitor.get_history()
    if history['overall']:
        results['cpu_usage'] = history['overall']
        results['average_usage'] = sum(history['overall']) / len(history['overall'])
        results['peak_usage'] = max(history['overall'])
    
    return results


def calculate_cpu_score() -> Dict[str, Any]:
    """计算CPU性能分数"""
    import timeit
    
    # 测试整数运算
    def integer_benchmark():
        result = 0
        for i in range(1000000):
            result += i * i
        return result
    
    # 测试浮点运算
    def float_benchmark():
        result = 0.0
        for i in range(1000000):
            result += i * 3.14159
        return result
    
    # 测试内存访问
    def memory_benchmark():
        array = list(range(100000))
        result = 0
        for i in array:
            result += array[i]
        return result
    
    integer_time = timeit.timeit(integer_benchmark, number=10)
    float_time = timeit.timeit(float_benchmark, number=10)
    memory_time = timeit.timeit(memory_benchmark, number=10)
    
    # 计算分数（分数越高越好）
    base_score = 1000
    integer_score = base_score / integer_time
    float_score = base_score / float_time
    memory_score = base_score / memory_time
    
    return {
        'integer_score': integer_score,
        'float_score': float_score,
        'memory_score': memory_score,
        'total_score': (integer_score + float_score + memory_score) / 3,
        'test_times': {
            'integer': integer_time,
            'float': float_time,
            'memory': memory_time
        }
    }


def set_process_priority(pid: int, priority: str) -> bool:
    """设置进程优先级（便捷函数）"""
    optimizer = CPUOptimizer()
    return optimizer.set_process_priority(pid, priority)


def get_cpu_affinity(pid: int) -> Optional[List[int]]:
    """获取CPU亲和性"""
    try:
        proc = psutil.Process(pid)
        return proc.cpu_affinity()
    except Exception:
        return None