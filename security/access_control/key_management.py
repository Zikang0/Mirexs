"""
密钥管理模块 - 管理加密密钥
提供密钥的生成、存储、轮换、吊销等全生命周期管理功能
"""

import asyncio
import logging
import time
import json
import secrets
import base64
import hashlib
import os
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# Cryptography 导入
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.x509 import CertificateBuilder, Name, NameOID, BasicConstraints, SubjectAlternativeName, DNSName
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption
import datetime

from ..security_monitoring.audit_logger import AuditLogger
from ...utils.security_utilities.encryption_utils import EncryptionUtils

logger = logging.getLogger(__name__)


class KeyType(Enum):
    """密钥类型枚举"""
    SYMMETRIC = "symmetric"  # 对称密钥 (AES)
    ASYMMETRIC = "asymmetric"  # 非对称密钥对 (RSA/EC)
    HMAC = "hmac"  # HMAC密钥
    CERTIFICATE = "certificate"  # 证书
    PASSWORD = "password"  # 密码（哈希后存储）


class KeyAlgorithm(Enum):
    """密钥算法枚举"""
    AES_128 = "aes-128"
    AES_256 = "aes-256"
    RSA_2048 = "rsa-2048"
    RSA_4096 = "rsa-4096"
    EC_P256 = "ec-p256"
    EC_P384 = "ec-p384"
    EC_P521 = "ec-p521"
    HMAC_SHA256 = "hmac-sha256"
    HMAC_SHA512 = "hmac-sha512"


class KeyStatus(Enum):
    """密钥状态枚举"""
    ACTIVE = "active"  # 活跃可用
    INACTIVE = "inactive"  # 未激活
    EXPIRED = "expired"  # 过期
    REVOKED = "revoked"  # 吊销
    COMPROMISED = "compromised"  # 泄露
    PENDING_ROTATION = "pending_rotation"  # 待轮换
    ARCHIVED = "archived"  # 归档


class KeyPurpose(Enum):
    """密钥用途枚举"""
    ENCRYPTION = "encryption"  # 数据加密
    DECRYPTION = "decryption"  # 数据解密
    SIGNING = "signing"  # 签名
    VERIFICATION = "verification"  # 验签
    AUTHENTICATION = "authentication"  # 认证
    KEY_WRAPPING = "key_wrapping"  # 密钥包装
    TLS = "tls"  # TLS/SSL
    CODE_SIGNING = "code_signing"  # 代码签名


@dataclass
class KeyMetadata:
    """密钥元数据"""
    key_id: str
    key_type: KeyType
    key_algorithm: KeyAlgorithm
    key_status: KeyStatus
    purpose: List[KeyPurpose]
    created_at: float
    created_by: str
    expires_at: Optional[float] = None
    last_used_at: Optional[float] = None
    rotation_due_at: Optional[float] = None
    version: int = 1
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptedKey:
    """加密存储的密钥"""
    key_id: str
    encrypted_data: bytes  # 加密的密钥数据
    key_metadata: KeyMetadata
    wrapped_by: Optional[str] = None  # 包装密钥ID
    integrity_hash: str  # 完整性哈希
    backup_available: bool = False
    backup_location: Optional[str] = None


class KeyManagement:
    """
    密钥管理器 - 管理加密密钥的全生命周期
    包括生成、存储、轮换、吊销、归档等
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化密钥管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储加密的密钥
        self.keys: Dict[str, EncryptedKey] = {}
        
        # 主密钥（用于加密其他密钥）
        self.master_key_id = self.config.get("master_key_id", "master_key")
        self.master_key = self._initialize_master_key()
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/keys"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.encryption_utils = EncryptionUtils()
        
        # 密钥使用计数器（用于审计）
        self.key_usage_counter: Dict[str, int] = {}
        
        # 加载已有密钥
        self._load_keys()
        
        # 启动自动轮换检查
        self._rotation_check_task = None
        
        logger.info(f"密钥管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/keys",
            "master_key_source": "env",  # env, file, hsm
            "master_key_env_var": "MIREXS_MASTER_KEY",
            "key_encryption_algorithm": "aes-256-gcm",
            "default_key_expiry_days": 365,
            "rotation_enabled": True,
            "rotation_check_interval_hours": 24,
            "key_backup_enabled": True,
            "max_keys_per_user": 100,
            "audit_key_usage": True
        }
    
    def _initialize_master_key(self) -> Optional[bytes]:
        """初始化主密钥"""
        try:
            master_key_source = self.config["master_key_source"]
            
            if master_key_source == "env":
                master_key_b64 = os.environ.get(self.config["master_key_env_var"])
                if master_key_b64:
                    master_key = base64.b64decode(master_key_b64)
                    if len(master_key) == 32:  # AES-256
                        return master_key
                    else:
                        logger.warning("环境变量中的主密钥长度不正确")
            
            # 如果没有找到或长度不正确，生成新的主密钥
            logger.info("生成新的主密钥")
            master_key = Fernet.generate_key()
            
            # 警告用户需要保存主密钥
            logger.warning("=" * 60)
            logger.warning("新的主密钥已生成！请安全保存以下密钥：")
            logger.warning(base64.b64encode(master_key).decode())
            logger.warning("如果丢失此密钥，所有加密数据将无法恢复！")
            logger.warning("=" * 60)
            
            return master_key
            
        except Exception as e:
            logger.error(f"初始化主密钥失败: {str(e)}")
            return None
    
    def _load_keys(self) -> None:
        """从存储加载密钥"""
        try:
            keys_file = self.storage_path / "keys.json"
            if not keys_file.exists():
                return
            
            with open(keys_file, 'r', encoding='utf-8') as f:
                keys_data = json.load(f)
            
            for key_id, key_dict in keys_data.items():
                # 解码加密数据
                encrypted_data = base64.b64decode(key_dict["encrypted_data"])
                
                # 重建密钥元数据
                metadata_dict = key_dict["key_metadata"]
                metadata_dict["key_type"] = KeyType(metadata_dict["key_type"])
                metadata_dict["key_algorithm"] = KeyAlgorithm(metadata_dict["key_algorithm"])
                metadata_dict["key_status"] = KeyStatus(metadata_dict["key_status"])
                metadata_dict["purpose"] = [KeyPurpose(p) for p in metadata_dict["purpose"]]
                metadata = KeyMetadata(**metadata_dict)
                
                encrypted_key = EncryptedKey(
                    key_id=key_id,
                    encrypted_data=encrypted_data,
                    key_metadata=metadata,
                    wrapped_by=key_dict.get("wrapped_by"),
                    integrity_hash=key_dict["integrity_hash"],
                    backup_available=key_dict.get("backup_available", False),
                    backup_location=key_dict.get("backup_location")
                )
                
                self.keys[key_id] = encrypted_key
            
            logger.info(f"加载了 {len(self.keys)} 个密钥")
        except Exception as e:
            logger.error(f"加载密钥失败: {str(e)}")
    
    def _save_keys(self) -> None:
        """保存密钥到存储"""
        try:
            keys_data = {}
            
            for key_id, encrypted_key in self.keys.items():
                keys_data[key_id] = {
                    "encrypted_data": base64.b64encode(encrypted_key.encrypted_data).decode(),
                    "key_metadata": {
                        "key_id": encrypted_key.key_metadata.key_id,
                        "key_type": encrypted_key.key_metadata.key_type.value,
                        "key_algorithm": encrypted_key.key_metadata.key_algorithm.value,
                        "key_status": encrypted_key.key_metadata.key_status.value,
                        "purpose": [p.value for p in encrypted_key.key_metadata.purpose],
                        "created_at": encrypted_key.key_metadata.created_at,
                        "created_by": encrypted_key.key_metadata.created_by,
                        "expires_at": encrypted_key.key_metadata.expires_at,
                        "last_used_at": encrypted_key.key_metadata.last_used_at,
                        "rotation_due_at": encrypted_key.key_metadata.rotation_due_at,
                        "version": encrypted_key.key_metadata.version,
                        "description": encrypted_key.key_metadata.description,
                        "tags": encrypted_key.key_metadata.tags,
                        "metadata": encrypted_key.key_metadata.metadata
                    },
                    "wrapped_by": encrypted_key.wrapped_by,
                    "integrity_hash": encrypted_key.integrity_hash,
                    "backup_available": encrypted_key.backup_available,
                    "backup_location": encrypted_key.backup_location
                }
            
            with open(self.storage_path / "keys.json", 'w', encoding='utf-8') as f:
                json.dump(keys_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.keys)} 个密钥")
        except Exception as e:
            logger.error(f"保存密钥失败: {str(e)}")
    
    def generate_symmetric_key(
        self,
        key_id: str,
        algorithm: KeyAlgorithm,
        purpose: List[KeyPurpose],
        created_by: str,
        expiry_days: Optional[int] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[KeyMetadata]]:
        """
        生成对称密钥
        
        Args:
            key_id: 密钥ID
            algorithm: 算法
            purpose: 用途
            created_by: 创建者
            expiry_days: 过期天数
            description: 描述
            tags: 标签
        
        Returns:
            (成功标志, 消息, 密钥元数据)
        """
        try:
            if key_id in self.keys:
                return False, f"密钥ID {key_id} 已存在", None
            
            # 根据算法生成密钥
            if algorithm == KeyAlgorithm.AES_128:
                key = secrets.token_bytes(16)  # 128位
            elif algorithm == KeyAlgorithm.AES_256:
                key = secrets.token_bytes(32)  # 256位
            elif algorithm == KeyAlgorithm.HMAC_SHA256:
                key = secrets.token_bytes(32)
            elif algorithm == KeyAlgorithm.HMAC_SHA512:
                key = secrets.token_bytes(64)
            else:
                return False, f"不支持的对称算法: {algorithm.value}", None
            
            # 创建密钥元数据
            created_at = time.time()
            expires_at = None
            if expiry_days:
                expires_at = created_at + (expiry_days * 24 * 3600)
            
            metadata = KeyMetadata(
                key_id=key_id,
                key_type=KeyType.SYMMETRIC,
                key_algorithm=algorithm,
                key_status=KeyStatus.ACTIVE,
                purpose=purpose,
                created_at=created_at,
                created_by=created_by,
                expires_at=expires_at,
                version=1,
                description=description,
                tags=tags or []
            )
            
            # 加密密钥
            encrypted_key = self._encrypt_key(key, metadata)
            
            self.keys[key_id] = encrypted_key
            self._save_keys()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="KEY_GENERATE",
                user_id=created_by,
                details={
                    "key_id": key_id,
                    "key_type": "symmetric",
                    "algorithm": algorithm.value,
                    "purpose": [p.value for p in purpose]
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {created_by} 生成对称密钥 {key_id}")
            return True, "对称密钥生成成功", metadata
            
        except Exception as e:
            logger.error(f"生成对称密钥失败: {str(e)}")
            return False, f"生成对称密钥失败: {str(e)}", None
    
    def generate_asymmetric_key_pair(
        self,
        key_id: str,
        algorithm: KeyAlgorithm,
        purpose: List[KeyPurpose],
        created_by: str,
        expiry_days: Optional[int] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[Dict[str, KeyMetadata]]]:
        """
        生成非对称密钥对
        
        Args:
            key_id: 密钥ID（用于私钥）
            algorithm: 算法
            purpose: 用途
            created_by: 创建者
            expiry_days: 过期天数
            description: 描述
            tags: 标签
        
        Returns:
            (成功标志, 消息, 密钥元数据字典 {private, public})
        """
        try:
            private_key_id = f"{key_id}_private"
            public_key_id = f"{key_id}_public"
            
            if private_key_id in self.keys or public_key_id in self.keys:
                return False, f"密钥ID {key_id} 已存在", None
            
            # 生成密钥对
            if algorithm == KeyAlgorithm.RSA_2048:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
            elif algorithm == KeyAlgorithm.RSA_4096:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096,
                    backend=default_backend()
                )
            elif algorithm == KeyAlgorithm.EC_P256:
                private_key = ec.generate_private_key(
                    ec.SECP256R1(),
                    backend=default_backend()
                )
            elif algorithm == KeyAlgorithm.EC_P384:
                private_key = ec.generate_private_key(
                    ec.SECP384R1(),
                    backend=default_backend()
                )
            elif algorithm == KeyAlgorithm.EC_P521:
                private_key = ec.generate_private_key(
                    ec.SECP521R1(),
                    backend=default_backend()
                )
            else:
                return False, f"不支持的非对称算法: {algorithm.value}", None
            
            public_key = private_key.public_key()
            
            # 序列化密钥
            private_bytes = private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.PKCS8,
                encryption_algorithm=NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=Encoding.PEM,
                format=PublicFormat.SubjectPublicKeyInfo
            )
            
            # 创建密钥元数据
            created_at = time.time()
            expires_at = None
            if expiry_days:
                expires_at = created_at + (expiry_days * 24 * 3600)
            
            private_metadata = KeyMetadata(
                key_id=private_key_id,
                key_type=KeyType.ASYMMETRIC,
                key_algorithm=algorithm,
                key_status=KeyStatus.ACTIVE,
                purpose=purpose,
                created_at=created_at,
                created_by=created_by,
                expires_at=expires_at,
                version=1,
                description=f"{description} (私钥)" if description else "私钥",
                tags=tags or []
            )
            
            public_metadata = KeyMetadata(
                key_id=public_key_id,
                key_type=KeyType.ASYMMETRIC,
                key_algorithm=algorithm,
                key_status=KeyStatus.ACTIVE,
                purpose=[p for p in purpose if p in [KeyPurpose.VERIFICATION, KeyPurpose.ENCRYPTION]],
                created_at=created_at,
                created_by=created_by,
                expires_at=expires_at,
                version=1,
                description=f"{description} (公钥)" if description else "公钥",
                tags=tags or []
            )
            
            # 加密密钥
            encrypted_private = self._encrypt_key(private_bytes, private_metadata)
            encrypted_public = self._encrypt_key(public_bytes, public_metadata)
            
            self.keys[private_key_id] = encrypted_private
            self.keys[public_key_id] = encrypted_public
            self._save_keys()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="KEY_GENERATE",
                user_id=created_by,
                details={
                    "key_id": key_id,
                    "key_type": "asymmetric",
                    "algorithm": algorithm.value,
                    "purpose": [p.value for p in purpose]
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {created_by} 生成非对称密钥对 {key_id}")
            return True, "非对称密钥对生成成功", {
                "private": private_metadata,
                "public": public_metadata
            }
            
        except Exception as e:
            logger.error(f"生成非对称密钥对失败: {str(e)}")
            return False, f"生成非对称密钥对失败: {str(e)}", None
    
    def generate_certificate(
        self,
        key_id: str,
        common_name: str,
        subject_alt_names: List[str],
        created_by: str,
        ca_key_id: Optional[str] = None,
        expiry_days: int = 365,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[KeyMetadata]]:
        """
        生成证书（自签名或由CA签发）
        
        Args:
            key_id: 密钥ID
            common_name: 通用名称
            subject_alt_names: 主题备用名称列表
            created_by: 创建者
            ca_key_id: CA密钥ID（None表示自签名）
            expiry_days: 过期天数
            description: 描述
            tags: 标签
        
        Returns:
            (成功标志, 消息, 证书密钥元数据)
        """
        try:
            # 生成密钥对
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # 构建证书主体 - 使用正确的 NameAttribute
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name)
            ])
            
            # 如果不是自签名，使用CA的密钥
            if ca_key_id:
                ca_key = self.get_key(ca_key_id)
                if not ca_key:
                    return False, f"CA密钥 {ca_key_id} 不存在", None
                issuer = x509.Name([
                    x509.NameAttribute(NameOID.COMMON_NAME, "Mirexs CA")
                ])
            
            # 构建证书
            cert_builder = x509.CertificateBuilder()
            cert_builder = cert_builder.subject_name(subject)
            cert_builder = cert_builder.issuer_name(issuer)
            cert_builder = cert_builder.public_key(private_key.public_key())
            cert_builder = cert_builder.serial_number(x509.random_serial_number())
            cert_builder = cert_builder.not_valid_before(datetime.datetime.utcnow())
            cert_builder = cert_builder.not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days)
            )
            
            # 添加SAN扩展
            san_list = [x509.DNSName(name) for name in subject_alt_names]
            cert_builder = cert_builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
            
            # 添加基本约束
            cert_builder = cert_builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
            
            # 签名证书
            if ca_key_id:
                # 使用CA签名
                ca_key_material = self.get_key_material(ca_key_id)
                if not ca_key_material:
                    return False, "无法获取CA密钥材料", None
                
                ca_private_key = serialization.load_pem_private_key(
                    ca_key_material,
                    password=None,
                    backend=default_backend()
                )
                certificate = cert_builder.sign(
                    private_key=ca_private_key,
                    algorithm=hashes.SHA256(),
                    backend=default_backend()
                )
            else:
                # 自签名
                certificate = cert_builder.sign(
                    private_key=private_key,
                    algorithm=hashes.SHA256(),
                    backend=default_backend()
                )
            
            # 序列化证书和私钥
            cert_bytes = certificate.public_bytes(Encoding.PEM)
            private_bytes = private_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.PKCS8,
                encryption_algorithm=NoEncryption()
            )
            
            # 创建证书元数据
            created_at = time.time()
            expires_at = created_at + (expiry_days * 24 * 3600)
            
            cert_metadata = KeyMetadata(
                key_id=key_id,
                key_type=KeyType.CERTIFICATE,
                key_algorithm=KeyAlgorithm.RSA_2048,
                key_status=KeyStatus.ACTIVE,
                purpose=[KeyPurpose.TLS, KeyPurpose.AUTHENTICATION],
                created_at=created_at,
                created_by=created_by,
                expires_at=expires_at,
                version=1,
                description=description or f"证书: {common_name}",
                tags=tags or [],
                metadata={
                    "common_name": common_name,
                    "subject_alt_names": subject_alt_names,
                    "issuer": "self-signed" if not ca_key_id else f"CA: {ca_key_id}",
                    "certificate": cert_bytes.decode()
                }
            )
            
            # 存储证书和私钥
            encrypted_cert = self._encrypt_key(cert_bytes, cert_metadata)
            self.keys[key_id] = encrypted_cert
            
            # 同时存储私钥
            private_key_id = f"{key_id}_private"
            private_metadata = KeyMetadata(
                key_id=private_key_id,
                key_type=KeyType.ASYMMETRIC,
                key_algorithm=KeyAlgorithm.RSA_2048,
                key_status=KeyStatus.ACTIVE,
                purpose=[KeyPurpose.SIGNING, KeyPurpose.DECRYPTION],
                created_at=created_at,
                created_by=created_by,
                expires_at=expires_at,
                version=1,
                description=f"{description} (私钥)" if description else f"证书私钥: {common_name}",
                tags=tags or []
            )
            
            encrypted_private = self._encrypt_key(private_bytes, private_metadata)
            self.keys[private_key_id] = encrypted_private
            
            self._save_keys()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="CERTIFICATE_GENERATE",
                user_id=created_by,
                details={
                    "key_id": key_id,
                    "common_name": common_name,
                    "expiry_days": expiry_days
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {created_by} 生成证书 {key_id} 用于 {common_name}")
            return True, "证书生成成功", cert_metadata
            
        except Exception as e:
            logger.error(f"生成证书失败: {str(e)}")
            return False, f"生成证书失败: {str(e)}", None
    
    def get_key(self, key_id: str) -> Optional[EncryptedKey]:
        """获取加密的密钥"""
        return self.keys.get(key_id)
    
    def get_key_material(self, key_id: str) -> Optional[bytes]:
        """获取解密后的密钥材料"""
        encrypted_key = self.keys.get(key_id)
        if not encrypted_key:
            return None
        
        # 验证完整性
        integrity_hash = self._compute_integrity_hash(encrypted_key.encrypted_data)
        if integrity_hash != encrypted_key.integrity_hash:
            logger.error(f"密钥 {key_id} 完整性验证失败")
            return None
        
        # 使用主密钥解密
        try:
            f = Fernet(self.master_key)
            decrypted = f.decrypt(encrypted_key.encrypted_data)
            
            # 更新使用计数
            if self.config["audit_key_usage"]:
                self.key_usage_counter[key_id] = self.key_usage_counter.get(key_id, 0) + 1
                encrypted_key.key_metadata.last_used_at = time.time()
            
            return decrypted
        except Exception as e:
            logger.error(f"解密密钥 {key_id} 失败: {str(e)}")
            return None
    
    def _encrypt_key(self, key_material: bytes, metadata: KeyMetadata) -> EncryptedKey:
        """加密密钥材料"""
        f = Fernet(self.master_key)
        encrypted = f.encrypt(key_material)
        
        integrity_hash = self._compute_integrity_hash(encrypted)
        
        return EncryptedKey(
            key_id=metadata.key_id,
            encrypted_data=encrypted,
            key_metadata=metadata,
            integrity_hash=integrity_hash
        )
    
    def _compute_integrity_hash(self, data: bytes) -> str:
        """计算完整性哈希"""
        return hashlib.sha256(data).hexdigest()
    
    def revoke_key(
        self,
        key_id: str,
        revoked_by: str,
        reason: str
    ) -> Tuple[bool, str]:
        """
        吊销密钥
        
        Args:
            key_id: 密钥ID
            revoked_by: 吊销者
            reason: 吊销原因
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if key_id not in self.keys:
                return False, f"密钥 {key_id} 不存在"
            
            encrypted_key = self.keys[key_id]
            encrypted_key.key_metadata.key_status = KeyStatus.REVOKED
            encrypted_key.key_metadata.metadata["revoked_at"] = time.time()
            encrypted_key.key_metadata.metadata["revoked_by"] = revoked_by
            encrypted_key.key_metadata.metadata["revoke_reason"] = reason
            
            self._save_keys()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="KEY_REVOKE",
                user_id=revoked_by,
                details={
                    "key_id": key_id,
                    "reason": reason
                },
                severity="WARNING"
            )
            
            logger.warning(f"用户 {revoked_by} 吊销密钥 {key_id}: {reason}")
            return True, "密钥吊销成功"
            
        except Exception as e:
            logger.error(f"吊销密钥失败: {str(e)}")
            return False, f"吊销密钥失败: {str(e)}"
    
    def rotate_key(
        self,
        key_id: str,
        rotated_by: str,
        archive_old: bool = True
    ) -> Tuple[bool, str, Optional[str]]:
        """
        轮换密钥
        
        Args:
            key_id: 密钥ID
            rotated_by: 轮换者
            archive_old: 是否归档旧密钥
        
        Returns:
            (成功标志, 消息, 新密钥ID)
        """
        try:
            if key_id not in self.keys:
                return False, f"密钥 {key_id} 不存在", None
            
            old_key = self.keys[key_id]
            
            # 根据密钥类型生成新密钥
            new_key_id = f"{key_id}_v{old_key.key_metadata.version + 1}"
            
            if old_key.key_metadata.key_type == KeyType.SYMMETRIC:
                success, msg, _ = self.generate_symmetric_key(
                    key_id=new_key_id,
                    algorithm=old_key.key_metadata.key_algorithm,
                    purpose=old_key.key_metadata.purpose,
                    created_by=rotated_by,
                    description=f"Rotated from {key_id}",
                    tags=old_key.key_metadata.tags
                )
                if not success:
                    return False, f"生成新密钥失败: {msg}", None
            
            elif old_key.key_metadata.key_type == KeyType.ASYMMETRIC:
                success, msg, _ = self.generate_asymmetric_key_pair(
                    key_id=new_key_id,
                    algorithm=old_key.key_metadata.key_algorithm,
                    purpose=old_key.key_metadata.purpose,
                    created_by=rotated_by,
                    description=f"Rotated from {key_id}",
                    tags=old_key.key_metadata.tags
                )
                if not success:
                    return False, f"生成新密钥对失败: {msg}", None
            
            # 更新旧密钥状态
            if archive_old:
                old_key.key_metadata.key_status = KeyStatus.ARCHIVED
            else:
                old_key.key_metadata.key_status = KeyStatus.INACTIVE
            
            old_key.key_metadata.metadata["rotated_at"] = time.time()
            old_key.key_metadata.metadata["rotated_by"] = rotated_by
            old_key.key_metadata.metadata["new_key_id"] = new_key_id
            
            self._save_keys()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="KEY_ROTATE",
                user_id=rotated_by,
                details={
                    "old_key_id": key_id,
                    "new_key_id": new_key_id,
                    "archived": archive_old
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {rotated_by} 轮换密钥 {key_id} -> {new_key_id}")
            return True, "密钥轮换成功", new_key_id
            
        except Exception as e:
            logger.error(f"轮换密钥失败: {str(e)}")
            return False, f"轮换密钥失败: {str(e)}", None
    
    def encrypt_with_key(
        self,
        key_id: str,
        data: bytes,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        使用指定密钥加密数据
        
        Args:
            key_id: 密钥ID
            data: 待加密数据
            context: 上下文信息
        
        Returns:
            加密后的数据
        """
        try:
            key_material = self.get_key_material(key_id)
            if not key_material:
                logger.error(f"无法获取密钥 {key_id}")
                return None
            
            encrypted_key = self.keys[key_id]
            
            if encrypted_key.key_metadata.key_type == KeyType.SYMMETRIC:
                # 对称加密
                f = Fernet(key_material)
                return f.encrypt(data)
            
            elif encrypted_key.key_metadata.key_type == KeyType.ASYMMETRIC:
                # 非对称加密（使用公钥）
                public_key = serialization.load_pem_public_key(
                    key_material,
                    backend=default_backend()
                )
                if isinstance(public_key, rsa.RSAPublicKey):
                    return public_key.encrypt(
                        data,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                else:
                    # EC公钥不能直接加密，需要混合加密
                    logger.error("EC公钥不支持直接加密")
                    return None
            
            else:
                logger.error(f"密钥类型 {encrypted_key.key_metadata.key_type} 不支持加密")
                return None
                
        except Exception as e:
            logger.error(f"使用密钥 {key_id} 加密失败: {str(e)}")
            return None
    
    def decrypt_with_key(
        self,
        key_id: str,
        encrypted_data: bytes,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        使用指定密钥解密数据
        
        Args:
            key_id: 密钥ID
            encrypted_data: 加密数据
            context: 上下文信息
        
        Returns:
            解密后的数据
        """
        try:
            key_material = self.get_key_material(key_id)
            if not key_material:
                logger.error(f"无法获取密钥 {key_id}")
                return None
            
            encrypted_key = self.keys[key_id]
            
            if encrypted_key.key_metadata.key_type == KeyType.SYMMETRIC:
                # 对称解密
                f = Fernet(key_material)
                return f.decrypt(encrypted_data)
            
            elif encrypted_key.key_metadata.key_type == KeyType.ASYMMETRIC:
                # 非对称解密（使用私钥）
                private_key = serialization.load_pem_private_key(
                    key_material,
                    password=None,
                    backend=default_backend()
                )
                if isinstance(private_key, rsa.RSAPrivateKey):
                    return private_key.decrypt(
                        encrypted_data,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                elif isinstance(private_key, ec.EllipticCurvePrivateKey):
                    # EC私钥需要ECDH等协议
                    logger.error("EC私钥不支持直接解密")
                    return None
            
            else:
                logger.error(f"密钥类型 {encrypted_key.key_metadata.key_type} 不支持解密")
                return None
                
        except Exception as e:
            logger.error(f"使用密钥 {key_id} 解密失败: {str(e)}")
            return None
    
    def get_key_info(self, key_id: str) -> Optional[Dict[str, Any]]:
        """获取密钥信息"""
        encrypted_key = self.keys.get(key_id)
        if not encrypted_key:
            return None
        
        metadata = encrypted_key.key_metadata
        return {
            "key_id": metadata.key_id,
            "key_type": metadata.key_type.value,
            "key_algorithm": metadata.key_algorithm.value,
            "key_status": metadata.key_status.value,
            "purpose": [p.value for p in metadata.purpose],
            "created_at": metadata.created_at,
            "created_by": metadata.created_by,
            "expires_at": metadata.expires_at,
            "last_used_at": metadata.last_used_at,
            "version": metadata.version,
            "description": metadata.description,
            "tags": metadata.tags,
            "usage_count": self.key_usage_counter.get(key_id, 0),
            "backup_available": encrypted_key.backup_available
        }
    
    def list_keys(
        self,
        status: Optional[KeyStatus] = None,
        key_type: Optional[KeyType] = None,
        purpose: Optional[KeyPurpose] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        列出符合条件的密钥
        
        Args:
            status: 密钥状态
            key_type: 密钥类型
            purpose: 用途
            tags: 标签
        
        Returns:
            密钥信息列表
        """
        result = []
        
        for key_id, encrypted_key in self.keys.items():
            metadata = encrypted_key.key_metadata
            
            # 应用过滤条件
            if status and metadata.key_status != status:
                continue
            if key_type and metadata.key_type != key_type:
                continue
            if purpose and purpose not in metadata.purpose:
                continue
            if tags and not all(tag in metadata.tags for tag in tags):
                continue
            
            result.append(self.get_key_info(key_id))
        
        return result
    
    def check_expired_keys(self) -> List[str]:
        """
        检查过期密钥
        
        Returns:
            过期密钥ID列表
        """
        expired = []
        current_time = time.time()
        
        for key_id, encrypted_key in self.keys.items():
            expires_at = encrypted_key.key_metadata.expires_at
            if expires_at and expires_at < current_time:
                if encrypted_key.key_metadata.key_status == KeyStatus.ACTIVE:
                    encrypted_key.key_metadata.key_status = KeyStatus.EXPIRED
                    expired.append(key_id)
        
        if expired:
            self._save_keys()
            logger.info(f"发现 {len(expired)} 个过期密钥")
        
        return expired
    
    def check_rotation_due(self) -> List[str]:
        """
        检查需要轮换的密钥
        
        Returns:
            待轮换密钥ID列表
        """
        rotation_due = []
        current_time = time.time()
        
        for key_id, encrypted_key in self.keys.items():
            rotation_due_at = encrypted_key.key_metadata.rotation_due_at
            if rotation_due_at and rotation_due_at < current_time:
                if encrypted_key.key_metadata.key_status == KeyStatus.ACTIVE:
                    encrypted_key.key_metadata.key_status = KeyStatus.PENDING_ROTATION
                    rotation_due.append(key_id)
        
        if rotation_due:
            self._save_keys()
            logger.info(f"发现 {len(rotation_due)} 个需要轮换的密钥")
        
        return rotation_due
    
    async def start_rotation_checker(self):
        """启动自动轮换检查任务"""
        if not self.config["rotation_enabled"]:
            return
        
        async def _rotation_check_loop():
            interval_hours = self.config["rotation_check_interval_hours"]
            
            while True:
                try:
                    # 检查过期密钥
                    expired = self.check_expired_keys()
                    if expired:
                        logger.info(f"自动检查发现过期密钥: {expired}")
                    
                    # 检查待轮换密钥
                    rotation_due = self.check_rotation_due()
                    if rotation_due:
                        logger.info(f"自动检查发现待轮换密钥: {rotation_due}")
                    
                    await asyncio.sleep(interval_hours * 3600)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"自动轮换检查异常: {str(e)}")
                    await asyncio.sleep(3600)  # 出错后1小时重试
        
        self._rotation_check_task = asyncio.create_task(_rotation_check_loop())
        logger.info(f"自动轮换检查任务已启动，间隔 {self.config['rotation_check_interval_hours']} 小时")
    
    async def stop_rotation_checker(self):
        """停止自动轮换检查任务"""
        if self._rotation_check_task:
            self._rotation_check_task.cancel()
            try:
                await self._rotation_check_task
            except asyncio.CancelledError:
                pass
            self._rotation_check_task = None
            logger.info("自动轮换检查任务已停止")
    
    def backup_keys(self, backup_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        备份密钥
        
        Args:
            backup_path: 备份路径
        
        Returns:
            (成功标志, 消息)
        """
        try:
            backup_path = backup_path or str(self.storage_path / "backup")
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出密钥数据
            keys_data = {}
            for key_id, encrypted_key in self.keys.items():
                keys_data[key_id] = {
                    "encrypted_data": base64.b64encode(encrypted_key.encrypted_data).decode(),
                    "integrity_hash": encrypted_key.integrity_hash,
                    "wrapped_by": encrypted_key.wrapped_by
                }
            
            # 添加时间戳
            backup_data = {
                "timestamp": time.time(),
                "key_count": len(self.keys),
                "keys": keys_data
            }
            
            backup_file = backup_dir / f"keys_backup_{int(time.time())}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            # 更新备份状态
            for encrypted_key in self.keys.values():
                encrypted_key.backup_available = True
                encrypted_key.backup_location = str(backup_file)
            
            self._save_keys()
            
            logger.info(f"密钥备份完成: {backup_file}")
            return True, f"备份成功: {backup_file}"
            
        except Exception as e:
            logger.error(f"备份密钥失败: {str(e)}")
            return False, f"备份失败: {str(e)}"
    
    def cleanup_archived_keys(self, days: int = 90) -> int:
        """
        清理归档的旧密钥
        
        Args:
            days: 保留天数
        
        Returns:
            清理数量
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            to_delete = []
            
            for key_id, encrypted_key in self.keys.items():
                metadata = encrypted_key.key_metadata
                if metadata.key_status == KeyStatus.ARCHIVED:
                    # 检查是否超过保留期
                    archived_at = metadata.metadata.get("archived_at", metadata.updated_at)
                    if archived_at < cutoff_time:
                        to_delete.append(key_id)
            
            for key_id in to_delete:
                del self.keys[key_id]
            
            if to_delete:
                self._save_keys()
                logger.info(f"清理了 {len(to_delete)} 个归档密钥")
            
            return len(to_delete)
            
        except Exception as e:
            logger.error(f"清理归档密钥失败: {str(e)}")
            return 0


# 单例实例
_key_management_instance = None


def get_key_management() -> KeyManagement:
    """获取密钥管理器单例实例"""
    global _key_management_instance
    if _key_management_instance is None:
        _key_management_instance = KeyManagement()
    return _key_management_instance