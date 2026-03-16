"""
数据度量工具模块

提供数据质量度量、统计度量、性能度量等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from scipy import stats
import warnings
import logging
from collections import Counter
import time

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataMetrics:
    """数据度量计算器类"""
    
    def __init__(self, data: Union[pd.DataFrame, pd.Series]):
        """
        初始化数据度量计算器
        
        Args:
            data: 要计算度量的数据
        """
        self.data = data
        self._validate_data()
    
    def _validate_data(self) -> None:
        """验证数据格式"""
        if not isinstance(self.data, (pd.DataFrame, pd.Series)):
            raise TypeError("数据必须是 pandas DataFrame 或 Series")
    
    def completeness_metrics(self) -> Dict[str, float]:
        """
        计算完整性度量
        
        Returns:
            完整性度量字典
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                total_cells = self.data.shape[0] * self.data.shape[1]
                non_null_cells = self.data.count().sum()
                completeness = (non_null_cells / total_cells) * 100
                
                # 按列计算完整性
                column_completeness = {}
                for col in self.data.columns:
                    column_completeness[col] = (self.data[col].count() / len(self.data)) * 100
                
                return {
                    'overall_completeness': completeness,
                    'column_completeness': column_completeness,
                    'complete_rows': int((self.data.isnull().sum(axis=1) == 0).sum()),
                    'incomplete_rows': int((self.data.isnull().sum(axis=1) > 0).sum()),
                    'missing_cells': int(total_cells - non_null_cells)
                }
            else:
                completeness = (self.data.count() / len(self.data)) * 100
                return {
                    'overall_completeness': completeness,
                    'missing_values': int(len(self.data) - self.data.count()),
                    'complete_values': int(self.data.count())
                }
        except Exception as e:
            logger.error(f"计算完整性度量时出错: {e}")
            raise
    
    def uniqueness_metrics(self) -> Dict[str, Any]:
        """
        计算唯一性度量
        
        Returns:
            唯一性度量字典
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                total_rows = len(self.data)
                duplicate_rows = self.data.duplicated().sum()
                uniqueness = ((total_rows - duplicate_rows) / total_rows) * 100
                
                # 按列计算唯一性
                column_uniqueness = {}
                for col in self.data.columns:
                    unique_values = self.data[col].nunique()
                    column_uniqueness[col] = {
                        'unique_count': unique_values,
                        'uniqueness_ratio': (unique_values / len(self.data)) * 100,
                        'duplicate_count': int(len(self.data) - self.data[col].nunique())
                    }
                
                return {
                    'overall_uniqueness': uniqueness,
                    'duplicate_rows': int(duplicate_rows),
                    'unique_rows': int(total_rows - duplicate_rows),
                    'column_uniqueness': column_uniqueness
                }
            else:
                unique_count = self.data.nunique()
                uniqueness = (unique_count / len(self.data)) * 100
                return {
                    'unique_count': unique_count,
                    'uniqueness_ratio': uniqueness,
                    'duplicate_count': int(len(self.data) - unique_count)
                }
        except Exception as e:
            logger.error(f"计算唯一性度量时出错: {e}")
            raise
    
    def validity_metrics(self, rules: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        """
        计算有效性度量
        
        Args:
            rules: 自定义验证规则字典 {column: validation_function}
            
        Returns:
            有效性度量字典
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                validity_results = {}
                overall_valid = 0
                total_validations = 0
                
                for col in self.data.columns:
                    col_valid = 0
                    col_total = len(self.data[col].dropna())
                    
                    if col_total == 0:
                        validity_results[col] = {'valid_ratio': 0, 'invalid_count': 0}
                        continue
                    
                    if rules and col in rules:
                        # 使用自定义规则
                        valid_mask = self.data[col].apply(lambda x: rules[col](x) if pd.notna(x) else False)
                        col_valid = valid_mask.sum()
                    else:
                        # 默认有效性检查
                        if self.data[col].dtype in ['int64', 'float64']:
                            # 数值列：检查是否为数字且非无穷
                            valid_mask = pd.to_numeric(self.data[col], errors='coerce').notna()
                            col_valid = valid_mask.sum()
                        else:
                            # 文本列：检查非空且非空字符串
                            valid_mask = (self.data[col].notna() & 
                                        (self.data[col].astype(str).str.strip() != '') &
                                        (self.data[col].astype(str) != 'nan'))
                            col_valid = valid_mask.sum()
                    
                    validity_ratio = (col_valid / col_total) * 100 if col_total > 0 else 0
                    validity_results[col] = {
                        'valid_ratio': validity_ratio,
                        'valid_count': int(col_valid),
                        'invalid_count': int(col_total - col_valid),
                        'total_count': int(col_total)
                    }
                    
                    overall_valid += col_valid
                    total_validations += col_total
                
                overall_validity = (overall_valid / total_validations) * 100 if total_validations > 0 else 0
                
                return {
                    'overall_validity': overall_validity,
                    'column_validity': validity_results
                }
            else:
                # 单列数据的有效性检查
                total_count = len(self.data.dropna())
                if total_count == 0:
                    return {'overall_validity': 0, 'valid_count': 0, 'invalid_count': 0}
                
                if rules:
                    valid_mask = self.data.apply(lambda x: rules[x] if pd.notna(x) else False)
                    valid_count = valid_mask.sum()
                else:
                    if self.data.dtype in ['int64', 'float64']:
                        valid_mask = pd.to_numeric(self.data, errors='coerce').notna()
                        valid_count = valid_mask.sum()
                    else:
                        valid_mask = (self.data.notna() & 
                                    (self.data.astype(str).str.strip() != '') &
                                    (self.data.astype(str) != 'nan'))
                        valid_count = valid_mask.sum()
                
                validity_ratio = (valid_count / total_count) * 100
                
                return {
                    'overall_validity': validity_ratio,
                    'valid_count': int(valid_count),
                    'invalid_count': int(total_count - valid_count),
                    'total_count': int(total_count)
                }
        except Exception as e:
            logger.error(f"计算有效性度量时出错: {e}")
            raise
    
    def consistency_metrics(self) -> Dict[str, Any]:
        """
        计算一致性度量
        
        Returns:
            一致性度量字典
        """
        try:
            if isinstance(self.data, pd.DataFrame):
                consistency_results = {}
                type_consistency = 0
                
                for col in self.data.columns:
                    # 数据类型一致性
                    expected_type = str(self.data[col].dtype)
                    actual_types = set()
                    
                    for val in self.data[col].dropna().head(1000):  # 采样检查
                        if pd.isna(val):
                            continue
                        if self.data[col].dtype in ['int64', 'float64']:
                            try:
                                float(val)
                                actual_types.add('numeric')
                            except:
                                actual_types.add('text')
                        else:
                            actual_types.add('text')
                    
                    type_consistency_score = 1.0 if len(actual_types) <= 1 else 0.0
                    type_consistency += type_consistency_score
                    
                    # 格式一致性（针对文本列）
                    format_consistency = 0
                    if self.data[col].dtype == 'object':
                        sample_size = min(100, len(self.data[col].dropna()))
                        if sample_size > 0:
                            # 检查长度一致性
                            lengths = self.data[col].dropna().head(sample_size).astype(str).str.len()
                            length_std = lengths.std()
                            format_consistency = 1.0 / (1 + length_std) if length_std > 0 else 1.0
                    
                    consistency_results[col] = {
                        'type_consistency': type_consistency_score,
                        'format_consistency': format_consistency,
                        'overall_consistency': (type_consistency_score + format_consistency) / 2
                    }
                
                overall_consistency = (type_consistency / len(self.data.columns)) * 100
                
                return {
                    'overall_consistency': overall_consistency,
                    'column_consistency': consistency_results
                }
            else:
                # 单列数据的一致性
                if self.data.dtype in ['int64', 'float64']:
                    # 数值列：检查异常值比例
                    Q1 = self.data.quantile(0.25)
                    Q3 = self.data.quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = ((self.data < (Q1 - 1.5 * IQR)) | 
                              (self.data > (Q3 + 1.5 * IQR))).sum()
                    consistency = ((len(self.data) - outliers) / len(self.data)) * 100
                else:
                    # 文本列：检查长度一致性
                    lengths = self.data.astype(str).str.len()
                    length_std = lengths.std()
                    consistency = 1.0 / (1 + length_std) * 100 if length_std > 0 else 100
                
                return {
                    'overall_consistency': consistency,
                    'data_type': str(self.data.dtype),
                    'sample_size': len(self.data)
                }
        except Exception as e:
            logger.error(f"计算一致性度量时出错: {e}")
            raise
    
    def accuracy_metrics(self, reference_data: Optional[Union[pd.DataFrame, pd.Series]] = None) -> Dict[str, Any]:
        """
        计算准确性度量
        
        Args:
            reference_data: 参考数据（如果提供）
            
        Returns:
            准确性度量字典
        """
        try:
            if reference_data is not None:
                if isinstance(self.data, pd.DataFrame) and isinstance(reference_data, pd.DataFrame):
                    # 比较两个数据集
                    if self.data.shape != reference_data.shape:
                        raise ValueError("数据形状不匹配")
                    
                    # 计算匹配率
                    matches = 0
                    total_cells = 0
                    
                    for col in self.data.columns:
                        if col in reference_data.columns:
                            # 处理缺失值
                            mask = self.data[col].notna() & reference_data[col].notna()
                            if mask.sum() > 0:
                                col_matches = (self.data.loc[mask, col] == reference_data.loc[mask, col]).sum()
                                matches += col_matches
                                total_cells += mask.sum()
                    
                    accuracy = (matches / total_cells) * 100 if total_cells > 0 else 0
                    
                    return {
                        'accuracy': accuracy,
                        'matches': int(matches),
                        'total_compared': int(total_cells),
                        'mismatches': int(total_cells - matches)
                    }
                
                elif isinstance(self.data, pd.Series) and isinstance(reference_data, pd.Series):
                    if len(self.data) != len(reference_data):
                        raise ValueError("序列长度不匹配")
                    
                    mask = self.data.notna() & reference_data.notna()
                    matches = (self.data[mask] == reference_data[mask]).sum()
                    total = mask.sum()
                    accuracy = (matches / total) * 100 if total > 0 else 0
                    
                    return {
                        'accuracy': accuracy,
                        'matches': int(matches),
                        'total_compared': int(total),
                        'mismatches': int(total - matches)
                    }
            
            else:
                # 无参考数据时的自一致性检查
                if isinstance(self.data, pd.DataFrame):
                    # 检查重复行的比例
                    duplicate_ratio = (self.data.duplicated().sum() / len(self.data)) * 100
                    consistency_score = 100 - duplicate_ratio
                    
                    return {
                        'self_consistency': consistency_score,
                        'duplicate_ratio': duplicate_ratio,
                        'unique_rows': len(self.data) - self.data.duplicated().sum()
                    }
                else:
                    # 单列数据：检查值的合理性
                    if self.data.dtype in ['int64', 'float64']:
                        # 检查异常值
                        Q1 = self.data.quantile(0.25)
                        Q3 = self.data.quantile(0.75)
                        IQR = Q3 - Q1
                        outliers = ((self.data < (Q1 - 1.5 * IQR)) | 
                                  (self.data > (Q3 + 1.5 * IQR))).sum()
                        accuracy = ((len(self.data) - outliers) / len(self.data)) * 100
                    else:
                        # 文本数据：检查空值和异常值
                        empty_ratio = (self.data.astype(str).str.strip() == '').sum() / len(self.data)
                        accuracy = (1 - empty_ratio) * 100
                    
                    return {
                        'self_consistency': accuracy,
                        'data_quality_score': accuracy
                    }
        except Exception as e:
            logger.error(f"计算准确性度量时出错: {e}")
            raise
    
    def timeliness_metrics(self, timestamp_column: Optional[str] = None) -> Dict[str, Any]:
        """
        计算时效性度量
        
        Args:
            timestamp_column: 时间戳列名
            
        Returns:
            时效性度量字典
        """
        try:
            if timestamp_column and isinstance(self.data, pd.DataFrame):
                if timestamp_column not in self.data.columns:
                    raise ValueError(f"时间戳列 '{timestamp_column}' 不存在")
                
                timestamps = pd.to_datetime(self.data[timestamp_column], errors='coerce')
                now = pd.Timestamp.now()
                
                # 计算数据新鲜度
                ages = (now - timestamps).dt.days
                
                return {
                    'freshness_score': max(0, 100 - ages.mean()),  # 假设100天为完全过期
                    'average_age_days': float(ages.mean()),
                    'oldest_record_days': float(ages.max()),
                    'newest_record_days': float(ages.min()),
                    'records_over_30_days': int((ages > 30).sum()),
                    'records_over_90_days': int((ages > 90).sum())
                }
            else:
                return {
                    'message': '需要提供时间戳列来计算时效性度量',
                    'freshness_score': 0
                }
        except Exception as e:
            logger.error(f"计算时效性度量时出错: {e}")
            raise
    
    def data_quality_score(self, weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        计算综合数据质量分数
        
        Args:
            weights: 各维度权重字典
            
        Returns:
            综合质量分数
        """
        try:
            # 默认权重
            if weights is None:
                weights = {
                    'completeness': 0.25,
                    'uniqueness': 0.20,
                    'validity': 0.25,
                    'consistency': 0.15,
                    'accuracy': 0.15
                }
            
            # 计算各维度分数
            completeness = self.completeness_metrics()
            uniqueness = self.uniqueness_metrics()
            validity = self.validity_metrics()
            consistency = self.consistency_metrics()
            accuracy = self.accuracy_metrics()
            
            # 提取分数
            scores = {
                'completeness': completeness.get('overall_completeness', 0),
                'uniqueness': uniqueness.get('overall_uniqueness', 0),
                'validity': validity.get('overall_validity', 0),
                'consistency': consistency.get('overall_consistency', 0),
                'accuracy': accuracy.get('accuracy', 0) if isinstance(accuracy, dict) and 'accuracy' in accuracy else accuracy.get('self_consistency', 0)
            }
            
            # 计算加权总分
            weighted_score = sum(scores[dimension] * weights.get(dimension, 0) 
                               for dimension in scores)
            
            return {
                'overall_score': weighted_score,
                'dimension_scores': scores,
                'weights_used': weights,
                'grade': self._get_quality_grade(weighted_score)
            }
        except Exception as e:
            logger.error(f"计算数据质量分数时出错: {e}")
            raise
    
    def _get_quality_grade(self, score: float) -> str:
        """根据分数获取质量等级"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "中等"
        elif score >= 60:
            return "及格"
        else:
            return "不及格"


def calculate_column_statistics(data: pd.Series) -> Dict[str, Any]:
    """
    计算列统计信息
    
    Args:
        data: 数据序列
        
    Returns:
        统计信息字典
    """
    try:
        stats_dict = {
            'count': len(data),
            'missing_count': data.isnull().sum(),
            'unique_count': data.nunique(),
            'memory_usage': data.memory_usage(deep=True)
        }
        
        if data.dtype in ['int64', 'float64']:
            # 数值统计
            stats_dict.update({
                'mean': float(data.mean()),
                'median': float(data.median()),
                'std': float(data.std()),
                'min': float(data.min()),
                'max': float(data.max()),
                'q25': float(data.quantile(0.25)),
                'q75': float(data.quantile(0.75)),
                'skewness': float(stats.skew(data.dropna())),
                'kurtosis': float(stats.kurtosis(data.dropna()))
            })
        else:
            # 分类统计
            value_counts = data.value_counts().head(10)
            stats_dict.update({
                'most_frequent': value_counts.index[0] if len(value_counts) > 0 else None,
                'most_frequent_count': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                'top_values': value_counts.to_dict(),
                'avg_length': float(data.astype(str).str.len().mean()) if len(data) > 0 else 0
            })
        
        return stats_dict
    except Exception as e:
        logger.error(f"计算列统计信息时出错: {e}")
        raise


def benchmark_data_quality(data: pd.DataFrame, 
                          baseline_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    数据质量基准测试
    
    Args:
        data: 要测试的数据
        baseline_data: 基准数据
        
    Returns:
        基准测试结果
    """
    try:
        metrics_calculator = DataMetrics(data)
        
        # 计算当前数据质量指标
        current_quality = {
            'completeness': metrics_calculator.completeness_metrics(),
            'uniqueness': metrics_calculator.uniqueness_metrics(),
            'validity': metrics_calculator.validity_metrics(),
            'consistency': metrics_calculator.consistency_metrics(),
            'accuracy': metrics_calculator.accuracy_metrics(),
            'overall_score': metrics_calculator.data_quality_score()
        }
        
        benchmark_result = {
            'current_data_quality': current_quality,
            'timestamp': time.time()
        }
        
        if baseline_data is not None:
            baseline_calculator = DataMetrics(baseline_data)
            baseline_quality = {
                'completeness': baseline_calculator.completeness_metrics(),
                'uniqueness': baseline_calculator.uniqueness_metrics(),
                'validity': baseline_calculator.validity_metrics(),
                'consistency': baseline_calculator.consistency_metrics(),
                'accuracy': baseline_calculator.accuracy_metrics(),
                'overall_score': baseline_calculator.data_quality_score()
            }
            
            # 计算改进情况
            improvements = {}
            for dimension in ['completeness', 'uniqueness', 'validity', 'consistency', 'accuracy']:
                current_score = current_quality[dimension].get(f'overall_{dimension}', 0)
                baseline_score = baseline_quality[dimension].get(f'overall_{dimension}', 0)
                improvements[dimension] = current_score - baseline_score
            
            overall_improvement = current_quality['overall_score']['overall_score'] - baseline_quality['overall_score']['overall_score']
            
            benchmark_result.update({
                'baseline_data_quality': baseline_quality,
                'improvements': improvements,
                'overall_improvement': overall_improvement,
                'trend': 'improving' if overall_improvement > 0 else 'declining' if overall_improvement < 0 else 'stable'
            })
        
        return benchmark_result
    except Exception as e:
        logger.error(f"数据质量基准测试时出错: {e}")
        raise


if __name__ == "__main__":
    # 示例用法
    print("数据度量工具模块")
    
    # 创建示例数据
    np.random.seed(42)
    sample_data = pd.DataFrame({
        'numeric_col': np.random.normal(100, 15, 1000),
        'category_col': np.random.choice(['A', 'B', 'C', None], 1000),
        'text_col': ['Sample text ' + str(i) for i in range(1000)] + [None] * 50,
        'date_col': pd.date_range('2023-01-01', periods=1000, freq='D')
    })
    
    # 添加一些重复行和缺失值
    sample_data.loc[0:50, 'numeric_col'] = None
    sample_data = pd.concat([sample_data, sample_data.iloc[0:100]], ignore_index=True)
    
    # 创建度量计算器
    metrics_calculator = DataMetrics(sample_data)
    
    # 计算各种度量
    completeness = metrics_calculator.completeness_metrics()
    print(f"完整性分数: {completeness['overall_completeness']:.2f}%")
    
    uniqueness = metrics_calculator.uniqueness_metrics()
    print(f"唯一性分数: {uniqueness['overall_uniqueness']:.2f}%")
    
    validity = metrics_calculator.validity_metrics()
    print(f"有效性分数: {validity['overall_validity']:.2f}%")
    
    quality_score = metrics_calculator.data_quality_score()
    print(f"综合质量分数: {quality_score['overall_score']:.2f} ({quality_score['grade']})")
    
    print("数据度量示例完成")