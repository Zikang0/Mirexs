"""
工具发现模块
提供自动发现可用工具的功能
"""

import os
import sys
import importlib
import inspect
import logging
from typing import Dict, List, Any, Optional, Set, Type
from pathlib import Path
import pkgutil
import ast

logger = logging.getLogger(__name__)

class ToolDiscoverer:
    """工具发现器"""
    
    def __init__(self, search_paths: Optional[List[str]] = None):
        self.search_paths = search_paths or [".", "tools", "custom_tools"]
        self.discovered_tools: Dict[str, Dict[str, Any]] = {}
    
    async def discover_tools(self) -> Dict[str, Any]:
        """发现可用工具"""
        try:
            discovered_count = 0
            
            # 搜索Python模块中的工具
            python_tools = await self._discover_python_tools()
            self.discovered_tools.update(python_tools)
            discovered_count += len(python_tools)
            
            # 搜索命令行工具
            cli_tools = await self._discover_cli_tools()
            self.discovered_tools.update(cli_tools)
            discovered_count += len(cli_tools)
            
            # 搜索Web服务工具
            web_tools = await self._discover_web_tools()
            self.discovered_tools.update(web_tools)
            discovered_count += len(web_tools)
            
            return {
                "success": True,
                "discovered_tools": self.discovered_tools,
                "total_tools": discovered_count,
                "categories": {
                    "python": len(python_tools),
                    "cli": len(cli_tools),
                    "web": len(web_tools)
                }
            }
        except Exception as e:
            logger.error(f"工具发现失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _discover_python_tools(self) -> Dict[str, Dict[str, Any]]:
        """发现Python工具"""
        tools = {}
        
        for search_path in self.search_paths:
            if not os.path.exists(search_path):
                continue
            
            if os.path.isdir(search_path):
                # 搜索目录中的Python文件
                python_files = self._find_python_files(search_path)
                for py_file in python_files:
                    file_tools = await self._analyze_python_file(py_file)
                    tools.update(file_tools)
            
            elif os.path.isfile(search_path) and search_path.endswith('.py'):
                # 分析单个Python文件
                file_tools = await self._analyze_python_file(search_path)
                tools.update(file_tools)
        
        return tools
    
    def _find_python_files(self, directory: str) -> List[str]:
        """查找Python文件"""
        python_files = []
        
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和虚拟环境
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    async def _analyze_python_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """分析Python文件中的工具"""
        tools = {}
        
        try:
            # 解析Python文件
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 使用AST分析
            tree = ast.parse(source_code)
            
            # 查找函数和类
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    tool_info = await self._analyze_function(node, file_path)
                    if tool_info:
                        tools[tool_info["name"]] = tool_info
                
                elif isinstance(node, ast.ClassDef):
                    class_tools = await self._analyze_class(node, file_path)
                    tools.update(class_tools)
        
        except Exception as e:
            logger.warning(f"Python文件分析失败 {file_path}: {e}")
        
        return tools
    
    async def _analyze_function(self, func_node: ast.FunctionDef, file_path: str) -> Optional[Dict[str, Any]]:
        """分析函数"""
        try:
            # 检查函数是否有工具相关的装饰器或文档字符串
            docstring = ast.get_docstring(func_node)
            
            # 简单的启发式规则：查找包含"tool"、"process"、"handle"等关键词的函数
            tool_keywords = ["tool", "process", "handle", "execute", "run", "generate"]
            func_name_lower = func_node.name.lower()
            
            if any(keyword in func_name_lower for keyword in tool_keywords) or (
                docstring and any(keyword in docstring.lower() for keyword in tool_keywords)
            ):
                # 分析函数参数
                parameters = []
                for arg in func_node.args.args:
                    if arg.arg != 'self':  # 跳过self参数
                        param_type = "unknown"
                        if arg.annotation:
                            param_type = self._get_annotation_type(arg.annotation)
                        
                        parameters.append({
                            "name": arg.arg,
                            "type": param_type,
                            "required": True
                        })
                
                return {
                    "name": func_node.name,
                    "type": "function",
                    "file_path": file_path,
                    "parameters": parameters,
                    "docstring": docstring,
                    "category": "python_function"
                }
        
        except Exception as e:
            logger.warning(f"函数分析失败 {func_node.name}: {e}")
        
        return None
    
    async def _analyze_class(self, class_node: ast.ClassDef, file_path: str) -> Dict[str, Dict[str, Any]]:
        """分析类"""
        tools = {}
        
        try:
            # 查找类中的工具方法
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name
                    
                    # 检查是否是工具方法
                    if method_name.startswith('execute_') or method_name.startswith('process_'):
                        tool_info = await self._analyze_function(node, file_path)
                        if tool_info:
                            tool_name = f"{class_node.name}.{method_name}"
                            tool_info["name"] = tool_name
                            tool_info["class_name"] = class_node.name
                            tools[tool_name] = tool_info
            
            # 检查类本身是否是工具
            class_docstring = ast.get_docstring(class_node)
            if class_docstring and any(keyword in class_docstring.lower() 
                                     for keyword in ["tool", "processor", "handler"]):
                tools[class_node.name] = {
                    "name": class_node.name,
                    "type": "class",
                    "file_path": file_path,
                    "docstring": class_docstring,
                    "category": "python_class"
                }
        
        except Exception as e:
            logger.warning(f"类分析失败 {class_node.name}: {e}")
        
        return tools
    
    def _get_annotation_type(self, annotation_node: ast.AST) -> str:
        """获取注解类型"""
        try:
            if isinstance(annotation_node, ast.Name):
                return annotation_node.id
            elif isinstance(annotation_node, ast.Attribute):
                return f"{annotation_node.value.id}.{annotation_node.attr}"
            elif isinstance(annotation_node, ast.Subscript):
                return self._get_annotation_type(annotation_node.value)
            else:
                return "unknown"
        except:
            return "unknown"
    
    async def _discover_cli_tools(self) -> Dict[str, Dict[str, Any]]:
        """发现命令行工具"""
        tools = {}
        
        try:
            # 查找PATH中的可执行文件
            paths = os.environ.get('PATH', '').split(os.pathsep)
            
            for path_dir in paths:
                if not os.path.isdir(path_dir):
                    continue
                
                try:
                    for item in os.listdir(path_dir):
                        item_path = os.path.join(path_dir, item)
                        
                        # 检查是否为可执行文件
                        if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                            # 简单的启发式规则：排除系统命令，关注用户工具
                            if any(keyword in item.lower() for keyword in 
                                  ["tool", "util", "cli", "cmd", "script"]):
                                
                                tools[item] = {
                                    "name": item,
                                    "type": "cli",
                                    "path": item_path,
                                    "category": "command_line"
                                }
                except (PermissionError, OSError):
                    continue
        
        except Exception as e:
            logger.warning(f"CLI工具发现失败: {e}")
        
        return tools
    
    async def _discover_web_tools(self) -> Dict[str, Dict[str, Any]]:
        """发现Web服务工具"""
        tools = {}
        
        try:
            # 这里可以集成服务发现机制
            # 简化实现，查找本地HTTP服务
            
            import socket
            
            # 检查常见的开发服务器端口
            common_ports = [8000, 8080, 3000, 5000, 9000]
            
            for port in common_ports:
                if self._is_port_open('localhost', port):
                    tools[f"web_service_{port}"] = {
                        "name": f"web_service_{port}",
                        "type": "web",
                        "url": f"http://localhost:{port}",
                        "port": port,
                        "category": "web_service"
                    }
        
        except Exception as e:
            logger.warning(f"Web工具发现失败: {e}")
        
        return tools
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """检查端口是否开放"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result == 0
        except:
            return False
    
    def get_tool_categories(self) -> Dict[str, List[str]]:
        """获取工具分类"""
        categories = {}
        
        for tool_name, tool_info in self.discovered_tools.items():
            category = tool_info.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
        
        return categories
    
    async def validate_tool(self, tool_name: str) -> Dict[str, Any]:
        """验证工具"""
        try:
            if tool_name not in self.discovered_tools:
                return {"success": False, "error": f"工具未发现: {tool_name}"}
            
            tool_info = self.discovered_tools[tool_name]
            validation_results = {}
            
            # 根据工具类型进行验证
            if tool_info["type"] == "function":
                validation_results = await self._validate_python_function(tool_info)
            elif tool_info["type"] == "cli":
                validation_results = await self._validate_cli_tool(tool_info)
            elif tool_info["type"] == "web":
                validation_results = await self._validate_web_tool(tool_info)
            
            return {
                "success": True,
                "tool_name": tool_name,
                "validation_results": validation_results,
                "is_valid": all(validation_results.values())
            }
        except Exception as e:
            logger.error(f"工具验证失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_python_function(self, tool_info: Dict[str, Any]) -> Dict[str, bool]:
        """验证Python函数工具"""
        results = {}
        
        try:
            # 检查文件存在
            file_path = tool_info.get("file_path")
            results["file_exists"] = os.path.exists(file_path) if file_path else False
            
            # 检查函数可导入（简化验证）
            results["importable"] = True  # 实际使用时需要更严格的检查
            
            # 检查文档完整性
            docstring = tool_info.get("docstring")
            results["has_documentation"] = bool(docstring and len(docstring.strip()) > 10)
            
        except Exception as e:
            logger.warning(f"Python函数验证失败: {e}")
            results["error"] = False
        
        return results
    
    async def _validate_cli_tool(self, tool_info: Dict[str, Any]) -> Dict[str, bool]:
        """验证命令行工具"""
        results = {}
        
        try:
            # 检查文件存在和可执行
            tool_path = tool_info.get("path")
            results["file_exists"] = os.path.exists(tool_path) if tool_path else False
            results["is_executable"] = os.access(tool_path, os.X_OK) if tool_path else False
            
            # 检查帮助信息
            import subprocess
            try:
                result = subprocess.run([tool_path, "--help"], 
                                      capture_output=True, timeout=5)
                results["has_help"] = result.returncode == 0
            except:
                results["has_help"] = False
            
        except Exception as e:
            logger.warning(f"CLI工具验证失败: {e}")
            results["error"] = False
        
        return results
    
    async def _validate_web_tool(self, tool_info: Dict[str, Any]) -> Dict[str, bool]:
        """验证Web工具"""
        results = {}
        
        try:
            import requests
            
            url = tool_info.get("url")
            if url:
                try:
                    response = requests.get(url, timeout=5)
                    results["is_accessible"] = response.status_code < 400
                    results["responds_to_http"] = True
                except:
                    results["is_accessible"] = False
                    results["responds_to_http"] = False
            else:
                results["is_accessible"] = False
                results["responds_to_http"] = False
            
        except Exception as e:
            logger.warning(f"Web工具验证失败: {e}")
            results["error"] = False
        
        return results

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.registered_tools: Dict[str, Dict[str, Any]] = {}
        self.discoverer = ToolDiscoverer()
    
    async def auto_discover_and_register(self) -> Dict[str, Any]:
        """自动发现并注册工具"""
        try:
            # 发现工具
            discovery_result = await self.discoverer.discover_tools()
            if not discovery_result["success"]:
                return discovery_result
            
            # 注册发现的工具
            registered_count = 0
            for tool_name, tool_info in discovery_result["discovered_tools"].items():
                # 验证工具
                validation_result = await self.discoverer.validate_tool(tool_name)
                if validation_result["success"] and validation_result["is_valid"]:
                    self.registered_tools[tool_name] = tool_info
                    registered_count += 1
            
            return {
                "success": True,
                "registered_tools": registered_count,
                "total_discovered": len(discovery_result["discovered_tools"]),
                "registration_rate": registered_count / len(discovery_result["discovered_tools"])
            }
        except Exception as e:
            logger.error(f"自动发现注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def register_tool(self, tool_name: str, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """手动注册工具"""
        try:
            self.registered_tools[tool_name] = tool_info
            
            return {
                "success": True,
                "message": f"工具 {tool_name} 注册成功",
                "tool_name": tool_name
            }
        except Exception as e:
            logger.error(f"工具注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def unregister_tool(self, tool_name: str) -> Dict[str, Any]:
        """取消注册工具"""
        try:
            if tool_name not in self.registered_tools:
                return {"success": False, "error": f"工具未注册: {tool_name}"}
            
            del self.registered_tools[tool_name]
            
            return {
                "success": True,
                "message": f"工具 {tool_name} 取消注册成功"
            }
        except Exception as e:
            logger.error(f"工具取消注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_registered_tools(self, category: Optional[str] = None) -> Dict[str, Any]:
        """获取已注册的工具"""
        try:
            if category:
                filtered_tools = {
                    name: info for name, info in self.registered_tools.items()
                    if info.get("category") == category
                }
                return {
                    "success": True,
                    "tools": filtered_tools,
                    "total_tools": len(filtered_tools),
                    "category": category
                }
            else:
                return {
                    "success": True,
                    "tools": self.registered_tools,
                    "total_tools": len(self.registered_tools)
                }
        except Exception as e:
            logger.error(f"注册工具获取失败: {e}")
            return {"success": False, "error": str(e)}
    
    def search_tools(self, query: str, search_fields: List[str] = None) -> Dict[str, Any]:
        """搜索工具"""
        try:
            if search_fields is None:
                search_fields = ["name", "description", "category", "docstring"]
            
            matching_tools = {}
            query_lower = query.lower()
            
            for tool_name, tool_info in self.registered_tools.items():
                for field in search_fields:
                    field_value = tool_info.get(field, "")
                    if isinstance(field_value, str) and query_lower in field_value.lower():
                        matching_tools[tool_name] = tool_info
                        break
            
            return {
                "success": True,
                "matching_tools": matching_tools,
                "query": query,
                "total_matches": len(matching_tools)
            }
        except Exception as e:
            logger.error(f"工具搜索失败: {e}")
            return {"success": False, "error": str(e)}

            