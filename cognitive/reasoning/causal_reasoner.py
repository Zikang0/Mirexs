"""
因果推理器 - 因果关系推理和分析
识别因果链、进行反事实推理和因果推断
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx
from collections import defaultdict
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

class CausalRelationship(Enum):
    """因果关系类型枚举"""
    DIRECT_CAUSE = "direct_cause"  # 直接原因
    INDIRECT_CAUSE = "indirect_cause"  # 间接原因
    CONTRIBUTING_FACTOR = "contributing_factor"  # 贡献因素
    CORRELATION = "correlation"  # 相关性
    SPURIOUS = "spurious"  # 伪相关

class EvidenceStrength(Enum):
    """证据强度枚举"""
    WEAK = "weak"  # 弱证据
    MODERATE = "moderate"  # 中等证据
    STRONG = "strong"  # 强证据
    CONCLUSIVE = "conclusive"  # 决定性证据

@dataclass
class CausalClaim:
    """因果声明"""
    cause: str
    effect: str
    relationship: CausalRelationship
    confidence: float  # 置信度 0-1
    evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)
    strength: EvidenceStrength = EvidenceStrength.WEAK

@dataclass
class CausalAnalysis:
    """因果分析结果"""
    event: str
    possible_causes: List[CausalClaim]
    likely_causes: List[CausalClaim]
    contributing_factors: List[CausalClaim]
    causal_graph: Any  # 因果图
    recommendations: List[str]

@dataclass
class CounterfactualScenario:
    """反事实场景"""
    scenario_id: str
    original_event: str
    modified_conditions: Dict[str, Any]
    predicted_outcome: str
    probability: float
    reasoning: str

class CausalReasoner:
    """因果推理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.causal_knowledge_base = self._initialize_knowledge_base()
        self.causal_graph = nx.DiGraph()
        self.causal_patterns = self._load_causal_patterns()
        self.counterfactual_engine = CounterfactualEngine()
        
        # 统计测试配置
        self.significance_level = 0.05
        self.min_correlation_threshold = 0.3
        
        self.logger.info("因果推理器初始化完成")
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """初始化知识库"""
        return {
            "common_causes": {
                "软件错误": ["代码缺陷", "测试不足", "需求变更"],
                "性能下降": ["资源不足", "配置错误", "数据量增加"],
                "安全漏洞": ["未及时更新", "配置错误", "输入验证不足"]
            },
            "causal_mechanisms": {
                "代码缺陷 -> 软件错误": "逻辑错误导致异常行为",
                "资源不足 -> 性能下降": "系统资源不足以处理负载",
                "未及时更新 -> 安全漏洞": "已知漏洞未被修复"
            },
            "domain_knowledge": {
                "技术": ["软件", "硬件", "网络", "安全"],
                "业务": ["流程", "人员", "管理", "市场"],
                "环境": ["时间", "位置", "条件", "约束"]
            }
        }
    
    def _load_causal_patterns(self) -> Dict[str, Any]:
        """加载因果模式"""
        return {
            "temporal_precedence": r"(.+)之后(.+)发生",
            "necessary_condition": r"只有(.+)才(.+)",
            "sufficient_condition": r"只要(.+)就(.+)",
            "mechanism": r"(.+)通过(.+)导致(.+)",
            "intervention": r"改变(.+)会影响(.+)"
        }
    
    def analyze_causality(self, event: str, context: Dict[str, Any] = None) -> CausalAnalysis:
        """
        分析事件的因果关系
        
        Args:
            event: 待分析的事件
            context: 上下文信息
            
        Returns:
            CausalAnalysis: 因果分析结果
        """
        self.logger.info(f"开始因果分析: {event}")
        
        if context is None:
            context = {}
        
        # 1. 识别可能的原因
        possible_causes = self._identify_possible_causes(event, context)
        
        # 2. 评估因果关系强度
        likely_causes = self._evaluate_causal_strength(possible_causes, event, context)
        
        # 3. 识别贡献因素
        contributing_factors = self._identify_contributing_factors(likely_causes, context)
        
        # 4. 构建因果图
        causal_graph = self._build_causal_graph(event, likely_causes, contributing_factors)
        
        # 5. 生成建议
        recommendations = self._generate_recommendations(likely_causes, contributing_factors)
        
        analysis = CausalAnalysis(
            event=event,
            possible_causes=possible_causes,
            likely_causes=likely_causes,
            contributing_factors=contributing_factors,
            causal_graph=causal_graph,
            recommendations=recommendations
        )
        
        self.logger.info(f"因果分析完成，找到 {len(likely_causes)} 个可能原因")
        return analysis
    
    def _identify_possible_causes(self, event: str, context: Dict[str, Any]) -> List[CausalClaim]:
        """识别可能的原因"""
        possible_causes = []
        
        # 从知识库中获取常见原因
        for effect_type, causes in self.causal_knowledge_base["common_causes"].items():
            if self._is_similar_event(event, effect_type):
                for cause in causes:
                    claim = CausalClaim(
                        cause=cause,
                        effect=event,
                        relationship=CausalRelationship.DIRECT_CAUSE,
                        confidence=0.5,  # 初始置信度
                        evidence=[f"知识库匹配: {effect_type}"],
                        strength=EvidenceStrength.MODERATE
                    )
                    possible_causes.append(claim)
        
        # 从上下文中提取可能原因
        if "related_events" in context:
            for related_event in context["related_events"]:
                if self._has_temporal_precedence(related_event, event, context):
                    claim = CausalClaim(
                        cause=related_event,
                        effect=event,
                        relationship=CausalRelationship.DIRECT_CAUSE,
                        confidence=0.3,
                        evidence=["时间先后关系"],
                        strength=EvidenceStrength.WEAK
                    )
                    possible_causes.append(claim)
        
        # 使用因果模式匹配
        text_analysis = self._analyze_text_for_causality(event, context)
        possible_causes.extend(text_analysis)
        
        return possible_causes
    
    def _is_similar_event(self, event1: str, event2: str) -> bool:
        """判断事件是否相似"""
        # 简单的关键词匹配
        words1 = set(re.findall(r'\w+', event1.lower()))
        words2 = set(re.findall(r'\w+', event2.lower()))
        
        common_words = words1.intersection(words2)
        similarity = len(common_words) / max(len(words1), len(words2))
        
        return similarity > 0.3
    
    def _has_temporal_precedence(self, cause: str, effect: str, context: Dict[str, Any]) -> bool:
        """判断是否有时间先后关系"""
        if "timeline" not in context:
            return False
        
        timeline = context["timeline"]
        cause_time = timeline.get(cause)
        effect_time = timeline.get(effect)
        
        if cause_time and effect_time:
            return cause_time < effect_time
        
        return False
    
    def _analyze_text_for_causality(self, event: str, context: Dict[str, Any]) -> List[CausalClaim]:
        """从文本中分析因果关系"""
        claims = []
        text = event + " " + context.get("description", "")
        
        for pattern_name, pattern in self.causal_patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    cause, effect = match
                elif len(match) == 3:
                    cause, mechanism, effect = match
                else:
                    continue
                
                claim = CausalClaim(
                    cause=cause.strip(),
                    effect=effect.strip(),
                    relationship=CausalRelationship.DIRECT_CAUSE,
                    confidence=0.4,
                    evidence=[f"文本模式匹配: {pattern_name}"],
                    strength=EvidenceStrength.WEAK
                )
                claims.append(claim)
        
        return claims
    
    def _evaluate_causal_strength(self, possible_causes: List[CausalClaim], 
                                event: str, context: Dict[str, Any]) -> List[CausalClaim]:
        """评估因果关系强度"""
        evaluated_causes = []
        
        for claim in possible_causes:
            # 评估置信度
            confidence = self._calculate_causal_confidence(claim, event, context)
            claim.confidence = confidence
            
            # 确定证据强度
            if confidence >= 0.8:
                claim.strength = EvidenceStrength.CONCLUSIVE
            elif confidence >= 0.6:
                claim.strength = EvidenceStrength.STRONG
            elif confidence >= 0.4:
                claim.strength = EvidenceStrength.MODERATE
            else:
                claim.strength = EvidenceStrength.WEAK
            
            # 只保留置信度足够高的原因
            if confidence >= 0.3:
                evaluated_causes.append(claim)
        
        # 按置信度排序
        evaluated_causes.sort(key=lambda x: x.confidence, reverse=True)
        
        return evaluated_causes
    
    def _calculate_causal_confidence(self, claim: CausalClaim, event: str, 
                                   context: Dict[str, Any]) -> float:
        """计算因果置信度"""
        confidence = 0.0
        
        # 1. 知识库匹配得分
        if any(self._is_similar_event(claim.cause, known_cause) 
               for known_cause in self.causal_knowledge_base["common_causes"].get(event, [])):
            confidence += 0.3
        
        # 2. 时间关系得分
        if self._has_temporal_precedence(claim.cause, event, context):
            confidence += 0.2
        
        # 3. 机制解释得分
        mechanism_key = f"{claim.cause} -> {event}"
        if mechanism_key in self.causal_knowledge_base["causal_mechanisms"]:
            confidence += 0.2
            claim.evidence.append(f"机制解释: {self.causal_knowledge_base['causal_mechanisms'][mechanism_key]}")
        
        # 4. 统计相关性得分（如果有数据）
        if "data" in context:
            correlation_score = self._calculate_statistical_correlation(claim.cause, event, context["data"])
            confidence += correlation_score * 0.3
        
        return min(confidence, 1.0)
    
    def _calculate_statistical_correlation(self, cause: str, effect: str, data: Dict[str, Any]) -> float:
        """计算统计相关性"""
        # 简化的相关性计算
        # 在实际实现中，应该使用真实的数据分析
        
        if cause not in data or effect not in data:
            return 0.0
        
        cause_data = data[cause]
        effect_data = data[effect]
        
        if len(cause_data) != len(effect_data) or len(cause_data) < 2:
            return 0.0
        
        try:
            correlation, p_value = stats.pearsonr(cause_data, effect_data)
            
            if p_value < self.significance_level and abs(correlation) > self.min_correlation_threshold:
                return abs(correlation)
            else:
                return 0.0
                
        except Exception as e:
            self.logger.warning(f"相关性计算失败: {e}")
            return 0.0
    
    def _identify_contributing_factors(self, likely_causes: List[CausalClaim], 
                                     context: Dict[str, Any]) -> List[CausalClaim]:
        """识别贡献因素"""
        contributing_factors = []
        
        # 从上下文中识别环境因素
        if "environment" in context:
            for factor, value in context["environment"].items():
                claim = CausalClaim(
                    cause=factor,
                    effect=context.get("main_event", "事件"),
                    relationship=CausalRelationship.CONTRIBUTING_FACTOR,
                    confidence=0.2,
                    evidence=[f"环境因素: {value}"],
                    strength=EvidenceStrength.WEAK
                )
                contributing_factors.append(claim)
        
        return contributing_factors
    
    def _build_causal_graph(self, event: str, likely_causes: List[CausalClaim],
                          contributing_factors: List[CausalClaim]) -> nx.DiGraph:
        """构建因果图"""
        graph = nx.DiGraph()
        
        # 添加主要事件
        graph.add_node(event, type="event")
        
        # 添加原因节点和边
        for claim in likely_causes:
            graph.add_node(claim.cause, type="cause", confidence=claim.confidence)
            graph.add_edge(claim.cause, event, 
                         relationship=claim.relationship.value,
                         confidence=claim.confidence)
        
        # 添加贡献因素
        for factor in contributing_factors:
            graph.add_node(factor.cause, type="factor", confidence=factor.confidence)
            graph.add_edge(factor.cause, event,
                         relationship=factor.relationship.value,
                         confidence=factor.confidence)
        
        return graph
    
    def _generate_recommendations(self, likely_causes: List[CausalClaim],
                               contributing_factors: List[CausalClaim]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 针对主要原因的建议
        for cause in likely_causes[:3]:  # 只处理前3个最可能的原因
            if cause.confidence > 0.5:
                recommendation = f"解决根本原因: {cause.cause}"
                recommendations.append(recommendation)
        
        # 针对贡献因素的建议
        for factor in contributing_factors:
            if "环境" in factor.cause or "条件" in factor.cause:
                recommendation = f"优化环境因素: {factor.cause}"
                recommendations.append(recommendation)
        
        # 预防性建议
        if len(likely_causes) > 0:
            recommendations.append("建立监控机制检测类似原因")
            recommendations.append("实施根本原因分析流程")
        
        return recommendations
    
    def perform_counterfactual_analysis(self, event: str, 
                                      changed_conditions: Dict[str, Any],
                                      context: Dict[str, Any]) -> CounterfactualScenario:
        """
        执行反事实分析
        
        Args:
            event: 原始事件
            changed_conditions: 改变的条件
            context: 上下文信息
            
        Returns:
            CounterfactualScenario: 反事实场景
        """
        self.logger.info(f"执行反事实分析: {event}")
        
        # 使用反事实引擎进行分析
        scenario = self.counterfactual_engine.analyze_scenario(
            event, changed_conditions, context
        )
        
        return scenario
    
    def identify_causal_chain(self, start_event: str, end_event: str, 
                            max_depth: int = 5) -> List[List[str]]:
        """
        识别因果链
        
        Args:
            start_event: 起始事件
            end_event: 结束事件
            max_depth: 最大深度
            
        Returns:
            List[List[str]]: 因果链列表
        """
        if start_event not in self.causal_graph or end_event not in self.causal_graph:
            return []
        
        try:
            # 查找所有路径
            all_paths = list(nx.all_simple_paths(
                self.causal_graph, start_event, end_event, cutoff=max_depth
            ))
            
            # 按路径长度排序
            all_paths.sort(key=len)
            
            return all_paths
            
        except nx.NetworkXNoPath:
            self.logger.info(f"未找到从 {start_event} 到 {end_event} 的因果路径")
            return []
    
    def calculate_causal_impact(self, intervention: str, outcome: str,
                              context: Dict[str, Any]) -> float:
        """
        计算因果影响
        
        Args:
            intervention: 干预措施
            outcome: 结果
            context: 上下文信息
            
        Returns:
            float: 影响程度 (0-1)
        """
        # 简化的因果影响计算
        # 在实际实现中，应该使用更复杂的方法如do-calculus
        
        impact = 0.0
        
        # 检查是否存在直接因果关系
        if self.causal_graph.has_edge(intervention, outcome):
            edge_data = self.causal_graph[intervention][outcome]
            impact = edge_data.get('confidence', 0.0)
        
        # 考虑间接影响
        paths = self.identify_causal_chain(intervention, outcome, max_depth=3)
        for path in paths:
            if len(path) > 2:  # 间接路径
                path_confidence = 1.0
                for i in range(len(path) - 1):
                    edge_data = self.causal_graph[path[i]][path[i+1]]
                    path_confidence *= edge_data.get('confidence', 0.0)
                
                impact = max(impact, path_confidence * 0.7)  # 间接影响折扣
        
        return impact

class CounterfactualEngine:
    """反事实推理引擎"""
    
    def analyze_scenario(self, original_event: str, 
                       changed_conditions: Dict[str, Any],
                       context: Dict[str, Any]) -> CounterfactualScenario:
        """分析反事实场景"""
        
        # 生成场景ID
        scenario_id = f"counterfactual_{hash(str(changed_conditions))}"
        
        # 预测结果（简化实现）
        predicted_outcome = self._predict_outcome(original_event, changed_conditions, context)
        
        # 计算概率
        probability = self._calculate_probability(original_event, changed_conditions, context)
        
        # 生成推理过程
        reasoning = self._generate_reasoning(original_event, changed_conditions, predicted_outcome)
        
        scenario = CounterfactualScenario(
            scenario_id=scenario_id,
            original_event=original_event,
            modified_conditions=changed_conditions,
            predicted_outcome=predicted_outcome,
            probability=probability,
            reasoning=reasoning
        )
        
        return scenario
    
    def _predict_outcome(self, original_event: str, changed_conditions: Dict[str, Any],
                       context: Dict[str, Any]) -> str:
        """预测结果"""
        # 简化的预测逻辑
        if "prevent" in changed_conditions or "fix" in changed_conditions:
            return "问题避免或解决"
        elif "worsen" in changed_conditions or "amplify" in changed_conditions:
            return "问题加剧"
        else:
            return "情况类似但有所不同"
    
    def _calculate_probability(self, original_event: str, changed_conditions: Dict[str, Any],
                             context: Dict[str, Any]) -> float:
        """计算概率"""
        # 简化的概率计算
        base_probability = 0.5
        
        # 基于改变的条件调整概率
        if len(changed_conditions) == 1:
            return 0.7
        elif len(changed_conditions) > 1:
            return 0.3
        else:
            return base_probability
    
    def _generate_reasoning(self, original_event: str, changed_conditions: Dict[str, Any],
                          predicted_outcome: str) -> str:
        """生成推理过程"""
        reasoning_parts = []
        
        for condition, change in changed_conditions.items():
            reasoning_parts.append(f"如果{condition}变为{change}")
        
        reasoning_parts.append(f"那么{original_event}可能会{predicted_outcome}")
        
        return "。".join(reasoning_parts)

