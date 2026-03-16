"""
API认证器模块 - Mirexs API网关

提供API身份认证功能，包括：
1. API密钥认证
2. JWT认证
3. OAuth2认证
4. 基本认证
5. 多因素认证
6. 角色权限控制
"""

import logging
import time
import json
import hashlib
import hmac
import base64
import jwt
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

# 尝试导入OAuth库
try:
    from authlib.integrations.requests_client import OAuth2Session
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    logger.warning("Authlib not available. OAuth2 functionality will be limited.")

class AuthMethod(Enum):
    """认证方法枚举"""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    JWT = "jwt"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    MFA = "mfa"
    CUSTOM = "custom"

class TokenType(Enum):
    """令牌类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    TEMPORARY = "temporary"

class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

@dataclass
class AuthToken:
    """认证令牌"""
    id: str
    token: str
    type: TokenType
    user_id: str
    permissions: List[str]
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APIKey:
    """API密钥"""
    id: str
    key: str
    name: str
    user_id: str
    permissions: List[str]
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    rate_limit: Optional[int] = None
    allowed_ips: List[str] = field(default_factory=list)

@dataclass
class User:
    """用户"""
    id: str
    username: str
    email: str
    password_hash: str
    permissions: List[str]
    roles: List[str] = field(default_factory=list)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None

@dataclass
class AuthenticatorConfig:
    """认证器配置"""
    # JWT配置
    jwt_secret: str = "mirexs-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    
    # API密钥配置
    api_key_header: str = "X-API-Key"
    api_key_expire_days: Optional[int] = 90
    
    # 密码配置
    password_min_length: int = 8
    password_hash_rounds: int = 12
    
    # 会话配置
    session_timeout: int = 3600  # 秒
    
    # MFA配置
    mfa_issuer: str = "Mirexs"

class APIAuthenticator:
    """
    API认证器
    
    负责API的身份认证和授权。
    """
    
    def __init__(self, config: Optional[AuthenticatorConfig] = None):
        """
        初始化API认证器
        
        Args:
            config: 认证器配置
        """
        self.config = config or AuthenticatorConfig()
        
        # 存储
        self.users: Dict[str, User] = {}
        self.api_keys: Dict[str, APIKey] = {}
        self.tokens: Dict[str, AuthToken] = {}
        
        # 用户名索引
        self.username_index: Dict[str, str] = {}  # username -> user_id
        
        # 回调函数
        self.on_authenticated: Optional[Callable[[str], None]] = None
        self.on_authorized: Optional[Callable[[str, str], None]] = None
        self.on_token_created: Optional[Callable[[AuthToken], None]] = None
        self.on_token_revoked: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "authentications": 0,
            "authorizations": 0,
            "tokens_issued": 0,
            "tokens_revoked": 0,
            "failed_attempts": 0
        }
        
        # 添加默认用户
        self._add_default_user()
        
        logger.info("APIAuthenticator initialized")
    
    def _add_default_user(self):
        """添加默认用户"""
        admin_user = User(
            id="admin",
            username="admin",
            email="admin@mirexs.com",
            password_hash=self._hash_password("admin123"),
            permissions=[p.value for p in Permission],
            roles=["admin"]
        )
        self.users[admin_user.id] = admin_user
        self.username_index[admin_user.username] = admin_user.id
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        import bcrypt
        salt = bcrypt.gensalt(rounds=self.config.password_hash_rounds)
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def _verify_password(self, password: str, hash_str: str) -> bool:
        """验证密码"""
        import bcrypt
        return bcrypt.checkpw(password.encode(), hash_str.encode())
    
    def _generate_token(self, user_id: str, token_type: TokenType,
                       permissions: List[str], expires_in: Optional[int] = None) -> str:
        """生成令牌"""
        if token_type == TokenType.JWT:
            payload = {
                "user_id": user_id,
                "type": token_type.value,
                "permissions": permissions,
                "iat": time.time(),
                "exp": time.time() + (expires_in or self.config.jwt_expire_minutes * 60)
            }
            return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
        else:
            return str(uuid.uuid4())
    
    def _generate_api_key(self) -> str:
        """生成API密钥"""
        return f"mk_{uuid.uuid4().hex[:24]}"
    
    def authenticate(self, method: AuthMethod, credentials: Dict[str, Any]) -> Optional[AuthToken]:
        """
        认证用户
        
        Args:
            method: 认证方法
            credentials: 凭证信息
        
        Returns:
            认证令牌
        """
        self.stats["authentications"] += 1
        
        try:
            if method == AuthMethod.API_KEY:
                return self._authenticate_api_key(credentials)
            elif method == AuthMethod.BASIC:
                return self._authenticate_basic(credentials)
            elif method == AuthMethod.JWT:
                return self._authenticate_jwt(credentials)
            elif method == AuthMethod.BEARER_TOKEN:
                return self._authenticate_bearer(credentials)
            else:
                logger.warning(f"Unsupported auth method: {method.value}")
                return None
                
        except Exception as e:
            self.stats["failed_attempts"] += 1
            logger.error(f"Authentication error: {e}")
            
            if self.on_error:
                self.on_error(str(e))
            
            return None
    
    def _authenticate_api_key(self, credentials: Dict[str, Any]) -> Optional[AuthToken]:
        """API密钥认证"""
        api_key = credentials.get("api_key")
        
        if not api_key:
            return None
        
        # 查找API密钥
        for key_id, key_obj in self.api_keys.items():
            if key_obj.key == api_key:
                # 检查过期
                if key_obj.expires_at and key_obj.expires_at < time.time():
                    logger.warning(f"API key expired: {key_id}")
                    return None
                
                # 更新最后使用时间
                key_obj.last_used = time.time()
                
                # 创建临时令牌
                token = AuthToken(
                    id=str(uuid.uuid4()),
                    token=str(uuid.uuid4()),
                    type=TokenType.ACCESS,
                    user_id=key_obj.user_id,
                    permissions=key_obj.permissions,
                    expires_at=time.time() + 3600  # 1小时
                )
                
                self.tokens[token.id] = token
                self.stats["tokens_issued"] += 1
                
                if self.on_authenticated:
                    self.on_authenticated(key_obj.user_id)
                
                if self.on_token_created:
                    self.on_token_created(token)
                
                return token
        
        return None
    
    def _authenticate_basic(self, credentials: Dict[str, Any]) -> Optional[AuthToken]:
        """基本认证"""
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            return None
        
        # 查找用户
        user_id = self.username_index.get(username)
        if not user_id or user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        # 验证密码
        if not self._verify_password(password, user.password_hash):
            return None
        
        # 更新最后登录
        user.last_login = time.time()
        
        # 创建令牌
        token = AuthToken(
            id=str(uuid.uuid4()),
            token=self._generate_token(user.id, TokenType.JWT, user.permissions),
            type=TokenType.JWT,
            user_id=user.id,
            permissions=user.permissions,
            expires_at=time.time() + self.config.jwt_expire_minutes * 60
        )
        
        self.tokens[token.id] = token
        self.stats["tokens_issued"] += 1
        
        if self.on_authenticated:
            self.on_authenticated(user.id)
        
        if self.on_token_created:
            self.on_token_created(token)
        
        return token
    
    def _authenticate_jwt(self, credentials: Dict[str, Any]) -> Optional[AuthToken]:
        """JWT认证"""
        token_str = credentials.get("token")
        
        if not token_str:
            return None
        
        try:
            # 解码JWT
            payload = jwt.decode(
                token_str,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            
            user_id = payload.get("user_id")
            if not user_id or user_id not in self.users:
                return None
            
            # 创建会话令牌
            token = AuthToken(
                id=str(uuid.uuid4()),
                token=token_str,
                type=TokenType.ACCESS,
                user_id=user_id,
                permissions=payload.get("permissions", []),
                expires_at=payload.get("exp")
            )
            
            self.tokens[token.id] = token
            
            if self.on_authenticated:
                self.on_authenticated(user_id)
            
            return token
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
        
        return None
    
    def _authenticate_bearer(self, credentials: Dict[str, Any]) -> Optional[AuthToken]:
        """Bearer令牌认证"""
        token_str = credentials.get("token")
        
        if not token_str:
            return None
        
        # 查找令牌
        for token in self.tokens.values():
            if token.token == token_str:
                # 检查过期
                if token.expires_at and token.expires_at < time.time():
                    logger.warning(f"Token expired: {token.id}")
                    return None
                
                token.last_used = time.time()
                
                if self.on_authenticated:
                    self.on_authenticated(token.user_id)
                
                return token
        
        return None
    
    def authorize(self, user_id: str, required_permissions: List[str],
                  resource: Optional[str] = None) -> bool:
        """
        授权检查
        
        Args:
            user_id: 用户ID
            required_permissions: 所需权限
            resource: 资源
        
        Returns:
            是否授权
        """
        self.stats["authorizations"] += 1
        
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        # 检查权限
        for perm in required_permissions:
            if perm not in user.permissions:
                return False
        
        if self.on_authorized:
            self.on_authorized(user_id, resource or "unknown")
        
        return True
    
    def create_api_key(self, user_id: str, name: str,
                      permissions: List[str],
                      expires_in_days: Optional[int] = None) -> APIKey:
        """
        创建API密钥
        
        Args:
            user_id: 用户ID
            name: 密钥名称
            permissions: 权限列表
            expires_in_days: 过期天数
        
        Returns:
            API密钥
        """
        key_id = str(uuid.uuid4())
        
        expires_at = None
        if expires_in_days or self.config.api_key_expire_days:
            days = expires_in_days or self.config.api_key_expire_days
            expires_at = time.time() + days * 86400
        
        api_key = APIKey(
            id=key_id,
            key=self._generate_api_key(),
            name=name,
            user_id=user_id,
            permissions=permissions,
            expires_at=expires_at
        )
        
        self.api_keys[key_id] = api_key
        
        logger.info(f"API key created for user {user_id}: {name}")
        
        return api_key
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        吊销API密钥
        
        Args:
            key_id: 密钥ID
        
        Returns:
            是否成功
        """
        if key_id in self.api_keys:
            del self.api_keys[key_id]
            self.stats["tokens_revoked"] += 1
            
            if self.on_token_revoked:
                self.on_token_revoked(key_id)
            
            logger.info(f"API key revoked: {key_id}")
            return True
        
        return False
    
    def create_user(self, username: str, email: str, password: str,
                   permissions: Optional[List[str]] = None,
                   roles: Optional[List[str]] = None) -> User:
        """
        创建用户
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            permissions: 权限列表
            roles: 角色列表
        
        Returns:
            用户
        """
        if username in self.username_index:
            raise ValueError(f"Username already exists: {username}")
        
        user_id = str(uuid.uuid4())
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            permissions=permissions or [Permission.READ.value],
            roles=roles or ["user"]
        )
        
        self.users[user_id] = user
        self.username_index[username] = user_id
        
        logger.info(f"User created: {username}")
        
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        user_id = self.username_index.get(username)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def get_api_keys(self, user_id: str) -> List[APIKey]:
        """获取用户的API密钥"""
        return [k for k in self.api_keys.values() if k.user_id == user_id]
    
    def validate_token(self, token_str: str) -> Optional[AuthToken]:
        """验证令牌"""
        for token in self.tokens.values():
            if token.token == token_str:
                if token.expires_at and token.expires_at < time.time():
                    return None
                return token
        return None
    
    def refresh_token(self, refresh_token: str) -> Optional[AuthToken]:
        """刷新令牌"""
        # 查找刷新令牌
        for token in self.tokens.values():
            if token.token == refresh_token and token.type == TokenType.REFRESH:
                if token.expires_at and token.expires_at < time.time():
                    return None
                
                # 创建新的访问令牌
                new_token = AuthToken(
                    id=str(uuid.uuid4()),
                    token=self._generate_token(token.user_id, TokenType.ACCESS, token.permissions),
                    type=TokenType.ACCESS,
                    user_id=token.user_id,
                    permissions=token.permissions,
                    expires_at=time.time() + self.config.jwt_expire_minutes * 60
                )
                
                self.tokens[new_token.id] = new_token
                self.stats["tokens_issued"] += 1
                
                return new_token
        
        return None
    
    def revoke_token(self, token_id: str) -> bool:
        """
        吊销令牌
        
        Args:
            token_id: 令牌ID
        
        Returns:
            是否成功
        """
        if token_id in self.tokens:
            del self.tokens[token_id]
            self.stats["tokens_revoked"] += 1
            
            if self.on_token_revoked:
                self.on_token_revoked(token_id)
            
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取认证器状态
        
        Returns:
            状态字典
        """
        return {
            "users": {
                "total": len(self.users),
                "active": len([u for u in self.users.values() if u.last_login])
            },
            "api_keys": {
                "total": len(self.api_keys),
                "active": len([k for k in self.api_keys.values() if not k.expires_at or k.expires_at > time.time()])
            },
            "tokens": {
                "total": len(self.tokens),
                "active": len([t for t in self.tokens.values() if not t.expires_at or t.expires_at > time.time()])
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭认证器"""
        logger.info("Shutting down APIAuthenticator...")
        
        self.users.clear()
        self.api_keys.clear()
        self.tokens.clear()
        self.username_index.clear()
        
        logger.info("APIAuthenticator shutdown completed")

# 单例模式实现
_api_authenticator_instance: Optional[APIAuthenticator] = None

def get_api_authenticator(config: Optional[AuthenticatorConfig] = None) -> APIAuthenticator:
    """
    获取API认证器单例
    
    Args:
        config: 认证器配置
    
    Returns:
        API认证器实例
    """
    global _api_authenticator_instance
    if _api_authenticator_instance is None:
        _api_authenticator_instance = APIAuthenticator(config)
    return _api_authenticator_instance

