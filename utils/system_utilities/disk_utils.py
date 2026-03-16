"""
磁盘工具模块

提供磁盘管理、监控和IO优化工具
"""

import os
import time
import threading
import shutil
from typing import Dict, List, Any, Optional, Tuple, Union
import logging
import psutil
import platform
from collections import deque
import fnmatch

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiskMonitor:
    """磁盘监控器"""
    
    def __init__(self):
        """初始化磁盘监控器"""
        self.monitoring = False
        self.monitor_thread = None
        self.io_history = deque(maxlen=3600)
        self.usage_history = deque(maxlen=3600)
        self.lock = threading.Lock()
    
    def get_disk_partitions(self) -> List[Dict[str, Any]]:
        """获取磁盘分区信息"""
        partitions = []
        
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    'device': part.device,
                    'mountpoint': part.mountpoint,
                    'fstype': part.fstype,
                    'opts': part.opts.split(','),
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent,
                    'total_gb': usage.total / (1024**3),
                    'used_gb': usage.used / (1024**3),
                    'free_gb': usage.free / (1024**3)
                })
            except PermissionError:
                continue
        
        return partitions
    
    def get_disk_usage(self, path: str = '/') -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            usage = psutil.disk_usage(path)
            return {
                'path': path,
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent,
                'total_gb': usage.total / (1024**3),
                'used_gb': usage.used / (1024**3),
                'free_gb': usage.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"获取磁盘使用情况失败: {e}")
            return {}
    
    def get_disk_io_counters(self, per_disk: bool = True) -> Dict[str, Any]:
        """获取磁盘IO统计"""
        counters = psutil.disk_io_counters(perdisk=per_disk)
        
        if per_disk:
            result = {}
            for disk, io in counters.items():
                result[disk] = {
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
            return result
        else:
            return {
                'read_count': counters.read_count,
                'write_count': counters.write_count,
                'read_bytes': counters.read_bytes,
                'write_bytes': counters.write_bytes,
                'read_time': counters.read_time,
                'write_time': counters.write_time
            }
    
    def calculate_io_speed(self, interval: float = 1.0) -> Dict[str, Any]:
        """计算磁盘IO速度"""
        before = self.get_disk_io_counters(per_disk=True)
        time.sleep(interval)
        after = self.get_disk_io_counters(per_disk=True)
        
        speeds = {}
        for disk in before:
            if disk in after:
                read_speed = (after[disk]['read_bytes'] - before[disk]['read_bytes']) / interval
                write_speed = (after[disk]['write_bytes'] - before[disk]['write_bytes']) / interval
                iops_read = (after[disk]['read_count'] - before[disk]['read_count']) / interval
                iops_write = (after[disk]['write_count'] - before[disk]['write_count']) / interval
                
                speeds[disk] = {
                    'read_speed': read_speed,
                    'write_speed': write_speed,
                    'read_speed_mb': read_speed / (1024*1024),
                    'write_speed_mb': write_speed / (1024*1024),
                    'iops_read': iops_read,
                    'iops_write': iops_write,
                    'total_iops': iops_read + iops_write
                }
        
        return speeds
    
    def get_inode_usage(self, path: str = '/') -> Optional[Dict[str, Any]]:
        """获取inode使用情况（仅Linux）"""
        try:
            if platform.system() != 'Linux':
                return None
            
            stat = os.statvfs(path)
            return {
                'total_inodes': stat.f_files,
                'free_inodes': stat.f_ffree,
                'used_inodes': stat.f_files - stat.f_ffree,
                'percent': ((stat.f_files - stat.f_ffree) / stat.f_files) * 100 if stat.f_files > 0 else 0
            }
        except Exception as e:
            logger.error(f"获取inode使用情况失败: {e}")
            return None
    
    def start_monitoring(self, interval: float = 5.0):
        """开始磁盘监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"磁盘监控已启动，间隔: {interval}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("磁盘监控已停止")
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        last_io = self.get_disk_io_counters(per_disk=True)
        
        while self.monitoring:
            try:
                time.sleep(interval)
                current_io = self.get_disk_io_counters(per_disk=True)
                
                # 计算IO速度
                speeds = {}
                for disk in last_io:
                    if disk in current_io:
                        read_speed = (current_io[disk]['read_bytes'] - last_io[disk]['read_bytes']) / interval
                        write_speed = (current_io[disk]['write_bytes'] - last_io[disk]['write_bytes']) / interval
                        speeds[disk] = {
                            'read_speed': read_speed,
                            'write_speed': write_speed,
                            'timestamp': time.time()
                        }
                
                # 获取磁盘使用情况
                usage = {}
                for part in self.get_disk_partitions():
                    usage[part['mountpoint']] = {
                        'percent': part['percent'],
                        'used': part['used'],
                        'free': part['free']
                    }
                
                self.io_history.append({
                    'timestamp': time.time(),
                    'speeds': speeds
                })
                
                self.usage_history.append({
                    'timestamp': time.time(),
                    'usage': usage
                })
                
                last_io = current_io
                
            except Exception as e:
                logger.error(f"磁盘监控错误: {e}")
    
    def get_statistics(self, minutes: int = 5) -> Dict[str, Any]:
        """获取磁盘统计信息"""
        samples_needed = int(minutes * 60 / 5)  # 假设5秒一个样本
        recent_io = list(self.io_history)[-samples_needed:]
        
        if not recent_io:
            return {}
        
        # 计算平均IO速度
        avg_speeds = {}
        for sample in recent_io:
            for disk, speed in sample['speeds'].items():
                if disk not in avg_speeds:
                    avg_speeds[disk] = {'read_speed': [], 'write_speed': []}
                avg_speeds[disk]['read_speed'].append(speed['read_speed'])
                avg_speeds[disk]['write_speed'].append(speed['write_speed'])
        
        for disk in avg_speeds:
            avg_speeds[disk] = {
                'avg_read_speed': sum(avg_speeds[disk]['read_speed']) / len(avg_speeds[disk]['read_speed']),
                'avg_write_speed': sum(avg_speeds[disk]['write_speed']) / len(avg_speeds[disk]['write_speed']),
                'avg_read_speed_mb': sum(avg_speeds[disk]['read_speed']) / len(avg_speeds[disk]['read_speed']) / (1024*1024),
                'avg_write_speed_mb': sum(avg_speeds[disk]['write_speed']) / len(avg_speeds[disk]['write_speed']) / (1024*1024)
            }
        
        # 获取当前使用情况
        current_usage = self.usage_history[-1]['usage'] if self.usage_history else {}
        
        return {
            'duration_minutes': minutes,
            'samples': len(recent_io),
            'average_speeds': avg_speeds,
            'current_usage': current_usage
        }


class DiskCleaner:
    """磁盘清理工具"""
    
    def __init__(self):
        self.cleaned_files = 0
        self.freed_space = 0
    
    def find_large_files(self, path: str, size_threshold_mb: int = 100) -> List[Dict[str, Any]]:
        """查找大文件"""
        large_files = []
        
        for root, dirs, files in os.walk(path):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    if size > size_threshold_mb * 1024 * 1024:
                        large_files.append({
                            'path': file_path,
                            'size': size,
                            'size_mb': size / (1024*1024),
                            'modified': os.path.getmtime(file_path)
                        })
                except (OSError, PermissionError):
                    continue
        
        return sorted(large_files, key=lambda x: x['size'], reverse=True)
    
    def find_old_files(self, path: str, days_old: int = 30) -> List[Dict[str, Any]]:
        """查找旧文件"""
        old_files = []
        cutoff_time = time.time() - (days_old * 24 * 3600)
        
        for root, dirs, files in os.walk(path):
            for file in files:
                try:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    if mtime < cutoff_time:
                        old_files.append({
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'size_mb': os.path.getsize(file_path) / (1024*1024),
                            'modified': mtime,
                            'days_old': (time.time() - mtime) / (24*3600)
                        })
                except (OSError, PermissionError):
                    continue
        
        return sorted(old_files, key=lambda x: x['modified'])
    
    def find_temp_files(self, path: str) -> List[Dict[str, Any]]:
        """查找临时文件"""
        temp_patterns = ['*.tmp', '*.temp', '*.log', '*.cache', '*.swp', '*.pyc']
        temp_files = []
        
        for root, dirs, files in os.walk(path):
            for pattern in temp_patterns:
                for file in fnmatch.filter(files, pattern):
                    try:
                        file_path = os.path.join(root, file)
                        temp_files.append({
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'size_mb': os.path.getsize(file_path) / (1024*1024),
                            'pattern': pattern
                        })
                    except (OSError, PermissionError):
                        continue
        
        return temp_files
    
    def delete_files(self, files: List[str], dry_run: bool = True) -> Dict[str, Any]:
        """删除文件"""
        result = {
            'deleted': 0,
            'freed_space': 0,
            'errors': []
        }
        
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    if not dry_run:
                        os.remove(file_path)
                    result['deleted'] += 1
                    result['freed_space'] += size
            except Exception as e:
                result['errors'].append(f"删除 {file_path} 失败: {e}")
        
        if dry_run:
            result['note'] = '此为模拟运行，未实际删除文件'
        
        self.cleaned_files += result['deleted']
        self.freed_space += result['freed_space']
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取清理统计"""
        return {
            'total_cleaned_files': self.cleaned_files,
            'total_freed_space': self.freed_space,
            'total_freed_space_mb': self.freed_space / (1024*1024),
            'total_freed_space_gb': self.freed_space / (1024**3)
        }


class DiskBenchmark:
    """磁盘基准测试"""
    
    def __init__(self, test_dir: str = './disk_test'):
        self.test_dir = test_dir
        os.makedirs(test_dir, exist_ok=True)
    
    def test_sequential_read_write(self, file_size_mb: int = 100) -> Dict[str, Any]:
        """测试顺序读写速度"""
        test_file = os.path.join(self.test_dir, 'seq_test.tmp')
        
        # 准备测试数据
        data = os.urandom(1024 * 1024)  # 1MB块
        
        # 写入测试
        start_time = time.time()
        with open(test_file, 'wb') as f:
            for _ in range(file_size_mb):
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.time() - start_time
        write_speed = (file_size_mb * 1024 * 1024) / write_time
        
        # 读取测试
        start_time = time.time()
        with open(test_file, 'rb') as f:
            while f.read(1024 * 1024):
                pass
        read_time = time.time() - start_time
        read_speed = (file_size_mb * 1024 * 1024) / read_time
        
        # 清理
        os.remove(test_file)
        
        return {
            'file_size_mb': file_size_mb,
            'write_speed_bps': write_speed,
            'write_speed_mbps': write_speed / (1024*1024),
            'write_time': write_time,
            'read_speed_bps': read_speed,
            'read_speed_mbps': read_speed / (1024*1024),
            'read_time': read_time
        }
    
    def test_random_read_write(self, file_size_mb: int = 100, operations: int = 1000) -> Dict[str, Any]:
        """测试随机读写速度"""
        import random
        
        test_file = os.path.join(self.test_dir, 'random_test.tmp')
        
        # 创建测试文件
        with open(test_file, 'wb') as f:
            f.write(os.urandom(file_size_mb * 1024 * 1024))
        
        block_size = 4096  # 4KB块
        max_offset = file_size_mb * 1024 * 1024 - block_size
        
        # 随机写入测试
        data = os.urandom(block_size)
        write_start = time.time()
        with open(test_file, 'r+b') as f:
            for _ in range(operations):
                offset = random.randint(0, max_offset)
                f.seek(offset)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        write_time = time.time() - write_start
        write_iops = operations / write_time
        
        # 随机读取测试
        read_start = time.time()
        with open(test_file, 'rb') as f:
            for _ in range(operations):
                offset = random.randint(0, max_offset)
                f.seek(offset)
                f.read(block_size)
        read_time = time.time() - read_start
        read_iops = operations / read_time
        
        # 清理
        os.remove(test_file)
        
        return {
            'file_size_mb': file_size_mb,
            'operations': operations,
            'block_size': block_size,
            'write_iops': write_iops,
            'write_time': write_time,
            'read_iops': read_iops,
            'read_time': read_time
        }
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """运行完整基准测试"""
        results = {
            'sequential': self.test_sequential_read_write(100),
            'random_4k': self.test_random_read_write(100, 1000),
            'timestamp': time.time()
        }
        
        # 清理测试目录
        shutil.rmtree(self.test_dir)
        
        return results


class DirectoryWatcher:
    """目录监控器"""
    
    def __init__(self, path: str):
        self.path = path
        self.watching = False
        self.watch_thread = None
        self.changes = []
        self.file_sizes = {}
        self.lock = threading.Lock()
    
    def start_watching(self, interval: float = 1.0):
        """开始监控目录"""
        self.watching = True
        self._scan_directory()
        
        self.watch_thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True
        )
        self.watch_thread.start()
        logger.info(f"开始监控目录: {self.path}")
    
    def stop_watching(self):
        """停止监控"""
        self.watching = False
        if self.watch_thread:
            self.watch_thread.join()
        logger.info("停止监控目录")
    
    def _scan_directory(self) -> Dict[str, Dict]:
        """扫描目录"""
        current_files = {}
        
        for root, dirs, files in os.walk(self.path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    current_files[file_path] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                        'ctime': stat.st_ctime
                    }
                except (OSError, PermissionError):
                    continue
        
        return current_files
    
    def _watch_loop(self, interval: float):
        """监控循环"""
        while self.watching:
            try:
                current = self._scan_directory()
                
                with self.lock:
                    # 检查新增文件
                    for file_path in current:
                        if file_path not in self.file_sizes:
                            self.changes.append({
                                'type': 'created',
                                'path': file_path,
                                'timestamp': time.time()
                            })
                    
                    # 检查删除文件
                    for file_path in self.file_sizes:
                        if file_path not in current:
                            self.changes.append({
                                'type': 'deleted',
                                'path': file_path,
                                'timestamp': time.time()
                            })
                    
                    # 检查修改文件
                    for file_path in current:
                        if file_path in self.file_sizes:
                            if current[file_path]['mtime'] != self.file_sizes[file_path]['mtime']:
                                self.changes.append({
                                    'type': 'modified',
                                    'path': file_path,
                                    'timestamp': time.time()
                                })
                    
                    self.file_sizes = current
                
            except Exception as e:
                logger.error(f"目录监控错误: {e}")
            
            time.sleep(interval)
    
    def get_changes(self, clear: bool = True) -> List[Dict[str, Any]]:
        """获取变更记录"""
        with self.lock:
            changes = list(self.changes)
            if clear:
                self.changes.clear()
            return changes


def get_disk_usage(path: str = '/') -> Dict[str, Any]:
    """获取磁盘使用情况（便捷函数）"""
    monitor = DiskMonitor()
    return monitor.get_disk_usage(path)


def get_disk_partitions() -> List[Dict[str, Any]]:
    """获取磁盘分区信息（便捷函数）"""
    monitor = DiskMonitor()
    return monitor.get_disk_partitions()


def calculate_disk_score() -> Dict[str, Any]:
    """计算磁盘性能分数"""
    benchmark = DiskBenchmark()
    results = benchmark.run_full_benchmark()
    
    # 计算分数
    seq_score = results['sequential']['read_speed_mbps'] + results['sequential']['write_speed_mbps']
    random_score = results['random_4k']['read_iops'] + results['random_4k']['write_iops']
    
    return {
        'sequential_score': seq_score,
        'random_score': random_score,
        'total_score': (seq_score + random_score) / 2,
        'details': results
    }