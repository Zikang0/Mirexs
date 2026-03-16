"""
逻辑推理器 - 逻辑推理能力
实现基于规则的推理、演绎推理和归纳推理
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sympy
from sympy.logic.boolalg import to_cnf, And, Or, Not, Implies, Equivalent
from sympy.logic.inference import satisfiable

logger = logging.getLogger(__name__)

class LogicType(Enum):
    """逻辑类型枚举"""
    PROPOSITIONAL = "propositional"  # 命题逻辑
    FIRST_ORDER = "first_order"  # 一阶逻辑
    TEMPORAL = "temporal"  # 时序逻辑
    FUZZY = "fuzzy"  # 模糊逻辑

class InferenceMethod(Enum):
    """推理方法枚举"""
    DEDUCTION = "deduction"  # 演绎推理
    INDUCTION = "induction"  # 归纳推理
    ABDUCTION = "abduction"  # 溯因推理
    DEFAULT = "default"  # 默认推理

@dataclass
class LogicalStatement:
    """逻辑语句"""
    statement_id: str
    content: str
    logic_type: LogicType
    truth_value: Optional[bool] = None
    confidence: float = 1.0  # 置信度 0-1
    source: str = "user"  # 来源
    dependencies: List[str] = field(default_factory=list)  # 依赖的语句ID

@dataclass
class InferenceResult:
    """推理结果"""
    conclusion: str
    method: InferenceMethod
    confidence: float
    supporting_evidence: List[str]
    contradictory_evidence: List[str]
    derivation_steps: List[str]

@dataclass
class LogicalContext:
    """逻辑上下文"""
    statements: Dict[str, LogicalStatement]
    rules: List[str]
    assumptions: List[str]
    contradictions: List[Tuple[str, str]]  # 矛盾语句对

class LogicalReasoner:
    """逻辑推理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.knowledge_base = self._initialize_knowledge_base()
        self.inference_rules = self._load_inference_rules()
        self.logic_parser = LogicParser()
        self.context = LogicalContext(
            statements={},
            rules=[],
            assumptions=[],
            contradictions=[]
        )
        
        self.logger.info("逻辑推理器初始化完成")
    
    def _initialize_knowledge_base(self) -> Dict[str, Any]:
        """初始化知识库"""
        return {
            "propositional_rules": [
                "P ∧ Q → P",  # 合取消除
                "P → P ∨ Q",  # 析取引入
                "(P → Q) ∧ P → Q",  # 假言推理
                "(P → Q) ∧ ¬Q → ¬P"  # 否定后件
            ],
            "domain_axioms": {
                "technology": [
                    "软件缺陷 → 系统故障",
                    "资源不足 → 性能下降",
                    "安全漏洞 → 风险增加"
                ],
                "business": [
                    "需求增加 → 工作量增加",
                    "效率提高 → 成本降低",
                    "质量改进 → 客户满意"
                ]
            },
            "common_sense": [
                "原因发生在结果之前",
                "相同原因导致相似结果",
                "异常需要解释"
            ]
        }
    
    def _load_inference_rules(self) -> Dict[str, Any]:
        """加载推理规则"""
        return {
            "modus_ponens": {
                "pattern": ["P → Q", "P"],
                "conclusion": "Q"
            },
            "modus_tollens": {
                "pattern": ["P → Q", "¬Q"],
                "conclusion": "¬P"
            },
            "hypothetical_syllogism": {
                "pattern": ["P → Q", "Q → R"],
                "conclusion": "P → R"
            },
            "disjunctive_syllogism": {
                "pattern": ["P ∨ Q", "¬P"],
                "conclusion": "Q"
            },
            "addition": {
                "pattern": ["P"],
                "conclusion": "P ∨ Q"
            },
            "simplification": {
                "pattern": ["P ∧ Q"],
                "conclusion": "P"
            }
        }
    
    def add_statement(self, statement: LogicalStatement) -> bool:
        """
        添加逻辑语句
        
        Args:
            statement: 逻辑语句
            
        Returns:
            bool: 是否成功添加
        """
        # 检查是否与现有语句矛盾
        contradictions = self._check_contradictions(statement)
        if contradictions:
            self.logger.warning(f"语句与现有知识矛盾: {statement.content}")
            for contras in contradictions:
                self.context.contradictions.append((statement.statement_id, contras))
            return False
        
        self.context.statements[statement.statement_id] = statement
        self.logger.info(f"添加逻辑语句: {statement.content}")
        
        # 触发自动推理
        self._trigger_automatic_inference(statement)
        
        return True
    
    def _check_contradictions(self, new_statement: LogicalStatement) -> List[str]:
        """检查矛盾"""
        contradictions = []
        
        for stmt_id, existing_stmt in self.context.statements.items():
            if self._are_contradictory(new_statement, existing_stmt):
                contradictions.append(stmt_id)
        
        return contradictions
    
    def _are_contradictory(self, stmt1: LogicalStatement, stmt2: LogicalStatement) -> bool:
        """判断两个语句是否矛盾"""
        # 简化的矛盾检查
        content1 = stmt1.content.lower()
        content2 = stmt2.content.lower()
        
        # 检查明显的否定关系
        if (f"¬{content2}" in content1 or f"not {content2}" in content1 or
            f"¬{content1}" in content2 or f"not {content1}" in content2):
            return True
        
        # 检查真值冲突
        if (stmt1.truth_value is not None and stmt2.truth_value is not None and
            stmt1.truth_value != stmt2.truth_value and
            self._are_equivalent(content1, content2)):
            return True
        
        return False
    
    def _are_equivalent(self, content1: str, content2: str) -> bool:
        """判断两个内容是否等价"""
        # 简化的等价性检查
        return (content1 == content2 or 
                content1.replace(" ", "") == content2.replace(" ", ""))
    
    def _trigger_automatic_inference(self, new_statement: LogicalStatement):
        """触发自动推理"""
        # 应用推理规则
        for rule_name, rule in self.inference_rules.items():
            if self._can_apply_rule(rule, new_statement):
                conclusion = self._apply_rule(rule, new_statement)
                if conclusion:
                    self.logger.info(f"自动推理得到结论: {conclusion}")
    
    def _can_apply_rule(self, rule: Dict[str, Any], new_statement: LogicalStatement) -> bool:
        """检查是否可以应用规则"""
        pattern = rule["pattern"]
        
        # 检查新语句是否匹配模式的某一部分
        for pattern_part in pattern:
            if self._matches_pattern(new_statement.content, pattern_part):
                # 检查其他部分是否在知识库中
                other_parts = [p for p in pattern if p != pattern_part]
                if all(self._has_matching_statement(p) for p in other_parts):
                    return True
        
        return False
    
    def _matches_pattern(self, content: str, pattern: str) -> bool:
        """检查内容是否匹配模式"""
        # 简化的模式匹配
        pattern_clean = pattern.replace("→", "->").replace("∧", "&").replace("∨", "|")
        content_clean = content.replace("→", "->").replace("∧", "&").replace("∨", "|")
        
        return pattern_clean in content_clean or content_clean in pattern_clean
    
    def _has_matching_statement(self, pattern: str) -> bool:
        """检查是否有匹配的语句"""
        for statement in self.context.statements.values():
            if self._matches_pattern(statement.content, pattern):
                return True
        return False
    
    def _apply_rule(self, rule: Dict[str, Any], new_statement: LogicalStatement) -> Optional[str]:
        """应用推理规则"""
        try:
            # 获取匹配的语句
            matching_statements = [new_statement]
            for pattern_part in rule["pattern"]:
                if not self._matches_pattern(new_statement.content, pattern_part):
                    for stmt in self.context.statements.values():
                        if self._matches_pattern(stmt.content, pattern_part):
                            matching_statements.append(stmt)
                            break
            
            if len(matching_statements) == len(rule["pattern"]):
                conclusion = rule["conclusion"]
                
                # 创建新语句
                new_stmt_id = f"inferred_{len(self.context.statements) + 1}"
                inferred_stmt = LogicalStatement(
                    statement_id=new_stmt_id,
                    content=conclusion,
                    logic_type=LogicType.PROPOSITIONAL,
                    confidence=min(s.confidence for s in matching_statements) * 0.9,  # 推理降低置信度
                    source="inference",
                    dependencies=[s.statement_id for s in matching_statements]
                )
                
                self.add_statement(inferred_stmt)
                return conclusion
        
        except Exception as e:
            self.logger.error(f"应用推理规则失败: {e}")
        
        return None
    
    def deduce(self, premises: List[str], goal: str) -> InferenceResult:
        """
        演绎推理
        
        Args:
            premises: 前提列表
            goal: 目标结论
            
        Returns:
            InferenceResult: 推理结果
        """
        self.logger.info(f"开始演绎推理: {goal}")
        
        derivation_steps = []
        supporting_evidence = []
        contradictory_evidence = []
        
        # 将前提转换为逻辑语句
        premise_statements = []
        for i, premise in enumerate(premises):
            stmt_id = f"premise_{i}"
            statement = LogicalStatement(
                statement_id=stmt_id,
                content=premise,
                logic_type=LogicType.PROPOSITIONAL,
                truth_value=True,
                source="deduction_premise"
            )
            premise_statements.append(statement)
            supporting_evidence.append(premise)
        
        # 尝试证明目标
        proven, proof_steps = self._prove_goal(premise_statements, goal)
        
        if proven:
            confidence = 0.95  # 演绎推理置信度高
            derivation_steps = proof_steps
            conclusion = f"已证明: {goal}"
        else:
            confidence = 0.3  # 未证明的置信度低
            conclusion = f"无法证明: {goal}"
        
        result = InferenceResult(
            conclusion=conclusion,
            method=InferenceMethod.DEDUCTION,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            contradictory_evidence=contradictory_evidence,
            derivation_steps=derivation_steps
        )
        
        self.logger.info(f"演绎推理完成: {conclusion}")
        return result
    
    def _prove_goal(self, premises: List[LogicalStatement], goal: str) -> Tuple[bool, List[str]]:
        """证明目标"""
        proof_steps = []
        
        # 简化的证明过程
        # 在实际实现中应该使用定理证明器
        
        # 检查目标是否直接是前提
        for premise in premises:
            if self._are_equivalent(premise.content, goal):
                proof_steps.append(f"目标 '{goal}' 是前提之一")
                return True, proof_steps
        
        # 检查是否可以通过推理规则得到
        all_statements = list(premises)
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            new_statements = []
            
            for statement in all_statements:
                # 临时添加到上下文以触发推理
                temp_id = f"temp_{iteration}_{len(new_statements)}"
                temp_stmt = LogicalStatement(
                    statement_id=temp_id,
                    content=statement.content,
                    logic_type=statement.logic_type,
                    truth_value=statement.truth_value,
                    confidence=statement.confidence,
                    source="temp"
                )
                
                # 应用推理规则
                for rule_name, rule in self.inference_rules.items():
                    if self._can_apply_rule(rule, temp_stmt):
                        conclusion = self._apply_rule_to_single(rule, temp_stmt, all_statements)
                        if conclusion and conclusion not in [s.content for s in all_statements + new_statements]:
                            new_stmt = LogicalStatement(
                                statement_id=f"inferred_{len(new_statements)}",
                                content=conclusion,
                                logic_type=LogicType.PROPOSITIONAL,
                                confidence=temp_stmt.confidence * 0.9,
                                source="inference"
                            )
                            new_statements.append(new_stmt)
                            proof_steps.append(f"应用 {rule_name}: 从 '{temp_stmt.content}' 得到 '{conclusion}'")
                            
                            # 检查是否达到目标
                            if self._are_equivalent(conclusion, goal):
                                return True, proof_steps
            
            if not new_statements:
                break  # 没有新语句产生
            
            all_statements.extend(new_statements)
            iteration += 1
        
        return False, proof_steps
    
    def _apply_rule_to_single(self, rule: Dict[str, Any], statement: LogicalStatement, 
                            all_statements: List[LogicalStatement]) -> Optional[str]:
        """对单个语句应用规则"""
        pattern = rule["pattern"]
        
        # 找到匹配的其他部分
        other_parts = []
        for pattern_part in pattern:
            if not self._matches_pattern(statement.content, pattern_part):
                found = False
                for stmt in all_statements:
                    if self._matches_pattern(stmt.content, pattern_part):
                        other_parts.append(stmt)
                        found = True
                        break
                if not found:
                    return None
        
        # 所有部分都找到，可以应用规则
        return rule["conclusion"]
    
    def induce(self, observations: List[str], pattern_type: str = "general") -> InferenceResult:
        """
        归纳推理
        
        Args:
            observations: 观察列表
            pattern_type: 模式类型
            
        Returns:
            InferenceResult: 推理结果
        """
        self.logger.info(f"开始归纳推理，观察数量: {len(observations)}")
        
        # 分析观察中的模式
        patterns = self._analyze_patterns(observations, pattern_type)
        
        if patterns:
            # 生成一般性结论
            general_conclusion = self._generalize_patterns(patterns, observations)
            confidence = self._calculate_induction_confidence(len(observations), patterns)
            
            result = InferenceResult(
                conclusion=general_conclusion,
                method=InferenceMethod.INDUCTION,
                confidence=confidence,
                supporting_evidence=observations[:3],  # 只取前3个作为证据
                contradictory_evidence=[],
                derivation_steps=[f"从 {len(observations)} 个观察中识别出模式: {', '.join(patterns)}"]
            )
        else:
            result = InferenceResult(
                conclusion="未发现明显的模式",
                method=InferenceMethod.INDUCTION,
                confidence=0.1,
                supporting_evidence=observations[:2],
                contradictory_evidence=[],
                derivation_steps=["观察数据中没有发现明显的模式"]
            )
        
        self.logger.info(f"归纳推理完成: {result.conclusion}")
        return result
    
    def _analyze_patterns(self, observations: List[str], pattern_type: str) -> List[str]:
        """分析模式"""
        patterns = []
        
        if len(observations) < 2:
            return patterns
        
        # 提取共同特征
        common_words = self._find_common_words(observations)
        if common_words:
            patterns.append(f"共同词汇: {', '.join(common_words)}")
        
        # 分析结构模式
        structural_patterns = self._analyze_structural_patterns(observations)
        patterns.extend(structural_patterns)
        
        return patterns
    
    def _find_common_words(self, texts: List[str]) -> List[str]:
        """查找共同词汇"""
        if not texts:
            return []
        
        # 分词并统计频率
        word_freq = {}
        for text in texts:
            words = re.findall(r'\w+', text.lower())
            for word in set(words):  # 每个文本中的词汇只计一次
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 返回出现频率高的词汇
        threshold = len(texts) * 0.7  # 在70%的文本中出现
        common_words = [word for word, freq in word_freq.items() 
                       if freq >= threshold and len(word) > 1]
        
        return common_words
    
    def _analyze_structural_patterns(self, observations: List[str]) -> List[str]:
        """分析结构模式"""
        patterns = []
        
        # 检查是否有相似句式
        if len(observations) >= 3:
            # 简化的结构分析
            first_obs = observations[0]
            if all(obs.startswith(first_obs.split()[0]) for obs in observations[1:3]):
                patterns.append("相似的句子开头")
            
            if all(obs.endswith(first_obs.split()[-1]) for obs in observations[1:3]):
                patterns.append("相似的句子结尾")
        
        return patterns
    
    def _generalize_patterns(self, patterns: List[str], observations: List[str]) -> str:
        """泛化模式"""
        if "共同词汇" in patterns[0]:
            common_words = patterns[0].replace("共同词汇: ", "").split(", ")
            return f"这些观察都涉及: {', '.join(common_words[:3])}"
        
        return "观察显示了一种重复出现的模式"
    
    def _calculate_induction_confidence(self, observation_count: int, patterns: List[str]) -> float:
        """计算归纳推理置信度"""
        base_confidence = min(observation_count / 10, 0.8)  # 每10个观察增加置信度
        
        # 模式数量和质量的影响
        pattern_bonus = len(patterns) * 0.1
        pattern_quality = 1.0 if any("共同" in p for p in patterns) else 0.5
        
        confidence = base_confidence * pattern_quality + pattern_bonus
        return min(confidence, 0.95)
    
    def abduce(self, observation: str, possible_explanations: List[str]) -> InferenceResult:
        """
        溯因推理
        
        Args:
            observation: 观察现象
            possible_explanations: 可能的解释列表
            
        Returns:
            InferenceResult: 推理结果
        """
        self.logger.info(f"开始溯因推理: {observation}")
        
        # 评估每个解释的合理性
        scored_explanations = []
        for explanation in possible_explanations:
            score = self._evaluate_explanation(explanation, observation)
            scored_explanations.append((explanation, score))
        
        # 选择最佳解释
        scored_explanations.sort(key=lambda x: x[1], reverse=True)
        best_explanation, best_score = scored_explanations[0] if scored_explanations else ("", 0)
        
        confidence = best_score
        supporting_evidence = [f"解释 '{best_explanation}' 与观察 '{observation}' 一致"]
        
        result = InferenceResult(
            conclusion=f"最可能的解释: {best_explanation}",
            method=InferenceMethod.ABDUCTION,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
            contradictory_evidence=[],
            derivation_steps=[f"评估了 {len(possible_explanations)} 个可能解释"]
        )
        
        self.logger.info(f"溯因推理完成: {result.conclusion}")
        return result
    
    def _evaluate_explanation(self, explanation: str, observation: str) -> float:
        """评估解释的合理性"""
        score = 0.0
        
        # 1. 解释与观察的相关性
        explanation_words = set(re.findall(r'\w+', explanation.lower()))
        observation_words = set(re.findall(r'\w+', observation.lower()))
        common_words = explanation_words.intersection(observation_words)
        
        if common_words:
            word_similarity = len(common_words) / len(observation_words)
            score += word_similarity * 0.4
        
        # 2. 解释的简洁性（奥卡姆剃刀）
        simplicity = 1.0 / (len(explanation.split()) + 1)
        score += simplicity * 0.3
        
        # 3. 与现有知识的一致性
        consistency_score = self._check_consistency(explanation)
        score += consistency_score * 0.3
        
        return min(score, 1.0)
    
    def _check_consistency(self, explanation: str) -> float:
        """检查与现有知识的一致性"""
        # 简化的检查
        for stmt in self.context.statements.values():
            if stmt.truth_value is True and self._are_contradictory_text(explanation, stmt.content):
                return 0.0
        
        return 0.8  # 默认较高一致性
    
    def _are_contradictory_text(self, text1: str, text2: str) -> bool:
        """检查两个文本是否矛盾"""
        # 简化的矛盾检查
        negative_indicators = ["不", "没", "无", "非", "错误", "失败", "问题"]
        positive_indicators = ["是", "有", "成功", "正确", "正常"]
        
        has_negative1 = any(indicator in text1 for indicator in negative_indicators)
        has_negative2 = any(indicator in text2 for indicator in negative_indicators)
        has_positive1 = any(indicator in text1 for indicator in positive_indicators)
        has_positive2 = any(indicator in text2 for indicator in positive_indicators)
        
        return ((has_negative1 and has_positive2 and self._are_about_same_topic(text1, text2)) or
                (has_positive1 and has_negative2 and self._are_about_same_topic(text1, text2)))
    
    def _are_about_same_topic(self, text1: str, text2: str) -> bool:
        """检查两个文本是否关于同一主题"""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        common_words = words1.intersection(words2)
        
        return len(common_words) >= 2  # 至少有2个共同词汇
    
    def check_consistency(self) -> List[Tuple[str, str]]:
        """检查知识库一致性"""
        inconsistencies = []
        
        statements = list(self.context.statements.values())
        for i in range(len(statements)):
            for j in range(i + 1, len(statements)):
                if self._are_contradictory(statements[i], statements[j]):
                    inconsistencies.append((statements[i].statement_id, statements[j].statement_id))
        
        return inconsistencies
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """获取知识摘要"""
        total_statements = len(self.context.statements)
        inferred_statements = sum(1 for s in self.context.statements.values() if s.source == "inference")
        contradictions = len(self.context.contradictions)
        
        logic_types = {}
        for statement in self.context.statements.values():
            logic_type = statement.logic_type.value
            logic_types[logic_type] = logic_types.get(logic_type, 0) + 1
        
        return {
            "total_statements": total_statements,
            "inferred_statements": inferred_statements,
            "contradictions": contradictions,
            "logic_type_distribution": logic_types,
            "average_confidence": sum(s.confidence for s in self.context.statements.values()) / total_statements if total_statements > 0 else 0
        }

class LogicParser:
    """逻辑解析器"""
    
    def parse_propositional(self, text: str) -> Any:
        """解析命题逻辑"""
        try:
            # 替换逻辑符号
            normalized = (text.replace("→", ">>")
                         .replace("∧", "&")
                         .replace("∨", "|")
                         .replace("¬", "~")
                         .replace("蕴含", ">>")
                         .replace("且", "&")
                         .replace("或", "|")
                         .replace("非", "~"))
            
            # 使用sympy解析
            expr = sympy.sympify(normalized)
            return expr
        except Exception as e:
            logger.warning(f"命题逻辑解析失败: {e}")
            return None
    
    def to_cnf(self, expression: Any) -> Any:
        """转换为合取范式"""
        try:
            return to_cnf(expression)
        except Exception as e:
            logger.warning(f"CNF转换失败: {e}")
            return expression

