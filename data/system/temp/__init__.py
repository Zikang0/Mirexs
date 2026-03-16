"""
临时文件管理包
负责临时文件、会话数据和定期清理的管理
"""

from .temp_file_manager import TempFileManager, temp_file_manager, TempFileInfo, TempFileType
from .session_data import SessionManager, session_manager, SessionData, SessionState
from .cleanup_scheduler import CleanupScheduler, cleanup_scheduler, CleanupTask, CleanupTaskStatus

__all__ = [
    # 临时文件管理
    'TempFileManager', 'temp_file_manager', 'TempFileInfo', 'TempFileType',
    
    # 会话数据管理
    'SessionManager', 'session_manager', 'SessionData', 'SessionState',
    
    # 清理调度
    'CleanupScheduler', 'cleanup_scheduler', 'CleanupTask', 'CleanupTaskStatus'
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Mirexs AI Team'
__description__ = 'Mirexs 临时文件管理系统'