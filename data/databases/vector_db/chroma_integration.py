"""
Chroma向量数据库集成
提供与Chroma向量数据库的完整集成功能
"""

import chromadb
from chromadb.config import Settings
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import logging
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)

class ChromaIntegration:
    """Chroma向量数据库集成类"""
    
    def __init__(self, persist_directory: str = "chroma_db", host: str = None, port: int = None):
        self.persist_directory = persist_directory
        self.host = host
        self.port = port
        self.client = None
        self.collections: Dict[str, chromadb.Collection] = {}
        self.is_connected = False
        
    def connect(self) -> bool:
        """
        连接到Chroma数据库
        
        Returns:
            bool: 是否连接成功
        """
        try:
            if self.host and self.port:
                # 连接到远程Chroma服务器
                self.client = chromadb.HttpClient(
                    host=self.host,
                    port=self.port
                )
                logger.info(f"Connected to remote Chroma at {self.host}:{self.port}")
            else:
                # 本地持久化存储
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"Connected to local Chroma at {self.persist_directory}")
                
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Chroma: {str(e)}")
            self.is_connected = False
            return False
            
    def create_collection(self, collection_name: str, metadata: Dict[str, Any] = None,
                         embedding_function: Any = None) -> bool:
        """
        创建集合
        
        Args:
            collection_name: 集合名称
            metadata: 集合元数据
            embedding_function: 嵌入函数
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Chroma")
                return False
                
            if metadata is None:
                metadata = {}
                
            # 添加创建时间戳
            metadata["created_at"] = datetime.now().isoformat()
            metadata["collection_type"] = "vector_store"
            
            # 创建或获取集合
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata=metadata,
                embedding_function=embedding_function
            )
            
            self.collections[collection_name] = collection
            logger.info(f"Created/retrieved collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            return False
            
    def add_documents(self, collection_name: str, documents: List[str],
                     metadatas: List[Dict[str, Any]] = None,
                     ids: List[str] = None, embeddings: List[np.ndarray] = None) -> bool:
        """
        添加文档到集合
        
        Args:
            collection_name: 集合名称
            documents: 文档列表
            metadatas: 元数据列表
            ids: ID列表
            embeddings: 嵌入向量列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return False
                
            collection = self.collections[collection_name]
            
            # 生成ID
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(documents))]
                
            # 准备元数据
            if metadatas is None:
                metadatas = [{} for _ in range(len(documents))]
                
            # 添加时间戳到元数据
            timestamp = datetime.now().isoformat()
            for metadata in metadatas:
                if "added_at" not in metadata:
                    metadata["added_at"] = timestamp
                    
            # 添加文档
            if embeddings is not None:
                # 使用提供的嵌入向量
                collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            else:
                # 使用集合的嵌入函数
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
            logger.info(f"Added {len(documents)} documents to {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to {collection_name}: {str(e)}")
            return False
            
    def query_collection(self, collection_name: str, query_texts: List[str] = None,
                        query_embeddings: List[np.ndarray] = None, n_results: int = 10,
                        where: Dict[str, Any] = None, where_document: Dict[str, Any] = None,
                        include: List[str] = None) -> Dict[str, Any]:
        """
        查询集合
        
        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            query_embeddings: 查询嵌入向量列表
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            include: 包含的字段
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return {}
                
            collection = self.collections[collection_name]
            
            if include is None:
                include = ["metadatas", "documents", "distances"]
                
            # 执行查询
            if query_embeddings is not None:
                results = collection.query(
                    query_embeddings=query_embeddings,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=include
                )
            elif query_texts is not None:
                results = collection.query(
                    query_texts=query_texts,
                    n_results=n_results,
                    where=where,
                    where_document=where_document,
                    include=include
                )
            else:
                logger.error("Either query_texts or query_embeddings must be provided")
                return {}
                
            logger.info(f"Queried {collection_name}, found {len(results.get('ids', [[]])[0])} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query collection {collection_name}: {str(e)}")
            return {}
            
    def update_document(self, collection_name: str, document_id: str,
                       document: str = None, metadata: Dict[str, Any] = None,
                       embedding: np.ndarray = None) -> bool:
        """
        更新文档
        
        Args:
            collection_name: 集合名称
            document_id: 文档ID
            document: 新文档内容
            metadata: 新元数据
            embedding: 新嵌入向量
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return False
                
            collection = self.collections[collection_name]
            
            # 准备更新数据
            update_data = {}
            if document is not None:
                update_data["documents"] = [document]
            if metadata is not None:
                metadata["updated_at"] = datetime.now().isoformat()
                update_data["metadatas"] = [metadata]
            if embedding is not None:
                update_data["embeddings"] = [embedding]
                
            update_data["ids"] = [document_id]
            
            # 执行更新
            collection.update(**update_data)
            
            logger.info(f"Updated document {document_id} in {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {str(e)}")
            return False
            
    def delete_documents(self, collection_name: str, document_ids: List[str] = None,
                        where: Dict[str, Any] = None) -> bool:
        """
        删除文档
        
        Args:
            collection_name: 集合名称
            document_ids: 要删除的文档ID列表
            where: 删除条件
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return False
                
            collection = self.collections[collection_name]
            
            if document_ids:
                collection.delete(ids=document_ids)
                logger.info(f"Deleted {len(document_ids)} documents from {collection_name}")
            elif where:
                collection.delete(where=where)
                logger.info(f"Deleted documents matching condition from {collection_name}")
            else:
                logger.error("Either document_ids or where must be provided")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {str(e)}")
            return False
            
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取集合信息
        
        Args:
            collection_name: 集合名称
            
        Returns:
            Dict[str, Any]: 集合信息
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return {}
                
            collection = self.collections[collection_name]
            
            # 获取集合统计信息
            count = collection.count()
            
            # 获取一些样本文档
            sample_results = collection.get(limit=min(5, count))
            
            info = {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata,
                "sample_documents": sample_results.get("documents", []),
                "sample_metadatas": sample_results.get("metadatas", [])
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_name}: {str(e)}")
            return {}
            
    def create_memory_collection(self, user_id: str = None) -> bool:
        """
        创建记忆集合
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否创建成功
        """
        try:
            collection_name = f"memories_{user_id}" if user_id else "memories_global"
            
            metadata = {
                "type": "memory",
                "user_id": user_id,
                "description": "存储用户记忆向量数据"
            }
            
            return self.create_collection(collection_name, metadata)
            
        except Exception as e:
            logger.error(f"Failed to create memory collection: {str(e)}")
            return False
            
    def create_knowledge_collection(self, domain: str = None) -> bool:
        """
        创建知识集合
        
        Args:
            domain: 知识领域
            
        Returns:
            bool: 是否创建成功
        """
        try:
            collection_name = f"knowledge_{domain}" if domain else "knowledge_general"
            
            metadata = {
                "type": "knowledge",
                "domain": domain,
                "description": "存储知识向量数据"
            }
            
            return self.create_collection(collection_name, metadata)
            
        except Exception as e:
            logger.error(f"Failed to create knowledge collection: {str(e)}")
            return False
            
    def backup_collection(self, collection_name: str, backup_path: str) -> bool:
        """
        备份集合数据
        
        Args:
            collection_name: 集合名称
            backup_path: 备份路径
            
        Returns:
            bool: 是否备份成功
        """
        try:
            if collection_name not in self.collections:
                logger.error(f"Collection {collection_name} not found")
                return False
                
            collection = self.collections[collection_name]
            
            # 获取所有数据
            all_data = collection.get()
            
            # 保存到文件
            backup_data = {
                "collection_name": collection_name,
                "metadata": collection.metadata,
                "documents": all_data.get("documents", []),
                "metadatas": all_data.get("metadatas", []),
                "embeddings": all_data.get("embeddings", []),
                "ids": all_data.get("ids", []),
                "backup_time": datetime.now().isoformat()
            }
            
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=self._json_serializer)
                
            logger.info(f"Backed up collection {collection_name} to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup collection {collection_name}: {str(e)}")
            return False
            
    def restore_collection(self, backup_path: str, new_collection_name: str = None) -> bool:
        """
        从备份恢复集合
        
        Args:
            backup_path: 备份文件路径
            new_collection_name: 新集合名称
            
        Returns:
            bool: 是否恢复成功
        """
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
                
            original_name = backup_data["collection_name"]
            collection_name = new_collection_name or original_name
            
            # 创建新集合
            metadata = backup_data.get("metadata", {})
            metadata["restored_from"] = original_name
            metadata["restore_time"] = datetime.now().isoformat()
            
            if not self.create_collection(collection_name, metadata):
                return False
                
            # 添加数据
            documents = backup_data.get("documents", [])
            metadatas = backup_data.get("metadatas", [])
            embeddings = backup_data.get("embeddings", [])
            ids = backup_data.get("ids", [])
            
            if embeddings:
                # 转换为numpy数组
                embeddings = [np.array(emb) for emb in embeddings]
                
            return self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings if embeddings else None
            )
            
        except Exception as e:
            logger.error(f"Failed to restore collection from {backup_path}: {str(e)}")
            return False
            
    def _json_serializer(self, obj):
        """JSON序列化辅助函数"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
    def close(self):
        """关闭连接"""
        try:
            if self.client:
                # Chroma客户端通常不需要显式关闭
                pass
            self.is_connected = False
            logger.info("Chroma integration closed")
        except Exception as e:
            logger.error(f"Error closing Chroma integration: {str(e)}")

