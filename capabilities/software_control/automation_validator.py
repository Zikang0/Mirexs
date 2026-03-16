"""
自动化验证器：验证自动化流程
"""
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """验证级别枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ValidationStatus(Enum):
    """验证状态枚举"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class ValidationRule:
    """验证规则"""
    id: str
    name: str
    description: str
    level: ValidationLevel
    check_function: str  # 检查函数名称
    parameters: Dict[str, Any] = None
    error_message: str = ""
    fix_suggestion: str = ""
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

@dataclass
class ValidationResult:
    """验证结果"""
    rule_id: str
    rule_name: str
    status: ValidationStatus
    message: str
    level: ValidationLevel
    timestamp: datetime
    details: Dict[str, Any] = None
    fix_suggestion: str = ""
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class AutomationValidator:
    """自动化验证器"""
    
    def __init__(self):
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.validation_results: List[ValidationResult] = []
        self._setup_logging()
        self._load_default_rules()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_default_rules(self):
        """加载默认验证规则"""
        # 安全性验证规则
        security_rules = [
            ValidationRule(
                id="sec_001",
                name="危险命令检查",
                description="检查自动化流程中是否包含危险系统命令",
                level=ValidationLevel.CRITICAL,
                check_function="check_dangerous_commands",
                error_message="发现危险系统命令",
                fix_suggestion="移除或替换危险命令"
            ),
            ValidationRule(
                id="sec_002",
                name="文件删除操作检查",
                description="检查是否包含无限制的文件删除操作",
                level=ValidationLevel.HIGH,
                check_function="check_file_deletion",
                error_message="发现无限制的文件删除操作",
                fix_suggestion="添加确认机制或限制删除范围"
            )
        ]
        
        # 性能验证规则
        performance_rules = [
            ValidationRule(
                id="perf_001",
                name="循环操作检查",
                description="检查是否包含可能无限循环的操作",
                level=ValidationLevel.HIGH,
                check_function="check_infinite_loops",
                error_message="发现可能无限循环的操作",
                fix_suggestion="添加循环终止条件"
            ),
            ValidationRule(
                id="perf_002",
                name="资源使用检查",
                description="检查资源使用是否合理",
                level=ValidationLevel.MEDIUM,
                check_function="check_resource_usage",
                error_message="资源使用可能不合理",
                fix_suggestion="优化资源使用"
            )
        ]
        
        # 功能性验证规则
        functional_rules = [
            ValidationRule(
                id="func_001",
                name="依赖项检查",
                description="检查所需的应用程序和依赖项是否可用",
                level=ValidationLevel.HIGH,
                check_function="check_dependencies",
                error_message="缺少必要的依赖项",
                fix_suggestion="安装缺失的依赖项"
            ),
            ValidationRule(
                id="func_002",
                name="文件路径检查",
                description="检查文件路径是否存在且可访问",
                level=ValidationLevel.MEDIUM,
                check_function="check_file_paths",
                error_message="文件路径不存在或不可访问",
                fix_suggestion="修正文件路径或创建缺失的目录"
            )
        ]
        
        # 注册所有规则
        all_rules = security_rules + performance_rules + functional_rules
        for rule in all_rules:
            self.register_validation_rule(rule)
    
    def register_validation_rule(self, rule: ValidationRule) -> bool:
        """注册验证规则"""
        try:
            self.validation_rules[rule.id] = rule
            logger.info(f"注册验证规则: {rule.name} (ID: {rule.id})")
            return True
        except Exception as e:
            logger.error(f"注册验证规则失败: {str(e)}")
            return False
    
    def validate_automation_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证自动化工作流"""
        try:
            logger.info("开始验证自动化工作流")
            
            validation_results = []
            critical_issues = 0
            high_issues = 0
            
            # 执行所有验证规则
            for rule_id, rule in self.validation_rules.items():
                result = self._execute_validation_rule(rule, workflow_data)
                validation_results.append(result)
                
                if result.status == ValidationStatus.FAILED:
                    if rule.level == ValidationLevel.CRITICAL:
                        critical_issues += 1
                    elif rule.level == ValidationLevel.HIGH:
                        high_issues += 1
            
            # 生成验证报告
            report = self._generate_validation_report(validation_results)
            
            # 确定总体验证状态
            if critical_issues > 0:
                overall_status = "FAILED"
            elif high_issues > 0:
                overall_status = "WARNING"
            else:
                overall_status = "PASSED"
            
            report['overall_status'] = overall_status
            report['critical_issues'] = critical_issues
            report['high_issues'] = high_issues
            
            logger.info(f"自动化工作流验证完成: {overall_status}")
            return report
            
        except Exception as e:
            logger.error(f"验证自动化工作流失败: {str(e)}")
            return {
                'overall_status': 'ERROR',
                'error_message': str(e),
                'validation_results': []
            }
    
    def _execute_validation_rule(self, rule: ValidationRule, workflow_data: Dict[str, Any]) -> ValidationResult:
        """执行单个验证规则"""
        try:
            # 获取检查函数
            check_function = getattr(self, rule.check_function, None)
            if not check_function:
                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.SKIPPED,
                    message=f"检查函数未找到: {rule.check_function}",
                    level=rule.level,
                    timestamp=datetime.now()
                )
            
            # 执行检查
            passed, message, details = check_function(workflow_data, rule.parameters)
            
            if passed:
                status = ValidationStatus.PASSED
                final_message = f"{rule.name}: 通过"
            else:
                status = ValidationStatus.FAILED
                final_message = f"{rule.name}: {rule.error_message} - {message}"
            
            return ValidationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                status=status,
                message=final_message,
                level=rule.level,
                timestamp=datetime.now(),
                details=details or {},
                fix_suggestion=rule.fix_suggestion if status == ValidationStatus.FAILED else ""
            )
            
        except Exception as e:
            return ValidationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                status=ValidationStatus.FAILED,
                message=f"验证执行错误: {str(e)}",
                level=rule.level,
                timestamp=datetime.now()
            )
    
    def _generate_validation_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """生成验证报告"""
        passed_count = len([r for r in results if r.status == ValidationStatus.PASSED])
        failed_count = len([r for r in results if r.status == ValidationStatus.FAILED])
        warning_count = len([r for r in results if r.status == ValidationStatus.WARNING])
        skipped_count = len([r for r in results if r.status == ValidationStatus.SKIPPED])
        
        # 按级别分类问题
        critical_issues = [r for r in results if r.status == ValidationStatus.FAILED and r.level == ValidationLevel.CRITICAL]
        high_issues = [r for r in results if r.status == ValidationStatus.FAILED and r.level == ValidationLevel.HIGH]
        medium_issues = [r for r in results if r.status == ValidationStatus.FAILED and r.level == ValidationLevel.MEDIUM]
        low_issues = [r for r in results if r.status == ValidationStatus.FAILED and r.level == ValidationLevel.LOW]
        
        return {
            'summary': {
                'total_rules': len(results),
                'passed': passed_count,
                'failed': failed_count,
                'warning': warning_count,
                'skipped': skipped_count,
                'pass_rate': passed_count / len(results) if len(results) > 0 else 0
            },
            'issues_by_severity': {
                'critical': len(critical_issues),
                'high': len(high_issues),
                'medium': len(medium_issues),
                'low': len(low_issues)
            },
            'validation_results': [asdict(result) for result in results],
            'critical_issues': [asdict(issue) for issue in critical_issues],
            'high_issues': [asdict(issue) for issue in high_issues],
            'timestamp': datetime.now().isoformat()
        }
    
    # 验证检查函数
    
    def check_dangerous_commands(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查危险命令"""
        dangerous_patterns = [
            r'rm\s+-rf',  # 强制删除
            r'format\s+[A-Z]:',  # 格式化磁盘
            r'del\s+/[FfQq]',  # 强制删除
            r'shutdown\s+',  # 关机命令
            r'cmdkey\s+/delete',  # 删除凭据
        ]
        
        workflow_text = json.dumps(workflow_data, ensure_ascii=False)
        
        found_commands = []
        for pattern in dangerous_patterns:
            if re.search(pattern, workflow_text, re.IGNORECASE):
                found_commands.append(pattern)
        
        if found_commands:
            return False, f"发现危险命令模式: {', '.join(found_commands)}", {'found_commands': found_commands}
        
        return True, "未发现危险命令", {}
    
    def check_file_deletion(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查文件删除操作"""
        deletion_patterns = [
            r'"operation":\s*"delete"',
            r'Remove-Item',
            r'del\s+',
            r'erase\s+'
        ]
        
        workflow_text = json.dumps(workflow_data, ensure_ascii=False)
        
        found_deletions = []
        for pattern in deletion_patterns:
            if re.search(pattern, workflow_text, re.IGNORECASE):
                found_deletions.append(pattern)
        
        if found_deletions:
            return False, f"发现文件删除操作: {len(found_deletions)}处", {'deletion_operations': found_deletions}
        
        return True, "未发现危险的文件删除操作", {}
    
    def check_infinite_loops(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查无限循环"""
        # 检查工作流步骤中是否有循环依赖
        steps = workflow_data.get('steps', [])
        step_ids = [step.get('id') for step in steps]
        next_step_references = [step.get('next_step_id') for step in steps if step.get('next_step_id')]
        
        # 检查循环引用
        cyclic_dependencies = []
        for step in steps:
            current_id = step.get('id')
            next_id = step.get('next_step_id')
            
            if next_id and self._has_cyclic_dependency(steps, current_id, next_id, set()):
                cyclic_dependencies.append(f"{current_id} -> {next_id}")
        
        if cyclic_dependencies:
            return False, f"发现循环依赖: {', '.join(cyclic_dependencies)}", {'cyclic_dependencies': cyclic_dependencies}
        
        return True, "未发现循环依赖", {}
    
    def _has_cyclic_dependency(self, steps: List[Dict[str, Any]], start_id: str, current_id: str, visited: set) -> bool:
        """检查循环依赖"""
        if current_id == start_id:
            return True
        
        if current_id in visited:
            return False
        
        visited.add(current_id)
        
        # 查找当前步骤的下一步
        current_step = next((step for step in steps if step.get('id') == current_id), None)
        if not current_step:
            return False
        
        next_id = current_step.get('next_step_id')
        if not next_id:
            return False
        
        return self._has_cyclic_dependency(steps, start_id, next_id, visited)
    
    def check_resource_usage(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查资源使用"""
        steps = workflow_data.get('steps', [])
        
        # 检查长时间运行的操作
        long_running_ops = []
        for step in steps:
            action_type = step.get('action_type', '')
            params = step.get('parameters', {})
            
            # 检查等待时间
            if action_type == 'wait':
                duration = params.get('duration', 0)
                if duration > 60:  # 超过60秒的等待
                    long_running_ops.append(f"长时间等待: {duration}秒")
            
            # 检查大文件操作
            elif action_type == 'file_operation':
                operation = params.get('operation', '')
                if operation in ['copy', 'move']:
                    source = params.get('source', '')
                    if any(ext in source.lower() for ext in ['.mp4', '.avi', '.iso', '.zip']):
                        long_running_ops.append(f"大文件操作: {source}")
        
        if long_running_ops:
            return False, f"发现可能的资源密集型操作: {len(long_running_ops)}处", {'long_running_operations': long_running_ops}
        
        return True, "资源使用合理", {}
    
    def check_dependencies(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查依赖项"""
        steps = workflow_data.get('steps', [])
        missing_dependencies = []
        
        for step in steps:
            action_type = step.get('action_type', '')
            params = step.get('parameters', {})
            
            if action_type == 'launch_application':
                app_name = params.get('application_name', '')
                if not self._check_application_exists(app_name):
                    missing_dependencies.append(f"应用程序: {app_name}")
            
            elif action_type == 'execute_script':
                script_type = params.get('script_type', '')
                if not self._check_script_environment(script_type):
                    missing_dependencies.append(f"脚本环境: {script_type}")
        
        if missing_dependencies:
            return False, f"缺少依赖项: {', '.join(missing_dependencies)}", {'missing_dependencies': missing_dependencies}
        
        return True, "所有依赖项可用", {}
    
    def _check_application_exists(self, app_name: str) -> bool:
        """检查应用程序是否存在"""
        try:
            from .application_launcher import get_application_launcher
            launcher = get_application_launcher()
            return app_name in launcher.application_registry
        except Exception:
            return False
    
    def _check_script_environment(self, script_type: str) -> bool:
        """检查脚本环境是否可用"""
        try:
            if script_type == 'python':
                import sys
                return True
            elif script_type == 'powershell':
                import subprocess
                result = subprocess.run(['powershell', '-Command', 'Get-Host'], capture_output=True)
                return result.returncode == 0
            else:
                return True
        except Exception:
            return False
    
    def check_file_paths(self, workflow_data: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """检查文件路径"""
        steps = workflow_data.get('steps', [])
        invalid_paths = []
        
        for step in steps:
            action_type = step.get('action_type', '')
            params = step.get('parameters', {})
            
            # 检查文件操作中的路径
            if action_type in ['file_operation', 'execute_script']:
                paths_to_check = []
                
                if 'source' in params:
                    paths_to_check.append(params['source'])
                if 'destination' in params:
                    paths_to_check.append(params['destination'])
                if 'script_path' in params:
                    paths_to_check.append(params['script_path'])
                
                for path in paths_to_check:
                    if path and not self._check_path_valid(path):
                        invalid_paths.append(path)
        
        if invalid_paths:
            return False, f"无效文件路径: {', '.join(invalid_paths)}", {'invalid_paths': invalid_paths}
        
        return True, "所有文件路径有效", {}
    
    def _check_path_valid(self, path: str) -> bool:
        """检查路径有效性"""
        try:
            # 检查路径格式
            if not path or len(path.strip()) == 0:
                return False
            
            # 对于相对路径，假设它们在工作目录中创建
            if not os.path.isabs(path):
                return True
            
            # 检查绝对路径的父目录是否存在
            parent_dir = os.path.dirname(path)
            return os.path.exists(parent_dir)
            
        except Exception:
            return False
    
    def validate_macro(self, macro_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证宏"""
        return self.validate_automation_workflow(macro_data)
    
    def validate_script(self, script_content: str, script_type: str) -> Dict[str, Any]:
        """验证脚本"""
        workflow_data = {
            'type': 'script',
            'script_type': script_type,
            'content': script_content
        }
        return self.validate_automation_workflow(workflow_data)
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        total_validations = len(self.validation_results)
        
        status_counts = {}
        level_counts = {}
        
        for result in self.validation_results:
            status = result.status.value
            level = result.level.value
            
            status_counts[status] = status_counts.get(status, 0) + 1
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            'total_validations': total_validations,
            'status_distribution': status_counts,
            'level_distribution': level_counts,
            'success_rate': status_counts.get('passed', 0) / total_validations if total_validations > 0 else 0
        }
    
    def export_validation_report(self, report: Dict[str, Any], file_path: str) -> bool:
        """导出验证报告"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"验证报告导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出验证报告失败: {str(e)}")
            return False

# 单例实例
_automation_validator_instance = None

def get_automation_validator() -> AutomationValidator:
    """获取自动化验证器单例"""
    global _automation_validator_instance
    if _automation_validator_instance is None:
        _automation_validator_instance = AutomationValidator()
    return _automation_validator_instance
