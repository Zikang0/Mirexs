"""
安全飞地模块 - 提供安全存储区域
实现隔离的安全存储环境，用于保护高度敏感的数据
"""

import logging
import time
import json
import os
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend

from ..access_control.key_management import KeyManagement, get_key_management
from ..security_monitoring.audit_logger import AuditLogger
from ...utils.security_utilities.encryption_utils import EncryptionUtils

logger = logging.getLogger(__name__)


class EnclaveType(Enum):
    """飞地类型枚举"""
    MEMORY = "memory"  # 内存飞地（进程隔离）
    FILE = "file"  # 文件飞地（加密文件）
    DATABASE = "database"  # 数据库飞地（加密表）
    HARDWARE = "hardware"  # 硬件飞地（TPM/SGX）


class EnclaveAccess(Enum):
    """飞地访问级别枚举"""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    ADMIN_ONLY = "admin_only"


@dataclass
class EnclaveData:
    """飞地数据"""
    data_id: str
    encrypted_data: bytes
    metadata: Dict[str, Any]
    created_at: float
    updated_at: float
    access_count: int = 0
    last_accessed: Optional[float] = None


@dataclass
class SecureEnclaveConfig:
    """安全飞地配置"""
    enclave_id: str
    enclave_type: EnclaveType
    path: Optional[Path] = None
    max_size: int = 1024 * 1024 * 100  # 100MB
    encryption_algorithm: str = "AES-256-GCM"
    auto_cleanup_days: int = 30
    access_logging: bool = True


class SecureEnclave:
    """
    安全飞地 - 提供隔离的安全存储环境
    用于存储高度敏感数据，如密钥、证书、生物特征模板等
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化安全飞地
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 飞地配置
        self.enclaves: Dict[str, SecureEnclaveConfig] = {}
        
        # 飞地数据存储
        self.data_store: Dict[str, Dict[str, EnclaveData]] = {}  # enclave_id -> {data_id -> data}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/enclave"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.key_management = get_key_management()
        self.audit_logger = AuditLogger()
        self.encryption_utils = EncryptionUtils()
        
        # 飞地主密钥
        self.master_key_id = self.config.get("master_key_id", "enclave_master_key")
        self._ensure_master_key()
        
        # 加载飞地数据
        self._load_enclaves()
        
        logger.info(f"安全飞地初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/enclave",
            "master_key_id": "enclave_master_key",
            "default_enclave_type": "file",
            "max_enclaves": 10,
            "max_data_per_enclave": 1000,
            "memory_enclave_size": 1024 * 1024 * 10,  # 10MB
            "file_enclave_size": 1024 * 1024 * 100,  # 100MB
            "auto_cleanup_enabled": True,
            "cleanup_interval_hours": 24,
            "access_audit_enabled": True
        }
    
    def _ensure_master_key(self) -> None:
        """确保飞地主密钥存在"""
        master_key = self.key_management.get_key(self.master_key_id)
        if not master_key:
            self.key_management.generate_symmetric_key(
                key_id=self.master_key_id,
                algorithm=KeyAlgorithm.AES_256,
                purpose=["encryption"],
                created_by="system",
                description="Secure enclave master key",
                expiry_days=365
            )
            logger.info(f"生成安全飞地主密钥: {self.master_key_id}")
    
    def _load_enclaves(self) -> None:
        """从存储加载飞地配置"""
        try:
            config_file = self.storage_path / "enclaves.json"
            if not config_file.exists():
                return
            
            with open(config_file, 'r', encoding='utf-8') as f:
                enclaves_data = json.load(f)
            
            for enclave_id, enclave_dict in enclaves_data.items():
                enclave_dict["enclave_type"] = EnclaveType(enclave_dict["enclave_type"])
                if enclave_dict.get("path"):
                    enclave_dict["path"] = Path(enclave_dict["path"])
                self.enclaves[enclave_id] = SecureEnclaveConfig(**enclave_dict)
            
            # 加载飞地数据
            data_file = self.storage_path / "data.json"
            if data_file.exists():
                with open(data_file, 'r', encoding='utf-8') as f:
                    data_dict = json.load(f)
                    for enclave_id, enclave_data in data_dict.items():
                        if enclave_id not in self.data_store:
                            self.data_store[enclave_id] = {}
                        for data_id, data_item in enclave_data.items():
                            data_item["encrypted_data"] = base64.b64decode(data_item["encrypted_data"])
                            self.data_store[enclave_id][data_id] = EnclaveData(**data_item)
            
            logger.info(f"加载了 {len(self.enclaves)} 个安全飞地")
        except Exception as e:
            logger.error(f"加载安全飞地失败: {str(e)}")
    
    def _save_enclaves(self) -> None:
        """保存飞地配置到存储"""
        try:
            enclaves_data = {}
            for enclave_id, enclave in self.enclaves.items():
                enclave_dict = {
                    "enclave_id": enclave.enclave_id,
                    "enclave_type": enclave.enclave_type.value,
                    "path": str(enclave.path) if enclave.path else None,
                    "max_size": enclave.max_size,
                    "encryption_algorithm": enclave.encryption_algorithm,
                    "auto_cleanup_days": enclave.auto_cleanup_days,
                    "access_logging": enclave.access_logging
                }
                enclaves_data[enclave_id] = enclave_dict
            
            with open(self.storage_path / "enclaves.json", 'w', encoding='utf-8') as f:
                json.dump(enclaves_data, f, ensure_ascii=False, indent=2)
            
            # 保存数据
            data_dict = {}
            for enclave_id, enclave_data in self.data_store.items():
                data_dict[enclave_id] = {}
                for data_id, data in enclave_data.items():
                    data_dict[enclave_id][data_id] = {
                        "data_id": data.data_id,
                        "encrypted_data": base64.b64encode(data.encrypted_data).decode(),
                        "metadata": data.metadata,
                        "created_at": data.created_at,
                        "updated_at": data.updated_at,
                        "access_count": data.access_count,
                        "last_accessed": data.last_accessed
                    }
            
            with open(self.storage_path / "data.json", 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.enclaves)} 个安全飞地")
        except Exception as e:
            logger.error(f"保存安全飞地失败: {str(e)}")
    
    def create_enclave(
        self,
        enclave_id: str,
        enclave_type: EnclaveType = EnclaveType.FILE,
        max_size: Optional[int] = None,
        auto_cleanup_days: int = 30,
        created_by: str = "system"
    ) -> Tuple[bool, str, Optional[SecureEnclaveConfig]]:
        """
        创建安全飞地
        
        Args:
            enclave_id: 飞地ID
            enclave_type: 飞地类型
            max_size: 最大大小
            auto_cleanup_days: 自动清理天数
            created_by: 创建者
        
        Returns:
            (成功标志, 消息, 飞地配置)
        """
        try:
            if enclave_id in self.enclaves:
                return False, f"飞地ID已存在: {enclave_id}", None
            
            if len(self.enclaves) >= self.config["max_enclaves"]:
                return False, f"已达到最大飞地数量限制 ({self.config['max_enclaves']})", None
            
            # 确定最大大小
            if max_size is None:
                if enclave_type == EnclaveType.MEMORY:
                    max_size = self.config["memory_enclave_size"]
                else:
                    max_size = self.config["file_enclave_size"]
            
            # 创建飞地路径
            enclave_path = None
            if enclave_type == EnclaveType.FILE:
                enclave_path = self.storage_path / enclave_id
                enclave_path.mkdir(parents=True, exist_ok=True)
            elif enclave_type == EnclaveType.DATABASE:
                enclave_path = self.storage_path / f"{enclave_id}.db"
            
            enclave = SecureEnclaveConfig(
                enclave_id=enclave_id,
                enclave_type=enclave_type,
                path=enclave_path,
                max_size=max_size,
                auto_cleanup_days=auto_cleanup_days,
                access_logging=self.config["access_audit_enabled"]
            )
            
            self.enclaves[enclave_id] = enclave
            self.data_store[enclave_id] = {}
            
            self._save_enclaves()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="ENCLAVE_CREATE",
                user_id=created_by,
                details={
                    "enclave_id": enclave_id,
                    "enclave_type": enclave_type.value,
                    "max_size": max_size
                },
                severity="INFO"
            )
            
            logger.info(f"创建安全飞地: {enclave_id} ({enclave_type.value})")
            return True, "安全飞地创建成功", enclave
            
        except Exception as e:
            logger.error(f"创建安全飞地失败: {str(e)}")
            return False, f"创建失败: {str(e)}", None
    
    def store_data(
        self,
        enclave_id: str,
        data_id: str,
        data: Any,
        metadata: Optional[Dict[str, Any]] = None,
        access_level: EnclaveAccess = EnclaveAccess.READ_WRITE,
        stored_by: str = "system"
    ) -> Tuple[bool, str]:
        """
        在飞地中存储数据
        
        Args:
            enclave_id: 飞地ID
            data_id: 数据ID
            data: 要存储的数据
            metadata: 元数据
            access_level: 访问级别
            stored_by: 存储者
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if enclave_id not in self.enclaves:
                return False, f"飞地不存在: {enclave_id}"
            
            enclave = self.enclaves[enclave_id]
            
            # 检查大小限制
            current_size = self._get_enclave_size(enclave_id)
            data_size = len(str(data)) if isinstance(data, str) else len(json.dumps(data))
            
            if current_size + data_size > enclave.max_size:
                return False, f"飞地存储空间不足 (已用: {current_size}, 最大: {enclave.max_size})"
            
            # 检查数据数量限制
            if enclave_id in self.data_store:
                if len(self.data_store[enclave_id]) >= self.config["max_data_per_enclave"]:
                    return False, f"飞地数据数量已达到上限 ({self.config['max_data_per_enclave']})"
            
            # 序列化数据
            if isinstance(data, (dict, list)):
                serialized = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, str):
                serialized = data.encode('utf-8')
            elif isinstance(data, bytes):
                serialized = data
            else:
                serialized = str(data).encode('utf-8')
            
            # 加密数据
            encrypted = self._encrypt_for_enclave(serialized, enclave_id)
            
            # 创建或更新数据
            now = time.time()
            
            if enclave_id in self.data_store and data_id in self.data_store[enclave_id]:
                # 更新现有数据
                existing = self.data_store[enclave_id][data_id]
                existing.encrypted_data = encrypted
                existing.metadata = metadata or {}
                existing.updated_at = now
                existing.metadata["updated_by"] = stored_by
                existing.metadata["access_level"] = access_level.value
            else:
                # 创建新数据
                enclave_data = EnclaveData(
                    data_id=data_id,
                    encrypted_data=encrypted,
                    metadata=metadata or {},
                    created_at=now,
                    updated_at=now
                )
                enclave_data.metadata["created_by"] = stored_by
                enclave_data.metadata["access_level"] = access_level.value
                
                if enclave_id not in self.data_store:
                    self.data_store[enclave_id] = {}
                self.data_store[enclave_id][data_id] = enclave_data
            
            self._save_enclaves()
            
            # 记录审计日志
            if enclave.access_logging:
                self.audit_logger.log_event(
                    event_type="ENCLAVE_STORE",
                    user_id=stored_by,
                    details={
                        "enclave_id": enclave_id,
                        "data_id": data_id,
                        "data_size": data_size
                    },
                    severity="INFO"
                )
            
            logger.debug(f"数据已存储到飞地 {enclave_id}: {data_id}")
            return True, "数据存储成功"
            
        except Exception as e:
            logger.error(f"存储数据到飞地失败: {str(e)}")
            return False, f"存储失败: {str(e)}"
    
    def retrieve_data(
        self,
        enclave_id: str,
        data_id: str,
        access_level: EnclaveAccess = EnclaveAccess.READ_ONLY,
        requested_by: str = "system"
    ) -> Tuple[bool, Optional[Any], str]:
        """
        从飞地检索数据
        
        Args:
            enclave_id: 飞地ID
            data_id: 数据ID
            access_level: 请求的访问级别
            requested_by: 请求者
        
        Returns:
            (成功标志, 数据, 消息)
        """
        try:
            if enclave_id not in self.enclaves:
                return False, None, f"飞地不存在: {enclave_id}"
            
            enclave = self.enclaves[enclave_id]
            
            if enclave_id not in self.data_store or data_id not in self.data_store[enclave_id]:
                return False, None, f"数据不存在: {data_id}"
            
            data = self.data_store[enclave_id][data_id]
            
            # 检查访问权限
            stored_level = data.metadata.get("access_level", EnclaveAccess.READ_WRITE.value)
            if stored_level == EnclaveAccess.ADMIN_ONLY.value and requested_by != "admin":
                return False, None, "访问被拒绝: 需要管理员权限"
            
            if access_level == EnclaveAccess.WRITE_ONLY and stored_level == EnclaveAccess.READ_ONLY:
                return False, None, "访问被拒绝: 数据为只读"
            
            # 解密数据
            decrypted = self._decrypt_from_enclave(data.encrypted_data, enclave_id)
            
            # 尝试反序列化
            try:
                result = json.loads(decrypted.decode('utf-8'))
            except:
                try:
                    result = decrypted.decode('utf-8')
                except:
                    result = decrypted
            
            # 更新访问统计
            data.access_count += 1
            data.last_accessed = time.time()
            
            self._save_enclaves()
            
            # 记录审计日志
            if enclave.access_logging:
                self.audit_logger.log_event(
                    event_type="ENCLAVE_RETRIEVE",
                    user_id=requested_by,
                    details={
                        "enclave_id": enclave_id,
                        "data_id": data_id,
                        "access_count": data.access_count
                    },
                    severity="INFO"
                )
            
            logger.debug(f"从飞地 {enclave_id} 检索数据: {data_id}")
            return True, result, "数据检索成功"
            
        except Exception as e:
            logger.error(f"从飞地检索数据失败: {str(e)}")
            return False, None, f"检索失败: {str(e)}"
    
    def delete_data(
        self,
        enclave_id: str,
        data_id: str,
        deleted_by: str = "system"
    ) -> Tuple[bool, str]:
        """
        从飞地删除数据
        
        Args:
            enclave_id: 飞地ID
            data_id: 数据ID
            deleted_by: 删除者
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if enclave_id not in self.enclaves:
                return False, f"飞地不存在: {enclave_id}"
            
            enclave = self.enclaves[enclave_id]
            
            if enclave_id not in self.data_store or data_id not in self.data_store[enclave_id]:
                return False, f"数据不存在: {data_id}"
            
            # 安全删除（覆盖）
            data = self.data_store[enclave_id][data_id]
            self._secure_delete(data.encrypted_data)
            
            del self.data_store[enclave_id][data_id]
            self._save_enclaves()
            
            # 记录审计日志
            if enclave.access_logging:
                self.audit_logger.log_event(
                    event_type="ENCLAVE_DELETE",
                    user_id=deleted_by,
                    details={
                        "enclave_id": enclave_id,
                        "data_id": data_id
                    },
                    severity="WARNING"
                )
            
            logger.info(f"从飞地 {enclave_id} 删除数据: {data_id}")
            return True, "数据删除成功"
            
        except Exception as e:
            logger.error(f"从飞地删除数据失败: {str(e)}")
            return False, f"删除失败: {str(e)}"
    
    def list_data(
        self,
        enclave_id: str,
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出飞地中的数据
        
        Args:
            enclave_id: 飞地ID
            include_metadata: 是否包含元数据
        
        Returns:
            数据列表
        """
        if enclave_id not in self.data_store:
            return []
        
        result = []
        for data_id, data in self.data_store[enclave_id].items():
            item = {
                "data_id": data_id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "access_count": data.access_count,
                "last_accessed": data.last_accessed
            }
            if include_metadata:
                item["metadata"] = data.metadata
            result.append(item)
        
        return result
    
    def _encrypt_for_enclave(self, data: bytes, enclave_id: str) -> bytes:
        """为飞地加密数据"""
        # 获取飞地专用密钥
        key_id = f"enclave_key_{enclave_id}"
        key_material = self.key_management.get_key_material(key_id)
        
        if not key_material:
            # 如果没有专用密钥，使用主密钥
            key_material = self.key_management.get_key_material(self.master_key_id)
        
        f = Fernet(base64.urlsafe_b64encode(key_material[:32]))
        return f.encrypt(data)
    
    def _decrypt_from_enclave(self, encrypted: bytes, enclave_id: str) -> bytes:
        """解密飞地数据"""
        key_id = f"enclave_key_{enclave_id}"
        key_material = self.key_management.get_key_material(key_id)
        
        if not key_material:
            key_material = self.key_management.get_key_material(self.master_key_id)
        
        f = Fernet(base64.urlsafe_b64encode(key_material[:32]))
        return f.decrypt(encrypted)
    
    def _get_enclave_size(self, enclave_id: str) -> int:
        """获取飞地已用大小"""
        if enclave_id not in self.data_store:
            return 0
        
        total = 0
        for data in self.data_store[enclave_id].values():
            total += len(data.encrypted_data)
        return total
    
    def _secure_delete(self, data: bytes) -> None:
        """安全删除数据（覆盖）"""
        # 多次覆盖
        for _ in range(3):
            data = os.urandom(len(data))
    
    def cleanup_expired_data(self, enclave_id: Optional[str] = None) -> int:
        """
        清理过期数据
        
        Args:
            enclave_id: 飞地ID（None表示所有飞地）
        
        Returns:
            清理的数据数量
        """
        cleaned = 0
        now = time.time()
        
        enclaves_to_check = [enclave_id] if enclave_id else self.enclaves.keys()
        
        for eid in enclaves_to_check:
            if eid not in self.enclaves or eid not in self.data_store:
                continue
            
            enclave = self.enclaves[eid]
            cutoff = now - (enclave.auto_cleanup_days * 24 * 3600)
            
            to_delete = []
            for data_id, data in self.data_store[eid].items():
                if data.updated_at < cutoff:
                    to_delete.append(data_id)
            
            for data_id in to_delete:
                self._secure_delete(self.data_store[eid][data_id].encrypted_data)
                del self.data_store[eid][data_id]
                cleaned += 1
        
        if cleaned > 0:
            self._save_enclaves()
            logger.info(f"清理了 {cleaned} 条过期数据")
        
        return cleaned
    
    def get_enclave_info(self, enclave_id: str) -> Optional[Dict[str, Any]]:
        """获取飞地信息"""
        if enclave_id not in self.enclaves:
            return None
        
        enclave = self.enclaves[enclave_id]
        data_count = len(self.data_store.get(enclave_id, {}))
        used_size = self._get_enclave_size(enclave_id)
        
        return {
            "enclave_id": enclave.enclave_id,
            "enclave_type": enclave.enclave_type.value,
            "path": str(enclave.path) if enclave.path else None,
            "max_size": enclave.max_size,
            "used_size": used_size,
            "usage_percent": (used_size / enclave.max_size * 100) if enclave.max_size > 0 else 0,
            "data_count": data_count,
            "auto_cleanup_days": enclave.auto_cleanup_days,
            "access_logging": enclave.access_logging
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_enclaves = len(self.enclaves)
        total_data = sum(len(d) for d in self.data_store.values())
        total_size = sum(self._get_enclave_size(eid) for eid in self.enclaves)
        
        return {
            "total_enclaves": total_enclaves,
            "total_data_items": total_data,
            "total_size_bytes": total_size,
            "average_enclave_size": total_size / total_enclaves if total_enclaves > 0 else 0,
            "enclave_types": {t.value: sum(1 for e in self.enclaves.values() if e.enclave_type == t) 
                             for t in EnclaveType}
        }


# 单例实例
_secure_enclave_instance = None


def get_secure_enclave() -> SecureEnclave:
    """获取安全飞地单例实例"""
    global _secure_enclave_instance
    if _secure_enclave_instance is None:
        _secure_enclave_instance = SecureEnclave()
    return _secure_enclave_instance

