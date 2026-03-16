"""
插件SDK模块

提供完整的插件开发工具包，包括：
- API库：核心API和扩展API
- 开发模板：基础插件、AI插件、集成插件模板
- 测试框架：单元测试、集成测试、性能测试
- 部署工具：打包、签名、分发工具

Author: AI Assistant
Date: 2025-11-05
"""

from .api_library import *
from .development_templates import *
from .testing_framework import *
from .deployment_tools import *

__version__ = "1.0.0"
__author__ = "AI Assistant"

# SDK组件列表
SDK_COMPONENTS = {
    "api_library": "API库",
    "development_templates": "开发模板",
    "testing_framework": "测试框架",
    "deployment_tools": "部署工具"
}

def get_sdk_components():
    """获取所有SDK组件列表"""
    return list(SDK_COMPONENTS.keys())