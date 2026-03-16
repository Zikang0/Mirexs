"""
唤醒词模块 - 语音唤醒和语音活动检测

包含唤醒词检测、语音活动检测、说话人验证等功能
"""

from .wake_word_model import WakeWordModel
from .voice_activity import VoiceActivityDetector
from .speaker_verification import SpeakerVerification
from .audio_preprocessor import AudioPreprocessor

__all__ = [
    "WakeWordModel",
    "VoiceActivityDetector", 
    "SpeakerVerification",
    "AudioPreprocessor"
]

class WakeWordSystem:
    """唤醒词系统管理器"""
    
    def __init__(self):
        self.wake_word_model = None
        self.vad = None
        self.speaker_verification = None
        self.audio_preprocessor = None
        self.initialized = False
        
    def initialize(self, wake_word: str = "小猫咪", sensitivity: float = 0.5):
        """初始化唤醒词系统"""
        # 初始化组件
        self.audio_preprocessor = AudioPreprocessor()
        self.wake_word_model = WakeWordModel(wake_word, sensitivity)
        self.vad = VoiceActivityDetector()
        self.speaker_verification = SpeakerVerification()
        
        # 加载模型
        self.wake_word_model.load()
        self.vad.load()
        self.speaker_verification.load()
        
        self.initialized = True
        print("✅ 唤醒词系统初始化完成")
        
    def process_audio_chunk(self, audio_chunk: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """处理音频块"""
        if not self.initialized:
            self.initialize()
            
        try:
            # 音频预处理
            processed_audio = self.audio_preprocessor.process(audio_chunk, sample_rate)
            
            # 语音活动检测
            vad_result = self.vad.detect(processed_audio)
            
            result = {
                "vad_detected": vad_result["speech_detected"],
                "vad_confidence": vad_result["confidence"],
                "wake_word_detected": False,
                "wake_word_confidence": 0.0,
                "speaker_verified": False,
                "speaker_confidence": 0.0
            }
            
            # 如果有语音活动，检测唤醒词
            if vad_result["speech_detected"]:
                wake_result = self.wake_word_model.detect(processed_audio)
                result["wake_word_detected"] = wake_result["detected"]
                result["wake_word_confidence"] = wake_result["confidence"]
                
                # 如果检测到唤醒词，进行说话人验证
                if wake_result["detected"]:
                    speaker_result = self.speaker_verification.verify(processed_audio)
                    result["speaker_verified"] = speaker_result["verified"]
                    result["speaker_confidence"] = speaker_result["confidence"]
                    
            return result
            
        except Exception as e:
            print(f"❌ 唤醒词处理失败: {e}")
            return {
                "vad_detected": False,
                "wake_word_detected": False, 
                "speaker_verified": False,
                "error": str(e)
            }
    
    def register_speaker(self, audio_data: np.ndarray, sample_rate: int, 
                        speaker_id: str) -> bool:
        """注册说话人"""
        if not self.initialized:
            self.initialize()
            
        return self.speaker_verification.register(audio_data, sample_rate, speaker_id)
    
    def set_wake_word(self, wake_word: str, sensitivity: float = 0.5):
        """设置唤醒词"""
        if self.wake_word_model:
            self.wake_word_model.set_wake_word(wake_word, sensitivity)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "initialized": self.initialized,
            "wake_word_loaded": self.wake_word_model.is_loaded() if self.wake_word_model else False,
            "vad_loaded": self.vad.is_loaded() if self.vad else False,
            "speaker_verification_loaded": self.speaker_verification.is_loaded() if self.speaker_verification else False,
            "current_wake_word": self.wake_word_model.get_wake_word() if self.wake_word_model else "Unknown"
        }