"""
异常检测器模块 - 提供时序数据异常检测功能
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

from .influxdb_integration import InfluxDBIntegration

class AnomalyType(Enum):
    """异常类型枚举"""
    SPIKES = "spikes"           # 尖峰异常
    DROPS = "drops"             # 跌落异常
    TREND_CHANGE = "trend_change"  # 趋势变化
    SEASONAL = "seasonal"       # 季节性异常
    CLUSTER = "cluster"         # 聚类异常

@dataclass
class AnomalyResult:
    """异常检测结果"""
    timestamp: datetime
    value: float
    anomaly_score: float
    anomaly_type: AnomalyType
    confidence: float
    description: str
    metadata: Dict[str, Any]

class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, influx_client: InfluxDBIntegration, config: Dict[str, Any]):
        """
        初始化异常检测器
        
        Args:
            influx_client: InfluxDB客户端
            config: 配置字典
        """
        self.influx_client = influx_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 异常检测配置
        self.anomaly_bucket = config.get('anomaly_bucket', 'mirexs_anomalies')
        self.default_threshold = config.get('default_threshold', 0.8)
        self.min_data_points = config.get('min_data_points', 10)
        
        # 机器学习模型
        self._isolation_forest = None
        self._dbscan = None
        self._scaler = StandardScaler()
        
        # 检测器状态
        self._trained_models = {}
    
    def detect_anomalies(self,
                        measurement: str,
                        field: str,
                        start_time: str = "-24h",
                        end_time: str = "now()",
                        tags: Optional[Dict[str, str]] = None,
                        method: str = "statistical") -> List[AnomalyResult]:
        """
        检测异常数据点
        
        Args:
            measurement: 测量名称
            field: 字段名称
            start_time: 开始时间
            end_time: 结束时间
            tags: 标签过滤
            method: 检测方法 (statistical, isolation_forest, dbscan)
            
        Returns:
            List: 异常检测结果列表
        """
        try:
            # 获取数据
            data = self._get_time_series_data(measurement, field, start_time, end_time, tags)
            
            if data is None or len(data) < self.min_data_points:
                self.logger.warning(f"Insufficient data for anomaly detection: {len(data) if data else 0} points")
                return []
            
            anomalies = []
            
            if method == "statistical":
                anomalies = self._detect_statistical_anomalies(data, measurement, field)
            elif method == "isolation_forest":
                anomalies = self._detect_isolation_forest_anomalies(data, measurement, field)
            elif method == "dbscan":
                anomalies = self._detect_dbscan_anomalies(data, measurement, field)
            else:
                self.logger.error(f"Unknown anomaly detection method: {method}")
                return []
            
            # 记录检测到的异常
            if anomalies:
                self._record_anomalies(anomalies, measurement, field)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {str(e)}")
            return []
    
    def _get_time_series_data(self,
                            measurement: str,
                            field: str,
                            start_time: str,
                            end_time: str,
                            tags: Optional[Dict[str, str]] = None) -> Optional[pd.DataFrame]:
        """
        获取时间序列数据
        
        Returns:
            DataFrame: 时间序列数据
        """
        try:
            query_parts = [
                f'from(bucket: "{self.influx_client.default_bucket}")',
                f'|> range(start: {start_time}, stop: {end_time})',
                f'|> filter(fn: (r) => r._measurement == "{measurement}")',
                f'|> filter(fn: (r) => r._field == "{field}")'
            ]
            
            if tags:
                for tag_key, tag_value in tags.items():
                    query_parts.append(f'|> filter(fn: (r) => r.{tag_key} == "{tag_value}")')
            
            query_parts.append('|> sort(columns: ["_time"])')
            
            query = '\n  '.join(query_parts)
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                # 确保数据按时间排序
                df = df.sort_values('_time')
                return df
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting time series data: {str(e)}")
            return None
    
    def _detect_statistical_anomalies(self, 
                                    data: pd.DataFrame,
                                    measurement: str,
                                    field: str) -> List[AnomalyResult]:
        """
        使用统计方法检测异常
        
        Returns:
            List: 异常检测结果
        """
        anomalies = []
        values = data['_value'].values
        
        if len(values) < 3:
            return anomalies
        
        # 计算移动平均值和标准差
        window_size = min(10, len(values) // 3)
        moving_avg = pd.Series(values).rolling(window=window_size, center=True).mean()
        moving_std = pd.Series(values).rolling(window=window_size, center=True).std()
        
        # 处理边界值
        moving_avg = moving_avg.fillna(method='bfill').fillna(method='ffill')
        moving_std = moving_std.fillna(method='bfill').fillna(method='ffill')
        
        # 检测异常
        for i, (idx, row) in enumerate(data.iterrows()):
            value = row['_value']
            timestamp = row['_time']
            
            if i >= window_size // 2 and i < len(values) - window_size // 2:
                avg = moving_avg.iloc[i]
                std = moving_std.iloc[i]
                
                if std > 0:  # 避免除零
                    z_score = abs(value - avg) / std
                    
                    if z_score > 2.5:  # 2.5个标准差
                        anomaly_type = AnomalyType.SPIKES if value > avg else AnomalyType.DROPS
                        confidence = min(z_score / 5.0, 1.0)  # 归一化到0-1
                        
                        anomaly = AnomalyResult(
                            timestamp=timestamp,
                            value=value,
                            anomaly_score=float(z_score),
                            anomaly_type=anomaly_type,
                            confidence=confidence,
                            description=f"Statistical anomaly detected (z-score: {z_score:.2f})",
                            metadata={
                                "method": "statistical",
                                "z_score": float(z_score),
                                "moving_avg": float(avg),
                                "moving_std": float(std)
                            }
                        )
                        anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_isolation_forest_anomalies(self,
                                         data: pd.DataFrame,
                                         measurement: str,
                                         field: str) -> List[AnomalyResult]:
        """
        使用孤立森林检测异常
        
        Returns:
            List: 异常检测结果
        """
        anomalies = []
        values = data['_value'].values.reshape(-1, 1)
        
        if len(values) < 10:
            return anomalies
        
        try:
            # 训练孤立森林模型
            contamination = min(0.1, 5.0 / len(values))  # 动态污染率
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            
            # 标准化数据
            values_scaled = self._scaler.fit_transform(values)
            
            # 预测异常
            predictions = iso_forest.fit_predict(values_scaled)
            scores = iso_forest.decision_function(values_scaled)
            
            for i, (idx, row) in enumerate(data.iterrows()):
                if predictions[i] == -1:  # 异常点
                    timestamp = row['_time']
                    value = row['_value']
                    
                    anomaly_score = -scores[i]  # 转换为正分数
                    confidence = min(anomaly_score * 2, 1.0)  # 粗略的置信度估计
                    
                    # 确定异常类型
                    avg_value = np.mean(values)
                    anomaly_type = AnomalyType.SPIKES if value > avg_value else AnomalyType.DROPS
                    
                    anomaly = AnomalyResult(
                        timestamp=timestamp,
                        value=value,
                        anomaly_score=float(anomaly_score),
                        anomaly_type=anomaly_type,
                        confidence=confidence,
                        description=f"Isolation Forest anomaly detected (score: {anomaly_score:.3f})",
                        metadata={
                            "method": "isolation_forest",
                            "contamination": contamination,
                            "avg_value": float(avg_value)
                        }
                    )
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error in isolation forest detection: {str(e)}")
            return []
    
    def _detect_dbscan_anomalies(self,
                                data: pd.DataFrame,
                                measurement: str,
                                field: str) -> List[AnomalyResult]:
        """
        使用DBSCAN检测异常
        
        Returns:
            List: 异常检测结果
        """
        anomalies = []
        values = data['_value'].values.reshape(-1, 1)
        
        if len(values) < 10:
            return anomalies
        
        try:
            # 使用DBSCAN聚类
            eps = np.std(values) * 0.5  # 动态epsilon
            dbscan = DBSCAN(eps=eps, min_samples=3)
            
            # 标准化数据
            values_scaled = self._scaler.fit_transform(values)
            
            # 聚类
            labels = dbscan.fit_predict(values_scaled)
            
            # 找出噪声点（标签为-1）
            for i, (idx, row) in enumerate(data.iterrows()):
                if labels[i] == -1:  # 噪声点（异常）
                    timestamp = row['_time']
                    value = row['_value']
                    
                    # 计算到最近簇的距离作为异常分数
                    cluster_centers = []
                    for label in set(labels):
                        if label != -1:
                            cluster_values = values_scaled[labels == label]
                            if len(cluster_values) > 0:
                                center = np.mean(cluster_values, axis=0)
                                cluster_centers.append(center)
                    
                    if cluster_centers:
                        distances = [np.linalg.norm(values_scaled[i] - center) for center in cluster_centers]
                        min_distance = min(distances) if distances else 1.0
                        anomaly_score = min_distance
                        confidence = min(anomaly_score, 1.0)
                        
                        avg_value = np.mean(values)
                        anomaly_type = AnomalyType.CLUSTER
                        
                        anomaly = AnomalyResult(
                            timestamp=timestamp,
                            value=value,
                            anomaly_score=float(anomaly_score),
                            anomaly_type=anomaly_type,
                            confidence=confidence,
                            description=f"DBSCAN cluster anomaly detected (distance: {anomaly_score:.3f})",
                            metadata={
                                "method": "dbscan",
                                "eps": float(eps),
                                "min_distance": float(min_distance)
                            }
                        )
                        anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error in DBSCAN detection: {str(e)}")
            return []
    
    def _record_anomalies(self, anomalies: List[AnomalyResult], measurement: str, field: str):
        """
        记录检测到的异常
        
        Args:
            anomalies: 异常列表
            measurement: 测量名称
            field: 字段名称
        """
        try:
            from influxdb_client import Point
            
            points = []
            
            for anomaly in anomalies:
                point = Point("detected_anomalies")
                
                # 添加标签
                point = point.tag("measurement", measurement)
                point = point.tag("field", field)
                point = point.tag("anomaly_type", anomaly.anomaly_type.value)
                
                # 添加字段
                point = point.field("value", anomaly.value)
                point = point.field("anomaly_score", anomaly.anomaly_score)
                point = point.field("confidence", anomaly.confidence)
                point = point.field("description", anomaly.description)
                
                # 添加元数据
                for key, value in anomaly.metadata.items():
                    if isinstance(value, (int, float)):
                        point = point.field(f"meta_{key}", value)
                    else:
                        point = point.field(f"meta_{key}", str(value))
                
                # 设置时间戳
                point = point.time(anomaly.timestamp)
                
                points.append(point)
            
            # 批量写入
            success = self.influx_client.batch_write_metrics(points, self.anomaly_bucket)
            
            if success:
                self.logger.info(f"Recorded {len(anomalies)} anomalies for {measurement}.{field}")
            else:
                self.logger.error(f"Failed to record anomalies for {measurement}.{field}")
                
        except Exception as e:
            self.logger.error(f"Error recording anomalies: {str(e)}")
    
    def detect_seasonal_anomalies(self,
                                measurement: str,
                                field: str,
                                seasonal_period: int = 24,  # 以小时为单位
                                start_time: str = "-7d",
                                end_time: str = "now()") -> List[AnomalyResult]:
        """
        检测季节性异常
        
        Args:
            measurement: 测量名称
            field: 字段名称
            seasonal_period: 季节性周期
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List: 季节性异常检测结果
        """
        try:
            data = self._get_time_series_data(measurement, field, start_time, end_time)
            
            if data is None or len(data) < seasonal_period * 2:
                self.logger.warning("Insufficient data for seasonal anomaly detection")
                return []
            
            anomalies = []
            values = data['_value'].values
            
            # 计算季节性基线
            seasonal_baseline = self._calculate_seasonal_baseline(values, seasonal_period)
            
            for i, (idx, row) in enumerate(data.iterrows()):
                if i >= len(seasonal_baseline):
                    continue
                
                value = row['_value']
                timestamp = row['_time']
                baseline = seasonal_baseline[i % seasonal_period]
                
                if baseline > 0:  # 避免除零
                    deviation = abs(value - baseline) / baseline
                    
                    if deviation > 0.3:  # 30%偏差
                        anomaly_score = min(deviation, 2.0) / 2.0  # 归一化到0-1
                        confidence = anomaly_score
                        
                        anomaly = AnomalyResult(
                            timestamp=timestamp,
                            value=value,
                            anomaly_score=float(anomaly_score),
                            anomaly_type=AnomalyType.SEASONAL,
                            confidence=confidence,
                            description=f"Seasonal anomaly detected (deviation: {deviation:.1%})",
                            metadata={
                                "method": "seasonal",
                                "deviation": float(deviation),
                                "baseline": float(baseline),
                                "seasonal_period": seasonal_period
                            }
                        )
                        anomalies.append(anomaly)
            
            # 记录检测到的异常
            if anomalies:
                self._record_anomalies(anomalies, measurement, field)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting seasonal anomalies: {str(e)}")
            return []
    
    def _calculate_seasonal_baseline(self, values: np.ndarray, period: int) -> np.ndarray:
        """
        计算季节性基线
        
        Args:
            values: 数值数组
            period: 周期长度
            
        Returns:
            ndarray: 季节性基线
        """
        # 简单的移动平均方法
        baseline = np.zeros(period)
        counts = np.zeros(period)
        
        for i, value in enumerate(values):
            idx = i % period
            baseline[idx] += value
            counts[idx] += 1
        
        # 计算平均值
        baseline = baseline / np.maximum(counts, 1)
        
        return baseline
    
    def get_anomaly_summary(self,
                          start_time: str = "-24h",
                          end_time: str = "now()") -> Optional[Dict[str, Any]]:
        """
        获取异常检测摘要
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 异常检测摘要
        """
        try:
            query = f'''
            from(bucket: "{self.anomaly_bucket}")
              |> range(start: {start_time}, stop: {end_time})
              |> filter(fn: (r) => r._measurement == "detected_anomalies")
            '''
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                summary = {
                    "time_range": f"{start_time} to {end_time}",
                    "total_anomalies": len(df),
                    "anomalies_by_type": {},
                    "anomalies_by_measurement": {},
                    "average_confidence": 0.0,
                    "high_confidence_anomalies": 0
                }
                
                # 按类型统计
                if 'anomaly_type' in df.columns:
                    type_counts = df['anomaly_type'].value_counts().to_dict()
                    summary["anomalies_by_type"] = type_counts
                
                # 按测量统计
                if 'measurement' in df.columns:
                    measurement_counts = df['measurement'].value_counts().to_dict()
                    summary["anomalies_by_measurement"] = measurement_counts
                
                # 计算平均置信度
                if 'confidence' in df.columns:
                    summary["average_confidence"] = float(df['confidence'].mean())
                    summary["high_confidence_anomalies"] = len(df[df['confidence'] > 0.8])
                
                return summary
            
            return {
                "time_range": f"{start_time} to {end_time}",
                "total_anomalies": 0,
                "message": "No anomalies detected"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting anomaly summary: {str(e)}")
            return None
    
    def create_anomaly_bucket(self) -> bool:
        """
        创建异常数据存储桶
        
        Returns:
            bool: 创建是否成功
        """
        return self.influx_client.create_bucket(
            self.anomaly_bucket,
            "Detected anomalies and anomaly detection results for Mirexs system"
        )

