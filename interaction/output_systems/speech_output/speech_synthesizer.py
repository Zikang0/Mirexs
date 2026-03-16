"""
语音合成器（Speech Synthesizer）

提供面向应用层的高层接口：
- 统一调用 MultilingualTTS
- 应用情感策略、音色定制
- 可选空间化与音效链
- 输出指标记录
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np

from .multilingual_tts import EmotionType, MultilingualTTS, TTSConfig, TTSResult, multilingual_tts
from .audio_effects import AudioEffectsConfig, AudioEffectsProcessor
from .spatial_audio import SpatialAudioConfig, SpatialAudioProcessor
from .voice_customization import VoiceCustomizationManager
from .emotional_voice import EmotionalVoiceEngine, EmotionRequest
from .speech_metrics import SpeechMetricsCollector, SpeechSynthesisMetrics

logger = logging.getLogger(__name__)


@dataclass
class SynthesisRequest:
    text: str
    tts_config: Optional[TTSConfig] = None

    # 个性化
    voice_id: Optional[str] = None
    emotion: Optional[EmotionType] = None
    auto_emotion: bool = True

    # 后处理
    spatial: Optional[SpatialAudioConfig] = None
    effects: Optional[AudioEffectsConfig] = None


@dataclass
class SynthesisOutput:
    success: bool
    audio_data: Optional[np.ndarray]
    sample_rate: int
    tts_result: Optional[TTSResult] = None
    applied_emotion: Optional[EmotionRequest] = None
    metrics: Optional[SpeechSynthesisMetrics] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class SpeechSynthesizer:
    """高层语音合成与后处理入口"""

    def __init__(self, tts: Optional[MultilingualTTS] = None):
        self.tts = tts or multilingual_tts
        self.voice_manager = VoiceCustomizationManager(self.tts)
        self.emotion_engine = EmotionalVoiceEngine()
        self.spatializer = SpatialAudioProcessor()
        self.effects_processor = AudioEffectsProcessor()
        self.metrics_collector = SpeechMetricsCollector()

    async def synthesize(self, request: SynthesisRequest) -> SynthesisOutput:
        text = (request.text or "").strip()
        if not text:
            return SynthesisOutput(success=False, audio_data=None, sample_rate=0, error="Empty text", metadata={})

        config = request.tts_config or TTSConfig()

        # 应用 voice_id
        if request.voice_id:
            voice = self.voice_manager.get_voice(request.voice_id)
            if voice:
                config.voice_profile = voice
            else:
                logger.warning(f"voice_id not found: {request.voice_id}")

        # 情感策略
        applied_emotion: Optional[EmotionRequest] = None
        if request.emotion is not None:
            config, applied_emotion = self.emotion_engine.apply(config, emotion=request.emotion, text=text)
        elif request.auto_emotion:
            config, applied_emotion = self.emotion_engine.apply(config, emotion=None, text=text)

        start_time = time.time()
        try:
            tts_result = await self.tts.synthesize(text, config)
            if not tts_result:
                return SynthesisOutput(success=False, audio_data=None, sample_rate=0, error="TTS synthesis failed", metadata={})

            audio = tts_result.audio_data
            sr = int(tts_result.sample_rate)

            # 空间化（mono->stereo 或 stereo->stereo）
            if request.spatial:
                audio = self.spatializer.apply(audio, sr, request.spatial)

            # 音效链
            if request.effects:
                audio = self.effects_processor.apply(audio, sr, request.effects)

            processing_time = time.time() - start_time
            metrics = self.metrics_collector.record(text, audio, sr, processing_time_s=processing_time)

            return SynthesisOutput(
                success=True,
                audio_data=audio,
                sample_rate=sr,
                tts_result=tts_result,
                applied_emotion=applied_emotion,
                metrics=metrics,
                metadata={
                    "voice_id": getattr(config.voice_profile, "voice_id", None),
                    "emotion": config.emotion.value if hasattr(config, "emotion") else None,
                },
            )

        except Exception as e:
            return SynthesisOutput(
                success=False,
                audio_data=None,
                sample_rate=0,
                error=str(e),
                metadata={},
            )


_speech_synthesizer_instance: Optional[SpeechSynthesizer] = None
_speech_synthesizer_lock = asyncio.Lock()


def get_speech_synthesizer() -> SpeechSynthesizer:
    global _speech_synthesizer_instance
    if _speech_synthesizer_instance is None:
        _speech_synthesizer_instance = SpeechSynthesizer()
    return _speech_synthesizer_instance


async def synthesize_speech(text: str, **kwargs) -> SynthesisOutput:
    synthesizer = get_speech_synthesizer()
    request = SynthesisRequest(text=text, **kwargs)
    return await synthesizer.synthesize(request)


