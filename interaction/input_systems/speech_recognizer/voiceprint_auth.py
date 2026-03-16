# interaction/input_systems/speech_recognizer/voiceprint_auth.py
"""
声纹认证：通过声纹识别用户身份
负责用户身份验证和声纹识别
"""

import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
import time
import hashlib

@dataclass
class VoicePrint:
    """声纹特征"""
    user_id: str
    features: np.ndarray
    created_time: float
    confidence: float

@dataclass
class AuthResult:
    """认证结果"""
    authenticated: bool
    user_id: Optional[str]
    confidence: float
    similarity: float
    processing_time: float

class VoicePrintAuthenticator:
    """声纹认证器"""
    
    def __init__(self):
        self.voice_prints: Dict[str, VoicePrint] = {}
        self.auth_threshold = 0.8
        self.is_initialized = False
        self.model = None
        
    async def initialize(self):
        """初始化声纹认证器"""
        if self.is_initialized:
            return
            
        logging.info("初始化声纹认证系统...")
        
        try:
            # 加载声纹模型
            from data.models.speech.wake_word.speaker_verification import SpeakerVerificationModel
            self.model = SpeakerVerificationModel()
            
            # 异步加载模型
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.model.load)
            
            # 加载已注册的声纹
            await self._load_voice_prints()
            
            self.is_initialized = True
            logging.info("声纹认证系统初始化完成")
            
        except Exception as e:
            logging.warning(f"声纹模型加载失败: {e}")
            self.is_initialized = True  # 使用基础方法
    
    async def _load_voice_prints(self):
        """加载已注册的声纹"""
        # 在实际实现中，这里会从数据库加载声纹数据
        # 这里使用模拟数据
        pass
    
    async def register_voice_print(self, user_id: str, audio_samples: List[np.ndarray]) -> bool:
        """注册用户声纹"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            if self.model and self.model.is_loaded:
                # 使用模型提取声纹特征
                features = await self._extract_features_with_model(audio_samples)
            else:
                # 使用基础特征提取
                features = await self._extract_basic_features(audio_samples)
            
            # 创建声纹记录
            voice_print = VoicePrint(
                user_id=user_id,
                features=features,
                created_time=time.time(),
                confidence=0.9  # 初始置信度
            )
            
            # 保存声纹
            self.voice_prints[user_id] = voice_print
            
            # 保存到持久化存储（在实际实现中）
            await self._save_voice_print(voice_print)
            
            logging.info(f"用户声纹注册成功: {user_id}")
            return True
            
        except Exception as e:
            logging.error(f"声纹注册失败 {user_id}: {e}")
            return False
    
    async def authenticate(self, audio_data: np.ndarray, sample_rate: int = 16000) -> AuthResult:
        """声纹认证"""
        if not self.is_initialized:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 提取测试音频特征
            if self.model and self.model.is_loaded:
                test_features = await self._extract_features_with_model([audio_data])
            else:
                test_features = await self._extract_basic_features([audio_data])
            
            best_match = None
            best_similarity = 0.0
            
            # 与所有注册声纹进行比较
            for user_id, voice_print in self.voice_prints.items():
                similarity = await self._calculate_similarity(test_features, voice_print.features)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = user_id
            
            # 判断认证结果
            authenticated = best_similarity >= self.auth_threshold
            confidence = min(1.0, best_similarity * 1.2)  # 调整置信度
            
            processing_time = time.time() - start_time
            
            return AuthResult(
                authenticated=authenticated,
                user_id=best_match if authenticated else None,
                confidence=confidence,
                similarity=best_similarity,
                processing_time=processing_time
            )
            
        except Exception as e:
            logging.error(f"声纹认证失败: {e}")
            return AuthResult(
                authenticated=False,
                user_id=None,
                confidence=0.0,
                similarity=0.0,
                processing_time=time.time() - start_time
            )
    
    async def _extract_features_with_model(self, audio_samples: List[np.ndarray]) -> np.ndarray:
        """使用模型提取声纹特征"""
        loop = asyncio.get_event_loop()
        
        # 提取每个样本的特征并取平均
        features_list = []
        for audio in audio_samples:
            features = await loop.run_in_executor(
                None, 
                self.model.extract_features, 
                audio
            )
            features_list.append(features)
        
        return np.mean(features_list, axis=0)
    
    async def _extract_basic_features(self, audio_samples: List[np.ndarray]) -> np.ndarray:
        """基础声纹特征提取"""
        all_features = []
        
        for audio in audio_samples:
            # 提取基础音频特征
            features = []
            
            # 能量特征
            energy = np.mean(audio ** 2)
            features.append(energy)
            
            # 频谱特征
            spectrum = np.abs(np.fft.fft(audio))
            spectral_centroid = np.sum(np.arange(len(spectrum)) * spectrum) / np.sum(spectrum)
            features.append(spectral_centroid)
            
            # 过零率
            zero_crossings = np.sum(np.diff(np.signbit(audio))) / len(audio)
            features.append(zero_crossings)
            
            # MFCC特征（模拟）
            mfcc_like = np.random.random(10)  # 模拟10维MFCC特征
            features.extend(mfcc_like)
            
            all_features.append(np.array(features))
        
        # 返回平均特征
        return np.mean(all_features, axis=0)
    
    async def _calculate_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算特征相似度"""
        try:
            # 余弦相似度
            dot_product = np.dot(features1, features2)
            norm1 = np.linalg.norm(features1)
            norm2 = np.linalg.norm(features2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))
            
        except Exception:
            return 0.0
    
    async def _save_voice_print(self, voice_print: VoicePrint):
        """保存声纹到持久化存储"""
        # 在实际实现中，这里会保存到数据库
        # 这里使用模拟实现
        pass
    
    async def delete_voice_print(self, user_id: str) -> bool:
        """删除用户声纹"""
        if user_id in self.voice_prints:
            del self.voice_prints[user_id]
            logging.info(f"用户声纹删除成功: {user_id}")
            return True
        return False
    
    def set_auth_threshold(self, threshold: float):
        """设置认证阈值"""
        self.auth_threshold = threshold
    
    def get_registered_users(self) -> List[str]:
        """获取已注册用户列表"""
        return list(self.voice_prints.keys())
    
    def get_auth_system_info(self) -> Dict[str, Any]:
        """获取认证系统信息"""
        return {
            "initialized": self.is_initialized,
            "registered_users": len(self.voice_prints),
            "auth_threshold": self.auth_threshold,
            "model_loaded": self.model.is_loaded if self.model else False
        }


# 模拟声纹验证模型
class SpeakerVerificationModel:
    def __init__(self):
        self.is_loaded = False
    
    def load(self):
        self.is_loaded = True
    
    def extract_features(self, audio_data):
        # 返回模拟特征向量
        return np.random.random(512)


# 全局声纹认证器实例
voice_authenticator = VoicePrintAuthenticator()
