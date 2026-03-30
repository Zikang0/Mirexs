"""
Mirexs 热重载配置模块（v2）
提供系统组件热重载功能配置。

说明：v1 目录名存在拼写问题（hot_reoad），v2 统一更正为 hot_reload。
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import yaml
import logging
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger("mirexs.config.runtime.hot_reload")

class HotReloadEvent:
    """热重载事件"""
    
    def __init__(self, event_type: str, component: str, timestamp: datetime = None, 
                 metadata: Dict[str, Any] = None):
        self.event_type = event_type
        self.component = component
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.success = True
        self.error_message = ""
        self.duration_seconds = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "success": self.success,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds
        }
    
    def __str__(self) -> str:
        return f"HotReloadEvent({self.event_type}, {self.component}, {self.timestamp})"

class HotReloadManager:
    """热重载管理器"""
    
    def __init__(self, config_dir: Path = None):
        """
        初始化热重载管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.configs = {}
        self.reload_handlers = {}
        self.event_history = []
        self.max_event_history = 1000
        self._load_configs()
        
        # 初始化默认处理器
        self._init_default_handlers()
    
    def _load_configs(self):
        """加载所有热重载配置文件"""
        config_files = [
            "config_reload.yaml",
            "model_reload.yaml",
            "service_reload.yaml",
            "plugin_reload.yaml",
            "hot_reload_metrics.yaml"
        ]
        
        for config_file in config_files:
            config_path = self.config_dir / config_file
            config_name = config_path.stem
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.configs[config_name] = config_data
                        logger.debug(f"Loaded hot reload config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load hot reload config {config_file}: {e}")
            else:
                logger.warning(f"Hot reload config file not found: {config_file}")
                self.configs[config_name] = {}
    
    def _init_default_handlers(self):
        """初始化默认重载处理器"""
        self.register_handler("config", self._reload_config_handler)
        self.register_handler("model", self._reload_model_handler)
        self.register_handler("service", self._reload_service_handler)
        self.register_handler("plugin", self._reload_plugin_handler)
    
    def get_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """获取配置"""
        if config_name not in self.configs:
            return default
        
        config = self.configs[config_name]
        
        if key is None:
            return config
        
        # 支持点分隔的嵌套键
        keys = key.split('.')
        current = config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def register_handler(self, component_type: str, handler: Callable):
        """注册重载处理器"""
        if component_type not in self.reload_handlers:
            self.reload_handlers[component_type] = []
        
        if handler not in self.reload_handlers[component_type]:
            self.reload_handlers[component_type].append(handler)
            logger.debug(f"Registered hot reload handler for {component_type}")
    
    def unregister_handler(self, component_type: str, handler: Callable):
        """取消注册处理器"""
        if component_type in self.reload_handlers and handler in self.reload_handlers[component_type]:
            self.reload_handlers[component_type].remove(handler)
            logger.debug(f"Unregistered hot reload handler for {component_type}")
    
    def trigger_reload(self, component_type: str, component_name: str, 
                       metadata: Dict[str, Any] = None) -> HotReloadEvent:
        """触发热重载"""
        start_time = datetime.now()
        event = HotReloadEvent("reload", f"{component_type}.{component_name}", metadata=metadata)
        
        try:
            if component_type not in self.reload_handlers:
                raise ValueError(f"No handlers registered for component type: {component_type}")
            
            config = self.get_config(f"{component_type}_reload", {})
            if not config.get("enabled", False):
                event.success = False
                event.error_message = f"Hot reload disabled for {component_type}"
                logger.warning(event.error_message)
                return event
            
            # 执行安全检查和验证
            if not self._perform_safety_checks(component_type, component_name, config):
                event.success = False
                event.error_message = "Safety checks failed"
                return event
            
            # 备份当前状态
            backup_id = self._create_backup(component_type, component_name)
            
            # 调用所有注册的处理器
            for handler in self.reload_handlers[component_type]:
                try:
                    handler(component_type, component_name, metadata)
                except Exception as e:
                    logger.error(f"Handler failed for {component_type}.{component_name}: {e}")
                    # 继续执行其他处理器
            
            # 验证重载结果
            if not self._validate_reload(component_type, component_name):
                # 回滚到备份
                self._rollback_to_backup(component_type, component_name, backup_id)
                event.success = False
                event.error_message = "Reload validation failed, rolled back"
            else:
                event.success = True
                logger.info(f"Successfully reloaded {component_type}.{component_name}")
                
                # 清理旧备份
                self._cleanup_old_backups(component_type, component_name)
            
        except Exception as e:
            event.success = False
            event.error_message = str(e)
            logger.error(f"Failed to reload {component_type}.{component_name}: {e}")
        
        finally:
            event.duration_seconds = (datetime.now() - start_time).total_seconds()
            self._record_event(event)
        
        return event
    
    def _reload_config_handler(self, component_type: str, component_name: str, metadata: Dict[str, Any]):
        """配置重载处理器"""
        logger.info(f"Reloading config: {component_name}")
        # 实际的重载逻辑由调用者实现
        # 这里只是占位符
    
    def _reload_model_handler(self, component_type: str, component_name: str, metadata: Dict[str, Any]):
        """模型重载处理器"""
        logger.info(f"Reloading model: {component_name}")
        # 实际的重载逻辑由调用者实现
        # 这里只是占位符
    
    def _reload_service_handler(self, component_type: str, component_name: str, metadata: Dict[str, Any]):
        """服务重载处理器"""
        logger.info(f"Reloading service: {component_name}")
        # 实际的重载逻辑由调用者实现
        # 这里只是占位符
    
    def _reload_plugin_handler(self, component_type: str, component_name: str, metadata: Dict[str, Any]):
        """插件重载处理器"""
        logger.info(f"Reloading plugin: {component_name}")
        # 实际的重载逻辑由调用者实现
        # 这里只是占位符
    
    def _perform_safety_checks(self, component_type: str, component_name: str, 
                              config: Dict[str, Any]) -> bool:
        """执行安全检查"""
        safety_checks = config.get("safety_checks", {})
        
        if not safety_checks.get("enabled", True):
            return True
        
        # 检查系统状态
        if not self._check_system_health():
            logger.warning("System health check failed")
            return False
        
        # 检查组件状态
        if not self._check_component_health(component_type, component_name):
            logger.warning(f"Component health check failed: {component_type}.{component_name}")
            return False
        
        # 检查依赖关系
        if safety_checks.get("check_dependencies", True):
            if not self._check_dependencies(component_type, component_name):
                logger.warning(f"Dependency check failed: {component_type}.{component_name}")
                return False
        
        # 检查版本兼容性
        if safety_checks.get("check_compatibility", True):
            if not self._check_compatibility(component_type, component_name):
                logger.warning(f"Compatibility check failed: {component_type}.{component_name}")
                return False
        
        return True
    
    def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        # 这里实现实际的健康检查逻辑
        # 例如：检查资源使用率、服务状态等
        return True
    
    def _check_component_health(self, component_type: str, component_name: str) -> bool:
        """检查组件健康状态"""
        # 这里实现实际的组件健康检查逻辑
        return True
    
    def _check_dependencies(self, component_type: str, component_name: str) -> bool:
        """检查依赖关系"""
        # 这里实现实际的依赖检查逻辑
        return True
    
    def _check_compatibility(self, component_type: str, component_name: str) -> bool:
        """检查版本兼容性"""
        # 这里实现实际的兼容性检查逻辑
        return True
    
    def _create_backup(self, component_type: str, component_name: str) -> str:
        """创建备份"""
        backup_id = f"{component_type}_{component_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 这里实现实际的备份逻辑
        # 例如：保存当前状态到备份文件
        
        logger.debug(f"Created backup: {backup_id}")
        return backup_id
    
    def _rollback_to_backup(self, component_type: str, component_name: str, backup_id: str):
        """回滚到备份"""
        logger.info(f"Rolling back {component_type}.{component_name} to backup: {backup_id}")
        
        # 这里实现实际的回滚逻辑
        
        logger.debug(f"Rolled back to backup: {backup_id}")
    
    def _cleanup_old_backups(self, component_type: str, component_name: str):
        """清理旧备份"""
        # 这里实现备份清理逻辑
        # 例如：保留最近的N个备份
        
        pass
    
    def _validate_reload(self, component_type: str, component_name: str) -> bool:
        """验证重载结果"""
        # 这里实现重载验证逻辑
        # 例如：检查组件是否正常运行
        
        return True
    
    def _record_event(self, event: HotReloadEvent):
        """记录事件"""
        self.event_history.append(event)
        
        # 限制历史记录大小
        if len(self.event_history) > self.max_event_history:
            self.event_history = self.event_history[-self.max_event_history:]
    
    def get_event_history(self, limit: int = 100, 
                         component_filter: str = None) -> List[HotReloadEvent]:
        """获取事件历史"""
        events = self.event_history
        
        if component_filter:
            events = [e for e in events if component_filter in e.component]
        
        if limit > 0:
            events = events[-limit:]
        
        return events
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取热重载指标"""
        metrics_config = self.get_config("hot_reload_metrics", {})
        if not metrics_config.get("enabled", False):
            return {}
        
        events = self.event_history
        if not events:
            return {"total_events": 0}
        
        recent_events = [e for e in events if datetime.now() - e.timestamp < timedelta(hours=24)]
        
        total_events = len(events)
        successful_events = sum(1 for e in events if e.success)
        failed_events = total_events - successful_events
        success_rate = successful_events / total_events if total_events > 0 else 0
        
        avg_duration = sum(e.duration_seconds for e in events) / total_events if total_events > 0 else 0
        
        recent_total = len(recent_events)
        recent_successful = sum(1 for e in recent_events if e.success)
        recent_failed = recent_total - recent_successful
        recent_success_rate = recent_successful / recent_total if recent_total > 0 else 0
        
        # 按组件类型统计
        component_stats = {}
        for event in events:
            component = event.component
            if component not in component_stats:
                component_stats[component] = {"total": 0, "successful": 0, "failed": 0}
            
            component_stats[component]["total"] += 1
            if event.success:
                component_stats[component]["successful"] += 1
            else:
                component_stats[component]["failed"] += 1
        
        return {
            "total_events": total_events,
            "successful_events": successful_events,
            "failed_events": failed_events,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "recent_24h": {
                "total": recent_total,
                "successful": recent_successful,
                "failed": recent_failed,
                "success_rate": recent_success_rate
            },
            "component_statistics": component_stats,
            "last_event": events[-1].to_dict() if events else None
        }
    
    def get_config_hash(self, config_name: str) -> str:
        """获取配置哈希值"""
        if config_name not in self.configs:
            return ""
        
        config_data = self.configs[config_name]
        config_json = json.dumps(config_data, sort_keys=True, default=str)
        
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]
    
    def watch_for_changes(self, watch_interval: int = 5):
        """监视配置变化"""
        # 这里实现文件监视逻辑
        # 例如：使用 watchdog 库监视配置文件变化
        
        logger.info(f"Started watching for config changes (interval: {watch_interval}s)")
        
        # 注意：这是一个简化的实现
        # 实际实现应该使用适当的文件监视机制
        initial_hashes = {
            config_name: self.get_config_hash(config_name)
            for config_name in self.configs.keys()
        }
        
        return initial_hashes
    
    def check_for_changes(self, initial_hashes: Dict[str, str]) -> List[str]:
        """检查配置变化"""
        changed_configs = []
        
        for config_name, initial_hash in initial_hashes.items():
            current_hash = self.get_config_hash(config_name)
            if current_hash != initial_hash:
                changed_configs.append(config_name)
                logger.info(f"Config changed: {config_name}")
        
        return changed_configs

# 全局热重载管理器实例
_hot_reload_manager = None

def get_hot_reload_manager(config_dir: Path = None) -> HotReloadManager:
    """获取全局热重载管理器实例"""
    global _hot_reload_manager
    
    if _hot_reload_manager is None:
        _hot_reload_manager = HotReloadManager(config_dir)
    
    return _hot_reload_manager

def trigger_hot_reload(component_type: str, component_name: str, 
                      metadata: Dict[str, Any] = None) -> HotReloadEvent:
    """触发热重载（便捷函数）"""
    return get_hot_reload_manager().trigger_reload(component_type, component_name, metadata)

def get_hot_reload_config(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取热重载配置（便捷函数）"""
    return get_hot_reload_manager().get_config(config_name, key, default)

def get_hot_reload_metrics() -> Dict[str, Any]:
    """获取热重载指标（便捷函数）"""
    return get_hot_reload_manager().get_metrics()

def register_hot_reload_handler(component_type: str, handler: Callable):
    """注册热重载处理器（便捷函数）"""
    get_hot_reload_manager().register_handler(component_type, handler)

__all__ = [
    'HotReloadManager',
    'HotReloadEvent',
    'get_hot_reload_manager',
    'trigger_hot_reload',
    'get_hot_reload_config',
    'get_hot_reload_metrics',
    'register_hot_reload_handler'
]
