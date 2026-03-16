"""
执行监控器 - 监控任务执行过程
实时跟踪执行状态、性能指标和异常情况
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import psutil
import gc
from concurrent.futures import Future, ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    """执行状态枚举"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

@dataclass
class ExecutionMetrics:
    """执行指标"""
    start_time: datetime
    end_time: Optional[datetime] = None
    cpu_usage: List[float] = field(default_factory=list)
    memory_usage: List[float] = field(default_factory=list)
    execution_steps: List[str] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    retry_count: int = 0
    progress: float = 0.0

@dataclass
class ResourceUsage:
    """资源使用情况"""
    resource_type: ResourceType
    current_usage: float
    max_usage: float
    usage_history: List[float] = field(default_factory=list)
    threshold: float = 0.8  # 阈值

@dataclass
class ExecutionAlert:
    """执行告警"""
    alert_id: str
    task_id: str
    alert_type: str
    severity: str  # critical, warning, info
    message: str
    timestamp: datetime
    resolved: bool = False

class ExecutionMonitor:
    """执行监控器"""
    
    def __init__(self, monitoring_interval: float = 1.0):
        self.logger = logging.getLogger(__name__)
        self.monitoring_interval = monitoring_interval
        
        # 监控数据存储
        self.execution_metrics: Dict[str, ExecutionMetrics] = {}
        self.resource_usage: Dict[ResourceType, ResourceUsage] = {}
        self.active_alerts: Dict[str, ExecutionAlert] = {}
        self.performance_thresholds = self._initialize_thresholds()
        
        # 回调函数
        self.alert_handlers: List[Callable] = []
        self.progress_handlers: List[Callable] = []
        
        # 监控控制
        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.RLock()
        
        # 初始化资源监控
        self._initialize_resource_monitoring()
        
        self.logger.info("执行监控器初始化完成")
    
    def _initialize_thresholds(self) -> Dict[str, float]:
        """初始化性能阈值"""
        return {
            "cpu_usage": 0.8,  # 80%
            "memory_usage": 0.85,  # 85%
            "disk_usage": 0.9,  # 90%
            "execution_time": 3600,  # 1小时
            "error_rate": 0.1,  # 10%
            "progress_stall": 300  # 5分钟无进展
        }
    
    def _initialize_resource_monitoring(self):
        """初始化资源监控"""
        self.resource_usage = {
            ResourceType.CPU: ResourceUsage(
                resource_type=ResourceType.CPU,
                current_usage=0.0,
                max_usage=0.0
            ),
            ResourceType.MEMORY: ResourceUsage(
                resource_type=ResourceType.MEMORY,
                current_usage=0.0,
                max_usage=0.0
            ),
            ResourceType.DISK: ResourceUsage(
                resource_type=ResourceType.DISK,
                current_usage=0.0,
                max_usage=0.0
            )
        }
    
    def start_monitoring_task(self, task_id: str) -> bool:
        """
        开始监控任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功开始监控
        """
        with self._lock:
            if task_id in self.execution_metrics:
                self.logger.warning(f"任务已在监控中: {task_id}")
                return False
            
            metrics = ExecutionMetrics(start_time=datetime.now())
            self.execution_metrics[task_id] = metrics
            
            self.logger.info(f"开始监控任务: {task_id}")
            return True
    
    def update_task_progress(self, task_id: str, progress: float, current_step: str = None) -> bool:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度 (0-1)
            current_step: 当前步骤描述
            
        Returns:
            bool: 是否成功更新
        """
        with self._lock:
            if task_id not in self.execution_metrics:
                self.logger.error(f"任务未在监控中: {task_id}")
                return False
            
            metrics = self.execution_metrics[task_id]
            metrics.progress = max(0.0, min(1.0, progress))
            
            if current_step:
                metrics.execution_steps.append(f"{datetime.now()}: {current_step}")
            
            # 检查进度停滞
            self._check_progress_stall(task_id, metrics)
            
            # 触发进度回调
            self._trigger_progress_handlers(task_id, progress, current_step)
            
            return True
    
    def record_error(self, task_id: str, error_message: str, severity: str = "error") -> bool:
        """
        记录错误
        
        Args:
            task_id: 任务ID
            error_message: 错误信息
            severity: 严重程度
            
        Returns:
            bool: 是否成功记录
        """
        with self._lock:
            if task_id not in self.execution_metrics:
                self.logger.error(f"任务未在监控中: {task_id}")
                return False
            
            metrics = self.execution_metrics[task_id]
            
            if severity == "error":
                metrics.error_count += 1
            elif severity == "warning":
                metrics.warning_count += 1
            
            # 创建告警
            alert = ExecutionAlert(
                alert_id=f"alert_{task_id}_{int(time.time())}",
                task_id=task_id,
                alert_type=severity,
                severity=severity,
                message=error_message,
                timestamp=datetime.now()
            )
            
            self.active_alerts[alert.alert_id] = alert
            
            # 触发告警回调
            self._trigger_alert_handlers(alert)
            
            # 检查错误率阈值
            self._check_error_rate(task_id, metrics)
            
            self.logger.warning(f"记录{severity}: {task_id} - {error_message}")
            return True
    
    def complete_task(self, task_id: str, success: bool = True) -> bool:
        """
        完成任务监控
        
        Args:
            task_id: 任务ID
            success: 是否成功完成
            
        Returns:
            bool: 是否成功完成
        """
        with self._lock:
            if task_id not in self.execution_metrics:
                self.logger.error(f"任务未在监控中: {task_id}")
                return False
            
            metrics = self.execution_metrics[task_id]
            metrics.end_time = datetime.now()
            
            if not success:
                metrics.error_count += 1
            
            # 生成执行报告
            report = self._generate_execution_report(task_id, metrics)
            
            self.logger.info(f"任务监控完成: {task_id}, 成功: {success}")
            return True
    
    def _check_progress_stall(self, task_id: str, metrics: ExecutionMetrics):
        """检查进度停滞"""
        if len(metrics.execution_steps) < 2:
            return
        
        # 检查最近是否有进展
        recent_steps = metrics.execution_steps[-5:]  # 最近5个步骤
        if len(recent_steps) < 2:
            return
        
        # 解析时间戳
        try:
            last_time_str = recent_steps[-1].split(':')[0]
            prev_time_str = recent_steps[0].split(':')[0]
            
            last_time = datetime.fromisoformat(last_time_str)
            prev_time = datetime.fromisoformat(prev_time_str)
            
            time_diff = (last_time - prev_time).total_seconds()
            
            if time_diff > self.performance_thresholds["progress_stall"]:
                self.record_error(
                    task_id,
                    f"任务进度停滞超过 {self.performance_thresholds['progress_stall']} 秒",
                    "warning"
                )
        except Exception as e:
            self.logger.warning(f"进度停滞检查失败: {e}")
    
    def _check_error_rate(self, task_id: str, metrics: ExecutionMetrics):
        """检查错误率"""
        total_steps = len(metrics.execution_steps)
        if total_steps == 0:
            return
        
        error_rate = metrics.error_count / total_steps
        
        if error_rate > self.performance_thresholds["error_rate"]:
            self.record_error(
                task_id,
                f"错误率过高: {error_rate:.2%}",
                "critical"
            )
    
    def _generate_execution_report(self, task_id: str, metrics: ExecutionMetrics) -> Dict[str, Any]:
        """生成执行报告"""
        execution_time = 0.0
        if metrics.end_time and metrics.start_time:
            execution_time = (metrics.end_time - metrics.start_time).total_seconds()
        
        report = {
            "task_id": task_id,
            "execution_time": execution_time,
            "progress": metrics.progress,
            "error_count": metrics.error_count,
            "warning_count": metrics.warning_count,
            "retry_count": metrics.retry_count,
            "execution_steps": metrics.execution_steps,
            "average_cpu_usage": sum(metrics.cpu_usage) / len(metrics.cpu_usage) if metrics.cpu_usage else 0.0,
            "max_memory_usage": max(metrics.memory_usage) if metrics.memory_usage else 0.0,
            "completion_status": "success" if metrics.error_count == 0 else "failed"
        }
        
        return report
    
    def start_resource_monitoring(self):
        """开始资源监控"""
        if self._monitoring:
            self.logger.warning("资源监控已在运行中")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._resource_monitoring_loop,
            daemon=True
        )
        self._monitor_thread.start()
        
        self.logger.info("资源监控已启动")
    
    def stop_resource_monitoring(self):
        """停止资源监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self.logger.info("资源监控已停止")
    
    def _resource_monitoring_loop(self):
        """资源监控循环"""
        while self._monitoring:
            try:
                with self._lock:
                    # 监控CPU使用率
                    cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
                    self.resource_usage[ResourceType.CPU].current_usage = cpu_percent
                    self.resource_usage[ResourceType.CPU].usage_history.append(cpu_percent)
                    self.resource_usage[ResourceType.CPU].max_usage = max(
                        self.resource_usage[ResourceType.CPU].max_usage, 
                        cpu_percent
                    )
                    
                    # 监控内存使用率
                    memory_info = psutil.virtual_memory()
                    memory_percent = memory_info.percent / 100.0
                    self.resource_usage[ResourceType.MEMORY].current_usage = memory_percent
                    self.resource_usage[ResourceType.MEMORY].usage_history.append(memory_percent)
                    self.resource_usage[ResourceType.MEMORY].max_usage = max(
                        self.resource_usage[ResourceType.MEMORY].max_usage, 
                        memory_percent
                    )
                    
                    # 监控磁盘使用率
                    disk_info = psutil.disk_usage('/')
                    disk_percent = disk_info.percent / 100.0
                    self.resource_usage[ResourceType.DISK].current_usage = disk_percent
                    self.resource_usage[ResourceType.DISK].usage_history.append(disk_percent)
                    self.resource_usage[ResourceType.DISK].max_usage = max(
                        self.resource_usage[ResourceType.DISK].max_usage, 
                        disk_percent
                    )
                    
                    # 检查资源阈值
                    self._check_resource_thresholds()
                    
                    # 更新所有活跃任务的资源使用情况
                    self._update_task_resource_metrics()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"资源监控错误: {e}")
                time.sleep(self.monitoring_interval)
    
    def _check_resource_thresholds(self):
        """检查资源阈值"""
        for resource_type, usage in self.resource_usage.items():
            if usage.current_usage > usage.threshold:
                alert = ExecutionAlert(
                    alert_id=f"resource_alert_{int(time.time())}",
                    task_id="system",
                    alert_type="resource_threshold",
                    severity="warning",
                    message=f"{resource_type.value}使用率超过阈值: {usage.current_usage:.1%}",
                    timestamp=datetime.now()
                )
                
                self.active_alerts[alert.alert_id] = alert
                self._trigger_alert_handlers(alert)
    
    def _update_task_resource_metrics(self):
        """更新任务资源指标"""
        current_cpu = self.resource_usage[ResourceType.CPU].current_usage
        current_memory = self.resource_usage[ResourceType.MEMORY].current_usage
        
        for task_id, metrics in self.execution_metrics.items():
            if metrics.end_time is None:  # 只更新活跃任务
                metrics.cpu_usage.append(current_cpu)
                metrics.memory_usage.append(current_memory)
    
    def register_alert_handler(self, handler: Callable):
        """注册告警处理器"""
        self.alert_handlers.append(handler)
    
    def register_progress_handler(self, handler: Callable):
        """注册进度处理器"""
        self.progress_handlers.append(handler)
    
    def _trigger_alert_handlers(self, alert: ExecutionAlert):
        """触发告警处理器"""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"告警处理器错误: {e}")
    
    def _trigger_progress_handlers(self, task_id: str, progress: float, step: str):
        """触发进度处理器"""
        for handler in self.progress_handlers:
            try:
                handler(task_id, progress, step)
            except Exception as e:
                self.logger.error(f"进度处理器错误: {e}")
    
    def get_task_metrics(self, task_id: str) -> Optional[ExecutionMetrics]:
        """获取任务指标"""
        with self._lock:
            return self.execution_metrics.get(task_id)
    
    def get_resource_usage(self, resource_type: ResourceType) -> Optional[ResourceUsage]:
        """获取资源使用情况"""
        with self._lock:
            return self.resource_usage.get(resource_type)
    
    def get_active_alerts(self) -> List[ExecutionAlert]:
        """获取活跃告警"""
        with self._lock:
            return [
                alert for alert in self.active_alerts.values() 
                if not alert.resolved
            ]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].resolved = True
                return True
            return False
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            total_tasks = len(self.execution_metrics)
            completed_tasks = sum(1 for m in self.execution_metrics.values() if m.end_time is not None)
            failed_tasks = sum(1 for m in self.execution_metrics.values() if m.error_count > 0)
            
            avg_cpu = 0.0
            avg_memory = 0.0
            if self.resource_usage[ResourceType.CPU].usage_history:
                avg_cpu = sum(self.resource_usage[ResourceType.CPU].usage_history) / len(self.resource_usage[ResourceType.CPU].usage_history)
            if self.resource_usage[ResourceType.MEMORY].usage_history:
                avg_memory = sum(self.resource_usage[ResourceType.MEMORY].usage_history) / len(self.resource_usage[ResourceType.MEMORY].usage_history)
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": (completed_tasks - failed_tasks) / completed_tasks if completed_tasks > 0 else 0.0,
                "average_cpu_usage": avg_cpu,
                "average_memory_usage": avg_memory,
                "active_alerts": len([a for a in self.active_alerts.values() if not a.resolved]),
                "monitoring_duration": self._get_monitoring_duration()
            }
    
    def _get_monitoring_duration(self) -> float:
        """获取监控持续时间"""
        if not self.execution_metrics:
            return 0.0
        
        start_times = [m.start_time for m in self.execution_metrics.values()]
        if not start_times:
            return 0.0
        
        earliest_start = min(start_times)
        return (datetime.now() - earliest_start).total_seconds()
    
    def cleanup_old_data(self, older_than_hours: int = 24):
        """清理旧数据"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            # 清理任务指标
            tasks_to_remove = []
            for task_id, metrics in self.execution_metrics.items():
                if metrics.end_time and metrics.end_time < cutoff_time:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.execution_metrics[task_id]
            
            # 清理历史数据
            for resource_usage in self.resource_usage.values():
                if len(resource_usage.usage_history) > 1000:  # 保持最近1000个数据点
                    resource_usage.usage_history = resource_usage.usage_history[-1000:]
            
            # 清理已解决的告警
            alerts_to_remove = [
                alert_id for alert_id, alert in self.active_alerts.items()
                if alert.resolved and alert.timestamp < cutoff_time
            ]
            
            for alert_id in alerts_to_remove:
                del self.active_alerts[alert_id]
            
            if tasks_to_remove or alerts_to_remove:
                self.logger.info(f"清理了 {len(tasks_to_remove)} 个任务和 {len(alerts_to_remove)} 个告警")

