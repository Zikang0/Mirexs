"""
审计日志模块 - 记录安全审计日志
提供不可篡改的审计日志记录，支持区块链式审计链
"""

import logging
import time
import json
import hashlib
import hmac
import secrets
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque

from ..access_control.key_management import KeyManagement, get_key_management
from ...utils.security_utilities.encryption_utils import EncryptionUtils

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型枚举"""
    # 认证事件
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLE = "mfa_enable"
    MFA_DISABLE = "mfa_disable"
    
    # 授权事件
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    ROLE_ASSIGN = "role_assign"
    ROLE_REMOVE = "role_remove"
    
    # 数据事件
    DATA_ACCESS = "data_access"
    DATA_MODIFY = "data_modify"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_SHARE = "data_share"
    
    # 配置事件
    CONFIG_CHANGE = "config_change"
    POLICY_UPDATE = "policy_update"
    SYSTEM_UPDATE = "system_update"
    
    # 安全事件
    THREAT_DETECTED = "threat_detected"
    INCIDENT_RESPONSE = "incident_response"
    COMPLIANCE_CHECK = "compliance_check"
    
    # 用户管理
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_LOCK = "user_lock"
    USER_UNLOCK = "user_unlock"
    
    # 密钥管理
    KEY_GENERATE = "key_generate"
    KEY_ROTATE = "key_rotate"
    KEY_REVOKE = "key_revoke"
    
    # 系统事件
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"


class AuditSeverity(Enum):
    """审计严重性枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """审计条目"""
    entry_id: str
    timestamp: float
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    source_ip: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    status: str  # success, failure, pending
    details: Dict[str, Any]
    previous_hash: str  # 前一个条目的哈希
    entry_hash: str  # 当前条目的哈希
    signature: Optional[str] = None  # 数字签名
    node_id: Optional[str] = None  # 节点ID（分布式环境）


class AuditLogger:
    """
    审计日志记录器
    提供不可篡改的区块链式审计日志
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化审计日志记录器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 审计链
        self.audit_chain: List[AuditEntry] = []
        self.chain_head: Optional[str] = None  # 最新条目的哈希
        
        # 最近日志缓存
        self.recent_entries: deque = deque(maxlen=1000)
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/audit"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.key_management = get_key_management()
        self.encryption_utils = EncryptionUtils()
        
        # 签名密钥
        self.signing_key_id = self.config.get("signing_key_id", "audit_signing_key")
        self._ensure_signing_key()
        
        # 加载现有审计链
        self._load_chain()
        
        logger.info(f"审计日志记录器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/audit",
            "signing_key_id": "audit_signing_key",
            "enable_signing": True,
            "chain_file": "audit_chain.json",
            "index_file": "audit_index.json",
            "max_chain_size": 1000000,  # 最大链长度
            "archive_threshold": 10000,  # 归档阈值
            "verify_on_load": True,
            "enable_distributed": False
        }
    
    def _ensure_signing_key(self):
        """确保签名密钥存在"""
        if not self.config["enable_signing"]:
            return
        
        key = self.key_management.get_key(self.signing_key_id)
        if not key:
            from ..access_control.key_management import KeyAlgorithm, KeyPurpose
            self.key_management.generate_asymmetric_key_pair(
                key_id=self.signing_key_id,
                algorithm=KeyAlgorithm.RSA_2048,
                purpose=[KeyPurpose.SIGNING],
                created_by="system",
                description="Audit log signing key"
            )
            logger.info(f"生成审计签名密钥: {self.signing_key_id}")
    
    def _load_chain(self):
        """从存储加载审计链"""
        try:
            chain_file = self.storage_path / self.config["chain_file"]
            if not chain_file.exists():
                # 创建创世区块
                genesis = self._create_genesis_block()
                self.audit_chain.append(genesis)
                self.chain_head = genesis.entry_hash
                self._save_chain()
                return
            
            with open(chain_file, 'r', encoding='utf-8') as f:
                chain_data = json.load(f)
            
            for entry_dict in chain_data:
                entry_dict["event_type"] = AuditEventType(entry_dict["event_type"])
                entry_dict["severity"] = AuditSeverity(entry_dict["severity"])
                entry = AuditEntry(**entry_dict)
                self.audit_chain.append(entry)
                
                # 更新最近缓存
                self.recent_entries.appendleft(entry)
            
            if self.audit_chain:
                self.chain_head = self.audit_chain[-1].entry_hash
            
            # 验证链完整性
            if self.config["verify_on_load"]:
                if not self.verify_chain():
                    logger.error("审计链完整性验证失败！")
            
            logger.info(f"加载了 {len(self.audit_chain)} 条审计记录")
            
        except Exception as e:
            logger.error(f"加载审计链失败: {str(e)}")
            # 创建新的审计链
            genesis = self._create_genesis_block()
            self.audit_chain = [genesis]
            self.chain_head = genesis.entry_hash
    
    def _save_chain(self):
        """保存审计链到存储"""
        try:
            chain_data = []
            for entry in self.audit_chain:
                entry_dict = {
                    "entry_id": entry.entry_id,
                    "timestamp": entry.timestamp,
                    "event_type": entry.event_type.value,
                    "severity": entry.severity.value,
                    "user_id": entry.user_id,
                    "source_ip": entry.source_ip,
                    "resource": entry.resource,
                    "action": entry.action,
                    "status": entry.status,
                    "details": entry.details,
                    "previous_hash": entry.previous_hash,
                    "entry_hash": entry.entry_hash,
                    "signature": entry.signature,
                    "node_id": entry.node_id
                }
                chain_data.append(entry_dict)
            
            with open(self.storage_path / self.config["chain_file"], 'w', encoding='utf-8') as f:
                json.dump(chain_data, f, ensure_ascii=False, indent=2)
            
            # 保存索引
            self._save_index()
            
            logger.debug(f"保存了 {len(self.audit_chain)} 条审计记录")
            
        except Exception as e:
            logger.error(f"保存审计链失败: {str(e)}")
    
    def _save_index(self):
        """保存索引文件"""
        try:
            index = {
                "last_entry_id": self.audit_chain[-1].entry_id if self.audit_chain else None,
                "last_hash": self.chain_head,
                "total_entries": len(self.audit_chain),
                "last_updated": time.time()
            }
            
            with open(self.storage_path / self.config["index_file"], 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)
                
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
    
    def _create_genesis_block(self) -> AuditEntry:
        """创建创世区块"""
        genesis_hash = hashlib.sha256(b"MIREXS_AUDIT_GENESIS_BLOCK_2026").hexdigest()
        
        return AuditEntry(
            entry_id="genesis",
            timestamp=time.time(),
            event_type=AuditEventType.SYSTEM_START,
            severity=AuditSeverity.INFO,
            user_id="system",
            source_ip="0.0.0.0",
            resource="audit_chain",
            action="initialize",
            status="success",
            details={"message": "Audit chain genesis block"},
            previous_hash="0" * 64,
            entry_hash=genesis_hash
        )
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            source_ip: 源IP
            resource: 资源
            action: 操作
            status: 状态
            severity: 严重性
            details: 详细信息
        
        Returns:
            条目ID
        """
        entry_id = f"audit_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        # 计算前一个哈希
        previous_hash = self.chain_head or "0" * 64
        
        # 构建条目数据
        entry_data = {
            "entry_id": entry_id,
            "timestamp": time.time(),
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "source_ip": source_ip,
            "resource": resource,
            "action": action,
            "status": status,
            "details": details or {},
            "previous_hash": previous_hash
        }
        
        # 计算条目哈希
        entry_hash = self._calculate_entry_hash(entry_data)
        entry_data["entry_hash"] = entry_hash
        
        # 签名
        signature = None
        if self.config["enable_signing"]:
            signature = self._sign_entry(entry_hash)
        
        # 创建条目
        entry = AuditEntry(**entry_data, signature=signature)
        
        # 添加到链
        self.audit_chain.append(entry)
        self.recent_entries.appendleft(entry)
        self.chain_head = entry_hash
        
        # 定期保存
        if len(self.audit_chain) % 100 == 0:
            self._save_chain()
        
        # 检查是否需要归档
        if len(self.audit_chain) > self.config["archive_threshold"]:
            self._archive_chain()
        
        logger.debug(f"审计事件已记录: {event_type.value}")
        
        return entry_id
    
    def _calculate_entry_hash(self, entry_data: Dict) -> str:
        """计算条目哈希"""
        # 排除signature字段
        hash_data = {k: v for k, v in entry_data.items() if k != "signature"}
        
        # 序列化
        serialized = json.dumps(hash_data, sort_keys=True, default=str).encode('utf-8')
        
        return hashlib.sha256(serialized).hexdigest()
    
    def _sign_entry(self, entry_hash: str) -> str:
        """签名条目"""
        try:
            key_material = self.key_management.get_key_material(self.signing_key_id)
            if not key_material:
                logger.warning("无法获取签名密钥")
                return None
            
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import serialization
            
            private_key = serialization.load_pem_private_key(
                key_material,
                password=None
            )
            
            signature = private_key.sign(
                entry_hash.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return signature.hex()
            
        except Exception as e:
            logger.error(f"签名失败: {str(e)}")
            return None
    
    def verify_chain(self) -> bool:
        """验证审计链完整性"""
        if len(self.audit_chain) < 2:
            return True
        
        for i in range(1, len(self.audit_chain)):
            current = self.audit_chain[i]
            previous = self.audit_chain[i-1]
            
            # 验证哈希链接
            if current.previous_hash != previous.entry_hash:
                logger.error(f"哈希链接断裂: 索引 {i}")
                return False
            
            # 验证当前条目哈希
            entry_data = {
                "entry_id": current.entry_id,
                "timestamp": current.timestamp,
                "event_type": current.event_type,
                "severity": current.severity,
                "user_id": current.user_id,
                "source_ip": current.source_ip,
                "resource": current.resource,
                "action": current.action,
                "status": current.status,
                "details": current.details,
                "previous_hash": current.previous_hash
            }
            
            calculated_hash = self._calculate_entry_hash(entry_data)
            if calculated_hash != current.entry_hash:
                logger.error(f"条目哈希不匹配: {current.entry_id}")
                return False
            
            # 验证签名
            if current.signature:
                if not self._verify_signature(current.entry_hash, current.signature):
                    logger.error(f"签名验证失败: {current.entry_id}")
                    return False
        
        return True
    
    def _verify_signature(self, entry_hash: str, signature: str) -> bool:
        """验证签名"""
        try:
            key_material = self.key_management.get_key_material(self.signing_key_id)
            if not key_material:
                return False
            
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.primitives import serialization
            
            public_key = serialization.load_pem_public_key(key_material)
            
            public_key.verify(
                bytes.fromhex(signature),
                entry_hash.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True
            
        except Exception:
            return False
    
    def _archive_chain(self):
        """归档旧审计链"""
        try:
            # 将旧数据移到归档文件
            archive_size = len(self.audit_chain) - self.config["max_chain_size"]
            if archive_size > 0:
                archive_data = self.audit_chain[:archive_size]
                self.audit_chain = self.audit_chain[archive_size:]
                
                archive_file = self.storage_path / f"audit_archive_{int(time.time())}.json"
                with open(archive_file, 'w', encoding='utf-8') as f:
                    json.dump([a.__dict__ for a in archive_data], f, default=str)
                
                logger.info(f"审计链已归档: {archive_file}")
                
        except Exception as e:
            logger.error(f"归档审计链失败: {str(e)}")
    
    def query(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询审计记录
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            event_type: 事件类型
            user_id: 用户ID
            severity: 严重性
            status: 状态
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            审计记录列表
        """
        results = []
        
        # 从最近缓存查询
        for entry in self.recent_entries:
            if len(results) >= limit + offset:
                break
            
            # 应用过滤条件
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            if event_type and entry.event_type != event_type:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if severity and entry.severity != severity:
                continue
            if status and entry.status != status:
                continue
            
            results.append(self._entry_to_dict(entry))
        
        # 应用分页
        return results[offset:offset + limit]
    
    def _entry_to_dict(self, entry: AuditEntry) -> Dict[str, Any]:
        """转换条目为字典"""
        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "event_type": entry.event_type.value,
            "severity": entry.severity.value,
            "user_id": entry.user_id,
            "source_ip": entry.source_ip,
            "resource": entry.resource,
            "action": entry.action,
            "status": entry.status,
            "details": entry.details,
            "entry_hash": entry.entry_hash[:8] + "..."  # 只显示部分哈希
        }
    
    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """获取指定条目"""
        for entry in self.audit_chain:
            if entry.entry_id == entry_id:
                return entry
        return None
    
    def verify_entry(self, entry_id: str) -> bool:
        """验证指定条目"""
        entry = self.get_entry(entry_id)
        if not entry:
            return False
        
        # 找到索引位置
        for i, e in enumerate(self.audit_chain):
            if e.entry_id == entry_id:
                # 验证当前条目
                entry_data = {
                    "entry_id": e.entry_id,
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "severity": e.severity,
                    "user_id": e.user_id,
                    "source_ip": e.source_ip,
                    "resource": e.resource,
                    "action": e.action,
                    "status": e.status,
                    "details": e.details,
                    "previous_hash": e.previous_hash
                }
                
                if self._calculate_entry_hash(entry_data) != e.entry_hash:
                    return False
                
                # 验证链接
                if i > 0:
                    if e.previous_hash != self.audit_chain[i-1].entry_hash:
                        return False
                
                if i < len(self.audit_chain) - 1:
                    if self.audit_chain[i+1].previous_hash != e.entry_hash:
                        return False
                
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_entries": len(self.audit_chain),
            "recent_entries": len(self.recent_entries),
            "chain_head": self.chain_head[:8] + "..." if self.chain_head else None,
            "by_event_type": {},
            "by_severity": {},
            "by_status": {},
            "first_entry": None,
            "last_entry": None
        }
        
        if self.audit_chain:
            stats["first_entry"] = self.audit_chain[0].timestamp
            stats["last_entry"] = self.audit_chain[-1].timestamp
        
        for entry in self.audit_chain:
            event_type = entry.event_type.value
            stats["by_event_type"][event_type] = stats["by_event_type"].get(event_type, 0) + 1
            
            severity = entry.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            status = entry.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        return stats
    
    def export_chain(self, output_file: str, start_time: Optional[float] = None, end_time: Optional[float] = None) -> bool:
        """
        导出审计链
        
        Args:
            output_file: 输出文件路径
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            是否成功
        """
        try:
            entries = []
            for entry in self.audit_chain:
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                
                entries.append({
                    "entry_id": entry.entry_id,
                    "timestamp": entry.timestamp,
                    "event_type": entry.event_type.value,
                    "severity": entry.severity.value,
                    "user_id": entry.user_id,
                    "source_ip": entry.source_ip,
                    "resource": entry.resource,
                    "action": entry.action,
                    "status": entry.status,
                    "details": entry.details,
                    "previous_hash": entry.previous_hash,
                    "entry_hash": entry.entry_hash,
                    "signature": entry.signature
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            
            logger.info(f"导出 {len(entries)} 条审计记录到 {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出审计链失败: {str(e)}")
            return False


# 单例实例
_audit_logger_instance = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志记录器单例实例"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()
    return _audit_logger_instance

