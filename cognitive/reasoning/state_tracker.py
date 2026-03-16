"""
状态跟踪器 - 跟踪任务执行状态和系统状态
维护完整的状态机和状态历史
"""

import logging
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import threading
from collections import deque

logger = logging.getLogger(__name__)

class TaskState(Enum):
    """任务状态枚举"""
    PENDING = "pending"  # 等待中
    READY = "ready"  # 准备执行
    RUNNING = "running"  # 执行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 已失败
    CANCELLED = "cancelled"  # 已取消

class SystemState(Enum):
    """系统状态枚举"""
    INITIALIZING = "initializing"  # 初始化中
    READY = "ready"  # 准备就绪
    BUSY = "busy"  # 忙碌中
    IDLE = "idle"  # 空闲中
    ERROR = "error"  # 错误状态
    MAINTENANCE = "maintenance"  # 维护中

@dataclass
class TaskStatus:
    """任务状态"""
    task_id: str
    state: TaskState
    progress: float  # 进度 0-1
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    current_step: str
    error_message: Optional[str] = None
    retry_count: int = 0
    dependencies: List[str] = field(default_factory=list)

@dataclass
class SystemStatus:
    """系统状态"""
    system_state: SystemState
    active_tasks: int
    queued_tasks: int
    completed_tasks: int
    failed_tasks: int
    cpu_usage: float
    memory_usage: float
    last_update: datetime

@dataclass
class StateSnapshot:
    """状态快照"""
    timestamp: datetime
    task_states: Dict[str, TaskStatus]
    system_status: SystemStatus
    context_data: Dict[str, Any]

class StateTracker:
    """状态跟踪器"""
    
    def __init__(self, max_history_size: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size
        
        # 状态存储
        self.task_states: Dict[str, TaskStatus] = {}
        self.system_status = SystemStatus(
            system_state=SystemState.INITIALIZING,
            active_tasks=0,
            queued_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            cpu_usage=0.0,
            memory_usage=0.0,
            last_update=datetime.now()
        )
        
        # 状态历史
        self.state_history: deque[StateSnapshot] = deque(maxlen=max_history_size)
        
        # 状态转换规则
        self.state_transitions = self._initialize_state_transitions()
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 监控线程
        self._monitor_thread = None
        self._monitoring = False
        
        self.logger.info("状态跟踪器初始化完成")
    
    def _initialize_state_transitions(self) -> Dict[TaskState, Set[TaskState]]:
        """初始化状态转换规则"""
        return {
            TaskState.PENDING: {TaskState.READY, TaskState.CANCELLED},
            TaskState.READY: {TaskState.RUNNING, TaskState.CANCELLED},
            TaskState.RUNNING: {TaskState.PAUSED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED},
            TaskState.PAUSED: {TaskState.RUNNING, TaskState.CANCELLED},
            TaskState.COMPLETED: set(),
            TaskState.FAILED: {TaskState.READY},  # 重试
            TaskState.CANCELLED: set()
        }
    
    def register_task(self, task_id: str, dependencies: List[str] = None) -> bool:
        """
        注册新任务
        
        Args:
            task_id: 任务ID
            dependencies: 依赖任务列表
            
        Returns:
            bool: 是否成功注册
        """
        with self._lock:
            if task_id in self.task_states:
                self.logger.warning(f"任务已存在: {task_id}")
                return False
            
            task_status = TaskStatus(
                task_id=task_id,
                state=TaskState.PENDING,
                progress=0.0,
                start_time=None,
                end_time=None,
                current_step="等待启动",
                dependencies=dependencies or []
            )
            
            self.task_states[task_id] = task_status
            self._update_system_status()
            
            self.logger.info(f"注册新任务: {task_id}")
            return True
    
    def update_task_state(self, task_id: str, new_state: TaskState, 
                         progress: float = None, current_step: str = None,
                         error_message: str = None) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            new_state: 新状态
            progress: 进度
            current_step: 当前步骤
            error_message: 错误信息
            
        Returns:
            bool: 是否成功更新
        """
        with self._lock:
            if task_id not in self.task_states:
                self.logger.error(f"任务不存在: {task_id}")
                return False
            
            current_status = self.task_states[task_id]
            
            # 检查状态转换是否有效
            if not self._is_valid_transition(current_status.state, new_state):
                self.logger.error(f"无效状态转换: {current_status.state.value} -> {new_state.value}")
                return False
            
            # 更新状态
            current_status.state = new_state
            
            if progress is not None:
                current_status.progress = max(0.0, min(1.0, progress))
            
            if current_step is not None:
                current_status.current_step = current_step
            
            if error_message is not None:
                current_status.error_message = error_message
                if new_state == TaskState.FAILED:
                    current_status.retry_count += 1
            
            # 设置时间戳
            if new_state == TaskState.RUNNING and current_status.start_time is None:
                current_status.start_time = datetime.now()
            elif new_state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
                current_status.end_time = datetime.now()
            
            self.logger.info(f"任务状态更新: {task_id} -> {new_state.value} (进度: {current_status.progress})")
            
            # 更新系统状态并保存快照
            self._update_system_status()
            self._save_snapshot()
            
            return True
    
    def _is_valid_transition(self, from_state: TaskState, to_state: TaskState) -> bool:
        """检查状态转换是否有效"""
        return to_state in self.state_transitions.get(from_state, set())
    
    def _update_system_status(self):
        """更新系统状态"""
        with self._lock:
            # 统计任务状态
            active_tasks = 0
            queued_tasks = 0
            completed_tasks = 0
            failed_tasks = 0
            
            for status in self.task_states.values():
                if status.state == TaskState.RUNNING:
                    active_tasks += 1
                elif status.state in [TaskState.PENDING, TaskState.READY]:
                    queued_tasks += 1
                elif status.state == TaskState.COMPLETED:
                    completed_tasks += 1
                elif status.state == TaskState.FAILED:
                    failed_tasks += 1
            
            # 确定系统状态
            if active_tasks > 0:
                system_state = SystemState.BUSY
            elif queued_tasks > 0:
                system_state = SystemState.READY
            else:
                system_state = SystemState.IDLE
            
            # 模拟资源使用率（在实际系统中应该从系统监控获取）
            cpu_usage = min(1.0, active_tasks * 0.1 + queued_tasks * 0.05)
            memory_usage = min(1.0, len(self.task_states) * 0.01)
            
            self.system_status = SystemStatus(
                system_state=system_state,
                active_tasks=active_tasks,
                queued_tasks=queued_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                last_update=datetime.now()
            )
    
    def _save_snapshot(self):
        """保存状态快照"""
        snapshot = StateSnapshot(
            timestamp=datetime.now(),
            task_states=self.task_states.copy(),
            system_status=self.system_status,
            context_data=self._gather_context_data()
        )
        
        self.state_history.append(snapshot)
    
    def _gather_context_data(self) -> Dict[str, Any]:
        """收集上下文数据"""
        return {
            "total_tasks": len(self.task_states),
            "recent_activity": self._get_recent_activity(),
            "system_load": self._calculate_system_load()
        }
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """获取最近活动"""
        recent_activities = []
        now = datetime.now()
        
        for task_id, status in self.task_states.items():
            if status.start_time and (now - status.start_time).seconds < 300:  # 最近5分钟
                activity = {
                    "task_id": task_id,
                    "state": status.state.value,
                    "progress": status.progress,
                    "current_step": status.current_step
                }
                recent_activities.append(activity)
        
        return recent_activities
    
    def _calculate_system_load(self) -> float:
        """计算系统负载"""
        total_tasks = len(self.task_states)
        if total_tasks == 0:
            return 0.0
        
        active_weight = self.system_status.active_tasks * 2.0
        queued_weight = self.system_status.queued_tasks * 0.5
        
        return min(1.0, (active_weight + queued_weight) / (total_tasks * 2))
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        with self._lock:
            return self.task_states.get(task_id)
    
    def get_all_task_statuses(self) -> Dict[str, TaskStatus]:
        """获取所有任务状态"""
        with self._lock:
            return self.task_states.copy()
    
    def get_system_status(self) -> SystemStatus:
        """获取系统状态"""
        with self._lock:
            return self.system_status
    
    def get_ready_tasks(self) -> List[str]:
        """获取准备就绪的任务"""
        with self._lock:
            ready_tasks = []
            
            for task_id, status in self.task_states.items():
                if status.state == TaskState.READY:
                    # 检查依赖是否满足
                    if self._are_dependencies_met(task_id):
                        ready_tasks.append(task_id)
            
            return ready_tasks
    
    def _are_dependencies_met(self, task_id: str) -> bool:
        """检查任务依赖是否满足"""
        task_status = self.task_states.get(task_id)
        if not task_status or not task_status.dependencies:
            return True
        
        for dep_id in task_status.dependencies:
            dep_status = self.task_states.get(dep_id)
            if not dep_status or dep_status.state != TaskState.COMPLETED:
                return False
        
        return True
    
    def get_task_progress(self, task_id: str) -> Optional[float]:
        """获取任务进度"""
        with self._lock:
            status = self.task_states.get(task_id)
            return status.progress if status else None
    
    def get_failed_tasks(self) -> List[TaskStatus]:
        """获取失败的任务"""
        with self._lock:
            return [
                status for status in self.task_states.values() 
                if status.state == TaskState.FAILED
            ]
    
    def retry_failed_task(self, task_id: str) -> bool:
        """重试失败的任务"""
        with self._lock:
            status = self.task_states.get(task_id)
            if not status or status.state != TaskState.FAILED:
                return False
            
            return self.update_task_state(
                task_id, 
                TaskState.READY, 
                progress=0.0,
                current_step="准备重试",
                error_message=None
            )
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            status = self.task_states.get(task_id)
            if not status or status.state in [TaskState.COMPLETED, TaskState.CANCELLED]:
                return False
            
            return self.update_task_state(
                task_id,
                TaskState.CANCELLED,
                current_step="已取消"
            )
    
    def get_state_history(self, start_time: datetime = None, 
                         end_time: datetime = None) -> List[StateSnapshot]:
        """获取状态历史"""
        with self._lock:
            if not start_time and not end_time:
                return list(self.state_history)
            
            filtered_history = []
            for snapshot in self.state_history:
                if start_time and snapshot.timestamp < start_time:
                    continue
                if end_time and snapshot.timestamp > end_time:
                    continue
                filtered_history.append(snapshot)
            
            return filtered_history
    
    def start_monitoring(self, interval_seconds: int = 5):
        """开始监控"""
        if self._monitoring:
            self.logger.warning("监控已在运行中")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info(f"状态监控已启动，间隔: {interval_seconds}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        
        self.logger.info("状态监控已停止")
    
    def _monitoring_loop(self, interval_seconds: int):
        """监控循环"""
        while self._monitoring:
            try:
                # 定期更新系统状态
                self._update_system_status()
                self._save_snapshot()
                
                # 检查超时任务
                self._check_timeout_tasks()
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
            
            time.sleep(interval_seconds)
    
    def _check_timeout_tasks(self):
        """检查超时任务"""
        with self._lock:
            now = datetime.now()
            timeout_threshold = timedelta(minutes=30)  # 30分钟超时
            
            for task_id, status in self.task_states.items():
                if (status.state == TaskState.RUNNING and 
                    status.start_time and 
                    (now - status.start_time) > timeout_threshold):
                    
                    self.logger.warning(f"任务超时: {task_id}")
                    self.update_task_state(
                        task_id,
                        TaskState.FAILED,
                        error_message="任务执行超时"
                    )
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """清理已完成的任务"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            tasks_to_remove = []
            
            for task_id, status in self.task_states.items():
                if (status.state in [TaskState.COMPLETED, TaskState.CANCELLED] and
                    status.end_time and status.end_time < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.task_states[task_id]
            
            if tasks_to_remove:
                self.logger.info(f"清理了 {len(tasks_to_remove)} 个已完成的任务")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        with self._lock:
            total_tasks = len(self.task_states)
            if total_tasks == 0:
                return {}
            
            completed_tasks = self.system_status.completed_tasks
            failed_tasks = self.system_status.failed_tasks
            
            success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
            
            # 计算平均执行时间
            execution_times = []
            for status in self.task_states.values():
                if status.start_time and status.end_time:
                    execution_time = (status.end_time - status.start_time).total_seconds()
                    execution_times.append(execution_time)
            
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time,
                "system_uptime": self._get_system_uptime(),
                "current_load": self._calculate_system_load()
            }
    
    def _get_system_uptime(self) -> float:
        """获取系统运行时间"""
        if not self.state_history:
            return 0.0
        
        first_snapshot = self.state_history[0]
        uptime = (datetime.now() - first_snapshot.timestamp).total_seconds()
        return uptime

