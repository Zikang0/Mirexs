"""
猫咪模型 - 3D猫咪模型文件
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

@dataclass
class CatModelConfig:
    """猫咪模型配置"""
    model_name: str
    model_path: str
    scale: float = 1.0
    lod_levels: int = 3
    enable_physics: bool = True
    enable_shadows: bool = True

class CatModel:
    """3D猫咪模型类"""
    
    def __init__(self, config: CatModelConfig):
        self.config = config
        self.model_data = None
        self.is_loaded = False
        self.mesh_data = {}
        self.texture_data = {}
        self.animation_data = {}
        self.skeleton_data = {}
        
        # 模型状态
        self.current_pose = {}
        self.current_animation = None
        self.animation_time = 0.0
        
        # 性能统计
        self.stats = {
            "load_time": 0.0,
            "render_calls": 0,
            "vertex_count": 0,
            "triangle_count": 0,
            "texture_memory": 0
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("CatModel")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load(self) -> bool:
        """加载猫咪模型"""
        try:
            self.logger.info(f"开始加载猫咪模型: {self.config.model_name}")
            
            # 检查模型文件是否存在
            if not os.path.exists(self.config.model_path):
                self.logger.error(f"模型文件不存在: {self.config.model_path}")
                return False
            
            # 根据文件类型加载模型
            file_ext = os.path.splitext(self.config.model_path)[1].lower()
            
            if file_ext == '.gltf' or file_ext == '.glb':
                success = self._load_gltf_model()
            elif file_ext == '.obj':
                success = self._load_obj_model()
            elif file_ext == '.fbx':
                success = self._load_fbx_model()
            else:
                self.logger.error(f"不支持的模型格式: {file_ext}")
                return False
            
            if success:
                self.is_loaded = True
                self.logger.info(f"猫咪模型加载成功: {self.config.model_name}")
                self._calculate_model_stats()
            else:
                self.logger.error(f"猫咪模型加载失败: {self.config.model_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"加载猫咪模型时发生错误: {e}")
            return False
    
    def _load_gltf_model(self) -> bool:
        """加载GLTF/GLB模型"""
        try:
            # 模拟GLTF模型加载
            self.logger.info("加载GLTF模型数据...")
            
            # 创建模拟的网格数据
            self.mesh_data = {
                "vertices": self._generate_cat_vertices(),
                "normals": self._generate_cat_normals(),
                "uvs": self._generate_cat_uvs(),
                "indices": self._generate_cat_indices(),
                "materials": ["body", "eyes", "nose"]
            }
            
            # 创建模拟的骨架数据
            self.skeleton_data = {
                "bones": self._generate_cat_bones(),
                "hierarchy": self._generate_cat_bone_hierarchy(),
                "bind_pose": self._generate_cat_bind_pose()
            }
            
            # 创建模拟的动画数据
            self.animation_data = {
                "idle": self._generate_idle_animation(),
                "walk": self._generate_walk_animation(),
                "run": self._generate_run_animation(),
                "sit": self._generate_sit_animation(),
                "sleep": self._generate_sleep_animation()
            }
            
            self.logger.info("GLTF模型数据加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载GLTF模型失败: {e}")
            return False
    
    def _load_obj_model(self) -> bool:
        """加载OBJ模型"""
        try:
            self.logger.info("加载OBJ模型数据...")
            
            # 模拟OBJ模型加载
            self.mesh_data = {
                "vertices": self._generate_cat_vertices(),
                "normals": self._generate_cat_normals(),
                "uvs": self._generate_cat_uvs(),
                "indices": self._generate_cat_indices(),
                "materials": ["cat_material"]
            }
            
            self.logger.info("OBJ模型数据加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载OBJ模型失败: {e}")
            return False
    
    def _load_fbx_model(self) -> bool:
        """加载FBX模型"""
        try:
            self.logger.info("加载FBX模型数据...")
            
            # 模拟FBX模型加载（包含动画和骨架）
            self.mesh_data = {
                "vertices": self._generate_cat_vertices(),
                "normals": self._generate_cat_normals(),
                "uvs": self._generate_cat_uvs(),
                "indices": self._generate_cat_indices(),
                "materials": ["body", "eyes", "nose", "mouth"]
            }
            
            self.skeleton_data = {
                "bones": self._generate_cat_bones(),
                "hierarchy": self._generate_cat_bone_hierarchy(),
                "bind_pose": self._generate_cat_bind_pose(),
                "skin_weights": self._generate_cat_skin_weights()
            }
            
            self.animation_data = {
                "idle": self._generate_idle_animation(),
                "walk": self._generate_walk_animation(),
                "run": self._generate_run_animation(),
                "jump": self._generate_jump_animation(),
                "stretch": self._generate_stretch_animation()
            }
            
            self.logger.info("FBX模型数据加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载FBX模型失败: {e}")
            return False
    
    def _generate_cat_vertices(self) -> np.ndarray:
        """生成猫咪顶点数据"""
        # 创建一个简单的猫咪形状的顶点数据
        # 实际应用中应该从模型文件加载
        vertices = []
        
        # 身体（椭圆体）
        body_vertices = self._generate_ellipsoid_vertices(0.5, 0.3, 1.0, 16, 8)
        vertices.extend(body_vertices)
        
        # 头部（球体）
        head_vertices = self._generate_sphere_vertices(0.3, 12, 8, offset=(0, 0, 0.8))
        vertices.extend(head_vertices)
        
        # 耳朵（圆锥体）
        ear1_vertices = self._generate_cone_vertices(0.08, 0.15, 8, offset=(0.15, 0, 1.1), rotation=(0, 0, 30))
        ear2_vertices = self._generate_cone_vertices(0.08, 0.15, 8, offset=(-0.15, 0, 1.1), rotation=(0, 0, -30))
        vertices.extend(ear1_vertices)
        vertices.extend(ear2_vertices)
        
        # 腿（圆柱体）
        leg_offsets = [(0.2, 0, 0.2), (-0.2, 0, 0.2), (0.15, 0, -0.6), (-0.15, 0, -0.6)]
        for offset in leg_offsets:
            leg_vertices = self._generate_cylinder_vertices(0.06, 0.3, 8, offset=offset)
            vertices.extend(leg_vertices)
        
        # 尾巴（圆锥体）
        tail_vertices = self._generate_cone_vertices(0.05, 0.4, 8, offset=(0, 0, -0.8), rotation=(0, 30, 0))
        vertices.extend(tail_vertices)
        
        return np.array(vertices, dtype=np.float32)
    
    def _generate_ellipsoid_vertices(self, rx: float, ry: float, rz: float, 
                                   segments: int, rings: int) -> List[Tuple]:
        """生成椭圆体顶点"""
        vertices = []
        for i in range(rings + 1):
            phi = i * np.pi / rings
            for j in range(segments):
                theta = j * 2 * np.pi / segments
                x = rx * np.sin(phi) * np.cos(theta)
                y = ry * np.sin(phi) * np.sin(theta)
                z = rz * np.cos(phi)
                vertices.append((x, y, z))
        return vertices
    
    def _generate_sphere_vertices(self, radius: float, segments: int, rings: int, 
                                offset: Tuple = (0, 0, 0)) -> List[Tuple]:
        """生成球体顶点"""
        vertices = []
        for i in range(rings + 1):
            phi = i * np.pi / rings
            for j in range(segments):
                theta = j * 2 * np.pi / segments
                x = offset[0] + radius * np.sin(phi) * np.cos(theta)
                y = offset[1] + radius * np.sin(phi) * np.sin(theta)
                z = offset[2] + radius * np.cos(phi)
                vertices.append((x, y, z))
        return vertices
    
    def _generate_cylinder_vertices(self, radius: float, height: float, segments: int,
                                  offset: Tuple = (0, 0, 0)) -> List[Tuple]:
        """生成圆柱体顶点"""
        vertices = []
        # 侧面
        for i in range(segments):
            theta = i * 2 * np.pi / segments
            x = offset[0] + radius * np.cos(theta)
            y = offset[1] + radius * np.sin(theta)
            vertices.append((x, y, offset[2]))  # 底部
            vertices.append((x, y, offset[2] + height))  # 顶部
        
        # 顶部和底部圆盘
        for z in [offset[2], offset[2] + height]:
            vertices.append((offset[0], offset[1], z))  # 中心点
            for i in range(segments + 1):
                theta = i * 2 * np.pi / segments
                x = offset[0] + radius * np.cos(theta)
                y = offset[1] + radius * np.sin(theta)
                vertices.append((x, y, z))
        
        return vertices
    
    def _generate_cone_vertices(self, radius: float, height: float, segments: int,
                              offset: Tuple = (0, 0, 0), rotation: Tuple = (0, 0, 0)) -> List[Tuple]:
        """生成圆锥体顶点"""
        vertices = []
        # 底部
        vertices.append((offset[0], offset[1], offset[2]))  # 底部中心
        for i in range(segments + 1):
            theta = i * 2 * np.pi / segments
            x = offset[0] + radius * np.cos(theta)
            y = offset[1] + radius * np.sin(theta)
            vertices.append((x, y, offset[2]))
        
        # 侧面和顶点
        apex = (offset[0], offset[1], offset[2] + height)
        vertices.append(apex)
        for i in range(segments + 1):
            theta = i * 2 * np.pi / segments
            x = offset[0] + radius * np.cos(theta)
            y = offset[1] + radius * np.sin(theta)
            vertices.append((x, y, offset[2]))
        
        return vertices
    
    def _generate_cat_normals(self) -> np.ndarray:
        """生成猫咪法线数据"""
        # 简化的法线计算，实际应该基于顶点数据计算
        vertices = self.mesh_data["vertices"]
        normals = []
        
        for vertex in vertices:
            # 计算顶点法线（指向原点的方向）
            length = np.sqrt(vertex[0]**2 + vertex[1]**2 + vertex[2]**2)
            if length > 0:
                normal = (vertex[0]/length, vertex[1]/length, vertex[2]/length)
            else:
                normal = (0, 1, 0)
            normals.append(normal)
        
        return np.array(normals, dtype=np.float32)
    
    def _generate_cat_uvs(self) -> np.ndarray:
        """生成猫咪UV坐标"""
        vertices = self.mesh_data["vertices"]
        uvs = []
        
        for vertex in vertices:
            # 简单的球面映射
            x, y, z = vertex
            u = 0.5 + np.arctan2(z, x) / (2 * np.pi)
            v = 0.5 - np.arcsin(y) / np.pi
            uvs.append((u, v))
        
        return np.array(uvs, dtype=np.float32)
    
    def _generate_cat_indices(self) -> np.ndarray:
        """生成猫咪索引数据"""
        # 简化的索引生成，实际应该基于顶点数据生成
        vertex_count = len(self.mesh_data["vertices"])
        indices = []
        
        # 创建三角形索引（简化版本）
        for i in range(0, vertex_count - 2, 3):
            indices.extend([i, i+1, i+2])
        
        return np.array(indices, dtype=np.uint32)
    
    def _generate_cat_bones(self) -> Dict[str, Any]:
        """生成猫咪骨骼数据"""
        bones = {
            "root": {"id": 0, "parent": -1, "position": (0, 0, 0), "rotation": (0, 0, 0, 1)},
            "spine": {"id": 1, "parent": 0, "position": (0, 0, 0.3), "rotation": (0, 0, 0, 1)},
            "chest": {"id": 2, "parent": 1, "position": (0, 0, 0.3), "rotation": (0, 0, 0, 1)},
            "neck": {"id": 3, "parent": 2, "position": (0, 0, 0.2), "rotation": (0, 0, 0, 1)},
            "head": {"id": 4, "parent": 3, "position": (0, 0, 0.2), "rotation": (0, 0, 0, 1)},
            "left_shoulder": {"id": 5, "parent": 2, "position": (0.15, 0, 0), "rotation": (0, 0, 0, 1)},
            "left_elbow": {"id": 6, "parent": 5, "position": (0, 0, -0.15), "rotation": (0, 0, 0, 1)},
            "left_wrist": {"id": 7, "parent": 6, "position": (0, 0, -0.15), "rotation": (0, 0, 0, 1)},
            "right_shoulder": {"id": 8, "parent": 2, "position": (-0.15, 0, 0), "rotation": (0, 0, 0, 1)},
            "right_elbow": {"id": 9, "parent": 8, "position": (0, 0, -0.15), "rotation": (0, 0, 0, 1)},
            "right_wrist": {"id": 10, "parent": 9, "position": (0, 0, -0.15), "rotation": (0, 0, 0, 1)},
            "left_hip": {"id": 11, "parent": 0, "position": (0.1, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "left_knee": {"id": 12, "parent": 11, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "left_ankle": {"id": 13, "parent": 12, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "right_hip": {"id": 14, "parent": 0, "position": (-0.1, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "right_knee": {"id": 15, "parent": 14, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "right_ankle": {"id": 16, "parent": 15, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "tail_base": {"id": 17, "parent": 0, "position": (0, 0, -0.3), "rotation": (0, 0, 0, 1)},
            "tail_mid": {"id": 18, "parent": 17, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)},
            "tail_tip": {"id": 19, "parent": 18, "position": (0, 0, -0.2), "rotation": (0, 0, 0, 1)}
        }
        
        return bones
    
    def _generate_cat_bone_hierarchy(self) -> Dict[str, List[str]]:
        """生成猫咪骨骼层级关系"""
        hierarchy = {
            "root": ["spine"],
            "spine": ["chest"],
            "chest": ["neck", "left_shoulder", "right_shoulder"],
            "neck": ["head"],
            "head": [],
            "left_shoulder": ["left_elbow"],
            "left_elbow": ["left_wrist"],
            "left_wrist": [],
            "right_shoulder": ["right_elbow"],
            "right_elbow": ["right_wrist"],
            "right_wrist": [],
            "left_hip": ["left_knee"],
            "left_knee": ["left_ankle"],
            "left_ankle": [],
            "right_hip": ["right_knee"],
            "right_knee": ["right_ankle"],
            "right_ankle": [],
            "tail_base": ["tail_mid"],
            "tail_mid": ["tail_tip"],
            "tail_tip": []
        }
        
        return hierarchy
    
    def _generate_cat_bind_pose(self) -> Dict[str, Any]:
        """生成猫咪绑定姿势"""
        bind_pose = {}
        bones = self._generate_cat_bones()
        
        for bone_name, bone_data in bones.items():
            bind_pose[bone_name] = {
                "position": bone_data["position"],
                "rotation": bone_data["rotation"],
                "scale": (1.0, 1.0, 1.0)
            }
        
        return bind_pose
    
    def _generate_cat_skin_weights(self) -> Dict[int, List[Tuple]]:
        """生成猫咪蒙皮权重"""
        # 简化的蒙皮权重，实际应该基于顶点和骨骼关系计算
        skin_weights = {}
        vertices = self.mesh_data["vertices"]
        
        for i, vertex in enumerate(vertices):
            x, y, z = vertex
            
            # 根据顶点位置分配权重
            weights = []
            
            # 身体部分主要受脊柱骨骼影响
            if z > 0.5:  # 上半身
                weights.append((1, 0.6))  # spine
                weights.append((2, 0.4))  # chest
            elif z > 0:  # 中部身体
                weights.append((0, 0.3))  # root
                weights.append((1, 0.7))  # spine
            else:  # 下半身
                weights.append((0, 0.5))  # root
                weights.append((11, 0.25))  # left_hip
                weights.append((14, 0.25))  # right_hip
            
            # 头部
            if z > 0.8:
                weights = [(3, 0.5), (4, 0.5)]
            
            # 四肢
            if abs(x) > 0.1:
                if x > 0:  # 左侧
                    if z > 0:  # 前腿
                        weights = [(5, 0.3), (6, 0.4), (7, 0.3)]
                    else:  # 后腿
                        weights = [(11, 0.3), (12, 0.4), (13, 0.3)]
                else:  # 右侧
                    if z > 0:  # 前腿
                        weights = [(8, 0.3), (9, 0.4), (10, 0.3)]
                    else:  # 后腿
                        weights = [(14, 0.3), (15, 0.4), (16, 0.3)]
            
            # 尾巴
            if z < -0.5:
                weights = [(17, 0.4), (18, 0.4), (19, 0.2)]
            
            skin_weights[i] = weights
        
        return skin_weights
    
    def _generate_idle_animation(self) -> Dict[str, Any]:
        """生成空闲动画"""
        return {
            "duration": 2.0,
            "keyframes": self._generate_breathing_keyframes(),
            "loop": True
        }
    
    def _generate_walk_animation(self) -> Dict[str, Any]:
        """生成行走动画"""
        return {
            "duration": 1.0,
            "keyframes": self._generate_walk_keyframes(),
            "loop": True
        }
    
    def _generate_run_animation(self) -> Dict[str, Any]:
        """生成奔跑动画"""
        return {
            "duration": 0.5,
            "keyframes": self._generate_run_keyframes(),
            "loop": True
        }
    
    def _generate_sit_animation(self) -> Dict[str, Any]:
        """生成坐下动画"""
        return {
            "duration": 1.5,
            "keyframes": self._generate_sit_keyframes(),
            "loop": False
        }
    
    def _generate_sleep_animation(self) -> Dict[str, Any]:
        """生成睡觉动画"""
        return {
            "duration": 4.0,
            "keyframes": self._generate_sleep_keyframes(),
            "loop": True
        }
    
    def _generate_jump_animation(self) -> Dict[str, Any]:
        """生成跳跃动画"""
        return {
            "duration": 1.0,
            "keyframes": self._generate_jump_keyframes(),
            "loop": False
        }
    
    def _generate_stretch_animation(self) -> Dict[str, Any]:
        """生成伸展动画"""
        return {
            "duration": 2.0,
            "keyframes": self._generate_stretch_keyframes(),
            "loop": False
        }
    
    def _generate_breathing_keyframes(self) -> Dict[str, List]:
        """生成呼吸关键帧"""
        keyframes = {}
        
        # 脊柱的轻微上下移动模拟呼吸
        times = [0.0, 1.0, 2.0]
        for bone in ["spine", "chest"]:
            keyframes[bone] = []
            for t in times:
                # 轻微的上下移动
                y_offset = 0.02 * np.sin(t * np.pi)
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_walk_keyframes(self) -> Dict[str, List]:
        """生成行走关键帧"""
        keyframes = {}
        
        times = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        # 腿部的行走动画
        leg_bones = ["left_elbow", "right_elbow", "left_knee", "right_knee"]
        
        for bone in leg_bones:
            keyframes[bone] = []
            for i, t in enumerate(times):
                # 前后摆动
                angle = 30 * np.sin(t * 2 * np.pi)
                if "left" in bone:
                    angle = -angle  # 左右腿相反
                
                keyframes[bone].append({
                    "time": t,
                    "position": (0, 0, 0),
                    "rotation": self._euler_to_quaternion(angle, 0, 0)
                })
        
        # 身体的轻微上下移动
        for bone in ["root"]:
            keyframes[bone] = []
            for t in times:
                y_offset = 0.05 * np.sin(t * 2 * np.pi)
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_run_keyframes(self) -> Dict[str, List]:
        """生成奔跑关键帧"""
        keyframes = {}
        
        times = [0.0, 0.125, 0.25, 0.375, 0.5]
        
        # 腿部的奔跑动画（幅度更大，频率更高）
        leg_bones = ["left_elbow", "right_elbow", "left_knee", "right_knee"]
        
        for bone in leg_bones:
            keyframes[bone] = []
            for i, t in enumerate(times):
                # 更大的前后摆动
                angle = 45 * np.sin(t * 4 * np.pi)
                if "left" in bone:
                    angle = -angle
                
                keyframes[bone].append({
                    "time": t,
                    "position": (0, 0, 0),
                    "rotation": self._euler_to_quaternion(angle, 0, 0)
                })
        
        # 身体的更大上下移动
        for bone in ["root"]:
            keyframes[bone] = []
            for t in times:
                y_offset = 0.1 * np.sin(t * 4 * np.pi)
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_sit_keyframes(self) -> Dict[str, List]:
        """生成坐下关键帧"""
        keyframes = {}
        
        times = [0.0, 0.5, 1.0, 1.5]
        
        # 后腿弯曲
        for bone in ["left_knee", "right_knee"]:
            keyframes[bone] = []
            for i, t in enumerate(times):
                angle = 90 * min(t / 1.0, 1.0)  # 逐渐弯曲到90度
                keyframes[bone].append({
                    "time": t,
                    "position": (0, 0, 0),
                    "rotation": self._euler_to_quaternion(angle, 0, 0)
                })
        
        # 身体下沉
        for bone in ["root"]:
            keyframes[bone] = []
            for i, t in enumerate(times):
                y_offset = -0.2 * min(t / 1.0, 1.0)  # 逐渐下沉
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_sleep_keyframes(self) -> Dict[str, List]:
        """生成睡觉关键帧"""
        keyframes = {}
        
        times = [0.0, 1.0, 2.0, 3.0, 4.0]
        
        # 身体的轻微呼吸移动
        for bone in ["spine", "chest"]:
            keyframes[bone] = []
            for t in times:
                # 缓慢的呼吸移动
                y_offset = 0.01 * np.sin(t * np.pi)
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_jump_keyframes(self) -> Dict[str, List]:
        """生成跳跃关键帧"""
        keyframes = {}
        
        times = [0.0, 0.3, 0.5, 0.7, 1.0]
        
        # 身体的跳跃轨迹
        for bone in ["root"]:
            keyframes[bone] = []
            for t in times:
                if t <= 0.3:  # 准备跳跃
                    y_offset = 0.0
                elif t <= 0.5:  # 上升
                    y_offset = 0.5 * ((t - 0.3) / 0.2)
                elif t <= 0.7:  # 下落
                    y_offset = 0.5 - 0.5 * ((t - 0.5) / 0.2)
                else:  # 落地
                    y_offset = 0.0
                
                keyframes[bone].append({
                    "time": t,
                    "position": (0, y_offset, 0),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _generate_stretch_keyframes(self) -> Dict[str, List]:
        """生成伸展关键帧"""
        keyframes = {}
        
        times = [0.0, 0.5, 1.0, 1.5, 2.0]
        
        # 前腿伸展
        for bone in ["left_elbow", "right_elbow"]:
            keyframes[bone] = []
            for t in times:
                if t <= 1.0:  # 伸展
                    angle = -30 * (t / 1.0)
                else:  # 收回
                    angle = -30 + 30 * ((t - 1.0) / 1.0)
                
                keyframes[bone].append({
                    "time": t,
                    "position": (0, 0, 0),
                    "rotation": self._euler_to_quaternion(angle, 0, 0)
                })
        
        # 身体伸展
        for bone in ["spine", "chest"]:
            keyframes[bone] = []
            for t in times:
                if t <= 1.0:  # 伸展
                    z_offset = 0.1 * (t / 1.0)
                else:  # 收回
                    z_offset = 0.1 - 0.1 * ((t - 1.0) / 1.0)
                
                keyframes[bone].append({
                    "time": t,
                    "position": (0, 0, z_offset),
                    "rotation": (0, 0, 0, 1)
                })
        
        return keyframes
    
    def _euler_to_quaternion(self, x: float, y: float, z: float) -> Tuple:
        """欧拉角转四元数"""
        # 简化的转换，实际应该使用完整的数学转换
        # 这里返回一个近似的四元数
        return (np.sin(x/2), np.sin(y/2), np.sin(z/2), np.cos(x/2)*np.cos(y/2)*np.cos(z/2))
    
    def _calculate_model_stats(self):
        """计算模型统计信息"""
        if "vertices" in self.mesh_data:
            self.stats["vertex_count"] = len(self.mesh_data["vertices"])
        
        if "indices" in self.mesh_data:
            self.stats["triangle_count"] = len(self.mesh_data["indices"]) // 3
        
        # 估算纹理内存
        self.stats["texture_memory"] = self.stats["vertex_count"] * 4 * 3  # 简化的估算
    
    def play_animation(self, animation_name: str, loop: bool = True) -> bool:
        """播放动画"""
        if animation_name not in self.animation_data:
            self.logger.error(f"动画不存在: {animation_name}")
            return False
        
        self.current_animation = animation_name
        self.animation_time = 0.0
        self.stats["render_calls"] += 1
        
        self.logger.info(f"开始播放动画: {animation_name}")
        return True
    
    def update_animation(self, delta_time: float):
        """更新动画状态"""
        if self.current_animation is None:
            return
        
        animation = self.animation_data[self.current_animation]
        self.animation_time += delta_time
        
        # 处理循环
        if animation["loop"] and self.animation_time > animation["duration"]:
            self.animation_time = 0.0
    
    def get_animation_pose(self) -> Dict[str, Any]:
        """获取当前动画姿势"""
        if self.current_animation is None:
            return self._generate_cat_bind_pose()
        
        animation = self.animation_data[self.current_animation]
        keyframes = animation["keyframes"]
        
        current_pose = {}
        
        for bone_name, frames in keyframes.items():
            # 查找当前时间对应的关键帧
            for i in range(len(frames) - 1):
                frame1 = frames[i]
                frame2 = frames[i + 1]
                
                if frame1["time"] <= self.animation_time <= frame2["time"]:
                    # 线性插值
                    t = (self.animation_time - frame1["time"]) / (frame2["time"] - frame1["time"])
                    
                    pos1 = np.array(frame1["position"])
                    pos2 = np.array(frame2["position"])
                    position = pos1 + (pos2 - pos1) * t
                    
                    rot1 = np.array(frame1["rotation"])
                    rot2 = np.array(frame2["rotation"])
                    rotation = self._slerp_quaternion(rot1, rot2, t)
                    
                    current_pose[bone_name] = {
                        "position": tuple(position),
                        "rotation": tuple(rotation)
                    }
                    break
            else:
                # 使用最后一帧
                if frames:
                    current_pose[bone_name] = {
                        "position": frames[-1]["position"],
                        "rotation": frames[-1]["rotation"]
                    }
        
        return current_pose
    
    def _slerp_quaternion(self, q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
        """球面线性插值四元数"""
        # 简化的SLERP实现
        dot = np.dot(q1, q2)
        
        if dot < 0.0:
            q2 = -q2
            dot = -dot
        
        if dot > 0.9995:
            result = q1 + t * (q2 - q1)
            return result / np.linalg.norm(result)
        
        theta_0 = np.arccos(dot)
        sin_theta_0 = np.sin(theta_0)
        
        theta = theta_0 * t
        sin_theta = np.sin(theta)
        
        s1 = np.cos(theta) - dot * sin_theta / sin_theta_0
        s2 = sin_theta / sin_theta_0
        
        return s1 * q1 + s2 * q2
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        info = {
            "model_name": self.config.model_name,
            "is_loaded": self.is_loaded,
            "vertex_count": self.stats["vertex_count"],
            "triangle_count": self.stats["triangle_count"],
            "bone_count": len(self.skeleton_data.get("bones", {})),
            "animation_count": len(self.animation_data),
            "current_animation": self.current_animation,
            "animation_time": self.animation_time
        }
        
        return info
    
    def unload(self):
        """卸载模型"""
        self.model_data = None
        self.mesh_data = {}
        self.texture_data = {}
        self.animation_data = {}
        self.skeleton_data = {}
        self.is_loaded = False
        
        self.logger.info(f"猫咪模型已卸载: {self.config.model_name}")

class CatModelManager:
    """猫咪模型管理器"""
    
    def __init__(self, models_dir: str = "./models/3d/cats"):
        self.models_dir = models_dir
        self.loaded_models: Dict[str, CatModel] = {}
        self.model_configs: Dict[str, CatModelConfig] = {}
        
        # 性能统计
        self.stats = {
            "total_models_loaded": 0,
            "total_memory_used": 0,
            "average_load_time": 0.0
        }
        
        self.logger = self._setup_logger()
        
        # 加载模型配置
        self._load_model_configs()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("CatModelManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _load_model_configs(self):
        """加载模型配置"""
        config_path = os.path.join(self.models_dir, "model_configs.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                for model_name, config_dict in config_data.items():
                    self.model_configs[model_name] = CatModelConfig(**config_dict)
                
                self.logger.info(f"加载了 {len(self.model_configs)} 个模型配置")
            except Exception as e:
                self.logger.warning(f"加载模型配置失败: {e}")
    
    def load_model(self, model_name: str, config: Optional[CatModelConfig] = None) -> Optional[CatModel]:
        """加载猫咪模型"""
        if model_name in self.loaded_models:
            self.logger.info(f"模型已加载: {model_name}")
            return self.loaded_models[model_name]
        
        try:
            # 获取配置
            if config is None:
                if model_name in self.model_configs:
                    config = self.model_configs[model_name]
                else:
                    # 创建默认配置
                    model_path = os.path.join(self.models_dir, f"{model_name}.gltf")
                    config = CatModelConfig(
                        model_name=model_name,
                        model_path=model_path
                    )
            
            # 创建并加载模型
            cat_model = CatModel(config)
            success = cat_model.load()
            
            if success:
                self.loaded_models[model_name] = cat_model
                self.stats["total_models_loaded"] += 1
                self.logger.info(f"猫咪模型加载成功: {model_name}")
                return cat_model
            else:
                self.logger.error(f"猫咪模型加载失败: {model_name}")
                return None
            
        except Exception as e:
            self.logger.error(f"加载猫咪模型时发生错误: {e}")
            return None
    
    def get_model(self, model_name: str) -> Optional[CatModel]:
        """获取已加载的模型"""
        return self.loaded_models.get(model_name)
    
    def unload_model(self, model_name: str) -> bool:
        """卸载模型"""
        if model_name not in self.loaded_models:
            self.logger.warning(f"模型未加载: {model_name}")
            return False
        
        try:
            model = self.loaded_models[model_name]
            model.unload()
            del self.loaded_models[model_name]
            
            self.logger.info(f"猫咪模型已卸载: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载猫咪模型失败: {e}")
            return False
    
    def get_loaded_models(self) -> List[str]:
        """获取已加载的模型列表"""
        return list(self.loaded_models.keys())
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        stats = self.stats.copy()
        stats["loaded_models_count"] = len(self.loaded_models)
        stats["available_configs_count"] = len(self.model_configs)
        
        return stats
    
    def cleanup(self):
        """清理所有模型"""
        for model_name in list(self.loaded_models.keys()):
            self.unload_model(model_name)
        
        self.logger.info("猫咪模型管理器清理完成")
