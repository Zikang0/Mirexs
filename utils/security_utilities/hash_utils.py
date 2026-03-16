"""
哈希工具模块

提供各种哈希算法、密钥派生、密码哈希等功能。
"""

import hashlib
import hmac
import secrets
import logging
from datetime import datetime
from typing import Union, Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import base64
import binascii
import pbkdf2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import bcrypt
import argon2
from passlib.context import CryptContext


class HashAlgorithm(Enum):
    """哈希算法枚举"""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"


class KeyDerivationFunction(Enum):
    """密钥派生函数枚举"""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    HKDF = "hkdf"
    ARGON2 = "argon2"


class HashStrength(Enum):
    """哈希强度枚举"""
    FAST = "fast"      # 用于快速验证
    BALANCED = "balanced"  # 平衡性能和安全
    SECURE = "secure"  # 高安全性
    PARANOID = "paranoid"  # 最高安全性


@dataclass
class HashResult:
    """哈希结果数据类"""
    algorithm: str
    hash_value: str
    salt: Optional[str] = None
    iterations: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class KeyDerivationResult:
    """密钥派生结果数据类"""
    kdf_algorithm: str
    derived_key: str
    salt: str
    iterations: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HashUtils:
    """哈希工具类"""
    
    def __init__(self):
        """初始化哈希工具"""
        # 密码哈希上下文
        self.pwd_context = CryptContext(
            schemes=["bcrypt", "argon2", "pbkdf2_sha256"],
            deprecated="auto"
        )
        
        # 哈希强度配置
        self.strength_config = {
            HashStrength.FAST: {
                "pbkdf2_iterations": 100000,
                "argon2_time_cost": 1,
                "argon2_memory_cost": 65536,
                "argon2_parallelism": 1
            },
            HashStrength.BALANCED: {
                "pbkdf2_iterations": 200000,
                "argon2_time_cost": 2,
                "argon2_memory_cost": 131072,
                "argon2_parallelism": 2
            },
            HashStrength.SECURE: {
                "pbkdf2_iterations": 500000,
                "argon2_time_cost": 3,
                "argon2_memory_cost": 262144,
                "argon2_parallelism": 4
            },
            HashStrength.PARANOID: {
                "pbkdf2_iterations": 1000000,
                "argon2_time_cost": 4,
                "argon2_memory_cost": 524288,
                "argon2_parallelism": 8
            }
        }
        
    def basic_hash(self, data: Union[str, bytes], 
                  algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
        """基础哈希
        
        Args:
            data: 待哈希数据
            algorithm: 哈希算法
            
        Returns:
            HashResult: 哈希结果
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        hash_func = getattr(hashlib, algorithm.value)
        hash_obj = hash_func(data)
        hash_value = hash_obj.hexdigest()
        
        return HashResult(
            algorithm=algorithm.value,
            hash_value=hash_value
        )
        
    def hmac_hash(self, data: Union[str, bytes], key: Union[str, bytes],
                 algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
        """HMAC哈希
        
        Args:
            data: 待哈希数据
            key: HMAC密钥
            algorithm: 哈希算法
            
        Returns:
            HashResult: HMAC哈希结果
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        if isinstance(key, str):
            key = key.encode('utf-8')
            
        hash_func = getattr(hashlib, algorithm.value)
        h = hmac.new(key, data, hash_func)
        hash_value = h.hexdigest()
        
        return HashResult(
            algorithm=f"hmac_{algorithm.value}",
            hash_value=hash_value
        )
        
    def salted_hash(self, data: Union[str, bytes], 
                   algorithm: HashAlgorithm = HashAlgorithm.SHA256,
                   salt_length: int = 32) -> HashResult:
        """加盐哈希
        
        Args:
            data: 待哈希数据
            algorithm: 哈希算法
            salt_length: 盐值长度
            
        Returns:
            HashResult: 加盐哈希结果
        """
        # 生成随机盐值
        salt = secrets.token_hex(salt_length)
        
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # 将盐值和数据进行组合
        salted_data = salt.encode('utf-8') + data
        
        # 计算哈希
        hash_func = getattr(hashlib, algorithm.value)
        hash_obj = hash_func(salted_data)
        hash_value = hash_obj.hexdigest()
        
        return HashResult(
            algorithm=f"salted_{algorithm.value}",
            hash_value=hash_value,
            salt=salt
        )
        
    def pbkdf2_hash(self, password: Union[str, bytes], 
                   salt: Optional[Union[str, bytes]] = None,
                   iterations: int = 100000,
                   key_length: int = 32,
                   algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
        """PBKDF2密钥派生
        
        Args:
            password: 密码
            salt: 盐值，为None时自动生成
            iterations: 迭代次数
            key_length: 派生密钥长度
            algorithm: 哈希算法
            
        Returns:
            HashResult: PBKDF2哈希结果
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        if salt is None:
            salt = secrets.token_hex(32)
            
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        # 使用cryptography库的PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=getattr(hashes, algorithm.value.upper()),
            length=key_length,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        derived_key = kdf.derive(password)
        hash_value = base64.b64encode(derived_key).decode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        return HashResult(
            algorithm="pbkdf2",
            hash_value=hash_value,
            salt=salt_b64,
            iterations=iterations
        )
        
    def scrypt_hash(self, password: Union[str, bytes],
                   salt: Optional[Union[str, bytes]] = None,
                   n: int = 16384,  # CPU/memory cost factor
                   r: int = 8,      # block size
                   p: int = 1,      # parallelization factor
                   key_length: int = 32) -> HashResult:
        """Scrypt密钥派生
        
        Args:
            password: 密码
            salt: 盐值，为None时自动生成
            n: CPU/memory cost factor
            r: block size
            p: parallelization factor
            key_length: 派生密钥长度
            
        Returns:
            HashResult: Scrypt哈希结果
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        if salt is None:
            salt = secrets.token_hex(32)
            
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        kdf = Scrypt(
            salt=salt,
            length=key_length,
            n=n,
            r=r,
            p=p,
            backend=default_backend()
        )
        
        derived_key = kdf.derive(password)
        hash_value = base64.b64encode(derived_key).decode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        return HashResult(
            algorithm="scrypt",
            hash_value=hash_value,
            salt=salt_b64,
            iterations=None
        )
        
    def argon2_hash(self, password: Union[str, bytes],
                   salt: Optional[Union[str, bytes]] = None,
                   time_cost: int = 2,
                   memory_cost: int = 131072,
                   parallelism: int = 2) -> HashResult:
        """Argon2哈希
        
        Args:
            password: 密码
            salt: 盐值，为None时自动生成
            time_cost: 时间成本
            memory_cost: 内存成本
            parallelism: 并行度
            
        Returns:
            HashResult: Argon2哈希结果
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        if salt is None:
            salt = secrets.token_hex(32).encode('utf-8')
        elif isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        ph = argon2.PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16
        )
        
        hash_value = ph.hash(password, salt=salt)
        
        return HashResult(
            algorithm="argon2",
            hash_value=hash_value,
            salt=base64.b64encode(salt).decode('utf-8')
        )
        
    def bcrypt_hash(self, password: Union[str, bytes],
                   rounds: int = 12) -> HashResult:
        """Bcrypt哈希
        
        Args:
            password: 密码
            rounds: 成本因子
            
        Returns:
            HashResult: Bcrypt哈希结果
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
            
        hash_value = bcrypt.hashpw(password, bcrypt.gensalt(rounds=rounds)).decode('utf-8')
        
        return HashResult(
            algorithm="bcrypt",
            hash_value=hash_value
        )
        
    def secure_password_hash(self, password: Union[str, bytes],
                           strength: HashStrength = HashStrength.BALANCED) -> HashResult:
        """安全密码哈希
        
        Args:
            password: 密码
            strength: 哈希强度
            
        Returns:
            HashResult: 哈希结果
        """
        config = self.strength_config[strength]
        
        # 优先使用Argon2，如果不可用则使用PBKDF2
        try:
            return self.argon2_hash(
                password,
                time_cost=config["argon2_time_cost"],
                memory_cost=config["argon2_memory_cost"],
                parallelism=config["argon2_parallelism"]
            )
        except Exception:
            return self.pbkdf2_hash(
                password,
                iterations=config["pbkdf2_iterations"]
            )
            
    def verify_password(self, password: Union[str, bytes], 
                       hash_result: HashResult) -> bool:
        """验证密码
        
        Args:
            password: 密码
            hash_result: 哈希结果
            
        Returns:
            bool: 验证结果
        """
        try:
            if hash_result.algorithm == "argon2":
                ph = argon2.PasswordHasher()
                ph.verify(hash_result.hash_value, password)
                return True
            elif hash_result.algorithm == "bcrypt":
                if isinstance(password, str):
                    password = password.encode('utf-8')
                return bcrypt.checkpw(password, hash_result.hash_value.encode('utf-8'))
            elif hash_result.algorithm.startswith("pbkdf2"):
                # 解析PBKDF2结果
                if isinstance(password, str):
                    password = password.encode('utf-8')
                    
                salt = base64.b64decode(hash_result.salt)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=hash_result.iterations or 100000,
                    backend=default_backend()
                )
                
                derived_key = kdf.derive(password)
                expected_hash = base64.b64decode(hash_result.hash_value)
                
                return hmac.compare_digest(derived_key, expected_hash)
            else:
                # 其他算法的验证逻辑
                return False
                
        except Exception as e:
            logging.error(f"密码验证失败: {str(e)}")
            return False
            
    def derive_key(self, password: Union[str, bytes], 
                  salt: Optional[Union[str, bytes]] = None,
                  kdf: KeyDerivationFunction = KeyDerivationFunction.PBKDF2,
                  key_length: int = 32) -> KeyDerivationResult:
        """密钥派生
        
        Args:
            password: 密码
            salt: 盐值
            kdf: 密钥派生函数
            key_length: 派生密钥长度
            
        Returns:
            KeyDerivationResult: 密钥派生结果
        """
        if salt is None:
            salt = secrets.token_hex(32)
            
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        if kdf == KeyDerivationFunction.PBKDF2:
            kdf_obj = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=key_length,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            derived_key = kdf_obj.derive(password)
            
        elif kdf == KeyDerivationFunction.SCRYPT:
            kdf_obj = Scrypt(
                salt=salt,
                length=key_length,
                n=16384,
                r=8,
                p=1,
                backend=default_backend()
            )
            derived_key = kdf_obj.derive(password)
            
        elif kdf == KeyDerivationFunction.HKDF:
            kdf_obj = HKDF(
                algorithm=hashes.SHA256(),
                length=key_length,
                salt=salt,
                info=b"key_derivation",
                backend=default_backend()
            )
            derived_key = kdf_obj.derive(password)
            
        else:
            raise ValueError(f"不支持的KDF算法: {kdf}")
            
        return KeyDerivationResult(
            kdf_algorithm=kdf.value,
            derived_key=base64.b64encode(derived_key).decode('utf-8'),
            salt=base64.b64encode(salt).decode('utf-8')
        )
        
    def hash_file(self, file_path: str, 
                 algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
        """文件哈希
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法
            
        Returns:
            HashResult: 文件哈希结果
        """
        hash_func = getattr(hashlib, algorithm.value)
        hash_obj = hash_func()
        
        try:
            with open(file_path, 'rb') as f:
                # 分块读取大文件
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
                    
            hash_value = hash_obj.hexdigest()
            
            return HashResult(
                algorithm=algorithm.value,
                hash_value=hash_value
            )
            
        except Exception as e:
            logging.error(f"文件哈希计算失败: {str(e)}")
            raise
            
    def generate_salt(self, length: int = 32) -> str:
        """生成随机盐值
        
        Args:
            length: 盐值长度
            
        Returns:
            str: 十六进制盐值
        """
        return secrets.token_hex(length)
        
    def hash_data_multiple(self, data: Union[str, bytes], 
                          algorithms: List[HashAlgorithm]) -> Dict[str, str]:
        """使用多种算法对数据进行哈希
        
        Args:
            data: 待哈希数据
            algorithms: 哈希算法列表
            
        Returns:
            Dict[str, str]: 算法名称到哈希值的映射
        """
        results = {}
        
        for algorithm in algorithms:
            try:
                result = self.basic_hash(data, algorithm)
                results[algorithm.value] = result.hash_value
            except Exception as e:
                logging.error(f"算法 {algorithm.value} 哈希失败: {str(e)}")
                results[algorithm.value] = None
                
        return results
        
    def constant_time_compare(self, a: Union[str, bytes], b: Union[str, bytes]) -> bool:
        """常量时间比较
        
        Args:
            a: 第一个值
            b: 第二个值
            
        Returns:
            bool: 比较结果
        """
        if isinstance(a, str):
            a = a.encode('utf-8')
        if isinstance(b, str):
            b = b.encode('utf-8')
            
        return hmac.compare_digest(a, b)
        
    def hash_to_int(self, hash_value: str, max_value: int) -> int:
        """将哈希值转换为指定范围内的整数
        
        Args:
            hash_value: 哈希值
            max_value: 最大值
            
        Returns:
            int: 转换后的整数
        """
        # 使用哈希值的前8个字节
        hash_bytes = bytes.fromhex(hash_value[:16])
        hash_int = int.from_bytes(hash_bytes, byteorder='big')
        return hash_int % max_value


# 全局哈希工具实例
hash_utils = HashUtils()


def basic_hash(data: Union[str, bytes], 
              algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
    """基础哈希便捷函数"""
    return hash_utils.basic_hash(data, algorithm)


def hmac_hash(data: Union[str, bytes], key: Union[str, bytes],
             algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
    """HMAC哈希便捷函数"""
    return hash_utils.hmac_hash(data, key, algorithm)


def salted_hash(data: Union[str, bytes], 
               algorithm: HashAlgorithm = HashAlgorithm.SHA256,
               salt_length: int = 32) -> HashResult:
    """加盐哈希便捷函数"""
    return hash_utils.salted_hash(data, algorithm, salt_length)


def secure_password_hash(password: Union[str, bytes],
                        strength: HashStrength = HashStrength.BALANCED) -> HashResult:
    """安全密码哈希便捷函数"""
    return hash_utils.secure_password_hash(password, strength)


def verify_password(password: Union[str, bytes], hash_result: HashResult) -> bool:
    """验证密码便捷函数"""
    return hash_utils.verify_password(password, hash_result)


def derive_key(password: Union[str, bytes], 
              salt: Optional[Union[str, bytes]] = None,
              kdf: KeyDerivationFunction = KeyDerivationFunction.PBKDF2,
              key_length: int = 32) -> KeyDerivationResult:
    """密钥派生便捷函数"""
    return hash_utils.derive_key(password, salt, kdf, key_length)


def hash_file(file_path: str, 
             algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> HashResult:
    """文件哈希便捷函数"""
    return hash_utils.hash_file(file_path, algorithm)


def generate_salt(length: int = 32) -> str:
    """生成随机盐值便捷函数"""
    return hash_utils.generate_salt(length)


def constant_time_compare(a: Union[str, bytes], b: Union[str, bytes]) -> bool:
    """常量时间比较便捷函数"""
    return hash_utils.constant_time_compare(a, b)


def hash_data_multiple(data: Union[str, bytes], 
                      algorithms: List[HashAlgorithm]) -> Dict[str, str]:
    """多算法哈希便捷函数"""
    return hash_utils.hash_data_multiple(data, algorithms)