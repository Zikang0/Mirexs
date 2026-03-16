"""
群体协调器：协调智能体群体，实现复杂的多智能体协作
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import time

from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.working_memory import WorkingMemory
from ...infrastructure.communication.message_bus import MessageBus
from ...infrastructure.compute_storage.resource_manager import ResourceManager

class SwarmState(Enum):
    """群体状态枚举"""
    IDLE = "idle"
    FORMING = "forming"
    ACTIVE = "active"
    COORDINATING = "coordinating"
    DISBANDING = "disbanding"

@dataclass
class SwarmMember:
    """群体成员信息"""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    current_workload: float
    reliability_score: float
    join_time: float

@dataclass
class SwarmTask:
    """群体任务信息"""
    task_id: str
    task_type: str
    complexity: float
    required_capabilities: List[str]
    priority: int
    deadline: Optional[float]
    subtasks: List[Dict[str, Any]]

class SwarmOrchestrator:
    """
    群体协调器 - 管理智能体群体的形成、协作和解散
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # 核心组件
        self.episodic_memory = EpisodicMemory(config.get("memory", {}))
        self.semantic_memory = SemanticMemory(config.get("memory", {}))
        self.working_memory = WorkingMemory(config.get("memory", {}))
        self.message_bus = MessageBus(config.get("message_bus", {}))
        self.resource_manager = ResourceManager(config.get("resource", {}))
        
        # 群体状态
        self.swarms: Dict[str, Dict[str, Any]] = {}
        self.available_agents: Dict[str, SwarmMember] = {}
        self.agent_capability_index: Dict[str, List[str]] = {}
        
        # 性能指标
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_coordination_time": 0.0,
            "swarm_success_rate": 0.0
        }
        
        # 模型加载
        self.coordination_model = self._load_coordination_model()
        self.formation_strategy_model = self._load_formation_strategy_model()
        
        self.logger.info("SwarmOrchestrator initialized")

    def _load_coordination_model(self):
        """加载群体协调模型"""
        try:
            # 加载预训练的群体协调模型
            # 这里使用模拟的协调逻辑，实际项目中会加载真实的机器学习模型
            self.logger.info("Loading coordination model...")
            
            # 模拟协调模型参数
            coordination_config = {
                "max_swarm_size": self.config.get("max_swarm_size", 10),
                "min_reliability_threshold": self.config.get("min_reliability_threshold", 0.7),
                "coordination_timeout": self.config.get("coordination_timeout", 300),
                "load_balancing_strategy": self.config.get("load_balancing_strategy", "round_robin")
            }
            
            self.logger.info("Coordination model loaded successfully")
            return coordination_config
            
        except Exception as e:
            self.logger.error(f"Failed to load coordination model: {e}")
            raise

    def _load_formation_strategy_model(self):
        """加载群体形成策略模型"""
        try:
            self.logger.info("Loading formation strategy model...")
            
            # 模拟群体形成策略模型
            formation_strategies = {
                "capability_based": self._capability_based_formation,
                "reliability_based": self._reliability_based_formation,
                "hybrid": self._hybrid_formation,
                "emergent": self._emergent_formation
            }
            
            self.logger.info("Formation strategy model loaded successfully")
            return formation_strategies
            
        except Exception as e:
            self.logger.error(f"Failed to load formation strategy model: {e}")
            raise

    async def form_swarm(self, task: SwarmTask, strategy: str = "hybrid") -> str:
        """
        形成智能体群体来执行任务
        
        Args:
            task: 群体任务
            strategy: 群体形成策略
            
        Returns:
            群体ID
        """
        self.logger.info(f"Forming swarm for task {task.task_id} using {strategy} strategy")
        
        try:
            # 选择形成策略
            formation_func = self.formation_strategy_model.get(strategy, self._hybrid_formation)
            selected_agents = await formation_func(task)
            
            if not selected_agents:
                self.logger.warning(f"No suitable agents found for task {task.task_id}")
                return ""
            
            # 创建群体
            swarm_id = f"swarm_{task.task_id}_{int(time.time())}"
            swarm = {
                "id": swarm_id,
                "task": task,
                "members": selected_agents,
                "state": SwarmState.FORMING,
                "formation_time": time.time(),
                "performance_history": deque(maxlen=100)
            }
            
            self.swarms[swarm_id] = swarm
            
            # 通知成员加入群体
            await self._notify_swarm_formation(swarm_id, selected_agents, task)
            
            # 更新群体状态
            swarm["state"] = SwarmState.ACTIVE
            
            self.logger.info(f"Swarm {swarm_id} formed successfully with {len(selected_agents)} members")
            
            # 记录到记忆系统
            await self.episodic_memory.record_swarm_formation(swarm_id, task, selected_agents)
            
            return swarm_id
            
        except Exception as e:
            self.logger.error(f"Failed to form swarm for task {task.task_id}: {e}")
            return ""

    async def _capability_based_formation(self, task: SwarmTask) -> List[SwarmMember]:
        """基于能力的群体形成策略"""
        required_caps = set(task.required_capabilities)
        suitable_agents = []
        
        for agent_id, agent in self.available_agents.items():
            agent_caps = set(agent.capabilities)
            
            # 检查能力匹配度
            if required_caps.issubset(agent_caps) and agent.current_workload < 0.8:
                suitable_agents.append(agent)
        
        # 按可靠性排序
        suitable_agents.sort(key=lambda x: x.reliability_score, reverse=True)
        
        return suitable_agents[:self.coordination_model["max_swarm_size"]]

    async def _reliability_based_formation(self, task: SwarmTask) -> List[SwarmMember]:
        """基于可靠性的群体形成策略"""
        required_caps = set(task.required_capabilities)
        suitable_agents = []
        
        for agent_id, agent in self.available_agents.items():
            agent_caps = set(agent.capabilities)
            
            # 检查基础能力匹配和可靠性阈值
            if (required_caps.intersection(agent_caps) and 
                agent.reliability_score >= self.coordination_model["min_reliability_threshold"] and
                agent.current_workload < 0.7):
                suitable_agents.append(agent)
        
        # 按可靠性排序
        suitable_agents.sort(key=lambda x: x.reliability_score, reverse=True)
        
        return suitable_agents[:self.coordination_model["max_swarm_size"]]

    async def _hybrid_formation(self, task: SwarmTask) -> List[SwarmMember]:
        """混合群体形成策略"""
        # 结合能力和可靠性
        capability_based = await self._capability_based_formation(task)
        reliability_based = await self._reliability_based_formation(task)
        
        # 合并并去重
        all_agents = {agent.agent_id: agent for agent in capability_based + reliability_based}
        
        # 计算综合得分
        scored_agents = []
        for agent in all_agents.values():
            capability_match = len(set(agent.capabilities) & set(task.required_capabilities)) / len(task.required_capabilities)
            score = (capability_match * 0.6 + agent.reliability_score * 0.4) * (1 - agent.current_workload)
            scored_agents.append((score, agent))
        
        # 按综合得分排序
        scored_agents.sort(key=lambda x: x[0], reverse=True)
        
        return [agent for score, agent in scored_agents[:self.coordination_model["max_swarm_size"]]]

    async def _emergent_formation(self, task: SwarmTask) -> List[SwarmMember]:
        """涌现式群体形成策略"""
        # 基于历史协作经验的智能涌现
        historical_patterns = await self.episodic_memory.get_similar_swarm_patterns(task)
        
        if historical_patterns:
            # 使用历史成功模式
            best_pattern = max(historical_patterns, key=lambda x: x["success_rate"])
            agent_combinations = best_pattern["effective_combinations"]
            
            # 选择最佳组合
            selected_agents = []
            for agent_type in agent_combinations[0]:  # 使用最佳组合的第一个模式
                matching_agents = [a for a in self.available_agents.values() 
                                 if a.agent_type == agent_type and a.current_workload < 0.8]
                if matching_agents:
                    selected_agents.append(max(matching_agents, key=lambda x: x.reliability_score))
            
            return selected_agents
        else:
            # 回退到混合策略
            return await self._hybrid_formation(task)

    async def coordinate_swarm(self, swarm_id: str, coordination_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        协调群体执行
        
        Args:
            swarm_id: 群体ID
            coordination_data: 协调数据
            
        Returns:
            协调结果
        """
        if swarm_id not in self.swarms:
            self.logger.error(f"Swarm {swarm_id} not found")
            return {"success": False, "error": "Swarm not found"}
        
        swarm = self.swarms[swarm_id]
        swarm["state"] = SwarmState.COORDINATING
        
        self.logger.info(f"Coordinating swarm {swarm_id}")
        
        try:
            # 任务分配
            task_assignments = await self._assign_subtasks(swarm, coordination_data)
            
            # 执行协调
            coordination_results = await self._execute_coordination(swarm, task_assignments)
            
            # 监控执行
            execution_monitor = asyncio.create_task(
                self._monitor_swarm_execution(swarm_id, coordination_data.get("timeout", 300))
            )
            
            # 等待协调完成
            final_result = await execution_monitor
            
            # 更新群体状态
            swarm["state"] = SwarmState.ACTIVE
            swarm["performance_history"].append({
                "timestamp": time.time(),
                "coordination_time": final_result.get("coordination_duration", 0),
                "success": final_result.get("success", False)
            })
            
            # 更新性能指标
            self._update_performance_metrics(final_result.get("success", False))
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Coordination failed for swarm {swarm_id}: {e}")
            swarm["state"] = SwarmState.ACTIVE
            return {"success": False, "error": str(e)}

    async def _assign_subtasks(self, swarm: Dict[str, Any], coordination_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """分配子任务给群体成员"""
        task_assignments = {}
        subtasks = swarm["task"].subtasks
        
        for i, subtask in enumerate(subtasks):
            required_caps = subtask.get("required_capabilities", [])
            suitable_members = []
            
            for member in swarm["members"]:
                if all(cap in member.capabilities for cap in required_caps):
                    suitable_members.append(member)
            
            if suitable_members:
                # 选择负载最低的成员
                selected_member = min(suitable_members, key=lambda x: x.current_workload)
                if selected_member.agent_id not in task_assignments:
                    task_assignments[selected_member.agent_id] = []
                task_assignments[selected_member.agent_id].append(f"subtask_{i}")
                
                # 更新成员工作负载
                selected_member.current_workload += 0.1  # 模拟负载增加
        
        return task_assignments

    async def _execute_coordination(self, swarm: Dict[str, Any], task_assignments: Dict[str, List[str]]) -> Dict[str, Any]:
        """执行群体协调"""
        coordination_start = time.time()
        
        # 发送任务分配
        coordination_tasks = []
        for agent_id, subtasks in task_assignments.items():
            task_data = {
                "swarm_id": swarm["id"],
                "subtasks": subtasks,
                "task_data": swarm["task"].__dict__,
                "deadline": swarm["task"].deadline
            }
            
            coordination_task = asyncio.create_task(
                self.message_bus.send_message(f"agent_{agent_id}_tasks", task_data)
            )
            coordination_tasks.append(coordination_task)
        
        # 等待所有任务分配完成
        await asyncio.gather(*coordination_tasks)
        
        coordination_duration = time.time() - coordination_start
        
        return {
            "coordination_duration": coordination_duration,
            "assignments_made": len(task_assignments),
            "total_subtasks": len(swarm["task"].subtasks)
        }

    async def _monitor_swarm_execution(self, swarm_id: str, timeout: float) -> Dict[str, Any]:
        """监控群体执行"""
        start_time = time.time()
        swarm = self.swarms[swarm_id]
        
        while time.time() - start_time < timeout:
            # 检查成员状态
            member_statuses = await self._check_member_statuses(swarm["members"])
            
            # 检查任务完成情况
            completion_status = await self._check_task_completion(swarm_id)
            
            if completion_status.get("all_completed", False):
                return {
                    "success": True,
                    "completion_time": time.time() - start_time,
                    "results": completion_status.get("results", {}),
                    "member_performance": member_statuses
                }
            
            # 处理失败或超时的成员
            await self._handle_failed_members(swarm_id, member_statuses)
            
            await asyncio.sleep(1)  # 每秒检查一次
        
        return {
            "success": False,
            "error": "Coordination timeout",
            "completion_time": timeout
        }

    async def _check_member_statuses(self, members: List[SwarmMember]) -> Dict[str, Any]:
        """检查成员状态"""
        statuses = {}
        
        for member in members:
            # 模拟状态检查 - 实际项目中会通过消息总线查询
            status = {
                "active": member.current_workload > 0,
                "reliability": member.reliability_score,
                "workload": member.current_workload,
                "last_heartbeat": time.time() - member.join_time
            }
            statuses[member.agent_id] = status
        
        return statuses

    async def _check_task_completion(self, swarm_id: str) -> Dict[str, Any]:
        """检查任务完成情况"""
        # 模拟任务完成检查 - 实际项目中会查询任务状态
        return {
            "all_completed": True,  # 模拟全部完成
            "results": {"simulated_result": "task_completed"}
        }

    async def _handle_failed_members(self, swarm_id: str, member_statuses: Dict[str, Any]):
        """处理失败的成员"""
        swarm = self.swarms[swarm_id]
        
        for member_id, status in member_statuses.items():
            if not status["active"] or status["reliability"] < 0.3:
                self.logger.warning(f"Member {member_id} in swarm {swarm_id} is failing")
                
                # 重新分配任务或替换成员
                await self._replace_failed_member(swarm_id, member_id)

    async def _replace_failed_member(self, swarm_id: str, failed_member_id: str):
        """替换失败的成员"""
        swarm = self.swarms[swarm_id]
        
        # 从群体中移除失败成员
        failed_member = next((m for m in swarm["members"] if m.agent_id == failed_member_id), None)
        if failed_member:
            swarm["members"].remove(failed_member)
            
            # 寻找替代成员
            replacement = await self._find_replacement_member(swarm["task"], failed_member)
            if replacement:
                swarm["members"].append(replacement)
                self.logger.info(f"Replaced failed member {failed_member_id} with {replacement.agent_id}")

    async def _find_replacement_member(self, task: SwarmTask, failed_member: SwarmMember) -> Optional[SwarmMember]:
        """寻找替代成员"""
        # 使用混合策略寻找替代成员
        potential_replacements = await self._hybrid_formation(task)
        
        for replacement in potential_replacements:
            if (replacement.agent_id != failed_member.agent_id and 
                replacement.agent_id not in [m.agent_id for m in self.available_agents.values()]):
                return replacement
        
        return None

    async def disband_swarm(self, swarm_id: str):
        """解散群体"""
        if swarm_id not in self.swarms:
            self.logger.warning(f"Swarm {swarm_id} not found for disbanding")
            return
        
        swarm = self.swarms[swarm_id]
        swarm["state"] = SwarmState.DISBANDING
        
        self.logger.info(f"Disbanding swarm {swarm_id}")
        
        # 通知成员群体解散
        for member in swarm["members"]:
            await self.message_bus.send_message(
                f"agent_{member.agent_id}_control", 
                {"action": "leave_swarm", "swarm_id": swarm_id}
            )
            
            # 重置成员工作负载
            member.current_workload = max(0, member.current_workload - 0.1)
        
        # 记录解散事件
        await self.episodic_memory.record_swarm_disband(swarm_id, swarm["task"])
        
        # 移除群体
        del self.swarms[swarm_id]
        
        self.logger.info(f"Swarm {swarm_id} disbanded successfully")

    async def _notify_swarm_formation(self, swarm_id: str, members: List[SwarmMember], task: SwarmTask):
        """通知群体形成"""
        for member in members:
            notification = {
                "swarm_id": swarm_id,
                "task": task.__dict__,
                "action": "join_swarm",
                "formation_time": time.time()
            }
            
            await self.message_bus.send_message(f"agent_{member.agent_id}_control", notification)

    def _update_performance_metrics(self, success: bool):
        """更新性能指标"""
        if success:
            self.performance_metrics["tasks_completed"] += 1
        else:
            self.performance_metrics["tasks_failed"] += 1
        
        total_tasks = self.performance_metrics["tasks_completed"] + self.performance_metrics["tasks_failed"]
        if total_tasks > 0:
            self.performance_metrics["swarm_success_rate"] = (
                self.performance_metrics["tasks_completed"] / total_tasks
            )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.performance_metrics.copy()

    async def register_agent(self, agent: SwarmMember):
        """注册可用智能体"""
        self.available_agents[agent.agent_id] = agent
        
        # 更新能力索引
        for capability in agent.capabilities:
            if capability not in self.agent_capability_index:
                self.agent_capability_index[capability] = []
            self.agent_capability_index[capability].append(agent.agent_id)
        
        self.logger.info(f"Agent {agent.agent_id} registered with capabilities: {agent.capabilities}")

    async def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.available_agents:
            agent = self.available_agents[agent_id]
            
            # 从能力索引中移除
            for capability in agent.capabilities:
                if capability in self.agent_capability_index and agent_id in self.agent_capability_index[capability]:
                    self.agent_capability_index[capability].remove(agent_id)
            
            # 从可用智能体中移除
            del self.available_agents[agent_id]
            
            self.logger.info(f"Agent {agent_id} unregistered")

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up SwarmOrchestrator...")
        
        # 解散所有活跃群体
        for swarm_id in list(self.swarms.keys()):
            await self.disband_swarm(swarm_id)
        
        self.logger.info("SwarmOrchestrator cleanup completed")
