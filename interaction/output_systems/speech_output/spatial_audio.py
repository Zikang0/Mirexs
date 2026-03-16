"""
3D 空间音频（Spatial Audio）

根据设计文档，Mirexs 的语音输出支持“3D 空间音频”。
在不依赖复杂 HRTF 数据集的前提下，本模块实现一个可运行的空间化算法：
- 角度（azimuth）控制左右声道增益（等响度 panning）
- 简单距离衰减
- 可选的左右耳时间差（ITD，分数延迟）

输入支持 mono / stereo numpy float 音频：
- mono: (n,) 或 (n,1) -> stereo (n,2)
- stereo: (n,2) -> 继续空间化（基于宽度/衰减）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math

import numpy as np


def _as_float32(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.dtype == np.float32:
        return audio
    return audio.astype(np.float32, copy=False)


def _as_2d(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.ndim == 1:
        return audio.reshape(-1, 1)
    if audio.ndim == 2 and audio.shape[1] in (1, 2):
        return audio
    raise ValueError(f"Unsupported audio shape: {audio.shape}")


def _fractional_delay(x: np.ndarray, delay_samples: float) -> np.ndarray:
    """线性插值分数延迟。delay_samples>0 表示向右延迟（输出更晚）。"""
    if abs(delay_samples) < 1e-6:
        return x

    n = x.shape[0]
    idx = np.arange(n, dtype=np.float32) - float(delay_samples)
    idx0 = np.floor(idx).astype(np.int32)
    frac = idx - idx0

    idx0_clipped = np.clip(idx0, 0, n - 1)
    idx1_clipped = np.clip(idx0 + 1, 0, n - 1)

    y0 = x[idx0_clipped]
    y1 = x[idx1_clipped]
    return (1.0 - frac) * y0 + frac * y1


@dataclass
class SpatialAudioConfig:
    azimuth_deg: float = 0.0  # -180..180；0在正前方，+右侧
    distance_m: float = 1.0
    stereo_width: float = 1.0  # 0..2

    # ITD（左右耳时间差）
    enable_itd: bool = True
    itd_max_ms: float = 0.6  # 常见范围 0.2-0.8ms

    # 衰减模型
    min_distance_m: float = 0.2
    attenuation: str = "inverse"  # inverse | none


class SpatialAudioProcessor:
    """空间音频处理器"""

    def apply(self, audio: np.ndarray, sample_rate: int, config: Optional[SpatialAudioConfig] = None) -> np.ndarray:
        if config is None:
            config = SpatialAudioConfig()

        audio2d = _as_2d(_as_float32(audio))

        # 统一为 stereo
        if audio2d.shape[1] == 1:
            stereo = np.repeat(audio2d, 2, axis=1)
        else:
            stereo = audio2d.copy()

        # 等响度 panning（cos/sin law）
        az = float(config.azimuth_deg)
        az = max(-180.0, min(180.0, az))
        # 将 [-90,90] 映射到 [0,1]；超出视为侧后方，仍按侧向处理
        pan = (max(-90.0, min(90.0, az)) + 90.0) / 180.0
        left_gain = math.cos(pan * math.pi / 2.0)
        right_gain = math.sin(pan * math.pi / 2.0)

        stereo[:, 0] *= left_gain
        stereo[:, 1] *= right_gain

        # 可选 ITD：右侧则左耳延迟，左侧则右耳延迟
        if config.enable_itd and config.itd_max_ms > 0:
            itd = (az / 90.0) * float(config.itd_max_ms)  # ms
            delay_samples = (itd / 1000.0) * float(sample_rate)
            if delay_samples > 0:
                stereo[:, 0] = _fractional_delay(stereo[:, 0], delay_samples)
            else:
                stereo[:, 1] = _fractional_delay(stereo[:, 1], -delay_samples)

        # 距离衰减
        dist = max(float(config.min_distance_m), float(config.distance_m))
        if config.attenuation == "inverse":
            gain = float(config.min_distance_m) / dist
            stereo *= gain

        # 宽度调整（mid/side）
        width = float(np.clip(config.stereo_width, 0.0, 2.0))
        if width != 1.0:
            mid = (stereo[:, 0] + stereo[:, 1]) * 0.5
            side = (stereo[:, 1] - stereo[:, 0]) * 0.5
            side *= width
            stereo[:, 0] = mid - side
            stereo[:, 1] = mid + side

        return stereo.astype(np.float32, copy=False)


