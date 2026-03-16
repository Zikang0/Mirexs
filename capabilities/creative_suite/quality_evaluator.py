"""
质量评估器：评估内容质量
支持语法、逻辑、一致性、相关性等多维度评估
"""

import os
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSequenceClassification
)
import language_tool_python
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """质量维度枚举"""
    GRAMMAR = "grammar"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"
    CONSISTENCY = "consistency"
    ENGAGEMENT = "engagement"
    READABILITY = "readability"

class QualityScore(BaseModel):
    """质量分数"""
    dimension: QualityDimension
    score: float  # 0.0-1.0
    confidence: float
    feedback: List[str]

class QualityEvaluationResult(BaseModel):
    """质量评估结果"""
    content: str
    scores: Dict[QualityDimension, QualityScore]
    overall_score: float
    recommendations: List[str]
    metadata: Dict[str, Any]

class QualityEvaluator:
    """质量评估器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.grammar_checker = None
        self.coherence_model = None
        self.relevance_model = None
        self.readability_analyzer = None
        
        # 初始化工具和模型
        self._initialize_tools()
        
        logger.info("QualityEvaluator initialized")
    
    def _initialize_tools(self):
        """初始化工具"""
        try:
            # 初始化语法检查器
            self.grammar_checker = language_tool_python.LanguageTool('zh-CN')
            
            # 初始化可读性分析器
            self.readability_analyzer = pipeline(
                "text-classification",
                model="cointegrated/roberta-base-readability",
                device=0 if self.device == "cuda" else -1
            )
            
            logger.info("Quality evaluation tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize quality evaluation tools: {e}")
    
    def load_models(self):
        """加载质量评估模型"""
        try:
            # 加载连贯性模型
            self.coherence_model = pipeline(
                "text-classification",
                model="textattack/roberta-base-CoLA",
                device=0 if self.device == "cuda" else -1
            )
            
            # 加载相关性模型
            self.relevance_model = pipeline(
                "text-classification", 
                model="cross-encoder/ms-marco-MiniLM-L-6-v2",
                device=0 if self.device == "cuda" else -1
            )
            
            logger.info("Quality evaluation models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load quality evaluation models: {e}")
    
    def evaluate_quality(self, 
                        content: str,
                        context: Optional[str] = None,
                        dimensions: Optional[List[QualityDimension]] = None) -> QualityEvaluationResult:
        """
        评估内容质量
        
        Args:
            content: 要评估的内容
            context: 上下文（用于相关性评估）
            dimensions: 要评估的维度
            
        Returns:
            QualityEvaluationResult: 评估结果
        """
        try:
            if self.grammar_checker is None:
                self._initialize_tools()
            
            if self.coherence_model is None:
                self.load_models()
            
            if dimensions is None:
                dimensions = list(QualityDimension)
            
            scores = {}
            
            # 按维度评估
            for dimension in dimensions:
                if dimension == QualityDimension.GRAMMAR:
                    scores[dimension] = self._evaluate_grammar(content)
                elif dimension == QualityDimension.COHERENCE:
                    scores[dimension] = self._evaluate_coherence(content)
                elif dimension == QualityDimension.RELEVANCE:
                    scores[dimension] = self._evaluate_relevance(content, context)
                elif dimension == QualityDimension.CONSISTENCY:
                    scores[dimension] = self._evaluate_consistency(content)
                elif dimension == QualityDimension.ENGAGEMENT:
                    scores[dimension] = self._evaluate_engagement(content)
                elif dimension == QualityDimension.READABILITY:
                    scores[dimension] = self._evaluate_readability(content)
            
            # 计算总体分数
            overall_score = self._calculate_overall_score(scores)
            
            # 生成改进建议
            recommendations = self._generate_recommendations(scores)
            
            return QualityEvaluationResult(
                content=content,
                scores=scores,
                overall_score=overall_score,
                recommendations=recommendations,
                metadata={
                    "evaluated_dimensions": [dim.value for dim in dimensions],
                    "context_provided": context is not None,
                    "evaluated_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to evaluate quality: {e}")
            raise
    
    def _evaluate_grammar(self, content: str) -> QualityScore:
        """评估语法质量"""
        try:
            # 使用语法检查器
            matches = self.grammar_checker.check(content)
            
            # 计算语法错误密度
            error_density = len(matches) / max(1, len(content.split()))
            
            # 转换为分数（错误越少分数越高）
            score = max(0.0, 1.0 - min(1.0, error_density * 10))
            
            feedback = []
            if matches:
                feedback.append(f"发现 {len(matches)} 处语法问题")
                # 添加前3个问题的具体反馈
                for match in matches[:3]:
                    feedback.append(f"- {match.message}")
            else:
                feedback.append("语法检查通过")
            
            return QualityScore(
                dimension=QualityDimension.GRAMMAR,
                score=score,
                confidence=0.8,
                feedback=feedback
            )
            
        except Exception as e:
            logger.warning(f"Grammar evaluation failed: {e}")
            return QualityScore(
                dimension=QualityDimension.GRAMMAR,
                score=0.5,
                confidence=0.0,
                feedback=[f"语法评估失败: {str(e)}"]
            )
    
    def _evaluate_coherence(self, content: str) -> QualityScore:
        """评估连贯性"""
        try:
            if self.coherence_model is None:
                return self._rule_based_coherence(content)
            
            # 使用模型评估连贯性
            sentences = self._split_into_sentences(content)
            if len(sentences) < 2:
                return QualityScore(
                    dimension=QualityDimension.COHERENCE,
                    score=0.8,
                    confidence=0.7,
                    feedback=["内容过短，无法充分评估连贯性"]
                )
            
            coherence_scores = []
            for sentence in sentences:
                result = self.coherence_model(sentence[:512])[0]
                # CoLA模型输出标签为LABEL_1表示连贯，LABEL_0表示不连贯
                score = result['score'] if result['label'] == 'LABEL_1' else 1 - result['score']
                coherence_scores.append(score)
            
            avg_score = sum(coherence_scores) / len(coherence_scores)
            
            feedback = []
            if avg_score > 0.8:
                feedback.append("内容连贯性良好")
            elif avg_score > 0.6:
                feedback.append("内容连贯性一般")
            else:
                feedback.append("内容连贯性需要改进")
            
            return QualityScore(
                dimension=QualityDimension.COHERENCE,
                score=avg_score,
                confidence=0.7,
                feedback=feedback
            )
            
        except Exception as e:
            logger.warning(f"Coherence evaluation failed: {e}")
            return self._rule_based_coherence(content)
    
    def _rule_based_coherence(self, content: str) -> QualityScore:
        """基于规则的连贯性评估"""
        sentences = self._split_into_sentences(content)
        
        if len(sentences) < 2:
            return QualityScore(
                dimension=QualityDimension.COHERENCE,
                score=0.8,
                confidence=0.5,
                feedback=["内容过短，无法充分评估连贯性"]
            )
        
        # 检查句子之间的连接词
        transition_words = ['首先', '其次', '然后', '接着', '最后', '因此', '所以', '然而', '另外']
        transition_count = sum(1 for sentence in sentences 
                             if any(word in sentence for word in transition_words))
        
        transition_ratio = transition_count / len(sentences)
        
        # 基于连接词比例计算分数
        score = min(1.0, transition_ratio * 3)
        
        feedback = []
        if transition_ratio > 0.3:
            feedback.append("句子连接良好")
        else:
            feedback.append("建议增加连接词以提高连贯性")
        
        return QualityScore(
            dimension=QualityDimension.COHERENCE,
            score=score,
            confidence=0.5,
            feedback=feedback
        )
    
    def _evaluate_relevance(self, content: str, context: Optional[str]) -> QualityScore:
        """评估相关性"""
        try:
            if context is None:
                # 没有上下文，无法评估相关性
                return QualityScore(
                    dimension=QualityDimension.RELEVANCE,
                    score=0.8,
                    confidence=0.3,
                    feedback=["缺少上下文，相关性评估受限"]
                )
            
            if self.relevance_model is None:
                return self._rule_based_relevance(content, context)
            
            # 使用模型评估相关性
            result = self.relevance_model(
                sequence=context[:512],
                candidate=content[:512]
            )[0]
            
            # 模型输出为相关性的概率
            score = result['score'] if result['label'] == 'LABEL_1' else 1 - result['score']
            
            feedback = []
            if score > 0.8:
                feedback.append("内容与上下文高度相关")
            elif score > 0.6:
                feedback.append("内容与上下文相关")
            else:
                feedback.append("内容与上下文相关性不足")
            
            return QualityScore(
                dimension=QualityDimension.RELEVANCE,
                score=score,
                confidence=0.7,
                feedback=feedback
            )
            
        except Exception as e:
            logger.warning(f"Relevance evaluation failed: {e}")
            return self._rule_based_relevance(content, context)
    
    def _rule_based_relevance(self, content: str, context: Optional[str]) -> QualityScore:
        """基于规则的相关性评估"""
        if context is None:
            return QualityScore(
                dimension=QualityDimension.RELEVANCE,
                score=0.8,
                confidence=0.3,
                feedback=["缺少上下文，相关性评估受限"]
            )
        
        # 简单的关键词重叠计算
        content_words = set(re.findall(r'\b\w+\b', content.lower()))
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        
        if not context_words:
            return QualityScore(
                dimension=QualityDimension.RELEVANCE,
                score=0.5,
                confidence=0.3,
                feedback=["上下文内容为空"]
            )
        
        overlap = len(content_words.intersection(context_words))
        overlap_ratio = overlap / len(context_words)
        
        score = min(1.0, overlap_ratio * 2)
        
        feedback = []
        if overlap_ratio > 0.3:
            feedback.append("内容与上下文有良好关联")
        else:
            feedback.append("内容与上下文关联较弱")
        
        return QualityScore(
            dimension=QualityDimension.RELEVANCE,
            score=score,
            confidence=0.5,
            feedback=feedback
        )
    
    def _evaluate_consistency(self, content: str) -> QualityScore:
        """评估一致性"""
        # 检查内容中的矛盾陈述
        contradictions = self._find_contradictions(content)
        
        # 根据矛盾数量计算分数
        contradiction_score = max(0.0, 1.0 - len(contradictions) * 0.3)
        
        feedback = []
        if not contradictions:
            feedback.append("内容一致性良好")
        else:
            feedback.append(f"发现 {len(contradictions)} 处可能的不一致")
            for contradiction in contradictions[:2]:
                feedback.append(f"- {contradiction}")
        
        return QualityScore(
            dimension=QualityDimension.CONSISTENCY,
            score=contradiction_score,
            confidence=0.6,
            feedback=feedback
        )
    
    def _find_contradictions(self, content: str) -> List[str]:
        """查找矛盾陈述"""
        contradictions = []
        
        # 简单的矛盾检测规则
        negation_pairs = [
            (r'是', r'不是'),
            (r'有', r'没有'),
            (r'可以', r'不能'),
            (r'会', r'不会')
        ]
        
        sentences = self._split_into_sentences(content)
        
        for i, sent1 in enumerate(sentences):
            for sent2 in sentences[i+1:]:
                for positive, negative in negation_pairs:
                    if (re.search(positive, sent1) and re.search(negative, sent2)) or \
                       (re.search(positive, sent2) and re.search(negative, sent1)):
                        contradictions.append(f"可能矛盾: '{sent1}' vs '{sent2}'")
                        break
        
        return contradictions
    
    def _evaluate_engagement(self, content: str) -> QualityScore:
        """评估吸引力"""
        # 基于规则评估内容吸引力
        engagement_indicators = {
            'questions': len(re.findall(r'[？?]', content)),  # 问号数量
            'exclamations': len(re.findall(r'[！!]', content)),  # 感叹号数量
            'length': len(content),  # 内容长度
            'paragraphs': len(content.split('\n\n')),  # 段落数量
        }
        
        # 计算吸引力分数
        question_score = min(1.0, engagement_indicators['questions'] * 0.5)
        exclamation_score = min(1.0, engagement_indicators['exclamations'] * 0.3)
        length_score = min(1.0, engagement_indicators['length'] / 500)  # 假设500字为理想长度
        paragraph_score = min(1.0, engagement_indicators['paragraphs'] / 5)  # 假设5段为理想数量
        
        engagement_score = (question_score + exclamation_score + length_score + paragraph_score) / 4
        
        feedback = []
        if engagement_score > 0.7:
            feedback.append("内容吸引力较强")
        elif engagement_score > 0.5:
            feedback.append("内容吸引力一般")
        else:
            feedback.append("内容吸引力需要提升")
        
        # 具体建议
        if engagement_indicators['questions'] == 0:
            feedback.append("可以考虑添加问题以增加互动性")
        if engagement_indicators['exclamations'] == 0:
            feedback.append("可以考虑使用感叹号增强情感表达")
        if length_score < 0.3:
            feedback.append("内容较短，可以考虑扩展")
        if paragraph_score < 0.3:
            feedback.append("段落较少，可以考虑分段以提高可读性")
        
        return QualityScore(
            dimension=QualityDimension.ENGAGEMENT,
            score=engagement_score,
            confidence=0.6,
            feedback=feedback
        )
    
    def _evaluate_readability(self, content: str) -> QualityScore:
        """评估可读性"""
        try:
            if self.readability_analyzer is None:
                return self._rule_based_readability(content)
            
            # 使用模型评估可读性
            result = self.readability_analyzer(content[:512])[0]
            
            # 模型输出为可读性等级，转换为分数
            label = result['label']
            score = result['score']
            
            # 简化映射：EASY -> 高分, DIFFICULT -> 低分
            if label == 'EASY':
                readability_score = 0.8 + 0.2 * score
            elif label == 'MEDIUM':
                readability_score = 0.5 + 0.3 * score
            else:  # DIFFICULT
                readability_score = 0.5 * score
            
            feedback = []
            if readability_score > 0.8:
                feedback.append("可读性优秀")
            elif readability_score > 0.6:
                feedback.append("可读性良好")
            else:
                feedback.append("可读性需要改进")
            
            return QualityScore(
                dimension=QualityDimension.READABILITY,
                score=readability_score,
                confidence=0.7,
                feedback=feedback
            )
            
        except Exception as e:
            logger.warning(f"Readability evaluation failed: {e}")
            return self._rule_based_readability(content)
    
    def _rule_based_readability(self, content: str) -> QualityScore:
        """基于规则的可读性评估"""
        sentences = self._split_into_sentences(content)
        words = re.findall(r'\b\w+\b', content)
        
        if not sentences or not words:
            return QualityScore(
                dimension=QualityDimension.READABILITY,
                score=0.5,
                confidence=0.3,
                feedback=["内容为空，无法评估可读性"]
            )
        
        # 计算平均句子长度和单词长度
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # 简化可读性公式
        readability_score = 1.0 - min(1.0, (avg_sentence_length / 25 + avg_word_length / 6) / 2)
        
        feedback = []
        if readability_score > 0.7:
            feedback.append("可读性良好")
        elif readability_score > 0.5:
            feedback.append("可读性一般")
        else:
            feedback.append("可读性需要改进，建议使用更短的句子和简单的词汇")
        
        return QualityScore(
            dimension=QualityDimension.READABILITY,
            score=readability_score,
            confidence=0.6,
            feedback=feedback
        )
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """分割文本为句子"""
        # 简单的句子分割
        sentences = re.split(r'[。！？.!?]', content)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_overall_score(self, scores: Dict[QualityDimension, QualityScore]) -> float:
        """计算总体质量分数"""
        if not scores:
            return 0.5
        
        # 加权平均计算总体分数
        weights = {
            QualityDimension.GRAMMAR: 0.2,
            QualityDimension.COHERENCE: 0.2,
            QualityDimension.RELEVANCE: 0.15,
            QualityDimension.CONSISTENCY: 0.15,
            QualityDimension.ENGAGEMENT: 0.15,
            QualityDimension.READABILITY: 0.15
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for dimension, score_obj in scores.items():
            weight = weights.get(dimension, 0.1)
            weighted_sum += score_obj.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _generate_recommendations(self, scores: Dict[QualityDimension, QualityScore]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 根据各维度分数生成建议
        for dimension, score_obj in scores.items():
            if score_obj.score < 0.6:
                if dimension == QualityDimension.GRAMMAR:
                    recommendations.append("检查并修正语法错误")
                elif dimension == QualityDimension.COHERENCE:
                    recommendations.append("改进内容连贯性，增加连接词")
                elif dimension == QualityDimension.RELEVANCE:
                    recommendations.append("增强内容与上下文的相关性")
                elif dimension == QualityDimension.CONSISTENCY:
                    recommendations.append("检查内容中的不一致之处")
                elif dimension == QualityDimension.ENGAGEMENT:
                    recommendations.append("提升内容吸引力，增加互动元素")
                elif dimension == QualityDimension.READABILITY:
                    recommendations.append("提高可读性，使用更简单的语言")
        
        # 如果没有低分项，提供一般性建议
        if not recommendations:
            recommendations.append("内容质量良好，继续保持")
        
        return recommendations
    
    def batch_evaluate_quality(self, 
                              contents: List[str],
                              contexts: Optional[List[str]] = None,
                              dimensions_list: Optional[List[List[QualityDimension]]] = None) -> List[QualityEvaluationResult]:
        """批量评估质量"""
        results = []
        
        if contexts is None:
            contexts = [None] * len(contents)
        
        if dimensions_list is None:
            dimensions_list = [None] * len(contents)
        
        for content, context, dimensions in zip(contents, contexts, dimensions_list):
            try:
                result = self.evaluate_quality(content, context, dimensions)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate quality for content: {e}")
                # 创建失败的结果
                results.append(QualityEvaluationResult(
                    content=content,
                    scores={},
                    overall_score=0.0,
                    recommendations=[f"评估失败: {str(e)}"],
                    metadata={"error": str(e)}
                ))
        
        return results

# 单例实例
_quality_evaluator_instance = None

def get_quality_evaluator() -> QualityEvaluator:
    """获取质量评估器单例"""
    global _quality_evaluator_instance
    if _quality_evaluator_instance is None:
        _quality_evaluator_instance = QualityEvaluator()
    return _quality_evaluator_instance

