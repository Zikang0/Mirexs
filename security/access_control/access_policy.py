"""
访问策略模块 - 定义访问控制策略
提供统一的策略管理接口，整合RBAC和ABAC
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .role_based_access import RoleBasedAccess, AccessRequest, AccessDecision
from .attribute_based_access import AttributeBasedAccess, AttributeContext, ABACPolicy
from .permission_manager import PermissionManager, get_permission_manager
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """策略类型枚举"""
    RBAC = "rbac"  # 基于角色的访问控制
    ABAC = "abac"  # 基于属性的访问控制
    HYBRID = "hybrid"  # 混合策略


class PolicyEffect(Enum):
    """策略效果枚举"""
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class Policy:
    """统一策略模型"""
    policy_id: str
    name: str
    description: str
    policy_type: PolicyType
    effect: PolicyEffect
    priority: int = 0
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)  # 策略条件
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AccessPolicy:
    """
    访问策略管理器
    统一管理RBAC和ABAC策略，提供策略的组合和评估
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化访问策略管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储策略
        self.policies: Dict[str, Policy] = {}
        
        # 初始化依赖
        self.rbac = RoleBasedAccess()
        self.abac = AttributeBasedAccess()
        self.permission_manager = get_permission_manager()
        self.audit_logger = AuditLogger()
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/policies"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 加载策略
        self._load_policies()
        
        # 初始化默认策略
        self._init_default_policies()
        
        logger.info(f"访问策略管理器初始化完成，已加载 {len(self.policies)} 个策略")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/policies",
            "evaluation_mode": "deny_overrides",  # deny_overrides, allow_overrides, first_applicable
            "enable_persistence": True,
            "max_policies": 1000,
            "cache_enabled": True,
            "cache_ttl_seconds": 300
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
                policy_dict["policy_type"] = PolicyType(policy_dict["policy_type"])
                policy_dict["effect"] = PolicyEffect(policy_dict["effect"])
                policy = Policy(**policy_dict)
                self.policies[policy_id] = policy
            
            logger.info(f"加载了 {len(self.policies)} 个策略")
        except Exception as e:
            logger.error(f"加载策略失败: {str(e)}")
    
    def _save_policies(self):
        """保存策略到存储"""
        if not self.config["enable_persistence"]:
            return
        
        try:
            policies_data = {}
            for policy_id, policy in self.policies.items():
                policy_dict = asdict(policy)
                policy_dict["policy_type"] = policy.policy_type.value
                policy_dict["effect"] = policy.effect.value
                policies_data[policy_id] = policy_dict
            
            with open(self.storage_path / "policies.json", 'w', encoding='utf-8') as f:
                json.dump(policies_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.policies)} 个策略")
        except Exception as e:
            logger.error(f"保存策略失败: {str(e)}")
    
    def _init_default_policies(self):
        """初始化默认策略"""
        default_policies = [
            Policy(
                policy_id="default_deny",
                name="默认拒绝策略",
                description="没有明确允许的访问默认拒绝",
                policy_type=PolicyType.HYBRID,
                effect=PolicyEffect.DENY,
                priority=0,
                conditions={"rule": "default"}
            ),
            Policy(
                policy_id="admin_full_access",
                name="管理员全权访问",
                description="管理员拥有所有资源的完全访问权限",
                policy_type=PolicyType.RBAC,
                effect=PolicyEffect.ALLOW,
                priority=100,
                conditions={
                    "roles": ["admin"],
                    "resources": ["*"],
                    "actions": ["*"]
                }
            ),
            Policy(
                policy_id="self_data_access",
                name="用户自有数据访问",
                description="用户可以访问自己的数据",
                policy_type=PolicyType.ABAC,
                effect=PolicyEffect.ALLOW,
                priority=50,
                conditions={
                    "resource_owner": "${user.id}",
                    "resources": ["user:*", "personal:*"],
                    "actions": ["read", "write"]
                }
            )
        ]
        
        for policy in default_policies:
            if policy.policy_id not in self.policies:
                self.add_policy(policy)
    
    async def evaluate(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        评估访问策略
        
        Args:
            user_id: 用户ID
            resource: 资源标识
            action: 操作
            context: 上下文信息
            session_id: 会话ID
        
        Returns:
            (是否允许, 原因, 策略ID)
        """
        try:
            # 获取适用策略
            applicable_policies = self._get_applicable_policies(resource, action)
            
            if not applicable_policies:
                # 没有适用策略，使用默认拒绝
                logger.debug(f"用户 {user_id} 访问 {resource}:{action} 无适用策略，默认拒绝")
                return False, "无适用策略，默认拒绝", None
            
            # 按优先级排序
            applicable_policies.sort(key=lambda p: p.priority, reverse=True)
            
            # 构建评估上下文
            eval_context = context or {}
            eval_context["user_id"] = user_id
            eval_context["resource"] = resource
            eval_context["action"] = action
            eval_context["session_id"] = session_id
            
            # 根据评估模式进行决策
            decision, policy_id, reason = await self._evaluate_policies(
                applicable_policies, eval_context
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="POLICY_EVALUATE",
                user_id=user_id,
                details={
                    "resource": resource,
                    "action": action,
                    "decision": "ALLOW" if decision else "DENY",
                    "policy_id": policy_id,
                    "reason": reason
                },
                severity="INFO"
            )
            
            return decision, reason, policy_id
            
        except Exception as e:
            logger.error(f"策略评估失败: {str(e)}")
            return False, f"评估异常: {str(e)}", None
    
    def _get_applicable_policies(
        self,
        resource: str,
        action: str
    ) -> List[Policy]:
        """获取适用策略"""
        applicable = []
        
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            
            # 检查策略条件
            if self._check_policy_applicability(policy, resource, action):
                applicable.append(policy)
        
        return applicable
    
    def _check_policy_applicability(
        self,
        policy: Policy,
        resource: str,
        action: str
    ) -> bool:
        """检查策略是否适用"""
        conditions = policy.conditions
        
        # 检查资源匹配
        if "resources" in conditions:
            resource_patterns = conditions["resources"]
            if not any(self._match_pattern(resource, pattern) for pattern in resource_patterns):
                return False
        
        # 检查操作匹配
        if "actions" in conditions:
            action_patterns = conditions["actions"]
            if not any(self._match_pattern(action, pattern) for pattern in action_patterns):
                return False
        
        return True
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """模式匹配"""
        if pattern == "*":
            return True
        if pattern == value:
            return True
        # 支持简单的通配符
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return value.endswith(pattern[1:])
        return False
    
    async def _evaluate_policies(
        self,
        policies: List[Policy],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], str]:
        """评估策略列表"""
        mode = self.config["evaluation_mode"]
        
        if mode == "deny_overrides":
            # 只要有一个DENY，就拒绝
            for policy in policies:
                if policy.effect == PolicyEffect.DENY:
                    result = await self._evaluate_single_policy(policy, context)
                    if result:
                        return False, policy.policy_id, f"被策略 {policy.name} 拒绝"
            
            # 检查是否有ALLOW
            for policy in policies:
                if policy.effect == PolicyEffect.ALLOW:
                    result = await self._evaluate_single_policy(policy, context)
                    if result:
                        return True, policy.policy_id, f"被策略 {policy.name} 允许"
            
            return False, None, "无决策"
        
        elif mode == "allow_overrides":
            # 只要有一个ALLOW，就允许
            for policy in policies:
                if policy.effect == PolicyEffect.ALLOW:
                    result = await self._evaluate_single_policy(policy, context)
                    if result:
                        return True, policy.policy_id, f"被策略 {policy.name} 允许"
            
            # 检查是否有DENY
            for policy in policies:
                if policy.effect == PolicyEffect.DENY:
                    result = await self._evaluate_single_policy(policy, context)
                    if result:
                        return False, policy.policy_id, f"被策略 {policy.name} 拒绝"
            
            return False, None, "无决策"
        
        else:  # first_applicable
            for policy in policies:
                result = await self._evaluate_single_policy(policy, context)
                if result:
                    if policy.effect == PolicyEffect.ALLOW:
                        return True, policy.policy_id, f"被策略 {policy.name} 允许"
                    else:
                        return False, policy.policy_id, f"被策略 {policy.name} 拒绝"
            
            return False, None, "无适用策略"
    
    async def _evaluate_single_policy(
        self,
        policy: Policy,
        context: Dict[str, Any]
    ) -> bool:
        """评估单个策略"""
        try:
            if policy.policy_type == PolicyType.RBAC:
                return await self._evaluate_rbac_policy(policy, context)
            elif policy.policy_type == PolicyType.ABAC:
                return await self._evaluate_abac_policy(policy, context)
            elif policy.policy_type == PolicyType.HYBRID:
                return await self._evaluate_hybrid_policy(policy, context)
            else:
                logger.warning(f"未知策略类型: {policy.policy_type}")
                return False
                
        except Exception as e:
            logger.error(f"评估策略 {policy.policy_id} 失败: {str(e)}")
            return False
    
    async def _evaluate_rbac_policy(
        self,
        policy: Policy,
        context: Dict[str, Any]
    ) -> bool:
        """评估RBAC策略"""
        user_id = context.get("user_id")
        resource = context.get("resource")
        action = context.get("action")
        
        # 检查角色
        required_roles = policy.conditions.get("roles", [])
        if required_roles:
            user_roles = self.permission_manager.get_user_roles(user_id)
            user_role_ids = [r["role_id"] for r in user_roles]
            if not any(role in user_role_ids for role in required_roles):
                return False
        
        # 检查权限
        required_permissions = policy.conditions.get("permissions", [])
        if required_permissions:
            user_permissions = self.permission_manager.get_user_permissions(user_id)
            if not all(perm in user_permissions for perm in required_permissions):
                return False
        
        return True
    
    async def _evaluate_abac_policy(
        self,
        policy: Policy,
        context: Dict[str, Any]
    ) -> bool:
        """评估ABAC策略"""
        # 构建ABAC上下文
        abac_context = AttributeContext(
            user_attributes={"id": context.get("user_id")},
            resource_attributes={"id": context.get("resource")},
            action_attributes={"name": context.get("action")},
            environment_attributes={k: v for k, v in context.items() 
                                   if k not in ["user_id", "resource", "action"]}
        )
        
        # 创建ABAC策略
        abac_policy = ABACPolicy(
            policy_id=policy.policy_id,
            name=policy.name,
            description=policy.description,
            target_resources=[context.get("resource", "*")],
            target_actions=[context.get("action", "*")],
            conditions=[],  # 需要从policy.conditions转换
            effect=AccessDecision.ALLOW if policy.effect == PolicyEffect.ALLOW else AccessDecision.DENY,
            priority=policy.priority
        )
        
        # 使用ABAC评估
        result = await self.abac.evaluate(
            user_id=context.get("user_id"),
            resource=context.get("resource"),
            action=context.get("action"),
            context=abac_context
        )
        
        return result.decision == AccessDecision.ALLOW
    
    async def _evaluate_hybrid_policy(
        self,
        policy: Policy,
        context: Dict[str, Any]
    ) -> bool:
        """评估混合策略"""
        # 先进行RBAC检查
        rbac_result = await self._evaluate_rbac_policy(policy, context)
        if not rbac_result:
            return False
        
        # 再进行ABAC检查
        abac_result = await self._evaluate_abac_policy(policy, context)
        
        return abac_result
    
    def add_policy(self, policy: Policy) -> Tuple[bool, str]:
        """添加策略"""
        try:
            if policy.policy_id in self.policies:
                return False, f"策略ID {policy.policy_id} 已存在"
            
            if len(self.policies) >= self.config["max_policies"]:
                return False, f"已达到最大策略数量限制 ({self.config['max_policies']})"
            
            policy.created_at = time.time()
            policy.updated_at = time.time()
            
            self.policies[policy.policy_id] = policy
            self._save_policies()
            
            logger.info(f"添加策略: {policy.policy_id} - {policy.name}")
            return True, "策略添加成功"
            
        except Exception as e:
            logger.error(f"添加策略失败: {str(e)}")
            return False, f"添加失败: {str(e)}"
    
    def update_policy(self, policy_id: str, **kwargs) -> Tuple[bool, str]:
        """更新策略"""
        try:
            if policy_id not in self.policies:
                return False, f"策略 {policy_id} 不存在"
            
            policy = self.policies[policy_id]
            
            for key, value in kwargs.items():
                if hasattr(policy, key) and key not in ["policy_id", "created_at"]:
                    setattr(policy, key, value)
            
            policy.updated_at = time.time()
            self._save_policies()
            
            logger.info(f"更新策略: {policy_id}")
            return True, "策略更新成功"
            
        except Exception as e:
            logger.error(f"更新策略失败: {str(e)}")
            return False, f"更新失败: {str(e)}"
    
    def delete_policy(self, policy_id: str) -> Tuple[bool, str]:
        """删除策略"""
        try:
            if policy_id not in self.policies:
                return False, f"策略 {policy_id} 不存在"
            
            del self.policies[policy_id]
            self._save_policies()
            
            logger.info(f"删除策略: {policy_id}")
            return True, "策略删除成功"
            
        except Exception as e:
            logger.error(f"删除策略失败: {str(e)}")
            return False, f"删除失败: {str(e)}"
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """获取策略"""
        return self.policies.get(policy_id)
    
    def list_policies(
        self,
        policy_type: Optional[PolicyType] = None,
        enabled_only: bool = False
    ) -> List[Dict[str, Any]]:
        """列出策略"""
        policies = []
        
        for policy in self.policies.values():
            if policy_type and policy.policy_type != policy_type:
                continue
            if enabled_only and not policy.enabled:
                continue
            
            policy_dict = asdict(policy)
            policy_dict["policy_type"] = policy.policy_type.value
            policy_dict["effect"] = policy.effect.value
            policies.append(policy_dict)
        
        return policies
    
    def validate_policy(self, policy: Policy) -> Tuple[bool, str]:
        """验证策略"""
        if not policy.policy_id:
            return False, "策略ID不能为空"
        
        if not policy.name:
            return False, "策略名称不能为空"
        
        if not isinstance(policy.policy_type, PolicyType):
            return False, "无效的策略类型"
        
        if not isinstance(policy.effect, PolicyEffect):
            return False, "无效的策略效果"
        
        return True, "策略有效"


# 单例实例
_access_policy_instance = None


def get_access_policy() -> AccessPolicy:
    """获取访问策略管理器单例实例"""
    global _access_policy_instance
    if _access_policy_instance is None:
        _access_policy_instance = AccessPolicy()
    return _access_policy_instance

