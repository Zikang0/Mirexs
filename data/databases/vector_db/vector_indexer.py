"""
向量索引管理器
提供统一的向量索引管理和维护功能
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from datetime import datetime
import json
import threading
from dataclasses import dataclass
from .faiss_integration import FAISSIntegration
from .chroma_integration import ChromaIntegration

logger = logging.getLogger(__name__)

@dataclass
class IndexConfig:
    """索引配置数据类"""
    index_type: str  # faiss, chroma
    dimension: int
    index_name: str
    description: str
    parameters: Dict[str, Any]

@dataclass
class IndexStats:
    """索引统计数据类"""
    total_vectors: int
    dimension: int
    memory_usage: float  # MB
    query_performance: float  # queries per second
    last_updated: datetime

class VectorIndexer:
    """向量索引管理器"""
    
    def __init__(self, base_storage_path: str = "vector_indices"):
        self.base_storage_path = base_storage_path
        self.indices: Dict[str, Any] = {}  # 索引名称 -> 索引对象
        self.index_configs: Dict[str, IndexConfig] = {}
        self.index_stats: Dict[str, IndexStats] = {}
        self.lock = threading.RLock()
        
        # 确保存储目录存在
        import os
        os.makedirs(base_storage_path, exist_ok=True)
        
    def create_index(self, config: IndexConfig) -> bool:
        """
        创建向量索引
        
        Args:
            config: 索引配置
            
        Returns:
            bool: 是否创建成功
        """
        try:
            with self.lock:
                if config.index_name in self.indices:
                    logger.warning(f"Index {config.index_name} already exists")
                    return False
                    
                if config.index_type == "faiss":
                    index = FAISSIntegration(
                        dimension=config.dimension,
                        index_type=config.parameters.get("faiss_index_type", "IVF")
                    )
                    
                    # 创建索引
                    if not index.create_index(
                        nlist=config.parameters.get("nlist", 100),
                        nprobe=config.parameters.get("nprobe", 10),
                        metric=config.parameters.get("metric", "l2")
                    ):
                        return False
                        
                elif config.index_type == "chroma":
                    index = ChromaIntegration(
                        persist_directory=f"{self.base_storage_path}/{config.index_name}",
                        host=config.parameters.get("host"),
                        port=config.parameters.get("port")
                    )
                    
                    # 连接到Chroma
                    if not index.connect():
                        return False
                        
                    # 创建集合
                    collection_metadata = {
                        "description": config.description,
                        "dimension": config.dimension,
                        "created_by": "vector_indexer"
                    }
                    
                    if not index.create_collection(config.index_name, collection_metadata):
                        return False
                        
                else:
                    logger.error(f"Unsupported index type: {config.index_type}")
                    return False
                    
                # 存储索引和配置
                self.indices[config.index_name] = index
                self.index_configs[config.index_name] = config
                
                # 初始化统计信息
                self.index_stats[config.index_name] = IndexStats(
                    total_vectors=0,
                    dimension=config.dimension,
                    memory_usage=0.0,
                    query_performance=0.0,
                    last_updated=datetime.now()
                )
                
                logger.info(f"Created {config.index_type} index: {config.index_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create index {config.index_name}: {str(e)}")
            return False
            
    def add_vectors(self, index_name: str, vectors: np.ndarray,
                   ids: List[str] = None, metadata_list: List[Dict[str, Any]] = None) -> bool:
        """
        添加向量到索引
        
        Args:
            index_name: 索引名称
            vectors: 向量数组
            ids: 向量ID列表
            metadata_list: 元数据列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return False
                    
                index = self.indices[index_name]
                config = self.index_configs[index_name]
                
                if config.index_type == "faiss":
                    # 对于FAISS，如果需要训练但未训练，先训练
                    if hasattr(index, 'is_trained') and not index.is_trained:
                        # 使用前1000个向量进行训练
                        training_size = min(1000, len(vectors))
                        if not index.train_index(vectors[:training_size]):
                            return False
                            
                    success = index.add_vectors(vectors, ids, metadata_list)
                    
                elif config.index_type == "chroma":
                    # 对于Chroma，将向量转换为文档
                    documents = [f"Vector {id}" for id in ids] if ids else [f"Vector {i}" for i in range(len(vectors))]
                    success = index.add_documents(
                        collection_name=index_name,
                        documents=documents,
                        metadatas=metadata_list,
                        ids=ids,
                        embeddings=vectors
                    )
                    
                else:
                    logger.error(f"Unsupported index type: {config.index_type}")
                    return False
                    
                if success:
                    # 更新统计信息
                    stats = self.index_stats[index_name]
                    stats.total_vectors += len(vectors)
                    stats.last_updated = datetime.now()
                    
                    # 估算内存使用
                    if config.index_type == "faiss":
                        stats.memory_usage = self._estimate_faiss_memory_usage(index)
                        
                return success
                
        except Exception as e:
            logger.error(f"Failed to add vectors to index {index_name}: {str(e)}")
            return False
            
    def search_vectors(self, index_name: str, query_vectors: np.ndarray, k: int = 10,
                      filters: Dict[str, Any] = None) -> List[List[Tuple[str, float, Dict[str, Any]]]]:
        """
        搜索相似向量
        
        Args:
            index_name: 索引名称
            query_vectors: 查询向量
            k: 返回的最近邻数量
            filters: 过滤条件
            
        Returns:
            List[List[Tuple[str, float, Dict[str, Any]]]]: 搜索结果
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return []
                    
                index = self.indices[index_name]
                config = self.index_configs[index_name]
                
                start_time = datetime.now()
                
                if config.index_type == "faiss":
                    results = index.search_vectors(query_vectors, k, include_metadata=True)
                    
                elif config.index_type == "chroma":
                    # 对于Chroma，使用嵌入向量查询
                    results = []
                    for query_vec in query_vectors:
                        chroma_results = index.query_collection(
                            collection_name=index_name,
                            query_embeddings=[query_vec],
                            n_results=k,
                            where=filters
                        )
                        
                        query_results = []
                        if chroma_results and "ids" in chroma_results:
                            for i, vec_id in enumerate(chroma_results["ids"][0]):
                                distance = chroma_results["distances"][0][i] if "distances" in chroma_results else 0.0
                                metadata = chroma_results["metadatas"][0][i] if "metadatas" in chroma_results else {}
                                query_results.append((vec_id, distance, metadata))
                                
                        results.append(query_results)
                        
                else:
                    logger.error(f"Unsupported index type: {config.index_type}")
                    return []
                    
                # 更新性能统计
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > 0:
                    qps = len(query_vectors) / elapsed
                    self.index_stats[index_name].query_performance = qps
                    
                logger.info(f"Search completed for index {index_name}: {len(query_vectors)} queries")
                return results
                
        except Exception as e:
            logger.error(f"Failed to search index {index_name}: {str(e)}")
            return []
            
    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """
        获取索引信息
        
        Args:
            index_name: 索引名称
            
        Returns:
            Dict[str, Any]: 索引信息
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return {}
                    
                config = self.index_configs[index_name]
                stats = self.index_stats[index_name]
                index = self.indices[index_name]
                
                info = {
                    "name": index_name,
                    "type": config.index_type,
                    "dimension": config.dimension,
                    "description": config.description,
                    "total_vectors": stats.total_vectors,
                    "memory_usage_mb": stats.memory_usage,
                    "query_performance_qps": stats.query_performance,
                    "last_updated": stats.last_updated.isoformat(),
                    "parameters": config.parameters
                }
                
                # 添加特定索引类型的额外信息
                if config.index_type == "faiss" and hasattr(index, 'get_index_stats'):
                    faiss_stats = index.get_index_stats()
                    info["faiss_stats"] = faiss_stats
                    
                elif config.index_type == "chroma" and hasattr(index, 'get_collection_info'):
                    chroma_info = index.get_collection_info(index_name)
                    info["chroma_info"] = chroma_info
                    
                return info
                
        except Exception as e:
            logger.error(f"Failed to get index info for {index_name}: {str(e)}")
            return {}
            
    def delete_index(self, index_name: str) -> bool:
        """
        删除索引
        
        Args:
            index_name: 索引名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return False
                    
                # 清理索引对象
                index = self.indices[index_name]
                if hasattr(index, 'close'):
                    index.close()
                    
                # 从管理器中移除
                del self.indices[index_name]
                del self.index_configs[index_name]
                del self.index_stats[index_name]
                
                # 清理存储文件
                import shutil
                index_path = f"{self.base_storage_path}/{index_name}"
                if os.path.exists(index_path):
                    shutil.rmtree(index_path)
                    
                logger.info(f"Deleted index: {index_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {str(e)}")
            return False
            
    def save_index(self, index_name: str) -> bool:
        """
        保存索引到文件
        
        Args:
            index_name: 索引名称
            
        Returns:
            bool: 是否保存成功
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return False
                    
                index = self.indices[index_name]
                config = self.index_configs[index_name]
                
                if config.index_type == "faiss":
                    file_path = f"{self.base_storage_path}/{index_name}.faiss"
                    success = index.save_index(file_path)
                    
                    # 保存配置
                    if success:
                        config_path = f"{self.base_storage_path}/{index_name}.config"
                        with open(config_path, 'w') as f:
                            json.dump({
                                "index_type": config.index_type,
                                "dimension": config.dimension,
                                "index_name": config.index_name,
                                "description": config.description,
                                "parameters": config.parameters
                            }, f, indent=2)
                            
                elif config.index_type == "chroma":
                    # Chroma自动持久化，只需备份
                    backup_path = f"{self.base_storage_path}/{index_name}_backup.json"
                    success = index.backup_collection(index_name, backup_path)
                    
                else:
                    logger.error(f"Unsupported index type: {config.index_type}")
                    return False
                    
                if success:
                    logger.info(f"Saved index {index_name}")
                    
                return success
                
        except Exception as e:
            logger.error(f"Failed to save index {index_name}: {str(e)}")
            return False
            
    def load_index(self, index_name: str) -> bool:
        """
        从文件加载索引
        
        Args:
            index_name: 索引名称
            
        Returns:
            bool: 是否加载成功
        """
        try:
            with self.lock:
                if index_name in self.indices:
                    logger.warning(f"Index {index_name} already loaded")
                    return False
                    
                # 检查配置文件
                config_path = f"{self.base_storage_path}/{index_name}.config"
                if not os.path.exists(config_path):
                    logger.error(f"Config file not found: {config_path}")
                    return False
                    
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    
                config = IndexConfig(**config_data)
                
                # 创建索引
                if not self.create_index(config):
                    return False
                    
                index = self.indices[index_name]
                
                if config.index_type == "faiss":
                    file_path = f"{self.base_storage_path}/{index_name}.faiss"
                    success = index.load_index(file_path)
                    
                elif config.index_type == "chroma":
                    # Chroma自动加载，无需额外操作
                    success = True
                    
                else:
                    logger.error(f"Unsupported index type: {config.index_type}")
                    return False
                    
                if success:
                    logger.info(f"Loaded index {index_name}")
                    
                return success
                
        except Exception as e:
            logger.error(f"Failed to load index {index_name}: {str(e)}")
            return False
            
    def optimize_index(self, index_name: str) -> bool:
        """
        优化索引
        
        Args:
            index_name: 索引名称
            
        Returns:
            bool: 是否优化成功
        """
        try:
            with self.lock:
                if index_name not in self.indices:
                    logger.error(f"Index {index_name} not found")
                    return False
                    
                index = self.indices[index_name]
                
                if hasattr(index, 'optimize_index'):
                    success = index.optimize_index()
                    if success:
                        logger.info(f"Optimized index {index_name}")
                    return success
                else:
                    logger.warning(f"Index {index_name} doesn't support optimization")
                    return True  # 不支持优化不算失败
                    
        except Exception as e:
            logger.error(f"Failed to optimize index {index_name}: {str(e)}")
            return False
            
    def _estimate_faiss_memory_usage(self, faiss_index: FAISSIntegration) -> float:
        """估算FAISS索引内存使用量（MB）"""
        try:
            if not hasattr(faiss_index, 'index') or faiss_index.index is None:
                return 0.0
                
            # 简化的内存估算
            # 实际内存使用取决于索引类型和参数
            if hasattr(faiss_index.index, 'ntotal'):
                n_vectors = faiss_index.index.ntotal
                dimension = faiss_index.index.d
                
                # 估算：每个向量占用 dimension * 4 字节（float32）
                vector_memory = n_vectors * dimension * 4 / (1024 * 1024)  # MB
                
                # 索引结构额外内存（估算）
                index_overhead = vector_memory * 0.5  # 50% 额外开销
                
                return vector_memory + index_overhead
                
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to estimate FAISS memory usage: {str(e)}")
            return 0.0
            
    def list_indices(self) -> List[Dict[str, Any]]:
        """
        列出所有索引
        
        Returns:
            List[Dict[str, Any]]: 索引列表信息
        """
        try:
            with self.lock:
                indices_info = []
                for index_name in self.indices.keys():
                    info = self.get_index_info(index_name)
                    indices_info.append(info)
                    
                return indices_info
                
        except Exception as e:
            logger.error(f"Failed to list indices: {str(e)}")
            return []

