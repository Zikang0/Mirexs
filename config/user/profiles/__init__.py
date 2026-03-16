"""
Mirexs 用户画像配置模块
管理用户的个性化设置、学习风格、技能水平、兴趣领域和使用模式
路径: config/user/profiles/
"""

import os
import yaml
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LearningMode(str, Enum):
    """学习模式枚举"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"


class ContentType(str, Enum):
    """内容类型枚举"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    INTERACTIVE = "interactive"
    EXAMPLES = "examples"


class DifficultyLevel(str, Enum):
    """难度级别枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillLevel(int, Enum):
    """技能级别枚举"""
    NOVICE = 1
    BEGINNER = 2
    COMPETENT = 3
    PROFICIENT = 4
    EXPERT = 5


@dataclass
class LearningStyle:
    """学习风格数据结构"""
    visual_preference: float = 0.0
    auditory_preference: float = 0.0
    kinesthetic_preference: float = 0.0
    reading_writing_preference: float = 0.0
    preferred_session_duration: int = 45
    attention_span: int = 5


@dataclass
class SkillAssessment:
    """技能评估数据结构"""
    skill_name: str
    level: SkillLevel
    experience_years: float = 0.0
    last_used: Optional[str] = None
    confidence: float = 0.0


@dataclass
class InterestArea:
    """兴趣领域数据结构"""
    area_name: str
    interest_level: int = 0  # 0-5
    last_explored: Optional[str] = None
    depth: str = "surface"  # surface, moderate, deep


@dataclass
class UsagePattern:
    """使用模式数据结构"""
    pattern_type: str
    frequency: float = 0.0
    context: str = ""
    effectiveness: float = 0.0


@dataclass
class AdaptationRecord:
    """适应记录数据结构"""
    adaptation_type: str
    timestamp: str
    reason: str
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    effectiveness: float = 0.0


class UserProfileConfig:
    """用户画像配置管理器"""

    def __init__(self, config_dir: str = None):
        """
        初始化用户画像配置管理器

        Args:
            config_dir: 配置文件目录，默认为当前目录
        """
        if config_dir is None:
            # 使用当前文件所在目录作为配置目录
            self.config_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.config_dir = config_dir

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

        # 配置文件路径
        self.learning_style_path = os.path.join(self.config_dir, "learning_style.yaml")
        self.skill_level_path = os.path.join(self.config_dir, "skill_level.yaml")
        self.interest_areas_path = os.path.join(self.config_dir, "interest_areas.yaml")
        self.usage_patterns_path = os.path.join(self.config_dir, "usage_patterns.yaml")
        self.adaptation_history_path = os.path.join(self.config_dir, "adaptation_history.yaml")

        # 初始化默认配置
        self._initialize_default_configs()

    def _initialize_default_configs(self):
        """初始化默认配置文件"""
        default_configs = {
            self.learning_style_path: self._get_default_learning_style(),
            self.skill_level_path: self._get_default_skill_level(),
            self.interest_areas_path: self._get_default_interest_areas(),
            self.usage_patterns_path: self._get_default_usage_patterns(),
            self.adaptation_history_path: self._get_default_adaptation_history()
        }

        for path, config in default_configs.items():
            if not os.path.exists(path):
                self._save_yaml(path, config)
                logger.info(f"创建默认配置文件: {path}")

    def _get_default_learning_style(self) -> Dict[str, Any]:
        """获取默认学习风格配置"""
        current_time = datetime.now().isoformat()
        return {
            "preferences": {
                "learning_modes": {
                    "visual": 70,
                    "auditory": 60,
                    "kinesthetic": 50,
                    "reading_writing": 80
                },
                "content_types": {
                    "video": 75,
                    "audio": 65,
                    "text": 85,
                    "interactive": 90,
                    "examples": 88
                },
                "difficulty_levels": {
                    "beginner": 30,
                    "intermediate": 70,
                    "advanced": 60,
                    "expert": 40
                }
            },
            "learning_pace": {
                "preferred_session_duration": 45,
                "breaks_frequency": 15,
                "daily_capacity": 180,
                "preferred_time_slots": ["09:00-11:00", "14:00-16:00", "19:00-21:00"]
            },
            "cognitive_traits": {
                "attention_span": 7,
                "memory_retention": 6,
                "pattern_recognition": 8,
                "abstraction": 5,
                "detail_oriented": 7
            },
            "feedback_preferences": {
                "immediate_feedback": True,
                "detailed_explanations": True,
                "error_correction": "step_by_step",
                "positive_reinforcement": True,
                "progress_tracking": True
            },
            "history": {
                "created_at": current_time,
                "last_updated": current_time,
                "total_learning_sessions": 0,
                "avg_session_duration": 0,
                "most_effective_modes": [],
                "adaptation_count": 0
            }
        }

    def _get_default_skill_level(self) -> Dict[str, Any]:
        """获取默认技能水平配置"""
        current_time = datetime.now().isoformat()
        return {
            "technical_skills": {
                "programming_languages": {},
                "frameworks_and_libraries": {},
                "tools_and_platforms": {}
            },
            "ai_skills": {
                "machine_learning": {},
                "nlp": {},
                "computer_vision": {}
            },
            "soft_skills": {
                "communication": {},
                "problem_solving": {},
                "collaboration": {}
            },
            "skill_assessment": {
                "last_assessment_date": current_time,
                "assessment_method": "initial",
                "confidence_level": 0.5,
                "improvement_areas": [],
                "strengths": []
            },
            "statistics": {
                "total_skills_tracked": 0,
                "avg_skill_level": 0.0,
                "skill_growth_rate": 0.0,
                "last_skill_update": current_time
            }
        }

    def _get_default_interest_areas(self) -> Dict[str, Any]:
        """获取默认兴趣领域配置"""
        current_time = datetime.now().isoformat()
        return {
            "technology_interests": {
                "programming_and_development": {},
                "ai_and_ml": {},
                "infrastructure_and_devops": {}
            },
            "non_technology_interests": {
                "science_and_math": {},
                "arts_and_creativity": {},
                "personal_development": {},
                "hobbies": {}
            },
            "interest_analysis": {
                "interest_clusters": [],
                "interest_stability": {
                    "stable_interests": [],
                    "fluctuating_interests": [],
                    "new_interests": []
                }
            },
            "statistics": {
                "total_interests_tracked": 0,
                "primary_interest_domains": [],
                "interest_diversity_score": 0.0,
                "interest_evolution_rate": 0.0,
                "last_interest_update": current_time
            }
        }

    def _get_default_usage_patterns(self) -> Dict[str, Any]:
        """获取默认使用模式配置"""
        current_time = datetime.now().isoformat()
        return {
            "frequency_patterns": {
                "daily": {
                    "average_sessions": 0,
                    "peak_hours": [],
                    "typical_duration": 0
                },
                "weekly": {
                    "usage_days": [],
                    "weekly_total_hours": 0,
                    "weekly_pattern": "unknown"
                }
            },
            "session_characteristics": {
                "session_length_distribution": {
                    "short_sessions": 0,
                    "medium_sessions": 0,
                    "long_sessions": 0
                }
            },
            "statistics_and_trends": {
                "total_interactions": 0,
                "avg_daily_interactions": 0,
                "usage_trend": "stable",
                "engagement_score": 0.0,
                "loyalty_pattern": "unknown"
            }
        }

    def _get_default_adaptation_history(self) -> Dict[str, Any]:
        """获取默认适应历史配置"""
        current_time = datetime.now().isoformat()
        return {
            "system_config_adaptations": [],
            "content_recommendation_adaptations": [],
            "learning_path_adaptations": [],
            "adaptation_statistics": {
                "total_adaptations": 0,
                "successful_adaptations": 0,
                "failed_adaptations": 0,
                "first_adaptation_date": current_time,
                "latest_adaptation_date": current_time
            }
        }

    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """加载YAML文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"配置文件不存在: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"YAML解析错误: {file_path} - {e}")
            return {}

    def _save_yaml(self, file_path: str, data: Dict[str, Any]):
        """保存到YAML文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"配置文件已保存: {file_path}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {file_path} - {e}")

    def _update_timestamp(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置中的时间戳"""
        current_time = datetime.now().isoformat()

        # 更新根级别的时间戳
        if 'last_updated' in data:
            data['last_updated'] = current_time

        # 更新历史记录中的时间戳
        if 'history' in data and isinstance(data['history'], dict):
            data['history']['last_updated'] = current_time

        return data

    # 学习风格相关方法
    def get_learning_style(self) -> Dict[str, Any]:
        """获取学习风格配置"""
        return self._load_yaml(self.learning_style_path)

    def update_learning_style(self, updates: Dict[str, Any]):
        """更新学习风格配置"""
        current_config = self.get_learning_style()

        # 深度合并更新
        self._deep_update(current_config, updates)

        # 更新统计信息
        if 'history' not in current_config:
            current_config['history'] = {}

        current_config['history']['total_learning_sessions'] = current_config['history'].get('total_learning_sessions',
                                                                                             0) + 1

        # 更新时间戳
        current_config = self._update_timestamp(current_config)

        # 保存配置
        self._save_yaml(self.learning_style_path, current_config)

    def get_preferred_learning_mode(self) -> str:
        """获取偏好的学习模式"""
        config = self.get_learning_style()
        preferences = config.get('preferences', {}).get('learning_modes', {})

        if not preferences:
            return LearningMode.READING_WRITING.value

        # 找到偏好值最高的学习模式
        return max(preferences.items(), key=lambda x: x[1])[0]

    def get_optimal_session_duration(self) -> int:
        """获取最优的单次学习时长"""
        config = self.get_learning_style()
        return config.get('learning_pace', {}).get('preferred_session_duration', 45)

    # 技能水平相关方法
    def get_skill_levels(self) -> Dict[str, Any]:
        """获取技能水平配置"""
        return self._load_yaml(self.skill_level_path)

    def update_skill(self, skill_category: str, skill_name: str, level: int,
                     experience_years: float = None, last_used: str = None):
        """更新技能水平"""
        config = self.get_skill_levels()

        # 确保技能类别存在
        if skill_category not in config:
            config[skill_category] = {}

        # 更新技能信息
        skill_data = {
            'level': level,
            'experience_years': experience_years or 0.0,
            'last_used': last_used or datetime.now().isoformat()
        }

        config[skill_category][skill_name] = skill_data

        # 更新统计信息
        self._update_skill_statistics(config)

        # 保存配置
        self._save_yaml(self.skill_level_path, config)

    def get_skill_gap_analysis(self) -> Dict[str, List[str]]:
        """获取技能缺口分析"""
        config = self.get_skill_levels()
        skill_assessment = config.get('skill_assessment', {})

        return {
            'improvement_areas': skill_assessment.get('improvement_areas', []),
            'strengths': skill_assessment.get('strengths', [])
        }

    def _update_skill_statistics(self, config: Dict[str, Any]):
        """更新技能统计信息"""
        all_skills = []

        # 收集所有技能级别
        for category in ['technical_skills', 'ai_skills', 'soft_skills']:
            if category in config:
                category_data = config[category]
                for subcategory, skills in category_data.items():
                    if isinstance(skills, dict):
                        for skill_name, skill_info in skills.items():
                            if isinstance(skill_info, dict) and 'level' in skill_info:
                                all_skills.append(skill_info['level'])

        # 计算统计信息
        if all_skills:
            avg_skill_level = sum(all_skills) / len(all_skills)
            total_skills_tracked = len(all_skills)
        else:
            avg_skill_level = 0.0
            total_skills_tracked = 0

        # 更新统计
        if 'statistics' not in config:
            config['statistics'] = {}

        config['statistics']['total_skills_tracked'] = total_skills_tracked
        config['statistics']['avg_skill_level'] = round(avg_skill_level, 2)
        config['statistics']['last_skill_update'] = datetime.now().isoformat()

    # 兴趣领域相关方法
    def get_interest_areas(self) -> Dict[str, Any]:
        """获取兴趣领域配置"""
        return self._load_yaml(self.interest_areas_path)

    def update_interest(self, category: str, interest_name: str, interest_level: int,
                        last_explored: str = None):
        """更新兴趣领域"""
        config = self.get_interest_areas()

        # 确保分类存在
        if category not in config:
            config[category] = {}

        # 更新兴趣信息
        interest_data = {
            'interest_level': max(0, min(5, interest_level)),  # 限制在0-5之间
            'last_explored': last_explored or datetime.now().isoformat()
        }

        config[category][interest_name] = interest_data

        # 更新统计信息
        self._update_interest_statistics(config)

        # 保存配置
        self._save_yaml(self.interest_areas_path, config)

    def get_top_interests(self, limit: int = 5) -> List[Tuple[str, int]]:
        """获取最感兴趣的前N个领域"""
        config = self.get_interest_areas()
        all_interests = []

        # 收集所有兴趣
        for category, interests in config.items():
            if isinstance(interests, dict):
                for interest_name, interest_data in interests.items():
                    if isinstance(interest_data, dict) and 'interest_level' in interest_data:
                        all_interests.append((f"{category}.{interest_name}", interest_data['interest_level']))

        # 按兴趣级别排序并返回前N个
        sorted_interests = sorted(all_interests, key=lambda x: x[1], reverse=True)
        return sorted_interests[:limit]

    def _update_interest_statistics(self, config: Dict[str, Any]):
        """更新兴趣统计信息"""
        all_interest_levels = []

        # 收集所有兴趣级别
        for category, interests in config.items():
            if category not in ['statistics', 'interest_analysis', 'exploration_history']:
                if isinstance(interests, dict):
                    for interest_name, interest_data in interests.items():
                        if isinstance(interest_data, dict) and 'interest_level' in interest_data:
                            all_interest_levels.append(interest_data['interest_level'])

        # 计算统计信息
        if all_interest_levels:
            avg_interest_level = sum(all_interest_levels) / len(all_interest_levels)
            total_interests_tracked = len(all_interest_levels)
        else:
            avg_interest_level = 0.0
            total_interests_tracked = 0

        # 更新统计
        if 'statistics' not in config:
            config['statistics'] = {}

        config['statistics']['total_interests_tracked'] = total_interests_tracked
        config['statistics']['interest_diversity_score'] = self._calculate_diversity_score(all_interest_levels)
        config['statistics']['last_interest_update'] = datetime.now().isoformat()

    def _calculate_diversity_score(self, interest_levels: List[int]) -> float:
        """计算兴趣多样性分数"""
        if not interest_levels:
            return 0.0

        # 简单多样性计算：基于标准差和范围
        import statistics
        if len(interest_levels) > 1:
            stdev = statistics.stdev(interest_levels)
            score_range = max(interest_levels) - min(interest_levels)
            diversity = (stdev + score_range / 2) / 10  # 归一化到0-1
            return round(min(1.0, max(0.0, diversity)), 3)
        return 0.0

    # 使用模式相关方法
    def get_usage_patterns(self) -> Dict[str, Any]:
        """获取使用模式配置"""
        return self._load_yaml(self.usage_patterns_path)

    def record_usage_session(self, session_type: str, duration_minutes: int,
                             features_used: List[str], context: str = "general"):
        """记录使用会话"""
        config = self.get_usage_patterns()

        # 更新会话统计
        session_stats = config.setdefault('session_characteristics', {})

        # 会话长度分布
        length_dist = session_stats.setdefault('session_length_distribution', {})
        if duration_minutes < 5:
            length_dist['short_sessions'] = length_dist.get('short_sessions', 0) + 1
        elif duration_minutes < 30:
            length_dist['medium_sessions'] = length_dist.get('medium_sessions', 0) + 1
        else:
            length_dist['long_sessions'] = length_dist.get('long_sessions', 0) + 1

        # 会话类型统计
        session_types = session_stats.setdefault('session_types', {})
        session_types[session_type] = session_types.get(session_type, 0) + 1

        # 更新功能使用统计
        feature_usage = config.setdefault('feature_usage', {})
        most_used = feature_usage.setdefault('most_used_features', [])

        for feature in features_used:
            # 查找是否已记录此功能
            found = False
            for i, item in enumerate(most_used):
                if item.get('feature') == feature:
                    most_used[i]['usage_count'] = item.get('usage_count', 0) + 1
                    most_used[i]['last_used'] = datetime.now().isoformat()
                    found = True
                    break

            # 如果未找到，添加新记录
            if not found:
                most_used.append({
                    'feature': feature,
                    'usage_count': 1,
                    'last_used': datetime.now().isoformat()
                })

        # 按使用次数排序
        if most_used:
            most_used.sort(key=lambda x: x.get('usage_count', 0), reverse=True)
            feature_usage['most_used_features'] = most_used[:10]  # 只保留前10个

        # 更新频率模式
        freq_patterns = config.setdefault('frequency_patterns', {})
        daily_stats = freq_patterns.setdefault('daily', {})
        daily_stats['average_sessions'] = daily_stats.get('average_sessions', 0) + 1

        # 更新总统计
        stats = config.setdefault('statistics_and_trends', {})
        stats['total_interactions'] = stats.get('total_interactions', 0) + 1

        # 保存配置
        self._save_yaml(self.usage_patterns_path, config)

    def get_engagement_score(self) -> float:
        """计算用户参与度分数"""
        config = self.get_usage_patterns()
        stats = config.get('statistics_and_trends', {})

        total_interactions = stats.get('total_interactions', 0)
        avg_daily = stats.get('avg_daily_interactions', 0)

        # 简单的参与度计算公式
        if total_interactions > 0 and avg_daily > 0:
            engagement = min(1.0, (total_interactions * 0.1 + avg_daily * 0.5) / 10)
            return round(engagement, 3)
        return 0.0

    # 适应历史相关方法
    def get_adaptation_history(self) -> Dict[str, Any]:
        """获取适应历史配置"""
        return self._load_yaml(self.adaptation_history_path)

    def record_adaptation(self, adaptation_type: str, reason: str,
                          previous_state: Dict[str, Any], new_state: Dict[str, Any],
                          effectiveness: float = 0.0):
        """记录系统适应事件"""
        config = self.get_adaptation_history()

        # 获取适应记录列表
        adaptation_list = config.setdefault(f"{adaptation_type}_adaptations", [])

        # 创建新的适应记录
        adaptation_record = {
            'date': datetime.now().isoformat(),
            'adaptation_type': adaptation_type,
            'reason': reason,
            'previous_state': previous_state,
            'new_state': new_state,
            'effectiveness': effectiveness,
            'user_feedback': ""
        }

        adaptation_list.append(adaptation_record)

        # 更新适应统计
        stats = config.setdefault('adaptation_statistics', {})
        stats['total_adaptations'] = stats.get('total_adaptations', 0) + 1

        if effectiveness > 0.7:  # 认为效果良好的适应
            stats['successful_adaptations'] = stats.get('successful_adaptations', 0) + 1
        elif effectiveness < 0.3:  # 认为效果不佳的适应
            stats['failed_adaptations'] = stats.get('failed_adaptations', 0) + 1

        stats['latest_adaptation_date'] = datetime.now().isoformat()

        # 保存配置
        self._save_yaml(self.adaptation_history_path, config)

        logger.info(f"记录适应事件: {adaptation_type} - {reason}")

    def get_adaptation_effectiveness(self) -> Dict[str, float]:
        """获取适应效果统计"""
        config = self.get_adaptation_history()
        stats = config.get('adaptation_statistics', {})

        total = stats.get('total_adaptations', 0)
        successful = stats.get('successful_adaptations', 0)
        failed = stats.get('failed_adaptations', 0)

        if total > 0:
            success_rate = successful / total
            failure_rate = failed / total
        else:
            success_rate = 0.0
            failure_rate = 0.0

        return {
            'total_adaptations': total,
            'success_rate': round(success_rate, 3),
            'failure_rate': round(failure_rate, 3),
            'pending_evaluations': total - successful - failed
        }

    # 工具方法
    def _deep_update(self, original: Dict[str, Any], updates: Dict[str, Any]):
        """深度更新字典"""
        for key, value in updates.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value

    def get_comprehensive_profile(self) -> Dict[str, Any]:
        """获取完整的用户画像摘要"""
        return {
            'learning_style': self.get_learning_style_summary(),
            'skill_summary': self.get_skill_summary(),
            'interest_summary': self.get_interest_summary(),
            'usage_summary': self.get_usage_summary(),
            'adaptation_summary': self.get_adaptation_summary(),
            'personalization_score': self.calculate_personalization_score()
        }

    def get_learning_style_summary(self) -> Dict[str, Any]:
        """获取学习风格摘要"""
        config = self.get_learning_style()
        prefs = config.get('preferences', {}).get('learning_modes', {})

        return {
            'preferred_mode': self.get_preferred_learning_mode(),
            'optimal_session_duration': self.get_optimal_session_duration(),
            'attention_span': config.get('cognitive_traits', {}).get('attention_span', 5),
            'total_sessions': config.get('history', {}).get('total_learning_sessions', 0)
        }

    def get_skill_summary(self) -> Dict[str, Any]:
        """获取技能水平摘要"""
        config = self.get_skill_levels()
        stats = config.get('statistics', {})

        return {
            'total_skills': stats.get('total_skills_tracked', 0),
            'average_level': stats.get('avg_skill_level', 0.0),
            'improvement_areas': config.get('skill_assessment', {}).get('improvement_areas', []),
            'strengths': config.get('skill_assessment', {}).get('strengths', [])
        }

    def get_interest_summary(self) -> Dict[str, Any]:
        """获取兴趣领域摘要"""
        top_interests = self.get_top_interests(5)

        return {
            'top_interests': [interest[0] for interest in top_interests],
            'top_interest_levels': [interest[1] for interest in top_interests],
            'diversity_score': self.get_interest_areas().get('statistics', {}).get('interest_diversity_score', 0.0)
        }

    def get_usage_summary(self) -> Dict[str, Any]:
        """获取使用模式摘要"""
        config = self.get_usage_patterns()
        stats = config.get('statistics_and_trends', {})

        return {
            'total_interactions': stats.get('total_interactions', 0),
            'engagement_score': self.get_engagement_score(),
            'usage_trend': stats.get('usage_trend', 'stable'),
            'most_used_features': config.get('feature_usage', {}).get('most_used_features', [])[:3]
        }

    def get_adaptation_summary(self) -> Dict[str, Any]:
        """获取适应历史摘要"""
        effectiveness = self.get_adaptation_effectiveness()

        return {
            'total_adaptations': effectiveness['total_adaptations'],
            'success_rate': effectiveness['success_rate'],
            'adaptation_frequency': 'unknown'  # 可以进一步计算
        }

    def calculate_personalization_score(self) -> float:
        """计算个性化程度分数"""
        scores = []

        # 学习风格个性化分数
        learning_config = self.get_learning_style()
        if learning_config.get('history', {}).get('adaptation_count', 0) > 0:
            scores.append(0.2)  # 有适应记录

        # 技能跟踪分数
        skill_config = self.get_skill_levels()
        if skill_config.get('statistics', {}).get('total_skills_tracked', 0) > 5:
            scores.append(0.2)

        # 兴趣跟踪分数
        interest_config = self.get_interest_areas()
        if interest_config.get('statistics', {}).get('total_interests_tracked', 0) > 10:
            scores.append(0.2)

        # 使用模式分析分数
        usage_config = self.get_usage_patterns()
        if usage_config.get('statistics_and_trends', {}).get('total_interactions', 0) > 50:
            scores.append(0.2)

        # 适应历史分数
        adaptation_config = self.get_adaptation_history()
        if adaptation_config.get('adaptation_statistics', {}).get('total_adaptations', 0) > 10:
            scores.append(0.2)

        return round(sum(scores), 3)

    def export_profile_json(self, export_path: str = None):
        """导出用户画像为JSON格式"""
        if export_path is None:
            export_path = os.path.join(self.config_dir, "user_profile_export.json")

        profile_data = self.get_comprehensive_profile()

        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
            logger.info(f"用户画像已导出到: {export_path}")
            return export_path
        except Exception as e:
            logger.error(f"导出用户画像失败: {e}")
            return None

    def reset_profile(self, keep_history: bool = False):
        """重置用户画像（用于测试或隐私保护）"""
        if keep_history:
            # 只重置配置，保留历史记录
            self._initialize_default_configs()
            logger.info("用户画像已重置（保留历史记录）")
        else:
            # 删除所有配置文件并重新初始化
            for file_path in [
                self.learning_style_path,
                self.skill_level_path,
                self.interest_areas_path,
                self.usage_patterns_path,
                self.adaptation_history_path
            ]:
                if os.path.exists(file_path):
                    os.remove(file_path)

            self._initialize_default_configs()
            logger.info("用户画像已完全重置")


# Pydantic模型定义
try:
    from pydantic import BaseModel, Field, validator


    class UserProfileModel(BaseModel):
        """用户画像Pydantic模型"""
        user_id: str = Field(..., description="用户唯一标识")
        learning_style: Dict[str, Any] = Field(default_factory=dict, description="学习风格配置")
        skill_levels: Dict[str, Any] = Field(default_factory=dict, description="技能水平配置")
        interest_areas: Dict[str, Any] = Field(default_factory=dict, description="兴趣领域配置")
        usage_patterns: Dict[str, Any] = Field(default_factory=dict, description="使用模式配置")
        adaptation_history: Dict[str, Any] = Field(default_factory=dict, description="适应历史配置")
        created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
        updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

except ImportError:
    logger.warning("pydantic未安装，UserProfileModel不可用")
    UserProfileModel = None

# 单例模式，确保全局只有一个配置管理器实例
_profile_manager = None


def get_profile_manager(config_dir: str = None) -> UserProfileConfig:
    """
    获取用户画像配置管理器实例（单例模式）

    Args:
        config_dir: 配置文件目录

    Returns:
        UserProfileConfig实例
    """
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = UserProfileConfig(config_dir)
    return _profile_manager


def create_default_profile(user_id: str) -> Dict[str, Any]:
    """
    创建默认用户画像

    Args:
        user_id: 用户ID

    Returns:
        默认用户画像数据
    """
    manager = get_profile_manager()

    # 创建默认配置
    if UserProfileModel is not None:
        profile = UserProfileModel(
            user_id=user_id,
            learning_style=manager._get_default_learning_style(),
            skill_levels=manager._get_default_skill_level(),
            interest_areas=manager._get_default_interest_areas(),
            usage_patterns=manager._get_default_usage_patterns(),
            adaptation_history=manager._get_default_adaptation_history()
        )

        return profile.dict()
    else:
        return {
            'user_id': user_id,
            'learning_style': manager._get_default_learning_style(),
            'skill_levels': manager._get_default_skill_level(),
            'interest_areas': manager._get_default_interest_areas(),
            'usage_patterns': manager._get_default_usage_patterns(),
            'adaptation_history': manager._get_default_adaptation_history(),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }


# 模块导出
__all__ = [
    'UserProfileConfig',
    'UserProfileModel',
    'LearningStyle',
    'SkillAssessment',
    'InterestArea',
    'UsagePattern',
    'AdaptationRecord',
    'get_profile_manager',
    'create_default_profile',
    'LearningMode',
    'ContentType',
    'DifficultyLevel',
    'SkillLevel'
]

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("Mirexs 用户画像配置模块测试")
    print("=" * 60)

    manager = get_profile_manager()

    # 测试获取配置
    print("\n1. 获取当前用户画像配置...")
    profile_summary = manager.get_comprehensive_profile()
    print(f"   个性化分数: {profile_summary['personalization_score']}")
    print(f"   学习偏好: {profile_summary['learning_style']['preferred_mode']}")

    # 测试更新技能
    print("\n2. 更新技能水平...")
    manager.update_skill(
        skill_category="technical_skills.programming_languages",
        skill_name="python",
        level=4,
        experience_years=3.5
    )
    print("   技能已更新")

    # 测试记录使用
    print("\n3. 记录使用会话...")
    manager.record_usage_session(
        session_type="learning",
        duration_minutes=45,
        features_used=["voice_assistant", "document_reader"],
        context="study"
    )
    print("   使用会话已记录")

    # 导出用户画像
    print("\n4. 导出用户画像...")
    export_path = manager.export_profile_json()
    if export_path:
        print(f"   用户画像已导出到: {export_path}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

