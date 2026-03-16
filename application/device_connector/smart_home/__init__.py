"""
智能家居集成模块 - Mirexs设备连接器

提供智能家居设备集成功能，包括：
- IoT设备管理
- 场景自动化
- 环境感知
- 家庭助理
- 能源管理
- 安全系统
- 智能家居指标
"""

from .iot_device_mgr import IoTDeviceManager, IoTDevice, DeviceType, DeviceProtocol, DeviceStatus
from .scene_automation import SceneAutomation, Scene, AutomationRule, TriggerType, ActionType
from .environment_sensing import EnvironmentSensing, EnvironmentData, SensorType, AirQuality
from .home_assistant import HomeAssistant, HomeAssistantConfig, HassEntity, HassService
from .energy_management import EnergyManagement, EnergyStats, PowerMeter, EnergyPrice
from .security_systems import SecuritySystems, SecurityConfig, SecurityEvent, AlarmStatus
from .smart_home_metrics import SmartHomeMetrics, SmartHomeStats, DeviceMetrics

__all__ = [
    'IoTDeviceManager', 'IoTDevice', 'DeviceType', 'DeviceProtocol', 'DeviceStatus',
    'SceneAutomation', 'Scene', 'AutomationRule', 'TriggerType', 'ActionType',
    'EnvironmentSensing', 'EnvironmentData', 'SensorType', 'AirQuality',
    'HomeAssistant', 'HomeAssistantConfig', 'HassEntity', 'HassService',
    'EnergyManagement', 'EnergyStats', 'PowerMeter', 'EnergyPrice',
    'SecuritySystems', 'SecurityConfig', 'SecurityEvent', 'AlarmStatus',
    'SmartHomeMetrics', 'SmartHomeStats', 'DeviceMetrics'
]

