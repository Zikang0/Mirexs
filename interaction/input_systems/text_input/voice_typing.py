"""
语音打字模块：将语音转换为文字输入
"""

import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable
import logging
from dataclasses import dataclass, field
import json

from interaction.input_systems.speech_recognizer.bilingual_asr import BilingualASR
from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager
from cognitive.memory.working_memory import WorkingMemory

logger = logging.getLogger(__name__)


@dataclass
class VoiceTypingResult:
    """语音打字结果"""
    text: str
    confidence: float
    language: str
    duration: float
    timestamp: float
    raw_audio: Optional[bytes] = None
    alternatives: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "duration": self.duration,
            "timestamp": self.timestamp,
            "alternatives": self.alternatives[:3]
        }


class VoiceTyping:
    """语音打字器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化语音打字器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 语音识别器
        self.asr_engine = None
        self.is_initialized = False
        
        # 状态控制
        self.is_active = False
        self.is_listening = False
        self.is_processing = False
        
        # 音频队列
        self.audio_queue = queue.Queue(maxsize=100)
        
        # 工作线程
        self.listening_thread = None
        self.processing_thread = None
        
        # 配置参数
        self.silence_threshold = 0.5  # 静音阈值（秒）
        self.max_duration = 10.0  # 最大录音时长（秒）
        self.min_confidence = 0.7  # 最小置信度
        
        # 历史记录
        self.recognition_history = []
        self.max_history_size = 100
        
        # 工作内存（用于上下文理解）
        self.working_memory = None
        
        # 回调函数
        self.result_callbacks = []
        self.error_callbacks = []
        
        # 加载配置
        self.load_config()
        
        logger.info("VoiceTyping initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("voice_typing_config")
            
            # 基本配置
            self.enable_auto_start = config.get("enable_auto_start", False)
            self.enable_punctuation = config.get("enable_punctuation", True)
            self.enable_capitalization = config.get("enable_capitalization", True)
            
            # 识别参数
            recognition = config.get("recognition", {})
            self.silence_threshold = recognition.get("silence_threshold", 0.5)
            self.max_duration = recognition.get("max_duration", 10.0)
            self.min_confidence = recognition.get("min_confidence", 0.7)
            self.language = recognition.get("default_language", "auto")
            
            # 音频参数
            audio = config.get("audio", {})
            self.sample_rate = audio.get("sample_rate", 16000)
            self.chunk_size = audio.get("chunk_size", 1024)
            
            logger.debug(f"Voice typing config loaded: language={self.language}")
        except Exception as e:
            logger.error(f"Failed to load voice typing config: {e}")
    
    def initialize(self) -> bool:
        """
        初始化语音打字器
        
        Returns:
            bool: 是否初始化成功
        """
        if self.is_initialized:
            logger.warning("Voice typing already initialized")
            return True
        
        try:
            # 初始化语音识别引擎
            self.asr_engine = BilingualASR(self.config_manager)
            if not self.asr_engine.initialize():
                logger.error("Failed to initialize ASR engine")
                return False
            
            # 初始化工作内存
            self.working_memory = WorkingMemory()
            
            # 注册消息处理器
            self.message_bus.subscribe("voice_typing_command", self._handle_command_message)
            self.message_bus.subscribe("audio_data", self._handle_audio_message)
            
            self.is_initialized = True
            logger.info("Voice typing initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize voice typing: {e}")
            return False
    
    def start_listening(self) -> bool:
        """
        开始监听语音输入
        
        Returns:
            bool: 是否成功开始
        """
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        if self.is_listening:
            logger.warning("Already listening for voice input")
            return False
        
        try:
            self.is_active = True
            self.is_listening = True
            
            # 启动监听线程
            self.listening_thread = threading.Thread(
                target=self._listening_loop,
                daemon=True,
                name="VoiceTypingListener"
            )
            self.listening_thread.start()
            
            # 启动处理线程
            self.processing_thread = threading.Thread(
                target=self._processing_loop,
                daemon=True,
                name="VoiceTypingProcessor"
            )
            self.processing_thread.start()
            
            # 通知其他组件
            self.message_bus.publish("voice_typing_status", {
                "status": "listening_started",
                "timestamp": time.time()
            })
            
            logger.info("Started listening for voice input")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start listening: {e}")
            self.is_listening = False
            return False
    
    def stop_listening(self) -> None:
        """停止监听语音输入"""
        if not self.is_listening:
            return
        
        self.is_listening = False
        
        # 等待线程结束
        if self.listening_thread:
            self.listening_thread.join(timeout=2.0)
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        self.is_active = False
        
        # 通知其他组件
        self.message_bus.publish("voice_typing_status", {
            "status": "listening_stopped",
            "timestamp": time.time()
        })
        
        logger.info("Stopped listening for voice input")
    
    def _listening_loop(self) -> None:
        """监听循环"""
        import pyaudio
        import numpy as np
        
        try:
            audio = pyaudio.PyAudio()
            
            # 打开音频流
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info("Audio stream opened for voice typing")
            
            # 语音活动检测状态
            is_speaking = False
            silence_start = None
            audio_buffer = []
            recording_start = None
            
            while self.is_listening:
                try:
                    # 读取音频数据
                    data = stream.read(self.chunk_size, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    
                    # 检测语音活动
                    energy = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
                    
                    if energy > 500:  # 简单的能量阈值
                        if not is_speaking:
                            is_speaking = True
                            silence_start = None
                            recording_start = time.time()
                            logger.debug("Speech detected")
                        
                        # 添加到缓冲区
                        audio_buffer.append(data)
                        
                        # 检查是否超过最大时长
                        if recording_start and (time.time() - recording_start) > self.max_duration:
                            logger.debug("Max recording duration reached")
                            self._process_audio_buffer(audio_buffer, recording_start)
                            audio_buffer = []
                            is_speaking = False
                    
                    else:
                        if is_speaking:
                            if silence_start is None:
                                silence_start = time.time()
                            elif (time.time() - silence_start) > self.silence_threshold:
                                # 语音结束
                                logger.debug("Speech ended, processing audio")
                                self._process_audio_buffer(audio_buffer, recording_start)
                                audio_buffer = []
                                is_speaking = False
                                silence_start = None
                
                except Exception as e:
                    logger.error(f"Error in listening loop: {e}")
                    time.sleep(0.01)
            
            # 关闭音频流
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            logger.info("Audio stream closed")
            
        except Exception as e:
            logger.error(f"Failed in listening loop: {e}")
    
    def _process_audio_buffer(self, audio_buffer: List[bytes], start_time: Optional[float]) -> None:
        """处理音频缓冲区"""
        if not audio_buffer:
            return
        
        # 计算时长
        duration = len(audio_buffer) * self.chunk_size / self.sample_rate
        logger.debug(f"Processing audio buffer: {len(audio_buffer)} chunks, {duration:.2f}s")
        
        # 将音频数据放入队列
        try:
            audio_data = b''.join(audio_buffer)
            self.audio_queue.put({
                "audio_data": audio_data,
                "start_time": start_time or time.time(),
                "duration": duration,
                "timestamp": time.time()
            }, timeout=1.0)
        except queue.Full:
            logger.warning("Audio queue is full, dropping audio data")
    
    def _processing_loop(self) -> None:
        """处理循环"""
        while self.is_active:
            try:
                # 从队列获取音频数据
                audio_item = self.audio_queue.get(timeout=0.1)
                
                # 处理音频
                result = self._recognize_audio(audio_item)
                
                if result and result.confidence >= self.min_confidence:
                    # 添加到历史记录
                    self.recognition_history.append(result)
                    if len(self.recognition_history) > self.max_history_size:
                        self.recognition_history = self.recognition_history[-self.max_history_size:]
                    
                    # 处理文本（添加标点、大写等）
                    processed_text = self._process_text(result.text)
                    
                    # 发布识别结果
                    self.message_bus.publish("voice_typing_result", {
                        "result": result.to_dict(),
                        "processed_text": processed_text,
                        "timestamp": time.time()
                    })
                    
                    # 调用回调函数
                    for callback in self.result_callbacks:
                        try:
                            callback(result, processed_text)
                        except Exception as e:
                            logger.error(f"Error in result callback: {e}")
                    
                    logger.info(f"Voice typing recognized: {processed_text}")
                
                self.audio_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
    
    def _recognize_audio(self, audio_item: Dict[str, Any]) -> Optional[VoiceTypingResult]:
        """识别音频"""
        if not self.asr_engine:
            return None
        
        try:
            audio_data = audio_item["audio_data"]
            start_time = audio_item["start_time"]
            duration = audio_item["duration"]
            
            # 执行语音识别
            recognition_start = time.time()
            
            # 使用双语ASR引擎
            result = self.asr_engine.recognize(
                audio_data=audio_data,
                language=self.language
            )
            
            recognition_time = time.time() - recognition_start
            
            if result and result.text:
                # 创建工作内存上下文
                context = self._create_context(result.text)
                
                # 创建语音打字结果
                typing_result = VoiceTypingResult(
                    text=result.text,
                    confidence=result.confidence,
                    language=result.language,
                    duration=duration,
                    timestamp=time.time(),
                    raw_audio=audio_data,
                    alternatives=result.alternatives if hasattr(result, 'alternatives') else []
                )
                
                # 更新工作内存
                if self.working_memory:
                    self.working_memory.update_context("voice_typing", context)
                
                return typing_result
            
            return None
            
        except Exception as e:
            logger.error(f"Audio recognition failed: {e}")
            return None
    
    def _create_context(self, text: str) -> Dict[str, Any]:
        """创建上下文"""
        return {
            "text": text,
            "source": "voice_typing",
            "timestamp": time.time(),
            "language": self.language
        }
    
    def _process_text(self, text: str) -> str:
        """处理文本（添加标点、大写等）"""
        processed = text
        
        # 添加标点（如果启用）
        if self.enable_punctuation:
            processed = self._add_punctuation(processed)
        
        # 添加大写（如果启用）
        if self.enable_capitalization:
            processed = self._add_capitalization(processed)
        
        return processed
    
    def _add_punctuation(self, text: str) -> str:
        """添加标点符号"""
        # 简单的标点添加规则
        # TODO: 使用更智能的标点模型
        
        # 确保文本以标点结尾
        if text and text[-1] not in '.!?,;:':
            text += '.'
        
        # 添加逗号到长句子中
        words = text.split()
        if len(words) > 10:
            # 在适当的位置添加逗号
            # 这是一个简化的实现，实际应用应该使用NLP模型
            pass
        
        return text
    
    def _add_capitalization(self, text: str) -> str:
        """添加大写"""
        if not text:
            return text
        
        # 句子首字母大写
        sentences = text.split('. ')
        capitalized_sentences = []
        
        for sentence in sentences:
            if sentence:
                # 确保首字母大写
                sentence = sentence[0].upper() + sentence[1:] if sentence else sentence
                capitalized_sentences.append(sentence)
        
        return '. '.join(capitalized_sentences)
    
    def _handle_command_message(self, message: Dict[str, Any]) -> None:
        """处理命令消息"""
        command = message.get("command")
        
        if command == "start":
            self.start_listening()
        elif command == "stop":
            self.stop_listening()
        elif command == "toggle":
            if self.is_listening:
                self.stop_listening()
            else:
                self.start_listening()
        elif command == "set_language":
            language = message.get("language")
            self.set_language(language)
        elif command == "clear_history":
            self.clear_history()
    
    def _handle_audio_message(self, message: Dict[str, Any]) -> None:
        """处理音频消息"""
        # 来自其他组件的音频数据
        if not self.is_listening:
            return
        
        audio_data = message.get("audio_data")
        if audio_data:
            try:
                self.audio_queue.put({
                    "audio_data": audio_data,
                    "start_time": message.get("start_time", time.time()),
                    "duration": message.get("duration", 0),
                    "timestamp": time.time()
                }, timeout=0.5)
            except queue.Full:
                logger.warning("Audio queue is full, dropping external audio data")
    
    def register_result_callback(self, callback: Callable[[VoiceTypingResult, str], None]) -> None:
        """
        注册结果回调函数
        
        Args:
            callback: 回调函数，接收识别结果和处理后的文本
        """
        self.result_callbacks.append(callback)
        logger.debug(f"Registered result callback: {callback.__name__}")
    
    def register_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """
        注册错误回调函数
        
        Args:
            callback: 回调函数，接收异常对象
        """
        self.error_callbacks.append(callback)
        logger.debug(f"Registered error callback: {callback.__name__}")
    
    def set_language(self, language: str) -> bool:
        """
        设置识别语言
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否成功设置
        """
        if not self.asr_engine:
            return False
        
        try:
            # 验证语言是否支持
            supported_languages = self.asr_engine.get_supported_languages()
            if language not in supported_languages and language != "auto":
                logger.error(f"Unsupported language: {language}")
                return False
            
            self.language = language
            
            # 通知其他组件
            self.message_bus.publish("voice_typing_language_changed", {
                "language": language,
                "timestamp": time.time()
            })
            
            logger.info(f"Voice typing language set to: {language}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set language: {e}")
            return False
    
    def clear_history(self) -> None:
        """清空识别历史"""
        self.recognition_history.clear()
        logger.info("Cleared voice typing history")
    
    def transcribe_audio_file(self, file_path: str) -> Optional[VoiceTypingResult]:
        """
        转录音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            VoiceTypingResult: 转录结果
        """
        if not self.asr_engine:
            return None
        
        try:
            import wave
            import numpy as np
            
            # 读取音频文件
            with wave.open(file_path, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_channels = wav_file.getnchannels()
                n_frames = wav_file.getnframes()
                
                audio_data = wav_file.readframes(n_frames)
                duration = n_frames / sample_rate
            
            # 转换为单声道16位PCM
            if n_channels > 1:
                # 简单的立体声转单声道：取平均值
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                audio_array = audio_array.reshape(-1, n_channels).mean(axis=1).astype(np.int16)
                audio_data = audio_array.tobytes()
            
            # 重采样到目标采样率（如果需要）
            if sample_rate != self.sample_rate:
                # 使用简单重采样
                import audioop
                audio_data = audioop.ratecv(
                    audio_data, 2, 1, sample_rate, self.sample_rate, None
                )[0]
            
            # 执行识别
            recognition_start = time.time()
            result = self.asr_engine.recognize(audio_data, self.language)
            recognition_time = time.time() - recognition_start
            
            if result and result.text:
                return VoiceTypingResult(
                    text=result.text,
                    confidence=result.confidence,
                    language=result.language,
                    duration=duration,
                    timestamp=time.time(),
                    raw_audio=audio_data,
                    alternatives=result.alternatives if hasattr(result, 'alternatives') else []
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Audio file transcription failed: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取语音打字统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "is_listening": self.is_listening,
            "is_processing": self.is_processing,
            "current_language": self.language,
            "audio_queue_size": self.audio_queue.qsize(),
            "recognition_history_size": len(self.recognition_history),
            "callbacks_count": len(self.result_callbacks) + len(self.error_callbacks),
            "silence_threshold": self.silence_threshold,
            "min_confidence": self.min_confidence
        }