"""
日历集成插件模块

提供日历功能集成，包括：
- Google日历集成
- Outlook日历集成
- 事件调度器
- 提醒系统

Author: AI Assistant
Date: 2025-11-05
"""

from .google_calendar import GoogleCalendarIntegration
from .outlook_calendar import OutlookCalendarIntegration
from .event_scheduler import EventScheduler
from .reminder_system import ReminderSystem

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 日历集成插件列表
CALENDAR_PLUGINS = {
    "google_calendar": GoogleCalendarIntegration,
    "outlook_calendar": OutlookCalendarIntegration,
    "event_scheduler": EventScheduler,
    "reminder_system": ReminderSystem
}

def get_calendar_plugins():
    """获取所有日历集成插件"""
    return list(CALENDAR_PLUGINS.keys())

def get_plugin_class(plugin_name: str):
    """获取插件类"""
    return CALENDAR_PLUGINS.get(plugin_name)