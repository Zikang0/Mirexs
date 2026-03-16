"""
骨骼绑定系统
负责3D角色骨骼的创建、绑定和动画控制
修复版本：移除mathutils依赖，使用自定义矩阵和四元数运算
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import logging
import math

logger = logging.getLogger(__name__)

@dataclass
class Bone:
    """骨骼数据类"""
    name: str
    parent: Optional[str]
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float, float]  # quaternion (x, y, z, w)
    length: float
    matrix: np.ndarray  # 4x4变换矩阵
    head: Tuple[float, float, float]
    tail: Tuple[float, float, float]
    
@dataclass
class BoneConstraint:
    """骨骼约束数据类"""
    name: str
    constraint_type: str  # IK, copy_rotation, limit_rotation, etc.
    target_bone: str
    influence: float
    parameters: Dict[str, float]

class RiggingSystem:
    """骨骼绑定系统 - 修复版本"""
    
    def __init__(self):
        self.bones: Dict[str, Bone] = {}
        self.bone_hierarchy: Dict[str, List[str]] = {}
        self.constraints: Dict[str, List[BoneConstraint]] = {}
        self.armature_matrix: np.ndarray = np.eye(4)
        self.rest_pose: Dict[str, np.ndarray] = {}
        
    def create_bone(self, name: str, parent: Optional[str] = None,
                   position: Tuple[float, float, float] = (0, 0, 0),
                   rotation: Tuple[float, float, float, float] = (0, 0, 0, 1),
                   length: float = 1.0) -> bool:
        """
        创建骨骼
        
        Args:
            name: 骨骼名称
            parent: 父骨骼名称
            position: 位置
            rotation: 旋转四元数
            length: 骨骼长度
            
        Returns:
            bool: 是否创建成功
        """
        try:
            # 计算头部和尾部位置
            head = np.array(position)
            rotation_matrix = self.quaternion_to_matrix(rotation)
            
            # 骨骼沿Y轴延伸
            tail_offset = np.array([0, length, 0, 1])
            tail_world = rotation_matrix @ tail_offset
            tail = head + tail_world[:3]
            
            # 创建变换矩阵
            matrix = self.compose_matrix(position, rotation)
            
            bone = Bone(
                name=name,
                parent=parent,
                position=position,
                rotation=rotation,
                length=length,
                matrix=matrix,
                head=tuple(head),
                tail=tuple(tail)
            )
            
            self.bones[name] = bone
            
            # 更新骨骼层级
            if parent is not None:
                if parent not in self.bone_hierarchy:
                    self.bone_hierarchy[parent] = []
                self.bone_hierarchy[parent].append(name)
                
            # 保存初始姿态
            self.rest_pose[name] = matrix.copy()
            
            logger.info(f"Created bone: {name} (parent: {parent})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create bone {name}: {str(e)}")
            return False
            
    def add_constraint(self, bone_name: str, constraint: BoneConstraint) -> bool:
        """
        为骨骼添加约束
        
        Args:
            bone_name: 骨骼名称
            constraint: 约束对象
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if bone_name not in self.constraints:
                self.constraints[bone_name] = []
                
            self.constraints[bone_name].append(constraint)
            logger.info(f"Added {constraint.constraint_type} constraint to {bone_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add constraint to {bone_name}: {str(e)}")
            return False
            
    def solve_ik(self, chain_root: str, target_bone: str, 
                target_position: Tuple[float, float, float],
                iterations: int = 10) -> bool:
        """
        解算逆向运动学
        
        Args:
            chain_root: IK链根骨骼
            target_bone: 目标骨骼
            target_position: 目标位置
            iterations: 迭代次数
            
        Returns:
            bool: 是否解算成功
        """
        try:
            target_pos = np.array(target_position)
            
            for iteration in range(iterations):
                # 前向传递：从末端到根骨骼
                current_bone = target_bone
                while current_bone != chain_root and current_bone is not None:
                    if current_bone not in self.bones:
                        break
                        
                    bone = self.bones[current_bone]
                    parent_name = bone.parent
                    
                    if parent_name not in self.bones:
                        break
                        
                    parent_bone = self.bones[parent_name]
                    
                    # 计算当前方向向量
                    current_pos = np.array(bone.position)
                    parent_pos = np.array(parent_bone.position)
                    
                    current_to_target = target_pos - current_pos
                    parent_to_current = current_pos - parent_pos
                    
                    # 计算旋转
                    rotation = self.rotate_to_align(parent_to_current, current_to_target)
                    
                    # 应用旋转到父骨骼
                    new_matrix = self.apply_rotation_to_matrix(parent_bone.matrix, rotation)
                    self.bones[parent_name].matrix = new_matrix
                    self.bones[parent_name].rotation = self.matrix_to_quaternion(new_matrix)
                    
                    # 更新位置
                    new_position = new_matrix[:3, 3]
                    self.bones[parent_name].position = tuple(new_position)
                    
                    current_bone = parent_name
                    
                # 检查是否达到目标精度
                end_effector_pos = np.array(self.bones[target_bone].position)
                distance = np.linalg.norm(target_pos - end_effector_pos)
                
                if distance < 0.01:  # 精度阈值
                    logger.info(f"IK solved in {iteration + 1} iterations")
                    break
                    
            self.update_bone_transforms()
            return True
            
        except Exception as e:
            logger.error(f"Failed to solve IK: {str(e)}")
            return False
            
    def update_bone_transforms(self):
        """更新所有骨骼的变换"""
        for bone_name, bone in self.bones.items():
            if bone.parent and bone.parent in self.bones:
                parent_matrix = self.bones[bone.parent].matrix
                bone.matrix = parent_matrix @ self.rest_pose[bone_name]
            else:
                bone.matrix = self.rest_pose[bone_name]
                
            # 更新位置和旋转
            bone.position = tuple(bone.matrix[:3, 3])
            bone.rotation = self.matrix_to_quaternion(bone.matrix)
            
    def apply_constraints(self):
        """应用所有约束"""
        for bone_name, constraint_list in self.constraints.items():
            if bone_name not in self.bones:
                continue
                
            bone = self.bones[bone_name]
            
            for constraint in constraint_list:
                if constraint.constraint_type == "copy_rotation":
                    self._apply_copy_rotation_constraint(bone, constraint)
                elif constraint.constraint_type == "limit_rotation":
                    self._apply_limit_rotation_constraint(bone, constraint)
                    
    def _apply_copy_rotation_constraint(self, bone: Bone, constraint: BoneConstraint):
        """应用复制旋转约束"""
        target_bone_name = constraint.target_bone
        if target_bone_name in self.bones:
            target_bone = self.bones[target_bone_name]
            influence = constraint.parameters.get("influence", 1.0)
            
            # 插值旋转
            current_rot = np.array(bone.rotation)
            target_rot = np.array(target_bone.rotation)
            new_rot = self.slerp(current_rot, target_rot, influence)
            
            bone.rotation = tuple(new_rot)
            bone.matrix = self.compose_matrix(bone.position, bone.rotation)
            
    def _apply_limit_rotation_constraint(self, bone: Bone, constraint: BoneConstraint):
        """应用旋转限制约束"""
        limits = constraint.parameters
        current_rot = np.array(bone.rotation)
        
        # 转换为欧拉角进行限制
        euler_angles = self.quaternion_to_euler(current_rot)
        
        # 限制各个轴的旋转角度
        if 'min_x' in limits and 'max_x' in limits:
            euler_angles[0] = np.clip(euler_angles[0], limits['min_x'], limits['max_x'])
        if 'min_y' in limits and 'max_y' in limits:
            euler_angles[1] = np.clip(euler_angles[1], limits['min_y'], limits['max_y'])
        if 'min_z' in limits and 'max_z' in limits:
            euler_angles[2] = np.clip(euler_angles[2], limits['min_z'], limits['max_z'])
        
        # 转换回四元数
        limited_rot = self.euler_to_quaternion(euler_angles)
        
        bone.rotation = tuple(limited_rot)
        bone.matrix = self.compose_matrix(bone.position, bone.rotation)
        
    def quaternion_to_matrix(self, quat: Tuple[float, float, float, float]) -> np.ndarray:
        """四元数转矩阵 - 完整实现"""
        x, y, z, w = quat
        
        # 归一化四元数
        norm = math.sqrt(x*x + y*y + z*z + w*w)
        if norm == 0:
            return np.eye(4)
        x, y, z, w = x/norm, y/norm, z/norm, w/norm
        
        # 计算旋转矩阵
        xx, yy, zz = x*x, y*y, z*z
        xy, xz, yz = x*y, x*z, y*z
        wx, wy, wz = w*x, w*y, w*z
        
        matrix = np.array([
            [1 - 2*(yy + zz),     2*(xy - wz),     2*(xz + wy), 0],
            [    2*(xy + wz), 1 - 2*(xx + zz),     2*(yz - wx), 0],
            [    2*(xz - wy),     2*(yz + wx), 1 - 2*(xx + yy), 0],
            [              0,               0,               0, 1]
        ])
        
        return matrix
        
    def matrix_to_quaternion(self, matrix: np.ndarray) -> Tuple[float, float, float, float]:
        """矩阵转四元数 - 完整实现"""
        m = matrix[:3, :3]  # 只取旋转部分
        
        trace = m[0, 0] + m[1, 1] + m[2, 2]
        
        if trace > 0:
            s = 0.5 / math.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (m[2, 1] - m[1, 2]) * s
            y = (m[0, 2] - m[2, 0]) * s
            z = (m[1, 0] - m[0, 1]) * s
        else:
            if m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
                s = 2.0 * math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2])
                w = (m[2, 1] - m[1, 2]) / s
                x = 0.25 * s
                y = (m[0, 1] + m[1, 0]) / s
                z = (m[0, 2] + m[2, 0]) / s
            elif m[1, 1] > m[2, 2]:
                s = 2.0 * math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2])
                w = (m[0, 2] - m[2, 0]) / s
                x = (m[0, 1] + m[1, 0]) / s
                y = 0.25 * s
                z = (m[1, 2] + m[2, 1]) / s
            else:
                s = 2.0 * math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1])
                w = (m[1, 0] - m[0, 1]) / s
                x = (m[0, 2] + m[2, 0]) / s
                y = (m[1, 2] + m[2, 1]) / s
                z = 0.25 * s
        
        # 归一化四元数
        norm = math.sqrt(x*x + y*y + z*z + w*w)
        if norm > 0:
            x, y, z, w = x/norm, y/norm, z/norm, w/norm
        
        return (x, y, z, w)
        
    def compose_matrix(self, position: Tuple[float, float, float], 
                      rotation: Tuple[float, float, float, float]) -> np.ndarray:
        """组合变换矩阵"""
        rot_matrix = self.quaternion_to_matrix(rotation)
        rot_matrix[:3, 3] = position
        return rot_matrix
        
    def rotate_to_align(self, from_vec: np.ndarray, to_vec: np.ndarray) -> np.ndarray:
        """计算对齐两个向量的旋转 - 完整实现"""
        # 归一化输入向量
        from_vec = from_vec / np.linalg.norm(from_vec)
        to_vec = to_vec / np.linalg.norm(to_vec)
        
        # 计算旋转轴
        axis = np.cross(from_vec, to_vec)
        axis_norm = np.linalg.norm(axis)
        
        if axis_norm < 1e-6:
            # 向量已经对齐或相反
            if np.dot(from_vec, to_vec) > 0:
                return np.eye(3)  # 已经对齐
            else:
                # 180度旋转，需要任意垂直轴
                if abs(from_vec[0]) > 1e-6:
                    axis = np.cross(from_vec, np.array([0, 1, 0]))
                else:
                    axis = np.cross(from_vec, np.array([1, 0, 0]))
                axis_norm = np.linalg.norm(axis)
        
        axis = axis / axis_norm
        
        # 计算旋转角度
        cos_angle = np.dot(from_vec, to_vec)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = math.acos(cos_angle)
        
        # 使用罗德里格斯公式计算旋转矩阵
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        one_minus_cos = 1 - cos_a
        
        x, y, z = axis
        rotation_matrix = np.array([
            [cos_a + x*x*one_minus_cos, x*y*one_minus_cos - z*sin_a, x*z*one_minus_cos + y*sin_a],
            [y*x*one_minus_cos + z*sin_a, cos_a + y*y*one_minus_cos, y*z*one_minus_cos - x*sin_a],
            [z*x*one_minus_cos - y*sin_a, z*y*one_minus_cos + x*sin_a, cos_a + z*z*one_minus_cos]
        ])
        
        return rotation_matrix
        
    def apply_rotation_to_matrix(self, matrix: np.ndarray, rotation: np.ndarray) -> np.ndarray:
        """将旋转应用到矩阵"""
        # 扩展3x3旋转矩阵到4x4
        rot_4x4 = np.eye(4)
        rot_4x4[:3, :3] = rotation
        return matrix @ rot_4x4
        
    def slerp(self, q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
        """球面线性插值 - 完整实现"""
        # 确保四元数归一化
        q1 = q1 / np.linalg.norm(q1)
        q2 = q2 / np.linalg.norm(q2)
        
        dot = np.dot(q1, q2)
        
        # 如果点积为负，取反其中一个四元数以保证最短路径
        if dot < 0.0:
            q2 = -q2
            dot = -dot
        
        # 如果四元数非常接近，使用线性插值避免除零
        if dot > 0.9995:
            result = q1 + t * (q2 - q1)
            return result / np.linalg.norm(result)
        
        # 计算插值角度
        theta_0 = math.acos(dot)
        sin_theta_0 = math.sin(theta_0)
        
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        
        s1 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s2 = sin_theta / sin_theta_0
        
        return s1 * q1 + s2 * q2
    
    def quaternion_to_euler(self, quat: np.ndarray) -> np.ndarray:
        """四元数转欧拉角 (XYZ顺序)"""
        x, y, z, w = quat
        
        # 计算欧拉角
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return np.array([roll, pitch, yaw])
    
    def euler_to_quaternion(self, euler: np.ndarray) -> np.ndarray:
        """欧拉角转四元数 (XYZ顺序)"""
        roll, pitch, yaw = euler
        
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        
        return np.array([x, y, z, w])
        
    def export_armature(self, file_path: str) -> bool:
        """导出骨骼结构到文件"""
        try:
            armature_data = {
                "bones": {
                    name: {
                        "parent": bone.parent,
                        "position": bone.position,
                        "rotation": bone.rotation,
                        "length": bone.length,
                        "head": bone.head,
                        "tail": bone.tail
                    }
                    for name, bone in self.bones.items()
                },
                "constraints": {
                    bone_name: [
                        {
                            "name": const.name,
                            "type": const.constraint_type,
                            "target": const.target_bone,
                            "influence": const.influence,
                            "parameters": const.parameters
                        }
                        for const in constraint_list
                    ]
                    for bone_name, constraint_list in self.constraints.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(armature_data, f, indent=2)
                
            logger.info(f"Exported armature to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export armature: {str(e)}")
            return False
            
    def import_armature(self, file_path: str) -> bool:
        """从文件导入骨骼结构"""
        try:
            with open(file_path, 'r') as f:
                armature_data = json.load(f)
            
            # 清空现有数据
            self.bones = {}
            self.bone_hierarchy = {}
            self.constraints = {}
            self.rest_pose = {}
            
            # 创建骨骼
            for name, bone_data in armature_data["bones"].items():
                self.create_bone(
                    name=name,
                    parent=bone_data["parent"],
                    position=tuple(bone_data["position"]),
                    rotation=tuple(bone_data["rotation"]),
                    length=bone_data["length"]
                )
            
            # 添加约束
            for bone_name, constraint_list in armature_data.get("constraints", {}).items():
                for const_data in constraint_list:
                    constraint = BoneConstraint(
                        name=const_data["name"],
                        constraint_type=const_data["type"],
                        target_bone=const_data["target"],
                        influence=const_data["influence"],
                        parameters=const_data["parameters"]
                    )
                    self.add_constraint(bone_name, constraint)
            
            logger.info(f"Imported armature from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import armature: {str(e)}")
            return False

# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建骨骼系统
    rig = RiggingSystem()
    
    # 创建一些骨骼
    rig.create_bone("root", position=(0, 0, 0))
    rig.create_bone("spine", parent="root", position=(0, 1, 0))
    rig.create_bone("chest", parent="spine", position=(0, 2, 0))
    
    # 添加约束
    constraint = BoneConstraint(
        name="copy_rotation",
        constraint_type="copy_rotation",
        target_bone="spine",
        influence=0.5,
        parameters={"influence": 0.5}
    )
    rig.add_constraint("chest", constraint)
    
    # 导出骨骼
    rig.export_armature("test_armature.json")
    
    print("骨骼系统测试完成！")