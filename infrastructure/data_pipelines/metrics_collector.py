"""
指标收集器：收集系统运行指标
负责收集、聚合和报告系统运行时的各种性能指标和业务指标
"""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import statistics

class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"        # 计数器，只增不减
    GAUGE = "gauge"            # 测量值，可增可减
    HISTOGRAM = "histogram"    # 直方图，统计分布
    SUMMARY = "summary"        # 摘要，分位数统计
    RATE = "rate"              # 速率，单位时间内的变化

@dataclass
class MetricDefinition:
    """指标定义"""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = None
    buckets: List[float] = None  # 用于直方图的分桶

@dataclass
class MetricValue:
    """指标值"""
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = None

@dataclass
class MetricReport:
    """指标报告"""
    report_id: str
    timestamp: datetime
    time_range: timedelta
    metrics: Dict[str, Any]
    summary: Dict[str, Any]

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.metric_values: Dict[str, List[MetricValue]] = {}
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        self.report_history: List[MetricReport] = []
        self.initialized = False
        
    async def initialize(self):
        """初始化指标收集器"""
        if self.initialized:
            return
            
        logging.info("初始化指标收集器...")
        
        # 注册系统指标
        await self._register_system_metrics()
        
        self.initialized = True
        logging.info("指标收集器初始化完成")
    
    async def _register_system_metrics(self):
        """注册系统指标"""
        system_metrics = [
            MetricDefinition(
                name="cpu_usage",
                metric_type=MetricType.GAUGE,
                description="CPU使用率百分比",
                labels=["core"]
            ),
            MetricDefinition(
                name="memory_usage",
                metric_type=MetricType.GAUGE,
                description="内存使用量（字节）"
            ),
            MetricDefinition(
                name="disk_usage",
                metric_type=MetricType.GAUGE,
                description="磁盘使用量（字节）",
                labels=["partition"]
            ),
            MetricDefinition(
                name="network_bytes",
                metric_type=MetricType.COUNTER,
                description="网络字节数",
                labels=["interface", "direction"]  # sent, received
            ),
            MetricDefinition(
                name="process_count",
                metric_type=MetricType.GAUGE,
                description="系统进程数量"
            )
        ]
        
        for metric in system_metrics:
            await self.register_metric(metric)
    
    async def register_metric(self, metric_def: MetricDefinition) -> bool:
        """注册指标"""
        if metric_def.name in self.metric_definitions:
            logging.warning(f"指标已存在: {metric_def.name}")
            return False
        
        self.metric_definitions[metric_def.name] = metric_def
        self.metric_values[metric_def.name] = []
        
        logging.info(f"指标注册成功: {metric_def.name}")
        return True
    
    async def record_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """记录指标值"""
        if metric_name not in self.metric_definitions:
            logging.warning(f"未注册的指标: {metric_name}")
            return
        
        metric_value = MetricValue(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(),
            labels=labels
        )
        
        self.metric_values[metric_name].append(metric_value)
        
        # 限制历史记录大小
        if len(self.metric_values[metric_name]) > 10000:
            self.metric_values[metric_name] = self.metric_values[metric_name][-5000:]
        
        logging.debug(f"指标记录: {metric_name} = {value}")
    
    async def increment_counter(self, metric_name: str, increment: float = 1.0, labels: Dict[str, str] = None):
        """递增计数器"""
        await self.record_metric(metric_name, increment, labels)
    
    async def set_gauge(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """设置测量值"""
        await self.record_metric(metric_name, value, labels)
    
    async def observe_histogram(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """观察直方图值"""
        await self.record_metric(metric_name, value, labels)
    
    async def start_periodic_collection(self, metric_name: str, collection_func: Callable, interval: float = 60.0):
        """启动定期指标收集"""
        if metric_name in self.collection_tasks:
            logging.warning(f"指标收集任务已存在: {metric_name}")
            return
        
        async def collection_worker():
            while True:
                try:
                    value = await collection_func()
                    await self.record_metric(metric_name, value)
                except Exception as e:
                    logging.error(f"指标收集失败 {metric_name}: {e}")
                
                await asyncio.sleep(interval)
        
        task = asyncio.create_task(collection_worker())
        self.collection_tasks[metric_name] = task
        
        logging.info(f"启动定期指标收集: {metric_name}, 间隔: {interval}秒")
    
    async def stop_periodic_collection(self, metric_name: str):
        """停止定期指标收集"""
        if metric_name in self.collection_tasks:
            task = self.collection_tasks[metric_name]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.collection_tasks[metric_name]
            logging.info(f"停止指标收集: {metric_name}")
    
    async def collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_metric("cpu_usage", cpu_percent)
            
            # 每个核心的CPU使用率
            cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
            for i, core_usage in enumerate(cpu_percent_per_core):
                await self.record_metric("cpu_usage", core_usage, {"core": f"core_{i}"})
            
            # 内存使用
            memory = psutil.virtual_memory()
            await self.record_metric("memory_usage", memory.used)
            
            # 磁盘使用
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    await self.record_metric("disk_usage", usage.used, {"partition": partition.mountpoint})
                except PermissionError:
                    # 可能无法访问某些分区
                    pass
            
            # 网络统计
            net_io = psutil.net_io_counters()
            await self.record_metric("network_bytes", net_io.bytes_sent, {"direction": "sent"})
            await self.record_metric("network_bytes", net_io.bytes_recv, {"direction": "received"})
            
            # 进程数量
            process_count = len(psutil.pids())
            await self.record_metric("process_count", process_count)
            
        except Exception as e:
            logging.error(f"系统指标收集失败: {e}")
    
    async def generate_report(self, time_range: timedelta = None, report_id: str = None) -> MetricReport:
        """生成指标报告"""
        if time_range is None:
            time_range = timedelta(hours=1)
        
        if report_id is None:
            report_id = f"report_{int(datetime.now().timestamp())}"
        
        end_time = datetime.now()
        start_time = end_time - time_range
        
        try:
            report_metrics = {}
            summary = {
                "total_metrics": len(self.metric_definitions),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }
            
            for metric_name, metric_def in self.metric_definitions.items():
                # 获取时间范围内的指标值
                recent_values = [
                    mv for mv in self.metric_values.get(metric_name, [])
                    if start_time <= mv.timestamp <= end_time
                ]
                
                if not recent_values:
                    continue
                
                values = [mv.value for mv in recent_values]
                
                if metric_def.metric_type == MetricType.COUNTER:
                    # 计数器：计算总量和增长率
                    total = sum(values)
                    rate = total / time_range.total_seconds() if time_range.total_seconds() > 0 else 0
                    
                    report_metrics[metric_name] = {
                        "type": "counter",
                        "total": total,
                        "rate_per_second": rate,
                        "sample_count": len(values)
                    }
                
                elif metric_def.metric_type == MetricType.GAUGE:
                    # 测量值：统计当前值、平均值、最大值、最小值
                    current_value = values[-1] if values else 0
                    
                    report_metrics[metric_name] = {
                        "type": "gauge",
                        "current": current_value,
                        "average": statistics.mean(values) if values else 0,
                        "max": max(values) if values else 0,
                        "min": min(values) if values else 0,
                        "sample_count": len(values)
                    }
                
                elif metric_def.metric_type == MetricType.HISTOGRAM:
                    # 直方图：统计分布
                    if metric_def.buckets:
                        bucket_counts = {}
                        for bucket in metric_def.buckets:
                            count = sum(1 for v in values if v <= bucket)
                            bucket_counts[f"le_{bucket}"] = count
                        
                        report_metrics[metric_name] = {
                            "type": "histogram",
                            "buckets": bucket_counts,
                            "sample_count": len(values),
                            "sum": sum(values)
                        }
                
                elif metric_def.metric_type == MetricType.SUMMARY:
                    # 摘要：分位数统计
                    if len(values) >= 5:  # 需要足够的数据点
                        quantiles = {
                            "0.5": statistics.median(values),
                            "0.9": sorted(values)[int(len(values) * 0.9)],
                            "0.95": sorted(values)[int(len(values) * 0.95)],
                            "0.99": sorted(values)[int(len(values) * 0.99)]
                        }
                        
                        report_metrics[metric_name] = {
                            "type": "summary",
                            "quantiles": quantiles,
                            "sample_count": len(values),
                            "sum": sum(values)
                        }
            
            report = MetricReport(
                report_id=report_id,
                timestamp=end_time,
                time_range=time_range,
                metrics=report_metrics,
                summary=summary
            )
            
            self.report_history.append(report)
            
            # 限制历史报告数量
            if len(self.report_history) > 100:
                self.report_history.pop(0)
            
            logging.info(f"指标报告生成完成: {report_id}")
            return report
            
        except Exception as e:
            logging.error(f"指标报告生成失败: {e}")
            raise
    
    async def get_metric_values(self, metric_name: str, time_range: timedelta = None) -> List[MetricValue]:
        """获取指标值"""
        if metric_name not in self.metric_values:
            return []
        
        values = self.metric_values[metric_name]
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            values = [v for v in values if v.timestamp >= cutoff_time]
        
        return values
    
    async def calculate_correlation(self, metric1: str, metric2: str, time_range: timedelta = None) -> float:
        """计算两个指标的相关性"""
        values1 = await self.get_metric_values(metric1, time_range)
        values2 = await self.get_metric_values(metric2, time_range)
        
        if not values1 or not values2:
            return 0.0
        
        # 对齐时间戳（简化实现）
        # 在实际实现中，可能需要更复杂的时间对齐逻辑
        if len(values1) != len(values2):
            min_len = min(len(values1), len(values2))
            values1 = values1[:min_len]
            values2 = values2[:min_len]
        
        v1 = [mv.value for mv in values1]
        v2 = [mv.value for mv in values2]
        
        try:
            correlation = np.corrcoef(v1, v2)[0, 1]
            return float(correlation) if not np.isnan(correlation) else 0.0
        except:
            return 0.0
    
    async def detect_anomalies(self, metric_name: str, threshold: float = 2.0) -> List[Dict[str, Any]]:
        """检测指标异常"""
        values = await self.get_metric_values(metric_name, timedelta(hours=24))
        
        if len(values) < 10:
            return []
        
        value_list = [mv.value for mv in values]
        
        # 使用Z-score检测异常
        mean = statistics.mean(value_list)
        std = statistics.stdev(value_list) if len(value_list) > 1 else 0
        
        if std == 0:
            return []
        
        anomalies = []
        for i, value in enumerate(value_list):
            z_score = abs(value - mean) / std
            if z_score > threshold:
                anomalies.append({
                    "timestamp": values[i].timestamp,
                    "value": value,
                    "z_score": z_score,
                    "deviation": (value - mean) / mean * 100  # 百分比偏差
                })
        
        return anomalies
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """获取收集器统计"""
        total_metrics = len(self.metric_definitions)
        total_values = sum(len(values) for values in self.metric_values.values())
        active_collections = len(self.collection_tasks)
        
        metric_type_counts = {}
        for metric_def in self.metric_definitions.values():
            metric_type = metric_def.metric_type.value
            metric_type_counts[metric_type] = metric_type_counts.get(metric_type, 0) + 1
        
        return {
            "total_metrics_registered": total_metrics,
            "total_values_collected": total_values,
            "active_collection_tasks": active_collections,
            "metric_type_distribution": metric_type_counts,
            "total_reports_generated": len(self.report_history)
        }
    
    async def export_metrics(self, format: str = "prometheus") -> str:
        """导出指标（Prometheus格式）"""
        if format != "prometheus":
            raise ValueError("目前只支持Prometheus格式导出")
        
        lines = []
        
        for metric_name, metric_def in self.metric_definitions.items():
            recent_values = self.metric_values.get(metric_name, [])
            if not recent_values:
                continue
            
            # 获取最新值
            latest_value = recent_values[-1]
            
            # Prometheus格式: metric_name{label1="value1",...} value timestamp
            labels_str = ""
            if latest_value.labels:
                labels = [f'{k}="{v}"' for k, v in latest_value.labels.items()]
                labels_str = "{" + ",".join(labels) + "}"
            
            timestamp_ms = int(latest_value.timestamp.timestamp() * 1000)
            line = f"{metric_name}{labels_str} {latest_value.value} {timestamp_ms}"
            lines.append(line)
        
        return "\n".join(lines)

# 全局指标收集器实例
metrics_collector = MetricsCollector()