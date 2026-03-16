"""
SQLite集成模块 - 提供SQLite数据库的完整集成功能
"""

import logging
import sqlite3
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class SQLiteIntegration:
    """SQLite数据库集成类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化SQLite集成
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.db_path = config.get('db_path', 'mirexs.db')
        self.connection_pool = {}
        self.thread_local = threading.local()
        self.logger = logger
        
        # 数据库配置
        self.timeout = config.get('timeout', 30.0)
        self.check_same_thread = config.get('check_same_thread', False)
        self.isolation_level = config.get('isolation_level', None)
        
        # 连接参数
        self.connection_params = {
            'timeout': self.timeout,
            'check_same_thread': self.check_same_thread,
            'isolation_level': self.isolation_level
        }
        
        # 确保数据库目录存在
        self._ensure_db_directory()
        
        # 初始化数据库
        self._initialize_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            with self.get_connection() as conn:
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")
                
                # 启用WAL模式以提高并发性能
                conn.execute("PRAGMA journal_mode = WAL")
                
                # 设置缓存大小
                conn.execute("PRAGMA cache_size = -64000")  # 64MB
                
                # 设置同步模式
                conn.execute("PRAGMA synchronous = NORMAL")
                
                self.logger.info("SQLite database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize SQLite database: {str(e)}")
            raise
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接（线程安全）
        
        Returns:
            sqlite3.Connection: 数据库连接
        """
        try:
            # 使用线程局部存储确保每个线程有独立的连接
            if not hasattr(self.thread_local, 'connection'):
                self.thread_local.connection = sqlite3.connect(
                    self.db_path,
                    **self.connection_params
                )
                # 设置行工厂以返回字典
                self.thread_local.connection.row_factory = sqlite3.Row
                
            return self.thread_local.connection
            
        except Exception as e:
            self.logger.error(f"Failed to get database connection: {str(e)}")
            raise
    
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                # 获取列名
                columns = [description[0] for description in cursor.description] if cursor.description else []
                
                # 转换为字典列表
                results = []
                for row in cursor.fetchall():
                    result_dict = {}
                    for idx, column in enumerate(columns):
                        result_dict[column] = row[idx]
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        执行插入操作
        
        Args:
            table: 表名
            data: 插入数据
            
        Returns:
            int: 插入的行ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建插入语句
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                
                # 执行插入
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                
                return cursor.lastrowid
                
        except Exception as e:
            self.logger.error(f"Insert operation failed: {str(e)}")
            raise
    
    def execute_update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple = None) -> int:
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建更新语句
                set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.executemany(query, params_list)
                conn.commit()
                
                return cursor.rowcount
                
        except Exception as e:
            self.logger.error(f"Batch operation failed: {str(e)}")
            raise
    
    def create_table(self, table_name: str, schema: Dict[str, str], constraints: List[str] = None) -> bool:
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
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
    
    def drop_table(self, table_name: str) -> bool:
        """
        删除表
        
        Args:
            table_name: 表名
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = f"DROP TABLE IF EXISTS {table_name}"
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
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
            """
            
            results = self.execute_query(query, (table_name,))
            return len(results) > 0
            
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
            query = f"PRAGMA table_info({table_name})"
            return self.execute_query(query)
            
        except Exception as e:
            self.logger.error(f"Failed to get table schema: {str(e)}")
            return []
    
    def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 备份是否成功
        """
        try:
            import shutil
            import os
            
            # 确保备份目录存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # 复制数据库文件
            shutil.copy2(self.db_path, backup_path)
            
            self.logger.info(f"Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup database: {str(e)}")
            return False
    
    def vacuum_database(self) -> bool:
        """
        优化数据库（VACUUM）
        
        Returns:
            bool: 优化是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                conn.commit()
                
                self.logger.info("Database vacuum completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to vacuum database: {str(e)}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 数据库统计信息
        """
        try:
            stats = {
                "db_path": self.db_path,
                "tables": [],
                "total_size": 0,
                "page_count": 0,
                "page_size": 0
            }
            
            # 获取表列表
            tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables = self.execute_query(tables_query)
            stats["tables"] = [table['name'] for table in tables]
            
            # 获取数据库大小
            db_path = Path(self.db_path)
            if db_path.exists():
                stats["total_size"] = db_path.stat().st_size
            
            # 获取页面信息
            page_info = self.execute_query("PRAGMA page_count")
            if page_info:
                stats["page_count"] = page_info[0]['page_count']
            
            page_size = self.execute_query("PRAGMA page_size")
            if page_size:
                stats["page_size"] = page_size[0]['page_size']
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {}
    
    def close_connection(self):
        """关闭数据库连接"""
        try:
            if hasattr(self.thread_local, 'connection'):
                self.thread_local.connection.close()
                delattr(self.thread_local, 'connection')
                
            self.logger.info("Database connection closed")
            
        except Exception as e:
            self.logger.error(f"Failed to close database connection: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

