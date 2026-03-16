"""
数据加密模块 - 加密敏感数据
提供多种加密算法的统一接口，支持字段级加密、文件加密和数据库加密
"""

import os
import logging
import base64
import hashlib
import json
import time
from typing import Dict, Any, Optional, Union, Tuple, List
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from ...utils.security_utilities.encryption_utils import EncryptionUtils
from ..access_control.key_management import KeyAlgorithm, KeyManagement, KeyPurpose, KeyType, get_key_management
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """加密算法枚举"""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    RSA_OAEP = "rsa-oaep"
    FERNET = "fernet"


class EncryptionMode(Enum):
    """加密模式枚举"""
    FIELD_LEVEL = "field_level"  # 字段级加密
    RECORD_LEVEL = "record_level"  # 记录级加密
    TABLE_LEVEL = "table_level"  # 表级加密
    FILE_LEVEL = "file_level"  # 文件级加密
    DATABASE_LEVEL = "database_level"  # 数据库级加密


@dataclass
class EncryptionKey:
    """加密密钥信息"""
    key_id: str
    algorithm: EncryptionAlgorithm
    key_material: bytes
    created_at: float
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = None


@dataclass
class EncryptedData:
    """加密数据容器"""
    data: bytes
    key_id: str
    algorithm: EncryptionAlgorithm
    iv: Optional[bytes] = None  # 初始化向量
    tag: Optional[bytes] = None  # 认证标签
    created_at: float = None
    metadata: Dict[str, Any] = None


class DataEncryption:
    """
    数据加密管理器
    提供统一的加密解密接口，支持多种加密算法和模式
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据加密管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 初始化依赖
        self.key_management = get_key_management()
        self.audit_logger = AuditLogger()
        self.encryption_utils = EncryptionUtils()
        
        # 加密上下文缓存
        self._cipher_cache: Dict[str, Any] = {}
        
        # 默认加密算法
        self.default_algorithm = EncryptionAlgorithm(
            self.config.get("default_algorithm", "aes-256-gcm")
        )
        
        # 加密密钥轮换策略
        self.key_rotation_days = self.config.get("key_rotation_days", 90)
        
        # 初始化主加密密钥
        self._master_key_id = self.config.get("master_key_id", "data_encryption_master")
        self._ensure_master_key()
        
        logger.info(f"数据加密管理器初始化完成，默认算法: {self.default_algorithm.value}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "default_algorithm": "aes-256-gcm",
            "key_rotation_days": 90,
            "master_key_id": "data_encryption_master",
            "enable_field_level_encryption": True,
            "enable_database_encryption": True,
            "encryption_key_cache_size": 100,
            "key_derivation_iterations": 100000,
            "encrypted_fields": [
                "password",
                "credit_card",
                "ssn",
                "phone_number",
                "email",
                "address",
                "personal_notes"
            ]
        }
    
    def _ensure_master_key(self) -> None:
        """确保主加密密钥存在"""
        master_key = self.key_management.get_key(self._master_key_id)
        if not master_key:
            # 生成主密钥
            self.key_management.generate_symmetric_key(
                key_id=self._master_key_id,
                algorithm=KeyAlgorithm.AES_256,
                purpose=["encryption"],
                created_by="system",
                description="Data encryption master key",
                expiry_days=self.key_rotation_days * 3  # 主密钥有效期更长
            )
            logger.info(f"生成数据加密主密钥: {self._master_key_id}")
    
    def encrypt_field(
        self,
        data: Union[str, bytes, Dict, List],
        field_name: Optional[str] = None,
        key_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[EncryptedData], str]:
        """
        加密字段数据
        
        Args:
            data: 待加密数据
            field_name: 字段名称
            key_id: 密钥ID
            context: 上下文信息
        
        Returns:
            (成功标志, 加密数据, 消息)
        """
        try:
            # 序列化数据
            if isinstance(data, (dict, list)):
                data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, str):
                data_bytes = data.encode('utf-8')
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                return False, None, f"不支持的数据类型: {type(data)}"
            
            # 获取加密密钥
            if not key_id:
                key_id = self._get_key_for_field(field_name)
            
            key_material = self.key_management.get_key_material(key_id)
            if not key_material:
                return False, None, f"无法获取密钥: {key_id}"
            
            # 获取密钥信息
            key_info = self.key_management.get_key(key_id)
            if not key_info:
                return False, None, f"密钥信息不存在: {key_id}"
            
            # 根据算法选择加密方式
            algorithm = self._get_algorithm_for_key(key_id)
            
            # 生成随机IV
            iv = os.urandom(12) if algorithm in [EncryptionAlgorithm.AES_256_GCM, EncryptionAlgorithm.CHACHA20_POLY1305] else os.urandom(16)
            
            # 执行加密
            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                cipher = Cipher(
                    algorithms.AES(key_material),
                    modes.GCM(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                encrypted_data = encryptor.update(data_bytes) + encryptor.finalize()
                tag = encryptor.tag
                
            elif algorithm == EncryptionAlgorithm.AES_256_CBC:
                cipher = Cipher(
                    algorithms.AES(key_material),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                # PKCS7填充
                padded_data = self._pad_pkcs7(data_bytes, 16)
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
                tag = None
                
            elif algorithm == EncryptionAlgorithm.FERNET:
                f = Fernet(base64.urlsafe_b64encode(key_material))
                encrypted_data = f.encrypt(data_bytes)
                iv = None
                tag = None
                
            else:
                return False, None, f"不支持的加密算法: {algorithm}"
            
            # 创建加密数据容器
            encrypted = EncryptedData(
                data=encrypted_data,
                key_id=key_id,
                algorithm=algorithm,
                iv=iv,
                tag=tag if 'tag' in locals() else None,
                created_at=time.time(),
                metadata={
                    "field_name": field_name,
                    "data_type": type(data).__name__,
                    "context": context or {}
                }
            )
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="DATA_ENCRYPT",
                user_id=context.get("user_id") if context else None,
                details={
                    "field_name": field_name,
                    "key_id": key_id,
                    "algorithm": algorithm.value,
                    "data_size": len(data_bytes)
                },
                severity="INFO"
            )
            
            logger.debug(f"字段 {field_name} 加密成功，使用密钥 {key_id}")
            return True, encrypted, "加密成功"
            
        except Exception as e:
            logger.error(f"字段加密失败: {str(e)}")
            return False, None, f"加密失败: {str(e)}"
    
    def decrypt_field(
        self,
        encrypted_data: EncryptedData,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Union[str, bytes, Dict, List]], str]:
        """
        解密字段数据
        
        Args:
            encrypted_data: 加密数据容器
            context: 上下文信息
        
        Returns:
            (成功标志, 解密数据, 消息)
        """
        try:
            # 获取解密密钥
            key_material = self.key_management.get_key_material(encrypted_data.key_id)
            if not key_material:
                return False, None, f"无法获取密钥: {encrypted_data.key_id}"
            
            # 根据算法选择解密方式
            if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM:
                cipher = Cipher(
                    algorithms.AES(key_material),
                    modes.GCM(encrypted_data.iv, encrypted_data.tag),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted_data = decryptor.update(encrypted_data.data) + decryptor.finalize()
                
            elif encrypted_data.algorithm == EncryptionAlgorithm.AES_256_CBC:
                cipher = Cipher(
                    algorithms.AES(key_material),
                    modes.CBC(encrypted_data.iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                padded_data = decryptor.update(encrypted_data.data) + decryptor.finalize()
                decrypted_data = self._unpad_pkcs7(padded_data)
                
            elif encrypted_data.algorithm == EncryptionAlgorithm.FERNET:
                f = Fernet(base64.urlsafe_b64encode(key_material))
                decrypted_data = f.decrypt(encrypted_data.data)
                
            else:
                return False, None, f"不支持的加密算法: {encrypted_data.algorithm}"
            
            # 反序列化数据
            field_name = encrypted_data.metadata.get("field_name") if encrypted_data.metadata else None
            data_type = encrypted_data.metadata.get("data_type") if encrypted_data.metadata else "str"
            
            try:
                if data_type == "dict":
                    result = json.loads(decrypted_data.decode('utf-8'))
                elif data_type == "list":
                    result = json.loads(decrypted_data.decode('utf-8'))
                elif data_type == "str":
                    result = decrypted_data.decode('utf-8')
                else:
                    result = decrypted_data
            except:
                result = decrypted_data
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="DATA_DECRYPT",
                user_id=context.get("user_id") if context else None,
                details={
                    "field_name": field_name,
                    "key_id": encrypted_data.key_id,
                    "algorithm": encrypted_data.algorithm.value
                },
                severity="INFO"
            )
            
            logger.debug(f"字段 {field_name} 解密成功")
            return True, result, "解密成功"
            
        except Exception as e:
            logger.error(f"字段解密失败: {str(e)}")
            return False, None, f"解密失败: {str(e)}"
    
    def encrypt_file(
        self,
        file_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        key_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Path], str]:
        """
        加密文件
        
        Args:
            file_path: 源文件路径
            output_path: 输出文件路径
            key_id: 密钥ID
            context: 上下文信息
        
        Returns:
            (成功标志, 输出文件路径, 消息)
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False, None, f"文件不存在: {file_path}"
            
            # 确定输出路径
            if not output_path:
                output_path = file_path.with_suffix(file_path.suffix + '.encrypted')
            else:
                output_path = Path(output_path)
            
            # 读取文件
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 加密文件数据
            success, encrypted, message = self.encrypt_field(
                data=file_data,
                field_name=f"file:{file_path.name}",
                key_id=key_id,
                context=context
            )
            
            if not success:
                return False, None, message
            
            # 保存加密文件
            with open(output_path, 'wb') as f:
                # 写入加密元数据
                metadata = {
                    "version": 1,
                    "original_name": file_path.name,
                    "original_size": len(file_data),
                    "encrypted_data": {
                        "key_id": encrypted.key_id,
                        "algorithm": encrypted.algorithm.value,
                        "iv": base64.b64encode(encrypted.iv).decode() if encrypted.iv else None,
                        "tag": base64.b64encode(encrypted.tag).decode() if encrypted.tag else None,
                        "created_at": encrypted.created_at
                    }
                }
                
                metadata_bytes = json.dumps(metadata).encode('utf-8')
                metadata_len = len(metadata_bytes)
                
                # 格式: [元数据长度(4字节)][元数据][加密数据]
                f.write(metadata_len.to_bytes(4, byteorder='big'))
                f.write(metadata_bytes)
                f.write(encrypted.data)
            
            logger.info(f"文件加密成功: {file_path} -> {output_path}")
            return True, output_path, "文件加密成功"
            
        except Exception as e:
            logger.error(f"文件加密失败: {str(e)}")
            return False, None, f"文件加密失败: {str(e)}"
    
    def decrypt_file(
        self,
        file_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[Path], str]:
        """
        解密文件
        
        Args:
            file_path: 加密文件路径
            output_path: 输出文件路径
            context: 上下文信息
        
        Returns:
            (成功标志, 输出文件路径, 消息)
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False, None, f"文件不存在: {file_path}"
            
            # 读取加密文件
            with open(file_path, 'rb') as f:
                # 读取元数据长度
                metadata_len_bytes = f.read(4)
                if len(metadata_len_bytes) < 4:
                    return False, None, "无效的加密文件格式"
                
                metadata_len = int.from_bytes(metadata_len_bytes, byteorder='big')
                
                # 读取元数据
                metadata_bytes = f.read(metadata_len)
                if len(metadata_bytes) < metadata_len:
                    return False, None, "无效的加密文件格式"
                
                metadata = json.loads(metadata_bytes.decode('utf-8'))
                
                # 读取加密数据
                encrypted_data = f.read()
            
            # 重建加密数据容器
            encrypted = EncryptedData(
                data=encrypted_data,
                key_id=metadata["encrypted_data"]["key_id"],
                algorithm=EncryptionAlgorithm(metadata["encrypted_data"]["algorithm"]),
                iv=base64.b64decode(metadata["encrypted_data"]["iv"]) if metadata["encrypted_data"]["iv"] else None,
                tag=base64.b64decode(metadata["encrypted_data"]["tag"]) if metadata["encrypted_data"]["tag"] else None,
                created_at=metadata["encrypted_data"]["created_at"]
            )
            
            # 解密数据
            success, decrypted_data, message = self.decrypt_field(
                encrypted_data=encrypted,
                context=context
            )
            
            if not success:
                return False, None, message
            
            # 确定输出路径
            if not output_path:
                output_path = file_path.with_suffix('')  # 移除.encrypted后缀
                if output_path == file_path:
                    output_path = file_path.with_name(f"decrypted_{file_path.name}")
            else:
                output_path = Path(output_path)
            
            # 保存解密文件
            with open(output_path, 'wb') as f:
                if isinstance(decrypted_data, bytes):
                    f.write(decrypted_data)
                else:
                    f.write(decrypted_data.encode('utf-8'))
            
            logger.info(f"文件解密成功: {file_path} -> {output_path}")
            return True, output_path, "文件解密成功"
            
        except Exception as e:
            logger.error(f"文件解密失败: {str(e)}")
            return False, None, f"文件解密失败: {str(e)}"
    
    def encrypt_database_field(
        self,
        table_name: str,
        field_name: str,
        value: Any,
        record_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str], str]:
        """
        加密数据库字段（返回Base64编码的加密字符串）
        
        Args:
            table_name: 表名
            field_name: 字段名
            value: 字段值
            record_id: 记录ID
            context: 上下文信息
        
        Returns:
            (成功标志, 加密字符串, 消息)
        """
        try:
            # 获取表专用的加密密钥
            key_id = f"db_{table_name}_{field_name}"
            
            # 加密字段
            success, encrypted, message = self.encrypt_field(
                data=value,
                field_name=f"{table_name}.{field_name}",
                key_id=key_id,
                context={**(context or {}), "record_id": record_id}
            )
            
            if not success:
                return False, None, message
            
            # 序列化加密数据为字符串
            encrypted_dict = {
                "v": 1,  # 版本
                "k": encrypted.key_id,
                "a": encrypted.algorithm.value,
                "d": base64.b64encode(encrypted.data).decode('utf-8'),
                "i": base64.b64encode(encrypted.iv).decode('utf-8') if encrypted.iv else None,
                "t": base64.b64encode(encrypted.tag).decode('utf-8') if encrypted.tag else None,
                "c": encrypted.created_at
            }
            
            encrypted_str = json.dumps(encrypted_dict, separators=(',', ':'))
            
            logger.debug(f"数据库字段 {table_name}.{field_name} 加密成功")
            return True, encrypted_str, "加密成功"
            
        except Exception as e:
            logger.error(f"数据库字段加密失败: {str(e)}")
            return False, None, f"数据库字段加密失败: {str(e)}"
    
    def decrypt_database_field(
        self,
        encrypted_str: str,
        table_name: Optional[str] = None,
        field_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, str]:
        """
        解密数据库字段
        
        Args:
            encrypted_str: 加密字符串
            table_name: 表名
            field_name: 字段名
            context: 上下文信息
        
        Returns:
            (成功标志, 解密值, 消息)
        """
        try:
            # 解析加密字符串
            encrypted_dict = json.loads(encrypted_str)
            
            # 重建加密数据容器
            encrypted = EncryptedData(
                data=base64.b64decode(encrypted_dict["d"]),
                key_id=encrypted_dict["k"],
                algorithm=EncryptionAlgorithm(encrypted_dict["a"]),
                iv=base64.b64decode(encrypted_dict["i"]) if encrypted_dict.get("i") else None,
                tag=base64.b64decode(encrypted_dict["t"]) if encrypted_dict.get("t") else None,
                created_at=encrypted_dict.get("c", time.time())
            )
            
            # 解密数据
            success, decrypted_value, message = self.decrypt_field(
                encrypted_data=encrypted,
                context={**(context or {}), "table_name": table_name, "field_name": field_name}
            )
            
            if not success:
                return False, None, message
            
            return True, decrypted_value, "解密成功"
            
        except Exception as e:
            logger.error(f"数据库字段解密失败: {str(e)}")
            return False, None, f"数据库字段解密失败: {str(e)}"
    
    def rotate_encryption_keys(
        self,
        days_threshold: Optional[int] = None,
        rotated_by: str = "system"
    ) -> Dict[str, Any]:
        """
        轮换加密密钥
        
        Args:
            days_threshold: 过期天数阈值
            rotated_by: 轮换者
        
        Returns:
            轮换结果统计
        """
        try:
            days = days_threshold or self.key_rotation_days
            threshold_time = time.time() - (days * 24 * 3600)
            
            result = {
                "rotated_keys": [],
                "failed_keys": [],
                "total_keys": 0
            }
            
            # 获取所有加密密钥
            keys = self.key_management.list_keys(
                key_type=KeyType.SYMMETRIC,
                purpose=[KeyPurpose.ENCRYPTION]
            )
            
            for key_info in keys:
                result["total_keys"] += 1
                key_id = key_info["key_id"]
                
                # 检查是否需要轮换
                created_at = key_info["created_at"]
                if created_at < threshold_time and key_id != self._master_key_id:
                    try:
                        # 轮换密钥
                        success, message, new_key_id = self.key_management.rotate_key(
                            key_id=key_id,
                            rotated_by=rotated_by,
                            archive_old=True
                        )
                        
                        if success:
                            result["rotated_keys"].append({
                                "old_key": key_id,
                                "new_key": new_key_id
                            })
                            logger.info(f"密钥轮换成功: {key_id} -> {new_key_id}")
                        else:
                            result["failed_keys"].append({
                                "key_id": key_id,
                                "reason": message
                            })
                            
                    except Exception as e:
                        result["failed_keys"].append({
                            "key_id": key_id,
                            "reason": str(e)
                        })
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="KEY_ROTATION",
                user_id=rotated_by,
                details=result,
                severity="INFO"
            )
            
            logger.info(f"密钥轮换完成: {len(result['rotated_keys'])} 成功, {len(result['failed_keys'])} 失败")
            return result
            
        except Exception as e:
            logger.error(f"密钥轮换失败: {str(e)}")
            return {
                "error": str(e),
                "rotated_keys": [],
                "failed_keys": [],
                "total_keys": 0
            }
    
    def _get_key_for_field(self, field_name: Optional[str]) -> str:
        """获取字段使用的加密密钥"""
        if field_name and field_name in self.config["encrypted_fields"]:
            return f"field_key_{field_name}"
        return self._master_key_id
    
    def _get_algorithm_for_key(self, key_id: str) -> EncryptionAlgorithm:
        """获取密钥对应的加密算法"""
        key_info = self.key_management.get_key(key_id)
        if key_info and key_info.key_metadata.key_algorithm:
            # 映射密钥算法到加密算法
            alg_map = {
                KeyAlgorithm.AES_256: EncryptionAlgorithm.AES_256_GCM,
                KeyAlgorithm.AES_128: EncryptionAlgorithm.AES_256_GCM,
            }
            return alg_map.get(key_info.key_metadata.key_algorithm, self.default_algorithm)
        return self.default_algorithm
    
    def _pad_pkcs7(self, data: bytes, block_size: int) -> bytes:
        """PKCS7填充"""
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def _unpad_pkcs7(self, data: bytes) -> bytes:
        """移除PKCS7填充"""
        padding_length = data[-1]
        return data[:-padding_length]
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """获取加密统计信息"""
        return {
            "default_algorithm": self.default_algorithm.value,
            "master_key_id": self._master_key_id,
            "key_rotation_days": self.key_rotation_days,
            "encrypted_fields_count": len(self.config["encrypted_fields"]),
            "encrypted_fields": self.config["encrypted_fields"],
            "algorithms_supported": [alg.value for alg in EncryptionAlgorithm]
        }


# 单例实例
_data_encryption_instance = None


def get_data_encryption() -> DataEncryption:
    """获取数据加密管理器单例实例"""
    global _data_encryption_instance
    if _data_encryption_instance is None:
        _data_encryption_instance = DataEncryption()
    return _data_encryption_instance

