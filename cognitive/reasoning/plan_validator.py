"""
计划验证器 - 验证计划可行性
检查计划的完整性、一致性和可执行性
"""

import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import networkx as nx
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class ValidationResult(Enum):
    """验证结果枚举"""
    VALID = "valid"  # 有效
    INVALID = "invalid"  # 无效
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误

class ValidationLevel(Enum):
    """验证级别枚举"""
    BASIC = "basic"  # 基本验证
    STANDARD = "standard"  # 标准验证
    STRICT = "strict"  # 严格验证
    COMPREHENSIVE = "comprehensive"  # 全面验证

@dataclass
class ValidationIssue:
    """验证问题"""
    issue_id: str
    issue_type: str  # error, warning, info
    severity: str  # critical, high, medium, low
    description: str
    location: str  # 问题位置
    suggestion: str
    related_elements: List[str] = field(default_factory=list)

@dataclass
class ValidationReport:
    """验证报告"""
    plan_id: str
    validation_level: ValidationLevel
    overall_result: ValidationResult
    issues: List[ValidationIssue]
    validation_time: float
    checked_elements: int
    passed_checks: int
    failed_checks: int

@dataclass
class PlanElement:
    """计划元素"""
    element_id: str
    element_type: str  # task, decision, condition, resource
    properties: Dict[str, Any]
    dependencies: List[str]
    requirements: List[str]
    constraints: List[str]

class PlanValidator:
    """计划验证器"""
    
    def __init__(self, validation_timeout: int = 60):
        self.logger = logging.getLogger(__name__)
        self.validation_timeout = validation_timeout
        self.validation_rules = self._load_validation_rules()
        self.resource_checker = ResourceChecker()
        self.dependency_analyzer = DependencyAnalyzer()
        self.constraint_checker = ConstraintChecker()
        
        self.logger.info(f"计划验证器初始化完成，超时时间: {validation_timeout}秒")
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """加载验证规则"""
        return {
            "structural": {
                "cyclic_dependencies": {
                    "severity": "critical",
                    "description": "检测循环依赖",
                    "enabled": True
                },
                "unreachable_elements": {
                    "severity": "high",
                    "description": "检测不可达元素",
                    "enabled": True
                },
                "dead_end_elements": {
                    "severity": "medium",
                    "description": "检测死端元素",
                    "enabled": True
                }
            },
            "semantic": {
                "resource_availability": {
                    "severity": "high",
                    "description": "检查资源可用性",
                    "enabled": True
                },
                "constraint_satisfaction": {
                    "severity": "critical",
                    "description": "检查约束满足",
                    "enabled": True
                },
                "temporal_consistency": {
                    "severity": "medium",
                    "description": "检查时间一致性",
                    "enabled": True
                }
            },
            "practical": {
                "execution_feasibility": {
                    "severity": "high",
                    "description": "检查执行可行性",
                    "enabled": True
                },
                "risk_assessment": {
                    "severity": "medium",
                    "description": "风险评估",
                    "enabled": True
                }
            }
        }
    
    def validate_plan(self, plan: Dict[str, Any], 
                     validation_level: ValidationLevel = ValidationLevel.STANDARD,
                     context: Dict[str, Any] = None) -> ValidationReport:
        """
        验证计划
        
        Args:
            plan: 计划数据
            validation_level: 验证级别
            context: 上下文信息
            
        Returns:
            ValidationReport: 验证报告
        """
        self.logger.info(f"开始验证计划: {plan.get('plan_id', 'unknown')}")
        
        if context is None:
            context = {}
        
        start_time = time.time()
        issues = []
        checked_elements = 0
        passed_checks = 0
        failed_checks = 0
        
        # 根据验证级别选择检查项
        checks_to_perform = self._select_checks_for_level(validation_level)
        
        # 并行执行检查
        with ThreadPoolExecutor(max_workers=min(len(checks_to_perform), 4)) as executor:
            future_to_check = {}
            
            for check_name in checks_to_perform:
                future = executor.submit(
                    self._perform_single_check,
                    check_name, plan, context
                )
                future_to_check[future] = check_name
            
            # 收集结果
            for future in as_completed(future_to_check, timeout=self.validation_timeout):
                check_name = future_to_check[future]
                try:
                    check_issues, elements_checked, checks_passed = future.result()
                    issues.extend(check_issues)
                    checked_elements += elements_checked
                    passed_checks += checks_passed
                    failed_checks += len(check_issues)
                except Exception as e:
                    self.logger.error(f"检查 {check_name} 失败: {e}")
                    issue = ValidationIssue(
                        issue_id=f"validation_error_{len(issues)}",
                        issue_type="error",
                        severity="high",
                        description=f"验证检查失败: {check_name}",
                        location="validation_system",
                        suggestion="检查验证系统配置"
                    )
                    issues.append(issue)
                    failed_checks += 1
        
        # 确定总体结果
        overall_result = self._determine_overall_result(issues)
        validation_time = time.time() - start_time
        
        report = ValidationReport(
            plan_id=plan.get('plan_id', 'unknown'),
            validation_level=validation_level,
            overall_result=overall_result,
            issues=issues,
            validation_time=validation_time,
            checked_elements=checked_elements,
            passed_checks=passed_checks,
            failed_checks=failed_checks
        )
        
        self.logger.info(f"计划验证完成: {overall_result.value}, 发现问题: {len(issues)}")
        return report
    
    def _select_checks_for_level(self, validation_level: ValidationLevel) -> List[str]:
        """根据验证级别选择检查项"""
        base_checks = []
        
        if validation_level == ValidationLevel.BASIC:
            base_checks = [
                "cyclic_dependencies",
                "resource_availability",
                "constraint_satisfaction"
            ]
        elif validation_level == ValidationLevel.STANDARD:
            base_checks = [
                "cyclic_dependencies",
                "unreachable_elements",
                "resource_availability",
                "constraint_satisfaction",
                "execution_feasibility"
            ]
        elif validation_level == ValidationLevel.STRICT:
            base_checks = [
                "cyclic_dependencies",
                "unreachable_elements",
                "dead_end_elements",
                "resource_availability",
                "constraint_satisfaction",
                "temporal_consistency",
                "execution_feasibility"
            ]
        else:  # COMPREHENSIVE
            base_checks = list(self.validation_rules["structural"].keys()) + \
                         list(self.validation_rules["semantic"].keys()) + \
                         list(self.validation_rules["practical"].keys())
        
        # 只返回启用的检查
        enabled_checks = []
        for check in base_checks:
            for category in self.validation_rules.values():
                if check in category and category[check].get("enabled", False):
                    enabled_checks.append(check)
                    break
        
        return enabled_checks
    
    def _perform_single_check(self, check_name: str, plan: Dict[str, Any], 
                            context: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """执行单个检查"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        try:
            if check_name == "cyclic_dependencies":
                issues, elements_checked, checks_passed = self._check_cyclic_dependencies(plan)
            elif check_name == "unreachable_elements":
                issues, elements_checked, checks_passed = self._check_unreachable_elements(plan)
            elif check_name == "dead_end_elements":
                issues, elements_checked, checks_passed = self._check_dead_end_elements(plan)
            elif check_name == "resource_availability":
                issues, elements_checked, checks_passed = self._check_resource_availability(plan, context)
            elif check_name == "constraint_satisfaction":
                issues, elements_checked, checks_passed = self._check_constraint_satisfaction(plan, context)
            elif check_name == "temporal_consistency":
                issues, elements_checked, checks_passed = self._check_temporal_consistency(plan)
            elif check_name == "execution_feasibility":
                issues, elements_checked, checks_passed = self._check_execution_feasibility(plan, context)
            elif check_name == "risk_assessment":
                issues, elements_checked, checks_passed = self._check_risk_assessment(plan, context)
            else:
                self.logger.warning(f"未知的检查项: {check_name}")
        
        except Exception as e:
            self.logger.error(f"检查 {check_name} 执行失败: {e}")
            issue = ValidationIssue(
                issue_id=f"check_error_{check_name}",
                issue_type="error",
                severity="high",
                description=f"检查执行失败: {check_name}",
                location="validation_system",
                suggestion="检查验证逻辑实现"
            )
            issues.append(issue)
        
        return issues, elements_checked, checks_passed
    
    def _check_cyclic_dependencies(self, plan: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查循环依赖"""
        issues = []
        
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(plan)
        
        # 检测循环
        try:
            cycles = list(nx.simple_cycles(dependency_graph))
            if cycles:
                for cycle in cycles:
                    issue = ValidationIssue(
                        issue_id=f"cycle_{len(issues)}",
                        issue_type="error",
                        severity="critical",
                        description=f"检测到循环依赖: {' -> '.join(cycle)}",
                        location="dependency_structure",
                        suggestion="重新设计依赖关系，打破循环"
                    )
                    issues.append(issue)
            
            elements_checked = len(dependency_graph.nodes())
            checks_passed = elements_checked - len(issues)
            
        except Exception as e:
            self.logger.error(f"循环依赖检查失败: {e}")
            elements_checked = 0
            checks_passed = 0
        
        return issues, elements_checked, checks_passed
    
    def _build_dependency_graph(self, plan: Dict[str, Any]) -> nx.DiGraph:
        """构建依赖图"""
        graph = nx.DiGraph()
        
        # 添加节点
        elements = plan.get('elements', {})
        for element_id in elements.keys():
            graph.add_node(element_id)
        
        # 添加边（依赖关系）
        for element_id, element_data in elements.items():
            dependencies = element_data.get('dependencies', [])
            for dep_id in dependencies:
                if dep_id in elements:
                    graph.add_edge(element_id, dep_id)
        
        return graph
    
    def _check_unreachable_elements(self, plan: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查不可达元素"""
        issues = []
        
        dependency_graph = self._build_dependency_graph(plan)
        elements = plan.get('elements', {})
        
        # 找到起始元素（没有依赖的元素）
        start_elements = [node for node in dependency_graph.nodes() 
                         if dependency_graph.in_degree(node) == 0]
        
        if not start_elements:
            issue = ValidationIssue(
                issue_id="no_start_elements",
                issue_type="warning",
                severity="medium",
                description="没有找到起始元素（没有依赖的元素）",
                location="plan_structure",
                suggestion="确保计划有明确的起始点"
            )
            issues.append(issue)
            return issues, len(elements), len(elements) - len(issues)
        
        # 查找从起始元素不可达的节点
        reachable_nodes = set()
        for start in start_elements:
            reachable_nodes.update(nx.descendants(dependency_graph, start))
            reachable_nodes.add(start)
        
        unreachable_nodes = set(elements.keys()) - reachable_nodes
        
        for node in unreachable_nodes:
            issue = ValidationIssue(
                issue_id=f"unreachable_{node}",
                issue_type="error",
                severity="high",
                description=f"元素 '{node}' 不可达",
                location=f"element_{node}",
                suggestion="添加从起始元素到该元素的路径，或将其标记为可选"
            )
            issues.append(issue)
        
        elements_checked = len(elements)
        checks_passed = elements_checked - len(issues)
        
        return issues, elements_checked, checks_passed
    
    def _check_dead_end_elements(self, plan: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查死端元素"""
        issues = []
        
        dependency_graph = self._build_dependency_graph(plan)
        elements = plan.get('elements', {})
        
        # 找到结束元素（没有后续元素的元素）
        end_elements = [node for node in dependency_graph.nodes() 
                       if dependency_graph.out_degree(node) == 0]
        
        # 检查是否有明确的目标元素
        goal_elements = [elem_id for elem_id, elem_data in elements.items() 
                        if elem_data.get('is_goal', False)]
        
        dead_end_elements = set(end_elements) - set(goal_elements)
        
        for node in dead_end_elements:
            element_data = elements.get(node, {})
            if not element_data.get('is_acceptable_end', False):
                issue = ValidationIssue(
                    issue_id=f"dead_end_{node}",
                    issue_type="warning",
                    severity="medium",
                    description=f"元素 '{node}' 是死端，没有后续步骤",
                    location=f"element_{node}",
                    suggestion="添加后续步骤或将其标记为可接受的结束点"
                )
                issues.append(issue)
        
        elements_checked = len(elements)
        checks_passed = elements_checked - len(issues)
        
        return issues, elements_checked, checks_passed
    
    def _check_resource_availability(self, plan: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查资源可用性"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        try:
            elements = plan.get('elements', {})
            available_resources = context.get('available_resources', {})
            
            for element_id, element_data in elements.items():
                elements_checked += 1
                
                required_resources = element_data.get('required_resources', {})
                for resource_type, required_amount in required_resources.items():
                    available_amount = available_resources.get(resource_type, 0)
                    
                    if required_amount > available_amount:
                        issue = ValidationIssue(
                            issue_id=f"resource_{element_id}_{resource_type}",
                            issue_type="error",
                            severity="high",
                            description=f"元素 '{element_id}' 需要 {required_amount} {resource_type}，但只有 {available_amount} 可用",
                            location=f"element_{element_id}",
                            suggestion=f"减少资源需求或增加 {resource_type} 资源"
                        )
                        issues.append(issue)
                    else:
                        checks_passed += 1
            
            # 如果没有资源需求，也算通过检查
            if elements_checked > 0 and all(not elements[elem_id].get('required_resources') 
                                          for elem_id in elements):
                checks_passed = elements_checked
        
        except Exception as e:
            self.logger.error(f"资源可用性检查失败: {e}")
        
        return issues, elements_checked, checks_passed
    
    def _check_constraint_satisfaction(self, plan: Dict[str, Any], 
                                     context: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查约束满足"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        try:
            elements = plan.get('elements', {})
            constraints = plan.get('constraints', [])
            
            for constraint in constraints:
                elements_checked += 1
                
                constraint_type = constraint.get('type', '')
                condition = constraint.get('condition', '')
                elements_involved = constraint.get('elements', [])
                
                # 简化的约束检查
                if constraint_type == "temporal" and "before" in condition:
                    # 检查时间顺序约束
                    element1, element2 = self._parse_temporal_constraint(condition)
                    if element1 and element2:
                        if not self._check_temporal_order(plan, element1, element2):
                            issue = ValidationIssue(
                                issue_id=f"temporal_constraint_{len(issues)}",
                                issue_type="error",
                                severity="high",
                                description=f"时间顺序约束违反: {element1} 应该在 {element2} 之前",
                                location="temporal_constraints",
                                suggestion="调整元素顺序或修改约束"
                            )
                            issues.append(issue)
                        else:
                            checks_passed += 1
                
                elif constraint_type == "resource" and "limit" in condition:
                    # 检查资源约束
                    resource_type, limit = self._parse_resource_constraint(condition)
                    if resource_type and limit is not None:
                        total_usage = self._calculate_resource_usage(plan, resource_type)
                        if total_usage > limit:
                            issue = ValidationIssue(
                                issue_id=f"resource_constraint_{len(issues)}",
                                issue_type="error",
                                severity="high",
                                description=f"资源约束违反: {resource_type} 使用量 {total_usage} 超过限制 {limit}",
                                location="resource_constraints",
                                suggestion="优化资源分配或提高资源限制"
                            )
                            issues.append(issue)
                        else:
                            checks_passed += 1
            
            # 如果没有约束，也算通过检查
            if elements_checked == 0:
                checks_passed = 1
        
        except Exception as e:
            self.logger.error(f"约束满足检查失败: {e}")
        
        return issues, elements_checked, checks_passed
    
    def _parse_temporal_constraint(self, condition: str) -> Tuple[Optional[str], Optional[str]]:
        """解析时间约束"""
        # 简化的解析
        if "before" in condition:
            parts = condition.split("before")
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        return None, None
    
    def _parse_resource_constraint(self, condition: str) -> Tuple[Optional[str], Optional[float]]:
        """解析资源约束"""
        # 简化的解析
        if "limit" in condition:
            parts = condition.split("limit")
            if len(parts) == 2:
                resource_type = parts[0].strip()
                try:
                    limit = float(parts[1].strip())
                    return resource_type, limit
                except ValueError:
                    pass
        return None, None
    
    def _check_temporal_order(self, plan: Dict[str, Any], element1: str, element2: str) -> bool:
        """检查时间顺序"""
        dependency_graph = self._build_dependency_graph(plan)
        
        # 检查 element1 是否在 element2 的依赖路径上
        return nx.has_path(dependency_graph, element1, element2)
    
    def _calculate_resource_usage(self, plan: Dict[str, Any], resource_type: str) -> float:
        """计算资源使用量"""
        total_usage = 0.0
        elements = plan.get('elements', {})
        
        for element_data in elements.values():
            required_resources = element_data.get('required_resources', {})
            total_usage += required_resources.get(resource_type, 0)
        
        return total_usage
    
    def _check_temporal_consistency(self, plan: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查时间一致性"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        # 检查时间估计的合理性
        elements = plan.get('elements', {})
        for element_id, element_data in elements.items():
            elements_checked += 1
            
            estimated_duration = element_data.get('estimated_duration')
            if estimated_duration is not None:
                if estimated_duration <= 0:
                    issue = ValidationIssue(
                        issue_id=f"invalid_duration_{element_id}",
                        issue_type="warning",
                        severity="medium",
                        description=f"元素 '{element_id}' 的时间估计无效: {estimated_duration}",
                        location=f"element_{element_id}",
                        suggestion="提供合理的时间估计"
                    )
                    issues.append(issue)
                else:
                    checks_passed += 1
            else:
                # 没有时间估计，发出警告
                issue = ValidationIssue(
                    issue_id=f"missing_duration_{element_id}",
                    issue_type="warning",
                    severity="low",
                    description=f"元素 '{element_id}' 缺少时间估计",
                    location=f"element_{element_id}",
                    suggestion="提供时间估计以便更好的计划"
                )
                issues.append(issue)
        
        return issues, elements_checked, checks_passed
    
    def _check_execution_feasibility(self, plan: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """检查执行可行性"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        elements = plan.get('elements', {})
        capabilities = context.get('available_capabilities', [])
        
        for element_id, element_data in elements.items():
            elements_checked += 1
            
            required_capabilities = element_data.get('required_capabilities', [])
            missing_capabilities = []
            
            for capability in required_capabilities:
                if capability not in capabilities:
                    missing_capabilities.append(capability)
            
            if missing_capabilities:
                issue = ValidationIssue(
                    issue_id=f"missing_capabilities_{element_id}",
                    issue_type="error",
                    severity="high",
                    description=f"元素 '{element_id}' 需要但缺少能力: {', '.join(missing_capabilities)}",
                    location=f"element_{element_id}",
                    suggestion="获取所需能力或修改计划"
                )
                issues.append(issue)
            else:
                checks_passed += 1
        
        return issues, elements_checked, checks_passed
    
    def _check_risk_assessment(self, plan: Dict[str, Any], 
                             context: Dict[str, Any]) -> Tuple[List[ValidationIssue], int, int]:
        """风险评估"""
        issues = []
        elements_checked = 0
        checks_passed = 0
        
        elements = plan.get('elements', {})
        
        for element_id, element_data in elements.items():
            elements_checked += 1
            
            # 检查高风险元素
            risk_level = element_data.get('risk_level', 'low')
            if risk_level in ['high', 'critical']:
                mitigation = element_data.get('risk_mitigation')
                if not mitigation:
                    issue = ValidationIssue(
                        issue_id=f"high_risk_no_mitigation_{element_id}",
                        issue_type="warning",
                        severity="high",
                        description=f"高风险元素 '{element_id}' 缺少风险缓解措施",
                        location=f"element_{element_id}",
                        suggestion="添加风险缓解策略或备用方案"
                    )
                    issues.append(issue)
                else:
                    checks_passed += 1
            else:
                checks_passed += 1
        
        return issues, elements_checked, checks_passed
    
    def _determine_overall_result(self, issues: List[ValidationIssue]) -> ValidationResult:
        """确定总体结果"""
        critical_errors = any(issue.severity == "critical" and issue.issue_type == "error" 
                            for issue in issues)
        high_errors = any(issue.severity == "high" and issue.issue_type == "error" 
                         for issue in issues)
        
        if critical_errors:
            return ValidationResult.ERROR
        elif high_errors:
            return ValidationResult.INVALID
        elif any(issue.issue_type == "warning" for issue in issues):
            return ValidationResult.WARNING
        else:
            return ValidationResult.VALID
    
    def generate_validation_summary(self, report: ValidationReport) -> Dict[str, Any]:
        """生成验证摘要"""
        issue_summary = {}
        for issue in report.issues:
            issue_type = f"{issue.issue_type}_{issue.severity}"
            issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
        
        return {
            "plan_id": report.plan_id,
            "validation_level": report.validation_level.value,
            "overall_result": report.overall_result.value,
            "total_issues": len(report.issues),
            "issue_summary": issue_summary,
            "validation_time": report.validation_time,
            "checked_elements": report.checked_elements,
            "success_rate": report.passed_checks / max(report.checked_elements, 1)
        }
    
    def export_validation_report(self, report: ValidationReport, 
                               format: str = "json") -> Dict[str, Any]:
        """导出验证报告"""
        if format == "json":
            return {
                "plan_id": report.plan_id,
                "validation_level": report.validation_level.value,
                "overall_result": report.overall_result.value,
                "validation_time": report.validation_time,
                "statistics": {
                    "checked_elements": report.checked_elements,
                    "passed_checks": report.passed_checks,
                    "failed_checks": report.failed_checks,
                    "success_rate": report.passed_checks / max(report.checked_elements, 1)
                },
                "issues": [
                    {
                        "id": issue.issue_id,
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "description": issue.description,
                        "location": issue.location,
                        "suggestion": issue.suggestion,
                        "related_elements": issue.related_elements
                    }
                    for issue in report.issues
                ]
            }
        else:
            raise ValueError(f"不支持的格式: {format}")

class ResourceChecker:
    """资源检查器"""
    
    def check_resource_availability(self, required: Dict[str, float], 
                                  available: Dict[str, float]) -> Dict[str, bool]:
        """检查资源可用性"""
        results = {}
        for resource, amount in required.items():
            available_amount = available.get(resource, 0)
            results[resource] = amount <= available_amount
        return results

class DependencyAnalyzer:
    """依赖分析器"""
    
    def analyze_dependencies(self, dependencies: Dict[str, List[str]]) -> Dict[str, Any]:
        """分析依赖关系"""
        graph = nx.DiGraph(dependencies)
        
        return {
            "has_cycles": len(list(nx.simple_cycles(graph))) > 0,
            "start_nodes": [node for node in graph.nodes() if graph.in_degree(node) == 0],
            "end_nodes": [node for node in graph.nodes() if graph.out_degree(node) == 0],
            "dependency_depth": self._calculate_dependency_depth(graph)
        }
    
    def _calculate_dependency_depth(self, graph: nx.DiGraph) -> int:
        """计算依赖深度"""
        if not graph.nodes():
            return 0
        
        # 找到最长的路径
        longest_path = 0
        for node in graph.nodes():
            if graph.in_degree(node) == 0:  # 起始节点
                path_length = self._longest_path_from_node(graph, node)
                longest_path = max(longest_path, path_length)
        
        return longest_path
    
    def _longest_path_from_node(self, graph: nx.DiGraph, start_node: str) -> int:
        """从节点开始的最长路径"""
        visited = set()
        
        def dfs(node, depth):
            visited.add(node)
            max_depth = depth
            for neighbor in graph.successors(node):
                if neighbor not in visited:
                    max_depth = max(max_depth, dfs(neighbor, depth + 1))
            return max_depth
        
        return dfs(start_node, 1)

class ConstraintChecker:
    """约束检查器"""
    
    def check_constraints(self, constraints: List[Dict[str, Any]], 
                        context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查约束"""
        results = []
        
        for constraint in constraints:
            constraint_type = constraint.get('type', '')
            condition = constraint.get('condition', '')
            
            satisfied = self._evaluate_constraint(constraint_type, condition, context)
            
            results.append({
                'constraint_id': constraint.get('id', 'unknown'),
                'type': constraint_type,
                'condition': condition,
                'satisfied': satisfied,
                'message': self._generate_constraint_message(constraint_type, satisfied)
            })
        
        return results
    
    def _evaluate_constraint(self, constraint_type: str, condition: str, 
                           context: Dict[str, Any]) -> bool:
        """评估约束"""
        # 简化的约束评估
        if constraint_type == "resource":
            return self._evaluate_resource_constraint(condition, context)
        elif constraint_type == "temporal":
            return self._evaluate_temporal_constraint(condition, context)
        else:
            return True  # 未知约束类型默认满足
    
    def _evaluate_resource_constraint(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估资源约束"""
        # 简化的资源约束评估
        if "limit" in condition:
            parts = condition.split("limit")
            if len(parts) == 2:
                resource_type = parts[0].strip()
                try:
                    limit = float(parts[1].strip())
                    current_usage = context.get('resource_usage', {}).get(resource_type, 0)
                    return current_usage <= limit
                except ValueError:
                    pass
        return True
    
    def _evaluate_temporal_constraint(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估时间约束"""
        # 简化的时间约束评估
        return True  # 在实际实现中应该进行更复杂的检查
    
    def _generate_constraint_message(self, constraint_type: str, satisfied: bool) -> str:
        """生成约束消息"""
        if satisfied:
            return f"{constraint_type}约束满足"
        else:
            return f"{constraint_type}约束违反"

