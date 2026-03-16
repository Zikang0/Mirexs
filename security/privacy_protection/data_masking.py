"""
数据脱敏模块 - 敏感数据脱敏处理
提供实时数据脱敏功能，用于日志、API响应等场景
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field

from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MaskingStrategy(Enum):
    """脱敏策略枚举"""
    FULL_MASK = "full_mask"  # 完全掩码
    PARTIAL_MASK = "partial_mask"  # 部分掩码
    HASH = "hash"  # 哈希
    TRUNCATE = "truncate"  # 截断
    REDACT = "redact"  # 编辑删除
    FORMAT_PRESERVING = "format_preserving"  # 保持格式


class MaskingRule:
    """脱敏规则"""
    
    def __init__(
        self,
        pattern: str,
        strategy: MaskingStrategy,
        replacement: str = "***",
        visible_chars: int = 2,
        hash_algorithm: str = "sha256"
    ):
        """
        初始化脱敏规则
        
        Args:
            pattern: 匹配模式（正则表达式）
            strategy: 脱敏策略
            replacement: 替换字符串
            visible_chars: 可见字符数（用于部分掩码）
            hash_algorithm: 哈希算法
        """
        self.pattern = re.compile(pattern) if pattern else None
        self.strategy = strategy
        self.replacement = replacement
        self.visible_chars = visible_chars
        self.hash_algorithm = hash_algorithm


@dataclass
class MaskedField:
    """脱敏字段定义"""
    field_path: str  # 字段路径，支持点号嵌套
    rule: MaskingRule
    description: str = ""
    enabled: bool = True


class DataMasking:
    """
    数据脱敏器 - 对敏感数据进行实时脱敏
    支持多种脱敏策略和灵活的规则配置
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据脱敏器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 脱敏规则
        self.rules: Dict[str, MaskingRule] = {}
        self.field_rules: Dict[str, MaskedField] = {}
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        
        # 初始化默认规则
        self._init_default_rules()
        
        logger.info(f"数据脱敏器初始化完成，已加载 {len(self.field_rules)} 条默认规则")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "default_mask_char": "*",
            "default_visible_chars": 2,
            "enable_audit": True,
            "mask_in_logs": True,
            "mask_in_api_responses": True,
            "sensitive_patterns": {
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "phone": r"1[3-9]\d{9}|\d{3}-\d{4}-\d{4}|\d{11}",
                "id_card": r"[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
                "credit_card": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
                "password": r"password[=:]\s*\S+",
                "token": r"token[=:]\s*\S+",
                "ip_address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
                "mac_address": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"
            }
        }
    
    def _init_default_rules(self):
        """初始化默认脱敏规则"""
        patterns = self.config["sensitive_patterns"]
        
        # 邮箱：只保留前2个字符和域名
        self.add_rule(
            field_path="email",
            pattern=patterns["email"],
            strategy=MaskingStrategy.PARTIAL_MASK,
            visible_chars=2,
            description="邮箱地址脱敏"
        )
        
        # 手机号：保留前3位和后4位
        self.add_rule(
            field_path="phone",
            pattern=patterns["phone"],
            strategy=MaskingStrategy.PARTIAL_MASK,
            visible_chars=3,
            description="手机号脱敏"
        )
        
        # 身份证号：保留前6位和后4位
        self.add_rule(
            field_path="id_card",
            pattern=patterns["id_card"],
            strategy=MaskingStrategy.PARTIAL_MASK,
            visible_chars=6,
            description="身份证号脱敏"
        )
        
        # 信用卡号：保留后4位
        self.add_rule(
            field_path="credit_card",
            pattern=patterns["credit_card"],
            strategy=MaskingStrategy.PARTIAL_MASK,
            visible_chars=0,  # 保留后4位，通过自定义处理
            description="信用卡号脱敏"
        )
        
        # 密码：完全掩码
        self.add_rule(
            field_path="password",
            pattern=patterns["password"],
            strategy=MaskingStrategy.FULL_MASK,
            replacement="[FILTERED]",
            description="密码完全掩码"
        )
        
        # 令牌：完全掩码
        self.add_rule(
            field_path="token",
            pattern=patterns["token"],
            strategy=MaskingStrategy.FULL_MASK,
            replacement="[TOKEN_REDACTED]",
            description="令牌完全掩码"
        )
    
    def add_rule(
        self,
        field_path: str,
        pattern: str,
        strategy: Union[str, MaskingStrategy],
        replacement: str = "***",
        visible_chars: int = 2,
        description: str = ""
    ) -> Tuple[bool, str]:
        """
        添加脱敏规则
        
        Args:
            field_path: 字段路径
            pattern: 匹配模式
            strategy: 脱敏策略
            replacement: 替换字符串
            visible_chars: 可见字符数
            description: 描述
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if isinstance(strategy, str):
                strategy = MaskingStrategy(strategy)
            
            rule = MaskingRule(
                pattern=pattern,
                strategy=strategy,
                replacement=replacement,
                visible_chars=visible_chars
            )
            
            self.rules[field_path] = rule
            
            masked_field = MaskedField(
                field_path=field_path,
                rule=rule,
                description=description,
                enabled=True
            )
            
            self.field_rules[field_path] = masked_field
            
            logger.info(f"添加脱敏规则: {field_path} ({strategy.value})")
            return True, "规则添加成功"
            
        except Exception as e:
            logger.error(f"添加脱敏规则失败: {str(e)}")
            return False, f"添加失败: {str(e)}"
    
    def remove_rule(self, field_path: str) -> Tuple[bool, str]:
        """
        移除脱敏规则
        
        Args:
            field_path: 字段路径
        
        Returns:
            (成功标志, 消息)
        """
        if field_path in self.field_rules:
            del self.field_rules[field_path]
            if field_path in self.rules:
                del self.rules[field_path]
            logger.info(f"移除脱敏规则: {field_path}")
            return True, "规则移除成功"
        return False, f"规则不存在: {field_path}"
    
    def mask_text(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        对文本进行脱敏处理
        
        Args:
            text: 原始文本
            context: 上下文信息
        
        Returns:
            脱敏后的文本
        """
        if not text:
            return text
        
        masked = text
        
        for field_path, rule in self.rules.items():
            if not rule.pattern:
                continue
            
            try:
                # 查找所有匹配
                matches = list(rule.pattern.finditer(masked))
                
                # 从后往前替换，避免位置变化
                for match in reversed(matches):
                    original = match.group(0)
                    masked_value = self._apply_strategy(original, rule)
                    masked = masked[:match.start()] + masked_value + masked[match.end():]
                    
            except Exception as e:
                logger.debug(f"应用规则 {field_path} 失败: {str(e)}")
        
        return masked
    
    def mask_object(
        self,
        obj: Any,
        rules: Optional[List[str]] = None,
        path: str = ""
    ) -> Any:
        """
        对对象进行脱敏处理
        
        Args:
            obj: 原始对象（dict, list, 或基本类型）
            rules: 要应用的规则列表（None表示所有规则）
            path: 当前路径
        
        Returns:
            脱敏后的对象
        """
        if obj is None:
            return None
        
        # 确定要应用的规则
        active_rules = rules if rules is not None else list(self.field_rules.keys())
        
        if isinstance(obj, dict):
            return self._mask_dict(obj, active_rules, path)
        elif isinstance(obj, list):
            return self._mask_list(obj, active_rules, path)
        elif isinstance(obj, str):
            # 检查当前路径是否有特定规则
            return self._mask_value(obj, path, active_rules)
        else:
            return obj
    
    def _mask_dict(
        self,
        data: Dict,
        rules: List[str],
        current_path: str
    ) -> Dict:
        """脱敏字典"""
        result = {}
        
        for key, value in data.items():
            field_path = f"{current_path}.{key}" if current_path else key
            
            if isinstance(value, dict):
                result[key] = self._mask_dict(value, rules, field_path)
            elif isinstance(value, list):
                result[key] = self._mask_list(value, rules, field_path)
            elif isinstance(value, str):
                result[key] = self._mask_value(value, field_path, rules)
            else:
                result[key] = value
        
        return result
    
    def _mask_list(
        self,
        data: List,
        rules: List[str],
        current_path: str
    ) -> List:
        """脱敏列表"""
        result = []
        
        for i, item in enumerate(data):
            item_path = f"{current_path}[{i}]"
            
            if isinstance(item, dict):
                result.append(self._mask_dict(item, rules, item_path))
            elif isinstance(item, list):
                result.append(self._mask_list(item, rules, item_path))
            elif isinstance(item, str):
                result.append(self._mask_value(item, item_path, rules))
            else:
                result.append(item)
        
        return result
    
    def _mask_value(
        self,
        value: str,
        field_path: str,
        rules: List[str]
    ) -> str:
        """脱敏单个值"""
        # 检查是否有针对该路径的特定规则
        for rule_path in rules:
            if self._path_matches(field_path, rule_path):
                rule = self.field_rules.get(rule_path)
                if rule and rule.enabled:
                    return self._apply_strategy(value, rule.rule)
        
        # 没有特定规则，使用全局模式匹配
        return self.mask_text(value)
    
    def _path_matches(self, current_path: str, rule_path: str) -> bool:
        """检查路径是否匹配规则"""
        # 支持通配符
        if rule_path.endswith(".*"):
            prefix = rule_path[:-2]
            return current_path.startswith(prefix)
        
        # 支持数组索引通配
        if "[*]" in rule_path:
            pattern = rule_path.replace("[*]", "\\[\\d+\\]")
            return re.match(f"^{pattern}$", current_path) is not None
        
        return current_path == rule_path or current_path.endswith(f".{rule_path}")
    
    def _apply_strategy(self, value: str, rule: MaskingRule) -> str:
        """应用脱敏策略"""
        if not value:
            return value
        
        if rule.strategy == MaskingStrategy.FULL_MASK:
            return rule.replacement
        
        elif rule.strategy == MaskingStrategy.PARTIAL_MASK:
            return self._partial_mask(value, rule)
        
        elif rule.strategy == MaskingStrategy.HASH:
            return self._hash_value(value, rule)
        
        elif rule.strategy == MaskingStrategy.TRUNCATE:
            return value[:rule.visible_chars] + "..."
        
        elif rule.strategy == MaskingStrategy.REDACT:
            return ""
        
        elif rule.strategy == MaskingStrategy.FORMAT_PRESERVING:
            return self._format_preserving_mask(value, rule)
        
        return value
    
    def _partial_mask(self, value: str, rule: MaskingRule) -> str:
        """部分掩码"""
        length = len(value)
        visible = rule.visible_chars
        mask_char = self.config["default_mask_char"]
        
        if length <= visible * 2:
            # 字符串太短，只保留首尾各1个字符
            if length <= 2:
                return mask_char * length
            return value[0] + mask_char * (length - 2) + value[-1]
        
        # 信用卡号特殊处理：只保留后4位
        if re.match(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}", value):
            clean = re.sub(r"[-\s]", "", value)
            if len(clean) == 16:
                return mask_char * 12 + clean[-4:]
        
        # 手机号特殊处理：保留前3后4
        if re.match(r"1[3-9]\d{9}", value):
            return value[:3] + mask_char * 4 + value[-4:]
        
        # 邮箱特殊处理：保留前visible个字符和域名
        if "@" in value:
            local, domain = value.split("@", 1)
            if len(local) > visible:
                local_masked = local[:visible] + mask_char * (len(local) - visible)
            else:
                local_masked = local
            return f"{local_masked}@{domain}"
        
        # 默认部分掩码
        return value[:visible] + mask_char * (length - visible * 2) + value[-visible:]
    
    def _hash_value(self, value: str, rule: MaskingRule) -> str:
        """哈希处理"""
        import hashlib
        
        if rule.hash_algorithm == "sha256":
            return hashlib.sha256(value.encode()).hexdigest()[:16]
        elif rule.hash_algorithm == "md5":
            return hashlib.md5(value.encode()).hexdigest()
        else:
            return hashlib.sha256(value.encode()).hexdigest()[:12]
    
    def _format_preserving_mask(self, value: str, rule: MaskingRule) -> str:
        """保持格式的掩码"""
        # 保持原始格式，但替换内容
        if re.match(r"\d+", value):
            # 数字：替换为随机数字
            import random
            return ''.join(str(random.randint(0, 9)) for _ in value)
        elif re.match(r"[a-zA-Z]+", value):
            # 字母：替换为随机字母
            import random
            import string
            return ''.join(random.choice(string.ascii_letters) for _ in value)
        else:
            # 其他：保持格式但替换为*
            return rule.replacement
    
    def mask_log_line(self, log_line: str) -> str:
        """
        脱敏日志行
        
        Args:
            log_line: 原始日志行
        
        Returns:
            脱敏后的日志行
        """
        if not self.config["mask_in_logs"]:
            return log_line
        
        return self.mask_text(log_line)
    
    def mask_api_response(
        self,
        response: Dict[str, Any],
        sensitive_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        脱敏API响应
        
        Args:
            response: API响应数据
            sensitive_fields: 敏感字段列表
        
        Returns:
            脱敏后的响应
        """
        if not self.config["mask_in_api_responses"]:
            return response
        
        rules = sensitive_fields or list(self.field_rules.keys())
        return self.mask_object(response, rules)
    
    def mask_sql_query(self, query: str) -> str:
        """
        脱敏SQL查询
        
        Args:
            query: SQL查询语句
        
        Returns:
            脱敏后的SQL
        """
        # SQL中的敏感数据通常在VALUES部分
        # 简单的模式匹配脱敏
        patterns = [
            (r"VALUES\s*\([^)]+\)", "VALUES ([REDACTED])"),  # VALUES部分
            (r"password\s*=\s*'[^']*'", "password = '[REDACTED]'"),  # password字段
            (r"token\s*=\s*'[^']*'", "token = '[REDACTED]'"),  # token字段
            (r"credit_card\s*=\s*'[^']*'", "credit_card = '[REDACTED]'"),  # 信用卡字段
        ]
        
        masked = query
        for pattern, replacement in patterns:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)
        
        return masked
    
    def add_sensitive_pattern(
        self,
        name: str,
        pattern: str,
        strategy: str = "partial_mask",
        visible_chars: int = 2
    ) -> Tuple[bool, str]:
        """
        添加敏感数据模式
        
        Args:
            name: 模式名称
            pattern: 正则表达式
            strategy: 脱敏策略
            visible_chars: 可见字符数
        
        Returns:
            (成功标志, 消息)
        """
        try:
            return self.add_rule(
                field_path=name,
                pattern=pattern,
                strategy=strategy,
                visible_chars=visible_chars,
                description=f"Custom pattern: {name}"
            )
        except Exception as e:
            logger.error(f"添加敏感模式失败: {str(e)}")
            return False, f"添加失败: {str(e)}"
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """获取所有规则"""
        rules = []
        for field_path, field in self.field_rules.items():
            rules.append({
                "field_path": field.field_path,
                "strategy": field.rule.strategy.value,
                "description": field.description,
                "enabled": field.enabled,
                "visible_chars": field.rule.visible_chars
            })
        return rules
    
    def enable_rule(self, field_path: str, enabled: bool = True) -> bool:
        """启用/禁用规则"""
        if field_path in self.field_rules:
            self.field_rules[field_path].enabled = enabled
            logger.info(f"{'启用' if enabled else '禁用'}脱敏规则: {field_path}")
            return True
        return False


# 单例实例
_data_masking_instance = None


def get_data_masking() -> DataMasking:
    """获取数据脱敏器单例实例"""
    global _data_masking_instance
    if _data_masking_instance is None:
        _data_masking_instance = DataMasking()
    return _data_masking_instance

