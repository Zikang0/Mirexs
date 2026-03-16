"""
碰撞检测器：检测物体碰撞
负责3D场景中的碰撞检测和物理交互
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)

class CollisionShapeType(Enum):
    """碰撞形状类型"""
    SPHERE = "sphere"
    BOX = "box"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"
    MESH = "mesh"
    PLANE = "plane"

@dataclass
class CollisionShape:
    """碰撞形状"""
    shape_id: str
    shape_type: CollisionShapeType
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)  # 四元数
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    
    # 形状特定参数
    radius: float = 1.0  # 球体、胶囊体、圆柱体
    height: float = 2.0  # 胶囊体、圆柱体
    half_extents: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # 盒子
    vertices: List[Tuple[float, float, float]] = None  # 网格
    indices: List[int] = None  # 网格
    normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)  # 平面
    distance: float = 0.0  # 平面
    
    # 物理属性
    mass: float = 1.0
    friction: float = 0.5
    restitution: float = 0.3
    is_static: bool = False
    collision_group: int = 1
    collision_mask: int = 0xFFFF

@dataclass
class CollisionContact:
    """碰撞接触点"""
    point_a: Tuple[float, float, float]  # 在物体A上的接触点
    point_b: Tuple[float, float, float]  # 在物体B上的接触点
    normal: Tuple[float, float, float]   # 碰撞法线（从A指向B）
    depth: float                         # 穿透深度
    impulse: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 冲量

@dataclass
class CollisionResult:
    """碰撞检测结果"""
    has_collision: bool
    contacts: List[CollisionContact]
    shape_a: str
    shape_b: str
    penetration_depth: float = 0.0

class CollisionDetector:
    """碰撞检测器"""
    
    def __init__(self):
        self.collision_shapes: Dict[str, CollisionShape] = {}
        self.broad_phase_pairs: Set[Tuple[str, str]] = set()
        self.contact_callbacks: Dict[str, Any] = {}
        
        # 空间划分优化
        self.spatial_grid: Dict[Tuple[int, int, int], Set[str]] = {}
        self.grid_size: float = 5.0
        
        # 性能统计
        self.stats = {
            "total_checks": 0,
            "collisions_found": 0,
            "broad_phase_time": 0.0,
            "narrow_phase_time": 0.0,
            "contact_resolution_time": 0.0
        }
        
        logger.info("碰撞检测器初始化完成")
    
    def add_collision_shape(self, shape: CollisionShape) -> bool:
        """添加碰撞形状"""
        if shape.shape_id in self.collision_shapes:
            logger.warning(f"碰撞形状已存在: {shape.shape_id}")
            return False
        
        self.collision_shapes[shape.shape_id] = shape
        self._update_spatial_grid(shape.shape_id)
        
        logger.info(f"添加碰撞形状: {shape.shape_id} ({shape.shape_type.value})")
        return True
    
    def remove_collision_shape(self, shape_id: str) -> bool:
        """移除碰撞形状"""
        if shape_id not in self.collision_shapes:
            logger.warning(f"碰撞形状不存在: {shape_id}")
            return False
        
        # 从空间网格中移除
        self._remove_from_spatial_grid(shape_id)
        
        # 移除相关的碰撞对
        self.broad_phase_pairs = {
            pair for pair in self.broad_phase_pairs 
            if shape_id not in pair
        }
        
        del self.collision_shapes[shape_id]
        logger.info(f"移除碰撞形状: {shape_id}")
        return True
    
    def update_shape_position(self, shape_id: str, position: Tuple[float, float, float]):
        """更新形状位置"""
        if shape_id not in self.collision_shapes:
            logger.warning(f"碰撞形状不存在: {shape_id}")
            return
        
        shape = self.collision_shapes[shape_id]
        shape.position = position
        
        # 更新空间网格
        self._update_spatial_grid(shape_id)
    
    def update_shape_rotation(self, shape_id: str, rotation: Tuple[float, float, float, float]):
        """更新形状旋转"""
        if shape_id not in self.collision_shapes:
            logger.warning(f"碰撞形状不存在: {shape_id}")
            return
        
        shape = self.collision_shapes[shape_id]
        shape.rotation = rotation
    
    def detect_collisions(self) -> List[CollisionResult]:
        """检测所有碰撞"""
        import time
        start_time = time.time()
        
        # 宽相位检测
        broad_phase_start = time.time()
        potential_pairs = self._broad_phase_detection()
        self.stats["broad_phase_time"] = time.time() - broad_phase_start
        
        # 窄相位检测
        narrow_phase_start = time.time()
        collision_results = []
        
        for shape_id_a, shape_id_b in potential_pairs:
            shape_a = self.collision_shapes[shape_id_a]
            shape_b = self.collision_shapes[shape_id_b]
            
            # 检查碰撞组和掩码
            if not self._check_collision_filter(shape_a, shape_b):
                continue
            
            result = self._narrow_phase_detection(shape_a, shape_b)
            if result.has_collision:
                collision_results.append(result)
                self._handle_collision_callbacks(result)
        
        self.stats["narrow_phase_time"] = time.time() - narrow_phase_start
        self.stats["total_checks"] += len(potential_pairs)
        self.stats["collisions_found"] += len(collision_results)
        self.stats["contact_resolution_time"] = time.time() - start_time
        
        return collision_results
    
    def _broad_phase_detection(self) -> List[Tuple[str, str]]:
        """宽相位检测 - 快速筛选可能的碰撞对"""
        potential_pairs = []
        shape_ids = list(self.collision_shapes.keys())
        
        # 使用空间网格优化
        grid_candidates = self._get_grid_candidates()
        
        # 检查每个网格中的形状对
        for shape_id_a, shape_id_b in grid_candidates:
            if shape_id_a >= shape_id_b:  # 避免重复检查
                continue
            
            shape_a = self.collision_shapes[shape_id_a]
            shape_b = self.collision_shapes[shape_id_b]
            
            # 简单的AABB检查
            if self._check_aabb_overlap(shape_a, shape_b):
                potential_pairs.append((shape_id_a, shape_id_b))
        
        return potential_pairs
    
    def _narrow_phase_detection(self, shape_a: CollisionShape, shape_b: CollisionShape) -> CollisionResult:
        """窄相位检测 - 精确碰撞检测"""
        # 根据形状类型选择相应的检测算法
        shape_types = (shape_a.shape_type, shape_b.shape_type)
        
        if CollisionShapeType.SPHERE in shape_types and CollisionShapeType.SPHERE in shape_types:
            return self._sphere_sphere_collision(shape_a, shape_b)
        elif CollisionShapeType.BOX in shape_types and CollisionShapeType.SPHERE in shape_types:
            if shape_a.shape_type == CollisionShapeType.SPHERE:
                return self._sphere_box_collision(shape_a, shape_b)
            else:
                return self._sphere_box_collision(shape_b, shape_a)
        elif CollisionShapeType.BOX in shape_types and CollisionShapeType.BOX in shape_types:
            return self._box_box_collision(shape_a, shape_b)
        elif CollisionShapeType.PLANE in shape_types:
            if shape_a.shape_type == CollisionShapeType.PLANE:
                return self._plane_shape_collision(shape_a, shape_b)
            else:
                return self._plane_shape_collision(shape_b, shape_a)
        else:
            # 默认使用GJK算法
            return self._gjk_collision_detection(shape_a, shape_b)
    
    def _sphere_sphere_collision(self, sphere_a: CollisionShape, sphere_b: CollisionShape) -> CollisionResult:
        """球体-球体碰撞检测"""
        pos_a = np.array(sphere_a.position)
        pos_b = np.array(sphere_b.position)
        
        distance = np.linalg.norm(pos_b - pos_a)
        min_distance = sphere_a.radius + sphere_b.radius
        
        if distance < min_distance:
            # 计算碰撞法线和接触点
            normal = (pos_b - pos_a) / distance if distance > 0 else np.array([1.0, 0.0, 0.0])
            contact_point = pos_a + normal * sphere_a.radius
            
            contact = CollisionContact(
                point_a=tuple(contact_point),
                point_b=tuple(contact_point - normal * (min_distance - distance)),
                normal=tuple(normal),
                depth=min_distance - distance
            )
            
            return CollisionResult(
                has_collision=True,
                contacts=[contact],
                shape_a=sphere_a.shape_id,
                shape_b=sphere_b.shape_id,
                penetration_depth=min_distance - distance
            )
        
        return CollisionResult(
            has_collision=False,
            contacts=[],
            shape_a=sphere_a.shape_id,
            shape_b=sphere_b.shape_id
        )
    
    def _sphere_box_collision(self, sphere: CollisionShape, box: CollisionShape) -> CollisionResult:
        """球体-盒子碰撞检测"""
        sphere_pos = np.array(sphere.position)
        box_pos = np.array(box.position)
        
        # 转换球体位置到盒子局部坐标系
        box_rotation = self._quaternion_to_matrix(box.rotation)
        local_sphere_pos = np.dot(box_rotation.T, sphere_pos - box_pos)
        
        # 计算最近点
        half_extents = np.array(box.half_extents) * np.array(box.scale)
        closest_point = np.clip(local_sphere_pos, -half_extents, half_extents)
        
        # 计算距离
        distance_vec = local_sphere_pos - closest_point
        distance = np.linalg.norm(distance_vec)
        
        if distance < sphere.radius:
            # 转换回世界坐标系
            world_closest = box_pos + np.dot(box_rotation, closest_point)
            world_normal = np.dot(box_rotation, distance_vec / distance if distance > 0 else np.array([1.0, 0.0, 0.0]))
            
            contact = CollisionContact(
                point_a=tuple(sphere_pos - world_normal * sphere.radius),
                point_b=tuple(world_closest),
                normal=tuple(world_normal),
                depth=sphere.radius - distance
            )
            
            return CollisionResult(
                has_collision=True,
                contacts=[contact],
                shape_a=sphere.shape_id,
                shape_b=box.shape_id,
                penetration_depth=sphere.radius - distance
            )
        
        return CollisionResult(
            has_collision=False,
            contacts=[],
            shape_a=sphere.shape_id,
            shape_b=box.shape_id
        )
    
    def _box_box_collision(self, box_a: CollisionShape, box_b: CollisionShape) -> CollisionResult:
        """盒子-盒子碰撞检测 (使用分离轴定理)"""
        # 简化的实现 - 实际应该使用完整的SAT算法
        pos_a = np.array(box_a.position)
        pos_b = np.array(box_b.position)
        
        # 简单的AABB检查
        half_a = np.array(box_a.half_extents) * np.array(box_a.scale)
        half_b = np.array(box_b.half_extents) * np.array(box_b.scale)
        
        overlap_x = abs(pos_a[0] - pos_b[0]) < (half_a[0] + half_b[0])
        overlap_y = abs(pos_a[1] - pos_b[1]) < (half_a[1] + half_b[1])
        overlap_z = abs(pos_a[2] - pos_b[2]) < (half_a[2] + half_b[2])
        
        if overlap_x and overlap_y and overlap_z:
            # 简化的接触点计算
            center_diff = pos_b - pos_a
            normal = center_diff / np.linalg.norm(center_diff) if np.linalg.norm(center_diff) > 0 else np.array([1.0, 0.0, 0.0])
            
            contact = CollisionContact(
                point_a=tuple(pos_a + normal * half_a[0]),
                point_b=tuple(pos_b - normal * half_b[0]),
                normal=tuple(normal),
                depth=(half_a[0] + half_b[0]) - abs(center_diff[0])
            )
            
            return CollisionResult(
                has_collision=True,
                contacts=[contact],
                shape_a=box_a.shape_id,
                shape_b=box_b.shape_id,
                penetration_depth=(half_a[0] + half_b[0]) - abs(center_diff[0])
            )
        
        return CollisionResult(
            has_collision=False,
            contacts=[],
            shape_a=box_a.shape_id,
            shape_b=box_b.shape_id
        )
    
    def _plane_shape_collision(self, plane: CollisionShape, shape: CollisionShape) -> CollisionResult:
        """平面-形状碰撞检测"""
        plane_normal = np.array(plane.normal)
        plane_point = plane_normal * plane.distance
        
        if shape.shape_type == CollisionShapeType.SPHERE:
            sphere_pos = np.array(shape.position)
            distance = np.dot(sphere_pos - plane_point, plane_normal)
            
            if distance < shape.radius:
                contact_point = sphere_pos - plane_normal * distance
                
                contact = CollisionContact(
                    point_a=tuple(contact_point),
                    point_b=tuple(contact_point),
                    normal=tuple(plane_normal),
                    depth=shape.radius - distance
                )
                
                return CollisionResult(
                    has_collision=True,
                    contacts=[contact],
                    shape_a=plane.shape_id,
                    shape_b=shape.shape_id,
                    penetration_depth=shape.radius - distance
                )
        
        return CollisionResult(
            has_collision=False,
            contacts=[],
            shape_a=plane.shape_id,
            shape_b=shape.shape_id
        )
    
    def _gjk_collision_detection(self, shape_a: CollisionShape, shape_b: CollisionShape) -> CollisionResult:
        """GJK算法碰撞检测 (用于复杂形状)"""
        # 简化的GJK实现 - 实际应该完整实现
        pos_a = np.array(shape_a.position)
        pos_b = np.array(shape_b.position)
        
        # 使用包围球作为简化
        if hasattr(shape_a, 'radius') and hasattr(shape_b, 'radius'):
            distance = np.linalg.norm(pos_b - pos_a)
            min_distance = getattr(shape_a, 'radius', 1.0) + getattr(shape_b, 'radius', 1.0)
            
            if distance < min_distance:
                normal = (pos_b - pos_a) / distance if distance > 0 else np.array([1.0, 0.0, 0.0])
                
                contact = CollisionContact(
                    point_a=tuple(pos_a + normal * getattr(shape_a, 'radius', 1.0)),
                    point_b=tuple(pos_b - normal * getattr(shape_b, 'radius', 1.0)),
                    normal=tuple(normal),
                    depth=min_distance - distance
                )
                
                return CollisionResult(
                    has_collision=True,
                    contacts=[contact],
                    shape_a=shape_a.shape_id,
                    shape_b=shape_b.shape_id,
                    penetration_depth=min_distance - distance
                )
        
        return CollisionResult(
            has_collision=False,
            contacts=[],
            shape_a=shape_a.shape_id,
            shape_b=shape_b.shape_id
        )
    
    def _check_aabb_overlap(self, shape_a: CollisionShape, shape_b: CollisionShape) -> bool:
        """检查AABB重叠"""
        aabb_a = self._compute_aabb(shape_a)
        aabb_b = self._compute_aabb(shape_b)
        
        return (
            aabb_a[0][0] <= aabb_b[1][0] and aabb_a[1][0] >= aabb_b[0][0] and
            aabb_a[0][1] <= aabb_b[1][1] and aabb_a[1][1] >= aabb_b[0][1] and
            aabb_a[0][2] <= aabb_b[1][2] and aabb_a[1][2] >= aabb_b[0][2]
        )
    
    def _compute_aabb(self, shape: CollisionShape) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """计算形状的AABB"""
        pos = np.array(shape.position)
        
        if shape.shape_type == CollisionShapeType.SPHERE:
            radius = shape.radius * max(shape.scale)
            return (
                tuple(pos - radius),
                tuple(pos + radius)
            )
        elif shape.shape_type == CollisionShapeType.BOX:
            half_extents = np.array(shape.half_extents) * np.array(shape.scale)
            return (
                tuple(pos - half_extents),
                tuple(pos + half_extents)
            )
        else:
            # 默认使用单位AABB
            return (
                tuple(pos - 1.0),
                tuple(pos + 1.0)
            )
    
    def _check_collision_filter(self, shape_a: CollisionShape, shape_b: CollisionShape) -> bool:
        """检查碰撞过滤器"""
        group_a = shape_a.collision_group
        mask_a = shape_a.collision_mask
        group_b = shape_b.collision_group
        mask_b = shape_b.collision_mask
        
        return (mask_a & group_b) != 0 and (mask_b & group_a) != 0
    
    def _quaternion_to_matrix(self, quat: Tuple[float, float, float, float]) -> np.ndarray:
        """四元数转旋转矩阵"""
        x, y, z, w = quat
        
        return np.array([
            [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
            [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
            [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y]
        ])
    
    def _update_spatial_grid(self, shape_id: str):
        """更新空间网格"""
        shape = self.collision_shapes[shape_id]
        aabb = self._compute_aabb(shape)
        
        # 计算网格坐标范围
        min_grid_x = int(aabb[0][0] // self.grid_size)
        min_grid_y = int(aabb[0][1] // self.grid_size)
        min_grid_z = int(aabb[0][2] // self.grid_size)
        max_grid_x = int(aabb[1][0] // self.grid_size)
        max_grid_y = int(aabb[1][1] // self.grid_size)
        max_grid_z = int(aabb[1][2] // self.grid_size)
        
        # 添加到所有相关的网格单元
        for x in range(min_grid_x, max_grid_x + 1):
            for y in range(min_grid_y, max_grid_y + 1):
                for z in range(min_grid_z, max_grid_z + 1):
                    grid_key = (x, y, z)
                    if grid_key not in self.spatial_grid:
                        self.spatial_grid[grid_key] = set()
                    self.spatial_grid[grid_key].add(shape_id)
    
    def _remove_from_spatial_grid(self, shape_id: str):
        """从空间网格中移除"""
        for grid_cell in self.spatial_grid.values():
            grid_cell.discard(shape_id)
        
        # 清理空网格单元
        self.spatial_grid = {k: v for k, v in self.spatial_grid.items() if v}
    
    def _get_grid_candidates(self) -> List[Tuple[str, str]]:
        """从空间网格获取候选碰撞对"""
        candidates = set()
        
        for grid_cell in self.spatial_grid.values():
            shape_list = list(grid_cell)
            for i in range(len(shape_list)):
                for j in range(i + 1, len(shape_list)):
                    candidates.add((shape_list[i], shape_list[j]))
        
        return list(candidates)
    
    def _handle_collision_callbacks(self, result: CollisionResult):
        """处理碰撞回调"""
        for callback_id, callback in self.contact_callbacks.items():
            try:
                callback(result)
            except Exception as e:
                logger.error(f"碰撞回调执行失败 {callback_id}: {e}")
    
    def register_contact_callback(self, callback_id: str, callback: Any):
        """注册碰撞回调函数"""
        self.contact_callbacks[callback_id] = callback
        logger.info(f"注册碰撞回调: {callback_id}")
    
    def unregister_contact_callback(self, callback_id: str):
        """注销碰撞回调函数"""
        if callback_id in self.contact_callbacks:
            del self.contact_callbacks[callback_id]
            logger.info(f"注销碰撞回调: {callback_id}")
    
    def get_detector_stats(self) -> Dict[str, Any]:
        """获取检测器统计信息"""
        stats = self.stats.copy()
        stats["total_shapes"] = len(self.collision_shapes)
        stats["spatial_grid_cells"] = len(self.spatial_grid)
        stats["registered_callbacks"] = len(self.contact_callbacks)
        
        return stats
    
    def raycast(self, origin: Tuple[float, float, float], 
                direction: Tuple[float, float, float], 
                max_distance: float = 100.0) -> List[Tuple[str, float, Tuple[float, float, float]]]:
        """射线检测"""
        results = []
        direction = np.array(direction)
        direction = direction / np.linalg.norm(direction)  # 归一化
        
        for shape_id, shape in self.collision_shapes.items():
            hit_distance, hit_point = self._ray_shape_intersection(origin, direction, shape, max_distance)
            if hit_distance is not None:
                results.append((shape_id, hit_distance, hit_point))
        
        # 按距离排序
        results.sort(key=lambda x: x[1])
        return results
    
    def _ray_shape_intersection(self, origin: Tuple[float, float, float], 
                               direction: Tuple[float, float, float],
                               shape: CollisionShape, 
                               max_distance: float) -> Tuple[Optional[float], Optional[Tuple[float, float, float]]]:
        """射线与形状相交检测"""
        origin = np.array(origin)
        direction = np.array(direction)
        
        if shape.shape_type == CollisionShapeType.SPHERE:
            return self._ray_sphere_intersection(origin, direction, shape, max_distance)
        elif shape.shape_type == CollisionShapeType.BOX:
            return self._ray_box_intersection(origin, direction, shape, max_distance)
        elif shape.shape_type == CollisionShapeType.PLANE:
            return self._ray_plane_intersection(origin, direction, shape, max_distance)
        
        return None, None
    
    def _ray_sphere_intersection(self, origin: np.ndarray, direction: np.ndarray,
                                sphere: CollisionShape, max_distance: float) -> Tuple[Optional[float], Optional[Tuple[float, float, float]]]:
        """射线与球体相交"""
        center = np.array(sphere.position)
        radius = sphere.radius * max(sphere.scale)
        
        oc = origin - center
        a = np.dot(direction, direction)
        b = 2.0 * np.dot(oc, direction)
        c = np.dot(oc, oc) - radius * radius
        
        discriminant = b * b - 4 * a * c
        
        if discriminant < 0:
            return None, None
        
        t1 = (-b - math.sqrt(discriminant)) / (2 * a)
        t2 = (-b + math.sqrt(discriminant)) / (2 * a)
        
        t = min(t1, t2) if t1 > 0 and t2 > 0 else max(t1, t2)
        
        if 0 <= t <= max_distance:
            hit_point = origin + direction * t
            return t, tuple(hit_point)
        
        return None, None
    
    def _ray_box_intersection(self, origin: np.ndarray, direction: np.ndarray,
                             box: CollisionShape, max_distance: float) -> Tuple[Optional[float], Optional[Tuple[float, float, float]]]:
        """射线与盒子相交"""
        # 简化的AABB射线检测
        aabb = self._compute_aabb(box)
        min_bounds = np.array(aabb[0])
        max_bounds = np.array(aabb[1])
        
        tmin = (min_bounds - origin) / direction
        tmax = (max_bounds - origin) / direction
        
        t1 = np.minimum(tmin, tmax)
        t2 = np.maximum(tmin, tmax)
        
        t_near = max(t1)
        t_far = min(t2)
        
        if t_near <= t_far and 0 <= t_near <= max_distance:
            hit_point = origin + direction * t_near
            return t_near, tuple(hit_point)
        
        return None, None
    
    def _ray_plane_intersection(self, origin: np.ndarray, direction: np.ndarray,
                               plane: CollisionShape, max_distance: float) -> Tuple[Optional[float], Optional[Tuple[float, float, float]]]:
        """射线与平面相交"""
        normal = np.array(plane.normal)
        plane_point = normal * plane.distance
        
        denom = np.dot(normal, direction)
        if abs(denom) < 1e-6:
            return None, None  # 平行
        
        t = np.dot(plane_point - origin, normal) / denom
        
        if 0 <= t <= max_distance:
            hit_point = origin + direction * t
            return t, tuple(hit_point)
        
        return None, None
    
    def cleanup(self):
        """清理碰撞检测器"""
        self.collision_shapes.clear()
        self.broad_phase_pairs.clear()
        self.contact_callbacks.clear()
        self.spatial_grid.clear()
        
        logger.info("碰撞检测器清理完成")

# 全局碰撞检测器实例
collision_detector = CollisionDetector()

