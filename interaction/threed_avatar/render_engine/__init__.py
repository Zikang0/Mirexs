"""
渲染引擎模块
负责3D场景的实时渲染和视觉效果
"""

from .lighting_system import LightingSystem, Light, LightConfig, LightType, lighting_system
from .post_processor import PostProcessor, PostEffectType, PostEffectConfig, post_processor
from .render_optimizer import RenderOptimizer, PerformanceMetrics, OptimizationStrategy, render_optimizer
from .quality_settings import QualitySettingsManager, QualityPreset, GraphicsSettings, quality_settings_manager

# 导出主要类
__all__ = [
    # 光照系统
    'LightingSystem',
    'Light', 
    'LightConfig',
    'LightType',
    'lighting_system',
    
    # 后处理器
    'PostProcessor',
    'PostEffectType',
    'PostEffectConfig',
    'post_processor',
    
    # 渲染优化器
    'RenderOptimizer',
    'PerformanceMetrics', 
    'OptimizationStrategy',
    'render_optimizer',
    
    # 质量设置
    'QualitySettingsManager',
    'QualityPreset',
    'GraphicsSettings',
    'quality_settings_manager'
]

# 模块版本
__version__ = '1.0.0'

def initialize_render_engine(screen_width: int, screen_height: int) -> bool:
    """
    初始化渲染引擎
    
    Args:
        screen_width: 屏幕宽度
        screen_height: 屏幕高度
        
    Returns:
        bool: 是否初始化成功
    """
    try:
        # 初始化后处理器
        if not post_processor.initialize(screen_width, screen_height):
            return False
        
        # 加载质量设置
        quality_settings_manager.load_settings()
        
        # 应用推荐的质量预设
        quality_settings_manager.apply_recommended_preset()
        
        print(f"✅ 渲染引擎初始化成功: {screen_width}x{screen_height}")
        return True
        
    except Exception as e:
        print(f"❌ 渲染引擎初始化失败: {e}")
        return False

def cleanup_render_engine():
    """清理渲染引擎"""
    try:
        lighting_system.cleanup()
        post_processor.cleanup()
        quality_settings_manager.save_settings()
        print("✅ 渲染引擎清理完成")
    except Exception as e:
        print(f"❌ 渲染引擎清理失败: {e}")
