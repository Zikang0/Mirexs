"""
系统日志包
提供完整的系统日志记录、管理和分析功能
"""

from .system_logs import SystemLogger, system_logger, log_system_info, log_system_warning, log_system_error
from .security_logs import SecurityLogger, security_logger, SecurityEventType, SecurityLevel
from .performance_logs import PerformanceLogger, performance_logger, PerformanceMetric, Timer
from .interaction_logs import InteractionLogger, interaction_logger, InteractionType, InteractionChannel
from .error_logs import ErrorLogger, error_logger, ErrorSeverity, ErrorCategory, catch_errors
from .audit_logs import AuditLogger, audit_logger, AuditAction, AuditResource, AuditStatus
from .log_rotator import LogRotator, log_rotator
from .log_analyzer import LogAnalyzer, log_analyzer

__all__ = [
    # 系统日志
    'SystemLogger', 'system_logger', 'log_system_info', 'log_system_warning', 'log_system_error',
    
    # 安全日志
    'SecurityLogger', 'security_logger', 'SecurityEventType', 'SecurityLevel',
    
    # 性能日志
    'PerformanceLogger', 'performance_logger', 'PerformanceMetric', 'Timer',
    
    # 交互日志
    'InteractionLogger', 'interaction_logger', 'InteractionType', 'InteractionChannel',
    
    # 错误日志
    'ErrorLogger', 'error_logger', 'ErrorSeverity', 'ErrorCategory', 'catch_errors',
    
    # 审计日志
    'AuditLogger', 'audit_logger', 'AuditAction', 'AuditResource', 'AuditStatus',
    
    # 日志轮转
    'LogRotator', 'log_rotator',
    
    # 日志分析
    'LogAnalyzer', 'log_analyzer'
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Mirexs AI Team'
__description__ = 'Mirexs 系统日志管理系统'
