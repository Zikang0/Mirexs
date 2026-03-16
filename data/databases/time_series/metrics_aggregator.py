"""
指标聚合器模块 - 提供时序数据的聚合分析功能
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

from .influxdb_integration import InfluxDBIntegration

class AggregationType(Enum):
    """聚合类型枚举"""
    MEAN = "mean"
    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    STD = "std"
    PERCENTILE = "percentile"
    RATE = "rate"

@dataclass
class AggregationConfig:
    """聚合配置"""
    measurement: str
    fields: List[str]
    aggregation_type: AggregationType
    window: str = "1h"
    every: str = "1h"
    fill_value: Optional[float] = None
    tags: Optional[List[str]] = None

class MetricsAggregator:
    """指标聚合器"""
    
    def __init__(self, influx_client: InfluxDBIntegration, config: Dict[str, Any]):
        """
        初始化指标聚合器
        
        Args:
            influx_client: InfluxDB客户端
            config: 配置字典
        """
        self.influx_client = influx_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 聚合配置
        self.aggregation_bucket = config.get('aggregation_bucket', 'mirexs_aggregated')
        self.default_window = config.get('default_window', '1h')
        self.retention_policy = config.get('retention_policy', '52w')
        
        # 预定义的聚合配置
        self._aggregation_configs = {}
        self._setup_default_aggregations()
    
    def _setup_default_aggregations(self):
        """设置默认聚合配置"""
        # 系统性能聚合
        self._aggregation_configs['system_performance'] = AggregationConfig(
            measurement="performance_metrics",
            fields=["cpu_percent", "memory_percent", "disk_percent"],
            aggregation_type=AggregationType.MEAN,
            window="5m",
            every="5m"
        )
        
        # 用户交互聚合
        self._aggregation_configs['user_interactions'] = AggregationConfig(
            measurement="user_interactions",
            fields=["duration", "confidence"],
            aggregation_type=AggregationType.MEAN,
            window="1h",
            every="1h",
            tags=["interaction_type", "user_id"]
        )
        
        # 错误率聚合
        self._aggregation_configs['error_rates'] = AggregationConfig(
            measurement="system_logs",
            fields=["level"],
            aggregation_type=AggregationType.COUNT,
            window="1h",
            every="1h",
            tags=["component", "level"]
        )
    
    def register_aggregation(self, name: str, config: AggregationConfig):
        """
        注册聚合配置
        
        Args:
            name: 聚合名称
            config: 聚合配置
        """
        self._aggregation_configs[name] = config
        self.logger.info(f"Registered aggregation: {name}")
    
    def run_aggregation(self, aggregation_name: str, 
                       start_time: str = "-1h",
                       end_time: str = "now()") -> bool:
        """
        运行指定的聚合
        
        Args:
            aggregation_name: 聚合名称
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 聚合是否成功
        """
        if aggregation_name not in self._aggregation_configs:
            self.logger.error(f"Aggregation {aggregation_name} not found")
            return False
        
        config = self._aggregation_configs[aggregation_name]
        
        try:
            # 构建Flux查询
            query = self._build_aggregation_query(config, start_time, end_time)
            
            # 执行查询
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                # 将聚合结果写回数据库
                success = self._write_aggregation_results(df, aggregation_name, config)
                return success
            else:
                self.logger.warning(f"No data found for aggregation {aggregation_name}")
                return True  # 没有数据不算失败
                
        except Exception as e:
            self.logger.error(f"Error running aggregation {aggregation_name}: {str(e)}")
            return False
    
    def _build_aggregation_query(self, config: AggregationConfig, 
                                start_time: str, end_time: str) -> str:
        """
        构建聚合查询
        
        Args:
            config: 聚合配置
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            str: Flux查询语句
        """
        query_parts = [
            f'from(bucket: "{self.influx_client.default_bucket}")',
            f'|> range(start: {start_time}, stop: {end_time})',
            f'|> filter(fn: (r) => r._measurement == "{config.measurement}")'
        ]
        
        # 过滤字段
        if config.fields:
            field_filters = ' or '.join([f'r._field == "{field}"' for field in config.fields])
            query_parts.append(f'|> filter(fn: (r) => {field_filters})')
        
        # 按标签分组
        group_columns = ["_measurement", "_field"]
        if config.tags:
            group_columns.extend(config.tags)
        
        query_parts.append(f'|> group(columns: {group_columns})')
        
        # 时间窗口聚合
        query_parts.append(f'|> aggregateWindow(every: {config.every}, fn: {config.aggregation_type.value}')
        
        if config.fill_value is not None:
            query_parts.append(f', fill: {config.fill_value}')
        
        query_parts.append(')')
        
        return '\n  '.join(query_parts)
    
    def _write_aggregation_results(self, df: pd.DataFrame, 
                                 aggregation_name: str,
                                 config: AggregationConfig) -> bool:
        """
        写入聚合结果
        
        Args:
            df: 聚合结果数据框
            aggregation_name: 聚合名称
            config: 聚合配置
            
        Returns:
            bool: 写入是否成功
        """
        try:
            from influxdb_client import Point
            
            points = []
            
            for _, row in df.iterrows():
                point = Point(f"aggregated_{config.measurement}")
                
                # 添加标签
                point = point.tag("aggregation_name", aggregation_name)
                point = point.tag("aggregation_type", config.aggregation_type.value)
                point = point.tag("window", config.window)
                
                # 添加原始标签
                for col in row.index:
                    if col.startswith('_') and col not in ['_time', '_value', '_field', '_measurement']:
                        point = point.tag(col[1:], str(row[col]))
                
                # 添加字段
                field_name = row.get('_field', 'value')
                point = point.field(field_name, float(row['_value']))
                
                # 设置时间戳
                point = point.time(row['_time'])
                
                points.append(point)
            
            # 批量写入
            success = self.influx_client.batch_write_metrics(points, self.aggregation_bucket)
            
            if success:
                self.logger.info(f"Successfully wrote {len(points)} aggregated points for {aggregation_name}")
            else:
                self.logger.error(f"Failed to write aggregated points for {aggregation_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error writing aggregation results: {str(e)}")
            return False
    
    def run_all_aggregations(self, start_time: str = "-1h", end_time: str = "now()") -> Dict[str, bool]:
        """
        运行所有注册的聚合
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 聚合名称到成功状态的映射
        """
        results = {}
        
        for aggregation_name in self._aggregation_configs:
            success = self.run_aggregation(aggregation_name, start_time, end_time)
            results[aggregation_name] = success
        
        return results
    
    def calculate_statistics(self,
                           measurement: str,
                           field: str,
                           start_time: str = "-24h",
                           end_time: str = "now()",
                           tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        计算指标的统计信息
        
        Args:
            measurement: 测量名称
            field: 字段名称
            start_time: 开始时间
            end_time: 结束时间
            tags: 标签过滤
            
        Returns:
            Dict: 统计信息
        """
        try:
            # 构建查询
            query_parts = [
                f'from(bucket: "{self.influx_client.default_bucket}")',
                f'|> range(start: {start_time}, stop: {end_time})',
                f'|> filter(fn: (r) => r._measurement == "{measurement}")',
                f'|> filter(fn: (r) => r._field == "{field}")'
            ]
            
            if tags:
                for tag_key, tag_value in tags.items():
                    query_parts.append(f'|> filter(fn: (r) => r.{tag_key} == "{tag_value}")')
            
            query = '\n  '.join(query_parts)
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                values = df['_value'].dropna()
                
                if len(values) > 0:
                    stats = {
                        "measurement": measurement,
                        "field": field,
                        "time_range": f"{start_time} to {end_time}",
                        "count": len(values),
                        "mean": float(values.mean()),
                        "median": float(values.median()),
                        "std": float(values.std()),
                        "min": float(values.min()),
                        "max": float(values.max()),
                        "q1": float(values.quantile(0.25)),
                        "q3": float(values.quantile(0.75))
                    }
                    
                    return stats
            
            return {
                "measurement": measurement,
                "field": field,
                "message": "No data found",
                "count": 0
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating statistics: {str(e)}")
            return None
    
    def detect_trends(self,
                     measurement: str,
                     field: str,
                     start_time: str = "-7d",
                     end_time: str = "now()",
                     window: str = "1h") -> Optional[Dict[str, Any]]:
        """
        检测数据趋势
        
        Args:
            measurement: 测量名称
            field: 字段名称
            start_time: 开始时间
            end_time: 结束时间
            window: 时间窗口
            
        Returns:
            Dict: 趋势分析结果
        """
        try:
            query = f'''
            from(bucket: "{self.influx_client.default_bucket}")
              |> range(start: {start_time}, stop: {end_time})
              |> filter(fn: (r) => r._measurement == "{measurement}")
              |> filter(fn: (r) => r._field == "{field}")
              |> aggregateWindow(every: {window}, fn: mean)
            '''
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and len(df) >= 2:
                values = df['_value'].dropna().values
                times = pd.to_datetime(df['_time']).values
                
                if len(values) >= 2:
                    # 计算线性趋势
                    x = np.arange(len(values))
                    slope, intercept = np.polyfit(x, values, 1)
                    
                    # 计算变化率
                    first_value = values[0]
                    last_value = values[-1]
                    change_rate = (last_value - first_value) / first_value if first_value != 0 else 0
                    
                    # 检测异常点（使用Z-score）
                    z_scores = np.abs((values - np.mean(values)) / np.std(values))
                    anomalies = np.where(z_scores > 2)[0]
                    
                    trend = {
                        "measurement": measurement,
                        "field": field,
                        "window": window,
                        "data_points": len(values),
                        "slope": float(slope),
                        "intercept": float(intercept),
                        "change_rate": float(change_rate),
                        "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                        "anomaly_count": len(anomalies),
                        "average_value": float(np.mean(values)),
                        "volatility": float(np.std(values))
                    }
                    
                    return trend
            
            return {
                "measurement": measurement,
                "field": field,
                "message": "Insufficient data for trend analysis",
                "data_points": len(df) if df is not None else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting trends: {str(e)}")
            return None
    
    def compare_periods(self,
                       measurement: str,
                       field: str,
                       current_period: Tuple[str, str],
                       previous_period: Tuple[str, str],
                       tags: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        比较两个时间段的指标
        
        Args:
            measurement: 测量名称
            field: 字段名称
            current_period: 当前时间段 (start, end)
            previous_period: 之前时间段 (start, end)
            tags: 标签过滤
            
        Returns:
            Dict: 比较结果
        """
        try:
            current_stats = self.calculate_statistics(
                measurement, field, current_period[0], current_period[1], tags
            )
            previous_stats = self.calculate_statistics(
                measurement, field, previous_period[0], previous_period[1], tags
            )
            
            if current_stats and previous_stats and current_stats['count'] > 0 and previous_stats['count'] > 0:
                comparison = {
                    "measurement": measurement,
                    "field": field,
                    "current_period": {
                        "range": f"{current_period[0]} to {current_period[1]}",
                        "stats": current_stats
                    },
                    "previous_period": {
                        "range": f"{previous_period[0]} to {previous_period[1]}",
                        "stats": previous_stats
                    },
                    "comparison": {}
                }
                
                # 计算变化
                for stat in ['mean', 'median', 'min', 'max']:
                    if stat in current_stats and stat in previous_stats:
                        current_val = current_stats[stat]
                        previous_val = previous_stats[stat]
                        
                        if previous_val != 0:
                            change = (current_val - previous_val) / previous_val
                            comparison["comparison"][f"{stat}_change"] = float(change)
                        else:
                            comparison["comparison"][f"{stat}_change"] = float('inf')
                
                return comparison
            
            return {
                "measurement": measurement,
                "field": field,
                "message": "Insufficient data for comparison"
            }
            
        except Exception as e:
            self.logger.error(f"Error comparing periods: {str(e)}")
            return None
    
    def create_aggregation_bucket(self) -> bool:
        """
        创建聚合数据存储桶
        
        Returns:
            bool: 创建是否成功
        """
        return self.influx_client.create_bucket(
            self.aggregation_bucket,
            "Aggregated metrics and statistics for Mirexs system"
        )

