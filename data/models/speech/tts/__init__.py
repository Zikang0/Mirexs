"""
语音合成(TTS)模块 - 多语言文本转语音功能

包含中英文语音合成、情感语音、语音克隆等功能
"""

from .chinese_tts_model import ChineseTTSModel
from .english_tts_model import EnglishTTSModel
from .emotional_tts import EmotionalTTS
from .voice_cloning import VoiceCloning
from .coqui_tts_integration import CoquiTTSIntegration
from .xtts_integration import XTTSIntegration

__all__ = [
    "ChineseTTSModel",
    "EnglishTTSModel",
    "EmotionalTTS", 
    "VoiceCloning",
    "CoquiTTSIntegration",
    "XTTSIntegration"
]

class TTSModelManager:
    """语音合成模型管理器"""
    
    def __init__(self):
        self.tts_models = {}
        self.voice_cloning = None
        self.emotional_tts = None
        self.initialized = False
        
    def initialize(self):
        """初始化所有TTS模型"""
        # 初始化基础TTS模型
        self.tts_models['chinese'] = ChineseTTSModel()
        self.tts_models['english'] = EnglishTTSModel()
        
        # 初始化高级功能
        self.emotional_tts = EmotionalTTS()
        self.voice_cloning = VoiceCloning()
        
        # 初始化集成模型
        self.tts_models['coqui'] = CoquiTTSIntegration()
        self.tts_models['xtts'] = XTTSIntegration()
        
        # 加载模型
        for name, model in self.tts_models.items():
            if hasattr(model, 'load'):
                model.load()
        
        self.initialized = True
        print("✅ 语音合成管理器初始化完成")
        
    def synthesize(self, text: str, language: str = 'auto', 
                  voice_id: str = None, emotion: str = None, 
                  speed: float = 1.0, **kwargs) -> dict:
        """语音合成主入口"""
        if not self.initialized:
            self.initialize()
            
        # 自动检测语言
        if language == 'auto':
            language = self._detect_language(text)
            
        # 选择模型
        if language in ['zh', 'chinese']:
            model = self.tts_models['chinese']
        elif language in ['en', 'english']:
            model = self.tts_models['english']
        else:
            # 默认使用多语言模型
            model = self.tts_models['coqui'] or self.tts_models['xtts']
            
        # 情感语音合成
        if emotion and self.emotional_tts:
            return self.emotional_tts.synthesize(text, emotion, language, speed)
            
        # 语音克隆
        if voice_id and self.voice_cloning:
            return self.voice_cloning.synthesize(text, voice_id, language, speed)
            
        # 基础语音合成
        return model.synthesize(text, speed=speed, **kwargs)
    
    def _detect_language(self, text: str) -> str:
        """简单语言检测"""
        import re
        
        # 中文检测
        if re.search(r'[\u4e00-\u9fff]', text):
            return 'zh'
        # 英文检测
        elif re.search(r'[a-zA-Z]', text):
            return 'en'
        else:
            return 'en'  # 默认英文
    
    def get_available_voices(self, language: str = None) -> list:
        """获取可用声音列表"""
        voices = []
        
        for model_name, model in self.tts_models.items():
            if hasattr(model, 'get_available_voices'):
                model_voices = model.get_available_voices()
                if language:
                    model_voices = [v for v in model_voices if v.get('language') == language]
                voices.extend(model_voices)
                
        return voices
    
    def get_model_status(self) -> dict:
        """获取模型状态"""
        status = {}
        
        for name, model in self.tts_models.items():
            status[name] = {
                'loaded': getattr(model, 'is_loaded', lambda: False)(),
                'language': getattr(model, 'language', 'unknown'),
                'voices': len(getattr(model, 'get_available_voices', lambda: [])())
            }
            
        return status