"""
入侵检测模块 - 检测入侵行为
实时监控系统活动，识别入侵尝试和异常行为
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime

from ..access_control.access_logger import AccessLogger, get_access_logger
from ..access_control.session_manager import SessionManager, get_session_manager
from .threat_detection import ThreatDetection, get_threat_detection

logger = logging.getLogger(__name__)


class IntrusionType(Enum):
    """入侵类型枚举"""
    PORT_SCAN = "port_scan"  # 端口扫描
    BRUTE_FORCE = "brute_force"  # 暴力破解
    DOS_ATTACK = "dos_attack"  # DoS攻击
    SQL_INJECTION = "sql_injection"  # SQL注入
    XSS_ATTACK = "xss_attack"  # XSS攻击
    CSRF_ATTACK = "csrf_attack"  # CSRF攻击
    PATH_TRAVERSAL = "path_traversal"  # 路径遍历
    COMMAND_INJECTION = "command_injection"  # 命令注入
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # 未授权访问
    PRIVILEGE_ESCALATION = "privilege_escalation"  # 权限提升
    DATA_EXFILTRATION = "data_exfiltration"  # 数据泄露
    MALWARE_ACTIVITY = "malware_activity"  # 恶意软件活动


class IntrusionSeverity(Enum):
    """入侵严重性枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IntrusionStatus(Enum):
    """入侵状态枚举"""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    BLOCKED = "blocked"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false_positive"
    IGNORED = "ignored"


@dataclass
class IntrusionAlert:
    """入侵告警"""
    alert_id: str
    intrusion_type: IntrusionType
    severity: IntrusionSeverity
    status: IntrusionStatus
    detected_at: float
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    target: Optional[str] = None
    description: str = ""
    indicators: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    mitigated_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntrusionDetection:
    """
    入侵检测系统 - 检测入侵行为
    基于规则和异常行为分析识别入侵尝试
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化入侵检测系统
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 入侵告警存储
        self.alerts: Dict[str, IntrusionAlert] = {}
        
        # 网络流量监控
        self.traffic_patterns: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 端口扫描检测
        self.port_scan_tracker: Dict[str, Dict[int, float]] = defaultdict(dict)
        
        # 初始化依赖
        self.access_logger = get_access_logger()
        self.session_manager = get_session_manager()
        self.threat_detection = get_threat_detection()
        
        # 检测规则
        self.detection_rules = self._load_detection_rules()
        
        # 启动监控
        self._monitor_task = None
        
        logger.info("入侵检测系统初始化完成")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "port_scan_threshold": 20,  # 20个端口
            "port_scan_window": 60,  # 60秒内
            "brute_force_threshold": 5,  # 5次失败
            "brute_force_window": 300,  # 5分钟内
            "dos_threshold": 100,  # 100请求/秒
            "dos_window": 10,  # 10秒窗口
            "syn_flood_threshold": 50,  # 50个SYN包/秒
            "enable_real_time": True,
            "auto_block": True,
            "block_duration": 3600,  # 1小时
            "signature_based_detection": True,
            "anomaly_based_detection": True
        }
    
    def _load_detection_rules(self) -> List[Dict[str, Any]]:
        """加载检测规则"""
        return [
            {
                "id": "rule_port_scan",
                "name": "端口扫描检测",
                "type": IntrusionType.PORT_SCAN,
                "severity": IntrusionSeverity.MEDIUM,
                "pattern": "multiple_ports_in_short_time",
                "enabled": True
            },
            {
                "id": "rule_syn_flood",
                "name": "SYN Flood检测",
                "type": IntrusionType.DOS_ATTACK,
                "severity": IntrusionSeverity.HIGH,
                "pattern": "high_rate_of_syn_packets",
                "enabled": True
            },
            {
                "id": "rule_sql_injection",
                "name": "SQL注入检测",
                "type": IntrusionType.SQL_INJECTION,
                "severity": IntrusionSeverity.HIGH,
                "pattern": "sql_keywords_in_request",
                "enabled": True
            },
            {
                "id": "rule_path_traversal",
                "name": "路径遍历检测",
                "type": IntrusionType.PATH_TRAVERSAL,
                "severity": IntrusionSeverity.MEDIUM,
                "pattern": "../ in path",
                "enabled": True
            }
        ]
    
    async def analyze_network_traffic(
        self,
        source_ip: str,
        dest_port: int,
        protocol: str,
        packet_size: int,
        flags: Optional[List[str]] = None
    ) -> Optional[IntrusionAlert]:
        """
        分析网络流量
        
        Args:
            source_ip: 源IP
            dest_port: 目标端口
            protocol: 协议
            packet_size: 包大小
            flags: TCP标志
        
        Returns:
            入侵告警
        """
        alerts = []
        
        # 记录流量
        key = f"traffic:{source_ip}"
        self.traffic_patterns[key].append({
            "timestamp": time.time(),
            "port": dest_port,
            "protocol": protocol,
            "size": packet_size,
            "flags": flags
        })
        
        # 检测端口扫描
        port_scan = self._detect_port_scan(source_ip)
        if port_scan:
            alerts.append(port_scan)
        
        # 检测SYN Flood
        syn_flood = self._detect_syn_flood(source_ip, flags)
        if syn_flood:
            alerts.append(syn_flood)
        
        # 检测异常流量
        if len(alerts) > 0:
            for alert in alerts:
                await self._handle_intrusion(alert)
            return alerts[0]
        
        return None
    
    def _detect_port_scan(self, source_ip: str) -> Optional[IntrusionAlert]:
        """检测端口扫描"""
        key = f"traffic:{source_ip}"
        if key not in self.traffic_patterns:
            return None
        
        # 获取最近流量
        recent = list(self.traffic_patterns[key])
        cutoff = time.time() - self.config["port_scan_window"]
        recent = [p for p in recent if p["timestamp"] > cutoff]
        
        # 统计不同端口
        ports = set(p["port"] for p in recent)
        
        if len(ports) > self.config["port_scan_threshold"]:
            alert = IntrusionAlert(
                alert_id=f"ids_{int(time.time())}_{source_ip.replace('.', '_')}",
                intrusion_type=IntrusionType.PORT_SCAN,
                severity=IntrusionSeverity.MEDIUM,
                status=IntrusionStatus.DETECTED,
                detected_at=time.time(),
                source_ip=source_ip,
                description=f"检测到端口扫描: {len(ports)} 个不同端口在 {self.config['port_scan_window']}秒内",
                indicators=[{
                    "type": "port_scan",
                    "ports": list(ports),
                    "count": len(ports)
                }],
                confidence=0.8
            )
            return alert
        
        return None
    
    def _detect_syn_flood(self, source_ip: str, flags: Optional[List[str]]) -> Optional[IntrusionAlert]:
        """检测SYN Flood"""
        if not flags or "SYN" not in flags:
            return None
        
        key = f"traffic:{source_ip}"
        if key not in self.traffic_patterns:
            return None
        
        # 统计SYN包
        recent = list(self.traffic_patterns[key])
        cutoff = time.time() - self.config["dos_window"]
        recent = [p for p in recent if p["timestamp"] > cutoff]
        
        syn_packets = [p for p in recent if p.get("flags") and "SYN" in p["flags"]]
        
        if len(syn_packets) > self.config["syn_flood_threshold"]:
            alert = IntrusionAlert(
                alert_id=f"ids_{int(time.time())}_{source_ip.replace('.', '_')}",
                intrusion_type=IntrusionType.DOS_ATTACK,
                severity=IntrusionSeverity.HIGH,
                status=IntrusionStatus.DETECTED,
                detected_at=time.time(),
                source_ip=source_ip,
                description=f"检测到SYN Flood攻击: {len(syn_packets)} SYN包/秒",
                indicators=[{
                    "type": "syn_flood",
                    "rate": len(syn_packets) / self.config["dos_window"]
                }],
                confidence=0.9
            )
            return alert
        
        return None
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[IntrusionAlert]:
        """
        分析HTTP请求
        
        Args:
            request_data: 请求数据
        
        Returns:
            入侵告警
        """
        alerts = []
        
        # SQL注入检测
        sql_injection = self._detect_sql_injection(request_data)
        if sql_injection:
            alerts.append(sql_injection)
        
        # XSS检测
        xss = self._detect_xss(request_data)
        if xss:
            alerts.append(xss)
        
        # 路径遍历检测
        path_traversal = self._detect_path_traversal(request_data)
        if path_traversal:
            alerts.append(path_traversal)
        
        # 命令注入检测
        cmd_injection = self._detect_command_injection(request_data)
        if cmd_injection:
            alerts.append(cmd_injection)
        
        if alerts:
            for alert in alerts:
                await self._handle_intrusion(alert)
            return alerts[0]
        
        return None
    
    def _detect_sql_injection(self, request_data: Dict[str, Any]) -> Optional[IntrusionAlert]:
        """检测SQL注入"""
        sql_patterns = [
            r"'.*OR.*'.*=",
            r"UNION.*SELECT",
            r"DROP.*TABLE",
            r"DELETE.*FROM",
            r"INSERT.*INTO",
            r"UPDATE.*SET",
            r"EXEC.*XP_",
            r"WAITFOR.*DELAY",
            r"BENCHMARK\(",
            r"SLEEP\("
        ]
        
        import re
        
        for key, value in request_data.items():
            if isinstance(value, str):
                for pattern in sql_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        alert = IntrusionAlert(
                            alert_id=f"ids_{int(time.time())}_{hash(value) % 10000}",
                            intrusion_type=IntrusionType.SQL_INJECTION,
                            severity=IntrusionSeverity.HIGH,
                            status=IntrusionStatus.DETECTED,
                            detected_at=time.time(),
                            source_ip=request_data.get("source_ip"),
                            user_id=request_data.get("user_id"),
                            target=request_data.get("path"),
                            description=f"SQL注入尝试: 参数 {key} 包含可疑模式",
                            indicators=[{
                                "type": "sql_injection",
                                "parameter": key,
                                "pattern": pattern,
                                "value": value[:100]
                            }],
                            confidence=0.85
                        )
                        return alert
        
        return None
    
    def _detect_xss(self, request_data: Dict[str, Any]) -> Optional[IntrusionAlert]:
        """检测XSS攻击"""
        xss_patterns = [
            r"<script>",
            r"javascript:",
            r"onerror=",
            r"onload=",
            r"onclick=",
            r"alert\(",
            r"prompt\(",
            r"confirm\(",
            r"document\.cookie",
            r"<img.*src=.*onerror"
        ]
        
        import re
        
        for key, value in request_data.items():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        alert = IntrusionAlert(
                            alert_id=f"ids_{int(time.time())}_{hash(value) % 10000}",
                            intrusion_type=IntrusionType.XSS_ATTACK,
                            severity=IntrusionSeverity.HIGH,
                            status=IntrusionStatus.DETECTED,
                            detected_at=time.time(),
                            source_ip=request_data.get("source_ip"),
                            user_id=request_data.get("user_id"),
                            target=request_data.get("path"),
                            description=f"XSS攻击尝试: 参数 {key} 包含可疑脚本",
                            indicators=[{
                                "type": "xss",
                                "parameter": key,
                                "pattern": pattern,
                                "value": value[:100]
                            }],
                            confidence=0.8
                        )
                        return alert
        
        return None
    
    def _detect_path_traversal(self, request_data: Dict[str, Any]) -> Optional[IntrusionAlert]:
        """检测路径遍历"""
        traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
            r"\.\.%2f",
            r"\.\.%5c"
        ]
        
        path = request_data.get("path", "")
        
        import re
        for pattern in traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                alert = IntrusionAlert(
                    alert_id=f"ids_{int(time.time())}_{hash(path) % 10000}",
                    intrusion_type=IntrusionType.PATH_TRAVERSAL,
                    severity=IntrusionSeverity.MEDIUM,
                    status=IntrusionStatus.DETECTED,
                    detected_at=time.time(),
                    source_ip=request_data.get("source_ip"),
                    user_id=request_data.get("user_id"),
                    target=path,
                    description=f"路径遍历尝试: {path}",
                    indicators=[{
                        "type": "path_traversal",
                        "pattern": pattern,
                        "path": path
                    }],
                    confidence=0.9
                )
                return alert
        
        return None
    
    def _detect_command_injection(self, request_data: Dict[str, Any]) -> Optional[IntrusionAlert]:
        """检测命令注入"""
        cmd_patterns = [
            r";.*\s",
            r"\|.*\s",
            r"&&.*\s",
            r"\|\|.*\s",
            r"`.*`",
            r"\$\(.*\)",
            r"ping.*-c",
            r"wget.*http",
            r"curl.*http",
            r"nslookup.*"
        ]
        
        import re
        
        for key, value in request_data.items():
            if isinstance(value, str):
                for pattern in cmd_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        alert = IntrusionAlert(
                            alert_id=f"ids_{int(time.time())}_{hash(value) % 10000}",
                            intrusion_type=IntrusionType.COMMAND_INJECTION,
                            severity=IntrusionSeverity.HIGH,
                            status=IntrusionStatus.DETECTED,
                            detected_at=time.time(),
                            source_ip=request_data.get("source_ip"),
                            user_id=request_data.get("user_id"),
                            target=request_data.get("path"),
                            description=f"命令注入尝试: 参数 {key} 包含可疑命令",
                            indicators=[{
                                "type": "command_injection",
                                "parameter": key,
                                "pattern": pattern,
                                "value": value[:100]
                            }],
                            confidence=0.85
                        )
                        return alert
        
        return None
    
    async def _handle_intrusion(self, alert: IntrusionAlert):
        """处理入侵告警"""
        self.alerts[alert.alert_id] = alert
        
        # 记录审计日志
        self.access_logger.log_security_event(
            user_id=alert.user_id,
            event_type=f"INTRUSION_{alert.intrusion_type.value}",
            severity=alert.severity.value,
            details={
                "alert_id": alert.alert_id,
                "description": alert.description,
                "source_ip": alert.source_ip,
                "confidence": alert.confidence
            }
        )
        
        # 自动阻断
        if self.config["auto_block"] and alert.severity in [IntrusionSeverity.HIGH, IntrusionSeverity.CRITICAL]:
            await self._block_source(alert)
        
        # 发送告警
        await self._send_alert(alert)
        
        logger.warning(f"检测到入侵 [{alert.severity.value}]: {alert.description}")
    
    async def _block_source(self, alert: IntrusionAlert):
        """阻断攻击源"""
        if alert.source_ip:
            # 添加到威胁检测的黑名单
            self.threat_detection.add_to_blacklist(
                source_ip=alert.source_ip,
                reason=f"入侵检测自动阻断: {alert.intrusion_type.value}"
            )
            
            alert.status = IntrusionStatus.BLOCKED
            alert.metadata["blocked_at"] = time.time()
            alert.metadata["block_duration"] = self.config["block_duration"]
            
            logger.info(f"已阻断攻击源: {alert.source_ip}")
    
    async def _send_alert(self, alert: IntrusionAlert):
        """发送告警"""
        from .alert_manager import get_alert_manager
        alert_manager = get_alert_manager()
        
        await alert_manager.send_alert(
            alert_type=f"intrusion_{alert.intrusion_type.value}",
            severity=alert.severity.value,
            message=alert.description,
            details={
                "alert_id": alert.alert_id,
                "source_ip": alert.source_ip,
                "user_id": alert.user_id,
                "confidence": alert.confidence,
                "indicators": alert.indicators
            }
        )
    
    def get_alerts(
        self,
        intrusion_type: Optional[IntrusionType] = None,
        severity: Optional[IntrusionSeverity] = None,
        status: Optional[IntrusionStatus] = None,
        source_ip: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取入侵告警"""
        alerts = list(self.alerts.values())
        
        if intrusion_type:
            alerts = [a for a in alerts if a.intrusion_type == intrusion_type]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if source_ip:
            alerts = [a for a in alerts if a.source_ip == source_ip]
        
        alerts.sort(key=lambda a: a.detected_at, reverse=True)
        
        return [
            {
                "alert_id": a.alert_id,
                "type": a.intrusion_type.value,
                "severity": a.severity.value,
                "status": a.status.value,
                "detected_at": a.detected_at,
                "source_ip": a.source_ip,
                "description": a.description,
                "confidence": a.confidence
            }
            for a in alerts[:limit]
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_alerts": len(self.alerts),
            "by_type": {},
            "by_severity": {},
            "by_status": {},
            "top_ips": {}
        }
        
        for alert in self.alerts.values():
            # 按类型统计
            atype = alert.intrusion_type.value
            stats["by_type"][atype] = stats["by_type"].get(atype, 0) + 1
            
            # 按严重性统计
            severity = alert.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            # 按状态统计
            status = alert.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # 按IP统计
            if alert.source_ip:
                stats["top_ips"][alert.source_ip] = stats["top_ips"].get(alert.source_ip, 0) + 1
        
        return stats
    
    async def start_monitoring(self):
        """启动实时监控"""
        if self._monitor_task:
            return
        
        async def _monitor_loop():
            while True:
                try:
                    # 定期清理过期数据
                    self._cleanup_old_data()
                    await asyncio.sleep(3600)  # 每小时清理一次
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"监控循环异常: {str(e)}")
        
        self._monitor_task = asyncio.create_task(_monitor_loop())
        logger.info("入侵检测监控已启动")
    
    async def stop_monitoring(self):
        """停止实时监控"""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("入侵检测监控已停止")
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        cutoff = time.time() - 7 * 24 * 3600  # 7天
        
        # 清理旧告警
        expired = []
        for alert_id, alert in self.alerts.items():
            if alert.detected_at < cutoff:
                expired.append(alert_id)
        
        for alert_id in expired:
            del self.alerts[alert_id]
        
        if expired:
            logger.debug(f"清理了 {len(expired)} 条旧入侵告警")


# 单例实例
_intrusion_detection_instance = None


def get_intrusion_detection() -> IntrusionDetection:
    """获取入侵检测系统单例实例"""
    global _intrusion_detection_instance
    if _intrusion_detection_instance is None:
        _intrusion_detection_instance = IntrusionDetection()
    return _intrusion_detection_instance

