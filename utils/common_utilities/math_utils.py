"""
数学工具模块

提供各种数学计算的实用工具函数，包括基础数学、统计、几何、随机数、向量矩阵运算等。
"""

import math
import statistics
import random
import itertools
import numpy as np
from typing import List, Union, Tuple, Optional, Dict, Any, Callable, TypeVar, Generic
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP, getcontext
import cmath


T = TypeVar('T', int, float)


class MathUtils:
    """基础数学工具类"""
    
    # 数学常数
    PI = math.pi
    E = math.e
    TAU = math.tau
    INF = math.inf
    NAN = math.nan
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """限制值在指定范围内
        
        Args:
            value: 要限制的值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            限制后的值
        """
        return max(min_val, min(value, max_val))
    
    @staticmethod
    def lerp(start: float, end: float, t: float) -> float:
        """线性插值
        
        Args:
            start: 起始值
            end: 结束值
            t: 插值参数 (0-1)
            
        Returns:
            插值结果
        """
        return start + (end - start) * MathUtils.clamp(t, 0.0, 1.0)
    
    @staticmethod
    def map_range(value: float, in_min: float, in_max: float, 
                 out_min: float, out_max: float, clamp: bool = True) -> float:
        """值域映射
        
        Args:
            value: 要映射的值
            in_min: 输入最小值
            in_max: 输入最大值
            out_min: 输出最小值
            out_max: 输出最大值
            clamp: 是否限制在输出范围内
            
        Returns:
            映射后的值
        """
        if in_max - in_min == 0:
            return out_min
        
        result = ((value - in_min) / (in_max - in_min)) * (out_max - out_min) + out_min
        
        if clamp:
            return MathUtils.clamp(result, min(out_min, out_max), max(out_min, out_max))
        return result
    
    @staticmethod
    def normalize(value: float, min_val: float, max_val: float) -> float:
        """归一化到 [0, 1] 区间
        
        Args:
            value: 要归一化的值
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            归一化后的值
        """
        return MathUtils.map_range(value, min_val, max_val, 0.0, 1.0)
    
    @staticmethod
    def round_half_up(value: float, decimals: int = 0) -> float:
        """四舍五入（.5向上取整）
        
        Args:
            value: 数值
            decimals: 小数位数
            
        Returns:
            四舍五入后的值
        """
        if decimals == 0:
            return float(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        else:
            format_str = '1.' + '0' * decimals
            return float(Decimal(str(value)).quantize(Decimal(format_str), rounding=ROUND_HALF_UP))
    
    @staticmethod
    def round_half_down(value: float, decimals: int = 0) -> float:
        """四舍五入（.5向下取整）
        
        Args:
            value: 数值
            decimals: 小数位数
            
        Returns:
            四舍五入后的值
        """
        factor = 10 ** decimals
        if value * factor % 1 == 0.5:
            return math.floor(value * factor) / factor
        return round(value, decimals)
    
    @staticmethod
    def round_half_even(value: float, decimals: int = 0) -> float:
        """银行家舍入法（.5取偶数）
        
        Args:
            value: 数值
            decimals: 小数位数
            
        Returns:
            舍入后的值
        """
        return round(value, decimals)
    
    @staticmethod
    def floor_to(value: float, precision: float) -> float:
        """向下取整到指定精度
        
        Args:
            value: 数值
            precision: 精度（如 0.1, 0.01）
            
        Returns:
            取整后的值
        """
        return math.floor(value / precision) * precision
    
    @staticmethod
    def ceil_to(value: float, precision: float) -> float:
        """向上取整到指定精度
        
        Args:
            value: 数值
            precision: 精度
            
        Returns:
            取整后的值
        """
        return math.ceil(value / precision) * precision
    
    @staticmethod
    def round_to(value: float, precision: float) -> float:
        """四舍五入到指定精度
        
        Args:
            value: 数值
            precision: 精度
            
        Returns:
            舍入后的值
        """
        return round(value / precision) * precision
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """安全除法（避免除零）
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 默认值
            
        Returns:
            除法结果
        """
        if denominator == 0:
            return default
        return numerator / denominator
    
    @staticmethod
    def safe_sqrt(x: float, default: float = 0.0) -> float:
        """安全开平方（处理负数）
        
        Args:
            x: 输入值
            default: 默认值
            
        Returns:
            平方根
        """
        if x < 0:
            return default
        return math.sqrt(x)
    
    @staticmethod
    def safe_log(x: float, base: float = math.e, default: float = 0.0) -> float:
        """安全对数（处理负数、零）
        
        Args:
            x: 输入值
            base: 底数
            default: 默认值
            
        Returns:
            对数值
        """
        if x <= 0:
            return default
        return math.log(x, base)
    
    @staticmethod
    def is_close(a: float, b: float, rel_tol: float = 1e-9, abs_tol: float = 0.0) -> bool:
        """判断两个浮点数是否接近
        
        Args:
            a: 第一个数
            b: 第二个数
            rel_tol: 相对容差
            abs_tol: 绝对容差
            
        Returns:
            是否接近
        """
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    
    @staticmethod
    def factorial(n: int) -> int:
        """计算阶乘
        
        Args:
            n: 非负整数
            
        Returns:
            阶乘结果
        """
        if n < 0:
            raise ValueError("阶乘不能计算负数")
        return math.factorial(n)
    
    @staticmethod
    def gcd(a: int, b: int) -> int:
        """计算最大公约数
        
        Args:
            a: 第一个数
            b: 第二个数
            
        Returns:
            最大公约数
        """
        return math.gcd(a, b)
    
    @staticmethod
    def lcm(a: int, b: int) -> int:
        """计算最小公倍数
        
        Args:
            a: 第一个数
            b: 第二个数
            
        Returns:
            最小公倍数
        """
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // MathUtils.gcd(a, b)
    
    @staticmethod
    def is_prime(n: int) -> bool:
        """判断是否为质数
        
        Args:
            n: 要判断的数
            
        Returns:
            是否为质数
        """
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True
    
    @staticmethod
    def prime_factors(n: int) -> List[int]:
        """分解质因数
        
        Args:
            n: 要分解的数
            
        Returns:
            质因数列表
        """
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        return factors
    
    @staticmethod
    def fibonacci(n: int) -> int:
        """计算斐波那契数列第n项
        
        Args:
            n: 项数
            
        Returns:
            斐波那契数
        """
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b
    
    @staticmethod
    def fibonacci_sequence(n: int) -> List[int]:
        """生成斐波那契数列前n项
        
        Args:
            n: 项数
            
        Returns:
            斐波那契数列
        """
        if n <= 0:
            return []
        if n == 1:
            return [0]
        
        seq = [0, 1]
        for i in range(2, n):
            seq.append(seq[i-1] + seq[i-2])
        return seq
    
    @staticmethod
    def is_power_of_two(n: int) -> bool:
        """判断是否为2的幂
        
        Args:
            n: 要判断的数
            
        Returns:
            是否为2的幂
        """
        return n > 0 and (n & (n - 1)) == 0
    
    @staticmethod
    def next_power_of_two(n: int) -> int:
        """获取下一个2的幂
        
        Args:
            n: 基准数
            
        Returns:
            下一个2的幂
        """
        if n <= 0:
            return 1
        return 1 << (n - 1).bit_length()
    
    @staticmethod
    def binomial_coefficient(n: int, k: int) -> int:
        """计算二项式系数 C(n, k)
        
        Args:
            n: 总数
            k: 选择数
            
        Returns:
            二项式系数
        """
        if k < 0 or k > n:
            return 0
        if k == 0 or k == n:
            return 1
        
        k = min(k, n - k)
        result = 1
        for i in range(1, k + 1):
            result = result * (n - k + i) // i
        return result
    
    @staticmethod
    def combination(n: int, k: int) -> int:
        """计算组合数（binomial_coefficient的别名）
        
        Args:
            n: 总数
            k: 选择数
            
        Returns:
            组合数
        """
        return MathUtils.binomial_coefficient(n, k)
    
    @staticmethod
    def permutation(n: int, k: int) -> int:
        """计算排列数 P(n, k)
        
        Args:
            n: 总数
            k: 选择数
            
        Returns:
            排列数
        """
        if k < 0 or k > n:
            return 0
        result = 1
        for i in range(k):
            result *= (n - i)
        return result
    
    @staticmethod
    def sigmoid(x: float) -> float:
        """Sigmoid函数
        
        Args:
            x: 输入值
            
        Returns:
            Sigmoid值 (0-1)
        """
        return 1 / (1 + math.exp(-x))
    
    @staticmethod
    def sigmoid_derivative(x: float) -> float:
        """Sigmoid函数的导数
        
        Args:
            x: 输入值
            
        Returns:
            导数值
        """
        s = MathUtils.sigmoid(x)
        return s * (1 - s)
    
    @staticmethod
    def relu(x: float) -> float:
        """ReLU函数
        
        Args:
            x: 输入值
            
        Returns:
            ReLU值
        """
        return max(0.0, x)
    
    @staticmethod
    def leaky_relu(x: float, alpha: float = 0.01) -> float:
        """Leaky ReLU函数
        
        Args:
            x: 输入值
            alpha: 负半轴斜率
            
        Returns:
            Leaky ReLU值
        """
        return x if x > 0 else alpha * x
    
    @staticmethod
    def elu(x: float, alpha: float = 1.0) -> float:
        """ELU函数
        
        Args:
            x: 输入值
            alpha: 参数
            
        Returns:
            ELU值
        """
        return x if x > 0 else alpha * (math.exp(x) - 1)
    
    @staticmethod
    def tanh(x: float) -> float:
        """双曲正切函数
        
        Args:
            x: 输入值
            
        Returns:
            tanh值
        """
        return math.tanh(x)
    
    @staticmethod
    def softmax(values: List[float]) -> List[float]:
        """Softmax函数
        
        Args:
            values: 输入列表
            
        Returns:
            Softmax概率分布
        """
        if not values:
            return []
        
        # 防止溢出
        max_val = max(values)
        exp_values = [math.exp(v - max_val) for v in values]
        sum_exp = sum(exp_values)
        return [v / sum_exp for v in exp_values]
    
    @staticmethod
    def log_softmax(values: List[float]) -> List[float]:
        """Log-Softmax函数
        
        Args:
            values: 输入列表
            
        Returns:
            Log-Softmax值
        """
        if not values:
            return []
        
        max_val = max(values)
        shifted = [v - max_val for v in values]
        log_sum = math.log(sum(math.exp(v) for v in shifted))
        return [v - log_sum for v in shifted]
    
    @staticmethod
    def mse(y_true: List[float], y_pred: List[float]) -> float:
        """均方误差
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            均方误差
        """
        if len(y_true) != len(y_pred) or not y_true:
            return 0.0
        
        n = len(y_true)
        return sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)) / n
    
    @staticmethod
    def mae(y_true: List[float], y_pred: List[float]) -> float:
        """平均绝对误差
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            平均绝对误差
        """
        if len(y_true) != len(y_pred) or not y_true:
            return 0.0
        
        n = len(y_true)
        return sum(abs(yt - yp) for yt, yp in zip(y_true, y_pred)) / n
    
    @staticmethod
    def rmse(y_true: List[float], y_pred: List[float]) -> float:
        """均方根误差
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            均方根误差
        """
        return math.sqrt(MathUtils.mse(y_true, y_pred))
    
    @staticmethod
    def r2_score(y_true: List[float], y_pred: List[float]) -> float:
        """R²决定系数
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            R²值
        """
        if len(y_true) != len(y_pred) or not y_true:
            return 0.0
        
        mean_y = sum(y_true) / len(y_true)
        ss_res = sum((yt - yp) ** 2 for yt, yp in zip(y_true, y_pred))
        ss_tot = sum((yt - mean_y) ** 2 for yt in y_true)
        
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        
        return 1 - ss_res / ss_tot


class StatisticsUtils:
    """统计工具类"""
    
    @staticmethod
    def mean(values: List[Union[int, float]]) -> float:
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
    def median(values: List[Union[int, float]]) -> float:
        """计算中位数
        
        Args:
            values: 数值列表
            
        Returns:
            中位数
        """
        if not values:
            return 0.0
        return statistics.median(values)
    
    @staticmethod
    def mode(values: List[Any]) -> Any:
        """计算众数
        
        Args:
            values: 值列表
            
        Returns:
            众数
        """
        try:
            return statistics.mode(values)
        except statistics.StatisticsError:
            return None
    
    @staticmethod
    def multimode(values: List[Any]) -> List[Any]:
        """计算多个众数
        
        Args:
            values: 值列表
            
        Returns:
            众数列表
        """
        return statistics.multimode(values)
    
    @staticmethod
    def quantiles(values: List[Union[int, float]], n: int = 4) -> List[float]:
        """计算分位数
        
        Args:
            values: 数值列表
            n: 分位数数量（4=四分位数）
            
        Returns:
            分位数列表
        """
        if not values or n < 2:
            return []
        return statistics.quantiles(values, n=n)
    
    @staticmethod
    def percentile(values: List[Union[int, float]], p: float) -> float:
        """计算百分位数
        
        Args:
            values: 数值列表
            p: 百分位数 (0-100)
            
        Returns:
            百分位数
        """
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        
        if f == c:
            return sorted_values[int(k)]
        
        d0 = sorted_values[int(f)] * (c - k)
        d1 = sorted_values[int(c)] * (k - f)
        return d0 + d1
    
    @staticmethod
    def quartiles(values: List[Union[int, float]]) -> Tuple[float, float, float]:
        """计算四分位数
        
        Args:
            values: 数值列表
            
        Returns:
            (Q1, Q2, Q3)
        """
        q1 = StatisticsUtils.percentile(values, 25)
        q2 = StatisticsUtils.percentile(values, 50)
        q3 = StatisticsUtils.percentile(values, 75)
        return q1, q2, q3
    
    @staticmethod
    def variance(values: List[Union[int, float]], sample: bool = True) -> float:
        """计算方差
        
        Args:
            values: 数值列表
            sample: 是否为样本方差
            
        Returns:
            方差
        """
        if len(values) < 2:
            return 0.0
        
        if sample:
            return statistics.variance(values)
        else:
            return statistics.pvariance(values)
    
    @staticmethod
    def std_dev(values: List[Union[int, float]], sample: bool = True) -> float:
        """计算标准差
        
        Args:
            values: 数值列表
            sample: 是否为样本标准差
            
        Returns:
            标准差
        """
        return math.sqrt(StatisticsUtils.variance(values, sample))
    
    @staticmethod
    def zscore(value: float, mean: float, std_dev: float) -> float:
        """计算Z分数
        
        Args:
            value: 原始值
            mean: 均值
            std_dev: 标准差
            
        Returns:
            Z分数
        """
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev
    
    @staticmethod
    def standardize(values: List[float]) -> List[float]:
        """标准化（Z-Score）
        
        Args:
            values: 数值列表
            
        Returns:
            标准化后的列表
        """
        if not values:
            return []
        
        mean = StatisticsUtils.mean(values)
        std = StatisticsUtils.std_dev(values)
        
        if std == 0:
            return [0.0] * len(values)
        
        return [(x - mean) / std for x in values]
    
    @staticmethod
    def covariance(x: List[float], y: List[float], sample: bool = True) -> float:
        """计算协方差
        
        Args:
            x: X值列表
            y: Y值列表
            sample: 是否为样本协方差
            
        Returns:
            协方差
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        mean_x = StatisticsUtils.mean(x)
        mean_y = StatisticsUtils.mean(y)
        
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        
        if sample:
            return cov / (len(x) - 1)
        else:
            return cov / len(x)
    
    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """计算相关系数
        
        Args:
            x: X值列表
            y: Y值列表
            
        Returns:
            相关系数
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        return statistics.correlation(x, y)
    
    @staticmethod
    def linear_regression(x: List[float], y: List[float]) -> Tuple[float, float, float]:
        """线性回归
        
        Args:
            x: X值列表
            y: Y值列表
            
        Returns:
            (斜率, 截距, R²)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0, 0.0, 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0, 0.0, 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # 计算R²
        y_pred = [slope * xi + intercept for xi in x]
        r2 = MathUtils.r2_score(y, y_pred)
        
        return slope, intercept, r2
    
    @staticmethod
    def skewness(values: List[float]) -> float:
        """计算偏度
        
        Args:
            values: 数值列表
            
        Returns:
            偏度
        """
        if len(values) < 3:
            return 0.0
        
        mean = StatisticsUtils.mean(values)
        std = StatisticsUtils.std_dev(values, sample=False)
        
        if std == 0:
            return 0.0
        
        n = len(values)
        skew = sum((x - mean) ** 3 for x in values) / n
        skew = skew / (std ** 3)
        
        return skew
    
    @staticmethod
    def kurtosis(values: List[float]) -> float:
        """计算峰度
        
        Args:
            values: 数值列表
            
        Returns:
            峰度
        """
        if len(values) < 4:
            return 0.0
        
        mean = StatisticsUtils.mean(values)
        std = StatisticsUtils.std_dev(values, sample=False)
        
        if std == 0:
            return 0.0
        
        n = len(values)
        kurt = sum((x - mean) ** 4 for x in values) / n
        kurt = kurt / (std ** 4) - 3
        
        return kurt
    
    @staticmethod
    def geometric_mean(values: List[Union[int, float]]) -> float:
        """几何平均数
        
        Args:
            values: 数值列表（必须为正数）
            
        Returns:
            几何平均数
        """
        if not values or any(v <= 0 for v in values):
            return 0.0
        
        product = 1.0
        for v in values:
            product *= v
        
        return product ** (1.0 / len(values))
    
    @staticmethod
    def harmonic_mean(values: List[Union[int, float]]) -> float:
        """调和平均数
        
        Args:
            values: 数值列表（必须为正数）
            
        Returns:
            调和平均数
        """
        if not values or any(v <= 0 for v in values):
            return 0.0
        
        return len(values) / sum(1.0 / v for v in values)
    
    @staticmethod
    def weighted_mean(values: List[Union[int, float]], 
                     weights: List[Union[int, float]]) -> float:
        """加权平均数
        
        Args:
            values: 数值列表
            weights: 权重列表
            
        Returns:
            加权平均数
        """
        if len(values) != len(weights) or not values:
            return 0.0
        
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        
        return sum(v * w for v, w in zip(values, weights)) / total_weight
    
    @staticmethod
    def moving_average(values: List[float], window: int) -> List[float]:
        """移动平均
        
        Args:
            values: 数值列表
            window: 窗口大小
            
        Returns:
            移动平均值列表
        """
        if len(values) < window:
            return []
        
        result = []
        for i in range(len(values) - window + 1):
            avg = sum(values[i:i+window]) / window
            result.append(avg)
        
        return result
    
    @staticmethod
    def exponential_moving_average(values: List[float], alpha: float) -> List[float]:
        """指数移动平均
        
        Args:
            values: 数值列表
            alpha: 平滑因子 (0-1)
            
        Returns:
            指数移动平均值列表
        """
        if not values:
            return []
        
        ema = [values[0]]
        for i in range(1, len(values)):
            ema.append(alpha * values[i] + (1 - alpha) * ema[-1])
        
        return ema
    
    @staticmethod
    def median_absolute_deviation(values: List[float]) -> float:
        """中位数绝对偏差
        
        Args:
            values: 数值列表
            
        Returns:
            MAD
        """
        if not values:
            return 0.0
        
        median_val = StatisticsUtils.median(values)
        deviations = [abs(x - median_val) for x in values]
        return StatisticsUtils.median(deviations)


class RandomUtils:
    """随机数工具类"""
    
    @staticmethod
    def random_int(min_val: int = 0, max_val: int = 100) -> int:
        """生成随机整数
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            随机整数
        """
        return random.randint(min_val, max_val)
    
    @staticmethod
    def random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
        """生成随机浮点数
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            随机浮点数
        """
        return random.uniform(min_val, max_val)
    
    @staticmethod
    def random_gaussian(mean: float = 0.0, std_dev: float = 1.0) -> float:
        """生成高斯分布随机数
        
        Args:
            mean: 均值
            std_dev: 标准差
            
        Returns:
            随机数
        """
        return random.gauss(mean, std_dev)
    
    @staticmethod
    def random_choice(items: List[Any]) -> Any:
        """从列表中随机选择一项
        
        Args:
            items: 选择列表
            
        Returns:
            随机选择的项目
        """
        return random.choice(items) if items else None
    
    @staticmethod
    def random_choices(items: List[Any], weights: Optional[List[float]] = None, 
                      k: int = 1) -> List[Any]:
        """从列表中随机选择多项（可重复）
        
        Args:
            items: 选择列表
            weights: 权重列表
            k: 选择数量
            
        Returns:
            随机选择的项目列表
        """
        if not items:
            return []
        return random.choices(items, weights=weights, k=k)
    
    @staticmethod
    def random_sample(items: List[Any], k: int) -> List[Any]:
        """从列表中随机采样（不重复）
        
        Args:
            items: 选择列表
            k: 采样数量
            
        Returns:
            采样结果
        """
        if not items or k <= 0:
            return []
        if k >= len(items):
            return items.copy()
        return random.sample(items, k)
    
    @staticmethod
    def shuffle(items: List[Any]) -> List[Any]:
        """随机打乱列表
        
        Args:
            items: 要打乱的列表
            
        Returns:
            打乱后的列表
        """
        shuffled = items.copy()
        random.shuffle(shuffled)
        return shuffled
    
    @staticmethod
    def random_bool(probability: float = 0.5) -> bool:
        """生成随机布尔值
        
        Args:
            probability: 为True的概率
            
        Returns:
            随机布尔值
        """
        return random.random() < probability
    
    @staticmethod
    def random_string(length: int, 
                     chars: str = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') -> str:
        """生成随机字符串
        
        Args:
            length: 字符串长度
            chars: 字符集
            
        Returns:
            随机字符串
        """
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def random_hex(length: int) -> str:
        """生成随机十六进制字符串
        
        Args:
            length: 长度
            
        Returns:
            随机十六进制字符串
        """
        return RandomUtils.random_string(length, '0123456789abcdef')
    
    @staticmethod
    def random_uuid4() -> str:
        """生成随机UUID v4
        
        Returns:
            UUID字符串
        """
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def random_seed(seed: Optional[int] = None):
        """设置随机种子
        
        Args:
            seed: 随机种子
        """
        random.seed(seed)
    
    @staticmethod
    def random_permutation(n: int) -> List[int]:
        """生成0到n-1的随机排列
        
        Args:
            n: 范围
            
        Returns:
            随机排列列表
        """
        perm = list(range(n))
        random.shuffle(perm)
        return perm


class GeometryUtils:
    """几何工具类"""
    
    @staticmethod
    def distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """计算两点间距离
        
        Args:
            point1: 第一个点坐标 (x1, y1)
            point2: 第二个点坐标 (x2, y2)
            
        Returns:
            距离
        """
        x1, y1 = point1
        x2, y2 = point2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    @staticmethod
    def distance_3d(point1: Tuple[float, float, float], 
                   point2: Tuple[float, float, float]) -> float:
        """计算三维空间两点间距离
        
        Args:
            point1: 第一个点坐标 (x1, y1, z1)
            point2: 第二个点坐标 (x2, y2, z2)
            
        Returns:
            距离
        """
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
    
    @staticmethod
    def midpoint(point1: Tuple[float, float], point2: Tuple[float, float]) -> Tuple[float, float]:
        """计算中点
        
        Args:
            point1: 第一个点
            point2: 第二个点
            
        Returns:
            中点坐标
        """
        x1, y1 = point1
        x2, y2 = point2
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    @staticmethod
    def slope(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """计算斜率
        
        Args:
            point1: 第一个点
            point2: 第二个点
            
        Returns:
            斜率
        """
        x1, y1 = point1
        x2, y2 = point2
        if x2 - x1 == 0:
            return float('inf')
        return (y2 - y1) / (x2 - x1)
    
    @staticmethod
    def line_equation(point1: Tuple[float, float], point2: Tuple[float, float]) -> Tuple[float, float]:
        """计算直线方程 y = ax + b
        
        Args:
            point1: 第一个点
            point2: 第二个点
            
        Returns:
            (a, b) 直线参数
        """
        x1, y1 = point1
        x2, y2 = point2
        if x2 - x1 == 0:
            return float('inf'), x1
        a = (y2 - y1) / (x2 - x1)
        b = y1 - a * x1
        return a, b
    
    @staticmethod
    def angle_between(v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
        """计算两个向量之间的夹角（弧度）
        
        Args:
            v1: 向量1 (x1, y1)
            v2: 向量2 (x2, y2)
            
        Returns:
            夹角（弧度）
        """
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        norm1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        norm2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cos_angle = dot / (norm1 * norm2)
        # 处理浮点误差
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(cos_angle)
    
    @staticmethod
    def angle_between_3d(v1: Tuple[float, float, float], 
                        v2: Tuple[float, float, float]) -> float:
        """计算三维向量夹角（弧度）
        
        Args:
            v1: 向量1 (x1, y1, z1)
            v2: 向量2 (x2, y2, z2)
            
        Returns:
            夹角（弧度）
        """
        dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
        norm1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
        norm2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        cos_angle = dot / (norm1 * norm2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        return math.acos(cos_angle)
    
    @staticmethod
    def triangle_area(a: Tuple[float, float], b: Tuple[float, float], 
                     c: Tuple[float, float]) -> float:
        """计算三角形面积
        
        Args:
            a, b, c: 三角形三个顶点
            
        Returns:
            面积
        """
        x1, y1 = a
        x2, y2 = b
        x3, y3 = c
        return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0)
    
    @staticmethod
    def circle_area(radius: float) -> float:
        """计算圆形面积
        
        Args:
            radius: 半径
            
        Returns:
            面积
        """
        return math.pi * radius ** 2
    
    @staticmethod
    def circle_circumference(radius: float) -> float:
        """计算圆形周长
        
        Args:
            radius: 半径
            
        Returns:
            周长
        """
        return 2 * math.pi * radius
    
    @staticmethod
    def rectangle_area(width: float, height: float) -> float:
        """计算矩形面积
        
        Args:
            width: 宽度
            height: 高度
            
        Returns:
            面积
        """
        return width * height
    
    @staticmethod
    def rectangle_perimeter(width: float, height: float) -> float:
        """计算矩形周长
        
        Args:
            width: 宽度
            height: 高度
            
        Returns:
            周长
        """
        return 2 * (width + height)
    
    @staticmethod
    def triangle_area_base_height(base: float, height: float) -> float:
        """计算三角形面积（底和高）
        
        Args:
            base: 底边长度
            height: 高度
            
        Returns:
            面积
        """
        return 0.5 * base * height
    
    @staticmethod
    def trapezoid_area(top: float, bottom: float, height: float) -> float:
        """计算梯形面积
        
        Args:
            top: 上底
            bottom: 下底
            height: 高
            
        Returns:
            面积
        """
        return (top + bottom) * height / 2
    
    @staticmethod
    def sphere_volume(radius: float) -> float:
        """计算球体体积
        
        Args:
            radius: 半径
            
        Returns:
            体积
        """
        return 4 / 3 * math.pi * radius ** 3
    
    @staticmethod
    def sphere_surface_area(radius: float) -> float:
        """计算球体表面积
        
        Args:
            radius: 半径
            
        Returns:
            表面积
        """
        return 4 * math.pi * radius ** 2
    
    @staticmethod
    def cylinder_volume(radius: float, height: float) -> float:
        """计算圆柱体体积
        
        Args:
            radius: 半径
            height: 高度
            
        Returns:
            体积
        """
        return math.pi * radius ** 2 * height
    
    @staticmethod
    def cone_volume(radius: float, height: float) -> float:
        """计算圆锥体体积
        
        Args:
            radius: 半径
            height: 高度
            
        Returns:
            体积
        """
        return math.pi * radius ** 2 * height / 3
    
    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """角度转弧度
        
        Args:
            degrees: 角度
            
        Returns:
            弧度
        """
        return math.radians(degrees)
    
    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """弧度转角度
        
        Args:
            radians: 弧度
            
        Returns:
            角度
        """
        return math.degrees(radians)
    
    @staticmethod
    def normalize_angle(angle: float, degrees: bool = True) -> float:
        """归一化角度到 [0, 360) 或 [0, 2π)
        
        Args:
            angle: 角度
            degrees: 是否为角度制
            
        Returns:
            归一化后的角度
        """
        if degrees:
            return angle % 360
        else:
            return angle % (2 * math.pi)


class VectorUtils:
    """向量运算工具类"""
    
    @staticmethod
    def dot_product(v1: List[float], v2: List[float]) -> float:
        """计算点积
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            点积
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度不匹配")
        return sum(a * b for a, b in zip(v1, v2))
    
    @staticmethod
    def cross_product(v1: List[float], v2: List[float]) -> List[float]:
        """计算叉积（三维）
        
        Args:
            v1: 三维向量1
            v2: 三维向量2
            
        Returns:
            叉积向量
        """
        if len(v1) != 3 or len(v2) != 3:
            raise ValueError("叉积仅支持三维向量")
        
        return [
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0]
        ]
    
    @staticmethod
    def norm(v: List[float]) -> float:
        """计算向量模长
        
        Args:
            v: 向量
            
        Returns:
            模长
        """
        return math.sqrt(sum(x * x for x in v))
    
    @staticmethod
    def normalize(v: List[float]) -> List[float]:
        """向量归一化
        
        Args:
            v: 向量
            
        Returns:
            单位向量
        """
        norm = VectorUtils.norm(v)
        if norm == 0:
            return v
        return [x / norm for x in v]
    
    @staticmethod
    def add(v1: List[float], v2: List[float]) -> List[float]:
        """向量加法
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            和向量
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度不匹配")
        return [a + b for a, b in zip(v1, v2)]
    
    @staticmethod
    def subtract(v1: List[float], v2: List[float]) -> List[float]:
        """向量减法
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            差向量
        """
        if len(v1) != len(v2):
            raise ValueError("向量维度不匹配")
        return [a - b for a, b in zip(v1, v2)]
    
    @staticmethod
    def multiply(v: List[float], scalar: float) -> List[float]:
        """向量数乘
        
        Args:
            v: 向量
            scalar: 标量
            
        Returns:
            数乘结果
        """
        return [x * scalar for x in v]
    
    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            余弦相似度 (-1 到 1)
        """
        dot = VectorUtils.dot_product(v1, v2)
        norm1 = VectorUtils.norm(v1)
        norm2 = VectorUtils.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    @staticmethod
    def euclidean_distance(v1: List[float], v2: List[float]) -> float:
        """计算欧氏距离
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            欧氏距离
        """
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    
    @staticmethod
    def manhattan_distance(v1: List[float], v2: List[float]) -> float:
        """计算曼哈顿距离
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            曼哈顿距离
        """
        return sum(abs(a - b) for a, b in zip(v1, v2))
    
    @staticmethod
    def chebyshev_distance(v1: List[float], v2: List[float]) -> float:
        """计算切比雪夫距离
        
        Args:
            v1: 向量1
            v2: 向量2
            
        Returns:
            切比雪夫距离
        """
        return max(abs(a - b) for a, b in zip(v1, v2))
    
    @staticmethod
    def minkowski_distance(v1: List[float], v2: List[float], p: float = 3) -> float:
        """计算闵可夫斯基距离
        
        Args:
            v1: 向量1
            v2: 向量2
            p: 阶数
            
        Returns:
            闵可夫斯基距离
        """
        return sum(abs(a - b) ** p for a, b in zip(v1, v2)) ** (1 / p)
    
    @staticmethod
    def projection(v: List[float], onto: List[float]) -> List[float]:
        """计算向量投影
        
        Args:
            v: 向量
            onto: 投影到的向量
            
        Returns:
            投影向量
        """
        dot = VectorUtils.dot_product(v, onto)
        norm_sq = VectorUtils.dot_product(onto, onto)
        
        if norm_sq == 0:
            return [0.0] * len(v)
        
        scalar = dot / norm_sq
        return [scalar * x for x in onto]


class MatrixUtils:
    """矩阵运算工具类"""
    
    @staticmethod
    def create(rows: int, cols: int, default: float = 0.0) -> List[List[float]]:
        """创建矩阵
        
        Args:
            rows: 行数
            cols: 列数
            default: 默认值
            
        Returns:
            矩阵
        """
        return [[default for _ in range(cols)] for _ in range(rows)]
    
    @staticmethod
    def identity(n: int) -> List[List[float]]:
        """创建单位矩阵
        
        Args:
            n: 维度
            
        Returns:
            单位矩阵
        """
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    @staticmethod
    def zeros(rows: int, cols: int) -> List[List[float]]:
        """创建零矩阵
        
        Args:
            rows: 行数
            cols: 列数
            
        Returns:
            零矩阵
        """
        return MatrixUtils.create(rows, cols, 0.0)
    
    @staticmethod
    def ones(rows: int, cols: int) -> List[List[float]]:
        """创建全1矩阵
        
        Args:
            rows: 行数
            cols: 列数
            
        Returns:
            全1矩阵
        """
        return MatrixUtils.create(rows, cols, 1.0)
    
    @staticmethod
    def diagonal(values: List[float]) -> List[List[float]]:
        """创建对角矩阵
        
        Args:
            values: 对角线值
            
        Returns:
            对角矩阵
        """
        n = len(values)
        return [[values[i] if i == j else 0.0 for j in range(n)] for i in range(n)]
    
    @staticmethod
    def transpose(matrix: List[List[float]]) -> List[List[float]]:
        """矩阵转置
        
        Args:
            matrix: 原矩阵
            
        Returns:
            转置矩阵
        """
        if not matrix:
            return []
        
        rows = len(matrix)
        cols = len(matrix[0])
        
        return [[matrix[i][j] for i in range(rows)] for j in range(cols)]
    
    @staticmethod
    def multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """矩阵乘法
        
        Args:
            A: 矩阵A (m x n)
            B: 矩阵B (n x p)
            
        Returns:
            结果矩阵 (m x p)
        """
        if not A or not B:
            return []
        
        m = len(A)
        n = len(A[0])
        p = len(B[0])
        
        if n != len(B):
            raise ValueError("矩阵维度不匹配")
        
        result = [[0.0 for _ in range(p)] for _ in range(m)]
        
        for i in range(m):
            for j in range(p):
                for k in range(n):
                    result[i][j] += A[i][k] * B[k][j]
        
        return result
    
    @staticmethod
    def add(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """矩阵加法
        
        Args:
            A: 矩阵A
            B: 矩阵B
            
        Returns:
            和矩阵
        """
        if len(A) != len(B) or len(A[0]) != len(B[0]):
            raise ValueError("矩阵维度不匹配")
        
        rows = len(A)
        cols = len(A[0])
        
        return [[A[i][j] + B[i][j] for j in range(cols)] for i in range(rows)]
    
    @staticmethod
    def subtract(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """矩阵减法
        
        Args:
            A: 矩阵A
            B: 矩阵B
            
        Returns:
            差矩阵
        """
        if len(A) != len(B) or len(A[0]) != len(B[0]):
            raise ValueError("矩阵维度不匹配")
        
        rows = len(A)
        cols = len(A[0])
        
        return [[A[i][j] - B[i][j] for j in range(cols)] for i in range(rows)]
    
    @staticmethod
    def scalar_multiply(matrix: List[List[float]], scalar: float) -> List[List[float]]:
        """矩阵数乘
        
        Args:
            matrix: 矩阵
            scalar: 标量
            
        Returns:
            数乘结果
        """
        rows = len(matrix)
        cols = len(matrix[0]) if rows > 0 else 0
        
        return [[matrix[i][j] * scalar for j in range(cols)] for i in range(rows)]
    
    @staticmethod
    def trace(matrix: List[List[float]]) -> float:
        """计算矩阵的迹
        
        Args:
            matrix: 方阵
            
        Returns:
            迹
        """
        n = len(matrix)
        return sum(matrix[i][i] for i in range(n))
    
    @staticmethod
    def determinant(matrix: List[List[float]]) -> float:
        """计算矩阵的行列式（2x2 和 3x3）
        
        Args:
            matrix: 方阵
            
        Returns:
            行列式
        """
        n = len(matrix)
        
        if n == 2:
            return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        elif n == 3:
            a, b, c = matrix[0]
            d, e, f = matrix[1]
            g, h, i = matrix[2]
            return (a * e * i + b * f * g + c * d * h -
                   c * e * g - b * d * i - a * f * h)
        else:
            raise ValueError("只支持2x2和3x3矩阵的行列式计算")
    
    @staticmethod
    def inverse_2x2(matrix: List[List[float]]) -> List[List[float]]:
        """计算2x2矩阵的逆
        
        Args:
            matrix: 2x2矩阵
            
        Returns:
            逆矩阵
        """
        det = MatrixUtils.determinant(matrix)
        if det == 0:
            raise ValueError("矩阵不可逆")
        
        a, b = matrix[0]
        c, d = matrix[1]
        
        inv_det = 1.0 / det
        return [
            [d * inv_det, -b * inv_det],
            [-c * inv_det, a * inv_det]
        ]
    
    @staticmethod
    def hadamard_product(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
        """Hadamard乘积（逐元素相乘）
        
        Args:
            A: 矩阵A
            B: 矩阵B
            
        Returns:
            逐元素乘积矩阵
        """
        if len(A) != len(B) or len(A[0]) != len(B[0]):
            raise ValueError("矩阵维度不匹配")
        
        rows = len(A)
        cols = len(A[0])
        
        return [[A[i][j] * B[i][j] for j in range(cols)] for i in range(rows)]
    
    @staticmethod
    def flatten(matrix: List[List[float]]) -> List[float]:
        """将矩阵展平为一维列表
        
        Args:
            matrix: 矩阵
            
        Returns:
            一维列表
        """
        return [elem for row in matrix for elem in row]
    
    @staticmethod
    def reshape(vector: List[float], rows: int, cols: int) -> List[List[float]]:
        """将一维向量重塑为矩阵
        
        Args:
            vector: 一维向量
            rows: 行数
            cols: 列数
            
        Returns:
            矩阵
        """
        if len(vector) != rows * cols:
            raise ValueError("元素数量不匹配")
        
        return [[vector[i * cols + j] for j in range(cols)] for i in range(rows)]


class ComplexUtils:
    """复数运算工具类"""
    
    @staticmethod
    def magnitude(z: complex) -> float:
        """计算复数的模
        
        Args:
            z: 复数
            
        Returns:
            模长
        """
        return abs(z)
    
    @staticmethod
    def phase(z: complex) -> float:
        """计算复数的辐角（弧度）
        
        Args:
            z: 复数
            
        Returns:
            辐角
        """
        return cmath.phase(z)
    
    @staticmethod
    def conjugate(z: complex) -> complex:
        """计算共轭复数
        
        Args:
            z: 复数
            
        Returns:
            共轭复数
        """
        return z.conjugate()
    
    @staticmethod
    def polar(z: complex) -> Tuple[float, float]:
        """转换为极坐标形式
        
        Args:
            z: 复数
            
        Returns:
            (模, 辐角)
        """
        return cmath.polar(z)
    
    @staticmethod
    def rect(r: float, phi: float) -> complex:
        """从极坐标创建复数
        
        Args:
            r: 模
            phi: 辐角
            
        Returns:
            复数
        """
        return cmath.rect(r, phi)


def percentage(value: float, total: float, decimals: int = 2) -> float:
    """计算百分比
    
    Args:
        value: 数值
        total: 总数
        decimals: 小数位数
        
    Returns:
        百分比
    """
    if total == 0:
        return 0.0
    return round((value / total) * 100, decimals)


def ratio(value1: float, value2: float, decimals: int = 4) -> float:
    """计算比率
    
    Args:
        value1: 第一个值
        value2: 第二个值
        decimals: 小数位数
        
    Returns:
        比率
    """
    if value2 == 0:
        return float('inf')
    return round(value1 / value2, decimals)


def is_even(n: int) -> bool:
    """判断是否为偶数
    
    Args:
        n: 要判断的数
        
    Returns:
        是否为偶数
    """
    return n % 2 == 0


def is_odd(n: int) -> bool:
    """判断是否为奇数
    
    Args:
        n: 要判断的数
        
    Returns:
        是否为奇数
    """
    return n % 2 == 1


def format_number(number: float, decimals: int = 2, thousands_sep: str = ',') -> str:
    """格式化数字
    
    Args:
        number: 数字
        decimals: 小数位数
        thousands_sep: 千位分隔符
        
    Returns:
        格式化后的字符串
    """
    formatted = f"{number:,.{decimals}f}"
    return formatted.replace(',', thousands_sep) if thousands_sep != ',' else formatted


def format_percentage(value: float, total: float, decimals: int = 2) -> str:
    """格式化为百分比字符串
    
    Args:
        value: 数值
        total: 总数
        decimals: 小数位数
        
    Returns:
        百分比字符串
    """
    pct = percentage(value, total, decimals)
    return f"{pct}%"


def clamp_int(value: int, min_val: int, max_val: int) -> int:
    """限制整数在指定范围内
    
    Args:
        value: 要限制的值
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        限制后的值
    """
    return max(min_val, min(value, max_val))


def lerp_int(start: int, end: int, t: float) -> int:
    """整数线性插值
    
    Args:
        start: 起始值
        end: 结束值
        t: 插值参数
        
    Returns:
        插值结果（取整）
    """
    return int(round(MathUtils.lerp(start, end, t)))


def golden_ratio() -> float:
    """获取黄金比例
    
    Returns:
        黄金比例 (1.618...)
    """
    return (1 + math.sqrt(5)) / 2


def fibonacci_sphere(n: int) -> List[Tuple[float, float, float]]:
    """生成球面上均匀分布的点（斐波那契球体算法）
    
    Args:
        n: 点的数量
        
    Returns:
        球面上的点列表 (x, y, z)
    """
    points = []
    phi = math.pi * (3 - math.sqrt(5))  # 黄金角
    
    for i in range(n):
        y = 1 - (i / (n - 1)) * 2  # y 从 1 到 -1
        radius = math.sqrt(1 - y * y)  # 在 y 处的半径
        
        theta = phi * i
        
        x = math.cos(theta) * radius
        z = math.sin(theta) * radius
        
        points.append((x, y, z))
    
    return points


def sigmoid_derivative_from_output(output: float) -> float:
    """从Sigmoid输出计算导数
    
    Args:
        output: Sigmoid输出值
        
    Returns:
        导数值
    """
    return output * (1 - output)


def softmax_derivative(softmax_output: List[float]) -> List[List[float]]:
    """计算Softmax的雅可比矩阵
    
    Args:
        softmax_output: Softmax输出
        
    Returns:
        雅可比矩阵
    """
    n = len(softmax_output)
    jacobian = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i == j:
                jacobian[i][j] = softmax_output[i] * (1 - softmax_output[i])
            else:
                jacobian[i][j] = -softmax_output[i] * softmax_output[j]
    
    return jacobian