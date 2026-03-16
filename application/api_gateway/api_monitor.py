"""
API监控器模块 - Mirexs API网关

提供API监控功能，包括：
1. 请求统计
2. 响应时间监控
3. 错误率监控
4. 端点使用统计
5. 告警触发
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class MonitorStatus(Enum):
    """监控状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"

@dataclass
class EndpointStats:
    """端点统计"""
    path: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    last_request: Optional[float] = None
    status_codes: Dict[int, int] = field(default_factory=dict)
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))

@dataclass
class RequestLog:
    """请求日志"""
    id: str
    timestamp: float
    path: str
    method: str
    ip: str
    user_id: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    error: Optional[str] = None

@dataclass
class MonitorAlert:
    """监控告警"""
    id: str
    level: AlertLevel
    message: str
    endpoint: Optional[str] = None
    threshold: Optional[float] = None
    value: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class MonitorConfig:
    """监控器配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    history_window: int = 3600  # 秒
    
    # 阈值配置
    error_rate_threshold: float = 0.05  # 5%
    response_time_threshold: float = 1000  # 毫秒
    request_rate_threshold: int = 1000  # 请求/分钟
    
    # 告警配置
    enable_alerts: bool = True
    alert_cooldown: int = 300  # 秒
    
    # 日志配置
    keep_logs: bool = True
    max_logs: int = 10000

class APIMonitor:
    """
    API监控器
    
    负责API的监控和统计。
    """
    
    def __init__(self, config: Optional[MonitorConfig] = None):
        """
        初始化API监控器
        
        Args:
            config: 监控器配置
        """
        self.config = config or MonitorConfig()
        
        # 端点统计
        self.endpoint_stats: Dict[str, EndpointStats] = {}
        
        # 请求日志
        self.request_logs: deque = deque(maxlen=self.config.max_logs)
        
        # 告警记录
        self.alerts: List[MonitorAlert] = []
        self.last_alert_time: Dict[str, float] = {}
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        
        # 回调函数
        self.on_alert: Optional[Callable[[MonitorAlert], None]] = None
        self.on_status_change: Optional[Callable[[str, MonitorStatus], None]] = None
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "active_endpoints": 0,
            "alerts_triggered": 0,
            "alerts_resolved": 0
        }
        
        # 启动监控
        self._start_monitoring()
        
        logger.info("APIMonitor initialized")
    
    def _start_monitoring(self):
        """启动监控"""
        def monitor_loop():
            while not self._stop_monitor.is_set():
                try:
                    self._check_alerts()
                    self._cleanup_old_logs()
                    self._stop_monitor.wait(self.config.sample_interval)
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("API monitoring started")
    
    def _get_endpoint_key(self, path: str, method: str) -> str:
        """获取端点键"""
        return f"{method}:{path}"
    
    def record_request(self, path: str, method: str, ip: str,
                      status_code: Optional[int] = None,
                      response_time: Optional[float] = None,
                      user_id: Optional[str] = None,
                      request_size: Optional[int] = None,
                      response_size: Optional[int] = None,
                      error: Optional[str] = None):
        """
        记录请求
        
        Args:
            path: 请求路径
            method: HTTP方法
            ip: 客户端IP
            status_code: 状态码
            response_time: 响应时间（毫秒）
            user_id: 用户ID
            request_size: 请求大小（字节）
            response_size: 响应大小（字节）
            error: 错误信息
        """
        # 创建请求日志
        log = RequestLog(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            path=path,
            method=method,
            ip=ip,
            user_id=user_id,
            status_code=status_code,
            response_time=response_time,
            request_size=request_size,
            response_size=response_size,
            error=error
        )
        
        self.request_logs.append(log)
        self.stats["total_requests"] += 1
        
        # 更新端点统计
        key = self._get_endpoint_key(path, method)
        
        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = EndpointStats(
                path=path,
                method=method
            )
            self.stats["active_endpoints"] += 1
        
        stats = self.endpoint_stats[key]
        stats.total_requests += 1
        stats.last_request = time.time()
        
        if status_code:
            stats.status_codes[status_code] = stats.status_codes.get(status_code, 0) + 1
            
            if 200 <= status_code < 300:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
        
        if response_time:
            stats.total_response_time += response_time
            stats.min_response_time = min(stats.min_response_time, response_time)
            stats.max_response_time = max(stats.max_response_time, response_time)
            stats.avg_response_time = stats.total_response_time / stats.total_requests
            stats.response_times.append(response_time)
            
            # 计算百分位数
            if len(stats.response_times) > 10:
                sorted_times = sorted(stats.response_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                stats.p95_response_time = sorted_times[p95_idx]
                stats.p99_response_time = sorted_times[p99_idx]
    
    def _check_alerts(self):
        """检查告警条件"""
        if not self.config.enable_alerts:
            return
        
        current_time = time.time()
        
        for key, stats in self.endpoint_stats.items():
            # 检查错误率
            if stats.total_requests > 0:
                error_rate = stats.failed_requests / stats.total_requests
                if error_rate > self.config.error_rate_threshold:
                    self._trigger_alert(
                        level=AlertLevel.WARNING,
                        message=f"High error rate for {key}: {error_rate:.2%}",
                        endpoint=key,
                        threshold=self.config.error_rate_threshold,
                        value=error_rate
                    )
            
            # 检查响应时间
            if stats.avg_response_time > self.config.response_time_threshold:
                self._trigger_alert(
                    level=AlertLevel.WARNING,
                    message=f"High response time for {key}: {stats.avg_response_time:.0f}ms",
                    endpoint=key,
                    threshold=self.config.response_time_threshold,
                    value=stats.avg_response_time
                )
            
            # 检查请求速率
            recent_requests = [log for log in self.request_logs 
                              if log.path == stats.path and log.method == stats.method
                              and log.timestamp > current_time - 60]
            
            request_rate = len(recent_requests)
            if request_rate > self.config.request_rate_threshold:
                self._trigger_alert(
                    level=AlertLevel.INFO,
                    message=f"High request rate for {key}: {request_rate}/min",
                    endpoint=key,
                    threshold=self.config.request_rate_threshold,
                    value=request_rate
                )
    
    def _trigger_alert(self, level: AlertLevel, message: str,
                      endpoint: Optional[str] = None,
                      threshold: Optional[float] = None,
                      value: Optional[float] = None):
        """触发告警"""
        # 检查冷却时间
        if endpoint and endpoint in self.last_alert_time:
            if time.time() - self.last_alert_time[endpoint] < self.config.alert_cooldown:
                return
        
        alert = MonitorAlert(
            id=str(uuid.uuid4()),
            level=level,
            message=message,
            endpoint=endpoint,
            threshold=threshold,
            value=value
        )
        
        self.alerts.append(alert)
        self.stats["alerts_triggered"] += 1
        
        if endpoint:
            self.last_alert_time[endpoint] = time.time()
        
        logger.warning(f"Alert triggered: {level.value} - {message}")
        
        if self.on_alert:
            self.on_alert(alert)
    
    def _cleanup_old_logs(self):
        """清理旧日志"""
        cutoff = time.time() - self.config.history_window
        self.request_logs = deque(
            [log for log in self.request_logs if log.timestamp > cutoff],
            maxlen=self.config.max_logs
        )
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        确认告警
        
        Args:
            alert_id: 告警ID
        
        Returns:
            是否成功
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警ID
        
        Returns:
            是否成功
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                self.stats["alerts_resolved"] += 1
                logger.info(f"Alert resolved: {alert_id}")
                return True
        return False
    
    def get_endpoint_stats(self, path: Optional[str] = None,
                          method: Optional[str] = None) -> List[EndpointStats]:
        """
        获取端点统计
        
        Args:
            path: 路径过滤
            method: 方法过滤
        
        Returns:
            端点统计列表
        """
        stats = list(self.endpoint_stats.values())
        
        if path:
            stats = [s for s in stats if s.path == path]
        
        if method:
            stats = [s for s in stats if s.method == method]
        
        return stats
    
    def get_requests(self, limit: int = 100) -> List[RequestLog]:
        """
        获取请求日志
        
        Args:
            limit: 返回数量
        
        Returns:
            请求日志列表
        """
        return list(self.request_logs)[-limit:]
    
    def get_alerts(self, active_only: bool = False) -> List[MonitorAlert]:
        """
        获取告警列表
        
        Args:
            active_only: 只返回未解决的告警
        
        Returns:
            告警列表
        """
        alerts = self.alerts
        
        if active_only:
            alerts = [a for a in alerts if not a.resolved]
        
        return alerts
    
    def get_health_status(self) -> MonitorStatus:
        """
        获取健康状态
        
        Returns:
            健康状态
        """
        # 检查错误率
        total_requests = sum(s.total_requests for s in self.endpoint_stats.values())
        total_errors = sum(s.failed_requests for s in self.endpoint_stats.values())
        
        if total_requests > 0:
            error_rate = total_errors / total_requests
            
            if error_rate > 0.1:  # 10%
                return MonitorStatus.UNHEALTHY
            elif error_rate > 0.05:  # 5%
                return MonitorStatus.DEGRADED
        
        # 检查响应时间
        avg_response_time = sum(s.avg_response_time for s in self.endpoint_stats.values()) / max(len(self.endpoint_stats), 1)
        
        if avg_response_time > 2000:  # 2秒
            return MonitorStatus.UNHEALTHY
        elif avg_response_time > 1000:  # 1秒
            return MonitorStatus.DEGRADED
        
        return MonitorStatus.HEALTHY
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取API监控器状态
        
        Returns:
            状态字典
        """
        return {
            "health": self.get_health_status().value,
            "endpoints": {
                "total": len(self.endpoint_stats),
                "active": self.stats["active_endpoints"]
            },
            "requests": {
                "total": self.stats["total_requests"],
                "recent": len(self.request_logs)
            },
            "alerts": {
                "total": len(self.alerts),
                "active": len([a for a in self.alerts if not a.resolved]),
                "triggered": self.stats["alerts_triggered"],
                "resolved": self.stats["alerts_resolved"]
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭API监控器"""
        logger.info("Shutting down APIMonitor...")
        
        self._stop_monitor.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        self.endpoint_stats.clear()
        self.request_logs.clear()
        self.alerts.clear()
        self.last_alert_time.clear()
        
        logger.info("APIMonitor shutdown completed")

# 单例模式实现
_api_monitor_instance: Optional[APIMonitor] = None

def get_api_monitor(config: Optional[MonitorConfig] = None) -> APIMonitor:
    """
    获取API监控器单例
    
    Args:
        config: 监控器配置
    
    Returns:
        API监控器实例
    """
    global _api_monitor_instance
    if _api_monitor_instance is None:
        _api_monitor_instance = APIMonitor(config)
    return _api_monitor_instance

