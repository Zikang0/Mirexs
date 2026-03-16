"""
移动端适配器 - 移动设备特定功能适配
"""

import os
import sys
import platform
import subprocess
from typing import Dict, Any, Optional

class MobileAdapter:
    """移动设备平台适配器"""
    
    def __init__(self):
        self.platform = "mobile"
        self.supported_platforms = ["android", "ios"]
        self.current_platform = None
        self.initialized = False
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化移动端适配器"""
        self.hardware_info = hardware_info
        self.current_platform = self._detect_mobile_platform()
        self.system_info = self._get_system_info()
        self.initialized = True
        
    def _detect_mobile_platform(self) -> Optional[str]:
        """检测移动平台"""
        # 在桌面环境中，移动平台通常不可用
        # 这里主要用于检测模拟器或未来扩展
        
        # 检查环境变量
        if 'ANDROID_ROOT' in os.environ:
            return "android"
        elif 'IOS_SIMULATOR_ROOT' in os.environ:
            return "ios"
            
        # 检查平台信息
        system_platform = sys.platform.lower()
        if system_platform == "linux" and "android" in platform.platform().lower():
            return "android"
            
        return None
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取移动系统信息"""
        info = {
            'platform': self.current_platform,
            'available': self.current_platform is not None
        }
        
        if self.current_platform == "android":
            info.update(self._get_android_info())
        elif self.current_platform == "ios":
            info.update(self._get_ios_info())
            
        return info
    
    def _get_android_info(self) -> Dict[str, Any]:
        """获取Android系统信息"""
        info = {}
        try:
            # 尝试读取Android系统属性
            if os.path.exists("/system/build.prop"):
                with open("/system/build.prop", "r") as f:
                    for line in f:
                        if "ro.build.version.sdk" in line:
                            info['sdk_version'] = line.split("=")[1].strip()
                        elif "ro.build.version.release" in line:
                            info['android_version'] = line.split("=")[1].strip()
                        elif "ro.product.model" in line:
                            info['device_model'] = line.split("=")[1].strip()
        except:
            pass
            
        return info
    
    def _get_ios_info(self) -> Dict[str, Any]:
        """获取iOS系统信息"""
        info = {}
        try:
            # 在iOS模拟器中获取信息
            if 'SIMULATOR_DEVICE_NAME' in os.environ:
                info['device_name'] = os.environ['SIMULATOR_DEVICE_NAME']
            if 'SIMULATOR_RUNTIME_VERSION' in os.environ:
                info['ios_version'] = os.environ['SIMULATOR_RUNTIME_VERSION']
        except:
            pass
            
        return info
    
    def is_mobile_environment(self) -> bool:
        """检查是否在移动环境中运行"""
        return self.current_platform is not None
    
    def get_sensor_capabilities(self) -> Dict[str, bool]:
        """获取传感器能力（在模拟环境中返回模拟值）"""
        capabilities = {
            'accelerometer': False,
            'gyroscope': False,
            'gps': False,
            'camera': False,
            'microphone': False,
            'touch_screen': False,
            'biometric': False
        }
        
        if not self.is_mobile_environment():
            # 在桌面环境中，模拟移动设备能力
            capabilities.update({
                'touch_screen': True,  # 假设有触摸屏
                'camera': True,        # 假设有摄像头
                'microphone': True     # 假设有麦克风
            })
            
        return capabilities
    
    def get_screen_info(self) -> Dict[str, Any]:
        """获取屏幕信息"""
        # 在桌面环境中返回默认值
        return {
            'width': 1920,
            'height': 1080,
            'density': 1.0,
            'orientation': 'landscape'  # 或 'portrait'
        }
    
    def get_battery_info(self) -> Dict[str, Any]:
        """获取电池信息"""
        # 在桌面环境中返回模拟值
        return {
            'level': 100,        # 电池电量百分比
            'status': 'charged',  # charging, discharging, charged, unknown
            'health': 'good'      # good, overheat, dead, unknown
        }
    
    def get_network_info(self) -> Dict[str, Any]:
        """获取网络信息"""
        return {
            'type': 'wifi',      # wifi, cellular, ethernet, unknown
            'connected': True,
            'metered': False
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        # 返回模拟的存储信息
        return {
            'total': 128 * 1024 * 1024 * 1024,  # 128 GB
            'available': 64 * 1024 * 1024 * 1024,  # 64 GB
            'external_available': False
        }
    
    def vibrate(self, duration: int = 100) -> bool:
        """触发振动（在桌面环境中模拟）"""
        if not self.is_mobile_environment():
            print(f"📳 模拟振动: {duration}ms")
            return True
        return False
    
    def show_toast(self, message: str, duration: str = "short") -> bool:
        """显示Toast通知"""
        print(f"🍞 Toast [{duration}]: {message}")
        return True
    
    def check_permission(self, permission: str) -> str:
        """检查权限状态"""
        # granted, denied, not_determined
        permission_map = {
            'camera': 'granted',
            'microphone': 'granted', 
            'location': 'not_determined',
            'storage': 'granted'
        }
        return permission_map.get(permission, 'not_determined')
    
    def request_permission(self, permission: str) -> str:
        """请求权限"""
        print(f"🔐 请求权限: {permission}")
        return 'granted'  # 模拟授权