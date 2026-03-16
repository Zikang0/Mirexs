"""
同步指标模块 - Mirexs数据同步系统

收集和报告数据同步的性能指标，包括：
1. 同步速度
2. 数据量统计
3. 延迟统计
4. 错误统计
5. 设备统计
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型枚举"""
    SPEED = "speed"              # 同步速度
    VOLUME = "volume"            # 数据量
    LATENCY = "latency"          # 延迟
    ERROR = "error"              # 错误
    DEVICE = "device"            # 设备
    CUSTOM = "custom"            # 自定义

@dataclass
class SyncPerformance:
    """同步性能"""
    items_per_second: float = 0.0
    bytes_per_second: float = 0.0
    avg_item_size: float = 0.0
    sync_duration: float = 0.0
    total_items: int = 0
    total_bytes: int = 0

@dataclass
class LatencyStats:
    """延迟统计"""
    min_ms: float = 0.0
    max_ms: float = 0.0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    sample_count: int = 0

@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None

@dataclass
class DeviceSyncStats:
    """设备同步统计"""
    device_id: str
    device_name: str
    last_sync: Optional[float] = None
    items_synced: int = 0
    bytes_transferred: int = 0
    avg_speed: float = 0.0
    success_rate: float = 100.0
    status: str = "unknown"

@dataclass
class SyncStats:
    """同步统计"""
    performance: SyncPerformance = field(default_factory=SyncPerformance)
    latency: LatencyStats = field(default_factory=LatencyStats)
    errors: ErrorStats = field(default_factory=ErrorStats)
    devices: Dict[str, DeviceSyncStats] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

@dataclass
class SyncMetricsConfig:
    """同步指标配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    window_size: int = 100  # 样本窗口大小
    
    # 阈值配置
    speed_threshold: float = 1024 * 1024  # 1MB/s
    latency_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.05  # 5%
    
    # 历史记录
    keep_history: bool = True
    max_history: int = 1000

class SyncMetrics:
    """
    同步指标收集器
    
    负责收集数据同步的性能指标。
    """
    
    def __init__(self, config: Optional[SyncMetricsConfig] = None):
        """
        初始化同步指标收集器
        
        Args:
            config: 指标配置
        """
        self.config = config or SyncMetricsConfig()
        
        # 统计
        self.stats = SyncStats()
        
        # 样本窗口
        self.speed_samples = deque(maxlen=self.config.window_size)
        self.latency_samples = deque(maxlen=self.config.window_size)
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        # 采样线程
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # 回调函数
        self.on_metrics_updated: Optional[Callable[[SyncStats], None]] = None
        self.on_threshold_exceeded: Optional[Callable[[str, str, float], None]] = None
        
        # 启动采样
        self._start_sampling()
        
        logger.info("SyncMetrics initialized")
    
    def _start_sampling(self):
        """启动采样"""
        def sampling_loop():
            while not self._stop_sampling.is_set():
                try:
                    self._update_stats()
                    self._check_thresholds()
                    self._add_to_history()
                    self._stop_sampling.wait(self.config.sample_interval)
                except Exception as e:
                    logger.error(f"Sampling error: {e}")
        
        self._sampling_thread = threading.Thread(target=sampling_loop, daemon=True)
        self._sampling_thread.start()
        logger.debug("Metrics sampling started")
    
    def _update_stats(self):
        """更新统计"""
        # 更新性能统计
        if self.speed_samples:
            self.stats.performance.items_per_second = sum(s.items_per_second for s in self.speed_samples) / len(self.speed_samples)
            self.stats.performance.bytes_per_second = sum(s.bytes_per_second for s in self.speed_samples) / len(self.speed_samples)
        
        # 更新延迟统计
        if self.latency_samples:
            samples = sorted(self.latency_samples)
            self.stats.latency.min_ms = samples[0]
            self.stats.latency.max_ms = samples[-1]
            self.stats.latency.avg_ms = sum(samples) / len(samples)
            self.stats.latency.p50_ms = samples[int(len(samples) * 0.5)]
            self.stats.latency.p95_ms = samples[int(len(samples) * 0.95)]
            self.stats.latency.p99_ms = samples[int(len(samples) * 0.99)]
            self.stats.latency.sample_count = len(samples)
        
        self.stats.last_update = time.time()
        
        if self.on_metrics_updated:
            self.on_metrics_updated(self.stats)
    
    def _check_thresholds(self):
        """检查阈值"""
        # 检查速度
        if self.stats.performance.bytes_per_second < self.config.speed_threshold:
            self._trigger_threshold("performance", "speed", self.stats.performance.bytes_per_second)
        
        # 检查延迟
        if self.stats.latency.avg_ms > self.config.latency_threshold_ms:
            self._trigger_threshold("latency", "average", self.stats.latency.avg_ms)
        
        # 检查错误率
        if self.stats.performance.total_items > 0:
            error_rate = self.stats.errors.total_errors / self.stats.performance.total_items
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("error", "rate", error_rate)
    
    def _trigger_threshold(self, category: str, metric: str, value: float):
        """触发阈值告警"""
        if self.on_threshold_exceeded:
            self.on_threshold_exceeded(category, metric, value)
    
    def _add_to_history(self):
        """添加到历史"""
        if not self.config.keep_history:
            return
        
        snapshot = {
            "timestamp": time.time(),
            "performance": {
                "items_per_second": self.stats.performance.items_per_second,
                "bytes_per_second": self.stats.performance.bytes_per_second,
                "total_items": self.stats.performance.total_items,
                "total_bytes": self.stats.performance.total_bytes
            },
            "latency": {
                "avg_ms": self.stats.latency.avg_ms,
                "p95_ms": self.stats.latency.p95_ms,
                "p99_ms": self.stats.latency.p99_ms
            },
            "errors": {
                "total": self.stats.errors.total_errors,
                "types": dict(self.stats.errors.error_types)
            },
            "devices": len(self.stats.devices)
        }
        
        self.history.append(snapshot)
        
        if len(self.history) > self.config.max_history:
            self.history = self.history[-self.config.max_history:]
    
    def record_sync(self, items: int, bytes_transferred: int, duration_ms: float,
                   device_id: Optional[str] = None, success: bool = True):
        """
        记录同步
        
        Args:
            items: 同步项数量
            bytes_transferred: 传输字节数
            duration_ms: 持续时间（毫秒）
            device_id: 设备ID
            success: 是否成功
        """
        # 计算速度
        items_per_second = items / (duration_ms / 1000) if duration_ms > 0 else 0
        bytes_per_second = bytes_transferred / (duration_ms / 1000) if duration_ms > 0 else 0
        
        # 添加到样本
        self.speed_samples.append(
            SyncPerformance(
                items_per_second=items_per_second,
                bytes_per_second=bytes_per_second,
                total_items=items,
                total_bytes=bytes_transferred,
                sync_duration=duration_ms
            )
        )
        
        # 更新总计
        self.stats.performance.total_items += items
        self.stats.performance.total_bytes += bytes_transferred
        
        # 记录延迟
        self.latency_samples.append(duration_ms)
        
        # 记录设备
        if device_id:
            if device_id not in self.stats.devices:
                self.stats.devices[device_id] = DeviceSyncStats(
                    device_id=device_id,
                    device_name=f"Device {device_id[:8]}"
                )
            
            device_stats = self.stats.devices[device_id]
            device_stats.last_sync = time.time()
            device_stats.items_synced += items
            device_stats.bytes_transferred += bytes_transferred
            device_stats.avg_speed = bytes_per_second
        
        logger.debug(f"Sync recorded: {items} items, {bytes_transferred} bytes, {duration_ms:.2f}ms")
    
    def record_error(self, error_type: str, error_msg: str,
                    device_id: Optional[str] = None):
        """
        记录错误
        
        Args:
            error_type: 错误类型
            error_msg: 错误信息
            device_id: 设备ID
        """
        self.stats.errors.total_errors += 1
        self.stats.errors.error_types[error_type] = self.stats.errors.error_types.get(error_type, 0) + 1
        self.stats.errors.last_error = error_msg
        self.stats.errors.last_error_time = time.time()
        
        logger.debug(f"Error recorded: {error_type} - {error_msg}")
    
    def update_device_status(self, device_id: str, status: str):
        """
        更新设备状态
        
        Args:
            device_id: 设备ID
            status: 状态
        """
        if device_id not in self.stats.devices:
            self.stats.devices[device_id] = DeviceSyncStats(
                device_id=device_id,
                device_name=f"Device {device_id[:8]}"
            )
        
        self.stats.devices[device_id].status = status
    
    def get_device_stats(self, device_id: str) -> Optional[DeviceSyncStats]:
        """获取设备统计"""
        return self.stats.devices.get(device_id)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取摘要统计
        
        Returns:
            摘要字典
        """
        return {
            "performance": {
                "items_per_second": round(self.stats.performance.items_per_second, 2),
                "bytes_per_second": round(self.stats.performance.bytes_per_second, 2),
                "total_items": self.stats.performance.total_items,
                "total_mb": round(self.stats.performance.total_bytes / (1024 * 1024), 2)
            },
            "latency": {
                "avg_ms": round(self.stats.latency.avg_ms, 2),
                "p95_ms": round(self.stats.latency.p95_ms, 2),
                "p99_ms": round(self.stats.latency.p99_ms, 2)
            },
            "errors": {
                "total": self.stats.errors.total_errors,
                "rate": round(self.stats.errors.total_errors / max(1, self.stats.performance.total_items) * 100, 2)
            },
            "devices": {
                "total": len(self.stats.devices),
                "active": len([d for d in self.stats.devices.values() if d.status == "online"])
            },
            "uptime": time.time() - self.stats.start_time
        }
    
    def reset(self):
        """重置统计"""
        self.stats = SyncStats()
        self.speed_samples.clear()
        self.latency_samples.clear()
        self.history.clear()
        logger.info("Metrics reset")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取指标收集器状态
        
        Returns:
            状态字典
        """
        return {
            "summary": self.get_summary(),
            "history_size": len(self.history),
            "samples": {
                "speed": len(self.speed_samples),
                "latency": len(self.latency_samples)
            },
            "config": {
                "sample_interval": self.config.sample_interval,
                "window_size": self.config.window_size
            }
        }
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down SyncMetrics...")
        
        self._stop_sampling.set()
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2)
        
        self.stats = SyncStats()
        self.speed_samples.clear()
        self.latency_samples.clear()
        self.history.clear()
        
        logger.info("SyncMetrics shutdown completed")

# 单例模式实现
_sync_metrics_instance: Optional[SyncMetrics] = None

def get_sync_metrics(config: Optional[SyncMetricsConfig] = None) -> SyncMetrics:
    """
    获取同步指标收集器单例
    
    Args:
        config: 指标配置
    
    Returns:
        同步指标收集器实例
    """
    global _sync_metrics_instance
    if _sync_metrics_instance is None:
        _sync_metrics_instance = SyncMetrics(config)
    return _sync_metrics_instance

