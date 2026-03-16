"""
时序数据库：存储时间序列数据，如日志和监控指标
负责系统监控、性能指标等时间序列数据的存储和查询
"""

import time
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"          # 测量值
    HISTOGRAM = "histogram"  # 直方图
    SUMMARY = "summary"      # 摘要

@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    metric: str
    value: float
    timestamp: float
    labels: Dict[str, str]
    metric_type: MetricType

@dataclass
class QueryRange:
    """查询时间范围"""
    start_time: float
    end_time: float
    step: int = 60  # 步长(秒)

class TimeSeriesDatabase:
    """时序数据库"""
    
    def __init__(self, storage_path: str = "data/time_series"):
        self.storage_path = storage_path
        self.metrics: Dict[str, List[TimeSeriesPoint]] = {}
        self.retention_period = 7 * 24 * 3600  # 7天保留期
        self.cleanup_interval = 3600  # 清理间隔(秒)
        self.initialized = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化时序数据库"""
        if self.initialized:
            return
            
        logging.info("初始化时序数据库...")
        
        # 创建存储目录
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        # 加载现有数据
        await self._load_existing_data()
        
        # 启动清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        self.initialized = True
        logging.info("时序数据库初始化完成")
    
    async def _load_existing_data(self):
        """加载现有数据"""
        try:
            data_file = f"{self.storage_path}/timeseries_data.json"
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for metric_name, points_data in data.get('metrics', {}).items():
                    self.metrics[metric_name] = []
                    for point_data in points_data:
                        point = TimeSeriesPoint(
                            metric=point_data['metric'],
                            value=point_data['value'],
                            timestamp=point_data['timestamp'],
                            labels=point_data['labels'],
                            metric_type=MetricType(point_data['metric_type'])
                        )
                        self.metrics[metric_name].append(point)
                
                logging.info(f"加载了 {len(self.metrics)} 个指标的时序数据")
                
        except Exception as e:
            logging.error(f"加载时序数据失败: {e}")
    
    async def write_metric(self, metric: str, value: float, 
                         labels: Dict[str, str] = None,
                         metric_type: MetricType = MetricType.GAUGE) -> bool:
        """写入指标数据"""
        if labels is None:
            labels = {}
            
        point = TimeSeriesPoint(
            metric=metric,
            value=value,
            timestamp=time.time(),
            labels=labels,
            metric_type=metric_type
        )
        
        if metric not in self.metrics:
            self.metrics[metric] = []
        
        self.metrics[metric].append(point)
        logging.debug(f"写入指标: {metric} = {value}")
        
        return True
    
    async def query_range(self, metric: str, query_range: QueryRange) -> List[TimeSeriesPoint]:
        """范围查询"""
        if metric not in self.metrics:
            return []
        
        points = self.metrics[metric]
        result = []
        
        for point in points:
            if query_range.start_time <= point.timestamp <= query_range.end_time:
                result.append(point)
        
        # 按时间排序
        result.sort(key=lambda x: x.timestamp)
        
        return result
    
    async def query_latest(self, metric: str) -> Optional[TimeSeriesPoint]:
        """查询最新数据点"""
        if metric not in self.metrics or not self.metrics[metric]:
            return None
        
        points = self.metrics[metric]
        return max(points, key=lambda x: x.timestamp)
    
    async def query_aggregate(self, metric: str, query_range: QueryRange, 
                            aggregation: str = "avg") -> Dict[str, Any]:
        """聚合查询"""
        points = await self.query_range(metric, query_range)
        if not points:
            return {"value": 0, "count": 0}
        
        values = [point.value for point in points]
        
        if aggregation == "avg":
            result_value = sum(values) / len(values)
        elif aggregation == "sum":
            result_value = sum(values)
        elif aggregation == "max":
            result_value = max(values)
        elif aggregation == "min":
            result_value = min(values)
        else:
            result_value = sum(values) / len(values)  # 默认平均值
        
        return {
            "value": result_value,
            "count": len(points),
            "timestamp": time.time()
        }
    
    async def _cleanup_worker(self):
        """清理工作线程"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_old_data()
            except Exception as e:
                logging.error(f"清理工作线程错误: {e}")
    
    async def _cleanup_old_data(self):
        """清理旧数据"""
        current_time = time.time()
        cleanup_threshold = current_time - self.retention_period
        
        metrics_removed = 0
        
        for metric_name in list(self.metrics.keys()):
            original_count = len(self.metrics[metric_name])
            self.metrics[metric_name] = [
                point for point in self.metrics[metric_name]
                if point.timestamp >= cleanup_threshold
            ]
            removed_count = original_count - len(self.metrics[metric_name])
            metrics_removed += removed_count
            
            # 如果指标没有数据了，删除该指标
            if not self.metrics[metric_name]:
                del self.metrics[metric_name]
        
        if metrics_removed > 0:
            logging.info(f"清理了 {metrics_removed} 个过期的数据点")
    
    async def save(self):
        """保存数据到磁盘"""
        try:
            data = {
                'metrics': {}
            }
            
            for metric_name, points in self.metrics.items():
                data['metrics'][metric_name] = []
                for point in points:
                    data['metrics'][metric_name].append({
                        'metric': point.metric,
                        'value': point.value,
                        'timestamp': point.timestamp,
                        'labels': point.labels,
                        'metric_type': point.metric_type.value
                    })
            
            data_file = f"{self.storage_path}/timeseries_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logging.info("时序数据库数据已保存")
            
        except Exception as e:
            logging.error(f"保存时序数据失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        total_points = sum(len(points) for points in self.metrics.values())
        
        return {
            "total_metrics": len(self.metrics),
            "total_data_points": total_points,
            "metrics": {
                name: len(points) for name, points in self.metrics.items()
            }
        }

# 全局时序数据库实例
time_series_db = TimeSeriesDatabase()
