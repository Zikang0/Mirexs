"""
移动设备集成模块 - Mirexs设备连接器

提供移动设备集成功能，包括：
- 传感器数据获取
- 通知同步
- 跨设备连续性
- 位置共享
- 移动远程控制
- 数据同步
- 移动集成性能指标
"""

from .sensor_data import SensorData, SensorDataType, SensorManager, SensorConfig
from .notification_sync import NotificationSync, NotificationSyncConfig, NotificationMessage
from .cross_device_cont import CrossDeviceContinuity, ContinuityConfig, ContinuitySession
from .location_sharing import LocationSharing, LocationConfig, LocationData
from .mobile_remote import MobileRemote, RemoteControlConfig, RemoteCommand
from .data_sync_mobile import DataSyncMobile, MobileSyncConfig, MobileSyncStatus
from .mobile_integration_metrics import MobileIntegrationMetrics, MobileIntegrationStats

__all__ = [
    'SensorData', 'SensorDataType', 'SensorManager', 'SensorConfig',
    'NotificationSync', 'NotificationSyncConfig', 'NotificationMessage',
    'CrossDeviceContinuity', 'ContinuityConfig', 'ContinuitySession',
    'LocationSharing', 'LocationConfig', 'LocationData',
    'MobileRemote', 'RemoteControlConfig', 'RemoteCommand',
    'DataSyncMobile', 'MobileSyncConfig', 'MobileSyncStatus',
    'MobileIntegrationMetrics', 'MobileIntegrationStats'
]

