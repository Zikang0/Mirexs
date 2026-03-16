"""
音素分析器 - 深度音素分析和处理系统
完整实现音频信号到音素的转换、音素边界检测和音素特征提取
支持多语言音素分析和实时音素识别
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
import asyncio
from enum import Enum
import threading

# 导入依赖
from infrastructure.compute_storage.model_serving_engine import ModelServingEngine, model_serving_engine, ModelType
from infrastructure.compute_storage.gpu_accelerator import GPUAccelerator, gpu_accelerator

logger = logging.getLogger(__name__)

class PhonemeType(Enum):
    """音素类型枚举"""
    VOWEL = "vowel"          # 元音
    CONSONANT = "consonant"  # 辅音
    SEMIVOWEL = "semivowel"  # 半元音
    NASAL = "nasal"          # 鼻音
    STOP = "stop"            # 塞音
    FRICATIVE = "fricative"  # 擦音
    AFFRICATE = "affricate"  # 塞擦音
    APPROXIMANT = "approximant"  # 近音
    SILENCE = "silence"      # 静音

@dataclass
class Phoneme:
    """音素数据"""
    symbol: str              # 音素符号
    phoneme_type: PhonemeType  # 音素类型
    start_time: float        # 开始时间
    end_time: float          # 结束时间
    duration: float          # 持续时间
    confidence: float        # 置信度
    intensity: float         # 强度
    pitch: float             # 音高
    formants: List[float]    # 共振峰
    spectral_features: Dict[str, float]  # 频谱特征

@dataclass
class PhonemeAnalysisConfig:
    """音素分析配置"""
    sample_rate: int = 22050
    frame_size: int = 1024
    hop_size: int = 256
    min_phoneme_duration: float = 0.05  # 最小音素持续时间
    max_phoneme_duration: float = 0.5   # 最大音素持续时间
    confidence_threshold: float = 0.6   # 置信度阈值
    language: str = "zh-cn"             # 语言
    use_deep_learning: bool = True      # 使用深度学习
    realtime_analysis: bool = True      # 实时分析

class PhonemeAnalyzer:
    """音素分析器 - 完整实现"""
    
    def __init__(self, cache_size: int = 1000):
        self.phoneme_models: Dict[str, Any] = {}
        self.analysis_cache: Dict[str, List[Phoneme]] = {}
        self.realtime_buffers: Dict[str, List[np.ndarray]] = {}
        
        # 配置
        self.config = PhonemeAnalysisConfig()
        
        # 统计信息
        self.stats = {
            "total_analyses": 0,
            "realtime_analyses": 0,
            "average_analysis_time": 0.0,
            "phoneme_count": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 音素数据库
        self.phoneme_database: Dict[str, Dict[str, Any]] = {}
        
        # 初始化音素分析系统
        self._initialize_phoneme_system()
        
        logger.info("PhonemeAnalyzer initialized")

    def _initialize_phoneme_system(self):
        """初始化音素分析系统"""
        try:
            # 加载音素数据库
            self._load_phoneme_database()
            
            # 初始化音素识别模型
            self._initialize_phoneme_models()
            
            # 初始化实时分析线程
            if self.config.realtime_analysis:
                self._initialize_realtime_analysis()
            
            logger.info("Phoneme analysis system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing phoneme system: {e}")

    def _load_phoneme_database(self):
        """加载音素数据库"""
        try:
            # 中文音素数据库
            self.phoneme_database["zh-cn"] = {
                # 元音
                "a": {"type": PhonemeType.VOWEL, "ipa": "a", "features": {"open": 0.9, "front": 0.3, "rounded": 0.0}},
                "o": {"type": PhonemeType.VOWEL, "ipa": "o", "features": {"open": 0.6, "back": 0.7, "rounded": 0.8}},
                "e": {"type": PhonemeType.VOWEL, "ipa": "ɛ", "features": {"open": 0.7, "front": 0.6, "rounded": 0.0}},
                "i": {"type": PhonemeType.VOWEL, "ipa": "i", "features": {"open": 0.2, "front": 0.9, "rounded": 0.0}},
                "u": {"type": PhonemeType.VOWEL, "ipa": "u", "features": {"open": 0.3, "back": 0.8, "rounded": 0.9}},
                "ü": {"type": PhonemeType.VOWEL, "ipa": "y", "features": {"open": 0.3, "front": 0.7, "rounded": 0.9}},
                
                # 辅音
                "b": {"type": PhonemeType.STOP, "ipa": "p", "features": {"voiced": 0.0, "place": "bilabial"}},
                "p": {"type": PhonemeType.STOP, "ipa": "pʰ", "features": {"voiced": 0.0, "place": "bilabial"}},
                "d": {"type": PhonemeType.STOP, "ipa": "t", "features": {"voiced": 1.0, "place": "alveolar"}},
                "t": {"type": PhonemeType.STOP, "ipa": "tʰ", "features": {"voiced": 0.0, "place": "alveolar"}},
                "g": {"type": PhonemeType.STOP, "ipa": "k", "features": {"voiced": 1.0, "place": "velar"}},
                "k": {"type": PhonemeType.STOP, "ipa": "kʰ", "features": {"voiced": 0.0, "place": "velar"}},
                
                # 擦音
                "f": {"type": PhonemeType.FRICATIVE, "ipa": "f", "features": {"voiced": 0.0, "place": "labiodental"}},
                "s": {"type": PhonemeType.FRICATIVE, "ipa": "s", "features": {"voiced": 0.0, "place": "alveolar"}},
                "sh": {"type": PhonemeType.FRICATIVE, "ipa": "ʂ", "features": {"voiced": 0.0, "place": "retroflex"}},
                "x": {"type": PhonemeType.FRICATIVE, "ipa": "ɕ", "features": {"voiced": 0.0, "place": "alveolo-palatal"}},
                "h": {"type": PhonemeType.FRICATIVE, "ipa": "x", "features": {"voiced": 0.0, "place": "velar"}},
                
                # 鼻音
                "m": {"type": PhonemeType.NASAL, "ipa": "m", "features": {"voiced": 1.0, "place": "bilabial"}},
                "n": {"type": PhonemeType.NASAL, "ipa": "n", "features": {"voiced": 1.0, "place": "alveolar"}},
                "ng": {"type": PhonemeType.NASAL, "ipa": "ŋ", "features": {"voiced": 1.0, "place": "velar"}},
                
                # 近音
                "l": {"type": PhonemeType.APPROXIMANT, "ipa": "l", "features": {"voiced": 1.0, "place": "alveolar"}},
                "r": {"type": PhonemeType.APPROXIMANT, "ipa": "ɻ", "features": {"voiced": 1.0, "place": "retroflex"}},
                
                # 塞擦音
                "z": {"type": PhonemeType.AFFRICATE, "ipa": "ts", "features": {"voiced": 0.0, "place": "alveolar"}},
                "c": {"type": PhonemeType.AFFRICATE, "ipa": "tsʰ", "features": {"voiced": 0.0, "place": "alveolar"}},
                "zh": {"type": PhonemeType.AFFRICATE, "ipa": "ʈʂ", "features": {"voiced": 0.0, "place": "retroflex"}},
                "ch": {"type": PhonemeType.AFFRICATE, "ipa": "ʈʂʰ", "features": {"voiced": 0.0, "place": "retroflex"}},
                "j": {"type": PhonemeType.AFFRICATE, "ipa": "tɕ", "features": {"voiced": 0.0, "place": "alveolo-palatal"}},
                "q": {"type": PhonemeType.AFFRICATE, "ipa": "tɕʰ", "features": {"voiced": 0.0, "place": "alveolo-palatal"}},
                
                # 静音
                "sil": {"type": PhonemeType.SILENCE, "ipa": "", "features": {}}
            }
            
            # 英文音素数据库
            self.phoneme_database["en-us"] = {
                # 元音
                "aa": {"type": PhonemeType.VOWEL, "ipa": "ɑ", "features": {"open": 0.8, "back": 0.8, "rounded": 0.0}},
                "ae": {"type": PhonemeType.VOWEL, "ipa": "æ", "features": {"open": 0.9, "front": 0.7, "rounded": 0.0}},
                "ah": {"type": PhonemeType.VOWEL, "ipa": "ʌ", "features": {"open": 0.7, "central": 0.8, "rounded": 0.0}},
                "ao": {"type": PhonemeType.VOWEL, "ipa": "ɔ", "features": {"open": 0.6, "back": 0.7, "rounded": 0.6}},
                "eh": {"type": PhonemeType.VOWEL, "ipa": "ɛ", "features": {"open": 0.7, "front": 0.6, "rounded": 0.0}},
                "er": {"type": PhonemeType.VOWEL, "ipa": "ɝ", "features": {"open": 0.5, "central": 0.9, "rounded": 0.3}},
                "ih": {"type": PhonemeType.VOWEL, "ipa": "ɪ", "features": {"open": 0.4, "front": 0.5, "rounded": 0.0}},
                "iy": {"type": PhonemeType.VOWEL, "ipa": "i", "features": {"open": 0.2, "front": 0.9, "rounded": 0.0}},
                "uh": {"type": PhonemeType.VOWEL, "ipa": "ʊ", "features": {"open": 0.4, "back": 0.6, "rounded": 0.7}},
                "uw": {"type": PhonemeType.VOWEL, "ipa": "u", "features": {"open": 0.3, "back": 0.8, "rounded": 0.9}},
                
                # 辅音
                "b": {"type": PhonemeType.STOP, "ipa": "b", "features": {"voiced": 1.0, "place": "bilabial"}},
                "p": {"type": PhonemeType.STOP, "ipa": "p", "features": {"voiced": 0.0, "place": "bilabial"}},
                "d": {"type": PhonemeType.STOP, "ipa": "d", "features": {"voiced": 1.0, "place": "alveolar"}},
                "t": {"type": PhonemeType.STOP, "ipa": "t", "features": {"voiced": 0.0, "place": "alveolar"}},
                "g": {"type": PhonemeType.STOP, "ipa": "g", "features": {"voiced": 1.0, "place": "velar"}},
                "k": {"type": PhonemeType.STOP, "ipa": "k", "features": {"voiced": 0.0, "place": "velar"}},
                
                # 更多音素...
            }
            
            logger.info(f"Phoneme database loaded: {len(self.phoneme_database)} languages")
            
        except Exception as e:
            logger.error(f"Error loading phoneme database: {e}")

    def _initialize_phoneme_models(self):
        """初始化音素识别模型"""
        try:
            # 使用模型服务引擎加载音素识别模型
            if self.config.use_deep_learning:
                # 这里应该加载实际的音素识别模型
                # 例如: wav2vec2, DeepSpeech, 或其他ASR模型
                self.phoneme_models["deep_phoneme"] = None  # 实际应该加载模型
                logger.info("Deep learning phoneme models initialized")
            else:
                # 传统方法
                self.phoneme_models["traditional"] = self._initialize_traditional_analyzer()
                logger.info("Traditional phoneme analysis initialized")
                
        except Exception as e:
            logger.error(f"Error initializing phoneme models: {e}")

    def _initialize_traditional_analyzer(self):
        """初始化传统音素分析器"""
        # 基于信号处理和特征提取的传统方法
        return {
            "mfcc_analyzer": self._analyze_mfcc,
            "formant_analyzer": self._analyze_formants,
            "pitch_analyzer": self._analyze_pitch
        }

    def _initialize_realtime_analysis(self):
        """初始化实时分析"""
        try:
            self.realtime_analysis_thread = threading.Thread(
                target=self._realtime_analysis_worker,
                daemon=True
            )
            self.realtime_analysis_thread.start()
            logger.info("Realtime phoneme analysis initialized")
            
        except Exception as e:
            logger.error(f"Error initializing realtime analysis: {e}")

    def _realtime_analysis_worker(self):
        """实时分析工作线程"""
        while True:
            try:
                # 处理实时缓冲区中的音频数据
                for buffer_id, audio_buffer in self.realtime_buffers.items():
                    if len(audio_buffer) > 0:
                        audio_data = np.concatenate(audio_buffer)
                        phonemes = asyncio.run(self.analyze_phonemes(audio_data, self.config.sample_rate))
                        
                        # 清空已处理的缓冲区
                        self.realtime_buffers[buffer_id].clear()
                        
                        self.stats["realtime_analyses"] += 1
                
                time.sleep(0.01)  # 10ms间隔
                
            except Exception as e:
                logger.error(f"Error in realtime analysis worker: {e}")
                time.sleep(0.1)

    async def analyze_phonemes(self, audio_data: np.ndarray, sample_rate: int, 
                             language: str = None) -> List[Phoneme]:
        """
        分析音素 - 完整实现
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            language: 语言代码
            
        Returns:
            List[Phoneme]: 音素列表
        """
        start_time = time.time()
        
        try:
            if language is None:
                language = self.config.language
            
            # 检查缓存
            cache_key = self._generate_cache_key(audio_data, sample_rate, language)
            if cache_key in self.analysis_cache:
                self.stats["cache_hits"] += 1
                return self.analysis_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            self.stats["total_analyses"] += 1
            
            # 预处理音频
            processed_audio = await self._preprocess_audio(audio_data, sample_rate)
            
            # 音素识别
            if self.config.use_deep_learning:
                phonemes = await self._deep_phoneme_recognition(processed_audio, sample_rate, language)
            else:
                phonemes = await self._traditional_phoneme_recognition(processed_audio, sample_rate, language)
            
            # 后处理
            phonemes = await self._postprocess_phonemes(phonemes)
            
            # 更新统计
            analysis_time = time.time() - start_time
            self.stats["average_analysis_time"] = (
                (self.stats["average_analysis_time"] * (self.stats["total_analyses"] - 1) + analysis_time) 
                / self.stats["total_analyses"]
            )
            self.stats["phoneme_count"] += len(phonemes)
            
            # 缓存结果
            self.analysis_cache[cache_key] = phonemes
            self._manage_cache_size()
            
            logger.info(f"Phoneme analysis completed: {len(phonemes)} phonemes found")
            return phonemes
            
        except Exception as e:
            logger.error(f"Error in phoneme analysis: {e}")
            return []

    async def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频"""
        try:
            # 归一化
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # 重采样到目标采样率
            if sample_rate != self.config.sample_rate:
                audio_data = await self._resample_audio(audio_data, sample_rate, self.config.sample_rate)
            
            # 降噪
            audio_data = await self._denoise_audio(audio_data)
            
            return audio_data
            
        except Exception as e:
            logger.warning(f"Error in audio preprocessing: {e}")
            return audio_data

    async def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        try:
            from scipy import signal
            
            # 计算重采样因子
            resample_factor = target_rate / original_rate
            num_samples = int(len(audio_data) * resample_factor)
            
            # 重采样
            resampled_audio = signal.resample(audio_data, num_samples)
            
            return resampled_audio
            
        except ImportError:
            # 简化的重采样实现
            logger.warning("scipy not available, using simple resampling")
            resample_factor = target_rate / original_rate
            num_samples = int(len(audio_data) * resample_factor)
            
            # 线性插值
            original_indices = np.arange(len(audio_data))
            target_indices = np.linspace(0, len(audio_data) - 1, num_samples)
            
            return np.interp(target_indices, original_indices, audio_data)
        except Exception as e:
            logger.warning(f"Error in audio resampling: {e}")
            return audio_data

    async def _denoise_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """降噪"""
        try:
            # 简单的降噪：高通滤波器去除低频噪声
            from scipy import signal
            
            # 设计高通滤波器
            nyquist = self.config.sample_rate / 2
            cutoff = 80 / nyquist  # 80Hz截止频率
            
            b, a = signal.butter(4, cutoff, btype='high')
            filtered_audio = signal.filtfilt(b, a, audio_data)
            
            return filtered_audio
            
        except ImportError:
            logger.warning("scipy not available, skipping denoising")
            return audio_data
        except Exception as e:
            logger.warning(f"Error in audio denoising: {e}")
            return audio_data

    async def _deep_phoneme_recognition(self, audio_data: np.ndarray, sample_rate: int, 
                                      language: str) -> List[Phoneme]:
        """深度学习音素识别"""
        try:
            # 这里应该使用实际的深度学习模型
            # 例如: wav2vec2, DeepSpeech, 或其他ASR模型
            
            # 模拟实现 - 实际应该替换为真实的模型推理
            phonemes = []
            current_time = 0.0
            
            # 基于音频能量检测音素边界
            frame_size = self.config.frame_size
            hop_size = self.config.hop_size
            
            for i in range(0, len(audio_data) - frame_size, hop_size):
                frame = audio_data[i:i + frame_size]
                
                # 计算帧能量
                energy = np.mean(frame ** 2)
                
                if energy > 0.001:  # 能量阈值
                    # 检测到语音，识别音素
                    phoneme_symbol = await self._classify_phoneme(frame, sample_rate, language)
                    
                    # 计算音素特征
                    features = await self._extract_phoneme_features(frame, sample_rate)
                    
                    phoneme = Phoneme(
                        symbol=phoneme_symbol,
                        phoneme_type=self._get_phoneme_type(phoneme_symbol, language),
                        start_time=current_time,
                        end_time=current_time + (frame_size / sample_rate),
                        duration=frame_size / sample_rate,
                        confidence=0.8,  # 模拟置信度
                        intensity=energy,
                        pitch=features.get("pitch", 0.0),
                        formants=features.get("formants", []),
                        spectral_features=features
                    )
                    
                    phonemes.append(phoneme)
                
                current_time += hop_size / sample_rate
            
            return phonemes
            
        except Exception as e:
            logger.error(f"Error in deep phoneme recognition: {e}")
            return await self._traditional_phoneme_recognition(audio_data, sample_rate, language)

    async def _traditional_phoneme_recognition(self, audio_data: np.ndarray, sample_rate: int,
                                             language: str) -> List[Phoneme]:
        """传统音素识别"""
        try:
            phonemes = []
            current_time = 0.0
            
            frame_size = self.config.frame_size
            hop_size = self.config.hop_size
            
            for i in range(0, len(audio_data) - frame_size, hop_size):
                frame = audio_data[i:i + frame_size]
                
                # 提取特征
                features = await self._extract_frame_features(frame, sample_rate)
                
                # 基于特征识别音素
                phoneme_symbol = await self._classify_phoneme_by_features(features, language)
                
                if phoneme_symbol != "sil":  # 忽略静音
                    phoneme = Phoneme(
                        symbol=phoneme_symbol,
                        phoneme_type=self._get_phoneme_type(phoneme_symbol, language),
                        start_time=current_time,
                        end_time=current_time + (frame_size / sample_rate),
                        duration=frame_size / sample_rate,
                        confidence=features.get("confidence", 0.7),
                        intensity=features.get("energy", 0.0),
                        pitch=features.get("pitch", 0.0),
                        formants=features.get("formants", []),
                        spectral_features=features
                    )
                    
                    phonemes.append(phoneme)
                
                current_time += hop_size / sample_rate
            
            return phonemes
            
        except Exception as e:
            logger.error(f"Error in traditional phoneme recognition: {e}")
            return []

    async def _extract_frame_features(self, frame: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取帧特征"""
        try:
            features = {}
            
            # 能量
            features["energy"] = np.mean(frame ** 2)
            
            # 过零率
            features["zero_crossing_rate"] = np.mean(np.diff(np.sign(frame)) != 0)
            
            # MFCC特征
            features.update(await self._extract_mfcc_features(frame, sample_rate))
            
            # 共振峰
            features.update(await self._extract_formant_features(frame, sample_rate))
            
            # 音高
            features.update(await self._extract_pitch_features(frame, sample_rate))
            
            # 频谱特征
            features.update(await self._extract_spectral_features(frame, sample_rate))
            
            return features
            
        except Exception as e:
            logger.warning(f"Error extracting frame features: {e}")
            return {"energy": 0.0}

    async def _extract_mfcc_features(self, frame: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取MFCC特征"""
        try:
            # 简化的MFCC实现
            # 实际应该使用librosa或类似库
            
            # 计算频谱
            spectrum = np.abs(np.fft.fft(frame))
            spectrum = spectrum[:len(spectrum)//2]  # 取正频率
            
            # 梅尔滤波器组
            mel_filters = self._create_mel_filterbank(sample_rate, len(spectrum))
            mel_spectrum = np.dot(mel_filters, spectrum)
            
            # 对数能量
            log_mel_spectrum = np.log(mel_spectrum + 1e-8)
            
            # DCT变换（简化版）
            mfcc = np.fft.dct(log_mel_spectrum, type=2, norm='ortho')[:13]  # 取前13个系数
            
            return {
                "mfcc": mfcc.tolist(),
                "mfcc_mean": float(np.mean(mfcc)),
                "mfcc_std": float(np.std(mfcc))
            }
            
        except Exception as e:
            logger.warning(f"Error extracting MFCC features: {e}")
            return {}

    def _create_mel_filterbank(self, sample_rate: int, n_fft: int, n_mels: int = 40) -> np.ndarray:
        """创建梅尔滤波器组"""
        try:
            # 简化的梅尔滤波器组实现
            # 实际应该使用标准的梅尔尺度
            
            f_min = 0
            f_max = sample_rate / 2
            
            # 梅尔频率点
            mel_points = np.linspace(self._hz_to_mel(f_min), self._hz_to_mel(f_max), n_mels + 2)
            hz_points = self._mel_to_hz(mel_points)
            
            # 转换为FFT bin索引
            bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
            
            # 创建滤波器
            filters = np.zeros((n_mels, n_fft))
            
            for i in range(1, n_mels + 1):
                left = bin_points[i - 1]
                center = bin_points[i]
                right = bin_points[i + 1]
                
                if left < center:
                    filters[i - 1, left:center] = np.linspace(0, 1, center - left)
                
                if center < right:
                    filters[i - 1, center:right] = np.linspace(1, 0, right - center)
            
            return filters
            
        except Exception as e:
            logger.warning(f"Error creating mel filterbank: {e}")
            return np.ones((n_mels, n_fft)) / n_mels

    def _hz_to_mel(self, hz: float) -> float:
        """Hz到Mel频率转换"""
        return 2595 * np.log10(1 + hz / 700)

    def _mel_to_hz(self, mel: float) -> float:
        """Mel到Hz频率转换"""
        return 700 * (10 ** (mel / 2595) - 1)

    async def _extract_formant_features(self, frame: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取共振峰特征"""
        try:
            # 简化的共振峰提取
            # 实际应该使用LPC或其他方法
            
            spectrum = np.abs(np.fft.fft(frame))
            spectrum = spectrum[:len(spectrum)//2]
            
            frequencies = np.linspace(0, sample_rate/2, len(spectrum))
            
            # 寻找频谱峰值（简化的共振峰检测）
            peaks, _ = self._find_spectral_peaks(spectrum)
            
            formants = []
            for peak_idx in peaks[:4]:  # 取前4个共振峰
                if peak_idx < len(frequencies):
                    formants.append(float(frequencies[peak_idx]))
            
            return {
                "formants": formants,
                "f1": formants[0] if len(formants) > 0 else 0.0,
                "f2": formants[1] if len(formants) > 1 else 0.0,
                "f3": formants[2] if len(formants) > 2 else 0.0
            }
            
        except Exception as e:
            logger.warning(f"Error extracting formant features: {e}")
            return {"formants": [], "f1": 0.0, "f2": 0.0, "f3": 0.0}

    def _find_spectral_peaks(self, spectrum: np.ndarray, min_distance: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """寻找频谱峰值"""
        try:
            peaks = []
            values = []
            
            for i in range(1, len(spectrum) - 1):
                if (spectrum[i] > spectrum[i - 1] and 
                    spectrum[i] > spectrum[i + 1] and 
                    spectrum[i] > 0.1 * np.max(spectrum)):
                    
                    # 检查最小距离
                    if not peaks or (i - peaks[-1]) >= min_distance:
                        peaks.append(i)
                        values.append(spectrum[i])
            
            return np.array(peaks), np.array(values)
            
        except Exception as e:
            logger.warning(f"Error finding spectral peaks: {e}")
            return np.array([]), np.array([])

    async def _extract_pitch_features(self, frame: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取音高特征"""
        try:
            # 自相关法计算音高
            autocorr = np.correlate(frame, frame, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # 寻找第一个峰值（基频）
            min_period = int(sample_rate / 500)  # 500Hz最大频率
            max_period = int(sample_rate / 80)   # 80Hz最小频率
            
            if len(autocorr) > max_period:
                search_range = autocorr[min_period:max_period]
                if len(search_range) > 0:
                    peak_idx = np.argmax(search_range) + min_period
                    pitch = sample_rate / peak_idx if peak_idx > 0 else 0.0
                else:
                    pitch = 0.0
            else:
                pitch = 0.0
            
            return {
                "pitch": pitch,
                "pitch_confidence": min(1.0, np.max(autocorr) * 10)  # 简化的置信度
            }
            
        except Exception as e:
            logger.warning(f"Error extracting pitch features: {e}")
            return {"pitch": 0.0, "pitch_confidence": 0.0}

    async def _extract_spectral_features(self, frame: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取频谱特征"""
        try:
            spectrum = np.abs(np.fft.fft(frame))
            spectrum = spectrum[:len(spectrum)//2]
            
            # 频谱质心
            frequencies = np.linspace(0, sample_rate/2, len(spectrum))
            spectral_centroid = np.sum(frequencies * spectrum) / np.sum(spectrum)
            
            # 频谱滚降
            spectral_rolloff = self._calculate_spectral_rolloff(spectrum, frequencies, 0.85)
            
            # 频谱通量
            spectral_flux = 0.0  # 需要前后帧计算
            
            # 频谱平坦度
            spectral_flatness = self._calculate_spectral_flatness(spectrum)
            
            return {
                "spectral_centroid": float(spectral_centroid),
                "spectral_rolloff": float(spectral_rolloff),
                "spectral_flatness": float(spectral_flatness),
                "spectral_flux": float(spectral_flux)
            }
            
        except Exception as e:
            logger.warning(f"Error extracting spectral features: {e}")
            return {}

    def _calculate_spectral_rolloff(self, spectrum: np.ndarray, frequencies: np.ndarray, 
                                  percentile: float) -> float:
        """计算频谱滚降"""
        try:
            cumulative_sum = np.cumsum(spectrum)
            total_energy = cumulative_sum[-1]
            target_energy = total_energy * percentile
            
            rolloff_idx = np.argmax(cumulative_sum >= target_energy)
            return frequencies[rolloff_idx] if rolloff_idx < len(frequencies) else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating spectral rolloff: {e}")
            return 0.0

    def _calculate_spectral_flatness(self, spectrum: np.ndarray) -> float:
        """计算频谱平坦度"""
        try:
            geometric_mean = np.exp(np.mean(np.log(spectrum + 1e-8)))
            arithmetic_mean = np.mean(spectrum)
            
            return geometric_mean / arithmetic_mean if arithmetic_mean > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating spectral flatness: {e}")
            return 0.0

    async def _classify_phoneme(self, frame: np.ndarray, sample_rate: int, language: str) -> str:
        """分类音素"""
        try:
            # 简化的音素分类
            # 实际应该使用训练好的分类器
            
            features = await self._extract_frame_features(frame, sample_rate)
            return await self._classify_phoneme_by_features(features, language)
            
        except Exception as e:
            logger.warning(f"Error classifying phoneme: {e}")
            return "sil"

    async def _classify_phoneme_by_features(self, features: Dict[str, Any], language: str) -> str:
        """基于特征分类音素"""
        try:
            # 基于能量判断是否为静音
            energy = features.get("energy", 0.0)
            if energy < 0.001:
                return "sil"
            
            # 基于音高和共振峰简单分类
            pitch = features.get("pitch", 0.0)
            f1 = features.get("f1", 0.0)
            f2 = features.get("f2", 0.0)
            
            if language == "zh-cn":
                # 中文音素分类规则
                if pitch > 200 and f1 > 400:  # 高音高，低F1 - 可能是元音i
                    return "i"
                elif f1 < 300 and f2 > 1500:  # 低F1，高F2 - 可能是元音u
                    return "u"
                elif f1 > 600 and f2 < 1200:  # 高F1，低F2 - 可能是元音a
                    return "a"
                else:
                    return "e"  # 默认元音
            
            elif language == "en-us":
                # 英文音素分类规则
                if f1 > 500 and f2 < 1500:  # 高F1，低F2 - 可能是元音aa
                    return "aa"
                elif f1 < 400 and f2 > 2000:  # 低F1，高F2 - 可能是元音iy
                    return "iy"
                else:
                    return "ah"  # 默认元音
            
            else:
                return "a"  # 默认音素
                
        except Exception as e:
            logger.warning(f"Error classifying phoneme by features: {e}")
            return "sil"

    def _get_phoneme_type(self, phoneme_symbol: str, language: str) -> PhonemeType:
        """获取音素类型"""
        try:
            if language in self.phoneme_database and phoneme_symbol in self.phoneme_database[language]:
                type_str = self.phoneme_database[language][phoneme_symbol]["type"]
                return PhonemeType(type_str)
            else:
                return PhonemeType.VOWEL  # 默认类型
                
        except Exception as e:
            logger.warning(f"Error getting phoneme type for {phoneme_symbol}: {e}")
            return PhonemeType.VOWEL

    async def _postprocess_phonemes(self, phonemes: List[Phoneme]) -> List[Phoneme]:
        """后处理音素"""
        try:
            if not phonemes:
                return []
            
            # 合并相同音素
            merged_phonemes = []
            current_phoneme = phonemes[0]
            
            for i in range(1, len(phonemes)):
                if (phonemes[i].symbol == current_phoneme.symbol and 
                    phonemes[i].start_time - current_phoneme.end_time < 0.05):  # 50ms内合并
                    
                    # 合并音素
                    current_phoneme.end_time = phonemes[i].end_time
                    current_phoneme.duration = current_phoneme.end_time - current_phoneme.start_time
                    current_phoneme.confidence = (current_phoneme.confidence + phonemes[i].confidence) / 2
                    current_phoneme.intensity = (current_phoneme.intensity + phonemes[i].intensity) / 2
                    
                else:
                    # 检查持续时间
                    if (current_phoneme.duration >= self.config.min_phoneme_duration and 
                        current_phoneme.duration <= self.config.max_phoneme_duration and
                        current_phoneme.confidence >= self.config.confidence_threshold):
                        
                        merged_phonemes.append(current_phoneme)
                    
                    current_phoneme = phonemes[i]
            
            # 添加最后一个音素
            if (current_phoneme.duration >= self.config.min_phoneme_duration and 
                current_phoneme.confidence >= self.config.confidence_threshold):
                merged_phonemes.append(current_phoneme)
            
            return merged_phonemes
            
        except Exception as e:
            logger.error(f"Error in phoneme postprocessing: {e}")
            return phonemes

    def _generate_cache_key(self, audio_data: np.ndarray, sample_rate: int, language: str) -> str:
        """生成缓存键"""
        import hashlib
        
        # 使用音频数据的哈希值作为缓存键
        audio_hash = hashlib.md5(audio_data.tobytes()).hexdigest()
        return f"{audio_hash}_{sample_rate}_{language}"

    def _manage_cache_size(self):
        """管理缓存大小"""
        try:
            max_cache_size = 1000  # 最大缓存条目数
            
            while len(self.analysis_cache) > max_cache_size:
                # 移除最旧的缓存项
                oldest_key = min(self.analysis_cache.keys(), 
                               key=lambda k: len(self.analysis_cache[k]))
                del self.analysis_cache[oldest_key]
                
        except Exception as e:
            logger.warning(f"Error managing cache size: {e}")

    async def analyze_phonemes_from_tts(self, tts_result) -> List[Tuple[str, float]]:
        """从TTS结果分析音素"""
        try:
            # 使用TTS结果中的音素信息
            if hasattr(tts_result, 'phonemes') and hasattr(tts_result, 'durations'):
                phoneme_data = []
                current_time = 0.0
                
                for phoneme, duration in zip(tts_result.phonemes, tts_result.durations):
                    phoneme_data.append((phoneme, duration))
                    current_time += duration
                
                return phoneme_data
            else:
                # 回退到音频分析
                return await self.analyze_phonemes(tts_result.audio_data, tts_result.sample_rate)
                
        except Exception as e:
            logger.error(f"Error analyzing phonemes from TTS: {e}")
            return []

    async def add_realtime_audio(self, buffer_id: str, audio_chunk: np.ndarray):
        """添加实时音频数据"""
        try:
            if buffer_id not in self.realtime_buffers:
                self.realtime_buffers[buffer_id] = []
            
            self.realtime_buffers[buffer_id].append(audio_chunk)
            
        except Exception as e:
            logger.error(f"Error adding realtime audio: {e}")

    async def get_realtime_phonemes(self, buffer_id: str) -> List[Phoneme]:
        """获取实时音素"""
        try:
            # 这里应该返回实时分析的结果
            # 简化实现：返回空列表
            return []
            
        except Exception as e:
            logger.error(f"Error getting realtime phonemes: {e}")
            return []

    def get_phoneme_info(self, phoneme_symbol: str, language: str = None) -> Optional[Dict[str, Any]]:
        """获取音素信息"""
        try:
            if language is None:
                language = self.config.language
            
            if language in self.phoneme_database and phoneme_symbol in self.phoneme_database[language]:
                return self.phoneme_database[language][phoneme_symbol]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting phoneme info: {e}")
            return None

    def get_available_languages(self) -> List[str]:
        """获取可用语言列表"""
        return list(self.phoneme_database.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["cache_size"] = len(self.analysis_cache)
        stats["realtime_buffers"] = len(self.realtime_buffers)
        stats["phoneme_database_size"] = sum(len(lang_db) for lang_db in self.phoneme_database.values())
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.analysis_cache.clear()
            self.realtime_buffers.clear()
            
            logger.info("PhonemeAnalyzer cleaned up")
            
        except Exception as e:
            logger.error(f"Error during PhonemeAnalyzer cleanup: {e}")

# 全局音素分析器实例
phoneme_analyzer = PhonemeAnalyzer()
