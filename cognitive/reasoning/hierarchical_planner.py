"""
分层规划器 - 制定分层执行计划
实现多层次的规划策略
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from .task_decomposer import TaskDecomposition, Subtask

logger = logging.getLogger(__name__)

class PlanningLevel(Enum):
    """规划层级枚举"""
    STRATEGIC = "strategic"  # 战略层
    TACTICAL = "tactical"    # 战术层
    OPERATIONAL = "operational"  # 操作层

@dataclass
class PlanNode:
    """规划节点"""
    id: str
    name: str
    level: PlanningLevel
    description: str
    parent_id: Optional[str]
    children_ids: List[str]
    subtask_ids: List[str]  # 关联的子任务ID
    constraints: Dict[str, Any]
    resources: Dict[str, Any]

@dataclass
class HierarchicalPlan:
    """分层规划结果"""
    plan_id: str
    root_node: PlanNode
    nodes: Dict[str, PlanNode]  # 所有节点
    levels: Dict[PlanningLevel, List[PlanNode]]
    execution_graph: Any  # 执行图

class HierarchicalPlanner:
    """分层规划器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.planning_rules = self._load_planning_rules()
        self.resource_manager = ResourceManager()
        self.constraint_solver = ConstraintSolver()
        
    def _load_planning_rules(self) -> Dict[str, Any]:
        """加载规划规则"""
        return {
            "max_strategic_nodes": 5,
            "max_tactical_nodes_per_strategic": 10,
            "max_operational_nodes_per_tactical": 20,
            "planning_horizon": 3600,  # 规划时间范围（秒）
            "resource_allocation_strategy": "balanced"
        }
    
    def create_plan(self, decomposition: TaskDecomposition, context: Dict[str, Any]) -> HierarchicalPlan:
        """
        创建分层执行计划
        
        Args:
            decomposition: 任务分解结果
            context: 上下文信息
            
        Returns:
            HierarchicalPlan: 分层规划结果
        """
        self.logger.info("开始创建分层执行计划")
        
        # 1. 战略层规划
        strategic_nodes = self._create_strategic_plan(decomposition, context)
        
        # 2. 战术层规划
        tactical_nodes = self._create_tactical_plan(strategic_nodes, decomposition, context)
        
        # 3. 操作层规划
        operational_nodes = self._create_operational_plan(tactical_nodes, decomposition, context)
        
        # 4. 构建规划树
        plan = self._build_plan_tree(strategic_nodes, tactical_nodes, operational_nodes, decomposition)
        
        # 5. 优化规划
        optimized_plan = self._optimize_plan(plan, context)
        
        self.logger.info(f"分层规划完成，包含 {len(optimized_plan.nodes)} 个节点")
        return optimized_plan
    
    def _create_strategic_plan(self, decomposition: TaskDecomposition, context: Dict[str, Any]) -> List[PlanNode]:
        """创建战略层规划"""
        strategic_nodes = []
        
        # 根据任务类型和复杂度确定战略节点
        strategic_goals = self._identify_strategic_goals(decomposition, context)
        
        for i, goal in enumerate(strategic_goals):
            node = PlanNode(
                id=f"strategic_{i+1:03d}",
                name=goal["name"],
                level=PlanningLevel.STRATEGIC,
                description=goal["description"],
                parent_id=None,
                children_ids=[],
                subtask_ids=goal["subtask_ids"],
                constraints=goal.get("constraints", {}),
                resources=goal.get("resources", {})
            )
            strategic_nodes.append(node)
        
        return strategic_nodes
    
    def _identify_strategic_goals(self, decomposition: TaskDecomposition, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别战略目标"""
        goals = []
        
        # 根据子任务类型分组
        task_groups = {}
        for subtask in decomposition.subtasks:
            task_type = subtask.task_type.value
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(subtask.id)
        
        # 为每个任务类型创建战略目标
        for task_type, subtask_ids in task_groups.items():
            goal = {
                "name": f"{task_type.capitalize()}战略目标",
                "description": f"完成所有{task_type}类型的子任务",
                "subtask_ids": subtask_ids,
                "constraints": {
                    "time_limit": decomposition.total_estimated_duration,
                    "resource_requirements": ["computation", "memory"]
                },
                "resources": {
                    "priority": 8,
                    "budget": 1000  # 虚拟资源预算
                }
            }
            goals.append(goal)
        
        return goals
    
    def _create_tactical_plan(self, strategic_nodes: List[PlanNode], 
                            decomposition: TaskDecomposition, 
                            context: Dict[str, Any]) -> List[PlanNode]:
        """创建战术层规划"""
        tactical_nodes = []
        
        for strategic_node in strategic_nodes:
            # 为每个战略节点创建战术节点
            tactical_subplans = self._decompose_strategic_node(strategic_node, decomposition, context)
            
            for i, subplan in enumerate(tactical_subplans):
                node = PlanNode(
                    id=f"tactical_{len(tactical_nodes)+1:03d}",
                    name=subplan["name"],
                    level=PlanningLevel.TACTICAL,
                    description=subplan["description"],
                    parent_id=strategic_node.id,
                    children_ids=[],
                    subtask_ids=subplan["subtask_ids"],
                    constraints=subplan.get("constraints", {}),
                    resources=subplan.get("resources", {})
                )
                tactical_nodes.append(node)
                strategic_node.children_ids.append(node.id)
        
        return tactical_nodes
    
    def _decompose_strategic_node(self, strategic_node: PlanNode, 
                                decomposition: TaskDecomposition, 
                                context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分解战略节点为战术节点"""
        tactical_plans = []
        subtask_ids = strategic_node.subtask_ids
        
        # 按执行顺序分组
        execution_groups = self._group_by_execution_order(subtask_ids, decomposition)
        
        for group_name, group_subtask_ids in execution_groups.items():
            tactical_plan = {
                "name": f"{group_name}战术执行",
                "description": f"执行{group_name}阶段的任务",
                "subtask_ids": group_subtask_ids,
                "constraints": {
                    "dependency_order": True,
                    "resource_sharing": False
                },
                "resources": {
                    "priority": 7,
                    "budget": 200
                }
            }
            tactical_plans.append(tactical_plan)
        
        return tactical_plans
    
    def _group_by_execution_order(self, subtask_ids: List[str], decomposition: TaskDecomposition) -> Dict[str, List[str]]:
        """按执行顺序分组子任务"""
        groups = {}
        current_group = []
        group_name = "初始阶段"
        
        for subtask_id in subtask_ids:
            subtask = next((s for s in decomposition.subtasks if s.id == subtask_id), None)
            if subtask:
                # 根据任务名称判断阶段
                if "分析" in subtask.name:
                    group_name = "分析阶段"
                elif "生成" in subtask.name or "创作" in subtask.name:
                    group_name = "生成阶段"
                elif "验证" in subtask.name or "测试" in subtask.name:
                    group_name = "验证阶段"
                elif "优化" in subtask.name:
                    group_name = "优化阶段"
                elif "完成" in subtask.name or "结束" in subtask.name:
                    group_name = "完成阶段"
                
                if group_name not in groups:
                    groups[group_name] = []
                groups[group_name].append(subtask_id)
        
        return groups
    
    def _create_operational_plan(self, tactical_nodes: List[PlanNode], 
                               decomposition: TaskDecomposition, 
                               context: Dict[str, Any]) -> List[PlanNode]:
        """创建操作层规划"""
        operational_nodes = []
        
        for tactical_node in tactical_nodes:
            # 为每个战术节点创建操作节点
            operational_tasks = self._decompose_tactical_node(tactical_node, decomposition, context)
            
            for i, task in enumerate(operational_tasks):
                node = PlanNode(
                    id=f"operational_{len(operational_nodes)+1:03d}",
                    name=task["name"],
                    level=PlanningLevel.OPERATIONAL,
                    description=task["description"],
                    parent_id=tactical_node.id,
                    children_ids=[],
                    subtask_ids=task["subtask_ids"],
                    constraints=task.get("constraints", {}),
                    resources=task.get("resources", {})
                )
                operational_nodes.append(node)
                tactical_node.children_ids.append(node.id)
        
        return operational_nodes
    
    def _decompose_tactical_node(self, tactical_node: PlanNode, 
                               decomposition: TaskDecomposition, 
                               context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分解战术节点为操作节点"""
        operational_tasks = []
        subtask_ids = tactical_node.subtask_ids
        
        # 每个子任务创建一个操作节点
        for subtask_id in subtask_ids:
            subtask = next((s for s in decomposition.subtasks if s.id == subtask_id), None)
            if subtask:
                operational_task = {
                    "name": f"执行: {subtask.name}",
                    "description": subtask.description,
                    "subtask_ids": [subtask_id],
                    "constraints": {
                        "duration_limit": subtask.estimated_duration,
                        "dependencies": subtask.dependencies
                    },
                    "resources": {
                        "priority": subtask.priority,
                        "capabilities": subtask.required_capabilities
                    }
                }
                operational_tasks.append(operational_task)
        
        return operational_tasks
    
    def _build_plan_tree(self, strategic_nodes: List[PlanNode], 
                        tactical_nodes: List[PlanNode], 
                        operational_nodes: List[PlanNode],
                        decomposition: TaskDecomposition) -> HierarchicalPlan:
        """构建规划树"""
        all_nodes = {}
        levels = {
            PlanningLevel.STRATEGIC: strategic_nodes,
            PlanningLevel.TACTICAL: tactical_nodes,
            PlanningLevel.OPERATIONAL: operational_nodes
        }
        
        # 收集所有节点
        for node_list in levels.values():
            for node in node_list:
                all_nodes[node.id] = node
        
        # 构建执行图
        execution_graph = self._build_execution_graph(all_nodes, decomposition)
        
        # 选择第一个战略节点作为根节点
        root_node = strategic_nodes[0] if strategic_nodes else None
        
        plan = HierarchicalPlan(
            plan_id=f"plan_{hash(str(decomposition.original_task))}",
            root_node=root_node,
            nodes=all_nodes,
            levels=levels,
            execution_graph=execution_graph
        )
        
        return plan
    
    def _build_execution_graph(self, nodes: Dict[str, PlanNode], decomposition: TaskDecomposition) -> nx.DiGraph:
        """构建执行图"""
        graph = nx.DiGraph()
        
        # 添加节点
        for node_id, node in nodes.items():
            graph.add_node(node_id, **{
                "name": node.name,
                "level": node.level.value,
                "subtask_ids": node.subtask_ids
            })
        
        # 添加边（父子关系）
        for node_id, node in nodes.items():
            for child_id in node.children_ids:
                if child_id in nodes:
                    graph.add_edge(node_id, child_id)
        
        # 添加子任务依赖关系
        for node_id, node in nodes.items():
            for subtask_id in node.subtask_ids:
                subtask = next((s for s in decomposition.subtasks if s.id == subtask_id), None)
                if subtask:
                    for dep_id in subtask.dependencies:
                        # 找到包含依赖子任务的节点
                        dep_node_id = self._find_node_with_subtask(nodes, dep_id)
                        if dep_node_id and dep_node_id != node_id:
                            graph.add_edge(dep_node_id, node_id)
        
        return graph
    
    def _find_node_with_subtask(self, nodes: Dict[str, PlanNode], subtask_id: str) -> Optional[str]:
        """查找包含指定子任务的节点"""
        for node_id, node in nodes.items():
            if subtask_id in node.subtask_ids:
                return node_id
        return None
    
    def _optimize_plan(self, plan: HierarchicalPlan, context: Dict[str, Any]) -> HierarchicalPlan:
        """优化规划"""
        # 资源优化
        plan = self.resource_manager.optimize_resource_allocation(plan, context)
        
        # 约束求解
        plan = self.constraint_solver.solve_constraints(plan, context)
        
        # 执行顺序优化
        plan = self._optimize_execution_order(plan)
        
        return plan
    
    def _optimize_execution_order(self, plan: HierarchicalPlan) -> HierarchicalPlan:
        """优化执行顺序"""
        # 使用关键路径方法优化
        try:
            # 计算关键路径
            critical_path = self._calculate_critical_path(plan.execution_graph, plan)
            
            # 根据关键路径调整优先级
            for node_id in critical_path:
                if node_id in plan.nodes:
                    node = plan.nodes[node_id]
                    # 提高关键路径上节点的优先级
                    if "resources" in node.__dict__:
                        node.resources["priority"] = min(10, node.resources.get("priority", 5) + 2)
        
        except Exception as e:
            self.logger.warning(f"关键路径计算失败: {e}")
        
        return plan
    
    def _calculate_critical_path(self, graph: nx.DiGraph, plan: HierarchicalPlan) -> List[str]:
        """计算关键路径"""
        # 简化的关键路径计算
        # 在实际实现中应该考虑任务持续时间
        try:
            if graph.number_of_nodes() == 0:
                return []
            
            # 使用最长路径作为关键路径的近似
            longest_path = []
            for path in nx.all_simple_paths(graph, plan.root_node.id, 
                                          [n for n in graph.nodes() if graph.out_degree(n) == 0]):
                if len(path) > len(longest_path):
                    longest_path = path
            
            return longest_path
        except:
            return list(graph.nodes())

class ResourceManager:
    """资源管理器"""
    
    def optimize_resource_allocation(self, plan: HierarchicalPlan, context: Dict[str, Any]) -> HierarchicalPlan:
        """优化资源分配"""
        # 简化的资源分配逻辑
        total_resources = context.get("available_resources", {"cpu": 100, "memory": 100, "gpu": 100})
        
        for node in plan.nodes.values():
            # 根据节点层级分配资源
            if node.level == PlanningLevel.STRATEGIC:
                node.resources["cpu_allocation"] = total_resources.get("cpu", 100) * 0.3
                node.resources["memory_allocation"] = total_resources.get("memory", 100) * 0.3
            elif node.level == PlanningLevel.TACTICAL:
                node.resources["cpu_allocation"] = total_resources.get("cpu", 100) * 0.5
                node.resources["memory_allocation"] = total_resources.get("memory", 100) * 0.5
            else:  # OPERATIONAL
                node.resources["cpu_allocation"] = total_resources.get("cpu", 100) * 0.2
                node.resources["memory_allocation"] = total_resources.get("memory", 100) * 0.2
        
        return plan

class ConstraintSolver:
    """约束求解器"""
    
    def solve_constraints(self, plan: HierarchicalPlan, context: Dict[str, Any]) -> HierarchicalPlan:
        """求解约束"""
        # 简化的约束求解
        for node in plan.nodes.values():
            if "constraints" in node.__dict__:
                constraints = node.constraints
                
                # 处理时间约束
                if "time_limit" in constraints:
                    # 确保时间约束合理
                    pass
                
                # 处理依赖约束
                if "dependencies" in constraints:
                    # 确保依赖关系满足
                    pass
        
        return plan

