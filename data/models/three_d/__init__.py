"""
Mirexs 3D模型系统
提供完整的3D模型管理、渲染和优化功能
"""

from .cat_models import CatModelManager, CatModel, ModelConfig
from .animations import AnimationManager, AnimationClip, AnimationController
from .textures import TextureManager, TextureInfo, MaterialInfo
from .rigging_system import RiggingSystem, Bone, BoneConstraint
from .blend_shapes import BlendShapeSystem, BlendShape, ExpressionPreset
from .panda3d_integration import Panda3DRenderer
from .blender_exporter import BlenderExporter
from .model_optimizer import ModelOptimizer, OptimizationSettings, LODLevel

__all__ = [
    # 猫咪模型管理
    'CatModelManager',
    'CatModel', 
    'ModelConfig',
    
    # 动画系统
    'AnimationManager',
    'AnimationClip',
    'AnimationController',
    
    # 纹理材质系统
    'TextureManager',
    'TextureInfo', 
    'MaterialInfo',
    
    # 骨骼绑定系统
    'RiggingSystem',
    'Bone',
    'BoneConstraint',
    
    # 混合形状系统
    'BlendShapeSystem',
    'BlendShape',
    'ExpressionPreset',
    
    # 渲染引擎集成
    'Panda3DRenderer',
    
    # 导出工具
    'BlenderExporter',
    
    # 优化工具
    'ModelOptimizer',
    'OptimizationSettings', 
    'LODLevel'
]

# 包版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "3D Model Management System for Mirexs AI Agent"

# 初始化日志配置
import logging

def setup_logging(level=logging.INFO):
    """设置日志配置"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('3d_models.log')
        ]
    )

# 包初始化时自动设置日志
setup_logging()

logger = logging.getLogger(__name__)
logger.info(f"Mirexs 3D Model System v{__version__} initialized")

class Mirexs3DSystem:
    """Mirexs 3D系统主类 - 提供统一的3D功能接口"""
    
    def __init__(self):
        self.model_manager = CatModelManager()
        self.animation_manager = AnimationManager()
        self.texture_manager = TextureManager()
        self.rigging_system = RiggingSystem()
        self.blend_shape_system = None
        self.renderer = None
        self.exporter = BlenderExporter()
        self.optimizer = ModelOptimizer()
        
    def initialize_renderer(self, window_title: str = "Mirexs 3D", 
                          window_size: Tuple[int, int] = (1280, 720)) -> bool:
        """
        初始化3D渲染器
        
        Args:
            window_title: 窗口标题
            window_size: 窗口尺寸
            
        Returns:
            bool: 是否初始化成功
        """
        try:
            self.renderer = Panda3DRenderer(window_title, window_size)
            success = self.renderer.initialize()
            
            if success:
                logger.info("3D renderer initialized successfully")
            else:
                logger.error("Failed to initialize 3D renderer")
                
            return success
            
        except Exception as e:
            logger.error(f"Error initializing 3D renderer: {str(e)}")
            return False
            
    def load_cat_model(self, model_name: str, config_path: str) -> bool:
        """
        加载猫咪模型
        
        Args:
            model_name: 模型名称
            config_path: 配置文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            success = self.model_manager.load_model(model_name, config_path)
            
            if success and self.renderer:
                # 在渲染器中加载模型
                model_config = self.model_manager.models[model_name]
                render_success = self.renderer.load_model(
                    model_name, model_config.mesh_path)
                    
                if render_success:
                    logger.info(f"Cat model {model_name} loaded in renderer")
                else:
                    logger.warning(f"Cat model {model_name} loaded but failed in renderer")
                    
            return success
            
        except Exception as e:
            logger.error(f"Error loading cat model {model_name}: {str(e)}")
            return False
            
    def setup_blend_shapes(self, base_vertices: np.ndarray, 
                          base_normals: np.ndarray) -> bool:
        """
        设置混合形状系统
        
        Args:
            base_vertices: 基础顶点
            base_normals: 基础法线
            
        Returns:
            bool: 是否设置成功
        """
        try:
            self.blend_shape_system = BlendShapeSystem(base_vertices, base_normals)
            logger.info("Blend shape system initialized")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up blend shapes: {str(e)}")
            return False
            
    def play_animation(self, model_name: str, animation_name: str) -> bool:
        """
        播放动画
        
        Args:
            model_name: 模型名称
            animation_name: 动画名称
            
        Returns:
            bool: 是否播放成功
        """
        try:
            # 通过动画管理器控制
            animation_success = self.animation_manager.play_animation(
                model_name, animation_name)
                
            # 通过渲染器播放
            render_success = False
            if self.renderer:
                render_success = self.renderer.play_animation(model_name, animation_name)
                
            return animation_success and render_success
            
        except Exception as e:
            logger.error(f"Error playing animation {animation_name}: {str(e)}")
            return False
            
    def export_model(self, model_name: str, export_path: str, 
                    format_type: str = 'gltf') -> bool:
        """
        导出模型
        
        Args:
            model_name: 模型名称
            export_path: 导出路径
            format_type: 导出格式
            
        Returns:
            bool: 是否导出成功
        """
        try:
            success = self.exporter.export_selected_objects(export_path, format_type)
            
            if success:
                logger.info(f"Exported model {model_name} to {export_path}")
            else:
                logger.error(f"Failed to export model {model_name}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error exporting model {model_name}: {str(e)}")
            return False
            
    def optimize_model(self, model_name: str) -> Dict[str, Any]:
        """
        优化模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            Dict[str, Any]: 优化报告
        """
        try:
            if model_name not in self.model_manager.models:
                logger.error(f"Model {model_name} not found")
                return {}
                
            model = self.model_manager.models[model_name]
            
            # 优化网格
            optimized_vertices, optimized_indices = self.optimizer.optimize_mesh(
                model.vertices, model.indices, model_name)
                
            # 生成LOD级别
            lod_levels = self.optimizer.generate_lod_levels(
                optimized_vertices, optimized_indices, model_name)
                
            # 生成优化报告
            report = self.optimizer.generate_optimization_report(model_name)
            
            logger.info(f"Optimized model {model_name}")
            return report
            
        except Exception as e:
            logger.error(f"Error optimizing model {model_name}: {str(e)}")
            return {}
            
    def shutdown(self):
        """关闭3D系统"""
        try:
            if self.renderer:
                self.renderer.shutdown()
                
            logger.info("Mirexs 3D System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during 3D system shutdown: {str(e)}")

# 创建全局实例
system = Mirexs3DSystem()

# 便捷函数
def get_3d_system() -> Mirexs3DSystem:
    """获取3D系统实例"""
    return system

def initialize_3d_system(window_title: str = "Mirexs 3D", 
                        window_size: Tuple[int, int] = (1280, 720)) -> bool:
    """初始化3D系统"""
    return system.initialize_renderer(window_title, window_size)

def load_model(model_name: str, config_path: str) -> bool:
    """加载模型"""
    return system.load_cat_model(model_name, config_path)

def play_animation(model_name: str, animation_name: str) -> bool:
    """播放动画"""
    return system.play_animation(model_name, animation_name)

# 模块导入完成
logger.info("Mirexs 3D Model package imported successfully")
