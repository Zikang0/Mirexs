"""
插件管理器

负责插件的全生命周期管理，包括插件的安装、激活、停用、卸载等操作。
提供插件状态管理和插件间通信功能。

Author: AI Assistant
Date: 2025-11-05
"""

import logging
import threading
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PluginStatus(Enum):
    """插件状态枚举"""
    UNKNOWN = "unknown"
    INSTALLED = "installed"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    ERROR = "error"
    UPDATING = "updating"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """插件信息数据类"""
    name: str
    version: str
    description: str
    author: str
    status: PluginStatus = PluginStatus.UNKNOWN
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    install_date: Optional[datetime] = None
    last_activated: Optional[datetime] = None
    error_message: Optional[str] = None


class PluginManager:
    """插件管理器类"""
    
    def __init__(self):
        """初始化插件管理器"""
        self.logger = logging.getLogger(__name__)
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugin_instances: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._loader = None  # 将在外部注入
        self._registry = None  # 将在外部注入
        
    def set_loader(self, loader) -> None:
        """设置插件加载器"""
        self._loader = loader
        self.logger.info("插件加载器已设置")
        
    def set_registry(self, registry) -> None:
        """设置插件注册表"""
        self._registry = registry
        self.logger.info("插件注册表已设置")
    
    def register_plugin(self, plugin_info: PluginInfo) -> bool:
        """
        注册插件
        
        Args:
            plugin_info: 插件信息
            
        Returns:
            bool: 注册成功返回True，否则返回False
        """
        try:
            with self._lock:
                if plugin_info.name in self._plugins:
                    self.logger.warning(f"插件已存在: {plugin_info.name}")
                    return False
                
                self._plugins[plugin_info.name] = plugin_info
                self.logger.info(f"插件注册成功: {plugin_info.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"插件注册失败 {plugin_info.name}: {str(e)}")
            return False
    
    def install_plugin(self, plugin_name: str, plugin_path: str) -> bool:
        """
        安装插件
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件路径
            
        Returns:
            bool: 安装成功返回True，否则返回False
        """
        try:
            self.logger.info(f"正在安装插件: {plugin_name}")
            
            # TODO: 实现插件安装逻辑
            # 1. 验证插件文件
            # 2. 检查依赖
            # 3. 复制插件文件
            # 4. 注册插件
            
            plugin_info = PluginInfo(
                name=plugin_name,
                version="1.0.0",
                description="插件描述",
                author="未知作者",
                status=PluginStatus.INSTALLED,
                install_date=datetime.now()
            )
            
            return self.register_plugin(plugin_info)
            
        except Exception as e:
            self.logger.error(f"插件安装失败 {plugin_name}: {str(e)}")
            return False
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """
        激活插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 激活成功返回True，否则返回False
        """
        try:
            with self._lock:
                if plugin_name not in self._plugins:
                    self.logger.error(f"插件不存在: {plugin_name}")
                    return False
                
                plugin_info = self._plugins[plugin_name]
                
                # 检查插件状态
                if plugin_info.status == PluginStatus.ACTIVATED:
                    self.logger.warning(f"插件已经激活: {plugin_name}")
                    return True
                
                if plugin_info.status == PluginStatus.ERROR:
                    self.logger.error(f"插件处于错误状态: {plugin_name}")
                    return False
                
                # TODO: 加载插件类并实例化
                # 1. 使用loader加载插件模块
                # 2. 验证插件类
                # 3. 实例化插件
                # 4. 调用激活方法
                
                plugin_info.status = PluginStatus.ACTIVATED
                plugin_info.last_activated = datetime.now()
                plugin_info.error_message = None
                
                self.logger.info(f"插件激活成功: {plugin_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"插件激活失败 {plugin_name}: {str(e)}")
            if plugin_name in self._plugins:
                self._plugins[plugin_name].status = PluginStatus.ERROR
                self._plugins[plugin_name].error_message = str(e)
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """
        停用插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 停用成功返回True，否则返回False
        """
        try:
            with self._lock:
                if plugin_name not in self._plugins:
                    self.logger.error(f"插件不存在: {plugin_name}")
                    return False
                
                plugin_info = self._plugins[plugin_name]
                
                if plugin_info.status != PluginStatus.ACTIVATED:
                    self.logger.warning(f"插件未激活: {plugin_name}")
                    return True
                
                # TODO: 停用插件
                # 1. 调用插件停用方法
                # 2. 清理插件实例
                
                plugin_info.status = PluginStatus.DEACTIVATED
                
                self.logger.info(f"插件停用成功: {plugin_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"插件停用失败 {plugin_name}: {str(e)}")
            return False
    
    def uninstall_plugin(self, plugin_name: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            bool: 卸载成功返回True，否则返回False
        """
        try:
            with self._lock:
                if plugin_name not in self._plugins:
                    self.logger.error(f"插件不存在: {plugin_name}")
                    return False
                
                # 如果插件正在运行，先停用
                plugin_info = self._plugins[plugin_name]
                if plugin_info.status == PluginStatus.ACTIVATED:
                    self.deactivate_plugin(plugin_name)
                
                # TODO: 清理插件文件和数据
                
                del self._plugins[plugin_name]
                if plugin_name in self._plugin_instances:
                    del self._plugin_instances[plugin_name]
                
                self.logger.info(f"插件卸载成功: {plugin_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"插件卸载失败 {plugin_name}: {str(e)}")
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
    
    def list_plugins(self, status: Optional[PluginStatus] = None) -> List[PluginInfo]:
        """
        获取插件列表
        
        Args:
            status: 插件状态过滤
            
        Returns:
            List[PluginInfo]: 插件信息列表
        """
        plugins = list(self._plugins.values())
        if status:
            plugins = [p for p in plugins if p.status == status]
        return plugins
    
    def get_plugin_instance(self, plugin_name: str) -> Optional[Any]:
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            Optional[Any]: 插件实例，如果不存在返回None
        """
        return self._plugin_instances.get(plugin_name)
    
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
                return False
            
            plugin_info = self._plugins[plugin_name]
            plugin_info.status = PluginStatus.DEACTIVATED
            
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
                return False
            
            plugin_info = self._plugins[plugin_name]
            plugin_info.status = PluginStatus.DISABLED
            
            self.logger.info(f"插件禁用成功: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"插件禁用失败 {plugin_name}: {str(e)}")
            return False