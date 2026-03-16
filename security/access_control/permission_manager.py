"""
权限管理模块 - 管理用户权限和角色
提供基于角色的访问控制(RBAC)和基于属性的访问控制(ABAC)的权限管理功能
"""

import asyncio
import logging
import time
import json
import secrets
from typing import Dict, Any, Optional, Set, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger
from ...utils.security_utilities.encryption_utils import EncryptionUtils
from ...config.system import main_config

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举 - 定义系统所有可能的权限"""
    # 系统管理权限
    SYSTEM_CONFIG_READ = "system:config:read"
    SYSTEM_CONFIG_WRITE = "system:config:write"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_MAINTENANCE = "system:maintenance"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"
    SYSTEM_AUDIT_VIEW = "system:audit:view"
    SYSTEM_AUDIT_EXPORT = "system:audit:export"
    
    # 用户管理权限
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    USER_ROLE_ASSIGN = "user:role:assign"
    USER_PERMISSION_GRANT = "user:permission:grant"
    
    # 角色管理权限
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_LIST = "role:list"
    ROLE_PERMISSION_ASSIGN = "role:permission:assign"
    
    # 数据访问权限
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_SHARE = "data:share"
    
    # AI模型权限
    MODEL_LOAD = "model:load"
    MODEL_UNLOAD = "model:unload"
    MODEL_UPDATE = "model:update"
    MODEL_TRAIN = "model:train"
    MODEL_INFERENCE = "model:inference"
    MODEL_EXPORT = "model:export"
    
    # 认知核心权限
    COGNITIVE_TASK_CREATE = "cognitive:task:create"
    COGNITIVE_TASK_READ = "cognitive:task:read"
    COGNITIVE_TASK_UPDATE = "cognitive:task:update"
    COGNITIVE_TASK_DELETE = "cognitive:task:delete"
    COGNITIVE_MEMORY_READ = "cognitive:memory:read"
    COGNITIVE_MEMORY_WRITE = "cognitive:memory:write"
    COGNITIVE_MEMORY_DELETE = "cognitive:memory:delete"
    COGNITIVE_LEARNING_ENABLE = "cognitive:learning:enable"
    COGNITIVE_LEARNING_DISABLE = "cognitive:learning:disable"
    
    # 能力服务权限
    CAPABILITY_CREATE = "capability:create"
    CAPABILITY_READ = "capability:read"
    CAPABILITY_UPDATE = "capability:update"
    CAPABILITY_DELETE = "capability:delete"
    CAPABILITY_EXECUTE = "capability:execute"
    
    # 交互呈现权限
    INTERACTION_3D_RENDER = "interaction:3d:render"
    INTERACTION_SPEECH_IN = "interaction:speech:in"
    INTERACTION_SPEECH_OUT = "interaction:speech:out"
    INTERACTION_VISION_IN = "interaction:vision:in"
    INTERACTION_VISION_OUT = "interaction:vision:out"
    
    # 安全相关权限
    SECURITY_POLICY_READ = "security:policy:read"
    SECURITY_POLICY_WRITE = "security:policy:write"
    SECURITY_THREAT_VIEW = "security:threat:view"
    SECURITY_THREAT_RESPOND = "security:threat:respond"
    SECURITY_ENCRYPTION_MANAGE = "security:encryption:manage"
    SECURITY_AUDIT_VIEW = "security:audit:view"
    SECURITY_AUDIT_MANAGE = "security:audit:manage"
    
    # 应用接口权限
    API_ACCESS = "api:access"
    API_KEY_MANAGE = "api:key:manage"
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_UNINSTALL = "plugin:uninstall"
    PLUGIN_ENABLE = "plugin:enable"
    PLUGIN_DISABLE = "plugin:disable"
    
    # 设备连接权限
    DEVICE_CONNECT = "device:connect"
    DEVICE_DISCONNECT = "device:disconnect"
    DEVICE_CONTROL = "device:control"
    DEVICE_MANAGE = "device:manage"
    
    # 个人数据权限
    PERSONAL_PROFILE_READ = "personal:profile:read"
    PERSONAL_PROFILE_WRITE = "personal:profile:write"
    PERSONAL_HISTORY_READ = "personal:history:read"
    PERSONAL_HISTORY_DELETE = "personal:history:delete"
    PERSONAL_PREFERENCES_READ = "personal:preferences:read"
    PERSONAL_PREFERENCES_WRITE = "personal:preferences:write"
    PERSONAL_DATA_EXPORT = "personal:data:export"
    PERSONAL_DATA_DELETE = "personal:data:delete"


class ResourceType(Enum):
    """资源类型枚举"""
    SYSTEM = "system"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    DATA = "data"
    MODEL = "model"
    TASK = "task"
    MEMORY = "memory"
    CAPABILITY = "capability"
    INTERACTION = "interaction"
    SECURITY = "security"
    API = "api"
    PLUGIN = "plugin"
    DEVICE = "device"
    PERSONAL = "personal"


class AccessType(Enum):
    """访问类型枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LIST = "list"
    ASSIGN = "assign"
    GRANT = "grant"
    REVOKE = "revoke"
    MANAGE = "manage"
    CONTROL = "control"
    CONNECT = "connect"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"


@dataclass
class Role:
    """角色数据模型"""
    role_id: str
    name: str
    description: str
    permissions: Set[str]  # 权限字符串集合
    created_at: float
    updated_at: float
    created_by: str
    is_system_role: bool = False  # 系统内置角色不可删除
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserRole:
    """用户角色分配"""
    user_id: str
    role_id: str
    assigned_at: float
    assigned_by: str
    expires_at: Optional[float] = None  # 角色过期时间
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPermission:
    """用户直接权限（非通过角色）"""
    user_id: str
    permission: str
    granted_at: float
    granted_by: str
    expires_at: Optional[float] = None
    conditions: Optional[Dict[str, Any]] = None  # ABAC条件
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionCheckResult:
    """权限检查结果"""
    granted: bool
    permission: str
    user_id: str
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[str] = None
    reason: Optional[str] = None
    source: Optional[str] = None  # 'role' 或 'direct'
    source_details: Optional[Dict[str, Any]] = None
    check_time: float = field(default_factory=time.time)


class PermissionManager:
    """
    权限管理器 - 管理角色、权限和访问控制
    同时支持RBAC（基于角色的访问控制）和ABAC（基于属性的访问控制）
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化权限管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储角色
        self.roles: Dict[str, Role] = {}
        
        # 存储用户角色分配
        self.user_roles: Dict[str, List[UserRole]] = {}  # user_id -> [UserRole]
        
        # 存储用户直接权限
        self.user_permissions: Dict[str, List[UserPermission]] = {}  # user_id -> [UserPermission]
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/permissions"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        
        # 加载已有数据
        self._load_data()
        
        # 初始化系统角色
        self._init_system_roles()
        
        logger.info(f"权限管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/permissions",
            "enable_abac": True,
            "cache_ttl_seconds": 300,  # 权限检查缓存时间
            "max_roles_per_user": 20,
            "system_roles": {
                "admin": {
                    "name": "系统管理员",
                    "description": "拥有所有系统权限",
                    "permissions": [p.value for p in Permission]
                },
                "security_admin": {
                    "name": "安全管理员",
                    "description": "管理安全相关配置",
                    "permissions": [
                        "security:policy:read", "security:policy:write",
                        "security:threat:view", "security:threat:respond",
                        "security:audit:view", "security:audit:manage",
                        "system:audit:view", "system:audit:export"
                    ]
                },
                "user_manager": {
                    "name": "用户管理员",
                    "description": "管理用户和角色",
                    "permissions": [
                        "user:create", "user:read", "user:update", "user:delete",
                        "user:list", "user:role:assign",
                        "role:create", "role:read", "role:update", "role:delete",
                        "role:list", "role:permission:assign"
                    ]
                },
                "ai_engineer": {
                    "name": "AI工程师",
                    "description": "管理AI模型和认知核心",
                    "permissions": [
                        "model:load", "model:unload", "model:update",
                        "model:train", "model:inference", "model:export",
                        "cognitive:task:create", "cognitive:task:read",
                        "cognitive:learning:enable", "cognitive:learning:disable",
                        "capability:create", "capability:execute"
                    ]
                },
                "data_analyst": {
                    "name": "数据分析师",
                    "description": "访问和分析数据",
                    "permissions": [
                        "data:read", "data:export",
                        "cognitive:memory:read",
                        "system:monitor"
                    ]
                },
                "regular_user": {
                    "name": "普通用户",
                    "description": "常规用户权限",
                    "permissions": [
                        "personal:profile:read", "personal:profile:write",
                        "personal:history:read",
                        "personal:preferences:read", "personal:preferences:write",
                        "personal:data:export", "personal:data:delete",
                        "cognitive:task:create", "cognitive:task:read",
                        "capability:execute",
                        "interaction:3d:render",
                        "interaction:speech:in", "interaction:speech:out",
                        "interaction:vision:in", "interaction:vision:out",
                        "api:access",
                        "device:connect", "device:control"
                    ]
                },
                "guest": {
                    "name": "访客",
                    "description": "最小权限用户",
                    "permissions": [
                        "interaction:speech:in", "interaction:speech:out",
                        "interaction:vision:in", "interaction:vision:out"
                    ]
                }
            }
        }
    
    def _load_data(self) -> None:
        """从存储加载数据"""
        try:
            # 加载角色
            roles_file = self.storage_path / "roles.json"
            if roles_file.exists():
                with open(roles_file, 'r', encoding='utf-8') as f:
                    roles_data = json.load(f)
                    for role_id, role_dict in roles_data.items():
                        role_dict['permissions'] = set(role_dict['permissions'])
                        self.roles[role_id] = Role(**role_dict)
            
            # 加载用户角色分配
            user_roles_file = self.storage_path / "user_roles.json"
            if user_roles_file.exists():
                with open(user_roles_file, 'r', encoding='utf-8') as f:
                    user_roles_data = json.load(f)
                    for user_id, roles_list in user_roles_data.items():
                        self.user_roles[user_id] = [UserRole(**ur) for ur in roles_list]
            
            # 加载用户直接权限
            user_permissions_file = self.storage_path / "user_permissions.json"
            if user_permissions_file.exists():
                with open(user_permissions_file, 'r', encoding='utf-8') as f:
                    user_perms_data = json.load(f)
                    for user_id, perms_list in user_perms_data.items():
                        self.user_permissions[user_id] = [UserPermission(**up) for up in perms_list]
            
            logger.info(f"权限数据加载完成: {len(self.roles)} 个角色, "
                       f"{sum(len(v) for v in self.user_roles.values())} 个角色分配")
        except Exception as e:
            logger.error(f"加载权限数据失败: {str(e)}")
    
    def _save_data(self) -> None:
        """保存数据到存储"""
        try:
            # 保存角色
            roles_data = {}
            for role_id, role in self.roles.items():
                role_dict = role.__dict__.copy()
                role_dict['permissions'] = list(role_dict['permissions'])
                roles_data[role_id] = role_dict
            
            with open(self.storage_path / "roles.json", 'w', encoding='utf-8') as f:
                json.dump(roles_data, f, ensure_ascii=False, indent=2)
            
            # 保存用户角色分配
            user_roles_data = {}
            for user_id, roles_list in self.user_roles.items():
                user_roles_data[user_id] = [ur.__dict__ for ur in roles_list]
            
            with open(self.storage_path / "user_roles.json", 'w', encoding='utf-8') as f:
                json.dump(user_roles_data, f, ensure_ascii=False, indent=2)
            
            # 保存用户直接权限
            user_perms_data = {}
            for user_id, perms_list in self.user_permissions.items():
                user_perms_data[user_id] = [up.__dict__ for up in perms_list]
            
            with open(self.storage_path / "user_permissions.json", 'w', encoding='utf-8') as f:
                json.dump(user_perms_data, f, ensure_ascii=False, indent=2)
            
            logger.debug("权限数据保存完成")
        except Exception as e:
            logger.error(f"保存权限数据失败: {str(e)}")
    
    def _init_system_roles(self) -> None:
        """初始化系统角色"""
        system_roles = self.config["system_roles"]
        
        for role_id, role_config in system_roles.items():
            if role_id not in self.roles:
                role = Role(
                    role_id=role_id,
                    name=role_config["name"],
                    description=role_config["description"],
                    permissions=set(role_config["permissions"]),
                    created_at=time.time(),
                    updated_at=time.time(),
                    created_by="system",
                    is_system_role=True
                )
                self.roles[role_id] = role
                logger.info(f"初始化系统角色: {role_id} - {role.name}")
    
    def create_role(
        self,
        name: str,
        description: str,
        permissions: List[str],
        created_by: str,
        role_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Role]]:
        """
        创建新角色
        
        Args:
            name: 角色名称
            description: 角色描述
            permissions: 权限列表
            created_by: 创建者用户ID
            role_id: 可选的角色ID
        
        Returns:
            (成功标志, 消息, 角色对象)
        """
        try:
            # 检查权限
            for perm in permissions:
                if not self._is_valid_permission(perm):
                    return False, f"无效的权限: {perm}", None
            
            # 生成角色ID
            if role_id is None:
                role_id = f"role_{secrets.token_hex(8)}"
            
            if role_id in self.roles:
                return False, f"角色ID {role_id} 已存在", None
            
            role = Role(
                role_id=role_id,
                name=name,
                description=description,
                permissions=set(permissions),
                created_at=time.time(),
                updated_at=time.time(),
                created_by=created_by,
                is_system_role=False
            )
            
            self.roles[role_id] = role
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="ROLE_CREATE",
                user_id=created_by,
                details={
                    "role_id": role_id,
                    "role_name": name,
                    "permissions_count": len(permissions)
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {created_by} 创建角色: {role_id} - {name}")
            return True, "角色创建成功", role
            
        except Exception as e:
            logger.error(f"创建角色失败: {str(e)}")
            return False, f"创建角色失败: {str(e)}", None
    
    def update_role(
        self,
        role_id: str,
        updated_by: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        更新角色信息
        
        Args:
            role_id: 角色ID
            updated_by: 更新者用户ID
            name: 新名称
            description: 新描述
            permissions: 新权限列表
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if role_id not in self.roles:
                return False, f"角色 {role_id} 不存在"
            
            role = self.roles[role_id]
            
            # 系统角色只能由系统修改
            if role.is_system_role and updated_by != "system":
                return False, "系统角色不能修改"
            
            changes = {}
            
            if name is not None and name != role.name:
                changes["name"] = {"old": role.name, "new": name}
                role.name = name
            
            if description is not None and description != role.description:
                changes["description"] = {"old": role.description, "new": description}
                role.description = description
            
            if permissions is not None:
                # 验证权限
                for perm in permissions:
                    if not self._is_valid_permission(perm):
                        return False, f"无效的权限: {perm}"
                
                old_perms = role.permissions.copy()
                role.permissions = set(permissions)
                changes["permissions"] = {
                    "old": list(old_perms),
                    "new": permissions
                }
            
            if changes:
                role.updated_at = time.time()
                self._save_data()
                
                # 记录审计日志
                self.audit_logger.log_event(
                    event_type="ROLE_UPDATE",
                    user_id=updated_by,
                    details={
                        "role_id": role_id,
                        "changes": changes
                    },
                    severity="INFO"
                )
                
                logger.info(f"用户 {updated_by} 更新角色 {role_id}")
            
            return True, "角色更新成功"
            
        except Exception as e:
            logger.error(f"更新角色失败: {str(e)}")
            return False, f"更新角色失败: {str(e)}"
    
    def delete_role(
        self,
        role_id: str,
        deleted_by: str,
        reassign_role_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        删除角色
        
        Args:
            role_id: 角色ID
            deleted_by: 删除者用户ID
            reassign_role_id: 可选的重新分配角色ID
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if role_id not in self.roles:
                return False, f"角色 {role_id} 不存在"
            
            role = self.roles[role_id]
            
            # 系统角色不能删除
            if role.is_system_role:
                return False, "系统角色不能删除"
            
            # 获取拥有此角色的用户
            affected_users = []
            for user_id, user_roles in self.user_roles.items():
                for ur in user_roles[:]:  # 使用切片复制以避免修改问题
                    if ur.role_id == role_id:
                        affected_users.append(user_id)
                        
                        if reassign_role_id:
                            # 重新分配角色
                            if reassign_role_id not in self.roles:
                                return False, f"重新分配的角色 {reassign_role_id} 不存在"
                            
                            ur.role_id = reassign_role_id
                            ur.metadata["reassigned_from"] = role_id
                            ur.metadata["reassigned_at"] = time.time()
                            ur.metadata["reassigned_by"] = deleted_by
                        else:
                            # 移除角色
                            self.user_roles[user_id].remove(ur)
            
            # 删除角色
            del self.roles[role_id]
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="ROLE_DELETE",
                user_id=deleted_by,
                details={
                    "role_id": role_id,
                    "role_name": role.name,
                    "affected_users": affected_users,
                    "reassign_role": reassign_role_id
                },
                severity="WARNING"
            )
            
            logger.info(f"用户 {deleted_by} 删除角色 {role_id}，影响用户数: {len(affected_users)}")
            return True, "角色删除成功"
            
        except Exception as e:
            logger.error(f"删除角色失败: {str(e)}")
            return False, f"删除角色失败: {str(e)}"
    
    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str,
        expires_in_seconds: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        为用户分配角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            assigned_by: 分配者用户ID
            expires_in_seconds: 过期时间（秒）
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if role_id not in self.roles:
                return False, f"角色 {role_id} 不存在"
            
            # 检查用户角色数量限制
            current_roles = self.user_roles.get(user_id, [])
            if len(current_roles) >= self.config["max_roles_per_user"]:
                return False, f"用户已达到最大角色数量限制 ({self.config['max_roles_per_user']})"
            
            # 检查是否已分配
            for ur in current_roles:
                if ur.role_id == role_id:
                    # 检查是否过期
                    if ur.expires_at and ur.expires_at < time.time():
                        # 过期了，可以重新分配
                        current_roles.remove(ur)
                        break
                    else:
                        return False, "用户已拥有此角色"
            
            expires_at = None
            if expires_in_seconds:
                expires_at = time.time() + expires_in_seconds
            
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_at=time.time(),
                assigned_by=assigned_by,
                expires_at=expires_at
            )
            
            if user_id not in self.user_roles:
                self.user_roles[user_id] = []
            
            self.user_roles[user_id].append(user_role)
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="ROLE_ASSIGN",
                user_id=assigned_by,
                details={
                    "target_user": user_id,
                    "role_id": role_id,
                    "expires_at": expires_at
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {assigned_by} 为用户 {user_id} 分配角色 {role_id}")
            return True, "角色分配成功"
            
        except Exception as e:
            logger.error(f"分配角色失败: {str(e)}")
            return False, f"分配角色失败: {str(e)}"
    
    def remove_role_from_user(
        self,
        user_id: str,
        role_id: str,
        removed_by: str
    ) -> Tuple[bool, str]:
        """
        从用户移除角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            removed_by: 移除者用户ID
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if user_id not in self.user_roles:
                return False, "用户没有角色分配"
            
            removed = False
            for ur in self.user_roles[user_id][:]:
                if ur.role_id == role_id:
                    self.user_roles[user_id].remove(ur)
                    removed = True
                    break
            
            if not removed:
                return False, "用户没有此角色"
            
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="ROLE_REMOVE",
                user_id=removed_by,
                details={
                    "target_user": user_id,
                    "role_id": role_id
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {removed_by} 从用户 {user_id} 移除角色 {role_id}")
            return True, "角色移除成功"
            
        except Exception as e:
            logger.error(f"移除角色失败: {str(e)}")
            return False, f"移除角色失败: {str(e)}"
    
    def grant_permission_to_user(
        self,
        user_id: str,
        permission: str,
        granted_by: str,
        expires_in_seconds: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        直接授予用户权限
        
        Args:
            user_id: 用户ID
            permission: 权限字符串
            granted_by: 授予者用户ID
            expires_in_seconds: 过期时间（秒）
            conditions: ABAC条件
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if not self._is_valid_permission(permission):
                return False, f"无效的权限: {permission}"
            
            expires_at = None
            if expires_in_seconds:
                expires_at = time.time() + expires_in_seconds
            
            user_perm = UserPermission(
                user_id=user_id,
                permission=permission,
                granted_at=time.time(),
                granted_by=granted_by,
                expires_at=expires_at,
                conditions=conditions
            )
            
            if user_id not in self.user_permissions:
                self.user_permissions[user_id] = []
            
            self.user_permissions[user_id].append(user_perm)
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="PERMISSION_GRANT",
                user_id=granted_by,
                details={
                    "target_user": user_id,
                    "permission": permission,
                    "expires_at": expires_at,
                    "conditions": conditions
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {granted_by} 授予用户 {user_id} 权限 {permission}")
            return True, "权限授予成功"
            
        except Exception as e:
            logger.error(f"授予权限失败: {str(e)}")
            return False, f"授予权限失败: {str(e)}"
    
    def revoke_permission_from_user(
        self,
        user_id: str,
        permission: str,
        revoked_by: str
    ) -> Tuple[bool, str]:
        """
        撤销用户的直接权限
        
        Args:
            user_id: 用户ID
            permission: 权限字符串
            revoked_by: 撤销者用户ID
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if user_id not in self.user_permissions:
                return False, "用户没有直接权限"
            
            revoked = False
            for up in self.user_permissions[user_id][:]:
                if up.permission == permission:
                    self.user_permissions[user_id].remove(up)
                    revoked = True
                    break
            
            if not revoked:
                return False, "用户没有此直接权限"
            
            self._save_data()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="PERMISSION_REVOKE",
                user_id=revoked_by,
                details={
                    "target_user": user_id,
                    "permission": permission
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {revoked_by} 撤销用户 {user_id} 的权限 {permission}")
            return True, "权限撤销成功"
            
        except Exception as e:
            logger.error(f"撤销权限失败: {str(e)}")
            return False, f"撤销权限失败: {str(e)}"
    
    def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PermissionCheckResult:
        """
        检查用户是否拥有权限
        
        Args:
            user_id: 用户ID
            permission: 权限字符串
            resource_type: 资源类型（用于ABAC）
            resource_id: 资源ID（用于ABAC）
            context: 上下文信息（用于ABAC）
        
        Returns:
            权限检查结果
        """
        try:
            # 检查直接权限
            direct_result = self._check_direct_permission(
                user_id, permission, resource_type, resource_id, context
            )
            if direct_result.granted:
                return direct_result
            
            # 检查角色权限
            role_result = self._check_role_permission(
                user_id, permission, resource_type, resource_id, context
            )
            if role_result.granted:
                return role_result
            
            # 权限被拒绝
            return PermissionCheckResult(
                granted=False,
                permission=permission,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                reason="用户没有所需权限",
                source=None
            )
            
        except Exception as e:
            logger.error(f"权限检查失败: {str(e)}")
            return PermissionCheckResult(
                granted=False,
                permission=permission,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                reason=f"权限检查异常: {str(e)}"
            )
    
    def _check_direct_permission(
        self,
        user_id: str,
        permission: str,
        resource_type: Optional[ResourceType],
        resource_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> PermissionCheckResult:
        """检查直接权限"""
        if user_id not in self.user_permissions:
            return PermissionCheckResult(
                granted=False,
                permission=permission,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                reason="没有直接权限"
            )
        
        for up in self.user_permissions[user_id]:
            if up.permission == permission:
                # 检查是否过期
                if up.expires_at and up.expires_at < time.time():
                    continue
                
                # 检查ABAC条件
                if up.conditions and self.config["enable_abac"]:
                    if not self._evaluate_conditions(up.conditions, resource_type, resource_id, context):
                        continue
                
                return PermissionCheckResult(
                    granted=True,
                    permission=permission,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    source="direct",
                    source_details={
                        "granted_at": up.granted_at,
                        "granted_by": up.granted_by
                    }
                )
        
        return PermissionCheckResult(
            granted=False,
            permission=permission,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            reason="没有匹配的直接权限"
        )
    
    def _check_role_permission(
        self,
        user_id: str,
        permission: str,
        resource_type: Optional[ResourceType],
        resource_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> PermissionCheckResult:
        """检查角色权限"""
        if user_id not in self.user_roles:
            return PermissionCheckResult(
                granted=False,
                permission=permission,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                reason="没有角色分配"
            )
        
        for ur in self.user_roles[user_id]:
            # 检查角色是否过期
            if ur.expires_at and ur.expires_at < time.time():
                continue
            
            role = self.roles.get(ur.role_id)
            if not role:
                continue
            
            if permission in role.permissions:
                # 检查ABAC条件（角色级别的条件）
                if role.metadata.get("conditions") and self.config["enable_abac"]:
                    if not self._evaluate_conditions(
                        role.metadata["conditions"], resource_type, resource_id, context
                    ):
                        continue
                
                return PermissionCheckResult(
                    granted=True,
                    permission=permission,
                    user_id=user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    source="role",
                    source_details={
                        "role_id": role.role_id,
                        "role_name": role.name,
                        "assigned_at": ur.assigned_at,
                        "assigned_by": ur.assigned_by
                    }
                )
        
        return PermissionCheckResult(
            granted=False,
            permission=permission,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            reason="没有角色拥有此权限"
        )
    
    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        resource_type: Optional[ResourceType],
        resource_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        评估ABAC条件
        
        Args:
            conditions: 条件字典
            resource_type: 资源类型
            resource_id: 资源ID
            context: 上下文
        
        Returns:
            条件是否满足
        """
        if not conditions:
            return True
        
        context = context or {}
        
        for key, value in conditions.items():
            if key == "resource_type":
                if resource_type and resource_type.value != value:
                    return False
            
            elif key == "resource_id_pattern":
                if resource_id and not self._match_pattern(resource_id, value):
                    return False
            
            elif key == "time_range":
                current_time = time.time()
                if "start" in value and current_time < value["start"]:
                    return False
                if "end" in value and current_time > value["end"]:
                    return False
            
            elif key == "ip_range":
                client_ip = context.get("client_ip")
                if client_ip and not self._ip_in_range(client_ip, value):
                    return False
            
            elif key == "location":
                user_location = context.get("location")
                if user_location and user_location != value:
                    return False
            
            elif key == "device_type":
                device_type = context.get("device_type")
                if device_type and device_type != value:
                    return False
            
            elif key == "auth_level":
                auth_level = context.get("auth_level")
                if auth_level and auth_level < value:
                    return False
            
            elif key == "custom":
                # 自定义条件评估
                if not self._evaluate_custom_condition(value, context):
                    return False
        
        return True
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """简单的模式匹配"""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
    
    def _ip_in_range(self, ip: str, ip_range: str) -> bool:
        """检查IP是否在范围内（简化版）"""
        # 实际应用应使用ipaddress模块
        return True
    
    def _evaluate_custom_condition(self, condition: Any, context: Dict[str, Any]) -> bool:
        """评估自定义条件"""
        # 实际应用可根据需要实现自定义条件逻辑
        return True
    
    def _is_valid_permission(self, permission: str) -> bool:
        """检查权限字符串是否有效"""
        # 检查是否在预定义权限中
        for p in Permission:
            if p.value == permission:
                return True
        
        # 检查格式
        parts = permission.split(':')
        if len(parts) < 2:
            return False
        
        # 可以添加更详细的验证
        return True
    
    def get_user_permissions(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> Set[str]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            include_expired: 是否包含已过期的权限
        
        Returns:
            权限集合
        """
        permissions = set()
        
        # 从角色获取
        if user_id in self.user_roles:
            for ur in self.user_roles[user_id]:
                if not include_expired and ur.expires_at and ur.expires_at < time.time():
                    continue
                
                role = self.roles.get(ur.role_id)
                if role:
                    permissions.update(role.permissions)
        
        # 从直接权限获取
        if user_id in self.user_permissions:
            for up in self.user_permissions[user_id]:
                if not include_expired and up.expires_at and up.expires_at < time.time():
                    continue
                permissions.add(up.permission)
        
        return permissions
    
    def get_user_roles(
        self,
        user_id: str,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有角色
        
        Args:
            user_id: 用户ID
            include_expired: 是否包含已过期的角色
        
        Returns:
            角色列表
        """
        result = []
        
        if user_id not in self.user_roles:
            return result
        
        for ur in self.user_roles[user_id]:
            if not include_expired and ur.expires_at and ur.expires_at < time.time():
                continue
            
            role = self.roles.get(ur.role_id)
            if role:
                result.append({
                    "role_id": role.role_id,
                    "name": role.name,
                    "description": role.description,
                    "assigned_at": ur.assigned_at,
                    "assigned_by": ur.assigned_by,
                    "expires_at": ur.expires_at,
                    "is_system_role": role.is_system_role
                })
        
        return result
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """获取所有预定义权限"""
        permissions = []
        for p in Permission:
            permissions.append({
                "name": p.name,
                "value": p.value,
                "category": p.value.split(':')[0] if ':' in p.value else "other"
            })
        return permissions
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """获取所有角色"""
        return [
            {
                "role_id": role.role_id,
                "name": role.name,
                "description": role.description,
                "permissions_count": len(role.permissions),
                "is_system_role": role.is_system_role,
                "created_at": role.created_at,
                "updated_at": role.updated_at,
                "created_by": role.created_by
            }
            for role in self.roles.values()
        ]
    
    def get_role_details(self, role_id: str) -> Optional[Dict[str, Any]]:
        """获取角色详细信息"""
        if role_id not in self.roles:
            return None
        
        role = self.roles[role_id]
        return {
            "role_id": role.role_id,
            "name": role.name,
            "description": role.description,
            "permissions": list(role.permissions),
            "is_system_role": role.is_system_role,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "created_by": role.created_by,
            "metadata": role.metadata
        }
    
    def cleanup_expired_assignments(self) -> int:
        """
        清理已过期的角色分配和权限
        
        Returns:
            清理数量
        """
        cleaned = 0
        current_time = time.time()
        
        # 清理过期角色分配
        for user_id, roles in list(self.user_roles.items()):
            original_count = len(roles)
            self.user_roles[user_id] = [
                ur for ur in roles
                if not ur.expires_at or ur.expires_at >= current_time
            ]
            cleaned += original_count - len(self.user_roles[user_id])
        
        # 清理过期直接权限
        for user_id, perms in list(self.user_permissions.items()):
            original_count = len(perms)
            self.user_permissions[user_id] = [
                up for up in perms
                if not up.expires_at or up.expires_at >= current_time
            ]
            cleaned += original_count - len(self.user_permissions[user_id])
        
        if cleaned > 0:
            self._save_data()
            logger.info(f"清理了 {cleaned} 个过期分配")
        
        return cleaned


# 单例实例
_permission_manager_instance = None


def get_permission_manager() -> PermissionManager:
    """获取权限管理器单例实例"""
    global _permission_manager_instance
    if _permission_manager_instance is None:
        _permission_manager_instance = PermissionManager()
    return _permission_manager_instance

