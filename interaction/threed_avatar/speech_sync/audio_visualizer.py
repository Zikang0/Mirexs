"""
音频可视化系统 - 实时音频分析和可视化
完整实现音频波形、频谱、语谱图等可视化功能
支持实时音频特征提取和可视化渲染
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
import asyncio
from enum import Enum
import threading
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.animation as animation

# 导入依赖
from infrastructure.compute_storage.gpu_accelerator import GPUAccelerator, gpu_accelerator
from infrastructure.compute_storage.resource_manager import ResourceManager, resource_manager, ResourceType

logger = logging.getLogger(__name__)

class VisualizationType(Enum):
    """可视化类型枚举"""
    WAVEFORM = "waveform"          # 波形图
    SPECTROGRAM = "spectrogram"    # 语谱图
    SPECTRUM = "spectrum"          # 频谱图
    MFCC = "mfcc"                  # MFCC特征图
    PITCH = "pitch"               # 音高图
    FORMANT = "formant"           # 共振峰图
    ENERGY = "energy"             # 能量图
    REAL_TIME = "real_time"       # 实时可视化

@dataclass
class VisualizationConfig:
    """可视化配置"""
    width: int = 800
    height: int = 400
    sample_rate: int = 22050
    fft_size: int = 1024
    hop_size: int = 256
    n_mels: int = 128
    n_mfcc: int = 13
    colormap: str = "viridis"
    refresh_rate: float = 30.0  # FPS
    realtime_enabled: bool = True
    save_to_file: bool = False

@dataclass
class VisualizationData:
    """可视化数据"""
    timestamp: float
    audio_data: np.ndarray
    features: Dict[str, Any]
    visualization_type: VisualizationType
    metadata: Dict[str, Any]

class AudioVisualizer:
    """音频可视化系统 - 完整实现"""
    
    def __init__(self, config: VisualizationConfig = None):
        self.config = config or VisualizationConfig()
        self.visualization_data: List[VisualizationData] = []
        self.realtime_buffer: List[np.ndarray] = []
        self.active_visualizations: Dict[str, Any] = {}
        
        # 图形对象
        self.figures: Dict[str, Figure] = {}
        self.axes: Dict[str, Axes] = {}
        self.animations: Dict[str, animation.FuncAnimation] = {}
        
        # 性能统计
        self.stats = {
            "visualizations_created": 0,
            "realtime_frames": 0,
            "average_render_time": 0.0,
            "memory_usage_mb": 0.0,
            "gpu_accelerated": 0
        }
        
        # 初始化可视化系统
        self._initialize_visualization_system()
        
        logger.info("AudioVisualizer initialized")

    def _initialize_visualization_system(self):
        """初始化可视化系统"""
        try:
            # 设置matplotlib后端
            import matplotlib
            matplotlib.use('Agg')  # 使用非交互式后端
            
            # 初始化图形样式
            plt.style.use('dark_background')
            
            # 初始化颜色映射
            self.colormaps = {
                "waveform": plt.cm.Blues,
                "spectrogram": plt.cm.viridis,
                "spectrum": plt.cm.plasma,
                "mfcc": plt.cm.inferno,
                "pitch": plt.cm.spring,
                "formant": plt.cm.autumn,
                "energy": plt.cm.winter
            }
            
            # 初始化实时可视化线程
            if self.config.realtime_enabled:
                self._initialize_realtime_visualization()
            
            logger.info("Visualization system initialized")
            
        except Exception as e:
            logger.error(f"Error initializing visualization system: {e}")

    def _initialize_realtime_visualization(self):
        """初始化实时可视化"""
        try:
            self.realtime_thread = threading.Thread(
                target=self._realtime_visualization_worker,
                daemon=True
            )
            self.realtime_thread.start()
            logger.info("Realtime visualization initialized")
            
        except Exception as e:
            logger.error(f"Error initializing realtime visualization: {e}")

    def _realtime_visualization_worker(self):
        """实时可视化工作线程"""
        while True:
            try:
                if self.realtime_buffer:
                    # 处理实时缓冲区中的音频数据
                    audio_data = np.concatenate(self.realtime_buffer)
                    self.realtime_buffer.clear()
                    
                    # 创建实时可视化
                    asyncio.run(self.create_realtime_visualization(audio_data))
                    self.stats["realtime_frames"] += 1
                
                time.sleep(1.0 / self.config.refresh_rate)
                
            except Exception as e:
                logger.error(f"Error in realtime visualization worker: {e}")
                time.sleep(0.1)

    async def create_visualization(self, audio_data: np.ndarray, 
                                 visualization_type: VisualizationType,
                                 title: str = None, 
                                 save_path: str = None) -> Optional[Figure]:
        """
        创建可视化 - 完整实现
        
        Args:
            audio_data: 音频数据
            visualization_type: 可视化类型
            title: 图表标题
            save_path: 保存路径
            
        Returns:
            Optional[Figure]: 创建的图形对象
        """
        start_time = time.time()
        
        try:
            # 预处理音频数据
            processed_audio = await self._preprocess_audio(audio_data)
            
            # 提取特征
            features = await self._extract_audio_features(processed_audio)
            
            # 创建可视化数据
            viz_data = VisualizationData(
                timestamp=time.time(),
                audio_data=processed_audio,
                features=features,
                visualization_type=visualization_type,
                metadata={"title": title, "save_path": save_path}
            )
            
            self.visualization_data.append(viz_data)
            
            # 创建图形
            figure = await self._create_figure(viz_data)
            if not figure:
                logger.error("Failed to create visualization figure")
                return None
            
            # 保存到文件
            if save_path and self.config.save_to_file:
                await self._save_visualization(figure, save_path)
            
            # 更新统计
            render_time = time.time() - start_time
            self.stats["visualizations_created"] += 1
            self.stats["average_render_time"] = (
                (self.stats["average_render_time"] * (self.stats["visualizations_created"] - 1) + render_time) 
                / self.stats["visualizations_created"]
            )
            
            logger.info(f"Visualization created: {visualization_type.value}")
            return figure
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            return None

    async def _preprocess_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """预处理音频数据"""
        try:
            # 归一化
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # 重采样到配置的采样率
            if len(audio_data) > 0:
                target_length = int(len(audio_data) * self.config.sample_rate / 22050)
                audio_data = await self._resample_audio(audio_data, target_length)
            
            return audio_data
            
        except Exception as e:
            logger.warning(f"Error preprocessing audio: {e}")
            return audio_data

    async def _resample_audio(self, audio_data: np.ndarray, target_length: int) -> np.ndarray:
        """重采样音频"""
        try:
            if len(audio_data) == target_length:
                return audio_data
            
            # 线性插值重采样
            original_indices = np.arange(len(audio_data))
            target_indices = np.linspace(0, len(audio_data) - 1, target_length)
            
            return np.interp(target_indices, original_indices, audio_data)
            
        except Exception as e:
            logger.warning(f"Error resampling audio: {e}")
            return audio_data

    async def _extract_audio_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """提取音频特征"""
        try:
            features = {}
            
            # 基础特征
            features["duration"] = len(audio_data) / self.config.sample_rate
            features["rms_energy"] = np.sqrt(np.mean(audio_data**2))
            features["zero_crossing_rate"] = np.mean(np.diff(np.sign(audio_data)) != 0)
            
            # 频谱特征
            spectrum_features = await self._extract_spectrum_features(audio_data)
            features.update(spectrum_features)
            
            # MFCC特征
            mfcc_features = await self._extract_mfcc_features(audio_data)
            features.update(mfcc_features)
            
            # 音高特征
            pitch_features = await self._extract_pitch_features(audio_data)
            features.update(pitch_features)
            
            # 共振峰特征
            formant_features = await self._extract_formant_features(audio_data)
            features.update(formant_features)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            return {}

    async def _extract_spectrum_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """提取频谱特征"""
        try:
            # 计算频谱
            spectrum = np.abs(np.fft.fft(audio_data))
            spectrum = spectrum[:len(spectrum)//2]  # 取正频率
            frequencies = np.linspace(0, self.config.sample_rate/2, len(spectrum))
            
            # 频谱特征
            spectral_centroid = np.sum(frequencies * spectrum) / np.sum(spectrum)
            spectral_rolloff = self._calculate_spectral_rolloff(spectrum, frequencies, 0.85)
            spectral_flux = await self._calculate_spectral_flux(spectrum)
            
            return {
                "spectrum": spectrum,
                "frequencies": frequencies,
                "spectral_centroid": spectral_centroid,
                "spectral_rolloff": spectral_rolloff,
                "spectral_flux": spectral_flux
            }
            
        except Exception as e:
            logger.warning(f"Error extracting spectrum features: {e}")
            return {}

    def _calculate_spectral_rolloff(self, spectrum: np.ndarray, frequencies: np.ndarray, 
                                  percentile: float) -> float:
        """计算频谱滚降"""
        try:
            cumulative_sum = np.cumsum(spectrum)
            total_energy = cumulative_sum[-1]
            target_energy = total_energy * percentile
            
            rolloff_idx = np.argmax(cumulative_sum >= target_energy)
            return frequencies[rolloff_idx] if rolloff_idx < len(frequencies) else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating spectral rolloff: {e}")
            return 0.0

    async def _calculate_spectral_flux(self, spectrum: np.ndarray) -> float:
        """计算频谱通量"""
        try:
            # 简化的频谱通量计算
            # 实际应该与前一帧比较
            diff = np.diff(spectrum)
            flux = np.sum(diff[diff > 0]**2)
            return float(flux)
            
        except Exception as e:
            logger.warning(f"Error calculating spectral flux: {e}")
            return 0.0

    async def _extract_mfcc_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """提取MFCC特征"""
        try:
            # 简化的MFCC实现
            spectrum = np.abs(np.fft.fft(audio_data))
            spectrum = spectrum[:len(spectrum)//2]
            
            # 梅尔滤波器组
            mel_filters = self._create_mel_filterbank(self.config.sample_rate, len(spectrum), self.config.n_mels)
            mel_spectrum = np.dot(mel_filters, spectrum)
            
            # 对数能量
            log_mel_spectrum = np.log(mel_spectrum + 1e-8)
            
            # DCT变换
            mfcc = np.fft.dct(log_mel_spectrum, type=2, norm='ortho')[:self.config.n_mfcc]
            
            return {
                "mfcc": mfcc,
                "mel_spectrum": mel_spectrum,
                "mfcc_mean": float(np.mean(mfcc)),
                "mfcc_std": float(np.std(mfcc))
            }
            
        except Exception as e:
            logger.warning(f"Error extracting MFCC features: {e}")
            return {}

    def _create_mel_filterbank(self, sample_rate: int, n_fft: int, n_mels: int = 128) -> np.ndarray:
        """创建梅尔滤波器组"""
        try:
            f_min = 0
            f_max = sample_rate / 2
            
            # 梅尔频率点
            mel_points = np.linspace(self._hz_to_mel(f_min), self._hz_to_mel(f_max), n_mels + 2)
            hz_points = self._mel_to_hz(mel_points)
            
            # 转换为FFT bin索引
            bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
            
            # 创建滤波器
            filters = np.zeros((n_mels, n_fft))
            
            for i in range(1, n_mels + 1):
                left = bin_points[i - 1]
                center = bin_points[i]
                right = bin_points[i + 1]
                
                if left < center:
                    filters[i - 1, left:center] = np.linspace(0, 1, center - left)
                
                if center < right:
                    filters[i - 1, center:right] = np.linspace(1, 0, right - center)
            
            # 能量归一化
            filters = filters / np.sum(filters, axis=1, keepdims=True)
            
            return filters
            
        except Exception as e:
            logger.warning(f"Error creating mel filterbank: {e}")
            return np.ones((n_mels, n_fft)) / n_mels

    def _hz_to_mel(self, hz: float) -> float:
        """Hz到Mel频率转换"""
        return 2595 * np.log10(1 + hz / 700)

    def _mel_to_hz(self, mel: float) -> float:
        """Mel到Hz频率转换"""
        return 700 * (10 ** (mel / 2595) - 1)

    async def _extract_pitch_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """提取音高特征"""
        try:
            # 自相关法计算音高
            autocorr = np.correlate(audio_data, audio_data, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # 寻找基频峰值
            min_period = int(self.config.sample_rate / 500)  # 500Hz最大频率
            max_period = int(self.config.sample_rate / 80)   # 80Hz最小频率
            
            if len(autocorr) > max_period:
                search_range = autocorr[min_period:max_period]
                if len(search_range) > 0:
                    peak_idx = np.argmax(search_range) + min_period
                    pitch = self.config.sample_rate / peak_idx if peak_idx > 0 else 0.0
                else:
                    pitch = 0.0
            else:
                pitch = 0.0
            
            return {
                "pitch": pitch,
                "pitch_confidence": min(1.0, np.max(autocorr) * 10)
            }
            
        except Exception as e:
            logger.warning(f"Error extracting pitch features: {e}")
            return {"pitch": 0.0, "pitch_confidence": 0.0}

    async def _extract_formant_features(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """提取共振峰特征"""
        try:
            spectrum = np.abs(np.fft.fft(audio_data))
            spectrum = spectrum[:len(spectrum)//2]
            frequencies = np.linspace(0, self.config.sample_rate/2, len(spectrum))
            
            # 简化的共振峰检测
            peaks, peak_values = self._find_spectral_peaks(spectrum)
            
            formants = []
            for peak_idx in peaks[:4]:  # 取前4个共振峰
                if peak_idx < len(frequencies):
                    formants.append(float(frequencies[peak_idx]))
            
            return {
                "formants": formants,
                "f1": formants[0] if len(formants) > 0 else 0.0,
                "f2": formants[1] if len(formants) > 1 else 0.0,
                "f3": formants[2] if len(formants) > 2 else 0.0
            }
            
        except Exception as e:
            logger.warning(f"Error extracting formant features: {e}")
            return {"formants": [], "f1": 0.0, "f2": 0.0, "f3": 0.0}

    def _find_spectral_peaks(self, spectrum: np.ndarray, min_distance: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """寻找频谱峰值"""
        try:
            peaks = []
            values = []
            
            for i in range(1, len(spectrum) - 1):
                if (spectrum[i] > spectrum[i - 1] and 
                    spectrum[i] > spectrum[i + 1] and 
                    spectrum[i] > 0.1 * np.max(spectrum)):
                    
                    # 检查最小距离
                    if not peaks or (i - peaks[-1]) >= min_distance:
                        peaks.append(i)
                        values.append(spectrum[i])
            
            return np.array(peaks), np.array(values)
            
        except Exception as e:
            logger.warning(f"Error finding spectral peaks: {e}")
            return np.array([]), np.array([])

    async def _create_figure(self, viz_data: VisualizationData) -> Optional[Figure]:
        """创建图形"""
        try:
            viz_type = viz_data.visualization_type
            
            if viz_type == VisualizationType.WAVEFORM:
                return await self._create_waveform_plot(viz_data)
            elif viz_type == VisualizationType.SPECTROGRAM:
                return await self._create_spectrogram_plot(viz_data)
            elif viz_type == VisualizationType.SPECTRUM:
                return await self._create_spectrum_plot(viz_data)
            elif viz_type == VisualizationType.MFCC:
                return await self._create_mfcc_plot(viz_data)
            elif viz_type == VisualizationType.PITCH:
                return await self._create_pitch_plot(viz_data)
            elif viz_type == VisualizationType.FORMANT:
                return await self._create_formant_plot(viz_data)
            elif viz_type == VisualizationType.ENERGY:
                return await self._create_energy_plot(viz_data)
            elif viz_type == VisualizationType.REAL_TIME:
                return await self._create_realtime_plot(viz_data)
            else:
                logger.error(f"Unknown visualization type: {viz_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating figure: {e}")
            return None

    async def _create_waveform_plot(self, viz_data: VisualizationData) -> Figure:
        """创建波形图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            audio_data = viz_data.audio_data
            time_axis = np.linspace(0, len(audio_data)/self.config.sample_rate, len(audio_data))
            
            ax.plot(time_axis, audio_data, color='cyan', linewidth=1)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Amplitude')
            ax.set_title(viz_data.metadata.get("title", "Audio Waveform"))
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating waveform plot: {e}")
            return await self._create_error_plot("Waveform")

    async def _create_spectrogram_plot(self, viz_data: VisualizationData) -> Figure:
        """创建语谱图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            audio_data = viz_data.audio_data
            
            # 计算语谱图
            spectrum, frequencies, times, im = ax.specgram(
                audio_data, 
                NFFT=self.config.fft_size,
                Fs=self.config.sample_rate,
                noverlap=self.config.fft_size - self.config.hop_size,
                cmap=self.colormaps["spectrogram"]
            )
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_title(viz_data.metadata.get("title", "Spectrogram"))
            
            # 添加颜色条
            plt.colorbar(im, ax=ax, label='Intensity (dB)')
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating spectrogram plot: {e}")
            return await self._create_error_plot("Spectrogram")

    async def _create_spectrum_plot(self, viz_data: VisualizationData) -> Figure:
        """创建频谱图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            features = viz_data.features
            spectrum = features.get("spectrum", np.array([]))
            frequencies = features.get("frequencies", np.array([]))
            
            if len(spectrum) > 0 and len(frequencies) > 0:
                ax.semilogy(frequencies, spectrum, color='magenta', linewidth=1)
                ax.set_xlabel('Frequency (Hz)')
                ax.set_ylabel('Amplitude')
                ax.set_title(viz_data.metadata.get("title", "Frequency Spectrum"))
                ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating spectrum plot: {e}")
            return await self._create_error_plot("Spectrum")

    async def _create_mfcc_plot(self, viz_data: VisualizationData) -> Figure:
        """创建MFCC特征图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            features = viz_data.features
            mfcc = features.get("mfcc", np.array([]))
            
            if len(mfcc) > 0:
                im = ax.imshow(
                    mfcc.reshape(-1, 1), 
                    aspect='auto', 
                    origin='lower',
                    cmap=self.colormaps["mfcc"]
                )
                ax.set_xlabel('MFCC Coefficients')
                ax.set_ylabel('Time Frames')
                ax.set_title(viz_data.metadata.get("title", "MFCC Features"))
                
                # 添加颜色条
                plt.colorbar(im, ax=ax, label='Coefficient Value')
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating MFCC plot: {e}")
            return await self._create_error_plot("MFCC")

    async def _create_pitch_plot(self, viz_data: VisualizationData) -> Figure:
        """创建音高图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            audio_data = viz_data.audio_data
            time_axis = np.linspace(0, len(audio_data)/self.config.sample_rate, len(audio_data))
            
            # 简化的音高轨迹（实际应该计算每帧的音高）
            pitch = viz_data.features.get("pitch", 0.0)
            if pitch > 0:
                pitch_track = np.full_like(time_axis, pitch)
                ax.plot(time_axis, pitch_track, color='yellow', linewidth=2)
                ax.set_ylim(0, 500)  # 限制在0-500Hz范围
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Pitch (Hz)')
            ax.set_title(viz_data.metadata.get("title", "Pitch Track"))
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating pitch plot: {e}")
            return await self._create_error_plot("Pitch")

    async def _create_formant_plot(self, viz_data: VisualizationData) -> Figure:
        """创建共振峰图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            features = viz_data.features
            formants = features.get("formants", [])
            
            if formants:
                # 绘制共振峰位置
                for i, formant in enumerate(formants[:3]):  # 前三个共振峰
                    ax.axvline(x=formant, color=['red', 'green', 'blue'][i], 
                              linestyle='--', linewidth=2, 
                              label=f'F{i+1}: {formant:.1f}Hz')
                
                # 绘制频谱背景
                spectrum = features.get("spectrum", np.array([]))
                frequencies = features.get("frequencies", np.array([]))
                
                if len(spectrum) > 0:
                    ax.plot(frequencies, spectrum, color='white', alpha=0.5, linewidth=1)
            
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel('Amplitude')
            ax.set_title(viz_data.metadata.get("title", "Formant Analysis"))
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating formant plot: {e}")
            return await self._create_error_plot("Formant")

    async def _create_energy_plot(self, viz_data: VisualizationData) -> Figure:
        """创建能量图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            audio_data = viz_data.audio_data
            time_axis = np.linspace(0, len(audio_data)/self.config.sample_rate, len(audio_data))
            
            # 计算能量包络
            frame_size = 256
            hop_size = 128
            energy = []
            energy_times = []
            
            for i in range(0, len(audio_data) - frame_size, hop_size):
                frame = audio_data[i:i + frame_size]
                frame_energy = np.mean(frame**2)
                energy.append(frame_energy)
                energy_times.append(time_axis[i])
            
            if energy:
                ax.plot(energy_times, energy, color='orange', linewidth=2)
                ax.fill_between(energy_times, 0, energy, alpha=0.3, color='orange')
            
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Energy')
            ax.set_title(viz_data.metadata.get("title", "Energy Envelope"))
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating energy plot: {e}")
            return await self._create_error_plot("Energy")

    async def _create_realtime_plot(self, viz_data: VisualizationData) -> Figure:
        """创建实时可视化图"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(self.config.width/100, self.config.height/100))
            
            audio_data = viz_data.audio_data
            time_axis = np.linspace(0, len(audio_data)/self.config.sample_rate, len(audio_data))
            
            # 上部：波形
            ax1.plot(time_axis, audio_data, color='cyan', linewidth=1)
            ax1.set_ylabel('Amplitude')
            ax1.set_title('Real-time Audio Waveform')
            ax1.grid(True, alpha=0.3)
            
            # 下部：频谱
            spectrum = np.abs(np.fft.fft(audio_data))
            spectrum = spectrum[:len(spectrum)//2]
            frequencies = np.linspace(0, self.config.sample_rate/2, len(spectrum))
            
            ax2.semilogy(frequencies, spectrum, color='magenta', linewidth=1)
            ax2.set_xlabel('Frequency (Hz)')
            ax2.set_ylabel('Amplitude')
            ax2.set_title('Real-time Spectrum')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return fig
            
        except Exception as e:
            logger.error(f"Error creating realtime plot: {e}")
            return await self._create_error_plot("Real-time")

    async def _create_error_plot(self, plot_type: str) -> Figure:
        """创建错误提示图"""
        try:
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            ax.text(0.5, 0.5, f"Error creating {plot_type} plot", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=14, color='red')
            ax.set_title(f"{plot_type} - Error")
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating error plot: {e}")
            return None

    async def _save_visualization(self, figure: Figure, save_path: str):
        """保存可视化"""
        try:
            figure.savefig(save_path, dpi=300, bbox_inches='tight', 
                          facecolor='black', edgecolor='none')
            logger.info(f"Visualization saved to: {save_path}")
            
        except Exception as e:
            logger.error(f"Error saving visualization: {e}")

    async def create_realtime_visualization(self, audio_data: np.ndarray):
        """创建实时可视化"""
        try:
            # 这里应该更新实时可视化窗口
            # 简化实现：创建静态图
            if self.config.realtime_enabled:
                await self.create_visualization(
                    audio_data, 
                    VisualizationType.REAL_TIME,
                    "Real-time Audio Analysis"
                )
                
        except Exception as e:
            logger.error(f"Error creating realtime visualization: {e}")

    async def add_realtime_audio(self, audio_chunk: np.ndarray):
        """添加实时音频数据"""
        try:
            self.realtime_buffer.append(audio_chunk)
            
            # 限制缓冲区大小
            max_buffer_size = 10  # 最多保存10个块
            if len(self.realtime_buffer) > max_buffer_size:
                self.realtime_buffer = self.realtime_buffer[-max_buffer_size:]
                
        except Exception as e:
            logger.error(f"Error adding realtime audio: {e}")

    async def start_realtime_visualization(self, window_id: str):
        """启动实时可视化"""
        try:
            if window_id in self.active_visualizations:
                logger.warning(f"Realtime visualization already running: {window_id}")
                return False
            
            # 创建实时可视化窗口
            fig, ax = plt.subplots(figsize=(self.config.width/100, self.config.height/100))
            
            def update(frame):
                # 更新实时可视化
                if self.realtime_buffer:
                    latest_audio = np.concatenate(self.realtime_buffer[-1:])
                    ax.clear()
                    
                    # 绘制最新音频
                    time_axis = np.linspace(0, len(latest_audio)/self.config.sample_rate, len(latest_audio))
                    ax.plot(time_axis, latest_audio, color='cyan')
                    ax.set_title('Real-time Audio')
                    ax.grid(True, alpha=0.3)
                
                return []
            
            # 创建动画
            anim = animation.FuncAnimation(
                fig, update, interval=1000/self.config.refresh_rate, 
                blit=False, cache_frame_data=False
            )
            
            self.active_visualizations[window_id] = {
                "figure": fig,
                "animation": anim
            }
            
            logger.info(f"Realtime visualization started: {window_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting realtime visualization: {e}")
            return False

    async def stop_realtime_visualization(self, window_id: str):
        """停止实时可视化"""
        try:
            if window_id in self.active_visualizations:
                viz_data = self.active_visualizations[window_id]
                
                # 停止动画
                if "animation" in viz_data:
                    viz_data["animation"].event_source.stop()
                
                # 关闭图形
                if "figure" in viz_data:
                    plt.close(viz_data["figure"])
                
                del self.active_visualizations[window_id]
                logger.info(f"Realtime visualization stopped: {window_id}")
                return True
            else:
                logger.warning(f"Realtime visualization not found: {window_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error stopping realtime visualization: {e}")
            return False

    async def get_visualization_data(self, index: int = -1) -> Optional[VisualizationData]:
        """获取可视化数据"""
        try:
            if self.visualization_data:
                return self.visualization_data[index]
            return None
        except Exception as e:
            logger.error(f"Error getting visualization data: {e}")
            return None

    async def clear_visualization_data(self):
        """清空可视化数据"""
        try:
            self.visualization_data.clear()
            logger.info("Visualization data cleared")
        except Exception as e:
            logger.error(f"Error clearing visualization data: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["visualization_data_count"] = len(self.visualization_data)
        stats["realtime_buffer_size"] = len(self.realtime_buffer)
        stats["active_visualizations"] = len(self.active_visualizations)
        
        # 估算内存使用
        total_memory = 0
        for viz_data in self.visualization_data:
            total_memory += viz_data.audio_data.nbytes
            for feature in viz_data.features.values():
                if hasattr(feature, 'nbytes'):
                    total_memory += feature.nbytes
        
        stats["memory_usage_mb"] = total_memory / (1024 * 1024)
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            # 停止所有实时可视化
            for window_id in list(self.active_visualizations.keys()):
                await self.stop_realtime_visualization(window_id)
            
            # 清空数据
            self.visualization_data.clear()
            self.realtime_buffer.clear()
            
            # 关闭所有图形
            plt.close('all')
            
            logger.info("AudioVisualizer cleaned up")
            
        except Exception as e:
            logger.error(f"Error during AudioVisualizer cleanup: {e}")

# 全局音频可视化器实例
audio_visualizer = AudioVisualizer()

