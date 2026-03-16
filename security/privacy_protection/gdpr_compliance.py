"""
GDPR合规模块 - GDPR法规合规性
提供GDPR要求的各项功能和检查
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field

from ..security_monitoring.audit_logger import AuditLogger
from .consent_manager import ConsentManager, ConsentPurpose, get_consent_manager
from .data_retention import DataRetention, DataCategory, get_data_retention
from .privacy_policy import PrivacyPolicy, PolicyType, get_privacy_policy

logger = logging.getLogger(__name__)


class GDPRRight(Enum):
    """GDPR权利枚举"""
    RIGHT_TO_BE_INFORMED = "right_to_be_informed"  # 知情权
    RIGHT_OF_ACCESS = "right_of_access"  # 访问权
    RIGHT_TO_RECTIFICATION = "right_to_rectification"  # 更正权
    RIGHT_TO_ERASURE = "right_to_erasure"  # 被遗忘权
    RIGHT_TO_RESTRICT_PROCESSING = "right_to_restrict_processing"  # 限制处理权
    RIGHT_TO_DATA_PORTABILITY = "right_to_data_portability"  # 数据可携权
    RIGHT_TO_OBJECT = "right_to_object"  # 反对权
    RIGHTS_RELATED_TO_AUTOMATED_DECISION = "rights_related_to_automated_decision"  # 自动化决策相关权利


class GDPRComplianceStatus(Enum):
    """GDPR合规状态枚举"""
    COMPLIANT = "compliant"  # 合规
    PARTIALLY_COMPLIANT = "partially_compliant"  # 部分合规
    NON_COMPLIANT = "non_compliant"  # 不合规
    NOT_APPLICABLE = "not_applicable"  # 不适用


@dataclass
class DataSubjectRequest:
    """数据主体请求"""
    request_id: str
    user_id: str
    right: GDPRRight
    status: str  # pending, processing, completed, rejected
    submitted_at: float
    completed_at: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    response_data: Optional[Any] = None
    rejection_reason: Optional[str] = None


@dataclass
class DataProcessingRecord:
    """数据处理记录"""
    record_id: str
    controller: str
    processor: str
    purpose: str
    data_categories: List[str]
    data_subjects: List[str]
    retention_period: str
    security_measures: List[str]
    transfers: List[str]
    created_at: float
    updated_at: float


class GDPRCompliance:
    """
    GDPR合规管理器 - 确保系统符合GDPR要求
    处理数据主体请求、记录数据处理、评估合规状态
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化GDPR合规管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 数据主体请求
        self.requests: Dict[str, DataSubjectRequest] = {}
        self.user_requests: Dict[str, List[str]] = {}  # user_id -> [request_ids]
        
        # 数据处理记录
        self.processing_records: Dict[str, DataProcessingRecord] = {}
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.consent_manager = get_consent_manager()
        self.data_retention = get_data_retention()
        self.privacy_policy = get_privacy_policy()
        
        # DPO信息
        self.dpo_info = self.config.get("dpo", {
            "name": "Data Protection Officer",
            "email": "dpo@mirexs.com",
            "phone": "+1234567890"
        })
        
        # 代表信息（非欧盟实体）
        self.representative_info = self.config.get("representative", {
            "name": "EU Representative",
            "email": "representative@mirexs-eu.com",
            "address": "EU Address"
        })
        
        logger.info("GDPR合规管理器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "controller_name": "Mirexs Technologies",
            "controller_email": "privacy@mirexs.com",
            "controller_address": "123 Privacy Street, Data City, 12345",
            "dpo": {
                "name": "Data Protection Officer",
                "email": "dpo@mirexs.com",
                "phone": "+1234567890"
            },
            "representative": {
                "name": "Mirexs EU Representative",
                "email": "eu.representative@mirexs.com",
                "address": "EU Representative Address"
            },
            "request_timeout_days": 30,  # GDPR要求30天内响应
            "automated_decisions": False,  # 是否使用自动化决策
            "data_transfers": ["standard_contractual_clauses"],  # 数据传输机制
            "legitimate_interests": ["security", "analytics"]  # 合法利益
        }
    
    def submit_data_subject_request(
        self,
        user_id: str,
        right: GDPRRight,
        details: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[DataSubjectRequest]]:
        """
        提交数据主体请求
        
        Args:
            user_id: 用户ID
            right: 请求的GDPR权利
            details: 请求详情
        
        Returns:
            (成功标志, 消息, 请求对象)
        """
        try:
            request_id = f"dsr_{int(time.time())}_{user_id[-8:]}"
            
            request = DataSubjectRequest(
                request_id=request_id,
                user_id=user_id,
                right=right,
                status="pending",
                submitted_at=time.time(),
                details=details or {}
            )
            
            self.requests[request_id] = request
            
            if user_id not in self.user_requests:
                self.user_requests[user_id] = []
            self.user_requests[user_id].append(request_id)
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="GDPR_REQUEST_SUBMIT",
                user_id=user_id,
                details={
                    "request_id": request_id,
                    "right": right.value,
                    "details": details
                },
                severity="INFO"
            )
            
            logger.info(f"用户 {user_id} 提交GDPR请求: {right.value}")
            return True, "请求已提交", request
            
        except Exception as e:
            logger.error(f"提交GDPR请求失败: {str(e)}")
            return False, f"提交失败: {str(e)}", None
    
    def process_data_subject_request(
        self,
        request_id: str,
        processor: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        处理数据主体请求
        
        Args:
            request_id: 请求ID
            processor: 处理者
        
        Returns:
            (成功标志, 消息, 响应数据)
        """
        if request_id not in self.requests:
            return False, f"请求不存在: {request_id}", None
        
        request = self.requests[request_id]
        request.status = "processing"
        
        try:
            response_data = None
            
            if request.right == GDPRRight.RIGHT_OF_ACCESS:
                # 访问权：提供用户数据的副本
                response_data = self._handle_access_request(request.user_id)
            
            elif request.right == GDPRRight.RIGHT_TO_ERASURE:
                # 被遗忘权：删除用户数据
                response_data = self._handle_erasure_request(request.user_id)
            
            elif request.right == GDPRRight.RIGHT_TO_DATA_PORTABILITY:
                # 数据可携权：提供可移植格式的数据
                response_data = self._handle_portability_request(request.user_id)
            
            elif request.right == GDPRRight.RIGHT_TO_RECTIFICATION:
                # 更正权：更正用户数据
                response_data = self._handle_rectification_request(
                    request.user_id, request.details
                )
            
            elif request.right == GDPRRight.RIGHT_TO_RESTRICT_PROCESSING:
                # 限制处理权：限制数据处理
                response_data = self._handle_restriction_request(
                    request.user_id, request.details
                )
            
            elif request.right == GDPRRight.RIGHT_TO_OBJECT:
                # 反对权：反对数据处理
                response_data = self._handle_objection_request(
                    request.user_id, request.details
                )
            
            request.status = "completed"
            request.completed_at = time.time()
            request.response_data = response_data
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="GDPR_REQUEST_PROCESS",
                user_id=request.user_id,
                details={
                    "request_id": request_id,
                    "right": request.right.value,
                    "processor": processor
                },
                severity="INFO"
            )
            
            logger.info(f"处理GDPR请求完成: {request_id}")
            return True, "请求处理完成", response_data
            
        except Exception as e:
            request.status = "rejected"
            request.rejection_reason = str(e)
            logger.error(f"处理GDPR请求失败: {str(e)}")
            return False, f"处理失败: {str(e)}", None
    
    def _handle_access_request(self, user_id: str) -> Dict[str, Any]:
        """处理访问请求"""
        # 收集用户的所有数据
        user_data = {
            "user_id": user_id,
            "profile": self._get_user_profile(user_id),
            "preferences": self._get_user_preferences(user_id),
            "consents": self.consent_manager.get_user_consents(user_id, include_expired=True),
            "interactions": self._get_user_interactions(user_id),
            "processing_info": {
                "controller": self.config["controller_name"],
                "purposes": ["service_provision", "analytics", "security"],
                "legal_bases": ["consent", "contract", "legitimate_interest"],
                "retention_periods": self._get_retention_periods()
            }
        }
        return user_data
    
    def _handle_erasure_request(self, user_id: str) -> Dict[str, Any]:
        """处理被遗忘权请求"""
        # 标记用户数据为待删除
        # 实际应用中应触发数据删除流程
        
        # 记录需要删除的数据类别
        categories_to_delete = [c.value for c in DataCategory]
        
        # 但保留必要的数据（如审计日志、法律要求）
        retained_categories = ["audit_logs", "legal_records"]
        
        result = {
            "user_id": user_id,
            "deleted_categories": [c for c in categories_to_delete if c not in retained_categories],
            "retained_categories": retained_categories,
            "deletion_scheduled": True,
            "estimated_completion": time.time() + 24 * 3600,  # 24小时内完成
            "confirmation_code": f"DEL_{user_id[-8:]}_{int(time.time())}"
        }
        
        return result
    
    def _handle_portability_request(self, user_id: str) -> Dict[str, Any]:
        """处理数据可携权请求"""
        # 收集用户数据并提供可移植格式
        user_data = self._handle_access_request(user_id)
        
        # 转换为通用格式（如JSON）
        portable_data = {
            "version": "1.0",
            "timestamp": time.time(),
            "controller": self.config["controller_name"],
            "data_subject": user_id,
            "data": user_data,
            "format": "application/json",
            "encoding": "UTF-8"
        }
        
        return portable_data
    
    def _handle_rectification_request(
        self,
        user_id: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理更正权请求"""
        corrections = details.get("corrections", {})
        
        # 实际应用中应更新用户数据
        result = {
            "user_id": user_id,
            "corrections_applied": list(corrections.keys()),
            "status": "completed",
            "timestamp": time.time()
        }
        
        return result
    
    def _handle_restriction_request(
        self,
        user_id: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理限制处理权请求"""
        restriction_type = details.get("restriction_type", "all")
        
        result = {
            "user_id": user_id,
            "restriction_type": restriction_type,
            "restricted_processing": True,
            "effective_from": time.time(),
            "expires_at": time.time() + 30 * 24 * 3600,  # 30天
            "confirmation_code": f"RST_{user_id[-8:]}_{int(time.time())}"
        }
        
        return result
    
    def _handle_objection_request(
        self,
        user_id: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理反对权请求"""
        objection_to = details.get("objection_to", ["marketing"])
        
        result = {
            "user_id": user_id,
            "objection_to": objection_to,
            "processing_stopped": True,
            "effective_from": time.time(),
            "exceptions": ["legal_obligations"],
            "confirmation_code": f"OBJ_{user_id[-8:]}_{int(time.time())}"
        }
        
        return result
    
    def check_compliance(self) -> Dict[str, Any]:
        """
        检查GDPR合规状态
        
        Returns:
            合规检查结果
        """
        checks = {
            "timestamp": time.time(),
            "overall_status": GDPRComplianceStatus.COMPLIANT.value,
            "checks": {},
            "recommendations": []
        }
        
        # 1. 检查同意管理
        consent_status = self._check_consent_compliance()
        checks["checks"]["consent_management"] = consent_status
        if consent_status["status"] != "compliant":
            checks["overall_status"] = GDPRComplianceStatus.PARTIALLY_COMPLIANT.value
            checks["recommendations"].extend(consent_status.get("recommendations", []))
        
        # 2. 检查数据保留
        retention_status = self._check_retention_compliance()
        checks["checks"]["data_retention"] = retention_status
        if retention_status["status"] != "compliant":
            checks["overall_status"] = GDPRComplianceStatus.PARTIALLY_COMPLIANT.value
            checks["recommendations"].extend(retention_status.get("recommendations", []))
        
        # 3. 检查隐私政策
        policy_status = self._check_policy_compliance()
        checks["checks"]["privacy_policy"] = policy_status
        if policy_status["status"] != "compliant":
            checks["overall_status"] = GDPRComplianceStatus.PARTIALLY_COMPLIANT.value
            checks["recommendations"].extend(policy_status.get("recommendations", []))
        
        # 4. 检查数据主体权利
        rights_status = self._check_rights_compliance()
        checks["checks"]["data_subject_rights"] = rights_status
        if rights_status["status"] != "compliant":
            checks["overall_status"] = GDPRComplianceStatus.PARTIALLY_COMPLIANT.value
            checks["recommendations"].extend(rights_status.get("recommendations", []))
        
        # 5. 检查数据处理记录
        records_status = self._check_processing_records()
        checks["checks"]["processing_records"] = records_status
        
        # 6. 检查数据传输
        transfer_status = self._check_data_transfers()
        checks["checks"]["data_transfers"] = transfer_status
        
        return checks
    
    def _check_consent_compliance(self) -> Dict[str, Any]:
        """检查同意管理合规性"""
        status = {
            "status": "compliant",
            "details": {},
            "recommendations": []
        }
        
        # 检查是否有同意记录
        stats = self.consent_manager.get_statistics()
        
        if stats["total_consents"] == 0:
            status["status"] = "non_compliant"
            status["recommendations"].append("需要收集用户同意记录")
        else:
            # 检查必要的同意类型
            required_purposes = [
                ConsentPurpose.DATA_COLLECTION,
                ConsentPurpose.DATA_PROCESSING
            ]
            
            # 这里应该检查是否有用户对这些目的给予同意
            status["details"]["consent_count"] = stats["total_consents"]
            status["details"]["unique_users"] = stats["unique_users"]
        
        return status
    
    def _check_retention_compliance(self) -> Dict[str, Any]:
        """检查数据保留合规性"""
        status = {
            "status": "compliant",
            "details": {},
            "recommendations": []
        }
        
        stats = self.data_retention.get_statistics()
        
        if stats["total_policies"] < 10:
            status["status"] = "warning"
            status["recommendations"].append("建议为所有数据类别定义保留策略")
        
        status["details"]["policies_count"] = stats["total_policies"]
        status["details"]["enabled_policies"] = stats["enabled_policies"]
        
        return status
    
    def _check_policy_compliance(self) -> Dict[str, Any]:
        """检查隐私政策合规性"""
        status = {
            "status": "compliant",
            "details": {},
            "recommendations": []
        }
        
        # 检查是否有活跃的隐私政策
        active_policy = self.privacy_policy.get_active_policy(PolicyType.PRIVACY_POLICY)
        
        if not active_policy:
            status["status"] = "non_compliant"
            status["recommendations"].append("需要发布隐私政策")
        else:
            status["details"]["policy_version"] = active_policy.version
            status["details"]["effective_date"] = active_policy.effective_date
            
            # 检查政策是否包含必要内容
            content = active_policy.content.lower()
            required_terms = ["data", "collect", "purpose", "right", "contact"]
            missing = [term for term in required_terms if term not in content]
            
            if missing:
                status["status"] = "warning"
                status["recommendations"].append(f"隐私政策缺少以下内容: {missing}")
        
        return status
    
    def _check_rights_compliance(self) -> Dict[str, Any]:
        """检查数据主体权利合规性"""
        status = {
            "status": "compliant",
            "details": {
                "total_requests": len(self.requests),
                "pending_requests": sum(1 for r in self.requests.values() if r.status == "pending"),
                "completed_requests": sum(1 for r in self.requests.values() if r.status == "completed"),
                "rejected_requests": sum(1 for r in self.requests.values() if r.status == "rejected")
            },
            "recommendations": []
        }
        
        # 检查是否有超时请求
        timeout_days = self.config["request_timeout_days"]
        now = time.time()
        
        for request in self.requests.values():
            if request.status in ["pending", "processing"]:
                age_days = (now - request.submitted_at) / (24 * 3600)
                if age_days > timeout_days:
                    status["status"] = "warning"
                    status["recommendations"].append(f"请求 {request.request_id} 已超过 {timeout_days} 天未处理")
        
        return status
    
    def _check_processing_records(self) -> Dict[str, Any]:
        """检查数据处理记录"""
        status = {
            "status": "compliant",
            "details": {
                "records_count": len(self.processing_records)
            }
        }
        return status
    
    def _check_data_transfers(self) -> Dict[str, Any]:
        """检查数据传输合规性"""
        status = {
            "status": "compliant",
            "details": {
                "transfer_mechanisms": self.config["data_transfers"]
            }
        }
        return status
    
    def create_processing_record(
        self,
        purpose: str,
        data_categories: List[str],
        data_subjects: List[str],
        retention_period: str,
        security_measures: List[str],
        transfers: Optional[List[str]] = None
    ) -> DataProcessingRecord:
        """
        创建数据处理记录
        
        Args:
            purpose: 处理目的
            data_categories: 数据类别
            data_subjects: 数据主体
            retention_period: 保留期限
            security_measures: 安全措施
            transfers: 数据传输
        
        Returns:
            处理记录
        """
        record_id = f"proc_{int(time.time())}_{len(self.processing_records)}"
        
        record = DataProcessingRecord(
            record_id=record_id,
            controller=self.config["controller_name"],
            processor=self.config["controller_name"],
            purpose=purpose,
            data_categories=data_categories,
            data_subjects=data_subjects,
            retention_period=retention_period,
            security_measures=security_measures,
            transfers=transfers or [],
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.processing_records[record_id] = record
        
        logger.info(f"创建数据处理记录: {record_id}")
        return record
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户资料（模拟实现）"""
        return {
            "user_id": user_id,
            "email": f"{user_id}@example.com",
            "name": "Test User",
            "created_at": time.time() - 30 * 24 * 3600
        }
    
    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好（模拟实现）"""
        return {
            "language": "zh-CN",
            "theme": "dark",
            "notifications": True
        }
    
    def _get_user_interactions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户交互记录（模拟实现）"""
        return [
            {
                "timestamp": time.time() - 3600,
                "type": "conversation",
                "content": "Sample interaction"
            }
        ]
    
    def _get_retention_periods(self) -> Dict[str, str]:
        """获取保留期限"""
        periods = {}
        for category in DataCategory:
            policy = self.data_retention.get_policy_for_category(category)
            if policy:
                periods[category.value] = f"{policy.retention_days} days"
        return periods
    
    def get_dpo_contact(self) -> Dict[str, str]:
        """获取DPO联系方式"""
        return self.dpo_info
    
    def get_representative_contact(self) -> Dict[str, str]:
        """获取欧盟代表联系方式"""
        return self.representative_info
    
    def get_requests_by_user(self, user_id: str) -> List[DataSubjectRequest]:
        """获取用户的所有请求"""
        if user_id not in self.user_requests:
            return []
        
        requests = []
        for request_id in self.user_requests[user_id]:
            if request_id in self.requests:
                requests.append(self.requests[request_id])
        
        return requests


# 单例实例
_gdpr_compliance_instance = None


def get_gdpr_compliance() -> GDPRCompliance:
    """获取GDPR合规管理器单例实例"""
    global _gdpr_compliance_instance
    if _gdpr_compliance_instance is None:
        _gdpr_compliance_instance = GDPRCompliance()
    return _gdpr_compliance_instance

