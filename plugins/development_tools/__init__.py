"""
开发工具模块

该模块提供插件开发所需的工具和SDK，包括：
- 插件SDK：开发插件的完整工具包
- 调试工具：插件调试和分析工具
- 文档工具：文档生成和管理工具

Author: AI Assistant
Date: 2025-11-05
"""

from .plugin_sdk import *
from .debug_tools import *
from .documentation_tools import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 开发工具分类
DEVELOPMENT_TOOLS = {
    "plugin_sdk": "插件SDK",
    "debug_tools": "调试工具",
    "documentation_tools": "文档工具"
}

def get_development_tools():
    """获取所有开发工具列表"""
    return list(DEVELOPMENT_TOOLS.keys())