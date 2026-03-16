"""
安全智能体模块：处理安全相关任务
实现基于威胁检测和风险评估的安全监控系统
"""

import uuid
import datetime
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from enum import Enum

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    MALWARE = "malware"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_LEAK = "data_leak"
    NETWORK_ATTACK = "network_attack"
    SOCIAL_ENGINEERING = "social_engineering"

class SecurityAgent:
    """安全智能体 - 处理安全相关任务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 智能体身份
        self.agent_id = self.config.get('agent_id', f"security_agent_{uuid.uuid4().hex[:8]}")
        self.agent_type = "security"
        
        # 安全配置
        self.security_level = SecurityLevel(self.config.get('security_level', 'high'))
        self.monitoring_enabled = self.config.get('monitoring_enabled', True)
        self.auto_response_enabled = self.config.get('auto_response_enabled', True)
        
        # 威胁情报
        self.threat_intelligence = self._load_threat_intelligence()
        self.security_rules = self._load_security_rules()
        self.whitelist = self.config.get('whitelist', [])
        self.blacklist = self.config.get('blacklist', [])
        
        # 监控状态
        self.current_tasks = set()
        self.security_events = []
        self.incident_log = []
        self.performance_metrics = {
            'threats_detected': 0,
            'incidents_handled': 0,
            'false_positives': 0,
            'response_times': [],
            'system_health': 'secure'
        }
        
        # 安全工具
        self._initialize_security_tools()
        
        # 启动监控
        if self.monitoring_enabled:
            self._start_security_monitoring()
        
        self.initialized = True
        self.logger.info(f"安全智能体初始化成功: {self.agent_id}")
    
    def _load_threat_intelligence(self) -> Dict[str, Any]:
        """加载威胁情报"""
        return {
            'malware_signatures': [
                'malicious_script',
                'suspicious_process',
                'unauthorized_modification'
            ],
            'suspicious_patterns': [
                r'password\s*=\s*[\'\"][^\'\"]+[\'\"]',  # 硬编码密码
                r'eval\([^)]+\)',  # eval函数使用
                r'exec\([^)]+\)',  # exec函数使用
                r'base64_decode\([^)]+\)'  # base64解码
            ],
            'network_threats': [
                'port_scanning',
                'brute_force_attempt',
                'ddos_attack',
                'sql_injection'
            ],
            'behavioral_anomalies': [
                'unusual_file_access',
                'privilege_escalation',
                'data_exfiltration',
                'system_modification'
            ]
        }
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """加载安全规则"""
        return {
            'access_control': {
                'max_login_attempts': 5,
                'session_timeout': 1800,  # 30分钟
                'password_complexity': True
            },
            'network_security': {
                'block_suspicious_ips': True,
                'monitor_open_ports': True,
                'detect_anomalous_traffic': True
            },
            'data_protection': {
                'encrypt_sensitive_data': True,
                'mask_personal_info': True,
                'log_data_access': True
            },
            'system_hardening': {
                'disable_unused_services': True,
                'regular_updates': True,
                'file_integrity_checking': True
            }
        }
    
    def _initialize_security_tools(self):
        """初始化安全工具"""
        try:
            # 初始化哈希数据库用于文件完整性检查
            self.file_hashes = {}
            
            # 初始化行为分析器
            self.behavior_analyzer = self._create_behavior_analyzer()
            
            # 初始化威胁评估器
            self.threat_assessor = self._create_threat_assessor()
            
            self.logger.info("安全工具初始化完成")
            
        except Exception as e:
            self.logger.error(f"安全工具初始化失败: {e}")
    
    def _create_behavior_analyzer(self):
        """创建行为分析器"""
        return {
            'baseline_established': False,
            'normal_patterns': {},
            'anomaly_detection_enabled': True,
            'learning_mode': True
        }
    
    def _create_threat_assessor(self):
        """创建威胁评估器"""
        return {
            'risk_calculator': True,
            'impact_assessment': True,
            'response_planner': True
        }
    
    def _start_security_monitoring(self):
        """启动安全监控"""
        self.logger.info("安全监控已启动")
        # 在实际系统中，这里会启动各种监控线程和服务
    
    async def monitor_security(self,
                            task_id: str,
                            monitoring_target: str,
                            monitoring_type: str) -> Dict[str, Any]:
        """
        安全监控
        
        Args:
            task_id: 任务ID
            monitoring_target: 监控目标
            monitoring_type: 监控类型
            
        Returns:
            监控结果
        """
        try:
            self.current_tasks.add(task_id)
            
            monitoring_result = {
                'task_id': task_id,
                'monitoring_target': monitoring_target,
                'monitoring_type': monitoring_type,
                'timestamp': datetime.datetime.now().isoformat(),
                'findings': [],
                'threats_detected': 0,
                'recommendations': []
            }
            
            if monitoring_type == 'file_system':
                result = await self._monitor_file_system(monitoring_target)
            elif monitoring_type == 'network':
                result = await self._monitor_network(monitoring_target)
            elif monitoring_type == 'system_activity':
                result = await self._monitor_system_activity(monitoring_target)
            elif monitoring_type == 'user_behavior':
                result = await self._monitor_user_behavior(monitoring_target)
            else:
                result = {'success': False, 'error': f'不支持的监控类型: {monitoring_type}'}
            
            monitoring_result.update(result)
            
            # 记录安全事件
            if monitoring_result['threats_detected'] > 0:
                security_event = {
                    'event_id': str(uuid.uuid4()),
                    'task_id': task_id,
                    'type': 'threat_detection',
                    'monitoring_type': monitoring_type,
                    'threat_count': monitoring_result['threats_detected'],
                    'timestamp': datetime.datetime.now().isoformat(),
                    'details': monitoring_result
                }
                self.security_events.append(security_event)
                
                # 自动响应（如果启用）
                if self.auto_response_enabled:
                    response_result = await self._auto_respond_to_threats(monitoring_result)
                    monitoring_result['auto_response'] = response_result
            
            # 更新性能指标
            self.performance_metrics['threats_detected'] += monitoring_result['threats_detected']
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'monitoring_result': monitoring_result
            }
            
        except Exception as e:
            self.logger.error(f"安全监控失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _monitor_file_system(self, target_path: str) -> Dict[str, Any]:
        """监控文件系统"""
        findings = []
        threats_detected = 0
        
        try:
            # 检查文件完整性
            integrity_check = await self._check_file_integrity(target_path)
            findings.extend(integrity_check['findings'])
            threats_detected += integrity_check['threats_detected']
            
            # 检查可疑文件
            suspicious_files = await self._scan_for_suspicious_files(target_path)
            findings.extend(suspicious_files['findings'])
            threats_detected += suspicious_files['threats_detected']
            
            # 检查权限设置
            permission_check = await self._check_file_permissions(target_path)
            findings.extend(permission_check['findings'])
            
            return {
                'findings': findings,
                'threats_detected': threats_detected,
                'recommendations': self._generate_file_security_recommendations(findings)
            }
            
        except Exception as e:
            self.logger.error(f"文件系统监控失败: {e}")
            return {
                'findings': [{'level': 'error', 'message': f'监控失败: {e}'}],
                'threats_detected': 0,
                'recommendations': ['检查监控目标路径的有效性']
            }
    
    async def _check_file_integrity(self, target_path: str) -> Dict[str, Any]:
        """检查文件完整性"""
        findings = []
        threats_detected = 0
        
        # 模拟文件完整性检查
        # 在实际系统中，这里会计算文件哈希并与已知安全哈希比较
        
        sample_files = [
            {'path': '/etc/passwd', 'status': 'modified', 'risk': 'high'},
            {'path': '/bin/bash', 'status': 'unchanged', 'risk': 'low'},
            {'path': '/tmp/suspicious_file', 'status': 'new', 'risk': 'medium'}
        ]
        
        for file_info in sample_files:
            if file_info['status'] != 'unchanged':
                finding = {
                    'level': 'warning' if file_info['risk'] == 'medium' else 'high',
                    'message': f"文件完整性异常: {file_info['path']} - {file_info['status']}",
                    'file_path': file_info['path'],
                    'risk_level': file_info['risk']
                }
                findings.append(finding)
                
                if file_info['risk'] in ['high', 'medium']:
                    threats_detected += 1
        
        return {
            'findings': findings,
            'threats_detected': threats_detected
        }
    
    async def _scan_for_suspicious_files(self, target_path: str) -> Dict[str, Any]:
        """扫描可疑文件"""
        findings = []
        threats_detected = 0
        
        # 模拟可疑文件扫描
        suspicious_patterns = self.threat_intelligence['suspicious_patterns']
        
        sample_suspicious_files = [
            {'path': '/tmp/malicious_script.py', 'content': 'eval("malicious code")'},
            {'path': '/var/log/.hidden_file', 'content': 'sensitive_data'},
            {'path': '/home/user/.ssh/unknown_key', 'content': 'ssh_private_key'}
        ]
        
        for file_info in sample_suspicious_files:
            for pattern in suspicious_patterns:
                if re.search(pattern, file_info['content']):
                    finding = {
                        'level': 'high',
                        'message': f"检测到可疑文件: {file_info['path']}",
                        'file_path': file_info['path'],
                        'matched_pattern': pattern,
                        'risk_level': 'high'
                    }
                    findings.append(finding)
                    threats_detected += 1
                    break
        
        return {
            'findings': findings,
            'threats_detected': threats_detected
        }
    
    async def _check_file_permissions(self, target_path: str) -> Dict[str, Any]:
        """检查文件权限"""
        findings = []
        
        # 模拟权限检查
        permission_issues = [
            {'path': '/etc/shadow', 'permission': 'rw-r--r--', 'recommended': 'rw-------', 'risk': 'high'},
            {'path': '/tmp/public_file', 'permission': 'rw-rw-rw-', 'recommended': 'rw-r--r--', 'risk': 'medium'},
            {'path': '/home/user/script.sh', 'permission': 'rwxrwxrwx', 'recommended': 'rwxr-xr-x', 'risk': 'medium'}
        ]
        
        for issue in permission_issues:
            finding = {
                'level': 'medium' if issue['risk'] == 'medium' else 'high',
                'message': f"文件权限问题: {issue['path']} - 当前: {issue['permission']}, 推荐: {issue['recommended']}",
                'file_path': issue['path'],
                'current_permission': issue['permission'],
                'recommended_permission': issue['recommended'],
                'risk_level': issue['risk']
            }
            findings.append(finding)
        
        return {
            'findings': findings,
            'threats_detected': 0  # 权限问题不算直接威胁
        }
    
    def _generate_file_security_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """生成文件安全建议"""
        recommendations = []
        
        high_risk_findings = [f for f in findings if f.get('risk_level') == 'high']
        medium_risk_findings = [f for f in findings if f.get('risk_level') == 'medium']
        
        if high_risk_findings:
            recommendations.append("立即处理高风险文件安全问题")
        
        if medium_risk_findings:
            recommendations.append("审查并修复中等风险文件权限问题")
        
        if any('suspicious' in f.get('message', '') for f in findings):
            recommendations.append("隔离并分析可疑文件")
        
        if not recommendations:
            recommendations.append("文件系统安全状态良好，继续保持")
        
        return recommendations
    
    async def _monitor_network(self, target: str) -> Dict[str, Any]:
        """监控网络"""
        findings = []
        threats_detected = 0
        
        try:
            # 模拟网络监控
            network_activities = [
                {'type': 'suspicious_connection', 'source': '192.168.1.100', 'destination': 'external_ip', 'port': 4444, 'risk': 'high'},
                {'type': 'port_scan', 'source': '10.0.0.50', 'ports': '22,80,443,3389', 'risk': 'medium'},
                {'type': 'unusual_traffic', 'source': 'internal', 'protocol': 'DNS', 'volume': 'high', 'risk': 'medium'}
            ]
            
            for activity in network_activities:
                finding = {
                    'level': 'high' if activity['risk'] == 'high' else 'medium',
                    'message': f"检测到{activity['type']}: {activity.get('source', '未知')}",
                    'activity_type': activity['type'],
                    'risk_level': activity['risk'],
                    'details': activity
                }
                findings.append(finding)
                
                if activity['risk'] in ['high', 'medium']:
                    threats_detected += 1
            
            return {
                'findings': findings,
                'threats_detected': threats_detected,
                'recommendations': self._generate_network_security_recommendations(findings)
            }
            
        except Exception as e:
            self.logger.error(f"网络监控失败: {e}")
            return {
                'findings': [{'level': 'error', 'message': f'网络监控失败: {e}'}],
                'threats_detected': 0,
                'recommendations': ['检查网络监控配置']
            }
    
    def _generate_network_security_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """生成网络安全建议"""
        recommendations = []
        
        suspicious_connections = [f for f in findings if f.get('activity_type') == 'suspicious_connection']
        port_scans = [f for f in findings if f.get('activity_type') == 'port_scan']
        
        if suspicious_connections:
            recommendations.append("阻止可疑的外部连接")
            recommendations.append("审查相关主机的安全状态")
        
        if port_scans:
            recommendations.append("加强防火墙规则，限制端口扫描")
            recommendations.append("监控源IP的进一步活动")
        
        if any(f.get('risk_level') == 'high' for f in findings):
            recommendations.append("立即启动应急响应流程")
        
        if not recommendations:
            recommendations.append("网络活动正常，继续保持监控")
        
        return recommendations
    
    async def _monitor_system_activity(self, target: str) -> Dict[str, Any]:
        """监控系统活动"""
        findings = []
        threats_detected = 0
        
        try:
            # 模拟系统活动监控
            system_activities = [
                {'type': 'unusual_process', 'process': 'suspicious_daemon', 'user': 'root', 'risk': 'high'},
                {'type': 'privilege_escalation', 'user': 'normal_user', 'target': 'root', 'risk': 'high'},
                {'type': 'resource_abuse', 'process': 'crypto_miner', 'cpu_usage': '95%', 'risk': 'medium'}
            ]
            
            for activity in system_activities:
                finding = {
                    'level': 'high' if activity['risk'] == 'high' else 'medium',
                    'message': f"检测到{activity['type']}: {activity.get('process', '未知进程')}",
                    'activity_type': activity['type'],
                    'risk_level': activity['risk'],
                    'details': activity
                }
                findings.append(finding)
                
                if activity['risk'] in ['high', 'medium']:
                    threats_detected += 1
            
            return {
                'findings': findings,
                'threats_detected': threats_detected,
                'recommendations': self._generate_system_security_recommendations(findings)
            }
            
        except Exception as e:
            self.logger.error(f"系统活动监控失败: {e}")
            return {
                'findings': [{'level': 'error', 'message': f'系统活动监控失败: {e}'}],
                'threats_detected': 0,
                'recommendations': ['检查系统监控工具']
            }
    
    def _generate_system_security_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """生成系统安全建议"""
        recommendations = []
        
        unusual_processes = [f for f in findings if f.get('activity_type') == 'unusual_process']
        privilege_escalations = [f for f in findings if f.get('activity_type') == 'privilege_escalation']
        
        if unusual_processes:
            recommendations.append("终止可疑进程并进行分析")
            recommendations.append("审查进程启动点和权限")
        
        if privilege_escalations:
            recommendations.append("立即调查权限提升事件")
            recommendations.append("审查系统漏洞和配置")
        
        if any(f.get('risk_level') == 'high' for f in findings):
            recommendations.append("启动系统级安全响应")
        
        return recommendations
    
    async def _monitor_user_behavior(self, target: str) -> Dict[str, Any]:
        """监控用户行为"""
        findings = []
        threats_detected = 0
        
        try:
            # 模拟用户行为监控
            user_behaviors = [
                {'user': 'alice', 'behavior': 'unusual_login_time', 'time': '03:00', 'risk': 'medium'},
                {'user': 'bob', 'behavior': 'multiple_failed_logins', 'attempts': 8, 'risk': 'high'},
                {'user': 'charlie', 'behavior': 'access_sensitive_data', 'files': ['/etc/shadow'], 'risk': 'high'}
            ]
            
            for behavior in user_behaviors:
                finding = {
                    'level': 'high' if behavior['risk'] == 'high' else 'medium',
                    'message': f"检测到用户异常行为: {behavior['user']} - {behavior['behavior']}",
                    'user': behavior['user'],
                    'behavior_type': behavior['behavior'],
                    'risk_level': behavior['risk'],
                    'details': behavior
                }
                findings.append(finding)
                
                if behavior['risk'] in ['high', 'medium']:
                    threats_detected += 1
            
            return {
                'findings': findings,
                'threats_detected': threats_detected,
                'recommendations': self._generate_user_security_recommendations(findings)
            }
            
        except Exception as e:
            self.logger.error(f"用户行为监控失败: {e}")
            return {
                'findings': [{'level': 'error', 'message': f'用户行为监控失败: {e}'}],
                'threats_detected': 0,
                'recommendations': ['检查用户行为分析配置']
            }
    
    def _generate_user_security_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """生成用户安全建议"""
        recommendations = []
        
        failed_logins = [f for f in findings if 'failed_logins' in f.get('behavior_type', '')]
        sensitive_access = [f for f in findings if 'sensitive_data' in f.get('behavior_type', '')]
        
        if failed_logins:
            recommendations.append("检查账户安全状态，考虑临时锁定")
            recommendations.append("审查登录尝试来源")
        
        if sensitive_access:
            recommendations.append("审查用户权限和访问需求")
            recommendations.append("加强敏感数据访问控制")
        
        if any(f.get('risk_level') == 'high' for f in findings):
            recommendations.append("立即进行用户账户安全审查")
        
        return recommendations
    
    async def _auto_respond_to_threats(self, monitoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """自动响应威胁"""
        response_actions = []
        
        high_risk_findings = [f for f in monitoring_result['findings'] if f.get('risk_level') == 'high']
        
        for finding in high_risk_findings:
            action = self._determine_response_action(finding)
            if action:
                response_actions.append(action)
        
        # 执行响应动作（模拟）
        executed_actions = []
        for action in response_actions:
            executed_actions.append({
                'action_type': action['type'],
                'target': action.get('target'),
                'status': 'executed',
                'timestamp': datetime.datetime.now().isoformat()
            })
        
        return {
            'actions_taken': executed_actions,
            'threats_mitigated': len(executed_actions),
            'response_level': 'automatic'
        }
    
    def _determine_response_action(self, finding: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """确定响应动作"""
        finding_type = finding.get('activity_type', '')
        
        if 'suspicious_connection' in finding_type:
            return {
                'type': 'block_ip',
                'target': finding.get('details', {}).get('source'),
                'reason': '可疑网络连接'
            }
        elif 'unusual_process' in finding_type:
            return {
                'type': 'terminate_process',
                'target': finding.get('details', {}).get('process'),
                'reason': '可疑系统进程'
            }
        elif 'multiple_failed_logins' in finding_type:
            return {
                'type': 'lock_account',
                'target': finding.get('user'),
                'reason': '多次登录失败'
            }
        
        return None
    
    async def assess_security_risk(self,
                                task_id: str,
                                target_system: str,
                                assessment_scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估安全风险
        
        Args:
            task_id: 任务ID
            target_system: 目标系统
            assessment_scope: 评估范围
            
        Returns:
            风险评估结果
        """
        try:
            self.current_tasks.add(task_id)
            
            # 执行风险评估
            risk_assessment = await self._perform_risk_assessment(target_system, assessment_scope)
            
            # 生成风险报告
            risk_report = self._generate_risk_report(risk_assessment)
            
            # 记录安全事件
            security_event = {
                'event_id': str(uuid.uuid4()),
                'task_id': task_id,
                'type': 'risk_assessment',
                'target_system': target_system,
                'risk_level': risk_assessment['overall_risk_level'],
                'timestamp': datetime.datetime.now().isoformat(),
                'details': risk_assessment
            }
            self.security_events.append(security_event)
            
            # 更新性能指标
            self.performance_metrics['incidents_handled'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'risk_assessment': risk_assessment,
                'risk_report': risk_report
            }
            
        except Exception as e:
            self.logger.error(f"安全风险评估失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _perform_risk_assessment(self, target_system: str, scope: Dict[str, Any]) -> Dict[str, Any]:
        """执行风险评估"""
        # 模拟风险评估
        risk_factors = [
            {'factor': 'network_exposure', 'score': 0.7, 'weight': 0.3},
            {'factor': 'system_complexity', 'score': 0.5, 'weight': 0.2},
            {'factor': 'data_sensitivity', 'score': 0.8, 'weight': 0.25},
            {'factor': 'access_controls', 'score': 0.6, 'weight': 0.15},
            {'factor': 'update_status', 'score': 0.4, 'weight': 0.1}
        ]
        
        # 计算加权风险分数
        total_score = 0
        total_weight = 0
        
        for factor in risk_factors:
            total_score += factor['score'] * factor['weight']
            total_weight += factor['weight']
        
        overall_score = total_score / total_weight if total_weight > 0 else 0
        
        # 确定风险等级
        if overall_score >= 0.8:
            risk_level = 'critical'
        elif overall_score >= 0.6:
            risk_level = 'high'
        elif overall_score >= 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'target_system': target_system,
            'assessment_scope': scope,
            'risk_factors': risk_factors,
            'overall_risk_score': overall_score,
            'overall_risk_level': risk_level,
            'assessment_date': datetime.datetime.now().isoformat()
        }
    
    def _generate_risk_report(self, risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """生成风险报告"""
        risk_level = risk_assessment['overall_risk_level']
        
        # 基于风险等级生成建议
        if risk_level == 'critical':
            recommendations = [
                "立即采取纠正措施",
                "考虑系统隔离",
                "启动应急响应计划",
                "通知相关利益相关者"
            ]
            urgency = "immediate"
        elif risk_level == 'high':
            recommendations = [
                "优先处理高风险问题",
                "加强监控和日志记录",
                "审查访问控制策略",
                "制定缓解计划"
            ]
            urgency = "high"
        elif risk_level == 'medium':
            recommendations = [
                "制定改进计划",
                "定期安全审查",
                "员工安全意识培训",
                "系统强化"
            ]
            urgency = "medium"
        else:
            recommendations = [
                "继续保持良好实践",
                "定期安全评估",
                "监控系统变化",
                "更新安全策略"
            ]
            urgency = "low"
        
        return {
            'executive_summary': f"系统安全风险等级: {risk_level.upper()}",
            'detailed_findings': risk_assessment['risk_factors'],
            'recommendations': recommendations,
            'urgency_level': urgency,
            'next_steps': self._determine_next_steps(risk_level),
            'report_generated': datetime.datetime.now().isoformat()
        }
    
    def _determine_next_steps(self, risk_level: str) -> List[str]:
        """确定后续步骤"""
        steps_mapping = {
            'critical': [
                "立即成立应急响应小组",
                "执行 containment 策略",
                "进行根本原因分析",
                "实施纠正措施"
            ],
            'high': [
                "制定风险缓解计划",
                "分配资源进行修复",
                "加强监控",
                "定期进度检查"
            ],
            'medium': [
                "制定改进时间表",
                "分配责任人员",
                "设置完成期限",
                "定期审查进展"
            ],
            'low': [
                "纳入常规维护计划",
                "设置提醒进行定期检查",
                "文档化改进建议",
                "监控风险变化"
            ]
        }
        
        return steps_mapping.get(risk_level, ["进行进一步分析"])
    
    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        capabilities = [
            'security_monitoring',
            'threat_detection', 
            'risk_assessment',
            'incident_response',
            'security_auditing'
        ]
        
        # 添加监控类型能力
        monitoring_types = ['file_system', 'network', 'system_activity', 'user_behavior']
        for monitoring_type in monitoring_types:
            capabilities.append(f"{monitoring_type}_monitoring")
        
        return capabilities
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            'current_tasks': list(self.current_tasks),
            'security_level': self.security_level.value,
            'monitoring_enabled': self.monitoring_enabled
        }
    
    def get_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取安全事件"""
        return self.security_events[-limit:] if limit else self.security_events
    
    def update_security_rules(self, new_rules: Dict[str, Any]) -> bool:
        """更新安全规则"""
        try:
            self.security_rules.update(new_rules)
            self.logger.info("安全规则已更新")
            return True
        except Exception as e:
            self.logger.error(f"更新安全规则失败: {e}")
            return False

