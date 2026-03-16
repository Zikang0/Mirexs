"""
数据验证器：数据格式和完整性验证
负责数据格式验证、完整性检查、业务规则验证等数据质量保证任务
"""

import asyncio
import re
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import pandas as pd
import numpy as np

class ValidationRule(Enum):
    """验证规则枚举"""
    REQUIRED = "required"              # 必需字段
    DATA_TYPE = "data_type"           # 数据类型
    VALUE_RANGE = "value_range"       # 值范围
    PATTERN = "pattern"               # 正则表达式模式
    UNIQUE = "unique"                 # 唯一性
    CUSTOM = "custom"                 # 自定义规则
    REFERENCE = "reference"           # 引用完整性

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_count: int
    failed_count: int
    validation_time: float

@dataclass
class FieldValidation:
    """字段验证配置"""
    field: str
    rule_type: ValidationRule
    condition: Any
    error_message: str = None
    is_critical: bool = True

@dataclass
class SchemaDefinition:
    """模式定义"""
    schema_id: str
    fields: Dict[str, Dict[str, Any]]  # 字段名 -> 字段定义
    validation_rules: List[FieldValidation]

class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        self.schemas: Dict[str, SchemaDefinition] = {}
        self.custom_validators: Dict[str, Callable] = {}
        self.validation_history: List[ValidationResult] = []
        self.initialized = False
        
    async def initialize(self):
        """初始化数据验证器"""
        if self.initialized:
            return
            
        logging.info("初始化数据验证器...")
        
        # 注册内置验证器
        await self._register_builtin_validators()
        
        self.initialized = True
        logging.info("数据验证器初始化完成")
    
    async def _register_builtin_validators(self):
        """注册内置验证器"""
        self.register_custom_validator("email", self._validate_email)
        self.register_custom_validator("phone", self._validate_phone)
        self.register_custom_validator("url", self._validate_url)
        self.register_custom_validator("date", self._validate_date)
        self.register_custom_validator("credit_card", self._validate_credit_card)
    
    def register_schema(self, schema: SchemaDefinition) -> bool:
        """注册数据模式"""
        if schema.schema_id in self.schemas:
            logging.warning(f"数据模式已存在: {schema.schema_id}")
            return False
        
        self.schemas[schema.schema_id] = schema
        logging.info(f"数据模式注册成功: {schema.schema_id}")
        return True
    
    def register_custom_validator(self, name: str, validator_func: Callable):
        """注册自定义验证器"""
        self.custom_validators[name] = validator_func
        logging.debug(f"自定义验证器注册: {name}")
    
    async def validate_data(self, data: List[Dict[str, Any]], schema_id: str = None,
                          validation_rules: List[FieldValidation] = None) -> ValidationResult:
        """验证数据"""
        start_time = datetime.now()
        
        try:
            if schema_id and schema_id in self.schemas:
                schema = self.schemas[schema_id]
                rules = schema.validation_rules
            elif validation_rules:
                rules = validation_rules
            else:
                raise ValueError("必须提供schema_id或validation_rules")
            
            errors = []
            warnings = []
            validated_count = 0
            failed_count = 0
            
            for record in data:
                record_errors = await self._validate_record(record, rules)
                
                if record_errors:
                    errors.extend(record_errors)
                    failed_count += 1
                else:
                    validated_count += 1
            
            validation_time = (datetime.now() - start_time).total_seconds()
            
            result = ValidationResult(
                is_valid=(failed_count == 0),
                errors=errors,
                warnings=warnings,
                validated_count=validated_count,
                failed_count=failed_count,
                validation_time=validation_time
            )
            
            self.validation_history.append(result)
            logging.info(f"数据验证完成: {validated_count}/{len(data)} 条记录通过验证")
            
            return result
            
        except Exception as e:
            validation_time = (datetime.now() - start_time).total_seconds()
            logging.error(f"数据验证失败: {e}")
            
            return ValidationResult(
                is_valid=False,
                errors=[str(e)],
                warnings=[],
                validated_count=0,
                failed_count=len(data),
                validation_time=validation_time
            )
    
    async def validate_record(self, record: Dict[str, Any], validation_rules: List[FieldValidation]) -> List[str]:
        """验证单条记录"""
        return await self._validate_record(record, validation_rules)
    
    async def _validate_record(self, record: Dict[str, Any], rules: List[FieldValidation]) -> List[str]:
        """验证单条记录（内部实现）"""
        errors = []
        
        for rule in rules:
            field = rule.field
            value = record.get(field)
            
            try:
                if rule.rule_type == ValidationRule.REQUIRED:
                    if not self._validate_required(value):
                        errors.append(self._format_error(rule, field, value))
                
                elif rule.rule_type == ValidationRule.DATA_TYPE:
                    expected_type = rule.condition
                    if not self._validate_data_type(value, expected_type):
                        errors.append(self._format_error(rule, field, value))
                
                elif rule.rule_type == ValidationRule.VALUE_RANGE:
                    if not self._validate_value_range(value, rule.condition):
                        errors.append(self._format_error(rule, field, value))
                
                elif rule.rule_type == ValidationRule.PATTERN:
                    if not self._validate_pattern(value, rule.condition):
                        errors.append(self._format_error(rule, field, value))
                
                elif rule.rule_type == ValidationRule.UNIQUE:
                    # 唯一性验证需要在数据集级别进行，这里跳过
                    pass
                
                elif rule.rule_type == ValidationRule.CUSTOM:
                    validator_name = rule.condition
                    if validator_name in self.custom_validators:
                        if not self.custom_validators[validator_name](value):
                            errors.append(self._format_error(rule, field, value))
                    else:
                        errors.append(f"未知的自定义验证器: {validator_name}")
                
                elif rule.rule_type == ValidationRule.REFERENCE:
                    # 引用完整性验证需要外部数据，这里跳过
                    pass
            
            except Exception as e:
                errors.append(f"验证规则执行错误 {field}: {e}")
        
        return errors
    
    def _validate_required(self, value: Any) -> bool:
        """验证必需字段"""
        if value is None:
            return False
        
        if isinstance(value, str) and value.strip() == "":
            return False
        
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        
        return True
    
    def _validate_data_type(self, value: Any, expected_type: str) -> bool:
        """验证数据类型"""
        if value is None:
            return True  # 空值由REQUIRED规则处理
        
        type_map = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "date": datetime,
            "array": list,
            "object": dict
        }
        
        if expected_type not in type_map:
            return True  # 未知类型，跳过验证
        
        expected_class = type_map[expected_type]
        
        # 特殊处理数值类型
        if expected_type == "integer":
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        elif expected_type == "float":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        elif expected_type == "date":
            try:
                pd.to_datetime(value)
                return True
            except (ValueError, TypeError):
                return False
        else:
            return isinstance(value, expected_class)
    
    def _validate_value_range(self, value: Any, condition: Dict[str, Any]) -> bool:
        """验证值范围"""
        if value is None:
            return True
        
        if isinstance(value, (int, float)):
            min_val = condition.get("min")
            max_val = condition.get("max")
            
            if min_val is not None and value < min_val:
                return False
            
            if max_val is not None and value > max_val:
                return False
            
            return True
        
        elif isinstance(value, str):
            min_len = condition.get("min_length")
            max_len = condition.get("max_length")
            
            if min_len is not None and len(value) < min_len:
                return False
            
            if max_len is not None and len(value) > max_len:
                return False
            
            return True
        
        return True
    
    def _validate_pattern(self, value: Any, pattern: str) -> bool:
        """验证正则表达式模式"""
        if value is None or not isinstance(value, str):
            return True
        
        try:
            return bool(re.match(pattern, value))
        except re.error:
            return False
    
    def _format_error(self, rule: FieldValidation, field: str, value: Any) -> str:
        """格式化错误信息"""
        if rule.error_message:
            return rule.error_message
        
        value_str = str(value) if value is not None else "null"
        
        error_templates = {
            ValidationRule.REQUIRED: f"字段 '{field}' 是必需的，但值为: {value_str}",
            ValidationRule.DATA_TYPE: f"字段 '{field}' 的数据类型不正确，期望: {rule.condition}, 实际: {value_str}",
            ValidationRule.VALUE_RANGE: f"字段 '{field}' 的值不在允许范围内: {value_str}",
            ValidationRule.PATTERN: f"字段 '{field}' 的值不符合模式要求: {value_str}",
            ValidationRule.CUSTOM: f"字段 '{field}' 未通过自定义验证: {rule.condition}"
        }
        
        return error_templates.get(rule.rule_type, f"字段 '{field}' 验证失败: {value_str}")
    
    # 内置自定义验证器
    def _validate_email(self, value: Any) -> bool:
        """验证电子邮件地址"""
        if not isinstance(value, str):
            return False
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))
    
    def _validate_phone(self, value: Any) -> bool:
        """验证电话号码"""
        if not isinstance(value, str):
            return False
        
        # 简单的电话号码验证（可根据需要调整）
        phone_pattern = r'^[\+]?[0-9\s\-\(\)]{10,}$'
        return bool(re.match(phone_pattern, value.replace(' ', '')))
    
    def _validate_url(self, value: Any) -> bool:
        """验证URL"""
        if not isinstance(value, str):
            return False
        
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return bool(re.match(url_pattern, value))
    
    def _validate_date(self, value: Any) -> bool:
        """验证日期"""
        if value is None:
            return True
        
        try:
            pd.to_datetime(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _validate_credit_card(self, value: Any) -> bool:
        """验证信用卡号（Luhn算法）"""
        if not isinstance(value, str):
            return False
        
        # 移除空格和连字符
        clean_value = value.replace(' ', '').replace('-', '')
        
        # 检查是否全为数字
        if not clean_value.isdigit():
            return False
        
        # Luhn算法验证
        def luhn_check(card_number):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_number)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10 == 0
        
        return luhn_check(clean_value)
    
    async def validate_dataset_quality(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """验证数据集质量"""
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        quality_report = {}
        
        # 计算完整性
        completeness = df.notnull().sum() / len(df) * 100
        quality_report["completeness"] = completeness.to_dict()
        
        # 计算唯一性
        uniqueness = df.nunique() / len(df) * 100
        quality_report["uniqueness"] = uniqueness.to_dict()
        
        # 检测数据类型一致性
        type_consistency = {}
        for column in df.columns:
            # 简单的一致性检查：检查第一行的类型是否与后续行一致
            if len(df) > 1:
                first_type = type(df[column].iloc[0])
                consistent = all(type(x) == first_type for x in df[column].iloc[1:] if pd.notnull(x))
                type_consistency[column] = consistent
            else:
                type_consistency[column] = True
        
        quality_report["type_consistency"] = type_consistency
        
        # 计算总体质量分数
        avg_completeness = completeness.mean()
        avg_uniqueness = uniqueness.mean()
        consistency_score = sum(type_consistency.values()) / len(type_consistency) * 100
        
        quality_score = (avg_completeness * 0.5 + avg_uniqueness * 0.3 + consistency_score * 0.2) / 100
        
        quality_report["quality_score"] = quality_score
        quality_report["summary"] = {
            "total_records": len(df),
            "total_columns": len(df.columns),
            "completeness_score": avg_completeness,
            "uniqueness_score": avg_uniqueness,
            "consistency_score": consistency_score
        }
        
        return quality_report
    
    async def generate_validation_schema(self, data: List[Dict[str, Any]], schema_id: str) -> SchemaDefinition:
        """从数据生成验证模式"""
        if not data:
            raise ValueError("数据为空，无法生成模式")
        
        df = pd.DataFrame(data)
        fields = {}
        validation_rules = []
        
        for column in df.columns:
            series = df[column]
            
            # 分析字段特性
            field_def = {
                "data_type": self._infer_data_type(series),
                "nullable": series.isnull().any(),
                "unique": series.nunique() == len(series),
                "sample_values": series.dropna().head(5).tolist()
            }
            
            # 为数值字段添加范围信息
            if pd.api.types.is_numeric_dtype(series):
                field_def.update({
                    "min_value": float(series.min()),
                    "max_value": float(series.max()),
                    "mean_value": float(series.mean())
                })
            
            fields[column] = field_def
            
            # 生成验证规则
            if not field_def["nullable"]:
                validation_rules.append(FieldValidation(
                    field=column,
                    rule_type=ValidationRule.REQUIRED,
                    condition=True
                ))
            
            validation_rules.append(FieldValidation(
                field=column,
                rule_type=ValidationRule.DATA_TYPE,
                condition=field_def["data_type"]
            ))
        
        schema = SchemaDefinition(
            schema_id=schema_id,
            fields=fields,
            validation_rules=validation_rules
        )
        
        await self.register_schema(schema)
        return schema
    
    def _infer_data_type(self, series: pd.Series) -> str:
        """推断数据类型"""
        if pd.api.types.is_integer_dtype(series):
            return "integer"
        elif pd.api.types.is_float_dtype(series):
            return "float"
        elif pd.api.types.is_bool_dtype(series):
            return "boolean"
        elif pd.api.types.is_datetime64_any_dtype(series):
            return "date"
        elif pd.api.types.is_object_dtype(series):
            # 检查是否为字符串
            sample = series.dropna().head(10)
            if all(isinstance(x, str) for x in sample):
                return "string"
            else:
                return "object"
        else:
            return "unknown"
    
    def get_validator_stats(self) -> Dict[str, Any]:
        """获取验证器统计"""
        total_validations = len(self.validation_history)
        successful_validations = sum(1 for result in self.validation_history if result.is_valid)
        total_records = sum(result.validated_count + result.failed_count for result in self.validation_history)
        
        error_distribution = {}
        for result in self.validation_history:
            for error in result.errors:
                # 提取错误类型（简化实现）
                error_type = error.split(':')[0] if ':' in error else "unknown"
                error_distribution[error_type] = error_distribution.get(error_type, 0) + 1
        
        return {
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "success_rate": (successful_validations / total_validations * 100) if total_validations > 0 else 0,
            "total_records_validated": total_records,
            "schemas_registered": len(self.schemas),
            "custom_validators": len(self.custom_validators),
            "error_distribution": error_distribution
        }

# 全局数据验证器实例
data_validator = DataValidator()
