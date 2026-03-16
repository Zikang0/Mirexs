"""
语音活动检测 - 检测语音活动
"""

import numpy as np
from typing import Dict, Any, List
import time

class VoiceActivityDetector:
    """语音活动检测器"""
    
    def __init__(self):
        self.model_name = "VoiceActivityDetector"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.is_loaded = False
        
        # 检测配置
        self.config = {
            'energy_threshold': 0.01,      # 能量阈值
            'spectral_flux_threshold': 0.1, # 频谱通量阈值
            'zcr_threshold': 0.1,          # 过零率阈值
            'min_speech_duration': 0.1,    # 最小语音时长(秒)
            'frame_length': 0.025,         # 帧长度(秒)
            'hop_length': 0.01,            # 帧跳跃(秒)
            'noise_adaptation': True,      # 噪声自适应
            'aggressive_mode': 0           # 激进模式 0-3
        }
        
        # 噪声估计
        self.noise_estimate = None
        self.noise_adaptation_rate = 0.98
        
        # 状态跟踪
        self.speech_state = False
        self.speech_start_time = 0
        self.speech_duration = 0
        
    def load(self) -> bool:
        """加载VAD模型"""
        try:
            print("📦 初始化语音活动检测器...")
            
            # VAD通常不需要复杂模型加载
            self.is_loaded = True
            print("✅ 语音活动检测器初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 初始化语音活动检测器失败: {e}")
            return False
    
    def detect(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """检测语音活动"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"speech_detected": False, "confidence": 0.0, "error": "初始化失败"}
        
        try:
            start_time = time.time()
            
            # 验证音频数据
            if len(audio_data) == 0:
                return {"speech_detected": False, "confidence": 0.0, "error": "音频数据为空"}
                
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data)
            
            # 提取特征
            features = self._extract_features(processed_audio)
            
            # 检测语音活动
            speech_detected, confidence = self._detect_speech(features, processed_audio)
            
            # 更新状态跟踪
            self._update_speech_state(speech_detected)
            
            processing_time = time.time() - start_time
            
            return {
                "speech_detected": speech_detected,
                "confidence": float(confidence),
                "speech_duration": self.speech_duration,
                "processing_time": processing_time,
                "features": {
                    "energy": float(features["energy"]),
                    "spectral_flux": float(features["spectral_flux"]),
                    "zero_crossing_rate": float(features["zero_crossing_rate"])
                }
            }
            
        except Exception as e:
            print(f"❌ 语音活动检测失败: {e}")
            return {"speech_detected": False, "confidence": 0.0, "error": str(e)}
    
    def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """预处理音频"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 高通滤波（去除DC偏移和低频噪声）
        processed_audio = self._highpass_filter(audio_data, cutoff=80)
        
        return processed_audio
    
    def _highpass_filter(self, audio_data: np.ndarray, cutoff: float) -> np.ndarray:
        """高通滤波器"""
        from scipy import signal
        
        nyquist = self.sample_rate / 2
        normal_cutoff = cutoff / nyquist
        
        # 设计巴特沃斯高通滤波器
        b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)
        filtered_audio = signal.filtfilt(b, a, audio_data)
        
        return filtered_audio
    
    def _extract_features(self, audio_data: np.ndarray) -> Dict[str, float]:
        """提取语音活动特征"""
        features = {}
        
        # 1. 能量特征
        features["energy"] = np.mean(audio_data**2)
        
        # 2. 频谱通量
        features["spectral_flux"] = self._calculate_spectral_flux(audio_data)
        
        # 3. 过零率
        features["zero_crossing_rate"] = self._calculate_zero_crossing_rate(audio_data)
        
        # 4. 频谱质心
        features["spectral_centroid"] = self._calculate_spectral_centroid(audio_data)
        
        # 5. 频谱滚降点
        features["spectral_rolloff"] = self._calculate_spectral_rolloff(audio_data)
        
        return features
    
    def _calculate_spectral_flux(self, audio_data: np.ndarray) -> float:
        """计算频谱通量"""
        if len(audio_data) < 512:
            return 0.0
            
        # 分帧处理
        frame_size = int(self.config['frame_length'] * self.sample_rate)
        hop_size = int(self.config['hop_length'] * self.sample_rate)
        
        if len(audio_data) < frame_size:
            return 0.0
            
        # 计算当前帧频谱
        current_frame = audio_data[:frame_size]
        current_spectrum = np.abs(np.fft.fft(current_frame)[:frame_size//2])
        
        # 如果有前一帧，计算通量
        if hasattr(self, 'previous_spectrum') and self.previous_spectrum is not None:
            flux = np.sum((current_spectrum - self.previous_spectrum)**2)
        else:
            flux = 0.0
            
        # 保存当前频谱
        self.previous_spectrum = current_spectrum
        
        return flux
    
    def _calculate_zero_crossing_rate(self, audio_data: np.ndarray) -> float:
        """计算过零率"""
        if len(audio_data) < 2:
            return 0.0
            
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        return zero_crossings / (len(audio_data) - 1)
    
    def _calculate_spectral_centroid(self, audio_data: np.ndarray) -> float:
        """计算频谱质心"""
        if len(audio_data) == 0:
            return 0.0
            
        fft = np.fft.fft(audio_data)
        magnitudes = np.abs(fft)[:len(fft)//2]
        frequencies = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)[:len(fft)//2]
        
        if np.sum(magnitudes) > 0:
            return np.sum(frequencies * magnitudes) / np.sum(magnitudes)
        return 0.0
    
    def _calculate_spectral_rolloff(self, audio_data: np.ndarray, percentile: float = 0.85) -> float:
        """计算频谱滚降点"""
        if len(audio_data) == 0:
            return 0.0
            
        fft = np.fft.fft(audio_data)
        magnitudes = np.abs(fft)[:len(fft)//2]
        frequencies = np.fft.fftfreq(len(audio_data), 1/self.sample_rate)[:len(fft)//2]
        
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
    
    def _detect_speech(self, features: Dict[str, float], audio_data: np.ndarray) -> tuple:
        """检测语音活动"""
        # 基于多特征决策
        scores = []
        
        # 1. 能量得分
        energy_threshold = self.config['energy_threshold']
        energy_score = min(1.0, features["energy"] / (energy_threshold * 2))
        scores.append(energy_score)
        
        # 2. 频谱通量得分
        flux_threshold = self.config['spectral_flux_threshold']
        flux_score = min(1.0, features["spectral_flux"] / (flux_threshold * 3))
        scores.append(flux_score)
        
        # 3. 过零率得分
        zcr_threshold = self.config['zcr_threshold']
        zcr_score = min(1.0, features["zero_crossing_rate"] / (zcr_threshold * 2))
        scores.append(zcr_score)
        
        # 计算综合置信度
        confidence = np.mean(scores)
        
        # 应用噪声自适应
        if self.config['noise_adaptation']:
            confidence = self._apply_noise_adaptation(confidence, features)
        
        # 应用激进模式
        if self.config['aggressive_mode'] > 0:
            confidence = self._apply_aggressive_mode(confidence)
        
        # 决策
        detection_threshold = 0.5
        speech_detected = confidence > detection_threshold
        
        return speech_detected, confidence
    
    def _apply_noise_adaptation(self, confidence: float, features: Dict[str, float]) -> float:
        """应用噪声自适应"""
        # 初始化噪声估计
        if self.noise_estimate is None:
            self.noise_estimate = features["energy"]
        
        # 更新噪声估计（如果当前不是语音）
        if confidence < 0.3:
            self.noise_estimate = (self.noise_adaptation_rate * self.noise_estimate + 
                                 (1 - self.noise_adaptation_rate) * features["energy"])
        
        # 基于噪声估计调整置信度
        if self.noise_estimate > 0:
            snr = features["energy"] / self.noise_estimate
            snr_factor = min(2.0, snr) / 2.0  # 归一化到0-1
            confidence = confidence * (0.5 + 0.5 * snr_factor)
        
        return confidence
    
    def _apply_aggressive_mode(self, confidence: float) -> float:
        """应用激进模式"""
        mode = self.config['aggressive_mode']
        
        if mode == 1:
            # 模式1：稍微降低阈值
            return confidence * 1.1
        elif mode == 2:
            # 模式2：中等降低阈值
            return confidence * 1.2
        elif mode == 3:
            # 模式3：大幅降低阈值
            return confidence * 1.3
        else:
            return confidence
    
    def _update_speech_state(self, speech_detected: bool):
        """更新语音状态"""
        current_time = time.time()
        
        if speech_detected:
            if not self.speech_state:
                # 语音开始
                self.speech_state = True
                self.speech_start_time = current_time
            # 更新持续时间
            self.speech_duration = current_time - self.speech_start_time
        else:
            if self.speech_state:
                # 检查是否应该结束语音状态
                if current_time - self.speech_start_time > self.speech_duration + 0.5:  # 0.5秒静音后结束
                    self.speech_state = False
                    self.speech_duration = 0
    
    def set_aggressive_mode(self, mode: int):
        """设置激进模式"""
        self.config['aggressive_mode'] = max(0, min(3, mode))
    
    def reset_noise_estimate(self):
        """重置噪声估计"""
        self.noise_estimate = None
    
    def get_detector_info(self) -> Dict[str, Any]:
        """获取检测器信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "speech_state": self.speech_state,
            "speech_duration": self.speech_duration,
            "noise_estimate": self.noise_estimate,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查检测器是否已加载"""
        return self.is_loaded