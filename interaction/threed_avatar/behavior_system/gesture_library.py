"""
手势库：存储和管理手势动画
负责3D虚拟猫咪手势动画的存储、管理和检索
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio

# 导入依赖模块
from data.models.three_d.animations import AnimationClip, AnimationConfig

class GestureCategory(Enum):
    """手势类别枚举"""
    GREETING = "greeting"  # 问候手势
    AFFIRMATIVE = "affirmative"  # 肯定手势
    NEGATIVE = "negative"  # 否定手势
    EXPRESSIVE = "expressive"  # 表达性手势
    FUNCTIONAL = "functional"  # 功能性手势
    IDLE = "idle"  # 空闲手势
    EMOTIONAL = "emotional"  # 情感手势

class GestureComplexity(Enum):
    """手势复杂度枚举"""
    SIMPLE = "simple"  # 简单手势
    MODERATE = "moderate"  # 中等复杂度
    COMPLEX = "complex"  # 复杂手势

@dataclass
class GestureDefinition:
    """手势定义"""
    gesture_id: str
    name: str
    category: GestureCategory
    complexity: GestureComplexity
    description: str
    emotional_context: List[str]  # 适用的情感上下文
    duration: float  # 手势持续时间（秒）
    intensity_range: Tuple[float, float]  # 强度范围
    body_parts: List[str]  # 涉及的身体部位
    animation_clip: Optional[AnimationClip] = None
    usage_count: int = 0
    success_rate: float = 1.0  # 手势成功率

class GestureLibrary:
    """手势库：存储和管理手势动画"""
    
    def __init__(self, library_path: str = "./data/gestures"):
        self.library_path = library_path
        self.logger = self._setup_logger()
        
        # 手势存储
        self.gestures: Dict[str, GestureDefinition] = {}
        self.gesture_categories: Dict[GestureCategory, List[str]] = {}
        
        # 手势序列
        self.gesture_sequences: Dict[str, List[str]] = {}
        
        # 使用统计
        self.usage_stats = {
            "total_gestures_used": 0,
            "category_usage": {category.value: 0 for category in GestureCategory},
            "successful_gestures": 0,
            "failed_gestures": 0
        }
        
        # 手势优先级
        self.gesture_priorities: Dict[str, float] = {}
        
        # 初始化手势库
        self._initialize_gesture_library()
        
        # 加载现有手势
        self._load_gesture_library()
        
        self.logger.info(f"手势库初始化完成，共加载 {len(self.gestures)} 个手势")
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("GestureLibrary")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_gesture_library(self):
        """初始化基础手势库"""
        # 创建基础手势定义
        base_gestures = [
            # 问候手势
            GestureDefinition(
                gesture_id="wave_hello",
                name="挥手问候",
                category=GestureCategory.GREETING,
                complexity=GestureComplexity.SIMPLE,
                description="友好的挥手问候手势",
                emotional_context=["happy", "friendly", "excited"],
                duration=2.0,
                intensity_range=(0.6, 0.9),
                body_parts=["right_arm", "right_hand"]
            ),
            GestureDefinition(
                gesture_id="nod_greeting",
                name="点头问候",
                category=GestureCategory.GREETING,
                complexity=GestureComplexity.SIMPLE,
                description="轻微的点头问候",
                emotional_context=["neutral", "friendly", "respectful"],
                duration=1.0,
                intensity_range=(0.3, 0.6),
                body_parts=["head", "neck"]
            ),
            
            # 肯定手势
            GestureDefinition(
                gesture_id="nod_yes",
                name="肯定点头",
                category=GestureCategory.AFFIRMATIVE,
                complexity=GestureComplexity.SIMPLE,
                description="表示同意或肯定的点头",
                emotional_context=["agreeing", "understanding", "positive"],
                duration=1.5,
                intensity_range=(0.5, 0.8),
                body_parts=["head", "neck"]
            ),
            GestureDefinition(
                gesture_id="thumbs_up",
                name="竖起大拇指",
                category=GestureCategory.AFFIRMATIVE,
                complexity=GestureComplexity.SIMPLE,
                description="竖起大拇指表示赞许",
                emotional_context=["happy", "proud", "approving"],
                duration=2.0,
                intensity_range=(0.7, 1.0),
                body_parts=["right_hand", "right_arm"]
            ),
            
            # 否定手势
            GestureDefinition(
                gesture_id="shake_no",
                name="摇头否定",
                category=GestureCategory.NEGATIVE,
                complexity=GestureComplexity.SIMPLE,
                description="摇头表示不同意或否定",
                emotional_context=["disagreeing", "confused", "negative"],
                duration=1.5,
                intensity_range=(0.5, 0.8),
                body_parts=["head", "neck"]
            ),
            GestureDefinition(
                gesture_id="paw_wave_no",
                name="爪子摆动否定",
                category=GestureCategory.NEGATIVE,
                complexity=GestureComplexity.MODERATE,
                description="用爪子摆动表示不同意",
                emotional_context=["annoyed", "impatient", "refusing"],
                duration=1.0,
                intensity_range=(0.6, 0.9),
                body_parts=["right_paw", "right_arm"]
            ),
            
            # 表达性手势
            GestureDefinition(
                gesture_id="thinking_chin",
                name="托腮思考",
                category=GestureCategory.EXPRESSIVE,
                complexity=GestureComplexity.MODERATE,
                description="托着腮帮子思考的姿态",
                emotional_context=["thinking", "curious", "pondering"],
                duration=3.0,
                intensity_range=(0.4, 0.7),
                body_parts=["right_paw", "head", "neck"]
            ),
            GestureDefinition(
                gesture_id="excited_jump",
                name="兴奋跳跃",
                category=GestureCategory.EXPRESSIVE,
                complexity=GestureComplexity.COMPLEX,
                description="兴奋时的跳跃动作",
                emotional_context=["excited", "happy", "surprised"],
                duration=1.5,
                intensity_range=(0.8, 1.0),
                body_parts=["all_limbs", "body", "tail"]
            ),
            
            # 功能性手势
            GestureDefinition(
                gesture_id="point_at_object",
                name="指向物体",
                category=GestureCategory.FUNCTIONAL,
                complexity=GestureComplexity.SIMPLE,
                description="用爪子指向特定物体",
                emotional_context=["directing", "showing", "explaining"],
                duration=2.0,
                intensity_range=(0.5, 0.8),
                body_parts=["right_paw", "right_arm", "head"]
            ),
            GestureDefinition(
                gesture_id="beckon_come",
                name="招手过来",
                category=GestureCategory.FUNCTIONAL,
                complexity=GestureComplexity.SIMPLE,
                description="招手示意靠近",
                emotional_context=["inviting", "calling", "friendly"],
                duration=1.5,
                intensity_range=(0.6, 0.9),
                body_parts=["right_paw", "right_arm"]
            ),
            
            # 空闲手势
            GestureDefinition(
                gesture_id="tail_sway_idle",
                name="尾巴摆动空闲",
                category=GestureCategory.IDLE,
                complexity=GestureComplexity.SIMPLE,
                description="空闲时尾巴的自然摆动",
                emotional_context=["neutral", "relaxed", "content"],
                duration=4.0,
                intensity_range=(0.2, 0.4),
                body_parts=["tail"]
            ),
            GestureDefinition(
                gesture_id="stretch_idle",
                name="伸展空闲",
                category=GestureCategory.IDLE,
                complexity=GestureComplexity.MODERATE,
                description="空闲时的伸展动作",
                emotional_context=["relaxed", "comfortable", "sleepy"],
                duration=3.0,
                intensity_range=(0.3, 0.6),
                body_parts=["front_limbs", "back_limbs", "body"]
            ),
            
            # 情感手势
            GestureDefinition(
                gesture_id="hug_self_comfort",
                name="自我拥抱安慰",
                category=GestureCategory.EMOTIONAL,
                complexity=GestureComplexity.MODERATE,
                description="自我拥抱表示需要安慰",
                emotional_context=["sad", "lonely", "needing_comfort"],
                duration=3.0,
                intensity_range=(0.5, 0.8),
                body_parts=["both_arms", "body"]
            ),
            GestureDefinition(
                gesture_id="paw_over_heart",
                name="爪子放在心上",
                category=GestureCategory.EMOTIONAL,
                complexity=GestureComplexity.SIMPLE,
                description="爪子放在胸前表示真诚",
                emotional_context=["sincere", "grateful", "emotional"],
                duration=2.0,
                intensity_range=(0.6, 0.9),
                body_parts=["right_paw", "chest"]
            )
        ]
        
        # 添加到手势库
        for gesture in base_gestures:
            self.add_gesture(gesture)
    
    def _load_gesture_library(self):
        """从文件加载手势库"""
        library_file = os.path.join(self.library_path, "gesture_library.json")
        stats_file = os.path.join(self.library_path, "gesture_stats.json")
        
        try:
            if os.path.exists(library_file):
                with open(library_file, 'r', encoding='utf-8') as f:
                    gesture_data = json.load(f)
                
                for gesture_id, data in gesture_data.items():
                    # 转换数据为GestureDefinition对象
                    gesture = GestureDefinition(
                        gesture_id=gesture_id,
                        name=data['name'],
                        category=GestureCategory(data['category']),
                        complexity=GestureComplexity(data['complexity']),
                        description=data['description'],
                        emotional_context=data['emotional_context'],
                        duration=data['duration'],
                        intensity_range=tuple(data['intensity_range']),
                        body_parts=data['body_parts'],
                        usage_count=data.get('usage_count', 0),
                        success_rate=data.get('success_rate', 1.0)
                    )
                    
                    # 加载动画剪辑
                    animation_path = os.path.join(self.library_path, f"{gesture_id}.anim")
                    if os.path.exists(animation_path):
                        animation_config = AnimationConfig(
                            name=gesture_id,
                            duration=gesture.duration,
                            fps=30,
                            loop=False
                        )
                        animation_clip = AnimationClip(animation_config)
                        if animation_clip.load_from_file(animation_path):
                            gesture.animation_clip = animation_clip
                    
                    self.gestures[gesture_id] = gesture
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    self.usage_stats = json.load(f)
            
            self.logger.info(f"手势库加载成功，共 {len(self.gestures)} 个手势")
            
        except Exception as e:
            self.logger.error(f"加载手势库失败: {e}")
    
    def save_gesture_library(self):
        """保存手势库到文件"""
        os.makedirs(self.library_path, exist_ok=True)
        
        try:
            # 保存手势数据
            library_file = os.path.join(self.library_path, "gesture_library.json")
            gesture_data = {}
            
            for gesture_id, gesture in self.gestures.items():
                gesture_data[gesture_id] = {
                    'name': gesture.name,
                    'category': gesture.category.value,
                    'complexity': gesture.complexity.value,
                    'description': gesture.description,
                    'emotional_context': gesture.emotional_context,
                    'duration': gesture.duration,
                    'intensity_range': list(gesture.intensity_range),
                    'body_parts': gesture.body_parts,
                    'usage_count': gesture.usage_count,
                    'success_rate': gesture.success_rate
                }
                
                # 保存动画数据
                if gesture.animation_clip:
                    animation_path = os.path.join(self.library_path, f"{gesture_id}.anim")
                    gesture.animation_clip.save_to_file(animation_path)
            
            with open(library_file, 'w', encoding='utf-8') as f:
                json.dump(gesture_data, f, ensure_ascii=False, indent=2)
            
            # 保存使用统计
            stats_file = os.path.join(self.library_path, "gesture_stats.json")
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.usage_stats, f, ensure_ascii=False, indent=2)
            
            self.logger.info("手势库保存成功")
            
        except Exception as e:
            self.logger.error(f"保存手势库失败: {e}")
    
    def add_gesture(self, gesture: GestureDefinition) -> bool:
        """
        添加新手势到库中
        
        Args:
            gesture: 手势定义
            
        Returns:
            是否添加成功
        """
        try:
            self.gestures[gesture.gesture_id] = gesture
            
            # 更新类别索引
            if gesture.category not in self.gesture_categories:
                self.gesture_categories[gesture.category] = []
            
            if gesture.gesture_id not in self.gesture_categories[gesture.category]:
                self.gesture_categories[gesture.category].append(gesture.gesture_id)
            
            # 初始化优先级
            self.gesture_priorities[gesture.gesture_id] = 1.0
            
            self.logger.info(f"手势添加成功: {gesture.name} ({gesture.gesture_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"添加手势失败: {e}")
            return False
    
    def remove_gesture(self, gesture_id: str) -> bool:
        """
        从库中移除手势
        
        Args:
            gesture_id: 手势ID
            
        Returns:
            是否移除成功
        """
        if gesture_id not in self.gestures:
            self.logger.warning(f"手势不存在: {gesture_id}")
            return False
        
        try:
            gesture = self.gestures[gesture_id]
            
            # 从类别索引中移除
            if gesture.category in self.gesture_categories:
                if gesture_id in self.gesture_categories[gesture.category]:
                    self.gesture_categories[gesture.category].remove(gesture_id)
            
            # 从优先级中移除
            if gesture_id in self.gesture_priorities:
                del self.gesture_priorities[gesture_id]
            
            # 从手势库中移除
            del self.gestures[gesture_id]
            
            self.logger.info(f"手势移除成功: {gesture_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"移除手势失败: {e}")
            return False
    
    def get_gesture(self, gesture_id: str) -> Optional[GestureDefinition]:
        """
        获取手势定义
        
        Args:
            gesture_id: 手势ID
            
        Returns:
            手势定义，如果不存在则返回None
        """
        return self.gestures.get(gesture_id)
    
    def find_gestures_by_context(self, emotional_context: List[str], 
                               category: Optional[GestureCategory] = None,
                               complexity: Optional[GestureComplexity] = None,
                               max_duration: Optional[float] = None) -> List[GestureDefinition]:
        """
        根据上下文查找合适的手势
        
        Args:
            emotional_context: 情感上下文
            category: 手势类别过滤
            complexity: 手势复杂度过滤
            max_duration: 最大持续时间
            
        Returns:
            匹配的手势列表
        """
        matching_gestures = []
        
        for gesture in self.gestures.values():
            # 检查类别
            if category is not None and gesture.category != category:
                continue
            
            # 检查复杂度
            if complexity is not None and gesture.complexity != complexity:
                continue
            
            # 检查持续时间
            if max_duration is not None and gesture.duration > max_duration:
                continue
            
            # 检查情感上下文匹配度
            context_match_score = self._calculate_context_match(gesture.emotional_context, emotional_context)
            
            if context_match_score > 0:
                matching_gestures.append((gesture, context_match_score))
        
        # 按匹配度排序
        matching_gestures.sort(key=lambda x: x[1], reverse=True)
        
        return [gesture for gesture, score in matching_gestures]
    
    def _calculate_context_match(self, gesture_context: List[str], target_context: List[str]) -> float:
        """计算上下文匹配度"""
        if not gesture_context or not target_context:
            return 0.0
        
        # 计算共同上下文数量
        common_context = set(gesture_context) & set(target_context)
        
        if not common_context:
            return 0.0
        
        # 计算匹配度
        match_score = len(common_context) / len(gesture_context)
        
        return match_score
    
    def record_gesture_usage(self, gesture_id: str, success: bool = True):
        """
        记录手势使用情况
        
        Args:
            gesture_id: 手势ID
            success: 是否成功执行
        """
        if gesture_id not in self.gestures:
            return
        
        gesture = self.gestures[gesture_id]
        
        # 更新手势使用统计
        gesture.usage_count += 1
        
        if success:
            self.usage_stats["successful_gestures"] += 1
            # 更新成功率
            total_uses = gesture.usage_count
            current_success_rate = gesture.success_rate
            gesture.success_rate = (current_success_rate * (total_uses - 1) + 1) / total_uses
        else:
            self.usage_stats["failed_gestures"] += 1
            # 更新成功率
            total_uses = gesture.usage_count
            current_success_rate = gesture.success_rate
            gesture.success_rate = (current_success_rate * (total_uses - 1)) / total_uses
        
        # 更新类别使用统计
        self.usage_stats["category_usage"][gesture.category.value] += 1
        self.usage_stats["total_gestures_used"] += 1
        
        # 更新优先级（基于使用成功率和频率）
        self._update_gesture_priority(gesture_id)
    
    def _update_gesture_priority(self, gesture_id: str):
        """更新手势优先级"""
        gesture = self.gestures[gesture_id]
        
        # 基于成功率和使用频率计算优先级
        success_weight = 0.6
        frequency_weight = 0.3
        recency_weight = 0.1
        
        success_score = gesture.success_rate
        frequency_score = min(gesture.usage_count / 100.0, 1.0)  # 归一化到0-1
        
        # 简单的优先级计算
        priority = (
            success_weight * success_score +
            frequency_weight * frequency_score +
            recency_weight * 0.5  # 简化的近期使用分数
        )
        
        self.gesture_priorities[gesture_id] = priority
    
    def get_high_priority_gestures(self, category: Optional[GestureCategory] = None, 
                                 limit: int = 5) -> List[GestureDefinition]:
        """
        获取高优先级手势
        
        Args:
            category: 手势类别过滤
            limit: 返回数量限制
            
        Returns:
            高优先级手势列表
        """
        gestures_with_priority = []
        
        for gesture_id, gesture in self.gestures.items():
            if category is not None and gesture.category != category:
                continue
            
            priority = self.gesture_priorities.get(gesture_id, 0.5)
            gestures_with_priority.append((gesture, priority))
        
        # 按优先级排序
        gestures_with_priority.sort(key=lambda x: x[1], reverse=True)
        
        return [gesture for gesture, priority in gestures_with_priority[:limit]]
    
    def create_gesture_sequence(self, sequence_id: str, gesture_ids: List[str]) -> bool:
        """
        创建手势序列
        
        Args:
            sequence_id: 序列ID
            gesture_ids: 手势ID列表
            
        Returns:
            是否创建成功
        """
        try:
            # 验证所有手势都存在
            for gesture_id in gesture_ids:
                if gesture_id not in self.gestures:
                    self.logger.error(f"手势不存在: {gesture_id}")
                    return False
            
            self.gesture_sequences[sequence_id] = gesture_ids
            self.logger.info(f"手势序列创建成功: {sequence_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建手势序列失败: {e}")
            return False
    
    def get_gesture_sequence(self, sequence_id: str) -> Optional[List[GestureDefinition]]:
        """
        获取手势序列
        
        Args:
            sequence_id: 序列ID
            
        Returns:
            手势定义列表，如果序列不存在则返回None
        """
        if sequence_id not in self.gesture_sequences:
            return None
        
        gesture_ids = self.gesture_sequences[sequence_id]
        gestures = []
        
        for gesture_id in gesture_ids:
            gesture = self.get_gesture(gesture_id)
            if gesture:
                gestures.append(gesture)
        
        return gestures
    
    def get_gesture_categories(self) -> List[GestureCategory]:
        """获取所有手势类别"""
        return list(self.gesture_categories.keys())
    
    def get_gestures_by_category(self, category: GestureCategory) -> List[GestureDefinition]:
        """获取指定类别的手势"""
        if category not in self.gesture_categories:
            return []
        
        gesture_ids = self.gesture_categories[category]
        gestures = []
        
        for gesture_id in gesture_ids:
            gesture = self.get_gesture(gesture_id)
            if gesture:
                gestures.append(gesture)
        
        return gestures
    
    def get_library_stats(self) -> Dict[str, Any]:
        """获取手势库统计信息"""
        total_gestures = len(self.gestures)
        category_counts = {}
        
        for category in GestureCategory:
            count = len(self.gesture_categories.get(category, []))
            category_counts[category.value] = count
        
        avg_success_rate = 0.0
        if total_gestures > 0:
            avg_success_rate = sum(gesture.success_rate for gesture in self.gestures.values()) / total_gestures
        
        return {
            "total_gestures": total_gestures,
            "category_distribution": category_counts,
            "average_success_rate": avg_success_rate,
            "usage_stats": self.usage_stats.copy(),
            "total_sequences": len(self.gesture_sequences)
        }
    
    async def generate_custom_gesture(self, parameters: Dict[str, Any]) -> Optional[GestureDefinition]:
        """
        生成自定义手势
        
        Args:
            parameters: 手势生成参数
            
        Returns:
            生成的手势定义，如果生成失败则返回None
        """
        try:
            # 生成唯一ID
            gesture_id = f"custom_gesture_{len(self.gestures) + 1:04d}"
            
            # 创建手势定义
            custom_gesture = GestureDefinition(
                gesture_id=gesture_id,
                name=parameters.get('name', '自定义手势'),
                category=GestureCategory(parameters.get('category', 'expressive')),
                complexity=GestureComplexity(parameters.get('complexity', 'simple')),
                description=parameters.get('description', '自动生成的自定义手势'),
                emotional_context=parameters.get('emotional_context', ['neutral']),
                duration=parameters.get('duration', 2.0),
                intensity_range=tuple(parameters.get('intensity_range', (0.5, 0.8))),
                body_parts=parameters.get('body_parts', [])
            )
            
            # 生成动画数据（简化实现）
            animation_config = AnimationConfig(
                name=gesture_id,
                duration=custom_gesture.duration,
                fps=30,
                loop=False
            )
            animation_clip = AnimationClip(animation_config)
            
            # 根据参数生成动画关键帧（简化实现）
            # 实际实现应该根据身体部位和强度生成具体的动画
            
            custom_gesture.animation_clip = animation_clip
            
            # 添加到库中
            self.add_gesture(custom_gesture)
            
            self.logger.info(f"自定义手势生成成功: {gesture_id}")
            return custom_gesture
            
        except Exception as e:
            self.logger.error(f"生成自定义手势失败: {e}")
            return None

# 全局手势库实例
_global_gesture_library: Optional[GestureLibrary] = None

def get_gesture_library() -> GestureLibrary:
    """获取全局手势库实例"""
    global _global_gesture_library
    if _global_gesture_library is None:
        _global_gesture_library = GestureLibrary()
    return _global_gesture_library

