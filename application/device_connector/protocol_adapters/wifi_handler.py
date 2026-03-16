"""
WiFi处理模块 - Mirexs协议适配器

提供WiFi设备连接和管理功能，包括：
1. WiFi网络扫描
2. 连接管理
3. 网络配置
4. 信号强度监测
5. 热点创建
6. WiFi直连
"""

import logging
import time
import threading
import subprocess
import re
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import socket
import netifaces

logger = logging.getLogger(__name__)

class WiFiSecurity(Enum):
    """WiFi安全类型枚举"""
    NONE = "none"
    WEP = "wep"
    WPA = "wpa"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    UNKNOWN = "unknown"

class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"

@dataclass
class WiFiNetwork:
    """WiFi网络信息"""
    ssid: str
    bssid: Optional[str] = None
    security: WiFiSecurity = WiFiSecurity.UNKNOWN
    rssi: Optional[int] = None
    frequency: Optional[int] = None
    channel: Optional[int] = None
    connected: bool = False
    saved: bool = False
    auto_connect: bool = False
    last_seen: float = field(default_factory=time.time)

@dataclass
class WiFiConfig:
    """WiFi配置"""
    # 扫描配置
    scan_interval: int = 30  # 秒
    auto_scan: bool = True
    
    # 连接配置
    connect_timeout: int = 30  # 秒
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 3
    
    # 热点配置
    hotspot_enabled: bool = False
    hotspot_ssid: str = "Mirexs_Hotspot"
    hotspot_password: Optional[str] = None
    hotspot_channel: int = 6
    
    # IP配置
    use_dhcp: bool = True
    static_ip: Optional[str] = None
    static_gateway: Optional[str] = None
    static_dns: List[str] = field(default_factory=list)
    
    # 网络配置
    preferred_networks: List[str] = field(default_factory=list)
    auto_join_open: bool = False
    power_save: bool = True

class WiFiHandler:
    """
    WiFi处理器
    
    负责WiFi网络的扫描、连接和管理。
    """
    
    def __init__(self, config: Optional[WiFiConfig] = None):
        """
        初始化WiFi处理器
        
        Args:
            config: WiFi配置
        """
        self.config = config or WiFiConfig()
        
        # 网络管理
        self.available_networks: Dict[str, WiFiNetwork] = {}
        self.saved_networks: Dict[str, WiFiNetwork] = {}
        self.current_network: Optional[WiFiNetwork] = None
        
        # 连接状态
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.is_scanning = False
        self.hotspot_active = False
        
        # 重连管理
        self._reconnect_attempts = 0
        self._reconnect_timer: Optional[threading.Timer] = None
        
        # 扫描线程
        self._scan_thread: Optional[threading.Thread] = None
        self._stop_scan = threading.Event()
        
        # 网络接口
        self.interface: Optional[str] = self._get_wifi_interface()
        
        # 回调函数
        self.on_network_found: Optional[Callable[[WiFiNetwork], None]] = None
        self.on_network_connected: Optional[Callable[[WiFiNetwork], None]] = None
        self.on_network_disconnected: Optional[Callable[[WiFiNetwork], None]] = None
        self.on_signal_changed: Optional[Callable[[int], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        # 统计
        self.stats = {
            "scan_count": 0,
            "connect_count": 0,
            "disconnect_count": 0,
            "signal_samples": [],
            "errors": 0
        }
        
        # 加载保存的网络
        self._load_saved_networks()
        
        # 启动自动扫描
        if self.config.auto_scan:
            self._start_auto_scan()
        
        logger.info(f"WiFiHandler initialized on interface {self.interface}")
    
    def _get_wifi_interface(self) -> Optional[str]:
        """获取WiFi网络接口名称"""
        try:
            interfaces = netifaces.interfaces()
            
            # 常见WiFi接口名称
            wifi_keywords = ['wlan', 'wlp', 'en0']  # en0 在macOS上通常是WiFi
            
            for iface in interfaces:
                if any(keyword in iface for keyword in wifi_keywords):
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_LINK in addrs:  # 有MAC地址，可能是WiFi
                        return iface
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting WiFi interface: {e}")
            return None
    
    def _load_saved_networks(self):
        """加载保存的网络"""
        # 在Linux上从NetworkManager读取
        if self.interface:
            try:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'NAME,UUID,TYPE', 'connection', 'show'],
                    capture_output=True, text=True
                )
                
                for line in result.stdout.split('\n'):
                    if 'wifi' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 1:
                            ssid = parts[0]
                            network = WiFiNetwork(
                                ssid=ssid,
                                saved=True
                            )
                            self.saved_networks[ssid] = network
                
                logger.info(f"Loaded {len(self.saved_networks)} saved networks")
                
            except Exception as e:
                logger.error(f"Error loading saved networks: {e}")
    
    def _start_auto_scan(self):
        """启动自动扫描"""
        def scan_loop():
            while not self._stop_scan.is_set():
                self.scan()
                self._stop_scan.wait(self.config.scan_interval)
        
        self._scan_thread = threading.Thread(target=scan_loop, daemon=True)
        self._scan_thread.start()
        logger.debug("Auto scan started")
    
    def scan(self, timeout: int = 10) -> List[WiFiNetwork]:
        """
        扫描WiFi网络
        
        Args:
            timeout: 扫描超时（秒）
        
        Returns:
            发现的网络列表
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return list(self.available_networks.values())
        
        logger.info("Scanning for WiFi networks...")
        
        self.is_scanning = True
        self.stats["scan_count"] += 1
        
        try:
            networks = []
            
            # 使用系统命令扫描
            if self.interface:
                # Linux使用nmcli
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'SSID,BSSID,SECURITY,SIGNAL,FREQ', 'dev', 'wifi', 'list'],
                    capture_output=True, text=True, timeout=timeout
                )
                
                for line in result.stdout.split('\n'):
                    if not line.strip():
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 5:
                        ssid = parts[0]
                        bssid = parts[1]
                        security_str = parts[2].lower()
                        signal_str = parts[3]
                        freq_str = parts[4]
                        
                        if not ssid:  # 隐藏SSID
                            continue
                        
                        # 解析安全类型
                        if 'wpa3' in security_str:
                            security = WiFiSecurity.WPA3
                        elif 'wpa2' in security_str:
                            security = WiFiSecurity.WPA2
                        elif 'wpa' in security_str:
                            security = WiFiSecurity.WPA
                        elif 'wep' in security_str:
                            security = WiFiSecurity.WEP
                        elif '--' in security_str:
                            security = WiFiSecurity.NONE
                        else:
                            security = WiFiSecurity.UNKNOWN
                        
                        # 解析信号强度
                        try:
                            rssi = int(signal_str)
                        except:
                            rssi = None
                        
                        # 解析频率
                        try:
                            freq = int(freq_str)
                        except:
                            freq = None
                        
                        network = WiFiNetwork(
                            ssid=ssid,
                            bssid=bssid,
                            security=security,
                            rssi=rssi,
                            frequency=freq,
                            saved=ssid in self.saved_networks,
                            last_seen=time.time()
                        )
                        
                        self.available_networks[ssid] = network
                        networks.append(network)
                        
                        if self.on_network_found:
                            self.on_network_found(network)
            
            # 检查当前连接的网络
            self._update_current_network()
            
            logger.info(f"Scan completed, found {len(networks)} networks")
            return networks
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.stats["errors"] += 1
            return list(self.available_networks.values())
            
        finally:
            self.is_scanning = False
    
    def _update_current_network(self):
        """更新当前连接的网络"""
        try:
            if self.interface:
                # 获取当前连接的WiFi
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'],
                    capture_output=True, text=True
                )
                
                for line in result.stdout.split('\n'):
                    if 'wifi' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 1:
                            ssid = parts[0]
                            if ssid in self.available_networks:
                                self.current_network = self.available_networks[ssid]
                                self.current_network.connected = True
                                self.connection_status = ConnectionStatus.CONNECTED
                            return
                
                # 没有活动的WiFi连接
                self.current_network = None
                self.connection_status = ConnectionStatus.DISCONNECTED
                
        except Exception as e:
            logger.error(f"Error updating current network: {e}")
    
    def connect(self, ssid: str, password: Optional[str] = None) -> bool:
        """
        连接WiFi网络
        
        Args:
            ssid: 网络SSID
            password: 密码
        
        Returns:
            是否成功连接
        """
        if self.connection_status == ConnectionStatus.CONNECTED:
            logger.warning(f"Already connected to {self.current_network.ssid}")
            return False
        
        logger.info(f"Connecting to {ssid}...")
        
        self.connection_status = ConnectionStatus.CONNECTING
        
        try:
            network = self.available_networks.get(ssid)
            
            if not network:
                # 尝试手动连接未知网络
                network = WiFiNetwork(ssid=ssid)
            
            # 使用nmcli连接
            if network.security == WiFiSecurity.NONE:
                cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid]
            else:
                if not password:
                    # 尝试使用保存的密码
                    if ssid in self.saved_networks:
                        cmd = ['nmcli', 'connection', 'up', ssid]
                    else:
                        logger.error(f"Password required for {ssid}")
                        self.connection_status = ConnectionStatus.ERROR
                        return False
                else:
                    cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid, 'password', password]
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.config.connect_timeout
            )
            
            if result.returncode == 0:
                self.current_network = network
                network.connected = True
                self.connection_status = ConnectionStatus.CONNECTED
                self.stats["connect_count"] += 1
                self._reconnect_attempts = 0
                
                # 保存网络信息
                if password and ssid not in self.saved_networks:
                    network.saved = True
                    self.saved_networks[ssid] = network
                
                logger.info(f"Connected to {ssid}")
                
                if self.on_network_connected:
                    self.on_network_connected(network)
                
                return True
            else:
                logger.error(f"Connection failed: {result.stderr}")
                self.connection_status = ConnectionStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connection_status = ConnectionStatus.ERROR
            self.stats["errors"] += 1
            return False
    
    def disconnect(self):
        """断开当前WiFi连接"""
        if not self.current_network:
            logger.warning("No active connection")
            return
        
        logger.info(f"Disconnecting from {self.current_network.ssid}...")
        
        self.connection_status = ConnectionStatus.DISCONNECTING
        
        try:
            if self.interface:
                subprocess.run(
                    ['nmcli', 'dev', 'disconnect', self.interface],
                    capture_output=True, timeout=10
                )
            
            if self.current_network:
                self.current_network.connected = False
            
            self.current_network = None
            self.connection_status = ConnectionStatus.DISCONNECTED
            self.stats["disconnect_count"] += 1
            
            logger.info("Disconnected")
            
            if self.on_network_disconnected:
                self.on_network_disconnected(self.current_network)
            
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            self.connection_status = ConnectionStatus.ERROR
    
    def forget_network(self, ssid: str) -> bool:
        """
        忘记保存的网络
        
        Args:
            ssid: 网络SSID
        
        Returns:
            是否成功
        """
        logger.info(f"Forgetting network {ssid}...")
        
        try:
            # 从NetworkManager删除
            subprocess.run(
                ['nmcli', 'connection', 'delete', ssid],
                capture_output=True, timeout=10
            )
            
            if ssid in self.saved_networks:
                del self.saved_networks[ssid]
            
            if ssid in self.available_networks:
                self.available_networks[ssid].saved = False
            
            logger.info(f"Network {ssid} forgotten")
            return True
            
        except Exception as e:
            logger.error(f"Error forgetting network: {e}")
            return False
    
    def create_hotspot(self, ssid: Optional[str] = None, 
                      password: Optional[str] = None) -> bool:
        """
        创建WiFi热点
        
        Args:
            ssid: 热点SSID
            password: 热点密码
        
        Returns:
            是否成功创建
        """
        hotspot_ssid = ssid or self.config.hotspot_ssid
        hotspot_pass = password or self.config.hotspot_password
        
        logger.info(f"Creating hotspot {hotspot_ssid}...")
        
        try:
            if not hotspot_pass:
                logger.error("Password required for hotspot")
                return False
            
            # 使用nmcli创建热点
            cmd = [
                'nmcli', 'dev', 'wifi', 'hotspot',
                'ifname', self.interface,
                'ssid', hotspot_ssid,
                'password', hotspot_pass
            ]
            
            if self.config.hotspot_channel:
                cmd.extend(['channel', str(self.config.hotspot_channel)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.hotspot_active = True
                logger.info(f"Hotspot {hotspot_ssid} created")
                return True
            else:
                logger.error(f"Hotspot creation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Hotspot creation error: {e}")
            return False
    
    def stop_hotspot(self):
        """停止热点"""
        if not self.hotspot_active:
            return
        
        logger.info("Stopping hotspot...")
        
        try:
            subprocess.run(
                ['nmcli', 'dev', 'wifi', 'hotspot', 'off'],
                capture_output=True, timeout=10
            )
            
            self.hotspot_active = False
            logger.info("Hotspot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping hotspot: {e}")
    
    def get_signal_strength(self) -> Optional[int]:
        """
        获取当前信号强度
        
        Returns:
            信号强度 (dBm)
        """
        if not self.current_network:
            return None
        
        try:
            # 从网络信息获取RSSI
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'SSID,SIGNAL', 'dev', 'wifi'],
                capture_output=True, text=True, timeout=5
            )
            
            for line in result.stdout.split('\n'):
                if self.current_network.ssid in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        try:
                            signal = int(parts[1])
                            self.stats["signal_samples"].append(signal)
                            
                            # 限制样本数量
                            if len(self.stats["signal_samples"]) > 100:
                                self.stats["signal_samples"] = self.stats["signal_samples"][-100:]
                            
                            return signal
                        except:
                            pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting signal strength: {e}")
            return None
    
    def get_ip_address(self) -> Optional[str]:
        """
        获取当前IP地址
        
        Returns:
            IP地址
        """
        if not self.interface:
            return None
        
        try:
            addrs = netifaces.ifaddresses(self.interface)
            if netifaces.AF_INET in addrs:
                return addrs[netifaces.AF_INET][0].get('addr')
            return None
        except:
            return None
    
    def get_networks(self, include_hidden: bool = False) -> List[WiFiNetwork]:
        """
        获取可用网络列表
        
        Args:
            include_hidden: 是否包含隐藏网络
        
        Returns:
            网络列表
        """
        networks = list(self.available_networks.values())
        
        if not include_hidden:
            networks = [n for n in networks if n.ssid]
        
        return networks
    
    def get_saved_networks(self) -> List[WiFiNetwork]:
        """
        获取保存的网络列表
        
        Returns:
            保存的网络列表
        """
        return list(self.saved_networks.values())
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取WiFi处理器状态
        
        Returns:
            状态字典
        """
        signal = self.get_signal_strength()
        
        return {
            "interface": self.interface,
            "connection_status": self.connection_status.value,
            "current_network": {
                "ssid": self.current_network.ssid if self.current_network else None,
                "signal": signal,
                "ip": self.get_ip_address()
            } if self.current_network else None,
            "hotspot_active": self.hotspot_active,
            "networks": {
                "available": len(self.available_networks),
                "saved": len(self.saved_networks)
            },
            "config": {
                "auto_scan": self.config.auto_scan,
                "auto_reconnect": self.config.auto_reconnect
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭WiFi处理器"""
        logger.info("Shutting down WiFiHandler...")
        
        # 停止扫描
        self._stop_scan.set()
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=2)
        
        # 断开连接
        if self.current_network:
            self.disconnect()
        
        # 停止热点
        if self.hotspot_active:
            self.stop_hotspot()
        
        # 取消重连定时器
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
        
        logger.info("WiFiHandler shutdown completed")

# 单例模式实现
_wifi_handler_instance: Optional[WiFiHandler] = None

def get_wifi_handler(config: Optional[WiFiConfig] = None) -> WiFiHandler:
    """
    获取WiFi处理器单例
    
    Args:
        config: WiFi配置
    
    Returns:
        WiFi处理器实例
    """
    global _wifi_handler_instance
    if _wifi_handler_instance is None:
        _wifi_handler_instance = WiFiHandler(config)
    return _wifi_handler_instance

