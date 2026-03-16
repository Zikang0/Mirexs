"""
请求验证器模块 - Mirexs API网关

提供API请求验证功能，包括：
1. 参数验证
2. 类型检查
3. 格式验证
4. 自定义规则
5. 错误消息
"""

import logging
import time
import json
import re
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ValidationRuleType(Enum):
    """验证规则类型枚举"""
    REQUIRED = "required"
    TYPE = "type"
    LENGTH = "length"
    RANGE = "range"
    PATTERN = "pattern"
    ENUM = "enum"
    CUSTOM = "custom"
    FORMAT = "format"
    DEPENDENCY = "dependency"

class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    URL = "url"
    IP = "ip"
    UUID = "uuid"

@dataclass
class ValidationRule:
    """验证规则"""
    field: str
    type: ValidationRuleType
    value: Any = None
    message: str = ""
    required: bool = True
    enabled: bool = True

@dataclass
class ValidationSchema:
    """验证模式"""
    id: str
    name: str
    rules: List[ValidationRule] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=time.time)

@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    code: str
    value: Any = None

class RequestValidator:
    """
    请求验证器
    
    负责API请求参数的验证。
    """
    
    def __init__(self):
        """初始化请求验证器"""
        self.schemas: Dict[str, ValidationSchema] = {}
        self.custom_validators: Dict[str, Callable] = {}
        
        # 注册内置验证器
        self._register_builtin_validators()
        
        # 统计
        self.stats = {
            "validations": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0
        }
        
        logger.info("RequestValidator initialized")
    
    def _register_builtin_validators(self):
        """注册内置验证器"""
        self.custom_validators["email"] = self._validate_email
        self.custom_validators["url"] = self._validate_url
        self.custom_validators["ip"] = self._validate_ip
        self.custom_validators["uuid"] = self._validate_uuid
        self.custom_validators["date"] = self._validate_date
        self.custom_validators["datetime"] = self._validate_datetime
    
    def _validate_email(self, value: Any) -> bool:
        """验证邮箱"""
        if not isinstance(value, str):
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, value) is not None
    
    def _validate_url(self, value: Any) -> bool:
        """验证URL"""
        if not isinstance(value, str):
            return False
        pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*$'
        return re.match(pattern, value) is not None
    
    def _validate_ip(self, value: Any) -> bool:
        """验证IP地址"""
        if not isinstance(value, str):
            return False
        # IPv4
        pattern_v4 = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        # IPv6简化验证
        pattern_v6 = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
        return re.match(pattern_v4, value) is not None or re.match(pattern_v6, value) is not None
    
    def _validate_uuid(self, value: Any) -> bool:
        """验证UUID"""
        if not isinstance(value, str):
            return False
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False
    
    def _validate_date(self, value: Any) -> bool:
        """验证日期"""
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d")
                return True
            except ValueError:
                return False
        return False
    
    def _validate_datetime(self, value: Any) -> bool:
        """验证日期时间"""
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        return False
    
    def create_schema(self, name: str, rules: List[Dict[str, Any]]) -> str:
        """
        创建验证模式
        
        Args:
            name: 模式名称
            rules: 规则列表
        
        Returns:
            模式ID
        """
        schema_id = str(uuid.uuid4())
        
        validation_rules = []
        for rule_data in rules:
            rule = ValidationRule(
                field=rule_data["field"],
                type=ValidationRuleType(rule_data["type"]),
                value=rule_data.get("value"),
                message=rule_data.get("message", ""),
                required=rule_data.get("required", True)
            )
            validation_rules.append(rule)
        
        schema = ValidationSchema(
            id=schema_id,
            name=name,
            rules=validation_rules
        )
        
        self.schemas[schema_id] = schema
        
        logger.info(f"Validation schema created: {name} ({schema_id})")
        
        return schema_id
    
    def validate(self, data: Dict[str, Any], schema_id: str) -> List[ValidationError]:
        """
        验证数据
        
        Args:
            data: 要验证的数据
            schema_id: 模式ID
        
        Returns:
            验证错误列表
        """
        self.stats["validations"] += 1
        
        if schema_id not in self.schemas:
            error = ValidationError(
                field="_schema",
                message=f"Schema not found: {schema_id}",
                code="schema_not_found"
            )
            self.stats["errors"] += 1
            return [error]
        
        schema = self.schemas[schema_id]
        errors = []
        
        # 检查必填字段
        for rule in schema.rules:
            if rule.type == ValidationRuleType.REQUIRED:
                if rule.field not in data:
                    errors.append(ValidationError(
                        field=rule.field,
                        message=rule.message or f"Field '{rule.field}' is required",
                        code="required",
                        value=None
                    ))
        
        # 验证字段
        for field_name, value in data.items():
            field_rules = [r for r in schema.rules if r.field == field_name]
            
            for rule in field_rules:
                if not rule.enabled:
                    continue
                
                error = self._apply_rule(rule, value)
                if error:
                    errors.append(error)
        
        if errors:
            self.stats["failed"] += 1
        else:
            self.stats["passed"] += 1
        
        return errors
    
    def _apply_rule(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """应用验证规则"""
        if rule.type == ValidationRuleType.TYPE:
            return self._validate_type(rule, value)
        elif rule.type == ValidationRuleType.LENGTH:
            return self._validate_length(rule, value)
        elif rule.type == ValidationRuleType.RANGE:
            return self._validate_range(rule, value)
        elif rule.type == ValidationRuleType.PATTERN:
            return self._validate_pattern(rule, value)
        elif rule.type == ValidationRuleType.ENUM:
            return self._validate_enum(rule, value)
        elif rule.type == ValidationRuleType.FORMAT:
            return self._validate_format(rule, value)
        elif rule.type == ValidationRuleType.CUSTOM:
            return self._validate_custom(rule, value)
        
        return None
    
    def _validate_type(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证类型"""
        expected_type = rule.value
        
        valid = False
        if expected_type == FieldType.STRING.value:
            valid = isinstance(value, str)
        elif expected_type == FieldType.INTEGER.value:
            valid = isinstance(value, int)
        elif expected_type == FieldType.FLOAT.value:
            valid = isinstance(value, (int, float))
        elif expected_type == FieldType.BOOLEAN.value:
            valid = isinstance(value, bool)
        elif expected_type == FieldType.ARRAY.value:
            valid = isinstance(value, list)
        elif expected_type == FieldType.OBJECT.value:
            valid = isinstance(value, dict)
        
        if not valid:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Expected type '{expected_type}'",
                code="type_mismatch",
                value=value
            )
        
        return None
    
    def _validate_length(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证长度"""
        if not isinstance(value, (str, list, dict)):
            return None
        
        length = len(value)
        min_len = rule.value.get("min") if isinstance(rule.value, dict) else None
        max_len = rule.value.get("max") if isinstance(rule.value, dict) else rule.value
        
        if min_len is not None and length < min_len:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Length must be at least {min_len}",
                code="length_too_short",
                value=value
            )
        
        if max_len is not None and length > max_len:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Length must be at most {max_len}",
                code="length_too_long",
                value=value
            )
        
        return None
    
    def _validate_range(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证范围"""
        if not isinstance(value, (int, float)):
            return None
        
        min_val = rule.value.get("min") if isinstance(rule.value, dict) else None
        max_val = rule.value.get("max") if isinstance(rule.value, dict) else rule.value
        
        if min_val is not None and value < min_val:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Value must be at least {min_val}",
                code="range_too_low",
                value=value
            )
        
        if max_val is not None and value > max_val:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Value must be at most {max_val}",
                code="range_too_high",
                value=value
            )
        
        return None
    
    def _validate_pattern(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证正则表达式"""
        if not isinstance(value, str):
            return None
        
        pattern = rule.value
        if not re.match(pattern, value):
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Value does not match pattern: {pattern}",
                code="pattern_mismatch",
                value=value
            )
        
        return None
    
    def _validate_enum(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证枚举值"""
        allowed_values = rule.value
        
        if value not in allowed_values:
            return ValidationError(
                field=rule.field,
                message=rule.message or f"Value must be one of: {allowed_values}",
                code="invalid_enum",
                value=value
            )
        
        return None
    
    def _validate_format(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证格式"""
        format_type = rule.value
        
        if format_type in self.custom_validators:
            validator = self.custom_validators[format_type]
            if not validator(value):
                return ValidationError(
                    field=rule.field,
                    message=rule.message or f"Invalid {format_type} format",
                    code="invalid_format",
                    value=value
                )
        
        return None
    
    def _validate_custom(self, rule: ValidationRule, value: Any) -> Optional[ValidationError]:
        """验证自定义规则"""
        if callable(rule.value):
            try:
                result = rule.value(value)
                if not result:
                    return ValidationError(
                        field=rule.field,
                        message=rule.message or "Custom validation failed",
                        code="custom_validation_failed",
                        value=value
                    )
            except Exception as e:
                return ValidationError(
                    field=rule.field,
                    message=str(e),
                    code="custom_validation_error",
                    value=value
                )
        
        return None
    
    def register_custom_validator(self, name: str, validator: Callable):
        """
        注册自定义验证器
        
        Args:
            name: 验证器名称
            validator: 验证函数
        """
        self.custom_validators[name] = validator
        logger.info(f"Custom validator registered: {name}")
    
    def get_schema(self, schema_id: str) -> Optional[ValidationSchema]:
        """获取验证模式"""
        return self.schemas.get(schema_id)
    
    def get_schemas(self) -> List[ValidationSchema]:
        """获取所有验证模式"""
        return list(self.schemas.values())
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取请求验证器状态
        
        Returns:
            状态字典
        """
        return {
            "schemas": {
                "total": len(self.schemas)
            },
            "custom_validators": len(self.custom_validators),
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭请求验证器"""
        logger.info("Shutting down RequestValidator...")
        
        self.schemas.clear()
        self.custom_validators.clear()
        
        logger.info("RequestValidator shutdown completed")

# 单例模式实现
_request_validator_instance: Optional[RequestValidator] = None

def get_request_validator() -> RequestValidator:
    """
    获取请求验证器单例
    
    Returns:
        请求验证器实例
    """
    global _request_validator_instance
    if _request_validator_instance is None:
        _request_validator_instance = RequestValidator()
    return _request_validator_instance

