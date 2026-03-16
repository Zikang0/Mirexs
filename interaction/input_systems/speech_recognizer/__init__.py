# interaction/input_systems/speech_recognizer/__init__.py
"""
语音识别模块初始化文件
集成所有语音识别组件并提供统一接口
"""

import logging
from typing import Dict, Any, Optional

# 导入所有语音识别组件
from .bilingual_asr import bilingual_asr, BilingualASR, ASRResult
from .wake_word_detector import wake_word_detector, WakeWordDetector, WakeWordResult
from .voiceprint_auth import voice_authenticator, VoicePrintAuthenticator, AuthResult
from .speech_enhancer import speech_enhancer, SpeechEnhancer, EnhancementResult
from .noise_suppressor import noise_suppressor, NoiseSuppressor, NoiseSuppressionResult
from .accent_adaptation import accent_adapter, AccentAdapter, AccentAdaptationResult
from .realtime_transcriber import realtime_transcriber, RealtimeTranscriber, TranscriptionSegment
from .speech_metrics import speech_metrics_collector, SpeechMetricsCollector

# 导出公共接口
__all__ = [
    # 组件实例
    'bilingual_asr',
    'wake_word_detector', 
    'voice_authenticator',
    'speech_enhancer',
    'noise_suppressor',
    'accent_adapter',
    'realtime_transcriber',
    'speech_metrics_collector',
    
    # 类定义
    'BilingualASR',
    'WakeWordDetector',
    'VoicePrintAuthenticator', 
    'SpeechEnhancer',
    'NoiseSuppressor',
    'AccentAdapter',
    'RealtimeTranscriber',
    'SpeechMetricsCollector',
    
    # 数据结构
    'ASRResult',
    'WakeWordResult',
    'AuthResult',
    'EnhancementResult',
    'NoiseSuppressionResult',
    'AccentAdaptationResult',
    'TranscriptionSegment',
    
    # 函数
    'initialize_speech_recognition',
    'get_speech_recognition_status',
    'transcribe_audio',
    'detect_wake_word',
    'authenticate_user'
]

class SpeechRecognitionManager:
    """语音识别管理器"""
    
    def __init__(self):
        self.components = {
            'bilingual_asr': bilingual_asr,
            'wake_word_detector': wake_word_detector,
            'voice_authenticator': voice_authenticator,
            'speech_enhancer': speech_enhancer,
            'noise_suppressor': noise_suppressor,
            'accent_adapter': accent_adapter,
            'realtime_transcriber': realtime_transcriber,
            'speech_metrics': speech_metrics_collector
        }
        self.is_initialized = False
    
    async def initialize(self):
        """初始化所有语音识别组件"""
        if self.is_initialized:
            return
            
        logging.info("初始化语音识别系统...")
        
        try:
            # 并行初始化所有组件
            init_tasks = []
            for name, component in self.components.items():
                if hasattr(component, 'initialize'):
                    init_tasks.append(component.initialize())
                    logging.debug(f"开始初始化组件: {name}")
            
            # 等待所有组件初始化完成
            await asyncio.gather(*init_tasks, return_exceptions=True)
            
            self.is_initialized = True
            logging.info("语音识别系统初始化完成")
            
        except Exception as e:
            logging.error(f"语音识别系统初始化失败: {e}")
            raise
    
    async def transcribe_audio(self, audio_data, sample_rate=16000, language="auto"):
        """转录音频（统一接口）"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # 预处理音频
            enhanced_audio = await speech_enhancer.enhance_speech(audio_data, sample_rate)
            
            # 抑制噪声
            clean_audio = await noise_suppressor.suppress_noise(enhanced_audio.enhanced_audio, sample_rate)
            
            # 检测口音并适应
            accent_result = await accent_adapter.detect_accent(clean_audio.suppressed_audio, sample_rate)
            
            # 执行转录
            transcription_result = await bilingual_asr.transcribe_audio(
                clean_audio.suppressed_audio, 
                sample_rate
            )
            
            # 记录指标
            if hasattr(speech_metrics_collector, '_handle_ai_response'):
                # 创建模拟消息用于记录指标
                from infrastructure.communication.message_bus import Message, MessageTopic
                message = Message(
                    id="transcription_metric",
                    topic=MessageTopic.AI_RESPONSE,
                    payload={
                        "type": "transcription",
                        "text": transcription_result.text,
                        "confidence": transcription_result.confidence,
                        "processing_time": transcription_result.processing_time,
                        "audio_length": len(audio_data) / sample_rate,
                        "language": transcription_result.language,
                        "model": "bilingual_asr"
                    },
                    timestamp=transcription_result.processing_time,
                    source="speech_recognition_manager"
                )
                await speech_metrics_collector._handle_ai_response(message)
            
            return transcription_result
            
        except Exception as e:
            logging.error(f"音频转录失败: {e}")
            return ASRResult(
                text="",
                confidence=0.0,
                language=language,
                processing_time=0.0,
                is_final=True,
                alternatives=[]
            )
    
    async def detect_wake_word(self, audio_data, sample_rate=16000):
        """检测唤醒词（统一接口）"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            return await wake_word_detector.detect(audio_data, sample_rate)
        except Exception as e:
            logging.error(f"唤醒词检测失败: {e}")
            return WakeWordResult(
                detected=False,
                confidence=0.0,
                wake_word="",
                timestamp=0.0,
                audio_data=audio_data
            )
    
    async def authenticate_user(self, audio_data, sample_rate=16000):
        """用户认证（统一接口）"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            return await voice_authenticator.authenticate(audio_data, sample_rate)
        except Exception as e:
            logging.error(f"用户认证失败: {e}")
            return AuthResult(
                authenticated=False,
                user_id=None,
                confidence=0.0,
                similarity=0.0,
                processing_time=0.0
            )
    
    async def start_realtime_transcription(self, config=None):
        """开始实时转录（统一接口）"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            return await realtime_transcriber.start_streaming(config)
        except Exception as e:
            logging.error(f"启动实时转录失败: {e}")
            return False
    
    async def stop_realtime_transcription(self):
        """停止实时转录（统一接口）"""
        try:
            return await realtime_transcriber.stop_streaming()
        except Exception as e:
            logging.error(f"停止实时转录失败: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "initialized": self.is_initialized,
            "components": {}
        }
        
        for name, component in self.components.items():
            if hasattr(component, 'get_system_info'):
                status["components"][name] = component.get_system_info()
            elif hasattr(component, 'get_detector_info'):
                status["components"][name] = component.get_detector_info()
            elif hasattr(component, 'get_enhancement_info'):
                status["components"][name] = component.get_enhancement_info()
            elif hasattr(component, 'get_suppression_info'):
                status["components"][name] = component.get_suppression_info()
            elif hasattr(component, 'get_accent_info'):
                status["components"][name] = component.get_accent_info()
            elif hasattr(component, 'get_streaming_stats'):
                # 实时转录器需要异步调用
                try:
                    if hasattr(component, 'get_streaming_stats'):
                        # 这里简化处理，实际应该异步获取
                        status["components"][name] = {"available": True}
                except:
                    status["components"][name] = {"available": False}
            elif hasattr(component, 'get_collector_info'):
                status["components"][name] = component.get_collector_info()
            else:
                status["components"][name] = {"available": True}
        
        return status


# 全局语音识别管理器实例
speech_recognition_manager = SpeechRecognitionManager()

# 公共函数
async def initialize_speech_recognition():
    """初始化语音识别系统"""
    return await speech_recognition_manager.initialize()

def get_speech_recognition_status() -> Dict[str, Any]:
    """获取语音识别系统状态"""
    return speech_recognition_manager.get_system_status()

async def transcribe_audio(audio_data, sample_rate=16000, language="auto"):
    """转录音频"""
    return await speech_recognition_manager.transcribe_audio(audio_data, sample_rate, language)

async def detect_wake_word(audio_data, sample_rate=16000):
    """检测唤醒词"""
    return await speech_recognition_manager.detect_wake_word(audio_data, sample_rate)

async def authenticate_user(audio_data, sample_rate=16000):
    """用户认证"""
    return await speech_recognition_manager.authenticate_user(audio_data, sample_rate)

# 导入asyncio用于异步操作
import asyncio
