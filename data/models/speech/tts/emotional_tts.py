"""
情感语音合成 - 带情感的语音合成
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

class EmotionalTTS:
    """情感语音合成模型"""
    
    def __init__(self):
        self.model_name = "EmotionalTTS"
        self.version = "1.0.0"
        self.sample_rate = 22050
        self.model = None
        self.is_loaded = False
        
        # 支持的情感类型
        self.emotions = {
            'neutral': {'intensity': 0.5, 'pitch_variance': 0.1, 'speed': 1.0},
            'happy': {'intensity': 0.8, 'pitch_variance': 0.3, 'speed': 1.2},
            'sad': {'intensity': 0.6, 'pitch_variance': 0.05, 'speed': 0.8},
            'angry': {'intensity': 0.9, 'pitch_variance': 0.4, 'speed': 1.3},
            'excited': {'intensity': 0.85, 'pitch_variance': 0.35, 'speed': 1.4},
            'calm': {'intensity': 0.4, 'pitch_variance': 0.08, 'speed': 0.9},
            'surprised': {'intensity': 0.7, 'pitch_variance': 0.5, 'speed': 1.1}
        }
        
        # 模型配置
        self.config = {
            'model_type': 'emotional_tacotron',
            'use_gpu': True,
            'emotion_embedding': True,
            'prosody_control': True,
            'intensity_control': True
        }
        
    def load(self) -> bool:
        """加载情感TTS模型"""
        try:
            if not TORCH_AVAILABLE:
                print("❌ PyTorch不可用，无法加载情感TTS模型")
                return False
                
            print("📦 正在加载情感TTS模型...")
            
            # 尝试加载情感TTS模型
            try:
                self._load_mock_model()
                self.is_loaded = True
                print("✅ 情感TTS模型加载成功")
                return True
                
            except Exception as e:
                print(f"❌ 加载情感TTS模型失败: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 初始化情感TTS模型失败: {e}")
            return False
    
    def _load_mock_model(self):
        """加载模拟模型"""
        print("🔧 初始化情感TTS模型组件...")
        time.sleep(1)
        
        # 模拟情感编码器、声学模型、声码器加载
        self.model = {
            "type": "EmotionalTTS",
            "emotion_encoder": "loaded",
            "acoustic_model": "loaded", 
            "vocoder": "loaded"
        }
        
    def synthesize(self, text: str, emotion: str, language: str = 'auto',
                  speed: float = 1.0, intensity: float = None, **kwargs) -> Dict[str, Any]:
        """情感语音合成"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._generate_error_audio("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 验证情感类型
            if emotion not in self.emotions:
                return self._generate_error_audio(f"不支持的情感类型: {emotion}")
                
            # 验证输入文本
            if not text or len(text.strip()) == 0:
                return self._generate_error_audio("输入文本为空")
                
            # 获取情感配置
            emotion_config = self.emotions[emotion].copy()
            if intensity is not None:
                emotion_config['intensity'] = max(0.1, min(1.0, intensity))
                
            # 应用速度控制
            emotion_config['speed'] *= speed
            
            # 文本预处理
            processed_text = self._preprocess_text(text, emotion)
            
            # 生成带情感的语音
            audio_data = self._generate_emotional_speech(processed_text, emotion_config, language)
            
            processing_time = time.time() - start_time
            
            return {
                "audio_data": audio_data,
                "sample_rate": self.sample_rate,
                "success": True,
                "processing_time": processing_time,
                "emotion": emotion,
                "intensity": emotion_config['intensity'],
                "text_length": len(text),
                "language": language
            }
            
        except Exception as e:
            print(f"❌ 情感语音合成失败: {e}")
            return self._generate_error_audio(str(e))
    
    def _preprocess_text(self, text: str, emotion: str) -> str:
        """情感文本预处理"""
        import re
        
        text = text.strip()
        
        # 根据情感调整文本（添加情感词缀等）
        if emotion == 'happy':
            # 对于高兴情感，可以添加感叹词等
            if not text.endswith(('!', '~')):
                text = text + '!'
        elif emotion == 'sad':
            # 对于悲伤情感，语气更平缓
            text = re.sub(r'[!?]', '.', text)
        elif emotion == 'angry':
            # 对于生气情感，加强语气
            if not text.endswith('!'):
                text = text + '!'
                
        return text
    
    def _generate_emotional_speech(self, text: str, emotion_config: dict, language: str) -> np.ndarray:
        """生成带情感的语音"""
        # 实际项目中这里会调用情感TTS模型
        # 这里生成模拟的带情感特征的音频
        
        duration = len(text) * 0.15 / emotion_config['speed']
        t = np.linspace(0, duration, int(duration * self.sample_rate), False)
        
        # 基础频率（根据语言调整）
        if language in ['zh', 'chinese']:
            base_freq = 220  # 中文基频稍低
        else:
            base_freq = 240  # 英文基频稍高
            
        # 根据情感调整基频和变化
        pitch_variance = emotion_config['pitch_variance']
        intensity = emotion_config['intensity']
        
        # 生成动态基频（模拟情感语调变化）
        dynamic_freq = base_freq * (1 + pitch_variance * np.sin(2 * np.pi * 2 * t))
        
        # 生成主音频
        audio = np.sin(2 * np.pi * dynamic_freq * t)
        
        # 添加谐波
        audio += 0.3 * np.sin(2 * np.pi * dynamic_freq * 2 * t)
        audio += 0.2 * np.sin(2 * np.pi * dynamic_freq * 3 * t)
        
        # 根据情感类型添加特定特征
        emotion = [k for k, v in self.emotions.items() if v['pitch_variance'] == emotion_config['pitch_variance']][0]
        
        if emotion == 'happy':
            # 高兴：更明亮的音色，更多高频
            audio += 0.1 * np.sin(2 * np.pi * dynamic_freq * 4 * t)
        elif emotion == 'sad':
            # 悲伤：更暗淡的音色，更多低频
            audio = audio * 0.8 + 0.2 * np.sin(2 * np.pi * dynamic_freq * 0.5 * t)
        elif emotion == 'angry':
            # 生气：更强的攻击性，更多不和谐音
            audio += 0.15 * np.sin(2 * np.pi * dynamic_freq * 2.5 * t)
        elif emotion == 'excited':
            # 兴奋：更快的振动，更多变化
            audio += 0.2 * np.sin(2 * np.pi * dynamic_freq * 5 * t)
            
        # 应用强度控制
        audio = audio * intensity
        
        # 动态包络（模拟语音的自然起伏）
        envelope = self._create_emotional_envelope(t, emotion, emotion_config['speed'])
        audio = audio * envelope
        
        # 归一化
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio)) * 0.8
            
        return audio.astype(np.float32)
    
    def _create_emotional_envelope(self, t: np.ndarray, emotion: str, speed: float) -> np.ndarray:
        """创建情感化包络"""
        envelope = np.ones_like(t)
        
        # 基础包络参数
        attack_time = 0.1 / speed
        release_time = 0.2 / speed
        
        attack_samples = int(attack_time * self.sample_rate)
        release_samples = int(release_time * self.sample_rate)
        
        # 起始包络
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
            
        # 结束包络
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(1, 0, release_samples)
            
        # 根据情感调整包络形状
        if emotion == 'angry':
            # 生气：更尖锐的起始
            envelope[:attack_samples] = np.power(envelope[:attack_samples], 0.5)
        elif emotion == 'sad':
            # 悲伤：更缓慢的衰减
            envelope[-release_samples:] = np.power(envelope[-release_samples:], 1.5)
        elif emotion == 'happy':
            # 高兴：更活泼的起伏
            modulation = 0.1 * np.sin(2 * np.pi * 3 * t)
            envelope = envelope * (1 + modulation)
            envelope = np.clip(envelope, 0, 1)
            
        return envelope
    
    def add_emotion(self, emotion_name: str, parameters: dict) -> bool:
        """添加新的情感类型"""
        if emotion_name in self.emotions:
            return False
            
        self.emotions[emotion_name] = parameters
        return True
    
    def get_supported_emotions(self) -> List[Dict[str, Any]]:
        """获取支持的情感列表"""
        emotions = []
        for name, config in self.emotions.items():
            emotions.append({
                'name': name,
                'intensity_range': (0.1, 1.0),
                'pitch_variance': config['pitch_variance'],
                'speed_multiplier': config['speed']
            })
        return emotions
    
    def analyze_emotion_from_text(self, text: str) -> Dict[str, float]:
        """从文本分析情感倾向"""
        import re
        
        # 简单的情感关键词分析
        emotion_keywords = {
            'happy': ['happy', 'joy', 'great', 'wonderful', 'excellent', 'love', 'amazing'],
            'sad': ['sad', 'sorry', 'unhappy', 'terrible', 'bad', 'hate', 'disappointed'],
            'angry': ['angry', 'mad', 'hate', 'annoying', 'stupid', 'idiot', 'terrible'],
            'excited': ['excited', 'wow', 'awesome', 'fantastic', 'great', 'amazing']
        }
        
        text_lower = text.lower()
        scores = {emotion: 0 for emotion in self.emotions}
        scores['neutral'] = 1.0  # 默认中性
        
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    scores[emotion] += 1
                    scores['neutral'] = max(0, scores['neutral'] - 0.2)
                    
        # 归一化分数
        total = sum(scores.values())
        if total > 0:
            for emotion in scores:
                scores[emotion] /= total
                
        return scores
    
    def _generate_error_audio(self, error_msg: str) -> Dict[str, Any]:
        """生成错误音频"""
        duration = 1.0
        t = np.linspace(0, duration, int(duration * self.sample_rate), False)
        
        # 生成表示错误的音频（快速交替）
        freq1, freq2 = 392, 294  # G4到D4
        audio = 0.3 * np.sin(2 * np.pi * freq1 * t)
        audio += 0.3 * np.sin(2 * np.pi * freq2 * t)
        
        # 添加振幅调制
        am = 0.5 * (1 + np.sin(2 * np.pi * 5 * t))
        audio = audio * am
        
        return {
            "audio_data": audio.astype(np.float32),
            "sample_rate": self.sample_rate,
            "success": False,
            "error": error_msg
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "is_loaded": self.is_loaded,
            "supported_emotions": list(self.emotions.keys()),
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded
