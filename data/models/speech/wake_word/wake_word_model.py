"""
唤醒词模型 - 唤醒词检测
"""

import os
import numpy as np
from typing import Dict, Any, Optional, List
import time

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class WakeWordModel:
    """唤醒词检测模型"""
    
    def __init__(self, wake_word: str = "小猫咪", sensitivity: float = 0.5):
        self.model_name = "WakeWordModel"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.model = None
        self.is_loaded = False
        
        # 唤醒词配置
        self.wake_word = wake_word
        self.sensitivity = max(0.1, min(1.0, sensitivity))  # 0.1到1.0
        
        # 支持的唤醒词
        self.supported_wake_words = {
            "小猫咪": "xiao_mao_mi",
            "hello kitty": "hello_kitty", 
            "hey mirexs": "hey_mirexs",
            "你好弥尔思": "ni_hao_mier_si"
        }
        
        # 模型配置
        self.config = {
            'model_type': 'keyword_spotting',
            'use_gpu': True,
            'frame_length': 0.1,  # 100ms帧
            'hop_length': 0.05,   # 50ms跳幅
            'threshold': 0.7,     # 检测阈值
            'smoothing_window': 5 # 平滑窗口
        }
        
        # 检测历史
        self.detection_history = []
        self.max_history = 10
        
    def load(self) -> bool:
        """加载唤醒词模型"""
        try:
            if not TORCH_AVAILABLE:
                print("❌ PyTorch不可用，无法加载唤醒词模型")
                return False
                
            print(f"📦 正在加载唤醒词模型: {self.wake_word}")
            
            # 尝试加载唤醒词模型
            try:
                self._load_mock_model()
                self.is_loaded = True
                print(f"✅ 唤醒词模型加载成功: {self.wake_word}")
                return True
                
            except Exception as e:
                print(f"❌ 加载唤醒词模型失败: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 初始化唤醒词模型失败: {e}")
            return False
    
    def _load_mock_model(self):
        """加载模拟模型"""
        print("🔧 初始化唤醒词模型组件...")
        time.sleep(1)
        
        # 模拟模型加载
        self.model = {
            "type": "KeywordSpotting",
            "feature_extractor": "loaded",
            "classifier": "loaded",
            "wake_word": self.wake_word,
            "status": "active"
        }
        
    def detect(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """检测唤醒词"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"detected": False, "confidence": 0.0, "error": "模型加载失败"}
        
        try:
            start_time = time.time()
            
            # 验证音频数据
            if len(audio_data) == 0:
                return {"detected": False, "confidence": 0.0, "error": "音频数据为空"}
                
            # 提取特征
            features = self._extract_features(audio_data)
            
            # 进行唤醒词检测
            confidence = self._predict_wake_word(features)
            
            # 应用灵敏度调整
            adjusted_confidence = confidence * self.sensitivity
            
            # 判断是否检测到
            threshold = self.config['threshold']
            detected = adjusted_confidence >= threshold
            
            # 更新检测历史
            self._update_detection_history(detected, adjusted_confidence)
            
            processing_time = time.time() - start_time
            
            return {
                "detected": detected,
                "confidence": float(confidence),
                "adjusted_confidence": float(adjusted_confidence),
                "threshold": threshold,
                "processing_time": processing_time,
                "wake_word": self.wake_word
            }
            
        except Exception as e:
            print(f"❌ 唤醒词检测失败: {e}")
            return {"detected": False, "confidence": 0.0, "error": str(e)}
    
    def _extract_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取音频特征"""
        # 实际项目中会提取MFCC、频谱图等特征
        # 这里生成模拟特征
        
        # 计算基础特征
        energy = np.mean(audio_data**2)
        spectral_centroid = self._calculate_spectral_centroid(audio_data)
        zero_crossing_rate = self._calculate_zero_crossing_rate(audio_data)
        
        # 模拟MFCC特征（13维）
        mfcc_features = np.random.randn(13).astype(np.float32)
        
        # 使用实际音频特征影响模拟特征
        mfcc_features[0] = energy * 10
        mfcc_features[1] = spectral_centroid / 1000
        mfcc_features[2] = zero_crossing_rate * 10
        
        return mfcc_features
    
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
    
    def _calculate_zero_crossing_rate(self, audio_data: np.ndarray) -> float:
        """计算过零率"""
        if len(audio_data) < 2:
            return 0.0
            
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        return zero_crossings / (len(audio_data) - 1)
    
    def _predict_wake_word(self, features: np.ndarray) -> float:
        """预测唤醒词置信度"""
        # 实际项目中这里会调用模型进行推理
        # 这里生成模拟置信度
        
        # 基础置信度
        base_confidence = 0.3
        
        # 根据特征计算置信度（模拟）
        energy_feature = features[0]
        spectral_feature = features[1]
        
        # 模拟唤醒词特征匹配
        if energy_feature > 0.01:  # 有足够能量
            base_confidence += 0.3
            
        if 0.1 < spectral_feature < 0.5:  # 合理的频谱范围
            base_confidence += 0.2
            
        # 添加随机性（模拟检测不确定性）
        random_factor = np.random.normal(0, 0.1)
        confidence = base_confidence + random_factor
        
        # 限制在0-1范围内
        confidence = max(0.0, min(1.0, confidence))
        
        return confidence
    
    def _update_detection_history(self, detected: bool, confidence: float):
        """更新检测历史"""
        self.detection_history.append({
            "timestamp": time.time(),
            "detected": detected,
            "confidence": confidence
        })
        
        # 保持历史长度
        if len(self.detection_history) > self.max_history:
            self.detection_history.pop(0)
    
    def set_wake_word(self, wake_word: str, sensitivity: float = None):
        """设置唤醒词"""
        if wake_word in self.supported_wake_words:
            self.wake_word = wake_word
            if sensitivity is not None:
                self.sensitivity = max(0.1, min(1.0, sensitivity))
            
            # 重新加载模型（实际项目中会加载对应的模型）
            self.is_loaded = False
            self.load()
        else:
            print(f"❌ 不支持的唤醒词: {wake_word}")
    
    def get_supported_wake_words(self) -> List[Dict[str, Any]]:
        """获取支持的唤醒词列表"""
        wake_words = []
        for word, model_id in self.supported_wake_words.items():
            wake_words.append({
                "word": word,
                "model_id": model_id,
                "is_current": word == self.wake_word
            })
        return wake_words
    
    def get_detection_history(self) -> List[Dict[str, Any]]:
        """获取检测历史"""
        return self.detection_history.copy()
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "current_wake_word": self.wake_word,
            "sensitivity": self.sensitivity,
            "supported_wake_words": len(self.supported_wake_words),
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded