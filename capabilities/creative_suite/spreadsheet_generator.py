"""
表格生成器：自动生成和分析电子表格
支持数据生成、公式计算、图表创建
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

import torch
from transformers import pipeline
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DataType(Enum):
    """数据类型枚举"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    TEXT = "text"
    BOOLEAN = "boolean"

class ColumnDefinition(BaseModel):
    """列定义"""
    name: str
    data_type: DataType
    description: str
    constraints: Optional[Dict] = None
    formula: Optional[str] = None

class SpreadsheetConfig(BaseModel):
    """表格配置"""
    row_count: int = 100
    include_formulas: bool = True
    include_charts: bool = False
    data_quality: str = "high"  # low, medium, high
    language: str = "zh"

class GeneratedSpreadsheet(BaseModel):
    """生成的表格"""
    data: pd.DataFrame
    metadata: Dict[str, Any]
    formulas: List[Dict]
    charts: List[Dict]
    data_quality_report: Dict

class SpreadsheetGenerator:
    """表格生成器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.data_generator = None
        self.formula_generator = None
        
        # 预定义的数据模式
        self.data_patterns = self._load_data_patterns()
        
        # 公式库
        self.formula_library = self._load_formula_library()
        
        logger.info("SpreadsheetGenerator initialized")
    
    def _load_data_patterns(self) -> Dict[str, Dict]:
        """加载数据模式"""
        return {
            "sales": {
                "columns": [
                    {"name": "日期", "type": DataType.TEMPORAL, "format": "date"},
                    {"name": "产品", "type": DataType.CATEGORICAL, "categories": ["产品A", "产品B", "产品C"]},
                    {"name": "区域", "type": DataType.CATEGORICAL, "categories": ["华东", "华南", "华北", "西部"]},
                    {"name": "销售额", "type": DataType.NUMERIC, "range": [1000, 50000]},
                    {"name": "数量", "type": DataType.NUMERIC, "range": [1, 100]},
                    {"name": "利润率", "type": DataType.NUMERIC, "range": [0.1, 0.4]}
                ]
            },
            "financial": {
                "columns": [
                    {"name": "月份", "type": DataType.TEMPORAL, "format": "month"},
                    {"name": "收入", "type": DataType.NUMERIC, "range": [50000, 200000]},
                    {"name": "成本", "type": DataType.NUMERIC, "range": [30000, 150000]},
                    {"name": "利润", "type": DataType.NUMERIC, "formula": "收入-成本"},
                    {"name": "利润率", "type": DataType.NUMERIC, "formula": "利润/收入"}
                ]
            },
            "hr": {
                "columns": [
                    {"name": "员工ID", "type": DataType.NUMERIC, "unique": True},
                    {"name": "姓名", "type": DataType.TEXT},
                    {"name": "部门", "type": DataType.CATEGORICAL, "categories": ["技术", "销售", "市场", "人事"]},
                    {"name": "职位", "type": DataType.CATEGORICAL, "categories": ["经理", "专员", "主管", "助理"]},
                    {"name": "薪资", "type": DataType.NUMERIC, "range": [5000, 30000]},
                    {"name": "入职日期", "type": DataType.TEMPORAL, "format": "date"}
                ]
            }
        }
    
    def _load_formula_library(self) -> Dict[str, str]:
        """加载公式库"""
        return {
            "sum": "SUM({range})",
            "average": "AVERAGE({range})",
            "max": "MAX({range})",
            "min": "MIN({range})",
            "count": "COUNT({range})",
            "growth_rate": "({current}-{previous})/{previous}",
            "percentage": "{part}/{total}",
            "if_else": "IF({condition}, {true_value}, {false_value})"
        }
    
    def load_models(self):
        """加载表格生成模型"""
        try:
            self.data_generator = pipeline(
                "text-generation",
                model="microsoft/DialoGPT-medium",
                device=0 if self.device == "cuda" else -1,
                max_length=256
            )
            
            logger.info("Spreadsheet generation models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load spreadsheet models: {e}")
            raise
    
    def generate_spreadsheet(self, 
                           template_type: str,
                           config: SpreadsheetConfig,
                           custom_columns: Optional[List[ColumnDefinition]] = None) -> GeneratedSpreadsheet:
        """
        生成电子表格
        
        Args:
            template_type: 模板类型
            config: 表格配置
            custom_columns: 自定义列定义
            
        Returns:
            GeneratedSpreadsheet: 生成的表格
        """
        try:
            if self.data_generator is None:
                self.load_models()
            
            # 获取或创建列定义
            if custom_columns:
                column_defs = custom_columns
            else:
                column_defs = self._get_column_definitions(template_type)
            
            # 生成数据
            data_frame = self._generate_data(column_defs, config)
            
            # 生成公式
            formulas = self._generate_formulas(data_frame, column_defs, config)
            
            # 应用公式
            data_frame = self._apply_formulas(data_frame, formulas)
            
            # 生成图表配置
            charts = self._generate_charts(data_frame, config)
            
            # 数据质量报告
            quality_report = self._generate_quality_report(data_frame)
            
            return GeneratedSpreadsheet(
                data=data_frame,
                metadata={
                    "template_type": template_type,
                    "row_count": config.row_count,
                    "generated_at": datetime.now().isoformat(),
                    "columns": [col.dict() for col in column_defs]
                },
                formulas=formulas,
                charts=charts,
                data_quality_report=quality_report
            )
            
        except Exception as e:
            logger.error(f"Failed to generate spreadsheet: {e}")
            raise
    
    def _get_column_definitions(self, template_type: str) -> List[ColumnDefinition]:
        """获取列定义"""
        if template_type in self.data_patterns:
            pattern = self.data_patterns[template_type]
            columns = []
            for col_def in pattern["columns"]:
                columns.append(ColumnDefinition(
                    name=col_def["name"],
                    data_type=DataType(col_def["type"]),
                    description=f"{col_def['name']}列",
                    constraints=col_def.get("constraints"),
                    formula=col_def.get("formula")
                ))
            return columns
        else:
            # 默认列定义
            return [
                ColumnDefinition(name="ID", data_type=DataType.NUMERIC, description="唯一标识"),
                ColumnDefinition(name="名称", data_type=DataType.TEXT, description="项目名称"),
                ColumnDefinition(name="数值", data_type=DataType.NUMERIC, description="主要数值")
            ]
    
    def _generate_data(self, 
                      columns: List[ColumnDefinition], 
                      config: SpreadsheetConfig) -> pd.DataFrame:
        """生成数据"""
        data = {}
        
        for column in columns:
            if column.data_type == DataType.NUMERIC:
                data[column.name] = self._generate_numeric_data(column, config)
            elif column.data_type == DataType.CATEGORICAL:
                data[column.name] = self._generate_categorical_data(column, config)
            elif column.data_type == DataType.TEMPORAL:
                data[column.name] = self._generate_temporal_data(column, config)
            elif column.data_type == DataType.TEXT:
                data[column.name] = self._generate_text_data(column, config)
            elif column.data_type == DataType.BOOLEAN:
                data[column.name] = self._generate_boolean_data(column, config)
        
        return pd.DataFrame(data)
    
    def _generate_numeric_data(self, column: ColumnDefinition, config: SpreadsheetConfig) -> List[float]:
        """生成数值数据"""
        constraints = column.constraints or {}
        
        if config.data_quality == "high":
            # 高质量数据：正态分布
            mean = constraints.get("mean", 1000)
            std = constraints.get("std", 200)
            data = np.random.normal(mean, std, config.row_count)
        elif config.data_quality == "medium":
            # 中等质量数据：均匀分布
            min_val = constraints.get("min", 0)
            max_val = constraints.get("max", 2000)
            data = np.random.uniform(min_val, max_val, config.row_count)
        else:
            # 低质量数据：随机分布，可能有异常值
            min_val = constraints.get("min", 0)
            max_val = constraints.get("max", 2000)
            data = np.random.uniform(min_val, max_val, config.row_count)
            # 添加一些异常值
            outlier_indices = np.random.choice(config.row_count, config.row_count // 10, replace=False)
            data[outlier_indices] *= 10
        
        return data.tolist()
    
    def _generate_categorical_data(self, column: ColumnDefinition, config: SpreadsheetConfig) -> List[str]:
        """生成分类数据"""
        constraints = column.constraints or {}
        categories = constraints.get("categories", ["选项A", "选项B", "选项C"])
        
        if config.data_quality == "high":
            # 高质量数据：平衡分布
            weights = [1.0] * len(categories)
        elif config.data_quality == "medium":
            # 中等质量数据：轻微不平衡
            weights = np.random.dirichlet(np.ones(len(categories))).tolist()
        else:
            # 低质量数据：高度不平衡
            weights = np.random.exponential(1, len(categories)).tolist()
            weights = [w / sum(weights) for w in weights]
        
        return np.random.choice(categories, config.row_count, p=weights).tolist()
    
    def _generate_temporal_data(self, column: ColumnDefinition, config: SpreadsheetConfig) -> List:
        """生成时间数据"""
        constraints = column.constraints or {}
        format_type = constraints.get("format", "date")
        
        start_date = datetime(2023, 1, 1)
        
        if format_type == "date":
            dates = [start_date + timedelta(days=x) for x in range(config.row_count)]
            return [date.strftime("%Y-%m-%d") for date in dates]
        elif format_type == "month":
            dates = [start_date + timedelta(days=30*x) for x in range(config.row_count)]
            return [date.strftime("%Y-%m") for date in dates]
        else:
            return [start_date + timedelta(hours=x) for x in range(config.row_count)]
    
    def _generate_text_data(self, column: ColumnDefinition, config: SpreadsheetConfig) -> List[str]:
        """生成文本数据"""
        base_texts = [
            "项目记录", "数据条目", "信息记录", "文档资料",
            "测试数据", "示例文本", "样本记录", "参考信息"
        ]
        
        if config.data_quality == "high":
            # 高质量数据：多样化的文本
            return [f"{base_texts[i % len(base_texts)]}_{i+1}" for i in range(config.row_count)]
        else:
            # 较低质量数据：可能有重复
            repetitions = max(1, config.row_count // 10)
            texts = []
            for i in range(config.row_count):
                if i % repetitions == 0:
                    texts.append(f"{base_texts[i % len(base_texts)]}_{i+1}")
                else:
                    texts.append(texts[-1])  # 重复上一个文本
            return texts
    
    def _generate_boolean_data(self, column: ColumnDefinition, config: SpreadsheetConfig) -> List[bool]:
        """生成布尔数据"""
        if config.data_quality == "high":
            prob_true = 0.5
        elif config.data_quality == "medium":
            prob_true = 0.7
        else:
            prob_true = 0.9
        
        return np.random.choice([True, False], config.row_count, p=[prob_true, 1-prob_true]).tolist()
    
    def _generate_formulas(self, 
                          data: pd.DataFrame, 
                          columns: List[ColumnDefinition],
                          config: SpreadsheetConfig) -> List[Dict]:
        """生成公式"""
        if not config.include_formulas:
            return []
        
        formulas = []
        
        # 为数值列生成统计公式
        numeric_columns = [col.name for col in columns if col.data_type == DataType.NUMERIC]
        
        for col in numeric_columns:
            formulas.extend([
                {
                    "cell": f"统计_{col}",
                    "formula": f"=SUM({col})",
                    "description": f"{col}列总和"
                },
                {
                    "cell": f"平均_{col}", 
                    "formula": f"=AVERAGE({col})",
                    "description": f"{col}列平均值"
                },
                {
                    "cell": f"最大_{col}",
                    "formula": f"=MAX({col})",
                    "description": f"{col}列最大值"
                },
                {
                    "cell": f"最小_{col}",
                    "formula": f"=MIN({col})",
                    "description": f"{col}列最小值"
                }
            ])
        
        # 处理预定义公式
        for column in columns:
            if column.formula:
                formulas.append({
                    "cell": f"计算_{column.name}",
                    "formula": f"={column.formula}",
                    "description": f"{column.name}计算列"
                })
        
        return formulas
    
    def _apply_formulas(self, data: pd.DataFrame, formulas: List[Dict]) -> pd.DataFrame:
        """应用公式到数据"""
        # 在实际实现中，这里应该使用openpyxl或类似库来设置Excel公式
        # 目前返回原始数据，公式信息在metadata中
        return data
    
    def _generate_charts(self, data: pd.DataFrame, config: SpreadsheetConfig) -> List[Dict]:
        """生成图表配置"""
        if not config.include_charts:
            return []
        
        charts = []
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object']).columns.tolist()
        
        # 柱状图
        if categorical_columns and numeric_columns:
            charts.append({
                "type": "bar",
                "title": "数据分布图",
                "x_axis": categorical_columns[0] if categorical_columns else "索引",
                "y_axis": numeric_columns[0],
                "description": "主要数据分布柱状图"
            })
        
        # 折线图（如果有时序数据）
        date_columns = [col for col in data.columns if any(keyword in col.lower() for keyword in ['日期', '时间', 'date', 'time'])]
        if date_columns and numeric_columns:
            charts.append({
                "type": "line",
                "title": "趋势图",
                "x_axis": date_columns[0],
                "y_axis": numeric_columns[0],
                "description": "数据趋势折线图"
            })
        
        # 饼图
        if categorical_columns:
            charts.append({
                "type": "pie",
                "title": "分类占比图",
                "category_column": categorical_columns[0],
                "value_column": numeric_columns[0] if numeric_columns else None,
                "description": "分类数据占比饼图"
            })
        
        return charts
    
    def _generate_quality_report(self, data: pd.DataFrame) -> Dict:
        """生成数据质量报告"""
        report = {
            "total_rows": len(data),
            "total_columns": len(data.columns),
            "completeness": {},
            "uniqueness": {},
            "data_types": {}
        }
        
        for column in data.columns:
            # 完整性
            null_count = data[column].isnull().sum()
            completeness = 1 - (null_count / len(data))
            report["completeness"][column] = completeness
            
            # 唯一性
            unique_count = data[column].nunique()
            uniqueness = unique_count / len(data) if len(data) > 0 else 0
            report["uniqueness"][column] = uniqueness
            
            # 数据类型
            report["data_types"][column] = str(data[column].dtype)
        
        # 总体质量评分
        avg_completeness = np.mean(list(report["completeness"].values()))
        avg_uniqueness = np.mean(list(report["uniqueness"].values()))
        report["overall_quality_score"] = (avg_completeness + avg_uniqueness) / 2
        
        return report
    
    def export_to_excel(self, spreadsheet: GeneratedSpreadsheet, output_path: str):
        """导出为Excel文件"""
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 写入数据
                spreadsheet.data.to_excel(writer, sheet_name='数据', index=False)
                
                # 写入元数据
                metadata_df = pd.DataFrame([spreadsheet.metadata])
                metadata_df.to_excel(writer, sheet_name='元数据', index=False)
                
                # 写入公式
                if spreadsheet.formulas:
                    formulas_df = pd.DataFrame(spreadsheet.formulas)
                    formulas_df.to_excel(writer, sheet_name='公式', index=False)
                
                # 写入图表配置
                if spreadsheet.charts:
                    charts_df = pd.DataFrame(spreadsheet.charts)
                    charts_df.to_excel(writer, sheet_name='图表', index=False)
                
                # 写入质量报告
                quality_flat = {}
                for key, value in spreadsheet.data_quality_report.items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            quality_flat[f"{key}_{subkey}"] = subvalue
                    else:
                        quality_flat[key] = value
                
                quality_df = pd.DataFrame([quality_flat])
                quality_df.to_excel(writer, sheet_name='质量报告', index=False)
            
            logger.info(f"Spreadsheet exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export spreadsheet: {e}")
            return False

# 单例实例
_spreadsheet_generator_instance = None

def get_spreadsheet_generator() -> SpreadsheetGenerator:
    """获取表格生成器单例"""
    global _spreadsheet_generator_instance
    if _spreadsheet_generator_instance is None:
        _spreadsheet_generator_instance = SpreadsheetGenerator()
    return _spreadsheet_generator_instance

