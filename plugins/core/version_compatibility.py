"""
版本兼容性检查器

负责检查插件版本兼容性，支持语义化版本规范。
提供版本范围匹配和兼容性矩阵功能。

Author: AI Assistant
Date: 2025-11-05
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from packaging import version


@dataclass
class CompatibilityRule:
    """兼容性规则数据类"""
    plugin_name: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    exact_version: Optional[str] = None
    allowed_versions: List[str] = None
    forbidden_versions: List[str] = None


@dataclass
class CompatibilityResult:
    """兼容性检查结果数据类"""
    compatible: bool
    reason: str
    current_version: str
    required_version: str


class VersionCompatibility:
    """版本兼容性检查器类"""
    
    def __init__(self):
        """初始化版本兼容性检查器"""
        self.logger = logging.getLogger(__name__)
        self._compatibility_rules: Dict[str, List[CompatibilityRule]] = {}
        self._version_matrix: Dict[str, Dict[str, bool]] = {}
        
    def add_compatibility_rule(self, rule: CompatibilityRule) -> None:
        """
        添加兼容性规则
        
        Args:
            rule: 兼容性规则
        """
        if rule.plugin_name not in self._compatibility_rules:
            self._compatibility_rules[rule.plugin_name] = []
        
        self._compatibility_rules[rule.plugin_name].append(rule)
        self.logger.info(f"添加兼容性规则: {rule.plugin_name}")
    
    def remove_compatibility_rule(self, plugin_name: str, rule_index: int = 0) -> bool:
        """
        移除兼容性规则
        
        Args:
            plugin_name: 插件名称
            rule_index: 规则索引
            
        Returns:
            bool: 移除成功返回True，否则返回False
        """
        try:
            if plugin_name in self._compatibility_rules and rule_index < len(self._compatibility_rules[plugin_name]):
                removed_rule = self._compatibility_rules[plugin_name].pop(rule_index)
                self.logger.info(f"移除兼容性规则: {removed_rule}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"移除兼容性规则失败: {str(e)}")
            return False
    
    def check_compatibility(self, plugin_name: str, current_version: str, 
                          target_version: str = None) -> CompatibilityResult:
        """
        检查版本兼容性
        
        Args:
            plugin_name: 插件名称
            current_version: 当前版本
            target_version: 目标版本（可选）
            
        Returns:
            CompatibilityResult: 兼容性检查结果
        """
        try:
            self.logger.info(f"检查插件 {plugin_name} 版本兼容性: {current_version}")
            
            if plugin_name not in self._compatibility_rules:
                return CompatibilityResult(
                    compatible=True,
                    reason="没有兼容性规则",
                    current_version=current_version,
                    required_version="任意"
                )
            
            # 验证版本格式
            if not self._is_valid_version(current_version):
                return CompatibilityResult(
                    compatible=False,
                    reason=f"无效的版本格式: {current_version}",
                    current_version=current_version,
                    required_version="未知"
                )
            
            # 检查每个兼容性规则
            for rule in self._compatibility_rules[plugin_name]:
                result = self._check_rule(rule, current_version)
                if not result.compatible:
                    return result
            
            return CompatibilityResult(
                compatible=True,
                reason="版本兼容",
                current_version=current_version,
                required_version="符合规则要求"
            )
            
        except Exception as e:
            self.logger.error(f"版本兼容性检查失败: {str(e)}")
            return CompatibilityResult(
                compatible=False,
                reason=f"检查过程中发生错误: {str(e)}",
                current_version=current_version,
                required_version="未知"
            )
    
    def _check_rule(self, rule: CompatibilityRule, version_str: str) -> CompatibilityResult:
        """
        检查单个兼容性规则
        
        Args:
            rule: 兼容性规则
            version_str: 版本字符串
            
        Returns:
            CompatibilityResult: 兼容性检查结果
        """
        try:
            current = version.parse(version_str)
            
            # 检查精确版本
            if rule.exact_version:
                if version.parse(rule.exact_version) != current:
                    return CompatibilityResult(
                        compatible=False,
                        reason=f"需要精确版本 {rule.exact_version}，但实际为 {version_str}",
                        current_version=version_str,
                        required_version=rule.exact_version
                    )
            
            # 检查最小版本
            if rule.min_version:
                if current < version.parse(rule.min_version):
                    return CompatibilityResult(
                        compatible=False,
                        reason=f"需要版本 >= {rule.min_version}，但实际为 {version_str}",
                        current_version=version_str,
                        required_version=f">= {rule.min_version}"
                    )
            
            # 检查最大版本
            if rule.max_version:
                if current > version.parse(rule.max_version):
                    return CompatibilityResult(
                        compatible=False,
                        reason=f"需要版本 <= {rule.max_version}，但实际为 {version_str}",
                        current_version=version_str,
                        required_version=f"<= {rule.max_version}"
                    )
            
            # 检查允许的版本列表
            if rule.allowed_versions:
                if not any(version.parse(v) == current for v in rule.allowed_versions):
                    return CompatibilityResult(
                        compatible=False,
                        reason=f"版本 {version_str} 不在允许列表中: {rule.allowed_versions}",
                        current_version=version_str,
                        required_version=f"在 {rule.allowed_versions} 中"
                    )
            
            # 检查禁止的版本列表
            if rule.forbidden_versions:
                if any(version.parse(v) == current for v in rule.forbidden_versions):
                    return CompatibilityResult(
                        compatible=False,
                        reason=f"版本 {version_str} 在禁止列表中: {rule.forbidden_versions}",
                        current_version=version_str,
                        required_version=f"不在 {rule.forbidden_versions} 中"
                    )
            
            return CompatibilityResult(
                compatible=True,
                reason="符合兼容性规则",
                current_version=version_str,
                required_version="符合规则要求"
            )
            
        except Exception as e:
            return CompatibilityResult(
                compatible=False,
                reason=f"规则检查失败: {str(e)}",
                current_version=version_str,
                required_version="未知"
            )
    
    def parse_version_spec(self, spec: str) -> Tuple[str, str]:
        """
        解析版本规范
        
        Args:
            spec: 版本规范字符串（如 ">=1.0.0", "~1.2.3", "^1.2.0"）
            
        Returns:
            Tuple[str, str]: (操作符, 版本号)
        """
        # 匹配版本规范的正则表达式
        patterns = [
            (r'^>=\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '>='),
            (r'^<=\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '<='),
            (r'^>\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '>'),
            (r'^<\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '<'),
            (r'^==\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '=='),
            (r'^\^\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '^'),
            (r'^~\s*([0-9]+\.[0-9]+\.[0-9]+.*)$', '~'),
            (r'^([0-9]+\.[0-9]+\.[0-9]+.*)$', '==')
        ]
        
        for pattern, operator in patterns:
            match = re.match(pattern, spec.strip())
            if match:
                return operator, match.group(1)
        
        # 如果没有匹配，默认为精确匹配
        return '==', spec
    
    def match_version_spec(self, version_str: str, spec: str) -> bool:
        """
        检查版本是否匹配规范
        
        Args:
            version_str: 版本字符串
            spec: 版本规范
            
        Returns:
            bool: 匹配返回True，否则返回False
        """
        try:
            operator, target_version = self.parse_version_spec(spec)
            current = version.parse(version_str)
            target = version.parse(target_version)
            
            if operator == '>=':
                return current >= target
            elif operator == '<=':
                return current <= target
            elif operator == '>':
                return current > target
            elif operator == '<':
                return current < target
            elif operator == '==':
                return current == target
            elif operator == '^':
                # 兼容性版本（major版本兼容）
                return current.major == target.major and current >= target
            elif operator == '~':
                # 近似版本（minor版本兼容）
                return (current.major == target.major and 
                       current.minor == target.minor and 
                       current >= target)
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"版本规范匹配失败: {str(e)}")
            return False
    
    def _is_valid_version(self, version_str: str) -> bool:
        """
        验证版本字符串格式
        
        Args:
            version_str: 版本字符串
            
        Returns:
            bool: 有效返回True，否则返回False
        """
        try:
            version.parse(version_str)
            return True
        except Exception:
            return False
    
    def get_compatible_versions(self, plugin_name: str, all_versions: List[str]) -> List[str]:
        """
        获取兼容的版本列表
        
        Args:
            plugin_name: 插件名称
            all_versions: 所有可用版本列表
            
        Returns:
            List[str]: 兼容的版本列表
        """
        compatible_versions = []
        
        if plugin_name not in self._compatibility_rules:
            return all_versions
        
        for version_str in all_versions:
            if self.check_compatibility(plugin_name, version_str).compatible:
                compatible_versions.append(version_str)
        
        return compatible_versions
    
    def get_latest_compatible_version(self, plugin_name: str, all_versions: List[str]) -> Optional[str]:
        """
        获取最新兼容版本
        
        Args:
            plugin_name: 插件名称
            all_versions: 所有可用版本列表
            
        Returns:
            Optional[str]: 最新兼容版本，如果不存在返回None
        """
        compatible_versions = self.get_compatible_versions(plugin_name, all_versions)
        
        if not compatible_versions:
            return None
        
        # 按版本号排序，返回最新版本
        sorted_versions = sorted(compatible_versions, key=lambda v: version.parse(v), reverse=True)
        return sorted_versions[0]