"""
关联记忆模块：关联相关信息
实现基于神经网络和相似性的关联记忆系统
"""

import uuid
import datetime
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory

class AssociationType(Enum):
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CONTEXTUAL = "contextual"
    EMOTIONAL = "emotional"
    CAUSAL = "causal"

class AssociativeMemory:
    """关联记忆系统 - 关联相关信息"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        
        # 关联网络
        self.association_network = {}
        self.association_strengths = {}
        
        # 关联配置
        self.min_association_strength = self.config.get('min_association_strength', 0.1)
        self.association_decay_rate = self.config.get('association_decay_rate', 0.95)
        self.max_associations_per_item = self.config.get('max_associations_per_item', 10)
        
        # 相似性阈值
        self.similarity_threshold = self.config.get('similarity_threshold', 0.6)
        
        # 关联历史
        self.association_history = []
        
        self.initialized = True
        self.logger.info("关联记忆系统初始化成功")
    
    def create_association(self,
                         source_id: str,
                         target_id: str,
                         association_type: AssociationType,
                         strength: float = 0.5,
                         context: Dict[str, Any] = None) -> bool:
        """
        创建关联
        
        Args:
            source_id: 源记忆ID
            target_id: 目标记忆ID
            association_type: 关联类型
            strength: 关联强度
            context: 关联上下文
            
        Returns:
            是否成功
        """
        try:
            # 验证关联强度
            strength = max(self.min_association_strength, min(1.0, strength))
            
            # 创建关联键
            association_key = self._generate_association_key(source_id, target_id, association_type)
            
            # 存储关联
            association_data = {
                'source_id': source_id,
                'target_id': target_id,
                'type': association_type.value,
                'strength': strength,
                'created_at': datetime.datetime.now().isoformat(),
                'last_accessed': datetime.datetime.now().isoformat(),
                'access_count': 0,
                'context': context or {}
            }
            
            self.association_network[association_key] = association_data
            
            # 更新关联强度矩阵
            self._update_association_strength(source_id, target_id, strength)
            
            # 记录关联创建
            self._record_association_creation(association_data)
            
            self.logger.info(f"创建关联: {source_id} -> {target_id} ({association_type.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"创建关联失败: {e}")
            return False
    
    def find_associations(self,
                        memory_id: str,
                        association_type: AssociationType = None,
                        min_strength: float = None,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        查找关联
        
        Args:
            memory_id: 记忆ID
            association_type: 关联类型过滤
            min_strength: 最小关联强度
            limit: 返回数量限制
            
        Returns:
            关联列表
        """
        min_strength = min_strength or self.min_association_strength
        
        try:
            associations = []
            
            # 查找以该记忆为源的关联
            for association_key, association_data in self.association_network.items():
                if association_data['source_id'] == memory_id:
                    if self._matches_filters(association_data, association_type, min_strength):
                        associations.append(association_data)
                
                # 同时查找以该记忆为目标的关联（双向关联）
                elif association_data['target_id'] == memory_id:
                    if self._matches_filters(association_data, association_type, min_strength):
                        # 创建反向关联视图
                        reverse_association = association_data.copy()
                        reverse_association['source_id'] = memory_id
                        reverse_association['target_id'] = association_data['source_id']
                        reverse_association['direction'] = 'incoming'
                        associations.append(reverse_association)
            
            # 按强度排序
            associations.sort(key=lambda x: x['strength'], reverse=True)
            
            # 更新访问统计
            for association in associations[:limit]:
                self._update_association_access(association)
            
            return associations[:limit]
            
        except Exception as e:
            self.logger.error(f"查找关联失败: {e}")
            return []
    
    def discover_associations(self,
                            memory_item: Dict[str, Any],
                            association_types: List[AssociationType] = None,
                            similarity_threshold: float = None) -> List[Dict[str, Any]]:
        """
        发现新关联
        
        Args:
            memory_item: 记忆项
            association_types: 关联类型
            similarity_threshold: 相似性阈值
            
        Returns:
            发现的关联列表
        """
        similarity_threshold = similarity_threshold or self.similarity_threshold
        association_types = association_types or list(AssociationType)
        
        discovered_associations = []
        
        try:
            memory_id = memory_item.get('id')
            memory_type = memory_item.get('memory_type', 'episodic')
            
            for assoc_type in association_types:
                if assoc_type == AssociationType.SEMANTIC:
                    semantic_associations = self._discover_semantic_associations(memory_item, similarity_threshold)
                    discovered_associations.extend(semantic_associations)
                
                elif assoc_type == AssociationType.TEMPORAL:
                    temporal_associations = self._discover_temporal_associations(memory_item)
                    discovered_associations.extend(temporal_associations)
                
                elif assoc_type == AssociationType.CONTEXTUAL:
                    contextual_associations = self._discover_contextual_associations(memory_item)
                    discovered_associations.extend(contextual_associations)
                
                elif assoc_type == AssociationType.EMOTIONAL:
                    emotional_associations = self._discover_emotional_associations(memory_item)
                    discovered_associations.extend(emotional_associations)
                
                elif assoc_type == AssociationType.CAUSAL:
                    causal_associations = self._discover_causal_associations(memory_item)
                    discovered_associations.extend(causal_associations)
            
            # 创建发现的关联
            for discovered in discovered_associations:
                if discovered['strength'] >= self.min_association_strength:
                    self.create_association(
                        source_id=memory_id,
                        target_id=discovered['target_id'],
                        association_type=AssociationType(discovered['type']),
                        strength=discovered['strength'],
                        context=discovered.get('context')
                    )
            
            return discovered_associations
            
        except Exception as e:
            self.logger.error(f"发现关联失败: {e}")
            return []
    
    def _discover_semantic_associations(self, memory_item: Dict[str, Any], similarity_threshold: float) -> List[Dict[str, Any]]:
        """发现语义关联"""
        associations = []
        
        try:
            memory_content = self._extract_memory_content(memory_item)
            if not memory_content:
                return associations
            
            # 搜索语义相似的记忆
            if memory_item.get('memory_type') == 'episodic':
                similar_events = self.episodic_memory.retrieve_events(
                    query=memory_content,
                    limit=5
                )
                
                for event in similar_events:
                    if event.get('id') != memory_item.get('id'):
                        similarity = self._calculate_semantic_similarity(memory_content, event.get('description', ''))
                        if similarity >= similarity_threshold:
                            associations.append({
                                'target_id': event.get('id'),
                                'type': AssociationType.SEMANTIC.value,
                                'strength': similarity,
                                'context': {'similarity_score': similarity}
                            })
            
            # 搜索相关概念
            related_concepts = self.semantic_memory.query_concepts(query=memory_content, limit=5)
            for concept in related_concepts:
                similarity = self._calculate_semantic_similarity(memory_content, concept.get('name', ''))
                if similarity >= similarity_threshold:
                    associations.append({
                        'target_id': concept.get('id'),
                        'type': AssociationType.SEMANTIC.value,
                        'strength': similarity,
                        'context': {'similarity_score': similarity}
                    })
        
        except Exception as e:
            self.logger.warning(f"发现语义关联失败: {e}")
        
        return associations
    
    def _discover_temporal_associations(self, memory_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现时间关联"""
        associations = []
        
        try:
            timestamp = memory_item.get('timestamp')
            if not timestamp:
                return associations
            
            if isinstance(timestamp, str):
                timestamp = datetime.datetime.fromisoformat(timestamp)
            
            # 查找时间上接近的记忆
            time_window = datetime.timedelta(hours=24)
            start_time = timestamp - time_window
            end_time = timestamp + time_window
            
            temporal_events = self.episodic_memory.retrieve_events(
                start_time=start_time,
                end_time=end_time,
                limit=5
            )
            
            for event in temporal_events:
                if event.get('id') != memory_item.get('id'):
                    event_time = datetime.datetime.fromisoformat(event.get('timestamp'))
                    time_diff = abs((timestamp - event_time).total_seconds())
                    
                    # 时间接近度转换为关联强度
                    temporal_strength = 1.0 / (1.0 + time_diff / 3600)  # 小时级衰减
                    
                    associations.append({
                        'target_id': event.get('id'),
                        'type': AssociationType.TEMPORAL.value,
                        'strength': temporal_strength,
                        'context': {'time_difference_hours': time_diff / 3600}
                    })
        
        except Exception as e:
            self.logger.warning(f"发现时间关联失败: {e}")
        
        return associations
    
    def _discover_contextual_associations(self, memory_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现上下文关联"""
        associations = []
        
        try:
            # 基于位置上下文
            location = memory_item.get('location')
            if location:
                location_events = self.episodic_memory.retrieve_events(limit=10)
                for event in location_events:
                    if (event.get('id') != memory_item.get('id') and 
                        event.get('location') == location):
                        associations.append({
                            'target_id': event.get('id'),
                            'type': AssociationType.CONTEXTUAL.value,
                            'strength': 0.7,
                            'context': {'shared_location': location}
                        })
            
            # 基于活动上下文
            activity = memory_item.get('activity_context')
            if activity:
                # 查找类似活动的记忆
                for event in self.episodic_memory.retrieve_events(limit=10):
                    if (event.get('id') != memory_item.get('id') and 
                        event.get('activity_context') == activity):
                        associations.append({
                            'target_id': event.get('id'),
                            'type': AssociationType.CONTEXTUAL.value,
                            'strength': 0.6,
                            'context': {'shared_activity': activity}
                        })
        
        except Exception as e:
            self.logger.warning(f"发现上下文关联失败: {e}")
        
        return associations
    
    def _discover_emotional_associations(self, memory_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现情感关联"""
        associations = []
        
        try:
            emotional_valence = memory_item.get('emotional_valence', 0)
            emotional_arousal = memory_item.get('emotional_arousal', 0)
            
            # 查找情感相似的记忆
            for event in self.episodic_memory.retrieve_events(limit=10):
                if event.get('id') != memory_item.get('id'):
                    event_valence = event.get('emotional_valence', 0)
                    event_arousal = event.get('emotional_arousal', 0)
                    
                    # 计算情感相似性
                    valence_similarity = 1.0 - abs(emotional_valence - event_valence) / 2.0
                    arousal_similarity = 1.0 - abs(emotional_arousal - event_arousal)
                    
                    emotional_similarity = (valence_similarity + arousal_similarity) / 2.0
                    
                    if emotional_similarity > 0.6:
                        associations.append({
                            'target_id': event.get('id'),
                            'type': AssociationType.EMOTIONAL.value,
                            'strength': emotional_similarity,
                            'context': {
                                'valence_similarity': valence_similarity,
                                'arousal_similarity': arousal_similarity
                            }
                        })
        
        except Exception as e:
            self.logger.warning(f"发现情感关联失败: {e}")
        
        return associations
    
    def _discover_causal_associations(self, memory_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """发现因果关联"""
        associations = []
        
        try:
            # 简化因果发现 - 基于时间顺序和内容模式
            timestamp = memory_item.get('timestamp')
            if not timestamp:
                return associations
            
            if isinstance(timestamp, str):
                timestamp = datetime.datetime.fromisoformat(timestamp)
            
            # 查找时间上在前的事件作为可能的原因
            previous_events = self.episodic_memory.retrieve_events(
                end_time=timestamp,
                limit=5
            )
            
            for event in previous_events:
                if event.get('id') != memory_item.get('id'):
                    # 简单的内容模式匹配
                    content_similarity = self._calculate_content_overlap(memory_item, event)
                    if content_similarity > 0.3:
                        associations.append({
                            'target_id': event.get('id'),
                            'type': AssociationType.CAUSAL.value,
                            'strength': content_similarity * 0.8,  # 因果关联通常较弱
                            'context': {
                                'content_overlap': content_similarity,
                                'temporal_relationship': 'precedes'
                            }
                        })
        
        except Exception as e:
            self.logger.warning(f"发现因果关联失败: {e}")
        
        return associations
    
    def _extract_memory_content(self, memory_item: Dict[str, Any]) -> str:
        """提取记忆内容"""
        content_parts = []
        
        if memory_item.get('description'):
            content_parts.append(memory_item['description'])
        if memory_item.get('content'):
            content_parts.append(str(memory_item['content']))
        if memory_item.get('name'):
            content_parts.append(memory_item['name'])
        
        return ' '.join(content_parts)
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """计算语义相似性"""
        if not text1 or not text2:
            return 0.0
        
        # 简化实现 - 使用词袋模型
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _calculate_content_overlap(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> float:
        """计算内容重叠"""
        content1 = self._extract_memory_content(item1)
        content2 = self._extract_memory_content(item2)
        
        return self._calculate_semantic_similarity(content1, content2)
    
    def _matches_filters(self, 
                        association_data: Dict[str, Any],
                        association_type: AssociationType,
                        min_strength: float) -> bool:
        """检查是否匹配过滤器"""
        if association_type and association_data['type'] != association_type.value:
            return False
        
        if min_strength and association_data['strength'] < min_strength:
            return False
        
        return True
    
    def _generate_association_key(self, source_id: str, target_id: str, association_type: AssociationType) -> str:
        """生成关联键"""
        return f"{source_id}_{target_id}_{association_type.value}"
    
    def _update_association_strength(self, source_id: str, target_id: str, strength: float):
        """更新关联强度"""
        key = f"{source_id}_{target_id}"
        self.association_strengths[key] = strength
    
    def _update_association_access(self, association_data: Dict[str, Any]):
        """更新关联访问统计"""
        association_key = self._generate_association_key(
            association_data['source_id'],
            association_data['target_id'],
            AssociationType(association_data['type'])
        )
        
        if association_key in self.association_network:
            self.association_network[association_key]['last_accessed'] = datetime.datetime.now().isoformat()
            self.association_network[association_key]['access_count'] += 1
            
            # 加强经常访问的关联
            current_strength = self.association_network[association_key]['strength']
            new_strength = min(1.0, current_strength * 1.05)  # 每次访问加强5%
            self.association_network[association_key]['strength'] = new_strength
    
    def _record_association_creation(self, association_data: Dict[str, Any]):
        """记录关联创建"""
        record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'association_key': self._generate_association_key(
                association_data['source_id'],
                association_data['target_id'],
                AssociationType(association_data['type'])
            ),
            'type': association_data['type'],
            'strength': association_data['strength']
        }
        
        self.association_history.append(record)
    
    def strengthen_association(self,
                             source_id: str,
                             target_id: str,
                             association_type: AssociationType,
                             increment: float = 0.1) -> bool:
        """
        加强关联
        
        Args:
            source_id: 源记忆ID
            target_id: 目标记忆ID
            association_type: 关联类型
            increment: 加强幅度
            
        Returns:
            是否成功
        """
        try:
            association_key = self._generate_association_key(source_id, target_id, association_type)
            
            if association_key in self.association_network:
                current_strength = self.association_network[association_key]['strength']
                new_strength = min(1.0, current_strength + increment)
                self.association_network[association_key]['strength'] = new_strength
                
                self.logger.info(f"加强关联: {source_id} -> {target_id} ({current_strength} -> {new_strength})")
                return True
            else:
                # 如果关联不存在，创建它
                return self.create_association(source_id, target_id, association_type, increment)
                
        except Exception as e:
            self.logger.error(f"加强关联失败: {e}")
            return False
    
    def weaken_association(self,
                         source_id: str,
                         target_id: str,
                         association_type: AssociationType,
                         decrement: float = 0.1) -> bool:
        """
        减弱关联
        
        Args:
            source_id: 源记忆ID
            target_id: 目标记忆ID
            association_type: 关联类型
            decrement: 减弱幅度
            
        Returns:
            是否成功
        """
        try:
            association_key = self._generate_association_key(source_id, target_id, association_type)
            
            if association_key in self.association_network:
                current_strength = self.association_network[association_key]['strength']
                new_strength = max(self.min_association_strength, current_strength - decrement)
                self.association_network[association_key]['strength'] = new_strength
                
                # 如果强度低于阈值，移除关联
                if new_strength <= self.min_association_strength:
                    del self.association_network[association_key]
                    self.logger.info(f"移除弱关联: {source_id} -> {target_id}")
                else:
                    self.logger.info(f"减弱关联: {source_id} -> {target_id} ({current_strength} -> {new_strength})")
                
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"减弱关联失败: {e}")
            return False
    
    def get_association_network_stats(self) -> Dict[str, Any]:
        """获取关联网络统计"""
        total_associations = len(self.association_network)
        
        # 按类型统计
        type_distribution = {}
        for association in self.association_network.values():
            assoc_type = association['type']
            type_distribution[assoc_type] = type_distribution.get(assoc_type, 0) + 1
        
        # 平均强度
        avg_strength = 0
        if total_associations > 0:
            avg_strength = sum(assoc['strength'] for assoc in self.association_network.values()) / total_associations
        
        # 网络密度
        unique_memories = set()
        for association in self.association_network.values():
            unique_memories.add(association['source_id'])
            unique_memories.add(association['target_id'])
        
        network_density = 0
        if len(unique_memories) > 1:
            possible_connections = len(unique_memories) * (len(unique_memories) - 1)
            network_density = total_associations / possible_connections
        
        return {
            "total_associations": total_associations,
            "unique_memories_in_network": len(unique_memories),
            "average_association_strength": avg_strength,
            "association_type_distribution": type_distribution,
            "network_density": network_density,
            "most_connected_memory": self._find_most_connected_memory()
        }
    
    def _find_most_connected_memory(self) -> Optional[Dict[str, Any]]:
        """查找连接最多的记忆"""
        connection_counts = {}
        
        for association in self.association_network.values():
            source_id = association['source_id']
            target_id = association['target_id']
            
            connection_counts[source_id] = connection_counts.get(source_id, 0) + 1
            connection_counts[target_id] = connection_counts.get(target_id, 0) + 1
        
        if not connection_counts:
            return None
        
        most_connected_id = max(connection_counts.items(), key=lambda x: x[1])[0]
        
        return {
            'memory_id': most_connected_id,
            'connection_count': connection_counts[most_connected_id]
        }
    
    def export_association_network(self) -> Dict[str, Any]:
        """导出关联网络"""
        return {
            'associations': self.association_network,
            'association_strengths': self.association_strengths,
            'export_timestamp': datetime.datetime.now().isoformat(),
            'statistics': self.get_association_network_stats()
        }

