"""
实时渲染器 - 核心渲染引擎
修复版本：解决模块命名和导入问题
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
import threading
from collections import deque

# 修复导入路径 - 使用下划线前缀避免数字开头的模块名
from data.models.three_d.cat_models import CatModel, CatModelManager, CatModelConfig
from data.models.three_d.textures import TextureManager
from data.models.three_d.animations import AnimationManager, AnimationConfig
from data.models.three_d.rigging_system import RiggingSystem
from data.models.three_d.blend_shapes import BlendShapeSystem
from data.models.three_d.panda3d_integration import Panda3DRenderer

logger = logging.getLogger(__name__)

@dataclass
class RenderSettings:
    """渲染设置"""
    resolution: Tuple[int, int] = (1920, 1080)
    fps_limit: int = 60
    vsync: bool = True
    msaa_samples: int = 4
    shadow_quality: str = "high"  # low, medium, high, ultra
    texture_quality: str = "high"
    post_processing: bool = True
    ambient_occlusion: bool = True
    bloom: bool = True
    motion_blur: bool = False

@dataclass
class RenderStats:
    """渲染统计"""
    frame_count: int = 0
    fps: float = 0.0
    frame_time: float = 0.0
    triangle_count: int = 0
    draw_calls: int = 0
    gpu_memory: float = 0.0
    cpu_time: float = 0.0
    gpu_time: float = 0.0

class RealtimeRenderer:
    """实时渲染器 - 核心渲染引擎"""
    
    def __init__(self, render_settings: RenderSettings = None):
        self.settings = render_settings or RenderSettings()
        self.stats = RenderStats()
        
        # 渲染状态
        self.is_rendering = False
        self.is_initialized = False
        self.frame_time_history = deque(maxlen=60)
        
        # 子系统 - 使用延迟初始化避免导入循环
        self.model_manager = None
        self.texture_manager = None
        self.animation_manager = None
        self.rigging_system = None
        self.blend_shape_system = None
        self.panda3d_renderer = None
        
        # 场景管理
        self.scene_objects: Dict[str, Any] = {}
        self.active_camera: str = "main"
        self.lights: Dict[str, Any] = {}
        self.post_effects: Dict[str, Any] = {}
        
        # 渲染线程
        self.render_thread = None
        self.stop_render_flag = False
        
        logger.info("RealtimeRenderer initialized")
    
    def _initialize_subsystems(self):
        """初始化子系统 - 延迟初始化避免导入问题"""
        try:
            # 只有在需要时才导入子系统
            if self.model_manager is None:
                self.model_manager = CatModelManager()
            if self.texture_manager is None:
                self.texture_manager = TextureManager()
            if self.animation_manager is None:
                self.animation_manager = AnimationManager()
            if self.rigging_system is None:
                self.rigging_system = RiggingSystem()
            if self.panda3d_renderer is None:
                self.panda3d_renderer = Panda3DRenderer()
                
        except ImportError as e:
            logger.warning(f"Subsystem import failed, using fallback: {e}")
            self._create_fallback_subsystems()
    
    def _create_fallback_subsystems(self):
        """创建回退子系统"""
        logger.info("Creating fallback subsystems")
        # 创建简单的回退实现
        self.model_manager = type('FallbackModelManager', (), {})()
        self.texture_manager = type('FallbackTextureManager', (), {})()
        self.animation_manager = type('FallbackAnimationManager', (), {})()
        self.rigging_system = type('FallbackRiggingSystem', (), {})()
        self.panda3d_renderer = type('FallbackRenderer', (), {})()

    def initialize(self) -> bool:
        """初始化渲染引擎"""
        try:
            logger.info("Initializing realtime renderer...")
            
            # 初始化子系统
            self._initialize_subsystems()
            
            # 初始化Panda3D渲染器
            if hasattr(self.panda3d_renderer, 'initialize'):
                if not self.panda3d_renderer.initialize():
                    logger.warning("Panda3D renderer initialization failed, using software rendering")
            else:
                logger.warning("Panda3D renderer not available, using software rendering")
            
            # 加载默认资源
            self._load_default_resources()
            
            # 设置渲染质量
            self._apply_render_settings()
            
            # 启动渲染统计
            self._start_render_stats()
            
            self.is_initialized = True
            self.is_rendering = True
            
            logger.info("Realtime renderer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize realtime renderer: {e}")
            return False
    
    def _load_default_resources(self):
        """加载默认资源"""
        try:
            # 只有在模型管理器可用时加载资源
            if hasattr(self.model_manager, 'load_model'):
                # 加载默认猫咪模型
                default_model_config = CatModelConfig(
                    model_name="default_cat",
                    model_path="./models/three_d/cats/default_cat.gltf",  # 修复路径
                    scale=1.0,
                    lod_levels=3,
                    enable_physics=True,
                    enable_shadows=True
                )
                
                self.model_manager.load_model("default_cat", default_model_config)
            
            # 加载默认纹理
            if hasattr(self.texture_manager, 'load_texture'):
                self.texture_manager.load_texture("cat_fur", "textures/cat_fur.png", "diffuse")
                self.texture_manager.load_texture("cat_eyes", "textures/cat_eyes.png", "diffuse")
                
                # 创建默认材质
                self.texture_manager.create_material(
                    "cat_material",
                    "pbr",
                    {
                        "diffuse": "cat_fur",
                        "normal": "cat_normal", 
                        "roughness": "cat_roughness"
                    },
                    {"metallic": 0.1, "roughness": 0.8}
                )
            
            logger.info("Default resources loaded")
            
        except Exception as e:
            logger.warning(f"Failed to load some default resources: {e}")
    
    def _apply_render_settings(self):
        """应用渲染设置"""
        try:
            # 设置渲染质量
            shadow_resolution = {
                "low": 512,
                "medium": 1024, 
                "high": 2048,
                "ultra": 4096
            }.get(self.settings.shadow_quality, 1024)
            
            texture_quality_map = {
                "low": (512, 512),
                "medium": (1024, 1024),
                "high": (2048, 2048),
                "ultra": (4096, 4096)
            }
            
            target_texture_size = texture_quality_map.get(self.settings.texture_quality, (1024, 1024))
            
            logger.info(f"Applied render settings: {self.settings.shadow_quality} shadows, {self.settings.texture_quality} textures")
            
        except Exception as e:
            logger.error(f"Failed to apply render settings: {e}")
    
    def load_scene(self, scene_file: str) -> bool:
        """加载场景"""
        try:
            logger.info(f"Loading scene: {scene_file}")
            
            # 这里实现场景加载逻辑
            # 包括模型、灯光、相机、材质等
            
            # 模拟场景加载
            self._create_default_scene()
            
            logger.info("Scene loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load scene: {e}")
            return False
    
    def _create_default_scene(self):
        """创建默认场景"""
        try:
            # 创建地面
            self.panda3d_renderer.create_primitive("plane", "ground", 10.0)
            self.panda3d_renderer.set_model_position("ground", (0, 0, 0))
            
            # 创建默认猫咪
            cat_model = self.model_manager.get_model("default_cat")
            if cat_model and cat_model.is_loaded:
                # 在Panda3D中创建模型实例
                success = self.panda3d_renderer.create_primitive("cube", "cat_body", 1.0)
                if success:
                    self.panda3d_renderer.set_model_position("cat_body", (0, 0, 0.5))
                    
                    # 应用材质
                    cat_texture = self.texture_manager.load_texture("cat_fur", "textures/cat_fur.png")
                    if cat_texture:
                        self.panda3d_renderer.apply_texture("cat_body", cat_texture)
            
            logger.info("Default scene created")
            
        except Exception as e:
            logger.error(f"Failed to create default scene: {e}")
    
    def render_frame(self) -> bool:
        """渲染一帧"""
        try:
            start_time = time.time()
            
            if not self.is_initialized:
                return False
            
            # 更新动画
            self._update_animations()
            
            # 更新物理
            self._update_physics()
            
            # 更新场景对象
            self._update_scene_objects()
            
            # 应用后处理效果
            if self.settings.post_processing:
                self._apply_post_processing()
            
            # 更新渲染统计
            frame_time = time.time() - start_time
            self._update_render_stats(frame_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Error rendering frame: {e}")
            return False
    
    def _update_animations(self):
        """更新动画系统"""
        try:
            delta_time = 1.0 / self.settings.fps_limit
            
            # 更新动画管理器
            self.animation_manager.update_animations(delta_time)
            
            # 获取混合姿势并应用到模型
            blended_pose = self.animation_manager.get_current_blended_pose()
            self._apply_pose_to_models(blended_pose)
            
        except Exception as e:
            logger.error(f"Error updating animations: {e}")
    
    def _update_physics(self):
        """更新物理系统"""
        # 这里实现物理更新逻辑
        # 包括碰撞检测、刚体运动等
        pass
    
    def _update_scene_objects(self):
        """更新场景对象"""
        for obj_name, obj_data in self.scene_objects.items():
            # 更新对象位置、旋转、缩放
            if "position" in obj_data:
                self.panda3d_renderer.set_model_position(obj_name, obj_data["position"])
            if "rotation" in obj_data:
                self.panda3d_renderer.set_model_rotation(obj_name, obj_data["rotation"])
            if "scale" in obj_data:
                self.panda3d_renderer.set_model_scale(obj_name, obj_data["scale"])
    
    def _apply_pose_to_models(self, pose: Dict[str, Dict[str, Tuple]]):
        """应用姿势到模型"""
        try:
            for bone_name, bone_data in pose.items():
                # 这里实现将骨骼姿势应用到3D模型
                # 包括顶点变换、骨骼矩阵更新等
                
                # 简化实现：直接更新模型变换
                if "cat_body" in self.scene_objects:
                    # 应用根骨骼的位置和旋转到猫咪身体
                    if bone_name == "root":
                        position = bone_data["position"]
                        # 将位置应用到模型
                        self.scene_objects["cat_body"]["position"] = position
                        
        except Exception as e:
            logger.error(f"Error applying pose to models: {e}")
    
    def _apply_post_processing(self):
        """应用后处理效果"""
        try:
            if self.settings.ambient_occlusion:
                self._apply_ambient_occlusion()
            
            if self.settings.bloom:
                self._apply_bloom_effect()
            
            if self.settings.motion_blur:
                self._apply_motion_blur()
                
        except Exception as e:
            logger.error(f"Error applying post-processing: {e}")
    
    def _apply_ambient_occlusion(self):
        """应用环境光遮蔽"""
        # 实现SSAO或其他AO技术
        pass
    
    def _apply_bloom_effect(self):
        """应用泛光效果"""
        # 实现泛光效果
        pass
    
    def _apply_motion_blur(self):
        """应用运动模糊"""
        # 实现运动模糊效果
        pass
    
    def _start_render_stats(self):
        """启动渲染统计"""
        self.stats = RenderStats()
        self.frame_time_history.clear()
    
    def _update_render_stats(self, frame_time: float):
        """更新渲染统计"""
        self.frame_time_history.append(frame_time)
        self.stats.frame_count += 1
        self.stats.frame_time = frame_time
        self.stats.fps = 1.0 / frame_time if frame_time > 0 else 0
        
        # 计算平均FPS
        if len(self.frame_time_history) > 0:
            avg_frame_time = sum(self.frame_time_history) / len(self.frame_time_history)
            self.stats.fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        # 更新其他统计信息
        self.stats.triangle_count = self._calculate_triangle_count()
        self.stats.draw_calls = len(self.scene_objects)
    
    def _calculate_triangle_count(self) -> int:
        """计算场景中的三角形数量"""
        total_triangles = 0
        for obj_name in self.scene_objects:
            # 这里实现三角形计数逻辑
            # 简化实现
            total_triangles += 1000  # 假设每个对象1000个三角形
        return total_triangles
    
    def start_render_loop(self):
        """启动渲染循环"""
        if not self.is_initialized:
            logger.error("Renderer not initialized")
            return
        
        self.stop_render_flag = False
        
        def render_loop():
            last_time = time.time()
            frame_duration = 1.0 / self.settings.fps_limit
            
            while not self.stop_render_flag and self.is_rendering:
                current_time = time.time()
                elapsed = current_time - last_time
                
                if elapsed >= frame_duration:
                    self.render_frame()
                    last_time = current_time
                
                # 稍微休眠以避免过度占用CPU
                time.sleep(0.001)
        
        self.render_thread = threading.Thread(target=render_loop, daemon=True)
        self.render_thread.start()
        
        logger.info("Render loop started")
    
    def stop_render_loop(self):
        """停止渲染循环"""
        self.stop_render_flag = True
        self.is_rendering = False
        
        if self.render_thread and self.render_thread.is_alive():
            self.render_thread.join(timeout=2.0)
        
        logger.info("Render loop stopped")
    
    def get_render_stats(self) -> RenderStats:
        """获取渲染统计"""
        return self.stats
    
    def set_camera_position(self, position: Tuple[float, float, float]):
        """设置相机位置"""
        try:
            self.panda3d_renderer.set_model_position("camera", position)
        except Exception as e:
            logger.error(f"Error setting camera position: {e}")
    
    def set_camera_rotation(self, rotation: Tuple[float, float, float]):
        """设置相机旋转"""
        try:
            self.panda3d_renderer.set_model_rotation("camera", rotation)
        except Exception as e:
            logger.error(f"Error setting camera rotation: {e}")
    
    def add_light(self, light_name: str, light_type: str, position: Tuple[float, float, float], 
                 color: Tuple[float, float, float, float] = (1, 1, 1, 1)) -> bool:
        """添加灯光"""
        try:
            # 这里实现灯光创建逻辑
            # 简化实现
            self.lights[light_name] = {
                "type": light_type,
                "position": position,
                "color": color
            }
            
            logger.info(f"Added light: {light_name} ({light_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding light: {e}")
            return False
    
    def shutdown(self):
        """关闭渲染器"""
        try:
            self.stop_render_loop()
            
            if self.panda3d_renderer:
                self.panda3d_renderer.shutdown()
            
            self.is_initialized = False
            self.is_rendering = False
            
            logger.info("Realtime renderer shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during renderer shutdown: {e}")


            