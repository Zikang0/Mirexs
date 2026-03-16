"""
脚本执行器：执行各种脚本
"""
import subprocess
import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import tempfile
from pathlib import Path
import threading
import queue

logger = logging.getLogger(__name__)

class ScriptType(Enum):
    """脚本类型枚举"""
    PYTHON = "python"
    BASH = "bash"
    POWERSHELL = "powershell"
    BATCH = "batch"
    JAVASCRIPT = "javascript"
    CUSTOM = "custom"

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class ScriptExecution:
    """脚本执行信息"""
    id: str
    script_type: ScriptType
    script_content: str
    script_path: Optional[str] = None
    arguments: List[str] = None
    working_directory: Optional[str] = None
    environment_vars: Dict[str, str] = None
    timeout: int = 300  # 默认5分钟
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.arguments is None:
            self.arguments = []
        if self.environment_vars is None:
            self.environment_vars = {}

class ScriptExecutor:
    """脚本执行器"""
    
    def __init__(self):
        self.execution_queue = queue.Queue()
        self.active_executions: Dict[str, ScriptExecution] = {}
        self.execution_history: List[ScriptExecution] = []
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.execution_lock = threading.Lock()
        self._setup_logging()
        self._initialize_script_templates()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_script_templates(self):
        """初始化脚本模板"""
        self.script_templates = {
            "file_processor": {
                ScriptType.PYTHON: """
import os
import sys

def process_files(directory):
    \"\"\"处理目录中的文件\"\"\"
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            print(f"处理文件: {filename}")
            # 在这里添加文件处理逻辑

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    process_files(directory)
"""
            },
            "data_backup": {
                ScriptType.POWERSHELL: """
param(
    [string]$SourcePath,
    [string]$BackupPath
)

# 创建备份目录
if (!(Test-Path $BackupPath)) {
    New-Item -ItemType Directory -Path $BackupPath -Force
}

# 复制文件
Copy-Item -Path $SourcePath -Destination $BackupPath -Recurse -Force
Write-Host "备份完成: $SourcePath -> $BackupPath"
"""
            }
        }
    
    def start_executor(self) -> bool:
        """启动脚本执行器"""
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True
            )
            self.worker_thread.start()
            
            logger.info("脚本执行器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"脚本执行器启动失败: {str(e)}")
            self.is_running = False
            return False
    
    def stop_executor(self) -> bool:
        """停止脚本执行器"""
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=10)
            
            logger.info("脚本执行器停止成功")
            return True
            
        except Exception as e:
            logger.error(f"脚本执行器停止失败: {str(e)}")
            return False
    
    def execute_script(self, execution: ScriptExecution) -> str:
        """执行脚本"""
        try:
            execution_id = execution.id
            
            with self.execution_lock:
                if execution_id in self.active_executions:
                    return ""  # 已在执行中
                
                self.active_executions[execution_id] = execution
            
            # 添加到执行队列
            self.execution_queue.put(execution_id)
            
            logger.info(f"提交脚本执行: {execution_id}")
            return execution_id
            
        except Exception as e:
            logger.error(f"提交脚本执行失败: {str(e)}")
            return ""
    
    def create_execution(self, script_type: ScriptType, script_content: str, 
                        script_path: str = None, **kwargs) -> ScriptExecution:
        """创建脚本执行实例"""
        import uuid
        
        execution = ScriptExecution(
            id=str(uuid.uuid4()),
            script_type=script_type,
            script_content=script_content,
            script_path=script_path,
            arguments=kwargs.get('arguments', []),
            working_directory=kwargs.get('working_directory'),
            environment_vars=kwargs.get('environment_vars', {}),
            timeout=kwargs.get('timeout', 300)
        )
        
        return execution
    
    def execute_script_from_template(self, template_name: str, script_type: ScriptType,
                                   parameters: Dict[str, Any] = None) -> Optional[str]:
        """从模板执行脚本"""
        try:
            if template_name not in self.script_templates:
                return None
            
            templates = self.script_templates[template_name]
            if script_type not in templates:
                return None
            
            script_content = templates[script_type]
            
            # 替换模板参数
            if parameters:
                for key, value in parameters.items():
                    script_content = script_content.replace(f"${key}", str(value))
            
            execution = self.create_execution(script_type, script_content)
            return self.execute_script(execution)
            
        except Exception as e:
            logger.error(f"从模板执行脚本失败: {str(e)}")
            return None
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.is_running:
            try:
                # 从队列获取执行ID
                execution_id = self.execution_queue.get(timeout=1.0)
                
                # 执行脚本
                self._execute_script_internal(execution_id)
                
                self.execution_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {str(e)}")
                time.sleep(1)
    
    def _execute_script_internal(self, execution_id: str):
        """内部脚本执行方法"""
        try:
            with self.execution_lock:
                if execution_id not in self.active_executions:
                    return
                
                execution = self.active_executions[execution_id]
                execution.status = ExecutionStatus.RUNNING
                execution.start_time = datetime.now()
            
            logger.info(f"开始执行脚本: {execution_id}")
            
            # 准备执行环境
            script_file = self._prepare_script_file(execution)
            if not script_file:
                raise Exception("准备脚本文件失败")
            
            # 构建执行命令
            command = self._build_execution_command(execution, script_file)
            
            # 执行脚本
            success, exit_code, stdout, stderr = self._run_script_command(
                command, execution.working_directory, 
                execution.environment_vars, execution.timeout
            )
            
            # 更新执行结果
            with self.execution_lock:
                execution.end_time = datetime.now()
                execution.exit_code = exit_code
                execution.stdout = stdout
                execution.stderr = stderr
                
                if success:
                    execution.status = ExecutionStatus.COMPLETED
                    logger.info(f"脚本执行成功: {execution_id}")
                else:
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = stderr or "执行失败"
                    logger.error(f"脚本执行失败: {execution_id}")
                
                # 移动到历史记录
                self.execution_history.append(execution)
                del self.active_executions[execution_id]
            
            # 清理临时文件
            if script_file and os.path.exists(script_file):
                try:
                    os.remove(script_file)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {str(e)}")
            
        except subprocess.TimeoutExpired:
            with self.execution_lock:
                if execution_id in self.active_executions:
                    execution = self.active_executions[execution_id]
                    execution.status = ExecutionStatus.TIMEOUT
                    execution.error_message = f"执行超时 ({execution.timeout}秒)"
                    self.execution_history.append(execution)
                    del self.active_executions[execution_id]
            
            logger.error(f"脚本执行超时: {execution_id}")
            
        except Exception as e:
            with self.execution_lock:
                if execution_id in self.active_executions:
                    execution = self.active_executions[execution_id]
                    execution.status = ExecutionStatus.FAILED
                    execution.error_message = str(e)
                    self.execution_history.append(execution)
                    del self.active_executions[execution_id]
            
            logger.error(f"脚本执行异常 {execution_id}: {str(e)}")
    
    def _prepare_script_file(self, execution: ScriptExecution) -> Optional[str]:
        """准备脚本文件"""
        try:
            if execution.script_path and os.path.exists(execution.script_path):
                return execution.script_path
            
            # 创建临时文件
            file_extension = self._get_script_extension(execution.script_type)
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=file_extension, 
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(execution.script_content)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"准备脚本文件失败: {str(e)}")
            return None
    
    def _get_script_extension(self, script_type: ScriptType) -> str:
        """获取脚本文件扩展名"""
        extension_map = {
            ScriptType.PYTHON: '.py',
            ScriptType.BASH: '.sh',
            ScriptType.POWERSHELL: '.ps1',
            ScriptType.BATCH: '.bat',
            ScriptType.JAVASCRIPT: '.js',
            ScriptType.CUSTOM: '.txt'
        }
        return extension_map.get(script_type, '.txt')
    
    def _build_execution_command(self, execution: ScriptExecution, script_file: str) -> List[str]:
        """构建执行命令"""
        if execution.script_type == ScriptType.PYTHON:
            command = [sys.executable, script_file]
        elif execution.script_type == ScriptType.BASH:
            command = ['bash', script_file]
        elif execution.script_type == ScriptType.POWERSHELL:
            command = ['powershell', '-File', script_file]
        elif execution.script_type == ScriptType.BATCH:
            command = ['cmd', '/c', script_file]
        elif execution.script_type == ScriptType.JAVASCRIPT:
            command = ['node', script_file]
        else:
            command = [script_file]
        
        # 添加参数
        command.extend(execution.arguments)
        
        return command
    
    def _run_script_command(self, command: List[str], working_directory: Optional[str],
                          environment_vars: Dict[str, str], timeout: int) -> Tuple[bool, int, str, str]:
        """运行脚本命令"""
        try:
            # 准备环境变量
            env = os.environ.copy()
            env.update(environment_vars)
            
            # 执行命令
            result = subprocess.run(
                command,
                cwd=working_directory,
                env=env,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            success = (result.returncode == 0)
            return success, result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            raise
        except Exception as e:
            return False, -1, "", str(e)
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        with self.execution_lock:
            # 检查活跃执行
            if execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                return self._execution_to_dict(execution)
            
            # 检查历史记录
            for execution in self.execution_history:
                if execution.id == execution_id:
                    return self._execution_to_dict(execution)
        
        return None
    
    def _execution_to_dict(self, execution: ScriptExecution) -> Dict[str, Any]:
        """将执行信息转换为字典"""
        return {
            'id': execution.id,
            'script_type': execution.script_type.value,
            'status': execution.status.value,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'exit_code': execution.exit_code,
            'stdout': execution.stdout,
            'stderr': execution.stderr,
            'error_message': execution.error_message
        }
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        try:
            with self.execution_lock:
                if execution_id not in self.active_executions:
                    return False
                
                execution = self.active_executions[execution_id]
                execution.status = ExecutionStatus.CANCELLED
                execution.end_time = datetime.now()
                execution.error_message = "用户取消"
                
                # 移动到历史记录
                self.execution_history.append(execution)
                del self.active_executions[execution_id]
            
            logger.info(f"取消脚本执行: {execution_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消脚本执行失败: {str(e)}")
            return False
    
    def get_active_executions(self) -> List[Dict[str, Any]]:
        """获取活跃执行列表"""
        with self.execution_lock:
            return [self._execution_to_dict(execution) for execution in self.active_executions.values()]
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行历史"""
        with self.execution_lock:
            history = self.execution_history[-limit:] if limit > 0 else self.execution_history
            return [self._execution_to_dict(execution) for execution in history]
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        with self.execution_lock:
            total_executions = len(self.execution_history) + len(self.active_executions)
            
            status_counts = {}
            for execution in self.execution_history:
                status = execution.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for execution in self.active_executions.values():
                status = execution.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                'total_executions': total_executions,
                'active_executions': len(self.active_executions),
                'status_counts': status_counts
            }

# 单例实例
_script_executor_instance = None

def get_script_executor() -> ScriptExecutor:
    """获取脚本执行器单例"""
    global _script_executor_instance
    if _script_executor_instance is None:
        _script_executor_instance = ScriptExecutor()
    return _script_executor_instance

