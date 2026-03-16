"""
错误日志模块 - 记录系统错误
负责记录系统运行过程中出现的所有错误和异常
"""

import logging
import json
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Type
from enum import Enum

class ErrorSeverity(Enum):
    LOW = "LOW"        # 轻微错误，不影响系统运行
    MEDIUM = "MEDIUM"  # 中等错误，可能影响部分功能
    HIGH = "HIGH"      # 严重错误，影响核心功能
    CRITICAL = "CRITICAL"  # 致命错误，可能导致系统崩溃

class ErrorCategory(Enum):
    SYSTEM_ERROR = "system_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    AI_MODEL_ERROR = "ai_model_error"
    MEMORY_ERROR = "memory_error"
    SECURITY_ERROR = "security_error"
    USER_INPUT_ERROR = "user_input_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorLogger:
    """错误日志记录器"""
    
    def __init__(self, log_dir: str = "logs/error"):
        self.log_dir = log_dir
        self._setup_logging()
        self._setup_exception_hook()
    
    def _setup_logging(self):
        """配置错误日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 错误日志记录器
        self.logger = logging.getLogger("error")
        self.logger.setLevel(logging.ERROR)
        
        # 错误日志文件处理器
        log_file = f"{self.log_dir}/error.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # 详细错误格式
        formatter = logging.Formatter(
            '%(asctime)s - ERROR - %(name)s - %(levelname)s\n'
            '模块: %(module)s\n函数: %(funcName)s\n行号: %(lineno)d\n'
            '消息: %(message)s\n',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_exception_hook(self):
        """设置全局异常钩子"""
        def global_exception_handler(exc_type, exc_value, exc_traceback):
            # 忽略KeyboardInterrupt，让控制台正常处理Ctrl+C
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # 记录未捕获的异常
            self.log_uncaught_exception(exc_type, exc_value, exc_traceback)
            
            # 调用默认的异常处理器
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = global_exception_handler
    
    def log_error(self,
                 error_message: str,
                 severity: ErrorSeverity,
                 category: ErrorCategory,
                 component: str,
                 exception: Optional[Exception] = None,
                 context: Optional[Dict[str, Any]] = None) -> str:
        """记录错误"""
        
        error_id = self._generate_error_id()
        timestamp = datetime.now()
        
        # 获取堆栈跟踪
        stack_trace = None
        if exception:
            stack_trace = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        else:
            # 获取当前堆栈
            stack_trace = ''.join(traceback.format_stack()[:-1])
        
        error_record = {
            "error_id": error_id,
            "timestamp": timestamp.isoformat(),
            "severity": severity.value,
            "category": category.value,
            "component": component,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "context": context or {},
            "system_info": self._get_system_info()
        }
        
        # 写入结构化错误日志
        self._write_error_log(error_record)
        
        # 根据严重级别记录到不同日志级别
        log_message = f"{error_message} [ErrorID: {error_id}]"
        extra_info = {
            "component": component,
            "error_id": error_id
        }
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra=extra_info, exc_info=exception)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra=extra_info, exc_info=exception)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra=extra_info, exc_info=exception)
        else:
            self.logger.info(log_message, extra=extra_info, exc_info=exception)
        
        return error_id
    
    def log_uncaught_exception(self, exc_type: Type[BaseException], exc_value: BaseException, exc_traceback):
        """记录未捕获的异常"""
        error_message = f"未捕获的异常: {exc_type.__name__}: {exc_value}"
        
        error_record = {
            "error_id": self._generate_error_id(),
            "timestamp": datetime.now().isoformat(),
            "severity": ErrorSeverity.CRITICAL.value,
            "category": ErrorCategory.SYSTEM_ERROR.value,
            "component": "system",
            "error_message": error_message,
            "stack_trace": ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
            "context": {"uncaught": True},
            "system_info": self._get_system_info()
        }
        
        self._write_error_log(error_record)
        
        # 记录到错误日志
        self.logger.critical(
            f"未捕获的异常: {error_message}",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    def log_ai_model_error(self, model_name: str, error: Exception, input_data: Optional[Dict] = None):
        """记录AI模型错误"""
        context = {
            "model_name": model_name,
            "input_data_preview": str(input_data)[:500] if input_data else None
        }
        
        return self.log_error(
            f"AI模型错误: {model_name} - {str(error)}",
            ErrorSeverity.HIGH,
            ErrorCategory.AI_MODEL_ERROR,
            "ai_engine",
            error,
            context
        )
    
    def log_database_error(self, operation: str, error: Exception, query: Optional[str] = None):
        """记录数据库错误"""
        context = {
            "operation": operation,
            "query_preview": query[:200] + "..." if query and len(query) > 200 else query
        }
        
        return self.log_error(
            f"数据库错误: {operation} - {str(error)}",
            ErrorSeverity.HIGH,
            ErrorCategory.DATABASE_ERROR,
            "database",
            error,
            context
        )
    
    def log_network_error(self, service: str, endpoint: str, error: Exception, status_code: Optional[int] = None):
        """记录网络错误"""
        context = {
            "service": service,
            "endpoint": endpoint,
            "status_code": status_code
        }
        
        return self.log_error(
            f"网络错误: {service} - {endpoint} - {str(error)}",
            ErrorSeverity.MEDIUM,
            ErrorCategory.NETWORK_ERROR,
            "network",
            error,
            context
        )
    
    def log_memory_error(self, memory_type: str, operation: str, error: Exception, details: Dict[str, Any]):
        """记录内存错误"""
        context = {
            "memory_type": memory_type,
            "operation": operation,
            "details": details
        }
        
        return self.log_error(
            f"内存错误: {memory_type} - {operation} - {str(error)}",
            ErrorSeverity.HIGH,
            ErrorCategory.MEMORY_ERROR,
            "memory_system",
            error,
            context
        )
    
    def _generate_error_id(self) -> str:
        """生成错误ID"""
        import hashlib
        base_string = f"{datetime.now().isoformat()}{id(self)}"
        return hashlib.md5(base_string.encode()).hexdigest()[:8].upper()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def _write_error_log(self, error_record: Dict[str, Any]):
        """写入错误日志文件"""
        import os
        log_file = f"{self.log_dir}/error_details.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_record, ensure_ascii=False) + '\n')
    
    def get_recent_errors(self, hours: int = 24, severity: Optional[ErrorSeverity] = None) -> List[Dict[str, Any]]:
        """获取最近的错误"""
        import os
        from datetime import datetime, timedelta
        
        errors = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        log_file = f"{self.log_dir}/error_details.jsonl"
        if not os.path.exists(log_file):
            return errors
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    error = json.loads(line.strip())
                    error_time = datetime.fromisoformat(error['timestamp'])
                    if error_time >= cutoff_time:
                        if severity is None or error['severity'] == severity.value:
                            errors.append(error)
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # 按时间倒序排列
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        return errors
    
    def analyze_error_trends(self) -> Dict[str, Any]:
        """分析错误趋势"""
        import os
        from collections import Counter
        from datetime import datetime, timedelta
        
        if not os.path.exists(f"{self.log_dir}/error_details.jsonl"):
            return {}
        
        categories = []
        severities = []
        components = []
        recent_errors = 0
        
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
        
        with open(f"{self.log_dir}/error_details.jsonl", 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    error = json.loads(line.strip())
                    categories.append(error['category'])
                    severities.append(error['severity'])
                    components.append(error['component'])
                    
                    error_time = datetime.fromisoformat(error['timestamp'])
                    if error_time >= twenty_four_hours_ago:
                        recent_errors += 1
                except (json.JSONDecodeError, KeyError):
                    continue
        
        analysis = {
            "total_errors": len(categories),
            "recent_errors_24h": recent_errors,
            "category_distribution": dict(Counter(categories)),
            "severity_distribution": dict(Counter(severities)),
            "component_distribution": dict(Counter(components)),
            "most_common_category": max(Counter(categories).items(), key=lambda x: x[1])[0] if categories else None,
            "most_error_prone_component": max(Counter(components).items(), key=lambda x: x[1])[0] if components else None
        }
        
        return analysis
    
    def create_error_report(self, days: int = 7) -> Dict[str, Any]:
        """创建错误报告"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        recent_errors = self.get_recent_errors(hours=days*24)
        
        critical_errors = [e for e in recent_errors if e['severity'] == 'CRITICAL']
        high_errors = [e for e in recent_errors if e['severity'] == 'HIGH']
        
        report = {
            "report_period": f"最近{days}天",
            "total_errors": len(recent_errors),
            "critical_errors": len(critical_errors),
            "high_errors": len(high_errors),
            "error_trends": self.analyze_error_trends(),
            "top_issues": self._identify_top_issues(recent_errors),
            "recommendations": self._generate_recommendations(recent_errors)
        }
        
        return report
    
    def _identify_top_issues(self, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别主要问题"""
        from collections import Counter
        
        if not errors:
            return []
        
        # 按错误消息分组
        error_messages = [e['error_message'] for e in errors]
        message_counts = Counter(error_messages)
        
        top_issues = []
        for message, count in message_counts.most_common(5):
            # 找到这个错误的一个例子
            example_error = next(e for e in errors if e['error_message'] == message)
            top_issues.append({
                "error_message": message,
                "count": count,
                "severity": example_error['severity'],
                "component": example_error['component']
            })
        
        return top_issues
    
    def _generate_recommendations(self, errors: List[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        critical_errors = [e for e in errors if e['severity'] == 'CRITICAL']
        if critical_errors:
            recommendations.append("发现严重错误，建议立即检查系统稳定性")
        
        ai_errors = [e for e in errors if e['category'] == 'ai_model_error']
        if len(ai_errors) > 10:
            recommendations.append("AI模型错误较多，建议检查模型服务和输入数据")
        
        memory_errors = [e for e in errors if e['category'] == 'memory_error']
        if memory_errors:
            recommendations.append("存在内存错误，建议检查内存管理和资源分配")
        
        database_errors = [e for e in errors if e['category'] == 'database_error']
        if database_errors:
            recommendations.append("数据库错误频发，建议检查数据库连接和查询优化")
        
        if not recommendations:
            recommendations.append("系统运行相对稳定，继续保持监控")
        
        return recommendations

# 全局错误日志实例
error_logger = ErrorLogger()

# 便捷的装饰器，用于捕获函数中的异常
def catch_errors(component: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """捕获函数中异常的装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_logger.log_error(
                    f"函数 {func.__name__} 执行失败: {str(e)}",
                    severity,
                    ErrorCategory.SYSTEM_ERROR,
                    component,
                    e
                )
                raise  # 重新抛出异常
        return wrapper
    return decorator

