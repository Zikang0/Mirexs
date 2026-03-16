"""
协议适配器模块 - Mirexs设备连接器

提供各种通信协议的适配器实现，包括：
- 蓝牙协议适配器
- WiFi协议适配器
- USB协议适配器
- 云同步适配器
- MQTT协议适配器
- WebSocket协议适配器
- HTTP协议适配器
- 协议性能指标收集
"""

from .bluetooth_handler import BluetoothHandler, BluetoothConfig, BluetoothDevice, ConnectionStatus
from .wifi_handler import WiFiHandler, WiFiConfig, WiFiNetwork, WiFiSecurity
from .usb_handler import USBHandler, USBConfig, USBDevice, USBInterface
from .cloud_sync import CloudSync, CloudSyncConfig, CloudProvider, SyncStatus
from .mqtt_adapter import MQTTAdapter, MQTTConfig, QoS, MQTTMessage
from .websocket_adapter import WebSocketAdapter, WebSocketAdapterConfig, WSConnection, WSMessage
from .http_adapter import HTTPAdapter, HTTPConfig, HTTPMethod, HTTPRequest, HTTPResponse
from .protocol_metrics import ProtocolMetrics, ProtocolType, ProtocolStats

__all__ = [
    'BluetoothHandler', 'BluetoothConfig', 'BluetoothDevice', 'ConnectionStatus',
    'WiFiHandler', 'WiFiConfig', 'WiFiNetwork', 'WiFiSecurity',
    'USBHandler', 'USBConfig', 'USBDevice', 'USBInterface',
    'CloudSync', 'CloudSyncConfig', 'CloudProvider', 'SyncStatus',
    'MQTTAdapter', 'MQTTConfig', 'QoS', 'MQTTMessage',
    'WebSocketAdapter', 'WebSocketAdapterConfig', 'WSConnection', 'WSMessage',
    'HTTPAdapter', 'HTTPConfig', 'HTTPMethod', 'HTTPRequest', 'HTTPResponse',
    'ProtocolMetrics', 'ProtocolType', 'ProtocolStats'
]

