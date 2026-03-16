"""
身份验证器模块 - 验证用户身份
提供统一的身份验证接口，整合多种验证方式
"""

import asyncio
import logging
import time
import hashlib
import hmac
import secrets
from typing import Dict, Any, Optional, Tuple, List, Union
from enum import Enum
from dataclasses import dataclass, field

from .biometric_auth import BiometricAuth, BiometricAuthLevel, BiometricType
from .multi_factor_auth import MultiFactorAuth, AuthResult
from .session_manager import SessionManager
from ..security_monitoring.audit_logger import AuditLogger
from ...utils.security_utilities.token_utils import TokenUtils

logger = logging.getLogger(__name__)


class VerificationMethod(Enum):
    """验证方法枚举"""
    PASSWORD = "password"  # 密码验证
    BIOMETRIC_VOICE = "biometric_voice"  # 声纹验证
    BIOMETRIC_FACE = "biometric_face"  # 面部验证
    BIOMETRIC_BEHAVIOR = "biometric_behavior"  # 行为验证
    MFA = "mfa"  # 多因素验证
    TOKEN = "token"  # 令牌验证
    API_KEY = "api_key"  # API密钥验证
    CERTIFICATE = "certificate"  # 证书验证


class VerificationLevel(Enum):
    """验证级别枚举"""
    LOW = 1  # 低安全级别，用于非敏感操作
    MEDIUM = 2  # 中安全级别，用于常规操作
    HIGH = 3  # 高安全级别，用于敏感操作
    CRITICAL = 4  # 关键级别，用于最高权限操作


@dataclass
class VerificationRequest:
    """验证请求"""
    user_id: str
    method: VerificationMethod
    level: VerificationLevel
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: secrets.token_hex(16))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """验证结果"""
    success: bool
    user_id: Optional[str]
    method: VerificationMethod
    level: VerificationLevel
    confidence: float  # 置信度 (0-1)
    verified_at: float
    request_id: str
    session_id: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[float] = None
    failure_reason: Optional[str] = None
    remaining_attempts: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IdentityVerifier:
    """
    身份验证器 - 统一的身份验证入口
    整合密码、生物特征、多因素等多种验证方式
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化身份验证器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 初始化依赖组件
        self.biometric_auth = BiometricAuth()
        self.multi_factor_auth = MultiFactorAuth()
        self.session_manager = SessionManager()
        self.audit_logger = AuditLogger()
        self.token_utils = TokenUtils()
        
        # 验证尝试记录（用于防暴力破解）
        self.attempt_records: Dict[str, List[float]] = {}  # user_id -> [attempt_timestamps]
        
        # API密钥存储（简化版，实际应使用数据库）
        self.api_keys: Dict[str, Dict[str, Any]] = {}  # api_key -> {user_id, permissions, expires_at}
        
        logger.info("身份验证器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "max_attempts_per_minute": 10,  # 每分钟最大尝试次数
            "lockout_duration_seconds": 300,  # 锁定持续时间
            "session_duration_seconds": 3600,  # 会话持续时间
            "verification_timeout_seconds": 30,  # 验证超时时间
            "confidence_thresholds": {
                "low": 0.6,
                "medium": 0.75,
                "high": 0.85,
                "critical": 0.95
            },
            "method_weights": {
                "password": 0.5,
                "biometric_voice": 0.7,
                "biometric_face": 0.8,
                "biometric_behavior": 0.6,
                "mfa": 0.9,
                "token": 0.8,
                "api_key": 0.7,
                "certificate": 0.9
            }
        }
    
    async def verify_identity(
        self,
        request: VerificationRequest
    ) -> VerificationResult:
        """
        验证用户身份
        
        Args:
            request: 验证请求
        
        Returns:
            验证结果
        """
        try:
            # 检查尝试频率
            if not self._check_attempt_rate(request.user_id):
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="尝试次数过多，请稍后再试",
                    remaining_attempts=0
                )
            
            # 记录尝试
            self._record_attempt(request.user_id)
            
            # 根据验证方法执行验证
            result = None
            
            if request.method == VerificationMethod.PASSWORD:
                result = await self._verify_password(request)
            elif request.method == VerificationMethod.BIOMETRIC_VOICE:
                result = await self._verify_biometric_voice(request)
            elif request.method == VerificationMethod.BIOMETRIC_FACE:
                result = await self._verify_biometric_face(request)
            elif request.method == VerificationMethod.BIOMETRIC_BEHAVIOR:
                result = await self._verify_biometric_behavior(request)
            elif request.method == VerificationMethod.MFA:
                result = await self._verify_mfa(request)
            elif request.method == VerificationMethod.TOKEN:
                result = await self._verify_token(request)
            elif request.method == VerificationMethod.API_KEY:
                result = await self._verify_api_key(request)
            else:
                result = VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason=f"不支持的验证方法: {request.method.value}"
                )
            
            # 验证成功，创建会话
            if result and result.success:
                session_result = await self.session_manager.create_session(
                    user_id=result.user_id,
                    auth_method=request.method.value,
                    metadata={
                        "verification_id": request.request_id,
                        "confidence": result.confidence,
                        "level": request.level.value
                    }
                )
                
                if session_result:
                    result.session_id = session_result.session_id
                    result.token = session_result.token
                    result.expires_at = session_result.expires_at
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="IDENTITY_VERIFICATION",
                user_id=request.user_id,
                details={
                    "request_id": request.request_id,
                    "method": request.method.value,
                    "level": request.level.value,
                    "success": result.success if result else False,
                    "confidence": result.confidence if result else 0,
                    "failure_reason": result.failure_reason if result else "Unknown error"
                },
                severity="INFO" if (result and result.success) else "WARNING"
            )
            
            return result or VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason="验证处理失败"
            )
            
        except Exception as e:
            logger.error(f"身份验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"验证异常: {str(e)}"
            )
    
    async def _verify_password(self, request: VerificationRequest) -> VerificationResult:
        """密码验证"""
        try:
            # 这里应该调用用户管理模块验证密码
            # 简化实现，假设密码正确
            password = request.data.get("password")
            stored_hash = self._get_stored_password_hash(request.user_id)
            
            if not stored_hash:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="用户未设置密码"
                )
            
            # 验证密码
            input_hash = self._hash_password(password)
            if not hmac.compare_digest(input_hash, stored_hash):
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="密码错误"
                )
            
            # 计算置信度
            confidence = self.config["method_weights"]["password"]
            
            return VerificationResult(
                success=True,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=confidence,
                verified_at=time.time(),
                request_id=request.request_id
            )
            
        except Exception as e:
            logger.error(f"密码验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"密码验证异常: {str(e)}"
            )
    
    async def _verify_biometric_voice(self, request: VerificationRequest) -> VerificationResult:
        """声纹验证"""
        try:
            audio = request.data.get("audio")
            if audio is None:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少音频数据"
                )
            
            # 映射验证级别
            auth_level = self._map_verification_level(request.level)
            
            result = await self.biometric_auth.verify_voiceprint(
                user_id=request.user_id,
                audio_samples=audio,
                sample_rate=request.data.get("sample_rate", 16000),
                auth_level=auth_level,
                require_liveness=request.level.value >= 3  # HIGH及以上需要活体检测
            )
            
            return VerificationResult(
                success=result.success,
                user_id=request.user_id if result.success else None,
                method=request.method,
                level=request.level,
                confidence=result.confidence_score,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=result.failure_reason,
                metadata={"match_score": result.match_score}
            )
            
        except Exception as e:
            logger.error(f"声纹验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"声纹验证异常: {str(e)}"
            )
    
    async def _verify_biometric_face(self, request: VerificationRequest) -> VerificationResult:
        """面部验证"""
        try:
            image = request.data.get("image")
            if image is None:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少图像数据"
                )
            
            auth_level = self._map_verification_level(request.level)
            
            result = await self.biometric_auth.verify_facial(
                user_id=request.user_id,
                face_image=image,
                auth_level=auth_level,
                require_liveness=request.level.value >= 3
            )
            
            return VerificationResult(
                success=result.success,
                user_id=request.user_id if result.success else None,
                method=request.method,
                level=request.level,
                confidence=result.confidence_score,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=result.failure_reason,
                metadata={"match_score": result.match_score}
            )
            
        except Exception as e:
            logger.error(f"面部验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"面部验证异常: {str(e)}"
            )
    
    async def _verify_biometric_behavior(self, request: VerificationRequest) -> VerificationResult:
        """行为验证"""
        try:
            behavior_data = request.data.get("behavior_data")
            if behavior_data is None:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少行为数据"
                )
            
            auth_level = self._map_verification_level(request.level)
            
            result = await self.biometric_auth.verify_behavioral(
                user_id=request.user_id,
                behavior_data=behavior_data,
                auth_level=auth_level
            )
            
            return VerificationResult(
                success=result.success,
                user_id=request.user_id if result.success else None,
                method=request.method,
                level=request.level,
                confidence=result.confidence_score,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=result.failure_reason,
                metadata={"match_score": result.match_score}
            )
            
        except Exception as e:
            logger.error(f"行为验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"行为验证异常: {str(e)}"
            )
    
    async def _verify_mfa(self, request: VerificationRequest) -> VerificationResult:
        """多因素验证"""
        try:
            auth_id = request.data.get("auth_id")
            factor_id = request.data.get("factor_id")
            verification_data = request.data.get("verification_data", {})
            
            if not auth_id or not factor_id:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少MFA会话信息"
                )
            
            result = await self.multi_factor_auth.submit_factor(
                auth_id=auth_id,
                factor_id=factor_id,
                verification_data=verification_data
            )
            
            return VerificationResult(
                success=result.success,
                user_id=result.user_id,
                method=request.method,
                level=request.level,
                confidence=0.9 if result.success else 0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=result.failure_reason,
                metadata={
                    "factors_used": [f.value for f in result.factors_used] if result.factors_used else []
                }
            )
            
        except Exception as e:
            logger.error(f"MFA验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"MFA验证异常: {str(e)}"
            )
    
    async def _verify_token(self, request: VerificationRequest) -> VerificationResult:
        """令牌验证"""
        try:
            token = request.data.get("token")
            if not token:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少令牌"
                )
            
            # 验证令牌
            payload = self.token_utils.verify_token(token)
            if not payload:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="令牌无效或已过期"
                )
            
            # 检查用户ID是否匹配
            token_user_id = payload.get("user_id")
            if token_user_id != request.user_id:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="令牌用户不匹配"
                )
            
            # 计算置信度
            confidence = self.config["method_weights"]["token"]
            
            return VerificationResult(
                success=True,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=confidence,
                verified_at=time.time(),
                request_id=request.request_id,
                metadata={"token_type": payload.get("type")}
            )
            
        except Exception as e:
            logger.error(f"令牌验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"令牌验证异常: {str(e)}"
            )
    
    async def _verify_api_key(self, request: VerificationRequest) -> VerificationResult:
        """API密钥验证"""
        try:
            api_key = request.data.get("api_key")
            if not api_key:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="缺少API密钥"
                )
            
            # 验证API密钥
            key_info = self.api_keys.get(api_key)
            if not key_info:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="API密钥无效"
                )
            
            # 检查是否过期
            if key_info["expires_at"] and key_info["expires_at"] < time.time():
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="API密钥已过期"
                )
            
            # 检查用户ID是否匹配
            if key_info["user_id"] != request.user_id:
                return VerificationResult(
                    success=False,
                    user_id=request.user_id,
                    method=request.method,
                    level=request.level,
                    confidence=0.0,
                    verified_at=time.time(),
                    request_id=request.request_id,
                    failure_reason="API密钥用户不匹配"
                )
            
            # 计算置信度
            confidence = self.config["method_weights"]["api_key"]
            
            return VerificationResult(
                success=True,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=confidence,
                verified_at=time.time(),
                request_id=request.request_id,
                metadata={"permissions": key_info.get("permissions", [])}
            )
            
        except Exception as e:
            logger.error(f"API密钥验证失败: {str(e)}")
            return VerificationResult(
                success=False,
                user_id=request.user_id,
                method=request.method,
                level=request.level,
                confidence=0.0,
                verified_at=time.time(),
                request_id=request.request_id,
                failure_reason=f"API密钥验证异常: {str(e)}"
            )
    
    def create_api_key(
        self,
        user_id: str,
        expires_in_days: int = 30,
        permissions: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        创建API密钥
        
        Args:
            user_id: 用户ID
            expires_in_days: 过期天数
            permissions: 权限列表
        
        Returns:
            (成功标志, 消息, API密钥)
        """
        try:
            api_key = secrets.token_urlsafe(32)
            expires_at = time.time() + (expires_in_days * 24 * 3600)
            
            self.api_keys[api_key] = {
                "user_id": user_id,
                "created_at": time.time(),
                "expires_at": expires_at,
                "permissions": permissions or [],
                "last_used": None
            }
            
            logger.info(f"为用户 {user_id} 创建API密钥，有效期 {expires_in_days} 天")
            return True, "API密钥创建成功", api_key
            
        except Exception as e:
            logger.error(f"创建API密钥失败: {str(e)}")
            return False, f"创建API密钥失败: {str(e)}", None
    
    def revoke_api_key(self, api_key: str, revoked_by: str) -> Tuple[bool, str]:
        """
        吊销API密钥
        
        Args:
            api_key: API密钥
            revoked_by: 吊销者
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if api_key not in self.api_keys:
                return False, "API密钥不存在"
            
            user_id = self.api_keys[api_key]["user_id"]
            del self.api_keys[api_key]
            
            self.audit_logger.log_event(
                event_type="API_KEY_REVOKE",
                user_id=revoked_by,
                details={"target_user": user_id},
                severity="INFO"
            )
            
            logger.info(f"用户 {revoked_by} 吊销了用户 {user_id} 的API密钥")
            return True, "API密钥吊销成功"
            
        except Exception as e:
            logger.error(f"吊销API密钥失败: {str(e)}")
            return False, f"吊销API密钥失败: {str(e)}"
    
    def _check_attempt_rate(self, user_id: str) -> bool:
        """检查尝试频率"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # 清理旧记录
        if user_id in self.attempt_records:
            self.attempt_records[user_id] = [
                t for t in self.attempt_records[user_id]
                if t > one_minute_ago
            ]
        
        # 检查尝试次数
        attempts = len(self.attempt_records.get(user_id, []))
        max_attempts = self.config["max_attempts_per_minute"]
        
        return attempts < max_attempts
    
    def _record_attempt(self, user_id: str) -> None:
        """记录尝试"""
        if user_id not in self.attempt_records:
            self.attempt_records[user_id] = []
        
        self.attempt_records[user_id].append(time.time())
        
        # 限制记录大小
        if len(self.attempt_records[user_id]) > 100:
            self.attempt_records[user_id] = self.attempt_records[user_id][-100:]
    
    def _map_verification_level(self, level: VerificationLevel):
        """映射验证级别到生物认证级别"""
        from .biometric_auth import BiometricAuthLevel
        
        mapping = {
            VerificationLevel.LOW: BiometricAuthLevel.LOW,
            VerificationLevel.MEDIUM: BiometricAuthLevel.MEDIUM,
            VerificationLevel.HIGH: BiometricAuthLevel.HIGH,
            VerificationLevel.CRITICAL: BiometricAuthLevel.CRITICAL
        }
        return mapping.get(level, BiometricAuthLevel.MEDIUM)
    
    def _get_stored_password_hash(self, user_id: str) -> Optional[str]:
        """获取存储的密码哈希（模拟实现）"""
        # 实际应用中应从数据库获取
        # 这里返回一个固定的测试哈希
        return hashlib.sha256("test_password".encode()).hexdigest()
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()


# 单例实例
_identity_verifier_instance = None


def get_identity_verifier() -> IdentityVerifier:
    """获取身份验证器单例实例"""
    global _identity_verifier_instance
    if _identity_verifier_instance is None:
        _identity_verifier_instance = IdentityVerifier()
    return _identity_verifier_instance

