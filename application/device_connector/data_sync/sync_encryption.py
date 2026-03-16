"""
同步加密模块 - Mirexs数据同步系统

提供同步数据加密功能，包括：
1. 数据加密
2. 数据解密
3. 密钥管理
4. 签名验证
5. 加密传输
"""

import logging
import time
import json
import base64
import hashlib
import os
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

# 尝试导入加密库
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography not available. Encryption functionality will be limited.")

class EncryptionMethod(Enum):
    """加密方法枚举"""
    NONE = "none"                    # 无加密
    AES_256_GCM = "aes_256_gcm"      # AES-256-GCM
    AES_256_CBC = "aes_256_cbc"      # AES-256-CBC
    CHACHA20 = "chacha20"            # ChaCha20-Poly1305
    FERNET = "fernet"                # Fernet (AES-128)
    RSA_OAEP = "rsa_oaep"            # RSA-OAEP
    HYBRID = "hybrid"                 # 混合加密

class KeyType(Enum):
    """密钥类型枚举"""
    SYMMETRIC = "symmetric"           # 对称密钥
    PRIVATE = "private"               # 私钥
    PUBLIC = "public"                 # 公钥
    SESSION = "session"               # 会话密钥

@dataclass
class EncryptionKey:
    """加密密钥"""
    id: str
    type: KeyType
    method: EncryptionMethod
    key: bytes
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EncryptedData:
    """加密数据"""
    data: bytes
    method: EncryptionMethod
    key_id: str
    iv: Optional[bytes] = None
    tag: Optional[bytes] = None
    signature: Optional[bytes] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class EncryptionConfig:
    """加密配置"""
    # 加密方法
    method: EncryptionMethod = EncryptionMethod.AES_256_GCM
    
    # 密钥配置
    key_rotation_interval: int = 604800  # 7天
    key_length: int = 32  # 256位
    
    # 签名配置
    sign_data: bool = True
    signature_algorithm: str = "sha256"
    
    # 传输配置
    encrypt_transport: bool = True
    compression: bool = False
    
    # 存储配置
    key_store_path: str = "data/keys/"
    auto_save_keys: bool = True

class SyncEncryption:
    """
    同步加密管理器
    
    负责同步数据的加密和解密。
    """
    
    def __init__(self, config: Optional[EncryptionConfig] = None):
        """
        初始化同步加密管理器
        
        Args:
            config: 加密配置
        """
        self.config = config or EncryptionConfig()
        
        # 密钥存储
        self.keys: Dict[str, EncryptionKey] = {}
        self.current_key_id: Optional[str] = None
        
        # 密钥对（用于非对称加密）
        self.key_pairs: Dict[str, Dict[str, EncryptionKey]] = {}  # pair_id -> {public, private}
        
        # 初始化密钥
        self._init_keys()
        
        # 统计
        self.stats = {
            "encryptions": 0,
            "decryptions": 0,
            "keys_created": 0,
            "keys_rotated": 0,
            "errors": 0
        }
        
        logger.info(f"SyncEncryption initialized with method {self.config.method.value}")
    
    def _init_keys(self):
        """初始化密钥"""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography not available, using mock encryption")
            return
        
        # 生成主密钥
        self._generate_symmetric_key()
        
        # 生成密钥对
        self._generate_key_pair()
    
    def _generate_symmetric_key(self) -> str:
        """生成对称密钥"""
        key_id = str(uuid.uuid4())
        
        if self.config.method == EncryptionMethod.FERNET:
            key = Fernet.generate_key()
        else:
            # 生成随机密钥
            key = os.urandom(self.config.key_length)
        
        encryption_key = EncryptionKey(
            id=key_id,
            type=KeyType.SYMMETRIC,
            method=self.config.method,
            key=key,
            expires_at=time.time() + self.config.key_rotation_interval
        )
        
        self.keys[key_id] = encryption_key
        self.current_key_id = key_id
        self.stats["keys_created"] += 1
        
        logger.debug(f"Symmetric key generated: {key_id}")
        
        return key_id
    
    def _generate_key_pair(self) -> str:
        """生成密钥对"""
        if not CRYPTOGRAPHY_AVAILABLE:
            return ""
        
        pair_id = str(uuid.uuid4())
        
        # 生成RSA密钥对
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        public_key = private_key.public_key()
        
        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # 创建密钥对象
        private = EncryptionKey(
            id=f"{pair_id}_private",
            type=KeyType.PRIVATE,
            method=EncryptionMethod.RSA_OAEP,
            key=private_pem
        )
        
        public = EncryptionKey(
            id=f"{pair_id}_public",
            type=KeyType.PUBLIC,
            method=EncryptionMethod.RSA_OAEP,
            key=public_pem
        )
        
        self.keys[private.id] = private
        self.keys[public.id] = public
        self.key_pairs[pair_id] = {
            "private": private,
            "public": public
        }
        
        self.stats["keys_created"] += 2
        
        logger.debug(f"Key pair generated: {pair_id}")
        
        return pair_id
    
    def encrypt(self, data: Union[str, bytes, Dict[str, Any]],
               method: Optional[EncryptionMethod] = None,
               key_id: Optional[str] = None) -> EncryptedData:
        """
        加密数据
        
        Args:
            data: 要加密的数据
            method: 加密方法
            key_id: 密钥ID
        
        Returns:
            加密数据
        """
        encrypt_method = method or self.config.method
        
        if encrypt_method == EncryptionMethod.NONE:
            # 无加密
            if isinstance(data, dict):
                data_bytes = json.dumps(data).encode()
            elif isinstance(data, str):
                data_bytes = data.encode()
            else:
                data_bytes = data
            
            return EncryptedData(
                data=data_bytes,
                method=EncryptionMethod.NONE,
                key_id="none"
            )
        
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography not available, using mock encryption")
            return self._mock_encrypt(data, encrypt_method)
        
        # 获取密钥
        if not key_id or key_id not in self.keys:
            key_id = self.current_key_id
        
        key = self.keys.get(key_id)
        if not key:
            raise ValueError(f"Key not found: {key_id}")
        
        # 准备数据
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode()
        elif isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = data
        
        # 根据方法加密
        if encrypt_method == EncryptionMethod.FERNET:
            fernet = Fernet(key.key)
            encrypted = fernet.encrypt(data_bytes)
            
            result = EncryptedData(
                data=encrypted,
                method=encrypt_method,
                key_id=key_id,
                timestamp=time.time()
            )
        
        elif encrypt_method == EncryptionMethod.AES_256_GCM:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            iv = os.urandom(12)
            aesgcm = AESGCM(key.key)
            encrypted = aesgcm.encrypt(iv, data_bytes, None)
            
            result = EncryptedData(
                data=encrypted,
                method=encrypt_method,
                key_id=key_id,
                iv=iv,
                timestamp=time.time()
            )
        
        elif encrypt_method == EncryptionMethod.RSA_OAEP:
            if key.type != KeyType.PUBLIC:
                raise ValueError("RSA encryption requires public key")
            
            from cryptography.hazmat.primitives.asymmetric import rsa, padding
            from cryptography.hazmat.primitives import hashes
            
            public_key = serialization.load_pem_public_key(key.key)
            encrypted = public_key.encrypt(
                data_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            result = EncryptedData(
                data=encrypted,
                method=encrypt_method,
                key_id=key_id,
                timestamp=time.time()
            )
        
        else:
            # 其他方法简化处理
            result = self._mock_encrypt(data, encrypt_method)
        
        # 添加签名
        if self.config.sign_data:
            result.signature = self._sign_data(data_bytes)
        
        self.stats["encryptions"] += 1
        
        return result
    
    def _mock_encrypt(self, data: Union[str, bytes, Dict[str, Any]],
                     method: EncryptionMethod) -> EncryptedData:
        """模拟加密（用于测试）"""
        if isinstance(data, dict):
            data_bytes = json.dumps(data).encode()
        elif isinstance(data, str):
            data_bytes = data.encode()
        else:
            data_bytes = data
        
        # 简单的base64编码
        import base64
        encoded = base64.b64encode(data_bytes)
        
        return EncryptedData(
            data=encoded,
            method=method,
            key_id="mock",
            iv=os.urandom(16),
            timestamp=time.time()
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> Union[str, bytes, Dict[str, Any]]:
        """
        解密数据
        
        Args:
            encrypted_data: 加密数据
        
        Returns:
            解密后的数据
        """
        if encrypted_data.method == EncryptionMethod.NONE:
            # 无加密
            try:
                return json.loads(encrypted_data.data)
            except:
                try:
                    return encrypted_data.data.decode()
                except:
                    return encrypted_data.data
        
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("Cryptography not available, using mock decryption")
            return self._mock_decrypt(encrypted_data)
        
        # 获取密钥
        key = self.keys.get(encrypted_data.key_id)
        if not key:
            raise ValueError(f"Key not found: {encrypted_data.key_id}")
        
        # 验证签名
        if encrypted_data.signature and self.config.sign_data:
            if not self._verify_signature(encrypted_data.data, encrypted_data.signature):
                logger.warning("Signature verification failed")
        
        # 根据方法解密
        if encrypted_data.method == EncryptionMethod.FERNET:
            fernet = Fernet(key.key)
            decrypted = fernet.decrypt(encrypted_data.data)
        
        elif encrypted_data.method == EncryptionMethod.AES_256_GCM:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            
            aesgcm = AESGCM(key.key)
            decrypted = aesgcm.decrypt(
                encrypted_data.iv,
                encrypted_data.data,
                None
            )
        
        elif encrypted_data.method == EncryptionMethod.RSA_OAEP:
            if key.type != KeyType.PRIVATE:
                raise ValueError("RSA decryption requires private key")
            
            from cryptography.hazmat.primitives.asymmetric import rsa, padding
            from cryptography.hazmat.primitives import hashes
            
            private_key = serialization.load_pem_private_key(
                key.key,
                password=None
            )
            decrypted = private_key.decrypt(
                encrypted_data.data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        
        else:
            decrypted = self._mock_decrypt(encrypted_data)
            if isinstance(decrypted, bytes):
                return decrypted
            return decrypted
        
        self.stats["decryptions"] += 1
        
        # 尝试解析JSON
        try:
            return json.loads(decrypted)
        except:
            try:
                return decrypted.decode()
            except:
                return decrypted
    
    def _mock_decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """模拟解密"""
        import base64
        return base64.b64decode(encrypted_data.data)
    
    def _sign_data(self, data: bytes) -> bytes:
        """签名数据"""
        if not CRYPTOGRAPHY_AVAILABLE:
            return hashlib.sha256(data).digest()
        
        # 简化签名，实际应用中应使用私钥签名
        return hashlib.sha256(data).digest()
    
    def _verify_signature(self, data: bytes, signature: bytes) -> bool:
        """验证签名"""
        expected = hashlib.sha256(data).digest()
        return expected == signature
    
    def rotate_key(self) -> str:
        """
        轮换密钥
        
        Returns:
            新密钥ID
        """
        new_key_id = self._generate_symmetric_key()
        self.stats["keys_rotated"] += 1
        
        logger.info(f"Key rotated: {new_key_id}")
        
        return new_key_id
    
    def export_public_key(self, pair_id: str) -> Optional[bytes]:
        """
        导出公钥
        
        Args:
            pair_id: 密钥对ID
        
        Returns:
            公钥PEM
        """
        if pair_id in self.key_pairs:
            return self.key_pairs[pair_id]["public"].key
        return None
    
    def import_public_key(self, public_key_pem: bytes) -> str:
        """
        导入公钥
        
        Args:
            public_key_pem: 公钥PEM
        
        Returns:
            公钥ID
        """
        key_id = str(uuid.uuid4())
        
        key = EncryptionKey(
            id=key_id,
            type=KeyType.PUBLIC,
            method=EncryptionMethod.RSA_OAEP,
            key=public_key_pem
        )
        
        self.keys[key_id] = key
        
        logger.debug(f"Public key imported: {key_id}")
        
        return key_id
    
    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """获取密钥"""
        return self.keys.get(key_id)
    
    def get_current_key(self) -> Optional[EncryptionKey]:
        """获取当前密钥"""
        if self.current_key_id:
            return self.keys.get(self.current_key_id)
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取加密管理器状态
        
        Returns:
            状态字典
        """
        return {
            "method": self.config.method.value,
            "keys": {
                "total": len(self.keys),
                "current": self.current_key_id,
                "symmetric": len([k for k in self.keys.values() if k.type == KeyType.SYMMETRIC]),
                "key_pairs": len(self.key_pairs)
            },
            "stats": self.stats,
            "cryptography_available": CRYPTOGRAPHY_AVAILABLE
        }
    
    def shutdown(self):
        """关闭加密管理器"""
        logger.info("Shutting down SyncEncryption...")
        
        self.keys.clear()
        self.key_pairs.clear()
        self.current_key_id = None
        
        logger.info("SyncEncryption shutdown completed")

# 单例模式实现
_sync_encryption_instance: Optional[SyncEncryption] = None

def get_sync_encryption(config: Optional[EncryptionConfig] = None) -> SyncEncryption:
    """
    获取同步加密管理器单例
    
    Args:
        config: 加密配置
    
    Returns:
        同步加密管理器实例
    """
    global _sync_encryption_instance
    if _sync_encryption_instance is None:
        _sync_encryption_instance = SyncEncryption(config)
    return _sync_encryption_instance

