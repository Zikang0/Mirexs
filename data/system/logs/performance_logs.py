"""
性能日志模块 - 记录性能指标
负责记录系统性能指标、响应时间、资源使用等
"""

import logging
import json
import time
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class PerformanceMetric(Enum):
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_QUERY = "database_query"
    MODEL_INFERENCE = "model_inference"

@dataclass
class PerformanceRecord:
    metric_type: PerformanceMetric
    component: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any]

class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, log_dir: str = "logs/performance"):
        self.log_dir = log_dir
        self.records: List[PerformanceRecord] = []
        self._setup_logging()
    
    def _setup_logging(self):
        """配置性能日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 性能日志记录器
        self.logger = logging.getLogger("performance")
        self.logger.setLevel(logging.INFO)
        
        # 性能日志文件处理器
        log_file = f"{self.log_dir}/performance.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        formatter = logging.Formatter(
            '%(asctime)s - PERFORMANCE - %(component)s - %(metric)s: %(value)s %(unit)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def log_metric(self, 
                  metric_type: PerformanceMetric,
                  component: str,
                  value: float,
                  unit: str,
                  metadata: Optional[Dict[str, Any]] = None):
        """记录性能指标"""
        
        record = PerformanceRecord(
            metric_type=metric_type,
            component=component,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.records.append(record)
        
        # 写入结构化日志
        self._write_performance_log(record)
        
        # 记录到文本日志
        log_message = f"{metric_type.value}: {value} {unit}"
        extra_info = {
            "component": component,
            "metric": metric_type.value,
            "value": value,
            "unit": unit
        }
        self.logger.info(log_message, extra=extra_info)
    
    def log_response_time(self, component: str, operation: str, response_time_ms: float):
        """记录响应时间"""
        metadata = {
            "operation": operation,
            "measurement_type": "response_time"
        }
        self.log_metric(
            PerformanceMetric.RESPONSE_TIME,
            component,
            response_time_ms,
            "ms",
            metadata
        )
    
    def log_throughput(self, component: str, operation: str, requests_per_second: float):
        """记录吞吐量"""
        metadata = {
            "operation": operation,
            "measurement_type": "throughput"
        }
        self.log_metric(
            PerformanceMetric.THROUGHPUT,
            component,
            requests_per_second,
            "req/s",
            metadata
        )
    
    def log_model_inference(self, model_name: str, inference_time_ms: float, input_size: Optional[int] = None):
        """记录模型推理性能"""
        metadata = {
            "model_name": model_name,
            "input_size": input_size
        }
        self.log_metric(
            PerformanceMetric.MODEL_INFERENCE,
            "ai_model",
            inference_time_ms,
            "ms",
            metadata
        )
    
    def log_system_resources(self):
        """记录系统资源使用情况"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.log_metric(
            PerformanceMetric.CPU_USAGE,
            "system",
            cpu_percent,
            "%"
        )
        
        # 内存使用
        memory = psutil.virtual_memory()
        self.log_metric(
            PerformanceMetric.MEMORY_USAGE,
            "system",
            memory.percent,
            "%",
            {"used_mb": memory.used // 1024 // 1024, "total_mb": memory.total // 1024 // 1024}
        )
        
        # 磁盘IO
        disk_io = psutil.disk_io_counters()
        if disk_io:
            self.log_metric(
                PerformanceMetric.DISK_IO,
                "system",
                disk_io.read_bytes + disk_io.write_bytes,
                "bytes",
                {"read_bytes": disk_io.read_bytes, "write_bytes": disk_io.write_bytes}
            )
        
        # 网络IO
        net_io = psutil.net_io_counters()
        if net_io:
            self.log_metric(
                PerformanceMetric.NETWORK_IO,
                "system",
                net_io.bytes_sent + net_io.bytes_recv,
                "bytes",
                {"sent_bytes": net_io.bytes_sent, "recv_bytes": net_io.bytes_recv}
            )
    
    def start_timer(self, component: str, operation: str) -> 'Timer':
        """开始计时器"""
        return Timer(self, component, operation)
    
    def _write_performance_log(self, record: PerformanceRecord):
        """写入性能日志文件"""
        import os
        log_file = f"{self.log_dir}/performance_metrics.jsonl"
        
        log_entry = {
            "timestamp": record.timestamp.isoformat(),
            "metric_type": record.metric_type.value,
            "component": record.component,
            "value": record.value,
            "unit": record.unit,
            "metadata": record.metadata
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def get_performance_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """获取性能摘要"""
        relevant_records = self.records
        if component:
            relevant_records = [r for r in self.records if r.component == component]
        
        if not relevant_records:
            return {}
        
        # 按指标类型分组
        metrics_by_type = {}
        for record in relevant_records:
            if record.metric_type not in metrics_by_type:
                metrics_by_type[record.metric_type] = []
            metrics_by_type[record.metric_type].append(record.value)
        
        summary = {}
        for metric_type, values in metrics_by_type.items():
            summary[metric_type.value] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1]
            }
        
        return summary
    
    def detect_performance_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """检测性能异常"""
        anomalies = []
        
        # 按组件和指标类型分组
        records_by_component_metric = {}
        for record in self.records:
            key = (record.component, record.metric_type)
            if key not in records_by_component_metric:
                records_by_component_metric[key] = []
            records_by_component_metric[key].append(record)
        
        for (component, metric_type), records in records_by_component_metric.items():
            if len(records) < 10:  # 需要足够的数据点
                continue
            
            values = [r.value for r in records]
            mean = sum(values) / len(values)
            std_dev = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
            
            # 检查最近的记录是否异常
            recent_record = records[-1]
            if abs(recent_record.value - mean) > threshold_std * std_dev:
                anomalies.append({
                    "component": component,
                    "metric_type": metric_type.value,
                    "value": recent_record.value,
                    "expected_range": [mean - std_dev, mean + std_dev],
                    "deviation": (recent_record.value - mean) / std_dev,
                    "timestamp": recent_record.timestamp.isoformat()
                })
        
        return anomalies

class Timer:
    """性能计时器"""
    
    def __init__(self, performance_logger: PerformanceLogger, component: str, operation: str):
        self.performance_logger = performance_logger
        self.component = component
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            response_time_ms = (time.time() - self.start_time) * 1000
            self.performance_logger.log_response_time(self.component, self.operation, response_time_ms)

# 全局性能日志实例
performance_logger = PerformanceLogger()

