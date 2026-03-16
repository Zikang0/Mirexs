"""
任务分解器 - 将复杂任务分解为可执行的子任务
实现Manus智能引擎的核心任务分解能力
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
    CREATIVE = "creative"  # 创意任务
    TECHNICAL = "technical"  # 技术任务
    RESEARCH = "research"  # 研究任务
    AUTOMATION = "automation"  # 自动化任务
    ANALYSIS = "analysis"  # 分析任务
    GENERATION = "generation"  # 生成任务

@dataclass
class Subtask:
    """子任务数据结构"""
    id: str
    name: str
    description: str
    task_type: TaskType
    dependencies: List[str]  # 依赖的子任务ID
    required_capabilities: List[str]  # 需要的能力
    estimated_duration: float  # 预估执行时间（秒）
    priority: int  # 优先级（1-10，10最高）
    parameters: Dict[str, Any]  # 执行参数

@dataclass
class TaskDecomposition:
    """任务分解结果"""
    original_task: str
    subtasks: List[Subtask]
    execution_order: List[str]  # 子任务执行顺序
    total_estimated_duration: float

class TaskDecomposer:
    """任务分解器 - 核心Manus智能引擎"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.decomposition_patterns = self._load_decomposition_patterns()
        self.capability_registry = self._load_capability_registry()
        
        # 加载预训练的任务分解模型（这里用规则引擎模拟）
        self.rules_engine = self._initialize_rules_engine()
        
        self.logger.info("任务分解器初始化完成")
    
    def _load_decomposition_patterns(self) -> Dict[str, Any]:
        """加载任务分解模式"""
        return {
            "creative_generation": {
                "pattern": r"(写|创作|生成|制作).*(文章|报告|故事|诗歌|代码|程序|图片|图像|音乐)",
                "stages": ["需求分析", "内容规划", "草稿生成", "优化完善", "格式调整"]
            },
            "technical_automation": {
                "pattern": r"(自动化|执行|运行|处理).*(文件|数据|程序|脚本|任务)",
                "stages": ["环境检查", "参数配置", "执行准备", "任务执行", "结果验证"]
            },
            "research_analysis": {
                "pattern": r"(研究|分析|调查|查找).*(信息|数据|资料|问题|原因)",
                "stages": ["问题定义", "信息收集", "数据分析", "结论推导", "报告生成"]
            },
            "system_management": {
                "pattern": r"(管理|监控|优化|维护).*(系统|文件|网络|安全|性能)",
                "stages": ["状态评估", "问题诊断", "方案制定", "执行实施", "效果验证"]
            }
        }
    
    def _load_capability_registry(self) -> Dict[str, List[str]]:
        """加载能力注册表"""
        return {
            "creative": ["content_generation", "style_transfer", "creative_writing"],
            "technical": ["code_generation", "system_automation", "data_processing"],
            "research": ["web_search", "data_analysis", "information_synthesis"],
            "automation": ["script_execution", "workflow_management", "api_integration"],
            "analysis": ["statistical_analysis", "pattern_recognition", "trend_analysis"],
            "generation": ["text_generation", "image_generation", "music_generation"]
        }
    
    def _initialize_rules_engine(self):
        """初始化规则引擎"""
        # 这里应该集成真正的规则引擎或机器学习模型
        # 目前用基于规则的实现
        return {
            "complexity_threshold": 3,  # 复杂度阈值
            "max_subtasks": 10,  # 最大子任务数
            "min_subtask_duration": 5.0,  # 最小子任务持续时间
            "dependency_analysis_depth": 3  # 依赖分析深度
        }
    
    def decompose_task(self, task_description: str, context: Dict[str, Any] = None) -> TaskDecomposition:
        """
        分解复杂任务为子任务
        
        Args:
            task_description: 任务描述
            context: 上下文信息
            
        Returns:
            TaskDecomposition: 任务分解结果
        """
        self.logger.info(f"开始分解任务: {task_description}")
        
        if context is None:
            context = {}
        
        # 1. 任务分析和分类
        task_type = self._classify_task(task_description)
        complexity = self._assess_complexity(task_description, context)
        
        # 2. 应用分解模式
        subtasks = self._apply_decomposition_pattern(task_description, task_type, complexity)
        
        # 3. 分析任务依赖关系
        execution_order = self._analyze_dependencies(subtasks)
        
        # 4. 估算总时间
        total_duration = sum(subtask.estimated_duration for subtask in subtasks)
        
        decomposition = TaskDecomposition(
            original_task=task_description,
            subtasks=subtasks,
            execution_order=execution_order,
            total_estimated_duration=total_duration
        )
        
        self.logger.info(f"任务分解完成，生成 {len(subtasks)} 个子任务")
        return decomposition
    
    def _classify_task(self, task_description: str) -> TaskType:
        """分类任务类型"""
        description_lower = task_description.lower()
        
        for task_type, pattern_info in self.decomposition_patterns.items():
            if re.search(pattern_info["pattern"], description_lower):
                if "creative" in task_type:
                    return TaskType.CREATIVE
                elif "technical" in task_type:
                    return TaskType.TECHNICAL
                elif "research" in task_type:
                    return TaskType.RESEARCH
                elif "automation" in task_type:
                    return TaskType.AUTOMATION
        
        # 默认分类
        return TaskType.ANALYSIS
    
    def _assess_complexity(self, task_description: str, context: Dict[str, Any]) -> int:
        """评估任务复杂度"""
        complexity_score = 1
        
        # 基于描述长度
        complexity_score += len(task_description) // 50
        
        # 基于关键词
        complexity_keywords = ["复杂", "多个", "整合", "协调", "系统", "全面"]
        for keyword in complexity_keywords:
            if keyword in task_description:
                complexity_score += 1
        
        # 基于上下文
        if context.get("has_dependencies", False):
            complexity_score += 2
        
        return min(complexity_score, 10)  # 限制在1-10范围内
    
    def _apply_decomposition_pattern(self, task_description: str, task_type: TaskType, complexity: int) -> List[Subtask]:
        """应用分解模式生成子任务"""
        subtasks = []
        
        # 根据任务类型选择分解策略
        if task_type == TaskType.CREATIVE:
            stages = ["需求分析", "内容规划", "草稿生成", "优化完善", "格式调整"]
        elif task_type == TaskType.TECHNICAL:
            stages = ["技术分析", "方案设计", "实现开发", "测试验证", "部署发布"]
        elif task_type == TaskType.RESEARCH:
            stages = ["问题定义", "信息收集", "数据分析", "结论推导", "报告生成"]
        else:
            stages = ["任务分析", "方案制定", "执行实施", "结果验证", "总结反馈"]
        
        # 根据复杂度调整阶段数量
        if complexity <= 3:
            stages = stages[:3]  # 简单任务减少阶段
        elif complexity >= 8:
            # 复杂任务增加阶段
            stages.extend(["风险评估", "应急预案", "质量保证"])
        
        for i, stage in enumerate(stages):
            subtask_id = f"subtask_{i+1:03d}"
            
            subtask = Subtask(
                id=subtask_id,
                name=f"{stage}",
                description=f"{task_description} - {stage}阶段",
                task_type=task_type,
                dependencies=self._get_dependencies_for_stage(i, stages),
                required_capabilities=self._get_required_capabilities(task_type, stage),
                estimated_duration=self._estimate_duration(task_type, stage, complexity),
                priority=self._calculate_priority(i, len(stages)),
                parameters={"stage": stage, "complexity": complexity}
            )
            
            subtasks.append(subtask)
        
        return subtasks
    
    def _get_dependencies_for_stage(self, stage_index: int, stages: List[str]) -> List[str]:
        """获取阶段依赖关系"""
        if stage_index == 0:
            return []
        
        # 每个阶段依赖前一个阶段
        prev_subtask_id = f"subtask_{stage_index:03d}"
        return [prev_subtask_id]
    
    def _get_required_capabilities(self, task_type: TaskType, stage: str) -> List[str]:
        """获取所需能力"""
        base_capabilities = self.capability_registry.get(task_type.value, [])
        
        # 根据阶段添加特定能力
        if "分析" in stage:
            base_capabilities.extend(["problem_analysis", "requirement_gathering"])
        elif "生成" in stage or "创作" in stage:
            base_capabilities.extend(["content_generation", "creative_thinking"])
        elif "验证" in stage or "测试" in stage:
            base_capabilities.extend(["quality_assurance", "testing"])
        
        return list(set(base_capabilities))  # 去重
    
    def _estimate_duration(self, task_type: TaskType, stage: str, complexity: int) -> float:
        """估算阶段持续时间"""
        base_durations = {
            TaskType.CREATIVE: 300,  # 5分钟基础
            TaskType.TECHNICAL: 600,  # 10分钟基础
            TaskType.RESEARCH: 900,  # 15分钟基础
            TaskType.AUTOMATION: 180,  # 3分钟基础
            TaskType.ANALYSIS: 480,  # 8分钟基础
            TaskType.GENERATION: 240  # 4分钟基础
        }
        
        stage_multipliers = {
            "分析": 1.2,
            "规划": 1.1,
            "生成": 1.5,
            "验证": 0.8,
            "优化": 1.3,
            "部署": 0.7
        }
        
        base_duration = base_durations.get(task_type, 300)
        multiplier = stage_multipliers.get(stage[:2], 1.0)  # 取前两个字符匹配
        complexity_factor = 1 + (complexity - 1) * 0.2
        
        return base_duration * multiplier * complexity_factor
    
    def _calculate_priority(self, stage_index: int, total_stages: int) -> int:
        """计算阶段优先级"""
        # 关键路径上的任务优先级较高
        if stage_index == 0:  # 开始阶段
            return 9
        elif stage_index == total_stages - 1:  # 结束阶段
            return 8
        else:
            return 7
    
    def _analyze_dependencies(self, subtasks: List[Subtask]) -> List[str]:
        """分析子任务依赖关系，确定执行顺序"""
        # 使用拓扑排序确定执行顺序
        dependency_graph = {}
        for subtask in subtasks:
            dependency_graph[subtask.id] = set(subtask.dependencies)
        
        # 简单实现 - 按ID顺序（实际应该用拓扑排序算法）
        execution_order = [subtask.id for subtask in subtasks]
        
        return execution_order
    
    def validate_decomposition(self, decomposition: TaskDecomposition) -> bool:
        """验证任务分解的合理性"""
        # 检查是否有循环依赖
        if self._has_cyclic_dependencies(decomposition):
            self.logger.warning("检测到循环依赖")
            return False
        
        # 检查子任务数量是否合理
        if len(decomposition.subtasks) > self.rules_engine["max_subtasks"]:
            self.logger.warning(f"子任务数量过多: {len(decomposition.subtasks)}")
            return False
        
        # 检查是否有必要的开始和结束任务
        has_start = any("开始" in subtask.name or "分析" in subtask.name for subtask in decomposition.subtasks)
        has_end = any("结束" in subtask.name or "完成" in subtask.name for subtask in decomposition.subtasks)
        
        if not has_start or not has_end:
            self.logger.warning("缺少开始或结束任务")
            return False
        
        return True
    
    def _has_cyclic_dependencies(self, decomposition: TaskDecomposition) -> bool:
        """检查是否存在循环依赖"""
        # 简化的循环依赖检查
        visited = set()
        
        def dfs(subtask_id, path):
            if subtask_id in path:
                return True
            if subtask_id in visited:
                return False
            
            visited.add(subtask_id)
            path.add(subtask_id)
            
            subtask = next((s for s in decomposition.subtasks if s.id == subtask_id), None)
            if subtask:
                for dep_id in subtask.dependencies:
                    if dfs(dep_id, path.copy()):
                        return True
            
            return False
        
        for subtask in decomposition.subtasks:
            if dfs(subtask.id, set()):
                return True
        
        return False
    
    def optimize_decomposition(self, decomposition: TaskDecomposition) -> TaskDecomposition:
        """优化任务分解"""
        optimized_subtasks = []
        
        for subtask in decomposition.subtasks:
            # 合并过短的子任务
            if subtask.estimated_duration < self.rules_engine["min_subtask_duration"]:
                self.logger.info(f"合并过短子任务: {subtask.name}")
                # 在实际实现中，这里应该合并逻辑
                continue
            
            # 优化依赖关系
            optimized_dependencies = [
                dep for dep in subtask.dependencies 
                if dep in [s.id for s in decomposition.subtasks]
            ]
            
            optimized_subtask = Subtask(
                id=subtask.id,
                name=subtask.name,
                description=subtask.description,
                task_type=subtask.task_type,
                dependencies=optimized_dependencies,
                required_capabilities=subtask.required_capabilities,
                estimated_duration=subtask.estimated_duration,
                priority=subtask.priority,
                parameters=subtask.parameters
            )
            optimized_subtasks.append(optimized_subtask)
        
        # 重新计算执行顺序
        optimized_order = self._analyze_dependencies(optimized_subtasks)
        total_duration = sum(subtask.estimated_duration for subtask in optimized_subtasks)
        
        return TaskDecomposition(
            original_task=decomposition.original_task,
            subtasks=optimized_subtasks,
            execution_order=optimized_order,
            total_estimated_duration=total_duration
        )
