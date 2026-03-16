"""
安全策略模块 - 安全管理策略
定义和管理系统安全策略，包括访问控制、加密、审计等策略
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.permission_manager import PermissionManager, get_permission_manager

logger = logging.getLogger(__name__)


class PolicyDomain(Enum):
    """策略域枚举"""
    ACCESS_CONTROL = "access_control"  # 访问控制
    AUTHENTICATION = "authentication"  # 认证
    ENCRYPTION = "encryption"  # 加密
    AUDIT = "audit"  # 审计
    NETWORK = "network"  # 网络
    DATA_PROTECTION = "data_protection"  # 数据保护
    INCIDENT_RESPONSE = "incident_response"  # 事件响应
    PASSWORD = "password"  # 密码
    SESSION = "session"  # 会话
    API = "api"  # API


class PolicyEffect(Enum):
    """策略效果枚举"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE = "require"
    AUDIT = "audit"
    NOTIFY = "notify"


class PolicyStatus(Enum):
    """策略状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    REVIEW = "review"


@dataclass
class SecurityPolicy:
    """安全策略"""
    policy_id: str
    domain: PolicyDomain
    name: str
    description: str
    version: str
    status: PolicyStatus
    effect: PolicyEffect
    rules: List[Dict[str, Any]]
    conditions: Optional[Dict[str, Any]] = None
    exceptions: Optional[List[str]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: str = "system"
    approved_by: Optional[str] = None
    effective_date: Optional[float] = None
    expiry_date: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityPolicy:
    """
    安全策略管理器 - 定义和管理系统安全策略
    支持策略的生命周期管理和自动评估
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全策略管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 策略存储
        self.policies: Dict[str, SecurityPolicy] = {}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/policies"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.permission_manager = get_permission_manager()
        
        # 加载策略
        self._load_policies()
        
        # 初始化默认策略
        self._init_default_policies()
        
        logger.info(f"安全策略管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/policies",
            "policy_auto_approve": True,
            "require_approval_for": ["critical", "high"],
            "versioning_enabled": True,
            "max_policy_versions": 10,
            "policy_check_interval": 3600,  # 1小时
            "enforcement_mode": "strict",  # strict, permissive, audit
            "default_policies": {
                "password_policy": {
                    "name": "密码策略",
                    "description": "定义密码复杂度要求",
                    "domain": "password",
                    "effect": "require",
                    "rules": [
                        {"rule": "min_length", "value": 8},
                        {"rule": "require_uppercase", "value": True},
                        {"rule": "require_lowercase", "value": True},
                        {"rule": "require_numbers", "value": True},
                        {"rule": "require_special", "value": True},
                        {"rule": "max_age_days", "value": 90}
                    ]
                },
                "session_policy": {
                    "name": "会话策略",
                    "description": "定义会话管理规则",
                    "domain": "session",
                    "effect": "require",
                    "rules": [
                        {"rule": "session_timeout", "value": 3600},
                        {"rule": "max_concurrent_sessions", "value": 5},
                        {"rule": "require_mfa", "value": True}
                    ]
                },
                "access_policy": {
                    "name": "访问控制策略",
                    "description": "定义访问控制规则",
                    "domain": "access_control",
                    "effect": "allow",
                    "rules": [
                        {"rule": "principle_of_least_privilege", "value": True},
                        {"rule": "require_approval_for_sensitive", "value": True}
                    ]
                },
                "audit_policy": {
                    "name": "审计策略",
                    "description": "定义审计日志要求",
                    "domain": "audit",
                    "effect": "require",
                    "rules": [
                        {"rule": "log_all_access", "value": True},
                        {"rule": "log_auth_events", "value": True},
                        {"rule": "retention_days", "value": 365}
                    ]
                },
                "encryption_policy": {
                    "name": "加密策略",
                    "description": "定义数据加密要求",
                    "domain": "encryption",
                    "effect": "require",
                    "rules": [
                        {"rule": "encrypt_at_rest", "value": True},
                        {"rule": "encrypt_in_transit", "value": True},
                        {"rule": "minimum_key_length", "value": 256}
                    ]
                }
            }
        }
    
    def _load_policies(self):
        """从存储加载策略"""
        try:
            policies_file = self.storage_path / "policies.json"
            if not policies_file.exists():
                return
            
            with open(policies_file, 'r', encoding='utf-8') as f:
                policies_data = json.load(f)
            
            for policy_id, policy_dict in policies_data.items():
                policy_dict["domain"] = PolicyDomain(policy_dict["domain"])
                policy_dict["effect"] = PolicyEffect(policy_dict["effect"])
                policy_dict["status"] = PolicyStatus(policy_dict["status"])
                self.policies[policy_id] = SecurityPolicy(**policy_dict)
            
            logger.info(f"加载了 {len(self.policies)} 条安全策略")
        except Exception as e:
            logger.error(f"加载安全策略失败: {str(e)}")
    
    def _save_policies(self):
        """保存策略到存储"""
        try:
            policies_data = {}
            for policy_id, policy in self.policies.items():
                policy_dict = {
                    "policy_id": policy.policy_id,
                    "domain": policy.domain.value,
                    "name": policy.name,
                    "description": policy.description,
                    "version": policy.version,
                    "status": policy.status.value,
                    "effect": policy.effect.value,
                    "rules": policy.rules,
                    "conditions": policy.conditions,
                    "exceptions": policy.exceptions,
                    "created_at": policy.created_at,
                    "updated_at": policy.updated_at,
                    "created_by": policy.created_by,
                    "approved_by": policy.approved_by,
                    "effective_date": policy.effective_date,
                    "expiry_date": policy.expiry_date,
                    "tags": policy.tags,
                    "metadata": policy.metadata
                }
                policies_data[policy_id] = policy_dict
            
            with open(self.storage_path / "policies.json", 'w', encoding='utf-8') as f:
                json.dump(policies_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.policies)} 条安全策略")
        except Exception as e:
            logger.error(f"保存安全策略失败: {str(e)}")
    
    def _init_default_policies(self):
        """初始化默认策略"""
        default_policies = self.config["default_policies"]
        
        for policy_id, policy_config in default_policies.items():
            if policy_id not in self.policies:
                policy = SecurityPolicy(
                    policy_id=policy_id,
                    domain=PolicyDomain(policy_config["domain"]),
                    name=policy_config["name"],
                    description=policy_config["description"],
                    version="1.0.0",
                    status=PolicyStatus.ACTIVE,
                    effect=PolicyEffect(policy_config["effect"]),
                    rules=policy_config["rules"],
                    created_by="system",
                    effective_date=time.time(),
                    tags=["default", policy_config["domain"]]
                )
                self.policies[policy_id] = policy
        
        self._save_policies()
        logger.info(f"初始化了 {len(default_policies)} 条默认安全策略")
    
    def create_policy(
        self,
        policy_id: str,
        domain: PolicyDomain,
        name: str,
        description: str,
        effect: PolicyEffect,
        rules: List[Dict[str, Any]],
        created_by: str,
        version: str = "1.0.0",
        conditions: Optional[Dict[str, Any]] = None,
        exceptions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[SecurityPolicy]]:
        """
        创建新策略
        
        Args:
            policy_id: 策略ID
            domain: 策略域
            name: 策略名称
            description: 描述
            effect: 策略效果
            rules: 规则列表
            created_by: 创建者
            version: 版本
            conditions: 条件
            exceptions: 例外
            tags: 标签
            metadata: 元数据
        
        Returns:
            (成功标志, 消息, 策略对象)
        """
        if policy_id in self.policies:
            return False, f"策略ID已存在: {policy_id}", None
        
        # 检查是否需要审批
        status = PolicyStatus.DRAFT
        if domain.value in self.config["require_approval_for"]:
            status = PolicyStatus.REVIEW
        elif self.config["policy_auto_approve"]:
            status = PolicyStatus.ACTIVE
        
        policy = SecurityPolicy(
            policy_id=policy_id,
            domain=domain,
            name=name,
            description=description,
            version=version,
            status=status,
            effect=effect,
            rules=rules,
            conditions=conditions,
            exceptions=exceptions,
            created_at=time.time(),
            updated_at=time.time(),
            created_by=created_by,
            effective_date=time.time() if status == PolicyStatus.ACTIVE else None,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self.policies[policy_id] = policy
        self._save_policies()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=created_by,
            event_type="POLICY_CREATED",
            severity="info",
            details={
                "policy_id": policy_id,
                "name": name,
                "domain": domain.value,
                "status": status.value
            }
        )
        
        logger.info(f"创建安全策略: {policy_id}")
        return True, "策略创建成功", policy
    
    def update_policy(
        self,
        policy_id: str,
        updated_by: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        更新策略
        
        Args:
            policy_id: 策略ID
            updated_by: 更新者
            **kwargs: 更新字段
        
        Returns:
            (成功标志, 消息)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}"
        
        policy = self.policies[policy_id]
        
        # 记录变更
        changes = []
        for key, value in kwargs.items():
            if hasattr(policy, key) and key not in ["policy_id", "created_at", "created_by"]:
                old_value = getattr(policy, key)
                setattr(policy, key, value)
                changes.append(f"{key}: {old_value} -> {value}")
        
        policy.updated_at = time.time()
        
        # 如果修改了规则，可能需要重新审批
        if "rules" in kwargs and policy.domain.value in self.config["require_approval_for"]:
            policy.status = PolicyStatus.REVIEW
        
        self._save_policies()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=updated_by,
            event_type="POLICY_UPDATED",
            severity="info",
            details={
                "policy_id": policy_id,
                "changes": changes
            }
        )
        
        logger.info(f"更新安全策略: {policy_id}")
        return True, "策略更新成功"
    
    def approve_policy(
        self,
        policy_id: str,
        approved_by: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        审批策略
        
        Args:
            policy_id: 策略ID
            approved_by: 审批者
            notes: 审批备注
        
        Returns:
            (成功标志, 消息)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}"
        
        policy = self.policies[policy_id]
        
        if policy.status != PolicyStatus.REVIEW:
            return False, f"策略状态不是待审批: {policy.status.value}"
        
        policy.status = PolicyStatus.ACTIVE
        policy.approved_by = approved_by
        policy.effective_date = time.time()
        policy.metadata["approval_notes"] = notes
        
        self._save_policies()
        
        self.access_logger.log_security_event(
            user_id=approved_by,
            event_type="POLICY_APPROVED",
            severity="info",
            details={
                "policy_id": policy_id,
                "notes": notes
            }
        )
        
        logger.info(f"安全策略已审批: {policy_id}")
        return True, "策略审批成功"
    
    def activate_policy(
        self,
        policy_id: str,
        activated_by: str
    ) -> Tuple[bool, str]:
        """
        激活策略
        
        Args:
            policy_id: 策略ID
            activated_by: 激活者
        
        Returns:
            (成功标志, 消息)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}"
        
        policy = self.policies[policy_id]
        
        if policy.status == PolicyStatus.ACTIVE:
            return False, "策略已经是激活状态"
        
        policy.status = PolicyStatus.ACTIVE
        policy.effective_date = time.time()
        policy.updated_at = time.time()
        
        self._save_policies()
        
        self.access_logger.log_security_event(
            user_id=activated_by,
            event_type="POLICY_ACTIVATED",
            severity="info",
            details={"policy_id": policy_id}
        )
        
        logger.info(f"安全策略已激活: {policy_id}")
        return True, "策略激活成功"
    
    def deactivate_policy(
        self,
        policy_id: str,
        deactivated_by: str,
        reason: str
    ) -> Tuple[bool, str]:
        """
        停用策略
        
        Args:
            policy_id: 策略ID
            deactivated_by: 停用者
            reason: 停用原因
        
        Returns:
            (成功标志, 消息)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}"
        
        policy = self.policies[policy_id]
        
        policy.status = PolicyStatus.INACTIVE
        policy.updated_at = time.time()
        policy.metadata["deactivated_reason"] = reason
        policy.metadata["deactivated_by"] = deactivated_by
        policy.metadata["deactivated_at"] = time.time()
        
        self._save_policies()
        
        self.access_logger.log_security_event(
            user_id=deactivated_by,
            event_type="POLICY_DEACTIVATED",
            severity="warning",
            details={
                "policy_id": policy_id,
                "reason": reason
            }
        )
        
        logger.info(f"安全策略已停用: {policy_id}")
        return True, "策略停用成功"
    
    def evaluate_policy(
        self,
        policy_id: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        评估策略
        
        Args:
            policy_id: 策略ID
            context: 评估上下文
        
        Returns:
            (是否通过, 消息, 评估结果)
        """
        if policy_id not in self.policies:
            return False, f"策略不存在: {policy_id}", None
        
        policy = self.policies[policy_id]
        
        if policy.status != PolicyStatus.ACTIVE:
            return True, "策略未激活，跳过评估", {"skipped": True}
        
        results = []
        passed = True
        
        for rule in policy.rules:
            rule_result = self._evaluate_rule(rule, context)
            results.append(rule_result)
            if not rule_result["passed"]:
                passed = False
        
        # 根据策略效果决定最终结果
        if policy.effect == PolicyEffect.DENY:
            final_passed = not passed  # 如果任何规则失败，则DENY通过
        elif policy.effect == PolicyEffect.REQUIRE:
            final_passed = passed  # 所有规则必须通过
        else:
            final_passed = True
        
        evaluation = {
            "policy_id": policy_id,
            "name": policy.name,
            "effect": policy.effect.value,
            "passed": final_passed,
            "rule_results": results,
            "timestamp": time.time()
        }
        
        # 记录审计
        if not final_passed and self.config["enforcement_mode"] != "permissive":
            self.access_logger.log_security_event(
                user_id=context.get("user_id"),
                event_type="POLICY_VIOLATION",
                severity="warning",
                details={
                    "policy_id": policy_id,
                    "policy_name": policy.name,
                    "context": context,
                    "results": results
                }
            )
        
        message = "策略评估通过" if final_passed else f"策略 {policy.name} 未通过"
        return final_passed, message, evaluation
    
    def _evaluate_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个规则"""
        rule_name = rule.get("rule")
        expected = rule.get("value")
        actual = context.get(rule_name)
        
        # 简单的相等比较
        if actual is not None:
            passed = actual == expected
        else:
            passed = False
        
        return {
            "rule": rule_name,
            "expected": expected,
            "actual": actual,
            "passed": passed
        }
    
    def get_policy(self, policy_id: str) -> Optional[SecurityPolicy]:
        """获取策略"""
        return self.policies.get(policy_id)
    
    def get_policies(
        self,
        domain: Optional[PolicyDomain] = None,
        status: Optional[PolicyStatus] = None,
        effect: Optional[PolicyEffect] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取策略列表
        
        Args:
            domain: 策略域
            status: 状态
            effect: 效果
            tags: 标签
        
        Returns:
            策略列表
        """
        policies = list(self.policies.values())
        
        if domain:
            policies = [p for p in policies if p.domain == domain]
        if status:
            policies = [p for p in policies if p.status == status]
        if effect:
            policies = [p for p in policies if p.effect == effect]
        if tags:
            policies = [p for p in policies if any(tag in p.tags for tag in tags)]
        
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "domain": p.domain.value,
                "status": p.status.value,
                "effect": p.effect.value,
                "version": p.version,
                "description": p.description,
                "updated_at": p.updated_at,
                "tags": p.tags
            }
            for p in policies
        ]
    
    def check_compliance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查上下文是否符合所有激活策略
        
        Args:
            context: 检查上下文
        
        Returns:
            合规检查结果
        """
        results = {
            "compliant": True,
            "policies_checked": 0,
            "violations": [],
            "details": {}
        }
        
        for policy_id, policy in self.policies.items():
            if policy.status != PolicyStatus.ACTIVE:
                continue
            
            passed, message, evaluation = self.evaluate_policy(policy_id, context)
            results["policies_checked"] += 1
            
            if not passed:
                results["compliant"] = False
                results["violations"].append({
                    "policy_id": policy_id,
                    "policy_name": policy.name,
                    "message": message,
                    "evaluation": evaluation
                })
            
            results["details"][policy_id] = {
                "name": policy.name,
                "passed": passed,
                "message": message
            }
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_policies": len(self.policies),
            "by_domain": {},
            "by_status": {},
            "by_effect": {},
            "active_policies": 0
        }
        
        for policy in self.policies.values():
            domain = policy.domain.value
            stats["by_domain"][domain] = stats["by_domain"].get(domain, 0) + 1
            
            status = policy.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            effect = policy.effect.value
            stats["by_effect"][effect] = stats["by_effect"].get(effect, 0) + 1
            
            if policy.status == PolicyStatus.ACTIVE:
                stats["active_policies"] += 1
        
        return stats


# 单例实例
_security_policy_instance = None


def get_security_policy() -> SecurityPolicy:
    """获取安全策略管理器单例实例"""
    global _security_policy_instance
    if _security_policy_instance is None:
        _security_policy_instance = SecurityPolicy()
    return _security_policy_instance

