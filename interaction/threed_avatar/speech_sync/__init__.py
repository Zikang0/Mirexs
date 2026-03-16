"""
语音同步系统包 - 提供完整的语音到3D口型同步功能
包含嘴唇同步引擎、音素分析、视素生成、同步优化等核心模块
"""

__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "Advanced lip-sync system for 3D virtual characters"

# 导入主要类
from .lip_sync_engine import LipSyncEngine, LipSyncConfig, LipSyncFrame, LipSyncState
from .voice_animation_map import VoiceAnimationMap, VoiceAnimationMapping, AnimationParameter, MappingType
from .phoneme_analyzer import PhonemeAnalyzer, Phoneme, PhonemeType, PhonemeAnalysisConfig
from .viseme_generator import VisemeGenerator, VisemeData, VisemeType, VisemeConfig
from .sync_metrics import SyncMetrics, SyncMetric, SyncMetricType, SyncQualityReport, SyncQualityLevel
from .emotional_tts import EmotionalTTS, EmotionalProfile, EmotionalFeature

# 导入工具函数
from .sync_optimizer import SyncOptimizer
from .audio_visualizer import AudioVisualizer

# 全局实例（根据需要创建）
__all__ = [
    # 主要类
    "LipSyncEngine",
    "VoiceAnimationMap", 
    "PhonemeAnalyzer",
    "VisemeGenerator",
    "SyncMetrics",
    "EmotionalTTS",
    "SyncOptimizer",
    "AudioVisualizer",
    
    # 数据类
    "LipSyncConfig",
    "LipSyncFrame", 
    "LipSyncState",
    "VoiceAnimationMapping",
    "AnimationParameter",
    "MappingType",
    "Phoneme",
    "PhonemeType",
    "PhonemeAnalysisConfig", 
    "VisemeData",
    "VisemeType",
    "VisemeConfig",
    "SyncMetric",
    "SyncMetricType",
    "SyncQualityReport",
    "SyncQualityLevel",
    "EmotionalProfile",
    "EmotionalFeature"
]

# 包初始化逻辑
def initialize_speech_sync_system():
    """
    初始化语音同步系统
    返回配置好的系统组件字典
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 这里可以添加系统初始化逻辑
        # 例如: 预加载模型、检查依赖等
        
        system_status = {
            "lip_sync_engine": "ready",
            "phoneme_analyzer": "ready", 
            "viseme_generator": "ready",
            "voice_animation_map": "ready",
            "sync_metrics": "ready",
            "emotional_tts": "ready",
            "version": __version__
        }
        
        logger.info(f"Speech sync system initialized: version {__version__}")
        return system_status
        
    except Exception as e:
        logger.error(f"Failed to initialize speech sync system: {e}")
        return {"status": "error", "error": str(e)}

# 包级别的便捷函数
def create_lip_sync_system(model_instance, skeleton_animation):
    """
    创建完整的嘴唇同步系统
    
    Args:
        model_instance: 3D模型实例
        skeleton_animation: 骨骼动画系统
        
    Returns:
        dict: 包含所有系统组件的字典
    """
    try:
        # 创建核心组件
        lip_sync_engine = LipSyncEngine(model_instance, skeleton_animation)
        phoneme_analyzer = PhonemeAnalyzer()
        viseme_generator = VisemeGenerator(model_instance)
        voice_animation_map = VoiceAnimationMap()
        sync_metrics = SyncMetrics()
        emotional_tts = EmotionalTTS()
        
        system_components = {
            "lip_sync_engine": lip_sync_engine,
            "phoneme_analyzer": phoneme_analyzer,
            "viseme_generator": viseme_generator, 
            "voice_animation_map": voice_animation_map,
            "sync_metrics": sync_metrics,
            "emotional_tts": emotional_tts
        }
        
        return system_components
        
    except Exception as e:
        logging.error(f"Failed to create lip sync system: {e}")
        return {}

# 包信息
def get_package_info():
    """获取包信息"""
    return {
        "name": "speech_sync",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "modules": __all__
    }

# 自动初始化检查
_AUTO_INIT = False  # 设置为True可启用自动初始化

if _AUTO_INIT:
    initialize_speech_sync_system()