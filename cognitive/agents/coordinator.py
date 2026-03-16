"""
主协调器模块：协调多个智能体
实现基于任务分解和资源调度的智能体协调系统
"""

import uuid
import datetime
import asyncio
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import logging
from dataclasses import dataclass
import threading

@dataclass
class Task:
    """任务数据结构"""
    id: str
    description: str
    priority: int  # 1-10, 10为最高
    complexity: float  # 0-1, 1为最复杂
    required_skills: List[str]
    dependencies: List[str]  # 依赖的任务ID
    status: str  # pending, assigned, in_progress, completed, failed
    assigned_agent: Optional[str] = None
    created_at: datetime.datetime = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    result: Any = None
    error: Optional[str] = None

class CoordinationStrategy(Enum):
    CENTRALIZED = "centralized"  # 集中式协调
    DECENTRALIZED = "decentralized"  # 分布式协调
    HYBRID = "hybrid"  # 混合协调

class Coordinator:
    """主协调器 - 协调多个智能体"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 智能体注册表
        self.agents = {}  # agent_id -> agent_info
        self.agent_skills = {}  # skill -> List[agent_id]
        
        # 任务管理
        self.tasks = {}  # task_id -> Task
        self.task_queue = []
        self.completed_tasks = []
        
        # 协调状态
        self.coordination_strategy = CoordinationStrategy(
            self.config.get('coordination_strategy', 'hybrid')
        )
        self.max_concurrent_tasks = self.config.get('max_concurrent_tasks', 10)
        self.task_timeout = self.config.get('task_timeout', 300)  # 5分钟
        
        # 性能监控
        self.coordination_history = []
        self.performance_metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'average_completion_time': 0,
            'agent_utilization': {}
        }
        
        # 锁和同步
        self.lock = threading.RLock()
        self.task_event = asyncio.Event()
        
        # 启动任务调度器
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._task_scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.initialized = True
        self.logger.info("主协调器初始化成功")
    
    def register_agent(self, 
                      agent_id: str,
                      agent_type: str,
                      capabilities: List[str],
                      capacity: int = 5,
                      metadata: Dict[str, Any] = None) -> bool:
        """
        注册智能体
        
        Args:
            agent_id: 智能体ID
            agent_type: 智能体类型
            capabilities: 能力列表
            capacity: 并发任务容量
            metadata: 元数据
            
        Returns:
            是否成功
        """
        with self.lock:
            if agent_id in self.agents:
                self.logger.warning(f"智能体已注册: {agent_id}")
                return False
            
            agent_info = {
                'id': agent_id,
                'type': agent_type,
                'capabilities': capabilities,
                'capacity': capacity,
                'current_tasks': [],
                'metadata': metadata or {},
                'registered_at': datetime.datetime.now(),
                'last_heartbeat': datetime.datetime.now(),
                'total_tasks_completed': 0,
                'total_tasks_failed': 0
            }
            
            self.agents[agent_id] = agent_info
            
            # 更新技能索引
            for skill in capabilities:
                if skill not in self.agent_skills:
                    self.agent_skills[skill] = []
                self.agent_skills[skill].append(agent_id)
            
            self.logger.info(f"智能体注册成功: {agent_id} ({agent_type})")
            return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """注销智能体"""
        with self.lock:
            if agent_id not in self.agents:
                return False
            
            # 从技能索引中移除
            agent_info = self.agents[agent_id]
            for skill in agent_info['capabilities']:
                if skill in self.agent_skills and agent_id in self.agent_skills[skill]:
                    self.agent_skills[skill].remove(agent_id)
            
            # 重新分配该智能体的任务
            current_tasks = agent_info['current_tasks'].copy()
            for task_id in current_tasks:
                task = self.tasks[task_id]
                task.status = 'pending'
                task.assigned_agent = None
                self._reschedule_task(task_id)
            
            del self.agents[agent_id]
            self.logger.info(f"智能体注销: {agent_id}")
            return True
    
    def submit_task(self,
                   description: str,
                   priority: int = 5,
                   complexity: float = 0.5,
                   required_skills: List[str] = None,
                   dependencies: List[str] = None) -> str:
        """
        提交任务
        
        Args:
            description: 任务描述
            priority: 优先级 (1-10)
            complexity: 复杂度 (0-1)
            required_skills: 所需技能
            dependencies: 依赖任务
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        required_skills = required_skills or []
        dependencies = dependencies or []
        
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            complexity=complexity,
            required_skills=required_skills,
            dependencies=dependencies,
            status='pending',
            created_at=datetime.datetime.now()
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.append(task_id)
            
            # 记录协调历史
            self.coordination_history.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'action': 'task_submitted',
                'task_id': task_id,
                'description': description,
                'priority': priority
            })
        
        self.logger.info(f"任务提交: {task_id} - {description}")
        self.task_event.set()  # 唤醒调度器
        
        return task_id
    
    def _task_scheduler_loop(self):
        """任务调度循环"""
        while self.scheduler_running:
            try:
                # 等待新任务或状态变化
                self.task_event.wait(timeout=1.0)
                self.task_event.clear()
                
                # 调度任务
                self._schedule_tasks()
                
                # 检查超时任务
                self._check_timeout_tasks()
                
                # 更新性能指标
                self._update_performance_metrics()
                
            except Exception as e:
                self.logger.error(f"任务调度循环错误: {e}")
                import time
                time.sleep(5)  # 错误后等待5秒
    
    def _schedule_tasks(self):
        """调度任务"""
        with self.lock:
            # 按优先级排序任务队列
            self.task_queue.sort(key=lambda task_id: self.tasks[task_id].priority, reverse=True)
            
            scheduled_count = 0
            
            for task_id in self.task_queue[:]:  # 使用副本进行迭代
                if scheduled_count >= self.max_concurrent_tasks:
                    break
                
                task = self.tasks[task_id]
                
                # 检查任务状态和依赖
                if task.status != 'pending':
                    continue
                
                if not self._check_dependencies(task):
                    continue
                
                # 寻找合适的智能体
                suitable_agent = self._find_suitable_agent(task)
                if suitable_agent:
                    if self._assign_task_to_agent(task_id, suitable_agent):
                        scheduled_count += 1
                        self.task_queue.remove(task_id)
    
    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖"""
        for dep_id in task.dependencies:
            if dep_id not in self.tasks:
                self.logger.warning(f"依赖任务不存在: {dep_id}")
                return False
            
            dep_task = self.tasks[dep_id]
            if dep_task.status != 'completed':
                return False
        
        return True
    
    def _find_suitable_agent(self, task: Task) -> Optional[str]:
        """寻找合适的智能体"""
        candidate_agents = set()
        
        # 根据技能筛选
        for skill in task.required_skills:
            if skill in self.agent_skills:
                skilled_agents = set(self.agent_skills[skill])
                if not candidate_agents:
                    candidate_agents = skilled_agents
                else:
                    candidate_agents = candidate_agents.intersection(skilled_agents)
            else:
                # 没有具备所需技能的智能体
                return None
        
        if not candidate_agents:
            return None
        
        # 根据负载和性能选择最佳智能体
        best_agent = None
        best_score = -1
        
        for agent_id in candidate_agents:
            agent = self.agents[agent_id]
            
            # 检查容量
            if len(agent['current_tasks']) >= agent['capacity']:
                continue
            
            # 计算匹配分数
            score = self._calculate_agent_score(agent, task)
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def _calculate_agent_score(self, agent: Dict[str, Any], task: Task) -> float:
        """计算智能体匹配分数"""
        score = 0.0
        
        # 负载分数 (负载越低分数越高)
        load_ratio = len(agent['current_tasks']) / agent['capacity']
        load_score = 1.0 - load_ratio
        
        # 性能分数 (基于历史成功率)
        total_tasks = agent['total_tasks_completed'] + agent['total_tasks_failed']
        success_rate = 1.0
        if total_tasks > 0:
            success_rate = agent['total_tasks_completed'] / total_tasks
        
        # 专业技能匹配度
        skill_match = len(set(task.required_skills).intersection(agent['capabilities'])) / len(task.required_skills)
        
        # 综合分数
        score = (load_score * 0.3 + success_rate * 0.4 + skill_match * 0.3)
        
        return score
    
    def _assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """将任务分配给智能体"""
        try:
            task = self.tasks[task_id]
            agent = self.agents[agent_id]
            
            task.status = 'assigned'
            task.assigned_agent = agent_id
            task.started_at = datetime.datetime.now()
            
            agent['current_tasks'].append(task_id)
            
            # 记录协调历史
            self.coordination_history.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'action': 'task_assigned',
                'task_id': task_id,
                'agent_id': agent_id,
                'description': task.description
            })
            
            self.logger.info(f"任务分配: {task_id} -> {agent_id}")
            
            # 在实际系统中，这里会调用智能体的执行接口
            # 模拟异步执行
            self._simulate_task_execution(task_id, agent_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"任务分配失败: {e}")
            return False
    
    def _simulate_task_execution(self, task_id: str, agent_id: str):
        """模拟任务执行（在实际系统中由智能体实际执行）"""
        def execute_task():
            import time
            import random
            
            task = self.tasks[task_id]
            
            # 模拟执行时间（基于复杂度）
            execution_time = task.complexity * 10 + random.uniform(0.1, 2.0)
            time.sleep(execution_time)
            
            # 模拟成功率（基于智能体性能）
            agent = self.agents[agent_id]
            success_rate = 0.9  # 基础成功率
            
            success = random.random() < success_rate
            
            if success:
                self.complete_task(task_id, f"模拟执行成功 - 耗时{execution_time:.2f}秒")
            else:
                self.fail_task(task_id, "模拟执行失败")
        
        # 在后台线程中执行
        execution_thread = threading.Thread(target=execute_task, daemon=True)
        execution_thread.start()
    
    def complete_task(self, task_id: str, result: Any = None):
        """完成任务"""
        with self.lock:
            if task_id not in self.tasks:
                self.logger.error(f"任务不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            
            if task.status not in ['assigned', 'in_progress']:
                self.logger.warning(f"任务状态不正确，无法完成: {task_id} - {task.status}")
                return
            
            task.status = 'completed'
            task.completed_at = datetime.datetime.now()
            task.result = result
            
            # 更新智能体状态
            if task.assigned_agent:
                agent = self.agents[task.assigned_agent]
                agent['current_tasks'].remove(task_id)
                agent['total_tasks_completed'] += 1
            
            self.completed_tasks.append(task_id)
            
            # 记录协调历史
            self.coordination_history.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'action': 'task_completed',
                'task_id': task_id,
                'agent_id': task.assigned_agent,
                'result': result
            })
            
            self.logger.info(f"任务完成: {task_id}")
    
    def fail_task(self, task_id: str, error: str):
        """任务失败"""
        with self.lock:
            if task_id not in self.tasks:
                self.logger.error(f"任务不存在: {task_id}")
                return
            
            task = self.tasks[task_id]
            task.status = 'failed'
            task.completed_at = datetime.datetime.now()
            task.error = error
            
            # 更新智能体状态
            if task.assigned_agent:
                agent = self.agents[task.assigned_agent]
                agent['current_tasks'].remove(task_id)
                agent['total_tasks_failed'] += 1
            
            # 重新调度或放入队列
            self.task_queue.append(task_id)
            
            # 记录协调历史
            self.coordination_history.append({
                'timestamp': datetime.datetime.now().isoformat(),
                'action': 'task_failed',
                'task_id': task_id,
                'agent_id': task.assigned_agent,
                'error': error
            })
            
            self.logger.error(f"任务失败: {task_id} - {error}")
    
    def _reschedule_task(self, task_id: str):
        """重新调度任务"""
        task = self.tasks[task_id]
        task.status = 'pending'
        task.assigned_agent = None
        task.started_at = None
        
        if task_id not in self.task_queue:
            self.task_queue.append(task_id)
        
        self.task_event.set()
        self.logger.info(f"任务重新调度: {task_id}")
    
    def _check_timeout_tasks(self):
        """检查超时任务"""
        current_time = datetime.datetime.now()
        
        with self.lock:
            for task_id, task in self.tasks.items():
                if task.status in ['assigned', 'in_progress'] and task.started_at:
                    time_elapsed = (current_time - task.started_at).total_seconds()
                    if time_elapsed > self.task_timeout:
                        self.logger.warning(f"任务超时: {task_id}")
                        self.fail_task(task_id, f"任务执行超时 ({time_elapsed:.1f}秒)")
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        with self.lock:
            # 任务统计
            total_tasks = len(self.tasks)
            completed_tasks = len(self.completed_tasks)
            failed_tasks = sum(1 for task in self.tasks.values() if task.status == 'failed')
            
            # 计算平均完成时间
            completion_times = []
            for task_id in self.completed_tasks:
                task = self.tasks[task_id]
                if task.started_at and task.completed_at:
                    completion_time = (task.completed_at - task.started_at).total_seconds()
                    completion_times.append(completion_time)
            
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            # 智能体利用率
            agent_utilization = {}
            for agent_id, agent in self.agents.items():
                utilization = len(agent['current_tasks']) / agent['capacity']
                agent_utilization[agent_id] = utilization
            
            self.performance_metrics.update({
                'total_tasks': total_tasks,
                'tasks_completed': completed_tasks,
                'tasks_failed': failed_tasks,
                'average_completion_time': avg_completion_time,
                'agent_utilization': agent_utilization
            })
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            'id': task.id,
            'description': task.description,
            'status': task.status,
            'assigned_agent': task.assigned_agent,
            'priority': task.priority,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'result': task.result,
            'error': task.error
        }
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取智能体状态"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return {
            'id': agent['id'],
            'type': agent['type'],
            'capabilities': agent['capabilities'],
            'capacity': agent['capacity'],
            'current_tasks': agent['current_tasks'],
            'total_tasks_completed': agent['total_tasks_completed'],
            'total_tasks_failed': agent['total_tasks_failed'],
            'utilization': len(agent['current_tasks']) / agent['capacity'],
            'last_heartbeat': agent['last_heartbeat'].isoformat()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self.lock:
            # 任务状态统计
            task_status_counts = {}
            for task in self.tasks.values():
                status = task.status
                task_status_counts[status] = task_status_counts.get(status, 0) + 1
            
            # 智能体类型统计
            agent_type_counts = {}
            for agent in self.agents.values():
                agent_type = agent['type']
                agent_type_counts[agent_type] = agent_type_counts.get(agent_type, 0) + 1
            
            return {
                'total_agents': len(self.agents),
                'agent_types': agent_type_counts,
                'total_tasks': len(self.tasks),
                'task_status': task_status_counts,
                'pending_tasks': len(self.task_queue),
                'performance_metrics': self.performance_metrics,
                'coordination_strategy': self.coordination_strategy.value,
                'system_uptime': self._get_system_uptime()
            }
    
    def _get_system_uptime(self) -> str:
        """获取系统运行时间（简化实现）"""
        return "运行中"
    
    def get_coordination_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取协调历史"""
        return self.coordination_history[-limit:] if limit else self.coordination_history
    
    def shutdown(self):
        """关闭协调器"""
        self.scheduler_running = False
        self.task_event.set()
        
        # 等待调度器线程结束
        if self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        self.logger.info("主协调器已关闭")