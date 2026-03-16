"""
依赖管理器模块
提供工具依赖关系的管理和解析功能
"""

import os
import sys
import importlib
import pkg_resources
import logging
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import json
import hashlib
import platform
from enum import Enum
import asyncio
import aiohttp
import shutil

logger = logging.getLogger(__name__)

class DependencyStatus(Enum):
    """依赖状态枚举"""
    INSTALLED = "installed"
    MISSING = "missing"
    OUTDATED = "outdated"
    CONFLICT = "conflict"
    INCOMPATIBLE = "incompatible"

class PackageManager(Enum):
    """包管理器枚举"""
    PIP = "pip"
    CONDA = "conda"
    NPM = "npm"
    SYSTEM = "system"
    CUSTOM = "custom"

@dataclass
class Dependency:
    """依赖项"""
    name: str
    version_spec: str
    package_manager: PackageManager
    required: bool = True
    description: str = ""
    checksum: Optional[str] = None
    download_url: Optional[str] = None
    install_script: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version_spec": self.version_spec,
            "package_manager": self.package_manager.value,
            "required": self.required,
            "description": self.description,
            "checksum": self.checksum,
            "download_url": self.download_url,
            "install_script": self.install_script
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Dependency':
        """从字典创建实例"""
        data = data.copy()
        data['package_manager'] = PackageManager(data['package_manager'])
        return cls(**data)

@dataclass
class DependencyResolution:
    """依赖解析结果"""
    dependency: Dependency
    status: DependencyStatus
    installed_version: Optional[str] = None
    required_version: Optional[str] = None
    message: Optional[str] = None
    resolution_action: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dependency": self.dependency.to_dict(),
            "status": self.status.value,
            "installed_version": self.installed_version,
            "required_version": self.required_version,
            "message": self.message,
            "resolution_action": self.resolution_action
        }

class DependencyResolver:
    """依赖解析器"""
    
    def __init__(self):
        self.package_managers = {
            PackageManager.PIP: PipPackageManager(),
            PackageManager.CONDA: CondaPackageManager(),
            PackageManager.NPM: NpmPackageManager(),
            PackageManager.SYSTEM: SystemPackageManager()
        }
    
    async def resolve_dependencies(self, dependencies: List[Dependency]) -> List[DependencyResolution]:
        """解析依赖关系"""
        resolutions = []
        
        for dependency in dependencies:
            try:
                # 获取对应的包管理器
                package_manager = self.package_managers.get(dependency.package_manager)
                if not package_manager:
                    resolution = DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"不支持的包管理器: {dependency.package_manager.value}"
                    )
                    resolutions.append(resolution)
                    continue
                
                # 检查依赖状态
                resolution = await package_manager.check_dependency(dependency)
                resolutions.append(resolution)
                
            except Exception as e:
                logger.error(f"依赖解析失败 {dependency.name}: {e}")
                resolution = DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"解析失败: {str(e)}"
                )
                resolutions.append(resolution)
        
        return resolutions
    
    async def install_dependencies(self, dependencies: List[Dependency]) -> List[DependencyResolution]:
        """安装依赖项"""
        installations = []
        
        for dependency in dependencies:
            try:
                package_manager = self.package_managers.get(dependency.package_manager)
                if not package_manager:
                    result = DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"不支持的包管理器: {dependency.package_manager.value}"
                    )
                    installations.append(result)
                    continue
                
                # 安装依赖
                result = await package_manager.install_dependency(dependency)
                installations.append(result)
                
            except Exception as e:
                logger.error(f"依赖安装失败 {dependency.name}: {e}")
                result = DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"安装失败: {str(e)}"
                )
                installations.append(result)
        
        return installations
    
    def validate_dependency_graph(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """验证依赖图"""
        issues = []
        warnings = []
        
        # 检查重复依赖
        dependency_names = [dep.name for dep in dependencies]
        duplicates = {name for name in dependency_names if dependency_names.count(name) > 1}
        
        if duplicates:
            issues.append(f"发现重复依赖: {', '.join(duplicates)}")
        
        # 检查版本冲突（简化实现）
        for dep1 in dependencies:
            for dep2 in dependencies:
                if (dep1.name == dep2.name and 
                    dep1.version_spec != dep2.version_spec and
                    dep1.required and dep2.required):
                    issues.append(f"版本冲突: {dep1.name} ({dep1.version_spec} vs {dep2.version_spec})")
        
        # 检查系统兼容性
        system = platform.system().lower()
        for dep in dependencies:
            if dep.package_manager == PackageManager.SYSTEM:
                if system not in ["linux", "windows", "darwin"]:
                    warnings.append(f"系统包管理器在 {system} 上可能不受支持")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "dependency_count": len(dependencies)
        }

class BasePackageManager:
    """基础包管理器"""
    
    async def check_dependency(self, dependency: Dependency) -> DependencyResolution:
        """检查依赖状态"""
        raise NotImplementedError("子类必须实现此方法")
    
    async def install_dependency(self, dependency: Dependency) -> DependencyResolution:
        """安装依赖"""
        raise NotImplementedError("子类必须实现此方法")
    
    def _parse_version_spec(self, version_spec: str) -> Tuple[str, str]:
        """解析版本规范"""
        # 简化实现，实际使用时需要更复杂的版本解析
        if version_spec.startswith("=="):
            return "exact", version_spec[2:]
        elif version_spec.startswith(">="):
            return "minimum", version_spec[2:]
        elif version_spec.startswith("~="):
            return "compatible", version_spec[2:]
        else:
            return "any", version_spec

class PipPackageManager(BasePackageManager):
    """Pip包管理器"""
    
    async def check_dependency(self, dependency: Dependency) -> DependencyResolution:
        """检查Pip依赖状态"""
        try:
            # 尝试导入包
            try:
                module = importlib.import_module(dependency.name.replace('-', '_'))
                installed_version = getattr(module, '__version__', 'unknown')
            except ImportError:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"包未安装: {dependency.name}"
                )
            
            # 检查版本兼容性
            if installed_version != 'unknown':
                try:
                    # 使用pkg_resources检查版本要求
                    requirement = pkg_resources.Requirement.parse(f"{dependency.name}{dependency.version_spec}")
                    if installed_version in requirement:
                        return DependencyResolution(
                            dependency=dependency,
                            status=DependencyStatus.INSTALLED,
                            installed_version=installed_version,
                            required_version=dependency.version_spec,
                            message=f"依赖已安装且版本兼容: {installed_version}"
                        )
                    else:
                        return DependencyResolution(
                            dependency=dependency,
                            status=DependencyStatus.OUTDATED,
                            installed_version=installed_version,
                            required_version=dependency.version_spec,
                            message=f"版本不兼容: 已安装 {installed_version}, 需要 {dependency.version_spec}",
                            resolution_action="upgrade"
                        )
                except Exception:
                    # 如果版本检查失败，假设兼容
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=installed_version,
                        required_version=dependency.version_spec,
                        message=f"依赖已安装 (版本检查失败): {installed_version}"
                    )
            else:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.INSTALLED,
                    installed_version=installed_version,
                    required_version=dependency.version_spec,
                    message="依赖已安装 (版本未知)"
                )
                
        except Exception as e:
            logger.error(f"Pip依赖检查失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"检查失败: {str(e)}"
            )
    
    async def install_dependency(self, dependency: Dependency) -> DependencyResolution:
        """安装Pip依赖"""
        try:
            # 构建安装命令
            package_spec = f"{dependency.name}{dependency.version_spec}"
            command = [sys.executable, "-m", "pip", "install", package_spec]
            
            # 执行安装
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 验证安装
                check_result = await self.check_dependency(dependency)
                if check_result.status == DependencyStatus.INSTALLED:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=check_result.installed_version,
                        message=f"依赖安装成功: {dependency.name}"
                    )
                else:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"安装后验证失败: {check_result.message}"
                    )
            else:
                error_output = stderr.decode('utf-8') if stderr else "未知错误"
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"安装失败: {error_output}"
                )
                
        except Exception as e:
            logger.error(f"Pip依赖安装失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"安装异常: {str(e)}"
            )

class CondaPackageManager(BasePackageManager):
    """Conda包管理器"""
    
    async def check_dependency(self, dependency: Dependency) -> DependencyResolution:
        """检查Conda依赖状态"""
        try:
            # 检查conda是否可用
            conda_path = shutil.which("conda")
            if not conda_path:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.INCOMPATIBLE,
                    message="Conda不可用"
                )
            
            # 检查包是否已安装
            command = ["conda", "list", dependency.name, "--json"]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                packages_data = json.loads(stdout.decode('utf-8'))
                if packages_data:
                    package_info = packages_data[0]
                    installed_version = package_info.get('version', 'unknown')
                    
                    # 简化版本检查
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=installed_version,
                        required_version=dependency.version_spec,
                        message=f"Conda包已安装: {installed_version}"
                    )
                else:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.MISSING,
                        message=f"Conda包未安装: {dependency.name}"
                    )
            else:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"Conda检查失败: {stderr.decode('utf-8') if stderr else '未知错误'}"
                )
                
        except Exception as e:
            logger.error(f"Conda依赖检查失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"检查失败: {str(e)}"
            )
    
    async def install_dependency(self, dependency: Dependency) -> DependencyResolution:
        """安装Conda依赖"""
        try:
            # 构建安装命令
            package_spec = f"{dependency.name}{dependency.version_spec}"
            command = ["conda", "install", "-y", package_spec]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 验证安装
                check_result = await self.check_dependency(dependency)
                if check_result.status == DependencyStatus.INSTALLED:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=check_result.installed_version,
                        message=f"Conda依赖安装成功: {dependency.name}"
                    )
                else:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"安装后验证失败: {check_result.message}"
                    )
            else:
                error_output = stderr.decode('utf-8') if stderr else "未知错误"
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"Conda安装失败: {error_output}"
                )
                
        except Exception as e:
            logger.error(f"Conda依赖安装失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"安装异常: {str(e)}"
            )

class NpmPackageManager(BasePackageManager):
    """NPM包管理器"""
    
    async def check_dependency(self, dependency: Dependency) -> DependencyResolution:
        """检查NPM依赖状态"""
        try:
            # 检查npm是否可用
            npm_path = shutil.which("npm")
            if not npm_path:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.INCOMPATIBLE,
                    message="NPM不可用"
                )
            
            # 检查包是否已安装
            command = ["npm", "list", dependency.name, "--json", "--depth=0"]
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                try:
                    package_data = json.loads(stdout.decode('utf-8'))
                    dependencies = package_data.get('dependencies', {})
                    
                    if dependency.name in dependencies:
                        package_info = dependencies[dependency.name]
                        installed_version = package_info.get('version', 'unknown')
                        
                        return DependencyResolution(
                            dependency=dependency,
                            status=DependencyStatus.INSTALLED,
                            installed_version=installed_version,
                            required_version=dependency.version_spec,
                            message=f"NPM包已安装: {installed_version}"
                        )
                    else:
                        return DependencyResolution(
                            dependency=dependency,
                            status=DependencyStatus.MISSING,
                            message=f"NPM包未安装: {dependency.name}"
                        )
                except json.JSONDecodeError:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.MISSING,
                        message="NPM输出解析失败"
                    )
            else:
                # 包未安装时npm list会返回非零退出码
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"NPM包未安装: {dependency.name}"
                )
                
        except Exception as e:
            logger.error(f"NPM依赖检查失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"检查失败: {str(e)}"
            )
    
    async def install_dependency(self, dependency: Dependency) -> DependencyResolution:
        """安装NPM依赖"""
        try:
            # 构建安装命令
            package_spec = f"{dependency.name}{dependency.version_spec}"
            command = ["npm", "install", package_spec]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 验证安装
                check_result = await self.check_dependency(dependency)
                if check_result.status == DependencyStatus.INSTALLED:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=check_result.installed_version,
                        message=f"NPM依赖安装成功: {dependency.name}"
                    )
                else:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"安装后验证失败: {check_result.message}"
                    )
            else:
                error_output = stderr.decode('utf-8') if stderr else "未知错误"
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"NPM安装失败: {error_output}"
                )
                
        except Exception as e:
            logger.error(f"NPM依赖安装失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"安装异常: {str(e)}"
            )

class SystemPackageManager(BasePackageManager):
    """系统包管理器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.manager_commands = {
            "linux": {
                "apt": ["apt", "install", "-y"],
                "yum": ["yum", "install", "-y"],
                "dnf": ["dnf", "install", "-y"],
                "pacman": ["pacman", "-S", "--noconfirm"],
                "zypper": ["zypper", "install", "-y"]
            },
            "darwin": {
                "brew": ["brew", "install"]
            },
            "windows": {
                "choco": ["choco", "install", "-y"],
                "scoop": ["scoop", "install"]
            }
        }
    
    async def check_dependency(self, dependency: Dependency) -> DependencyResolution:
        """检查系统依赖状态"""
        try:
            # 检查命令是否存在
            command_path = shutil.which(dependency.name)
            if command_path:
                # 尝试获取版本信息
                try:
                    process = await asyncio.create_subprocess_exec(
                        dependency.name, "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    version_output = stdout.decode('utf-8') if stdout else stderr.decode('utf-8')
                    # 提取版本号（简化实现）
                    version_match = None
                    if version_output:
                        import re
                        version_pattern = r'(\d+\.\d+\.\d+|\d+\.\d+)'
                        matches = re.findall(version_pattern, version_output)
                        if matches:
                            version_match = matches[0]
                    
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=version_match or "unknown",
                        message=f"系统命令可用: {dependency.name}"
                    )
                except Exception:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version="unknown",
                        message=f"系统命令可用 (版本未知): {dependency.name}"
                    )
            else:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"系统命令不可用: {dependency.name}"
                )
                
        except Exception as e:
            logger.error(f"系统依赖检查失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"检查失败: {str(e)}"
            )
    
    async def install_dependency(self, dependency: Dependency) -> DependencyResolution:
        """安装系统依赖"""
        try:
            # 确定可用的包管理器
            available_managers = self.manager_commands.get(self.system, {})
            manager_name = None
            manager_command = None
            
            for name, command in available_managers.items():
                if shutil.which(name):
                    manager_name = name
                    manager_command = command
                    break
            
            if not manager_name:
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.INCOMPATIBLE,
                    message=f"系统 {self.system} 上没有可用的包管理器"
                )
            
            # 执行安装
            install_command = manager_command + [dependency.name]
            process = await asyncio.create_subprocess_exec(
                *install_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # 验证安装
                check_result = await self.check_dependency(dependency)
                if check_result.status == DependencyStatus.INSTALLED:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INSTALLED,
                        installed_version=check_result.installed_version,
                        message=f"系统依赖安装成功: {dependency.name} (使用 {manager_name})"
                    )
                else:
                    return DependencyResolution(
                        dependency=dependency,
                        status=DependencyStatus.INCOMPATIBLE,
                        message=f"安装后验证失败: {check_result.message}"
                    )
            else:
                error_output = stderr.decode('utf-8') if stderr else "未知错误"
                return DependencyResolution(
                    dependency=dependency,
                    status=DependencyStatus.MISSING,
                    message=f"系统安装失败 ({manager_name}): {error_output}"
                )
                
        except Exception as e:
            logger.error(f"系统依赖安装失败 {dependency.name}: {e}")
            return DependencyResolution(
                dependency=dependency,
                status=DependencyStatus.MISSING,
                message=f"安装异常: {str(e)}"
            )

class DependencyManager:
    """依赖管理器"""
    
    def __init__(self, cache_dir: str = "dependency_cache"):
        self.resolver = DependencyResolver()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.dependency_cache: Dict[str, List[DependencyResolution]] = {}
    
    async def ensure_dependencies(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """确保所有依赖都已安装"""
        # 解析依赖状态
        resolutions = await self.resolver.resolve_dependencies(dependencies)
        
        # 筛选需要安装的依赖
        missing_dependencies = []
        for resolution in resolutions:
            if resolution.status in [DependencyStatus.MISSING, DependencyStatus.OUTDATED]:
                missing_dependencies.append(resolution.dependency)
        
        # 安装缺失的依赖
        installation_results = []
        if missing_dependencies:
            installation_results = await self.resolver.install_dependencies(missing_dependencies)
        
        # 合并结果
        final_resolutions = []
        installed_map = {result.dependency.name: result for result in installation_results}
        
        for resolution in resolutions:
            if resolution.dependency.name in installed_map:
                final_resolutions.append(installed_map[resolution.dependency.name])
            else:
                final_resolutions.append(resolution)
        
        # 统计结果
        status_counts = {}
        for resolution in final_resolutions:
            status = resolution.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 验证依赖图
        validation = self.resolver.validate_dependency_graph(dependencies)
        
        return {
            "success": all(r.status == DependencyStatus.INSTALLED for r in final_resolutions if r.dependency.required),
            "resolutions": [r.to_dict() for r in final_resolutions],
            "status_counts": status_counts,
            "validation": validation,
            "total_dependencies": len(dependencies),
            "installed_count": status_counts.get(DependencyStatus.INSTALLED.value, 0),
            "missing_count": status_counts.get(DependencyStatus.MISSING.value, 0)
        }
    
    async def create_requirements_file(self, dependencies: List[Dependency], 
                                     file_path: str) -> Dict[str, Any]:
        """创建需求文件"""
        try:
            requirements = {}
            
            for dependency in dependencies:
                if dependency.package_manager == PackageManager.PIP:
                    requirements[dependency.name] = dependency.version_spec
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for name, version_spec in requirements.items():
                    f.write(f"{name}{version_spec}\n")
            
            return {
                "success": True,
                "file_path": file_path,
                "dependency_count": len(requirements),
                "message": f"需求文件已创建: {file_path}"
            }
            
        except Exception as e:
            logger.error(f"需求文件创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def export_dependency_report(self, dependencies: List[Dependency], 
                                     report_path: str) -> Dict[str, Any]:
        """导出依赖报告"""
        try:
            # 解析依赖状态
            resolutions = await self.resolver.resolve_dependencies(dependencies)
            
            # 生成报告数据
            report_data = {
                "generated_at": __import__('datetime').datetime.now().isoformat(),
                "system_info": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "system": platform.system(),
                    "machine": platform.machine()
                },
                "dependencies": [dep.to_dict() for dep in dependencies],
                "resolutions": [res.to_dict() for res in resolutions],
                "summary": {
                    "total": len(dependencies),
                    "installed": sum(1 for r in resolutions if r.status == DependencyStatus.INSTALLED),
                    "missing": sum(1 for r in resolutions if r.status == DependencyStatus.MISSING),
                    "outdated": sum(1 for r in resolutions if r.status == DependencyStatus.OUTDATED),
                    "incompatible": sum(1 for r in resolutions if r.status == DependencyStatus.INCOMPATIBLE)
                }
            }
            
            # 写入报告文件
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "report_path": report_path,
                "summary": report_data["summary"],
                "message": f"依赖报告已导出: {report_path}"
            }
            
        except Exception as e:
            logger.error(f"依赖报告导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_cache(self) -> Dict[str, Any]:
        """清理缓存"""
        try:
            cache_files = list(self.cache_dir.glob("*"))
            for cache_file in cache_files:
                if cache_file.is_file():
                    cache_file.unlink()
            
            self.dependency_cache.clear()
            
            return {
                "success": True,
                "cleared_files": len(cache_files),
                "message": "依赖缓存已清理"
            }
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def check_system_compatibility(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """检查系统兼容性"""
        system_info = {
            "platform": platform.system().lower(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        }
        
        compatibility_issues = []
        compatible_dependencies = []
        
        for dependency in dependencies:
            # 检查包管理器兼容性
            if dependency.package_manager == PackageManager.SYSTEM:
                if system_info["platform"] == "windows" and not any(
                    manager in ["choco", "scoop"] for manager in 
                    self.resolver.package_managers[PackageManager.SYSTEM].manager_commands.get("windows", {})
                ):
                    compatibility_issues.append(f"{dependency.name}: Windows系统包管理器支持有限")
                elif system_info["platform"] == "darwin" and not any(
                    manager in ["brew"] for manager in
                    self.resolver.package_managers[PackageManager.SYSTEM].manager_commands.get("darwin", {})
                ):
                    compatibility_issues.append(f"{dependency.name}: macOS需要Homebrew")
                else:
                    compatible_dependencies.append(dependency)
            else:
                compatible_dependencies.append(dependency)
        
        return {
            "system_info": system_info,
            "compatible_dependencies": len(compatible_dependencies),
            "total_dependencies": len(dependencies),
            "compatibility_issues": compatibility_issues,
            "compatibility_score": len(compatible_dependencies) / len(dependencies) if dependencies else 1.0
        }

# 使用示例
async def demo_dependency_manager():
    """演示依赖管理器的使用"""
    manager = DependencyManager()
    
    # 定义依赖项
    dependencies = [
        Dependency(
            name="requests",
            version_spec=">=2.25.0",
            package_manager=PackageManager.PIP,
            description="HTTP库"
        ),
        Dependency(
            name="numpy",
            version_spec="==1.21.0",
            package_manager=PackageManager.PIP,
            description="数值计算库"
        ),
        Dependency(
            name="git",
            version_spec="",
            package_manager=PackageManager.SYSTEM,
            description="版本控制系统"
        )
    ]
    
    # 确保依赖安装
    result = await manager.ensure_dependencies(dependencies)
    print("依赖安装结果:", json.dumps(result, indent=2, ensure_ascii=False))
    
    # 导出依赖报告
    report_result = await manager.export_dependency_report(dependencies, "dependency_report.json")
    print("依赖报告:", report_result)
    
    # 检查系统兼容性
    compatibility = await manager.check_system_compatibility(dependencies)
    print("系统兼容性:", compatibility)

if __name__ == "__main__":
    asyncio.run(demo_dependency_manager())

