# interaction/input_systems/speech_recognizer/noise_suppressor.py
"""
噪声抑制：抑制背景噪声
负责背景噪声的检测和抑制
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time

@dataclass
class NoiseProfile:
    """噪声配置文件"""
    noise_spectrum: np.ndarray
    noise_variance: float
    update_rate: float = 0.1
    min_noise_level: float = 0.001

@dataclass
class NoiseSuppressionResult:
    """噪声抑制结果"""
    suppressed_audio: np.ndarray
    noise_level: float
    suppression_applied: bool
    processing_time: float
    noise_reduction_db: float

class NoiseSuppressor:
    """噪声抑制器"""
    
    def __init__(self):
        self.is_initialized = False
        self.sample_rate = 16000
        self.frame_size = 512
        self.hop_size = 256
        self.noise_profiles: Dict[str, NoiseProfile] = {}
        self.current_noise_profile = None
        
        # 集成基础设施组件
        from infrastructure.compute_storage.inference_optimizer import inference_optimizer
        self.inference_optimizer = inference_optimizer
        
    async def initialize(self):
        """初始化噪声抑制器"""
        if self.is_initialized:
            return
            
        logging.info("初始化噪声抑制系统...")
        
        try:
            # 初始化基础设施组件
            await self.inference_optimizer.initialize()
            
            # 加载噪声抑制模型
            from data.models.speech.asr.speech_enhancement import NoiseSuppressionModel
            self.suppression_model = NoiseSuppressionModel()
            
            # 异步加载模型
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.suppression_model.load)
            
            # 初始化默认噪声配置文件
            await self._initialize_default_profiles()
            
            self.is_initialized = True
            logging.info("噪声抑制系统初始化完成")
            
        except Exception as e:
            logging.error(f"噪声抑制系统初始化失败: {e}")
            self.is_initialized = True  # 使用基础方法
    
    async def _initialize_default_profiles(self):
        """初始化默认噪声配置文件"""
        # 创建常见环境的噪声配置文件
        environments = ['office', 'street', 'car', 'home', 'cafe']
        
        for env in environments:
            # 基础噪声频谱（在实际实现中会从训练数据学习）
            noise_spectrum = await self._create_default_noise_spectrum(env)
            variance = await self._estimate_noise_variance(env)
            
            self.noise_profiles[env] = NoiseProfile(
                noise_spectrum=noise_spectrum,
                noise_variance=variance,
                update_rate=0.1
            )
        
        self.current_noise_profile = self.noise_profiles['office']
    
    async def _create_default_noise_spectrum(self, environment: str) -> np.ndarray:
        """创建默认噪声频谱"""
        # 基于环境类型创建典型的噪声频谱
        base_spectrum = np.ones(self.frame_size // 2 + 1)
        
        if environment == 'office':
            # 办公室噪声：低频空调声 + 中频键盘声
            base_spectrum[:50] *= 0.8  # 低频增强
            base_spectrum[100:200] *= 0.6  # 中频
        elif environment == 'street':
            # 街道噪声：宽频带交通噪声
            base_spectrum *= 1.2
        elif environment == 'car':
            # 车内噪声：低频引擎声 + 道路噪声
            base_spectrum[:100] *= 1.5
        elif environment == 'cafe':
            # 咖啡厅：人声和背景音乐
            base_spectrum[200:400] *= 0.9
        
        return base_spectrum
    
    async def _estimate_noise_variance(self, environment: str) -> float:
        """估计噪声方差"""
        variances = {
            'office': 0.01,
            'street': 0.05,
            'car': 0.03,
            'home': 0.008,
            'cafe': 0.02
        }
        return variances.get(environment, 0.01)
    
    async def suppress_noise(self, audio_data: np.ndarray, sample_rate: int = None, 
                           environment: str = None) -> NoiseSuppressionResult:
        """抑制噪声"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 预处理音频
            processed_audio = await self._preprocess_audio(audio_data, sample_rate or self.sample_rate)
            
            # 选择噪声配置文件
            if environment and environment in self.noise_profiles:
                noise_profile = self.noise_profiles[environment]
            else:
                noise_profile = self.current_noise_profile
            
            # 检测噪声水平
            noise_level = await self._estimate_noise_level(processed_audio, noise_profile)
            
            # 应用噪声抑制
            if noise_level > noise_profile.min_noise_level:
                if hasattr(self, 'suppression_model') and self.suppression_model.is_loaded:
                    # 使用模型进行噪声抑制
                    suppressed_audio = await self._apply_model_suppression(processed_audio, noise_profile)
                else:
                    # 使用传统方法
                    suppressed_audio = await self._apply_spectral_subtraction(processed_audio, noise_profile)
                
                suppression_applied = True
                noise_reduction_db = await self._calculate_noise_reduction(processed_audio, suppressed_audio)
            else:
                suppressed_audio = processed_audio
                suppression_applied = False
                noise_reduction_db = 0.0
            
            processing_time = time.time() - start_time
            
            return NoiseSuppressionResult(
                suppressed_audio=suppressed_audio,
                noise_level=noise_level,
                suppression_applied=suppression_applied,
                processing_time=processing_time,
                noise_reduction_db=noise_reduction_db
            )
            
        except Exception as e:
            logging.error(f"噪声抑制失败: {e}")
            return NoiseSuppressionResult(
                suppressed_audio=audio_data,
                noise_level=0.0,
                suppression_applied=False,
                processing_time=time.time() - start_time,
                noise_reduction_db=0.0
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
    
    async def _estimate_noise_level(self, audio_data: np.ndarray, noise_profile: NoiseProfile) -> float:
        """估计噪声水平"""
        try:
            # 使用频谱分析估计噪声水平
            stft = np.fft.rfft(audio_data)
            magnitude = np.abs(stft)
            
            # 计算与噪声谱的相关性
            correlation = np.corrcoef(magnitude[:len(noise_profile.noise_spectrum)], 
                                    noise_profile.noise_spectrum)[0, 1]
            
            if np.isnan(correlation):
                correlation = 0.0
            
            # 综合噪声水平估计
            overall_level = np.mean(magnitude)
            noise_level = overall_level * (1 - correlation) * noise_profile.noise_variance
            
            return noise_level
            
        except Exception:
            return 0.01  # 默认噪声水平
    
    async def _apply_spectral_subtraction(self, audio_data: np.ndarray, noise_profile: NoiseProfile) -> np.ndarray:
        """应用谱减法"""
        try:
            # 分帧处理
            frames = await self._segment_into_frames(audio_data)
            enhanced_frames = []
            
            for frame in frames:
                # 计算STFT
                stft = np.fft.rfft(frame)
                magnitude = np.abs(stft)
                phase = np.angle(stft)
                
                # 谱减法
                enhanced_magnitude = magnitude - noise_profile.noise_spectrum[:len(magnitude)]
                enhanced_magnitude = np.maximum(enhanced_magnitude, 0.001 * np.max(magnitude))
                
                # 重建信号
                enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
                enhanced_frame = np.fft.irfft(enhanced_stft)
                enhanced_frames.append(enhanced_frame)
            
            # 合并帧
            suppressed_audio = await self._overlap_add_frames(enhanced_frames)
            return suppressed_audio
            
        except Exception as e:
            logging.warning(f"谱减法失败: {e}")
            return audio_data
    
    async def _segment_into_frames(self, audio_data: np.ndarray) -> List[np.ndarray]:
        """将音频分割成帧"""
        frames = []
        num_frames = (len(audio_data) - self.frame_size) // self.hop_size + 1
        
        for i in range(num_frames):
            start = i * self.hop_size
            end = start + self.frame_size
            frame = audio_data[start:end]
            
            # 应用窗函数
            window = np.hanning(len(frame))
            frame = frame * window
            
            frames.append(frame)
        
        return frames
    
    async def _overlap_add_frames(self, frames: List[np.ndarray]) -> np.ndarray:
        """重叠相加重建音频"""
        output_length = len(frames) * self.hop_size + self.frame_size - self.hop_size
        reconstructed = np.zeros(output_length)
        
        for i, frame in enumerate(frames):
            start = i * self.hop_size
            end = start + len(frame)
            reconstructed[start:end] += frame
        
        return reconstructed
    
    async def _apply_model_suppression(self, audio_data: np.ndarray, noise_profile: NoiseProfile) -> np.ndarray:
        """应用模型抑制"""
        try:
            loop = asyncio.get_event_loop()
            suppressed_audio = await loop.run_in_executor(
                None, 
                self.suppression_model.suppress, 
                audio_data, 
                self.sample_rate
            )
            return suppressed_audio
        except Exception as e:
            logging.warning(f"模型抑制失败: {e}")
            return await self._apply_spectral_subtraction(audio_data, noise_profile)
    
    async def _calculate_noise_reduction(self, original: np.ndarray, suppressed: np.ndarray) -> float:
        """计算噪声减少量"""
        try:
            # 估计原始信号中的噪声
            original_noise = await self._estimate_residual_noise(original)
            suppressed_noise = await self._estimate_residual_noise(suppressed)
            
            if original_noise > 0:
                reduction_db = 10 * np.log10(original_noise / suppressed_noise)
                return max(0.0, reduction_db)
            else:
                return 0.0
                
        except Exception:
            return 3.0  # 默认减少量
    
    async def _estimate_residual_noise(self, audio_data: np.ndarray) -> float:
        """估计残余噪声"""
        try:
            # 使用高通滤波器估计噪声
            high_freq = audio_data - np.convolve(audio_data, np.ones(20)/20, mode='same')
            noise_power = np.mean(high_freq ** 2)
            return noise_power
        except Exception:
            return 0.001
    
    async def learn_environment_noise(self, audio_data: np.ndarray, environment: str, duration: float = 5.0):
        """学习环境噪声"""
        try:
            # 分析音频数据以更新噪声配置文件
            stft = np.fft.rfft(audio_data)
            magnitude = np.abs(stft)
            
            if environment not in self.noise_profiles:
                # 创建新的噪声配置文件
                self.noise_profiles[environment] = NoiseProfile(
                    noise_spectrum=magnitude,
                    noise_variance=np.var(audio_data),
                    update_rate=0.1
                )
            else:
                # 更新现有配置文件
                profile = self.noise_profiles[environment]
                profile.noise_spectrum = (1 - profile.update_rate) * profile.noise_spectrum + \
                                       profile.update_rate * magnitude
                profile.noise_variance = (1 - profile.update_rate) * profile.noise_variance + \
                                       profile.update_rate * np.var(audio_data)
            
            logging.info(f"环境噪声学习完成: {environment}")
            
        except Exception as e:
            logging.error(f"环境噪声学习失败: {e}")
    
    async def set_current_environment(self, environment: str):
        """设置当前环境"""
        if environment in self.noise_profiles:
            self.current_noise_profile = self.noise_profiles[environment]
            logging.info(f"当前环境设置为: {environment}")
        else:
            logging.warning(f"未知环境: {environment}")
    
    def get_suppression_info(self) -> Dict[str, Any]:
        """获取抑制系统信息"""
        return {
            "initialized": self.is_initialized,
            "sample_rate": self.sample_rate,
            "frame_size": self.frame_size,
            "hop_size": self.hop_size,
            "known_environments": list(self.noise_profiles.keys()),
            "model_loaded": getattr(self.suppression_model, 'is_loaded', False) if hasattr(self, 'suppression_model') else False
        }


# 模拟噪声抑制模型
class NoiseSuppressionModel:
    def __init__(self):
        self.is_loaded = False
    
    def load(self):
        self.is_loaded = True
    
    def suppress(self, audio_data, sample_rate):
        # 模拟噪声抑制
        return audio_data * 0.8  # 简单衰减


# 全局噪声抑制器实例
noise_suppressor = NoiseSuppressor()

