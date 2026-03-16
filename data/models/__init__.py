"""
AI模型存储模块 - 多模态模型管理与版本控制

包含语音、视觉、NLP、3D等各类AI模型的管理
"""

__all__ = ["ModelManager"]

class ModelManager:
    """AI模型管理器"""
    
    def __init__(self):
        self.speech_models = {}
        self.vision_models = {}
        self.nlp_models = {}
        self.three_d_models = {}
        self.model_cache = {}
        
    def initialize(self):
        """初始化所有模型"""
        from .speech.asr import ChineseASRModel, EnglishASRModel, WhisperIntegration
        from .vision import FaceDetection, EmotionRecognition
        
        # 初始化语音模型
        self.speech_models['chinese_asr'] = ChineseASRModel()
        self.speech_models['english_asr'] = EnglishASRModel()
        self.speech_models['whisper'] = WhisperIntegration()
        
        # 初始化视觉模型
        self.vision_models['face_detection'] = FaceDetection()
        self.vision_models['emotion_recognition'] = EmotionRecognition()
        
        print("✅ AI模型管理器初始化完成")
        
    def get_model(self, model_type: str, model_name: str):
        """获取指定模型"""
        model_map = {
            'speech': self.speech_models,
            'vision': self.vision_models, 
            'nlp': self.nlp_models,
            '3d': self.three_d_models
        }
        
        return model_map.get(model_type, {}).get(model_name)
    
    def preload_models(self, model_list: list):
        """预加载模型列表"""
        for model_info in model_list:
            model_type = model_info.get('type')
            model_name = model_info.get('name')
            
            if model_type and model_name:
                model = self.get_model(model_type, model_name)
                if model:
                    model.load()
                    print(f"📦 预加载模型: {model_type}/{model_name}")
    
    def get_model_info(self):
        """获取所有模型信息"""
        info = {
            'speech_models': list(self.speech_models.keys()),
            'vision_models': list(self.vision_models.keys()),
            'nlp_models': list(self.nlp_models.keys()),
            'three_d_models': list(self.three_d_models.keys())
        }
        return info
