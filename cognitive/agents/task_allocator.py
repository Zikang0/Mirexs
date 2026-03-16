"""
任务分配器：实现智能体任务分配算法和负载均衡
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import time
import heapq

from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.working_memory import WorkingMemory
from ...infrastructure.communication.message_bus import MessageBus
from ...data.databases.vector_db.similarity_search import SimilaritySearch

class AllocationStrategy(Enum):
    """分配策略枚举"""
    CAPABILITY_BASED = "capability_based"
    LOAD_BALANCED = "load_balanced"
    COST_EFFICIENT = "cost_efficient"
    PERFORMANCE_OPTIMIZED = "performance_optimized"
    HYBRID = "hybrid"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Task:
    """任务信息"""
    task_id: str
    task_type: str
    description: str
    required_capabilities: List[str]
    estimated_duration: float
    priority: TaskPriority
    dependencies: List[str]
    deadline: Optional[float]
    metadata: Dict[str, Any]

@dataclass
class AgentCapacity:
    """智能体能力信息"""
    agent_id: str
    capabilities: List[str]
    current_workload: float
    max_capacity: float
    capability_proficiency: Dict[str, float]
    reliability_score: float
    cost_per_task: float

@dataclass
class AllocationResult:
    """分配结果"""
    allocation_id: str
    task_id: str
    agent_id: str
    allocation_strategy: AllocationStrategy
    expected_completion_time: float
    confidence_score: float
    allocation_time: float

class TaskAllocator:
    """
    任务分配器 - 管理智能体任务分配和负载均衡
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 核心组件
        self.episodic_memory = EpisodicMemory(config.get("memory", {}))
        self.semantic_memory = SemanticMemory(config.get("memory", {}))
        self.working_memory = WorkingMemory(config.get("memory", {}))
        self.message_bus = MessageBus(config.get("message_bus", {}))
        self.similarity_search = SimilaritySearch(config.get("vector_db", {}))
        
        # 任务管理
        self.pending_tasks: Dict[str, Task] = {}
        self.allocated_tasks: Dict[str, AllocationResult] = {}
        self.task_queue: List[Tuple[int, str]] = []  # 优先级队列
        
        # 智能体管理
        self.available_agents: Dict[str, AgentCapacity] = {}
        self.agent_performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 分配策略
        self.allocation_strategies: Dict[AllocationStrategy, callable] = {
            AllocationStrategy.CAPABILITY_BASED: self._capability_based_allocation,
            AllocationStrategy.LOAD_BALANCED: self._load_balanced_allocation,
            AllocationStrategy.COST_EFFICIENT: self._cost_efficient_allocation,
            AllocationStrategy.PERFORMANCE_OPTIMIZED: self._performance_optimized_allocation,
            AllocationStrategy.HYBRID: self._hybrid_allocation
        }
        
        # 性能指标
        self.performance_metrics = {
            "total_allocations": 0,
            "successful_allocations": 0,
            "average_allocation_time": 0.0,
            "load_imbalance_score": 0.0,
            "allocation_success_rate": 0.0
        }
        
        # 模型加载
        self.allocation_model = self._load_allocation_model()
        
        self.logger.info("TaskAllocator initialized")

    def _load_allocation_model(self):
        """加载分配模型"""
        try:
            self.logger.info("Loading allocation model...")
            
            # 模拟分配模型参数
            allocation_config = {
                "max_allocation_time": self.config.get("max_allocation_time", 30),
                "min_confidence_threshold": self.config.get("min_confidence_threshold", 0.6),
                "load_balance_threshold": self.config.get("load_balance_threshold", 0.3),
                "default_strategy": AllocationStrategy(self.config.get("default_strategy", "hybrid")),
                "reallocation_enabled": self.config.get("reallocation_enabled", True)
            }
            
            self.logger.info("Allocation model loaded successfully")
            return allocation_config
            
        except Exception as e:
            self.logger.error(f"Failed to load allocation model: {e}")
            raise

    async def register_agent(self, agent_capacity: AgentCapacity) -> bool:
        """
        注册智能体
        
        Args:
            agent_capacity: 智能体能力信息
            
        Returns:
            注册是否成功
        """
        try:
            self.available_agents[agent_capacity.agent_id] = agent_capacity
            
            # 初始化性能历史
            self.agent_performance_history[agent_capacity.agent_id].append({
                "timestamp": time.time(),
                "workload": agent_capacity.current_workload,
                "reliability": agent_capacity.reliability_score
            })
            
            self.logger.info(f"Agent {agent_capacity.agent_id} registered with capabilities: {agent_capacity.capabilities}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_capacity.agent_id}: {e}")
            return False

    async def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.available_agents:
            # 重新分配该智能体的任务
            await self._reallocate_agent_tasks(agent_id)
            
            # 移除智能体
            del self.available_agents[agent_id]
            if agent_id in self.agent_performance_history:
                del self.agent_performance_history[agent_id]
            
            self.logger.info(f"Agent {agent_id} unregistered")

    async def submit_task(self, task: Task) -> str:
        """
        提交任务
        
        Args:
            task: 任务信息
            
        Returns:
            任务ID
        """
        try:
            # 验证任务
            if not await self._validate_task(task):
                self.logger.error(f"Task validation failed: {task.task_id}")
                return ""
            
            # 添加到待处理任务
            self.pending_tasks[task.task_id] = task
            
            # 添加到优先级队列
            priority_score = self._calculate_priority_score(task)
            heapq.heappush(self.task_queue, (-priority_score, task.task_id))  # 使用负值实现最大堆
            
            self.logger.info(f"Task {task.task_id} submitted with priority {task.priority}")
            
            # 触发分配
            asyncio.create_task(self._process_task_allocation())
            
            return task.task_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit task {task.task_id}: {e}")
            return ""

    async def allocate_task(self, 
                          task_id: str, 
                          strategy: Optional[AllocationStrategy] = None) -> Optional[AllocationResult]:
        """
        分配任务
        
        Args:
            task_id: 任务ID
            strategy: 分配策略
            
        Returns:
            分配结果
        """
        if task_id not in self.pending_tasks:
            self.logger.error(f"Task {task_id} not found")
            return None
        
        task = self.pending_tasks[task_id]
        strategy = strategy or self.allocation_model["default_strategy"]
        
        self.logger.info(f"Allocating task {task_id} using {strategy.value} strategy")
        
        start_time = time.time()
        
        try:
            # 选择分配策略
            allocation_func = self.allocation_strategies.get(strategy, self._hybrid_allocation)
            allocation_result = await allocation_func(task)
            
            if allocation_result and allocation_result.confidence_score >= self.allocation_model["min_confidence_threshold"]:
                # 记录分配结果
                self.allocated_tasks[task_id] = allocation_result
                
                # 从待处理任务中移除
                del self.pending_tasks[task_id]
                
                # 更新智能体工作负载
                if allocation_result.agent_id in self.available_agents:
                    agent = self.available_agents[allocation_result.agent_id]
                    agent.current_workload += task.estimated_duration / agent.max_capacity
                
                # 更新性能指标
                allocation_time = time.time() - start_time
                self._update_performance_metrics(True, allocation_time)
                
                self.logger.info(f"Task {task_id} allocated to agent {allocation_result.agent_id} "
                               f"with confidence {allocation_result.confidence_score:.2f}")
                
                # 通知智能体
                await self._notify_agent_allocation(allocation_result, task)
                
                return allocation_result
            else:
                self.logger.warning(f"Task {task_id} allocation failed: low confidence")
                self._update_performance_metrics(False, time.time() - start_time)
                return None
                
        except Exception as e:
            self.logger.error(f"Task allocation failed for {task_id}: {e}")
            self._update_performance_metrics(False, time.time() - start_time)
            return None

    async def _capability_based_allocation(self, task: Task) -> Optional[AllocationResult]:
        """基于能力的分配策略"""
        best_agent = None
        best_match_score = 0.0
        
        for agent_id, agent in self.available_agents.items():
            # 检查工作负载
            if agent.current_workload >= 0.9:  # 负载过高
                continue
            
            # 计算能力匹配度
            match_score = self._calculate_capability_match(agent, task)
            
            if match_score > best_match_score:
                best_match_score = match_score
                best_agent = agent
        
        if best_agent:
            return self._create_allocation_result(task, best_agent.agent_id, 
                                               AllocationStrategy.CAPABILITY_BASED, best_match_score)
        return None

    async def _load_balanced_allocation(self, task: Task) -> Optional[AllocationResult]:
        """负载均衡分配策略"""
        best_agent = None
        best_load_score = float('inf')
        
        for agent_id, agent in self.available_agents.items():
            # 检查能力匹配
            if not self._has_required_capabilities(agent, task):
                continue
            
            # 计算负载得分（负载越低越好）
            load_score = agent.current_workload
            
            if load_score < best_load_score:
                best_load_score = load_score
                best_agent = agent
        
        if best_agent:
            confidence = 1.0 - best_load_score  # 负载越低，置信度越高
            return self._create_allocation_result(task, best_agent.agent_id,
                                               AllocationStrategy.LOAD_BALANCED, confidence)
        return None

    async def _cost_efficient_allocation(self, task: Task) -> Optional[AllocationResult]:
        """成本效益分配策略"""
        best_agent = None
        best_cost_score = float('inf')
        
        for agent_id, agent in self.available_agents.items():
            # 检查能力匹配
            if not self._has_required_capabilities(agent, task):
                continue
            
            # 检查工作负载
            if agent.current_workload >= 0.8:
                continue
            
            # 计算成本得分
            capability_match = self._calculate_capability_match(agent, task)
            cost_score = agent.cost_per_task / (capability_match + 0.001)  # 避免除零
            
            if cost_score < best_cost_score:
                best_cost_score = cost_score
                best_agent = agent
        
        if best_agent:
            confidence = 1.0 / (1.0 + best_cost_score)  # 成本越低，置信度越高
            return self._create_allocation_result(task, best_agent.agent_id,
                                               AllocationStrategy.COST_EFFICIENT, confidence)
        return None

    async def _performance_optimized_allocation(self, task: Task) -> Optional[AllocationResult]:
        """性能优化分配策略"""
        best_agent = None
        best_performance_score = 0.0
        
        for agent_id, agent in self.available_agents.items():
            # 检查能力匹配
            if not self._has_required_capabilities(agent, task):
                continue
            
            # 计算性能得分
            capability_match = self._calculate_capability_match(agent, task)
            reliability = agent.reliability_score
            workload_factor = 1.0 - agent.current_workload
            
            performance_score = capability_match * reliability * workload_factor
            
            if performance_score > best_performance_score:
                best_performance_score = performance_score
                best_agent = agent
        
        if best_agent:
            return self._create_allocation_result(task, best_agent.agent_id,
                                               AllocationStrategy.PERFORMANCE_OPTIMIZED, best_performance_score)
        return None

    async def _hybrid_allocation(self, task: Task) -> Optional[AllocationResult]:
        """混合分配策略"""
        candidates = []
        
        for agent_id, agent in self.available_agents.items():
            # 基础能力检查
            if not self._has_required_capabilities(agent, task):
                continue
            
            # 计算综合得分
            capability_match = self._calculate_capability_match(agent, task)
            reliability = agent.reliability_score
            workload_factor = 1.0 - agent.current_workload
            cost_factor = 1.0 / (1.0 + agent.cost_per_task)
            
            # 综合得分（可调整权重）
            hybrid_score = (
                capability_match * 0.4 +
                reliability * 0.3 +
                workload_factor * 0.2 +
                cost_factor * 0.1
            )
            
            candidates.append((hybrid_score, agent))
        
        if candidates:
            best_score, best_agent = max(candidates, key=lambda x: x[0])
            return self._create_allocation_result(task, best_agent.agent_id,
                                               AllocationStrategy.HYBRID, best_score)
        return None

    def _calculate_capability_match(self, agent: AgentCapacity, task: Task) -> float:
        """计算能力匹配度"""
        if not task.required_capabilities:
            return 1.0  # 没有要求的能力，完全匹配
        
        match_score = 0.0
        total_weight = 0.0
        
        for required_cap in task.required_capabilities:
            if required_cap in agent.capabilities:
                proficiency = agent.capability_proficiency.get(required_cap, 0.5)
                match_score += proficiency
            total_weight += 1.0
        
        return match_score / total_weight if total_weight > 0 else 0.0

    def _has_required_capabilities(self, agent: AgentCapacity, task: Task) -> bool:
        """检查是否具备所需能力"""
        if not task.required_capabilities:
            return True
        
        return all(cap in agent.capabilities for cap in task.required_capabilities)

    def _calculate_priority_score(self, task: Task) -> int:
        """计算优先级得分"""
        base_priority = task.priority.value
        
        # 考虑截止时间
        time_factor = 0
        if task.deadline:
            time_remaining = task.deadline - time.time()
            if time_remaining < 3600:  # 1小时内
                time_factor = 3
            elif time_remaining < 86400:  # 24小时内
                time_factor = 1
        
        # 考虑任务复杂度
        complexity_factor = min(len(task.required_capabilities) // 2, 2)
        
        return base_priority + time_factor + complexity_factor

    def _create_allocation_result(self, 
                                task: Task, 
                                agent_id: str, 
                                strategy: AllocationStrategy,
                                confidence_score: float) -> AllocationResult:
        """创建分配结果"""
        # 计算预计完成时间
        agent = self.available_agents[agent_id]
        base_duration = task.estimated_duration
        proficiency_factor = 1.0 / (self._calculate_capability_match(agent, task) + 0.001)
        workload_factor = 1.0 + agent.current_workload
        
        expected_duration = base_duration * proficiency_factor * workload_factor
        
        return AllocationResult(
            allocation_id=f"alloc_{task.task_id}_{int(time.time())}",
            task_id=task.task_id,
            agent_id=agent_id,
            allocation_strategy=strategy,
            expected_completion_time=expected_duration,
            confidence_score=confidence_score,
            allocation_time=time.time()
        )

    async def _process_task_allocation(self):
        """处理任务分配"""
        while self.task_queue and self.available_agents:
            # 获取最高优先级任务
            _, task_id = heapq.heappop(self.task_queue)
            
            if task_id not in self.pending_tasks:
                continue
            
            # 分配任务
            allocation_result = await self.allocate_task(task_id)
            
            if not allocation_result:
                # 分配失败，重新加入队列（降低优先级）
                task = self.pending_tasks[task_id]
                new_priority = self._calculate_priority_score(task) - 1  # 降低优先级
                if new_priority > 0:
                    heapq.heappush(self.task_queue, (-new_priority, task_id))
            
            # 短暂休息避免过度占用CPU
            await asyncio.sleep(0.01)

    async def _notify_agent_allocation(self, allocation_result: AllocationResult, task: Task):
        """通知智能体分配结果"""
        notification = {
            "allocation_id": allocation_result.allocation_id,
            "task_id": task.task_id,
            "task_details": {
                "type": task.task_type,
                "description": task.description,
                "required_capabilities": task.required_capabilities,
                "estimated_duration": task.estimated_duration,
                "priority": task.priority.value,
                "deadline": task.deadline,
                "metadata": task.metadata
            },
            "expected_completion_time": allocation_result.expected_completion_time,
            "allocation_time": allocation_result.allocation_time
        }
        
        await self.message_bus.send_message(
            f"agent_{allocation_result.agent_id}_tasks",
            notification
        )

    async def _reallocate_agent_tasks(self, agent_id: str):
        """重新分配智能体任务"""
        tasks_to_reallocate = []
        
        for task_id, allocation in self.allocated_tasks.items():
            if allocation.agent_id == agent_id:
                tasks_to_reallocate.append(task_id)
        
        for task_id in tasks_to_reallocate:
            # 从已分配任务中移除
            del self.allocated_tasks[task_id]
            
            # 重新提交任务
            task = await self._recreate_task_from_allocation(task_id)
            if task:
                await self.submit_task(task)
        
        self.logger.info(f"Reallocated {len(tasks_to_reallocate)} tasks from agent {agent_id}")

    async def _recreate_task_from_allocation(self, task_id: str) -> Optional[Task]:
        """从分配结果重新创建任务"""
        # 这里需要从记忆系统中获取原始任务信息
        # 简化实现：返回一个基本任务对象
        try:
            task_info = await self.episodic_memory.get_task_info(task_id)
            if task_info:
                return Task(
                    task_id=task_id,
                    task_type=task_info.get("type", "unknown"),
                    description=task_info.get("description", ""),
                    required_capabilities=task_info.get("required_capabilities", []),
                    estimated_duration=task_info.get("estimated_duration", 300),
                    priority=TaskPriority(task_info.get("priority", 2)),
                    dependencies=task_info.get("dependencies", []),
                    deadline=task_info.get("deadline"),
                    metadata=task_info.get("metadata", {})
                )
        except Exception as e:
            self.logger.warning(f"Failed to recreate task {task_id}: {e}")
        
        return None

    async def _validate_task(self, task: Task) -> bool:
        """验证任务"""
        if not task.task_id or not task.description:
            return False
        
        if task.estimated_duration <= 0:
            return False
        
        # 检查依赖关系
        for dep_id in task.dependencies:
            if dep_id not in self.allocated_tasks:
                self.logger.warning(f"Task {task.task_id} has unmet dependency: {dep_id}")
                # 这里可以实施更复杂的依赖检查
        
        return True

    def _update_performance_metrics(self, success: bool, allocation_time: float):
        """更新性能指标"""
        self.performance_metrics["total_allocations"] += 1
        
        if success:
            self.performance_metrics["successful_allocations"] += 1
        
        # 更新平均分配时间（指数移动平均）
        alpha = 0.1
        self.performance_metrics["average_allocation_time"] = (
            alpha * allocation_time + 
            (1 - alpha) * self.performance_metrics["average_allocation_time"]
        )
        
        # 计算分配成功率
        self.performance_metrics["allocation_success_rate"] = (
            self.performance_metrics["successful_allocations"] / 
            self.performance_metrics["total_allocations"]
        )
        
        # 计算负载不均衡分数
        self.performance_metrics["load_imbalance_score"] = self._calculate_load_imbalance()

    def _calculate_load_imbalance(self) -> float:
        """计算负载不均衡分数"""
        if not self.available_agents:
            return 0.0
        
        workloads = [agent.current_workload for agent in self.available_agents.values()]
        mean_workload = np.mean(workloads)
        
        if mean_workload == 0:
            return 0.0
        
        variance = np.var(workloads)
        return variance / mean_workload

    async def update_agent_workload(self, agent_id: str, workload_change: float):
        """更新智能体工作负载"""
        if agent_id in self.available_agents:
            agent = self.available_agents[agent_id]
            agent.current_workload = max(0, min(1.0, agent.current_workload + workload_change))
            
            # 记录性能历史
            self.agent_performance_history[agent_id].append({
                "timestamp": time.time(),
                "workload": agent.current_workload,
                "reliability": agent.reliability_score
            })

    async def update_agent_reliability(self, agent_id: str, reliability_score: float):
        """更新智能体可靠性分数"""
        if agent_id in self.available_agents:
            agent = self.available_agents[agent_id]
            agent.reliability_score = max(0, min(1.0, reliability_score))

    def get_allocation_statistics(self) -> Dict[str, Any]:
        """获取分配统计信息"""
        strategy_distribution = defaultdict(int)
        for allocation in self.allocated_tasks.values():
            strategy_distribution[allocation.allocation_strategy.value] += 1
        
        return {
            **self.performance_metrics,
            "pending_tasks": len(self.pending_tasks),
            "allocated_tasks": len(self.allocated_tasks),
            "available_agents": len(self.available_agents),
            "strategy_distribution": dict(strategy_distribution),
            "average_agent_workload": np.mean([a.current_workload for a in self.available_agents.values()]) 
                                     if self.available_agents else 0.0
        }

    async def get_agent_recommendations(self, task: Task) -> List[Tuple[str, float]]:
        """
        获取智能体推荐列表
        
        Args:
            task: 任务信息
            
        Returns:
            推荐智能体列表（智能体ID, 推荐分数）
        """
        recommendations = []
        
        for agent_id, agent in self.available_agents.items():
            if self._has_required_capabilities(agent, task):
                capability_match = self._calculate_capability_match(agent, task)
                reliability = agent.reliability_score
                workload_factor = 1.0 - agent.current_workload
                
                recommendation_score = capability_match * reliability * workload_factor
                recommendations.append((agent_id, recommendation_score))
        
        # 按推荐分数排序
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up TaskAllocator...")
        
        # 保存分配历史到记忆系统
        for task_id, allocation in self.allocated_tasks.items():
            await self.episodic_memory.record_allocation_history(allocation)
        
        self.logger.info("TaskAllocator cleanup completed")

