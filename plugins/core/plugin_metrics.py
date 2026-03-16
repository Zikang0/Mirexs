"""
插件指标收集器

负责收集插件的性能指标、使用统计和健康监控数据。
提供指标存储、分析和报告功能。

Author: AI Assistant
Date: 2025-11-05
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"             # 仪表盘
    HISTOGRAM = "histogram"     # 直方图
    TIMER = "timer"             # 计时器


@dataclass
class MetricData:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginMetrics:
    """插件指标数据"""
    plugin_name: str
    load_time: float = 0.0
    activation_time: float = 0.0
    memory_usage: int = 0
    cpu_usage: float = 0.0
    request_count: int = 0
    error_count: int = 0
    success_count: int = 0
    response_times: List[float] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    health_status: str = "unknown"


class PluginMetricsCollector:
    """插件指标收集器"""
    
    def __init__(self, max_history_size: int = 1000):
        """
        初始化指标收集器
        
        Args:
            max_history_size: 最大历史记录数
        """
        self.logger = logging.getLogger(__name__)
        self._metrics: Dict[str, List[MetricData]] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._plugin_metrics: Dict[str, PluginMetrics] = {}
        self._active_timers: Dict[str, float] = {}
        self._metric_aggregators: Dict[str, Callable] = {}
        
        # 注册默认聚合器
        self._register_default_aggregators()
    
    def _register_default_aggregators(self) -> None:
        """注册默认聚合器"""
        self._metric_aggregators = {
            "sum": lambda values: sum(values),
            "avg": lambda values: sum(values) / len(values) if values else 0,
            "min": lambda values: min(values) if values else 0,
            "max": lambda values: max(values) if values else 0,
            "count": lambda values: len(values),
            "latest": lambda values: values[-1] if values else 0
        }
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE,
                     tags: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            metric_type: 指标类型
            tags: 标签
            metadata: 元数据
        """
        metric_data = MetricData(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self._metrics[name].append(metric_data)
        self.logger.debug(f"记录指标: {name} = {value}")
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """
        增加计数器
        
        Args:
            name: 计数器名称
            value: 增加的值
            tags: 标签
        """
        self.record_metric(name, value, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        设置仪表盘值
        
        Args:
            name: 仪表盘名称
            value: 值
            tags: 标签
        """
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def start_timer(self, name: str) -> None:
        """
        开始计时
        
        Args:
            name: 计时器名称
        """
        self._active_timers[name] = time.time()
        self.logger.debug(f"开始计时: {name}")
    
    def stop_timer(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """
        停止计时并记录
        
        Args:
            name: 计时器名称
            tags: 标签
            
        Returns:
            float: 耗时（秒）
        """
        if name not in self._active_timers:
            self.logger.warning(f"计时器未开始: {name}")
            return 0.0
        
        elapsed = time.time() - self._active_timers[name]
        del self._active_timers[name]
        
        self.record_metric(name, elapsed, MetricType.TIMER, tags)
        self.logger.debug(f"计时完成: {name} = {elapsed:.3f}s")
        return elapsed
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        记录直方图数据
        
        Args:
            name: 直方图名称
            value: 值
            tags: 标签
        """
        self.record_metric(name, value, MetricType.HISTOGRAM, tags)
    
    def update_plugin_metrics(self, plugin_name: str, metrics: PluginMetrics) -> None:
        """
        更新插件指标
        
        Args:
            plugin_name: 插件名称
            metrics: 插件指标数据
        """
        self._plugin_metrics[plugin_name] = metrics
        metrics.last_activity = datetime.now()
        
        # 记录关键指标
        self.increment_counter(f"{plugin_name}.requests", metrics.request_count)
        self.increment_counter(f"{plugin_name}.errors", metrics.error_count)
        self.increment_counter(f"{plugin_name}.success", metrics.success_count)
        self.set_gauge(f"{plugin_name}.memory_usage", metrics.memory_usage)
        self.set_gauge(f"{plugin_name}.cpu_usage", metrics.cpu_usage)
        
        # 记录响应时间
        for response_time in metrics.response_times:
            self.record_histogram(f"{plugin_name}.response_time", response_time)
    
    def get_metric_history(self, name: str, limit: int = 100) -> List[MetricData]:
        """
        获取指标历史
        
        Args:
            name: 指标名称
            limit: 返回记录数量限制
            
        Returns:
            List[MetricData]: 指标历史记录
        """
        history = list(self._metrics.get(name, []))
        return history[-limit:] if limit > 0 else history
    
    def get_aggregated_metric(self, name: str, aggregator: str = "avg", 
                            time_window: Optional[timedelta] = None) -> float:
        """
        获取聚合指标
        
        Args:
            name: 指标名称
            aggregator: 聚合函数名称
            time_window: 时间窗口
            
        Returns:
            float: 聚合结果
        """
        if aggregator not in self._metric_aggregators:
            self.logger.error(f"未知的聚合器: {aggregator}")
            return 0.0
        
        history = list(self._metrics.get(name, []))
        
        # 过滤时间窗口
        if time_window:
            cutoff_time = datetime.now() - time_window
            history = [m for m in history if m.timestamp >= cutoff_time]
        
        if not history:
            return 0.0
        
        values = [m.value for m in history]
        return self._metric_aggregators[aggregator](values)
    
    def get_plugin_health_score(self, plugin_name: str) -> float:
        """
        计算插件健康评分
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            float: 健康评分 (0-100)
        """
        if plugin_name not in self._plugin_metrics:
            return 0.0
        
        metrics = self._plugin_metrics[plugin_name]
        score = 100.0
        
        # 根据错误率扣分
        total_requests = metrics.error_count + metrics.success_count
        if total_requests > 0:
            error_rate = metrics.error_count / total_requests
            score -= error_rate * 30  # 最多扣30分
        
        # 根据CPU使用率扣分
        if metrics.cpu_usage > 80:
            score -= 20
        elif metrics.cpu_usage > 50:
            score -= 10
        
        # 根据内存使用扣分
        if metrics.memory_usage > 100 * 1024 * 1024:  # 100MB
            score -= 15
        elif metrics.memory_usage > 50 * 1024 * 1024:  # 50MB
            score -= 8
        
        # 根据响应时间扣分
        if metrics.response_times:
            avg_response_time = sum(metrics.response_times) / len(metrics.response_times)
            if avg_response_time > 5.0:  # 5秒
                score -= 25
            elif avg_response_time > 2.0:  # 2秒
                score -= 15
            elif avg_response_time > 1.0:  # 1秒
                score -= 5
        
        return max(0.0, score)
    
    def get_performance_summary(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Dict[str, Any]: 性能摘要
        """
        if plugin_name not in self._plugin_metrics:
            return {}
        
        metrics = self._plugin_metrics[plugin_name]
        
        # 计算响应时间统计
        response_stats = {}
        if metrics.response_times:
            response_stats = {
                "avg_response_time": sum(metrics.response_times) / len(metrics.response_times),
                "min_response_time": min(metrics.response_times),
                "max_response_time": max(metrics.response_times),
                "p95_response_time": self._calculate_percentile(metrics.response_times, 95),
                "p99_response_time": self._calculate_percentile(metrics.response_times, 99)
            }
        
        # 计算成功率
        total_requests = metrics.error_count + metrics.success_count
        success_rate = (metrics.success_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "plugin_name": plugin_name,
            "health_score": self.get_plugin_health_score(plugin_name),
            "total_requests": total_requests,
            "success_rate": success_rate,
            "error_count": metrics.error_count,
            "memory_usage_mb": metrics.memory_usage / (1024 * 1024),
            "cpu_usage_percent": metrics.cpu_usage,
            "load_time": metrics.load_time,
            "activation_time": metrics.activation_time,
            "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None,
            "response_time_stats": response_stats
        }
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """
        计算百分位数
        
        Args:
            values: 值列表
            percentile: 百分位数 (0-100)
            
        Returns:
            float: 百分位数值
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight
    
    def export_metrics(self, format: str = "json") -> str:
        """
        导出指标数据
        
        Args:
            format: 导出格式 ("json", "csv")
            
        Returns:
            str: 导出的数据
        """
        try:
            if format.lower() == "json":
                import json
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {name: [{"value": m.value, "timestamp": m.timestamp.isoformat(), 
                                       "tags": m.tags} for m in metrics] 
                              for name, metrics in self._metrics.items()},
                    "plugin_metrics": {name: {
                        "load_time": metrics.load_time,
                        "activation_time": metrics.activation_time,
                        "memory_usage": metrics.memory_usage,
                        "cpu_usage": metrics.cpu_usage,
                        "request_count": metrics.request_count,
                        "error_count": metrics.error_count,
                        "success_count": metrics.success_count,
                        "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None
                    } for name, metrics in self._plugin_metrics.items()}
                }
                return json.dumps(data, indent=2, ensure_ascii=False)
            
            elif format.lower() == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 写入头部
                writer.writerow(["metric_name", "value", "timestamp", "plugin_name", "tags"])
                
                # 写入指标数据
                for name, metrics_list in self._metrics.items():
                    for metric in metrics_list:
                        plugin_name = metric.tags.get("plugin_name", "")
                        tags_str = ";".join([f"{k}={v}" for k, v in metric.tags.items()])
                        writer.writerow([
                            name, metric.value, metric.timestamp.isoformat(), 
                            plugin_name, tags_str
                        ])
                
                return output.getvalue()
            
            else:
                raise ValueError(f"不支持的导出格式: {format}")
                
        except Exception as e:
            self.logger.error(f"指标导出失败: {str(e)}")
            return ""
    
    def cleanup_old_metrics(self, days: int = 7) -> int:
        """
        清理旧指标数据
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的记录数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for name, metrics_list in self._metrics.items():
            original_count = len(metrics_list)
            # 过滤掉过期的记录
            self._metrics[name] = deque(
                [m for m in metrics_list if m.timestamp >= cutoff_time],
                maxlen=metrics_list.maxlen
            )
            cleaned_count += original_count - len(self._metrics[name])
        
        self.logger.info(f"清理了 {cleaned_count} 条旧指标记录")
        return cleaned_count