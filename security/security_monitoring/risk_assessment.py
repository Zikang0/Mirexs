"""
风险评估模块 - 安全风险评估
评估系统安全风险，提供风险等级和建议
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.permission_manager import PermissionManager, get_permission_manager
from .vulnerability_scanner import VulnerabilityScanner, get_vulnerability_scanner
from .threat_detection import ThreatDetection, get_threat_detection
from .incident_response import IncidentResponse, get_incident_response

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险级别枚举"""
    CRITICAL = "critical"  # 严重风险
    HIGH = "high"  # 高风险
    MEDIUM = "medium"  # 中风险
    LOW = "low"  # 低风险
    NEGLIGIBLE = "negligible"  # 可忽略


class RiskCategory(Enum):
    """风险类别枚举"""
    TECHNICAL = "technical"  # 技术风险
    OPERATIONAL = "operational"  # 运营风险
    COMPLIANCE = "compliance"  # 合规风险
    REPUTATIONAL = "reputational"  # 声誉风险
    FINANCIAL = "financial"  # 财务风险
    STRATEGIC = "strategic"  # 战略风险


class RiskStatus(Enum):
    """风险状态枚举"""
    IDENTIFIED = "identified"  # 已识别
    ASSESSED = "assessed"  # 已评估
    TREATING = "treating"  # 处理中
    ACCEPTED = "accepted"  # 已接受
    TRANSFERRED = "transferred"  # 已转移
    MITIGATED = "mitigated"  # 已缓解
    CLOSED = "closed"  # 已关闭


@dataclass
class Risk:
    """风险项"""
    risk_id: str
    name: str
    description: str
    category: RiskCategory
    level: RiskLevel
    status: RiskStatus
    probability: float  # 0-1
    impact: float  # 0-1
    risk_score: float  # probability * impact
    identified_at: float
    identified_by: str
    affected_assets: List[str]
    threats: List[str]
    vulnerabilities: List[str]
    controls: List[str]
    treatment: Optional[str] = None
    residual_risk: Optional[float] = None
    due_date: Optional[float] = None
    owner: Optional[str] = None
    updated_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """风险评估"""
    assessment_id: str
    assessed_at: float
    assessed_by: str
    scope: str
    risks: List[Risk]
    summary: Dict[str, Any]
    recommendations: List[str]
    next_assessment_due: Optional[float] = None


class RiskAssessment:
    """
    风险评估器 - 评估系统安全风险
    综合分析漏洞、威胁、控制措施，评估整体风险水平
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化风险评估器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 风险存储
        self.risks: Dict[str, Risk] = {}
        
        # 风险评估记录
        self.assessments: Dict[str, RiskAssessment] = {}
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/risk"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.permission_manager = get_permission_manager()
        self.vulnerability_scanner = get_vulnerability_scanner()
        self.threat_detection = get_threat_detection()
        self.incident_response = get_incident_response()
        
        # 加载数据
        self._load_risks()
        self._load_assessments()
        
        # 风险矩阵
        self.risk_matrix = self._init_risk_matrix()
        
        logger.info(f"风险评估器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/risk",
            "assessment_interval_days": 30,  # 评估间隔
            "risk_acceptance_threshold": 0.3,  # 可接受风险阈值
            "risk_tolerance": {
                "critical": 0,
                "high": 1,
                "medium": 5,
                "low": 10
            },
            "impact_levels": {
                "critical": 1.0,
                "high": 0.7,
                "medium": 0.4,
                "low": 0.1
            },
            "probability_levels": {
                "very_likely": 0.9,
                "likely": 0.7,
                "possible": 0.5,
                "unlikely": 0.3,
                "rare": 0.1
            },
            "asset_values": {
                "critical": 1.0,
                "high": 0.8,
                "medium": 0.5,
                "low": 0.2
            }
        }
    
    def _init_risk_matrix(self) -> Dict[str, Any]:
        """初始化风险矩阵"""
        return {
            "levels": ["critical", "high", "medium", "low", "negligible"],
            "thresholds": {
                "critical": 0.7,
                "high": 0.5,
                "medium": 0.3,
                "low": 0.1
            },
            "matrix": {
                (0.9, 0.9): "critical",
                (0.9, 0.7): "critical",
                (0.9, 0.4): "high",
                (0.9, 0.1): "medium",
                (0.7, 0.9): "critical",
                (0.7, 0.7): "high",
                (0.7, 0.4): "high",
                (0.7, 0.1): "medium",
                (0.5, 0.9): "high",
                (0.5, 0.7): "high",
                (0.5, 0.4): "medium",
                (0.5, 0.1): "low",
                (0.3, 0.9): "medium",
                (0.3, 0.7): "medium",
                (0.3, 0.4): "low",
                (0.3, 0.1): "low",
                (0.1, 0.9): "medium",
                (0.1, 0.7): "low",
                (0.1, 0.4): "low",
                (0.1, 0.1): "negligible"
            }
        }
    
    def _load_risks(self):
        """从存储加载风险"""
        try:
            risks_file = self.storage_path / "risks.json"
            if risks_file.exists():
                with open(risks_file, 'r', encoding='utf-8') as f:
                    risks_data = json.load(f)
                    for risk_id, risk_dict in risks_data.items():
                        risk_dict["category"] = RiskCategory(risk_dict["category"])
                        risk_dict["level"] = RiskLevel(risk_dict["level"])
                        risk_dict["status"] = RiskStatus(risk_dict["status"])
                        self.risks[risk_id] = Risk(**risk_dict)
            
            logger.info(f"加载了 {len(self.risks)} 个风险项")
        except Exception as e:
            logger.error(f"加载风险失败: {str(e)}")
    
    def _load_assessments(self):
        """从存储加载风险评估"""
        try:
            assessments_file = self.storage_path / "assessments.json"
            if assessments_file.exists():
                with open(assessments_file, 'r', encoding='utf-8') as f:
                    assessments_data = json.load(f)
                    for assessment_id, assessment_dict in assessments_data.items():
                        # 反序列化风险列表
                        risks = []
                        for r in assessment_dict["risks"]:
                            if isinstance(r, dict):
                                r["category"] = RiskCategory(r["category"])
                                r["level"] = RiskLevel(r["level"])
                                r["status"] = RiskStatus(r["status"])
                                risks.append(Risk(**r))
                        assessment_dict["risks"] = risks
                        self.assessments[assessment_id] = RiskAssessment(**assessment_dict)
            
            logger.info(f"加载了 {len(self.assessments)} 次风险评估")
        except Exception as e:
            logger.error(f"加载风险评估失败: {str(e)}")
    
    def _save_risks(self):
        """保存风险到存储"""
        try:
            risks_data = {}
            for risk_id, risk in self.risks.items():
                risk_dict = {
                    "risk_id": risk.risk_id,
                    "name": risk.name,
                    "description": risk.description,
                    "category": risk.category.value,
                    "level": risk.level.value,
                    "status": risk.status.value,
                    "probability": risk.probability,
                    "impact": risk.impact,
                    "risk_score": risk.risk_score,
                    "identified_at": risk.identified_at,
                    "identified_by": risk.identified_by,
                    "affected_assets": risk.affected_assets,
                    "threats": risk.threats,
                    "vulnerabilities": risk.vulnerabilities,
                    "controls": risk.controls,
                    "treatment": risk.treatment,
                    "residual_risk": risk.residual_risk,
                    "due_date": risk.due_date,
                    "owner": risk.owner,
                    "updated_at": risk.updated_at,
                    "closed_at": risk.closed_at,
                    "metadata": risk.metadata
                }
                risks_data[risk_id] = risk_dict
            
            with open(self.storage_path / "risks.json", 'w', encoding='utf-8') as f:
                json.dump(risks_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存风险失败: {str(e)}")
    
    def _save_assessments(self):
        """保存风险评估到存储"""
        try:
            assessments_data = {}
            for assessment_id, assessment in self.assessments.items():
                assessment_dict = {
                    "assessment_id": assessment.assessment_id,
                    "assessed_at": assessment.assessed_at,
                    "assessed_by": assessment.assessed_by,
                    "scope": assessment.scope,
                    "risks": [r.__dict__ for r in assessment.risks],
                    "summary": assessment.summary,
                    "recommendations": assessment.recommendations,
                    "next_assessment_due": assessment.next_assessment_due
                }
                assessments_data[assessment_id] = assessment_dict
            
            with open(self.storage_path / "assessments.json", 'w', encoding='utf-8') as f:
                json.dump(assessments_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存风险评估失败: {str(e)}")
    
    async def assess_risks(
        self,
        assessed_by: str,
        scope: str = "full"
    ) -> RiskAssessment:
        """
        执行风险评估
        
        Args:
            assessed_by: 评估者
            scope: 评估范围
        
        Returns:
            风险评估结果
        """
        assessment_id = f"ra_{int(time.time())}_{assessed_by[:8]}"
        
        logger.info(f"开始风险评估: {assessment_id}")
        
        risks = []
        
        # 从漏洞扫描获取风险
        vuln_stats = self.vulnerability_scanner.get_statistics()
        for severity, count in vuln_stats.get("by_severity", {}).items():
            if count > 0:
                risk = self._create_risk_from_vulnerability(severity, count)
                if risk:
                    risks.append(risk)
        
        # 从威胁检测获取风险
        threat_stats = self.threat_detection.get_threat_statistics()
        for level, count in threat_stats.get("by_level", {}).items():
            if count > 0 and level in ["critical", "high"]:
                risk = self._create_risk_from_threat(level, count)
                if risk:
                    risks.append(risk)
        
        # 从事件响应获取风险
        incident_stats = self.incident_response.get_statistics()
        if incident_stats.get("pending_count", 0) > 0:
            risk = self._create_risk_from_incidents(incident_stats)
            if risk:
                risks.append(risk)
        
        # 检查权限配置风险
        perm_risks = await self._assess_permission_risks()
        risks.extend(perm_risks)
        
        # 计算风险分数
        for risk in risks:
            risk.risk_score = risk.probability * risk.impact
            risk.level = self._determine_risk_level(risk.risk_score)
        
        # 生成摘要
        summary = self._generate_assessment_summary(risks)
        
        # 生成建议
        recommendations = self._generate_recommendations(risks)
        
        # 计算下次评估时间
        next_assessment_due = time.time() + (self.config["assessment_interval_days"] * 24 * 3600)
        
        assessment = RiskAssessment(
            assessment_id=assessment_id,
            assessed_at=time.time(),
            assessed_by=assessed_by,
            scope=scope,
            risks=risks,
            summary=summary,
            recommendations=recommendations,
            next_assessment_due=next_assessment_due
        )
        
        self.assessments[assessment_id] = assessment
        
        # 更新风险库
        for risk in risks:
            self.risks[risk.risk_id] = risk
        
        self._save_risks()
        self._save_assessments()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=assessed_by,
            event_type="RISK_ASSESSMENT",
            severity="info",
            details={
                "assessment_id": assessment_id,
                "total_risks": len(risks),
                "critical_count": summary.get("critical", 0),
                "high_count": summary.get("high", 0),
                "risk_score": summary.get("total_risk_score", 0)
            }
        )
        
        logger.info(f"风险评估完成: {assessment_id}, 发现 {len(risks)} 个风险")
        
        return assessment
    
    def _create_risk_from_vulnerability(self, severity: str, count: int) -> Optional[Risk]:
        """从漏洞创建风险"""
        risk_id = f"risk_vuln_{int(time.time())}_{severity}"
        
        # 确定概率和影响
        if severity == "critical":
            probability = 0.8
            impact = 0.9
        elif severity == "high":
            probability = 0.6
            impact = 0.7
        elif severity == "medium":
            probability = 0.4
            impact = 0.4
        else:
            probability = 0.2
            impact = 0.2
        
        return Risk(
            risk_id=risk_id,
            name=f"{severity.capitalize()}级别漏洞风险",
            description=f"存在 {count} 个{severity}级别漏洞",
            category=RiskCategory.TECHNICAL,
            level=RiskLevel(severity),
            status=RiskStatus.IDENTIFIED,
            probability=probability,
            impact=impact,
            risk_score=probability * impact,
            identified_at=time.time(),
            identified_by="system",
            affected_assets=["system"],
            threats=["漏洞利用"],
            vulnerabilities=[severity],
            controls=["漏洞扫描", "补丁管理"],
            treatment="需要修复漏洞"
        )
    
    def _create_risk_from_threat(self, level: str, count: int) -> Optional[Risk]:
        """从威胁创建风险"""
        risk_id = f"risk_threat_{int(time.time())}_{level}"
        
        return Risk(
            risk_id=risk_id,
            name=f"{level.capitalize()}级别威胁风险",
            description=f"最近检测到 {count} 个{level}级别威胁",
            category=RiskCategory.TECHNICAL,
            level=RiskLevel(level),
            status=RiskStatus.IDENTIFIED,
            probability=0.7 if level == "critical" else 0.5,
            impact=0.8 if level == "critical" else 0.6,
            risk_score=0.56 if level == "critical" else 0.3,
            identified_at=time.time(),
            identified_by="system",
            affected_assets=["system"],
            threats=["威胁活动"],
            vulnerabilities=["威胁检测"],
            controls=["入侵检测", "威胁情报"],
            treatment="加强威胁监控和防护"
        )
    
    def _create_risk_from_incidents(self, incident_stats: Dict[str, Any]) -> Optional[Risk]:
        """从事件创建风险"""
        risk_id = f"risk_incident_{int(time.time())}"
        
        pending = incident_stats.get("pending_count", 0)
        
        return Risk(
            risk_id=risk_id,
            name="未处理安全事件风险",
            description=f"有 {pending} 个待处理安全事件",
            category=RiskCategory.OPERATIONAL,
            level=RiskLevel.HIGH if pending > 5 else RiskLevel.MEDIUM,
            status=RiskStatus.IDENTIFIED,
            probability=0.6,
            impact=0.7,
            risk_score=0.42,
            identified_at=time.time(),
            identified_by="system",
            affected_assets=["operations"],
            threats=["事件响应延迟"],
            vulnerabilities=["事件处理能力"],
            controls=["事件响应流程"],
            treatment="加快事件处理速度"
        )
    
    async def _assess_permission_risks(self) -> List[Risk]:
        """评估权限风险"""
        risks = []
        
        # 检查过度授权的角色
        roles = self.permission_manager.get_all_roles()
        for role in roles:
            if role.get("permissions_count", 0) > 50:
                risk = Risk(
                    risk_id=f"risk_perm_{int(time.time())}_{role['role_id']}",
                    name="过度授权风险",
                    description=f"角色 '{role['name']}' 拥有过多权限 ({role['permissions_count']}个)",
                    category=RiskCategory.TECHNICAL,
                    level=RiskLevel.MEDIUM,
                    status=RiskStatus.IDENTIFIED,
                    probability=0.4,
                    impact=0.5,
                    risk_score=0.2,
                    identified_at=time.time(),
                    identified_by="system",
                    affected_assets=["access_control"],
                    threats=["权限滥用"],
                    vulnerabilities=["过度授权"],
                    controls=["权限审计"],
                    treatment="审查并精简角色权限"
                )
                risks.append(risk)
        
        return risks
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """确定风险级别"""
        if risk_score >= 0.7:
            return RiskLevel.CRITICAL
        elif risk_score >= 0.5:
            return RiskLevel.HIGH
        elif risk_score >= 0.3:
            return RiskLevel.MEDIUM
        elif risk_score >= 0.1:
            return RiskLevel.LOW
        else:
            return RiskLevel.NEGLIGIBLE
    
    def _generate_assessment_summary(self, risks: List[Risk]) -> Dict[str, Any]:
        """生成评估摘要"""
        summary = {
            "total_risks": len(risks),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "negligible": 0,
            "by_category": {},
            "total_risk_score": 0,
            "average_risk_score": 0
        }
        
        for risk in risks:
            level = risk.level.value
            summary[level] = summary.get(level, 0) + 1
            
            category = risk.category.value
            if category not in summary["by_category"]:
                summary["by_category"][category] = 0
            summary["by_category"][category] += 1
            
            summary["total_risk_score"] += risk.risk_score
        
        if risks:
            summary["average_risk_score"] = summary["total_risk_score"] / len(risks)
        
        return summary
    
    def _generate_recommendations(self, risks: List[Risk]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 按风险级别排序
        sorted_risks = sorted(risks, key=lambda r: r.risk_score, reverse=True)
        
        for risk in sorted_risks[:10]:  # 最多10条建议
            if risk.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
                recommendations.append(
                    f"[{risk.level.value.upper()}] {risk.name}: {risk.treatment or '需要立即处理'}"
                )
        
        return recommendations
    
    def add_risk(self, risk: Risk) -> Tuple[bool, str]:
        """添加风险项"""
        if risk.risk_id in self.risks:
            return False, f"风险ID已存在: {risk.risk_id}"
        
        self.risks[risk.risk_id] = risk
        self._save_risks()
        
        logger.info(f"添加风险: {risk.risk_id}")
        return True, "风险添加成功"
    
    def update_risk(
        self,
        risk_id: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        更新风险
        
        Args:
            risk_id: 风险ID
            **kwargs: 更新字段
        
        Returns:
            (成功标志, 消息)
        """
        if risk_id not in self.risks:
            return False, f"风险不存在: {risk_id}"
        
        risk = self.risks[risk_id]
        
        for key, value in kwargs.items():
            if hasattr(risk, key):
                setattr(risk, key, value)
        
        risk.updated_at = time.time()
        
        self._save_risks()
        
        logger.info(f"更新风险: {risk_id}")
        return True, "风险更新成功"
    
    def accept_risk(
        self,
        risk_id: str,
        accepted_by: str,
        justification: str
    ) -> Tuple[bool, str]:
        """
        接受风险
        
        Args:
            risk_id: 风险ID
            accepted_by: 接受者
            justification: 理由
        
        Returns:
            (成功标志, 消息)
        """
        if risk_id not in self.risks:
            return False, f"风险不存在: {risk_id}"
        
        risk = self.risks[risk_id]
        risk.status = RiskStatus.ACCEPTED
        risk.metadata["accepted_by"] = accepted_by
        risk.metadata["acceptance_justification"] = justification
        risk.metadata["accepted_at"] = time.time()
        risk.updated_at = time.time()
        
        self._save_risks()
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=accepted_by,
            event_type="RISK_ACCEPTED",
            severity="warning",
            details={
                "risk_id": risk_id,
                "risk_name": risk.name,
                "justification": justification
            }
        )
        
        logger.info(f"风险已接受: {risk_id}")
        return True, "风险已接受"
    
    def mitigate_risk(
        self,
        risk_id: str,
        mitigation: str,
        mitigated_by: str
    ) -> Tuple[bool, str]:
        """
        缓解风险
        
        Args:
            risk_id: 风险ID
            mitigation: 缓解措施
            mitigated_by: 缓解者
        
        Returns:
            (成功标志, 消息)
        """
        if risk_id not in self.risks:
            return False, f"风险不存在: {risk_id}"
        
        risk = self.risks[risk_id]
        risk.status = RiskStatus.MITIGATED
        risk.treatment = mitigation
        risk.metadata["mitigated_by"] = mitigated_by
        risk.metadata["mitigated_at"] = time.time()
        risk.updated_at = time.time()
        
        # 计算残余风险
        risk.residual_risk = risk.risk_score * 0.3  # 假设缓解后残余30%
        
        self._save_risks()
        
        logger.info(f"风险已缓解: {risk_id}")
        return True, "风险已缓解"
    
    def get_risks(
        self,
        level: Optional[RiskLevel] = None,
        category: Optional[RiskCategory] = None,
        status: Optional[RiskStatus] = None,
        owner: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取风险列表
        
        Args:
            level: 风险级别
            category: 风险类别
            status: 风险状态
            owner: 负责人
            limit: 返回数量限制
        
        Returns:
            风险列表
        """
        risks = list(self.risks.values())
        
        if level:
            risks = [r for r in risks if r.level == level]
        if category:
            risks = [r for r in risks if r.category == category]
        if status:
            risks = [r for r in risks if r.status == status]
        if owner:
            risks = [r for r in risks if r.owner == owner]
        
        # 按风险分数排序
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        
        return [
            {
                "risk_id": r.risk_id,
                "name": r.name,
                "level": r.level.value,
                "category": r.category.value,
                "status": r.status.value,
                "risk_score": r.risk_score,
                "probability": r.probability,
                "impact": r.impact,
                "identified_at": r.identified_at,
                "owner": r.owner,
                "due_date": r.due_date
            }
            for r in risks[:limit]
        ]
    
    def get_risk(self, risk_id: str) -> Optional[Risk]:
        """获取风险详情"""
        return self.risks.get(risk_id)
    
    def get_assessment(self, assessment_id: str) -> Optional[RiskAssessment]:
        """获取风险评估"""
        return self.assessments.get(assessment_id)
    
    def get_latest_assessment(self) -> Optional[RiskAssessment]:
        """获取最新风险评估"""
        if not self.assessments:
            return None
        
        return max(self.assessments.values(), key=lambda a: a.assessed_at)
    
    def get_risk_heatmap(self) -> Dict[str, Any]:
        """获取风险热力图"""
        heatmap = {
            "matrix": [],
            "legend": []
        }
        
        probability_levels = [0.9, 0.7, 0.5, 0.3, 0.1]
        impact_levels = [0.9, 0.7, 0.5, 0.3, 0.1]
        
        for p in probability_levels:
            row = []
            for i in impact_levels:
                count = sum(1 for r in self.risks.values() 
                           if abs(r.probability - p) < 0.15 and abs(r.impact - i) < 0.15)
                row.append(count)
            heatmap["matrix"].append(row)
        
        return heatmap
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_risks": len(self.risks),
            "by_level": {},
            "by_category": {},
            "by_status": {},
            "average_risk_score": 0,
            "total_risk_exposure": 0,
            "open_risks": 0,
            "accepted_risks": 0,
            "mitigated_risks": 0,
            "overdue_risks": 0
        }
        
        now = time.time()
        total_score = 0
        
        for risk in self.risks.values():
            level = risk.level.value
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            
            category = risk.category.value
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            status = risk.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            total_score += risk.risk_score
            
            if risk.status in [RiskStatus.IDENTIFIED, RiskStatus.ASSESSED, RiskStatus.TREATING]:
                stats["open_risks"] += 1
            elif risk.status == RiskStatus.ACCEPTED:
                stats["accepted_risks"] += 1
            elif risk.status == RiskStatus.MITIGATED:
                stats["mitigated_risks"] += 1
            
            if risk.due_date and risk.due_date < now and risk.status not in [RiskStatus.CLOSED, RiskStatus.MITIGATED]:
                stats["overdue_risks"] += 1
        
        if stats["total_risks"] > 0:
            stats["average_risk_score"] = total_score / stats["total_risks"]
            stats["total_risk_exposure"] = total_score
        
        return stats


# 单例实例
_risk_assessment_instance = None


def get_risk_assessment() -> RiskAssessment:
    """获取风险评估器单例实例"""
    global _risk_assessment_instance
    if _risk_assessment_instance is None:
        _risk_assessment_instance = RiskAssessment()
    return _risk_assessment_instance

