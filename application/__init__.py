"""
应用接口层 - Mirexs数字生命体

提供多端应用接口与设备连接能力，包括：
- 桌面应用程序 (Windows, macOS, Linux)
- 移动应用程序 (iOS, Android)
- Web界面 (Web App, PWA, 浏览器扩展)
- 设备连接器 (蓝牙, WiFi, USB, IoT)
- API网关 (REST API, WebSocket, 插件系统)

此模块是Mirexs与用户交互的入口点，负责将底层能力呈现给用户，
并处理用户输入和系统输出。
"""

from .desktop_app import (
    WindowsClient, MacOSClient, LinuxClient,
    MainWindow, TaskbarIntegration, SystemTray,
    WindowManager, ThemeSelector, ShortcutHandler,
    DesktopMetrics
)

from .mobile_app import (
    iOSApp, AndroidApp, MobileUI, TouchGestures,
    MobileNotifications, OfflineSupport, BatteryOptimizer,
    MobileSensors, MobileMetrics
)

from .web_interface import (
    WebApp, BrowserExtension, ProgressiveWebApp,
    WebComponents, ServiceWorker, WebSockets,
    ResponsiveDesign, WebStorage, WebMetrics
)

from .device_connector import (
    BluetoothHandler, WiFiHandler, USBHandler, CloudSync,
    MQTTAdapter, WebSocketAdapter, HTTPAdapter, ProtocolMetrics,
    SensorData, NotificationSync, CrossDeviceContinuity,
    LocationSharing, MobileRemote, DataSyncMobile,
    IoTDeviceManager, SceneAutomation, EnvironmentSensing,
    HomeAssistant, EnergyManagement, SecuritySystems,
    MultiDeviceSync, ConflictResolution, OfflineOperation,
    SyncScheduler, DataConsistency, SyncEncryption
)

from .api_gateway import (
    RESTAPI, WebhookHandler, PluginSystem,
    SDKDevelopment, Documentation, RateLimiter,
    APIAuthenticator, RequestValidator, ResponseFormatter,
    APIMonitor, APIMetrics
)

__version__ = "0.1.0"
__all__ = [
    # 桌面应用
    'WindowsClient', 'MacOSClient', 'LinuxClient',
    'MainWindow', 'TaskbarIntegration', 'SystemTray',
    'WindowManager', 'ThemeSelector', 'ShortcutHandler',
    'DesktopMetrics',
    
    # 移动应用
    'iOSApp', 'AndroidApp', 'MobileUI', 'TouchGestures',
    'MobileNotifications', 'OfflineSupport', 'BatteryOptimizer',
    'MobileSensors', 'MobileMetrics',
    
    # Web界面
    'WebApp', 'BrowserExtension', 'ProgressiveWebApp',
    'WebComponents', 'ServiceWorker', 'WebSockets',
    'ResponsiveDesign', 'WebStorage', 'WebMetrics',
    
    # 设备连接器
    'BluetoothHandler', 'WiFiHandler', 'USBHandler', 'CloudSync',
    'MQTTAdapter', 'WebSocketAdapter', 'HTTPAdapter', 'ProtocolMetrics',
    'SensorData', 'NotificationSync', 'CrossDeviceContinuity',
    'LocationSharing', 'MobileRemote', 'DataSyncMobile',
    'IoTDeviceManager', 'SceneAutomation', 'EnvironmentSensing',
    'HomeAssistant', 'EnergyManagement', 'SecuritySystems',
    'MultiDeviceSync', 'ConflictResolution', 'OfflineOperation',
    'SyncScheduler', 'DataConsistency', 'SyncEncryption',
    
    # API网关
    'RESTAPI', 'WebhookHandler', 'PluginSystem',
    'SDKDevelopment', 'Documentation', 'RateLimiter',
    'APIAuthenticator', 'RequestValidator', 'ResponseFormatter',
    'APIMonitor', 'APIMetrics'
]
