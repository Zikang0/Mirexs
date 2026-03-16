"""
内容精炼器：优化和精炼生成的内容
支持语法检查、风格优化、内容增强等功能
"""

import os
import re
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import torch
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForSeq2SeqLM
)
import language_tool_python
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RefinementType(Enum):
    """精炼类型枚举"""
    GRAMMAR = "grammar"
    STYLE = "style"
    CLARITY = "clarity"
    CONCISENESS = "conciseness"
    ENGAGEMENT = "engagement"
    SEO = "seo"

class RefinementConfig(BaseModel):
    """内容精炼配置"""
    refinement_types: List[RefinementType]
    target_audience: str = "general"
    tone: str = "professional"
    reading_level: str = "standard"  # basic, standard, advanced
    max_length: Optional[int] = None
    min_length: Optional[int] = None

class RefinementResult(BaseModel):
    """精炼结果"""
    original_content: str
    refined_content: str
    changes: List[Dict[str, Any]]
    quality_improvement: float
    readability_score: float
    metadata: Dict[str, Any]

class ContentRefiner:
    """内容精炼器"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.grammar_checker = None
        self.style_transfer_model = None
        self.paraphrase_model = None
        self.readability_analyzer = None
        self.seo_analyzer = None
        
        # 加载工具和模型
        self._initialize_tools()
        
        logger.info("ContentRefiner initialized")
    
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
            
            logger.info("Content refinement tools initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize content refinement tools: {e}")
    
    def load_models(self):
        """加载精炼模型"""
        try:
            # 加载风格迁移模型
            self.style_transfer_model = pipeline(
                "text2text-generation",
                model="pranaydeeps/formal-to-informal-styletransfer",
                device=0 if self.device == "cuda" else -1
            )
            
            # 加载复述模型
            self.paraphrase_model = pipeline(
                "text2text-generation",
                model="Vamsi/T5_Paraphrase_Paws",
                device=0 if self.device == "cuda" else -1
            )
            
            logger.info("Content refinement models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load content refinement models: {e}")
    
    def refine_content(self, 
                      content: str, 
                      config: RefinementConfig) -> RefinementResult:
        """
        精炼内容
        
        Args:
            content: 原始内容
            config: 精炼配置
            
        Returns:
            RefinementResult: 精炼结果
        """
        try:
            if self.grammar_checker is None:
                self._initialize_tools()
            
            if self.style_transfer_model is None:
                self.load_models()
            
            refined_content = content
            all_changes = []
            original_readability = self._calculate_readability(content)
            
            # 按顺序应用各种精炼
            for refinement_type in config.refinement_types:
                if refinement_type == RefinementType.GRAMMAR:
                    refined_content, grammar_changes = self._refine_grammar(refined_content)
                    all_changes.extend(grammar_changes)
                
                elif refinement_type == RefinementType.STYLE:
                    refined_content, style_changes = self._refine_style(refined_content, config.tone)
                    all_changes.extend(style_changes)
                
                elif refinement_type == RefinementType.CLARITY:
                    refined_content, clarity_changes = self._refine_clarity(refined_content)
                    all_changes.extend(clarity_changes)
                
                elif refinement_type == RefinementType.CONCISENESS:
                    refined_content, conciseness_changes = self._refine_conciseness(refined_content)
                    all_changes.extend(conciseness_changes)
                
                elif refinement_type == RefinementType.ENGAGEMENT:
                    refined_content, engagement_changes = self._refine_engagement(refined_content)
                    all_changes.extend(engagement_changes)
                
                elif refinement_type == RefinementType.SEO:
                    refined_content, seo_changes = self._refine_seo(refined_content)
                    all_changes.extend(seo_changes)
            
            # 应用长度约束
            if config.max_length or config.min_length:
                refined_content = self._apply_length_constraints(
                    refined_content, config.max_length, config.min_length
                )
            
            # 计算质量改进
            final_readability = self._calculate_readability(refined_content)
            quality_improvement = final_readability - original_readability
            
            return RefinementResult(
                original_content=content,
                refined_content=refined_content,
                changes=all_changes,
                quality_improvement=quality_improvement,
                readability_score=final_readability,
                metadata={
                    "refinement_types": [rt.value for rt in config.refinement_types],
                    "target_audience": config.target_audience,
                    "tone": config.tone,
                    "reading_level": config.reading_level,
                    "refined_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to refine content: {e}")
            raise
    
    def _refine_grammar(self, content: str) -> Tuple[str, List[Dict]]:
        """精炼语法"""
        changes = []
        
        try:
            # 检查语法错误
            matches = self.grammar_checker.check(content)
            
            corrected_content = content
            offset = 0
            
            for match in matches:
                # 应用修正
                if match.replacements:
                    best_replacement = match.replacements[0]
                    
                    # 计算修正位置
                    start = match.offset + offset
                    end = start + match.errorLength
                    
                    # 应用修正
                    corrected_content = (
                        corrected_content[:start] + 
                        best_replacement + 
                        corrected_content[end:]
                    )
                    
                    # 更新偏移量
                    offset += len(best_replacement) - match.errorLength
                    
                    changes.append({
                        "type": "grammar",
                        "original": match.context[match.offsetInContext:match.offsetInContext + match.errorLength],
                        "corrected": best_replacement,
                        "message": match.message,
                        "position": (match.offset, match.offset + match.errorLength)
                    })
            
            return corrected_content, changes
            
        except Exception as e:
            logger.warning(f"Grammar refinement failed: {e}")
            return content, []
    
    def _refine_style(self, content: str, target_tone: str) -> Tuple[str, List[Dict]]:
        """精炼风格"""
        changes = []
        
        try:
            if self.style_transfer_model is None:
                return content, changes
            
            # 根据目标语气调整风格
            if target_tone == "formal":
                prompt = f"将以下文本转换为正式语气: {content}"
            elif target_tone == "casual":
                prompt = f"将以下文本转换为随意语气: {content}"
            elif target_tone == "professional":
                prompt = f"将以下文本转换为专业语气: {content}"
            else:
                return content, changes
            
            result = self.style_transfer_model(
                prompt,
                max_length=len(content) + 50,
                num_return_sequences=1
            )
            
            refined_content = result[0]['generated_text']
            
            changes.append({
                "type": "style",
                "original": content,
                "corrected": refined_content,
                "message": f"调整为{target_tone}语气",
                "position": (0, len(content))
            })
            
            return refined_content, changes
            
        except Exception as e:
            logger.warning(f"Style refinement failed: {e}")
            return content, []
    
    def _refine_clarity(self, content: str) -> Tuple[str, List[Dict]]:
        """提高清晰度"""
        changes = []
        
        try:
            # 识别并修正模糊表达
            clarity_issues = self._identify_clarity_issues(content)
            
            refined_content = content
            offset = 0
            
            for issue in clarity_issues:
                if issue['replacement']:
                    start = issue['position'][0] + offset
                    end = issue['position'][1] + offset
                    
                    refined_content = (
                        refined_content[:start] + 
                        issue['replacement'] + 
                        refined_content[end:]
                    )
                    
                    offset += len(issue['replacement']) - (end - start)
                    
                    changes.append({
                        "type": "clarity",
                        "original": issue['text'],
                        "corrected": issue['replacement'],
                        "message": issue['issue'],
                        "position": issue['position']
                    })
            
            return refined_content, changes
            
        except Exception as e:
            logger.warning(f"Clarity refinement failed: {e}")
            return content, []
    
    def _identify_clarity_issues(self, content: str) -> List[Dict]:
        """识别清晰度问题"""
        issues = []
        
        # 模糊代词检测
        vague_pronouns = ['这个', '那个', '这些', '那些', '它', '他们']
        for pronoun in vague_pronouns:
            for match in re.finditer(pronoun, content):
                # 检查代词前面是否有明确的指代
                preceding_text = content[max(0, match.start()-50):match.start()]
                if not any(noun in preceding_text for noun in ['具体', '明确', '特定']):
                    issues.append({
                        'text': pronoun,
                        'issue': '模糊代词',
                        'replacement': '具体内容',  # 应该根据上下文生成具体内容
                        'position': (match.start(), match.end())
                    })
        
        # 复杂句子检测
        sentences = re.split(r'[。！？]', content)
        for i, sentence in enumerate(sentences):
            if len(sentence) > 50:  # 长句子可能难以理解
                # 找到句子开始位置
                start = content.find(sentence)
                if start != -1:
                    issues.append({
                        'text': sentence,
                        'issue': '句子过长',
                        'replacement': self._split_long_sentence(sentence),
                        'position': (start, start + len(sentence))
                    })
        
        return issues
    
    def _split_long_sentence(self, sentence: str) -> str:
        """分割长句子"""
        # 简单的基于逗号的分割
        parts = sentence.split('，')
        if len(parts) > 1:
            return '。'.join(parts) + '。'
        else:
            return sentence
    
    def _refine_conciseness(self, content: str) -> Tuple[str, List[Dict]]:
        """提高简洁性"""
        changes = []
        
        try:
            if self.paraphrase_model is None:
                return content, changes
            
            # 使用复述模型简化表达
            prompt = f"用更简洁的方式表达: {content}"
            
            result = self.paraphrase_model(
                prompt,
                max_length=len(content),
                num_return_sequences=1
            )
            
            refined_content = result[0]['generated_text']
            
            # 计算精简程度
            original_length = len(content)
            refined_length = len(refined_content)
            reduction = (original_length - refined_length) / original_length
            
            if reduction > 0.1:  # 至少精简10%
                changes.append({
                    "type": "conciseness",
                    "original": content,
                    "corrected": refined_content,
                    "message": f"精简了{reduction:.1%}",
                    "position": (0, len(content))
                })
                
                return refined_content, changes
            else:
                return content, []
            
        except Exception as e:
            logger.warning(f"Conciseness refinement failed: {e}")
            return content, []
    
    def _refine_engagement(self, content: str) -> Tuple[str, List[Dict]]:
        """提高吸引力"""
        changes = []
        refined_content = content
        
        # 检测并改进开头
        first_sentence = content.split('。')[0] if '。' in content else content
        if len(first_sentence) > 0:
            engaging_start = self._make_engaging_start(first_sentence)
            if engaging_start != first_sentence:
                refined_content = refined_content.replace(first_sentence, engaging_start, 1)
                changes.append({
                    "type": "engagement",
                    "original": first_sentence,
                    "corrected": engaging_start,
                    "message": "改进开头吸引注意力",
                    "position": (0, len(first_sentence))
                })
        
        # 添加问题引导思考
        sentences = refined_content.split('。')
        if len(sentences) > 3:
            # 在中间插入一个问题
            insert_pos = len('。'.join(sentences[:len(sentences)//2])) + 1
            question = "您觉得这个观点如何？"
            refined_content = (
                refined_content[:insert_pos] + 
                question + " " + 
                refined_content[insert_pos:]
            )
            changes.append({
                "type": "engagement",
                "original": "",
                "corrected": question,
                "message": "添加互动问题",
                "position": (insert_pos, insert_pos + len(question))
            })
        
        return refined_content, changes
    
    def _make_engaging_start(self, sentence: str) -> str:
        """创建吸引人的开头"""
        engaging_patterns = [
            "您知道吗？",
            "想象一下，",
            "有趣的是，",
            "令人惊讶的是，"
        ]
        
        # 检查是否已经是吸引人的开头
        if any(pattern in sentence for pattern in engaging_patterns):
            return sentence
        
        # 添加吸引人的模式
        import random
        pattern = random.choice(engaging_patterns)
        return pattern + sentence
    
    def _refine_seo(self, content: str) -> Tuple[str, List[Dict]]:
        """SEO优化"""
        changes = []
        refined_content = content
        
        # 简单的SEO优化规则
        seo_suggestions = []
        
        # 检查关键词密度
        words = re.findall(r'\b\w+\b', content)
        if len(words) > 0:
            # 建议添加更多相关关键词（这里需要根据主题生成）
            seo_suggestions.append("考虑添加更多相关关键词")
        
        # 检查标题结构
        if not any(marker in content for marker in ['#', '标题', '主题']):
            seo_suggestions.append("建议添加明确的标题")
        
        # 检查段落长度
        paragraphs = content.split('\n\n')
        for i, para in enumerate(paragraphs):
            if len(para) > 300:
                seo_suggestions.append(f"第{i+1}段过长，建议分割")
        
        if seo_suggestions:
            changes.append({
                "type": "seo",
                "original": "",
                "corrected": "",
                "message": " | ".join(seo_suggestions),
                "position": (0, 0)
            })
        
        return refined_content, changes
    
    def _apply_length_constraints(self, content: str, max_length: Optional[int], min_length: Optional[int]) -> str:
        """应用长度约束"""
        refined_content = content
        
        if max_length and len(content) > max_length:
            # 截断到最大长度，尽量在句子边界处截断
            if len(content) > max_length:
                truncated = content[:max_length]
                # 找到最后一个句子结束的位置
                last_period = max(truncated.rfind('。'), truncated.rfind('!'), truncated.rfind('?'))
                if last_period != -1:
                    refined_content = content[:last_period + 1]
                else:
                    refined_content = truncated + "..."
        
        if min_length and len(content) < min_length:
            # 扩展内容到最小长度
            # 这里应该使用内容生成模型来扩展内容
            # 目前简单地重复部分内容（实际应用中应该避免）
            extension = "。需要进一步详细说明。"
            refined_content = content + extension * ((min_length - len(content)) // len(extension) + 1)
            refined_content = refined_content[:min_length]
        
        return refined_content
    
    def _calculate_readability(self, content: str) -> float:
        """计算可读性分数"""
        try:
            if self.readability_analyzer:
                result = self.readability_analyzer(content)[0]
                # 将分类结果转换为分数
                label = result['label']
                score = result['score']
                
                # 简化映射：EASY -> 0.8-1.0, MEDIUM -> 0.5-0.8, DIFFICULT -> 0.0-0.5
                if label == 'EASY':
                    return 0.8 + 0.2 * score
                elif label == 'MEDIUM':
                    return 0.5 + 0.3 * score
                else:
                    return 0.5 * score
            else:
                # 基于规则的简单可读性计算
                words = re.findall(r'\b\w+\b', content)
                sentences = re.split(r'[。！？]', content)
                
                if len(sentences) == 0 or len(words) == 0:
                    return 0.5
                
                avg_sentence_length = len(words) / len(sentences)
                avg_word_length = sum(len(word) for word in words) / len(words)
                
                # 简化可读性公式
                readability = 1.0 - min(1.0, (avg_sentence_length / 20 + avg_word_length / 6) / 2)
                return max(0.0, min(1.0, readability))
                
        except Exception as e:
            logger.warning(f"Readability calculation failed: {e}")
            return 0.5
    
    def batch_refine_content(self, 
                           contents: List[str], 
                           configs: List[RefinementConfig]) -> List[RefinementResult]:
        """批量精炼内容"""
        results = []
        for content, config in zip(contents, configs):
            try:
                result = self.refine_content(content, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to refine content: {e}")
                results.append(RefinementResult(
                    original_content=content,
                    refined_content=content,
                    changes=[],
                    quality_improvement=0.0,
                    readability_score=self._calculate_readability(content),
                    metadata={"error": str(e)}
                ))
        return results

# 单例实例
_content_refiner_instance = None

def get_content_refiner() -> ContentRefiner:
    """获取内容精炼器单例"""
    global _content_refiner_instance
    if _content_refiner_instance is None:
        _content_refiner_instance = ContentRefiner()
    return _content_refiner_instance

