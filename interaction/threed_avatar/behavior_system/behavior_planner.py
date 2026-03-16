"""
行为规划器：规划角色行为序列
负责3D虚拟猫咪的行为序列规划、执行监控和动态调整
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import random

# 导入依赖模块
from cognitive.reasoning.task_decomposer import TaskDecomposer, TaskDecomposition, Subtask
from cognitive.learning.pattern_recognizer import PatternRecognizer

class BehaviorType(Enum):
    """行为类型枚举"""
    IDLE = "idle"  # 空闲行为
    SOCIAL = "social"  # 社交行为
    EXPLORATORY = "exploratory"  # 探索行为
    PLAYFUL = "playful"  # 玩耍行为
    LEARNING = "learning"  # 学习行为
    EMOTIONAL = "emotional"  # 情感表达
    FUNCTIONAL = "functional"  # 功能行为

class BehaviorPriority(Enum):
    """行为优先级枚举"""
    CRITICAL = 4  # 关键行为（紧急情况）
    HIGH = 3  # 高优先级（重要任务）
    MEDIUM = 2  # 中优先级（常规行为）
    LOW = 1  # 低优先级（背景行为）

@dataclass
class BehaviorAction:
    """行为动作"""
    action_id: str
    behavior_type: BehaviorType
    description: str
    duration: float  # 预计持续时间
    priority: BehaviorPriority
    prerequisites: List[str]  # 前置条件
    effects: Dict[str, Any]  # 行为效果
    success_probability: float  # 成功概率
    emotional_impact: Dict[str, float]  # 情感影响

@dataclass
class BehaviorPlan:
    """行为计划"""
    plan_id: str
    goal: str
    actions: List[BehaviorAction]
    expected_duration: float
    success_probability: float
    emotional_trajectory: List[Dict[str, float]]  # 情感轨迹预测

class BehaviorPlanner:
    """行为规划器：规划角色行为序列"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 核心组件
        self.task_decomposer = TaskDecomposer()
        self.pattern_recognizer = PatternRecognizer()
        
        # 行为库
        self.behavior_library: Dict[str, BehaviorAction] = {}
        self.behavior_patterns: Dict[str, List[BehaviorAction]] = {}
        
        # 当前计划状态
        self.current_plan: Optional[BehaviorPlan] = None
        self.current_action_index: int = 0
        self.plan_start_time: float = 0.0
        self.plan_execution_history: List[Dict[str, Any]] = []
        
        # 行为上下文
        self.behavior_context: Dict[str, Any] = {
            "emotional_state": "neutral",
            "energy_level": 0.8,
            "social_context": "alone",
            "environment_familiarity": 0.5,
            "time_of_day": "day"
        }
        
        # 规划参数
        self.planning_horizon = 10.0  # 规划视野（秒）
        self.replanning_threshold = 0.3  # 重新规划阈值
        self.adaptation_rate = 0.1  # 适应速率
        
        # 初始化行为库
        self._initialize_behavior_library()
        
        self.logger.info("行为规划器初始化完成")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("BehaviorPlanner")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_behavior_library(self):
        """初始化行为库"""
        # 空闲行为
        self.behavior_library["idle_relax"] = BehaviorAction(
            action_id="idle_relax",
            behavior_type=BehaviorType.IDLE,
            description="放松休息",
            duration=5.0,
            priority=BehaviorPriority.LOW,
            prerequisites=[],
            effects={"energy_change": 0.1, "emotional_change": 0.05},
            success_probability=1.0,
            emotional_impact={"valence": 0.1, "arousal": -0.2}
        )
        
        self.behavior_library["idle_stretch"] = BehaviorAction(
            action_id="idle_stretch",
            behavior_type=BehaviorType.IDLE,
            description="伸展身体",
            duration=2.0,
            priority=BehaviorPriority.LOW,
            prerequisites=[],
            effects={"energy_change": 0.05, "comfort_change": 0.1},
            success_probability=1.0,
            emotional_impact={"valence": 0.2, "arousal": 0.1}
        )
        
        # 社交行为
        self.behavior_library["social_greet"] = BehaviorAction(
            action_id="social_greet",
            behavior_type=BehaviorType.SOCIAL,
            description="问候用户",
            duration=3.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["user_present"],
            effects={"social_bond": 0.2, "emotional_change": 0.1},
            success_probability=0.9,
            emotional_impact={"valence": 0.3, "arousal": 0.2}
        )
        
        self.behavior_library["social_seek_attention"] = BehaviorAction(
            action_id="social_seek_attention",
            behavior_type=BehaviorType.SOCIAL,
            description="寻求关注",
            duration=4.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["user_present", "energy_level > 0.5"],
            effects={"attention_received": 0.3, "emotional_change": 0.15},
            success_probability=0.8,
            emotional_impact={"valence": 0.4, "arousal": 0.3}
        )
        
        # 探索行为
        self.behavior_library["explore_environment"] = BehaviorAction(
            action_id="explore_environment",
            behavior_type=BehaviorType.EXPLORATORY,
            description="探索环境",
            duration=8.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["environment_unfamiliar"],
            effects={"knowledge_gain": 0.3, "curiosity_satisfaction": 0.4},
            success_probability=0.7,
            emotional_impact={"valence": 0.2, "arousal": 0.4}
        )
        
        self.behavior_library["explore_object"] = BehaviorAction(
            action_id="explore_object",
            behavior_type=BehaviorType.EXPLORATORY,
            description="探索物体",
            duration=5.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["novel_object_present"],
            effects={"object_knowledge": 0.4, "curiosity_satisfaction": 0.3},
            success_probability=0.6,
            emotional_impact={"valence": 0.3, "arousal": 0.5}
        )
        
        # 玩耍行为
        self.behavior_library["play_chase_tail"] = BehaviorAction(
            action_id="play_chase_tail",
            behavior_type=BehaviorType.PLAYFUL,
            description="追尾巴玩耍",
            duration=6.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["energy_level > 0.6"],
            effects={"energy_change": -0.3, "enjoyment": 0.5},
            success_probability=0.8,
            emotional_impact={"valence": 0.6, "arousal": 0.7}
        )
        
        self.behavior_library["play_with_toy"] = BehaviorAction(
            action_id="play_with_toy",
            behavior_type=BehaviorType.PLAYFUL,
            description="玩玩具",
            duration=7.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["toy_available", "energy_level > 0.5"],
            effects={"energy_change": -0.4, "enjoyment": 0.6},
            success_probability=0.7,
            emotional_impact={"valence": 0.7, "arousal": 0.6}
        )
        
        # 学习行为
        self.behavior_library["learn_observation"] = BehaviorAction(
            action_id="learn_observation",
            behavior_type=BehaviorType.LEARNING,
            description="观察学习",
            duration=10.0,
            priority=BehaviorPriority.HIGH,
            prerequisites=["learning_opportunity"],
            effects={"knowledge_gain": 0.5, "skill_improvement": 0.3},
            success_probability=0.6,
            emotional_impact={"valence": 0.1, "arousal": 0.3}
        )
        
        self.behavior_library["learn_practice"] = BehaviorAction(
            action_id="learn_practice",
            behavior_type=BehaviorType.LEARNING,
            description="练习技能",
            duration=8.0,
            priority=BehaviorPriority.HIGH,
            prerequisites=["skill_to_practice"],
            effects={"skill_improvement": 0.4, "confidence_gain": 0.3},
            success_probability=0.5,
            emotional_impact={"valence": 0.2, "arousal": 0.4}
        )
        
        # 情感表达行为
        self.behavior_library["express_affection"] = BehaviorAction(
            action_id="express_affection",
            behavior_type=BehaviorType.EMOTIONAL,
            description="表达亲昵",
            duration=4.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["user_present", "emotional_bond > 0.3"],
            effects={"emotional_bond": 0.2, "emotional_expression": 0.4},
            success_probability=0.9,
            emotional_impact={"valence": 0.5, "arousal": 0.3}
        )
        
        self.behavior_library["express_curiosity"] = BehaviorAction(
            action_id="express_curiosity",
            behavior_type=BehaviorType.EMOTIONAL,
            description="表达好奇",
            duration=3.0,
            priority=BehaviorPriority.MEDIUM,
            prerequisites=["novel_stimulus"],
            effects={"curiosity_expression": 0.5, "attention_drawn": 0.3},
            success_probability=0.8,
            emotional_impact={"valence": 0.4, "arousal": 0.6}
        )
    
    async def create_behavior_plan(self, goal: str, context: Dict[str, Any] = None) -> Optional[BehaviorPlan]:
        """
        创建行为计划
        
        Args:
            goal: 行为目标
            context: 上下文信息
            
        Returns:
            行为计划，如果创建失败则返回None
        """
        try:
            self.logger.info(f"开始创建行为计划，目标: {goal}")
            
            # 更新上下文
            if context:
                self.behavior_context.update(context)
            
            # 使用任务分解器分解目标
            task_decomposition = self.task_decomposer.decompose_task(goal, self.behavior_context)
            
            if not task_decomposition.subtasks:
                self.logger.warning("任务分解失败，无法创建行为计划")
                return None
            
            # 将子任务映射到行为动作
            behavior_actions = await self._map_subtasks_to_actions(task_decomposition.subtasks)
            
            if not behavior_actions:
                self.logger.warning("无法找到合适的行为动作")
                return None
            
            # 创建行为计划
            plan_id = f"plan_{int(time.time())}"
            expected_duration = sum(action.duration for action in behavior_actions)
            success_probability = np.mean([action.success_probability for action in behavior_actions])
            
            # 预测情感轨迹
            emotional_trajectory = self._predict_emotional_trajectory(behavior_actions)
            
            plan = BehaviorPlan(
                plan_id=plan_id,
                goal=goal,
                actions=behavior_actions,
                expected_duration=expected_duration,
                success_probability=success_probability,
                emotional_trajectory=emotional_trajectory
            )
            
            self.logger.info(f"行为计划创建成功: {plan_id}，包含 {len(behavior_actions)} 个动作")
            return plan
            
        except Exception as e:
            self.logger.error(f"创建行为计划失败: {e}")
            return None
    
    async def _map_subtasks_to_actions(self, subtasks: List[Subtask]) -> List[BehaviorAction]:
        """将子任务映射到行为动作"""
        behavior_actions = []
        
        for subtask in subtasks:
            # 根据子任务类型和上下文选择合适的行为动作
            suitable_actions = self._find_suitable_actions(subtask, self.behavior_context)
            
            if suitable_actions:
                # 选择最合适的行为动作
                selected_action = self._select_best_action(suitable_actions, subtask.priority)
                behavior_actions.append(selected_action)
            else:
                self.logger.warning(f"没有找到适合子任务的行为动作: {subtask.name}")
        
        return behavior_actions
    
    def _find_suitable_actions(self, subtask: Subtask, context: Dict[str, Any]) -> List[BehaviorAction]:
        """查找适合的行为动作"""
        suitable_actions = []
        
        for action_id, action in self.behavior_library.items():
            # 检查行为类型匹配
            if not self._matches_behavior_type(action, subtask.task_type):
                continue
            
            # 检查前置条件
            if not self._satisfies_prerequisites(action, context):
                continue
            
            # 检查上下文适宜性
            if not self._is_context_appropriate(action, context):
                continue
            
            suitable_actions.append(action)
        
        return suitable_actions
    
    def _matches_behavior_type(self, action: BehaviorAction, task_type: Any) -> bool:
        """检查行为类型匹配"""
        # 简化的类型匹配逻辑
        type_mapping = {
            "creative": [BehaviorType.PLAYFUL, BehaviorType.EXPLORATORY],
            "technical": [BehaviorType.LEARNING, BehaviorType.FUNCTIONAL],
            "research": [BehaviorType.EXPLORATORY, BehaviorType.LEARNING],
            "automation": [BehaviorType.FUNCTIONAL],
            "analysis": [BehaviorType.LEARNING],
            "generation": [BehaviorType.PLAYFUL, BehaviorType.CREATIVE]
        }
        
        # 获取任务类型字符串表示
        task_type_str = str(task_type).lower()
        
        for key, behavior_types in type_mapping.items():
            if key in task_type_str and action.behavior_type in behavior_types:
                return True
        
        return False
    
    def _satisfies_prerequisites(self, action: BehaviorAction, context: Dict[str, Any]) -> bool:
        """检查前置条件满足"""
        for prerequisite in action.prerequisites:
            if not self._evaluate_prerequisite(prerequisite, context):
                return False
        return True
    
    def _evaluate_prerequisite(self, prerequisite: str, context: Dict[str, Any]) -> bool:
        """评估前置条件"""
        # 简单的前置条件评估
        if prerequisite == "user_present":
            return context.get("user_present", False)
        elif prerequisite == "energy_level > 0.5":
            return context.get("energy_level", 0.0) > 0.5
        elif prerequisite == "environment_unfamiliar":
            return context.get("environment_familiarity", 1.0) < 0.7
        elif prerequisite == "novel_object_present":
            return context.get("novel_objects", 0) > 0
        elif prerequisite == "toy_available":
            return context.get("toys_available", False)
        elif prerequisite == "learning_opportunity":
            return context.get("learning_opportunities", 0) > 0
        elif prerequisite == "skill_to_practice":
            return context.get("skills_to_practice", [])
        elif prerequisite == "emotional_bond > 0.3":
            return context.get("emotional_bond", 0.0) > 0.3
        elif prerequisite == "novel_stimulus":
            return context.get("novel_stimuli", 0) > 0
        
        return True  # 未知条件默认满足
    
    def _is_context_appropriate(self, action: BehaviorAction, context: Dict[str, Any]) -> bool:
        """检查上下文适宜性"""
        # 基于情感状态的适宜性检查
        emotional_state = context.get("emotional_state", "neutral")
        
        # 不同情感状态下适宜的行为类型
        appropriate_behaviors = {
            "happy": [BehaviorType.PLAYFUL, BehaviorType.SOCIAL, BehaviorType.EXPLORATORY],
            "sad": [BehaviorType.EMOTIONAL, BehaviorType.IDLE],
            "angry": [BehaviorType.EMOTIONAL, BehaviorType.FUNCTIONAL],
            "fearful": [BehaviorType.IDLE, BehaviorType.EMOTIONAL],
            "surprised": [BehaviorType.EXPLORATORY, BehaviorType.EMOTIONAL],
            "neutral": [BehaviorType.LEARNING, BehaviorType.FUNCTIONAL, BehaviorType.IDLE]
        }
        
        if emotional_state in appropriate_behaviors:
            return action.behavior_type in appropriate_behaviors[emotional_state]
        
        return True
    
    def _select_best_action(self, suitable_actions: List[BehaviorAction], priority: int) -> BehaviorAction:
        """选择最佳行为动作"""
        if not suitable_actions:
            return None
        
        # 根据优先级和成功概率评分
        scored_actions = []
        for action in suitable_actions:
            score = self._calculate_action_score(action, priority)
            scored_actions.append((action, score))
        
        # 选择分数最高的动作
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        return scored_actions[0][0]
    
    def _calculate_action_score(self, action: BehaviorAction, task_priority: int) -> float:
        """计算行为动作分数"""
        # 基础分数基于成功概率
        base_score = action.success_probability
        
        # 优先级匹配加分
        priority_match = 1.0 - abs(action.priority.value - task_priority) / 10.0
        
        # 能量效率考虑
        energy_efficiency = 1.0 - abs(action.effects.get("energy_change", 0))
        
        # 情感收益考虑
        emotional_benefit = abs(action.emotional_impact.get("valence", 0))
        
        # 综合分数
        total_score = (
            base_score * 0.4 +
            priority_match * 0.3 +
            energy_efficiency * 0.2 +
            emotional_benefit * 0.1
        )
        
        return total_score
    
    def _predict_emotional_trajectory(self, actions: List[BehaviorAction]) -> List[Dict[str, float]]:
        """预测情感轨迹"""
        trajectory = []
        current_valence = 0.0
        current_arousal = 0.0
        
        for action in actions:
            # 应用情感影响
            current_valence += action.emotional_impact.get("valence", 0)
            current_arousal += action.emotional_impact.get("arousal", 0)
            
            # 限制情感值范围
            current_valence = max(-1.0, min(1.0, current_valence))
            current_arousal = max(0.0, min(1.0, current_arousal))
            
            trajectory.append({
                "valence": current_valence,
                "arousal": current_arousal,
                "action_id": action.action_id
            })
        
        return trajectory
    
    async def execute_plan(self, plan: BehaviorPlan) -> bool:
        """
        执行行为计划
        
        Args:
            plan: 行为计划
            
        Returns:
            是否开始执行
        """
        try:
            self.current_plan = plan
            self.current_action_index = 0
            self.plan_start_time = time.time()
            
            # 记录执行开始
            execution_record = {
                "plan_id": plan.plan_id,
                "start_time": self.plan_start_time,
                "goal": plan.goal,
                "total_actions": len(plan.actions),
                "actions_executed": []
            }
            self.plan_execution_history.append(execution_record)
            
            self.logger.info(f"开始执行行为计划: {plan.plan_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"开始执行行为计划失败: {e}")
            return False
    
    async def get_next_action(self) -> Optional[BehaviorAction]:
        """
        获取下一个要执行的行为动作
        
        Returns:
            下一个行为动作，如果计划完成则返回None
        """
        if not self.current_plan or self.current_action_index >= len(self.current_plan.actions):
            return None
        
        next_action = self.current_plan.actions[self.current_action_index]
        return next_action
    
    async def complete_current_action(self, success: bool = True, actual_duration: float = None):
        """
        完成当前行为动作
        
        Args:
            success: 是否成功完成
            actual_duration: 实际持续时间
        """
        if not self.current_plan or self.current_action_index >= len(self.current_plan.actions):
            return
        
        current_action = self.current_plan.actions[self.current_action_index]
        
        # 记录执行结果
        execution_record = self.plan_execution_history[-1]
        action_record = {
            "action_id": current_action.action_id,
            "planned_duration": current_action.duration,
            "actual_duration": actual_duration or current_action.duration,
            "success": success,
            "completion_time": time.time()
        }
        execution_record["actions_executed"].append(action_record)
        
        # 更新上下文基于行为效果
        if success:
            await self._update_context_from_action(current_action)
        
        # 移动到下一个动作
        self.current_action_index += 1
        
        self.logger.info(f"行为动作完成: {current_action.action_id} (成功: {success})")
    
    async def _update_context_from_action(self, action: BehaviorAction):
        """根据行为效果更新上下文"""
        # 更新能量水平
        energy_change = action.effects.get("energy_change", 0)
        self.behavior_context["energy_level"] = max(0.0, min(1.0, 
            self.behavior_context.get("energy_level", 0.8) + energy_change))
        
        # 更新情感状态（简化实现）
        emotional_change = action.effects.get("emotional_change", 0)
        # 实际实现应该更复杂的情感状态更新
    
    async def should_replan(self) -> bool:
        """
        检查是否需要重新规划
        
        Returns:
            是否需要重新规划
        """
        if not self.current_plan:
            return True
        
        # 检查计划执行进度
        current_progress = self.current_action_index / len(self.current_plan.actions)
        elapsed_time = time.time() - self.plan_start_time
        expected_progress = elapsed_time / self.current_plan.expected_duration
        
        # 如果实际进度严重偏离预期，考虑重新规划
        progress_deviation = abs(current_progress - expected_progress)
        
        if progress_deviation > self.replanning_threshold:
            self.logger.info(f"进度偏差过大 ({progress_deviation:.2f})，需要重新规划")
            return True
        
        # 检查上下文变化
        context_changed = await self._check_context_changes()
        if context_changed:
            self.logger.info("上下文发生重大变化，需要重新规划")
            return True
        
        return False
    
    async def _check_context_changes(self) -> bool:
        """检查上下文变化"""
        # 简化的上下文变化检查
        # 实际实现应该更复杂的上下文监控
        
        # 检查能量水平是否过低
        if self.behavior_context.get("energy_level", 0.8) < 0.2:
            return True
        
        # 检查用户状态变化
        user_present = self.behavior_context.get("user_present", False)
        # 如果用户出现或消失，可能需要重新规划
        
        return False
    
    async def adapt_plan(self) -> Optional[BehaviorPlan]:
        """
        适应性地调整当前计划
        
        Returns:
            调整后的行为计划，如果无法调整则返回None
        """
        if not self.current_plan:
            return None
        
        try:
            # 获取剩余目标
            remaining_goal = f"继续完成: {self.current_plan.goal}"
            
            # 获取当前上下文
            current_context = self.behavior_context.copy()
            
            # 考虑已执行动作的影响
            if self.plan_execution_history:
                last_execution = self.plan_execution_history[-1]
                executed_actions = last_execution.get("actions_executed", [])
                
                # 更新上下文基于已执行动作
                for action_record in executed_actions:
                    action_id = action_record["action_id"]
                    if action_id in self.behavior_library:
                        action = self.behavior_library[action_id]
                        if action_record["success"]:
                            await self._update_context_from_action(action)
            
            # 创建新的计划
            new_plan = await self.create_behavior_plan(remaining_goal, current_context)
            
            if new_plan:
                self.logger.info("行为计划适应调整完成")
            else:
                self.logger.warning("行为计划适应调整失败")
            
            return new_plan
            
        except Exception as e:
            self.logger.error(f"行为计划适应调整失败: {e}")
            return None
    
    def get_current_plan_status(self) -> Dict[str, Any]:
        """获取当前计划状态"""
        if not self.current_plan:
            return {"status": "no_active_plan"}
        
        current_progress = self.current_action_index / len(self.current_plan.actions)
        elapsed_time = time.time() - self.plan_start_time
        
        return {
            "plan_id": self.current_plan.plan_id,
            "goal": self.current_plan.goal,
            "total_actions": len(self.current_plan.actions),
            "current_action_index": self.current_action_index,
            "progress": current_progress,
            "elapsed_time": elapsed_time,
            "expected_remaining_time": self.current_plan.expected_duration * (1 - current_progress),
            "status": "executing" if self.current_action_index < len(self.current_plan.actions) else "completed"
        }
    
    def get_planning_statistics(self) -> Dict[str, Any]:
        """获取规划统计信息"""
        total_plans = len(self.plan_execution_history)
        
        if total_plans == 0:
            return {"total_plans": 0}
        
        # 计算成功率
        successful_plans = 0
        total_actions = 0
        successful_actions = 0
        
        for execution in self.plan_execution_history:
            actions_executed = execution.get("actions_executed", [])
            total_actions += len(actions_executed)
            successful_actions += sum(1 for action in actions_executed if action.get("success", False))
            
            if actions_executed and all(action.get("success", False) for action in actions_executed):
                successful_plans += 1
        
        plan_success_rate = successful_plans / total_plans if total_plans > 0 else 0.0
        action_success_rate = successful_actions / total_actions if total_actions > 0 else 0.0
        
        return {
            "total_plans": total_plans,
            "plan_success_rate": plan_success_rate,
            "action_success_rate": action_success_rate,
            "average_plan_duration": np.mean([
                exec_data.get("actions_executed", [])[-1]["completion_time"] - exec_data["start_time"]
                for exec_data in self.plan_execution_history
                if exec_data.get("actions_executed")
            ]) if self.plan_execution_history else 0.0,
            "replanning_count": sum(1 for exec_data in self.plan_execution_history 
                                  if len(exec_data.get("actions_executed", [])) < 
                                  exec_data.get("total_actions", 0))
        }

# 全局行为规划器实例
_global_behavior_planner: Optional[BehaviorPlanner] = None

def get_behavior_planner() -> BehaviorPlanner:
    """获取全局行为规划器实例"""
    global _global_behavior_planner
    if _global_behavior_planner is None:
        _global_behavior_planner = BehaviorPlanner()
    return _global_behavior_planner
