"""
数据采样工具模块

提供各种数据采样方法，包括随机采样、分层采样、系统采样、聚类采样等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from sklearn.model_selection import train_test_split, StratifiedKFold, KFold
from sklearn.cluster import KMeans
from imblearn.over_sampling import SMOTE, ADASYN, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler, NearMiss, TomekLinks
import logging
from datetime import datetime
import random
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RandomSampler:
    """随机采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化随机采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
        random.seed(random_state)
    
    def sample(self, data: Union[pd.DataFrame, pd.Series], 
               n: Optional[int] = None,
               frac: Optional[float] = None,
               replace: bool = False) -> Union[pd.DataFrame, pd.Series]:
        """随机采样
        
        Args:
            data: 输入数据
            n: 采样数量
            frac: 采样比例
            replace: 是否放回采样
            
        Returns:
            采样结果
        """
        if isinstance(data, pd.DataFrame):
            if n is not None:
                return data.sample(n=n, replace=replace, random_state=self.random_state)
            elif frac is not None:
                return data.sample(frac=frac, replace=replace, random_state=self.random_state)
            else:
                raise ValueError("必须指定 n 或 frac 参数")
        else:
            if n is not None:
                indices = np.random.choice(len(data), n, replace=replace)
                return data.iloc[indices]
            elif frac is not None:
                n = int(len(data) * frac)
                indices = np.random.choice(len(data), n, replace=replace)
                return data.iloc[indices]
            else:
                raise ValueError("必须指定 n 或 frac 参数")


class StratifiedSampler:
    """分层采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化分层采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample(self, data: pd.DataFrame, stratify_column: str,
               n: Optional[int] = None,
               frac: Optional[float] = None) -> pd.DataFrame:
        """分层采样
        
        Args:
            data: 输入数据
            stratify_column: 分层依据的列名
            n: 采样数量
            frac: 采样比例
            
        Returns:
            分层采样结果
        """
        if stratify_column not in data.columns:
            raise ValueError(f"列 '{stratify_column}' 不存在于数据中")
        
        # 计算各层的采样数量
        value_counts = data[stratify_column].value_counts()
        total_size = len(data)
        
        if n is not None:
            sample_sizes = {}
            for value, count in value_counts.items():
                # 按比例分配采样数量
                proportion = count / total_size
                sample_sizes[value] = max(1, int(n * proportion))
        elif frac is not None:
            sample_sizes = {}
            for value, count in value_counts.items():
                sample_sizes[value] = max(1, int(count * frac))
        else:
            raise ValueError("必须指定 n 或 frac 参数")
        
        # 执行分层采样
        sampled_dfs = []
        for value, sample_size in sample_sizes.items():
            subset = data[data[stratify_column] == value]
            if len(subset) > 0:
                sampled_subset = subset.sample(
                    n=min(sample_size, len(subset)),
                    replace=False,
                    random_state=self.random_state
                )
                sampled_dfs.append(sampled_subset)
        
        if sampled_dfs:
            result = pd.concat(sampled_dfs, ignore_index=True)
            return result.sort_index()
        else:
            return pd.DataFrame()
    
    def train_test_split(self, data: pd.DataFrame, stratify_column: str,
                        test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """分层训练测试集分割"""
        from sklearn.model_selection import train_test_split
        
        train, test = train_test_split(
            data,
            test_size=test_size,
            stratify=data[stratify_column],
            random_state=self.random_state
        )
        
        return train, test


class SystematicSampler:
    """系统采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化系统采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample(self, data: Union[pd.DataFrame, pd.Series],
               interval: int,
               start: int = 0) -> Union[pd.DataFrame, pd.Series]:
        """系统采样
        
        Args:
            data: 输入数据
            interval: 采样间隔
            start: 起始位置
            
        Returns:
            系统采样结果
        """
        indices = list(range(start, len(data), interval))
        
        if isinstance(data, pd.DataFrame):
            return data.iloc[indices]
        else:
            return data.iloc[indices]
    
    def random_start_systematic(self, data: Union[pd.DataFrame, pd.Series],
                               interval: int) -> Union[pd.DataFrame, pd.Series]:
        """随机起始系统采样"""
        start = np.random.randint(0, interval)
        return self.sample(data, interval, start)


class ClusterSampler:
    """聚类采样器"""
    
    def __init__(self, n_clusters: int = 5, random_state: int = 42):
        """初始化聚类采样器"""
        self.n_clusters = n_clusters
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample(self, data: pd.DataFrame,
              sample_per_cluster: Optional[int] = None,
              fraction_per_cluster: Optional[float] = None,
              feature_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """聚类采样
        
        Args:
            data: 输入数据
            sample_per_cluster: 每个聚类的采样数量
            fraction_per_cluster: 每个聚类的采样比例
            feature_columns: 用于聚类的特征列
            
        Returns:
            聚类采样结果
        """
        if feature_columns is None:
            feature_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        if not feature_columns:
            raise ValueError("没有可用的数值列进行聚类")
        
        # 准备聚类数据
        cluster_data = data[feature_columns].fillna(0)
        
        # 执行K-means聚类
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state, n_init=10)
        cluster_labels = kmeans.fit_predict(cluster_data)
        
        # 从每个聚类中采样
        sampled_dfs = []
        for cluster_id in range(self.n_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_subset = data[cluster_mask]
            
            if len(cluster_subset) == 0:
                continue
            
            if sample_per_cluster is not None:
                sample_size = min(sample_per_cluster, len(cluster_subset))
                sampled = cluster_subset.sample(n=sample_size, random_state=self.random_state)
            elif fraction_per_cluster is not None:
                sample_size = max(1, int(len(cluster_subset) * fraction_per_cluster))
                sampled = cluster_subset.sample(n=sample_size, random_state=self.random_state)
            else:
                sampled = cluster_subset
            
            sampled_dfs.append(sampled)
        
        result = pd.concat(sampled_dfs, ignore_index=True)
        logger.info(f"聚类采样完成，从 {self.n_clusters} 个聚类中采样 {len(result)} 条记录")
        
        return result
    
    def get_cluster_labels(self, data: pd.DataFrame,
                          feature_columns: Optional[List[str]] = None) -> np.ndarray:
        """获取聚类标签"""
        if feature_columns is None:
            feature_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        cluster_data = data[feature_columns].fillna(0)
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=self.random_state, n_init=10)
        return kmeans.fit_predict(cluster_data)


class ReservoirSampler:
    """水库采样器（适用于流数据）"""
    
    def __init__(self, random_state: int = 42):
        """初始化水库采样器"""
        self.random_state = random_state
        random.seed(random_state)
        self.reservoir = []
        self.counter = 0
    
    def sample(self, k: int, data_stream: Optional[List] = None) -> List:
        """水库采样
        
        Args:
            k: 采样大小
            data_stream: 数据流（如果提供）
            
        Returns:
            采样结果
        """
        if data_stream is not None:
            # 一次性处理整个数据流
            reservoir = []
            for i, item in enumerate(data_stream):
                if i < k:
                    reservoir.append(item)
                else:
                    j = random.randint(0, i)
                    if j < k:
                        reservoir[j] = item
            return reservoir
        else:
            # 流式处理
            return self._process_stream(k)
    
    def _process_stream(self, k: int) -> List:
        """流式处理"""
        if len(self.reservoir) < k:
            return self.reservoir
        return self.reservoir
    
    def update(self, item: Any, k: int) -> bool:
        """更新采样器（流式处理）"""
        self.counter += 1
        
        if len(self.reservoir) < k:
            self.reservoir.append(item)
            return True
        else:
            j = random.randint(0, self.counter - 1)
            if j < k:
                self.reservoir[j] = item
                return True
        return False
    
    def get_sample(self) -> List:
        """获取当前样本"""
        return self.reservoir
    
    def reset(self):
        """重置采样器"""
        self.reservoir = []
        self.counter = 0


class TimeBasedSampler:
    """基于时间的采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化基于时间的采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample_by_frequency(self, data: pd.DataFrame,
                           timestamp_column: str,
                           frequency: str = 'D') -> pd.DataFrame:
        """按频率采样
        
        Args:
            data: 输入数据
            timestamp_column: 时间戳列名
            frequency: 频率 ('D'=天, 'W'=周, 'M'=月, 'Q'=季度, 'Y'=年, 'H'=小时)
            
        Returns:
            采样结果
        """
        if timestamp_column not in data.columns:
            raise ValueError(f"时间戳列 '{timestamp_column}' 不存在")
        
        # 转换时间戳
        timestamps = pd.to_datetime(data[timestamp_column])
        data_with_index = data.copy()
        data_with_index['_timestamp'] = timestamps
        
        # 按频率采样
        sampled_indices = []
        
        if frequency == 'D':
            groups = data_with_index.groupby(data_with_index['_timestamp'].dt.date)
        elif frequency == 'W':
            groups = data_with_index.groupby(data_with_index['_timestamp'].dt.isocalendar().week)
        elif frequency == 'M':
            groups = data_with_index.groupby([data_with_index['_timestamp'].dt.year, data_with_index['_timestamp'].dt.month])
        elif frequency == 'Q':
            groups = data_with_index.groupby([data_with_index['_timestamp'].dt.year, data_with_index['_timestamp'].dt.quarter])
        elif frequency == 'Y':
            groups = data_with_index.groupby(data_with_index['_timestamp'].dt.year)
        elif frequency == 'H':
            groups = data_with_index.groupby(data_with_index['_timestamp'].dt.floor('H'))
        else:
            raise ValueError(f"不支持的频率: {frequency}")
        
        for _, group in groups:
            if not group.empty:
                sampled_indices.append(np.random.choice(group.index))
        
        return data.loc[sampled_indices].sort_index()
    
    def sample_by_interval(self, data: pd.DataFrame,
                          timestamp_column: str,
                          interval: str = '7D',
                          start_date: Optional[str] = None) -> pd.DataFrame:
        """按时间间隔采样
        
        Args:
            data: 输入数据
            timestamp_column: 时间戳列名
            interval: 间隔（如 '7D' 表示7天，'1M' 表示1个月）
            start_date: 开始日期
            
        Returns:
            采样结果
        """
        if timestamp_column not in data.columns:
            raise ValueError(f"时间戳列 '{timestamp_column}' 不存在")
        
        # 转换时间戳
        timestamps = pd.to_datetime(data[timestamp_column])
        
        if start_date is not None:
            start = pd.to_datetime(start_date)
        else:
            start = timestamps.min()
        
        end = timestamps.max()
        
        # 生成采样时间点
        sample_times = pd.date_range(start=start, end=end, freq=interval)
        
        # 找到每个采样时间点最近的数据
        sampled_indices = []
        for sample_time in sample_times:
            time_diff = (timestamps - sample_time).abs()
            nearest_idx = time_diff.idxmin()
            sampled_indices.append(nearest_idx)
        
        return data.loc[sampled_indices].drop_duplicates().sort_index()


class WeightedSampler:
    """加权采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化加权采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample(self, data: pd.DataFrame,
              weight_column: str,
              n: Optional[int] = None,
              frac: Optional[float] = None,
              replace: bool = False) -> pd.DataFrame:
        """加权采样
        
        Args:
            data: 输入数据
            weight_column: 权重列名
            n: 采样数量
            frac: 采样比例
            replace: 是否放回采样
            
        Returns:
            加权采样结果
        """
        if weight_column not in data.columns:
            raise ValueError(f"权重列 '{weight_column}' 不存在")
        
        # 获取权重
        weights = data[weight_column].fillna(0)
        
        # 确保权重为正数
        if (weights <= 0).any():
            weights = weights - weights.min() + 1e-8
        
        if n is not None:
            sample_size = n
        elif frac is not None:
            sample_size = int(len(data) * frac)
        else:
            raise ValueError("必须指定 n 或 frac 参数")
        
        # 执行加权采样
        sample_indices = np.random.choice(
            len(data),
            size=sample_size,
            replace=replace,
            p=weights / weights.sum()
        )
        
        return data.iloc[sample_indices]
    
    def sample_with_probabilities(self, data: pd.DataFrame,
                                 probabilities: np.ndarray,
                                 n: int,
                                 replace: bool = False) -> pd.DataFrame:
        """根据概率采样"""
        if len(probabilities) != len(data):
            raise ValueError("概率数组长度必须与数据长度相同")
        
        if (probabilities < 0).any():
            raise ValueError("概率不能为负数")
        
        prob_sum = probabilities.sum()
        if prob_sum == 0:
            raise ValueError("概率和不能为0")
        
        norm_probs = probabilities / prob_sum
        
        sample_indices = np.random.choice(
            len(data),
            size=n,
            replace=replace,
            p=norm_probs
        )
        
        return data.iloc[sample_indices]


class DiversitySampler:
    """多样性采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化多样性采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
    
    def sample_by_diversity(self, data: pd.DataFrame,
                          diversity_column: str,
                          n: int) -> pd.DataFrame:
        """基于多样性的采样（确保覆盖不同类别）"""
        if diversity_column not in data.columns:
            raise ValueError(f"多样性列 '{diversity_column}' 不存在")
        
        unique_values = data[diversity_column].unique()
        samples_per_group = max(1, n // len(unique_values))
        
        sampled_dfs = []
        for value in unique_values:
            subset = data[data[diversity_column] == value]
            sample_size = min(samples_per_group, len(subset))
            sampled = subset.sample(n=sample_size, random_state=self.random_state)
            sampled_dfs.append(sampled)
        
        result = pd.concat(sampled_dfs, ignore_index=True)
        
        # 如果样本数量不够，从剩余数据中补充
        if len(result) < n:
            remaining = data.index.difference(result.index)
            additional_needed = n - len(result)
            additional = data.loc[remaining].sample(
                n=min(additional_needed, len(remaining)),
                random_state=self.random_state
            )
            result = pd.concat([result, additional], ignore_index=True)
        
        return result.head(n)
    
    def sample_by_clustering(self, data: pd.DataFrame,
                            feature_columns: List[str],
                            n: int,
                            n_clusters: Optional[int] = None) -> pd.DataFrame:
        """基于聚类的多样性采样"""
        if n_clusters is None:
            n_clusters = min(n, 10)
        
        # 聚类
        cluster_data = data[feature_columns].fillna(0)
        kmeans = KMeans(n_clusters=n_clusters, random_state=self.random_state, n_init=10)
        cluster_labels = kmeans.fit_predict(cluster_data)
        
        # 从每个聚类中采样
        samples_per_cluster = max(1, n // n_clusters)
        
        sampled_dfs = []
        for cluster_id in range(n_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_subset = data[cluster_mask]
            
            if len(cluster_subset) == 0:
                continue
            
            sample_size = min(samples_per_cluster, len(cluster_subset))
            sampled = cluster_subset.sample(n=sample_size, random_state=self.random_state)
            sampled_dfs.append(sampled)
        
        result = pd.concat(sampled_dfs, ignore_index=True)
        
        # 如果样本数量不够，从剩余数据中补充
        if len(result) < n:
            remaining = data.index.difference(result.index)
            additional_needed = n - len(result)
            if len(remaining) > 0:
                additional = data.loc[remaining].sample(
                    n=min(additional_needed, len(remaining)),
                    random_state=self.random_state
                )
                result = pd.concat([result, additional], ignore_index=True)
        
        return result.head(n)


class DataSampler:
    """综合数据采样器"""
    
    def __init__(self, random_state: int = 42):
        """初始化数据采样器"""
        self.random_state = random_state
        np.random.seed(random_state)
        random.seed(random_state)
        
        self.random_sampler = RandomSampler(random_state)
        self.stratified_sampler = StratifiedSampler(random_state)
        self.systematic_sampler = SystematicSampler(random_state)
        self.cluster_sampler = ClusterSampler(random_state=random_state)
        self.reservoir_sampler = ReservoirSampler(random_state)
        self.time_sampler = TimeBasedSampler(random_state)
        self.weighted_sampler = WeightedSampler(random_state)
        self.diversity_sampler = DiversitySampler(random_state)
        
        self.sampling_log = []
    
    def sample(self, data: Union[pd.DataFrame, pd.Series],
              method: str = 'random',
              **kwargs) -> Union[pd.DataFrame, pd.Series]:
        """采样
        
        Args:
            data: 输入数据
            method: 采样方法 
                    ('random', 'stratified', 'systematic', 'cluster',
                     'reservoir', 'time', 'weighted', 'diversity')
            **kwargs: 方法参数
            
        Returns:
            采样结果
        """
        self._log(f"开始 {method} 采样")
        
        if method == 'random':
            result = self.random_sampler.sample(data, **kwargs)
        elif method == 'stratified':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("分层采样需要 DataFrame 数据")
            result = self.stratified_sampler.sample(data, **kwargs)
        elif method == 'systematic':
            result = self.systematic_sampler.sample(data, **kwargs)
        elif method == 'cluster':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("聚类采样需要 DataFrame 数据")
            result = self.cluster_sampler.sample(data, **kwargs)
        elif method == 'reservoir':
            if isinstance(data, (pd.DataFrame, pd.Series)):
                result = self.reservoir_sampler.sample(kwargs.get('k', 100), data.tolist())
                if isinstance(data, pd.DataFrame):
                    result = data.iloc[result]
                else:
                    result = data.iloc[result]
            else:
                result = self.reservoir_sampler.sample(**kwargs)
        elif method == 'time':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("时间采样需要 DataFrame 数据")
            result = self.time_sampler.sample_by_frequency(data, **kwargs)
        elif method == 'time_interval':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("时间间隔采样需要 DataFrame 数据")
            result = self.time_sampler.sample_by_interval(data, **kwargs)
        elif method == 'weighted':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("加权采样需要 DataFrame 数据")
            result = self.weighted_sampler.sample(data, **kwargs)
        elif method == 'diversity':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("多样性采样需要 DataFrame 数据")
            result = self.diversity_sampler.sample_by_diversity(data, **kwargs)
        elif method == 'diversity_cluster':
            if not isinstance(data, pd.DataFrame):
                raise ValueError("聚类多样性采样需要 DataFrame 数据")
            result = self.diversity_sampler.sample_by_clustering(data, **kwargs)
        else:
            raise ValueError(f"不支持的采样方法: {method}")
        
        self._log(f"完成 {method} 采样，得到 {len(result) if hasattr(result, '__len__') else '?'} 条记录")
        return result
    
    def train_test_split(self, data: pd.DataFrame,
                        test_size: float = 0.2,
                        stratify_column: Optional[str] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """训练测试集分割"""
        if stratify_column:
            return self.stratified_sampler.train_test_split(data, stratify_column, test_size)
        else:
            train, test = train_test_split(data, test_size=test_size, random_state=self.random_state)
            return train, test
    
    def cross_validation_split(self, data: pd.DataFrame,
                              n_folds: int = 5,
                              stratify_column: Optional[str] = None) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """交叉验证分割"""
        folds = []
        
        if stratify_column:
            skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
            for train_idx, val_idx in skf.split(data, data[stratify_column]):
                train_fold = data.iloc[train_idx]
                val_fold = data.iloc[val_idx]
                folds.append((train_fold, val_fold))
        else:
            kf = KFold(n_splits=n_folds, shuffle=True, random_state=self.random_state)
            for train_idx, val_idx in kf.split(data):
                train_fold = data.iloc[train_idx]
                val_fold = data.iloc[val_idx]
                folds.append((train_fold, val_fold))
        
        return folds
    
    def bootstrap_sample(self, data: Union[pd.DataFrame, pd.Series],
                        n_bootstrap: int = 100,
                        sample_size: Optional[int] = None,
                        statistic: Optional[Callable] = None) -> Dict[str, Any]:
        """自助法采样"""
        if sample_size is None:
            sample_size = len(data)
        
        bootstrap_samples = []
        bootstrap_stats = []
        
        for i in range(n_bootstrap):
            # 有放回采样
            if isinstance(data, pd.DataFrame):
                bootstrap_sample = data.sample(n=sample_size, replace=True, random_state=self.random_state + i)
            else:
                indices = np.random.choice(len(data), sample_size, replace=True)
                bootstrap_sample = data.iloc[indices]
            
            bootstrap_samples.append(bootstrap_sample)
            
            if statistic is not None:
                bootstrap_stats.append(statistic(bootstrap_sample))
        
        result = {
            'bootstrap_samples': bootstrap_samples,
            'n_bootstrap': n_bootstrap,
            'sample_size': sample_size
        }
        
        if statistic is not None and bootstrap_stats:
            bootstrap_stats = np.array(bootstrap_stats)
            original_stat = statistic(data)
            
            result.update({
                'original_statistic': original_stat,
                'bootstrap_mean': float(np.mean(bootstrap_stats)),
                'bootstrap_std': float(np.std(bootstrap_stats)),
                'bootstrap_median': float(np.median(bootstrap_stats)),
                'confidence_interval_95': (
                    float(np.percentile(bootstrap_stats, 2.5)),
                    float(np.percentile(bootstrap_stats, 97.5))
                ),
                'bias': float(np.mean(bootstrap_stats) - original_stat),
                'all_statistics': bootstrap_stats.tolist()
            })
        
        return result
    
    def progressive_sample(self, data: pd.DataFrame,
                          sample_sizes: List[int],
                          random_state: int = 42) -> Dict[int, pd.DataFrame]:
        """渐进式采样"""
        results = {}
        
        for size in sample_sizes:
            if size > len(data):
                continue
            
            # 固定种子确保可重复性
            sample = data.sample(n=size, random_state=random_state)
            results[size] = sample
        
        return results
    
    def balance_dataset(self, data: pd.DataFrame,
                       target_column: str,
                       method: str = 'random_oversample',
                       random_state: int = 42) -> pd.DataFrame:
        """平衡数据集
        
        Args:
            data: 输入数据
            target_column: 目标列名
            method: 平衡方法 
                    ('random_oversample', 'smote', 'adasyn', 'random_undersample', 
                     'nearmiss', 'tomek_links')
            random_state: 随机种子
            
        Returns:
            平衡后的数据集
        """
        if target_column not in data.columns:
            raise ValueError(f"目标列 '{target_column}' 不存在")
        
        X = data.drop(columns=[target_column])
        y = data[target_column]
        
        # 选择数值列
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X_numeric = X[numeric_cols].fillna(0)
        
        # 记录原始分布
        original_dist = Counter(y)
        logger.info(f"原始分布: {dict(original_dist)}")
        
        if method == 'random_oversample':
            sampler = RandomOverSampler(random_state=random_state)
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        elif method == 'smote':
            sampler = SMOTE(random_state=random_state)
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        elif method == 'adasyn':
            sampler = ADASYN(random_state=random_state)
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        elif method == 'random_undersample':
            sampler = RandomUnderSampler(random_state=random_state)
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        elif method == 'nearmiss':
            sampler = NearMiss()
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        elif method == 'tomek_links':
            sampler = TomekLinks()
            X_resampled, y_resampled = sampler.fit_resample(X_numeric, y)
        else:
            raise ValueError(f"不支持的平衡方法: {method}")
        
        # 重构数据框
        balanced_df = X.loc[X_resampled.index].copy()
        balanced_df[target_column] = y_resampled
        
        # 记录平衡后分布
        balanced_dist = Counter(y_resampled)
        logger.info(f"平衡后分布: {dict(balanced_dist)}")
        
        return balanced_df
    
    def _log(self, message: str):
        """记录日志"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.sampling_log.append(log_entry)
        logger.info(log_entry)
    
    def get_log(self) -> List[str]:
        """获取日志"""
        return self.sampling_log


# 便捷函数
def train_test_split_sample(data: pd.DataFrame,
                           test_size: float = 0.2,
                           stratify_column: Optional[str] = None,
                           random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """训练测试集分割（便捷函数）"""
    sampler = DataSampler(random_state)
    return sampler.train_test_split(data, test_size, stratify_column)


def bootstrap_sample(data: pd.DataFrame,
                    n_bootstrap: int = 100,
                    statistic: Optional[Callable] = None,
                    random_state: int = 42) -> Dict[str, Any]:
    """自助法采样（便捷函数）"""
    sampler = DataSampler(random_state)
    return sampler.bootstrap_sample(data, n_bootstrap=n_bootstrap, statistic=statistic)


def cross_validation_sample(data: pd.DataFrame,
                           n_folds: int = 5,
                           stratify_column: Optional[str] = None,
                           random_state: int = 42) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """交叉验证采样（便捷函数）"""
    sampler = DataSampler(random_state)
    return sampler.cross_validation_split(data, n_folds, stratify_column)


def progressive_sample(data: pd.DataFrame,
                      sample_sizes: List[int],
                      random_state: int = 42) -> Dict[int, pd.DataFrame]:
    """渐进式采样（便捷函数）"""
    sampler = DataSampler(random_state)
    return sampler.progressive_sample(data, sample_sizes, random_state)


def create_sample_weights(y: pd.Series, method: str = 'balanced') -> np.ndarray:
    """创建样本权重
    
    Args:
        y: 目标变量
        method: 权重方法 ('balanced', 'inverse')
        
    Returns:
        样本权重数组
    """
    from sklearn.utils.class_weight import compute_class_weight
    
    classes = np.unique(y)
    
    if method == 'balanced':
        weights = compute_class_weight('balanced', classes=classes, y=y)
    elif method == 'inverse':
        weights = 1 / (np.bincount(y) + 1e-8)
    else:
        raise ValueError(f"不支持的权重方法: {method}")
    
    sample_weights = np.array([weights[np.where(classes == val)[0][0]] for val in y])
    
    return sample_weights


def balance_dataset(data: pd.DataFrame,
                   target_column: str,
                   method: str = 'random_oversample',
                   random_state: int = 42) -> pd.DataFrame:
    """平衡数据集（便捷函数）"""
    sampler = DataSampler(random_state)
    return sampler.balance_dataset(data, target_column, method, random_state)