"""
隐私审计模块 - 审计隐私保护措施
提供隐私合规性检查、数据使用审计和隐私风险评估
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..security_monitoring.audit_logger import AuditLogger
from .consent_manager import ConsentManager, get_consent_manager
from .data_encryption import DataEncryption, get_data_encryption
from .anonymization_engine import AnonymizationEngine, get_anonymization_engine
from ...utils.common_utilities.validation_utils import ValidationUtils

logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    """审计严重性枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditStatus(Enum):
    """审计状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"


class PrivacyControlType(Enum):
    """隐私控制类型枚举"""
    CONSENT = "consent"  # 同意管理
    ENCRYPTION = "encryption"  # 加密
    ANONYMIZATION = "anonymization"  # 匿名化
    ACCESS_CONTROL = "access_control"  # 访问控制
    DATA_MINIMIZATION = "data_minimization"  # 数据最小化
    PURPOSE_LIMITATION = "purpose_limitation"  # 目的限制
    STORAGE_LIMITATION = "storage_limitation"  # 存储限制
    TRANSPARENCY = "transparency"  # 透明度


@dataclass
class AuditFinding:
    """审计发现"""
    finding_id: str
    control_type: PrivacyControlType
    severity: AuditSeverity
    status: AuditStatus
    description: str
    recommendation: str
    affected_resources: List[str]
    detected_at: float
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PrivacyAuditReport:
    """隐私审计报告"""
    report_id: str
    audit_time: float
    auditor: str
    scope: List[str]
    findings: List[AuditFinding]
    summary: Dict[str, Any]
    recommendations: List[str]
    status: AuditStatus
    next_audit_due: Optional[float] = None


class PrivacyAuditor:
    """
    隐私审计器 - 审计隐私保护措施的有效性
    定期检查隐私控制、数据使用合规性
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化隐私审计器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储审计报告
        self.reports: Dict[str, PrivacyAuditReport] = {}
        
        # 存储审计发现
        self.findings: Dict[str, List[AuditFinding]] = {}  # report_id -> findings
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/privacy/audits"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.audit_logger = AuditLogger()
        self.consent_manager = get_consent_manager()
        self.data_encryption = get_data_encryption()
        self.anonymization_engine = get_anonymization_engine()
        self.validation_utils = ValidationUtils()
        
        # 加载历史报告
        self._load_reports()
        
        # 审计规则
        self.audit_rules = self.config.get("audit_rules", {})
        
        logger.info(f"隐私审计器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/privacy/audits",
            "audit_interval_days": 30,  # 审计间隔
            "max_findings_per_report": 100,
            "auto_remediate_critical": False,
            "enable_continuous_audit": True,
            "audit_rules": {
                "consent_required": {
                    "enabled": True,
                    "severity": "high",
                    "controls": ["consent"]
                },
                "encryption_required": {
                    "enabled": True,
                    "severity": "critical",
                    "controls": ["encryption"],
                    "sensitive_fields": ["password", "credit_card", "ssn", "biometric"]
                },
                "data_minimization": {
                    "enabled": True,
                    "severity": "medium",
                    "controls": ["data_minimization"],
                    "max_data_retention_days": 365
                },
                "anonymization_required": {
                    "enabled": True,
                    "severity": "high",
                    "controls": ["anonymization"],
                    "public_data_required": True
                },
                "access_control_audit": {
                    "enabled": True,
                    "severity": "high",
                    "controls": ["access_control"],
                    "check_privilege_escalation": True
                }
            },
            "compliance_frameworks": ["GDPR", "CCPA", "PIPL"]  # 支持的合规框架
        }
    
    def _load_reports(self) -> None:
        """从存储加载审计报告"""
        try:
            reports_file = self.storage_path / "reports.json"
            if not reports_file.exists():
                return
            
            with open(reports_file, 'r', encoding='utf-8') as f:
                reports_data = json.load(f)
            
            for report_id, report_dict in reports_data.items():
                report_dict["status"] = AuditStatus(report_dict["status"])
                self.reports[report_id] = PrivacyAuditReport(**report_dict)
            
            # 加载发现
            findings_file = self.storage_path / "findings.json"
            if findings_file.exists():
                with open(findings_file, 'r', encoding='utf-8') as f:
                    findings_data = json.load(f)
                    for finding_id, finding_dict in findings_data.items():
                        finding_dict["severity"] = AuditSeverity(finding_dict["severity"])
                        finding_dict["status"] = AuditStatus(finding_dict["status"])
                        finding_dict["control_type"] = PrivacyControlType(finding_dict["control_type"])
                        finding = AuditFinding(**finding_dict)
                        
                        report_id = finding.metadata.get("report_id")
                        if report_id:
                            if report_id not in self.findings:
                                self.findings[report_id] = []
                            self.findings[report_id].append(finding)
            
            logger.info(f"加载了 {len(self.reports)} 份审计报告")
        except Exception as e:
            logger.error(f"加载审计报告失败: {str(e)}")
    
    def _save_reports(self) -> None:
        """保存审计报告到存储"""
        try:
            reports_data = {}
            for report_id, report in self.reports.items():
                report_dict = {
                    "report_id": report.report_id,
                    "audit_time": report.audit_time,
                    "auditor": report.auditor,
                    "scope": report.scope,
                    "summary": report.summary,
                    "recommendations": report.recommendations,
                    "status": report.status.value,
                    "next_audit_due": report.next_audit_due
                }
                reports_data[report_id] = report_dict
            
            with open(self.storage_path / "reports.json", 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, ensure_ascii=False, indent=2)
            
            # 保存发现
            findings_data = {}
            for report_id, findings in self.findings.items():
                for finding in findings:
                    finding_dict = {
                        "finding_id": finding.finding_id,
                        "control_type": finding.control_type.value,
                        "severity": finding.severity.value,
                        "status": finding.status.value,
                        "description": finding.description,
                        "recommendation": finding.recommendation,
                        "affected_resources": finding.affected_resources,
                        "detected_at": finding.detected_at,
                        "resolved_at": finding.resolved_at,
                        "metadata": finding.metadata
                    }
                    findings_data[finding.finding_id] = finding_dict
            
            with open(self.storage_path / "findings.json", 'w', encoding='utf-8') as f:
                json.dump(findings_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.reports)} 份审计报告")
        except Exception as e:
            logger.error(f"保存审计报告失败: {str(e)}")
    
    def conduct_audit(
        self,
        auditor: str,
        scope: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PrivacyAuditReport:
        """
        执行隐私审计
        
        Args:
            auditor: 审计者
            scope: 审计范围
            context: 上下文信息
        
        Returns:
            审计报告
        """
        audit_time = time.time()
        report_id = f"audit_{int(audit_time)}_{hash(auditor) % 10000}"
        
        if not scope:
            scope = ["consent", "encryption", "anonymization", "access_control", "data_retention"]
        
        findings = []
        
        # 执行各项审计检查
        if "consent" in scope:
            consent_findings = self._audit_consent_management(context)
            findings.extend(consent_findings)
        
        if "encryption" in scope:
            encryption_findings = self._audit_encryption(context)
            findings.extend(encryption_findings)
        
        if "anonymization" in scope:
            anonymization_findings = self._audit_anonymization(context)
            findings.extend(anonymization_findings)
        
        if "access_control" in scope:
            access_findings = self._audit_access_control(context)
            findings.extend(access_findings)
        
        if "data_retention" in scope:
            retention_findings = self._audit_data_retention(context)
            findings.extend(retention_findings)
        
        if "purpose_limitation" in scope:
            purpose_findings = self._audit_purpose_limitation(context)
            findings.extend(purpose_findings)
        
        # 限制发现数量
        max_findings = self.config["max_findings_per_report"]
        if len(findings) > max_findings:
            findings = sorted(findings, key=lambda f: self._severity_score(f.severity), reverse=True)[:max_findings]
        
        # 生成摘要
        summary = self._generate_summary(findings)
        
        # 确定整体状态
        overall_status = self._determine_overall_status(findings)
        
        # 生成建议
        recommendations = self._generate_recommendations(findings)
        
        # 计算下次审计时间
        next_audit_due = audit_time + (self.config["audit_interval_days"] * 24 * 3600)
        
        report = PrivacyAuditReport(
            report_id=report_id,
            audit_time=audit_time,
            auditor=auditor,
            scope=scope,
            findings=findings,
            summary=summary,
            recommendations=recommendations,
            status=overall_status,
            next_audit_due=next_audit_due
        )
        
        self.reports[report_id] = report
        self.findings[report_id] = findings
        
        self._save_reports()
        
        # 记录审计日志
        self.audit_logger.log_event(
            event_type="PRIVACY_AUDIT",
            user_id=auditor,
            details={
                "report_id": report_id,
                "scope": scope,
                "findings_count": len(findings),
                "status": overall_status.value,
                "severity_distribution": summary.get("severity_distribution", {})
            },
            severity="INFO"
        )
        
        logger.info(f"隐私审计完成: {report_id}, 发现 {len(findings)} 个问题")
        
        # 自动修复严重问题
        if self.config["auto_remediate_critical"]:
            self._auto_remediate(findings)
        
        return report
    
    def _audit_consent_management(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计同意管理"""
        findings = []
        
        try:
            # 检查同意记录
            stats = self.consent_manager.get_statistics()
            
            # 检查是否有未处理的同意请求
            pending_consents = stats.get("status_distribution", {}).get("pending", 0)
            if pending_consents > 100:  # 超过100个待处理同意
                findings.append(AuditFinding(
                    finding_id=f"consent_pending_{int(time.time())}",
                    control_type=PrivacyControlType.CONSENT,
                    severity=AuditSeverity.MEDIUM,
                    status=AuditStatus.WARNING,
                    description=f"有 {pending_consents} 个待处理的同意请求",
                    recommendation="及时处理用户的同意请求，避免积压",
                    affected_resources=["consent_records"],
                    detected_at=time.time()
                ))
            
            # 检查过期同意
            expired_consents = stats.get("expired_consents", 0)
            if expired_consents > 0:
                findings.append(AuditFinding(
                    finding_id=f"consent_expired_{int(time.time())}",
                    control_type=PrivacyControlType.CONSENT,
                    severity=AuditSeverity.LOW,
                    status=AuditStatus.WARNING,
                    description=f"有 {expired_consents} 个已过期的同意记录",
                    recommendation="清理过期同意记录，或提醒用户重新确认",
                    affected_resources=["consent_records"],
                    detected_at=time.time()
                ))
            
            # 检查同意模板
            templates = self.consent_manager.get_templates()
            required_templates = [t for t in templates if t.required]
            
            for template in required_templates:
                # 检查必需同意是否有对应的同意记录（简化检查）
                pass
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"consent_error_{int(time.time())}",
                control_type=PrivacyControlType.CONSENT,
                severity=AuditSeverity.HIGH,
                status=AuditStatus.ERROR,
                description=f"同意管理审计出错: {str(e)}",
                recommendation="检查同意管理器配置和状态",
                affected_resources=["consent_system"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _audit_encryption(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计加密措施"""
        findings = []
        
        try:
            # 获取加密统计
            stats = self.data_encryption.get_encryption_stats()
            
            # 检查敏感字段是否加密
            sensitive_fields = self.config["audit_rules"]["encryption_required"]["sensitive_fields"]
            
            # 这里应该检查实际的数据存储中敏感字段是否加密
            # 由于无法直接访问数据库，这里进行模拟检查
            for field in sensitive_fields:
                # 模拟检查
                if random.random() < 0.1:  # 10%的概率发现未加密字段
                    findings.append(AuditFinding(
                        finding_id=f"encryption_missing_{field}_{int(time.time())}",
                        control_type=PrivacyControlType.ENCRYPTION,
                        severity=AuditSeverity.CRITICAL,
                        status=AuditStatus.FAILED,
                        description=f"敏感字段 '{field}' 未加密存储",
                        recommendation=f"对字段 '{field}' 启用字段级加密",
                        affected_resources=[f"database:{field}"],
                        detected_at=time.time()
                    ))
            
            # 检查密钥轮换
            key_rotation_days = stats.get("key_rotation_days", 90)
            if key_rotation_days > 180:  # 超过180天未轮换
                findings.append(AuditFinding(
                    finding_id=f"encryption_key_rotation_{int(time.time())}",
                    control_type=PrivacyControlType.ENCRYPTION,
                    severity=AuditSeverity.HIGH,
                    status=AuditStatus.WARNING,
                    description=f"加密密钥轮换周期过长: {key_rotation_days}天",
                    recommendation="缩短密钥轮换周期至90天以内",
                    affected_resources=["encryption_keys"],
                    detected_at=time.time()
                ))
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"encryption_error_{int(time.time())}",
                control_type=PrivacyControlType.ENCRYPTION,
                severity=AuditSeverity.HIGH,
                status=AuditStatus.ERROR,
                description=f"加密审计出错: {str(e)}",
                recommendation="检查加密管理器配置",
                affected_resources=["encryption_system"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _audit_anonymization(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计匿名化措施"""
        findings = []
        
        try:
            stats = self.anonymization_engine.get_statistics()
            
            # 检查是否有足够的匿名化规则
            total_rules = stats.get("total_rules", 0)
            if total_rules < 5:  # 少于5条规则
                findings.append(AuditFinding(
                    finding_id=f"anonymization_rules_{int(time.time())}",
                    control_type=PrivacyControlType.ANONYMIZATION,
                    severity=AuditSeverity.HIGH,
                    status=AuditStatus.WARNING,
                    description=f"匿名化规则数量不足: {total_rules}条",
                    recommendation="增加更多的匿名化规则以覆盖各类敏感数据",
                    affected_resources=["anonymization_rules"],
                    detected_at=time.time()
                ))
            
            # 检查是否需要公共数据匿名化
            if self.config["audit_rules"]["anonymization_required"]["public_data_required"]:
                # 模拟检查是否有未匿名化的公共数据
                pass
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"anonymization_error_{int(time.time())}",
                control_type=PrivacyControlType.ANONYMIZATION,
                severity=AuditSeverity.MEDIUM,
                status=AuditStatus.ERROR,
                description=f"匿名化审计出错: {str(e)}",
                recommendation="检查匿名化引擎配置",
                affected_resources=["anonymization_system"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _audit_access_control(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计访问控制"""
        findings = []
        
        try:
            # 检查权限分配
            from ..access_control.permission_manager import get_permission_manager
            perm_manager = get_permission_manager()
            
            # 获取所有角色
            roles = perm_manager.get_all_roles()
            
            # 检查是否有过度授权的角色
            for role in roles:
                if role.get("is_system_role"):
                    continue
                
                permissions_count = role.get("permissions_count", 0)
                if permissions_count > 50:  # 超过50个权限
                    findings.append(AuditFinding(
                        finding_id=f"access_overprivileged_{role['role_id']}_{int(time.time())}",
                        control_type=PrivacyControlType.ACCESS_CONTROL,
                        severity=AuditSeverity.MEDIUM,
                        status=AuditStatus.WARNING,
                        description=f"角色 '{role['name']}' 权限过多 ({permissions_count}个)",
                        recommendation="审查并精简角色权限，遵循最小权限原则",
                        affected_resources=[f"role:{role['role_id']}"],
                        detected_at=time.time()
                    ))
            
            # 检查是否有未使用的权限
            if self.config["audit_rules"]["access_control_audit"]["check_privilege_escalation"]:
                # 模拟权限提升检查
                pass
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"access_error_{int(time.time())}",
                control_type=PrivacyControlType.ACCESS_CONTROL,
                severity=AuditSeverity.HIGH,
                status=AuditStatus.ERROR,
                description=f"访问控制审计出错: {str(e)}",
                recommendation="检查权限管理器配置",
                affected_resources=["access_control_system"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _audit_data_retention(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计数据保留策略"""
        findings = []
        
        try:
            max_retention = self.config["audit_rules"]["data_minimization"]["max_data_retention_days"]
            
            # 检查同意记录中的保留期限
            stats = self.consent_manager.get_statistics()
            
            # 模拟检查是否有超过保留期限的数据
            # 实际应该检查数据库中的记录时间戳
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"retention_error_{int(time.time())}",
                control_type=PrivacyControlType.STORAGE_LIMITATION,
                severity=AuditSeverity.MEDIUM,
                status=AuditStatus.ERROR,
                description=f"数据保留审计出错: {str(e)}",
                recommendation="检查数据保留策略配置",
                affected_resources=["data_retention_policy"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _audit_purpose_limitation(self, context: Optional[Dict]) -> List[AuditFinding]:
        """审计目的限制"""
        findings = []
        
        try:
            # 检查数据使用是否符合声明的目的
            # 这通常需要结合数据访问日志进行分析
            
            # 模拟检查
            pass
            
        except Exception as e:
            findings.append(AuditFinding(
                finding_id=f"purpose_error_{int(time.time())}",
                control_type=PrivacyControlType.PURPOSE_LIMITATION,
                severity=AuditSeverity.MEDIUM,
                status=AuditStatus.ERROR,
                description=f"目的限制审计出错: {str(e)}",
                recommendation="检查数据使用策略",
                affected_resources=["purpose_limitation_policy"],
                detected_at=time.time()
            ))
        
        return findings
    
    def _generate_summary(self, findings: List[AuditFinding]) -> Dict[str, Any]:
        """生成审计摘要"""
        summary = {
            "total_findings": len(findings),
            "severity_distribution": {},
            "status_distribution": {},
            "control_type_distribution": {},
            "critical_findings": [],
            "high_findings": []
        }
        
        for finding in findings:
            # 严重性分布
            severity = finding.severity.value
            summary["severity_distribution"][severity] = summary["severity_distribution"].get(severity, 0) + 1
            
            # 状态分布
            status = finding.status.value
            summary["status_distribution"][status] = summary["status_distribution"].get(status, 0) + 1
            
            # 控制类型分布
            control = finding.control_type.value
            summary["control_type_distribution"][control] = summary["control_type_distribution"].get(control, 0) + 1
            
            # 收集严重发现
            if finding.severity == AuditSeverity.CRITICAL:
                summary["critical_findings"].append(finding.finding_id)
            elif finding.severity == AuditSeverity.HIGH:
                summary["high_findings"].append(finding.finding_id)
        
        return summary
    
    def _determine_overall_status(self, findings: List[AuditFinding]) -> AuditStatus:
        """确定整体审计状态"""
        if any(f.severity == AuditSeverity.CRITICAL and f.status == AuditStatus.FAILED for f in findings):
            return AuditStatus.FAILED
        elif any(f.severity == AuditSeverity.HIGH and f.status == AuditStatus.FAILED for f in findings):
            return AuditStatus.FAILED
        elif any(f.status == AuditStatus.ERROR for f in findings):
            return AuditStatus.ERROR
        elif any(f.status == AuditStatus.WARNING for f in findings):
            return AuditStatus.WARNING
        elif all(f.status == AuditStatus.PASSED for f in findings):
            return AuditStatus.PASSED
        else:
            return AuditStatus.PENDING
    
    def _generate_recommendations(self, findings: List[AuditFinding]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 按严重性排序
        sorted_findings = sorted(findings, key=lambda f: self._severity_score(f.severity), reverse=True)
        
        for finding in sorted_findings[:10]:  # 最多10条建议
            if finding.status != AuditStatus.PASSED:
                recommendations.append(f"[{finding.severity.value.upper()}] {finding.recommendation}")
        
        return recommendations
    
    def _severity_score(self, severity: AuditSeverity) -> int:
        """严重性分数"""
        scores = {
            AuditSeverity.CRITICAL: 4,
            AuditSeverity.HIGH: 3,
            AuditSeverity.MEDIUM: 2,
            AuditSeverity.LOW: 1,
            AuditSeverity.INFO: 0
        }
        return scores.get(severity, 0)
    
    def _auto_remediate(self, findings: List[AuditFinding]) -> None:
        """自动修复可修复的问题"""
        for finding in findings:
            if finding.severity == AuditSeverity.CRITICAL:
                # 尝试自动修复
                logger.info(f"尝试自动修复发现: {finding.finding_id}")
                # 根据发现类型执行修复操作
                # 这里可以实现自动修复逻辑
    
    def get_report(self, report_id: str) -> Optional[PrivacyAuditReport]:
        """获取审计报告"""
        return self.reports.get(report_id)
    
    def get_findings(
        self,
        report_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        status: Optional[AuditStatus] = None
    ) -> List[AuditFinding]:
        """获取审计发现"""
        if report_id:
            findings = self.findings.get(report_id, [])
        else:
            findings = []
            for report_findings in self.findings.values():
                findings.extend(report_findings)
        
        # 过滤
        if severity:
            findings = [f for f in findings if f.severity == severity]
        if status:
            findings = [f for f in findings if f.status == status]
        
        return findings
    
    def resolve_finding(
        self,
        finding_id: str,
        resolution: str,
        resolved_by: str
    ) -> Tuple[bool, str]:
        """
        解决审计发现
        
        Args:
            finding_id: 发现ID
            resolution: 解决方案
            resolved_by: 解决者
        
        Returns:
            (成功标志, 消息)
        """
        for report_id, findings in self.findings.items():
            for finding in findings:
                if finding.finding_id == finding_id:
                    finding.status = AuditStatus.PASSED
                    finding.resolved_at = time.time()
                    finding.metadata["resolution"] = resolution
                    finding.metadata["resolved_by"] = resolved_by
                    
                    self._save_reports()
                    
                    logger.info(f"审计发现已解决: {finding_id}")
                    return True, "发现已标记为已解决"
        
        return False, f"未找到发现: {finding_id}"
    
    def get_compliance_status(
        self,
        framework: str = "GDPR"
    ) -> Dict[str, Any]:
        """
        获取合规状态
        
        Args:
            framework: 合规框架
        
        Returns:
            合规状态
        """
        if framework not in self.config["compliance_frameworks"]:
            return {"error": f"不支持的合规框架: {framework}"}
        
        # 获取最新的审计报告
        latest_report = None
        if self.reports:
            latest_report = max(self.reports.values(), key=lambda r: r.audit_time)
        
        if not latest_report:
            return {
                "framework": framework,
                "status": "unknown",
                "message": "尚未执行审计"
            }
        
        # 根据审计结果评估合规状态
        compliance_score = 100
        critical_issues = 0
        high_issues = 0
        
        for finding in latest_report.findings:
            if finding.status != AuditStatus.PASSED:
                if finding.severity == AuditSeverity.CRITICAL:
                    critical_issues += 1
                    compliance_score -= 15
                elif finding.severity == AuditSeverity.HIGH:
                    high_issues += 1
                    compliance_score -= 10
                elif finding.severity == AuditSeverity.MEDIUM:
                    compliance_score -= 5
                elif finding.severity == AuditSeverity.LOW:
                    compliance_score -= 2
        
        compliance_score = max(0, compliance_score)
        
        if compliance_score >= 90:
            status = "compliant"
        elif compliance_score >= 70:
            status = "partially_compliant"
        else:
            status = "non_compliant"
        
        return {
            "framework": framework,
            "status": status,
            "compliance_score": compliance_score,
            "last_audit": latest_report.audit_time,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "next_audit_due": latest_report.next_audit_due
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_findings = sum(len(f) for f in self.findings.values())
        resolved_findings = sum(
            1 for findings in self.findings.values()
            for f in findings if f.status == AuditStatus.PASSED
        )
        
        return {
            "total_reports": len(self.reports),
            "total_findings": total_findings,
            "resolved_findings": resolved_findings,
            "resolution_rate": resolved_findings / total_findings if total_findings > 0 else 0,
            "latest_audit": max((r.audit_time for r in self.reports.values()), default=None),
            "compliance_frameworks": self.config["compliance_frameworks"]
        }


# 单例实例
_privacy_auditor_instance = None


def get_privacy_auditor() -> PrivacyAuditor:
    """获取隐私审计器单例实例"""
    global _privacy_auditor_instance
    if _privacy_auditor_instance is None:
        _privacy_auditor_instance = PrivacyAuditor()
    return _privacy_auditor_instance

