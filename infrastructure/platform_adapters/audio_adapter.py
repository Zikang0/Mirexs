"""
音频适配器 - 跨平台音频处理
"""

import os
import sys
import platform
from typing import Dict, Any, List, Optional

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

class AudioAdapter:
    """跨平台音频处理适配器"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.audio_backend = self._select_audio_backend()
        self.initialized = False
        self.audio_stream = None
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化音频适配器"""
        self.hardware_info = hardware_info
        self.audio_info = self._get_audio_info()
        self.initialized = True
        
    def _select_audio_backend(self) -> str:
        """选择音频后端"""
        if PYAUDIO_AVAILABLE:
            return "pyaudio"
        elif SOUNDDEVICE_AVAILABLE:
            return "sounddevice"
        else:
            return "none"
    
    def _get_audio_info(self) -> Dict[str, Any]:
        """获取音频设备信息"""
        info = {
            'backend': self.audio_backend,
            'input_devices': [],
            'output_devices': [],
            'default_input': None,
            'default_output': None
        }
        
        try:
            if self.audio_backend == "pyaudio":
                audio = pyaudio.PyAudio()
                
                # 获取输入设备
                for i in range(audio.get_device_count()):
                    device_info = audio.get_device_info_by_index(i)
                    if device_info.get('maxInputChannels', 0) > 0:
                        info['input_devices'].append({
                            'id': i,
                            'name': device_info.get('name', 'Unknown'),
                            'channels': device_info.get('maxInputChannels', 1),
                            'sample_rate': device_info.get('defaultSampleRate', 44100)
                        })
                    
                    if device_info.get('maxOutputChannels', 0) > 0:
                        info['output_devices'].append({
                            'id': i,
                            'name': device_info.get('name', 'Unknown'),
                            'channels': device_info.get('maxOutputChannels', 2),
                            'sample_rate': device_info.get('defaultSampleRate', 44100)
                        })
                
                # 获取默认设备
                try:
                    default_input = audio.get_default_input_device_info()
                    info['default_input'] = default_input.get('index', 0)
                except:
                    pass
                    
                try:
                    default_output = audio.get_default_output_device_info()
                    info['default_output'] = default_output.get('index', 0)
                except:
                    pass
                
                audio.terminate()
                
            elif self.audio_backend == "sounddevice":
                devices = sd.query_devices()
                hostapis = sd.query_hostapis()
                
                for i, device in enumerate(devices):
                    if device.get('max_input_channels', 0) > 0:
                        info['input_devices'].append({
                            'id': i,
                            'name': device.get('name', 'Unknown'),
                            'channels': device.get('max_input_channels', 1),
                            'sample_rate': device.get('default_samplerate', 44100)
                        })
                    
                    if device.get('max_output_channels', 0) > 0:
                        info['output_devices'].append({
                            'id': i,
                            'name': device.get('name', 'Unknown'),
                            'channels': device.get('max_output_channels', 2),
                            'sample_rate': device.get('default_samplerate', 44100)
                        })
                
                # 获取默认设备
                info['default_input'] = sd.default.device[0] if sd.default.device else 0
                info['default_output'] = sd.default.device[1] if sd.default.device else 0
                
        except Exception as e:
            print(f"⚠️ 获取音频设备信息失败: {e}")
            
        return info
    
    def record_audio(self, duration: float = 5.0, sample_rate: int = 16000, 
                    channels: int = 1, device_index: Optional[int] = None) -> Optional[bytes]:
        """录制音频"""
        if self.audio_backend == "none":
            print("❌ 没有可用的音频后端")
            return None
            
        try:
            if self.audio_backend == "pyaudio":
                return self._record_with_pyaudio(duration, sample_rate, channels, device_index)
            elif self.audio_backend == "sounddevice":
                return self._record_with_sounddevice(duration, sample_rate, channels, device_index)
        except Exception as e:
            print(f"❌ 录制音频失败: {e}")
            return None
    
    def _record_with_pyaudio(self, duration: float, sample_rate: int, 
                           channels: int, device_index: Optional[int]) -> bytes:
        """使用PyAudio录制音频"""
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        frames = []
        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        return b''.join(frames)
    
    def _record_with_sounddevice(self, duration: float, sample_rate: int,
                               channels: int, device_index: Optional[int]) -> bytes:
        """使用sounddevice录制音频"""
        import numpy as np
        
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            device=device_index,
            dtype='int16'
        )
        sd.wait()
        
        return recording.tobytes()
    
    def play_audio(self, audio_data: bytes, sample_rate: int = 22050, 
                  channels: int = 2, device_index: Optional[int] = None) -> bool:
        """播放音频"""
        if self.audio_backend == "none":
            print("❌ 没有可用的音频后端")
            return False
            
        try:
            if self.audio_backend == "pyaudio":
                return self._play_with_pyaudio(audio_data, sample_rate, channels, device_index)
            elif self.audio_backend == "sounddevice":
                return self._play_with_sounddevice(audio_data, sample_rate, channels, device_index)
        except Exception as e:
            print(f"❌ 播放音频失败: {e}")
            return False
    
    def _play_with_pyaudio(self, audio_data: bytes, sample_rate: int,
                          channels: int, device_index: Optional[int]) -> bool:
        """使用PyAudio播放音频"""
        audio = pyaudio.PyAudio()
        
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=device_index
        )
        
        stream.write(audio_data)
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        return True
    
    def _play_with_sounddevice(self, audio_data: bytes, sample_rate: int,
                              channels: int, device_index: Optional[int]) -> bool:
        """使用sounddevice播放音频"""
        import numpy as np
        
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        audio_array = audio_array.reshape(-1, channels)
        
        sd.play(audio_array, samplerate=sample_rate, device=device_index)
        sd.wait()
        
        return True
    
    def get_audio_level(self, duration: float = 0.1) -> float:
        """获取当前音频输入电平"""
        if self.audio_backend == "none":
            return 0.0
            
        try:
            if self.audio_backend == "pyaudio":
                return self._get_level_with_pyaudio(duration)
            elif self.audio_backend == "sounddevice":
                return self._get_level_with_sounddevice(duration)
        except Exception as e:
            print(f"⚠️ 获取音频电平失败: {e}")
            return 0.0
    
    def _get_level_with_pyaudio(self, duration: float) -> float:
        """使用PyAudio获取音频电平"""
        import numpy as np
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
        data = stream.read(1024)
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        audio_data = np.frombuffer(data, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_data**2))
        
        # 标准化到0-1范围
        level = min(rms / 32768.0, 1.0)
        return level
    
    def _get_level_with_sounddevice(self, duration: float) -> float:
        """使用sounddevice获取音频电平"""
        import numpy as np
        
        recording = sd.rec(int(16000 * duration), samplerate=16000, channels=1, dtype='int16')
        sd.wait()
        
        rms = np.sqrt(np.mean(recording**2))
        level = min(rms / 32768.0, 1.0)
        return level
    
    def set_audio_parameters(self, sample_rate: int = 44100, 
                           channels: int = 2, chunk_size: int = 1024) -> None:
        """设置音频参数"""
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的音频格式"""
        formats = ['wav', 'mp3', 'flac', 'ogg']
        
        # 根据平台添加特定格式
        if self.platform == "windows":
            formats.extend(['wma', 'aac'])
        elif self.platform == "darwin":  # macOS
            formats.extend(['aac', 'caf'])
            
        return formats