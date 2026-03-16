"""
向量数据库：用于存储和检索向量数据
负责记忆系统、知识库等向量数据的存储和检索
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import time
import logging
import asyncio

@dataclass
class VectorRecord:
    """向量记录"""
    id: str
    vector: np.ndarray
    metadata: Dict[str, Any]
    timestamp: float
    collection: str

@dataclass
class SearchResult:
    """搜索结果"""
    record: VectorRecord
    similarity: float
    distance: float

class VectorDatabase:
    """向量数据库"""
    
    def __init__(self, storage_path: str = "data/vector_db"):
        self.storage_path = storage_path
        self.collections: Dict[str, List[VectorRecord]] = {}
        self.vector_index: Dict[str, np.ndarray] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化向量数据库"""
        if self.initialized:
            return
            
        logging.info("初始化向量数据库...")
        
        # 创建存储目录
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        # 加载现有数据
        await self._load_existing_data()
        
        self.initialized = True
        logging.info("向量数据库初始化完成")
    
    async def _load_existing_data(self):
        """加载现有数据"""
        try:
            data_file = f"{self.storage_path}/vector_data.json"
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for collection_name, records_data in data.get('collections', {}).items():
                    self.collections[collection_name] = []
                    for record_data in records_data:
                        vector = np.array(record_data['vector'])
                        record = VectorRecord(
                            id=record_data['id'],
                            vector=vector,
                            metadata=record_data['metadata'],
                            timestamp=record_data['timestamp'],
                            collection=collection_name
                        )
                        self.collections[collection_name].append(record)
                        self.vector_index[record_data['id']] = vector
                        
            logging.info(f"加载了 {len(self.collections)} 个集合的向量数据")
            
        except Exception as e:
            logging.error(f"加载向量数据失败: {e}")
    
    async def create_collection(self, collection_name: str) -> bool:
        """创建集合"""
        if collection_name in self.collections:
            logging.warning(f"集合已存在: {collection_name}")
            return False
            
        self.collections[collection_name] = []
        logging.info(f"创建集合: {collection_name}")
        return True
    
    async def insert_vector(self, collection_name: str, vector: np.ndarray, 
                          metadata: Dict[str, Any]) -> str:
        """插入向量"""
        if collection_name not in self.collections:
            await self.create_collection(collection_name)
        
        # 生成唯一ID
        vector_id = f"vec_{int(time.time() * 1000)}_{len(self.collections[collection_name])}"
        
        record = VectorRecord(
            id=vector_id,
            vector=vector,
            metadata=metadata,
            timestamp=time.time(),
            collection=collection_name
        )
        
        self.collections[collection_name].append(record)
        self.vector_index[vector_id] = vector
        
        logging.debug(f"插入向量到集合 {collection_name}: {vector_id}")
        return vector_id
    
    async def search_similar(self, collection_name: str, query_vector: np.ndarray, 
                           top_k: int = 10, min_similarity: float = 0.0) -> List[SearchResult]:
        """相似度搜索"""
        if collection_name not in self.collections:
            return []
        
        collection = self.collections[collection_name]
        if not collection:
            return []
        
        results = []
        
        for record in collection:
            similarity = self._cosine_similarity(query_vector, record.vector)
            distance = self._euclidean_distance(query_vector, record.vector)
            
            if similarity >= min_similarity:
                results.append(SearchResult(
                    record=record,
                    similarity=similarity,
                    distance=distance
                ))
        
        # 按相似度排序
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _euclidean_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算欧几里得距离"""
        return np.linalg.norm(vec1 - vec2)
    
    async def get_vector(self, vector_id: str) -> Optional[VectorRecord]:
        """获取向量记录"""
        for collection in self.collections.values():
            for record in collection:
                if record.id == vector_id:
                    return record
        return None
    
    async def update_metadata(self, vector_id: str, metadata: Dict[str, Any]) -> bool:
        """更新元数据"""
        record = await self.get_vector(vector_id)
        if not record:
            return False
            
        record.metadata.update(metadata)
        return True
    
    async def delete_vector(self, vector_id: str) -> bool:
        """删除向量"""
        for collection_name, collection in self.collections.items():
            for i, record in enumerate(collection):
                if record.id == vector_id:
                    del collection[i]
                    del self.vector_index[vector_id]
                    return True
        return False
    
    async def save(self):
        """保存数据到磁盘"""
        try:
            data = {
                'collections': {}
            }
            
            for collection_name, records in self.collections.items():
                data['collections'][collection_name] = []
                for record in records:
                    data['collections'][collection_name].append({
                        'id': record.id,
                        'vector': record.vector.tolist(),
                        'metadata': record.metadata,
                        'timestamp': record.timestamp,
                        'collection': record.collection
                    })
            
            data_file = f"{self.storage_path}/vector_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logging.info("向量数据库数据已保存")
            
        except Exception as e:
            logging.error(f"保存向量数据失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        total_vectors = sum(len(collection) for collection in self.collections.values())
        
        return {
            "total_collections": len(self.collections),
            "total_vectors": total_vectors,
            "collections": {
                name: len(records) for name, records in self.collections.items()
            }
        }

# 全局向量数据库实例
vector_database = VectorDatabase()