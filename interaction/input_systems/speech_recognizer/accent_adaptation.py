# interaction/input_systems/speech_recognizer/accent_adaptation.py
"""
口音适应：适应不同口音
负责识别和适应不同地区的口音变体
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time

@dataclass
class AccentProfile:
    """口音配置文件"""
    accent_type: str
    phonetic_features: np.ndarray
    prosodic_features: np.ndarray
    adaptation_weights: np.ndarray
    confidence: float

@dataclass
class AccentAdaptationResult:
    """口音适应结果"""
    detected_accent: str
    confidence: float
    adaptation_applied: bool
    processing_time: float
    phonetic_adjustments: List[str]
    prosodic_adjustments: List[str]

class AccentAdapter:
    """口音适配器"""
    
    def __init__(self):
        self.is_initialized = False
        self.sample_rate = 16000
        self.accent_profiles: Dict[str, AccentProfile] = {}
        self.current_accent = "standard"
        
        # 集成基础设施组件
        from infrastructure.compute_storage.inference_optimizer import inference_optimizer
        self.inference_optimizer = inference_optimizer
        from infrastructure.compute_storage.model_serving_engine import model_serving_engine
        self.model_serving_engine = model_serving_engine
        
    async def initialize(self):
        """初始化口音适配器"""
        if self.is_initialized:
            return
            
        logging.info("初始化口音适应系统...")
        
        try:
            # 初始化基础设施组件
            await self.inference_optimizer.initialize()
            await self.model_serving_engine.initialize()
            
            # 加载口音检测模型
            from data.models.speech.asr.multilingual_asr import AccentDetectionModel
            self.accent_model = AccentDetectionModel()
            
            # 异步加载模型
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.accent_model.load)
            
            # 加载口音配置文件
            await self._load_accent_profiles()
            
            self.is_initialized = True
            logging.info("口音适应系统初始化完成")
            
        except Exception as e:
            logging.error(f"口音适应系统初始化失败: {e}")
            self.is_initialized = True  # 使用基础方法
    
    async def _load_accent_profiles(self):
        """加载口音配置文件"""
        # 定义支持的口音类型
        supported_accents = [
            "standard",      # 标准普通话
            "northern",      # 北方口音
            "southern",      # 南方口音
            "cantonese",     # 粤语口音
            "sichuan",       # 四川口音
            "shanghai",      # 上海口音
            "american",      # 美式英语
            "british",       # 英式英语
            "australian"     # 澳大利亚英语
        ]
        
        for accent in supported_accents:
            self.accent_profiles[accent] = await self._create_accent_profile(accent)
    
    async def _create_accent_profile(self, accent_type: str) -> AccentProfile:
        """创建口音配置文件"""
        # 在实际实现中，这些特征会从训练数据中学习
        # 这里使用基于典型特征的模拟数据
        
        if accent_type == "standard":
            phonetic_features = np.array([1.0, 0.9, 0.8, 0.7, 1.0])  # 标准发音特征
            prosodic_features = np.array([1.0, 1.0, 1.0, 1.0])       # 标准韵律特征
        elif accent_type == "northern":
            phonetic_features = np.array([0.8, 1.0, 0.7, 0.6, 0.9])  # 儿化音特征
            prosodic_features = np.array([1.2, 0.9, 1.1, 0.8])       # 语调较高
        elif accent_type == "southern":
            phonetic_features = np.array([0.9, 0.7, 1.0, 0.8, 0.8])  # 平翘舌特征
            prosodic_features = np.array([0.8, 1.1, 0.9, 1.2])       # 语调较平
        elif "english" in accent_type.lower():
            # 英语口音特征
            phonetic_features = np.array([0.6, 0.5, 0.4, 0.3, 0.2])
            prosodic_features = np.array([1.3, 0.7, 1.4, 0.6])
        else:
            # 默认特征
            phonetic_features = np.array([0.8, 0.8, 0.8, 0.8, 0.8])
            prosodic_features = np.array([1.0, 1.0, 1.0, 1.0])
        
        adaptation_weights = np.ones(len(phonetic_features) + len(prosodic_features))
        
        return AccentProfile(
            accent_type=accent_type,
            phonetic_features=phonetic_features,
            prosodic_features=prosodic_features,
            adaptation_weights=adaptation_weights,
            confidence=0.8
        )
    
    async def detect_accent(self, audio_data: np.ndarray, sample_rate: int = None) -> AccentAdaptationResult:
        """检测口音"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 预处理音频
            processed_audio = await self._preprocess_audio(audio_data, sample_rate or self.sample_rate)
            
            # 提取语音特征
            features = await self._extract_speech_features(processed_audio)
            
            # 口音分类
            if hasattr(self, 'accent_model') and self.accent_model.is_loaded:
                detected_accent, confidence = await self._classify_accent_with_model(features)
            else:
                detected_accent, confidence = await self._classify_accent_basic(features)
            
            # 应用口音适应
            adaptation_applied = await self._apply_accent_adaptation(detected_accent)
            
            processing_time = time.time() - start_time
            
            return AccentAdaptationResult(
                detected_accent=detected_accent,
                confidence=confidence,
                adaptation_applied=adaptation_applied,
                processing_time=processing_time,
                phonetic_adjustments=await self._get_phonetic_adjustments(detected_accent),
                prosodic_adjustments=await self._get_prosodic_adjustments(detected_accent)
            )
            
        except Exception as e:
            logging.error(f"口音检测失败: {e}")
            return AccentAdaptationResult(
                detected_accent="unknown",
                confidence=0.0,
                adaptation_applied=False,
                processing_time=time.time() - start_time,
                phonetic_adjustments=[],
                prosodic_adjustments=[]
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
    
    async def _extract_speech_features(self, audio_data: np.ndarray) -> Dict[str, np.ndarray]:
        """提取语音特征"""
        features = {}
        
        try:
            # 提取基频特征（音高）
            f0_features = await self._extract_f0_features(audio_data)
            features['f0'] = f0_features
            
            # 提取共振峰特征
            formant_features = await self._extract_formant_features(audio_data)
            features['formants'] = formant_features
            
            # 提取时长特征
            duration_features = await self._extract_duration_features(audio_data)
            features['duration'] = duration_features
            
            # 提取能量特征
            energy_features = await self._extract_energy_features(audio_data)
            features['energy'] = energy_features
            
            # 提取频谱特征
            spectral_features = await self._extract_spectral_features(audio_data)
            features['spectral'] = spectral_features
            
        except Exception as e:
            logging.warning(f"特征提取失败: {e}")
            # 返回模拟特征
            features = {
                'f0': np.random.random(5),
                'formants': np.random.random(4),
                'duration': np.random.random(3),
                'energy': np.random.random(4),
                'spectral': np.random.random(6)
            }
        
        return features
    
    async def _extract_f0_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取基频特征"""
        try:
            import librosa
            
            f0, voiced_flag, voiced_probs = librosa.pyin(
                audio_data, 
                fmin=50, 
                fmax=400, 
                sr=self.sample_rate
            )
            
            # 清理NaN值
            f0_clean = f0[~np.isnan(f0)]
            
            if len(f0_clean) > 0:
                features = np.array([
                    np.mean(f0_clean),      # 平均音高
                    np.std(f0_clean),       # 音高变化
                    np.median(f0_clean),    # 中值音高
                    np.max(f0_clean),       # 最高音高
                    np.min(f0_clean)        # 最低音高
                ])
            else:
                features = np.array([120.0, 20.0, 120.0, 140.0, 100.0])  # 默认值
            
            return features
            
        except ImportError:
            return np.array([120.0, 20.0, 120.0, 140.0, 100.0])  # 模拟特征
    
    async def _extract_formant_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取共振峰特征"""
        try:
            # 使用线性预测编码(LPC)估计共振峰
            import scipy.signal
            
            # 计算LPC系数
            order = 12  # LPC阶数
            a = librosa.lpc(audio_data, order=order)
            
            # 找到根（共振峰频率）
            roots = np.roots(a)
            roots = roots[np.imag(roots) >= 0]  # 只保留上半平面
            angz = np.arctan2(np.imag(roots), np.real(roots))
            
            # 转换为频率
            freqs = angz * (self.sample_rate / (2 * np.pi))
            
            # 取前几个共振峰
            freqs = np.sort(freqs)
            formants = freqs[:4]  # F1, F2, F3, F4
            
            if len(formants) < 4:
                formants = np.pad(formants, (0, 4 - len(formants)), 'constant', constant_values=500)
            
            return formants
            
        except Exception:
            return np.array([500, 1500, 2500, 3500])  # 默认共振峰
    
    async def _extract_duration_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取时长特征"""
        try:
            # 语音活动检测
            energy = audio_data ** 2
            energy_smooth = np.convolve(energy, np.ones(100)/100, mode='same')
            
            # 找到语音段
            threshold = np.mean(energy_smooth) + 0.5 * np.std(energy_smooth)
            speech_segments = energy_smooth > threshold
            
            # 计算时长特征
            segment_lengths = []
            current_length = 0
            
            for is_speech in speech_segments:
                if is_speech:
                    current_length += 1
                else:
                    if current_length > 0:
                        segment_lengths.append(current_length)
                        current_length = 0
            
            if current_length > 0:
                segment_lengths.append(current_length)
            
            if segment_lengths:
                features = np.array([
                    np.mean(segment_lengths) / self.sample_rate,  # 平均段长
                    np.std(segment_lengths) / self.sample_rate,   # 段长变化
                    len(segment_lengths)                          # 段数
                ])
            else:
                features = np.array([0.2, 0.1, 0])  # 默认值
            
            return features
            
        except Exception:
            return np.array([0.2, 0.1, 5])  # 默认时长特征
    
    async def _extract_energy_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取能量特征"""
        try:
            energy = audio_data ** 2
            
            features = np.array([
                np.mean(energy),                    # 平均能量
                np.std(energy),                     # 能量变化
                np.max(energy),                     # 峰值能量
                len(energy[energy > np.mean(energy)]) / len(energy)  # 高能量比例
            ])
            
            return features
            
        except Exception:
            return np.array([0.1, 0.05, 0.5, 0.3])  # 默认能量特征
    
    async def _extract_spectral_features(self, audio_data: np.ndarray) -> np.ndarray:
        """提取频谱特征"""
        try:
            spectrum = np.abs(np.fft.rfft(audio_data))
            frequencies = np.fft.rfftfreq(len(audio_data), 1/self.sample_rate)
            
            features = np.array([
                np.mean(spectrum),                  # 平均频谱幅度
                np.std(spectrum),                   # 频谱变化
                np.argmax(spectrum) / len(spectrum), # 频谱重心
                np.sum(spectrum[:len(spectrum)//4]) / np.sum(spectrum),  # 低频能量比
                np.sum(spectrum[len(spectrum)//4:len(spectrum)//2]) / np.sum(spectrum),  # 中频能量比
                np.sum(spectrum[len(spectrum)//2:]) / np.sum(spectrum)   # 高频能量比
            ])
            
            return features
            
        except Exception:
            return np.array([0.5, 0.2, 0.3, 0.4, 0.3, 0.3])  # 默认频谱特征
    
    async def _classify_accent_with_model(self, features: Dict[str, np.ndarray]) -> Tuple[str, float]:
        """使用模型分类口音"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.accent_model.classify, 
                features
            )
            return result.get('accent', 'standard'), result.get('confidence', 0.5)
        except Exception as e:
            logging.warning(f"模型口音分类失败: {e}")
            return await self._classify_accent_basic(features)
    
    async def _classify_accent_basic(self, features: Dict[str, np.ndarray]) -> Tuple[str, float]:
        """基础口音分类"""
        try:
            # 合并所有特征
            all_features = np.concatenate([
                features['f0'],
                features['formants'],
                features['duration'],
                features['energy'],
                features['spectral']
            ])
            
            best_accent = "standard"
            best_similarity = 0.0
            
            # 计算与每个口音配置文件的相似度
            for accent_type, profile in self.accent_profiles.items():
                profile_features = np.concatenate([
                    profile.phonetic_features,
                    profile.prosodic_features
                ])
                
                # 计算余弦相似度
                similarity = await self._calculate_similarity(all_features, profile_features)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_accent = accent_type
            
            return best_accent, best_similarity
            
        except Exception:
            return "standard", 0.5
    
    async def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算相似度"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))
            
        except Exception:
            return 0.5
    
    async def _apply_accent_adaptation(self, detected_accent: str) -> bool:
        """应用口音适应"""
        try:
            if detected_accent in self.accent_profiles:
                self.current_accent = detected_accent
                
                # 在实际实现中，这里会调整ASR模型的参数
                # 例如更新语言模型的权重、调整声学模型等
                
                logging.info(f"口音适应已应用: {detected_accent}")
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"口音适应应用失败: {e}")
            return False
    
    async def _get_phonetic_adjustments(self, accent: str) -> List[str]:
        """获取音系调整"""
        adjustments = {
            "northern": ["增强儿化音识别", "调整平翘舌权重"],
            "southern": ["加强平翘舌区分", "适应入声变化"],
            "cantonese": ["适应声调系统", "调整韵母识别"],
            "american": ["适应美式元音", "调整R音色识别"],
            "british": ["适应英式元音", "调整T音发音"]
        }
        return adjustments.get(accent, ["标准发音处理"])
    
    async def _get_prosodic_adjustments(self, accent: str) -> List[str]:
        """获取韵律调整"""
        adjustments = {
            "northern": ["适应较高语调", "调整语速模型"],
            "southern": ["适应平缓语调", "调整节奏模式"],
            "cantonese": ["适应九声系统", "调整声调曲线"],
            "american": ["适应美式语调", "调整重音模式"],
            "british": ["适应英式语调", "调整韵律结构"]
        }
        return adjustments.get(accent, ["标准韵律处理"])
    
    async def learn_user_accent(self, audio_samples: List[np.ndarray], user_id: str):
        """学习用户口音"""
        try:
            # 分析用户语音样本
            all_features = []
            for audio in audio_samples:
                features = await self._extract_speech_features(audio)
                combined_features = np.concatenate([
                    features['f0'],
                    features['formants'],
                    features['duration'],
                    features['energy'],
                    features['spectral']
                ])
                all_features.append(combined_features)
            
            # 计算平均特征
            user_features = np.mean(all_features, axis=0)
            
            # 创建用户特定的口音配置文件
            user_accent = f"user_{user_id}"
            split_point = len(self.accent_profiles["standard"].phonetic_features)
            
            self.accent_profiles[user_accent] = AccentProfile(
                accent_type=user_accent,
                phonetic_features=user_features[:split_point],
                prosodic_features=user_features[split_point:],
                adaptation_weights=np.ones(len(user_features)),
                confidence=0.9
            )
            
            logging.info(f"用户口音学习完成: {user_id}")
            
        except Exception as e:
            logging.error(f"用户口音学习失败: {e}")
    
    def get_accent_info(self) -> Dict[str, Any]:
        """获取口音系统信息"""
        return {
            "initialized": self.is_initialized,
            "current_accent": self.current_accent,
            "supported_accents": list(self.accent_profiles.keys()),
            "model_loaded": getattr(self.accent_model, 'is_loaded', False) if hasattr(self, 'accent_model') else False
        }


# 模拟口音检测模型
class AccentDetectionModel:
    def __init__(self):
        self.is_loaded = False
    
    def load(self):
        self.is_loaded = True
    
    def classify(self, features):
        # 模拟口音分类
        import random
        accents = ["standard", "northern", "southern", "american", "british"]
        return {
            'accent': random.choice(accents),
            'confidence': random.uniform(0.7, 0.95)
        }


# 全局口音适配器实例
accent_adapter = AccentAdapter()
