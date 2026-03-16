"""
开发工具集成模块
提供代码编辑、调试、版本控制等开发相关功能
"""

import os
import subprocess
import logging
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import ast
import traceback

logger = logging.getLogger(__name__)

class CodeEditor:
    """代码编辑器"""
    
    def __init__(self):
        self.current_file = None
        self.undo_stack = []
        self.redo_stack = []
    
    def create_file(self, filepath: str, content: str = "") -> Dict[str, Any]:
        """创建代码文件"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.current_file = filepath
            self.undo_stack.clear()
            self.redo_stack.clear()
            
            return {"success": True, "message": f"文件创建成功: {filepath}"}
        except Exception as e:
            logger.error(f"文件创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    def open_file(self, filepath: str) -> Dict[str, Any]:
        """打开代码文件"""
        try:
            if not os.path.exists(filepath):
                return {"success": False, "error": "文件不存在"}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.current_file = filepath
            self.undo_stack.clear()
            self.redo_stack.clear()
            
            return {
                "success": True,
                "content": content,
                "filepath": filepath
            }
        except Exception as e:
            logger.error(f"文件打开失败: {e}")
            return {"success": False, "error": str(e)}
    
    def save_file(self, content: str, filepath: Optional[str] = None) -> Dict[str, Any]:
        """保存代码文件"""
        try:
            save_path = filepath or self.current_file
            if not save_path:
                return {"success": False, "error": "未指定保存路径"}
            
            # 保存到撤销栈
            if self.current_file and os.path.exists(self.current_file):
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                self.undo_stack.append(old_content)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.current_file = save_path
            self.redo_stack.clear()
            
            return {"success": True, "message": f"文件保存成功: {save_path}"}
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            return {"success": False, "error": str(e)}
    
    def undo(self) -> Dict[str, Any]:
        """撤销操作"""
        try:
            if not self.undo_stack:
                return {"success": False, "error": "无可撤销操作"}
            
            if self.current_file and os.path.exists(self.current_file):
                with open(self.current_file, 'r', encoding='utf-8') as f:
                    current_content = f.read()
                self.redo_stack.append(current_content)
            
            previous_content = self.undo_stack.pop()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(previous_content)
            
            return {
                "success": True,
                "content": previous_content,
                "message": "撤销成功"
            }
        except Exception as e:
            logger.error(f"撤销操作失败: {e}")
            return {"success": False, "error": str(e)}
    
    def format_code(self, content: str, language: str = "python") -> Dict[str, Any]:
        """格式化代码"""
        try:
            if language == "python":
                return self._format_python_code(content)
            elif language == "json":
                return self._format_json_code(content)
            else:
                return {"success": False, "error": f"不支持的语言: {language}"}
        except Exception as e:
            logger.error(f"代码格式化失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_python_code(self, content: str) -> Dict[str, Any]:
        """格式化Python代码"""
        try:
            # 简单的Python代码格式化
            tree = ast.parse(content)
            formatted_code = ast.unparse(tree)
            return {"success": True, "formatted_code": formatted_code}
        except SyntaxError as e:
            return {"success": False, "error": f"语法错误: {e}"}
        except Exception as e:
            logger.error(f"Python代码格式化失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_json_code(self, content: str) -> Dict[str, Any]:
        """格式化JSON代码"""
        try:
            parsed = json.loads(content)
            formatted_code = json.dumps(parsed, indent=2, ensure_ascii=False)
            return {"success": True, "formatted_code": formatted_code}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON解析错误: {e}"}
        except Exception as e:
            logger.error(f"JSON代码格式化失败: {e}")
            return {"success": False, "error": str(e)}

class CodeExecutor:
    """代码执行器"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def execute_python_code(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """执行Python代码"""
        try:
            # 创建临时文件
            temp_file = os.path.join(self.temp_dir, "temp_script.py")
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # 执行代码
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir
            )
            
            return {
                "success": True,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "代码执行超时"}
        except Exception as e:
            logger.error(f"代码执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def execute_shell_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """执行Shell命令"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir
            )
            
            return {
                "success": True,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令执行超时"}
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return {"success": False, "error": str(e)}
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

class Debugger:
    """调试器"""
    
    def __init__(self):
        self.breakpoints = {}
        self.watch_expressions = []
    
    def set_breakpoint(self, filepath: str, line_number: int) -> Dict[str, Any]:
        """设置断点"""
        try:
            if filepath not in self.breakpoints:
                self.breakpoints[filepath] = []
            
            if line_number not in self.breakpoints[filepath]:
                self.breakpoints[filepath].append(line_number)
            
            return {
                "success": True,
                "message": f"在 {filepath}:{line_number} 设置断点",
                "breakpoints": self.breakpoints
            }
        except Exception as e:
            logger.error(f"设置断点失败: {e}")
            return {"success": False, "error": str(e)}
    
    def add_watch_expression(self, expression: str) -> Dict[str, Any]:
        """添加监视表达式"""
        try:
            if expression not in self.watch_expressions:
                self.watch_expressions.append(expression)
            
            return {
                "success": True,
                "message": f"添加监视表达式: {expression}",
                "watch_expressions": self.watch_expressions
            }
        except Exception as e:
            logger.error(f"添加监视表达式失败: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """代码分析"""
        try:
            issues = []
            
            # 检查语法错误
            try:
                ast.parse(code)
            except SyntaxError as e:
                issues.append({
                    "type": "syntax_error",
                    "line": e.lineno,
                    "message": str(e),
                    "severity": "error"
                })
            
            # 简单的代码质量检查
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                line = line.strip()
                
                # 检查行长度
                if len(line) > 120:
                    issues.append({
                        "type": "line_too_long",
                        "line": i,
                        "message": f"行 {i} 超过120个字符",
                        "severity": "warning"
                    })
                
                # 检查未使用的导入（简化版）
                if line.startswith('import ') or line.startswith('from '):
                    # 这里可以添加更复杂的导入使用分析
                    pass
            
            return {
                "success": True,
                "issues": issues,
                "issue_count": len(issues)
            }
        except Exception as e:
            logger.error(f"代码分析失败: {e}")
            return {"success": False, "error": str(e)}

class VersionControl:
    """版本控制"""
    
    def __init__(self):
        self.repo_path = None
    
    def init_repository(self, path: str) -> Dict[str, Any]:
        """初始化版本库"""
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            
            result = subprocess.run(
                ['git', 'init'],
                cwd=path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.repo_path = path
                return {"success": True, "message": "版本库初始化成功"}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"版本库初始化失败: {e}")
            return {"success": False, "error": str(e)}
    
    def clone_repository(self, repo_url: str, local_path: str) -> Dict[str, Any]:
        """克隆远程版本库"""
        try:
            result = subprocess.run(
                ['git', 'clone', repo_url, local_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.repo_path = local_path
                return {"success": True, "message": "版本库克隆成功"}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"版本库克隆失败: {e}")
            return {"success": False, "error": str(e)}
    
    def add_files(self, files: List[str]) -> Dict[str, Any]:
        """添加文件到版本控制"""
        try:
            if not self.repo_path:
                return {"success": False, "error": "未设置版本库路径"}
            
            cmd = ['git', 'add'] + files
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "文件添加成功"}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"文件添加失败: {e}")
            return {"success": False, "error": str(e)}
    
    def commit_changes(self, message: str) -> Dict[str, Any]:
        """提交更改"""
        try:
            if not self.repo_path:
                return {"success": False, "error": "未设置版本库路径"}
            
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "更改提交成功"}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"更改提交失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """获取版本库状态"""
        try:
            if not self.repo_path:
                return {"success": False, "error": "未设置版本库路径"}
            
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                files = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        status = line[:2]
                        filename = line[3:]
                        files.append({"status": status, "filename": filename})
                
                return {"success": True, "files": files}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"success": False, "error": str(e)}

class DevelopmentToolsManager:
    """开发工具管理器"""
    
    def __init__(self):
        self.code_editor = CodeEditor()
        self.code_executor = CodeExecutor()
        self.debugger = Debugger()
        self.version_control = VersionControl()
    
    def create_project(self, project_path: str, template: str = "basic") -> Dict[str, Any]:
        """创建新项目"""
        try:
            if os.path.exists(project_path):
                return {"success": False, "error": "项目路径已存在"}
            
            os.makedirs(project_path)
            
            # 创建项目结构
            if template == "basic":
                self._create_basic_project(project_path)
            elif template == "web":
                self._create_web_project(project_path)
            elif template == "data_science":
                self._create_data_science_project(project_path)
            
            # 初始化版本控制
            vc_result = self.version_control.init_repository(project_path)
            
            return {
                "success": True,
                "message": f"项目创建成功: {project_path}",
                "version_control": vc_result
            }
        except Exception as e:
            logger.error(f"项目创建失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_basic_project(self, project_path: str):
        """创建基础项目结构"""
        # 创建主要目录
        directories = ['src', 'tests', 'docs', 'data']
        for directory in directories:
            os.makedirs(os.path.join(project_path, directory), exist_ok=True)
        
        # 创建基础文件
        base_files = {
            'README.md': '# Project README\n\n项目说明文档',
            'requirements.txt': '# 项目依赖\n\n',
            'main.py': '#!/usr/bin/env python3\n\nprint("Hello, World!")'
        }
        
        for filename, content in base_files.items():
            with open(os.path.join(project_path, filename), 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _create_web_project(self, project_path: str):
        """创建Web项目结构"""
        self._create_basic_project(project_path)
        
        web_dirs = ['templates', 'static/css', 'static/js', 'static/images']
        for directory in web_dirs:
            os.makedirs(os.path.join(project_path, directory), exist_ok=True)
        
        # 添加Web相关文件
        web_files = {
            'app.py': 'from flask import Flask\n\napp = Flask(__name__)\n\n@app.route("/")\ndef hello():\n    return "Hello, World!"',
            'templates/index.html': '<!DOCTYPE html>\n<html>\n<head>\n    <title>Web Project</title>\n</head>\n<body>\n    <h1>Welcome to my Web Project</h1>\n</body>\n</html>'
        }
        
        for filename, content in web_files.items():
            file_path = os.path.join(project_path, filename)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _create_data_science_project(self, project_path: str):
        """创建数据科学项目结构"""
        self._create_basic_project(project_path)
        
        ds_dirs = ['notebooks', 'models', 'reports']
        for directory in ds_dirs:
            os.makedirs(os.path.join(project_path, directory), exist_ok=True)
        
        # 添加数据科学相关文件
        ds_files = {
            'notebooks/exploratory_analysis.ipynb': '{}',  # 空的Jupyter notebook
            'src/data_preprocessing.py': '# 数据预处理模块\n\nimport pandas as pd\nimport numpy as np',
            'src/model_training.py': '# 模型训练模块\n\nfrom sklearn.ensemble import RandomForestClassifier'
        }
        
        for filename, content in ds_files.items():
            file_path = os.path.join(project_path, filename)
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

