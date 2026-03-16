"""
中文语音识别模型 - 中文语音转文本
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import time

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class ChineseASRModel:
    """中文语音识别模型"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_name = "ChineseASR"
        self.language = "zh-CN"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.model = None
        self.processor = None
        self.is_loaded = False
        
        # 模型配置
        self.config = {
            'model_size': 'base',
            'use_gpu': True,
            'beam_size': 5,
            'hotwords': [],  # 热词列表
            'vad_enabled': True  # 语音活动检测
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载中文ASR模型"""
        try:
            if not TORCH_AVAILABLE:
                print("❌ PyTorch不可用，无法加载中文ASR模型")
                return False
                
            # 尝试加载预训练的中文语音识别模型
            try:
                from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
                
                model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"
                self.processor = Wav2Vec2Processor.from_pretrained(model_name)
                self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
                
                # 移动到GPU（如果可用）
                if self.config['use_gpu'] and torch.cuda.is_available():
                    self.model = self.model.cuda()
                    
                self.is_loaded = True
                print(f"✅ 中文ASR模型加载成功: {model_name}")
                return True
                
            except ImportError:
                print("❌ transformers库不可用")
                return False
                
        except Exception as e:
            print(f"❌ 加载中文ASR模型失败: {e}")
            return False
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """语音识别主函数"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"text": "", "confidence": 0.0, "success": False}
        
        try:
            start_time = time.time()
            
            # 预处理音频
            processed_audio = self._preprocess_audio(audio_data, sample_rate)
            
            # 语音活动检测
            if self.config['vad_enabled']:
                has_speech = self._voice_activity_detection(processed_audio)
                if not has_speech:
                    return {"text": "", "confidence": 0.0, "success": True, "no_speech": True}
            
            # 进行语音识别
            inputs = self.processor(processed_audio, 
                                  sampling_rate=self.sample_rate, 
                                  return_tensors="pt", 
                                  padding=True)
            
            # 移动到GPU
            if self.config['use_gpu'] and torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 推理
            with torch.no_grad():
                logits = self.model(**inputs).logits
            
            # 解码
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            
            # 计算置信度
            confidence = self._calculate_confidence(logits, predicted_ids)
            
            processing_time = time.time() - start_time
            
            return {
                "text": transcription,
                "confidence": confidence,
                "success": True,
                "processing_time": processing_time,
                "language": self.language
            }
            
        except Exception as e:
            print(f"❌ 中文语音识别失败: {e}")
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}
    
    def _preprocess_audio(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """预处理音频数据"""
        # 转换为单声道
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # 重采样到目标采样率
        if sample_rate != self.sample_rate:
            audio_data = self._resample_audio(audio_data, sample_rate, self.sample_rate)
        
        # 归一化
        audio_data = audio_data / np.max(np.abs(audio_data))
        
        return audio_data
    
    def _resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """重采样音频"""
        if TORCH_AVAILABLE:
            # 使用torchaudio重采样
            audio_tensor = torch.from_numpy(audio_data).float()
            resampler = torchaudio.transforms.Resample(orig_freq=original_rate, new_freq=target_rate)
            resampled_audio = resampler(audio_tensor)
            return resampled_audio.numpy()
        else:
            # 简单的线性重采样
            import scipy.signal
            num_samples = int(len(audio_data) * target_rate / original_rate)
            return scipy.signal.resample(audio_data, num_samples)
    
    def _voice_activity_detection(self, audio_data: np.ndarray, threshold: float = 0.01) -> bool:
        """简单的语音活动检测"""
        # 计算音频的RMS能量
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > threshold
    
    def _calculate_confidence(self, logits: torch.Tensor, predicted_ids: torch.Tensor) -> float:
        """计算识别置信度"""
        try:
            # 使用softmax计算概率
            probabilities = torch.nn.functional.softmax(logits, dim=-1)
            
            # 获取预测token的概率
            batch_size, seq_length, vocab_size = probabilities.shape
            confidence_scores = []
            
            for i in range(batch_size):
                for j in range(seq_length):
                    token_id = predicted_ids[i, j].item()
                    prob = probabilities[i, j, token_id].item()
                    confidence_scores.append(prob)
            
            # 计算平均置信度（忽略padding）
            valid_scores = [score for score in confidence_scores if score > 0.1]
            if valid_scores:
                return float(np.mean(valid_scores))
            else:
                return 0.0
                
        except Exception:
            return 0.5  # 默认置信度
    
    def set_hotwords(self, hotwords: List[str]) -> None:
        """设置热词（提升特定词汇的识别概率）"""
        self.config['hotwords'] = hotwords
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded