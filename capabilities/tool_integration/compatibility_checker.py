"""
兼容性检查器模块
提供工具兼容性检查，包括系统兼容性、版本兼容性等
"""

import os
import sys
import platform
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import json
from enum import Enum

logger = logging.getLogger(__name__)

class CompatibilityLevel(Enum):
    """兼容性级别枚举"""
    COMPATIBLE = "compatible"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"

class CompatibilityIssue:
    """兼容性问题"""
    
    def __init__(self, level: CompatibilityLevel, message: str, component: str, details: Dict[str, Any] = None):
        self.level = level
        self.message = message
        self.component = component
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "level": self.level.value,
            "message": self.message,
            "component": self.component,
            "details": self.details
        }

class CompatibilityResult:
    """兼容性检查结果"""
    
    def __init__(self, tool_id: str, tool_name: str):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.issues: List[CompatibilityIssue] = []
        self.compatibility_score: float = 1.0  # 兼容性评分，0-1之间
        self.overall_level: CompatibilityLevel = CompatibilityLevel.COMPATIBLE
    
    def add_issue(self, issue: CompatibilityIssue):
        """添加问题"""
        self.issues.append(issue)
        # 根据问题严重程度更新整体兼容性级别
        if issue.level == CompatibilityLevel.ERROR and self.overall_level != CompatibilityLevel.ERROR:
            self.overall_level = CompatibilityLevel.ERROR
        elif issue.level == CompatibilityLevel.WARNING and self.overall_level == CompatibilityLevel.COMPATIBLE:
            self.overall_level = CompatibilityLevel.WARNING
    
    def calculate_score(self):
        """计算兼容性评分"""
        if not self.issues:
            self.compatibility_score = 1.0
            return
        
        # 根据问题严重程度计算分数
        error_count = sum(1 for issue in self.issues if issue.level == CompatibilityLevel.ERROR)
        warning_count = sum(1 for issue in self.issues if issue.level == CompatibilityLevel.WARNING)
        total_issues = len(self.issues)
        
        # 权重：错误问题比警告问题更严重
        penalty = (error_count * 0.5 + warning_count * 0.2) / total_issues if total_issues > 0 else 0
        self.compatibility_score = max(0.0, 1.0 - penalty)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        self.calculate_score()
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "compatibility_score": self.compatibility_score,
            "overall_level": self.overall_level.value,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
            "error_count": sum(1 for issue in self.issues if issue.level == CompatibilityLevel.ERROR),
            "warning_count": sum(1 for issue in self.issues if issue.level == CompatibilityLevel.WARNING)
        }

class SystemCompatibilityChecker:
    """系统兼容性检查器"""
    
    def __init__(self):
        self.system_info = self._get_system_info()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "platform": platform.system().lower(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "processor": platform.processor()
        }
    
    def check_os_compatibility(self, tool_requirements: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查操作系统兼容性"""
        issues = []
        required_os = tool_requirements.get("operating_systems", [])
        current_os = self.system_info["platform"]
        
        if required_os and current_os not in required_os:
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.ERROR,
                message=f"工具不支持当前操作系统: {current_os}",
                component="operating_system",
                details={
                    "current_os": current_os,
                    "supported_os": required_os
                }
            ))
        
        return issues
    
    def check_architecture_compatibility(self, tool_requirements: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查架构兼容性"""
        issues = []
        required_arch = tool_requirements.get("architectures", [])
        current_arch = self.system_info["architecture"]
        
        if required_arch and current_arch not in required_arch:
            # 架构不匹配通常是警告，因为许多工具是跨架构的
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message=f"工具可能不支持当前系统架构: {current_arch}",
                component="architecture",
                details={
                    "current_architecture": current_arch,
                    "supported_architectures": required_arch
                }
            ))
        
        return issues
    
    def check_python_compatibility(self, tool_requirements: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查Python兼容性"""
        issues = []
        required_python = tool_requirements.get("python_versions", "")
        current_python = self.system_info["python_version"]
        
        if required_python:
            # 简单的版本范围检查（简化实现）
            if not self._check_version_range(current_python, required_python):
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.ERROR,
                    message=f"Python版本不兼容: 当前 {current_python}, 需要 {required_python}",
                    component="python",
                    details={
                        "current_version": current_python,
                        "required_version": required_python
                    }
                ))
        
        return issues
    
    def _check_version_range(self, current_version: str, required_range: str) -> bool:
        """检查版本是否在要求范围内"""
        # 简化实现，实际使用时需要更复杂的版本比较
        try:
            from packaging import version
            from packaging.specifiers import SpecifierSet
            
            spec = SpecifierSet(required_range)
            return spec.contains(version.parse(current_version))
        except ImportError:
            # 如果packaging不可用，使用简单比较
            logger.warning("packaging模块不可用，使用简化的版本检查")
            # 移除版本号中的非数字字符
            current_clean = re.sub(r'[^\d.]', '', current_version)
            # 这里只检查主要版本号作为示例
            current_major = current_clean.split('.')[0]
            # 从要求范围中提取主要版本号（简化）
            required_major = re.findall(r'\d+', required_range)
            if required_major:
                return current_major == required_major[0]
            return True
    
    def check_system_dependencies(self, tool_requirements: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查系统依赖"""
        issues = []
        system_deps = tool_requirements.get("system_dependencies", [])
        
        for dep in system_deps:
            if not self._check_system_dependency(dep):
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.WARNING,
                    message=f"系统依赖不可用: {dep}",
                    component="system_dependency",
                    details={"dependency": dep}
                ))
        
        return issues
    
    def _check_system_dependency(self, dependency: str) -> bool:
        """检查系统依赖是否可用"""
        import shutil
        return shutil.which(dependency) is not None

class VersionCompatibilityChecker:
    """版本兼容性检查器"""
    
    def check_tool_version(self, tool_metadata: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查工具版本兼容性"""
        issues = []
        
        # 检查工具版本状态
        status = tool_metadata.get("status", "")
        if status == "deprecated":
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message="此工具版本已弃用，建议升级",
                component="tool_version",
                details={"status": status}
            ))
        elif status == "experimental":
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message="此工具版本为实验性，可能不稳定",
                component="tool_version",
                details={"status": status}
            ))
        
        # 检查版本格式
        version = tool_metadata.get("version", "")
        if not self._is_valid_version(version):
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message=f"工具版本格式可能无效: {version}",
                component="tool_version",
                details={"version": version}
            ))
        
        return issues
    
    def _is_valid_version(self, version: str) -> bool:
        """检查版本号格式是否有效"""
        # 简单的语义化版本检查
        pattern = r'^\d+\.\d+\.\d+([+-][a-zA-Z0-9.-]+)?$'
        return re.match(pattern, version) is not None
    
    def check_dependency_versions(self, tool_metadata: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查依赖版本兼容性"""
        issues = []
        dependencies = tool_metadata.get("dependencies", [])
        
        for dep in dependencies:
            # 这里可以添加更复杂的依赖版本冲突检测
            # 简化实现，只检查基本格式
            if not self._is_valid_dependency_spec(dep):
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.WARNING,
                    message=f"依赖规范格式可能无效: {dep}",
                    component="dependency_version",
                    details={"dependency": dep}
                ))
        
        return issues
    
    def _is_valid_dependency_spec(self, dependency_spec: str) -> bool:
        """检查依赖规范格式"""
        # 简化实现，检查常见的依赖规范格式
        patterns = [
            r'^[a-zA-Z0-9_-]+==\d+\.\d+\.\d+$',
            r'^[a-zA-Z0-9_-]+>=\d+\.\d+\.\d+$',
            r'^[a-zA-Z0-9_-]+<=\d+\.\d+\.\d+$',
            r'^[a-zA-Z0-9_-]+~=\d+\.\d+\.\d+$'
        ]
        
        return any(re.match(pattern, dependency_spec) for pattern in patterns)

class SecurityCompatibilityChecker:
    """安全兼容性检查器"""
    
    def check_security_compatibility(self, tool_metadata: Dict[str, Any]) -> List[CompatibilityIssue]:
        """检查安全兼容性"""
        issues = []
        
        # 检查权限要求
        permissions = tool_metadata.get("required_permissions", [])
        for perm in permissions:
            if self._is_dangerous_permission(perm):
                issues.append(CompatibilityIssue(
                    level=CompatibilityLevel.WARNING,
                    message=f"工具要求潜在危险的权限: {perm}",
                    component="security",
                    details={"permission": perm}
                ))
        
        # 检查网络访问
        if tool_metadata.get("network_access", False):
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message="工具需要网络访问权限",
                component="security",
                details={"network_access": True}
            ))
        
        # 检查文件系统访问
        if tool_metadata.get("filesystem_access", False):
            issues.append(CompatibilityIssue(
                level=CompatibilityLevel.WARNING,
                message="工具需要文件系统访问权限",
                component="security",
                details={"filesystem_access": True}
            ))
        
        return issues
    
    def _is_dangerous_permission(self, permission: str) -> bool:
        """检查是否为危险权限"""
        dangerous_permissions = [
            "admin", "root", "sudo", "system", "registry",
            "all_files", "home_directory", "personal_data"
        ]
        
        return any(dangerous in permission.lower() for dangerous in dangerous_permissions)

class CompatibilityChecker:
    """兼容性检查器"""
    
    def __init__(self):
        self.system_checker = SystemCompatibilityChecker()
        self.version_checker = VersionCompatibilityChecker()
        self.security_checker = SecurityCompatibilityChecker()
    
    def check_tool_compatibility(self, tool_metadata: Dict[str, Any]) -> CompatibilityResult:
        """检查工具兼容性"""
        tool_id = tool_metadata.get("tool_id", "unknown")
        tool_name = tool_metadata.get("name", "unknown")
        
        result = CompatibilityResult(tool_id, tool_name)
        
        # 系统兼容性检查
        requirements = tool_metadata.get("requirements", {})
        result.issues.extend(self.system_checker.check_os_compatibility(requirements))
        result.issues.extend(self.system_checker.check_architecture_compatibility(requirements))
        result.issues.extend(self.system_checker.check_python_compatibility(requirements))
        result.issues.extend(self.system_checker.check_system_dependencies(requirements))
        
        # 版本兼容性检查
        result.issues.extend(self.version_checker.check_tool_version(tool_metadata))
        result.issues.extend(self.version_checker.check_dependency_versions(tool_metadata))
        
        # 安全兼容性检查
        result.issues.extend(self.security_checker.check_security_compatibility(tool_metadata))
        
        return result
    
    def batch_check_compatibility(self, tools_metadata: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量检查兼容性"""
        results = []
        compatible_count = 0
        warning_count = 0
        error_count = 0
        
        for tool_metadata in tools_metadata:
            result = self.check_tool_compatibility(tool_metadata)
            results.append(result.to_dict())
            
            if result.overall_level == CompatibilityLevel.COMPATIBLE:
                compatible_count += 1
            elif result.overall_level == CompatibilityLevel.WARNING:
                warning_count += 1
            elif result.overall_level == CompatibilityLevel.ERROR:
                error_count += 1
        
        return {
            "results": results,
            "summary": {
                "total_tools": len(tools_metadata),
                "compatible_tools": compatible_count,
                "warning_tools": warning_count,
                "error_tools": error_count,
                "compatibility_rate": compatible_count / len(tools_metadata) if tools_metadata else 0
            }
        }

# 使用示例
def demo_compatibility_checker():
    """演示兼容性检查器的使用"""
    checker = CompatibilityChecker()
    
    # 示例工具元数据
    tool_metadata = {
        "tool_id": "tool_123",
        "name": "图像处理器",
        "version": "1.2.3",
        "status": "stable",
        "requirements": {
            "operating_systems": ["windows", "linux"],
            "python_versions": ">=3.8",
            "system_dependencies": ["ffmpeg", "imagemagick"]
        },
        "dependencies": ["numpy==1.21.0", "pillow>=8.0.0"],
        "required_permissions": ["file_system_access", "network_access"],
        "network_access": True,
        "filesystem_access": True
    }
    
    result = checker.check_tool_compatibility(tool_metadata)
    print("兼容性检查结果:", json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demo_compatibility_checker()

