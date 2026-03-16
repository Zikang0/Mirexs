"""
IoT设备管理模块 - Mirexs智能家居集成

提供IoT设备管理功能，包括：
1. 设备发现
2. 设备注册
3. 设备控制
4. 状态监控
5. 设备分组
6. 协议适配
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """设备类型枚举"""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    CAMERA = "camera"
    COVER = "cover"  # 窗帘、卷帘等
    FAN = "fan"
    AC = "air_conditioner"
    VACUUM = "vacuum"
    SPEAKER = "speaker"
    TV = "tv"
    PLUG = "plug"
    GATEWAY = "gateway"
    OTHER = "other"

class DeviceProtocol(Enum):
    """设备协议枚举"""
    ZIGBEE = "zigbee"
    Z_WAVE = "z_wave"
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    MATTER = "matter"
    THREAD = "thread"
    RF = "rf"
    INFRARED = "infrared"
    CUSTOM = "custom"

class DeviceStatus(Enum):
    """设备状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    UPDATING = "updating"
    UNKNOWN = "unknown"

@dataclass
class IoTDevice:
    """IoT设备"""
    id: str
    name: str
    type: DeviceType
    protocol: DeviceProtocol
    manufacturer: str
    model: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    room: Optional[str] = None
    zone: Optional[str] = None
    
    # 连接信息
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    signal_strength: Optional[int] = None  # dBm
    battery_level: Optional[int] = None  # 百分比
    
    # 功能
    capabilities: List[str] = field(default_factory=list)
    states: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    paired_at: Optional[float] = None
    last_seen: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeviceGroup:
    """设备分组"""
    id: str
    name: str
    device_ids: List[str]
    room: Optional[str] = None
    type: Optional[str] = None
    created_at: float = field(default_factory=time.time)

@dataclass
class DeviceCommand:
    """设备命令"""
    id: str
    device_id: str
    command: str
    params: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"  # pending, sent, success, failed
    result: Optional[Any] = None

@dataclass
class IoTDeviceConfig:
    """IoT设备管理配置"""
    # 发现配置
    auto_discovery: bool = True
    discovery_interval: int = 300  # 秒
    
    # 监控配置
    monitor_interval: int = 60  # 秒
    offline_timeout: int = 600  # 秒
    
    # 重连配置
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    
    # 存储配置
    save_devices: bool = True
    devices_file: str = "iot_devices.json"

class IoTDeviceManager:
    """
    IoT设备管理器
    
    负责智能家居设备的管理和控制。
    """
    
    def __init__(self, config: Optional[IoTDeviceConfig] = None):
        """
        初始化IoT设备管理器
        
        Args:
            config: 设备管理配置
        """
        self.config = config or IoTDeviceConfig()
        
        # 设备存储
        self.devices: Dict[str, IoTDevice] = {}
        self.groups: Dict[str, DeviceGroup] = {}
        self.commands: Dict[str, DeviceCommand] = {}
        
        # 设备类型索引
        self.devices_by_type: Dict[DeviceType, List[str]] = {}
        self.devices_by_room: Dict[str, List[str]] = {}
        self.devices_by_protocol: Dict[DeviceProtocol, List[str]] = {}
        
        # 发现线程
        self._discovery_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_discovery = threading.Event()
        
        # 回调函数
        self.on_device_discovered: Optional[Callable[[IoTDevice], None]] = None
        self.on_device_added: Optional[Callable[[IoTDevice], None]] = None
        self.on_device_updated: Optional[Callable[[IoTDevice], None]] = None
        self.on_device_removed: Optional[Callable[[str], None]] = None
        self.on_device_status_changed: Optional[Callable[[str, DeviceStatus, DeviceStatus], None]] = None
        self.on_command_result: Optional[Callable[[DeviceCommand], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "total_devices": 0,
            "online_devices": 0,
            "offline_devices": 0,
            "commands_sent": 0,
            "commands_succeeded": 0,
            "commands_failed": 0,
            "discoveries": 0,
            "errors": 0
        }
        
        # 启动自动发现
        if self.config.auto_discovery:
            self._start_discovery()
        
        # 启动状态监控
        self._start_monitoring()
        
        logger.info("IoTDeviceManager initialized")
    
    def _start_discovery(self):
        """启动设备发现"""
        def discovery_loop():
            while not self._stop_discovery.is_set():
                try:
                    self.discover_devices()
                    self._stop_discovery.wait(self.config.discovery_interval)
                except Exception as e:
                    logger.error(f"Discovery error: {e}")
                    self.stats["errors"] += 1
        
        self._discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
        self._discovery_thread.start()
        logger.debug("Device discovery started")
    
    def _start_monitoring(self):
        """启动状态监控"""
        def monitor_loop():
            while not self._stop_discovery.is_set():
                try:
                    self._update_device_status()
                    self._stop_discovery.wait(self.config.monitor_interval)
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    self.stats["errors"] += 1
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("Device monitoring started")
    
    def _update_device_status(self):
        """更新设备状态"""
        current_time = time.time()
        
        for device_id, device in self.devices.items():
            # 检查是否离线
            if device.last_seen:
                if current_time - device.last_seen > self.config.offline_timeout:
                    if device.status != DeviceStatus.OFFLINE:
                        self._set_device_status(device_id, DeviceStatus.OFFLINE)
    
    def _set_device_status(self, device_id: str, new_status: DeviceStatus):
        """设置设备状态"""
        if device_id not in self.devices:
            return
        
        device = self.devices[device_id]
        old_status = device.status
        
        if old_status != new_status:
            device.status = new_status
            
            # 更新统计
            if new_status == DeviceStatus.ONLINE:
                self.stats["online_devices"] += 1
                self.stats["offline_devices"] -= 1
            elif new_status == DeviceStatus.OFFLINE:
                self.stats["online_devices"] -= 1
                self.stats["offline_devices"] += 1
            
            logger.info(f"Device {device.name} status changed: {old_status.value} -> {new_status.value}")
            
            if self.on_device_status_changed:
                self.on_device_status_changed(device_id, old_status, new_status)
    
    def discover_devices(self) -> List[IoTDevice]:
        """
        发现新设备
        
        Returns:
            发现的设备列表
        """
        logger.info("Discovering IoT devices...")
        
        self.stats["discoveries"] += 1
        
        discovered = []
        
        # 实际实现中会通过不同协议发现设备
        # 这里返回模拟数据
        mock_devices = self._mock_discover_devices()
        
        for device_info in mock_devices:
            device = self._create_device_from_info(device_info)
            
            if device.id not in self.devices:
                self.add_device(device)
                discovered.append(device)
                
                if self.on_device_discovered:
                    self.on_device_discovered(device)
        
        logger.info(f"Discovered {len(discovered)} new devices")
        
        return discovered
    
    def _mock_discover_devices(self) -> List[Dict[str, Any]]:
        """模拟设备发现"""
        return [
            {
                "id": "light_1",
                "name": "Living Room Light",
                "type": DeviceType.LIGHT,
                "protocol": DeviceProtocol.ZIGBEE,
                "manufacturer": "Philips",
                "model": "Hue White",
                "capabilities": ["on_off", "brightness", "color"]
            },
            {
                "id": "sensor_1",
                "name": "Temperature Sensor",
                "type": DeviceType.SENSOR,
                "protocol": DeviceProtocol.Z_WAVE,
                "manufacturer": "Aeotec",
                "model": "MultiSensor 6",
                "capabilities": ["temperature", "humidity", "motion"]
            },
            {
                "id": "plug_1",
                "name": "Smart Plug",
                "type": DeviceType.PLUG,
                "protocol": DeviceProtocol.WIFI,
                "manufacturer": "TP-Link",
                "model": "HS110",
                "capabilities": ["on_off", "power_meter"]
            }
        ]
    
    def _create_device_from_info(self, info: Dict[str, Any]) -> IoTDevice:
        """从信息创建设备"""
        return IoTDevice(
            id=info["id"],
            name=info["name"],
            type=info["type"],
            protocol=info["protocol"],
            manufacturer=info["manufacturer"],
            model=info["model"],
            capabilities=info.get("capabilities", []),
            last_seen=time.time()
        )
    
    def add_device(self, device: IoTDevice) -> bool:
        """
        添加设备
        
        Args:
            device: 设备对象
        
        Returns:
            是否成功
        """
        if device.id in self.devices:
            logger.warning(f"Device {device.id} already exists")
            return False
        
        self.devices[device.id] = device
        self.stats["total_devices"] += 1
        
        # 更新索引
        if device.type not in self.devices_by_type:
            self.devices_by_type[device.type] = []
        self.devices_by_type[device.type].append(device.id)
        
        if device.protocol not in self.devices_by_protocol:
            self.devices_by_protocol[device.protocol] = []
        self.devices_by_protocol[device.protocol].append(device.id)
        
        if device.room:
            if device.room not in self.devices_by_room:
                self.devices_by_room[device.room] = []
            self.devices_by_room[device.room].append(device.id)
        
        logger.info(f"Device added: {device.name} ({device.id})")
        
        if self.on_device_added:
            self.on_device_added(device)
        
        return True
    
    def remove_device(self, device_id: str) -> bool:
        """
        移除设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否成功
        """
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        
        # 从索引中移除
        if device.type in self.devices_by_type:
            if device_id in self.devices_by_type[device.type]:
                self.devices_by_type[device.type].remove(device_id)
        
        if device.protocol in self.devices_by_protocol:
            if device_id in self.devices_by_protocol[device.protocol]:
                self.devices_by_protocol[device.protocol].remove(device_id)
        
        if device.room and device.room in self.devices_by_room:
            if device_id in self.devices_by_room[device.room]:
                self.devices_by_room[device.room].remove(device_id)
        
        # 从设备存储中移除
        del self.devices[device_id]
        self.stats["total_devices"] -= 1
        
        if device.status == DeviceStatus.ONLINE:
            self.stats["online_devices"] -= 1
        elif device.status == DeviceStatus.OFFLINE:
            self.stats["offline_devices"] -= 1
        
        logger.info(f"Device removed: {device.name} ({device_id})")
        
        if self.on_device_removed:
            self.on_device_removed(device_id)
        
        return True
    
    def update_device(self, device_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新设备信息
        
        Args:
            device_id: 设备ID
            updates: 更新内容
        
        Returns:
            是否成功
        """
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        
        # 更新字段
        for key, value in updates.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.last_seen = time.time()
        
        # 如果收到在线信号，更新状态
        if "status" in updates and updates["status"] == DeviceStatus.ONLINE.value:
            self._set_device_status(device_id, DeviceStatus.ONLINE)
        
        logger.debug(f"Device updated: {device_id}")
        
        if self.on_device_updated:
            self.on_device_updated(device)
        
        return True
    
    def send_command(self, device_id: str, command: str, 
                    params: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        发送设备命令
        
        Args:
            device_id: 设备ID
            command: 命令名称
            params: 命令参数
        
        Returns:
            命令ID
        """
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return None
        
        device = self.devices[device_id]
        
        if device.status != DeviceStatus.ONLINE:
            logger.warning(f"Device {device.name} is offline")
            return None
        
        command_id = str(uuid.uuid4())
        
        cmd = DeviceCommand(
            id=command_id,
            device_id=device_id,
            command=command,
            params=params or {}
        )
        
        self.commands[command_id] = cmd
        self.stats["commands_sent"] += 1
        
        logger.info(f"Sending command {command} to {device.name}")
        
        # 实际实现中会发送到设备
        # 这里模拟命令执行
        self._execute_command(cmd)
        
        return command_id
    
    def send_group_command(self, group_id: str, command: str,
                          params: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        发送组命令
        
        Args:
            group_id: 组ID
            command: 命令名称
            params: 命令参数
        
        Returns:
            命令ID列表
        """
        if group_id not in self.groups:
            logger.warning(f"Group {group_id} not found")
            return []
        
        group = self.groups[group_id]
        command_ids = []
        
        for device_id in group.device_ids:
            cmd_id = self.send_command(device_id, command, params)
            if cmd_id:
                command_ids.append(cmd_id)
        
        return command_ids
    
    def _execute_command(self, command: DeviceCommand):
        """执行命令（模拟）"""
        import random
        
        # 模拟命令执行
        time.sleep(random.uniform(0.1, 0.5))
        
        # 90%成功率
        success = random.random() < 0.9
        
        command.status = "success" if success else "failed"
        command.result = {"success": success}
        
        if success:
            self.stats["commands_succeeded"] += 1
        else:
            self.stats["commands_failed"] += 1
        
        if self.on_command_result:
            self.on_command_result(command)
        
        logger.debug(f"Command {command.id} {command.status}")
    
    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """
        获取设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            设备对象
        """
        return self.devices.get(device_id)
    
    def get_devices(self, device_type: Optional[DeviceType] = None,
                   room: Optional[str] = None,
                   protocol: Optional[DeviceProtocol] = None) -> List[IoTDevice]:
        """
        获取设备列表
        
        Args:
            device_type: 设备类型
            room: 房间
            protocol: 协议
        
        Returns:
            设备列表
        """
        devices = list(self.devices.values())
        
        if device_type:
            devices = [d for d in devices if d.type == device_type]
        
        if room:
            devices = [d for d in devices if d.room == room]
        
        if protocol:
            devices = [d for d in devices if d.protocol == protocol]
        
        return devices
    
    def create_group(self, name: str, device_ids: List[str],
                    room: Optional[str] = None) -> str:
        """
        创建设备组
        
        Args:
            name: 组名称
            device_ids: 设备ID列表
            room: 房间
        
        Returns:
            组ID
        """
        group_id = str(uuid.uuid4())
        
        group = DeviceGroup(
            id=group_id,
            name=name,
            device_ids=device_ids,
            room=room
        )
        
        self.groups[group_id] = group
        
        logger.info(f"Group created: {name} ({group_id}) with {len(device_ids)} devices")
        
        return group_id
    
    def delete_group(self, group_id: str) -> bool:
        """
        删除设备组
        
        Args:
            group_id: 组ID
        
        Returns:
            是否成功
        """
        if group_id not in self.groups:
            logger.warning(f"Group {group_id} not found")
            return False
        
        del self.groups[group_id]
        logger.info(f"Group deleted: {group_id}")
        
        return True
    
    def get_command_result(self, command_id: str) -> Optional[DeviceCommand]:
        """
        获取命令结果
        
        Args:
            command_id: 命令ID
        
        Returns:
            命令对象
        """
        return self.commands.get(command_id)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取设备管理器状态
        
        Returns:
            状态字典
        """
        return {
            "devices": {
                "total": self.stats["total_devices"],
                "online": self.stats["online_devices"],
                "offline": self.stats["offline_devices"],
                "by_type": {t.value: len(ids) for t, ids in self.devices_by_type.items()},
                "by_room": {r: len(ids) for r, ids in self.devices_by_room.items()}
            },
            "groups": len(self.groups),
            "commands": {
                "total": self.stats["commands_sent"],
                "succeeded": self.stats["commands_succeeded"],
                "failed": self.stats["commands_failed"]
            },
            "stats": self.stats,
            "discovery_running": self._discovery_thread is not None and self._discovery_thread.is_alive()
        }
    
    def shutdown(self):
        """关闭设备管理器"""
        logger.info("Shutting down IoTDeviceManager...")
        
        self._stop_discovery.set()
        
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=2)
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        self.devices.clear()
        self.groups.clear()
        self.commands.clear()
        self.devices_by_type.clear()
        self.devices_by_room.clear()
        self.devices_by_protocol.clear()
        
        logger.info("IoTDeviceManager shutdown completed")

# 单例模式实现
_iot_device_manager_instance: Optional[IoTDeviceManager] = None

def get_iot_device_manager(config: Optional[IoTDeviceConfig] = None) -> IoTDeviceManager:
    """
    获取IoT设备管理器单例
    
    Args:
        config: 设备管理配置
    
    Returns:
        IoT设备管理器实例
    """
    global _iot_device_manager_instance
    if _iot_device_manager_instance is None:
        _iot_device_manager_instance = IoTDeviceManager(config)
    return _iot_device_manager_instance

