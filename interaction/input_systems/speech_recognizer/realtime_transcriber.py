# interaction/input_systems/speech_recognizer/realtime_transcriber.py
"""
实时转录器：实时语音转文本
负责实时音频流的连续语音识别
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
import logging
from dataclasses import dataclass
import time
import queue
import threading

@dataclass
class TranscriptionSegment:
    """转录片段"""
    text: str
    start_time: float
    end_time: float
    confidence: float
    is_final: bool
    language: str

@dataclass
class RealtimeConfig:
    """实时配置"""
    chunk_duration: float = 0.1  # 每个音频块的长度（秒）
    overlap_ratio: float = 0.5   # 块重叠比例
    min_segment_duration: float = 0.3  # 最小片段时长
    max_segment_duration: float = 5.0  # 最大片段时长
    silence_threshold: float = 0.01    # 静音阈值
    language: str = "auto"             # 语言设置

class RealtimeTranscriber:
    """实时转录器"""
    
    def __init__(self):
        self.is_initialized = False
        self.is_streaming = False
        self.sample_rate = 16000
        self.audio_buffer = queue.Queue()
        self.transcription_buffer = queue.Queue()
        self.processing_thread = None
        self.callbacks = []
        
        # 集成基础设施组件
        from infrastructure.compute_storage.inference_optimizer import inference_optimizer
        self.inference_optimizer = inference_optimizer
        from infrastructure.compute_storage.model_serving_engine import model_serving_engine
        self.model_serving_engine = model_serving_engine
        from infrastructure.communication.message_bus import message_bus
        self.message_bus = message_bus
        
        # 集成其他语音组件
        from interaction.input_systems.speech_recognizer.bilingual_asr import bilingual_asr
        from interaction.input_systems.speech_recognizer.speech_enhancer import speech_enhancer
        from interaction.input_systems.speech_recognizer.noise_suppressor import noise_suppressor
        
        self.bilingual_asr = bilingual_asr
        self.speech_enhancer = speech_enhancer
        self.noise_suppressor = noise_suppressor
        
    async def initialize(self):
        """初始化实时转录器"""
        if self.is_initialized:
            return
            
        logging.info("初始化实时转录系统...")
        
        try:
            # 初始化基础设施组件
            await self.inference_optimizer.initialize()
            await self.model_serving_engine.initialize()
            await self.message_bus.initialize()
            
            # 初始化语音组件
            await self.bilingual_asr.initialize()
            await self.speech_enhancer.initialize()
            await self.noise_suppressor.initialize()
            
            self.is_initialized = True
            logging.info("实时转录系统初始化完成")
            
        except Exception as e:
            logging.error(f"实时转录系统初始化失败: {e}")
            raise
    
    async def start_streaming(self, config: RealtimeConfig = None) -> bool:
        """开始实时转录流"""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_streaming:
            logging.warning("实时转录已经在运行")
            return False
        
        self.config = config or RealtimeConfig()
        self.is_streaming = True
        
        # 启动处理线程
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        # 发布系统消息
        await self.message_bus.publish(
            topic="SYSTEM_STARTUP",
            payload={"component": "realtime_transcriber", "status": "started"},
            source="realtime_transcriber"
        )
        
        logging.info("实时转录流已启动")
        return True
    
    async def stop_streaming(self) -> bool:
        """停止实时转录流"""
        if not self.is_streaming:
            return False
        
        self.is_streaming = False
        
        # 等待处理线程结束
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        # 清空缓冲区
        while not self.audio_buffer.empty():
            try:
                self.audio_buffer.get_nowait()
            except queue.Empty:
                break
        
        # 发布系统消息
        await self.message_bus.publish(
            topic="SYSTEM_SHUTDOWN", 
            payload={"component": "realtime_transcriber", "status": "stopped"},
            source="realtime_transcriber"
        )
        
        logging.info("实时转录流已停止")
        return True
    
    async def add_audio_data(self, audio_chunk: np.ndarray, sample_rate: int = None):
        """添加音频数据到流"""
        if not self.is_streaming:
            logging.warning("实时转录未启动，无法添加音频数据")
            return
        
        try:
            # 预处理音频块
            processed_chunk = await self._preprocess_audio_chunk(audio_chunk, sample_rate)
            
            # 添加到音频缓冲区
            timestamp = time.time()
            self.audio_buffer.put({
                'audio_data': processed_chunk,
                'timestamp': timestamp,
                'sample_rate': self.sample_rate
            })
            
        except Exception as e:
            logging.error(f"添加音频数据失败: {e}")
    
    async def _preprocess_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频块"""
        # 转换为单声道
        if len(audio_chunk.shape) > 1:
            audio_chunk = np.mean(audio_chunk, axis=1)
        
        # 重采样到目标采样率
        if sample_rate and sample_rate != self.sample_rate:
            audio_chunk = await self._resample_audio(audio_chunk, sample_rate, self.sample_rate)
        
        return audio_chunk
    
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
            # 线性重采样
            num_samples = int(len(audio_data) * target_rate / original_rate)
            indices = np.linspace(0, len(audio_data)-1, num_samples)
            return np.interp(indices, np.arange(len(audio_data)), audio_data)
    
    def _processing_loop(self):
        """处理循环（在单独线程中运行）"""
        buffer = []
        last_processing_time = 0
        segment_start_time = None
        
        while self.is_streaming:
            try:
                # 从缓冲区获取音频数据
                try:
                    audio_item = self.audio_buffer.get(timeout=0.1)
                    buffer.append(audio_item)
                except queue.Empty:
                    continue
                
                current_time = time.time()
                
                # 检查是否应该处理缓冲区
                buffer_duration = len(buffer) * self.config.chunk_duration * (1 - self.config.overlap_ratio)
                time_since_last_process = current_time - last_processing_time
                
                if (buffer_duration >= self.config.min_segment_duration or 
                    time_since_last_process >= self.config.max_segment_duration):
                    
                    if buffer:
                        # 处理音频段
                        segment = self._process_audio_segment(buffer, segment_start_time)
                        
                        if segment:
                            # 添加到转录缓冲区
                            self.transcription_buffer.put(segment)
                            
                            # 触发回调
                            asyncio.run_coroutine_threadsafe(
                                self._trigger_callbacks(segment),
                                asyncio.get_event_loop()
                            )
                            
                            # 发布消息
                            asyncio.run_coroutine_threadsafe(
                                self.message_bus.publish(
                                    topic="AI_RESPONSE",
                                    payload={
                                        "type": "transcription",
                                        "text": segment.text,
                                        "confidence": segment.confidence,
                                        "is_final": segment.is_final
                                    },
                                    source="realtime_transcriber"
                                ),
                                asyncio.get_event_loop()
                            )
                        
                        # 清空缓冲区（保留重叠部分）
                        overlap_count = int(len(buffer) * self.config.overlap_ratio)
                        buffer = buffer[-overlap_count:] if overlap_count > 0 else []
                        
                        # 更新段开始时间
                        if segment:
                            segment_start_time = segment.end_time
                        else:
                            segment_start_time = current_time
                    
                    last_processing_time = current_time
                
            except Exception as e:
                logging.error(f"处理循环错误: {e}")
                continue
    
    def _process_audio_segment(self, buffer: List[Dict], segment_start_time: float) -> Optional[TranscriptionSegment]:
        """处理音频段"""
        try:
            # 合并缓冲区中的音频数据
            audio_chunks = [item['audio_data'] for item in buffer]
            combined_audio = np.concatenate(audio_chunks)
            
            # 计算时间信息
            if segment_start_time is None:
                segment_start_time = buffer[0]['timestamp']
            segment_end_time = buffer[-1]['timestamp'] + len(buffer[-1]['audio_data']) / self.sample_rate
            
            # 检查是否有语音活动
            has_speech = self._detect_speech_activity(combined_audio)
            if not has_speech:
                return None
            
            # 增强音频质量
            enhanced_audio = self._enhance_audio_segment(combined_audio)
            
            # 执行语音识别
            transcription_result = self._transcribe_audio_segment(enhanced_audio)
            
            if transcription_result and transcription_result.text.strip():
                return TranscriptionSegment(
                    text=transcription_result.text,
                    start_time=segment_start_time,
                    end_time=segment_end_time,
                    confidence=transcription_result.confidence,
                    is_final=transcription_result.is_final,
                    language=transcription_result.language
                )
            else:
                return None
                
        except Exception as e:
            logging.error(f"音频段处理失败: {e}")
            return None
    
    def _detect_speech_activity(self, audio_data: np.ndarray) -> bool:
        """检测语音活动"""
        try:
            # 计算能量
            energy = np.mean(audio_data ** 2)
            
            # 计算过零率
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_data)))) / len(audio_data)
            
            # 综合判断
            energy_threshold = self.config.silence_threshold
            zcr_threshold = 0.01
            
            return energy > energy_threshold and zero_crossings > zcr_threshold
            
        except Exception:
            return True  # 默认认为有语音
    
    def _enhance_audio_segment(self, audio_data: np.ndarray) -> np.ndarray:
        """增强音频段"""
        try:
            # 使用语音增强器
            enhancement_result = asyncio.run_coroutine_threadsafe(
                self.speech_enhancer.enhance_speech(audio_data, self.sample_rate),
                asyncio.get_event_loop()
            ).result(timeout=5.0)
            
            return enhancement_result.enhanced_audio
            
        except Exception as e:
            logging.warning(f"音频增强失败: {e}")
            return audio_data  # 返回原始音频
    
    def _transcribe_audio_segment(self, audio_data: np.ndarray):
        """转录音频段"""
        try:
            # 使用双语ASR进行转录
            transcription_result = asyncio.run_coroutine_threadsafe(
                self.bilingual_asr.transcribe_audio(audio_data, self.sample_rate),
                asyncio.get_event_loop()
            ).result(timeout=10.0)
            
            return transcription_result
            
        except Exception as e:
            logging.error(f"音频转录失败: {e}")
            return None
    
    async def get_transcription(self, timeout: float = None) -> Optional[TranscriptionSegment]:
        """获取转录结果"""
        try:
            if timeout:
                segment = self.transcription_buffer.get(timeout=timeout)
                self.transcription_buffer.task_done()
                return segment
            else:
                if not self.transcription_buffer.empty():
                    segment = self.transcription_buffer.get_nowait()
                    self.transcription_buffer.task_done()
                    return segment
                else:
                    return None
                    
        except queue.Empty:
            return None
    
    async def transcription_generator(self) -> AsyncGenerator[TranscriptionSegment, None]:
        """转录生成器"""
        while self.is_streaming:
            try:
                segment = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.transcription_buffer.get, 
                    True,  # block
                    1.0    # timeout
                )
                if segment:
                    yield segment
                self.transcription_buffer.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"转录生成器错误: {e}")
                break
    
    async def add_callback(self, callback: Callable[[TranscriptionSegment], None]):
        """添加转录回调"""
        self.callbacks.append(callback)
    
    async def remove_callback(self, callback: Callable[[TranscriptionSegment], None]):
        """移除转录回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def _trigger_callbacks(self, segment: TranscriptionSegment):
        """触发所有回调函数"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(segment)
                else:
                    callback(segment)
            except Exception as e:
                logging.error(f"转录回调执行失败: {e}")
    
    async def get_streaming_stats(self) -> Dict[str, Any]:
        """获取流统计信息"""
        return {
            "is_streaming": self.is_streaming,
            "is_initialized": self.is_initialized,
            "audio_buffer_size": self.audio_buffer.qsize(),
            "transcription_buffer_size": self.transcription_buffer.qsize(),
            "config": {
                "chunk_duration": self.config.chunk_duration,
                "overlap_ratio": self.config.overlap_ratio,
                "min_segment_duration": self.config.min_segment_duration,
                "max_segment_duration": self.config.max_segment_duration,
                "silence_threshold": self.config.silence_threshold,
                "language": self.config.language
            } if hasattr(self, 'config') else {},
            "callback_count": len(self.callbacks)
        }
    
    async def update_config(self, new_config: RealtimeConfig):
        """更新配置"""
        self.config = new_config
        logging.info("实时转录配置已更新")


# 全局实时转录器实例
realtime_transcriber = RealtimeTranscriber()
