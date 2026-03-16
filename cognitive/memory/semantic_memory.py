"""
语义记忆模块：存储概念和知识
实现基于知识图谱的语义记忆系统
"""

import uuid
import json
import datetime
from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
from py2neo import Graph, Node, Relationship, NodeMatcher
import logging

class SemanticMemory:
    """语义记忆系统 - 存储概念和知识"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.graph = None
        self.initialized = False
        
        # 概念类型定义
        self.concept_types = {
            "entity", "category", "property", "relation", "event", "skill"
        }
        
        self._initialize_graph_database()
    
    def _initialize_graph_database(self):
        """初始化图数据库连接"""
        try:
            # 连接Neo4j数据库
            self.graph = Graph(
                self.config.get("neo4j_uri", "bolt://localhost:7687"),
                auth=(
                    self.config.get("neo4j_user", "neo4j"),
                    self.config.get("neo4j_password", "password")
                )
            )
            
            # 创建约束确保概念唯一性
            self._create_constraints()
            self.initialized = True
            self.logger.info("语义记忆图数据库初始化成功")
            
        except Exception as e:
            self.logger.error(f"语义记忆图数据库初始化失败: {e}")
            # 回退到内存图
            self.graph = nx.MultiDiGraph()
            self.initialized = True
            self.logger.info("使用内存图作为语义记忆存储")
    
    def _create_constraints(self):
        """创建数据库约束"""
        try:
            # 确保概念名称唯一
            self.graph.run("CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE")
            self.graph.run("CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE")
        except Exception as e:
            self.logger.warning(f"创建约束失败: {e}")
    
    def store_concept(self, 
                     name: str,
                     concept_type: str = "entity",
                     properties: Dict[str, Any] = None,
                     description: str = None,
                     confidence: float = 1.0) -> str:
        """
        存储概念到语义记忆
        
        Args:
            name: 概念名称
            concept_type: 概念类型
            properties: 概念属性
            description: 概念描述
            confidence: 置信度
            
        Returns:
            概念ID
        """
        if not self.initialized:
            raise RuntimeError("语义记忆系统未初始化")
        
        concept_id = str(uuid.uuid4())
        properties = properties or {}
        
        concept_data = {
            "id": concept_id,
            "name": name,
            "type": concept_type if concept_type in self.concept_types else "entity",
            "description": description or "",
            "confidence": float(confidence),
            "created_at": datetime.datetime.now().isoformat(),
            "access_count": 0,
            **properties
        }
        
        try:
            if isinstance(self.graph, Graph):
                # Neo4j存储
                concept_node = Node("Concept", **concept_data)
                self.graph.create(concept_node)
            else:
                # 内存图存储
                self.graph.add_node(concept_id, **concept_data)
            
            self.logger.info(f"语义概念存储成功: {name} ({concept_id})")
            return concept_id
            
        except Exception as e:
            self.logger.error(f"语义概念存储失败: {e}")
            raise
    
    def create_relationship(self,
                          source_concept: str,
                          target_concept: str,
                          relation_type: str,
                          properties: Dict[str, Any] = None,
                          confidence: float = 1.0) -> bool:
        """
        创建概念间的关系
        
        Args:
            source_concept: 源概念ID或名称
            target_concept: 目标概念ID或名称
            relation_type: 关系类型
            properties: 关系属性
            confidence: 置信度
            
        Returns:
            是否成功
        """
        if not self.initialized:
            return False
        
        properties = properties or {}
        relation_data = {
            "type": relation_type,
            "confidence": float(confidence),
            "created_at": datetime.datetime.now().isoformat(),
            **properties
        }
        
        try:
            if isinstance(self.graph, Graph):
                # Neo4j关系创建
                matcher = NodeMatcher(self.graph)
                source_node = self._find_concept_node(source_concept, matcher)
                target_node = self._find_concept_node(target_concept, matcher)
                
                if source_node and target_node:
                    relation = Relationship(source_node, relation_type, target_node, **relation_data)
                    self.graph.create(relation)
                    return True
                return False
            else:
                # 内存图关系创建
                source_id = self._find_concept_id(source_concept)
                target_id = self._find_concept_id(target_concept)
                
                if source_id and target_id:
                    self.graph.add_edge(source_id, target_id, **relation_data)
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"创建关系失败: {e}")
            return False
    
    def _find_concept_node(self, concept_identifier: str, matcher: NodeMatcher) -> Optional[Node]:
        """查找概念节点"""
        # 先按ID查找
        node = matcher.match("Concept", id=concept_identifier).first()
        if node:
            return node
        
        # 按名称查找
        node = matcher.match("Concept", name=concept_identifier).first()
        return node
    
    def _find_concept_id(self, concept_identifier: str) -> Optional[str]:
        """在内存图中查找概念ID"""
        for node_id, data in self.graph.nodes(data=True):
            if data.get('id') == concept_identifier or data.get('name') == concept_identifier:
                return node_id
        return None
    
    def query_concepts(self,
                      query: str = None,
                      concept_type: str = None,
                      properties: Dict[str, Any] = None,
                      limit: int = 20) -> List[Dict[str, Any]]:
        """
        查询概念
        
        Args:
            query: 查询文本（名称或描述匹配）
            concept_type: 概念类型过滤
            properties: 属性过滤
            limit: 返回数量限制
            
        Returns:
            概念列表
        """
        if not self.initialized:
            return []
        
        try:
            if isinstance(self.graph, Graph):
                # Neo4j查询
                cypher_query = "MATCH (c:Concept) WHERE 1=1"
                params = {}
                
                if query:
                    cypher_query += " AND (c.name CONTAINS $query OR c.description CONTAINS $query)"
                    params["query"] = query
                
                if concept_type:
                    cypher_query += " AND c.type = $concept_type"
                    params["concept_type"] = concept_type
                
                if properties:
                    for key, value in properties.items():
                        param_name = f"prop_{key}"
                        cypher_query += f" AND c.`{key}` = ${param_name}"
                        params[param_name] = value
                
                cypher_query += f" RETURN c LIMIT {limit}"
                
                results = self.graph.run(cypher_query, **params).data()
                concepts = [dict(result['c']) for result in results]
                
            else:
                # 内存图查询
                concepts = []
                for node_id, data in self.graph.nodes(data=True):
                    if self._matches_query(data, query, concept_type, properties):
                        concepts.append(data)
                    if len(concepts) >= limit:
                        break
            
            # 更新访问统计
            for concept in concepts:
                self._update_concept_access(concept['id'])
            
            return concepts
            
        except Exception as e:
            self.logger.error(f"概念查询失败: {e}")
            return []
    
    def _matches_query(self, 
                      concept_data: Dict[str, Any],
                      query: str = None,
                      concept_type: str = None,
                      properties: Dict[str, Any] = None) -> bool:
        """检查概念是否匹配查询条件"""
        if query and query not in concept_data.get('name', '') and query not in concept_data.get('description', ''):
            return False
        
        if concept_type and concept_data.get('type') != concept_type:
            return False
        
        if properties:
            for key, value in properties.items():
                if concept_data.get(key) != value:
                    return False
        
        return True
    
    def get_related_concepts(self,
                           concept_identifier: str,
                           relation_types: List[str] = None,
                           direction: str = "both",
                           depth: int = 1) -> List[Tuple[Dict, str, Dict]]:
        """
        获取相关概念
        
        Args:
            concept_identifier: 概念标识符
            relation_types: 关系类型过滤
            direction: 关系方向 (outgoing, incoming, both)
            depth: 查询深度
            
        Returns:
            (概念, 关系类型, 关系属性) 元组列表
        """
        if not self.initialized:
            return []
        
        try:
            if isinstance(self.graph, Graph):
                # Neo4j相关概念查询
                cypher_query = f"MATCH (start:Concept) WHERE start.id = $id OR start.name = $id"
                
                if direction == "outgoing":
                    cypher_query += " MATCH (start)-[r]->(related:Concept)"
                elif direction == "incoming":
                    cypher_query += " MATCH (start)<-[r]-(related:Concept)"
                else:  # both
                    cypher_query += " MATCH (start)-[r]-(related:Concept)"
                
                if relation_types:
                    types_str = "|".join([f"`{rt}`" for rt in relation_types])
                    cypher_query += f" WHERE type(r) IN [{types_str}]"
                
                cypher_query += " RETURN related, type(r) as relation_type, r"
                
                results = self.graph.run(cypher_query, id=concept_identifier).data()
                related = [(dict(result['related']), result['relation_type'], dict(result['r'])) 
                          for result in results]
                
            else:
                # 内存图相关概念查询
                concept_id = self._find_concept_id(concept_identifier)
                if not concept_id:
                    return []
                
                related = []
                if direction in ["outgoing", "both"]:
                    for target_id, edge_data in self.graph[concept_id].items():
                        for relation_type, rel_data in edge_data.items():
                            if not relation_types or relation_type in relation_types:
                                target_data = self.graph.nodes[target_id]
                                related.append((target_data, relation_type, rel_data))
                
                if direction in ["incoming", "both"]:
                    for source_id, targets in self.graph.pred[concept_id].items():
                        for target_id, edge_data in targets.items():
                            for relation_type, rel_data in edge_data.items():
                                if not relation_types or relation_type in relation_types:
                                    source_data = self.graph.nodes[source_id]
                                    related.append((source_data, relation_type, rel_data))
            
            # 更新访问统计
            self._update_concept_access(concept_identifier)
            
            return related
            
        except Exception as e:
            self.logger.error(f"获取相关概念失败: {e}")
            return []
    
    def _update_concept_access(self, concept_identifier: str):
        """更新概念访问统计"""
        try:
            if isinstance(self.graph, Graph):
                cypher_query = """
                MATCH (c:Concept) 
                WHERE c.id = $id OR c.name = $id
                SET c.access_count = COALESCE(c.access_count, 0) + 1,
                    c.last_accessed = $timestamp
                """
                self.graph.run(cypher_query, 
                             id=concept_identifier,
                             timestamp=datetime.datetime.now().isoformat())
            else:
                concept_id = self._find_concept_id(concept_identifier)
                if concept_id and concept_id in self.graph.nodes:
                    self.graph.nodes[concept_id]['access_count'] = \
                        self.graph.nodes[concept_id].get('access_count', 0) + 1
                    self.graph.nodes[concept_id]['last_accessed'] = \
                        datetime.datetime.now().isoformat()
                        
        except Exception as e:
            self.logger.warning(f"更新概念访问统计失败: {e}")
    
    def infer_relationships(self, concept1: str, concept2: str) -> List[Tuple[str, float]]:
        """
        推断概念间可能的关系
        
        Args:
            concept1: 概念1标识符
            concept2: 概念2标识符
            
        Returns:
            (关系类型, 置信度) 元组列表
        """
        if not self.initialized:
            return []
        
        try:
            # 获取两个概念的属性
            concept1_data = self.query_concepts(concept1)
            concept2_data = self.query_concepts(concept2)
            
            if not concept1_data or not concept2_data:
                return []
            
            concept1_data = concept1_data[0]
            concept2_data = concept2_data[0]
            
            inferred_relations = []
            
            # 基于类型推断
            type1 = concept1_data.get('type')
            type2 = concept2_data.get('type')
            
            if type1 == "category" and type2 == "entity":
                inferred_relations.append(("instance_of", 0.8))
            elif type1 == "entity" and type2 == "category":
                inferred_relations.append(("has_instance", 0.8))
            elif type1 == "property" and type2 == "entity":
                inferred_relations.append(("has_property", 0.7))
            
            # 基于名称相似性推断
            name1 = concept1_data.get('name', '').lower()
            name2 = concept2_data.get('name', '').lower()
            
            if any(word in name2 for word in name1.split()):
                inferred_relations.append(("related_to", 0.6))
            elif any(word in name1 for word in name2.split()):
                inferred_relations.append(("related_to", 0.6))
            
            return inferred_relations
            
        except Exception as e:
            self.logger.error(f"关系推断失败: {e}")
            return []
    
    def get_semantic_network_stats(self) -> Dict[str, Any]:
        """获取语义网络统计信息"""
        if not self.initialized:
            return {"error": "系统未初始化"}
        
        try:
            if isinstance(self.graph, Graph):
                # Neo4j统计
                node_count = self.graph.run("MATCH (n:Concept) RETURN COUNT(n) as count").data()[0]['count']
                relation_count = self.graph.run("MATCH ()-[r]->() RETURN COUNT(r) as count").data()[0]['count']
                
                type_distribution = self.graph.run("""
                    MATCH (c:Concept) 
                    RETURN c.type as type, COUNT(c) as count
                    ORDER BY count DESC
                """).data()
                
            else:
                # 内存图统计
                node_count = self.graph.number_of_nodes()
                relation_count = self.graph.number_of_edges()
                
                type_distribution = {}
                for _, data in self.graph.nodes(data=True):
                    node_type = data.get('type', 'unknown')
                    type_distribution[node_type] = type_distribution.get(node_type, 0) + 1
                type_distribution = [{"type": k, "count": v} for k, v in type_distribution.items()]
            
            return {
                "total_concepts": node_count,
                "total_relationships": relation_count,
                "concept_type_distribution": type_distribution,
                "density": relation_count / (node_count * (node_count - 1)) if node_count > 1 else 0
            }
            
        except Exception as e:
            self.logger.error(f"获取语义网络统计失败: {e}")
            return {"error": str(e)}

