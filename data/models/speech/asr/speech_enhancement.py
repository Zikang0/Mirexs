"""
语音增强 - 噪声消除和语音增强
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
import time

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class SpeechEnhancement:
    """语音增强处理器"""
    
    def __init__(self):
        self.processor_name = "SpeechEnhancement"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.is_loaded = False
        
        # 增强算法配置
        self.config = {
            'noise_reduction': True,
            'echo_cancellation': True,
            'gain_normalization': True,
            'spectral_enhancement': True,
            'aggressive_mode': False,
            'use_deep_learning': False  # 使用深度学习模型进行增强
        }
        
        # 深度学习模型（如果可用）
        self.dl_model = None
        
    def load(self) -> bool:
        """加载语音增强模型"""
        try:
            if self.config['use_deep_learning'] and TORCH_AVAILABLE:
                # 尝试加载深度学习语音增强模型
                # 这里可以集成Demucs、Spectral等模型
                print("🔊 加载深度学习语音增强模型...")
                # 暂时使用传统方法
                pass
                
            self.is_loaded = True
            print("✅ 语音增强处理器初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 加载语音增强模型失败: {e}")
            return False
    
    def enhance(self, audio_data: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """语音增强主函数"""
        if not self.is_loaded:
            self.load()
        
        try:
            start_time = time.time()
            
            # 预处理：确保单声道和正确采样率
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 应用各种增强技术
            if self.config['noise_reduction']:
                processed_audio = self._noise_reduction(processed_audio)
            
            if self.config['echo_cancellation']:
                processed_audio = self._echo_cancellation(processed_audio)
            
            if self.config['gain_normalization']:
                processed_audio = self._gain_normalization(processed_audio)
            
            if self.config['spectral_enhancement']:
                processed_audio = self._spectral_enhancement(processed_audio)
            
            processing_time = time.time() - start_time
            print(f"🔊 语音增强完成，耗时: {processing_time:.3f}s")
            
            return processed_audio
            
        except Exception as e:
            print(f"❌ 语音增强失败: {e}")
            return audio_data  # 返回原始音频
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """音频预处理"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
        return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        if TORCH_AVAILABLE:
            audio_tensor = torch.from_numpy(audio_data).float()
            resampler = torchaudio.transforms.Resample(orig_freq=original_rate, new_freq=target_rate)
            resampled_audio = resampler(audio_tensor)
            return resampled_audio.numpy()
        else:
            import scipy.signal
            num_samples = int(len(audio_data) * target_rate / original_rate)
            return scipy.signal.resample(audio_data, num_samples)
    
    def _noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """噪声消除"""
        try:
            # 使用谱减法进行噪声消除
            if len(audio_data) < 256:  # 太短的音频不处理
                return audio_data
            
            # 简单的谱减法实现
            enhanced_audio = self._spectral_subtraction(audio_data)
            return enhanced_audio
            
        except Exception as e:
            print(f"⚠️ 噪声消除失败: {e}")
            return audio_data
    
    def _spectral_subtraction(self, audio_data: np.ndarray, frame_size: int = 512, 
                             overlap: int = 256) -> np.ndarray:
        """谱减法噪声消除"""
        import scipy.signal
        
        # 计算帧数
        hop_size = frame_size - overlap
        num_frames = (len(audio_data) - frame_size) // hop_size + 1
        
        # 初始化输出
        output_signal = np.zeros_like(audio_data)
        window = np.hanning(frame_size)
        
        # 估计噪声谱（使用前几帧）
        noise_frames = min(10, num_frames)
        noise_spectrum = np.zeros(frame_size // 2 + 1)
        
        for i in range(noise_frames):
            start = i * hop_size
            frame = audio_data[start:start + frame_size] * window
            spectrum = np.fft.rfft(frame)
            noise_spectrum += np.abs(spectrum)
        
        if noise_frames > 0:
            noise_spectrum /= noise_frames
        
        # 谱减法处理
        for i in range(num_frames):
            start = i * hop_size
            frame = audio_data[start:start + frame_size] * window
            
            # 计算频谱
            spectrum = np.fft.rfft(frame)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)
            
            # 谱减法
            enhanced_magnitude = magnitude - noise_spectrum
            enhanced_magnitude = np.maximum(enhanced_magnitude, 0.01 * magnitude)  # 避免过度削减
            
            # 重建信号
            enhanced_spectrum = enhanced_magnitude * np.exp(1j * phase)
            enhanced_frame = np.fft.irfft(enhanced_spectrum)
            
            # 叠加到输出
            output_signal[start:start + frame_size] += enhanced_frame * window
        
        return output_signal
    
    def _echo_cancellation(self, audio_data: np.ndarray) -> np.ndarray:
        """回声消除"""
        # 简单的回声消除实现
        # 实际项目中可以使用更复杂的自适应滤波算法
        
        try:
            # 使用高通滤波器消除低频回声
            from scipy import signal
            
            # 设计高通滤波器
            nyquist = self.sample_rate / 2
            highpass_freq = 80  # Hz
            b, a = signal.butter(4, highpass_freq / nyquist, btype='high')
            
            # 应用滤波器
            filtered_audio = signal.filtfilt(b, a, audio_data)
            
            return filtered_audio
            
        except Exception as e:
            print(f"⚠️ 回声消除失败: {e}")
            return audio_data
    
    def _gain_normalization(self, audio_data: np.ndarray) -> np.ndarray:
        """增益归一化"""
        try:
            # 计算RMS能量
            rms = np.sqrt(np.mean(audio_data**2))
            
            if rms > 0:
                # 目标RMS
                target_rms = 0.1
                gain = target_rms / rms
                
                # 应用增益（限制最大增益）
                max_gain = 10.0
                gain = min(gain, max_gain)
                
                normalized_audio = audio_data * gain
                
                # 限制幅度（防止削波）
                max_amplitude = 0.95
                peak = np.max(np.abs(normalized_audio))
                if peak > max_amplitude:
                    normalized_audio = normalized_audio * (max_amplitude / peak)
                
                return normalized_audio
            
            return audio_data
            
        except Exception as e:
            print(f"⚠️ 增益归一化失败: {e}")
            return audio_data
    
    def _spectral_enhancement(self, audio_data: np.ndarray) -> np.ndarray:
        """频谱增强"""
        try:
            # 简单的频谱增强：提升高频分量
            from scipy import signal
            
            # 设计频谱增强滤波器
            nyquist = self.sample_rate / 2
            frequencies = [0, 1000, 2000, 4000, nyquist]
            gains = [1.0, 1.2, 1.5, 1.8, 2.0]  # 高频增益
            
            # 使用FIR滤波器设计
            numtaps = 101
            fir_coeff = signal.firwin2(numtaps, frequencies, gains, fs=self.sample_rate)
            
            # 应用滤波器
            enhanced_audio = signal.lfilter(fir_coeff, 1.0, audio_data)
            
            return enhanced_audio
            
        except Exception as e:
            print(f"⚠️ 频谱增强失败: {e}")
            return audio_data
    
    def set_aggressive_mode(self, enabled: bool = True) -> None:
        """设置激进模式（更强的噪声消除）"""
        self.config['aggressive_mode'] = enabled
        
        if enabled:
            self.config.update({
                'noise_reduction': True,
                'echo_cancellation': True, 
                'gain_normalization': True,
                'spectral_enhancement': True
            })
    
    def analyze_audio_quality(self, audio_data: np.ndarray) -> Dict[str, float]:
        """分析音频质量"""
        try:
            # 计算信噪比（估计）
            noise_floor = self._estimate_noise_floor(audio_data)
            signal_power = np.mean(audio_data**2)
            snr = 10 * np.log10(signal_power / noise_floor) if noise_floor > 0 else 50
            
            # 计算动态范围
            dynamic_range = 20 * np.log10(np.max(np.abs(audio_data)) / (np.std(audio_data) + 1e-10))
            
            # 计算谐波失真（估计）
            distortion = self._estimate_distortion(audio_data)
            
            return {
                "snr_db": snr,
                "dynamic_range_db": dynamic_range,
                "distortion_percent": distortion,
                "clipping_ratio": self._calculate_clipping(audio_data)
            }
            
        except Exception as e:
            print(f"⚠️ 音频质量分析失败: {e}")
            return {"snr_db": 0, "dynamic_range_db": 0, "distortion_percent": 0, "clipping_ratio": 0}
    
    def _estimate_noise_floor(self, audio_data: np.ndarray) -> float:
        """估计噪声基底"""
        # 使用音频开始部分估计噪声
        noise_segment = audio_data[:min(1000, len(audio_data) // 10)]
        return np.mean(noise_segment**2)
    
    def _estimate_distortion(self, audio_data: np.ndarray) -> float:
        """估计谐波失真"""
        # 简单的失真估计
        clipped_samples = np.sum(np.abs(audio_data) > 0.95)
        return (clipped_samples / len(audio_data)) * 100
    
    def _calculate_clipping(self, audio_data: np.ndarray) -> float:
        """计算削波比例"""
        clipped = np.sum(np.abs(audio_data) >= 0.99)
        return clipped / len(audio_data)
    
    def get_processor_info(self) -> Dict[str, Any]:
        """获取处理器信息"""
        return {
            "processor_name": self.processor_name,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查处理器是否已加载"""
        return self.is_loaded