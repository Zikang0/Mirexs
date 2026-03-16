# config/user/preferences/__init__.py
"""
用户偏好模块
管理语言、交互、内容、隐私和通知偏好
"""

import os
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class LanguageCode(Enum):
    """语言代码枚举"""
    ZH_CN = "zh-CN"  # 简体中文
    EN_US = "en-US"  # 美式英语
    JA_JP = "ja-JP"  # 日语
    KO_KR = "ko-KR"  # 韩语
    FR_FR = "fr-FR"  # 法语
    DE_DE = "de-DE"  # 德语
    ES_ES = "es-ES"  # 西班牙语
    RU_RU = "ru-RU"  # 俄语


class InputMethod(Enum):
    """输入方法枚举"""
    VOICE_PRIMARY = "voice_primary"  # 语音优先
    TEXT_PRIMARY = "text_primary"  # 文本优先
    MIXED = "mixed"  # 混合输入
    GESTURE = "gesture"  # 手势输入


class ContentFilterLevel(Enum):
    """内容过滤级别枚举"""
    NONE = "none"  # 不过滤
    MINIMAL = "minimal"  # 最小过滤
    MODERATE = "moderate"  # 适度过滤
    STRICT = "strict"  # 严格过滤
    MAXIMUM = "maximum"  # 最大过滤


class PrivacyLevel(Enum):
    """隐私级别枚举"""
    MINIMAL = "minimal"  # 最小隐私
    STANDARD = "standard"  # 标准隐私
    ENHANCED = "enhanced"  # 增强隐私
    MAXIMUM = "maximum"  # 最大隐私


@dataclass
class LanguagePreferences:
    """语言偏好设置"""
    primary_language: LanguageCode = LanguageCode.ZH_CN
    secondary_languages: List[LanguageCode] = field(default_factory=lambda: [LanguageCode.EN_US])
    auto_translate: bool = True
    translation_target: LanguageCode = LanguageCode.ZH_CN
    preferred_dialect: str = "standard"
    show_original_text: bool = False
    language_learning_mode: bool = False

    def get_language_list(self) -> List[str]:
        """获取语言列表"""
        languages = [self.primary_language.value]
        languages.extend([lang.value for lang in self.secondary_languages])
        return languages

    def should_translate(self, source_lang: str) -> bool:
        """判断是否需要翻译"""
        if not self.auto_translate:
            return False

        target = self.translation_target.value
        return source_lang != target


@dataclass
class InteractionPreferences:
    """交互偏好设置"""
    input_method: InputMethod = InputMethod.VOICE_PRIMARY
    response_speed: str = "balanced"  # slow, balanced, fast, instant
    confirmation_level: str = "medium"  # low, medium, high
    feedback_level: str = "detailed"  # minimal, basic, detailed, verbose
    auto_complete: bool = True
    predictive_text: bool = True
    gesture_sensitivity: float = 0.5  # 0-1
    voice_command_timeout: int = 5  # 秒

    def get_response_timeout(self) -> int:
        """获取响应超时时间（毫秒）"""
        speed_map = {
            "slow": 10000,
            "balanced": 5000,
            "fast": 2000,
            "instant": 1000
        }
        return speed_map.get(self.response_speed, 5000)


@dataclass
class ContentPreferences:
    """内容偏好设置"""
    content_filter: ContentFilterLevel = ContentFilterLevel.MODERATE
    safe_search: bool = True
    content_types: Set[str] = field(default_factory=lambda: {"text", "image", "video", "audio"})
    preferred_sources: List[str] = field(default_factory=list)
    content_quality: str = "balanced"  # low, balanced, high
    auto_summarize: bool = False
    content_warnings: bool = True
    age_restriction: Optional[int] = None

    def is_content_allowed(self, content_type: str, source: Optional[str] = None) -> bool:
        """检查内容是否允许"""
        # 检查内容类型
        if content_type not in self.content_types:
            return False

        # 检查来源
        if source and self.preferred_sources:
            return source in self.preferred_sources

        return True

    def get_filter_strength(self) -> float:
        """获取过滤强度（0-1）"""
        strength_map = {
            ContentFilterLevel.NONE: 0.0,
            ContentFilterLevel.MINIMAL: 0.25,
            ContentFilterLevel.MODERATE: 0.5,
            ContentFilterLevel.STRICT: 0.75,
            ContentFilterLevel.MAXIMUM: 1.0
        }
        return strength_map.get(self.content_filter, 0.5)


@dataclass
class PrivacyPreferences:
    """隐私偏好设置"""
    data_collection: str = "essential"  # none, essential, enhanced, full
    analytics: bool = True
    personalized_ads: bool = False
    data_retention: str = "90_days"  # 7_days, 30_days, 90_days, 1_year, indefinite
    location_sharing: bool = False
    contact_sync: bool = False
    biometric_data: bool = False
    encryption_level: str = "standard"  # basic, standard, enhanced, maximum

    def get_privacy_score(self) -> float:
        """计算隐私分数（0-1，越高越私密）"""
        score = 0.0

        # 数据收集
        collection_map = {"none": 1.0, "essential": 0.75, "enhanced": 0.5, "full": 0.25}
        score += collection_map.get(self.data_collection, 0.5) * 0.3

        # 分析数据
        score += (0 if self.analytics else 1) * 0.2

        # 个性化广告
        score += (0 if self.personalized_ads else 1) * 0.2

        # 数据保留
        retention_map = {"7_days": 1.0, "30_days": 0.75, "90_days": 0.5, "1_year": 0.25, "indefinite": 0.0}
        score += retention_map.get(self.data_retention, 0.5) * 0.3

        return min(score, 1.0)


@dataclass
class NotificationPreferences:
    """通知偏好设置"""
    enabled: bool = True
    sound: bool = True
    desktop: bool = True
    email: bool = False
    push: bool = False
    do_not_disturb: bool = False
    dnd_schedule: Optional[Dict[str, str]] = None  # {"start": "22:00", "end": "08:00"}
    vibration: bool = False
    led_light: bool = False

    # 通知类型
    notification_types: Dict[str, bool] = field(default_factory=lambda: {
        "messages": True,
        "reminders": True,
        "updates": True,
        "promotions": False,
        "system": True,
        "emergency": True
    })

    def should_notify(self, notification_type: str, current_time: Optional[str] = None) -> bool:
        """判断是否应该发送通知"""
        if not self.enabled:
            return False

        if self.do_not_disturb and current_time and self.dnd_schedule:
            # 检查是否在勿扰时段
            start = self.dnd_schedule.get("start", "22:00")
            end = self.dnd_schedule.get("end", "08:00")
            # 简化检查，实际应该解析时间
            pass

        # 检查通知类型
        return self.notification_types.get(notification_type, False)


class PreferencesManager:
    """偏好设置管理器"""

    def __init__(self, user_manager):
        """初始化偏好设置管理器"""
        self.user_manager = user_manager
        self.load_preferences()

    def load_preferences(self):
        """加载所有偏好设置"""
        # 加载语言偏好
        language_data = self.user_manager.get_config("preferences", "language")
        self.language = LanguagePreferences(**language_data)

        # 加载交互偏好
        interaction_data = self.user_manager.get_config("preferences", "interaction")
        self.interaction = InteractionPreferences(**interaction_data)

        # 加载内容偏好
        content_data = self.user_manager.get_config("preferences", "content")
        # 转换set类型
        if "content_types" in content_data and isinstance(content_data["content_types"], list):
            content_data["content_types"] = set(content_data["content_types"])
        self.content = ContentPreferences(**content_data)

        # 加载隐私偏好
        privacy_data = self.user_manager.get_config("preferences", "privacy")
        self.privacy = PrivacyPreferences(**privacy_data)

        # 加载通知偏好
        notification_data = self.user_manager.get_config("preferences", "notifications")
        self.notifications = NotificationPreferences(**notification_data)

    def save_preferences(self):
        """保存所有偏好设置"""
        # 保存语言偏好
        self.user_manager.save_config("preferences", "language", self.language.__dict__)

        # 保存交互偏好
        self.user_manager.save_config("preferences", "interaction", self.interaction.__dict__)

        # 保存内容偏好
        content_dict = self.content.__dict__.copy()
        content_dict["content_types"] = list(content_dict["content_types"])
        self.user_manager.save_config("preferences", "content", content_dict)

        # 保存隐私偏好
        self.user_manager.save_config("preferences", "privacy", self.privacy.__dict__)

        # 保存通知偏好
        self.user_manager.save_config("preferences", "notifications", self.notifications.__dict__)

    def get_localization_settings(self) -> Dict:
        """获取本地化设置"""
        return {
            "language": self.language.primary_language.value,
            "region": self.language.primary_language.value.split("-")[
                -1] if "-" in self.language.primary_language.value else "US",
            "timezone": "auto",
            "currency": "auto",
            "date_format": "auto",
            "time_format": "auto"
        }

    def get_interaction_settings(self) -> Dict:
        """获取交互设置"""
        return {
            "input_method": self.interaction.input_method.value,
            "response_timeout": self.interaction.get_response_timeout(),
            "confirmation_required": self.interaction.confirmation_level != "low",
            "feedback_enabled": self.interaction.feedback_level != "minimal"
        }

    def get_content_filters(self) -> Dict:
        """获取内容过滤器"""
        return {
            "filter_level": self.content.content_filter.value,
            "safe_search": self.content.safe_search,
            "allowed_types": list(self.content.content_types),
            "filter_strength": self.content.get_filter_strength()
        }

    def get_privacy_settings(self) -> Dict:
        """获取隐私设置"""
        return {
            "data_collection": self.privacy.data_collection,
            "analytics_enabled": self.privacy.analytics,
            "personalized_ads": self.privacy.personalized_ads,
            "data_retention_days": self._parse_retention_days(self.privacy.data_retention),
            "privacy_score": self.privacy.get_privacy_score()
        }

    def _parse_retention_days(self, retention_str: str) -> int:
        """解析保留天数"""
        retention_map = {
            "7_days": 7,
            "30_days": 30,
            "90_days": 90,
            "1_year": 365,
            "indefinite": 9999
        }
        return retention_map.get(retention_str, 90)

    def update_notification_settings(self, notification_type: str, enabled: bool):
        """更新通知设置"""
        if notification_type in self.notifications.notification_types:
            self.notifications.notification_types[notification_type] = enabled
            self.save_preferences()

    def add_preferred_source(self, source: str):
        """添加首选来源"""
        if source not in self.content.preferred_sources:
            self.content.preferred_sources.append(source)
            self.save_preferences()

    def set_primary_language(self, language_code: str):
        """设置主要语言"""
        try:
            language = LanguageCode(language_code)
            self.language.primary_language = language
            self.save_preferences()
        except ValueError:
            print(f"不支持的语言代码: {language_code}")


# 导出主要功能
__all__ = [
    'LanguageCode',
    'InputMethod',
    'ContentFilterLevel',
    'PrivacyLevel',
    'LanguagePreferences',
    'InteractionPreferences',
    'ContentPreferences',
    'PrivacyPreferences',
    'NotificationPreferences',
    'PreferencesManager'
]

