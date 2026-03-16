"""
知识图谱管理系统
负责知识图谱数据的存储、查询和推理
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime
import uuid
import networkx as nx

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeEntity:
    """知识实体数据类"""
    id: str
    name: str
    entity_type: str
    properties: Dict[str, Any]
    confidence: float
    created_time: datetime
    updated_time: datetime

@dataclass
class KnowledgeRelation:
    """知识关系数据类"""
    id: str
    source_entity: str
    target_entity: str
    relation_type: str
    properties: Dict[str, Any]
    confidence: float
    created_time: datetime

class KnowledgeGraph:
    """知识图谱管理器"""
    
    def __init__(self, graph_name: str = "default_knowledge_graph"):
        self.graph_name = graph_name
        self.entities: Dict[str, KnowledgeEntity] = {}
        self.relations: Dict[str, KnowledgeRelation] = {}
        self.entity_index: Dict[str, List[str]] = {}  # 类型 -> 实体ID列表
        self.relation_index: Dict[str, List[str]] = {}  # 关系类型 -> 关系ID列表
        self.graph = nx.MultiDiGraph()  # 使用NetworkX作为内存图结构
        
    def add_entity(self, name: str, entity_type: str, properties: Dict[str, Any] = None,
                  confidence: float = 1.0) -> str:
        """
        添加知识实体
        
        Args:
            name: 实体名称
            entity_type: 实体类型
            properties: 实体属性
            confidence: 置信度
            
        Returns:
            str: 实体ID
        """
        try:
            entity_id = str(uuid.uuid4())
            now = datetime.now()
            
            if properties is None:
                properties = {}
                
            entity = KnowledgeEntity(
                id=entity_id,
                name=name,
                entity_type=entity_type,
                properties=properties,
                confidence=confidence,
                created_time=now,
                updated_time=now
            )
            
            # 存储实体
            self.entities[entity_id] = entity
            
            # 更新索引
            if entity_type not in self.entity_index:
                self.entity_index[entity_type] = []
            self.entity_index[entity_type].append(entity_id)
            
            # 添加到图结构
            self.graph.add_node(entity_id, 
                              name=name,
                              type=entity_type,
                              properties=properties,
                              confidence=confidence)
            
            logger.info(f"Added entity: {name} ({entity_type}) with ID {entity_id}")
            return entity_id
            
        except Exception as e:
            logger.error(f"Failed to add entity {name}: {str(e)}")
            return None
            
    def add_relation(self, source_entity: str, target_entity: str, relation_type: str,
                    properties: Dict[str, Any] = None, confidence: float = 1.0) -> str:
        """
        添加知识关系
        
        Args:
            source_entity: 源实体ID
            target_entity: 目标实体ID
            relation_type: 关系类型
            properties: 关系属性
            confidence: 置信度
            
        Returns:
            str: 关系ID
        """
        try:
            # 检查实体是否存在
            if source_entity not in self.entities or target_entity not in self.entities:
                logger.error("Source or target entity not found")
                return None
                
            relation_id = str(uuid.uuid4())
            now = datetime.now()
            
            if properties is None:
                properties = {}
                
            relation = KnowledgeRelation(
                id=relation_id,
                source_entity=source_entity,
                target_entity=target_entity,
                relation_type=relation_type,
                properties=properties,
                confidence=confidence,
                created_time=now
            )
            
            # 存储关系
            self.relations[relation_id] = relation
            
            # 更新索引
            if relation_type not in self.relation_index:
                self.relation_index[relation_type] = []
            self.relation_index[relation_type].append(relation_id)
            
            # 添加到图结构
            self.graph.add_edge(source_entity, target_entity, key=relation_id,
                              relation_type=relation_type,
                              properties=properties,
                              confidence=confidence)
            
            logger.info(f"Added relation: {relation_type} between {source_entity} and {target_entity}")
            return relation_id
            
        except Exception as e:
            logger.error(f"Failed to add relation: {str(e)}")
            return None
            
    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]:
        """获取实体"""
        return self.entities.get(entity_id)
        
    def get_relation(self, relation_id: str) -> Optional[KnowledgeRelation]:
        """获取关系"""
        return self.relations.get(relation_id)
        
    def find_entities_by_type(self, entity_type: str) -> List[KnowledgeEntity]:
        """根据类型查找实体"""
        entity_ids = self.entity_index.get(entity_type, [])
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
        
    def find_relations_by_type(self, relation_type: str) -> List[KnowledgeRelation]:
        """根据类型查找关系"""
        relation_ids = self.relation_index.get(relation_type, [])
        return [self.relations[rid] for rid in relation_ids if rid in self.relations]
        
    def get_entity_relations(self, entity_id: str, direction: str = "both") -> List[KnowledgeRelation]:
        """
        获取实体的关系
        
        Args:
            entity_id: 实体ID
            direction: 关系方向 (in, out, both)
            
        Returns:
            List[KnowledgeRelation]: 关系列表
        """
        try:
            relations = []
            
            if direction in ["out", "both"]:
                # 出边关系
                out_edges = self.graph.out_edges(entity_id, keys=True, data=True)
                for source, target, key, data in out_edges:
                    if key in self.relations:
                        relations.append(self.relations[key])
                        
            if direction in ["in", "both"]:
                # 入边关系
                in_edges = self.graph.in_edges(entity_id, keys=True, data=True)
                for source, target, key, data in in_edges:
                    if key in self.relations:
                        relations.append(self.relations[key])
                        
            return relations
            
        except Exception as e:
            logger.error(f"Failed to get entity relations: {str(e)}")
            return []
            
    def infer_relations(self, entity_id: str, max_depth: int = 2) -> List[Tuple[str, List[str]]]:
        """
        推理实体关系
        
        Args:
            entity_id: 实体ID
            max_depth: 最大推理深度
            
        Returns:
            List[Tuple[str, List[str]]]: (目标实体ID, 路径) 列表
        """
        try:
            if entity_id not in self.graph:
                return []
                
            inferred_relations = []
            visited = set()
            
            def dfs(current_entity: str, path: List[str], depth: int):
                if depth > max_depth or current_entity in visited:
                    return
                    
                visited.add(current_entity)
                
                # 获取所有出边
                for _, target, key, data in self.graph.out_edges(current_entity, keys=True, data=True):
                    if key in self.relations:
                        new_path = path + [key]
                        inferred_relations.append((target, new_path))
                        dfs(target, new_path, depth + 1)
                        
            dfs(entity_id, [], 0)
            return inferred_relations
            
        except Exception as e:
            logger.error(f"Failed to infer relations: {str(e)}")
            return []
            
    def search_entities(self, query: str, entity_types: List[str] = None) -> List[KnowledgeEntity]:
        """
        搜索实体
        
        Args:
            query: 搜索查询
            entity_types: 实体类型过滤
            
        Returns:
            List[KnowledgeEntity]: 匹配的实体列表
        """
        try:
            results = []
            query_lower = query.lower()
            
            for entity in self.entities.values():
                # 过滤类型
                if entity_types and entity.entity_type not in entity_types:
                    continue
                    
                # 搜索名称和属性
                if query_lower in entity.name.lower():
                    results.append(entity)
                    continue
                    
                # 搜索属性值
                for prop_value in entity.properties.values():
                    if isinstance(prop_value, str) and query_lower in prop_value.lower():
                        results.append(entity)
                        break
                        
            return results
            
        except Exception as e:
            logger.error(f"Failed to search entities: {str(e)}")
            return []
            
    def get_subgraph(self, center_entity: str, radius: int = 2) -> 'KnowledgeGraph':
        """
        获取子图
        
        Args:
            center_entity: 中心实体
            radius: 子图半径
            
        Returns:
            KnowledgeGraph: 子图实例
        """
        try:
            if center_entity not in self.graph:
                logger.error(f"Center entity {center_entity} not found")
                return None
                
            # 使用NetworkX的ego_graph获取子图
            ego_graph = nx.ego_graph(self.graph, center_entity, radius=radius, undirected=True)
            
            # 创建新的知识图谱实例
            subgraph = KnowledgeGraph(f"subgraph_of_{self.graph_name}")
            
            # 添加节点
            for node_id in ego_graph.nodes():
                if node_id in self.entities:
                    entity = self.entities[node_id]
                    subgraph.entities[node_id] = entity
                    
                    # 更新索引
                    if entity.entity_type not in subgraph.entity_index:
                        subgraph.entity_index[entity.entity_type] = []
                    subgraph.entity_index[entity.entity_type].append(node_id)
                    
            # 添加边
            for source, target, key, data in ego_graph.edges(keys=True, data=True):
                if key in self.relations:
                    relation = self.relations[key]
                    subgraph.relations[key] = relation
                    
                    # 更新索引
                    if relation.relation_type not in subgraph.relation_index:
                        subgraph.relation_index[relation.relation_type] = []
                    subgraph.relation_index[relation.relation_type].append(key)
                    
            # 复制图结构
            subgraph.graph = ego_graph.copy()
            
            logger.info(f"Created subgraph with {len(subgraph.entities)} entities and {len(subgraph.relations)} relations")
            return subgraph
            
        except Exception as e:
            logger.error(f"Failed to create subgraph: {str(e)}")
            return None
            
    def calculate_centrality(self) -> Dict[str, float]:
        """
        计算实体中心性
        
        Returns:
            Dict[str, float]: 实体ID -> 中心性分数
        """
        try:
            # 使用度中心性
            degree_centrality = nx.degree_centrality(self.graph)
            return degree_centrality
            
        except Exception as e:
            logger.error(f"Failed to calculate centrality: {str(e)}")
            return {}
            
    def save_to_file(self, file_path: str) -> bool:
        """保存知识图谱到文件"""
        try:
            save_data = {
                "graph_name": self.graph_name,
                "entities": {
                    eid: {
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "properties": entity.properties,
                        "confidence": entity.confidence,
                        "created_time": entity.created_time.isoformat(),
                        "updated_time": entity.updated_time.isoformat()
                    }
                    for eid, entity in self.entities.items()
                },
                "relations": {
                    rid: {
                        "source_entity": relation.source_entity,
                        "target_entity": relation.target_entity,
                        "relation_type": relation.relation_type,
                        "properties": relation.properties,
                        "confidence": relation.confidence,
                        "created_time": relation.created_time.isoformat()
                    }
                    for rid, relation in self.relations.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            logger.info(f"Saved knowledge graph to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {str(e)}")
            return False
            
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载知识图谱"""
        try:
            with open(file_path, 'r') as f:
                save_data = json.load(f)
                
            self.graph_name = save_data["graph_name"]
            self.entities.clear()
            self.relations.clear()
            self.entity_index.clear()
            self.relation_index.clear()
            self.graph.clear()
            
            # 加载实体
            for eid, entity_data in save_data["entities"].items():
                entity = KnowledgeEntity(
                    id=eid,
                    name=entity_data["name"],
                    entity_type=entity_data["entity_type"],
                    properties=entity_data["properties"],
                    confidence=entity_data["confidence"],
                    created_time=datetime.fromisoformat(entity_data["created_time"]),
                    updated_time=datetime.fromisoformat(entity_data["updated_time"])
                )
                self.entities[eid] = entity
                
                # 重建索引
                if entity.entity_type not in self.entity_index:
                    self.entity_index[entity.entity_type] = []
                self.entity_index[entity.entity_type].append(eid)
                
                # 重建图节点
                self.graph.add_node(eid, 
                                  name=entity.name,
                                  type=entity.entity_type,
                                  properties=entity.properties,
                                  confidence=entity.confidence)
                
            # 加载关系
            for rid, relation_data in save_data["relations"].items():
                relation = KnowledgeRelation(
                    id=rid,
                    source_entity=relation_data["source_entity"],
                    target_entity=relation_data["target_entity"],
                    relation_type=relation_data["relation_type"],
                    properties=relation_data["properties"],
                    confidence=relation_data["confidence"],
                    created_time=datetime.fromisoformat(relation_data["created_time"])
                )
                self.relations[rid] = relation
                
                # 重建索引
                if relation.relation_type not in self.relation_index:
                    self.relation_index[relation.relation_type] = []
                self.relation_index[relation.relation_type].append(rid)
                
                # 重建图边
                self.graph.add_edge(relation.source_entity, relation.target_entity, key=rid,
                                  relation_type=relation.relation_type,
                                  properties=relation.properties,
                                  confidence=relation.confidence)
                
            logger.info(f"Loaded knowledge graph from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load knowledge graph: {str(e)}")
            return False

