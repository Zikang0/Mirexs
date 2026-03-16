"""
Mirexs 性能调优配置模块
提供系统性能优化参数配置
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import logging

logger = logging.getLogger("mirexs.config.runtime.performance")

class PerformanceTuningManager:
    """性能调优管理器"""
    
    def __init__(self, config_dir: Path = None):
        """
        初始化性能调优管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载所有性能调优配置文件"""
        config_files = [
            "cache_strategies.yaml",
            "memory_management.yaml",
            "cpu_optimization.yaml",
            "gpu_optimization.yaml",
            "network_optimization.yaml"
        ]
        
        for config_file in config_files:
            config_path = self.config_dir / config_file
            config_name = config_path.stem
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.configs[config_name] = config_data
                        logger.debug(f"Loaded performance config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load performance config {config_file}: {e}")
            else:
                logger.warning(f"Performance config file not found: {config_file}")
                self.configs[config_name] = {}
    
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
    
    def get_cache_config(self, cache_level: str = None) -> Dict[str, Any]:
        """获取缓存配置"""
        cache_config = self.get_config("cache_strategies", {})
        
        if cache_level:
            cache_levels = cache_config.get("cache_levels", {})
            return cache_levels.get(cache_level, {})
        
        return cache_config
    
    def get_memory_config(self, memory_type: str = None) -> Dict[str, Any]:
        """获取内存配置"""
        memory_config = self.get_config("memory_management", {})
        
        if memory_type:
            allocation_strategies = memory_config.get("allocation_strategies", {})
            return allocation_strategies.get(memory_type, {})
        
        return memory_config
    
    def get_cpu_config(self) -> Dict[str, Any]:
        """获取CPU配置"""
        return self.get_config("cpu_optimization", {})
    
    def get_gpu_config(self) -> Dict[str, Any]:
        """获取GPU配置"""
        return self.get_config("gpu_optimization", {})
    
    def get_network_config(self) -> Dict[str, Any]:
        """获取网络配置"""
        return self.get_config("network_optimization", {})
    
    def update_config(self, config_name: str, updates: Dict[str, Any], save: bool = True):
        """更新配置"""
        if config_name not in self.configs:
            self.configs[config_name] = {}
        
        self._update_nested_dict(self.configs[config_name], updates)
        
        if save:
            self._save_config(config_name)
    
    def _update_nested_dict(self, target: Dict[str, Any], updates: Dict[str, Any]):
        """递归更新嵌套字典"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def _save_config(self, config_name: str):
        """保存配置到文件"""
        if config_name not in self.configs:
            return
        
        config_path = self.config_dir / f"{config_name}.yaml"
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.configs[config_name], f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.debug(f"Saved performance config: {config_name}")
            
        except Exception as e:
            logger.error(f"Failed to save performance config {config_name}: {e}")
    
    def get_optimization_profile(self, profile_name: str) -> Dict[str, Any]:
        """获取优化配置集"""
        profiles = {
            "performance": {
                "cache_strategies": {
                    "cache_levels": {
                        "l1": {"size_mb": 1024},
                        "l2": {"size_mb": 20480},
                        "l3": {"size_mb": 204800}
                    }
                },
                "cpu_optimization": {
                    "core_allocation": {"reserved_cores": 0}
                }
            },
            "balanced": {
                "cache_strategies": {
                    "cache_levels": {
                        "l1": {"size_mb": 512},
                        "l2": {"size_mb": 10240},
                        "l3": {"size_mb": 102400}
                    }
                },
                "cpu_optimization": {
                    "core_allocation": {"reserved_cores": 1}
                }
            },
            "memory_saver": {
                "cache_strategies": {
                    "cache_levels": {
                        "l1": {"size_mb": 256},
                        "l2": {"size_mb": 5120},
                        "l3": {"size_mb": 51200}
                    }
                },
                "memory_management": {
                    "garbage_collection": {"gc_threshold": 0.7}
                }
            }
        }
        
        return profiles.get(profile_name, {})
    
    def apply_optimization_profile(self, profile_name: str):
        """应用优化配置集"""
        profile = self.get_optimization_profile(profile_name)
        
        if not profile:
            logger.warning(f"Unknown optimization profile: {profile_name}")
            return
        
        for config_name, config_updates in profile.items():
            self.update_config(config_name, config_updates)
        
        logger.info(f"Applied optimization profile: {profile_name}")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        return self.configs.copy()
    
    def validate_configs(self) -> List[str]:
        """验证所有配置"""
        errors = []
        
        # 验证缓存配置
        cache_config = self.get_config("cache_strategies", {})
        if cache_config.get("enabled", False):
            cache_levels = cache_config.get("cache_levels", {})
            for level, level_config in cache_levels.items():
                if "size_mb" in level_config and level_config["size_mb"] <= 0:
                    errors.append(f"cache_strategies.cache_levels.{level}.size_mb must be positive")
        
        # 验证内存配置
        memory_config = self.get_config("memory_management", {})
        if memory_config.get("enabled", False):
            gc_config = memory_config.get("garbage_collection", {})
            if gc_config.get("gc_threshold", 0) <= 0 or gc_config.get("gc_threshold", 0) > 1:
                errors.append("memory_management.garbage_collection.gc_threshold must be between 0 and 1")
        
        return errors

# 全局性能调优管理器实例
_performance_tuning_manager = None

def get_performance_tuning_manager(config_dir: Path = None) -> PerformanceTuningManager:
    """获取全局性能调优管理器实例"""
    global _performance_tuning_manager
    
    if _performance_tuning_manager is None:
        _performance_tuning_manager = PerformanceTuningManager(config_dir)
    
    return _performance_tuning_manager

def get_performance_config_value(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取性能配置值（便捷函数）"""
    return get_performance_tuning_manager().get_config(config_name, key, default)

def update_performance_config(config_name: str, updates: Dict[str, Any], save: bool = True):
    """更新性能配置（便捷函数）"""
    get_performance_tuning_manager().update_config(config_name, updates, save)

def apply_optimization_profile(profile_name: str):
    """应用优化配置集（便捷函数）"""
    get_performance_tuning_manager().apply_optimization_profile(profile_name)

__all__ = [
    'PerformanceTuningManager',
    'get_performance_tuning_manager',
    'get_performance_config_value',
    'update_performance_config',
    'apply_optimization_profile'
]