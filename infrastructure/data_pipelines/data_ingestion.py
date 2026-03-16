"""
数据摄入：从各种数据源收集数据
负责从文件、API、数据库、消息队列等数据源收集和摄入数据
"""

import asyncio
import json
import csv
import aiohttp
import aiofiles
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import pandas as pd

class DataSource(Enum):
    """数据源类型枚举"""
    FILE_CSV = "file_csv"
    FILE_JSON = "file_json"
    FILE_EXCEL = "file_excel"
    API_REST = "api_rest"
    API_GRAPHQL = "api_graphql"
    DATABASE_SQL = "database_sql"
    DATABASE_NOSQL = "database_nosql"
    MESSAGE_QUEUE = "message_queue"
    STREAMING = "streaming"

@dataclass
class IngestionConfig:
    """数据摄入配置"""
    source_type: DataSource
    source_uri: str
    batch_size: int = 1000
    max_records: int = 10000
    timeout: int = 30
    encoding: str = "utf-8"
    headers: Dict[str, str] = None
    auth: Dict[str, str] = None
    filters: Dict[str, Any] = None

@dataclass
class IngestionResult:
    """数据摄入结果"""
    total_records: int
    successful_records: int
    failed_records: int
    ingestion_time: float
    data_sample: List[Dict[str, Any]]
    errors: List[str]

class DataIngestion:
    """数据摄入器"""
    
    def __init__(self):
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.ingestion_history: List[IngestionResult] = []
        self.initialized = False
        
    async def initialize(self):
        """初始化数据摄入器"""
        if self.initialized:
            return
            
        logging.info("初始化数据摄入器...")
        
        # 创建HTTP会话
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        self.initialized = True
        logging.info("数据摄入器初始化完成")
    
    async def ingest_data(self, config: IngestionConfig) -> IngestionResult:
        """摄入数据"""
        start_time = datetime.now()
        
        try:
            if config.source_type == DataSource.FILE_CSV:
                data = await self._ingest_csv_file(config)
            elif config.source_type == DataSource.FILE_JSON:
                data = await self._ingest_json_file(config)
            elif config.source_type == DataSource.API_REST:
                data = await self._ingest_rest_api(config)
            elif config.source_type == DataSource.DATABASE_SQL:
                data = await self._ingest_sql_database(config)
            else:
                raise ValueError(f"不支持的数据源类型: {config.source_type}")
            
            # 应用过滤器
            if config.filters:
                data = self._apply_filters(data, config.filters)
            
            # 限制记录数量
            if config.max_records and len(data) > config.max_records:
                data = data[:config.max_records]
            
            ingestion_time = (datetime.now() - start_time).total_seconds()
            
            result = IngestionResult(
                total_records=len(data),
                successful_records=len(data),
                failed_records=0,
                ingestion_time=ingestion_time,
                data_sample=data[:min(5, len(data))],
                errors=[]
            )
            
            self.ingestion_history.append(result)
            logging.info(f"数据摄入完成: {len(data)} 条记录")
            
            return result
            
        except Exception as e:
            ingestion_time = (datetime.now() - start_time).total_seconds()
            logging.error(f"数据摄入失败: {e}")
            
            return IngestionResult(
                total_records=0,
                successful_records=0,
                failed_records=0,
                ingestion_time=ingestion_time,
                data_sample=[],
                errors=[str(e)]
            )
    
    async def _ingest_csv_file(self, config: IngestionConfig) -> List[Dict[str, Any]]:
        """摄入CSV文件"""
        try:
            async with aiofiles.open(config.source_uri, 'r', encoding=config.encoding) as f:
                content = await f.read()
            
            # 使用pandas解析CSV
            import io
            df = pd.read_csv(io.StringIO(content))
            return df.to_dict('records')
            
        except Exception as e:
            logging.error(f"CSV文件摄入失败: {e}")
            raise
    
    async def _ingest_json_file(self, config: IngestionConfig) -> List[Dict[str, Any]]:
        """摄入JSON文件"""
        try:
            async with aiofiles.open(config.source_uri, 'r', encoding=config.encoding) as f:
                content = await f.read()
            
            data = json.loads(content)
            
            # 如果数据是字典，转换为列表
            if isinstance(data, dict):
                data = [data]
            
            return data
            
        except Exception as e:
            logging.error(f"JSON文件摄入失败: {e}")
            raise
    
    async def _ingest_rest_api(self, config: IngestionConfig) -> List[Dict[str, Any]]:
        """摄入REST API数据"""
        if not self.http_session:
            raise RuntimeError("HTTP会话未初始化")
        
        try:
            headers = config.headers or {}
            
            async with self.http_session.get(
                config.source_uri,
                headers=headers,
                timeout=config.timeout
            ) as response:
                
                if response.status != 200:
                    raise RuntimeError(f"API请求失败: {response.status}")
                
                content = await response.text()
                data = json.loads(content)
                
                # 处理不同的API响应格式
                if isinstance(data, dict):
                    if 'data' in data:
                        data = data['data']
                    elif 'results' in data:
                        data = data['results']
                    elif 'items' in data:
                        data = data['items']
                
                if isinstance(data, dict):
                    data = [data]
                
                return data
                
        except Exception as e:
            logging.error(f"REST API摄入失败: {e}")
            raise
    
    async def _ingest_sql_database(self, config: IngestionConfig) -> List[Dict[str, Any]]:
        """摄入SQL数据库数据"""
        try:
            # 这里需要根据具体的数据库驱动实现
            # 例如使用asyncpg for PostgreSQL, aiomysql for MySQL等
            # 这里提供模拟实现
            
            logging.info(f"从SQL数据库摄入数据: {config.source_uri}")
            
            # 模拟数据
            mock_data = [
                {"id": 1, "name": "示例数据1", "value": 100},
                {"id": 2, "name": "示例数据2", "value": 200},
                {"id": 3, "name": "示例数据3", "value": 300}
            ]
            
            return mock_data
            
        except Exception as e:
            logging.error(f"SQL数据库摄入失败: {e}")
            raise
    
    def _apply_filters(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用数据过滤器"""
        filtered_data = []
        
        for record in data:
            include_record = True
            
            for field, condition in filters.items():
                if field in record:
                    if isinstance(condition, dict):
                        # 复杂条件处理
                        if 'eq' in condition and record[field] != condition['eq']:
                            include_record = False
                        elif 'gt' in condition and record[field] <= condition['gt']:
                            include_record = False
                        elif 'lt' in condition and record[field] >= condition['lt']:
                            include_record = False
                        elif 'in' in condition and record[field] not in condition['in']:
                            include_record = False
                    else:
                        # 简单相等条件
                        if record[field] != condition:
                            include_record = False
                else:
                    include_record = False
            
            if include_record:
                filtered_data.append(record)
        
        return filtered_data
    
    async def stream_ingest(self, config: IngestionConfig) -> AsyncGenerator[Dict[str, Any], None]:
        """流式数据摄入"""
        if config.source_type == DataSource.FILE_CSV:
            async for record in self._stream_csv_file(config):
                yield record
        elif config.source_type == DataSource.API_REST:
            async for record in self._stream_rest_api(config):
                yield record
        else:
            raise ValueError(f"不支持流式摄入的数据源类型: {config.source_type}")
    
    async def _stream_csv_file(self, config: IngestionConfig) -> AsyncGenerator[Dict[str, Any], None]:
        """流式摄入CSV文件"""
        try:
            async with aiofiles.open(config.source_uri, 'r', encoding=config.encoding) as f:
                # 读取标题行
                header_line = await f.readline()
                headers = header_line.strip().split(',')
                
                # 读取数据行
                batch = []
                async for line in f:
                    values = line.strip().split(',')
                    record = dict(zip(headers, values))
                    batch.append(record)
                    
                    if len(batch) >= config.batch_size:
                        for item in batch:
                            yield item
                        batch = []
                
                # 处理剩余数据
                for item in batch:
                    yield item
                    
        except Exception as e:
            logging.error(f"CSV文件流式摄入失败: {e}")
            raise
    
    async def _stream_rest_api(self, config: IngestionConfig) -> AsyncGenerator[Dict[str, Any], None]:
        """流式摄入REST API数据"""
        if not self.http_session:
            raise RuntimeError("HTTP会话未初始化")
        
        try:
            # 这里假设API支持分页
            page = 1
            has_more = True
            
            while has_more:
                url = f"{config.source_uri}?page={page}&limit={config.batch_size}"
                
                async with self.http_session.get(url, headers=config.headers) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    
                    if not data:
                        has_more = False
                    else:
                        for record in data:
                            yield record
                        
                        page += 1
                        
        except Exception as e:
            logging.error(f"REST API流式摄入失败: {e}")
            raise
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """获取摄入统计"""
        if not self.ingestion_history:
            return {}
        
        total_records = sum(result.total_records for result in self.ingestion_history)
        successful_records = sum(result.successful_records for result in self.ingestion_history)
        total_time = sum(result.ingestion_time for result in self.ingestion_history)
        
        return {
            "total_ingestions": len(self.ingestion_history),
            "total_records": total_records,
            "successful_records": successful_records,
            "average_ingestion_time": total_time / len(self.ingestion_history),
            "success_rate": (successful_records / total_records * 100) if total_records > 0 else 0
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()

# 全局数据摄入器实例
data_ingestion = DataIngestion()