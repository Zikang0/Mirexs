# interaction/input_systems/speech_recognizer/speech_enhancer.py
"""
语音增强：改善语音质量
负责语音信号的增强和音质改善
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time

@dataclass
class EnhancementConfig:
    """增强配置"""
    noise_reduction: bool = True
    echo_cancellation: bool = True
    gain_control: bool = True
    voice_boost: bool = False
    target_level: float = -20.0  # dB

@dataclass
class EnhancementResult:
    """增强结果"""
    enhanced_audio: np.ndarray
    original_audio: np.ndarray
    noise_reduction_applied: bool
    echo_cancellation_applied: bool
    gain_adjustment: float
    processing_time: float
    quality_improvement: float

class SpeechEnhancer:
    """语音增强器"""
    
    def __init__(self):
        self.config = EnhancementConfig()
        self.is_initialized = False
        self.sample_rate = 16000
        self.noise_profile = None
        self.echo_profile = None
        
        # 集成基础设施层的优化器
        from infrastructure.compute_storage.inference_optimizer import inference_optimizer
        self.inference_optimizer = inference_optimizer
        
    async def initialize(self):
        """初始化语音增强器"""
        if self.is_initialized:
            return
            
        logging.info("初始化语音增强系统...")
        
        try:
            # 初始化基础设施组件
            await self.inference_optimizer.initialize()
            
            # 加载语音增强模型
            from data.models.speech.asr.speech_enhancement import SpeechEnhancementModel
            self.enhancement_model = SpeechEnhancementModel()
            
            # 异步加载模型
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.enhancement_model.load)
            
            # 初始化噪声和回声配置文件
            await self._initialize_profiles()
            
            self.is_initialized = True
            logging.info("语音增强系统初始化完成")
            
        except Exception as e:
            logging.error(f"语音增强系统初始化失败: {e}")
            self.is_initialized = True  # 即使模型加载失败也继续使用基础方法
    
    async def _initialize_profiles(self):
        """初始化噪声和回声配置文件"""
        # 在实际实现中，这里会加载预训练的噪声和回声配置文件
        # 这里使用基础配置
        self.noise_profile = {
            'spectral_subtraction_factor': 0.8,
            'noise_floor': 0.01,
            'smoothing_factor': 0.9
        }
        
        self.echo_profile = {
            'delay_samples': 100,
            'attenuation_factor': 0.3,
            'adaptive_filter_length': 256
        }
    
    async def enhance_speech(self, audio_data: np.ndarray, sample_rate: int = None, 
                           config: EnhancementConfig = None) -> EnhancementResult:
        """增强语音信号"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        current_config = config or self.config
        original_audio = audio_data.copy()
        
        try:
            # 预处理音频
            processed_audio = await self._preprocess_audio(audio_data, sample_rate or self.sample_rate)
            
            enhanced_audio = processed_audio.copy()
            applied_enhancements = {
                'noise_reduction': False,
                'echo_cancellation': False,
                'gain_control': False
            }
            gain_adjustment = 0.0
            
            # 应用各种增强技术
            if current_config.noise_reduction:
                enhanced_audio = await self._apply_noise_reduction(enhanced_audio)
                applied_enhancements['noise_reduction'] = True
            
            if current_config.echo_cancellation:
                enhanced_audio = await self._apply_echo_cancellation(enhanced_audio)
                applied_enhancements['echo_cancellation'] = True
            
            if current_config.gain_control:
                enhanced_audio, gain_adjustment = await self._apply_gain_control(enhanced_audio, current_config.target_level)
                applied_enhancements['gain_control'] = True
            
            if current_config.voice_boost:
                enhanced_audio = await self._apply_voice_boost(enhanced_audio)
            
            # 使用模型进行高级增强（如果可用）
            if hasattr(self, 'enhancement_model') and self.enhancement_model.is_loaded:
                enhanced_audio = await self._apply_model_enhancement(enhanced_audio)
            
            processing_time = time.time() - start_time
            
            # 计算质量改进
            quality_improvement = await self._calculate_quality_improvement(original_audio, enhanced_audio)
            
            return EnhancementResult(
                enhanced_audio=enhanced_audio,
                original_audio=original_audio,
                noise_reduction_applied=applied_enhancements['noise_reduction'],
                echo_cancellation_applied=applied_enhancements['echo_cancellation'],
                gain_adjustment=gain_adjustment,
                processing_time=processing_time,
                quality_improvement=quality_improvement
            )
            
        except Exception as e:
            logging.error(f"语音增强失败: {e}")
            return EnhancementResult(
                enhanced_audio=audio_data,
                original_audio=audio_data,
                noise_reduction_applied=False,
                echo_cancellation_applied=False,
                gain_adjustment=0.0,
                processing_time=time.time() - start_time,
                quality_improvement=0.0
            )
    
    async def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = await self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
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
            # 线性重采样
            num_samples = int(len(audio_data) * target_rate / original_rate)
            indices = np.linspace(0, len(audio_data)-1, num_samples)
            return np.interp(indices, np.arange(len(audio_data)), audio_data)
    
    async def _apply_noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """应用噪声消除"""
        try:
            # 使用谱减法进行噪声消除
            stft = np.fft.fft(audio_data)
            magnitude = np.abs(stft)
            phase = np.angle(stft)
            
            # 估计噪声谱
            noise_magnitude = await self._estimate_noise_spectrum(magnitude)
            
            # 谱减法
            enhanced_magnitude = magnitude - self.noise_profile['spectral_subtraction_factor'] * noise_magnitude
            enhanced_magnitude = np.maximum(enhanced_magnitude, self.noise_profile['noise_floor'] * np.max(magnitude))
            
            # 重建信号
            enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
            enhanced_audio = np.real(np.fft.ifft(enhanced_stft))
            
            return enhanced_audio
            
        except Exception as e:
            logging.warning(f"噪声消除失败: {e}")
            return audio_data
    
    async def _estimate_noise_spectrum(self, magnitude: np.ndarray) -> np.ndarray:
        """估计噪声频谱"""
        # 简化实现：使用信号的前10%作为噪声估计
        noise_length = len(magnitude) // 10
        if noise_length > 0:
            return np.mean(magnitude[:noise_length]) * np.ones_like(magnitude)
        else:
            return 0.01 * np.ones_like(magnitude)
    
    async def _apply_echo_cancellation(self, audio_data: np.ndarray) -> np.ndarray:
        """应用回声消除"""
        try:
            # 简单的自适应回声消除
            echo_delay = self.echo_profile['delay_samples']
            attenuation = self.echo_profile['attenuation_factor']
            
            if len(audio_data) > echo_delay:
                # 模拟回声消除
                echo_component = np.roll(audio_data, echo_delay) * attenuation
                enhanced_audio = audio_data - echo_component
                return enhanced_audio
            else:
                return audio_data
                
        except Exception as e:
            logging.warning(f"回声消除失败: {e}")
            return audio_data
    
    async def _apply_gain_control(self, audio_data: np.ndarray, target_level: float) -> Tuple[np.ndarray, float]:
        """应用增益控制"""
        try:
            # 计算当前RMS水平
            current_rms = np.sqrt(np.mean(audio_data ** 2))
            if current_rms == 0:
                return audio_data, 0.0
            
            # 转换为dB
            current_level = 20 * np.log10(current_rms)
            
            # 计算需要的增益
            gain_db = target_level - current_level
            gain_linear = 10 ** (gain_db / 20)
            
            # 应用增益
            enhanced_audio = audio_data * gain_linear
            
            # 限制最大幅度
            max_amplitude = np.max(np.abs(enhanced_audio))
            if max_amplitude > 1.0:
                enhanced_audio = enhanced_audio / max_amplitude
            
            return enhanced_audio, gain_db
            
        except Exception as e:
            logging.warning(f"增益控制失败: {e}")
            return audio_data, 0.0
    
    async def _apply_voice_boost(self, audio_data: np.ndarray) -> np.ndarray:
        """应用语音增强"""
        try:
            # 基于频谱的语音增强
            stft = np.fft.fft(audio_data)
            frequencies = np.fft.fftfreq(len(audio_data))
            
            # 增强语音频段（300-3400Hz）
            voice_band_mask = (np.abs(frequencies) >= 300/self.sample_rate) & (np.abs(frequencies) <= 3400/self.sample_rate)
            boost_factor = 1.5
            
            enhanced_stft = stft.copy()
            enhanced_stft[voice_band_mask] *= boost_factor
            
            enhanced_audio = np.real(np.fft.ifft(enhanced_stft))
            return enhanced_audio
            
        except Exception as e:
            logging.warning(f"语音增强失败: {e}")
            return audio_data
    
    async def _apply_model_enhancement(self, audio_data: np.ndarray) -> np.ndarray:
        """应用模型增强"""
        try:
            loop = asyncio.get_event_loop()
            enhanced_audio = await loop.run_in_executor(
                None, 
                self.enhancement_model.enhance, 
                audio_data, 
                self.sample_rate
            )
            return enhanced_audio
        except Exception as e:
            logging.warning(f"模型增强失败: {e}")
            return audio_data
    
    async def _calculate_quality_improvement(self, original: np.ndarray, enhanced: np.ndarray) -> float:
        """计算质量改进"""
        try:
            # 计算信噪比改进
            original_snr = await self._calculate_snr(original)
            enhanced_snr = await self._calculate_snr(enhanced)
            
            snr_improvement = enhanced_snr - original_snr
            
            # 计算动态范围改进
            original_dynamic_range = np.max(original) - np.min(original)
            enhanced_dynamic_range = np.max(enhanced) - np.min(enhanced)
            dynamic_improvement = enhanced_dynamic_range - original_dynamic_range
            
            # 综合质量评分
            quality_improvement = 0.7 * snr_improvement + 0.3 * dynamic_improvement
            return max(0.0, min(1.0, quality_improvement / 20.0))  # 归一化到0-1
            
        except Exception:
            return 0.5
    
    async def _calculate_snr(self, audio_data: np.ndarray) -> float:
        """计算信噪比（简化版本）"""
        try:
            signal_power = np.mean(audio_data ** 2)
            if signal_power == 0:
                return 0.0
            
            # 估计噪声功率（使用高频成分）
            high_freq = audio_data - np.convolve(audio_data, np.ones(10)/10, mode='same')
            noise_power = np.mean(high_freq ** 2)
            
            if noise_power == 0:
                return 100.0  # 无限SNR
            
            snr = 10 * np.log10(signal_power / noise_power)
            return snr
            
        except Exception:
            return 20.0  # 默认SNR
    
    def update_config(self, new_config: EnhancementConfig):
        """更新增强配置"""
        self.config = new_config
        logging.info("语音增强配置已更新")
    
    def get_enhancement_info(self) -> Dict[str, Any]:
        """获取增强系统信息"""
        return {
            "initialized": self.is_initialized,
            "sample_rate": self.sample_rate,
            "config": {
                "noise_reduction": self.config.noise_reduction,
                "echo_cancellation": self.config.echo_cancellation,
                "gain_control": self.config.gain_control,
                "voice_boost": self.config.voice_boost,
                "target_level": self.config.target_level
            },
            "model_loaded": getattr(self.enhancement_model, 'is_loaded', False) if hasattr(self, 'enhancement_model') else False
        }


# 模拟语音增强模型
class SpeechEnhancementModel:
    def __init__(self):
        self.is_loaded = False
    
    def load(self):
        self.is_loaded = True
    
    def enhance(self, audio_data, sample_rate):
        # 模拟增强处理
        return audio_data * 1.1  # 简单增益


# 全局语音增强器实例
speech_enhancer = SpeechEnhancer()

