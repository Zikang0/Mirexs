"""
多语言语音识别 - 支持多种语言的语音识别
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import time

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class MultilingualASR:
    """多语言语音识别模型"""
    
    def __init__(self):
        self.model_name = "MultilingualASR"
        self.language = "multilingual"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        # 支持的语言列表
        self.supported_languages = {
            'en': 'English',
            'zh': 'Chinese', 
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'ja': 'Japanese',
            'ko': 'Korean',
            'ru': 'Russian'
        }
        
        # 模型配置
        self.config = {
            'model_size': 'large',
            'use_gpu': True,
            'beam_size': 5,
            'language_detection': True,
            'vad_enabled': True
        }
        
    def load(self) -> bool:
        """加载多语言ASR模型"""
        try:
            if not TORCH_AVAILABLE:
                print("❌ PyTorch不可用，无法加载多语言ASR模型")
                return False
                
            # 尝试加载多语言语音识别模型
            try:
                from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
                
                model_name = "openai/whisper-large"  # 或其他多语言模型
                self.processor = AutoProcessor.from_pretrained(model_name)
                self.model = AutoModelForSpeechSeq2Seq.from_pretrained(model_name)
                
                # 移动到GPU（如果可用）
                if self.config['use_gpu'] and torch.cuda.is_available():
                    self.model = self.model.cuda()
                    
                self.is_loaded = True
                print(f"✅ 多语言ASR模型加载成功: {model_name}")
                return True
                
            except ImportError:
                print("❌ transformers库不可用")
                return False
                
        except Exception as e:
            print(f"❌ 加载多语言ASR模型失败: {e}")
            return False
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, 
                  language: Optional[str] = None) -> Dict[str, Any]:
        """多语言语音识别"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"text": "", "confidence": 0.0, "success": False}
        
        try:
            start_time = time.time()
            
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 自动语言检测（如果未指定语言）
            if language is None and self.config['language_detection']:
                detected_language = self._detect_language(processed_audio)
                language = detected_language
            else:
                detected_language = language
            
            # 验证语言支持
            if language and language not in self.supported_languages:
                print(f"⚠️ 不支持的语言: {language}，使用自动检测")
                language = None
            
            # 语音活动检测
            if self.config['vad_enabled']:
                has_speech = self._voice_activity_detection(processed_audio)
                if not has_speech:
                    return {"text": "", "confidence": 0.0, "success": True, "no_speech": True}
            
            # 准备输入
            inputs = self.processor(processed_audio, 
                                  sampling_rate=self.sample_rate,
                                  return_tensors="pt")
            
            # 设置语言（如果指定）
            if language:
                forced_decoder_ids = self.processor.get_decoder_prompt_ids(
                    language=language, task="transcribe"
                )
                inputs["forced_decoder_ids"] = forced_decoder_ids
            
            # 移动到GPU
            if self.config['use_gpu'] and torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 推理
            with torch.no_grad():
                outputs = self.model.generate(**inputs)
            
            # 解码
            transcription = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # 计算置信度
            confidence = self._calculate_confidence(outputs)
            
            processing_time = time.time() - start_time
            
            return {
                "text": transcription,
                "confidence": confidence,
                "success": True,
                "processing_time": processing_time,
                "language": detected_language or "auto",
                "detected_language": self.supported_languages.get(detected_language, "Unknown")
            }
            
        except Exception as e:
            print(f"❌ 多语言语音识别失败: {e}")
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频数据"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
        # 归一化
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        if TORCH_AVAILABLE:
            import torchaudio
            audio_tensor = torch.from_numpy(audio_data).float()
            resampler = torchaudio.transforms.Resample(orig_freq=original_rate, new_freq=target_rate)
            resampled_audio = resampler(audio_tensor)
            return resampled_audio.numpy()
        else:
            import scipy.signal
            num_samples = int(len(audio_data) * target_rate / original_rate)
            return scipy.signal.resample(audio_data, num_samples)
    
    def _detect_language(self, audio_data: np.ndarray) -> Optional[str]:
        """自动语言检测"""
        # 这里可以实现简单的语言检测逻辑
        # 实际项目中可以使用专门的语言检测模型
        
        # 临时实现：返回None让模型自动检测
        return None
    
    def _voice_activity_detection(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """语音活动检测"""
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > threshold
    
    def _calculate_confidence(self, outputs) -> float:
        """计算识别置信度"""
        # 对于多语言模型，置信度计算可能更复杂
        # 这里返回一个默认值
        return 0.7
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.supported_languages
    
    def add_language_support(self, language_code: str, language_name: str) -> None:
        """添加语言支持"""
        self.supported_languages[language_code] = language_name
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "supported_languages": self.supported_languages,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded