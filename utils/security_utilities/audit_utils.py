"""
审计工具模块

提供安全审计、日志记录、监控等功能
"""

import logging
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """审计级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"


class AuditLogger:
    """审计日志器"""
    
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.DEBUG)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.audit_logger.addHandler(file_handler)
    
    def log_event(self, event_type: str, user_id: str, action: str, 
                  details: Dict[str, Any] = None, level: AuditLevel = AuditLevel.INFO) -> None:
        """记录审计事件"""
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'level': level.value,
            'hash': self._calculate_event_hash(event_type, user_id, action, details)
        }
        
        log_message = json.dumps(audit_entry, ensure_ascii=False)
        
        if level == AuditLevel.INFO:
            self.audit_logger.info(log_message)
        elif level == AuditLevel.WARNING:
            self.audit_logger.warning(log_message)
        elif level == AuditLevel.ERROR:
            self.audit_logger.error(log_message)
        elif level == AuditLevel.CRITICAL:
            self.audit_logger.critical(log_message)
        elif level == AuditLevel.SECURITY:
            self.audit_logger.critical(f"SECURITY: {log_message}")
    
    def _calculate_event_hash(self, event_type: str, user_id: str, 
                            action: str, details: Dict[str, Any]) -> str:
        """计算事件哈希"""
        event_string = f"{event_type}:{user_id}:{action}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(event_string.encode('utf-8')).hexdigest()[:16]


class SecurityAuditor:
    """安全审计器"""
    
    def __init__(self):
        self.audit_logger = AuditLogger()
        self.violations = []
    
    def audit_login_attempt(self, user_id: str, ip_address: str, 
                           success: bool, failure_reason: str = None) -> None:
        """审计登录尝试"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        details = {
            'ip_address': ip_address,
            'success': success,
            'failure_reason': failure_reason
        }
        
        self.audit_logger.log_event(
            'login_attempt', user_id, 'login', details, level
        )
    
    def audit_data_access(self, user_id: str, resource: str, 
                         action: str, success: bool) -> None:
        """审计数据访问"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        details = {
            'resource': resource,
            'action': action,
            'success': success
        }
        
        self.audit_logger.log_event(
            'data_access', user_id, action, details, level
        )
    
    def audit_permission_change(self, admin_user: str, target_user: str, 
                               permission: str, action: str) -> None:
        """审计权限变更"""
        details = {
            'target_user': target_user,
            'permission': permission,
            'action': action
        }
        
        self.audit_logger.log_event(
            'permission_change', admin_user, 'modify_permissions', 
            details, AuditLevel.SECURITY
        )
    
    def audit_system_change(self, user_id: str, change_type: str, 
                           details: Dict[str, Any]) -> None:
        """审计系统变更"""
        self.audit_logger.log_event(
            'system_change', user_id, change_type, 
            details, AuditLevel.SECURITY
        )
    
    def detect_suspicious_activity(self, user_id: str, activity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测可疑活动"""
        violations = []
        
        # 检测异常登录时间
        current_hour = datetime.now().hour
        if activity_data.get('login_time'):
            login_hour = activity_data['login_time'].hour
            if login_hour < 6 or login_hour > 22:  # 深夜登录
                violations.append({
                    'type': 'unusual_login_time',
                    'user_id': user_id,
                    'description': f'用户在异常时间 {login_hour}:00 登录',
                    'severity': 'medium'
                })
        
        # 检测多次失败登录
        failed_attempts = activity_data.get('failed_login_attempts', 0)
        if failed_attempts > 5:
            violations.append({
                'type': 'multiple_failed_logins',
                'user_id': user_id,
                'description': f'用户 {failed_attempts} 次登录失败',
                'severity': 'high'
            })
        
        # 检测异常访问模式
        access_count = activity_data.get('access_count', 0)
        if access_count > 100:  # 异常高频访问
            violations.append({
                'type': 'high_frequency_access',
                'user_id': user_id,
                'description': f'用户在短时间内访问 {access_count} 次',
                'severity': 'medium'
            })
        
        # 记录违规行为
        for violation in violations:
            self.audit_logger.log_event(
                'security_violation', user_id, violation['type'], 
                violation, AuditLevel.SECURITY
            )
        
        return violations
    
    def generate_audit_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """生成审计报告"""
        # 这里简化处理，实际应该从日志文件读取和分析数据
        report = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_events': 0,
                'security_events': 0,
                'violations': 0,
                'unique_users': 0
            },
            'event_breakdown': {},
            'top_violations': [],
            'recommendations': []
        }
        
        # 生成建议
        report['recommendations'] = [
            "加强用户身份验证机制",
            "实施更严格的访问控制",
            "增加实时监控和告警",
            "定期进行安全审计"
        ]
        
        return report


class ComplianceChecker:
    """合规性检查器"""
    
    def __init__(self):
        self.compliance_rules = {
            'gdpr': self._check_gdpr_compliance,
            'sox': self._check_sox_compliance,
            'pci_dss': self._check_pci_dss_compliance,
            'iso27001': self._check_iso27001_compliance
        }
    
    def check_compliance(self, standard: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """检查合规性"""
        if standard not in self.compliance_rules:
            return {
                'standard': standard,
                'compliant': False,
                'error': f'不支持的合规标准: {standard}'
            }
        
        checker_func = self.compliance_rules[standard]
        return checker_func(data)
    
    def _check_gdpr_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """检查GDPR合规性"""
        violations = []
        
        # 检查数据加密
        if not data.get('data_encrypted', False):
            violations.append('个人数据未加密存储')
        
        # 检查访问控制
        if not data.get('access_controls_implemented', False):
            violations.append('未实施适当的访问控制')
        
        # 检查数据保留策略
        if not data.get('data_retention_policy', False):
            violations.append('缺少数据保留策略')
        
        return {
            'standard': 'GDPR',
            'compliant': len(violations) == 0,
            'violations': violations,
            'compliance_score': max(0, 100 - len(violations) * 20)
        }
    
    def _check_sox_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """检查SOX合规性"""
        violations = []
        
        # 检查财务数据完整性
        if not data.get('financial_data_integrity', False):
            violations.append('财务数据完整性控制缺失')
        
        # 检查审计日志
        if not data.get('audit_logging_enabled', False):
            violations.append('未启用审计日志')
        
        # 检查访问权限管理
        if not data.get('access_rights_management', False):
            violations.append('访问权限管理不当')
        
        return {
            'standard': 'SOX',
            'compliant': len(violations) == 0,
            'violations': violations,
            'compliance_score': max(0, 100 - len(violations) * 25)
        }
    
    def _check_pci_dss_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """检查PCI DSS合规性"""
        violations = []
        
        # 检查信用卡数据加密
        if not data.get('card_data_encrypted', False):
            violations.append('信用卡数据未加密')
        
        # 检查网络安全
        if not data.get('network_security', False):
            violations.append('网络安全控制不足')
        
        # 检查访问监控
        if not data.get('access_monitoring', False):
            violations.append('访问监控不充分')
        
        return {
            'standard': 'PCI DSS',
            'compliant': len(violations) == 0,
            'violations': violations,
            'compliance_score': max(0, 100 - len(violations) * 30)
        }
    
    def _check_iso27001_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """检查ISO 27001合规性"""
        violations = []
        
        # 检查信息安全政策
        if not data.get('information_security_policy', False):
            violations.append('缺少信息安全政策')
        
        # 检查风险管理
        if not data.get('risk_management', False):
            violations.append('风险管理不充分')
        
        # 检查事件响应
        if not data.get('incident_response', False):
            violations.append('事件响应机制缺失')
        
        return {
            'standard': 'ISO 27001',
            'compliant': len(violations) == 0,
            'violations': violations,
            'compliance_score': max(0, 100 - len(violations) * 20)
        }


class AuditTrail:
    """审计跟踪"""
    
    def __init__(self):
        self.trail = []
    
    def add_entry(self, entry: Dict[str, Any]) -> None:
        """添加审计条目"""
        entry['timestamp'] = datetime.now().isoformat()
        entry['id'] = len(self.trail) + 1
        self.trail.append(entry)
    
    def get_user_activity(self, user_id: str, start_date: datetime = None, 
                         end_date: datetime = None) -> List[Dict[str, Any]]:
        """获取用户活动"""
        user_activities = [entry for entry in self.trail if entry.get('user_id') == user_id]
        
        if start_date:
            user_activities = [entry for entry in user_activities 
                             if datetime.fromisoformat(entry['timestamp']) >= start_date]
        
        if end_date:
            user_activities = [entry for entry in user_activities 
                             if datetime.fromisoformat(entry['timestamp']) <= end_date]
        
        return user_activities
    
    def get_system_changes(self, start_date: datetime = None, 
                          end_date: datetime = None) -> List[Dict[str, Any]]:
        """获取系统变更"""
        system_changes = [entry for entry in self.trail if entry.get('event_type') == 'system_change']
        
        if start_date:
            system_changes = [entry for entry in system_changes 
                            if datetime.fromisoformat(entry['timestamp']) >= start_date]
        
        if end_date:
            system_changes = [entry for entry in system_changes 
                            if datetime.fromisoformat(entry['timestamp']) <= end_date]
        
        return system_changes
    
    def search_audit_trail(self, query: str) -> List[Dict[str, Any]]:
        """搜索审计跟踪"""
        results = []
        query_lower = query.lower()
        
        for entry in self.trail:
            # 搜索所有字段
            entry_str = json.dumps(entry, ensure_ascii=False).lower()
            if query_lower in entry_str:
                results.append(entry)
        
        return results
    
    def export_audit_data(self, format_type: str = 'json') -> str:
        """导出审计数据"""
        if format_type.lower() == 'json':
            return json.dumps(self.trail, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format_type}")


if __name__ == "__main__":
    print("审计工具模块")
    
    # 创建审计器
    auditor = SecurityAuditor()
    
    # 审计登录尝试
    auditor.audit_login_attempt('user123', '192.168.1.100', True)
    auditor.audit_login_attempt('user456', '10.0.0.50', False, 'Invalid password')
    
    # 审计数据访问
    auditor.audit_data_access('user123', '/api/users', 'read', True)
    auditor.audit_data_access('user456', '/api/admin', 'delete', False)
    
    # 审计权限变更
    auditor.audit_permission_change('admin', 'user123', 'admin', 'grant')
    
    # 审计系统变更
    auditor.audit_system_change('admin', 'config_change', {
        'config_file': '/etc/app.conf',
        'changes': ['updated_timeout', 'added_feature_x']
    })
    
    # 检测可疑活动
    suspicious_activity = {
        'login_time': datetime.now().replace(hour=2),  # 深夜登录
        'failed_login_attempts': 7,
        'access_count': 150
    }
    
    violations = auditor.detect_suspicious_activity('user789', suspicious_activity)
    print(f"检测到 {len(violations)} 个可疑活动")
    
    # 合规性检查
    compliance_checker = ComplianceChecker()
    
    gdpr_data = {
        'data_encrypted': True,
        'access_controls_implemented': True,
        'data_retention_policy': False
    }
    
    gdpr_result = compliance_checker.check_compliance('gdpr', gdpr_data)
    print(f"GDPR合规性: {'合规' if gdpr_result['compliant'] else '不合规'}")
    
    # 审计跟踪
    trail = AuditTrail()
    trail.add_entry({
        'user_id': 'user123',
        'action': 'login',
        'ip_address': '192.168.1.100',
        'success': True
    })
    
    trail.add_entry({
        'user_id': 'user123',
        'action': 'access_file',
        'resource': '/data/report.pdf',
        'success': True
    })
    
    # 获取用户活动
    user_activities = trail.get_user_activity('user123')
    print(f"用户活动记录: {len(user_activities)} 条")
    
    # 搜索审计跟踪
    search_results = trail.search_audit_trail('login')
    print(f"搜索结果: {len(search_results)} 条")
    
    # 生成审计报告
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    
    report = auditor.generate_audit_report(start_date, end_date)
    print(f"审计报告生成完成")
    
    print("审计工具示例完成")