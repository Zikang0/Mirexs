"""
隐私保护模块 - 提供全面的数据隐私保护功能

该模块实现了多层隐私保护机制，包括：
1. 数据加密 (data_encryption) - 敏感数据加密存储
2. 差分隐私 (differential_privacy) - 统计数据发布时的隐私保护
3. 同意管理 (consent_manager) - 用户数据使用同意管理
4. 匿名化引擎 (anonymization_engine) - 数据匿名化处理
5. 隐私审计 (privacy_auditor) - 隐私保护措施审计
6. 安全飞地 (secure_enclave) - 隔离的安全存储环境
7. 数据脱敏 (data_masking) - 实时数据脱敏处理
8. 隐私策略 (privacy_policy) - 隐私政策管理
9. 数据保留 (data_retention) - 数据生命周期管理
10. GDPR合规 (gdpr_compliance) - GDPR法规合规性
11. 隐私指标 (privacy_metrics) - 隐私保护效果指标

该模块是Mirexs安全治理层的核心组成部分，遵循"数据归用户，信任归我们"的设计原则，
提供企业级的隐私保护能力。
"""

import logging
from typing import Dict, Any, Optional, List
import asyncio

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Mirexs Privacy Protection Module - Enterprise-grade data privacy and protection"

# 导入所有子模块
from . import data_encryption
from . import differential_privacy
from . import consent_manager
from . import anonymization_engine
from . import privacy_auditor
from . import secure_enclave
from . import data_masking
from . import privacy_policy
from . import data_retention
from . import gdpr_compliance
from . import privacy_metrics

# 导出主要类和函数
from .data_encryption import (
    DataEncryption,
    EncryptionAlgorithm,
    EncryptionMode,
    EncryptedData,
    get_data_encryption
)

from .differential_privacy import (
    DifferentialPrivacy,
    PrivacyMechanism,
    SensitivityType,
    PrivacyBudget,
    DPResult,
    get_differential_privacy
)

from .consent_manager import (
    ConsentManager,
    ConsentStatus,
    ConsentPurpose,
    ConsentSource,
    ConsentRecord,
    ConsentTemplate,
    get_consent_manager
)

from .anonymization_engine import (
    AnonymizationEngine,
    AnonymizationTechnique,
    DataType,
    AnonymizationRule,
    AnonymizationResult,
    get_anonymization_engine
)

from .privacy_auditor import (
    PrivacyAuditor,
    AuditSeverity,
    AuditStatus,
    PrivacyControlType,
    AuditFinding,
    PrivacyAuditReport,
    get_privacy_auditor
)

from .secure_enclave import (
    SecureEnclave,
    EnclaveType,
    EnclaveAccess,
    SecureEnclaveConfig,
    EnclaveData,
    get_secure_enclave
)

from .data_masking import (
    DataMasking,
    MaskingStrategy,
    MaskingRule,
    MaskedField,
    get_data_masking
)

from .privacy_policy import (
    PrivacyPolicy,
    PolicyStatus,
    PolicyType,
    PolicyVersion,
    UserPolicyAcceptance,
    get_privacy_policy
)

from .data_retention import (
    DataRetention,
    RetentionPolicyType,
    DataCategory,
    RetentionPolicy,
    DataRetentionRule,
    get_data_retention
)

from .gdpr_compliance import (
    GDPRCompliance,
    GDPRRight,
    GDPRComplianceStatus,
    DataSubjectRequest,
    DataProcessingRecord,
    get_gdpr_compliance
)

from .privacy_metrics import (
    PrivacyMetrics,
    PrivacyMetricPoint,
    get_privacy_metrics
)

# 配置日志
logger = logging.getLogger(__name__)


def initialize_privacy_protection(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化整个隐私保护模块
    
    该函数会初始化所有子模块，建立必要的依赖关系，
    并启动后台任务（如数据清理、审计检查等）。
    
    Args:
        config: 全局配置字典
        
    Returns:
        初始化是否成功
    """
    try:
        logger.info("正在初始化隐私保护模块...")
        
        # 获取所有单例实例（自动初始化）
        encryption = get_data_encryption()
        dp = get_differential_privacy()
        consent = get_consent_manager()
        anonymization = get_anonymization_engine()
        auditor = get_privacy_auditor()
        enclave = get_secure_enclave()
        masking = get_data_masking()
        policy = get_privacy_policy()
        retention = get_data_retention()
        gdpr = get_gdpr_compliance()
        metrics = get_privacy_metrics()
        
        # 创建事件循环（如果不存在）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 启动数据清理任务
        if retention.config.get("enable_auto_cleanup", True):
            async def cleanup_loop():
                while True:
                    try:
                        await asyncio.sleep(retention.config["cleanup_interval_hours"] * 3600)
                        result = retention.cleanup_expired_data()
                        if result["total_deleted"] > 0:
                            logger.info(f"自动清理完成: 删除了 {result['total_deleted']} 条过期数据")
                    except Exception as e:
                        logger.error(f"自动清理任务异常: {str(e)}")
            
            loop.create_task(cleanup_loop())
            logger.info(f"自动数据清理任务已启动，间隔 {retention.config['cleanup_interval_hours']} 小时")
        
        # 启动定期审计
        async def audit_loop():
            while True:
                try:
                    await asyncio.sleep(auditor.config.get("audit_interval_days", 30) * 24 * 3600)
                    report = auditor.conduct_audit(auditor="system", scope=None)
                    if report.status.value in ["failed", "error"]:
                        logger.warning(f"定期审计发现问题: {len(report.findings)} 个")
                        
                        # 触发告警
                        from ..security_monitoring.alert_manager import get_alert_manager
                        alert_mgr = get_alert_manager()
                        alert_mgr.send_alert(
                            alert_type="privacy_audit",
                            severity="high" if any(f.severity.value in ["critical", "high"] for f in report.findings) else "medium",
                            message=f"隐私审计发现 {len(report.findings)} 个问题",
                            details={"report_id": report.report_id}
                        )
                except Exception as e:
                    logger.error(f"定期审计任务异常: {str(e)}")
        
        loop.create_task(audit_loop())
        logger.info(f"定期隐私审计任务已启动，间隔 {auditor.config.get('audit_interval_days', 30)} 天")
        
        # 启动指标收集
        async def metrics_loop():
            while True:
                try:
                    await asyncio.sleep(metrics.config["collection_interval_seconds"])
                    metrics.collect_all_metrics()
                    
                    # 定期保存快照
                    if int(time.time()) % metrics.config["report_interval_seconds"] == 0:
                        metrics.save_snapshot()
                        
                except Exception as e:
                    logger.error(f"指标收集任务异常: {str(e)}")
        
        loop.create_task(metrics_loop())
        logger.info(f"隐私指标收集任务已启动，间隔 {metrics.config['collection_interval_seconds']} 秒")
        
        # 记录审计日志
        from ..security_monitoring.audit_logger import get_audit_logger
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type="PRIVACY_MODULE_INIT",
            user_id="system",
            details={
                "status": "success",
                "version": __version__,
                "modules": [
                    "encryption", "differential_privacy", "consent", "anonymization",
                    "auditor", "enclave", "masking", "policy", "retention", "gdpr", "metrics"
                ]
            },
            severity="INFO"
        )
        
        logger.info("隐私保护模块初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"隐私保护模块初始化失败: {str(e)}")
        
        # 尝试记录错误日志
        try:
            from ..security_monitoring.audit_logger import get_audit_logger
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type="PRIVACY_MODULE_INIT",
                user_id="system",
                details={"status": "failed", "error": str(e)},
                severity="CRITICAL"
            )
        except:
            pass
        
        return False


def shutdown_privacy_protection() -> bool:
    """
    关闭隐私保护模块，清理资源
    
    Returns:
        是否成功关闭
    """
    try:
        logger.info("正在关闭隐私保护模块...")
        
        # 获取所有管理器实例
        metrics = get_privacy_metrics()
        retention = get_data_retention()
        
        # 保存最终指标快照
        metrics.save_snapshot()
        
        # 记录最后一次清理统计
        logger.info(f"数据清理统计: 总计清理 {retention.cleanup_stats.get('total_cleaned', 0)} 条数据")
        
        # 记录审计日志
        from ..security_monitoring.audit_logger import get_audit_logger
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type="PRIVACY_MODULE_SHUTDOWN",
            user_id="system",
            details={"status": "success"},
            severity="INFO"
        )
        
        logger.info("隐私保护模块已关闭")
        return True
        
    except Exception as e:
        logger.error(f"关闭隐私保护模块失败: {str(e)}")
        return False


# 便捷函数 - 数据加密
def encrypt_sensitive_data(
    data: Any,
    field_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[EncryptedData], str]:
    """
    便捷函数：加密敏感数据
    
    Args:
        data: 待加密数据
        field_name: 字段名称
        context: 上下文信息
    
    Returns:
        (成功标志, 加密数据, 消息)
    """
    encryption = get_data_encryption()
    return encryption.encrypt_field(data, field_name, context=context)


def decrypt_sensitive_data(
    encrypted_data: EncryptedData,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[Any], str]:
    """
    便捷函数：解密敏感数据
    
    Args:
        encrypted_data: 加密数据
        context: 上下文信息
    
    Returns:
        (成功标志, 解密数据, 消息)
    """
    encryption = get_data_encryption()
    return encryption.decrypt_field(encrypted_data, context)


# 便捷函数 - 匿名化
def anonymize_data(
    data: Any,
    rules: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None
) -> AnonymizationResult:
    """
    便捷函数：匿名化数据
    
    Args:
        data: 待匿名化数据
        rules: 规则列表
        context: 上下文信息
    
    Returns:
        匿名化结果
    """
    anonymization = get_anonymization_engine()
    return anonymization.anonymize(data, rules, context)


def mask_sensitive_text(text: str) -> str:
    """
    便捷函数：脱敏敏感文本
    
    Args:
        text: 原始文本
    
    Returns:
        脱敏后的文本
    """
    masking = get_data_masking()
    return masking.mask_text(text)


# 便捷函数 - 同意管理
def check_user_consent(
    user_id: str,
    purpose: ConsentPurpose
) -> Tuple[bool, ConsentStatus, Optional[ConsentRecord]]:
    """
    便捷函数：检查用户是否已同意
    
    Args:
        user_id: 用户ID
        purpose: 同意目的
    
    Returns:
        (是否有效, 状态, 同意记录)
    """
    consent = get_consent_manager()
    return consent.check_consent(user_id, purpose)


def grant_user_consent(
    user_id: str,
    purpose: ConsentPurpose,
    source: ConsentSource = ConsentSource.USER_INTERFACE,
    ip_address: Optional[str] = None
) -> Tuple[bool, str, Optional[ConsentRecord]]:
    """
    便捷函数：授予用户同意
    
    Args:
        user_id: 用户ID
        purpose: 同意目的
        source: 同意来源
        ip_address: IP地址
    
    Returns:
        (成功标志, 消息, 同意记录)
    """
    consent = get_consent_manager()
    return consent.grant_consent(
        user_id=user_id,
        purpose=purpose,
        source=source,
        ip_address=ip_address
    )


def revoke_user_consent(
    user_id: str,
    purpose: ConsentPurpose,
    reason: Optional[str] = None
) -> Tuple[bool, str]:
    """
    便捷函数：撤销用户同意
    
    Args:
        user_id: 用户ID
        purpose: 同意目的
        reason: 撤销原因
    
    Returns:
        (成功标志, 消息)
    """
    consent = get_consent_manager()
    return consent.revoke_consent(
        user_id=user_id,
        purpose=purpose,
        reason=reason
    )


# 便捷函数 - GDPR
def submit_gdpr_request(
    user_id: str,
    right: GDPRRight,
    details: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str, Optional[DataSubjectRequest]]:
    """
    便捷函数：提交GDPR请求
    
    Args:
        user_id: 用户ID
        right: GDPR权利
        details: 请求详情
    
    Returns:
        (成功标志, 消息, 请求对象)
    """
    gdpr = get_gdpr_compliance()
    return gdpr.submit_data_subject_request(user_id, right, details)


def export_user_data(user_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    便捷函数：导出用户数据（GDPR数据可携权）
    
    Args:
        user_id: 用户ID
    
    Returns:
        (成功标志, 导出数据, 消息)
    """
    gdpr = get_gdpr_compliance()
    
    # 创建访问请求
    success, message, request = gdpr.submit_data_subject_request(
        user_id=user_id,
        right=GDPRRight.RIGHT_OF_ACCESS
    )
    
    if not success or not request:
        return False, None, message
    
    # 处理请求
    success, message, data = gdpr.process_data_subject_request(
        request_id=request.request_id,
        processor="system"
    )
    
    return success, data, message


def delete_user_data(user_id: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    便捷函数：删除用户数据（GDPR被遗忘权）
    
    Args:
        user_id: 用户ID
    
    Returns:
        (成功标志, 删除结果, 消息)
    """
    gdpr = get_gdpr_compliance()
    
    success, message, request = gdpr.submit_data_subject_request(
        user_id=user_id,
        right=GDPRRight.RIGHT_TO_ERASURE
    )
    
    if not success or not request:
        return False, {}, message
    
    success, message, result = gdpr.process_data_subject_request(
        request_id=request.request_id,
        processor="system"
    )
    
    return success, result or {}, message


# 便捷函数 - 数据保留
def get_data_retention_policy(category: DataCategory) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取数据类别的保留策略
    
    Args:
        category: 数据类别
    
    Returns:
        策略信息
    """
    retention = get_data_retention()
    policy = retention.get_policy_for_category(category)
    
    if policy:
        return {
            "category": policy.data_category.value,
            "type": policy.policy_type.value,
            "retention_days": policy.retention_days,
            "description": policy.description
        }
    return None


def is_data_expired(
    category: DataCategory,
    created_at: float,
    user_id: Optional[str] = None
) -> bool:
    """
    便捷函数：检查数据是否已过期
    
    Args:
        category: 数据类别
        created_at: 创建时间
        user_id: 用户ID
    
    Returns:
        是否过期
    """
    retention = get_data_retention()
    return retention.is_expired(category, created_at, user_id)


# 便捷函数 - 安全飞地
def store_in_enclave(
    enclave_id: str,
    data_id: str,
    data: Any,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    便捷函数：在安全飞地中存储数据
    
    Args:
        enclave_id: 飞地ID
        data_id: 数据ID
        data: 要存储的数据
        metadata: 元数据
    
    Returns:
        (成功标志, 消息)
    """
    enclave = get_secure_enclave()
    return enclave.store_data(enclave_id, data_id, data, metadata)


def retrieve_from_enclave(
    enclave_id: str,
    data_id: str
) -> Tuple[bool, Optional[Any], str]:
    """
    便捷函数：从安全飞地检索数据
    
    Args:
        enclave_id: 飞地ID
        data_id: 数据ID
    
    Returns:
        (成功标志, 数据, 消息)
    """
    enclave = get_secure_enclave()
    return enclave.retrieve_data(enclave_id, data_id)


# 便捷函数 - 差分隐私
def add_differential_privacy(
    value: float,
    epsilon: float = 1.0,
    sensitivity: float = 1.0
) -> float:
    """
    便捷函数：添加差分隐私噪声（拉普拉斯机制）
    
    Args:
        value: 原始值
        epsilon: 隐私预算
        sensitivity: 敏感度
    
    Returns:
        加噪后的值
    """
    dp = get_differential_privacy()
    result = dp.laplace_mechanism(value, sensitivity, epsilon)
    return result.value


# 便捷函数 - 隐私审计
def run_privacy_audit(
    auditor: str = "user",
    scope: Optional[List[str]] = None
) -> PrivacyAuditReport:
    """
    便捷函数：执行隐私审计
    
    Args:
        auditor: 审计者
        scope: 审计范围
    
    Returns:
        审计报告
    """
    auditor_instance = get_privacy_auditor()
    return auditor_instance.conduct_audit(auditor=auditor, scope=scope)


def get_privacy_compliance_status(framework: str = "GDPR") -> Dict[str, Any]:
    """
    便捷函数：获取隐私合规状态
    
    Args:
        framework: 合规框架
    
    Returns:
        合规状态
    """
    gdpr = get_gdpr_compliance()
    return gdpr.check_compliance()


# 导出模块级别的函数
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    
    # 初始化/关闭函数
    'initialize_privacy_protection',
    'shutdown_privacy_protection',
    
    # 数据加密
    'DataEncryption',
    'EncryptionAlgorithm',
    'EncryptionMode',
    'EncryptedData',
    'get_data_encryption',
    'encrypt_sensitive_data',
    'decrypt_sensitive_data',
    
    # 差分隐私
    'DifferentialPrivacy',
    'PrivacyMechanism',
    'SensitivityType',
    'PrivacyBudget',
    'DPResult',
    'get_differential_privacy',
    'add_differential_privacy',
    
    # 同意管理
    'ConsentManager',
    'ConsentStatus',
    'ConsentPurpose',
    'ConsentSource',
    'ConsentRecord',
    'ConsentTemplate',
    'get_consent_manager',
    'check_user_consent',
    'grant_user_consent',
    'revoke_user_consent',
    
    # 匿名化引擎
    'AnonymizationEngine',
    'AnonymizationTechnique',
    'DataType',
    'AnonymizationRule',
    'AnonymizationResult',
    'get_anonymization_engine',
    'anonymize_data',
    
    # 隐私审计
    'PrivacyAuditor',
    'AuditSeverity',
    'AuditStatus',
    'PrivacyControlType',
    'AuditFinding',
    'PrivacyAuditReport',
    'get_privacy_auditor',
    'run_privacy_audit',
    
    # 安全飞地
    'SecureEnclave',
    'EnclaveType',
    'EnclaveAccess',
    'SecureEnclaveConfig',
    'EnclaveData',
    'get_secure_enclave',
    'store_in_enclave',
    'retrieve_from_enclave',
    
    # 数据脱敏
    'DataMasking',
    'MaskingStrategy',
    'MaskingRule',
    'MaskedField',
    'get_data_masking',
    'mask_sensitive_text',
    
    # 隐私策略
    'PrivacyPolicy',
    'PolicyStatus',
    'PolicyType',
    'PolicyVersion',
    'UserPolicyAcceptance',
    'get_privacy_policy',
    
    # 数据保留
    'DataRetention',
    'RetentionPolicyType',
    'DataCategory',
    'RetentionPolicy',
    'DataRetentionRule',
    'get_data_retention',
    'get_data_retention_policy',
    'is_data_expired',
    
    # GDPR合规
    'GDPRCompliance',
    'GDPRRight',
    'GDPRComplianceStatus',
    'DataSubjectRequest',
    'DataProcessingRecord',
    'get_gdpr_compliance',
    'submit_gdpr_request',
    'export_user_data',
    'delete_user_data',
    'get_privacy_compliance_status',
    
    # 隐私指标
    'PrivacyMetrics',
    'PrivacyMetricPoint',
    'get_privacy_metrics',
]


# 模块初始化时的日志
logger.debug(f"隐私保护模块 v{__version__} 已加载")
logger.debug(f"模块描述: {__description__}")

