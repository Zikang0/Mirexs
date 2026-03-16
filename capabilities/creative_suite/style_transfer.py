"""
风格迁移：内容风格迁移
支持文本风格转换、写作风格适应等功能
"""

import os
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    T5ForConditionalGeneration
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class WritingStyle(Enum):
    """写作风格枚举"""
    FORMAL = "formal"
    CASUAL = "casual"
    ACADEMIC = "academic"
    BUSINESS = "business"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    CONVERSATIONAL = "conversational"

class StyleTransferConfig(BaseModel):
    """风格迁移配置"""
    source_style: WritingStyle
    target_style: WritingStyle
    intensity: float = 0.7  # 迁移强度 0.0-1.0
    preserve_content: bool = True
    adapt_vocabulary: bool = True

class StyleTransferResult(BaseModel):
    """风格迁移结果"""
    original_content: str
    transferred_content: str
    source_style: WritingStyle
    target_style: WritingStyle
    style_similarity: float
    content_preservation: float
    metadata: Dict[str, Any]

class StyleAnalyzer:
    """风格分析器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.style_classifier = None
        self.feature_extractor = None
        
    def load_models(self):
        """加载风格分析模型"""
        try:
            # 加载风格分类器
            self.style_classifier = pipeline(
                "text-classification",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if self.device == "cuda" else -1
            )
            
            logger.info("Style analyzer models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load style analyzer models: {e}")
    
    def analyze_style(self, content: str) -> Dict[str, float]:
        """分析文本风格"""
        try:
            if self.style_classifier is None:
                self.load_models()
            
            # 基于规则的特征提取
            features = self._extract_style_features(content)
            
            # 使用模型进行分类（如果可用）
            if self.style_classifier:
                model_prediction = self.style_classifier(content[:512])[0]
                features["model_confidence"] = model_prediction["score"]
                features["model_label"] = model_prediction["label"]
            
            return features
            
        except Exception as e:
            logger.warning(f"Style analysis failed: {e}")
            return self._extract_style_features(content)  # 回退到基于规则的分析
    
    def _extract_style_features(self, content: str) -> Dict[str, float]:
        """提取风格特征"""
        features = {}
        
        # 句子长度分析
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences)
            features["avg_sentence_length"] = avg_sentence_length
            features["sentence_complexity"] = min(1.0, avg_sentence_length / 50)
        else:
            features["avg_sentence_length"] = 0
            features["sentence_complexity"] = 0
        
        # 词汇复杂性
        words = re.findall(r'\b\w+\b', content)
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            features["avg_word_length"] = avg_word_length
            features["vocabulary_complexity"] = min(1.0, avg_word_length / 8)
        else:
            features["avg_word_length"] = 0
            features["vocabulary_complexity"] = 0
        
        # 正式程度指标
        formal_indicators = ['据悉', '根据', '综上所述', '因此', '然而']
        casual_indicators = ['我觉得', '好像', '大概', '可能', '吧']
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in content)
        casual_count = sum(1 for indicator in casual_indicators if indicator in content)
        
        total_indicators = formal_count + casual_count
        if total_indicators > 0:
            features["formality_score"] = formal_count / total_indicators
        else:
            features["formality_score"] = 0.5
        
        # 情感倾向（简化）
        positive_words = ['好', '优秀', '成功', '高兴', '满意']
        negative_words = ['差', '失败', '悲伤', '不满', '问题']
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        
        total_sentiment = positive_count + negative_count
        if total_sentiment > 0:
            features["sentiment_score"] = (positive_count - negative_count) / total_sentiment
        else:
            features["sentiment_score"] = 0
        
        return features
    
    def classify_writing_style(self, content: str) -> WritingStyle:
        """分类写作风格"""
        features = self.analyze_style(content)
        
        # 基于特征进行风格分类
        formality = features.get("formality_score", 0.5)
        complexity = features.get("sentence_complexity", 0.5)
        
        if formality > 0.7 and complexity > 0.6:
            return WritingStyle.ACADEMIC
        elif formality > 0.6:
            return WritingStyle.FORMAL
        elif formality > 0.4:
            return WritingStyle.BUSINESS
        elif complexity > 0.6:
            return WritingStyle.TECHNICAL
        elif formality < 0.3:
            return WritingStyle.CASUAL
        else:
            return WritingStyle.CONVERSATIONAL

class StyleTransfer:
    """风格迁移器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.style_analyzer = StyleAnalyzer()
        self.transfer_models: Dict[Tuple[WritingStyle, WritingStyle], Any] = {}
        
        # 风格迁移提示模板
        self.transfer_prompts = self._load_transfer_prompts()
        
        # 初始化基础模型
        self.base_model = None
        
        logger.info("StyleTransfer initialized")
    
    def _load_transfer_prompts(self) -> Dict[Tuple[WritingStyle, WritingStyle], str]:
        """加载风格迁移提示模板"""
        return {
            (WritingStyle.FORMAL, WritingStyle.CASUAL): 
                "将以下正式文本转换为随意口语化的表达：{}",
            (WritingStyle.CASUAL, WritingStyle.FORMAL): 
                "将以下随意文本转换为正式专业的表达：{}",
            (WritingStyle.ACADEMIC, WritingStyle.BUSINESS): 
                "将以下学术文本转换为商务表达：{}",
            (WritingStyle.BUSINESS, WritingStyle.ACADEMIC): 
                "将以下商务文本转换为学术表达：{}",
            (WritingStyle.TECHNICAL, WritingStyle.CONVERSATIONAL): 
                "将以下技术文本转换为通俗易懂的表达：{}",
            (WritingStyle.CONVERSATIONAL, WritingStyle.TECHNICAL): 
                "将以下通俗文本转换为专业技术的表达：{}"
        }
    
    def load_models(self):
        """加载风格迁移模型"""
        try:
            # 加载基础的文本到文本模型
            self.base_model = pipeline(
                "text2text-generation",
                model="t5-small",
                device=0 if self.device == "cuda" else -1
            )
            
            # 加载风格分析器
            self.style_analyzer.load_models()
            
            logger.info("Style transfer models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load style transfer models: {e}")
    
    def transfer_style(self, 
                      content: str, 
                      config: StyleTransferConfig) -> StyleTransferResult:
        """
        迁移文本风格
        
        Args:
            content: 原始内容
            config: 风格迁移配置
            
        Returns:
            StyleTransferResult: 迁移结果
        """
        try:
            if self.base_model is None:
                self.load_models()
            
            # 分析原始风格
            source_analysis = self.style_analyzer.analyze_style(content)
            detected_source_style = self.style_analyzer.classify_writing_style(content)
            
            # 应用风格迁移
            transferred_content = self._apply_style_transfer(content, config)
            
            # 分析迁移后风格
            target_analysis = self.style_analyzer.analyze_style(transferred_content)
            detected_target_style = self.style_analyzer.classify_writing_style(transferred_content)
            
            # 计算相似度和保留度
            style_similarity = self._calculate_style_similarity(
                target_analysis, config.target_style
            )
            content_preservation = self._calculate_content_preservation(
                content, transferred_content
            )
            
            return StyleTransferResult(
                original_content=content,
                transferred_content=transferred_content,
                source_style=detected_source_style,
                target_style=detected_target_style,
                style_similarity=style_similarity,
                content_preservation=content_preservation,
                metadata={
                    "source_analysis": source_analysis,
                    "target_analysis": target_analysis,
                    "intensity": config.intensity,
                    "preserve_content": config.preserve_content,
                    "transferred_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to transfer style: {e}")
            raise
    
    def _apply_style_transfer(self, content: str, config: StyleTransferConfig) -> str:
        """应用风格迁移"""
        # 获取迁移提示
        prompt_template = self.transfer_prompts.get(
            (config.source_style, config.target_style)
        )
        
        if not prompt_template:
            # 使用通用提示
            prompt_template = "将以下文本从{source}风格转换为{target}风格：{}".format(
                source=config.source_style.value,
                target=config.target_style.value,
                content="{}"
            )
        
        prompt = prompt_template.format(content)
        
        try:
            # 使用模型进行风格迁移
            if self.base_model:
                result = self.base_model(
                    prompt,
                    max_length=len(content) + 100,
                    num_return_sequences=1,
                    temperature=config.intensity
                )
                transferred = result[0]['generated_text']
            else:
                # 模型不可用，使用基于规则的迁移
                transferred = self._rule_based_style_transfer(content, config)
            
            # 应用强度控制
            if config.intensity < 1.0:
                transferred = self._adjust_transfer_intensity(
                    content, transferred, config.intensity
                )
            
            return transferred
            
        except Exception as e:
            logger.warning(f"Model-based style transfer failed, using rule-based: {e}")
            return self._rule_based_style_transfer(content, config)
    
    def _rule_based_style_transfer(self, content: str, config: StyleTransferConfig) -> str:
        """基于规则的风格迁移"""
        transferred = content
        
        # 根据目标风格应用不同的转换规则
        if config.target_style == WritingStyle.FORMAL:
            transferred = self._make_formal(transferred)
        elif config.target_style == WritingStyle.CASUAL:
            transferred = self._make_casual(transferred)
        elif config.target_style == WritingStyle.ACADEMIC:
            transferred = self._make_academic(transferred)
        elif config.target_style == WritingStyle.BUSINESS:
            transferred = self._make_business(transferred)
        elif config.target_style == WritingStyle.TECHNICAL:
            transferred = self._make_technical(transferred)
        elif config.target_style == WritingStyle.CONVERSATIONAL:
            transferred = self._make_conversational(transferred)
        
        return transferred
    
    def _make_formal(self, content: str) -> str:
        """转换为正式风格"""
        replacements = {
            '我': '本人',
            '你': '您',
            '咱们': '我们',
            '搞': '进行',
            '弄': '处理',
            '做': '执行',
            '说': '表示',
            '告诉': '告知',
            '想': '认为',
            '觉得': '认为'
        }
        
        return self._apply_replacements(content, replacements)
    
    def _make_casual(self, content: str) -> str:
        """转换为随意风格"""
        replacements = {
            '本人': '我',
            '您': '你',
            '我们': '咱们',
            '进行': '搞',
            '处理': '弄',
            '执行': '做',
            '表示': '说',
            '告知': '告诉',
            '认为': '觉得',
            '因此': '所以'
        }
        
        return self._apply_replacements(content, replacements)
    
    def _make_academic(self, content: str) -> str:
        """转换为学术风格"""
        replacements = {
            '我': '本研究',
            '我们': '本团队',
            '发现': '观察到',
            '觉得': '认为',
            '可能': '或许',
            '大概': '约',
            '很多': '大量',
            '很快': '迅速'
        }
        
        return self._apply_replacements(content, replacements)
    
    def _make_business(self, content: str) -> str:
        """转换为商务风格"""
        replacements = {
            '我': '本公司',
            '我们': '我方',
            '做': '开展',
            '弄': '处理',
            '搞': '实施',
            '觉得': '认为',
            '可能': '有望',
            '大概': '约',
            '很多': '显著'
        }
        
        return self._apply_replacements(content, replacements)
    
    def _make_technical(self, content: str) -> str:
        """转换为技术风格"""
        # 技术风格更注重精确性和专业性
        transferred = content
        # 这里可以添加技术术语的替换规则
        return transferred
    
    def _make_conversational(self, content: str) -> str:
        """转换为对话风格"""
        transferred = content
        
        # 添加对话标记
        if not transferred.startswith(('您知道吗？', '想象一下', '有趣的是')):
            transferred = "您知道吗？" + transferred
        
        # 缩短长句子
        sentences = transferred.split('。')
        if len(sentences) > 1:
            transferred = '。'.join(sentences[:2]) + '。'
        
        return transferred
    
    def _apply_replacements(self, content: str, replacements: Dict[str, str]) -> str:
        """应用替换规则"""
        transferred = content
        for old, new in replacements.items():
            transferred = transferred.replace(old, new)
        return transferred
    
    def _adjust_transfer_intensity(self, 
                                 original: str, 
                                 transferred: str, 
                                 intensity: float) -> str:
        """调整迁移强度"""
        if intensity >= 1.0:
            return transferred
        
        # 简单的线性插值
        # 在实际应用中应该使用更复杂的方法
        words_original = original.split()
        words_transferred = transferred.split()
        
        # 保持原始长度
        if len(words_transferred) > len(words_original):
            words_transferred = words_transferred[:len(words_original)]
        else:
            words_transferred.extend([''] * (len(words_original) - len(words_transferred)))
        
        # 混合原始和迁移后的内容
        mixed_words = []
        for i, (orig_word, trans_word) in enumerate(zip(words_original, words_transferred)):
            if i < len(words_original) * intensity:
                mixed_words.append(trans_word if trans_word else orig_word)
            else:
                mixed_words.append(orig_word)
        
        return ' '.join(mixed_words)
    
    def _calculate_style_similarity(self, 
                                  analysis: Dict[str, float], 
                                  target_style: WritingStyle) -> float:
        """计算风格相似度"""
        # 基于特征计算与目标风格的相似度
        target_features = self._get_target_style_features(target_style)
        
        similarity = 0.0
        feature_count = 0
        
        for feature, target_value in target_features.items():
            if feature in analysis:
                actual_value = analysis[feature]
                feature_similarity = 1.0 - abs(actual_value - target_value)
                similarity += feature_similarity
                feature_count += 1
        
        return similarity / feature_count if feature_count > 0 else 0.5
    
    def _get_target_style_features(self, style: WritingStyle) -> Dict[str, float]:
        """获取目标风格的特征值"""
        # 这些值是基于经验的估计
        features = {
            "formality_score": 0.5,
            "sentence_complexity": 0.5,
            "vocabulary_complexity": 0.5
        }
        
        if style == WritingStyle.FORMAL:
            features.update({"formality_score": 0.8, "sentence_complexity": 0.6})
        elif style == WritingStyle.CASUAL:
            features.update({"formality_score": 0.2, "sentence_complexity": 0.3})
        elif style == WritingStyle.ACADEMIC:
            features.update({"formality_score": 0.9, "sentence_complexity": 0.8, "vocabulary_complexity": 0.8})
        elif style == WritingStyle.BUSINESS:
            features.update({"formality_score": 0.7, "sentence_complexity": 0.5})
        elif style == WritingStyle.TECHNICAL:
            features.update({"formality_score": 0.6, "vocabulary_complexity": 0.9})
        elif style == WritingStyle.CONVERSATIONAL:
            features.update({"formality_score": 0.3, "sentence_complexity": 0.2})
        
        return features
    
    def _calculate_content_preservation(self, original: str, transferred: str) -> float:
        """计算内容保留度"""
        # 简单的基于词汇重叠的计算
        words_original = set(re.findall(r'\b\w+\b', original.lower()))
        words_transferred = set(re.findall(r'\b\w+\b', transferred.lower()))
        
        if not words_original:
            return 0.0
        
        overlap = len(words_original.intersection(words_transferred))
        return overlap / len(words_original)
    
    def batch_transfer_styles(self, 
                            contents: List[str], 
                            configs: List[StyleTransferConfig]) -> List[StyleTransferResult]:
        """批量风格迁移"""
        results = []
        for content, config in zip(contents, configs):
            try:
                result = self.transfer_style(content, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to transfer style for content: {e}")
                # 创建失败的结果
                results.append(StyleTransferResult(
                    original_content=content,
                    transferred_content=content,
                    source_style=WritingStyle.CONVERSATIONAL,
                    target_style=config.target_style,
                    style_similarity=0.0,
                    content_preservation=1.0,
                    metadata={"error": str(e)}
                ))
        return results
    
    def analyze_style_compatibility(self, 
                                  content: str, 
                                  target_style: WritingStyle) -> Dict[str, Any]:
        """分析风格兼容性"""
        current_analysis = self.style_analyzer.analyze_style(content)
        current_style = self.style_analyzer.classify_writing_style(content)
        target_features = self._get_target_style_features(target_style)
        
        compatibility_score = self._calculate_style_similarity(current_analysis, target_style)
        
        # 识别需要调整的方面
        adjustments_needed = []
        for feature, target_value in target_features.items():
            if feature in current_analysis:
                current_value = current_analysis[feature]
                if abs(current_value - target_value) > 0.3:
                    adjustments_needed.append({
                        "feature": feature,
                        "current": current_value,
                        "target": target_value,
                        "adjustment": target_value - current_value
                    })
        
        return {
            "current_style": current_style.value,
            "target_style": target_style.value,
            "compatibility_score": compatibility_score,
            "adjustments_needed": adjustments_needed,
            "recommendations": self._generate_style_recommendations(adjustments_needed, target_style)
        }
    
    def _generate_style_recommendations(self, 
                                      adjustments: List[Dict], 
                                      target_style: WritingStyle) -> List[str]:
        """生成风格调整建议"""
        recommendations = []
        
        for adjustment in adjustments:
            feature = adjustment["feature"]
            diff = adjustment["adjustment"]
            
            if feature == "formality_score":
                if diff > 0:
                    recommendations.append("增加正式表达，使用更专业的词汇")
                else:
                    recommendations.append("减少正式表达，使用更随意的语言")
            
            elif feature == "sentence_complexity":
                if diff > 0:
                    recommendations.append("使用更复杂的句子结构")
                else:
                    recommendations.append("简化句子结构，使用短句")
            
            elif feature == "vocabulary_complexity":
                if diff > 0:
                    recommendations.append("使用更专业的术语和复杂词汇")
                else:
                    recommendations.append("使用更简单易懂的词汇")
        
        return recommendations

# 单例实例
_style_transfer_instance = None

def get_style_transfer() -> StyleTransfer:
    """获取风格迁移器单例"""
    global _style_transfer_instance
    if _style_transfer_instance is None:
        _style_transfer_instance = StyleTransfer()
    return _style_transfer_instance

