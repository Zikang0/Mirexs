"""
USB处理模块 - Mirexs协议适配器

提供USB设备连接和管理功能，包括：
1. USB设备发现
2. 设备连接管理
3. 数据传输
4. 端点管理
5. 热插拔检测
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 尝试导入USB库
try:
    import usb.core
    import usb.util
    import usb.backend.libusb1
    PYLIBUSB_AVAILABLE = True
except ImportError:
    PYLIBUSB_AVAILABLE = False
    logger.warning("PyUSB not available. USB functionality will be limited.")

class USBClass(Enum):
    """USB设备类枚举"""
    AUDIO = 0x01
    COMMUNICATIONS = 0x02
    HID = 0x03
    PHYSICAL = 0x05
    IMAGE = 0x06
    PRINTER = 0x07
    MASS_STORAGE = 0x08
    HUB = 0x09
    CDC_DATA = 0x0A
    SMART_CARD = 0x0B
    CONTENT_SECURITY = 0x0D
    VIDEO = 0x0E
    PERSONAL_HEALTHCARE = 0x0F
    AUDIO_VIDEO = 0x10
    BILLBOARD = 0x11
    USB_TYPE_C_BRIDGE = 0x12
    DIAGNOSTIC = 0xDC
    WIRELESS = 0xE0
    MISCELLANEOUS = 0xEF
    APPLICATION = 0xFE
    VENDOR = 0xFF

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"

class TransferType(Enum):
    """传输类型枚举"""
    CONTROL = "control"
    BULK = "bulk"
    INTERRUPT = "interrupt"
    ISOCHRONOUS = "isochronous"

@dataclass
class USBEndpoint:
    """USB端点信息"""
    address: int
    number: int
    direction: str  # "in" or "out"
    type: TransferType
    max_packet_size: int
    interval: int

@dataclass
class USBInterface:
    """USB接口信息"""
    number: int
    class_code: int
    subclass: int
    protocol: int
    endpoints: List[USBEndpoint] = field(default_factory=list)

@dataclass
class USBConfiguration:
    """USB配置信息"""
    value: int
    interfaces: List[USBInterface] = field(default_factory=list)
    max_power: int  # mA

@dataclass
class USBDevice:
    """USB设备信息"""
    vid: int  # Vendor ID
    pid: int  # Product ID
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    serial_number: Optional[str] = None
    bus: int = 0
    address: int = 0
    speed: Optional[str] = None
    configurations: List[USBConfiguration] = field(default_factory=list)
    connected: bool = False
    last_seen: float = field(default_factory=time.time)

@dataclass
class USBConfig:
    """USB配置"""
    # 扫描配置
    scan_interval: int = 5  # 秒
    auto_scan: bool = True
    
    # 连接配置
    connect_timeout: int = 10  # 秒
    auto_reconnect: bool = False
    
    # 传输配置
    bulk_timeout: int = 1000  # 毫秒
    control_timeout: int = 1000  # 毫秒
    max_transfer_size: int = 16384  # 字节
    
    # 过滤器
    filter_vid: Optional[int] = None
    filter_pid: Optional[int] = None
    filter_class: Optional[int] = None

class USBHandler:
    """
    USB处理器
    
    负责USB设备的发现、连接和数据传输。
    """
    
    def __init__(self, config: Optional[USBConfig] = None):
        """
        初始化USB处理器
        
        Args:
            config: USB配置
        """
        self.config = config or USBConfig()
        
        # 设备管理
        self.devices: Dict[str, USBDevice] = {}  # key: f"{vid}:{pid}:{bus}:{address}"
        self.connected_devices: Dict[str, USBDevice] = {}
        
        # 连接状态
        self.is_scanning = False
        self.current_device: Optional[USBDevice] = None
        self.connection_status = ConnectionStatus.DISCONNECTED
        
        # USB设备句柄
        self._handles: Dict[str, Any] = {}  # key -> usb.core.Device
        
        # 扫描线程
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_scan = threading.Event()
        
        # 热插拔检测
        self._hotplug_thread: Optional[threading.Thread] = None
        
        # 回调函数
        self.on_device_found: Optional[Callable[[USBDevice], None]] = None
        self.on_device_connected: Optional[Callable[[USBDevice], None]] = None
        self.on_device_disconnected: Optional[Callable[[USBDevice], None]] = None
        self.on_data_received: Optional[Callable[[bytes], None]] = None
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
        
        # 启动自动扫描
        if self.config.auto_scan:
            self._start_auto_scan()
        
        logger.info("USBHandler initialized")
    
    def _start_auto_scan(self):
        """启动自动扫描"""
        def scan_loop():
            while not self._stop_scan.is_set():
                self.scan()
                self._stop_scan.wait(self.config.scan_interval)
        
        self._scan_thread = threading.Thread(target=scan_loop, daemon=True)
        self._scan_thread.start()
        logger.debug("Auto scan started")
    
    def scan(self) -> List[USBDevice]:
        """
        扫描USB设备
        
        Returns:
            发现的设备列表
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return list(self.devices.values())
        
        if not PYLIBUSB_AVAILABLE:
            logger.error("PyUSB not available")
            return []
        
        logger.info("Scanning for USB devices...")
        
        self.is_scanning = True
        self.stats["scan_count"] += 1
        
        devices = []
        
        try:
            # 查找所有设备
            found_devices = usb.core.find(find_all=True)
            
            for dev in found_devices:
                try:
                    vid = dev.idVendor
                    pid = dev.idProduct
                    
                    # 应用过滤器
                    if self.config.filter_vid and vid != self.config.filter_vid:
                        continue
                    if self.config.filter_pid and pid != self.config.filter_pid:
                        continue
                    
                    # 获取设备信息
                    try:
                        manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else None
                    except:
                        manufacturer = None
                    
                    try:
                        product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else None
                    except:
                        product = None
                    
                    try:
                        serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else None
                    except:
                        serial = None
                    
                    # 获取配置信息
                    configurations = []
                    for cfg in dev:
                        config = USBConfiguration(
                            value=cfg.bConfigurationValue,
                            max_power=cfg.bMaxPower * 2  # 单位: 2mA
                        )
                        
                        for intf in cfg:
                            interface = USBInterface(
                                number=intf.bInterfaceNumber,
                                class_code=intf.bInterfaceClass,
                                subclass=intf.bInterfaceSubClass,
                                protocol=intf.bInterfaceProtocol
                            )
                            
                            for ep in intf:
                                direction = "in" if (ep.bEndpointAddress & 0x80) else "out"
                                
                                if ep.bmAttributes & 0x03 == 0:
                                    xfer_type = TransferType.CONTROL
                                elif ep.bmAttributes & 0x03 == 1:
                                    xfer_type = TransferType.ISOCHRONOUS
                                elif ep.bmAttributes & 0x03 == 2:
                                    xfer_type = TransferType.BULK
                                else:
                                    xfer_type = TransferType.INTERRUPT
                                
                                endpoint = USBEndpoint(
                                    address=ep.bEndpointAddress,
                                    number=ep.bEndpointAddress & 0x0F,
                                    direction=direction,
                                    type=xfer_type,
                                    max_packet_size=ep.wMaxPacketSize,
                                    interval=ep.bInterval
                                )
                                interface.endpoints.append(endpoint)
                            
                            config.interfaces.append(interface)
                        
                        configurations.append(config)
                    
                    # 创建设备对象
                    device = USBDevice(
                        vid=vid,
                        pid=pid,
                        manufacturer=manufacturer,
                        product=product,
                        serial_number=serial,
                        bus=dev.bus,
                        address=dev.address,
                        speed=dev.speed,
                        configurations=configurations,
                        connected=True,
                        last_seen=time.time()
                    )
                    
                    device_key = f"{vid:04x}:{pid:04x}:{dev.bus}:{dev.address}"
                    self.devices[device_key] = device
                    devices.append(device)
                    
                    if self.on_device_found:
                        self.on_device_found(device)
                    
                    logger.debug(f"USB device found: {vid:04x}:{pid:04x} - {product}")
                    
                except Exception as e:
                    logger.error(f"Error processing USB device: {e}")
            
            logger.info(f"Scan completed, found {len(devices)} devices")
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.stats["errors"] += 1
        
        finally:
            self.is_scanning = False
        
        return devices
    
    def connect(self, device_key: str, interface: int = 0) -> bool:
        """
        连接USB设备
        
        Args:
            device_key: 设备键
            interface: 接口号
        
        Returns:
            是否成功连接
        """
        if self.connection_status == ConnectionStatus.CONNECTED:
            logger.warning(f"Already connected to {self.current_device.product}")
            return False
        
        if device_key not in self.devices:
            logger.warning(f"Device {device_key} not found")
            return False
        
        if not PYLIBUSB_AVAILABLE:
            logger.error("PyUSB not available")
            return False
        
        logger.info(f"Connecting to USB device {device_key}...")
        
        self.connection_status = ConnectionStatus.CONNECTING
        
        try:
            device_info = self.devices[device_key]
            
            # 查找设备
            dev = usb.core.find(
                idVendor=device_info.vid,
                idProduct=device_info.pid,
                bus=device_info.bus,
                address=device_info.address
            )
            
            if dev is None:
                raise Exception("Device not found")
            
            # 设置配置
            if dev.is_kernel_driver_active(interface):
                dev.detach_kernel_driver(interface)
            
            dev.set_configuration()
            
            # 获取端点
            cfg = dev.get_active_configuration()
            intf = cfg[(interface, 0)]
            
            # 查找端点
            ep_in = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            ep_out = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
            )
            
            # 保存句柄
            self._handles[device_key] = {
                "device": dev,
                "ep_in": ep_in,
                "ep_out": ep_out,
                "interface": interface
            }
            
            device_info.connected = True
            self.connected_devices[device_key] = device_info
            self.current_device = device_info
            self.connection_status = ConnectionStatus.CONNECTED
            self.stats["connect_count"] += 1
            
            logger.info(f"Connected to {device_info.product}")
            
            if self.on_device_connected:
                self.on_device_connected(device_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
            return False
    
    def disconnect(self, device_key: Optional[str] = None):
        """
        断开USB设备连接
        
        Args:
            device_key: 设备键，None表示断开当前连接
        """
        target = device_key or (self.current_device and self._get_device_key(self.current_device))
        
        if not target:
            logger.warning("No device to disconnect")
            return
        
        logger.info(f"Disconnecting USB device {target}...")
        
        self.connection_status = ConnectionStatus.DISCONNECTING
        
        try:
            if target in self._handles:
                handle = self._handles[target]
                dev = handle["device"]
                interface = handle["interface"]
                
                # 重新附加内核驱动
                try:
                    if dev.is_kernel_driver_active(interface):
                        dev.attach_kernel_driver(interface)
                except:
                    pass
                
                # 释放设备
                usb.util.dispose_resources(dev)
                
                del self._handles[target]
            
            if target in self.connected_devices:
                device = self.connected_devices[target]
                device.connected = False
                del self.connected_devices[target]
            
            if self.current_device and self._get_device_key(self.current_device) == target:
                self.current_device = None
            
            self.connection_status = ConnectionStatus.DISCONNECTED
            self.stats["disconnect_count"] += 1
            
            logger.info("USB device disconnected")
            
            if self.on_device_disconnected:
                self.on_device_disconnected(self.connected_devices.get(target))
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self.connection_status = ConnectionStatus.ERROR
    
    def _get_device_key(self, device: USBDevice) -> str:
        """获取设备键"""
        return f"{device.vid:04x}:{device.pid:04x}:{device.bus}:{device.address}"
    
    def bulk_write(self, data: bytes, device_key: Optional[str] = None) -> int:
        """
        批量写入数据
        
        Args:
            data: 要写入的数据
            device_key: 设备键
        
        Returns:
            写入的字节数
        """
        target = device_key or (self.current_device and self._get_device_key(self.current_device))
        
        if not target or target not in self._handles:
            logger.warning("No device connected")
            return 0
        
        try:
            handle = self._handles[target]
            ep_out = handle["ep_out"]
            
            if not ep_out:
                logger.warning("No OUT endpoint available")
                return 0
            
            written = ep_out.write(data, self.config.bulk_timeout)
            self.stats["bytes_sent"] += written
            
            logger.debug(f"Bulk write: {written} bytes")
            return written
            
        except Exception as e:
            logger.error(f"Bulk write error: {e}")
            return 0
    
    def bulk_read(self, size: Optional[int] = None, device_key: Optional[str] = None) -> Optional[bytes]:
        """
        批量读取数据
        
        Args:
            size: 读取大小，None表示使用端点最大包大小
            device_key: 设备键
        
        Returns:
            读取的数据
        """
        target = device_key or (self.current_device and self._get_device_key(self.current_device))
        
        if not target or target not in self._handles:
            logger.warning("No device connected")
            return None
        
        try:
            handle = self._handles[target]
            ep_in = handle["ep_in"]
            
            if not ep_in:
                logger.warning("No IN endpoint available")
                return None
            
            read_size = size or ep_in.wMaxPacketSize
            data = ep_in.read(read_size, self.config.bulk_timeout)
            
            if data:
                self.stats["bytes_received"] += len(data)
                logger.debug(f"Bulk read: {len(data)} bytes")
                return bytes(data)
            
            return None
            
        except usb.core.USBError as e:
            if e.errno == 110:  # 超时
                return None
            logger.error(f"Bulk read error: {e}")
            return None
        except Exception as e:
            logger.error(f"Bulk read error: {e}")
            return None
    
    def control_transfer(self, bmRequestType: int, bRequest: int, 
                        wValue: int, wIndex: int, 
                        data_or_wLength: Any) -> Optional[bytes]:
        """
        控制传输
        
        Args:
            bmRequestType: 请求类型
            bRequest: 请求
            wValue: 值
            wIndex: 索引
            data_or_wLength: 数据或长度
        
        Returns:
            读取的数据
        """
        if not self.current_device:
            logger.warning("No device connected")
            return None
        
        target = self._get_device_key(self.current_device)
        
        if target not in self._handles:
            logger.warning("Device handle not found")
            return None
        
        try:
            handle = self._handles[target]
            dev = handle["device"]
            
            result = dev.ctrl_transfer(
                bmRequestType,
                bRequest,
                wValue,
                wIndex,
                data_or_wLength,
                timeout=self.config.control_timeout
            )
            
            if isinstance(result, bytes):
                self.stats["bytes_received"] += len(result)
            elif isinstance(result, int):
                self.stats["bytes_sent"] += result
            
            return result
            
        except Exception as e:
            logger.error(f"Control transfer error: {e}")
            return None
    
    def get_devices(self) -> List[USBDevice]:
        """
        获取设备列表
        
        Returns:
            设备列表
        """
        return list(self.devices.values())
    
    def get_connected_devices(self) -> List[USBDevice]:
        """
        获取已连接的设备列表
        
        Returns:
            已连接设备列表
        """
        return list(self.connected_devices.values())
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取USB处理器状态
        
        Returns:
            状态字典
        """
        return {
            "available": PYLIBUSB_AVAILABLE,
            "is_scanning": self.is_scanning,
            "connection_status": self.connection_status.value,
            "current_device": self.current_device.product if self.current_device else None,
            "devices": {
                "total": len(self.devices),
                "connected": len(self.connected_devices)
            },
            "config": {
                "auto_scan": self.config.auto_scan,
                "auto_reconnect": self.config.auto_reconnect
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭USB处理器"""
        logger.info("Shutting down USBHandler...")
        
        # 停止扫描
        self._stop_scan.set()
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=2)
        
        # 断开所有连接
        for device_key in list(self.connected_devices.keys()):
            self.disconnect(device_key)
        
        logger.info("USBHandler shutdown completed")

# 单例模式实现
_usb_handler_instance: Optional[USBHandler] = None

def get_usb_handler(config: Optional[USBConfig] = None) -> USBHandler:
    """
    获取USB处理器单例
    
    Args:
        config: USB配置
    
    Returns:
        USB处理器实例
    """
    global _usb_handler_instance
    if _usb_handler_instance is None:
        _usb_handler_instance = USBHandler(config)
    return _usb_handler_instance

