"""
音乐生成器：基于文本描述生成音乐和音频
支持多种音乐风格和乐器
"""

import os
import json
import logging
import base64
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from io import BytesIO
from enum import Enum

import torch
import numpy as np
from pydantic import BaseModel

# 尝试导入音乐生成相关库
try:
    import pretty_midi
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    logger.warning("pretty_midi not available, MIDI generation will be limited")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa not available, audio analysis will be limited")

logger = logging.getLogger(__name__)

class MusicGenre(Enum):
    """音乐流派枚举"""
    CLASSICAL = "classical"
    JAZZ = "jazz"
    ROCK = "rock"
    POP = "pop"
    ELECTRONIC = "electronic"
    AMBIENT = "ambient"
    FOLK = "folk"

class InstrumentType(Enum):
    """乐器类型枚举"""
    PIANO = "piano"
    GUITAR = "guitar"
    VIOLIN = "violin"
    DRUMS = "drums"
    BASS = "bass"
    SYNTH = "synth"
    ORCHESTRA = "orchestra"

class MusicConfig(BaseModel):
    """音乐生成配置"""
    description: str
    genre: MusicGenre = MusicGenre.CLASSICAL
    instruments: List[InstrumentType] = [InstrumentType.PIANO]
    duration: float = 30.0  # 秒
    tempo: int = 120  # BPM
    key: str = "C"  # 调性
    complexity: str = "medium"  # simple, medium, complex

class GeneratedMusic(BaseModel):
    """生成的音乐"""
    audio_data: str  # base64编码的音频数据
    midi_data: Optional[str] = None  # base64编码的MIDI数据
    metadata: Dict[str, Any]
    duration: float

class MusicGenerator:
    """音乐生成器"""
    
    def __init__(self, model_name: str = "facebook/musicgen-small"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.music_gen_pipeline = None
        self.midi_generator = None
        
        # 音乐理论配置
        self.music_theory = self._load_music_theory()
        
        # 乐器映射
        self.instrument_programs = self._load_instrument_programs()
        
        logger.info(f"MusicGenerator initialized with device: {self.device}")
    
    def _load_music_theory(self) -> Dict:
        """加载音乐理论配置"""
        return {
            "scales": {
                "major": [0, 2, 4, 5, 7, 9, 11],
                "minor": [0, 2, 3, 5, 7, 8, 10],
                "pentatonic": [0, 2, 4, 7, 9]
            },
            "chords": {
                "major": [0, 4, 7],
                "minor": [0, 3, 7],
                "seventh": [0, 4, 7, 10]
            },
            "progressions": {
                "pop": ["I", "V", "vi", "IV"],
                "jazz": ["ii", "V", "I"],
                "classical": ["I", "IV", "V", "I"]
            }
        }
    
    def _load_instrument_programs(self) -> Dict[InstrumentType, int]:
        """加载乐器程序号映射"""
        return {
            InstrumentType.PIANO: 0,
            InstrumentType.GUITAR: 24,
            InstrumentType.VIOLIN: 40,
            InstrumentType.DRUMS: 118,  # 打击乐通道
            InstrumentType.BASS: 32,
            InstrumentType.SYNTH: 80,
            InstrumentType.ORCHESTRA: 48
        }
    
    def load_models(self):
        """加载音乐生成模型"""
        try:
            # 尝试加载MusicGen模型
            try:
                from transformers import MusicgenForConditionalGeneration, AutoProcessor
                
                logger.info(f"Loading music generation model: {self.model_name}")
                
                self.processor = AutoProcessor.from_pretrained(self.model_name)
                self.music_gen_model = MusicgenForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
                )
                
                if self.device == "cuda":
                    self.music_gen_model = self.music_gen_model.to("cuda")
                
                self.music_gen_loaded = True
                logger.info("MusicGen model loaded successfully")
                
            except ImportError:
                logger.warning("MusicGen not available, using rule-based generation")
                self.music_gen_loaded = False
                
        except Exception as e:
            logger.error(f"Failed to load music generation models: {e}")
            self.music_gen_loaded = False
    
    def generate_music(self, config: MusicConfig) -> GeneratedMusic:
        """
        生成音乐
        
        Args:
            config: 音乐生成配置
            
        Returns:
            GeneratedMusic: 生成的音乐
        """
        try:
            # 尝试使用AI模型生成
            if self.music_gen_loaded and self.music_gen_model is not None:
                return self._generate_with_ai_model(config)
            else:
                # 使用基于规则的生成
                return self._generate_with_rules(config)
                
        except Exception as e:
            logger.error(f"Failed to generate music: {e}")
            # 返回简单的占位音乐
            return self._generate_placeholder_music(config)
    
    def _generate_with_ai_model(self, config: MusicConfig) -> GeneratedMusic:
        """使用AI模型生成音乐"""
        try:
            # 构建提示词
            prompt = self._build_music_prompt(config)
            
            # 预处理输入
            inputs = self.processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            )
            
            if self.device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # 生成音频
            with torch.autocast("cuda" if self.device == "cuda" else "cpu"):
                audio_values = self.music_gen_model.generate(
                    **inputs,
                    do_sample=True,
                    guidance_scale=3,
                    max_new_tokens=1024,
                )
            
            # 转换为numpy数组
            audio_array = audio_values[0, 0].cpu().numpy()
            
            # 生成MIDI数据（可选）
            midi_data = self._generate_midi_from_audio(audio_array, config)
            
            # 编码音频数据
            audio_base64 = self._encode_audio_data(audio_array)
            midi_base64 = self._encode_midi_data(midi_data) if midi_data else None
            
            return GeneratedMusic(
                audio_data=audio_base64,
                midi_data=midi_base64,
                metadata={
                    "model": self.model_name,
                    "genre": config.genre.value,
                    "instruments": [inst.value for inst in config.instruments],
                    "tempo": config.tempo,
                    "key": config.key,
                    "duration": config.duration,
                    "generated_at": datetime.now().isoformat()
                },
                duration=config.duration
            )
            
        except Exception as e:
            logger.error(f"AI music generation failed, falling back to rule-based: {e}")
            return self._generate_with_rules(config)
    
    def _build_music_prompt(self, config: MusicConfig) -> str:
        """构建音乐生成提示词"""
        instruments = ", ".join([inst.value for inst in config.instruments])
        
        prompt = f"""
        {config.description}
        Genre: {config.genre.value}
        Instruments: {instruments}
        Tempo: {config.tempo} BPM
        Key: {config.key}
        Duration: {config.duration} seconds
        Complexity: {config.complexity}
        """
        
        return prompt.strip()
    
    def _generate_with_rules(self, config: MusicConfig) -> GeneratedMusic:
        """使用基于规则的生成"""
        try:
            if not MIDI_AVAILABLE:
                return self._generate_placeholder_music(config)
            
            # 创建MIDI对象
            midi = pretty_midi.PrettyMIDI()
            midi.resolution = 480  # ticks per quarter note
            
            # 为每个乐器创建轨道
            for instrument_type in config.instruments:
                if instrument_type == InstrumentType.DRUMS:
                    # 打击乐使用通道10
                    instrument = pretty_midi.Instrument(program=0, is_drum=True)
                else:
                    program = self.instrument_programs.get(instrument_type, 0)
                    instrument = pretty_midi.Instrument(program=program)
                
                # 生成音符
                notes = self._generate_notes_for_instrument(instrument_type, config)
                instrument.notes.extend(notes)
                
                midi.instruments.append(instrument)
            
            # 合成音频
            audio_data = midi.synthesize(fs=22050)
            
            # 确保音频长度正确
            target_samples = int(config.duration * 22050)
            if len(audio_data) > target_samples:
                audio_data = audio_data[:target_samples]
            else:
                # 如果太短，填充静音
                padding = np.zeros(target_samples - len(audio_data))
                audio_data = np.concatenate([audio_data, padding])
            
            # 编码数据
            audio_base64 = self._encode_audio_data(audio_data)
            midi_base64 = self._encode_midi_data(midi)
            
            return GeneratedMusic(
                audio_data=audio_base64,
                midi_data=midi_base64,
                metadata={
                    "model": "rule_based",
                    "genre": config.genre.value,
                    "instruments": [inst.value for inst in config.instruments],
                    "tempo": config.tempo,
                    "key": config.key,
                    "duration": config.duration,
                    "generated_at": datetime.now().isoformat()
                },
                duration=config.duration
            )
            
        except Exception as e:
            logger.error(f"Rule-based music generation failed: {e}")
            return self._generate_placeholder_music(config)
    
    def _generate_notes_for_instrument(self, 
                                     instrument: InstrumentType, 
                                     config: MusicConfig) -> List:
        """为乐器生成音符"""
        notes = []
        tempo = config.tempo
        duration = config.duration
        beats_per_second = tempo / 60.0
        total_beats = duration * beats_per_second
        
        # 根据乐器类型生成不同的音符模式
        if instrument == InstrumentType.PIANO:
            notes = self._generate_piano_notes(config, total_beats)
        elif instrument == InstrumentType.GUITAR:
            notes = self._generate_guitar_notes(config, total_beats)
        elif instrument == InstrumentType.DRUMS:
            notes = self._generate_drum_notes(config, total_beats)
        elif instrument == InstrumentType.BASS:
            notes = self._generate_bass_notes(config, total_beats)
        else:
            notes = self._generate_melody_notes(config, total_beats)
        
        return notes
    
    def _generate_piano_notes(self, config: MusicConfig, total_beats: float) -> List:
        """生成钢琴音符"""
        notes = []
        scale = self.music_theory["scales"]["major"]  # 简化使用大调音阶
        base_note = 60  # C4
        
        beat_duration = 0.5  # 每拍持续时间（秒）
        current_time = 0.0
        
        while current_time < config.duration:
            # 随机选择音阶中的音符
            note_pitch = base_note + np.random.choice(scale)
            velocity = np.random.randint(60, 100)
            
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=note_pitch,
                start=current_time,
                end=current_time + beat_duration
            )
            notes.append(note)
            
            current_time += beat_duration
        
        return notes
    
    def _generate_drum_notes(self, config: MusicConfig, total_beats: float) -> List:
        """生成鼓点音符"""
        notes = []
        
        # 简单的鼓点模式
        drum_pattern = [
            (36, 1.0),  # 底鼓在第一拍
            (42, 0.5),  # 踩镲在每半拍
            (42, 1.5),
            (38, 2.0),  # 军鼓在第三拍
            (42, 2.5),
            (42, 3.5)
        ]
        
        beat_duration = 60.0 / config.tempo
        pattern_duration = 4.0 * beat_duration  # 4拍一个模式
        
        current_time = 0.0
        while current_time < config.duration:
            for drum_note, beat_position in drum_pattern:
                note_time = current_time + beat_position * beat_duration
                if note_time < config.duration:
                    note = pretty_midi.Note(
                        velocity=80,
                        pitch=drum_note,
                        start=note_time,
                        end=note_time + 0.1
                    )
                    notes.append(note)
            
            current_time += pattern_duration
        
        return notes
    
    def _generate_guitar_notes(self, config: MusicConfig, total_beats: float) -> List:
        """生成吉他音符"""
        return self._generate_chord_notes(config, total_beats, base_note=40)
    
    def _generate_bass_notes(self, config: MusicConfig, total_beats: float) -> List:
        """生成贝斯音符"""
        notes = []
        base_note = 36  # C2
        beat_duration = 1.0  # 每拍
        
        current_time = 0.0
        while current_time < config.duration:
            note_pitch = base_note
            velocity = 90
            
            note = pretty_midi.Note(
                velocity=velocity,
                pitch=note_pitch,
                start=current_time,
                end=current_time + beat_duration * 0.9
            )
            notes.append(note)
            
            current_time += beat_duration
        
        return notes
    
    def _generate_melody_notes(self, config: MusicConfig, total_beats: float) -> List:
        """生成旋律音符"""
        return self._generate_piano_notes(config, total_beats)
    
    def _generate_chord_notes(self, config: MusicConfig, total_beats: float, base_note: int) -> List:
        """生成和弦音符"""
        notes = []
        chord = self.music_theory["chords"]["major"]
        beat_duration = 2.0  # 每和弦持续2拍
        
        current_time = 0.0
        while current_time < config.duration:
            for interval in chord:
                note_pitch = base_note + interval
                velocity = 70
                
                note = pretty_midi.Note(
                    velocity=velocity,
                    pitch=note_pitch,
                    start=current_time,
                    end=current_time + beat_duration * 0.9
                )
                notes.append(note)
            
            current_time += beat_duration
        
        return notes
    
    def _generate_midi_from_audio(self, audio_array: np.ndarray, config: MusicConfig):
        """从音频生成MIDI数据（简化实现）"""
        if not MIDI_AVAILABLE:
            return None
        
        try:
            # 创建简单的MIDI结构
            midi = pretty_midi.PrettyMIDI()
            instrument = pretty_midi.Instrument(program=0)  # 钢琴
            
            # 基于音频振幅生成简单音符（非常简化的实现）
            hop_length = 512
            frame_duration = hop_length / 22050.0
            
            for i in range(0, len(audio_array), hop_length):
                frame = audio_array[i:i+hop_length]
                if len(frame) == 0:
                    continue
                
                # 计算帧的RMS能量
                rms = np.sqrt(np.mean(frame**2))
                
                if rms > 0.01:  # 能量阈值
                    # 简单的音高映射（实际应该使用音高检测）
                    pitch = 60 + int(rms * 24)  # C4到C6的范围
                    pitch = max(0, min(127, pitch))
                    
                    note = pretty_midi.Note(
                        velocity=int(rms * 100),
                        pitch=pitch,
                        start=i * frame_duration,
                        end=(i + hop_length) * frame_duration
                    )
                    instrument.notes.append(note)
            
            midi.instruments.append(instrument)
            return midi
            
        except Exception as e:
            logger.warning(f"MIDI generation from audio failed: {e}")
            return None
    
    def _encode_audio_data(self, audio_array: np.ndarray) -> str:
        """编码音频数据为base64"""
        try:
            # 将音频数据归一化到16位PCM范围
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # 使用wave模块创建WAV文件
            import wave
            import struct
            
            buffered = BytesIO()
            with wave.open(buffered, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(22050)  # 采样率
                
                # 将数据打包为字节
                frames = struct.pack('<' + 'h' * len(audio_int16), *audio_int16)
                wav_file.writeframes(frames)
            
            return base64.b64encode(buffered.getvalue()).decode()
            
        except Exception as e:
            logger.error(f"Failed to encode audio data: {e}")
            # 返回空的音频数据
            return ""
    
    def _encode_midi_data(self, midi) -> str:
        """编码MIDI数据为base64"""
        try:
            buffered = BytesIO()
            midi.write(buffered)
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            logger.error(f"Failed to encode MIDI data: {e}")
            return None
    
    def _generate_placeholder_music(self, config: MusicConfig) -> GeneratedMusic:
        """生成占位音乐"""
        try:
            # 生成简单的正弦波作为占位
            duration = config.duration
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # 生成基于配置的简单旋律
            base_freq = 440.0  # A4
            melody = np.sin(2 * np.pi * base_freq * t)
            
            # 添加一些和声
            harmony = 0.3 * np.sin(2 * np.pi * base_freq * 1.5 * t)
            audio_data = melody + harmony
            
            # 归一化
            audio_data = audio_data / np.max(np.abs(audio_data))
            
            audio_base64 = self._encode_audio_data(audio_data)
            
            return GeneratedMusic(
                audio_data=audio_base64,
                midi_data=None,
                metadata={
                    "model": "placeholder",
                    "genre": config.genre.value,
                    "instruments": [inst.value for inst in config.instruments],
                    "tempo": config.tempo,
                    "key": config.key,
                    "duration": config.duration,
                    "note": "Real model not available, using placeholder",
                    "generated_at": datetime.now().isoformat()
                },
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Failed to generate placeholder music: {e}")
            # 返回空的音乐数据
            return GeneratedMusic(
                audio_data="",
                midi_data=None,
                metadata={"error": str(e)},
                duration=0.0
            )

# 单例实例
_music_generator_instance = None

def get_music_generator() -> MusicGenerator:
    """获取音乐生成器单例"""
    global _music_generator_instance
    if _music_generator_instance is None:
        _music_generator_instance = MusicGenerator()
    return _music_generator_instance

