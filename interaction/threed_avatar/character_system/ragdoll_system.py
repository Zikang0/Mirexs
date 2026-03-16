"""
布娃娃系统：物理布娃娃模拟
负责角色的物理布娃娃效果和死亡/击倒物理模拟
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math

from .collision_detector import CollisionDetector, CollisionShape, CollisionShapeType
from .skeleton_animation import Skeleton, Bone

logger = logging.getLogger(__name__)

class RagdollState(Enum):
    """布娃娃状态"""
    ACTIVE = "active"          # 激活状态
    INACTIVE = "inactive"      # 未激活
    BLENDING = "blending"      # 动画混合状态
    SETTLING = "settling"      # 稳定状态

@dataclass
class RagdollBone:
    """布娃娃骨骼"""
    bone_name: str
    collision_shape: CollisionShape
    mass: float
    parent_constraint: Optional[str] = None
    joint_limits: Tuple[float, float] = (-45.0, 45.0)  # 关节限制（度）

@dataclass
class RagdollConstraint:
    """布娃娃约束"""
    constraint_id: str
    bone_a: str
    bone_b: str
    pivot_a: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    pivot_b: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    swing_limit: float = 45.0  # 摆动限制（度）
    twist_limit: float = 30.0  # 扭转限制（度）

class RagdollSystem:
    """布娃娃系统"""
    
    def __init__(self, collision_detector: CollisionDetector):
        self.collision_detector = collision_detector
        self.ragdolls: Dict[str, Any] = {}
        self.ragdoll_bones: Dict[str, Dict[str, RagdollBone]] = {}
        self.ragdoll_constraints: Dict[str, List[RagdollConstraint]] = {}
        
        # 物理参数
        self.gravity = (0.0, -9.81, 0.0)
        self.damping = 0.99
        self.sleep_threshold = 0.1
        self.max_velocity = 10.0
        
        # 性能统计
        self.stats = {
            "active_ragdolls": 0,
            "total_bones": 0,
            "physics_updates": 0,
            "constraint_solves": 0
        }
        
        logger.info("布娃娃系统初始化完成")
    
    def create_ragdoll(self, ragdoll_id: str, skeleton: Skeleton) -> bool:
        """为骨骼创建布娃娃"""
        if ragdoll_id in self.ragdolls:
            logger.warning(f"布娃娃已存在: {ragdoll_id}")
            return False
        
        try:
            ragdoll_data = {
                "skeleton": skeleton,
                "state": RagdollState.INACTIVE,
                "blend_factor": 0.0,
                "velocities": {},
                "forces": {},
                "is_sleeping": False
            }
            
            self.ragdolls[ragdoll_id] = ragdoll_data
            self.ragdoll_bones[ragdoll_id] = {}
            self.ragdoll_constraints[ragdoll_id] = []
            
            # 为重要骨骼创建碰撞形状
            self._create_ragdoll_bones(ragdoll_id, skeleton)
            
            # 创建骨骼约束
            self._create_ragdoll_constraints(ragdoll_id, skeleton)
            
            self.stats["active_ragdolls"] += 1
            logger.info(f"创建布娃娃: {ragdoll_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建布娃娃失败 {ragdoll_id}: {e}")
            return False
    
    def _create_ragdoll_bones(self, ragdoll_id: str, skeleton: Skeleton):
        """为布娃娃创建骨骼碰撞形状"""
        # 主要骨骼的碰撞形状配置
        bone_configs = {
            "spine": ("capsule", 0.15, 0.8, 5.0),
            "chest": ("capsule", 0.2, 0.6, 8.0),
            "head": ("sphere", 0.25, 0.0, 3.0),
            "left_upper_arm": ("capsule", 0.1, 0.4, 2.0),
            "right_upper_arm": ("capsule", 0.1, 0.4, 2.0),
            "left_forearm": ("capsule", 0.08, 0.35, 1.5),
            "right_forearm": ("capsule", 0.08, 0.35, 1.5),
            "left_thigh": ("capsule", 0.15, 0.5, 5.0),
            "right_thigh": ("capsule", 0.15, 0.5, 5.0),
            "left_shin": ("capsule", 0.12, 0.45, 4.0),
            "right_shin": ("capsule", 0.12, 0.45, 4.0)
        }
        
        for bone_name, bone in skeleton.bones.items():
            if bone_name in bone_configs:
                shape_type, radius, height, mass = bone_configs[bone_name]
                
                # 创建碰撞形状
                if shape_type == "sphere":
                    collision_shape = CollisionShape(
                        shape_id=f"{ragdoll_id}_{bone_name}",
                        shape_type=CollisionShapeType.SPHERE,
                        position=bone.position,
                        radius=radius,
                        mass=mass,
                        restitution=0.2
                    )
                elif shape_type == "capsule":
                    collision_shape = CollisionShape(
                        shape_id=f"{ragdoll_id}_{bone_name}",
                        shape_type=CollisionShapeType.CAPSULE,
                        position=bone.position,
                        radius=radius,
                        height=height,
                        mass=mass,
                        restitution=0.1
                    )
                
                # 添加到碰撞检测器
                self.collision_detector.add_collision_shape(collision_shape)
                
                # 创建布娃娃骨骼
                ragdoll_bone = RagdollBone(
                    bone_name=bone_name,
                    collision_shape=collision_shape,
                    mass=mass
                )
                
                self.ragdoll_bones[ragdoll_id][bone_name] = ragdoll_bone
                self.stats["total_bones"] += 1
    
    def _create_ragdoll_constraints(self, ragdoll_id: str, skeleton: Skeleton):
        """创建布娃娃约束"""
        # 定义骨骼约束关系
        constraint_definitions = [
            # 脊柱链
            ("spine", "chest", (0, 0.4, 0), (0, -0.3, 0), 30.0, 20.0),
            ("chest", "head", (0, 0.3, 0), (0, -0.2, 0), 40.0, 30.0),
            
            # 左臂
            ("chest", "left_upper_arm", (-0.2, 0.1, 0), (0.1, 0, 0), 60.0, 45.0),
            ("left_upper_arm", "left_forearm", (0, -0.2, 0), (0, 0.15, 0), 90.0, 10.0),
            
            # 右臂
            ("chest", "right_upper_arm", (0.2, 0.1, 0), (-0.1, 0, 0), 60.0, 45.0),
            ("right_upper_arm", "right_forearm", (0, -0.2, 0), (0, 0.15, 0), 90.0, 10.0),
            
            # 左腿
            ("spine", "left_thigh", (-0.1, -0.4, 0), (0, 0.25, 0), 45.0, 30.0),
            ("left_thigh", "left_shin", (0, -0.25, 0), (0, 0.2, 0), 90.0, 10.0),
            
            # 右腿
            ("spine", "right_thigh", (0.1, -0.4, 0), (0, 0.25, 0), 45.0, 30.0),
            ("right_thigh", "right_shin", (0, -0.25, 0), (0, 0.2, 0), 90.0, 10.0),
        ]
        
        for i, (bone_a, bone_b, pivot_a, pivot_b, swing_limit, twist_limit) in enumerate(constraint_definitions):
            if bone_a in skeleton.bones and bone_b in skeleton.bones:
                constraint = RagdollConstraint(
                    constraint_id=f"{ragdoll_id}_constraint_{i}",
                    bone_a=bone_a,
                    bone_b=bone_b,
                    pivot_a=pivot_a,
                    pivot_b=pivot_b,
                    swing_limit=swing_limit,
                    twist_limit=twist_limit
                )
                
                self.ragdoll_constraints[ragdoll_id].append(constraint)
    
    def activate_ragdoll(self, ragdoll_id: str, initial_velocity: Tuple[float, float, float] = (0, 0, 0)):
        """激活布娃娃"""
        if ragdoll_id not in self.ragdolls:
            logger.error(f"布娃娃不存在: {ragdoll_id}")
            return
        
        ragdoll = self.ragdolls[ragdoll_id]
        ragdoll["state"] = RagdollState.ACTIVE
        ragdoll["blend_factor"] = 0.0
        ragdoll["is_sleeping"] = False
        
        # 设置初始速度
        for bone_name in self.ragdoll_bones[ragdoll_id]:
            ragdoll["velocities"][bone_name] = np.array(initial_velocity)
            ragdoll["forces"][bone_name] = np.array([0.0, 0.0, 0.0])
        
        logger.info(f"激活布娃娃: {ragdoll_id}")
    
    def deactivate_ragdoll(self, ragdoll_id: str):
        """停用布娃娃"""
        if ragdoll_id not in self.ragdolls:
            return
        
        ragdoll = self.ragdolls[ragdoll_id]
        ragdoll["state"] = RagdollState.INACTIVE
        
        # 移除碰撞形状
        for bone_name, ragdoll_bone in self.ragdoll_bones[ragdoll_id].items():
            self.collision_detector.remove_collision_shape(ragdoll_bone.collision_shape.shape_id)
        
        logger.info(f"停用布娃娃: {ragdoll_id}")
    
    def blend_to_ragdoll(self, ragdoll_id: str, blend_time: float = 0.5):
        """混合到布娃娃状态"""
        if ragdoll_id not in self.ragdolls:
            return
        
        ragdoll = self.ragdolls[ragdoll_id]
        ragdoll["state"] = RagdollState.BLENDING
        ragdoll["blend_factor"] = 0.0
        ragdoll["blend_time"] = blend_time
        
        logger.info(f"开始混合到布娃娃: {ragdoll_id}, 时间: {blend_time}秒")
    
    def update_ragdoll(self, ragdoll_id: str, delta_time: float):
        """更新布娃娃物理"""
        if ragdoll_id not in self.ragdolls:
            return
        
        ragdoll = self.ragdolls[ragdoll_id]
        
        if ragdoll["state"] == RagdollState.INACTIVE:
            return
        
        # 处理混合状态
        if ragdoll["state"] == RagdollState.BLENDING:
            self._update_blending(ragdoll, delta_time)
        
        # 更新物理
        if ragdoll["state"] in [RagdollState.ACTIVE, RagdollState.BLENDING]:
            self._update_physics(ragdoll_id, delta_time)
            self._solve_constraints(ragdoll_id)
        
        self.stats["physics_updates"] += 1
    
    def _update_blending(self, ragdoll: Dict[str, Any], delta_time: float):
        """更新混合状态"""
        ragdoll["blend_factor"] += delta_time / ragdoll["blend_time"]
        
        if ragdoll["blend_factor"] >= 1.0:
            ragdoll["state"] = RagdollState.ACTIVE
            ragdoll["blend_factor"] = 1.0
    
    def _update_physics(self, ragdoll_id: str, delta_time: float):
        """更新物理模拟"""
        ragdoll = self.ragdolls[ragdoll_id]
        bones = self.ragdoll_bones[ragdoll_id]
        
        for bone_name, ragdoll_bone in bones.items():
            if bone_name not in ragdoll["velocities"]:
                continue
            
            # 获取碰撞形状
            shape = ragdoll_bone.collision_shape
            
            # 应用重力
            gravity_force = np.array(self.gravity) * ragdoll_bone.mass
            ragdoll["forces"][bone_name] = gravity_force
            
            # 计算加速度
            acceleration = ragdoll["forces"][bone_name] / ragdoll_bone.mass
            
            # 更新速度
            velocity = ragdoll["velocities"][bone_name]
            velocity += acceleration * delta_time
            
            # 应用阻尼
            velocity *= self.damping
            
            # 限制最大速度
            speed = np.linalg.norm(velocity)
            if speed > self.max_velocity:
                velocity = velocity / speed * self.max_velocity
            
            ragdoll["velocities"][bone_name] = velocity
            
            # 更新位置
            new_position = np.array(shape.position) + velocity * delta_time
            self.collision_detector.update_shape_position(shape.shape_id, tuple(new_position))
            
            # 重置力
            ragdoll["forces"][bone_name] = np.array([0.0, 0.0, 0.0])
    
    def _solve_constraints(self, ragdoll_id: str):
        """解算约束"""
        ragdoll = self.ragdolls[ragdoll_id]
        bones = self.ragdoll_bones[ragdoll_id]
        constraints = self.ragdoll_constraints[ragdoll_id]
        
        for constraint in constraints:
            if constraint.bone_a not in bones or constraint.bone_b not in bones:
                continue
            
            bone_a = bones[constraint.bone_a]
            bone_b = bones[constraint.bone_b]
            
            # 获取骨骼位置
            pos_a = np.array(bone_a.collision_shape.position)
            pos_b = np.array(bone_b.collision_shape.position)
            
            # 计算约束向量
            pivot_a_world = pos_a + np.array(constraint.pivot_a)
            pivot_b_world = pos_b + np.array(constraint.pivot_b)
            
            constraint_vector = pivot_b_world - pivot_a_world
            constraint_length = np.linalg.norm(constraint_vector)
            
            # 简单的距离约束
            if constraint_length > 0.1:  # 如果有拉伸
                correction = constraint_vector * 0.5  # 50%修正
                
                # 应用修正到位置
                if not bone_a.collision_shape.is_static:
                    new_pos_a = pos_a + correction * 0.5
                    self.collision_detector.update_shape_position(
                        bone_a.collision_shape.shape_id, tuple(new_pos_a)
                    )
                
                if not bone_b.collision_shape.is_static:
                    new_pos_b = pos_b - correction * 0.5
                    self.collision_detector.update_shape_position(
                        bone_b.collision_shape.shape_id, tuple(new_pos_b)
                    )
            
            self.stats["constraint_solves"] += 1
    
    def apply_impulse(self, ragdoll_id: str, bone_name: str, impulse: Tuple[float, float, float], 
                     point: Tuple[float, float, float] = None):
        """对布娃娃骨骼施加冲量"""
        if ragdoll_id not in self.ragdolls or bone_name not in self.ragdoll_bones[ragdoll_id]:
            return
        
        ragdoll = self.ragdolls[ragdoll_id]
        
        if bone_name in ragdoll["velocities"]:
            velocity = ragdoll["velocities"][bone_name]
            mass = self.ragdoll_bones[ragdoll_id][bone_name].mass
            
            # 计算速度变化
            delta_v = np.array(impulse) / mass
            ragdoll["velocities"][bone_name] = velocity + delta_v
            
            # 唤醒布娃娃
            ragdoll["is_sleeping"] = False
            
            logger.debug(f"对布娃娃 {ragdoll_id} 骨骼 {bone_name} 施加冲量: {impulse}")
    
    def get_ragdoll_pose(self, ragdoll_id: str) -> Dict[str, Dict[str, Tuple]]:
        """获取布娃娃当前姿势"""
        if ragdoll_id not in self.ragdolls:
            return {}
        
        pose = {}
        bones = self.ragdoll_bones[ragdoll_id]
        
        for bone_name, ragdoll_bone in bones.items():
            shape = ragdoll_bone.collision_shape
            pose[bone_name] = {
                "position": shape.position,
                "rotation": shape.rotation,
                "scale": shape.scale
            }
        
        return pose
    
    def is_ragdoll_sleeping(self, ragdoll_id: str) -> bool:
        """检查布娃娃是否处于睡眠状态"""
        if ragdoll_id not in self.ragdolls:
            return True
        
        return self.ragdolls[ragdoll_id]["is_sleeping"]
    
    def get_ragdoll_state(self, ragdoll_id: str) -> RagdollState:
        """获取布娃娃状态"""
        if ragdoll_id not in self.ragdolls:
            return RagdollState.INACTIVE
        
        return self.ragdolls[ragdoll_id]["state"]
    
    def check_ragdoll_settled(self, ragdoll_id: str) -> bool:
        """检查布娃娃是否已经稳定"""
        if ragdoll_id not in self.ragdolls:
            return True
        
        ragdoll = self.ragdolls[ragdoll_id]
        
        # 检查所有骨骼的速度
        max_velocity = 0.0
        for velocity in ragdoll["velocities"].values():
            speed = np.linalg.norm(velocity)
            max_velocity = max(max_velocity, speed)
        
        # 如果最大速度低于阈值，则认为已经稳定
        is_settled = max_velocity < self.sleep_threshold
        
        if is_settled and not ragdoll["is_sleeping"]:
            ragdoll["is_sleeping"] = True
            ragdoll["state"] = RagdollState.SETTLING
            logger.info(f"布娃娃已稳定: {ragdoll_id}")
        
        return is_settled
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = self.stats.copy()
        stats["total_ragdolls"] = len(self.ragdolls)
        stats["gravity"] = self.gravity
        
        return stats
    
    def cleanup_ragdoll(self, ragdoll_id: str):
        """清理布娃娃"""
        if ragdoll_id not in self.ragdolls:
            return
        
        self.deactivate_ragdoll(ragdoll_id)
        
        del self.ragdolls[ragdoll_id]
        del self.ragdoll_bones[ragdoll_id]
        del self.ragdoll_constraints[ragdoll_id]
        
        self.stats["active_ragdolls"] -= 1
        logger.info(f"清理布娃娃: {ragdoll_id}")
    
    def cleanup(self):
        """清理整个系统"""
        for ragdoll_id in list(self.ragdolls.keys()):
            self.cleanup_ragdoll(ragdoll_id)
        
        logger.info("布娃娃系统清理完成")

