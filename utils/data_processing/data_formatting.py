"""
数据格式化工具模块

提供数据格式转换、标准化、格式化等功能
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union, Callable
import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import locale
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFormatter:
    """数据格式化器类"""
    
    def __init__(self, data: Union[pd.DataFrame, pd.Series]):
        """
        初始化数据格式化器
        
        Args:
            data: 要格式化的数据
        """
        self.data = data
        self._validation()
    
    def _validation(self) -> None:
        """验证数据格式"""
        if not isinstance(self.data, (pd.DataFrame, pd.Series)):
            raise TypeError("数据必须是 pandas DataFrame 或 Series")
    
    def format_numbers(self, columns: Optional[List[str]] = None, 
                      decimal_places: int = 2,
                      thousands_separator: str = ',',
                      decimal_separator: str = '.') -> pd.DataFrame:
        """
        格式化数字列
        
        Args:
            columns: 要格式化的列名列表，None表示所有数值列
            decimal_places: 小数位数
            thousands_separator: 千位分隔符
            decimal_separator: 小数点分隔符
            
        Returns:
            格式化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            for col in columns:
                if col in df.columns:
                    # 确保是数值类型
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # 格式化数字
                    df[col] = df[col].apply(lambda x: 
                        f"{x:,.{decimal_places}f}".replace(',', thousands_separator).replace('.', decimal_separator)
                        if pd.notna(x) else x
                    )
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"格式化数字时出错: {e}")
            raise
    
    def format_currency(self, columns: List[str], 
                       currency_symbol: str = '¥',
                       decimal_places: int = 2) -> pd.DataFrame:
        """
        格式化货币列
        
        Args:
            columns: 要格式化的列名列表
            currency_symbol: 货币符号
            decimal_places: 小数位数
            
        Returns:
            格式化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            for col in columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].apply(lambda x: 
                        f"{currency_symbol}{x:,.{decimal_places}f}" if pd.notna(x) else x
                    )
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"格式化货币时出错: {e}")
            raise
    
    def format_percentage(self, columns: List[str], 
                         decimal_places: int = 1,
                         multiply_by_100: bool = True) -> pd.DataFrame:
        """
        格式化百分比列
        
        Args:
            columns: 要格式化的列名列表
            decimal_places: 小数位数
            multiply_by_100: 是否乘以100
            
        Returns:
            格式化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            for col in columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    if multiply_by_100:
                        df[col] = df[col] * 100
                    df[col] = df[col].apply(lambda x: 
                        f"{x:.{decimal_places}f}%" if pd.notna(x) else x
                    )
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"格式化百分比时出错: {e}")
            raise
    
    def format_dates(self, columns: List[str], 
                    date_format: str = '%Y-%m-%d',
                    output_format: Optional[str] = None) -> pd.DataFrame:
        """
        格式化日期列
        
        Args:
            columns: 要格式化的列名列表
            date_format: 输入日期格式
            output_format: 输出日期格式，None表示使用默认格式
            
        Returns:
            格式化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            for col in columns:
                if col in df.columns:
                    # 解析日期
                    df[col] = pd.to_datetime(df[col], format=date_format, errors='coerce')
                    
                    # 格式化日期
                    if output_format:
                        df[col] = df[col].dt.strftime(output_format)
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"格式化日期时出错: {e}")
            raise
    
    def format_text(self, columns: List[str],
                   case: str = 'title',
                   remove_special_chars: bool = False,
                   trim_whitespace: bool = True) -> pd.DataFrame:
        """
        格式化文本列
        
        Args:
            columns: 要格式化的列名列表
            case: 大小写转换 ('upper', 'lower', 'title', 'capitalize')
            remove_special_chars: 是否移除特殊字符
            trim_whitespace: 是否去除前后空格
            
        Returns:
            格式化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            for col in columns:
                if col in df.columns:
                    if trim_whitespace:
                        df[col] = df[col].astype(str).str.strip()
                    
                    if case == 'upper':
                        df[col] = df[col].str.upper()
                    elif case == 'lower':
                        df[col] = df[col].str.lower()
                    elif case == 'title':
                        df[col] = df[col].str.title()
                    elif case == 'capitalize':
                        df[col] = df[col].str.capitalize()
                    
                    if remove_special_chars:
                        df[col] = df[col].str.replace(r'[^\w\s]', '', regex=True)
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"格式化文本时出错: {e}")
            raise
    
    def standardize_categories(self, column: str, 
                             mapping: Optional[Dict[str, str]] = None,
                             case_sensitive: bool = False) -> pd.Series:
        """
        标准化分类数据
        
        Args:
            column: 要标准化的列名
            mapping: 自定义映射字典
            case_sensitive: 是否区分大小写
            
        Returns:
            标准化后的序列
        """
        try:
            if column not in self.data.columns:
                raise ValueError(f"列 '{column}' 不存在于数据中")
            
            series = self.data[column].copy()
            
            if mapping:
                # 使用自定义映射
                if not case_sensitive:
                    # 创建不区分大小写的映射
                    mapping_lower = {k.lower(): v for k, v in mapping.items()}
                    series = series.astype(str).str.lower().map(mapping_lower).fillna(series)
                else:
                    series = series.map(mapping).fillna(series)
            else:
                # 自动标准化
                if not case_sensitive:
                    series = series.astype(str).str.strip().str.lower()
                
                # 去除重复值并排序
                unique_values = sorted(series.unique())
                value_mapping = {val: f"Category_{i+1:03d}" for i, val in enumerate(unique_values)}
                series = series.map(value_mapping)
            
            return series
        except Exception as e:
            logger.error(f"标准化分类数据时出错: {e}")
            raise
    
    def normalize_data(self, columns: Optional[List[str]] = None,
                      method: str = 'minmax') -> pd.DataFrame:
        """
        数据标准化
        
        Args:
            columns: 要标准化的列名列表，None表示所有数值列
            method: 标准化方法 ('minmax', 'zscore', 'robust')
            
        Returns:
            标准化后的数据
        """
        try:
            df = self.data.copy() if isinstance(self.data, pd.DataFrame) else pd.DataFrame({'value': self.data})
            
            if columns is None:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            for col in columns:
                if col in df.columns:
                    if method == 'minmax':
                        min_val = df[col].min()
                        max_val = df[col].max()
                        if max_val != min_val:
                            df[col] = (df[col] - min_val) / (max_val - min_val)
                    
                    elif method == 'zscore':
                        mean_val = df[col].mean()
                        std_val = df[col].std()
                        if std_val != 0:
                            df[col] = (df[col] - mean_val) / std_val
                    
                    elif method == 'robust':
                        median_val = df[col].median()
                        mad_val = df[col].mad()  # 中位数绝对偏差
                        if mad_val != 0:
                            df[col] = (df[col] - median_val) / mad_val
            
            return df if isinstance(self.data, pd.DataFrame) else df['value']
        except Exception as e:
            logger.error(f"数据标准化时出错: {e}")
            raise


def format_for_export(data: pd.DataFrame, 
                     format_type: str,
                     **kwargs) -> str:
    """
    格式化数据用于导出
    
    Args:
        data: 要格式化的数据
        format_type: 导出格式 ('csv', 'json', 'xml', 'excel', 'html')
        **kwargs: 格式化参数
        
    Returns:
        格式化后的字符串
    """
    try:
        if format_type == 'csv':
            return data.to_csv(**kwargs)
        
        elif format_type == 'json':
            return data.to_json(**kwargs)
        
        elif format_type == 'xml':
            # 转换为XML
            root = ET.Element('data')
            for _, row in data.iterrows():
                row_elem = ET.SubElement(root, 'row')
                for col, val in row.items():
                    col_elem = ET.SubElement(row_elem, col)
                    col_elem.text = str(val)
            return ET.tostring(root, encoding='unicode')
        
        elif format_type == 'html':
            return data.to_html(**kwargs)
        
        elif format_type == 'excel':
            # Excel需要文件路径，这里返回提示
            return "Excel格式需要文件路径，请使用 data.to_excel(filepath)"
        
        else:
            raise ValueError(f"不支持的格式类型: {format_type}")
    
    except Exception as e:
        logger.error(f"格式化导出数据时出错: {e}")
        raise


def clean_and_format_data(data: pd.DataFrame,
                         text_columns: Optional[List[str]] = None,
                         number_columns: Optional[List[str]] = None,
                         date_columns: Optional[List[str]] = None,
                         category_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    清理并格式化数据
    
    Args:
        data: 原始数据
        text_columns: 文本列名列表
        number_columns: 数值列名列表
        date_columns: 日期列名列表
        category_columns: 分类列名列表
        
    Returns:
        清理格式化后的数据
    """
    try:
        df = data.copy()
        
        # 清理文本列
        if text_columns:
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].str.replace(r'\s+', ' ', regex=True)  # 多个空格替换为单个空格
        
        # 清理数值列
        if number_columns:
            for col in number_columns:
                if col in df.columns:
                    # 移除非数字字符（保留小数点和负号）
                    df[col] = df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 清理日期列
        if date_columns:
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 清理分类列
        if category_columns:
            for col in category_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip().str.lower()
                    # 移除空值
                    df[col] = df[col].replace(['', 'nan', 'null', 'none'], np.nan)
        
        return df
    except Exception as e:
        logger.error(f"清理格式化数据时出错: {e}")
        raise


def format_report_data(data: pd.DataFrame,
                      title: str = "数据报告",
                      include_summary: bool = True,
                      include_charts: bool = False) -> Dict[str, Any]:
    """
    格式化报告数据
    
    Args:
        data: 报告数据
        title: 报告标题
        include_summary: 是否包含摘要
        include_charts: 是否包含图表数据
        
    Returns:
        格式化后的报告数据
    """
    try:
        report = {
            'title': title,
            'timestamp': datetime.now().isoformat(),
            'data_shape': data.shape,
            'columns': list(data.columns),
            'dtypes': data.dtypes.astype(str).to_dict()
        }
        
        if include_summary:
            report['summary'] = {
                'numeric_summary': data.describe().to_dict() if len(data.select_dtypes(include=[np.number]).columns) > 0 else {},
                'categorical_summary': {},
                'missing_values': data.isnull().sum().to_dict(),
                'duplicate_rows': int(data.duplicated().sum())
            }
            
            # 分类数据摘要
            cat_cols = data.select_dtypes(include=['object']).columns
            for col in cat_cols:
                report['summary']['categorical_summary'][col] = {
                    'unique_count': int(data[col].nunique()),
                    'most_frequent': data[col].mode().iloc[0] if not data[col].mode().empty else None,
                    'value_counts': data[col].value_counts().head(10).to_dict()
                }
        
        if include_charts:
            report['chart_data'] = {}
            
            # 数值列的分布数据
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                report['chart_data'][col] = {
                    'histogram': data[col].hist(bins=20).get_figure().to_dict() if hasattr(data[col].hist(), 'get_figure') else {},
                    'boxplot_data': {
                        'min': float(data[col].min()),
                        'q1': float(data[col].quantile(0.25)),
                        'median': float(data[col].median()),
                        'q3': float(data[col].quantile(0.75)),
                        'max': float(data[col].max())
                    }
                }
        
        return report
    except Exception as e:
        logger.error(f"格式化报告数据时出错: {e}")
        raise


def create_pivot_table(data: pd.DataFrame,
                      index: Union[str, List[str]],
                      columns: Optional[Union[str, List[str]]] = None,
                      values: Optional[Union[str, List[str]]] = None,
                      aggfunc: str = 'mean') -> pd.DataFrame:
    """
    创建透视表
    
    Args:
        data: 源数据
        index: 行索引列
        columns: 列索引列
        values: 值列
        aggfunc: 聚合函数
        
    Returns:
        透视表
    """
    try:
        return pd.pivot_table(data, 
                            index=index, 
                            columns=columns, 
                            values=values, 
                            aggfunc=aggfunc,
                            fill_value=0)
    except Exception as e:
        logger.error(f"创建透视表时出错: {e}")
        raise


if __name__ == "__main__":
    # 示例用法
    print("数据格式化工具模块")
    
    # 创建示例数据
    sample_data = pd.DataFrame({
        'name': ['  John Doe  ', 'jane smith', 'BOB JOHNSON'],
        'salary': [50000.567, 75000.123, 60000.999],
        'percentage': [0.15, 0.25, 0.20],
        'date': ['2023-01-01', '2023-02-15', '2023-03-20'],
        'category': ['A', 'b', 'C']
    })
    
    # 创建格式化器
    formatter = DataFormatter(sample_data)
    
    # 格式化文本
    formatted_text = formatter.format_text(['name'], case='title', trim_whitespace=True)
    print("文本格式化完成")
    
    # 格式化数字
    formatted_numbers = formatter.format_numbers(['salary'], decimal_places=2)
    print("数字格式化完成")
    
    # 格式化百分比
    formatted_percentage = formatter.format_percentage(['percentage'])
    print("百分比格式化完成")
    
    # 标准化分类
    standardized_cat = formatter.standardize_categories('category')
    print("分类标准化完成")
    
    print("格式化示例完成")