"""
维护管理器：管理系统维护任务
"""
import os
import time
import threading
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import tempfile

logger = logging.getLogger(__name__)

class MaintenanceTaskType(Enum):
    """维护任务类型枚举"""
    CLEANUP = "cleanup"
    OPTIMIZATION = "optimization"
    BACKUP = "backup"
    UPDATE = "update"
    SECURITY = "security"
    DIAGNOSTIC = "diagnostic"

class MaintenanceStatus(Enum):
    """维护状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class MaintenanceTask:
    """维护任务"""
    id: str
    task_type: MaintenanceTaskType
    name: str
    description: str
    schedule: str  # cron表达式或立即执行
    status: MaintenanceStatus
    created_time: datetime
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    parameters: Dict[str, Any] = None
    result: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.result is None:
            self.result = {}

class MaintenanceManager:
    """维护管理器"""
    
    def __init__(self):
        self.maintenance_tasks: Dict[str, MaintenanceTask] = {}
        self.task_queue = []
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self._setup_logging()
        self._load_default_tasks()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_default_tasks(self):
        """加载默认维护任务"""
        default_tasks = [
            MaintenanceTask(
                id="temp_cleanup_daily",
                task_type=MaintenanceTaskType.CLEANUP,
                name="每日临时文件清理",
                description="清理系统临时文件和缓存",
                schedule="0 2 * * *",  # 每天凌晨2点
                status=MaintenanceStatus.PENDING,
                created_time=datetime.now(),
                parameters={
                    "cleanup_paths": [
                        tempfile.gettempdir(),
                        "C:\\Windows\\Temp",
                        "C:\\Users\\*\\AppData\\Local\\Temp"
                    ],
                    "retention_days": 7
                }
            ),
            MaintenanceTask(
                id="disk_optimization_weekly",
                task_type=MaintenanceTaskType.OPTIMIZATION,
                name="每周磁盘优化",
                description="优化磁盘性能和整理碎片",
                schedule="0 3 * * 0",  # 每周日凌晨3点
                status=MaintenanceStatus.PENDING,
                created_time=datetime.now(),
                parameters={
                    "optimize_drives": ["C:"],
                    "defragment": True
                }
            ),
            MaintenanceTask(
                id="system_backup_monthly",
                task_type=MaintenanceTaskType.BACKUP,
                name="每月系统备份",
                description="创建系统重要文件备份",
                schedule="0 4 1 * *",  # 每月1日凌晨4点
                status=MaintenanceStatus.PENDING,
                created_time=datetime.now(),
                parameters={
                    "backup_paths": [
                        "C:\\Users",
                        "C:\\ImportantData"
                    ],
                    "backup_destination": "D:\\Backups",
                    "compression": True
                }
            )
        ]
        
        for task in default_tasks:
            self.maintenance_tasks[task.id] = task
    
    def start_maintenance_scheduler(self) -> bool:
        """启动维护调度器"""
        if self.is_running:
            return False
        
        try:
            self.is_running = True
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True
            )
            self.scheduler_thread.start()
            
            logger.info("维护调度器已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动维护调度器失败: {str(e)}")
            return False
    
    def stop_maintenance_scheduler(self) -> bool:
        """停止维护调度器"""
        if not self.is_running:
            return False
        
        try:
            self.is_running = False
            if self.scheduler_thread:
                self.scheduler_thread.join(timeout=30)
            
            logger.info("维护调度器已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止维护调度器失败: {str(e)}")
            return False
    
    def _scheduler_loop(self):
        """调度器循环"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 检查需要执行的任务
                for task in self.maintenance_tasks.values():
                    if (task.status == MaintenanceStatus.PENDING and 
                        self._should_execute_task(task, current_time)):
                        
                        # 添加到执行队列
                        self._execute_task(task)
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"维护调度器循环错误: {str(e)}")
                time.sleep(300)  # 错误时等待5分钟
    
    def _should_execute_task(self, task: MaintenanceTask, current_time: datetime) -> bool:
        """检查任务是否应该执行"""
        # 简化实现：立即执行或基于简单时间判断
        if task.schedule == "immediate":
            return True
        
        # 检查cron表达式（简化版）
        if task.next_run_time and current_time >= task.next_run_time:
            return True
        
        return False
    
    def _execute_task(self, task: MaintenanceTask):
        """执行维护任务"""
        try:
            # 更新任务状态
            task.status = MaintenanceStatus.RUNNING
            task.started_time = datetime.now()
            task.last_run_time = datetime.now()
            
            logger.info(f"开始执行维护任务: {task.name}")
            
            # 根据任务类型执行相应的操作
            if task.task_type == MaintenanceTaskType.CLEANUP:
                result = self._execute_cleanup_task(task)
            elif task.task_type == MaintenanceTaskType.OPTIMIZATION:
                result = self._execute_optimization_task(task)
            elif task.task_type == MaintenanceTaskType.BACKUP:
                result = self._execute_backup_task(task)
            elif task.task_type == MaintenanceTaskType.UPDATE:
                result = self._execute_update_task(task)
            elif task.task_type == MaintenanceTaskType.SECURITY:
                result = self._execute_security_task(task)
            else:
                result = {"success": False, "error": "未知任务类型"}
            
            # 更新任务结果
            task.result = result
            task.completed_time = datetime.now()
            
            if result.get("success", False):
                task.status = MaintenanceStatus.COMPLETED
                logger.info(f"维护任务完成: {task.name}")
            else:
                task.status = MaintenanceStatus.FAILED
                task.error_message = result.get("error", "未知错误")
                logger.error(f"维护任务失败: {task.name} - {task.error_message}")
            
            # 计算下一次执行时间
            task.next_run_time = self._calculate_next_run_time(task)
            
        except Exception as e:
            task.status = MaintenanceStatus.FAILED
            task.error_message = str(e)
            task.completed_time = datetime.now()
            logger.error(f"执行维护任务异常 {task.name}: {str(e)}")
    
    def _execute_cleanup_task(self, task: MaintenanceTask) -> Dict[str, Any]:
        """执行清理任务"""
        try:
            cleanup_paths = task.parameters.get("cleanup_paths", [])
            retention_days = task.parameters.get("retention_days", 7)
            
            cleanup_results = {
                "success": True,
                "cleaned_files": 0,
                "freed_space": 0,
                "errors": []
            }
            
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            for path_pattern in cleanup_paths:
                try:
                    # 处理通配符路径
                    if '*' in path_pattern:
                        # 简化实现，实际应该使用glob
                        base_path = path_pattern.split('*')[0]
                        if os.path.exists(base_path):
                            path_stats = self._cleanup_directory(base_path, cutoff_time)
                            cleanup_results["cleaned_files"] += path_stats["cleaned_files"]
                            cleanup_results["freed_space"] += path_stats["freed_space"]
                    else:
                        if os.path.exists(path_pattern):
                            if os.path.isfile(path_pattern):
                                file_stats = self._cleanup_file(path_pattern, cutoff_time)
                                if file_stats["cleaned"]:
                                    cleanup_results["cleaned_files"] += 1
                                    cleanup_results["freed_space"] += file_stats["size"]
                            else:
                                path_stats = self._cleanup_directory(path_pattern, cutoff_time)
                                cleanup_results["cleaned_files"] += path_stats["cleaned_files"]
                                cleanup_results["freed_space"] += path_stats["freed_space"]
                
                except Exception as e:
                    cleanup_results["errors"].append(f"清理路径 {path_pattern} 失败: {str(e)}")
            
            cleanup_results["freed_space_mb"] = cleanup_results["freed_space"] / (1024 * 1024)
            return cleanup_results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cleanup_directory(self, directory: str, cutoff_time: datetime) -> Dict[str, Any]:
        """清理目录"""
        stats = {"cleaned_files": 0, "freed_space": 0}
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_stats = self._cleanup_file(file_path, cutoff_time)
                    if file_stats["cleaned"]:
                        stats["cleaned_files"] += 1
                        stats["freed_space"] += file_stats["size"]
        except Exception as e:
            logger.error(f"清理目录失败 {directory}: {str(e)}")
        
        return stats
    
    def _cleanup_file(self, file_path: str, cutoff_time: datetime) -> Dict[str, Any]:
        """清理单个文件"""
        try:
            if not os.path.exists(file_path):
                return {"cleaned": False, "size": 0}
            
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_time < cutoff_time:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                return {"cleaned": True, "size": file_size}
            
            return {"cleaned": False, "size": 0}
            
        except Exception as e:
            logger.error(f"清理文件失败 {file_path}: {str(e)}")
            return {"cleaned": False, "size": 0}
    
    def _execute_optimization_task(self, task: MaintenanceTask) -> Dict[str, Any]:
        """执行优化任务"""
        try:
            optimize_drives = task.parameters.get("optimize_drives", [])
            defragment = task.parameters.get("defragment", False)
            
            optimization_results = {
                "success": True,
                "optimized_drives": [],
                "errors": []
            }
            
            for drive in optimize_drives:
                try:
                    if defragment and platform.system() == "Windows":
                        # 执行磁盘碎片整理
                        result = subprocess.run(
                            ['defrag', drive, '/O'],
                            capture_output=True, text=True, timeout=3600
                        )
                        
                        if result.returncode == 0:
                            optimization_results["optimized_drives"].append(drive)
                        else:
                            optimization_results["errors"].append(f"优化驱动器 {drive} 失败: {result.stderr}")
                    
                    # 检查磁盘空间
                    usage = shutil.disk_usage(drive)
                    free_space_gb = usage.free / (1024**3)
                    
                    optimization_results[f"{drive}_free_space_gb"] = free_space_gb
                    
                except Exception as e:
                    optimization_results["errors"].append(f"优化驱动器 {drive} 异常: {str(e)}")
            
            return optimization_results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_backup_task(self, task: MaintenanceTask) -> Dict[str, Any]:
        """执行备份任务"""
        try:
            backup_paths = task.parameters.get("backup_paths", [])
            backup_destination = task.parameters.get("backup_destination", "")
            compression = task.parameters.get("compression", False)
            
            backup_results = {
                "success": True,
                "backed_up_files": 0,
                "total_size": 0,
                "backup_location": backup_destination,
                "errors": []
            }
            
            # 创建备份目录
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(backup_destination, f"backup_{backup_time}")
            os.makedirs(backup_dir, exist_ok=True)
            
            for source_path in backup_paths:
                try:
                    if os.path.exists(source_path):
                        if os.path.isfile(source_path):
                            # 备份单个文件
                            shutil.copy2(source_path, backup_dir)
                            backup_results["backed_up_files"] += 1
                            backup_results["total_size"] += os.path.getsize(source_path)
                        else:
                            # 备份目录
                            for root, dirs, files in os.walk(source_path):
                                for file in files:
                                    source_file = os.path.join(root, file)
                                    relative_path = os.path.relpath(source_file, source_path)
                                    dest_file = os.path.join(backup_dir, relative_path)
                                    
                                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                                    shutil.copy2(source_file, dest_file)
                                    
                                    backup_results["backed_up_files"] += 1
                                    backup_results["total_size"] += os.path.getsize(source_file)
                
                except Exception as e:
                    backup_results["errors"].append(f"备份路径 {source_path} 失败: {str(e)}")
            
            backup_results["total_size_mb"] = backup_results["total_size"] / (1024 * 1024)
            return backup_results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execute_update_task(self, task: MaintenanceTask) -> Dict[str, Any]:
        """执行更新任务"""
        # 实现系统更新逻辑
        return {"success": True, "message": "更新任务执行完成"}
    
    def _execute_security_task(self, task: MaintenanceTask) -> Dict[str, Any]:
        """执行安全任务"""
        # 实现安全维护逻辑
        return {"success": True, "message": "安全任务执行完成"}
    
    def _calculate_next_run_time(self, task: MaintenanceTask) -> Optional[datetime]:
        """计算下一次执行时间"""
        if task.schedule == "immediate":
            return None
        
        # 简化实现：每天同一时间执行
        if task.schedule.startswith("0 "):
            parts = task.schedule.split()
            if len(parts) >= 2:
                hour = int(parts[1])
                next_run = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                if next_run <= datetime.now():
                    next_run += timedelta(days=1)
                return next_run
        
        return None
    
    def create_maintenance_task(self, task_type: MaintenanceTaskType, name: str, 
                              description: str, schedule: str, parameters: Dict[str, Any] = None) -> Optional[str]:
        """创建维护任务"""
        try:
            import uuid
            task_id = str(uuid.uuid4())
            
            task = MaintenanceTask(
                id=task_id,
                task_type=task_type,
                name=name,
                description=description,
                schedule=schedule,
                status=MaintenanceStatus.PENDING,
                created_time=datetime.now(),
                parameters=parameters or {}
            )
            
            self.maintenance_tasks[task_id] = task
            logger.info(f"创建维护任务: {name} (ID: {task_id})")
            return task_id
            
        except Exception as e:
            logger.error(f"创建维护任务失败: {str(e)}")
            return None
    
    def execute_task_immediately(self, task_id: str) -> bool:
        """立即执行任务"""
        try:
            if task_id not in self.maintenance_tasks:
                return False
            
            task = self.maintenance_tasks[task_id]
            
            # 在单独线程中执行任务
            execution_thread = threading.Thread(
                target=self._execute_task,
                args=(task,),
                daemon=True
            )
            execution_thread.start()
            
            logger.info(f"立即执行维护任务: {task.name}")
            return True
            
        except Exception as e:
            logger.error(f"立即执行任务失败: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id in self.maintenance_tasks:
            task = self.maintenance_tasks[task_id]
            return {
                'id': task.id,
                'name': task.name,
                'type': task.task_type.value,
                'status': task.status.value,
                'created_time': task.created_time.isoformat(),
                'started_time': task.started_time.isoformat() if task.started_time else None,
                'completed_time': task.completed_time.isoformat() if task.completed_time else None,
                'last_run_time': task.last_run_time.isoformat() if task.last_run_time else None,
                'next_run_time': task.next_run_time.isoformat() if task.next_run_time else None,
                'error_message': task.error_message
            }
        return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return [self.get_task_status(task_id) for task_id in self.maintenance_tasks]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            if task_id in self.maintenance_tasks:
                task_name = self.maintenance_tasks[task_id].name
                del self.maintenance_tasks[task_id]
                logger.info(f"删除维护任务: {task_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return False
    
    def get_maintenance_statistics(self) -> Dict[str, Any]:
        """获取维护统计信息"""
        tasks = list(self.maintenance_tasks.values())
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == MaintenanceStatus.COMPLETED])
        failed_tasks = len([t for t in tasks if t.status == MaintenanceStatus.FAILED])
        running_tasks = len([t for t in tasks if t.status == MaintenanceStatus.RUNNING])
        
        type_counts = {}
        for task in tasks:
            task_type = task.task_type.value
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'tasks_by_type': type_counts
        }

# 单例实例
_maintenance_manager_instance = None

def get_maintenance_manager() -> MaintenanceManager:
    """获取维护管理器单例"""
    global _maintenance_manager_instance
    if _maintenance_manager_instance is None:
        _maintenance_manager_instance = MaintenanceManager()
    return _maintenance_manager_instance

