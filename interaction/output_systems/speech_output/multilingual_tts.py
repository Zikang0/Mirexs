"""
多语言语音合成系统 - 完整实现
基于Coqui TTS和XTTS引擎，提供高质量的多语言语音合成
支持情感化语音、语音克隆和实时语音生成
"""

import os
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from pathlib import Path
import asyncio
from enum import Enum
import threading
import wave

# 导入基础设施层依赖
from infrastructure.compute_storage.gpu_accelerator import GPUAccelerator, gpu_accelerator
from infrastructure.compute_storage.model_serving_engine import ModelServingEngine, model_serving_engine, ModelType
from infrastructure.compute_storage.resource_manager import ResourceManager, resource_manager, ResourceType

# 导入数据层依赖
from data.models.speech.tts.chinese_tts_model import ChineseTTSModel
from data.models.speech.tts.english_tts_model import EnglishTTSModel
from data.models.speech.tts.emotional_tts import EmotionalTTS
from data.models.speech.tts.voice_cloning import VoiceCloning

logger = logging.getLogger(__name__)

class VoiceGender(Enum):
    """语音性别枚举"""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

class VoiceAge(Enum):
    """语音年龄枚举"""
    CHILD = "child"
    YOUNG = "young"
    ADULT = "adult"
    ELDER = "elder"

class EmotionType(Enum):
    """情感类型枚举"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    EXCITED = "excited"
    CALM = "calm"
    SURPRISED = "surprised"
    FEARFUL = "fearful"

@dataclass
class VoiceProfile:
    """语音配置文件"""
    voice_id: str
    name: str
    gender: VoiceGender
    age: VoiceAge
    language: str
    accent: str = "standard"
    pitch: float = 1.0  # 音调 (0.5-2.0)
    speed: float = 1.0  # 语速 (0.5-2.0)
    energy: float = 1.0  # 能量/音量 (0.5-2.0)
    emotion_strength: float = 1.0  # 情感强度 (0.0-2.0)
    voice_characteristics: Dict[str, float] = field(default_factory=dict)

@dataclass
class TTSConfig:
    """TTS配置"""
    engine: str = "coqui"  # coqui, xtts, ms_sapi, espeak
    language: str = "zh-cn"
    voice_profile: Optional[VoiceProfile] = None
    emotion: EmotionType = EmotionType.NEUTRAL
    emotion_strength: float = 1.0  # 情感强度 (0.0-2.0)，可覆盖 voice_profile.emotion_strength
    sample_rate: int = 22050
    chunk_size: int = 1024
    realtime: bool = True
    use_gpu: bool = True
    cache_enabled: bool = True

@dataclass
class TTSResult:
    """TTS结果"""
    audio_data: np.ndarray
    sample_rate: int
    phonemes: List[str]
    durations: List[float]
    emotion_scores: Dict[str, float]
    processing_time: float
    voice_characteristics: Dict[str, float]

class MultilingualTTS:
    """多语言语音合成系统 - 完整实现"""
    
    def __init__(self, cache_size_mb: int = 512):
        self.voice_profiles: Dict[str, VoiceProfile] = {}
        self.tts_engines: Dict[str, Any] = {}
        self.audio_cache: Dict[str, TTSResult] = {}
        self.current_voice: Optional[VoiceProfile] = None
        
        # 子系统
        self.chinese_tts = ChineseTTSModel()
        self.english_tts = EnglishTTSModel()
        self.emotional_tts = EmotionalTTS()
        self.voice_cloning = VoiceCloning()
        
        # 性能统计
        self.stats = {
            "total_synthesized": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_latency": 0.0,
            "real_time_synthesis": 0,
            "emotion_applied": 0
        }
        
        # 内存管理
        self.cache_size_limit = cache_size_mb * 1024 * 1024
        self.current_cache_size = 0
        
        # 初始化默认语音
        self._initialize_default_voices()
        
        # 初始化TTS引擎
        self._initialize_tts_engines()
        
        logger.info("Multilingual TTS system initialized")

    def _initialize_default_voices(self):
        """初始化默认语音配置"""
        # 中文语音配置
        chinese_female = VoiceProfile(
            voice_id="chinese_female_01",
            name="小爱",
            gender=VoiceGender.FEMALE,
            age=VoiceAge.YOUNG,
            language="zh-cn",
            accent="standard",
            pitch=1.1,
            speed=1.0,
            energy=1.0
        )
        
        chinese_male = VoiceProfile(
            voice_id="chinese_male_01",
            name="小明",
            gender=VoiceGender.MALE,
            age=VoiceAge.ADULT,
            language="zh-cn",
            accent="standard",
            pitch=0.9,
            speed=1.1,
            energy=1.2
        )
        
        # 英文语音配置
        english_female = VoiceProfile(
            voice_id="english_female_01",
            name="Emma",
            gender=VoiceGender.FEMALE,
            age=VoiceAge.YOUNG,
            language="en-us",
            accent="american",
            pitch=1.0,
            speed=1.0,
            energy=1.0
        )
        
        self.voice_profiles = {
            chinese_female.voice_id: chinese_female,
            chinese_male.voice_id: chinese_male,
            english_female.voice_id: english_female
        }
        
        self.current_voice = chinese_female

    def _initialize_tts_engines(self):
        """初始化TTS引擎"""
        try:
            # 初始化Coqui TTS
            self._initialize_coqui_tts()
            
            # 初始化XTTS
            self._initialize_xtts()
            
            # 初始化其他TTS引擎
            self._initialize_backup_engines()
            
            logger.info("TTS engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing TTS engines: {e}")

    def _initialize_coqui_tts(self):
        """初始化Coqui TTS引擎"""
        try:
            import torch
            from TTS.api import TTS
            
            # 获取可用设备
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # 初始化多语言TTS
            self.tts_engines["coqui"] = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False,
                gpu=torch.cuda.is_available()
            )
            
            logger.info(f"Coqui TTS initialized on {device}")
            
        except ImportError:
            logger.warning("Coqui TTS not available, using fallback")
            self.tts_engines["coqui"] = None
        except Exception as e:
            logger.error(f"Error initializing Coqui TTS: {e}")
            self.tts_engines["coqui"] = None

    def _initialize_xtts(self):
        """初始化XTTS引擎"""
        try:
            # XTTS是Coqui TTS的一部分，已在上面的Coqui初始化中加载
            # 这里可以添加XTTS特定的配置
            self.tts_engines["xtts"] = self.tts_engines.get("coqui")
            logger.info("XTTS engine initialized")
            
        except Exception as e:
            logger.error(f"Error initializing XTTS: {e}")
            self.tts_engines["xtts"] = None

    def _initialize_backup_engines(self):
        """初始化备用TTS引擎"""
        try:
            # Microsoft Speech API (Windows)
            if os.name == 'nt':
                import win32com.client
                self.tts_engines["ms_sapi"] = win32com.client.Dispatch("SAPI.SpVoice")
                logger.info("Microsoft SAPI engine initialized")
            else:
                self.tts_engines["ms_sapi"] = None
                
            # eSpeak NG (跨平台)
            try:
                from espeakng import ESpeakNG
                self.tts_engines["espeak"] = ESpeakNG()
                logger.info("eSpeak NG engine initialized")
            except ImportError:
                self.tts_engines["espeak"] = None
                logger.warning("eSpeak NG not available")
                
        except Exception as e:
            logger.warning(f"Error initializing backup TTS engines: {e}")

    async def synthesize(self, text: str, config: TTSConfig = None) -> Optional[TTSResult]:
        """
        语音合成主方法 - 完整实现
        
        Args:
            text: 要合成的文本
            config: TTS配置
            
        Returns:
            TTSResult: 语音合成结果
        """
        start_time = time.time()
        
        try:
            # 使用默认配置如果未提供
            if config is None:
                config = TTSConfig()
            
            # 设置语音配置
            if config.voice_profile:
                voice_profile = config.voice_profile
            else:
                voice_profile = self.current_voice
            
            if not voice_profile:
                logger.error("No voice profile available")
                return None
            
            # 检查缓存
            cache_key = self._generate_cache_key(text, config, voice_profile)
            if config.cache_enabled and cache_key in self.audio_cache:
                self.stats["cache_hits"] += 1
                logger.debug(f"TTS result found in cache: {text[:50]}...")
                return self.audio_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            
            # 根据语言选择引擎
            engine = await self._select_engine(config, voice_profile)
            if not engine:
                logger.error("No available TTS engine")
                return None
            
            # 执行语音合成
            tts_result = await self._perform_synthesis(text, config, voice_profile, engine)
            if not tts_result:
                return None
            
            # 计算处理时间
            processing_time = time.time() - start_time
            tts_result.processing_time = processing_time
            
            # 更新统计
            self.stats["total_synthesized"] += 1
            self.stats["average_latency"] = (
                (self.stats["average_latency"] * (self.stats["total_synthesized"] - 1) + processing_time) 
                / self.stats["total_synthesized"]
            )
            
            # 缓存结果
            if config.cache_enabled:
                await self._cache_result(cache_key, tts_result)
            
            logger.info(f"TTS synthesis completed: {text[:50]}... "
                       f"(Time: {processing_time:.2f}s, "
                       f"Length: {len(tts_result.audio_data)/tts_result.sample_rate:.2f}s)")
            
            return tts_result
            
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
            return None

    async def _select_engine(self, config: TTSConfig, voice_profile: VoiceProfile) -> Any:
        """选择TTS引擎"""
        # 优先使用配置的引擎
        selected_engine_name = config.engine
        engine = self.tts_engines.get(selected_engine_name)
        
        # 如果首选引擎不可用，自动降级
        if not engine:
            # 语言无关的降级顺序：coqui/xtts -> ms_sapi -> espeak
            preferred = ["coqui", "xtts"]
            fallback = ["ms_sapi", "espeak"]
            for candidate in preferred + fallback:
                candidate_engine = self.tts_engines.get(candidate)
                if candidate_engine:
                    selected_engine_name = candidate
                    engine = candidate_engine
                    break
            
        # 关键：同步 config.engine 与实际引擎，避免后续分支判断失配
        config.engine = selected_engine_name
        
        return engine

    async def _perform_synthesis(self, text: str, config: TTSConfig, 
                               voice_profile: VoiceProfile, engine: Any) -> Optional[TTSResult]:
        """执行语音合成"""
        try:
            # 预处理文本
            processed_text = await self._preprocess_text(text, voice_profile.language)
            
            # 根据引擎类型执行合成
            if hasattr(engine, 'tts_to_file') or hasattr(engine, 'tts'):
                # Coqui TTS / XTTS
                return await self._synthesize_coqui(processed_text, config, voice_profile, engine)
            elif config.engine == "ms_sapi":
                # Microsoft SAPI
                return await self._synthesize_sapi(processed_text, config, voice_profile, engine)
            elif config.engine == "espeak":
                # eSpeak NG
                return await self._synthesize_espeak(processed_text, config, voice_profile, engine)
            else:
                logger.error(f"Unsupported TTS engine: {config.engine}")
                return None
                
        except Exception as e:
            logger.error(f"Error in TTS synthesis: {e}")
            return None

    async def _synthesize_coqui(self, text: str, config: TTSConfig, 
                               voice_profile: VoiceProfile, engine: Any) -> Optional[TTSResult]:
        """使用Coqui TTS合成语音"""
        try:
            import torch
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 语音合成参数
            synthesis_params = {
                "text": text,
                "speaker_wav": await self._get_voice_reference(voice_profile),
                "language": voice_profile.language,
                "file_path": temp_path
            }
            
            # 应用情感参数
            if config.emotion != EmotionType.NEUTRAL:
                emotion_params = await self._get_emotion_parameters(config.emotion, config.emotion_strength)
                synthesis_params.update(emotion_params)
                self.stats["emotion_applied"] += 1
            
            # 执行合成
            engine.tts_to_file(**synthesis_params)
            
            # 读取音频文件（避免依赖 soundfile）
            audio_data, sample_rate = self._read_wav_file(temp_path)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            # 分析音素和时长
            phonemes, durations = await self._analyze_phonemes(text, voice_profile.language)
            
            # 计算情感分数
            emotion_scores = await self._calculate_emotion_scores(config.emotion, config.emotion_strength)
            
            # 获取语音特征
            voice_characteristics = await self._extract_voice_characteristics(audio_data, sample_rate)
            
            return TTSResult(
                audio_data=audio_data,
                sample_rate=sample_rate,
                phonemes=phonemes,
                durations=durations,
                emotion_scores=emotion_scores,
                processing_time=0.0,  # 将在外部设置
                voice_characteristics=voice_characteristics
            )
            
        except Exception as e:
            logger.error(f"Error in Coqui TTS synthesis: {e}")
            return None

    async def _synthesize_sapi(self, text: str, config: TTSConfig,
                              voice_profile: VoiceProfile, engine: Any) -> Optional[TTSResult]:
        """使用Microsoft SAPI合成语音"""
        try:
            import tempfile
            import win32com.client
            
            # 设置语音
            voices = engine.GetVoices()
            suitable_voice = None
            
            for voice in voices:
                voice_language = voice.GetAttribute("Language")
                if voice_profile.language in str(voice_language):
                    suitable_voice = voice
                    break
            
            if suitable_voice:
                engine.Voice = suitable_voice
            
            # 设置语速和音量
            engine.Rate = int((voice_profile.speed - 1.0) * 10)  # -10 to 10
            engine.Volume = int(voice_profile.energy * 100)  # 0 to 100
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # 创建音频流
            from win32com.client import constants
            stream = win32com.client.Dispatch("SAPI.SpFileStream")

            # 某些环境下常量可能未生成，提供数值降级
            create_for_write = getattr(constants, "SSFMCreateForWrite", None)
            if create_for_write is None:
                create_for_write = 3

            stream.Open(temp_path, create_for_write)
            engine.AudioOutputStream = stream
            
            # 执行合成
            engine.Speak(text)
            stream.Close()
            
            # 读取音频文件
            audio_data, sample_rate = self._read_wav_file(temp_path)
            
            # 清理临时文件
            os.unlink(temp_path)
            
            # 生成基本结果
            return TTSResult(
                audio_data=audio_data,
                sample_rate=sample_rate,
                phonemes=[],
                durations=[],
                emotion_scores={},
                processing_time=0.0,
                voice_characteristics={}
            )
            
        except Exception as e:
            logger.error(f"Error in SAPI TTS synthesis: {e}")
            return None

    async def _synthesize_espeak(self, text: str, config: TTSConfig,
                               voice_profile: VoiceProfile, engine: Any) -> Optional[TTSResult]:
        """使用eSpeak NG合成语音"""
        try:
            # 设置语音参数
            engine.voice = voice_profile.language
            engine.pitch = int(50 + (voice_profile.pitch - 1.0) * 50)  # 0-100
            engine.speed = int(voice_profile.speed * 160)  # 80-450
            engine.amplitude = int(voice_profile.energy * 100)  # 0-200
            
            # 合成语音
            audio_data = engine.synth(text)
            
            # 转换为numpy数组
            if audio_data:
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                sample_rate = 22050  # eSpeak默认采样率
                
                return TTSResult(
                    audio_data=audio_array.astype(np.float32) / 32768.0,  # 归一化
                    sample_rate=sample_rate,
                    phonemes=[],
                    durations=[],
                    emotion_scores={},
                    processing_time=0.0,
                    voice_characteristics={}
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error in eSpeak TTS synthesis: {e}")
            return None

    def _read_wav_file(self, wav_path: str) -> Tuple[np.ndarray, int]:
        """
        读取 WAV 文件为 float32 numpy 数组（避免依赖 soundfile）。

        Returns:
            (audio_data, sample_rate)
        """
        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if sample_width == 1:
            # 8-bit unsigned PCM
            data = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        elif sample_width == 2:
            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sample_width == 4:
            data = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported WAV sample width: {sample_width}")

        if channels > 1:
            data = data.reshape(-1, channels)
        return data, int(sample_rate)

    async def _preprocess_text(self, text: str, language: str) -> str:
        """预处理文本"""
        try:
            # 移除多余空格和特殊字符
            text = ' '.join(text.split())
            
            # 语言特定的预处理
            if language.startswith("zh"):
                # 中文预处理：确保标点符号正确
                text = text.replace(' ,', '，').replace(' .', '。').replace(' !', '！').replace(' ?', '？')
            elif language.startswith("en"):
                # 英文预处理：扩展缩写
                text = text.replace("'re", " are").replace("'s", " is").replace("'ll", " will")
            
            return text
            
        except Exception as e:
            logger.warning(f"Error in text preprocessing: {e}")
            return text

    async def _get_voice_reference(self, voice_profile: VoiceProfile) -> str:
        """获取语音参考文件路径"""
        try:
            # 这里应该返回对应语音配置的参考音频文件路径
            # 实际实现中，这会从语音配置中获取预录制的参考音频
            voice_ref_dir = Path("data/voice_references")
            voice_ref_file = voice_ref_dir / f"{voice_profile.voice_id}.wav"
            
            if voice_ref_file.exists():
                return str(voice_ref_file)
            else:
                # 返回默认参考文件
                default_ref = voice_ref_dir / "default.wav"
                return str(default_ref) if default_ref.exists() else ""
                
        except Exception as e:
            logger.warning(f"Error getting voice reference: {e}")
            return ""

    async def _get_emotion_parameters(self, emotion: EmotionType, strength: float) -> Dict[str, Any]:
        """获取情感参数"""
        emotion_params = {
            EmotionType.NEUTRAL: {"speed": 1.0, "pitch": 1.0, "energy": 1.0},
            EmotionType.HAPPY: {"speed": 1.2, "pitch": 1.3, "energy": 1.4},
            EmotionType.SAD: {"speed": 0.8, "pitch": 0.7, "energy": 0.6},
            EmotionType.ANGRY: {"speed": 1.4, "pitch": 1.1, "energy": 1.6},
            EmotionType.EXCITED: {"speed": 1.3, "pitch": 1.4, "energy": 1.5},
            EmotionType.CALM: {"speed": 0.9, "pitch": 0.9, "energy": 0.8},
            EmotionType.SURPRISED: {"speed": 1.1, "pitch": 1.5, "energy": 1.3},
            EmotionType.FEARFUL: {"speed": 1.0, "pitch": 1.6, "energy": 0.7}
        }
        
        base_params = emotion_params.get(emotion, emotion_params[EmotionType.NEUTRAL])
        
        # 应用强度
        scaled_params = {}
        for key, value in base_params.items():
            # 强度在0.5-2.0之间缩放
            scaled_value = 1.0 + (value - 1.0) * strength
            scaled_params[key] = max(0.5, min(2.0, scaled_value))
        
        return scaled_params

    async def _analyze_phonemes(self, text: str, language: str) -> Tuple[List[str], List[float]]:
        """分析音素和时长"""
        try:
            # 这里应该使用音素分析器
            # 简化实现：基于文本长度估算
            words = text.split()
            phonemes = []
            durations = []
            
            for word in words:
                # 简单的音素分割（实际应该使用专业的音素分析）
                if language.startswith("zh"):
                    # 中文：每个字作为一个音素
                    for char in word:
                        if char.strip():
                            phonemes.append(char)
                            durations.append(0.2)  # 默认200ms
                else:
                    # 英文：简单的音节分割
                    syllables = self._split_english_syllables(word)
                    phonemes.extend(syllables)
                    durations.extend([0.15] * len(syllables))  # 默认150ms
            
            return phonemes, durations
            
        except Exception as e:
            logger.warning(f"Error in phoneme analysis: {e}")
            return [], []

    def _split_english_syllables(self, word: str) -> List[str]:
        """简单的英文音节分割"""
        # 这是一个简化的实现，实际应该使用专业的音节分割算法
        vowels = "aeiouAEIOU"
        syllables = []
        current_syllable = ""
        
        for char in word:
            current_syllable += char
            if char in vowels and len(current_syllable) > 1:
                syllables.append(current_syllable)
                current_syllable = ""
        
        if current_syllable:
            syllables.append(current_syllable)
        
        return syllables if syllables else [word]

    async def _calculate_emotion_scores(self, emotion: EmotionType, strength: float) -> Dict[str, float]:
        """计算情感分数"""
        base_scores = {
            EmotionType.NEUTRAL: {"valence": 0.5, "arousal": 0.5, "dominance": 0.5},
            EmotionType.HAPPY: {"valence": 0.9, "arousal": 0.7, "dominance": 0.6},
            EmotionType.SAD: {"valence": 0.2, "arousal": 0.3, "dominance": 0.3},
            EmotionType.ANGRY: {"valence": 0.3, "arousal": 0.9, "dominance": 0.8},
            EmotionType.EXCITED: {"valence": 0.8, "arousal": 0.9, "dominance": 0.7},
            EmotionType.CALM: {"valence": 0.6, "arousal": 0.2, "dominance": 0.4},
            EmotionType.SURPRISED: {"valence": 0.7, "arousal": 0.8, "dominance": 0.5},
            EmotionType.FEARFUL: {"valence": 0.3, "arousal": 0.9, "dominance": 0.2}
        }
        
        scores = base_scores.get(emotion, base_scores[EmotionType.NEUTRAL]).copy()
        
        # 应用强度
        for key in scores:
            scores[key] = 0.5 + (scores[key] - 0.5) * strength
        
        return scores

    async def _extract_voice_characteristics(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """提取语音特征"""
        try:
            characteristics = {}
            
            if len(audio_data) == 0:
                return characteristics
            
            # 基本统计特征
            characteristics["rms_energy"] = float(np.sqrt(np.mean(audio_data**2)))
            characteristics["peak_amplitude"] = float(np.max(np.abs(audio_data)))
            characteristics["zero_crossing_rate"] = float(np.mean(np.diff(np.sign(audio_data)) != 0))
            
            # 频谱特征（简化）
            if len(audio_data) > 1024:
                spectrum = np.abs(np.fft.fft(audio_data[:1024]))
                characteristics["spectral_centroid"] = float(np.sum(spectrum * np.arange(len(spectrum))) / np.sum(spectrum))
            
            return characteristics
            
        except Exception as e:
            logger.warning(f"Error extracting voice characteristics: {e}")
            return {}

    def _generate_cache_key(self, text: str, config: TTSConfig, voice_profile: VoiceProfile) -> str:
        """生成缓存键"""
        import hashlib
        
        key_data = f"{text}_{config.engine}_{voice_profile.voice_id}_{config.emotion.value}_{config.emotion_strength}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _cache_result(self, cache_key: str, result: TTSResult):
        """缓存结果"""
        try:
            # 计算缓存大小
            result_size = result.audio_data.nbytes if hasattr(result.audio_data, 'nbytes') else len(result.audio_data) * 4
            
            # 检查缓存限制
            while self.current_cache_size + result_size > self.cache_size_limit and self.audio_cache:
                # 移除最旧的缓存项
                oldest_key = min(self.audio_cache.keys(), key=lambda k: self.audio_cache[k].processing_time)
                oldest_result = self.audio_cache[oldest_key]
                oldest_size = oldest_result.audio_data.nbytes if hasattr(oldest_result.audio_data, 'nbytes') else len(oldest_result.audio_data) * 4
                self.current_cache_size -= oldest_size
                del self.audio_cache[oldest_key]
            
            # 添加新缓存
            self.audio_cache[cache_key] = result
            self.current_cache_size += result_size
            
        except Exception as e:
            logger.warning(f"Error caching TTS result: {e}")

    async def set_voice_profile(self, voice_id: str) -> bool:
        """设置当前语音配置"""
        try:
            if voice_id not in self.voice_profiles:
                logger.error(f"Voice profile not found: {voice_id}")
                return False
            
            self.current_voice = self.voice_profiles[voice_id]
            logger.info(f"Voice profile set to: {voice_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting voice profile: {e}")
            return False

    async def create_custom_voice(self, name: str, gender: VoiceGender, age: VoiceAge,
                                language: str, reference_audio: str = None) -> Optional[VoiceProfile]:
        """创建自定义语音"""
        try:
            voice_id = f"custom_{name.lower()}_{int(time.time())}"
            
            voice_profile = VoiceProfile(
                voice_id=voice_id,
                name=name,
                gender=gender,
                age=age,
                language=language
            )
            
            # 如果有参考音频，进行语音克隆
            if reference_audio and os.path.exists(reference_audio):
                cloning_result = await self.voice_cloning.clone_voice(reference_audio, voice_profile)
                if cloning_result:
                    voice_profile.voice_characteristics = cloning_result
            
            self.voice_profiles[voice_id] = voice_profile
            logger.info(f"Custom voice created: {voice_id}")
            
            return voice_profile
            
        except Exception as e:
            logger.error(f"Error creating custom voice: {e}")
            return None

    async def synthesize_realtime(self, text: str, callback: callable, 
                                config: TTSConfig = None) -> bool:
        """实时语音合成"""
        try:
            self.stats["real_time_synthesis"] += 1
            
            # 使用流式合成
            if config is None:
                config = TTSConfig(realtime=True)
            
            # 分块处理文本
            chunks = self._split_text_chunks(text)
            
            for chunk in chunks:
                result = await self.synthesize(chunk, config)
                if result and callback:
                    await callback(result.audio_data, result.sample_rate)
                    # 模拟实时延迟
                    await asyncio.sleep(len(result.audio_data) / result.sample_rate)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in realtime TTS: {e}")
            return False

    def _split_text_chunks(self, text: str, max_chunk_length: int = 50) -> List[str]:
        """分割文本块"""
        sentences = text.split('。') if '。' in text else text.split('.')
        chunks = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(sentence) <= max_chunk_length:
                chunks.append(sentence)
            else:
                # 进一步分割长句子
                words = sentence.split()
                current_chunk = ""
                
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_chunk_length:
                        current_chunk += " " + word if current_chunk else word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = word
                
                if current_chunk:
                    chunks.append(current_chunk)
        
        return chunks

    async def get_available_voices(self, language: str = None) -> List[VoiceProfile]:
        """获取可用语音列表"""
        if language:
            return [vp for vp in self.voice_profiles.values() if vp.language.startswith(language)]
        else:
            return list(self.voice_profiles.values())

    async def get_voice_info(self, voice_id: str) -> Optional[VoiceProfile]:
        """获取语音信息"""
        return self.voice_profiles.get(voice_id)

    async def export_voice(self, voice_id: str, export_path: str) -> bool:
        """导出语音配置"""
        try:
            voice_profile = self.voice_profiles.get(voice_id)
            if not voice_profile:
                return False
            
            import json
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(voice_profile.__dict__, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Voice profile exported: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting voice profile: {e}")
            return False

    async def import_voice(self, import_path: str) -> Optional[VoiceProfile]:
        """导入语音配置"""
        try:
            import json
            with open(import_path, 'r', encoding='utf-8') as f:
                voice_data = json.load(f)
            
            voice_profile = VoiceProfile(**voice_data)
            self.voice_profiles[voice_profile.voice_id] = voice_profile
            
            logger.info(f"Voice profile imported: {voice_profile.voice_id}")
            return voice_profile
            
        except Exception as e:
            logger.error(f"Error importing voice profile: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["voice_profiles_count"] = len(self.voice_profiles)
        stats["cache_size_mb"] = self.current_cache_size / (1024 * 1024)
        stats["cache_entries"] = len(self.audio_cache)
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.audio_cache.clear()
            self.current_cache_size = 0
            
            # 清理引擎资源
            for engine_name, engine in self.tts_engines.items():
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            
            logger.info("Multilingual TTS system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during TTS cleanup: {e}")

# 全局TTS实例
multilingual_tts = MultilingualTTS()

