"""
多因素认证模块 - 多因素身份验证
支持多种认证因素的组合验证，包括知识因素、持有因素和生物因素
"""

import asyncio
import logging
import time
import secrets
import string
import hashlib
import hmac
from typing import Dict, Any, Optional, Tuple, List, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import jwt
import pyotp
import qrcode
from cryptography.fernet import Fernet

from .biometric_auth import BiometricAuth, BiometricAuthLevel, BiometricType
from ...utils.security_utilities.encryption_utils import EncryptionUtils
from ...utils.security_utilities.token_utils import TokenUtils
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class AuthFactorType(Enum):
    """认证因素类型枚举"""
    PASSWORD = "password"  # 密码（知识因素）
    TOTP = "totp"  # 基于时间的一次性密码（持有因素）
    SMS = "sms"  # 短信验证码（持有因素）
    EMAIL = "email"  # 邮件验证码（持有因素）
    BIOMETRIC_VOICE = "biometric_voice"  # 声纹（生物因素）
    BIOMETRIC_FACE = "biometric_face"  # 面部（生物因素）
    BIOMETRIC_BEHAVIOR = "biometric_behavior"  # 行为（生物因素）
    HARDWARE_TOKEN = "hardware_token"  # 硬件令牌（持有因素）
    RECOVERY_CODE = "recovery_code"  # 恢复码（备用因素）


class AuthFactorStatus(Enum):
    """认证因素状态枚举"""
    ACTIVE = "active"  # 激活
    PENDING = "pending"  # 待验证（新注册）
    LOCKED = "locked"  # 锁定（多次失败）
    EXPIRED = "expired"  # 过期
    REVOKED = "revoked"  # 吊销


@dataclass
class AuthFactor:
    """认证因素数据模型"""
    factor_id: str
    user_id: str
    factor_type: AuthFactorType
    status: AuthFactorStatus
    created_at: float
    updated_at: float
    last_used_at: Optional[float] = None
    failure_count: int = 0
    locked_until: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    user_id: Optional[str]
    factors_used: List[AuthFactorType]
    factors_required: int
    factors_completed: int
    auth_id: str
    session_id: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[float] = None
    failure_reason: Optional[str] = None
    remaining_attempts: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiFactorAuth:
    """
    多因素认证主类
    管理多种认证因素的注册、验证和组合策略
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化多因素认证模块
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 用户认证因素存储
        self.factors: Dict[str, Dict[str, AuthFactor]] = {}  # user_id -> {factor_id -> factor}
        
        # 进行中的认证会话
        self.auth_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 初始化依赖组件
        self.biometric_auth = BiometricAuth()
        self.audit_logger = AuditLogger()
        self.encryption_utils = EncryptionUtils()
        self.token_utils = TokenUtils()
        
        # 密码哈希配置
        self.password_hasher = hashlib.sha256
        
        # TOTP配置
        self.totp_issuer = self.config.get("totp_issuer", "Mirexs")
        
        # 失败限制
        self.max_failures = self.config.get("max_failures_per_factor", 5)
        self.lockout_duration = self.config.get("lockout_duration_seconds", 300)  # 5分钟
        
        logger.info("多因素认证模块初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "totp_issuer": "Mirexs",
            "max_failures_per_factor": 5,
            "lockout_duration_seconds": 300,
            "session_timeout_seconds": 600,  # 认证会话超时
            "code_expiry_seconds": 300,  # 验证码过期时间
            "code_length": 6,  # 验证码长度
            "min_factors_required": {
                "low_security": 1,
                "medium_security": 2,
                "high_security": 2,
                "critical_security": 3
            },
            "recovery_codes_count": 10  # 恢复码数量
        }
    
    async def register_password(
        self,
        user_id: str,
        password: str
    ) -> Tuple[bool, str, Optional[AuthFactor]]:
        """
        注册密码认证因素
        
        Args:
            user_id: 用户ID
            password: 密码
        
        Returns:
            (成功标志, 消息, 认证因素)
        """
        try:
            # 验证密码强度
            is_valid, message = self._validate_password_strength(password)
            if not is_valid:
                return False, message, None
            
            # 哈希密码
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            factor_id = f"pwd_{secrets.token_hex(8)}"
            
            factor = AuthFactor(
                factor_id=factor_id,
                user_id=user_id,
                factor_type=AuthFactorType.PASSWORD,
                status=AuthFactorStatus.ACTIVE,
                created_at=time.time(),
                updated_at=time.time(),
                metadata={
                    "salt": salt,
                    "hash": password_hash,
                    "last_changed": time.time()
                }
            )
            
            if user_id not in self.factors:
                self.factors[user_id] = {}
            
            self.factors[user_id][factor_id] = factor
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="MFA_REGISTER",
                user_id=user_id,
                details={"factor_type": "password", "factor_id": factor_id},
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 密码注册成功")
            return True, "密码注册成功", factor
            
        except Exception as e:
            logger.error(f"密码注册失败: {str(e)}")
            return False, f"密码注册失败: {str(e)}", None
    
    async def register_totp(
        self,
        user_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        注册TOTP认证因素
        
        Args:
            user_id: 用户ID
        
        Returns:
            (成功标志, 消息, TOTP设置信息)
        """
        try:
            # 生成TOTP密钥
            secret = pyotp.random_base32()
            
            # 创建URI用于二维码
            uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_id,
                issuer_name=self.totp_issuer
            )
            
            factor_id = f"totp_{secrets.token_hex(8)}"
            
            factor = AuthFactor(
                factor_id=factor_id,
                user_id=user_id,
                factor_type=AuthFactorType.TOTP,
                status=AuthFactorStatus.PENDING,  # 需要验证才能激活
                created_at=time.time(),
                updated_at=time.time(),
                metadata={
                    "secret": self.encryption_utils.encrypt_string(secret),
                    "verified": False
                }
            )
            
            if user_id not in self.factors:
                self.factors[user_id] = {}
            
            self.factors[user_id][factor_id] = factor
            
            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=5
            )
            qr.add_data(uri)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # 将二维码转换为base64
            import io
            import base64
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            totp_info = {
                "factor_id": factor_id,
                "secret": secret,
                "uri": uri,
                "qr_code": f"data:image/png;base64,{qr_base64}"
            }
            
            logger.info(f"用户 {user_id} TOTP注册成功，待验证")
            return True, "TOTP注册成功，请扫描二维码完成验证", totp_info
            
        except Exception as e:
            logger.error(f"TOTP注册失败: {str(e)}")
            return False, f"TOTP注册失败: {str(e)}", None
    
    async def verify_totp(
        self,
        user_id: str,
        factor_id: str,
        token: str
    ) -> Tuple[bool, str]:
        """
        验证TOTP令牌并激活因素
        
        Args:
            user_id: 用户ID
            factor_id: 因素ID
            token: TOTP令牌
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if user_id not in self.factors or factor_id not in self.factors[user_id]:
                return False, "认证因素不存在"
            
            factor = self.factors[user_id][factor_id]
            
            if factor.factor_type != AuthFactorType.TOTP:
                return False, "因素类型错误"
            
            if factor.status != AuthFactorStatus.PENDING:
                return False, "因素已激活或已失效"
            
            # 解密密钥
            secret = self.encryption_utils.decrypt_string(factor.metadata["secret"])
            
            # 验证令牌
            totp = pyotp.TOTP(secret)
            if not totp.verify(token, valid_window=1):
                return False, "验证码错误"
            
            # 激活因素
            factor.status = AuthFactorStatus.ACTIVE
            factor.metadata["verified"] = True
            factor.metadata["verified_at"] = time.time()
            factor.updated_at = time.time()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="MFA_VERIFY",
                user_id=user_id,
                details={"factor_type": "totp", "factor_id": factor_id, "action": "activate"},
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} TOTP验证成功，因素已激活")
            return True, "TOTP验证成功"
            
        except Exception as e:
            logger.error(f"TOTP验证失败: {str(e)}")
            return False, f"TOTP验证失败: {str(e)}"
    
    async def generate_sms_code(
        self,
        user_id: str,
        phone_number: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        生成短信验证码
        
        Args:
            user_id: 用户ID
            phone_number: 手机号码
        
        Returns:
            (成功标志, 消息, 因素ID)
        """
        try:
            # 检查发送频率
            if user_id in self.factors:
                sms_factors = [f for f in self.factors[user_id].values() 
                               if f.factor_type == AuthFactorType.SMS]
                recent_sms = [f for f in sms_factors 
                              if f.created_at > time.time() - 60]  # 1分钟内
                if len(recent_sms) >= 3:
                    return False, "发送频率过高，请稍后再试", None
            
            # 生成验证码
            code = ''.join(secrets.choice(string.digits) for _ in range(self.config["code_length"]))
            expires_at = time.time() + self.config["code_expiry_seconds"]
            
            factor_id = f"sms_{secrets.token_hex(8)}"
            
            factor = AuthFactor(
                factor_id=factor_id,
                user_id=user_id,
                factor_type=AuthFactorType.SMS,
                status=AuthFactorStatus.PENDING,
                created_at=time.time(),
                updated_at=time.time(),
                metadata={
                    "phone": phone_number,
                    "code": self._hash_code(code),  # 存储哈希
                    "expires_at": expires_at,
                    "attempts": 0
                }
            )
            
            if user_id not in self.factors:
                self.factors[user_id] = {}
            
            self.factors[user_id][factor_id] = factor
            
            # 实际应用中应调用短信服务发送验证码
            # sms_service.send(phone_number, f"您的验证码是: {code}")
            
            logger.info(f"用户 {user_id} 短信验证码已生成，有效期至 {datetime.fromtimestamp(expires_at)}")
            return True, "验证码已发送", factor_id
            
        except Exception as e:
            logger.error(f"生成短信验证码失败: {str(e)}")
            return False, f"生成验证码失败: {str(e)}", None
    
    async def verify_code(
        self,
        user_id: str,
        factor_id: str,
        code: str
    ) -> Tuple[bool, str]:
        """
        验证验证码（短信或邮件）
        
        Args:
            user_id: 用户ID
            factor_id: 因素ID
            code: 验证码
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if user_id not in self.factors or factor_id not in self.factors[user_id]:
                return False, "认证因素不存在"
            
            factor = self.factors[user_id][factor_id]
            
            if factor.factor_type not in [AuthFactorType.SMS, AuthFactorType.EMAIL]:
                return False, "因素类型错误"
            
            # 检查过期
            if time.time() > factor.metadata["expires_at"]:
                return False, "验证码已过期"
            
            # 检查尝试次数
            factor.metadata["attempts"] = factor.metadata.get("attempts", 0) + 1
            if factor.metadata["attempts"] > 3:
                factor.status = AuthFactorStatus.LOCKED
                return False, "尝试次数过多，验证码已锁定"
            
            # 验证码哈希比对
            if self._hash_code(code) != factor.metadata["code"]:
                return False, "验证码错误"
            
            # 验证成功
            factor.status = AuthFactorStatus.ACTIVE
            factor.last_used_at = time.time()
            factor.updated_at = time.time()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="MFA_VERIFY",
                user_id=user_id,
                details={"factor_type": factor.factor_type.value, "factor_id": factor_id},
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 验证码验证成功")
            return True, "验证成功"
            
        except Exception as e:
            logger.error(f"验证码验证失败: {str(e)}")
            return False, f"验证失败: {str(e)}"
    
    async def generate_recovery_codes(
        self,
        user_id: str
    ) -> Tuple[bool, str, Optional[List[str]]]:
        """
        生成恢复码（备用认证方式）
        
        Args:
            user_id: 用户ID
        
        Returns:
            (成功标志, 消息, 恢复码列表)
        """
        try:
            count = self.config["recovery_codes_count"]
            codes = []
            hashed_codes = []
            
            for _ in range(count):
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
                codes.append(code)
                hashed_codes.append(self._hash_code(code))
            
            factor_id = f"recovery_{secrets.token_hex(8)}"
            
            factor = AuthFactor(
                factor_id=factor_id,
                user_id=user_id,
                factor_type=AuthFactorType.RECOVERY_CODE,
                status=AuthFactorStatus.ACTIVE,
                created_at=time.time(),
                updated_at=time.time(),
                metadata={
                    "codes": hashed_codes,
                    "used_codes": []
                }
            )
            
            if user_id not in self.factors:
                self.factors[user_id] = {}
            
            self.factors[user_id][factor_id] = factor
            
            logger.info(f"用户 {user_id} 生成 {count} 个恢复码")
            return True, "恢复码生成成功", codes
            
        except Exception as e:
            logger.error(f"生成恢复码失败: {str(e)}")
            return False, f"生成恢复码失败: {str(e)}", None
    
    async def verify_recovery_code(
        self,
        user_id: str,
        code: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        验证恢复码
        
        Args:
            user_id: 用户ID
            code: 恢复码
        
        Returns:
            (成功标志, 消息, 临时令牌)
        """
        try:
            if user_id not in self.factors:
                return False, "用户不存在", None
            
            # 查找恢复码因素
            recovery_factors = [f for f in self.factors[user_id].values() 
                                if f.factor_type == AuthFactorType.RECOVERY_CODE]
            
            if not recovery_factors:
                return False, "未找到恢复码", None
            
            factor = recovery_factors[0]
            
            # 检查状态
            if factor.status != AuthFactorStatus.ACTIVE:
                return False, "恢复码已失效", None
            
            # 验证码
            hashed_input = self._hash_code(code)
            if hashed_input in factor.metadata["used_codes"]:
                return False, "恢复码已被使用", None
            
            if hashed_input not in factor.metadata["codes"]:
                return False, "恢复码无效", None
            
            # 标记为已使用
            factor.metadata["used_codes"].append(hashed_input)
            
            # 如果所有恢复码都已使用，置为过期
            if len(factor.metadata["used_codes"]) >= len(factor.metadata["codes"]):
                factor.status = AuthFactorStatus.EXPIRED
            
            factor.updated_at = time.time()
            
            # 生成临时令牌
            temp_token = self.token_utils.generate_token(
                user_id=user_id,
                expires_in=300,  # 5分钟
                token_type="recovery_access"
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="MFA_RECOVERY_USED",
                user_id=user_id,
                details={"remaining_codes": len(factor.metadata["codes"]) - len(factor.metadata["used_codes"])},
                severity="WARNING"
            )
            
            logger.info(f"用户 {user_id} 使用恢复码成功，剩余 {len(factor.metadata['codes']) - len(factor.metadata['used_codes'])} 个")
            return True, "恢复码验证成功", temp_token
            
        except Exception as e:
            logger.error(f"验证恢复码失败: {str(e)}")
            return False, f"验证恢复码失败: {str(e)}", None
    
    async def start_authentication(
        self,
        user_id: str,
        required_level: str = "medium_security",
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        开始多因素认证流程
        
        Args:
            user_id: 用户ID
            required_level: 所需安全级别
            context: 上下文信息
        
        Returns:
            (成功标志, 消息, 认证会话信息)
        """
        try:
            # 获取用户可用的认证因素
            available_factors = self._get_available_factors(user_id)
            
            if not available_factors:
                return False, "用户未配置任何认证因素", None
            
            # 确定所需因素数量
            required_count = self.config["min_factors_required"].get(required_level, 1)
            
            # 创建认证会话
            auth_id = secrets.token_hex(16)
            expires_at = time.time() + self.config["session_timeout_seconds"]
            
            auth_session = {
                "auth_id": auth_id,
                "user_id": user_id,
                "required_level": required_level,
                "required_count": required_count,
                "completed_factors": [],
                "remaining_factors": [f.factor_id for f in available_factors],
                "status": "pending",
                "created_at": time.time(),
                "expires_at": expires_at,
                "context": context or {}
            }
            
            self.auth_sessions[auth_id] = auth_session
            
            # 获取认证选项
            auth_options = []
            for factor in available_factors[:5]:  # 最多返回5个选项
                auth_options.append({
                    "factor_id": factor.factor_id,
                    "factor_type": factor.factor_type.value,
                    "description": self._get_factor_description(factor)
                })
            
            session_info = {
                "auth_id": auth_id,
                "required_count": required_count,
                "options": auth_options,
                "expires_at": expires_at
            }
            
            logger.info(f"用户 {user_id} 开始认证流程，需要 {required_count} 个因素")
            return True, "认证流程已开始", session_info
            
        except Exception as e:
            logger.error(f"开始认证流程失败: {str(e)}")
            return False, f"开始认证失败: {str(e)}", None
    
    async def submit_factor(
        self,
        auth_id: str,
        factor_id: str,
        verification_data: Dict[str, Any]
    ) -> AuthResult:
        """
        提交认证因素验证
        
        Args:
            auth_id: 认证会话ID
            factor_id: 因素ID
            verification_data: 验证数据
        
        Returns:
            认证结果
        """
        try:
            # 检查认证会话
            if auth_id not in self.auth_sessions:
                return AuthResult(
                    success=False,
                    user_id=None,
                    factors_used=[],
                    factors_required=0,
                    factors_completed=0,
                    auth_id=auth_id,
                    failure_reason="认证会话不存在"
                )
            
            session = self.auth_sessions[auth_id]
            
            # 检查会话是否过期
            if time.time() > session["expires_at"]:
                return AuthResult(
                    success=False,
                    user_id=None,
                    factors_used=[],
                    factors_required=session["required_count"],
                    factors_completed=len(session["completed_factors"]),
                    auth_id=auth_id,
                    failure_reason="认证会话已过期"
                )
            
            # 检查因素是否可用
            if factor_id not in session["remaining_factors"]:
                return AuthResult(
                    success=False,
                    user_id=session["user_id"],
                    factors_used=session["completed_factors"],
                    factors_required=session["required_count"],
                    factors_completed=len(session["completed_factors"]),
                    auth_id=auth_id,
                    failure_reason="因素不可用或已使用"
                )
            
            user_id = session["user_id"]
            
            # 获取因素信息
            if user_id not in self.factors or factor_id not in self.factors[user_id]:
                return AuthResult(
                    success=False,
                    user_id=user_id,
                    factors_used=session["completed_factors"],
                    factors_required=session["required_count"],
                    factors_completed=len(session["completed_factors"]),
                    auth_id=auth_id,
                    failure_reason="因素不存在"
                )
            
            factor = self.factors[user_id][factor_id]
            
            # 根据因素类型进行验证
            verification_success = False
            factor_result = None
            
            if factor.factor_type == AuthFactorType.PASSWORD:
                verification_success = await self._verify_password(
                    user_id, factor_id, verification_data.get("password", "")
                )
            
            elif factor.factor_type == AuthFactorType.TOTP:
                verification_success = await self._verify_totp_token(
                    user_id, factor_id, verification_data.get("token", "")
                )
            
            elif factor.factor_type == AuthFactorType.SMS:
                result, _ = await self.verify_code(
                    user_id, factor_id, verification_data.get("code", "")
                )
                verification_success = result
            
            elif factor.factor_type == AuthFactorType.BIOMETRIC_VOICE:
                # 使用生物认证模块
                result = await self.biometric_auth.verify_voiceprint(
                    user_id=user_id,
                    audio_samples=verification_data.get("audio"),
                    sample_rate=verification_data.get("sample_rate", 16000),
                    auth_level=BiometricAuthLevel.MEDIUM
                )
                verification_success = result.success
                factor_result = result
            
            elif factor.factor_type == AuthFactorType.BIOMETRIC_FACE:
                result = await self.biometric_auth.verify_facial(
                    user_id=user_id,
                    face_image=verification_data.get("image"),
                    auth_level=BiometricAuthLevel.MEDIUM
                )
                verification_success = result.success
                factor_result = result
            
            # 处理验证结果
            if verification_success:
                # 更新因素使用记录
                factor.last_used_at = time.time()
                factor.failure_count = 0
                
                # 添加到已完成列表
                session["completed_factors"].append(factor_id)
                session["remaining_factors"].remove(factor_id)
                
                # 记录审计日志
                self.audit_logger.log_event(
                    event_type="MFA_FACTOR_SUCCESS",
                    user_id=user_id,
                    details={
                        "auth_id": auth_id,
                        "factor_type": factor.factor_type.value,
                        "factor_id": factor_id
                    },
                    severity="INFO"
                )
                
                logger.info(f"用户 {user_id} 认证因素 {factor.factor_type.value} 验证成功")
                
                # 检查是否完成所需因素数量
                if len(session["completed_factors"]) >= session["required_count"]:
                    return await self._complete_authentication(auth_id)
                else:
                    # 返回部分成功
                    return AuthResult(
                        success=True,
                        user_id=user_id,
                        factors_used=session["completed_factors"],
                        factors_required=session["required_count"],
                        factors_completed=len(session["completed_factors"]),
                        auth_id=auth_id,
                        metadata={
                            "next_factors": session["remaining_factors"],
                            "factor_result": factor_result.metadata if factor_result else None
                        }
                    )
            else:
                # 处理失败
                factor.failure_count += 1
                
                # 检查是否需要锁定
                if factor.failure_count >= self.max_failures:
                    factor.status = AuthFactorStatus.LOCKED
                    factor.locked_until = time.time() + self.lockout_duration
                    
                    logger.warning(f"用户 {user_id} 因素 {factor.factor_type.value} 已被锁定")
                
                # 记录审计日志
                self.audit_logger.log_event(
                    event_type="MFA_FACTOR_FAILURE",
                    user_id=user_id,
                    details={
                        "auth_id": auth_id,
                        "factor_type": factor.factor_type.value,
                        "factor_id": factor_id,
                        "failure_count": factor.failure_count
                    },
                    severity="WARNING"
                )
                
                remaining_attempts = max(0, self.max_failures - factor.failure_count)
                
                return AuthResult(
                    success=False,
                    user_id=user_id,
                    factors_used=session["completed_factors"],
                    factors_required=session["required_count"],
                    factors_completed=len(session["completed_factors"]),
                    auth_id=auth_id,
                    failure_reason="验证失败",
                    remaining_attempts=remaining_attempts
                )
            
        except Exception as e:
            logger.error(f"提交认证因素失败: {str(e)}")
            return AuthResult(
                success=False,
                user_id=None,
                factors_used=[],
                factors_required=0,
                factors_completed=0,
                auth_id=auth_id,
                failure_reason=f"验证过程异常: {str(e)}"
            )
    
    async def _complete_authentication(self, auth_id: str) -> AuthResult:
        """完成认证流程，生成会话和令牌"""
        session = self.auth_sessions[auth_id]
        user_id = session["user_id"]
        
        # 生成会话ID
        session_id = secrets.token_hex(16)
        
        # 生成认证令牌
        token = self.token_utils.generate_token(
            user_id=user_id,
            expires_in=3600,  # 1小时
            token_type="access",
            metadata={
                "auth_id": auth_id,
                "factors_used": session["completed_factors"]
            }
        )
        
        expires_at = time.time() + 3600
        
        # 记录审计日志
        self.audit_logger.log_event(
            event_type="MFA_COMPLETE",
            user_id=user_id,
            details={
                "auth_id": auth_id,
                "factors_count": len(session["completed_factors"]),
                "required_level": session["required_level"]
            },
            severity="INFO"
        )
        
        logger.info(f"用户 {user_id} 认证完成，使用了 {len(session['completed_factors'])} 个因素")
        
        # 可选：清理会话
        # del self.auth_sessions[auth_id]
        
        return AuthResult(
            success=True,
            user_id=user_id,
            factors_used=session["completed_factors"],
            factors_required=session["required_count"],
            factors_completed=len(session["completed_factors"]),
            auth_id=auth_id,
            session_id=session_id,
            token=token,
            expires_at=expires_at
        )
    
    async def _verify_password(
        self,
        user_id: str,
        factor_id: str,
        password: str
    ) -> bool:
        """验证密码"""
        factor = self.factors[user_id][factor_id]
        
        if factor.status != AuthFactorStatus.ACTIVE:
            return False
        
        salt = factor.metadata["salt"]
        stored_hash = factor.metadata["hash"]
        
        calculated_hash = self._hash_password(password, salt)
        
        return hmac.compare_digest(calculated_hash, stored_hash)
    
    async def _verify_totp_token(
        self,
        user_id: str,
        factor_id: str,
        token: str
    ) -> bool:
        """验证TOTP令牌"""
        factor = self.factors[user_id][factor_id]
        
        if factor.status != AuthFactorStatus.ACTIVE:
            return False
        
        secret = self.encryption_utils.decrypt_string(factor.metadata["secret"])
        totp = pyotp.TOTP(secret)
        
        return totp.verify(token, valid_window=1)
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """验证密码强度"""
        if len(password) < 8:
            return False, "密码长度至少8位"
        
        if not any(c.isupper() for c in password):
            return False, "密码需要至少一个大写字母"
        
        if not any(c.islower() for c in password):
            return False, "密码需要至少一个小写字母"
        
        if not any(c.isdigit() for c in password):
            return False, "密码需要至少一个数字"
        
        if not any(c in string.punctuation for c in password):
            return False, "密码需要至少一个特殊字符"
        
        return True, "密码强度符合要求"
    
    def _hash_password(self, password: str, salt: str) -> str:
        """哈希密码"""
        salted = password + salt
        return hashlib.sha256(salted.encode()).hexdigest()
    
    def _hash_code(self, code: str) -> str:
        """哈希验证码"""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def _get_available_factors(self, user_id: str) -> List[AuthFactor]:
        """获取用户可用的认证因素"""
        if user_id not in self.factors:
            return []
        
        available = []
        for factor in self.factors[user_id].values():
            if factor.status == AuthFactorStatus.ACTIVE:
                # 检查是否被锁定
                if factor.locked_until and time.time() < factor.locked_until:
                    continue
                available.append(factor)
        
        return available
    
    def _get_factor_description(self, factor: AuthFactor) -> str:
        """获取因素描述"""
        descriptions = {
            AuthFactorType.PASSWORD: "密码",
            AuthFactorType.TOTP: "身份验证器应用",
            AuthFactorType.SMS: "短信验证码",
            AuthFactorType.EMAIL: "邮件验证码",
            AuthFactorType.BIOMETRIC_VOICE: "声纹识别",
            AuthFactorType.BIOMETRIC_FACE: "面部识别",
            AuthFactorType.HARDWARE_TOKEN: "硬件令牌",
            AuthFactorType.RECOVERY_CODE: "恢复码"
        }
        return descriptions.get(factor.factor_type, "未知因素")
    
    def get_user_factors(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有认证因素信息"""
        if user_id not in self.factors:
            return []
        
        result = []
        for factor in self.factors[user_id].values():
            result.append({
                "factor_id": factor.factor_id,
                "factor_type": factor.factor_type.value,
                "status": factor.status.value,
                "created_at": factor.created_at,
                "last_used_at": factor.last_used_at,
                "description": self._get_factor_description(factor)
            })
        
        return result
    
    async def remove_factor(self, user_id: str, factor_id: str) -> bool:
        """移除用户的认证因素"""
        try:
            if user_id not in self.factors or factor_id not in self.factors[user_id]:
                return False
            
            factor = self.factors[user_id][factor_id]
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="MFA_REMOVE",
                user_id=user_id,
                details={"factor_type": factor.factor_type.value, "factor_id": factor_id},
                severity="INFO"
            )
            
            del self.factors[user_id][factor_id]
            
            logger.info(f"用户 {user_id} 移除了认证因素 {factor.factor_type.value}")
            return True
        except Exception as e:
            logger.error(f"移除认证因素失败: {str(e)}")
            return False


# 单例实例
_multi_factor_auth_instance = None


def get_multi_factor_auth() -> MultiFactorAuth:
    """获取多因素认证单例实例"""
    global _multi_factor_auth_instance
    if _multi_factor_auth_instance is None:
        _multi_factor_auth_instance = MultiFactorAuth()
    return _multi_factor_auth_instance

