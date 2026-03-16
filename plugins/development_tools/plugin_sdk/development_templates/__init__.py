"""
开发模板模块

提供插件开发所需的各种模板，包括：
- 基础插件模板
- AI插件模板
- 集成插件模板

Author: AI Assistant
Date: 2025-11-05
"""

from .basic_plugin import *
from .ai_plugin import *
from .integration_plugin import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 开发模板列表
DEVELOPMENT_TEMPLATES = {
    "basic_plugin": "基础插件模板",
    "ai_plugin": "AI插件模板",
    "integration_plugin": "集成插件模板"
}

def get_development_templates():
    """获取所有开发模板"""
    return list(DEVELOPMENT_TEMPLATES.keys())