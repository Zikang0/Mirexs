"""
数据库连接工具模块

提供数据库连接和操作工具。
"""

from typing import List, Dict, Any, Optional, Union, Tuple, Callable
import sqlite3
import psycopg2
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text
from contextlib import contextmanager
import logging


class DatabaseConnection:
    """数据库连接基类"""
    
    def __init__(self, connection_string: str):
        """初始化数据库连接
        
        Args:
            connection_string: 数据库连接字符串
        """
        self.connection_string = connection_string
        self.connection = None
        self.engine = None
    
    def connect(self) -> Any:
        """建立数据库连接
        
        Returns:
            数据库连接对象
        """
        raise NotImplementedError
    
    def disconnect(self) -> None:
        """断开数据库连接"""
        raise NotImplementedError
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = None
        try:
            conn = self.connect()
            yield conn
        finally:
            if conn:
                conn.close()


class SQLiteConnection(DatabaseConnection):
    """SQLite数据库连接"""
    
    def connect(self) -> sqlite3.Connection:
        """建立SQLite数据库连接"""
        self.connection = sqlite3.connect(self.connection_string)
        self.connection.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        return self.connection
    
    def disconnect(self) -> None:
        """断开SQLite数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL数据库连接"""
    
    def connect(self) -> psycopg2.extensions.connection:
        """建立PostgreSQL数据库连接"""
        self.connection = psycopg2.connect(self.connection_string)
        return self.connection
    
    def disconnect(self) -> None:
        """断开PostgreSQL数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


class MySQLConnection(DatabaseConnection):
    """MySQL数据库连接"""
    
    def connect(self) -> pymysql.connections.Connection:
        """建立MySQL数据库连接"""
        self.connection = pymysql.connect(**self._parse_connection_string())
        return self.connection
    
    def disconnect(self) -> None:
        """断开MySQL数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def _parse_connection_string(self) -> Dict[str, Any]:
        """解析MySQL连接字符串"""
        # 简单的解析逻辑，实际应用中可能需要更复杂的解析
        parts = self.connection_string.split(';')
        params = {}
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                params[key.strip()] = value.strip()
        return params


class SQLAlchemyConnection(DatabaseConnection):
    """SQLAlchemy数据库连接"""
    
    def connect(self):
        """建立SQLAlchemy数据库连接"""
        self.engine = create_engine(self.connection_string)
        self.connection = self.engine.connect()
        return self.connection
    
    def disconnect(self) -> None:
        """断开SQLAlchemy数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.engine:
            self.engine.dispose()


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, connection_string: str, db_type: str = 'sqlite'):
        """初始化数据库管理器
        
        Args:
            connection_string: 数据库连接字符串
            db_type: 数据库类型 ('sqlite', 'postgresql', 'mysql', 'sqlalchemy')
        """
        self.connection_string = connection_string
        self.db_type = db_type.lower()
        
        # 创建连接对象
        if self.db_type == 'sqlite':
            self.db_connection = SQLiteConnection(connection_string)
        elif self.db_type == 'postgresql':
            self.db_connection = PostgreSQLConnection(connection_string)
        elif self.db_type == 'mysql':
            self.db_connection = MySQLConnection(connection_string)
        elif self.db_type == 'sqlalchemy':
            self.db_connection = SQLAlchemyConnection(connection_string)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询SQL
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        with self.db_connection.get_connection() as conn:
            if self.db_type == 'sqlalchemy':
                result = conn.execute(text(query), params or {})
                return [dict(row._mapping) for row in result]
            else:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新SQL
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        with self.db_connection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行SQL
        
        Args:
            query: SQL语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        with self.db_connection.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
    
    def execute_transaction(self, queries: List[Tuple[str, tuple]]) -> bool:
        """执行事务
        
        Args:
            queries: 查询列表 [(query, params), ...]
            
        Returns:
            是否执行成功
        """
        with self.db_connection.get_connection() as conn:
            try:
                cursor = conn.cursor()
                for query, params in queries:
                    cursor.execute(query, params or ())
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logging.error(f"Transaction failed: {e}")
                return False
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息
        """
        if self.db_type == 'sqlite':
            query = "PRAGMA table_info(?)"
        elif self.db_type == 'postgresql':
            query = """
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = ?
            """
        elif self.db_type == 'mysql':
            query = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ?
            """
        else:
            # SQLAlchemy的情况
            query = f"DESCRIBE {table_name}"
        
        return self.execute_query(query, (table_name,))
    
    def get_tables(self) -> List[str]:
        """获取所有表名
        
        Returns:
            表名列表
        """
        if self.db_type == 'sqlite':
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        elif self.db_type == 'postgresql':
            query = "SELECT tablename FROM pg_tables WHERE schemaname='public'"
        elif self.db_type == 'mysql':
            query = "SHOW TABLES"
        else:
            query = "SHOW TABLES"
        
        results = self.execute_query(query)
        if self.db_type == 'sqlite':
            return [row['name'] for row in results]
        else:
            return list(results[0].values()) if results else []
    
    def create_table(self, table_name: str, columns: Dict[str, str], 
                    primary_key: str = None) -> bool:
        """创建表
        
        Args:
            table_name: 表名
            columns: 列定义 {列名: 数据类型}
            primary_key: 主键列名
            
        Returns:
            是否创建成功
        """
        column_defs = []
        for col_name, col_type in columns.items():
            if primary_key and col_name == primary_key:
                column_defs.append(f"{col_name} {col_type} PRIMARY KEY")
            else:
                column_defs.append(f"{col_name} {col_type}")
        
        columns_str = ", ".join(column_defs)
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        
        try:
            self.execute_update(query)
            return True
        except Exception as e:
            logging.error(f"Failed to create table {table_name}: {e}")
            return False
    
    def drop_table(self, table_name: str) -> bool:
        """删除表
        
        Args:
            table_name: 表名
            
        Returns:
            是否删除成功
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        
        try:
            self.execute_update(query)
            return True
        except Exception as e:
            logging.error(f"Failed to drop table {table_name}: {e}")
            return False
    
    def insert_data(self, table_name: str, data: Union[List[Dict], Dict]) -> bool:
        """插入数据
        
        Args:
            table_name: 表名
            data: 要插入的数据
            
        Returns:
            是否插入成功
        """
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return False
        
        # 获取列名
        columns = list(data[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        column_names = ", ".join(columns)
        
        query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        # 准备参数
        params_list = []
        for row in data:
            params_list.append(tuple(row[col] for col in columns))
        
        try:
            self.execute_many(query, params_list)
            return True
        except Exception as e:
            logging.error(f"Failed to insert data into {table_name}: {e}")
            return False
    
    def update_data(self, table_name: str, data: Dict[str, Any], 
                   where_clause: str, where_params: tuple = None) -> bool:
        """更新数据
        
        Args:
            table_name: 表名
            data: 更新数据
            where_clause: WHERE条件
            where_params: WHERE参数
            
        Returns:
            是否更新成功
        """
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        
        params = list(data.values())
        if where_params:
            params.extend(where_params)
        
        try:
            self.execute_update(query, tuple(params))
            return True
        except Exception as e:
            logging.error(f"Failed to update data in {table_name}: {e}")
            return False
    
    def delete_data(self, table_name: str, where_clause: str, 
                   where_params: tuple = None) -> bool:
        """删除数据
        
        Args:
            table_name: 表名
            where_clause: WHERE条件
            where_params: WHERE参数
            
        Returns:
            是否删除成功
        """
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        
        try:
            self.execute_update(query, where_params)
            return True
        except Exception as e:
            logging.error(f"Failed to delete data from {table_name}: {e}")
            return False
    
    def read_to_dataframe(self, query: str, params: tuple = None) -> pd.DataFrame:
        """将查询结果读取为DataFrame
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            DataFrame对象
        """
        results = self.execute_query(query, params)
        return pd.DataFrame(results)
    
    def write_from_dataframe(self, df: pd.DataFrame, table_name: str, 
                           if_exists: str = 'replace') -> bool:
        """将DataFrame写入数据库
        
        Args:
            df: DataFrame对象
            table_name: 表名
            if_exists: 如果表存在的处理方式 ('replace', 'append', 'fail')
            
        Returns:
            是否写入成功
        """
        try:
            if self.db_type == 'sqlalchemy':
                df.to_sql(table_name, self.db_connection.engine, 
                         if_exists=if_exists, index=False)
            else:
                # 对于其他数据库，使用临时SQLAlchemy引擎
                engine = create_engine(self.connection_string)
                df.to_sql(table_name, engine, if_exists=if_exists, index=False)
                engine.dispose()
            return True
        except Exception as e:
            logging.error(f"Failed to write DataFrame to {table_name}: {e}")
            return False


class DatabaseMigrator:
    """数据库迁移工具"""
    
    def __init__(self, db_manager: DatabaseManager):
        """初始化迁移工具
        
        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
    
    def create_migration_table(self) -> bool:
        """创建迁移记录表"""
        query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
        """
        return self.db_manager.execute_update(query) >= 0
    
    def apply_migration(self, version: str, sql_script: str, 
                       description: str = None) -> bool:
        """应用迁移
        
        Args:
            version: 迁移版本
            sql_script: SQL脚本
            description: 迁移描述
            
        Returns:
            是否应用成功
        """
        # 检查是否已经应用过
        check_query = "SELECT COUNT(*) as count FROM schema_migrations WHERE version = ?"
        result = self.db_manager.execute_query(check_query, (version,))
        
        if result[0]['count'] > 0:
            logging.info(f"Migration {version} already applied")
            return True
        
        # 应用迁移
        success = self.db_manager.execute_transaction([
            (sql_script, ()),
            ("INSERT INTO schema_migrations (version, description) VALUES (?, ?)", 
             (version, description))
        ])
        
        if success:
            logging.info(f"Migration {version} applied successfully")
        else:
            logging.error(f"Failed to apply migration {version}")
        
        return success
    
    def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史
        
        Returns:
            迁移历史列表
        """
        query = "SELECT * FROM schema_migrations ORDER BY applied_at"
        return self.db_manager.execute_query(query)


def create_database_manager(db_config: Dict[str, Any]) -> DatabaseManager:
    """创建数据库管理器
    
    Args:
        db_config: 数据库配置
        
    Returns:
        数据库管理器
    """
    db_type = db_config.get('type', 'sqlite')
    
    if db_type == 'sqlite':
        connection_string = db_config['path']
    elif db_type == 'postgresql':
        connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    elif db_type == 'mysql':
        connection_string = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    elif db_type == 'sqlalchemy':
        connection_string = db_config['connection_string']
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return DatabaseManager(connection_string, db_type)