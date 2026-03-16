"""
匿名化引擎模块 - 数据匿名化处理
提供多种数据匿名化技术，包括泛化、抑制、置换、噪声添加等
"""

import logging
import time
import hashlib
import random
import re
from typing import Dict, Any, Optional, List, Union, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
import json

from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class AnonymizationTechnique(Enum):
    """匿名化技术枚举"""
    SUPPRESSION = "suppression"  # 抑制（删除）
    GENERALIZATION = "generalization"  # 泛化（如年龄->年龄段）
    PERTURBATION = "perturbation"  # 扰动（添加噪声）
    PERMUTATION = "permutation"  # 置换（打乱）
    PSEUDONYMIZATION = "pseudonymization"  # 假名化
    MASKING = "masking"  # 掩码
    TOKENIZATION = "tokenization"  # 令牌化
    HASHING = "hashing"  # 哈希
    ENCRYPTION = "encryption"  # 加密
    AGGREGATION = "aggregation"  # 聚合
    BINNING = "binning"  # 分箱
    ROUNDING = "rounding"  # 四舍五入


class DataType(Enum):
    """数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    NAME = "name"
    ID = "id"
    LOCATION = "location"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


@dataclass
class AnonymizationRule:
    """匿名化规则"""
    rule_id: str
    field_path: str  # 字段路径（如 "user.profile.age"）
    data_type: DataType
    technique: AnonymizationTechnique
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class AnonymizationResult:
    """匿名化结果"""
    anonymized_data: Any
    rules_applied: List[str]
    original_data_hash: str
    anonymized_data_hash: str
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnonymizationEngine:
    """
    匿名化引擎 - 对敏感数据进行匿名化处理
    支持多种匿名化技术，可配置规则和策略
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化匿名化引擎
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储匿名化规则
        self.rules: Dict[str, AnonymizationRule] = {}
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        
        # 假名映射表（用于可逆假名化）
        self.pseudonym_map: Dict[str, str] = {}
        
        # 令牌映射表
        self.token_map: Dict[str, str] = {}
        
        # 初始化默认规则
        self._init_default_rules()
        
        logger.info(f"匿名化引擎初始化完成，已加载 {len(self.rules)} 条默认规则")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "default_suppression_value": "[REDACTED]",
            "default_masking_char": "*",
            "hash_algorithm": "sha256",
            "max_bin_count": 10,
            "pseudonym_salt": "mirexs_anon_salt",
            "enable_audit": True,
            "preserve_format": True,  # 匿名化时保持格式
            "default_rules": {
                "email": {
                    "technique": "masking",
                    "parameters": {"mask_pattern": "(.{2})[^@]*(@.*)", "replacement": "\\1***\\2"}
                },
                "phone": {
                    "technique": "masking",
                    "parameters": {"mask_pattern": "(\\d{3})\\d{4}(\\d{4})", "replacement": "\\1****\\2"}
                },
                "id_card": {
                    "technique": "masking",
                    "parameters": {"mask_pattern": "(\\d{6})\\d{8}(\\d{4})", "replacement": "\\1********\\2"}
                },
                "name": {
                    "technique": "pseudonymization"
                },
                "address": {
                    "technique": "generalization",
                    "parameters": {"level": "city"}  # 只保留城市级别
                },
                "age": {
                    "technique": "binning",
                    "parameters": {"bins": [0, 18, 30, 45, 60, 100], "labels": ["0-18", "19-30", "31-45", "46-60", "60+"]}
                },
                "salary": {
                    "technique": "rounding",
                    "parameters": {"precision": -3}  # 千位取整
                }
            }
        }
    
    def _init_default_rules(self):
        """初始化默认匿名化规则"""
        default_rules = self.config.get("default_rules", {})
        
        for field_path, rule_config in default_rules.items():
            technique = AnonymizationTechnique(rule_config.get("technique", "suppression"))
            
            rule = AnonymizationRule(
                rule_id=f"default_{field_path}",
                field_path=field_path,
                data_type=self._infer_data_type(field_path),
                technique=technique,
                parameters=rule_config.get("parameters", {}),
                description=f"Default anonymization rule for {field_path}"
            )
            
            self.rules[rule.rule_id] = rule
        
        logger.info(f"初始化了 {len(default_rules)} 条默认匿名化规则")
    
    def add_rule(self, rule: AnonymizationRule) -> Tuple[bool, str]:
        """
        添加匿名化规则
        
        Args:
            rule: 匿名化规则
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if rule.rule_id in self.rules:
                return False, f"规则ID已存在: {rule.rule_id}"
            
            self.rules[rule.rule_id] = rule
            logger.info(f"添加匿名化规则: {rule.rule_id}")
            return True, "规则添加成功"
        except Exception as e:
            logger.error(f"添加规则失败: {str(e)}")
            return False, f"添加规则失败: {str(e)}"
    
    def remove_rule(self, rule_id: str) -> Tuple[bool, str]:
        """
        移除匿名化规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            (成功标志, 消息)
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"移除匿名化规则: {rule_id}")
            return True, "规则移除成功"
        return False, f"规则不存在: {rule_id}"
    
    def anonymize(
        self,
        data: Any,
        rules: Optional[List[Union[str, AnonymizationRule]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AnonymizationResult:
        """
        匿名化数据
        
        Args:
            data: 待匿名化数据
            rules: 要应用的规则（规则ID列表或规则对象列表）
            context: 上下文信息
        
        Returns:
            匿名化结果
        """
        start_time = time.time()
        
        try:
            # 计算原始数据哈希
            original_hash = self._compute_hash(data)
            
            # 确定要应用的规则
            rules_to_apply = self._resolve_rules(rules)
            
            # 深拷贝数据以避免修改原始数据
            if isinstance(data, dict):
                anonymized = self._anonymize_dict(data, rules_to_apply, context or {})
            elif isinstance(data, list):
                anonymized = self._anonymize_list(data, rules_to_apply, context or {})
            else:
                # 单值数据，使用第一条匹配的规则
                rule = rules_to_apply[0] if rules_to_apply else None
                anonymized = self._apply_rule_to_value(data, rule, context or {})
            
            # 计算匿名化后数据哈希
            anonymized_hash = self._compute_hash(anonymized)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = AnonymizationResult(
                anonymized_data=anonymized,
                rules_applied=[r.rule_id for r in rules_to_apply],
                original_data_hash=original_hash,
                anonymized_data_hash=anonymized_hash,
                processing_time_ms=processing_time,
                metadata={"context": context}
            )
            
            # 记录审计日志
            if self.config["enable_audit"]:
                self.audit_logger.log_event(
                    event_type="DATA_ANONYMIZATION",
                    user_id=context.get("user_id") if context else None,
                    details={
                        "rules_applied": len(rules_to_apply),
                        "original_hash": original_hash[:8],
                        "anonymized_hash": anonymized_hash[:8],
                        "processing_time_ms": processing_time
                    },
                    severity="INFO"
                )
            
            logger.debug(f"数据匿名化完成，应用了 {len(rules_to_apply)} 条规则")
            return result
            
        except Exception as e:
            logger.error(f"匿名化失败: {str(e)}")
            return AnonymizationResult(
                anonymized_data=data,
                rules_applied=[],
                original_data_hash=self._compute_hash(data),
                anonymized_data_hash=self._compute_hash(data),
                processing_time_ms=(time.time() - start_time) * 1000,
                metadata={"error": str(e)}
            )
    
    def _resolve_rules(
        self,
        rules: Optional[List[Union[str, AnonymizationRule]]]
    ) -> List[AnonymizationRule]:
        """解析规则列表"""
        resolved = []
        
        if not rules:
            # 使用所有规则
            resolved = list(self.rules.values())
        else:
            for rule in rules:
                if isinstance(rule, str):
                    if rule in self.rules:
                        resolved.append(self.rules[rule])
                elif isinstance(rule, AnonymizationRule):
                    resolved.append(rule)
        
        return resolved
    
    def _anonymize_dict(
        self,
        data: Dict,
        rules: List[AnonymizationRule],
        context: Dict[str, Any]
    ) -> Dict:
        """匿名化字典数据"""
        result = {}
        
        for key, value in data.items():
            # 查找匹配当前路径的规则
            field_path = context.get("current_path", key)
            matching_rules = [r for r in rules if self._path_matches(field_path, r.field_path)]
            
            if matching_rules:
                # 使用第一条匹配的规则
                rule = matching_rules[0]
                result[key] = self._apply_rule_to_value(value, rule, {
                    **context,
                    "current_path": field_path
                })
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self._anonymize_dict(value, rules, {
                    **context,
                    "current_path": f"{field_path}.{key}" if field_path else key
                })
            elif isinstance(value, list):
                # 递归处理列表
                result[key] = self._anonymize_list(value, rules, {
                    **context,
                    "current_path": field_path
                })
            else:
                # 没有匹配规则，保留原值
                result[key] = value
        
        return result
    
    def _anonymize_list(
        self,
        data: List,
        rules: List[AnonymizationRule],
        context: Dict[str, Any]
    ) -> List:
        """匿名化列表数据"""
        result = []
        
        for i, item in enumerate(data):
            if isinstance(item, dict):
                result.append(self._anonymize_dict(item, rules, {
                    **context,
                    "current_path": f"{context.get('current_path', '')}[{i}]"
                }))
            elif isinstance(item, list):
                result.append(self._anonymize_list(item, rules, {
                    **context,
                    "current_path": f"{context.get('current_path', '')}[{i}]"
                }))
            else:
                # 查找匹配当前路径的规则
                field_path = f"{context.get('current_path', '')}[{i}]"
                matching_rules = [r for r in rules if self._path_matches(field_path, r.field_path)]
                
                if matching_rules:
                    rule = matching_rules[0]
                    result.append(self._apply_rule_to_value(item, rule, context))
                else:
                    result.append(item)
        
        return result
    
    def _apply_rule_to_value(
        self,
        value: Any,
        rule: Optional[AnonymizationRule],
        context: Dict[str, Any]
    ) -> Any:
        """对单个值应用匿名化规则"""
        if rule is None:
            return value
        
        technique = rule.technique
        params = rule.parameters
        
        try:
            if technique == AnonymizationTechnique.SUPPRESSION:
                return self._suppress(value, params)
            
            elif technique == AnonymizationTechnique.GENERALIZATION:
                return self._generalize(value, params, context)
            
            elif technique == AnonymizationTechnique.PERTURBATION:
                return self._perturb(value, params)
            
            elif technique == AnonymizationTechnique.PERMUTATION:
                return self._permute(value, params, context)
            
            elif technique == AnonymizationTechnique.PSEUDONYMIZATION:
                return self._pseudonymize(value, params)
            
            elif technique == AnonymizationTechnique.MASKING:
                return self._mask(value, params)
            
            elif technique == AnonymizationTechnique.TOKENIZATION:
                return self._tokenize(value, params)
            
            elif technique == AnonymizationTechnique.HASHING:
                return self._hash_value(value, params)
            
            elif technique == AnonymizationTechnique.AGGREGATION:
                return self._aggregate(value, params, context)
            
            elif technique == AnonymizationTechnique.BINNING:
                return self._bin_value(value, params)
            
            elif technique == AnonymizationTechnique.ROUNDING:
                return self._round_value(value, params)
            
            else:
                logger.warning(f"不支持的匿名化技术: {technique}")
                return value
                
        except Exception as e:
            logger.error(f"应用规则 {rule.rule_id} 失败: {str(e)}")
            return value
    
    def _suppress(self, value: Any, params: Dict) -> Any:
        """抑制（删除）"""
        return params.get("suppression_value", self.config["default_suppression_value"])
    
    def _generalize(self, value: Any, params: Dict, context: Dict) -> Any:
        """泛化"""
        level = params.get("level", "high")
        
        if isinstance(value, (int, float)):
            # 数值泛化
            if level == "high":
                return f"~{value // 10 * 10}"
            elif level == "medium":
                return f"{value // 100 * 100}-{value // 100 * 100 + 99}"
            else:
                return str(value)
        
        elif isinstance(value, str):
            if level == "city" and "@" not in value:  # 地址
                # 提取城市级别（简化实现）
                parts = value.split()
                return parts[0] if parts else value
            elif level == "domain" and "@" in value:  # 邮箱
                # 只保留域名
                return value.split('@')[1]
        
        return str(value)
    
    def _perturb(self, value: Any, params: Dict) -> Any:
        """扰动（添加噪声）"""
        if isinstance(value, (int, float)):
            noise_level = params.get("noise_level", 0.1)
            noise = random.uniform(-noise_level, noise_level) * value
            return value + noise
        
        return value
    
    def _permute(self, value: Any, params: Dict, context: Dict) -> Any:
        """置换（需要上下文中的置换表）"""
        permutation_map = context.get("permutation_map", {})
        if value in permutation_map:
            return permutation_map[value]
        return value
    
    def _pseudonymize(self, value: Any, params: Dict) -> Any:
        """假名化"""
        str_value = str(value)
        
        if str_value in self.pseudonym_map:
            return self.pseudonym_map[str_value]
        
        # 生成假名
        salt = params.get("salt", self.config["pseudonym_salt"])
        hash_input = f"{str_value}{salt}".encode()
        pseudonym = hashlib.sha256(hash_input).hexdigest()[:12]
        
        # 如果要求保持格式
        if self.config["preserve_format"] and isinstance(value, str):
            # 尝试保持原始格式（如保持邮箱格式）
            if '@' in str_value:
                pseudonym = f"user_{pseudonym}@anon.local"
        
        self.pseudonym_map[str_value] = pseudonym
        return pseudonym
    
    def _mask(self, value: Any, params: Dict) -> Any:
        """掩码"""
        str_value = str(value)
        mask_pattern = params.get("mask_pattern")
        replacement = params.get("replacement", "***")
        
        if mask_pattern and re.search(mask_pattern, str_value):
            return re.sub(mask_pattern, replacement, str_value)
        
        # 默认掩码：显示首尾，中间用*代替
        if len(str_value) > 4:
            visible_chars = params.get("visible_chars", 2)
            return str_value[:visible_chars] + "*" * (len(str_value) - 2*visible_chars) + str_value[-visible_chars:]
        else:
            return "*" * len(str_value)
    
    def _tokenize(self, value: Any, params: Dict) -> Any:
        """令牌化"""
        str_value = str(value)
        
        if str_value in self.token_map:
            return self.token_map[str_value]
        
        # 生成令牌
        token_length = params.get("token_length", 16)
        token = hashlib.sha256(str_value.encode()).hexdigest()[:token_length]
        
        self.token_map[str_value] = token
        return token
    
    def _hash_value(self, value: Any, params: Dict) -> str:
        """哈希"""
        str_value = str(value)
        algorithm = params.get("algorithm", self.config["hash_algorithm"])
        
        if algorithm == "sha256":
            return hashlib.sha256(str_value.encode()).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(str_value.encode()).hexdigest()
        else:
            return hashlib.sha256(str_value.encode()).hexdigest()
    
    def _aggregate(self, value: Any, params: Dict, context: Dict) -> Any:
        """聚合（需要上下文中的聚合值）"""
        return context.get("aggregated_value", value)
    
    def _bin_value(self, value: Any, params: Dict) -> Any:
        """分箱"""
        bins = params.get("bins", [])
        labels = params.get("labels", [])
        
        if not bins or not isinstance(value, (int, float)):
            return value
        
        for i in range(len(bins) - 1):
            if bins[i] <= value < bins[i + 1]:
                return labels[i] if i < len(labels) else f"{bins[i]}-{bins[i+1]}"
        
        # 超出范围
        if value >= bins[-1]:
            return labels[-1] if labels and len(labels) >= len(bins) else f">{bins[-1]}"
        
        return str(value)
    
    def _round_value(self, value: Any, params: Dict) -> Any:
        """四舍五入"""
        if not isinstance(value, (int, float)):
            return value
        
        precision = params.get("precision", 0)
        
        if precision >= 0:
            # 小数位取整
            return round(value, precision)
        else:
            # 整数位取整（如千位取整）
            factor = 10 ** (-precision)
            return round(value / factor) * factor
    
    def _path_matches(self, current_path: str, rule_path: str) -> bool:
        """检查路径是否匹配规则"""
        # 支持通配符匹配
        if rule_path == "*":
            return True
        
        if rule_path.endswith(".*"):
            prefix = rule_path[:-2]
            return current_path.startswith(prefix)
        
        return current_path == rule_path
    
    def _infer_data_type(self, field_path: str) -> DataType:
        """推断字段的数据类型"""
        if "email" in field_path or "mail" in field_path:
            return DataType.EMAIL
        elif "phone" in field_path or "mobile" in field_path:
            return DataType.PHONE
        elif "name" in field_path:
            return DataType.NAME
        elif "address" in field_path:
            return DataType.ADDRESS
        elif "age" in field_path:
            return DataType.INTEGER
        elif "salary" in field_path or "amount" in field_path:
            return DataType.FLOAT
        elif "date" in field_path:
            return DataType.DATE
        elif "id" in field_path or "identifier" in field_path:
            return DataType.ID
        else:
            return DataType.STRING
    
    def _compute_hash(self, data: Any) -> str:
        """计算数据的哈希值"""
        try:
            if isinstance(data, (dict, list)):
                str_data = json.dumps(data, sort_keys=True)
            else:
                str_data = str(data)
            
            return hashlib.sha256(str_data.encode()).hexdigest()
        except:
            return hashlib.sha256(str(time.time()).encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_rules": len(self.rules),
            "techniques_used": list(set(r.technique.value for r in self.rules.values())),
            "pseudonym_map_size": len(self.pseudonym_map),
            "token_map_size": len(self.token_map)
        }


# 单例实例
_anonymization_engine_instance = None


def get_anonymization_engine() -> AnonymizationEngine:
    """获取匿名化引擎单例实例"""
    global _anonymization_engine_instance
    if _anonymization_engine_instance is None:
        _anonymization_engine_instance = AnonymizationEngine()
    return _anonymization_engine_instance

