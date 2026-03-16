"""
Mirexs 向量数据库系统
提供完整的向量存储、索引和搜索功能
"""

from .memory_vectors import MemoryVectorStore, MemoryVector, MemoryQuery
from .knowledge_vectors import KnowledgeVectorStore, KnowledgeVector, KnowledgeRelation
from .chroma_integration import ChromaIntegration
from .faiss_integration import FAISSIntegration
from .vector_indexer import VectorIndexer, IndexConfig, IndexStats
from .similarity_search import SimilaritySearch, SearchQuery, SearchResult, SearchStrategy, RankingMethod

__all__ = [
    # 记忆向量存储
    'MemoryVectorStore',
    'MemoryVector', 
    'MemoryQuery',
    
    # 知识向量存储
    'KnowledgeVectorStore',
    'KnowledgeVector',
    'KnowledgeRelation',
    
    # 数据库集成
    'ChromaIntegration',
    'FAISSIntegration',
    
    # 索引管理
    'VectorIndexer',
    'IndexConfig', 
    'IndexStats',
    
    # 搜索功能
    'SimilaritySearch',
    'SearchQuery',
    'SearchResult',
    'SearchStrategy',
    'RankingMethod'
]

# 包版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Vector Database System for Mirexs AI Agent"

# 初始化日志配置
import logging

def setup_logging(level=logging.INFO):
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('vector_db.log')
        ]
    )

# 包初始化时自动设置日志
setup_logging()

logger = logging.getLogger(__name__)
logger.info(f"Mirexs Vector Database System v{__version__} initialized")

class MirexsVectorDB:
    """Mirexs向量数据库主类 - 提供统一的向量数据库功能接口"""
    
    def __init__(self, storage_path: str = "vector_storage"):
        self.storage_path = storage_path
        self.memory_store = MemoryVectorStore()
        self.knowledge_store = KnowledgeVectorStore()
        self.vector_indexer = VectorIndexer(f"{storage_path}/indices")
        self.similarity_search = SimilaritySearch(self.vector_indexer)
        self.chroma_integration = None
        self.faiss_indices = {}
        
    def initialize_chroma(self, host: str = None, port: int = None) -> bool:
        """
        初始化Chroma集成
        
        Args:
            host: Chroma服务器主机
            port: Chroma服务器端口
            
        Returns:
            bool: 是否初始化成功
        """
        try:
            self.chroma_integration = ChromaIntegration(
                persist_directory=f"{self.storage_path}/chroma",
                host=host,
                port=port
            )
            
            success = self.chroma_integration.connect()
            if success:
                logger.info("Chroma integration initialized successfully")
            else:
                logger.error("Failed to initialize Chroma integration")
                
            return success
            
        except Exception as e:
            logger.error(f"Error initializing Chroma integration: {str(e)}")
            return False
            
    def create_faiss_index(self, index_name: str, dimension: int = 768, 
                          index_type: str = "IVF") -> bool:
        """
        创建FAISS索引
        
        Args:
            index_name: 索引名称
            dimension: 向量维度
            index_type: 索引类型
            
        Returns:
            bool: 是否创建成功
        """
        try:
            config = IndexConfig(
                index_type="faiss",
                dimension=dimension,
                index_name=index_name,
                description=f"FAISS {index_type} index for vector storage",
                parameters={
                    "faiss_index_type": index_type,
                    "nlist": 100,
                    "nprobe": 10,
                    "metric": "l2"
                }
            )
            
            success = self.vector_indexer.create_index(config)
            if success:
                logger.info(f"FAISS index {index_name} created successfully")
            else:
                logger.error(f"Failed to create FAISS index {index_name}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error creating FAISS index {index_name}: {str(e)}")
            return False
            
    def add_memory_vector(self, user_id: str, memory_type: str, content: str,
                         embedding: np.ndarray, metadata: Dict[str, Any] = None) -> str:
        """
        添加记忆向量
        
        Args:
            user_id: 用户ID
            memory_type: 记忆类型
            content: 记忆内容
            embedding: 记忆向量
            metadata: 元数据
            
        Returns:
            str: 记忆ID
        """
        try:
            memory_id = self.memory_store.add_memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                embedding=embedding,
                metadata=metadata
            )
            
            if memory_id and self.chroma_integration:
                # 同时保存到Chroma
                chroma_metadata = {
                    "type": "memory",
                    "user_id": user_id,
                    "memory_type": memory_type,
                    "content": content,
                    **metadata
                }
                
                self.chroma_integration.add_documents(
                    collection_name=f"memories_{user_id}",
                    documents=[content],
                    metadatas=[chroma_metadata],
                    ids=[memory_id],
                    embeddings=[embedding]
                )
                
            return memory_id
            
        except Exception as e:
            logger.error(f"Error adding memory vector: {str(e)}")
            return None
            
    def search_similar_memories(self, user_id: str, query_embedding: np.ndarray,
                               max_results: int = 10) -> List[Tuple[MemoryVector, float]]:
        """
        搜索相似记忆
        
        Args:
            user_id: 用户ID
            query_embedding: 查询向量
            max_results: 最大结果数
            
        Returns:
            List[Tuple[MemoryVector, float]]: 记忆向量和相似度列表
        """
        try:
            query = MemoryQuery(
                query_embedding=query_embedding,
                memory_types=["episodic", "semantic"],
                time_range=None,
                importance_threshold=0.0,
                max_results=max_results,
                similarity_threshold=0.5
            )
            
            results = self.memory_store.search_memories(query)
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar memories: {str(e)}")
            return []
            
    def semantic_search(self, index_name: str, query_text: str, 
                       text_embedding_model: Any, max_results: int = 10) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            index_name: 索引名称
            query_text: 查询文本
            text_embedding_model: 文本嵌入模型
            max_results: 最大结果数
            
        Returns:
            List[SearchResult]: 搜索结果
        """
        try:
            search_query = SearchQuery(
                query_vectors=np.zeros((1, 768)),  # 占位符，会被替换
                strategy=SearchStrategy.APPROXIMATE,
                ranking_method=RankingMethod.HYBRID,
                filters={},
                max_results=max_results,
                similarity_threshold=0.0,
                ranking_weights={
                    "similarity": 0.7,
                    "recency": 0.2,
                    "importance": 0.1
                }
            )
            
            results = self.similarity_search.semantic_search(
                index_name=index_name,
                query_text=query_text,
                text_embedding_model=text_embedding_model,
                query=search_query
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {str(e)}")
            return []
            
    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            Dict[str, Any]: 系统统计信息
        """
        try:
            stats = {
                "memory_vectors": self.memory_store.get_user_memory_stats("global"),
                "knowledge_vectors": {
                    "total_entities": len(self.knowledge_store.entity_index),
                    "total_relations": len(self.knowledge_store.relations)
                },
                "vector_indices": self.vector_indexer.list_indices(),
                "search_performance": self.similarity_search.get_performance_report()
            }
            
            if self.chroma_integration:
                stats["chroma_status"] = "connected"
            else:
                stats["chroma_status"] = "disconnected"
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}")
            return {}
            
    def backup_system(self, backup_path: str) -> bool:
        """
        备份系统数据
        
        Args:
            backup_path: 备份路径
            
        Returns:
            bool: 是否备份成功
        """
        try:
            import os
            os.makedirs(backup_path, exist_ok=True)
            
            # 备份记忆向量
            memory_backup = f"{backup_path}/memory_vectors.json"
            self.memory_store.save_to_file(memory_backup)
            
            # 备份知识向量
            knowledge_backup = f"{backup_path}/knowledge_vectors.json"
            self.knowledge_store.save_to_file(knowledge_backup)
            
            # 备份索引配置
            indices_backup = f"{backup_path}/indices_config.json"
            indices_info = self.vector_indexer.list_indices()
            with open(indices_backup, 'w') as f:
                import json
                json.dump(indices_info, f, indent=2)
                
            logger.info(f"Vector database system backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up system: {str(e)}")
            return False
            
    def shutdown(self):
        """关闭向量数据库系统"""
        try:
            # 保存所有索引
            for index_name in self.vector_indexer.indices.keys():
                self.vector_indexer.save_index(index_name)
                
            # 关闭Chroma连接
            if self.chroma_integration:
                self.chroma_integration.close()
                
            logger.info("Vector database system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {str(e)}")

# 创建全局实例
vector_db = MirexsVectorDB()

# 便捷函数
def get_vector_db() -> MirexsVectorDB:
    """获取向量数据库实例"""
    return vector_db

def initialize_vector_db(storage_path: str = "vector_storage") -> MirexsVectorDB:
    """初始化向量数据库"""
    global vector_db
    vector_db = MirexsVectorDB(storage_path)
    return vector_db

# 模块导入完成
logger.info("Mirexs Vector Database package imported successfully")

