"""
情景记忆模块：存储具体经历和事件
实现基于向量数据库的情景记忆存储和检索
"""

import uuid
import json
import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from chromadb import HttpClient, PersistentClient
from chromadb.config import Settings
import logging

class EpisodicMemory:
    """情景记忆系统 - 存储具体经历和事件"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.collection_name = "episodic_memory"
        self.client = None
        self.collection = None
        self.initialized = False
        
        # 记忆属性
        self.recency_weight = 0.3
        self.importance_weight = 0.4
        self.emotional_weight = 0.3
        
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化向量数据库连接"""
        try:
            # 根据配置选择客户端类型
            if self.config.get("persistent_mode", True):
                self.client = PersistentClient(
                    path=self.config.get("db_path", "./data/memory/episodic"),
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = HttpClient(
                    host=self.config.get("host", "localhost"),
                    port=self.config.get("port", 8000)
                )
            
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Episodic memory storage"}
            )
            
            self.initialized = True
            self.logger.info("情景记忆数据库初始化成功")
            
        except Exception as e:
            self.logger.error(f"情景记忆数据库初始化失败: {e}")
            self.initialized = False
    
    def store_event(self, 
                   event_description: str,
                   timestamp: datetime.datetime = None,
                   importance: float = 0.5,
                   emotional_valence: float = 0.0,
                   emotional_arousal: float = 0.0,
                   context: Dict[str, Any] = None,
                   embeddings: List[float] = None) -> str:
        """
        存储事件到情景记忆
        
        Args:
            event_description: 事件描述
            timestamp: 时间戳
            importance: 重要性权重 (0.0-1.0)
            emotional_valence: 情感效价 (-1.0到1.0)
            emotional_arousal: 情感唤醒度 (0.0-1.0)
            context: 上下文信息
            embeddings: 预计算的嵌入向量
            
        Returns:
            记忆ID
        """
        if not self.initialized:
            raise RuntimeError("情景记忆系统未初始化")
        
        memory_id = str(uuid.uuid4())
        timestamp = timestamp or datetime.datetime.now()
        
        # 创建记忆文档
        memory_doc = {
            "id": memory_id,
            "description": event_description,
            "timestamp": timestamp.isoformat(),
            "importance": float(importance),
            "emotional_valence": float(emotional_valence),
            "emotional_arousal": float(emotional_arousal),
            "context": context or {},
            "access_count": 0,
            "last_accessed": timestamp.isoformat()
        }
        
        # 生成或使用提供的嵌入向量
        if embeddings is None:
            embeddings = self._generate_embeddings(event_description)
        
        # 存储到向量数据库
        try:
            self.collection.add(
                documents=[json.dumps(memory_doc)],
                metadatas=[memory_doc],
                ids=[memory_id],
                embeddings=[embeddings]
            )
            
            self.logger.info(f"情景记忆存储成功: {memory_id}")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"情景记忆存储失败: {e}")
            raise
    
    def retrieve_events(self, 
                       query: str = None,
                       query_embeddings: List[float] = None,
                       start_time: datetime.datetime = None,
                       end_time: datetime.datetime = None,
                       min_importance: float = 0.0,
                       emotional_filter: str = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索相关事件
        
        Args:
            query: 查询文本
            query_embeddings: 查询嵌入向量
            start_time: 开始时间
            end_time: 结束时间
            min_importance: 最小重要性
            emotional_filter: 情感过滤器
            limit: 返回数量限制
            
        Returns:
            相关事件列表
        """
        if not self.initialized:
            return []
        
        try:
            # 基于相似度检索
            if query or query_embeddings is not None:
                if query_embeddings is None:
                    query_embeddings = self._generate_embeddings(query)
                
                results = self.collection.query(
                    query_embeddings=[query_embeddings],
                    n_results=limit * 2  # 获取更多结果用于过滤
                )
                
                memories = self._process_query_results(results)
            else:
                # 获取所有记忆进行过滤
                results = self.collection.get()
                memories = self._convert_to_memory_dicts(results)
            
            # 应用时间过滤器
            if start_time or end_time:
                memories = self._filter_by_time(memories, start_time, end_time)
            
            # 应用重要性过滤器
            if min_importance > 0:
                memories = [m for m in memories if m.get('importance', 0) >= min_importance]
            
            # 应用情感过滤器
            if emotional_filter:
                memories = self._filter_by_emotion(memories, emotional_filter)
            
            # 计算综合分数并排序
            scored_memories = []
            for memory in memories[:limit * 2]:  # 再次限制数量用于评分
                score = self._calculate_memory_score(memory)
                memory['retrieval_score'] = score
                scored_memories.append(memory)
            
            # 按分数排序并返回前limit个
            scored_memories.sort(key=lambda x: x['retrieval_score'], reverse=True)
            
            # 更新访问记录
            for memory in scored_memories[:limit]:
                self._update_access_stats(memory['id'])
            
            return scored_memories[:limit]
            
        except Exception as e:
            self.logger.error(f"情景记忆检索失败: {e}")
            return []
    
    def _generate_embeddings(self, text: str) -> List[float]:
        """生成文本嵌入向量（简化实现）"""
        # 在实际系统中，这里应该调用嵌入模型
        # 这里使用随机向量作为示例
        embedding_dim = 384  # 常见嵌入维度
        return list(np.random.normal(0, 1, embedding_dim))
    
    def _process_query_results(self, results) -> List[Dict[str, Any]]:
        """处理查询结果"""
        memories = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                try:
                    memory = json.loads(doc)
                    # 添加相似度分数
                    if results['distances']:
                        memory['similarity'] = 1 - results['distances'][0][i]
                    memories.append(memory)
                except json.JSONDecodeError:
                    continue
        return memories
    
    def _convert_to_memory_dicts(self, results) -> List[Dict[str, Any]]:
        """转换查询结果为记忆字典"""
        memories = []
        if results and results['metadatas']:
            for metadata in results['metadatas']:
                memories.append(metadata)
        return memories
    
    def _filter_by_time(self, memories: List[Dict], start_time: datetime.datetime, end_time: datetime.datetime):
        """按时间过滤记忆"""
        filtered = []
        for memory in memories:
            memory_time = datetime.datetime.fromisoformat(memory['timestamp'])
            if start_time and memory_time < start_time:
                continue
            if end_time and memory_time > end_time:
                continue
            filtered.append(memory)
        return filtered
    
    def _filter_by_emotion(self, memories: List[Dict], emotional_filter: str):
        """按情感过滤记忆"""
        # 简化的情感过滤
        filtered = []
        for memory in memories:
            valence = memory.get('emotional_valence', 0)
            if emotional_filter == "positive" and valence > 0.3:
                filtered.append(memory)
            elif emotional_filter == "negative" and valence < -0.3:
                filtered.append(memory)
            elif emotional_filter == "neutral" and -0.3 <= valence <= 0.3:
                filtered.append(memory)
        return filtered
    
    def _calculate_memory_score(self, memory: Dict[str, Any]) -> float:
        """计算记忆检索分数"""
        # 基于时效性、重要性、情感强度计算分数
        timestamp = datetime.datetime.fromisoformat(memory['timestamp'])
        recency = self._calculate_recency(timestamp)
        importance = memory.get('importance', 0.5)
        emotional_intensity = abs(memory.get('emotional_valence', 0))
        
        score = (self.recency_weight * recency + 
                self.importance_weight * importance + 
                self.emotional_weight * emotional_intensity)
        
        return score
    
    def _calculate_recency(self, timestamp: datetime.datetime) -> float:
        """计算时效性分数"""
        now = datetime.datetime.now()
        time_diff = (now - timestamp).total_seconds() / 3600  # 小时差
        
        # 指数衰减：24小时后衰减到约0.37
        recency = np.exp(-time_diff / 24.0)
        return recency
    
    def _update_access_stats(self, memory_id: str):
        """更新访问统计"""
        try:
            # 获取当前记忆
            results = self.collection.get(ids=[memory_id])
            if results['metadatas']:
                memory = results['metadatas'][0]
                memory['access_count'] = memory.get('access_count', 0) + 1
                memory['last_accessed'] = datetime.datetime.now().isoformat()
                
                # 更新数据库
                self.collection.update(
                    ids=[memory_id],
                    metadatas=[memory]
                )
        except Exception as e:
            self.logger.warning(f"更新访问统计失败: {e}")
    
    def forget_old_memories(self, max_age_days: int = 30, min_importance: float = 0.1):
        """遗忘旧的不重要记忆"""
        if not self.initialized:
            return
        
        try:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=max_age_days)
            all_memories = self.collection.get()
            
            to_delete = []
            for memory in all_memories['metadatas']:
                memory_time = datetime.datetime.fromisoformat(memory['timestamp'])
                importance = memory.get('importance', 0.5)
                
                if memory_time < cutoff_time and importance < min_importance:
                    to_delete.append(memory['id'])
            
            if to_delete:
                self.collection.delete(ids=to_delete)
                self.logger.info(f"已遗忘 {len(to_delete)} 条旧记忆")
                
        except Exception as e:
            self.logger.error(f"遗忘记忆失败: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        if not self.initialized:
            return {"error": "系统未初始化"}
        
        try:
            results = self.collection.get()
            total_memories = len(results['ids'])
            
            if total_memories == 0:
                return {
                    "total_memories": 0,
                    "avg_importance": 0,
                    "oldest_memory": None,
                    "newest_memory": None
                }
            
            importances = [m.get('importance', 0) for m in results['metadatas']]
            timestamps = [datetime.datetime.fromisoformat(m['timestamp']) for m in results['metadatas']]
            
            return {
                "total_memories": total_memories,
                "avg_importance": sum(importances) / len(importances),
                "oldest_memory": min(timestamps).isoformat(),
                "newest_memory": max(timestamps).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"获取记忆统计失败: {e}")
            return {"error": str(e)}

