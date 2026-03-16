"""
移动应用程序模块 - Mirexs应用接口层

提供移动端应用程序实现，包括iOS和Android平台客户端，
以及移动端特有的UI、手势、通知、离线支持、电池优化和传感器集成等功能。

此模块负责Mirexs数字生命体在移动设备上的运行和交互，包括：
1. iOS和Android原生客户端实现
2. 移动端用户界面适配
3. 触摸手势识别
4. 移动通知系统
5. 离线功能支持
6. 电池使用优化
7. 移动传感器集成
8. 移动端性能指标收集
"""

from .ios_app import iOSApp, iOSAppConfig
from .android_app import AndroidApp, AndroidAppConfig
from .mobile_ui import MobileUI, MobileUIConfig, ScreenOrientation, UITheme
from .touch_gestures import TouchGestures, GestureType, GestureEvent
from .mobile_notifications import MobileNotifications, NotificationPriority, NotificationChannel
from .offline_support import OfflineSupport, SyncStatus, OfflineQueue
from .battery_optimizer import BatteryOptimizer, PowerMode, BatteryStats
from .mobile_sensors import MobileSensors, SensorType, SensorData
from .mobile_metrics import MobileMetrics, MobilePerformanceReport

__all__ = [
    # iOS
    'iOSApp', 'iOSAppConfig',
    
    # Android
    'AndroidApp', 'AndroidAppConfig',
    
    # 移动UI
    'MobileUI', 'MobileUIConfig', 'ScreenOrientation', 'UITheme',
    
    # 触摸手势
    'TouchGestures', 'GestureType', 'GestureEvent',
    
    # 移动通知
    'MobileNotifications', 'NotificationPriority', 'NotificationChannel',
    
    # 离线支持
    'OfflineSupport', 'SyncStatus', 'OfflineQueue',
    
    # 电池优化
    'BatteryOptimizer', 'PowerMode', 'BatteryStats',
    
    # 移动传感器
    'MobileSensors', 'SensorType', 'SensorData',
    
    # 移动指标
    'MobileMetrics', 'MobilePerformanceReport'
]
