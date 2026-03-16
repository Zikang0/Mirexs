"""
设备连接器模块 - Mirexs应用接口层

提供各种设备连接和协议适配功能，包括：
1. 协议适配器（蓝牙、WiFi、USB、MQTT、WebSocket、HTTP）
2. 移动设备集成（传感器、通知、跨设备连续性、位置共享、远程控制）
3. 智能家居集成（IoT设备管理、场景自动化、环境感知、能源管理）
4. 数据同步系统（多设备同步、冲突解决、离线操作、数据一致性）

此模块负责Mirexs数字生命体与外部设备的连接和数据交换。
"""

from .protocol_adapters import (
    BluetoothHandler, BluetoothConfig,
    WiFiHandler, WiFiConfig,
    USBHandler, USBConfig,
    CloudSync, CloudSyncConfig,
    MQTTAdapter, MQTTConfig,
    WebSocketAdapter, WebSocketAdapterConfig,
    HTTPAdapter, HTTPConfig,
    ProtocolMetrics
)

from .mobile_integration import (
    SensorData, SensorDataType,
    NotificationSync, NotificationSyncConfig,
    CrossDeviceContinuity, ContinuityConfig,
    LocationSharing, LocationConfig,
    MobileRemote, RemoteControlConfig,
    DataSyncMobile, MobileSyncConfig,
    MobileIntegrationMetrics
)

from .smart_home import (
    IoTDeviceManager, IoTDevice, DeviceType,
    SceneAutomation, Scene, AutomationRule,
    EnvironmentSensing, EnvironmentData,
    HomeAssistant, HomeAssistantConfig,
    EnergyManagement, EnergyStats,
    SecuritySystems, SecurityConfig,
    SmartHomeMetrics
)

from .data_sync import (
    MultiDeviceSync, DeviceInfo,
    ConflictResolution, ConflictStrategy,
    OfflineOperation, OfflineQueue,
    SyncScheduler, SyncTask,
    DataConsistency, ConsistencyCheck,
    SyncEncryption, EncryptionConfig,
    SyncMetrics
)

__all__ = [
    # 协议适配器
    'BluetoothHandler', 'BluetoothConfig',
    'WiFiHandler', 'WiFiConfig',
    'USBHandler', 'USBConfig',
    'CloudSync', 'CloudSyncConfig',
    'MQTTAdapter', 'MQTTConfig',
    'WebSocketAdapter', 'WebSocketAdapterConfig',
    'HTTPAdapter', 'HTTPConfig',
    'ProtocolMetrics',
    
    # 移动设备集成
    'SensorData', 'SensorDataType',
    'NotificationSync', 'NotificationSyncConfig',
    'CrossDeviceContinuity', 'ContinuityConfig',
    'LocationSharing', 'LocationConfig',
    'MobileRemote', 'RemoteControlConfig',
    'DataSyncMobile', 'MobileSyncConfig',
    'MobileIntegrationMetrics',
    
    # 智能家居集成
    'IoTDeviceManager', 'IoTDevice', 'DeviceType',
    'SceneAutomation', 'Scene', 'AutomationRule',
    'EnvironmentSensing', 'EnvironmentData',
    'HomeAssistant', 'HomeAssistantConfig',
    'EnergyManagement', 'EnergyStats',
    'SecuritySystems', 'SecurityConfig',
    'SmartHomeMetrics',
    
    # 数据同步系统
    'MultiDeviceSync', 'DeviceInfo',
    'ConflictResolution', 'ConflictStrategy',
    'OfflineOperation', 'OfflineQueue',
    'SyncScheduler', 'SyncTask',
    'DataConsistency', 'ConsistencyCheck',
    'SyncEncryption', 'EncryptionConfig',
    'SyncMetrics'
]

