# communication
# 通信与网络
# 创建时间: 2025-10-24 11:07:30
# config/user/__init__.py
"""
用户配置模块
管理所有用户级别的个性化配置，包括个性化设置、用户偏好和用户画像
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import yaml

from ..system import config_manager


class UserConfigError(Exception):
    """用户配置相关异常"""
    pass


class PreferenceLevel(Enum):
    """偏好级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REQUIRED = "required"


@dataclass
class UserProfile:
    """用户画像数据类"""
    user_id: str
    username: str
    email: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 统计信息
    total_sessions: int = 0
    total_interactions: int = 0
    total_tasks_completed: int = 0

    # 使用时长
    total_usage_hours: float = 0.0
    average_session_minutes: float = 0.0

    # 活跃度
    last_active: Optional[datetime] = None
    is_active: bool = False

    def update(self, **kwargs):
        """更新用户信息"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 处理datetime对象
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'UserProfile':
        """从字典创建"""
        # 处理datetime字符串
        datetime_fields = ['created_at', 'updated_at', 'last_active']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)


class UserConfigManager:
    """用户配置管理器"""

    def __init__(self, user_id: Optional[str] = None):
        """初始化用户配置管理器

        Args:
            user_id: 用户ID，如果为None则使用默认用户
        """
        self.user_id = user_id or "default"
        self.user_dir = self._get_user_config_dir()
        self.profile = self._load_user_profile()

        # 确保用户目录存在
        self.user_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_config_dir(self) -> Path:
        """获取用户配置目录"""
        # 从系统配置获取基础路径
        system_config = config_manager.get_system_config()
        user_data_dir = system_config.get('paths', {}).get('user_data_dir', 'data/users')

        # 构建用户特定目录
        user_dir = Path(user_data_dir) / self.user_id / "config"
        return user_dir

    def _load_user_profile(self) -> UserProfile:
        """加载用户画像"""
        profile_file = self.user_dir.parent / "profile.json"

        if profile_file.exists():
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return UserProfile.from_dict(data)
            except Exception as e:
                print(f"加载用户画像失败: {e}")

        # 创建默认用户画像
        return UserProfile(
            user_id=self.user_id,
            username=f"User_{self.user_id[:8]}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def save_user_profile(self):
        """保存用户画像"""
        profile_file = self.user_dir.parent / "profile.json"

        try:
            profile_file.parent.mkdir(parents=True, exist_ok=True)
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(self.profile.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise UserConfigError(f"保存用户画像失败: {e}")

    def get_config(self, config_type: str, config_name: str) -> Dict:
        """获取用户配置

        Args:
            config_type: 配置类型，如 'personalization', 'preferences', 'profiles'
            config_name: 配置文件名（不含扩展名）

        Returns:
            Dict: 配置字典
        """
        config_path = self.user_dir / config_type / f"{config_name}.yaml"

        if not config_path.exists():
            # 返回默认配置
            return self.get_default_config(config_type, config_name)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except Exception as e:
            print(f"加载用户配置失败 {config_path}: {e}")
            return self.get_default_config(config_type, config_name)

    def save_config(self, config_type: str, config_name: str, config: Dict):
        """保存用户配置

        Args:
            config_type: 配置类型
            config_name: 配置文件名
            config: 配置字典
        """
        config_dir = self.user_dir / config_type
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = config_dir / f"{config_name}.yaml"

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
        except Exception as e:
            raise UserConfigError(f"保存用户配置失败 {config_path}: {e}")

    def get_default_config(self, config_type: str, config_name: str) -> Dict:
        """获取默认配置

        Args:
            config_type: 配置类型
            config_name: 配置文件名

        Returns:
            Dict: 默认配置字典
        """
        # 内置默认配置
        defaults = {
            "personalization": {
                "appearance": {
                    "theme": "auto",
                    "font_size": "medium",
                    "animation_speed": "normal",
                    "avatar_size": "medium",
                    "ui_density": "comfortable"
                },
                "behavior": {
                    "auto_start": False,
                    "minimize_to_tray": True,
                    "confirm_exit": True,
                    "save_session": True
                },
                "shortcuts": {
                    "activate_app": "Ctrl+Shift+M",
                    "mute_microphone": "Ctrl+Shift+S",
                    "screenshot": "Ctrl+Shift+P",
                    "quick_note": "Ctrl+Shift+N"
                },
                "themes": {
                    "active_theme": "default",
                    "custom_colors": {},
                    "dark_mode": "auto"
                },
                "accessibility": {
                    "screen_reader": False,
                    "high_contrast": False,
                    "reduce_motion": False,
                    "text_to_speech": False
                }
            },
            "preferences": {
                "language": {
                    "primary": "zh-CN",
                    "secondary": "en-US",
                    "auto_translate": True,
                    "translation_target": "primary"
                },
                "interaction": {
                    "input_method": "voice_primary",
                    "response_speed": "balanced",
                    "confirmation_level": "medium",
                    "feedback_level": "detailed"
                },
                "content": {
                    "content_filter": "moderate",
                    "safe_search": True,
                    "content_types": ["text", "image", "video"],
                    "preferred_sources": []
                },
                "privacy": {
                    "data_collection": "essential",
                    "analytics": True,
                    "personalized_ads": False,
                    "data_retention": "90_days"
                },
                "notifications": {
                    "enabled": True,
                    "sound": True,
                    "desktop": True,
                    "email": False,
                    "push": False
                }
            },
            "profiles": {
                "learning_style": {
                    "visual": 0.7,
                    "auditory": 0.5,
                    "kinesthetic": 0.3,
                    "reading_writing": 0.6
                },
                "skill_level": {
                    "technical": "intermediate",
                    "creative": "beginner",
                    "analytical": "advanced",
                    "social": "intermediate"
                },
                "interest_areas": {
                    "technology": 0.9,
                    "science": 0.7,
                    "arts": 0.5,
                    "sports": 0.3,
                    "business": 0.6
                },
                "usage_patterns": {
                    "peak_hours": [9, 14, 20],
                    "average_session_minutes": 30,
                    "preferred_devices": ["desktop"],
                    "common_tasks": ["research", "writing", "coding"]
                },
                "adaptation_history": {
                    "last_adaptation": None,
                    "adaptation_count": 0,
                    "success_rate": 0.0,
                    "recent_changes": []
                }
            }
        }

        # 获取默认配置
        if config_type in defaults and config_name in defaults[config_type]:
            return defaults[config_type][config_name]
        else:
            return {}

    def get_all_configs(self) -> Dict[str, Dict]:
        """获取所有用户配置"""
        configs = {}

        # 遍历所有配置类型
        for config_type in ["personalization", "preferences", "profiles"]:
            configs[config_type] = {}
            config_dir = self.user_dir / config_type

            if config_dir.exists():
                for config_file in config_dir.glob("*.yaml"):
                    config_name = config_file.stem
                    configs[config_type][config_name] = self.get_config(config_type, config_name)
            else:
                # 使用默认配置
                for config_name in self.get_default_config(config_type, {}).keys():
                    configs[config_type][config_name] = self.get_config(config_type, config_name)

        return configs

    def update_profile_statistics(self, session_duration: float = 0,
                                  interactions: int = 0,
                                  tasks_completed: int = 0):
        """更新用户画像统计信息

        Args:
            session_duration: 会话时长（分钟）
            interactions: 交互次数
            tasks_completed: 完成的任务数
        """
        self.profile.total_sessions += 1
        self.profile.total_interactions += interactions
        self.profile.total_tasks_completed += tasks_completed
        self.profile.total_usage_hours += session_duration / 60

        # 计算平均会话时长
        if self.profile.total_sessions > 0:
            self.profile.average_session_minutes = (
                    self.profile.total_usage_hours * 60 / self.profile.total_sessions
            )

        self.profile.last_active = datetime.now()
        self.profile.is_active = True

        self.save_user_profile()

    def get_preference_score(self, category: str, item: str) -> float:
        """获取偏好分数

        Args:
            category: 偏好类别，如 'content', 'interaction'
            item: 具体偏好项

        Returns:
            float: 偏好分数（0-1）
        """
        preferences = self.get_config("preferences", category)

        if category == "content" and item == "content_types":
            # 内容类型偏好
            enabled_types = preferences.get(item, [])
            return len(enabled_types) / 4  # 假设有4种内容类型

        elif category == "interaction" and item == "response_speed":
            # 响应速度偏好
            speed = preferences.get(item, "balanced")
            speed_map = {"slow": 0.3, "balanced": 0.5, "fast": 0.8, "instant": 1.0}
            return speed_map.get(speed, 0.5)

        return 0.5  # 默认分数

    def export_config(self, export_path: Path) -> bool:
        """导出用户配置

        Args:
            export_path: 导出路径

        Returns:
            bool: 是否成功
        """
        try:
            export_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "user_id": self.user_id,
                    "version": "2.0.0"
                },
                "profile": self.profile.to_dict(),
                "configs": self.get_all_configs()
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"导出用户配置失败: {e}")
            return False

    def import_config(self, import_path: Path) -> bool:
        """导入用户配置

        Args:
            import_path: 导入路径

        Returns:
            bool: 是否成功
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # 导入用户画像
            if "profile" in import_data:
                self.profile = UserProfile.from_dict(import_data["profile"])
                self.save_user_profile()

            # 导入配置
            if "configs" in import_data:
                configs = import_data["configs"]
                for config_type, type_configs in configs.items():
                    for config_name, config in type_configs.items():
                        self.save_config(config_type, config_name, config)

            return True
        except Exception as e:
            print(f"导入用户配置失败: {e}")
            return False


# 全局用户配置管理器实例（默认用户）
default_user_manager = UserConfigManager()

__all__ = [
    'UserConfigError',
    'PreferenceLevel',
    'UserProfile',
    'UserConfigManager',
    'default_user_manager'
]

