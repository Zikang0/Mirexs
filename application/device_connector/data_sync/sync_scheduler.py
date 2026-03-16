"""
同步调度器模块 - Mirexs数据同步系统

提供同步任务调度功能，包括：
1. 定时同步
2. 事件触发同步
3. 优先级调度
4. 任务依赖
5. 并发控制
6. 调度策略
"""

import logging
import time
import threading
import heapq
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import croniter

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
    FULL_SYNC = "full_sync"
    INCREMENTAL_SYNC = "incremental_sync"
    MERGE_SYNC = "merge_sync"
    CONFLICT_RESOLUTION = "conflict_resolution"
    DATA_CLEANUP = "data_cleanup"
    CUSTOM = "custom"

class TaskPriority(Enum):
    """任务优先级枚举"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

class TriggerType(Enum):
    """触发类型枚举"""
    MANUAL = "manual"          # 手动触发
    SCHEDULE = "schedule"      # 定时触发
    EVENT = "event"            # 事件触发
    DEPENDENCY = "dependency"  # 依赖触发

@dataclass
class ScheduleConfig:
    """调度配置"""
    cron: Optional[str] = None           # Cron表达式
    interval: Optional[int] = None       # 间隔时间（秒）
    start_time: Optional[float] = None   # 开始时间
    end_time: Optional[float] = None     # 结束时间
    max_runs: Optional[int] = None       # 最大运行次数
    timezone: str = "UTC"

@dataclass
class SyncTask:
    """同步任务"""
    id: str
    name: str
    type: TaskType
    priority: TaskPriority
    target_device: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 调度信息
    schedule: Optional[ScheduleConfig] = None
    trigger_type: TriggerType = TriggerType.MANUAL
    status: TaskStatus = TaskStatus.PENDING
    
    # 依赖
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    blocked_by: List[str] = field(default_factory=list)    # 阻塞的任务
    
    # 执行信息
    created_at: float = field(default_factory=time.time)
    scheduled_time: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    
    # 结果
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # 回调
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None

@dataclass
class SchedulerConfig:
    """调度器配置"""
    # 并发配置
    max_concurrent: int = 5
    worker_threads: int = 3
    
    # 队列配置
    max_queue_size: int = 1000
    queue_timeout: int = 60  # 秒
    
    # 重试配置
    retry_on_failure: bool = True
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    
    # 历史记录
    keep_history: bool = True
    max_history: int = 1000

class SyncScheduler:
    """
    同步调度器
    
    负责同步任务的调度和管理。
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None):
        """
        初始化同步调度器
        
        Args:
            config: 调度器配置
        """
        self.config = config or SchedulerConfig()
        
        # 任务存储
        self.tasks: Dict[str, SyncTask] = {}
        self.task_queue: List[tuple] = []  # 优先级队列 (priority, scheduled_time, task_id)
        
        # 正在运行的任务
        self.running_tasks: Dict[str, threading.Thread] = {}
        
        # 任务历史
        self.task_history: List[SyncTask] = []
        
        # 线程锁
        self.queue_lock = threading.Lock()
        
        # 调度线程
        self._scheduler_thread: Optional[threading.Thread] = None
        self._worker_threads: List[threading.Thread] = []
        self._stop_scheduler = threading.Event()
        self._task_available = threading.Event()
        
        # 回调函数
        self.on_task_scheduled: Optional[Callable[[SyncTask], None]] = None
        self.on_task_started: Optional[Callable[[SyncTask], None]] = None
        self.on_task_completed: Optional[Callable[[SyncTask], None]] = None
        self.on_task_failed: Optional[Callable[[SyncTask, str], None]] = None
        self.on_task_cancelled: Optional[Callable[[SyncTask], None]] = None
        
        # 统计
        self.stats = {
            "tasks_scheduled": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "average_wait_time": 0.0,
            "average_execution_time": 0.0
        }
        
        # 启动调度器
        self._start_scheduler()
        
        logger.info("SyncScheduler initialized")
    
    def _start_scheduler(self):
        """启动调度器"""
        def scheduler_loop():
            while not self._stop_scheduler.is_set():
                try:
                    self._check_scheduled_tasks()
                    self._check_dependencies()
                    self._stop_scheduler.wait(1)
                except Exception as e:
                    logger.error(f"Scheduler error: {e}")
        
        def worker_loop(worker_id: int):
            logger.debug(f"Worker {worker_id} started")
            
            while not self._stop_scheduler.is_set():
                try:
                    task = self._get_next_task()
                    if task:
                        self._execute_task(task)
                    else:
                        self._task_available.wait(1)
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
            
            logger.debug(f"Worker {worker_id} stopped")
        
        self._scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        for i in range(self.config.worker_threads):
            worker = threading.Thread(target=worker_loop, args=(i,), daemon=True)
            worker.start()
            self._worker_threads.append(worker)
        
        logger.debug("Sync scheduler started")
    
    def _check_scheduled_tasks(self):
        """检查定时任务"""
        current_time = time.time()
        
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING and task.status != TaskStatus.SCHEDULED:
                continue
            
            if task.schedule and task.schedule.cron:
                # Cron任务
                if task.next_run and current_time >= task.next_run:
                    self._schedule_task(task.id)
            
            elif task.schedule and task.schedule.interval:
                # 间隔任务
                if task.last_run:
                    next_run = task.last_run + task.schedule.interval
                    if current_time >= next_run:
                        self._schedule_task(task.id)
                elif task.created_at:
                    next_run = task.created_at + (task.schedule.interval or 0)
                    if current_time >= next_run:
                        self._schedule_task(task.id)
    
    def _check_dependencies(self):
        """检查任务依赖"""
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            
            if task.dependencies:
                # 检查所有依赖是否完成
                all_completed = True
                blocked_by = []
                
                for dep_id in task.dependencies:
                    dep_task = self.tasks.get(dep_id)
                    if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                        all_completed = False
                        if dep_task and dep_task.status == TaskStatus.FAILED:
                            blocked_by.append(dep_id)
                
                if all_completed:
                    # 依赖全部完成，可以调度
                    task.blocked_by = []
                    self._schedule_task(task.id)
                elif blocked_by:
                    # 被失败的任务阻塞
                    task.status = TaskStatus.BLOCKED
                    task.blocked_by = blocked_by
                    logger.debug(f"Task {task.id} blocked by: {blocked_by}")
    
    def _schedule_task(self, task_id: str):
        """调度任务"""
        with self.queue_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            # 更新状态
            task.status = TaskStatus.SCHEDULED
            task.scheduled_time = time.time()
            
            # 计算优先级值（数字越小优先级越高）
            priority_value = task.priority.value
            
            # 添加到优先级队列
            heapq.heappush(self.task_queue, (priority_value, task.scheduled_time, task_id))
            
            logger.debug(f"Task scheduled: {task.name} ({task_id})")
            
            if self.on_task_scheduled:
                self.on_task_scheduled(task)
            
            # 通知有任务可用
            self._task_available.set()
    
    def _get_next_task(self) -> Optional[SyncTask]:
        """获取下一个任务"""
        with self.queue_lock:
            if not self.task_queue:
                self._task_available.clear()
                return None
            
            # 检查并发限制
            if len(self.running_tasks) >= self.config.max_concurrent:
                return None
            
            # 获取下一个任务
            priority, scheduled_time, task_id = heapq.heappop(self.task_queue)
            
            task = self.tasks.get(task_id)
            if not task:
                return self._get_next_task()
            
            return task
    
    def _execute_task(self, task: SyncTask):
        """执行任务"""
        # 更新状态
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        task.run_count += 1
        
        # 记录开始时间
        wait_time = task.start_time - (task.scheduled_time or task.created_at)
        
        logger.info(f"Executing task: {task.name} (wait time: {wait_time:.2f}s)")
        
        if self.on_task_started:
            self.on_task_started(task)
        
        # 在独立线程中执行
        def run():
            try:
                # 执行任务
                result = self._execute_task_logic(task)
                
                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()
                task.result = result
                
                execution_time = task.end_time - task.start_time
                
                self.stats["tasks_completed"] += 1
                
                # 更新平均等待时间
                total_completed = self.stats["tasks_completed"]
                current_avg_wait = self.stats["average_wait_time"]
                self.stats["average_wait_time"] = (current_avg_wait * (total_completed - 1) + wait_time) / total_completed
                
                # 更新平均执行时间
                current_avg_exec = self.stats["average_execution_time"]
                self.stats["average_execution_time"] = (current_avg_exec * (total_completed - 1) + execution_time) / total_completed
                
                logger.info(f"Task completed: {task.name} ({execution_time:.2f}s)")
                
                if self.on_task_completed:
                    self.on_task_completed(task)
                
                if task.on_complete:
                    task.on_complete(task)
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.end_time = time.time()
                task.error = str(e)
                
                self.stats["tasks_failed"] += 1
                
                logger.error(f"Task failed: {task.name} - {e}")
                
                if self.on_task_failed:
                    self.on_task_failed(task, str(e))
                
                if task.on_error:
                    task.on_error(task, str(e))
                
                # 重试逻辑
                if self.config.retry_on_failure and task.run_count < self.config.max_retries:
                    self._retry_task(task)
            
            finally:
                # 从运行中移除
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]
                
                # 添加到历史
                if self.config.keep_history:
                    self.task_history.append(task)
                    if len(self.task_history) > self.config.max_history:
                        self.task_history = self.task_history[-self.config.max_history:]
        
        thread = threading.Thread(target=run, daemon=True)
        self.running_tasks[task.id] = thread
        thread.start()
    
    def _execute_task_logic(self, task: SyncTask) -> Optional[Dict[str, Any]]:
        """执行任务逻辑"""
        # 实际实现中会调用相应的同步功能
        # 这里返回模拟结果
        import random
        time.sleep(random.uniform(0.5, 2.0))
        
        return {
            "task_id": task.id,
            "items_processed": random.randint(10, 100),
            "bytes_transferred": random.randint(1024, 102400)
        }
    
    def _retry_task(self, task: SyncTask):
        """重试任务"""
        logger.info(f"Retrying task: {task.name} (attempt {task.run_count}/{self.config.max_retries})")
        
        # 重置状态
        task.status = TaskStatus.PENDING
        task.error = None
        
        # 延迟重试
        delay = self.config.retry_delay * (2 ** (task.run_count - 1))
        
        # 创建延迟任务
        retry_task = SyncTask(
            id=f"retry_{task.id}_{task.run_count}",
            name=f"Retry: {task.name}",
            type=task.type,
            priority=TaskPriority(task.priority.value + 1),  # 降低优先级
            target_device=task.target_device,
            config=task.config,
            dependencies=task.dependencies
        )
        
        # 设置延迟
        retry_task.schedule = ScheduleConfig(
            interval=delay,
            start_time=time.time() + delay
        )
        
        self.add_task(retry_task)
    
    def add_task(self, task: SyncTask) -> str:
        """
        添加任务
        
        Args:
            task: 同步任务
        
        Returns:
            任务ID
        """
        if not task.id:
            task.id = str(uuid.uuid4())
        
        self.tasks[task.id] = task
        self.stats["tasks_scheduled"] += 1
        
        # 计算下次运行时间
        if task.schedule:
            if task.schedule.cron:
                # 解析Cron表达式
                try:
                    cron = croniter.croniter(task.schedule.cron, datetime.now())
                    task.next_run = cron.get_next(float)
                except:
                    task.next_run = time.time()
            elif task.schedule.interval:
                task.next_run = time.time() + task.schedule.interval
        
        # 如果没有依赖，立即调度
        if not task.dependencies:
            self._schedule_task(task.id)
        
        logger.info(f"Task added: {task.name} ({task.id})")
        
        return task.id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return False
        
        task = self.tasks[task_id]
        
        if task.status == TaskStatus.RUNNING:
            # 无法取消正在运行的任务
            logger.warning(f"Cannot cancel running task: {task_id}")
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            logger.warning(f"Task already in final state: {task.status.value}")
            return False
        
        task.status = TaskStatus.CANCELLED
        task.end_time = time.time()
        
        self.stats["tasks_cancelled"] += 1
        
        logger.info(f"Task cancelled: {task.name} ({task_id})")
        
        if self.on_task_cancelled:
            self.on_task_cancelled(task)
        
        return True
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status == TaskStatus.SCHEDULED:
            task.status = TaskStatus.PENDING
            logger.info(f"Task paused: {task.name} ({task_id})")
            return True
        
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否成功
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status == TaskStatus.PENDING:
            self._schedule_task(task_id)
            logger.info(f"Task resumed: {task.name} ({task_id})")
            return True
        
        return False
    
    def get_task(self, task_id: str) -> Optional[SyncTask]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            同步任务
        """
        return self.tasks.get(task_id)
    
    def get_tasks(self, status: Optional[TaskStatus] = None,
                 type: Optional[TaskType] = None) -> List[SyncTask]:
        """
        获取任务列表
        
        Args:
            status: 状态过滤
            type: 类型过滤
        
        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if type:
            tasks = [t for t in tasks if t.type == type]
        
        return tasks
    
    def get_task_history(self, limit: int = 100) -> List[SyncTask]:
        """
        获取任务历史
        
        Args:
            limit: 返回数量
        
        Returns:
            任务列表
        """
        return self.task_history[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            状态字典
        """
        return {
            "tasks": {
                "total": len(self.tasks),
                "pending": len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                "scheduled": len([t for t in self.tasks.values() if t.status == TaskStatus.SCHEDULED]),
                "running": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
                "completed": len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                "failed": len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
                "cancelled": len([t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED]),
                "blocked": len([t for t in self.tasks.values() if t.status == TaskStatus.BLOCKED])
            },
            "queue_size": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "history_size": len(self.task_history),
            "stats": self.stats,
            "config": {
                "max_concurrent": self.config.max_concurrent,
                "worker_threads": self.config.worker_threads
            }
        }
    
    def shutdown(self):
        """关闭调度器"""
        logger.info("Shutting down SyncScheduler...")
        
        self._stop_scheduler.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2)
        
        for worker in self._worker_threads:
            if worker.is_alive():
                worker.join(timeout=2)
        
        # 取消所有任务
        for task_id in list(self.tasks.keys()):
            self.cancel_task(task_id)
        
        self.tasks.clear()
        self.task_queue.clear()
        self.running_tasks.clear()
        self.task_history.clear()
        
        logger.info("SyncScheduler shutdown completed")

# 单例模式实现
_sync_scheduler_instance: Optional[SyncScheduler] = None

def get_sync_scheduler(config: Optional[SchedulerConfig] = None) -> SyncScheduler:
    """
    获取同步调度器单例
    
    Args:
        config: 调度器配置
    
    Returns:
        同步调度器实例
    """
    global _sync_scheduler_instance
    if _sync_scheduler_instance is None:
        _sync_scheduler_instance = SyncScheduler(config)
    return _sync_scheduler_instance

