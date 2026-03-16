"""
审计日志模块 - 记录审计信息
负责记录系统操作审计、合规性检查等审计信息
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

class AuditAction(Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    ACCESS = "ACCESS"
    MODIFY = "MODIFY"
    APPROVE = "APPROVE"
    REJECT = "REJECT"

class AuditResource(Enum):
    USER_DATA = "user_data"
    SYSTEM_CONFIG = "system_config"
    AI_MODEL = "ai_model"
    DATABASE = "database"
    NETWORK = "network"
    SECURITY = "security"
    FINANCIAL = "financial"
    DOCUMENT = "document"

class AuditStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"
    REVOKED = "REVOKED"

class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = log_dir
        self._setup_logging()
    
    def _setup_logging(self):
        """配置审计日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 审计日志记录器
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 审计日志文件处理器
        log_file = f"{self.log_dir}/audit.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # 审计专用格式
        formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(user_id)s - %(action)s - %(resource)s - %(status)s - %(audit_id)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def log_audit_event(self,
                       user_id: str,
                       action: AuditAction,
                       resource: AuditResource,
                       resource_id: Optional[str],
                       status: AuditStatus,
                       details: Dict[str, Any],
                       justification: Optional[str] = None) -> str:
        """记录审计事件"""
        
        audit_id = self._generate_audit_id(user_id, action, resource, resource_id)
        timestamp = datetime.now()
        
        audit_record = {
            "audit_id": audit_id,
            "timestamp": timestamp.isoformat(),
            "user_id": user_id,
            "action": action.value,
            "resource": resource.value,
            "resource_id": resource_id,
            "status": status.value,
            "details": details,
            "justification": justification,
            "checksum": self._calculate_checksum(user_id, action, resource, resource_id, details)
        }
        
        # 写入结构化审计日志
        self._write_audit_log(audit_record)
        
        # 记录到文本日志
        log_message = f"用户 {user_id} 执行 {action.value} 操作于 {resource.value}"
        if resource_id:
            log_message += f" ({resource_id})"
        log_message += f" - 状态: {status.value}"
        
        extra_info = {
            "user_id": user_id,
            "action": action.value,
            "resource": resource.value,
            "status": status.value,
            "audit_id": audit_id
        }
        
        if status == AuditStatus.SUCCESS:
            self.logger.info(log_message, extra=extra_info)
        else:
            self.logger.warning(log_message, extra=extra_info)
        
        return audit_id
    
    def log_data_access(self,
                       user_id: str,
                       resource: AuditResource,
                       resource_id: str,
                       data_sensitivity: str,
                       access_reason: str) -> str:
        """记录数据访问事件"""
        details = {
            "data_sensitivity": data_sensitivity,
            "access_reason": access_reason,
            "access_type": "data_retrieval"
        }
        
        return self.log_audit_event(
            user_id,
            AuditAction.ACCESS,
            resource,
            resource_id,
            AuditStatus.SUCCESS,
            details,
            access_reason
        )
    
    def log_configuration_change(self,
                                user_id: str,
                                config_item: str,
                                old_value: Any,
                                new_value: Any,
                                change_reason: str) -> str:
        """记录配置变更事件"""
        details = {
            "config_item": config_item,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "change_type": "configuration_update"
        }
        
        return self.log_audit_event(
            user_id,
            AuditAction.MODIFY,
            AuditResource.SYSTEM_CONFIG,
            config_item,
            AuditStatus.SUCCESS,
            details,
            change_reason
        )
    
    def log_security_event(self,
                          user_id: str,
                          action: AuditAction,
                          resource: AuditResource,
                          security_level: str,
                          event_details: Dict[str, Any]) -> str:
        """记录安全审计事件"""
        details = {
            "security_level": security_level,
            "event_type": "security_audit",
            **event_details
        }
        
        return self.log_audit_event(
            user_id,
            action,
            resource,
            None,
            AuditStatus.SUCCESS,
            details,
            "安全策略执行"
        )
    
    def log_compliance_check(self,
                           check_type: str,
                           standard: str,
                           result: str,
                           details: Dict[str, Any]) -> str:
        """记录合规性检查"""
        compliance_record = {
            "check_id": self._generate_compliance_id(),
            "timestamp": datetime.now().isoformat(),
            "check_type": check_type,
            "standard": standard,
            "result": result,
            "details": details,
            "auditor": "system"  # 系统自动执行
        }
        
        self._write_compliance_log(compliance_record)
        
        # 记录到审计日志
        log_message = f"合规检查: {check_type} - 标准: {standard} - 结果: {result}"
        extra_info = {
            "user_id": "system",
            "action": "EXECUTE",
            "resource": "compliance",
            "status": AuditStatus.SUCCESS,
            "audit_id": compliance_record["check_id"]
        }
        self.logger.info(log_message, extra=extra_info)
        
        return compliance_record["check_id"]
    
    def log_user_consent(self,
                        user_id: str,
                        consent_type: str,
                        granted: bool,
                        version: str,
                        terms: Dict[str, Any]) -> str:
        """记录用户同意事件"""
        details = {
            "consent_type": consent_type,
            "granted": granted,
            "version": version,
            "terms_accepted": terms
        }
        
        return self.log_audit_event(
            user_id,
            AuditAction.APPROVE if granted else AuditAction.REJECT,
            AuditResource.USER_DATA,
            "consent",
            AuditStatus.SUCCESS,
            details,
            "用户同意管理"
        )
    
    def _generate_audit_id(self, 
                          user_id: str, 
                          action: AuditAction, 
                          resource: AuditResource, 
                          resource_id: Optional[str]) -> str:
        """生成审计ID"""
        base_string = f"{user_id}_{action.value}_{resource.value}_{resource_id}_{datetime.now().isoformat()}"
        return hashlib.sha256(base_string.encode()).hexdigest()[:16].upper()
    
    def _generate_compliance_id(self) -> str:
        """生成合规检查ID"""
        base_string = f"compliance_{datetime.now().isoformat()}_{id(self)}"
        return hashlib.md5(base_string.encode()).hexdigest()[:12].upper()
    
    def _calculate_checksum(self,
                           user_id: str,
                           action: AuditAction,
                           resource: AuditResource,
                           resource_id: Optional[str],
                           details: Dict[str, Any]) -> str:
        """计算审计记录校验和"""
        data_string = f"{user_id}{action.value}{resource.value}{resource_id}{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _write_audit_log(self, audit_record: Dict[str, Any]):
        """写入审计日志文件"""
        import os
        log_file = f"{self.log_dir}/audit_trail.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_record, ensure_ascii=False) + '\n')
    
    def _write_compliance_log(self, compliance_record: Dict[str, Any]):
        """写入合规日志文件"""
        import os
        log_file = f"{self.log_dir}/compliance_checks.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(compliance_record, ensure_ascii=False) + '\n')
    
    def verify_audit_integrity(self, audit_id: str) -> bool:
        """验证审计记录完整性"""
        import os
        
        log_file = f"{self.log_dir}/audit_trail.jsonl"
        if not os.path.exists(log_file):
            return False
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    if record.get('audit_id') == audit_id:
                        # 重新计算校验和
                        expected_checksum = self._calculate_checksum(
                            record['user_id'],
                            AuditAction(record['action']),
                            AuditResource(record['resource']),
                            record.get('resource_id'),
                            record['details']
                        )
                        return record.get('checksum') == expected_checksum
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        return False
    
    def get_user_activity_report(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """获取用户活动报告"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        user_activities = self._get_audit_records(user_id=user_id, start_time=cutoff_time)
        
        actions = [activity['action'] for activity in user_activities]
        resources = [activity['resource'] for activity in user_activities]
        
        report = {
            "user_id": user_id,
            "report_period": f"最近{days}天",
            "total_activities": len(user_activities),
            "action_distribution": dict(zip(*np.unique(actions, return_counts=True))),
            "resource_distribution": dict(zip(*np.unique(resources, return_counts=True))),
            "recent_activities": user_activities[:10]  # 最近10条活动
        }
        
        return report
    
    def generate_compliance_report(self, standard: str, period_days: int = 90) -> Dict[str, Any]:
        """生成合规性报告"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=period_days)
        compliance_checks = self._get_compliance_records(standard=standard, start_time=cutoff_time)
        
        if not compliance_checks:
            return {"error": f"未找到{standard}标准的合规检查记录"}
        
        passed_checks = [check for check in compliance_checks if check['result'] == 'PASS']
        failed_checks = [check for check in compliance_checks if check['result'] == 'FAIL']
        
        report = {
            "standard": standard,
            "report_period": f"最近{period_days}天",
            "total_checks": len(compliance_checks),
            "passed_checks": len(passed_checks),
            "failed_checks": len(failed_checks),
            "compliance_rate": len(passed_checks) / len(compliance_checks) * 100,
            "recent_failures": failed_checks[:5],
            "recommendations": self._generate_compliance_recommendations(failed_checks)
        }
        
        return report
    
    def _get_audit_records(self, 
                          user_id: Optional[str] = None,
                          start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取审计记录"""
        import os
        
        records = []
        log_file = f"{self.log_dir}/audit_trail.jsonl"
        if not os.path.exists(log_file):
            return records
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    record_time = datetime.fromisoformat(record['timestamp'])
                    
                    # 应用过滤器
                    if user_id and record['user_id'] != user_id:
                        continue
                    if start_time and record_time < start_time:
                        continue
                    
                    records.append(record)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # 按时间倒序排列
        records.sort(key=lambda x: x['timestamp'], reverse=True)
        return records
    
    def _get_compliance_records(self,
                               standard: Optional[str] = None,
                               start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取合规检查记录"""
        import os
        
        records = []
        log_file = f"{self.log_dir}/compliance_checks.jsonl"
        if not os.path.exists(log_file):
            return records
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    record_time = datetime.fromisoformat(record['timestamp'])
                    
                    # 应用过滤器
                    if standard and record['standard'] != standard:
                        continue
                    if start_time and record_time < start_time:
                        continue
                    
                    records.append(record)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        records.sort(key=lambda x: x['timestamp'], reverse=True)
        return records
    
    def _generate_compliance_recommendations(self, failed_checks: List[Dict[str, Any]]) -> List[str]:
        """生成合规改进建议"""
        recommendations = []
        
        gdpr_failures = [check for check in failed_checks if 'GDPR' in check['standard']]
        if gdpr_failures:
            recommendations.append("发现GDPR合规问题，建议检查数据保护措施和用户同意管理")
        
        security_failures = [check for check in failed_checks if '安全' in check['check_type'] or 'security' in check['check_type'].lower()]
        if security_failures:
            recommendations.append("存在安全检查失败，建议加强访问控制和加密措施")
        
        data_failures = [check for check in failed_checks if '数据' in check['check_type'] or 'data' in check['check_type'].lower()]
        if data_failures:
            recommendations.append("数据管理合规性需要改进，建议完善数据备份和恢复策略")
        
        return recommendations

# 全局审计日志实例
audit_logger = AuditLogger()
