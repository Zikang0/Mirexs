"""
图分析器系统
提供图结构分析和度量计算功能
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
import numpy as np
from collections import defaultdict, Counter
import math

logger = logging.getLogger(__name__)

@dataclass
class GraphMetrics:
    """图度量数据类"""
    node_count: int
    edge_count: int
    density: float
    average_degree: float
    diameter: float
    average_path_length: float
    clustering_coefficient: float
    connected_components: int
    largest_component_size: int
    assortativity: float

@dataclass
class CommunityAnalysis:
    """社区分析数据类"""
    community_count: int
    community_sizes: List[int]
    modularity: float
    community_quality: float
    inter_community_edges: int
    intra_community_edges: int

class GraphAnalyzer:
    """图分析器"""
    
    def __init__(self, graph):
        self.graph = graph
        self.metrics_cache: Dict[str, Any] = {}
        
    def calculate_basic_metrics(self) -> GraphMetrics:
        """
        计算基本图度量
        
        Returns:
            GraphMetrics: 图度量
        """
        try:
            cache_key = "basic_metrics"
            if cache_key in self.metrics_cache:
                return self.metrics_cache[cache_key]
                
            node_count = len(self.graph.nodes())
            edge_count = len(self.graph.edges())
            
            # 计算密度
            if node_count > 1:
                max_edges = node_count * (node_count - 1)
                if hasattr(self.graph, 'is_directed') and self.graph.is_directed():
                    density = edge_count / max_edges
                else:
                    density = (2 * edge_count) / max_edges
            else:
                density = 0.0
                
            # 计算平均度
            if node_count > 0:
                degrees = [deg for _, deg in self.graph.degree()]
                average_degree = sum(degrees) / node_count
            else:
                average_degree = 0.0
                
            # 计算直径和平均路径长度
            diameter, avg_path_length = self._calculate_diameter_and_path_length()
            
            # 计算聚类系数
            clustering_coefficient = self._calculate_clustering_coefficient()
            
            # 计算连通分量
            connected_components, largest_component_size = self._calculate_connected_components()
            
            # 计算同配性
            assortativity = self._calculate_assortativity()
            
            metrics = GraphMetrics(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                average_degree=average_degree,
                diameter=diameter,
                average_path_length=avg_path_length,
                clustering_coefficient=clustering_coefficient,
                connected_components=connected_components,
                largest_component_size=largest_component_size,
                assortativity=assortativity
            )
            
            self.metrics_cache[cache_key] = metrics
            logger.info("Calculated basic graph metrics")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate basic metrics: {str(e)}")
            return GraphMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0.0)
            
    def analyze_communities(self, community_partition: Dict[str, int] = None) -> CommunityAnalysis:
        """
        分析社区结构
        
        Args:
            community_partition: 社区划分
            
        Returns:
            CommunityAnalysis: 社区分析结果
        """
        try:
            if community_partition is None:
                # 使用默认社区检测
                from .graph_traversal import GraphTraversal
                traversal = GraphTraversal(self.graph)
                community_partition = traversal.detect_communities("louvain")
                
            if not community_partition:
                return CommunityAnalysis(0, [], 0.0, 0.0, 0, 0)
                
            # 计算社区数量和各社区大小
            community_sizes = list(Counter(community_partition.values()).values())
            community_count = len(community_sizes)
            
            # 计算模块度
            modularity = self._calculate_modularity(community_partition)
            
            # 计算社区间和社区内边数
            inter_edges, intra_edges = self._count_inter_intra_edges(community_partition)
            
            # 计算社区质量
            community_quality = self._calculate_community_quality(community_partition, intra_edges, inter_edges)
            
            analysis = CommunityAnalysis(
                community_count=community_count,
                community_sizes=community_sizes,
                modularity=modularity,
                community_quality=community_quality,
                inter_community_edges=inter_edges,
                intra_community_edges=intra_edges
            )
            
            logger.info(f"Community analysis: {community_count} communities, modularity {modularity:.3f}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze communities: {str(e)}")
            return CommunityAnalysis(0, [], 0.0, 0.0, 0, 0)
            
    def detect_anomalies(self, method: str = "degree") -> List[Tuple[str, float]]:
        """
        检测异常节点
        
        Args:
            method: 检测方法 (degree, betweenness, clustering)
            
        Returns:
            List[Tuple[str, float]]: (节点ID, 异常分数) 列表
        """
        try:
            if method == "degree":
                return self._detect_degree_anomalies()
            elif method == "betweenness":
                return self._detect_betweenness_anomalies()
            elif method == "clustering":
                return self._detect_clustering_anomalies()
            else:
                logger.error(f"Unsupported anomaly detection method: {method}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {str(e)}")
            return []
            
    def analyze_network_evolution(self, previous_graph, time_interval: float = 1.0) -> Dict[str, Any]:
        """
        分析网络演化
        
        Args:
            previous_graph: 前一个时间点的图
            time_interval: 时间间隔
            
        Returns:
            Dict[str, Any]: 演化分析结果
        """
        try:
            current_metrics = self.calculate_basic_metrics()
            
            # 计算前一个图的度量
            previous_analyzer = GraphAnalyzer(previous_graph)
            previous_metrics = previous_analyzer.calculate_basic_metrics()
            
            # 计算变化率
            growth_rate = (current_metrics.node_count - previous_metrics.node_count) / time_interval
            edge_growth_rate = (current_metrics.edge_count - previous_metrics.edge_count) / time_interval
            
            # 计算稳定性指标
            stability = self._calculate_network_stability(previous_graph)
            
            evolution_analysis = {
                "growth_rate": growth_rate,
                "edge_growth_rate": edge_growth_rate,
                "stability": stability,
                "node_growth": current_metrics.node_count - previous_metrics.node_count,
                "edge_growth": current_metrics.edge_count - previous_metrics.edge_count,
                "density_change": current_metrics.density - previous_metrics.density,
                "average_degree_change": current_metrics.average_degree - previous_metrics.average_degree
            }
            
            logger.info(f"Network evolution analysis: growth rate {growth_rate:.2f} nodes/time unit")
            return evolution_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze network evolution: {str(e)}")
            return {}
            
    def find_structural_holes(self) -> List[Tuple[str, float]]:
        """
        查找结构洞
        
        Returns:
            List[Tuple[str, float]]: (节点ID, 结构洞分数) 列表
        """
        try:
            structural_holes = []
            
            for node in self.graph.nodes():
                # 计算节点的有效大小和约束系数
                effective_size = self._calculate_effective_size(node)
                constraint = self._calculate_constraint(node)
                
                # 结构洞分数（有效大小高且约束低）
                hole_score = effective_size * (1 - constraint)
                structural_holes.append((node, hole_score))
                
            # 按分数排序
            structural_holes.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"Found {len(structural_holes)} structural holes")
            return structural_holes
            
        except Exception as e:
            logger.error(f"Failed to find structural holes: {str(e)}")
            return []
            
    def _calculate_diameter_and_path_length(self) -> Tuple[float, float]:
        """计算直径和平均路径长度"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return 0.0, 0.0
                
            # 只计算最大连通分量
            if nx.is_connected(self.graph):
                diameter = nx.diameter(self.graph)
                avg_path_length = nx.average_shortest_path_length(self.graph)
            else:
                # 对于非连通图，计算最大连通分量的直径
                largest_cc = max(nx.connected_components(self.graph), key=len)
                subgraph = self.graph.subgraph(largest_cc)
                diameter = nx.diameter(subgraph)
                avg_path_length = nx.average_shortest_path_length(subgraph)
                
            return diameter, avg_path_length
            
        except Exception as e:
            logger.warning(f"Failed to calculate diameter and path length: {str(e)}")
            return 0.0, 0.0
            
    def _calculate_clustering_coefficient(self) -> float:
        """计算聚类系数"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return 0.0
                
            return nx.average_clustering(self.graph)
            
        except Exception as e:
            logger.warning(f"Failed to calculate clustering coefficient: {str(e)}")
            return 0.0
            
    def _calculate_connected_components(self) -> Tuple[int, int]:
        """计算连通分量"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return 0, 0
                
            components = list(nx.connected_components(self.graph))
            component_count = len(components)
            largest_component_size = max(len(comp) for comp in components) if components else 0
            
            return component_count, largest_component_size
            
        except Exception as e:
            logger.warning(f"Failed to calculate connected components: {str(e)}")
            return 0, 0
            
    def _calculate_assortativity(self) -> float:
        """计算同配性"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return 0.0
                
            return nx.degree_assortativity_coefficient(self.graph)
            
        except Exception as e:
            logger.warning(f"Failed to calculate assortativity: {str(e)}")
            return 0.0
            
    def _calculate_modularity(self, community_partition: Dict[str, int]) -> float:
        """计算模块度"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return 0.0
                
            return nx.algorithms.community.modularity(self.graph, 
                                                     [set(n for n, c in community_partition.items() if c == comm) 
                                                      for comm in set(community_partition.values())])
            
        except Exception as e:
            logger.warning(f"Failed to calculate modularity: {str(e)}")
            return 0.0
            
    def _count_inter_intra_edges(self, community_partition: Dict[str, int]) -> Tuple[int, int]:
        """计算社区间和社区内边数"""
        inter_edges = 0
        intra_edges = 0
        
        for edge in self.graph.edges():
            u, v = edge
            if community_partition.get(u) == community_partition.get(v):
                intra_edges += 1
            else:
                inter_edges += 1
                
        return inter_edges, intra_edges
        
    def _calculate_community_quality(self, community_partition: Dict[str, int], 
                                   intra_edges: int, inter_edges: int) -> float:
        """计算社区质量"""
        try:
            total_edges = intra_edges + inter_edges
            if total_edges == 0:
                return 0.0
                
            # 社区内边比例
            intra_ratio = intra_edges / total_edges
            
            # 社区大小平衡性
            community_sizes = list(Counter(community_partition.values()).values())
            size_std = np.std(community_sizes) if community_sizes else 0
            max_size = max(community_sizes) if community_sizes else 1
            balance_ratio = 1 - (size_std / max_size) if max_size > 0 else 1.0
            
            # 综合质量分数
            quality = 0.7 * intra_ratio + 0.3 * balance_ratio
            return quality
            
        except Exception as e:
            logger.warning(f"Failed to calculate community quality: {str(e)}")
            return 0.0
            
    def _detect_degree_anomalies(self) -> List[Tuple[str, float]]:
        """基于度的异常检测"""
        try:
            degrees = dict(self.graph.degree())
            if not degrees:
                return []
                
            degree_values = list(degrees.values())
            mean_degree = np.mean(degree_values)
            std_degree = np.std(degree_values)
            
            anomalies = []
            for node, degree in degrees.items():
                # 计算Z-score
                if std_degree > 0:
                    z_score = abs(degree - mean_degree) / std_degree
                else:
                    z_score = 0
                    
                # 高Z-score表示异常
                if z_score > 2.0:  # 2个标准差
                    anomalies.append((node, z_score))
                    
            anomalies.sort(key=lambda x: x[1], reverse=True)
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect degree anomalies: {str(e)}")
            return []
            
    def _detect_betweenness_anomalies(self) -> List[Tuple[str, float]]:
        """基于介数中心性的异常检测"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return []
                
            betweenness = nx.betweenness_centrality(self.graph)
            if not betweenness:
                return []
                
            betweenness_values = list(betweenness.values())
            mean_betweenness = np.mean(betweenness_values)
            std_betweenness = np.std(betweenness_values)
            
            anomalies = []
            for node, score in betweenness.items():
                # 计算Z-score
                if std_betweenness > 0:
                    z_score = abs(score - mean_betweenness) / std_betweenness
                else:
                    z_score = 0
                    
                # 高Z-score表示异常
                if z_score > 2.0:
                    anomalies.append((node, z_score))
                    
            anomalies.sort(key=lambda x: x[1], reverse=True)
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect betweenness anomalies: {str(e)}")
            return []
            
    def _detect_clustering_anomalies(self) -> List[Tuple[str, float]]:
        """基于聚类系数的异常检测"""
        try:
            import networkx as nx
            
            if not isinstance(self.graph, nx.Graph):
                return []
                
            clustering = nx.clustering(self.graph)
            if not clustering:
                return []
                
            clustering_values = list(clustering.values())
            mean_clustering = np.mean(clustering_values)
            std_clustering = np.std(clustering_values)
            
            anomalies = []
            for node, score in clustering.items():
                # 计算Z-score
                if std_clustering > 0:
                    z_score = abs(score - mean_clustering) / std_clustering
                else:
                    z_score = 0
                    
                # 高Z-score表示异常
                if z_score > 2.0:
                    anomalies.append((node, z_score))
                    
            anomalies.sort(key=lambda x: x[1], reverse=True)
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect clustering anomalies: {str(e)}")
            return []
            
    def _calculate_network_stability(self, previous_graph) -> float:
        """计算网络稳定性"""
        try:
            # 计算节点重叠度
            current_nodes = set(self.graph.nodes())
            previous_nodes = set(previous_graph.nodes())
            
            if not previous_nodes:
                return 1.0  # 如果没有前一个图，认为完全稳定
                
            node_overlap = len(current_nodes.intersection(previous_nodes)) / len(previous_nodes)
            
            # 计算边重叠度
            current_edges = set(self.graph.edges())
            previous_edges = set(previous_graph.edges())
            
            if not previous_edges:
                edge_overlap = 1.0
            else:
                edge_overlap = len(current_edges.intersection(previous_edges)) / len(previous_edges)
                
            # 综合稳定性分数
            stability = 0.6 * node_overlap + 0.4 * edge_overlap
            return stability
            
        except Exception as e:
            logger.warning(f"Failed to calculate network stability: {str(e)}")
            return 0.0
            
    def _calculate_effective_size(self, node: str) -> float:
        """计算节点的有效大小"""
        try:
            neighbors = set(self.graph.neighbors(node))
            if not neighbors:
                return 0.0
                
            # 计算冗余度
            redundancy = 0
            for neighbor in neighbors:
                # 邻居的其他连接（不包括当前节点）
                neighbor_neighbors = set(self.graph.neighbors(neighbor)) - {node}
                redundancy += len(neighbor_neighbors.intersection(neighbors))
                
            if len(neighbors) > 0:
                redundancy /= len(neighbors)
                
            effective_size = len(neighbors) - redundancy
            return max(0.0, effective_size)
            
        except Exception as e:
            logger.warning(f"Failed to calculate effective size for {node}: {str(e)}")
            return 0.0
            
    def _calculate_constraint(self, node: str) -> float:
        """计算节点的约束系数"""
        try:
            neighbors = set(self.graph.neighbors(node))
            if not neighbors:
                return 1.0  # 孤立节点的约束最大
                
            constraint = 0.0
            for neighbor in neighbors:
                # 计算p_{ij} - 节点i在节点j上的投资比例
                p_ij = 1.0 / len(neighbors)
                
                # 计算节点i和j的共同邻居
                common_neighbors = set(self.graph.neighbors(node)).intersection(set(self.graph.neighbors(neighbor)))
                
                # 计算约束项
                for common in common_neighbors:
                    if common != node and common != neighbor:
                        p_ik = 1.0 / len(neighbors)
                        p_jk = 1.0 / len(set(self.graph.neighbors(neighbor)))
                        constraint += p_ij * p_ik * p_jk
                        
            return constraint
            
        except Exception as e:
            logger.warning(f"Failed to calculate constraint for {node}: {str(e)}")
            return 1.0

