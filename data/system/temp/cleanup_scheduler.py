"""
清理调度器模块 - 定期清理临时文件
负责调度和执行定期清理任务
"""

import time
import threading
import schedule
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

class CleanupTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CleanupTask:
    task_id: str
    name: str
    description: str
    schedule_pattern: str
    function: Callable
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    status: CleanupTaskStatus = CleanupTaskStatus.PENDING
    enabled: bool = True
    metadata: Dict[str, Any] = None

class CleanupScheduler:
    """清理调度器"""
    
    def __init__(self, auto_start: bool = True):
        self.tasks: Dict[str, CleanupTask] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.logger = self._setup_logging()
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_execution_time": 0,
            "last_cleanup_time": 0
        }
        
        # 注册默认清理任务
        self._register_default_tasks()
        
        if auto_start:
            self.start()
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("cleanup_scheduler")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def _register_default_tasks(self):
        """注册默认清理任务"""
        # 临时文件清理任务
        self.add_task(
            "cleanup_temp_files",
            "清理临时文件",
            "清理过期的临时文件和缓存",
            "0 2 * * *",  # 每天凌晨2点
            self._cleanup_temp_files
        )
        
        # 会话数据清理任务
        self.add_task(
            "cleanup_sessions", 
            "清理会话数据",
            "清理过期的用户会话数据",
            "*/30 * * * *",  # 每30分钟
            self._cleanup_sessions
        )
        
        # 缓存清理任务
        self.add_task(
            "cleanup_caches",
            "清理缓存",
            "清理过期的内存和磁盘缓存",
            "0 */6 * * *",  # 每6小时
            self._cleanup_caches
        )
        
        # 日志文件清理任务
        self.add_task(
            "cleanup_logs",
            "清理日志文件",
            "清理旧的日志文件",
            "0 1 * * 0",  # 每周日凌晨1点
            self._cleanup_logs
        )
    
    def add_task(self, 
                task_id: str, 
                name: str, 
                description: str, 
                schedule_pattern: str, 
                function: Callable) -> bool:
        """
        添加清理任务
        
        Args:
            task_id: 任务ID
            name: 任务名称
            description: 任务描述
            schedule_pattern: 调度模式（cron格式）
            function: 执行函数
            
        Returns:
            是否添加成功
        """
        if task_id in self.tasks:
            self.logger.warning(f"任务ID已存在: {task_id}")
            return False
        
        task = CleanupTask(
            task_id=task_id,
            name=name,
            description=description,
            schedule_pattern=schedule_pattern,
            function=function,
            metadata={}
        )
        
        self.tasks[task_id] = task
        
        # 注册到schedule
        if self.running and task.enabled:
            self._schedule_task(task)
        
        self.stats["total_tasks"] = len(self.tasks)
        self.logger.info(f"添加清理任务: {name}")
        
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """
        移除清理任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否移除成功
        """
        if task_id not in self.tasks:
            return False
        
        # 从schedule中取消
        if self.running:
            schedule.clear(task_id)
        
        del self.tasks[task_id]
        self.stats["total_tasks"] = len(self.tasks)
        self.logger.info(f"移除清理任务: {task_id}")
        
        return True
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.enabled = True
        
        if self.running:
            self._schedule_task(task)
        
        self.logger.info(f"启用清理任务: {task_id}")
        return True
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        task.enabled = False
        
        if self.running:
            schedule.clear(task_id)
        
        self.logger.info(f"禁用清理任务: {task_id}")
        return True
    
    def run_task_now(self, task_id: str) -> bool:
        """立即运行任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        self._execute_task(task)
        
        return True
    
    def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        
        # 调度所有启用的任务
        for task in self.tasks.values():
            if task.enabled:
                self._schedule_task(task)
        
        # 启动调度线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("清理调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        self.logger.info("清理调度器已停止")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "schedule_pattern": task.schedule_pattern,
            "status": task.status.value,
            "enabled": task.enabled,
            "last_run": task.last_run,
            "next_run": task.next_run,
            "metadata": task.metadata
        }
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
        pending_tasks = sum(1 for task in self.tasks.values() if task.status == CleanupTaskStatus.PENDING)
        running_tasks = sum(1 for task in self.tasks.values() if task.status == CleanupTaskStatus.RUNNING)
        
        return {
            **self.stats,
            "enabled_tasks": enabled_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "scheduler_running": self.running
        }
    
    def _schedule_task(self, task: CleanupTask):
        """调度任务"""
        try:
            # 解析cron格式并调度
            parts = task.schedule_pattern.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                
                job = schedule.every()
                
                # 设置分钟
                if minute != '*':
                    job = job.minute.at(minute)
                
                # 设置小时
                if hour != '*':
                    job = job.hour.at(hour)
                
                # 设置日期
                if day != '*':
                    job = job.day.at(day)
                
                # 设置月份
                if month != '*':
                    job = job.month.at(month)
                
                # 设置星期
                if day_of_week != '*':
                    job = job.week.at(day_of_week)
                
                # 注册任务
                job.do(self._execute_task, task).tag(task.task_id)
                
                # 计算下次运行时间
                task.next_run = time.time() + 60  # 简化计算
                
                self.logger.info(f"已调度任务: {task.name} - {task.schedule_pattern}")
            
            else:
                self.logger.error(f"无效的调度模式: {task.schedule_pattern}")
                
        except Exception as e:
            self.logger.error(f"调度任务失败 {task.name}: {e}")
    
    def _execute_task(self, task: CleanupTask):
        """执行任务"""
        task.status = CleanupTaskStatus.RUNNING
        task.last_run = time.time()
        
        self.logger.info(f"开始执行清理任务: {task.name}")
        
        start_time = time.time()
        success = False
        
        try:
            # 执行清理函数
            result = task.function()
            success = True
            
            task.status = CleanupTaskStatus.COMPLETED
            self.stats["completed_tasks"] += 1
            
            execution_time = time.time() - start_time
            self.stats["total_execution_time"] += execution_time
            self.stats["last_cleanup_time"] = time.time()
            
            # 记录执行结果
            task.metadata = task.metadata or {}
            task.metadata.update({
                "last_execution_time": execution_time,
                "last_success": True,
                "last_result": result
            })
            
            self.logger.info(f"清理任务完成: {task.name} - 耗时: {execution_time:.2f}秒")
            
        except Exception as e:
            task.status = CleanupTaskStatus.FAILED
            self.stats["failed_tasks"] += 1
            
            task.metadata = task.metadata or {}
            task.metadata.update({
                "last_execution_time": time.time() - start_time,
                "last_success": False,
                "last_error": str(e)
            })
            
            self.logger.error(f"清理任务失败 {task.name}: {e}")
        
        return success
    
    def _scheduler_worker(self):
        """调度器工作线程"""
        self.logger.info("调度器工作线程已启动")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"调度器工作线程错误: {e}")
                time.sleep(10)
    
    def _cleanup_temp_files(self) -> Dict[str, Any]:
        """清理临时文件任务"""
        try:
            from data.system.temp.temp_file_manager import temp_file_manager
            
            deleted_count = temp_file_manager.cleanup_expired()
            total_files = len(temp_file_manager.file_index)
            
            self.logger.info(f"临时文件清理完成: 删除了 {deleted_count} 个文件，剩余 {total_files} 个文件")
            
            return {
                "deleted_files": deleted_count,
                "remaining_files": total_files,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"临时文件清理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cleanup_sessions(self) -> Dict[str, Any]:
        """清理会话数据任务"""
        try:
            from data.system.temp.session_data import session_manager
            
            expired_count = session_manager.cleanup_expired_sessions()
            total_sessions = len(session_manager.sessions)
            
            self.logger.info(f"会话数据清理完成: 删除了 {expired_count} 个会话，剩余 {total_sessions} 个会话")
            
            return {
                "expired_sessions": expired_count,
                "remaining_sessions": total_sessions,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"会话数据清理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cleanup_caches(self) -> Dict[str, Any]:
        """清理缓存任务"""
        try:
            from data.system.cache.memory_cache import memory_cache
            from data.system.cache.disk_cache import disk_cache
            
            memory_cleaned = memory_cache.cleanup_expired()
            disk_cleaned = disk_cache.cleanup_expired()
            
            memory_stats = memory_cache.get_stats()
            disk_stats = disk_cache.get_stats()
            
            self.logger.info(f"缓存清理完成: 内存缓存 {memory_cleaned} 项，磁盘缓存 {disk_cleaned} 项")
            
            return {
                "memory_cache_cleaned": memory_cleaned,
                "disk_cache_cleaned": disk_cleaned,
                "memory_cache_stats": memory_stats,
                "disk_cache_stats": disk_stats,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"缓存清理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _cleanup_logs(self) -> Dict[str, Any]:
        """清理日志文件任务"""
        try:
            from data.system.logs.log_rotator import log_rotator
            
            # 清理各种类型的日志
            cleaned_count = 0
            for log_type in ["system", "security", "performance", "interaction", "error", "audit"]:
                deleted = log_rotator.cleanup_expired_logs(log_type)
                cleaned_count += deleted
            
            log_stats = log_rotator.get_log_stats()
            
            self.logger.info(f"日志文件清理完成: 删除了 {cleaned_count} 个日志文件")
            
            return {
                "cleaned_log_files": cleaned_count,
                "log_stats": log_stats,
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"日志文件清理失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 全局清理调度器实例
cleanup_scheduler = CleanupScheduler(auto_start=True)

