"""
逆向运动学：计算关节运动
负责从目标位置计算关节旋转的逆向运动学求解
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math

logger = logging.getLogger(__name__)

class IKAlgorithm(Enum):
    """逆向运动学算法类型"""
    FABRIK = "fabrik"          # 前向和后向到达逆向运动学
    CCD = "ccd"                # 循环坐标下降
    JACOBIAN = "jacobian"      # 雅可比矩阵方法
    ANALYTIC = "analytic"      # 解析解

@dataclass
class IKChain:
    """逆向运动学链"""
    chain_id: str
    root_bone: str
    end_effector: str
    target_bone: str
    max_iterations: int = 20
    tolerance: float = 0.01
    algorithm: IKAlgorithm = IKAlgorithm.FABRIK

@dataclass
class IKSolution:
    """逆向运动学解"""
    success: bool
    bone_rotations: Dict[str, Tuple[float, float, float, float]]  # 四元数旋转
    iterations: int
    error: float
    processing_time: float

class InverseKinematics:
    """逆向运动学求解器"""
    
    def __init__(self):
        self.ik_chains: Dict[str, IKChain] = {}
        self.bone_constraints: Dict[str, Any] = {}
        
        # 性能统计
        self.stats = {
            "total_solves": 0,
            "successful_solves": 0,
            "average_iterations": 0.0,
            "average_error": 0.0,
            "total_processing_time": 0.0
        }
        
        logger.info("逆向运动学求解器初始化完成")
    
    def create_ik_chain(self, chain_id: str, root_bone: str, end_effector: str, 
                       target_bone: str, algorithm: IKAlgorithm = IKAlgorithm.FABRIK) -> bool:
        """创建逆向运动学链"""
        if chain_id in self.ik_chains:
            logger.warning(f"逆向运动学链已存在: {chain_id}")
            return False
        
        chain = IKChain(
            chain_id=chain_id,
            root_bone=root_bone,
            end_effector=end_effector,
            target_bone=target_bone,
            algorithm=algorithm
        )
        
        self.ik_chains[chain_id] = chain
        logger.info(f"创建逆向运动学链: {chain_id} ({algorithm.value})")
        return True
    
    def solve_ik(self, chain_id: str, target_position: Tuple[float, float, float],
                skeleton_data: Dict[str, Any]) -> IKSolution:
        """解算逆向运动学"""
        import time
        start_time = time.time()
        
        if chain_id not in self.ik_chains:
            logger.error(f"逆向运动学链不存在: {chain_id}")
            return IKSolution(
                success=False,
                bone_rotations={},
                iterations=0,
                error=0.0,
                processing_time=0.0
            )
        
        chain = self.ik_chains[chain_id]
        
        # 根据算法选择求解方法
        if chain.algorithm == IKAlgorithm.FABRIK:
            result = self._solve_fabrik(chain, target_position, skeleton_data)
        elif chain.algorithm == IKAlgorithm.CCD:
            result = self._solve_ccd(chain, target_position, skeleton_data)
        elif chain.algorithm == IKAlgorithm.JACOBIAN:
            result = self._solve_jacobian(chain, target_position, skeleton_data)
        else:
            result = self._solve_analytic(chain, target_position, skeleton_data)
        
        processing_time = time.time() - start_time
        
        # 更新统计信息
        self.stats["total_solves"] += 1
        if result.success:
            self.stats["successful_solves"] += 1
        self.stats["average_iterations"] = (
            (self.stats["average_iterations"] * (self.stats["total_solves"] - 1) + result.iterations) 
            / self.stats["total_solves"]
        )
        self.stats["average_error"] = (
            (self.stats["average_error"] * (self.stats["total_solves"] - 1) + result.error) 
            / self.stats["total_solves"]
        )
        self.stats["total_processing_time"] += processing_time
        
        return IKSolution(
            success=result.success,
            bone_rotations=result.bone_rotations,
            iterations=result.iterations,
            error=result.error,
            processing_time=processing_time
        )
    
    def _solve_fabrik(self, chain: IKChain, target_position: Tuple[float, float, float],
                     skeleton_data: Dict[str, Any]) -> IKSolution:
        """FABRIK算法求解"""
        # 获取骨骼链
        bone_chain = self._get_bone_chain(chain.root_bone, chain.end_effector, skeleton_data)
        if not bone_chain:
            return IKSolution(
                success=False,
                bone_rotations={},
                iterations=0,
                error=0.0,
                processing_time=0.0
            )
        
        # 保存初始位置
        initial_positions = {}
        bone_lengths = {}
        
        for i, bone_name in enumerate(bone_chain):
            bone_data = skeleton_data[bone_name]
            initial_positions[bone_name] = np.array(bone_data["position"])
            
            # 计算骨骼长度
            if i < len(bone_chain) - 1:
                next_bone_data = skeleton_data[bone_chain[i + 1]]
                bone_lengths[bone_name] = np.linalg.norm(
                    np.array(next_bone_data["position"]) - np.array(bone_data["position"])
                )
        
        target_pos = np.array(target_position)
        root_pos = initial_positions[chain.root_bone]
        end_effector_pos = initial_positions[chain.end_effector]
        
        # 检查目标是否可达
        total_chain_length = sum(bone_lengths.values())
        distance_to_target = np.linalg.norm(target_pos - root_pos)
        
        if distance_to_target > total_chain_length:
            # 目标不可达，直接拉伸到最大长度
            direction = (target_pos - root_pos) / distance_to_target
            current_pos = root_pos.copy()
            
            for i, bone_name in enumerate(bone_chain[:-1]):
                next_pos = current_pos + direction * bone_lengths[bone_name]
                initial_positions[bone_chain[i + 1]] = next_pos
                current_pos = next_pos
            
            return self._compute_bone_rotations(bone_chain, initial_positions, skeleton_data, 1, 0.0)
        
        # FABRIK算法主循环
        positions = initial_positions.copy()
        iterations = 0
        error = float('inf')
        
        while iterations < chain.max_iterations and error > chain.tolerance:
            # 前向传递：从末端效应器到根节点
            positions[chain.end_effector] = target_pos
            
            for i in range(len(bone_chain) - 2, -1, -1):
                current_bone = bone_chain[i]
                next_bone = bone_chain[i + 1]
                
                direction = positions[current_bone] - positions[next_bone]
                distance = np.linalg.norm(direction)
                
                if distance > 0:
                    direction = direction / distance
                    positions[current_bone] = positions[next_bone] + direction * bone_lengths[current_bone]
            
            # 后向传递：从根节点到末端效应器
            positions[chain.root_bone] = root_pos
            
            for i in range(len(bone_chain) - 1):
                current_bone = bone_chain[i]
                next_bone = bone_chain[i + 1]
                
                direction = positions[next_bone] - positions[current_bone]
                distance = np.linalg.norm(direction)
                
                if distance > 0:
                    direction = direction / distance
                    positions[next_bone] = positions[current_bone] + direction * bone_lengths[current_bone]
            
            # 计算误差
            error = np.linalg.norm(positions[chain.end_effector] - target_pos)
            iterations += 1
        
        return self._compute_bone_rotations(bone_chain, positions, skeleton_data, iterations, error)
    
    def _solve_ccd(self, chain: IKChain, target_position: Tuple[float, float, float],
                  skeleton_data: Dict[str, Any]) -> IKSolution:
        """循环坐标下降算法求解"""
        bone_chain = self._get_bone_chain(chain.root_bone, chain.end_effector, skeleton_data)
        if not bone_chain:
            return IKSolution(
                success=False,
                bone_rotations={},
                iterations=0,
                error=0.0,
                processing_time=0.0
            )
        
        positions = {}
        for bone_name in bone_chain:
            bone_data = skeleton_data[bone_name]
            positions[bone_name] = np.array(bone_data["position"])
        
        target_pos = np.array(target_position)
        iterations = 0
        error = float('inf')
        
        while iterations < chain.max_iterations and error > chain.tolerance:
            # 从末端效应器向根节点遍历
            for i in range(len(bone_chain) - 2, -1, -1):
                current_bone = bone_chain[i]
                end_effector_pos = positions[chain.end_effector]
                
                # 计算当前关节到末端效应器和目标的向量
                to_end_effector = end_effector_pos - positions[current_bone]
                to_target = target_pos - positions[current_bone]
                
                # 归一化向量
                if np.linalg.norm(to_end_effector) > 0 and np.linalg.norm(to_target) > 0:
                    to_end_effector = to_end_effector / np.linalg.norm(to_end_effector)
                    to_target = to_target / np.linalg.norm(to_target)
                    
                    # 计算旋转轴和角度
                    rotation_axis = np.cross(to_end_effector, to_target)
                    rotation_axis = rotation_axis / np.linalg.norm(rotation_axis) if np.linalg.norm(rotation_axis) > 0 else np.array([0, 0, 1])
                    
                    dot_product = np.clip(np.dot(to_end_effector, to_target), -1.0, 1.0)
                    rotation_angle = math.acos(dot_product)
                    
                    # 应用旋转到当前关节之后的所有关节
                    rotation_quat = self._axis_angle_to_quaternion(rotation_axis, rotation_angle)
                    
                    for j in range(i, len(bone_chain)):
                        bone_name = bone_chain[j]
                        if j > i:  # 只旋转子骨骼
                            relative_pos = positions[bone_name] - positions[current_bone]
                            rotated_pos = self._rotate_vector(relative_pos, rotation_quat)
                            positions[bone_name] = positions[current_bone] + rotated_pos
            
            # 计算误差
            error = np.linalg.norm(positions[chain.end_effector] - target_pos)
            iterations += 1
        
        return self._compute_bone_rotations(bone_chain, positions, skeleton_data, iterations, error)
    
    def _solve_jacobian(self, chain: IKChain, target_position: Tuple[float, float, float],
                       skeleton_data: Dict[str, Any]) -> IKSolution:
        """雅可比矩阵方法求解"""
        # 简化的雅可比矩阵实现
        # 实际应该计算完整的雅可比矩阵和使用伪逆
        return self._solve_ccd(chain, target_position, skeleton_data)
    
    def _solve_analytic(self, chain: IKChain, target_position: Tuple[float, float, float],
                       skeleton_data: Dict[str, Any]) -> IKSolution:
        """解析解方法求解（适用于简单链）"""
        bone_chain = self._get_bone_chain(chain.root_bone, chain.end_effector, skeleton_data)
        if len(bone_chain) != 3:  # 只支持3骨骼链的解析解
            logger.warning("解析解只支持3骨骼链，使用CCD代替")
            return self._solve_ccd(chain, target_position, skeleton_data)
        
        # 两骨骼链的解析解
        root_pos = np.array(skeleton_data[bone_chain[0]]["position"])
        middle_pos = np.array(skeleton_data[bone_chain[1]]["position"])
        end_pos = np.array(skeleton_data[bone_chain[2]]["position"])
        target_pos = np.array(target_position)
        
        # 计算骨骼长度
        bone1_length = np.linalg.norm(middle_pos - root_pos)
        bone2_length = np.linalg.norm(end_pos - middle_pos)
        
        # 计算距离
        distance = np.linalg.norm(target_pos - root_pos)
        distance = np.clip(distance, 0.0, bone1_length + bone2_length - 0.001)
        
        # 计算角度
        cos_angle2 = (bone1_length**2 + bone2_length**2 - distance**2) / (2 * bone1_length * bone2_length)
        cos_angle2 = np.clip(cos_angle2, -1.0, 1.0)
        angle2 = math.acos(cos_angle2)
        
        cos_angle1 = (distance**2 + bone1_length**2 - bone2_length**2) / (2 * distance * bone1_length)
        cos_angle1 = np.clip(cos_angle1, -1.0, 1.0)
        angle1 = math.acos(cos_angle1)
        
        # 计算方向
        to_target = target_pos - root_pos
        to_target_dir = to_target / np.linalg.norm(to_target) if np.linalg.norm(to_target) > 0 else np.array([1, 0, 0])
        
        # 计算平面法线（使用默认上向量）
        up_vector = np.array([0, 1, 0])
        rotation_axis = np.cross(to_target_dir, up_vector)
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis) if np.linalg.norm(rotation_axis) > 0 else np.array([0, 0, 1])
        
        # 计算旋转
        rot1_quat = self._axis_angle_to_quaternion(rotation_axis, angle1)
        rot2_quat = self._axis_angle_to_quaternion(rotation_axis, angle2 - math.pi)  # 第二个关节反向
        
        # 应用旋转计算新位置
        positions = {}
        positions[bone_chain[0]] = root_pos
        positions[bone_chain[1]] = root_pos + self._rotate_vector(np.array([bone1_length, 0, 0]), rot1_quat)
        positions[bone_chain[2]] = positions[bone_chain[1]] + self._rotate_vector(np.array([bone2_length, 0, 0]), rot2_quat)
        
        error = np.linalg.norm(positions[bone_chain[2]] - target_pos)
        
        bone_rotations = {}
        bone_rotations[bone_chain[1]] = rot1_quat
        bone_rotations[bone_chain[2]] = rot2_quat
        
        return IKSolution(
            success=error < chain.tolerance,
            bone_rotations=bone_rotations,
            iterations=1,
            error=error,
            processing_time=0.0
        )
    
    def _get_bone_chain(self, root_bone: str, end_effector: str, skeleton_data: Dict[str, Any]) -> List[str]:
        """获取从根骨骼到末端效应器的骨骼链"""
        chain = []
        current_bone = end_effector
        
        while current_bone and current_bone in skeleton_data:
            chain.insert(0, current_bone)
            
            if current_bone == root_bone:
                break
            
            # 获取父骨骼
            bone_data = skeleton_data[current_bone]
            current_bone = bone_data.get("parent")
        
        # 检查是否成功找到完整链
        if chain and chain[0] == root_bone:
            return chain
        else:
            logger.error(f"无法找到从 {root_bone} 到 {end_effector} 的完整骨骼链")
            return []
    
    def _compute_bone_rotations(self, bone_chain: List[str], positions: Dict[str, np.ndarray],
                              skeleton_data: Dict[str, Any], iterations: int, error: float) -> IKSolution:
        """从位置计算骨骼旋转"""
        bone_rotations = {}
        
        for i in range(len(bone_chain) - 1):
            current_bone = bone_chain[i]
            next_bone = bone_chain[i + 1]
            
            # 获取骨骼的初始方向
            initial_current_pos = np.array(skeleton_data[current_bone]["position"])
            initial_next_pos = np.array(skeleton_data[next_bone]["position"])
            initial_direction = initial_next_pos - initial_current_pos
            
            # 计算当前方向
            current_direction = positions[next_bone] - positions[current_bone]
            
            # 计算旋转
            if np.linalg.norm(initial_direction) > 0 and np.linalg.norm(current_direction) > 0:
                initial_direction = initial_direction / np.linalg.norm(initial_direction)
                current_direction = current_direction / np.linalg.norm(current_direction)
                
                rotation_axis = np.cross(initial_direction, current_direction)
                if np.linalg.norm(rotation_axis) > 0:
                    rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
                    dot_product = np.clip(np.dot(initial_direction, current_direction), -1.0, 1.0)
                    rotation_angle = math.acos(dot_product)
                    
                    rotation_quat = self._axis_angle_to_quaternion(rotation_axis, rotation_angle)
                    bone_rotations[current_bone] = tuple(rotation_quat)
        
        return IKSolution(
            success=error < 0.1,  # 宽松的容差
            bone_rotations=bone_rotations,
            iterations=iterations,
            error=error,
            processing_time=0.0
        )
    
    def _axis_angle_to_quaternion(self, axis: np.ndarray, angle: float) -> np.ndarray:
        """轴角转四元数"""
        axis = axis / np.linalg.norm(axis)
        half_angle = angle * 0.5
        sin_half = math.sin(half_angle)
        
        return np.array([
            axis[0] * sin_half,
            axis[1] * sin_half,
            axis[2] * sin_half,
            math.cos(half_angle)
        ])
    
    def _rotate_vector(self, vector: np.ndarray, quaternion: np.ndarray) -> np.ndarray:
        """用四元数旋转向量"""
        q = quaternion
        v = np.array([vector[0], vector[1], vector[2], 0.0])
        
        q_conj = np.array([-q[0], -q[1], -q[2], q[3]])
        qv = self._quaternion_multiply(q, v)
        qvq = self._quaternion_multiply(qv, q_conj)
        
        return qvq[:3]
    
    def _quaternion_multiply(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """四元数乘法"""
        w1, x1, y1, z1 = q1[3], q1[0], q1[1], q1[2]
        w2, x2, y2, z2 = q2[3], q2[0], q2[1], q2[2]
        
        return np.array([
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        ])
    
    def set_bone_constraint(self, bone_name: str, constraint: Any):
        """设置骨骼约束"""
        self.bone_constraints[bone_name] = constraint
        logger.debug(f"设置骨骼约束: {bone_name}")
    
    def get_ik_chain(self, chain_id: str) -> Optional[IKChain]:
        """获取逆向运动学链"""
        return self.ik_chains.get(chain_id)
    
    def remove_ik_chain(self, chain_id: str) -> bool:
        """移除逆向运动学链"""
        if chain_id not in self.ik_chains:
            return False
        
        del self.ik_chains[chain_id]
        logger.info(f"移除逆向运动学链: {chain_id}")
        return True
    
    def get_solver_stats(self) -> Dict[str, Any]:
        """获取求解器统计信息"""
        stats = self.stats.copy()
        stats["active_chains"] = len(self.ik_chains)
        stats["bone_constraints"] = len(self.bone_constraints)
        
        if stats["total_solves"] > 0:
            stats["success_rate"] = stats["successful_solves"] / stats["total_solves"]
            stats["average_processing_time"] = stats["total_processing_time"] / stats["total_solves"]
        else:
            stats["success_rate"] = 0.0
            stats["average_processing_time"] = 0.0
        
        return stats
    
    def cleanup(self):
        """清理求解器"""
        self.ik_chains.clear()
        self.bone_constraints.clear()
        
        logger.info("逆向运动学求解器清理完成")

# 全局逆向运动学求解器实例
inverse_kinematics = InverseKinematics()

