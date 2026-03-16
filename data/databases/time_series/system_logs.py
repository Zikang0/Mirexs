"""
系统日志模块 - 管理系统运行日志的存储和查询
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from .influxdb_integration import InfluxDBIntegration

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SystemLogs:
    """系统日志管理类"""
    
    def __init__(self, influx_client: InfluxDBIntegration, config: Dict[str, Any]):
        """
        初始化系统日志管理器
        
        Args:
            influx_client: InfluxDB客户端
            config: 配置字典
        """
        self.influx_client = influx_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 日志配置
        self.log_bucket = config.get('log_bucket', 'mirexs_logs')
        self.retention_days = config.get('retention_days', 90)
        self.batch_size = config.get('batch_size', 100)
        
        self._pending_logs = []
        
    def log_system_event(self,
                        level: LogLevel,
                        component: str,
                        message: str,
                        details: Optional[Dict[str, Any]] = None,
                        user_id: Optional[str] = None,
                        session_id: Optional[str] = None) -> bool:
        """
        记录系统事件日志
        
        Args:
            level: 日志级别
            component: 组件名称
            message: 日志消息
            details: 详细数据
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            bool: 记录是否成功
        """
        try:
            fields = {
                "level": level.value,
                "message": message,
                "component": component
            }
            
            tags = {
                "log_type": "system_event",
                "component": component,
                "level": level.value
            }
            
            if user_id:
                tags["user_id"] = user_id
            if session_id:
                tags["session_id"] = session_id
            if details:
                fields["details"] = json.dumps(details, ensure_ascii=False)
            
            # 添加堆栈信息用于错误级别
            if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                import traceback
                stack_trace = traceback.format_stack()
                fields["stack_trace"] = json.dumps(stack_trace, ensure_ascii=False)
            
            success = self.influx_client.write_metric(
                measurement="system_logs",
                fields=fields,
                tags=tags,
                bucket=self.log_bucket
            )
            
            if success:
                self.logger.debug(f"Logged system event: {component} - {message}")
            else:
                self.logger.error(f"Failed to log system event: {component} - {message}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error logging system event: {str(e)}")
            return False
    
    def log_performance_metric(self,
                             metric_name: str,
                             value: float,
                             component: str,
                             tags: Optional[Dict[str, str]] = None) -> bool:
        """
        记录性能指标
        
        Args:
            metric_name: 指标名称
            value: 指标值
            component: 组件名称
            tags: 额外标签
            
        Returns:
            bool: 记录是否成功
        """
        try:
            fields = {
                metric_name: value,
                "component": component
            }
            
            base_tags = {
                "log_type": "performance_metric",
                "component": component,
                "metric_name": metric_name
            }
            
            if tags:
                base_tags.update(tags)
            
            success = self.influx_client.write_metric(
                measurement="system_logs",
                fields=fields,
                tags=base_tags,
                bucket=self.log_bucket
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error logging performance metric: {str(e)}")
            return False
    
    def log_security_event(self,
                          event_type: str,
                          severity: str,
                          message: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None) -> bool:
        """
        记录安全事件
        
        Args:
            event_type: 事件类型
            severity: 严重程度
            message: 事件消息
            user_id: 用户ID
            ip_address: IP地址
            details: 详细数据
            
        Returns:
            bool: 记录是否成功
        """
        try:
            fields = {
                "event_type": event_type,
                "severity": severity,
                "message": message
            }
            
            tags = {
                "log_type": "security_event",
                "event_type": event_type,
                "severity": severity
            }
            
            if user_id:
                tags["user_id"] = user_id
            if ip_address:
                tags["ip_address"] = ip_address
            if details:
                fields["details"] = json.dumps(details, ensure_ascii=False)
            
            success = self.influx_client.write_metric(
                measurement="system_logs",
                fields=fields,
                tags=tags,
                bucket=self.log_bucket
            )
            
            if success:
                self.logger.info(f"Logged security event: {event_type} - {message}")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {str(e)}")
            return False
    
    def query_logs(self,
                  start_time: str = "-1h",
                  end_time: str = "now()",
                  level: Optional[str] = None,
                  component: Optional[str] = None,
                  log_type: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        查询系统日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            level: 日志级别过滤
            component: 组件名称过滤
            log_type: 日志类型过滤
            
        Returns:
            List: 日志记录列表
        """
        try:
            query_parts = [
                f'from(bucket: "{self.log_bucket}")',
                f'|> range(start: {start_time}, stop: {end_time})',
                '|> filter(fn: (r) => r._measurement == "system_logs")'
            ]
            
            if level:
                query_parts.append(f'|> filter(fn: (r) => r.level == "{level}")')
            if component:
                query_parts.append(f'|> filter(fn: (r) => r.component == "{component}")')
            if log_type:
                query_parts.append(f'|> filter(fn: (r) => r.log_type == "{log_type}")')
            
            query = '\n  '.join(query_parts)
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                logs = []
                for _, row in df.iterrows():
                    log_entry = {
                        "timestamp": row.get('_time', ''),
                        "level": row.get('level', ''),
                        "component": row.get('component', ''),
                        "message": row.get('message', ''),
                        "log_type": row.get('log_type', '')
                    }
                    
                    # 解析详细信息
                    if 'details' in row and row['details']:
                        try:
                            log_entry["details"] = json.loads(row['details'])
                        except:
                            log_entry["details"] = row['details']
                    
                    logs.append(log_entry)
                
                return logs
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error querying logs: {str(e)}")
            return None
    
    def get_error_stats(self, 
                       start_time: str = "-24h",
                       end_time: str = "now()") -> Optional[Dict[str, Any]]:
        """
        获取错误统计信息
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 错误统计信息
        """
        try:
            query = f'''
            from(bucket: "{self.log_bucket}")
              |> range(start: {start_time}, stop: {end_time})
              |> filter(fn: (r) => r._measurement == "system_logs")
              |> filter(fn: (r) => r.level == "ERROR" or r.level == "CRITICAL")
              |> group(columns: ["component"])
              |> count()
            '''
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                stats = {}
                for _, row in df.iterrows():
                    component = row.get('component', 'unknown')
                    count = row.get('_value', 0)
                    stats[component] = count
                
                return stats
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting error stats: {str(e)}")
            return None
    
    def cleanup_old_logs(self, older_than_days: Optional[int] = None) -> bool:
        """
        清理旧日志
        
        Args:
            older_than_days: 清理多少天前的日志
            
        Returns:
            bool: 清理是否成功
        """
        try:
            days = older_than_days or self.retention_days
            return self.influx_client.delete_old_data("system_logs", days)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {str(e)}")
            return False
    
    def batch_log(self,
                 level: LogLevel,
                 component: str,
                 message: str,
                 details: Optional[Dict[str, Any]] = None) -> None:
        """
        批量记录日志（延迟写入）
        
        Args:
            level: 日志级别
            component: 组件名称
            message: 日志消息
            details: 详细数据
        """
        log_entry = {
            "timestamp": datetime.utcnow(),
            "level": level,
            "component": component,
            "message": message,
            "details": details or {}
        }
        
        self._pending_logs.append(log_entry)
        
        # 如果达到批量大小，立即写入
        if len(self._pending_logs) >= self.batch_size:
            self.flush_batch()
    
    def flush_batch(self) -> bool:
        """
        刷新批量日志到数据库
        
        Returns:
            bool: 写入是否成功
        """
        if not self._pending_logs:
            return True
        
        try:
            from influxdb_client import Point
            
            points = []
            for log_entry in self._pending_logs:
                point = Point("system_logs")
                
                point = point.tag("log_type", "system_event")
                point = point.tag("component", log_entry["component"])
                point = point.tag("level", log_entry["level"].value)
                
                point = point.field("message", log_entry["message"])
                point = point.field("component", log_entry["component"])
                point = point.field("level", log_entry["level"].value)
                
                if log_entry["details"]:
                    point = point.field("details", json.dumps(log_entry["details"], ensure_ascii=False))
                
                point = point.time(log_entry["timestamp"])
                points.append(point)
            
            success = self.influx_client.batch_write_metrics(points, self.log_bucket)
            
            if success:
                self.logger.debug(f"Flushed {len(points)} log entries to database")
                self._pending_logs.clear()
            else:
                self.logger.error("Failed to flush batch logs")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error flushing batch logs: {str(e)}")
            return False

