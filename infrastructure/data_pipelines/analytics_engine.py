"""
分析引擎：数据分析功能
负责数据的统计分析、模式识别、趋势分析等分析任务
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
from scipy import stats
import statistics

class AnalysisType(Enum):
    """分析类型枚举"""
    DESCRIPTIVE_STATS = "descriptive_stats"
    TREND_ANALYSIS = "trend_analysis"
    CORRELATION_ANALYSIS = "correlation_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    ANOMALY_DETECTION = "anomaly_detection"
    CLUSTERING_ANALYSIS = "clustering_analysis"
    PREDICTIVE_ANALYSIS = "predictive_analysis"

@dataclass
class AnalysisResult:
    """分析结果"""
    analysis_id: str
    analysis_type: AnalysisType
    data_source: str
    timestamp: datetime
    results: Dict[str, Any]
    insights: List[str]
    execution_time: float

@dataclass
class AnalysisConfig:
    """分析配置"""
    analysis_type: AnalysisType
    target_columns: List[str]
    parameters: Dict[str, Any] = None
    time_column: str = None
    group_by: List[str] = None

class AnalyticsEngine:
    """分析引擎"""
    
    def __init__(self):
        self.analysis_history: List[AnalysisResult] = []
        self.model_registry: Dict[str, Any] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化分析引擎"""
        if self.initialized:
            return
            
        logging.info("初始化分析引擎...")
        
        # 加载预训练模型（如果有）
        await self._load_pretrained_models()
        
        self.initialized = True
        logging.info("分析引擎初始化完成")
    
    async def _load_pretrained_models(self):
        """加载预训练模型"""
        # 这里可以加载预训练的机器学习模型
        # 当前实现是空的，可以根据需要扩展
        pass
    
    async def analyze_data(self, data: List[Dict[str, Any]], config: AnalysisConfig) -> AnalysisResult:
        """分析数据"""
        start_time = datetime.now()
        analysis_id = f"analysis_{int(start_time.timestamp())}"
        
        try:
            df = pd.DataFrame(data)
            
            if config.analysis_type == AnalysisType.DESCRIPTIVE_STATS:
                results = await self._descriptive_statistics(df, config)
            elif config.analysis_type == AnalysisType.TREND_ANALYSIS:
                results = await self._trend_analysis(df, config)
            elif config.analysis_type == AnalysisType.CORRELATION_ANALYSIS:
                results = await self._correlation_analysis(df, config)
            elif config.analysis_type == AnalysisType.PATTERN_RECOGNITION:
                results = await self._pattern_recognition(df, config)
            elif config.analysis_type == AnalysisType.ANOMALY_DETECTION:
                results = await self._anomaly_detection(df, config)
            elif config.analysis_type == AnalysisType.CLUSTERING_ANALYSIS:
                results = await self._clustering_analysis(df, config)
            elif config.analysis_type == AnalysisType.PREDICTIVE_ANALYSIS:
                results = await self._predictive_analysis(df, config)
            else:
                raise ValueError(f"不支持的分析类型: {config.analysis_type}")
            
            # 生成洞察
            insights = await self._generate_insights(results, config)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = AnalysisResult(
                analysis_id=analysis_id,
                analysis_type=config.analysis_type,
                data_source="memory",
                timestamp=start_time,
                results=results,
                insights=insights,
                execution_time=execution_time
            )
            
            self.analysis_history.append(result)
            logging.info(f"数据分析完成: {config.analysis_type.value}")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logging.error(f"数据分析失败: {e}")
            
            return AnalysisResult(
                analysis_id=analysis_id,
                analysis_type=config.analysis_type,
                data_source="memory",
                timestamp=start_time,
                results={},
                insights=[f"分析失败: {str(e)}"],
                execution_time=execution_time
            )
    
    async def _descriptive_statistics(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """描述性统计分析"""
        results = {}
        
        for column in config.target_columns:
            if column not in df.columns:
                continue
                
            series = df[column]
            
            if pd.api.types.is_numeric_dtype(series):
                stats_data = {
                    "count": int(series.count()),
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "median": float(series.median()),
                    "q1": float(series.quantile(0.25)),
                    "q3": float(series.quantile(0.75)),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurtosis())
                }
            else:
                # 对于分类数据
                value_counts = series.value_counts()
                stats_data = {
                    "count": int(series.count()),
                    "unique_count": int(series.nunique()),
                    "mode": str(value_counts.index[0]) if not value_counts.empty else None,
                    "mode_count": int(value_counts.iloc[0]) if not value_counts.empty else 0,
                    "value_distribution": value_counts.head(10).to_dict()
                }
            
            results[column] = stats_data
        
        return {"descriptive_stats": results}
    
    async def _trend_analysis(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """趋势分析"""
        if not config.time_column or config.time_column not in df.columns:
            raise ValueError("趋势分析需要时间列")
        
        results = {}
        
        # 转换时间列
        df[config.time_column] = pd.to_datetime(df[config.time_column])
        df = df.sort_values(config.time_column)
        
        for column in config.target_columns:
            if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
                continue
            
            # 计算移动平均
            window = config.parameters.get("window", 7) if config.parameters else 7
            df[f"{column}_ma"] = df[column].rolling(window=window).mean()
            
            # 线性趋势分析
            x = np.arange(len(df))
            y = df[column].values
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            trend_direction = "上升" if slope > 0 else "下降" if slope < 0 else "平稳"
            
            results[column] = {
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r_value ** 2),
                "p_value": float(p_value),
                "trend_direction": trend_direction,
                "trend_strength": "强" if abs(r_value) > 0.7 else "中等" if abs(r_value) > 0.3 else "弱"
            }
        
        return {"trend_analysis": results}
    
    async def _correlation_analysis(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """相关性分析"""
        numeric_columns = [col for col in config.target_columns 
                          if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_columns) < 2:
            return {"correlation_analysis": {"error": "需要至少两个数值列进行相关性分析"}}
        
        # 计算相关系数矩阵
        correlation_matrix = df[numeric_columns].corr()
        
        # 找出强相关性（绝对值 > 0.7）
        strong_correlations = []
        for i, col1 in enumerate(numeric_columns):
            for j, col2 in enumerate(numeric_columns):
                if i < j:  # 避免重复和自相关
                    corr = correlation_matrix.iloc[i, j]
                    if abs(corr) > 0.7:
                        strong_correlations.append({
                            "variable1": col1,
                            "variable2": col2,
                            "correlation": float(corr),
                            "strength": "强正相关" if corr > 0.7 else "强负相关"
                        })
        
        return {
            "correlation_analysis": {
                "correlation_matrix": correlation_matrix.to_dict(),
                "strong_correlations": strong_correlations,
                "highest_correlation": max([abs(corr) for corr in correlation_matrix.values.flatten()]) if not correlation_matrix.empty else 0
            }
        }
    
    async def _pattern_recognition(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """模式识别"""
        results = {}
        
        for column in config.target_columns:
            if column not in df.columns:
                continue
                
            series = df[column]
            
            if pd.api.types.is_numeric_dtype(series):
                # 检测周期性模式
                patterns = await self._detect_numeric_patterns(series)
            else:
                # 检测文本模式
                patterns = await self._detect_text_patterns(series)
            
            results[column] = patterns
        
        return {"pattern_recognition": results}
    
    async def _detect_numeric_patterns(self, series: pd.Series) -> Dict[str, Any]:
        """检测数值模式"""
        patterns = {}
        
        # 检测异常值（使用IQR方法）
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = series[(series < lower_bound) | (series > upper_bound)]
        patterns["outliers"] = {
            "count": len(outliers),
            "indices": outliers.index.tolist(),
            "values": outliers.tolist()
        }
        
        # 检测分布类型
        if len(series) > 30:  # 需要足够的数据点
            try:
                # 正态性检验
                _, p_value = stats.normaltest(series.dropna())
                patterns["distribution"] = {
                    "is_normal": p_value > 0.05,
                    "p_value": float(p_value)
                }
            except:
                patterns["distribution"] = {"is_normal": False, "p_value": 0.0}
        
        return patterns
    
    async def _detect_text_patterns(self, series: pd.Series) -> Dict[str, Any]:
        """检测文本模式"""
        patterns = {}
        
        # 检测常见模式（电子邮件、URL、电话号码等）
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        url_pattern = r'https?://[^\s]+'
        
        email_count = series.str.contains(email_pattern, na=False).sum()
        url_count = series.str.contains(url_pattern, na=False).sum()
        
        patterns["common_patterns"] = {
            "email_addresses": int(email_count),
            "urls": int(url_count)
        }
        
        # 文本长度分析
        text_lengths = series.str.len()
        patterns["text_length"] = {
            "mean": float(text_lengths.mean()),
            "std": float(text_lengths.std()),
            "min": int(text_lengths.min()),
            "max": int(text_lengths.max())
        }
        
        return patterns
    
    async def _anomaly_detection(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """异常检测"""
        results = {}
        
        for column in config.target_columns:
            if column not in df.columns or not pd.api.types.is_numeric_dtype(df[column]):
                continue
            
            series = df[column]
            
            # 使用Z-score方法检测异常
            z_scores = np.abs(stats.zscore(series.dropna()))
            threshold = config.parameters.get("threshold", 3) if config.parameters else 3
            
            anomalies = series[z_scores > threshold]
            
            results[column] = {
                "anomaly_count": len(anomalies),
                "anomaly_indices": anomalies.index.tolist(),
                "anomaly_values": anomalies.tolist(),
                "anomaly_percentage": (len(anomalies) / len(series)) * 100
            }
        
        return {"anomaly_detection": results}
    
    async def _clustering_analysis(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """聚类分析"""
        numeric_columns = [col for col in config.target_columns 
                          if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_columns) < 2:
            return {"clustering_analysis": {"error": "需要至少两个数值列进行聚类分析"}}
        
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        # 准备数据
        X = df[numeric_columns].dropna()
        
        if len(X) < 2:
            return {"clustering_analysis": {"error": "数据点不足进行聚类分析"}}
        
        # 标准化数据
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 使用肘部法则确定最佳聚类数
        wcss = []  # Within-Cluster Sum of Square
        max_clusters = min(10, len(X))
        
        for i in range(1, max_clusters + 1):
            kmeans = KMeans(n_clusters=i, random_state=42)
            kmeans.fit(X_scaled)
            wcss.append(kmeans.inertia_)
        
        # 选择最佳聚类数（简化实现）
        optimal_clusters = 3  # 实际应该基于肘部法则自动选择
        
        # 执行聚类
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
        clusters = kmeans.fit_predict(X_scaled)
        
        results = {
            "optimal_clusters": optimal_clusters,
            "cluster_labels": clusters.tolist(),
            "cluster_centers": kmeans.cluster_centers_.tolist(),
            "within_cluster_sum_of_squares": float(kmeans.inertia_),
            "wcss_curve": wcss
        }
        
        return {"clustering_analysis": results}
    
    async def _predictive_analysis(self, df: pd.DataFrame, config: AnalysisConfig) -> Dict[str, Any]:
        """预测分析"""
        # 简化的预测分析实现
        # 在实际应用中，这里会使用更复杂的机器学习模型
        
        numeric_columns = [col for col in config.target_columns 
                          if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_columns) == 0:
            return {"predictive_analysis": {"error": "需要数值列进行预测分析"}}
        
        # 简单的线性预测
        predictions = {}
        
        for column in numeric_columns:
            series = df[column].dropna()
            
            if len(series) < 2:
                continue
            
            # 简单线性回归预测
            x = np.arange(len(series))
            y = series.values
            
            slope, intercept, _, _, _ = stats.linregress(x, y)
            
            # 预测未来3个点
            future_x = np.array([len(series), len(series) + 1, len(series) + 2])
            future_y = slope * future_x + intercept
            
            predictions[column] = {
                "slope": float(slope),
                "intercept": float(intercept),
                "future_predictions": future_y.tolist(),
                "prediction_confidence": 0.8  # 简化置信度
            }
        
        return {"predictive_analysis": predictions}
    
    async def _generate_insights(self, results: Dict[str, Any], config: AnalysisConfig) -> List[str]:
        """生成分析洞察"""
        insights = []
        
        if config.analysis_type == AnalysisType.DESCRIPTIVE_STATS:
            insights = await self._generate_descriptive_insights(results)
        elif config.analysis_type == AnalysisType.TREND_ANALYSIS:
            insights = await self._generate_trend_insights(results)
        elif config.analysis_type == AnalysisType.CORRELATION_ANALYSIS:
            insights = await self._generate_correlation_insights(results)
        elif config.analysis_type == AnalysisType.ANOMALY_DETECTION:
            insights = await self._generate_anomaly_insights(results)
        
        return insights
    
    async def _generate_descriptive_insights(self, results: Dict[str, Any]) -> List[str]:
        """生成描述性统计洞察"""
        insights = []
        stats_data = results.get("descriptive_stats", {})
        
        for column, stats in stats_data.items():
            if "mean" in stats:
                insights.append(f"列 '{column}' 的平均值为 {stats['mean']:.2f}")
                
                if stats.get("skewness", 0) > 1:
                    insights.append(f"列 '{column}' 呈正偏态分布")
                elif stats.get("skewness", 0) < -1:
                    insights.append(f"列 '{column}' 呈负偏态分布")
        
        return insights
    
    async def _generate_trend_insights(self, results: Dict[str, Any]) -> List[str]:
        """生成趋势分析洞察"""
        insights = []
        trend_data = results.get("trend_analysis", {})
        
        for column, trend in trend_data.items():
            direction = trend.get("trend_direction", "未知")
            strength = trend.get("trend_strength", "未知")
            insights.append(f"列 '{column}' 显示{strength}{direction}趋势")
        
        return insights
    
    async def _generate_correlation_insights(self, results: Dict[str, Any]) -> List[str]:
        """生成相关性分析洞察"""
        insights = []
        corr_data = results.get("correlation_analysis", {})
        
        strong_corrs = corr_data.get("strong_correlations", [])
        for corr in strong_corrs:
            insights.append(f"'{corr['variable1']}' 和 '{corr['variable2']}' 存在{corr['strength']}")
        
        return insights
    
    async def _generate_anomaly_insights(self, results: Dict[str, Any]) -> List[str]:
        """生成异常检测洞察"""
        insights = []
        anomaly_data = results.get("anomaly_detection", {})
        
        for column, anomalies in anomaly_data.items():
            count = anomalies.get("anomaly_count", 0)
            percentage = anomalies.get("anomaly_percentage", 0)
            if count > 0:
                insights.append(f"列 '{column}' 检测到 {count} 个异常值 ({percentage:.1f}%)")
        
        return insights
    
    def get_analytics_stats(self) -> Dict[str, Any]:
        """获取分析统计"""
        if not self.analysis_history:
            return {}
        
        analysis_counts = {}
        for result in self.analysis_history:
            analysis_type = result.analysis_type.value
            analysis_counts[analysis_type] = analysis_counts.get(analysis_type, 0) + 1
        
        total_time = sum(result.execution_time for result in self.analysis_history)
        
        return {
            "total_analyses": len(self.analysis_history),
            "analysis_type_distribution": analysis_counts,
            "average_execution_time": total_time / len(self.analysis_history),
            "total_insights_generated": sum(len(result.insights) for result in self.analysis_history)
        }

# 全局分析引擎实例
analytics_engine = AnalyticsEngine()