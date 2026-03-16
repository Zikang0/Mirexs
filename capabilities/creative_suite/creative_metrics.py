"""
创意指标：创意能力性能指标追踪和分析
支持生成质量、效率、多样性等多维度指标
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import statistics
import sqlite3
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """指标类型枚举"""
    GENERATION_QUALITY = "generation_quality"
    GENERATION_SPEED = "generation_speed"
    DIVERSITY = "diversity"
    USER_SATISFACTION = "user_satisfaction"
    USAGE_STATISTICS = "usage_statistics"
    ERROR_RATES = "error_rates"

class CreativeMetric(BaseModel):
    """创意指标"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any]

class PerformanceReport(BaseModel):
    """性能报告"""
    report_id: str
    period_start: datetime
    period_end: datetime
    metrics: Dict[MetricType, CreativeMetric]
    summary: Dict[str, Any]
    recommendations: List[str]

class CreativeMetrics:
    """创意指标追踪器"""
    
    def __init__(self, db_path: str = "creative_metrics.db"):
        self.db_path = db_path
        self._initialize_database()
        
        logger.info("CreativeMetrics initialized")
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建指标表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creative_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp DATETIME NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_metric_type 
                ON creative_metrics(metric_type)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON creative_metrics(timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Creative metrics database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize metrics database: {e}")
            raise
    
    def track_metric(self, 
                    metric_type: MetricType,
                    value: float,
                    metadata: Optional[Dict] = None) -> str:
        """
        追踪指标
        
        Args:
            metric_type: 指标类型
            value: 指标值
            metadata: 元数据
            
        Returns:
            str: 指标ID
        """
        try:
            metric_id = self._generate_metric_id()
            timestamp = datetime.now()
            
            metric = CreativeMetric(
                metric_id=metric_id,
                metric_type=metric_type,
                value=value,
                timestamp=timestamp,
                metadata=metadata or {}
            )
            
            self._save_metric_to_db(metric)
            
            logger.debug(f"Tracked metric {metric_type.value}: {value}")
            return metric_id
            
        except Exception as e:
            logger.error(f"Failed to track metric: {e}")
            raise
    
    def _generate_metric_id(self) -> str:
        """生成指标ID"""
        import hashlib
        unique_string = f"{datetime.now().isoformat()}_{hash(str(time.time()))}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def _save_metric_to_db(self, metric: CreativeMetric):
        """保存指标到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO creative_metrics 
                (metric_id, metric_type, value, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                metric.metric_id,
                metric.metric_type.value,
                metric.value,
                metric.timestamp.isoformat(),
                json.dumps(metric.metadata, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save metric to database: {e}")
            raise
    
    def get_metrics(self, 
                   metric_type: Optional[MetricType] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[CreativeMetric]:
        """获取指标数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM creative_metrics WHERE 1=1"
            params = []
            
            if metric_type:
                query += " AND metric_type = ?"
                params.append(metric_type.value)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            metrics = []
            for row in rows:
                metrics.append(CreativeMetric(
                    metric_id=row[0],
                    metric_type=MetricType(row[1]),
                    value=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    metadata=json.loads(row[4])
                ))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    def generate_performance_report(self, 
                                  period_hours: int = 24) -> PerformanceReport:
        """
        生成性能报告
        
        Args:
            period_hours: 报告周期（小时）
            
        Returns:
            PerformanceReport: 性能报告
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=period_hours)
            
            # 获取所有指标
            all_metrics = self.get_metrics(start_time=start_time, end_time=end_time)
            
            # 按类型分组
            metrics_by_type = {}
            for metric in all_metrics:
                if metric.metric_type not in metrics_by_type:
                    metrics_by_type[metric.metric_type] = []
                metrics_by_type[metric.metric_type].append(metric)
            
            # 计算各类型指标的统计信息
            report_metrics = {}
            summary = {
                "total_metrics": len(all_metrics),
                "period_start": start_time.isoformat(),
                "period_end": end_time.isoformat(),
                "metric_types_tracked": len(metrics_by_type)
            }
            
            for metric_type, metrics in metrics_by_type.items():
                values = [m.value for m in metrics]
                
                if values:
                    report_metrics[metric_type] = CreativeMetric(
                        metric_id="summary",
                        metric_type=metric_type,
                        value=statistics.mean(values),
                        timestamp=end_time,
                        metadata={
                            "count": len(values),
                            "min": min(values),
                            "max": max(values),
                            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
                        }
                    )
            
            # 生成建议
            recommendations = self._generate_recommendations(report_metrics)
            
            report = PerformanceReport(
                report_id=self._generate_report_id(),
                period_start=start_time,
                period_end=end_time,
                metrics=report_metrics,
                summary=summary,
                recommendations=recommendations
            )
            
            logger.info(f"Generated performance report for {period_hours} hours")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            raise
    
    def _generate_report_id(self) -> str:
        """生成报告ID"""
        import hashlib
        unique_string = f"report_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:8]
    
    def _generate_recommendations(self, metrics: Dict[MetricType, CreativeMetric]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于指标值生成建议
        for metric_type, metric in metrics.items():
            value = metric.value
            
            if metric_type == MetricType.GENERATION_QUALITY:
                if value < 0.6:
                    recommendations.append("内容生成质量较低，建议优化生成模型")
                elif value > 0.9:
                    recommendations.append("内容生成质量优秀，继续保持")
            
            elif metric_type == MetricType.GENERATION_SPEED:
                if value > 10.0:  # 假设10秒为阈值
                    recommendations.append("内容生成速度较慢，建议优化性能")
                elif value < 2.0:
                    recommendations.append("内容生成速度优秀")
            
            elif metric_type == MetricType.DIVERSITY:
                if value < 0.5:
                    recommendations.append("内容多样性不足，建议增加多样性")
                elif value > 0.8:
                    recommendations.append("内容多样性良好")
            
            elif metric_type == MetricType.USER_SATISFACTION:
                if value < 3.0:  # 假设5分制
                    recommendations.append("用户满意度较低，需要改进用户体验")
                elif value > 4.5:
                    recommendations.append("用户满意度优秀")
            
            elif metric_type == MetricType.ERROR_RATES:
                if value > 0.1:  # 10%错误率
                    recommendations.append("错误率较高，需要检查系统稳定性")
                elif value < 0.01:
                    recommendations.append("系统稳定性优秀")
        
        # 如果没有特定建议，提供一般性建议
        if not recommendations:
            recommendations.append("系统运行良好，继续保持当前配置")
        
        return recommendations
    
    def track_generation_quality(self, 
                               content_quality: float,
                               content_type: str,
                               model_used: str,
                               generation_time: float):
        """追踪生成质量"""
        metadata = {
            "content_type": content_type,
            "model_used": model_used,
            "generation_time": generation_time
        }
        
        return self.track_metric(
            metric_type=MetricType.GENERATION_QUALITY,
            value=content_quality,
            metadata=metadata
        )
    
    def track_generation_speed(self, 
                             generation_time: float,
                             content_length: int,
                             model_used: str):
        """追踪生成速度"""
        # 计算每秒生成的字数
        speed = content_length / generation_time if generation_time > 0 else 0
        
        metadata = {
            "generation_time_seconds": generation_time,
            "content_length": content_length,
            "model_used": model_used
        }
        
        return self.track_metric(
            metric_type=MetricType.GENERATION_SPEED,
            value=speed,
            metadata=metadata
        )
    
    def track_diversity(self, 
                       diversity_score: float,
                       content_type: str,
                       sample_size: int):
        """追踪多样性"""
        metadata = {
            "content_type": content_type,
            "sample_size": sample_size
        }
        
        return self.track_metric(
            metric_type=MetricType.DIVERSITY,
            value=diversity_score,
            metadata=metadata
        )
    
    def track_user_satisfaction(self, 
                              satisfaction_score: float,
                              user_id: str,
                              content_id: str):
        """追踪用户满意度"""
        metadata = {
            "user_id": user_id,
            "content_id": content_id
        }
        
        return self.track_metric(
            metric_type=MetricType.USER_SATISFACTION,
            value=satisfaction_score,
            metadata=metadata
        )
    
    def track_error_rate(self, 
                       error_count: int,
                       total_operations: int,
                       error_type: str):
        """追踪错误率"""
        error_rate = error_count / total_operations if total_operations > 0 else 0
        
        metadata = {
            "error_count": error_count,
            "total_operations": total_operations,
            "error_type": error_type
        }
        
        return self.track_metric(
            metric_type=MetricType.ERROR_RATES,
            value=error_rate,
            metadata=metadata
        )
    
    def get_system_health_score(self, period_hours: int = 24) -> float:
        """获取系统健康分数"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=period_hours)
            
            # 获取关键指标
            quality_metrics = self.get_metrics(
                MetricType.GENERATION_QUALITY, start_time, end_time
            )
            speed_metrics = self.get_metrics(
                MetricType.GENERATION_SPEED, start_time, end_time
            )
            error_metrics = self.get_metrics(
                MetricType.ERROR_RATES, start_time, end_time
            )
            satisfaction_metrics = self.get_metrics(
                MetricType.USER_SATISFACTION, start_time, end_time
            )
            
            # 计算各维度分数
            quality_score = statistics.mean([m.value for m in quality_metrics]) if quality_metrics else 0.5
            speed_score = min(1.0, statistics.mean([m.value for m in speed_metrics]) / 100) if speed_metrics else 0.5  # 假设100字/秒为满分
            error_score = 1.0 - (statistics.mean([m.value for m in error_metrics]) if error_metrics else 0.1)
            satisfaction_score = statistics.mean([m.value for m in satisfaction_metrics]) / 5.0 if satisfaction_metrics else 0.5  # 假设5分制
            
            # 加权计算总体健康分数
            weights = {
                "quality": 0.3,
                "speed": 0.25,
                "error": 0.25,
                "satisfaction": 0.2
            }
            
            health_score = (
                quality_score * weights["quality"] +
                speed_score * weights["speed"] +
                error_score * weights["error"] +
                satisfaction_score * weights["satisfaction"]
            )
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            logger.error(f"Failed to calculate system health score: {e}")
            return 0.5
    
    def export_metrics_data(self, 
                          output_path: str,
                          start_time: Optional[datetime] = None,
                          end_time: Optional[datetime] = None) -> bool:
        """导出指标数据"""
        try:
            metrics = self.get_metrics(start_time=start_time, end_time=end_time)
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "period": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                },
                "total_metrics": len(metrics),
                "metrics": [metric.dict() for metric in metrics]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Exported {len(metrics)} metrics to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics data: {e}")
            return False
    
    def cleanup_old_metrics(self, days_old: int = 30) -> int:
        """
        清理旧指标数据
        
        Args:
            days_old: 保留多少天内的数据
            
        Returns:
            int: 删除的记录数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM creative_metrics WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old metrics")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0

# 单例实例
_creative_metrics_instance = None

def get_creative_metrics() -> CreativeMetrics:
    """获取创意指标追踪器单例"""
    global _creative_metrics_instance
    if _creative_metrics_instance is None:
        _creative_metrics_instance = CreativeMetrics()
    return _creative_metrics_instance

