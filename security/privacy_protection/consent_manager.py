"""
同意管理模块 - 管理用户数据使用同意
提供用户同意的收集、存储、验证和撤销功能
"""

import logging
import time
import json
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger
from ...utils.common_utilities.validation_utils import ValidationUtils

logger = logging.getLogger(__name__)


class ConsentStatus(Enum):
    """同意状态枚举"""
    GRANTED = "granted"  # 已同意
    DENIED = "denied"  # 已拒绝
    PENDING = "pending"  # 待确认
    EXPIRED = "expired"  # 已过期
    REVOKED = "revoked"  # 已撤销
    WITHDRAWN = "withdrawn"  # 已撤回（用户主动）


class ConsentPurpose(Enum):
    """同意目的枚举"""
    DATA_COLLECTION = "data_collection"  # 数据收集
    DATA_PROCESSING = "data_processing"  # 数据处理
    DATA_SHARING = "data_sharing"  # 数据共享
    DATA_RETENTION = "data_retention"  # 数据保留
    MARKETING = "marketing"  # 营销
    ANALYTICS = "analytics"  # 分析
    PERSONALIZATION = "personalization"  # 个性化
    THIRD_PARTY = "third_party"  # 第三方共享
    RESEARCH = "research"  # 研究
    PROFILING = "profiling"  # 画像分析
    LOCATION = "location"  # 位置数据
    BIOMETRIC = "biometric"  # 生物特征


class ConsentSource(Enum):
    """同意来源枚举"""
    USER_INTERFACE = "user_interface"  # 用户界面
    API = "api"  # API调用
    INITIAL_SETUP = "initial_setup"  # 初始设置
    POLICY_UPDATE = "policy_update"  # 策略更新
    LEGAL_REQUIREMENT = "legal_requirement"  # 法律要求
    ADMIN_ACTION = "admin_action"  # 管理员操作


@dataclass
class ConsentRecord:
    """同意记录"""
    consent_id: str
    user_id: str
    purpose: ConsentPurpose
    status: ConsentStatus
    granted_at: float
    expires_at: Optional[float] = None
    revoked_at: Optional[float] = None
    source: ConsentSource = ConsentSource.USER_INTERFACE
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_version: str = "1.0"
    data_categories: List[str] = field(default_factory=list)
    third_parties: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    proof_hash: Optional[str] = None  # 同意证明哈希


@dataclass
class ConsentTemplate:
    """同意模板"""
    template_id: str
    purpose: ConsentPurpose
    title: str
    description: str
    version: str
    required: bool = False
    data_categories: List[str] = field(default_factory=list)
    third_parties: List[str] = field(default_factory=list)
    retention_days: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ConsentManager:
    """
    同意管理器 - 管理用户数据使用同意
    符合GDPR、CCPA等隐私法规要求
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化同意管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储同意记录
        self.consents: Dict[str, ConsentRecord] = {}  # consent_id -> record
        self.user_consents: Dict[str, List[str]] = {}  # user_id -> [consent_ids]
        self.purpose_consents: Dict[str, Dict[str, str]] = {}  # user_id -> {purpose -> consent_id}
        
        # 同意模板
        self.templates: Dict[str, ConsentTemplate] = {}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/privacy/consents"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.validation_utils = ValidationUtils()
        
        # 加载数据
        self._load_consents()
        self._load_templates()
        
        # 初始化默认模板
        self._init_default_templates()
        
        logger.info(f"同意管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/privacy/consents",
            "consent_expiry_days": 365,  # 同意有效期
            "require_proof": True,  # 是否需要同意证明
            "min_consent_age_days": 30,  # 最小同意保留天数
            "max_consent_history": 100,  # 每个用户最大同意历史
            "enable_audit": True,
            "default_consent_version": "1.0",
            "purposes": {
                "essential": {
                    "title": "必要数据",
                    "description": "提供服务所必需的数据",
                    "required": True,
                    "data_categories": ["account", "authentication", "service_usage"]
                },
                "analytics": {
                    "title": "分析数据",
                    "description": "用于改进服务和用户体验",
                    "required": False,
                    "data_categories": ["usage_patterns", "performance_metrics"]
                },
                "personalization": {
                    "title": "个性化推荐",
                    "description": "提供个性化内容和推荐",
                    "required": False,
                    "data_categories": ["preferences", "interaction_history"]
                },
                "marketing": {
                    "title": "营销通信",
                    "description": "接收产品更新和营销信息",
                    "required": False,
                    "data_categories": ["email", "contact_info"]
                }
            }
        }
    
    def _init_default_templates(self):
        """初始化默认同意模板"""
        purposes_config = self.config.get("purposes", {})
        
        for purpose_name, purpose_config in purposes_config.items():
            try:
                purpose = ConsentPurpose(purpose_name)
            except ValueError:
                purpose = ConsentPurpose.DATA_COLLECTION
            
            template = ConsentTemplate(
                template_id=f"template_{purpose.value}",
                purpose=purpose,
                title=purpose_config.get("title", purpose.value),
                description=purpose_config.get("description", ""),
                version=self.config["default_consent_version"],
                required=purpose_config.get("required", False),
                data_categories=purpose_config.get("data_categories", []),
                retention_days=purpose_config.get("retention_days", self.config["consent_expiry_days"])
            )
            
            self.templates[template.template_id] = template
        
        logger.info(f"初始化了 {len(self.templates)} 个默认同意模板")
    
    def _load_consents(self) -> None:
        """从存储加载同意记录"""
        try:
            consents_file = self.storage_path / "consents.json"
            if not consents_file.exists():
                return
            
            with open(consents_file, 'r', encoding='utf-8') as f:
                consents_data = json.load(f)
            
            for consent_id, consent_dict in consents_data.items():
                consent_dict["purpose"] = ConsentPurpose(consent_dict["purpose"])
                consent_dict["status"] = ConsentStatus(consent_dict["status"])
                consent_dict["source"] = ConsentSource(consent_dict["source"])
                consent = ConsentRecord(**consent_dict)
                
                self.consents[consent_id] = consent
                
                # 更新索引
                if consent.user_id not in self.user_consents:
                    self.user_consents[consent.user_id] = []
                self.user_consents[consent.user_id].append(consent_id)
                
                # 更新目的索引
                if consent.user_id not in self.purpose_consents:
                    self.purpose_consents[consent.user_id] = {}
                self.purpose_consents[consent.user_id][consent.purpose.value] = consent_id
            
            logger.info(f"加载了 {len(self.consents)} 条同意记录")
        except Exception as e:
            logger.error(f"加载同意记录失败: {str(e)}")
    
    def _load_templates(self) -> None:
        """从存储加载同意模板"""
        try:
            templates_file = self.storage_path / "templates.json"
            if not templates_file.exists():
                return
            
            with open(templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            for template_id, template_dict in templates_data.items():
                template_dict["purpose"] = ConsentPurpose(template_dict["purpose"])
                template = ConsentTemplate(**template_dict)
                self.templates[template_id] = template
            
            logger.info(f"加载了 {len(self.templates)} 个同意模板")
        except Exception as e:
            logger.error(f"加载同意模板失败: {str(e)}")
    
    def _save_consents(self) -> None:
        """保存同意记录到存储"""
        try:
            consents_data = {}
            for consent_id, consent in self.consents.items():
                consent_dict = {
                    "consent_id": consent.consent_id,
                    "user_id": consent.user_id,
                    "purpose": consent.purpose.value,
                    "status": consent.status.value,
                    "granted_at": consent.granted_at,
                    "expires_at": consent.expires_at,
                    "revoked_at": consent.revoked_at,
                    "source": consent.source.value,
                    "ip_address": consent.ip_address,
                    "user_agent": consent.user_agent,
                    "consent_version": consent.consent_version,
                    "data_categories": consent.data_categories,
                    "third_parties": consent.third_parties,
                    "metadata": consent.metadata,
                    "proof_hash": consent.proof_hash
                }
                consents_data[consent_id] = consent_dict
            
            with open(self.storage_path / "consents.json", 'w', encoding='utf-8') as f:
                json.dump(consents_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.consents)} 条同意记录")
        except Exception as e:
            logger.error(f"保存同意记录失败: {str(e)}")
    
    def _save_templates(self) -> None:
        """保存同意模板到存储"""
        try:
            templates_data = {}
            for template_id, template in self.templates.items():
                template_dict = {
                    "template_id": template.template_id,
                    "purpose": template.purpose.value,
                    "title": template.title,
                    "description": template.description,
                    "version": template.version,
                    "required": template.required,
                    "data_categories": template.data_categories,
                    "third_parties": template.third_parties,
                    "retention_days": template.retention_days,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
                templates_data[template_id] = template_dict
            
            with open(self.storage_path / "templates.json", 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同意模板失败: {str(e)}")
    
    def request_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        source: ConsentSource = ConsentSource.USER_INTERFACE,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[ConsentRecord]]:
        """
        请求用户同意
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            source: 同意来源
            ip_address: IP地址
            user_agent: 用户代理
            metadata: 元数据
        
        Returns:
            (成功标志, 消息, 同意记录)
        """
        try:
            # 检查是否已有有效同意
            existing = self.get_user_consent(user_id, purpose)
            if existing and existing.status == ConsentStatus.GRANTED:
                if existing.expires_at and existing.expires_at > time.time():
                    return True, "已有有效同意", existing
            
            # 创建同意记录
            consent_id = f"consent_{secrets.token_hex(16)}"
            
            # 计算过期时间
            template = self._find_template_by_purpose(purpose)
            expiry_days = template.retention_days if template else self.config["consent_expiry_days"]
            expires_at = time.time() + (expiry_days * 24 * 3600)
            
            # 创建同意记录（初始为待确认）
            consent = ConsentRecord(
                consent_id=consent_id,
                user_id=user_id,
                purpose=purpose,
                status=ConsentStatus.PENDING,
                granted_at=time.time(),
                expires_at=expires_at,
                source=source,
                ip_address=ip_address,
                user_agent=user_agent,
                consent_version=self.config["default_consent_version"],
                metadata=metadata or {}
            )
            
            # 如果有模板，复制模板数据
            if template:
                consent.data_categories = template.data_categories.copy()
                consent.third_parties = template.third_parties.copy()
            
            # 生成同意证明哈希
            if self.config["require_proof"]:
                consent.proof_hash = self._generate_proof_hash(consent)
            
            # 存储同意
            self.consents[consent_id] = consent
            
            if user_id not in self.user_consents:
                self.user_consents[user_id] = []
            self.user_consents[user_id].append(consent_id)
            
            self._save_consents()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="CONSENT_REQUEST",
                user_id=user_id,
                details={
                    "consent_id": consent_id,
                    "purpose": purpose.value,
                    "source": source.value
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 的同意请求已创建: {purpose.value}")
            return True, "同意请求已创建，请确认", consent
            
        except Exception as e:
            logger.error(f"请求同意失败: {str(e)}")
            return False, f"请求同意失败: {str(e)}", None
    
    def grant_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        consent_id: Optional[str] = None,
        source: ConsentSource = ConsentSource.USER_INTERFACE,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[ConsentRecord]]:
        """
        授予同意
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            consent_id: 同意ID（如果不指定，则查找待确认的同意）
            source: 同意来源
            ip_address: IP地址
            user_agent: 用户代理
            metadata: 元数据
        
        Returns:
            (成功标志, 消息, 同意记录)
        """
        try:
            consent = None
            
            if consent_id:
                # 使用指定的同意ID
                if consent_id not in self.consents:
                    return False, f"同意记录不存在: {consent_id}", None
                consent = self.consents[consent_id]
                if consent.user_id != user_id:
                    return False, "同意记录不属于该用户", None
            else:
                # 查找待确认的同意
                pending = self._find_pending_consent(user_id, purpose)
                if pending:
                    consent = pending
                else:
                    # 创建新的同意
                    success, message, new_consent = self.request_consent(
                        user_id=user_id,
                        purpose=purpose,
                        source=source,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        metadata=metadata
                    )
                    if not success:
                        return False, message, None
                    consent = new_consent
            
            # 更新同意状态
            consent.status = ConsentStatus.GRANTED
            consent.granted_at = time.time()
            if metadata:
                consent.metadata.update(metadata)
            
            # 更新目的索引
            if user_id not in self.purpose_consents:
                self.purpose_consents[user_id] = {}
            self.purpose_consents[user_id][purpose.value] = consent.consent_id
            
            self._save_consents()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="CONSENT_GRANT",
                user_id=user_id,
                details={
                    "consent_id": consent.consent_id,
                    "purpose": purpose.value
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 授予同意: {purpose.value}")
            return True, "同意已授予", consent
            
        except Exception as e:
            logger.error(f"授予同意失败: {str(e)}")
            return False, f"授予同意失败: {str(e)}", None
    
    def deny_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        consent_id: Optional[str] = None,
        source: ConsentSource = ConsentSource.USER_INTERFACE,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        拒绝同意
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            consent_id: 同意ID
            source: 同意来源
            reason: 拒绝原因
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if consent_id:
                if consent_id not in self.consents:
                    return False, f"同意记录不存在: {consent_id}"
                consent = self.consents[consent_id]
                if consent.user_id != user_id:
                    return False, "同意记录不属于该用户"
            else:
                # 查找现有同意
                existing = self.get_user_consent(user_id, purpose)
                if existing:
                    consent = existing
                else:
                    # 创建拒绝记录
                    success, message, consent = self.request_consent(
                        user_id=user_id,
                        purpose=purpose,
                        source=source
                    )
                    if not success:
                        return False, message
            
            # 更新状态
            consent.status = ConsentStatus.DENIED
            consent.metadata["deny_reason"] = reason
            
            # 从目的索引中移除
            if user_id in self.purpose_consents:
                if purpose.value in self.purpose_consents[user_id]:
                    del self.purpose_consents[user_id][purpose.value]
            
            self._save_consents()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="CONSENT_DENY",
                user_id=user_id,
                details={
                    "consent_id": consent.consent_id,
                    "purpose": purpose.value,
                    "reason": reason
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 拒绝同意: {purpose.value}")
            return True, "同意已拒绝"
            
        except Exception as e:
            logger.error(f"拒绝同意失败: {str(e)}")
            return False, f"拒绝同意失败: {str(e)}"
    
    def revoke_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        consent_id: Optional[str] = None,
        source: ConsentSource = ConsentSource.USER_INTERFACE,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        撤销已授予的同意
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            consent_id: 同意ID
            source: 撤销来源
            reason: 撤销原因
        
        Returns:
            (成功标志, 消息)
        """
        try:
            consent = None
            
            if consent_id:
                if consent_id not in self.consents:
                    return False, f"同意记录不存在: {consent_id}"
                consent = self.consents[consent_id]
                if consent.user_id != user_id:
                    return False, "同意记录不属于该用户"
            else:
                consent = self.get_user_consent(user_id, purpose)
                if not consent:
                    return False, f"未找到用户对 {purpose.value} 的同意记录"
            
            if consent.status != ConsentStatus.GRANTED:
                return False, f"当前状态不是已授予: {consent.status.value}"
            
            # 更新状态
            consent.status = ConsentStatus.REVOKED
            consent.revoked_at = time.time()
            consent.metadata["revoke_reason"] = reason
            consent.metadata["revoke_source"] = source.value
            
            # 从目的索引中移除
            if user_id in self.purpose_consents:
                if purpose.value in self.purpose_consents[user_id]:
                    del self.purpose_consents[user_id][purpose.value]
            
            self._save_consents()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="CONSENT_REVOKE",
                user_id=user_id,
                details={
                    "consent_id": consent.consent_id,
                    "purpose": purpose.value,
                    "reason": reason
                },
                severity="WARNING"
            )
            
            logger.info(f"用户 {user_id} 撤销同意: {purpose.value}")
            return True, "同意已撤销"
            
        except Exception as e:
            logger.error(f"撤销同意失败: {str(e)}")
            return False, f"撤销同意失败: {str(e)}"
    
    def check_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        check_expiry: bool = True
    ) -> Tuple[bool, ConsentStatus, Optional[ConsentRecord]]:
        """
        检查用户是否已同意
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            check_expiry: 是否检查过期
        
        Returns:
            (是否有效, 状态, 同意记录)
        """
        consent = self.get_user_consent(user_id, purpose)
        
        if not consent:
            return False, ConsentStatus.DENIED, None
        
        if consent.status != ConsentStatus.GRANTED:
            return False, consent.status, consent
        
        if check_expiry and consent.expires_at:
            if consent.expires_at < time.time():
                consent.status = ConsentStatus.EXPIRED
                self._save_consents()
                return False, ConsentStatus.EXPIRED, consent
        
        return True, ConsentStatus.GRANTED, consent
    
    def get_user_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose
    ) -> Optional[ConsentRecord]:
        """
        获取用户对特定目的的同意记录
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
        
        Returns:
            同意记录
        """
        # 先从目的索引查找
        if user_id in self.purpose_consents:
            if purpose.value in self.purpose_consents[user_id]:
                consent_id = self.purpose_consents[user_id][purpose.value]
                return self.consents.get(consent_id)
        
        # 遍历用户的所有同意记录
        if user_id in self.user_consents:
            for consent_id in reversed(self.user_consents[user_id]):
                consent = self.consents.get(consent_id)
                if consent and consent.purpose == purpose:
                    return consent
        
        return None
    
    def get_user_consents(
        self,
        user_id: str,
        include_expired: bool = False,
        include_revoked: bool = False
    ) -> List[ConsentRecord]:
        """
        获取用户的所有同意记录
        
        Args:
            user_id: 用户ID
            include_expired: 是否包含已过期的
            include_revoked: 是否包含已撤销的
        
        Returns:
            同意记录列表
        """
        if user_id not in self.user_consents:
            return []
        
        consents = []
        now = time.time()
        
        for consent_id in self.user_consents[user_id]:
            consent = self.consents.get(consent_id)
            if not consent:
                continue
            
            # 过滤
            if not include_expired and consent.expires_at and consent.expires_at < now:
                continue
            if not include_revoked and consent.status == ConsentStatus.REVOKED:
                continue
            
            consents.append(consent)
        
        # 按时间倒序排序
        consents.sort(key=lambda c: c.granted_at, reverse=True)
        
        return consents
    
    def get_consent_history(
        self,
        user_id: str,
        purpose: Optional[ConsentPurpose] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取用户的同意历史
        
        Args:
            user_id: 用户ID
            purpose: 同意目的
            limit: 返回条数限制
        
        Returns:
            历史记录列表
        """
        if user_id not in self.user_consents:
            return []
        
        history = []
        
        for consent_id in self.user_consents[user_id]:
            consent = self.consents.get(consent_id)
            if not consent:
                continue
            
            if purpose and consent.purpose != purpose:
                continue
            
            history.append({
                "consent_id": consent.consent_id,
                "purpose": consent.purpose.value,
                "status": consent.status.value,
                "granted_at": consent.granted_at,
                "expires_at": consent.expires_at,
                "revoked_at": consent.revoked_at,
                "source": consent.source.value,
                "consent_version": consent.consent_version
            })
        
        # 按时间倒序排序
        history.sort(key=lambda h: h["granted_at"], reverse=True)
        
        return history[:limit]
    
    def create_template(
        self,
        template_id: str,
        purpose: ConsentPurpose,
        title: str,
        description: str,
        required: bool = False,
        data_categories: Optional[List[str]] = None,
        third_parties: Optional[List[str]] = None,
        retention_days: Optional[int] = None
    ) -> Tuple[bool, str, Optional[ConsentTemplate]]:
        """
        创建同意模板
        
        Args:
            template_id: 模板ID
            purpose: 同意目的
            title: 标题
            description: 描述
            required: 是否必需
            data_categories: 数据类别
            third_parties: 第三方列表
            retention_days: 保留天数
        
        Returns:
            (成功标志, 消息, 模板)
        """
        try:
            if template_id in self.templates:
                return False, f"模板ID已存在: {template_id}", None
            
            template = ConsentTemplate(
                template_id=template_id,
                purpose=purpose,
                title=title,
                description=description,
                version=self.config["default_consent_version"],
                required=required,
                data_categories=data_categories or [],
                third_parties=third_parties or [],
                retention_days=retention_days or self.config["consent_expiry_days"]
            )
            
            self.templates[template_id] = template
            self._save_templates()
            
            logger.info(f"创建同意模板: {template_id}")
            return True, "模板创建成功", template
            
        except Exception as e:
            logger.error(f"创建模板失败: {str(e)}")
            return False, f"创建模板失败: {str(e)}", None
    
    def get_templates(
        self,
        purpose: Optional[ConsentPurpose] = None,
        required_only: bool = False
    ) -> List[ConsentTemplate]:
        """
        获取同意模板列表
        
        Args:
            purpose: 同意目的
            required_only: 只返回必需的模板
        
        Returns:
            模板列表
        """
        templates = list(self.templates.values())
        
        if purpose:
            templates = [t for t in templates if t.purpose == purpose]
        
        if required_only:
            templates = [t for t in templates if t.required]
        
        return templates
    
    def _find_template_by_purpose(self, purpose: ConsentPurpose) -> Optional[ConsentTemplate]:
        """根据目的查找模板"""
        for template in self.templates.values():
            if template.purpose == purpose:
                return template
        return None
    
    def _find_pending_consent(
        self,
        user_id: str,
        purpose: ConsentPurpose
    ) -> Optional[ConsentRecord]:
        """查找待确认的同意记录"""
        if user_id not in self.user_consents:
            return None
        
        for consent_id in self.user_consents[user_id]:
            consent = self.consents.get(consent_id)
            if consent and consent.purpose == purpose and consent.status == ConsentStatus.PENDING:
                return consent
        
        return None
    
    def _generate_proof_hash(self, consent: ConsentRecord) -> str:
        """生成同意证明哈希"""
        proof_data = (
            f"{consent.consent_id}:{consent.user_id}:{consent.purpose.value}:"
            f"{consent.granted_at}:{consent.consent_version}"
        )
        return hashlib.sha256(proof_data.encode()).hexdigest()
    
    def verify_proof(self, consent_id: str, proof_hash: str) -> bool:
        """验证同意证明"""
        consent = self.consents.get(consent_id)
        if not consent or not consent.proof_hash:
            return False
        
        return consent.proof_hash == proof_hash
    
    def cleanup_expired_consents(self) -> int:
        """
        清理过期同意记录
        
        Returns:
            清理数量
        """
        try:
            now = time.time()
            cleaned = 0
            
            for consent_id, consent in list(self.consents.items()):
                if consent.expires_at and consent.expires_at < now:
                    # 标记为过期
                    if consent.status == ConsentStatus.GRANTED:
                        consent.status = ConsentStatus.EXPIRED
                        cleaned += 1
                    
                    # 如果超过最小保留期，可以考虑归档
                    min_retention = self.config["min_consent_age_days"] * 24 * 3600
                    if now - consent.granted_at > min_retention:
                        # 从索引中移除
                        if consent.user_id in self.user_consents:
                            if consent_id in self.user_consents[consent.user_id]:
                                self.user_consents[consent.user_id].remove(consent_id)
                        
                        if consent.user_id in self.purpose_consents:
                            if consent.purpose.value in self.purpose_consents[consent.user_id]:
                                del self.purpose_consents[consent.user_id][consent.purpose.value]
                        
                        del self.consents[consent_id]
                        cleaned += 1
            
            if cleaned > 0:
                self._save_consents()
                logger.info(f"清理了 {cleaned} 个过期同意记录")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"清理过期同意失败: {str(e)}")
            return 0
    
    def export_user_consents(
        self,
        user_id: str,
        format: str = "json"
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        导出用户同意记录（用于数据可移植性）
        
        Args:
            user_id: 用户ID
            format: 导出格式
        
        Returns:
            (成功标志, 导出数据, 消息)
        """
        try:
            consents = self.get_user_consents(user_id, include_expired=True, include_revoked=True)
            
            export_data = {
                "user_id": user_id,
                "exported_at": time.time(),
                "total_consents": len(consents),
                "consents": []
            }
            
            for consent in consents:
                export_data["consents"].append({
                    "purpose": consent.purpose.value,
                    "status": consent.status.value,
                    "granted_at": consent.granted_at,
                    "expires_at": consent.expires_at,
                    "revoked_at": consent.revoked_at,
                    "consent_version": consent.consent_version,
                    "data_categories": consent.data_categories,
                    "third_parties": consent.third_parties
                })
            
            return True, export_data, "导出成功"
            
        except Exception as e:
            logger.error(f"导出用户同意失败: {str(e)}")
            return False, None, f"导出失败: {str(e)}"
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts = {}
        purpose_counts = {}
        
        for consent in self.consents.values():
            status_counts[consent.status.value] = status_counts.get(consent.status.value, 0) + 1
            purpose_counts[consent.purpose.value] = purpose_counts.get(consent.purpose.value, 0) + 1
        
        return {
            "total_consents": len(self.consents),
            "unique_users": len(self.user_consents),
            "templates_count": len(self.templates),
            "status_distribution": status_counts,
            "purpose_distribution": purpose_counts,
            "expired_consents": len([c for c in self.consents.values() if c.expires_at and c.expires_at < time.time()])
        }


# 单例实例
_consent_manager_instance = None


def get_consent_manager() -> ConsentManager:
    """获取同意管理器单例实例"""
    global _consent_manager_instance
    if _consent_manager_instance is None:
        _consent_manager_instance = ConsentManager()
    return _consent_manager_instance

