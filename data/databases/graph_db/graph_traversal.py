"""
图遍历算法系统
提供多种图遍历算法和路径查找功能
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass
from enum import Enum
import heapq
import numpy as np
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class TraversalStrategy(Enum):
    """遍历策略枚举"""
    BFS = "breadth_first"  # 广度优先搜索
    DFS = "depth_first"    # 深度优先搜索
    DIJKSTRA = "dijkstra"  # 迪杰斯特拉算法
    A_STAR = "a_star"      # A*算法

class TraversalDirection(Enum):
    """遍历方向枚举"""
    OUTGOING = "outgoing"  # 出边方向
    INCOMING = "incoming"  # 入边方向
    BOTH = "both"          # 双向

@dataclass
class TraversalResult:
    """遍历结果数据类"""
    visited_nodes: List[str]
    traversal_order: List[str]
    depth_map: Dict[str, int]
    parent_map: Dict[str, str]

@dataclass
class PathResult:
    """路径结果数据类"""
    path: List[str]
    total_cost: float
    visited_nodes: int
    execution_time: float

class GraphTraversal:
    """图遍历算法管理器"""
    
    def __init__(self, graph):
        self.graph = graph
        self.traversal_cache: Dict[str, TraversalResult] = {}
        
    def traverse(self, start_node: str, strategy: TraversalStrategy = TraversalStrategy.BFS,
                direction: TraversalDirection = TraversalDirection.OUTGOING,
                max_depth: int = None, node_filter: Callable = None) -> TraversalResult:
        """
        执行图遍历
        
        Args:
            start_node: 起始节点
            strategy: 遍历策略
            direction: 遍历方向
            max_depth: 最大深度
            node_filter: 节点过滤函数
            
        Returns:
            TraversalResult: 遍历结果
        """
        try:
            if start_node not in self.graph:
                logger.error(f"Start node {start_node} not found in graph")
                return TraversalResult([], [], {}, {})
                
            cache_key = f"{start_node}_{strategy.value}_{direction.value}_{max_depth}"
            if cache_key in self.traversal_cache:
                logger.debug(f"Using cached traversal result for {cache_key}")
                return self.traversal_cache[cache_key]
                
            if strategy == TraversalStrategy.BFS:
                result = self._bfs_traversal(start_node, direction, max_depth, node_filter)
            elif strategy == TraversalStrategy.DFS:
                result = self._dfs_traversal(start_node, direction, max_depth, node_filter)
            elif strategy == TraversalStrategy.DIJKSTRA:
                result = self._dijkstra_traversal(start_node, direction, max_depth, node_filter)
            elif strategy == TraversalStrategy.A_STAR:
                result = self._a_star_traversal(start_node, direction, max_depth, node_filter)
            else:
                logger.error(f"Unsupported traversal strategy: {strategy}")
                return TraversalResult([], [], {}, {})
                
            # 缓存结果
            self.traversal_cache[cache_key] = result
            logger.info(f"Traversal completed: {strategy.value} from {start_node}, visited {len(result.visited_nodes)} nodes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to perform traversal: {str(e)}")
            return TraversalResult([], [], {}, {})
            
    def find_shortest_path(self, start_node: str, end_node: str, 
                          cost_function: Callable = None,
                          direction: TraversalDirection = TraversalDirection.OUTGOING) -> PathResult:
        """
        查找最短路径
        
        Args:
            start_node: 起始节点
            end_node: 目标节点
            cost_function: 成本函数
            direction: 遍历方向
            
        Returns:
            PathResult: 路径结果
        """
        try:
            import time
            start_time = time.time()
            
            if start_node not in self.graph or end_node not in self.graph:
                logger.error("Start or end node not found in graph")
                return PathResult([], float('inf'), 0, 0.0)
                
            # 默认成本函数（边权重）
            if cost_function is None:
                cost_function = self._default_cost_function
                
            # 使用Dijkstra算法查找最短路径
            distances = {start_node: 0}
            previous = {}
            visited = set()
            priority_queue = [(0, start_node)]
            
            visited_count = 0
            
            while priority_queue:
                current_distance, current_node = heapq.heappop(priority_queue)
                
                if current_node in visited:
                    continue
                    
                visited.add(current_node)
                visited_count += 1
                
                # 如果到达目标节点
                if current_node == end_node:
                    break
                    
                # 探索邻居节点
                neighbors = self._get_neighbors(current_node, direction)
                for neighbor, edge_data in neighbors:
                    if neighbor in visited:
                        continue
                        
                    # 计算新的距离
                    cost = cost_function(current_node, neighbor, edge_data)
                    new_distance = current_distance + cost
                    
                    if new_distance < distances.get(neighbor, float('inf')):
                        distances[neighbor] = new_distance
                        previous[neighbor] = current_node
                        heapq.heappush(priority_queue, (new_distance, neighbor))
                        
            # 重建路径
            path = []
            current = end_node
            while current in previous:
                path.insert(0, current)
                current = previous[current]
                
            if path:
                path.insert(0, start_node)
                total_cost = distances.get(end_node, float('inf'))
            else:
                total_cost = float('inf')
                
            execution_time = time.time() - start_time
            
            result = PathResult(path, total_cost, visited_count, execution_time)
            logger.info(f"Shortest path found: {len(path)} nodes, cost {total_cost:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to find shortest path: {str(e)}")
            return PathResult([], float('inf'), 0, 0.0)
            
    def find_all_paths(self, start_node: str, end_node: str, 
                      max_paths: int = 10, max_depth: int = 10,
                      direction: TraversalDirection = TraversalDirection.OUTGOING) -> List[PathResult]:
        """
        查找所有路径
        
        Args:
            start_node: 起始节点
            end_node: 目标节点
            max_paths: 最大路径数
            max_depth: 最大深度
            direction: 遍历方向
            
        Returns:
            List[PathResult]: 路径结果列表
        """
        try:
            import time
            start_time = time.time()
            
            if start_node not in self.graph or end_node not in self.graph:
                logger.error("Start or end node not found in graph")
                return []
                
            all_paths = []
            visited_count = 0
            
            def dfs_find_paths(current_node: str, current_path: List[str], current_depth: int):
                nonlocal visited_count
                visited_count += 1
                
                if current_depth > max_depth:
                    return
                    
                if current_node == end_node:
                    # 找到一条路径
                    path_cost = self._calculate_path_cost(current_path)
                    all_paths.append(PathResult(
                        path=current_path.copy(),
                        total_cost=path_cost,
                        visited_nodes=visited_count,
                        execution_time=0.0  # 最后统一计算
                    ))
                    return
                    
                # 探索邻居节点
                neighbors = self._get_neighbors(current_node, direction)
                for neighbor, edge_data in neighbors:
                    if neighbor not in current_path:  # 避免循环
                        current_path.append(neighbor)
                        dfs_find_paths(neighbor, current_path, current_depth + 1)
                        current_path.pop()
                        
                        # 限制路径数量
                        if len(all_paths) >= max_paths:
                            return
                            
            # 执行DFS查找所有路径
            dfs_find_paths(start_node, [start_node], 0)
            
            # 计算执行时间
            execution_time = time.time() - start_time
            for path_result in all_paths:
                path_result.execution_time = execution_time
                
            # 按成本排序
            all_paths.sort(key=lambda x: x.total_cost)
            
            logger.info(f"Found {len(all_paths)} paths from {start_node} to {end_node}")
            return all_paths
            
        except Exception as e:
            logger.error(f"Failed to find all paths: {str(e)}")
            return []
            
    def find_central_nodes(self, metric: str = "betweenness", top_k: int = 10) -> List[Tuple[str, float]]:
        """
        查找中心节点
        
        Args:
            metric: 中心性指标 (betweenness, closeness, degree, eigenvector)
            top_k: 返回前K个节点
            
        Returns:
            List[Tuple[str, float]]: (节点ID, 中心性分数) 列表
        """
        try:
            if metric == "betweenness":
                centrality = self._calculate_betweenness_centrality()
            elif metric == "closeness":
                centrality = self._calculate_closeness_centrality()
            elif metric == "degree":
                centrality = self._calculate_degree_centrality()
            elif metric == "eigenvector":
                centrality = self._calculate_eigenvector_centrality()
            else:
                logger.error(f"Unsupported centrality metric: {metric}")
                return []
                
            # 排序并返回前K个
            sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            return sorted_nodes[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find central nodes: {str(e)}")
            return []
            
    def detect_communities(self, algorithm: str = "louvain") -> Dict[str, int]:
        """
        检测社区结构
        
        Args:
            algorithm: 社区检测算法 (louvain, label_propagation, girvan_newman)
            
        Returns:
            Dict[str, int]: 节点ID -> 社区ID 映射
        """
        try:
            if algorithm == "louvain":
                return self._louvain_community_detection()
            elif algorithm == "label_propagation":
                return self._label_propagation_community_detection()
            elif algorithm == "girvan_newman":
                return self._girvan_newman_community_detection()
            else:
                logger.error(f"Unsupported community detection algorithm: {algorithm}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to detect communities: {str(e)}")
            return {}
            
    def _bfs_traversal(self, start_node: str, direction: TraversalDirection,
                      max_depth: int, node_filter: Callable) -> TraversalResult:
        """广度优先搜索遍历"""
        visited_nodes = set()
        traversal_order = []
        depth_map = {start_node: 0}
        parent_map = {}
        
        queue = deque([start_node])
        visited_nodes.add(start_node)
        
        while queue:
            current_node = queue.popleft()
            traversal_order.append(current_node)
            current_depth = depth_map[current_node]
            
            # 检查深度限制
            if max_depth is not None and current_depth >= max_depth:
                continue
                
            # 获取邻居节点
            neighbors = self._get_neighbors(current_node, direction)
            for neighbor, edge_data in neighbors:
                if neighbor not in visited_nodes:
                    # 应用节点过滤
                    if node_filter is None or node_filter(neighbor, edge_data):
                        visited_nodes.add(neighbor)
                        depth_map[neighbor] = current_depth + 1
                        parent_map[neighbor] = current_node
                        queue.append(neighbor)
                        
        return TraversalResult(
            visited_nodes=list(visited_nodes),
            traversal_order=traversal_order,
            depth_map=depth_map,
            parent_map=parent_map
        )
        
    def _dfs_traversal(self, start_node: str, direction: TraversalDirection,
                      max_depth: int, node_filter: Callable) -> TraversalResult:
        """深度优先搜索遍历"""
        visited_nodes = set()
        traversal_order = []
        depth_map = {start_node: 0}
        parent_map = {}
        
        stack = [(start_node, 0)]  # (node, depth)
        
        while stack:
            current_node, current_depth = stack.pop()
            
            if current_node not in visited_nodes:
                visited_nodes.add(current_node)
                traversal_order.append(current_node)
                
                # 检查深度限制
                if max_depth is not None and current_depth >= max_depth:
                    continue
                    
                # 获取邻居节点（逆序入栈以保持原始顺序）
                neighbors = self._get_neighbors(current_node, direction)
                for neighbor, edge_data in reversed(neighbors):
                    if neighbor not in visited_nodes:
                        # 应用节点过滤
                        if node_filter is None or node_filter(neighbor, edge_data):
                            depth_map[neighbor] = current_depth + 1
                            parent_map[neighbor] = current_node
                            stack.append((neighbor, current_depth + 1))
                            
        return TraversalResult(
            visited_nodes=list(visited_nodes),
            traversal_order=traversal_order,
            depth_map=depth_map,
            parent_map=parent_map
        )
        
    def _dijkstra_traversal(self, start_node: str, direction: TraversalDirection,
                           max_depth: int, node_filter: Callable) -> TraversalResult:
        """Dijkstra算法遍历"""
        distances = {start_node: 0}
        visited_nodes = set()
        traversal_order = []
        depth_map = {start_node: 0}
        parent_map = {}
        
        priority_queue = [(0, start_node)]
        
        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited_nodes:
                continue
                
            visited_nodes.add(current_node)
            traversal_order.append(current_node)
            current_depth = depth_map[current_node]
            
            # 检查深度限制
            if max_depth is not None and current_depth >= max_depth:
                continue
                
            # 获取邻居节点
            neighbors = self._get_neighbors(current_node, direction)
            for neighbor, edge_data in neighbors:
                if neighbor not in visited_nodes:
                    # 应用节点过滤
                    if node_filter is None or node_filter(neighbor, edge_data):
                        # 计算成本
                        cost = self._default_cost_function(current_node, neighbor, edge_data)
                        new_distance = current_distance + cost
                        
                        if new_distance < distances.get(neighbor, float('inf')):
                            distances[neighbor] = new_distance
                            depth_map[neighbor] = current_depth + 1
                            parent_map[neighbor] = current_node
                            heapq.heappush(priority_queue, (new_distance, neighbor))
                            
        return TraversalResult(
            visited_nodes=list(visited_nodes),
            traversal_order=traversal_order,
            depth_map=depth_map,
            parent_map=parent_map
        )
        
    def _a_star_traversal(self, start_node: str, direction: TraversalDirection,
                         max_depth: int, node_filter: Callable) -> TraversalResult:
        """A*算法遍历"""
        # 简化的A*实现，使用度中心性作为启发式函数
        def heuristic(node):
            return len(list(self._get_neighbors(node, direction)))
            
        distances = {start_node: 0}
        visited_nodes = set()
        traversal_order = []
        depth_map = {start_node: 0}
        parent_map = {}
        
        # (f_score, g_score, node)
        priority_queue = [(heuristic(start_node), 0, start_node)]
        
        while priority_queue:
            f_score, g_score, current_node = heapq.heappop(priority_queue)
            
            if current_node in visited_nodes:
                continue
                
            visited_nodes.add(current_node)
            traversal_order.append(current_node)
            current_depth = depth_map[current_node]
            
            # 检查深度限制
            if max_depth is not None and current_depth >= max_depth:
                continue
                
            # 获取邻居节点
            neighbors = self._get_neighbors(current_node, direction)
            for neighbor, edge_data in neighbors:
                if neighbor not in visited_nodes:
                    # 应用节点过滤
                    if node_filter is None or node_filter(neighbor, edge_data):
                        # 计算成本
                        cost = self._default_cost_function(current_node, neighbor, edge_data)
                        new_g_score = g_score + cost
                        new_f_score = new_g_score + heuristic(neighbor)
                        
                        if new_g_score < distances.get(neighbor, float('inf')):
                            distances[neighbor] = new_g_score
                            depth_map[neighbor] = current_depth + 1
                            parent_map[neighbor] = current_node
                            heapq.heappush(priority_queue, (new_f_score, new_g_score, neighbor))
                            
        return TraversalResult(
            visited_nodes=list(visited_nodes),
            traversal_order=traversal_order,
            depth_map=depth_map,
            parent_map=parent_map
        )
        
    def _get_neighbors(self, node: str, direction: TraversalDirection) -> List[Tuple[str, Dict]]:
        """获取邻居节点"""
        neighbors = []
        
        if direction in [TraversalDirection.OUTGOING, TraversalDirection.BOTH]:
            # 出边邻居
            if hasattr(self.graph, 'out_edges'):
                # NetworkX图
                for _, target, data in self.graph.out_edges(node, data=True):
                    neighbors.append((target, data))
            else:
                # 其他图结构
                pass
                
        if direction in [TraversalDirection.INCOMING, TraversalDirection.BOTH]:
            # 入边邻居
            if hasattr(self.graph, 'in_edges'):
                # NetworkX图
                for source, _, data in self.graph.in_edges(node, data=True):
                    neighbors.append((source, data))
            else:
                # 其他图结构
                pass
                
        return neighbors
        
    def _default_cost_function(self, source: str, target: str, edge_data: Dict) -> float:
        """默认成本函数"""
        # 使用边权重，默认为1.0
        return edge_data.get('weight', 1.0)
        
    def _calculate_path_cost(self, path: List[str]) -> float:
        """计算路径成本"""
        total_cost = 0.0
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # 获取边数据
            if hasattr(self.graph, 'get_edge_data'):
                edge_data = self.graph.get_edge_data(source, target)
                if edge_data:
                    total_cost += self._default_cost_function(source, target, edge_data)
                    
        return total_cost
        
    def _calculate_betweenness_centrality(self) -> Dict[str, float]:
        """计算介数中心性"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                return nx.betweenness_centrality(self.graph)
            else:
                logger.warning("Betweenness centrality requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for betweenness centrality")
            return {}
            
    def _calculate_closeness_centrality(self) -> Dict[str, float]:
        """计算接近中心性"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                return nx.closeness_centrality(self.graph)
            else:
                logger.warning("Closeness centrality requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for closeness centrality")
            return {}
            
    def _calculate_degree_centrality(self) -> Dict[str, float]:
        """计算度中心性"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                return nx.degree_centrality(self.graph)
            else:
                logger.warning("Degree centrality requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for degree centrality")
            return {}
            
    def _calculate_eigenvector_centrality(self) -> Dict[str, float]:
        """计算特征向量中心性"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                return nx.eigenvector_centrality(self.graph, max_iter=1000)
            else:
                logger.warning("Eigenvector centrality requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for eigenvector centrality")
            return {}
            
    def _louvain_community_detection(self) -> Dict[str, int]:
        """Louvain社区检测"""
        try:
            import community as community_louvain
            if isinstance(self.graph, nx.Graph):
                partition = community_louvain.best_partition(self.graph)
                return partition
            else:
                logger.warning("Louvain community detection requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("python-louvain package not available")
            return {}
            
    def _label_propagation_community_detection(self) -> Dict[str, int]:
        """标签传播社区检测"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                communities = list(nx.algorithms.community.label_propagation_communities(self.graph))
                partition = {}
                for i, community in enumerate(communities):
                    for node in community:
                        partition[node] = i
                return partition
            else:
                logger.warning("Label propagation requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for label propagation")
            return {}
            
    def _girvan_newman_community_detection(self) -> Dict[str, int]:
        """Girvan-Newman社区检测"""
        try:
            import networkx as nx
            if isinstance(self.graph, nx.Graph):
                # 只获取第一层社区（两个社区）
                comp = nx.algorithms.community.girvan_newman(self.graph)
                communities = next(comp)
                partition = {}
                for i, community in enumerate(communities):
                    for node in community:
                        partition[node] = i
                return partition
            else:
                logger.warning("Girvan-Newman requires NetworkX graph")
                return {}
        except ImportError:
            logger.warning("NetworkX not available for Girvan-Newman")
            return {}

