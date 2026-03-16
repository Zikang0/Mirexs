"""
目标识别器 - 识别用户真实目标和潜在需求
深度理解用户意图和期望结果
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import jieba
from collections import Counter

logger = logging.getLogger(__name__)

class GoalType(Enum):
    """目标类型枚举"""
    INFORMATION_RETRIEVAL = "information_retrieval"  # 信息获取
    PROBLEM_SOLUTION = "problem_solution"  # 问题解决
    CREATION_GENERATION = "creation_generation"  # 创作生成
    AUTOMATION_EFFICIENCY = "automation_efficiency"  # 自动化效率
    LEARNING_EDUCATION = "learning_education"  # 学习教育
    ENTERTAINMENT_ENGAGEMENT = "entertainment_engagement"  # 娱乐互动

class GoalPriority(Enum):
    """目标优先级枚举"""
    CRITICAL = "critical"  # 关键
    HIGH = "high"  # 高
    MEDIUM = "medium"  # 中
    LOW = "low"  # 低

@dataclass
class RecognizedGoal:
    """识别到的目标"""
    goal_id: str
    description: str
    goal_type: GoalType
    priority: GoalPriority
    confidence: float  # 置信度 0-1
    explicit: bool  # 是否显式目标
    underlying_needs: List[str]  # 潜在需求
    success_criteria: List[str]  # 成功标准
    constraints: Dict[str, Any]  # 约束条件

@dataclass
class GoalRecognitionResult:
    """目标识别结果"""
    original_input: str
    primary_goal: RecognizedGoal
    secondary_goals: List[RecognizedGoal]
    goal_hierarchy: Dict[str, List[str]]  # 目标层次结构
    conflicting_goals: List[Tuple[str, str]]  # 冲突目标对

class GoalRecognizer:
    """目标识别器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.goal_patterns = self._load_goal_patterns()
        self.need_patterns = self._load_need_patterns()
        self.priority_indicators = self._load_priority_indicators()
        
        # 初始化NLP组件
        jieba.initialize()
        self._load_goal_vocabulary()
        
    def _load_goal_patterns(self) -> Dict[str, Any]:
        """加载目标模式"""
        return {
            "information_retrieval": {
                "patterns": [
                    r"(查|找|搜索|了解|知道).*(信息|资料|数据|内容)",
                    r".*(是什么|什么意思|如何定义)",
                    r"告诉我关于(.+)",
                    r"解释一下(.+)"
                ],
                "keywords": ["查询", "搜索", "了解", "知道", "解释", "定义"]
            },
            "problem_solution": {
                "patterns": [
                    r"(解决|处理|修复|调试).*(问题|错误|故障|bug)",
                    r".*(怎么办|怎么解决|如何修复)",
                    r"遇到(.+)问题",
                    r"无法(.+)"
                ],
                "keywords": ["解决", "处理", "修复", "调试", "问题", "错误"]
            },
            "creation_generation": {
                "patterns": [
                    r"(写|创作|生成|制作|设计).*(文章|代码|程序|图片|音乐)",
                    r"创建一个(.+)",
                    r"帮我写(.+)",
                    r"生成一个(.+)"
                ],
                "keywords": ["写", "创作", "生成", "制作", "设计", "创建"]
            },
            "automation_efficiency": {
                "patterns": [
                    r"(自动化|自动|批量).*(处理|执行|操作)",
                    r"提高(.+)效率",
                    r"优化(.+)流程",
                    r"减少(.+)时间"
                ],
                "keywords": ["自动化", "自动", "批量", "效率", "优化", "减少"]
            }
        }
    
    def _load_need_patterns(self) -> Dict[str, List[str]]:
        """加载需求模式"""
        return {
            "efficiency": ["更快", "更高效", "节省时间", "提高效率", "优化速度"],
            "quality": ["更好", "更优质", "提高质量", "提升水平", "完善"],
            "simplicity": ["更简单", "更容易", "简化", "便捷", "方便"],
            "reliability": ["更稳定", "更可靠", "安全", "保险", "放心"],
            "innovation": ["创新", "新颖", "独特", "突破", "革新"]
        }
    
    def _load_priority_indicators(self) -> Dict[str, List[str]]:
        """加载优先级指示器"""
        return {
            "critical": ["紧急", "立刻", "马上", "尽快", "重要", "必须", "务必"],
            "high": ["需要", "希望", "尽快", "优先", "重要"],
            "medium": ["可以", "适当", "一般", "普通"],
            "low": ["有空", "方便", "随意", "不着急"]
        }
    
    def _load_goal_vocabulary(self):
        """加载目标词汇"""
        goal_words = [
            '目标', '目的', '意图', '需求', '需要', '想要', '希望',
            '查询', '搜索', '了解', '知道', '解决', '处理', '修复',
            '创作', '生成', '制作', '设计', '自动化', '优化', '学习'
        ]
        
        for word in goal_words:
            jieba.add_word(word)
    
    def recognize_goals(self, user_input: str, context: Dict[str, Any] = None) -> GoalRecognitionResult:
        """
        识别用户目标
        
        Args:
            user_input: 用户输入
            context: 上下文信息
            
        Returns:
            GoalRecognitionResult: 目标识别结果
        """
        self.logger.info(f"开始识别用户目标: {user_input}")
        
        if context is None:
            context = {}
        
        # 1. 识别主要目标
        primary_goal = self._identify_primary_goal(user_input, context)
        
        # 2. 识别次要目标
        secondary_goals = self._identify_secondary_goals(user_input, context, primary_goal)
        
        # 3. 构建目标层次结构
        goal_hierarchy = self._build_goal_hierarchy(primary_goal, secondary_goals)
        
        # 4. 识别冲突目标
        conflicting_goals = self._identify_conflicting_goals(primary_goal, secondary_goals)
        
        result = GoalRecognitionResult(
            original_input=user_input,
            primary_goal=primary_goal,
            secondary_goals=secondary_goals,
            goal_hierarchy=goal_hierarchy,
            conflicting_goals=conflicting_goals
        )
        
        self.logger.info(f"目标识别完成，主要目标: {primary_goal.goal_type.value}")
        return result
    
    def _identify_primary_goal(self, user_input: str, context: Dict[str, Any]) -> RecognizedGoal:
        """识别主要目标"""
        input_lower = user_input.lower()
        
        # 计算每个目标类型的得分
        goal_scores = {}
        confidence_scores = {}
        
        for goal_type, pattern_info in self.goal_patterns.items():
            score = 0
            confidence = 0.0
            
            # 模式匹配
            for pattern in pattern_info["patterns"]:
                matches = re.findall(pattern, input_lower)
                if matches:
                    score += len(matches) * 2
                    confidence += 0.3
            
            # 关键词匹配
            for keyword in pattern_info["keywords"]:
                if keyword in input_lower:
                    score += 1
                    confidence += 0.1
            
            goal_scores[goal_type] = score
            confidence_scores[goal_type] = min(confidence, 1.0)
        
        # 选择得分最高的目标类型
        if goal_scores:
            primary_goal_type = max(goal_scores.items(), key=lambda x: x[1])[0]
            confidence = confidence_scores[primary_goal_type]
        else:
            primary_goal_type = "information_retrieval"
            confidence = 0.5
        
        # 确定优先级
        priority = self._determine_priority(user_input, context)
        
        # 识别潜在需求
        underlying_needs = self._identify_underlying_needs(user_input)
        
        # 定义成功标准
        success_criteria = self._define_success_criteria(primary_goal_type, user_input)
        
        # 识别约束条件
        constraints = self._identify_constraints(user_input, context)
        
        goal = RecognizedGoal(
            goal_id=f"goal_{hash(user_input)}",
            description=self._generate_goal_description(primary_goal_type, user_input),
            goal_type=GoalType(primary_goal_type),
            priority=priority,
            confidence=confidence,
            explicit=self._is_explicit_goal(user_input),
            underlying_needs=underlying_needs,
            success_criteria=success_criteria,
            constraints=constraints
        )
        
        return goal
    
    def _identify_secondary_goals(self, user_input: str, context: Dict[str, Any], 
                                primary_goal: RecognizedGoal) -> List[RecognizedGoal]:
        """识别次要目标"""
        secondary_goals = []
        
        # 基于用户输入识别相关但非主要的目标
        input_lower = user_input.lower()
        
        for goal_type, pattern_info in self.goal_patterns.items():
            if goal_type == primary_goal.goal_type.value:
                continue  # 跳过主要目标
            
            # 检查是否有该目标类型的迹象
            score = 0
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, input_lower):
                    score += 1
            
            for keyword in pattern_info["keywords"]:
                if keyword in input_lower:
                    score += 1
            
            # 如果得分足够高，认为是次要目标
            if score >= 1:
                confidence = min(score * 0.2, 0.8)  # 次要目标置信度较低
                
                goal = RecognizedGoal(
                    goal_id=f"secondary_{goal_type}_{hash(user_input)}",
                    description=f"相关的{goal_type}目标",
                    goal_type=GoalType(goal_type),
                    priority=GoalPriority.LOW,  # 次要目标优先级较低
                    confidence=confidence,
                    explicit=False,
                    underlying_needs=[],
                    success_criteria=[],
                    constraints={}
                )
                secondary_goals.append(goal)
        
        return secondary_goals
    
    def _determine_priority(self, user_input: str, context: Dict[str, Any]) -> GoalPriority:
        """确定目标优先级"""
        input_lower = user_input.lower()
        
        # 检查优先级指示词
        for priority_level, indicators in self.priority_indicators.items():
            for indicator in indicators:
                if indicator in input_lower:
                    return GoalPriority(priority_level)
        
        # 从上下文中推断优先级
        if context.get("urgent", False):
            return GoalPriority.HIGH
        
        # 默认优先级
        return GoalPriority.MEDIUM
    
    def _identify_underlying_needs(self, user_input: str) -> List[str]:
        """识别潜在需求"""
        needs = []
        input_lower = user_input.lower()
        
        for need_type, indicators in self.need_patterns.items():
            for indicator in indicators:
                if indicator in input_lower:
                    needs.append(need_type)
                    break
        
        return needs
    
    def _define_success_criteria(self, goal_type: str, user_input: str) -> List[str]:
        """定义成功标准"""
        criteria_map = {
            "information_retrieval": [
                "获取准确的信息",
                "信息全面且相关",
                "及时获得答案"
            ],
            "problem_solution": [
                "问题得到解决",
                "解决方案有效",
                "避免问题再次发生"
            ],
            "creation_generation": [
                "生成高质量内容",
                "内容符合要求",
                "按时完成创作"
            ],
            "automation_efficiency": [
                "实现自动化",
                "提高效率",
                "减少人工干预"
            ]
        }
        
        return criteria_map.get(goal_type, ["满足用户需求"])
    
    def _identify_constraints(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """识别约束条件"""
        constraints = {}
        input_lower = user_input.lower()
        
        # 时间约束
        time_patterns = [
            (r"在(.{1,10})内", "time_limit"),
            (r"截止到(.{1,10})", "deadline"),
            (r"在(.{1,10})之前", "before_time")
        ]
        
        for pattern, constraint_type in time_patterns:
            matches = re.findall(pattern, input_lower)
            if matches:
                constraints[constraint_type] = matches[0]
        
        # 资源约束
        if "简单" in input_lower or "快速" in input_lower:
            constraints["simplicity"] = True
        
        if "免费" in input_lower or "低成本" in input_lower:
            constraints["cost"] = "low"
        
        # 从上下文中获取约束
        if "constraints" in context:
            constraints.update(context["constraints"])
        
        return constraints
    
    def _generate_goal_description(self, goal_type: str, user_input: str) -> str:
        """生成目标描述"""
        descriptions = {
            "information_retrieval": f"获取关于'{user_input}'的信息",
            "problem_solution": f"解决'{user_input}'相关的问题",
            "creation_generation": f"创作或生成'{user_input}'相关的内容",
            "automation_efficiency": f"自动化'{user_input}'相关的流程",
            "learning_education": f"学习关于'{user_input}'的知识",
            "entertainment_engagement": f"进行'{user_input}'相关的娱乐互动"
        }
        
        return descriptions.get(goal_type, f"实现'{user_input}'相关的目标")
    
    def _is_explicit_goal(self, user_input: str) -> bool:
        """判断是否是显式目标"""
        explicit_indicators = ["我要", "我想", "我需要", "我希望", "帮我", "请"]
        return any(indicator in user_input for indicator in explicit_indicators)
    
    def _build_goal_hierarchy(self, primary_goal: RecognizedGoal, 
                            secondary_goals: List[RecognizedGoal]) -> Dict[str, List[str]]:
        """构建目标层次结构"""
        hierarchy = {
            "primary": [primary_goal.goal_id],
            "secondary": [goal.goal_id for goal in secondary_goals],
            "supporting": []  # 支持性目标
        }
        
        # 根据目标类型添加支持性目标
        if primary_goal.goal_type == GoalType.CREATION_GENERATION:
            hierarchy["supporting"].extend([
                "quality_assurance", "content_optimization", "formatting"
            ])
        elif primary_goal.goal_type == GoalType.PROBLEM_SOLUTION:
            hierarchy["supporting"].extend([
                "root_cause_analysis", "solution_evaluation", "prevention_planning"
            ])
        
        return hierarchy
    
    def _identify_conflicting_goals(self, primary_goal: RecognizedGoal, 
                                  secondary_goals: List[RecognizedGoal]) -> List[Tuple[str, str]]:
        """识别冲突目标"""
        conflicts = []
        
        # 定义目标冲突规则
        conflict_rules = [
            (GoalType.AUTOMATION_EFFICIENCY, GoalType.QUALITY_ASSURANCE),
            (GoalType.SPEED_OPTIMIZATION, GoalType.COMPREHENSIVENESS),
            (GoalType.COST_REDUCTION, GoalType.QUALITY_IMPROVEMENT)
        ]
        
        for secondary_goal in secondary_goals:
            for rule in conflict_rules:
                if (primary_goal.goal_type in rule and secondary_goal.goal_type in rule):
                    conflicts.append((primary_goal.goal_id, secondary_goal.goal_id))
        
        return conflicts
    
    def refine_goals_based_on_feedback(self, recognition_result: GoalRecognitionResult, 
                                     feedback: Dict[str, Any]) -> GoalRecognitionResult:
        """基于反馈精炼目标"""
        # 根据用户反馈调整目标识别结果
        if feedback.get("correct_goal"):
            # 用户确认了正确目标
            recognition_result.primary_goal.confidence = 1.0
        elif feedback.get("wrong_goal"):
            # 用户指出错误目标，需要重新识别
            recognition_result.primary_goal.confidence = 0.0
        
        # 调整优先级
        if "priority" in feedback:
            recognition_result.primary_goal.priority = GoalPriority(feedback["priority"])
        
        return recognition_result
    
    def track_goal_evolution(self, initial_goals: GoalRecognitionResult, 
                           new_input: str, context: Dict[str, Any]) -> GoalRecognitionResult:
        """跟踪目标演化"""
        # 识别新输入中的目标
        new_goals = self.recognize_goals(new_input, context)
        
        # 检查目标是否发生变化
        if new_goals.primary_goal.goal_type != initial_goals.primary_goal.goal_type:
            self.logger.info(f"检测到目标变化: {initial_goals.primary_goal.goal_type.value} -> {new_goals.primary_goal.goal_type.value}")
        
        return new_goals

