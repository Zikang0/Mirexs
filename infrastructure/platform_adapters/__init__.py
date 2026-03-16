"""
平台适配器模块 - 跨平台硬件检测和功能适配

提供统一的跨平台接口，自动适配不同操作系统的特定功能
"""

from .windows_adapter import WindowsAdapter
from .linux_adapter import LinuxAdapter
from .macos_adapter import MacOSAdapter
from .mobile_adapter import MobileAdapter
from .audio_adapter import AudioAdapter
from .graphics_adapter import GraphicsAdapter
from .file_system_adapter import FileSystemAdapter
from .hardware_detector import HardwareDetector

__all__ = [
    "WindowsAdapter",
    "LinuxAdapter", 
    "MacOSAdapter",
    "MobileAdapter",
    "AudioAdapter",
    "GraphicsAdapter",
    "FileSystemAdapter", 
    "HardwareDetector"
]

class PlatformAdapterManager:
    """平台适配器管理器"""
    
    def __init__(self):
        self.adapters = {}
        self.current_platform = None
        self.hardware_info = None
        
    def initialize(self):
        """初始化平台适配器"""
        from .hardware_detector import HardwareDetector
        
        # 检测硬件和平台
        detector = HardwareDetector()
        self.hardware_info = detector.detect_all()
        self.current_platform = self.hardware_info['system']['platform']
        
        # 根据平台初始化对应的适配器
        if self.current_platform == "windows":
            self.adapters['os'] = WindowsAdapter()
        elif self.current_platform == "linux":
            self.adapters['os'] = LinuxAdapter()
        elif self.current_platform == "darwin":  # macOS
            self.adapters['os'] = MacOSAdapter()
        else:
            raise NotImplementedError(f"平台 {self.current_platform} 暂不支持")
            
        # 初始化通用适配器
        self.adapters['audio'] = AudioAdapter()
        self.adapters['graphics'] = GraphicsAdapter()
        self.adapters['filesystem'] = FileSystemAdapter()
        self.adapters['mobile'] = MobileAdapter()
        
        # 初始化所有适配器
        for adapter in self.adapters.values():
            adapter.initialize(self.hardware_info)
            
        print(f"✅ 平台适配器初始化完成 - {self.current_platform}")
        
    def get_adapter(self, adapter_type):
        """获取指定类型的适配器"""
        return self.adapters.get(adapter_type)
    
    def get_platform_info(self):
        """获取平台信息"""
        return {
            'platform': self.current_platform,
            'hardware': self.hardware_info
        }