"""
计算机视觉输入系统
提供完整的多模态视觉感知能力，包括人脸识别、情绪检测、手势识别、姿态估计等
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(__file__))

# 配置日志
logger = logging.getLogger(__name__)

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "多模态计算机视觉输入系统"

# 导入子模块
try:
    from .face_recognition import FaceRecognition, face_recognition_system
    from .emotion_detection import EmotionRecognition
    from .gesture_recognizer import GestureRecognition
    from .pose_estimation import PoseEstimation
    from .gaze_tracker import GazeTracker
    from .object_interaction import ObjectInteraction
    from .scene_analyzer import SceneAnalyzer
    from .motion_detector import MotionDetector
    from .vision_metrics import VisionMetrics
    
    # 标记模块可用性
    FACE_RECOGNITION_AVAILABLE = True
    EMOTION_DETECTION_AVAILABLE = True
    GESTURE_RECOGNITION_AVAILABLE = True
    POSE_ESTIMATION_AVAILABLE = True
    GAZE_TRACKING_AVAILABLE = True
    OBJECT_INTERACTION_AVAILABLE = True
    SCENE_ANALYSIS_AVAILABLE = True
    MOTION_DETECTION_AVAILABLE = True
    VISION_METRICS_AVAILABLE = True
    
except ImportError as e:
    logger.warning(f"部分计算机视觉模块导入失败: {e}")
    # 设置模块可用性标志
    FACE_RECOGNITION_AVAILABLE = False
    EMOTION_DETECTION_AVAILABLE = False
    GESTURE_RECOGNITION_AVAILABLE = False
    POSE_ESTIMATION_AVAILABLE = False
    GAZE_TRACKING_AVAILABLE = False
    OBJECT_INTERACTION_AVAILABLE = False
    SCENE_ANALYSIS_AVAILABLE = False
    MOTION_DETECTION_AVAILABLE = False
    VISION_METRICS_AVAILABLE = False

class ComputerVisionSystem:
    """计算机视觉系统管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 子系统实例
        self.face_recognition = None
        self.emotion_detection = None
        self.gesture_recognition = None
        self.pose_estimation = None
        self.gaze_tracker = None
        self.object_interaction = None
        self.scene_analyzer = None
        self.motion_detector = None
        self.vision_metrics = None
        
        # 系统状态
        self.is_initialized = False
        self.initialization_progress = 0.0
        self.active_modules = set()
        
        # 性能配置
        self.enable_gpu_acceleration = self.config.get('enable_gpu_acceleration', True)
        self.enable_real_time_processing = self.config.get('enable_real_time_processing', True)
        self.max_processing_fps = self.config.get('max_processing_fps', 30)
        
        self.logger.info("计算机视觉系统初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化计算机视觉系统"""
        try:
            self.logger.info("正在初始化计算机视觉系统...")
            
            # 初始化各个子系统
            modules_to_init = [
                ('face_recognition', self._init_face_recognition),
                ('emotion_detection', self._init_emotion_detection),
                ('gesture_recognition', self._init_gesture_recognition),
                ('pose_estimation', self._init_pose_estimation),
                ('gaze_tracker', self._init_gaze_tracker),
                ('object_interaction', self._init_object_interaction),
                ('scene_analyzer', self._init_scene_analyzer),
                ('motion_detector', self._init_motion_detector),
                ('vision_metrics', self._init_vision_metrics)
            ]
            
            total_modules = len(modules_to_init)
            
            for i, (module_name, init_func) in enumerate(modules_to_init):
                self.logger.info(f"正在初始化 {module_name}...")
                
                try:
                    success = await init_func()
                    if success:
                        self.active_modules.add(module_name)
                        self.logger.info(f"{module_name} 初始化成功")
                    else:
                        self.logger.warning(f"{module_name} 初始化失败")
                except Exception as e:
                    self.logger.error(f"{module_name} 初始化错误: {e}")
                
                # 更新进度
                self.initialization_progress = (i + 1) / total_modules
            
            self.is_initialized = True
            self.logger.info(f"计算机视觉系统初始化完成，激活模块: {len(self.active_modules)}/{total_modules}")
            
            return len(self.active_modules) > 0
            
        except Exception as e:
            self.logger.error(f"计算机视觉系统初始化失败: {e}")
            return False
    
    async def _init_face_recognition(self) -> bool:
        """初始化人脸识别系统"""
        if not FACE_RECOGNITION_AVAILABLE:
            return False
        
        try:
            self.face_recognition = FaceRecognition(self.config.get('face_recognition', {}))
            return await self.face_recognition.initialize()
        except Exception as e:
            self.logger.error(f"人脸识别系统初始化失败: {e}")
            return False
    
    async def _init_emotion_detection(self) -> bool:
        """初始化情绪检测系统"""
        if not EMOTION_DETECTION_AVAILABLE:
            return False
        
        try:
            self.emotion_detection = EmotionRecognition(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.emotion_detection.load()
        except Exception as e:
            self.logger.error(f"情绪检测系统初始化失败: {e}")
            return False
    
    async def _init_gesture_recognition(self) -> bool:
        """初始化手势识别系统"""
        if not GESTURE_RECOGNITION_AVAILABLE:
            return False
        
        try:
            self.gesture_recognition = GestureRecognition(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.gesture_recognition.load()
        except Exception as e:
            self.logger.error(f"手势识别系统初始化失败: {e}")
            return False
    
    async def _init_pose_estimation(self) -> bool:
        """初始化姿态估计系统"""
        if not POSE_ESTIMATION_AVAILABLE:
            return False
        
        try:
            self.pose_estimation = PoseEstimation(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.pose_estimation.load()
        except Exception as e:
            self.logger.error(f"姿态估计系统初始化失败: {e}")
            return False
    
    async def _init_gaze_tracker(self) -> bool:
        """初始化视线追踪系统"""
        if not GAZE_TRACKING_AVAILABLE:
            return False
        
        try:
            self.gaze_tracker = GazeTracker(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.gaze_tracker.load()
        except Exception as e:
            self.logger.error(f"视线追踪系统初始化失败: {e}")
            return False
    
    async def _init_object_interaction(self) -> bool:
        """初始化物体交互检测系统"""
        if not OBJECT_INTERACTION_AVAILABLE:
            return False
        
        try:
            self.object_interaction = ObjectInteraction(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.object_interaction.load()
        except Exception as e:
            self.logger.error(f"物体交互检测系统初始化失败: {e}")
            return False
    
    async def _init_scene_analyzer(self) -> bool:
        """初始化场景分析系统"""
        if not SCENE_ANALYSIS_AVAILABLE:
            return False
        
        try:
            self.scene_analyzer = SceneAnalyzer(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.scene_analyzer.load()
        except Exception as e:
            self.logger.error(f"场景分析系统初始化失败: {e}")
            return False
    
    async def _init_motion_detector(self) -> bool:
        """初始化运动检测系统"""
        if not MOTION_DETECTION_AVAILABLE:
            return False
        
        try:
            self.motion_detector = MotionDetector(
                use_gpu=self.enable_gpu_acceleration
            )
            return self.motion_detector.load()
        except Exception as e:
            self.logger.error(f"运动检测系统初始化失败: {e}")
            return False
    
    async def _init_vision_metrics(self) -> bool:
        """初始化视觉指标系统"""
        if not VISION_METRICS_AVAILABLE:
            return False
        
        try:
            self.vision_metrics = VisionMetrics()
            return True
        except Exception as e:
            self.logger.error(f"视觉指标系统初始化失败: {e}")
            return False
    
    async def process_frame(self, image, analysis_types: List[str] = None) -> Dict[str, Any]:
        """
        处理单帧图像，执行指定的视觉分析
        
        Args:
            image: 输入图像
            analysis_types: 分析类型列表，如果为None则执行所有可用分析
            
        Returns:
            分析结果字典
        """
        if not self.is_initialized:
            success = await self.initialize()
            if not success:
                return self._create_error_result("系统未初始化")
        
        if analysis_types is None:
            analysis_types = list(self.active_modules)
        
        results = {}
        
        try:
            # 并行执行各种视觉分析
            for analysis_type in analysis_types:
                if analysis_type not in self.active_modules:
                    continue
                
                try:
                    if analysis_type == 'face_recognition' and self.face_recognition:
                        results['face_recognition'] = await self.face_recognition.process_frame(image)
                    
                    elif analysis_type == 'emotion_detection' and self.emotion_detection:
                        # 如果有面部检测结果，优先使用
                        if 'face_recognition' in results:
                            faces = results['face_recognition'].get('faces', [])
                            emotion_results = []
                            for face in faces:
                                emotion_result = self.emotion_detection.recognize(
                                    image, face.bbox
                                )
                                emotion_results.append(emotion_result)
                            results['emotion_detection'] = emotion_results
                        else:
                            results['emotion_detection'] = self.emotion_detection.recognize(image)
                    
                    elif analysis_type == 'gesture_recognition' and self.gesture_recognition:
                        results['gesture_recognition'] = self.gesture_recognition.recognize(image)
                    
                    elif analysis_type == 'pose_estimation' and self.pose_estimation:
                        results['pose_estimation'] = self.pose_estimation.estimate(image)
                    
                    elif analysis_type == 'gaze_tracking' and self.gaze_tracker:
                        # 如果有面部检测结果，优先使用
                        if 'face_recognition' in results:
                            faces = results['face_recognition'].get('faces', [])
                            gaze_results = []
                            for face in faces:
                                gaze_result = self.gaze_tracker.track(
                                    image, face.bbox, face.landmarks
                                )
                                gaze_results.append(gaze_result)
                            results['gaze_tracking'] = gaze_results
                        else:
                            results['gaze_tracking'] = self.gaze_tracker.track(image)
                    
                    elif analysis_type == 'object_interaction' and self.object_interaction:
                        results['object_interaction'] = self.object_interaction.detect(image)
                    
                    elif analysis_type == 'scene_analysis' and self.scene_analyzer:
                        results['scene_analysis'] = self.scene_analyzer.analyze(image)
                    
                    elif analysis_type == 'motion_detection' and self.motion_detector:
                        results['motion_detection'] = self.motion_detector.detect(image)
                    
                except Exception as e:
                    self.logger.error(f"{analysis_type} 分析失败: {e}")
                    results[analysis_type] = self._create_module_error_result(analysis_type, str(e))
            
            # 计算视觉指标
            if self.vision_metrics:
                results['vision_metrics'] = self.vision_metrics.calculate_metrics(results)
            
            results['success'] = True
            results['processed_modules'] = list(results.keys())
            
            return results
            
        except Exception as e:
            self.logger.error(f"视觉分析处理失败: {e}")
            return self._create_error_result(str(e))
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'initialized': self.is_initialized,
            'initialization_progress': self.initialization_progress,
            'active_modules': list(self.active_modules),
            'total_modules': 9,  # 总模块数
            'gpu_acceleration': self.enable_gpu_acceleration,
            'real_time_processing': self.enable_real_time_processing,
            'max_processing_fps': self.max_processing_fps
        }
    
    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """获取指定模块信息"""
        module_map = {
            'face_recognition': self.face_recognition,
            'emotion_detection': self.emotion_detection,
            'gesture_recognition': self.gesture_recognition,
            'pose_estimation': self.pose_estimation,
            'gaze_tracking': self.gaze_tracker,
            'object_interaction': self.object_interaction,
            'scene_analysis': self.scene_analyzer,
            'motion_detection': self.motion_detector,
            'vision_metrics': self.vision_metrics
        }
        
        module = module_map.get(module_name)
        if module and hasattr(module, 'get_model_info'):
            return module.get_model_info()
        else:
            return {'available': module is not None}
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'error': error_message,
            'processed_modules': []
        }
    
    def _create_module_error_result(self, module_name: str, error_message: str) -> Dict[str, Any]:
        """创建模块错误结果"""
        return {
            'success': False,
            'error': error_message,
            'module': module_name
        }
    
    async def shutdown(self):
        """关闭计算机视觉系统"""
        self.logger.info("正在关闭计算机视觉系统...")
        
        # 清理资源
        self.is_initialized = False
        self.active_modules.clear()
        
        # 这里可以添加各个模块的清理逻辑
        self.logger.info("计算机视觉系统已关闭")

# 全局计算机视觉系统实例
computer_vision_system = ComputerVisionSystem()

# 便捷导入
def get_computer_vision_system() -> ComputerVisionSystem:
    """获取计算机视觉系统实例"""
    return computer_vision_system

# 包级别功能函数
async def initialize_computer_vision(config: Dict[str, Any] = None) -> bool:
    """初始化计算机视觉系统"""
    global computer_vision_system
    computer_vision_system = ComputerVisionSystem(config)
    return await computer_vision_system.initialize()

async def process_image(image, analysis_types: List[str] = None) -> Dict[str, Any]:
    """处理图像（便捷函数）"""
    return await computer_vision_system.process_frame(image, analysis_types)

def get_vision_system_status() -> Dict[str, Any]:
    """获取视觉系统状态（便捷函数）"""
    return computer_vision_system.get_system_status()

# 导出主要类和方法
__all__ = [
    'ComputerVisionSystem',
    'computer_vision_system',
    'get_computer_vision_system',
    'initialize_computer_vision',
    'process_image',
    'get_vision_system_status',
    
    # 子模块
    'FaceRecognition',
    'EmotionRecognition',
    'GestureRecognition',
    'PoseEstimation',
    'GazeTracker',
    'ObjectInteraction',
    'SceneAnalyzer',
    'MotionDetector',
    'VisionMetrics',
    
    # 模块可用性标志
    'FACE_RECOGNITION_AVAILABLE',
    'EMOTION_DETECTION_AVAILABLE',
    'GESTURE_RECOGNITION_AVAILABLE',
    'POSE_ESTIMATION_AVAILABLE',
    'GAZE_TRACKING_AVAILABLE',
    'OBJECT_INTERACTION_AVAILABLE',
    'SCENE_ANALYSIS_AVAILABLE',
    'MOTION_DETECTION_AVAILABLE',
    'VISION_METRICS_AVAILABLE'
]

# 包初始化信息
logger.info(f"计算机视觉输入系统 v{__version__} 已加载")
logger.info(f"描述: {__description__}")
