"""
协作引擎：促进智能体之间的高效协作和知识共享
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict, deque
import time
import json

from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.working_memory import WorkingMemory
from ...infrastructure.communication.message_bus import MessageBus
from ...data.databases.vector_db.similarity_search import SimilaritySearch

class CollaborationPattern(Enum):
    """协作模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序协作
    PARALLEL = "parallel"      # 并行协作
    HIERARCHICAL = "hierarchical"  # 层次协作
    PEER_TO_PEER = "peer_to_peer"  # 对等协作
    SWARM = "swarm"            # 群体协作

@dataclass
class CollaborationSession:
    """协作会话信息"""
    session_id: str
    participants: List[str]
    pattern: CollaborationPattern
    goal: str
    start_time: float
    status: str
    shared_knowledge: Dict[str, Any]

@dataclass
class CollaborationResult:
    """协作结果"""
    session_id: str
    success: bool
    results: Dict[str, Any]
    participant_contributions: Dict[str, float]
    collaboration_quality: float
    duration: float

class CollaborationEngine:
    """
    协作引擎 - 促进智能体之间的高效协作
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
        
        # 协作状态
        self.active_sessions: Dict[str, CollaborationSession] = {}
        self.collaboration_history: deque = deque(maxlen=1000)
        self.agent_compatibility: Dict[str, Dict[str, float]] = {}
        
        # 知识共享
        self.shared_knowledge_base: Dict[str, Any] = {}
        self.knowledge_access_log: List[Dict[str, Any]] = []
        
        # 模型加载
        self.collaboration_model = self._load_collaboration_model()
        self.pattern_recognition_model = self._load_pattern_recognition_model()
        
        self.logger.info("CollaborationEngine initialized")

    def _load_collaboration_model(self):
        """加载协作模型"""
        try:
            self.logger.info("Loading collaboration model...")
            
            # 模拟协作模型参数
            collaboration_config = {
                "max_session_duration": self.config.get("max_session_duration", 3600),
                "min_trust_threshold": self.config.get("min_trust_threshold", 0.5),
                "knowledge_sharing_enabled": self.config.get("knowledge_sharing_enabled", True),
                "conflict_resolution_enabled": self.config.get("conflict_resolution_enabled", True)
            }
            
            self.logger.info("Collaboration model loaded successfully")
            return collaboration_config
            
        except Exception as e:
            self.logger.error(f"Failed to load collaboration model: {e}")
            raise

    def _load_pattern_recognition_model(self):
        """加载模式识别模型"""
        try:
            self.logger.info("Loading pattern recognition model...")
            
            # 模拟模式识别模型
            pattern_handlers = {
                CollaborationPattern.SEQUENTIAL: self._handle_sequential_collaboration,
                CollaborationPattern.PARALLEL: self._handle_parallel_collaboration,
                CollaborationPattern.HIERARCHICAL: self._handle_hierarchical_collaboration,
                CollaborationPattern.PEER_TO_PEER: self._handle_peer_collaboration,
                CollaborationPattern.SWARM: self._handle_swarm_collaboration
            }
            
            self.logger.info("Pattern recognition model loaded successfully")
            return pattern_handlers
            
        except Exception as e:
            self.logger.error(f"Failed to load pattern recognition model: {e}")
            raise

    async def initiate_collaboration(self, 
                                   initiator: str,
                                   participants: List[str],
                                   goal: str,
                                   pattern: Optional[CollaborationPattern] = None) -> str:
        """
        发起协作会话
        
        Args:
            initiator: 发起者ID
            participants: 参与者列表
            goal: 协作目标
            pattern: 协作模式
            
        Returns:
            会话ID
        """
        self.logger.info(f"Initiating collaboration session for goal: {goal}")
        
        try:
            # 确定最佳协作模式
            if pattern is None:
                pattern = await self._determine_optimal_pattern(participants, goal)
            
            # 创建协作会话
            session_id = f"collab_{int(time.time())}_{hash(goal) % 10000}"
            session = CollaborationSession(
                session_id=session_id,
                participants=participants,
                pattern=pattern,
                goal=goal,
                start_time=time.time(),
                status="active",
                shared_knowledge={}
            )
            
            self.active_sessions[session_id] = session
            
            # 初始化共享知识
            await self._initialize_shared_knowledge(session)
            
            # 通知参与者
            await self._notify_participants(session, initiator)
            
            # 记录协作开始
            await self.episodic_memory.record_collaboration_start(session)
            
            self.logger.info(f"Collaboration session {session_id} initiated with pattern {pattern.value}")
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to initiate collaboration: {e}")
            return ""

    async def _determine_optimal_pattern(self, participants: List[str], goal: str) -> CollaborationPattern:
        """确定最优协作模式"""
        # 基于历史数据选择模式
        historical_patterns = await self.episodic_memory.get_successful_collaboration_patterns(
            participants, goal
        )
        
        if historical_patterns:
            # 选择最成功的模式
            best_pattern = max(historical_patterns, key=lambda x: x["success_rate"])
            return CollaborationPattern(best_pattern["pattern"])
        
        # 基于参与者和目标特征选择模式
        num_participants = len(participants)
        goal_complexity = await self._assess_goal_complexity(goal)
        
        if num_participants == 1:
            return CollaborationPattern.SEQUENTIAL
        elif num_participants == 2:
            return CollaborationPattern.PEER_TO_PEER
        elif goal_complexity > 0.7 and num_participants > 3:
            return CollaborationPattern.HIERARCHICAL
        elif num_participants > 5:
            return CollaborationPattern.SWARM
        else:
            return CollaborationPattern.PARALLEL

    async def _assess_goal_complexity(self, goal: str) -> float:
        """评估目标复杂性"""
        # 使用语义分析评估目标复杂性
        try:
            complexity_features = {
                "length": len(goal.split()),
                "has_multiple_actions": len([w for w in goal.split() if w in ["and", "then", "after"]]) > 0,
                "requires_coordination": any(word in goal.lower() for word in ["coordinate", "collaborate", "together"]),
                "involves_multiple_domains": len(set(await self._extract_domains(goal))) > 1
            }
            
            complexity_score = sum(complexity_features.values()) / len(complexity_features)
            return min(complexity_score, 1.0)
            
        except Exception:
            return 0.5  # 默认中等复杂性

    async def _extract_domains(self, text: str) -> List[str]:
        """从文本中提取领域信息"""
        # 模拟领域提取 - 实际项目中会使用NLP模型
        domains = []
        text_lower = text.lower()
        
        domain_keywords = {
            "creative": ["create", "design", "write", "compose"],
            "technical": ["code", "debug", "analyze", "optimize"],
            "personal": ["schedule", "remind", "organize"],
            "security": ["secure", "protect", "monitor"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                domains.append(domain)
        
        return domains if domains else ["general"]

    async def _initialize_shared_knowledge(self, session: CollaborationSession):
        """初始化共享知识"""
        # 从语义记忆中获取相关知识
        relevant_knowledge = await self.semantic_memory.retrieve_relevant_knowledge(session.goal)
        
        session.shared_knowledge = {
            "goal": session.goal,
            "participants": session.participants,
            "domain_knowledge": relevant_knowledge,
            "session_context": {
                "start_time": session.start_time,
                "pattern": session.pattern.value
            },
            "intermediate_results": {},
            "decisions_made": []
        }

    async def _notify_participants(self, session: CollaborationSession, initiator: str):
        """通知参与者"""
        notification_tasks = []
        
        for participant in session.participants:
            notification = {
                "session_id": session.session_id,
                "initiator": initiator,
                "goal": session.goal,
                "pattern": session.pattern.value,
                "participants": session.participants,
                "action": "join_collaboration"
            }
            
            task = asyncio.create_task(
                self.message_bus.send_message(f"agent_{participant}_collaboration", notification)
            )
            notification_tasks.append(task)
        
        await asyncio.gather(*notification_tasks)

    async def facilitate_collaboration(self, session_id: str, facilitation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        促进协作过程
        
        Args:
            session_id: 会话ID
            facilitation_data: 促进数据
            
        Returns:
            促进结果
        """
        if session_id not in self.active_sessions:
            return {"success": False, "error": "Session not found"}
        
        session = self.active_sessions[session_id]
        self.logger.info(f"Facilitating collaboration session {session_id}")
        
        try:
            # 获取协作模式处理器
            pattern_handler = self.pattern_recognition_model.get(session.pattern)
            if not pattern_handler:
                return {"success": False, "error": f"Unsupported pattern: {session.pattern}"}
            
            # 执行协作促进
            facilitation_result = await pattern_handler(session, facilitation_data)
            
            # 监控协作质量
            collaboration_quality = await self._monitor_collaboration_quality(session_id)
            facilitation_result["collaboration_quality"] = collaboration_quality
            
            # 更新共享知识
            await self._update_shared_knowledge(session, facilitation_data)
            
            return facilitation_result
            
        except Exception as e:
            self.logger.error(f"Collaboration facilitation failed: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_sequential_collaboration(self, session: CollaborationSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理顺序协作"""
        self.logger.info(f"Handling sequential collaboration for session {session.session_id}")
        
        # 确定执行顺序
        execution_order = await self._determine_execution_order(session.participants, session.goal)
        
        # 协调顺序执行
        results = {}
        current_input = data.get("initial_input", {})
        
        for agent_id in execution_order:
            self.logger.info(f"Sequential step: {agent_id}")
            
            step_task = {
                "session_id": session.session_id,
                "input_data": current_input,
                "step_number": execution_order.index(agent_id) + 1,
                "total_steps": len(execution_order)
            }
            
            # 发送任务给智能体
            response = await self.message_bus.send_and_receive(
                f"agent_{agent_id}_task",
                step_task,
                timeout=60
            )
            
            if response and response.get("success"):
                current_input = response.get("output", {})
                results[agent_id] = current_input
            else:
                self.logger.error(f"Sequential step failed for agent {agent_id}")
                return {"success": False, "failed_step": agent_id}
        
        return {"success": True, "results": results, "pattern": "sequential"}

    async def _handle_parallel_collaboration(self, session: CollaborationSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理并行协作"""
        self.logger.info(f"Handling parallel collaboration for session {session.session_id}")
        
        # 分配并行任务
        task_assignments = await self._assign_parallel_tasks(session.participants, data)
        
        # 并行执行
        parallel_tasks = []
        for agent_id, task_data in task_assignments.items():
            task = asyncio.create_task(
                self.message_bus.send_and_receive(
                    f"agent_{agent_id}_task",
                    {
                        "session_id": session.session_id,
                        "task_data": task_data,
                        "parallel_execution": True
                    },
                    timeout=120
                )
            )
            parallel_tasks.append((agent_id, task))
        
        # 收集结果
        results = {}
        successful_tasks = 0
        
        for agent_id, task in parallel_tasks:
            try:
                response = await task
                if response and response.get("success"):
                    results[agent_id] = response.get("output", {})
                    successful_tasks += 1
                else:
                    results[agent_id] = {"success": False, "error": response.get("error", "Unknown error")}
            except Exception as e:
                results[agent_id] = {"success": False, "error": str(e)}
        
        success_rate = successful_tasks / len(parallel_tasks)
        
        return {
            "success": success_rate > 0.5,
            "results": results,
            "success_rate": success_rate,
            "pattern": "parallel"
        }

    async def _handle_hierarchical_collaboration(self, session: CollaborationSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理层次协作"""
        self.logger.info(f"Handling hierarchical collaboration for session {session.session_id}")
        
        # 确定层次结构
        hierarchy = await self._determine_hierarchy(session.participants, session.goal)
        
        # 协调层次执行
        coordinator_id = hierarchy["coordinator"]
        worker_agents = hierarchy["workers"]
        
        # 协调者分配任务
        coordination_task = {
            "session_id": session.session_id,
            "workers": worker_agents,
            "goal": session.goal,
            "input_data": data,
            "action": "coordinate_workers"
        }
        
        coordination_response = await self.message_bus.send_and_receive(
            f"agent_{coordinator_id}_coordination",
            coordination_task,
            timeout=60
        )
        
        if not coordination_response or not coordination_response.get("success"):
            return {"success": False, "error": "Coordination failed"}
        
        # 执行分配的任务
        worker_tasks = []
        for worker_id, worker_task in coordination_response.get("task_assignments", {}).items():
            task = asyncio.create_task(
                self.message_bus.send_and_receive(
                    f"agent_{worker_id}_task",
                    worker_task,
                    timeout=120
                )
            )
            worker_tasks.append((worker_id, task))
        
        # 收集工人结果
        worker_results = {}
        for worker_id, task in worker_tasks:
            try:
                response = await task
                worker_results[worker_id] = response
            except Exception as e:
                worker_results[worker_id] = {"success": False, "error": str(e)}
        
        # 协调者整合结果
        integration_task = {
            "session_id": session.session_id,
            "worker_results": worker_results,
            "action": "integrate_results"
        }
        
        final_response = await self.message_bus.send_and_receive(
            f"agent_{coordinator_id}_integration",
            integration_task,
            timeout=60
        )
        
        return {
            "success": final_response.get("success", False) if final_response else False,
            "results": final_response,
            "worker_results": worker_results,
            "pattern": "hierarchical"
        }

    async def _handle_peer_collaboration(self, session: CollaborationSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理对等协作"""
        self.logger.info(f"Handling peer-to-peer collaboration for session {session.session_id}")
        
        # 建立对等通信
        peer_connections = await self._establish_peer_connections(session.participants)
        
        # 协调对等协商
        negotiation_results = {}
        for agent_id in session.participants:
            negotiation_task = {
                "session_id": session.session_id,
                "peers": [p for p in session.participants if p != agent_id],
                "goal": session.goal,
                "input_data": data,
                "action": "peer_negotiation"
            }
            
            response = await self.message_bus.send_and_receive(
                f"agent_{agent_id}_negotiation",
                negotiation_task,
                timeout=90
            )
            
            negotiation_results[agent_id] = response
        
        # 达成共识
        consensus = await self._reach_consensus(negotiation_results, session.participants)
        
        return {
            "success": consensus.get("achieved", False),
            "consensus": consensus,
            "negotiation_results": negotiation_results,
            "pattern": "peer_to_peer"
        }

    async def _handle_swarm_collaboration(self, session: CollaborationSession, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理群体协作"""
        self.logger.info(f"Handling swarm collaboration for session {session.session_id}")
        
        # 使用群体协调器
        from .swarm_orchestrator import SwarmOrchestrator, SwarmTask
        
        swarm_task = SwarmTask(
            task_id=session.session_id,
            task_type="collaboration",
            complexity=await self._assess_goal_complexity(session.goal),
            required_capabilities=await self._extract_required_capabilities(session.goal),
            priority=2,
            deadline=time.time() + 3600,
            subtasks=[{"description": session.goal, "required_capabilities": []}]
        )
        
        # 这里需要访问SwarmOrchestrator实例
        # 实际项目中会通过依赖注入或服务发现获取
        swarm_orchestrator = self._get_swarm_orchestrator()
        
        if swarm_orchestrator:
            swarm_result = await swarm_orchestrator.form_swarm(swarm_task, "hybrid")
            return {
                "success": bool(swarm_result),
                "swarm_id": swarm_result,
                "pattern": "swarm"
            }
        else:
            return {"success": False, "error": "Swarm orchestrator not available"}

    async def _determine_execution_order(self, participants: List[str], goal: str) -> List[str]:
        """确定执行顺序"""
        # 基于能力和历史性能确定顺序
        agent_capabilities = await self._get_agent_capabilities(participants)
        goal_requirements = await self._extract_required_capabilities(goal)
        
        # 计算匹配度
        matching_scores = {}
        for agent_id in participants:
            capabilities = agent_capabilities.get(agent_id, [])
            match_score = len(set(capabilities) & set(goal_requirements)) / len(goal_requirements)
            matching_scores[agent_id] = match_score
        
        # 按匹配度排序
        return sorted(participants, key=lambda x: matching_scores.get(x, 0), reverse=True)

    async def _assign_parallel_tasks(self, participants: List[str], data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """分配并行任务"""
        # 基于能力分配任务
        task_assignments = {}
        available_tasks = data.get("parallel_tasks", [])
        
        if not available_tasks:
            # 如果没有预定义任务，创建基于能力的任务
            available_tasks = await self._create_capability_based_tasks(participants, data)
        
        agent_capabilities = await self._get_agent_capabilities(participants)
        
        for task in available_tasks:
            required_caps = task.get("required_capabilities", [])
            best_agent = None
            best_match = 0
            
            for agent_id in participants:
                if agent_id in task_assignments:
                    continue
                    
                capabilities = agent_capabilities.get(agent_id, [])
                match = len(set(capabilities) & set(required_caps)) / len(required_caps) if required_caps else 0.5
                
                if match > best_match:
                    best_match = match
                    best_agent = agent_id
            
            if best_agent and best_match > 0.3:
                task_assignments[best_agent] = task
        
        return task_assignments

    async def _determine_hierarchy(self, participants: List[str], goal: str) -> Dict[str, Any]:
        """确定层次结构"""
        # 基于领导能力和专业知识确定层次
        leadership_scores = await self._assess_leadership_capability(participants)
        expertise_scores = await self._assess_domain_expertise(participants, goal)
        
        # 选择协调者
        coordinator = max(participants, key=lambda x: leadership_scores.get(x, 0) * 0.6 + expertise_scores.get(x, 0) * 0.4)
        workers = [p for p in participants if p != coordinator]
        
        return {"coordinator": coordinator, "workers": workers}

    async def _establish_peer_connections(self, participants: List[str]) -> Dict[str, List[str]]:
        """建立对等连接"""
        # 基于历史协作建立对等连接
        connections = {}
        
        for agent_id in participants:
            # 获取历史协作伙伴
            historical_partners = await self.episodic_memory.get_collaboration_partners(agent_id)
            preferred_partners = [p for p in historical_partners if p in participants]
            
            if not preferred_partners:
                # 如果没有历史伙伴，连接所有其他参与者
                preferred_partners = [p for p in participants if p != agent_id]
            
            connections[agent_id] = preferred_partners
        
        return connections

    async def _reach_consensus(self, negotiation_results: Dict[str, Any], participants: List[str]) -> Dict[str, Any]:
        """达成共识"""
        # 分析协商结果
        proposals = {}
        for agent_id, result in negotiation_results.items():
            if result and result.get("success"):
                proposals[agent_id] = result.get("proposal", {})
        
        if not proposals:
            return {"achieved": False, "error": "No valid proposals"}
        
        # 计算相似度
        similarity_matrix = await self._calculate_proposal_similarity(proposals)
        
        # 寻找最相似的提案
        best_proposal = max(proposals.values(), key=lambda p: self._calculate_proposal_support(p, proposals))
        
        support_count = sum(1 for prop in proposals.values() 
                          if self._proposals_similar(prop, best_proposal) > 0.7)
        
        consensus_achieved = support_count / len(participants) > 0.5
        
        return {
            "achieved": consensus_achieved,
            "supported_proposal": best_proposal if consensus_achieved else None,
            "support_rate": support_count / len(participants),
            "total_participants": len(participants)
        }

    async def _monitor_collaboration_quality(self, session_id: str) -> float:
        """监控协作质量"""
        session = self.active_sessions.get(session_id)
        if not session:
            return 0.0
        
        quality_metrics = {
            "communication_frequency": await self._measure_communication_frequency(session_id),
            "knowledge_sharing": await self._measure_knowledge_sharing(session_id),
            "conflict_resolution": await self._measure_conflict_resolution(session_id),
            "goal_progress": await self._measure_goal_progress(session_id)
        }
        
        # 计算综合质量分数
        quality_score = sum(quality_metrics.values()) / len(quality_metrics)
        return quality_score

    async def _measure_communication_frequency(self, session_id: str) -> float:
        """测量通信频率"""
        # 模拟通信频率测量
        return 0.8  # 实际项目中会分析消息总线数据

    async def _measure_knowledge_sharing(self, session_id: str) -> float:
        """测量知识共享程度"""
        session = self.active_sessions.get(session_id)
        if not session:
            return 0.0
        
        knowledge_entries = len(session.shared_knowledge.get("intermediate_results", {}))
        participant_count = len(session.participants)
        
        sharing_score = min(knowledge_entries / (participant_count * 2), 1.0)
        return sharing_score

    async def _measure_conflict_resolution(self, session_id: str) -> float:
        """测量冲突解决效果"""
        # 模拟冲突解决测量
        return 0.9  # 实际项目中会分析冲突解决记录

    async def _measure_goal_progress(self, session_id: str) -> float:
        """测量目标进展"""
        # 模拟目标进展测量
        return 0.7  # 实际项目中会分析任务完成情况

    async def _update_shared_knowledge(self, session: CollaborationSession, new_data: Dict[str, Any]):
        """更新共享知识"""
        # 添加新知识
        if "new_knowledge" in new_data:
            session.shared_knowledge["intermediate_results"].update(new_data["new_knowledge"])
        
        # 记录决策
        if "decision" in new_data:
            session.shared_knowledge["decisions_made"].append({
                "timestamp": time.time(),
                "decision": new_data["decision"],
                "made_by": new_data.get("made_by", "unknown")
            })

    async def _get_agent_capabilities(self, agent_ids: List[str]) -> Dict[str, List[str]]:
        """获取智能体能力"""
        # 模拟能力查询 - 实际项目中会从智能体注册表获取
        capabilities = {}
        for agent_id in agent_ids:
            # 模拟不同智能体的能力
            if "creative" in agent_id:
                capabilities[agent_id] = ["writing", "design", "creativity"]
            elif "technical" in agent_id:
                capabilities[agent_id] = ["coding", "debugging", "analysis"]
            elif "personal" in agent_id:
                capabilities[agent_id] = ["scheduling", "organization", "communication"]
            elif "security" in agent_id:
                capabilities[agent_id] = ["monitoring", "protection", "analysis"]
            else:
                capabilities[agent_id] = ["general"]
        
        return capabilities

    async def _extract_required_capabilities(self, goal: str) -> List[str]:
        """从目标中提取所需能力"""
        required_capabilities = []
        goal_lower = goal.lower()
        
        capability_mapping = {
            "writing": ["write", "compose", "draft"],
            "design": ["design", "create", "layout"],
            "coding": ["code", "program", "develop"],
            "analysis": ["analyze", "evaluate", "assess"],
            "scheduling": ["schedule", "plan", "organize"],
            "monitoring": ["monitor", "watch", "observe"]
        }
        
        for capability, keywords in capability_mapping.items():
            if any(keyword in goal_lower for keyword in keywords):
                required_capabilities.append(capability)
        
        return required_capabilities if required_capabilities else ["general"]

    async def _assess_leadership_capability(self, agent_ids: List[str]) -> Dict[str, float]:
        """评估领导能力"""
        # 模拟领导能力评估
        leadership_scores = {}
        for agent_id in agent_ids:
            # 基于历史协作表现评估
            historical_performance = await self.episodic_memory.get_agent_leadership_performance(agent_id)
            leadership_scores[agent_id] = historical_performance.get("success_rate", 0.5)
        
        return leadership_scores

    async def _assess_domain_expertise(self, agent_ids: List[str], goal: str) -> Dict[str, float]:
        """评估领域专业知识"""
        # 模拟专业知识评估
        expertise_scores = {}
        goal_domains = await self._extract_domains(goal)
        
        for agent_id in agent_ids:
            # 基于历史表现评估
            domain_expertise = await self.episodic_memory.get_agent_domain_expertise(agent_id, goal_domains)
            expertise_scores[agent_id] = domain_expertise.get("expertise_score", 0.5)
        
        return expertise_scores

    async def _create_capability_based_tasks(self, participants: List[str], data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建基于能力的任务"""
        agent_capabilities = await self._get_agent_capabilities(participants)
        all_capabilities = set()
        
        for capabilities in agent_capabilities.values():
            all_capabilities.update(capabilities)
        
        tasks = []
        for capability in all_capabilities:
            tasks.append({
                "description": f"Task requiring {capability}",
                "required_capabilities": [capability],
                "input_data": data
            })
        
        return tasks

    def _calculate_proposal_support(self, proposal: Dict[str, Any], all_proposals: Dict[str, Any]) -> float:
        """计算提案支持度"""
        support = 0
        for other_proposal in all_proposals.values():
            if self._proposals_similar(proposal, other_proposal) > 0.7:
                support += 1
        
        return support / len(all_proposals)

    def _proposals_similar(self, prop1: Dict[str, Any], prop2: Dict[str, Any]) -> float:
        """计算提案相似度"""
        # 简单相似度计算 - 实际项目中会使用更复杂的算法
        if not prop1 or not prop2:
            return 0.0
        
        keys1 = set(prop1.keys())
        keys2 = set(prop2.keys())
        
        common_keys = keys1.intersection(keys2)
        if not common_keys:
            return 0.0
        
        similarity = 0
        for key in common_keys:
            if prop1[key] == prop2[key]:
                similarity += 1
        
        return similarity / len(common_keys)

    async def _calculate_proposal_similarity(self, proposals: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """计算提案相似度矩阵"""
        similarity_matrix = {}
        agent_ids = list(proposals.keys())
        
        for i, agent1 in enumerate(agent_ids):
            similarity_matrix[agent1] = {}
            for j, agent2 in enumerate(agent_ids):
                if i == j:
                    similarity_matrix[agent1][agent2] = 1.0
                else:
                    similarity_matrix[agent1][agent2] = self._proposals_similar(
                        proposals[agent1], proposals[agent2]
                    )
        
        return similarity_matrix

    def _get_swarm_orchestrator(self):
        """获取群体协调器实例"""
        # 在实际项目中，这会通过依赖注入或服务发现实现
        # 这里返回None作为占位符
        return None

    async def complete_collaboration(self, session_id: str, results: Dict[str, Any]) -> CollaborationResult:
        """
        完成协作会话
        
        Args:
            session_id: 会话ID
            results: 协作结果
            
        Returns:
            协作结果对象
        """
        if session_id not in self.active_sessions:
            return CollaborationResult(
                session_id=session_id,
                success=False,
                results={},
                participant_contributions={},
                collaboration_quality=0.0,
                duration=0.0
            )
        
        session = self.active_sessions[session_id]
        session.status = "completed"
        
        # 计算协作持续时间
        duration = time.time() - session.start_time
        
        # 计算参与者贡献
        contributions = await self._calculate_participant_contributions(session_id)
        
        # 计算协作质量
        collaboration_quality = await self._monitor_collaboration_quality(session_id)
        
        # 创建结果对象
        collaboration_result = CollaborationResult(
            session_id=session_id,
            success=results.get("success", False),
            results=results,
            participant_contributions=contributions,
            collaboration_quality=collaboration_quality,
            duration=duration
        )
        
        # 记录到历史
        self.collaboration_history.append({
            "session": session.__dict__,
            "result": collaboration_result.__dict__,
            "timestamp": time.time()
        })
        
        # 保存到记忆系统
        await self.episodic_memory.record_collaboration_result(collaboration_result)
        
        # 更新共享知识库
        await self._update_shared_knowledge_base(session, collaboration_result)
        
        # 移除活跃会话
        del self.active_sessions[session_id]
        
        self.logger.info(f"Collaboration session {session_id} completed with quality {collaboration_quality:.2f}")
        
        return collaboration_result

    async def _calculate_participant_contributions(self, session_id: str) -> Dict[str, float]:
        """计算参与者贡献"""
        session = self.active_sessions.get(session_id)
        if not session:
            return {}
        
        # 模拟贡献计算 - 实际项目中会基于实际参与度计算
        contributions = {}
        total_participants = len(session.participants)
        
        for participant in session.participants:
            # 基于通信频率和知识共享计算贡献
            communication_score = await self._measure_agent_communication(participant, session_id)
            knowledge_contribution = await self._measure_knowledge_contribution(participant, session_id)
            
            contributions[participant] = (communication_score + knowledge_contribution) / 2
        
        # 归一化
        total_contribution = sum(contributions.values())
        if total_contribution > 0:
            contributions = {k: v/total_contribution for k, v in contributions.items()}
        
        return contributions

    async def _measure_agent_communication(self, agent_id: str, session_id: str) -> float:
        """测量智能体通信参与度"""
        # 模拟通信参与度测量
        return 0.8  # 实际项目中会分析消息总线数据

    async def _measure_knowledge_contribution(self, agent_id: str, session_id: str) -> float:
        """测量知识贡献"""
        session = self.active_sessions.get(session_id)
        if not session:
            return 0.0
        
        # 计算该智能体贡献的知识比例
        agent_knowledge = session.shared_knowledge.get("contributions", {}).get(agent_id, {})
        total_knowledge = len(session.shared_knowledge.get("intermediate_results", {}))
        
        if total_knowledge == 0:
            return 0.5  # 默认贡献
        
        contribution_ratio = len(agent_knowledge) / total_knowledge
        return min(contribution_ratio, 1.0)

    async def _update_shared_knowledge_base(self, session: CollaborationSession, result: CollaborationResult):
        """更新共享知识库"""
        # 将成功的协作知识添加到共享知识库
        if result.success and result.collaboration_quality > 0.7:
            knowledge_key = f"collab_{session.session_id}"
            self.shared_knowledge_base[knowledge_key] = {
                "goal": session.goal,
                "pattern": session.pattern.value,
                "participants": session.participants,
                "results": result.results,
                "quality": result.collaboration_quality,
                "timestamp": time.time()
            }
            
            # 记录知识访问日志
            self.knowledge_access_log.append({
                "knowledge_key": knowledge_key,
                "accessed_by": "system",
                "purpose": "collaboration_completion",
                "timestamp": time.time()
            })

    def get_collaboration_statistics(self) -> Dict[str, Any]:
        """获取协作统计信息"""
        total_sessions = len(self.collaboration_history)
        successful_sessions = len([h for h in self.collaboration_history 
                                 if h["result"]["success"]])
        
        avg_quality = np.mean([h["result"]["collaboration_quality"] 
                             for h in self.collaboration_history]) if self.collaboration_history else 0
        
        pattern_distribution = defaultdict(int)
        for history in self.collaboration_history:
            pattern = history["session"]["pattern"]
            pattern_distribution[pattern] += 1
        
        return {
            "total_sessions": total_sessions,
            "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0,
            "average_quality": avg_quality,
            "active_sessions": len(self.active_sessions),
            "pattern_distribution": dict(pattern_distribution),
            "knowledge_base_size": len(self.shared_knowledge_base)
        }

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up CollaborationEngine...")
        
        # 完成所有活跃会话
        for session_id in list(self.active_sessions.keys()):
            await self.complete_collaboration(session_id, {"success": False, "reason": "system_cleanup"})
        
        self.logger.info("CollaborationEngine cleanup completed")

