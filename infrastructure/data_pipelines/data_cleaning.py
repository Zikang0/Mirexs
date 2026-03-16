"""
数据清洗：清洗和预处理数据
负责数据清洗、去重、格式标准化、缺失值处理等数据预处理任务
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import re
from datetime import datetime

class CleaningRule(Enum):
    """数据清洗规则枚举"""
    REMOVE_DUPLICATES = "remove_duplicates"
    FILL_MISSING_VALUES = "fill_missing_values"
    STANDARDIZE_FORMATS = "standardize_formats"
    REMOVE_OUTLIERS = "remove_outliers"
    VALIDATE_DATA_TYPES = "validate_data_types"
    NORMALIZE_TEXT = "normalize_text"
    ENCODE_CATEGORICAL = "encode_categorical"

@dataclass
class DataQualityReport:
    """数据质量报告"""
    total_records: int
    valid_records: int
    invalid_records: int
    quality_score: float
    column_stats: Dict[str, Dict[str, Any]]
    cleaning_summary: Dict[str, int]

@dataclass
class CleaningConfig:
    """数据清洗配置"""
    rules: List[CleaningRule]
    fill_strategies: Dict[str, str] = None  # 列名 -> 填充策略
    outlier_threshold: float = 3.0  # 离群值阈值
    text_columns: List[str] = None  # 需要文本标准化的列
    categorical_columns: List[str] = None  # 需要编码的分类列

class DataCleaner:
    """数据清洗器"""
    
    def __init__(self):
        self.cleaning_history: List[DataQualityReport] = []
        self.initialized = False
        
    async def initialize(self):
        """初始化数据清洗器"""
        if self.initialized:
            return
            
        logging.info("初始化数据清洗器...")
        self.initialized = True
        logging.info("数据清洗器初始化完成")
    
    async def clean_data(self, data: List[Dict[str, Any]], config: CleaningConfig) -> List[Dict[str, Any]]:
        """清洗数据"""
        start_time = datetime.now()
        
        try:
            # 转换为DataFrame以便处理
            df = pd.DataFrame(data)
            original_count = len(df)
            
            # 应用清洗规则
            for rule in config.rules:
                if rule == CleaningRule.REMOVE_DUPLICATES:
                    df = self._remove_duplicates(df)
                elif rule == CleaningRule.FILL_MISSING_VALUES:
                    df = self._fill_missing_values(df, config.fill_strategies)
                elif rule == CleaningRule.STANDARDIZE_FORMATS:
                    df = self._standardize_formats(df)
                elif rule == CleaningRule.REMOVE_OUTLIERS:
                    df = self._remove_outliers(df, config.outlier_threshold)
                elif rule == CleaningRule.VALIDATE_DATA_TYPES:
                    df = self._validate_data_types(df)
                elif rule == CleaningRule.NORMALIZE_TEXT:
                    df = self._normalize_text(df, config.text_columns or [])
                elif rule == CleaningRule.ENCODE_CATEGORICAL:
                    df = self._encode_categorical(df, config.categorical_columns or [])
            
            # 生成质量报告
            cleaned_data = df.to_dict('records')
            quality_report = await self._generate_quality_report(data, cleaned_data, config)
            quality_report.cleaning_time = (datetime.now() - start_time).total_seconds()
            
            self.cleaning_history.append(quality_report)
            logging.info(f"数据清洗完成: {len(cleaned_data)}/{original_count} 条记录保留")
            
            return cleaned_data
            
        except Exception as e:
            logging.error(f"数据清洗失败: {e}")
            raise
    
    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除重复记录"""
        original_count = len(df)
        df_cleaned = df.drop_duplicates()
        removed_count = original_count - len(df_cleaned)
        
        if removed_count > 0:
            logging.info(f"移除 {removed_count} 条重复记录")
        
        return df_cleaned
    
    def _fill_missing_values(self, df: pd.DataFrame, strategies: Dict[str, str]) -> pd.DataFrame:
        """填充缺失值"""
        if not strategies:
            return df
        
        for column, strategy in strategies.items():
            if column not in df.columns:
                continue
                
            if strategy == "mean":
                if pd.api.types.is_numeric_dtype(df[column]):
                    df[column] = df[column].fillna(df[column].mean())
            elif strategy == "median":
                if pd.api.types.is_numeric_dtype(df[column]):
                    df[column] = df[column].fillna(df[column].median())
            elif strategy == "mode":
                df[column] = df[column].fillna(df[column].mode()[0] if not df[column].mode().empty else "Unknown")
            elif strategy == "forward_fill":
                df[column] = df[column].fillna(method='ffill')
            elif strategy == "backward_fill":
                df[column] = df[column].fillna(method='bfill')
            elif strategy == "constant":
                df[column] = df[column].fillna("Unknown")
        
        return df
    
    def _standardize_formats(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化数据格式"""
        for column in df.columns:
            # 尝试检测和转换日期格式
            if self._is_date_column(df[column]):
                df[column] = pd.to_datetime(df[column], errors='coerce')
            
            # 标准化布尔值
            elif self._is_boolean_column(df[column]):
                df[column] = df[column].map({
                    'true': True, 'false': False,
                    'yes': True, 'no': False,
                    '1': True, '0': False,
                    True: True, False: False
                })
        
        return df
    
    def _is_date_column(self, series: pd.Series) -> bool:
        """检测是否为日期列"""
        sample = series.dropna().head(10)
        if len(sample) == 0:
            return False
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}'
        ]
        
        for value in sample:
            value_str = str(value)
            if any(re.match(pattern, value_str) for pattern in date_patterns):
                return True
        
        return False
    
    def _is_boolean_column(self, series: pd.Series) -> bool:
        """检测是否为布尔列"""
        sample = series.dropna().head(10)
        if len(sample) == 0:
            return False
        
        boolean_values = ['true', 'false', 'yes', 'no', '1', '0', True, False]
        
        for value in sample:
            if str(value).lower() not in [str(b).lower() for b in boolean_values]:
                return False
        
        return True
    
    def _remove_outliers(self, df: pd.DataFrame, threshold: float) -> pd.DataFrame:
        """移除数值列的离群值"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
            df = df[z_scores < threshold]
        
        return df
    
    def _validate_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据类型"""
        # 这里可以添加更复杂的数据类型验证逻辑
        # 当前实现是基础的验证
        return df
    
    def _normalize_text(self, df: pd.DataFrame, text_columns: List[str]) -> pd.DataFrame:
        """标准化文本数据"""
        for column in text_columns:
            if column in df.columns:
                # 转换为小写
                df[column] = df[column].astype(str).str.lower()
                # 移除多余空格
                df[column] = df[column].str.strip()
                # 移除特殊字符（保留字母、数字、空格和基本标点）
                df[column] = df[column].apply(lambda x: re.sub(r'[^\w\s\.\-]', '', x))
        
        return df
    
    def _encode_categorical(self, df: pd.DataFrame, categorical_columns: List[str]) -> pd.DataFrame:
        """编码分类数据"""
        for column in categorical_columns:
            if column in df.columns:
                # 使用pandas的category类型
                df[column] = df[column].astype('category')
                # 或者使用one-hot编码
                # df = pd.get_dummies(df, columns=[column])
        
        return df
    
    async def _generate_quality_report(self, original_data: List[Dict[str, Any]], 
                                     cleaned_data: List[Dict[str, Any]], 
                                     config: CleaningConfig) -> DataQualityReport:
        """生成数据质量报告"""
        original_df = pd.DataFrame(original_data)
        cleaned_df = pd.DataFrame(cleaned_data)
        
        column_stats = {}
        for column in original_df.columns:
            original_series = original_df[column]
            cleaned_series = cleaned_df[column] if column in cleaned_df.columns else pd.Series()
            
            stats = {
                "original_count": len(original_series),
                "cleaned_count": len(cleaned_series),
                "missing_original": original_series.isnull().sum(),
                "missing_cleaned": cleaned_series.isnull().sum() if not cleaned_series.empty else 0,
                "data_type": str(original_series.dtype)
            }
            
            if pd.api.types.is_numeric_dtype(original_series):
                stats.update({
                    "min": float(original_series.min()) if not original_series.empty else 0,
                    "max": float(original_series.max()) if not original_series.empty else 0,
                    "mean": float(original_series.mean()) if not original_series.empty else 0,
                    "std": float(original_series.std()) if not original_series.empty else 0
                })
            
            column_stats[column] = stats
        
        cleaning_summary = {
            rule.value: 1 for rule in config.rules
        }
        
        quality_score = self._calculate_quality_score(original_df, cleaned_df)
        
        return DataQualityReport(
            total_records=len(original_data),
            valid_records=len(cleaned_data),
            invalid_records=len(original_data) - len(cleaned_data),
            quality_score=quality_score,
            column_stats=column_stats,
            cleaning_summary=cleaning_summary
        )
    
    def _calculate_quality_score(self, original_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> float:
        """计算数据质量分数"""
        if len(original_df) == 0:
            return 0.0
        
        # 基于多个维度计算质量分数
        completeness_score = len(cleaned_df) / len(original_df)
        
        # 计算完整性（非空值比例）
        non_null_ratio = cleaned_df.notnull().sum().sum() / (cleaned_df.shape[0] * cleaned_df.shape[1])
        
        # 计算一致性（数据类型一致性等）
        consistency_score = 0.8  # 简化实现
        
        # 综合质量分数
        quality_score = (completeness_score * 0.4 + non_null_ratio * 0.4 + consistency_score * 0.2) * 100
        
        return round(quality_score, 2)
    
    def get_cleaning_stats(self) -> Dict[str, Any]:
        """获取清洗统计"""
        if not self.cleaning_history:
            return {}
        
        total_cleanings = len(self.cleaning_history)
        total_records = sum(report.total_records for report in self.cleaning_history)
        total_valid = sum(report.valid_records for report in self.cleaning_history)
        avg_quality_score = sum(report.quality_score for report in self.cleaning_history) / total_cleanings
        
        return {
            "total_cleanings": total_cleanings,
            "total_records_processed": total_records,
            "average_quality_score": avg_quality_score,
            "average_success_rate": (total_valid / total_records * 100) if total_records > 0 else 0,
            "recent_reports": [
                {
                    "total_records": report.total_records,
                    "valid_records": report.valid_records,
                    "quality_score": report.quality_score
                }
                for report in self.cleaning_history[-5:]  # 最近5次报告
            ]
        }

# 全局数据清洗器实例
data_cleaner = DataCleaner()