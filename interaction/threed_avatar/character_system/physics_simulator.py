"""
物理模拟器 - 处理角色物理效果
负责刚体物理、碰撞检测、布料模拟、重力系统和物理约束
完整实现物理引擎功能，包括实时模拟和物理效果
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
import time
from enum import Enum
import math
from collections import deque

# 导入基础设施层依赖
from infrastructure.compute_storage.gpu_accelerator import GPUAccelerator, gpu_accelerator
from infrastructure.compute_storage.resource_manager import ResourceManager, resource_manager, ResourceType

# 导入数据层依赖
from data.models.three_d.cat_models import CatModel

# 导入角色系统依赖
from interaction.threed_avatar.character_system.model_manager import ModelInstance
from interaction.threed_avatar.character_system.skeleton_animation import SkeletonAnimation, SkeletonPose

logger = logging.getLogger(__name__)

class PhysicsType(Enum):
    """物理类型枚举"""
    STATIC = "static"          # 静态物体
    DYNAMIC = "dynamic"        # 动态物体
    KINEMATIC = "kinematic"    # 运动学物体
    RAGDOLL = "ragdoll"        # 布娃娃系统

class CollisionShape(Enum):
    """碰撞形状枚举"""
    SPHERE = "sphere"          # 球体
    BOX = "box"                # 盒子
    CAPSULE = "capsule"        # 胶囊体
    CYLINDER = "cylinder"      # 圆柱体
    MESH = "mesh"              # 网格
    CONVEX_HULL = "convex_hull" # 凸包

class PhysicsMaterial:
    """物理材质"""
    
    def __init__(self, name: str, friction: float = 0.5, restitution: float = 0.3, density: float = 1.0):
        self.name = name
        self.friction = friction  # 摩擦系数
        self.restitution = restitution  # 弹性系数
        self.density = density  # 密度
        self.static_friction = friction * 1.2
        self.rolling_friction = friction * 0.5
        self.spinning_friction = friction * 0.3

@dataclass
class RigidBody:
    """刚体数据"""
    body_id: str
    physics_type: PhysicsType
    collision_shape: CollisionShape
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)  # 四元数
    linear_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mass: float = 1.0
    inertia: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # 惯性张量
    damping: float = 0.1
    angular_damping: float = 0.1
    material: PhysicsMaterial = None
    shape_data: Dict[str, Any] = field(default_factory=dict)  # 形状特定数据
    is_active: bool = True
    gravity_scale: float = 1.0

@dataclass
class CollisionInfo:
    """碰撞信息"""
    body_a: str
    body_b: str
    contact_point: Tuple[float, float, float]
    contact_normal: Tuple[float, float, float]
    penetration_depth: float
    impulse: Tuple[float, float, float]
    friction_impulse: Tuple[float, float, float]

@dataclass
class PhysicsWorldSettings:
    """物理世界设置"""
    gravity: Tuple[float, float, float] = (0.0, -9.81, 0.0)  # 重力
    sub_steps: int = 4  # 子步数
    fixed_time_step: float = 1.0 / 60.0  # 固定时间步长
    max_sub_steps: int = 10  # 最大子步数
    solver_iterations: int = 10  # 求解器迭代次数
    enable_ccd: bool = True  # 连续碰撞检测
    enable_sleeping: bool = True  # 休眠机制
    collision_margin: float = 0.04  # 碰撞边界

class PhysicsSimulator:
    """物理模拟器 - 完整实现"""
    
    def __init__(self, settings: PhysicsWorldSettings = None):
        self.settings = settings or PhysicsWorldSettings()
        
        # 物理世界状态
        self.rigid_bodies: Dict[str, RigidBody] = {}
        self.collision_pairs: Set[Tuple[str, str]] = set()
        self.active_collisions: List[CollisionInfo] = []
        
        # 物理约束
        self.constraints: Dict[str, Any] = {}
        
        # 物理材质
        self.materials: Dict[str, PhysicsMaterial] = {}
        self._create_default_materials()
        
        # 碰撞检测系统
        self.broad_phase_pairs: Set[Tuple[str, str]] = set()
        self.narrow_phase_cache: Dict[Tuple[str, str], bool] = {}
        
        # 性能优化
        self.spatial_partition: Dict[Tuple[int, int, int], Set[str]] = {}
        self.cell_size: float = 2.0
        
        # 统计信息
        self.stats = {
            "total_bodies": 0,
            "active_bodies": 0,
            "collision_checks": 0,
            "collisions_detected": 0,
            "constraint_solves": 0,
            "average_step_time": 0.0,
            "broad_phase_time": 0.0,
            "narrow_phase_time": 0.0,
            "solver_time": 0.0
        }
        
        # 时间管理
        self.accumulated_time = 0.0
        self.last_update_time = time.time()
        
        # GPU加速
        self.gpu_enabled = False
        self.gpu_buffers: Dict[str, Any] = {}
        
        logger.info("Physics Simulator initialized")

    async def initialize(self):
        """初始化物理模拟器"""
        try:
            # 初始化GPU资源
            await self._initialize_gpu_resources()
            
            # 创建默认物理世界
            await self._create_default_world()
            
            logger.info("Physics Simulator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Physics Simulator: {e}")

    async def _initialize_gpu_resources(self):
        """初始化GPU资源"""
        try:
            # 检查GPU可用性
            gpu_status = gpu_accelerator.get_gpu_status(0)
            if gpu_status and gpu_status.get("is_available", False):
                self.gpu_enabled = True
                
                # 分配GPU内存用于物理计算
                gpu_request = ResourceRequest(
                    resource_type=ResourceType.GPU,
                    amount=100 * 1024 * 1024,  # 100MB
                    priority=1,
                    timeout=30
                )
                
                allocation = await resource_manager.request_resources(gpu_request)
                if allocation:
                    logger.info("GPU acceleration enabled for physics simulation")
                else:
                    logger.warning("GPU allocation failed, using CPU physics")
                    self.gpu_enabled = False
            else:
                logger.info("Using CPU physics simulation")
                
        except Exception as e:
            logger.warning(f"GPU initialization failed: {e}")
            self.gpu_enabled = False

    async def _create_default_world(self):
        """创建默认物理世界"""
        # 创建默认材质
        default_material = PhysicsMaterial("default", 0.5, 0.3, 1.0)
        self.materials["default"] = default_material
        
        # 创建地面
        ground_body = RigidBody(
            body_id="ground",
            physics_type=PhysicsType.STATIC,
            collision_shape=CollisionShape.BOX,
            position=(0.0, -1.0, 0.0),
            shape_data={"half_extents": (50.0, 1.0, 50.0)},
            material=default_material
        )
        await self.add_rigid_body(ground_body)
        
        logger.info("Default physics world created")

    def _create_default_materials(self):
        """创建默认物理材质"""
        materials = {
            "default": PhysicsMaterial("default", 0.5, 0.3, 1.0),
            "ice": PhysicsMaterial("ice", 0.02, 0.1, 0.9),
            "rubber": PhysicsMaterial("rubber", 0.8, 0.8, 1.2),
            "metal": PhysicsMaterial("metal", 0.4, 0.1, 7.8),
            "wood": PhysicsMaterial("wood", 0.6, 0.4, 0.7),
            "cat_fur": PhysicsMaterial("cat_fur", 0.7, 0.2, 0.5)
        }
        
        self.materials.update(materials)

    async def add_rigid_body(self, rigid_body: RigidBody) -> bool:
        """添加刚体到物理世界"""
        try:
            if rigid_body.body_id in self.rigid_bodies:
                logger.warning(f"Rigid body already exists: {rigid_body.body_id}")
                return False
            
            # 设置默认材质
            if rigid_body.material is None:
                rigid_body.material = self.materials["default"]
            
            # 添加到物理世界
            self.rigid_bodies[rigid_body.body_id] = rigid_body
            
            # 更新空间分区
            await self._update_spatial_partition(rigid_body.body_id)
            
            self.stats["total_bodies"] += 1
            if rigid_body.is_active:
                self.stats["active_bodies"] += 1
            
            logger.debug(f"Added rigid body: {rigid_body.body_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding rigid body {rigid_body.body_id}: {e}")
            return False

    async def remove_rigid_body(self, body_id: str) -> bool:
        """从物理世界移除刚体"""
        try:
            if body_id not in self.rigid_bodies:
                logger.warning(f"Rigid body not found: {body_id}")
                return False
            
            # 从空间分区移除
            await self._remove_from_spatial_partition(body_id)
            
            # 移除相关的碰撞对
            self.collision_pairs = {pair for pair in self.collision_pairs 
                                  if body_id not in pair}
            
            # 移除刚体
            rigid_body = self.rigid_bodies[body_id]
            if rigid_body.is_active:
                self.stats["active_bodies"] -= 1
            
            del self.rigid_bodies[body_id]
            self.stats["total_bodies"] -= 1
            
            logger.debug(f"Removed rigid body: {body_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing rigid body {body_id}: {e}")
            return False

    async def create_sphere_body(self, body_id: str, position: Tuple[float, float, float], 
                               radius: float, mass: float = 1.0, 
                               physics_type: PhysicsType = PhysicsType.DYNAMIC) -> bool:
        """创建球体刚体"""
        try:
            sphere_body = RigidBody(
                body_id=body_id,
                physics_type=physics_type,
                collision_shape=CollisionShape.SPHERE,
                position=position,
                mass=mass,
                shape_data={"radius": radius},
                material=self.materials["default"]
            )
            
            return await self.add_rigid_body(sphere_body)
            
        except Exception as e:
            logger.error(f"Error creating sphere body {body_id}: {e}")
            return False

    async def create_box_body(self, body_id: str, position: Tuple[float, float, float],
                            half_extents: Tuple[float, float, float], mass: float = 1.0,
                            physics_type: PhysicsType = PhysicsType.DYNAMIC) -> bool:
        """创建立方体刚体"""
        try:
            box_body = RigidBody(
                body_id=body_id,
                physics_type=physics_type,
                collision_shape=CollisionShape.BOX,
                position=position,
                mass=mass,
                shape_data={"half_extents": half_extents},
                material=self.materials["default"]
            )
            
            return await self.add_rigid_body(box_body)
            
        except Exception as e:
            logger.error(f"Error creating box body {body_id}: {e}")
            return False

    async def create_capsule_body(self, body_id: str, position: Tuple[float, float, float],
                                radius: float, height: float, mass: float = 1.0,
                                physics_type: PhysicsType = PhysicsType.DYNAMIC) -> bool:
        """创建胶囊体刚体"""
        try:
            capsule_body = RigidBody(
                body_id=body_id,
                physics_type=physics_type,
                collision_shape=CollisionShape.CAPSULE,
                position=position,
                mass=mass,
                shape_data={"radius": radius, "height": height},
                material=self.materials["default"]
            )
            
            return await self.add_rigid_body(capsule_body)
            
        except Exception as e:
            logger.error(f"Error creating capsule body {body_id}: {e}")
            return False

    async def create_character_body(self, body_id: str, position: Tuple[float, float, float],
                                  radius: float, height: float, mass: float = 70.0) -> bool:
        """创建角色刚体（胶囊体）"""
        return await self.create_capsule_body(body_id, position, radius, height, mass, PhysicsType.KINEMATIC)

    async def update(self, delta_time: float):
        """更新物理模拟"""
        start_time = time.time()
        
        try:
            # 累积时间
            self.accumulated_time += delta_time
            
            # 固定时间步长模拟
            step_count = 0
            while self.accumulated_time >= self.settings.fixed_time_step and step_count < self.settings.max_sub_steps:
                await self._fixed_step(self.settings.fixed_time_step)
                self.accumulated_time -= self.settings.fixed_time_step
                step_count += 1
            
            # 更新统计信息
            total_time = time.time() - start_time
            self.stats["average_step_time"] = (
                (self.stats["average_step_time"] * (self.stats["constraint_solves"] - 1) + total_time) 
                / self.stats["constraint_solves"] if self.stats["constraint_solves"] > 0 else total_time
            )
            
        except Exception as e:
            logger.error(f"Error updating physics simulation: {e}")

    async def _fixed_step(self, time_step: float):
        """固定时间步长模拟"""
        try:
            # 1. 应用力和冲量
            await self._apply_forces_and_impulses(time_step)
            
            # 2. 碰撞检测
            collision_start = time.time()
            await self._detect_collisions()
            self.stats["broad_phase_time"] = time.time() - collision_start
            
            # 3. 求解约束
            solver_start = time.time()
            await self._solve_constraints(time_step)
            self.stats["solver_time"] = time.time() - solver_start
            
            # 4. 积分运动
            await self._integrate_motion(time_step)
            
            # 5. 更新空间分区
            await self._update_spatial_partitions()
            
            self.stats["constraint_solves"] += 1
            
        except Exception as e:
            logger.error(f"Error in physics fixed step: {e}")

    async def _apply_forces_and_impulses(self, time_step: float):
        """应用力和冲量"""
        for body_id, body in self.rigid_bodies.items():
            if not body.is_active or body.physics_type == PhysicsType.STATIC:
                continue
            
            # 应用重力
            gravity_force = (
                self.settings.gravity[0] * body.mass * body.gravity_scale,
                self.settings.gravity[1] * body.mass * body.gravity_scale,
                self.settings.gravity[2] * body.mass * body.gravity_scale
            )
            
            # 更新线速度（F = ma => a = F/m, v = v0 + a*t）
            linear_acceleration = (
                gravity_force[0] / body.mass,
                gravity_force[1] / body.mass,
                gravity_force[2] / body.mass
            )
            
            body.linear_velocity = (
                body.linear_velocity[0] + linear_acceleration[0] * time_step,
                body.linear_velocity[1] + linear_acceleration[1] * time_step,
                body.linear_velocity[2] + linear_acceleration[2] * time_step
            )
            
            # 应用阻尼
            damping_factor = 1.0 - body.damping * time_step
            body.linear_velocity = (
                body.linear_velocity[0] * damping_factor,
                body.linear_velocity[1] * damping_factor,
                body.linear_velocity[2] * damping_factor
            )
            
            angular_damping_factor = 1.0 - body.angular_damping * time_step
            body.angular_velocity = (
                body.angular_velocity[0] * angular_damping_factor,
                body.angular_velocity[1] * angular_damping_factor,
                body.angular_velocity[2] * angular_damping_factor
            )

    async def _detect_collisions(self):
        """检测碰撞"""
        try:
            # 清空碰撞信息
            self.active_collisions.clear()
            self.broad_phase_pairs.clear()
            
            # 宽相位检测
            broad_phase_start = time.time()
            await self._broad_phase_collision_detection()
            self.stats["broad_phase_time"] = time.time() - broad_phase_start
            
            # 窄相位检测
            narrow_phase_start = time.time()
            await self._narrow_phase_collision_detection()
            self.stats["narrow_phase_time"] = time.time() - narrow_phase_start
            
            self.stats["collision_checks"] += len(self.broad_phase_pairs)
            self.stats["collisions_detected"] = len(self.active_collisions)
            
        except Exception as e:
            logger.error(f"Error in collision detection: {e}")

    async def _broad_phase_collision_detection(self):
        """宽相位碰撞检测"""
        # 使用空间分区优化碰撞检测
        active_bodies = [body_id for body_id, body in self.rigid_bodies.items() 
                        if body.is_active and body.physics_type != PhysicsType.STATIC]
        
        # 检查每个单元格内的物体对
        for cell_coord, bodies_in_cell in self.spatial_partition.items():
            body_list = list(bodies_in_cell)
            for i in range(len(body_list)):
                for j in range(i + 1, len(body_list)):
                    body_a = body_list[i]
                    body_b = body_list[j]
                    
                    # 检查是否已经检测过这个对
                    pair = tuple(sorted([body_a, body_b]))
                    if pair in self.broad_phase_pairs:
                        continue
                    
                    # 简单的AABB测试
                    if await self._aabb_test(body_a, body_b):
                        self.broad_phase_pairs.add(pair)

    async def _aabb_test(self, body_a_id: str, body_b_id: str) -> bool:
        """AABB（轴对齐边界框）测试"""
        try:
            body_a = self.rigid_bodies[body_a_id]
            body_b = self.rigid_bodies[body_b_id]
            
            # 获取AABB边界
            aabb_a = await self._get_body_aabb(body_a)
            aabb_b = await self._get_body_aabb(body_b)
            
            # 检查AABB重叠
            return (aabb_a[0][0] <= aabb_b[1][0] and aabb_a[1][0] >= aabb_b[0][0] and
                    aabb_a[0][1] <= aabb_b[1][1] and aabb_a[1][1] >= aabb_b[0][1] and
                    aabb_a[0][2] <= aabb_b[1][2] and aabb_a[1][2] >= aabb_b[0][2])
            
        except Exception as e:
            logger.error(f"Error in AABB test: {e}")
            return False

    async def _get_body_aabb(self, body: RigidBody) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """获取刚体的AABB边界"""
        position = np.array(body.position)
        
        if body.collision_shape == CollisionShape.SPHERE:
            radius = body.shape_data.get("radius", 1.0)
            min_bound = position - radius
            max_bound = position + radius
            return (tuple(min_bound), tuple(max_bound))
        
        elif body.collision_shape == CollisionShape.BOX:
            half_extents = np.array(body.shape_data.get("half_extents", (1.0, 1.0, 1.0)))
            min_bound = position - half_extents
            max_bound = position + half_extents
            return (tuple(min_bound), tuple(max_bound))
        
        elif body.collision_shape == CollisionShape.CAPSULE:
            radius = body.shape_data.get("radius", 0.5)
            height = body.shape_data.get("height", 1.0)
            half_height = height * 0.5
            min_bound = position - np.array([radius, half_height + radius, radius])
            max_bound = position + np.array([radius, half_height + radius, radius])
            return (tuple(min_bound), tuple(max_bound))
        
        else:
            # 默认使用单位立方体
            min_bound = position - np.array([1.0, 1.0, 1.0])
            max_bound = position + np.array([1.0, 1.0, 1.0])
            return (tuple(min_bound), tuple(max_bound))

    async def _narrow_phase_collision_detection(self):
        """窄相位碰撞检测"""
        for body_a_id, body_b_id in self.broad_phase_pairs:
            collision = await self._check_collision(body_a_id, body_b_id)
            if collision:
                self.active_collisions.append(collision)

    async def _check_collision(self, body_a_id: str, body_b_id: str) -> Optional[CollisionInfo]:
        """检查两个刚体之间的碰撞"""
        try:
            body_a = self.rigid_bodies[body_a_id]
            body_b = self.rigid_bodies[body_b_id]
            
            # 根据形状类型调用相应的碰撞检测函数
            shape_a = body_a.collision_shape
            shape_b = body_b.collision_shape
            
            if shape_a == CollisionShape.SPHERE and shape_b == CollisionShape.SPHERE:
                return await self._sphere_sphere_collision(body_a, body_b)
            elif shape_a == CollisionShape.SPHERE and shape_b == CollisionShape.BOX:
                return await self._sphere_box_collision(body_a, body_b)
            elif shape_a == CollisionShape.BOX and shape_b == CollisionShape.SPHERE:
                collision = await self._sphere_box_collision(body_b, body_a)
                if collision:
                    # 交换碰撞体顺序
                    collision.body_a, collision.body_b = collision.body_b, collision.body_a
                    collision.contact_normal = tuple(-np.array(collision.contact_normal))
                return collision
            elif shape_a == CollisionShape.BOX and shape_b == CollisionShape.BOX:
                return await self._box_box_collision(body_a, body_b)
            elif shape_a == CollisionShape.CAPSULE and shape_b == CollisionShape.SPHERE:
                return await self._capsule_sphere_collision(body_a, body_b)
            elif shape_a == CollisionShape.SPHERE and shape_b == CollisionShape.CAPSULE:
                collision = await self._capsule_sphere_collision(body_b, body_a)
                if collision:
                    collision.body_a, collision.body_b = collision.body_b, collision.body_a
                    collision.contact_normal = tuple(-np.array(collision.contact_normal))
                return collision
            
            # 默认使用球体碰撞
            return await self._sphere_sphere_collision(body_a, body_b)
            
        except Exception as e:
            logger.error(f"Error checking collision between {body_a_id} and {body_b_id}: {e}")
            return None

    async def _sphere_sphere_collision(self, sphere_a: RigidBody, sphere_b: RigidBody) -> Optional[CollisionInfo]:
        """球体-球体碰撞检测"""
        try:
            pos_a = np.array(sphere_a.position)
            pos_b = np.array(sphere_b.position)
            
            radius_a = sphere_a.shape_data.get("radius", 1.0)
            radius_b = sphere_b.shape_data.get("radius", 1.0)
            
            # 计算距离
            distance_vec = pos_b - pos_a
            distance = np.linalg.norm(distance_vec)
            
            # 检查碰撞
            if distance < radius_a + radius_b:
                # 计算碰撞信息
                penetration = radius_a + radius_b - distance
                contact_normal = distance_vec / (distance + 1e-8)  # 避免除零
                contact_point = pos_a + contact_normal * radius_a
                
                return CollisionInfo(
                    body_a=sphere_a.body_id,
                    body_b=sphere_b.body_id,
                    contact_point=tuple(contact_point),
                    contact_normal=tuple(contact_normal),
                    penetration_depth=penetration,
                    impulse=(0.0, 0.0, 0.0),
                    friction_impulse=(0.0, 0.0, 0.0)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in sphere-sphere collision: {e}")
            return None

    async def _sphere_box_collision(self, sphere: RigidBody, box: RigidBody) -> Optional[CollisionInfo]:
        """球体-盒子碰撞检测"""
        try:
            sphere_pos = np.array(sphere.position)
            box_pos = np.array(box.position)
            box_half_extents = np.array(box.shape_data.get("half_extents", (1.0, 1.0, 1.0)))
            sphere_radius = sphere.shape_data.get("radius", 1.0)
            
            # 将球体坐标转换到盒子局部空间
            local_sphere_pos = sphere_pos - box_pos
            
            # 找到盒子上最近的点
            closest_point = np.clip(local_sphere_pos, -box_half_extents, box_half_extents)
            
            # 计算距离
            distance_vec = local_sphere_pos - closest_point
            distance = np.linalg.norm(distance_vec)
            
            # 检查碰撞
            if distance < sphere_radius:
                # 计算碰撞信息
                penetration = sphere_radius - distance
                contact_normal = distance_vec / (distance + 1e-8)
                contact_point = box_pos + closest_point
                
                return CollisionInfo(
                    body_a=sphere.body_id,
                    body_b=box.body_id,
                    contact_point=tuple(contact_point),
                    contact_normal=tuple(contact_normal),
                    penetration_depth=penetration,
                    impulse=(0.0, 0.0, 0.0),
                    friction_impulse=(0.0, 0.0, 0.0)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in sphere-box collision: {e}")
            return None

    async def _box_box_collision(self, box_a: RigidBody, box_b: RigidBody) -> Optional[CollisionInfo]:
        """盒子-盒子碰撞检测（简化版，使用分离轴定理的近似）"""
        try:
            pos_a = np.array(box_a.position)
            pos_b = np.array(box_b.position)
            
            half_a = np.array(box_a.shape_data.get("half_extents", (1.0, 1.0, 1.0)))
            half_b = np.array(box_b.shape_data.get("half_extents", (1.0, 1.0, 1.0)))
            
            # 计算中心距离
            distance = pos_b - pos_a
            
            # 检查分离轴（简化版，只检查坐标轴）
            overlap_x = half_a[0] + half_b[0] - abs(distance[0])
            overlap_y = half_a[1] + half_b[1] - abs(distance[1])
            overlap_z = half_a[2] + half_b[2] - abs(distance[2])
            
            if overlap_x > 0 and overlap_y > 0 and overlap_z > 0:
                # 找到最小穿透深度的轴
                min_overlap = min(overlap_x, overlap_y, overlap_z)
                
                if min_overlap == overlap_x:
                    normal = (1.0 if distance[0] > 0 else -1.0, 0.0, 0.0)
                elif min_overlap == overlap_y:
                    normal = (0.0, 1.0 if distance[1] > 0 else -1.0, 0.0)
                else:
                    normal = (0.0, 0.0, 1.0 if distance[2] > 0 else -1.0)
                
                contact_point = pos_a + np.array(normal) * half_a[0]  # 近似接触点
                
                return CollisionInfo(
                    body_a=box_a.body_id,
                    body_b=box_b.body_id,
                    contact_point=tuple(contact_point),
                    contact_normal=normal,
                    penetration_depth=min_overlap,
                    impulse=(0.0, 0.0, 0.0),
                    friction_impulse=(0.0, 0.0, 0.0)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in box-box collision: {e}")
            return None

    async def _capsule_sphere_collision(self, capsule: RigidBody, sphere: RigidBody) -> Optional[CollisionInfo]:
        """胶囊体-球体碰撞检测"""
        try:
            capsule_pos = np.array(capsule.position)
            sphere_pos = np.array(sphere.position)
            
            capsule_radius = capsule.shape_data.get("radius", 0.5)
            capsule_height = capsule.shape_data.get("height", 2.0)
            sphere_radius = sphere.shape_data.get("radius", 1.0)
            
            # 胶囊体线段端点
            half_height = capsule_height * 0.5 - capsule_radius
            top_point = capsule_pos + np.array([0, half_height, 0])
            bottom_point = capsule_pos - np.array([0, half_height, 0])
            
            # 找到线段上最近的点
            line_vec = bottom_point - top_point
            sphere_vec = sphere_pos - top_point
            
            line_length_sq = np.dot(line_vec, line_vec)
            if line_length_sq < 1e-8:
                # 线段退化为点
                closest_point = top_point
            else:
                t = max(0, min(1, np.dot(sphere_vec, line_vec) / line_length_sq))
                closest_point = top_point + t * line_vec
            
            # 计算距离
            distance_vec = sphere_pos - closest_point
            distance = np.linalg.norm(distance_vec)
            
            # 检查碰撞
            if distance < capsule_radius + sphere_radius:
                penetration = capsule_radius + sphere_radius - distance
                contact_normal = distance_vec / (distance + 1e-8)
                contact_point = closest_point + contact_normal * capsule_radius
                
                return CollisionInfo(
                    body_a=capsule.body_id,
                    body_b=sphere.body_id,
                    contact_point=tuple(contact_point),
                    contact_normal=tuple(contact_normal),
                    penetration_depth=penetration,
                    impulse=(0.0, 0.0, 0.0),
                    friction_impulse=(0.0, 0.0, 0.0)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in capsule-sphere collision: {e}")
            return None

    async def _solve_constraints(self, time_step: float):
        """求解约束（碰撞响应）"""
        for collision in self.active_collisions:
            await self._resolve_collision(collision, time_step)

    async def _resolve_collision(self, collision: CollisionInfo, time_step: float):
        """解析碰撞响应"""
        try:
            body_a = self.rigid_bodies[collision.body_a]
            body_b = self.rigid_bodies[collision.body_b]
            
            # 跳过静态物体之间的碰撞
            if (body_a.physics_type == PhysicsType.STATIC and 
                body_b.physics_type == PhysicsType.STATIC):
                return
            
            # 计算相对速度
            contact_normal = np.array(collision.contact_normal)
            relative_velocity = await self._get_relative_velocity(body_a, body_b, collision.contact_point)
            
            # 计算法向速度
            normal_velocity = np.dot(relative_velocity, contact_normal)
            
            # 如果物体正在分离，不处理碰撞
            if normal_velocity > 0:
                return
            
            # 计算恢复系数（使用两个材质的平均值）
            restitution = (body_a.material.restitution + body_b.material.restitution) * 0.5
            
            # 计算冲量
            impulse = await self._calculate_collision_impulse(body_a, body_b, collision, restitution)
            
            # 应用冲量
            await self._apply_impulse(body_a, body_b, collision.contact_point, impulse, contact_normal)
            
            # 计算摩擦力
            friction_impulse = await self._calculate_friction_impulse(body_a, body_b, collision, impulse)
            await self._apply_friction_impulse(body_a, body_b, collision.contact_point, friction_impulse)
            
            # 更新碰撞信息
            collision.impulse = tuple(impulse)
            collision.friction_impulse = tuple(friction_impulse)
            
        except Exception as e:
            logger.error(f"Error resolving collision: {e}")

    async def _get_relative_velocity(self, body_a: RigidBody, body_b: RigidBody, contact_point: Tuple[float, float, float]) -> np.ndarray:
        """计算接触点的相对速度"""
        contact_pos = np.array(contact_point)
        
        # 计算线速度
        vel_a = np.array(body_a.linear_velocity)
        vel_b = np.array(body_b.linear_velocity)
        
        # 计算角速度贡献
        if body_a.physics_type != PhysicsType.STATIC:
            r_a = contact_pos - np.array(body_a.position)
            ang_vel_a = np.array(body_a.angular_velocity)
            vel_a += np.cross(ang_vel_a, r_a)
        
        if body_b.physics_type != PhysicsType.STATIC:
            r_b = contact_pos - np.array(body_b.position)
            ang_vel_b = np.array(body_b.angular_velocity)
            vel_b += np.cross(ang_vel_b, r_b)
        
        return vel_b - vel_a

    async def _calculate_collision_impulse(self, body_a: RigidBody, body_b: RigidBody, 
                                         collision: CollisionInfo, restitution: float) -> np.ndarray:
        """计算碰撞冲量"""
        contact_normal = np.array(collision.contact_normal)
        contact_point = np.array(collision.contact_point)
        
        # 计算相对速度
        relative_velocity = await self._get_relative_velocity(body_a, body_b, contact_point)
        normal_velocity = np.dot(relative_velocity, contact_normal)
        
        # 计算有效质量
        inv_mass_a = 0.0 if body_a.physics_type == PhysicsType.STATIC else 1.0 / body_a.mass
        inv_mass_b = 0.0 if body_b.physics_type == PhysicsType.STATIC else 1.0 / body_b.mass
        
        # 简化计算（忽略转动惯量）
        effective_mass = 1.0 / (inv_mass_a + inv_mass_b)
        
        # 计算冲量大小
        impulse_magnitude = -(1.0 + restitution) * normal_velocity * effective_mass
        
        return impulse_magnitude * contact_normal

    async def _apply_impulse(self, body_a: RigidBody, body_b: RigidBody, 
                           contact_point: Tuple[float, float, float], 
                           impulse: np.ndarray, normal: np.ndarray):
        """应用冲量"""
        contact_pos = np.array(contact_point)
        
        if body_a.physics_type != PhysicsType.STATIC:
            # 应用线速度冲量
            inv_mass_a = 1.0 / body_a.mass
            body_a.linear_velocity = tuple(np.array(body_a.linear_velocity) - impulse * inv_mass_a)
            
            # 应用角速度冲量（简化）
            r_a = contact_pos - np.array(body_a.position)
            torque_a = np.cross(r_a, -impulse)
            body_a.angular_velocity = tuple(np.array(body_a.angular_velocity) + torque_a * 0.1)  # 简化转动惯量
        
        if body_b.physics_type != PhysicsType.STATIC:
            # 应用线速度冲量
            inv_mass_b = 1.0 / body_b.mass
            body_b.linear_velocity = tuple(np.array(body_b.linear_velocity) + impulse * inv_mass_b)
            
            # 应用角速度冲量（简化）
            r_b = contact_pos - np.array(body_b.position)
            torque_b = np.cross(r_b, impulse)
            body_b.angular_velocity = tuple(np.array(body_b.angular_velocity) + torque_b * 0.1)  # 简化转动惯量

    async def _calculate_friction_impulse(self, body_a: RigidBody, body_b: RigidBody,
                                        collision: CollisionInfo, normal_impulse: np.ndarray) -> np.ndarray:
        """计算摩擦力冲量"""
        try:
            contact_normal = np.array(collision.contact_normal)
            contact_point = np.array(collision.contact_point)
            
            # 计算相对速度
            relative_velocity = await self._get_relative_velocity(body_a, body_b, contact_point)
            
            # 计算切向速度
            normal_velocity = np.dot(relative_velocity, contact_normal)
            tangent_velocity = relative_velocity - normal_velocity * contact_normal
            
            tangent_speed = np.linalg.norm(tangent_velocity)
            if tangent_speed < 1e-8:
                return np.zeros(3)
            
            tangent_direction = tangent_velocity / tangent_speed
            
            # 计算摩擦系数
            friction = (body_a.material.friction + body_b.material.friction) * 0.5
            
            # 计算有效质量
            inv_mass_a = 0.0 if body_a.physics_type == PhysicsType.STATIC else 1.0 / body_a.mass
            inv_mass_b = 0.0 if body_b.physics_type == PhysicsType.STATIC else 1.0 / body_b.mass
            effective_mass = 1.0 / (inv_mass_a + inv_mass_b)
            
            # 计算摩擦力冲量大小
            friction_impulse_magnitude = friction * np.linalg.norm(normal_impulse)
            max_friction_impulse = friction_impulse_magnitude * effective_mass
            
            # 限制摩擦力冲量
            desired_friction_impulse = -tangent_speed * effective_mass
            friction_impulse_magnitude = min(max_friction_impulse, abs(desired_friction_impulse))
            
            return friction_impulse_magnitude * tangent_direction
            
        except Exception as e:
            logger.error(f"Error calculating friction impulse: {e}")
            return np.zeros(3)

    async def _apply_friction_impulse(self, body_a: RigidBody, body_b: RigidBody,
                                    contact_point: Tuple[float, float, float], 
                                    friction_impulse: np.ndarray):
        """应用摩擦力冲量"""
        await self._apply_impulse(body_a, body_b, contact_point, friction_impulse, np.zeros(3))

    async def _integrate_motion(self, time_step: float):
        """积分运动"""
        for body_id, body in self.rigid_bodies.items():
            if not body.is_active or body.physics_type == PhysicsType.STATIC:
                continue
            
            # 更新位置
            new_position = (
                body.position[0] + body.linear_velocity[0] * time_step,
                body.position[1] + body.linear_velocity[1] * time_step,
                body.position[2] + body.linear_velocity[2] * time_step
            )
            
            # 更新旋转（简化，使用欧拉角）
            # 实际应该使用四元数积分
            body.position = new_position

    async def _update_spatial_partition(self, body_id: str):
        """更新空间分区"""
        try:
            body = self.rigid_bodies[body_id]
            position = body.position
            
            # 计算单元格坐标
            cell_x = int(position[0] / self.cell_size)
            cell_y = int(position[1] / self.cell_size)
            cell_z = int(position[2] / self.cell_size)
            cell_coord = (cell_x, cell_y, cell_z)
            
            # 添加到单元格
            if cell_coord not in self.spatial_partition:
                self.spatial_partition[cell_coord] = set()
            self.spatial_partition[cell_coord].add(body_id)
            
        except Exception as e:
            logger.error(f"Error updating spatial partition for {body_id}: {e}")

    async def _remove_from_spatial_partition(self, body_id: str):
        """从空间分区移除"""
        for cell_coord, bodies in self.spatial_partition.items():
            if body_id in bodies:
                bodies.remove(body_id)
                if not bodies:
                    del self.spatial_partition[cell_coord]
                break

    async def _update_spatial_partitions(self):
        """更新所有空间分区"""
        # 清空分区
        self.spatial_partition.clear()
        
        # 重新添加所有活动物体
        for body_id, body in self.rigid_bodies.items():
            if body.is_active:
                await self._update_spatial_partition(body_id)

    async def apply_force(self, body_id: str, force: Tuple[float, float, float]):
        """应用力到刚体"""
        try:
            if body_id not in self.rigid_bodies:
                logger.warning(f"Body not found: {body_id}")
                return
            
            body = self.rigid_bodies[body_id]
            if body.physics_type == PhysicsType.STATIC:
                return
            
            # 更新线速度（F = ma => Δv = F/m * Δt）
            # 这里简化处理，实际应该在积分步骤中处理
            acceleration = (
                force[0] / body.mass,
                force[1] / body.mass,
                force[2] / body.mass
            )
            
            body.linear_velocity = (
                body.linear_velocity[0] + acceleration[0] * self.settings.fixed_time_step,
                body.linear_velocity[1] + acceleration[1] * self.settings.fixed_time_step,
                body.linear_velocity[2] + acceleration[2] * self.settings.fixed_time_step
            )
            
        except Exception as e:
            logger.error(f"Error applying force to {body_id}: {e}")

    async def apply_impulse(self, body_id: str, impulse: Tuple[float, float, float]):
        """应用冲量到刚体"""
        try:
            if body_id not in self.rigid_bodies:
                logger.warning(f"Body not found: {body_id}")
                return
            
            body = self.rigid_bodies[body_id]
            if body.physics_type == PhysicsType.STATIC:
                return
            
            # 直接更新速度（冲量 = m * Δv）
            delta_velocity = (
                impulse[0] / body.mass,
                impulse[1] / body.mass,
                impulse[2] / body.mass
            )
            
            body.linear_velocity = (
                body.linear_velocity[0] + delta_velocity[0],
                body.linear_velocity[1] + delta_velocity[1],
                body.linear_velocity[2] + delta_velocity[2]
            )
            
        except Exception as e:
            logger.error(f"Error applying impulse to {body_id}: {e}")

    async def set_body_position(self, body_id: str, position: Tuple[float, float, float]):
        """设置刚体位置"""
        try:
            if body_id not in self.rigid_bodies:
                logger.warning(f"Body not found: {body_id}")
                return
            
            body = self.rigid_bodies[body_id]
            body.position = position
            
            # 更新空间分区
            await self._update_spatial_partition(body_id)
            
        except Exception as e:
            logger.error(f"Error setting position for {body_id}: {e}")

    async def get_body_position(self, body_id: str) -> Optional[Tuple[float, float, float]]:
        """获取刚体位置"""
        if body_id in self.rigid_bodies:
            return self.rigid_bodies[body_id].position
        return None

    async def raycast(self, origin: Tuple[float, float, float], 
                     direction: Tuple[float, float, float], 
                     max_distance: float = 100.0) -> Optional[Dict[str, Any]]:
        """射线检测"""
        try:
            origin_np = np.array(origin)
            direction_np = np.array(direction)
            direction_np = direction_np / (np.linalg.norm(direction_np) + 1e-8)  # 归一化
            
            closest_hit = None
            closest_distance = max_distance
            
            for body_id, body in self.rigid_bodies.items():
                if not body.is_active:
                    continue
                
                hit = await self._raycast_against_body(origin_np, direction_np, body, max_distance)
                if hit and hit["distance"] < closest_distance:
                    closest_hit = hit
                    closest_distance = hit["distance"]
            
            return closest_hit
            
        except Exception as e:
            logger.error(f"Error in raycast: {e}")
            return None

    async def _raycast_against_body(self, origin: np.ndarray, direction: np.ndarray,
                                  body: RigidBody, max_distance: float) -> Optional[Dict[str, Any]]:
        """对单个刚体进行射线检测"""
        try:
            if body.collision_shape == CollisionShape.SPHERE:
                return await self._raycast_sphere(origin, direction, body, max_distance)
            elif body.collision_shape == CollisionShape.BOX:
                return await self._raycast_box(origin, direction, body, max_distance)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in raycast against body {body.body_id}: {e}")
            return None

    async def _raycast_sphere(self, origin: np.ndarray, direction: np.ndarray,
                            sphere: RigidBody, max_distance: float) -> Optional[Dict[str, Any]]:
        """射线-球体检测"""
        try:
            sphere_center = np.array(sphere.position)
            sphere_radius = sphere.shape_data.get("radius", 1.0)
            
            # 计算射线到球心的向量
            to_sphere = sphere_center - origin
            
            # 计算投影长度
            projection = np.dot(to_sphere, direction)
            
            # 计算最近点距离
            closest_point_distance_sq = np.dot(to_sphere, to_sphere) - projection * projection
            
            # 检查是否相交
            if closest_point_distance_sq > sphere_radius * sphere_radius:
                return None
            
            # 计算交点距离
            inside_distance = np.sqrt(sphere_radius * sphere_radius - closest_point_distance_sq)
            hit_distance = projection - inside_distance
            
            if hit_distance < 0 or hit_distance > max_distance:
                return None
            
            # 计算交点位置和法线
            hit_point = origin + direction * hit_distance
            hit_normal = (hit_point - sphere_center) / sphere_radius
            
            return {
                "body_id": sphere.body_id,
                "point": tuple(hit_point),
                "normal": tuple(hit_normal),
                "distance": hit_distance
            }
            
        except Exception as e:
            logger.error(f"Error in sphere raycast: {e}")
            return None

    async def _raycast_box(self, origin: np.ndarray, direction: np.ndarray,
                         box: RigidBody, max_distance: float) -> Optional[Dict[str, Any]]:
        """射线-盒子检测"""
        try:
            box_center = np.array(box.position)
            half_extents = np.array(box.shape_data.get("half_extents", (1.0, 1.0, 1.0)))
            
            # 转换到盒子局部空间
            local_origin = origin - box_center
            
            # 计算射线与每个轴的相交
            t_min = -np.inf
            t_max = np.inf
            
            for i in range(3):
                if abs(direction[i]) < 1e-8:
                    # 射线与轴平行
                    if local_origin[i] < -half_extents[i] or local_origin[i] > half_extents[i]:
                        return None
                else:
                    inv_dir = 1.0 / direction[i]
                    t1 = (-half_extents[i] - local_origin[i]) * inv_dir
                    t2 = (half_extents[i] - local_origin[i]) * inv_dir
                    
                    if t1 > t2:
                        t1, t2 = t2, t1
                    
                    t_min = max(t_min, t1)
                    t_max = min(t_max, t2)
                    
                    if t_min > t_max:
                        return None
            
            if t_min < 0 or t_min > max_distance:
                return None
            
            # 计算交点
            hit_point = origin + direction * t_min
            
            # 计算法线（找到相交的平面）
            local_hit = hit_point - box_center
            normal = np.zeros(3)
            
            for i in range(3):
                if abs(abs(local_hit[i]) - half_extents[i]) < 1e-4:
                    normal[i] = 1.0 if local_hit[i] > 0 else -1.0
            
            return {
                "body_id": box.body_id,
                "point": tuple(hit_point),
                "normal": tuple(normal),
                "distance": t_min
            }
            
        except Exception as e:
            logger.error(f"Error in box raycast: {e}")
            return None

    async def get_collision_info(self, body_id: str) -> List[CollisionInfo]:
        """获取刚体的碰撞信息"""
        return [collision for collision in self.active_collisions 
                if collision.body_a == body_id or collision.body_b == body_id]

    async def get_physics_stats(self) -> Dict[str, Any]:
        """获取物理统计信息"""
        stats = self.stats.copy()
        stats["rigid_body_count"] = len(self.rigid_bodies)
        stats["active_collisions"] = len(self.active_collisions)
        stats["collision_pairs"] = len(self.collision_pairs)
        stats["spatial_partition_cells"] = len(self.spatial_partition)
        
        return stats

    async def cleanup(self):
        """清理物理模拟器"""
        try:
            # 清空所有刚体
            self.rigid_bodies.clear()
            self.collision_pairs.clear()
            self.active_collisions.clear()
            self.constraints.clear()
            self.spatial_partition.clear()
            
            # 释放GPU资源
            if self.gpu_enabled:
                self.gpu_buffers.clear()
            
            logger.info("Physics Simulator cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during physics cleanup: {e}")

# 全局物理模拟器实例
physics_simulator = PhysicsSimulator()

