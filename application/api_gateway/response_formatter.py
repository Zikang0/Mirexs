"""
响应格式化器模块 - Mirexs API网关

提供API响应格式化功能，包括：
1. 统一响应格式
2. 错误响应
3. 分页响应
4. 数据包装
5. 元数据添加
"""

import logging
import time
import json
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

class ResponseFormat(Enum):
    """响应格式枚举"""
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    HTML = "html"
    BINARY = "binary"

class ResponseStatus(Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    FAIL = "fail"
    WARNING = "warning"

@dataclass
class ResponseWrapper:
    """响应包装器"""
    status: ResponseStatus
    code: int
    message: str
    data: Any = None
    meta: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "status": self.status.value,
            "code": self.code,
            "message": self.message,
            "timestamp": self.timestamp
        }
        
        if self.data is not None:
            result["data"] = self.data
        
        if self.meta:
            result["meta"] = self.meta
        
        if self.errors:
            result["errors"] = self.errors
        
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

@dataclass
class PaginatedResponse:
    """分页响应"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "page_size": self.page_size,
                "pages": self.pages,
                "has_next": self.page < self.pages,
                "has_prev": self.page > 1
            }
        }

@dataclass
class FormatterConfig:
    """格式化器配置"""
    # 默认格式
    default_format: ResponseFormat = ResponseFormat.JSON
    
    # JSON配置
    json_indent: Optional[int] = 2
    json_ensure_ascii: bool = False
    
    # 时间格式
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    date_format: str = "%Y-%m-%d"
    
    # 字段映射
    success_code: int = 200
    error_code: int = 500
    validation_code: int = 422
    not_found_code: int = 404
    
    # 调试模式
    debug_mode: bool = False
    include_stacktrace: bool = False

class ResponseFormatter:
    """
    响应格式化器
    
    负责API响应的格式化。
    """
    
    def __init__(self, config: Optional[FormatterConfig] = None):
        """
        初始化响应格式化器
        
        Args:
            config: 格式化器配置
        """
        self.config = config or FormatterConfig()
        
        # 统计
        self.stats = {
            "responses_formatted": 0,
            "success_responses": 0,
            "error_responses": 0
        }
        
        logger.info("ResponseFormatter initialized")
    
    def success(self, data: Any = None, message: str = "Success",
               code: Optional[int] = None, meta: Optional[Dict] = None) -> ResponseWrapper:
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: HTTP状态码
            meta: 元数据
        
        Returns:
            响应包装器
        """
        self.stats["responses_formatted"] += 1
        self.stats["success_responses"] += 1
        
        return ResponseWrapper(
            status=ResponseStatus.SUCCESS,
            code=code or self.config.success_code,
            message=message,
            data=data,
            meta=meta or {}
        )
    
    def error(self, message: str = "Error", code: Optional[int] = None,
             errors: Optional[List[Dict]] = None) -> ResponseWrapper:
        """
        错误响应
        
        Args:
            message: 错误消息
            code: HTTP状态码
            errors: 错误详情列表
        
        Returns:
            响应包装器
        """
        self.stats["responses_formatted"] += 1
        self.stats["error_responses"] += 1
        
        return ResponseWrapper(
            status=ResponseStatus.ERROR,
            code=code or self.config.error_code,
            message=message,
            errors=errors or []
        )
    
    def fail(self, message: str = "Failed", code: Optional[int] = None,
            errors: Optional[List[Dict]] = None) -> ResponseWrapper:
        """
        失败响应（用于验证错误等）
        
        Args:
            message: 失败消息
            code: HTTP状态码
            errors: 错误详情列表
        
        Returns:
            响应包装器
        """
        return ResponseWrapper(
            status=ResponseStatus.FAIL,
            code=code or self.config.validation_code,
            message=message,
            errors=errors or []
        )
    
    def warning(self, message: str = "Warning", data: Any = None,
               code: Optional[int] = None) -> ResponseWrapper:
        """
        警告响应
        
        Args:
            message: 警告消息
            data: 响应数据
            code: HTTP状态码
        
        Returns:
            响应包装器
        """
        return ResponseWrapper(
            status=ResponseStatus.WARNING,
            code=code or self.config.success_code,
            message=message,
            data=data
        )
    
    def paginated(self, items: List[Any], total: int, page: int,
                 page_size: int, message: str = "Success") -> ResponseWrapper:
        """
        分页响应
        
        Args:
            items: 数据项列表
            total: 总数
            page: 当前页码
            page_size: 每页大小
            message: 响应消息
        
        Returns:
            响应包装器
        """
        pages = (total + page_size - 1) // page_size
        
        paginated = PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
        
        return self.success(
            data=paginated.to_dict(),
            message=message,
            meta={
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "pages": pages
                }
            }
        )
    
    def created(self, data: Any = None, message: str = "Created") -> ResponseWrapper:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
        
        Returns:
            响应包装器
        """
        return self.success(data=data, message=message, code=201)
    
    def no_content(self) -> ResponseWrapper:
        """
        无内容响应
        
        Returns:
            响应包装器
        """
        return self.success(data=None, message="No Content", code=204)
    
    def not_found(self, message: str = "Resource not found") -> ResponseWrapper:
        """
        未找到响应
        
        Args:
            message: 错误消息
        
        Returns:
            响应包装器
        """
        return self.error(message=message, code=self.config.not_found_code)
    
    def validation_error(self, errors: List[Dict[str, Any]]) -> ResponseWrapper:
        """
        验证错误响应
        
        Args:
            errors: 验证错误列表
        
        Returns:
            响应包装器
        """
        formatted_errors = []
        for error in errors:
            formatted_errors.append({
                "field": error.get("field"),
                "message": error.get("message"),
                "code": error.get("code")
            })
        
        return self.fail(
            message="Validation failed",
            errors=formatted_errors
        )
    
    def format_validation_errors(self, errors: List[Any]) -> List[Dict[str, Any]]:
        """
        格式化验证错误
        
        Args:
            errors: 原始错误列表
        
        Returns:
            格式化后的错误列表
        """
        formatted = []
        
        for error in errors:
            if hasattr(error, '__dict__'):
                formatted.append({
                    "field": getattr(error, 'field', None),
                    "message": getattr(error, 'message', str(error)),
                    "code": getattr(error, 'code', 'validation_error')
                })
            elif isinstance(error, dict):
                formatted.append({
                    "field": error.get("field"),
                    "message": error.get("message", str(error)),
                    "code": error.get("code", "validation_error")
                })
            else:
                formatted.append({
                    "message": str(error),
                    "code": "validation_error"
                })
        
        return formatted
    
    def with_meta(self, response: ResponseWrapper, meta: Dict[str, Any]) -> ResponseWrapper:
        """
        添加元数据
        
        Args:
            response: 响应包装器
            meta: 元数据
        
        Returns:
            更新后的响应包装器
        """
        response.meta.update(meta)
        return response
    
    def format(self, response: ResponseWrapper, format_type: Optional[ResponseFormat] = None) -> Any:
        """
        格式化响应
        
        Args:
            response: 响应包装器
            format_type: 格式类型
        
        Returns:
            格式化后的响应
        """
        fmt = format_type or self.config.default_format
        
        if fmt == ResponseFormat.JSON:
            return self._format_json(response)
        elif fmt == ResponseFormat.XML:
            return self._format_xml(response)
        elif fmt == ResponseFormat.TEXT:
            return self._format_text(response)
        elif fmt == ResponseFormat.HTML:
            return self._format_html(response)
        else:
            return response.to_dict()
    
    def _format_json(self, response: ResponseWrapper) -> str:
        """格式化为JSON"""
        data = response.to_dict()
        
        # 处理日期时间
        self._process_datetime(data)
        
        return json.dumps(
            data,
            indent=self.config.json_indent,
            ensure_ascii=self.config.json_ensure_ascii,
            default=str
        )
    
    def _format_xml(self, response: ResponseWrapper) -> str:
        """格式化为XML"""
        # 简化XML生成
        data = response.to_dict()
        
        def dict_to_xml(d: Dict, root: str = "response") -> str:
            xml = [f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"]
            xml.append(f"<{root}>")
            
            for key, value in d.items():
                if isinstance(value, dict):
                    xml.append(f"<{key}>{dict_to_xml(value, key)}</{key}>")
                elif isinstance(value, list):
                    xml.append(f"<{key}>")
                    for item in value:
                        if isinstance(item, dict):
                            xml.append(f"<item>{dict_to_xml(item, 'item')}</item>")
                        else:
                            xml.append(f"<item>{item}</item>")
                    xml.append(f"</{key}>")
                else:
                    xml.append(f"<{key}>{value}</{key}>")
            
            xml.append(f"</{root}>")
            return "\n".join(xml)
        
        return dict_to_xml(data)
    
    def _format_text(self, response: ResponseWrapper) -> str:
        """格式化为纯文本"""
        data = response.to_dict()
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _format_html(self, response: ResponseWrapper) -> str:
        """格式化为HTML"""
        data = response.to_dict()
        
        html = ["<!DOCTYPE html>", "<html>", "<head>", "<title>API Response</title>", "</head>", "<body>", "<pre>"]
        html.append(json.dumps(data, indent=2, ensure_ascii=False))
        html.append("</pre>", "</body>", "</html>")
        
        return "\n".join(html)
    
    def _process_datetime(self, data: Any):
        """处理日期时间字段"""
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if isinstance(value, datetime):
                    data[key] = value.strftime(self.config.datetime_format)
                elif isinstance(value, (dict, list)):
                    self._process_datetime(value)
        elif isinstance(data, list):
            for item in data:
                self._process_datetime(item)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取响应格式化器状态
        
        Returns:
            状态字典
        """
        return {
            "default_format": self.config.default_format.value,
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭响应格式化器"""
        logger.info("Shutting down ResponseFormatter...")
        logger.info("ResponseFormatter shutdown completed")

# 单例模式实现
_response_formatter_instance: Optional[ResponseFormatter] = None

def get_response_formatter(config: Optional[FormatterConfig] = None) -> ResponseFormatter:
    """
    获取响应格式化器单例
    
    Args:
        config: 格式化器配置
    
    Returns:
        响应格式化器实例
    """
    global _response_formatter_instance
    if _response_formatter_instance is None:
        _response_formatter_instance = ResponseFormatter(config)
    return _response_formatter_instance

