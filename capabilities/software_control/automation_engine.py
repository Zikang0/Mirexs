"""
自动化引擎：执行自动化任务
"""
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json
from datetime import datetime
import queue

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AutomationTask:
    """自动化任务"""
    id: str
    name: str
    description: str
    actions: List[Dict[str, Any]]  # 任务动作序列
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_time: Optional[datetime] = None
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['created_time'] = self.created_time.isoformat() if self.created_time else None
        data['started_time'] = self.started_time.isoformat() if self.started_time else None
        data['completed_time'] = self.completed_time.isoformat() if self.completed_time else None
        return data

class AutomationEngine:
    """自动化引擎"""
    
    def __init__(self):
        self.tasks: Dict[str, AutomationTask] = {}
        self.task_queue = queue.PriorityQueue()
        self.worker_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.task_lock = threading.Lock()
        self._setup_logging()
        self._initialize_action_handlers()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_action_handlers(self):
        """初始化动作处理器"""
        self.action_handlers = {
            "launch_application": self._handle_launch_application,
            "close_application": self._handle_close_application,
            "keyboard_input": self._handle_keyboard_input,
            "mouse_click": self._handle_mouse_click,
            "wait": self._handle_wait,
            "execute_script": self._handle_execute_script,
            "file_operation": self._handle_file_operation,
            "system_command": self._handle_system_command
        }
    
    def start_engine(self) -> bool:
        """启动自动化引擎"""
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True
            )
            self.worker_thread.start()
            
            logger.info("自动化引擎启动成功")
            return True
            
        except Exception as e:
            logger.error(f"自动化引擎启动失败: {str(e)}")
            self.is_running = False
            return False
    
    def stop_engine(self) -> bool:
        """停止自动化引擎"""
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=10)
            
            logger.info("自动化引擎停止成功")
            return True
            
        except Exception as e:
            logger.error(f"自动化引擎停止失败: {str(e)}")
            return False
    
    def create_task(self, name: str, description: str, actions: List[Dict[str, Any]], 
                   priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """创建自动化任务"""
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            task = AutomationTask(
                id=task_id,
                name=name,
                description=description,
                actions=actions,
                priority=priority,
                created_time=datetime.now()
            )
            
            with self.task_lock:
                self.tasks[task_id] = task
            
            # 根据优先级添加到队列
            priority_value = self._get_priority_value(priority)
            self.task_queue.put((priority_value, task_id))
            
            logger.info(f"创建自动化任务: {name} (ID: {task_id})")
            return task_id
            
        except Exception as e:
            logger.error(f"创建自动化任务失败: {str(e)}")
            return ""
    
    def _get_priority_value(self, priority: TaskPriority) -> int:
        """获取优先级数值"""
        priority_map = {
            TaskPriority.LOW: 3,
            TaskPriority.NORMAL: 2,
            TaskPriority.HIGH: 1,
            TaskPriority.CRITICAL: 0
        }
        return priority_map.get(priority, 2)
    
    def execute_task(self, task_id: str) -> bool:
        """立即执行任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    return False
                
                task = self.tasks[task_id]
                if task.status not in [TaskStatus.PENDING, TaskStatus.FAILED]:
                    return False
                
                # 更新任务状态
                task.status = TaskStatus.RUNNING
                task.started_time = datetime.now()
                task.error_message = None
            
            # 在新线程中执行任务
            execution_thread = threading.Thread(
                target=self._execute_task_actions,
                args=(task_id,),
                daemon=True
            )
            execution_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"执行任务失败 {task_id}: {str(e)}")
            return False
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    return False
                
                task = self.tasks[task_id]
                if task.status == TaskStatus.RUNNING:
                    # 标记为取消，实际停止需要动作处理器支持
                    task.status = TaskStatus.CANCELLED
                    task.completed_time = datetime.now()
                elif task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_time = datetime.now()
            
            logger.info(f"取消任务: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败 {task_id}: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.task_lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return task.to_dict()
        return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        with self.task_lock:
            return [task.to_dict() for task in self.tasks.values()]
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.is_running:
            try:
                # 从队列获取任务
                priority, task_id = self.task_queue.get(timeout=1.0)
                
                # 执行任务
                self.execute_task(task_id)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"工作线程错误: {str(e)}")
                time.sleep(1)
    
    def _execute_task_actions(self, task_id: str):
        """执行任务动作序列"""
        try:
            with self.task_lock:
                if task_id not in self.tasks:
                    return
                task = self.tasks[task_id]
                actions = task.actions.copy()
            
            task_result = {
                'successful_actions': 0,
                'failed_actions': 0,
                'total_actions': len(actions),
                'execution_time': 0
            }
            
            start_time = time.time()
            
            for i, action in enumerate(actions):
                # 检查任务是否被取消
                with self.task_lock:
                    if task.status == TaskStatus.CANCELLED:
                        break
                
                action_type = action.get('type')
                action_params = action.get('params', {})
                
                if action_type in self.action_handlers:
                    try:
                        success, message = self.action_handlers[action_type](action_params)
                        
                        if success:
                            task_result['successful_actions'] += 1
                            logger.info(f"任务 {task_id} 动作 {i+1}/{len(actions)} 执行成功: {message}")
                        else:
                            task_result['failed_actions'] += 1
                            logger.error(f"任务 {task_id} 动作 {i+1}/{len(actions)} 执行失败: {message}")
                            # 如果动作失败且配置了停止条件，则停止执行
                            if action.get('stop_on_failure', False):
                                raise Exception(f"动作执行失败: {message}")
                    
                    except Exception as e:
                        task_result['failed_actions'] += 1
                        logger.error(f"任务 {task_id} 动作 {i+1}/{len(actions)} 执行异常: {str(e)}")
                        break
                else:
                    task_result['failed_actions'] += 1
                    logger.error(f"未知动作类型: {action_type}")
            
            execution_time = time.time() - start_time
            task_result['execution_time'] = execution_time
            
            # 更新任务状态
            with self.task_lock:
                task.completed_time = datetime.now()
                task.result = task_result
                
                if task.status != TaskStatus.CANCELLED:
                    if task_result['failed_actions'] == 0:
                        task.status = TaskStatus.COMPLETED
                    else:
                        task.status = TaskStatus.FAILED
                        task.error_message = f"{task_result['failed_actions']} 个动作执行失败"
            
            logger.info(f"任务 {task_id} 执行完成: {task_result}")
            
        except Exception as e:
            logger.error(f"执行任务动作序列失败 {task_id}: {str(e)}")
            
            with self.task_lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                    task.completed_time = datetime.now()
    
    # 动作处理器方法
    def _handle_launch_application(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理启动应用程序动作"""
        try:
            from .application_launcher import get_application_launcher
            
            app_name = params.get('application_name')
            arguments = params.get('arguments', [])
            
            launcher = get_application_launcher()
            success, message = launcher.launch_application(app_name, arguments)
            
            return success, message
            
        except Exception as e:
            return False, f"启动应用程序失败: {str(e)}"
    
    def _handle_close_application(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理关闭应用程序动作"""
        try:
            from .application_launcher import get_application_launcher
            
            app_name = params.get('application_name')
            force = params.get('force', False)
            
            launcher = get_application_launcher()
            success, message = launcher.close_application(app_name, force)
            
            return success, message
            
        except Exception as e:
            return False, f"关闭应用程序失败: {str(e)}"
    
    def _handle_keyboard_input(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理键盘输入动作"""
        try:
            import pyautogui
            
            text = params.get('text', '')
            interval = params.get('interval', 0.1)
            
            pyautogui.write(text, interval=interval)
            
            return True, f"输入文本: {text}"
            
        except Exception as e:
            return False, f"键盘输入失败: {str(e)}"
    
    def _handle_mouse_click(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理鼠标点击动作"""
        try:
            import pyautogui
            
            x = params.get('x')
            y = params.get('y')
            button = params.get('button', 'left')
            clicks = params.get('clicks', 1)
            
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button, clicks=clicks)
                return True, f"在位置 ({x}, {y}) 点击鼠标"
            else:
                pyautogui.click(button=button, clicks=clicks)
                return True, "在当前位置点击鼠标"
            
        except Exception as e:
            return False, f"鼠标点击失败: {str(e)}"
    
    def _handle_wait(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理等待动作"""
        try:
            duration = params.get('duration', 1.0)
            time.sleep(duration)
            return True, f"等待 {duration} 秒"
        except Exception as e:
            return False, f"等待失败: {str(e)}"
    
    def _handle_execute_script(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理执行脚本动作"""
        try:
            script_path = params.get('script_path')
            script_type = params.get('script_type', 'python')
            
            if script_type == 'python':
                import subprocess
                result = subprocess.run(['python', script_path], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return True, f"Python脚本执行成功: {result.stdout}"
                else:
                    return False, f"Python脚本执行失败: {result.stderr}"
            else:
                return False, f"不支持的脚本类型: {script_type}"
            
        except Exception as e:
            return False, f"执行脚本失败: {str(e)}"
    
    def _handle_file_operation(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理文件操作动作"""
        try:
            operation = params.get('operation')  # copy, move, delete, create
            source = params.get('source')
            destination = params.get('destination')
            
            import shutil
            from pathlib import Path
            
            if operation == 'copy':
                shutil.copy2(source, destination)
                return True, f"复制文件: {source} -> {destination}"
            elif operation == 'move':
                shutil.move(source, destination)
                return True, f"移动文件: {source} -> {destination}"
            elif operation == 'delete':
                Path(source).unlink()
                return True, f"删除文件: {source}"
            elif operation == 'create':
                Path(source).touch()
                return True, f"创建文件: {source}"
            else:
                return False, f"不支持的文件操作: {operation}"
            
        except Exception as e:
            return False, f"文件操作失败: {str(e)}"
    
    def _handle_system_command(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        """处理系统命令动作"""
        try:
            command = params.get('command')
            timeout = params.get('timeout', 30)
            
            import subprocess
            result = subprocess.run(command, shell=True, 
                                  capture_output=True, text=True, timeout=timeout)
            
            if result.returncode == 0:
                return True, f"系统命令执行成功: {result.stdout}"
            else:
                return False, f"系统命令执行失败: {result.stderr}"
            
        except Exception as e:
            return False, f"系统命令执行失败: {str(e)}"

# 单例实例
_automation_engine_instance = None

def get_automation_engine() -> AutomationEngine:
    """获取自动化引擎单例"""
    global _automation_engine_instance
    if _automation_engine_instance is None:
        _automation_engine_instance = AutomationEngine()
    return _automation_engine_instance

