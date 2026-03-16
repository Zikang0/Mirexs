"""
工具指标模块
收集和分析工具使用指标，提供性能监控和优化建议
"""

import time
import statistics
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型枚举"""
    EXECUTION_TIME = "execution_time"
    SUCCESS_RATE = "success_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    ERROR_RATE = "error_rate"
    USAGE_FREQUENCY = "usage_frequency"

@dataclass
class ToolMetric:
    """工具指标数据点"""
    tool_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_id": self.tool_id,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

@dataclass
class PerformanceStats:
    """性能统计"""
    tool_id: str
    metric_type: MetricType
    count: int
    average: float
    median: float
    min: float
    max: float
    standard_deviation: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_id": self.tool_id,
            "metric_type": self.metric_type.value,
            "count": self.count,
            "average": self.average,
            "median": self.median,
            "min": self.min,
            "max": self.max,
            "standard_deviation": self.standard_deviation,
            "timestamp": self.timestamp.isoformat()
        }

class ToolMetricsCollector:
    """工具指标收集器"""
    
    def __init__(self, storage_backend: Optional[Callable] = None):
        self.metrics: List[ToolMetric] = []
        self.storage_backend = storage_backend
        self._lock = asyncio.Lock()
    
    async def record_metric(self, tool_id: str, metric_type: MetricType, value: float, 
                          metadata: Dict[str, Any] = None):
        """记录指标"""
        async with self._lock:
            metric = ToolMetric(
                tool_id=tool_id,
                metric_type=metric_type,
                value=value,
                timestamp=datetime.now(),
                metadata=metadata
            )
            self.metrics.append(metric)
            
            # 如果有存储后端，保存指标
            if self.storage_backend:
                try:
                    await self.storage_backend(metric)
                except Exception as e:
                    logger.error(f"指标存储失败: {e}")
    
    async def record_execution_time(self, tool_id: str, execution_time: float, 
                                  success: bool = True, error_message: str = None):
        """记录执行时间"""
        metadata = {
            "success": success,
            "error_message": error_message
        }
        await self.record_metric(tool_id, MetricType.EXECUTION_TIME, execution_time, metadata)
        
        # 同时记录成功/失败
        success_value = 1.0 if success else 0.0
        await self.record_metric(tool_id, MetricType.SUCCESS_RATE, success_value, metadata)
    
    async def record_resource_usage(self, tool_id: str, memory_usage: float, cpu_usage: float):
        """记录资源使用情况"""
        await self.record_metric(tool_id, MetricType.MEMORY_USAGE, memory_usage)
        await self.record_metric(tool_id, MetricType.CPU_USAGE, cpu_usage)
    
    def get_metrics(self, tool_id: Optional[str] = None, 
                   metric_type: Optional[MetricType] = None,
                   time_range: Optional[timedelta] = None) -> List[ToolMetric]:
        """获取指标数据"""
        filtered_metrics = self.metrics
        
        # 按工具ID过滤
        if tool_id:
            filtered_metrics = [m for m in filtered_metrics if m.tool_id == tool_id]
        
        # 按指标类型过滤
        if metric_type:
            filtered_metrics = [m for m in filtered_metrics if m.metric_type == metric_type]
        
        # 按时间范围过滤
        if time_range:
            cutoff_time = datetime.now() - time_range
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= cutoff_time]
        
        return filtered_metrics
    
    async def calculate_performance_stats(self, tool_id: str, metric_type: MetricType,
                                       time_range: Optional[timedelta] = None) -> Optional[PerformanceStats]:
        """计算性能统计"""
        metrics = self.get_metrics(tool_id, metric_type, time_range)
        
        if not metrics:
            return None
        
        values = [metric.value for metric in metrics]
        
        return PerformanceStats(
            tool_id=tool_id,
            metric_type=metric_type,
            count=len(values),
            average=statistics.mean(values),
            median=statistics.median(values),
            min=min(values),
            max=max(values),
            standard_deviation=statistics.stdev(values) if len(values) > 1 else 0.0,
            timestamp=datetime.now()
        )
    
    async def get_tool_performance_report(self, tool_id: str, 
                                        time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """获取工具性能报告"""
        report = {
            "tool_id": tool_id,
            "generated_at": datetime.now().isoformat(),
            "time_range": str(time_range) if time_range else "all",
            "metrics": {}
        }
        
        # 计算各种指标的统计信息
        metric_types = [
            MetricType.EXECUTION_TIME,
            MetricType.SUCCESS_RATE,
            MetricType.MEMORY_USAGE,
            MetricType.CPU_USAGE
        ]
        
        for metric_type in metric_types:
            stats = await self.calculate_performance_stats(tool_id, metric_type, time_range)
            if stats:
                report["metrics"][metric_type.value] = stats.to_dict()
        
        # 计算使用频率
        usage_metrics = self.get_metrics(tool_id, time_range=time_range)
        usage_frequency = len(usage_metrics)
        report["metrics"]["usage_frequency"] = {
            "value": usage_frequency,
            "time_range": str(time_range) if time_range else "all"
        }
        
        return report
    
    async def detect_performance_issues(self, tool_id: str) -> List[Dict[str, Any]]:
        """检测性能问题"""
        issues = []
        
        # 获取执行时间统计
        exec_stats = await self.calculate_performance_stats(tool_id, MetricType.EXECUTION_TIME)
        if exec_stats and exec_stats.average > 10.0:  # 假设10秒为阈值
            issues.append({
                "type": "high_execution_time",
                "severity": "warning",
                "message": f"平均执行时间较高: {exec_stats.average:.2f}秒",
                "details": exec_stats.to_dict()
            })
        
        # 获取成功率统计
        success_stats = await self.calculate_performance_stats(tool_id, MetricType.SUCCESS_RATE)
        if success_stats and success_stats.average < 0.9:  # 成功率低于90%
            issues.append({
                "type": "low_success_rate",
                "severity": "error",
                "message": f"成功率较低: {success_stats.average * 100:.1f}%",
                "details": success_stats.to_dict()
            })
        
        # 获取内存使用统计
        memory_stats = await self.calculate_performance_stats(tool_id, MetricType.MEMORY_USAGE)
        if memory_stats and memory_stats.average > 500.0:  # 假设500MB为阈值
            issues.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"平均内存使用较高: {memory_stats.average:.2f}MB",
                "details": memory_stats.to_dict()
            })
        
        return issues
    
    async def export_metrics(self, file_path: str, 
                           tool_id: Optional[str] = None,
                           time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """导出指标数据"""
        try:
            metrics = self.get_metrics(tool_id, time_range=time_range)
            export_data = {
                "export_time": datetime.now().isoformat(),
                "metrics_count": len(metrics),
                "metrics": [metric.to_dict() for metric in metrics]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "file_path": file_path,
                "metrics_count": len(metrics),
                "message": f"指标数据已导出到 {file_path}"
            }
            
        except Exception as e:
            logger.error(f"指标导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_old_metrics(self, older_than: timedelta) -> int:
        """清理旧指标"""
        cutoff_time = datetime.now() - older_than
        initial_count = len(self.metrics)
        
        self.metrics = [metric for metric in self.metrics if metric.timestamp >= cutoff_time]
        
        removed_count = initial_count - len(self.metrics)
        logger.info(f"清理了 {removed_count} 个旧指标")
        return removed_count

class ToolOptimizationAdvisor:
    """工具优化顾问"""
    
    def __init__(self, metrics_collector: ToolMetricsCollector):
        self.collector = metrics_collector
    
    async def generate_optimization_recommendations(self, tool_id: str) -> Dict[str, Any]:
        """生成优化建议"""
        recommendations = []
        
        # 检测性能问题
        issues = await self.collector.detect_performance_issues(tool_id)
        
        for issue in issues:
            if issue["type"] == "high_execution_time":
                recommendations.append({
                    "type": "performance",
                    "priority": "high" if issue["severity"] == "error" else "medium",
                    "message": "优化执行时间",
                    "suggestions": [
                        "检查工具内部算法复杂度",
                        "考虑使用缓存机制",
                        "优化I/O操作",
                        "并行处理可能的任务"
                    ]
                })
            
            elif issue["type"] == "low_success_rate":
                recommendations.append({
                    "type": "reliability",
                    "priority": "high",
                    "message": "提高工具可靠性",
                    "suggestions": [
                        "增加错误处理和重试机制",
                        "改进输入验证",
                        "添加更详细的错误日志",
                        "检查依赖项稳定性"
                    ]
                })
            
            elif issue["type"] == "high_memory_usage":
                recommendations.append({
                    "type": "resource",
                    "priority": "medium",
                    "message": "减少内存使用",
                    "suggestions": [
                        "优化数据结构和算法",
                        "使用流式处理代替加载全部数据",
                        "及时释放不再使用的资源",
                        "考虑使用更高效的数据格式"
                    ]
                })
        
        # 如果没有检测到问题，提供一般性建议
        if not recommendations:
            recommendations.append({
                "type": "general",
                "priority": "low",
                "message": "工具性能良好",
                "suggestions": [
                    "定期监控性能指标",
                    "考虑添加新功能",
                    "优化用户体验"
                ]
            })
        
        return {
            "tool_id": tool_id,
            "generated_at": datetime.now().isoformat(),
            "recommendations": recommendations,
            "issues_detected": len(issues)
        }
    
    async def compare_tools_performance(self, tool_ids: List[str]) -> Dict[str, Any]:
        """比较多个工具的性能"""
        comparison = {
            "compared_tools": tool_ids,
            "comparison_time": datetime.now().isoformat(),
            "results": {}
        }
        
        for tool_id in tool_ids:
            tool_report = await self.collector.get_tool_performance_report(tool_id)
            comparison["results"][tool_id] = tool_report
        
        # 计算排名
        execution_times = []
        success_rates = []
        
        for tool_id in tool_ids:
            metrics = tool_report["metrics"]
            if "execution_time" in metrics:
                execution_times.append((tool_id, metrics["execution_time"]["average"]))
            if "success_rate" in metrics:
                success_rates.append((tool_id, metrics["success_rate"]["average"]))
        
        # 按执行时间排序（越低越好）
        execution_times.sort(key=lambda x: x[1])
        comparison["execution_time_ranking"] = [tool_id for tool_id, _ in execution_times]
        
        # 按成功率排序（越高越好）
        success_rates.sort(key=lambda x: x[1], reverse=True)
        comparison["success_rate_ranking"] = [tool_id for tool_id, _ in success_rates]
        
        return comparison

# 使用示例
async def demo_tool_metrics():
    """演示工具指标的使用"""
    collector = ToolMetricsCollector()
    advisor = ToolOptimizationAdvisor(collector)
    
    # 记录一些示例指标
    await collector.record_execution_time("tool_123", 2.5, True)
    await collector.record_execution_time("tool_123", 1.8, True)
    await collector.record_execution_time("tool_123", 15.2, False, "Timeout error")
    await collector.record_resource_usage("tool_123", 250.0, 15.0)
    
    # 获取性能报告
    report = await collector.get_tool_performance_report("tool_123")
    print("性能报告:", json.dumps(report, indent=2, ensure_ascii=False))
    
    # 检测性能问题
    issues = await collector.detect_performance_issues("tool_123")
    print("性能问题:", issues)
    
    # 获取优化建议
    recommendations = await advisor.generate_optimization_recommendations("tool_123")
    print("优化建议:", json.dumps(recommendations, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(demo_tool_metrics())

