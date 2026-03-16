"""
数据清洗模块

提供数据清洗和预处理工具，包括缺失值处理、异常值检测、重复数据处理、文本清洗等。
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Callable
from scipy import stats
import re
import string
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutlierDetector:
    """异常值检测器"""
    
    def __init__(self, method: str = 'iqr', threshold: float = 1.5):
        """初始化异常值检测器
        
        Args:
            method: 检测方法 ('iqr', 'zscore', 'modified_zscore', 'isolation_forest', 'dbscan')
            threshold: 阈值
        """
        self.method = method
        self.threshold = threshold
    
    def detect(self, data: pd.Series) -> pd.Series:
        """检测异常值
        
        Args:
            data: 输入数据
            
        Returns:
            布尔序列，True表示异常值
        """
        if self.method == 'iqr':
            return self._detect_iqr(data)
        elif self.method == 'zscore':
            return self._detect_zscore(data)
        elif self.method == 'modified_zscore':
            return self._detect_modified_zscore(data)
        elif self.method == 'isolation_forest':
            return self._detect_isolation_forest(data)
        elif self.method == 'dbscan':
            return self._detect_dbscan(data)
        else:
            raise ValueError(f"不支持的异常值检测方法: {self.method}")
    
    def _detect_iqr(self, data: pd.Series) -> pd.Series:
        """IQR方法检测异常值"""
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - self.threshold * IQR
        upper_bound = Q3 + self.threshold * IQR
        return (data < lower_bound) | (data > upper_bound)
    
    def _detect_zscore(self, data: pd.Series) -> pd.Series:
        """Z-Score方法检测异常值"""
        z_scores = np.abs(stats.zscore(data.dropna()))
        outlier_mask = pd.Series(False, index=data.index)
        outlier_mask[data.dropna().index] = z_scores > self.threshold
        return outlier_mask
    
    def _detect_modified_zscore(self, data: pd.Series) -> pd.Series:
        """修正Z-Score方法检测异常值"""
        median = data.median()
        mad = np.median(np.abs(data - median))
        if mad == 0:
            return pd.Series(False, index=data.index)
        modified_z_scores = 0.6745 * (data - median) / mad
        return np.abs(modified_z_scores) > self.threshold
    
    def _detect_isolation_forest(self, data: pd.Series) -> pd.Series:
        """孤立森林检测异常值"""
        from sklearn.ensemble import IsolationForest
        iso_forest = IsolationForest(contamination='auto', random_state=42)
        X = data.values.reshape(-1, 1)
        outlier_labels = iso_forest.fit_predict(X)
        return pd.Series(outlier_labels == -1, index=data.index)
    
    def _detect_dbscan(self, data: pd.Series) -> pd.Series:
        """DBSCAN检测异常值"""
        from sklearn.cluster import DBSCAN
        X = data.values.reshape(-1, 1)
        clustering = DBSCAN(eps=self.threshold, min_samples=5)
        cluster_labels = clustering.fit_predict(X)
        return pd.Series(cluster_labels == -1, index=data.index)
    
    def get_outlier_indices(self, data: pd.Series) -> List[int]:
        """获取异常值索引"""
        outlier_mask = self.detect(data)
        return data[outlier_mask].index.tolist()
    
    def get_outlier_stats(self, data: pd.Series) -> Dict[str, Any]:
        """获取异常值统计"""
        outlier_mask = self.detect(data)
        outlier_count = outlier_mask.sum()
        total_count = len(data)
        
        return {
            'outlier_count': int(outlier_count),
            'outlier_percentage': float(outlier_count / total_count * 100),
            'outlier_indices': data[outlier_mask].index.tolist(),
            'outlier_values': data[outlier_mask].tolist(),
            'method': self.method,
            'threshold': self.threshold
        }


class MissingValueHandler:
    """缺失值处理器"""
    
    def __init__(self, strategy: str = 'auto', fill_value: Any = None):
        """初始化缺失值处理器
        
        Args:
            strategy: 处理策略 
                     ('auto', 'drop', 'mean', 'median', 'mode', 'constant', 
                      'forward_fill', 'backward_fill', 'interpolate', 'knn')
            fill_value: 填充值
        """
        self.strategy = strategy
        self.fill_value = fill_value
        self.imputer = None
    
    def handle(self, data: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """处理缺失值
        
        Args:
            data: 输入数据
            columns: 要处理的列，None表示所有列
            
        Returns:
            处理后的数据
        """
        df = data.copy()
        
        if columns is None:
            columns = df.columns.tolist()
        
        for col in columns:
            if col not in df.columns:
                continue
            
            missing_count = df[col].isnull().sum()
            if missing_count == 0:
                continue
            
            if self.strategy == 'auto':
                self._auto_handle_column(df, col)
            elif self.strategy == 'drop':
                df = df.dropna(subset=[col])
            elif self.strategy == 'mean':
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col].fillna(df[col].mean(), inplace=True)
            elif self.strategy == 'median':
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col].fillna(df[col].median(), inplace=True)
            elif self.strategy == 'mode':
                mode_value = df[col].mode()
                if not mode_value.empty:
                    df[col].fillna(mode_value[0], inplace=True)
            elif self.strategy == 'constant':
                df[col].fillna(self.fill_value, inplace=True)
            elif self.strategy == 'forward_fill':
                df[col].fillna(method='ffill', inplace=True)
            elif self.strategy == 'backward_fill':
                df[col].fillna(method='bfill', inplace=True)
            elif self.strategy == 'interpolate':
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col].interpolate(method='linear', inplace=True)
            elif self.strategy == 'knn':
                df = self._handle_knn(df, [col])
            
            logger.info(f"列 '{col}': 处理了 {missing_count} 个缺失值")
        
        return df
    
    def _auto_handle_column(self, df: pd.DataFrame, col: str):
        """自动处理单列缺失值"""
        missing_count = df[col].isnull().sum()
        missing_ratio = missing_count / len(df)
        
        if missing_ratio > 0.5:
            # 缺失太多，删除列
            df.drop(columns=[col], inplace=True)
            logger.warning(f"列 '{col}' 缺失率 {missing_ratio:.2%} > 50%，已删除")
        elif missing_ratio < 0.01:
            # 缺失很少，删除行
            df.dropna(subset=[col], inplace=True)
        else:
            # 根据数据类型填充
            if pd.api.types.is_numeric_dtype(df[col]):
                if abs(df[col].skew()) > 1:
                    df[col].fillna(df[col].median(), inplace=True)
                else:
                    df[col].fillna(df[col].mean(), inplace=True)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col].fillna(method='ffill', inplace=True)
            else:
                mode_value = df[col].mode()
                if not mode_value.empty:
                    df[col].fillna(mode_value[0], inplace=True)
    
    def _handle_knn(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """使用KNN填充缺失值"""
        try:
            from sklearn.impute import KNNImputer
            
            # 只处理数值列
            numeric_cols = df[columns].select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                imputer = KNNImputer(n_neighbors=5)
                df_numeric = df[numeric_cols].copy()
                df_imputed = pd.DataFrame(
                    imputer.fit_transform(df_numeric),
                    columns=numeric_cols,
                    index=df.index
                )
                for col in numeric_cols:
                    df[col] = df_imputed[col]
                self.imputer = imputer
        except ImportError:
            logger.warning("KNNImputer 需要 scikit-learn，使用均值填充替代")
            for col in columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    df[col].fillna(df[col].mean(), inplace=True)
        
        return df
    
    def get_missing_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """获取缺失值统计"""
        total_cells = data.shape[0] * data.shape[1]
        missing_cells = data.isnull().sum().sum()
        
        missing_by_column = {}
        for col in data.columns:
            missing = data[col].isnull().sum()
            if missing > 0:
                missing_by_column[col] = {
                    'count': int(missing),
                    'percentage': float(missing / len(data) * 100)
                }
        
        return {
            'total_missing': int(missing_cells),
            'missing_percentage': float(missing_cells / total_cells * 100),
            'columns_with_missing': len(missing_by_column),
            'missing_by_column': missing_by_column,
            'complete_rows': int(data.dropna().shape[0]),
            'complete_rows_percentage': float(data.dropna().shape[0] / len(data) * 100)
        }


class DuplicateHandler:
    """重复数据处理"""
    
    def __init__(self, strategy: str = 'keep_first', subset: Optional[List[str]] = None):
        """初始化重复处理器
        
        Args:
            strategy: 处理策略 ('keep_first', 'keep_last', 'drop_all', 'mark', 'aggregate')
            subset: 用于判断重复的子集列
        """
        self.strategy = strategy
        self.subset = subset
    
    def handle(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理重复数据
        
        Args:
            data: 输入数据
            
        Returns:
            处理后的数据
        """
        df = data.copy()
        duplicate_count = df.duplicated(subset=self.subset).sum()
        
        if duplicate_count == 0:
            return df
        
        if self.strategy == 'keep_first':
            return df.drop_duplicates(subset=self.subset, keep='first')
        elif self.strategy == 'keep_last':
            return df.drop_duplicates(subset=self.subset, keep='last')
        elif self.strategy == 'drop_all':
            return df.drop_duplicates(subset=self.subset, keep=False)
        elif self.strategy == 'mark':
            df['is_duplicate'] = df.duplicated(subset=self.subset, keep=False)
            return df
        elif self.strategy == 'aggregate':
            return self._aggregate_duplicates(df)
        else:
            raise ValueError(f"不支持的重复处理策略: {self.strategy}")
    
    def _aggregate_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """聚合重复数据"""
        # 获取重复行的索引
        duplicate_mask = df.duplicated(subset=self.subset, keep=False)
        duplicate_indices = df[duplicate_mask].index
        
        if len(duplicate_indices) == 0:
            return df
        
        # 对重复数据进行聚合
        agg_df = df.loc[~duplicate_mask].copy()
        
        for _, group in df.loc[duplicate_indices].groupby(self.subset):
            # 对数值列取平均，对类别列取众数
            agg_row = {}
            for col in df.columns:
                if self.subset and col in self.subset:
                    agg_row[col] = group[col].iloc[0]
                elif pd.api.types.is_numeric_dtype(df[col]):
                    agg_row[col] = group[col].mean()
                else:
                    agg_row[col] = group[col].mode().iloc[0] if not group[col].mode().empty else None
            
            agg_df = pd.concat([agg_df, pd.DataFrame([agg_row])], ignore_index=True)
        
        return agg_df
    
    def get_duplicate_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """获取重复数据统计"""
        duplicate_mask = data.duplicated(subset=self.subset, keep=False)
        duplicate_count = duplicate_mask.sum()
        
        if duplicate_count > 0:
            duplicate_groups = data.groupby(self.subset).size()
            duplicate_groups = duplicate_groups[duplicate_groups > 1]
        else:
            duplicate_groups = pd.Series()
        
        return {
            'duplicate_count': int(duplicate_count),
            'duplicate_percentage': float(duplicate_count / len(data) * 100),
            'unique_count': int(len(data) - duplicate_count),
            'duplicate_groups': int(len(duplicate_groups)),
            'max_duplicates': int(duplicate_groups.max()) if not duplicate_groups.empty else 0,
            'duplicate_indices': data[duplicate_mask].index.tolist()[:10]  # 只返回前10个
        }


class DataTypeConverter:
    """数据类型转换器"""
    
    def __init__(self, infer_dates: bool = True, coerce_numeric: bool = True):
        """初始化数据类型转换器
        
        Args:
            infer_dates: 是否自动识别日期
            coerce_numeric: 是否强制转换数值
        """
        self.infer_dates = infer_dates
        self.coerce_numeric = coerce_numeric
        self.conversion_log = []
    
    def convert(self, data: pd.DataFrame, column_types: Optional[Dict[str, str]] = None) -> pd.DataFrame:
        """转换数据类型
        
        Args:
            data: 输入数据
            column_types: 列类型字典 {列名: 类型}
            
        Returns:
            转换后的数据
        """
        df = data.copy()
        self.conversion_log = []
        
        for col in df.columns:
            original_type = str(df[col].dtype)
            
            if column_types and col in column_types:
                target_type = column_types[col]
                self._convert_column(df, col, target_type)
            else:
                self._auto_convert_column(df, col)
            
            new_type = str(df[col].dtype)
            if original_type != new_type:
                self.conversion_log.append(f"{col}: {original_type} -> {new_type}")
        
        return df
    
    def _convert_column(self, df: pd.DataFrame, col: str, target_type: str):
        """转换单列数据类型"""
        try:
            if target_type == 'int':
                df[col] = pd.to_numeric(df[col], errors='coerce' if self.coerce_numeric else 'raise')
                df[col] = df[col].astype('Int64')
            elif target_type == 'float':
                df[col] = pd.to_numeric(df[col], errors='coerce' if self.coerce_numeric else 'raise')
            elif target_type == 'str' or target_type == 'string':
                df[col] = df[col].astype(str)
            elif target_type == 'bool':
                df[col] = df[col].astype(bool)
            elif target_type == 'datetime':
                df[col] = pd.to_datetime(df[col], errors='coerce')
            elif target_type == 'category':
                df[col] = df[col].astype('category')
        except Exception as e:
            logger.warning(f"转换列 '{col}' 到 {target_type} 失败: {e}")
    
    def _auto_convert_column(self, df: pd.DataFrame, col: str):
        """自动转换单列数据类型"""
        # 尝试转换为数值
        if df[col].dtype == 'object':
            # 尝试转换为数值
            try:
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                if numeric_series.notna().sum() > len(df) * 0.8:
                    df[col] = numeric_series
                    return
            except:
                pass
            
            # 尝试转换为日期
            if self.infer_dates:
                try:
                    date_series = pd.to_datetime(df[col], errors='coerce')
                    if date_series.notna().sum() > len(df) * 0.8:
                        df[col] = date_series
                        return
                except:
                    pass
            
            # 转换为类别
            if df[col].nunique() / len(df) < 0.05:  # 如果唯一值少于5%
                df[col] = df[col].astype('category')
    
    def get_conversion_log(self) -> List[str]:
        """获取转换日志"""
        return self.conversion_log


class DataStandardizer:
    """数据标准化器"""
    
    def __init__(self, standardize_text: bool = True, standardize_dates: bool = True,
                 standardize_categories: bool = True, standardize_numbers: bool = False):
        """初始化数据标准化器
        
        Args:
            standardize_text: 是否标准化文本
            standardize_dates: 是否标准化日期
            standardize_categories: 是否标准化类别
            standardize_numbers: 是否标准化数值
        """
        self.standardize_text = standardize_text
        self.standardize_dates = standardize_dates
        self.standardize_categories = standardize_categories
        self.standardize_numbers = standardize_numbers
    
    def standardize(self, data: pd.DataFrame) -> pd.DataFrame:
        """标准化数据
        
        Args:
            data: 输入数据
            
        Returns:
            标准化后的数据
        """
        df = data.copy()
        
        for col in df.columns:
            if self.standardize_text and df[col].dtype == 'object':
                df[col] = self._standardize_text_column(df[col])
            elif self.standardize_dates and pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = self._standardize_date_column(df[col])
            elif self.standardize_categories and df[col].dtype.name == 'category':
                df[col] = self._standardize_category_column(df[col])
            elif self.standardize_numbers and pd.api.types.is_numeric_dtype(df[col]):
                df[col] = self._standardize_numeric_column(df[col])
        
        return df
    
    def _standardize_text_column(self, series: pd.Series) -> pd.Series:
        """标准化文本列"""
        # 去除前后空格
        series = series.astype(str).str.strip()
        # 多个空格合并为一个
        series = series.str.replace(r'\s+', ' ', regex=True)
        # 移除特殊字符
        series = series.str.replace(r'[^\w\s]', '', regex=True)
        return series
    
    def _standardize_date_column(self, series: pd.Series) -> pd.Series:
        """标准化日期列"""
        # 统一格式为 YYYY-MM-DD
        return pd.to_datetime(series).dt.strftime('%Y-%m-%d')
    
    def _standardize_category_column(self, series: pd.Series) -> pd.Series:
        """标准化类别列"""
        # 统一为小写，去除空格
        return series.astype(str).str.lower().str.strip()
    
    def _standardize_numeric_column(self, series: pd.Series) -> pd.Series:
        """标准化数值列"""
        # 确保是数值类型
        return pd.to_numeric(series, errors='coerce')


class DataCleaner:
    """综合数据清洗器"""
    
    def __init__(self, 
                 outlier_detector: Optional[OutlierDetector] = None,
                 missing_handler: Optional[MissingValueHandler] = None,
                 duplicate_handler: Optional[DuplicateHandler] = None,
                 type_converter: Optional[DataTypeConverter] = None,
                 standardizer: Optional[DataStandardizer] = None):
        """初始化数据清洗器
        
        Args:
            outlier_detector: 异常值检测器
            missing_handler: 缺失值处理器
            duplicate_handler: 重复处理器
            type_converter: 类型转换器
            standardizer: 标准化器
        """
        self.outlier_detector = outlier_detector or OutlierDetector()
        self.missing_handler = missing_handler or MissingValueHandler()
        self.duplicate_handler = duplicate_handler or DuplicateHandler()
        self.type_converter = type_converter or DataTypeConverter()
        self.standardizer = standardizer or DataStandardizer()
        
        self.cleaning_log = []
        self.stats = {}
    
    def clean(self, data: pd.DataFrame, 
             remove_outliers: bool = False,
             handle_missing: bool = True,
             remove_duplicates: bool = True,
             convert_types: bool = True,
             standardize: bool = True,
             outlier_columns: Optional[List[str]] = None,
             missing_columns: Optional[List[str]] = None,
             duplicate_subset: Optional[List[str]] = None) -> pd.DataFrame:
        """清洗数据
        
        Args:
            data: 输入数据
            remove_outliers: 是否移除异常值
            handle_missing: 是否处理缺失值
            remove_duplicates: 是否移除重复值
            convert_types: 是否转换类型
            standardize: 是否标准化
            outlier_columns: 要检测异常值的列
            missing_columns: 要处理缺失值的列
            duplicate_subset: 判断重复的子集列
            
        Returns:
            清洗后的数据
        """
        df = data.copy()
        original_shape = df.shape
        self.cleaning_log = []
        
        # 记录初始状态
        self._log_step("开始清洗", f"原始数据形状: {original_shape}")
        
        # 转换类型
        if convert_types:
            df = self.type_converter.convert(df)
            self._log_step("类型转换", self.type_converter.get_conversion_log())
        
        # 标准化
        if standardize:
            df = self.standardizer.standardize(df)
            self._log_step("数据标准化", "完成")
        
        # 处理缺失值
        if handle_missing:
            missing_stats = self.missing_handler.get_missing_stats(df)
            self.stats['before_missing'] = missing_stats
            df = self.missing_handler.handle(df, missing_columns)
            self._log_step("缺失值处理", f"处理后缺失值: {df.isnull().sum().sum()}")
        
        # 处理重复值
        if remove_duplicates:
            duplicate_stats = self.duplicate_handler.get_duplicate_stats(df)
            self.stats['before_duplicates'] = duplicate_stats
            df = self.duplicate_handler.handle(df)
            self._log_step("重复值处理", f"处理后形状: {df.shape}")
        
        # 处理异常值
        if remove_outliers and outlier_columns:
            for col in outlier_columns:
                if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                    outlier_mask = self.outlier_detector.detect(df[col])
                    outlier_count = outlier_mask.sum()
                    if outlier_count > 0:
                        df = df[~outlier_mask]
                        self._log_step(f"异常值处理 - {col}", f"移除了 {outlier_count} 个异常值")
        
        # 记录最终状态
        self._log_step("清洗完成", f"最终数据形状: {df.shape}")
        self.stats['original_shape'] = original_shape
        self.stats['final_shape'] = df.shape
        self.stats['rows_removed'] = original_shape[0] - df.shape[0]
        self.stats['columns_removed'] = original_shape[1] - df.shape[1]
        
        return df
    
    def _log_step(self, step: str, message: str):
        """记录清洗步骤"""
        log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] {step}: {message}"
        self.cleaning_log.append(log_entry)
        logger.info(log_entry)
    
    def get_cleaning_log(self) -> List[str]:
        """获取清洗日志"""
        return self.cleaning_log
    
    def get_cleaning_stats(self) -> Dict[str, Any]:
        """获取清洗统计"""
        return self.stats


class TextCleaner:
    """文本清洗器"""
    
    def __init__(self, remove_html: bool = True, remove_urls: bool = True,
                 remove_emails: bool = True, remove_phone_numbers: bool = True,
                 remove_punctuation: bool = False, convert_lowercase: bool = True,
                 normalize_whitespace: bool = True, remove_stopwords: bool = False,
                 stopwords: Optional[List[str]] = None):
        """初始化文本清洗器
        
        Args:
            remove_html: 是否移除HTML标签
            remove_urls: 是否移除URL
            remove_emails: 是否移除邮箱
            remove_phone_numbers: 是否移除电话号码
            remove_punctuation: 是否移除标点符号
            convert_lowercase: 是否转换为小写
            normalize_whitespace: 是否标准化空白字符
            remove_stopwords: 是否移除停用词
            stopwords: 停用词列表
        """
        self.remove_html = remove_html
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phone_numbers = remove_phone_numbers
        self.remove_punctuation = remove_punctuation
        self.convert_lowercase = convert_lowercase
        self.normalize_whitespace = normalize_whitespace
        self.remove_stopwords = remove_stopwords
        self.stopwords = stopwords or self._get_default_stopwords()
    
    def _get_default_stopwords(self) -> List[str]:
        """获取默认停用词"""
        return ['a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than',
                'such', 'both', 'through', 'about', 'for', 'is', 'of', 'while', 'during']
    
    def clean(self, text: str) -> str:
        """清洗文本
        
        Args:
            text: 输入文本
            
        Returns:
            清洗后的文本
        """
        if not isinstance(text, str):
            return ""
        
        if self.remove_html:
            text = re.sub(r'<[^>]+>', '', text)
        
        if self.remove_urls:
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+])+', '', text)
        
        if self.remove_emails:
            text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        if self.remove_phone_numbers:
            text = re.sub(r'\d{3}[-.]?\d{3}[-.]?\d{4}', '', text)
        
        if self.remove_punctuation:
            text = text.translate(str.maketrans('', '', string.punctuation))
        
        if self.convert_lowercase:
            text = text.lower()
        
        if self.normalize_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()
        
        if self.remove_stopwords:
            words = text.split()
            words = [w for w in words if w not in self.stopwords]
            text = ' '.join(words)
        
        return text
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        """批量清洗文本"""
        return [self.clean(text) for text in texts]
    
    def extract_emails(self, text: str) -> List[str]:
        """提取邮箱地址"""
        return re.findall(r'\S+@\S+\.\S+', text)
    
    def extract_urls(self, text: str) -> List[str]:
        """提取URL"""
        return re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+])+', text)
    
    def extract_phone_numbers(self, text: str) -> List[str]:
        """提取电话号码"""
        return re.findall(r'\d{3}[-.]?\d{3}[-.]?\d{4}', text)


class DataProfiler:
    """数据剖析器"""
    
    def __init__(self, data: pd.DataFrame):
        """初始化数据剖析器
        
        Args:
            data: 输入数据
        """
        self.data = data
        self.profile = {}
    
    def generate_profile(self) -> Dict[str, Any]:
        """生成数据剖析报告"""
        self.profile = {
            'basic_info': self._profile_basic_info(),
            'column_stats': self._profile_columns(),
            'missing_values': self._profile_missing(),
            'duplicates': self._profile_duplicates(),
            'correlations': self._profile_correlations(),
            'outliers': self._profile_outliers(),
            'data_types': self._profile_data_types(),
            'memory_usage': self._profile_memory()
        }
        
        return self.profile
    
    def _profile_basic_info(self) -> Dict[str, Any]:
        """剖析基本信息"""
        return {
            'shape': {
                'rows': int(self.data.shape[0]),
                'columns': int(self.data.shape[1])
            },
            'size': int(self.data.size),
            'column_names': list(self.data.columns),
            'index_range': [int(self.data.index.min()), int(self.data.index.max())]
        }
    
    def _profile_columns(self) -> Dict[str, Dict[str, Any]]:
        """剖析列信息"""
        column_stats = {}
        
        for col in self.data.columns:
            stats = {
                'dtype': str(self.data[col].dtype),
                'count': int(self.data[col].count()),
                'null_count': int(self.data[col].isnull().sum()),
                'null_percentage': float(self.data[col].isnull().sum() / len(self.data) * 100),
                'unique_count': int(self.data[col].nunique())
            }
            
            if pd.api.types.is_numeric_dtype(self.data[col]):
                stats.update({
                    'mean': float(self.data[col].mean()) if not pd.isna(self.data[col].mean()) else None,
                    'std': float(self.data[col].std()) if not pd.isna(self.data[col].std()) else None,
                    'min': float(self.data[col].min()) if not pd.isna(self.data[col].min()) else None,
                    'max': float(self.data[col].max()) if not pd.isna(self.data[col].max()) else None,
                    'q1': float(self.data[col].quantile(0.25)),
                    'q2': float(self.data[col].quantile(0.5)),
                    'q3': float(self.data[col].quantile(0.75))
                })
            elif pd.api.types.is_datetime64_any_dtype(self.data[col]):
                stats.update({
                    'min_date': str(self.data[col].min()) if not pd.isna(self.data[col].min()) else None,
                    'max_date': str(self.data[col].max()) if not pd.isna(self.data[col].max()) else None,
                    'range_days': int((self.data[col].max() - self.data[col].min()).days) if not pd.isna(self.data[col].min()) else None
                })
            else:
                value_counts = self.data[col].value_counts().head(10).to_dict()
                stats['top_values'] = {str(k): int(v) for k, v in value_counts.items()}
            
            column_stats[col] = stats
        
        return column_stats
    
    def _profile_missing(self) -> Dict[str, Any]:
        """剖析缺失值"""
        missing = {
            'total_missing': int(self.data.isnull().sum().sum()),
            'missing_percentage': float(self.data.isnull().sum().sum() / self.data.size * 100),
            'columns_with_missing': []
        }
        
        for col in self.data.columns:
            missing_count = self.data[col].isnull().sum()
            if missing_count > 0:
                missing['columns_with_missing'].append({
                    'column': col,
                    'count': int(missing_count),
                    'percentage': float(missing_count / len(self.data) * 100)
                })
        
        return missing
    
    def _profile_duplicates(self) -> Dict[str, Any]:
        """剖析重复值"""
        duplicates = {
            'total_duplicates': int(self.data.duplicated().sum()),
            'duplicate_percentage': float(self.data.duplicated().sum() / len(self.data) * 100)
        }
        
        if duplicates['total_duplicates'] > 0:
            duplicate_groups = self.data.groupby(list(self.data.columns)).size()
            duplicate_groups = duplicate_groups[duplicate_groups > 1]
            duplicates['max_duplicates'] = int(duplicate_groups.max())
            duplicates['unique_duplicate_groups'] = len(duplicate_groups)
        
        return duplicates
    
    def _profile_correlations(self) -> Dict[str, Any]:
        """剖析相关性"""
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) >= 2:
            corr_matrix = self.data[numeric_cols].corr()
            
            # 找到最强相关性
            correlations = []
            for i in range(len(numeric_cols)):
                for j in range(i + 1, len(numeric_cols)):
                    corr = corr_matrix.iloc[i, j]
                    if not pd.isna(corr):
                        correlations.append({
                            'col1': numeric_cols[i],
                            'col2': numeric_cols[j],
                            'correlation': float(corr)
                        })
            
            correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            return {
                'top_correlations': correlations[:10],
                'high_correlations': [c for c in correlations if abs(c['correlation']) > 0.8]
            }
        
        return {}
    
    def _profile_outliers(self) -> Dict[str, Any]:
        """剖析异常值"""
        outliers = {}
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            Q1 = self.data[col].quantile(0.25)
            Q3 = self.data[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outlier_mask = (self.data[col] < lower_bound) | (self.data[col] > upper_bound)
            outlier_count = outlier_mask.sum()
            
            if outlier_count > 0:
                outliers[col] = {
                    'count': int(outlier_count),
                    'percentage': float(outlier_count / len(self.data) * 100),
                    'lower_bound': float(lower_bound),
                    'upper_bound': float(upper_bound)
                }
        
        return outliers
    
    def _profile_data_types(self) -> Dict[str, Any]:
        """剖析数据类型"""
        type_counts = {}
        for dtype in self.data.dtypes:
            dtype_str = str(dtype)
            type_counts[dtype_str] = type_counts.get(dtype_str, 0) + 1
        
        return {
            'type_distribution': type_counts,
            'numeric_columns': int(self.data.select_dtypes(include=[np.number]).shape[1]),
            'categorical_columns': int(self.data.select_dtypes(include=['object', 'category']).shape[1]),
            'datetime_columns': int(self.data.select_dtypes(include=['datetime64']).shape[1])
        }
    
    def _profile_memory(self) -> Dict[str, Any]:
        """剖析内存使用"""
        memory_usage = self.data.memory_usage(deep=True)
        
        return {
            'total_bytes': int(memory_usage.sum()),
            'total_mb': float(memory_usage.sum() / (1024 * 1024)),
            'per_column': {col: int(memory_usage[col]) for col in memory_usage.index}
        }


class DataValidator:
    """数据验证器"""
    
    def __init__(self, rules: Optional[Dict[str, Any]] = None):
        """初始化数据验证器
        
        Args:
            rules: 验证规则字典
        """
        self.rules = rules or {}
        self.validation_results = {}
    
    def validate(self, data: pd.DataFrame) -> Dict[str, Any]:
        """验证数据
        
        Args:
            data: 输入数据
            
        Returns:
            验证结果
        """
        results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'details': {}
        }
        
        # 验证必填列
        if 'required_columns' in self.rules:
            required_cols = self.rules['required_columns']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                results['errors'].append(f"缺少必填列: {missing_cols}")
                results['is_valid'] = False
        
        # 验证数据类型
        if 'column_types' in self.rules:
            type_errors = self._validate_column_types(data, self.rules['column_types'])
            if type_errors:
                results['errors'].extend(type_errors)
                results['is_valid'] = False
        
        # 验证数值范围
        if 'value_ranges' in self.rules:
            range_errors = self._validate_value_ranges(data, self.rules['value_ranges'])
            if range_errors:
                results['errors'].extend(range_errors)
                results['is_valid'] = False
        
        # 验证唯一性
        if 'unique_columns' in self.rules:
            unique_cols = self.rules['unique_columns']
            for col in unique_cols:
                if col in data.columns and data[col].duplicated().any():
                    results['errors'].append(f"列 '{col}' 必须唯一，但存在重复值")
                    results['is_valid'] = False
        
        # 验证值列表
        if 'allowed_values' in self.rules:
            for col, allowed_values in self.rules['allowed_values'].items():
                if col in data.columns:
                    invalid_values = data[~data[col].isin(allowed_values)][col].unique()
                    if len(invalid_values) > 0:
                        results['warnings'].append(f"列 '{col}' 包含不允许的值: {list(invalid_values)[:5]}")
        
        self.validation_results = results
        return results
    
    def _validate_column_types(self, data: pd.DataFrame, column_types: Dict[str, str]) -> List[str]:
        """验证列类型"""
        errors = []
        for col, expected_type in column_types.items():
            if col in data.columns:
                actual_type = str(data[col].dtype)
                if not self._type_matches(actual_type, expected_type):
                    errors.append(f"列 '{col}' 类型应为 {expected_type}，实际为 {actual_type}")
        return errors
    
    def _type_matches(self, actual_type: str, expected_type: str) -> bool:
        """检查类型是否匹配"""
        type_mapping = {
            'int': ['int64', 'int32', 'int16', 'int8'],
            'float': ['float64', 'float32'],
            'str': ['object', 'string'],
            'bool': ['bool', 'boolean'],
            'datetime': ['datetime64[ns]', 'datetime64']
        }
        
        if expected_type in type_mapping:
            return any(t in actual_type for t in type_mapping[expected_type])
        return actual_type == expected_type
    
    def _validate_value_ranges(self, data: pd.DataFrame, ranges: Dict[str, Tuple]) -> List[str]:
        """验证数值范围"""
        errors = []
        for col, (min_val, max_val) in ranges.items():
            if col in data.columns and pd.api.types.is_numeric_dtype(data[col]):
                if data[col].min() < min_val:
                    errors.append(f"列 '{col}' 最小值 {data[col].min()} 小于允许的最小值 {min_val}")
                if data[col].max() > max_val:
                    errors.append(f"列 '{col}' 最大值 {data[col].max()} 大于允许的最大值 {max_val}")
        return errors
    
    def get_validation_summary(self) -> str:
        """获取验证摘要"""
        if not self.validation_results:
            return "尚未执行验证"
        
        results = self.validation_results
        summary = []
        summary.append("=" * 50)
        summary.append("数据验证结果")
        summary.append("=" * 50)
        summary.append(f"验证通过: {'是' if results['is_valid'] else '否'}")
        summary.append(f"错误数: {len(results['errors'])}")
        summary.append(f"警告数: {len(results['warnings'])}")
        
        if results['errors']:
            summary.append("\n错误:")
            for error in results['errors']:
                summary.append(f"  - {error}")
        
        if results['warnings']:
            summary.append("\n警告:")
            for warning in results['warnings']:
                summary.append(f"  - {warning}")
        
        return "\n".join(summary)