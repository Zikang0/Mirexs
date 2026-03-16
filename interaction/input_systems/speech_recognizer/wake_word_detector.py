# interaction/input_systems/speech_recognizer/wake_word_detector.py
"""
唤醒词检测器：检测唤醒词
负责检测特定的唤醒词来激活语音助手
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Callable
import logging
from dataclasses import dataclass
import time

@dataclass
class WakeWordResult:
    """唤醒词检测结果"""
    detected: bool
    confidence: float
    wake_word: str
    timestamp: float
    audio_data: np.ndarray

class WakeWordDetector:
    """唤醒词检测器"""
    
    def __init__(self):
        self.wake_words = ["弥尔思", "mirexs", "hey mirexs", "hello mirexs"]
        self.detection_threshold = 0.7
        self.is_initialized = False
        self.model = None
        self.callbacks = []
        
    async def initialize(self):
        """初始化唤醒词检测器"""
        if self.is_initialized:
            return
            
        logging.info("初始化唤醒词检测器...")
        
        try:
            # 加载唤醒词模型
            from data.models.speech.wake_word.wake_word_model import WakeWordModel
            self.model = WakeWordModel()
            
            # 异步加载模型
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.model.load)
            
            self.is_initialized = True
            logging.info("唤醒词检测器初始化完成")
            
        except Exception as e:
            logging.warning(f"唤醒词模型加载失败，使用基础检测: {e}")
            self.is_initialized = True  # 即使模型加载失败也标记为已初始化
    
    async def detect(self, audio_data: np.ndarray, sample_rate: int = 16000) -> WakeWordResult:
        """检测唤醒词"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            if self.model and self.model.is_loaded:
                # 使用模型进行检测
                result = await self._detect_with_model(audio_data, sample_rate)
            else:
                # 使用基础检测方法
                result = await self._detect_basic(audio_data, sample_rate)
            
            result.timestamp = time.time()
            result.audio_data = audio_data
            
            # 如果检测到唤醒词，触发回调
            if result.detected:
                await self._trigger_callbacks(result)
            
            return result
            
        except Exception as e:
            logging.error(f"唤醒词检测失败: {e}")
            return WakeWordResult(
                detected=False,
                confidence=0.0,
                wake_word="",
                timestamp=time.time(),
                audio_data=audio_data
            )
    
    async def _detect_with_model(self, audio_data: np.ndarray, sample_rate: int) -> WakeWordResult:
        """使用模型检测唤醒词"""
        loop = asyncio.get_event_loop()
        model_result = await loop.run_in_executor(
            None, 
            self.model.detect, 
            audio_data, 
            sample_rate
        )
        
        return WakeWordResult(
            detected=model_result["detected"],
            confidence=model_result["confidence"],
            wake_word=model_result["wake_word"],
            timestamp=0,  # 会在外层设置
            audio_data=audio_data
        )
    
    async def _detect_basic(self, audio_data: np.ndarray, sample_rate: int) -> WakeWordResult:
        """基础唤醒词检测（能量和简单模式匹配）"""
        # 计算音频能量
        energy = np.mean(audio_data ** 2)
        
        # 简单的能量阈值检测
        if energy < 0.001:  # 能量太低，不太可能是语音
            return WakeWordResult(
                detected=False,
                confidence=0.0,
                wake_word="",
                timestamp=0,
                audio_data=audio_data
            )
        
        # 计算频谱特征
        spectrum = np.abs(np.fft.fft(audio_data))
        spectral_centroid = np.sum(np.arange(len(spectrum)) * spectrum) / np.sum(spectrum)
        
        # 简单的特征匹配（模拟）
        confidence = min(1.0, energy * 100 + spectral_centroid / 1000)
        detected = confidence > self.detection_threshold
        
        return WakeWordResult(
            detected=detected,
            confidence=confidence,
            wake_word="mirexs" if detected else "",
            timestamp=0,
            audio_data=audio_data
        )
    
    async def add_callback(self, callback: Callable[[WakeWordResult], None]):
        """添加唤醒词检测回调"""
        self.callbacks.append(callback)
    
    async def remove_callback(self, callback: Callable[[WakeWordResult], None]):
        """移除唤醒词检测回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def _trigger_callbacks(self, result: WakeWordResult):
        """触发所有回调函数"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logging.error(f"唤醒词回调执行失败: {e}")
    
    async def continuous_detection(self, audio_stream, callback=None):
        """连续唤醒词检测"""
        buffer = []
        frame_duration = 0.1  # 100ms每帧
        
        async for audio_frame in audio_stream:
            buffer.append(audio_frame)
            
            # 每10帧（1秒）进行一次检测
            if len(buffer) >= 10:
                combined_audio = np.concatenate(buffer)
                result = await self.detect(combined_audio)
                
                if callback and result.detected:
                    await callback(result)
                
                # 清空缓冲区
                buffer = []
    
    def set_wake_words(self, wake_words: List[str]):
        """设置唤醒词列表"""
        self.wake_words = wake_words
    
    def set_threshold(self, threshold: float):
        """设置检测阈值"""
        self.detection_threshold = threshold
    
    def get_detector_info(self) -> Dict[str, Any]:
        """获取检测器信息"""
        return {
            "initialized": self.is_initialized,
            "wake_words": self.wake_words,
            "threshold": self.detection_threshold,
            "model_loaded": self.model.is_loaded if self.model else False,
            "callback_count": len(self.callbacks)
        }


# 全局唤醒词检测器实例
wake_word_detector = WakeWordDetector()

