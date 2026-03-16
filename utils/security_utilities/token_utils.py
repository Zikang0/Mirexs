"""
令牌工具模块

提供JWT、OAuth令牌的生成、验证和管理功能
"""

import jwt
import time
import secrets
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import hashlib
import base64
import json

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TokenType(Enum):
    """令牌类型枚举"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"
    API_KEY = "api_key"
    SESSION = "session"


class TokenAlgorithm(Enum):
    """令牌算法枚举"""
    HS256 = "HS256"
    HS384 = "HS384"
    HS512 = "HS512"
    RS256 = "RS256"
    RS384 = "RS384"
    RS512 = "RS512"
    ES256 = "ES256"
    ES384 = "ES384"
    ES512 = "ES512"


@dataclass
class TokenInfo:
    """令牌信息数据类"""
    token: str
    token_type: TokenType
    user_id: str
    expires_at: datetime
    created_at: datetime
    metadata: Dict[str, Any]
    jti: str  # JWT ID


@dataclass
class TokenPayload:
    """令牌载荷数据类"""
    sub: str  # 主题（用户ID）
    exp: int  # 过期时间
    iat: int  # 签发时间
    jti: str  # JWT ID
    type: str  # 令牌类型
    data: Dict[str, Any]  # 自定义数据


class TokenError(Exception):
    """令牌异常"""
    pass


class TokenExpiredError(Exception):
    """令牌过期异常"""
    pass


class TokenInvalidError(Exception):
    """令牌无效异常"""
    pass


class TokenManager:
    """令牌管理器"""
    
    def __init__(self, secret_key: str, algorithm: TokenAlgorithm = TokenAlgorithm.HS256):
        """初始化令牌管理器
        
        Args:
            secret_key: 签名密钥
            algorithm: 签名算法
        """
        self.secret_key = secret_key
        self.algorithm = algorithm.value
        self.tokens: Dict[str, TokenInfo] = {}
        self.blacklist: Dict[str, datetime] = {}
        self.default_expiry = {
            TokenType.ACCESS: timedelta(minutes=15),
            TokenType.REFRESH: timedelta(days=7),
            TokenType.RESET_PASSWORD: timedelta(hours=1),
            TokenType.EMAIL_VERIFICATION: timedelta(days=1),
            TokenType.API_KEY: timedelta(days=365),
            TokenType.SESSION: timedelta(hours=8)
        }
        
    def generate_token(self, user_id: str, token_type: TokenType = TokenType.ACCESS,
                      expires_in: Optional[timedelta] = None,
                      metadata: Optional[Dict[str, Any]] = None,
                      custom_claims: Optional[Dict[str, Any]] = None) -> TokenInfo:
        """生成令牌
        
        Args:
            user_id: 用户ID
            token_type: 令牌类型
            expires_in: 过期时间
            metadata: 元数据
            custom_claims: 自定义声明
            
        Returns:
            TokenInfo: 令牌信息
            
        Raises:
            TokenError: 令牌生成失败
        """
        try:
            # 设置过期时间
            if expires_in is None:
                expires_in = self.default_expiry.get(token_type, timedelta(minutes=15))
                
            now = datetime.utcnow()
            expires_at = now + expires_in
            
            # 生成JWT ID
            jti = str(uuid.uuid4())
            
            # 构建载荷
            payload = {
                'sub': user_id,
                'exp': int(expires_at.timestamp()),
                'iat': int(now.timestamp()),
                'jti': jti,
                'type': token_type.value,
                'data': metadata or {}
            }
            
            # 添加自定义声明
            if custom_claims:
                payload.update(custom_claims)
                
            # 生成令牌
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # 存储令牌信息
            token_info = TokenInfo(
                token=token,
                token_type=token_type,
                user_id=user_id,
                expires_at=expires_at,
                created_at=now,
                metadata=metadata or {},
                jti=jti
            )
            
            self.tokens[jti] = token_info
            
            logger.info(f"生成令牌: {jti}, 类型: {token_type.value}, 用户: {user_id}")
            return token_info
            
        except Exception as e:
            logger.error(f"生成令牌失败: {e}")
            raise TokenError(f"生成令牌失败: {e}")
            
    def verify_token(self, token: str, token_type: Optional[TokenType] = None,
                    verify_exp: bool = True) -> TokenPayload:
        """验证令牌
        
        Args:
            token: JWT令牌
            token_type: 期望的令牌类型
            verify_exp: 是否验证过期时间
            
        Returns:
            TokenPayload: 令牌载荷
            
        Raises:
            TokenExpiredError: 令牌过期
            TokenInvalidError: 令牌无效
        """
        try:
            # 解码令牌
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': verify_exp}
            )
            
            # 检查是否在黑名单中
            jti = payload.get('jti')
            if jti and jti in self.blacklist:
                raise TokenInvalidError("令牌已被撤销")
                
            # 验证令牌类型
            if token_type:
                token_type_value = payload.get('type')
                if token_type_value != token_type.value:
                    raise TokenInvalidError(f"令牌类型不匹配: 期望 {token_type.value}, 实际 {token_type_value}")
                    
            # 构建载荷对象
            token_payload = TokenPayload(
                sub=payload.get('sub'),
                exp=payload.get('exp'),
                iat=payload.get('iat'),
                jti=payload.get('jti'),
                type=payload.get('type'),
                data=payload.get('data', {})
            )
            
            return token_payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("令牌已过期")
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(f"令牌无效: {e}")
        except Exception as e:
            raise TokenInvalidError(f"验证失败: {e}")
            
    def refresh_token(self, refresh_token: str) -> TokenInfo:
        """刷新访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            TokenInfo: 新的访问令牌
            
        Raises:
            TokenInvalidError: 刷新令牌无效
        """
        try:
            # 验证刷新令牌
            payload = self.verify_token(refresh_token, TokenType.REFRESH)
            
            # 撤销旧刷新令牌
            self.revoke_token(refresh_token)
            
            # 生成新访问令牌
            access_token = self.generate_token(
                user_id=payload.sub,
                token_type=TokenType.ACCESS,
                metadata=payload.data
            )
            
            # 生成新刷新令牌
            new_refresh_token = self.generate_token(
                user_id=payload.sub,
                token_type=TokenType.REFRESH,
                metadata=payload.data
            )
            
            logger.info(f"刷新令牌: 用户 {payload.sub}")
            return access_token, new_refresh_token
            
        except TokenExpiredError:
            raise TokenInvalidError("刷新令牌已过期")
        except Exception as e:
            raise TokenInvalidError(f"刷新失败: {e}")
            
    def revoke_token(self, token: str) -> bool:
        """撤销令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            bool: 是否成功撤销
        """
        try:
            # 解码令牌（不验证过期）
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}
            )
            
            jti = payload.get('jti')
            if jti:
                # 添加到黑名单
                exp = payload.get('exp')
                self.blacklist[jti] = datetime.fromtimestamp(exp)
                
                # 从存储中移除
                if jti in self.tokens:
                    del self.tokens[jti]
                    
                logger.info(f"撤销令牌: {jti}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"撤销令牌失败: {e}")
            return False
            
    def revoke_user_tokens(self, user_id: str) -> int:
        """撤销用户的所有令牌
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 撤销的令牌数量
        """
        revoked_count = 0
        
        for jti, token_info in list(self.tokens.items()):
            if token_info.user_id == user_id:
                self.revoke_token(token_info.token)
                revoked_count += 1
                
        logger.info(f"撤销用户 {user_id} 的所有令牌: {revoked_count} 个")
        return revoked_count
        
    def cleanup_expired_tokens(self) -> int:
        """清理过期令牌
        
        Returns:
            int: 清理的令牌数量
        """
        now = datetime.utcnow()
        cleaned = 0
        
        # 清理黑名单中的过期令牌
        for jti, exp in list(self.blacklist.items()):
            if exp < now:
                del self.blacklist[jti]
                cleaned += 1
                
        # 清理存储中的过期令牌
        for jti, token_info in list(self.tokens.items()):
            if token_info.expires_at < now:
                del self.tokens[jti]
                cleaned += 1
                
        logger.info(f"清理过期令牌: {cleaned} 个")
        return cleaned
        
    def get_token_info(self, token: str) -> Optional[TokenInfo]:
        """获取令牌信息
        
        Args:
            token: JWT令牌
            
        Returns:
            Optional[TokenInfo]: 令牌信息
        """
        try:
            # 解码令牌
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': False}
            )
            
            jti = payload.get('jti')
            if jti and jti in self.tokens:
                return self.tokens[jti]
                
            return None
            
        except Exception:
            return None
            
    def generate_api_key(self) -> str:
        """生成API密钥
        
        Returns:
            str: API密钥
        """
        return secrets.token_urlsafe(32)
        
    def hash_api_key(self, api_key: str) -> str:
        """哈希API密钥
        
        Args:
            api_key: API密钥
            
        Returns:
            str: 哈希值
        """
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((api_key + salt).encode()).hexdigest()
        return f"{salt}${hash_obj}"
        
    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """验证API密钥
        
        Args:
            api_key: API密钥
            hashed_key: 哈希值
            
        Returns:
            bool: 验证结果
        """
        try:
            salt, hash_value = hashed_key.split('$')
            computed_hash = hashlib.sha256((api_key + salt).encode()).hexdigest()
            return secrets.compare_digest(computed_hash, hash_value)
        except Exception:
            return False


class OAuth2TokenManager:
    """OAuth2令牌管理器"""
    
    def __init__(self, token_manager: TokenManager):
        """初始化OAuth2令牌管理器
        
        Args:
            token_manager: 令牌管理器
        """
        self.token_manager = token_manager
        self.auth_codes: Dict[str, Dict[str, Any]] = {}
        self.clients: Dict[str, Dict[str, Any]] = {}
        
    def register_client(self, client_id: str, client_secret: str,
                       redirect_uris: List[str],
                       allowed_grant_types: List[str]) -> bool:
        """注册OAuth2客户端
        
        Args:
            client_id: 客户端ID
            client_secret: 客户端密钥
            redirect_uris: 重定向URI列表
            allowed_grant_types: 允许的授权类型
            
        Returns:
            bool: 注册成功返回True
        """
        if client_id in self.clients:
            return False
            
        self.clients[client_id] = {
            'client_secret': client_secret,
            'redirect_uris': redirect_uris,
            'allowed_grant_types': allowed_grant_types,
            'created_at': datetime.utcnow()
        }
        
        logger.info(f"注册OAuth2客户端: {client_id}")
        return True
        
    def generate_auth_code(self, client_id: str, user_id: str,
                          redirect_uri: str, scope: Optional[str] = None) -> str:
        """生成授权码
        
        Args:
            client_id: 客户端ID
            user_id: 用户ID
            redirect_uri: 重定向URI
            scope: 授权范围
            
        Returns:
            str: 授权码
        """
        auth_code = secrets.token_urlsafe(32)
        
        self.auth_codes[auth_code] = {
            'client_id': client_id,
            'user_id': user_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10)
        }
        
        logger.info(f"生成授权码: {auth_code}, 客户端: {client_id}, 用户: {user_id}")
        return auth_code
        
    def exchange_auth_code(self, auth_code: str, client_id: str,
                          client_secret: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """交换授权码获取令牌
        
        Args:
            auth_code: 授权码
            client_id: 客户端ID
            client_secret: 客户端密钥
            redirect_uri: 重定向URI
            
        Returns:
            Optional[Dict[str, Any]]: 令牌信息
        """
        # 验证客户端
        if client_id not in self.clients:
            logger.warning(f"客户端不存在: {client_id}")
            return None
            
        client = self.clients[client_id]
        if client['client_secret'] != client_secret:
            logger.warning(f"客户端密钥错误: {client_id}")
            return None
            
        # 验证授权码
        if auth_code not in self.auth_codes:
            logger.warning(f"授权码不存在: {auth_code}")
            return None
            
        auth_data = self.auth_codes[auth_code]
        
        # 验证客户端ID
        if auth_data['client_id'] != client_id:
            logger.warning(f"授权码客户端不匹配")
            return None
            
        # 验证重定向URI
        if auth_data['redirect_uri'] != redirect_uri:
            logger.warning(f"重定向URI不匹配")
            return None
            
        # 验证授权码未过期
        if datetime.utcnow() > auth_data['expires_at']:
            logger.warning(f"授权码已过期")
            return None
            
        # 生成访问令牌
        access_token = self.token_manager.generate_token(
            user_id=auth_data['user_id'],
            token_type=TokenType.ACCESS,
            metadata={'scope': auth_data['scope']}
        )
        
        # 生成刷新令牌
        refresh_token = self.token_manager.generate_token(
            user_id=auth_data['user_id'],
            token_type=TokenType.REFRESH,
            metadata={'scope': auth_data['scope']}
        )
        
        # 删除已使用的授权码
        del self.auth_codes[auth_code]
        
        return {
            'access_token': access_token.token,
            'refresh_token': refresh_token.token,
            'token_type': 'Bearer',
            'expires_in': int(access_token.expires_at.timestamp()),
            'scope': auth_data['scope']
        }
        
    def validate_bearer_token(self, auth_header: str) -> Optional[TokenPayload]:
        """验证Bearer令牌
        
        Args:
            auth_header: Authorization头
            
        Returns:
            Optional[TokenPayload]: 令牌载荷
        """
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header[7:]  # 去掉"Bearer "
        
        try:
            return self.token_manager.verify_token(token, TokenType.ACCESS)
        except (TokenExpiredError, TokenInvalidError):
            return None


class RateLimiter:
    """令牌限流器"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """初始化限流器
        
        Args:
            max_requests: 最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = {}
        
    def check_rate_limit(self, key: str) -> bool:
        """检查限流
        
        Args:
            key: 限流键（如用户ID、IP）
            
        Returns:
            bool: 是否允许请求
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # 清理过期记录
        if key in self.requests:
            self.requests[key] = [
                t for t in self.requests[key]
                if t > window_start
            ]
            
        # 检查请求数
        if key not in self.requests:
            self.requests[key] = []
            
        if len(self.requests[key]) >= self.max_requests:
            return False
            
        # 添加新请求
        self.requests[key].append(now)
        return True
        
    def get_remaining_requests(self, key: str) -> int:
        """获取剩余请求数
        
        Args:
            key: 限流键
            
        Returns:
            int: 剩余请求数
        """
        if key not in self.requests:
            return self.max_requests
            
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        active_requests = [t for t in self.requests[key] if t > window_start]
        return max(0, self.max_requests - len(active_requests))
        
    def reset(self, key: Optional[str] = None):
        """重置限流
        
        Args:
            key: 限流键，None表示重置所有
        """
        if key:
            self.requests.pop(key, None)
        else:
            self.requests.clear()


# 便捷函数
def generate_access_token(user_id: str, secret_key: str,
                         expires_in: Optional[timedelta] = None) -> TokenInfo:
    """生成访问令牌"""
    manager = TokenManager(secret_key)
    return manager.generate_token(user_id, TokenType.ACCESS, expires_in)


def verify_access_token(token: str, secret_key: str) -> TokenPayload:
    """验证访问令牌"""
    manager = TokenManager(secret_key)
    return manager.verify_token(token, TokenType.ACCESS)


def generate_refresh_token(user_id: str, secret_key: str,
                          expires_in: Optional[timedelta] = None) -> TokenInfo:
    """生成刷新令牌"""
    manager = TokenManager(secret_key)
    return manager.generate_token(user_id, TokenType.REFRESH, expires_in)


def refresh_tokens(refresh_token: str, secret_key: str) -> Tuple[TokenInfo, TokenInfo]:
    """刷新令牌"""
    manager = TokenManager(secret_key)
    return manager.refresh_token(refresh_token)


def revoke_token(token: str, secret_key: str) -> bool:
    """撤销令牌"""
    manager = TokenManager(secret_key)
    return manager.revoke_token(token)


def generate_api_key() -> str:
    """生成API密钥"""
    manager = TokenManager('dummy')
    return manager.generate_api_key()


def hash_api_key(api_key: str) -> str:
    """哈希API密钥"""
    manager = TokenManager('dummy')
    return manager.hash_api_key(api_key)


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """验证API密钥"""
    manager = TokenManager('dummy')
    return manager.verify_api_key(api_key, hashed_key)