"""
语音模型模块 - 语音识别、语音合成、唤醒词检测等语音相关模型

包含中英文语音识别、多语言支持、语音增强等功能
"""

from __future__ import annotations

from typing import Any

__all__ = ["SpeechModelManager"]

class SpeechModelManager:
    """语音模型管理器"""
    
    def __init__(self):
        self.asr_models = {}
        self.tts_models = {}
        self.wake_word_models = {}
        self.initialized = False
        
    def initialize(self):
        """初始化语音模型"""
        from .asr import ChineseASRModel, EnglishASRModel, WhisperIntegration, MultilingualASR, SpeechEnhancement
        
        # 初始化ASR模型
        self.asr_models['chinese'] = ChineseASRModel()
        self.asr_models['english'] = EnglishASRModel() 
        self.asr_models['whisper'] = WhisperIntegration()
        self.asr_models['multilingual'] = MultilingualASR()
        
        # 初始化语音增强
        self.speech_enhancement = SpeechEnhancement()
        
        self.initialized = True
        print("✅ 语音模型管理器初始化完成")
        
    def transcribe_audio(self, audio_data, language='auto'):
        """语音识别主入口"""
        if not self.initialized:
            self.initialize()
            
        # 根据语言选择模型
        if language == 'zh' or language == 'chinese':
            model = self.asr_models['chinese']
        elif language == 'en' or language == 'english':
            model = self.asr_models['english'] 
        else:
            # 使用多语言或Whisper模型
            model = self.asr_models['whisper']
            
        # 应用语音增强
        enhanced_audio = self.speech_enhancement.enhance(audio_data)
        
        # 进行语音识别
        return model.transcribe(enhanced_audio)
    
    def get_supported_languages(self):
        """获取支持的语言列表"""
        return {
            'chinese': '中文',
            'english': '英文', 
            'multilingual': '多语言 (Whisper)'
        }
    
    def get_model_status(self):
        """获取模型状态"""
        status = {}
        for name, model in self.asr_models.items():
            status[name] = {
                'loaded': model.is_loaded(),
                'language': getattr(model, 'language', 'unknown'),
                'version': getattr(model, 'version', '1.0.0')
            }
        return status


def __getattr__(name: str) -> Any:
    """
    懒加载导出（避免包导入时触发重依赖/可选依赖错误）。

    示例：`from data.models.speech import ChineseASRModel`
    """
    if name in {"ChineseASRModel", "EnglishASRModel", "MultilingualASR", "WhisperIntegration", "SpeechEnhancement"}:
        from .asr import chinese_asr_model, english_asr_model, multilingual_asr, whisper_integration, speech_enhancement

        mapping = {
            "ChineseASRModel": chinese_asr_model.ChineseASRModel,
            "EnglishASRModel": english_asr_model.EnglishASRModel,
            "MultilingualASR": multilingual_asr.MultilingualASR,
            "WhisperIntegration": whisper_integration.WhisperIntegration,
            "SpeechEnhancement": speech_enhancement.SpeechEnhancement,
        }
        return mapping[name]

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
