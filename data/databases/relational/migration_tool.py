"""
迁移工具模块 - 提供数据库迁移和版本控制功能
"""

import logging
import yaml
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class MigrationTool:
    """数据库迁移工具"""
    
    def __init__(self, db_integration, schema_manager, config: Dict[str, Any]):
        """
        初始化迁移工具
        
        Args:
            db_integration: 数据库集成实例
            schema_manager: 模式管理器实例
            config: 配置字典
        """
        self.db = db_integration
        self.schema_manager = schema_manager
        self.config = config
        self.logger = logger
        
        # 迁移配置
        self.migrations_path = Path(config.get('migrations_path', 'migrations'))
        self.migrations_path.mkdir(exist_ok=True)
    
    def create_migration(self, name: str, description: str = "") -> str:
        """
        创建新的迁移文件
        
        Args:
            name: 迁移名称
            description: 迁移描述
            
        Returns:
            str: 迁移文件路径
        """
        try:
            # 生成迁移ID（时间戳）
            migration_id = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
            filename = f"{migration_id}_{safe_name}.yaml"
            filepath = self.migrations_path / filename
            
            # 创建迁移模板
            migration_template = {
                'id': migration_id,
                'name': name,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'changes': []
            }
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(migration_template, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Migration template created: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to create migration: {str(e)}")
            raise
    
    def add_table_change(self, migration_file: str, change_type: str, 
                        table_name: str, columns: Dict[str, str] = None,
                        constraints: List[str] = None) -> bool:
        """
        添加表变更到迁移文件
        
        Args:
            migration_file: 迁移文件路径
            change_type: 变更类型 (create, alter, drop)
            table_name: 表名
            columns: 列定义
            constraints: 约束条件
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 读取迁移文件
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration = yaml.safe_load(f)
            
            # 构建变更
            change = {
                'type': 'table',
                'operation': change_type,
                'table': table_name
            }
            
            if columns:
                change['columns'] = columns
            
            if constraints:
                change['constraints'] = constraints
            
            # 生成SQL语句
            if change_type == 'create':
                columns_sql = ', '.join([f"{col} {typ}" for col, typ in columns.items()])
                if constraints:
                    columns_sql += ', ' + ', '.join(constraints)
                change['sql'] = f"CREATE TABLE {table_name} ({columns_sql})"
                
            elif change_type == 'drop':
                change['sql'] = f"DROP TABLE {table_name}"
                
            elif change_type == 'alter':
                # 这里简化处理，实际项目中需要更复杂的ALTER TABLE逻辑
                change['sql'] = f"-- ALTER TABLE {table_name} operations"
            
            # 添加到变更列表
            migration['changes'].append(change)
            
            # 写回文件
            with open(migration_file, 'w', encoding='utf-8') as f:
                yaml.dump(migration, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Added table change to migration: {change_type} {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add table change: {str(e)}")
            return False
    
    def add_column_change(self, migration_file: str, change_type: str,
                         table_name: str, column_name: str, 
                         data_type: str = None) -> bool:
        """
        添加列变更到迁移文件
        
        Args:
            migration_file: 迁移文件路径
            change_type: 变更类型 (add, modify, drop)
            table_name: 表名
            column_name: 列名
            data_type: 数据类型（仅对add和modify操作需要）
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 读取迁移文件
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration = yaml.safe_load(f)
            
            # 构建变更
            change = {
                'type': 'column',
                'operation': change_type,
                'table': table_name,
                'column': column_name
            }
            
            if data_type and change_type in ['add', 'modify']:
                change['data_type'] = data_type
            
            # 生成SQL语句
            if change_type == 'add':
                change['sql'] = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}"
            elif change_type == 'modify':
                change['sql'] = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {data_type}"
            elif change_type == 'drop':
                change['sql'] = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
            
            # 添加到变更列表
            migration['changes'].append(change)
            
            # 写回文件
            with open(migration_file, 'w', encoding='utf-8') as f:
                yaml.dump(migration, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Added column change to migration: {change_type} {table_name}.{column_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add column change: {str(e)}")
            return False
    
    def execute_migration(self, migration_file: str, rollback: bool = False) -> bool:
        """
        执行迁移
        
        Args:
            migration_file: 迁移文件路径
            rollback: 是否执行回滚
            
        Returns:
            bool: 执行是否成功
        """
        try:
            # 读取迁移文件
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration = yaml.safe_load(f)
            
            operations = []
            
            for change in migration['changes']:
                if rollback:
                    # 执行回滚SQL（如果存在）
                    if 'rollback_sql' in change and change['rollback_sql']:
                        operations.append((change['rollback_sql'], ()))
                    else:
                        self.logger.warning(f"No rollback SQL for change: {change}")
                else:
                    # 执行正向迁移SQL
                    operations.append((change['sql'], ()))
            
            # 在事务中执行所有操作
            success = self.db.execute_transaction(operations)
            
            if success and not rollback:
                # 记录迁移版本
                version = migration['id']
                description = f"{migration['name']}: {migration['description']}"
                self.schema_manager.register_schema_version(version, description, migration['changes'])
            
            action = "rollback" if rollback else "migration"
            self.logger.info(f"{action} executed successfully: {migration_file}")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to execute migration: {str(e)}")
            return False
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """
        获取待执行的迁移
        
        Returns:
            List[Dict]: 待执行迁移列表
        """
        try:
            pending_migrations = []
            current_version = self.schema_manager.get_current_version()
            
            # 获取所有迁移文件
            migration_files = list(self.migrations_path.glob("*.yaml"))
            migration_files.sort()  # 按文件名排序（时间戳顺序）
            
            for migration_file in migration_files:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration = yaml.safe_load(f)
                
                # 检查是否已应用
                if current_version and migration['id'] <= current_version:
                    continue  # 已应用的迁移
                
                pending_migrations.append({
                    'file': str(migration_file),
                    'id': migration['id'],
                    'name': migration['name'],
                    'description': migration['description'],
                    'changes_count': len(migration.get('changes', []))
                })
            
            return pending_migrations
            
        except Exception as e:
            self.logger.error(f"Failed to get pending migrations: {str(e)}")
            return []
    
    def migrate_to_latest(self) -> bool:
        """
        迁移到最新版本
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            pending_migrations = self.get_pending_migrations()
            
            if not pending_migrations:
                self.logger.info("No pending migrations")
                return True
            
            self.logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            for migration_info in pending_migrations:
                self.logger.info(f"Executing migration: {migration_info['name']}")
                
                success = self.execute_migration(migration_info['file'])
                if not success:
                    self.logger.error(f"Migration failed: {migration_info['name']}")
                    return False
            
            self.logger.info("All migrations completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate to latest: {str(e)}")
            return False
    
    def rollback_migration(self, migration_id: str) -> bool:
        """
        回滚指定迁移
        
        Args:
            migration_id: 迁移ID
            
        Returns:
            bool: 回滚是否成功
        """
        try:
            # 查找迁移文件
            migration_files = list(self.migrations_path.glob("*.yaml"))
            target_file = None
            
            for migration_file in migration_files:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    migration = yaml.safe_load(f)
                
                if migration['id'] == migration_id:
                    target_file = migration_file
                    break
            
            if not target_file:
                self.logger.error(f"Migration not found: {migration_id}")
                return False
            
            # 执行回滚
            success = self.execute_migration(target_file, rollback=True)
            
            if success:
                self.logger.info(f"Migration rolled back: {migration_id}")
            else:
                self.logger.error(f"Failed to rollback migration: {migration_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to rollback migration: {str(e)}")
            return False
    
    def validate_migrations(self) -> Dict[str, Any]:
        """
        验证所有迁移文件
        
        Returns:
            Dict: 验证结果
        """
        try:
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'migrations': []
            }
            
            migration_files = list(self.migrations_path.glob("*.yaml"))
            
            for migration_file in migration_files:
                migration_info = {
                    'file': str(migration_file),
                    'is_valid': True,
                    'errors': []
                }
                
                try:
                    with open(migration_file, 'r', encoding='utf-8') as f:
                        migration = yaml.safe_load(f)
                    
                    # 检查必需字段
                    required_fields = ['id', 'name', 'changes']
                    for field in required_fields:
                        if field not in migration:
                            migration_info['is_valid'] = False
                            migration_info['errors'].append(f"Missing required field: {field}")
                    
                    # 检查变更格式
                    if 'changes' in migration:
                        for i, change in enumerate(migration['changes']):
                            if 'type' not in change or 'operation' not in change:
                                migration_info['is_valid'] = False
                                migration_info['errors'].append(f"Invalid change format at index {i}")
                    
                    if not migration_info['is_valid']:
                        validation_result['is_valid'] = False
                        validation_result['errors'].extend([
                            f"{migration_file}: {error}" 
                            for error in migration_info['errors']
                        ])
                    
                except Exception as e:
                    migration_info['is_valid'] = False
                    migration_info['errors'].append(f"File parsing error: {str(e)}")
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(f"{migration_file}: {str(e)}")
                
                validation_result['migrations'].append(migration_info)
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Failed to validate migrations: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation failed: {str(e)}"],
                'warnings': [],
                'migrations': []
            }
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """
        生成迁移报告
        
        Returns:
            Dict: 迁移报告
        """
        try:
            report = {
                'generated_at': datetime.now().isoformat(),
                'current_version': self.schema_manager.get_current_version(),
                'pending_migrations': self.get_pending_migrations(),
                'migration_history': self.schema_manager.get_version_history(50),
                'validation': self.validate_migrations()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate migration report: {str(e)}")
            return {
                'generated_at': datetime.now().isoformat(),
                'error': str(e)
            }
