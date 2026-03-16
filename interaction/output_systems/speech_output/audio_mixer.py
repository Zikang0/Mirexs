"""
音频混合器（Audio Mixer）

用于将多路音频（例如：TTS + 背景音 + 提示音）合成为单路输出。
仅依赖 numpy，提供：
- 多轨道对齐与叠加
- 简单重采样（线性插值）
- 增益与声像（pan）控制
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

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


def _linear_resample(x: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate:
        return x
    if x.size == 0:
        return x

    n_src = x.shape[0]
    n_dst = int(round(n_src * float(dst_rate) / float(src_rate)))
    if n_dst <= 1:
        return x[:1].copy()

    src_idx = np.linspace(0.0, n_src - 1, n_dst, dtype=np.float32)
    idx0 = np.floor(src_idx).astype(np.int32)
    idx1 = np.clip(idx0 + 1, 0, n_src - 1)
    frac = src_idx - idx0

    y0 = x[idx0]
    y1 = x[idx1]
    return (1.0 - frac).reshape(-1, 1) * y0 + frac.reshape(-1, 1) * y1


def _apply_pan(stereo: np.ndarray, pan: float) -> np.ndarray:
    """pan: [-1,1]，-1全左，+1全右。"""
    pan = float(np.clip(pan, -1.0, 1.0))
    left = (1.0 - pan) * 0.5 + 0.5
    right = (1.0 + pan) * 0.5 + 0.5
    stereo[:, 0] *= left
    stereo[:, 1] *= right
    return stereo


@dataclass
class AudioTrack:
    audio_data: np.ndarray
    sample_rate: int
    start_time_s: float = 0.0
    gain_db: float = 0.0
    pan: float = 0.0  # -1..1


@dataclass
class MixedAudio:
    audio_data: np.ndarray
    sample_rate: int


class AudioMixer:
    """多轨音频混合器"""

    def mix(self, tracks: List[AudioTrack], target_sample_rate: Optional[int] = None, normalize: bool = True) -> MixedAudio:
        if not tracks:
            return MixedAudio(audio_data=np.zeros((0, 2), dtype=np.float32), sample_rate=target_sample_rate or 22050)

        if target_sample_rate is None:
            target_sample_rate = max(int(t.sample_rate) for t in tracks)

        rendered = []
        max_end = 0
        for t in tracks:
            audio2d = _as_2d(_as_float32(t.audio_data))
            if audio2d.shape[1] == 1:
                audio2d = np.repeat(audio2d, 2, axis=1)

            # 重采样
            if int(t.sample_rate) != int(target_sample_rate):
                audio2d = _linear_resample(audio2d, int(t.sample_rate), int(target_sample_rate)).astype(np.float32, copy=False)

            # 增益
            if t.gain_db:
                gain = float(10 ** (float(t.gain_db) / 20.0))
                audio2d = audio2d * gain

            # 声像
            if t.pan:
                audio2d = _apply_pan(audio2d, float(t.pan))

            start = int(round(float(t.start_time_s) * float(target_sample_rate)))
            end = start + audio2d.shape[0]
            max_end = max(max_end, end)
            rendered.append((start, audio2d))

        mix = np.zeros((max_end, 2), dtype=np.float32)
        for start, audio2d in rendered:
            mix[start : start + audio2d.shape[0]] += audio2d

        if normalize and mix.size:
            peak = float(np.max(np.abs(mix)))
            if peak > 1.0:
                mix /= peak

        return MixedAudio(audio_data=mix, sample_rate=int(target_sample_rate))


