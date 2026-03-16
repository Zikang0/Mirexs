"""
邮件助手插件模块

提供邮件处理和智能回复功能，包括：
- Gmail集成
- Outlook集成
- 邮件分析器
- 智能回复
- 垃圾邮件过滤

Author: AI Assistant
Date: 2025-11-05
"""

from .gmail_integration import GmailIntegration
from .outlook_integration import OutlookIntegration
from .email_analyzer import EmailAnalyzer
from .smart_reply import SmartReply
from .spam_filter import SpamFilter

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 邮件助手插件列表
EMAIL_ASSISTANT_PLUGINS = {
    "gmail_integration": GmailIntegration,
    "outlook_integration": OutlookIntegration,
    "email_analyzer": EmailAnalyzer,
    "smart_reply": SmartReply,
    "spam_filter": SpamFilter
}

def get_email_assistant_plugins():
    """获取所有邮件助手插件"""
    return list(EMAIL_ASSISTANT_PLUGINS.keys())