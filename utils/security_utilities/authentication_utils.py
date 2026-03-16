"""
认证工具模块

提供用户认证、会话管理、密码验证等功能。
"""

import hashlib
import hmac
import jwt
import secrets
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Union
from dataclasses import dataclass
from enum import Enum
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class AuthMethod(Enum):
    """认证方法枚举"""
    PASSWORD = "password"
    TOKEN = "token"
    BIOMETRIC = "biometric"
    MULTI_FACTOR = "multi_factor"
    OAUTH = "oauth"


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class UserCredentials:
    """用户凭据数据类"""
    username: str
    password_hash: str
    salt: str
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None


@dataclass
class SessionInfo:
    """会话信息数据类"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    status: SessionStatus


class AuthenticationError(Exception):
    """认证异常"""
    pass


class PasswordPolicyError(Exception):
    """密码策略异常"""
    pass


class SessionExpiredError(Exception):
    """会话过期异常"""
    pass


class AuthenticationManager:
    """认证管理器"""
    
    def __init__(self, secret_key: str = None):
        """初始化认证管理器
        
        Args:
            secret_key: JWT签名密钥
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.sessions: Dict[str, SessionInfo] = {}
        self.users: Dict[str, UserCredentials] = {}
        self.password_min_length = 8
        self.password_require_uppercase = True
        self.password_require_lowercase = True
        self.password_require_numbers = True
        self.password_require_symbols = True
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.session_timeout = timedelta(hours=24)
        
    def create_user(self, username: str, password: str, **kwargs) -> bool:
        """创建新用户
        
        Args:
            username: 用户名
            password: 密码
            **kwargs: 其他用户属性
            
        Returns:
            bool: 创建成功返回True
            
        Raises:
            PasswordPolicyError: 密码不符合策略
            AuthenticationError: 用户已存在
        """
        if username in self.users:
            raise AuthenticationError(f"用户 {username} 已存在")
            
        if not self.validate_password_policy(password):
            raise PasswordPolicyError("密码不符合安全策略")
            
        salt = secrets.token_hex(32)
        password_hash = self.hash_password(password, salt)
        
        user = UserCredentials(
            username=username,
            password_hash=password_hash,
            salt=salt,
            created_at=datetime.now()
        )
        
        self.users[username] = user
        logging.info(f"用户 {username} 创建成功")
        return True
        
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = "", user_agent: str = "") -> Optional[str]:
        """用户认证
        
        Args:
            username: 用户名
            password: 密码
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            str: 会话令牌，认证失败返回None
            
        Raises:
            AuthenticationError: 认证失败或账户被锁定
        """
        if username not in self.users:
            raise AuthenticationError("用户不存在")
            
        user = self.users[username]
        
        # 检查账户是否被锁定
        if user.locked_until and datetime.now() < user.locked_until:
            raise AuthenticationError("账户被锁定，请稍后再试")
            
        # 验证密码
        if not self.verify_password(password, user.password_hash, user.salt):
            user.failed_attempts += 1
            
            # 检查是否需要锁定账户
            if user.failed_attempts >= self.max_failed_attempts:
                user.locked_until = datetime.now() + self.lockout_duration
                logging.warning(f"用户 {username} 账户被锁定")
                
            raise AuthenticationError("密码错误")
            
        # 重置失败计数
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()
        
        # 创建会话
        session_id = self.create_session(user.username, ip_address, user_agent)
        logging.info(f"用户 {username} 认证成功")
        
        return session_id
        
    def create_session(self, username: str, ip_address: str = "", 
                      user_agent: str = "") -> str:
        """创建用户会话
        
        Args:
            username: 用户名
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            str: 会话ID
        """
        session_id = secrets.token_urlsafe(32)
        
        session = SessionInfo(
            session_id=session_id,
            user_id=username,
            created_at=datetime.now(),
            expires_at=datetime.now() + self.session_timeout,
            ip_address=ip_address,
            user_agent=user_agent,
            status=SessionStatus.ACTIVE
        )
        
        self.sessions[session_id] = session
        return session_id
        
    def validate_session(self, session_id: str) -> Optional[str]:
        """验证会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            str: 用户名，会话无效返回None
            
        Raises:
            SessionExpiredError: 会话已过期
        """
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        
        if session.status != SessionStatus.ACTIVE:
            raise SessionExpiredError("会话状态无效")
            
        if datetime.now() > session.expires_at:
            session.status = SessionStatus.EXPIRED
            raise SessionExpiredError("会话已过期")
            
        return session.user_id
        
    def revoke_session(self, session_id: str) -> bool:
        """撤销会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 撤销成功返回True
        """
        if session_id in self.sessions:
            self.sessions[session_id].status = SessionStatus.REVOKED
            return True
        return False
        
    def revoke_user_sessions(self, username: str) -> int:
        """撤销用户所有会话
        
        Args:
            username: 用户名
            
        Returns:
            int: 撤销的会话数量
        """
        revoked_count = 0
        for session_id, session in self.sessions.items():
            if session.user_id == username:
                session.status = SessionStatus.REVOKED
                revoked_count += 1
        return revoked_count
        
    def hash_password(self, password: str, salt: str) -> str:
        """密码哈希
        
        Args:
            password: 原始密码
            salt: 盐值
            
        Returns:
            str: 哈希后的密码
        """
        return bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8')).decode('utf-8')
        
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """验证密码
        
        Args:
            password: 原始密码
            password_hash: 哈希后的密码
            salt: 盐值
            
        Returns:
            bool: 验证结果
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
            
    def validate_password_policy(self, password: str) -> bool:
        """验证密码策略
        
        Args:
            password: 密码
            
        Returns:
            bool: 是否符合策略
        """
        if len(password) < self.password_min_length:
            return False
            
        if self.password_require_uppercase and not any(c.isupper() for c in password):
            return False
            
        if self.password_require_lowercase and not any(c.islower() for c in password):
            return False
            
        if self.password_require_numbers and not any(c.isdigit() for c in password):
            return False
            
        if self.password_require_symbols and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
            
        return True
        
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """生成JWT令牌
        
        Args:
            user_id: 用户ID
            expires_in: 过期时间（秒）
            
        Returns:
            str: JWT令牌
        """
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
        
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            Dict: 令牌载荷，验证失败返回None
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logging.warning("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError:
            logging.warning("JWT令牌无效")
            return None
            
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码
        
        Args:
            username: 用户名
            old_password: 旧密码
            new_password: 新密码
            
        Returns:
            bool: 修改成功返回True
            
        Raises:
            AuthenticationError: 旧密码错误
            PasswordPolicyError: 新密码不符合策略
        """
        if username not in self.users:
            raise AuthenticationError("用户不存在")
            
        user = self.users[username]
        
        # 验证旧密码
        if not self.verify_password(old_password, user.password_hash, user.salt):
            raise AuthenticationError("旧密码错误")
            
        # 验证新密码策略
        if not self.validate_password_policy(new_password):
            raise PasswordPolicyError("新密码不符合安全策略")
            
        # 生成新的盐值和哈希
        new_salt = secrets.token_hex(32)
        new_hash = self.hash_password(new_password, new_salt)
        
        user.password_hash = new_hash
        user.salt = new_salt
        
        # 撤销所有会话
        self.revoke_user_sessions(username)
        
        logging.info(f"用户 {username} 密码修改成功")
        return True
        
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话
        
        Returns:
            int: 清理的会话数量
        """
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time > session.expires_at:
                session.status = SessionStatus.EXPIRED
                expired_sessions.append(session_id)
                
        return len(expired_sessions)
        
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            Dict: 用户信息字典
        """
        if username not in self.users:
            return None
            
        user = self.users[username]
        return {
            'username': user.username,
            'created_at': user.created_at,
            'last_login': user.last_login,
            'failed_attempts': user.failed_attempts,
            'locked_until': user.locked_until
        }
        
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 会话信息字典
        """
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        return {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'created_at': session.created_at,
            'expires_at': session.expires_at,
            'ip_address': session.ip_address,
            'status': session.status.value
        }


# 全局认证管理器实例
auth_manager = AuthenticationManager()


def authenticate(username: str, password: str, **kwargs) -> Optional[str]:
    """用户认证便捷函数
    
    Args:
        username: 用户名
        password: 密码
        **kwargs: 其他参数
        
    Returns:
        str: 会话令牌
    """
    return auth_manager.authenticate_user(username, password, **kwargs)


def create_user(username: str, password: str, **kwargs) -> bool:
    """创建用户便捷函数
    
    Args:
        username: 用户名
        password: 密码
        **kwargs: 其他参数
        
    Returns:
        bool: 创建成功返回True
    """
    return auth_manager.create_user(username, password, **kwargs)


def validate_session(session_id: str) -> Optional[str]:
    """验证会话便捷函数
    
    Args:
        session_id: 会话ID
        
    Returns:
        str: 用户名
    """
    return auth_manager.validate_session(session_id)


def generate_token(user_id: str, expires_in: int = 3600) -> str:
    """生成令牌便捷函数
    
    Args:
        user_id: 用户ID
        expires_in: 过期时间
        
    Returns:
        str: JWT令牌
    """
    return auth_manager.generate_token(user_id, expires_in)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证令牌便捷函数
    
    Args:
        token: JWT令牌
        
    Returns:
        Dict: 令牌载荷
    """
    return auth_manager.verify_token(token)


def change_password(username: str, old_password: str, new_password: str) -> bool:
    """修改密码便捷函数
    
    Args:
        username: 用户名
        old_password: 旧密码
        new_password: 新密码
        
    Returns:
        bool: 修改成功返回True
    """
    return auth_manager.change_password(username, old_password, new_password)


def revoke_session(session_id: str) -> bool:
    """撤销会话便捷函数
    
    Args:
        session_id: 会话ID
        
    Returns:
        bool: 撤销成功返回True
    """
    return auth_manager.revoke_session(session_id)


def revoke_user_sessions(username: str) -> int:
    """撤销用户会话便捷函数
    
    Args:
        username: 用户名
        
    Returns:
        int: 撤销的会话数量
    """
    return auth_manager.revoke_user_sessions(username)


def validate_password_policy(password: str) -> bool:
    """验证密码策略便捷函数
    
    Args:
        password: 密码
        
    Returns:
        bool: 是否符合策略
    """
    return auth_manager.validate_password_policy(password)


def cleanup_expired_sessions() -> int:
    """清理过期会话便捷函数
    
    Returns:
        int: 清理的会话数量
    """
    return auth_manager.cleanup_expired_sessions()


def get_user_info(username: str) -> Optional[Dict[str, Any]]:
    """获取用户信息便捷函数
    
    Args:
        username: 用户名
        
    Returns:
        Dict: 用户信息
    """
    return auth_manager.get_user_info(username)


def get_session_info(session_id: str) -> Optional[Dict[str, Any]]:
    """获取会话信息便捷函数
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 会话信息
    """
    return auth_manager.get_session_info(session_id)