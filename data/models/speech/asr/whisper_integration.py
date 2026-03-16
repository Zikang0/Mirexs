"""
Whisper集成 - OpenAI Whisper模型集成
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import time

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

class WhisperIntegration:
    """OpenAI Whisper模型集成"""
    
    def __init__(self, model_size: str = "base"):
        self.model_name = f"Whisper-{model_size}"
        self.language = "multilingual"
        self.version = "1.0.0"
        self.sample_rate = 16000
        self.model = None
        self.model_size = model_size
        self.is_loaded = False
        
        # Whisper支持的语言代码映射
        self.language_codes = {
            'en': 'english', 'zh': 'chinese', 'de': 'german', 'es': 'spanish',
            'ru': 'russian', 'ko': 'korean', 'fr': 'french', 'ja': 'japanese',
            'pt': 'portuguese', 'tr': 'turkish', 'pl': 'polish', 'ca': 'catalan',
            'nl': 'dutch', 'ar': 'arabic', 'sv': 'swedish', 'it': 'italian',
            'id': 'indonesian', 'hi': 'hindi', 'fi': 'finnish', 'vi': 'vietnamese',
            'he': 'hebrew', 'uk': 'ukrainian', 'el': 'greek', 'ms': 'malay',
            'cs': 'czech', 'ro': 'romanian', 'da': 'danish', 'hu': 'hungarian',
            'ta': 'tamil', 'no': 'norwegian', 'th': 'thai', 'ur': 'urdu',
            'hr': 'croatian', 'bg': 'bulgarian', 'lt': 'lithuanian', 'la': 'latin',
            'mi': 'maori', 'ml': 'malayalam', 'cy': 'welsh', 'sk': 'slovak',
            'te': 'telugu', 'fa': 'persian', 'lv': 'latvian', 'bn': 'bengali',
            'sr': 'serbian', 'az': 'azerbaijani', 'sl': 'slovenian', 'kn': 'kannada',
            'et': 'estonian', 'mk': 'macedonian', 'br': 'breton', 'eu': 'basque',
            'is': 'icelandic', 'hy': 'armenian', 'ne': 'nepali', 'mn': 'mongolian',
            'bs': 'bosnian', 'kk': 'kazakh', 'sq': 'albanian', 'sw': 'swahili',
            'gl': 'galician', 'mr': 'marathi', 'pa': 'punjabi', 'si': 'sinhala',
            'km': 'khmer', 'sn': 'shona', 'yo': 'yoruba', 'so': 'somali',
            'af': 'afrikaans', 'oc': 'occitan', 'ka': 'georgian', 'be': 'belarusian',
            'tg': 'tajik', 'sd': 'sindhi', 'gu': 'gujarati', 'am': 'amharic',
            'yi': 'yiddish', 'lo': 'lao', 'uz': 'uzbek', 'fo': 'faroese',
            'ht': 'haitian creole', 'ps': 'pashto', 'tk': 'turkmen', 'nn': 'nynorsk',
            'mt': 'maltese', 'sa': 'sanskrit', 'lb': 'luxembourgish', 'my': 'myanmar',
            'bo': 'tibetan', 'tl': 'tagalog', 'mg': 'malagasy', 'as': 'assamese',
            'tt': 'tatar', 'haw': 'hawaiian', 'ln': 'lingala', 'ha': 'hausa',
            'ba': 'bashkir', 'jw': 'javanese', 'su': 'sundanese'
        }
        
        # 模型配置
        self.config = {
            'model_size': model_size,
            'use_gpu': True,
            'task': 'transcribe',  # transcribe 或 translate
            'temperature': 0.0,
            'best_of': 5,
            'beam_size': 5,
            'without_timestamps': True,
            'fp16': True  # 使用半精度浮点数
        }
        
    def load(self) -> bool:
        """加载Whisper模型"""
        try:
            if not WHISPER_AVAILABLE:
                print("❌ Whisper库不可用，请安装: pip install openai-whisper")
                return False
            
            print(f"📦 正在加载Whisper模型 ({self.model_size})...")
            self.model = whisper.load_model(self.model_size)
            self.is_loaded = True
            print(f"✅ Whisper模型加载成功: {self.model_size}")
            return True
            
        except Exception as e:
            print(f"❌ 加载Whisper模型失败: {e}")
            return False
    
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000,
                  language: Optional[str] = None, task: str = "transcribe") -> Dict[str, Any]:
        """使用Whisper进行语音识别"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"text": "", "confidence": 0.0, "success": False}
        
        try:
            start_time = time.time()
            
            # 保存临时音频文件（Whisper需要文件路径）
            temp_audio_path = self._save_temp_audio(audio_data, sample_rate)
            
            if not temp_audio_path:
                return {"text": "", "confidence": 0.0, "success": False}
            
            # 准备选项
            options = {
                'task': task,
                'temperature': self.config['temperature'],
                'best_of': self.config['best_of'],
                'beam_size': self.config['beam_size'],
                'fp16': self.config['fp16']
            }
            
            # 设置语言（如果指定）
            if language and language in self.language_codes:
                options['language'] = language
            
            # 进行语音识别
            result = self.model.transcribe(temp_audio_path, **options)
            
            # 清理临时文件
            self._cleanup_temp_file(temp_audio_path)
            
            processing_time = time.time() - start_time
            
            return {
                "text": result["text"],
                "confidence": self._calculate_whisper_confidence(result),
                "success": True,
                "processing_time": processing_time,
                "language": result.get("language", "unknown"),
                "task": task,
                "segments": result.get("segments", [])
            }
            
        except Exception as e:
            print(f"❌ Whisper语音识别失败: {e}")
            # 清理临时文件
            if 'temp_audio_path' in locals():
                self._cleanup_temp_file(temp_audio_path)
            return {"text": "", "confidence": 0.0, "success": False, "error": str(e)}
    
    def translate(self, audio_data: np.ndarray, sample_rate: int = 16000,
                 target_language: str = "en") -> Dict[str, Any]:
        """语音翻译（翻译为英文）"""
        return self.transcribe(audio_data, sample_rate, task="translate")
    
    def _save_temp_audio(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """保存临时音频文件"""
        try:
            import tempfile
            import soundfile as sf
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"whisper_temp_{int(time.time())}.wav")
            
            # 确保音频数据是单声道
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # 保存为WAV文件
            sf.write(temp_path, audio_data, sample_rate)
            
            return temp_path
            
        except Exception as e:
            print(f"❌ 保存临时音频文件失败: {e}")
            return None
    
    def _cleanup_temp_file(self, file_path: str) -> None:
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {e}")
    
    def _calculate_whisper_confidence(self, result: Dict[str, Any]) -> float:
        """计算Whisper识别置信度"""
        try:
            segments = result.get("segments", [])
            if not segments:
                return 0.5
            
            # 计算所有segment的平均置信度
            total_confidence = 0.0
            segment_count = 0
            
            for segment in segments:
                if 'confidence' in segment:
                    total_confidence += segment['confidence']
                    segment_count += 1
            
            if segment_count > 0:
                return total_confidence / segment_count
            else:
                # 如果没有置信度信息，使用简单的启发式方法
                text = result.get("text", "").strip()
                if len(text) > 10:
                    return 0.7
                else:
                    return 0.3
                    
        except Exception:
            return 0.5
    
    def get_supported_languages(self) -> Dict[str, str]:
        """获取Whisper支持的语言"""
        return self.language_codes
    
    def detect_language(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """检测音频语言"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"language": "unknown", "confidence": 0.0, "success": False}
        
        try:
            # 保存临时音频文件
            temp_audio_path = self._save_temp_audio(audio_data, sample_rate)
            if not temp_audio_path:
                return {"language": "unknown", "confidence": 0.0, "success": False}
            
            # 加载音频并修剪（为了快速检测）
            audio = whisper.load_audio(temp_audio_path)
            audio = whisper.pad_or_trim(audio)
            
            # 制作log-Mel频谱图
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            
            # 检测语言
            _, probs = self.model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            confidence = probs[detected_language]
            
            # 清理临时文件
            self._cleanup_temp_file(temp_audio_path)
            
            return {
                "language": detected_language,
                "language_name": self.language_codes.get(detected_language, "Unknown"),
                "confidence": float(confidence),
                "success": True
            }
            
        except Exception as e:
            print(f"❌ 语言检测失败: {e}")
            if 'temp_audio_path' in locals():
                self._cleanup_temp_file(temp_audio_path)
            return {"language": "unknown", "confidence": 0.0, "success": False}
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "language": self.language,
            "version": self.version,
            "sample_rate": self.sample_rate,
            "model_size": self.model_size,
            "is_loaded": self.is_loaded,
            "supported_languages_count": len(self.language_codes),
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded