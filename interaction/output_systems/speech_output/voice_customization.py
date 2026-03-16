"""
语音定制（Voice Customization）

与 Mirexs 的“个性化”理念一致，本模块负责管理与定制语音配置文件（VoiceProfile）：
- 基于 MultilingualTTS 的内置 voice_profiles
- 创建/保存/导入自定义音色
- 将 voice_id 应用到 TTSConfig
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union
import json
import logging

from .multilingual_tts import MultilingualTTS, VoiceProfile, VoiceGender, VoiceAge

logger = logging.getLogger(__name__)


@dataclass
class VoiceProfileExport:
    """可序列化的语音配置（用于导入导出）。"""

    voice_id: str
    name: str
    gender: str
    age: str
    language: str
    accent: str = "standard"
    pitch: float = 1.0
    speed: float = 1.0
    energy: float = 1.0
    emotion_strength: float = 1.0
    voice_characteristics: Dict[str, float] = None

    @classmethod
    def from_profile(cls, profile: VoiceProfile) -> "VoiceProfileExport":
        return cls(
            voice_id=profile.voice_id,
            name=profile.name,
            gender=profile.gender.value,
            age=profile.age.value,
            language=profile.language,
            accent=profile.accent,
            pitch=profile.pitch,
            speed=profile.speed,
            energy=profile.energy,
            emotion_strength=profile.emotion_strength,
            voice_characteristics=dict(profile.voice_characteristics or {}),
        )

    def to_profile(self) -> VoiceProfile:
        return VoiceProfile(
            voice_id=self.voice_id,
            name=self.name,
            gender=VoiceGender(self.gender),
            age=VoiceAge(self.age),
            language=self.language,
            accent=self.accent,
            pitch=float(self.pitch),
            speed=float(self.speed),
            energy=float(self.energy),
            emotion_strength=float(self.emotion_strength),
            voice_characteristics=dict(self.voice_characteristics or {}),
        )


class VoiceCustomizationManager:
    """语音定制管理器"""

    def __init__(self, tts: Optional[MultilingualTTS] = None):
        self.tts = tts or MultilingualTTS()

    def list_voices(self, language: Optional[str] = None) -> List[VoiceProfile]:
        voices = list(self.tts.voice_profiles.values())
        if language:
            voices = [v for v in voices if v.language.lower() == language.lower()]
        return voices

    def get_voice(self, voice_id: str) -> Optional[VoiceProfile]:
        return self.tts.voice_profiles.get(voice_id)

    def set_default_voice(self, voice_id: str) -> bool:
        profile = self.get_voice(voice_id)
        if not profile:
            return False
        self.tts.current_voice = profile
        return True

    def create_custom_voice(
        self,
        base_voice_id: str,
        new_voice_id: str,
        name: Optional[str] = None,
        **overrides,
    ) -> Optional[VoiceProfile]:
        base = self.get_voice(base_voice_id)
        if not base:
            return None

        export = VoiceProfileExport.from_profile(base)
        export.voice_id = new_voice_id
        export.name = name or base.name

        for k, v in overrides.items():
            if hasattr(export, k):
                setattr(export, k, v)

        profile = export.to_profile()
        self.tts.voice_profiles[profile.voice_id] = profile
        return profile

    def export_profiles(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        exports = [VoiceProfileExport.from_profile(v).__dict__ for v in self.tts.voice_profiles.values()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(exports, f, indent=2, ensure_ascii=False)
        return path

    def import_profiles(self, path: Union[str, Path], overwrite: bool = False) -> int:
        path = Path(path)
        if not path.exists():
            return 0

        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        imported = 0
        for item in items:
            try:
                export = VoiceProfileExport(**item)
                profile = export.to_profile()
                if (not overwrite) and profile.voice_id in self.tts.voice_profiles:
                    continue
                self.tts.voice_profiles[profile.voice_id] = profile
                imported += 1
            except Exception as e:
                logger.warning(f"跳过无效 voice profile: {e}")

        return imported


