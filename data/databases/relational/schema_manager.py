"""
模式管理器模块 - 管理数据库模式和版本控制
"""

import logging
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class SchemaChangeType(Enum):
    """模式变更类型枚举"""
    CREATE_TABLE = "create_table"
    ALTER_TABLE = "alter_table"
    DROP_TABLE = "drop_table"
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    MODIFY_COLUMN = "modify_column"

class SchemaManager:
    """数据库模式管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化模式管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 模式版本表名
        self.schema_version_table = config.get('schema_version_table', 'schema_versions')
        self.schema_changes_table = config.get('schema_changes_table', 'schema_changes')
        
        # 初始化模式版本表
        self._initialize_schema_tables()
    
    def _initialize_schema_tables(self):
        """初始化模式版本表"""
        try:
            # 创建模式版本表
            schema_version_schema = {
                'id': 'SERIAL PRIMARY KEY',
                'version': 'VARCHAR(50) NOT NULL',
                'description': 'TEXT',
                'checksum': 'VARCHAR(64) NOT NULL',
                'applied_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'applied_by': 'VARCHAR(100)'
            }
            
            self.db.create_table(
                self.schema_version_table,
                schema_version_schema,
                constraints=['UNIQUE(version)']
            )
            
            # 创建模式变更表
            schema_changes_schema = {
                'id': 'SERIAL PRIMARY KEY',
                'version_id': 'INTEGER REFERENCES schema_versions(id)',
                'change_type': 'VARCHAR(50) NOT NULL',
                'object_name': 'VARCHAR(255) NOT NULL',
                'sql_statement': 'TEXT NOT NULL',
                'rollback_sql': 'TEXT',
                'applied_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            self.db.create_table(self.schema_changes_table, schema_changes_schema)
            
            self.logger.info("Schema version tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize schema tables: {str(e)}")
            raise
    
    def register_schema_version(self, version: str, description: str, 
                              changes: List[Dict[str, Any]], applied_by: str = None) -> bool:
        """
        注册模式版本
        
        Args:
            version: 版本号
            description: 版本描述
            changes: 变更列表
            applied_by: 应用者
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 计算变更的校验和
            changes_json = json.dumps(changes, sort_keys=True)
            checksum = hashlib.sha256(changes_json.encode()).hexdigest()
            
            # 检查版本是否已存在
            existing = self.db.execute_query(
                f"SELECT id FROM {self.schema_version_table} WHERE version = %s",
                (version,)
            )
            
            if existing:
                self.logger.warning(f"Schema version {version} already exists")
                return False
            
            # 插入版本记录
            version_data = {
                'version': version,
                'description': description,
                'checksum': checksum,
                'applied_by': applied_by or 'system'
            }
            
            version_id = self.db.execute_insert(self.schema_version_table, version_data)
            
            # 记录变更详情
            for change in changes:
                change_data = {
                    'version_id': version_id,
                    'change_type': change['change_type'],
                    'object_name': change['object_name'],
                    'sql_statement': change['sql_statement'],
                    'rollback_sql': change.get('rollback_sql')
                }
                self.db.execute_insert(self.schema_changes_table, change_data)
            
            self.logger.info(f"Schema version {version} registered successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register schema version: {str(e)}")
            return False
    
    def apply_schema_changes(self, version: str, changes: List[Dict[str, Any]]) -> bool:
        """
        应用模式变更
        
        Args:
            version: 版本号
            changes: 变更列表
            
        Returns:
            bool: 应用是否成功
        """
        try:
            operations = []
            
            for change in changes:
                sql_statement = change['sql_statement']
                operations.append((sql_statement, ()))
            
            # 在事务中执行所有变更
            success = self.db.execute_transaction(operations)
            
            if success:
                # 注册版本
                description = f"Applied schema changes for version {version}"
                self.register_schema_version(version, description, changes)
                self.logger.info(f"Schema changes for version {version} applied successfully")
            else:
                self.logger.error(f"Failed to apply schema changes for version {version}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to apply schema changes: {str(e)}")
            return False
    
    def get_current_version(self) -> Optional[str]:
        """
        获取当前模式版本
        
        Returns:
            str: 当前版本号，如果没有版本则返回None
        """
        try:
            query = f"""
            SELECT version 
            FROM {self.schema_version_table} 
            ORDER BY applied_at DESC 
            LIMIT 1
            """
            
            results = self.db.execute_query(query)
            return results[0]['version'] if results else None
            
        except Exception as e:
            self.logger.error(f"Failed to get current version: {str(e)}")
            return None
    
    def get_version_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取版本历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Dict]: 版本历史
        """
        try:
            query = f"""
            SELECT 
                v.id, v.version, v.description, v.checksum, 
                v.applied_at, v.applied_by,
                COUNT(c.id) as change_count
            FROM {self.schema_version_table} v
            LEFT JOIN {self.schema_changes_table} c ON v.id = c.version_id
            GROUP BY v.id, v.version, v.description, v.checksum, v.applied_at, v.applied_by
            ORDER BY v.applied_at DESC
            LIMIT %s
            """
            
            return self.db.execute_query(query, (limit,))
            
        except Exception as e:
            self.logger.error(f"Failed to get version history: {str(e)}")
            return []
    
    def validate_schema(self, expected_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证当前模式是否符合预期
        
        Args:
            expected_schema: 预期模式定义
            
        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'details': {}
            }
            
            for table_name, expected_columns in expected_schema.items():
                table_details = {
                    'exists': False,
                    'column_matches': [],
                    'missing_columns': [],
                    'extra_columns': []
                }
                
                # 检查表是否存在
                if not self.db.table_exists(table_name):
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(f"Table {table_name} does not exist")
                    table_details['exists'] = False
                    continue
                
                table_details['exists'] = True
                
                # 获取实际表结构
                actual_schema = self.db.get_table_schema(table_name)
                actual_columns = {col['column_name']: col for col in actual_schema}
                
                # 检查列匹配
                for expected_col, expected_type in expected_columns.items():
                    if expected_col not in actual_columns:
                        validation_result['is_valid'] = False
                        validation_result['errors'].append(
                            f"Column {expected_col} missing in table {table_name}"
                        )
                        table_details['missing_columns'].append(expected_col)
                    else:
                        actual_col_info = actual_columns[expected_col]
                        # 简化的类型比较（实际项目中需要更复杂的类型映射）
                        if expected_type.lower() not in actual_col_info['data_type'].lower():
                            validation_result['warnings'].append(
                                f"Column {expected_col} type mismatch in table {table_name}: "
                                f"expected {expected_type}, got {actual_col_info['data_type']}"
                            )
                        
                        table_details['column_matches'].append({
                            'column': expected_col,
                            'expected_type': expected_type,
                            'actual_type': actual_col_info['data_type'],
                            'is_nullable': actual_col_info['is_nullable']
                        })
                
                # 检查额外列
                expected_col_set = set(expected_columns.keys())
                actual_col_set = set(actual_columns.keys())
                extra_columns = actual_col_set - expected_col_set
                
                if extra_columns:
                    table_details['extra_columns'] = list(extra_columns)
                    validation_result['warnings'].extend([
                        f"Extra column {col} in table {table_name}" 
                        for col in extra_columns
                    ])
                
                validation_result['details'][table_name] = table_details
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Failed to validate schema: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'details': {}
            }
    
    def generate_migration_script(self, current_schema: Dict[str, Any], 
                                target_schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成迁移脚本
        
        Args:
            current_schema: 当前模式
            target_schema: 目标模式
            
        Returns:
            List[Dict]: 迁移操作列表
        """
        try:
            migrations = []
            
            # 找出需要创建的表
            current_tables = set(current_schema.keys())
            target_tables = set(target_schema.keys())
            
            tables_to_create = target_tables - current_tables
            tables_to_drop = current_tables - target_tables
            
            # 创建新表
            for table in tables_to_create:
                columns_def = ', '.join([
                    f"{col_name} {col_type}" 
                    for col_name, col_type in target_schema[table].items()
                ])
                
                migration = {
                    'change_type': SchemaChangeType.CREATE_TABLE.value,
                    'object_name': table,
                    'sql_statement': f"CREATE TABLE {table} ({columns_def})",
                    'rollback_sql': f"DROP TABLE {table}"
                }
                migrations.append(migration)
            
            # 删除不需要的表
            for table in tables_to_drop:
                migration = {
                    'change_type': SchemaChangeType.DROP_TABLE.value,
                    'object_name': table,
                    'sql_statement': f"DROP TABLE {table}",
                    'rollback_sql': None  # 删除操作通常无法回滚
                }
                migrations.append(migration)
            
            # 处理现有表的变更
            common_tables = current_tables.intersection(target_tables)
            for table in common_tables:
                current_columns = set(current_schema[table].keys())
                target_columns = set(target_schema[table].keys())
                
                # 添加新列
                for col in target_columns - current_columns:
                    migration = {
                        'change_type': SchemaChangeType.ADD_COLUMN.value,
                        'object_name': f"{table}.{col}",
                        'sql_statement': f"ALTER TABLE {table} ADD COLUMN {col} {target_schema[table][col]}",
                        'rollback_sql': f"ALTER TABLE {table} DROP COLUMN {col}"
                    }
                    migrations.append(migration)
                
                # 删除不需要的列
                for col in current_columns - target_columns:
                    migration = {
                        'change_type': SchemaChangeType.DROP_COLUMN.value,
                        'object_name': f"{table}.{col}",
                        'sql_statement': f"ALTER TABLE {table} DROP COLUMN {col}",
                        'rollback_sql': f"ALTER TABLE {table} ADD COLUMN {col} {current_schema[table][col]}"
                    }
                    migrations.append(migration)
                
                # 检查类型变更（简化处理）
                common_cols = current_columns.intersection(target_columns)
                for col in common_cols:
                    if current_schema[table][col] != target_schema[table][col]:
                        migration = {
                            'change_type': SchemaChangeType.MODIFY_COLUMN.value,
                            'object_name': f"{table}.{col}",
                            'sql_statement': f"ALTER TABLE {table} ALTER COLUMN {col} TYPE {target_schema[table][col]}",
                            'rollback_sql': f"ALTER TABLE {table} ALTER COLUMN {col} TYPE {current_schema[table][col]}"
                        }
                        migrations.append(migration)
            
            return migrations
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration script: {str(e)}")
            return []
    
    def create_schema_snapshot(self) -> Dict[str, Any]:
        """
        创建当前模式快照
        
        Returns:
            Dict: 模式快照
        """
        try:
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'version': self.get_current_version(),
                'tables': {}
            }
            
            # 获取所有表
            if isinstance(self.db, PostgreSQLIntegration):
                tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                """
            else:  # SQLite
                tables_query = "SELECT name as table_name FROM sqlite_master WHERE type='table'"
            
            tables = self.db.execute_query(tables_query)
            
            for table in tables:
                table_name = table['table_name']
                if table_name in [self.schema_version_table, self.schema_changes_table]:
                    continue  # 跳过模式管理表
                
                # 获取表结构
                schema = self.db.get_table_schema(table_name)
                table_schema = {}
                
                for column in schema:
                    if isinstance(self.db, PostgreSQLIntegration):
                        col_def = column['data_type']
                        if column['character_maximum_length']:
                            col_def += f"({column['character_maximum_length']})"
                    else:  # SQLite
                        col_def = column['type']
                    
                    table_schema[column['column_name']] = col_def
                
                snapshot['tables'][table_name] = table_schema
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to create schema snapshot: {str(e)}")
            return {}

