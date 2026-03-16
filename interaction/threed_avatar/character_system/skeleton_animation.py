"""
骨骼动画系统 - 处理角色骨骼动画
负责骨骼变换、动画混合、关键帧插值和骨骼层级计算
完整实现骨骼动画的播放、混合和实时计算
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from enum import Enum
import math

# 导入基础设施层依赖
from infrastructure.compute_storage.gpu_accelerator import GPUAccelerator, gpu_accelerator
from infrastructure.compute_storage.resource_manager import ResourceManager, resource_manager, ResourceType

# 导入数据层依赖
from data.models.three_d.animations import AnimationManager, AnimationClip, AnimationConfig, Keyframe
from data.models.three_d.cat_models import CatModel

# 导入角色系统依赖
from interaction.threed_avatar.character_system.model_manager import ModelManager, ModelInstance

logger = logging.getLogger(__name__)

class AnimationState(Enum):
    """动画状态枚举"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BLENDING = "blending"
    TRANSITIONING = "transitioning"

class BlendMode(Enum):
    """混合模式枚举"""
    OVERRIDE = "override"      # 覆盖混合
    ADDITIVE = "additive"      # 叠加混合
    MULTIPLICATIVE = "multiplicative"  # 乘法混合

@dataclass
class BoneTransform:
    """骨骼变换数据"""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)  # 四元数
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)

@dataclass
class AnimationStateData:
    """动画状态数据"""
    animation_name: str
    current_time: float = 0.0
    playback_speed: float = 1.0
    weight: float = 1.0
    loop: bool = True
    state: AnimationState = AnimationState.STOPPED
    blend_mode: BlendMode = BlendMode.OVERRIDE

@dataclass
class SkeletonPose:
    """骨骼姿势"""
    bone_transforms: Dict[str, BoneTransform] = field(default_factory=dict)
    global_transforms: Dict[str, np.ndarray] = field(default_factory=dict)  # 全局变换矩阵
    skinning_matrices: Dict[str, np.ndarray] = field(default_factory=dict)  # 蒙皮矩阵

class SkeletonAnimation:
    """骨骼动画系统 - 完整实现"""
    
    def __init__(self, model_instance: ModelInstance):
        self.model_instance = model_instance
        self.skeleton_data = model_instance.skeleton_data
        self.animation_states: Dict[str, AnimationStateData] = {}
        self.current_pose = SkeletonPose()
        self.blended_pose = SkeletonPose()
        
        # 动画管理器
        self.animation_manager = AnimationManager()
        
        # 性能优化
        self.bone_cache: Dict[str, Dict[str, Any]] = {}
        self.hierarchy_cache: Dict[str, List[str]] = {}
        self.inverse_bind_poses: Dict[str, np.ndarray] = {}
        
        # 统计信息
        self.stats = {
            "total_animations_played": 0,
            "current_animation_count": 0,
            "blend_operations": 0,
            "matrix_calculations": 0,
            "average_frame_time": 0.0,
            "bone_update_count": 0
        }
        
        # 初始化骨骼系统
        self._initialize_skeleton_system()
        
        logger.info(f"SkeletonAnimation initialized for model: {model_instance.metadata.name}")

    def _initialize_skeleton_system(self):
        """初始化骨骼系统"""
        try:
            # 构建骨骼层级缓存
            self._build_hierarchy_cache()
            
            # 预计算逆绑定姿势矩阵
            self._precompute_inverse_bind_poses()
            
            # 初始化骨骼变换缓存
            self._initialize_bone_cache()
            
            # 创建默认姿势
            self._create_default_pose()
            
            logger.info(f"Skeleton system initialized with {len(self.skeleton_data.get('bones', {}))} bones")
            
        except Exception as e:
            logger.error(f"Error initializing skeleton system: {e}")

    def _build_hierarchy_cache(self):
        """构建骨骼层级缓存"""
        hierarchy = self.skeleton_data.get("hierarchy", {})
        self.hierarchy_cache = hierarchy
        
        # 如果没有提供层级，自动构建
        if not hierarchy:
            bones = self.skeleton_data.get("bones", {})
            self.hierarchy_cache = self._build_bone_hierarchy(bones)

    def _build_bone_hierarchy(self, bones: Dict[str, Any]) -> Dict[str, List[str]]:
        """构建骨骼层级关系"""
        hierarchy = {}
        
        for bone_name, bone_data in bones.items():
            parent_id = bone_data.get("parent", -1)
            if parent_id != -1:
                # 查找父骨骼名称
                parent_name = None
                for name, data in bones.items():
                    if data.get("id") == parent_id:
                        parent_name = name
                        break
                
                if parent_name:
                    if parent_name not in hierarchy:
                        hierarchy[parent_name] = []
                    hierarchy[parent_name].append(bone_name)
        
        # 确保根骨骼存在
        if "root" not in hierarchy and "root" in bones:
            hierarchy["root"] = []
            for bone_name, bone_data in bones.items():
                if bone_data.get("parent") == -1 and bone_name != "root":
                    hierarchy["root"].append(bone_name)
        
        return hierarchy

    def _precompute_inverse_bind_poses(self):
        """预计算逆绑定姿势矩阵"""
        bind_pose = self.skeleton_data.get("bind_pose", {})
        
        for bone_name, bone_pose in bind_pose.items():
            # 计算绑定姿势矩阵
            bind_matrix = self._compose_transform_matrix(
                bone_pose.get("position", (0, 0, 0)),
                bone_pose.get("rotation", (0, 0, 0, 1)),
                bone_pose.get("scale", (1, 1, 1))
            )
            
            # 计算逆矩阵
            try:
                inverse_matrix = np.linalg.inv(bind_matrix)
                self.inverse_bind_poses[bone_name] = inverse_matrix
            except np.linalg.LinAlgError:
                # 如果矩阵不可逆，使用单位矩阵
                self.inverse_bind_poses[bone_name] = np.eye(4)
                logger.warning(f"Bind pose matrix for {bone_name} is not invertible, using identity matrix")

    def _compose_transform_matrix(self, position: Tuple[float, float, float], 
                                rotation: Tuple[float, float, float, float],
                                scale: Tuple[float, float, float]) -> np.ndarray:
        """组合变换矩阵"""
        # 创建4x4变换矩阵
        matrix = np.eye(4)
        
        # 位置
        matrix[0, 3] = position[0]
        matrix[1, 3] = position[1]
        matrix[2, 3] = position[2]
        
        # 缩放
        matrix[0, 0] = scale[0]
        matrix[1, 1] = scale[1]
        matrix[2, 2] = scale[2]
        
        # 旋转（四元数转矩阵）
        x, y, z, w = rotation
        
        # 四元数转旋转矩阵
        matrix[0, 0] = 1 - 2*(y*y + z*z)
        matrix[0, 1] = 2*(x*y - z*w)
        matrix[0, 2] = 2*(x*z + y*w)
        
        matrix[1, 0] = 2*(x*y + z*w)
        matrix[1, 1] = 1 - 2*(x*x + z*z)
        matrix[1, 2] = 2*(y*z - x*w)
        
        matrix[2, 0] = 2*(x*z - y*w)
        matrix[2, 1] = 2*(y*z + x*w)
        matrix[2, 2] = 1 - 2*(x*x + y*y)
        
        return matrix

    def _initialize_bone_cache(self):
        """初始化骨骼缓存"""
        bones = self.skeleton_data.get("bones", {})
        
        for bone_name, bone_data in bones.items():
            self.bone_cache[bone_name] = {
                "id": bone_data.get("id"),
                "parent": bone_data.get("parent", -1),
                "local_position": bone_data.get("position", (0, 0, 0)),
                "local_rotation": bone_data.get("rotation", (0, 0, 0, 1)),
                "children": self.hierarchy_cache.get(bone_name, [])
            }

    def _create_default_pose(self):
        """创建默认姿势"""
        bones = self.skeleton_data.get("bones", {})
        bind_pose = self.skeleton_data.get("bind_pose", {})
        
        for bone_name in bones.keys():
            if bone_name in bind_pose:
                # 使用绑定姿势
                pose_data = bind_pose[bone_name]
                transform = BoneTransform(
                    position=pose_data.get("position", (0, 0, 0)),
                    rotation=pose_data.get("rotation", (0, 0, 0, 1)),
                    scale=pose_data.get("scale", (1, 1, 1))
                )
            else:
                # 使用默认变换
                transform = BoneTransform()
            
            self.current_pose.bone_transforms[bone_name] = transform
        
        # 计算全局变换
        self._calculate_global_transforms()

    async def load_animation(self, animation_name: str, animation_config: AnimationConfig) -> bool:
        """加载动画"""
        try:
            # 使用动画管理器加载动画
            animation_clip = self.animation_manager.load_animation(animation_name, animation_config)
            if not animation_clip or not animation_clip.is_loaded:
                logger.error(f"Failed to load animation: {animation_name}")
                return False
            
            # 创建动画状态
            animation_state = AnimationStateData(
                animation_name=animation_name,
                playback_speed=1.0,
                loop=animation_config.loop,
                state=AnimationState.STOPPED
            )
            
            self.animation_states[animation_name] = animation_state
            self.stats["current_animation_count"] = len(self.animation_states)
            
            logger.info(f"Animation loaded: {animation_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading animation {animation_name}: {e}")
            return False

    async def play_animation(self, animation_name: str, blend_time: float = 0.0) -> bool:
        """播放动画"""
        try:
            if animation_name not in self.animation_states:
                logger.error(f"Animation not loaded: {animation_name}")
                return False
            
            animation_state = self.animation_states[animation_name]
            animation_state.state = AnimationState.PLAYING
            animation_state.current_time = 0.0
            
            # 如果是混合播放，设置混合权重
            if blend_time > 0:
                animation_state.state = AnimationState.BLENDING
                animation_state.weight = 0.0
            
            self.stats["total_animations_played"] += 1
            
            logger.info(f"Playing animation: {animation_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error playing animation {animation_name}: {e}")
            return False

    async def stop_animation(self, animation_name: str) -> bool:
        """停止动画"""
        try:
            if animation_name not in self.animation_states:
                logger.error(f"Animation not loaded: {animation_name}")
                return False
            
            animation_state = self.animation_states[animation_name]
            animation_state.state = AnimationState.STOPPED
            animation_state.weight = 0.0
            
            logger.info(f"Stopped animation: {animation_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping animation {animation_name}: {e}")
            return False

    async def pause_animation(self, animation_name: str) -> bool:
        """暂停动画"""
        try:
            if animation_name not in self.animation_states:
                logger.error(f"Animation not loaded: {animation_name}")
                return False
            
            animation_state = self.animation_states[animation_name]
            if animation_state.state == AnimationState.PLAYING:
                animation_state.state = AnimationState.PAUSED
            
            logger.info(f"Paused animation: {animation_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error pausing animation {animation_name}: {e}")
            return False

    async def set_animation_speed(self, animation_name: str, speed: float) -> bool:
        """设置动画播放速度"""
        try:
            if animation_name not in self.animation_states:
                logger.error(f"Animation not loaded: {animation_name}")
                return False
            
            animation_state = self.animation_states[animation_name]
            animation_state.playback_speed = max(0.0, speed)  # 防止负速度
            
            logger.debug(f"Set animation speed: {animation_name} -> {speed}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting animation speed for {animation_name}: {e}")
            return False

    async def set_animation_weight(self, animation_name: str, weight: float) -> bool:
        """设置动画混合权重"""
        try:
            if animation_name not in self.animation_states:
                logger.error(f"Animation not loaded: {animation_name}")
                return False
            
            animation_state = self.animation_states[animation_name]
            animation_state.weight = max(0.0, min(1.0, weight))  # 限制在0-1之间
            
            logger.debug(f"Set animation weight: {animation_name} -> {weight}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting animation weight for {animation_name}: {e}")
            return False

    async def blend_animations(self, animation_weights: Dict[str, float]) -> bool:
        """混合多个动画"""
        try:
            # 验证输入
            valid_animations = {}
            total_weight = 0.0
            
            for anim_name, weight in animation_weights.items():
                if anim_name in self.animation_states and weight > 0:
                    valid_animations[anim_name] = weight
                    total_weight += weight
            
            if not valid_animations:
                logger.warning("No valid animations to blend")
                return False
            
            # 归一化权重
            if total_weight > 0:
                normalized_weights = {name: weight / total_weight for name, weight in valid_animations.items()}
            else:
                normalized_weights = valid_animations
            
            # 执行动画混合
            blended_pose = await self._perform_animation_blending(normalized_weights)
            if blended_pose:
                self.blended_pose = blended_pose
                self.stats["blend_operations"] += 1
                return True
            else:
                return False
            
        except Exception as e:
            logger.error(f"Error blending animations: {e}")
            return False

    async def _perform_animation_blending(self, animation_weights: Dict[str, float]) -> Optional[SkeletonPose]:
        """执行动画混合"""
        try:
            blended_pose = SkeletonPose()
            bones = self.skeleton_data.get("bones", {})
            
            # 为每个骨骼初始化混合数据
            for bone_name in bones.keys():
                blended_position = np.zeros(3)
                blended_rotation = np.array([0.0, 0.0, 0.0, 1.0])  # 单位四元数
                blended_scale = np.ones(3)
                
                total_weight = 0.0
                first_animation = True
                
                # 混合每个动画的骨骼变换
                for anim_name, weight in animation_weights.items():
                    if weight <= 0:
                        continue
                    
                    # 获取动画的当前姿势
                    anim_pose = await self._get_animation_pose_at_time(anim_name, self.animation_states[anim_name].current_time)
                    if not anim_pose or bone_name not in anim_pose.bone_transforms:
                        continue
                    
                    bone_transform = anim_pose.bone_transforms[bone_name]
                    
                    # 位置和缩放线性混合
                    blended_position += np.array(bone_transform.position) * weight
                    blended_scale += np.array(bone_transform.scale) * weight
                    
                    # 旋转球面线性混合
                    current_rotation = np.array(bone_transform.rotation)
                    if first_animation:
                        blended_rotation = current_rotation
                        first_animation = False
                    else:
                        blended_rotation = self._slerp_quaternions(blended_rotation, current_rotation, weight / (total_weight + weight))
                    
                    total_weight += weight
                
                # 创建混合后的骨骼变换
                if total_weight > 0:
                    blended_transform = BoneTransform(
                        position=tuple(blended_position),
                        rotation=tuple(blended_rotation / np.linalg.norm(blended_rotation)),  # 归一化四元数
                        scale=tuple(blended_scale)
                    )
                    blended_pose.bone_transforms[bone_name] = blended_transform
            
            # 计算全局变换
            self._calculate_global_transforms_for_pose(blended_pose)
            
            return blended_pose
            
        except Exception as e:
            logger.error(f"Error performing animation blending: {e}")
            return None

    def _slerp_quaternions(self, q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
        """四元数球面线性插值"""
        # 确保四元数是单位四元数
        q1 = q1 / np.linalg.norm(q1)
        q2 = q2 / np.linalg.norm(q2)
        
        # 计算点积
        dot = np.dot(q1, q2)
        
        # 如果点积为负，取反其中一个四元数以保证最短路径
        if dot < 0.0:
            q2 = -q2
            dot = -dot
        
        # 如果四元数非常接近，使用线性插值避免数值问题
        if dot > 0.9995:
            result = q1 + t * (q2 - q1)
            return result / np.linalg.norm(result)
        
        # 计算插值角度
        theta_0 = np.arccos(dot)
        sin_theta_0 = np.sin(theta_0)
        
        theta = theta_0 * t
        sin_theta = np.sin(theta)
        
        # 计算插值系数
        s1 = np.cos(theta) - dot * sin_theta / sin_theta_0
        s2 = sin_theta / sin_theta_0
        
        return s1 * q1 + s2 * q2

    async def _get_animation_pose_at_time(self, animation_name: str, time: float) -> Optional[SkeletonPose]:
        """获取动画在指定时间的姿势"""
        try:
            animation_clip = self.animation_manager.get_animation(animation_name)
            if not animation_clip:
                return None
            
            # 获取动画片段的关键帧数据
            keyframes = animation_clip.keyframes
            
            # 创建姿势
            pose = SkeletonPose()
            
            for bone_name, frames in keyframes.items():
                if not frames:
                    continue
                
                # 查找当前时间对应的关键帧
                frame1, frame2 = self._find_keyframes_for_time(frames, time)
                
                if frame1 and frame2:
                    # 计算插值系数
                    t = (time - frame1.time) / (frame2.time - frame1.time) if frame2.time > frame1.time else 0.0
                    t = max(0.0, min(1.0, t))  # 限制在0-1之间
                    
                    # 插值位置
                    position = self._lerp_vector(frame1.position, frame2.position, t)
                    
                    # 插值旋转（四元数SLERP）
                    rotation = self._slerp_quaternions(np.array(frame1.rotation), np.array(frame2.rotation), t)
                    rotation = rotation / np.linalg.norm(rotation)  # 归一化
                    
                    # 插值缩放
                    scale = self._lerp_vector(frame1.scale, frame2.scale, t)
                    
                    # 创建骨骼变换
                    bone_transform = BoneTransform(
                        position=tuple(position),
                        rotation=tuple(rotation),
                        scale=tuple(scale)
                    )
                    
                    pose.bone_transforms[bone_name] = bone_transform
            
            return pose
            
        except Exception as e:
            logger.error(f"Error getting animation pose for {animation_name} at time {time}: {e}")
            return None

    def _find_keyframes_for_time(self, keyframes: List[Keyframe], time: float) -> Tuple[Optional[Keyframe], Optional[Keyframe]]:
        """查找时间对应的关键帧"""
        if not keyframes:
            return None, None
        
        # 在时间之前的关键帧
        frame1 = None
        frame2 = None
        
        for i in range(len(keyframes) - 1):
            if keyframes[i].time <= time <= keyframes[i + 1].time:
                frame1 = keyframes[i]
                frame2 = keyframes[i + 1]
                break
        
        # 如果时间在第一个关键帧之前
        if time < keyframes[0].time:
            frame1 = frame2 = keyframes[0]
        # 如果时间在最后一个关键帧之后
        elif time > keyframes[-1].time:
            frame1 = frame2 = keyframes[-1]
        
        return frame1, frame2

    def _lerp_vector(self, v1: Tuple[float, float, float], v2: Tuple[float, float, float], t: float) -> np.ndarray:
        """向量线性插值"""
        return np.array(v1) + (np.array(v2) - np.array(v1)) * t

    async def update(self, delta_time: float):
        """更新动画系统"""
        start_time = time.time()
        
        try:
            # 更新所有动画状态
            await self._update_animation_states(delta_time)
            
            # 计算当前姿势
            await self._calculate_current_pose()
            
            # 计算蒙皮矩阵
            self._calculate_skinning_matrices()
            
            # 更新统计信息
            frame_time = time.time() - start_time
            self.stats["average_frame_time"] = (
                (self.stats["average_frame_time"] * (self.stats["blend_operations"] - 1) + frame_time) 
                / self.stats["blend_operations"] if self.stats["blend_operations"] > 0 else frame_time
            )
            
        except Exception as e:
            logger.error(f"Error updating skeleton animation: {e}")

    async def _update_animation_states(self, delta_time: float):
        """更新动画状态"""
        for animation_state in self.animation_states.values():
            if animation_state.state == AnimationState.PLAYING:
                # 更新动画时间
                animation_state.current_time += delta_time * animation_state.playback_speed
                
                # 检查循环
                animation_clip = self.animation_manager.get_animation(animation_state.animation_name)
                if animation_clip and animation_state.loop:
                    if animation_state.current_time > animation_clip.config.duration:
                        animation_state.current_time = 0.0
                        self.stats["total_animations_played"] += 1
            
            elif animation_state.state == AnimationState.BLENDING:
                # 更新混合权重
                animation_state.weight = min(1.0, animation_state.weight + delta_time / 0.2)  # 0.2秒混合时间
                if animation_state.weight >= 1.0:
                    animation_state.state = AnimationState.PLAYING

    async def _calculate_current_pose(self):
        """计算当前姿势"""
        try:
            # 获取活动的动画
            active_animations = {}
            for anim_name, anim_state in self.animation_states.items():
                if anim_state.state in [AnimationState.PLAYING, AnimationState.BLENDING] and anim_state.weight > 0:
                    active_animations[anim_name] = anim_state.weight
            
            if active_animations:
                # 混合动画
                if len(active_animations) == 1:
                    # 单一动画，直接使用
                    anim_name = list(active_animations.keys())[0]
                    anim_pose = await self._get_animation_pose_at_time(anim_name, self.animation_states[anim_name].current_time)
                    if anim_pose:
                        self.current_pose = anim_pose
                else:
                    # 多个动画，进行混合
                    await self.blend_animations(active_animations)
                    self.current_pose = self.blended_pose
            else:
                # 没有活动动画，使用绑定姿势
                self._create_default_pose()
            
            # 计算全局变换
            self._calculate_global_transforms()
            
        except Exception as e:
            logger.error(f"Error calculating current pose: {e}")

    def _calculate_global_transforms(self):
        """计算全局变换矩阵"""
        self._calculate_global_transforms_for_pose(self.current_pose)

    def _calculate_global_transforms_for_pose(self, pose: SkeletonPose):
        """为指定姿势计算全局变换矩阵"""
        try:
            # 清空之前的全局变换
            pose.global_transforms.clear()
            
            # 从根骨骼开始递归计算
            root_bones = [bone_name for bone_name, bone_data in self.bone_cache.items() if bone_data["parent"] == -1]
            
            for root_bone in root_bones:
                self._calculate_bone_global_transform(root_bone, np.eye(4), pose)
            
            self.stats["matrix_calculations"] += len(pose.bone_transforms)
            
        except Exception as e:
            logger.error(f"Error calculating global transforms: {e}")

    def _calculate_bone_global_transform(self, bone_name: str, parent_matrix: np.ndarray, pose: SkeletonPose):
        """计算骨骼的全局变换矩阵"""
        try:
            if bone_name not in pose.bone_transforms:
                return
            
            # 获取骨骼的局部变换
            bone_transform = pose.bone_transforms[bone_name]
            
            # 计算局部变换矩阵
            local_matrix = self._compose_transform_matrix(
                bone_transform.position,
                bone_transform.rotation,
                bone_transform.scale
            )
            
            # 计算全局变换矩阵
            global_matrix = np.dot(parent_matrix, local_matrix)
            pose.global_transforms[bone_name] = global_matrix
            
            # 递归计算子骨骼
            children = self.bone_cache[bone_name].get("children", [])
            for child_name in children:
                self._calculate_bone_global_transform(child_name, global_matrix, pose)
            
            self.stats["bone_update_count"] += 1
            
        except Exception as e:
            logger.error(f"Error calculating global transform for bone {bone_name}: {e}")

    def _calculate_skinning_matrices(self):
        """计算蒙皮矩阵"""
        try:
            self.current_pose.skinning_matrices.clear()
            
            for bone_name, global_matrix in self.current_pose.global_transforms.items():
                if bone_name in self.inverse_bind_poses:
                    # 蒙皮矩阵 = 全局变换矩阵 × 逆绑定姿势矩阵
                    skinning_matrix = np.dot(global_matrix, self.inverse_bind_poses[bone_name])
                    self.current_pose.skinning_matrices[bone_name] = skinning_matrix
            
        except Exception as e:
            logger.error(f"Error calculating skinning matrices: {e}")

    async def get_current_pose(self) -> SkeletonPose:
        """获取当前姿势"""
        return self.current_pose

    async def get_skinning_matrices(self) -> Dict[str, np.ndarray]:
        """获取蒙皮矩阵"""
        return self.current_pose.skinning_matrices

    async def get_bone_position(self, bone_name: str) -> Optional[Tuple[float, float, float]]:
        """获取骨骼位置"""
        if bone_name in self.current_pose.global_transforms:
            matrix = self.current_pose.global_transforms[bone_name]
            return (matrix[0, 3], matrix[1, 3], matrix[2, 3])
        return None

    async def get_bone_rotation(self, bone_name: str) -> Optional[Tuple[float, float, float, float]]:
        """获取骨骼旋转（四元数）"""
        if bone_name in self.current_pose.bone_transforms:
            return self.current_pose.bone_transforms[bone_name].rotation
        return None

    async def set_bone_transform(self, bone_name: str, position: Tuple[float, float, float] = None,
                               rotation: Tuple[float, float, float, float] = None,
                               scale: Tuple[float, float, float] = None) -> bool:
        """手动设置骨骼变换"""
        try:
            if bone_name not in self.current_pose.bone_transforms:
                logger.error(f"Bone not found: {bone_name}")
                return False
            
            bone_transform = self.current_pose.bone_transforms[bone_name]
            
            if position is not None:
                bone_transform.position = position
            
            if rotation is not None:
                bone_transform.rotation = rotation
            
            if scale is not None:
                bone_transform.scale = scale
            
            # 重新计算全局变换
            self._calculate_global_transforms()
            self._calculate_skinning_matrices()
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting bone transform for {bone_name}: {e}")
            return False

    async def get_animation_state(self, animation_name: str) -> Optional[AnimationStateData]:
        """获取动画状态"""
        return self.animation_states.get(animation_name)

    async def get_active_animations(self) -> List[str]:
        """获取活动动画列表"""
        return [name for name, state in self.animation_states.items() 
                if state.state in [AnimationState.PLAYING, AnimationState.BLENDING]]

    async def get_skeleton_info(self) -> Dict[str, Any]:
        """获取骨骼系统信息"""
        bones = self.skeleton_data.get("bones", {})
        
        return {
            "bone_count": len(bones),
            "hierarchy_depth": self._calculate_hierarchy_depth(),
            "animation_count": len(self.animation_states),
            "active_animations": len(await self.get_active_animations()),
            "pose_bone_count": len(self.current_pose.bone_transforms)
        }

    def _calculate_hierarchy_depth(self) -> int:
        """计算骨骼层级深度"""
        def get_bone_depth(bone_name: str) -> int:
            children = self.hierarchy_cache.get(bone_name, [])
            if not children:
                return 1
            return 1 + max(get_bone_depth(child) for child in children)
        
        root_bones = [name for name in self.bone_cache.keys() if self.bone_cache[name]["parent"] == -1]
        if not root_bones:
            return 0
        return max(get_bone_depth(root) for root in root_bones)

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["animation_states_count"] = len(self.animation_states)
        stats["skeleton_info"] = await self.get_skeleton_info()
        
        return stats

    async def cleanup(self):
        """清理动画系统"""
        try:
            # 停止所有动画
            for animation_name in list(self.animation_states.keys()):
                await self.stop_animation(animation_name)
            
            # 清空动画状态
            self.animation_states.clear()
            
            # 清空缓存
            self.bone_cache.clear()
            self.hierarchy_cache.clear()
            self.inverse_bind_poses.clear()
            
            # 重置姿势
            self.current_pose = SkeletonPose()
            self.blended_pose = SkeletonPose()
            
            logger.info("Skeleton animation system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during skeleton animation cleanup: {e}")

