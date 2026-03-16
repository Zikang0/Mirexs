"""
通用指标模块

提供各种通用指标计算的实用工具函数，包括统计指标、性能指标等。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import statistics
import math
from collections import defaultdict


class CommonMetrics:
    """通用指标计算类"""
    
    @staticmethod
    def calculate_mean(values: List[Union[int, float]]) -> float:
        """计算平均值
        
        Args:
            values: 数值列表
            
        Returns:
            平均值
        """
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    @staticmethod
    def calculate_median(values: List[Union[int, float]]) -> float:
        """计算中位数
        
        Args:
            values: 数值列表
            
        Returns:
            中位数
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
        else:
            return sorted_values[n//2]
    
    @staticmethod
    def calculate_mode(values: List[Any]) -> Any:
        """计算众数
        
        Args:
            values: 值列表
            
        Returns:
            众数
        """
        if not values:
            return None
        frequency = defaultdict(int)
        for value in values:
            frequency[value] += 1
        return max(frequency, key=frequency.get)
    
    @staticmethod
    def calculate_variance(values: List[Union[int, float]]) -> float:
        """计算方差
        
        Args:
            values: 数值列表
            
        Returns:
            方差
        """
        if len(values) < 2:
            return 0.0
        mean = CommonMetrics.calculate_mean(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    
    @staticmethod
    def calculate_standard_deviation(values: List[Union[int, float]]) -> float:
        """计算标准差
        
        Args:
            values: 数值列表
            
        Returns:
            标准差
        """
        return math.sqrt(CommonMetrics.calculate_variance(values))
    
    @staticmethod
    def calculate_percentile(values: List[Union[int, float]], percentile: float) -> float:
        """计算百分位数
        
        Args:
            values: 数值列表
            percentile: 百分位数 (0-100)
            
        Returns:
            百分位数对应的值
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    @staticmethod
    def calculate_quartiles(values: List[Union[int, float]]) -> Dict[str, float]:
        """计算四分位数
        
        Args:
            values: 数值列表
            
        Returns:
            包含Q1, Q2, Q3的字典
        """
        sorted_values = sorted(values)
        return {
            'Q1': CommonMetrics.calculate_percentile(sorted_values, 25),
            'Q2': CommonMetrics.calculate_percentile(sorted_values, 50),
            'Q3': CommonMetrics.calculate_percentile(sorted_values, 75)
        }
    
    @staticmethod
    def calculate_correlation(x: List[Union[int, float]], 
                            y: List[Union[int, float]]) -> float:
        """计算相关系数
        
        Args:
            x: x轴数据
            y: y轴数据
            
        Returns:
            相关系数
        """
        if len(x) != len(y) or len(x) == 0:
            return 0.0
        
        mean_x = CommonMetrics.calculate_mean(x)
        mean_y = CommonMetrics.calculate_mean(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(len(y)))
        
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator


class PerformanceMetrics:
    """性能指标计算类"""
    
    @staticmethod
    def calculate_throughput(operations: int, time_seconds: float) -> float:
        """计算吞吐量 (操作/秒)
        
        Args:
            operations: 操作数量
            time_seconds: 时间(秒)
            
        Returns:
            吞吐量
        """
        if time_seconds <= 0:
            return 0.0
        return operations / time_seconds
    
    @staticmethod
    def calculate_latency_percentile(latencies: List[float], percentile: float) -> float:
        """计算延迟百分位数
        
        Args:
            latencies: 延迟列表(毫秒)
            percentile: 百分位数
            
        Returns:
            延迟百分位数
        """
        return CommonMetrics.calculate_percentile(latencies, percentile)
    
    @staticmethod
    def calculate_error_rate(errors: int, total_requests: int) -> float:
        """计算错误率
        
        Args:
            errors: 错误数量
            total_requests: 总请求数
            
        Returns:
            错误率 (0-1)
        """
        if total_requests == 0:
            return 0.0
        return errors / total_requests
    
    @staticmethod
    def calculate_success_rate(successful: int, total: int) -> float:
        """计算成功率
        
        Args:
            successful: 成功数量
            total: 总数量
            
        Returns:
            成功率 (0-1)
        """
        if total == 0:
            return 0.0
        return successful / total


def calculate_summary_statistics(values: List[Union[int, float]]) -> Dict[str, float]:
    """计算汇总统计信息
    
    Args:
        values: 数值列表
        
    Returns:
        包含各种统计指标的字典
    """
    if not values:
        return {}
    
    return {
        'count': len(values),
        'mean': CommonMetrics.calculate_mean(values),
        'median': CommonMetrics.calculate_median(values),
        'min': min(values),
        'max': max(values),
        'range': max(values) - min(values),
        'variance': CommonMetrics.calculate_variance(values),
        'std_dev': CommonMetrics.calculate_standard_deviation(values),
        'q1': CommonMetrics.calculate_percentile(values, 25),
        'q3': CommonMetrics.calculate_percentile(values, 75),
        'iqr': CommonMetrics.calculate_percentile(values, 75) - CommonMetrics.calculate_percentile(values, 25)
    }


def calculate_roc_metrics(true_positives: int, false_positives: int,
                        false_negatives: int, true_negatives: int) -> Dict[str, float]:
    """计算ROC相关指标
    
    Args:
        true_positives: 真阳性
        false_positives: 假阳性
        false_negatives: 假阴性
        true_negatives: 真阴性
        
    Returns:
        ROC相关指标字典
    """
    total = true_positives + false_positives + false_negatives + true_negatives
    
    if total == 0:
        return {'precision': 0.0, 'recall': 0.0, 'f1_score': 0.0, 'accuracy': 0.0}
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (true_positives + true_negatives) / total
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'accuracy': accuracy
    }