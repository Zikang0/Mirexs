"""
依赖解析器

负责解析插件依赖关系，解决依赖冲突和版本兼容性问题。
提供依赖图构建和拓扑排序功能。

Author: AI Assistant
Date: 2025-11-05
"""

import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict, deque


@dataclass
class DependencyInfo:
    """依赖信息数据类"""
    name: str
    version_spec: str
    optional: bool = False


class DependencyResolver:
    """依赖解析器类"""
    
    def __init__(self):
        """初始化依赖解析器"""
        self.logger = logging.getLogger(__name__)
        self._dependencies: Dict[str, List[DependencyInfo]] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        
    def add_plugin_dependencies(self, plugin_name: str, dependencies: List[DependencyInfo]) -> None:
        """
        添加插件依赖
        
        Args:
            plugin_name: 插件名称
            dependencies: 依赖列表
        """
        self._dependencies[plugin_name] = dependencies
        self.logger.info(f"为插件 {plugin_name} 添加了 {len(dependencies)} 个依赖")
        
        # 更新依赖图
        for dep in dependencies:
            self._dependency_graph[plugin_name].add(dep.name)
            self._reverse_graph[dep.name].add(plugin_name)
    
    def remove_plugin_dependencies(self, plugin_name: str) -> None:
        """
        移除插件依赖
        
        Args:
            plugin_name: 插件名称
        """
        if plugin_name in self._dependencies:
            # 从依赖图中移除
            for dep in self._dependencies[plugin_name]:
                self._dependency_graph[plugin_name].discard(dep.name)
                self._reverse_graph[dep.name].discard(plugin_name)
            
            # 从其他插件的依赖中移除
            for other_plugin in self._dependency_graph:
                self._dependency_graph[other_plugin].discard(plugin_name)
            
            del self._dependencies[plugin_name]
            self.logger.info(f"移除插件 {plugin_name} 的依赖")
    
    def resolve_dependencies(self, plugin_name: str, available_plugins: Set[str]) -> Tuple[bool, List[str], List[str]]:
        """
        解析插件依赖
        
        Args:
            plugin_name: 插件名称
            available_plugins: 可用插件集合
            
        Returns:
            Tuple[bool, List[str], List[str]]: (是否可解析, 解析后的依赖列表, 缺失的依赖列表)
        """
        try:
            self.logger.info(f"正在解析插件 {plugin_name} 的依赖")
            
            if plugin_name not in self._dependencies:
                return True, [], []
            
            resolved_deps = []
            missing_deps = []
            visited = set()
            visiting = set()
            
            def dfs(current_plugin: str) -> bool:
                if current_plugin in visiting:
                    self.logger.warning(f"检测到循环依赖: {current_plugin}")
                    return False
                
                if current_plugin in visited:
                    return True
                
                visiting.add(current_plugin)
                
                if current_plugin not in self._dependencies:
                    visited.add(current_plugin)
                    return True
                
                for dep in self._dependencies[current_plugin]:
                    if dep.name not in available_plugins:
                        missing_deps.append(dep.name)
                        continue
                    
                    if not dfs(dep.name):
                        return False
                    
                    resolved_deps.append(dep.name)
                
                visiting.remove(current_plugin)
                visited.add(current_plugin)
                return True
            
            if not dfs(plugin_name):
                return False, [], missing_deps
            
            # 去重并保持顺序
            resolved_deps = list(dict.fromkeys(resolved_deps))
            
            self.logger.info(f"插件 {plugin_name} 依赖解析成功")
            return True, resolved_deps, missing_deps
            
        except Exception as e:
            self.logger.error(f"依赖解析失败 {plugin_name}: {str(e)}")
            return False, [], []
    
    def get_load_order(self, plugin_names: List[str], available_plugins: Set[str]) -> List[str]:
        """
        获取插件加载顺序（拓扑排序）
        
        Args:
            plugin_names: 插件名称列表
            available_plugins: 可用插件集合
            
        Returns:
            List[str]: 加载顺序列表
        """
        try:
            self.logger.info(f"正在计算 {len(plugin_names)} 个插件的加载顺序")
            
            # 构建子图
            subgraph = defaultdict(set)
            for plugin in plugin_names:
                if plugin in self._dependency_graph:
                    for dep in self._dependency_graph[plugin]:
                        if dep in plugin_names:
                            subgraph[plugin].add(dep)
            
            # 拓扑排序
            in_degree = defaultdict(int)
            for plugin in plugin_names:
                in_degree[plugin] = 0
            
            for plugin in plugin_names:
                for dep in subgraph[plugin]:
                    in_degree[dep] += 1
            
            queue = deque([plugin for plugin in plugin_names if in_degree[plugin] == 0])
            result = []
            
            while queue:
                current = queue.popleft()
                result.append(current)
                
                for dependent in subgraph[current]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
            
            # 检查是否有循环依赖
            if len(result) != len(plugin_names):
                remaining = set(plugin_names) - set(result)
                self.logger.error(f"检测到循环依赖，剩余插件: {remaining}")
                return result + list(remaining)  # 返回部分结果
            
            self.logger.info(f"加载顺序计算成功: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"加载顺序计算失败: {str(e)}")
            return plugin_names  # 返回原始顺序作为fallback
    
    def check_version_compatibility(self, plugin_name: str, version: str, 
                                  dependency_versions: Dict[str, str]) -> bool:
        """
        检查版本兼容性
        
        Args:
            plugin_name: 插件名称
            version: 插件版本
            dependency_versions: 依赖版本字典
            
        Returns:
            bool: 兼容返回True，否则返回False
        """
        try:
            if plugin_name not in self._dependencies:
                return True
            
            for dep in self._dependencies[plugin_name]:
                if dep.name in dependency_versions:
                    dep_version = dependency_versions[dep.name]
                    # TODO: 实现版本比较逻辑
                    # 这里应该根据version_spec进行版本匹配
                    if not self._compare_versions(dep_version, dep.version_spec):
                        self.logger.warning(f"版本不兼容: {plugin_name} 需要 {dep.name} {dep.version_spec}，但实际为 {dep_version}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"版本兼容性检查失败: {str(e)}")
            return False
    
    def _compare_versions(self, actual: str, spec: str) -> bool:
        """
        比较版本（简化实现）
        
        Args:
            actual: 实际版本
            spec: 版本规范
            
        Returns:
            bool: 匹配返回True，否则返回False
        """
        # TODO: 实现完整的版本比较逻辑
        # 这里应该支持语义化版本规范 (semver)
        return actual == spec or spec == "*"  # 简化实现
    
    def get_plugin_dependencies(self, plugin_name: str) -> List[DependencyInfo]:
        """
        获取插件依赖列表
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            List[DependencyInfo]: 依赖列表
        """
        return self._dependencies.get(plugin_name, [])
    
    def get_reverse_dependencies(self, plugin_name: str) -> List[str]:
        """
        获取依赖指定插件的插件列表
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            List[str]: 依赖插件列表
        """
        return list(self._reverse_graph.get(plugin_name, set()))