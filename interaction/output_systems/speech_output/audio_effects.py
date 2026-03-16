"""
音效处理模块（Audio Effects）

本模块为语音合成后的音频提供轻量、可组合的后处理能力：
- 增益与归一化
- 淡入/淡出
- 简单回声与混响（卷积式衰减脉冲响应）
- 一阶高通/低通滤波（无需 SciPy）

设计目标：
1) 在依赖缺失的环境下也可用（仅依赖 numpy）
2) 对 mono / stereo 数据都安全
3) 与 Mirexs 的实时输出需求兼容（性能/复杂度可控）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math

import numpy as np


def _as_float32(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.float32:
        return audio
    return audio.astype(np.float32, copy=False)


def _as_2d(audio: np.ndarray) -> np.ndarray:
    """将输入统一为 (n, c) 形状，c=1 或 2。"""
    audio = np.asarray(audio)
    if audio.ndim == 1:
        return audio.reshape(-1, 1)
    if audio.ndim == 2 and audio.shape[1] in (1, 2):
        return audio
    raise ValueError(f"Unsupported audio shape: {audio.shape} (expected (n,), (n,1) or (n,2))")


def _clip(audio: np.ndarray, limit: float = 1.0) -> np.ndarray:
    return np.clip(audio, -limit, limit, out=audio)


def peak_normalize(audio: np.ndarray, target_peak: float = 0.98, eps: float = 1e-9) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    peak = float(np.max(np.abs(audio2d)))
    if peak < eps:
        return audio2d
    gain = target_peak / peak
    audio2d *= gain
    return audio2d


def apply_gain_db(audio: np.ndarray, gain_db: float) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    gain = float(10 ** (gain_db / 20.0))
    audio2d *= gain
    return audio2d


def apply_fade(audio: np.ndarray, sample_rate: int, fade_in_ms: float = 0.0, fade_out_ms: float = 0.0) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    n = audio2d.shape[0]
    if n == 0:
        return audio2d

    fade_in = int(max(0.0, fade_in_ms) * sample_rate / 1000.0)
    fade_out = int(max(0.0, fade_out_ms) * sample_rate / 1000.0)

    if fade_in > 0:
        fade_in = min(fade_in, n)
        ramp = np.linspace(0.0, 1.0, fade_in, dtype=np.float32).reshape(-1, 1)
        audio2d[:fade_in] *= ramp

    if fade_out > 0:
        fade_out = min(fade_out, n)
        ramp = np.linspace(1.0, 0.0, fade_out, dtype=np.float32).reshape(-1, 1)
        audio2d[n - fade_out :] *= ramp

    return audio2d


def _first_order_low_pass(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    if cutoff_hz <= 0:
        return audio
    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * math.pi * float(cutoff_hz))
    alpha = dt / (rc + dt)

    y = np.empty_like(audio)
    y[0] = audio[0]
    for i in range(1, audio.shape[0]):
        y[i] = y[i - 1] + alpha * (audio[i] - y[i - 1])
    return y


def _first_order_high_pass(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    if cutoff_hz <= 0:
        return audio
    dt = 1.0 / float(sample_rate)
    rc = 1.0 / (2.0 * math.pi * float(cutoff_hz))
    alpha = rc / (rc + dt)

    y = np.empty_like(audio)
    y[0] = audio[0]
    x_prev = audio[0]
    for i in range(1, audio.shape[0]):
        y[i] = alpha * (y[i - 1] + audio[i] - x_prev)
        x_prev = audio[i]
    return y


def apply_low_pass(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    for ch in range(audio2d.shape[1]):
        audio2d[:, ch] = _first_order_low_pass(audio2d[:, ch], sample_rate, cutoff_hz)
    return audio2d


def apply_high_pass(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    for ch in range(audio2d.shape[1]):
        audio2d[:, ch] = _first_order_high_pass(audio2d[:, ch], sample_rate, cutoff_hz)
    return audio2d


@dataclass
class EchoConfig:
    delay_ms: float = 120.0
    decay: float = 0.35
    repeats: int = 3


def apply_echo(audio: np.ndarray, sample_rate: int, config: EchoConfig) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    if config.repeats <= 0 or config.decay <= 0.0 or config.delay_ms <= 0.0:
        return audio2d

    delay = int(config.delay_ms * sample_rate / 1000.0)
    if delay <= 0:
        return audio2d

    out = audio2d.copy()
    for i in range(1, config.repeats + 1):
        start = i * delay
        if start >= out.shape[0]:
            break
        length = out.shape[0] - start
        out[start:] += (config.decay**i) * audio2d[:length]
    return out


@dataclass
class ReverbConfig:
    """简单混响：通过指数衰减脉冲响应进行卷积（轻量实现）。"""

    room_size: float = 0.35  # 0-1，越大尾音越长
    damping: float = 0.5  # 0-1，高频衰减
    wet: float = 0.25  # 0-1
    impulse_ms: float = 180.0


def apply_reverb(audio: np.ndarray, sample_rate: int, config: ReverbConfig) -> np.ndarray:
    audio2d = _as_2d(_as_float32(audio)).copy()
    wet = float(np.clip(config.wet, 0.0, 1.0))
    if wet <= 0.0:
        return audio2d

    impulse_len = int(max(1.0, config.impulse_ms) * sample_rate / 1000.0)
    t = np.arange(impulse_len, dtype=np.float32) / float(sample_rate)

    # 指数衰减 + 高频阻尼（用更快的衰减模拟）
    decay = 2.0 + 10.0 * float(np.clip(config.room_size, 0.0, 1.0))
    damping = 1.0 + 8.0 * float(np.clip(config.damping, 0.0, 1.0))
    impulse = np.exp(-decay * t) * np.exp(-damping * t)
    impulse[0] = 1.0
    impulse = impulse.astype(np.float32)

    out = audio2d.copy()
    for ch in range(audio2d.shape[1]):
        convolved = np.convolve(audio2d[:, ch], impulse, mode="full")[: audio2d.shape[0]]
        out[:, ch] = (1.0 - wet) * audio2d[:, ch] + wet * convolved.astype(np.float32)
    return out


@dataclass
class AudioEffectsConfig:
    """音效链配置"""

    # 基础增益与归一化
    gain_db: float = 0.0
    normalize_peak: bool = True
    target_peak: float = 0.98

    # 淡入淡出
    fade_in_ms: float = 0.0
    fade_out_ms: float = 0.0

    # 滤波
    high_pass_hz: Optional[float] = None
    low_pass_hz: Optional[float] = None

    # 效果
    echo: Optional[EchoConfig] = None
    reverb: Optional[ReverbConfig] = None

    # 安全
    hard_clip: bool = True
    clip_limit: float = 1.0


class AudioEffectsProcessor:
    """音效处理器"""

    def apply(self, audio: np.ndarray, sample_rate: int, config: Optional[AudioEffectsConfig] = None) -> np.ndarray:
        if config is None:
            config = AudioEffectsConfig()

        processed = _as_2d(_as_float32(audio))

        if config.high_pass_hz:
            processed = apply_high_pass(processed, sample_rate, float(config.high_pass_hz))
        if config.low_pass_hz:
            processed = apply_low_pass(processed, sample_rate, float(config.low_pass_hz))

        if config.echo:
            processed = apply_echo(processed, sample_rate, config.echo)
        if config.reverb:
            processed = apply_reverb(processed, sample_rate, config.reverb)

        if config.gain_db:
            processed = apply_gain_db(processed, float(config.gain_db))

        if config.fade_in_ms or config.fade_out_ms:
            processed = apply_fade(processed, sample_rate, config.fade_in_ms, config.fade_out_ms)

        if config.normalize_peak:
            processed = peak_normalize(processed, float(config.target_peak))

        if config.hard_clip:
            processed = _clip(processed, float(config.clip_limit))

        return processed


