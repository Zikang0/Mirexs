"""
记忆向量存储系统
负责存储和检索用户的交互记忆向量数据
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
class MemoryVector:
    """记忆向量数据类"""
    id: str
    user_id: str
    memory_type: str  # episodic, semantic, procedural
    content: str
    embedding: np.ndarray
    timestamp: datetime
    metadata: Dict[str, Any]
    importance: float
    access_count: int
    last_accessed: datetime

@dataclass
class MemoryQuery:
    """记忆查询数据类"""
    query_embedding: np.ndarray
    memory_types: List[str]
    time_range: Optional[Tuple[datetime, datetime]]
    importance_threshold: float
    max_results: int
    similarity_threshold: float

class MemoryVectorStore:
    """记忆向量存储管理器"""
    
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self.memories: Dict[str, MemoryVector] = {}
        self.user_memories: Dict[str, List[str]] = {}
        self.type_index: Dict[str, List[str]] = {}
        self.timestamp_index = []
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
    def add_memory(self, user_id: str, memory_type: str, content: str,
                  embedding: np.ndarray, metadata: Dict[str, Any] = None,
                  importance: float = 0.5) -> str:
        """
        添加记忆向量
        
        Args:
            user_id: 用户ID
            memory_type: 记忆类型
            content: 记忆内容
            embedding: 记忆向量
            metadata: 元数据
            importance: 重要性评分
            
        Returns:
            str: 记忆ID
        """
        try:
            if embedding.shape[0] != self.dimension:
                logger.error(f"Embedding dimension mismatch: {embedding.shape[0]} vs {self.dimension}")
                return None
                
            memory_id = str(uuid.uuid4())
            now = datetime.now()
            
            if metadata is None:
                metadata = {}
                
            memory = MemoryVector(
                id=memory_id,
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                embedding=embedding.copy(),
                timestamp=now,
                metadata=metadata,
                importance=importance,
                access_count=0,
                last_accessed=now
            )
            
            # 存储记忆
            self.memories[memory_id] = memory
            self.embedding_cache[memory_id] = embedding.copy()
            
            # 更新索引
            if user_id not in self.user_memories:
                self.user_memories[user_id] = []
            self.user_memories[user_id].append(memory_id)
            
            if memory_type not in self.type_index:
                self.type_index[memory_type] = []
            self.type_index[memory_type].append(memory_id)
            
            self.timestamp_index.append((memory_id, now))
            
            logger.info(f"Added memory vector: {memory_id} for user {user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to add memory vector: {str(e)}")
            return None
            
    def get_memory(self, memory_id: str) -> Optional[MemoryVector]:
        """
        获取记忆向量
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Optional[MemoryVector]: 记忆向量对象
        """
        try:
            if memory_id not in self.memories:
                return None
                
            memory = self.memories[memory_id]
            
            # 更新访问统计
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            
            return memory
            
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {str(e)}")
            return None
            
    def search_memories(self, query: MemoryQuery) -> List[Tuple[MemoryVector, float]]:
        """
        搜索记忆向量
        
        Args:
            query: 搜索查询
            
        Returns:
            List[Tuple[MemoryVector, float]]: 记忆向量和相似度得分列表
        """
        try:
            results = []
            
            # 过滤记忆类型
            candidate_ids = set()
            if query.memory_types:
                for memory_type in query.memory_types:
                    if memory_type in self.type_index:
                        candidate_ids.update(self.type_index[memory_type])
            else:
                candidate_ids = set(self.memories.keys())
                
            # 过滤时间范围
            if query.time_range:
                start_time, end_time = query.time_range
                candidate_ids = {
                    memory_id for memory_id in candidate_ids
                    if start_time <= self.memories[memory_id].timestamp <= end_time
                }
                
            # 过滤重要性
            candidate_ids = {
                memory_id for memory_id in candidate_ids
                if self.memories[memory_id].importance >= query.importance_threshold
            }
            
            # 计算相似度
            for memory_id in candidate_ids:
                memory = self.memories[memory_id]
                similarity = self._calculate_similarity(
                    query.query_embedding, memory.embedding)
                    
                if similarity >= query.similarity_threshold:
                    results.append((memory, similarity))
                    
            # 按相似度排序并限制结果数量
            results.sort(key=lambda x: x[1], reverse=True)
            results = results[:query.max_results]
            
            logger.info(f"Memory search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {str(e)}")
            return []
            
    def update_memory_importance(self, memory_id: str, importance: float) -> bool:
        """
        更新记忆重要性
        
        Args:
            memory_id: 记忆ID
            importance: 新的重要性评分
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if memory_id not in self.memories:
                return False
                
            self.memories[memory_id].importance = max(0.0, min(1.0, importance))
            logger.info(f"Updated memory {memory_id} importance to {importance}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update memory importance: {str(e)}")
            return False
            
    def consolidate_memories(self, user_id: str, consolidation_threshold: float = 0.9) -> List[str]:
        """
        合并相似记忆
        
        Args:
            user_id: 用户ID
            consolidation_threshold: 合并阈值
            
        Returns:
            List[str]: 被合并的记忆ID列表
        """
        try:
            if user_id not in self.user_memories:
                return []
                
            user_memory_ids = self.user_memories[user_id]
            consolidated_ids = []
            
            # 查找相似记忆对
            similar_pairs = []
            for i, mem_id1 in enumerate(user_memory_ids):
                for mem_id2 in user_memory_ids[i+1:]:
                    if (mem_id1 in self.embedding_cache and 
                        mem_id2 in self.embedding_cache):
                        similarity = self._calculate_similarity(
                            self.embedding_cache[mem_id1],
                            self.embedding_cache[mem_id2]
                        )
                        if similarity > consolidation_threshold:
                            similar_pairs.append((mem_id1, mem_id2, similarity))
                            
            # 合并相似记忆（简化实现）
            for mem_id1, mem_id2, similarity in similar_pairs:
                if mem_id1 in self.memories and mem_id2 in self.memories:
                    # 保留重要性更高的记忆
                    mem1 = self.memories[mem_id1]
                    mem2 = self.memories[mem_id2]
                    
                    if mem1.importance >= mem2.importance:
                        self._merge_memories(mem1, mem2)
                        consolidated_ids.append(mem_id2)
                    else:
                        self._merge_memories(mem2, mem1)
                        consolidated_ids.append(mem_id1)
                        
            # 移除被合并的记忆
            for memory_id in consolidated_ids:
                self._remove_memory(memory_id)
                
            logger.info(f"Consolidated {len(consolidated_ids)} memories for user {user_id}")
            return consolidated_ids
            
        except Exception as e:
            logger.error(f"Failed to consolidate memories: {str(e)}")
            return []
            
    def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户记忆统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 记忆统计信息
        """
        try:
            if user_id not in self.user_memories:
                return {}
                
            memory_ids = self.user_memories[user_id]
            memories = [self.memories[mem_id] for mem_id in memory_ids]
            
            stats = {
                "total_memories": len(memories),
                "memory_types": {},
                "average_importance": 0.0,
                "total_access_count": 0,
                "recent_memories": 0
            }
            
            # 按类型统计
            for memory in memories:
                mem_type = memory.memory_type
                if mem_type not in stats["memory_types"]:
                    stats["memory_types"][mem_type] = 0
                stats["memory_types"][mem_type] += 1
                
            # 计算平均值
            if memories:
                stats["average_importance"] = sum(m.importance for m in memories) / len(memories)
                stats["total_access_count"] = sum(m.access_count for m in memories)
                
                # 最近记忆（过去7天）
                week_ago = datetime.now().timestamp() - 7 * 24 * 3600
                stats["recent_memories"] = sum(
                    1 for m in memories if m.timestamp.timestamp() > week_ago
                )
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user memory stats: {str(e)}")
            return {}
            
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
            
    def _merge_memories(self, target_memory: MemoryVector, source_memory: MemoryVector):
        """合并两个记忆"""
        try:
            # 更新目标记忆
            target_memory.content += f"\n[合并自 {source_memory.timestamp}]: {source_memory.content}"
            target_memory.importance = max(target_memory.importance, source_memory.importance)
            target_memory.access_count += source_memory.access_count
            target_memory.last_accessed = max(target_memory.last_accessed, source_memory.last_accessed)
            
            # 合并元数据
            for key, value in source_memory.metadata.items():
                if key not in target_memory.metadata:
                    target_memory.metadata[key] = value
                    
        except Exception as e:
            logger.error(f"Failed to merge memories: {str(e)}")
            
    def _remove_memory(self, memory_id: str):
        """移除记忆"""
        try:
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                
                # 从索引中移除
                if memory.user_id in self.user_memories:
                    self.user_memories[memory.user_id].remove(memory_id)
                    
                if memory.memory_type in self.type_index:
                    self.type_index[memory.memory_type].remove(memory_id)
                    
                self.timestamp_index = [(mid, ts) for mid, ts in self.timestamp_index if mid != memory_id]
                
                # 从缓存中移除
                if memory_id in self.embedding_cache:
                    del self.embedding_cache[memory_id]
                    
                # 从主存储中移除
                del self.memories[memory_id]
                
        except Exception as e:
            logger.error(f"Failed to remove memory {memory_id}: {str(e)}")
            
    def save_to_file(self, file_path: str) -> bool:
        """保存记忆向量到文件"""
        try:
            save_data = {
                "dimension": self.dimension,
                "memories": {
                    mem_id: {
                        "user_id": memory.user_id,
                        "memory_type": memory.memory_type,
                        "content": memory.content,
                        "embedding": memory.embedding.tolist(),
                        "timestamp": memory.timestamp.isoformat(),
                        "metadata": memory.metadata,
                        "importance": memory.importance,
                        "access_count": memory.access_count,
                        "last_accessed": memory.last_accessed.isoformat()
                    }
                    for mem_id, memory in self.memories.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            logger.info(f"Saved memory vectors to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save memory vectors: {str(e)}")
            return False
            
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载记忆向量"""
        try:
            with open(file_path, 'r') as f:
                save_data = json.load(f)
                
            self.dimension = save_data["dimension"]
            self.memories.clear()
            self.user_memories.clear()
            self.type_index.clear()
            self.timestamp_index.clear()
            self.embedding_cache.clear()
            
            for mem_id, memory_data in save_data["memories"].items():
                memory = MemoryVector(
                    id=mem_id,
                    user_id=memory_data["user_id"],
                    memory_type=memory_data["memory_type"],
                    content=memory_data["content"],
                    embedding=np.array(memory_data["embedding"]),
                    timestamp=datetime.fromisoformat(memory_data["timestamp"]),
                    metadata=memory_data["metadata"],
                    importance=memory_data["importance"],
                    access_count=memory_data["access_count"],
                    last_accessed=datetime.fromisoformat(memory_data["last_accessed"])
                )
                
                self.memories[mem_id] = memory
                self.embedding_cache[mem_id] = memory.embedding.copy()
                
                # 重建索引
                if memory.user_id not in self.user_memories:
                    self.user_memories[memory.user_id] = []
                self.user_memories[memory.user_id].append(mem_id)
                
                if memory.memory_type not in self.type_index:
                    self.type_index[memory.memory_type] = []
                self.type_index[memory.memory_type].append(mem_id)
                
                self.timestamp_index.append((mem_id, memory.timestamp))
                
            logger.info(f"Loaded memory vectors from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load memory vectors: {str(e)}")
            return False

