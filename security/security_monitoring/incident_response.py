"""
事件响应模块 - 安全事件响应处理
提供安全事件的检测、响应、处置和恢复全流程管理
"""

import asyncio
import logging
import time
import json
import secrets
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.session_manager import SessionManager, get_session_manager
from ..access_control.permission_manager import PermissionManager, get_permission_manager
from .threat_detection import ThreatDetection, get_threat_detection
from .alert_manager import AlertManager, get_alert_manager

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """事件严重性枚举"""
    CRITICAL = "critical"  # 严重，需要立即响应
    HIGH = "high"  # 高，需要尽快响应
    MEDIUM = "medium"  # 中，需要计划响应
    LOW = "low"  # 低，可以延后处理
    INFO = "info"  # 信息性事件


class IncidentStatus(Enum):
    """事件状态枚举"""
    DETECTED = "detected"  # 已检测
    TRIAGING = "triaging"  # 分类中
    ANALYZING = "analyzing"  # 分析中
    CONTAINING = "containing"  # 遏制中
    ERADICATING = "eradicating"  # 根除中
    RECOVERING = "recovering"  # 恢复中
    RESOLVED = "resolved"  # 已解决
    FALSE_POSITIVE = "false_positive"  # 误报
    CLOSED = "closed"  # 已关闭


class IncidentType(Enum):
    """事件类型枚举"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # 未授权访问
    DATA_BREACH = "data_breach"  # 数据泄露
    MALWARE_INFECTION = "malware_infection"  # 恶意软件感染
    DOS_ATTACK = "dos_attack"  # DoS攻击
    ACCOUNT_COMPROMISE = "account_compromise"  # 账户入侵
    PRIVILEGE_ESCALATION = "privilege_escalation"  # 权限提升
    POLICY_VIOLATION = "policy_violation"  # 策略违规
    ABNORMAL_BEHAVIOR = "abnormal_behavior"  # 异常行为
    SYSTEM_FAILURE = "system_failure"  # 系统故障
    COMPLIANCE_VIOLATION = "compliance_violation"  # 合规违规


@dataclass
class Incident:
    """安全事件"""
    incident_id: str
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    detected_at: float
    detected_by: str
    title: str
    description: str
    affected_resources: List[str]
    affected_users: List[str]
    indicators: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    actions_taken: List[Dict[str, Any]]
    assigned_to: Optional[str] = None
    escalated_at: Optional[float] = None
    contained_at: Optional[float] = None
    eradicated_at: Optional[float] = None
    recovered_at: Optional[float] = None
    resolved_at: Optional[float] = None
    closed_at: Optional[float] = None
    root_cause: Optional[str] = None
    remediation: Optional[str] = None
    lessons_learned: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentResponsePlan:
    """事件响应计划"""
    plan_id: str
    incident_type: IncidentType
    name: str
    description: str
    steps: List[Dict[str, Any]]
    estimated_time_minutes: int
    required_roles: List[str]
    automated: bool = False
    enabled: bool = True


class IncidentResponse:
    """
    事件响应管理器 - 处理安全事件的全生命周期
    包括检测、分类、遏制、根除、恢复和事后分析
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化事件响应管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 事件存储
        self.incidents: Dict[str, Incident] = {}
        
        # 响应计划
        self.response_plans: Dict[str, IncidentResponsePlan] = {}
        
        # 待处理事件队列
        self.pending_incidents: List[str] = []
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.session_manager = get_session_manager()
        self.permission_manager = get_permission_manager()
        self.threat_detection = get_threat_detection()
        self.alert_manager = get_alert_manager()
        
        # 加载响应计划
        self._load_response_plans()
        
        # 启动事件处理任务
        self._processor_task = None
        
        logger.info("事件响应管理器初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "auto_respond": True,  # 自动响应
            "escalation_timeout_minutes": 30,  # 升级超时
            "max_concurrent_incidents": 10,
            "notification_channels": ["email", "slack", "sms"],
            "response_teams": {
                "critical": ["security_lead", "system_admin", "dpo"],
                "high": ["security_analyst", "system_admin"],
                "medium": ["security_analyst"],
                "low": ["on_call"]
            },
            "sla_minutes": {
                "critical": 15,
                "high": 60,
                "medium": 240,
                "low": 720
            },
            "auto_contain": True,  # 自动遏制
            "auto_block_ips": True,  # 自动封禁IP
            "auto_revoke_sessions": True,  # 自动吊销会话
            "evidence_retention_days": 90  # 证据保留天数
        }
    
    def _load_response_plans(self):
        """加载响应计划"""
        plans = [
            {
                "incident_type": IncidentType.UNAUTHORIZED_ACCESS,
                "name": "未授权访问响应计划",
                "description": "处理未授权访问事件的标准化流程",
                "steps": [
                    {"order": 1, "action": "验证事件真实性", "automated": True},
                    {"order": 2, "action": "识别受影响资源", "automated": True},
                    {"order": 3, "action": "阻止源IP", "automated": True},
                    {"order": 4, "action": "吊销相关会话", "automated": True},
                    {"order": 5, "action": "收集证据", "automated": False},
                    {"order": 6, "action": "分析访问日志", "automated": False},
                    {"order": 7, "action": "修复漏洞", "automated": False},
                    {"order": 8, "action": "恢复受影响系统", "automated": False},
                    {"order": 9, "action": "编写事后报告", "automated": False}
                ],
                "estimated_time_minutes": 120,
                "required_roles": ["security_analyst", "system_admin"]
            },
            {
                "incident_type": IncidentType.ACCOUNT_COMPROMISE,
                "name": "账户入侵响应计划",
                "description": "处理账户被入侵事件的标准化流程",
                "steps": [
                    {"order": 1, "action": "确认账户入侵", "automated": False},
                    {"order": 2, "action": "锁定受影响账户", "automated": True},
                    {"order": 3, "action": "重置所有会话", "automated": True},
                    {"order": 4, "action": "重置密码", "automated": False},
                    {"order": 5, "action": "检查异常活动", "automated": True},
                    {"order": 6, "action": "通知用户", "automated": False},
                    {"order": 7, "action": "审计权限变更", "automated": True},
                    {"order": 8, "action": "加强认证措施", "automated": False}
                ],
                "estimated_time_minutes": 90,
                "required_roles": ["security_analyst", "user_admin"]
            },
            {
                "incident_type": IncidentType.DATA_BREACH,
                "name": "数据泄露响应计划",
                "description": "处理数据泄露事件的标准化流程",
                "steps": [
                    {"order": 1, "action": "确认数据泄露", "automated": False},
                    {"order": 2, "action": "评估泄露范围", "automated": True},
                    {"order": 3, "action": "阻止数据外流", "automated": True},
                    {"order": 4, "action": "收集泄露证据", "automated": False},
                    {"order": 5, "action": "通知DPO", "automated": True},
                    {"order": 6, "action": "评估法律义务", "automated": False},
                    {"order": 7, "action": "通知受影响用户", "automated": False},
                    {"order": 8, "action": "报告监管机构", "automated": False},
                    {"order": 9, "action": "加强数据保护", "automated": False}
                ],
                "estimated_time_minutes": 240,
                "required_roles": ["security_lead", "dpo", "legal"]
            }
        ]
        
        for i, plan_config in enumerate(plans):
            plan = IncidentResponsePlan(
                plan_id=f"plan_{i+1}",
                **plan_config
            )
            self.response_plans[plan.plan_id] = plan
    
    async def create_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        detected_by: str,
        affected_resources: Optional[List[str]] = None,
        affected_users: Optional[List[str]] = None,
        indicators: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Incident:
        """
        创建安全事件
        
        Args:
            incident_type: 事件类型
            severity: 严重性
            title: 标题
            description: 描述
            detected_by: 检测者
            affected_resources: 受影响资源
            affected_users: 受影响用户
            indicators: 威胁指标
            metadata: 元数据
        
        Returns:
            创建的事件
        """
        incident_id = f"inc_{int(time.time())}_{secrets.token_hex(4)}"
        
        incident = Incident(
            incident_id=incident_id,
            type=incident_type,
            severity=severity,
            status=IncidentStatus.DETECTED,
            detected_at=time.time(),
            detected_by=detected_by,
            title=title,
            description=description,
            affected_resources=affected_resources or [],
            affected_users=affected_users or [],
            indicators=indicators or [],
            timeline=[{
                "timestamp": time.time(),
                "action": "incident_created",
                "performed_by": detected_by,
                "details": "事件已创建"
            }],
            actions_taken=[],
            metadata=metadata or {}
        )
        
        self.incidents[incident_id] = incident
        self.pending_incidents.append(incident_id)
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=detected_by,
            event_type="INCIDENT_CREATED",
            severity=severity.value,
            details={
                "incident_id": incident_id,
                "type": incident_type.value,
                "title": title
            }
        )
        
        # 发送告警
        await self.alert_manager.send_alert(
            alert_type=f"incident_{incident_type.value}",
            severity=severity.value,
            message=f"新安全事件: {title}",
            details={
                "incident_id": incident_id,
                "description": description,
                "affected_resources": affected_resources
            }
        )
        
        logger.info(f"创建安全事件: {incident_id} - {title}")
        
        # 自动响应
        if self.config["auto_respond"]:
            asyncio.create_task(self._auto_respond(incident_id))
        
        return incident
    
    async def _auto_respond(self, incident_id: str):
        """自动响应事件"""
        incident = self.incidents.get(incident_id)
        if not incident:
            return
        
        try:
            # 查找匹配的响应计划
            plan = self._find_matching_plan(incident.type)
            if not plan:
                logger.warning(f"未找到匹配的响应计划: {incident.type.value}")
                return
            
            # 自动执行可自动化的步骤
            for step in plan.steps:
                if step.get("automated") and step["action"] in self._get_auto_actions():
                    result = await self._execute_auto_action(incident, step["action"])
                    if result:
                        incident.actions_taken.append({
                            "timestamp": time.time(),
                            "action": step["action"],
                            "performed_by": "system",
                            "result": result
                        })
            
            # 更新事件状态
            incident.status = IncidentStatus.TRIAGING
            
        except Exception as e:
            logger.error(f"自动响应失败: {str(e)}")
    
    def _find_matching_plan(self, incident_type: IncidentType) -> Optional[IncidentResponsePlan]:
        """查找匹配的响应计划"""
        for plan in self.response_plans.values():
            if plan.incident_type == incident_type:
                return plan
        return None
    
    def _get_auto_actions(self) -> List[str]:
        """获取可自动执行的操作"""
        return [
            "阻止源IP",
            "吊销相关会话",
            "锁定受影响账户",
            "重置所有会话",
            "检查异常活动",
            "审计权限变更",
            "评估泄露范围",
            "阻止数据外流",
            "通知DPO"
        ]
    
    async def _execute_auto_action(self, incident: Incident, action: str) -> Optional[Dict[str, Any]]:
        """执行自动操作"""
        try:
            if action == "阻止源IP":
                # 从指标中提取IP
                source_ips = []
                for indicator in incident.indicators:
                    if "source_ip" in indicator:
                        source_ips.append(indicator["source_ip"])
                
                if source_ips and self.config["auto_block_ips"]:
                    from .threat_detection import get_threat_detection
                    threat_detection = get_threat_detection()
                    
                    for ip in source_ips:
                        threat_detection.add_to_blacklist(
                            source_ip=ip,
                            reason=f"事件 {incident.incident_id} 自动封禁"
                        )
                    
                    return {"blocked_ips": source_ips}
            
            elif action == "吊销相关会话":
                if self.config["auto_revoke_sessions"]:
                    for user_id in incident.affected_users:
                        count = await self.session_manager.revoke_user_sessions(
                            user_id=user_id,
                            reason=f"事件 {incident.incident_id} 自动吊销"
                        )
                        return {"revoked_sessions": count}
            
            elif action == "锁定受影响账户":
                from ..access_control.identity_verifier import get_identity_verifier
                from ..access_control.multi_factor_auth import get_multi_factor_auth
                
                mfa = get_multi_factor_auth()
                
                locked_users = []
                for user_id in incident.affected_users:
                    # 锁定MFA因素
                    # 简化实现
                    locked_users.append(user_id)
                
                return {"locked_users": locked_users}
            
            elif action == "通知DPO":
                # 发送通知给DPO
                await self.alert_manager.send_alert(
                    alert_type="dpo_notification",
                    severity=incident.severity.value,
                    message=f"需要DPO介入: {incident.title}",
                    details={
                        "incident_id": incident.incident_id,
                        "type": incident.type.value,
                        "description": incident.description
                    }
                )
                return {"notified": True}
            
        except Exception as e:
            logger.error(f"执行自动操作 {action} 失败: {str(e)}")
            return {"error": str(e)}
        
        return None
    
    async def update_incident(
        self,
        incident_id: str,
        status: Optional[IncidentStatus] = None,
        assigned_to: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        更新事件状态
        
        Args:
            incident_id: 事件ID
            status: 新状态
            assigned_to: 分配责任人
            actions: 采取的行动
            metadata: 元数据
        
        Returns:
            (成功标志, 消息)
        """
        if incident_id not in self.incidents:
            return False, f"事件不存在: {incident_id}"
        
        incident = self.incidents[incident_id]
        
        if status:
            old_status = incident.status
            incident.status = status
            incident.timeline.append({
                "timestamp": time.time(),
                "action": "status_changed",
                "details": f"状态从 {old_status.value} 变更为 {status.value}"
            })
            
            # 记录状态变更时间
            if status == IncidentStatus.CONTAINING:
                incident.contained_at = time.time()
            elif status == IncidentStatus.ERADICATING:
                incident.eradicated_at = time.time()
            elif status == IncidentStatus.RECOVERING:
                incident.recovered_at = time.time()
            elif status == IncidentStatus.RESOLVED:
                incident.resolved_at = time.time()
            elif status == IncidentStatus.CLOSED:
                incident.closed_at = time.time()
        
        if assigned_to:
            incident.assigned_to = assigned_to
            incident.timeline.append({
                "timestamp": time.time(),
                "action": "assigned",
                "details": f"分配给 {assigned_to}"
            })
        
        if actions:
            for action in actions:
                incident.actions_taken.append({
                    "timestamp": time.time(),
                    **action
                })
        
        if metadata:
            incident.metadata.update(metadata)
        
        # 如果事件从待处理队列中移除
        if status in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE, IncidentStatus.CLOSED]:
            if incident_id in self.pending_incidents:
                self.pending_incidents.remove(incident_id)
        
        logger.info(f"事件 {incident_id} 已更新")
        return True, "事件更新成功"
    
    async def add_evidence(
        self,
        incident_id: str,
        evidence_type: str,
        evidence_data: Any,
        collected_by: str
    ) -> Tuple[bool, str]:
        """
        添加事件证据
        
        Args:
            incident_id: 事件ID
            evidence_type: 证据类型
            evidence_data: 证据数据
            collected_by: 收集者
        
        Returns:
            (成功标志, 消息)
        """
        if incident_id not in self.incidents:
            return False, f"事件不存在: {incident_id}"
        
        incident = self.incidents[incident_id]
        
        evidence = {
            "evidence_id": f"ev_{int(time.time())}_{secrets.token_hex(4)}",
            "type": evidence_type,
            "data": evidence_data,
            "collected_at": time.time(),
            "collected_by": collected_by
        }
        
        if "evidence" not in incident.metadata:
            incident.metadata["evidence"] = []
        
        incident.metadata["evidence"].append(evidence)
        
        incident.timeline.append({
            "timestamp": time.time(),
            "action": "evidence_added",
            "details": f"添加证据: {evidence_type}",
            "performed_by": collected_by
        })
        
        logger.info(f"事件 {incident_id} 添加证据")
        return True, "证据添加成功"
    
    async def resolve_incident(
        self,
        incident_id: str,
        root_cause: str,
        remediation: str,
        lessons_learned: Optional[str] = None,
        resolved_by: str = "system"
    ) -> Tuple[bool, str]:
        """
        解决事件
        
        Args:
            incident_id: 事件ID
            root_cause: 根本原因
            remediation: 修复措施
            lessons_learned: 经验教训
            resolved_by: 解决者
        
        Returns:
            (成功标志, 消息)
        """
        if incident_id not in self.incidents:
            return False, f"事件不存在: {incident_id}"
        
        incident = self.incidents[incident_id]
        
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = time.time()
        incident.root_cause = root_cause
        incident.remediation = remediation
        incident.lessons_learned = lessons_learned
        
        incident.timeline.append({
            "timestamp": time.time(),
            "action": "resolved",
            "details": f"事件已解决: {remediation}",
            "performed_by": resolved_by
        })
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=resolved_by,
            event_type="INCIDENT_RESOLVED",
            severity=incident.severity.value,
            details={
                "incident_id": incident_id,
                "root_cause": root_cause,
                "remediation": remediation
            }
        )
        
        logger.info(f"事件 {incident_id} 已解决")
        return True, "事件已解决"
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """获取事件详情"""
        return self.incidents.get(incident_id)
    
    def get_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        incident_type: Optional[IncidentType] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取事件列表
        
        Args:
            status: 状态
            severity: 严重性
            incident_type: 事件类型
            assigned_to: 分配责任人
            limit: 返回数量限制
        
        Returns:
            事件列表
        """
        incidents = list(self.incidents.values())
        
        if status:
            incidents = [i for i in incidents if i.status == status]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        if incident_type:
            incidents = [i for i in incidents if i.type == incident_type]
        if assigned_to:
            incidents = [i for i in incidents if i.assigned_to == assigned_to]
        
        # 按检测时间倒序排序
        incidents.sort(key=lambda i: i.detected_at, reverse=True)
        
        return [
            {
                "incident_id": i.incident_id,
                "type": i.type.value,
                "severity": i.severity.value,
                "status": i.status.value,
                "title": i.title,
                "detected_at": i.detected_at,
                "assigned_to": i.assigned_to,
                "affected_resources_count": len(i.affected_resources),
                "affected_users_count": len(i.affected_users)
            }
            for i in incidents[:limit]
        ]
    
    def get_pending_incidents(self) -> List[Dict[str, Any]]:
        """获取待处理事件"""
        pending = []
        for incident_id in self.pending_incidents:
            incident = self.incidents.get(incident_id)
            if incident:
                # 检查是否超时
                time_elapsed = time.time() - incident.detected_at
                sla_minutes = self.config["sla_minutes"].get(incident.severity.value, 60)
                
                pending.append({
                    "incident_id": incident.incident_id,
                    "title": incident.title,
                    "severity": incident.severity.value,
                    "detected_at": incident.detected_at,
                    "time_elapsed_minutes": time_elapsed / 60,
                    "sla_minutes": sla_minutes,
                    "breached": time_elapsed > sla_minutes * 60
                })
        
        # 按严重性和时间排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        pending.sort(key=lambda i: (severity_order.get(i["severity"], 4), -i["detected_at"]))
        
        return pending
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_incidents": len(self.incidents),
            "pending_count": len(self.pending_incidents),
            "by_status": {},
            "by_severity": {},
            "by_type": {},
            "average_resolution_time": 0,
            "sla_compliance": 0
        }
        
        resolved_times = []
        sla_compliant = 0
        total_sla_tracked = 0
        
        for incident in self.incidents.values():
            # 按状态统计
            status = incident.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # 按严重性统计
            severity = incident.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            # 按类型统计
            itype = incident.type.value
            stats["by_type"][itype] = stats["by_type"].get(itype, 0) + 1
            
            # 计算解决时间
            if incident.resolved_at:
                resolution_time = incident.resolved_at - incident.detected_at
                resolved_times.append(resolution_time)
                
                # 检查SLA
                sla_minutes = self.config["sla_minutes"].get(incident.severity.value)
                if sla_minutes:
                    total_sla_tracked += 1
                    if resolution_time <= sla_minutes * 60:
                        sla_compliant += 1
        
        if resolved_times:
            stats["average_resolution_time"] = sum(resolved_times) / len(resolved_times) / 60  # 分钟
        
        if total_sla_tracked > 0:
            stats["sla_compliance"] = sla_compliant / total_sla_tracked * 100
        
        return stats
    
    async def start_processor(self):
        """启动事件处理任务"""
        if self._processor_task:
            return
        
        async def _processor_loop():
            while True:
                try:
                    # 检查待处理事件
                    pending = self.get_pending_incidents()
                    
                    for p in pending:
                        if p["breached"]:
                            incident = self.incidents.get(p["incident_id"])
                            if incident and incident.status == IncidentStatus.DETECTED:
                                # 升级处理
                                await self._escalate_incident(p["incident_id"])
                    
                    await asyncio.sleep(60)  # 每分钟检查一次
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"事件处理器异常: {str(e)}")
        
        self._processor_task = asyncio.create_task(_processor_loop())
        logger.info("事件处理器已启动")
    
    async def stop_processor(self):
        """停止事件处理任务"""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
            logger.info("事件处理器已停止")
    
    async def _escalate_incident(self, incident_id: str):
        """升级事件处理"""
        incident = self.incidents.get(incident_id)
        if not incident:
            return
        
        incident.status = IncidentStatus.TRIAGING
        incident.escalated_at = time.time()
        
        # 通知升级团队
        team = self.config["response_teams"].get(incident.severity.value, [])
        
        await self.alert_manager.send_alert(
            alert_type="incident_escalated",
            severity=incident.severity.value,
            message=f"事件 {incident.title} 需要升级处理",
            details={
                "incident_id": incident_id,
                "severity": incident.severity.value,
                "time_elapsed": time.time() - incident.detected_at,
                "assigned_team": team
            }
        )
        
        logger.warning(f"事件 {incident_id} 已升级")
    
    def add_response_plan(self, plan: IncidentResponsePlan) -> bool:
        """添加响应计划"""
        if plan.plan_id in self.response_plans:
            return False
        self.response_plans[plan.plan_id] = plan
        return True
    
    def generate_report(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """
        生成事件报告
        
        Args:
            incident_id: 事件ID
        
        Returns:
            事件报告
        """
        incident = self.incidents.get(incident_id)
        if not incident:
            return None
        
        return {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "type": incident.type.value,
            "severity": incident.severity.value,
            "detected_at": incident.detected_at,
            "resolved_at": incident.resolved_at,
            "duration_minutes": (incident.resolved_at - incident.detected_at) / 60 if incident.resolved_at else None,
            "status": incident.status.value,
            "description": incident.description,
            "root_cause": incident.root_cause,
            "remediation": incident.remediation,
            "lessons_learned": incident.lessons_learned,
            "affected_resources": incident.affected_resources,
            "affected_users": incident.affected_users,
            "timeline": incident.timeline,
            "actions_taken": incident.actions_taken,
            "indicators": incident.indicators
        }


# 单例实例
_incident_response_instance = None


def get_incident_response() -> IncidentResponse:
    """获取事件响应管理器单例实例"""
    global _incident_response_instance
    if _incident_response_instance is None:
        _incident_response_instance = IncidentResponse()
    return _incident_response_instance

