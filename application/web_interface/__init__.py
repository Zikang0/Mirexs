"""
Web界面模块 - Mirexs应用接口层

提供Web平台客户端实现，包括：
1. Web应用 (React/Vue)
2. 浏览器扩展
3. 渐进式Web应用 (PWA)
4. WebSocket实时通信
5. Service Worker离线支持
6. 响应式设计
7. Web存储管理
8. Web性能指标收集

此模块负责Mirexs数字生命体在浏览器环境中的运行和交互。
"""

from .web_app import WebApp, WebAppConfig
from .browser_extension import BrowserExtension, ExtensionConfig
from .progressive_web_app import ProgressiveWebApp, PWAConfig
from .web_components import WebComponents, ComponentRegistry
from .service_worker import ServiceWorker, WorkerConfig
from .web_sockets import WebSocketManager, WebSocketConfig
from .responsive_design import ResponsiveDesign, Breakpoint
from .web_storage import WebStorage, StorageType
from .web_metrics import WebMetrics, WebPerformanceReport

__all__ = [
    # Web应用
    'WebApp', 'WebAppConfig',
    
    # 浏览器扩展
    'BrowserExtension', 'ExtensionConfig',
    
    # PWA
    'ProgressiveWebApp', 'PWAConfig',
    
    # Web组件
    'WebComponents', 'ComponentRegistry',
    
    # Service Worker
    'ServiceWorker', 'WorkerConfig',
    
    # WebSocket
    'WebSocketManager', 'WebSocketConfig',
    
    # 响应式设计
    'ResponsiveDesign', 'Breakpoint',
    
    # Web存储
    'WebStorage', 'StorageType',
    
    # Web指标
    'WebMetrics', 'WebPerformanceReport'
]

