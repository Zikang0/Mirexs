"""
API库模块

提供插件开发所需的核心API和扩展API，包括：
- 核心API：基础功能API
- 扩展API：高级功能API
- 工具函数：通用工具函数
- 类型定义：数据类型定义

Author: AI Assistant
Date: 2025-11-05
"""

from .core_apis import CoreAPIs
from .extension_apis import ExtensionAPIs
from .utility_functions import UtilityFunctions
from .type_definitions import TypeDefinitions

__version__ = "1.0.0"
__author__ = "AI Assistant"

# API库组件
API_LIBRARY_COMPONENTS = {
    "core_apis": CoreAPIs,
    "extension_apis": ExtensionAPIs,
    "utility_functions": UtilityFunctions,
    "type_definitions": TypeDefinitions
}

def get_api_library_components():
    """获取所有API库组件"""
    return list(API_LIBRARY_COMPONENTS.keys())