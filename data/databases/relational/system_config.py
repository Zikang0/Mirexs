"""
系统配置模块 - 管理系统配置数据和参数设置
"""

import logging
import json
import yaml
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigCategory(Enum):
    """配置分类枚举"""
    SYSTEM = "system"
    PERFORMANCE = "performance"
    SECURITY = "security"
    UI = "ui"
    INTEGRATION = "integration"
    BACKUP = "backup"
    LOGGING = "logging"

class ConfigDataType(Enum):
    """配置数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"

@dataclass
class SystemConfig:
    """系统配置数据类"""
    config_key: str
    config_value: Any
    data_type: ConfigDataType
    category: ConfigCategory
    description: str
    is_encrypted: bool
    is_readonly: bool
    created_at: datetime
    updated_at: datetime
    updated_by: str

class SystemConfiguration:
    """系统配置管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化系统配置管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.config_table = config.get('config_table', 'system_configurations')
        
        # 缓存配置值
        self._config_cache = {}
        self._cache_timestamp = None
        
        # 初始化表结构
        self._initialize_tables()
        
        # 加载默认配置
        self._load_default_configurations()
    
    def _initialize_tables(self):
        """初始化系统配置表"""
        try:
            config_schema = {
                'config_key': 'VARCHAR(255) PRIMARY KEY',
                'config_value': 'TEXT NOT NULL',
                'data_type': 'VARCHAR(50) NOT NULL',
                'category': 'VARCHAR(50) NOT NULL',
                'description': 'TEXT',
                'is_encrypted': 'BOOLEAN DEFAULT FALSE',
                'is_readonly': 'BOOLEAN DEFAULT FALSE',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_by': 'VARCHAR(100) DEFAULT "system"'
            }
            
            self.db.create_table(self.config_table, config_schema)
            
            # 创建索引
            self.db.create_index(self.config_table, 'category')
            self.db.create_index(self.config_table, 'data_type')
            
            self.logger.info("System configuration table initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize system configuration table: {str(e)}")
            raise
    
    def _load_default_configurations(self):
        """加载默认系统配置"""
        default_configs = [
            {
                'config_key': 'system.name',
                'config_value': 'Mirexs AI System',
                'data_type': ConfigDataType.STRING.value,
                'category': ConfigCategory.SYSTEM.value,
                'description': '系统名称',
                'is_readonly': False
            },
            {
                'config_key': 'system.version',
                'config_value': '1.0.0',
                'data_type': ConfigDataType.STRING.value,
                'category': ConfigCategory.SYSTEM.value,
                'description': '系统版本',
                'is_readonly': True
            },
            {
                'config_key': 'performance.max_concurrent_tasks',
                'config_value': '10',
                'data_type': ConfigDataType.INTEGER.value,
                'category': ConfigCategory.PERFORMANCE.value,
                'description': '最大并发任务数',
                'is_readonly': False
            },
            {
                'config_key': 'performance.cache_ttl',
                'config_value': '3600',
                'data_type': ConfigDataType.INTEGER.value,
                'category': ConfigCategory.PERFORMANCE.value,
                'description': '缓存生存时间（秒）',
                'is_readonly': False
            },
            {
                'config_key': 'security.encryption_enabled',
                'config_value': 'true',
                'data_type': ConfigDataType.BOOLEAN.value,
                'category': ConfigCategory.SECURITY.value,
                'description': '是否启用数据加密',
                'is_readonly': False
            },
            {
                'config_key': 'ui.theme',
                'config_value': 'light',
                'data_type': ConfigDataType.STRING.value,
                'category': ConfigCategory.UI.value,
                'description': '界面主题',
                'is_readonly': False
            },
            {
                'config_key': 'logging.level',
                'config_value': 'INFO',
                'data_type': ConfigDataType.STRING.value,
                'category': ConfigCategory.LOGGING.value,
                'description': '日志级别',
                'is_readonly': False
            }
        ]
        
        for config_data in default_configs:
            if not self.get_config(config_data['config_key']):
                self.set_config(
                    config_data['config_key'],
                    config_data['config_value'],
                    ConfigDataType(config_data['data_type']),
                    ConfigCategory(config_data['category']),
                    config_data['description'],
                    config_data.get('is_encrypted', False),
                    config_data.get('is_readonly', False)
                )
    
    def get_config(self, config_key: str, default_value: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            config_key: 配置键
            default_value: 默认值
            
        Returns:
            Any: 配置值
        """
        try:
            # 检查缓存
            if config_key in self._config_cache:
                return self._config_cache[config_key]
            
            query = f"SELECT * FROM {self.config_table} WHERE config_key = %s"
            results = self.db.execute_query(query, (config_key,))
            
            if not results:
                return default_value
            
            config_data = results[0]
            raw_value = config_data['config_value']
            data_type = ConfigDataType(config_data['data_type'])
            
            # 根据数据类型转换值
            value = self._convert_value(raw_value, data_type)
            
            # 更新缓存
            self._config_cache[config_key] = value
            
            return value
            
        except Exception as e:
            self.logger.error(f"Failed to get config {config_key}: {str(e)}")
            return default_value
    
    def set_config(self, config_key: str, config_value: Any, 
                  data_type: ConfigDataType, category: ConfigCategory,
                  description: str = "", is_encrypted: bool = False,
                  is_readonly: bool = False, updated_by: str = "system") -> bool:
        """
        设置配置值
        
        Args:
            config_key: 配置键
            config_value: 配置值
            data_type: 数据类型
            category: 配置分类
            description: 配置描述
            is_encrypted: 是否加密
            is_readonly: 是否只读
            updated_by: 更新者
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 检查是否只读
            existing = self.get_config_record(config_key)
            if existing and existing.is_readonly:
                self.logger.warning(f"Config {config_key} is read-only")
                return False
            
            # 准备数据
            config_data = {
                'config_key': config_key,
                'config_value': str(config_value),
                'data_type': data_type.value,
                'category': category.value,
                'description': description,
                'is_encrypted': is_encrypted,
                'is_readonly': is_readonly,
                'updated_at': datetime.now(),
                'updated_by': updated_by
            }
            
            # 检查配置是否存在
            if existing:
                # 更新现有配置
                affected = self.db.execute_update(
                    self.config_table,
                    config_data,
                    "config_key = %s",
                    (config_key,)
                )
            else:
                # 插入新配置
                config_data['created_at'] = datetime.now()
                self.db.execute_insert(self.config_table, config_data)
            
            # 更新缓存
            self._config_cache[config_key] = config_value
            
            self.logger.info(f"Config updated: {config_key} = {config_value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set config {config_key}: {str(e)}")
            return False
    
    def get_config_record(self, config_key: str) -> Optional[SystemConfig]:
        """
        获取配置记录
        
        Args:
            config_key: 配置键
            
        Returns:
            SystemConfig: 配置记录，如果不存在返回None
        """
        try:
            query = f"SELECT * FROM {self.config_table} WHERE config_key = %s"
            results = self.db.execute_query(query, (config_key,))
            
            if not results:
                return None
            
            config_data = results[0]
            
            return SystemConfig(
                config_key=config_data['config_key'],
                config_value=self._convert_value(
                    config_data['config_value'],
                    ConfigDataType(config_data['data_type'])
                ),
                data_type=ConfigDataType(config_data['data_type']),
                category=ConfigCategory(config_data['category']),
                description=config_data['description'],
                is_encrypted=config_data['is_encrypted'],
                is_readonly=config_data['is_readonly'],
                created_at=config_data['created_at'],
                updated_at=config_data['updated_at'],
                updated_by=config_data['updated_by']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get config record: {str(e)}")
            return None
    
    def get_configs_by_category(self, category: ConfigCategory) -> Dict[str, Any]:
        """
        按分类获取配置
        
        Args:
            category: 配置分类
            
        Returns:
            Dict: 配置字典
        """
        try:
            query = f"SELECT config_key, config_value, data_type FROM {self.config_table} WHERE category = %s"
            results = self.db.execute_query(query, (category.value,))
            
            configs = {}
            for row in results:
                config_key = row['config_key']
                raw_value = row['config_value']
                data_type = ConfigDataType(row['data_type'])
                
                configs[config_key] = self._convert_value(raw_value, data_type)
            
            return configs
            
        except Exception as e:
            self.logger.error(f"Failed to get configs by category: {str(e)}")
            return {}
    
    def delete_config(self, config_key: str) -> bool:
        """
        删除配置
        
        Args:
            config_key: 配置键
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 检查是否只读
            existing = self.get_config_record(config_key)
            if existing and existing.is_readonly:
                self.logger.warning(f"Cannot delete read-only config: {config_key}")
                return False
            
            affected = self.db.execute_delete(
                self.config_table,
                "config_key = %s",
                (config_key,)
            )
            
            if affected > 0:
                # 从缓存中移除
                if config_key in self._config_cache:
                    del self._config_cache[config_key]
                
                self.logger.info(f"Config deleted: {config_key}")
                return True
            else:
                self.logger.warning(f"Config not found: {config_key}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete config: {str(e)}")
            return False
    
    def import_config_from_file(self, file_path: str, overwrite: bool = False) -> bool:
        """
        从文件导入配置
        
        Args:
            file_path: 文件路径
            overwrite: 是否覆盖现有配置
            
        Returns:
            bool: 导入是否成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    config_data = json.load(f)
                elif file_path.endswith(('.yaml', '.yml')):
                    config_data = yaml.safe_load(f)
                else:
                    self.logger.error(f"Unsupported file format: {file_path}")
                    return False
            
            imported_count = 0
            for config_key, config_info in config_data.items():
                # 检查配置是否已存在
                existing = self.get_config_record(config_key)
                if existing and not overwrite:
                    continue
                
                # 设置配置
                success = self.set_config(
                    config_key=config_key,
                    config_value=config_info['value'],
                    data_type=ConfigDataType(config_info['data_type']),
                    category=ConfigCategory(config_info['category']),
                    description=config_info.get('description', ''),
                    is_encrypted=config_info.get('is_encrypted', False),
                    is_readonly=config_info.get('is_readonly', False),
                    updated_by='import_tool'
                )
                
                if success:
                    imported_count += 1
            
            self.logger.info(f"Imported {imported_count} configurations from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import configurations: {str(e)}")
            return False
    
    def export_config_to_file(self, file_path: str, categories: List[ConfigCategory] = None) -> bool:
        """
        导出配置到文件
        
        Args:
            file_path: 文件路径
            categories: 导出的分类列表（为空则导出所有）
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 构建查询
            if categories:
                category_values = [cat.value for cat in categories]
                placeholders = ', '.join(['%s' for _ in categories])
                query = f"SELECT * FROM {self.config_table} WHERE category IN ({placeholders})"
                params = tuple(category_values)
            else:
                query = f"SELECT * FROM {self.config_table}"
                params = ()
            
            results = self.db.execute_query(query, params)
            
            # 转换为导出格式
            export_data = {}
            for row in results:
                config_key = row['config_key']
                export_data[config_key] = {
                    'value': self._convert_value(row['config_value'], ConfigDataType(row['data_type'])),
                    'data_type': row['data_type'],
                    'category': row['category'],
                    'description': row['description'],
                    'is_encrypted': row['is_encrypted'],
                    'is_readonly': row['is_readonly'],
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'updated_by': row['updated_by']
                }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                elif file_path.endswith(('.yaml', '.yml')):
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    self.logger.error(f"Unsupported file format: {file_path}")
                    return False
            
            self.logger.info(f"Exported {len(export_data)} configurations to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configurations: {str(e)}")
            return False
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        验证系统配置
        
        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'missing_configs': [],
                'invalid_configs': []
            }
            
            # 必需配置列表
            required_configs = [
                'system.name',
                'system.version',
                'performance.max_concurrent_tasks',
                'security.encryption_enabled'
            ]
            
            # 检查必需配置
            for config_key in required_configs:
                if not self.get_config_record(config_key):
                    validation_result['is_valid'] = False
                    validation_result['missing_configs'].append(config_key)
                    validation_result['errors'].append(f"Required config missing: {config_key}")
            
            # 验证配置值
            all_configs = self.db.execute_query(f"SELECT * FROM {self.config_table}")
            for config in all_configs:
                try:
                    # 尝试转换值以验证数据类型
                    self._convert_value(
                        config['config_value'],
                        ConfigDataType(config['data_type'])
                    )
                except Exception as e:
                    validation_result['is_valid'] = False
                    validation_result['invalid_configs'].append(config['config_key'])
                    validation_result['errors'].append(
                        f"Invalid config value for {config['config_key']}: {str(e)}"
                    )
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Failed to validate configuration: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'missing_configs': [],
                'invalid_configs': []
            }
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            Dict: 配置摘要
        """
        try:
            summary = {
                'total_configs': 0,
                'configs_by_category': {},
                'configs_by_type': {},
                'readonly_configs': 0,
                'encrypted_configs': 0
            }
            
            # 获取所有配置
            all_configs = self.db.execute_query(f"SELECT * FROM {self.config_table}")
            summary['total_configs'] = len(all_configs)
            
            for config in all_configs:
                # 按分类统计
                category = config['category']
                summary['configs_by_category'][category] = \
                    summary['configs_by_category'].get(category, 0) + 1
                
                # 按类型统计
                data_type = config['data_type']
                summary['configs_by_type'][data_type] = \
                    summary['configs_by_type'].get(data_type, 0) + 1
                
                # 统计只读和加密配置
                if config['is_readonly']:
                    summary['readonly_configs'] += 1
                if config['is_encrypted']:
                    summary['encrypted_configs'] += 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get configuration summary: {str(e)}")
            return {}
    
    def _convert_value(self, raw_value: str, data_type: ConfigDataType) -> Any:
        """
        转换配置值
        
        Args:
            raw_value: 原始值
            data_type: 数据类型
            
        Returns:
            Any: 转换后的值
        """
        try:
            if data_type == ConfigDataType.STRING:
                return str(raw_value)
            elif data_type == ConfigDataType.INTEGER:
                return int(raw_value)
            elif data_type == ConfigDataType.FLOAT:
                return float(raw_value)
            elif data_type == ConfigDataType.BOOLEAN:
                return raw_value.lower() in ('true', '1', 'yes', 'on')
            elif data_type == ConfigDataType.JSON:
                return json.loads(raw_value)
            elif data_type == ConfigDataType.LIST:
                if raw_value.startswith('[') and raw_value.endswith(']'):
                    return json.loads(raw_value)
                else:
                    return [item.strip() for item in raw_value.split(',')]
            else:
                return raw_value
                
        except Exception as e:
            self.logger.error(f"Failed to convert config value: {raw_value} to {data_type}")
            raise
    
    def clear_cache(self):
        """清空配置缓存"""
        self._config_cache.clear()
        self._cache_timestamp = None
        self.logger.info("Configuration cache cleared")

