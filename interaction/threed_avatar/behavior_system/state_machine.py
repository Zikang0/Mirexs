"""
状态机：行为状态管理
负责3D虚拟猫咪行为状态的管理和状态转换
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

class BehaviorState(Enum):
    """行为状态枚举"""
    IDLE = "idle"  # 空闲状态
    SLEEPING = "sleeping"  # 睡眠状态
    PLAYING = "playing"  # 玩耍状态
    EXPLORING = "exploring"  # 探索状态
    LEARNING = "learning"  # 学习状态
    SOCIALIZING = "socializing"  # 社交状态
    EATING = "eating"  # 进食状态
    GROOMING = "grooming"  # 梳理状态
    ALERT = "alert"  # 警觉状态
    CURIOUS = "curious"  # 好奇状态
    AFFECTIONATE = "affectionate"  # 亲昵状态

class StatePriority(Enum):
    """状态优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class StateTransition:
    """状态转换定义"""
    from_state: BehaviorState
    to_state: BehaviorState
    condition: Callable[[Dict[str, Any]], bool]  # 转换条件函数
    priority: StatePriority
    description: str

@dataclass
class StateHistory:
    """状态历史记录"""
    state: BehaviorState
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    reason: str

class BehaviorStateMachine:
    """行为状态机：管理行为状态和状态转换"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = self._setup_logger()
        
        # 状态管理
        self.current_state = BehaviorState.IDLE
        self.previous_state: Optional[BehaviorState] = None
        self.state_start_time = time.time()
        
        # 状态历史
        self.state_history: List[StateHistory] = []
        self.max_history_size = 1000
        
        # 状态转换规则
        self.transitions: List[StateTransition] = []
        
        # 状态上下文
        self.state_context: Dict[str, Any] = {
            "energy_level": 0.8,
            "hunger_level": 0.3,
            "social_desire": 0.5,
            "curiosity_level": 0.6,
            "emotional_state": "neutral",
            "environment_stimuli": [],
            "user_interaction": False,
            "time_of_day": "day"
        }
        
        # 状态持续时间统计
        self.state_duration_stats: Dict[BehaviorState, List[float]] = {}
        
        # 初始化状态机
        self._initialize_state_machine()
        
        self.logger.info(f"行为状态机初始化完成，初始状态: {self.current_state.value}")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("BehaviorStateMachine")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_state_machine(self):
        """初始化状态机"""
        # 初始化状态持续时间统计
        for state in BehaviorState:
            self.state_duration_stats[state] = []
        
        # 定义状态转换规则
        self._define_state_transitions()
    
    def _define_state_transitions(self):
        """定义状态转换规则"""
        # 从空闲状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.IDLE,
            to_state=BehaviorState.SLEEPING,
            condition=lambda ctx: ctx["energy_level"] < 0.2 and ctx["time_of_day"] == "night",
            priority=StatePriority.HIGH,
            description="能量低且夜晚时进入睡眠"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.IDLE,
            to_state=BehaviorState.PLAYING,
            condition=lambda ctx: ctx["energy_level"] > 0.6 and ctx.get("toys_available", False),
            priority=StatePriority.MEDIUM,
            description="能量充足且有玩具时玩耍"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.IDLE,
            to_state=BehaviorState.EXPLORING,
            condition=lambda ctx: ctx["curiosity_level"] > 0.7 and len(ctx["environment_stimuli"]) > 0,
            priority=StatePriority.MEDIUM,
            description="好奇心强且有环境刺激时探索"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.IDLE,
            to_state=BehaviorState.SOCIALIZING,
            condition=lambda ctx: ctx["user_interaction"] and ctx["social_desire"] > 0.5,
            priority=StatePriority.HIGH,
            description="用户交互且社交需求高时社交"
        ))
        
        # 从睡眠状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.SLEEPING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["energy_level"] > 0.8 or ctx["time_of_day"] == "day",
            priority=StatePriority.MEDIUM,
            description="能量充足或白天时醒来"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.SLEEPING,
            to_state=BehaviorState.ALERT,
            condition=lambda ctx: len(ctx.get("loud_noises", [])) > 0,
            priority=StatePriority.CRITICAL,
            description="有巨大噪音时惊醒"
        ))
        
        # 从玩耍状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.PLAYING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["energy_level"] < 0.3,
            priority=StatePriority.MEDIUM,
            description="能量低时停止玩耍"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.PLAYING,
            to_state=BehaviorState.EATING,
            condition=lambda ctx: ctx["hunger_level"] > 0.7,
            priority=StatePriority.HIGH,
            description="饥饿时进食"
        ))
        
        # 从探索状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.EXPLORING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["curiosity_level"] < 0.3 or len(ctx["environment_stimuli"]) == 0,
            priority=StatePriority.MEDIUM,
            description="好奇心降低或无刺激时停止探索"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.EXPLORING,
            to_state=BehaviorState.CURIOUS,
            condition=lambda ctx: ctx.get("novel_object_detected", False),
            priority=StatePriority.HIGH,
            description="发现新物体时进入好奇状态"
        ))
        
        # 从社交状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.SOCIALIZING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: not ctx["user_interaction"] or ctx["social_desire"] < 0.3,
            priority=StatePriority.MEDIUM,
            description="用户离开或社交需求降低时停止社交"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.SOCIALIZING,
            to_state=BehaviorState.AFFECTIONATE,
            condition=lambda ctx: ctx["emotional_state"] == "happy" and ctx.get("petting_received", False),
            priority=StatePriority.MEDIUM,
            description="心情好且被抚摸时表现亲昵"
        ))
        
        # 从警觉状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.ALERT,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: len(ctx.get("threats_detected", [])) == 0 and time.time() - self.state_start_time > 10,
            priority=StatePriority.MEDIUM,
            description="无威胁且一段时间后恢复空闲"
        ))
        
        # 从好奇状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.CURIOUS,
            to_state=BehaviorState.EXPLORING,
            condition=lambda ctx: ctx["curiosity_level"] > 0.5,
            priority=StatePriority.MEDIUM,
            description="保持好奇心时继续探索"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.CURIOUS,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["curiosity_level"] < 0.2,
            priority=StatePriority.MEDIUM,
            description="好奇心降低时恢复空闲"
        ))
        
        # 从亲昵状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.AFFECTIONATE,
            to_state=BehaviorState.SOCIALIZING,
            condition=lambda ctx: ctx["user_interaction"],
            priority=StatePriority.MEDIUM,
            description="保持用户交互时继续社交"
        ))
        
        self.transitions.append(StateTransition(
            from_state=BehaviorState.AFFECTIONATE,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: not ctx["user_interaction"],
            priority=StatePriority.MEDIUM,
            description="用户离开时恢复空闲"
        ))
        
        # 从学习状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.LEARNING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["energy_level"] < 0.4 or ctx.get("learning_complete", False),
            priority=StatePriority.MEDIUM,
            description="能量低或学习完成时停止学习"
        ))
        
        # 从进食状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.EATING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx["hunger_level"] < 0.2,
            priority=StatePriority.MEDIUM,
            description="饥饿感降低时停止进食"
        ))
        
        # 从梳理状态的转换
        self.transitions.append(StateTransition(
            from_state=BehaviorState.GROOMING,
            to_state=BehaviorState.IDLE,
            condition=lambda ctx: ctx.get("grooming_complete", False) or ctx["energy_level"] < 0.3,
            priority=StatePriority.MEDIUM,
            description="梳理完成或能量低时停止梳理"
        ))
    
    def update_context(self, context_updates: Dict[str, Any]):
        """
        更新状态上下文
        
        Args:
            context_updates: 上下文更新数据
        """
        self.state_context.update(context_updates)
        self.logger.debug(f"状态上下文已更新: {list(context_updates.keys())}")
    
    async def evaluate_state_transitions(self) -> Optional[BehaviorState]:
        """
        评估状态转换
        
        Returns:
            建议的新状态，如果不需要转换则返回None
        """
        # 获取适用于当前状态的转换规则
        applicable_transitions = [
            transition for transition in self.transitions
            if transition.from_state == self.current_state
        ]
        
        if not applicable_transitions:
            return None
        
        # 评估所有适用的转换条件
        triggered_transitions = []
        for transition in applicable_transitions:
            try:
                if transition.condition(self.state_context):
                    triggered_transitions.append(transition)
            except Exception as e:
                self.logger.warning(f"评估状态转换条件失败: {e}")
                continue
        
        if not triggered_transitions:
            return None
        
        # 按优先级排序触发的转换
        triggered_transitions.sort(key=lambda t: t.priority.value, reverse=True)
        
        # 选择最高优先级的转换
        selected_transition = triggered_transitions[0]
        
        self.logger.info(f"状态转换触发: {self.current_state.value} -> {selected_transition.to_state.value}")
        self.logger.info(f"转换原因: {selected_transition.description}")
        
        return selected_transition.to_state
    
    async def transition_to_state(self, new_state: BehaviorState, reason: str = "自动转换"):
        """
        转换到新状态
        
        Args:
            new_state: 新状态
            reason: 转换原因
        """
        if new_state == self.current_state:
            return
        
        # 记录当前状态的结束
        current_duration = time.time() - self.state_start_time
        if self.state_history:
            self.state_history[-1].end_time = time.time()
            self.state_history[-1].duration = current_duration
        
        # 更新状态持续时间统计
        self.state_duration_stats[self.current_state].append(current_duration)
        
        # 保存先前状态
        self.previous_state = self.current_state
        
        # 更新当前状态
        self.current_state = new_state
        self.state_start_time = time.time()
        
        # 记录新状态开始
        new_history = StateHistory(
            state=new_state,
            start_time=self.state_start_time,
            end_time=None,
            duration=None,
            reason=reason
        )
        self.state_history.append(new_history)
        
        # 限制历史记录大小
        if len(self.state_history) > self.max_history_size:
            self.state_history = self.state_history[-self.max_history_size:]
        
        self.logger.info(f"状态转换完成: {self.previous_state.value} -> {new_state.value} ({reason})")
    
    async def force_state(self, new_state: BehaviorState, reason: str = "强制转换"):
        """
        强制转换到指定状态
        
        Args:
            new_state: 新状态
            reason: 转换原因
        """
        await self.transition_to_state(new_state, reason)
    
    def get_current_state_info(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        current_duration = time.time() - self.state_start_time
        
        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "state_duration": current_duration,
            "state_start_time": self.state_start_time,
            "context_snapshot": self.state_context.copy()
        }
    
    def get_state_statistics(self, state: Optional[BehaviorState] = None) -> Dict[str, Any]:
        """
        获取状态统计信息
        
        Args:
            state: 特定状态，如果为None则返回所有状态统计
            
        Returns:
            状态统计信息
        """
        if state:
            # 返回特定状态的统计
            durations = self.state_duration_stats.get(state, [])
            if not durations:
                return {
                    "state": state.value,
                    "total_occurrences": 0,
                    "average_duration": 0.0,
                    "total_duration": 0.0
                }
            
            return {
                "state": state.value,
                "total_occurrences": len(durations),
                "average_duration": sum(durations) / len(durations),
                "total_duration": sum(durations),
                "min_duration": min(durations),
                "max_duration": max(durations)
            }
        else:
            # 返回所有状态的统计
            all_stats = {}
            total_duration_all_states = 0.0
            
            for state_enum in BehaviorState:
                durations = self.state_duration_stats.get(state_enum, [])
                total_duration = sum(durations)
                total_duration_all_states += total_duration
                
                all_stats[state_enum.value] = {
                    "total_occurrences": len(durations),
                    "average_duration": total_duration / len(durations) if durations else 0.0,
                    "total_duration": total_duration,
                    "percentage": (total_duration / total_duration_all_states * 100) if total_duration_all_states > 0 else 0.0
                }
            
            return all_stats
    
    def get_recent_state_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的状态历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            状态历史记录
        """
        recent_history = self.state_history[-limit:] if self.state_history else []
        
        formatted_history = []
        for history in recent_history:
            formatted_history.append({
                "state": history.state.value,
                "start_time": history.start_time,
                "end_time": history.end_time,
                "duration": history.duration,
                "reason": history.reason
            })
        
        return formatted_history
    
    def get_state_patterns(self) -> Dict[str, Any]:
        """获取状态模式分析"""
        if len(self.state_history) < 10:
            return {"analysis": "insufficient_data"}
        
        # 分析状态序列模式
        state_sequences = []
        current_sequence = []
        
        for history in self.state_history:
            if not current_sequence or history.state == current_sequence[-1]:
                current_sequence.append(history.state)
            else:
                if len(current_sequence) > 1:
                    state_sequences.append(current_sequence)
                current_sequence = [history.state]
        
        # 分析常见状态转换
        transition_counts = {}
        for i in range(len(self.state_history) - 1):
            from_state = self.state_history[i].state
            to_state = self.state_history[i + 1].state
            transition_key = f"{from_state.value}->{to_state.value}"
            transition_counts[transition_key] = transition_counts.get(transition_key, 0) + 1
        
        # 找出最常见的状态转换
        common_transitions = sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_state_changes": len(self.state_history),
            "common_transitions": common_transitions,
            "state_sequence_count": len(state_sequences),
            "average_sequence_length": sum(len(seq) for seq in state_sequences) / len(state_sequences) if state_sequences else 0
        }
    
    async def suggest_optimal_state(self) -> BehaviorState:
        """
        建议最优状态（基于当前上下文）
        
        Returns:
            建议的最优状态
        """
        # 基于上下文参数计算状态适宜性分数
        state_scores = {}
        
        for state in BehaviorState:
            score = self._calculate_state_suitability(state)
            state_scores[state] = score
        
        # 选择分数最高的状态
        optimal_state = max(state_scores.items(), key=lambda x: x[1])[0]
        
        # 如果当前状态已经是最优，或者分数差异不大，保持当前状态
        current_score = state_scores[self.current_state]
        optimal_score = state_scores[optimal_state]
        
        if optimal_state == self.current_state or (optimal_score - current_score) < 0.1:
            return self.current_state
        
        return optimal_state
    
    def _calculate_state_suitability(self, state: BehaviorState) -> float:
        """计算状态适宜性分数"""
        base_score = 0.5
        
        # 基于能量水平的适宜性
        energy_suitability = {
            BehaviorState.SLEEPING: 1.0 - self.state_context["energy_level"],  # 能量低时适合睡眠
            BehaviorState.PLAYING: self.state_context["energy_level"],  # 能量高时适合玩耍
            BehaviorState.EXPLORING: self.state_context["energy_level"] * 0.8,  # 探索需要中等能量
            BehaviorState.LEARNING: self.state_context["energy_level"] * 0.7,  # 学习需要中等能量
            BehaviorState.IDLE: 0.5  # 空闲状态总是适中
        }
        
        # 基于时间的适宜性
        time_suitability = {
            BehaviorState.SLEEPING: 1.0 if self.state_context["time_of_day"] == "night" else 0.2,
            BehaviorState.PLAYING: 0.8 if self.state_context["time_of_day"] == "day" else 0.3,
            BehaviorState.EXPLORING: 0.9 if self.state_context["time_of_day"] == "day" else 0.4
        }
        
        # 基于社交需求的适宜性
        social_suitability = {
            BehaviorState.SOCIALIZING: self.state_context["social_desire"],
            BehaviorState.AFFECTIONATE: self.state_context["social_desire"] * 0.8,
            BehaviorState.IDLE: 1.0 - self.state_context["social_desire"] * 0.5
        }
        
        # 计算综合分数
        score = base_score
        score += energy_suitability.get(state, 0.5) * 0.3
        score += time_suitability.get(state, 0.5) * 0.2
        score += social_suitability.get(state, 0.5) * 0.2
        score += self.state_context.get("curiosity_level", 0.5) * 0.1 if state == BehaviorState.EXPLORING else 0.0
        score += (1.0 - self.state_context.get("hunger_level", 0.3)) * 0.1 if state == BehaviorState.EATING else 0.0
        
        return min(1.0, max(0.0, score))
    
    def reset_statistics(self):
        """重置状态统计"""
        self.state_duration_stats.clear()
        for state in BehaviorState:
            self.state_duration_stats[state] = []
        
        self.state_history.clear()
        self.logger.info("状态统计已重置")

# 全局行为状态机实例
_global_state_machine: Optional[BehaviorStateMachine] = None

def get_state_machine() -> BehaviorStateMachine:
    """获取全局行为状态机实例"""
    global _global_state_machine
    if _global_state_machine is None:
        _global_state_machine = BehaviorStateMachine()
    return _global_state_machine

