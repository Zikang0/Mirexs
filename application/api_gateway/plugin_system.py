"""
插件系统模块 - Mirexs API网关

提供插件扩展功能，包括：
1. 插件发现和加载
2. 插件生命周期管理
3. 钩子系统
4. 依赖管理
5. 插件配置
6. 插件隔离
"""

import logging
import time
import json
import importlib
import inspect
import threading
import os
import sys
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)

class PluginStatus(Enum):
    """插件状态枚举"""
    DISCOVERED = "discovered"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNINSTALLED = "uninstalled"

class PluginHook(Enum):
    """插件钩子枚举"""
    # 系统钩子
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    
    # API钩子
    BEFORE_REQUEST = "before_request"
    AFTER_REQUEST = "after_request"
    BEFORE_RESPONSE = "before_response"
    AFTER_RESPONSE = "after_response"
    
    # 路由钩子
    ROUTE_REGISTERED = "route_registered"
    ROUTE_UNREGISTERED = "route_unregistered"
    
    # 认证钩子
    AUTHENTICATE = "authenticate"
    AUTHORIZE = "authorize"
    
    # 数据钩子
    BEFORE_CREATE = "before_create"
    AFTER_CREATE = "after_create"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"
    
    # 事件钩子
    ON_EVENT = "on_event"
    
    # 自定义钩子
    CUSTOM = "custom"

@dataclass
class PluginManifest:
    """插件清单"""
    id: str
    name: str
    version: str
    description: str
    author: str
    license: str
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    min_api_version: str = "1.0.0"
    max_api_version: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

@dataclass
class Plugin:
    """插件"""
    id: str
    manifest: PluginManifest
    module: Optional[Any] = None
    instance: Optional[Any] = None
    status: PluginStatus = PluginStatus.DISCOVERED
    config: Dict[str, Any] = field(default_factory=dict)
    hooks: Dict[str, List[Callable]] = field(default_factory=dict)
    error: Optional[str] = None
    load_time: Optional[float] = None
    enabled_time: Optional[float] = None

@dataclass
class PluginConfig:
    """插件系统配置"""
    # 插件目录
    plugins_dir: str = "plugins/"
    system_plugins_dir: str = "plugins/system/"
    user_plugins_dir: str = "plugins/user/"
    
    # 加载配置
    auto_load: bool = True
    safe_mode: bool = False
    enable_hot_reload: bool = False
    
    # 安全配置
    sandbox: bool = True
    allowed_imports: List[str] = field(default_factory=lambda: [
        "json", "time", "datetime", "logging"
    ])
    
    # 缓存配置
    cache_manifests: bool = True
    cache_dir: str = "data/plugins/cache/"

class PluginSystem:
    """
    插件系统管理器
    
    负责插件的发现、加载、管理和执行。
    """
    
    def __init__(self, config: Optional[PluginConfig] = None):
        """
        初始化插件系统管理器
        
        Args:
            config: 插件系统配置
        """
        self.config = config or PluginConfig()
        
        # 插件存储
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[str]] = {}  # hook_name -> [plugin_ids]
        
        # 依赖图
        self.dependency_graph: Dict[str, List[str]] = {}
        
        # 钩子执行顺序
        self.hook_execution_order: Dict[str, List[str]] = {}
        
        # 监控线程
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_watcher = threading.Event()
        
        # 回调函数
        self.on_plugin_discovered: Optional[Callable[[Plugin], None]] = None
        self.on_plugin_loaded: Optional[Callable[[Plugin], None]] = None
        self.on_plugin_enabled: Optional[Callable[[Plugin], None]] = None
        self.on_plugin_disabled: Optional[Callable[[Plugin], None]] = None
        self.on_plugin_error: Optional[Callable[[str, str], None]] = None
        self.on_hook_executed: Optional[Callable[[str, str, Any], None]] = None
        
        # 统计
        self.stats = {
            "plugins_discovered": 0,
            "plugins_loaded": 0,
            "plugins_enabled": 0,
            "plugins_disabled": 0,
            "hooks_executed": 0,
            "errors": 0
        }
        
        # 创建插件目录
        self._ensure_directories()
        
        # 自动发现
        if self.config.auto_load:
            self.discover_plugins()
            self.load_all()
        
        logger.info("PluginSystem initialized")
    
    def _ensure_directories(self):
        """确保插件目录存在"""
        os.makedirs(self.config.plugins_dir, exist_ok=True)
        os.makedirs(self.config.system_plugins_dir, exist_ok=True)
        os.makedirs(self.config.user_plugins_dir, exist_ok=True)
        os.makedirs(self.config.cache_dir, exist_ok=True)
    
    def discover_plugins(self, directory: Optional[str] = None) -> List[Plugin]:
        """
        发现插件
        
        Args:
            directory: 插件目录
        
        Returns:
            发现的插件列表
        """
        discover_dirs = []
        
        if directory:
            discover_dirs = [directory]
        else:
            discover_dirs = [
                self.config.system_plugins_dir,
                self.config.user_plugins_dir
            ]
        
        discovered = []
        
        for plugin_dir in discover_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            for item in os.listdir(plugin_dir):
                plugin_path = os.path.join(plugin_dir, item)
                
                # 检查是否是插件目录
                if os.path.isdir(plugin_path):
                    manifest_path = os.path.join(plugin_path, "manifest.json")
                    if os.path.exists(manifest_path):
                        plugin = self._load_manifest(manifest_path, plugin_path)
                        if plugin:
                            discovered.append(plugin)
        
        logger.info(f"Discovered {len(discovered)} plugins")
        
        return discovered
    
    def _load_manifest(self, manifest_path: str, plugin_path: str) -> Optional[Plugin]:
        """加载插件清单"""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            manifest = PluginManifest(
                id=data.get("id", os.path.basename(plugin_path)),
                name=data.get("name", "Unknown"),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                author=data.get("author", "Unknown"),
                license=data.get("license", "MIT"),
                entry_point=data.get("entry_point", "main.py"),
                dependencies=data.get("dependencies", []),
                hooks=data.get("hooks", []),
                permissions=data.get("permissions", []),
                config_schema=data.get("config_schema"),
                min_api_version=data.get("min_api_version", "1.0.0"),
                max_api_version=data.get("max_api_version")
            )
            
            plugin = Plugin(
                id=manifest.id,
                manifest=manifest,
                status=PluginStatus.DISCOVERED,
                config=data.get("config", {})
            )
            
            self.plugins[manifest.id] = plugin
            self.stats["plugins_discovered"] += 1
            
            if self.on_plugin_discovered:
                self.on_plugin_discovered(plugin)
            
            logger.debug(f"Plugin discovered: {manifest.name} v{manifest.version}")
            
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading manifest {manifest_path}: {e}")
            return None
    
    def load_plugin(self, plugin_id: str) -> bool:
        """
        加载插件
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            是否成功
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin {plugin_id} not found")
            return False
        
        plugin = self.plugins[plugin_id]
        
        if plugin.status in [PluginStatus.LOADED, PluginStatus.ENABLED]:
            logger.warning(f"Plugin {plugin_id} already loaded")
            return True
        
        # 检查依赖
        for dep_id in plugin.manifest.dependencies:
            if dep_id not in self.plugins:
                logger.error(f"Dependency {dep_id} not found for plugin {plugin_id}")
                plugin.status = PluginStatus.ERROR
                plugin.error = f"Missing dependency: {dep_id}"
                return False
            
            if self.plugins[dep_id].status != PluginStatus.ENABLED:
                # 尝试加载依赖
                if not self.load_plugin(dep_id):
                    plugin.status = PluginStatus.ERROR
                    plugin.error = f"Failed to load dependency: {dep_id}"
                    return False
        
        logger.info(f"Loading plugin: {plugin.manifest.name}")
        
        plugin.status = PluginStatus.LOADING
        
        try:
            # 构建插件模块路径
            plugin_dir = self._get_plugin_dir(plugin_id)
            sys.path.insert(0, plugin_dir)
            
            # 导入插件模块
            module_name = plugin.manifest.entry_point.replace('.py', '')
            module = importlib.import_module(module_name)
            
            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and hasattr(obj, '__plugin__'):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                # 尝试查找默认的Plugin类
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and name == "Plugin":
                        plugin_class = obj
                        break
            
            if not plugin_class:
                raise Exception("No plugin class found")
            
            # 创建插件实例
            plugin_instance = plugin_class()
            plugin_instance.plugin_id = plugin_id
            plugin_instance.config = plugin.config
            
            # 注册钩子
            self._register_hooks(plugin_id, plugin_instance)
            
            plugin.module = module
            plugin.instance = plugin_instance
            plugin.status = PluginStatus.LOADED
            plugin.load_time = time.time()
            
            self.stats["plugins_loaded"] += 1
            
            if self.on_plugin_loaded:
                self.on_plugin_loaded(plugin)
            
            logger.info(f"Plugin loaded: {plugin.manifest.name}")
            
            return True
            
        except Exception as e:
            plugin.status = PluginStatus.ERROR
            plugin.error = str(e)
            self.stats["errors"] += 1
            
            logger.error(f"Error loading plugin {plugin_id}: {e}")
            
            if self.on_plugin_error:
                self.on_plugin_error(plugin_id, str(e))
            
            return False
    
    def _get_plugin_dir(self, plugin_id: str) -> str:
        """获取插件目录"""
        # 检查系统插件目录
        system_path = os.path.join(self.config.system_plugins_dir, plugin_id)
        if os.path.exists(system_path):
            return system_path
        
        # 检查用户插件目录
        user_path = os.path.join(self.config.user_plugins_dir, plugin_id)
        if os.path.exists(user_path):
            return user_path
        
        return ""
    
    def _register_hooks(self, plugin_id: str, plugin_instance: Any):
        """注册插件钩子"""
        for hook_name in PluginHook:
            hook_value = hook_name.value
            if hasattr(plugin_instance, hook_value):
                method = getattr(plugin_instance, hook_value)
                if callable(method):
                    if hook_value not in self.hooks:
                        self.hooks[hook_value] = []
                    self.hooks[hook_value].append(plugin_id)
                    
                    if hook_value not in self.hook_execution_order:
                        self.hook_execution_order[hook_value] = []
                    self.hook_execution_order[hook_value].append(plugin_id)
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        启用插件
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            是否成功
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin {plugin_id} not found")
            return False
        
        plugin = self.plugins[plugin_id]
        
        if plugin.status == PluginStatus.ERROR:
            logger.warning(f"Cannot enable plugin in error state: {plugin_id}")
            return False
        
        if plugin.status == PluginStatus.DISCOVERED:
            if not self.load_plugin(plugin_id):
                return False
        
        if plugin.status == PluginStatus.LOADED:
            try:
                if hasattr(plugin.instance, 'on_enable'):
                    plugin.instance.on_enable()
                
                plugin.status = PluginStatus.ENABLED
                plugin.enabled_time = time.time()
                
                self.stats["plugins_enabled"] += 1
                
                if self.on_plugin_enabled:
                    self.on_plugin_enabled(plugin)
                
                logger.info(f"Plugin enabled: {plugin.manifest.name}")
                
                return True
                
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error = str(e)
                self.stats["errors"] += 1
                
                logger.error(f"Error enabling plugin {plugin_id}: {e}")
        
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        禁用插件
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            是否成功
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin {plugin_id} not found")
            return False
        
        plugin = self.plugins[plugin_id]
        
        if plugin.status == PluginStatus.ENABLED:
            try:
                if hasattr(plugin.instance, 'on_disable'):
                    plugin.instance.on_disable()
                
                plugin.status = PluginStatus.DISABLED
                
                self.stats["plugins_disabled"] += 1
                
                if self.on_plugin_disabled:
                    self.on_plugin_disabled(plugin)
                
                logger.info(f"Plugin disabled: {plugin.manifest.name}")
                
                return True
                
            except Exception as e:
                plugin.status = PluginStatus.ERROR
                plugin.error = str(e)
                self.stats["errors"] += 1
                
                logger.error(f"Error disabling plugin {plugin_id}: {e}")
        
        return False
    
    def load_all(self) -> int:
        """
        加载所有插件
        
        Returns:
            成功加载的数量
        """
        loaded = 0
        
        # 按依赖顺序加载
        for plugin_id in self._sort_by_dependencies():
            if self.load_plugin(plugin_id):
                loaded += 1
        
        return loaded
    
    def enable_all(self) -> int:
        """
        启用所有插件
        
        Returns:
            成功启用的数量
        """
        enabled = 0
        
        for plugin_id in self._sort_by_dependencies():
            if self.enable_plugin(plugin_id):
                enabled += 1
        
        return enabled
    
    def _sort_by_dependencies(self) -> List[str]:
        """按依赖关系排序"""
        # 构建依赖图
        graph = {}
        for plugin_id, plugin in self.plugins.items():
            graph[plugin_id] = plugin.manifest.dependencies.copy()
        
        # 拓扑排序
        sorted_plugins = []
        visited = set()
        temp_visited = set()
        
        def visit(plugin_id):
            if plugin_id in temp_visited:
                # 检测到循环依赖
                logger.warning(f"Circular dependency detected for {plugin_id}")
                return
            
            if plugin_id in visited:
                return
            
            temp_visited.add(plugin_id)
            
            for dep_id in graph.get(plugin_id, []):
                if dep_id in graph:
                    visit(dep_id)
            
            temp_visited.remove(plugin_id)
            visited.add(plugin_id)
            sorted_plugins.append(plugin_id)
        
        for plugin_id in graph:
            if plugin_id not in visited:
                visit(plugin_id)
        
        return sorted_plugins
    
    def execute_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        执行钩子
        
        Args:
            hook_name: 钩子名称
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            执行结果列表
        """
        results = []
        
        if hook_name not in self.hooks:
            return results
        
        for plugin_id in self.hook_execution_order.get(hook_name, []):
            plugin = self.plugins.get(plugin_id)
            
            if not plugin or plugin.status != PluginStatus.ENABLED:
                continue
            
            if hasattr(plugin.instance, hook_name):
                try:
                    method = getattr(plugin.instance, hook_name)
                    result = method(*args, **kwargs)
                    results.append((plugin_id, result))
                    
                    self.stats["hooks_executed"] += 1
                    
                    if self.on_hook_executed:
                        self.on_hook_executed(plugin_id, hook_name, result)
                        
                except Exception as e:
                    logger.error(f"Error executing hook {hook_name} for plugin {plugin_id}: {e}")
                    self.stats["errors"] += 1
        
        return results
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """获取插件"""
        return self.plugins.get(plugin_id)
    
    def get_plugins(self, status: Optional[PluginStatus] = None) -> List[Plugin]:
        """
        获取插件列表
        
        Args:
            status: 状态过滤
        
        Returns:
            插件列表
        """
        plugins = list(self.plugins.values())
        
        if status:
            plugins = [p for p in plugins if p.status == status]
        
        return plugins
    
    def get_plugins_by_hook(self, hook_name: str) -> List[Plugin]:
        """
        获取实现了指定钩子的插件
        
        Args:
            hook_name: 钩子名称
        
        Returns:
            插件列表
        """
        plugin_ids = self.hooks.get(hook_name, [])
        return [self.plugins[pid] for pid in plugin_ids if pid in self.plugins]
    
    def install_plugin(self, plugin_path: str) -> Optional[str]:
        """
        安装插件
        
        Args:
            plugin_path: 插件文件或目录路径
        
        Returns:
            插件ID
        """
        import shutil
        
        try:
            # 复制插件到用户插件目录
            plugin_name = os.path.basename(plugin_path)
            target_path = os.path.join(self.config.user_plugins_dir, plugin_name)
            
            if os.path.isfile(plugin_path):
                shutil.copy2(plugin_path, target_path)
            else:
                shutil.copytree(plugin_path, target_path)
            
            # 发现插件
            discovered = self.discover_plugins(target_path)
            
            if discovered:
                plugin_id = discovered[0].id
                logger.info(f"Plugin installed: {plugin_id}")
                return plugin_id
            
        except Exception as e:
            logger.error(f"Error installing plugin: {e}")
        
        return None
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            是否成功
        """
        if plugin_id not in self.plugins:
            logger.warning(f"Plugin {plugin_id} not found")
            return False
        
        plugin = self.plugins[plugin_id]
        
        # 禁用插件
        if plugin.status == PluginStatus.ENABLED:
            self.disable_plugin(plugin_id)
        
        # 删除插件文件
        plugin_dir = self._get_plugin_dir(plugin_id)
        if plugin_dir and os.path.exists(plugin_dir):
            import shutil
            shutil.rmtree(plugin_dir)
        
        # 从系统中移除
        del self.plugins[plugin_id]
        
        logger.info(f"Plugin uninstalled: {plugin_id}")
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取插件系统状态
        
        Returns:
            状态字典
        """
        return {
            "plugins": {
                "total": len(self.plugins),
                "discovered": len([p for p in self.plugins.values() if p.status == PluginStatus.DISCOVERED]),
                "loaded": len([p for p in self.plugins.values() if p.status == PluginStatus.LOADED]),
                "enabled": len([p for p in self.plugins.values() if p.status == PluginStatus.ENABLED]),
                "disabled": len([p for p in self.plugins.values() if p.status == PluginStatus.DISABLED]),
                "error": len([p for p in self.plugins.values() if p.status == PluginStatus.ERROR])
            },
            "hooks": {
                "total": len(self.hooks),
                "by_hook": {k: len(v) for k, v in self.hooks.items()}
            },
            "stats": self.stats,
            "config": {
                "auto_load": self.config.auto_load,
                "safe_mode": self.config.safe_mode,
                "hot_reload": self.config.enable_hot_reload
            }
        }
    
    def shutdown(self):
        """关闭插件系统"""
        logger.info("Shutting down PluginSystem...")
        
        # 禁用所有插件
        for plugin_id in list(self.plugins.keys()):
            self.disable_plugin(plugin_id)
        
        self.plugins.clear()
        self.hooks.clear()
        self.dependency_graph.clear()
        self.hook_execution_order.clear()
        
        logger.info("PluginSystem shutdown completed")

# 单例模式实现
_plugin_system_instance: Optional[PluginSystem] = None

def get_plugin_system(config: Optional[PluginConfig] = None) -> PluginSystem:
    """
    获取插件系统单例
    
    Args:
        config: 插件系统配置
    
    Returns:
        插件系统实例
    """
    global _plugin_system_instance
    if _plugin_system_instance is None:
        _plugin_system_instance = PluginSystem(config)
    return _plugin_system_instance