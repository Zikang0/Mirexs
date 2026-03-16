# interaction/input_systems/speech_recognizer/bilingual_asr.py
"""
双语语音识别：中英文语音识别
负责中英文混合语音的识别和语言检测
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time

@dataclass
class ASRResult:
    """语音识别结果"""
    text: str
    confidence: float
    language: str
    processing_time: float
    is_final: bool
    alternatives: List[str]

class BilingualASR:
    """双语语音识别器"""
    
    def __init__(self):
        self.chinese_model = None
        self.english_model = None
        self.language_detector = None
        self.is_initialized = False
        self.sample_rate = 16000
        self.chunk_size = 1024
        
    async def initialize(self):
        """初始化双语ASR系统"""
        if self.is_initialized:
            return
            
        logging.info("初始化双语语音识别系统...")
        
        try:
            # 初始化中文ASR模型
            from data.models.speech.asr.chinese_asr_model import ChineseASRModel
            self.chinese_model = ChineseASRModel()
            
            # 初始化英文ASR模型  
            from data.models.speech.asr.english_asr_model import EnglishASRModel
            self.english_model = EnglishASRModel()
            
            # 初始化语言检测器
            self.language_detector = LanguageDetector()
            
            # 加载模型
            await asyncio.gather(
                self._load_model_async(self.chinese_model),
                self._load_model_async(self.english_model)
            )
            
            self.is_initialized = True
            logging.info("双语语音识别系统初始化完成")
            
        except Exception as e:
            logging.error(f"双语ASR初始化失败: {e}")
            raise
    
    async def _load_model_async(self, model):
        """异步加载模型"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, model.load)
    
    async def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = None) -> ASRResult:
        """转录音频数据"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 预处理音频
            processed_audio = await self._preprocess_audio(audio_data, sample_rate or self.sample_rate)
            
            # 检测语言
            detected_lang = await self._detect_language(processed_audio)
            
            # 选择合适的模型进行识别
            if detected_lang == "zh-CN":
                result = await self._transcribe_chinese(processed_audio)
            elif detected_lang == "en-US":
                result = await self._transcribe_english(processed_audio)
            else:
                # 默认使用英文模型
                result = await self._transcribe_english(processed_audio)
            
            processing_time = time.time() - start_time
            
            return ASRResult(
                text=result["text"],
                confidence=result["confidence"],
                language=detected_lang,
                processing_time=processing_time,
                is_final=True,
                alternatives=result.get("alternatives", [])
            )
            
        except Exception as e:
            logging.error(f"语音识别失败: {e}")
            return ASRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=time.time() - start_time,
                is_final=True,
                alternatives=[]
            )
    
    async def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频数据"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = await self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
        # 归一化
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data
    
    async def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        try:
            import torch
            import torchaudio
            
            audio_tensor = torch.from_numpy(audio_data).float()
            resampler = torchaudio.transforms.Resample(orig_freq=original_rate, new_freq=target_rate)
            resampled_audio = resampler(audio_tensor)
            return resampled_audio.numpy()
            
        except ImportError:
            # 简单的线性重采样
            num_samples = int(len(audio_data) * target_rate / original_rate)
            indices = np.linspace(0, len(audio_data)-1, num_samples)
            return np.interp(indices, np.arange(len(audio_data)), audio_data)
    
    async def _detect_language(self, audio_data: np.ndarray) -> str:
        """检测语言"""
        if self.language_detector:
            return await self.language_detector.detect(audio_data)
        
        # 简单的基于音频特征的语言检测
        # 在实际实现中，这里会使用更复杂的语言检测模型
        try:
            # 计算梅尔频率倒谱系数(MFCC)特征
            mfcc_features = await self._extract_mfcc(audio_data)
            
            # 简单的基于特征的语言分类（简化实现）
            spectral_centroid = np.mean(np.abs(np.fft.fft(audio_data)))
            
            if spectral_centroid > 1000:  # 这个阈值需要根据实际数据调整
                return "en-US"
            else:
                return "zh-CN"
                
        except Exception:
            return "en-US"  # 默认英文
    
    async def _extract_mfcc(self, audio_data: np.ndarray) -> np.ndarray:
        """提取MFCC特征"""
        try:
            import librosa
            
            mfcc = librosa.feature.mfcc(
                y=audio_data, 
                sr=self.sample_rate, 
                n_mfcc=13
            )
            return np.mean(mfcc, axis=1)
            
        except ImportError:
            # 返回模拟特征
            return np.random.random(13)
    
    async def _transcribe_chinese(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """中文语音识别"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.chinese_model.transcribe, 
            audio_data, 
            self.sample_rate
        )
        return result
    
    async def _transcribe_english(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """英文语音识别"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.english_model.transcribe, 
            audio_data, 
            self.sample_rate
        )
        return result
    
    async def realtime_transcribe(self, audio_stream, callback=None) -> None:
        """实时语音转录"""
        buffer = []
        buffer_duration = 0.5  # 500ms缓冲区
        
        async for audio_chunk in audio_stream:
            buffer.append(audio_chunk)
            
            # 检查缓冲区是否达到处理时长
            if len(buffer) * len(audio_chunk) / self.sample_rate >= buffer_duration:
                # 合并缓冲区数据
                combined_audio = np.concatenate(buffer)
                
                # 进行识别
                result = await self.transcribe_audio(combined_audio)
                
                if callback and result.text:
                    await callback(result)
                
                # 清空缓冲区（保留最后一部分用于连续识别）
                buffer = buffer[-int(0.1 * self.sample_rate / len(audio_chunk)):]  # 保留100ms
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "sample_rate": self.sample_rate,
            "chunk_size": self.chunk_size,
            "chinese_model_loaded": self.chinese_model.is_loaded if self.chinese_model else False,
            "english_model_loaded": self.english_model.is_loaded if self.english_model else False
        }


class LanguageDetector:
    """语言检测器"""
    
    async def detect(self, audio_data: np.ndarray) -> str:
        """检测音频语言"""
        # 简化实现 - 在实际应用中会使用专门的语言检测模型
        # 这里使用随机选择来模拟检测结果
        import random
        languages = ["zh-CN", "en-US"]
        return random.choice(languages)


# 全局双语ASR实例
bilingual_asr = BilingualASR()
