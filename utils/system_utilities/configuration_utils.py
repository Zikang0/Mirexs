"""
配置工具模块

提供配置管理、读取、验证、热重载等功能
"""

import os
import json
import yaml
import configparser
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from datetime import datetime
import threading
import time
from pathlib import Path
import copy
import hashlib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load_from_file(file_path: str, format: Optional[str] = None) -> Dict[str, Any]:
        """从文件加载配置
        
        Args:
            file_path: 配置文件路径
            format: 文件格式，None则从扩展名推断
            
        Returns:
            配置字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        if format is None:
            format = Path(file_path).suffix.lower()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            if format in ['.json', 'json']:
                return json.load(f)
            elif format in ['.yaml', '.yml', 'yaml']:
                return yaml.safe_load(f)
            elif format in ['.ini', 'ini']:
                config = configparser.ConfigParser()
                config.read_file(f)
                return {section: dict(config.items(section)) for section in config.sections()}
            elif format in ['.env', 'env']:
                return ConfigLoader._load_env_file(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {format}")
    
    @staticmethod
    def _load_env_file(file) -> Dict[str, str]:
        """加载.env文件"""
        config = {}
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"').strip("'")
        return config
    
    @staticmethod
    def load_from_env(prefix: str = 'APP_') -> Dict[str, Any]:
        """从环境变量加载配置
        
        Args:
            prefix: 环境变量前缀
            
        Returns:
            配置字典
        """
        config = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                config[config_key] = ConfigLoader._parse_env_value(value)
        return config
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为数字
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # 尝试解析为布尔值
        if value.lower() in ['true', 'yes', 'on', '1']:
            return True
        if value.lower() in ['false', 'no', 'off', '0']:
            return False
        
        # 尝试解析为JSON
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except:
                pass
        
        return value
    
    @staticmethod
    def load_from_multiple(files: List[str], merge_strategy: str = 'deep') -> Dict[str, Any]:
        """从多个文件加载配置
        
        Args:
            files: 配置文件路径列表
            merge_strategy: 合并策略 ('shallow', 'deep', 'override')
            
        Returns:
            合并后的配置字典
        """
        config = {}
        for file_path in files:
            file_config = ConfigLoader.load_from_file(file_path)
            if merge_strategy == 'shallow':
                config.update(file_config)
            elif merge_strategy == 'deep':
                config = ConfigMerger.deep_merge(config, file_config)
            elif merge_strategy == 'override':
                config = file_config
            else:
                raise ValueError(f"不支持的合并策略: {merge_strategy}")
        return config


class ConfigSaver:
    """配置保存器"""
    
    @staticmethod
    def save_to_file(config: Dict[str, Any], file_path: str, format: Optional[str] = None) -> bool:
        """保存配置到文件
        
        Args:
            config: 配置字典
            file_path: 保存路径
            format: 文件格式，None则从扩展名推断
            
        Returns:
            是否成功
        """
        try:
            if format is None:
                format = Path(file_path).suffix.lower()
            
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format in ['.json', 'json']:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                elif format in ['.yaml', '.yml', 'yaml']:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                elif format in ['.ini', 'ini']:
                    ConfigSaver._save_as_ini(config, f)
                elif format in ['.env', 'env']:
                    ConfigSaver._save_as_env(config, f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {format}")
            
            logger.info(f"配置已保存到 {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    @staticmethod
    def _save_as_ini(config: Dict[str, Any], file):
        """保存为INI格式"""
        for section, values in config.items():
            if isinstance(values, dict):
                file.write(f"[{section}]\n")
                for key, value in values.items():
                    file.write(f"{key} = {value}\n")
                file.write("\n")
    
    @staticmethod
    def _save_as_env(config: Dict[str, Any], file, prefix: str = 'APP_'):
        """保存为.env格式"""
        for key, value in config.items():
            env_key = f"{prefix}{key.upper()}"
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            file.write(f"{env_key}={value}\n")


class ConfigMerger:
    """配置合并器"""
    
    @staticmethod
    def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并配置
        
        Args:
            base: 基础配置
            override: 覆盖配置
            
        Returns:
            合并后的配置
        """
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigMerger.deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    @staticmethod
    def merge_with_env(config: Dict[str, Any], prefix: str = 'APP_') -> Dict[str, Any]:
        """与环境变量合并
        
        Args:
            config: 基础配置
            prefix: 环境变量前缀
            
        Returns:
            合并后的配置
        """
        env_config = ConfigLoader.load_from_env(prefix)
        return ConfigMerger.deep_merge(config, env_config)
    
    @staticmethod
    def merge_layers(layers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """多层合并
        
        Args:
            layers: 配置层列表，后面的层会覆盖前面的层
            
        Returns:
            合并后的配置
        """
        if not layers:
            return {}
        
        result = layers[0]
        for layer in layers[1:]:
            result = ConfigMerger.deep_merge(result, layer)
        
        return result


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None):
        """初始化配置验证器
        
        Args:
            schema: 配置模式
        """
        self.schema = schema or {}
        self.errors = []
        self.warnings = []
    
    def validate(self, config: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> bool:
        """验证配置
        
        Args:
            config: 配置字典
            schema: 配置模式，None则使用初始化时的模式
            
        Returns:
            是否通过验证
        """
        self.errors = []
        self.warnings = []
        
        if schema is None:
            schema = self.schema
        
        self._validate_dict(config, schema, '')
        
        return len(self.errors) == 0
    
    def _validate_dict(self, config: Dict[str, Any], schema: Dict[str, Any], path: str):
        """验证字典"""
        # 检查必填字段
        required = schema.get('required', [])
        for field in required:
            if field not in config:
                self.errors.append(f"{path}.{field}: 缺少必填字段")
        
        # 检查字段类型
        properties = schema.get('properties', {})
        for field, field_schema in properties.items():
            if field in config:
                self._validate_value(config[field], field_schema, f"{path}.{field}")
            elif field in required:
                continue
            elif 'default' in field_schema:
                config[field] = field_schema['default']
    
    def _validate_value(self, value: Any, schema: Dict[str, Any], path: str):
        """验证值"""
        # 检查类型
        expected_type = schema.get('type')
        if expected_type:
            type_map = {
                'string': str,
                'integer': int,
                'number': (int, float),
                'boolean': bool,
                'array': list,
                'object': dict
            }
            expected = type_map.get(expected_type)
            if expected and not isinstance(value, expected):
                self.errors.append(f"{path}: 类型应为 {expected_type}，实际为 {type(value).__name__}")
        
        # 检查枚举值
        enum_values = schema.get('enum')
        if enum_values and value not in enum_values:
            self.errors.append(f"{path}: 值 {value} 不在允许的枚举值 {enum_values} 中")
        
        # 检查最小值
        minimum = schema.get('minimum')
        if minimum is not None and value < minimum:
            self.errors.append(f"{path}: 值 {value} 小于最小值 {minimum}")
        
        # 检查最大值
        maximum = schema.get('maximum')
        if maximum is not None and value > maximum:
            self.errors.append(f"{path}: 值 {value} 大于最大值 {maximum}")
        
        # 检查最小长度
        min_length = schema.get('minLength')
        if min_length is not None and len(value) < min_length:
            self.errors.append(f"{path}: 长度 {len(value)} 小于最小长度 {min_length}")
        
        # 检查最大长度
        max_length = schema.get('maxLength')
        if max_length is not None and len(value) > max_length:
            self.errors.append(f"{path}: 长度 {len(value)} 大于最大长度 {max_length}")
        
        # 检查模式
        pattern = schema.get('pattern')
        if pattern and isinstance(value, str):
            import re
            if not re.match(pattern, value):
                self.errors.append(f"{path}: 不匹配模式 {pattern}")
        
        # 递归验证对象
        if isinstance(value, dict) and 'properties' in schema:
            self._validate_dict(value, schema, path)
        
        # 验证数组项
        if isinstance(value, list) and 'items' in schema:
            items_schema = schema['items']
            for i, item in enumerate(value):
                self._validate_value(item, items_schema, f"{path}[{i}]")
    
    def get_errors(self) -> List[str]:
        """获取错误列表"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """获取警告列表"""
        return self.warnings
    
    def get_report(self) -> str:
        """获取验证报告"""
        report = []
        report.append("配置验证报告")
        report.append("=" * 40)
        
        if not self.errors and not self.warnings:
            report.append("✓ 配置验证通过")
            return "\n".join(report)
        
        if self.errors:
            report.append(f"\n错误 ({len(self.errors)}):")
            for error in self.errors:
                report.append(f"  ✗ {error}")
        
        if self.warnings:
            report.append(f"\n警告 ({len(self.warnings)}):")
            for warning in self.warnings:
                report.append(f"  ⚠ {warning}")
        
        return "\n".join(report)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, app_name: str, config_dir: Optional[str] = None):
        """初始化配置管理器
        
        Args:
            app_name: 应用名称
            config_dir: 配置目录
        """
        self.app_name = app_name
        self.config_dir = config_dir or self._get_default_config_dir()
        self.config = {}
        self.original_config = {}
        self.lock = threading.RLock()
        self.watchers = []
        self.watch_thread = None
        self.watching = False
        self.last_modified = {}
        self.config_hash = None
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _get_default_config_dir(self) -> str:
        """获取默认配置目录"""
        if os.name == 'nt':  # Windows
            base_dir = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:  # Linux/Mac
            base_dir = os.path.expanduser('~')
        
        return os.path.join(base_dir, f'.{self.app_name}', 'config')
    
    def load(self, filename: str = 'config.json', 
             env_prefix: Optional[str] = None,
             validate_schema: Optional[Dict[str, Any]] = None) -> bool:
        """加载配置
        
        Args:
            filename: 配置文件名
            env_prefix: 环境变量前缀
            validate_schema: 验证模式
            
        Returns:
            是否成功
        """
        config_path = os.path.join(self.config_dir, filename)
        
        try:
            # 加载文件配置
            if os.path.exists(config_path):
                file_config = ConfigLoader.load_from_file(config_path)
            else:
                file_config = {}
            
            # 合并环境变量
            if env_prefix:
                file_config = ConfigMerger.merge_with_env(file_config, env_prefix)
            
            # 验证配置
            if validate_schema:
                validator = ConfigValidator(validate_schema)
                if not validator.validate(file_config):
                    logger.warning(f"配置验证失败:\n{validator.get_report()}")
                    self.config = file_config
                    return False
            
            with self.lock:
                self.config = file_config
                self.original_config = copy.deepcopy(file_config)
                self.config_hash = self._calculate_hash(file_config)
            
            logger.info(f"配置已加载: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return False
    
    def save(self, filename: str = 'config.json') -> bool:
        """保存配置
        
        Args:
            filename: 配置文件名
            
        Returns:
            是否成功
        """
        config_path = os.path.join(self.config_dir, filename)
        
        try:
            with self.lock:
                success = ConfigSaver.save_to_file(self.config, config_path)
                if success:
                    self.original_config = copy.deepcopy(self.config)
                    self.config_hash = self._calculate_hash(self.config)
            return success
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值
        
        Args:
            key: 配置键，支持点号分隔的路径
            default: 默认值
            
        Returns:
            配置值
        """
        with self.lock:
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
            return value if value is not None else default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值
        
        Args:
            key: 配置键，支持点号分隔的路径
            value: 配置值
        """
        with self.lock:
            keys = key.split('.')
            target = self.config
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
    
    def update(self, config: Dict[str, Any]) -> None:
        """更新配置
        
        Args:
            config: 配置字典
        """
        with self.lock:
            self.config = ConfigMerger.deep_merge(self.config, config)
    
    def reset(self) -> None:
        """重置配置到原始状态"""
        with self.lock:
            self.config = copy.deepcopy(self.original_config)
    
    def has_changed(self) -> bool:
        """检查配置是否已更改"""
        with self.lock:
            current_hash = self._calculate_hash(self.config)
            return current_hash != self.config_hash
    
    def _calculate_hash(self, config: Dict[str, Any]) -> str:
        """计算配置哈希"""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def export(self, format: str = 'json') -> str:
        """导出配置
        
        Args:
            format: 导出格式 ('json', 'yaml', 'env')
            
        Returns:
            配置字符串
        """
        with self.lock:
            if format == 'json':
                return json.dumps(self.config, indent=2, ensure_ascii=False)
            elif format == 'yaml':
                import yaml
                return yaml.dump(self.config, allow_unicode=True, default_flow_style=False)
            elif format == 'env':
                lines = []
                self._dict_to_env(self.config, lines)
                return '\n'.join(lines)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
    
    def _dict_to_env(self, d: Dict[str, Any], lines: List[str], prefix: str = 'APP_'):
        """将字典转换为环境变量格式"""
        for key, value in d.items():
            env_key = f"{prefix}{key.upper()}"
            if isinstance(value, dict):
                self._dict_to_env(value, lines, f"{env_key}_")
            elif isinstance(value, (list, tuple)):
                lines.append(f"{env_key}={json.dumps(value, ensure_ascii=False)}")
            else:
                lines.append(f"{env_key}={value}")
    
    def watch(self, filename: str = 'config.json', interval: float = 5.0):
        """监控配置文件变化
        
        Args:
            filename: 配置文件名
            interval: 检查间隔
        """
        if self.watching:
            return
        
        self.config_file = os.path.join(self.config_dir, filename)
        self.watching = True
        self.watch_thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True
        )
        self.watch_thread.start()
        logger.info(f"开始监控配置文件: {self.config_file}")
    
    def _watch_loop(self, interval: float):
        """监控循环"""
        last_mtime = 0
        if os.path.exists(self.config_file):
            last_mtime = os.path.getmtime(self.config_file)
        
        while self.watching:
            try:
                time.sleep(interval)
                
                if not os.path.exists(self.config_file):
                    continue
                
                current_mtime = os.path.getmtime(self.config_file)
                if current_mtime > last_mtime:
                    logger.info("检测到配置文件变化")
                    self._reload_config()
                    last_mtime = current_mtime
                    
            except Exception as e:
                logger.error(f"配置监控错误: {e}")
    
    def _reload_config(self):
        """重新加载配置"""
        try:
            new_config = ConfigLoader.load_from_file(self.config_file)
            with self.lock:
                old_config = self.config
                self.config = new_config
                
                # 通知观察者
                for callback in self.watchers:
                    try:
                        callback(old_config, new_config)
                    except Exception as e:
                        logger.error(f"配置观察者回调错误: {e}")
                        
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
    
    def add_watcher(self, callback: callable):
        """添加配置观察者
        
        Args:
            callback: 回调函数，接收(old_config, new_config)
        """
        self.watchers.append(callback)
    
    def stop_watching(self):
        """停止监控"""
        self.watching = False
        if self.watch_thread:
            self.watch_thread.join(timeout=2)
        logger.info("停止监控配置文件")
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self.lock:
            return copy.deepcopy(self.config)


class EnvironmentConfig:
    """环境配置管理"""
    
    def __init__(self, environment: str = 'development'):
        """初始化环境配置
        
        Args:
            environment: 环境名称
        """
        self.environment = environment
        self.configs = {}
        self.current = {}
    
    def load_environment_configs(self, config_dir: str):
        """加载环境配置
        
        Args:
            config_dir: 配置目录
        """
        base_config = os.path.join(config_dir, 'base.yaml')
        env_config = os.path.join(config_dir, f'{self.environment}.yaml')
        
        # 加载基础配置
        if os.path.exists(base_config):
            self.configs['base'] = ConfigLoader.load_from_file(base_config)
        
        # 加载环境配置
        if os.path.exists(env_config):
            self.configs[self.environment] = ConfigLoader.load_from_file(env_config)
        
        # 合并配置
        self._merge_configs()
    
    def _merge_configs(self):
        """合并配置"""
        self.current = {}
        
        # 先加载基础配置
        if 'base' in self.configs:
            self.current = copy.deepcopy(self.configs['base'])
        
        # 覆盖环境配置
        if self.environment in self.configs:
            self.current = ConfigMerger.deep_merge(
                self.current, 
                self.configs[self.environment]
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.current
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set_environment(self, environment: str):
        """设置环境"""
        self.environment = environment
        self._merge_configs()


class ConfigTemplate:
    """配置模板"""
    
    @staticmethod
    def create_default_config(app_name: str) -> Dict[str, Any]:
        """创建默认配置
        
        Args:
            app_name: 应用名称
            
        Returns:
            默认配置字典
        """
        return {
            'app': {
                'name': app_name,
                'version': '1.0.0',
                'debug': False,
                'environment': 'development'
            },
            'logging': {
                'level': 'INFO',
                'format': 'json',
                'output': ['console', 'file'],
                'file': {
                    'path': 'logs/app.log',
                    'max_size': 10485760,  # 10MB
                    'backup_count': 5
                }
            },
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': f'{app_name}_db',
                'user': 'postgres',
                'password': '',
                'pool_size': 10,
                'timeout': 30
            },
            'cache': {
                'enabled': True,
                'type': 'redis',
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'ttl': 3600
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000,
                'workers': 4,
                'timeout': 60,
                'rate_limit': 100
            }
        }
    
    @staticmethod
    def create_config_schema() -> Dict[str, Any]:
        """创建配置模式"""
        return {
            'type': 'object',
            'required': ['app', 'logging'],
            'properties': {
                'app': {
                    'type': 'object',
                    'required': ['name', 'version'],
                    'properties': {
                        'name': {'type': 'string'},
                        'version': {'type': 'string'},
                        'debug': {'type': 'boolean'},
                        'environment': {
                            'type': 'string',
                            'enum': ['development', 'testing', 'staging', 'production']
                        }
                    }
                },
                'logging': {
                    'type': 'object',
                    'required': ['level'],
                    'properties': {
                        'level': {
                            'type': 'string',
                            'enum': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
                        },
                        'format': {
                            'type': 'string',
                            'enum': ['text', 'json']
                        },
                        'output': {
                            'type': 'array',
                            'items': {
                                'type': 'string',
                                'enum': ['console', 'file']
                            }
                        }
                    }
                },
                'database': {
                    'type': 'object',
                    'properties': {
                        'host': {'type': 'string'},
                        'port': {'type': 'integer', 'minimum': 1, 'maximum': 65535},
                        'name': {'type': 'string'},
                        'user': {'type': 'string'},
                        'password': {'type': 'string'},
                        'pool_size': {'type': 'integer', 'minimum': 1},
                        'timeout': {'type': 'integer', 'minimum': 1}
                    }
                },
                'cache': {
                    'type': 'object',
                    'properties': {
                        'enabled': {'type': 'boolean'},
                        'type': {
                            'type': 'string',
                            'enum': ['redis', 'memcached', 'memory']
                        },
                        'host': {'type': 'string'},
                        'port': {'type': 'integer'},
                        'db': {'type': 'integer'},
                        'ttl': {'type': 'integer', 'minimum': 0}
                    }
                }
            }
        }


def get_config(app_name: str, config_file: str = 'config.json') -> ConfigManager:
    """获取配置管理器（便捷函数）"""
    manager = ConfigManager(app_name)
    manager.load(config_file)
    return manager


def create_config_from_template(app_name: str, output_dir: str) -> bool:
    """从模板创建配置文件"""
    config = ConfigTemplate.create_default_config(app_name)
    config_path = os.path.join(output_dir, 'config.json')
    return ConfigSaver.save_to_file(config, config_path)