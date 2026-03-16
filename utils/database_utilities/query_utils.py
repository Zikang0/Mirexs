"""
查询工具模块

提供数据库查询构建和优化工具。
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from abc import ABC, abstractmethod
import re
from datetime import datetime
import json


class QueryBuilder:
    """SQL查询构建器"""
    
    def __init__(self, table_name: str = None):
        """初始化查询构建器
        
        Args:
            table_name: 表名
        """
        self.table_name = table_name
        self.query_parts = {
            'select': [],
            'from': table_name,
            'join': [],
            'where': [],
            'group_by': [],
            'having': [],
            'order_by': [],
            'limit': None,
            'offset': None
        }
        self.params = []
    
    def select(self, *columns) -> 'QueryBuilder':
        """添加SELECT子句
        
        Args:
            *columns: 要选择的列
            
        Returns:
            QueryBuilder实例
        """
        if columns:
            self.query_parts['select'].extend(columns)
        else:
            self.query_parts['select'].append('*')
        return self
    
    def from_table(self, table_name: str) -> 'QueryBuilder':
        """设置FROM子句
        
        Args:
            table_name: 表名
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['from'] = table_name
        return self
    
    def join(self, table: str, condition: str, join_type: str = 'INNER') -> 'QueryBuilder':
        """添加JOIN子句
        
        Args:
            table: 连接表名
            condition: 连接条件
            join_type: 连接类型 (INNER, LEFT, RIGHT, FULL)
            
        Returns:
            QueryBuilder实例
        """
        join_clause = f"{join_type} JOIN {table} ON {condition}"
        self.query_parts['join'].append(join_clause)
        return self
    
    def where(self, condition: str, *params) -> 'QueryBuilder':
        """添加WHERE子句
        
        Args:
            condition: WHERE条件
            *params: 参数值
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['where'].append(condition)
        self.params.extend(params)
        return self
    
    def and_where(self, condition: str, *params) -> 'QueryBuilder':
        """添加AND WHERE子句
        
        Args:
            condition: WHERE条件
            *params: 参数值
            
        Returns:
            QueryBuilder实例
        """
        if self.query_parts['where']:
            condition = f"AND {condition}"
        return self.where(condition, *params)
    
    def or_where(self, condition: str, *params) -> 'QueryBuilder':
        """添加OR WHERE子句
        
        Args:
            condition: WHERE条件
            *params: 参数值
            
        Returns:
            QueryBuilder实例
        """
        if self.query_parts['where']:
            condition = f"OR {condition}"
        return self.where(condition, *params)
    
    def group_by(self, *columns) -> 'QueryBuilder':
        """添加GROUP BY子句
        
        Args:
            *columns: 分组列
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['group_by'].extend(columns)
        return self
    
    def having(self, condition: str, *params) -> 'QueryBuilder':
        """添加HAVING子句
        
        Args:
            condition: HAVING条件
            *params: 参数值
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['having'].append(condition)
        self.params.extend(params)
        return self
    
    def order_by(self, column: str, direction: str = 'ASC') -> 'QueryBuilder':
        """添加ORDER BY子句
        
        Args:
            column: 排序列
            direction: 排序方向 (ASC, DESC)
            
        Returns:
            QueryBuilder实例
        """
        order_clause = f"{column} {direction}"
        self.query_parts['order_by'].append(order_clause)
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """添加LIMIT子句
        
        Args:
            count: 限制数量
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['limit'] = count
        return self
    
    def offset(self, count: int) -> 'QueryBuilder':
        """添加OFFSET子句
        
        Args:
            count: 偏移量
            
        Returns:
            QueryBuilder实例
        """
        self.query_parts['offset'] = count
        return self
    
    def build(self) -> Tuple[str, List[Any]]:
        """构建SQL查询
        
        Returns:
            (SQL查询字符串, 参数列表)
        """
        query_parts = []
        params = []
        
        # SELECT
        if self.query_parts['select']:
            select_clause = "SELECT " + ", ".join(self.query_parts['select'])
            query_parts.append(select_clause)
        
        # FROM
        if self.query_parts['from']:
            query_parts.append(f"FROM {self.query_parts['from']}")
        
        # JOIN
        if self.query_parts['join']:
            query_parts.extend(self.query_parts['join'])
        
        # WHERE
        if self.query_parts['where']:
            where_clause = "WHERE " + " ".join(self.query_parts['where'])
            query_parts.append(where_clause)
        
        # GROUP BY
        if self.query_parts['group_by']:
            group_clause = "GROUP BY " + ", ".join(self.query_parts['group_by'])
            query_parts.append(group_clause)
        
        # HAVING
        if self.query_parts['having']:
            having_clause = "HAVING " + " ".join(self.query_parts['having'])
            query_parts.append(having_clause)
        
        # ORDER BY
        if self.query_parts['order_by']:
            order_clause = "ORDER BY " + ", ".join(self.query_parts['order_by'])
            query_parts.append(order_clause)
        
        # LIMIT
        if self.query_parts['limit'] is not None:
            query_parts.append(f"LIMIT {self.query_parts['limit']}")
        
        # OFFSET
        if self.query_parts['offset'] is not None:
            query_parts.append(f"OFFSET {self.query_parts['offset']}")
        
        query = " ".join(query_parts)
        params = self.params.copy()
        
        return query, params
    
    def __str__(self) -> str:
        """返回SQL查询字符串"""
        query, _ = self.build()
        return query


class InsertQueryBuilder:
    """插入查询构建器"""
    
    def __init__(self, table_name: str):
        """初始化插入查询构建器
        
        Args:
            table_name: 表名
        """
        self.table_name = table_name
        self.columns = []
        self.values = []
        self.params = []
    
    def insert(self, data: Dict[str, Any]) -> 'InsertQueryBuilder':
        """插入单条数据
        
        Args:
            data: 数据字典
            
        Returns:
            InsertQueryBuilder实例
        """
        if not self.columns:
            self.columns = list(data.keys())
        
        values = [data[col] for col in self.columns]
        self.values.append(values)
        self.params.extend(values)
        return self
    
    def insert_many(self, data_list: List[Dict[str, Any]]) -> 'InsertQueryBuilder':
        """批量插入数据
        
        Args:
            data_list: 数据字典列表
            
        Returns:
            InsertQueryBuilder实例
        """
        if not self.columns:
            self.columns = list(data_list[0].keys())
        
        for data in data_list:
            values = [data[col] for col in self.columns]
            self.values.append(values)
            self.params.extend(values)
        return self
    
    def build(self) -> Tuple[str, List[Any]]:
        """构建插入SQL查询
        
        Returns:
            (SQL查询字符串, 参数列表)
        """
        if not self.columns or not self.values:
            raise ValueError("No data to insert")
        
        # 构建列名
        columns_str = ", ".join(self.columns)
        
        # 构建占位符
        placeholders = []
        for _ in self.values:
            row_placeholders = "(" + ", ".join(["?"] * len(self.columns)) + ")"
            placeholders.append(row_placeholders)
        
        values_str = ", ".join(placeholders)
        
        query = f"INSERT INTO {self.table_name} ({columns_str}) VALUES {values_str}"
        
        return query, self.params


class UpdateQueryBuilder:
    """更新查询构建器"""
    
    def __init__(self, table_name: str):
        """初始化更新查询构建器
        
        Args:
            table_name: 表名
        """
        self.table_name = table_name
        self.set_clauses = []
        self.where_clauses = []
        self.params = []
    
    def set(self, column: str, value: Any) -> 'UpdateQueryBuilder':
        """设置更新字段
        
        Args:
            column: 列名
            value: 值
            
        Returns:
            UpdateQueryBuilder实例
        """
        self.set_clauses.append(f"{column} = ?")
        self.params.append(value)
        return self
    
    def where(self, condition: str, *params) -> 'UpdateQueryBuilder':
        """添加WHERE条件
        
        Args:
            condition: WHERE条件
            *params: 参数值
            
        Returns:
            UpdateQueryBuilder实例
        """
        self.where_clauses.append(condition)
        self.params.extend(params)
        return self
    
    def build(self) -> Tuple[str, List[Any]]:
        """构建更新SQL查询
        
        Returns:
            (SQL查询字符串, 参数列表)
        """
        if not self.set_clauses:
            raise ValueError("No fields to update")
        
        # 构建SET子句
        set_clause = "SET " + ", ".join(self.set_clauses)
        
        # 构建WHERE子句
        where_clause = ""
        if self.where_clauses:
            where_clause = "WHERE " + " ".join(self.where_clauses)
        
        query = f"UPDATE {self.table_name} {set_clause} {where_clause}".strip()
        
        return query, self.params


class DeleteQueryBuilder:
    """删除查询构建器"""
    
    def __init__(self, table_name: str):
        """初始化删除查询构建器
        
        Args:
            table_name: 表名
        """
        self.table_name = table_name
        self.where_clauses = []
        self.params = []
    
    def where(self, condition: str, *params) -> 'DeleteQueryBuilder':
        """添加WHERE条件
        
        Args:
            condition: WHERE条件
            *params: 参数值
            
        Returns:
            DeleteQueryBuilder实例
        """
        self.where_clauses.append(condition)
        self.params.extend(params)
        return self
    
    def build(self) -> Tuple[str, List[Any]]:
        """构建删除SQL查询
        
        Returns:
            (SQL查询字符串, 参数列表)
        """
        where_clause = ""
        if self.where_clauses:
            where_clause = "WHERE " + " ".join(self.where_clauses)
        
        query = f"DELETE FROM {self.table_name} {where_clause}".strip()
        
        return query, self.params


class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def analyze_query(query: str) -> Dict[str, Any]:
        """分析查询语句
        
        Args:
            query: SQL查询语句
            
        Returns:
            查询分析结果
        """
        analysis = {
            'query_type': QueryOptimizer._detect_query_type(query),
            'tables': QueryOptimizer._extract_tables(query),
            'columns': QueryOptimizer._extract_columns(query),
            'conditions': QueryOptimizer._extract_conditions(query),
            'joins': QueryOptimizer._extract_joins(query),
            'potential_issues': []
        }
        
        # 检查潜在问题
        analysis['potential_issues'] = QueryOptimizer._check_potential_issues(query)
        
        return analysis
    
    @staticmethod
    def _detect_query_type(query: str) -> str:
        """检测查询类型"""
        query_upper = query.strip().upper()
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'UNKNOWN'
    
    @staticmethod
    def _extract_tables(query: str) -> List[str]:
        """提取表名"""
        tables = []
        
        # 简单的FROM子句解析
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))
        
        # 解析JOIN子句
        join_matches = re.findall(r'(?:INNER|LEFT|RIGHT|FULL)\s+JOIN\s+(\w+)', query, re.IGNORECASE)
        tables.extend(join_matches)
        
        return list(set(tables))
    
    @staticmethod
    def _extract_columns(query: str) -> List[str]:
        """提取列名"""
        columns = []
        
        # 解析SELECT子句
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            # 简单的列名提取
            col_matches = re.findall(r'(\w+(?:\.\w+)?)', select_clause)
            columns.extend(col_matches)
        
        return list(set(columns))
    
    @staticmethod
    def _extract_conditions(query: str) -> List[str]:
        """提取条件"""
        conditions = []
        
        # 解析WHERE子句
        where_match = re.search(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # 简单的条件提取
            conditions.append(where_clause.strip())
        
        return conditions
    
    @staticmethod
    def _extract_joins(query: str) -> List[Dict[str, str]]:
        """提取连接信息"""
        joins = []
        
        # 解析JOIN子句
        join_pattern = r'(INNER|LEFT|RIGHT|FULL)\s+JOIN\s+(\w+)\s+ON\s+(.+?)(?=\s+(?:INNER|LEFT|RIGHT|FULL|WHERE|GROUP|ORDER|LIMIT|$))'
        join_matches = re.findall(join_pattern, query, re.IGNORECASE | re.DOTALL)
        
        for join_type, table, condition in join_matches:
            joins.append({
                'type': join_type.upper(),
                'table': table,
                'condition': condition.strip()
            })
        
        return joins
    
    @staticmethod
    def _check_potential_issues(query: str) -> List[str]:
        """检查潜在问题"""
        issues = []
        
        # 检查SELECT *
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            issues.append("使用SELECT *可能影响性能，建议明确指定需要的列")
        
        # 检查没有WHERE条件的UPDATE/DELETE
        if re.search(r'(UPDATE|DELETE)\s+\w+\s+FROM', query, re.IGNORECASE):
            if 'WHERE' not in query.upper():
                issues.append("UPDATE/DELETE语句没有WHERE条件，可能影响所有数据")
        
        # 检查子查询
        if 'SELECT' in query.upper() and '(' in query:
            issues.append("检测到子查询，可能影响性能，考虑使用JOIN优化")
        
        # 检查LIKE通配符
        if re.search(r'LIKE\s+[\'"]%', query, re.IGNORECASE):
            issues.append("LIKE查询以%开头无法使用索引，考虑使用全文搜索")
        
        return issues
    
    @staticmethod
    def suggest_indexes(query: str) -> List[Dict[str, Any]]:
        """建议索引
        
        Args:
            query: SQL查询语句
            
        Returns:
            索引建议列表
        """
        suggestions = []
        
        # 分析WHERE条件中的列
        where_match = re.search(r'WHERE\s+(.+?)(?:GROUP|ORDER|LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            
            # 提取WHERE条件中的列
            column_matches = re.findall(r'(\w+(?:\.\w+)?)\s*=', where_clause)
            for column in set(column_matches):
                suggestions.append({
                    'type': 'INDEX',
                    'column': column,
                    'reason': 'WHERE条件中使用的列，建议创建索引'
                })
        
        # 分析ORDER BY列
        order_match = re.search(r'ORDER\s+BY\s+(.+?)(?:LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if order_match:
            order_clause = order_match.group(1)
            columns = [col.strip() for col in order_clause.split(',')]
            
            for column in columns:
                # 移除排序方向
                column = column.split()[0]
                suggestions.append({
                    'type': 'INDEX',
                    'column': column,
                    'reason': 'ORDER BY中使用的列，建议创建索引以优化排序'
                })
        
        return suggestions


class QueryValidator:
    """查询验证器"""
    
    @staticmethod
    def validate_query(query: str, query_type: str = None) -> Dict[str, Any]:
        """验证查询语句
        
        Args:
            query: SQL查询语句
            query_type: 期望的查询类型
            
        Returns:
            验证结果
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        # 检查基本语法
        if not query.strip():
            validation_result['is_valid'] = False
            validation_result['errors'].append("查询语句不能为空")
            return validation_result
        
        # 检查查询类型
        detected_type = QueryOptimizer._detect_query_type(query)
        if query_type and detected_type != query_type.upper():
            validation_result['warnings'].append(f"期望的查询类型是{query_type}，但检测到的是{detected_type}")
        
        # 检查SQL注入风险
        injection_risk = QueryValidator._check_sql_injection_risk(query)
        if injection_risk['risk_level'] > 0:
            validation_result['warnings'].append(f"存在SQL注入风险: {injection_risk['issues']}")
        
        # 检查性能问题
        performance_issues = QueryValidator._check_performance_issues(query)
        if performance_issues:
            validation_result['warnings'].extend(performance_issues)
        
        # 生成建议
        if detected_type == 'SELECT':
            validation_result['suggestions'] = QueryOptimizer.suggest_indexes(query)
        
        return validation_result
    
    @staticmethod
    def _check_sql_injection_risk(query: str) -> Dict[str, Any]:
        """检查SQL注入风险"""
        risk_level = 0
        issues = []
        
        # 检查危险关键字
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE']
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', query, re.IGNORECASE):
                risk_level = max(risk_level, 3)
                issues.append(f"检测到危险关键字: {keyword}")
        
        # 检查注释
        if '--' in query or '/*' in query:
            risk_level = max(risk_level, 2)
            issues.append("检测到SQL注释")
        
        # 检查多个语句
        if ';' in query.strip():
            risk_level = max(risk_level, 2)
            issues.append("检测到多个SQL语句")
        
        return {
            'risk_level': risk_level,
            'issues': issues
        }
    
    @staticmethod
    def _check_performance_issues(query: str) -> List[str]:
        """检查性能问题"""
        issues = []
        
        # 检查SELECT *
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            issues.append("使用SELECT *可能影响性能")
        
        # 检查没有WHERE条件的全表扫描
        if re.search(r'SELECT\s+\w+', query, re.IGNORECASE):
            if 'WHERE' not in query.upper():
                issues.append("没有WHERE条件，可能导致全表扫描")
        
        # 检查LIKE通配符
        if re.search(r'LIKE\s+[\'"]%', query, re.IGNORECASE):
            issues.append("LIKE查询以%开头无法使用索引")
        
        return issues


class QueryLogger:
    """查询日志记录器"""
    
    def __init__(self, log_file: str = None):
        """初始化查询日志记录器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self.queries = []
    
    def log_query(self, query: str, execution_time: float, 
                 row_count: int = None, error: str = None):
        """记录查询
        
        Args:
            query: SQL查询语句
            execution_time: 执行时间（秒）
            row_count: 返回行数
            error: 错误信息
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'execution_time': execution_time,
            'row_count': row_count,
            'error': error
        }
        
        self.queries.append(log_entry)
        
        # 如果有日志文件，写入文件
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            except Exception:
                pass  # 静默处理文件写入错误
    
    def get_query_stats(self) -> Dict[str, Any]:
        """获取查询统计信息
        
        Returns:
            统计信息字典
        """
        if not self.queries:
            return {}
        
        execution_times = [q['execution_time'] for q in self.queries if q['execution_time'] is not None]
        row_counts = [q['row_count'] for q in self.queries if q['row_count'] is not None]
        
        return {
            'total_queries': len(self.queries),
            'successful_queries': len([q for q in self.queries if q['error'] is None]),
            'failed_queries': len([q for q in self.queries if q['error'] is not None]),
            'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'max_execution_time': max(execution_times) if execution_times else 0,
            'min_execution_time': min(execution_times) if execution_times else 0,
            'avg_row_count': sum(row_counts) / len(row_counts) if row_counts else 0,
            'total_rows': sum(row_counts) if row_counts else 0
        }
    
    def get_slow_queries(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """获取慢查询
        
        Args:
            threshold: 时间阈值（秒）
            
        Returns:
            慢查询列表
        """
        return [
            q for q in self.queries 
            if q['execution_time'] is not None and q['execution_time'] > threshold
        ]
    
    def clear_logs(self):
        """清除日志"""
        self.queries.clear()


def build_select_query(table: str, columns: List[str] = None, 
                      where: str = None, params: List[Any] = None,
                      order_by: str = None, limit: int = None) -> Tuple[str, List[Any]]:
    """构建SELECT查询
    
    Args:
        table: 表名
        columns: 列名列表
        where: WHERE条件
        params: 参数列表
        order_by: 排序字段
        limit: 限制数量
        
    Returns:
        (SQL查询字符串, 参数列表)
    """
    builder = QueryBuilder(table)
    
    if columns:
        builder.select(*columns)
    else:
        builder.select('*')
    
    if where:
        builder.where(where, *(params or []))
    
    if order_by:
        parts = order_by.split()
        column = parts[0]
        direction = parts[1] if len(parts) > 1 else 'ASC'
        builder.order_by(column, direction)
    
    if limit:
        builder.limit(limit)
    
    return builder.build()


def build_insert_query(table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Tuple[str, List[Any]]:
    """构建INSERT查询
    
    Args:
        table: 表名
        data: 要插入的数据
        
    Returns:
        (SQL查询字符串, 参数列表)
    """
    builder = InsertQueryBuilder(table)
    
    if isinstance(data, dict):
        builder.insert(data)
    else:
        builder.insert_many(data)
    
    return builder.build()


def build_update_query(table: str, data: Dict[str, Any], 
                      where: str, params: List[Any] = None) -> Tuple[str, List[Any]]:
    """构建UPDATE查询
    
    Args:
        table: 表名
        data: 要更新的数据
        where: WHERE条件
        params: 参数列表
        
    Returns:
        (SQL查询字符串, 参数列表)
    """
    builder = UpdateQueryBuilder(table)
    
    for column, value in data.items():
        builder.set(column, value)
    
    builder.where(where, *(params or []))
    
    return builder.build()


def build_delete_query(table: str, where: str, params: List[Any] = None) -> Tuple[str, List[Any]]:
    """构建DELETE查询
    
    Args:
        table: 表名
        where: WHERE条件
        params: 参数列表
        
    Returns:
        (SQL查询字符串, 参数列表)
    """
    builder = DeleteQueryBuilder(table)
    builder.where(where, *(params or []))
    
    return builder.build()