"""
PostgreSQL集成模块 - 提供PostgreSQL数据库的完整集成功能
"""

import logging
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PostgreSQLIntegration:
    """PostgreSQL数据库集成类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PostgreSQL集成
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.connection_params = self._build_connection_params(config)
        self.thread_local = threading.local()
        self.logger = logger
        
        # 连接池配置
        self.min_connections = config.get('min_connections', 1)
        self.max_connections = config.get('max_connections', 10)
        
        # 测试连接
        self._test_connection()
    
    def _build_connection_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """构建连接参数"""
        params = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 5432),
            'database': config.get('database', 'mirexs'),
            'user': config.get('user', 'postgres'),
            'password': config.get('password', ''),
        }
        
        # 可选参数
        optional_params = [
            'sslmode', 'connect_timeout', 'application_name',
            'keepalives', 'keepalives_idle', 'keepalives_interval'
        ]
        
        for param in optional_params:
            if param in config:
                params[param] = config[param]
        
        return params
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()
                    self.logger.info(f"PostgreSQL connection successful: {version[0]}")
                    
        except Exception as e:
            self.logger.error(f"PostgreSQL connection test failed: {str(e)}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接（上下文管理器）
        
        Yields:
            psycopg2.Connection: 数据库连接
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            # 设置返回字典格式的游标
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            yield conn
        except Exception as e:
            self.logger.error(f"Failed to get database connection: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询语句
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict]: 查询结果
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    results = cursor.fetchall()
                    # 转换为普通字典
                    return [dict(row) for row in results]
                    
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_insert(self, table: str, data: Dict[str, Any], returning: str = "id") -> Any:
        """
        执行插入操作
        
        Args:
            table: 表名
            data: 插入数据
            returning: 返回字段
            
        Returns:
            Any: 返回字段的值
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建插入语句
                    columns = ', '.join(data.keys())
                    placeholders = ', '.join(['%s' for _ in data])
                    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    
                    if returning:
                        query += f" RETURNING {returning}"
                    
                    # 执行插入
                    cursor.execute(query, tuple(data.values()))
                    conn.commit()
                    
                    if returning:
                        result = cursor.fetchone()
                        return result[returning] if result else None
                    else:
                        return cursor.rowcount
                        
        except Exception as e:
            self.logger.error(f"Insert operation failed: {str(e)}")
            raise
    
    def execute_update(self, table: str, data: Dict[str, Any], 
                      where: str, where_params: Tuple = None) -> int:
        """
        执行更新操作
        
        Args:
            table: 表名
            data: 更新数据
            where: WHERE条件
            where_params: WHERE条件参数
            
        Returns:
            int: 影响的行数
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建更新语句
                    set_clause = ', '.join([f"{key} = %s" for key in data.keys()])
                    query = f"UPDATE {table} SET {set_clause} WHERE {where}"
                    
                    # 合并参数
                    params = tuple(data.values())
                    if where_params:
                        params += where_params
                    
                    # 执行更新
                    cursor.execute(query, params)
                    conn.commit()
                    
                    return cursor.rowcount
                    
        except Exception as e:
            self.logger.error(f"Update operation failed: {str(e)}")
            raise
    
    def execute_delete(self, table: str, where: str, where_params: Tuple = None) -> int:
        """
        执行删除操作
        
        Args:
            table: 表名
            where: WHERE条件
            where_params: WHERE条件参数
            
        Returns:
            int: 影响的行数
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    query = f"DELETE FROM {table} WHERE {where}"
                    
                    # 执行删除
                    if where_params:
                        cursor.execute(query, where_params)
                    else:
                        cursor.execute(query)
                        
                    conn.commit()
                    
                    return cursor.rowcount
                    
        except Exception as e:
            self.logger.error(f"Delete operation failed: {str(e)}")
            raise
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """
        执行批量操作
        
        Args:
            query: SQL语句
            params_list: 参数列表
            
        Returns:
            int: 影响的行数
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    conn.commit()
                    
                    return cursor.rowcount
                    
        except Exception as e:
            self.logger.error(f"Batch operation failed: {str(e)}")
            raise
    
    def create_table(self, table_name: str, schema: Dict[str, str], 
                    constraints: List[str] = None) -> bool:
        """
        创建表
        
        Args:
            table_name: 表名
            schema: 表结构 {列名: 数据类型}
            constraints: 约束条件列表
            
        Returns:
            bool: 创建是否成功
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建列定义
                    columns = []
                    for column_name, data_type in schema.items():
                        columns.append(f"{column_name} {data_type}")
                    
                    # 添加约束
                    if constraints:
                        columns.extend(constraints)
                    
                    # 构建创建表语句
                    columns_sql = ', '.join(columns)
                    query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})"
                    
                    cursor.execute(query)
                    conn.commit()
                    
                    self.logger.info(f"Table {table_name} created successfully")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to create table {table_name}: {str(e)}")
            return False
    
    def drop_table(self, table_name: str, cascade: bool = False) -> bool:
        """
        删除表
        
        Args:
            table_name: 表名
            cascade: 是否级联删除
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cascade_clause = " CASCADE" if cascade else ""
                    query = f"DROP TABLE IF EXISTS {table_name}{cascade_clause}"
                    
                    cursor.execute(query)
                    conn.commit()
                    
                    self.logger.info(f"Table {table_name} dropped successfully")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to drop table {table_name}: {str(e)}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 表是否存在
        """
        try:
            query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
            """
            
            results = self.execute_query(query, (table_name,))
            return results[0]['exists'] if results else False
            
        except Exception as e:
            self.logger.error(f"Failed to check table existence: {str(e)}")
            return False
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取表结构
        
        Args:
            table_name: 表名
            
        Returns:
            List[Dict]: 表结构信息
        """
        try:
            query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """
            
            return self.execute_query(query, (table_name,))
            
        except Exception as e:
            self.logger.error(f"Failed to get table schema: {str(e)}")
            return []
    
    def create_index(self, table_name: str, column_name: str, 
                    index_name: str = None, unique: bool = False) -> bool:
        """
        创建索引
        
        Args:
            table_name: 表名
            column_name: 列名
            index_name: 索引名称（可选）
            unique: 是否唯一索引
            
        Returns:
            bool: 创建是否成功
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    if not index_name:
                        index_name = f"idx_{table_name}_{column_name}"
                    
                    unique_clause = "UNIQUE " if unique else ""
                    query = f"CREATE {unique_clause}INDEX {index_name} ON {table_name} ({column_name})"
                    
                    cursor.execute(query)
                    conn.commit()
                    
                    self.logger.info(f"Index {index_name} created successfully")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to create index: {str(e)}")
            return False
    
    def execute_transaction(self, operations: List[Tuple[str, Tuple]]) -> bool:
        """
        执行事务操作
        
        Args:
            operations: 操作列表 [(query, params), ...]
            
        Returns:
            bool: 事务是否成功
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    for query, params in operations:
                        cursor.execute(query, params)
                    
                    conn.commit()
                    self.logger.info(f"Transaction completed: {len(operations)} operations")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Transaction failed: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 数据库统计信息
        """
        try:
            stats = {
                "connection_params": {k: '***' if k == 'password' else v 
                                   for k, v in self.connection_params.items()},
                "tables": [],
                "size": 0
            }
            
            # 获取表列表
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            """
            tables = self.execute_query(tables_query)
            stats["tables"] = [table['table_name'] for table in tables]
            
            # 获取数据库大小
            size_query = "SELECT pg_database_size(%s) as size"
            size_result = self.execute_query(size_query, (self.connection_params['database'],))
            if size_result:
                stats["size"] = size_result[0]['size']
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库（需要pg_dump工具）
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            import subprocess
            import os
            
            # 构建pg_dump命令
            cmd = [
                'pg_dump',
                '-h', self.connection_params['host'],
                '-p', str(self.connection_params['port']),
                '-U', self.connection_params['user'],
                '-d', self.connection_params['database'],
                '-f', backup_path,
                '-F', 'c'  # 自定义格式
            ]
            
            # 设置密码环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.connection_params['password']
            
            # 执行备份
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Database backed up to {backup_path}")
                return True
            else:
                self.logger.error(f"Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to backup database: {str(e)}")
            return False
