"""
基于角色的访问控制模块
提供RBAC（Role-Based Access Control）的核心实现
"""

import logging
import time
from typing import Dict, Any, Optional, List, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .permission_manager import PermissionManager, Permission, get_permission_manager
from .session_manager import SessionManager, get_session_manager
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class AccessDecision(Enum):
    """访问决策枚举"""
    ALLOW = "allow"  # 允许
    DENY = "deny"  # 拒绝
    ABSTAIN = "abstain"  # 弃权（无法决定）


@dataclass
class AccessRequest:
    """访问请求"""
    user_id: str
    resource: str
    action: str
    session_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessDecisionResult:
    """访问决策结果"""
    decision: AccessDecision
    permission: Optional[str] = None
    reason: Optional[str] = None
    policy: Optional[str] = None
    evaluated_at: float = field(default_factory=time.time)


class RoleBasedAccess:
    """
    基于角色的访问控制器
    实现RBAC的核心决策逻辑
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化RBAC控制器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 初始化依赖
        self.permission_manager = get_permission_manager()
        self.session_manager = get_session_manager()
        self.audit_logger = AuditLogger()
        
        # 角色层次结构（角色继承）
        self.role_hierarchy: Dict[str, List[str]] = self.config.get("role_hierarchy", {})
        
        # 资源权限映射（简化版，实际应从配置或数据库加载）
        self.resource_permissions: Dict[str, List[str]] = self._init_resource_permissions()
        
        logger.info("基于角色的访问控制器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "enable_audit": True,
            "deny_by_default": True,
            "role_hierarchy": {
                "admin": ["security_admin", "user_manager", "data_analyst"],
                "security_admin": [],
                "user_manager": [],
                "data_analyst": [],
                "regular_user": ["guest"],
                "guest": []
            }
        }
    
    def _init_resource_permissions(self) -> Dict[str, List[str]]:
        """初始化资源权限映射"""
        return {
            "user:profile": ["personal:profile:read", "personal:profile:write"],
            "user:preferences": ["personal:preferences:read", "personal:preferences:write"],
            "user:history": ["personal:history:read", "personal:history:delete"],
            "data:documents": ["data:read", "data:write", "data:delete"],
            "system:config": ["system:config:read", "system:config:write"],
            "system:logs": ["system:audit:view"],
            "security:policy": ["security:policy:read", "security:policy:write"],
            "api:keys": ["api:key:manage"],
            "device:control": ["device:connect", "device:control"],
            "model:inference": ["model:inference"],
            "cognitive:memory": ["cognitive:memory:read", "cognitive:memory:write"]
        }
    
    async def check_access(
        self,
        request: AccessRequest
    ) -> AccessDecisionResult:
        """
        检查访问请求
        
        Args:
            request: 访问请求
        
        Returns:
            访问决策结果
        """
        try:
            # 验证会话
            if request.session_id:
                valid, session = await self.session_manager.validate_session(
                    request.session_id,
                    update_last_access=True
                )
                if not valid:
                    return AccessDecisionResult(
                        decision=AccessDecision.DENY,
                        reason=f"无效会话: {request.session_id}",
                        policy="session_validation"
                    )
                
                # 确保用户ID匹配
                if session.user_id != request.user_id:
                    return AccessDecisionResult(
                        decision=AccessDecision.DENY,
                        reason="会话用户不匹配",
                        policy="session_validation"
                    )
            
            # 确定所需权限
            required_permissions = self._get_required_permissions(request.resource, request.action)
            if not required_permissions:
                # 如果没有定义所需权限，根据配置决定
                if self.config["deny_by_default"]:
                    return AccessDecisionResult(
                        decision=AccessDecision.DENY,
                        reason="未定义资源权限，默认拒绝",
                        policy="default_deny"
                    )
                else:
                    return AccessDecisionResult(
                        decision=AccessDecision.ALLOW,
                        reason="未定义资源权限，默认允许",
                        policy="default_allow"
                    )
            
            # 检查每个所需权限
            granted_permissions = []
            denied_permissions = []
            
            for permission in required_permissions:
                result = self.permission_manager.check_permission(
                    user_id=request.user_id,
                    permission=permission,
                    context=request.context
                )
                
                if result.granted:
                    granted_permissions.append(permission)
                else:
                    denied_permissions.append(permission)
            
            # 决策：需要所有权限
            if len(denied_permissions) == 0:
                decision = AccessDecision.ALLOW
                reason = f"所有必要权限已授予: {', '.join(granted_permissions)}"
            else:
                decision = AccessDecision.DENY
                reason = f"缺少权限: {', '.join(denied_permissions[:3])}"
            
            # 记录审计日志
            if self.config["enable_audit"]:
                self.audit_logger.log_event(
                    event_type="RBAC_CHECK",
                    user_id=request.user_id,
                    details={
                        "resource": request.resource,
                        "action": request.action,
                        "decision": decision.value,
                        "required_permissions": required_permissions,
                        "granted_permissions": granted_permissions,
                        "reason": reason
                    },
                    severity="INFO" if decision == AccessDecision.ALLOW else "WARNING"
                )
            
            return AccessDecisionResult(
                decision=decision,
                permission=",".join(granted_permissions) if granted_permissions else None,
                reason=reason,
                policy="rbac"
            )
            
        except Exception as e:
            logger.error(f"访问检查失败: {str(e)}")
            return AccessDecisionResult(
                decision=AccessDecision.DENY,
                reason=f"访问检查异常: {str(e)}",
                policy="error"
            )
    
    def _get_required_permissions(self, resource: str, action: str) -> List[str]:
        """
        获取访问资源所需权限
        
        Args:
            resource: 资源标识
            action: 操作
        
        Returns:
            所需权限列表
        """
        # 从预定义映射获取
        if resource in self.resource_permissions:
            return self.resource_permissions[resource]
        
        # 尝试构建权限字符串
        parts = resource.split(':')
        if len(parts) >= 2:
            category = parts[0]
            sub_resource = parts[1]
            
            # 常见模式：category:sub_resource -> 对应 permission:category:action
            permission = f"{category}:{action}"
            
            # 验证权限是否存在
            if self._is_valid_permission(permission):
                return [permission]
        
        return []
    
    def _is_valid_permission(self, permission: str) -> bool:
        """验证权限是否有效"""
        for p in Permission:
            if p.value == permission:
                return True
        return False
    
    def get_user_effective_permissions(
        self,
        user_id: str
    ) -> Set[str]:
        """
        获取用户的有效权限（考虑角色继承）
        
        Args:
            user_id: 用户ID
        
        Returns:
            权限集合
        """
        # 获取用户的直接权限
        permissions = self.permission_manager.get_user_permissions(user_id)
        
        # 获取用户的所有角色
        user_roles = self.permission_manager.get_user_roles(user_id)
        
        # 扩展角色权限（考虑继承）
        all_roles = set()
        for role_info in user_roles:
            role_id = role_info["role_id"]
            all_roles.add(role_id)
            # 添加继承的角色
            self._get_inherited_roles(role_id, all_roles)
        
        # 从所有角色获取权限
        for role_id in all_roles:
            role_details = self.permission_manager.get_role_details(role_id)
            if role_details and "permissions" in role_details:
                permissions.update(role_details["permissions"])
        
        return permissions
    
    def _get_inherited_roles(
        self,
        role_id: str,
        collected_roles: Set[str]
    ) -> None:
        """
        递归获取继承的角色
        
        Args:
            role_id: 角色ID
            collected_roles: 已收集的角色集合
        """
        if role_id in self.role_hierarchy:
            for inherited_role in self.role_hierarchy[role_id]:
                if inherited_role not in collected_roles:
                    collected_roles.add(inherited_role)
                    self._get_inherited_roles(inherited_role, collected_roles)
    
    def add_role_hierarchy(
        self,
        parent_role: str,
        child_role: str
    ) -> bool:
        """
        添加角色继承关系
        
        Args:
            parent_role: 父角色
            child_role: 子角色
        
        Returns:
            是否成功
        """
        try:
            if parent_role not in self.role_hierarchy:
                self.role_hierarchy[parent_role] = []
            
            if child_role not in self.role_hierarchy[parent_role]:
                self.role_hierarchy[parent_role].append(child_role)
                logger.info(f"添加角色继承: {parent_role} -> {child_role}")
            
            return True
        except Exception as e:
            logger.error(f"添加角色继承失败: {str(e)}")
            return False
    
    def remove_role_hierarchy(
        self,
        parent_role: str,
        child_role: str
    ) -> bool:
        """
        移除角色继承关系
        
        Args:
            parent_role: 父角色
            child_role: 子角色
        
        Returns:
            是否成功
        """
        try:
            if parent_role in self.role_hierarchy:
                if child_role in self.role_hierarchy[parent_role]:
                    self.role_hierarchy[parent_role].remove(child_role)
                    logger.info(f"移除角色继承: {parent_role} -> {child_role}")
                    return True
            return False
        except Exception as e:
            logger.error(f"移除角色继承失败: {str(e)}")
            return False
    
    def get_role_hierarchy(self) -> Dict[str, List[str]]:
        """获取角色继承层次"""
        return self.role_hierarchy.copy()


# 单例实例
_role_based_access_instance = None


def get_role_based_access() -> RoleBasedAccess:
    """获取RBAC控制器单例实例"""
    global _role_based_access_instance
    if _role_based_access_instance is None:
        _role_based_access_instance = RoleBasedAccess()
    return _role_based_access_instance

