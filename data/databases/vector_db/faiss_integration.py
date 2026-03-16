"""
FAISS向量搜索集成
提供高效的向量相似度搜索功能
"""

import faiss
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import pickle
import os
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class FAISSIntegration:
    """FAISS向量搜索集成类"""
    
    def __init__(self, dimension: int = 768, index_type: str = "IVF"):
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.metadata: Dict[str, Any] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.is_trained = False
        self.is_loaded = False
        
    def create_index(self, nlist: int = 100, nprobe: int = 10, metric: str = "l2") -> bool:
        """
        创建FAISS索引
        
        Args:
            nlist: 聚类中心数量（用于IVF）
            nprobe: 搜索时探查的聚类数量
            metric: 距离度量（l2或ip）
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if self.index_type == "IVF":
                # 使用IVF（倒排文件）索引
                quantizer = faiss.IndexFlatIP(self.dimension) if metric == "ip" else faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist, metric)
                self.index.nprobe = nprobe
            elif self.index_type == "Flat":
                # 使用平面索引（精确搜索）
                if metric == "ip":
                    self.index = faiss.IndexFlatIP(self.dimension)
                else:
                    self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "HNSW":
                # 使用HNSW（分层可导航小世界）索引
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
                self.index.hnsw.efConstruction = 200
                self.index.hnsw.efSearch = 128
            else:
                logger.error(f"Unsupported index type: {self.index_type}")
                return False
                
            self.metadata = {
                "index_type": self.index_type,
                "dimension": self.dimension,
                "metric": metric,
                "created_at": self._get_timestamp(),
                "nlist": nlist if self.index_type == "IVF" else None,
                "nprobe": nprobe if self.index_type == "IVF" else None
            }
            
            logger.info(f"Created FAISS index: {self.index_type}, dim={self.dimension}, metric={metric}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {str(e)}")
            return False
            
    def train_index(self, training_vectors: np.ndarray) -> bool:
        """
        训练索引（仅对需要训练的索引类型）
        
        Args:
            training_vectors: 训练向量
            
        Returns:
            bool: 是否训练成功
        """
        try:
            if self.index is None:
                logger.error("Index not created")
                return False
                
            if not self.index.is_trained:
                if training_vectors.shape[1] != self.dimension:
                    logger.error(f"Training vectors dimension mismatch: {training_vectors.shape[1]} vs {self.dimension}")
                    return False
                    
                self.index.train(training_vectors.astype(np.float32))
                self.is_trained = True
                logger.info(f"Trained FAISS index with {len(training_vectors)} vectors")
            else:
                logger.info("Index already trained")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to train FAISS index: {str(e)}")
            return False
            
    def add_vectors(self, vectors: np.ndarray, ids: List[str] = None, 
                   metadata_list: List[Dict[str, Any]] = None) -> bool:
        """
        添加向量到索引
        
        Args:
            vectors: 向量数组
            ids: 向量ID列表
            metadata_list: 元数据列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if self.index is None:
                logger.error("Index not created")
                return False
                
            if vectors.shape[1] != self.dimension:
                logger.error(f"Vectors dimension mismatch: {vectors.shape[1]} vs {self.dimension}")
                return False
                
            n_vectors = vectors.shape[0]
            
            # 生成ID
            if ids is None:
                ids = [f"vec_{i}" for i in range(len(self.id_to_index), len(self.id_to_index) + n_vectors)]
                
            if len(ids) != n_vectors:
                logger.error(f"IDs count mismatch: {len(ids)} vs {n_vectors}")
                return False
                
            # 添加向量到索引
            start_index = self.index.ntotal
            self.index.add(vectors.astype(np.float32))
            
            # 更新ID映射
            for i, vec_id in enumerate(ids):
                index_pos = start_index + i
                self.id_to_index[vec_id] = index_pos
                self.index_to_id[index_pos] = vec_id
                
            # 更新元数据
            if metadata_list:
                for i, metadata in enumerate(metadata_list):
                    vec_id = ids[i]
                    if "vectors" not in self.metadata:
                        self.metadata["vectors"] = {}
                    self.metadata["vectors"][vec_id] = metadata
                    
            self.metadata["total_vectors"] = self.index.ntotal
            self.metadata["last_updated"] = self._get_timestamp()
            
            logger.info(f"Added {n_vectors} vectors to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add vectors to FAISS index: {str(e)}")
            return False
            
    def search_vectors(self, query_vectors: np.ndarray, k: int = 10,
                      include_metadata: bool = True) -> List[List[Tuple[str, float, Dict[str, Any]]]]:
        """
        搜索相似向量
        
        Args:
            query_vectors: 查询向量
            k: 返回的最近邻数量
            include_metadata: 是否包含元数据
            
        Returns:
            List[List[Tuple[str, float, Dict[str, Any]]]]: 搜索结果
        """
        try:
            if self.index is None:
                logger.error("Index not created")
                return []
                
            if query_vectors.shape[1] != self.dimension:
                logger.error(f"Query vectors dimension mismatch: {query_vectors.shape[1]} vs {self.dimension}")
                return []
                
            # 执行搜索
            distances, indices = self.index.search(query_vectors.astype(np.float32), k)
            
            results = []
            for i in range(len(query_vectors)):
                query_results = []
                for j in range(len(indices[i])):
                    idx = indices[i][j]
                    if idx != -1:  # -1表示没有足够的结果
                        vec_id = self.index_to_id.get(idx, f"unknown_{idx}")
                        distance = float(distances[i][j])
                        
                        metadata = {}
                        if include_metadata and "vectors" in self.metadata:
                            metadata = self.metadata["vectors"].get(vec_id, {})
                            
                        query_results.append((vec_id, distance, metadata))
                        
                results.append(query_results)
                
            logger.info(f"FAISS search completed: {len(query_vectors)} queries, {k} results per query")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search FAISS index: {str(e)}")
            return []
            
    def get_vector_by_id(self, vector_id: str) -> Optional[np.ndarray]:
        """
        根据ID获取向量
        
        Args:
            vector_id: 向量ID
            
        Returns:
            Optional[np.ndarray]: 向量数据
        """
        try:
            if vector_id not in self.id_to_index:
                logger.error(f"Vector ID not found: {vector_id}")
                return None
                
            index_pos = self.id_to_index[vector_id]
            
            # FAISS没有直接获取向量的方法，需要重建
            # 这里使用近似方法：搜索自身
            if self.index.ntotal == 0:
                return None
                
            # 创建一个查询向量来搜索自身
            dummy_query = np.zeros((1, self.dimension), dtype=np.float32)
            distances, indices = self.index.search(dummy_query, self.index.ntotal)
            
            # 这种方法不准确，实际应该保存向量副本
            logger.warning("FAISS doesn't support direct vector retrieval. Returning None.")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get vector by ID {vector_id}: {str(e)}")
            return None
            
    def remove_vector(self, vector_id: str) -> bool:
        """
        移除向量
        
        Args:
            vector_id: 要移除的向量ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if vector_id not in self.id_to_index:
                logger.error(f"Vector ID not found: {vector_id}")
                return False
                
            # FAISS不支持直接删除向量，需要重建索引
            # 这里标记为已删除，在下次保存/加载时处理
            index_pos = self.id_to_index[vector_id]
            
            # 从映射中移除
            del self.id_to_index[vector_id]
            del self.index_to_id[index_pos]
            
            # 从元数据中移除
            if "vectors" in self.metadata and vector_id in self.metadata["vectors"]:
                del self.metadata["vectors"][vector_id]
                
            logger.info(f"Marked vector {vector_id} for removal (will be effective after index rebuild)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove vector {vector_id}: {str(e)}")
            return False
            
    def save_index(self, file_path: str) -> bool:
        """
        保存索引到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if self.index is None:
                logger.error("Index not created")
                return False
                
            # 保存FAISS索引
            faiss.write_index(self.index, file_path)
            
            # 保存元数据和映射
            metadata_file = file_path + ".metadata"
            metadata_data = {
                "metadata": self.metadata,
                "id_to_index": self.id_to_index,
                "index_to_id": self.index_to_id
            }
            
            with open(metadata_file, 'wb') as f:
                pickle.dump(metadata_data, f)
                
            logger.info(f"Saved FAISS index to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {str(e)}")
            return False
            
    def load_index(self, file_path: str) -> bool:
        """
        从文件加载索引
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Index file not found: {file_path}")
                return False
                
            # 加载FAISS索引
            self.index = faiss.read_index(file_path)
            
            # 加载元数据和映射
            metadata_file = file_path + ".metadata"
            if os.path.exists(metadata_file):
                with open(metadata_file, 'rb') as f:
                    metadata_data = pickle.load(f)
                    
                self.metadata = metadata_data.get("metadata", {})
                self.id_to_index = metadata_data.get("id_to_index", {})
                self.index_to_id = metadata_data.get("index_to_id", {})
                
            self.is_loaded = True
            self.dimension = self.index.d
            self.is_trained = self.index.is_trained
            
            logger.info(f"Loaded FAISS index from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {str(e)}")
            return False
            
    def get_index_stats(self) -> Dict[str, Any]:
        """
        获取索引统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if self.index is None:
                return {}
                
            stats = {
                "total_vectors": self.index.ntotal,
                "dimension": self.index.d,
                "is_trained": self.index.is_trained,
                "index_type": self.metadata.get("index_type", "unknown"),
                "metric": self.metadata.get("metric", "unknown"),
                "id_mapping_size": len(self.id_to_index)
            }
            
            # 添加特定索引类型的统计
            if hasattr(self.index, 'nlist'):
                stats["nlist"] = self.index.nlist
            if hasattr(self.index, 'nprobe'):
                stats["nprobe"] = self.index.nprobe
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {}
            
    def optimize_index(self) -> bool:
        """
        优化索引
        
        Returns:
            bool: 是否优化成功
        """
        try:
            if self.index is None:
                logger.error("Index not created")
                return False
                
            # 不同类型的索引有不同的优化方法
            if hasattr(self.index, 'make_direct_map'):
                # 为IVF索引创建直接映射
                self.index.make_direct_map()
                logger.info("Optimized IVF index with direct map")
                
            # 其他优化操作...
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize FAISS index: {str(e)}")
            return False
            
    def _get_timestamp(self) -> str:
        """获取时间戳字符串"""
        from datetime import datetime
        return datetime.now().isoformat()

