"""
访问指标模块 - 收集和报告访问控制性能指标
"""

import logging
import time
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import threading

from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """指标数据点"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """指标定义"""
    name: str
    description: str
    unit: str  # ms, count, percent, etc.
    type: str  # counter, gauge, histogram


class AccessMetrics:
    """
    访问指标收集器
    收集和报告访问控制相关的性能指标
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化访问指标收集器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 指标存储
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, float] = {}  # 用于计时
        
        # 指标定义
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        
        # 标签
        self.labels: Dict[str, Dict[str, str]] = defaultdict(dict)
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/metrics"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        
        # 定义标准指标
        self._define_standard_metrics()
        
        # 上报任务
        self._report_task = None
        
        logger.info(f"访问指标收集器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/metrics",
            "report_interval_seconds": 60,
            "histogram_max_size": 1000,
            "enable_persistence": True,
            "enable_prometheus": False,
            "prometheus_port": 9090
        }
    
    def _define_standard_metrics(self):
        """定义标准指标"""
        standard_metrics = [
            MetricDefinition(
                name="auth_requests_total",
                description="Total number of authentication requests",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="auth_success_total",
                description="Total number of successful authentications",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="auth_failure_total",
                description="Total number of failed authentications",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="auth_duration_ms",
                description="Authentication duration in milliseconds",
                unit="ms",
                type="histogram"
            ),
            MetricDefinition(
                name="active_sessions",
                description="Number of active sessions",
                unit="count",
                type="gauge"
            ),
            MetricDefinition(
                name="permission_checks_total",
                description="Total number of permission checks",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="permission_checks_duration_ms",
                description="Permission check duration in milliseconds",
                unit="ms",
                type="histogram"
            ),
            MetricDefinition(
                name="policy_evaluations_total",
                description="Total number of policy evaluations",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="policy_evaluations_duration_ms",
                description="Policy evaluation duration in milliseconds",
                unit="ms",
                type="histogram"
            ),
            MetricDefinition(
                name="api_key_usage_total",
                description="Total number of API key usage",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="session_creations_total",
                description="Total number of session creations",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="session_revocations_total",
                description="Total number of session revocations",
                unit="count",
                type="counter"
            ),
            MetricDefinition(
                name="rate_limit_exceeded_total",
                description="Total number of rate limit exceeded events",
                unit="count",
                type="counter"
            )
        ]
        
        for metric in standard_metrics:
            self.metric_definitions[metric.name] = metric
    
    def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        增加计数器
        
        Args:
            name: 指标名称
            value: 增加的值
            labels: 标签
        """
        if name not in self.metric_definitions:
            logger.warning(f"未定义的指标: {name}")
        
        self.counters[name] += value
        
        if labels:
            label_key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            self.labels[label_key] = labels
        
        logger.debug(f"计数器 {name} 增加 {value}，当前值: {self.counters[name]}")
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        设置仪表盘值
        
        Args:
            name: 指标名称
            value: 值
            labels: 标签
        """
        if name not in self.metric_definitions:
            logger.warning(f"未定义的指标: {name}")
        
        self.gauges[name] = value
        
        if labels:
            label_key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            self.labels[label_key] = labels
        
        logger.debug(f"仪表盘 {name} 设置为 {value}")
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        观察直方图值
        
        Args:
            name: 指标名称
            value: 观察值
            labels: 标签
        """
        if name not in self.metric_definitions:
            logger.warning(f"未定义的指标: {name}")
        
        hist = self.histograms[name]
        hist.append(value)
        
        # 限制大小
        max_size = self.config["histogram_max_size"]
        if len(hist) > max_size:
            self.histograms[name] = hist[-max_size:]
        
        if labels:
            label_key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            self.labels[label_key] = labels
        
        logger.debug(f"直方图 {name} 添加值 {value}")
    
    def start_timer(self, name: str) -> str:
        """
        开始计时
        
        Args:
            name: 计时器名称
        
        Returns:
            计时器ID
        """
        timer_id = f"{name}_{time.time()}_{id(name)}"
        self.timers[timer_id] = time.time()
        return timer_id
    
    def stop_timer(
        self,
        timer_id: str,
        metric_name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """
        停止计时并记录
        
        Args:
            timer_id: 计时器ID
            metric_name: 指标名称
            labels: 标签
        
        Returns:
            持续时间（毫秒）
        """
        if timer_id not in self.timers:
            logger.warning(f"计时器 {timer_id} 不存在")
            return 0
        
        duration = (time.time() - self.timers[timer_id]) * 1000
        del self.timers[timer_id]
        
        self.observe_histogram(metric_name, duration, labels)
        
        return duration
    
    def record_auth_request(
        self,
        success: bool,
        method: str,
        duration_ms: float
    ):
        """
        记录认证请求
        
        Args:
            success: 是否成功
            method: 认证方法
            duration_ms: 持续时间
        """
        labels = {"method": method}
        
        self.increment_counter("auth_requests_total", labels=labels)
        
        if success:
            self.increment_counter("auth_success_total", labels=labels)
        else:
            self.increment_counter("auth_failure_total", labels=labels)
        
        self.observe_histogram("auth_duration_ms", duration_ms, labels)
    
    def record_permission_check(
        self,
        granted: bool,
        duration_ms: float
    ):
        """
        记录权限检查
        
        Args:
            granted: 是否授予
            duration_ms: 持续时间
        """
        labels = {"granted": str(granted).lower()}
        
        self.increment_counter("permission_checks_total", labels=labels)
        self.observe_histogram("permission_checks_duration_ms", duration_ms, labels)
    
    def record_policy_evaluation(
        self,
        policy_id: str,
        decision: str,
        duration_ms: float
    ):
        """
        记录策略评估
        
        Args:
            policy_id: 策略ID
            decision: 决策
            duration_ms: 持续时间
        """
        labels = {"policy_id": policy_id, "decision": decision}
        
        self.increment_counter("policy_evaluations_total", labels=labels)
        self.observe_histogram("policy_evaluations_duration_ms", duration_ms, labels)
    
    def record_session_creation(self, auth_method: str):
        """
        记录会话创建
        
        Args:
            auth_method: 认证方法
        """
        self.increment_counter("session_creations_total", labels={"auth_method": auth_method})
    
    def record_session_revocation(self, reason: str):
        """
        记录会话吊销
        
        Args:
            reason: 吊销原因
        """
        self.increment_counter("session_revocations_total", labels={"reason": reason})
    
    def record_api_key_usage(self, key_id: str):
        """
        记录API密钥使用
        
        Args:
            key_id: 密钥ID
        """
        self.increment_counter("api_key_usage_total", labels={"key_id": key_id[:8]})
    
    def record_rate_limit_exceeded(self, user_id: str, limit_type: str):
        """
        记录速率限制超限
        
        Args:
            user_id: 用户ID
            limit_type: 限制类型
        """
        self.increment_counter(
            "rate_limit_exceeded_total",
            labels={"user_id": user_id[:8], "type": limit_type}
        )
    
    def set_active_sessions(self, count: int):
        """设置活跃会话数"""
        self.set_gauge("active_sessions", count)
    
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """获取指标快照"""
        snapshot = {
            "timestamp": time.time(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {}
        }
        
        # 计算直方图统计
        for name, values in self.histograms.items():
            if values:
                snapshot["histograms"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": self._percentile(values, 50),
                    "p90": self._percentile(values, 90),
                    "p95": self._percentile(values, 95),
                    "p99": self._percentile(values, 99)
                }
            else:
                snapshot["histograms"][name] = {
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "p50": 0,
                    "p90": 0,
                    "p95": 0,
                    "p99": 0
                }
        
        return snapshot
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def save_snapshot(self):
        """保存指标快照"""
        try:
            snapshot = self.get_metrics_snapshot()
            
            filename = f"metrics_{int(time.time())}.json"
            filepath = self.storage_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"指标快照已保存: {filepath}")
            
            # 清理旧文件
            self._cleanup_old_snapshots()
            
        except Exception as e:
            logger.error(f"保存指标快照失败: {str(e)}")
    
    def _cleanup_old_snapshots(self, keep_days: int = 7):
        """清理旧快照"""
        try:
            cutoff_time = time.time() - (keep_days * 24 * 3600)
            
            for filepath in self.storage_path.glob("metrics_*.json"):
                if filepath.stat().st_mtime < cutoff_time:
                    filepath.unlink()
                    logger.debug(f"删除旧快照: {filepath}")
                    
        except Exception as e:
            logger.error(f"清理旧快照失败: {str(e)}")
    
    async def start_reporting(self):
        """启动定期上报"""
        if self._report_task:
            return
        
        async def _report_loop():
            interval = self.config["report_interval_seconds"]
            
            while True:
                try:
                    await asyncio.sleep(interval)
                    
                    # 保存快照
                    self.save_snapshot()
                    
                    # 如果启用Prometheus，更新指标
                    if self.config["enable_prometheus"]:
                        self._update_prometheus_metrics()
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"指标上报循环异常: {str(e)}")
        
        self._report_task = asyncio.create_task(_report_loop())
        logger.info(f"指标上报任务已启动，间隔 {self.config['report_interval_seconds']} 秒")
    
    async def stop_reporting(self):
        """停止定期上报"""
        if self._report_task:
            self._report_task.cancel()
            try:
                await self._report_task
            except asyncio.CancelledError:
                pass
            self._report_task = None
            logger.info("指标上报任务已停止")
    
    def _update_prometheus_metrics(self):
        """更新Prometheus指标"""
        # 这里可以实现Prometheus exporter
        pass
    
    def reset_counters(self):
        """重置计数器"""
        self.counters.clear()
        logger.info("所有计数器已重置")
    
    def reset_histograms(self):
        """重置直方图"""
        self.histograms.clear()
        logger.info("所有直方图已重置")


# 单例实例
_access_metrics_instance = None


def get_access_metrics() -> AccessMetrics:
    """获取访问指标收集器单例实例"""
    global _access_metrics_instance
    if _access_metrics_instance is None:
        _access_metrics_instance = AccessMetrics()
    return _access_metrics_instance

