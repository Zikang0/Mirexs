"""
推理指标 - 推理性能指标
收集、分析和报告推理系统的性能指标
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import statistics
import numpy as np
from collections import defaultdict, deque
import json

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型枚举"""
    PERFORMANCE = "performance"  # 性能指标
    ACCURACY = "accuracy"  # 准确率指标
    EFFICIENCY = "efficiency"  # 效率指标
    RELIABILITY = "reliability"  # 可靠性指标
    RESOURCE = "resource"  # 资源指标

class TimeWindow(Enum):
    """时间窗口枚举"""
    REAL_TIME = "real_time"  # 实时
    SHORT_TERM = "short_term"  # 短期
    MEDIUM_TERM = "medium_term"  # 中期
    LONG_TERM = "long_term"  # 长期

@dataclass
class MetricDataPoint:
    """指标数据点"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MetricSeries:
    """指标序列"""
    metric_id: str
    metric_type: MetricType
    data_points: List[MetricDataPoint]
    window_size: int = 1000  # 最大数据点数
    aggregation_interval: timedelta = timedelta(minutes=1)  # 聚合间隔

@dataclass
class PerformanceReport:
    """性能报告"""
    report_id: str
    time_period: Tuple[datetime, datetime]
    summary: Dict[str, float]
    detailed_metrics: Dict[str, MetricSeries]
    recommendations: List[str]
    anomalies: List[Dict[str, Any]]

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_id: str
    test_cases: int
    success_cases: int
    average_response_time: float
    throughput: float  # 每秒处理数
    resource_usage: Dict[str, float]
    comparison_to_baseline: Dict[str, float]  # 与基线比较

class ReasoningMetrics:
    """推理指标收集器"""
    
    def __init__(self, data_retention_days: int = 30):
        self.logger = logging.getLogger(__name__)
        self.data_retention_days = data_retention_days
        
        # 指标存储
        self.metrics: Dict[str, MetricSeries] = {}
        self.benchmark_results: Dict[str, BenchmarkResult] = {}
        self.performance_thresholds = self._initialize_thresholds()
        
        # 实时监控
        self.realtime_monitoring = False
        self.monitoring_thread = None
        
        # 初始化核心指标
        self._initialize_core_metrics()
        
        self.logger.info("推理指标系统初始化完成")
    
    def _initialize_thresholds(self) -> Dict[str, float]:
        """初始化性能阈值"""
        return {
            "response_time_warning": 1.0,  # 响应时间警告阈值（秒）
            "response_time_critical": 5.0,  # 响应时间严重阈值（秒）
            "cpu_usage_warning": 0.8,  # CPU使用率警告阈值
            "memory_usage_warning": 0.85,  # 内存使用率警告阈值
            "error_rate_warning": 0.05,  # 错误率警告阈值
            "success_rate_warning": 0.95  # 成功率警告阈值
        }
    
    def _initialize_core_metrics(self):
        """初始化核心指标"""
        core_metrics = {
            "response_time": MetricType.PERFORMANCE,
            "task_success_rate": MetricType.ACCURACY,
            "throughput": MetricType.EFFICIENCY,
            "error_rate": MetricType.RELIABILITY,
            "cpu_usage": MetricType.RESOURCE,
            "memory_usage": MetricType.RESOURCE,
            "reasoning_depth": MetricType.PERFORMANCE,
            "solution_quality": MetricType.ACCURACY
        }
        
        for metric_id, metric_type in core_metrics.items():
            self.metrics[metric_id] = MetricSeries(
                metric_id=metric_id,
                metric_type=metric_type,
                data_points=[],
                window_size=10000  # 较大的窗口用于历史分析
            )
    
    def record_metric(self, metric_id: str, value: float, 
                     metadata: Dict[str, Any] = None) -> bool:
        """
        记录指标
        
        Args:
            metric_id: 指标ID
            value: 指标值
            metadata: 元数据
            
        Returns:
            bool: 是否成功记录
        """
        if metric_id not in self.metrics:
            self.logger.warning(f"未知指标: {metric_id}，自动创建")
            self.metrics[metric_id] = MetricSeries(
                metric_id=metric_id,
                metric_type=MetricType.PERFORMANCE,  # 默认类型
                data_points=[]
            )
        
        data_point = MetricDataPoint(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata or {}
        )
        
        series = self.metrics[metric_id]
        series.data_points.append(data_point)
        
        # 维护窗口大小
        if len(series.data_points) > series.window_size:
            series.data_points = series.data_points[-series.window_size:]
        
        self.logger.debug(f"记录指标: {metric_id} = {value}")
        return True
    
    def record_response_time(self, task_type: str, response_time: float, 
                           success: bool = True) -> bool:
        """
        记录响应时间
        
        Args:
            task_type: 任务类型
            response_time: 响应时间（秒）
            success: 是否成功
            
        Returns:
            bool: 是否成功记录
        """
        # 记录通用响应时间
        self.record_metric("response_time", response_time, {
            "task_type": task_type,
            "success": success
        })
        
        # 记录特定任务类型的响应时间
        task_metric_id = f"response_time_{task_type}"
        self.record_metric(task_metric_id, response_time, {
            "success": success
        })
        
        # 记录成功率
        success_value = 1.0 if success else 0.0
        self.record_metric("task_success_rate", success_value, {
            "task_type": task_type
        })
        
        return True
    
    def record_resource_usage(self, cpu_usage: float, memory_usage: float, 
                            gpu_usage: float = None) -> bool:
        """
        记录资源使用情况
        
        Args:
            cpu_usage: CPU使用率 (0-1)
            memory_usage: 内存使用率 (0-1)
            gpu_usage: GPU使用率 (0-1)
            
        Returns:
            bool: 是否成功记录
        """
        self.record_metric("cpu_usage", cpu_usage)
        self.record_metric("memory_usage", memory_usage)
        
        if gpu_usage is not None:
            self.record_metric("gpu_usage", gpu_usage)
        
        return True
    
    def record_reasoning_quality(self, reasoning_depth: int, solution_quality: float,
                               complexity: str = "medium") -> bool:
        """
        记录推理质量
        
        Args:
            reasoning_depth: 推理深度
            solution_quality: 解决方案质量 (0-1)
            complexity: 问题复杂度
            
        Returns:
            bool: 是否成功记录
        """
        self.record_metric("reasoning_depth", reasoning_depth, {
            "complexity": complexity
        })
        self.record_metric("solution_quality", solution_quality, {
            "complexity": complexity
        })
        
        return True
    
    def get_metric_statistics(self, metric_id: str, 
                            time_window: TimeWindow = TimeWindow.SHORT_TERM) -> Dict[str, float]:
        """
        获取指标统计
        
        Args:
            metric_id: 指标ID
            time_window: 时间窗口
            
        Returns:
            Dict[str, float]: 统计信息
        """
        if metric_id not in self.metrics:
            return {}
        
        series = self.metrics[metric_id]
        if not series.data_points:
            return {}
        
        # 根据时间窗口过滤数据
        filtered_data = self._filter_data_by_window(series.data_points, time_window)
        if not filtered_data:
            return {}
        
        values = [point.value for point in filtered_data]
        
        return {
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "q1": np.percentile(values, 25) if len(values) >= 4 else values[0],
            "q3": np.percentile(values, 75) if len(values) >= 4 else values[-1]
        }
    
    def _filter_data_by_window(self, data_points: List[MetricDataPoint],
                             time_window: TimeWindow) -> List[MetricDataPoint]:
        """根据时间窗口过滤数据"""
        now = datetime.now()
        
        if time_window == TimeWindow.REAL_TIME:
            cutoff = now - timedelta(minutes=1)
        elif time_window == TimeWindow.SHORT_TERM:
            cutoff = now - timedelta(hours=1)
        elif time_window == TimeWindow.MEDIUM_TERM:
            cutoff = now - timedelta(days=1)
        elif time_window == TimeWindow.LONG_TERM:
            cutoff = now - timedelta(days=7)
        else:
            cutoff = now - timedelta(hours=1)  # 默认短期
        
        return [point for point in data_points if point.timestamp >= cutoff]
    
    def generate_performance_report(self, 
                                 start_time: datetime = None,
                                 end_time: datetime = None) -> PerformanceReport:
        """
        生成性能报告
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            PerformanceReport: 性能报告
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=24)  # 默认24小时
        if end_time is None:
            end_time = datetime.now()
        
        self.logger.info(f"生成性能报告: {start_time} 到 {end_time}")
        
        # 过滤时间范围内的数据
        filtered_metrics = {}
        for metric_id, series in self.metrics.items():
            filtered_points = [
                point for point in series.data_points
                if start_time <= point.timestamp <= end_time
            ]
            filtered_metrics[metric_id] = MetricSeries(
                metric_id=metric_id,
                metric_type=series.metric_type,
                data_points=filtered_points
            )
        
        # 计算摘要统计
        summary = self._calculate_summary_statistics(filtered_metrics)
        
        # 检测异常
        anomalies = self._detect_anomalies(filtered_metrics)
        
        # 生成建议
        recommendations = self._generate_recommendations(summary, anomalies)
        
        report = PerformanceReport(
            report_id=f"report_{int(time.time())}",
            time_period=(start_time, end_time),
            summary=summary,
            detailed_metrics=filtered_metrics,
            recommendations=recommendations,
            anomalies=anomalies
        )
        
        return report
    
    def _calculate_summary_statistics(self, metrics: Dict[str, MetricSeries]) -> Dict[str, float]:
        """计算摘要统计"""
        summary = {}
        
        # 核心指标统计
        core_metrics = ["response_time", "task_success_rate", "throughput", 
                       "error_rate", "cpu_usage", "memory_usage"]
        
        for metric_id in core_metrics:
            if metric_id in metrics and metrics[metric_id].data_points:
                values = [point.value for point in metrics[metric_id].data_points]
                summary[f"{metric_id}_avg"] = statistics.mean(values)
                summary[f"{metric_id}_p95"] = np.percentile(values, 95)
        
        # 计算整体成功率
        if "task_success_rate" in metrics and metrics["task_success_rate"].data_points:
            success_values = [point.value for point in metrics["task_success_rate"].data_points]
            summary["overall_success_rate"] = statistics.mean(success_values)
        
        # 计算平均响应时间
        if "response_time" in metrics and metrics["response_time"].data_points:
            response_times = [point.value for point in metrics["response_time"].data_points]
            summary["average_response_time"] = statistics.mean(response_times)
        
        return summary
    
    def _detect_anomalies(self, metrics: Dict[str, MetricSeries]) -> List[Dict[str, Any]]:
        """检测异常"""
        anomalies = []
        
        # 检查响应时间异常
        if "response_time" in metrics:
            response_stats = self.get_metric_statistics("response_time", TimeWindow.SHORT_TERM)
            if response_stats and response_stats["mean"] > self.performance_thresholds["response_time_warning"]:
                anomalies.append({
                    "metric": "response_time",
                    "severity": "warning" if response_stats["mean"] < self.performance_thresholds["response_time_critical"] else "critical",
                    "value": response_stats["mean"],
                    "threshold": self.performance_thresholds["response_time_warning"],
                    "description": "响应时间超过阈值"
                })
        
        # 检查错误率异常
        if "error_rate" in metrics:
            error_stats = self.get_metric_statistics("error_rate", TimeWindow.SHORT_TERM)
            if error_stats and error_stats["mean"] > self.performance_thresholds["error_rate_warning"]:
                anomalies.append({
                    "metric": "error_rate",
                    "severity": "warning",
                    "value": error_stats["mean"],
                    "threshold": self.performance_thresholds["error_rate_warning"],
                    "description": "错误率超过阈值"
                })
        
        # 检查资源使用异常
        for resource in ["cpu_usage", "memory_usage"]:
            if resource in metrics:
                resource_stats = self.get_metric_statistics(resource, TimeWindow.SHORT_TERM)
                threshold_key = f"{resource}_warning"
                if (resource_stats and threshold_key in self.performance_thresholds and
                    resource_stats["mean"] > self.performance_thresholds[threshold_key]):
                    anomalies.append({
                        "metric": resource,
                        "severity": "warning",
                        "value": resource_stats["mean"],
                        "threshold": self.performance_thresholds[threshold_key],
                        "description": f"{resource}超过阈值"
                    })
        
        return anomalies
    
    def _generate_recommendations(self, summary: Dict[str, float],
                               anomalies: List[Dict[str, Any]]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于异常生成建议
        for anomaly in anomalies:
            if anomaly["metric"] == "response_time":
                recommendations.append("优化推理算法以减少响应时间")
            elif anomaly["metric"] == "error_rate":
                recommendations.append("加强错误处理和恢复机制")
            elif anomaly["metric"] == "cpu_usage":
                recommendations.append("优化CPU密集型操作或增加计算资源")
            elif anomaly["metric"] == "memory_usage":
                recommendations.append("优化内存使用或增加内存资源")
        
        # 基于性能数据生成建议
        if "average_response_time" in summary and summary["average_response_time"] > 2.0:
            recommendations.append("考虑实现缓存机制提高响应速度")
        
        if "overall_success_rate" in summary and summary["overall_success_rate"] < 0.9:
            recommendations.append("改进推理逻辑提高任务成功率")
        
        # 如果没有问题，给出积极反馈
        if not recommendations and not anomalies:
            recommendations.append("系统性能良好，继续保持当前配置")
        
        return recommendations
    
    def run_benchmark(self, benchmark_id: str, test_cases: List[Dict[str, Any]]) -> BenchmarkResult:
        """
        运行基准测试
        
        Args:
            benchmark_id: 基准测试ID
            test_cases: 测试用例列表
            
        Returns:
            BenchmarkResult: 基准测试结果
        """
        self.logger.info(f"开始基准测试: {benchmark_id}, 测试用例数: {len(test_cases)}")
        
        start_time = time.time()
        success_count = 0
        response_times = []
        resource_usage = []
        
        for i, test_case in enumerate(test_cases):
            case_start = time.time()
            
            try:
                # 执行测试用例（这里需要具体的测试逻辑）
                success = self._execute_test_case(test_case)
                if success:
                    success_count += 1
                
                # 记录响应时间
                response_time = time.time() - case_start
                response_times.append(response_time)
                
                # 记录资源使用（简化）
                resource_usage.append({
                    "cpu": 0.5,  # 模拟数据
                    "memory": 0.6  # 模拟数据
                })
                
                self.logger.debug(f"测试用例 {i+1}/{len(test_cases)} 完成")
                
            except Exception as e:
                self.logger.error(f"测试用例 {i+1} 执行失败: {e}")
                response_times.append(time.time() - case_start)
        
        total_time = time.time() - start_time
        throughput = len(test_cases) / total_time if total_time > 0 else 0
        
        # 计算平均资源使用
        avg_cpu = statistics.mean([r["cpu"] for r in resource_usage]) if resource_usage else 0
        avg_memory = statistics.mean([r["memory"] for r in resource_usage]) if resource_usage else 0
        
        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            test_cases=len(test_cases),
            success_cases=success_count,
            average_response_time=statistics.mean(response_times) if response_times else 0,
            throughput=throughput,
            resource_usage={
                "cpu": avg_cpu,
                "memory": avg_memory
            },
            comparison_to_baseline=self._compare_to_baseline(benchmark_id, {
                "success_rate": success_count / len(test_cases),
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "throughput": throughput
            })
        )
        
        # 保存基准测试结果
        self.benchmark_results[benchmark_id] = result
        
        self.logger.info(f"基准测试完成: {benchmark_id}, 成功率: {success_count/len(test_cases):.2%}")
        return result
    
    def _execute_test_case(self, test_case: Dict[str, Any]) -> bool:
        """执行测试用例"""
        # 这里应该实现具体的测试逻辑
        # 目前返回模拟结果
        return True
    
    def _compare_to_baseline(self, benchmark_id: str, current_results: Dict[str, float]) -> Dict[str, float]:
        """与基线比较"""
        # 简化的比较逻辑
        # 在实际实现中应该加载基线数据
        baseline = {
            "success_rate": 0.95,
            "avg_response_time": 1.0,
            "throughput": 10.0
        }
        
        comparison = {}
        for key, current_value in current_results.items():
            if key in baseline:
                baseline_value = baseline[key]
                if baseline_value != 0:
                    comparison[key] = (current_value - baseline_value) / baseline_value
                else:
                    comparison[key] = 0.0
        
        return comparison
    
    def start_realtime_monitoring(self, interval_seconds: int = 5):
        """开始实时监控"""
        if self.realtime_monitoring:
            self.logger.warning("实时监控已在运行中")
            return
        
        self.realtime_monitoring = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        self.logger.info(f"实时监控已启动，间隔: {interval_seconds}秒")
    
    def stop_realtime_monitoring(self):
        """停止实时监控"""
        self.realtime_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("实时监控已停止")
    
    def _monitoring_loop(self, interval_seconds: int):
        """监控循环"""
        while self.realtime_monitoring:
            try:
                # 检查性能阈值
                self._check_performance_thresholds()
                
                # 记录系统状态
                self._record_system_status()
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(interval_seconds)
    
    def _check_performance_thresholds(self):
        """检查性能阈值"""
        # 获取当前性能指标
        response_stats = self.get_metric_statistics("response_time", TimeWindow.REAL_TIME)
        error_stats = self.get_metric_statistics("error_rate", TimeWindow.REAL_TIME)
        
        # 检查响应时间
        if (response_stats and 
            response_stats["mean"] > self.performance_thresholds["response_time_critical"]):
            self.logger.warning(f"响应时间严重超限: {response_stats['mean']:.2f}s")
        
        # 检查错误率
        if (error_stats and 
            error_stats["mean"] > self.performance_thresholds["error_rate_warning"]):
            self.logger.warning(f"错误率超限: {error_stats['mean']:.2%}")
    
    def _record_system_status(self):
        """记录系统状态"""
        # 这里应该获取真实的系统状态
        # 目前使用模拟数据
        import psutil
        import os
        
        cpu_usage = psutil.cpu_percent() / 100.0
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent / 100.0
        
        self.record_resource_usage(cpu_usage, memory_usage)
    
    def export_metrics(self, format: str = "json") -> str:
        """导出指标数据"""
        if format == "json":
            export_data = {
                "export_time": datetime.now().isoformat(),
                "metrics": {}
            }
            
            for metric_id, series in self.metrics.items():
                export_data["metrics"][metric_id] = {
                    "type": series.metric_type.value,
                    "data_points": [
                        {
                            "timestamp": point.timestamp.isoformat(),
                            "value": point.value,
                            "metadata": point.metadata
                        }
                        for point in series.data_points[-1000:]  # 只导出最近1000个点
                    ]
                }
            
            return json.dumps(export_data, indent=2, default=str)
        
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = datetime.now() - timedelta(days=self.data_retention_days)
        
        for metric_id, series in self.metrics.items():
            series.data_points = [
                point for point in series.data_points
                if point.timestamp >= cutoff_time
            ]
        
        self.logger.info("已完成旧数据清理")

import threading  # 添加threading导入

