# cognitive/learning/knowledge_curator.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import heapq

class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.concept_embeddings = {}
        self.concept_importance = {}
        
    def add_concept(self, concept_id: str, concept_data: Dict[str, Any], 
                   embedding: Optional[np.ndarray] = None):
        """添加概念到知识图谱"""
        self.graph.add_node(concept_id, **concept_data)
        
        if embedding is not None:
            self.concept_embeddings[concept_id] = embedding
        
        # 初始化重要性分数
        if concept_id not in self.concept_importance:
            self.concept_importance[concept_id] = 1.0
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relationship_type: str, weight: float = 1.0):
        """添加概念间关系"""
        self.graph.add_edge(source_id, target_id, 
                          relationship_type=relationship_type, weight=weight)
    
    def get_related_concepts(self, concept_id: str, max_degree: int = 2) -> List[str]:
        """获取相关概念"""
        if concept_id not in self.graph:
            return []
        
        related = set()
        # 获取直接关联的概念
        related.update(self.graph.successors(concept_id))
        related.update(self.graph.predecessors(concept_id))
        
        # 获取二级关联的概念
        if max_degree >= 2:
            for neighbor in list(related):
                related.update(self.graph.successors(neighbor))
                related.update(self.graph.predecessors(neighbor))
        
        return list(related - {concept_id})
    
    def calculate_centrality(self):
        """计算概念中心性"""
        try:
            centrality = nx.pagerank(self.graph, weight='weight')
            self.concept_importance.update(centrality)
        except:
            # 如果PageRank失败，使用度中心性
            degree_centrality = nx.degree_centrality(self.graph)
            self.concept_importance.update(degree_centrality)
    
    def find_similar_concepts(self, query_embedding: np.ndarray, 
                            top_k: int = 5) -> List[Tuple[str, float]]:
        """查找相似概念"""
        similarities = []
        
        for concept_id, embedding in self.concept_embeddings.items():
            if len(embedding) == len(query_embedding):
                similarity = cosine_similarity([embedding], [query_embedding])[0][0]
                # 结合重要性分数
                adjusted_similarity = similarity * self.concept_importance.get(concept_id, 1.0)
                similarities.append((concept_id, adjusted_similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

class KnowledgeCurator:
    """知识管理：管理和更新知识"""
    
    def __init__(self, knowledge_dir: str = "data/knowledge"):
        self.knowledge_dir = knowledge_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 初始化知识图谱
        self.knowledge_graph = KnowledgeGraph()
        
        # 知识库
        self.knowledge_base: Dict[str, Dict] = {}
        self.knowledge_sources: Dict[str, List[str]] = defaultdict(list)
        
        # 知识质量评估
        self.knowledge_quality: Dict[str, float] = {}
        self.knowledge_freshness: Dict[str, datetime] = {}
        
        # 知识使用统计
        self.knowledge_usage: Dict[str, Dict] = defaultdict(lambda: {
            'access_count': 0,
            'last_accessed': None,
            'successful_uses': 0,
            'failed_uses': 0
        })
        
        # 文本向量化器
        self.vectorizer = TfidfVectorizer(max_features=512, stop_words='english')
        self.is_vectorizer_trained = False
        
        # 加载现有知识
        self._load_knowledge()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('knowledge_curator')
        if not logger.handlers:
            handler = logging.FileHandler('logs/knowledge_curation.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_knowledge(self):
        """加载知识库"""
        knowledge_file = os.path.join(self.knowledge_dir, "knowledge_base.json")
        graph_file = os.path.join(self.knowledge_dir, "knowledge_graph.pkl")
        quality_file = os.path.join(self.knowledge_dir, "knowledge_quality.json")
        usage_file = os.path.join(self.knowledge_dir, "knowledge_usage.json")
        
        try:
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    self.knowledge_base = json.load(f)
            
            # 注意：实际实现中需要使用适当的图序列化方法
            # 这里简化处理
            
            if os.path.exists(quality_file):
                with open(quality_file, 'r', encoding='utf-8') as f:
                    self.knowledge_quality = json.load(f)
            
            if os.path.exists(usage_file):
                with open(usage_file, 'r', encoding='utf-8') as f:
                    loaded_usage = json.load(f)
                    # 转换日期字符串回datetime对象
                    for key, value in loaded_usage.items():
                        if value['last_accessed']:
                            value['last_accessed'] = datetime.fromisoformat(value['last_accessed'])
                        self.knowledge_usage[key] = value
            
            self.logger.info(f"知识库加载成功，共{len(self.knowledge_base)}个知识项")
            
            # 重建知识图谱
            self._rebuild_knowledge_graph()
            
        except Exception as e:
            self.logger.error(f"加载知识库失败: {e}")
    
    def save_knowledge(self):
        """保存知识库"""
        os.makedirs(self.knowledge_dir, exist_ok=True)
        
        try:
            # 保存知识库
            knowledge_file = os.path.join(self.knowledge_dir, "knowledge_base.json")
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, ensure_ascii=False, indent=2)
            
            # 保存质量评估
            quality_file = os.path.join(self.knowledge_dir, "knowledge_quality.json")
            with open(quality_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_quality, f, ensure_ascii=False, indent=2)
            
            # 保存使用统计
            usage_file = os.path.join(self.knowledge_dir, "knowledge_usage.json")
            serializable_usage = {}
            for key, value in self.knowledge_usage.items():
                serializable_value = value.copy()
                if serializable_value['last_accessed']:
                    serializable_value['last_accessed'] = serializable_value['last_accessed'].isoformat()
                serializable_usage[key] = serializable_value
            with open(usage_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_usage, f, ensure_ascii=False, indent=2)
            
            self.logger.info("知识库保存成功")
            
        except Exception as e:
            self.logger.error(f"保存知识库失败: {e}")
    
    def _rebuild_knowledge_graph(self):
        """重建知识图谱"""
        self.knowledge_graph = KnowledgeGraph()
        
        # 添加所有概念到图谱
        for concept_id, concept_data in self.knowledge_base.items():
            embedding = self._generate_concept_embedding(concept_data)
            self.knowledge_graph.add_concept(concept_id, concept_data, embedding)
        
        # 重建关系（简化实现）
        # 实际实现中需要根据知识内容建立更复杂的关系
        
        self.knowledge_graph.calculate_centrality()
        self.logger.info("知识图谱重建完成")
    
    def _generate_concept_embedding(self, concept_data: Dict[str, Any]) -> np.ndarray:
        """生成概念嵌入向量"""
        # 结合多个文本字段生成嵌入
        text_parts = []
        
        # 添加概念名称
        text_parts.append(concept_data.get('name', ''))
        
        # 添加描述
        text_parts.append(concept_data.get('description', ''))
        
        # 添加内容
        content = concept_data.get('content', '')
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            text_parts.extend([str(item) for item in content[:3]])  # 前3个内容项
        
        # 添加标签
        tags = concept_data.get('tags', [])
        text_parts.extend(tags)
        
        combined_text = ' '.join(text_parts)
        
        # 使用TF-IDF生成嵌入
        if not self.is_vectorizer_trained:
            # 第一次使用时需要训练向量化器
            all_texts = [concept.get('name', '') + ' ' + concept.get('description', '') 
                        for concept in self.knowledge_base.values()]
            self.vectorizer.fit(all_texts)
            self.is_vectorizer_trained = True
        
        embedding = self.vectorizer.transform([combined_text]).toarray()[0]
        
        # 确保嵌入向量长度一致
        if len(embedding) < 512:
            embedding = np.pad(embedding, (0, 512 - len(embedding)))
        else:
            embedding = embedding[:512]
        
        return embedding
    
    def add_knowledge(self, knowledge_data: Dict[str, Any], 
                     source: str = "user_input") -> str:
        """
        添加新知识
        
        Args:
            knowledge_data: 知识数据
            source: 知识来源
            
        Returns:
            知识ID
        """
        try:
            # 生成知识ID
            knowledge_id = self._generate_knowledge_id(knowledge_data)
            
            # 完善知识数据
            complete_data = self._complete_knowledge_data(knowledge_data, source)
            
            # 添加到知识库
            self.knowledge_base[knowledge_id] = complete_data
            self.knowledge_sources[source].append(knowledge_id)
            
            # 初始质量评估
            initial_quality = self._assess_knowledge_quality(complete_data)
            self.knowledge_quality[knowledge_id] = initial_quality
            self.knowledge_freshness[knowledge_id] = datetime.now()
            
            # 更新知识图谱
            embedding = self._generate_concept_embedding(complete_data)
            self.knowledge_graph.add_concept(knowledge_id, complete_data, embedding)
            self.knowledge_graph.calculate_centrality()
            
            # 建立关系
            self._establish_relationships(knowledge_id, complete_data)
            
            self.logger.info(f"新知识添加成功: {knowledge_id} (质量: {initial_quality:.3f})")
            return knowledge_id
            
        except Exception as e:
            self.logger.error(f"添加知识失败: {e}")
            return f"error_knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _generate_knowledge_id(self, knowledge_data: Dict[str, Any]) -> str:
        """生成知识ID"""
        name = knowledge_data.get('name', 'unknown')
        category = knowledge_data.get('category', 'general')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hash(str(knowledge_data.get('content', ''))[:100])
        
        # 创建URL友好的ID
        name_clean = ''.join(c if c.isalnum() else '_' for c in name.lower())
        category_clean = ''.join(c if c.isalnum() else '_' for c in category.lower())
        
        return f"{category_clean}_{name_clean}_{timestamp}_{abs(content_hash) % 10000:04d}"
    
    def _complete_knowledge_data(self, knowledge_data: Dict[str, Any], 
                               source: str) -> Dict[str, Any]:
        """完善知识数据"""
        completed_data = knowledge_data.copy()
        
        # 确保必要字段存在
        if 'name' not in completed_data:
            completed_data['name'] = f"未命名知识_{datetime.now().strftime('%H%M%S')}"
        
        if 'category' not in completed_data:
            completed_data['category'] = 'general'
        
        # 添加元数据
        completed_data['metadata'] = {
            'source': source,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'version': 1,
            'confidence': completed_data.get('confidence', 0.5)
        }
        
        # 添加默认标签
        if 'tags' not in completed_data:
            completed_data['tags'] = [completed_data['category']]
        
        return completed_data
    
    def _assess_knowledge_quality(self, knowledge_data: Dict[str, Any]) -> float:
        """评估知识质量"""
        quality_score = 0.0
        
        # 基于完整性的评估
        completeness = self._assess_completeness(knowledge_data)
        quality_score += completeness * 0.3
        
        # 基于一致性的评估
        consistency = self._assess_consistency(knowledge_data)
        quality_score += consistency * 0.2
        
        # 基于来源可信度的评估
        source_credibility = self._assess_source_credibility(knowledge_data)
        quality_score += source_credibility * 0.3
        
        # 基于时效性的评估
        timeliness = self._assess_timeliness(knowledge_data)
        quality_score += timeliness * 0.2
        
        return min(quality_score, 1.0)
    
    def _assess_completeness(self, knowledge_data: Dict[str, Any]) -> float:
        """评估知识完整性"""
        required_fields = ['name', 'description', 'content']
        optional_fields = ['examples', 'references', 'prerequisites']
        
        completeness = 0.0
        
        # 检查必要字段
        present_required = sum(1 for field in required_fields if field in knowledge_data and knowledge_data[field])
        completeness += (present_required / len(required_fields)) * 0.6
        
        # 检查可选字段
        present_optional = sum(1 for field in optional_fields if field in knowledge_data and knowledge_data[field])
        completeness += (present_optional / len(optional_fields)) * 0.4
        
        return completeness
    
    def _assess_consistency(self, knowledge_data: Dict[str, Any]) -> float:
        """评估知识一致性"""
        # 检查内部一致性（简化实现）
        content = str(knowledge_data.get('content', ''))
        description = str(knowledge_data.get('description', ''))
        
        # 简单的文本相似度检查
        if content and description:
            # 实际实现中可以使用更复杂的NLP方法
            common_words = set(content.lower().split()) & set(description.lower().split())
            if common_words:
                return min(len(common_words) / 10.0, 1.0)
        
        return 0.5  # 默认中等一致性
    
    def _assess_source_credibility(self, knowledge_data: Dict[str, Any]) -> float:
        """评估来源可信度"""
        source = knowledge_data.get('metadata', {}).get('source', 'unknown')
        
        source_credibility = {
            'expert_verified': 0.9,
            'system_generated': 0.7,
            'user_input': 0.5,
            'external_api': 0.6,
            'unknown': 0.3
        }
        
        return source_credibility.get(source, 0.3)
    
    def _assess_timeliness(self, knowledge_data: Dict[str, Any]) -> float:
        """评估知识时效性"""
        created_at = knowledge_data.get('metadata', {}).get('created_at')
        if created_at:
            try:
                create_date = datetime.fromisoformat(created_at)
                age_days = (datetime.now() - create_date).days
                # 知识越新，时效性分数越高
                timeliness = max(0.0, 1.0 - (age_days / 365.0))  # 一年内有效
                return timeliness
            except:
                pass
        
        return 0.5  # 默认中等时效性
    
    def _establish_relationships(self, knowledge_id: str, knowledge_data: Dict[str, Any]):
        """建立知识关系"""
        # 基于类别的关系
        category = knowledge_data.get('category')
        if category:
            # 查找同类别知识
            for other_id, other_data in self.knowledge_base.items():
                if other_id != knowledge_id and other_data.get('category') == category:
                    self.knowledge_graph.add_relationship(knowledge_id, other_id, 'same_category', 0.3)
        
        # 基于标签的关系
        tags = knowledge_data.get('tags', [])
        for tag in tags:
            for other_id, other_data in self.knowledge_base.items():
                if other_id != knowledge_id and tag in other_data.get('tags', []):
                    self.knowledge_graph.add_relationship(knowledge_id, other_id, 'shared_tag', 0.2)
        
        # 基于内容相似度的关系
        query_embedding = self.knowledge_graph.concept_embeddings.get(knowledge_id)
        if query_embedding is not None:
            similar_concepts = self.knowledge_graph.find_similar_concepts(query_embedding, top_k=3)
            for similar_id, similarity in similar_concepts:
                if similar_id != knowledge_id and similarity > 0.7:
                    self.knowledge_graph.add_relationship(knowledge_id, similar_id, 
                                                        'semantically_similar', similarity)
    
    def search_knowledge(self, query: str, category: Optional[str] = None,
                        min_quality: float = 0.3, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        搜索知识
        
        Args:
            query: 搜索查询
            category: 知识类别过滤
            min_quality: 最小质量阈值
            max_results: 最大返回结果数
            
        Returns:
            相关知识列表
        """
        try:
            # 生成查询嵌入
            query_embedding = self.vectorizer.transform([query]).toarray()[0]
            if len(query_embedding) < 512:
                query_embedding = np.pad(query_embedding, (0, 512 - len(query_embedding)))
            else:
                query_embedding = query_embedding[:512]
            
            # 查找相似概念
            similar_concepts = self.knowledge_graph.find_similar_concepts(query_embedding, 
                                                                        top_k=max_results * 2)
            
            results = []
            for concept_id, similarity in similar_concepts:
                knowledge_data = self.knowledge_base.get(concept_id)
                quality = self.knowledge_quality.get(concept_id, 0.0)
                
                # 应用过滤器
                if (quality >= min_quality and 
                    (category is None or knowledge_data.get('category') == category)):
                    
                    result = {
                        'knowledge_id': concept_id,
                        'knowledge_data': knowledge_data,
                        'similarity_score': similarity,
                        'quality_score': quality,
                        'importance_score': self.knowledge_graph.concept_importance.get(concept_id, 0.0),
                        'usage_stats': self.knowledge_usage[concept_id]
                    }
                    results.append(result)
            
            # 按综合评分排序
            results.sort(key=lambda x: (
                x['similarity_score'] * 0.4 +
                x['quality_score'] * 0.3 +
                x['importance_score'] * 0.2 +
                min(x['usage_stats']['access_count'] / 100.0, 0.1)  # 使用频率加成
            ), reverse=True)
            
            # 更新使用统计
            for result in results[:5]:  # 只更新前5个结果的统计
                self._update_usage_stats(result['knowledge_id'])
            
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"知识搜索失败: {e}")
            return []
    
    def _update_usage_stats(self, knowledge_id: str):
        """更新使用统计"""
        stats = self.knowledge_usage[knowledge_id]
        stats['access_count'] += 1
        stats['last_accessed'] = datetime.now()
    
    def update_knowledge_quality(self, knowledge_id: str, usage_feedback: Dict[str, Any]):
        """
        基于使用反馈更新知识质量
        
        Args:
            knowledge_id: 知识ID
            usage_feedback: 使用反馈
        """
        if knowledge_id not in self.knowledge_base:
            self.logger.warning(f"未知知识ID: {knowledge_id}")
            return
        
        current_quality = self.knowledge_quality.get(knowledge_id, 0.5)
        feedback_score = usage_feedback.get('effectiveness', 0.5)
        
        # 基于反馈更新质量分数（移动平均）
        learning_rate = 0.1
        new_quality = current_quality * (1 - learning_rate) + feedback_score * learning_rate
        
        self.knowledge_quality[knowledge_id] = new_quality
        
        # 更新使用统计
        stats = self.knowledge_usage[knowledge_id]
        if feedback_score > 0.7:
            stats['successful_uses'] += 1
        elif feedback_score < 0.3:
            stats['failed_uses'] += 1
        
        self.logger.info(f"知识质量更新: {knowledge_id} -> {new_quality:.3f}")
    
    def get_knowledge_recommendations(self, context: Dict[str, Any], 
                                    max_recommendations: int = 5) -> List[Dict[str, Any]]:
        """
        获取知识推荐
        
        Args:
            context: 上下文信息
            max_recommendations: 最大推荐数
            
        Returns:
            知识推荐列表
        """
        try:
            # 基于上下文生成查询
            query = self._generate_recommendation_query(context)
            
            # 搜索相关知识
            search_results = self.search_knowledge(query, max_results=max_recommendations * 2)
            
            # 应用推荐逻辑
            recommendations = []
            for result in search_results:
                recommendation_score = self._calculate_recommendation_score(result, context)
                
                if recommendation_score > 0.3:  # 推荐阈值
                    recommendation = result.copy()
                    recommendation['recommendation_score'] = recommendation_score
                    recommendation['reason'] = self._generate_recommendation_reason(result, context)
                    recommendations.append(recommendation)
            
            # 按推荐分数排序
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            return recommendations[:max_recommendations]
            
        except Exception as e:
            self.logger.error(f"生成知识推荐失败: {e}")
            return []
    
    def _generate_recommendation_query(self, context: Dict[str, Any]) -> str:
        """生成推荐查询"""
        # 基于上下文生成搜索查询
        query_parts = []
        
        # 添加任务类型
        task_type = context.get('task_type')
        if task_type:
            query_parts.append(task_type)
        
        # 添加用户兴趣
        user_interests = context.get('user_interests', [])
        query_parts.extend(user_interests[:2])
        
        # 添加最近访问的知识类别
        recent_categories = context.get('recent_categories', [])
        query_parts.extend(recent_categories[:2])
        
        return ' '.join(query_parts) if query_parts else 'general knowledge'
    
    def _calculate_recommendation_score(self, knowledge_result: Dict[str, Any], 
                                      context: Dict[str, Any]) -> float:
        """计算推荐分数"""
        base_score = 0.0
        
        # 质量分数
        base_score += knowledge_result['quality_score'] * 0.3
        
        # 相关性分数
        base_score += knowledge_result['similarity_score'] * 0.4
        
        # 重要性分数
        base_score += knowledge_result['importance_score'] * 0.2
        
        # 新鲜度加成（新知识优先）
        knowledge_data = knowledge_result['knowledge_data']
        created_at = knowledge_data.get('metadata', {}).get('created_at')
        if created_at:
            try:
                create_date = datetime.fromisoformat(created_at)
                days_old = (datetime.now() - create_date).days
                freshness_boost = max(0.0, 1.0 - (days_old / 30.0))  # 一个月内较新
                base_score += freshness_boost * 0.1
            except:
                pass
        
        return min(base_score, 1.0)
    
    def _generate_recommendation_reason(self, knowledge_result: Dict[str, Any], 
                                      context: Dict[str, Any]) -> str:
        """生成推荐理由"""
        knowledge_data = knowledge_result['knowledge_data']
        category = knowledge_data.get('category', 'general')
        quality = knowledge_result['quality_score']
        
        reasons = []
        
        if quality > 0.8:
            reasons.append("高质量内容")
        elif quality < 0.4:
            reasons.append("基础内容")
        
        if category in context.get('user_interests', []):
            reasons.append("符合您的兴趣")
        
        if knowledge_result['usage_stats']['access_count'] > 10:
            reasons.append("热门知识")
        
        return "，".join(reasons) if reasons else "系统推荐"
    
    def perform_knowledge_maintenance(self):
        """执行知识维护"""
        try:
            maintenance_report = {
                'timestamp': datetime.now().isoformat(),
                'actions_taken': [],
                'knowledge_removed': 0,
                'quality_updated': 0
            }
            
            # 1. 移除低质量且很少使用的知识
            knowledge_to_remove = []
            for knowledge_id, knowledge_data in self.knowledge_base.items():
                quality = self.knowledge_quality.get(knowledge_id, 0.0)
                usage_stats = self.knowledge_usage[knowledge_id]
                access_count = usage_stats['access_count']
                
                if quality < 0.2 and access_count < 3:
                    knowledge_to_remove.append(knowledge_id)
            
            for knowledge_id in knowledge_to_remove:
                self._remove_knowledge(knowledge_id)
                maintenance_report['knowledge_removed'] += 1
            
            if knowledge_to_remove:
                maintenance_report['actions_taken'].append(
                    f"移除了 {len(knowledge_to_remove)} 个低质量知识项")
            
            # 2. 更新陈旧知识的质量分数
            current_time = datetime.now()
            quality_updates = 0
            
            for knowledge_id, knowledge_data in self.knowledge_base.items():
                created_at = knowledge_data.get('metadata', {}).get('created_at')
                if created_at:
                    try:
                        create_date = datetime.fromisoformat(created_at)
                        if (current_time - create_date).days > 180:  # 6个月以上
                            # 陈旧知识质量逐渐衰减
                            current_quality = self.knowledge_quality.get(knowledge_id, 0.5)
                            decay_factor = 0.9  # 质量衰减系数
                            new_quality = current_quality * decay_factor
                            self.knowledge_quality[knowledge_id] = new_quality
                            quality_updates += 1
                    except:
                        continue
            
            if quality_updates > 0:
                maintenance_report['quality_updated'] = quality_updates
                maintenance_report['actions_taken'].append(
                    f"更新了 {quality_updates} 个陈旧知识项的质量分数")
            
            # 3. 重新计算知识图谱中心性
            self.knowledge_graph.calculate_centrality()
            maintenance_report['actions_taken'].append("重新计算了知识图谱中心性")
            
            self.logger.info(f"知识维护完成: {maintenance_report}")
            return maintenance_report
            
        except Exception as e:
            self.logger.error(f"知识维护失败: {e}")
            return {'error': str(e)}
    
    def _remove_knowledge(self, knowledge_id: str):
        """移除知识项"""
        if knowledge_id in self.knowledge_base:
            del self.knowledge_base[knowledge_id]
        
        if knowledge_id in self.knowledge_quality:
            del self.knowledge_quality[knowledge_id]
        
        if knowledge_id in self.knowledge_freshness:
            del self.knowledge_freshness[knowledge_id]
        
        if knowledge_id in self.knowledge_usage:
            del self.knowledge_usage[knowledge_id]
        
        # 从知识图谱中移除
        if knowledge_id in self.knowledge_graph.graph:
            self.knowledge_graph.graph.remove_node(knowledge_id)
        
        if knowledge_id in self.knowledge_graph.concept_embeddings:
            del self.knowledge_graph.concept_embeddings[knowledge_id]
        
        if knowledge_id in self.knowledge_graph.concept_importance:
            del self.knowledge_graph.concept_importance[knowledge_id]
    
    def get_knowledge_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        total_knowledge = len(self.knowledge_base)
        
        # 类别分布
        category_distribution = defaultdict(int)
        for knowledge_data in self.knowledge_base.values():
            category = knowledge_data.get('category', 'unknown')
            category_distribution[category] += 1
        
        # 质量分布
        quality_scores = list(self.knowledge_quality.values())
        quality_stats = {
            'average': np.mean(quality_scores) if quality_scores else 0.0,
            'std': np.std(quality_scores) if quality_scores else 0.0,
            'min': min(quality_scores) if quality_scores else 0.0,
            'max': max(quality_scores) if quality_scores else 0.0
        }
        
        # 使用统计
        usage_counts = [stats['access_count'] for stats in self.knowledge_usage.values()]
        usage_stats = {
            'total_accesses': sum(usage_counts),
            'average_per_item': np.mean(usage_counts) if usage_counts else 0.0,
            'most_accessed': max(usage_counts) if usage_counts else 0
        }
        
        # 知识图谱统计
        graph_stats = {
            'total_nodes': self.knowledge_graph.graph.number_of_nodes(),
            'total_edges': self.knowledge_graph.graph.number_of_edges(),
            'average_degree': np.mean([d for n, d in self.knowledge_graph.graph.degree()]) 
                            if list(self.knowledge_graph.graph.degree()) else 0.0
        }
        
        return {
            'total_knowledge_items': total_knowledge,
            'category_distribution': dict(category_distribution),
            'quality_statistics': quality_stats,
            'usage_statistics': usage_stats,
            'knowledge_graph_statistics': graph_stats,
            'knowledge_freshness': {
                'oldest': min(self.knowledge_freshness.values()).isoformat() 
                         if self.knowledge_freshness else None,
                'newest': max(self.knowledge_freshness.values()).isoformat() 
                         if self.knowledge_freshness else None
            }
        }

# 全局知识管理实例
_global_knowledge_curator: Optional[KnowledgeCurator] = None

def get_knowledge_curator() -> KnowledgeCurator:
    """获取全局知识管理实例"""
    global _global_knowledge_curator
    if _global_knowledge_curator is None:
        _global_knowledge_curator = KnowledgeCurator()
    return _global_knowledge_curator
