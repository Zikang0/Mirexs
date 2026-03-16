"""
威胁检测模块 - 检测安全威胁
实时监控系统行为，识别潜在的安全威胁和异常活动
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.session_manager import SessionManager, get_session_manager
from ..access_control.permission_manager import PermissionManager, get_permission_manager
from ...utils.common_utilities.validation_utils import ValidationUtils

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """威胁级别枚举"""
    INFO = "info"  # 信息性事件
    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


class ThreatType(Enum):
    """威胁类型枚举"""
    BRUTE_FORCE = "brute_force"  # 暴力破解
    DOS_ATTACK = "dos_attack"  # DoS攻击
    SQL_INJECTION = "sql_injection"  # SQL注入
    XSS_ATTACK = "xss_attack"  # XSS攻击
    PRIVILEGE_ESCALATION = "privilege_escalation"  # 权限提升
    DATA_EXFILTRATION = "data_exfiltration"  # 数据泄露
    ABNORMAL_BEHAVIOR = "abnormal_behavior"  # 异常行为
    MALWARE_DETECTED = "malware_detected"  # 恶意软件
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # 未授权访问
    ACCOUNT_COMPROMISE = "account_compromise"  # 账户入侵
    API_ABUSE = "api_abuse"  # API滥用
    BOT_ACTIVITY = "bot_activity"  # 机器人活动


class ThreatStatus(Enum):
    """威胁状态枚举"""
    DETECTED = "detected"  # 已检测
    ANALYZING = "analyzing"  # 分析中
    CONFIRMED = "confirmed"  # 已确认
    MITIGATED = "mitigated"  # 已缓解
    FALSE_POSITIVE = "false_positive"  # 误报
    IGNORED = "ignored"  # 已忽略


@dataclass
class ThreatIndicator:
    """威胁指标"""
    indicator_id: str
    threat_type: ThreatType
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    frequency: int = 0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatEvent:
    """威胁事件"""
    event_id: str
    threat_type: ThreatType
    level: ThreatLevel
    status: ThreatStatus
    detected_at: float
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    resource: Optional[str] = None
    description: str = ""
    indicators: List[ThreatIndicator] = field(default_factory=list)
    confidence: float = 0.0  # 置信度 0-1
    mitigation_action: Optional[str] = None
    resolved_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreatDetection:
    """
    威胁检测器 - 实时检测安全威胁
    基于规则和异常行为分析识别潜在威胁
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化威胁检测器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 威胁事件存储
        self.threat_events: Dict[str, ThreatEvent] = {}
        
        # 威胁指标缓存
        self.threat_indicators: Dict[str, ThreatIndicator] = {}
        
        # 检测规则
        self.detection_rules: List[Dict[str, Any]] = []
        
        # 请求频率跟踪（用于检测暴力破解和DoS）
        self.request_frequency: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 异常行为基线
        self.behavior_baselines: Dict[str, Dict[str, Any]] = {}
        
        # 黑名单
        self.blacklist: Set[str] = set()
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.session_manager = get_session_manager()
        self.permission_manager = get_permission_manager()
        self.validation_utils = ValidationUtils()
        
        # 加载检测规则
        self._load_detection_rules()
        
        # 启动监控任务
        self._monitor_task = None
        
        logger.info(f"威胁检测器初始化完成，已加载 {len(self.detection_rules)} 条检测规则")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "request_thresholds": {
                "per_ip_per_minute": 60,  # 每个IP每分钟请求上限
                "per_user_per_minute": 30,  # 每个用户每分钟请求上限
                "login_attempts_per_minute": 5,  # 每分钟登录尝试上限
                "api_calls_per_minute": 100  # API调用频率上限
            },
            "time_windows": {
                "short_term": 60,  # 短期窗口（1分钟）
                "medium_term": 300,  # 中期窗口（5分钟）
                "long_term": 3600  # 长期窗口（1小时）
            },
            "thresholds": {
                "brute_force": {
                    "attempts": 5,
                    "window_seconds": 300
                },
                "dos_attack": {
                    "requests_per_second": 10,
                    "window_seconds": 60
                },
                "api_abuse": {
                    "calls_per_minute": 100,
                    "error_rate": 0.3
                },
                "data_exfiltration": {
                    "data_size_mb": 100,
                    "window_seconds": 60
                }
            },
            "enable_real_time_monitoring": True,
            "enable_behavioral_analysis": True,
            "auto_block_threshold": 3,  # 自动封禁阈值（威胁次数）
            "block_duration_seconds": 3600,  # 封禁时长
            "learning_period_days": 7  # 行为学习周期
        }
    
    def _load_detection_rules(self):
        """加载检测规则"""
        self.detection_rules = [
            {
                "id": "rule_brute_force",
                "name": "暴力破解检测",
                "threat_type": ThreatType.BRUTE_FORCE,
                "level": ThreatLevel.HIGH,
                "condition": "login_failures > 5 in 5 minutes",
                "enabled": True
            },
            {
                "id": "rule_dos",
                "name": "DoS攻击检测",
                "threat_type": ThreatType.DOS_ATTACK,
                "level": ThreatLevel.HIGH,
                "condition": "requests_per_second > 10 for 1 minute",
                "enabled": True
            },
            {
                "id": "rule_privilege_escalation",
                "name": "权限提升检测",
                "threat_type": ThreatType.PRIVILEGE_ESCALATION,
                "level": ThreatLevel.CRITICAL,
                "condition": "user attempts admin action without permission",
                "enabled": True
            },
            {
                "id": "rule_api_abuse",
                "name": "API滥用检测",
                "threat_type": ThreatType.API_ABUSE,
                "level": ThreatLevel.MEDIUM,
                "condition": "api_calls > 100 per minute or error_rate > 0.3",
                "enabled": True
            },
            {
                "id": "rule_data_exfiltration",
                "name": "数据泄露检测",
                "threat_type": ThreatType.DATA_EXFILTRATION,
                "level": ThreatLevel.CRITICAL,
                "condition": "data_transfer > 100MB in 1 minute",
                "enabled": True
            },
            {
                "id": "rule_abnormal_hours",
                "name": "异常时段访问",
                "threat_type": ThreatType.ABNORMAL_BEHAVIOR,
                "level": ThreatLevel.MEDIUM,
                "condition": "access outside normal hours with sensitive data",
                "enabled": True
            },
            {
                "id": "rule_multiple_factors",
                "name": "多因素异常",
                "threat_type": ThreatType.ACCOUNT_COMPROMISE,
                "level": ThreatLevel.HIGH,
                "condition": "login from multiple countries in short time",
                "enabled": True
            }
        ]
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """
        分析请求，检测威胁
        
        Args:
            request_data: 请求数据
        
        Returns:
            检测到的威胁事件，如果没有则返回None
        """
        threats = []
        
        # 提取请求信息
        source_ip = request_data.get("source_ip")
        user_id = request_data.get("user_id")
        action = request_data.get("action")
        resource = request_data.get("resource")
        timestamp = request_data.get("timestamp", time.time())
        
        # 记录请求频率
        self._record_request(source_ip, user_id, timestamp)
        
        # 1. 检查黑名单
        if source_ip and source_ip in self.blacklist:
            threat = ThreatEvent(
                event_id=self._generate_event_id(),
                threat_type=ThreatType.UNAUTHORIZED_ACCESS,
                level=ThreatLevel.HIGH,
                status=ThreatStatus.DETECTED,
                detected_at=time.time(),
                source_ip=source_ip,
                user_id=user_id,
                resource=resource,
                description=f"来自黑名单IP的访问: {source_ip}",
                confidence=1.0,
                metadata=request_data
            )
            threats.append(threat)
        
        # 2. 暴力破解检测
        brute_force = await self._detect_brute_force(source_ip, user_id)
        if brute_force:
            threats.append(brute_force)
        
        # 3. DoS攻击检测
        dos = await self._detect_dos_attack(source_ip)
        if dos:
            threats.append(dos)
        
        # 4. API滥用检测
        api_abuse = await self._detect_api_abuse(user_id, action, request_data)
        if api_abuse:
            threats.append(api_abuse)
        
        # 5. 权限提升检测
        privilege = await self._detect_privilege_escalation(user_id, action, resource)
        if privilege:
            threats.append(privilege)
        
        # 6. SQL注入检测
        sql_injection = self._detect_sql_injection(request_data)
        if sql_injection:
            threats.append(sql_injection)
        
        # 7. XSS攻击检测
        xss = self._detect_xss(request_data)
        if xss:
            threats.append(xss)
        
        # 8. 异常行为检测
        if self.config["enable_behavioral_analysis"]:
            abnormal = await self._detect_abnormal_behavior(user_id, action, resource, timestamp)
            if abnormal:
                threats.append(abnormal)
        
        # 处理检测到的威胁
        for threat in threats:
            await self._handle_threat(threat)
        
        return threats[0] if threats else None
    
    def _record_request(self, source_ip: Optional[str], user_id: Optional[str], timestamp: float):
        """记录请求频率"""
        if source_ip:
            self.request_frequency[f"ip:{source_ip}"].append(timestamp)
        if user_id:
            self.request_frequency[f"user:{user_id}"].append(timestamp)
    
    def _get_request_count(self, key: str, window_seconds: int) -> int:
        """获取指定时间窗口内的请求次数"""
        if key not in self.request_frequency:
            return 0
        
        cutoff = time.time() - window_seconds
        timestamps = self.request_frequency[key]
        return sum(1 for t in timestamps if t > cutoff)
    
    async def _detect_brute_force(
        self,
        source_ip: Optional[str],
        user_id: Optional[str]
    ) -> Optional[ThreatEvent]:
        """检测暴力破解"""
        config = self.config["thresholds"]["brute_force"]
        
        # 检查登录失败次数
        if source_ip:
            # 这里应该从访问日志中获取登录失败次数
            # 简化实现：检查请求频率
            request_count = self._get_request_count(
                f"ip:{source_ip}",
                config["window_seconds"]
            )
            
            if request_count > config["attempts"] * 3:  # 假设1/3是登录尝试
                threat = ThreatEvent(
                    event_id=self._generate_event_id(),
                    threat_type=ThreatType.BRUTE_FORCE,
                    level=ThreatLevel.HIGH,
                    status=ThreatStatus.DETECTED,
                    detected_at=time.time(),
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"可能的暴力破解攻击: IP {source_ip} 在 {config['window_seconds']}秒内请求 {request_count} 次",
                    confidence=0.7,
                    metadata={"request_count": request_count, "window": config["window_seconds"]}
                )
                return threat
        
        return None
    
    async def _detect_dos_attack(self, source_ip: Optional[str]) -> Optional[ThreatEvent]:
        """检测DoS攻击"""
        if not source_ip:
            return None
        
        config = self.config["thresholds"]["dos_attack"]
        
        # 计算每秒请求数
        request_count = self._get_request_count(f"ip:{source_ip}", config["window_seconds"])
        requests_per_second = request_count / config["window_seconds"]
        
        if requests_per_second > config["requests_per_second"]:
            threat = ThreatEvent(
                event_id=self._generate_event_id(),
                threat_type=ThreatType.DOS_ATTACK,
                level=ThreatLevel.HIGH,
                status=ThreatStatus.DETECTED,
                detected_at=time.time(),
                source_ip=source_ip,
                description=f"可能的DoS攻击: {requests_per_second:.2f} 请求/秒",
                confidence=min(0.9, requests_per_second / config["requests_per_second"] / 2),
                metadata={
                    "requests_per_second": requests_per_second,
                    "threshold": config["requests_per_second"]
                }
            )
            return threat
        
        return None
    
    async def _detect_api_abuse(
        self,
        user_id: Optional[str],
        action: Optional[str],
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """检测API滥用"""
        if not user_id or not action or not action.startswith("api:"):
            return None
        
        config = self.config["thresholds"]["api_abuse"]
        
        # 检查API调用频率
        call_count = self._get_request_count(f"user:{user_id}", 60)  # 1分钟窗口
        if call_count > config["calls_per_minute"]:
            threat = ThreatEvent(
                event_id=self._generate_event_id(),
                threat_type=ThreatType.API_ABUSE,
                level=ThreatLevel.MEDIUM,
                status=ThreatStatus.DETECTED,
                detected_at=time.time(),
                user_id=user_id,
                description=f"API滥用: 用户 {user_id} 1分钟内调用 {call_count} 次",
                confidence=0.8,
                metadata={"call_count": call_count, "threshold": config["calls_per_minute"]}
            )
            return threat
        
        # 检查错误率（简化实现）
        # 实际应从日志中获取错误率
        
        return None
    
    async def _detect_privilege_escalation(
        self,
        user_id: Optional[str],
        action: Optional[str],
        resource: Optional[str]
    ) -> Optional[ThreatEvent]:
        """检测权限提升"""
        if not user_id or not action:
            return None
        
        # 检查用户是否有权限执行该操作
        if action in ["admin:create", "admin:delete", "system:config:write"]:
            from ..access_control.permission_manager import get_permission_manager
            perm_manager = get_permission_manager()
            
            result = perm_manager.check_permission(
                user_id=user_id,
                permission=action.replace(":", "."),
                resource_id=resource
            )
            
            if not result.granted:
                threat = ThreatEvent(
                    event_id=self._generate_event_id(),
                    threat_type=ThreatType.PRIVILEGE_ESCALATION,
                    level=ThreatLevel.CRITICAL,
                    status=ThreatStatus.DETECTED,
                    detected_at=time.time(),
                    user_id=user_id,
                    resource=resource,
                    description=f"权限提升尝试: 用户 {user_id} 尝试执行 {action}",
                    confidence=0.9,
                    metadata={"action": action, "permission_check": result.__dict__}
                )
                return threat
        
        return None
    
    def _detect_sql_injection(self, request_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """检测SQL注入"""
        sql_patterns = [
            r"'.*OR.*'.*=",
            r"UNION.*SELECT",
            r"DROP.*TABLE",
            r"DELETE.*FROM",
            r"INSERT.*INTO",
            r"UPDATE.*SET",
            r"EXEC.*XP_",
            r"WAITFOR.*DELAY"
        ]
        
        import re
        
        # 检查请求参数
        for key, value in request_data.items():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        threat = ThreatEvent(
                            event_id=self._generate_event_id(),
                            threat_type=ThreatType.SQL_INJECTION,
                            level=ThreatLevel.HIGH,
                            status=ThreatStatus.DETECTED,
                            detected_at=time.time(),
                            source_ip=request_data.get("source_ip"),
                            user_id=request_data.get("user_id"),
                            description=f"SQL注入尝试: 参数 {key} 包含可疑模式",
                            confidence=0.85,
                            metadata={"parameter": key, "pattern": pattern}
                        )
                        return threat
        
        return None
    
    def _detect_xss(self, request_data: Dict[str, Any]) -> Optional[ThreatEvent]:
        """检测XSS攻击"""
        xss_patterns = [
            r"<script>",
            r"javascript:",
            r"onerror=",
            r"onload=",
            r"onclick=",
            r"alert\(",
            r"prompt\(",
            r"confirm\("
        ]
        
        import re
        
        for key, value in request_data.items():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        threat = ThreatEvent(
                            event_id=self._generate_event_id(),
                            threat_type=ThreatType.XSS_ATTACK,
                            level=ThreatLevel.HIGH,
                            status=ThreatStatus.DETECTED,
                            detected_at=time.time(),
                            source_ip=request_data.get("source_ip"),
                            user_id=request_data.get("user_id"),
                            description=f"XSS攻击尝试: 参数 {key} 包含可疑脚本",
                            confidence=0.8,
                            metadata={"parameter": key, "pattern": pattern}
                        )
                        return threat
        
        return None
    
    async def _detect_abnormal_behavior(
        self,
        user_id: Optional[str],
        action: Optional[str],
        resource: Optional[str],
        timestamp: float
    ) -> Optional[ThreatEvent]:
        """检测异常行为"""
        if not user_id:
            return None
        
        # 获取用户行为基线
        baseline = self.behavior_baselines.get(user_id)
        if not baseline:
            # 首次学习
            self.behavior_baselines[user_id] = {
                "first_seen": timestamp,
                "normal_hours": self._learn_normal_hours([]),
                "sensitive_actions": set(),
                "locations": set()
            }
            return None
        
        # 检查异常时段访问敏感数据
        if resource and "sensitive" in resource:
            hour = datetime.fromtimestamp(timestamp).hour
            normal_hours = baseline.get("normal_hours", set(range(9, 18)))
            
            if hour not in normal_hours:
                threat = ThreatEvent(
                    event_id=self._generate_event_id(),
                    threat_type=ThreatType.ABNORMAL_BEHAVIOR,
                    level=ThreatLevel.MEDIUM,
                    status=ThreatStatus.DETECTED,
                    detected_at=time.time(),
                    user_id=user_id,
                    resource=resource,
                    description=f"异常时段访问敏感数据: 用户 {user_id} 在 {hour}点访问 {resource}",
                    confidence=0.6,
                    metadata={"hour": hour, "normal_hours": list(normal_hours)}
                )
                return threat
        
        return None
    
    def _learn_normal_hours(self, activity_log: List[float]) -> Set[int]:
        """学习用户正常活动时段"""
        # 简化实现：返回工作时间
        return set(range(9, 18))
    
    async def _handle_threat(self, threat: ThreatEvent) -> None:
        """处理检测到的威胁"""
        # 存储威胁事件
        self.threat_events[threat.event_id] = threat
        
        # 更新威胁指标
        self._update_threat_indicators(threat)
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=threat.user_id,
            event_type=f"THREAT_DETECTED_{threat.threat_type.value}",
            severity=threat.level.value,
            details={
                "threat_id": threat.event_id,
                "description": threat.description,
                "confidence": threat.confidence,
                "source_ip": threat.source_ip
            }
        )
        
        # 检查是否需要自动封禁
        await self._check_auto_block(threat)
        
        # 发送告警
        await self._send_alert(threat)
        
        logger.warning(f"检测到威胁 [{threat.level.value.upper()}]: {threat.description}")
    
    def _update_threat_indicators(self, threat: ThreatEvent) -> None:
        """更新威胁指标"""
        for indicator in threat.indicators:
            if indicator.indicator_id not in self.threat_indicators:
                self.threat_indicators[indicator.indicator_id] = indicator
            else:
                existing = self.threat_indicators[indicator.indicator_id]
                existing.frequency += 1
                existing.last_seen = time.time()
    
    async def _check_auto_block(self, threat: ThreatEvent) -> None:
        """检查是否需要自动封禁"""
        if threat.level not in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            return
        
        # 统计IP的威胁次数
        if threat.source_ip:
            ip_threats = [
                t for t in self.threat_events.values()
                if t.source_ip == threat.source_ip and
                t.level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            ]
            
            if len(ip_threats) >= self.config["auto_block_threshold"]:
                # 加入黑名单
                self.blacklist.add(threat.source_ip)
                
                # 记录封禁
                self.access_logger.log_security_event(
                    user_id="system",
                    event_type="IP_AUTO_BLOCKED",
                    severity="high",
                    details={
                        "source_ip": threat.source_ip,
                        "threat_count": len(ip_threats),
                        "block_duration": self.config["block_duration_seconds"]
                    }
                )
                
                logger.warning(f"IP {threat.source_ip} 已自动封禁 {self.config['block_duration_seconds']}秒")
    
    async def _send_alert(self, threat: ThreatEvent) -> None:
        """发送告警"""
        from .alert_manager import get_alert_manager
        alert_manager = get_alert_manager()
        
        await alert_manager.send_alert(
            alert_type=f"threat_{threat.threat_type.value}",
            severity=threat.level.value,
            message=threat.description,
            details={
                "threat_id": threat.event_id,
                "source_ip": threat.source_ip,
                "user_id": threat.user_id,
                "confidence": threat.confidence
            }
        )
    
    def _generate_event_id(self) -> str:
        """生成事件ID"""
        import secrets
        return f"threat_{int(time.time())}_{secrets.token_hex(4)}"
    
    def get_threats(
        self,
        level: Optional[ThreatLevel] = None,
        threat_type: Optional[ThreatType] = None,
        status: Optional[ThreatStatus] = None,
        limit: int = 100
    ) -> List[ThreatEvent]:
        """
        获取威胁事件列表
        
        Args:
            level: 威胁级别
            threat_type: 威胁类型
            status: 威胁状态
            limit: 返回数量限制
        
        Returns:
            威胁事件列表
        """
        threats = list(self.threat_events.values())
        
        if level:
            threats = [t for t in threats if t.level == level]
        if threat_type:
            threats = [t for t in threats if t.threat_type == threat_type]
        if status:
            threats = [t for t in threats if t.status == status]
        
        # 按时间倒序排序
        threats.sort(key=lambda t: t.detected_at, reverse=True)
        
        return threats[:limit]
    
    def get_threat_statistics(self) -> Dict[str, Any]:
        """获取威胁统计"""
        stats = {
            "total_threats": len(self.threat_events),
            "by_level": {},
            "by_type": {},
            "by_status": {},
            "top_ips": {},
            "recent_threats": []
        }
        
        for threat in self.threat_events.values():
            # 按级别统计
            level = threat.level.value
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            
            # 按类型统计
            ttype = threat.threat_type.value
            stats["by_type"][ttype] = stats["by_type"].get(ttype, 0) + 1
            
            # 按状态统计
            status = threat.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # 按IP统计
            if threat.source_ip:
                stats["top_ips"][threat.source_ip] = stats["top_ips"].get(threat.source_ip, 0) + 1
        
        # 获取最近威胁
        recent = self.get_threats(limit=10)
        stats["recent_threats"] = [
            {
                "event_id": t.event_id,
                "type": t.threat_type.value,
                "level": t.level.value,
                "description": t.description,
                "detected_at": t.detected_at
            }
            for t in recent
        ]
        
        return stats
    
    def update_threat_status(
        self,
        event_id: str,
        status: ThreatStatus,
        resolution: Optional[str] = None
    ) -> bool:
        """
        更新威胁状态
        
        Args:
            event_id: 事件ID
            status: 新状态
            resolution: 解决方案
        
        Returns:
            是否成功
        """
        if event_id not in self.threat_events:
            return False
        
        threat = self.threat_events[event_id]
        threat.status = status
        
        if status in [ThreatStatus.MITIGATED, ThreatStatus.FALSE_POSITIVE, ThreatStatus.IGNORED]:
            threat.resolved_at = time.time()
            threat.metadata["resolution"] = resolution
        
        logger.info(f"威胁 {event_id} 状态更新为 {status.value}")
        return True
    
    def add_to_blacklist(self, source_ip: str, reason: str) -> bool:
        """
        添加IP到黑名单
        
        Args:
            source_ip: IP地址
            reason: 原因
        
        Returns:
            是否成功
        """
        self.blacklist.add(source_ip)
        
        self.access_logger.log_security_event(
            user_id="system",
            event_type="IP_MANUAL_BLOCK",
            severity="high",
            details={
                "source_ip": source_ip,
                "reason": reason,
                "timestamp": time.time()
            }
        )
        
        logger.info(f"IP {source_ip} 已手动添加到黑名单: {reason}")
        return True
    
    def remove_from_blacklist(self, source_ip: str) -> bool:
        """
        从黑名单移除IP
        
        Args:
            source_ip: IP地址
        
        Returns:
            是否成功
        """
        if source_ip in self.blacklist:
            self.blacklist.remove(source_ip)
            logger.info(f"IP {source_ip} 已从黑名单移除")
            return True
        return False
    
    async def start_monitoring(self):
        """启动实时监控"""
        if self._monitor_task:
            return
        
        async def _monitor_loop():
            while True:
                try:
                    # 定期清理过期数据
                    await self._cleanup_expired_data()
                    
                    # 更新行为基线
                    if self.config["enable_behavioral_analysis"]:
                        await self._update_behavior_baselines()
                    
                    await asyncio.sleep(60)  # 每分钟检查一次
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"监控循环异常: {str(e)}")
        
        self._monitor_task = asyncio.create_task(_monitor_loop())
        logger.info("威胁监控任务已启动")
    
    async def stop_monitoring(self):
        """停止实时监控"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("威胁监控任务已停止")
    
    async def _cleanup_expired_data(self):
        """清理过期数据"""
        now = time.time()
        
        # 清理超过7天的威胁事件
        expired = []
        for event_id, threat in self.threat_events.items():
            if now - threat.detected_at > 7 * 24 * 3600:
                expired.append(event_id)
        
        for event_id in expired:
            del self.threat_events[event_id]
        
        if expired:
            logger.debug(f"清理了 {len(expired)} 个过期威胁事件")
    
    async def _update_behavior_baselines(self):
        """更新行为基线"""
        # 简化实现
        pass


# 单例实例
_threat_detection_instance = None


def get_threat_detection() -> ThreatDetection:
    """获取威胁检测器单例实例"""
    global _threat_detection_instance
    if _threat_detection_instance is None:
        _threat_detection_instance = ThreatDetection()
    return _threat_detection_instance

