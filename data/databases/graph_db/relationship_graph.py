"""
关系图谱管理系统
专门处理实体间复杂关系的存储和分析
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime
import uuid
import networkx as nx
from enum import Enum

logger = logging.getLogger(__name__)

class RelationshipStrength(Enum):
    """关系强度枚举"""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class Relationship:
    """关系数据类"""
    id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    strength: RelationshipStrength
    properties: Dict[str, Any]
    weight: float
    created_time: datetime
    last_accessed: datetime
    access_count: int

class RelationshipGraph:
    """关系图谱管理器"""
    
    def __init__(self, graph_name: str = "default_relationship_graph"):
        self.graph_name = graph_name
        self.relationships: Dict[str, Relationship] = {}
        self.relationship_index: Dict[str, List[str]] = {}  # 关系类型 -> 关系ID列表
        self.strength_index: Dict[RelationshipStrength, List[str]] = {}  # 强度 -> 关系ID列表
        self.graph = nx.Graph()  # 使用无向图表示关系
        
    def add_relationship(self, source_entity: str, target_entity: str, 
                        relationship_type: str, strength: RelationshipStrength = RelationshipStrength.MEDIUM,
                        properties: Dict[str, Any] = None, weight: float = 1.0) -> str:
        """
        添加关系
        
        Args:
            source_entity: 源实体
            target_entity: 目标实体
            relationship_type: 关系类型
            strength: 关系强度
            properties: 关系属性
            weight: 关系权重
            
        Returns:
            str: 关系ID
        """
        try:
            relationship_id = str(uuid.uuid4())
            now = datetime.now()
            
            if properties is None:
                properties = {}
                
            relationship = Relationship(
                id=relationship_id,
                source_entity=source_entity,
                target_entity=target_entity,
                relationship_type=relationship_type,
                strength=strength,
                properties=properties,
                weight=weight,
                created_time=now,
                last_accessed=now,
                access_count=0
            )
            
            # 存储关系
            self.relationships[relationship_id] = relationship
            
            # 更新索引
            if relationship_type not in self.relationship_index:
                self.relationship_index[relationship_type] = []
            self.relationship_index[relationship_type].append(relationship_id)
            
            if strength not in self.strength_index:
                self.strength_index[strength] = []
            self.strength_index[strength].append(relationship_id)
            
            # 添加到图结构
            self.graph.add_edge(source_entity, target_entity, 
                              relationship_id=relationship_id,
                              relationship_type=relationship_type,
                              strength=strength,
                              weight=weight,
                              properties=properties)
            
            logger.info(f"Added relationship: {relationship_type} between {source_entity} and {target_entity}")
            return relationship_id
            
        except Exception as e:
            logger.error(f"Failed to add relationship: {str(e)}")
            return None
            
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """获取关系"""
        if relationship_id in self.relationships:
            # 更新访问统计
            relationship = self.relationships[relationship_id]
            relationship.access_count += 1
            relationship.last_accessed = datetime.now()
            return relationship
        return None
        
    def find_relationships_by_type(self, relationship_type: str) -> List[Relationship]:
        """根据类型查找关系"""
        relationship_ids = self.relationship_index.get(relationship_type, [])
        return [self.relationships[rid] for rid in relationship_ids if rid in self.relationships]
        
    def find_relationships_by_strength(self, strength: RelationshipStrength) -> List[Relationship]:
        """根据强度查找关系"""
        relationship_ids = self.strength_index.get(strength, [])
        return [self.relationships[rid] for rid in relationship_ids if rid in self.relationships]
        
    def get_entity_relationships(self, entity_id: str) -> List[Relationship]:
        """
        获取实体的所有关系
        
        Args:
            entity_id: 实体ID
            
        Returns:
            List[Relationship]: 关系列表
        """
        try:
            relationships = []
            
            if entity_id in self.graph:
                # 获取所有相邻边
                edges = self.graph.edges(entity_id, data=True)
                for source, target, data in edges:
                    relationship_id = data.get('relationship_id')
                    if relationship_id and relationship_id in self.relationships:
                        relationships.append(self.relationships[relationship_id])
                        
            return relationships
            
        except Exception as e:
            logger.error(f"Failed to get entity relationships: {str(e)}")
            return []
            
    def calculate_relationship_strength(self, entity1: str, entity2: str, 
                                      relationship_type: str) -> RelationshipStrength:
        """
        计算关系强度
        
        Args:
            entity1: 实体1
            entity2: 实体2
            relationship_type: 关系类型
            
        Returns:
            RelationshipStrength: 关系强度
        """
        try:
            # 基于多种因素计算关系强度
            strength_factors = []
            
            # 1. 交互频率
            interaction_count = self._get_interaction_count(entity1, entity2)
            if interaction_count > 100:
                strength_factors.append(3)
            elif interaction_count > 50:
                strength_factors.append(2)
            elif interaction_count > 10:
                strength_factors.append(1)
            else:
                strength_factors.append(0)
                
            # 2. 关系权重
            relationship_weight = self._get_relationship_weight(entity1, entity2, relationship_type)
            strength_factors.append(int(relationship_weight * 2))
            
            # 3. 时间因素（最近交互）
            recency_score = self._get_recency_score(entity1, entity2)
            strength_factors.append(recency_score)
            
            # 计算总分
            total_score = sum(strength_factors)
            
            if total_score >= 5:
                return RelationshipStrength.VERY_STRONG
            elif total_score >= 3:
                return RelationshipStrength.STRONG
            elif total_score >= 1:
                return RelationshipStrength.MEDIUM
            else:
                return RelationshipStrength.WEAK
                
        except Exception as e:
            logger.error(f"Failed to calculate relationship strength: {str(e)}")
            return RelationshipStrength.WEAK
            
    def find_related_entities(self, entity_id: str, max_degree: int = 2, 
                            min_strength: RelationshipStrength = RelationshipStrength.WEAK) -> List[str]:
        """
        查找相关实体
        
        Args:
            entity_id: 实体ID
            max_degree: 最大度数
            min_strength: 最小关系强度
            
        Returns:
            List[str]: 相关实体ID列表
        """
        try:
            if entity_id not in self.graph:
                return []
                
            related_entities = set()
            visited = set([entity_id])
            
            def traverse(current_entity: str, degree: int):
                if degree > max_degree:
                    return
                    
                # 获取相邻实体
                neighbors = list(self.graph.neighbors(current_entity))
                for neighbor in neighbors:
                    if neighbor not in visited:
                        # 检查关系强度
                        edge_data = self.graph.get_edge_data(current_entity, neighbor)
                        if edge_data:
                            strength = edge_data.get('strength', RelationshipStrength.WEAK)
                            if self._strength_meets_minimum(strength, min_strength):
                                related_entities.add(neighbor)
                                visited.add(neighbor)
                                traverse(neighbor, degree + 1)
                                
            traverse(entity_id, 0)
            return list(related_entities)
            
        except Exception as e:
            logger.error(f"Failed to find related entities: {str(e)}")
            return []
            
    def detect_communities(self) -> List[List[str]]:
        """
        检测社区结构
        
        Returns:
            List[List[str]]: 社区列表，每个社区是实体ID列表
        """
        try:
            # 使用Louvain算法检测社区
            import community as community_louvain  # python-louvain包
            
            if len(self.graph.nodes) == 0:
                return []
                
            partition = community_louvain.best_partition(self.graph)
            
            # 将分区结果转换为社区列表
            communities_dict = {}
            for node, community_id in partition.items():
                if community_id not in communities_dict:
                    communities_dict[community_id] = []
                communities_dict[community_id].append(node)
                
            communities = list(communities_dict.values())
            
            logger.info(f"Detected {len(communities)} communities")
            return communities
            
        except ImportError:
            logger.warning("python-louvain package not available, using simple connected components")
            # 回退到连通组件
            return [list(component) for component in nx.connected_components(self.graph)]
        except Exception as e:
            logger.error(f"Failed to detect communities: {str(e)}")
            return []
            
    def calculate_centrality_measures(self) -> Dict[str, Dict[str, float]]:
        """
        计算中心性指标
        
        Returns:
            Dict[str, Dict[str, float]]: 实体ID -> 中心性指标映射
        """
        try:
            centrality_measures = {}
            
            # 度中心性
            degree_centrality = nx.degree_centrality(self.graph)
            
            # 接近中心性
            closeness_centrality = nx.closeness_centrality(self.graph)
            
            # 介数中心性
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            
            # 特征向量中心性
            try:
                eigenvector_centrality = nx.eigenvector_centrality(self.graph, max_iter=1000)
            except:
                eigenvector_centrality = {node: 0.0 for node in self.graph.nodes()}
                
            for node in self.graph.nodes():
                centrality_measures[node] = {
                    'degree': degree_centrality.get(node, 0.0),
                    'closeness': closeness_centrality.get(node, 0.0),
                    'betweenness': betweenness_centrality.get(node, 0.0),
                    'eigenvector': eigenvector_centrality.get(node, 0.0)
                }
                
            return centrality_measures
            
        except Exception as e:
            logger.error(f"Failed to calculate centrality measures: {str(e)}")
            return {}
            
    def find_influential_entities(self, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        查找有影响力的实体
        
        Args:
            top_k: 返回前K个实体
            
        Returns:
            List[Tuple[str, float]]: (实体ID, 影响力分数) 列表
        """
        try:
            centrality_measures = self.calculate_centrality_measures()
            
            # 计算综合影响力分数
            influential_scores = []
            for entity_id, measures in centrality_measures.items():
                # 加权综合分数
                composite_score = (
                    measures['degree'] * 0.3 +
                    measures['closeness'] * 0.25 +
                    measures['betweenness'] * 0.25 +
                    measures['eigenvector'] * 0.2
                )
                influential_scores.append((entity_id, composite_score))
                
            # 按分数排序
            influential_scores.sort(key=lambda x: x[1], reverse=True)
            return influential_scores[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find influential entities: {str(e)}")
            return []
            
    def _get_interaction_count(self, entity1: str, entity2: str) -> int:
        """获取交互次数"""
        try:
            relationships = self.get_entity_relationships(entity1)
            count = 0
            for rel in relationships:
                if (rel.source_entity == entity2 or rel.target_entity == entity2):
                    count += rel.access_count
            return count
        except:
            return 0
            
    def _get_relationship_weight(self, entity1: str, entity2: str, relationship_type: str) -> float:
        """获取关系权重"""
        try:
            if self.graph.has_edge(entity1, entity2):
                edge_data = self.graph.get_edge_data(entity1, entity2)
                if edge_data and edge_data.get('relationship_type') == relationship_type:
                    return edge_data.get('weight', 1.0)
            return 1.0
        except:
            return 1.0
            
    def _get_recency_score(self, entity1: str, entity2: str) -> int:
        """获取最近性分数"""
        try:
            relationships = self.get_entity_relationships(entity1)
            recent_interaction = False
            for rel in relationships:
                if (rel.source_entity == entity2 or rel.target_entity == entity2):
                    # 检查是否在最近30天内有交互
                    days_since_access = (datetime.now() - rel.last_accessed).days
                    if days_since_access <= 30:
                        recent_interaction = True
                        break
            return 1 if recent_interaction else 0
        except:
            return 0
            
    def _strength_meets_minimum(self, current_strength: RelationshipStrength, 
                               min_strength: RelationshipStrength) -> bool:
        """检查关系强度是否满足最小值"""
        strength_order = {
            RelationshipStrength.WEAK: 0,
            RelationshipStrength.MEDIUM: 1,
            RelationshipStrength.STRONG: 2,
            RelationshipStrength.VERY_STRONG: 3
        }
        return strength_order[current_strength] >= strength_order[min_strength]
        
    def save_to_file(self, file_path: str) -> bool:
        """保存关系图谱到文件"""
        try:
            save_data = {
                "graph_name": self.graph_name,
                "relationships": {
                    rid: {
                        "source_entity": rel.source_entity,
                        "target_entity": rel.target_entity,
                        "relationship_type": rel.relationship_type,
                        "strength": rel.strength.value,
                        "properties": rel.properties,
                        "weight": rel.weight,
                        "created_time": rel.created_time.isoformat(),
                        "last_accessed": rel.last_accessed.isoformat(),
                        "access_count": rel.access_count
                    }
                    for rid, rel in self.relationships.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            logger.info(f"Saved relationship graph to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save relationship graph: {str(e)}")
            return False
            
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载关系图谱"""
        try:
            with open(file_path, 'r') as f:
                save_data = json.load(f)
                
            self.graph_name = save_data["graph_name"]
            self.relationships.clear()
            self.relationship_index.clear()
            self.strength_index.clear()
            self.graph.clear()
            
            # 加载关系
            for rid, rel_data in save_data["relationships"].items():
                relationship = Relationship(
                    id=rid,
                    source_entity=rel_data["source_entity"],
                    target_entity=rel_data["target_entity"],
                    relationship_type=rel_data["relationship_type"],
                    strength=RelationshipStrength(rel_data["strength"]),
                    properties=rel_data["properties"],
                    weight=rel_data["weight"],
                    created_time=datetime.fromisoformat(rel_data["created_time"]),
                    last_accessed=datetime.fromisoformat(rel_data["last_accessed"]),
                    access_count=rel_data["access_count"]
                )
                self.relationships[rid] = relationship
                
                # 重建索引
                if relationship.relationship_type not in self.relationship_index:
                    self.relationship_index[relationship.relationship_type] = []
                self.relationship_index[relationship.relationship_type].append(rid)
                
                if relationship.strength not in self.strength_index:
                    self.strength_index[relationship.strength] = []
                self.strength_index[relationship.strength].append(rid)
                
                # 重建图边
                self.graph.add_edge(relationship.source_entity, relationship.target_entity,
                                  relationship_id=rid,
                                  relationship_type=relationship.relationship_type,
                                  strength=relationship.strength,
                                  weight=relationship.weight,
                                  properties=relationship.properties)
                
            logger.info(f"Loaded relationship graph from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load relationship graph: {str(e)}")
            return False

