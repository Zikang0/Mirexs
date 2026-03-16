"""
测试断言工具模块

提供各种测试断言工具和辅助函数，用于单元测试和集成测试。
"""

from typing import Any, Dict, List, Optional, Union, Callable, Type
import json
import re
import math
from datetime import datetime, date
import pandas as pd
import numpy as np
from contextlib import contextmanager
import warnings


class AssertionError(Exception):
    """自定义断言错误"""
    pass


class BaseAssertion:
    """断言基类"""
    
    def __init__(self, value: Any, description: str = ""):
        """初始化断言
        
        Args:
            value: 要断言的值
            description: 断言描述
        """
        self.value = value
        self.description = description or f"断言值: {value}"
    
    def _format_error(self, message: str) -> str:
        """格式化错误消息"""
        return f"{self.description}\n{message}"


class ValueAssertion(BaseAssertion):
    """值断言"""
    
    def is_equal(self, expected: Any, tolerance: float = None) -> 'ValueAssertion':
        """断言值相等
        
        Args:
            expected: 期望值
            tolerance: 数值比较的容差
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值不相等时
        """
        if tolerance is not None and isinstance(self.value, (int, float)) and isinstance(expected, (int, float)):
            if abs(self.value - expected) > tolerance:
                raise AssertionError(self._format_error(
                    f"值不相等: 期望 {expected}，实际 {self.value}，容差 {tolerance}"
                ))
        elif self.value != expected:
            raise AssertionError(self._format_error(
                f"值不相等: 期望 {expected}，实际 {self.value}"
            ))
        return self
    
    def is_not_equal(self, expected: Any) -> 'ValueAssertion':
        """断言值不相等
        
        Args:
            expected: 不期望的值
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值相等时
        """
        if self.value == expected:
            raise AssertionError(self._format_error(
                f"值应该不相等，但实际相等: {self.value}"
            ))
        return self
    
    def is_greater_than(self, threshold: Union[int, float]) -> 'ValueAssertion':
        """断言值大于阈值
        
        Args:
            threshold: 阈值
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值不大于阈值时
        """
        if not isinstance(self.value, (int, float)):
            raise AssertionError(self._format_error(
                f"值必须是数字类型，实际类型: {type(self.value)}"
            ))
        
        if self.value <= threshold:
            raise AssertionError(self._format_error(
                f"值 {self.value} 不大于阈值 {threshold}"
            ))
        return self
    
    def is_less_than(self, threshold: Union[int, float]) -> 'ValueAssertion':
        """断言值小于阈值
        
        Args:
            threshold: 阈值
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值不小于阈值时
        """
        if not isinstance(self.value, (int, float)):
            raise AssertionError(self._format_error(
                f"值必须是数字类型，实际类型: {type(self.value)}"
            ))
        
        if self.value >= threshold:
            raise AssertionError(self._format_error(
                f"值 {self.value} 不小于阈值 {threshold}"
            ))
        return self
    
    def is_in_range(self, min_val: Union[int, float], max_val: Union[int, float]) -> 'ValueAssertion':
        """断言值在范围内
        
        Args:
            min_val: 最小值
            max_val: 最大值
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值不在范围内时
        """
        if not isinstance(self.value, (int, float)):
            raise AssertionError(self._format_error(
                f"值必须是数字类型，实际类型: {type(self.value)}"
            ))
        
        if not (min_val <= self.value <= max_val):
            raise AssertionError(self._format_error(
                f"值 {self.value} 不在范围 [{min_val}, {max_val}] 内"
            ))
        return self
    
    def is_none(self) -> 'ValueAssertion':
        """断言值为None
        
        Returns:
            自身
            
        Raises:
            AssertionError: 值不为None时
        """
        if self.value is not None:
            raise AssertionError(self._format_error(
                f"值应该为None，实际为: {self.value}"
            ))
        return self
    
    def is_not_none(self) -> 'ValueAssertion':
        """断言值不为None
        
        Returns:
            自身
            
        Raises:
            AssertionError: 值为None时
        """
        if self.value is None:
            raise AssertionError(self._format_error("值应该不为None"))
        return self
    
    def is_true(self) -> 'ValueAssertion':
        """断言值为True
        
        Returns:
            自身
            
        Raises:
            AssertionError: 值不为True时
        """
        if not bool(self.value):
            raise AssertionError(self._format_error(
                f"值应该为True，实际为: {self.value}"
            ))
        return self
    
    def is_false(self) -> 'ValueAssertion':
        """断言值为False
        
        Returns:
            自身
            
        Raises:
            AssertionError: 值不为False时
        """
        if bool(self.value):
            raise AssertionError(self._format_error(
                f"值应该为False，实际为: {self.value}"
            ))
        return self


class CollectionAssertion(BaseAssertion):
    """集合断言"""
    
    def has_length(self, expected_length: int) -> 'CollectionAssertion':
        """断言集合长度
        
        Args:
            expected_length: 期望长度
            
        Returns:
            自身
            
        Raises:
            AssertionError: 长度不匹配时
        """
        actual_length = len(self.value)
        if actual_length != expected_length:
            raise AssertionError(self._format_error(
                f"集合长度不匹配: 期望 {expected_length}，实际 {actual_length}"
            ))
        return self
    
    def is_empty(self) -> 'CollectionAssertion':
        """断言集合为空
        
        Returns:
            自身
            
        Raises:
            AssertionError: 集合不为空时
        """
        if len(self.value) > 0:
            raise AssertionError(self._format_error(
                f"集合应该为空，实际包含 {len(self.value)} 个元素"
            ))
        return self
    
    def is_not_empty(self) -> 'CollectionAssertion':
        """断言集合不为空
        
        Returns:
            自身
            
        Raises:
            AssertionError: 集合为空时
        """
        if len(self.value) == 0:
            raise AssertionError(self._format_error("集合应该不为空"))
        return self
    
    def contains(self, item: Any) -> 'CollectionAssertion':
        """断言集合包含指定项
        
        Args:
            item: 要检查的项
            
        Returns:
            自身
            
        Raises:
            AssertionError: 集合不包含指定项时
        """
        if item not in self.value:
            raise AssertionError(self._format_error(
                f"集合不包含项: {item}"
            ))
        return self
    
    def does_not_contain(self, item: Any) -> 'CollectionAssertion':
        """断言集合不包含指定项
        
        Args:
            item: 要检查的项
            
        Returns:
            自身
            
        Raises:
            AssertionError: 集合包含指定项时
        """
        if item in self.value:
            raise AssertionError(self._format_error(
                f"集合不应该包含项: {item}"
            ))
        return self
    
    def contains_duplicates(self) -> 'CollectionAssertion':
        """断言集合包含重复项
        
        Returns:
            自身
            
        Raises:
            AssertionError: 集合不包含重复项时
        """
        unique_items = set()
        duplicates = set()
        
        for item in self.value:
            if item in unique_items:
                duplicates.add(item)
            else:
                unique_items.add(item)
        
        if not duplicates:
            raise AssertionError(self._format_error("集合不包含重复项"))
        return self
    
    def has_no_duplicates(self) -> 'CollectionAssertion':
        """断言集合不包含重复项
        
        Returns:
            自身
            
        Raises:
            AssertionError: 集合包含重复项时
        """
        unique_items = set()
        duplicates = set()
        
        for item in self.value:
            if item in unique_items:
                duplicates.add(item)
            else:
                unique_items.add(item)
        
        if duplicates:
            raise AssertionError(self._format_error(
                f"集合包含重复项: {duplicates}"
            ))
        return self


class StringAssertion(BaseAssertion):
    """字符串断言"""
    
    def is_empty(self) -> 'StringAssertion':
        """断言字符串为空
        
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串不为空时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if self.value != "":
            raise AssertionError(self._format_error(
                f"字符串应该为空，实际为: '{self.value}'"
            ))
        return self
    
    def is_not_empty(self) -> 'StringAssertion':
        """断言字符串不为空
        
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串为空时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if self.value == "":
            raise AssertionError(self._format_error("字符串应该不为空"))
        return self
    
    def starts_with(self, prefix: str) -> 'StringAssertion':
        """断言字符串以指定前缀开始
        
        Args:
            prefix: 前缀
            
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串不以指定前缀开始时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if not self.value.startswith(prefix):
            raise AssertionError(self._format_error(
                f"字符串不以 '{prefix}' 开头，实际为: '{self.value}'"
            ))
        return self
    
    def ends_with(self, suffix: str) -> 'StringAssertion':
        """断言字符串以指定后缀结束
        
        Args:
            suffix: 后缀
            
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串不以指定后缀结束时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if not self.value.endswith(suffix):
            raise AssertionError(self._format_error(
                f"字符串不以 '{suffix}' 结尾，实际为: '{self.value}'"
            ))
        return self
    
    def contains_substring(self, substring: str) -> 'StringAssertion':
        """断言字符串包含指定子串
        
        Args:
            substring: 子串
            
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串不包含指定子串时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if substring not in self.value:
            raise AssertionError(self._format_error(
                f"字符串不包含子串 '{substring}'，实际为: '{self.value}'"
            ))
        return self
    
    def matches_pattern(self, pattern: str, flags: int = 0) -> 'StringAssertion':
        """断言字符串匹配正则表达式
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串不匹配模式时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        if not re.search(pattern, self.value, flags):
            raise AssertionError(self._format_error(
                f"字符串不匹配模式 '{pattern}'，实际为: '{self.value}'"
            ))
        return self
    
    def has_length_between(self, min_length: int, max_length: int) -> 'StringAssertion':
        """断言字符串长度在范围内
        
        Args:
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            自身
            
        Raises:
            AssertionError: 字符串长度不在范围内时
        """
        if not isinstance(self.value, str):
            raise AssertionError(self._format_error(
                f"值必须是字符串类型，实际类型: {type(self.value)}"
            ))
        
        length = len(self.value)
        if not (min_length <= length <= max_length):
            raise AssertionError(self._format_error(
                f"字符串长度 {length} 不在范围 [{min_length}, {max_length}] 内"
            ))
        return self


class DataFrameAssertion(BaseAssertion):
    """DataFrame断言"""
    
    def has_shape(self, rows: int, columns: int) -> 'DataFrameAssertion':
        """断言DataFrame形状
        
        Args:
            rows: 期望行数
            columns: 期望列数
            
        Returns:
            自身
            
        Raises:
            AssertionError: DataFrame形状不匹配时
        """
        if not isinstance(self.value, pd.DataFrame):
            raise AssertionError(self._format_error(
                f"值必须是DataFrame，实际类型: {type(self.value)}"
            ))
        
        actual_shape = self.value.shape
        if actual_shape != (rows, columns):
            raise AssertionError(self._format_error(
                f"DataFrame形状不匹配: 期望 ({rows}, {columns})，实际 {actual_shape}"
            ))
        return self
    
    def has_columns(self, expected_columns: List[str]) -> 'DataFrameAssertion':
        """断言DataFrame包含指定列
        
        Args:
            expected_columns: 期望的列名列表
            
        Returns:
            自身
            
        Raises:
            AssertionError: DataFrame不包含指定列时
        """
        if not isinstance(self.value, pd.DataFrame):
            raise AssertionError(self._format_error(
                f"值必须是DataFrame，实际类型: {type(self.value)}"
            ))
        
        actual_columns = list(self.value.columns)
        missing_columns = set(expected_columns) - set(actual_columns)
        
        if missing_columns:
            raise AssertionError(self._format_error(
                f"DataFrame缺少列: {missing_columns}"
            ))
        return self
    
    def has_no_null_values(self) -> 'DataFrameAssertion':
        """断言DataFrame无空值
        
        Returns:
            自身
            
        Raises:
            AssertionError: DataFrame包含空值时
        """
        if not isinstance(self.value, pd.DataFrame):
            raise AssertionError(self._format_error(
                f"值必须是DataFrame，实际类型: {type(self.value)}"
            ))
        
        null_count = self.value.isnull().sum().sum()
        if null_count > 0:
            raise AssertionError(self._format_error(
                f"DataFrame包含 {null_count} 个空值"
            ))
        return self
    
    def has_duplicate_rows(self) -> 'DataFrameAssertion':
        """断言DataFrame有重复行
        
        Returns:
            自身
            
        Raises:
            AssertionError: DataFrame没有重复行时
        """
        if not isinstance(self.value, pd.DataFrame):
            raise AssertionError(self._format_error(
                f"值必须是DataFrame，实际类型: {type(self.value)}"
            ))
        
        if not self.value.duplicated().any():
            raise AssertionError(self._format_error("DataFrame没有重复行"))
        return self
    
    def has_no_duplicate_rows(self) -> 'DataFrameAssertion':
        """断言DataFrame无重复行
        
        Returns:
            自身
            
        Raises:
            AssertionError: DataFrame有重复行时
        """
        if not isinstance(self.value, pd.DataFrame):
            raise AssertionError(self._format_error(
                f"值必须是DataFrame，实际类型: {type(self.value)}"
            ))
        
        duplicate_count = self.value.duplicated().sum()
        if duplicate_count > 0:
            raise AssertionError(self._format_error(
                f"DataFrame有 {duplicate_count} 行重复"
            ))
        return self


class ExceptionAssertion(BaseAssertion):
    """异常断言"""
    
    def raises(self, exception_type: Type[Exception], message: str = None) -> 'ExceptionAssertion':
        """断言函数抛出指定异常
        
        Args:
            exception_type: 异常类型
            message: 期望的异常消息（可选）
            
        Returns:
            自身
            
        Raises:
            AssertionError: 没有抛出指定异常或异常消息不匹配时
        """
        if not callable(self.value):
            raise AssertionError(self._format_error(
                f"值必须是可调用对象，实际类型: {type(self.value)}"
            ))
        
        try:
            self.value()
            raise AssertionError(self._format_error(
                f"没有抛出异常 {exception_type.__name__}"
            ))
        except exception_type as e:
            if message and message not in str(e):
                raise AssertionError(self._format_error(
                    f"异常消息不匹配: 期望包含 '{message}'，实际为 '{str(e)}'"
                ))
        except Exception as e:
            raise AssertionError(self._format_error(
                f"抛出了错误的异常类型: 期望 {exception_type.__name__}，实际 {type(e).__name__}"
            ))
        
        return self
    
    def does_not_raise(self) -> 'ExceptionAssertion':
        """断言函数不抛出异常
        
        Returns:
            自身
            
        Raises:
            AssertionError: 函数抛出异常时
        """
        if not callable(self.value):
            raise AssertionError(self._format_error(
                f"值必须是可调用对象，实际类型: {type(self.value)}"
            ))
        
        try:
            self.value()
        except Exception as e:
            raise AssertionError(self._format_error(
                f"不应该抛出异常，但抛出了: {type(e).__name__}: {str(e)}"
            ))
        
        return self


class JSONAssertion(BaseAssertion):
    """JSON断言"""
    
    def is_valid_json(self) -> 'JSONAssertion':
        """断言是有效的JSON
        
        Returns:
            自身
            
        Raises:
            AssertionError: 不是有效JSON时
        """
        try:
            json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            raise AssertionError(self._format_error(
                f"不是有效的JSON: {self.value}"
            ))
        return self
    
    def has_key(self, key: str) -> 'JSONAssertion':
        """断言JSON包含指定键
        
        Args:
            key: 要检查的键
            
        Returns:
            自身
            
        Raises:
            AssertionError: JSON不包含指定键时
        """
        try:
            data = json.loads(self.value) if isinstance(self.value, str) else self.value
        except (json.JSONDecodeError, TypeError):
            raise AssertionError(self._format_error("不是有效的JSON"))
        
        if key not in data:
            raise AssertionError(self._format_error(
                f"JSON不包含键 '{key}'"
            ))
        return self
    
    def has_value_for_key(self, key: str, expected_value: Any) -> 'JSONAssertion':
        """断言JSON键的值匹配期望值
        
        Args:
            key: 键
            expected_value: 期望值
            
        Returns:
            自身
            
        Raises:
            AssertionError: 值不匹配时
        """
        try:
            data = json.loads(self.value) if isinstance(self.value, str) else self.value
        except (json.JSONDecodeError, TypeError):
            raise AssertionError(self._format_error("不是有效的JSON"))
        
        if key not in data:
            raise AssertionError(self._format_error(
                f"JSON不包含键 '{key}'"
            ))
        
        actual_value = data[key]
        if actual_value != expected_value:
            raise AssertionError(self._format_error(
                f"键 '{key}' 的值不匹配: 期望 {expected_value}，实际 {actual_value}"
            ))
        return self


class Assert:
    """断言工具类"""
    
    @staticmethod
    def that(value: Any, description: str = "") -> ValueAssertion:
        """创建值断言
        
        Args:
            value: 要断言的值
            description: 断言描述
            
        Returns:
            值断言对象
        """
        return ValueAssertion(value, description)
    
    @staticmethod
    def collection(value: Any, description: str = "") -> CollectionAssertion:
        """创建集合断言
        
        Args:
            value: 要断言的集合
            description: 断言描述
            
        Returns:
            集合断言对象
        """
        return CollectionAssertion(value, description)
    
    @staticmethod
    def string(value: str, description: str = "") -> StringAssertion:
        """创建字符串断言
        
        Args:
            value: 要断言的字符串
            description: 断言描述
            
        Returns:
            字符串断言对象
        """
        return StringAssertion(value, description)
    
    @staticmethod
    def dataframe(value: pd.DataFrame, description: str = "") -> DataFrameAssertion:
        """创建DataFrame断言
        
        Args:
            value: 要断言的DataFrame
            description: 断言描述
            
        Returns:
            DataFrame断言对象
        """
        return DataFrameAssertion(value, description)
    
    @staticmethod
    def exception(func: Callable, description: str = "") -> ExceptionAssertion:
        """创建异常断言
        
        Args:
            func: 要测试的函数
            description: 断言描述
            
        Returns:
            异常断言对象
        """
        return ExceptionAssertion(func, description)
    
    @staticmethod
    def json(value: Union[str, dict], description: str = "") -> JSONAssertion:
        """创建JSON断言
        
        Args:
            value: 要断言的JSON数据
            description: 断言描述
            
        Returns:
            JSON断言对象
        """
        return JSONAssertion(value, description)
    
    @staticmethod
    @contextmanager
    def suppress_warnings():
        """上下文管理器：抑制警告"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            yield
    
    @staticmethod
    def all_equal(*values: Any) -> bool:
        """断言所有值相等
        
        Args:
            *values: 要比较的值
            
        Returns:
            是否所有值相等
        """
        if len(values) < 2:
            return True
        
        first_value = values[0]
        return all(value == first_value for value in values[1:])
    
    @staticmethod
    def all_unique(*values: Any) -> bool:
        """断言所有值唯一
        
        Args:
            *values: 要检查的值
            
        Returns:
            是否所有值唯一
        """
        return len(values) == len(set(values))
    
    @staticmethod
    def approx_equal(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
        """断言两个浮点数近似相等
        
        Args:
            actual: 实际值
            expected: 期望值
            tolerance: 容差
            
        Returns:
            是否近似相等
        """
        return abs(actual - expected) <= tolerance


class TestDataValidator:
    """测试数据验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否有效
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式
        
        Args:
            phone: 手机号
            
        Returns:
            是否有效
        """
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式
        
        Args:
            url: URL地址
            
        Returns:
            是否有效
        """
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_date(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
        """验证日期格式
        
        Args:
            date_str: 日期字符串
            format_str: 日期格式
            
        Returns:
            是否有效
        """
        try:
            datetime.strptime(date_str, format_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址格式
        
        Args:
            ip: IP地址
            
        Returns:
            是否有效
        """
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        
        try:
            parts = ip.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        except ValueError:
            return False


class PerformanceAssertion(BaseAssertion):
    """性能断言"""
    
    def executes_within(self, time_limit: float) -> 'PerformanceAssertion':
        """断言函数在指定时间内执行完成
        
        Args:
            time_limit: 时间限制（秒）
            
        Returns:
            自身
            
        Raises:
            AssertionError: 执行时间超过限制时
        """
        if not callable(self.value):
            raise AssertionError(self._format_error(
                f"值必须是可调用对象，实际类型: {type(self.value)}"
            ))
        
        import time
        start_time = time.time()
        self.value()
        end_time = time.time()
        
        execution_time = end_time - start_time
        if execution_time > time_limit:
            raise AssertionError(self._format_error(
                f"执行时间 {execution_time:.4f}秒 超过限制 {time_limit}秒"
            ))
        
        return self
    
    def memory_usage_below(self, memory_limit: int) -> 'PerformanceAssertion':
        """断言函数内存使用量低于限制
        
        Args:
            memory_limit: 内存限制（MB）
            
        Returns:
            自身
            
        Raises:
            AssertionError: 内存使用量超过限制时
        """
        if not callable(self.value):
            raise AssertionError(self._format_error(
                f"值必须是可调用对象，实际类型: {type(self.value)}"
            ))
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        self.value()
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        
        if memory_used > memory_limit:
            raise AssertionError(self._format_error(
                f"内存使用量 {memory_used:.2f}MB 超过限制 {memory_limit}MB"
            ))
        
        return self


def assert_performance(func: Callable, time_limit: float = None, memory_limit: int = None):
    """性能断言装饰器
    
    Args:
        func: 要测试的函数
        time_limit: 时间限制（秒）
        memory_limit: 内存限制（MB）
    """
    def wrapper(*args, **kwargs):
        if time_limit is not None:
            PerformanceAssertion(func).executes_within(time_limit)
        if memory_limit is not None:
            PerformanceAssertion(func).memory_usage_below(memory_limit)
        return func(*args, **kwargs)
    return wrapper


def assert_type(value: Any, expected_type: Union[Type, tuple]) -> None:
    """断言值的类型
    
    Args:
        value: 要检查的值
        expected_type: 期望的类型
    
    Raises:
        AssertionError: 类型不匹配时
    """
    if not isinstance(value, expected_type):
        raise AssertionError(
            f"类型不匹配: 期望 {expected_type}，实际 {type(value)}"
        )


def assert_range(value: Union[int, float], min_val: Union[int, float], 
                max_val: Union[int, float], inclusive: bool = True) -> None:
    """断言值在范围内
    
    Args:
        value: 要检查的值
        min_val: 最小值
        max_val: 最大值
        inclusive: 是否包含边界值
    
    Raises:
        AssertionError: 值不在范围内时
    """
    if not isinstance(value, (int, float)):
        raise AssertionError(f"值必须是数字类型，实际类型: {type(value)}")
    
    if inclusive:
        if not (min_val <= value <= max_val):
            raise AssertionError(
                f"值 {value} 不在范围 [{min_val}, {max_val}] 内"
            )
    else:
        if not (min_val < value < max_val):
            raise AssertionError(
                f"值 {value} 不在范围 ({min_val}, {max_val}) 内"
            )