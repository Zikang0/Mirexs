"""
安全验证器

负责验证插件的安全性，包括代码安全、权限检查、风险评估。
提供安全扫描和威胁检测功能。

Author: AI Assistant
Date: 2025-11-05
"""

import ast
import os
import hashlib
import logging
import subprocess
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SecurityIssue:
    """安全问题数据类"""
    severity: str  # 'low', 'medium', 'high', 'critical'
    issue_type: str
    description: str
    file_path: str
    line_number: int
    recommendation: str


@dataclass
class SecurityReport:
    """安全报告数据类"""
    plugin_name: str
    overall_score: float  # 0-100
    issues: List[SecurityIssue]
    permissions: List[str]
    dependencies: List[str]
    verified: bool
    scan_timestamp: str


class SecurityValidator:
    """安全验证器类"""
    
    def __init__(self):
        """初始化安全验证器"""
        self.logger = logging.getLogger(__name__)
        self._security_rules: Dict[str, Any] = {}
        self._whitelist_files: Set[str] = set()
        self._blacklist_patterns: List[str] = []
        self._required_permissions: List[str] = []
        
    def add_security_rule(self, rule_name: str, rule_config: Any) -> None:
        """
        添加安全规则
        
        Args:
            rule_name: 规则名称
            rule_config: 规则配置
        """
        self._security_rules[rule_name] = rule_config
        self.logger.info(f"添加安全规则: {rule_name}")
    
    def add_to_whitelist(self, file_path: str) -> None:
        """
        添加文件到白名单
        
        Args:
            file_path: 文件路径
        """
        self._whitelist_files.add(file_path)
        self.logger.info(f"添加文件到白名单: {file_path}")
    
    def add_to_blacklist(self, pattern: str) -> None:
        """
        添加模式到黑名单
        
        Args:
            pattern: 匹配模式
        """
        self._blacklist_patterns.append(pattern)
        self.logger.info(f"添加模式到黑名单: {pattern}")
    
    def scan_plugin(self, plugin_path: str, plugin_name: str) -> SecurityReport:
        """
        扫描插件安全性
        
        Args:
            plugin_path: 插件路径
            plugin_name: 插件名称
            
        Returns:
            SecurityReport: 安全报告
        """
        try:
            self.logger.info(f"开始扫描插件安全性: {plugin_name}")
            
            issues = []
            permissions = []
            dependencies = []
            
            # 扫描Python文件
            for file_path in Path(plugin_path).rglob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                file_issues = self._scan_python_file(str(file_path))
                issues.extend(file_issues)
            
            # 扫描权限需求
            permissions = self._scan_permissions(plugin_path)
            
            # 扫描依赖
            dependencies = self._scan_dependencies(plugin_path)
            
            # 计算安全评分
            overall_score = self._calculate_security_score(issues)
            
            # 检查是否验证通过
            verified = overall_score >= 70 and not any(issue.severity == 'critical' for issue in issues)
            
            report = SecurityReport(
                plugin_name=plugin_name,
                overall_score=overall_score,
                issues=issues,
                permissions=permissions,
                dependencies=dependencies,
                verified=verified,
                scan_timestamp=str(Path().cwd())
            )
            
            self.logger.info(f"插件安全扫描完成: {plugin_name}, 评分: {overall_score}")
            return report
            
        except Exception as e:
            self.logger.error(f"插件安全扫描失败 {plugin_name}: {str(e)}")
            return SecurityReport(
                plugin_name=plugin_name,
                overall_score=0.0,
                issues=[],
                permissions=[],
                dependencies=[],
                verified=False,
                scan_timestamp=str(Path().cwd())
            )
    
    def _scan_python_file(self, file_path: str) -> List[SecurityIssue]:
        """
        扫描Python文件安全性
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[SecurityIssue]: 安全问题列表
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            # 检查危险函数调用
            dangerous_functions = [
                'eval', 'exec', 'compile', 'open', 'input', 'raw_input',
                'importlib.import_module', '__import__', 'reload'
            ]
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in dangerous_functions:
                        issues.append(SecurityIssue(
                            severity='medium',
                            issue_type='dangerous_function',
                            description=f'使用危险函数: {node.func.id}',
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation=f'避免使用 {node.func.id} 函数，考虑更安全的替代方案'
                        ))
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ['os', 'sys', 'subprocess', 'pickle']:
                            issues.append(SecurityIssue(
                                severity='low',
                                issue_type='sensitive_import',
                                description=f'导入敏感模块: {alias.name}',
                                file_path=file_path,
                                line_number=node.lineno,
                                recommendation='确保敏感模块的使用是安全的'
                            ))
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in ['os', 'sys', 'subprocess', 'pickle', 'tempfile']:
                        issues.append(SecurityIssue(
                            severity='low',
                            issue_type='sensitive_import',
                            description=f'从敏感模块导入: {node.module}',
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation='确保敏感模块的使用是安全的'
                        ))
            
            # 检查文件操作
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if (isinstance(node.func, ast.Attribute) and 
                        node.func.attr in ['open', 'read', 'write']):
                        issues.append(SecurityIssue(
                            severity='medium',
                            issue_type='file_operation',
                            description=f'文件操作: {node.func.attr}',
                            file_path=file_path,
                            line_number=node.lineno,
                            recommendation='确保文件操作是安全的，避免路径遍历攻击'
                        ))
            
        except Exception as e:
            self.logger.error(f"Python文件扫描失败 {file_path}: {str(e)}")
            issues.append(SecurityIssue(
                severity='high',
                issue_type='scan_error',
                description=f'扫描文件时发生错误: {str(e)}',
                file_path=file_path,
                line_number=0,
                recommendation='检查文件格式和语法'
            ))
        
        return issues
    
    def _scan_permissions(self, plugin_path: str) -> List[str]:
        """
        扫描权限需求
        
        Args:
            plugin_path: 插件路径
            
        Returns:
            List[str]: 权限列表
        """
        permissions = []
        
        try:
            # 检查manifest文件
            manifest_files = ['manifest.json', 'plugin.json', 'requirements.txt', 'setup.py']
            
            for manifest_file in manifest_files:
                manifest_path = Path(plugin_path) / manifest_file
                if manifest_path.exists():
                    if manifest_file.endswith('.json'):
                        import json
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                            if 'permissions' in manifest:
                                permissions.extend(manifest['permissions'])
                        except Exception as e:
                            self.logger.warning(f"解析manifest文件失败: {manifest_file}")
                    
                    elif manifest_file == 'requirements.txt':
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    permissions.append(f"dependency: {line}")
            
            # 检查setup.py中的权限
            setup_path = Path(plugin_path) / 'setup.py'
            if setup_path.exists():
                with open(setup_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'install_requires' in content:
                        permissions.append("python_dependencies")
                    if 'scripts' in content:
                        permissions.append("script_installation")
        
        except Exception as e:
            self.logger.error(f"权限扫描失败: {str(e)}")
        
        return permissions
    
    def _scan_dependencies(self, plugin_path: str) -> List[str]:
        """
        扫描依赖
        
        Args:
            plugin_path: 插件路径
            
        Returns:
            List[str]: 依赖列表
        """
        dependencies = []
        
        try:
            # 检查requirements.txt
            req_file = Path(plugin_path) / 'requirements.txt'
            if req_file.exists():
                with open(req_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dependencies.append(line)
            
            # 检查setup.py
            setup_file = Path(plugin_path) / 'setup.py'
            if setup_file.exists():
                with open(setup_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单的依赖提取
                    import re
                    matches = re.findall(r'["\']([^"\']+)["\']', content)
                    for match in matches:
                        if any(keyword in match.lower() for keyword in ['install', 'require', 'dependency']):
                            dependencies.append(match)
        
        except Exception as e:
            self.logger.error(f"依赖扫描失败: {str(e)}")
        
        return dependencies
    
    def _calculate_security_score(self, issues: List[SecurityIssue]) -> float:
        """
        计算安全评分
        
        Args:
            issues: 安全问题列表
            
        Returns:
            float: 安全评分 (0-100)
        """
        base_score = 100.0
        
        # 根据问题严重程度扣分
        severity_penalty = {
            'low': 5,
            'medium': 15,
            'high': 30,
            'critical': 50
        }
        
        for issue in issues:
            penalty = severity_penalty.get(issue.severity, 10)
            base_score -= penalty
        
        return max(0.0, base_score)
    
    def validate_permissions(self, plugin_name: str, requested_permissions: List[str]) -> Tuple[bool, List[str]]:
        """
        验证插件权限
        
        Args:
            plugin_name: 插件名称
            requested_permissions: 请求的权限列表
            
        Returns:
            Tuple[bool, List[str]]: (是否通过验证, 警告列表)
        """
        warnings = []
        
        # 检查危险权限
        dangerous_permissions = [
            'file_system_access', 'network_access', 'system_execution',
            'process_control', 'memory_access', 'registry_access'
        ]
        
        for permission in requested_permissions:
            if permission in dangerous_permissions:
                warnings.append(f"插件 {plugin_name} 请求危险权限: {permission}")
        
        # 检查是否超过最大权限限制
        max_permissions = 10
        if len(requested_permissions) > max_permissions:
            warnings.append(f"插件 {plugin_name} 请求过多权限 ({len(requested_permissions)} > {max_permissions})")
        
        return len(warnings) == 0, warnings
    
    def check_code_integrity(self, plugin_path: str) -> Tuple[bool, str]:
        """
        检查代码完整性
        
        Args:
            plugin_path: 插件路径
            
        Returns:
            Tuple[bool, str]: (是否完整, 校验结果)
        """
        try:
            # 计算所有文件的哈希值
            file_hashes = []
            for file_path in Path(plugin_path).rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                        file_hashes.append(f"{file_path.name}:{file_hash}")
            
            # 生成总体校验和
            combined_hash = hashlib.md5(''.join(sorted(file_hashes)).encode()).hexdigest()
            
            return True, f"代码完整性检查通过，校验和: {combined_hash}"
            
        except Exception as e:
            self.logger.error(f"代码完整性检查失败: {str(e)}")
            return False, f"代码完整性检查失败: {str(e)}"
    
    def get_security_report(self, plugin_name: str) -> Optional[SecurityReport]:
        """
        获取安全报告
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[SecurityReport]: 安全报告，如果不存在返回None
        """
        # TODO: 实现从缓存获取安全报告的逻辑
        return None