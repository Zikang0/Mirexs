"""
数据转换工具模块

提供数据转换、特征工程、数据预处理等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, PowerTransformer, QuantileTransformer
from sklearn.decomposition import PCA, TruncatedSVD, NMF, FactorAnalysis
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif, RFE
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from scipy import stats
import logging
import warnings
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataNormalizer:
    """数据标准化器"""
    
    def __init__(self, method: str = 'standard', **kwargs):
        """初始化数据标准化器
        
        Args:
            method: 标准化方法 
                    ('standard', 'minmax', 'robust', 'maxabs', 'l2', 
                     'power', 'quantile', 'unit_length')
            **kwargs: 其他参数
        """
        self.method = method
        self.kwargs = kwargs
        self.scaler = None
        self.fitted = False
    
    def fit(self, X: Union[pd.DataFrame, np.ndarray]) -> 'DataNormalizer':
        """拟合标准化器"""
        if isinstance(X, pd.DataFrame):
            X_values = X.values
            self.feature_names = X.columns.tolist()
        else:
            X_values = X
            self.feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        
        if self.method == 'standard':
            self.scaler = StandardScaler(**self.kwargs)
        elif self.method == 'minmax':
            self.scaler = MinMaxScaler(**self.kwargs)
        elif self.method == 'robust':
            self.scaler = RobustScaler(**self.kwargs)
        elif self.method == 'maxabs':
            from sklearn.preprocessing import MaxAbsScaler
            self.scaler = MaxAbsScaler(**self.kwargs)
        elif self.method == 'l2':
            from sklearn.preprocessing import Normalizer
            self.scaler = Normalizer(norm='l2', **self.kwargs)
        elif self.method == 'power':
            self.scaler = PowerTransformer(**self.kwargs)
        elif self.method == 'quantile':
            self.scaler = QuantileTransformer(**self.kwargs)
        elif self.method == 'unit_length':
            from sklearn.preprocessing import Normalizer
            self.scaler = Normalizer(norm='l2', **self.kwargs)
        else:
            raise ValueError(f"不支持的标准化方法: {self.method}")
        
        self.scaler.fit(X_values)
        self.fitted = True
        return self
    
    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        """转换数据"""
        if not self.fitted:
            raise ValueError("标准化器尚未拟合，请先调用 fit()")
        
        if isinstance(X, pd.DataFrame):
            X_values = X.values
            X_transformed = self.scaler.transform(X_values)
            return pd.DataFrame(X_transformed, columns=self.feature_names, index=X.index)
        else:
            return self.scaler.transform(X)
    
    def fit_transform(self, X: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: Union[pd.DataFrame, np.ndarray]) -> Union[pd.DataFrame, np.ndarray]:
        """逆转换"""
        if not self.fitted:
            raise ValueError("标准化器尚未拟合，请先调用 fit()")
        
        if isinstance(X, pd.DataFrame):
            X_values = X.values
            X_inverse = self.scaler.inverse_transform(X_values)
            return pd.DataFrame(X_inverse, columns=self.feature_names, index=X.index)
        else:
            return self.scaler.inverse_transform(X)


class DataEncoder:
    """数据编码器"""
    
    def __init__(self, method: str = 'label', **kwargs):
        """初始化数据编码器
        
        Args:
            method: 编码方法 
                    ('label', 'onehot', 'ordinal', 'binary', 'frequency', 
                     'target', 'hash', 'leave_one_out')
            **kwargs: 其他参数
        """
        self.method = method
        self.kwargs = kwargs
        self.encoder = None
        self.fitted = False
        self.encoding_map = {}
        self.feature_names = []
    
    def fit(self, X: Union[pd.DataFrame, pd.Series]) -> 'DataEncoder':
        """拟合编码器"""
        if isinstance(X, pd.DataFrame):
            if X.shape[1] == 1:
                self._fit_series(X.iloc[:, 0])
            else:
                self._fit_dataframe(X)
        else:
            self._fit_series(X)
        
        self.fitted = True
        return self
    
    def _fit_series(self, series: pd.Series):
        """拟合单列数据"""
        if self.method == 'label':
            self.encoder = LabelEncoder()
            self.encoder.fit(series.dropna())
            self.encoding_map['label_mapping'] = dict(zip(self.encoder.classes_, self.encoder.transform(self.encoder.classes_)))
            
        elif self.method == 'onehot':
            self.encoder = OneHotEncoder(sparse_output=False, **self.kwargs)
            self.encoder.fit(series.values.reshape(-1, 1))
            self.feature_names = [f"{series.name}_{cat}" for cat in self.encoder.categories_[0]]
            
        elif self.method == 'ordinal':
            self.encoder = OrdinalEncoder(**self.kwargs)
            self.encoder.fit(series.values.reshape(-1, 1))
            
        elif self.method == 'frequency':
            freq_map = series.value_counts(normalize=True).to_dict()
            self.encoding_map['frequency'] = freq_map
            
        elif self.method == 'target':
            self.encoding_map['target_map'] = {}
            # Target encoding 需要目标变量，将在transform时提供
            
        elif self.method == 'binary':
            try:
                from category_encoders import BinaryEncoder
                self.encoder = BinaryEncoder(**self.kwargs)
                self.encoder.fit(series.values.reshape(-1, 1))
            except ImportError:
                raise ImportError("BinaryEncoder 需要 category_encoders: pip install category-encoders")
        
        elif self.method == 'hash':
            try:
                from category_encoders import HashingEncoder
                self.encoder = HashingEncoder(**self.kwargs)
                self.encoder.fit(series.values.reshape(-1, 1))
            except ImportError:
                raise ImportError("HashingEncoder 需要 category_encoders")
        
        elif self.method == 'leave_one_out':
            try:
                from category_encoders import LeaveOneOutEncoder
                self.encoder = LeaveOneOutEncoder(**self.kwargs)
                self.encoder.fit(series.values.reshape(-1, 1))
            except ImportError:
                raise ImportError("LeaveOneOutEncoder 需要 category_encoders")
    
    def _fit_dataframe(self, df: pd.DataFrame):
        """拟合多列数据"""
        if self.method == 'onehot':
            self.encoder = OneHotEncoder(sparse_output=False, **self.kwargs)
            self.encoder.fit(df)
            self.feature_names = self.encoder.get_feature_names_out(df.columns).tolist()
        elif self.method == 'ordinal':
            self.encoder = OrdinalEncoder(**self.kwargs)
            self.encoder.fit(df)
        else:
            # 对于其他方法，逐列处理
            for col in df.columns:
                col_encoder = DataEncoder(method=self.method, **self.kwargs)
                col_encoder._fit_series(df[col])
                self.encoding_map[col] = col_encoder
    
    def transform(self, X: Union[pd.DataFrame, pd.Series], 
                  y: Optional[pd.Series] = None) -> Union[pd.DataFrame, pd.Series]:
        """转换数据"""
        if not self.fitted:
            raise ValueError("编码器尚未拟合，请先调用 fit()")
        
        if isinstance(X, pd.DataFrame):
            if X.shape[1] == 1:
                return self._transform_series(X.iloc[:, 0], y)
            else:
                return self._transform_dataframe(X, y)
        else:
            return self._transform_series(X, y)
    
    def _transform_series(self, series: pd.Series, y: Optional[pd.Series] = None) -> Union[pd.Series, pd.DataFrame]:
        """转换单列数据"""
        if self.method == 'label':
            transformed = series.map(self.encoding_map['label_mapping']).fillna(-1).astype(int)
            return pd.Series(transformed, name=series.name, index=series.index)
        
        elif self.method == 'onehot':
            transformed = self.encoder.transform(series.values.reshape(-1, 1))
            return pd.DataFrame(transformed, columns=self.feature_names, index=series.index)
        
        elif self.method == 'ordinal':
            transformed = self.encoder.transform(series.values.reshape(-1, 1))
            return pd.Series(transformed.flatten(), name=series.name, index=series.index)
        
        elif self.method == 'frequency':
            transformed = series.map(self.encoding_map['frequency']).fillna(0)
            return pd.Series(transformed, name=f"{series.name}_freq", index=series.index)
        
        elif self.method == 'target':
            if y is None:
                raise ValueError("Target encoding 需要目标变量 y")
            
            target_map = series.groupby(series).agg(lambda x: y[x.index].mean()).to_dict()
            transformed = series.map(target_map).fillna(y.mean())
            return pd.Series(transformed, name=f"{series.name}_target", index=series.index)
        
        elif self.method in ['binary', 'hash', 'leave_one_out']:
            transformed = self.encoder.transform(series.values.reshape(-1, 1))
            if hasattr(transformed, 'values'):
                return pd.DataFrame(transformed, index=series.index)
            else:
                return pd.Series(transformed.flatten(), name=series.name, index=series.index)
    
    def _transform_dataframe(self, df: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """转换多列数据"""
        if self.method == 'onehot':
            transformed = self.encoder.transform(df)
            return pd.DataFrame(transformed, columns=self.feature_names, index=df.index)
        
        elif self.method == 'ordinal':
            transformed = self.encoder.transform(df)
            return pd.DataFrame(transformed, columns=df.columns, index=df.index)
        
        else:
            # 逐列转换
            transformed_dfs = []
            for col in df.columns:
                if col in self.encoding_map:
                    col_encoder = self.encoding_map[col]
                    col_transformed = col_encoder.transform(df[col], y)
                    if isinstance(col_transformed, pd.DataFrame):
                        transformed_dfs.append(col_transformed)
                    else:
                        transformed_dfs.append(col_transformed.to_frame())
                else:
                    transformed_dfs.append(df[[col]])
            
            return pd.concat(transformed_dfs, axis=1)
    
    def fit_transform(self, X: Union[pd.DataFrame, pd.Series], 
                      y: Optional[pd.Series] = None) -> Union[pd.DataFrame, pd.Series]:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X, y)


class DataTransformer:
    """数据转换器"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        """初始化数据转换器
        
        Args:
            data: 输入数据
        """
        self.data = data.copy() if data is not None else None
        self.transformers = {}
        self.transformation_log = []
    
    def set_data(self, data: pd.DataFrame):
        """设置数据"""
        self.data = data.copy()
        return self
    
    def normalize(self, columns: Optional[List[str]] = None, 
                  method: str = 'standard', suffix: str = '_norm') -> pd.DataFrame:
        """标准化数据"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col in df.columns:
                normalizer = DataNormalizer(method=method)
                transformed = normalizer.fit_transform(df[[col]])
                new_col_name = f"{col}{suffix}"
                df[new_col_name] = transformed[col].values
                self.transformers[f"{col}_norm"] = normalizer
                self._log_transformation(f"标准化列 '{col}' 使用 {method} 方法")
        
        self.data = df
        return df
    
    def encode_categorical(self, columns: Optional[List[str]] = None,
                          method: str = 'label', drop_original: bool = True) -> pd.DataFrame:
        """编码分类变量"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        for col in columns:
            if col in df.columns:
                encoder = DataEncoder(method=method)
                encoded = encoder.fit_transform(df[col])
                
                if isinstance(encoded, pd.DataFrame):
                    for encoded_col in encoded.columns:
                        df[encoded_col] = encoded[encoded_col].values
                else:
                    new_col_name = f"{col}_{method}"
                    df[new_col_name] = encoded.values
                
                if drop_original:
                    df = df.drop(columns=[col])
                
                self.transformers[f"{col}_encoder"] = encoder
                self._log_transformation(f"编码列 '{col}' 使用 {method} 方法")
        
        self.data = df
        return df
    
    def create_polynomial_features(self, columns: List[str], degree: int = 2,
                                   interaction_only: bool = False) -> pd.DataFrame:
        """创建多项式特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        from sklearn.preprocessing import PolynomialFeatures
        
        df = self.data.copy()
        available_cols = [col for col in columns if col in df.columns]
        
        if len(available_cols) == 0:
            return df
        
        poly = PolynomialFeatures(degree=degree, interaction_only=interaction_only, include_bias=False)
        poly_features = poly.fit_transform(df[available_cols])
        
        feature_names = poly.get_feature_names_out(available_cols)
        
        for i, name in enumerate(feature_names):
            if name not in available_cols:  # 避免创建原始特征的副本
                clean_name = name.replace(' ', '_').replace('^', '_power_')
                df[clean_name] = poly_features[:, i]
        
        self.transformers['poly_features'] = poly
        self._log_transformation(f"创建多项式特征，度数={degree}")
        
        self.data = df
        return df
    
    def create_interaction_features(self, columns: List[str]) -> pd.DataFrame:
        """创建交互特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        available_cols = [col for col in columns if col in df.columns]
        
        if len(available_cols) < 2:
            return df
        
        for i in range(len(available_cols)):
            for j in range(i + 1, len(available_cols)):
                col1, col2 = available_cols[i], available_cols[j]
                interaction_name = f"{col1}_x_{col2}"
                df[interaction_name] = df[col1] * df[col2]
        
        self._log_transformation(f"创建 {len(available_cols) * (len(available_cols)-1) // 2} 个交互特征")
        
        self.data = df
        return df
    
    def create_aggregation_features(self, group_column: str,
                                   agg_columns: List[str],
                                   agg_functions: List[str] = ['mean', 'std', 'min', 'max', 'count']) -> pd.DataFrame:
        """创建聚合特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if group_column not in df.columns:
            raise ValueError(f"分组列 '{group_column}' 不存在")
        
        # 计算分组统计
        agg_df = df.groupby(group_column)[agg_columns].agg(agg_functions)
        agg_df.columns = ['_'.join(col).strip() for col in agg_df.columns]
        
        # 合并回原数据
        df = df.merge(agg_df, left_on=group_column, right_index=True, how='left')
        
        # 添加分组大小
        group_sizes = df.groupby(group_column).size()
        df[f'{group_column}_group_size'] = df[group_column].map(group_sizes)
        
        # 添加分组占比
        for col in agg_columns:
            if col in df.columns:
                mean_col = f"{col}_mean"
                if mean_col in df.columns:
                    df[f'{col}_group_ratio'] = df[col] / (df[mean_col] + 1e-8)
        
        self._log_transformation(f"为列 {agg_columns} 创建聚合特征")
        
        self.data = df
        return df
    
    def create_time_features(self, timestamp_column: str,
                            features: List[str] = ['year', 'month', 'day', 'hour', 'dayofweek',
                                                  'quarter', 'week', 'is_weekend']) -> pd.DataFrame:
        """创建时间特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if timestamp_column not in df.columns:
            raise ValueError(f"时间戳列 '{timestamp_column}' 不存在")
        
        # 转换时间戳
        df[timestamp_column] = pd.to_datetime(df[timestamp_column])
        
        feature_map = {
            'year': lambda x: x.dt.year,
            'month': lambda x: x.dt.month,
            'day': lambda x: x.dt.day,
            'hour': lambda x: x.dt.hour,
            'minute': lambda x: x.dt.minute,
            'second': lambda x: x.dt.second,
            'dayofweek': lambda x: x.dt.dayofweek,
            'dayofyear': lambda x: x.dt.dayofyear,
            'week': lambda x: x.dt.isocalendar().week,
            'quarter': lambda x: x.dt.quarter,
            'is_weekend': lambda x: (x.dt.dayofweek >= 5).astype(int),
            'is_month_start': lambda x: x.dt.is_month_start,
            'is_month_end': lambda x: x.dt.is_month_end,
            'is_quarter_start': lambda x: x.dt.is_quarter_start,
            'is_quarter_end': lambda x: x.dt.is_quarter_end,
            'is_year_start': lambda x: x.dt.is_year_start,
            'is_year_end': lambda x: x.dt.is_year_end,
            'days_in_month': lambda x: x.dt.days_in_month,
            'days_since_start': lambda x: (x - x.min()).dt.days,
            'sin_hour': lambda x: np.sin(2 * np.pi * x.dt.hour / 24),
            'cos_hour': lambda x: np.cos(2 * np.pi * x.dt.hour / 24),
            'sin_dayofweek': lambda x: np.sin(2 * np.pi * x.dt.dayofweek / 7),
            'cos_dayofweek': lambda x: np.cos(2 * np.pi * x.dt.dayofweek / 7),
            'sin_month': lambda x: np.sin(2 * np.pi * x.dt.month / 12),
            'cos_month': lambda x: np.cos(2 * np.pi * x.dt.month / 12)
        }
        
        for feature in features:
            if feature in feature_map:
                feature_name = f"{timestamp_column}_{feature}"
                df[feature_name] = feature_map[feature](df[timestamp_column])
        
        self._log_transformation(f"为列 '{timestamp_column}' 创建 {len(features)} 个时间特征")
        
        self.data = df
        return df
    
    def create_text_features(self, text_column: str,
                            features: List[str] = ['length', 'word_count', 'char_count',
                                                  'avg_word_length', 'digit_count']) -> pd.DataFrame:
        """创建文本特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if text_column not in df.columns:
            raise ValueError(f"文本列 '{text_column}' 不存在")
        
        text_series = df[text_column].astype(str)
        
        feature_map = {
            'length': lambda x: x.str.len(),
            'word_count': lambda x: x.str.split().str.len(),
            'char_count': lambda x: x.str.len(),
            'avg_word_length': lambda x: x.apply(lambda t: np.mean([len(w) for w in t.split()]) if t.split() else 0),
            'upper_count': lambda x: x.str.count(r'[A-Z]'),
            'lower_count': lambda x: x.str.count(r'[a-z]'),
            'digit_count': lambda x: x.str.count(r'\d'),
            'special_char_count': lambda x: x.str.count(r'[^a-zA-Z0-9\s]'),
            'space_count': lambda x: x.str.count(r'\s'),
            'sentence_count': lambda x: x.str.count(r'[.!?]+') + 1
        }
        
        for feature in features:
            if feature in feature_map:
                feature_name = f"{text_column}_{feature}"
                df[feature_name] = feature_map[feature](text_series)
        
        self._log_transformation(f"为列 '{text_column}' 创建 {len(features)} 个文本特征")
        
        self.data = df
        return df
    
    def create_statistical_features(self, columns: List[str],
                                   window_sizes: List[int] = [3, 5, 7]) -> pd.DataFrame:
        """创建统计特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            series = df[col]
            
            for window in window_sizes:
                if len(series) >= window:
                    # 移动平均
                    df[f'{col}_ma_{window}'] = series.rolling(window=window, min_periods=1).mean()
                    
                    # 移动标准差
                    df[f'{col}_std_{window}'] = series.rolling(window=window, min_periods=1).std().fillna(0)
                    
                    # 移动最小值
                    df[f'{col}_min_{window}'] = series.rolling(window=window, min_periods=1).min()
                    
                    # 移动最大值
                    df[f'{col}_max_{window}'] = series.rolling(window=window, min_periods=1).max()
                    
                    # 移动中位数
                    df[f'{col}_median_{window}'] = series.rolling(window=window, min_periods=1).median()
                    
                    # 移动偏度
                    if len(series) >= window * 2:
                        df[f'{col}_skew_{window}'] = series.rolling(window=window, min_periods=1).skew().fillna(0)
            
            # 差分特征
            df[f'{col}_diff'] = series.diff().fillna(0)
            df[f'{col}_pct_change'] = series.pct_change().fillna(0)
            
            # 累积特征
            df[f'{col}_cumsum'] = series.cumsum()
            df[f'{col}_cumprod'] = series.cumprod()
            df[f'{col}_cummax'] = series.cummax()
            df[f'{col}_cummin'] = series.cummin()
        
        self._log_transformation(f"为列 {columns} 创建统计特征")
        
        self.data = df
        return df
    
    def create_categorical_features(self, columns: List[str],
                                   top_k: int = 10) -> pd.DataFrame:
        """创建分类特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col not in df.columns:
                continue
            
            # 获取top K类别
            top_categories = df[col].value_counts().head(top_k).index.tolist()
            
            # 为每个top类别创建二进制特征
            for cat in top_categories:
                feature_name = f"{col}_is_{cat}"
                df[feature_name] = (df[col] == cat).astype(int)
            
            # 创建"其他"类别
            df[f"{col}_is_other"] = (~df[col].isin(top_categories)).astype(int)
        
        self._log_transformation(f"为列 {columns} 创建分类特征")
        
        self.data = df
        return df
    
    def create_binning_features(self, columns: List[str],
                               n_bins: int = 5,
                               strategy: str = 'quantile',
                               labels: Optional[List[str]] = None) -> pd.DataFrame:
        """创建分箱特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            if strategy == 'quantile':
                df[f'{col}_bin'] = pd.qcut(df[col], q=n_bins, labels=labels, duplicates='drop')
            elif strategy == 'uniform':
                df[f'{col}_bin'] = pd.cut(df[col], bins=n_bins, labels=labels, include_lowest=True)
            elif strategy == 'kmeans':
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=n_bins, random_state=42)
                df[f'{col}_bin'] = kmeans.fit_predict(df[[col]])
            
            # 独热编码分箱结果
            if pd.api.types.is_categorical_dtype(df[f'{col}_bin']):
                dummies = pd.get_dummies(df[f'{col}_bin'], prefix=f'{col}_bin')
                df = pd.concat([df, dummies], axis=1)
        
        self._log_transformation(f"为列 {columns} 创建分箱特征，{n_bins}个箱")
        
        self.data = df
        return df
    
    def create_cluster_features(self, columns: List[str],
                               n_clusters: int = 5) -> pd.DataFrame:
        """创建聚类特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        available_cols = [col for col in columns if col in df.columns]
        
        if len(available_cols) == 0:
            return df
        
        from sklearn.cluster import KMeans
        
        # 准备聚类数据
        cluster_data = df[available_cols].fillna(0)
        
        # 执行聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(cluster_data)
        
        # 添加聚类标签
        df['cluster'] = cluster_labels
        
        # 添加聚类距离特征
        distances = kmeans.transform(cluster_data)
        for i in range(n_clusters):
            df[f'cluster_distance_{i}'] = distances[:, i]
        
        self.transformers['clusterer'] = kmeans
        self._log_transformation(f"创建 {n_clusters} 个聚类特征")
        
        self.data = df
        return df
    
    def reduce_dimensions(self, columns: Optional[List[str]] = None,
                         method: str = 'pca', n_components: int = 2) -> pd.DataFrame:
        """降维"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        X = df[columns].fillna(0).values
        
        if method == 'pca':
            reducer = PCA(n_components=n_components)
        elif method == 'svd':
            reducer = TruncatedSVD(n_components=n_components)
        elif method == 'nmf':
            reducer = NMF(n_components=n_components)
        elif method == 'factor':
            reducer = FactorAnalysis(n_components=n_components)
        else:
            raise ValueError(f"不支持的降维方法: {method}")
        
        X_reduced = reducer.fit_transform(X)
        
        for i in range(n_components):
            df[f'{method}_{i+1}'] = X_reduced[:, i]
        
        self.transformers['reducer'] = reducer
        self._log_transformation(f"使用 {method} 降维到 {n_components} 维")
        
        self.data = df
        return df
    
    def select_features(self, target_column: str,
                       method: str = 'importance',
                       n_features: int = 10) -> pd.DataFrame:
        """特征选择"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if target_column not in df.columns:
            raise ValueError(f"目标列 '{target_column}' 不存在")
        
        feature_cols = [col for col in df.columns if col != target_column and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(feature_cols) <= n_features:
            return df
        
        X = df[feature_cols].fillna(0)
        y = df[target_column]
        
        if method == 'importance':
            from sklearn.ensemble import RandomForestRegressor
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X, y)
            importances = rf.feature_importances_
            selected_indices = np.argsort(importances)[-n_features:]
            selected_features = [feature_cols[i] for i in selected_indices]
        
        elif method == 'correlation':
            correlations = X.corrwith(y).abs()
            selected_features = correlations.nlargest(n_features).index.tolist()
        
        elif method == 'mutual_info':
            mi_scores = mutual_info_classif(X, y) if y.dtype == 'object' else mutual_info_regression(X, y)
            selected_indices = np.argsort(mi_scores)[-n_features:]
            selected_features = [feature_cols[i] for i in selected_indices]
        
        elif method == 'f_classif':
            selector = SelectKBest(score_func=f_classif, k=n_features)
            selector.fit(X, y)
            selected_features = [feature_cols[i] for i in selector.get_support(indices=True)]
        
        else:
            raise ValueError(f"不支持的特征选择方法: {method}")
        
        # 保留选择的特征
        keep_cols = [target_column] + selected_features
        df = df[keep_cols]
        
        self._log_transformation(f"特征选择，从 {len(feature_cols)} 个特征中选择 {n_features} 个")
        
        self.data = df
        return df
    
    def apply_custom_transformation(self, func: Callable, columns: List[str],
                                    new_column_suffix: str = '_transformed') -> pd.DataFrame:
        """应用自定义转换函数"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col in df.columns:
                new_col_name = f"{col}{new_column_suffix}"
                df[new_col_name] = df[col].apply(func)
        
        self._log_transformation(f"应用自定义转换到列 {columns}")
        
        self.data = df
        return df
    
    def log_transform(self, columns: List[str]) -> pd.DataFrame:
        """对数转换"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                # 确保值为正
                min_val = df[col].min()
                if min_val <= 0:
                    shift = abs(min_val) + 1
                    df[f'{col}_log'] = np.log(df[col] + shift)
                else:
                    df[f'{col}_log'] = np.log(df[col])
        
        self._log_transformation(f"对数转换列 {columns}")
        
        self.data = df
        return df
    
    def boxcox_transform(self, columns: List[str]) -> pd.DataFrame:
        """Box-Cox转换"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                # 确保值为正
                min_val = df[col].min()
                if min_val <= 0:
                    shift = abs(min_val) + 1
                    transformed, lambda_param = stats.boxcox(df[col] + shift)
                else:
                    transformed, lambda_param = stats.boxcox(df[col])
                
                df[f'{col}_boxcox'] = transformed
                self.transformers[f'{col}_boxcox_lambda'] = lambda_param
        
        self._log_transformation(f"Box-Cox转换列 {columns}")
        
        self.data = df
        return df
    
    def _log_transformation(self, message: str):
        """记录转换日志"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.transformation_log.append(log_entry)
        logger.info(log_entry)
    
    def get_transformation_log(self) -> List[str]:
        """获取转换日志"""
        return self.transformation_log
    
    def get_data(self) -> pd.DataFrame:
        """获取当前数据"""
        return self.data
    
    def reset(self, data: Optional[pd.DataFrame] = None):
        """重置转换器"""
        self.transformers = {}
        self.transformation_log = []
        if data is not None:
            self.data = data.copy()
        return self


def create_polynomial_features(data: pd.DataFrame, columns: List[str],
                               degree: int = 2) -> pd.DataFrame:
    """创建多项式特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_polynomial_features(columns, degree).get_data()


def create_interaction_features(data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """创建交互特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_interaction_features(columns).get_data()


def create_aggregation_features(data: pd.DataFrame, group_column: str,
                               agg_columns: List[str]) -> pd.DataFrame:
    """创建聚合特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_aggregation_features(group_column, agg_columns).get_data()


def create_time_features(data: pd.DataFrame, timestamp_column: str) -> pd.DataFrame:
    """创建时间特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_time_features(timestamp_column).get_data()


def create_text_features(data: pd.DataFrame, text_column: str) -> pd.DataFrame:
    """创建文本特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_text_features(text_column).get_data()


def create_statistical_features(data: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """创建统计特征（便捷函数）"""
    transformer = DataTransformer(data)
    return transformer.create_statistical_features(columns).get_data()


def transform_pipeline(data: pd.DataFrame, 
                      transformations: List[Dict[str, Any]]) -> pd.DataFrame:
    """转换管道
    
    Args:
        data: 输入数据
        transformations: 转换配置列表
        
    Returns:
        转换后的数据
    """
    transformer = DataTransformer(data)
    
    for config in transformations:
        transform_type = config.get('type')
        params = config.get('params', {})
        
        if transform_type == 'normalize':
            transformer.normalize(**params)
        elif transform_type == 'encode_categorical':
            transformer.encode_categorical(**params)
        elif transform_type == 'polynomial':
            transformer.create_polynomial_features(**params)
        elif transform_type == 'interaction':
            transformer.create_interaction_features(**params)
        elif transform_type == 'aggregation':
            transformer.create_aggregation_features(**params)
        elif transform_type == 'time':
            transformer.create_time_features(**params)
        elif transform_type == 'text':
            transformer.create_text_features(**params)
        elif transform_type == 'statistical':
            transformer.create_statistical_features(**params)
        elif transform_type == 'categorical':
            transformer.create_categorical_features(**params)
        elif transform_type == 'binning':
            transformer.create_binning_features(**params)
        elif transform_type == 'cluster':
            transformer.create_cluster_features(**params)
        elif transform_type == 'reduce_dimensions':
            transformer.reduce_dimensions(**params)
        elif transform_type == 'log':
            transformer.log_transform(**params)
        elif transform_type == 'boxcox':
            transformer.boxcox_transform(**params)
    
    return transformer.get_data()


def inverse_transform(transformed_data: pd.DataFrame,
                     transformers: Dict[str, Any]) -> pd.DataFrame:
    """逆转换"""
    result = transformed_data.copy()
    
    for name, transformer in transformers.items():
        if hasattr(transformer, 'inverse_transform'):
            try:
                if 'norm' in name and isinstance(transformer, DataNormalizer):
                    # 找出被转换的列
                    norm_cols = [col for col in result.columns if col.endswith('_norm')]
                    if norm_cols:
                        result[norm_cols] = transformer.inverse_transform(result[norm_cols])
            except Exception as e:
                logger.warning(f"逆转换失败 {name}: {e}")
    
    return result