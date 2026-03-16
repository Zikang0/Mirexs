"""
工具函数模块

提供插件开发所需的各种工具函数，包括：
- 数据处理函数
- 验证函数
- 格式化函数
- 转换函数

Author: AI Assistant
Date: 2025-11-05
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path


class UtilityFunctions:
    """工具函数类"""
    
    def __init__(self):
        """初始化工具函数"""
        self.logger = logging.getLogger(__name__)
    
    def validate_email(self, email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            bool: 格式正确返回True，否则返回False
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_url(self, url: str) -> bool:
        """
        验证URL格式
        
        Args:
            url: URL地址
            
        Returns:
            bool: 格式正确返回True，否则返回False
        """
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    def format_datetime(self, dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        格式化日期时间
        
        Args:
            dt: 日期时间对象
            format_str: 格式字符串
            
        Returns:
            str: 格式化后的字符串
        """
        return dt.strftime(format_str)
    
    def parse_datetime(self, date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """
        解析日期时间字符串
        
        Args:
            date_str: 日期时间字符串
            format_str: 格式字符串
            
        Returns:
            Optional[datetime]: 解析后的日期时间对象，失败返回None
        """
        try:
            return datetime.strptime(date_str, format_str)
        except ValueError:
            return None
    
    def calculate_hash(self, data: str, algorithm: str = "md5") -> str:
        """
        计算数据哈希值
        
        Args:
            data: 数据字符串
            algorithm: 哈希算法
            
        Returns:
            str: 哈希值
        """
        try:
            if algorithm == "md5":
                return hashlib.md5(data.encode()).hexdigest()
            elif algorithm == "sha256":
                return hashlib.sha256(data.encode()).hexdigest()
            else:
                raise ValueError(f"不支持的哈希算法: {algorithm}")
        except Exception as e:
            self.logger.error(f"哈希计算失败: {str(e)}")
            return ""
    
    def json_dumps(self, obj: Any, indent: int = 2) -> str:
        """
        序列化JSON数据
        
        Args:
            obj: 要序列化的对象
            indent: 缩进空格数
            
        Returns:
            str: JSON字符串
        """
        try:
            return json.dumps(obj, indent=indent, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"JSON序列化失败: {str(e)}")
            return ""
    
    def json_loads(self, json_str: str) -> Optional[Any]:
        """
        反序列化JSON数据
        
        Args:
            json_str: JSON字符串
            
        Returns:
            Optional[Any]: 反序列化后的对象，失败返回None
        """
        try:
            return json.loads(json_str)
        except Exception as e:
            self.logger.error(f"JSON反序列化失败: {str(e)}")
            return None
    
    def truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """
        截断文本
        
        Args:
            text: 原文本
            max_length: 最大长度
            suffix: 后缀
            
        Returns:
            str: 截断后的文本
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    def slugify(self, text: str) -> str:
        """
        生成URL友好的slug
        
        Args:
            text: 原文本
            
        Returns:
            str: slug字符串
        """
        import re
        # 转换为小写并替换空格为连字符
        text = text.lower().strip()
        # 移除特殊字符
        text = re.sub(r'[^\w\s-]', '', text)
        # 替换空格为连字符
        text = re.sub(r'[-\s]+', '-', text)
        return text
    
    def generate_id(self, prefix: str = "", length: int = 8) -> str:
        """
        生成唯一ID
        
        Args:
            prefix: ID前缀
            length: ID长度
            
        Returns:
            str: 生成的ID
        """
        import secrets
        import string
        
        characters = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(characters) for _ in range(length))
        return f"{prefix}_{random_part}" if prefix else random_part
    
    def deep_merge_dict(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并字典
        
        Args:
            dict1: 第一个字典
            dict2: 第二个字典
            
        Returns:
            Dict[str, Any]: 合并后的字典
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge_dict(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def chunk_list(self, items: List[Any], chunk_size: int) -> List[List[Any]]:
        """
        将列表分块
        
        Args:
            items: 原列表
            chunk_size: 块大小
            
        Returns:
            List[List[Any]]: 分块后的列表
        """
        return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    def retry_on_failure(self, func: callable, max_retries: int = 3, delay: float = 1.0):
        """
        失败重试装饰器
        
        Args:
            func: 要重试的函数
            max_retries: 最大重试次数
            delay: 重试间隔
            
        Returns:
            Any: 函数执行结果
        """
        import time
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries:
                    raise e
                self.logger.warning(f"函数执行失败，{delay}秒后重试: {str(e)}")
                time.sleep(delay)