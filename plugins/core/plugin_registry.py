"""
插件注册表

负责注册和管理所有插件，提供插件发现、注册、查询功能。
维护插件元数据和依赖关系信息。

Author: AI Assistant
Date: 2025-11-05
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class PluginInfo:
    """插件信息数据类"""
    name: str
    version: str
    description: str
    author: str
    category: str
    dependencies: List[str]
    entry_point: str
    registered_at: datetime
    enabled: bool = False


class PluginRegistry:
    """插件注册表类"""
    
    def __init__(self, registry_file: str = "plugin_registry.json"):
        """
        初始化插件注册表
        
        Args:
            registry_file: 注册表文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.registry_file = Path(registry_file)
        self._plugins: Dict[str, PluginInfo] = {}
        self._categories: Dict[str, List[str]] = {}
        
    def register_plugin(self, plugin_info: PluginInfo) -> bool:
        """
        注册插件
        
        Args:
            plugin_info: 插件信息
            
        Returns:
            bool: 注册成功返回True，否则返回False
        """
        try:
            self.logger.info(f"正在注册插件: {plugin_info.name}")
            
            # 检查插件是否已存在
            if plugin_info.name in self._plugins:
                self.logger.warning(f"插件已存在: {plugin_info.name}")
                return False
            
            # 注册插件
            self._plugins[plugin_info.name] = plugin_info
            
            # 更新分类
            if plugin_info.category not in self._categories:
                self._categories[plugin_info.category] = []
            self._categories[plugin_info.category].append(plugin_info.name)
            
            self.logger.info(f"插件注册成功: {plugin_info.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件注册失败 {plugin_info.name}: {str(e)}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """
        注销插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 注销成功返回True，否则返回False
        """
        try:
            self.logger.info(f"正在注销插件: {plugin_name}")
            
            if plugin_name not in self._plugins:
                self.logger.warning(f"插件不存在: {plugin_name}")
                return False
            
            plugin_info = self._plugins[plugin_name]
            
            # 从注册表中删除
            del self._plugins[plugin_name]
            
            # 从分类中删除
            if plugin_info.category in self._categories:
                if plugin_name in self._categories[plugin_info.category]:
                    self._categories[plugin_info.category].remove(plugin_name)
                    if not self._categories[plugin_info.category]:
                        del self._categories[plugin_info.category]
            
            self.logger.info(f"插件注销成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件注销失败 {plugin_name}: {str(e)}")
            return False
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        获取插件信息
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[PluginInfo]: 插件信息，如果不存在返回None
        """
        return self._plugins.get(plugin_name)
    
    def list_plugins(self, category: Optional[str] = None) -> List[str]:
        """
        列出插件
        
        Args:
            category: 插件分类，如果为None则返回所有插件
            
        Returns:
            List[str]: 插件名称列表
        """
        if category is None:
            return list(self._plugins.keys())
        else:
            return self._categories.get(category, [])
    
    def list_categories(self) -> List[str]:
        """
        列出所有插件分类
        
        Returns:
            List[str]: 分类名称列表
        """
        return list(self._categories.keys())
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """
        启用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 启用成功返回True，否则返回False
        """
        try:
            if plugin_name not in self._plugins:
                self.logger.warning(f"插件不存在: {plugin_name}")
                return False
            
            self._plugins[plugin_name].enabled = True
            self.logger.info(f"插件启用成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件启用失败 {plugin_name}: {str(e)}")
            return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """
        禁用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 禁用成功返回True，否则返回False
        """
        try:
            if plugin_name not in self._plugins:
                self.logger.warning(f"插件不存在: {plugin_name}")
                return False
            
            self._plugins[plugin_name].enabled = False
            self.logger.info(f"插件禁用成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件禁用失败 {plugin_name}: {str(e)}")
            return False
    
    def save_registry(self) -> bool:
        """
        保存注册表到文件
        
        Returns:
            bool: 保存成功返回True，否则返回False
        """
        try:
            registry_data = {
                "plugins": {name: asdict(info) for name, info in self._plugins.items()},
                "categories": self._categories
            }
            
            # 转换datetime为字符串
            for plugin_data in registry_data["plugins"].values():
                plugin_data["registered_at"] = plugin_data["registered_at"].isoformat()
            
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(registry_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"注册表保存成功: {self.registry_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册表保存失败: {str(e)}")
            return False
    
    def load_registry(self) -> bool:
        """
        从文件加载注册表
        
        Returns:
            bool: 加载成功返回True，否则返回False
        """
        try:
            if not self.registry_file.exists():
                self.logger.info("注册表文件不存在，跳过加载")
                return True
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            # 恢复插件信息
            self._plugins = {}
            for name, plugin_data in registry_data.get("plugins", {}).items():
                plugin_data["registered_at"] = datetime.fromisoformat(plugin_data["registered_at"])
                self._plugins[name] = PluginInfo(**plugin_data)
            
            # 恢复分类信息
            self._categories = registry_data.get("categories", {})
            
            self.logger.info(f"注册表加载成功，加载了 {len(self._plugins)} 个插件")
            return True
            
        except Exception as e:
            self.logger.error(f"注册表加载失败: {str(e)}")
            return False