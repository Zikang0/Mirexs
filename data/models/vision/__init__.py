"""
视觉模型模块 - 计算机视觉相关模型管理

包含人脸检测、情绪识别、手势识别、物体检测、场景理解等功能
"""

from .face_detection import FaceDetection
from .emotion_recognition import EmotionRecognition
from .gesture_recognition import GestureRecognition
from .object_detection import ObjectDetection
from .scene_understanding import SceneUnderstanding
from .insightface_integration import InsightFaceIntegration
from .mediapipe_integration import MediaPipeIntegration
from .opencv_utils import OpenCVUtils

__all__ = [
    "FaceDetection",
    "EmotionRecognition", 
    "GestureRecognition",
    "ObjectDetection",
    "SceneUnderstanding",
    "InsightFaceIntegration",
    "MediaPipeIntegration",
    "OpenCVUtils"
]

class VisionModelManager:
    """视觉模型管理器"""
    
    def __init__(self):
        self.face_detection = None
        self.emotion_recognition = None
        self.gesture_recognition = None
        self.object_detection = None
        self.scene_understanding = None
        self.insightface = None
        self.mediapipe = None
        self.opencv_utils = None
        self.initialized = False
        
    def initialize(self, use_gpu: bool = True):
        """初始化所有视觉模型"""
        print("🔍 正在初始化视觉模型...")
        
        # 初始化工具类
        self.opencv_utils = OpenCVUtils()
        
        # 初始化基础模型
        self.face_detection = FaceDetection(use_gpu=use_gpu)
        self.emotion_recognition = EmotionRecognition(use_gpu=use_gpu)
        self.gesture_recognition = GestureRecognition(use_gpu=use_gpu)
        self.object_detection = ObjectDetection(use_gpu=use_gpu)
        self.scene_understanding = SceneUnderstanding(use_gpu=use_gpu)
        
        # 初始化集成模型
        self.insightface = InsightFaceIntegration(use_gpu=use_gpu)
        self.mediapipe = MediaPipeIntegration()
        
        # 加载模型
        models_to_load = [
            (self.face_detection, "人脸检测"),
            (self.emotion_recognition, "情绪识别"),
            (self.gesture_recognition, "手势识别"), 
            (self.object_detection, "物体检测"),
            (self.scene_understanding, "场景理解"),
            (self.insightface, "InsightFace"),
            (self.mediapipe, "MediaPipe")
        ]
        
        for model, name in models_to_load:
            if hasattr(model, 'load'):
                success = model.load()
                if success:
                    print(f"✅ {name}模型加载成功")
                else:
                    print(f"❌ {name}模型加载失败")
        
        self.initialized = True
        print("✅ 视觉模型管理器初始化完成")
        
    def process_image(self, image, tasks: list = None) -> dict:
        """处理图像（执行多个视觉任务）"""
        if not self.initialized:
            self.initialize()
            
        if tasks is None:
            tasks = ['face_detection', 'emotion', 'objects', 'scene']
            
        results = {}
        
        try:
            # 人脸检测和情绪识别
            if 'face_detection' in tasks or 'emotion' in tasks:
                face_results = self.face_detection.detect(image)
                results['faces'] = face_results
                
                if 'emotion' in tasks and face_results['success']:
                    for face in face_results['faces']:
                        emotion_result = self.emotion_recognition.recognize(
                            face['cropped_face'] if 'cropped_face' in face else image,
                            face['bbox'] if 'bbox' in face else None
                        )
                        face['emotion'] = emotion_result
            
            # 物体检测
            if 'objects' in tasks:
                object_results = self.object_detection.detect(image)
                results['objects'] = object_results
            
            # 场景理解
            if 'scene' in tasks:
                scene_results = self.scene_understanding.analyze(image)
                results['scene'] = scene_results
            
            # 手势识别
            if 'gesture' in tasks:
                gesture_results = self.gesture_recognition.recognize(image)
                results['gestures'] = gesture_results
                
            results['success'] = True
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            
        return results
    
    def get_model_status(self) -> dict:
        """获取所有模型状态"""
        models = {
            'face_detection': self.face_detection,
            'emotion_recognition': self.emotion_recognition,
            'gesture_recognition': self.gesture_recognition,
            'object_detection': self.object_detection, 
            'scene_understanding': self.scene_understanding,
            'insightface': self.insightface,
            'mediapipe': self.mediapipe
        }
        
        status = {}
        for name, model in models.items():
            if model and hasattr(model, 'is_loaded'):
                status[name] = {
                    'loaded': model.is_loaded(),
                    'version': getattr(model, 'version', 'unknown'),
                    'description': getattr(model, 'model_name', 'unknown')
                }
                
        return status
    
    def get_available_tasks(self) -> list:
        """获取可用的视觉任务"""
        return [
            {'task': 'face_detection', 'name': '人脸检测', 'description': '检测和定位图像中的人脸'},
            {'task': 'emotion_recognition', 'name': '情绪识别', 'description': '识别人脸的情绪状态'},
            {'task': 'gesture_recognition', 'name': '手势识别', 'description': '识别手部姿势和手势'},
            {'task': 'object_detection', 'name': '物体检测', 'description': '检测和识别常见物体'},
            {'task': 'scene_understanding', 'name': '场景理解', 'description': '理解图像场景内容'},
            {'task': 'face_recognition', 'name': '人脸识别', 'description': '识别特定人物身份'},
            {'task': 'pose_estimation', 'name': '姿态估计', 'description': '估计人体关键点'}
        ]