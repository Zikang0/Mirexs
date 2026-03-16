"""
语音识别(ASR)模块 - 多语言语音转文本功能

包含中文、英文、多语言语音识别及语音增强功能
"""

from .chinese_asr_model import ChineseASRModel
from .english_asr_model import EnglishASRModel
from .multilingual_asr import MultilingualASR
from .whisper_integration import WhisperIntegration
from .speech_enhancement import SpeechEnhancement

__all__ = [
    "ChineseASRModel",
    "EnglishASRModel", 
    "MultilingualASR",
    "WhisperIntegration",
    "SpeechEnhancement"
]

class ASRModelFactory:
    """ASR模型工厂"""
    
    def __init__(self):
        self.models = {}
        
    def create_model(self, model_type: str, **kwargs):
        """创建ASR模型实例"""
        model_classes = {
            'chinese': ChineseASRModel,
            'english': EnglishASRModel,
            'multilingual': MultilingualASR,
            'whisper': WhisperIntegration
        }
        
        if model_type in model_classes:
            model = model_classes[model_type](**kwargs)
            self.models[model_type] = model
            return model
        else:
            raise ValueError(f"不支持的ASR模型类型: {model_type}")
    
    def get_model(self, model_type: str):
        """获取ASR模型"""
        return self.models.get(model_type)
    
    def auto_select_model(self, language: str = 'auto'):
        """根据语言自动选择模型"""
        language_map = {
            'zh': 'chinese',
            'zh-CN': 'chinese', 
            'zh-TW': 'chinese',
            'en': 'english',
            'en-US': 'english',
            'en-GB': 'english'
        }
        
        if language in language_map:
            return self.get_model(language_map[language])
        else:
            # 默认使用多语言模型
            return self.get_model('whisper') or self.get_model('multilingual')