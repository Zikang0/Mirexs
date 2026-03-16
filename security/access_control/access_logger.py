"""
访问日志模块 - 记录访问日志
记录所有访问尝试、成功和失败的操作，用于审计和安全分析
"""

import logging
import secrets
import time
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import threading
from queue import Queue, Empty
import atexit

logger = logging.getLogger(__name__)


class AccessType(Enum):
    """访问类型枚举"""
    LOGIN = "login"  # 登录
    LOGOUT = "logout"  # 登出
    API_CALL = "api_call"  # API调用
    DATA_ACCESS = "data_access"  # 数据访问
    DATA_MODIFY = "data_modify"  # 数据修改
    DATA_DELETE = "data_delete"  # 数据删除
    CONFIG_CHANGE = "config_change"  # 配置变更
    PERMISSION_CHANGE = "permission_change"  # 权限变更
    USER_MANAGEMENT = "user_management"  # 用户管理
    SYSTEM_OPERATION = "system_operation"  # 系统操作
    SECURITY_EVENT = "security_event"  # 安全事件


class AccessResult(Enum):
    """访问结果枚举"""
    SUCCESS = "success"  # 成功
    FAILURE = "failure"  # 失败
    DENIED = "denied"  # 拒绝
    ERROR = "error"  # 错误
    TIMEOUT = "timeout"  # 超时
    SUSPICIOUS = "suspicious"  # 可疑


@dataclass
class AccessLogEntry:
    """访问日志条目"""
    log_id: str
    timestamp: float
    user_id: Optional[str]
    access_type: AccessType
    result: AccessResult
    resource: Optional[str] = None
    action: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class AccessLogger:
    """
    访问日志记录器
    异步记录所有访问事件，支持多种输出目标
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化访问日志记录器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 日志队列（用于异步写入）
        self.log_queue: Queue = Queue()
        
        # 日志文件路径
        self.log_file = Path(self.config.get("log_file", "logs/access.log"))
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 错误日志文件
        self.error_log_file = Path(self.config.get("error_log_file", "logs/access_error.log"))
        self.error_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 索引文件（用于快速检索）
        self.index_file = Path(self.config.get("index_file", "logs/access_index.json"))
        
        # 内存中的最近日志（用于快速查询）
        self.recent_logs: List[AccessLogEntry] = []
        self.max_recent_logs = self.config.get("max_recent_logs", 1000)
        
        # 日志计数器
        self.log_counter = 0
        self.error_counter = 0
        
        # 写入线程
        self.writer_thread = None
        self.running = False
        
        # 启动写入线程
        self._start_writer()
        
        # 注册退出处理
        atexit.register(self._shutdown)
        
        # 加载索引
        self._load_index()
        
        logger.info(f"访问日志记录器初始化完成，日志文件: {self.log_file}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "log_file": "logs/access.log",
            "error_log_file": "logs/access_error.log",
            "index_file": "logs/access_index.json",
            "max_recent_logs": 1000,
            "batch_size": 100,  # 批量写入大小
            "flush_interval_seconds": 5,  # 刷新间隔
            "enable_index": True,
            "index_retention_days": 30,
            "log_format": "json",  # json 或 text
            "log_level": "info"  # debug, info, error
        }
    
    def _start_writer(self):
        """启动日志写入线程"""
        self.running = True
        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()
        logger.debug("日志写入线程已启动")
    
    def _writer_loop(self):
        """日志写入循环"""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # 从队列获取日志
                try:
                    entry = self.log_queue.get(timeout=1)
                    batch.append(entry)
                except Empty:
                    pass
                
                # 检查是否需要刷新
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.config["batch_size"] or
                    (batch and current_time - last_flush >= self.config["flush_interval_seconds"])
                )
                
                if should_flush and batch:
                    self._write_batch(batch)
                    last_flush = current_time
                    batch = []
                    
            except Exception as e:
                logger.error(f"日志写入循环异常: {str(e)}")
                # 将失败的日志写入错误日志
                self._write_error_log(batch)
                batch = []
                time.sleep(1)
    
    def _write_batch(self, batch: List[AccessLogEntry]):
        """批量写入日志"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                for entry in batch:
                    if self.config["log_format"] == "json":
                        log_data = self._entry_to_dict(entry)
                        f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
                    else:
                        log_data = self._format_text_log(entry)
                        f.write(log_data + '\n')
            
            # 更新计数器
            self.log_counter += len(batch)
            
            # 更新最近日志
            self.recent_logs.extend(batch)
            if len(self.recent_logs) > self.max_recent_logs:
                self.recent_logs = self.recent_logs[-self.max_recent_logs:]
            
            # 更新索引
            if self.config["enable_index"]:
                self._update_index(batch)
                
        except Exception as e:
            logger.error(f"批量写入日志失败: {str(e)}")
            self._write_error_log(batch)
    
    def _write_error_log(self, entries: List[AccessLogEntry]):
        """写入错误日志"""
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                for entry in entries:
                    f.write(f"[ERROR] Failed to write log: {self._entry_to_dict(entry)}\n")
            self.error_counter += len(entries)
        except Exception as e:
            logger.error(f"写入错误日志失败: {str(e)}")
    
    def _entry_to_dict(self, entry: AccessLogEntry) -> Dict[str, Any]:
        """将日志条目转换为字典"""
        result = asdict(entry)
        result["access_type"] = entry.access_type.value
        result["result"] = entry.result.value
        result["timestamp_iso"] = datetime.fromtimestamp(entry.timestamp).isoformat()
        return result
    
    def _format_text_log(self, entry: AccessLogEntry) -> str:
        """格式化文本日志"""
        timestamp = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        user = entry.user_id or "anonymous"
        return (f"[{timestamp}] {user} | {entry.access_type.value} | {entry.result.value} | "
                f"{entry.resource or '-'} | {entry.ip_address or '-'} | {entry.duration_ms or '-'}ms")
    
    def _update_index(self, batch: List[AccessLogEntry]):
        """更新日志索引"""
        try:
            # 加载现有索引
            index = {}
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            
            # 更新索引
            for entry in batch:
                date_key = datetime.fromtimestamp(entry.timestamp).strftime("%Y%m%d")
                if date_key not in index:
                    index[date_key] = {
                        "count": 0,
                        "users": set(),
                        "types": set()
                    }
                
                index[date_key]["count"] += 1
                if entry.user_id:
                    index[date_key]["users"].add(entry.user_id)
                index[date_key]["types"].add(entry.access_type.value)
            
            # 转换set为list以便JSON序列化
            for date_key in index:
                index[date_key]["users"] = list(index[date_key]["users"])
                index[date_key]["types"] = list(index[date_key]["types"])
            
            # 保存索引
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"更新日志索引失败: {str(e)}")
    
    def _load_index(self):
        """加载日志索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                logger.info(f"加载日志索引，包含 {len(index)} 天的记录")
        except Exception as e:
            logger.error(f"加载日志索引失败: {str(e)}")
    
    def _shutdown(self):
        """关闭日志记录器"""
        self.running = False
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5)
        
        # 写入剩余的日志
        remaining_logs = []
        while not self.log_queue.empty():
            try:
                remaining_logs.append(self.log_queue.get_nowait())
            except Empty:
                break
        
        if remaining_logs:
            self._write_batch(remaining_logs)
        
        logger.info(f"访问日志记录器已关闭，共记录 {self.log_counter} 条日志，{self.error_counter} 条错误")
    
    def log(
        self,
        user_id: Optional[str],
        access_type: AccessType,
        result: AccessResult,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        记录访问日志
        
        Args:
            user_id: 用户ID
            access_type: 访问类型
            result: 访问结果
            resource: 访问的资源
            action: 执行的操作
            ip_address: IP地址
            user_agent: 用户代理
            session_id: 会话ID
            request_id: 请求ID
            duration_ms: 持续时间（毫秒）
            details: 详细信息
            error_message: 错误信息
            tags: 标签
        
        Returns:
            日志ID
        """
        log_id = f"log_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        
        entry = AccessLogEntry(
            log_id=log_id,
            timestamp=time.time(),
            user_id=user_id,
            access_type=access_type,
            result=result,
            resource=resource,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            request_id=request_id,
            duration_ms=duration_ms,
            details=details or {},
            error_message=error_message,
            tags=tags or []
        )
        
        # 放入队列
        self.log_queue.put(entry)
        
        # 如果日志级别是debug，立即记录
        if self.config["log_level"] == "debug":
            logger.debug(f"访问日志: {self._format_text_log(entry)}")
        
        return log_id
    
    def log_login(
        self,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录登录事件"""
        return self.log(
            user_id=user_id,
            access_type=AccessType.LOGIN,
            result=AccessResult.SUCCESS if success else AccessResult.FAILURE,
            resource="login",
            action="login",
            ip_address=ip_address,
            user_agent=user_agent,
            error_message=error_message,
            details=details,
            tags=["authentication"]
        )
    def log_logout(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录登出事件"""
        return self.log(
            user_id=user_id,
            access_type=AccessType.LOGOUT,
            result=AccessResult.SUCCESS,
            resource="logout",
            action="logout",
            session_id=session_id,
            details=details,
            tags=["authentication"]
        )
    
    def log_api_call(
        self,
        user_id: Optional[str],
        api_name: str,
        success: bool,
        duration_ms: float,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录API调用"""
        return self.log(
            user_id=user_id,
            access_type=AccessType.API_CALL,
            result=AccessResult.SUCCESS if success else AccessResult.ERROR,
            resource=f"api:{api_name}",
            action="call",
            ip_address=ip_address,
            request_id=request_id,
            duration_ms=duration_ms,
            error_message=error_message,
            details=details,
            tags=["api"]
        )
    
    def log_data_access(
        self,
        user_id: str,
        data_type: str,
        data_id: str,
        success: bool,
        access_type: str = "read",  # read, write, delete
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """记录数据访问"""
        access_type_map = {
            "read": AccessType.DATA_ACCESS,
            "write": AccessType.DATA_MODIFY,
            "delete": AccessType.DATA_DELETE
        }
        
        return self.log(
            user_id=user_id,
            access_type=access_type_map.get(access_type, AccessType.DATA_ACCESS),
            result=AccessResult.SUCCESS if success else AccessResult.FAILURE,
            resource=f"data:{data_type}:{data_id}",
            action=access_type,
            ip_address=ip_address,
            session_id=session_id,
            details=details,
            tags=["data"]
        )
    
    def log_security_event(
        self,
        user_id: Optional[str],
        event_type: str,
        severity: str,  # low, medium, high, critical
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> str:
        """记录安全事件"""
        result_map = {
            "low": AccessResult.SUSPICIOUS,
            "medium": AccessResult.SUSPICIOUS,
            "high": AccessResult.DENIED,
            "critical": AccessResult.ERROR
        }
        
        return self.log(
            user_id=user_id,
            access_type=AccessType.SECURITY_EVENT,
            result=result_map.get(severity, AccessResult.SUSPICIOUS),
            resource=f"security:{event_type}",
            action=event_type,
            ip_address=ip_address,
            details=details,
            tags=["security", severity]
        )
    
    def query_logs(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        user_id: Optional[str] = None,
        access_type: Optional[AccessType] = None,
        result: Optional[AccessResult] = None,
        resource_pattern: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询日志
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            user_id: 用户ID
            access_type: 访问类型
            result: 访问结果
            resource_pattern: 资源模式
            tags: 标签
            limit: 返回条数限制
            offset: 偏移量
        
        Returns:
            日志条目列表
        """
        try:
            results = []
            
            # 从最近日志中查询
            for entry in reversed(self.recent_logs):
                # 应用过滤条件
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                if user_id and entry.user_id != user_id:
                    continue
                if access_type and entry.access_type != access_type:
                    continue
                if result and entry.result != result:
                    continue
                if resource_pattern and entry.resource:
                    if resource_pattern not in entry.resource:
                        continue
                if tags and not all(tag in entry.tags for tag in tags):
                    continue
                
                results.append(self._entry_to_dict(entry))
                
                if len(results) >= limit + offset:
                    break
            
            # 如果最近日志不够，从文件查询
            if len(results) < limit + offset and self.log_file.exists():
                file_results = self._query_from_file(
                    start_time, end_time, user_id, access_type, result,
                    resource_pattern, tags, limit + offset - len(results)
                )
                results.extend(file_results)
            
            # 应用分页
            return results[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"查询日志失败: {str(e)}")
            return []
    
    def _query_from_file(
        self,
        start_time: Optional[float],
        end_time: Optional[float],
        user_id: Optional[str],
        access_type: Optional[AccessType],
        result: Optional[AccessResult],
        resource_pattern: Optional[str],
        tags: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """从文件查询日志"""
        results = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # 读取文件末尾（最近的日志）
                lines = f.readlines()
                for line in reversed(lines[-10000:]):  # 最多读取最近10000条
                    try:
                        data = json.loads(line.strip())
                        
                        # 应用过滤条件
                        if start_time and data["timestamp"] < start_time:
                            continue
                        if end_time and data["timestamp"] > end_time:
                            continue
                        if user_id and data.get("user_id") != user_id:
                            continue
                        if access_type and data.get("access_type") != access_type.value:
                            continue
                        if result and data.get("result") != result.value:
                            continue
                        if resource_pattern and data.get("resource"):
                            if resource_pattern not in data["resource"]:
                                continue
                        
                        results.append(data)
                        
                        if len(results) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"从文件查询日志失败: {str(e)}")
        
        return results
    
    def get_statistics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Args:
            days: 统计天数
        
        Returns:
            统计信息
        """
        try:
            stats = {
                "total_logs": self.log_counter,
                "total_errors": self.error_counter,
                "daily_stats": {},
                "type_stats": {},
                "result_stats": {},
                "user_stats": {}
            }
            
            start_time = time.time() - (days * 24 * 3600)
            
            for entry in self.recent_logs:
                if entry.timestamp < start_time:
                    continue
                
                # 按天统计
                date = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d")
                if date not in stats["daily_stats"]:
                    stats["daily_stats"][date] = 0
                stats["daily_stats"][date] += 1
                
                # 按类型统计
                type_key = entry.access_type.value
                if type_key not in stats["type_stats"]:
                    stats["type_stats"][type_key] = 0
                stats["type_stats"][type_key] += 1
                
                # 按结果统计
                result_key = entry.result.value
                if result_key not in stats["result_stats"]:
                    stats["result_stats"][result_key] = 0
                stats["result_stats"][result_key] += 1
                
                # 按用户统计
                if entry.user_id:
                    if entry.user_id not in stats["user_stats"]:
                        stats["user_stats"][entry.user_id] = 0
                    stats["user_stats"][entry.user_id] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取日志统计失败: {str(e)}")
            return {}
    
    def export_logs(
        self,
        output_file: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        format: str = "json"  # json 或 csv
    ) -> Tuple[bool, str]:
        """
        导出日志
        
        Args:
            output_file: 输出文件路径
            start_time: 开始时间
            end_time: 结束时间
            format: 导出格式
        
        Returns:
            (成功标志, 消息)
        """
        try:
            logs = self.query_logs(
                start_time=start_time,
                end_time=end_time,
                limit=100000  # 最大导出10万条
            )
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                if logs:
                    with open(output_path, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                        writer.writeheader()
                        writer.writerows(logs)
            else:
                return False, f"不支持的导出格式: {format}"
            
            logger.info(f"导出 {len(logs)} 条日志到 {output_file}")
            return True, f"成功导出 {len(logs)} 条日志"
            
        except Exception as e:
            logger.error(f"导出日志失败: {str(e)}")
            return False, f"导出失败: {str(e)}"
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        清理旧日志
        
        Args:
            days: 保留天数
        
        Returns:
            清理的文件数
        """
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            cutoff_date = datetime.fromtimestamp(cutoff_time).strftime("%Y%m%d")
            
            cleaned = 0
            
            # 清理日志文件（实际应用中可能需要日志轮转）
            if self.log_file.exists():
                # 这里只是重命名，实际应根据需求实现
                archive_name = self.log_file.with_suffix(f".{cutoff_date}.log")
                self.log_file.rename(archive_name)
                cleaned += 1
            
            # 清理索引中的旧记录
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                
                # 删除旧日期的索引
                for date_key in list(index.keys()):
                    if date_key < cutoff_date:
                        del index[date_key]
                        cleaned += 1
                
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index, f, ensure_ascii=False, indent=2)
            
            logger.info(f"清理了 {cleaned} 个旧日志文件")
            return cleaned
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {str(e)}")
            return 0


# 单例实例
_access_logger_instance = None


def get_access_logger() -> AccessLogger:
    """获取访问日志记录器单例实例"""
    global _access_logger_instance
    if _access_logger_instance is None:
        _access_logger_instance = AccessLogger()
    return _access_logger_instance

