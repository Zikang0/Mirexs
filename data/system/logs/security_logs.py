"""
安全日志模块 - 记录安全相关事件
负责记录认证、授权、安全威胁等安全事件
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class SecurityEventType(Enum):
    AUTHENTICATION_SUCCESS = "authentication_success"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_GRANTED = "authorization_granted"
    AUTHORIZATION_DENIED = "authorization_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_THREAT = "security_threat"
    MALWARE_DETECTED = "malware_detected"
    INTRUSION_ATTEMPT = "intrusion_attempt"

class SecurityLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecurityLogger:
    """安全日志记录器"""
    
    def __init__(self, log_dir: str = "logs/security"):
        self.log_dir = log_dir
        self._setup_logging()
    
    def _setup_logging(self):
        """配置安全日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 安全日志记录器
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # 安全日志文件处理器
        log_file = f"{self.log_dir}/security.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # 安全专用格式
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - [%(event_type)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def log_security_event(self, 
                          event_type: SecurityEventType,
                          user_id: Optional[str],
                          source_ip: Optional[str],
                          details: Dict[str, Any],
                          security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """记录安全事件"""
        
        # 生成事件ID
        event_id = self._generate_event_id(event_type, user_id, source_ip)
        
        security_event = {
            "event_id": event_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "source_ip": source_ip,
            "security_level": security_level.value,
            "details": details
        }
        
        # 记录到结构化日志
        self._write_security_log(security_event)
        
        # 根据安全级别记录到不同日志级别
        log_message = f"Event: {event_type.value}, User: {user_id}, IP: {source_ip}"
        extra_info = {"event_type": event_type.value}
        
        if security_level == SecurityLevel.CRITICAL:
            self.logger.critical(log_message, extra=extra_info)
        elif security_level == SecurityLevel.HIGH:
            self.logger.error(log_message, extra=extra_info)
        elif security_level == SecurityLevel.MEDIUM:
            self.logger.warning(log_message, extra=extra_info)
        else:
            self.logger.info(log_message, extra=extra_info)
    
    def log_authentication_success(self, user_id: str, auth_method: str, source_ip: str):
        """记录认证成功事件"""
        details = {
            "auth_method": auth_method,
            "result": "success"
        }
        self.log_security_event(
            SecurityEventType.AUTHENTICATION_SUCCESS,
            user_id,
            source_ip,
            details,
            SecurityLevel.LOW
        )
    
    def log_authentication_failure(self, user_id: str, auth_method: str, source_ip: str, reason: str):
        """记录认证失败事件"""
        details = {
            "auth_method": auth_method,
            "result": "failure",
            "reason": reason
        }
        self.log_security_event(
            SecurityEventType.AUTHENTICATION_FAILURE,
            user_id,
            source_ip,
            details,
            SecurityLevel.MEDIUM
        )
    
    def log_authorization_denied(self, user_id: str, resource: str, action: str, source_ip: str):
        """记录授权拒绝事件"""
        details = {
            "resource": resource,
            "action": action,
            "result": "denied"
        }
        self.log_security_event(
            SecurityEventType.AUTHORIZATION_DENIED,
            user_id,
            source_ip,
            details,
            SecurityLevel.HIGH
        )
    
    def log_intrusion_attempt(self, source_ip: str, attack_type: str, details: Dict[str, Any]):
        """记录入侵尝试"""
        intrusion_details = {
            "attack_type": attack_type,
            "details": details
        }
        self.log_security_event(
            SecurityEventType.INTRUSION_ATTEMPT,
            None,
            source_ip,
            intrusion_details,
            SecurityLevel.CRITICAL
        )
    
    def log_data_access(self, user_id: str, data_type: str, operation: str, record_id: Optional[str] = None):
        """记录数据访问事件"""
        details = {
            "data_type": data_type,
            "operation": operation,
            "record_id": record_id
        }
        self.log_security_event(
            SecurityEventType.DATA_ACCESS,
            user_id,
            None,
            details,
            SecurityLevel.LOW
        )
    
    def _generate_event_id(self, event_type: SecurityEventType, user_id: Optional[str], source_ip: Optional[str]) -> str:
        """生成唯一事件ID"""
        base_string = f"{event_type.value}_{user_id}_{source_ip}_{datetime.now().isoformat()}"
        return hashlib.md5(base_string.encode()).hexdigest()[:16]
    
    def _write_security_log(self, security_event: Dict[str, Any]):
        """写入安全日志文件"""
        import os
        log_file = f"{self.log_dir}/security_events.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(security_event, ensure_ascii=False) + '\n')
    
    def get_security_alerts(self, hours: int = 24) -> list:
        """获取最近的安全告警"""
        import os
        import glob
        from datetime import datetime, timedelta
        
        alerts = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 读取安全事件文件
        log_file = f"{self.log_dir}/security_events.jsonl"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event['timestamp'])
                        if event_time >= cutoff_time and event['security_level'] in ['HIGH', 'CRITICAL']:
                            alerts.append(event)
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        return alerts
    
    def analyze_threat_patterns(self) -> Dict[str, Any]:
        """分析威胁模式"""
        import os
        from collections import Counter
        
        if not os.path.exists(f"{self.log_dir}/security_events.jsonl"):
            return {}
        
        event_types = []
        source_ips = []
        
        with open(f"{self.log_dir}/security_events.jsonl", 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    event_types.append(event['event_type'])
                    if event.get('source_ip'):
                        source_ips.append(event['source_ip'])
                except (json.JSONDecodeError, KeyError):
                    continue
        
        analysis = {
            "total_events": len(event_types),
            "event_type_distribution": dict(Counter(event_types)),
            "suspicious_ips": [ip for ip, count in Counter(source_ips).items() if count > 10],
            "failed_attempts": event_types.count(SecurityEventType.AUTHENTICATION_FAILURE.value)
        }
        
        return analysis

# 全局安全日志实例
security_logger = SecurityLogger()

