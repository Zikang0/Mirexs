"""
情感语音策略（Emotional Voice）

本模块提供“从文本/上下文推断情感 → 应用到 TTSConfig”的策略层。
它不依赖大型模型，采用规则 + 轻量打分，便于离线/本地化部署。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
import re

from .multilingual_tts import EmotionType, TTSConfig


@dataclass
class EmotionRequest:
    emotion: EmotionType
    strength: float = 1.0  # 0..2（由 voice_profile.emotion_strength 共同作用）


class EmotionalVoiceEngine:
    """情感语音引擎（规则/启发式）。"""

    _zh_positive = {"开心", "太棒了", "谢谢", "喜欢", "高兴", "爱", "赞", "哈哈"}
    _zh_negative = {"难过", "伤心", "烦", "生气", "愤怒", "讨厌", "害怕", "焦虑", "糟糕"}
    _en_positive = {"great", "awesome", "thanks", "love", "happy", "nice", "good", "haha"}
    _en_negative = {"sad", "angry", "hate", "scared", "afraid", "anxious", "upset", "terrible"}

    def infer_from_text(self, text: str) -> EmotionRequest:
        text = (text or "").strip()
        if not text:
            return EmotionRequest(EmotionType.NEUTRAL, 1.0)

        lowered = text.lower()
        score = 0.0

        # 标点倾向
        exclam = text.count("!") + text.count("！")
        quest = text.count("?") + text.count("？")
        if exclam >= 2:
            score += 0.4
        elif exclam == 1:
            score += 0.2
        if quest >= 2:
            score += 0.1

        # 关键词
        if any(k in text for k in self._zh_positive) or any(k in lowered for k in self._en_positive):
            score += 0.6
        if any(k in text for k in self._zh_negative) or any(k in lowered for k in self._en_negative):
            score -= 0.6

        # 全大写（英文）通常带情绪/紧迫
        if re.search(r"[A-Z]{6,}", text):
            score -= 0.2

        emotion = self._map_score_to_emotion(score, exclam, lowered)
        strength = 1.0 + min(1.0, abs(score))
        return EmotionRequest(emotion=emotion, strength=strength)

    def apply(self, config: TTSConfig, emotion: Optional[EmotionType] = None, text: Optional[str] = None) -> Tuple[TTSConfig, EmotionRequest]:
        """将情感应用到 TTSConfig。若 emotion 未提供，则从 text 推断。"""
        if emotion is not None:
            req = EmotionRequest(emotion=emotion, strength=1.0)
        else:
            req = self.infer_from_text(text or "")

        config.emotion = req.emotion
        return config, req

    def _map_score_to_emotion(self, score: float, exclam: int, lowered: str) -> EmotionType:
        if "谢谢" in lowered or "thank" in lowered:
            return EmotionType.HAPPY
        if score >= 0.6:
            return EmotionType.EXCITED if exclam >= 1 else EmotionType.HAPPY
        if score >= 0.2:
            return EmotionType.HAPPY
        if score <= -0.6:
            if any(w in lowered for w in ("fear", "scared", "afraid", "害怕")):
                return EmotionType.FEARFUL
            return EmotionType.ANGRY
        if score <= -0.2:
            return EmotionType.SAD
        return EmotionType.NEUTRAL


