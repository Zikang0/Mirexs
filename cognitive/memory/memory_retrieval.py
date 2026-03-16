"""
记忆检索模块：从记忆中检索相关信息
实现基于多模态查询的记忆检索系统
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .procedural_memory import ProceduralMemory

class RetrievalStrategy(Enum):
    SEMANTIC_SIMILARITY = "semantic_similarity"
    TEMPORAL_PROXIMITY = "temporal_proximity"
    ASSOCIATIVE_CHAINING = "associative_chaining"
    CONTEXTUAL_RELEVANCE = "contextual_relevance"
    HYBRID = "hybrid"

class MemoryRetrieval:
    """记忆检索系统 - 从记忆中检索相关信息"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化各记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        self.procedural_memory = ProceduralMemory(config.get('procedural_config', {}))
        
        # 检索配置
        self.default_strategy = RetrievalStrategy(self.config.get('default_strategy', 'hybrid'))
        self.max_results = self.config.get('max_results', 10)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.6)
        
        # 检索缓存
        self.retrieval_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5分钟
        
        self.initialized = True
        self.logger.info("记忆检索系统初始化成功")
    
    def retrieve(self,
                query: str,
                context: Dict[str, Any] = None,
                strategy: RetrievalStrategy = None,
                memory_types: List[str] = None,
                limit: int = None) -> Dict[str, Any]:
        """
        检索记忆
        
        Args:
            query: 查询内容
            context: 上下文信息
            strategy: 检索策略
            memory_types: 记忆类型过滤
            limit: 结果数量限制
            
        Returns:
            检索结果
        """
        strategy = strategy or self.default_strategy
        context = context or {}
        limit = limit or self.max_results
        memory_types = memory_types or ['episodic', 'semantic', 'procedural']
        
        # 检查缓存
        cache_key = self._generate_cache_key(query, context, strategy, memory_types)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("使用缓存检索结果")
            return cached_result
        
        # 执行检索
        start_time = datetime.datetime.now()
        
        try:
            results = {}
            
            # 根据策略执行检索
            if strategy == RetrievalStrategy.SEMANTIC_SIMILARITY:
                results = self._retrieve_by_semantic_similarity(query, context, memory_types, limit)
            elif strategy == RetrievalStrategy.TEMPORAL_PROXIMITY:
                results = self._retrieve_by_temporal_proximity(query, context, memory_types, limit)
            elif strategy == RetrievalStrategy.ASSOCIATIVE_CHAINING:
                results = self._retrieve_by_associative_chaining(query, context, memory_types, limit)
            elif strategy == RetrievalStrategy.CONTEXTUAL_RELEVANCE:
                results = self._retrieve_by_contextual_relevance(query, context, memory_types, limit)
            else:  # HYBRID
                results = self._retrieve_hybrid(query, context, memory_types, limit)
            
            # 后处理结果
            processed_results = self._post_process_results(results, query, context)
            
            # 创建检索记录
            retrieval_record = {
                'query': query,
                'strategy': strategy.value,
                'memory_types': memory_types,
                'results_count': len(processed_results.get('items', [])),
                'retrieval_time': (datetime.datetime.now() - start_time).total_seconds(),
                'timestamp': start_time.isoformat()
            }
            
            # 缓存结果
            self._cache_result(cache_key, processed_results)
            
            return processed_results
            
        except Exception as e:
            self.logger.error(f"记忆检索失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'items': [],
                'retrieval_time': (datetime.datetime.now() - start_time).total_seconds()
            }
    
    def _retrieve_by_semantic_similarity(self,
                                       query: str,
                                       context: Dict[str, Any],
                                       memory_types: List[str],
                                       limit: int) -> Dict[str, Any]:
        """基于语义相似性检索"""
        results = {'episodic': [], 'semantic': [], 'procedural': []}
        
        # 情景记忆检索
        if 'episodic' in memory_types:
            episodic_results = self.episodic_memory.retrieve_events(
                query=query,
                limit=limit
            )
            results['episodic'] = episodic_results
        
        # 语义记忆检索
        if 'semantic' in memory_types:
            semantic_results = self.semantic_memory.query_concepts(
                query=query,
                limit=limit
            )
            results['semantic'] = semantic_results
            
            # 获取相关概念
            for concept in semantic_results[:3]:  # 只处理前3个相关概念
                related = self.semantic_memory.get_related_concepts(
                    concept['id'],
                    depth=1
                )
                results['semantic'].extend([r[0] for r in related])
        
        # 程序记忆检索
        if 'procedural' in memory_types:
            # 基于技能名称和描述检索
            all_skills = self.procedural_memory.list_skills()
            matched_skills = []
            
            for skill in all_skills:
                skill_text = f"{skill.get('name', '')} {skill.get('description', '')}"
                if self._text_similarity(query, skill_text) > self.similarity_threshold:
                    matched_skills.append(skill)
            
            results['procedural'] = matched_skills[:limit]
        
        return results
    
    def _retrieve_by_temporal_proximity(self,
                                      query: str,
                                      context: Dict[str, Any],
                                      memory_types: List[str],
                                      limit: int) -> Dict[str, Any]:
        """基于时间邻近性检索"""
        results = {'episodic': [], 'semantic': [], 'procedural': []}
        
        # 获取最近的时间上下文
        time_context = context.get('temporal_context', {})
        target_time = time_context.get('target_time', datetime.datetime.now())
        time_window = time_context.get('time_window_hours', 24)
        
        start_time = target_time - datetime.timedelta(hours=time_window)
        end_time = target_time + datetime.timedelta(hours=time_window)
        
        if 'episodic' in memory_types:
            # 检索时间窗口内的事件
            episodic_results = self.episodic_memory.retrieve_events(
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )
            results['episodic'] = episodic_results
        
        if 'semantic' in memory_types:
            # 检索最近访问的概念
            semantic_results = self.semantic_memory.query_concepts(limit=limit)
            # 按最后访问时间排序
            semantic_results.sort(
                key=lambda x: x.get('last_accessed', ''),
                reverse=True
            )
            results['semantic'] = semantic_results[:limit]
        
        if 'procedural' in memory_types:
            # 检索最近执行的技能
            execution_history = self.procedural_memory.get_execution_history(limit=limit)
            recent_skills = []
            
            for execution in execution_history:
                skill = self.procedural_memory.get_skill(execution['skill_id'])
                if skill and skill not in recent_skills:
                    recent_skills.append(skill)
            
            results['procedural'] = recent_skills[:limit]
        
        return results
    
    def _retrieve_by_associative_chaining(self,
                                        query: str,
                                        context: Dict[str, Any],
                                        memory_types: List[str],
                                        limit: int) -> Dict[str, Any]:
        """基于关联链检索"""
        results = {'episodic': [], 'semantic': [], 'procedural': []}
        
        # 初始语义检索获取种子概念
        seed_concepts = self.semantic_memory.query_concepts(query=query, limit=5)
        
        all_related = []
        for concept in seed_concepts:
            # 获取关联概念
            related = self.semantic_memory.get_related_concepts(
                concept['id'],
                direction='both',
                depth=2
            )
            all_related.extend([r[0] for r in related])
        
        # 去重
        seen_ids = set()
        unique_related = []
        for concept in all_related:
            if concept['id'] not in seen_ids:
                seen_ids.add(concept['id'])
                unique_related.append(concept)
        
        results['semantic'] = unique_related[:limit]
        
        # 基于关联概念检索情景记忆
        if 'episodic' in memory_types:
            episodic_results = []
            for concept in unique_related[:10]:  # 只处理前10个关联概念
                concept_query = concept.get('name', '') + ' ' + concept.get('description', '')
                events = self.episodic_memory.retrieve_events(
                    query=concept_query,
                    limit=3
                )
                episodic_results.extend(events)
            
            # 去重并限制数量
            seen_event_ids = set()
            unique_events = []
            for event in episodic_results:
                event_id = event.get('id')
                if event_id and event_id not in seen_event_ids:
                    seen_event_ids.add(event_id)
                    unique_events.append(event)
            
            results['episodic'] = unique_events[:limit]
        
        return results
    
    def _retrieve_by_contextual_relevance(self,
                                        query: str,
                                        context: Dict[str, Any],
                                        memory_types: List[str],
                                        limit: int) -> Dict[str, Any]:
        """基于上下文相关性检索"""
        results = {'episodic': [], 'semantic': [], 'procedural': []}
        
        # 提取上下文特征
        context_features = self._extract_context_features(context)
        
        if 'episodic' in memory_types:
            # 基于上下文过滤情景记忆
            episodic_results = self.episodic_memory.retrieve_events(
                query=query,
                limit=limit * 2
            )
            
            # 应用上下文过滤器
            filtered_events = []
            for event in episodic_results:
                relevance_score = self._compute_contextual_relevance(event, context_features)
                if relevance_score > self.similarity_threshold:
                    event['contextual_relevance'] = relevance_score
                    filtered_events.append(event)
            
            # 按上下文相关性排序
            filtered_events.sort(key=lambda x: x.get('contextual_relevance', 0), reverse=True)
            results['episodic'] = filtered_events[:limit]
        
        if 'semantic' in memory_types:
            # 基于上下文增强语义检索
            enhanced_query = self._enhance_query_with_context(query, context_features)
            semantic_results = self.semantic_memory.query_concepts(
                query=enhanced_query,
                limit=limit
            )
            results['semantic'] = semantic_results
        
        return results
    
    def _retrieve_hybrid(self,
                        query: str,
                        context: Dict[str, Any],
                        memory_types: List[str],
                        limit: int) -> Dict[str, Any]:
        """混合检索策略"""
        # 并行执行多种检索策略
        strategies = [
            RetrievalStrategy.SEMANTIC_SIMILARITY,
            RetrievalStrategy.CONTEXTUAL_RELEVANCE,
            RetrievalStrategy.TEMPORAL_PROXIMITY
        ]
        
        all_results = {}
        for strategy in strategies:
            try:
                strategy_results = self._execute_retrieval_strategy(
                    strategy, query, context, memory_types, limit
                )
                self._merge_results(all_results, strategy_results)
            except Exception as e:
                self.logger.warning(f"策略 {strategy.value} 检索失败: {e}")
        
        return all_results
    
    def _execute_retrieval_strategy(self,
                                  strategy: RetrievalStrategy,
                                  query: str,
                                  context: Dict[str, Any],
                                  memory_types: List[str],
                                  limit: int) -> Dict[str, Any]:
        """执行单个检索策略"""
        if strategy == RetrievalStrategy.SEMANTIC_SIMILARITY:
            return self._retrieve_by_semantic_similarity(query, context, memory_types, limit)
        elif strategy == RetrievalStrategy.TEMPORAL_PROXIMITY:
            return self._retrieve_by_temporal_proximity(query, context, memory_types, limit)
        elif strategy == RetrievalStrategy.ASSOCIATIVE_CHAINING:
            return self._retrieve_by_associative_chaining(query, context, memory_types, limit)
        elif strategy == RetrievalStrategy.CONTEXTUAL_RELEVANCE:
            return self._retrieve_by_contextual_relevance(query, context, memory_types, limit)
        else:
            return {'episodic': [], 'semantic': [], 'procedural': []}
    
    def _merge_results(self, all_results: Dict[str, Any], new_results: Dict[str, Any]):
        """合并检索结果"""
        for memory_type in ['episodic', 'semantic', 'procedural']:
            if memory_type not in all_results:
                all_results[memory_type] = []
            
            existing_ids = {item.get('id') for item in all_results[memory_type] if item.get('id')}
            
            for item in new_results.get(memory_type, []):
                item_id = item.get('id')
                if not item_id or item_id not in existing_ids:
                    all_results[memory_type].append(item)
    
    def _extract_context_features(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取上下文特征"""
        features = {
            'location': context.get('location', ''),
            'time_of_day': context.get('time_of_day', ''),
            'user_activity': context.get('user_activity', ''),
            'emotional_state': context.get('emotional_state', {}),
            'current_goals': context.get('current_goals', []),
            'recent_interactions': context.get('recent_interactions', [])
        }
        
        return features
    
    def _compute_contextual_relevance(self, item: Dict[str, Any], context_features: Dict[str, Any]) -> float:
        """计算上下文相关性"""
        relevance_score = 0.0
        factors_considered = 0
        
        # 位置相关性
        item_location = item.get('location')
        context_location = context_features.get('location')
        if item_location and context_location:
            location_similarity = 1.0 if item_location == context_location else 0.0
            relevance_score += location_similarity * 0.2
            factors_considered += 0.2
        
        # 活动相关性
        item_activity = item.get('activity_context')
        context_activity = context_features.get('user_activity')
        if item_activity and context_activity:
            activity_similarity = self._text_similarity(item_activity, context_activity)
            relevance_score += activity_similarity * 0.3
            factors_considered += 0.3
        
        # 目标相关性
        item_goals = item.get('related_goals', [])
        context_goals = context_features.get('current_goals', [])
        if item_goals and context_goals:
            goal_overlap = len(set(item_goals).intersection(context_goals)) / len(context_goals)
            relevance_score += goal_overlap * 0.4
            factors_considered += 0.4
        
        # 情感相关性
        item_emotion = item.get('emotional_valence', 0)
        context_emotion = context_features.get('emotional_state', {}).get('valence', 0)
        emotion_similarity = 1.0 - abs(item_emotion - context_emotion) / 2.0
        relevance_score += emotion_similarity * 0.1
        factors_considered += 0.1
        
        # 归一化
        if factors_considered > 0:
            relevance_score /= factors_considered
        
        return relevance_score
    
    def _enhance_query_with_context(self, query: str, context_features: Dict[str, Any]) -> str:
        """使用上下文增强查询"""
        enhanced_terms = [query]
        
        # 添加位置上下文
        location = context_features.get('location')
        if location:
            enhanced_terms.append(location)
        
        # 添加活动上下文
        activity = context_features.get('user_activity')
        if activity:
            enhanced_terms.append(activity)
        
        # 添加目标上下文
        goals = context_features.get('current_goals', [])
        for goal in goals[:2]:  # 只添加前2个目标
            enhanced_terms.append(goal)
        
        return ' '.join(enhanced_terms)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似性（简化实现）"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _post_process_results(self, results: Dict[str, Any], query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """后处理检索结果"""
        processed = {
            'success': True,
            'query': query,
            'context': context,
            'timestamp': datetime.datetime.now().isoformat(),
            'items': [],
            'summary': {}
        }
        
        # 合并所有类型的记忆项
        all_items = []
        for memory_type, items in results.items():
            for item in items:
                item['memory_type'] = memory_type
                item['retrieval_score'] = self._compute_retrieval_score(item, query, context)
                all_items.append(item)
        
        # 按检索分数排序
        all_items.sort(key=lambda x: x.get('retrieval_score', 0), reverse=True)
        
        # 生成摘要
        processed['items'] = all_items
        processed['summary'] = self._generate_results_summary(all_items, results)
        
        return processed
    
    def _compute_retrieval_score(self, item: Dict[str, Any], query: str, context: Dict[str, Any]) -> float:
        """计算综合检索分数"""
        base_score = item.get('similarity', 0.5)
        
        # 时效性加分
        recency_score = self._compute_recency_score(item)
        
        # 重要性加分
        importance_score = item.get('importance', 0.5)
        
        # 上下文相关性加分
        context_score = self._compute_contextual_relevance(item, context)
        
        # 综合分数
        final_score = (
            base_score * 0.4 +
            recency_score * 0.2 +
            importance_score * 0.2 +
            context_score * 0.2
        )
        
        return final_score
    
    def _compute_recency_score(self, item: Dict[str, Any]) -> float:
        """计算时效性分数"""
        timestamp = item.get('timestamp') or item.get('created_at') or item.get('last_accessed')
        if not timestamp:
            return 0.5
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return 0.5
        
        now = datetime.datetime.now()
        time_diff = (now - timestamp).total_seconds() / 3600  # 小时
        
        # 指数衰减
        recency = 2.0 ** (-time_diff / 24.0)  # 24小时半衰期
        return recency
    
    def _generate_results_summary(self, items: List[Dict[str, Any]], raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成结果摘要"""
        total_items = len(items)
        
        # 按记忆类型统计
        type_counts = {}
        for memory_type in ['episodic', 'semantic', 'procedural']:
            type_counts[memory_type] = len(raw_results.get(memory_type, []))
        
        # 平均置信度
        avg_confidence = 0
        if items:
            confidences = [item.get('confidence', 0.5) for item in items]
            avg_confidence = sum(confidences) / len(confidences)
        
        # 时间分布
        recent_count = 0
        for item in items:
            recency = self._compute_recency_score(item)
            if recency > 0.7:  # 最近的项目
                recent_count += 1
        
        return {
            'total_items': total_items,
            'items_by_type': type_counts,
            'average_confidence': avg_confidence,
            'recent_items_count': recent_count,
            'top_categories': self._extract_top_categories(items)
        }
    
    def _extract_top_categories(self, items: List[Dict[str, Any]]) -> List[str]:
        """提取主要类别"""
        categories = {}
        for item in items:
            item_categories = item.get('categories', [])
            if isinstance(item_categories, str):
                item_categories = [item_categories]
            
            for category in item_categories:
                categories[category] = categories.get(category, 0) + 1
        
        # 返回出现次数最多的5个类别
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, count in sorted_categories[:5]]
    
    def _generate_cache_key(self, query: str, context: Dict[str, Any], strategy: RetrievalStrategy, memory_types: List[str]) -> str:
        """生成缓存键"""
        import hashlib
        key_data = {
            'query': query,
            'strategy': strategy.value,
            'memory_types': sorted(memory_types),
            'context_hash': hash(str(sorted(context.items()))) if context else 0
        }
        key_string = str(key_data)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        if cache_key in self.retrieval_cache:
            cache_entry = self.retrieval_cache[cache_key]
            cache_time = cache_entry.get('cache_time')
            
            # 检查是否过期
            if datetime.datetime.now() - cache_time < datetime.timedelta(seconds=self.cache_ttl):
                return cache_entry.get('result')
            else:
                # 清理过期缓存
                del self.retrieval_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """缓存检索结果"""
        self.retrieval_cache[cache_key] = {
            'result': result,
            'cache_time': datetime.datetime.now()
        }
        
        # 清理旧缓存（如果缓存太大）
        if len(self.retrieval_cache) > 100:
            # 移除最旧的缓存项
            oldest_key = None
            oldest_time = datetime.datetime.now()
            
            for key, entry in self.retrieval_cache.items():
                if entry['cache_time'] < oldest_time:
                    oldest_time = entry['cache_time']
                    oldest_key = key
            
            if oldest_key:
                del self.retrieval_cache[oldest_key]
    
    def clear_cache(self):
        """清空检索缓存"""
        self.retrieval_cache.clear()
        self.logger.info("检索缓存已清空")
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """获取检索统计信息"""
        cache_stats = {
            'cached_entries': len(self.retrieval_cache),
            'cache_hit_rate': self._compute_cache_hit_rate()
        }
        
        memory_stats = {
            'episodic': self.episodic_memory.get_memory_stats(),
            'semantic': self.semantic_memory.get_semantic_network_stats(),
            'procedural': self.procedural_memory.get_procedural_stats()
        }
        
        return {
            'cache_stats': cache_stats,
            'memory_stats': memory_stats,
            'configuration': {
                'default_strategy': self.default_strategy.value,
                'max_results': self.max_results,
                'similarity_threshold': self.similarity_threshold
            }
        }
    
    def _compute_cache_hit_rate(self) -> float:
        """计算缓存命中率（简化实现）"""
        # 在实际系统中，这里应该记录实际的命中统计
        return 0.0  # 占位实现

