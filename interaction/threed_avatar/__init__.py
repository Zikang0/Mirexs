"""
3D虚拟猫咪核心系统 - 主入口和集成模块
负责协调3D渲染、角色系统、行为系统和语音同步系统
提供统一的API接口和系统管理功能
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import time
from pathlib import Path

# 导入各子系统
from interaction.threed_avatar.render_engine.realtime_renderer import RealtimeRenderer
from interaction.threed_avatar.render_engine.lighting_system import LightingSystem
from interaction.threed_avatar.render_engine.material_manager import MaterialManager

from interaction.threed_avatar.character_system.model_manager import ModelManager, ModelInstance, ModelLoadConfig, ModelFormat, ModelQuality
from interaction.threed_avatar.character_system.skeleton_animation import SkeletonAnimation, AnimationState, BlendMode

from interaction.threed_avatar.behavior_system.emotion_engine import EmotionEngine, EmotionType, EmotionIntensity
from interaction.threed_avatar.behavior_system.behavior_planner import BehaviorPlanner, BehaviorType, BehaviorPriority
from interaction.threed_avatar.behavior_system.personality_model import PersonalityModel, PersonalityTraits

from interaction.threed_avatar.speech_sync.lip_sync_engine import LipSyncEngine, LipSyncConfig, LipSyncState
from interaction.threed_avatar.speech_sync.voice_animation_map import VoiceAnimationMap, MappingType
from interaction.threed_avatar.speech_sync.phoneme_analyzer import PhonemeAnalyzer, PhonemeAnalysisConfig
from interaction.threed_avatar.speech_sync.viseme_generator import VisemeGenerator, VisemeType, VisemeConfig
from interaction.threed_avatar.speech_sync.sync_optimizer import SyncOptimizer, SyncQualityMetrics
from interaction.threed_avatar.speech_sync.audio_visualizer import AudioVisualizer, VisualizationType
from interaction.threed_avatar.speech_sync.sync_metrics import SyncMetrics, PerformanceMetrics

# 导入输出系统依赖
from interaction.output_systems.speech_output.multilingual_tts import MultilingualTTS, TTSConfig, VoiceProfile, EmotionType as TTS_EmotionType

logger = logging.getLogger(__name__)

@dataclass
class ThreeDAvatarConfig:
    """3D虚拟猫咪配置"""
    # 渲染配置
    screen_width: int = 1920
    screen_height: int = 1080
    frame_rate: int = 60
    quality_preset: str = "high"  # low, medium, high, ultra
    
    # 模型配置
    model_path: str = "models/3d/cat_avatar.glb"
    model_format: ModelFormat = ModelFormat.GLB
    model_quality: ModelQuality = ModelQuality.HIGH
    
    # 行为配置
    personality_traits: PersonalityTraits = None
    default_emotion: EmotionType = EmotionType.NEUTRAL
    
    # 语音同步配置
    lip_sync_enabled: bool = True
    lip_sync_config: LipSyncConfig = None
    
    # 性能配置
    max_memory_mb: int = 1024
    gpu_acceleration: bool = True
    realtime_processing: bool = True

class ThreeDAvatarSystem:
    """3D虚拟猫咪核心系统 - 完整集成"""
    
    def __init__(self, config: ThreeDAvatarConfig = None):
        # 配置
        self.config = config or ThreeDAvatarConfig()
        
        # 系统状态
        self.is_initialized = False
        self.is_running = False
        self.current_state = "stopped"
        
        # 子系统实例
        self.render_engine: Optional[RealtimeRenderer] = None
        self.lighting_system: Optional[LightingSystem] = None
        self.material_manager: Optional[MaterialManager] = None
        
        self.model_manager: Optional[ModelManager] = None
        self.model_instance: Optional[ModelInstance] = None
        self.skeleton_animation: Optional[SkeletonAnimation] = None
        
        self.emotion_engine: Optional[EmotionEngine] = None
        self.behavior_planner: Optional[BehaviorPlanner] = None
        self.personality_model: Optional[PersonalityModel] = None
        
        self.lip_sync_engine: Optional[LipSyncEngine] = None
        self.voice_animation_map: Optional[VoiceAnimationMap] = None
        self.phoneme_analyzer: Optional[PhonemeAnalyzer] = None
        self.viseme_generator: Optional[VisemeGenerator] = None
        self.sync_optimizer: Optional[SyncOptimizer] = None
        self.audio_visualizer: Optional[AudioVisualizer] = None
        self.sync_metrics: Optional[SyncMetrics] = None
        
        self.tts_system: Optional[MultilingualTTS] = None
        
        # 性能统计
        self.performance_stats = {
            "frame_count": 0,
            "average_fps": 0.0,
            "memory_usage_mb": 0.0,
            "system_uptime": 0.0,
            "last_update_time": 0.0
        }
        
        # 事件回调
        self.event_callbacks = {
            "on_initialized": [],
            "on_error": [],
            "on_state_changed": [],
            "on_animation_completed": [],
            "on_speech_started": [],
            "on_speech_completed": []
        }
        
        logger.info("3D Avatar System created")

    async def initialize(self) -> bool:
        """初始化3D虚拟猫咪系统"""
        try:
            logger.info("Initializing 3D Avatar System...")
            self.current_state = "initializing"
            
            # 1. 初始化渲染系统
            await self._initialize_rendering_system()
            
            # 2. 初始化模型和动画系统
            await self._initialize_model_system()
            
            # 3. 初始化行为系统
            await self._initialize_behavior_system()
            
            # 4. 初始化语音同步系统
            await self._initialize_speech_sync_system()
            
            # 5. 初始化TTS系统
            await self._initialize_tts_system()
            
            # 6. 启动主循环
            await self._start_main_loop()
            
            self.is_initialized = True
            self.current_state = "ready"
            
            # 触发初始化完成事件
            await self._trigger_event("on_initialized", {"system": self})
            
            logger.info("3D Avatar System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize 3D Avatar System: {e}")
            await self._trigger_event("on_error", {"error": str(e), "phase": "initialization"})
            return False

    async def _initialize_rendering_system(self):
        """初始化渲染系统"""
        try:
            logger.info("Initializing rendering system...")
            
            # 初始化材质管理器
            self.material_manager = MaterialManager()
            await self.material_manager.initialize()
            
            # 初始化光照系统
            self.lighting_system = LightingSystem()
            await self.lighting_system.initialize()
            
            # 初始化实时渲染器
            self.render_engine = RealtimeRenderer(
                screen_width=self.config.screen_width,
                screen_height=self.config.screen_height,
                frame_rate=self.config.frame_rate,
                quality_preset=self.config.quality_preset
            )
            await self.render_engine.initialize()
            
            logger.info("Rendering system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing rendering system: {e}")
            raise

    async def _initialize_model_system(self):
        """初始化模型系统"""
        try:
            logger.info("Initializing model system...")
            
            # 初始化模型管理器
            self.model_manager = ModelManager(cache_size_mb=self.config.max_memory_mb // 2)
            
            # 加载主模型
            model_config = ModelLoadConfig(
                model_name="cat_avatar",
                file_path=self.config.model_path,
                model_format=self.config.model_format,
                quality=self.config.model_quality,
                load_animations=True,
                load_textures=True,
                preload_gpu=self.config.gpu_acceleration
            )
            
            self.model_instance = await self.model_manager.load_model(model_config)
            if not self.model_instance or not self.model_instance.is_loaded:
                raise Exception("Failed to load 3D model")
            
            # 初始化骨骼动画系统
            self.skeleton_animation = SkeletonAnimation(self.model_instance)
            
            logger.info(f"Model system initialized: {self.model_instance.metadata.name}")
            
        except Exception as e:
            logger.error(f"Error initializing model system: {e}")
            raise

    async def _initialize_behavior_system(self):
        """初始化行为系统"""
        try:
            logger.info("Initializing behavior system...")
            
            # 初始化个性模型
            self.personality_model = PersonalityModel(
                self.config.personality_traits or PersonalityTraits()
            )
            
            # 初始化情感引擎
            self.emotion_engine = EmotionEngine(self.personality_model)
            await self.emotion_engine.initialize()
            
            # 设置默认情感
            await self.emotion_engine.set_emotion(
                self.config.default_emotion, 
                EmotionIntensity.MEDIUM
            )
            
            # 初始化行为规划器
            self.behavior_planner = BehaviorPlanner(
                self.emotion_engine, 
                self.skeleton_animation
            )
            await self.behavior_planner.initialize()
            
            logger.info("Behavior system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing behavior system: {e}")
            raise

    async def _initialize_speech_sync_system(self):
        """初始化语音同步系统"""
        try:
            if not self.config.lip_sync_enabled:
                logger.info("Lip sync disabled, skipping initialization")
                return
                
            logger.info("Initializing speech sync system...")
            
            # 初始化语音动画映射
            self.voice_animation_map = VoiceAnimationMap()
            
            # 初始化音素分析器
            self.phoneme_analyzer = PhonemeAnalyzer()
            
            # 初始化视素生成器
            self.viseme_generator = VisemeGenerator(self.model_instance)
            
            # 初始化同步优化器
            self.sync_optimizer = SyncOptimizer()
            
            # 初始化音频可视化器
            self.audio_visualizer = AudioVisualizer()
            
            # 初始化同步指标
            self.sync_metrics = SyncMetrics()
            
            # 初始化嘴唇同步引擎
            lip_sync_config = self.config.lip_sync_config or LipSyncConfig()
            self.lip_sync_engine = LipSyncEngine(
                self.model_instance, 
                self.skeleton_animation
            )
            
            logger.info("Speech sync system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing speech sync system: {e}")
            raise

    async def _initialize_tts_system(self):
        """初始化TTS系统"""
        try:
            logger.info("Initializing TTS system...")
            
            self.tts_system = MultilingualTTS()
            
            # 设置默认语音配置
            default_voice = VoiceProfile(
                voice_id="chinese_female_01",
                name="弥尔思",
                gender="female",
                age="young",
                language="zh-cn"
            )
            await self.tts_system.set_voice_profile(default_voice.voice_id)
            
            logger.info("TTS system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing TTS system: {e}")
            raise

    async def _start_main_loop(self):
        """启动主循环"""
        try:
            self.is_running = True
            self.current_state = "running"
            
            # 启动异步更新任务
            asyncio.create_task(self._update_loop())
            
            logger.info("Main loop started")
            
        except Exception as e:
            logger.error(f"Error starting main loop: {e}")
            raise

    async def _update_loop(self):
        """主更新循环"""
        last_time = time.time()
        frame_count = 0
        fps_update_interval = 1.0  # 每秒更新一次FPS
        fps_timer = 0.0
        
        while self.is_running:
            try:
                current_time = time.time()
                delta_time = current_time - last_time
                last_time = current_time
                
                # 更新性能统计
                frame_count += 1
                fps_timer += delta_time
                
                if fps_timer >= fps_update_interval:
                    self.performance_stats["average_fps"] = frame_count / fps_timer
                    self.performance_stats["frame_count"] = frame_count
                    self.performance_stats["system_uptime"] = current_time
                    frame_count = 0
                    fps_timer = 0.0
                
                # 更新各子系统
                await self._update_subsystems(delta_time)
                
                # 控制帧率
                await asyncio.sleep(1.0 / self.config.frame_rate - delta_time)
                
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(0.016)  # 至少等待16ms

    async def _update_subsystems(self, delta_time: float):
        """更新所有子系统"""
        try:
            # 更新行为系统
            if self.behavior_planner:
                await self.behavior_planner.update(delta_time)
            
            # 更新情感系统
            if self.emotion_engine:
                await self.emotion_engine.update(delta_time)
            
            # 更新动画系统
            if self.skeleton_animation:
                await self.skeleton_animation.update(delta_time)
            
            # 更新嘴唇同步
            if self.lip_sync_engine and self.config.lip_sync_enabled:
                await self.lip_sync_engine.update(delta_time)
            
            # 更新渲染
            if self.render_engine:
                await self.render_engine.render_frame()
            
            # 更新性能指标
            self.performance_stats["last_update_time"] = time.time()
            
        except Exception as e:
            logger.error(f"Error updating subsystems: {e}")

    async def speak(self, text: str, emotion: TTS_EmotionType = TTS_EmotionType.NEUTRAL) -> bool:
        """
        让虚拟猫咪说话
        
        Args:
            text: 要说的文本
            emotion: 说话时的情感
            
        Returns:
            bool: 是否成功开始说话
        """
        try:
            if not self.is_initialized or not self.is_running:
                logger.error("System not ready for speech")
                return False
            
            # 触发语音开始事件
            await self._trigger_event("on_speech_started", {"text": text, "emotion": emotion})
            
            # 同步嘴唇动画
            if self.lip_sync_engine and self.config.lip_sync_enabled:
                success = await self.lip_sync_engine.synchronize_speech(text, emotion)
                if not success:
                    logger.warning("Lip sync failed, continuing without synchronization")
            
            # 执行TTS语音合成和播放
            if self.tts_system:
                tts_config = TTSConfig(emotion=emotion, realtime=self.config.realtime_processing)
                tts_result = await self.tts_system.synthesize(text, tts_config)
                
                if tts_result:
                    # 这里应该播放音频，实际实现需要音频播放系统
                    logger.info(f"Speech synthesized: {text}")
                    
                    # 等待语音播放完成（模拟）
                    speech_duration = len(tts_result.audio_data) / tts_result.sample_rate
                    await asyncio.sleep(speech_duration)
            
            # 触发语音完成事件
            await self._trigger_event("on_speech_completed", {"text": text, "emotion": emotion})
            
            logger.info(f"Speech completed: {text}")
            return True
            
        except Exception as e:
            logger.error(f"Error during speech: {e}")
            await self._trigger_event("on_error", {"error": str(e), "phase": "speech"})
            return False

    async def set_emotion(self, emotion: EmotionType, intensity: EmotionIntensity = EmotionIntensity.MEDIUM) -> bool:
        """设置虚拟猫咪的情感状态"""
        try:
            if not self.emotion_engine:
                return False
            
            success = await self.emotion_engine.set_emotion(emotion, intensity)
            if success:
                logger.info(f"Emotion set to: {emotion.value} (intensity: {intensity.value})")
            return success
            
        except Exception as e:
            logger.error(f"Error setting emotion: {e}")
            return False

    async def play_animation(self, animation_name: str, blend_time: float = 0.0) -> bool:
        """播放动画"""
        try:
            if not self.skeleton_animation:
                return False
            
            success = await self.skeleton_animation.play_animation(animation_name, blend_time)
            if success:
                logger.info(f"Animation started: {animation_name}")
            return success
            
        except Exception as e:
            logger.error(f"Error playing animation: {e}")
            return False

    async def execute_behavior(self, behavior_type: BehaviorType, priority: BehaviorPriority = BehaviorPriority.NORMAL) -> bool:
        """执行行为"""
        try:
            if not self.behavior_planner:
                return False
            
            success = await self.behavior_planner.execute_behavior(behavior_type, priority)
            if success:
                logger.info(f"Behavior executed: {behavior_type.value}")
            return success
            
        except Exception as e:
            logger.error(f"Error executing behavior: {e}")
            return False

    async def set_voice_profile(self, voice_id: str) -> bool:
        """设置语音配置"""
        try:
            if not self.tts_system:
                return False
            
            success = await self.tts_system.set_voice_profile(voice_id)
            if success:
                logger.info(f"Voice profile set to: {voice_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error setting voice profile: {e}")
            return False

    async def load_custom_model(self, model_path: str, model_format: ModelFormat = ModelFormat.GLB) -> bool:
        """加载自定义模型"""
        try:
            if not self.model_manager:
                return False
            
            model_config = ModelLoadConfig(
                model_name="custom_model",
                file_path=model_path,
                model_format=model_format,
                quality=self.config.model_quality
            )
            
            new_model = await self.model_manager.load_model(model_config)
            if new_model and new_model.is_loaded:
                # 卸载旧模型
                if self.model_instance:
                    await self.model_manager.unload_model(self.model_instance)
                
                # 更新模型实例
                self.model_instance = new_model
                
                # 重新初始化相关系统
                self.skeleton_animation = SkeletonAnimation(self.model_instance)
                
                if self.lip_sync_engine:
                    self.lip_sync_engine = LipSyncEngine(self.model_instance, self.skeleton_animation)
                
                if self.viseme_generator:
                    self.viseme_generator = VisemeGenerator(self.model_instance)
                
                logger.info(f"Custom model loaded: {model_path}")
                return True
            else:
                logger.error("Failed to load custom model")
                return False
                
        except Exception as e:
            logger.error(f"Error loading custom model: {e}")
            return False

    def add_event_listener(self, event_type: str, callback: callable):
        """添加事件监听器"""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def remove_event_listener(self, event_type: str, callback: callable):
        """移除事件监听器"""
        if event_type in self.event_callbacks and callback in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].remove(callback)

    async def _trigger_event(self, event_type: str, data: Dict[str, Any]):
        """触发事件"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error in event callback for {event_type}: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "current_state": self.current_state,
            "performance": self.performance_stats.copy(),
            "subsystems": {
                "rendering": self.render_engine is not None,
                "model": self.model_instance is not None and self.model_instance.is_loaded,
                "animation": self.skeleton_animation is not None,
                "behavior": self.behavior_planner is not None,
                "emotion": self.emotion_engine is not None,
                "lip_sync": self.lip_sync_engine is not None and self.config.lip_sync_enabled,
                "tts": self.tts_system is not None
            }
        }
        
        # 添加各子系统详细状态
        if self.skeleton_animation:
            status["animation_state"] = await self.skeleton_animation.get_stats()
        
        if self.emotion_engine:
            status["emotion_state"] = await self.emotion_engine.get_current_emotion()
        
        if self.lip_sync_engine and self.config.lip_sync_enabled:
            status["lip_sync_state"] = await self.lip_sync_engine.get_sync_quality()
        
        return status

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self.performance_stats.copy()
        
        # 添加各子系统性能指标
        if self.render_engine:
            metrics["rendering"] = await self.render_engine.get_performance_metrics()
        
        if self.model_manager:
            metrics["memory"] = self.model_manager.get_memory_usage()
        
        if self.sync_metrics:
            metrics["sync"] = await self.sync_metrics.get_metrics()
        
        return metrics

    async def export_system_data(self, export_path: str) -> bool:
        """导出系统数据"""
        try:
            import json
            import pickle
            
            # 创建导出目录
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出系统配置
            config_path = export_dir / "system_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.__dict__, f, indent=2)
            
            # 导出个性模型
            if self.personality_model:
                personality_path = export_dir / "personality_model.json"
                await self.personality_model.export_model(str(personality_path))
            
            # 导出语音配置
            if self.tts_system:
                voice_path = export_dir / "voice_profiles.json"
                await self.tts_system.export_voice_profiles(str(voice_path))
            
            # 导出同步数据
            if self.lip_sync_engine:
                sync_path = export_dir / "sync_data.json"
                await self.lip_sync_engine.export_sync_data(str(sync_path))
            
            logger.info(f"System data exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting system data: {e}")
            return False

    async def import_system_data(self, import_path: str) -> bool:
        """导入系统数据"""
        try:
            import json
            
            import_dir = Path(import_path)
            
            # 导入系统配置
            config_path = import_dir / "system_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                # 更新配置（注意：某些运行时配置可能无法更改）
                for key, value in config_data.items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
            
            # 导入个性模型
            personality_path = import_dir / "personality_model.json"
            if personality_path.exists() and self.personality_model:
                await self.personality_model.import_model(str(personality_path))
            
            # 导入语音配置
            voice_path = import_dir / "voice_profiles.json"
            if voice_path.exists() and self.tts_system:
                await self.tts_system.import_voice_profiles(str(voice_path))
            
            logger.info(f"System data imported from {import_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing system data: {e}")
            return False

    async def shutdown(self):
        """关闭系统"""
        try:
            logger.info("Shutting down 3D Avatar System...")
            self.is_running = False
            self.current_state = "shutting_down"
            
            # 关闭各子系统
            if self.lip_sync_engine:
                await self.lip_sync_engine.cleanup()
            
            if self.behavior_planner:
                await self.behavior_planner.cleanup()
            
            if self.emotion_engine:
                await self.emotion_engine.cleanup()
            
            if self.skeleton_animation:
                await self.skeleton_animation.cleanup()
            
            if self.model_manager and self.model_instance:
                await self.model_manager.unload_model(self.model_instance)
            
            if self.render_engine:
                await self.render_engine.cleanup()
            
            if self.tts_system:
                await self.tts_system.cleanup()
            
            self.is_initialized = False
            self.current_state = "stopped"
            
            logger.info("3D Avatar System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")

    def __del__(self):
        """析构函数"""
        if self.is_running:
            try:
                # 尝试异步关闭，但析构函数不能是async
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.shutdown())
                else:
                    asyncio.run(self.shutdown())
            except:
                pass  # 忽略析构过程中的错误

# 全局系统实例（单例模式）
_global_avatar_system: Optional[ThreeDAvatarSystem] = None

async def get_avatar_system(config: ThreeDAvatarConfig = None) -> ThreeDAvatarSystem:
    """获取全局3D虚拟猫咪系统实例（单例）"""
    global _global_avatar_system
    
    if _global_avatar_system is None:
        _global_avatar_system = ThreeDAvatarSystem(config)
        await _global_avatar_system.initialize()
    
    return _global_avatar_system

async def shutdown_avatar_system():
    """关闭全局3D虚拟猫咪系统"""
    global _global_avatar_system
    
    if _global_avatar_system:
        await _global_avatar_system.shutdown()
        _global_avatar_system = None

# 导出主要类和函数
__all__ = [
    # 主系统
    "ThreeDAvatarSystem",
    "ThreeDAvatarConfig",
    "get_avatar_system",
    "shutdown_avatar_system",
    
    # 渲染系统
    "RealtimeRenderer",
    "LightingSystem", 
    "MaterialManager",
    
    # 模型和动画系统
    "ModelManager",
    "ModelInstance", 
    "ModelLoadConfig",
    "ModelFormat",
    "ModelQuality",
    "SkeletonAnimation",
    "AnimationState",
    "BlendMode",
    
    # 行为系统
    "EmotionEngine",
    "EmotionType",
    "EmotionIntensity", 
    "BehaviorPlanner",
    "BehaviorType",
    "BehaviorPriority",
    "PersonalityModel", 
    "PersonalityTraits",
    
    # 语音同步系统
    "LipSyncEngine",
    "LipSyncConfig", 
    "LipSyncState",
    "VoiceAnimationMap",
    "MappingType",
    "PhonemeAnalyzer",
    "PhonemeAnalysisConfig",
    "VisemeGenerator", 
    "VisemeType",
    "VisemeConfig",
    "SyncOptimizer",
    "SyncQualityMetrics",
    "AudioVisualizer",
    "VisualizationType", 
    "SyncMetrics",
    "PerformanceMetrics",
    
    # TTS系统
    "MultilingualTTS",
    "TTSConfig",
    "VoiceProfile",
    "TTS_EmotionType"
]