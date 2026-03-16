"""
基础设施层 - 提供计算、存储、通信、数据处理等基础服务

核心模块:
- compute_storage: 计算与存储管理
- communication: 通信与网络服务  
- data_pipelines: 数据处理管道
- platform_adapters: 平台适配器
"""

__version__ = "1.0.0"
__all__ = ["initialize_infrastructure"]

# 基础设施层初始化
def initialize_infrastructure():
    """初始化基础设施层所有组件"""
    from .platform_adapters.hardware_detector import HardwareDetector
    from .compute_storage.resource_manager import ResourceManager
    
    # 检测硬件配置
    hardware_info = HardwareDetector().detect_all()
    
    # 初始化资源管理器
    resource_mgr = ResourceManager()
    resource_mgr.initialize(hardware_info)
    
    print(f"✅ 基础设施层初始化完成")
    print(f"💻 硬件信息: {hardware_info['cpu']['name']}, {hardware_info['gpu']['name']}")
    
    return {
        "hardware_info": hardware_info,
        "resource_manager": resource_mgr
    }
