"""
行为指标：行为系统性能指标
负责3D虚拟猫咪行为系统的性能监控、指标收集和分析
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json
import asyncio
from datetime import datetime, timedelta

class MetricType(Enum):
    """指标类型枚举"""
    PERFORMANCE = "performance"  # 性能指标
    BEHAVIORAL = "behavioral"  # 行为指标
    EMOTIONAL = "emotional"  # 情感指标
    SOCIAL = "social"  # 社交指标
    LEARNING = "learning"  # 学习指标

class MetricSeverity(Enum):
    """指标严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class BehaviorMetric:
    """行为指标"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: float
    severity: MetricSeverity
    description: str
    tags: List[str]

@dataclass
class MetricThreshold:
    """指标阈值"""
    metric_id: str
    warning_threshold: float
    critical_threshold: float
    min_value: float
    max_value: float

class BehaviorMetrics:
    """行为指标：行为系统性能指标"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 指标存储
        self.metrics_history: Dict[str, List[BehaviorMetric]] = {}
        self.metric_thresholds: Dict[str, MetricThreshold] = {}
        
        # 性能统计
        self.performance_stats: Dict[str, Any] = {
            "total_metrics_collected": 0,
            "alerts_triggered": 0,
            "system_uptime": 0.0
        }
        
        # 指标配置
        self.retention_period = 7 * 24 * 3600  # 保留7天数据
        self.sampling_interval = 60.0  # 采样间隔60秒
        self.last_sample_time = 0.0
        
        # 初始化指标系统
        self._initialize_metrics_system()
        
        self.logger.info("行为指标系统初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("BehaviorMetrics")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_metrics_system(self):
        """初始化指标系统"""
        # 定义指标阈值
        self._define_metric_thresholds()
        
        # 初始化指标历史存储
        for metric_type in MetricType:
            self.metrics_history[metric_type.value] = []
    
    def _define_metric_thresholds(self):
        """定义指标阈值"""
        # 性能指标阈值
        self.metric_thresholds["response_time"] = MetricThreshold(
            metric_id="response_time",
            warning_threshold=1.0,  # 1秒
            critical_threshold=3.0,  # 3秒
            min_value=0.0,
            max_value=10.0
        )
        
        self.metric_thresholds["memory_usage"] = MetricThreshold(
            metric_id="memory_usage",
            warning_threshold=0.8,  # 80%
            critical_threshold=0.9,  # 90%
            min_value=0.0,
            max_value=1.0
        )
        
        self.metric_thresholds["cpu_usage"] = MetricThreshold(
            metric_id="cpu_usage",
            warning_threshold=0.7,  # 70%
            critical_threshold=0.9,  # 90%
            min_value=0.0,
            max_value=1.0
        )
        
        # 行为指标阈值
        self.metric_thresholds["behavior_success_rate"] = MetricThreshold(
            metric_id="behavior_success_rate",
            warning_threshold=0.6,  # 60%
            critical_threshold=0.4,  # 40%
            min_value=0.0,
            max_value=1.0
        )
        
        self.metric_thresholds["plan_completion_rate"] = MetricThreshold(
            metric_id="plan_completion_rate",
            warning_threshold=0.7,  # 70%
            critical_threshold=0.5,  # 50%
            min_value=0.0,
            max_value=1.0
        )
        
        # 情感指标阈值
        self.metric_thresholds["emotional_stability"] = MetricThreshold(
            metric_id="emotional_stability",
            warning_threshold=0.3,  # 低稳定性
            critical_threshold=0.1,  # 极低稳定性
            min_value=0.0,
            max_value=1.0
        )
        
        # 学习指标阈值
        self.metric_thresholds["learning_efficiency"] = MetricThreshold(
            metric_id="learning_efficiency",
            warning_threshold=0.4,  # 40%
            critical_threshold=0.2,  # 20%
            min_value=0.0,
            max_value=1.0
        )
    
    async def record_metric(self, metric_id: str, value: float, metric_type: MetricType, 
                          description: str = "", tags: List[str] = None):
        """
        记录指标
        
        Args:
            metric_id: 指标ID
            value: 指标值
            metric_type: 指标类型
            description: 指标描述
            tags: 标签列表
        """
        try:
            current_time = time.time()
            
            # 确定严重程度
            severity = self._evaluate_metric_severity(metric_id, value)
            
            # 创建指标记录
            metric = BehaviorMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                timestamp=current_time,
                severity=severity,
                description=description,
                tags=tags or []
            )
            
            # 存储指标
            metric_key = metric_type.value
            if metric_key not in self.metrics_history:
                self.metrics_history[metric_key] = []
            
            self.metrics_history[metric_key].append(metric)
            
            # 更新统计
            self.performance_stats["total_metrics_collected"] += 1
            
            # 检查是否需要触发警报
            if severity in [MetricSeverity.HIGH, MetricSeverity.CRITICAL]:
                await self._trigger_metric_alert(metric)
            
            # 清理过期数据
            await self._cleanup_old_metrics()
            
            self.logger.debug(f"指标记录完成: {metric_id} = {value}")
            
        except Exception as e:
            self.logger.error(f"记录指标失败: {e}")
    
    def _evaluate_metric_severity(self, metric_id: str, value: float) -> MetricSeverity:
        """评估指标严重程度"""
        if metric_id not in self.metric_thresholds:
            return MetricSeverity.LOW
        
        threshold = self.metric_thresholds[metric_id]
        
        # 检查是否超过临界阈值
        if (threshold.critical_threshold is not None and 
            self._is_beyond_threshold(value, threshold.critical_threshold, threshold.min_value, threshold.max_value)):
            return MetricSeverity.CRITICAL
        
        # 检查是否超过警告阈值
        if (threshold.warning_threshold is not None and 
            self._is_beyond_threshold(value, threshold.warning_threshold, threshold.min_value, threshold.max_value)):
            return MetricSeverity.HIGH
        
        return MetricSeverity.LOW
    
    def _is_beyond_threshold(self, value: float, threshold: float, min_val: float, max_val: float) -> bool:
        """检查是否超过阈值"""
        # 确定阈值方向（越高越好还是越低越好）
        # 默认假设：值超过阈值表示问题
        midpoint = (min_val + max_val) / 2
        
        if threshold > midpoint:
            # 高值可能表示问题（如CPU使用率）
            return value > threshold
        else:
            # 低值可能表示问题（如成功率）
            return value < threshold
    
    async def _trigger_metric_alert(self, metric: BehaviorMetric):
        """触发指标警报"""
        alert_message = (
            f"指标警报: {metric.metric_id}\n"
            f"值: {metric.value}\n"
            f"严重程度: {metric.severity.value}\n"
            f"描述: {metric.description}\n"
            f"时间: {datetime.fromtimestamp(metric.timestamp)}"
        )
        
        self.logger.warning(alert_message)
        
        # 更新警报统计
        self.performance_stats["alerts_triggered"] += 1
        
        # 这里可以添加更多的警报处理逻辑，如发送通知、记录日志文件等
    
    async def _cleanup_old_metrics(self):
        """清理过期指标数据"""
        current_time = time.time()
        cutoff_time = current_time - self.retention_period
        
        for metric_type, metrics_list in self.metrics_history.items():
            # 移除过期指标
            self.metrics_history[metric_type] = [
                metric for metric in metrics_list
                if metric.timestamp >= cutoff_time
            ]
    
    async def record_performance_metric(self, operation: str, duration: float, success: bool = True):
        """
        记录性能指标
        
        Args:
            operation: 操作名称
            duration: 持续时间
            success: 是否成功
        """
        metric_id = f"perf_{operation}"
        metric_type = MetricType.PERFORMANCE
        
        description = f"{operation} 操作性能指标"
        tags = ["performance", operation]
        
        if not success:
            tags.append("failed")
        
        await self.record_metric(metric_id, duration, metric_type, description, tags)
    
    async def record_behavior_metric(self, behavior_type: str, success_rate: float, context: Dict[str, Any] = None):
        """
        记录行为指标
        
        Args:
            behavior_type: 行为类型
            success_rate: 成功率
            context: 上下文信息
        """
        metric_id = f"behavior_{behavior_type}_success_rate"
        metric_type = MetricType.BEHAVIORAL
        
        description = f"{behavior_type} 行为成功率"
        tags = ["behavior", behavior_type, "success_rate"]
        
        if context:
            tags.extend([f"ctx_{key}" for key in context.keys()])
        
        await self.record_metric(metric_id, success_rate, metric_type, description, tags)
    
    async def record_emotional_metric(self, emotion: str, intensity: float, stability: float):
        """
        记录情感指标
        
        Args:
            emotion: 情感类型
            intensity: 情感强度
            stability: 情感稳定性
        """
        # 记录情感强度
        intensity_metric_id = f"emotion_{emotion}_intensity"
        await self.record_metric(
            intensity_metric_id, intensity, MetricType.EMOTIONAL,
            f"{emotion} 情感强度", ["emotion", emotion, "intensity"]
        )
        
        # 记录情感稳定性
        stability_metric_id = f"emotion_{emotion}_stability"
        await self.record_metric(
            stability_metric_id, stability, MetricType.EMOTIONAL,
            f"{emotion} 情感稳定性", ["emotion", emotion, "stability"]
        )
    
    async def record_learning_metric(self, learning_type: str, efficiency: float, progress: float):
        """
        记录学习指标
        
        Args:
            learning_type: 学习类型
            efficiency: 学习效率
            progress: 学习进度
        """
        # 记录学习效率
        efficiency_metric_id = f"learning_{learning_type}_efficiency"
        await self.record_metric(
            efficiency_metric_id, efficiency, MetricType.LEARNING,
            f"{learning_type} 学习效率", ["learning", learning_type, "efficiency"]
        )
        
        # 记录学习进度
        progress_metric_id = f"learning_{learning_type}_progress"
        await self.record_metric(
            progress_metric_id, progress, MetricType.LEARNING,
            f"{learning_type} 学习进度", ["learning", learning_type, "progress"]
        )
    
    def get_metric_summary(self, metric_type: Optional[MetricType] = None, 
                          time_window: float = 3600) -> Dict[str, Any]:
        """
        获取指标摘要
        
        Args:
            metric_type: 指标类型，None表示所有类型
            time_window: 时间窗口（秒）
            
        Returns:
            指标摘要
        """
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        if metric_type:
            metric_types = [metric_type]
        else:
            metric_types = list(MetricType)
        
        summary = {}
        
        for mt in metric_types:
            metric_key = mt.value
            if metric_key not in self.metrics_history:
                continue
            
            # 过滤时间窗口内的指标
            recent_metrics = [
                metric for metric in self.metrics_history[metric_key]
                if metric.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                summary[metric_key] = {"count": 0, "message": "no_recent_data"}
                continue
            
            # 按指标ID分组
            metrics_by_id = {}
            for metric in recent_metrics:
                if metric.metric_id not in metrics_by_id:
                    metrics_by_id[metric.metric_id] = []
                metrics_by_id[metric.metric_id].append(metric)
            
            # 计算每个指标的统计
            type_summary = {}
            for metric_id, metrics in metrics_by_id.items():
                values = [metric.value for metric in metrics]
                severities = [metric.severity for metric in metrics]
                
                type_summary[metric_id] = {
                    "count": len(metrics),
                    "average": np.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "std_dev": np.std(values),
                    "latest_value": values[-1],
                    "critical_count": sum(1 for s in severities if s == MetricSeverity.CRITICAL),
                    "high_count": sum(1 for s in severities if s == MetricSeverity.HIGH)
                }
            
            summary[metric_key] = type_summary
        
        return summary
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """获取系统健康报告"""
        # 获取最近1小时的指标摘要
        recent_summary = self.get_metric_summary(time_window=3600)
        
        # 评估系统健康状态
        health_status = "healthy"
        critical_issues = 0
        warning_issues = 0
        
        for metric_type, metrics in recent_summary.items():
            if isinstance(metrics, dict) and "message" not in metrics:
                for metric_id, stats in metrics.items():
                    critical_issues += stats.get("critical_count", 0)
                    warning_issues += stats.get("high_count", 0)
        
        if critical_issues > 0:
            health_status = "critical"
        elif warning_issues > 3:
            health_status = "warning"
        elif warning_issues > 0:
            health_status = "degraded"
        
        return {
            "health_status": health_status,
            "timestamp": time.time(),
            "critical_issues": critical_issues,
            "warning_issues": warning_issues,
            "total_metrics_collected": self.performance_stats["total_metrics_collected"],
            "alerts_triggered": self.performance_stats["alerts_triggered"],
            "metrics_summary": recent_summary
        }
    
    def get_trend_analysis(self, metric_id: str, time_window: float = 24 * 3600) -> Dict[str, Any]:
        """
        获取趋势分析
        
        Args:
            metric_id: 指标ID
            time_window: 时间窗口（秒）
            
        Returns:
            趋势分析结果
        """
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        # 查找所有相关指标
        all_metrics = []
        for metric_list in self.metrics_history.values():
            for metric in metric_list:
                if metric.metric_id == metric_id and metric.timestamp >= cutoff_time:
                    all_metrics.append(metric)
        
        if not all_metrics:
            return {"status": "no_data", "metric_id": metric_id}
        
        # 按时间排序
        all_metrics.sort(key=lambda m: m.timestamp)
        
        # 提取数值和时间
        values = [metric.value for metric in all_metrics]
        timestamps = [metric.timestamp for metric in all_metrics]
        
        # 计算趋势
        if len(values) > 1:
            # 线性回归计算趋势
            x = np.array(timestamps) - timestamps[0]
            y = np.array(values)
            
            # 线性回归
            slope, intercept = np.polyfit(x, y, 1)
            trend_direction = "increasing" if slope > 0 else "decreasing"
            trend_strength = abs(slope) * 3600  # 每小时变化率
        else:
            trend_direction = "stable"
            trend_strength = 0.0
        
        return {
            "metric_id": metric_id,
            "data_points": len(values),
            "current_value": values[-1],
            "average_value": np.mean(values),
            "min_value": min(values),
            "max_value": max(values),
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "time_window": time_window
        }
    
    async def export_metrics(self, file_path: str, time_window: float = None):
        """
        导出指标数据
        
        Args:
            file_path: 文件路径
            time_window: 时间窗口（秒），None表示所有数据
        """
        try:
            export_data = {
                "export_timestamp": time.time(),
                "metrics_data": {}
            }
            
            current_time = time.time()
            cutoff_time = current_time - time_window if time_window else 0
            
            for metric_type, metrics_list in self.metrics_history.items():
                filtered_metrics = [
                    {
                        "metric_id": metric.metric_id,
                        "value": metric.value,
                        "timestamp": metric.timestamp,
                        "severity": metric.severity.value,
                        "description": metric.description,
                        "tags": metric.tags
                    }
                    for metric in metrics_list
                    if metric.timestamp >= cutoff_time
                ]
                
                export_data["metrics_data"][metric_type] = filtered_metrics
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"指标数据已导出到: {file_path}")
            
        except Exception as e:
            self.logger.error(f"导出指标数据失败: {e}")
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.performance_stats.copy()

# 全局行为指标实例
_global_behavior_metrics: Optional[BehaviorMetrics] = None

def get_behavior_metrics() -> BehaviorMetrics:
    """获取全局行为指标实例"""
    global _global_behavior_metrics
    if _global_behavior_metrics is None:
        _global_behavior_metrics = BehaviorMetrics()
    return _global_behavior_metrics
