"""
协议指标模块 - Mirexs协议适配器

收集和报告各种协议的性能指标，包括：
1. 连接指标
2. 消息指标
3. 延迟指标
4. 错误指标
5. 带宽使用
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

class ProtocolType(Enum):
    """协议类型枚举"""
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    USB = "usb"
    CLOUD = "cloud"
    MQTT = "mqtt"
    WEBSOCKET = "websocket"
    HTTP = "http"
    ZIGBEE = "zigbee"
    Z_WAVE = "z_wave"
    MODBUS = "modbus"
    CAN = "can"
    SERIAL = "serial"
    CUSTOM = "custom"

class MetricType(Enum):
    """指标类型枚举"""
    CONNECTION = "connection"
    MESSAGE = "message"
    LATENCY = "latency"
    BANDWIDTH = "bandwidth"
    ERROR = "error"
    CUSTOM = "custom"

@dataclass
class ConnectionMetric:
    """连接指标"""
    protocol: ProtocolType
    status: str
    connect_time: float
    disconnect_time: Optional[float] = None
    duration: Optional[float] = None
    reconnect_count: int = 0
    endpoint: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class MessageMetric:
    """消息指标"""
    protocol: ProtocolType
    direction: str  # send/receive
    count: int = 1
    bytes: int = 0
    avg_size: float = 0.0
    rate: float = 0.0  # 消息/秒
    timestamp: float = field(default_factory=time.time)

@dataclass
class LatencyMetric:
    """延迟指标"""
    protocol: ProtocolType
    min_ms: float
    max_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int
    timestamp: float = field(default_factory=time.time)

@dataclass
class ErrorMetric:
    """错误指标"""
    protocol: ProtocolType
    error_type: str
    count: int
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class BandwidthMetric:
    """带宽指标"""
    protocol: ProtocolType
    bytes_sent: int
    bytes_received: int
    send_rate: float  # 字节/秒
    receive_rate: float  # 字节/秒
    total_bytes: int
    timestamp: float = field(default_factory=time.time)

@dataclass
class ProtocolStats:
    """协议统计"""
    protocol: ProtocolType
    connections: ConnectionMetric
    messages: MessageMetric
    latency: LatencyMetric
    errors: ErrorMetric
    bandwidth: BandwidthMetric
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

@dataclass
class ProtocolMetricsConfig:
    """协议指标配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    history_size: int = 1000
    
    # 延迟计算
    latency_window: int = 100  # 样本数
    
    # 速率计算
    rate_window: int = 60  # 秒
    
    # 告警阈值
    latency_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.1  # 10%
    bandwidth_threshold_mbps: float = 10.0
    
    # 持久化
    save_metrics: bool = True
    metrics_file: str = "protocol_metrics.json"

class ProtocolMetrics:
    """
    协议指标收集器
    
    负责收集各种协议的性能指标。
    """
    
    def __init__(self, config: Optional[ProtocolMetricsConfig] = None):
        """
        初始化协议指标收集器
        
        Args:
            config: 指标配置
        """
        self.config = config or ProtocolMetricsConfig()
        
        # 协议统计
        self.stats: Dict[str, ProtocolStats] = {}
        
        # 延迟样本
        self.latency_samples: Dict[str, deque] = {}
        
        # 消息计数
        self.message_counts: Dict[str, Dict[str, int]] = {}  # protocol -> {send: 0, receive: 0}
        
        # 字节计数
        self.byte_counts: Dict[str, Dict[str, int]] = {}  # protocol -> {sent: 0, received: 0}
        
        # 错误计数
        self.error_counts: Dict[str, Dict[str, int]] = {}  # protocol -> {error_type: count}
        
        # 时间窗口
        self.time_windows: Dict[str, deque] = {}  # 用于计算速率
        
        # 收集线程
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_collection = threading.Event()
        
        # 回调函数
        self.on_metric_updated: Optional[Callable[[str, ProtocolStats], None]] = None
        self.on_threshold_exceeded: Optional[Callable[[str, str, float], None]] = None
        
        # 启动收集
        self._start_collection()
        
        logger.info("ProtocolMetrics initialized")
    
    def _start_collection(self):
        """启动指标收集"""
        def collection_loop():
            while not self._stop_collection.is_set():
                try:
                    self._update_all_stats()
                    self._check_thresholds()
                    self._stop_collection.wait(self.config.sample_interval)
                except Exception as e:
                    logger.error(f"Collection error: {e}")
        
        self._collection_thread = threading.Thread(target=collection_loop, daemon=True)
        self._collection_thread.start()
        logger.debug("Metrics collection started")
    
    def _get_protocol_key(self, protocol: ProtocolType, endpoint: str = "") -> str:
        """获取协议键"""
        if endpoint:
            return f"{protocol.value}:{endpoint}"
        return protocol.value
    
    def _ensure_protocol_stats(self, protocol: ProtocolType, endpoint: str = ""):
        """确保协议统计存在"""
        key = self._get_protocol_key(protocol, endpoint)
        
        if key not in self.stats:
            self.stats[key] = ProtocolStats(
                protocol=protocol,
                connections=ConnectionMetric(protocol=protocol, status="unknown", connect_time=0),
                messages=MessageMetric(protocol=protocol, direction="total", count=0, bytes=0),
                latency=LatencyMetric(
                    protocol=protocol,
                    min_ms=0, max_ms=0, avg_ms=0,
                    p50_ms=0, p95_ms=0, p99_ms=0,
                    sample_count=0
                ),
                errors=ErrorMetric(protocol=protocol, error_type="total", count=0),
                bandwidth=BandwidthMetric(
                    protocol=protocol,
                    bytes_sent=0, bytes_received=0,
                    send_rate=0, receive_rate=0,
                    total_bytes=0
                )
            )
            
            self.latency_samples[key] = deque(maxlen=self.config.latency_window)
            self.message_counts[key] = {"send": 0, "receive": 0}
            self.byte_counts[key] = {"sent": 0, "received": 0}
            self.error_counts[key] = {}
            self.time_windows[key] = deque(maxlen=self.config.rate_window)
    
    def record_connection(self, protocol: ProtocolType, status: str, 
                         connect_time: float, endpoint: str = ""):
        """
        记录连接指标
        
        Args:
            protocol: 协议类型
            status: 连接状态
            connect_time: 连接时间（毫秒）
            endpoint: 端点标识
        """
        key = self._get_protocol_key(protocol, endpoint)
        self._ensure_protocol_stats(protocol, endpoint)
        
        self.stats[key].connections = ConnectionMetric(
            protocol=protocol,
            status=status,
            connect_time=connect_time,
            endpoint=endpoint,
            timestamp=time.time()
        )
        
        logger.debug(f"Connection recorded for {key}: {status} ({connect_time}ms)")
    
    def record_message(self, protocol: ProtocolType, direction: str, 
                      size: int = 0, endpoint: str = ""):
        """
        记录消息指标
        
        Args:
            protocol: 协议类型
            direction: 方向 (send/receive)
            size: 消息大小（字节）
            endpoint: 端点标识
        """
        key = self._get_protocol_key(protocol, endpoint)
        self._ensure_protocol_stats(protocol, endpoint)
        
        # 更新消息计数
        if direction in self.message_counts[key]:
            self.message_counts[key][direction] += 1
        
        # 更新字节计数
        if direction == "send":
            self.byte_counts[key]["sent"] += size
        elif direction == "receive":
            self.byte_counts[key]["received"] += size
        
        # 记录时间窗口
        self.time_windows[key].append(time.time())
        
        logger.debug(f"Message recorded for {key}: {direction} ({size} bytes)")
    
    def record_latency(self, protocol: ProtocolType, latency_ms: float, 
                      endpoint: str = ""):
        """
        记录延迟指标
        
        Args:
            protocol: 协议类型
            latency_ms: 延迟（毫秒）
            endpoint: 端点标识
        """
        key = self._get_protocol_key(protocol, endpoint)
        self._ensure_protocol_stats(protocol, endpoint)
        
        self.latency_samples[key].append(latency_ms)
        
        logger.debug(f"Latency recorded for {key}: {latency_ms}ms")
    
    def record_error(self, protocol: ProtocolType, error_type: str, 
                    error_msg: str = "", endpoint: str = ""):
        """
        记录错误指标
        
        Args:
            protocol: 协议类型
            error_type: 错误类型
            error_msg: 错误信息
            endpoint: 端点标识
        """
        key = self._get_protocol_key(protocol, endpoint)
        self._ensure_protocol_stats(protocol, endpoint)
        
        if error_type not in self.error_counts[key]:
            self.error_counts[key][error_type] = 0
        
        self.error_counts[key][error_type] += 1
        
        # 更新最后错误
        self.stats[key].errors.last_error = error_msg
        self.stats[key].errors.last_error_time = time.time()
        
        logger.debug(f"Error recorded for {key}: {error_type}")
    
    def _update_all_stats(self):
        """更新所有统计"""
        for key in self.stats.keys():
            self._update_stats(key)
    
    def _update_stats(self, key: str):
        """更新单个协议的统计"""
        stats = self.stats[key]
        
        # 更新消息统计
        send_count = self.message_counts[key].get("send", 0)
        receive_count = self.message_counts[key].get("receive", 0)
        total_messages = send_count + receive_count
        
        # 计算消息速率
        now = time.time()
        window_start = now - self.config.rate_window
        
        recent_messages = [t for t in self.time_windows[key] if t > window_start]
        message_rate = len(recent_messages) / self.config.rate_window if recent_messages else 0
        
        stats.messages.count = total_messages
        stats.messages.rate = message_rate
        
        # 更新字节统计
        bytes_sent = self.byte_counts[key].get("sent", 0)
        bytes_received = self.byte_counts[key].get("received", 0)
        total_bytes = bytes_sent + bytes_received
        
        # 计算带宽速率
        bytes_in_window = sum(1 for _ in recent_messages) * stats.messages.avg_size if stats.messages.avg_size else 0
        send_rate = bytes_sent / self.config.rate_window if bytes_sent else 0
        receive_rate = bytes_received / self.config.rate_window if bytes_received else 0
        
        stats.bandwidth.bytes_sent = bytes_sent
        stats.bandwidth.bytes_received = bytes_received
        stats.bandwidth.send_rate = send_rate
        stats.bandwidth.receive_rate = receive_rate
        stats.bandwidth.total_bytes = total_bytes
        
        # 更新延迟统计
        if self.latency_samples[key]:
            samples = list(self.latency_samples[key])
            samples.sort()
            
            stats.latency.min_ms = min(samples)
            stats.latency.max_ms = max(samples)
            stats.latency.avg_ms = sum(samples) / len(samples)
            stats.latency.p50_ms = samples[int(len(samples) * 0.5)]
            stats.latency.p95_ms = samples[int(len(samples) * 0.95)]
            stats.latency.p99_ms = samples[int(len(samples) * 0.99)]
            stats.latency.sample_count = len(samples)
        
        # 更新错误统计
        total_errors = sum(self.error_counts[key].values())
        stats.errors.count = total_errors
        
        stats.last_update = now
        
        if self.on_metric_updated:
            self.on_metric_updated(key, stats)
    
    def _check_thresholds(self):
        """检查阈值"""
        for key, stats in self.stats.items():
            # 检查延迟阈值
            if stats.latency.avg_ms > self.config.latency_threshold_ms:
                if self.on_threshold_exceeded:
                    self.on_threshold_exceeded(
                        key, "latency", stats.latency.avg_ms
                    )
            
            # 检查错误率
            if stats.messages.count > 0:
                error_rate = stats.errors.count / stats.messages.count
                if error_rate > self.config.error_rate_threshold:
                    if self.on_threshold_exceeded:
                        self.on_threshold_exceeded(
                            key, "error_rate", error_rate
                        )
            
            # 检查带宽
            total_rate = (stats.bandwidth.send_rate + stats.bandwidth.receive_rate) / (1024 * 1024)  # 转换为Mbps
            if total_rate > self.config.bandwidth_threshold_mbps:
                if self.on_threshold_exceeded:
                    self.on_threshold_exceeded(
                        key, "bandwidth", total_rate
                    )
    
    def get_stats(self, protocol: Optional[ProtocolType] = None, 
                 endpoint: str = "") -> Dict[str, Any]:
        """
        获取协议统计
        
        Args:
            protocol: 协议类型
            endpoint: 端点标识
        
        Returns:
            统计字典
        """
        if protocol:
            key = self._get_protocol_key(protocol, endpoint)
            if key in self.stats:
                stats = self.stats[key]
                return {
                    "protocol": stats.protocol.value,
                    "connections": {
                        "status": stats.connections.status,
                        "connect_time": stats.connections.connect_time,
                        "reconnect_count": stats.connections.reconnect_count
                    },
                    "messages": {
                        "total": stats.messages.count,
                        "rate": stats.messages.rate,
                        "avg_size": stats.messages.avg_size
                    },
                    "latency": {
                        "min_ms": stats.latency.min_ms,
                        "max_ms": stats.latency.max_ms,
                        "avg_ms": stats.latency.avg_ms,
                        "p95_ms": stats.latency.p95_ms,
                        "p99_ms": stats.latency.p99_ms
                    },
                    "errors": {
                        "total": stats.errors.count,
                        "last_error": stats.errors.last_error,
                        "last_error_time": stats.errors.last_error_time
                    },
                    "bandwidth": {
                        "bytes_sent": stats.bandwidth.bytes_sent,
                        "bytes_received": stats.bandwidth.bytes_received,
                        "send_rate": stats.bandwidth.send_rate,
                        "receive_rate": stats.bandwidth.receive_rate
                    },
                    "uptime": time.time() - stats.start_time,
                    "last_update": stats.last_update
                }
        
        # 返回所有统计
        return {
            key: {
                "protocol": stats.protocol.value,
                "messages": stats.messages.count,
                "errors": stats.errors.count,
                "avg_latency": stats.latency.avg_ms
            }
            for key, stats in self.stats.items()
        }
    
    def reset_stats(self, protocol: Optional[ProtocolType] = None, 
                   endpoint: str = ""):
        """
        重置统计
        
        Args:
            protocol: 协议类型
            endpoint: 端点标识
        """
        if protocol:
            key = self._get_protocol_key(protocol, endpoint)
            if key in self.stats:
                del self.stats[key]
            if key in self.latency_samples:
                del self.latency_samples[key]
            if key in self.message_counts:
                del self.message_counts[key]
            if key in self.byte_counts:
                del self.byte_counts[key]
            if key in self.error_counts:
                del self.error_counts[key]
            if key in self.time_windows:
                del self.time_windows[key]
        else:
            self.stats.clear()
            self.latency_samples.clear()
            self.message_counts.clear()
            self.byte_counts.clear()
            self.error_counts.clear()
            self.time_windows.clear()
        
        logger.info(f"Stats reset for {protocol.value if protocol else 'all protocols'}")
    
    def export_to_json(self) -> str:
        """
        导出统计到JSON
        
        Returns:
            JSON字符串
        """
        data = {
            "timestamp": time.time(),
            "stats": self.get_stats(),
            "config": {
                "sample_interval": self.config.sample_interval,
                "latency_window": self.config.latency_window,
                "rate_window": self.config.rate_window
            }
        }
        
        return json.dumps(data, indent=2, default=str)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取指标收集器状态
        
        Returns:
            状态字典
        """
        return {
            "active_protocols": len(self.stats),
            "total_messages": sum(s.messages.count for s in self.stats.values()),
            "total_errors": sum(s.errors.count for s in self.stats.values()),
            "config": {
                "sample_interval": self.config.sample_interval,
                "latency_threshold_ms": self.config.latency_threshold_ms
            }
        }
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down ProtocolMetrics...")
        
        self._stop_collection.set()
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=2)
        
        self.stats.clear()
        self.latency_samples.clear()
        self.message_counts.clear()
        self.byte_counts.clear()
        self.error_counts.clear()
        self.time_windows.clear()
        
        logger.info("ProtocolMetrics shutdown completed")

# 单例模式实现
_protocol_metrics_instance: Optional[ProtocolMetrics] = None

def get_protocol_metrics(config: Optional[ProtocolMetricsConfig] = None) -> ProtocolMetrics:
    """
    获取协议指标收集器单例
    
    Args:
        config: 指标配置
    
    Returns:
        协议指标收集器实例
    """
    global _protocol_metrics_instance
    if _protocol_metrics_instance is None:
        _protocol_metrics_instance = ProtocolMetrics(config)
    return _protocol_metrics_instance

