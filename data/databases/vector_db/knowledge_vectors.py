"""
知识向量存储系统
负责存储和检索知识图谱的向量数据
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeVector:
    """知识向量数据类"""
    id: str
    entity_id: str
    entity_type: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    confidence: float
    source: str
    created_time: datetime
    updated_time: datetime

@dataclass
class KnowledgeRelation:
    """知识关系数据类"""
    id: str
    source_entity: str
    target_entity: str
    relation_type: str
    weight: float
    metadata: Dict[str, Any]

class KnowledgeVectorStore:
    """知识向量存储管理器"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.knowledge_vectors: Dict[str, KnowledgeVector] = {}
        self.entity_index: Dict[str, List[str]] = {}
        self.type_index: Dict[str, List[str]] = {}
        self.relations: Dict[str, KnowledgeRelation] = {}
        self.relation_index: Dict[str, List[str]] = {}
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
    def add_knowledge(self, entity_id: str, entity_type: str, content: str,
                     embedding: np.ndarray, metadata: Dict[str, Any] = None,
                     confidence: float = 1.0, source: str = "system") -> str:
        """
        添加知识向量
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            content: 内容
            embedding: 向量
            metadata: 元数据
            confidence: 置信度
            source: 来源
            
        Returns:
            str: 知识向量ID
        """
        try:
            if embedding.shape[0] != self.dimension:
                logger.error(f"Embedding dimension mismatch: {embedding.shape[0]} vs {self.dimension}")
                return None
                
            knowledge_id = str(uuid.uuid4())
            now = datetime.now()
            
            if metadata is None:
                metadata = {}
                
            knowledge = KnowledgeVector(
                id=knowledge_id,
                entity_id=entity_id,
                entity_type=entity_type,
                content=content,
                embedding=embedding.copy(),
                metadata=metadata,
                confidence=confidence,
                source=source,
                created_time=now,
                updated_time=now
            )
            
            # 存储知识向量
            self.knowledge_vectors[knowledge_id] = knowledge
            self.embedding_cache[knowledge_id] = embedding.copy()
            
            # 更新索引
            if entity_id not in self.entity_index:
                self.entity_index[entity_id] = []
            self.entity_index[entity_id].append(knowledge_id)
            
            if entity_type not in self.type_index:
                self.type_index[entity_type] = []
            self.type_index[entity_type].append(knowledge_id)
            
            logger.info(f"Added knowledge vector: {knowledge_id} for entity {entity_id}")
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Failed to add knowledge vector: {str(e)}")
            return None
            
    def add_relation(self, source_entity: str, target_entity: str,
                    relation_type: str, weight: float = 1.0,
                    metadata: Dict[str, Any] = None) -> str:
        """
        添加知识关系
        
        Args:
            source_entity: 源实体
            target_entity: 目标实体
            relation_type: 关系类型
            weight: 关系权重
            metadata: 元数据
            
        Returns:
            str: 关系ID
        """
        try:
            relation_id = str(uuid.uuid4())
            
            if metadata is None:
                metadata = {}
                
            relation = KnowledgeRelation(
                id=relation_id,
                source_entity=source_entity,
                target_entity=target_entity,
                relation_type=relation_type,
                weight=weight,
                metadata=metadata
            )
            
            # 存储关系
            self.relations[relation_id] = relation
            
            # 更新关系索引
            relation_key = f"{source_entity}->{target_entity}"
            if relation_key not in self.relation_index:
                self.relation_index[relation_key] = []
            self.relation_index[relation_key].append(relation_id)
            
            logger.info(f"Added relation: {relation_id} ({source_entity} -> {target_entity})")
            return relation_id
            
        except Exception as e:
            logger.error(f"Failed to add relation: {str(e)}")
            return None
            
    def get_entity_knowledge(self, entity_id: str) -> List[KnowledgeVector]:
        """
        获取实体的知识向量
        
        Args:
            entity_id: 实体ID
            
        Returns:
            List[KnowledgeVector]: 知识向量列表
        """
        try:
            if entity_id not in self.entity_index:
                return []
                
            knowledge_ids = self.entity_index[entity_id]
            return [self.knowledge_vectors[kid] for kid in knowledge_ids 
                   if kid in self.knowledge_vectors]
                   
        except Exception as e:
            logger.error(f"Failed to get entity knowledge: {str(e)}")
            return []
            
    def search_similar_knowledge(self, query_embedding: np.ndarray,
                               entity_types: List[str] = None,
                               confidence_threshold: float = 0.0,
                               max_results: int = 10,
                               similarity_threshold: float = 0.0) -> List[Tuple[KnowledgeVector, float]]:
        """
        搜索相似知识
        
        Args:
            query_embedding: 查询向量
            entity_types: 实体类型过滤
            confidence_threshold: 置信度阈值
            max_results: 最大结果数
            similarity_threshold: 相似度阈值
            
        Returns:
            List[Tuple[KnowledgeVector, float]]: 知识向量和相似度列表
        """
        try:
            results = []
            
            # 过滤实体类型
            candidate_ids = set()
            if entity_types:
                for entity_type in entity_types:
                    if entity_type in self.type_index:
                        candidate_ids.update(self.type_index[entity_type])
            else:
                candidate_ids = set(self.knowledge_vectors.keys())
                
            # 过滤置信度
            candidate_ids = {
                kid for kid in candidate_ids
                if self.knowledge_vectors[kid].confidence >= confidence_threshold
            }
            
            # 计算相似度
            for knowledge_id in candidate_ids:
                knowledge = self.knowledge_vectors[knowledge_id]
                similarity = self._calculate_similarity(
                    query_embedding, knowledge.embedding)
                    
                if similarity >= similarity_threshold:
                    results.append((knowledge, similarity))
                    
            # 按相似度排序并限制结果数量
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:max_results]
            
            logger.info(f"Knowledge search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search knowledge: {str(e)}")
            return []
            
    def get_related_entities(self, entity_id: str, relation_types: List[str] = None,
                           max_depth: int = 1) -> List[Tuple[str, str, float]]:
        """
        获取相关实体
        
        Args:
            entity_id: 实体ID
            relation_types: 关系类型过滤
            max_depth: 最大深度
            
        Returns:
            List[Tuple[str, str, float]]: (目标实体, 关系类型, 权重) 列表
        """
        try:
            related_entities = []
            visited = set()
            
            def traverse(current_entity: str, depth: int):
                if depth > max_depth or current_entity in visited:
                    return
                    
                visited.add(current_entity)
                
                # 查找以当前实体为起点的关系
                for relation_key, relation_ids in self.relation_index.items():
                    if relation_key.startswith(f"{current_entity}->"):
                        for relation_id in relation_ids:
                            relation = self.relations[relation_id]
                            
                            # 过滤关系类型
                            if relation_types and relation.relation_type not in relation_types:
                                continue
                                
                            related_entities.append((
                                relation.target_entity,
                                relation.relation_type,
                                relation.weight
                            ))
                            
                            # 递归遍历
                            traverse(relation.target_entity, depth + 1)
                            
                # 查找以当前实体为终点的关系
                for relation_key, relation_ids in self.relation_index.items():
                    if relation_key.endswith(f"->{current_entity}"):
                        for relation_id in relation_ids:
                            relation = self.relations[relation_id]
                            
                            # 过滤关系类型
                            if relation_types and relation.relation_type not in relation_types:
                                continue
                                
                            related_entities.append((
                                relation.source_entity,
                                relation.relation_type,
                                relation.weight
                            ))
                            
                            # 递归遍历
                            traverse(relation.source_entity, depth + 1)
                            
            traverse(entity_id, 0)
            return related_entities
            
        except Exception as e:
            logger.error(f"Failed to get related entities: {str(e)}")
            return []
            
    def update_knowledge_confidence(self, knowledge_id: str, confidence: float) -> bool:
        """
        更新知识置信度
        
        Args:
            knowledge_id: 知识ID
            confidence: 新的置信度
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if knowledge_id not in self.knowledge_vectors:
                return False
                
            self.knowledge_vectors[knowledge_id].confidence = max(0.0, min(1.0, confidence))
            self.knowledge_vectors[knowledge_id].updated_time = datetime.now()
            
            logger.info(f"Updated knowledge {knowledge_id} confidence to {confidence}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update knowledge confidence: {str(e)}")
            return False
            
    def get_knowledge_graph(self, center_entity: str, max_relations: int = 50) -> Dict[str, Any]:
        """
        获取知识图谱
        
        Args:
            center_entity: 中心实体
            max_relations: 最大关系数
            
        Returns:
            Dict[str, Any]: 知识图谱数据
        """
        try:
            graph = {
                "entities": {},
                "relations": []
            }
            
            # 添加中心实体
            if center_entity in self.entity_index:
                knowledge_list = self.get_entity_knowledge(center_entity)
                if knowledge_list:
                    graph["entities"][center_entity] = {
                        "type": knowledge_list[0].entity_type,
                        "content": knowledge_list[0].content,
                        "confidence": knowledge_list[0].confidence
                    }
                    
            # 获取相关实体和关系
            related_entities = self.get_related_entities(center_entity, max_depth=2)
            
            for target_entity, relation_type, weight in related_entities[:max_relations]:
                # 添加目标实体
                if target_entity not in graph["entities"]:
                    target_knowledge = self.get_entity_knowledge(target_entity)
                    if target_knowledge:
                        graph["entities"][target_entity] = {
                            "type": target_knowledge[0].entity_type,
                            "content": target_knowledge[0].content,
                            "confidence": target_knowledge[0].confidence
                        }
                        
                # 添加关系
                graph["relations"].append({
                    "source": center_entity,
                    "target": target_entity,
                    "type": relation_type,
                    "weight": weight
                })
                
            logger.info(f"Generated knowledge graph for {center_entity}")
            return graph
            
        except Exception as e:
            logger.error(f"Failed to get knowledge graph: {str(e)}")
            return {"entities": {}, "relations": []}
            
    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算向量相似度（余弦相似度）"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0
            
    def save_to_file(self, file_path: str) -> bool:
        """保存知识向量到文件"""
        try:
            save_data = {
                "dimension": self.dimension,
                "knowledge_vectors": {
                    kid: {
                        "entity_id": knowledge.entity_id,
                        "entity_type": knowledge.entity_type,
                        "content": knowledge.content,
                        "embedding": knowledge.embedding.tolist(),
                        "metadata": knowledge.metadata,
                        "confidence": knowledge.confidence,
                        "source": knowledge.source,
                        "created_time": knowledge.created_time.isoformat(),
                        "updated_time": knowledge.updated_time.isoformat()
                    }
                    for kid, knowledge in self.knowledge_vectors.items()
                },
                "relations": {
                    rid: {
                        "source_entity": relation.source_entity,
                        "target_entity": relation.target_entity,
                        "relation_type": relation.relation_type,
                        "weight": relation.weight,
                        "metadata": relation.metadata
                    }
                    for rid, relation in self.relations.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            logger.info(f"Saved knowledge vectors to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save knowledge vectors: {str(e)}")
            return False
            
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载知识向量"""
        try:
            with open(file_path, 'r') as f:
                save_data = json.load(f)
                
            self.dimension = save_data["dimension"]
            self.knowledge_vectors.clear()
            self.entity_index.clear()
            self.type_index.clear()
            self.relations.clear()
            self.relation_index.clear()
            self.embedding_cache.clear()
            
            # 加载知识向量
            for kid, knowledge_data in save_data["knowledge_vectors"].items():
                knowledge = KnowledgeVector(
                    id=kid,
                    entity_id=knowledge_data["entity_id"],
                    entity_type=knowledge_data["entity_type"],
                    content=knowledge_data["content"],
                    embedding=np.array(knowledge_data["embedding"]),
                    metadata=knowledge_data["metadata"],
                    confidence=knowledge_data["confidence"],
                    source=knowledge_data["source"],
                    created_time=datetime.fromisoformat(knowledge_data["created_time"]),
                    updated_time=datetime.fromisoformat(knowledge_data["updated_time"])
                )
                
                self.knowledge_vectors[kid] = knowledge
                self.embedding_cache[kid] = knowledge.embedding.copy()
                
                # 重建索引
                if knowledge.entity_id not in self.entity_index:
                    self.entity_index[knowledge.entity_id] = []
                self.entity_index[knowledge.entity_id].append(kid)
                
                if knowledge.entity_type not in self.type_index:
                    self.type_index[knowledge.entity_type] = []
                self.type_index[knowledge.entity_type].append(kid)
                
            # 加载关系
            for rid, relation_data in save_data["relations"].items():
                relation = KnowledgeRelation(
                    id=rid,
                    source_entity=relation_data["source_entity"],
                    target_entity=relation_data["target_entity"],
                    relation_type=relation_data["relation_type"],
                    weight=relation_data["weight"],
                    metadata=relation_data["metadata"]
                )
                
                self.relations[rid] = relation
                
                # 重建关系索引
                relation_key = f"{relation.source_entity}->{relation.target_entity}"
                if relation_key not in self.relation_index:
                    self.relation_index[relation_key] = []
                self.relation_index[relation_key].append(rid)
                
            logger.info(f"Loaded knowledge vectors from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load knowledge vectors: {str(e)}")
            return False
