"""
语音输出子系统 (Speech Output)

面向 Mirexs 的多模态输出系统中的“语音输出”部分，提供：
- 多语言语音合成（MultilingualTTS）
- 情感语音策略（EmotionalVoiceEngine）
- 语音定制与音色管理（VoiceCustomizationManager）
- 音频后处理（AudioEffectsProcessor / SpatialAudioProcessor / AudioMixer）
- 指标采集（SpeechMetricsCollector）
"""

from .multilingual_tts import (
    MultilingualTTS,
    TTSConfig,
    TTSResult,
    VoiceProfile,
    VoiceGender,
    VoiceAge,
    EmotionType,
    multilingual_tts,
)
from .audio_effects import AudioEffectsConfig, AudioEffectsProcessor, EchoConfig, ReverbConfig
from .audio_mixer import AudioMixer, AudioTrack, MixedAudio
from .spatial_audio import SpatialAudioConfig, SpatialAudioProcessor
from .voice_customization import VoiceCustomizationManager, VoiceProfileExport
from .emotional_voice import EmotionalVoiceEngine, EmotionRequest
from .speech_metrics import SpeechMetricsCollector, SpeechSynthesisMetrics
from .speech_synthesizer import (
    SpeechSynthesizer,
    SynthesisRequest,
    SynthesisOutput,
    get_speech_synthesizer,
    synthesize_speech,
)

__all__ = [
    # TTS
    "MultilingualTTS",
    "TTSConfig",
    "TTSResult",
    "VoiceProfile",
    "VoiceGender",
    "VoiceAge",
    "EmotionType",
    "multilingual_tts",
    # 音频处理
    "AudioEffectsConfig",
    "EchoConfig",
    "ReverbConfig",
    "AudioEffectsProcessor",
    "AudioMixer",
    "AudioTrack",
    "MixedAudio",
    "SpatialAudioConfig",
    "SpatialAudioProcessor",
    # 语音策略与定制
    "VoiceCustomizationManager",
    "VoiceProfileExport",
    "EmotionalVoiceEngine",
    "EmotionRequest",
    # 指标
    "SpeechMetricsCollector",
    "SpeechSynthesisMetrics",
    # 高层合成器
    "SpeechSynthesizer",
    "SynthesisRequest",
    "SynthesisOutput",
    "get_speech_synthesizer",
    "synthesize_speech",
]

