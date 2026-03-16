"""
内存工具模块

提供内存管理和监控工具。
"""

import psutil
import gc
import sys
import tracemalloc
from typing import Dict, List, Optional, Any, Tuple
import threading
import time
from collections import defaultdict
import weakref


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self):
        """初始化内存监控器"""
        self.start_time = time.time()
        self.peak_memory = 0
        self.current_memory = 0
        self.monitoring = False
        self.monitor_thread = None
        self.memory_history = []
    
    def start_monitoring(self, interval: float = 1.0):
        """开始内存监控
        
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
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            memory_info = self.get_memory_usage()
            self.current_memory = memory_info['used']
            self.peak_memory = max(self.peak_memory, self.current_memory)
            
            self.memory_history.append({
                'timestamp': time.time(),
                'used': self.current_memory,
                'available': memory_info['available'],
                'percent': memory_info['percent']
            })
            
            time.sleep(interval)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况
        
        Returns:
            内存使用信息字典
        """
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'free': memory.free,
            'percent': memory.percent,
            'cached': getattr(memory, 'cached', 0),
            'buffers': getattr(memory, 'buffers', 0),
            'shared': getattr(memory, 'shared', 0)
        }
    
    def get_swap_usage(self) -> Dict[str, Any]:
        """获取交换分区使用情况
        
        Returns:
            交换分区使用信息字典
        """
        swap = psutil.swap_memory()
        return {
            'total': swap.total,
            'used': swap.used,
            'free': swap.free,
            'percent': swap.percent,
            'sin': swap.sin,  # 页交换入
            'sout': swap.sout  # 页交换出
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """获取内存使用摘要
        
        Returns:
            内存摘要信息
        """
        memory_info = self.get_memory_usage()
        swap_info = self.get_swap_usage()
        
        return {
            'memory': memory_info,
            'swap': swap_info,
            'peak_memory': self.peak_memory,
            'monitoring_duration': time.time() - self.start_time,
            'samples_count': len(self.memory_history)
        }
    
    def get_memory_history(self) -> List[Dict[str, Any]]:
        """获取内存使用历史
        
        Returns:
            内存使用历史列表
        """
        return self.memory_history.copy()
    
    def reset_peak_memory(self):
        """重置峰值内存记录"""
        self.peak_memory = 0


class MemoryProfiler:
    """内存分析器"""
    
    def __init__(self):
        """初始化内存分析器"""
        self.snapshots = []
        self.traced_objects = weakref.WeakSet()
    
    def start_tracing(self):
        """开始内存跟踪"""
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)  # 跟踪25层调用栈
    
    def stop_tracing(self):
        """停止内存跟踪"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
    
    def take_snapshot(self) -> Any:
        """拍摄内存快照
        
        Returns:
            内存快照对象
        """
        if not tracemalloc.is_tracing():
            self.start_tracing()
        
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append({
            'snapshot': snapshot,
            'timestamp': time.time(),
            'total_size': sum(stat.size for stat in snapshot.statistics('lineno'))
        })
        return snapshot
    
    def get_memory_stats(self, snapshot=None) -> Dict[str, Any]:
        """获取内存统计信息
        
        Args:
            snapshot: 内存快照，如果为None则使用最新的快照
            
        Returns:
            内存统计信息
        """
        if snapshot is None:
            if not self.snapshots:
                return {}
            snapshot = self.snapshots[-1]['snapshot']
        
        stats = snapshot.statistics('lineno')
        total_size = sum(stat.size for stat in stats)
        
        return {
            'total_size': total_size,
            'total_count': len(stats),
            'top_10': [
                {
                    'filename': stat.traceback.format()[-1],
                    'size': stat.size,
                    'count': stat.count,
                    'size_per_item': stat.size / stat.count if stat.count > 0 else 0
                }
                for stat in stats[:10]
            ]
        }
    
    def compare_snapshots(self, snapshot1=None, snapshot2=None) -> Dict[str, Any]:
        """比较两个内存快照
        
        Args:
            snapshot1: 第一个快照
            snapshot2: 第二个快照
            
        Returns:
            快照比较结果
        """
        if snapshot1 is None or snapshot2 is None:
            if len(self.snapshots) < 2:
                return {}
            snapshot1 = self.snapshots[-2]['snapshot']
            snapshot2 = self.snapshots[-1]['snapshot']
        
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        return {
            'top_10_increased': [
                {
                    'filename': stat.traceback.format()[-1],
                    'size_diff': stat.size_diff,
                    'count_diff': stat.count_diff
                }
                for stat in top_stats[:10] if stat.size_diff > 0
            ],
            'top_10_decreased': [
                {
                    'filename': stat.traceback.format()[-1],
                    'size_diff': stat.size_diff,
                    'count_diff': stat.count_diff
                }
                for stat in top_stats[:10] if stat.size_diff < 0
            ]
        }
    
    def get_object_size(self, obj: Any) -> int:
        """获取对象大小
        
        Args:
            obj: 要测量的对象
            
        Returns:
            对象大小（字节）
        """
        return sys.getsizeof(obj)
    
    def get_detailed_size(self, obj: Any) -> Dict[str, int]:
        """获取对象详细大小信息
        
        Args:
            obj: 要测量的对象
            
        Returns:
            详细大小信息字典
        """
        size = sys.getsizeof(obj)
        recursive_size = 0
        
        try:
            if hasattr(obj, '__dict__'):
                for value in obj.__dict__.values():
                    recursive_size += self.get_detailed_size(value)
        except:
            pass
        
        try:
            if hasattr(obj, '__slots__'):
                for slot in obj.__slots__:
                    try:
                        value = getattr(obj, slot)
                        recursive_size += self.get_detailed_size(value)
                    except:
                        pass
        except:
            pass
        
        return {
            'direct_size': size,
            'recursive_size': recursive_size,
            'total_size': size + recursive_size
        }


class MemoryManager:
    """内存管理器"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """获取当前进程的内存使用情况
        
        Returns:
            内存使用信息字典
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        return {
            'rss': memory_info.rss,  # 物理内存
            'vms': memory_info.vms,  # 虚拟内存
            'percent': memory_percent,  # 内存使用百分比
            'available_system_memory': psutil.virtual_memory().available
        }
    
    @staticmethod
    def get_memory_maps() -> List[Dict[str, Any]]:
        """获取进程内存映射
        
        Returns:
            内存映射列表
        """
        process = psutil.Process()
        memory_maps = []
        
        for mmap in process.memory_maps():
            memory_maps.append({
                'path': mmap.path,
                'rss': mmap.rss,
                'size': mmap.size,
                'pss': getattr(mmap, 'pss', 0),
                'private_clean': getattr(mmap, 'private_clean', 0),
                'private_dirty': getattr(mmap, 'private_dirty', 0)
            })
        
        return memory_maps
    
    @staticmethod
    def force_garbage_collection():
        """强制垃圾回收"""
        collected = gc.collect()
        return collected
    
    @staticmethod
    def get_garbage_collection_stats() -> Dict[str, Any]:
        """获取垃圾回收统计信息
        
        Returns:
            垃圾回收统计信息
        """
        stats = gc.get_stats()
        garbage = gc.garbage
        
        return {
            'generation_stats': stats,
            'garbage_count': len(garbage),
            'garbage_objects': garbage,
            'gc_thresholds': gc.get_threshold()
        }
    
    @staticmethod
    def set_gc_thresholds(threshold0: int, threshold1: int = None, threshold2: int = None):
        """设置垃圾回收阈值
        
        Args:
            threshold0: 第0代阈值
            threshold1: 第1代阈值
            threshold2: 第2代阈值
        """
        if threshold1 is None:
            threshold1 = threshold0
        if threshold2 is None:
            threshold2 = threshold1
        
        gc.set_threshold(threshold0, threshold1, threshold2)
    
    @staticmethod
    def enable_gc():
        """启用垃圾回收"""
        gc.enable()
    
    @staticmethod
    def disable_gc():
        """禁用垃圾回收"""
        gc.disable()
    
    @staticmethod
    def is_gc_enabled() -> bool:
        """检查垃圾回收是否启用
        
        Returns:
            是否启用
        """
        return gc.isenabled()


class ObjectTracker:
    """对象跟踪器"""
    
    def __init__(self):
        """初始化对象跟踪器"""
        self.tracked_objects = {}
        self.object_counts = defaultdict(int)
        self.lock = threading.Lock()
    
    def track_object(self, obj: Any, name: str = None):
        """跟踪对象
        
        Args:
            obj: 要跟踪的对象
            name: 对象名称
        """
        with self.lock:
            obj_id = id(obj)
            if name is None:
                name = f"Object_{obj_id}"
            
            self.tracked_objects[obj_id] = {
                'object': obj,
                'name': name,
                'created_at': time.time(),
                'type': type(obj).__name__
            }
            self.object_counts[type(obj).__name__] += 1
    
    def untrack_object(self, obj: Any):
        """取消跟踪对象
        
        Args:
            obj: 要取消跟踪的对象
        """
        with self.lock:
            obj_id = id(obj)
            if obj_id in self.tracked_objects:
                obj_type = self.tracked_objects[obj_id]['type']
                del self.tracked_objects[obj_id]
                self.object_counts[obj_type] -= 1
                if self.object_counts[obj_type] <= 0:
                    del self.object_counts[obj_type]
    
    def get_tracked_objects(self) -> Dict[str, Any]:
        """获取跟踪的对象列表
        
        Returns:
            跟踪对象信息字典
        """
        with self.lock:
            return {
                'objects': {
                    obj_id: {
                        'name': info['name'],
                        'type': info['type'],
                        'created_at': info['created_at'],
                        'age': time.time() - info['created_at']
                    }
                    for obj_id, info in self.tracked_objects.items()
                },
                'object_counts': dict(self.object_counts),
                'total_tracked': len(self.tracked_objects)
            }
    
    def clear_tracked_objects(self):
        """清除所有跟踪的对象"""
        with self.lock:
            self.tracked_objects.clear()
            self.object_counts.clear()


class MemoryLeakDetector:
    """内存泄漏检测器"""
    
    def __init__(self):
        """初始化内存泄漏检测器"""
        self.baseline_snapshot = None
        self.profiler = MemoryProfiler()
        self.monitor = MemoryMonitor()
    
    def start_detection(self):
        """开始内存泄漏检测"""
        self.profiler.start_tracing()
        self.baseline_snapshot = self.profiler.take_snapshot()
        self.monitor.start_monitoring()
    
    def stop_detection(self):
        """停止内存泄漏检测"""
        self.monitor.stop_monitoring()
        self.profiler.stop_tracing()
    
    def detect_leaks(self) -> Dict[str, Any]:
        """检测内存泄漏
        
        Returns:
            内存泄漏检测结果
        """
        current_snapshot = self.profiler.take_snapshot()
        comparison = self.profiler.compare_snapshots(
            self.baseline_snapshot, 
            current_snapshot
        )
        
        memory_summary = self.monitor.get_memory_summary()
        
        return {
            'memory_comparison': comparison,
            'memory_summary': memory_summary,
            'potential_leaks': self._identify_potential_leaks(comparison),
            'recommendations': self._generate_recommendations(comparison, memory_summary)
        }
    
    def _identify_potential_leaks(self, comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别潜在的内存泄漏
        
        Args:
            comparison: 快照比较结果
            
        Returns:
            潜在泄漏列表
        """
        potential_leaks = []
        
        for item in comparison.get('top_10_increased', []):
            if item['size_diff'] > 1024 * 1024:  # 超过1MB的增长
                potential_leaks.append({
                    'location': item['filename'],
                    'size_increase': item['size_diff'],
                    'count_increase': item['count_diff'],
                    'severity': 'high' if item['size_diff'] > 10 * 1024 * 1024 else 'medium'
                })
        
        return potential_leaks
    
    def _generate_recommendations(self, comparison: Dict[str, Any], 
                                memory_summary: Dict[str, Any]) -> List[str]:
        """生成优化建议
        
        Args:
            comparison: 快照比较结果
            memory_summary: 内存摘要
            
        Returns:
            优化建议列表
        """
        recommendations = []
        
        # 检查内存使用率
        memory_percent = memory_summary.get('memory', {}).get('percent', 0)
        if memory_percent > 80:
            recommendations.append("系统内存使用率过高，建议优化内存使用或增加内存")
        
        # 检查交换分区使用
        swap_percent = memory_summary.get('swap', {}).get('percent', 0)
        if swap_percent > 50:
            recommendations.append("交换分区使用率过高，可能存在内存不足问题")
        
        # 检查内存增长
        increased_count = len(comparison.get('top_10_increased', []))
        if increased_count > 5:
            recommendations.append("检测到多个内存增长点，建议检查代码中的内存泄漏")
        
        # 垃圾回收建议
        gc_stats = MemoryManager.get_garbage_collection_stats()
        if gc_stats['garbage_count'] > 0:
            recommendations.append(f"发现 {gc_stats['garbage_count']} 个垃圾对象，建议检查循环引用")
        
        return recommendations


def format_bytes(bytes_value: int) -> str:
    """格式化字节数
    
    Args:
        bytes_value: 字节数
        
    Returns:
        格式化的字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_memory_pressure() -> Dict[str, Any]:
    """获取内存压力信息
    
    Returns:
        内存压力信息字典
    """
    memory = psutil.virtual_memory()
    
    # 计算内存压力等级
    if memory.percent < 60:
        pressure_level = "low"
    elif memory.percent < 80:
        pressure_level = "medium"
    else:
        pressure_level = "high"
    
    return {
        'pressure_level': pressure_level,
        'memory_percent': memory.percent,
        'available_gb': memory.available / (1024**3),
        'total_gb': memory.total / (1024**3),
        'used_gb': memory.used / (1024**3)
    }


def optimize_memory_usage():
    """优化内存使用
    
    Returns:
        优化结果字典
    """
    results = {
        'garbage_collected': 0,
        'freed_memory': 0,
        'actions_taken': []
    }
    
    # 强制垃圾回收
    collected = MemoryManager.force_garbage_collection()
    results['garbage_collected'] = collected
    results['actions_taken'].append(f"垃圾回收清理了 {collected} 个对象")
    
    # 检查内存压力
    pressure = get_memory_pressure()
    if pressure['pressure_level'] == 'high':
        results['actions_taken'].append("检测到高内存压力，建议检查内存泄漏")
    
    return results