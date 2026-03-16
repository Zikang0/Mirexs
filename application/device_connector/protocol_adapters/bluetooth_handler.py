"""
蓝牙处理模块 - Mirexs协议适配器

提供蓝牙设备连接和管理功能，包括：
1. 蓝牙设备发现
2. 连接管理
3. 服务发现
4. 数据收发
5. 低功耗蓝牙(BLE)支持
6. 经典蓝牙支持
"""

import logging
import time
import uuid
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 尝试导入蓝牙库
try:
    import bluetooth
    import bluetooth.ble
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False
    logger.warning("PyBluez not available. Bluetooth functionality will be limited.")

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"

class BluetoothType(Enum):
    """蓝牙类型枚举"""
    CLASSIC = "classic"
    BLE = "ble"
    UNKNOWN = "unknown"

@dataclass
class BluetoothDevice:
    """蓝牙设备信息"""
    address: str
    name: Optional[str] = None
    type: BluetoothType = BluetoothType.UNKNOWN
    rssi: Optional[int] = None
    paired: bool = False
    connected: bool = False
    services: List[Dict[str, Any]] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    manufacturer_data: Dict[int, bytes] = field(default_factory=dict)
    service_uuids: List[str] = field(default_factory=list)

@dataclass
class BluetoothConfig:
    """蓝牙配置"""
    # 扫描配置
    scan_timeout: int = 10  # 秒
    scan_duration: int = 5  # 秒
    enable_classic: bool = True
    enable_ble: bool = True
    scan_filter_rssi: Optional[int] = None  # 只扫描RSSI大于此值的设备
    
    # 连接配置
    connect_timeout: int = 30  # 秒
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    reconnect_delay: int = 5  # 秒
    
    # 数据配置
    max_packet_size: int = 1024  # 字节
    receive_buffer_size: int = 4096
    send_timeout: int = 10  # 秒
    
    # 设备缓存
    cache_devices: bool = True
    cache_timeout: int = 3600  # 秒
    
    # 安全配置
    require_encryption: bool = False
    pin_code: Optional[str] = None
    bonding: bool = False

class BluetoothHandler:
    """
    蓝牙处理器
    
    负责蓝牙设备的发现、连接和数据传输，支持经典蓝牙和BLE。
    """
    
    def __init__(self, config: Optional[BluetoothConfig] = None):
        """
        初始化蓝牙处理器
        
        Args:
            config: 蓝牙配置
        """
        self.config = config or BluetoothConfig()
        
        # 设备管理
        self.discovered_devices: Dict[str, BluetoothDevice] = {}
        self.connected_devices: Dict[str, BluetoothDevice] = {}
        self.paired_devices: Dict[str, BluetoothDevice] = {}
        
        # 连接状态
        self.is_scanning = False
        self.current_connection: Optional[BluetoothDevice] = None
        self.connection_status = ConnectionStatus.DISCONNECTED
        
        # 重连管理
        self._reconnect_attempts = 0
        self._reconnect_timer: Optional[threading.Timer] = None
        
        # 数据接收
        self._receive_thread: Optional[threading.Thread] = None
        self._stop_receive = threading.Event()
        
        # 套接字
        self._sockets: Dict[str, Any] = {}  # address -> socket
        
        # 回调函数
        self.on_device_found: Optional[Callable[[BluetoothDevice], None]] = None
        self.on_device_connected: Optional[Callable[[BluetoothDevice], None]] = None
        self.on_device_disconnected: Optional[Callable[[BluetoothDevice], None]] = None
        self.on_data_received: Optional[Callable[[str, bytes], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        # 统计
        self.stats = {
            "scan_count": 0,
            "connect_count": 0,
            "disconnect_count": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "errors": 0
        }
        
        # 加载已配对的设备
        self._load_paired_devices()
        
        logger.info("BluetoothHandler initialized")
    
    def _load_paired_devices(self):
        """加载已配对的设备"""
        if not BLUETOOTH_AVAILABLE:
            return
        
        try:
            # 获取已配对设备列表
            paired = bluetooth.discover_devices(lookup_names=True, flush_cache=True)
            
            for addr, name in paired:
                device = BluetoothDevice(
                    address=addr,
                    name=name,
                    type=BluetoothType.CLASSIC,
                    paired=True
                )
                self.paired_devices[addr] = device
                logger.debug(f"Loaded paired device: {name} ({addr})")
            
            logger.info(f"Loaded {len(self.paired_devices)} paired devices")
            
        except Exception as e:
            logger.error(f"Error loading paired devices: {e}")
    
    def start_scan(self, duration: Optional[int] = None) -> bool:
        """
        开始扫描蓝牙设备
        
        Args:
            duration: 扫描持续时间（秒）
        
        Returns:
            是否成功启动扫描
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return False
        
        scan_duration = duration or self.config.scan_duration
        
        logger.info(f"Starting Bluetooth scan for {scan_duration} seconds")
        
        self.is_scanning = True
        self.stats["scan_count"] += 1
        
        def scan_thread():
            try:
                if not BLUETOOTH_AVAILABLE:
                    logger.error("Bluetooth not available")
                    self.is_scanning = False
                    return
                
                discovered = []
                
                # 扫描经典蓝牙设备
                if self.config.enable_classic:
                    classic_devices = bluetooth.discover_devices(
                        duration=scan_duration,
                        lookup_names=True,
                        flush_cache=True
                    )
                    discovered.extend(classic_devices)
                
                # 扫描BLE设备
                if self.config.enable_ble:
                    try:
                        ble_devices = bluetooth.ble.discover_devices(
                            timeout=scan_duration
                        )
                        discovered.extend([(d.address, d.name) for d in ble_devices])
                    except Exception as e:
                        logger.error(f"BLE scan error: {e}")
                
                # 处理发现的设备
                for addr, name in discovered:
                    if self.config.scan_filter_rssi:
                        # 这里需要获取RSSI，简化处理
                        pass
                    
                    device = BluetoothDevice(
                        address=addr,
                        name=name,
                        type=BluetoothType.CLASSIC,
                        last_seen=time.time()
                    )
                    
                    self.discovered_devices[addr] = device
                    
                    if self.on_device_found:
                        self.on_device_found(device)
                    
                    logger.debug(f"Device found: {name} ({addr})")
                
                logger.info(f"Scan completed, found {len(discovered)} devices")
                
            except Exception as e:
                logger.error(f"Scan error: {e}")
                self.stats["errors"] += 1
                if self.on_error:
                    self.on_error("scan", str(e))
            
            finally:
                self.is_scanning = False
        
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
        
        return True
    
    def stop_scan(self):
        """停止扫描"""
        self.is_scanning = False
        logger.info("Scan stopped")
    
    def connect(self, address: str, timeout: Optional[int] = None) -> bool:
        """
        连接蓝牙设备
        
        Args:
            address: 设备地址
            timeout: 连接超时（秒）
        
        Returns:
            是否成功连接
        """
        if self.connection_status == ConnectionStatus.CONNECTED:
            logger.warning(f"Already connected to {self.current_connection.address}")
            return False
        
        logger.info(f"Connecting to {address}...")
        
        self.connection_status = ConnectionStatus.CONNECTING
        connect_timeout = timeout or self.config.connect_timeout
        
        try:
            if not BLUETOOTH_AVAILABLE:
                raise Exception("Bluetooth not available")
            
            # 创建蓝牙套接字
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            sock.settimeout(connect_timeout)
            
            # 连接设备（使用默认端口1）
            sock.connect((address, 1))
            
            # 获取设备信息
            device_info = self.discovered_devices.get(address) or self.paired_devices.get(address)
            
            if device_info:
                device = device_info
            else:
                # 尝试获取设备名称
                try:
                    name = bluetooth.lookup_name(address, timeout=5)
                except:
                    name = None
                
                device = BluetoothDevice(
                    address=address,
                    name=name,
                    type=BluetoothType.CLASSIC,
                    connected=True
                )
            
            device.connected = True
            self.connected_devices[address] = device
            self.current_connection = device
            self._sockets[address] = sock
            
            self.connection_status = ConnectionStatus.CONNECTED
            self.stats["connect_count"] += 1
            self._reconnect_attempts = 0
            
            logger.info(f"Connected to {device.name or address}")
            
            # 启动接收线程
            self._start_receive_thread(address)
            
            if self.on_device_connected:
                self.on_device_connected(device)
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
            
            if self.on_error:
                self.on_error("connect", str(e))
            
            return False
    
    def disconnect(self, address: Optional[str] = None):
        """
        断开蓝牙设备连接
        
        Args:
            address: 设备地址，None表示断开当前连接
        """
        target = address or (self.current_connection.address if self.current_connection else None)
        
        if not target:
            logger.warning("No device to disconnect")
            return
        
        logger.info(f"Disconnecting from {target}...")
        
        self.connection_status = ConnectionStatus.DISCONNECTING
        
        try:
            if target in self._sockets:
                sock = self._sockets[target]
                sock.close()
                del self._sockets[target]
            
            if target in self.connected_devices:
                device = self.connected_devices[target]
                device.connected = False
                del self.connected_devices[target]
            
            if self.current_connection and self.current_connection.address == target:
                self.current_connection = None
            
            self.connection_status = ConnectionStatus.DISCONNECTED
            self.stats["disconnect_count"] += 1
            
            logger.info(f"Disconnected from {target}")
            
            if self.on_device_disconnected:
                self.on_device_disconnected(self.connected_devices.get(target))
            
            # 停止接收线程
            self._stop_receive.set()
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self.connection_status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
    
    def _start_receive_thread(self, address: str):
        """启动接收线程"""
        self._stop_receive.clear()
        
        def receive_loop():
            sock = self._sockets.get(address)
            if not sock:
                return
            
            while not self._stop_receive.is_set():
                try:
                    data = sock.recv(self.config.receive_buffer_size)
                    if data:
                        self.stats["bytes_received"] += len(data)
                        
                        if self.on_data_received:
                            self.on_data_received(address, data)
                        
                        logger.debug(f"Received {len(data)} bytes from {address}")
                    else:
                        # 连接关闭
                        break
                        
                except bluetooth.btcommon.BluetoothError as e:
                    if e.args[0] == 'timed out':
                        continue
                    else:
                        logger.error(f"Receive error: {e}")
                        break
                except Exception as e:
                    logger.error(f"Receive error: {e}")
                    break
            
            # 检查是否需要重连
            if (self.config.auto_reconnect and 
                self._reconnect_attempts < self.config.max_reconnect_attempts):
                self._schedule_reconnect(address)
        
        self._receive_thread = threading.Thread(target=receive_loop, daemon=True)
        self._receive_thread.start()
    
    def _schedule_reconnect(self, address: str):
        """调度重连"""
        self._reconnect_attempts += 1
        delay = self.config.reconnect_delay * self._reconnect_attempts
        
        logger.info(f"Scheduling reconnect to {address} in {delay}s (attempt {self._reconnect_attempts})")
        
        def reconnect():
            if self.connection_status != ConnectionStatus.CONNECTED:
                self.connect(address)
        
        self._reconnect_timer = threading.Timer(delay, reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
    
    def send_data(self, data: bytes, address: Optional[str] = None) -> bool:
        """
        发送数据到蓝牙设备
        
        Args:
            data: 要发送的数据
            address: 目标设备地址，None表示当前连接
        
        Returns:
            是否成功发送
        """
        target = address or (self.current_connection.address if self.current_connection else None)
        
        if not target:
            logger.warning("No device to send data")
            return False
        
        if target not in self._sockets:
            logger.warning(f"Device {target} not connected")
            return False
        
        try:
            sock = self._sockets[target]
            sock.settimeout(self.config.send_timeout)
            sent = sock.send(data)
            
            self.stats["bytes_sent"] += sent
            logger.debug(f"Sent {sent} bytes to {target}")
            
            return True
            
        except Exception as e:
            logger.error(f"Send error: {e}")
            self.stats["errors"] += 1
            return False
    
    def pair_device(self, address: str, pin: Optional[str] = None) -> bool:
        """
        配对蓝牙设备
        
        Args:
            address: 设备地址
            pin: PIN码
        
        Returns:
            是否成功配对
        """
        logger.info(f"Pairing with {address}...")
        
        try:
            # 这里简化处理，实际实现需要平台特定API
            pin_code = pin or self.config.pin_code or "0000"
            
            # 模拟配对过程
            if address in self.discovered_devices:
                device = self.discovered_devices[address]
                device.paired = True
                self.paired_devices[address] = device
                
                logger.info(f"Paired with {address}")
                return True
            else:
                logger.warning(f"Device {address} not found")
                return False
                
        except Exception as e:
            logger.error(f"Pairing error: {e}")
            return False
    
    def get_device_services(self, address: str) -> List[Dict[str, Any]]:
        """
        获取设备服务
        
        Args:
            address: 设备地址
        
        Returns:
            服务列表
        """
        services = []
        
        try:
            if not BLUETOOTH_AVAILABLE:
                return services
            
            # 查询服务
            service_matches = bluetooth.find_service(address=address)
            
            for service in service_matches:
                services.append({
                    "name": service.get("name", "Unknown"),
                    "host": service.get("host", address),
                    "protocol": service.get("protocol", "RFCOMM"),
                    "port": service.get("port", 1),
                    "service_classes": service.get("service-classes", []),
                    "profiles": service.get("profiles", []),
                    "description": service.get("description", "")
                })
            
            logger.debug(f"Found {len(services)} services for {address}")
            
        except Exception as e:
            logger.error(f"Error getting services: {e}")
        
        return services
    
    def get_connected_devices(self) -> List[BluetoothDevice]:
        """
        获取已连接的设备列表
        
        Returns:
            已连接设备列表
        """
        return list(self.connected_devices.values())
    
    def get_discovered_devices(self) -> List[BluetoothDevice]:
        """
        获取已发现的设备列表
        
        Returns:
            已发现设备列表
        """
        return list(self.discovered_devices.values())
    
    def get_paired_devices(self) -> List[BluetoothDevice]:
        """
        获取已配对的设备列表
        
        Returns:
            已配对设备列表
        """
        return list(self.paired_devices.values())
    
    def clear_discovered_devices(self):
        """清除发现的设备列表"""
        self.discovered_devices.clear()
        logger.info("Discovered devices cleared")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取蓝牙处理器状态
        
        Returns:
            状态字典
        """
        return {
            "available": BLUETOOTH_AVAILABLE,
            "is_scanning": self.is_scanning,
            "connection_status": self.connection_status.value,
            "current_connection": self.current_connection.address if self.current_connection else None,
            "devices": {
                "discovered": len(self.discovered_devices),
                "connected": len(self.connected_devices),
                "paired": len(self.paired_devices)
            },
            "config": {
                "enable_classic": self.config.enable_classic,
                "enable_ble": self.config.enable_ble,
                "auto_reconnect": self.config.auto_reconnect
            },
            "stats": self.stats,
            "reconnect_attempts": self._reconnect_attempts
        }
    
    def shutdown(self):
        """关闭蓝牙处理器"""
        logger.info("Shutting down BluetoothHandler...")
        
        # 停止扫描
        self.stop_scan()
        
        # 断开所有连接
        for address in list(self.connected_devices.keys()):
            self.disconnect(address)
        
        # 取消重连定时器
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
        
        # 停止接收线程
        self._stop_receive.set()
        
        # 关闭所有套接字
        for sock in self._sockets.values():
            try:
                sock.close()
            except:
                pass
        
        self._sockets.clear()
        
        logger.info("BluetoothHandler shutdown completed")

# 单例模式实现
_bluetooth_handler_instance: Optional[BluetoothHandler] = None

def get_bluetooth_handler(config: Optional[BluetoothConfig] = None) -> BluetoothHandler:
    """
    获取蓝牙处理器单例
    
    Args:
        config: 蓝牙配置
    
    Returns:
        蓝牙处理器实例
    """
    global _bluetooth_handler_instance
    if _bluetooth_handler_instance is None:
        _bluetooth_handler_instance = BluetoothHandler(config)
    return _bluetooth_handler_instance

