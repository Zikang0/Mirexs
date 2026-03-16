"""
约束求解器 - 约束条件求解
处理各种类型的约束并找到可行解
"""

import logging
import random
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from scipy.optimize import linprog, minimize
import pulp

logger = logging.getLogger(__name__)

class ConstraintType(Enum):
    """约束类型枚举"""
    EQUALITY = "equality"  # 等式约束
    INEQUALITY = "inequality"  # 不等式约束
    BOUND = "bound"  # 边界约束
    LOGICAL = "logical"  # 逻辑约束
    TEMPORAL = "temporal"  # 时序约束

class SolutionStatus(Enum):
    """解状态枚举"""
    OPTIMAL = "optimal"  # 最优解
    FEASIBLE = "feasible"  # 可行解
    INFEASIBLE = "infeasible"  # 无可行解
    UNBOUNDED = "unbounded"  # 无界
    TIMEOUT = "timeout"  # 超时

@dataclass
class Constraint:
    """约束"""
    constraint_id: str
    constraint_type: ConstraintType
    expression: str
    variables: List[str]
    bounds: Tuple[Optional[float], Optional[float]] = (None, None)  # 下界, 上界
    weight: float = 1.0  # 权重
    strict: bool = False  # 是否严格约束

@dataclass
class Variable:
    """变量"""
    name: str
    variable_type: str  # continuous, integer, binary
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    initial_value: Optional[float] = None

@dataclass
class OptimizationResult:
    """优化结果"""
    status: SolutionStatus
    objective_value: Optional[float]
    variables: Dict[str, float]
    solving_time: float
    iterations: int
    constraints_satisfied: List[str]
    constraints_violated: List[str]

@dataclass
class ConstraintProblem:
    """约束问题"""
    problem_id: str
    objective: str  # 目标函数
    variables: Dict[str, Variable]
    constraints: Dict[str, Constraint]
    preferences: Dict[str, float] = field(default_factory=dict)  # 偏好权重

class ConstraintSolver:
    """约束求解器"""
    
    def __init__(self, timeout: int = 30):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.solving_strategies = self._initialize_strategies()
        self.relaxation_factors = self._initialize_relaxation_factors()
        
        self.logger.info(f"约束求解器初始化完成，超时时间: {timeout}秒")
    
    def _initialize_strategies(self) -> Dict[str, Any]:
        """初始化求解策略"""
        return {
            "linear_programming": {
                "applicable_types": [ConstraintType.EQUALITY, ConstraintType.INEQUALITY, ConstraintType.BOUND],
                "solver": "scipy"
            },
            "genetic_algorithm": {
                "applicable_types": [ConstraintType.LOGICAL, ConstraintType.TEMPORAL],
                "solver": "custom"
            },
            "constraint_propagation": {
                "applicable_types": [ConstraintType.LOGICAL],
                "solver": "custom"
            },
            "mixed_integer": {
                "applicable_types": [ConstraintType.INEQUALITY, ConstraintType.BOUND, ConstraintType.LOGICAL],
                "solver": "pulp"
            }
        }
    
    def _initialize_relaxation_factors(self) -> Dict[str, float]:
        """初始化松弛因子"""
        return {
            "strict": 0.0,  # 严格约束不允许违反
            "high": 0.1,    # 高优先级约束
            "medium": 0.3,  # 中等优先级约束
            "low": 0.5      # 低优先级约束
        }
    
    def solve_problem(self, problem: ConstraintProblem) -> OptimizationResult:
        """
        求解约束问题
        
        Args:
            problem: 约束问题
            
        Returns:
            OptimizationResult: 优化结果
        """
        self.logger.info(f"开始求解约束问题: {problem.problem_id}")
        
        start_time = time.time()
        
        # 选择求解策略
        strategy = self._select_solving_strategy(problem)
        self.logger.info(f"选择求解策略: {strategy}")
        
        # 应用求解策略
        if strategy == "linear_programming":
            result = self._solve_linear_programming(problem)
        elif strategy == "genetic_algorithm":
            result = self._solve_genetic_algorithm(problem)
        elif strategy == "mixed_integer":
            result = self._solve_mixed_integer(problem)
        else:
            result = self._solve_constraint_propagation(problem)
        
        # 计算求解时间
        solving_time = time.time() - start_time
        
        result.solving_time = solving_time
        
        self.logger.info(f"约束问题求解完成: {result.status.value}, 目标值: {result.objective_value}")
        return result
    
    def _select_solving_strategy(self, problem: ConstraintProblem) -> str:
        """选择求解策略"""
        constraint_types = set(constraint.constraint_type for constraint in problem.constraints.values())
        variable_types = set(var.variable_type for var in problem.variables.values())
        
        # 检查变量类型
        has_integer_vars = any(vt in ["integer", "binary"] for vt in variable_types)
        
        # 检查约束类型
        has_logical_constraints = ConstraintType.LOGICAL in constraint_types
        has_temporal_constraints = ConstraintType.TEMPORAL in constraint_types
        
        if has_integer_vars:
            return "mixed_integer"
        elif has_logical_constraints or has_temporal_constraints:
            return "genetic_algorithm"
        else:
            return "linear_programming"
    
    def _solve_linear_programming(self, problem: ConstraintProblem) -> OptimizationResult:
        """线性规划求解"""
        try:
            # 提取变量信息
            var_names = list(problem.variables.keys())
            n_vars = len(var_names)
            
            # 构建目标函数系数
            c = self._parse_objective(problem.objective, var_names)
            
            # 构建约束矩阵和边界
            A, b_lower, b_upper = self._build_constraint_matrix(problem, var_names)
            
            # 变量边界
            bounds = []
            for var_name in var_names:
                var = problem.variables[var_name]
                bounds.append((var.lower_bound, var.upper_bound))
            
            # 求解线性规划
            result = linprog(c, A_ub=A, b_ub=b_upper, 
                           A_eq=None, b_eq=None, bounds=bounds, 
                           method='highs')
            
            # 解析结果
            if result.success:
                variables = {var_names[i]: result.x[i] for i in range(n_vars)}
                
                # 检查约束满足情况
                satisfied, violated = self._check_constraints(problem, variables)
                
                return OptimizationResult(
                    status=SolutionStatus.OPTIMAL if result.status == 0 else SolutionStatus.FEASIBLE,
                    objective_value=result.fun,
                    variables=variables,
                    solving_time=0.0,  # 将在外部设置
                    iterations=getattr(result, 'nit', 0),
                    constraints_satisfied=satisfied,
                    constraints_violated=violated
                )
            else:
                return OptimizationResult(
                    status=SolutionStatus.INFEASIBLE,
                    objective_value=None,
                    variables={},
                    solving_time=0.0,
                    iterations=0,
                    constraints_satisfied=[],
                    constraints_violated=list(problem.constraints.keys())
                )
                
        except Exception as e:
            self.logger.error(f"线性规划求解失败: {e}")
            return self._create_error_result(problem)
    
    def _parse_objective(self, objective: str, var_names: List[str]) -> np.ndarray:
        """解析目标函数"""
        # 简化的目标函数解析
        # 在实际实现中应该使用更复杂的解析器
        c = np.zeros(len(var_names))
        
        for i, var_name in enumerate(var_names):
            if var_name in objective:
                # 简单假设系数为1或-1
                if f"-{var_name}" in objective or f"minimize {var_name}" in objective:
                    c[i] = 1  # 最小化该变量
                else:
                    c[i] = -1  # 最大化该变量
        
        return c
    
    def _build_constraint_matrix(self, problem: ConstraintProblem, var_names: List[str]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """构建约束矩阵"""
        constraints_list = list(problem.constraints.values())
        n_constraints = len(constraints_list)
        n_vars = len(var_names)
        
        if n_constraints == 0:
            return np.zeros((0, n_vars)), np.array([]), np.array([])
        
        A = np.zeros((n_constraints, n_vars))
        b_lower = np.full(n_constraints, -np.inf)
        b_upper = np.full(n_constraints, np.inf)
        
        var_index_map = {name: i for i, name in enumerate(var_names)}
        
        for i, constraint in enumerate(constraints_list):
            # 简化的约束解析
            # 在实际实现中应该使用更复杂的解析器
            for var_name in constraint.variables:
                if var_name in var_index_map:
                    idx = var_index_map[var_name]
                    
                    # 简单假设系数
                    if ">=" in constraint.expression or "至少" in constraint.expression:
                        A[i, idx] = 1
                        if constraint.bounds[0] is not None:
                            b_lower[i] = constraint.bounds[0]
                    elif "<=" in constraint.expression or "最多" in constraint.expression:
                        A[i, idx] = 1
                        if constraint.bounds[1] is not None:
                            b_upper[i] = constraint.bounds[1]
                    elif "=" in constraint.expression or "等于" in constraint.expression:
                        A[i, idx] = 1
                        if constraint.bounds[0] is not None:
                            b_lower[i] = constraint.bounds[0]
                            b_upper[i] = constraint.bounds[0]
        
        return A, b_lower, b_upper
    
    def _solve_genetic_algorithm(self, problem: ConstraintProblem) -> OptimizationResult:
        """遗传算法求解"""
        # 简化的遗传算法实现
        population_size = 50
        generations = 100
        mutation_rate = 0.1
        
        # 初始化种群
        population = self._initialize_population(problem, population_size)
        
        best_solution = None
        best_fitness = -float('inf')
        
        for generation in range(generations):
            # 评估适应度
            fitness_scores = []
            for solution in population:
                fitness = self._evaluate_fitness(problem, solution)
                fitness_scores.append(fitness)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = solution.copy()
            
            # 选择
            selected = self._select_population(population, fitness_scores)
            
            # 交叉
            offspring = self._crossover_population(selected, population_size)
            
            # 变异
            population = self._mutate_population(problem, offspring, mutation_rate)
        
        # 检查约束满足情况
        satisfied, violated = self._check_constraints(problem, best_solution)
        
        return OptimizationResult(
            status=SolutionStatus.FEASIBLE,
            objective_value=best_fitness,
            variables=best_solution,
            solving_time=0.0,
            iterations=generations,
            constraints_satisfied=satisfied,
            constraints_violated=violated
        )
    
    def _initialize_population(self, problem: ConstraintProblem, size: int) -> List[Dict[str, float]]:
        """初始化种群"""
        population = []
        
        for _ in range(size):
            solution = {}
            for var_name, variable in problem.variables.items():
                if variable.variable_type == "continuous":
                    # 在边界内随机生成
                    lower = variable.lower_bound if variable.lower_bound is not None else 0
                    upper = variable.upper_bound if variable.upper_bound is not None else 100
                    solution[var_name] = random.uniform(lower, upper)
                elif variable.variable_type == "integer":
                    lower = int(variable.lower_bound) if variable.lower_bound is not None else 0
                    upper = int(variable.upper_bound) if variable.upper_bound is not None else 100
                    solution[var_name] = random.randint(lower, upper)
                else:  # binary
                    solution[var_name] = random.randint(0, 1)
            
            population.append(solution)
        
        return population
    
    def _evaluate_fitness(self, problem: ConstraintProblem, solution: Dict[str, float]) -> float:
        """评估适应度"""
        # 计算目标函数值
        objective_value = self._calculate_objective(problem.objective, solution)
        
        # 计算约束违反惩罚
        penalty = self._calculate_constraint_penalty(problem, solution)
        
        # 适应度 = 目标值 - 惩罚
        fitness = objective_value - penalty
        
        return fitness
    
    def _calculate_objective(self, objective: str, solution: Dict[str, float]) -> float:
        """计算目标函数值"""
        # 简化的目标计算
        value = 0.0
        
        for var_name, var_value in solution.items():
            if var_name in objective:
                if f"minimize {var_name}" in objective or f"-{var_name}" in objective:
                    value -= var_value
                else:
                    value += var_value
        
        return value
    
    def _calculate_constraint_penalty(self, problem: ConstraintProblem, solution: Dict[str, float]) -> float:
        """计算约束违反惩罚"""
        penalty = 0.0
        
        for constraint in problem.constraints.values():
            violation = self._check_constraint_violation(constraint, solution)
            if violation > 0:
                penalty += violation * constraint.weight * 100  # 惩罚系数
        
        return penalty
    
    def _check_constraint_violation(self, constraint: Constraint, solution: Dict[str, float]) -> float:
        """检查约束违反程度"""
        # 简化的约束检查
        relevant_vars = [var for var in constraint.variables if var in solution]
        if not relevant_vars:
            return 0.0
        
        # 计算相关变量的值
        var_value = sum(solution[var] for var in relevant_vars)
        
        # 检查边界
        lower, upper = constraint.bounds
        
        violation = 0.0
        if lower is not None and var_value < lower:
            violation = lower - var_value
        elif upper is not None and var_value > upper:
            violation = var_value - upper
        
        return violation
    
    def _select_population(self, population: List[Dict[str, float]], 
                         fitness_scores: List[float]) -> List[Dict[str, float]]:
        """选择种群"""
        # 轮盘赌选择
        total_fitness = sum(fitness_scores)
        if total_fitness <= 0:
            return population[:len(population)//2]
        
        probabilities = [score / total_fitness for score in fitness_scores]
        selected_indices = np.random.choice(
            len(population), 
            size=len(population)//2, 
            p=probabilities
        )
        
        return [population[i] for i in selected_indices]
    
    def _crossover_population(self, population: List[Dict[str, float]], 
                            target_size: int) -> List[Dict[str, float]]:
        """交叉种群"""
        offspring = []
        
        while len(offspring) < target_size:
            if len(population) < 2:
                break
            
            parent1, parent2 = random.sample(population, 2)
            child = {}
            
            # 单点交叉
            crossover_point = random.randint(1, len(parent1) - 1)
            keys = list(parent1.keys())
            
            for i, key in enumerate(keys):
                if i < crossover_point:
                    child[key] = parent1[key]
                else:
                    child[key] = parent2[key]
            
            offspring.append(child)
        
        return offspring
    
    def _mutate_population(self, problem: ConstraintProblem, 
                         population: List[Dict[str, float]], 
                         mutation_rate: float) -> List[Dict[str, float]]:
        """变异种群"""
        mutated_population = []
        
        for solution in population:
            mutated_solution = solution.copy()
            
            for var_name, variable in problem.variables.items():
                if random.random() < mutation_rate:
                    if variable.variable_type == "continuous":
                        lower = variable.lower_bound if variable.lower_bound is not None else 0
                        upper = variable.upper_bound if variable.upper_bound is not None else 100
                        mutated_solution[var_name] = random.uniform(lower, upper)
                    elif variable.variable_type == "integer":
                        lower = int(variable.lower_bound) if variable.lower_bound is not None else 0
                        upper = int(variable.upper_bound) if variable.upper_bound is not None else 100
                        mutated_solution[var_name] = random.randint(lower, upper)
                    else:  # binary
                        mutated_solution[var_name] = 1 - mutated_solution[var_name]  # 翻转
            
            mutated_population.append(mutated_solution)
        
        return mutated_population
    
    def _solve_mixed_integer(self, problem: ConstraintProblem) -> OptimizationResult:
        """混合整数规划求解"""
        try:
            # 使用PuLP求解器
            solver = pulp.PULP_CBC_CMD(timeLimit=self.timeout)
            lp_problem = pulp.LpProblem(problem.problem_id, pulp.LpMinimize)
            
            # 创建变量
            pulp_vars = {}
            for var_name, variable in problem.variables.items():
                if variable.variable_type == "continuous":
                    pulp_vars[var_name] = pulp.LpVariable(
                        var_name, 
                        lowBound=variable.lower_bound,
                        upBound=variable.upper_bound
                    )
                elif variable.variable_type == "integer":
                    pulp_vars[var_name] = pulp.LpVariable(
                        var_name,
                        lowBound=variable.lower_bound,
                        upBound=variable.upper_bound,
                        cat=pulp.LpInteger
                    )
                else:  # binary
                    pulp_vars[var_name] = pulp.LpVariable(
                        var_name,
                        cat=pulp.LpBinary
                    )
            
            # 设置目标函数
            objective = self._build_pulp_objective(problem.objective, pulp_vars)
            lp_problem += objective
            
            # 添加约束
            for constraint in problem.constraints.values():
                pulp_constraint = self._build_pulp_constraint(constraint, pulp_vars)
                if pulp_constraint is not None:
                    lp_problem += pulp_constraint
            
            # 求解
            lp_problem.solve(solver)
            
            # 解析结果
            if lp_problem.status == pulp.LpStatusOptimal:
                variables = {name: var.value() for name, var in pulp_vars.items()}
                satisfied, violated = self._check_constraints(problem, variables)
                
                return OptimizationResult(
                    status=SolutionStatus.OPTIMAL,
                    objective_value=pulp.value(lp_problem.objective),
                    variables=variables,
                    solving_time=0.0,
                    iterations=0,  # PuLP不直接提供迭代次数
                    constraints_satisfied=satisfied,
                    constraints_violated=violated
                )
            else:
                return OptimizationResult(
                    status=SolutionStatus.INFEASIBLE,
                    objective_value=None,
                    variables={},
                    solving_time=0.0,
                    iterations=0,
                    constraints_satisfied=[],
                    constraints_violated=list(problem.constraints.keys())
                )
                
        except Exception as e:
            self.logger.error(f"混合整数规划求解失败: {e}")
            return self._create_error_result(problem)
    
    def _build_pulp_objective(self, objective: str, pulp_vars: Dict[str, Any]) -> Any:
        """构建PuLP目标函数"""
        # 简化的目标构建
        expr = 0
        
        for var_name, var in pulp_vars.items():
            if var_name in objective:
                if f"minimize {var_name}" in objective or f"-{var_name}" in objective:
                    expr += var
                else:
                    expr -= var
        
        return expr
    
    def _build_pulp_constraint(self, constraint: Constraint, pulp_vars: Dict[str, Any]) -> Optional[Any]:
        """构建PuLP约束"""
        relevant_vars = [var for var_name, var in pulp_vars.items() 
                        if var_name in constraint.variables]
        
        if not relevant_vars:
            return None
        
        # 构建表达式
        expr = sum(relevant_vars)
        lower, upper = constraint.bounds
        
        if lower is not None and upper is not None and lower == upper:
            return expr == lower
        elif lower is not None:
            return expr >= lower
        elif upper is not None:
            return expr <= upper
        else:
            return None
    
    def _solve_constraint_propagation(self, problem: ConstraintProblem) -> OptimizationResult:
        """约束传播求解"""
        # 简化的约束传播
        solution = {}
        
        # 初始化变量域
        domains = {}
        for var_name, variable in problem.variables.items():
            if variable.variable_type == "continuous":
                domains[var_name] = (variable.lower_bound or 0, variable.upper_bound or 100)
            elif variable.variable_type == "integer":
                domains[var_name] = (int(variable.lower_bound or 0), int(variable.upper_bound or 100))
            else:  # binary
                domains[var_name] = (0, 1)
        
        # 约束传播
        changed = True
        iterations = 0
        max_iterations = 100
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for constraint in problem.constraints.values():
                domain_changes = self._propagate_constraint(constraint, domains)
                if domain_changes:
                    changed = True
        
        # 选择解
        for var_name, domain in domains.items():
            if domain[0] == domain[1]:
                solution[var_name] = domain[0]
            else:
                # 随机选择域中的值
                if problem.variables[var_name].variable_type == "continuous":
                    solution[var_name] = random.uniform(domain[0], domain[1])
                else:
                    solution[var_name] = random.randint(int(domain[0]), int(domain[1]))
        
        # 检查约束满足情况
        satisfied, violated = self._check_constraints(problem, solution)
        
        return OptimizationResult(
            status=SolutionStatus.FEASIBLE,
            objective_value=self._calculate_objective(problem.objective, solution),
            variables=solution,
            solving_time=0.0,
            iterations=iterations,
            constraints_satisfied=satisfied,
            constraints_violated=violated
        )
    
    def _propagate_constraint(self, constraint: Constraint, domains: Dict[str, Tuple[float, float]]) -> bool:
        """传播约束"""
        changed = False
        
        relevant_vars = [var for var in constraint.variables if var in domains]
        if len(relevant_vars) != 1:
            return False  # 只处理单变量约束
        
        var_name = relevant_vars[0]
        current_domain = domains[var_name]
        lower, upper = constraint.bounds
        
        new_lower = current_domain[0]
        new_upper = current_domain[1]
        
        if lower is not None and lower > new_lower:
            new_lower = lower
            changed = True
        
        if upper is not None and upper < new_upper:
            new_upper = upper
            changed = True
        
        if changed:
            domains[var_name] = (new_lower, new_upper)
        
        return changed
    
    def _check_constraints(self, problem: ConstraintProblem, solution: Dict[str, float]) -> Tuple[List[str], List[str]]:
        """检查约束满足情况"""
        satisfied = []
        violated = []
        
        for constraint_id, constraint in problem.constraints.items():
            if self._is_constraint_satisfied(constraint, solution):
                satisfied.append(constraint_id)
            else:
                violated.append(constraint_id)
        
        return satisfied, violated
    
    def _is_constraint_satisfied(self, constraint: Constraint, solution: Dict[str, float]) -> bool:
        """检查约束是否满足"""
        relevant_vars = [var for var in constraint.variables if var in solution]
        if not relevant_vars:
            return True  # 没有相关变量，默认满足
        
        var_value = sum(solution[var] for var in relevant_vars)
        lower, upper = constraint.bounds
        
        if lower is not None and var_value < lower:
            return False
        if upper is not None and var_value > upper:
            return False
        
        return True
    
    def _create_error_result(self, problem: ConstraintProblem) -> OptimizationResult:
        """创建错误结果"""
        return OptimizationResult(
            status=SolutionStatus.INFEASIBLE,
            objective_value=None,
            variables={},
            solving_time=0.0,
            iterations=0,
            constraints_satisfied=[],
            constraints_violated=list(problem.constraints.keys())
        )
    
    def relax_constraints(self, problem: ConstraintProblem, 
                        relaxation_level: str = "medium") -> ConstraintProblem:
        """
        松弛约束
        
        Args:
            problem: 原始问题
            relaxation_level: 松弛级别
            
        Returns:
            ConstraintProblem: 松弛后的问题
        """
        relaxation_factor = self.relaxation_factors.get(relaxation_level, 0.3)
        
        relaxed_constraints = {}
        for constraint_id, constraint in problem.constraints.items():
            if constraint.strict:
                # 严格约束不松弛
                relaxed_constraints[constraint_id] = constraint
            else:
                # 松弛边界
                lower, upper = constraint.bounds
                
                if lower is not None:
                    lower = lower * (1 - relaxation_factor)
                if upper is not None:
                    upper = upper * (1 + relaxation_factor)
                
                relaxed_constraint = Constraint(
                    constraint_id=constraint_id,
                    constraint_type=constraint.constraint_type,
                    expression=constraint.expression,
                    variables=constraint.variables,
                    bounds=(lower, upper),
                    weight=constraint.weight * 0.8,  # 降低权重
                    strict=constraint.strict
                )
                relaxed_constraints[constraint_id] = relaxed_constraint
        
        relaxed_problem = ConstraintProblem(
            problem_id=f"{problem.problem_id}_relaxed",
            objective=problem.objective,
            variables=problem.variables,
            constraints=relaxed_constraints,
            preferences=problem.preferences
        )
        
        return relaxed_problem

import time  # 添加time导入
