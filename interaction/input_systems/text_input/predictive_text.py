"""
预测文本模块：智能文本预测和自动补全
"""

import threading
import time
import json
import pickle
from typing import Dict, List, Tuple, Optional, Any, Set
import logging
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import heapq
import os

from data.models.nlp.language_models import LanguageModel
from cognitive.memory.semantic_memory import SemanticMemory
from infrastructure.communication.message_bus import MessageBus
from utils.ai_utilities.model_utils import ModelLoader
from config.system import ConfigManager

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PredictionCandidate:
    """预测候选词"""
    priority: float
    text: str = field(compare=False)
    confidence: float = field(compare=False)
    source: str = field(compare=False)  # ngram, neural, dictionary, etc.
    context: Dict[str, Any] = field(default_factory=dict, compare=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "source": self.source,
            "priority": self.priority
        }


class PredictiveText:
    """预测文本引擎"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化预测文本引擎
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 语言模型
        self.language_model = None
        self.neural_model = None
        
        # 数据存储
        self.ngram_model = defaultdict(Counter)  # n-gram 模型
        self.user_dictionary = set()  # 用户词典
        self.common_phrases = set()  # 常用短语
        
        # 缓存
        self.prediction_cache = {}  # context -> predictions
        self.user_patterns = defaultdict(Counter)  # 用户输入模式
        
        # 语义内存（用于上下文理解）
        self.semantic_memory = None
        
        # 配置参数
        self.max_predictions = 5
        self.ngram_order = 3
        self.cache_size = 1000
        self.learning_rate = 0.1
        
        # 状态
        self.is_active = False
        self.is_learning = True
        
        # 线程安全
        self.lock = threading.RLock()
        
        # 加载配置
        self.load_config()
        
        # 加载模型和数据
        self.load_models()
        self.load_dictionaries()
        
        logger.info("PredictiveText initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("predictive_text_config")
            
            # 基本配置
            self.enable_predictions = config.get("enable_predictions", True)
            self.enable_learning = config.get("enable_learning", True)
            self.enable_context_aware = config.get("enable_context_aware", True)
            
            # 模型参数
            model = config.get("model", {})
            self.max_predictions = model.get("max_predictions", 5)
            self.ngram_order = model.get("ngram_order", 3)
            self.min_confidence = model.get("min_confidence", 0.3)
            
            # 缓存参数
            cache = config.get("cache", {})
            self.cache_size = cache.get("cache_size", 1000)
            self.cache_ttl = cache.get("cache_ttl", 3600)  # 1小时
            
            # 学习参数
            learning = config.get("learning", {})
            self.learning_rate = learning.get("learning_rate", 0.1)
            self.max_user_words = learning.get("max_user_words", 10000)
            
            # 语言配置
            self.languages = config.get("supported_languages", ["zh-CN", "en-US"])
            self.current_language = config.get("default_language", "zh-CN")
            
            logger.debug(f"Predictive text config loaded: language={self.current_language}")
        except Exception as e:
            logger.error(f"Failed to load predictive text config: {e}")
    
    def load_models(self) -> None:
        """加载预测模型"""
        try:
            # 加载语言模型
            self.language_model = LanguageModel(language=self.current_language)
            
            # 加载神经预测模型
            model_path = f"data/models/nlp/predictive/{self.current_language}/model.pt"
            if os.path.exists(model_path):
                self.neural_model = ModelLoader.load_model(
                    model_path,
                    model_class="PredictiveModel"
                )
                logger.info(f"Loaded neural predictive model for {self.current_language}")
            else:
                logger.warning(f"Neural model not found at {model_path}, using n-gram only")
            
            # 加载n-gram模型
            ngram_path = f"data/models/nlp/predictive/{self.current_language}/ngram.pkl"
            if os.path.exists(ngram_path):
                with open(ngram_path, 'rb') as f:
                    self.ngram_model = pickle.load(f)
                logger.info(f"Loaded n-gram model for {self.current_language}")
            
            # 初始化语义内存
            self.semantic_memory = SemanticMemory()
            
            self.is_active = True
            logger.info("Predictive models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load predictive models: {e}")
            self.is_active = False
    
    def load_dictionaries(self) -> None:
        """加载词典"""
        try:
            # 加载用户词典
            user_dict_path = f"data/user_data/dictionaries/{self.current_language}_user.txt"
            if os.path.exists(user_dict_path):
                with open(user_dict_path, 'r', encoding='utf-8') as f:
                    self.user_dictionary = set(line.strip() for line in f if line.strip())
                logger.info(f"Loaded user dictionary: {len(self.user_dictionary)} words")
            
            # 加载常用短语
            phrases_path = f"data/models/nlp/predictive/{self.current_language}/phrases.txt"
            if os.path.exists(phrases_path):
                with open(phrases_path, 'r', encoding='utf-8') as f:
                    self.common_phrases = set(line.strip() for line in f if line.strip())
                logger.info(f"Loaded common phrases: {len(self.common_phrases)} phrases")
            
        except Exception as e:
            logger.error(f"Failed to load dictionaries: {e}")
    
    def predict(self, context: str, cursor_position: int = -1, 
                max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        预测下一个词或短语
        
        Args:
            context: 上下文文本
            cursor_position: 光标位置（-1表示在末尾）
            max_results: 最大结果数（None则使用默认值）
            
        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        if not self.is_active or not self.enable_predictions:
            return []
        
        max_results = max_results or self.max_predictions
        
        try:
            # 构建缓存键
            cache_key = self._create_cache_key(context, cursor_position)
            
            # 检查缓存
            with self.lock:
                if cache_key in self.prediction_cache:
                    cached = self.prediction_cache[cache_key]
                    if time.time() - cached["timestamp"] < self.cache_ttl:
                        logger.debug(f"Cache hit for: {context[:50]}...")
                        return cached["predictions"][:max_results]
            
            # 提取上下文特征
            features = self._extract_features(context, cursor_position)
            
            # 获取候选预测
            candidates = self._get_candidates(features)
            
            # 排序和筛选
            sorted_candidates = self._rank_candidates(candidates, features)
            
            # 转换为字典格式
            predictions = [
                candidate.to_dict() for candidate in sorted_candidates[:max_results]
            ]
            
            # 更新缓存
            with self.lock:
                self.prediction_cache[cache_key] = {
                    "predictions": predictions,
                    "timestamp": time.time(),
                    "features": features
                }
                
                # 清理过期缓存
                self._clean_cache()
            
            logger.debug(f"Generated {len(predictions)} predictions for context: {context[:50]}...")
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []
    
    def _create_cache_key(self, context: str, cursor_position: int) -> str:
        """创建缓存键"""
        # 使用简化的上下文（最后N个字符）
        if cursor_position == -1:
            relevant_context = context[-100:]  # 最后100个字符
        else:
            relevant_context = context[max(0, cursor_position - 50):cursor_position]
        
        return f"{self.current_language}:{hash(relevant_context)}:{cursor_position}"
    
    def _extract_features(self, context: str, cursor_position: int) -> Dict[str, Any]:
        """提取上下文特征"""
        features = {
            "language": self.current_language,
            "context_length": len(context),
            "cursor_position": cursor_position,
            "timestamp": time.time()
        }
        
        # 提取当前词
        current_word = self._get_current_word(context, cursor_position)
        features["current_word"] = current_word
        
        # 提取前文（用于n-gram）
        preceding_text = self._get_preceding_text(context, cursor_position)
        features["preceding_text"] = preceding_text
        
        # 提取n-gram上下文
        ngram_context = self._extract_ngram_context(preceding_text)
        features["ngram_context"] = ngram_context
        
        # 获取语义上下文（如果启用）
        if self.enable_context_aware and self.semantic_memory:
            semantic_context = self.semantic_memory.get_context()
            features["semantic_context"] = semantic_context
        
        # 分析上下文类型
        context_type = self._analyze_context_type(context, cursor_position)
        features["context_type"] = context_type
        
        return features
    
    def _get_current_word(self, context: str, cursor_position: int) -> str:
        """获取当前正在输入的词"""
        if cursor_position == -1:
            cursor_position = len(context)
        
        # 向前查找词的开头
        start = cursor_position
        while start > 0 and context[start - 1].isalnum():
            start -= 1
        
        # 向后查找词的结尾
        end = cursor_position
        while end < len(context) and context[end].isalnum():
            end += 1
        
        return context[start:end]
    
    def _get_preceding_text(self, context: str, cursor_position: int) -> str:
        """获取光标前的内容"""
        if cursor_position == -1:
            return context
        return context[:cursor_position]
    
    def _extract_ngram_context(self, text: str) -> List[str]:
        """提取n-gram上下文"""
        if not text:
            return []
        
        # 分词
        words = self._tokenize(text)
        
        # 取最后N-1个词作为上下文
        n = min(self.ngram_order - 1, len(words))
        return words[-n:]
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单的分词，实际应用应该使用语言特定的分词器
        if self.current_language == "zh-CN":
            # 中文分词（简化版）
            # TODO: 使用jieba等专业分词器
            import re
            return re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+|[^\w\s]', text)
        else:
            # 英文分词
            return text.split()
    
    def _analyze_context_type(self, context: str, cursor_position: int) -> str:
        """分析上下文类型"""
        if cursor_position == -1:
            text_to_analyze = context
        else:
            text_to_analyze = context[:cursor_position]
        
        if not text_to_analyze:
            return "general"
        
        # 简单的类型检测
        if any(char in text_to_analyze for char in '@'):
            return "email"
        elif any(char in text_to_analyze for char in '://'):
            return "url"
        elif text_to_analyze.strip().endswith(':'):
            return "label"
        elif text_to_analyze.count(' ') < 3:
            return "short"
        else:
            return "general"
    
    def _get_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """获取候选预测"""
        candidates = []
        
        # 1. 从n-gram模型获取候选
        ngram_candidates = self._get_ngram_candidates(features)
        candidates.extend(ngram_candidates)
        
        # 2. 从神经模型获取候选（如果可用）
        if self.neural_model:
            neural_candidates = self._get_neural_candidates(features)
            candidates.extend(neural_candidates)
        
        # 3. 从用户词典获取候选
        user_candidates = self._get_user_candidates(features)
        candidates.extend(user_candidates)
        
        # 4. 从常用短语获取候选
        phrase_candidates = self._get_phrase_candidates(features)
        candidates.extend(phrase_candidates)
        
        # 5. 基于语义上下文获取候选
        if self.enable_context_aware:
            semantic_candidates = self._get_semantic_candidates(features)
            candidates.extend(semantic_candidates)
        
        return candidates
    
    def _get_ngram_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """从n-gram模型获取候选"""
        candidates = []
        ngram_context = features.get("ngram_context", [])
        
        if not ngram_context:
            return candidates
        
        # 构建n-gram键
        context_key = " ".join(ngram_context[-self.ngram_order+1:])
        
        with self.lock:
            if context_key in self.ngram_model:
                word_counts = self.ngram_model[context_key]
                total_count = sum(word_counts.values())
                
                for word, count in word_counts.most_common(10):
                    confidence = count / total_count
                    if confidence >= self.min_confidence:
                        candidate = PredictionCandidate(
                            priority=confidence * 0.8,  # n-gram权重
                            text=word,
                            confidence=confidence,
                            source="ngram",
                            context={"ngram_context": context_key}
                        )
                        candidates.append(candidate)
        
        return candidates
    
    def _get_neural_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """从神经模型获取候选"""
        candidates = []
        
        try:
            # 准备输入
            input_text = features.get("preceding_text", "")
            if not input_text:
                return candidates
            
            # 使用语言模型生成预测
            predictions = self.language_model.predict_next(
                input_text,
                num_predictions=10,
                temperature=0.7
            )
            
            for pred in predictions:
                candidate = PredictionCandidate(
                    priority=pred["probability"] * 0.9,  # 神经模型权重
                    text=pred["text"],
                    confidence=pred["probability"],
                    source="neural",
                    context={"model": "language_model"}
                )
                candidates.append(candidate)
                
        except Exception as e:
            logger.error(f"Neural prediction failed: {e}")
        
        return candidates
    
    def _get_user_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """从用户词典获取候选"""
        candidates = []
        current_word = features.get("current_word", "")
        
        if not current_word:
            return candidates
        
        # 查找用户词典中以当前词开头的词
        matching_words = [
            word for word in self.user_dictionary
            if word.lower().startswith(current_word.lower())
        ]
        
        for word in matching_words[:5]:  # 取前5个
            # 计算相似度（简单的基于前缀）
            similarity = len(current_word) / len(word)
            
            candidate = PredictionCandidate(
                priority=similarity * 0.7,  # 用户词典权重
                text=word,
                confidence=similarity,
                source="user_dictionary",
                context={"current_word": current_word}
            )
            candidates.append(candidate)
        
        return candidates
    
    def _get_phrase_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """从常用短语获取候选"""
        candidates = []
        current_word = features.get("current_word", "")
        context_type = features.get("context_type", "general")
        
        if not current_word:
            # 如果没有当前词，提供完整的常用短语
            for phrase in list(self.common_phrases)[:5]:
                candidate = PredictionCandidate(
                    priority=0.5,  # 常用短语基础权重
                    text=phrase,
                    confidence=0.8,
                    source="common_phrases",
                    context={"context_type": context_type}
                )
                candidates.append(candidate)
        else:
            # 查找包含当前词的短语
            for phrase in self.common_phrases:
                if current_word.lower() in phrase.lower():
                    candidate = PredictionCandidate(
                        priority=0.6,  # 匹配短语权重
                        text=phrase,
                        confidence=0.7,
                        source="common_phrases",
                        context={"current_word": current_word}
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _get_semantic_candidates(self, features: Dict[str, Any]) -> List[PredictionCandidate]:
        """基于语义上下文获取候选"""
        candidates = []
        
        if not self.semantic_memory:
            return candidates
        
        try:
            semantic_context = features.get("semantic_context", {})
            current_topic = semantic_context.get("current_topic")
            recent_concepts = semantic_context.get("recent_concepts", [])
            
            if current_topic:
                # 获取与当前主题相关的词
                related_words = self.semantic_memory.get_related_concepts(
                    current_topic, 
                    max_results=5
                )
                
                for word, relevance in related_words:
                    candidate = PredictionCandidate(
                        priority=relevance * 0.85,  # 语义相关权重
                        text=word,
                        confidence=relevance,
                        source="semantic",
                        context={"topic": current_topic}
                    )
                    candidates.append(candidate)
            
        except Exception as e:
            logger.error(f"Semantic prediction failed: {e}")
        
        return candidates
    
    def _rank_candidates(self, candidates: List[PredictionCandidate], 
                        features: Dict[str, Any]) -> List[PredictionCandidate]:
        """对候选进行排序"""
        if not candidates:
            return []
        
        # 使用堆排序获取优先级最高的候选
        heap = []
        for candidate in candidates:
            # 调整优先级基于上下文
            adjusted_priority = self._adjust_priority(candidate, features)
            heapq.heappush(heap, (-adjusted_priority, candidate))  # 使用负值因为heapq是最小堆
        
        # 提取排序后的候选
        sorted_candidates = []
        while heap and len(sorted_candidates) < self.max_predictions * 2:  # 取两倍然后去重
            _, candidate = heapq.heappop(heap)
            sorted_candidates.append(candidate)
        
        # 去重
        unique_candidates = []
        seen_texts = set()
        
        for candidate in sorted_candidates:
            if candidate.text not in seen_texts:
                seen_texts.add(candidate.text)
                unique_candidates.append(candidate)
            
            if len(unique_candidates) >= self.max_predictions:
                break
        
        return unique_candidates
    
    def _adjust_priority(self, candidate: PredictionCandidate, 
                        features: Dict[str, Any]) -> float:
        """基于上下文调整优先级"""
        adjusted = candidate.priority
        
        # 基于上下文类型调整
        context_type = features.get("context_type", "general")
        if context_type == "email" and "@" in candidate.text:
            adjusted *= 1.2
        elif context_type == "url" and ("http" in candidate.text or "www" in candidate.text):
            adjusted *= 1.2
        
        # 基于用户模式调整
        current_word = features.get("current_word", "")
        if current_word and current_word in self.user_patterns:
            if candidate.text in self.user_patterns[current_word]:
                pattern_weight = self.user_patterns[current_word][candidate.text]
                adjusted *= (1.0 + pattern_weight)
        
        # 基于时间调整（最近学习的内容权重更高）
        if "learned_at" in candidate.context:
            learned_time = candidate.context["learned_at"]
            time_diff = time.time() - learned_time
            if time_diff < 3600:  # 1小时内学习的
                adjusted *= 1.1
        
        return min(adjusted, 1.0)  # 确保不超过1.0
    
    def _clean_cache(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        
        for key, value in self.prediction_cache.items():
            if current_time - value["timestamp"] > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.prediction_cache[key]
        
        # 如果缓存仍然太大，删除最旧的条目
        while len(self.prediction_cache) > self.cache_size:
            oldest_key = min(
                self.prediction_cache.keys(),
                key=lambda k: self.prediction_cache[k]["timestamp"]
            )
            del self.prediction_cache[oldest_key]
    
    def learn_from_input(self, text: str, accepted_prediction: Optional[str] = None) -> None:
        """
        从用户输入中学习
        
        Args:
            text: 用户输入的文本
            accepted_prediction: 用户接受的预测（如果有）
        """
        if not self.is_learning:
            return
        
        try:
            with self.lock:
                # 分词
                words = self._tokenize(text)
                
                # 更新n-gram模型
                self._update_ngram_model(words)
                
                # 更新用户词典
                self._update_user_dictionary(words)
                
                # 更新用户模式
                if accepted_prediction:
                    self._update_user_patterns(text, accepted_prediction)
                
                # 通知语义内存
                if self.semantic_memory:
                    self.semantic_memory.learn_from_text(text)
                
                logger.debug(f"Learned from input: {text[:50]}...")
                
        except Exception as e:
            logger.error(f"Learning failed: {e}")
    
    def _update_ngram_model(self, words: List[str]) -> None:
        """更新n-gram模型"""
        if len(words) < self.ngram_order:
            return
        
        for i in range(len(words) - self.ngram_order + 1):
            # 构建上下文和下一个词
            context = " ".join(words[i:i+self.ngram_order-1])
            next_word = words[i+self.ngram_order-1]
            
            # 更新计数
            self.ngram_model[context][next_word] += 1
            
            # 限制模型大小
            if len(self.ngram_model[context]) > 100:
                # 保留最常见的100个
                most_common = self.ngram_model[context].most_common(100)
                self.ngram_model[context] = Counter(dict(most_common))
    
    def _update_user_dictionary(self, words: List[str]) -> None:
        """更新用户词典"""
        for word in words:
            if len(word) > 1 and word.isalpha():  # 只添加字母词
                self.user_dictionary.add(word)
        
        # 限制词典大小
        if len(self.user_dictionary) > self.max_user_words:
            # 转换为列表，删除最旧的词（这里简化处理：随机删除）
            user_list = list(self.user_dictionary)
            self.user_dictionary = set(user_list[-self.max_user_words:])
    
    def _update_user_patterns(self, context: str, accepted_prediction: str) -> None:
        """更新用户模式"""
        # 提取当前词
        current_word = self._get_current_word(context, -1)
        
        if current_word and accepted_prediction:
            # 更新模式计数器
            self.user_patterns[current_word][accepted_prediction] += 1
            
            # 限制模式数量
            if len(self.user_patterns[current_word]) > 20:
                most_common = self.user_patterns[current_word].most_common(20)
                self.user_patterns[current_word] = Counter(dict(most_common))
    
    def save_models(self) -> bool:
        """
        保存模型到磁盘
        
        Returns:
            bool: 是否成功保存
        """
        try:
            # 创建目录
            model_dir = f"data/models/nlp/predictive/{self.current_language}"
            os.makedirs(model_dir, exist_ok=True)
            
            # 保存n-gram模型
            ngram_path = os.path.join(model_dir, "ngram.pkl")
            with open(ngram_path, 'wb') as f:
                pickle.dump(self.ngram_model, f)
            
            # 保存用户词典
            dict_path = f"data/user_data/dictionaries/{self.current_language}_user.txt"
            with open(dict_path, 'w', encoding='utf-8') as f:
                for word in sorted(self.user_dictionary):
                    f.write(f"{word}\n")
            
            logger.info("Predictive models saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
            return False
    
    def set_language(self, language: str) -> bool:
        """
        设置预测语言
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否成功设置
        """
        if language not in self.languages:
            logger.error(f"Unsupported language: {language}")
            return False
        
        try:
            # 保存当前模型
            self.save_models()
            
            # 更新语言
            self.current_language = language
            
            # 重新加载模型
            self.load_models()
            self.load_dictionaries()
            
            # 清空缓存
            self.prediction_cache.clear()
            
            # 通知其他组件
            self.message_bus.publish("predictive_text_language_changed", {
                "language": language,
                "timestamp": time.time()
            })
            
            logger.info(f"Predictive text language set to: {language}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False
    
    def add_custom_word(self, word: str, frequency: int = 1) -> None:
        """
        添加自定义词到用户词典
        
        Args:
            word: 要添加的词
            frequency: 初始频率
        """
        with self.lock:
            self.user_dictionary.add(word)
            
            # 也可以添加到n-gram模型
            if len(word.split()) == 1:  # 单个词
                # 添加到各种上下文中
                for context in list(self.ngram_model.keys())[:10]:  # 添加到前10个上下文
                    self.ngram_model[context][word] += frequency
            
            logger.info(f"Added custom word: {word}")
    
    def add_custom_phrase(self, phrase: str) -> None:
        """
        添加自定义短语
        
        Args:
            phrase: 要添加的短语
        """
        self.common_phrases.add(phrase)
        logger.info(f"Added custom phrase: {phrase}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取预测文本统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        with self.lock:
            return {
                "is_active": self.is_active,
                "is_learning": self.is_learning,
                "current_language": self.current_language,
                "ngram_model_size": len(self.ngram_model),
                "user_dictionary_size": len(self.user_dictionary),
                "common_phrases_size": len(self.common_phrases),
                "prediction_cache_size": len(self.prediction_cache),
                "user_patterns_size": len(self.user_patterns),
                "max_predictions": self.max_predictions,
                "min_confidence": self.min_confidence
            }

