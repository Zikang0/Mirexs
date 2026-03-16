"""
注意力机制模块：关注重要信息
实现基于多因素加权的注意力系统
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import datetime
import logging

class AttentionType(Enum):
    BOTTOM_UP = "bottom_up"      # 数据驱动
    TOP_DOWN = "top_down"        # 目标驱动
    SALIENCY = "saliency"        # 显著性驱动
    EXPECTATION = "expectation"  # 期望驱动

class AttentionMechanism:
    """注意力机制系统 - 关注重要信息"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 注意力权重配置
        self.weights = {
            'recency': self.config.get('recency_weight', 0.25),
            'importance': self.config.get('importance_weight', 0.30),
            'relevance': self.config.get('relevance_weight', 0.25),
            'novelty': self.config.get('novelty_weight', 0.10),
            'emotional': self.config.get('emotional_weight', 0.10)
        }
        
        # 注意力阈值
        self.attention_threshold = self.config.get('attention_threshold', 0.3)
        self.focus_threshold = self.config.get('focus_threshold', 0.7)
        
        # 注意力状态
        self.current_focus = None
        self.attention_history = []
        self.attention_span = self.config.get('attention_span', 10)  # 关注的项目数
        
        # 显著性检测器
        self.saliency_detectors = {}
        self._initialize_saliency_detectors()
        
        self.initialized = True
        self.logger.info("注意力机制系统初始化成功")
    
    def _initialize_saliency_detectors(self):
        """初始化显著性检测器"""
        # 文本显著性检测
        self.saliency_detectors['text'] = self._detect_text_saliency
        # 视觉显著性检测
        self.saliency_detectors['visual'] = self._detect_visual_saliency
        # 音频显著性检测
        self.saliency_detectors['audio'] = self._detect_audio_saliency
    
    def compute_attention_scores(self,
                               items: List[Dict[str, Any]],
                               context: Dict[str, Any] = None,
                               attention_type: AttentionType = AttentionType.BOTTOM_UP) -> List[Tuple[Dict, float]]:
        """
        计算注意力分数
        
        Args:
            items: 待评分项目列表
            context: 上下文信息
            attention_type: 注意力类型
            
        Returns:
            (项目, 注意力分数) 元组列表
        """
        if not items:
            return []
        
        context = context or {}
        scored_items = []
        
        for item in items:
            score = self._compute_item_attention_score(item, context, attention_type)
            scored_items.append((item, score))
        
        # 按分数排序
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # 记录注意力分配
        self._record_attention_allocation(scored_items, attention_type)
        
        return scored_items
    
    def _compute_item_attention_score(self,
                                    item: Dict[str, Any],
                                    context: Dict[str, Any],
                                    attention_type: AttentionType) -> float:
        """计算单个项目的注意力分数"""
        scores = {}
        
        # 计算各项分数
        scores['recency'] = self._compute_recency_score(item, context)
        scores['importance'] = self._compute_importance_score(item, context)
        scores['relevance'] = self._compute_relevance_score(item, context)
        scores['novelty'] = self._compute_novelty_score(item, context)
        scores['emotional'] = self._compute_emotional_score(item, context)
        
        # 根据注意力类型调整权重
        adjusted_weights = self._adjust_weights_for_type(attention_type)
        
        # 计算加权总分
        total_score = 0.0
        total_weight = 0.0
        
        for factor, weight in adjusted_weights.items():
            factor_score = scores.get(factor, 0)
            total_score += factor_score * weight
            total_weight += weight
        
        if total_weight > 0:
            total_score /= total_weight
        
        # 应用显著性增强
        saliency_boost = self._compute_saliency_boost(item, context)
        total_score *= (1.0 + saliency_boost)
        
        return min(1.0, total_score)  # 确保不超过1.0
    
    def _compute_recency_score(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算时效性分数"""
        timestamp = item.get('timestamp')
        if not timestamp:
            return 0.5
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return 0.5
        
        now = datetime.datetime.now()
        time_diff = (now - timestamp).total_seconds() / 3600  # 小时
        
        # 指数衰减：24小时后衰减到约0.37
        recency = np.exp(-time_diff / 24.0)
        return recency
    
    def _compute_importance_score(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算重要性分数"""
        # 基于显式重要性标签
        explicit_importance = item.get('importance', 0.5)
        
        # 基于上下文的重要性推断
        contextual_importance = self._infer_contextual_importance(item, context)
        
        # 基于访问频率的重要性
        access_importance = min(1.0, item.get('access_count', 0) / 10.0)
        
        # 综合重要性
        importance = (explicit_importance * 0.5 + 
                     contextual_importance * 0.3 + 
                     access_importance * 0.2)
        
        return importance
    
    def _compute_relevance_score(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算相关性分数"""
        current_goal = context.get('current_goal')
        if not current_goal:
            return 0.5
        
        # 基于语义相似性
        semantic_similarity = self._compute_semantic_similarity(item, current_goal)
        
        # 基于任务相关性
        task_relevance = self._compute_task_relevance(item, context)
        
        # 基于历史相关性模式
        historical_relevance = self._compute_historical_relevance(item, context)
        
        relevance = (semantic_similarity * 0.4 + 
                    task_relevance * 0.4 + 
                    historical_relevance * 0.2)
        
        return relevance
    
    def _compute_novelty_score(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算新颖性分数"""
        # 基于首次出现
        is_first_occurrence = item.get('first_occurrence', False)
        first_occurrence_score = 1.0 if is_first_occurrence else 0.0
        
        # 基于模式偏离
        pattern_deviation = self._compute_pattern_deviation(item, context)
        
        # 基于信息熵
        information_entropy = self._compute_information_entropy(item)
        
        novelty = (first_occurrence_score * 0.4 + 
                  pattern_deviation * 0.4 + 
                  information_entropy * 0.2)
        
        return novelty
    
    def _compute_emotional_score(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算情感分数"""
        # 情感强度
        emotional_intensity = abs(item.get('emotional_valence', 0))
        
        # 情感一致性
        emotional_coherence = self._compute_emotional_coherence(item, context)
        
        # 情感显著性
        emotional_salience = self._compute_emotional_salience(item)
        
        emotional_score = (emotional_intensity * 0.5 + 
                          emotional_coherence * 0.3 + 
                          emotional_salience * 0.2)
        
        return emotional_score
    
    def _infer_contextual_importance(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """推断上下文重要性"""
        # 基于与当前任务的关系
        task_relation = context.get('task_relevance', {}).get(item.get('id'), 0.5)
        
        # 基于用户显式标记
        user_marked_importance = item.get('user_importance', 0.5)
        
        # 基于社交重要性
        social_importance = item.get('social_significance', 0.5)
        
        return (task_relation * 0.4 + user_marked_importance * 0.4 + social_importance * 0.2)
    
    def _compute_semantic_similarity(self, item: Dict[str, Any], goal: str) -> float:
        """计算语义相似性"""
        # 简化实现 - 实际系统中应使用嵌入模型
        item_text = str(item.get('content', '')) + str(item.get('description', ''))
        goal_words = set(goal.lower().split())
        item_words = set(item_text.lower().split())
        
        if not goal_words or not item_words:
            return 0.0
        
        intersection = goal_words.intersection(item_words)
        similarity = len(intersection) / len(goal_words)
        
        return similarity
    
    def _compute_task_relevance(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算任务相关性"""
        current_tasks = context.get('active_tasks', [])
        if not current_tasks:
            return 0.5
        
        item_categories = item.get('categories', [])
        item_skills = item.get('required_skills', [])
        
        max_relevance = 0.0
        for task in current_tasks:
            task_categories = task.get('categories', [])
            task_skills = task.get('required_skills', [])
            
            # 类别匹配
            category_match = len(set(item_categories).intersection(task_categories)) / max(1, len(task_categories))
            
            # 技能匹配
            skill_match = len(set(item_skills).intersection(task_skills)) / max(1, len(task_skills))
            
            relevance = (category_match + skill_match) / 2
            max_relevance = max(max_relevance, relevance)
        
        return max_relevance
    
    def _compute_historical_relevance(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算历史相关性"""
        # 基于过去在类似上下文中的有用性
        historical_usefulness = item.get('historical_usefulness', 0.5)
        
        # 基于使用模式
        usage_pattern = self._analyze_usage_pattern(item, context)
        
        return (historical_usefulness + usage_pattern) / 2
    
    def _compute_pattern_deviation(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算模式偏离度"""
        # 基于与典型模式的差异
        typical_pattern = context.get('typical_pattern', {})
        if not typical_pattern:
            return 0.5
        
        # 计算特征差异
        features = ['size', 'frequency', 'duration', 'complexity']
        total_deviation = 0.0
        valid_features = 0
        
        for feature in features:
            typical_value = typical_pattern.get(feature)
            item_value = item.get(feature)
            
            if typical_value is not None and item_value is not None:
                deviation = abs(typical_value - item_value) / max(typical_value, 1.0)
                total_deviation += deviation
                valid_features += 1
        
        if valid_features == 0:
            return 0.5
        
        avg_deviation = total_deviation / valid_features
        # 偏离度越高，新颖性越高
        return min(1.0, avg_deviation)
    
    def _compute_information_entropy(self, item: Dict[str, Any]) -> float:
        """计算信息熵"""
        # 简化实现 - 基于内容变化性
        content = str(item.get('content', ''))
        if not content:
            return 0.0
        
        # 计算字符级熵
        from collections import Counter
        char_counts = Counter(content)
        total_chars = len(content)
        
        entropy = 0.0
        for count in char_counts.values():
            probability = count / total_chars
            entropy -= probability * np.log2(probability)
        
        # 归一化到0-1范围
        max_entropy = np.log2(len(set(content))) if content else 0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        return normalized_entropy
    
    def _compute_emotional_coherence(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算情感一致性"""
        current_mood = context.get('current_mood', 0.0)
        item_valence = item.get('emotional_valence', 0.0)
        
        # 情感一致性：与当前情绪状态的一致性
        coherence = 1.0 - abs(current_mood - item_valence) / 2.0
        return coherence
    
    def _compute_emotional_salience(self, item: Dict[str, Any]) -> float:
        """计算情感显著性"""
        # 基于情感极性和强度
        valence = item.get('emotional_valence', 0.0)
        arousal = item.get('emotional_arousal', 0.0)
        
        # 情感显著性 = |效价| * 唤醒度
        salience = abs(valence) * arousal
        return salience
    
    def _compute_saliency_boost(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """计算显著性增强"""
        modality = item.get('modality', 'text')
        detector = self.saliency_detectors.get(modality)
        
        if detector:
            return detector(item, context)
        return 0.0
    
    def _detect_text_saliency(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """检测文本显著性"""
        text = str(item.get('content', ''))
        if not text:
            return 0.0
        
        # 基于关键词密度
        salient_keywords = context.get('salient_keywords', [])
        keyword_matches = sum(1 for keyword in salient_keywords if keyword.lower() in text.lower())
        keyword_density = keyword_matches / max(1, len(salient_keywords))
        
        # 基于文本特征（大写、标点等）
        features = self._analyze_text_features(text)
        
        saliency = (keyword_density * 0.6 + features * 0.4)
        return saliency
    
    def _detect_visual_saliency(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """检测视觉显著性"""
        # 简化实现 - 实际应使用计算机视觉
        visual_features = item.get('visual_features', {})
        
        contrast = visual_features.get('contrast', 0.5)
        color_variance = visual_features.get('color_variance', 0.5)
        motion = visual_features.get('motion', 0.0)
        
        saliency = (contrast * 0.4 + color_variance * 0.3 + motion * 0.3)
        return saliency
    
    def _detect_audio_saliency(self, item: Dict[str, Any], context: Dict[str, Any]) -> float:
        """检测音频显著性"""
        # 简化实现
        audio_features = item.get('audio_features', {})
        
        volume = audio_features.get('volume', 0.5)
        pitch_variance = audio_features.get('pitch_variance', 0.5)
        tempo = audio_features.get('tempo', 0.5)
        
        saliency = (volume * 0.4 + pitch_variance * 0.3 + tempo * 0.3)
        return saliency
    
    def _analyze_text_features(self, text: str) -> float:
        """分析文本特征"""
        if not text:
            return 0.0
        
        # 大写字母比例
        uppercase_ratio = sum(1 for c in text if c.isupper()) / len(text)
        
        # 标点密度
        punctuation = set('!?¡¿')
        punctuation_ratio = sum(1 for c in text if c in punctuation) / len(text)
        
        # 情感词密度（简化）
        emotional_words = {'amazing', 'terrible', 'wonderful', 'horrible', 'love', 'hate'}
        words = text.lower().split()
        emotional_ratio = sum(1 for word in words if word in emotional_words) / max(1, len(words))
        
        features = (uppercase_ratio * 0.4 + punctuation_ratio * 0.3 + emotional_ratio * 0.3)
        return features
    
    def _adjust_weights_for_type(self, attention_type: AttentionType) -> Dict[str, float]:
        """根据注意力类型调整权重"""
        base_weights = self.weights.copy()
        
        if attention_type == AttentionType.TOP_DOWN:
            # 目标驱动：提高相关性和重要性权重
            base_weights['relevance'] *= 1.5
            base_weights['importance'] *= 1.3
            base_weights['novelty'] *= 0.7
        
        elif attention_type == AttentionType.SALIENCY:
            # 显著性驱动：提高新颖性和情感权重
            base_weights['novelty'] *= 1.5
            base_weights['emotional'] *= 1.3
            base_weights['recency'] *= 0.8
        
        elif attention_type == AttentionType.EXPECTATION:
            # 期望驱动：提高相关性和时效性权重
            base_weights['relevance'] *= 1.4
            base_weights['recency'] *= 1.2
            base_weights['novelty'] *= 0.6
        
        # 归一化权重
        total = sum(base_weights.values())
        if total > 0:
            for key in base_weights:
                base_weights[key] /= total
        
        return base_weights
    
    def _record_attention_allocation(self, 
                                   scored_items: List[Tuple[Dict, float]], 
                                   attention_type: AttentionType):
        """记录注意力分配"""
        allocation = {
            'timestamp': datetime.datetime.now().isoformat(),
            'attention_type': attention_type.value,
            'total_items': len(scored_items),
            'focused_item': scored_items[0][0] if scored_items else None,
            'focus_score': scored_items[0][1] if scored_items else 0.0,
            'attention_distribution': [
                {'item_id': item.get('id'), 'score': score}
                for item, score in scored_items[:5]  # 记录前5个
            ]
        }
        
        self.attention_history.append(allocation)
        
        # 保持历史记录长度
        if len(self.attention_history) > 100:
            self.attention_history = self.attention_history[-100:]
        
        # 更新当前焦点
        if scored_items and scored_items[0][1] >= self.focus_threshold:
            self.current_focus = scored_items[0][0]
    
    def get_attention_focus(self) -> Optional[Dict[str, Any]]:
        """获取当前注意力焦点"""
        return self.current_focus
    
    def shift_attention(self, new_focus: Dict[str, Any], context: Dict[str, Any] = None):
        """主动转移注意力"""
        old_focus = self.current_focus
        self.current_focus = new_focus
        
        # 记录注意力转移
        shift_record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'from_focus': old_focus,
            'to_focus': new_focus,
            'context': context or {}
        }
        
        self.logger.info(f"注意力转移: {old_focus} -> {new_focus}")
    
    def get_attention_history(self, 
                            limit: int = 20,
                            attention_type: str = None) -> List[Dict[str, Any]]:
        """获取注意力历史"""
        history = self.attention_history.copy()
        
        if attention_type:
            history = [h for h in history if h.get('attention_type') == attention_type]
        
        return history[-limit:] if limit else history
    
    def analyze_attention_patterns(self) -> Dict[str, Any]:
        """分析注意力模式"""
        if not self.attention_history:
            return {"error": "无注意力历史数据"}
        
        # 分析注意力类型分布
        type_distribution = {}
        for record in self.attention_history:
            att_type = record.get('attention_type', 'unknown')
            type_distribution[att_type] = type_distribution.get(att_type, 0) + 1
        
        # 分析注意力稳定性
        focus_changes = 0
        last_focus = None
        for record in self.attention_history:
            current_focus = record.get('focused_item', {}).get('id')
            if current_focus != last_focus:
                focus_changes += 1
                last_focus = current_focus
        
        stability = 1.0 - (focus_changes / len(self.attention_history))
        
        # 分析平均注意力分数
        avg_scores = {}
        score_counts = {}
        
        for record in self.attention_history:
            for item in record.get('attention_distribution', []):
                item_id = item.get('item_id')
                score = item.get('score', 0)
                
                if item_id not in avg_scores:
                    avg_scores[item_id] = 0
                    score_counts[item_id] = 0
                
                avg_scores[item_id] += score
                score_counts[item_id] += 1
        
        for item_id in avg_scores:
            avg_scores[item_id] /= score_counts[item_id]
        
        return {
            "total_attention_records": len(self.attention_history),
            "attention_type_distribution": type_distribution,
            "attention_stability": stability,
            "focus_change_count": focus_changes,
            "average_scores_by_item": avg_scores,
            "current_focus": self.current_focus
        }

