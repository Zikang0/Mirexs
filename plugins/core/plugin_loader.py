"""
插件加载器

负责动态加载插件模块，支持多种加载方式和插件格式。
提供插件发现、验证和初始化功能。

Author: AI Assistant
Date: 2025-11-05
"""

import importlib
import importlib.util
import os
import sys
import logging
from typing import Dict, List, Optional, Any, Type
from pathlib import Path


class PluginLoader:
    """插件加载器类"""
    
    def __init__(self):
        """初始化插件加载器"""
        self.logger = logging.getLogger(__name__)
        self._plugin_paths: List[str] = []
        self._loaded_modules: Dict[str, Any] = {}
        
    def add_plugin_path(self, path: str) -> None:
        """
        添加插件搜索路径
        
        Args:
            path: 插件路径
        """
        if path not in self._plugin_paths:
            self._plugin_paths.append(path)
            if path not in sys.path:
                sys.path.insert(0, path)
            self.logger.info(f"添加插件路径: {path}")
    
    def discover_plugins(self, directory: str) -> List[str]:
        """
        发现目录中的插件
        
        Args:
            directory: 插件目录
            
        Returns:
            List[str]: 发现的插件列表
        """
        plugins = []
        try:
            self.logger.info(f"在目录中发现插件: {directory}")
            # TODO: 实现插件发现逻辑
            # 扫描目录中的Python文件
            for file_path in Path(directory).rglob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                plugins.append(str(file_path))
            self.logger.info(f"发现 {len(plugins)} 个插件")
        except Exception as e:
            self.logger.error(f"插件发现失败: {str(e)}")
        return plugins
    
    def load_plugin_module(self, module_path: str, module_name: str) -> Optional[Any]:
        """
        加载插件模块
        
        Args:
            module_path: 模块文件路径
            module_name: 模块名称
            
        Returns:
            Optional[Any]: 加载的模块，如果失败返回None
        """
        try:
            self.logger.info(f"正在加载插件模块: {module_name}")
            
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法创建模块规范: {module_name}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            self._loaded_modules[module_name] = module
            self.logger.info(f"插件模块加载成功: {module_name}")
            return module
            
        except Exception as e:
            self.logger.error(f"插件模块加载失败 {module_name}: {str(e)}")
            return None
    
    def load_plugin_class(self, module: Any, class_name: str) -> Optional[Type]:
        """
        从模块中加载插件类
        
        Args:
            module: 插件模块
            class_name: 类名
            
        Returns:
            Optional[Type]: 插件类，如果失败返回None
        """
        try:
            if not hasattr(module, class_name):
                raise AttributeError(f"模块中没有找到类: {class_name}")
            
            plugin_class = getattr(module, class_name)
            self.logger.info(f"插件类加载成功: {class_name}")
            return plugin_class
            
        except Exception as e:
            self.logger.error(f"插件类加载失败 {class_name}: {str(e)}")
            return None
    
    def validate_plugin(self, plugin_class: Type) -> bool:
        """
        验证插件类的有效性
        
        Args:
            plugin_class: 插件类
            
        Returns:
            bool: 验证通过返回True，否则返回False
        """
        try:
            # TODO: 实现插件验证逻辑
            # 检查插件类是否实现了必要的接口
            required_methods = ['activate', 'deactivate', 'get_info']
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    self.logger.warning(f"插件缺少必要方法: {method}")
                    return False
            
            self.logger.info("插件验证通过")
            return True
            
        except Exception as e:
            self.logger.error(f"插件验证失败: {str(e)}")
            return False
    
    def get_loaded_modules(self) -> Dict[str, Any]:
        """
        获取已加载的模块列表
        
        Returns:
            Dict[str, Any]: 已加载的模块字典
        """
        return self._loaded_modules.copy()
    
    def unload_module(self, module_name: str) -> bool:
        """
        卸载模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 卸载成功返回True，否则返回False
        """
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]
            if module_name in self._loaded_modules:
                del self._loaded_modules[module_name]
            self.logger.info(f"模块卸载成功: {module_name}")
            return True
        except Exception as e:
            self.logger.error(f"模块卸载失败 {module_name}: {str(e)}")
            return False