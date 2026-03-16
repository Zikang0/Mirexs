"""
Mirexs 动态配置模块
提供运行时动态调整系统参数的功能
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import logging

logger = logging.getLogger("mirexs.config.runtime.dynamic")

class DynamicConfigManager:
    """动态配置管理器"""
    
    def __init__(self, config_dir: Path = None):
        """
        初始化动态配置管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.configs = {}
        self._load_configs()
    
    def _load_configs(self):
        """加载所有动态配置文件"""
        config_files = [
            "performance_tuning.yaml",
            "resource_allocation.yaml",
            "adaptive_learning.yaml",
            "realtime_optimization.yaml",
            "dynamic_scaling.yaml"
        ]
        
        for config_file in config_files:
            config_path = self.config_dir / config_file
            config_name = config_path.stem
            
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.configs[config_name] = config_data
                        logger.debug(f"Loaded dynamic config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load dynamic config {config_file}: {e}")
            else:
                logger.warning(f"Dynamic config file not found: {config_file}")
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
            
            logger.debug(f"Saved dynamic config: {config_name}")
            
        except Exception as e:
            logger.error(f"Failed to save dynamic config {config_name}: {e}")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        return self.configs.copy()
    
    def reset_config(self, config_name: str):
        """重置配置为默认值"""
        default_configs = {
            "performance_tuning": {
                "enabled": True,
                "auto_tuning": True,
                "tuning_interval": 300
            },
            "resource_allocation": {
                "enabled": True,
                "allocation_strategy": "dynamic_weighted"
            },
            "adaptive_learning": {
                "enabled": True,
                "learning_modes": {
                    "supervised": True,
                    "reinforcement": True
                }
            },
            "realtime_optimization": {
                "enabled": True,
                "latency_targets": {
                    "speech_recognition": 200,
                    "text_generation": 500
                }
            },
            "dynamic_scaling": {
                "enabled": True,
                "scaling_policies": {
                    "cpu_utilization": {
                        "scale_up_threshold": 0.8,
                        "scale_down_threshold": 0.3
                    }
                }
            }
        }
        
        if config_name in default_configs:
            self.configs[config_name] = default_configs[config_name]
            self._save_config(config_name)
        else:
            logger.warning(f"No default config for: {config_name}")

# 全局动态配置管理器实例
_dynamic_config_manager = None

def get_dynamic_config_manager(config_dir: Path = None) -> DynamicConfigManager:
    """获取全局动态配置管理器实例"""
    global _dynamic_config_manager
    
    if _dynamic_config_manager is None:
        _dynamic_config_manager = DynamicConfigManager(config_dir)
    
    return _dynamic_config_manager

def get_dynamic_config_value(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取动态配置值（便捷函数）"""
    return get_dynamic_config_manager().get_config(config_name, key, default)

def update_dynamic_config(config_name: str, updates: Dict[str, Any], save: bool = True):
    """更新动态配置（便捷函数）"""
    get_dynamic_config_manager().update_config(config_name, updates, save)

__all__ = [
    'DynamicConfigManager',
    'get_dynamic_config_manager',
    'get_dynamic_config_value',
    'update_dynamic_config'
]