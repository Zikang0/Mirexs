"""
API指标模块 - Mirexs API网关

收集和报告API性能指标，包括：
1. 请求量统计
2. 响应时间
3. 错误率
4. 并发数
5. 带宽使用
6. 用户统计
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 测量值
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"          # 计时器

@dataclass
class MetricValue:
    """指标值"""
    name: str
    type: MetricType
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class APIPerformance:
    """API性能"""
    requests_per_second: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    error_rate: float = 0.0
    concurrent_requests: int = 0
    active_users: int = 0
    bandwidth_in_mbps: float = 0.0
    bandwidth_out_mbps: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0

@dataclass
class MetricsCollector:
    """指标收集器"""
    metrics: Dict[str, List[MetricValue]] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)
    histograms: Dict[str, deque] = field(default_factory=dict)

@dataclass
class MetricsConfig:
    """指标配置"""
    # 采样配置
    collection_interval: int = 10  # 秒
    retention_period: int = 86400  # 秒
    
    # 直方图配置
    histogram_buckets: List[float] = field(default_factory=lambda: [10, 50, 100, 200, 500, 1000, 2000, 5000])
    histogram_max_size: int = 1000
    
    # 导出配置
    export_enabled: bool = False
    export_endpoint: Optional[str] = None

class APIMetrics:
    """
    API指标收集器
    
    负责收集API的性能指标。
    """
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        """
        初始化API指标收集器
        
        Args:
            config: 指标配置
        """
        self.config = config or MetricsConfig()
        
        # 指标存储
        self.collector = MetricsCollector()
        
        # 当前性能
        self.performance = APIPerformance()
        
        # 请求时间窗口
        self.request_times = deque(maxlen=self.config.histogram_max_size)
        self.response_times = deque(maxlen=self.config.histogram_max_size)
        
        # 并发计数
        self.concurrent_requests = 0
        self.concurrent_lock = threading.Lock()
        
        # 带宽计数
        self.bytes_in = 0
        self.bytes_out = 0
        self.last_bandwidth_time = time.time()
        
        # 收集线程
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_collection = threading.Event()
        
        # 回调函数
        self.on_metrics_collected: Optional[Callable[[APIPerformance], None]] = None
        
        # 统计
        self.stats = {
            "metrics_collected": 0,
            "total_requests": 0,
            "total_errors": 0
        }
        
        # 启动收集
        self._start_collection()
        
        logger.info("APIMetrics initialized")
    
    def _start_collection(self):
        """启动指标收集"""
        def collection_loop():
            while not self._stop_collection.is_set():
                try:
                    self._collect_metrics()
                    self._stop_collection.wait(self.config.collection_interval)
                except Exception as e:
                    logger.error(f"Collection error: {e}")
        
        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        logger.debug("Metrics collection started")
    
    def _collect_metrics(self):
        """收集指标"""
        current_time = time.time()
        window = 60  # 1分钟窗口
        
        # 计算请求速率
        recent_requests = [t for t in self.request_times if t > current_time - window]
        self.performance.requests_per_second = len(recent_requests) / window
        
        # 计算响应时间
        if self.response_times:
            times = list(self.response_times)
            self.performance.avg_response_time_ms = sum(times) / len(times)
            
            sorted_times = sorted(times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            self.performance.p95_response_time_ms = sorted_times[p95_idx]
            self.performance.p99_response_time_ms = sorted_times[p99_idx]
        
        # 计算错误率
        if self.stats["total_requests"] > 0:
            self.performance.error_rate = self.stats["total_errors"] / self.stats["total_requests"]
        
        # 并发请求
        self.performance.concurrent_requests = self.concurrent_requests
        
        # 计算带宽
        bandwidth_window = current_time - self.last_bandwidth_time
        if bandwidth_window > 0:
            self.performance.bandwidth_in_mbps = (self.bytes_in * 8) / (bandwidth_window * 1024 * 1024)
            self.performance.bandwidth_out_mbps = (self.bytes_out * 8) / (bandwidth_window * 1024 * 1024)
            
            # 重置计数器
            self.bytes_in = 0
            self.bytes_out = 0
            self.last_bandwidth_time = current_time
        
        # 系统指标
        self.performance.cpu_percent = psutil.cpu_percent()
        self.performance.memory_percent = psutil.virtual_memory().percent
        
        self.stats["metrics_collected"] += 1
        
        if self.on_metrics_collected:
            self.on_metrics_collected(self.performance)
    
    def record_request(self, response_time_ms: float, success: bool = True,
                      bytes_in: int = 0, bytes_out: int = 0):
        """
        记录请求
        
        Args:
            response_time_ms: 响应时间（毫秒）
            success: 是否成功
            bytes_in: 入站字节数
            bytes_out: 出站字节数
        """
        self.request_times.append(time.time())
        self.response_times.append(response_time_ms)
        self.stats["total_requests"] += 1
        
        if not success:
            self.stats["total_errors"] += 1
        
        self.bytes_in += bytes_in
        self.bytes_out += bytes_out
    
    def increment_concurrent(self):
        """增加并发计数"""
        with self.concurrent_lock:
            self.concurrent_requests += 1
    
    def decrement_concurrent(self):
        """减少并发计数"""
        with self.concurrent_lock:
            self.concurrent_requests = max(0, self.concurrent_requests - 1)
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict] = None):
        """
        增加计数器
        
        Args:
            name: 计数器名称
            value: 增加值
            tags: 标签
        """
        if name not in self.collector.counters:
            self.collector.counters[name] = 0
        self.collector.counters[name] += value
        
        metric = MetricValue(
            name=name,
            type=MetricType.COUNTER,
            value=self.collector.counters[name],
            tags=tags or {}
        )
        
        self._add_metric(metric)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict] = None):
        """
        设置测量值
        
        Args:
            name: 测量名称
            value: 测量值
            tags: 标签
        """
        self.collector.gauges[name] = value
        
        metric = MetricValue(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            tags=tags or {}
        )
        
        self._add_metric(metric)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict] = None):
        """
        记录直方图
        
        Args:
            name: 直方图名称
            value: 值
            tags: 标签
        """
        if name not in self.collector.histograms:
            self.collector.histograms[name] = deque(maxlen=self.config.histogram_max_size)
        
        self.collector.histograms[name].append(value)
        
        metric = MetricValue(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            tags=tags or {}
        )
        
        self._add_metric(metric)
    
    def _add_metric(self, metric: MetricValue):
        """添加指标"""
        if metric.name not in self.collector.metrics:
            self.collector.metrics[metric.name] = []
        
        self.collector.metrics[metric.name].append(metric)
        
        # 清理旧指标
        cutoff = time.time() - self.config.retention_period
        self.collector.metrics[metric.name] = [
            m for m in self.collector.metrics[metric.name]
            if m.timestamp > cutoff
        ]
    
    def get_counter(self, name: str) -> int:
        """获取计数器值"""
        return self.collector.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """获取测量值"""
        return self.collector.gauges.get(name, 0.0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        if name not in self.collector.histograms:
            return {}
        
        values = list(self.collector.histograms[name])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted_values[int(len(sorted_values) * 0.5)],
            "p95": sorted_values[int(len(sorted_values) * 0.95)],
            "p99": sorted_values[int(len(sorted_values) * 0.99)],
            "count": len(values)
        }
    
    def get_metrics(self, name: Optional[str] = None,
                   since: Optional[float] = None) -> Dict[str, List[MetricValue]]:
        """
        获取指标
        
        Args:
            name: 指标名称
            since: 起始时间
        
        Returns:
            指标字典
        """
        if name:
            metrics = {name: self.collector.metrics.get(name, [])}
        else:
            metrics = self.collector.metrics.copy()
        
        if since:
            filtered = {}
            for n, values in metrics.items():
                filtered[n] = [v for v in values if v.timestamp >= since]
            return filtered
        
        return metrics
    
    def get_performance(self) -> APIPerformance:
        """获取当前性能"""
        return self.performance
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取API指标收集器状态
        
        Returns:
            状态字典
        """
        return {
            "performance": {
                "requests_per_second": round(self.performance.requests_per_second, 2),
                "avg_response_time_ms": round(self.performance.avg_response_time_ms, 2),
                "p95_response_time_ms": round(self.performance.p95_response_time_ms, 2),
                "p99_response_time_ms": round(self.performance.p99_response_time_ms, 2),
                "error_rate": round(self.performance.error_rate * 100, 2),
                "concurrent_requests": self.performance.concurrent_requests,
                "cpu_percent": round(self.performance.cpu_percent, 2),
                "memory_percent": round(self.performance.memory_percent, 2)
            },
            "metrics": {
                "counters": len(self.collector.counters),
                "gauges": len(self.collector.gauges),
                "histograms": len(self.collector.histograms),
                "total_series": len(self.collector.metrics)
            },
            "stats": self.stats,
            "config": {
                "collection_interval": self.config.collection_interval,
                "retention_period": self.config.retention_period
            }
        }
    
    def shutdown(self):
        """关闭API指标收集器"""
        logger.info("Shutting down APIMetrics...")
        
        self._stop_collection.set()
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=2)
        
        self.collector.metrics.clear()
        self.collector.counters.clear()
        self.collector.gauges.clear()
        self.collector.histograms.clear()
        self.request_times.clear()
        self.response_times.clear()
        
        logger.info("APIMetrics shutdown completed")

# 单例模式实现
_api_metrics_instance: Optional[APIMetrics] = None

def get_api_metrics(config: Optional[MetricsConfig] = None) -> APIMetrics:
    """
    获取API指标收集器单例
    
    Args:
        config: 指标配置
    
    Returns:
        API指标收集器实例
    """
    global _api_metrics_instance
    if _api_metrics_instance is None:
        _api_metrics_instance = APIMetrics(config)
    return _api_metrics_instance

