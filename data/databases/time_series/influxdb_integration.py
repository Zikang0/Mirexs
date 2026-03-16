"""
InfluxDB集成模块 - 提供时序数据库的核心集成功能
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
    from influxdb_client.client.exceptions import InfluxDBError
    HAS_INFLUXDB = True
except ImportError:
    HAS_INFLUXDB = False
    logging.warning("InfluxDB client not installed. Please install with: pip install influxdb-client")

class InfluxDBIntegration:
    """InfluxDB集成类 - 提供完整的时序数据库操作功能"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化InfluxDB集成
        
        Args:
            config: 配置字典，包含url, token, org, bucket等参数
        """
        self.config = config
        self.client = None
        self.write_api = None
        self.query_api = None
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
        # 默认配置
        self.default_bucket = config.get('bucket', 'mirexs_metrics')
        self.default_org = config.get('org', 'mirexs_org')
        self.timeout = config.get('timeout', 10000)
        
        self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """初始化InfluxDB客户端"""
        try:
            if not HAS_INFLUXDB:
                self.logger.error("InfluxDB client not available")
                return False
            
            url = self.config.get('url', 'http://localhost:8086')
            token = self.config.get('token', '')
            
            self.client = InfluxDBClient(
                url=url,
                token=token,
                org=self.default_org,
                timeout=self.timeout
            )
            
            # 测试连接
            health = self.client.health()
            if health.status == "pass":
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                self.query_api = self.client.query_api()
                self.connected = True
                self.logger.info(f"Successfully connected to InfluxDB at {url}")
                return True
            else:
                self.logger.error(f"InfluxDB health check failed: {health.message}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize InfluxDB client: {str(e)}")
            return False
    
    def write_metric(self, 
                    measurement: str, 
                    fields: Dict[str, Any], 
                    tags: Optional[Dict[str, str]] = None,
                    timestamp: Optional[datetime] = None,
                    bucket: Optional[str] = None) -> bool:
        """
        写入指标数据
        
        Args:
            measurement: 测量名称
            fields: 字段数据字典
            tags: 标签字典
            timestamp: 时间戳
            bucket: 存储桶名称
            
        Returns:
            bool: 写入是否成功
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return False
        
        try:
            point = Point(measurement)
            
            # 添加标签
            if tags:
                for tag_key, tag_value in tags.items():
                    point = point.tag(tag_key, str(tag_value))
            
            # 添加字段
            for field_key, field_value in fields.items():
                if isinstance(field_value, (int, float)):
                    point = point.field(field_key, field_value)
                elif isinstance(field_value, bool):
                    point = point.field(field_key, field_value)
                else:
                    point = point.field(field_key, str(field_value))
            
            # 设置时间戳
            if timestamp:
                point = point.time(timestamp, WritePrecision.NS)
            else:
                point = point.time(datetime.utcnow(), WritePrecision.NS)
            
            # 写入数据
            target_bucket = bucket or self.default_bucket
            self.write_api.write(bucket=target_bucket, record=point)
            
            self.logger.debug(f"Successfully wrote metric: {measurement}")
            return True
            
        except InfluxDBError as e:
            self.logger.error(f"InfluxDB write error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during write: {str(e)}")
            return False
    
    def batch_write_metrics(self, points: List[Point], bucket: Optional[str] = None) -> bool:
        """
        批量写入指标数据
        
        Args:
            points: Point对象列表
            bucket: 存储桶名称
            
        Returns:
            bool: 写入是否成功
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return False
        
        try:
            target_bucket = bucket or self.default_bucket
            self.write_api.write(bucket=target_bucket, record=points)
            
            self.logger.debug(f"Successfully wrote {len(points)} metrics in batch")
            return True
            
        except InfluxDBError as e:
            self.logger.error(f"InfluxDB batch write error: {str(e)}")
            return False
    
    def query_metrics(self, 
                     query: str,
                     params: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
        """
        查询指标数据
        
        Args:
            query: Flux查询语句
            params: 查询参数
            
        Returns:
            DataFrame: 查询结果，失败返回None
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return None
        
        try:
            if params:
                tables = self.query_api.query(query, params=params)
            else:
                tables = self.query_api.query(query)
            
            # 转换为DataFrame
            if tables:
                records = []
                for table in tables:
                    for record in table.records:
                        records.append(record.values)
                
                if records:
                    df = pd.DataFrame(records)
                    self.logger.debug(f"Query returned {len(df)} records")
                    return df
            
            self.logger.debug("Query returned no results")
            return pd.DataFrame()
            
        except InfluxDBError as e:
            self.logger.error(f"InfluxDB query error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during query: {str(e)}")
            return None
    
    def query_system_metrics(self, 
                           start_time: str = "-1h",
                           end_time: str = "now()",
                           measurement: str = "system_metrics") -> Optional[pd.DataFrame]:
        """
        查询系统指标数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            measurement: 测量名称
            
        Returns:
            DataFrame: 系统指标数据
        """
        query = f'''
        from(bucket: "{self.default_bucket}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r._measurement == "{measurement}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        return self.query_metrics(query)
    
    def query_performance_metrics(self,
                                metric_type: str,
                                start_time: str = "-1h",
                                end_time: str = "now()") -> Optional[pd.DataFrame]:
        """
        查询性能指标数据
        
        Args:
            metric_type: 指标类型 (cpu, memory, disk, network等)
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            DataFrame: 性能指标数据
        """
        query = f'''
        from(bucket: "{self.default_bucket}")
          |> range(start: {start_time}, stop: {end_time})
          |> filter(fn: (r) => r._measurement == "performance_metrics")
          |> filter(fn: (r) => r.metric_type == "{metric_type}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        return self.query_metrics(query)
    
    def create_bucket(self, bucket_name: str, description: str = "") -> bool:
        """
        创建存储桶
        
        Args:
            bucket_name: 存储桶名称
            description: 描述信息
            
        Returns:
            bool: 创建是否成功
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return False
        
        try:
            buckets_api = self.client.buckets_api()
            
            # 检查存储桶是否已存在
            existing_buckets = buckets_api.find_buckets().buckets
            for bucket in existing_buckets:
                if bucket.name == bucket_name:
                    self.logger.info(f"Bucket {bucket_name} already exists")
                    return True
            
            # 创建存储桶
            buckets_api.create_bucket(
                bucket_name=bucket_name,
                description=description,
                org_id=self.client.org
            )
            
            self.logger.info(f"Successfully created bucket: {bucket_name}")
            return True
            
        except InfluxDBError as e:
            self.logger.error(f"Failed to create bucket: {str(e)}")
            return False
    
    def delete_old_data(self, 
                       measurement: str,
                       older_than_days: int = 30) -> bool:
        """
        删除旧数据
        
        Args:
            measurement: 测量名称
            older_than_days: 删除多少天前的数据
            
        Returns:
            bool: 删除是否成功
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return False
        
        try:
            delete_api = self.client.delete_api()
            
            start = "1970-01-01T00:00:00Z"
            stop = f"now() - {older_than_days}d"
            
            delete_api.delete(
                start=start,
                stop=stop,
                predicate=f'_measurement="{measurement}"',
                bucket=self.default_bucket,
                org=self.default_org
            )
            
            self.logger.info(f"Successfully deleted {measurement} data older than {older_than_days} days")
            return True
            
        except InfluxDBError as e:
            self.logger.error(f"Failed to delete old data: {str(e)}")
            return False
    
    def get_database_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 数据库统计信息
        """
        if not self.connected:
            self.logger.error("InfluxDB client not connected")
            return None
        
        try:
            # 这里可以添加更详细的统计信息查询
            stats = {
                "connected": True,
                "url": self.config.get('url', ''),
                "org": self.default_org,
                "default_bucket": self.default_bucket,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return None
    
    def close(self):
        """关闭连接"""
        if self.client:
            self.client.close()
            self.connected = False
            self.logger.info("InfluxDB connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

        