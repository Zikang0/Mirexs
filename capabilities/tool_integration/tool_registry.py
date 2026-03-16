"""
工具注册表模块
提供工具的统一注册、管理和发现功能
"""

import os
import sys
import json
import logging
import sqlite3
import threading
import hashlib
from typing import Dict, List, Any, Optional, Set, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import time
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class ToolCategory(Enum):
    """工具分类枚举"""
    WEB = "web"
    OFFICE = "office"
    DEVELOPMENT = "development"
    CREATIVE = "creative"
    SYSTEM = "system"
    CUSTOM = "custom"
    UTILITY = "utility"
    AI = "ai"
    DATA = "data"
    NETWORK = "network"

class ToolStatus(Enum):
    """工具状态枚举"""
    REGISTERED = "registered"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"

@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_id: str
    name: str
    version: str
    description: str
    author: str
    category: ToolCategory
    status: ToolStatus
    created_at: str
    updated_at: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    requirements: List[str]
    dependencies: List[str]
    tags: List[str]
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    license: Optional[str] = None
    repository: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['category'] = self.category.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolMetadata':
        """从字典创建实例"""
        data = data.copy()
        data['category'] = ToolCategory(data['category'])
        data['status'] = ToolStatus(data['status'])
        return cls(**data)

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self, db_path: str = "tool_registry.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化数据库"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 创建工具表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tools (
                        tool_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        description TEXT,
                        author TEXT,
                        category TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        input_schema TEXT,
                        output_schema TEXT,
                        requirements TEXT,
                        dependencies TEXT,
                        tags TEXT,
                        icon TEXT,
                        documentation_url TEXT,
                        license TEXT,
                        repository TEXT
                    )
                ''')
                
                # 创建工具使用统计表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tool_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tool_id TEXT NOT NULL,
                        execution_time TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        execution_duration REAL,
                        error_message TEXT,
                        user_id TEXT,
                        FOREIGN KEY (tool_id) REFERENCES tools (tool_id)
                    )
                ''')
                
                # 创建工具关系表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tool_relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_tool_id TEXT NOT NULL,
                        target_tool_id TEXT NOT NULL,
                        relationship_type TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (source_tool_id) REFERENCES tools (tool_id),
                        FOREIGN KEY (target_tool_id) REFERENCES tools (tool_id)
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tools_category ON tools(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_tool_id ON tool_usage(tool_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_time ON tool_usage(execution_time)')
                
                conn.commit()
                logger.info("工具注册表数据库初始化完成")
                
            except Exception as e:
                logger.error(f"数据库初始化失败: {e}")
                raise
            finally:
                conn.close()
    
    def register_tool(self, metadata: ToolMetadata) -> Dict[str, Any]:
        """注册工具"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 检查工具是否已存在
                cursor.execute('SELECT tool_id FROM tools WHERE tool_id = ?', (metadata.tool_id,))
                if cursor.fetchone():
                    return {"success": False, "error": f"工具ID已存在: {metadata.tool_id}"}
                
                # 插入工具数据
                cursor.execute('''
                    INSERT INTO tools (
                        tool_id, name, version, description, author, category, status,
                        created_at, updated_at, input_schema, output_schema, requirements,
                        dependencies, tags, icon, documentation_url, license, repository
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata.tool_id,
                    metadata.name,
                    metadata.version,
                    metadata.description,
                    metadata.author,
                    metadata.category.value,
                    metadata.status.value,
                    metadata.created_at,
                    metadata.updated_at,
                    json.dumps(metadata.input_schema),
                    json.dumps(metadata.output_schema),
                    json.dumps(metadata.requirements),
                    json.dumps(metadata.dependencies),
                    json.dumps(metadata.tags),
                    metadata.icon,
                    metadata.documentation_url,
                    metadata.license,
                    metadata.repository
                ))
                
                conn.commit()
                logger.info(f"工具注册成功: {metadata.name} ({metadata.tool_id})")
                
                return {
                    "success": True,
                    "tool_id": metadata.tool_id,
                    "message": f"工具 {metadata.name} 注册成功"
                }
                
            except Exception as e:
                conn.rollback()
                logger.error(f"工具注册失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def update_tool(self, tool_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新工具信息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 检查工具是否存在
                cursor.execute('SELECT tool_id FROM tools WHERE tool_id = ?', (tool_id,))
                if not cursor.fetchone():
                    return {"success": False, "error": f"工具不存在: {tool_id}"}
                
                # 构建更新语句
                update_fields = []
                update_values = []
                
                for field, value in updates.items():
                    if field in ['category', 'status']:
                        value = value.value if hasattr(value, 'value') else value
                    
                    if field in ['input_schema', 'output_schema', 'requirements', 'dependencies', 'tags']:
                        value = json.dumps(value)
                    
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
                
                # 添加更新时间
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())
                update_values.append(tool_id)
                
                # 执行更新
                query = f"UPDATE tools SET {', '.join(update_fields)} WHERE tool_id = ?"
                cursor.execute(query, update_values)
                
                conn.commit()
                logger.info(f"工具更新成功: {tool_id}")
                
                return {
                    "success": True,
                    "tool_id": tool_id,
                    "message": f"工具 {tool_id} 更新成功"
                }
                
            except Exception as e:
                conn.rollback()
                logger.error(f"工具更新失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def unregister_tool(self, tool_id: str) -> Dict[str, Any]:
        """注销工具"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 检查工具是否存在
                cursor.execute('SELECT name FROM tools WHERE tool_id = ?', (tool_id,))
                result = cursor.fetchone()
                if not result:
                    return {"success": False, "error": f"工具不存在: {tool_id}"}
                
                tool_name = result[0]
                
                # 删除工具相关数据
                cursor.execute('DELETE FROM tool_usage WHERE tool_id = ?', (tool_id,))
                cursor.execute('DELETE FROM tool_relationships WHERE source_tool_id = ? OR target_tool_id = ?', 
                             (tool_id, tool_id))
                cursor.execute('DELETE FROM tools WHERE tool_id = ?', (tool_id,))
                
                conn.commit()
                logger.info(f"工具注销成功: {tool_name} ({tool_id})")
                
                return {
                    "success": True,
                    "tool_id": tool_id,
                    "message": f"工具 {tool_name} 注销成功"
                }
                
            except Exception as e:
                conn.rollback()
                logger.error(f"工具注销失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def get_tool(self, tool_id: str) -> Optional[ToolMetadata]:
        """获取工具信息"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM tools WHERE tool_id = ?', (tool_id,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                # 构建ToolMetadata对象
                return self._row_to_tool_metadata(result)
                
            except Exception as e:
                logger.error(f"获取工具信息失败: {e}")
                return None
            finally:
                conn.close()
    
    def _row_to_tool_metadata(self, row) -> ToolMetadata:
        """将数据库行转换为ToolMetadata对象"""
        return ToolMetadata(
            tool_id=row[0],
            name=row[1],
            version=row[2],
            description=row[3],
            author=row[4],
            category=ToolCategory(row[5]),
            status=ToolStatus(row[6]),
            created_at=row[7],
            updated_at=row[8],
            input_schema=json.loads(row[9]) if row[9] else {},
            output_schema=json.loads(row[10]) if row[10] else {},
            requirements=json.loads(row[11]) if row[11] else [],
            dependencies=json.loads(row[12]) if row[12] else [],
            tags=json.loads(row[13]) if row[13] else [],
            icon=row[14],
            documentation_url=row[15],
            license=row[16],
            repository=row[17]
        )
    
    def list_tools(self, 
                  category: Optional[ToolCategory] = None,
                  status: Optional[ToolStatus] = None,
                  tags: Optional[List[str]] = None,
                  limit: int = 100,
                  offset: int = 0) -> List[ToolMetadata]:
        """列出工具"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 构建查询条件
                conditions = []
                params = []
                
                if category:
                    conditions.append("category = ?")
                    params.append(category.value)
                
                if status:
                    conditions.append("status = ?")
                    params.append(status.value)
                
                if tags:
                    for tag in tags:
                        conditions.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                query = f"SELECT * FROM tools WHERE {where_clause} ORDER BY name LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                tools = []
                for row in results:
                    try:
                        tool = self._row_to_tool_metadata(row)
                        tools.append(tool)
                    except Exception as e:
                        logger.warning(f"工具数据解析失败: {e}")
                        continue
                
                return tools
                
            except Exception as e:
                logger.error(f"列出工具失败: {e}")
                return []
            finally:
                conn.close()
    
    def search_tools(self, 
                    query: str,
                    search_fields: List[str] = None,
                    limit: int = 50) -> List[ToolMetadata]:
        """搜索工具"""
        if search_fields is None:
            search_fields = ["name", "description", "tags", "author"]
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 构建搜索条件
                conditions = []
                params = []
                
                for field in search_fields:
                    if field == "tags":
                        conditions.append("tags LIKE ?")
                        params.append(f'%"{query}"%')
                    else:
                        conditions.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")
                
                where_clause = " OR ".join(conditions)
                sql = f"SELECT * FROM tools WHERE {where_clause} ORDER BY name LIMIT ?"
                params.append(limit)
                
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                tools = []
                for row in results:
                    try:
                        tool = self._row_to_tool_metadata(row)
                        tools.append(tool)
                    except Exception as e:
                        logger.warning(f"工具数据解析失败: {e}")
                        continue
                
                return tools
                
            except Exception as e:
                logger.error(f"搜索工具失败: {e}")
                return []
            finally:
                conn.close()
    
    def record_usage(self, 
                    tool_id: str,
                    success: bool,
                    execution_duration: Optional[float] = None,
                    error_message: Optional[str] = None,
                    user_id: Optional[str] = None) -> Dict[str, Any]:
        """记录工具使用情况"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 检查工具是否存在
                cursor.execute('SELECT tool_id FROM tools WHERE tool_id = ?', (tool_id,))
                if not cursor.fetchone():
                    return {"success": False, "error": f"工具不存在: {tool_id}"}
                
                # 插入使用记录
                cursor.execute('''
                    INSERT INTO tool_usage (
                        tool_id, execution_time, success, execution_duration, error_message, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tool_id,
                    datetime.now().isoformat(),
                    success,
                    execution_duration,
                    error_message,
                    user_id
                ))
                
                conn.commit()
                return {"success": True, "message": "使用记录保存成功"}
                
            except Exception as e:
                conn.rollback()
                logger.error(f"使用记录保存失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def get_usage_statistics(self, 
                           tool_id: Optional[str] = None,
                           days: int = 30) -> Dict[str, Any]:
        """获取使用统计"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 计算时间范围
                cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
                cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()
                
                # 构建查询条件
                conditions = ["execution_time > ?"]
                params = [cutoff_iso]
                
                if tool_id:
                    conditions.append("tool_id = ?")
                    params.append(tool_id)
                
                where_clause = " AND ".join(conditions)
                
                # 获取基本统计
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_executions,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                        AVG(execution_duration) as avg_duration
                    FROM tool_usage 
                    WHERE {where_clause}
                ''', params)
                
                stats_result = cursor.fetchone()
                total, successful, avg_duration = stats_result
                
                # 获取按日期的使用统计
                cursor.execute(f'''
                    SELECT 
                        DATE(execution_time) as usage_date,
                        COUNT(*) as daily_count
                    FROM tool_usage 
                    WHERE {where_clause}
                    GROUP BY DATE(execution_time)
                    ORDER BY usage_date
                ''', params)
                
                daily_stats = cursor.fetchall()
                
                # 获取最常用的工具
                cursor.execute(f'''
                    SELECT 
                        tool_id,
                        COUNT(*) as usage_count
                    FROM tool_usage 
                    WHERE execution_time > ?
                    GROUP BY tool_id
                    ORDER BY usage_count DESC
                    LIMIT 10
                ''', [cutoff_iso])
                
                popular_tools = cursor.fetchall()
                
                return {
                    "success": True,
                    "statistics": {
                        "total_executions": total,
                        "successful_executions": successful,
                        "success_rate": successful / total if total > 0 else 0,
                        "average_duration": avg_duration or 0,
                        "period_days": days
                    },
                    "daily_usage": [
                        {"date": row[0], "count": row[1]} for row in daily_stats
                    ],
                    "popular_tools": [
                        {"tool_id": row[0], "usage_count": row[1]} for row in popular_tools
                    ]
                }
                
            except Exception as e:
                logger.error(f"获取使用统计失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def add_tool_relationship(self,
                            source_tool_id: str,
                            target_tool_id: str,
                            relationship_type: str) -> Dict[str, Any]:
        """添加工具关系"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 检查工具是否存在
                for tool_id in [source_tool_id, target_tool_id]:
                    cursor.execute('SELECT tool_id FROM tools WHERE tool_id = ?', (tool_id,))
                    if not cursor.fetchone():
                        return {"success": False, "error": f"工具不存在: {tool_id}"}
                
                # 检查关系是否已存在
                cursor.execute('''
                    SELECT id FROM tool_relationships 
                    WHERE source_tool_id = ? AND target_tool_id = ? AND relationship_type = ?
                ''', (source_tool_id, target_tool_id, relationship_type))
                
                if cursor.fetchone():
                    return {"success": False, "error": "关系已存在"}
                
                # 插入关系记录
                cursor.execute('''
                    INSERT INTO tool_relationships (
                        source_tool_id, target_tool_id, relationship_type, created_at
                    ) VALUES (?, ?, ?, ?)
                ''', (
                    source_tool_id,
                    target_tool_id,
                    relationship_type,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                return {"success": True, "message": "工具关系添加成功"}
                
            except Exception as e:
                conn.rollback()
                logger.error(f"工具关系添加失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()
    
    def get_tool_relationships(self, tool_id: str) -> Dict[str, Any]:
        """获取工具关系"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # 获取作为源工具的关系
                cursor.execute('''
                    SELECT target_tool_id, relationship_type 
                    FROM tool_relationships 
                    WHERE source_tool_id = ?
                ''', (tool_id,))
                
                outgoing = cursor.fetchall()
                
                # 获取作为目标工具的关系
                cursor.execute('''
                    SELECT source_tool_id, relationship_type 
                    FROM tool_relationships 
                    WHERE target_tool_id = ?
                ''', (tool_id,))
                
                incoming = cursor.fetchall()
                
                return {
                    "success": True,
                    "tool_id": tool_id,
                    "outgoing_relationships": [
                        {"target_tool_id": row[0], "relationship_type": row[1]} 
                        for row in outgoing
                    ],
                    "incoming_relationships": [
                        {"source_tool_id": row[0], "relationship_type": row[1]} 
                        for row in incoming
                    ]
                }
                
            except Exception as e:
                logger.error(f"获取工具关系失败: {e}")
                return {"success": False, "error": str(e)}
            finally:
                conn.close()

class ToolRegistryManager:
    """工具注册表管理器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._cache: Dict[str, ToolMetadata] = {}
        self._cache_ttl = 300  # 5分钟
        self._cache_timestamps: Dict[str, float] = {}
    
    def create_tool_metadata(self,
                           name: str,
                           description: str,
                           author: str,
                           category: ToolCategory,
                           input_schema: Dict[str, Any],
                           output_schema: Dict[str, Any],
                           version: str = "1.0.0",
                           status: ToolStatus = ToolStatus.REGISTERED,
                           requirements: List[str] = None,
                           dependencies: List[str] = None,
                           tags: List[str] = None,
                           **kwargs) -> ToolMetadata:
        """创建工具元数据"""
        tool_id = self._generate_tool_id(name, version)
        now = datetime.now().isoformat()
        
        return ToolMetadata(
            tool_id=tool_id,
            name=name,
            version=version,
            description=description,
            author=author,
            category=category,
            status=status,
            created_at=now,
            updated_at=now,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            requirements=requirements or [],
            dependencies=dependencies or [],
            tags=tags or [],
            **kwargs
        )
    
    def _generate_tool_id(self, name: str, version: str) -> str:
        """生成工具ID"""
        # 使用名称和版本生成确定性ID
        base_string = f"{name}_{version}".lower().replace(' ', '_')
        hash_object = hashlib.md5(base_string.encode())
        return f"tool_{hash_object.hexdigest()[:12]}"
    
    def register_tool_with_metadata(self, **kwargs) -> Dict[str, Any]:
        """使用元数据注册工具"""
        try:
            metadata = self.create_tool_metadata(**kwargs)
            return self.registry.register_tool(metadata)
        except Exception as e:
            logger.error(f"工具注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_tool_with_cache(self, tool_id: str) -> Optional[ToolMetadata]:
        """使用缓存获取工具信息"""
        now = time.time()
        
        # 检查缓存
        if (tool_id in self._cache and 
            tool_id in self._cache_timestamps and
            now - self._cache_timestamps[tool_id] < self._cache_ttl):
            return self._cache[tool_id]
        
        # 从注册表获取
        tool = self.registry.get_tool(tool_id)
        if tool:
            self._cache[tool_id] = tool
            self._cache_timestamps[tool_id] = now
        
        return tool
    
    def bulk_register_tools(self, tools_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量注册工具"""
        results = {
            "successful": [],
            "failed": []
        }
        
        for tool_data in tools_data:
            result = self.register_tool_with_metadata(**tool_data)
            if result["success"]:
                results["successful"].append({
                    "tool_id": result["tool_id"],
                    "name": tool_data["name"]
                })
            else:
                results["failed"].append({
                    "name": tool_data["name"],
                    "error": result["error"]
                })
        
        return {
            "success": True,
            "results": results,
            "total": len(tools_data),
            "successful": len(results["successful"]),
            "failed": len(results["failed"])
        }
    
    def export_tools(self, file_path: str, tool_ids: List[str] = None) -> Dict[str, Any]:
        """导出工具数据"""
        try:
            if tool_ids:
                tools = [self.registry.get_tool(tool_id) for tool_id in tool_ids]
                tools = [tool for tool in tools if tool is not None]
            else:
                tools = self.registry.list_tools()
            
            # 转换为可序列化的字典
            export_data = {
                "export_time": datetime.now().isoformat(),
                "tool_count": len(tools),
                "tools": [tool.to_dict() for tool in tools]
            }
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "file_path": file_path,
                "tool_count": len(tools),
                "message": f"成功导出 {len(tools)} 个工具到 {file_path}"
            }
            
        except Exception as e:
            logger.error(f"工具导出失败: {e}")
            return {"success": False, "error": str(e)}
    
    def import_tools(self, file_path: str) -> Dict[str, Any]:
        """导入工具数据"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "文件不存在"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "tools" not in import_data:
                return {"success": False, "error": "无效的导入文件格式"}
            
            tools_data = import_data["tools"]
            results = {
                "successful": [],
                "failed": []
            }
            
            for tool_dict in tools_data:
                try:
                    # 创建ToolMetadata对象
                    metadata = ToolMetadata.from_dict(tool_dict)
                    
                    # 注册工具
                    result = self.registry.register_tool(metadata)
                    if result["success"]:
                        results["successful"].append(metadata.tool_id)
                    else:
                        results["failed"].append({
                            "tool_id": metadata.tool_id,
                            "error": result["error"]
                        })
                        
                except Exception as e:
                    results["failed"].append({
                        "tool_id": tool_dict.get("tool_id", "unknown"),
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "results": results,
                "total": len(tools_data),
                "successful": len(results["successful"]),
                "failed": len(results["failed"])
            }
            
        except Exception as e:
            logger.error(f"工具导入失败: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_tool_compatibility(self, tool_id: str) -> Dict[str, Any]:
        """验证工具兼容性"""
        tool = self.get_tool_with_cache(tool_id)
        if not tool:
            return {"success": False, "error": f"工具不存在: {tool_id}"}
        
        compatibility_issues = []
        
        # 检查依赖项
        for dep in tool.dependencies:
            dep_tool = self.get_tool_with_cache(dep)
            if not dep_tool:
                compatibility_issues.append(f"依赖工具不存在: {dep}")
            elif dep_tool.status == ToolStatus.DEPRECATED:
                compatibility_issues.append(f"依赖工具已弃用: {dep}")
            elif dep_tool.status == ToolStatus.DISABLED:
                compatibility_issues.append(f"依赖工具已禁用: {dep}")
        
        # 检查输入输出schema
        if not tool.input_schema:
            compatibility_issues.append("缺少输入schema")
        
        if not tool.output_schema:
            compatibility_issues.append("缺少输出schema")
        
        return {
            "success": True,
            "tool_id": tool_id,
            "compatible": len(compatibility_issues) == 0,
            "issues": compatibility_issues,
            "recommendations": self._generate_compatibility_recommendations(compatibility_issues)
        }
    
    def _generate_compatibility_recommendations(self, issues: List[str]) -> List[str]:
        """生成兼容性建议"""
        recommendations = []
        
        for issue in issues:
            if "依赖工具不存在" in issue:
                recommendations.append("安装或注册缺失的依赖工具")
            elif "依赖工具已弃用" in issue:
                recommendations.append("寻找替代工具或更新依赖关系")
            elif "依赖工具已禁用" in issue:
                recommendations.append("启用依赖工具或寻找替代方案")
            elif "缺少输入schema" in issue:
                recommendations.append("定义输入参数schema以提高工具可靠性")
            elif "缺少输出schema" in issue:
                recommendations.append("定义输出数据schema以提高工具可靠性")
        
        return recommendations

# 使用示例
def demo_tool_registry():
    """演示工具注册表的使用"""
    registry = ToolRegistry()
    manager = ToolRegistryManager(registry)
    
    # 注册一个工具
    tool_metadata = manager.create_tool_metadata(
        name="图像处理器",
        description="提供基本的图像处理功能，包括调整大小、裁剪和滤镜",
        author="Mirexs Team",
        category=ToolCategory.CREATIVE,
        input_schema={
            "type": "object",
            "properties": {
                "image_path": {"type": "string"},
                "operation": {"type": "string", "enum": ["resize", "crop", "filter"]},
                "width": {"type": "integer"},
                "height": {"type": "integer"}
            },
            "required": ["image_path", "operation"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "output_path": {"type": "string"},
                "processing_time": {"type": "number"}
            }
        },
        requirements=["Pillow>=8.0.0"],
        tags=["image", "processing", "creative"],
        version="1.2.0"
    )
    
    result = registry.register_tool(tool_metadata)
    print("工具注册结果:", result)
    
    # 获取工具信息
    tool = registry.get_tool(tool_metadata.tool_id)
    if tool:
        print("工具信息:", tool.to_dict())
    
    # 记录使用情况
    registry.record_usage(
        tool_id=tool_metadata.tool_id,
        success=True,
        execution_duration=2.5,
        user_id="user123"
    )
    
    # 获取使用统计
    stats = registry.get_usage_statistics()
    print("使用统计:", stats)

if __name__ == "__main__":
    demo_tool_registry()

