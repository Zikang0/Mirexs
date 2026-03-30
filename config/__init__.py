"""
Mirexs 配置管理中心
统一管理系统、用户和运行时配置，提供完整的配置管理功能
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml
import json
import logging
from datetime import datetime, timedelta
import threading
import hashlib
import copy
import inspect

# 配置系统日志
logger = logging.getLogger("mirexs.config")

class ConfigType(Enum):
    """配置类型枚举"""
    SYSTEM = "system"
    USER = "user"
    RUNTIME = "runtime"
    ALL = "all"

class ConfigLoadMode(Enum):
    """配置加载模式"""
    LAZY = "lazy"          # 懒加载，按需加载
    EAGER = "eager"        # 预加载，启动时加载所有配置
    ON_DEMAND = "on_demand" # 按需加载并缓存

class ConfigUpdateStrategy(Enum):
    """配置更新策略"""
    IMMEDIATE = "immediate"  # 立即更新
    VALIDATE_FIRST = "validate_first"  # 先验证后更新
    ATOMIC = "atomic"        # 原子更新，要么全成功要么全失败
    ROLLING = "rolling"      # 滚动更新

class ConfigError(Exception):
    """配置错误基类"""
    pass

class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass

class ConfigNotFoundError(ConfigError):
    """配置未找到错误"""
    pass

class ConfigPermissionError(ConfigError):
    """配置权限错误"""
    pass

@dataclass
class ConfigMetadata:
    """配置元数据"""
    config_id: str
    config_type: ConfigType
    config_path: Path
    version: str = "2.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_by: str = "system"
    checksum: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

@dataclass
class ConfigChange:
    """配置变更记录"""
    change_id: str
    config_id: str
    change_type: str  # create, update, delete
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    changed_by: str = "system"
    change_reason: str = ""
    rollback_data: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "change_id": self.change_id,
            "config_id": self.config_id,
            "change_type": self.change_type,
            "timestamp": self.timestamp.isoformat(),
            "changed_by": self.changed_by,
            "change_reason": self.change_reason
        }

class ConfigValidator:
    """配置验证器基类"""
    
    def __init__(self):
        self.validation_rules = {}
        self._load_validation_rules()
    
    def _load_validation_rules(self):
        """加载验证规则"""
        # 基础验证规则
        self.validation_rules = {
            "required": self._validate_required,
            "type": self._validate_type,
            "range": self._validate_range,
            "pattern": self._validate_pattern,
            "enum": self._validate_enum,
            "custom": self._validate_custom
        }
    
    def validate(self, config_data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        验证配置数据
        
        Args:
            config_data: 配置数据
            schema: 验证模式
            
        Returns:
            错误消息列表
        """
        errors = []
        
        for field_name, field_schema in schema.items():
            if field_name not in config_data:
                if field_schema.get("required", False):
                    errors.append(f"Missing required field: {field_name}")
                continue
            
            value = config_data[field_name]
            
            # 应用所有验证规则
            for rule_name, rule_func in self.validation_rules.items():
                if rule_name in field_schema:
                    error = rule_func(field_name, value, field_schema[rule_name])
                    if error:
                        errors.append(error)
        
        return errors
    
    def _validate_required(self, field_name: str, value: Any, rule: bool) -> Optional[str]:
        """验证必填字段"""
        if rule and value is None:
            return f"Field '{field_name}' is required"
        return None
    
    def _validate_type(self, field_name: str, value: Any, expected_type: str) -> Optional[str]:
        """验证类型"""
        type_map = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if not expected:
            return f"Unknown type '{expected_type}' for field '{field_name}'"
        
        if not isinstance(value, expected):
            return f"Field '{field_name}' must be of type {expected_type}, got {type(value).__name__}"
        
        return None
    
    def _validate_range(self, field_name: str, value: Any, range_spec: Dict[str, Any]) -> Optional[str]:
        """验证范围"""
        if isinstance(value, (int, float)):
            if "min" in range_spec and value < range_spec["min"]:
                return f"Field '{field_name}' must be >= {range_spec['min']}"
            if "max" in range_spec and value > range_spec["max"]:
                return f"Field '{field_name}' must be <= {range_spec['max']}"
        return None
    
    def _validate_pattern(self, field_name: str, value: Any, pattern: str) -> Optional[str]:
        """验证正则表达式模式"""
        if isinstance(value, str):
            import re
            if not re.match(pattern, value):
                return f"Field '{field_name}' must match pattern: {pattern}"
        return None
    
    def _validate_enum(self, field_name: str, value: Any, enum_values: List[Any]) -> Optional[str]:
        """验证枚举值"""
        if value not in enum_values:
            return f"Field '{field_name}' must be one of {enum_values}"
        return None
    
    def _validate_custom(self, field_name: str, value: Any, custom_validator: Callable) -> Optional[str]:
        """自定义验证"""
        try:
            result = custom_validator(value)
            if result is not True:
                return f"Custom validation failed for field '{field_name}': {result}"
        except Exception as e:
            return f"Custom validation error for field '{field_name}': {str(e)}"
        return None

class ConfigObserver:
    """配置观察者"""
    
    def __init__(self, callback: Callable, config_pattern: str = None):
        """
        初始化配置观察者
        
        Args:
            callback: 回调函数，接收(config_path, old_value, new_value)参数
            config_pattern: 配置路径模式，支持通配符
        """
        self.callback = callback
        self.config_pattern = config_pattern
        self.call_count = 0
    
    def notify(self, config_path: str, old_value: Any, new_value: Any) -> bool:
        """
        通知观察者
        
        Args:
            config_path: 配置路径
            old_value: 旧值
            new_value: 新值
            
        Returns:
            通知是否成功
        """
        if self.config_pattern and not self._match_pattern(config_path):
            return False
        
        try:
            self.callback(config_path, old_value, new_value)
            self.call_count += 1
            return True
        except Exception as e:
            logger.error(f"Config observer callback failed: {e}")
            return False
    
    def _match_pattern(self, config_path: str) -> bool:
        """匹配配置路径模式"""
        if self.config_pattern == "*":
            return True
        
        # 简单的通配符匹配
        pattern_parts = self.config_pattern.split(".")
        path_parts = config_path.split(".")
        
        if len(pattern_parts) != len(path_parts):
            return False
        
        for pattern_part, path_part in zip(pattern_parts, path_parts):
            if pattern_part != "*" and pattern_part != path_part:
                return False
        
        return True

class ConfigManager:
    """
    配置管理器
    统一管理Mirexs系统的所有配置
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, config_root: Path = None):
        """
        初始化配置管理器
        
        Args:
            config_root: 配置根目录，默认为项目根目录下的config目录
        """
        if hasattr(self, '_initialized'):
            return
        
        # 设置配置根目录
        if config_root is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            self.config_root = project_root / "config"
        else:
            self.config_root = Path(config_root)
        
        # 确保配置目录存在
        self._ensure_config_directories()
        
        # 初始化属性
        self.system_configs = {}
        self.user_configs = {}
        self.runtime_configs = {}
        self.config_metadata = {}
        self.config_cache = {}
        self.observers = []
        self.validator = ConfigValidator()
        self.change_history = []
        self.max_history_size = 1000
        self.load_mode = ConfigLoadMode.LAZY
        self.update_strategy = ConfigUpdateStrategy.VALIDATE_FIRST
        
        # 加载配置索引
        self._load_config_index()
        
        # 标记已初始化
        self._initialized = True
        
        logger.info(f"ConfigManager initialized with root: {self.config_root}")
    
    def _ensure_config_directories(self):
        """确保配置目录存在"""
        directories = [
            self.config_root,
            self.config_root / "system",
            self.config_root / "system" / "model_configs",
            self.config_root / "system" / "service_configs",
            self.config_root / "system" / "platform_configs",
            self.config_root / "user",
            self.config_root / "user" / "personalization",
            self.config_root / "user" / "preferences",
            self.config_root / "user" / "profiles",
            self.config_root / "runtime",
            self.config_root / "runtime" / "dynamic_config",
            self.config_root / "runtime" / "performance_tuning",
            self.config_root / "runtime" / "hot_reload"
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True, parents=True)
    
    def _load_config_index(self):
        """加载配置索引"""
        index_file = self.config_root / "config_index.json"
        
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.config_metadata = json.load(f)
                logger.debug("Loaded config index from file")
            except Exception as e:
                logger.error(f"Failed to load config index: {e}")
                self.config_metadata = {}
        else:
            # 扫描目录构建索引
            self._build_config_index()
    
    def _build_config_index(self):
        """构建配置索引"""
        logger.info("Building config index...")
        
        # 扫描系统配置
        self._scan_directory(self.config_root / "system", ConfigType.SYSTEM, "system")
        
        # 扫描用户配置
        self._scan_directory(self.config_root / "user", ConfigType.USER, "user")
        
        # 扫描运行时配置
        self._scan_directory(self.config_root / "runtime", ConfigType.RUNTIME, "runtime")
        
        # 保存索引
        self._save_config_index()
    
    def _scan_directory(self, directory: Path, config_type: ConfigType, prefix: str):
        """扫描目录并构建索引"""
        for item in directory.rglob("*"):
            if item.is_file() and item.suffix in ['.yaml', '.yml', '.json']:
                # 计算相对路径
                relative_path = item.relative_to(self.config_root)
                config_path = str(relative_path).replace('/', '.').replace('\\', '.')
                config_id = config_path.rsplit('.', 1)[0]  # 移除扩展名
                
                # 计算校验和
                checksum = self._calculate_checksum(item)
                
                # 添加到索引
                self.config_metadata[config_id] = ConfigMetadata(
                    config_id=config_id,
                    config_type=config_type,
                    config_path=item,
                    checksum=checksum
                ).to_dict()
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                chunk = f.read(8192)
                while chunk:
                    file_hash.update(chunk)
                    chunk = f.read(8192)
                return file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""
    
    def _save_config_index(self):
        """保存配置索引"""
        index_file = self.config_root / "config_index.json"
        
        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_metadata, f, indent=2, default=str)
            logger.debug("Saved config index to file")
        except Exception as e:
            logger.error(f"Failed to save config index: {e}")
    
    def get_config(self, config_path: str, default: Any = None, 
                   reload: bool = False) -> Any:
        """
        获取配置值
        
        Args:
            config_path: 配置路径，支持点分隔符，如"system.main"
            default: 默认值
            reload: 是否重新加载配置
            
        Returns:
            配置值
        """
        # 规范化配置路径
        config_path = config_path.strip('.')
        
        # 检查缓存
        if not reload and config_path in self.config_cache:
            return self.config_cache[config_path]
        
        # 解析配置路径
        config_id, config_key = self._parse_config_path(config_path)
        
        if not config_id:
            logger.warning(f"Invalid config path: {config_path}")
            return default
        
        # 加载配置
        config_data = self._load_config(config_id, reload)
        if config_data is None:
            return default
        
        # 获取嵌套值
        if config_key:
            value = self._get_nested_value(config_data, config_key)
            if value is None:
                return default
        else:
            value = config_data
        
        # 缓存结果
        if not reload:
            self.config_cache[config_path] = value
        
        return value
    
    def _parse_config_path(self, config_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析配置路径
        
        Args:
            config_path: 配置路径
            
        Returns:
            (配置ID, 配置键)
        """
        parts = config_path.split('.')
        
        # 尝试不同的前缀组合来找到配置ID
        for i in range(len(parts), 0, -1):
            candidate_id = '.'.join(parts[:i])
            if candidate_id in self.config_metadata:
                config_key = '.'.join(parts[i:]) if i < len(parts) else None
                return candidate_id, config_key
        
        # 如果找不到精确匹配，尝试模糊匹配
        for config_id in self.config_metadata.keys():
            if config_path.startswith(config_id):
                config_key = config_path[len(config_id):].strip('.')
                return config_id, config_key
        
        return None, None
    
    def _load_config(self, config_id: str, reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        加载配置
        
        Args:
            config_id: 配置ID
            reload: 是否重新加载
            
        Returns:
            配置数据
        """
        # 检查元数据
        if config_id not in self.config_metadata:
            logger.warning(f"Config not found: {config_id}")
            return None
        
        metadata = self.config_metadata[config_id]
        config_path = Path(metadata['config_path'])
        config_type = ConfigType(metadata['config_type'])
        
        # 检查文件是否存在
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return None
        
        # 加载配置
        try:
            if config_path.suffix in ['.yaml', '.yml']:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                logger.error(f"Unsupported config format: {config_path.suffix}")
                return None
            
            # 更新缓存
            if config_type == ConfigType.SYSTEM:
                self.system_configs[config_id] = config_data
            elif config_type == ConfigType.USER:
                self.user_configs[config_id] = config_data
            elif config_type == ConfigType.RUNTIME:
                self.runtime_configs[config_id] = config_data
            
            # 更新元数据
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['checksum'] = self._calculate_checksum(config_path)
            
            logger.debug(f"Loaded config: {config_id}")
            return config_data
            
        except Exception as e:
            logger.error(f"Failed to load config {config_id}: {e}")
            return None
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """获取嵌套值"""
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def set_config(self, config_path: str, value: Any, 
                   validate: bool = True, save: bool = True) -> bool:
        """
        设置配置值
        
        Args:
            config_path: 配置路径
            value: 配置值
            validate: 是否验证配置
            save: 是否保存到文件
            
        Returns:
            是否成功
        """
        # 规范化配置路径
        config_path = config_path.strip('.')
        
        # 解析配置路径
        config_id, config_key = self._parse_config_path(config_path)
        
        if not config_id:
            logger.error(f"Invalid config path: {config_path}")
            return False
        
        # 检查权限（用户配置可以修改，系统配置可能需要特殊权限）
        metadata = self.config_metadata[config_id]
        config_type = ConfigType(metadata['config_type'])
        
        if config_type == ConfigType.SYSTEM:
            # 系统配置需要管理员权限
            # 这里可以添加权限检查逻辑
            pass
        
        # 加载当前配置
        current_config = self._load_config(config_id)
        if current_config is None:
            logger.error(f"Failed to load config: {config_id}")
            return False
        
        # 获取旧值
        if config_key:
            old_value = self._get_nested_value(current_config, config_key)
        else:
            old_value = copy.deepcopy(current_config)
        
        # 验证新值
        if validate:
            validation_errors = self._validate_config_update(config_id, config_key, value)
            if validation_errors:
                logger.error(f"Config validation failed: {validation_errors}")
                return False
        
        # 更新配置
        if config_key:
            # 更新嵌套值
            self._set_nested_value(current_config, config_key, value)
            new_value = value
        else:
            # 更新整个配置
            current_config = value
            new_value = value
        
        # 应用更新策略
        success = self._apply_update_strategy(
            config_id, current_config, config_type, save
        )
        
        if success:
            # 清除缓存
            self._clear_cache_for_config(config_id)
            
            # 记录变更
            self._record_change(
                config_id=config_id,
                change_type="update",
                old_value=old_value,
                new_value=new_value,
                changed_by="user"  # 这里可以替换为实际的用户标识
            )
            
            # 通知观察者
            self._notify_observers(config_path, old_value, new_value)
            
            logger.info(f"Config updated: {config_path}")
        
        return success
    
    def _validate_config_update(self, config_id: str, config_key: str, value: Any) -> List[str]:
        """验证配置更新"""
        # 这里可以添加特定的验证逻辑
        # 例如：检查值类型、范围、格式等
        
        errors = []
        
        # 加载验证模式
        schema = self._load_validation_schema(config_id)
        if schema:
            # 如果有验证模式，使用验证器
            validation_data = {config_key: value} if config_key else value
            errors = self.validator.validate(validation_data, schema)
        
        return errors
    
    def _load_validation_schema(self, config_id: str) -> Optional[Dict[str, Any]]:
        """加载验证模式"""
        # 检查是否有对应的验证模式文件
        schema_path = self.config_root / "schemas" / f"{config_id}_schema.json"
        
        if schema_path.exists():
            try:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schema for {config_id}: {e}")
        
        return None
    
    def _set_nested_value(self, data: Dict[str, Any], key_path: str, value: Any):
        """设置嵌套值"""
        keys = key_path.split('.')
        current = data
        
        # 遍历到倒数第二个键
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # 设置最后一个键的值
        current[keys[-1]] = value
    
    def _apply_update_strategy(self, config_id: str, new_config: Dict[str, Any],
                              config_type: ConfigType, save: bool = True) -> bool:
        """应用更新策略"""
        strategy = self.update_strategy
        
        if strategy == ConfigUpdateStrategy.IMMEDIATE:
            return self._apply_immediate_update(config_id, new_config, config_type, save)
        
        elif strategy == ConfigUpdateStrategy.VALIDATE_FIRST:
            return self._apply_validated_update(config_id, new_config, config_type, save)
        
        elif strategy == ConfigUpdateStrategy.ATOMIC:
            return self._apply_atomic_update(config_id, new_config, config_type, save)
        
        elif strategy == ConfigUpdateStrategy.ROLLING:
            return self._apply_rolling_update(config_id, new_config, config_type, save)
        
        else:
            logger.error(f"Unknown update strategy: {strategy}")
            return False
    
    def _apply_immediate_update(self, config_id: str, new_config: Dict[str, Any],
                               config_type: ConfigType, save: bool = True) -> bool:
        """立即更新"""
        try:
            # 更新内存中的配置
            if config_type == ConfigType.SYSTEM:
                self.system_configs[config_id] = new_config
            elif config_type == ConfigType.USER:
                self.user_configs[config_id] = new_config
            elif config_type == ConfigType.RUNTIME:
                self.runtime_configs[config_id] = new_config
            
            # 保存到文件
            if save:
                return self._save_config_to_file(config_id, new_config)
            
            return True
            
        except Exception as e:
            logger.error(f"Immediate update failed for {config_id}: {e}")
            return False
    
    def _apply_validated_update(self, config_id: str, new_config: Dict[str, Any],
                               config_type: ConfigType, save: bool = True) -> bool:
        """先验证后更新"""
        # 这里可以添加更复杂的验证逻辑
        # 例如：检查配置的一致性、依赖关系等
        
        # 简单验证：检查配置是否为有效的字典
        if not isinstance(new_config, dict):
            logger.error(f"Invalid config format for {config_id}")
            return False
        
        # 应用更新
        return self._apply_immediate_update(config_id, new_config, config_type, save)
    
    def _apply_atomic_update(self, config_id: str, new_config: Dict[str, Any],
                            config_type: ConfigType, save: bool = True) -> bool:
        """原子更新"""
        # 备份当前配置
        metadata = self.config_metadata[config_id]
        config_path = Path(metadata['config_path'])
        
        backup_path = config_path.with_suffix(config_path.suffix + '.backup')
        
        try:
            # 备份当前配置
            if config_path.exists():
                import shutil
                shutil.copy2(config_path, backup_path)
            
            # 尝试更新
            success = self._apply_immediate_update(config_id, new_config, config_type, save)
            
            if not success:
                # 恢复备份
                if backup_path.exists():
                    shutil.copy2(backup_path, config_path)
                    logger.info(f"Rolled back config: {config_id}")
                return False
            
            # 清理备份
            if backup_path.exists():
                backup_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Atomic update failed for {config_id}: {e}")
            
            # 恢复备份
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, config_path)
                    logger.info(f"Rolled back config after error: {config_id}")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
            
            return False
    
    def _apply_rolling_update(self, config_id: str, new_config: Dict[str, Any],
                             config_type: ConfigType, save: bool = True) -> bool:
        """滚动更新"""
        # 对于配置系统，滚动更新可能不适用
        # 这里可以留作扩展，例如分批更新相关配置
        
        logger.warning(f"Rolling update not implemented for config {config_id}")
        return self._apply_atomic_update(config_id, new_config, config_type, save)
    
    def _save_config_to_file(self, config_id: str, config_data: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        if config_id not in self.config_metadata:
            logger.error(f"Config metadata not found: {config_id}")
            return False
        
        metadata = self.config_metadata[config_id]
        config_path = Path(metadata['config_path'])
        
        try:
            # 确保目录存在
            config_path.parent.mkdir(exist_ok=True, parents=True)
            
            # 保存配置
            if config_path.suffix in ['.yaml', '.yml']:
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, 
                              allow_unicode=True, sort_keys=False)
            elif config_path.suffix == '.json':
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, default=str)
            else:
                logger.error(f"Unsupported config format: {config_path.suffix}")
                return False
            
            # 更新元数据
            metadata['updated_at'] = datetime.now().isoformat()
            metadata['checksum'] = self._calculate_checksum(config_path)
            metadata['updated_by'] = "user"  # 这里可以替换为实际的用户标识
            
            # 保存索引
            self._save_config_index()
            
            logger.debug(f"Saved config to file: {config_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config {config_id}: {e}")
            return False
    
    def _clear_cache_for_config(self, config_id: str):
        """清除配置相关的缓存"""
        keys_to_remove = []
        
        for key in self.config_cache.keys():
            if key.startswith(config_id):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.config_cache[key]
    
    def _record_change(self, config_id: str, change_type: str, old_value: Any = None,
                      new_value: Any = None, changed_by: str = "system",
                      change_reason: str = ""):
        """记录配置变更"""
        change_id = f"{config_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        change = ConfigChange(
            change_id=change_id,
            config_id=config_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            change_reason=change_reason
        )
        
        self.change_history.append(change)
        
        # 限制历史记录大小
        if len(self.change_history) > self.max_history_size:
            self.change_history = self.change_history[-self.max_history_size:]
    
    def register_observer(self, callback: Callable, config_pattern: str = "*"):
        """
        注册配置观察者
        
        Args:
            callback: 回调函数，接收(config_path, old_value, new_value)参数
            config_pattern: 配置路径模式，支持通配符
            
        Returns:
            观察者ID
        """
        observer = ConfigObserver(callback, config_pattern)
        self.observers.append(observer)
        
        observer_id = f"observer_{len(self.observers)}"
        logger.debug(f"Registered config observer: {observer_id}")
        
        return observer_id
    
    def unregister_observer(self, observer_id: str):
        """取消注册观察者"""
        # 这里简化处理，实际可以根据observer_id进行查找
        # 当前实现中，我们假设observer_id是索引
        try:
            index = int(observer_id.split('_')[1]) - 1
            if 0 <= index < len(self.observers):
                self.observers.pop(index)
                logger.debug(f"Unregistered config observer: {observer_id}")
                return True
        except (ValueError, IndexError):
            pass
        
        logger.warning(f"Observer not found: {observer_id}")
        return False
    
    def _notify_observers(self, config_path: str, old_value: Any, new_value: Any):
        """通知所有观察者"""
        for observer in self.observers:
            observer.notify(config_path, old_value, new_value)
    
    def get_all_configs(self, config_type: ConfigType = ConfigType.ALL) -> Dict[str, Any]:
        """
        获取所有配置
        
        Args:
            config_type: 配置类型
            
        Returns:
            配置字典
        """
        if config_type == ConfigType.SYSTEM:
            return self.system_configs.copy()
        elif config_type == ConfigType.USER:
            return self.user_configs.copy()
        elif config_type == ConfigType.RUNTIME:
            return self.runtime_configs.copy()
        elif config_type == ConfigType.ALL:
            all_configs = {}
            all_configs.update(self.system_configs)
            all_configs.update(self.user_configs)
            all_configs.update(self.runtime_configs)
            return all_configs
        else:
            logger.warning(f"Unknown config type: {config_type}")
            return {}
    
    def reload_all_configs(self, config_type: ConfigType = ConfigType.ALL):
        """
        重新加载所有配置
        
        Args:
            config_type: 配置类型
        """
        logger.info(f"Reloading all configs of type: {config_type}")
        
        config_ids_to_reload = []
        
        for config_id, metadata in self.config_metadata.items():
            if config_type == ConfigType.ALL or metadata['config_type'] == config_type.value:
                config_ids_to_reload.append(config_id)
        
        for config_id in config_ids_to_reload:
            self._load_config(config_id, reload=True)
        
        # 清除所有缓存
        self.config_cache.clear()
        
        logger.info(f"Reloaded {len(config_ids_to_reload)} configs")
    
    def export_configs(self, export_dir: Path, config_type: ConfigType = ConfigType.ALL,
                      include_metadata: bool = True) -> Dict[str, Path]:
        """
        导出配置
        
        Args:
            export_dir: 导出目录
            config_type: 配置类型
            include_metadata: 是否包含元数据
            
        Returns:
            导出文件路径字典
        """
        export_dir.mkdir(exist_ok=True, parents=True)
        
        exported_files = {}
        config_count = 0
        
        # 导出配置
        for config_id, metadata in self.config_metadata.items():
            if config_type != ConfigType.ALL and metadata['config_type'] != config_type.value:
                continue
            
            config_path = Path(metadata['config_path'])
            if not config_path.exists():
                continue
            
            # 创建导出路径
            export_path = export_dir / config_path.relative_to(self.config_root)
            export_path.parent.mkdir(exist_ok=True, parents=True)
            
            # 复制配置文件
            import shutil
            shutil.copy2(config_path, export_path)
            
            exported_files[config_id] = export_path
            config_count += 1
        
        # 导出元数据
        if include_metadata:
            metadata_path = export_dir / "config_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_metadata, f, indent=2, default=str)
            
            exported_files["metadata"] = metadata_path
            
            # 导出变更历史
            history_path = export_dir / "change_history.json"
            history_data = [change.to_dict() for change in self.change_history]
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, default=str)
            
            exported_files["history"] = history_path
        
        logger.info(f"Exported {config_count} configs to {export_dir}")
        return exported_files
    
    def import_configs(self, import_dir: Path, backup: bool = True) -> bool:
        """
        导入配置
        
        Args:
            import_dir: 导入目录
            backup: 是否备份现有配置
            
        Returns:
            是否成功
        """
        if not import_dir.exists():
            logger.error(f"Import directory not found: {import_dir}")
            return False
        
        # 备份现有配置
        if backup:
            backup_dir = self.config_root.parent / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.export_configs(backup_dir, ConfigType.ALL, include_metadata=True)
            logger.info(f"Created backup at: {backup_dir}")
        
        # 导入配置文件
        success_count = 0
        failure_count = 0
        
        for item in import_dir.rglob("*"):
            if item.is_file() and item.suffix in ['.yaml', '.yml', '.json']:
                # 计算目标路径
                relative_path = item.relative_to(import_dir)
                target_path = self.config_root / relative_path
                
                try:
                    # 确保目标目录存在
                    target_path.parent.mkdir(exist_ok=True, parents=True)
                    
                    # 复制文件
                    import shutil
                    shutil.copy2(item, target_path)
                    
                    success_count += 1
                    logger.debug(f"Imported config: {relative_path}")
                    
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Failed to import {relative_path}: {e}")
        
        # 重新加载配置索引
        self._build_config_index()
        
        # 重新加载所有配置
        self.reload_all_configs(ConfigType.ALL)
        
        logger.info(f"Import completed: {success_count} succeeded, {failure_count} failed")
        return failure_count == 0
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """
        验证所有配置
        
        Returns:
            验证结果字典
        """
        validation_results = {}
        
        for config_id in self.config_metadata.keys():
            config_data = self.get_config(config_id)
            if config_data is None:
                validation_results[config_id] = ["Failed to load config"]
                continue
            
            schema = self._load_validation_schema(config_id)
            if schema:
                errors = self.validator.validate(config_data, schema)
                if errors:
                    validation_results[config_id] = errors
        
        return validation_results
    
    def get_config_info(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        获取配置信息
        
        Args:
            config_id: 配置ID
            
        Returns:
            配置信息字典
        """
        if config_id not in self.config_metadata:
            return None
        
        info = dict(self.config_metadata[config_id])
        
        # 添加额外信息
        config_data = self.get_config(config_id)
        if config_data:
            info['size'] = len(str(config_data))
            info['keys_count'] = len(self._flatten_dict(config_data))
        
        # 添加变更历史
        config_changes = []
        for change in self.change_history[-10:]:  # 最近10个变更
            if change.config_id == config_id:
                config_changes.append(change.to_dict())
        
        if config_changes:
            info['recent_changes'] = config_changes
        
        return info
    
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """展平字典"""
        items = {}
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                items.update(self._flatten_dict(value, full_key))
            else:
                items[full_key] = value
        
        return items
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            配置摘要字典
        """
        summary = {
            "total_configs": len(self.config_metadata),
            "by_type": {
                "system": 0,
                "user": 0,
                "runtime": 0
            },
            "by_format": {
                "yaml": 0,
                "json": 0
            },
            "cache_stats": {
                "cached_items": len(self.config_cache),
                "cache_hits": 0,  # 这里可以添加缓存命中统计
                "cache_misses": 0
            },
            "observer_count": len(self.observers),
            "change_history_size": len(self.change_history)
        }
        
        # 统计配置类型
        for metadata in self.config_metadata.values():
            config_type = metadata['config_type']
            if config_type in summary["by_type"]:
                summary["by_type"][config_type] += 1
            
            config_path = metadata['config_path']
            if isinstance(config_path, str):
                config_path = Path(config_path)
            
            if config_path.suffix in ['.yaml', '.yml']:
                summary["by_format"]["yaml"] += 1
            elif config_path.suffix == '.json':
                summary["by_format"]["json"] += 1
        
        return summary
    
    def create_config_template(self, config_type: ConfigType, template_name: str,
                              template_data: Dict[str, Any]) -> bool:
        """
        创建配置模板
        
        Args:
            config_type: 配置类型
            template_name: 模板名称
            template_data: 模板数据
            
        Returns:
            是否成功
        """
        template_dir = self.config_root / "templates" / config_type.value
        template_dir.mkdir(exist_ok=True, parents=True)
        
        template_path = template_dir / f"{template_name}.yaml"
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, 
                          allow_unicode=True, sort_keys=False)
            
            logger.info(f"Created config template: {template_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create config template: {e}")
            return False
    
    def apply_config_template(self, config_type: ConfigType, template_name: str,
                             target_config_id: str) -> bool:
        """
        应用配置模板
        
        Args:
            config_type: 配置类型
            template_name: 模板名称
            target_config_id: 目标配置ID
            
        Returns:
            是否成功
        """
        template_path = self.config_root / "templates" / config_type.value / f"{template_name}.yaml"
        
        if not template_path.exists():
            logger.error(f"Template not found: {template_path}")
            return False
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            # 应用模板
            return self.set_config(target_config_id, template_data, validate=True, save=True)
            
        except Exception as e:
            logger.error(f"Failed to apply config template: {e}")
            return False
    
    def watch_config_changes(self, watch_interval: int = 5):
        """
        监视配置变化
        
        Args:
            watch_interval: 检查间隔（秒）
        """
        import time
        import threading
        
        def watch_loop():
            logger.info(f"Started config watcher (interval: {watch_interval}s)")
            
            # 记录初始校验和
            initial_checksums = {}
            for config_id, metadata in self.config_metadata.items():
                config_path = Path(metadata['config_path'])
                if config_path.exists():
                    initial_checksums[config_id] = self._calculate_checksum(config_path)
            
            while True:
                time.sleep(watch_interval)
                
                changed_configs = []
                for config_id, initial_checksum in initial_checksums.items():
                    metadata = self.config_metadata[config_id]
                    config_path = Path(metadata['config_path'])
                    
                    if not config_path.exists():
                        continue
                    
                    current_checksum = self._calculate_checksum(config_path)
                    if current_checksum != initial_checksum:
                        changed_configs.append(config_id)
                        initial_checksums[config_id] = current_checksum
                
                if changed_configs:
                    logger.info(f"Detected changes in configs: {changed_configs}")
                    
                    # 重新加载变化的配置
                    for config_id in changed_configs:
                        self._load_config(config_id, reload=True)
                    
                    # 通知观察者
                    for config_id in changed_configs:
                        config_data = self.get_config(config_id)
                        if config_data:
                            self._notify_observers(config_id, None, config_data)
        
        # 启动监视线程
        watch_thread = threading.Thread(target=watch_loop, daemon=True)
        watch_thread.start()
        
        return watch_thread
    
    def reset_to_defaults(self, config_type: ConfigType = ConfigType.ALL,
                         backup: bool = True) -> bool:
        """
        重置为默认配置
        
        Args:
            config_type: 配置类型
            backup: 是否备份
            
        Returns:
            是否成功
        """
        logger.warning(f"Resetting {config_type.value} configs to defaults")
        
        # 备份现有配置
        if backup:
            backup_dir = self.config_root.parent / f"config_reset_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.export_configs(backup_dir, config_type, include_metadata=True)
            logger.info(f"Created reset backup at: {backup_dir}")
        
        # 重置配置
        default_configs_dir = self.config_root.parent / "config_defaults"
        
        if not default_configs_dir.exists():
            logger.error(f"Default configs directory not found: {default_configs_dir}")
            return False
        
        # 导入默认配置
        return self.import_configs(default_configs_dir, backup=False)

# 全局配置管理器实例
_config_manager = None

def get_config_manager(config_root: Path = None) -> ConfigManager:
    """
    获取全局配置管理器实例
    
    Args:
        config_root: 配置根目录
        
    Returns:
        配置管理器实例
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_root)
    
    return _config_manager

def get_config(config_path: str, default: Any = None, reload: bool = False) -> Any:
    """
    获取配置值（便捷函数）
    
    Args:
        config_path: 配置路径
        default: 默认值
        reload: 是否重新加载
        
    Returns:
        配置值
    """
    return get_config_manager().get_config(config_path, default, reload)

def set_config(config_path: str, value: Any, validate: bool = True, save: bool = True) -> bool:
    """
    设置配置值（便捷函数）
    
    Args:
        config_path: 配置路径
        value: 配置值
        validate: 是否验证
        save: 是否保存
        
    Returns:
        是否成功
    """
    return get_config_manager().set_config(config_path, value, validate, save)

def reload_configs(config_type: ConfigType = ConfigType.ALL):
    """
    重新加载配置（便捷函数）
    
    Args:
        config_type: 配置类型
    """
    get_config_manager().reload_all_configs(config_type)

def watch_config_changes(watch_interval: int = 5):
    """
    监视配置变化（便捷函数）
    
    Args:
        watch_interval: 检查间隔（秒）
    """
    return get_config_manager().watch_config_changes(watch_interval)

def register_config_observer(callback: Callable, config_pattern: str = "*") -> str:
    """
    注册配置观察者（便捷函数）
    
    Args:
        callback: 回调函数
        config_pattern: 配置模式
        
    Returns:
        观察者ID
    """
    return get_config_manager().register_observer(callback, config_pattern)

# 导出的配置访问快捷方式
# 系统配置
def get_system_config(config_path: str, default: Any = None) -> Any:
    """获取系统配置"""
    return get_config(f"system.{config_path}", default)

def set_system_config(config_path: str, value: Any, validate: bool = True) -> bool:
    """设置系统配置"""
    return set_config(f"system.{config_path}", value, validate)

# 用户配置
def get_user_config(config_path: str, default: Any = None) -> Any:
    """获取用户配置"""
    return get_config(f"user.{config_path}", default)

def set_user_config(config_path: str, value: Any, validate: bool = True) -> bool:
    """设置用户配置"""
    return set_config(f"user.{config_path}", value, validate)

# 运行时配置
def get_runtime_config(config_path: str, default: Any = None) -> Any:
    """获取运行时配置"""
    return get_config(f"runtime.{config_path}", default)

def set_runtime_config(config_path: str, value: Any, validate: bool = True) -> bool:
    """设置运行时配置"""
    return set_config(f"runtime.{config_path}", value, validate)

# 配置管理快捷方式
def export_all_configs(export_dir: Path) -> Dict[str, Path]:
    """导出所有配置"""
    return get_config_manager().export_configs(export_dir, ConfigType.ALL)

def import_configs_from_dir(import_dir: Path) -> bool:
    """从目录导入配置"""
    return get_config_manager().import_configs(import_dir)

def validate_configs() -> Dict[str, List[str]]:
    """验证所有配置"""
    return get_config_manager().validate_all_configs()

def get_config_summary() -> Dict[str, Any]:
    """获取配置摘要"""
    return get_config_manager().get_config_summary()

__all__ = [
    # 核心类
    'ConfigManager',
    'ConfigType',
    'ConfigLoadMode',
    'ConfigUpdateStrategy',
    'ConfigError',
    'ConfigValidationError',
    'ConfigNotFoundError',
    'ConfigPermissionError',
    'ConfigMetadata',
    'ConfigChange',
    'ConfigValidator',
    'ConfigObserver',
    
    # 管理器函数
    'get_config_manager',
    
    # 配置访问函数
    'get_config',
    'set_config',
    'reload_configs',
    'watch_config_changes',
    'register_config_observer',
    
    # 快捷方式
    'get_system_config',
    'set_system_config',
    'get_user_config',
    'set_user_config',
    'get_runtime_config',
    'set_runtime_config',
    
    # 管理函数
    'export_all_configs',
    'import_configs_from_dir',
    'validate_configs',
    'get_config_summary',
]

# 配置管理器初始化提示
if __name__ == "__main__":
    print("Mirexs Configuration Management System")
    print("=" * 50)
    
    # 测试配置管理器
    try:
        config_mgr = get_config_manager()
        summary = config_mgr.get_config_summary()
        
        print(f"Configuration Manager Initialized")
        print(f"Config Root: {config_mgr.config_root}")
        print(f"Total Configs: {summary['total_configs']}")
        print(f"System Configs: {summary['by_type']['system']}")
        print(f"User Configs: {summary['by_type']['user']}")
        print(f"Runtime Configs: {summary['by_type']['runtime']}")
        print(f"Cache Items: {summary['cache_stats']['cached_items']}")
        
        # 显示一些示例配置路径
        print("\nExample Config Paths:")
        for config_id in list(config_mgr.config_metadata.keys())[:5]:
            print(f"  - {config_id}")
        
        print("\nUsage:")
        print("  from config import get_config, set_config")
        print("  value = get_config('system.main_config')")
        print("  success = set_config('user.preferences.language', 'zh-CN')")
        
    except Exception as e:
        print(f"Error initializing ConfigManager: {e}")
