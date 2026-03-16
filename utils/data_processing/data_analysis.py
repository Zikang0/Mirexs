"""
数据分析工具模块

提供数据探索、统计分析、趋势分析等功能
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Union
from scipy import stats
import warnings
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataAnalyzer:
    """数据分析器类"""
    
    def __init__(self, data: Union[pd.DataFrame, pd.Series, np.ndarray]):
        """
        初始化数据分析器
        
        Args:
            data: 要分析的数据
        """
        self.data = data
        self._validate_data()
    
    def _validate_data(self) -> None:
        """验证数据格式"""
        if not isinstance(self.data, (pd.DataFrame, pd.Series, np.ndarray)):
            raise TypeError("数据必须是 pandas DataFrame、Series 或 numpy array")
    
    def basic_statistics(self) -> Dict[str, Any]:
        """
        计算基本统计信息
        
        Returns:
            包含基本统计信息的字典
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                return {
                    'shape': self.data.shape,
                    'columns': list(self.data.columns),
                    'dtypes': self.data.dtypes.to_dict(),
                    'missing_values': self.data.isnull().sum().to_dict(),
                    'memory_usage': self.data.memory_usage(deep=True).sum(),
                    'describe': self.data.describe().to_dict()
                }
            elif isinstance(self.data, pd.Series):
                return {
                    'length': len(self.data),
                    'dtype': str(self.data.dtype),
                    'missing_values': self.data.isnull().sum(),
                    'unique_values': self.data.nunique(),
                    'describe': self.data.describe().to_dict()
                }
            else:  # numpy array
                return {
                    'shape': self.data.shape,
                    'dtype': str(self.data.dtype),
                    'mean': float(np.mean(self.data)),
                    'std': float(np.std(self.data)),
                    'min': float(np.min(self.data)),
                    'max': float(np.max(self.data))
                }
        except Exception as e:
            logger.error(f"计算基本统计信息时出错: {e}")
            raise
    
    def correlation_analysis(self, method: str = 'pearson') -> pd.DataFrame:
        """
        相关性分析
        
        Args:
            method: 相关性方法 ('pearson', 'spearman', 'kendall')
            
        Returns:
            相关性矩阵
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                return self.data.corr(method=method)
            else:
                raise ValueError("相关性分析需要 DataFrame 数据")
        except Exception as e:
            logger.error(f"相关性分析时出错: {e}")
            raise
    
    def outlier_detection(self, method: str = 'iqr', threshold: float = 1.5) -> Dict[str, Any]:
        """
        异常值检测
        
        Args:
            method: 检测方法 ('iqr', 'zscore', 'isolation_forest')
            threshold: 阈值
            
        Returns:
            异常值检测结果
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                outliers = {}
                
                for col in numeric_cols:
                    if method == 'iqr':
                        Q1 = self.data[col].quantile(0.25)
                        Q3 = self.data[col].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - threshold * IQR
                        upper_bound = Q3 + threshold * IQR
                        outliers[col] = self.data[(self.data[col] < lower_bound) | 
                                                (self.data[col] > upper_bound)].index.tolist()
                    
                    elif method == 'zscore':
                        z_scores = np.abs(stats.zscore(self.data[col].dropna()))
                        outliers[col] = self.data[z_scores > threshold].index.tolist()
                    
                    elif method == 'isolation_forest':
                        from sklearn.ensemble import IsolationForest
                        iso_forest = IsolationForest(contamination=0.1, random_state=42)
                        outlier_labels = iso_forest.fit_predict(self.data[[col]])
                        outliers[col] = self.data[outlier_labels == -1].index.tolist()
                
                return outliers
            else:
                raise ValueError("异常值检测需要 DataFrame 数据")
        except Exception as e:
            logger.error(f"异常值检测时出错: {e}")
            raise
    
    def trend_analysis(self, column: str, window: int = 7) -> Dict[str, Any]:
        """
        趋势分析
        
        Args:
            column: 要分析的列名
            window: 移动窗口大小
            
        Returns:
            趋势分析结果
        """
        try:
            if isinstance(self.data, pd.DataFrame) and column in self.data.columns:
                series = self.data[column].dropna()
                
                # 移动平均
                moving_avg = series.rolling(window=window).mean()
                
                # 趋势检测
                x = np.arange(len(series))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, series.values)
                
                trend_direction = "上升" if slope > 0 else "下降" if slope < 0 else "平稳"
                
                return {
                    'trend_slope': slope,
                    'trend_direction': trend_direction,
                    'r_squared': r_value ** 2,
                    'p_value': p_value,
                    'moving_average': moving_avg.to_dict(),
                    'series_length': len(series)
                }
            else:
                raise ValueError(f"列 '{column}' 不存在于数据中")
        except Exception as e:
            logger.error(f"趋势分析时出错: {e}")
            raise
    
    def distribution_analysis(self, column: str) -> Dict[str, Any]:
        """
        分布分析
        
        Args:
            column: 要分析的列名
            
        Returns:
            分布分析结果
        """
        try:
            if isinstance(self.data, pd.DataFrame) and column in self.data.columns:
                series = self.data[column].dropna()
                
                # 正态性检验
                shapiro_stat, shapiro_p = stats.shapiro(series[:5000] if len(series) > 5000 else series)
                
                # 分布拟合
                distributions = ['norm', 'expon', 'gamma', 'uniform']
                best_dist = None
                best_params = None
                best_ks_stat = float('inf')
                
                for dist_name in distributions:
                    try:
                        dist = getattr(stats, dist_name)
                        params = dist.fit(series)
                        ks_stat, ks_p = stats.kstest(series, lambda x: dist.cdf(x, *params))
                        
                        if ks_stat < best_ks_stat:
                            best_ks_stat = ks_stat
                            best_dist = dist_name
                            best_params = params
                    except:
                        continue
                
                return {
                    'shapiro_statistic': shapiro_stat,
                    'shapiro_p_value': shapiro_p,
                    'is_normal': shapiro_p > 0.05,
                    'best_fit_distribution': best_dist,
                    'distribution_parameters': best_params,
                    'ks_statistic': best_ks_stat,
                    'skewness': float(stats.skew(series)),
                    'kurtosis': float(stats.kurtosis(series))
                }
            else:
                raise ValueError(f"列 '{column}' 不存在于数据中")
        except Exception as e:
            logger.error(f"分布分析时出错: {e}")
            raise
    
    def segment_analysis(self, segment_column: str, target_column: str) -> Dict[str, Any]:
        """
        分段分析
        
        Args:
            segment_column: 分段依据的列
            target_column: 目标分析的列
            
        Returns:
            分段分析结果
        """
        try:
            if (isinstance(self.data, pd.DataFrame) and 
                segment_column in self.data.columns and 
                target_column in self.data.columns):
                
                segments = self.data.groupby(segment_column)[target_column].agg([
                    'count', 'mean', 'std', 'min', 'max', 'median'
                ]).round(4)
                
                return {
                    'segment_summary': segments.to_dict('index'),
                    'segment_count': len(segments),
                    'largest_segment': segments['count'].idxmax(),
                    'highest_mean': segments['mean'].idxmax(),
                    'lowest_mean': segments['mean'].idxmin()
                }
            else:
                raise ValueError("指定的列不存在于数据中")
        except Exception as e:
            logger.error(f"分段分析时出错: {e}")
            raise


def analyze_data_quality(data: Union[pd.DataFrame, pd.Series]) -> Dict[str, Any]:
    """
    数据质量分析
    
    Args:
        data: 要分析的数据
        
    Returns:
        数据质量报告
    """
    try:
        analyzer = DataAnalyzer(data)
        
        quality_report = {
            'basic_stats': analyzer.basic_statistics(),
            'completeness': 0,
            'consistency': 0,
            'validity': 0,
            'uniqueness': 0
        }
        
        if isinstance(data, pd.DataFrame):
            # 计算完整性
            total_cells = data.shape[0] * data.shape[1]
            non_null_cells = data.count().sum()
            quality_report['completeness'] = (non_null_cells / total_cells) * 100
            
            # 计算唯一性
            duplicate_rows = data.duplicated().sum()
            quality_report['uniqueness'] = ((data.shape[0] - duplicate_rows) / data.shape[0]) * 100
            
            # 计算一致性（数据类型一致性）
            type_consistency = 0
            for col in data.columns:
                if data[col].dtype in ['int64', 'float64']:
                    # 检查数值列是否有非数值数据
                    non_numeric = data[col].apply(lambda x: not isinstance(x, (int, float, np.number)))
                    type_consistency += (1 - non_numeric.sum() / len(data)) * 100
                else:
                    type_consistency += 100
            
            quality_report['consistency'] = type_consistency / len(data.columns)
            
            # 计算有效性（基于常见约束）
            validity_scores = []
            for col in data.columns:
                if data[col].dtype in ['int64', 'float64']:
                    # 检查是否有异常值
                    Q1 = data[col].quantile(0.25)
                    Q3 = data[col].quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = ((data[col] < (Q1 - 1.5 * IQR)) | 
                              (data[col] > (Q3 + 1.5 * IQR))).sum()
                    validity_scores.append((1 - outliers / len(data)) * 100)
                else:
                    validity_scores.append(100)  # 假设文本列都是有效的
            
            quality_report['validity'] = np.mean(validity_scores)
        
        return quality_report
    except Exception as e:
        logger.error(f"数据质量分析时出错: {e}")
        raise


def detect_data_patterns(data: pd.DataFrame) -> Dict[str, Any]:
    """
    检测数据模式
    
    Args:
        data: 要分析的数据
        
    Returns:
        检测到的模式
    """
    try:
        patterns = {
            'temporal_patterns': {},
            'seasonal_patterns': {},
            'cyclical_patterns': {},
            'trend_patterns': {}
        }
        
        # 查找时间相关的列
        date_columns = []
        for col in data.columns:
            if data[col].dtype == 'object':
                # 尝试检测日期格式
                sample = data[col].dropna().head(100)
                try:
                    pd.to_datetime(sample)
                    date_columns.append(col)
                except:
                    continue
        
        # 分析时间模式
        for col in date_columns:
            try:
                date_series = pd.to_datetime(data[col])
                
                # 按小时、星期、月份分析
                patterns['temporal_patterns'][col] = {
                    'hour_distribution': date_series.dt.hour.value_counts().to_dict(),
                    'weekday_distribution': date_series.dt.dayofweek.value_counts().to_dict(),
                    'month_distribution': date_series.dt.month.value_counts().to_dict()
                }
            except Exception as e:
                logger.warning(f"分析时间列 {col} 时出错: {e}")
        
        # 分析数值列的模式
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            series = data[col].dropna()
            if len(series) > 10:
                # 简单的趋势检测
                x = np.arange(len(series))
                slope, _, r_value, _, _ = stats.linregress(x, series.values)
                
                patterns['trend_patterns'][col] = {
                    'slope': slope,
                    'r_squared': r_value ** 2,
                    'trend_strength': 'strong' if abs(r_value) > 0.7 else 'moderate' if abs(r_value) > 0.3 else 'weak'
                }
        
        return patterns
    except Exception as e:
        logger.error(f"检测数据模式时出错: {e}")
        raise


def compare_datasets(data1: pd.DataFrame, data2: pd.DataFrame, 
                    method: str = 'basic') -> Dict[str, Any]:
    """
    数据集比较
    
    Args:
        data1: 第一个数据集
        data2: 第二个数据集
        method: 比较方法 ('basic', 'statistical', 'structural')
        
    Returns:
        比较结果
    """
    try:
        comparison = {
            'basic_comparison': {},
            'statistical_comparison': {},
            'structural_comparison': {}
        }
        
        # 基本比较
        comparison['basic_comparison'] = {
            'shape_difference': {
                'rows': data2.shape[0] - data1.shape[0],
                'columns': data2.shape[1] - data1.shape[1]
            },
            'common_columns': list(set(data1.columns) & set(data2.columns)),
            'unique_to_data1': list(set(data1.columns) - set(data2.columns)),
            'unique_to_data2': list(set(data2.columns) - set(data1.columns))
        }
        
        # 统计比较
        if method in ['basic', 'statistical']:
            numeric_cols1 = data1.select_dtypes(include=[np.number]).columns
            numeric_cols2 = data2.select_dtypes(include=[np.number]).columns
            common_numeric = list(set(numeric_cols1) & set(numeric_cols2))
            
            for col in common_numeric:
                stats1 = data1[col].describe()
                stats2 = data2[col].describe()
                
                comparison['statistical_comparison'][col] = {
                    'mean_difference': float(stats2['mean'] - stats1['mean']),
                    'std_difference': float(stats2['std'] - stats1['std']),
                    'ks_statistic': float(stats.ks_2samp(data1[col].dropna(), data2[col].dropna())[0])
                }
        
        # 结构比较
        if method in ['basic', 'structural']:
            comparison['structural_comparison'] = {
                'dtypes_match': (data1.dtypes == data2.dtypes.reindex(data1.columns)).all(),
                'missing_pattern_similarity': 0,
                'value_distribution_similarity': {}
            }
            
            # 计算缺失值模式相似性
            missing1 = data1.isnull().sum()
            missing2 = data2.reindex(columns=data1.columns).isnull().sum()
            comparison['structural_comparison']['missing_pattern_similarity'] = float(
                1 - np.mean(np.abs(missing1 - missing2) / np.maximum(missing1 + missing2, 1))
            )
        
        return comparison
    except Exception as e:
        logger.error(f"数据集比较时出错: {e}")
        raise


# 便捷函数
def quick_analysis(data: Union[pd.DataFrame, pd.Series]) -> Dict[str, Any]:
    """
    快速数据分析
    
    Args:
        data: 要分析的数据
        
    Returns:
        快速分析结果
    """
    try:
        analyzer = DataAnalyzer(data)
        
        result = {
            'basic_stats': analyzer.basic_statistics(),
            'data_quality': analyze_data_quality(data)
        }
        
        if isinstance(data, pd.DataFrame):
            # 添加相关性分析
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 1:
                result['correlations'] = analyzer.correlation_analysis().to_dict()
            
            # 添加数据模式检测
            result['patterns'] = detect_data_patterns(data)
        
        return result
    except Exception as e:
        logger.error(f"快速分析时出错: {e}")
        raise


if __name__ == "__main__":
    # 示例用法
    print("数据分析工具模块")
    
    # 创建示例数据
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'A': np.random.normal(100, 15, 1000),
        'B': np.random.exponential(2, 1000),
        'C': np.random.choice(['X', 'Y', 'Z'], 1000),
        'date': pd.date_range('2023-01-01', periods=1000, freq='D')
    })
    
    # 执行快速分析
    result = quick_analysis(sample_data)
    print("快速分析完成")
    print(f"数据形状: {result['basic_stats']['shape']}")
    print(f"数据质量完整性: {result['data_quality']['completeness']:.2f}%")