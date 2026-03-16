"""
特征提取器：从数据中提取特征
负责从原始数据中提取有意义的特征，支持数值、文本、时间序列等特征提取
"""

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import re
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder

class FeatureType(Enum):
    """特征类型枚举"""
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    TEXT = "text"
    TEMPORAL = "temporal"
    STATISTICAL = "statistical"
    TRANSFORMED = "transformed"

@dataclass
class FeatureSet:
    """特征集"""
    feature_set_id: str
    features: Dict[str, Any]
    feature_names: List[str]
    feature_types: Dict[str, FeatureType]
    extraction_time: datetime
    metadata: Dict[str, Any]

@dataclass
class ExtractionConfig:
    """特征提取配置"""
    numerical_columns: List[str] = None
    categorical_columns: List[str] = None
    text_columns: List[str] = None
    temporal_columns: List[str] = None
    feature_scaling: bool = True
    text_vectorization: str = "tfidf"  # tfidf, count
    max_text_features: int = 100
    include_statistical: bool = True

class FeatureExtractor:
    """特征提取器"""
    
    def __init__(self):
        self.feature_sets: Dict[str, FeatureSet] = {}
        self.vectorizers: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.encoders: Dict[str, Any] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化特征提取器"""
        if self.initialized:
            return
            
        logging.info("初始化特征提取器...")
        self.initialized = True
        logging.info("特征提取器初始化完成")
    
    async def extract_features(self, data: List[Dict[str, Any]], config: ExtractionConfig, 
                             feature_set_id: str = None) -> FeatureSet:
        """提取特征"""
        start_time = datetime.now()
        
        if feature_set_id is None:
            feature_set_id = f"features_{int(start_time.timestamp())}"
        
        try:
            df = pd.DataFrame(data)
            features = {}
            feature_types = {}
            feature_names = []
            
            # 数值特征提取
            if config.numerical_columns:
                numerical_features = await self._extract_numerical_features(df, config.numerical_columns, config)
                features.update(numerical_features)
                for col in config.numerical_columns:
                    if col in df.columns:
                        feature_types[col] = FeatureType.NUMERICAL
                        feature_names.append(col)
            
            # 分类特征提取
            if config.categorical_columns:
                categorical_features = await self._extract_categorical_features(df, config.categorical_columns)
                features.update(categorical_features)
                for col in config.categorical_columns:
                    if col in df.columns:
                        feature_types[col] = FeatureType.CATEGORICAL
                        feature_names.append(f"{col}_encoded")
            
            # 文本特征提取
            if config.text_columns:
                text_features = await self._extract_text_features(df, config.text_columns, config)
                features.update(text_features)
                for col in config.text_columns:
                    if col in df.columns:
                        feature_types[f"{col}_vectorized"] = FeatureType.TEXT
                        # 文本特征会有多个特征名
                        feature_names.extend([f"{col}_vec_{i}" for i in range(config.max_text_features)])
            
            # 时间特征提取
            if config.temporal_columns:
                temporal_features = await self._extract_temporal_features(df, config.temporal_columns)
                features.update(temporal_features)
                for col in config.temporal_columns:
                    if col in df.columns:
                        feature_types[f"{col}_temporal"] = FeatureType.TEMPORAL
                        feature_names.extend([f"{col}_year", f"{col}_month", f"{col}_day", 
                                            f"{col}_hour", f"{col}_weekday"])
            
            # 统计特征提取
            if config.include_statistical and config.numerical_columns:
                statistical_features = await self._extract_statistical_features(df, config.numerical_columns)
                features.update(statistical_features)
                for col in config.numerical_columns:
                    if col in df.columns:
                        feature_types[f"{col}_stats"] = FeatureType.STATISTICAL
                        feature_names.extend([f"{col}_mean", f"{col}_std", f"{col}_skew", f"{col}_kurtosis"])
            
            # 特征缩放
            if config.feature_scaling and features:
                features = await self._scale_features(features, feature_set_id)
            
            feature_set = FeatureSet(
                feature_set_id=feature_set_id,
                features=features,
                feature_names=feature_names,
                feature_types=feature_types,
                extraction_time=datetime.now(),
                metadata={
                    "original_columns": list(df.columns),
                    "total_features": len(feature_names),
                    "extraction_config": config.__dict__
                }
            )
            
            self.feature_sets[feature_set_id] = feature_set
            logging.info(f"特征提取完成: {len(feature_names)} 个特征")
            
            return feature_set
            
        except Exception as e:
            logging.error(f"特征提取失败: {e}")
            raise
    
    async def _extract_numerical_features(self, df: pd.DataFrame, columns: List[str], 
                                        config: ExtractionConfig) -> Dict[str, Any]:
        """提取数值特征"""
        features = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column]
            
            # 处理缺失值
            series = series.fillna(series.mean())
            
            # 基本数值特征
            features[column] = series.values.tolist()
            
            # 对数变换（处理偏态分布）
            if series.min() > 0:  # 确保所有值都大于0
                log_col = f"{column}_log"
                features[log_col] = np.log1p(series).tolist()
        
        return features
    
    async def _extract_categorical_features(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        """提取分类特征"""
        features = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column].fillna("Unknown")
            
            # 创建或获取标签编码器
            if column not in self.encoders:
                self.encoders[column] = LabelEncoder()
                encoded_values = self.encoders[column].fit_transform(series)
            else:
                encoded_values = self.encoders[column].transform(series)
            
            features[f"{column}_encoded"] = encoded_values.tolist()
            
            # 频率编码
            value_counts = series.value_counts()
            frequency_map = value_counts.to_dict()
            frequency_encoded = series.map(frequency_map)
            features[f"{column}_frequency"] = frequency_encoded.tolist()
        
        return features
    
    async def _extract_text_features(self, df: pd.DataFrame, columns: List[str], 
                                   config: ExtractionConfig) -> Dict[str, Any]:
        """提取文本特征"""
        features = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column].fillna("").astype(str)
            
            # 文本预处理
            processed_text = series.apply(self._preprocess_text)
            
            # 选择向量化方法
            if config.text_vectorization == "tfidf":
                if column not in self.vectorizers:
                    self.vectorizers[column] = TfidfVectorizer(
                        max_features=config.max_text_features,
                        stop_words='english'
                    )
                    vectorized = self.vectorizers[column].fit_transform(processed_text)
                else:
                    vectorized = self.vectorizers[column].transform(processed_text)
            else:  # count vectorizer
                if column not in self.vectorizers:
                    self.vectorizers[column] = CountVectorizer(
                        max_features=config.max_text_features,
                        stop_words='english'
                    )
                    vectorized = self.vectorizers[column].fit_transform(processed_text)
                else:
                    vectorized = self.vectorizers[column].transform(processed_text)
            
            # 转换为密集矩阵并存储
            vectorized_dense = vectorized.toarray()
            for i in range(vectorized_dense.shape[1]):
                features[f"{column}_vec_{i}"] = vectorized_dense[:, i].tolist()
            
            # 提取文本统计特征
            text_length = series.str.len()
            features[f"{column}_length"] = text_length.tolist()
            
            word_count = series.str.split().str.len()
            features[f"{column}_word_count"] = word_count.tolist()
        
        return features
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        if not isinstance(text, str):
            return ""
        
        # 转换为小写
        text = text.lower()
        
        # 移除特殊字符和数字
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # 移除多余空格
        text = ' '.join(text.split())
        
        return text
    
    async def _extract_temporal_features(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        """提取时间特征"""
        features = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column]
            
            # 转换为datetime
            try:
                datetime_series = pd.to_datetime(series, errors='coerce')
                
                # 提取时间组件
                features[f"{column}_year"] = datetime_series.dt.year.fillna(0).astype(int).tolist()
                features[f"{column}_month"] = datetime_series.dt.month.fillna(0).astype(int).tolist()
                features[f"{column}_day"] = datetime_series.dt.day.fillna(0).astype(int).tolist()
                features[f"{column}_hour"] = datetime_series.dt.hour.fillna(0).astype(int).tolist()
                features[f"{column}_weekday"] = datetime_series.dt.weekday.fillna(0).astype(int).tolist()
                
                # 时间戳（数值形式）
                features[f"{column}_timestamp"] = datetime_series.astype(np.int64).tolist()
                
            except Exception as e:
                logging.warning(f"时间特征提取失败 {column}: {e}")
        
        return features
    
    async def _extract_statistical_features(self, df: pd.DataFrame, columns: List[str]) -> Dict[str, Any]:
        """提取统计特征"""
        features = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column]
            
            # 滚动统计特征（如果数据有序）
            if len(series) > 10:
                rolling_mean = series.rolling(window=5, min_periods=1).mean()
                rolling_std = series.rolling(window=5, min_periods=1).std()
                
                features[f"{column}_rolling_mean"] = rolling_mean.tolist()
                features[f"{column}_rolling_std"] = rolling_std.tolist()
            
            # 整体统计特征
            features[f"{column}_mean"] = [series.mean()] * len(series)
            features[f"{column}_std"] = [series.std()] * len(series)
            features[f"{column}_skew"] = [series.skew()] * len(series)
            features[f"{column}_kurtosis"] = [series.kurtosis()] * len(series)
        
        return features
    
    async def _scale_features(self, features: Dict[str, Any], feature_set_id: str) -> Dict[str, Any]:
        """特征缩放"""
        scaled_features = {}
        
        for feature_name, feature_values in features.items():
            # 跳过已经是标量值的统计特征
            if len(set(feature_values)) == 1:
                scaled_features[feature_name] = feature_values
                continue
            
            # 创建或获取缩放器
            if feature_name not in self.scalers:
                self.scalers[feature_name] = StandardScaler()
                scaled_values = self.scalers[feature_name].fit_transform(np.array(feature_values).reshape(-1, 1))
            else:
                scaled_values = self.scalers[feature_name].transform(np.array(feature_values).reshape(-1, 1))
            
            scaled_features[feature_name] = scaled_values.flatten().tolist()
        
        return scaled_features
    
    async def get_feature_set(self, feature_set_id: str) -> Optional[FeatureSet]:
        """获取特征集"""
        return self.feature_sets.get(feature_set_id)
    
    async def get_feature_matrix(self, feature_set_id: str) -> Optional[np.ndarray]:
        """获取特征矩阵"""
        feature_set = await self.get_feature_set(feature_set_id)
        if not feature_set:
            return None
        
        # 将特征字典转换为矩阵
        feature_arrays = []
        for feature_name in feature_set.feature_names:
            if feature_name in feature_set.features:
                feature_arrays.append(feature_set.features[feature_name])
        
        if feature_arrays:
            return np.column_stack(feature_arrays)
        return None
    
    async def export_features(self, feature_set_id: str, format: str = "json") -> Dict[str, Any]:
        """导出特征"""
        feature_set = await self.get_feature_set(feature_set_id)
        if not feature_set:
            return {}
        
        if format == "json":
            return {
                "feature_set_id": feature_set.feature_set_id,
                "features": feature_set.features,
                "feature_names": feature_set.feature_names,
                "feature_types": {k: v.value for k, v in feature_set.feature_types.items()},
                "metadata": feature_set.metadata
            }
        else:
            raise ValueError(f"不支持的导出格式: {format}")
    
    def get_extractor_stats(self) -> Dict[str, Any]:
        """获取提取器统计"""
        total_feature_sets = len(self.feature_sets)
        total_features = sum(len(fs.feature_names) for fs in self.feature_sets.values())
        
        feature_type_counts = {}
        for feature_set in self.feature_sets.values():
            for feature_type in feature_set.feature_types.values():
                type_name = feature_type.value
                feature_type_counts[type_name] = feature_type_counts.get(type_name, 0) + 1
        
        return {
            "total_feature_sets": total_feature_sets,
            "total_features_extracted": total_features,
            "feature_type_distribution": feature_type_counts,
            "vectorizers_count": len(self.vectorizers),
            "scalers_count": len(self.scalers),
            "encoders_count": len(self.encoders)
        }

# 全局特征提取器实例
feature_extractor = FeatureExtractor()