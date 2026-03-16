"""
时序数据库模块 - 提供系统日志、性能指标、用户交互数据的存储和分析功能

模块组成:
- influxdb_integration: InfluxDB数据库集成
- system_logs: 系统日志管理
- performance_metrics: 性能指标收集
- user_interactions: 用户交互管理  
- metrics_aggregator: 指标聚合分析
- anomaly_detector: 异常检测
"""

from .influxdb_integration import InfluxDBIntegration
from .system_logs import SystemLogs, LogLevel
from .performance_metrics import PerformanceMetrics
from .user_interactions import UserInteractions, InteractionType
from .metrics_aggregator import MetricsAggregator, AggregationType, AggregationConfig
from .anomaly_detector import AnomalyDetector, AnomalyType, AnomalyResult

__all__ = [
    # 主要类
    'InfluxDBIntegration',
    'SystemLogs', 
    'PerformanceMetrics',
    'UserInteractions',
    'MetricsAggregator',
    'AnomalyDetector',
    
    # 枚举类型
    'LogLevel',
    'InteractionType', 
    'AggregationType',
    'AnomalyType',
    
    # 数据类
    'AggregationConfig',
    'AnomalyResult'
]

__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "时序数据库模块 - 提供完整的时间序列数据存储、分析和监控功能"
