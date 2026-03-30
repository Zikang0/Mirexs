"""
Mirexs 运行时配置模块
提供系统运行时动态配置、性能调优和热重载功能
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import yaml
import json
from datetime import datetime
import logging

# 运行时配置日志
logger = logging.getLogger("mirexs.config.runtime")

class RuntimeConfigMode(Enum):
    """运行时配置模式"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    DEBUG = "debug"
    BENCHMARK = "benchmark"

class RuntimeConfigSource(Enum):
    """配置来源"""
    FILE = "file"
    ENV = "environment"
    API = "api"
    HOT_RELOAD = "hot_reload"

@dataclass
class RuntimeConfigState:
    """运行时配置状态"""
    mode: RuntimeConfigMode = RuntimeConfigMode.DEVELOPMENT
    last_updated: datetime = field(default_factory=datetime.now)
    source: RuntimeConfigSource = RuntimeConfigSource.FILE
    version: str = "2.0.0"
    checksum: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

class RuntimeConfigManager:
    """运行时配置管理器"""
    
    def __init__(self, config_dir: Path = None):
        """
        初始化运行时配置管理器
        
        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = config_dir or Path(__file__).parent
        self.state = RuntimeConfigState()
        self.dynamic_configs = {}
        self.performance_configs = {}
        self.hot_reload_configs = {}
        self.observers = []
        
        # 初始化配置文件
        self._init_config_directories()
        self._load_all_configs()
        
        logger.info(f"RuntimeConfigManager initialized in mode: {self.state.mode.value}")
    
    def _init_config_directories(self):
        """初始化配置目录"""
        directories = [
            self.config_dir / "dynamic_config",
            self.config_dir / "performance_tuning",
            self.config_dir / "hot_reload"
        ]
        
        for dir_path in directories:
            dir_path.mkdir(exist_ok=True, parents=True)
    
    def _load_all_configs(self):
        """加载所有配置文件"""
        try:
            # 加载动态配置
            self._load_dynamic_configs()
            
            # 加载性能调优配置
            self._load_performance_configs()
            
            # 加载热重载配置
            self._load_hot_reload_configs()
            
            logger.info("All runtime configs loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load runtime configs: {e}")
            self.state.is_valid = False
            self.state.validation_errors.append(str(e))
    
    def _load_dynamic_configs(self):
        """加载动态配置文件"""
        dynamic_dir = self.config_dir / "dynamic_config"
        
        config_files = {
            "performance_tuning": dynamic_dir / "performance_tuning.yaml",
            "resource_allocation": dynamic_dir / "resource_allocation.yaml",
            "adaptive_learning": dynamic_dir / "adaptive_learning.yaml",
            "realtime_optimization": dynamic_dir / "realtime_optimization.yaml",
            "dynamic_scaling": dynamic_dir / "dynamic_scaling.yaml"
        }
        
        for config_name, config_path in config_files.items():
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.dynamic_configs[config_name] = config_data
                        logger.debug(f"Loaded dynamic config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load {config_name}: {e}")
                    self.state.validation_errors.append(f"{config_name}: {e}")
            else:
                # 创建默认配置文件
                default_config = self._create_default_dynamic_config(config_name)
                self._save_config(config_path, default_config)
                self.dynamic_configs[config_name] = default_config
    
    def _load_performance_configs(self):
        """加载性能调优配置"""
        perf_dir = self.config_dir / "performance_tuning"
        
        config_files = {
            "cache_strategies": perf_dir / "cache_strategies.yaml",
            "memory_management": perf_dir / "memory_management.yaml",
            "cpu_optimization": perf_dir / "cpu_optimization.yaml",
            "gpu_optimization": perf_dir / "gpu_optimization.yaml",
            "network_optimization": perf_dir / "network_optimization.yaml"
        }
        
        for config_name, config_path in config_files.items():
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.performance_configs[config_name] = config_data
                        logger.debug(f"Loaded performance config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load {config_name}: {e}")
                    self.state.validation_errors.append(f"{config_name}: {e}")
            else:
                # 创建默认配置文件
                default_config = self._create_default_performance_config(config_name)
                self._save_config(config_path, default_config)
                self.performance_configs[config_name] = default_config
    
    def _load_hot_reload_configs(self):
        """加载热重载配置"""
        hot_reload_dir = self.config_dir / "hot_reload"
        
        config_files = {
            "config_reload": hot_reload_dir / "config_reload.yaml",
            "model_reload": hot_reload_dir / "model_reload.yaml",
            "service_reload": hot_reload_dir / "service_reload.yaml",
            "plugin_reload": hot_reload_dir / "plugin_reload.yaml",
            "hot_reload_metrics": hot_reload_dir / "hot_reload_metrics.yaml"
        }
        
        for config_name, config_path in config_files.items():
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                        self.hot_reload_configs[config_name] = config_data
                        logger.debug(f"Loaded hot reload config: {config_name}")
                except Exception as e:
                    logger.error(f"Failed to load {config_name}: {e}")
                    self.state.validation_errors.append(f"{config_name}: {e}")
            else:
                # 创建默认配置文件
                default_config = self._create_default_hot_reload_config(config_name)
                self._save_config(config_path, default_config)
                self.hot_reload_configs[config_name] = default_config
    
    def _create_default_dynamic_config(self, config_type: str) -> Dict[str, Any]:
        """创建默认动态配置"""
        defaults = {
            "performance_tuning": {
                "enabled": True,
                "auto_tuning": True,
                "tuning_interval": 300,  # 5分钟
                "max_iterations": 100,
                "tolerance": 0.01,
                "strategies": {
                    "inference": {
                        "batch_size": {
                            "min": 1,
                            "max": 64,
                            "default": 16
                        },
                        "precision": ["float32", "float16", "bfloat16"],
                        "threads": {
                            "cpu": 4,
                            "io": 2
                        }
                    },
                    "rendering": {
                        "quality_presets": ["low", "medium", "high", "ultra"],
                        "fps_target": 60,
                        "adaptive_resolution": True
                    },
                    "data_processing": {
                        "chunk_size": 1024,
                        "prefetch_factor": 2,
                        "num_workers": 4
                    }
                }
            },
            "resource_allocation": {
                "enabled": True,
                "allocation_strategy": "dynamic_weighted",
                "resources": {
                    "cpu": {
                        "min_cores": 1,
                        "max_cores": "auto",
                        "priority": "medium"
                    },
                    "memory": {
                        "min_gb": 2,
                        "max_gb": "auto",
                        "reserved_percent": 10
                    },
                    "gpu": {
                        "enabled": True,
                        "min_memory_mb": 1024,
                        "priority_tasks": ["inference", "rendering"]
                    },
                    "disk": {
                        "cache_size_gb": 10,
                        "temp_space_gb": 20
                    }
                },
                "scheduling": {
                    "task_priority": {
                        "critical": 10,
                        "high": 7,
                        "medium": 5,
                        "low": 3,
                        "background": 1
                    },
                    "preemption_enabled": True
                }
            },
            "adaptive_learning": {
                "enabled": True,
                "learning_modes": {
                    "supervised": True,
                    "reinforcement": True,
                    "unsupervised": False,
                    "transfer": True
                },
                "parameters": {
                    "learning_rate": {
                        "initial": 0.001,
                        "decay_rate": 0.95,
                        "decay_steps": 1000,
                        "min_lr": 1e-6
                    },
                    "regularization": {
                        "l1_lambda": 0.01,
                        "l2_lambda": 0.001,
                        "dropout_rate": 0.2
                    },
                    "optimization": {
                        "optimizer": "adam",
                        "momentum": 0.9,
                        "beta1": 0.9,
                        "beta2": 0.999,
                        "epsilon": 1e-8
                    }
                },
                "adaptation_strategies": {
                    "exploration_exploitation": {
                        "epsilon": 0.1,
                        "decay": 0.99,
                        "min_epsilon": 0.01
                    },
                    "curriculum_learning": {
                        "enabled": True,
                        "difficulty_steps": 10,
                        "progression_rate": 0.1
                    }
                }
            },
            "realtime_optimization": {
                "enabled": True,
                "latency_targets": {
                    "speech_recognition": 200,  # ms
                    "text_generation": 500,
                    "image_processing": 300,
                    "3d_rendering": 16.67,  # 60 FPS
                    "database_query": 100
                },
                "optimization_strategies": {
                    "caching": {
                        "enabled": True,
                        "ttl_seconds": 300,
                        "max_size_mb": 1024,
                        "eviction_policy": "lru"
                    },
                    "batching": {
                        "enabled": True,
                        "max_batch_size": 64,
                        "timeout_ms": 50
                    },
                    "pipelining": {
                        "enabled": True,
                        "stages": 3,
                        "buffer_size": 100
                    }
                },
                "monitoring": {
                    "sampling_rate": 1.0,  # 100%
                    "metrics_interval": 60,  # seconds
                    "alert_threshold": 0.9  # 90% utilization
                }
            },
            "dynamic_scaling": {
                "enabled": True,
                "scaling_policies": {
                    "cpu_utilization": {
                        "scale_up_threshold": 0.8,
                        "scale_down_threshold": 0.3,
                        "scale_up_factor": 1.5,
                        "scale_down_factor": 0.7,
                        "cooldown_seconds": 300
                    },
                    "memory_utilization": {
                        "scale_up_threshold": 0.85,
                        "scale_down_threshold": 0.4,
                        "scale_up_factor": 2.0,
                        "scale_down_factor": 0.8
                    },
                    "request_rate": {
                        "scale_up_threshold": 1000,  # requests/second
                        "scale_down_threshold": 200,
                        "scale_up_factor": 1.8,
                        "scale_down_factor": 0.6
                    }
                },
                "scaling_limits": {
                    "min_instances": 1,
                    "max_instances": 10,
                    "min_resources": {
                        "cpu": 1,
                        "memory_gb": 2,
                        "gpu": 0
                    },
                    "max_resources": {
                        "cpu": 16,
                        "memory_gb": 64,
                        "gpu": 2
                    }
                }
            }
        }
        
        return defaults.get(config_type, {})
    
    def _create_default_performance_config(self, config_type: str) -> Dict[str, Any]:
        """创建默认性能调优配置"""
        defaults = {
            "cache_strategies": {
                "enabled": True,
                "cache_levels": {
                    "l1": {
                        "type": "memory",
                        "size_mb": 512,
                        "eviction_policy": "lru",
                        "ttl_seconds": 60
                    },
                    "l2": {
                        "type": "disk",
                        "size_mb": 10240,
                        "eviction_policy": "lru",
                        "ttl_seconds": 300
                    },
                    "l3": {
                        "type": "redis",
                        "size_mb": 102400,
                        "eviction_policy": "volatile-lru",
                        "ttl_seconds": 3600
                    }
                },
                "caching_policies": {
                    "ai_models": {
                        "cache_weights": True,
                        "cache_embeddings": True,
                        "cache_results": True,
                        "compression": "zstd"
                    },
                    "user_data": {
                        "cache_profiles": True,
                        "cache_preferences": True,
                        "cache_history": True,
                        "encryption": True
                    },
                    "rendering": {
                        "cache_textures": True,
                        "cache_shaders": True,
                        "cache_meshes": True
                    }
                },
                "optimization": {
                    "prefetch_enabled": True,
                    "prefetch_distance": 5,
                    "compression_enabled": True,
                    "compression_algorithm": "zstd",
                    "compression_level": 3
                }
            },
            "memory_management": {
                "enabled": True,
                "allocation_strategies": {
                    "ai_models": {
                        "memory_pool": True,
                        "chunk_size_mb": 256,
                        "alignment": 256
                    },
                    "rendering": {
                        "memory_pool": True,
                        "chunk_size_mb": 128,
                        "alignment": 128
                    },
                    "data_processing": {
                        "memory_pool": True,
                        "chunk_size_mb": 64,
                        "alignment": 64
                    }
                },
                "garbage_collection": {
                    "enabled": True,
                    "strategy": "generational",
                    "gc_threshold": 0.8,
                    "full_gc_interval": 3600,
                    "min_free_memory_mb": 1024
                },
                "swap_management": {
                    "swap_enabled": False,
                    "swap_path": "/tmp/mirexs_swap",
                    "max_swap_gb": 20,
                    "swapiness": 10
                }
            },
            "cpu_optimization": {
                "enabled": True,
                "core_allocation": {
                    "strategy": "dynamic",
                    "reserved_cores": 1,
                    "affinity_enabled": True,
                    "isolated_cores": []
                },
                "scheduling": {
                    "scheduler": "cfs",
                    "priority_levels": {
                        "realtime": 99,
                        "high": 80,
                        "normal": 50,
                        "low": 20,
                        "idle": 1
                    },
                    "cpu_quota_us": 100000,  # 100ms
                    "cpu_period_us": 1000000  # 1s
                },
                "optimization_techniques": {
                    "vectorization": True,
                    "parallelization": True,
                    "branch_prediction": True,
                    "cache_prefetching": True,
                    "instruction_pipelining": True
                }
            },
            "gpu_optimization": {
                "enabled": True,
                "device_selection": {
                    "strategy": "auto",
                    "preferred_devices": ["cuda:0"],
                    "fallback_devices": ["cpu"]
                },
                "memory_management": {
                    "memory_pool": True,
                    "max_split_size_mb": 256,
                    "cache_allocator": True,
                    "fragmentation_threshold": 0.1
                },
                "kernel_optimization": {
                    "autotune": True,
                    "max_workspace_size_mb": 1024,
                    "kernel_cache": True,
                    "tensor_cores": True
                },
                "pipeline_optimization": {
                    "overlap_compute_copy": True,
                    "streams": 4,
                    "event_sync": True,
                    "graph_capture": True
                }
            },
            "network_optimization": {
                "enabled": True,
                "tcp_optimization": {
                    "tcp_congestion": "bbr",
                    "tcp_window_scaling": True,
                    "tcp_timestamps": True,
                    "tcp_sack": True,
                    "tcp_fast_open": True
                },
                "bandwidth_management": {
                    "qos_enabled": True,
                    "traffic_classes": {
                        "realtime": {
                            "priority": 7,
                            "bandwidth_percent": 40,
                            "latency_ms": 20
                        },
                        "interactive": {
                            "priority": 5,
                            "bandwidth_percent": 30,
                            "latency_ms": 100
                        },
                        "bulk": {
                            "priority": 3,
                            "bandwidth_percent": 20,
                            "latency_ms": 500
                        },
                        "background": {
                            "priority": 1,
                            "bandwidth_percent": 10,
                            "latency_ms": 1000
                        }
                    }
                },
                "connection_pooling": {
                    "enabled": True,
                    "max_pool_size": 100,
                    "max_connections_per_host": 10,
                    "connection_timeout": 30,
                    "keepalive": True,
                    "keepalive_idle": 60,
                    "keepalive_interval": 30,
                    "keepalive_count": 5
                }
            }
        }
        
        return defaults.get(config_type, {})
    
    def _create_default_hot_reload_config(self, config_type: str) -> Dict[str, Any]:
        """创建默认热重载配置"""
        defaults = {
            "config_reload": {
                "enabled": True,
                "reload_strategies": {
                    "full_reload": {
                        "enabled": True,
                        "trigger": "file_change",
                        "check_interval": 5
                    },
                    "partial_reload": {
                        "enabled": True,
                        "trigger": "api_request",
                        "validate_before_reload": True
                    },
                    "incremental_reload": {
                        "enabled": True,
                        "trigger": "config_change",
                        "track_changes": True
                    }
                },
                "safety_checks": {
                    "validation_enabled": True,
                    "backup_before_reload": True,
                    "rollback_on_failure": True,
                    "max_rollback_attempts": 3
                },
                "notification": {
                    "notify_on_reload": True,
                    "notification_channels": ["log", "event"],
                    "log_level": "info"
                }
            },
            "model_reload": {
                "enabled": True,
                "reload_triggers": {
                    "file_change": True,
                    "version_update": True,
                    "performance_degradation": True,
                    "manual_request": True
                },
                "reload_strategies": {
                    "hot_swap": {
                        "enabled": True,
                        "keep_old_version": True,
                        "drain_connections": True
                    },
                    "version_switch": {
                        "enabled": True,
                        "version_check_interval": 60,
                        "auto_rollback": True
                    },
                    "canary_deployment": {
                        "enabled": False,
                        "traffic_percentage": 10,
                        "evaluation_period": 300
                    }
                },
                "model_management": {
                    "cache_models": True,
                    "model_format": "onnx",
                    "compression": "quantization",
                    "quantization_bits": 8
                }
            },
            "service_reload": {
                "enabled": True,
                "reload_scopes": {
                    "microservices": True,
                    "background_services": True,
                    "scheduled_tasks": True,
                    "api_endpoints": True
                },
                "reload_methods": {
                    "rolling_restart": {
                        "enabled": True,
                        "batch_size": 1,
                        "delay_between_batches": 30
                    },
                    "blue_green": {
                        "enabled": False,
                        "traffic_switch_delay": 60
                    },
                    "drain_and_refill": {
                        "enabled": True,
                        "drain_timeout": 300,
                        "connection_drain": True
                    }
                },
                "dependency_management": {
                    "check_dependencies": True,
                    "dependency_graph": True,
                    "order_of_operations": True
                }
            },
            "plugin_reload": {
                "enabled": True,
                "reload_policies": {
                    "automatic": {
                        "enabled": True,
                        "detect_changes": True,
                        "reload_on_change": True
                    },
                    "manual": {
                        "enabled": True,
                        "api_endpoint": "/api/plugins/reload",
                        "require_auth": True
                    },
                    "scheduled": {
                        "enabled": False,
                        "schedule": "0 2 * * *",  # 每天凌晨2点
                        "reload_all": False
                    }
                },
                "isolation": {
                    "sandbox_enabled": True,
                    "resource_limits": True,
                    "permission_boundaries": True
                },
                "version_management": {
                    "version_check": True,
                    "compatibility_check": True,
                    "downgrade_protection": True
                }
            },
            "hot_reload_metrics": {
                "enabled": True,
                "metrics_collection": {
                    "reload_frequency": True,
                    "reload_duration": True,
                    "success_rate": True,
                    "error_rate": True,
                    "performance_impact": True
                },
                "metrics_storage": {
                    "storage_backend": "prometheus",
                    "retention_days": 30,
                    "sampling_interval": 60
                },
                "alerting": {
                    "alert_on_failure": True,
                    "failure_threshold": 3,
                    "alert_on_performance_degradation": True,
                    "degradation_threshold": 0.2  # 20% performance drop
                },
                "analytics": {
                    "collect_analytics": True,
                    "anonymize_data": True,
                    "reporting_interval": 3600
                }
            }
        }
        
        return defaults.get(config_type, {})
    
    def _save_config(self, config_path: Path, config_data: Dict[str, Any]):
        """保存配置文件"""
        try:
            # 确保目录存在
            config_path.parent.mkdir(exist_ok=True, parents=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.debug(f"Saved config to: {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            raise
    
    def get_dynamic_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """获取动态配置"""
        if config_name not in self.dynamic_configs:
            logger.warning(f"Dynamic config not found: {config_name}")
            return default
        
        config = self.dynamic_configs[config_name]
        
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
    
    def get_performance_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """获取性能配置"""
        if config_name not in self.performance_configs:
            logger.warning(f"Performance config not found: {config_name}")
            return default
        
        config = self.performance_configs[config_name]
        
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
    
    def get_hot_reload_config(self, config_name: str, key: str = None, default: Any = None) -> Any:
        """获取热重载配置"""
        if config_name not in self.hot_reload_configs:
            logger.warning(f"Hot reload config not found: {config_name}")
            return default
        
        config = self.hot_reload_configs[config_name]
        
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
    
    def update_dynamic_config(self, config_name: str, updates: Dict[str, Any], save: bool = True):
        """更新动态配置"""
        if config_name not in self.dynamic_configs:
            self.dynamic_configs[config_name] = {}
        
        self._update_nested_dict(self.dynamic_configs[config_name], updates)
        
        if save:
            config_path = self.config_dir / "dynamic_config" / f"{config_name}.yaml"
            self._save_config(config_path, self.dynamic_configs[config_name])
        
        self._notify_observers("dynamic_config", config_name, updates)
        self.state.last_updated = datetime.now()
        self.state.source = RuntimeConfigSource.HOT_RELOAD
    
    def update_performance_config(self, config_name: str, updates: Dict[str, Any], save: bool = True):
        """更新性能配置"""
        if config_name not in self.performance_configs:
            self.performance_configs[config_name] = {}
        
        self._update_nested_dict(self.performance_configs[config_name], updates)
        
        if save:
            config_path = self.config_dir / "performance_tuning" / f"{config_name}.yaml"
            self._save_config(config_path, self.performance_configs[config_name])
        
        self._notify_observers("performance_config", config_name, updates)
        self.state.last_updated = datetime.now()
        self.state.source = RuntimeConfigSource.HOT_RELOAD
    
    def update_hot_reload_config(self, config_name: str, updates: Dict[str, Any], save: bool = True):
        """更新热重载配置"""
        if config_name not in self.hot_reload_configs:
            self.hot_reload_configs[config_name] = {}
        
        self._update_nested_dict(self.hot_reload_configs[config_name], updates)
        
        if save:
            config_path = self.config_dir / "hot_reload" / f"{config_name}.yaml"
            self._save_config(config_path, self.hot_reload_configs[config_name])
        
        self._notify_observers("hot_reload_config", config_name, updates)
        self.state.last_updated = datetime.now()
        self.state.source = RuntimeConfigSource.HOT_RELOAD
    
    def _update_nested_dict(self, target: Dict[str, Any], updates: Dict[str, Any]):
        """递归更新嵌套字典"""
        for key, value in updates.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def register_observer(self, callback):
        """注册配置变化观察者"""
        if callback not in self.observers:
            self.observers.append(callback)
    
    def unregister_observer(self, callback):
        """取消注册观察者"""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def _notify_observers(self, config_type: str, config_name: str, changes: Dict[str, Any]):
        """通知观察者配置变化"""
        for observer in self.observers:
            try:
                observer(config_type, config_name, changes)
            except Exception as e:
                logger.error(f"Observer callback failed: {e}")
    
    def set_mode(self, mode: RuntimeConfigMode):
        """设置运行时模式"""
        self.state.mode = mode
        logger.info(f"Runtime config mode changed to: {mode.value}")
        
        # 根据模式调整配置
        self._adjust_configs_for_mode(mode)
    
    def _adjust_configs_for_mode(self, mode: RuntimeConfigMode):
        """根据模式调整配置"""
        mode_adjustments = {
            RuntimeConfigMode.DEVELOPMENT: {
                "dynamic_config.performance_tuning.auto_tuning": False,
                "dynamic_config.realtime_optimization.latency_targets.speech_recognition": 500,
                "performance_tuning.cache_strategies.cache_levels.l1.size_mb": 256,
                "hot_reload.config_reload.reload_strategies.full_reload.check_interval": 2
            },
            RuntimeConfigMode.PRODUCTION: {
                "dynamic_config.performance_tuning.auto_tuning": True,
                "dynamic_config.realtime_optimization.latency_targets.speech_recognition": 200,
                "performance_tuning.cache_strategies.cache_levels.l1.size_mb": 512,
                "hot_reload.config_reload.reload_strategies.full_reload.check_interval": 10
            },
            RuntimeConfigMode.DEBUG: {
                "dynamic_config.performance_tuning.auto_tuning": False,
                "dynamic_config.realtime_optimization.latency_targets.speech_recognition": 1000,
                "performance_tuning.cache_strategies.cache_levels.l1.size_mb": 128,
                "hot_reload.config_reload.reload_strategies.full_reload.check_interval": 1
            }
        }
        
        adjustments = mode_adjustments.get(mode, {})
        
        for config_key, value in adjustments.items():
            try:
                parts = config_key.split('.')
                config_type = parts[0]
                config_name = parts[1]
                key = '.'.join(parts[2:])
                
                if config_type == "dynamic_config":
                    self.update_dynamic_config(config_name, {key: value}, save=False)
                elif config_type == "performance_tuning":
                    self.update_performance_config(config_name, {key: value}, save=False)
                elif config_type == "hot_reload":
                    self.update_hot_reload_config(config_name, {key: value}, save=False)
                    
            except Exception as e:
                logger.error(f"Failed to apply mode adjustment {config_key}: {e}")
    
    def reload_all_configs(self):
        """重新加载所有配置"""
        logger.info("Reloading all runtime configs...")
        self._load_all_configs()
        self.state.source = RuntimeConfigSource.HOT_RELOAD
        self.state.last_updated = datetime.now()
        
        # 通知观察者
        self._notify_observers("all", "all", {"reload": True})
    
    def export_configs(self, export_dir: Path) -> Dict[str, Path]:
        """导出所有配置文件"""
        export_dir.mkdir(exist_ok=True, parents=True)
        
        exported_files = {}
        
        # 导出动态配置
        dynamic_export_dir = export_dir / "dynamic_config"
        dynamic_export_dir.mkdir(exist_ok=True)
        
        for config_name, config_data in self.dynamic_configs.items():
            export_path = dynamic_export_dir / f"{config_name}.yaml"
            self._save_config(export_path, config_data)
            exported_files[f"dynamic_config.{config_name}"] = export_path
        
        # 导出性能配置
        perf_export_dir = export_dir / "performance_tuning"
        perf_export_dir.mkdir(exist_ok=True)
        
        for config_name, config_data in self.performance_configs.items():
            export_path = perf_export_dir / f"{config_name}.yaml"
            self._save_config(export_path, config_data)
            exported_files[f"performance_tuning.{config_name}"] = export_path
        
        # 导出热重载配置
        hot_reload_export_dir = export_dir / "hot_reload"
        hot_reload_export_dir.mkdir(exist_ok=True)
        
        for config_name, config_data in self.hot_reload_configs.items():
            export_path = hot_reload_export_dir / f"{config_name}.yaml"
            self._save_config(export_path, config_data)
            exported_files[f"hot_reload.{config_name}"] = export_path
        
        # 导出元数据
        metadata = {
            "export_time": datetime.now().isoformat(),
            "config_state": {
                "mode": self.state.mode.value,
                "last_updated": self.state.last_updated.isoformat(),
                "source": self.state.source.value,
                "version": self.state.version,
                "is_valid": self.state.is_valid
            },
            "exported_files": list(exported_files.keys())
        }
        
        metadata_path = export_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        exported_files["metadata"] = metadata_path
        
        logger.info(f"Exported {len(exported_files)} config files to {export_dir}")
        return exported_files
    
    def validate_configs(self) -> Dict[str, List[str]]:
        """验证所有配置"""
        validation_results = {}
        
        # 验证动态配置
        validation_results["dynamic_config"] = self._validate_dynamic_configs()
        
        # 验证性能配置
        validation_results["performance_tuning"] = self._validate_performance_configs()
        
        # 验证热重载配置
        validation_results["hot_reload"] = self._validate_hot_reload_configs()
        
        # 更新状态
        all_errors = []
        for category, errors in validation_results.items():
            all_errors.extend(errors)
        
        self.state.is_valid = len(all_errors) == 0
        self.state.validation_errors = all_errors
        
        return validation_results
    
    def _validate_dynamic_configs(self) -> List[str]:
        """验证动态配置"""
        errors = []
        
        required_fields = {
            "performance_tuning": ["enabled", "auto_tuning"],
            "resource_allocation": ["enabled", "allocation_strategy"],
            "adaptive_learning": ["enabled"],
            "realtime_optimization": ["enabled", "latency_targets"],
            "dynamic_scaling": ["enabled", "scaling_policies"]
        }
        
        for config_name, config_data in self.dynamic_configs.items():
            if config_name in required_fields:
                for field in required_fields[config_name]:
                    if not self._has_nested_key(config_data, field):
                        errors.append(f"dynamic_config.{config_name}.{field} is required")
            
            # 特定配置的验证
            if config_name == "realtime_optimization":
                latency_targets = config_data.get("latency_targets", {})
                for service, target in latency_targets.items():
                    if not isinstance(target, (int, float)) or target <= 0:
                        errors.append(f"dynamic_config.{config_name}.latency_targets.{service} must be positive number")
        
        return errors
    
    def _validate_performance_configs(self) -> List[str]:
        """验证性能配置"""
        errors = []
        
        required_fields = {
            "cache_strategies": ["enabled", "cache_levels"],
            "memory_management": ["enabled", "allocation_strategies"],
            "cpu_optimization": ["enabled"],
            "gpu_optimization": ["enabled"],
            "network_optimization": ["enabled"]
        }
        
        for config_name, config_data in self.performance_configs.items():
            if config_name in required_fields:
                for field in required_fields[config_name]:
                    if not self._has_nested_key(config_data, field):
                        errors.append(f"performance_tuning.{config_name}.{field} is required")
            
            # 特定配置的验证
            if config_name == "cache_strategies":
                cache_levels = config_data.get("cache_levels", {})
                for level, level_config in cache_levels.items():
                    if "size_mb" in level_config and level_config["size_mb"] <= 0:
                        errors.append(f"performance_tuning.{config_name}.cache_levels.{level}.size_mb must be positive")
        
        return errors
    
    def _validate_hot_reload_configs(self) -> List[str]:
        """验证热重载配置"""
        errors = []
        
        required_fields = {
            "config_reload": ["enabled", "reload_strategies"],
            "model_reload": ["enabled"],
            "service_reload": ["enabled"],
            "plugin_reload": ["enabled"],
            "hot_reload_metrics": ["enabled", "metrics_collection"]
        }
        
        for config_name, config_data in self.hot_reload_configs.items():
            if config_name in required_fields:
                for field in required_fields[config_name]:
                    if not self._has_nested_key(config_data, field):
                        errors.append(f"hot_reload.{config_name}.{field} is required")
        
        return errors
    
    def _has_nested_key(self, data: Dict[str, Any], key: str) -> bool:
        """检查嵌套键是否存在"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "state": {
                "mode": self.state.mode.value,
                "last_updated": self.state.last_updated.isoformat(),
                "source": self.state.source.value,
                "version": self.state.version,
                "is_valid": self.state.is_valid,
                "validation_errors": self.state.validation_errors
            },
            "config_counts": {
                "dynamic_configs": len(self.dynamic_configs),
                "performance_configs": len(self.performance_configs),
                "hot_reload_configs": len(self.hot_reload_configs)
            },
            "observer_count": len(self.observers)
        }

# 全局运行时配置管理器实例
_runtime_config_manager = None

def get_runtime_config_manager(config_dir: Path = None) -> RuntimeConfigManager:
    """获取全局运行时配置管理器实例"""
    global _runtime_config_manager
    
    if _runtime_config_manager is None:
        _runtime_config_manager = RuntimeConfigManager(config_dir)
    
    return _runtime_config_manager

# 导出的配置访问函数
def get_dynamic_config(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取动态配置（便捷函数）"""
    return get_runtime_config_manager().get_dynamic_config(config_name, key, default)

def get_performance_config(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取性能配置（便捷函数）"""
    return get_runtime_config_manager().get_performance_config(config_name, key, default)

def get_hot_reload_config(config_name: str, key: str = None, default: Any = None) -> Any:
    """获取热重载配置（便捷函数）"""
    return get_runtime_config_manager().get_hot_reload_config(config_name, key, default)

def set_runtime_mode(mode: RuntimeConfigMode):
    """设置运行时模式（便捷函数）"""
    get_runtime_config_manager().set_mode(mode)

def reload_runtime_configs():
    """重新加载运行时配置（便捷函数）"""
    get_runtime_config_manager().reload_all_configs()

__all__ = [
    'RuntimeConfigManager',
    'RuntimeConfigMode',
    'RuntimeConfigSource',
    'RuntimeConfigState',
    'get_runtime_config_manager',
    'get_dynamic_config',
    'get_performance_config',
    'get_hot_reload_config',
    'set_runtime_mode',
    'reload_runtime_configs'
]

