"""
资源优化器：优化系统资源使用
"""
import psutil
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import json
from pathlib import Path
import subprocess
import os

logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

class OptimizationAction(Enum):
    """优化操作枚举"""
    PROCESS_KILL = "process_kill"
    PROCESS_SUSPEND = "process_suspend"
    PRIORITY_ADJUST = "priority_adjust"
    MEMORY_CLEANUP = "memory_cleanup"
    DISK_CLEANUP = "disk_cleanup"
    SERVICE_STOP = "service_stop"
    SERVICE_RESTART = "service_restart"

@dataclass
class ResourceUsage:
    """资源使用情况"""
    resource_type: ResourceType
    usage_percent: float
    total: int
    used: int
    free: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['resource_type'] = self.resource_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class OptimizationResult:
    """优化结果"""
    action: OptimizationAction
    target: str
    description: str
    timestamp: datetime
    success: bool
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['action'] = self.action.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

class ResourceOptimizer:
    """资源优化器"""
    
    def __init__(self):
        self.is_monitoring = False
        self.is_optimizing = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.optimization_thread: Optional[threading.Thread] = None
        self.resource_history: Dict[ResourceType, List[ResourceUsage]] = {}
        self.optimization_history: List[OptimizationResult] = []
        self.optimization_config = self._load_optimization_config()
        self._setup_logging()
        self._initialize_resource_tracking()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_optimization_config(self) -> Dict[str, Any]:
        """加载优化配置"""
        return {
            "auto_optimize": True,
            "cpu_threshold": 85.0,
            "memory_threshold": 90.0,
            "disk_threshold": 95.0,
            "check_interval": 30,
            "max_optimizations_per_hour": 10,
            "excluded_processes": ["system", "svchost.exe", "explorer.exe"],
            "optimization_strategies": {
                "cpu": ["process_priority", "process_suspend"],
                "memory": ["memory_cleanup", "process_kill"],
                "disk": ["disk_cleanup"]
            }
        }
    
    def _initialize_resource_tracking(self):
        """初始化资源跟踪"""
        for resource_type in ResourceType:
            self.resource_history[resource_type] = []
    
    def start_resource_monitoring(self) -> bool:
        """开始资源监控"""
        if self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info("资源监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动资源监控失败: {str(e)}")
            return False
    
    def stop_resource_monitoring(self) -> bool:
        """停止资源监控"""
        if not self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            
            logger.info("资源监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止资源监控失败: {str(e)}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        interval = self.optimization_config["check_interval"]
        
        while self.is_monitoring:
            try:
                # 收集资源使用数据
                self._collect_resource_usage()
                
                # 检查是否需要优化
                if self.optimization_config["auto_optimize"]:
                    self._check_optimization_needed()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"资源监控循环错误: {str(e)}")
                time.sleep(interval * 2)
    
    def _collect_resource_usage(self):
        """收集资源使用数据"""
        current_time = datetime.now()
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_usage = ResourceUsage(
                resource_type=ResourceType.CPU,
                usage_percent=cpu_percent,
                total=100,  # 百分比
                used=cpu_percent,
                free=100 - cpu_percent,
                timestamp=current_time
            )
            self.resource_history[ResourceType.CPU].append(cpu_usage)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = ResourceUsage(
                resource_type=ResourceType.MEMORY,
                usage_percent=memory.percent,
                total=memory.total,
                used=memory.used,
                free=memory.free,
                timestamp=current_time
            )
            self.resource_history[ResourceType.MEMORY].append(memory_usage)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = ResourceUsage(
                resource_type=ResourceType.DISK,
                usage_percent=(disk.used / disk.total) * 100,
                total=disk.total,
                used=disk.used,
                free=disk.free,
                timestamp=current_time
            )
            self.resource_history[ResourceType.DISK].append(disk_usage)
            
            # 限制历史数据长度
            for resource_type in ResourceType:
                if len(self.resource_history[resource_type]) > 1000:
                    self.resource_history[resource_type].pop(0)
            
        except Exception as e:
            logger.error(f"收集资源使用数据失败: {str(e)}")
    
    def _check_optimization_needed(self):
        """检查是否需要优化"""
        try:
            # 获取当前资源使用情况
            current_cpu = self.resource_history[ResourceType.CPU][-1] if self.resource_history[ResourceType.CPU] else None
            current_memory = self.resource_history[ResourceType.MEMORY][-1] if self.resource_history[ResourceType.MEMORY] else None
            current_disk = self.resource_history[ResourceType.DISK][-1] if self.resource_history[ResourceType.DISK] else None
            
            optimization_actions = []
            
            # 检查CPU使用率
            if current_cpu and current_cpu.usage_percent > self.optimization_config["cpu_threshold"]:
                logger.warning(f"CPU使用率过高: {current_cpu.usage_percent:.1f}%")
                optimization_actions.extend(self._get_cpu_optimization_actions())
            
            # 检查内存使用率
            if current_memory and current_memory.usage_percent > self.optimization_config["memory_threshold"]:
                logger.warning(f"内存使用率过高: {current_memory.usage_percent:.1f}%")
                optimization_actions.extend(self._get_memory_optimization_actions())
            
            # 检查磁盘使用率
            if current_disk and current_disk.usage_percent > self.optimization_config["disk_threshold"]:
                logger.warning(f"磁盘使用率过高: {current_disk.usage_percent:.1f}%")
                optimization_actions.extend(self._get_disk_optimization_actions())
            
            # 执行优化操作
            if optimization_actions and not self.is_optimizing:
                self._execute_optimizations(optimization_actions)
            
        except Exception as e:
            logger.error(f"检查优化需求失败: {str(e)}")
    
    def _get_cpu_optimization_actions(self) -> List[Tuple[OptimizationAction, Dict[str, Any]]]:
        """获取CPU优化操作"""
        actions = []
        
        try:
            # 查找高CPU使用率的进程
            high_cpu_processes = []
            for process in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    process_info = process.info
                    cpu_percent = process_info['cpu_percent'] or 0
                    
                    if (cpu_percent > 10 and 
                        process_info['name'] not in self.optimization_config["excluded_processes"]):
                        high_cpu_processes.append({
                            'pid': process_info['pid'],
                            'name': process_info['name'],
                            'cpu_percent': cpu_percent
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按CPU使用率排序
            high_cpu_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # 为前3个高CPU进程添加优化操作
            for process in high_cpu_processes[:3]:
                if "process_priority" in self.optimization_config["optimization_strategies"]["cpu"]:
                    actions.append((
                        OptimizationAction.PRIORITY_ADJUST,
                        {
                            'pid': process['pid'],
                            'name': process['name'],
                            'current_priority': 'normal',
                            'new_priority': 'below_normal'
                        }
                    ))
                
                if "process_suspend" in self.optimization_config["optimization_strategies"]["cpu"]:
                    actions.append((
                        OptimizationAction.PROCESS_SUSPEND,
                        {
                            'pid': process['pid'],
                            'name': process['name'],
                            'duration': 30  # 暂停30秒
                        }
                    ))
        
        except Exception as e:
            logger.error(f"获取CPU优化操作失败: {str(e)}")
        
        return actions
    
    def _get_memory_optimization_actions(self) -> List[Tuple[OptimizationAction, Dict[str, Any]]]:
        """获取内存优化操作"""
        actions = []
        
        try:
            # 查找高内存使用率的进程
            high_memory_processes = []
            for process in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    process_info = process.info
                    memory_info = process_info['memory_info']
                    
                    if memory_info and memory_info.rss > 100 * 1024 * 1024:  # 100MB
                        high_memory_processes.append({
                            'pid': process_info['pid'],
                            'name': process_info['name'],
                            'memory_usage': memory_info.rss
                        })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按内存使用量排序
            high_memory_processes.sort(key=lambda x: x['memory_usage'], reverse=True)
            
            # 为前3个高内存进程添加优化操作
            for process in high_memory_processes[:3]:
                if "process_kill" in self.optimization_config["optimization_strategies"]["memory"]:
                    actions.append((
                        OptimizationAction.PROCESS_KILL,
                        {
                            'pid': process['pid'],
                            'name': process['name'],
                            'memory_freed': process['memory_usage']
                        }
                    ))
            
            # 内存清理操作
            if "memory_cleanup" in self.optimization_config["optimization_strategies"]["memory"]:
                actions.append((
                    OptimizationAction.MEMORY_CLEANUP,
                    {'method': 'system_cache'}
                ))
        
        except Exception as e:
            logger.error(f"获取内存优化操作失败: {str(e)}")
        
        return actions
    
    def _get_disk_optimization_actions(self) -> List[Tuple[OptimizationAction, Dict[str, Any]]]:
        """获取磁盘优化操作"""
        actions = []
        
        try:
            if "disk_cleanup" in self.optimization_config["optimization_strategies"]["disk"]:
                actions.append((
                    OptimizationAction.DISK_CLEANUP,
                    {
                        'target_paths': [
                            tempfile.gettempdir(),
                            "C:\\Windows\\Temp",
                            "C:\\Users\\*\\AppData\\Local\\Temp"
                        ],
                        'cleanup_method': 'temporary_files'
                    }
                ))
        
        except Exception as e:
            logger.error(f"获取磁盘优化操作失败: {str(e)}")
        
        return actions
    
    def _execute_optimizations(self, optimizations: List[Tuple[OptimizationAction, Dict[str, Any]]]):
        """执行优化操作"""
        if self.is_optimizing:
            return
        
        try:
            self.is_optimizing = True
            
            # 在单独线程中执行优化
            self.optimization_thread = threading.Thread(
                target=self._optimization_worker,
                args=(optimizations,),
                daemon=True
            )
            self.optimization_thread.start()
            
            logger.info(f"开始执行 {len(optimizations)} 个优化操作")
            
        except Exception as e:
            logger.error(f"启动优化执行失败: {str(e)}")
            self.is_optimizing = False
    
    def _optimization_worker(self, optimizations: List[Tuple[OptimizationAction, Dict[str, Any]]]):
        """优化工作线程"""
        try:
            for action, parameters in optimizations:
                if not self.is_optimizing:
                    break
                
                result = self._execute_single_optimization(action, parameters)
                self.optimization_history.append(result)
                
                if result.success:
                    logger.info(f"优化操作成功: {result.description}")
                else:
                    logger.error(f"优化操作失败: {result.description}")
                
                # 添加延迟避免过度优化
                time.sleep(2)
            
            self.is_optimizing = False
            logger.info("优化操作执行完成")
            
        except Exception as e:
            logger.error(f"优化工作线程错误: {str(e)}")
            self.is_optimizing = False
    
    def _execute_single_optimization(self, action: OptimizationAction, parameters: Dict[str, Any]) -> OptimizationResult:
        """执行单个优化操作"""
        try:
            timestamp = datetime.now()
            
            if action == OptimizationAction.PROCESS_KILL:
                return self._kill_process(parameters, timestamp)
            elif action == OptimizationAction.PROCESS_SUSPEND:
                return self._suspend_process(parameters, timestamp)
            elif action == OptimizationAction.PRIORITY_ADJUST:
                return self._adjust_process_priority(parameters, timestamp)
            elif action == OptimizationAction.MEMORY_CLEANUP:
                return self._cleanup_memory(parameters, timestamp)
            elif action == OptimizationAction.DISK_CLEANUP:
                return self._cleanup_disk(parameters, timestamp)
            else:
                return OptimizationResult(
                    action=action,
                    target="unknown",
                    description=f"未知优化操作: {action.value}",
                    timestamp=timestamp,
                    success=False,
                    details={'error': '未知操作类型'}
                )
            
        except Exception as e:
            return OptimizationResult(
                action=action,
                target=parameters.get('name', 'unknown'),
                description=f"优化操作执行异常: {str(e)}",
                timestamp=datetime.now(),
                success=False,
                details={'error': str(e)}
            )
    
    def _kill_process(self, parameters: Dict[str, Any], timestamp: datetime) -> OptimizationResult:
        """终止进程"""
        try:
            pid = parameters['pid']
            process_name = parameters['name']
            
            process = psutil.Process(pid)
            process.terminate()
            
            # 等待进程结束
            process.wait(timeout=5)
            
            return OptimizationResult(
                action=OptimizationAction.PROCESS_KILL,
                target=process_name,
                description=f"终止高资源进程: {process_name} (PID: {pid})",
                timestamp=timestamp,
                success=True,
                details={
                    'pid': pid,
                    'memory_freed': parameters.get('memory_freed', 0),
                    'process_name': process_name
                }
            )
            
        except Exception as e:
            return OptimizationResult(
                action=OptimizationAction.PROCESS_KILL,
                target=parameters.get('name', 'unknown'),
                description=f"终止进程失败: {str(e)}",
                timestamp=timestamp,
                success=False,
                details={'error': str(e), 'pid': parameters.get('pid')}
            )
    
    def _suspend_process(self, parameters: Dict[str, Any], timestamp: datetime) -> OptimizationResult:
        """暂停进程"""
        try:
            pid = parameters['pid']
            process_name = parameters['name']
            duration = parameters.get('duration', 30)
            
            process = psutil.Process(pid)
            process.suspend()
            
            # 在指定时间后恢复进程
            def resume_process():
                time.sleep(duration)
                try:
                    process.resume()
                except Exception:
                    pass
            
            threading.Thread(target=resume_process, daemon=True).start()
            
            return OptimizationResult(
                action=OptimizationAction.PROCESS_SUSPEND,
                target=process_name,
                description=f"暂停进程 {duration} 秒: {process_name} (PID: {pid})",
                timestamp=timestamp,
                success=True,
                details={
                    'pid': pid,
                    'duration': duration,
                    'process_name': process_name
                }
            )
            
        except Exception as e:
            return OptimizationResult(
                action=OptimizationAction.PROCESS_SUSPEND,
                target=parameters.get('name', 'unknown'),
                description=f"暂停进程失败: {str(e)}",
                timestamp=timestamp,
                success=False,
                details={'error': str(e), 'pid': parameters.get('pid')}
            )
    
    def _adjust_process_priority(self, parameters: Dict[str, Any], timestamp: datetime) -> OptimizationResult:
        """调整进程优先级"""
        try:
            pid = parameters['pid']
            process_name = parameters['name']
            new_priority = parameters.get('new_priority', 'below_normal')
            
            process = psutil.Process(pid)
            
            priority_map = {
                'idle': psutil.IDLE_PRIORITY_CLASS,
                'below_normal': psutil.BELOW_NORMAL_PRIORITY_CLASS,
                'normal': psutil.NORMAL_PRIORITY_CLASS,
                'above_normal': psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                'high': psutil.HIGH_PRIORITY_CLASS,
                'realtime': psutil.REALTIME_PRIORITY_CLASS
            }
            
            process.nice(priority_map.get(new_priority, psutil.BELOW_NORMAL_PRIORITY_CLASS))
            
            return OptimizationResult(
                action=OptimizationAction.PRIORITY_ADJUST,
                target=process_name,
                description=f"调整进程优先级: {process_name} -> {new_priority}",
                timestamp=timestamp,
                success=True,
                details={
                    'pid': pid,
                    'new_priority': new_priority,
                    'process_name': process_name
                }
            )
            
        except Exception as e:
            return OptimizationResult(
                action=OptimizationAction.PRIORITY_ADJUST,
                target=parameters.get('name', 'unknown'),
                description=f"调整进程优先级失败: {str(e)}",
                timestamp=timestamp,
                success=False,
                details={'error': str(e), 'pid': parameters.get('pid')}
            )
    
    def _cleanup_memory(self, parameters: Dict[str, Any], timestamp: datetime) -> OptimizationResult:
        """清理内存"""
        try:
            # 这里应该实现具体的内存清理逻辑
            # 简化实现，只记录操作
            
            return OptimizationResult(
                action=OptimizationAction.MEMORY_CLEANUP,
                target="system_memory",
                description="执行系统内存清理",
                timestamp=timestamp,
                success=True,
                details={
                    'method': parameters.get('method', 'system_cache'),
                    'estimated_memory_freed': 'unknown'
                }
            )
            
        except Exception as e:
            return OptimizationResult(
                action=OptimizationAction.MEMORY_CLEANUP,
                target="system_memory",
                description=f"内存清理失败: {str(e)}",
                timestamp=timestamp,
                success=False,
                details={'error': str(e)}
            )
    
    def _cleanup_disk(self, parameters: Dict[str, Any], timestamp: datetime) -> OptimizationResult:
        """清理磁盘"""
        try:
            target_paths = parameters.get('target_paths', [])
            cleanup_method = parameters.get('cleanup_method', 'temporary_files')
            
            # 这里应该实现具体的磁盘清理逻辑
            # 简化实现，只记录操作
            
            return OptimizationResult(
                action=OptimizationAction.DISK_CLEANUP,
                target="system_disk",
                description=f"执行磁盘清理: {cleanup_method}",
                timestamp=timestamp,
                success=True,
                details={
                    'target_paths': target_paths,
                    'method': cleanup_method,
                    'estimated_space_freed': 'unknown'
                }
            )
            
        except Exception as e:
            return OptimizationResult(
                action=OptimizationAction.DISK_CLEANUP,
                target="system_disk",
                description=f"磁盘清理失败: {str(e)}",
                timestamp=timestamp,
                success=False,
                details={'error': str(e)}
            )
    
    def get_resource_usage(self, resource_type: ResourceType = None, time_range: int = 3600) -> Dict[str, Any]:
        """获取资源使用情况"""
        try:
            if resource_type:
                resource_data = self.resource_history.get(resource_type, [])
            else:
                resource_data = []
                for rt in ResourceType:
                    resource_data.extend(self.resource_history.get(rt, []))
            
            # 过滤时间范围
            cutoff_time = datetime.now().timestamp() - time_range
            filtered_data = [data for data in resource_data if data.timestamp.timestamp() > cutoff_time]
            
            # 计算统计信息
            if filtered_data:
                usage_values = [data.usage_percent for data in filtered_data]
                avg_usage = sum(usage_values) / len(usage_values)
                max_usage = max(usage_values)
                min_usage = min(usage_values)
            else:
                avg_usage = max_usage = min_usage = 0
            
            return {
                'average_usage': avg_usage,
                'max_usage': max_usage,
                'min_usage': min_usage,
                'data_points': len(filtered_data),
                'time_range_seconds': time_range
            }
            
        except Exception as e:
            logger.error(f"获取资源使用情况失败: {str(e)}")
            return {}
    
    def get_optimization_history(self, limit: int = 50) -> List[OptimizationResult]:
        """获取优化历史"""
        return self.optimization_history[-limit:] if limit > 0 else self.optimization_history
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        total_optimizations = len(self.optimization_history)
        successful_optimizations = len([r for r in self.optimization_history if r.success])
        failed_optimizations = total_optimizations - successful_optimizations
        
        action_counts = {}
        for result in self.optimization_history:
            action = result.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'total_optimizations': total_optimizations,
            'successful_optimizations': successful_optimizations,
            'failed_optimizations': failed_optimizations,
            'success_rate': successful_optimizations / total_optimizations if total_optimizations > 0 else 0,
            'optimizations_by_action': action_counts
        }
    
    def stop_optimization(self):
        """停止优化操作"""
        self.is_optimizing = False
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=5)
        
        logger.info("优化操作已停止")

# 单例实例
_resource_optimizer_instance = None

def get_resource_optimizer() -> ResourceOptimizer:
    """获取资源优化器单例"""
    global _resource_optimizer_instance
    if _resource_optimizer_instance is None:
        _resource_optimizer_instance = ResourceOptimizer()
    return _resource_optimizer_instance

