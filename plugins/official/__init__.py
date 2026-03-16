"""
官方插件模块

该模块包含由官方开发的插件集合，包括：
- 生产力插件：提高工作效率的工具
- 创意插件：支持创意工作的功能
- 开发工具插件：开发过程中的辅助工具
- 娱乐插件：休闲娱乐功能

Author: AI Assistant
Date: 2025-11-05
"""

from .productivity import *
from .creative import *
from .development import *
from .entertainment import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 官方插件分类
PLUGIN_CATEGORIES = {
    "productivity": "生产力插件",
    "creative": "创意插件", 
    "development": "开发工具插件",
    "entertainment": "娱乐插件"
}

def get_official_plugins():
    """获取所有官方插件列表"""
    return PLUGIN_CATEGORIES.keys()

def get_plugins_by_category(category: str):
    """根据分类获取插件列表"""
    return PLUGIN_CATEGORIES.get(category, [])