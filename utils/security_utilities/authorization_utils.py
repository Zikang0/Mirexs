"""
授权工具模块

提供基于角色的访问控制(RBAC)、权限管理、访问控制列表(ACL)等功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import copy


class PermissionType(Enum):
    """权限类型枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(Enum):
    """资源类型枚举"""
    USER = "user"
    FILE = "file"
    DATABASE = "database"
    API = "api"
    SYSTEM = "system"


class AccessEffect(Enum):
    """访问效果枚举"""
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class Permission:
    """权限数据类"""
    name: str
    resource_type: ResourceType
    permission_type: PermissionType
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Role:
    """角色数据类"""
    name: str
    description: str
    permissions: Set[str] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class UserRole:
    """用户角色关联数据类"""
    user_id: str
    role_name: str
    assigned_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    assigned_by: str = ""


@dataclass
class AccessControlEntry:
    """访问控制条目数据类"""
    user_id: str
    resource_id: str
    resource_type: ResourceType
    effect: AccessEffect
    permissions: Set[PermissionType]
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class AuthorizationError(Exception):
    """授权异常"""
    pass


class RoleNotFoundError(Exception):
    """角色不存在异常"""
    pass


class PermissionNotFoundError(Exception):
    """权限不存在异常"""
    pass


class AccessDeniedError(Exception):
    """访问拒绝异常"""
    pass


class RoleManager:
    """角色管理器"""
    
    def __init__(self):
        """初始化角色管理器"""
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self.user_roles: Dict[str, List[UserRole]] = {}
        self.acl: Dict[str, List[AccessControlEntry]] = {}
        
    def create_permission(self, name: str, resource_type: ResourceType, 
                         permission_type: PermissionType, description: str = "") -> Permission:
        """创建权限
        
        Args:
            name: 权限名称
            resource_type: 资源类型
            permission_type: 权限类型
            description: 权限描述
            
        Returns:
            Permission: 创建的权限对象
            
        Raises:
            ValueError: 权限已存在
        """
        if name in self.permissions:
            raise ValueError(f"权限 {name} 已存在")
            
        permission = Permission(
            name=name,
            resource_type=resource_type,
            permission_type=permission_type,
            description=description
        )
        
        self.permissions[name] = permission
        logging.info(f"权限 {name} 创建成功")
        return permission
        
    def get_permission(self, name: str) -> Optional[Permission]:
        """获取权限
        
        Args:
            name: 权限名称
            
        Returns:
            Permission: 权限对象，不存在返回None
        """
        return self.permissions.get(name)
        
    def list_permissions(self, resource_type: Optional[ResourceType] = None) -> List[Permission]:
        """列出权限
        
        Args:
            resource_type: 资源类型过滤
            
        Returns:
            List[Permission]: 权限列表
        """
        permissions = list(self.permissions.values())
        
        if resource_type:
            permissions = [p for p in permissions if p.resource_type == resource_type]
            
        return permissions
        
    def create_role(self, name: str, description: str, 
                   permissions: Optional[List[str]] = None,
                   parent_roles: Optional[List[str]] = None) -> Role:
        """创建角色
        
        Args:
            name: 角色名称
            description: 角色描述
            permissions: 权限列表
            parent_roles: 父角色列表
            
        Returns:
            Role: 创建的角色对象
            
        Raises:
            ValueError: 角色已存在或权限/父角色不存在
        """
        if name in self.roles:
            raise ValueError(f"角色 {name} 已存在")
            
        # 验证权限存在
        if permissions:
            for perm_name in permissions:
                if perm_name not in self.permissions:
                    raise PermissionNotFoundError(f"权限 {perm_name} 不存在")
                    
        # 验证父角色存在
        if parent_roles:
            for role_name in parent_roles:
                if role_name not in self.roles:
                    raise RoleNotFoundError(f"父角色 {role_name} 不存在")
                    
        role = Role(
            name=name,
            description=description,
            permissions=set(permissions or []),
            parent_roles=set(parent_roles or [])
        )
        
        self.roles[name] = role
        logging.info(f"角色 {name} 创建成功")
        return role
        
    def get_role(self, name: str) -> Optional[Role]:
        """获取角色
        
        Args:
            name: 角色名称
            
        Returns:
            Role: 角色对象，不存在返回None
        """
        return self.roles.get(name)
        
    def update_role(self, name: str, description: Optional[str] = None,
                   permissions: Optional[List[str]] = None,
                   parent_roles: Optional[List[str]] = None) -> Role:
        """更新角色
        
        Args:
            name: 角色名称
            description: 角色描述
            permissions: 权限列表
            parent_roles: 父角色列表
            
        Returns:
            Role: 更新后的角色对象
            
        Raises:
            RoleNotFoundError: 角色不存在
            PermissionNotFoundError: 权限不存在
        """
        if name not in self.roles:
            raise RoleNotFoundError(f"角色 {name} 不存在")
            
        role = self.roles[name]
        
        if description is not None:
            role.description = description
            
        if permissions is not None:
            # 验证权限存在
            for perm_name in permissions:
                if perm_name not in self.permissions:
                    raise PermissionNotFoundError(f"权限 {perm_name} 不存在")
            role.permissions = set(permissions)
            
        if parent_roles is not None:
            # 验证父角色存在
            for role_name in parent_roles:
                if role_name not in self.roles:
                    raise RoleNotFoundError(f"父角色 {role_name} 不存在")
            role.parent_roles = set(parent_roles)
            
        logging.info(f"角色 {name} 更新成功")
        return role
        
    def delete_role(self, name: str) -> bool:
        """删除角色
        
        Args:
            name: 角色名称
            
        Returns:
            bool: 删除成功返回True
            
        Raises:
            RoleNotFoundError: 角色不存在
        """
        if name not in self.roles:
            raise RoleNotFoundError(f"角色 {name} 不存在")
            
        # 检查是否有用户使用此角色
        for user_id, roles in self.user_roles.items():
            for user_role in roles:
                if user_role.role_name == name:
                    raise ValueError(f"角色 {name} 正在被用户 {user_id} 使用")
                    
        # 检查是否有其他角色继承此角色
        for role in self.roles.values():
            if name in role.parent_roles:
                raise ValueError(f"角色 {name} 正在被角色 {role.name} 继承")
                
        del self.roles[name]
        logging.info(f"角色 {name} 删除成功")
        return True
        
    def assign_role_to_user(self, user_id: str, role_name: str,
                           expires_at: Optional[datetime] = None,
                           assigned_by: str = "") -> UserRole:
        """为用户分配角色
        
        Args:
            user_id: 用户ID
            role_name: 角色名称
            expires_at: 过期时间
            assigned_by: 分配者
            
        Returns:
            UserRole: 用户角色关联对象
            
        Raises:
            RoleNotFoundError: 角色不存在
        """
        if role_name not in self.roles:
            raise RoleNotFoundError(f"角色 {role_name} 不存在")
            
        user_role = UserRole(
            user_id=user_id,
            role_name=role_name,
            expires_at=expires_at,
            assigned_by=assigned_by
        )
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
            
        self.user_roles[user_id].append(user_role)
        logging.info(f"角色 {role_name} 分配给用户 {user_id}")
        return user_role
        
    def revoke_role_from_user(self, user_id: str, role_name: str) -> bool:
        """撤销用户角色
        
        Args:
            user_id: 用户ID
            role_name: 角色名称
            
        Returns:
            bool: 撤销成功返回True
        """
        if user_id not in self.user_roles:
            return False
            
        roles = self.user_roles[user_id]
        for i, user_role in enumerate(roles):
            if user_role.role_name == role_name:
                del roles[i]
                logging.info(f"撤销用户 {user_id} 的角色 {role_name}")
                return True
                
        return False
        
    def get_user_roles(self, user_id: str) -> List[UserRole]:
        """获取用户角色
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[UserRole]: 用户角色列表
        """
        return self.user_roles.get(user_id, [])
        
    def get_effective_permissions(self, user_id: str) -> Set[str]:
        """获取用户有效权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            Set[str]: 权限名称集合
        """
        permissions = set()
        
        if user_id not in self.user_roles:
            return permissions
            
        for user_role in self.user_roles[user_id]:
            # 检查角色是否过期
            if user_role.expires_at and datetime.now() > user_role.expires_at:
                continue
                
            role = self.roles.get(user_role.role_name)
            if role and role.is_active:
                permissions.update(role.permissions)
                
                # 递归获取父角色权限
                permissions.update(self._get_inherited_permissions(role.name))
                
        return permissions
        
    def _get_inherited_permissions(self, role_name: str) -> Set[str]:
        """获取继承的权限
        
        Args:
            role_name: 角色名称
            
        Returns:
            Set[str]: 继承的权限集合
        """
        permissions = set()
        role = self.roles.get(role_name)
        
        if not role:
            return permissions
            
        for parent_role_name in role.parent_roles:
            parent_role = self.roles.get(parent_role_name)
            if parent_role and parent_role.is_active:
                permissions.update(parent_role.permissions)
                permissions.update(self._get_inherited_permissions(parent_role_name))
                
        return permissions
        
    def has_permission(self, user_id: str, permission_name: str) -> bool:
        """检查用户是否有指定权限
        
        Args:
            user_id: 用户ID
            permission_name: 权限名称
            
        Returns:
            bool: 是否有权限
        """
        effective_permissions = self.get_effective_permissions(user_id)
        return permission_name in effective_permissions
        
    def add_acl_entry(self, user_id: str, resource_id: str, resource_type: ResourceType,
                     effect: AccessEffect, permissions: List[PermissionType],
                     conditions: Optional[Dict[str, Any]] = None) -> AccessControlEntry:
        """添加访问控制条目
        
        Args:
            user_id: 用户ID
            resource_id: 资源ID
            resource_type: 资源类型
            effect: 访问效果
            permissions: 权限列表
            conditions: 条件字典
            
        Returns:
            AccessControlEntry: 创建的ACL条目
        """
        acl_entry = AccessControlEntry(
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            effect=effect,
            permissions=set(permissions),
            conditions=conditions or {}
        )
        
        if resource_id not in self.acl:
            self.acl[resource_id] = []
            
        self.acl[resource_id].append(acl_entry)
        logging.info(f"ACL条目添加成功: 用户 {user_id}, 资源 {resource_id}")
        return acl_entry
        
    def check_access(self, user_id: str, resource_id: str, 
                    resource_type: ResourceType, permission: PermissionType,
                    context: Optional[Dict[str, Any]] = None) -> bool:
        """检查访问权限
        
        Args:
            user_id: 用户ID
            resource_id: 资源ID
            resource_type: 资源类型
            permission: 请求的权限
            context: 上下文信息
            
        Returns:
            bool: 是否允许访问
        """
        context = context or {}
        
        # 首先检查ACL
        if resource_id in self.acl:
            for entry in self.acl[resource_id]:
                if (entry.user_id == user_id and 
                    entry.resource_type == resource_type and
                    permission in entry.permissions):
                    
                    # 检查条件
                    if self._check_conditions(entry.conditions, context):
                        return entry.effect == AccessEffect.ALLOW
                        
        # 如果ACL中没有明确拒绝，则检查角色权限
        effective_permissions = self.get_effective_permissions(user_id)
        
        # 构建权限名称
        permission_name = f"{permission.value}_{resource_type.value}"
        
        # 检查是否有相应权限
        for perm_name in effective_permissions:
            if perm_name == permission_name:
                return True
                
        return False
        
    def _check_conditions(self, conditions: Dict[str, Any], 
                         context: Dict[str, Any]) -> bool:
        """检查条件
        
        Args:
            conditions: 条件字典
            context: 上下文信息
            
        Returns:
            bool: 条件是否满足
        """
        for key, expected_value in conditions.items():
            if key not in context:
                return False
                
            actual_value = context[key]
            
            # 支持多种条件类型
            if isinstance(expected_value, dict):
                # 范围条件
                if 'min' in expected_value and actual_value < expected_value['min']:
                    return False
                if 'max' in expected_value and actual_value > expected_value['max']:
                    return False
                if 'in' in expected_value and actual_value not in expected_value['in']:
                    return False
            else:
                # 精确匹配
                if actual_value != expected_value:
                    return False
                    
        return True
        
    def remove_acl_entry(self, user_id: str, resource_id: str) -> bool:
        """移除访问控制条目
        
        Args:
            user_id: 用户ID
            resource_id: 资源ID
            
        Returns:
            bool: 移除成功返回True
        """
        if resource_id not in self.acl:
            return False
            
        original_count = len(self.acl[resource_id])
        self.acl[resource_id] = [
            entry for entry in self.acl[resource_id] 
            if entry.user_id != user_id
        ]
        
        removed = original_count - len(self.acl[resource_id])
        if removed > 0:
            logging.info(f"移除 {removed} 个ACL条目: 用户 {user_id}, 资源 {resource_id}")
            
        return removed > 0
        
    def get_user_permissions_summary(self, user_id: str) -> Dict[str, Any]:
        """获取用户权限摘要
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 权限摘要信息
        """
        roles = self.get_user_roles(user_id)
        permissions = self.get_effective_permissions(user_id)
        
        return {
            'user_id': user_id,
            'roles': [
                {
                    'role_name': ur.role_name,
                    'assigned_at': ur.assigned_at,
                    'expires_at': ur.expires_at
                }
                for ur in roles
            ],
            'effective_permissions': list(permissions),
            'permission_count': len(permissions)
        }


# 全局角色管理器实例
role_manager = RoleManager()


def create_permission(name: str, resource_type: ResourceType, 
                     permission_type: PermissionType, description: str = "") -> Permission:
    """创建权限便捷函数"""
    return role_manager.create_permission(name, resource_type, permission_type, description)


def create_role(name: str, description: str, 
               permissions: Optional[List[str]] = None,
               parent_roles: Optional[List[str]] = None) -> Role:
    """创建角色便捷函数"""
    return role_manager.create_role(name, description, permissions, parent_roles)


def assign_role_to_user(user_id: str, role_name: str,
                       expires_at: Optional[datetime] = None,
                       assigned_by: str = "") -> UserRole:
    """分配角色给用户便捷函数"""
    return role_manager.assign_role_to_user(user_id, role_name, expires_at, assigned_by)


def has_permission(user_id: str, permission_name: str) -> bool:
    """检查用户权限便捷函数"""
    return role_manager.has_permission(user_id, permission_name)


def check_access(user_id: str, resource_id: str, 
                resource_type: ResourceType, permission: PermissionType,
                context: Optional[Dict[str, Any]] = None) -> bool:
    """检查访问权限便捷函数"""
    return role_manager.check_access(user_id, resource_id, resource_type, permission, context)


def get_user_permissions_summary(user_id: str) -> Dict[str, Any]:
    """获取用户权限摘要便捷函数"""
    return role_manager.get_user_permissions_summary(user_id)


def get_effective_permissions(user_id: str) -> Set[str]:
    """获取用户有效权限便捷函数"""
    return role_manager.get_effective_permissions(user_id)


def get_user_roles(user_id: str) -> List[UserRole]:
    """获取用户角色便捷函数"""
    return role_manager.get_user_roles(user_id)


def add_acl_entry(user_id: str, resource_id: str, resource_type: ResourceType,
                 effect: AccessEffect, permissions: List[PermissionType],
                 conditions: Optional[Dict[str, Any]] = None) -> AccessControlEntry:
    """添加ACL条目便捷函数"""
    return role_manager.add_acl_entry(user_id, resource_id, resource_type, effect, permissions, conditions)


def remove_acl_entry(user_id: str, resource_id: str) -> bool:
    """移除ACL条目便捷函数"""
    return role_manager.remove_acl_entry(user_id, resource_id)


def update_role(name: str, description: Optional[str] = None,
               permissions: Optional[List[str]] = None,
               parent_roles: Optional[List[str]] = None) -> Role:
    """更新角色便捷函数"""
    return role_manager.update_role(name, description, permissions, parent_roles)


def delete_role(name: str) -> bool:
    """删除角色便捷函数"""
    return role_manager.delete_role(name)


def revoke_role_from_user(user_id: str, role_name: str) -> bool:
    """撤销用户角色便捷函数"""
    return role_manager.revoke_role_from_user(user_id, role_name)