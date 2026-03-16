"""
Mirexs 图数据库系统
提供完整的图数据存储、查询和分析功能
"""

from .knowledge_graph import KnowledgeGraph, KnowledgeEntity, KnowledgeRelation
from .relationship_graph import RelationshipGraph, Relationship, RelationshipStrength
from .neo4j_integration import Neo4jIntegration, Neo4jConfig, Neo4jNode, Neo4jRelationship
from .graph_traversal import GraphTraversal, TraversalStrategy, TraversalDirection, TraversalResult, PathResult
from .graph_analyzer import GraphAnalyzer, GraphMetrics, CommunityAnalysis

__all__ = [
    # 知识图谱
    'KnowledgeGraph',
    'KnowledgeEntity',
    'KnowledgeRelation',
    
    # 关系图谱
    'RelationshipGraph', 
    'Relationship',
    'RelationshipStrength',
    
    # Neo4j集成
    'Neo4jIntegration',
    'Neo4jConfig',
    'Neo4jNode',
    'Neo4jRelationship',
    
    # 图遍历
    'GraphTraversal',
    'TraversalStrategy',
    'TraversalDirection', 
    'TraversalResult',
    'PathResult',
    
    # 图分析
    'GraphAnalyzer',
    'GraphMetrics',
    'CommunityAnalysis'
]

# 包版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Graph Database System for Mirexs AI Agent"

# 初始化日志配置
import logging

def setup_logging(level=logging.INFO):
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('graph_db.log')
        ]
    )

# 包初始化时自动设置日志
setup_logging()

logger = logging.getLogger(__name__)
logger.info(f"Mirexs Graph Database System v{__version__} initialized")

class MirexsGraphDB:
    """Mirexs图数据库主类 - 提供统一的图数据库功能接口"""
    
    def __init__(self, storage_path: str = "graph_storage"):
        self.storage_path = storage_path
        self.knowledge_graph = KnowledgeGraph()
        self.relationship_graph = RelationshipGraph()
        self.neo4j_integration = None
        self.graph_traversal = None
        self.graph_analyzer = None
        
    def initialize_neo4j(self, config: Neo4jConfig = None) -> bool:
        """
        初始化Neo4j集成
        
        Args:
            config: Neo4j配置
            
        Returns:
            bool: 是否初始化成功
        """
        try:
            self.neo4j_integration = Neo4jIntegration(config)
            success = self.neo4j_integration.connect()
            
            if success:
                logger.info("Neo4j integration initialized successfully")
            else:
                logger.error("Failed to initialize Neo4j integration")
                
            return success
            
        except Exception as e:
            logger.error(f"Error initializing Neo4j integration: {str(e)}")
            return False
            
    def create_knowledge_entity(self, name: str, entity_type: str, 
                               properties: dict = None) -> str:
        """
        创建知识实体
        
        Args:
            name: 实体名称
            entity_type: 实体类型
            properties: 实体属性
            
        Returns:
            str: 实体ID
        """
        try:
            entity_id = self.knowledge_graph.add_entity(
                name=name,
                entity_type=entity_type,
                properties=properties
            )
            
            # 同时同步到Neo4j
            if self.neo4j_integration and self.neo4j_integration.is_connected:
                neo4j_node_id = self.neo4j_integration.create_node(
                    labels=[entity_type],
                    properties={"name": name, **(properties or {})}
                )
                
            return entity_id
            
        except Exception as e:
            logger.error(f"Error creating knowledge entity: {str(e)}")
            return None
            
    def create_relationship(self, source_entity: str, target_entity: str,
                           relation_type: str, properties: dict = None) -> str:
        """
        创建关系
        
        Args:
            source_entity: 源实体ID
            target_entity: 目标实体ID
            relation_type: 关系类型
            properties: 关系属性
            
        Returns:
            str: 关系ID
        """
        try:
            # 在知识图谱中创建关系
            relation_id = self.knowledge_graph.add_relation(
                source_entity=source_entity,
                target_entity=target_entity,
                relation_type=relation_type,
                properties=properties
            )
            
            # 在关系图谱中创建关系
            strength = RelationshipStrength.MEDIUM
            self.relationship_graph.add_relationship(
                source_entity=source_entity,
                target_entity=target_entity,
                relationship_type=relation_type,
                strength=strength,
                properties=properties
            )
            
            # 同步到Neo4j
            if (self.neo4j_integration and self.neo4j_integration.is_connected and
                hasattr(self.knowledge_graph.entities[source_entity], 'id') and
                hasattr(self.knowledge_graph.entities[target_entity], 'id')):
                
                # 这里需要实际的Neo4j节点ID，简化实现
                pass
                
            return relation_id
            
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            return None
            
    def find_related_entities(self, entity_id: str, max_degree: int = 2) -> List[str]:
        """
        查找相关实体
        
        Args:
            entity_id: 实体ID
            max_degree: 最大度数
            
        Returns:
            List[str]: 相关实体ID列表
        """
        try:
            if not self.graph_traversal:
                self.graph_traversal = GraphTraversal(self.knowledge_graph.graph)
                
            related_entities = self.relationship_graph.find_related_entities(
                entity_id, max_degree
            )
            
            return related_entities
            
        except Exception as e:
            logger.error(f"Error finding related entities: {str(e)}")
            return []
            
    def analyze_graph_structure(self) -> GraphMetrics:
        """
        分析图结构
        
        Returns:
            GraphMetrics: 图度量
        """
        try:
            if not self.graph_analyzer:
                self.graph_analyzer = GraphAnalyzer(self.knowledge_graph.graph)
                
            metrics = self.graph_analyzer.calculate_basic_metrics()
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing graph structure: {str(e)}")
            return GraphMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0)
            
    def find_shortest_path(self, start_entity: str, end_entity: str) -> PathResult:
        """
        查找最短路径
        
        Args:
            start_entity: 起始实体
            end_entity: 目标实体
            
        Returns:
            PathResult: 路径结果
        """
        try:
            if not self.graph_traversal:
                self.graph_traversal = GraphTraversal(self.knowledge_graph.graph)
                
            path_result = self.graph_traversal.find_shortest_path(
                start_entity, end_entity
            )
            
            return path_result
            
        except Exception as e:
            logger.error(f"Error finding shortest path: {str(e)}")
            return PathResult([], float('inf'), 0, 0.0)
            
    def detect_communities(self) -> Dict[str, int]:
        """
        检测社区结构
        
        Returns:
            Dict[str, int]: 社区划分
        """
        try:
            if not self.graph_traversal:
                self.graph_traversal = GraphTraversal(self.knowledge_graph.graph)
                
            communities = self.graph_traversal.detect_communities()
            return communities
            
        except Exception as e:
            logger.error(f"Error detecting communities: {str(e)}")
            return {}
            
    def import_from_neo4j(self) -> bool:
        """
        从Neo4j导入数据
        
        Returns:
            bool: 是否导入成功
        """
        try:
            if not self.neo4j_integration or not self.neo4j_integration.is_connected:
                logger.error("Neo4j integration not available")
                return False
                
            imported_graph = self.neo4j_integration.export_to_knowledge_graph()
            if imported_graph:
                self.knowledge_graph = imported_graph
                logger.info("Successfully imported data from Neo4j")
                return True
            else:
                logger.error("Failed to import data from Neo4j")
                return False
                
        except Exception as e:
            logger.error(f"Error importing from Neo4j: {str(e)}")
            return False
            
    def export_to_neo4j(self) -> bool:
        """
        导出数据到Neo4j
        
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.neo4j_integration or not self.neo4j_integration.is_connected:
                logger.error("Neo4j integration not available")
                return False
                
            success = self.neo4j_integration.import_knowledge_graph(self.knowledge_graph)
            if success:
                logger.info("Successfully exported data to Neo4j")
            else:
                logger.error("Failed to export data to Neo4j")
                
            return success
            
        except Exception as e:
            logger.error(f"Error exporting to Neo4j: {str(e)}")
            return False
            
    def get_system_stats(self) -> Dict[str, Any]:
        """
        获取系统统计信息
        
        Returns:
            Dict[str, Any]: 系统统计
        """
        try:
            stats = {
                "knowledge_graph": {
                    "entities": len(self.knowledge_graph.entities),
                    "relations": len(self.knowledge_graph.relations)
                },
                "relationship_graph": {
                    "relationships": len(self.relationship_graph.relationships)
                },
                "neo4j_connected": self.neo4j_integration.is_connected if self.neo4j_integration else False
            }
            
            # 添加图分析统计
            if self.graph_analyzer:
                metrics = self.analyze_graph_structure()
                stats["graph_metrics"] = {
                    "node_count": metrics.node_count,
                    "edge_count": metrics.edge_count,
                    "density": metrics.density,
                    "connected_components": metrics.connected_components
                }
                
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
            
            # 备份知识图谱
            kg_backup = f"{backup_path}/knowledge_graph.json"
            self.knowledge_graph.save_to_file(kg_backup)
            
            # 备份关系图谱
            rg_backup = f"{backup_path}/relationship_graph.json"
            self.relationship_graph.save_to_file(rg_backup)
            
            logger.info(f"Graph database system backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up system: {str(e)}")
            return False
            
    def shutdown(self):
        """关闭图数据库系统"""
        try:
            if self.neo4j_integration:
                self.neo4j_integration.close()
                
            logger.info("Graph database system shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {str(e)}")

# 创建全局实例
graph_db = MirexsGraphDB()

# 便捷函数
def get_graph_db() -> MirexsGraphDB:
    """获取图数据库实例"""
    return graph_db

def initialize_graph_db(storage_path: str = "graph_storage") -> MirexsGraphDB:
    """初始化图数据库"""
    global graph_db
    graph_db = MirexsGraphDB(storage_path)
    return graph_db

# 模块导入完成
logger.info("Mirexs Graph Database package imported successfully")
