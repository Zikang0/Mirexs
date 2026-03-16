"""
技术智能体模块：处理技术相关任务
实现基于代码分析和技术推理的技术问题解决系统
"""

import uuid
import datetime
import ast
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
import logging
from enum import Enum

class TechnicalDomain(Enum):
    PROGRAMMING = "programming"  # 编程
    SYSTEM_ADMIN = "system_admin"  # 系统管理
    NETWORKING = "networking"  # 网络
    SECURITY = "security"  # 安全
    DATA_SCIENCE = "data_science"  # 数据科学

class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "c++"
    GO = "go"
    RUST = "rust"

class TechnicalAgent:
    """技术智能体 - 处理技术相关任务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 智能体身份
        self.agent_id = self.config.get('agent_id', f"technical_agent_{uuid.uuid4().hex[:8]}")
        self.agent_type = "technical"
        
        # 技术能力配置
        self.supported_domains = self.config.get('supported_domains', [domain.value for domain in TechnicalDomain])
        self.programming_languages = self.config.get('programming_languages', [lang.value for lang in CodeLanguage])
        self.skill_level = self.config.get('skill_level', 0.8)  # 技术水平
        
        # 工具配置
        self.code_analysis_tools = self.config.get('code_analysis_tools', ['pylint', 'flake8', 'mypy'])
        self.testing_frameworks = self.config.get('testing_frameworks', ['pytest', 'unittest'])
        
        # 知识库
        self.technical_knowledge_base = self._initialize_knowledge_base()
        self.code_patterns = self._load_code_patterns()
        
        # 工作状态
        self.current_tasks = set()
        self.technical_history = []
        self.performance_metrics = {
            'tasks_completed': 0,
            'code_written': 0,
            'bugs_fixed': 0,
            'system_issues_resolved': 0,
            'domain_expertise': {domain: 0.5 for domain in self.supported_domains}
        }
        
        # 初始化技术工具
        self._initialize_technical_tools()
        
        self.initialized = True
        self.logger.info(f"技术智能体初始化成功: {self.agent_id}")
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """初始化技术知识库"""
        return {
            'programming': {
                'best_practices': [
                    '编写清晰的变量名和函数名',
                    '遵循代码风格指南',
                    '添加适当的注释',
                    '编写单元测试',
                    '错误处理和安全考虑'
                ],
                'common_patterns': {
                    'singleton': '单例模式',
                    'factory': '工厂模式',
                    'observer': '观察者模式',
                    'strategy': '策略模式'
                }
            },
            'system_admin': {
                'monitoring_tools': ['prometheus', 'grafana', 'zabbix'],
                'automation_tools': ['ansible', 'puppet', 'chef'],
                'containerization': ['docker', 'kubernetes']
            },
            'networking': {
                'protocols': ['TCP/IP', 'HTTP/HTTPS', 'DNS', 'SSL/TLS'],
                'tools': ['wireshark', 'nmap', 'ping', 'traceroute']
            },
            'security': {
                'principles': ['最小权限', '防御深度', '安全默认值'],
                'practices': ['定期更新', '安全审计', '漏洞扫描']
            }
        }
    
    def _load_code_patterns(self) -> Dict[str, Any]:
        """加载代码模式"""
        return {
            'python': {
                'file_operations': {
                    'template': '''
def read_file(file_path):
    """读取文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"文件不存在: {file_path}")
        return None
                    ''',
                    'description': '安全的文件读取操作'
                },
                'api_client': {
                    'template': '''
import requests

class APIClient:
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def get(self, endpoint, params=None):
        """发送GET请求"""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API请求失败: {e}")
            return None
                    ''',
                    'description': 'API客户端模板'
                }
            },
            'javascript': {
                'async_operations': {
                    'template': '''
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('获取数据失败:', error);
        return null;
    }
}
                    ''',
                    'description': '异步数据获取'
                }
            }
        }
    
    def _initialize_technical_tools(self):
        """初始化技术工具"""
        try:
            # 检查系统工具可用性
            self.available_tools = {}
            
            for tool in self.code_analysis_tools:
                try:
                    subprocess.run([tool, '--version'], capture_output=True, check=True)
                    self.available_tools[tool] = True
                    self.logger.info(f"工具可用: {tool}")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self.available_tools[tool] = False
                    self.logger.warning(f"工具不可用: {tool}")
            
            # 初始化代码分析器
            self._initialize_code_analyzer()
            
        except Exception as e:
            self.logger.error(f"技术工具初始化失败: {e}")
    
    def _initialize_code_analyzer(self):
        """初始化代码分析器"""
        try:
            # 使用内置的ast模块进行基本代码分析
            self.code_analyzer = ast
            self.logger.info("代码分析器初始化完成")
        except Exception as e:
            self.logger.error(f"代码分析器初始化失败: {e}")
    
    async def analyze_code(self,
                         task_id: str,
                         code: str,
                         language: str,
                         analysis_type: str = 'quality') -> Dict[str, Any]:
        """
        分析代码
        
        Args:
            task_id: 任务ID
            code: 代码内容
            language: 编程语言
            analysis_type: 分析类型
            
        Returns:
            分析结果
        """
        try:
            self.current_tasks.add(task_id)
            
            analysis_result = {
                'task_id': task_id,
                'language': language,
                'analysis_type': analysis_type,
                'timestamp': datetime.datetime.now().isoformat(),
                'issues': [],
                'metrics': {},
                'suggestions': []
            }
            
            if language == 'python':
                result = await self._analyze_python_code(code, analysis_type)
                analysis_result.update(result)
            else:
                analysis_result['issues'].append({
                    'level': 'warning',
                    'message': f'不支持的语言: {language}，使用基本分析',
                    'line': 0
                })
                # 基本文本分析
                basic_analysis = self._basic_code_analysis(code, language)
                analysis_result.update(basic_analysis)
            
            # 记录技术历史
            self.technical_history.append({
                'task_id': task_id,
                'action': 'code_analysis',
                'language': language,
                'analysis_type': analysis_type,
                'result': analysis_result,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'analysis_result': analysis_result
            }
            
        except Exception as e:
            self.logger.error(f"代码分析失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _analyze_python_code(self, code: str, analysis_type: str) -> Dict[str, Any]:
        """分析Python代码"""
        analysis_result = {
            'issues': [],
            'metrics': {},
            'suggestions': []
        }
        
        try:
            # 语法分析
            try:
                tree = ast.parse(code)
                analysis_result['metrics']['syntax_valid'] = True
            except SyntaxError as e:
                analysis_result['issues'].append({
                    'level': 'error',
                    'message': f'语法错误: {e}',
                    'line': e.lineno,
                    'column': e.offset
                })
                analysis_result['metrics']['syntax_valid'] = False
                return analysis_result
            
            # 基本代码度量
            analysis_result['metrics'].update(self._calculate_code_metrics(tree, code))
            
            # 代码质量检查
            if analysis_type in ['quality', 'all']:
                quality_issues = self._check_code_quality(tree, code)
                analysis_result['issues'].extend(quality_issues)
            
            # 安全检查
            if analysis_type in ['security', 'all']:
                security_issues = self._check_security_issues(tree)
                analysis_result['issues'].extend(security_issues)
            
            # 性能检查
            if analysis_type in ['performance', 'all']:
                performance_issues = self._check_performance_issues(tree)
                analysis_result['issues'].extend(performance_issues)
            
            # 生成改进建议
            analysis_result['suggestions'] = self._generate_improvement_suggestions(analysis_result)
            
        except Exception as e:
            self.logger.error(f"Python代码分析错误: {e}")
            analysis_result['issues'].append({
                'level': 'error',
                'message': f'分析过程中发生错误: {e}',
                'line': 0
            })
        
        return analysis_result
    
    def _calculate_code_metrics(self, tree: ast.AST, code: str) -> Dict[str, Any]:
        """计算代码度量"""
        lines = code.split('\n')
        
        # 基本统计
        metrics = {
            'line_count': len(lines),
            'function_count': 0,
            'class_count': 0,
            'import_count': 0,
            'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0
        }
        
        # 遍历AST统计
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                metrics['function_count'] += 1
            elif isinstance(node, ast.ClassDef):
                metrics['class_count'] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics['import_count'] += 1
        
        # 计算复杂度（简化）
        metrics['complexity_score'] = min(1.0, (metrics['function_count'] * 0.1 + metrics['class_count'] * 0.2))
        
        return metrics
    
    def _check_code_quality(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """检查代码质量"""
        issues = []
        
        # 检查函数长度
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_code = ast.get_source_segment(code, node)
                if function_code:
                    function_lines = function_code.split('\n')
                    if len(function_lines) > 50:
                        issues.append({
                            'level': 'warning',
                            'message': f'函数 "{node.name}" 过长 ({len(function_lines)} 行)，建议拆分为更小的函数',
                            'line': node.lineno
                        })
        
        # 检查变量命名
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                var_name = node.id
                if len(var_name) == 1 and var_name not in ['i', 'j', 'k']:
                    issues.append({
                        'level': 'info',
                        'message': f'变量名 "{var_name}" 过于简单，建议使用描述性名称',
                        'line': node.lineno
                    })
        
        # 检查魔法数字
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if abs(node.value) not in [0, 1, 2, 10, 100, 1000]:
                    issues.append({
                        'level': 'info', 
                        'message': f'发现魔法数字: {node.value}，建议定义为常量',
                        'line': node.lineno
                    })
        
        return issues
    
    def _check_security_issues(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """检查安全问题"""
        issues = []
        security_patterns = {
            'eval': '使用eval函数可能导致代码注入',
            'exec': '使用exec函数可能执行任意代码',
            'pickle': '反序列化pickle数据可能执行任意代码',
            'subprocess': '使用shell=True可能造成命令注入'
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in security_patterns:
                        issues.append({
                            'level': 'warning',
                            'message': security_patterns[func_name],
                            'line': node.lineno
                        })
        
        return issues
    
    def _check_performance_issues(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """检查性能问题"""
        issues = []
        
        # 检查循环中的函数调用
        in_loop = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                in_loop = True
            elif in_loop and isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and not node.func.id.startswith('_'):
                    issues.append({
                        'level': 'info',
                        'message': f'在循环中调用函数 "{node.func.id}"，可能影响性能',
                        'line': node.lineno
                    })
        
        return issues
    
    def _generate_improvement_suggestions(self, analysis_result: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        metrics = analysis_result['metrics']
        
        # 基于度量的建议
        if metrics.get('function_count', 0) == 0:
            suggestions.append("考虑将代码组织到函数中，提高可读性和可复用性")
        
        if metrics.get('line_count', 0) > 200:
            suggestions.append("代码文件较长，考虑拆分为多个模块")
        
        if metrics.get('average_line_length', 0) > 100:
            suggestions.append("行长度较长，建议适当换行提高可读性")
        
        # 基于问题的建议
        issue_levels = [issue['level'] for issue in analysis_result['issues']]
        if 'error' in issue_levels:
            suggestions.append("修复代码中的语法错误")
        if 'warning' in issue_levels:
            suggestions.append("处理代码中的警告问题")
        
        return suggestions
    
    def _basic_code_analysis(self, code: str, language: str) -> Dict[str, Any]:
        """基本代码分析（用于不支持的语言）"""
        lines = code.split('\n')
        
        return {
            'metrics': {
                'line_count': len(lines),
                'character_count': len(code),
                'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0
            },
            'issues': [
                {
                    'level': 'info',
                    'message': f'使用基本分析，建议使用专门的分析工具进行{language}代码分析',
                    'line': 0
                }
            ],
            'suggestions': [
                f'使用{language}专用工具进行更深入的分析',
                '检查代码语法和结构',
                '确保遵循编程最佳实践'
            ]
        }
    
    async def generate_code(self,
                          task_id: str,
                          requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成代码
        
        Args:
            task_id: 任务ID
            requirements: 需求说明
            
        Returns:
            生成的代码
        """
        try:
            self.current_tasks.add(task_id)
            
            language = requirements.get('language', 'python')
            code_type = requirements.get('code_type', 'function')
            description = requirements.get('description', '')
            
            # 生成代码
            generated_code = await self._generate_code_implementation(language, code_type, description, requirements)
            
            # 代码质量检查
            analysis_result = await self._analyze_python_code(generated_code, 'quality') if language == 'python' else {}
            
            # 记录技术历史
            self.technical_history.append({
                'task_id': task_id,
                'action': 'code_generation',
                'language': language,
                'code_type': code_type,
                'generated_code': generated_code,
                'analysis_result': analysis_result,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            self.performance_metrics['code_written'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'generated_code': generated_code,
                'language': language,
                'analysis_result': analysis_result
            }
            
        except Exception as e:
            self.logger.error(f"代码生成失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    async def _generate_code_implementation(self, language: str, code_type: str, description: str, requirements: Dict[str, Any]) -> str:
        """生成代码实现"""
        if language == 'python':
            return self._generate_python_code(code_type, description, requirements)
        else:
            return f"# 代码生成 ({language} - {code_type})\n# 描述: {description}\n# 详细需求: {requirements}\n\n# 这里应该生成{language}代码"
    
    def _generate_python_code(self, code_type: str, description: str, requirements: Dict[str, Any]) -> str:
        """生成Python代码"""
        if code_type in self.code_patterns['python']:
            pattern = self.code_patterns['python'][code_type]
            code_template = pattern['template']
            
            # 简单的模板替换
            generated_code = code_template.replace('{description}', description)
            
            # 添加需求相关的定制
            if 'function_name' in requirements:
                generated_code = generated_code.replace('read_file', requirements['function_name'])
            
            return generated_code
        else:
            # 生成基本代码结构
            return f'''
def {requirements.get('function_name', 'main')}():
    """{description}"""
    # TODO: 实现功能
    pass

if __name__ == "__main__":
    {requirements.get('function_name', 'main')}()
'''
    
    async def troubleshoot_issue(self,
                               task_id: str,
                               issue_description: str,
                               symptoms: List[str],
                               domain: str) -> Dict[str, Any]:
        """
        故障排除
        
        Args:
            task_id: 任务ID
            issue_description: 问题描述
            symptoms: 症状列表
            domain: 问题领域
            
        Returns:
            故障排除结果
        """
        try:
            self.current_tasks.add(task_id)
            
            # 分析问题
            analysis = self._analyze_technical_issue(issue_description, symptoms, domain)
            
            # 生成解决方案
            solutions = self._generate_solutions(analysis, domain)
            
            # 评估解决方案
            evaluated_solutions = self._evaluate_solutions(solutions, analysis)
            
            # 记录技术历史
            self.technical_history.append({
                'task_id': task_id,
                'action': 'troubleshooting',
                'domain': domain,
                'issue_description': issue_description,
                'symptoms': symptoms,
                'analysis': analysis,
                'solutions': evaluated_solutions,
                'timestamp': datetime.datetime.now().isoformat()
            })
            
            # 更新性能指标
            self.performance_metrics['tasks_completed'] += 1
            self.performance_metrics['system_issues_resolved'] += 1
            
            self.current_tasks.remove(task_id)
            
            return {
                'success': True,
                'task_id': task_id,
                'analysis': analysis,
                'solutions': evaluated_solutions,
                'recommended_solution': self._select_best_solution(evaluated_solutions)
            }
            
        except Exception as e:
            self.logger.error(f"故障排除失败: {e}")
            self.current_tasks.remove(task_id)
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    def _analyze_technical_issue(self, issue_description: str, symptoms: List[str], domain: str) -> Dict[str, Any]:
        """分析技术问题"""
        # 基于知识库的问题分析
        analysis = {
            'domain': domain,
            'symptoms_analysis': [],
            'possible_causes': [],
            'severity': 'medium',  # low, medium, high, critical
            'urgency': 'medium'    # low, medium, high, immediate
        }
        
        # 症状分析
        for symptom in symptoms:
            symptom_analysis = self._analyze_symptom(symptom, domain)
            analysis['symptoms_analysis'].append(symptom_analysis)
        
        # 可能原因
        analysis['possible_causes'] = self._identify_possible_causes(analysis['symptoms_analysis'], domain)
        
        # 严重性和紧急性评估
        analysis.update(self._assess_issue_severity(analysis['possible_causes'], symptoms))
        
        return analysis
    
    def _analyze_symptom(self, symptom: str, domain: str) -> Dict[str, Any]:
        """分析症状"""
        symptom_lower = symptom.lower()
        
        # 基于关键词的症状分析
        critical_keywords = ['crash', 'error', 'fail', 'broken', 'not working']
        warning_keywords = ['slow', 'lag', 'delay', 'timeout']
        info_keywords = ['warning', 'notice', 'info']
        
        severity = 'info'
        for keyword in critical_keywords:
            if keyword in symptom_lower:
                severity = 'critical'
                break
        
        if severity == 'info':
            for keyword in warning_keywords:
                if keyword in symptom_lower:
                    severity = 'warning'
                    break
        
        return {
            'symptom': symptom,
            'severity': severity,
            'related_domains': [domain],
            'common_causes': self._get_common_causes_for_symptom(symptom, domain)
        }
    
    def _get_common_causes_for_symptom(self, symptom: str, domain: str) -> List[str]:
        """获取症状的常见原因"""
        # 基于知识库的常见原因映射
        cause_mapping = {
            'programming': {
                'crash': ['内存泄漏', '空指针引用', '数组越界', '递归深度过大'],
                'slow': ['算法复杂度高', '频繁IO操作', '内存不足', '网络延迟'],
                'error': ['语法错误', '类型错误', '逻辑错误', '配置错误']
            },
            'system_admin': {
                'crash': ['资源耗尽', '配置错误', '软件冲突', '硬件故障'],
                'slow': ['CPU过载', '内存不足', '磁盘IO瓶颈', '网络拥堵'],
                'error': ['权限问题', '服务未启动', '配置文件错误', '依赖缺失']
            }
        }
        
        symptom_lower = symptom.lower()
        causes = []
        
        if domain in cause_mapping:
            for symptom_pattern, domain_causes in cause_mapping[domain].items():
                if symptom_pattern in symptom_lower:
                    causes.extend(domain_causes)
        
        return causes if causes else ['未知原因，需要进一步分析']
    
    def _identify_possible_causes(self, symptoms_analysis: List[Dict[str, Any]], domain: str) -> List[Dict[str, Any]]:
        """识别可能原因"""
        causes = []
        
        for symptom_analysis in symptoms_analysis:
            for cause in symptom_analysis['common_causes']:
                causes.append({
                    'cause': cause,
                    'confidence': 0.7,  # 置信度
                    'symptoms_matched': [symptom_analysis['symptom']],
                    'domain': domain
                })
        
        # 去重和排序
        unique_causes = {}
        for cause in causes:
            cause_key = cause['cause']
            if cause_key not in unique_causes:
                unique_causes[cause_key] = cause
            else:
                # 合并症状和更新置信度
                unique_causes[cause_key]['symptoms_matched'].extend(cause['symptoms_matched'])
                unique_causes[cause_key]['confidence'] = min(1.0, unique_causes[cause_key]['confidence'] + 0.1)
        
        sorted_causes = sorted(unique_causes.values(), key=lambda x: x['confidence'], reverse=True)
        return sorted_causes
    
    def _assess_issue_severity(self, possible_causes: List[Dict[str, Any]], symptoms: List[str]) -> Dict[str, str]:
        """评估问题严重性"""
        # 基于原因和症状的严重性评估
        max_severity = 'low'
        max_urgency = 'low'
        
        for cause in possible_causes:
            cause_text = cause['cause'].lower()
            
            # 严重原因
            if any(keyword in cause_text for keyword in ['crash', '数据丢失', '安全漏洞', '系统崩溃']):
                max_severity = 'critical'
                max_urgency = 'immediate'
            elif any(keyword in cause_text for keyword in ['性能下降', '资源耗尽', '服务中断']):
                if max_severity != 'critical':
                    max_severity = 'high'
                    max_urgency = 'high'
            elif any(keyword in cause_text for keyword in ['警告', '配置问题', '小问题']):
                if max_severity not in ['critical', 'high']:
                    max_severity = 'medium'
                    max_urgency = 'medium'
        
        # 检查症状关键词
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            if any(keyword in symptom_lower for keyword in ['紧急', '立即', '严重', '崩溃']):
                max_urgency = 'immediate'
                if max_severity != 'critical':
                    max_severity = 'high'
        
        return {
            'severity': max_severity,
            'urgency': max_urgency
        }
    
    def _generate_solutions(self, analysis: Dict[str, Any], domain: str) -> List[Dict[str, Any]]:
        """生成解决方案"""
        solutions = []
        
        for cause in analysis['possible_causes']:
            solution = self._create_solution_for_cause(cause, domain)
            solutions.append(solution)
        
        return solutions
    
    def _create_solution_for_cause(self, cause: Dict[str, Any], domain: str) -> Dict[str, Any]:
        """为原因创建解决方案"""
        solution_templates = {
            'programming': {
                '内存泄漏': '检查代码中的资源管理，确保正确释放内存，使用内存分析工具检测泄漏点',
                '空指针引用': '添加空值检查，使用可选类型或空对象模式',
                '算法复杂度高': '分析算法时间复杂度，考虑使用更高效的算法或数据结构优化',
                '配置错误': '验证配置文件格式和内容，检查环境变量和配置路径'
            },
            'system_admin': {
                '资源耗尽': '监控系统资源使用情况，优化资源配置，考虑横向扩展',
                '服务未启动': '检查服务状态，查看日志文件，重新启动服务',
                '权限问题': '验证用户权限，检查文件和目录权限设置',
                '网络拥堵': '分析网络流量，优化网络配置，增加带宽或使用负载均衡'
            }
        }
        
        cause_text = cause['cause']
        solution_text = "请参考相关文档或寻求专业帮助"
        
        if domain in solution_templates and cause_text in solution_templates[domain]:
            solution_text = solution_templates[domain][cause_text]
        
        return {
            'cause': cause_text,
            'solution': solution_text,
            'complexity': 'medium',  # low, medium, high
            'estimated_time': '30分钟',  # 预估解决时间
            'prerequisites': [],  # 先决条件
            'confidence': cause['confidence']
        }
    
    def _evaluate_solutions(self, solutions: List[Dict[str, Any]], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """评估解决方案"""
        evaluated_solutions = []
        
        for solution in solutions:
            # 计算解决方案评分
            score = self._calculate_solution_score(solution, analysis)
            solution['score'] = score
            evaluated_solutions.append(solution)
        
        # 按评分排序
        evaluated_solutions.sort(key=lambda x: x['score'], reverse=True)
        return evaluated_solutions
    
    def _calculate_solution_score(self, solution: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """计算解决方案评分"""
        score = solution['confidence'] * 0.6  # 基础置信度
        
        # 复杂性调整（越简单越好）
        complexity_weights = {'low': 1.0, 'medium': 0.7, 'high': 0.4}
        score *= complexity_weights.get(solution['complexity'], 0.5)
        
        # 紧急性调整（紧急问题偏好快速解决方案）
        if analysis['urgency'] in ['immediate', 'high']:
            time_penalty = 0.1 if '小时' in solution['estimated_time'] else 0
            score -= time_penalty
        
        return min(1.0, score)
    
    def _select_best_solution(self, evaluated_solutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """选择最佳解决方案"""
        if not evaluated_solutions:
            return {
                'solution': '暂无可用解决方案，建议收集更多信息或寻求专家帮助',
                'confidence': 0.0,
                'reason': '无匹配解决方案'
            }
        
        best_solution = evaluated_solutions[0]
        return {
            'solution': best_solution['solution'],
            'confidence': best_solution['score'],
            'cause': best_solution['cause'],
            'complexity': best_solution['complexity'],
            'estimated_time': best_solution['estimated_time'],
            'reason': '综合评分最高的解决方案'
        }
    
    def get_capabilities(self) -> List[str]:
        """获取能力列表"""
        capabilities = [
            'code_analysis',
            'code_generation', 
            'troubleshooting',
            'technical_consulting',
            'system_diagnostics'
        ]
        
        # 添加支持的领域能力
        for domain in self.supported_domains:
            capabilities.append(f"{domain}_expertise")
        
        # 添加编程语言能力
        for language in self.programming_languages:
            capabilities.append(f"{language}_programming")
        
        return capabilities
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            **self.performance_metrics,
            'current_tasks': list(self.current_tasks),
            'supported_domains': self.supported_domains,
            'programming_languages': self.programming_languages
        }
    
    def get_technical_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取技术历史"""
        return self.technical_history[-limit:] if limit else self.technical_history

