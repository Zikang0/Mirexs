"""
说话人验证 - 验证说话人身份
"""

import os
import numpy as np
from typing import Dict, Any, Optional, List
import time
import hashlib

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class SpeakerVerification:
    """说话人验证系统"""
    
    def __init__(self):
        self.model_name = "SpeakerVerification"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.model = None
        self.is_loaded = False
        
        # 注册的说话人数据库
        self.speaker_database = {}
        
        # 验证配置
        self.config = {
            'model_type': 'speaker_embedding',
            'use_gpu': True,
            'embedding_dim': 256,
            'verification_threshold': 0.7,  # 验证阈值
            'enrollment_min_duration': 3.0, # 注册最小时长(秒)
            'enrollment_max_duration': 10.0, # 注册最大时长(秒)
            'similarity_metric': 'cosine',  # 相似度度量
            'adaptive_threshold': True      # 自适应阈值
        }
        
        # 说话人统计
        self.speaker_stats = {}
        
    def load(self) -> bool:
        """加载说话人验证模型"""
        try:
            if not TORCH_AVAILABLE:
                print("❌ PyTorch不可用，无法加载说话人验证模型")
                return False
                
            print("📦 正在加载说话人验证模型...")
            
            # 尝试加载说话人验证模型
            try:
                self._load_mock_model()
                self.is_loaded = True
                print("✅ 说话人验证模型加载成功")
                return True
                
            except Exception as e:
                print(f"❌ 加载说话人验证模型失败: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 初始化说话人验证模型失败: {e}")
            return False
    
    def _load_mock_model(self):
        """加载模拟模型"""
        print("🔧 初始化说话人验证模型组件...")
        time.sleep(2)
        
        # 模拟说话人编码器加载
        self.model = {
            "type": "SpeakerEncoder",
            "embedding_dim": self.config['embedding_dim'],
            "architecture": "d-vector",
            "status": "active"
        }
        
    def register(self, audio_data: np.ndarray, sample_rate: int, 
                speaker_id: str, speaker_name: str = None) -> Dict[str, Any]:
        """注册说话人"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"success": False, "error": "模型加载失败"}
        
        try:
            start_time = time.time()
            
            # 验证音频长度
            audio_duration = len(audio_data) / sample_rate
            if audio_duration < self.config['enrollment_min_duration']:
                return {
                    "success": False,
                    "error": f"音频过短，至少需要{self.config['enrollment_min_duration']}秒"
                }
                
            if audio_duration > self.config['enrollment_max_duration']:
                return {
                    "success": False,
                    "error": f"音频过长，最多允许{self.config['enrollment_max_duration']}秒"
                }
            
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 提取说话人特征
            embedding = self._extract_speaker_embedding(processed_audio)
            
            # 生成说话人ID（如果未提供）
            if not speaker_id:
                speaker_id = self._generate_speaker_id(processed_audio)
            
            # 存储说话人信息
            self.speaker_database[speaker_id] = {
                'embedding': embedding,
                'name': speaker_name or speaker_id,
                'sample_rate': self.sample_rate,
                'duration': audio_duration,
                'enrollment_time': time.time(),
                'verification_count': 0,
                'successful_verifications': 0
            }
            
            # 初始化统计信息
            self.speaker_stats[speaker_id] = {
                'enrollments': 1,
                'verification_attempts': 0,
                'successful_verifications': 0,
                'failed_verifications': 0
            }
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "speaker_id": speaker_id,
                "speaker_name": speaker_name or speaker_id,
                "embedding_dim": len(embedding),
                "audio_duration": audio_duration,
                "processing_time": processing_time,
                "message": "说话人注册成功"
            }
            
        except Exception as e:
            print(f"❌ 说话人注册失败: {e}")
            return {"success": False, "error": str(e)}
    
    def verify(self, audio_data: np.ndarray, sample_rate: int, 
              claimed_speaker_id: str = None) -> Dict[str, Any]:
        """验证说话人身份"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"verified": False, "confidence": 0.0, "error": "模型加载失败"}
        
        try:
            start_time = time.time()
            
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 提取测试音频的特征
            test_embedding = self._extract_speaker_embedding(processed_audio)
            
            # 如果没有指定说话人，进行说话人识别
            if claimed_speaker_id is None:
                return self._identify_speaker(test_embedding)
            
            # 验证指定的说话人
            if claimed_speaker_id not in self.speaker_database:
                return {
                    "verified": False, 
                    "confidence": 0.0, 
                    "error": f"说话人未注册: {claimed_speaker_id}"
                }
            
            # 获取注册的特征
            enrolled_embedding = self.speaker_database[claimed_speaker_id]['embedding']
            
            # 计算相似度
            similarity = self._calculate_similarity(test_embedding, enrolled_embedding)
            
            # 应用自适应阈值
            threshold = self._get_adaptive_threshold(claimed_speaker_id)
            
            # 判断验证结果
            verified = similarity >= threshold
            
            # 更新统计信息
            self._update_verification_stats(claimed_speaker_id, verified, similarity)
            
            processing_time = time.time() - start_time
            
            return {
                "verified": verified,
                "confidence": float(similarity),
                "threshold": threshold,
                "speaker_id": claimed_speaker_id,
                "speaker_name": self.speaker_database[claimed_speaker_id]['name'],
                "processing_time": processing_time
            }
            
        except Exception as e:
            print(f"❌ 说话人验证失败: {e}")
            return {"verified": False, "confidence": 0.0, "error": str(e)}
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """音频预处理"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
        # 音量归一化
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        if TORCH_AVAILABLE:
            import torchaudio
            audio_tensor = torch.from_numpy(audio_data).float()
            resampler = torchaudio.transforms.Resample(orig_freq=original_rate, new_freq=target_rate)
            resampled_audio = resampler(audio_tensor)
            return resampled_audio.numpy()
        else:
            import scipy.signal
            num_samples = int(len(audio_data) * target_rate / original_rate)
            return scipy.signal.resample(audio_data, num_samples)
    
    def _extract_speaker_embedding(self, audio_data: np.ndarray) -> np.ndarray:
        """提取说话人特征向量"""
        # 实际项目中这里会调用说话人编码器模型
        # 这里生成模拟的特征向量
        
        # 使用音频的声学特征生成模拟embedding
        energy = np.mean(audio_data**2)
        spectral_centroid = self._calculate_spectral_centroid(audio_data)
        zero_crossing_rate = self._calculate_zero_crossing_rate(audio_data)
        
        # 生成模拟embedding
        embedding = np.random.randn(self.config['embedding_dim']).astype(np.float32)
        
        # 使用音频特征影响embedding（使其与音频相关）
        embedding[0] = energy * 10
        embedding[1] = spectral_centroid / 1000
        embedding[2] = zero_crossing_rate * 10
        
        # 归一化
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        return embedding
    
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
    
    def _generate_speaker_id(self, audio_data: np.ndarray) -> str:
        """生成说话人ID"""
        # 使用音频特征生成唯一ID
        energy = np.mean(audio_data**2)
        spectral_centroid = self._calculate_spectral_centroid(audio_data)
        
        # 创建特征字符串
        feature_string = f"{energy:.6f}_{spectral_centroid:.6f}_{time.time()}"
        
        # 生成哈希ID
        speaker_id = "spk_" + hashlib.md5(feature_string.encode()).hexdigest()[:8]
        
        return speaker_id
    
    def _calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算特征相似度"""
        if self.config['similarity_metric'] == 'cosine':
            # 余弦相似度
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2) + 1e-8
            )
        elif self.config['similarity_metric'] == 'euclidean':
            # 欧氏距离（转换为相似度）
            distance = np.linalg.norm(embedding1 - embedding2)
            similarity = 1.0 / (1.0 + distance)
        else:
            # 默认使用余弦相似度
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2) + 1e-8
            )
        
        return float(similarity)
    
    def _get_adaptive_threshold(self, speaker_id: str) -> float:
        """获取自适应阈值"""
        base_threshold = self.config['verification_threshold']
        
        if not self.config['adaptive_threshold']:
            return base_threshold
        
        # 根据说话人历史调整阈值
        if speaker_id in self.speaker_stats:
            stats = self.speaker_stats[speaker_id]
            total_attempts = stats['verification_attempts']
            success_rate = stats['successful_verifications'] / max(1, total_attempts)
            
            # 如果历史成功率很高，稍微降低阈值
            if success_rate > 0.9 and total_attempts > 5:
                return base_threshold * 0.95
            # 如果历史成功率很低，提高阈值
            elif success_rate < 0.5 and total_attempts > 3:
                return base_threshold * 1.1
        
        return base_threshold
    
    def _update_verification_stats(self, speaker_id: str, verified: bool, confidence: float):
        """更新验证统计信息"""
        if speaker_id not in self.speaker_stats:
            self.speaker_stats[speaker_id] = {
                'enrollments': 0,
                'verification_attempts': 0,
                'successful_verifications': 0,
                'failed_verifications': 0
            }
        
        stats = self.speaker_stats[speaker_id]
        stats['verification_attempts'] += 1
        
        if verified:
            stats['successful_verifications'] += 1
        else:
            stats['failed_verifications'] += 1
    
    def _identify_speaker(self, test_embedding: np.ndarray) -> Dict[str, Any]:
        """说话人识别（不指定说话人）"""
        if not self.speaker_database:
            return {
                "verified": False,
                "confidence": 0.0,
                "error": "没有注册的说话人"
            }
        
        best_similarity = -1
        best_speaker_id = None
        
        # 与所有注册说话人比较
        for speaker_id, speaker_data in self.speaker_database.items():
            enrolled_embedding = speaker_data['embedding']
            similarity = self._calculate_similarity(test_embedding, enrolled_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_speaker_id = speaker_id
        
        # 应用阈值
        threshold = self.config['verification_threshold']
        verified = best_similarity >= threshold
        
        return {
            "verified": verified,
            "confidence": float(best_similarity),
            "threshold": threshold,
            "speaker_id": best_speaker_id,
            "speaker_name": self.speaker_database[best_speaker_id]['name'] if best_speaker_id else None,
            "identification": True  # 标记这是识别而非验证
        }
    
    def get_registered_speakers(self) -> List[Dict[str, Any]]:
        """获取注册的说话人列表"""
        speakers = []
        for speaker_id, data in self.speaker_database.items():
            stats = self.speaker_stats.get(speaker_id, {})
            speakers.append({
                'speaker_id': speaker_id,
                'speaker_name': data['name'],
                'enrollment_time': data['enrollment_time'],
                'audio_duration': data['duration'],
                'verification_attempts': stats.get('verification_attempts', 0),
                'success_rate': stats.get('successful_verifications', 0) / max(1, stats.get('verification_attempts', 1))
            })
        return speakers
    
    def delete_speaker(self, speaker_id: str) -> bool:
        """删除注册的说话人"""
        if speaker_id in self.speaker_database:
            del self.speaker_database[speaker_id]
            if speaker_id in self.speaker_stats:
                del self.speaker_stats[speaker_id]
            return True
        return False
    
    def set_verification_threshold(self, threshold: float):
        """设置验证阈值"""
        self.config['verification_threshold'] = max(0.1, min(1.0, threshold))
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        total_speakers = len(self.speaker_database)
        total_attempts = sum(stats.get('verification_attempts', 0) for stats in self.speaker_stats.values())
        total_success = sum(stats.get('successful_verifications', 0) for stats in self.speaker_stats.values())
        
        overall_success_rate = total_success / max(1, total_attempts)
        
        return {
            "total_speakers": total_speakers,
            "total_verification_attempts": total_attempts,
            "successful_verifications": total_success,
            "overall_success_rate": overall_success_rate,
            "verification_threshold": self.config['verification_threshold']
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "registered_speakers": len(self.speaker_database),
            "embedding_dim": self.config['embedding_dim'],
            "similarity_metric": self.config['similarity_metric'],
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded