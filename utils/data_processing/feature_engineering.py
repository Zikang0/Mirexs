"""
特征工程工具模块

提供特征创建、特征选择、特征提取、特征转换等功能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from sklearn.feature_selection import SelectKBest, SelectPercentile, RFE, RFECV
from sklearn.feature_selection import chi2, f_classif, f_regression, mutual_info_classif, mutual_info_regression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.decomposition import PCA, TruncatedSVD, NMF, FactorAnalysis
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import Pipeline
from scipy import stats
import logging
from datetime import datetime
import warnings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureGenerator:
    """特征生成器"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        """初始化特征生成器
        
        Args:
            data: 输入数据
        """
        self.data = data.copy() if data is not None else None
        self.generated_features = []
        self.feature_stats = {}
    
    def set_data(self, data: pd.DataFrame) -> 'FeatureGenerator':
        """设置数据"""
        self.data = data.copy()
        return self
    
    def generate_interaction_features(self, columns: List[str], 
                                     max_interactions: int = 10) -> pd.DataFrame:
        """生成交互特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if len(numeric_cols) < 2:
            return df
        
        from itertools import combinations
        
        # 计算相关性，选择相关性最高的几对
        correlations = []
        for col1, col2 in combinations(numeric_cols, 2):
            corr = df[col1].corr(df[col2])
            if not pd.isna(corr):
                correlations.append((abs(corr), col1, col2))
        
        correlations.sort(reverse=True)
        
        # 生成交互特征
        for i, (_, col1, col2) in enumerate(correlations[:max_interactions]):
            interaction_name = f"{col1}_x_{col2}"
            df[interaction_name] = df[col1] * df[col2]
            self.generated_features.append(interaction_name)
            
            # 记录统计信息
            self.feature_stats[interaction_name] = {
                'type': 'interaction',
                'columns': [col1, col2],
                'correlation': float(correlations[i][0])
            }
        
        self.data = df
        logger.info(f"生成 {min(max_interactions, len(correlations))} 个交互特征")
        return df
    
    def generate_polynomial_features(self, columns: List[str], 
                                    degree: int = 2) -> pd.DataFrame:
        """生成多项式特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
        
        if not numeric_cols:
            return df
        
        poly = PolynomialFeatures(degree=degree, include_bias=False, interaction_only=False)
        poly_features = poly.fit_transform(df[numeric_cols])
        
        feature_names = poly.get_feature_names_out(numeric_cols)
        
        for i, name in enumerate(feature_names):
            if name not in numeric_cols:  # 避免重复原始特征
                clean_name = name.replace(' ', '_').replace('^', '_power_')
                df[clean_name] = poly_features[:, i]
                self.generated_features.append(clean_name)
                
                self.feature_stats[clean_name] = {
                    'type': 'polynomial',
                    'degree': degree,
                    'original_features': name.split()
                }
        
        self.data = df
        logger.info(f"生成 {len(feature_names) - len(numeric_cols)} 个多项式特征")
        return df
    
    def generate_ratio_features(self, column_pairs: List[Tuple[str, str]]) -> pd.DataFrame:
        """生成比率特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col1, col2 in column_pairs:
            if col1 in df.columns and col2 in df.columns:
                # 避免除零
                denominator = df[col2].replace(0, np.nan).fillna(1e-8)
                ratio_name = f"{col1}_div_{col2}"
                df[ratio_name] = df[col1] / denominator
                self.generated_features.append(ratio_name)
                
                self.feature_stats[ratio_name] = {
                    'type': 'ratio',
                    'numerator': col1,
                    'denominator': col2
                }
        
        self.data = df
        logger.info(f"生成 {len(column_pairs)} 个比率特征")
        return df
    
    def generate_aggregate_features(self, group_column: str,
                                   agg_columns: List[str],
                                   agg_functions: List[str] = ['mean', 'std', 'min', 'max']) -> pd.DataFrame:
        """生成聚合特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if group_column not in df.columns:
            raise ValueError(f"分组列 '{group_column}' 不存在")
        
        # 计算分组统计
        for agg_func in agg_functions:
            if agg_func == 'mean':
                agg_result = df.groupby(group_column)[agg_columns].transform('mean')
            elif agg_func == 'std':
                agg_result = df.groupby(group_column)[agg_columns].transform('std').fillna(0)
            elif agg_func == 'min':
                agg_result = df.groupby(group_column)[agg_columns].transform('min')
            elif agg_func == 'max':
                agg_result = df.groupby(group_column)[agg_columns].transform('max')
            elif agg_func == 'median':
                agg_result = df.groupby(group_column)[agg_columns].transform('median')
            elif agg_func == 'count':
                agg_result = df.groupby(group_column)[agg_columns].transform('count')
            elif agg_func == 'sum':
                agg_result = df.groupby(group_column)[agg_columns].transform('sum')
            else:
                continue
            
            for col in agg_columns:
                if col in agg_result.columns:
                    new_col = f"{col}_by_{group_column}_{agg_func}"
                    df[new_col] = agg_result[col]
                    self.generated_features.append(new_col)
                    
                    self.feature_stats[new_col] = {
                        'type': 'aggregate',
                        'group_column': group_column,
                        'agg_column': col,
                        'agg_function': agg_func
                    }
        
        self.data = df
        logger.info(f"生成聚合特征")
        return df
    
    def generate_window_features(self, time_column: str,
                                value_columns: List[str],
                                window_sizes: List[int] = [3, 5, 7],
                                functions: List[str] = ['mean', 'std', 'min', 'max']) -> pd.DataFrame:
        """生成窗口特征（用于时间序列）"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if time_column not in df.columns:
            raise ValueError(f"时间列 '{time_column}' 不存在")
        
        # 确保数据按时间排序
        df = df.sort_values(time_column).reset_index(drop=True)
        
        for col in value_columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            series = df[col]
            
            for window in window_sizes:
                if len(series) < window:
                    continue
                
                for func in functions:
                    if func == 'mean':
                        window_values = series.rolling(window=window, min_periods=1).mean()
                    elif func == 'std':
                        window_values = series.rolling(window=window, min_periods=1).std().fillna(0)
                    elif func == 'min':
                        window_values = series.rolling(window=window, min_periods=1).min()
                    elif func == 'max':
                        window_values = series.rolling(window=window, min_periods=1).max()
                    elif func == 'median':
                        window_values = series.rolling(window=window, min_periods=1).median()
                    elif func == 'skew':
                        window_values = series.rolling(window=window, min_periods=1).skew().fillna(0)
                    elif func == 'kurt':
                        window_values = series.rolling(window=window, min_periods=1).kurt().fillna(0)
                    else:
                        continue
                    
                    new_col = f"{col}_window_{window}_{func}"
                    df[new_col] = window_values
                    self.generated_features.append(new_col)
                    
                    self.feature_stats[new_col] = {
                        'type': 'window',
                        'column': col,
                        'window': window,
                        'function': func
                    }
        
        self.data = df
        logger.info(f"生成窗口特征")
        return df
    
    def generate_lag_features(self, value_columns: List[str],
                             lag_periods: List[int] = [1, 2, 3, 7]) -> pd.DataFrame:
        """生成滞后特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        for col in value_columns:
            if col not in df.columns:
                continue
            
            for lag in lag_periods:
                new_col = f"{col}_lag_{lag}"
                df[new_col] = df[col].shift(lag)
                self.generated_features.append(new_col)
                
                self.feature_stats[new_col] = {
                    'type': 'lag',
                    'column': col,
                    'lag': lag
                }
        
        self.data = df
        logger.info(f"生成滞后特征")
        return df
    
    def generate_text_features(self, text_column: str,
                              method: str = 'tfidf',
                              max_features: int = 100) -> pd.DataFrame:
        """生成文本特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        df = self.data.copy()
        
        if text_column not in df.columns:
            raise ValueError(f"文本列 '{text_column}' 不存在")
        
        text_data = df[text_column].fillna('').astype(str)
        
        if method == 'tfidf':
            vectorizer = TfidfVectorizer(max_features=max_features)
            text_features = vectorizer.fit_transform(text_data).toarray()
            feature_names = [f"{text_column}_tfidf_{i}" for i in range(text_features.shape[1])]
        elif method == 'count':
            vectorizer = CountVectorizer(max_features=max_features)
            text_features = vectorizer.fit_transform(text_data).toarray()
            feature_names = [f"{text_column}_count_{i}" for i in range(text_features.shape[1])]
        else:
            raise ValueError(f"不支持的文本特征方法: {method}")
        
        for i, name in enumerate(feature_names):
            df[name] = text_features[:, i]
            self.generated_features.append(name)
            
            self.feature_stats[name] = {
                'type': 'text',
                'method': method,
                'text_column': text_column
            }
        
        self.data = df
        logger.info(f"生成 {len(feature_names)} 个文本特征")
        return df
    
    def get_generated_features(self) -> List[str]:
        """获取生成的特征列表"""
        return self.generated_features
    
    def get_feature_stats(self) -> Dict[str, Any]:
        """获取特征统计信息"""
        return self.feature_stats


class FeatureSelector:
    """特征选择器"""
    
    def __init__(self, method: str = 'importance', n_features: Optional[int] = None,
                 threshold: Optional[float] = None):
        """初始化特征选择器
        
        Args:
            method: 选择方法 
                    ('importance', 'correlation', 'mutual_info', 'variance', 
                     'f_classif', 'chi2', 'rfe', 'rfecv', 'l1')
            n_features: 选择的特征数量
            threshold: 阈值（用于基于阈值的方��）
        """
        self.method = method
        self.n_features = n_features
        self.threshold = threshold
        self.selected_features = []
        self.feature_scores = {}
        self.selector = None
    
    def select(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> List[str]:
        """选择特征
        
        Args:
            X: 特征数据
            y: 目标变量（监督方法需要）
            
        Returns:
            选择的特征列表
        """
        feature_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        
        if not feature_cols:
            return []
        
        X_numeric = X[feature_cols].fillna(0)
        
        if self.method == 'variance':
            return self._select_by_variance(X_numeric)
        elif self.method == 'correlation':
            return self._select_by_correlation(X_numeric)
        elif self.method == 'importance':
            if y is None:
                raise ValueError("重要性方法需要目标变量 y")
            return self._select_by_importance(X_numeric, y)
        elif self.method == 'mutual_info':
            if y is None:
                raise ValueError("互信息方法需要目标变量 y")
            return self._select_by_mutual_info(X_numeric, y)
        elif self.method == 'f_classif':
            if y is None:
                raise ValueError("F分类方法需要目标变量 y")
            return self._select_by_f_classif(X_numeric, y)
        elif self.method == 'chi2':
            if y is None:
                raise ValueError("卡方方法需要目标变量 y")
            return self._select_by_chi2(X_numeric, y)
        elif self.method == 'rfe':
            if y is None:
                raise ValueError("RFE方法需要目标变量 y")
            return self._select_by_rfe(X_numeric, y)
        elif self.method == 'rfecv':
            if y is None:
                raise ValueError("RFECV方法需要目标变量 y")
            return self._select_by_rfecv(X_numeric, y)
        else:
            raise ValueError(f"不支持的特征选择方法: {self.method}")
    
    def _select_by_variance(self, X: pd.DataFrame) -> List[str]:
        """基于方差选择"""
        variances = X.var()
        
        if self.threshold is not None:
            selected = variances[variances > self.threshold].index.tolist()
        elif self.n_features is not None:
            selected = variances.nlargest(self.n_features).index.tolist()
        else:
            selected = X.columns.tolist()
        
        for col in selected:
            self.feature_scores[col] = float(variances[col])
        
        self.selected_features = selected
        logger.info(f"基于方差选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_correlation(self, X: pd.DataFrame) -> List[str]:
        """基于相关性选择（去除高相关特征）"""
        corr_matrix = X.corr().abs()
        
        # 找到高度相关的特征对（相关性 > 0.95）
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
        
        selected = [col for col in X.columns if col not in to_drop]
        
        # 如果需要限制数量
        if self.n_features and len(selected) > self.n_features:
            # 基于方差选择
            variances = X[selected].var()
            selected = variances.nlargest(self.n_features).index.tolist()
        
        self.selected_features = selected
        logger.info(f"基于相关性选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_importance(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于随机森林重要性选择"""
        if y.dtype in ['int64', 'int32', 'object'] and y.nunique() <= 10:
            model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        
        model.fit(X, y)
        importances = pd.Series(model.feature_importances_, index=X.columns)
        
        if self.n_features:
            selected = importances.nlargest(self.n_features).index.tolist()
        else:
            # 使用平均重要性作为阈值
            threshold = importances.mean() if self.threshold is None else self.threshold
            selected = importances[importances > threshold].index.tolist()
        
        for col in selected:
            self.feature_scores[col] = float(importances[col])
        
        self.selector = model
        self.selected_features = selected
        logger.info(f"基于重要性选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_mutual_info(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于互信息选择"""
        if y.dtype in ['int64', 'int32', 'object'] and y.nunique() <= 10:
            mi_scores = mutual_info_classif(X, y, random_state=42)
        else:
            mi_scores = mutual_info_regression(X, y, random_state=42)
        
        mi_series = pd.Series(mi_scores, index=X.columns)
        
        if self.n_features:
            selected = mi_series.nlargest(self.n_features).index.tolist()
        else:
            threshold = mi_series.mean() if self.threshold is None else self.threshold
            selected = mi_series[mi_series > threshold].index.tolist()
        
        for col in selected:
            self.feature_scores[col] = float(mi_series[col])
        
        self.selected_features = selected
        logger.info(f"基于互信息选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_f_classif(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于F统计量选择"""
        selector = SelectKBest(score_func=f_classif, k=self.n_features or 'all')
        selector.fit(X, y)
        
        scores = pd.Series(selector.scores_, index=X.columns)
        
        if self.n_features:
            selected = scores.nlargest(self.n_features).index.tolist()
        else:
            threshold = scores.mean() if self.threshold is None else self.threshold
            selected = scores[scores > threshold].index.tolist()
        
        for col in selected:
            self.feature_scores[col] = float(scores[col])
        
        self.selector = selector
        self.selected_features = selected
        logger.info(f"基于F统计量选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_chi2(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于卡方选择"""
        # 确保X为非负
        X_non_negative = X - X.min() if X.min().min() < 0 else X
        
        selector = SelectKBest(score_func=chi2, k=self.n_features or 'all')
        selector.fit(X_non_negative, y)
        
        scores = pd.Series(selector.scores_, index=X.columns)
        
        if self.n_features:
            selected = scores.nlargest(self.n_features).index.tolist()
        else:
            threshold = scores.mean() if self.threshold is None else self.threshold
            selected = scores[scores > threshold].index.tolist()
        
        for col in selected:
            self.feature_scores[col] = float(scores[col])
        
        self.selector = selector
        self.selected_features = selected
        logger.info(f"基于卡方选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_rfe(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于RFE选择"""
        from sklearn.svm import SVC, SVR
        
        if y.dtype in ['int64', 'int32', 'object'] and y.nunique() <= 10:
            estimator = SVC(kernel='linear', random_state=42)
        else:
            estimator = SVR(kernel='linear')
        
        n_features = self.n_features or max(1, X.shape[1] // 2)
        selector = RFE(estimator, n_features_to_select=n_features, step=1)
        selector.fit(X, y)
        
        selected = [X.columns[i] for i in range(len(X.columns)) if selector.support_[i]]
        
        for i, col in enumerate(X.columns):
            self.feature_scores[col] = float(selector.ranking_[i])
        
        self.selector = selector
        self.selected_features = selected
        logger.info(f"基于RFE选择 {len(selected)} 个特征")
        return selected
    
    def _select_by_rfecv(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
        """基于RFECV选择"""
        from sklearn.svm import SVC, SVR
        
        if y.dtype in ['int64', 'int32', 'object'] and y.nunique() <= 10:
            estimator = SVC(kernel='linear', random_state=42)
        else:
            estimator = SVR(kernel='linear')
        
        min_features = self.n_features or 1
        selector = RFECV(estimator, step=1, min_features_to_select=min_features, cv=5)
        selector.fit(X, y)
        
        selected = [X.columns[i] for i in range(len(X.columns)) if selector.support_[i]]
        
        for i, col in enumerate(X.columns):
            self.feature_scores[col] = float(selector.ranking_[i])
        
        self.selector = selector
        self.selected_features = selected
        logger.info(f"基于RFECV选择 {len(selected)} 个特征")
        return selected
    
    def get_selected_features(self) -> List[str]:
        """获取选择的特征"""
        return self.selected_features
    
    def get_feature_scores(self) -> Dict[str, float]:
        """获取特征分数"""
        return self.feature_scores
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """转换数据（只保留选择的特征）"""
        if not self.selected_features:
            return X
        
        available_features = [f for f in self.selected_features if f in X.columns]
        return X[available_features]
    
    def fit_transform(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> pd.DataFrame:
        """拟合并转换"""
        self.select(X, y)
        return self.transform(X)


class FeatureExtractor:
    """特征提取器"""
    
    def __init__(self, method: str = 'pca', n_components: Optional[int] = None):
        """初始化特征提取器
        
        Args:
            method: 提取方法 ('pca', 'svd', 'nmf', 'factor', 'tsne', 'umap')
            n_components: 组件数量
        """
        self.method = method
        self.n_components = n_components
        self.extractor = None
        self.feature_names = []
    
    def extract(self, X: pd.DataFrame) -> pd.DataFrame:
        """提取特征"""
        X_numeric = X.select_dtypes(include=[np.number]).fillna(0)
        
        if self.n_components is None:
            self.n_components = min(10, X_numeric.shape[1])
        
        if self.method == 'pca':
            self.extractor = PCA(n_components=self.n_components)
            X_extracted = self.extractor.fit_transform(X_numeric)
            self.feature_names = [f'PC{i+1}' for i in range(self.n_components)]
        elif self.method == 'svd':
            self.extractor = TruncatedSVD(n_components=self.n_components)
            X_extracted = self.extractor.fit_transform(X_numeric)
            self.feature_names = [f'SVD{i+1}' for i in range(self.n_components)]
        elif self.method == 'nmf':
            # 确保X非负
            X_non_negative = X_numeric - X_numeric.min() + 1e-8
            self.extractor = NMF(n_components=self.n_components, random_state=42)
            X_extracted = self.extractor.fit_transform(X_non_negative)
            self.feature_names = [f'NMF{i+1}' for i in range(self.n_components)]
        elif self.method == 'factor':
            self.extractor = FactorAnalysis(n_components=self.n_components, random_state=42)
            X_extracted = self.extractor.fit_transform(X_numeric)
            self.feature_names = [f'FA{i+1}' for i in range(self.n_components)]
        elif self.method == 'tsne':
            from sklearn.manifold import TSNE
            self.extractor = TSNE(n_components=self.n_components, random_state=42)
            X_extracted = self.extractor.fit_transform(X_numeric)
            self.feature_names = [f'TSNE{i+1}' for i in range(self.n_components)]
        elif self.method == 'umap':
            try:
                import umap
                self.extractor = umap.UMAP(n_components=self.n_components, random_state=42)
                X_extracted = self.extractor.fit_transform(X_numeric)
                self.feature_names = [f'UMAP{i+1}' for i in range(self.n_components)]
            except ImportError:
                raise ImportError("UMAP需要安装: pip install umap-learn")
        else:
            raise ValueError(f"不支持的特征提取方法: {self.method}")
        
        result_df = pd.DataFrame(X_extracted, columns=self.feature_names, index=X.index)
        logger.info(f"使用 {self.method} 提取 {self.n_components} 个特征")
        
        return result_df
    
    def get_explained_variance(self) -> Optional[np.ndarray]:
        """获取解释方差（仅适用于PCA）"""
        if self.method == 'pca' and hasattr(self.extractor, 'explained_variance_ratio_'):
            return self.extractor.explained_variance_ratio_
        return None
    
    def get_components(self) -> Optional[np.ndarray]:
        """获取组件"""
        if hasattr(self.extractor, 'components_'):
            return self.extractor.components_
        return None


class FeatureScaler:
    """特征缩放器"""
    
    def __init__(self, method: str = 'standard'):
        """初始化特征缩放器
        
        Args:
            method: 缩放方法 ('standard', 'minmax', 'robust', 'maxabs', 'unit')
        """
        self.method = method
        self.scaler = None
    
    def fit(self, X: pd.DataFrame) -> 'FeatureScaler':
        """拟合"""
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, MaxAbsScaler, Normalizer
        
        if self.method == 'standard':
            self.scaler = StandardScaler()
        elif self.method == 'minmax':
            self.scaler = MinMaxScaler()
        elif self.method == 'robust':
            self.scaler = RobustScaler()
        elif self.method == 'maxabs':
            self.scaler = MaxAbsScaler()
        elif self.method == 'unit':
            self.scaler = Normalizer()
        else:
            raise ValueError(f"不支持的缩放方法: {self.method}")
        
        self.scaler.fit(X.select_dtypes(include=[np.number]).fillna(0))
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """转换"""
        X_numeric = X.select_dtypes(include=[np.number]).fillna(0)
        X_scaled = self.scaler.transform(X_numeric)
        
        result = X.copy()
        result[X_numeric.columns] = X_scaled
        return result
    
    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """拟合并转换"""
        self.fit(X)
        return self.transform(X)
    
    def inverse_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """逆转换"""
        X_numeric = X.select_dtypes(include=[np.number]).fillna(0)
        X_inverse = self.scaler.inverse_transform(X_numeric)
        
        result = X.copy()
        result[X_numeric.columns] = X_inverse
        return result


class FeatureTransformer:
    """特征转换器"""
    
    def __init__(self):
        self.transformers = {}
    
    def log_transform(self, X: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """对数转换"""
        result = X.copy()
        
        for col in columns:
            if col in result.columns and pd.api.types.is_numeric_dtype(result[col]):
                min_val = result[col].min()
                if min_val <= 0:
                    shift = abs(min_val) + 1
                    result[f'{col}_log'] = np.log(result[col] + shift)
                else:
                    result[f'{col}_log'] = np.log(result[col])
                self.transformers[f'{col}_log'] = {'type': 'log', 'shift': shift if min_val <= 0 else 0}
        
        return result
    
    def boxcox_transform(self, X: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Box-Cox转换"""
        result = X.copy()
        
        for col in columns:
            if col in result.columns and pd.api.types.is_numeric_dtype(result[col]):
                min_val = result[col].min()
                if min_val <= 0:
                    shift = abs(min_val) + 1
                    transformed, lambda_param = stats.boxcox(result[col] + shift)
                    result[f'{col}_boxcox'] = transformed
                    self.transformers[f'{col}_boxcox'] = {
                        'type': 'boxcox',
                        'lambda': lambda_param,
                        'shift': shift
                    }
                else:
                    transformed, lambda_param = stats.boxcox(result[col])
                    result[f'{col}_boxcox'] = transformed
                    self.transformers[f'{col}_boxcox'] = {
                        'type': 'boxcox',
                        'lambda': lambda_param,
                        'shift': 0
                    }
        
        return result
    
    def yeojohnson_transform(self, X: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """Yeo-Johnson转换"""
        result = X.copy()
        
        for col in columns:
            if col in result.columns and pd.api.types.is_numeric_dtype(result[col]):
                transformed, lambda_param = stats.yeojohnson(result[col])
                result[f'{col}_yeojohnson'] = transformed
                self.transformers[f'{col}_yeojohnson'] = {
                    'type': 'yeojohnson',
                    'lambda': lambda_param
                }
        
        return result
    
    def power_transform(self, X: pd.DataFrame, columns: List[str], power: float = 2) -> pd.DataFrame:
        """幂次转换"""
        result = X.copy()
        
        for col in columns:
            if col in result.columns and pd.api.types.is_numeric_dtype(result[col]):
                # 确保值为非负
                min_val = result[col].min()
                if min_val < 0:
                    shifted = result[col] - min_val + 1
                else:
                    shifted = result[col] + 1
                
                result[f'{col}_power_{power}'] = shifted ** power
                self.transformers[f'{col}_power_{power}'] = {
                    'type': 'power',
                    'power': power,
                    'shift': -min_val + 1 if min_val < 0 else 1
                }
        
        return result
    
    def reciprocal_transform(self, X: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """倒数转换"""
        result = X.copy()
        
        for col in columns:
            if col in result.columns and pd.api.types.is_numeric_dtype(result[col]):
                # 避免除零
                safe_values = result[col].replace(0, np.nan).fillna(1e-8)
                result[f'{col}_reciprocal'] = 1 / safe_values
                self.transformers[f'{col}_reciprocal'] = {'type': 'reciprocal'}
        
        return result


class FeatureEngineer:
    """综合特征工程器"""
    
    def __init__(self, data: Optional[pd.DataFrame] = None):
        """初始化特征工程器
        
        Args:
            data: 输入数据
        """
        self.data = data.copy() if data is not None else None
        self.generator = FeatureGenerator()
        self.selector = FeatureSelector()
        self.extractor = FeatureExtractor()
        self.scaler = FeatureScaler()
        self.transformer = FeatureTransformer()
        
        self.engineering_log = []
    
    def set_data(self, data: pd.DataFrame) -> 'FeatureEngineer':
        """设置数据"""
        self.data = data.copy()
        self.generator.set_data(data)
        return self
    
    def generate_features(self, configs: List[Dict[str, Any]]) -> pd.DataFrame:
        """生成特征"""
        if self.data is None:
            raise ValueError("请先设置数据")
        
        self.generator.set_data(self.data)
        
        for config in configs:
            feature_type = config.get('type')
            params = config.get('params', {})
            
            if feature_type == 'interaction':
                self.generator.generate_interaction_features(**params)
            elif feature_type == 'polynomial':
                self.generator.generate_polynomial_features(**params)
            elif feature_type == 'ratio':
                self.generator.generate_ratio_features(**params)
            elif feature_type == 'aggregate':
                self.generator.generate_aggregate_features(**params)
            elif feature_type == 'window':
                self.generator.generate_window_features(**params)
            elif feature_type == 'lag':
                self.generator.generate_lag_features(**params)
            elif feature_type == 'text':
                self.generator.generate_text_features(**params)
            
            self._log(f"生成 {feature_type} 特征")
        
        self.data = self.generator.get_data()
        return self.data
    
    def select_features(self, X: pd.DataFrame, y: Optional[pd.Series] = None,
                       method: str = 'importance', n_features: Optional[int] = None) -> List[str]:
        """选择特征"""
        selected = self.selector.select(X, y, method=method, n_features=n_features)
        self._log(f"选择 {len(selected)} 个特征")
        return selected
    
    def extract_features(self, X: pd.DataFrame, method: str = 'pca',
                        n_components: Optional[int] = None) -> pd.DataFrame:
        """提取特征"""
        extractor = FeatureExtractor(method=method, n_components=n_components)
        extracted = extractor.extract(X)
        self._log(f"提取 {extracted.shape[1]} 个特征")
        return extracted
    
    def scale_features(self, X: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        """缩放特征"""
        scaler = FeatureScaler(method=method)
        scaled = scaler.fit_transform(X)
        self._log(f"缩放特征")
        return scaled
    
    def transform_features(self, X: pd.DataFrame, 
                          transformations: List[Dict[str, Any]]) -> pd.DataFrame:
        """转换特征"""
        transformer = FeatureTransformer()
        result = X.copy()
        
        for config in transformations:
            trans_type = config.get('type')
            columns = config.get('columns', [])
            
            if trans_type == 'log':
                result = transformer.log_transform(result, columns)
            elif trans_type == 'boxcox':
                result = transformer.boxcox_transform(result, columns)
            elif trans_type == 'yeojohnson':
                result = transformer.yeojohnson_transform(result, columns)
            elif trans_type == 'power':
                result = transformer.power_transform(result, columns)
            elif trans_type == 'reciprocal':
                result = transformer.reciprocal_transform(result, columns)
        
        self._log(f"应用 {len(transformations)} 个特征转换")
        return result
    
    def create_feature_pipeline(self, X: pd.DataFrame, y: Optional[pd.Series] = None,
                               steps: List[Dict[str, Any]]) -> pd.DataFrame:
        """创建特征工程管道"""
        result = X.copy()
        
        for step in steps:
            step_type = step.get('type')
            params = step.get('params', {})
            
            if step_type == 'generate':
                self.generator.set_data(result)
                self.generator.generate_features(**params)
                result = self.generator.get_data()
            elif step_type == 'select':
                selected = self.select_features(result, y, **params)
                result = result[selected]
            elif step_type == 'extract':
                result = self.extract_features(result, **params)
            elif step_type == 'scale':
                result = self.scale_features(result, **params)
            elif step_type == 'transform':
                result = self.transform_features(result, **params)
            
            self._log(f"完成步骤: {step_type}")
        
        return result
    
    def _log(self, message: str):
        """记录日志"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.engineering_log.append(log_entry)
        logger.info(log_entry)
    
    def get_log(self) -> List[str]:
        """获取日志"""
        return self.engineering_log
    
    def get_generated_features(self) -> List[str]:
        """获取生成的特征"""
        return self.generator.get_generated_features()
    
    def get_feature_stats(self) -> Dict[str, Any]:
        """获取特征统计"""
        return self.generator.get_feature_stats()


# 便捷函数
def select_features_by_importance(X: pd.DataFrame, y: pd.Series,
                                 n_features: int = 10) -> List[str]:
    """基于重要性选择特征"""
    selector = FeatureSelector(method='importance', n_features=n_features)
    return selector.select(X, y)


def select_features_by_correlation(X: pd.DataFrame, threshold: float = 0.9) -> List[str]:
    """基于相关性选择特征"""
    selector = FeatureSelector(method='correlation', threshold=threshold)
    return selector.select(X)


def select_features_by_variance(X: pd.DataFrame, threshold: float = 0.01) -> List[str]:
    """基于方差选择特征"""
    selector = FeatureSelector(method='variance', threshold=threshold)
    return selector.select(X)


def select_features_by_mutual_info(X: pd.DataFrame, y: pd.Series,
                                   n_features: int = 10) -> List[str]:
    """基于互信息选择特征"""
    selector = FeatureSelector(method='mutual_info', n_features=n_features)
    return selector.select(X, y)


def create_feature_pipeline(data: pd.DataFrame, y: Optional[pd.Series] = None,
                          generation_configs: Optional[List[Dict]] = None,
                          selection_config: Optional[Dict] = None,
                          extraction_config: Optional[Dict] = None,
                          scaling_config: Optional[Dict] = None,
                          transformation_configs: Optional[List[Dict]] = None) -> pd.DataFrame:
    """创建完整的特征工程管道"""
    engineer = FeatureEngineer(data)
    
    if generation_configs:
        engineer.generate_features(generation_configs)
    
    if transformation_configs:
        data = engineer.transform_features(data, transformation_configs)
    
    if scaling_config:
        data = engineer.scale_features(data, **scaling_config)
    
    if extraction_config:
        data = engineer.extract_features(data, **extraction_config)
    
    if selection_config and y is not None:
        selected = engineer.select_features(data, y, **selection_config)
        data = data[selected]
    
    return data