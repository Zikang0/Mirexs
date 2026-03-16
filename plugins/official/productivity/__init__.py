"""
生产力插件模块

提供提高工作效率的插件集合，包括：
- 日历集成：日历管理和事件调度
- 邮件助手：邮件处理和智能回复
- 文档管理：文件整理和版本控制
- 任务自动化：工作流构建和批处理

Author: AI Assistant
Date: 2025-11-05
"""

from .calendar_integration import *
from .email_assistant import *
from .document_management import *
from .task_automation import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 生产力插件列表
PRODUCTIVITY_PLUGINS = {
    "calendar_integration": "日历集成",
    "email_assistant": "邮件助手",
    "document_management": "文档管理",
    "task_automation": "任务自动化"
}

def get_productivity_plugins():
    """获取所有生产力插件列表"""
    return list(PRODUCTIVITY_PLUGINS.keys())