"""
音频预处理器 - 音频预处理
"""

import numpy as np
from typing import Dict, Any, Optional
import time

class AudioPreprocessor:
    """音频预处理器"""
    
    def __init__(self):
        self.processor_name = "AudioPreprocessor"
        self.version = "1.0.0"
        self.target_sample_rate = 16000
        self.is_loaded = True  # 预处理器不需要复杂加载
        
        # 处理配置
        self.config = {
            'resample_method': 'linear',      # 重采样方法
            'normalization': True,           # 音量归一化
            'noise_reduction': True,         # 噪声消除
            'dc_offset_removal': True,       # DC偏移消除
            'highpass_filter': True,         # 高通滤波
            'highpass_cutoff': 80,           # 高通截止频率(Hz)
            'pre_emphasis': True,            # 预加重
            'pre_emphasis_coeff': 0.97,      # 预加重系数
            'frame_size': 0.025,             # 帧大小(秒)
            'frame_shift': 0.01              # 帧移(秒)
        }
        
        # 状态信息
        self.processing_stats = {
            'total_processed': 0,
            'total_duration': 0.0,
            'average_processing_time': 0.0
        }
        
    def load(self) -> bool:
        """加载预处理器"""
        # 预处理器不需要复杂加载过程
        self.is_loaded = True
        print("✅ 音频预处理器初始化完成")
        return True
    
    def process(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """处理音频数据"""
        if not self.is_loaded:
            self.load()
        
        try:
            start_time = time.time()
            
            # 验证输入
            if len(audio_data) == 0:
                return audio_data
            
            # 记录原始信息
            original_shape = audio_data.shape
            original_dtype = audio_data.dtype
            
            # 执行处理流水线
            processed_audio = audio_data.copy()
            
            # 1. 转换为单声道
            processed_audio = self._convert_to_mono(processed_audio)
            
            # 2. 重采样到目标采样率
            if sample_rate != self.target_sample_rate:
                processed_audio = self._resample_audio(processed_audio, sample_rate, self.target_sample_rate)
                sample_rate = self.target_sample_rate
            
            # 3. 移除DC偏移
            if self.config['dc_offset_removal']:
                processed_audio = self._remove_dc_offset(processed_audio)
            
            # 4. 高通滤波
            if self.config['highpass_filter']:
                processed_audio = self._highpass_filter(processed_audio, sample_rate)
            
            # 5. 预加重
            if self.config['pre_emphasis']:
                processed_audio = self._pre_emphasis(processed_audio)
            
            # 6. 噪声消除
            if self.config['noise_reduction']:
                processed_audio = self._noise_reduction(processed_audio)
            
            # 7. 音量归一化
            if self.config['normalization']:
                processed_audio = self._normalize_volume(processed_audio)
            
            # 更新统计信息
            self._update_processing_stats(len(processed_audio) / sample_rate, 
                                        time.time() - start_time)
            
            return processed_audio
            
        except Exception as e:
            print(f"❌ 音频预处理失败: {e}")
            # 返回原始音频作为降级方案
            return audio_data
    
    def _convert_to_mono(self, audio_data: np.ndarray) -> np.ndarray:
        """转换为单声道"""
        if len(audio_data.shape) > 1:
            return np.mean(audio_data, axis=1)
        return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        if self.config['resample_method'] == 'linear':
            # 线性重采样
            import scipy.signal
            num_samples = int(len(audio_data) * target_rate / original_rate)
            return scipy.signal.resample(audio_data, num_samples)
        else:
            # 默认使用scipy的resample_poly（更高质量）
            import scipy.signal
            gcd = np.gcd(original_rate, target_rate)
            up = target_rate // gcd
            down = original_rate // gcd
            return scipy.signal.resample_poly(audio_data, up, down)
    
    def _remove_dc_offset(self, audio_data: np.ndarray) -> np.ndarray:
        """移除DC偏移"""
        return audio_data - np.mean(audio_data)
    
    def _highpass_filter(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """高通滤波器"""
        from scipy import signal
        
        nyquist = sample_rate / 2
        cutoff = self.config['highpass_cutoff']
        normal_cutoff = cutoff / nyquist
        
        # 设计巴特沃斯高通滤波器
        b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)
        filtered_audio = signal.filtfilt(b, a, audio_data)
        
        return filtered_audio
    
    def _pre_emphasis(self, audio_data: np.ndarray) -> np.ndarray:
        """预加重滤波器"""
        alpha = self.config['pre_emphasis_coeff']
        emphasized_audio = np.append(audio_data[0], audio_data[1:] - alpha * audio_data[:-1])
        return emphasized_audio
    
    def _noise_reduction(self, audio_data: np.ndarray) -> np.ndarray:
        """噪声消除"""
        # 简单的谱减法噪声消除
        try:
            # 计算频谱
            fft = np.fft.fft(audio_data)
            magnitudes = np.abs(fft)
            phases = np.angle(fft)
            
            # 估计噪声谱（使用前10%的帧）
            noise_frames = max(1, len(audio_data) // 10)
            noise_estimate = np.mean(magnitudes[:noise_frames])
            
            # 谱减法
            enhanced_magnitudes = magnitudes - noise_estimate
            enhanced_magnitudes = np.maximum(enhanced_magnitudes, 0.01 * magnitudes)
            
            # 重建信号
            enhanced_fft = enhanced_magnitudes * np.exp(1j * phases)
            enhanced_audio = np.real(np.fft.ifft(enhanced_fft))
            
            return enhanced_audio
            
        except Exception as e:
            print(f"⚠️ 噪声消除失败: {e}")
            return audio_data
    
    def _normalize_volume(self, audio_data: np.ndarray) -> np.ndarray:
        """音量归一化"""
        if len(audio_data) == 0:
            return audio_data
            
        max_amplitude = np.max(np.abs(audio_data))
        if max_amplitude > 0:
            # 峰值归一化到0.8
            normalized_audio = audio_data * (0.8 / max_amplitude)
            return normalized_audio
        
        return audio_data
    
    def _update_processing_stats(self, duration: float, processing_time: float):
        """更新处理统计信息"""
        self.processing_stats['total_processed'] += 1
        self.processing_stats['total_duration'] += duration
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        old_avg = self.processing_stats['average_processing_time']
        self.processing_stats['average_processing_time'] = (
            alpha * processing_time + (1 - alpha) * old_avg
        )
    
    def extract_features(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """提取音频特征"""
        try:
            # 预处理音频
            processed_audio = self.process(audio_data, sample_rate)
            
            features = {}
            
            # 基础特征
            features['duration'] = len(processed_audio) / sample_rate
            features['sample_rate'] = sample_rate
            features['samples'] = len(processed_audio)
            
            # 时域特征
            features['energy'] = np.mean(processed_audio**2)
            features['rms'] = np.sqrt(features['energy'])
            features['zero_crossing_rate'] = self._calculate_zero_crossing_rate(processed_audio)
            features['peak_amplitude'] = np.max(np.abs(processed_audio))
            
            # 频域特征
            spectral_centroid = self._calculate_spectral_centroid(processed_audio, sample_rate)
            features['spectral_centroid'] = spectral_centroid
            features['spectral_rolloff'] = self._calculate_spectral_rolloff(processed_audio, sample_rate)
            features['spectral_flux'] = self._calculate_spectral_flux(processed_audio, sample_rate)
            
            # 统计特征
            features['mean'] = np.mean(processed_audio)
            features['std'] = np.std(processed_audio)
            features['dynamic_range'] = 20 * np.log10(features['peak_amplitude'] / (features['std'] + 1e-10))
            
            return {
                "success": True,
                "features": features,
                "audio_duration": features['duration'],
                "sample_rate": sample_rate
            }
            
        except Exception as e:
            print(f"❌ 特征提取失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_zero_crossing_rate(self, audio_data: np.ndarray) -> float:
        """计算过零率"""
        if len(audio_data) < 2:
            return 0.0
            
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        return zero_crossings / (len(audio_data) - 1)
    
    def _calculate_spectral_centroid(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """计算频谱质心"""
        if len(audio_data) == 0:
            return 0.0
            
        fft = np.fft.fft(audio_data)
        magnitudes = np.abs(fft)[:len(fft)//2]
        frequencies = np.fft.fftfreq(len(audio_data), 1/sample_rate)[:len(fft)//2]
        
        if np.sum(magnitudes) > 0:
            return np.sum(frequencies * magnitudes) / np.sum(magnitudes)
        return 0.0
    
    def _calculate_spectral_rolloff(self, audio_data: np.ndarray, sample_rate: int, percentile: float = 0.85) -> float:
        """计算频谱滚降点"""
        if len(audio_data) == 0:
            return 0.0
            
        fft = np.fft.fft(audio_data)
        magnitudes = np.abs(fft)[:len(fft)//2]
        frequencies = np.fft.fftfreq(len(audio_data), 1/sample_rate)[:len(fft)//2]
        
        if np.sum(magnitudes) == 0:
            return 0.0
            
        # 计算累积能量
        total_energy = np.sum(magnitudes)
        cumulative_energy = np.cumsum(magnitudes)
        
        # 找到滚降点
        target_energy = percentile * total_energy
        rolloff_index = np.where(cumulative_energy >= target_energy)[0]
        
        if len(rolloff_index) > 0:
            return frequencies[rolloff_index[0]]
        else:
            return frequencies[-1]
    
    def _calculate_spectral_flux(self, audio_data: np.ndarray, sample_rate: int) -> float:
        """计算频谱通量"""
        if len(audio_data) < 512:
            return 0.0
            
        # 分帧处理
        frame_size = int(self.config['frame_size'] * sample_rate)
        hop_size = int(self.config['frame_shift'] * sample_rate)
        
        if len(audio_data) < frame_size:
            return 0.0
            
        num_frames = (len(audio_data) - frame_size) // hop_size + 1
        total_flux = 0.0
        
        previous_spectrum = None
        
        for i in range(num_frames):
            start = i * hop_size
            frame = audio_data[start:start + frame_size]
            
            # 计算当前帧频谱
            spectrum = np.abs(np.fft.fft(frame)[:frame_size//2])
            
            # 计算频谱通量
            if previous_spectrum is not None:
                flux = np.sum((spectrum - previous_spectrum)**2)
                total_flux += flux
            
            previous_spectrum = spectrum
        
        # 平均频谱通量
        if num_frames > 1:
            return total_flux / (num_frames - 1)
        else:
            return 0.0
    
    def set_processing_config(self, config_updates: Dict[str, Any]):
        """设置处理配置"""
        self.config.update(config_updates)
        print("✅ 音频预处理配置已更新")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.processing_stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.processing_stats = {
            'total_processed': 0,
            'total_duration': 0.0,
            'average_processing_time': 0.0
        }
    
    def get_processor_info(self) -> Dict[str, Any]:
        """获取处理器信息"""
        return {
            "processor_name": self.processor_name,
            "version": self.version,
            "target_sample_rate": self.target_sample_rate,
            "is_loaded": self.is_loaded,
            "config": self.config,
            "processing_stats": self.processing_stats
        }
    
    def is_loaded(self) -> bool:
        """检查处理器是否已加载"""
        return self.is_loaded
