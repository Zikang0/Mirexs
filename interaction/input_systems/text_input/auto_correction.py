"""
自动校正模块：自动检测和校正输入错误
"""

import re
import difflib
from typing import Dict, List, Tuple, Optional, Any, Set
import logging
from collections import defaultdict
from dataclasses import dataclass, field
import json
import time
import threading

from data.models.nlp.language_models import LanguageModel
from cognitive.memory.semantic_memory import SemanticMemory
from infrastructure.communication.message_bus import MessageBus
from utils.ai_utilities.model_utils import ModelLoader
from config.system import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class CorrectionCandidate:
    """校正候选"""
    original: str
    corrected: str
    confidence: float
    error_type: str  # spelling, grammar, punctuation, etc.
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "original": self.original,
            "corrected": self.corrected,
            "confidence": self.confidence,
            "error_type": self.error_type
        }


class AutoCorrection:
    """自动校正器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化自动校正器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 模型和字典
        self.dictionary = set()
        self.spell_checker = None
        self.grammar_checker = None
        self.language_model = None
        
        # 语义内存
        self.semantic_memory = None
        
        # 配置参数
        self.enable_spell_check = True
        self.enable_grammar_check = True
        self.enable_auto_correct = True
        self.confidence_threshold = 0.8
        self.max_suggestions = 3
        
        # 语言配置
        self.languages = ["zh-CN", "en-US"]
        self.current_language = "zh-CN"
        
        # 缓存
        self.correction_cache = {}
        self.common_errors = defaultdict(int)
        
        # 学习数据
        self.user_corrections = defaultdict(list)
        self.ignored_corrections = set()
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 加载配置
        self.load_config()
        
        # 加载模型
        self.load_models()
        
        logger.info("AutoCorrection initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("auto_correction_config")
            
            # 基本配置
            self.enable_spell_check = config.get("enable_spell_check", True)
            self.enable_grammar_check = config.get("enable_grammar_check", True)
            self.enable_auto_correct = config.get("enable_auto_correct", True)
            self.enable_learning = config.get("enable_learning", True)
            
            # 校正参数
            correction = config.get("correction", {})
            self.confidence_threshold = correction.get("confidence_threshold", 0.8)
            self.max_suggestions = correction.get("max_suggestions", 3)
            self.max_context_length = correction.get("max_context_length", 50)
            
            # 语言配置
            self.languages = config.get("supported_languages", ["zh-CN", "en-US"])
            self.current_language = config.get("default_language", "zh-CN")
            
            logger.debug(f"Auto correction config loaded: language={self.current_language}")
        except Exception as e:
            logger.error(f"Failed to load auto correction config: {e}")
    
    def load_models(self) -> None:
        """加载校正模型"""
        try:
            # 加载词典
            self._load_dictionary()
            
            # 加载语言模型
            self.language_model = LanguageModel(language=self.current_language)
            
            # 加载拼写检查模型
            spell_model_path = f"data/models/nlp/correction/{self.current_language}/spell.pt"
            if os.path.exists(spell_model_path):
                self.spell_checker = ModelLoader.load_model(
                    spell_model_path,
                    model_class="SpellChecker"
                )
                logger.info(f"Loaded spell checker for {self.current_language}")
            
            # 加载语法检查模型
            grammar_model_path = f"data/models/nlp/correction/{self.current_language}/grammar.pt"
            if os.path.exists(grammar_model_path):
                self.grammar_checker = ModelLoader.load_model(
                    grammar_model_path,
                    model_class="GrammarChecker"
                )
                logger.info(f"Loaded grammar checker for {self.current_language}")
            
            # 初始化语义内存
            self.semantic_memory = SemanticMemory()
            
            logger.info("Auto correction models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load correction models: {e}")
    
    def _load_dictionary(self) -> None:
        """加载词典"""
        try:
            # 加载主词典
            dict_path = f"data/models/nlp/dictionaries/{self.current_language}.txt"
            if os.path.exists(dict_path):
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.dictionary = set(line.strip().lower() for line in f if line.strip())
                logger.info(f"Loaded dictionary: {len(self.dictionary)} words")
            
            # 加载用户词典
            user_dict_path = f"data/user_data/dictionaries/{self.current_language}_user.txt"
            if os.path.exists(user_dict_path):
                with open(user_dict_path, 'r', encoding='utf-8') as f:
                    user_words = set(line.strip().lower() for line in f if line.strip())
                    self.dictionary.update(user_words)
                logger.info(f"Added {len(user_words)} user words to dictionary")
            
        except Exception as e:
            logger.error(f"Failed to load dictionary: {e}")
    
    def check_text(self, text: str, context: Optional[str] = None) -> List[CorrectionCandidate]:
        """
        检查文本中的错误
        
        Args:
            text: 要检查的文本
            context: 上下文文本（可选）
            
        Returns:
            List[CorrectionCandidate]: 校正候选列表
        """
        if not text:
            return []
        
        try:
            candidates = []
            
            # 1. 拼写检查
            if self.enable_spell_check:
                spell_candidates = self._check_spelling(text, context)
                candidates.extend(spell_candidates)
            
            # 2. 语法检查
            if self.enable_grammar_check:
                grammar_candidates = self._check_grammar(text, context)
                candidates.extend(grammar_candidates)
            
            # 3. 标点检查
            punctuation_candidates = self._check_punctuation(text)
            candidates.extend(punctuation_candidates)
            
            # 4. 样式检查
            style_candidates = self._check_style(text)
            candidates.extend(style_candidates)
            
            # 按置信度排序
            candidates.sort(key=lambda x: x.confidence, reverse=True)
            
            # 去重
            unique_candidates = self._deduplicate_candidates(candidates)
            
            # 过滤低置信度的建议
            filtered_candidates = [
                cand for cand in unique_candidates 
                if cand.confidence >= self.confidence_threshold
            ]
            
            logger.debug(f"Found {len(filtered_candidates)} corrections for text: {text[:50]}...")
            return filtered_candidates[:self.max_suggestions]
            
        except Exception as e:
            logger.error(f"Text checking failed: {e}")
            return []
    
    def _check_spelling(self, text: str, context: Optional[str] = None) -> List[CorrectionCandidate]:
        """检查拼写错误"""
        candidates = []
        
        # 分词（根据语言）
        words = self._tokenize(text)
        
        for i, word in enumerate(words):
            # 检查是否是单词（跳过标点和数字）
            if not self._is_word(word):
                continue
            
            # 检查是否在词典中
            if word.lower() not in self.dictionary and word not in self.ignored_corrections:
                # 可能是拼写错误
                suggestions = self._get_spell_suggestions(word, context)
                
                for suggestion, confidence in suggestions:
                    candidate = CorrectionCandidate(
                        original=word,
                        corrected=suggestion,
                        confidence=confidence,
                        error_type="spelling",
                        context={
                            "position": i,
                            "word_index": i,
                            "suggestion_source": "dictionary"
                        }
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        if self.current_language == "zh-CN":
            # 中文分词（简化版）
            import jieba
            return list(jieba.cut(text))
        else:
            # 英文分词
            import re
            return re.findall(r'\b\w+\b|[^\w\s]', text)
    
    def _is_word(self, token: str) -> bool:
        """判断是否是单词"""
        if not token:
            return False
        
        # 检查是否包含字母
        if self.current_language == "en-US":
            return any(c.isalpha() for c in token)
        else:
            # 中文：检查是否是汉字
            return any('\u4e00' <= c <= '\u9fff' for c in token)
    
    def _get_spell_suggestions(self, word: str, context: Optional[str] = None) -> List[Tuple[str, float]]:
        """获取拼写建议"""
        suggestions = []
        
        # 方法1：使用编辑距离从词典中查找相似词
        dict_suggestions = self._get_dict_suggestions(word)
        suggestions.extend(dict_suggestions)
        
        # 方法2：使用神经拼写检查器（如果可用）
        if self.spell_checker:
            neural_suggestions = self._get_neural_suggestions(word, context)
            suggestions.extend(neural_suggestions)
        
        # 方法3：使用语言模型
        if self.language_model and context:
            lm_suggestions = self._get_lm_suggestions(word, context)
            suggestions.extend(lm_suggestions)
        
        # 去重并排序
        unique_suggestions = {}
        for suggestion, confidence in suggestions:
            if suggestion not in unique_suggestions or confidence > unique_suggestions[suggestion]:
                unique_suggestions[suggestion] = confidence
        
        sorted_suggestions = sorted(
            unique_suggestions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_suggestions[:5]  # 返回前5个
    
    def _get_dict_suggestions(self, word: str) -> List[Tuple[str, float]]:
        """从词典获取建议"""
        suggestions = []
        
        # 计算与词典中词的编辑距离
        for dict_word in self.dictionary:
            if abs(len(dict_word) - len(word)) > 2:  # 长度差太大跳过
                continue
            
            # 计算相似度
            similarity = difflib.SequenceMatcher(None, word.lower(), dict_word).ratio()
            
            if similarity > 0.7:  # 相似度阈值
                suggestions.append((dict_word, similarity))
        
        # 按相似度排序
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:3]
    
    def _get_neural_suggestions(self, word: str, context: Optional[str] = None) -> List[Tuple[str, float]]:
        """使用神经模型获取建议"""
        suggestions = []
        
        try:
            # 准备输入
            input_text = context or ""
            if input_text:
                input_text += " " + word
            
            # 使用拼写检查模型
            # TODO: 实现实际的神经拼写检查
            # 这里使用简化版
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Neural suggestion failed: {e}")
            return suggestions
    
    def _get_lm_suggestions(self, word: str, context: str) -> List[Tuple[str, float]]:
        """使用语言模型获取建议"""
        suggestions = []
        
        try:
            # 使用语言模型预测
            predictions = self.language_model.predict_next(
                context,
                num_predictions=5,
                temperature=0.5
            )
            
            for pred in predictions:
                # 检查预测词是否与错误词相似
                similarity = difflib.SequenceMatcher(None, word.lower(), pred["text"].lower()).ratio()
                if similarity > 0.6:
                    suggestions.append((pred["text"], pred["probability"] * similarity))
            
            return suggestions
            
        except Exception as e:
            logger.error(f"LM suggestion failed: {e}")
            return suggestions
    
    def _check_grammar(self, text: str, context: Optional[str] = None) -> List[CorrectionCandidate]:
        """检查语法错误"""
        candidates = []
        
        if not self.grammar_checker:
            return candidates
        
        try:
            # 使用语法检查模型
            # TODO: 实现实际的语法检查
            # 这里使用简化规则
            
            # 规则1：检查主谓一致（英文）
            if self.current_language == "en-US":
                grammar_errors = self._check_english_grammar(text)
                candidates.extend(grammar_errors)
            
            # 规则2：检查常见语法错误
            common_errors = self._check_common_grammar_errors(text)
            candidates.extend(common_errors)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Grammar check failed: {e}")
            return candidates
    
    def _check_english_grammar(self, text: str) -> List[CorrectionCandidate]:
        """检查英文语法错误（简化版）"""
        candidates = []
        
        # 简单的规则检查
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            words = sentence.split()
            if len(words) < 2:
                continue
            
            # 检查句子首字母大写
            if sentence and sentence[0].islower():
                corrected = sentence[0].upper() + sentence[1:]
                candidate = CorrectionCandidate(
                    original=sentence,
                    corrected=corrected,
                    confidence=0.9,
                    error_type="grammar",
                    context={"rule": "sentence_capitalization"}
                )
                candidates.append(candidate)
            
            # 检查常见错误：their/there/they're
            for i, word in enumerate(words):
                word_lower = word.lower()
                if word_lower in ["their", "there", "they're"]:
                    # 检查上下文确定是否正确
                    # 这是一个简化实现
                    pass
        
        return candidates
    
    def _check_common_grammar_errors(self, text: str) -> List[CorrectionCandidate]:
        """检查常见语法错误"""
        candidates = []
        
        # 常见错误模式
        error_patterns = [
            (r'\ba lot\b', 'alot', 'a lot', 0.95),
            (r'\bcould of\b', 'could of', 'could have', 0.9),
            (r'\bshould of\b', 'should of', 'should have', 0.9),
            (r'\bwould of\b', 'would of', 'would have', 0.9),
            (r'\byour\s+a\b', 'your a', "you're a", 0.85),
        ]
        
        for pattern, original, corrected, confidence in error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                candidate = CorrectionCandidate(
                    original=original,
                    corrected=corrected,
                    confidence=confidence,
                    error_type="grammar",
                    context={"pattern": pattern}
                )
                candidates.append(candidate)
        
        return candidates
    
    def _check_punctuation(self, text: str) -> List[CorrectionCandidate]:
        """检查标点错误"""
        candidates = []
        
        # 检查多余的标点
        if re.search(r'[.!?]{2,}', text):
            # 替换多个标点为单个
            corrected = re.sub(r'([.!?])\1+', r'\1', text)
            if corrected != text:
                candidate = CorrectionCandidate(
                    original=text,
                    corrected=corrected,
                    confidence=0.8,
                    error_type="punctuation",
                    context={"rule": "multiple_punctuation"}
                )
                candidates.append(candidate)
        
        # 检查缺失的句号
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 1:
            # 检查最后一个句子是否以标点结尾
            last_sentence = sentences[-1].strip()
            if last_sentence and not text.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
                corrected = text.rstrip() + '.'
                candidate = CorrectionCandidate(
                    original=text,
                    corrected=corrected,
                    confidence=0.7,
                    error_type="punctuation",
                    context={"rule": "missing_period"}
                )
                candidates.append(candidate)
        
        # 检查空格标点（英文）
        if self.current_language == "en-US":
            # 检查标点前的空格
            if re.search(r'\s+[.,!?;:]', text):
                corrected = re.sub(r'\s+([.,!?;:])', r'\1', text)
                if corrected != text:
                    candidate = CorrectionCandidate(
                        original=text,
                        corrected=corrected,
                        confidence=0.85,
                        error_type="punctuation",
                        context={"rule": "space_before_punctuation"}
                    )
                    candidates.append(candidate)
            
            # 检查标点后缺少空格
            if re.search(r'[.,!?;:](?!\s|$)', text):
                corrected = re.sub(r'([.,!?;:])(?!\s|$)', r'\1 ', text)
                if corrected != text:
                    candidate = CorrectionCandidate(
                        original=text,
                        corrected=corrected,
                        confidence=0.85,
                        error_type="punctuation",
                        context={"rule": "missing_space_after_punctuation"}
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _check_style(self, text: str) -> List[CorrectionCandidate]:
        """检查样式问题"""
        candidates = []
        
        # 检查重复词
        words = self._tokenize(text)
        for i in range(len(words) - 1):
            if words[i] == words[i + 1] and self._is_word(words[i]):
                # 可能是错误重复
                corrected_words = words.copy()
                corrected_words.pop(i)  # 删除重复词
                corrected = ' '.join(corrected_words) if self.current_language == "en-US" else ''.join(corrected_words)
                
                candidate = CorrectionCandidate(
                    original=text,
                    corrected=corrected,
                    confidence=0.75,
                    error_type="style",
                    context={"rule": "repeated_word"}
                )
                candidates.append(candidate)
                break
        
        # 检查过长的句子（英文）
        if self.current_language == "en-US":
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if len(sentence.split()) > 30:  # 超过30词
                    # 建议拆分句子
                    candidate = CorrectionCandidate(
                        original=sentence.strip(),
                        corrected=f"{sentence.strip()} [Consider splitting this long sentence]",
                        confidence=0.6,
                        error_type="style",
                        context={"rule": "long_sentence"}
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _deduplicate_candidates(self, candidates: List[CorrectionCandidate]) -> List[CorrectionCandidate]:
        """去重校正候选"""
        unique_candidates = []
        seen_corrections = set()
        
        for candidate in candidates:
            correction_key = f"{candidate.original}->{candidate.corrected}"
            if correction_key not in seen_corrections:
                seen_corrections.add(correction_key)
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    def apply_correction(self, text: str, correction: CorrectionCandidate) -> str:
        """
        应用校正
        
        Args:
            text: 原始文本
            correction: 要应用的校正
            
        Returns:
            str: 校正后的文本
        """
        try:
            # 简单的替换
            corrected_text = text.replace(correction.original, correction.corrected)
            
            # 记录用户接受
            self._record_accepted_correction(correction)
            
            # 更新常见错误统计
            with self.lock:
                error_key = f"{correction.error_type}:{correction.original}"
                self.common_errors[error_key] += 1
            
            logger.info(f"Applied correction: {correction.original} -> {correction.corrected}")
            return corrected_text
            
        except Exception as e:
            logger.error(f"Failed to apply correction: {e}")
            return text
    
    def ignore_correction(self, correction: CorrectionCandidate) -> None:
        """
        忽略校正
        
        Args:
            correction: 要忽略的校正
        """
        # 添加到忽略列表
        self.ignored_corrections.add(correction.original)
        
        # 记录用户忽略
        self._record_ignored_correction(correction)
        
        logger.info(f"Ignored correction: {correction.original}")
    
    def _record_accepted_correction(self, correction: CorrectionCandidate) -> None:
        """记录用户接受的校正"""
        if not self.enable_learning:
            return
        
        with self.lock:
            self.user_corrections[correction.error_type].append({
                "original": correction.original,
                "corrected": correction.corrected,
                "confidence": correction.confidence,
                "timestamp": time.time()
            })
            
            # 限制历史大小
            if len(self.user_corrections[correction.error_type]) > 1000:
                self.user_corrections[correction.error_type] = self.user_corrections[correction.error_type][-500:]
    
    def _record_ignored_correction(self, correction: CorrectionCandidate) -> None:
        """记录用户忽略的校正"""
        if not self.enable_learning:
            return
        
        with self.lock:
            ignore_key = f"{correction.error_type}:{correction.original}"
            # 可以记录忽略的原因等
    
    def add_custom_rule(self, pattern: str, replacement: str, 
                       error_type: str = "custom", confidence: float = 0.8) -> None:
        """
        添加自定义校正规则
        
        Args:
            pattern: 匹配模式（正则表达式）
            replacement: 替换文本
            error_type: 错误类型
            confidence: 置信度
        """
        with self.lock:
            # TODO: 实现自定义规则存储
            logger.info(f"Added custom rule: {pattern} -> {replacement}")
    
    def learn_from_feedback(self, original: str, corrected: str, 
                           was_correct: bool, feedback: Optional[str] = None) -> None:
        """
        从用户反馈中学习
        
        Args:
            original: 原始文本
            corrected: 校正后的文本（或用户修改的文本）
            was_correct: 校正是否正确
            feedback: 用户反馈（可选）
        """
        if not self.enable_learning:
            return
        
        try:
            with self.lock:
                if was_correct:
                    # 强化这个校正
                    self._reinforce_correction(original, corrected)
                else:
                    # 学习用户修正
                    self._learn_from_user_correction(original, corrected)
                
                # 记录反馈
                self._record_feedback(original, corrected, was_correct, feedback)
                
                logger.debug(f"Learned from feedback: {original} -> {corrected}")
                
        except Exception as e:
            logger.error(f"Failed to learn from feedback: {e}")
    
    def _reinforce_correction(self, original: str, corrected: str) -> None:
        """强化校正"""
        # 增加常见错误计数
        error_key = f"spelling:{original}"
        self.common_errors[error_key] += 1
        
        # 可以更新模型权重等
    
    def _learn_from_user_correction(self, original: str, corrected: str) -> None:
        """从用户修正中学习"""
        # 添加到用户词典（如果是新词）
        if self._is_word(corrected):
            self.dictionary.add(corrected.lower())
        
        # 更新常见错误模式
        # TODO: 实现更复杂的学习逻辑
    
    def _record_feedback(self, original: str, corrected: str, 
                        was_correct: bool, feedback: Optional[str]) -> None:
        """记录用户反馈"""
        feedback_record = {
            "original": original,
            "corrected": corrected,
            "was_correct": was_correct,
            "feedback": feedback,
            "timestamp": time.time()
        }
        
        # 可以保存到文件或数据库
        feedback_file = f"data/user_data/correction_feedback/{self.current_language}.jsonl"
        os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
        
        with open(feedback_file, 'a', encoding='utf-8') as f:
            json.dump(feedback_record, f, ensure_ascii=False)
            f.write('\n')
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取自动校正统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            return {
                "current_language": self.current_language,
                "dictionary_size": len(self.dictionary),
                "common_errors_count": len(self.common_errors),
                "ignored_corrections_count": len(self.ignored_corrections),
                "user_corrections_total": sum(len(v) for v in self.user_corrections.values()),
                "has_spell_checker": self.spell_checker is not None,
                "has_grammar_checker": self.grammar_checker is not None,
                "enable_auto_correct": self.enable_auto_correct,
                "confidence_threshold": self.confidence_threshold
            }

