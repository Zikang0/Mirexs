"""
工具集成框架模块
提供统一的工具集成、管理和调用功能
"""

from .web_browser import WebBrowserTool, WebContentExtractor
from .office_tools import WordProcessor, ExcelProcessor, PowerPointProcessor, OfficeAutomation
from .development_tools import CodeEditor, CodeExecutor, Debugger, VersionControl, DevelopmentToolsManager
from .creative_tools import ImageGenerator, ImageEditor, MusicGenerator, VideoEditor, CreativeToolsManager
from .system_tools import SystemInfo, ProcessManager, FileSystemManager, SystemMonitor, SystemToolsManager
from .custom_tools import CustomTool, ToolPackageManager, PythonFunctionTool, CommandLineTool, CustomToolsManager
from .tool_discovery import ToolDiscoverer, ToolRegistry
from .tool_wrapper import BaseToolWrapper, PythonFunctionWrapper, CommandLineWrapper, WebServiceWrapper, CompositeToolWrapper, ToolWrapperFactory, ToolExecutionManager
from .tool_registry import ToolRegistry, ToolMetadata, ToolCategory, ToolStatus, ToolRegistryManager
from .dependency_manager import Dependency, DependencyResolver, DependencyManager, DependencyStatus, PackageManager
from .compatibility_checker import CompatibilityChecker, CompatibilityLevel, CompatibilityResult
from .tool_metrics import ToolMetricsCollector, ToolOptimizationAdvisor, MetricType, PerformanceStats

__all__ = [
    # Web浏览器工具
    "WebBrowserTool",
    "WebContentExtractor",
    
    # Office工具
    "WordProcessor",
    "ExcelProcessor",
    "PowerPointProcessor",
    "OfficeAutomation",
    
    # 开发工具
    "CodeEditor",
    "CodeExecutor",
    "Debugger",
    "VersionControl",
    "DevelopmentToolsManager",
    
    # 创意工具
    "ImageGenerator",
    "ImageEditor",
    "MusicGenerator",
    "VideoEditor",
    "CreativeToolsManager",
    
    # 系统工具
    "SystemInfo",
    "ProcessManager",
    "FileSystemManager",
    "SystemMonitor",
    "SystemToolsManager",
    
    # 自定义工具
    "CustomTool",
    "ToolPackageManager",
    "PythonFunctionTool",
    "CommandLineTool",
    "CustomToolsManager",
    
    # 工具发现
    "ToolDiscoverer",
    "ToolRegistry",
    
    # 工具包装器
    "BaseToolWrapper",
    "PythonFunctionWrapper",
    "CommandLineWrapper",
    "WebServiceWrapper",
    "CompositeToolWrapper",
    "ToolWrapperFactory",
    "ToolExecutionManager",
    
    # 工具注册表
    "ToolRegistry",
    "ToolMetadata",
    "ToolCategory",
    "ToolStatus",
    "ToolRegistryManager",
    
    # 依赖管理
    "Dependency",
    "DependencyResolver",
    "DependencyManager",
    "DependencyStatus",
    "PackageManager",
    
    # 兼容性检查
    "CompatibilityChecker",
    "CompatibilityLevel",
    "CompatibilityResult",
    
    # 工具指标
    "ToolMetricsCollector",
    "ToolOptimizationAdvisor",
    "MetricType",
    "PerformanceStats",
]

__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Mirexs工具集成框架，提供统一的工具集成、管理和调用功能"

# 初始化日志配置
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
