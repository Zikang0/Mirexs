"""
角色特化器：实现智能体角色的动态特化和能力优化
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict
import time
import json

from ..memory.episodic_memory import EpisodicMemory
from ..memory.semantic_memory import SemanticMemory
from ..memory.working_memory import WorkingMemory
from ...infrastructure.communication.message_bus import MessageBus
from ...data.databases.vector_db.similarity_search import SimilaritySearch

class RoleType(Enum):
    """角色类型枚举"""
    GENERALIST = "generalist"
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    PERSONAL = "personal"
    SECURITY = "security"

@dataclass
class RoleProfile:
    """角色配置文件"""
    role_type: RoleType
    core_competencies: List[str]
    skill_weights: Dict[str, float]
    learning_parameters: Dict[str, float]
    performance_thresholds: Dict[str, float]
    adaptation_strategy: str

@dataclass
class SpecializationResult:
    """特化结果"""
    agent_id: str
    original_role: RoleType
    new_role: RoleType
    specialization_level: float
    improved_competencies: List[str]
    adaptation_duration: float
    success: bool

class RoleSpecializer:
    """
    角色特化器 - 管理智能体角色的动态特化和优化
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
        
        # 角色管理
        self.agent_roles: Dict[str, RoleProfile] = {}
        self.role_templates: Dict[RoleType, RoleProfile] = {}
        self.specialization_history: List[Dict[str, Any]] = []
        
        # 性能跟踪
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        self.adaptation_log: List[Dict[str, Any]] = []
        
        # 模型加载
        self.specialization_model = self._load_specialization_model()
        self.role_assessment_model = self._load_role_assessment_model()
        
        self.logger.info("RoleSpecializer initialized")

    def _load_specialization_model(self):
        """加载特化模型"""
        try:
            self.logger.info("Loading specialization model...")
            
            # 模拟特化模型参数
            specialization_config = {
                "max_adaptation_time": self.config.get("max_adaptation_time", 3600),
                "min_performance_improvement": self.config.get("min_performance_improvement", 0.1),
                "role_compatibility_threshold": self.config.get("role_compatibility_threshold", 0.7),
                "learning_rate": self.config.get("learning_rate", 0.01),
                "exploration_factor": self.config.get("exploration_factor", 0.1)
            }
            
            self.logger.info("Specialization model loaded successfully")
            return specialization_config
            
        except Exception as e:
            self.logger.error(f"Failed to load specialization model: {e}")
            raise

    def _load_role_assessment_model(self):
        """加载角色评估模型"""
        try:
            self.logger.info("Loading role assessment model...")
            
            # 初始化角色模板
            self._initialize_role_templates()
            
            # 模拟评估函数
            assessment_functions = {
                "performance_based": self._assess_performance_based,
                "capability_based": self._assess_capability_based,
                "hybrid": self._assess_hybrid,
                "context_aware": self._assess_context_aware
            }
            
            self.logger.info("Role assessment model loaded successfully")
            return assessment_functions
            
        except Exception as e:
            self.logger.error(f"Failed to load role assessment model: {e}")
            raise

    def _initialize_role_templates(self):
        """初始化角色模板"""
        # 通用角色模板
        self.role_templates[RoleType.GENERALIST] = RoleProfile(
            role_type=RoleType.GENERALIST,
            core_competencies=["problem_solving", "communication", "adaptability"],
            skill_weights={
                "problem_solving": 0.3,
                "communication": 0.3,
                "adaptability": 0.4
            },
            learning_parameters={"learning_rate": 0.02, "exploration": 0.15},
            performance_thresholds={"min_success_rate": 0.6, "max_response_time": 5.0},
            adaptation_strategy="balanced"
        )
        
        # 创意角色模板
        self.role_templates[RoleType.CREATIVE] = RoleProfile(
            role_type=RoleType.CREATIVE,
            core_competencies=["creativity", "ideation", "design_thinking"],
            skill_weights={
                "creativity": 0.5,
                "ideation": 0.3,
                "design_thinking": 0.2
            },
            learning_parameters={"learning_rate": 0.03, "exploration": 0.2},
            performance_thresholds={"min_innovation_score": 0.7, "max_iteration_time": 10.0},
            adaptation_strategy="explorative"
        )
        
        # 技术角色模板
        self.role_templates[RoleType.TECHNICAL] = RoleProfile(
            role_type=RoleType.TECHNICAL,
            core_competencies=["technical_analysis", "problem_solving", "precision"],
            skill_weights={
                "technical_analysis": 0.4,
                "problem_solving": 0.4,
                "precision": 0.2
            },
            learning_parameters={"learning_rate": 0.015, "exploration": 0.05},
            performance_thresholds={"min_accuracy": 0.9, "max_processing_time": 3.0},
            adaptation_strategy="focused"
        )
        
        # 个人助理角色模板
        self.role_templates[RoleType.PERSONAL] = RoleProfile(
            role_type=RoleType.PERSONAL,
            core_competencies=["personalization", "scheduling", "communication"],
            skill_weights={
                "personalization": 0.4,
                "scheduling": 0.3,
                "communication": 0.3
            },
            learning_parameters={"learning_rate": 0.025, "exploration": 0.1},
            performance_thresholds={"min_user_satisfaction": 0.8, "max_response_time": 2.0},
            adaptation_strategy="adaptive"
        )
        
        # 安全角色模板
        self.role_templates[RoleType.SECURITY] = RoleProfile(
            role_type=RoleType.SECURITY,
            core_competencies=["threat_detection", "risk_assessment", "vigilance"],
            skill_weights={
                "threat_detection": 0.5,
                "risk_assessment": 0.3,
                "vigilance": 0.2
            },
            learning_parameters={"learning_rate": 0.01, "exploration": 0.02},
            performance_thresholds={"min_detection_rate": 0.95, "max_response_time": 1.0},
            adaptation_strategy="defensive"
        )
        
        # 协调者角色模板
        self.role_templates[RoleType.COORDINATOR] = RoleProfile(
            role_type=RoleType.COORDINATOR,
            core_competencies=["coordination", "leadership", "conflict_resolution"],
            skill_weights={
                "coordination": 0.4,
                "leadership": 0.3,
                "conflict_resolution": 0.3
            },
            learning_parameters={"learning_rate": 0.02, "exploration": 0.08},
            performance_thresholds={"min_coordination_success": 0.8, "max_decision_time": 5.0},
            adaptation_strategy="collaborative"
        )

    async def register_agent(self, agent_id: str, initial_role: RoleType = RoleType.GENERALIST) -> bool:
        """
        注册智能体
        
        Args:
            agent_id: 智能体ID
            initial_role: 初始角色
            
        Returns:
            注册是否成功
        """
        try:
            if initial_role not in self.role_templates:
                self.logger.error(f"Unknown role type: {initial_role}")
                return False
            
            # 创建初始角色配置
            template = self.role_templates[initial_role]
            agent_role = RoleProfile(
                role_type=initial_role,
                core_competencies=template.core_competencies.copy(),
                skill_weights=template.skill_weights.copy(),
                learning_parameters=template.learning_parameters.copy(),
                performance_thresholds=template.performance_thresholds.copy(),
                adaptation_strategy=template.adaptation_strategy
            )
            
            self.agent_roles[agent_id] = agent_role
            
            # 初始化性能指标
            self.performance_metrics[agent_id] = {
                "task_success_rate": 0.5,
                "average_response_time": 0.0,
                "skill_proficiency": {competency: 0.5 for competency in agent_role.core_competencies},
                "role_satisfaction": 0.5,
                "adaptation_count": 0
            }
            
            self.logger.info(f"Agent {agent_id} registered with initial role: {initial_role.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    async def assess_role_suitability(self, 
                                    agent_id: str, 
                                    assessment_strategy: str = "hybrid") -> Dict[str, Any]:
        """
        评估角色适合度
        
        Args:
            agent_id: 智能体ID
            assessment_strategy: 评估策略
            
        Returns:
            适合度评估结果
        """
        if agent_id not in self.agent_roles:
            return {"success": False, "error": "Agent not registered"}
        
        current_role = self.agent_roles[agent_id]
        performance_data = self.performance_metrics.get(agent_id, {})
        
        self.logger.info(f"Assessing role suitability for agent {agent_id}")
        
        try:
            # 选择评估策略
            assessment_func = self.role_assessment_model.get(assessment_strategy, self._assess_hybrid)
            suitability_scores = await assessment_func(agent_id, current_role, performance_data)
            
            # 找到最适合的角色
            best_role = max(suitability_scores.items(), key=lambda x: x[1])
            
            assessment_result = {
                "agent_id": agent_id,
                "current_role": current_role.role_type.value,
                "suitability_scores": {k.value: v for k, v in suitability_scores.items()},
                "recommended_role": best_role[0].value,
                "recommendation_confidence": best_role[1],
                "assessment_timestamp": time.time()
            }
            
            # 记录评估结果
            self.adaptation_log.append(assessment_result)
            
            return assessment_result
            
        except Exception as e:
            self.logger.error(f"Role assessment failed for agent {agent_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _assess_performance_based(self, 
                                      agent_id: str, 
                                      current_role: RoleProfile,
                                      performance_data: Dict[str, Any]) -> Dict[RoleType, float]:
        """基于性能的角色评估"""
        suitability_scores = {}
        
        for role_type, template in self.role_templates.items():
            # 计算性能匹配度
            performance_match = 0.0
            matched_metrics = 0
            
            for metric, threshold in template.performance_thresholds.items():
                if metric in performance_data:
                    actual_value = performance_data[metric]
                    if isinstance(threshold, (int, float)):
                        # 数值型指标
                        if "min" in metric:
                            match = min(actual_value / threshold, 1.0) if threshold > 0 else 1.0
                        else:  # max指标
                            match = min(threshold / actual_value, 1.0) if actual_value > 0 else 1.0
                        performance_match += match
                        matched_metrics += 1
            
            if matched_metrics > 0:
                suitability_scores[role_type] = performance_match / matched_metrics
            else:
                suitability_scores[role_type] = 0.5  # 默认分数
        
        return suitability_scores

    async def _assess_capability_based(self, 
                                     agent_id: str, 
                                     current_role: RoleProfile,
                                     performance_data: Dict[str, Any]) -> Dict[RoleType, float]:
        """基于能力的角色评估"""
        suitability_scores = {}
        agent_skills = performance_data.get("skill_proficiency", {})
        
        for role_type, template in self.role_templates.items():
            capability_match = 0.0
            total_weight = 0.0
            
            for competency, weight in template.skill_weights.items():
                skill_level = agent_skills.get(competency, 0.5)
                capability_match += skill_level * weight
                total_weight += weight
            
            if total_weight > 0:
                suitability_scores[role_type] = capability_match / total_weight
            else:
                suitability_scores[role_type] = 0.5
        
        return suitability_scores

    async def _assess_hybrid(self, 
                           agent_id: str, 
                           current_role: RoleProfile,
                           performance_data: Dict[str, Any]) -> Dict[RoleType, float]:
        """混合角色评估"""
        # 结合性能和能力评估
        performance_scores = await self._assess_performance_based(agent_id, current_role, performance_data)
        capability_scores = await self._assess_capability_based(agent_id, current_role, performance_data)
        
        suitability_scores = {}
        for role_type in self.role_templates.keys():
            perf_score = performance_scores.get(role_type, 0.5)
            cap_score = capability_scores.get(role_type, 0.5)
            
            # 加权组合
            suitability_scores[role_type] = perf_score * 0.6 + cap_score * 0.4
        
        return suitability_scores

    async def _assess_context_aware(self, 
                                  agent_id: str, 
                                  current_role: RoleProfile,
                                  performance_data: Dict[str, Any]) -> Dict[RoleType, float]:
        """上下文感知的角色评估"""
        # 获取上下文信息
        context_data = await self._get_agent_context(agent_id)
        
        # 结合上下文进行混合评估
        hybrid_scores = await self._assess_hybrid(agent_id, current_role, performance_data)
        
        # 根据上下文调整分数
        context_adjustments = await self._calculate_context_adjustments(agent_id, context_data)
        
        suitability_scores = {}
        for role_type, base_score in hybrid_scores.items():
            adjustment = context_adjustments.get(role_type, 1.0)
            suitability_scores[role_type] = min(base_score * adjustment, 1.0)
        
        return suitability_scores

    async def _get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """获取智能体上下文"""
        try:
            # 从记忆系统获取上下文信息
            recent_tasks = await self.episodic_memory.get_recent_tasks(agent_id, limit=10)
            collaboration_patterns = await self.episodic_memory.get_collaboration_patterns(agent_id)
            environmental_factors = await self.working_memory.get_environmental_context(agent_id)
            
            return {
                "recent_tasks": recent_tasks,
                "collaboration_patterns": collaboration_patterns,
                "environmental_factors": environmental_factors,
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.warning(f"Failed to get agent context for {agent_id}: {e}")
            return {}

    async def _calculate_context_adjustments(self, agent_id: str, context_data: Dict[str, Any]) -> Dict[RoleType, float]:
        """计算上下文调整因子"""
        adjustments = {role_type: 1.0 for role_type in self.role_templates.keys()}
        
        try:
            recent_tasks = context_data.get("recent_tasks", [])
            collaboration_patterns = context_data.get("collaboration_patterns", {})
            
            # 分析任务类型分布
            task_type_distribution = defaultdict(int)
            for task in recent_tasks:
                task_type = task.get("type", "unknown")
                task_type_distribution[task_type] += 1
            
            # 根据任务分布调整角色适合度
            total_tasks = len(recent_tasks)
            if total_tasks > 0:
                for role_type in self.role_templates.keys():
                    role_task_affinity = self._calculate_role_task_affinity(role_type, task_type_distribution)
                    adjustments[role_type] *= (1.0 + role_task_affinity * 0.3)  # 最大30%调整
            
            # 考虑协作模式
            if collaboration_patterns:
                coordinator_need = collaboration_patterns.get("coordination_required", 0)
                adjustments[RoleType.COORDINATOR] *= (1.0 + coordinator_need * 0.2)
        
        except Exception as e:
            self.logger.warning(f"Context adjustment calculation failed: {e}")
        
        return adjustments

    def _calculate_role_task_affinity(self, role_type: RoleType, task_distribution: Dict[str, int]) -> float:
        """计算角色与任务的亲和度"""
        # 定义角色与任务类型的映射
        role_task_mapping = {
            RoleType.CREATIVE: ["creative", "design", "writing", "ideation"],
            RoleType.TECHNICAL: ["technical", "analysis", "debugging", "optimization"],
            RoleType.PERSONAL: ["personal", "scheduling", "organization", "reminder"],
            RoleType.SECURITY: ["security", "monitoring", "protection", "threat_detection"],
            RoleType.COORDINATOR: ["coordination", "planning", "management"],
            RoleType.GENERALIST: []  # 通用角色匹配所有任务
        }
        
        if role_type == RoleType.GENERALIST:
            return 0.5  # 通用角色中等亲和度
        
        relevant_tasks = role_task_mapping.get(role_type, [])
        total_relevant = sum(count for task_type, count in task_distribution.items() 
                           if any(keyword in task_type for keyword in relevant_tasks))
        total_tasks = sum(task_distribution.values())
        
        if total_tasks == 0:
            return 0.5
        
        return total_relevant / total_tasks

    async def specialize_agent(self, 
                             agent_id: str, 
                             target_role: RoleType,
                             adaptation_strategy: Optional[str] = None) -> SpecializationResult:
        """
        特化智能体角色
        
        Args:
            agent_id: 智能体ID
            target_role: 目标角色
            adaptation_strategy: 适应策略
            
        Returns:
            特化结果
        """
        if agent_id not in self.agent_roles:
            return SpecializationResult(
                agent_id=agent_id,
                original_role=RoleType.GENERALIST,
                new_role=target_role,
                specialization_level=0.0,
                improved_competencies=[],
                adaptation_duration=0.0,
                success=False
            )
        
        original_role = self.agent_roles[agent_id]
        start_time = time.time()
        
        self.logger.info(f"Specializing agent {agent_id} from {original_role.role_type.value} to {target_role.value}")
        
        try:
            # 获取目标角色模板
            if target_role not in self.role_templates:
                self.logger.error(f"Unknown target role: {target_role}")
                return SpecializationResult(
                    agent_id=agent_id,
                    original_role=original_role.role_type,
                    new_role=target_role,
                    specialization_level=0.0,
                    improved_competencies=[],
                    adaptation_duration=time.time() - start_time,
                    success=False
                )
            
            target_template = self.role_templates[target_role]
            
            # 执行角色特化
            specialization_success = await self._execute_specialization(
                agent_id, original_role, target_template, adaptation_strategy
            )
            
            adaptation_duration = time.time() - start_time
            
            if specialization_success:
                # 更新角色配置
                self.agent_roles[agent_id] = RoleProfile(
                    role_type=target_role,
                    core_competencies=target_template.core_competencies.copy(),
                    skill_weights=target_template.skill_weights.copy(),
                    learning_parameters=target_template.learning_parameters.copy(),
                    performance_thresholds=target_template.performance_thresholds.copy(),
                    adaptation_strategy=adaptation_strategy or target_template.adaptation_strategy
                )
                
                # 计算特化程度
                specialization_level = await self._calculate_specialization_level(agent_id, target_role)
                
                # 识别提升的能力
                improved_competencies = await self._identify_improved_competencies(agent_id, target_role)
                
                # 更新性能指标
                self.performance_metrics[agent_id]["adaptation_count"] += 1
                
                result = SpecializationResult(
                    agent_id=agent_id,
                    original_role=original_role.role_type,
                    new_role=target_role,
                    specialization_level=specialization_level,
                    improved_competencies=improved_competencies,
                    adaptation_duration=adaptation_duration,
                    success=True
                )
                
                self.logger.info(f"Agent {agent_id} successfully specialized to {target_role.value}")
                
            else:
                result = SpecializationResult(
                    agent_id=agent_id,
                    original_role=original_role.role_type,
                    new_role=target_role,
                    specialization_level=0.0,
                    improved_competencies=[],
                    adaptation_duration=adaptation_duration,
                    success=False
                )
                
                self.logger.warning(f"Agent {agent_id} specialization failed")
            
            # 记录特化历史
            self.specialization_history.append({
                "agent_id": agent_id,
                "original_role": original_role.role_type.value,
                "target_role": target_role.value,
                "result": result.__dict__,
                "timestamp": time.time()
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Specialization process failed for agent {agent_id}: {e}")
            
            return SpecializationResult(
                agent_id=agent_id,
                original_role=original_role.role_type,
                new_role=target_role,
                specialization_level=0.0,
                improved_competencies=[],
                adaptation_duration=time.time() - start_time,
                success=False
            )

    async def _execute_specialization(self,
                                   agent_id: str,
                                   current_role: RoleProfile,
                                   target_template: RoleProfile,
                                   adaptation_strategy: Optional[str]) -> bool:
        """执行角色特化"""
        try:
            # 通知智能体开始特化
            specialization_notification = {
                "action": "start_specialization",
                "current_role": current_role.role_type.value,
                "target_role": target_template.role_type.value,
                "target_competencies": target_template.core_competencies,
                "adaptation_strategy": adaptation_strategy or target_template.adaptation_strategy
            }
            
            await self.message_bus.send_message(
                f"agent_{agent_id}_specialization",
                specialization_notification
            )
            
            # 执行能力训练
            training_success = await self._train_agent_competencies(
                agent_id, current_role, target_template
            )
            
            if not training_success:
                self.logger.warning(f"Competency training failed for agent {agent_id}")
                return False
            
            # 验证特化效果
            validation_success = await self._validate_specialization(agent_id, target_template)
            
            return validation_success
            
        except Exception as e:
            self.logger.error(f"Specialization execution failed for agent {agent_id}: {e}")
            return False

    async def _train_agent_competencies(self,
                                      agent_id: str,
                                      current_role: RoleProfile,
                                      target_template: RoleProfile) -> bool:
        """训练智能体能力"""
        try:
            # 识别需要训练的能力
            current_skills = self.performance_metrics[agent_id].get("skill_proficiency", {})
            training_needs = []
            
            for competency in target_template.core_competencies:
                current_level = current_skills.get(competency, 0.5)
                target_level = target_template.skill_weights.get(competency, 0.5)
                
                if current_level < target_level * 0.8:  # 需要提升
                    training_needs.append({
                        "competency": competency,
                        "current_level": current_level,
                        "target_level": target_level,
                        "improvement_needed": target_level - current_level
                    })
            
            if not training_needs:
                self.logger.info(f"Agent {agent_id} already meets competency requirements")
                return True
            
            # 执行训练
            training_tasks = []
            for need in training_needs:
                training_task = {
                    "agent_id": agent_id,
                    "competency": need["competency"],
                    "training_intensity": need["improvement_needed"],
                    "training_method": self._select_training_method(need["competency"])
                }
                training_tasks.append(training_task)
            
            # 发送训练任务
            for task in training_tasks:
                await self.message_bus.send_message(
                    f"agent_{agent_id}_training",
                    task
                )
            
            # 监控训练进度
            training_success = await self._monitor_training_progress(agent_id, training_needs)
            
            return training_success
            
        except Exception as e:
            self.logger.error(f"Competency training failed for agent {agent_id}: {e}")
            return False

    def _select_training_method(self, competency: str) -> str:
        """选择训练方法"""
        method_mapping = {
            "creativity": "creative_exercises",
            "technical_analysis": "problem_solving_tasks",
            "personalization": "user_interaction_simulation",
            "threat_detection": "security_scenarios",
            "coordination": "collaboration_exercises",
            "communication": "dialogue_practice"
        }
        
        return method_mapping.get(competency, "general_training")

    async def _monitor_training_progress(self, 
                                      agent_id: str, 
                                      training_needs: List[Dict[str, Any]]) -> bool:
        """监控训练进度"""
        max_training_time = self.specialization_model["max_adaptation_time"]
        start_time = time.time()
        
        while time.time() - start_time < max_training_time:
            # 检查技能提升
            current_skills = self.performance_metrics[agent_id].get("skill_proficiency", {})
            all_trained = True
            
            for need in training_needs:
                current_level = current_skills.get(need["competency"], 0.5)
                if current_level < need["target_level"] * 0.8:  # 达到目标的80%即可
                    all_trained = False
                    break
            
            if all_trained:
                self.logger.info(f"Agent {agent_id} training completed successfully")
                return True
            
            await asyncio.sleep(1)  # 每秒检查一次
        
        self.logger.warning(f"Agent {agent_id} training timeout")
        return False

    async def _validate_specialization(self, agent_id: str, target_template: RoleProfile) -> bool:
        """验证特化效果"""
        try:
            # 执行验证任务
            validation_tasks = self._create_validation_tasks(target_template)
            successful_validations = 0
            
            for task in validation_tasks:
                validation_result = await self._execute_validation_task(agent_id, task)
                if validation_result:
                    successful_validations += 1
            
            success_rate = successful_validations / len(validation_tasks)
            min_success_rate = target_template.performance_thresholds.get("min_success_rate", 0.7)
            
            validation_success = success_rate >= min_success_rate
            
            self.logger.info(f"Agent {agent_id} specialization validation: {success_rate:.2f} (required: {min_success_rate})")
            
            return validation_success
            
        except Exception as e:
            self.logger.error(f"Specialization validation failed for agent {agent_id}: {e}")
            return False

    def _create_validation_tasks(self, target_template: RoleProfile) -> List[Dict[str, Any]]:
        """创建验证任务"""
        role_validation_mapping = {
            RoleType.CREATIVE: [
                {"type": "ideation", "complexity": "medium"},
                {"type": "design", "requirements": "basic"}
            ],
            RoleType.TECHNICAL: [
                {"type": "analysis", "data_complexity": "medium"},
                {"type": "problem_solving", "difficulty": "intermediate"}
            ],
            RoleType.PERSONAL: [
                {"type": "scheduling", "constraints": "multiple"},
                {"type": "personalization", "context": "complex"}
            ],
            RoleType.SECURITY: [
                {"type": "threat_detection", "scenario": "standard"},
                {"type": "risk_assessment", "factors": "multiple"}
            ],
            RoleType.COORDINATOR: [
                {"type": "task_allocation", "agents": 3},
                {"type": "conflict_resolution", "complexity": "medium"}
            ]
        }
        
        return role_validation_mapping.get(target_template.role_type, [{"type": "general_validation"}])

    async def _execute_validation_task(self, agent_id: str, task: Dict[str, Any]) -> bool:
        """执行验证任务"""
        try:
            # 发送验证任务给智能体
            response = await self.message_bus.send_and_receive(
                f"agent_{agent_id}_validation",
                task,
                timeout=30
            )
            
            return response and response.get("success", False)
            
        except Exception as e:
            self.logger.error(f"Validation task execution failed: {e}")
            return False

    async def _calculate_specialization_level(self, agent_id: str, target_role: RoleType) -> float:
        """计算特化程度"""
        try:
            target_template = self.role_templates[target_role]
            current_skills = self.performance_metrics[agent_id].get("skill_proficiency", {})
            
            specialization_score = 0.0
            total_weight = 0.0
            
            for competency, weight in target_template.skill_weights.items():
                skill_level = current_skills.get(competency, 0.5)
                specialization_score += skill_level * weight
                total_weight += weight
            
            if total_weight > 0:
                return specialization_score / total_weight
            else:
                return 0.5
                
        except Exception:
            return 0.5

    async def _identify_improved_competencies(self, agent_id: str, target_role: RoleType) -> List[str]:
        """识别提升的能力"""
        try:
            # 这里需要比较特化前后的技能水平
            # 简化实现：返回目标角色的核心能力
            target_template = self.role_templates[target_role]
            return target_template.core_competencies.copy()
            
        except Exception:
            return []

    async def update_performance_metrics(self, agent_id: str, metrics: Dict[str, Any]):
        """更新性能指标"""
        if agent_id in self.performance_metrics:
            self.performance_metrics[agent_id].update(metrics)
            
            # 检查是否需要角色调整
            await self._check_role_adjustment_needed(agent_id)

    async def _check_role_adjustment_needed(self, agent_id: str):
        """检查是否需要角色调整"""
        if agent_id not in self.performance_metrics:
            return
        
        current_role = self.agent_roles[agent_id]
        performance_data = self.performance_metrics[agent_id]
        
        # 检查性能阈值
        for metric, threshold in current_role.performance_thresholds.items():
            if metric in performance_data:
                actual_value = performance_data[metric]
                
                if "min" in metric and actual_value < threshold:
                    self.logger.info(f"Agent {agent_id} performance below threshold for {metric}")
                    await self.assess_role_suitability(agent_id)
                    return
                elif "max" in metric and actual_value > threshold:
                    self.logger.info(f"Agent {agent_id} performance above threshold for {metric}")
                    await self.assess_role_suitability(agent_id)
                    return

    def get_agent_role(self, agent_id: str) -> Optional[RoleProfile]:
        """获取智能体角色"""
        return self.agent_roles.get(agent_id)

    def get_specialization_statistics(self) -> Dict[str, Any]:
        """获取特化统计信息"""
        role_distribution = defaultdict(int)
        for role_profile in self.agent_roles.values():
            role_distribution[role_profile.role_type.value] += 1
        
        total_specializations = len(self.specialization_history)
        successful_specializations = len([h for h in self.specialization_history 
                                        if h["result"]["success"]])
        
        return {
            "total_agents": len(self.agent_roles),
            "role_distribution": dict(role_distribution),
            "total_specializations": total_specializations,
            "success_rate": successful_specializations / total_specializations if total_specializations > 0 else 0,
            "average_adaptation_time": np.mean([h["result"]["adaptation_duration"] 
                                              for h in self.specialization_history]) if self.specialization_history else 0
        }

    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up RoleSpecializer...")
        
        # 保存特化历史到记忆系统
        for history in self.specialization_history:
            await self.episodic_memory.record_specialization_history(history)
        
        self.logger.info("RoleSpecializer cleanup completed")

