"""
自定义工具集成模块
提供用户自定义工具的集成和管理功能
"""

import os
import sys
import importlib
import inspect
import logging
import tempfile
import json
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass
import hashlib
import zipfile
import shutil

logger = logging.getLogger(__name__)

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    version: str
    description: str
    author: str
    category: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requirements: List[str]
    entry_point: str

class CustomTool:
    """自定义工具基类"""
    
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
        self.loaded = False
        self.function = None
    
    def load(self) -> bool:
        """加载工具"""
        try:
            # 这里应该实现动态加载工具的逻辑
            # 简化实现
            self.loaded = True
            logger.info(f"工具加载成功: {self.metadata.name}")
            return True
        except Exception as e:
            logger.error(f"工具加载失败: {e}")
            return False
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        try:
            if not self.loaded:
                if not self.load():
                    return {"success": False, "error": "工具加载失败"}
            
            # 验证输入参数
            validation_result = self._validate_input(kwargs)
            if not validation_result["success"]:
                return validation_result
            
            # 执行工具
            if self.function:
                result = await self.function(**kwargs)
            else:
                result = await self._default_execute(**kwargs)
            
            # 验证输出
            output_validation = self._validate_output(result)
            if not output_validation["success"]:
                return output_validation
            
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入参数"""
        try:
            required_params = self.metadata.input_schema.get("required", [])
            properties = self.metadata.input_schema.get("properties", {})
            
            # 检查必需参数
            for param in required_params:
                if param not in input_data:
                    return {
                        "success": False, 
                        "error": f"缺少必需参数: {param}"
                    }
            
            # 检查参数类型
            for param, value in input_data.items():
                if param in properties:
                    expected_type = properties[param].get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        return {
                            "success": False,
                            "error": f"参数 {param} 类型不匹配，期望 {expected_type}，实际 {type(value).__name__}"
                        }
            
            return {"success": True}
        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_output(self, output_data: Any) -> Dict[str, Any]:
        """验证输出数据"""
        try:
            # 简化实现，实际使用时需要更严格的验证
            if output_data is None:
                return {"success": False, "error": "工具输出不能为 None"}
            
            return {"success": True}
        except Exception as e:
            logger.error(f"输出验证失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型匹配"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        if expected_type in type_map:
            expected = type_map[expected_type]
            if isinstance(expected, tuple):
                return any(isinstance(value, t) for t in expected)
            return isinstance(value, expected)
        
        return True  # 对于未知类型，不进行严格检查
    
    async def _default_execute(self, **kwargs) -> Any:
        """默认执行方法"""
        return {
            "message": f"工具 {self.metadata.name} 执行成功",
            "input": kwargs,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

class ToolPackageManager:
    """工具包管理器"""
    
    def __init__(self, tools_directory: str = "tools"):
        self.tools_directory = Path(tools_directory)
        self.tools_directory.mkdir(exist_ok=True)
        self.loaded_tools: Dict[str, CustomTool] = {}
        
        # 创建必要的子目录
        (self.tools_directory / "installed").mkdir(exist_ok=True)
        (self.tools_directory / "cache").mkdir(exist_ok=True)
        (self.tools_directory / "temp").mkdir(exist_ok=True)
    
    async def install_tool(self, package_path: str) -> Dict[str, Any]:
        """安装工具包"""
        try:
            if not os.path.exists(package_path):
                return {"success": False, "error": "工具包文件不存在"}
            
            # 验证工具包格式
            if package_path.endswith('.zip'):
                return await self._install_zip_package(package_path)
            elif package_path.endswith('.json'):
                return await self._install_json_package(package_path)
            else:
                return {"success": False, "error": "不支持的包格式"}
        except Exception as e:
            logger.error(f"工具包安装失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _install_zip_package(self, zip_path: str) -> Dict[str, Any]:
        """安装ZIP格式的工具包"""
        try:
            # 提取包信息
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 检查是否包含tool_manifest.json
                if 'tool_manifest.json' not in zip_ref.namelist():
                    return {"success": False, "error": "工具包缺少 manifest 文件"}
                
                # 读取manifest
                manifest_data = zip_ref.read('tool_manifest.json')
                manifest = json.loads(manifest_data.decode('utf-8'))
                
                # 验证manifest
                validation = self._validate_manifest(manifest)
                if not validation["success"]:
                    return validation
                
                tool_name = manifest["name"]
                tool_version = manifest["version"]
                
                # 创建安装目录
                install_dir = self.tools_directory / "installed" / f"{tool_name}-{tool_version}"
                install_dir.mkdir(parents=True, exist_ok=True)
                
                # 解压文件
                zip_ref.extractall(install_dir)
                
                # 注册工具
                metadata = ToolMetadata(
                    name=manifest["name"],
                    version=manifest["version"],
                    description=manifest.get("description", ""),
                    author=manifest.get("author", ""),
                    category=manifest.get("category", "uncategorized"),
                    input_schema=manifest.get("input_schema", {}),
                    output_schema=manifest.get("output_schema", {}),
                    requirements=manifest.get("requirements", []),
                    entry_point=manifest.get("entry_point", "")
                )
                
                tool = CustomTool(metadata)
                self.loaded_tools[tool_name] = tool
                
                return {
                    "success": True,
                    "message": f"工具 {tool_name} v{tool_version} 安装成功",
                    "install_dir": str(install_dir),
                    "metadata": manifest
                }
        except Exception as e:
            logger.error(f"ZIP包安装失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _install_json_package(self, json_path: str) -> Dict[str, Any]:
        """安装JSON格式的工具包"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # 验证manifest
            validation = self._validate_manifest(manifest)
            if not validation["success"]:
                return validation
            
            tool_name = manifest["name"]
            tool_version = manifest["version"]
            
            # 创建安装目录
            install_dir = self.tools_directory / "installed" / f"{tool_name}-{tool_version}"
            install_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制manifest文件
            shutil.copy2(json_path, install_dir / "tool_manifest.json")
            
            # 如果有代码文件，复制它们
            code_files = manifest.get("code_files", [])
            for code_file in code_files:
                if os.path.exists(code_file):
                    shutil.copy2(code_file, install_dir / os.path.basename(code_file))
            
            # 注册工具
            metadata = ToolMetadata(
                name=manifest["name"],
                version=manifest["version"],
                description=manifest.get("description", ""),
                author=manifest.get("author", ""),
                category=manifest.get("category", "uncategorized"),
                input_schema=manifest.get("input_schema", {}),
                output_schema=manifest.get("output_schema", {}),
                requirements=manifest.get("requirements", []),
                entry_point=manifest.get("entry_point", "")
            )
            
            tool = CustomTool(metadata)
            self.loaded_tools[tool_name] = tool
            
            return {
                "success": True,
                "message": f"工具 {tool_name} v{tool_version} 安装成功",
                "install_dir": str(install_dir),
                "metadata": manifest
            }
        except Exception as e:
            logger.error(f"JSON包安装失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """验证工具清单"""
        try:
            required_fields = ["name", "version", "description"]
            
            for field in required_fields:
                if field not in manifest:
                    return {"success": False, "error": f"清单缺少必需字段: {field}"}
            
            # 检查名称格式
            name = manifest["name"]
            if not isinstance(name, str) or not name.replace('_', '').replace('-', '').isalnum():
                return {"success": False, "error": "工具名称只能包含字母、数字、下划线和连字符"}
            
            # 检查版本格式
            version = manifest["version"]
            if not isinstance(version, str) or not self._is_valid_version(version):
                return {"success": False, "error": "版本号格式无效，应该符合语义化版本规范"}
            
            return {"success": True}
        except Exception as e:
            logger.error(f"清单验证失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _is_valid_version(self, version: str) -> bool:
        """检查版本号格式"""
        import re
        pattern = r'^\d+\.\d+\.\d+([+-][a-zA-Z0-9.-]+)?$'
        return re.match(pattern, version) is not None
    
    async def uninstall_tool(self, tool_name: str) -> Dict[str, Any]:
        """卸载工具"""
        try:
            if tool_name not in self.loaded_tools:
                return {"success": False, "error": f"工具未安装: {tool_name}"}
            
            # 查找安装目录
            installed_dir = self.tools_directory / "installed"
            tool_dirs = [d for d in installed_dir.iterdir() if d.name.startswith(tool_name)]
            
            # 删除工具目录
            for tool_dir in tool_dirs:
                shutil.rmtree(tool_dir)
            
            # 从内存中移除
            del self.loaded_tools[tool_name]
            
            return {
                "success": True,
                "message": f"工具 {tool_name} 卸载成功"
            }
        except Exception as e:
            logger.error(f"工具卸载失败: {e}")
            return {"success": False, "error": str(e)}
    
    def list_installed_tools(self) -> Dict[str, Any]:
        """列出已安装的工具"""
        try:
            tools_info = []
            for tool_name, tool in self.loaded_tools.items():
                tools_info.append({
                    "name": tool.metadata.name,
                    "version": tool.metadata.version,
                    "description": tool.metadata.description,
                    "author": tool.metadata.author,
                    "category": tool.metadata.category,
                    "loaded": tool.loaded
                })
            
            return {
                "success": True,
                "tools": tools_info,
                "total_tools": len(tools_info)
            }
        except Exception as e:
            logger.error(f"工具列表获取失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """获取工具详细信息"""
        try:
            if tool_name not in self.loaded_tools:
                return {"success": False, "error": f"工具未安装: {tool_name}"}
            
            tool = self.loaded_tools[tool_name]
            
            return {
                "success": True,
                "tool_info": {
                    "name": tool.metadata.name,
                    "version": tool.metadata.version,
                    "description": tool.metadata.description,
                    "author": tool.metadata.author,
                    "category": tool.metadata.category,
                    "input_schema": tool.metadata.input_schema,
                    "output_schema": tool.metadata.output_schema,
                    "requirements": tool.metadata.requirements,
                    "entry_point": tool.metadata.entry_point,
                    "loaded": tool.loaded
                }
            }
        except Exception as e:
            logger.error(f"工具信息获取失败: {e}")
            return {"success": False, "error": str(e)}

class PythonFunctionTool(CustomTool):
    """Python函数工具"""
    
    def __init__(self, function: Callable, metadata: ToolMetadata):
        super().__init__(metadata)
        self.function = function
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行Python函数工具"""
        try:
            if inspect.iscoroutinefunction(self.function):
                result = await self.function(**kwargs)
            else:
                result = self.function(**kwargs)
            
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Python函数执行失败: {e}")
            return {"success": False, "error": str(e)}

class CommandLineTool(CustomTool):
    """命令行工具"""
    
    def __init__(self, command_template: str, metadata: ToolMetadata):
        super().__init__(metadata)
        self.command_template = command_template
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行命令行工具"""
        try:
            import subprocess
            import asyncio
            
            # 构建命令
            command = self.command_template.format(**kwargs)
            
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else ""
            }
        except Exception as e:
            logger.error(f"命令行工具执行失败: {e}")
            return {"success": False, "error": str(e)}

class CustomToolsManager:
    """自定义工具管理器"""
    
    def __init__(self):
        self.package_manager = ToolPackageManager()
        self.python_tools: Dict[str, PythonFunctionTool] = {}
        self.command_line_tools: Dict[str, CommandLineTool] = {}
    
    def register_python_function(self, 
                               function: Callable,
                               name: str,
                               description: str,
                               author: str = "unknown",
                               category: str = "custom",
                               input_schema: Optional[Dict[str, Any]] = None,
                               output_schema: Optional[Dict[str, Any]] = None,
                               requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """注册Python函数工具"""
        try:
            # 自动生成输入schema（如果未提供）
            if input_schema is None:
                input_schema = self._generate_input_schema(function)
            
            # 自动生成输出schema（如果未提供）
            if output_schema is None:
                output_schema = {"type": "object"}
            
            metadata = ToolMetadata(
                name=name,
                version="1.0.0",
                description=description,
                author=author,
                category=category,
                input_schema=input_schema,
                output_schema=output_schema,
                requirements=requirements or [],
                entry_point=f"{function.__module__}.{function.__name__}"
            )
            
            tool = PythonFunctionTool(function, metadata)
            self.python_tools[name] = tool
            self.package_manager.loaded_tools[name] = tool
            
            return {
                "success": True,
                "message": f"Python函数工具 {name} 注册成功",
                "tool_name": name
            }
        except Exception as e:
            logger.error(f"Python函数工具注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_input_schema(self, function: Callable) -> Dict[str, Any]:
        """生成输入schema"""
        try:
            signature = inspect.signature(function)
            properties = {}
            required = []
            
            for param_name, param in signature.parameters.items():
                param_type = "string"  # 默认类型
                
                if param.annotation != inspect.Parameter.empty:
                    type_map = {
                        str: "string",
                        int: "integer",
                        float: "number",
                        bool: "boolean",
                        list: "array",
                        dict: "object"
                    }
                    param_type = type_map.get(param.annotation, "string")
                
                properties[param_name] = {"type": param_type}
                
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            
            return {
                "type": "object",
                "properties": properties,
                "required": required
            }
        except Exception as e:
            logger.error(f"输入schema生成失败: {e}")
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
    
    def register_command_line_tool(self,
                                 command_template: str,
                                 name: str,
                                 description: str,
                                 author: str = "unknown",
                                 category: str = "command_line",
                                 input_schema: Optional[Dict[str, Any]] = None,
                                 output_schema: Optional[Dict[str, Any]] = None,
                                 requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """注册命令行工具"""
        try:
            # 提取命令中的参数
            import re
            params = re.findall(r'\{(\w+)\}', command_template)
            
            # 生成输入schema（如果未提供）
            if input_schema is None:
                properties = {param: {"type": "string"} for param in params}
                input_schema = {
                    "type": "object",
                    "properties": properties,
                    "required": params
                }
            
            metadata = ToolMetadata(
                name=name,
                version="1.0.0",
                description=description,
                author=author,
                category=category,
                input_schema=input_schema,
                output_schema=output_schema or {"type": "object"},
                requirements=requirements or [],
                entry_point=command_template
            )
            
            tool = CommandLineTool(command_template, metadata)
            self.command_line_tools[name] = tool
            self.package_manager.loaded_tools[name] = tool
            
            return {
                "success": True,
                "message": f"命令行工具 {name} 注册成功",
                "tool_name": name
            }
        except Exception as e:
            logger.error(f"命令行工具注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        try:
            if tool_name not in self.package_manager.loaded_tools:
                return {"success": False, "error": f"工具未找到: {tool_name}"}
            
            tool = self.package_manager.loaded_tools[tool_name]
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def create_tool_package(self, tool_name: str, output_path: str) -> Dict[str, Any]:
        """创建工具包"""
        try:
            if tool_name not in self.package_manager.loaded_tools:
                return {"success": False, "error": f"工具未找到: {tool_name}"}
            
            tool = self.package_manager.loaded_tools[tool_name]
            
            # 创建包目录结构
            temp_dir = Path(tempfile.mkdtemp())
            package_dir = temp_dir / f"{tool.metadata.name}-{tool.metadata.version}"
            package_dir.mkdir()
            
            # 创建manifest文件
            manifest = {
                "name": tool.metadata.name,
                "version": tool.metadata.version,
                "description": tool.metadata.description,
                "author": tool.metadata.author,
                "category": tool.metadata.category,
                "input_schema": tool.metadata.input_schema,
                "output_schema": tool.metadata.output_schema,
                "requirements": tool.metadata.requirements,
                "entry_point": tool.metadata.entry_point
            }
            
            with open(package_dir / "tool_manifest.json", 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            # 如果是Python函数工具，保存代码
            if tool_name in self.python_tools:
                self._export_python_tool(tool, package_dir)
            
            # 创建ZIP包
            shutil.make_archive(output_path.replace('.zip', ''), 'zip', package_dir)
            
            # 清理临时文件
            shutil.rmtree(temp_dir)
            
            return {
                "success": True,
                "message": f"工具包创建成功: {output_path}",
                "package_path": output_path
            }
        except Exception as e:
            logger.error(f"工具包创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _export_python_tool(self, tool: PythonFunctionTool, package_dir: Path):
        """导出Python工具"""
        try:
            # 获取函数源码
            source = inspect.getsource(tool.function)
            
            # 创建Python文件
            with open(package_dir / f"{tool.metadata.name}.py", 'w', encoding='utf-8') as f:
                f.write(source)
        except Exception as e:
            logger.error(f"Python工具导出失败: {e}")

