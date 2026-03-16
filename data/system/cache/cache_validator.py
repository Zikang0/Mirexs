"""
缓存验证器模块 - 缓存有效性验证
负责验证缓存数据的有效性和一致性
"""

import time
import hashlib
import json
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import threading
from dataclasses import dataclass

class ValidationResult(Enum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    UNKNOWN = "unknown"

@dataclass
class ValidationRule:
    name: str
    condition: Callable[[Any], bool]
    severity: str  # "low", "medium", "high"
    description: str

class CacheValidator:
    """缓存验证器"""
    
    def __init__(self):
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.consistency_checks: List[Callable] = []
        self.health_metrics: Dict[str, Any] = {}
        self.lock = threading.RLock()
        
        # 注册默认验证规则
        self._register_default_rules()
    
    def _register_default_rules(self):
        """注册默认验证规则"""
        # TTL检查规则
        self.add_validation_rule(
            "ttl_check",
            lambda data: data.get('expires_at', 0) > time.time() if data.get('expires_at') else True,
            "high",
            "检查缓存项是否过期"
        )
        
        # 数据完整性检查
        self.add_validation_rule(
            "integrity_check", 
            lambda data: self._check_data_integrity(data),
            "high",
            "检查数据完整性"
        )
        
        # 大小限制检查
        self.add_validation_rule(
            "size_check",
            lambda data: len(str(data.get('value', ''))) < 10 * 1024 * 1024,  # 10MB限制
            "medium",
            "检查数据大小是否合理"
        )
    
    def add_validation_rule(self, name: str, condition: Callable, severity: str, description: str):
        """添加验证规则"""
        with self.lock:
            self.validation_rules[name] = ValidationRule(
                name=name,
                condition=condition,
                severity=severity,
                description=description
            )
    
    def validate_cache_item(self, key: str, data: Any, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        验证单个缓存项
        
        Args:
            key: 缓存键
            data: 缓存数据
            context: 验证上下文
            
        Returns:
            验证结果
        """
        with self.lock:
            results = {
                "key": key,
                "overall_status": ValidationResult.VALID,
                "validation_time": time.time(),
                "rule_results": {},
                "errors": [],
                "warnings": []
            }
            
            # 应用所有验证规则
            for rule_name, rule in self.validation_rules.items():
                try:
                    is_valid = rule.condition(data)
                    results["rule_results"][rule_name] = {
                        "valid": is_valid,
                        "severity": rule.severity,
                        "description": rule.description
                    }
                    
                    if not is_valid:
                        if rule.severity == "high":
                            results["errors"].append(f"规则 '{rule_name}' 验证失败: {rule.description}")
                            results["overall_status"] = ValidationResult.INVALID
                        else:
                            results["warnings"].append(f"规则 '{rule_name}' 验证失败: {rule.description}")
                            if results["overall_status"] == ValidationResult.VALID:
                                results["overall_status"] = ValidationResult.STALE
                
                except Exception as e:
                    results["rule_results"][rule_name] = {
                        "valid": False,
                        "severity": rule.severity,
                        "description": rule.description,
                        "error": str(e)
                    }
                    results["errors"].append(f"规则 '{rule_name}' 执行错误: {str(e)}")
                    results["overall_status"] = ValidationResult.INVALID
            
            # 更新健康指标
            self._update_health_metrics(results)
            
            return results
    
    def validate_cache_batch(self, items: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """批量验证缓存项"""
        results = {}
        for key, data in items.items():
            results[key] = self.validate_cache_item(key, data)
        return results
    
    def add_consistency_check(self, check_function: Callable):
        """添加一致性检查"""
        with self.lock:
            self.consistency_checks.append(check_function)
    
    def perform_consistency_check(self, cache_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行一致性检查"""
        with self.lock:
            results = {
                "check_time": time.time(),
                "total_checks": len(self.consistency_checks),
                "passed_checks": 0,
                "failed_checks": 0,
                "check_details": []
            }
            
            for check_func in self.consistency_checks:
                try:
                    check_result = check_func(cache_data)
                    results["check_details"].append({
                        "check": check_func.__name__,
                        "passed": check_result.get("passed", False),
                        "message": check_result.get("message", ""),
                        "details": check_result.get("details", {})
                    })
                    
                    if check_result.get("passed", False):
                        results["passed_checks"] += 1
                    else:
                        results["failed_checks"] += 1
                
                except Exception as e:
                    results["check_details"].append({
                        "check": check_func.__name__,
                        "passed": False,
                        "message": f"检查执行失败: {str(e)}",
                        "error": str(e)
                    })
                    results["failed_checks"] += 1
            
            return results
    
    def _check_data_integrity(self, data: Any) -> bool:
        """检查数据完整性"""
        try:
            if isinstance(data, dict) and 'checksum' in data:
                # 如果有校验和，验证数据完整性
                stored_checksum = data['checksum']
                data_copy = data.copy()
                del data_copy['checksum']
                
                calculated_checksum = self._calculate_checksum(data_copy)
                return stored_checksum == calculated_checksum
            
            return True
        except Exception:
            return False
    
    def _calculate_checksum(self, data: Any) -> str:
        """计算数据校验和"""
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode('utf-8')).hexdigest()
    
    def _update_health_metrics(self, validation_result: Dict[str, Any]):
        """更新健康指标"""
        key = validation_result["key"]
        status = validation_result["overall_status"]
        
        if "validation_stats" not in self.health_metrics:
            self.health_metrics["validation_stats"] = {
                "total_validations": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "stale_count": 0,
                "error_count": 0
            }
        
        stats = self.health_metrics["validation_stats"]
        stats["total_validations"] += 1
        
        if status == ValidationResult.VALID:
            stats["valid_count"] += 1
        elif status == ValidationResult.INVALID:
            stats["invalid_count"] += 1
        elif status == ValidationResult.STALE:
            stats["stale_count"] += 1
        else:
            stats["error_count"] += 1
        
        # 更新最近验证结果
        if "recent_validations" not in self.health_metrics:
            self.health_metrics["recent_validations"] = []
        
        recent = self.health_metrics["recent_validations"]
        recent.append({
            "key": key,
            "status": status.value,
            "timestamp": validation_result["validation_time"]
        })
        
        # 保持最近100条记录
        if len(recent) > 100:
            self.health_metrics["recent_validations"] = recent[-100:]
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        with self.lock:
            stats = self.health_metrics.get("validation_stats", {})
            total = stats.get("total_validations", 0)
            
            if total > 0:
                valid_rate = (stats.get("valid_count", 0) / total) * 100
                invalid_rate = (stats.get("invalid_count", 0) / total) * 100
                stale_rate = (stats.get("stale_count", 0) / total) * 100
            else:
                valid_rate = invalid_rate = stale_rate = 0
            
            return {
                "validation_stats": stats,
                "health_metrics": {
                    "valid_rate_percent": round(valid_rate, 2),
                    "invalid_rate_percent": round(invalid_rate, 2),
                    "stale_rate_percent": round(stale_rate, 2),
                    "overall_health": self._calculate_overall_health(valid_rate, invalid_rate)
                },
                "rule_count": len(self.validation_rules),
                "consistency_check_count": len(self.consistency_checks),
                "recent_issues": self._get_recent_issues()
            }
    
    def _calculate_overall_health(self, valid_rate: float, invalid_rate: float) -> str:
        """计算整体健康状态"""
        if valid_rate >= 95:
            return "excellent"
        elif valid_rate >= 85:
            return "good"
        elif valid_rate >= 70:
            return "fair"
        else:
            return "poor"
    
    def _get_recent_issues(self) -> List[Dict[str, Any]]:
        """获取最近的问题"""
        recent = self.health_metrics.get("recent_validations", [])
        issues = []
        
        for validation in recent[-20:]:  # 最近20条
            if validation["status"] in ["invalid", "stale"]:
                issues.append(validation)
        
        return issues
    
    def create_data_with_integrity(self, data: Any) -> Dict[str, Any]:
        """创建带完整性保护的数据"""
        checksum = self._calculate_checksum(data)
        return {
            "data": data,
            "checksum": checksum,
            "created_at": time.time(),
            "version": "1.0"
        }
    
    def verify_data_integrity(self, protected_data: Dict[str, Any]) -> bool:
        """验证数据完整性"""
        try:
            if not isinstance(protected_data, dict):
                return False
            
            if 'checksum' not in protected_data or 'data' not in protected_data:
                return False
            
            stored_checksum = protected_data['checksum']
            data = protected_data['data']
            
            calculated_checksum = self._calculate_checksum(data)
            return stored_checksum == calculated_checksum
        
        except Exception:
            return False

# 预定义的验证规则
class StandardValidationRules:
    """标准验证规则集合"""
    
    @staticmethod
    def create_ttl_rule(max_age: int) -> ValidationRule:
        """创建TTL验证规则"""
        return ValidationRule(
            name=f"ttl_max_{max_age}s",
            condition=lambda data: (data.get('created_at', 0) + max_age) > time.time(),
            severity="high",
            description=f"检查数据是否在{max_age}秒内创建"
        )
    
    @staticmethod
    def create_size_rule(max_size_kb: int) -> ValidationRule:
        """创建大小验证规则"""
        return ValidationRule(
            name=f"size_max_{max_size_kb}kb",
            condition=lambda data: len(str(data.get('value', ''))) <= max_size_kb * 1024,
            severity="medium",
            description=f"检查数据大小是否超过{max_size_kb}KB"
        )
    
    @staticmethod
    def create_schema_rule(schema: Dict) -> ValidationRule:
        """创建模式验证规则"""
        def schema_check(data):
            if not isinstance(data, dict):
                return False
            
            for key, expected_type in schema.items():
                if key not in data:
                    return False
                if not isinstance(data[key], expected_type):
                    return False
            
            return True
        
        return ValidationRule(
            name="schema_validation",
            condition=schema_check,
            severity="high",
            description="检查数据是否符合预期模式"
        )

# 全局缓存验证器实例
cache_validator = CacheValidator()

# 添加一些标准规则
cache_validator.add_validation_rule(
    "default_ttl",
    StandardValidationRules.create_ttl_rule(3600).condition,
    "high",
    "默认TTL检查（1小时）"
)

