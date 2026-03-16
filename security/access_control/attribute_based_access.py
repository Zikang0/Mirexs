"""
基于属性的访问控制模块
提供ABAC（Attribute-Based Access Control）的核心实现
支持基于用户属性、资源属性、环境属性的动态访问控制
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List, Set, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
import json

from .permission_manager import PermissionManager, get_permission_manager
from .session_manager import SessionManager, get_session_manager
from .role_based_access import AccessDecision, AccessDecisionResult
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class AttributeType(Enum):
    """属性类型枚举"""
    USER = "user"  # 用户属性
    RESOURCE = "resource"  # 资源属性
    ACTION = "action"  # 操作属性
    ENVIRONMENT = "environment"  # 环境属性


class Operator(Enum):
    """操作符枚举"""
    EQUALS = "equals"  # 等于
    NOT_EQUALS = "not_equals"  # 不等于
    GREATER_THAN = "greater_than"  # 大于
    LESS_THAN = "less_than"  # 小于
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"  # 大于等于
    LESS_THAN_OR_EQUALS = "less_than_or_equals"  # 小于等于
    IN = "in"  # 在列表中
    NOT_IN = "not_in"  # 不在列表中
    CONTAINS = "contains"  # 包含
    STARTS_WITH = "starts_with"  # 以...开头
    ENDS_WITH = "ends_with"  # 以...结尾
    MATCHES = "matches"  # 正则匹配
    BETWEEN = "between"  # 在范围内
    EXISTS = "exists"  # 存在


@dataclass
class AttributeCondition:
    """属性条件"""
    attribute_type: AttributeType
    attribute_name: str
    operator: Operator
    value: Any
    attribute_path: Optional[str] = None  # 嵌套属性路径，如 "profile.age"


@dataclass
class ABACPolicy:
    """ABAC策略"""
    policy_id: str
    name: str
    description: str
    target_resources: List[str]  # 匹配的资源模式
    target_actions: List[str]  # 匹配的操作
    conditions: List[AttributeCondition]  # 条件列表
    effect: AccessDecision  # ALLOW 或 DENY
    priority: int = 0  # 优先级，数字越大优先级越高
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttributeContext:
    """属性上下文"""
    user_attributes: Dict[str, Any] = field(default_factory=dict)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    action_attributes: Dict[str, Any] = field(default_factory=dict)
    environment_attributes: Dict[str, Any] = field(default_factory=dict)


class AttributeBasedAccess:
    """
    基于属性的访问控制器
    实现ABAC的动态策略评估
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化ABAC控制器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储ABAC策略
        self.policies: Dict[str, ABACPolicy] = {}
        
        # 策略索引
        self.resource_policy_index: Dict[str, List[str]] = {}  # resource_pattern -> [policy_ids]
        
        # 初始化依赖
        self.permission_manager = get_permission_manager()
        self.session_manager = get_session_manager()
        self.audit_logger = AuditLogger()
        
        # 自定义函数注册表
        self.custom_functions: Dict[str, Callable] = {}
        
        # 初始化默认策略
        self._init_default_policies()
        
        logger.info(f"基于属性的访问控制器初始化完成，已加载 {len(self.policies)} 个策略")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "enable_audit": True,
            "policy_evaluation_mode": "first_applicable",  # first_applicable, deny_overrides, allow_overrides
            "enable_caching": True,
            "cache_ttl_seconds": 300,
            "max_policies_per_resource": 100,
            "attribute_resolution_timeout": 5
        }
    
    def _init_default_policies(self):
        """初始化默认策略"""
        # 示例：只有部门匹配的用户才能访问部门文档
        default_policies = [
            ABACPolicy(
                policy_id="dept_doc_access",
                name="部门文档访问控制",
                description="用户只能访问本部门的文档",
                target_resources=["document:dept:*"],
                target_actions=["read", "write"],
                conditions=[
                    AttributeCondition(
                        attribute_type=AttributeType.USER,
                        attribute_name="department",
                        operator=Operator.EQUALS,
                        value="${resource.department}"
                    )
                ],
                effect=AccessDecision.ALLOW,
                priority=10,
                created_by="system"
            ),
            ABACPolicy(
                policy_id="time_based_access",
                name="基于时间的访问控制",
                description="只能在工作时间访问工作相关资源",
                target_resources=["work:*"],
                target_actions=["read", "write", "execute"],
                conditions=[
                    AttributeCondition(
                        attribute_type=AttributeType.ENVIRONMENT,
                        attribute_name="time_of_day",
                        operator=Operator.BETWEEN,
                        value=["09:00", "18:00"]
                    ),
                    AttributeCondition(
                        attribute_type=AttributeType.ENVIRONMENT,
                        attribute_name="day_of_week",
                        operator=Operator.IN,
                        value=[1, 2, 3, 4, 5]  # 周一到周五
                    )
                ],
                effect=AccessDecision.ALLOW,
                priority=5,
                created_by="system"
            ),
            ABACPolicy(
                policy_id="ip_restriction",
                name="IP限制策略",
                description="只能从公司IP范围访问敏感数据",
                target_resources=["sensitive:*"],
                target_actions=["read", "write"],
                conditions=[
                    AttributeCondition(
                        attribute_type=AttributeType.ENVIRONMENT,
                        attribute_name="ip_address",
                        operator=Operator.MATCHES,
                        value=r"^10\.[0-9]+\.[0-9]+\.[0-9]+$"  # 内网IP
                    )
                ],
                effect=AccessDecision.ALLOW,
                priority=15,
                created_by="system"
            )
        ]
        
        for policy in default_policies:
            self.add_policy(policy)
    
    async def evaluate(
        self,
        user_id: str,
        resource: str,
        action: str,
        context: Optional[AttributeContext] = None,
        session_id: Optional[str] = None
    ) -> AccessDecisionResult:
        """
        评估访问请求
        
        Args:
            user_id: 用户ID
            resource: 资源标识
            action: 操作
            context: 属性上下文
            session_id: 会话ID
        
        Returns:
            访问决策结果
        """
        try:
            # 验证会话
            if session_id:
                valid, session = await self.session_manager.validate_session(
                    session_id,
                    update_last_access=True
                )
                if not valid:
                    return AccessDecisionResult(
                        decision=AccessDecision.DENY,
                        reason=f"无效会话: {session_id}",
                        policy="session_validation"
                    )
            
            # 构建完整的属性上下文
            full_context = await self._build_attribute_context(
                user_id, resource, action, context
            )
            
            # 查找适用的策略
            applicable_policies = self._find_applicable_policies(resource, action)
            
            if not applicable_policies:
                # 没有适用策略，根据配置决定
                if self.config.get("deny_by_default", True):
                    return AccessDecisionResult(
                        decision=AccessDecision.DENY,
                        reason="无适用策略，默认拒绝",
                        policy="default_deny"
                    )
                else:
                    return AccessDecisionResult(
                        decision=AccessDecision.ALLOW,
                        reason="无适用策略，默认允许",
                        policy="default_allow"
                    )
            
            # 根据评估模式进行决策
            decision, policy_id, reason = await self._evaluate_policies(
                applicable_policies, full_context
            )
            
            # 记录审计日志
            if self.config["enable_audit"]:
                self.audit_logger.log_event(
                    event_type="ABAC_EVALUATE",
                    user_id=user_id,
                    details={
                        "resource": resource,
                        "action": action,
                        "decision": decision.value,
                        "policy_id": policy_id,
                        "reason": reason
                    },
                    severity="INFO" if decision == AccessDecision.ALLOW else "WARNING"
                )
            
            return AccessDecisionResult(
                decision=decision,
                reason=reason,
                policy=policy_id
            )
            
        except Exception as e:
            logger.error(f"ABAC评估失败: {str(e)}")
            return AccessDecisionResult(
                decision=AccessDecision.DENY,
                reason=f"评估异常: {str(e)}",
                policy="error"
            )
    
    async def _build_attribute_context(
        self,
        user_id: str,
        resource: str,
        action: str,
        provided_context: Optional[AttributeContext]
    ) -> AttributeContext:
        """构建完整的属性上下文"""
        context = provided_context or AttributeContext()
        
        # 获取用户属性（实际应从用户管理模块获取）
        if not context.user_attributes:
            context.user_attributes = await self._get_user_attributes(user_id)
        
        # 获取资源属性
        if not context.resource_attributes:
            context.resource_attributes = await self._get_resource_attributes(resource)
        
        # 设置操作属性
        context.action_attributes["name"] = action
        context.action_attributes["type"] = self._categorize_action(action)
        
        # 获取环境属性
        if not context.environment_attributes:
            context.environment_attributes = self._get_environment_attributes()
        
        return context
    
    async def _get_user_attributes(self, user_id: str) -> Dict[str, Any]:
        """获取用户属性（模拟实现）"""
        # 实际应从用户管理服务获取
        return {
            "id": user_id,
            "department": "engineering",
            "role": "developer",
            "clearance_level": 3,
            "location": "beijing",
            "employment_type": "full_time",
            "years_of_service": 2
        }
    
    async def _get_resource_attributes(self, resource: str) -> Dict[str, Any]:
        """获取资源属性（模拟实现）"""
        # 解析资源标识
        parts = resource.split(':')
        
        attributes = {
            "id": resource,
            "type": parts[0] if parts else "unknown",
            "category": parts[1] if len(parts) > 1 else "general",
            "name": parts[-1] if parts else resource
        }
        
        # 添加一些示例属性
        if attributes["type"] == "document":
            attributes["department"] = "engineering"
            attributes["classification"] = "internal"
            attributes["owner"] = "user123"
        elif attributes["type"] == "sensitive":
            attributes["classification"] = "confidential"
            attributes["requires_approval"] = True
        
        return attributes
    
    def _get_environment_attributes(self) -> Dict[str, Any]:
        """获取环境属性"""
        from datetime import datetime
        
        now = datetime.now()
        
        return {
            "time_of_day": now.strftime("%H:%M"),
            "day_of_week": now.weekday() + 1,  # 1-7
            "day_of_month": now.day,
            "month": now.month,
            "year": now.year,
            "timestamp": time.time(),
            "ip_address": "10.0.0.1",  # 应从请求中获取
            "user_agent": "Mozilla/5.0",  # 应从请求中获取
            "auth_method": "password"  # 应从会话中获取
        }
    
    def _categorize_action(self, action: str) -> str:
        """对操作进行分类"""
        read_actions = ["read", "view", "get", "list", "search"]
        write_actions = ["write", "create", "update", "modify", "edit"]
        delete_actions = ["delete", "remove", "destroy"]
        execute_actions = ["execute", "run", "start", "stop"]
        
        if action in read_actions:
            return "read"
        elif action in write_actions:
            return "write"
        elif action in delete_actions:
            return "delete"
        elif action in execute_actions:
            return "execute"
        else:
            return "other"
    
    def _find_applicable_policies(
        self,
        resource: str,
        action: str
    ) -> List[ABACPolicy]:
        """查找适用的策略"""
        applicable = []
        
        for policy in self.policies.values():
            if not policy.enabled:
                continue
            
            # 检查资源匹配
            resource_match = False
            for pattern in policy.target_resources:
                if self._match_pattern(resource, pattern):
                    resource_match = True
                    break
            
            if not resource_match:
                continue
            
            # 检查操作匹配
            if action not in policy.target_actions and "*" not in policy.target_actions:
                continue
            
            applicable.append(policy)
        
        # 按优先级排序
        applicable.sort(key=lambda p: p.priority, reverse=True)
        
        return applicable
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """模式匹配（支持*通配符）"""
        if pattern == "*":
            return True
        
        # 将通配符模式转换为正则表达式
        regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
        return re.match(f"^{regex_pattern}$", value) is not None
    
    async def _evaluate_policies(
        self,
        policies: List[ABACPolicy],
        context: AttributeContext
    ) -> Tuple[AccessDecision, Optional[str], str]:
        """
        评估策略集
        
        Returns:
            (决策, 策略ID, 原因)
        """
        mode = self.config["policy_evaluation_mode"]
        
        if mode == "first_applicable":
            for policy in policies:
                result = await self._evaluate_policy(policy, context)
                if result is not None:
                    return result, policy.policy_id, f"策略 {policy.name} 适用"
            
            # 没有策略适用
            return AccessDecision.ABSTAIN, None, "无适用策略"
        
        elif mode == "deny_overrides":
            # 只要有一个DENY，就拒绝
            for policy in policies:
                result = await self._evaluate_policy(policy, context)
                if result == AccessDecision.DENY:
                    return AccessDecision.DENY, policy.policy_id, f"被策略 {policy.name} 拒绝"
            
            # 检查是否有ALLOW
            for policy in policies:
                result = await self._evaluate_policy(policy, context)
                if result == AccessDecision.ALLOW:
                    return AccessDecision.ALLOW, policy.policy_id, f"被策略 {policy.name} 允许"
            
            return AccessDecision.ABSTAIN, None, "无决策"
        
        elif mode == "allow_overrides":
            # 只要有一个ALLOW，就允许
            for policy in policies:
                result = await self._evaluate_policy(policy, context)
                if result == AccessDecision.ALLOW:
                    return AccessDecision.ALLOW, policy.policy_id, f"被策略 {policy.name} 允许"
            
            # 检查是否有DENY
            for policy in policies:
                result = await self._evaluate_policy(policy, context)
                if result == AccessDecision.DENY:
                    return AccessDecision.DENY, policy.policy_id, f"被策略 {policy.name} 拒绝"
            
            return AccessDecision.ABSTAIN, None, "无决策"
        
        else:
            # 默认使用first_applicable
            return self._evaluate_policies(policies, context, "first_applicable")
    
    async def _evaluate_policy(
        self,
        policy: ABACPolicy,
        context: AttributeContext
    ) -> Optional[AccessDecision]:
        """评估单个策略"""
        try:
            for condition in policy.conditions:
                if not await self._evaluate_condition(condition, context):
                    return None  # 条件不满足，策略不适用
            
            return policy.effect
            
        except Exception as e:
            logger.error(f"评估策略 {policy.policy_id} 失败: {str(e)}")
            return None
    
    async def _evaluate_condition(
        self,
        condition: AttributeCondition,
        context: AttributeContext
    ) -> bool:
        """评估单个条件"""
        # 获取属性值
        attribute_value = self._get_attribute_value(condition, context)
        if attribute_value is None and condition.operator != Operator.EXISTS:
            return False
        
        # 获取比较值（处理变量替换）
        compare_value = self._resolve_value(condition.value, context)
        
        # 执行比较
        return self._compare(attribute_value, compare_value, condition.operator)
    
    def _get_attribute_value(
        self,
        condition: AttributeCondition,
        context: AttributeContext
    ) -> Any:
        """获取属性值"""
        # 根据属性类型选择上下文
        if condition.attribute_type == AttributeType.USER:
            source = context.user_attributes
        elif condition.attribute_type == AttributeType.RESOURCE:
            source = context.resource_attributes
        elif condition.attribute_type == AttributeType.ACTION:
            source = context.action_attributes
        elif condition.attribute_type == AttributeType.ENVIRONMENT:
            source = context.environment_attributes
        else:
            return None
        
        # 处理嵌套属性
        if condition.attribute_path:
            path_parts = condition.attribute_path.split('.')
            value = source
            for part in path_parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        else:
            return source.get(condition.attribute_name)
    
    def _resolve_value(self, value: Any, context: AttributeContext) -> Any:
        """解析值（处理变量替换）"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            # 变量引用，如 "${resource.department}"
            path = value[2:-1]
            parts = path.split('.')
            
            if parts[0] == "user":
                source = context.user_attributes
            elif parts[0] == "resource":
                source = context.resource_attributes
            elif parts[0] == "action":
                source = context.action_attributes
            elif parts[0] == "environment":
                source = context.environment_attributes
            else:
                return value
            
            # 遍历路径
            current = source
            for part in parts[1:]:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return value
            
            return current
        
        return value
    
    def _compare(self, left: Any, right: Any, operator: Operator) -> bool:
        """执行比较操作"""
        try:
            if operator == Operator.EQUALS:
                return left == right
            elif operator == Operator.NOT_EQUALS:
                return left != right
            elif operator == Operator.GREATER_THAN:
                return left > right
            elif operator == Operator.LESS_THAN:
                return left < right
            elif operator == Operator.GREATER_THAN_OR_EQUALS:
                return left >= right
            elif operator == Operator.LESS_THAN_OR_EQUALS:
                return left <= right
            elif operator == Operator.IN:
                return left in right
            elif operator == Operator.NOT_IN:
                return left not in right
            elif operator == Operator.CONTAINS:
                return right in left
            elif operator == Operator.STARTS_WITH:
                return str(left).startswith(str(right))
            elif operator == Operator.ENDS_WITH:
                return str(left).endswith(str(right))
            elif operator == Operator.MATCHES:
                return re.match(str(right), str(left)) is not None
            elif operator == Operator.BETWEEN:
                return right[0] <= left <= right[1]
            elif operator == Operator.EXISTS:
                return left is not None
            else:
                return False
        except Exception as e:
            logger.error(f"比较操作失败: {str(e)}")
            return False
    
    def add_policy(self, policy: ABACPolicy) -> bool:
        """添加策略"""
        try:
            if policy.policy_id in self.policies:
                logger.warning(f"策略 {policy.policy_id} 已存在，将被覆盖")
            
            policy.updated_at = time.time()
            self.policies[policy.policy_id] = policy
            
            # 更新索引
            for pattern in policy.target_resources:
                if pattern not in self.resource_policy_index:
                    self.resource_policy_index[pattern] = []
                if policy.policy_id not in self.resource_policy_index[pattern]:
                    self.resource_policy_index[pattern].append(policy.policy_id)
            
            logger.info(f"添加策略: {policy.policy_id} - {policy.name}")
            return True
            
        except Exception as e:
            logger.error(f"添加策略失败: {str(e)}")
            return False
    
    def update_policy(self, policy_id: str, **kwargs) -> bool:
        """更新策略"""
        try:
            if policy_id not in self.policies:
                logger.error(f"策略 {policy_id} 不存在")
                return False
            
            policy = self.policies[policy_id]
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            policy.updated_at = time.time()
            
            logger.info(f"更新策略: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新策略失败: {str(e)}")
            return False
    
    def delete_policy(self, policy_id: str) -> bool:
        """删除策略"""
        try:
            if policy_id not in self.policies:
                return False
            
            policy = self.policies[policy_id]
            
            # 从索引中移除
            for pattern in policy.target_resources:
                if pattern in self.resource_policy_index:
                    if policy_id in self.resource_policy_index[pattern]:
                        self.resource_policy_index[pattern].remove(policy_id)
            
            del self.policies[policy_id]
            
            logger.info(f"删除策略: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除策略失败: {str(e)}")
            return False
    
    def get_policy(self, policy_id: str) -> Optional[ABACPolicy]:
        """获取策略"""
        return self.policies.get(policy_id)
    
    def list_policies(
        self,
        resource_pattern: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[ABACPolicy]:
        """列出策略"""
        policies = list(self.policies.values())
        
        if resource_pattern:
            policies = [
                p for p in policies
                if any(self._match_pattern(resource_pattern, pattern) 
                       for pattern in p.target_resources)
            ]
        
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        
        return policies
    
    def register_custom_function(
        self,
        name: str,
        func: Callable
    ) -> None:
        """注册自定义函数"""
        self.custom_functions[name] = func
        logger.info(f"注册自定义函数: {name}")
    
    def validate_policy(self, policy: ABACPolicy) -> Tuple[bool, str]:
        """验证策略的有效性"""
        # 检查必要字段
        if not policy.policy_id:
            return False, "策略ID不能为空"
        
        if not policy.target_resources:
            return False, "至少需要一个目标资源"
        
        if not policy.target_actions:
            return False, "至少需要一个目标操作"
        
        # 检查条件
        for condition in policy.conditions:
            if not isinstance(condition, AttributeCondition):
                return False, "无效的条件格式"
        
        return True, "策略有效"


# 单例实例
_attribute_based_access_instance = None


def get_attribute_based_access() -> AttributeBasedAccess:
    """获取ABAC控制器单例实例"""
    global _attribute_based_access_instance
    if _attribute_based_access_instance is None:
        _attribute_based_access_instance = AttributeBasedAccess()
    return _attribute_based_access_instance

