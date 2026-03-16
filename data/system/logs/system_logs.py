"""
系统日志模块 - 记录系统运行日志
负责记录系统启动、关闭、运行状态等关键事件
"""

import logging
import logging.handlers
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class SystemLogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SystemLogger:
    """系统日志记录器"""
    
    def __init__(self, log_dir: str = "logs/system", max_bytes: int = 100*1024*1024, backup_count: int = 10):
        self.log_dir = log_dir
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """配置日志系统"""
        # 创建日志目录
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 系统主日志记录器
        system_logger = logging.getLogger("system")
        system_logger.setLevel(logging.INFO)
        
        # 文件处理器 - 按文件大小轮转
        log_file = f"{self.log_dir}/system.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=self.max_bytes, 
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        system_logger.addHandler(file_handler)
        system_logger.addHandler(console_handler)
        
        self.loggers["system"] = system_logger
    
    def log_system_startup(self, version: str, components: Dict[str, Any]):
        """记录系统启动事件"""
        logger = self.loggers["system"]
        logger.info(f"系统启动 - 版本: {version}")
        logger.info(f"启动组件: {json.dumps(components, ensure_ascii=False)}")
        
        # 记录到启动专用日志
        startup_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "system_startup",
            "version": version,
            "components": components,
            "status": "success"
        }
        self._write_structured_log("startup", startup_log)
    
    def log_system_shutdown(self, reason: str = "normal"):
        """记录系统关闭事件"""
        logger = self.loggers["system"]
        logger.info(f"系统关闭 - 原因: {reason}")
        
        shutdown_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "system_shutdown",
            "reason": reason,
            "status": "success"
        }
        self._write_structured_log("shutdown", shutdown_log)
    
    def log_component_status(self, component: str, status: str, details: Dict[str, Any]):
        """记录组件状态"""
        logger = self.loggers["system"]
        logger.info(f"组件状态 - {component}: {status}")
        
        status_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "component_status",
            "component": component,
            "status": status,
            "details": details
        }
        self._write_structured_log("component_status", status_log)
    
    def log_resource_usage(self, cpu_percent: float, memory_mb: float, disk_usage: Dict[str, float]):
        """记录资源使用情况"""
        resource_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "resource_usage",
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "disk_usage": disk_usage
        }
        self._write_structured_log("resource_usage", resource_log)
    
    def log_service_event(self, service: str, event: str, details: Dict[str, Any]):
        """记录服务事件"""
        logger = self.loggers["system"]
        logger.info(f"服务事件 - {service}: {event}")
        
        service_log = {
            "timestamp": datetime.now().isoformat(),
            "event": "service_event",
            "service": service,
            "event_type": event,
            "details": details
        }
        self._write_structured_log("service_events", service_log)
    
    def _write_structured_log(self, log_type: str, log_data: Dict[str, Any]):
        """写入结构化日志"""
        import os
        log_file = f"{self.log_dir}/{log_type}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    
    def get_recent_logs(self, lines: int = 100) -> list:
        """获取最近的系统日志"""
        log_file = f"{self.log_dir}/system.log"
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines_list = f.readlines()
                return lines_list[-lines:]
        except FileNotFoundError:
            return ["No system logs found"]
    
    def cleanup_old_logs(self, days: int = 30):
        """清理旧的日志文件"""
        import os
        import glob
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 清理 .log 文件
        log_files = glob.glob(f"{self.log_dir}/*.log.*")  # 轮转文件
        for log_file in log_files:
            file_time = datetime.fromtimestamp(os.path.getctime(log_file))
            if file_time < cutoff_time:
                os.remove(log_file)
        
        # 清理旧的 JSONL 文件
        jsonl_files = glob.glob(f"{self.log_dir}/*.jsonl")
        for jsonl_file in jsonl_files:
            file_time = datetime.fromtimestamp(os.path.getctime(jsonl_file))
            if file_time < cutoff_time:
                # 可以在这里实现更复杂的清理逻辑
                pass

# 全局系统日志实例
system_logger = SystemLogger()

# 便捷函数
def log_system_info(message: str, **kwargs):
    system_logger.loggers["system"].info(message, extra=kwargs)

def log_system_warning(message: str, **kwargs):
    system_logger.loggers["system"].warning(message, extra=kwargs)

def log_system_error(message: str, **kwargs):
    system_logger.loggers["system"].error(message, extra=kwargs)

