"""
Panda3D游戏引擎集成
负责3D场景的渲染、相机控制和Panda3D引擎的封装
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    NodePath, ModelNode, GeomNode, Geom, GeomVertexData, GeomVertexFormat,
    GeomVertexWriter, GeomTriangles, Texture, GeomVertexArrayFormat,
    InternalName, TransparencyAttrib, Material, LVector3, LPoint3,
    PerspectiveLens, OrthographicLens, AmbientLight, DirectionalLight,
    Vec3, Vec4, BitMask32, Shader, Loader, TextureStage, CardMaker,
    MovieTexture, WindowProperties
)

logger = logging.getLogger(__name__)

class Panda3DRenderer:
    """Panda3D渲染器封装类"""
    
    def __init__(self, window_title: str = "Mirexs 3D Renderer", 
                 window_size: Tuple[int, int] = (1280, 720)):
        self.showbase = None
        self.window_title = window_title
        self.window_size = window_size
        self.models: Dict[str, NodePath] = {}
        self.animations: Dict[str, Any] = {}
        self.cameras: Dict[str, NodePath] = {}
        self.lights: Dict[str, NodePath] = {}
        self.shaders: Dict[str, Shader] = {}
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """
        初始化Panda3D引擎
        
        Returns:
            bool: 是否初始化成功
        """
        try:
            # 创建ShowBase实例
            self.showbase = ShowBase()
            
            # 设置窗口属性
            props = WindowProperties()
            props.setTitle(self.window_title)
            props.setSize(self.window_size[0], self.window_size[1])
            self.showbase.win.requestProperties(props)
            
            # 设置默认相机
            self.setup_default_camera()
            
            # 设置默认光照
            self.setup_default_lighting()
            
            # 设置渲染状态
            self.setup_render_state()
            
            self.is_initialized = True
            logger.info("Panda3D renderer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Panda3D renderer: {str(e)}")
            return False
            
    def setup_default_camera(self):
        """设置默认相机"""
        try:
            # 主相机
            self.cameras['main'] = self.showbase.camera
            self.showbase.camera.setPos(0, -10, 2)
            self.showbase.camera.lookAt(0, 0, 0)
            
            # 透视镜头
            lens = PerspectiveLens()
            lens.setFov(60)
            lens.setNearFar(0.1, 1000)
            self.showbase.cam.node().setLens(lens)
            
            logger.info("Default camera setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup default camera: {str(e)}")
            
    def setup_default_lighting(self):
        """设置默认光照"""
        try:
            # 环境光
            ambient_light = AmbientLight("ambient_light")
            ambient_light.setColor(Vec4(0.3, 0.3, 0.3, 1))
            ambient_light_np = self.showbase.render.attachNewNode(ambient_light)
            self.showbase.render.setLight(ambient_light_np)
            self.lights['ambient'] = ambient_light_np
            
            # 方向光
            directional_light = DirectionalLight("directional_light")
            directional_light.setColor(Vec4(0.8, 0.8, 0.8, 1))
            directional_light_np = self.showbase.render.attachNewNode(directional_light)
            directional_light_np.setHpr(45, -45, 0)
            self.showbase.render.setLight(directional_light_np)
            self.lights['directional'] = directional_light_np
            
            logger.info("Default lighting setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup default lighting: {str(e)}")
            
    def setup_render_state(self):
        """设置渲染状态"""
        try:
            # 启用深度测试
            self.showbase.render.setDepthTest(True)
            self.showbase.render.setDepthWrite(True)
            
            # 设置背景颜色
            self.showbase.setBackgroundColor(0.1, 0.1, 0.2, 1)
            
            logger.info("Render state setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup render state: {str(e)}")
            
    def load_model(self, model_name: str, file_path: str) -> bool:
        """
        加载3D模型
        
        Args:
            model_name: 模型名称
            file_path: 模型文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not self.is_initialized:
                logger.error("Renderer not initialized")
                return False
                
            if not os.path.exists(file_path):
                logger.error(f"Model file not found: {file_path}")
                return False
                
            # 使用Panda3D加载器加载模型
            model = self.showbase.loader.loadModel(file_path)
            if model is None:
                logger.error(f"Failed to load model: {file_path}")
                return False
                
            # 添加到场景图
            model.reparentTo(self.showbase.render)
            self.models[model_name] = model
            
            logger.info(f"Loaded model: {model_name} from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            return False
            
    def create_primitive(self, primitive_type: str, name: str, 
                        size: float = 1.0) -> bool:
        """
        创建基本几何体
        
        Args:
            primitive_type: 几何体类型 (cube, sphere, plane)
            name: 几何体名称
            size: 尺寸
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if not self.is_initialized:
                return False
                
            if primitive_type == "cube":
                model = self.showbase.loader.loadModel("models/box")
            elif primitive_type == "sphere":
                model = self.showbase.loader.loadModel("models/sphere")
            elif primitive_type == "plane":
                model = self.showbase.loader.loadModel("models/plane")
            else:
                logger.error(f"Unknown primitive type: {primitive_type}")
                return False
                
            if model is None:
                # 如果标准模型不存在，使用CardMaker创建平面
                if primitive_type == "plane":
                    card_maker = CardMaker("plane")
                    card_maker.setFrame(-size, size, -size, size)
                    model = self.showbase.render.attachNewNode(card_maker.generate())
                else:
                    logger.error(f"Failed to create primitive: {primitive_type}")
                    return False
                    
            model.setScale(size)
            model.reparentTo(self.showbase.render)
            self.models[name] = model
            
            logger.info(f"Created primitive: {name} ({primitive_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create primitive {name}: {str(e)}")
            return False
            
    def set_model_position(self, model_name: str, 
                          position: Tuple[float, float, float]) -> bool:
        """
        设置模型位置
        
        Args:
            model_name: 模型名称
            position: 位置坐标 (x, y, z)
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if model_name not in self.models:
                return False
                
            self.models[model_name].setPos(*position)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set position for {model_name}: {str(e)}")
            return False
            
    def set_model_rotation(self, model_name: str, 
                          rotation: Tuple[float, float, float]) -> bool:
        """
        设置模型旋转
        
        Args:
            model_name: 模型名称
            rotation: 旋转角度 (h, p, r)
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if model_name not in self.models:
                return False
                
            self.models[model_name].setHpr(*rotation)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set rotation for {model_name}: {str(e)}")
            return False
            
    def set_model_scale(self, model_name: str, 
                       scale: Tuple[float, float, float]) -> bool:
        """
        设置模型缩放
        
        Args:
            model_name: 模型名称
            scale: 缩放比例 (x, y, z)
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if model_name not in self.models:
                return False
                
            self.models[model_name].setScale(*scale)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set scale for {model_name}: {str(e)}")
            return False
            
    def load_texture(self, texture_name: str, file_path: str) -> Optional[Texture]:
        """
        加载纹理
        
        Args:
            texture_name: 纹理名称
            file_path: 纹理文件路径
            
        Returns:
            Optional[Texture]: 加载的纹理对象
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Texture file not found: {file_path}")
                return None
                
            texture = self.showbase.loader.loadTexture(file_path)
            if texture is None:
                logger.error(f"Failed to load texture: {file_path}")
                return None
                
            logger.info(f"Loaded texture: {texture_name} from {file_path}")
            return texture
            
        except Exception as e:
            logger.error(f"Failed to load texture {texture_name}: {str(e)}")
            return None
            
    def apply_texture(self, model_name: str, texture: Texture) -> bool:
        """
        为模型应用纹理
        
        Args:
            model_name: 模型名称
            texture: 纹理对象
            
        Returns:
            bool: 是否应用成功
        """
        try:
            if model_name not in self.models:
                return False
                
            self.models[model_name].setTexture(texture, 1)
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply texture to {model_name}: {str(e)}")
            return False
            
    def load_shader(self, shader_name: str, vertex_path: str, 
                   fragment_path: str) -> bool:
        """
        加载着色器
        
        Args:
            shader_name: 着色器名称
            vertex_path: 顶点着色器文件路径
            fragment_path: 片段着色器文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if not os.path.exists(vertex_path) or not os.path.exists(fragment_path):
                logger.error("Shader files not found")
                return False
                
            shader = Shader.load(Shader.SL_GLSL, vertex_path, fragment_path)
            if shader is None:
                logger.error("Failed to load shader")
                return False
                
            self.shaders[shader_name] = shader
            logger.info(f"Loaded shader: {shader_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load shader {shader_name}: {str(e)}")
            return False
            
    def apply_shader(self, model_name: str, shader_name: str) -> bool:
        """
        为模型应用着色器
        
        Args:
            model_name: 模型名称
            shader_name: 着色器名称
            
        Returns:
            bool: 是否应用成功
        """
        try:
            if model_name not in self.models or shader_name not in self.shaders:
                return False
                
            self.models[model_name].setShader(self.shaders[shader_name])
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply shader {shader_name} to {model_name}: {str(e)}")
            return False
            
    def create_animation_control(self, model_name: str) -> bool:
        """
        为模型创建动画控制
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if model_name not in self.models:
                return False
                
            model = self.models[model_name]
            
            # 检查模型是否有动画
            if model.getNumAnimControls() > 0:
                anim_control = model.getAnimControl(0)
                self.animations[model_name] = anim_control
                logger.info(f"Created animation control for {model_name}")
                return True
            else:
                logger.warning(f"No animations found for {model_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create animation control for {model_name}: {str(e)}")
            return False
            
    def play_animation(self, model_name: str, anim_name: str = None, 
                      from_frame: int = 0, to_frame: int = None, 
                      loop: bool = True) -> bool:
        """
        播放模型动画
        
        Args:
            model_name: 模型名称
            anim_name: 动画名称（可选）
            from_frame: 开始帧
            to_frame: 结束帧
            loop: 是否循环播放
            
        Returns:
            bool: 是否播放成功
        """
        try:
            if model_name not in self.animations:
                return False
                
            anim_control = self.animations[model_name]
            
            if to_frame is None:
                to_frame = anim_control.getNumFrames() - 1
                
            anim_control.play(from_frame, to_frame, loop)
            logger.info(f"Playing animation for {model_name} (frames {from_frame}-{to_frame})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to play animation for {model_name}: {str(e)}")
            return False
            
    def stop_animation(self, model_name: str) -> bool:
        """
        停止动画播放
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 是否停止成功
        """
        try:
            if model_name not in self.animations:
                return False
                
            self.animations[model_name].stop()
            logger.info(f"Stopped animation for {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop animation for {model_name}: {str(e)}")
            return False
            
    def run(self):
        """运行渲染循环"""
        try:
            if self.is_initialized:
                self.showbase.run()
            else:
                logger.error("Renderer not initialized")
        except Exception as e:
            logger.error(f"Error in render loop: {str(e)}")
            
    def shutdown(self):
        """关闭渲染器"""
        try:
            if self.showbase:
                self.showbase.destroy()
            self.is_initialized = False
            logger.info("Panda3D renderer shutdown")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")

