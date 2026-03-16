"""
Neo4j图数据库集成
提供与Neo4j图数据库的完整集成功能
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import uuid
import json

logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase, basic_auth
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("Neo4j driver not available. Install with: pip install neo4j")
    NEO4J_AVAILABLE = False

@dataclass
class Neo4jConfig:
    """Neo4j配置数据类"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"
    encrypted: bool = False
    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 100

@dataclass
class Neo4jNode:
    """Neo4j节点数据类"""
    node_id: int
    labels: List[str]
    properties: Dict[str, Any]

@dataclass
class Neo4jRelationship:
    """Neo4j关系数据类"""
    relationship_id: int
    start_node: int
    end_node: int
    type: str
    properties: Dict[str, Any]

class Neo4jIntegration:
    """Neo4j图数据库集成类"""
    
    def __init__(self, config: Neo4jConfig = None):
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j driver not available. Install with: pip install neo4j")
            
        self.config = config or Neo4jConfig()
        self.driver = None
        self.is_connected = False
        
    def connect(self) -> bool:
        """
        连接到Neo4j数据库
        
        Returns:
            bool: 是否连接成功
        """
        try:
            self.driver = GraphDatabase.driver(
                self.config.uri,
                auth=basic_auth(self.config.username, self.config.password),
                encrypted=self.config.encrypted,
                max_connection_lifetime=self.config.max_connection_lifetime,
                max_connection_pool_size=self.config.max_connection_pool_size
            )
            
            # 测试连接
            with self.driver.session(database=self.config.database) as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                
                if test_value == 1:
                    self.is_connected = True
                    logger.info(f"Connected to Neo4j at {self.config.uri}")
                    return True
                else:
                    logger.error("Neo4j connection test failed")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            self.is_connected = False
            return False
            
    def create_node(self, labels: List[str], properties: Dict[str, Any] = None) -> Optional[int]:
        """
        创建节点
        
        Args:
            labels: 节点标签
            properties: 节点属性
            
        Returns:
            Optional[int]: 节点ID
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return None
                
            if properties is None:
                properties = {}
                
            # 添加创建时间戳
            properties["created_at"] = datetime.now().isoformat()
            properties["mirexs_id"] = str(uuid.uuid4())
            
            with self.driver.session(database=self.config.database) as session:
                # 构建标签字符串
                labels_str = ":".join(labels)
                
                # 构建属性字符串
                props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
                
                query = f"CREATE (n:{labels_str} {{{props_str}}}) RETURN id(n) as node_id"
                result = session.run(query, **properties)
                
                node_id = result.single()["node_id"]
                logger.info(f"Created node with ID {node_id} and labels {labels}")
                return node_id
                
        except Exception as e:
            logger.error(f"Failed to create node: {str(e)}")
            return None
            
    def create_relationship(self, start_node_id: int, end_node_id: int, 
                          relationship_type: str, properties: Dict[str, Any] = None) -> Optional[int]:
        """
        创建关系
        
        Args:
            start_node_id: 起始节点ID
            end_node_id: 结束节点ID
            relationship_type: 关系类型
            properties: 关系属性
            
        Returns:
            Optional[int]: 关系ID
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return None
                
            if properties is None:
                properties = {}
                
            # 添加创建时间戳
            properties["created_at"] = datetime.now().isoformat()
            properties["mirexs_id"] = str(uuid.uuid4())
            
            with self.driver.session(database=self.config.database) as session:
                # 构建属性字符串
                props_str = ", ".join([f"{k}: ${k}" for k in properties.keys()])
                
                query = f"""
                MATCH (a), (b) 
                WHERE id(a) = $start_id AND id(b) = $end_id
                CREATE (a)-[r:{relationship_type} {{{props_str}}}]->(b)
                RETURN id(r) as rel_id
                """
                
                params = {"start_id": start_node_id, "end_id": end_node_id, **properties}
                result = session.run(query, **params)
                
                rel_id = result.single()["rel_id"]
                logger.info(f"Created relationship with ID {rel_id} and type {relationship_type}")
                return rel_id
                
        except Exception as e:
            logger.error(f"Failed to create relationship: {str(e)}")
            return None
            
    def get_node(self, node_id: int) -> Optional[Neo4jNode]:
        """
        获取节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            Optional[Neo4jNode]: 节点对象
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return None
                
            with self.driver.session(database=self.config.database) as session:
                query = "MATCH (n) WHERE id(n) = $node_id RETURN n"
                result = session.run(query, node_id=node_id)
                record = result.single()
                
                if record:
                    node = record["n"]
                    return Neo4jNode(
                        node_id=node_id,
                        labels=list(node.labels),
                        properties=dict(node)
                    )
                else:
                    logger.warning(f"Node with ID {node_id} not found")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {str(e)}")
            return None
            
    def get_relationship(self, relationship_id: int) -> Optional[Neo4jRelationship]:
        """
        获取关系
        
        Args:
            relationship_id: 关系ID
            
        Returns:
            Optional[Neo4jRelationship]: 关系对象
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return None
                
            with self.driver.session(database=self.config.database) as session:
                query = "MATCH ()-[r]-() WHERE id(r) = $rel_id RETURN r, startNode(r) as start, endNode(r) as end"
                result = session.run(query, rel_id=relationship_id)
                record = result.single()
                
                if record:
                    rel = record["r"]
                    start_node = record["start"]
                    end_node = record["end"]
                    
                    return Neo4jRelationship(
                        relationship_id=relationship_id,
                        start_node=start_node.id,
                        end_node=end_node.id,
                        type=rel.type,
                        properties=dict(rel)
                    )
                else:
                    logger.warning(f"Relationship with ID {relationship_id} not found")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get relationship {relationship_id}: {str(e)}")
            return None
            
    def update_node_properties(self, node_id: int, properties: Dict[str, Any]) -> bool:
        """
        更新节点属性
        
        Args:
            node_id: 节点ID
            properties: 新属性
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            # 添加更新时间戳
            properties["updated_at"] = datetime.now().isoformat()
            
            with self.driver.session(database=self.config.database) as session:
                # 构建属性设置字符串
                set_clauses = ", ".join([f"n.{k} = ${k}" for k in properties.keys()])
                
                query = f"""
                MATCH (n) 
                WHERE id(n) = $node_id
                SET {set_clauses}
                """
                
                params = {"node_id": node_id, **properties}
                session.run(query, **params)
                
                logger.info(f"Updated properties for node {node_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update node properties: {str(e)}")
            return False
            
    def update_relationship_properties(self, relationship_id: int, properties: Dict[str, Any]) -> bool:
        """
        更新关系属性
        
        Args:
            relationship_id: 关系ID
            properties: 新属性
            
        Returns:
            bool: 是否更新成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            # 添加更新时间戳
            properties["updated_at"] = datetime.now().isoformat()
            
            with self.driver.session(database=self.config.database) as session:
                # 构建属性设置字符串
                set_clauses = ", ".join([f"r.{k} = ${k}" for k in properties.keys()])
                
                query = f"""
                MATCH ()-[r]-() 
                WHERE id(r) = $rel_id
                SET {set_clauses}
                """
                
                params = {"rel_id": relationship_id, **properties}
                session.run(query, **params)
                
                logger.info(f"Updated properties for relationship {relationship_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update relationship properties: {str(e)}")
            return False
            
    def delete_node(self, node_id: int) -> bool:
        """
        删除节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            with self.driver.session(database=self.config.database) as session:
                # 先删除所有关系，再删除节点
                query = """
                MATCH (n) 
                WHERE id(n) = $node_id
                DETACH DELETE n
                """
                
                result = session.run(query, node_id=node_id)
                summary = result.consume()
                
                if summary.counters.nodes_deleted > 0:
                    logger.info(f"Deleted node {node_id}")
                    return True
                else:
                    logger.warning(f"Node {node_id} not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete node {node_id}: {str(e)}")
            return False
            
    def delete_relationship(self, relationship_id: int) -> bool:
        """
        删除关系
        
        Args:
            relationship_id: 关系ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            with self.driver.session(database=self.config.database) as session:
                query = """
                MATCH ()-[r]-() 
                WHERE id(r) = $rel_id
                DELETE r
                """
                
                result = session.run(query, rel_id=relationship_id)
                summary = result.consume()
                
                if summary.counters.relationships_deleted > 0:
                    logger.info(f"Deleted relationship {relationship_id}")
                    return True
                else:
                    logger.warning(f"Relationship {relationship_id} not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete relationship {relationship_id}: {str(e)}")
            return False
            
    def execute_cypher_query(self, cypher_query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        Args:
            cypher_query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return []
                
            if parameters is None:
                parameters = {}
                
            with self.driver.session(database=self.config.database) as session:
                result = session.run(cypher_query, **parameters)
                records = []
                
                for record in result:
                    # 将记录转换为字典
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        
                        # 处理节点和关系对象
                        if hasattr(value, 'id'):
                            if hasattr(value, 'labels'):  # 节点
                                record_dict[key] = {
                                    "id": value.id,
                                    "labels": list(value.labels),
                                    "properties": dict(value)
                                }
                            elif hasattr(value, 'type'):  # 关系
                                record_dict[key] = {
                                    "id": value.id,
                                    "type": value.type,
                                    "properties": dict(value)
                                }
                        else:
                            record_dict[key] = value
                            
                    records.append(record_dict)
                    
                logger.info(f"Executed Cypher query, returned {len(records)} records")
                return records
                
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {str(e)}")
            return []
            
    def import_knowledge_graph(self, knowledge_graph) -> bool:
        """
        从知识图谱导入数据到Neo4j
        
        Args:
            knowledge_graph: 知识图谱对象
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            # 导入实体
            entity_mapping = {}  # 实体ID -> Neo4j节点ID映射
            for entity_id, entity in knowledge_graph.entities.items():
                node_id = self.create_node(
                    labels=[entity.entity_type],
                    properties={
                        "name": entity.name,
                        "confidence": entity.confidence,
                        **entity.properties
                    }
                )
                
                if node_id:
                    entity_mapping[entity_id] = node_id
                    
            # 导入关系
            for relation_id, relation in knowledge_graph.relations.items():
                if (relation.source_entity in entity_mapping and 
                    relation.target_entity in entity_mapping):
                    
                    self.create_relationship(
                        start_node_id=entity_mapping[relation.source_entity],
                        end_node_id=entity_mapping[relation.target_entity],
                        relationship_type=relation.relation_type,
                        properties={
                            "confidence": relation.confidence,
                            **relation.properties
                        }
                    )
                    
            logger.info(f"Imported knowledge graph with {len(entity_mapping)} entities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import knowledge graph: {str(e)}")
            return False
            
    def export_to_knowledge_graph(self) -> Any:
        """
        从Neo4j导出数据到知识图谱
        
        Returns:
            Any: 知识图谱对象
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return None
                
            # 这里需要导入KnowledgeGraph类
            from .knowledge_graph import KnowledgeGraph
            
            kg = KnowledgeGraph("exported_from_neo4j")
            
            # 获取所有节点
            nodes_query = "MATCH (n) RETURN n, id(n) as node_id"
            nodes_result = self.execute_cypher_query(nodes_query)
            
            node_mapping = {}  # Neo4j节点ID -> 实体ID映射
            
            for record in nodes_result:
                node_data = record["n"]
                neo4j_node_id = record["node_id"]
                
                # 创建实体
                entity_id = kg.add_entity(
                    name=node_data["properties"].get("name", f"Node_{neo4j_node_id}"),
                    entity_type=node_data["labels"][0] if node_data["labels"] else "Unknown",
                    properties=node_data["properties"],
                    confidence=node_data["properties"].get("confidence", 1.0)
                )
                
                if entity_id:
                    node_mapping[neo4j_node_id] = entity_id
                    
            # 获取所有关系
            rels_query = "MATCH (a)-[r]->(b) RETURN r, id(r) as rel_id, id(a) as start_id, id(b) as end_id"
            rels_result = self.execute_cypher_query(rels_query)
            
            for record in rels_result:
                rel_data = record["r"]
                start_id = record["start_id"]
                end_id = record["end_id"]
                
                if start_id in node_mapping and end_id in node_mapping:
                    kg.add_relation(
                        source_entity=node_mapping[start_id],
                        target_entity=node_mapping[end_id],
                        relation_type=rel_data["type"],
                        properties=rel_data["properties"],
                        confidence=rel_data["properties"].get("confidence", 1.0)
                    )
                    
            logger.info(f"Exported knowledge graph with {len(kg.entities)} entities and {len(kg.relations)} relations")
            return kg
            
        except Exception as e:
            logger.error(f"Failed to export to knowledge graph: {str(e)}")
            return None
            
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return {}
                
            stats_query = """
            CALL db.labels() YIELD label
            RETURN collect(label) as labels
            UNION ALL
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN collect(relationshipType) as relationshipTypes
            UNION ALL
            MATCH (n) RETURN count(n) as nodeCount
            UNION ALL
            MATCH ()-[r]-() RETURN count(r) as relationshipCount
            """
            
            results = self.execute_cypher_query(stats_query)
            
            stats = {}
            for result in results:
                if "labels" in result:
                    stats["labels"] = result["labels"]
                elif "relationshipTypes" in result:
                    stats["relationship_types"] = result["relationshipTypes"]
                elif "nodeCount" in result:
                    stats["node_count"] = result["nodeCount"]
                elif "relationshipCount" in result:
                    stats["relationship_count"] = result["relationshipCount"]
                    
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}
            
    def create_index(self, label: str, property_name: str) -> bool:
        """
        创建索引
        
        Args:
            label: 节点标签
            property_name: 属性名
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            query = f"CREATE INDEX IF NOT EXISTS FOR (n:{label}) ON (n.{property_name})"
            self.execute_cypher_query(query)
            
            logger.info(f"Created index on {label}.{property_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            return False
            
    def create_constraint(self, label: str, property_name: str) -> bool:
        """
        创建约束
        
        Args:
            label: 节点标签
            property_name: 属性名
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if not self.is_connected:
                logger.error("Not connected to Neo4j")
                return False
                
            query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE"
            self.execute_cypher_query(query)
            
            logger.info(f"Created constraint on {label}.{property_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create constraint: {str(e)}")
            return False
            
    def close(self):
        """关闭连接"""
        try:
            if self.driver:
                self.driver.close()
                self.is_connected = False
                logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {str(e)}")

