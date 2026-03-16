"""
安全治理层 - Mirexs系统的安全核心

该模块提供了企业级的安全防护能力，包含三个核心子模块：
1. access_control - 访问控制模块：身份认证、权限管理、会话控制
2. privacy_protection - 隐私保护模块：数据加密、匿名化、同意管理
3. security_monitoring - 安全监控模块：威胁检测、入侵防御、事件响应

遵循"安全内置"的设计原则，将安全作为底层架构的核心组成部分。
"""

import logging
from typing import Dict, Any, Optional

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Mirexs Security Layer - Enterprise-grade security, privacy and monitoring"

# 导入所有子模块
from . import access_control
from . import privacy_protection
from . import security_monitoring

# 重新导出子模块的主要接口
from .access_control import (
    # 生物认证
    BiometricAuth, BiometricType, BiometricAuthLevel, BiometricAuthResult, get_biometric_auth,
    
    # 多因素认证
    MultiFactorAuth, AuthFactorType, AuthFactorStatus, AuthResult, get_multi_factor_auth,
    
    # 权限管理
    PermissionManager, Permission, ResourceType, AccessType, Role, PermissionCheckResult, get_permission_manager,
    
    # 密钥管理
    KeyManagement, KeyType, KeyAlgorithm, KeyStatus, KeyPurpose, KeyMetadata, get_key_management,
    
    # 身份验证
    IdentityVerifier, VerificationMethod, VerificationLevel, VerificationRequest, VerificationResult, get_identity_verifier,
    
    # 访问日志
    AccessLogger, LogAccessType, AccessResult, AccessLogEntry, get_access_logger,
    
    # 会话管理
    SessionManager, Session, SessionStatus, SessionCreateResult, get_session_manager,
    
    # 基于角色的访问控制
    RoleBasedAccess, AccessDecision, AccessRequest, AccessDecisionResult, get_role_based_access,
    
    # 基于属性的访问控制
    AttributeBasedAccess, AttributeType, Operator, AttributeCondition, ABACPolicy, AttributeContext, get_attribute_based_access,
    
    # 访问策略
    AccessPolicy, PolicyType, PolicyEffect, Policy, get_access_policy,
    
    # 访问指标
    AccessMetrics, MetricDefinition, MetricPoint, get_access_metrics,
    
    # 便捷函数
    quick_authenticate, check_user_permission, get_user_effective_permissions
)

from .privacy_protection import (
    # 数据加密
    DataEncryption, EncryptionAlgorithm, EncryptionMode, EncryptedData, get_data_encryption,
    encrypt_sensitive_data, decrypt_sensitive_data,
    
    # 差分隐私
    DifferentialPrivacy, PrivacyMechanism, SensitivityType, PrivacyBudget, DPResult, get_differential_privacy,
    add_differential_privacy,
    
    # 同意管理
    ConsentManager, ConsentStatus, ConsentPurpose, ConsentSource, ConsentRecord, ConsentTemplate, get_consent_manager,
    check_user_consent, grant_user_consent, revoke_user_consent,
    
    # 匿名化引擎
    AnonymizationEngine, AnonymizationTechnique, DataType, AnonymizationRule, AnonymizationResult, get_anonymization_engine,
    anonymize_data,
    
    # 隐私审计
    PrivacyAuditor, AuditSeverity, AuditStatus, PrivacyControlType, AuditFinding, PrivacyAuditReport, get_privacy_auditor,
    run_privacy_audit,
    
    # 安全飞地
    SecureEnclave, EnclaveType, EnclaveAccess, SecureEnclaveConfig, EnclaveData, get_secure_enclave,
    store_in_enclave, retrieve_from_enclave,
    
    # 数据脱敏
    DataMasking, MaskingStrategy, MaskingRule, MaskedField, get_data_masking,
    mask_sensitive_text,
    
    # 隐私策略
    PrivacyPolicy, PolicyStatus, PolicyType, PolicyVersion, UserPolicyAcceptance, get_privacy_policy,
    
    # 数据保留
    DataRetention, RetentionPolicyType, DataCategory, RetentionPolicy, DataRetentionRule, get_data_retention,
    get_data_retention_policy, is_data_expired,
    
    # GDPR合规
    GDPRCompliance, GDPRRight, GDPRComplianceStatus, DataSubjectRequest, DataProcessingRecord, get_gdpr_compliance,
    submit_gdpr_request, export_user_data, delete_user_data, get_privacy_compliance_status,
    
    # 隐私指标
    PrivacyMetrics, PrivacyMetricPoint, get_privacy_metrics
)

from .security_monitoring import (
    # 威胁检测
    ThreatDetection, ThreatLevel, ThreatType, ThreatStatus, ThreatEvent, get_threat_detection,
    analyze_request_security, block_ip,
    
    # 行为分析
    BehaviorAnalysis, BehaviorPattern, AnomalyScore, UserBehaviorProfile, BehaviorAnomaly, get_behavior_analysis,
    
    # 合规检查
    ComplianceChecker, ComplianceStandard, ComplianceStatus, ControlCategory, ComplianceControl, ComplianceReport, get_compliance_checker,
    
    # 审计日志
    AuditLogger, AuditEventType, AuditSeverity, AuditEntry, get_audit_logger,
    log_security_event,
    
    # 事件响应
    IncidentResponse, IncidentSeverity, IncidentStatus, IncidentType, Incident, IncidentResponsePlan, get_incident_response,
    report_incident,
    
    # 安全策略
    SecurityPolicy, PolicyDomain, PolicyEffect, PolicyStatus, get_security_policy,
    
    # 漏洞扫描
    VulnerabilityScanner, VulnerabilitySeverity, VulnerabilityStatus, ScanType, Vulnerability, ScanResult, get_vulnerability_scanner,
    scan_for_vulnerabilities,
    
    # 入侵检测
    IntrusionDetection, IntrusionType, IntrusionSeverity, IntrusionStatus, IntrusionAlert, get_intrusion_detection,
    analyze_network_traffic,
    
    # 恶意软件防护
    MalwareProtection, MalwareType, MalwareSeverity, MalwareStatus, MalwareThreat, get_malware_protection,
    scan_file, quarantine_file,
    
    # 安全意识
    SecurityAwareness, TrainingType, TrainingStatus, TrainingModule, UserTraining, get_security_awareness,
    assign_security_training,
    
    # 风险评估
    RiskAssessment, RiskLevel, RiskCategory, RiskStatus, Risk, get_risk_assessment,
    assess_current_risks,
    
    # 安全指标
    SecurityMetrics, SecurityMetricPoint, get_security_metrics,
    get_security_posture,
    
    # 告警管理
    AlertManager, AlertSeverity, AlertStatus, Alert, AlertChannel, get_alert_manager
)

# 配置日志
logger = logging.getLogger(__name__)


def initialize_security(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化整个安全治理层
    
    该函数会依次初始化所有安全子模块：
    - 访问控制模块 (access_control)
    - 隐私保护模块 (privacy_protection)
    - 安全监控模块 (security_monitoring)
    
    并建立模块间的依赖关系，启动必要的后台任务。
    
    Args:
        config: 全局配置字典
        
    Returns:
        初始化是否成功
    """
    try:
        logger.info("=" * 60)
        logger.info("正在初始化Mirexs安全治理层...")
        logger.info("=" * 60)
        
        # 初始化访问控制模块
        logger.info("初始化访问控制模块...")
        if not access_control.initialize_access_control(config):
            logger.error("访问控制模块初始化失败")
            return False
        logger.info("✓ 访问控制模块初始化完成")
        
        # 初始化隐私保护模块
        logger.info("初始化隐私保护模块...")
        if not privacy_protection.initialize_privacy_protection(config):
            logger.error("隐私保护模块初始化失败")
            return False
        logger.info("✓ 隐私保护模块初始化完成")
        
        # 初始化安全监控模块
        logger.info("初始化安全监控模块...")
        if not security_monitoring.initialize_security_monitoring(config):
            logger.error("安全监控模块初始化失败")
            return False
        logger.info("✓ 安全监控模块初始化完成")
        
        # 验证模块间集成
        logger.info("验证安全模块集成...")
        if not _verify_integration():
            logger.error("安全模块集成验证失败")
            return False
        logger.info("✓ 安全模块集成验证通过")
        
        # 记录初始化日志
        audit_logger = security_monitoring.get_audit_logger()
        audit_logger.log_event(
            event_type=security_monitoring.AuditEventType.SYSTEM_START,
            user_id="system",
            details={
                "component": "security_layer",
                "version": __version__,
                "modules": ["access_control", "privacy_protection", "security_monitoring"]
            },
            severity=security_monitoring.AuditSeverity.INFO
        )
        
        logger.info("=" * 60)
        logger.info(f"安全治理层 v{__version__} 初始化完成")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"安全治理层初始化失败: {str(e)}")
        return False


def _verify_integration() -> bool:
    """
    验证模块间集成是否正常
    
    Returns:
        集成是否正常
    """
    try:
        # 验证访问控制与审计日志的集成
        access_logger = access_control.get_access_logger()
        if not access_logger:
            logger.error("访问日志模块不可用")
            return False
        
        # 验证隐私保护与密钥管理的集成
        key_management = access_control.get_key_management()
        data_encryption = privacy_protection.get_data_encryption()
        if not key_management or not data_encryption:
            logger.error("加密模块集成失败")
            return False
        
        # 验证安全监控与事件响应的集成
        threat_detection = security_monitoring.get_threat_detection()
        incident_response = security_monitoring.get_incident_response()
        if not threat_detection or not incident_response:
            logger.error("安全监控模块集成失败")
            return False
        
        # 验证跨模块功能
        test_user = "integration_test"
        
        # 测试权限检查
        perm_result = access_control.check_user_permission(test_user, "system:monitor")
        
        # 测试审计日志
        log_id = security_monitoring.log_security_event(
            event_type="integration_test",
            user_id=test_user,
            details={"test": "integration_check"}
        )
        
        if not log_id:
            logger.error("审计日志记录失败")
            return False
        
        logger.debug("安全模块集成验证通过")
        return True
        
    except Exception as e:
        logger.error(f"集成验证异常: {str(e)}")
        return False


def shutdown_security() -> bool:
    """
    关闭安全治理层，清理资源
    
    Returns:
        是否成功关闭
    """
    try:
        logger.info("正在关闭安全治理层...")
        
        # 按相反顺序关闭模块
        # 1. 先关闭安全监控（停止监控任务）
        if not security_monitoring.shutdown_security_monitoring():
            logger.warning("安全监控模块关闭时出现异常")
        
        # 2. 关闭隐私保护（保存隐私配置）
        if not privacy_protection.shutdown_privacy_protection():
            logger.warning("隐私保护模块关闭时出现异常")
        
        # 3. 最后关闭访问控制（清理会话）
        if not access_control.shutdown_access_control():
            logger.warning("访问控制模块关闭时出现异常")
        
        logger.info("安全治理层已关闭")
        return True
        
    except Exception as e:
        logger.error(f"关闭安全治理层失败: {str(e)}")
        return False


def get_security_status() -> Dict[str, Any]:
    """
    获取安全治理层整体状态
    
    Returns:
        状态字典
    """
    status = {
        "version": __version__,
        "initialized": True,
        "modules": {},
        "summary": {}
    }
    
    try:
        # 获取访问控制状态
        perm_manager = access_control.get_permission_manager()
        session_manager = access_control.get_session_manager()
        
        status["modules"]["access_control"] = {
            "roles_count": len(perm_manager.get_all_roles()),
            "active_sessions": session_manager.get_statistics().get("active_sessions", 0)
        }
        
        # 获取隐私保护状态
        consent_manager = privacy_protection.get_consent_manager()
        data_retention = privacy_protection.get_data_retention()
        
        status["modules"]["privacy_protection"] = {
            "consents_count": consent_manager.get_statistics().get("total_consents", 0),
            "retention_policies": data_retention.get_statistics().get("total_policies", 0)
        }
        
        # 获取安全监控状态
        threat_detection = security_monitoring.get_threat_detection()
        incident_response = security_monitoring.get_incident_response()
        vulnerability_scanner = security_monitoring.get_vulnerability_scanner()
        
        status["modules"]["security_monitoring"] = {
            "threats_count": threat_detection.get_threat_statistics().get("total_threats", 0),
            "incidents_pending": incident_response.get_statistics().get("pending_count", 0),
            "vulnerabilities_total": vulnerability_scanner.get_statistics().get("total_vulnerabilities", 0)
        }
        
        # 计算整体安全评分
        posture = security_monitoring.get_security_posture()
        status["summary"]["security_posture"] = posture["posture_level"]
        status["summary"]["security_score"] = posture["posture_score"]
        
    except Exception as e:
        logger.error(f"获取安全状态失败: {str(e)}")
        status["error"] = str(e)
    
    return status


# 导出所有子模块
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    
    # 初始化/关闭函数
    'initialize_security',
    'shutdown_security',
    'get_security_status',
    
    # 子模块
    'access_control',
    'privacy_protection',
    'security_monitoring',
    
    # 访问控制导出
    'BiometricAuth', 'BiometricType', 'BiometricAuthLevel', 'BiometricAuthResult', 'get_biometric_auth',
    'MultiFactorAuth', 'AuthFactorType', 'AuthFactorStatus', 'AuthResult', 'get_multi_factor_auth',
    'PermissionManager', 'Permission', 'ResourceType', 'AccessType', 'Role', 'PermissionCheckResult', 'get_permission_manager',
    'KeyManagement', 'KeyType', 'KeyAlgorithm', 'KeyStatus', 'KeyPurpose', 'KeyMetadata', 'get_key_management',
    'IdentityVerifier', 'VerificationMethod', 'VerificationLevel', 'VerificationRequest', 'VerificationResult', 'get_identity_verifier',
    'AccessLogger', 'LogAccessType', 'AccessResult', 'AccessLogEntry', 'get_access_logger',
    'SessionManager', 'Session', 'SessionStatus', 'SessionCreateResult', 'get_session_manager',
    'RoleBasedAccess', 'AccessDecision', 'AccessRequest', 'AccessDecisionResult', 'get_role_based_access',
    'AttributeBasedAccess', 'AttributeType', 'Operator', 'AttributeCondition', 'ABACPolicy', 'AttributeContext', 'get_attribute_based_access',
    'AccessPolicy', 'PolicyType', 'PolicyEffect', 'Policy', 'get_access_policy',
    'AccessMetrics', 'MetricDefinition', 'MetricPoint', 'get_access_metrics',
    'quick_authenticate', 'check_user_permission', 'get_user_effective_permissions',
    
    # 隐私保护导出
    'DataEncryption', 'EncryptionAlgorithm', 'EncryptionMode', 'EncryptedData', 'get_data_encryption',
    'encrypt_sensitive_data', 'decrypt_sensitive_data',
    'DifferentialPrivacy', 'PrivacyMechanism', 'SensitivityType', 'PrivacyBudget', 'DPResult', 'get_differential_privacy',
    'add_differential_privacy',
    'ConsentManager', 'ConsentStatus', 'ConsentPurpose', 'ConsentSource', 'ConsentRecord', 'ConsentTemplate', 'get_consent_manager',
    'check_user_consent', 'grant_user_consent', 'revoke_user_consent',
    'AnonymizationEngine', 'AnonymizationTechnique', 'DataType', 'AnonymizationRule', 'AnonymizationResult', 'get_anonymization_engine',
    'anonymize_data',
    'PrivacyAuditor', 'AuditSeverity', 'AuditStatus', 'PrivacyControlType', 'AuditFinding', 'PrivacyAuditReport', 'get_privacy_auditor',
    'run_privacy_audit',
    'SecureEnclave', 'EnclaveType', 'EnclaveAccess', 'SecureEnclaveConfig', 'EnclaveData', 'get_secure_enclave',
    'store_in_enclave', 'retrieve_from_enclave',
    'DataMasking', 'MaskingStrategy', 'MaskingRule', 'MaskedField', 'get_data_masking',
    'mask_sensitive_text',
    'PrivacyPolicy', 'PolicyStatus', 'PolicyType', 'PolicyVersion', 'UserPolicyAcceptance', 'get_privacy_policy',
    'DataRetention', 'RetentionPolicyType', 'DataCategory', 'RetentionPolicy', 'DataRetentionRule', 'get_data_retention',
    'get_data_retention_policy', 'is_data_expired',
    'GDPRCompliance', 'GDPRRight', 'GDPRComplianceStatus', 'DataSubjectRequest', 'DataProcessingRecord', 'get_gdpr_compliance',
    'submit_gdpr_request', 'export_user_data', 'delete_user_data', 'get_privacy_compliance_status',
    'PrivacyMetrics', 'PrivacyMetricPoint', 'get_privacy_metrics',
    
    # 安全监控导出
    'ThreatDetection', 'ThreatLevel', 'ThreatType', 'ThreatStatus', 'ThreatEvent', 'get_threat_detection',
    'analyze_request_security', 'block_ip',
    'BehaviorAnalysis', 'BehaviorPattern', 'AnomalyScore', 'UserBehaviorProfile', 'BehaviorAnomaly', 'get_behavior_analysis',
    'ComplianceChecker', 'ComplianceStandard', 'ComplianceStatus', 'ControlCategory', 'ComplianceControl', 'ComplianceReport', 'get_compliance_checker',
    'AuditLogger', 'AuditEventType', 'AuditSeverity', 'AuditEntry', 'get_audit_logger',
    'log_security_event',
    'IncidentResponse', 'IncidentSeverity', 'IncidentStatus', 'IncidentType', 'Incident', 'IncidentResponsePlan', 'get_incident_response',
    'report_incident',
    'SecurityPolicy', 'PolicyDomain', 'PolicyEffect', 'PolicyStatus', 'get_security_policy',
    'VulnerabilityScanner', 'VulnerabilitySeverity', 'VulnerabilityStatus', 'ScanType', 'Vulnerability', 'ScanResult', 'get_vulnerability_scanner',
    'scan_for_vulnerabilities',
    'IntrusionDetection', 'IntrusionType', 'IntrusionSeverity', 'IntrusionStatus', 'IntrusionAlert', 'get_intrusion_detection',
    'analyze_network_traffic',
    'MalwareProtection', 'MalwareType', 'MalwareSeverity', 'MalwareStatus', 'MalwareThreat', 'get_malware_protection',
    'scan_file', 'quarantine_file',
    'SecurityAwareness', 'TrainingType', 'TrainingStatus', 'TrainingModule', 'UserTraining', 'get_security_awareness',
    'assign_security_training',
    'RiskAssessment', 'RiskLevel', 'RiskCategory', 'RiskStatus', 'Risk', 'get_risk_assessment',
    'assess_current_risks',
    'SecurityMetrics', 'SecurityMetricPoint', 'get_security_metrics',
    'get_security_posture',
    'AlertManager', 'AlertSeverity', 'AlertStatus', 'Alert', 'AlertChannel', 'get_alert_manager'
]


# 模块初始化时的日志
logger.debug(f"Mirexs安全治理层 v{__version__} 已加载")
logger.debug(f"模块描述: {__description__}")
logger.debug(f"包含子模块: access_control, privacy_protection, security_monitoring")

