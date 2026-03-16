"""
社区插件模块

该模块包含社区开发的插件集合，包括：
- 第三方插件：第三方服务集成
- 用户创建插件：用户自定义插件
- 实验性插件：前沿技术试验

Author: AI Assistant
Date: 2025-11-05
"""

from .third_party import *
from .user_created import *
from .experimental import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 社区插件分类
COMMUNITY_PLUGIN_CATEGORIES = {
    "third_party": "第三方插件",
    "user_created": "用户创建插件",
    "experimental": "实验性插件"
}

def get_community_plugins():
    """获取所有社区插件列表"""
    return list(COMMUNITY_PLUGIN_CATEGORIES.keys())