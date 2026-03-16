"""
安全监控模块 - 提供全面的安全监控和防护功能

该模块实现了多层次的安全监控机制，包括：
1. 威胁检测 (threat_detection) - 实时检测安全威胁
2. 行为分析 (behavior_analysis) - 分析用户行为模式
3. 合规检查 (compliance_checker) - 检查安全合规性
4. 审计日志 (audit_logger) - 记录安全审计日志
5. 事件响应 (incident_response) - 安全事件响应处理
6. 安全策略 (security_policy) - 安全管理策略
7. 漏洞扫描 (vulnerability_scanner) - 扫描系统安全漏洞
8. 入侵检测 (intrusion_detection) - 检测入侵行为
9. 恶意软件防护 (malware_protection) - 防护恶意软件
10. 安全意识 (security_awareness) - 安全培训和意识
11. 风险评估 (risk_assessment) - 安全风险评估
12. 安全指标 (security_metrics) - 安全系统性能指标
13. 告警管理 (alert_manager) - 统一告警管理

该模块是Mirexs安全治理层的核心组成部分，遵循"主动防御"的设计原则，
提供企业级的实时安全监控和防护能力。
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Mirexs Security Monitoring Module - Enterprise-grade security monitoring and protection"

# 导入所有子模块
from . import threat_detection
from . import behavior_analysis
from . import compliance_checker
from . import audit_logger
from . import incident_response
from . import security_policy
from . import vulnerability_scanner
from . import intrusion_detection
from . import malware_protection
from . import security_awareness
from . import risk_assessment
from . import security_metrics
from . import alert_manager

# 导出主要类和函数
from .threat_detection import (
    ThreatDetection,
    ThreatLevel,
    ThreatType,
    ThreatStatus,
    ThreatEvent,
    get_threat_detection
)

from .behavior_analysis import (
    BehaviorAnalysis,
    BehaviorPattern,
    AnomalyScore,
    UserBehaviorProfile,
    BehaviorAnomaly,
    get_behavior_analysis
)

from .compliance_checker import (
    ComplianceChecker,
    ComplianceStandard,
    ComplianceStatus,
    ControlCategory,
    ComplianceControl,
    ComplianceReport,
    get_compliance_checker
)

from .audit_logger import (
    AuditLogger,
    AuditEventType,
    AuditSeverity,
    AuditEntry,
    get_audit_logger
)

from .incident_response import (
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    Incident,
    IncidentResponsePlan,
    get_incident_response
)

from .security_policy import (
    SecurityPolicy,
    PolicyDomain,
    PolicyEffect,
    PolicyStatus,
    get_security_policy
)

from .vulnerability_scanner import (
    VulnerabilityScanner,
    VulnerabilitySeverity,
    VulnerabilityStatus,
    ScanType,
    Vulnerability,
    ScanResult,
    get_vulnerability_scanner
)

from .intrusion_detection import (
    IntrusionDetection,
    IntrusionType,
    IntrusionSeverity,
    IntrusionStatus,
    IntrusionAlert,
    get_intrusion_detection
)

from .malware_protection import (
    MalwareProtection,
    MalwareType,
    MalwareSeverity,
    MalwareStatus,
    MalwareThreat,
    get_malware_protection
)

from .security_awareness import (
    SecurityAwareness,
    TrainingType,
    TrainingStatus,
    TrainingModule,
    UserTraining,
    get_security_awareness
)

from .risk_assessment import (
    RiskAssessment,
    RiskLevel,
    RiskCategory,
    RiskStatus,
    Risk,
    get_risk_assessment
)

from .security_metrics import (
    SecurityMetrics,
    SecurityMetricPoint,
    get_security_metrics
)

from .alert_manager import (
    AlertManager,
    AlertSeverity,
    AlertStatus,
    Alert,
    AlertChannel,
    get_alert_manager
)

# 配置日志
logger = logging.getLogger(__name__)


def initialize_security_monitoring(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化整个安全监控模块
    
    该函数会初始化所有子模块，建立必要的依赖关系，
    并启动后台任务（如实时监控、自动扫描、事件处理等）。
    
    Args:
        config: 全局配置字典
        
    Returns:
        初始化是否成功
    """
    try:
        logger.info("正在初始化安全监控模块...")
        
        # 获取所有单例实例（自动初始化）
        threat_detection = get_threat_detection()
        behavior_analysis = get_behavior_analysis()
        compliance_checker = get_compliance_checker()
        audit_logger = get_audit_logger()
        incident_response = get_incident_response()
        security_policy = get_security_policy()
        vulnerability_scanner = get_vulnerability_scanner()
        intrusion_detection = get_intrusion_detection()
        malware_protection = get_malware_protection()
        security_awareness = get_security_awareness()
        risk_assessment = get_risk_assessment()
        security_metrics = get_security_metrics()
        alert_manager = get_alert_manager()
        
        # 创建事件循环（如果不存在）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 启动威胁检测监控
        loop.create_task(threat_detection.start_monitoring())
        logger.info("威胁检测监控已启动")
        
        # 启动入侵检测监控
        loop.create_task(intrusion_detection.start_monitoring())
        logger.info("入侵检测监控已启动")
        
        # 启动漏洞自动扫描
        if vulnerability_scanner.config.get("auto_scan_enabled", True):
            loop.create_task(vulnerability_scanner.start_auto_scan())
            logger.info(f"漏洞自动扫描已启动，间隔 {vulnerability_scanner.config.get('scan_interval_hours', 24)} 小时")
        
        # 启动事件处理器
        loop.create_task(incident_response.start_processor())
        logger.info("事件处理器已启动")
        
        # 启动恶意软件实时监控
        if malware_protection.config.get("real_time_protection", True):
            loop.create_task(malware_protection.start_monitoring())
            logger.info("恶意软件实时监控已启动")
        
        # 启动指标收集
        async def metrics_loop():
            while True:
                try:
                    await asyncio.sleep(security_metrics.config["collection_interval_seconds"])
                    security_metrics.collect_all_metrics()
                    
                    # 定期保存快照
                    if int(time.time()) % security_metrics.config["report_interval_seconds"] == 0:
                        security_metrics.save_snapshot()
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"指标收集任务异常: {str(e)}")
        
        loop.create_task(metrics_loop())
        logger.info(f"安全指标收集任务已启动，间隔 {security_metrics.config['collection_interval_seconds']} 秒")
        
        # 启动定期风险评估
        async def risk_assessment_loop():
            while True:
                try:
                    await asyncio.sleep(risk_assessment.config.get("assessment_interval_days", 30) * 24 * 3600)
                    await risk_assessment.assess_risks(assessed_by="system", scope="full")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"风险评估任务异常: {str(e)}")
        
        loop.create_task(risk_assessment_loop())
        logger.info(f"定期风险评估已启动，间隔 {risk_assessment.config.get('assessment_interval_days', 30)} 天")
        
        # 记录审计日志
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_START,
            user_id="system",
            details={
                "status": "success",
                "version": __version__,
                "modules": [
                    "threat_detection", "behavior_analysis", "compliance_checker",
                    "audit_logger", "incident_response", "security_policy",
                    "vulnerability_scanner", "intrusion_detection", "malware_protection",
                    "security_awareness", "risk_assessment", "security_metrics",
                    "alert_manager"
                ]
            },
            severity=AuditSeverity.INFO
        )
        
        logger.info("安全监控模块初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"安全监控模块初始化失败: {str(e)}")
        
        # 尝试记录错误日志
        try:
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                event_type=AuditEventType.SYSTEM_START,
                user_id="system",
                details={"status": "failed", "error": str(e)},
                severity=AuditSeverity.CRITICAL
            )
        except:
            pass
        
        return False


def shutdown_security_monitoring() -> bool:
    """
    关闭安全监控模块，清理资源
    
    Returns:
        是否成功关闭
    """
    try:
        logger.info("正在关闭安全监控模块...")
        
        # 获取所有管理器实例
        threat_detection = get_threat_detection()
        intrusion_detection = get_intrusion_detection()
        vulnerability_scanner = get_vulnerability_scanner()
        incident_response = get_incident_response()
        malware_protection = get_malware_protection()
        security_metrics = get_security_metrics()
        audit_logger = get_audit_logger()
        
        # 停止所有监控任务
        loop = asyncio.get_event_loop()
        
        # 停止威胁检测
        loop.create_task(threat_detection.stop_monitoring())
        
        # 停止入侵检测
        loop.create_task(intrusion_detection.stop_monitoring())
        
        # 停止漏洞扫描
        loop.create_task(vulnerability_scanner.stop_auto_scan())
        
        # 停止事件处理器
        loop.create_task(incident_response.stop_processor())
        
        # 停止恶意软件监控
        loop.create_task(malware_protection.stop_monitoring())
        
        # 保存最终指标快照
        security_metrics.save_snapshot()
        
        # 生成最终风险评估
        loop.run_until_complete(risk_assessment.assess_risks(
            assessed_by="system",
            scope="shutdown"
        ))
        
        # 记录审计日志
        audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_STOP,
            user_id="system",
            details={"status": "success"},
            severity=AuditSeverity.INFO
        )
        
        logger.info("安全监控模块已关闭")
        return True
        
    except Exception as e:
        logger.error(f"关闭安全监控模块失败: {str(e)}")
        return False


# 便捷函数 - 威胁检测
def analyze_request_security(request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    便捷函数：分析请求的安全威胁
    
    Args:
        request_data: 请求数据
    
    Returns:
        检测到的威胁信息
    """
    import asyncio
    
    threat_detection = get_threat_detection()
    loop = asyncio.new_event_loop()
    try:
        threat = loop.run_until_complete(threat_detection.analyze_request(request_data))
        if threat:
            return {
                "threat_id": threat.event_id,
                "type": threat.threat_type.value,
                "level": threat.level.value,
                "description": threat.description,
                "confidence": threat.confidence
            }
        return None
    finally:
        loop.close()


def block_ip(source_ip: str, reason: str) -> bool:
    """
    便捷函数：封禁IP地址
    
    Args:
        source_ip: IP地址
        reason: 封禁原因
    
    Returns:
        是否成功
    """
    threat_detection = get_threat_detection()
    return threat_detection.add_to_blacklist(source_ip, reason)


# 便捷函数 - 入侵检测
def analyze_network_traffic(
    source_ip: str,
    dest_port: int,
    protocol: str,
    packet_size: int,
    flags: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：分析网络流量
    
    Args:
        source_ip: 源IP
        dest_port: 目标端口
        protocol: 协议
        packet_size: 包大小
        flags: TCP标志
    
    Returns:
        入侵告警信息
    """
    import asyncio
    
    intrusion_detection = get_intrusion_detection()
    loop = asyncio.new_event_loop()
    try:
        alert = loop.run_until_complete(intrusion_detection.analyze_network_traffic(
            source_ip, dest_port, protocol, packet_size, flags
        ))
        if alert:
            return {
                "alert_id": alert.alert_id,
                "type": alert.intrusion_type.value,
                "severity": alert.severity.value,
                "description": alert.description,
                "confidence": alert.confidence
            }
        return None
    finally:
        loop.close()


# 便捷函数 - 审计日志
def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    source_ip: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: str = "info"
) -> str:
    """
    便捷函数：记录安全事件
    
    Args:
        event_type: 事件类型
        user_id: 用户ID
        source_ip: 源IP
        resource: 资源
        action: 操作
        details: 详细信息
        severity: 严重性
    
    Returns:
        日志条目ID
    """
    audit_logger = get_audit_logger()
    
    # 映射字符串到枚举
    severity_map = {
        "debug": AuditSeverity.DEBUG,
        "info": AuditSeverity.INFO,
        "warning": AuditSeverity.WARNING,
        "error": AuditSeverity.ERROR,
        "critical": AuditSeverity.CRITICAL
    }
    
    try:
        event_type_enum = AuditEventType(event_type)
    except ValueError:
        # 如果不是预定义类型，使用自定义
        event_type_enum = AuditEventType.SYSTEM_UPDATE
    
    return audit_logger.log_event(
        event_type=event_type_enum,
        user_id=user_id,
        source_ip=source_ip,
        resource=resource,
        action=action,
        status="success",
        severity=severity_map.get(severity, AuditSeverity.INFO),
        details=details or {}
    )


# 便捷函数 - 事件响应
def report_incident(
    title: str,
    description: str,
    severity: str,
    incident_type: str,
    affected_users: Optional[List[str]] = None,
    affected_resources: Optional[List[str]] = None,
    reported_by: str = "system"
) -> Optional[Dict[str, Any]]:
    """
    便捷函数：报告安全事件
    
    Args:
        title: 标题
        description: 描述
        severity: 严重性
        incident_type: 事件类型
        affected_users: 受影响用户
        affected_resources: 受影响资源
        reported_by: 报告者
    
    Returns:
        创建的事件信息
    """
    import asyncio
    
    incident_response = get_incident_response()
    
    # 映射字符串到枚举
    severity_map = {
        "critical": IncidentSeverity.CRITICAL,
        "high": IncidentSeverity.HIGH,
        "medium": IncidentSeverity.MEDIUM,
        "low": IncidentSeverity.LOW,
        "info": IncidentSeverity.INFO
    }
    
    type_map = {
        "unauthorized_access": IncidentType.UNAUTHORIZED_ACCESS,
        "data_breach": IncidentType.DATA_BREACH,
        "malware": IncidentType.MALWARE_INFECTION,
        "dos": IncidentType.DOS_ATTACK,
        "account_compromise": IncidentType.ACCOUNT_COMPROMISE,
        "privilege_escalation": IncidentType.PRIVILEGE_ESCALATION
    }
    
    loop = asyncio.new_event_loop()
    try:
        incident = loop.run_until_complete(incident_response.create_incident(
            incident_type=type_map.get(incident_type, IncidentType.POLICY_VIOLATION),
            severity=severity_map.get(severity, IncidentSeverity.MEDIUM),
            title=title,
            description=description,
            detected_by=reported_by,
            affected_users=affected_users or [],
            affected_resources=affected_resources or []
        ))
        
        return {
            "incident_id": incident.incident_id,
            "status": incident.status.value,
            "detected_at": incident.detected_at
        }
    finally:
        loop.close()


# 便捷函数 - 漏洞扫描
def scan_for_vulnerabilities(scan_type: str = "full") -> Dict[str, Any]:
    """
    便捷函数：执行漏洞扫描
    
    Args:
        scan_type: 扫描类型
    
    Returns:
        扫描结果摘要
    """
    import asyncio
    
    scanner = get_vulnerability_scanner()
    
    type_map = {
        "full": ScanType.FULL,
        "config": ScanType.CONFIGURATION,
        "dependency": ScanType.DEPENDENCY,
        "permission": ScanType.PERMISSION,
        "compliance": ScanType.COMPLIANCE
    }
    
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(scanner.scan(
            scan_type=type_map.get(scan_type, ScanType.FULL)
        ))
        
        return {
            "scan_id": result.scan_id,
            "vulnerabilities_found": len(result.vulnerabilities),
            "summary": result.summary,
            "duration_seconds": result.end_time - result.start_time
        }
    finally:
        loop.close()


# 便捷函数 - 恶意软件防护
def scan_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：扫描文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        扫描结果
    """
    import asyncio
    
    malware_protection = get_malware_protection()
    
    loop = asyncio.new_event_loop()
    try:
        threat = loop.run_until_complete(malware_protection.scan_file(file_path))
        if threat:
            return {
                "threat_id": threat.threat_id,
                "name": threat.name,
                "type": threat.malware_type.value,
                "severity": threat.severity.value,
                "description": threat.description
            }
        return None
    finally:
        loop.close()


def quarantine_file(file_path: str, threat_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    便捷函数：隔离文件
    
    Args:
        file_path: 文件路径
        threat_id: 威胁ID
    
    Returns:
        (成功标志, 消息)
    """
    malware_protection = get_malware_protection()
    
    if threat_id:
        return asyncio.run(malware_protection.quarantine_file(threat_id))
    
    # 如果没有威胁ID，先扫描
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        threat = loop.run_until_complete(malware_protection.scan_file(file_path))
        if threat:
            return loop.run_until_complete(malware_protection.quarantine_file(threat.threat_id))
        return False, "未检测到威胁"
    finally:
        loop.close()


# 便捷函数 - 安全意识
def assign_security_training(
    user_id: str,
    module_id: Optional[str] = None,
    assigned_by: str = "system"
) -> Dict[str, Any]:
    """
    便捷函数：分配安全培训
    
    Args:
        user_id: 用户ID
        module_id: 模块ID（None表示分配所有必需培训）
        assigned_by: 分配者
    
    Returns:
        分配结果
    """
    awareness = get_security_awareness()
    
    if module_id:
        success, message, training = awareness.assign_training(user_id, module_id, assigned_by)
        if success and training:
            return {
                "success": True,
                "record_id": training.record_id,
                "module_id": module_id,
                "status": training.status.value
            }
        return {"success": False, "message": message}
    else:
        # 分配所有必需培训
        from ..access_control.permission_manager import get_permission_manager
        perm_manager = get_permission_manager()
        user_roles = perm_manager.get_user_roles(user_id)
        role_names = [r["name"] for r in user_roles]
        
        required = awareness.get_required_trainings(user_id, role_names)
        results = []
        
        for module in required:
            success, message, training = awareness.assign_training(
                user_id, module["module_id"], assigned_by
            )
            if success:
                results.append({
                    "module_id": module["module_id"],
                    "name": module["name"],
                    "status": "assigned"
                })
        
        return {
            "success": len(results) > 0,
            "assigned_count": len(results),
            "trainings": results
        }


# 便捷函数 - 风险评估
async def assess_current_risks(assessed_by: str = "system") -> Dict[str, Any]:
    """
    便捷函数：评估当前风险
    
    Args:
        assessed_by: 评估者
    
    Returns:
        风险评估结果
    """
    risk_assessment = get_risk_assessment()
    result = await risk_assessment.assess_risks(assessed_by, "current")
    
    return {
        "assessment_id": result.assessment_id,
        "total_risks": result.summary.get("total_risks", 0),
        "critical_risks": result.summary.get("critical", 0),
        "high_risks": result.summary.get("high", 0),
        "risk_score": result.summary.get("total_risk_score", 0),
        "recommendations": result.recommendations[:5]
    }


# 便捷函数 - 安全态势
def get_security_posture() -> Dict[str, Any]:
    """
    便捷函数：获取当前安全态势
    
    Returns:
        安全态势报告
    """
    metrics = get_security_metrics()
    report = metrics.get_report()
    
    return {
        "timestamp": report["generated_at"],
        "posture_level": report["security_posture"]["level"],
        "posture_score": report["security_posture"]["overall"],
        "summary": report["summary"],
        "threats": report["summary"]["total_threats"],
        "incidents": report["summary"]["total_incidents"],
        "vulnerabilities": report["summary"]["total_vulnerabilities"],
        "compliance": report["summary"]["compliance_score"]
    }


# 导出模块级别的函数
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    
    # 初始化/关闭函数
    'initialize_security_monitoring',
    'shutdown_security_monitoring',
    
    # 威胁检测
    'ThreatDetection',
    'ThreatLevel',
    'ThreatType',
    'ThreatStatus',
    'ThreatEvent',
    'get_threat_detection',
    'analyze_request_security',
    'block_ip',
    
    # 行为分析
    'BehaviorAnalysis',
    'BehaviorPattern',
    'AnomalyScore',
    'UserBehaviorProfile',
    'BehaviorAnomaly',
    'get_behavior_analysis',
    
    # 合规检查
    'ComplianceChecker',
    'ComplianceStandard',
    'ComplianceStatus',
    'ControlCategory',
    'ComplianceControl',
    'ComplianceReport',
    'get_compliance_checker',
    
    # 审计日志
    'AuditLogger',
    'AuditEventType',
    'AuditSeverity',
    'AuditEntry',
    'get_audit_logger',
    'log_security_event',
    
    # 事件响应
    'IncidentResponse',
    'IncidentSeverity',
    'IncidentStatus',
    'IncidentType',
    'Incident',
    'IncidentResponsePlan',
    'get_incident_response',
    'report_incident',
    
    # 安全策略
    'SecurityPolicy',
    'PolicyDomain',
    'PolicyEffect',
    'PolicyStatus',
    'get_security_policy',
    
    # 漏洞扫描
    'VulnerabilityScanner',
    'VulnerabilitySeverity',
    'VulnerabilityStatus',
    'ScanType',
    'Vulnerability',
    'ScanResult',
    'get_vulnerability_scanner',
    'scan_for_vulnerabilities',
    
    # 入侵检测
    'IntrusionDetection',
    'IntrusionType',
    'IntrusionSeverity',
    'IntrusionStatus',
    'IntrusionAlert',
    'get_intrusion_detection',
    'analyze_network_traffic',
    
    # 恶意软件防护
    'MalwareProtection',
    'MalwareType',
    'MalwareSeverity',
    'MalwareStatus',
    'MalwareThreat',
    'get_malware_protection',
    'scan_file',
    'quarantine_file',
    
    # 安全意识
    'SecurityAwareness',
    'TrainingType',
    'TrainingStatus',
    'TrainingModule',
    'UserTraining',
    'get_security_awareness',
    'assign_security_training',
    
    # 风险评估
    'RiskAssessment',
    'RiskLevel',
    'RiskCategory',
    'RiskStatus',
    'Risk',
    'get_risk_assessment',
    'assess_current_risks',
    
    # 安全指标
    'SecurityMetrics',
    'SecurityMetricPoint',
    'get_security_metrics',
    'get_security_posture',
    
    # 告警管理
    'AlertManager',
    'AlertSeverity',
    'AlertStatus',
    'Alert',
    'AlertChannel',
    'get_alert_manager',
]


# 模块初始化时的日志
logger.debug(f"安全监控模块 v{__version__} 已加载")
logger.debug(f"模块描述: {__description__}")

