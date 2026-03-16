"""
动画数据 - 猫咪动画数据
"""

import os
import json
import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

@dataclass
class AnimationConfig:
    """动画配置"""
    name: str
    duration: float
    fps: int = 30
    loop: bool = True
    blend_time: float = 0.2
    priority: int = 0

@dataclass
class Keyframe:
    """关键帧数据"""
    time: float
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float, float]  # 四元数
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)

class AnimationClip:
    """动画片段"""
    
    def __init__(self, config: AnimationConfig):
        self.config = config
        self.keyframes: Dict[str, List[Keyframe]] = {}
        self.bone_mapping: Dict[str, str] = {}
        self.is_loaded = False
        
        # 动画状态
        self.current_time = 0.0
        self.playback_speed = 1.0
        self.is_playing = False
        
        # 性能统计
        self.stats = {
            "play_count": 0,
            "total_play_time": 0.0,
            "blend_count": 0
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(f"AnimationClip_{self.config.name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载动画数据"""
        try:
            self.logger.info(f"从文件加载动画: {file_path}")
            
            if not os.path.exists(file_path):
                self.logger.error(f"动画文件不存在: {file_path}")
                return False
            
            # 根据文件类型加载
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.json':
                success = self._load_json_animation(file_path)
            elif file_ext == '.anim':
                success = self._load_binary_animation(file_path)
            else:
                self.logger.error(f"不支持的动画格式: {file_ext}")
                return False
            
            if success:
                self.is_loaded = True
                self.logger.info(f"动画加载成功: {self.config.name}")
            else:
                self.logger.error(f"动画加载失败: {self.config.name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"加载动画时发生错误: {e}")
            return False
    
    def _load_json_animation(self, file_path: str) -> bool:
        """加载JSON格式动画"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 解析动画数据
            self.config.name = data.get('name', self.config.name)
            self.config.duration = data.get('duration', self.config.duration)
            self.config.fps = data.get('fps', self.config.fps)
            self.config.loop = data.get('loop', self.config.loop)
            
            # 解析关键帧数据
            keyframes_data = data.get('keyframes', {})
            for bone_name, frames in keyframes_data.items():
                self.keyframes[bone_name] = []
                for frame_data in frames:
                    keyframe = Keyframe(
                        time=frame_data['time'],
                        position=tuple(frame_data['position']),
                        rotation=tuple(frame_data['rotation']),
                        scale=tuple(frame_data.get('scale', (1.0, 1.0, 1.0)))
                    )
                    self.keyframes[bone_name].append(keyframe)
            
            # 解析骨骼映射
            self.bone_mapping = data.get('bone_mapping', {})
            
            self.logger.info(f"JSON动画数据解析完成: {len(self.keyframes)} 个骨骼")
            return True
            
        except Exception as e:
            self.logger.error(f"解析JSON动画失败: {e}")
            return False
    
    def _load_binary_animation(self, file_path: str) -> bool:
        """加载二进制格式动画"""
        try:
            # 模拟二进制动画加载
            self.logger.info("加载二进制动画数据...")
            
            # 创建模拟的关键帧数据
            self._generate_cat_animations()
            
            self.logger.info("二进制动画数据加载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"加载二进制动画失败: {e}")
            return False
    
    def _generate_cat_animations(self):
        """生成猫咪动画数据"""
        # 为不同动画类型生成关键帧
        if "idle" in self.config.name.lower():
            self._generate_idle_animation()
        elif "walk" in self.config.name.lower():
            self._generate_walk_animation()
        elif "run" in self.config.name.lower():
            self._generate_run_animation()
        elif "jump" in self.config.name.lower():
            self._generate_jump_animation()
        elif "sit" in self.config.name.lower():
            self._generate_sit_animation()
        elif "sleep" in self.config.name.lower():
            self._generate_sleep_animation()
        else:
            self._generate_default_animation()
    
    def _generate_idle_animation(self):
        """生成空闲动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 脊柱的呼吸运动
        spine_bones = ["spine", "chest"]
        for bone in spine_bones:
            self.keyframes[bone] = []
            for t in times:
                # 轻微的上下移动模拟呼吸
                y_offset = 0.02 * math.sin(t * math.pi * 2)
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, y_offset, 0),
                    rotation=(0, 0, 0, 1)
                ))
        
        # 尾巴的轻微摆动
        tail_bones = ["tail_base", "tail_mid", "tail_tip"]
        for i, bone in enumerate(tail_bones):
            self.keyframes[bone] = []
            for t in times:
                # 逐渐减弱的摆动
                swing = 5 * math.sin(t * math.pi * 0.5) * (1 - i * 0.3)
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(0, swing, 0)
                ))
    
    def _generate_walk_animation(self):
        """生成行走动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 腿部运动
        leg_pairs = [
            ("left_elbow", "right_knee"),
            ("right_elbow", "left_knee")
        ]
        
        for front_leg, back_leg in leg_pairs:
            self.keyframes[front_leg] = []
            self.keyframes[back_leg] = []
            
            for t in times:
                # 前后摆动
                front_angle = 30 * math.sin(t * math.pi * 2)
                back_angle = -30 * math.sin(t * math.pi * 2)  # 相反相位
                
                self.keyframes[front_leg].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(front_angle, 0, 0)
                ))
                
                self.keyframes[back_leg].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(back_angle, 0, 0)
                ))
        
        # 身体的上下移动
        self.keyframes["root"] = []
        for t in times:
            y_offset = 0.05 * math.sin(t * math.pi * 2)
            self.keyframes["root"].append(Keyframe(
                time=t,
                position=(0, y_offset, 0),
                rotation=(0, 0, 0, 1)
            ))
    
    def _generate_run_animation(self):
        """生成奔跑动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 更大幅度的腿部运动
        leg_pairs = [
            ("left_elbow", "right_knee"),
            ("right_elbow", "left_knee")
        ]
        
        for front_leg, back_leg in leg_pairs:
            self.keyframes[front_leg] = []
            self.keyframes[back_leg] = []
            
            for t in times:
                # 更大的前后摆动
                front_angle = 45 * math.sin(t * math.pi * 4)
                back_angle = -45 * math.sin(t * math.pi * 4)
                
                self.keyframes[front_leg].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(front_angle, 0, 0)
                ))
                
                self.keyframes[back_leg].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(back_angle, 0, 0)
                ))
        
        # 更大的身体移动
        self.keyframes["root"] = []
        for t in times:
            y_offset = 0.1 * math.sin(t * math.pi * 4)
            self.keyframes["root"].append(Keyframe(
                time=t,
                position=(0, y_offset, 0),
                rotation=(0, 0, 0, 1)
            ))
    
    def _generate_jump_animation(self):
        """生成跳跃动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 身体的跳跃轨迹
        self.keyframes["root"] = []
        for t in times:
            if t <= 0.3:  # 准备阶段
                y_offset = 0.0
            elif t <= 0.5:  # 上升阶段
                y_offset = 0.5 * ((t - 0.3) / 0.2)
            elif t <= 0.7:  # 下落阶段
                y_offset = 0.5 - 0.5 * ((t - 0.5) / 0.2)
            else:  # 落地阶段
                y_offset = 0.0
            
            self.keyframes["root"].append(Keyframe(
                time=t,
                position=(0, y_offset, 0),
                rotation=(0, 0, 0, 1)
            ))
        
        # 腿部的跳跃动作
        leg_bones = ["left_elbow", "right_elbow", "left_knee", "right_knee"]
        for bone in leg_bones:
            self.keyframes[bone] = []
            for t in times:
                if t <= 0.3:  # 准备阶段 - 弯曲
                    angle = 30
                elif t <= 0.5:  # 上升阶段 - 伸展
                    angle = -20
                elif t <= 0.7:  # 下落阶段 - 准备落地
                    angle = 15
                else:  # 落地阶段 - 缓冲
                    angle = 45 * (1 - (t - 0.7) / 0.3)
                
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(angle, 0, 0)
                ))
    
    def _generate_sit_animation(self):
        """生成坐下动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 后腿弯曲
        hind_legs = ["left_knee", "right_knee"]
        for bone in hind_legs:
            self.keyframes[bone] = []
            for t in times:
                angle = 90 * min(t / 0.8, 1.0)  # 逐渐弯曲
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(angle, 0, 0)
                ))
        
        # 身体下沉
        self.keyframes["root"] = []
        for t in times:
            y_offset = -0.2 * min(t / 0.8, 1.0)  # 逐渐下沉
            self.keyframes["root"].append(Keyframe(
                time=t,
                position=(0, y_offset, 0),
                rotation=(0, 0, 0, 1)
            ))
        
        # 前腿调整
        front_legs = ["left_elbow", "right_elbow"]
        for bone in front_legs:
            self.keyframes[bone] = []
            for t in times:
                angle = -15 * min(t / 0.8, 1.0)  # 轻微前倾
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, 0, 0),
                    rotation=self._euler_to_quaternion(angle, 0, 0)
                ))
    
    def _generate_sleep_animation(self):
        """生成睡觉动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 身体的呼吸运动
        body_bones = ["spine", "chest"]
        for bone in body_bones:
            self.keyframes[bone] = []
            for t in times:
                # 缓慢的呼吸
                y_offset = 0.01 * math.sin(t * math.pi)
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, y_offset, 0),
                    rotation=(0, 0, 0, 1)
                ))
        
        # 头部放松
        self.keyframes["head"] = []
        for t in times:
            # 轻微的头部摆动
            rotation = self._euler_to_quaternion(0, 2 * math.sin(t * math.pi * 0.2), 0)
            self.keyframes["head"].append(Keyframe(
                time=t,
                position=(0, 0, 0),
                rotation=rotation
            ))
    
    def _generate_default_animation(self):
        """生成默认动画"""
        times = np.linspace(0, self.config.duration, int(self.config.duration * self.config.fps))
        
        # 为所有主要骨骼生成轻微运动
        main_bones = ["root", "spine", "chest", "head"]
        for bone in main_bones:
            self.keyframes[bone] = []
            for t in times:
                # 轻微的运动
                y_offset = 0.01 * math.sin(t * math.pi * 2)
                self.keyframes[bone].append(Keyframe(
                    time=t,
                    position=(0, y_offset, 0),
                    rotation=(0, 0, 0, 1)
                ))
    
    def _euler_to_quaternion(self, x: float, y: float, z: float) -> Tuple[float, float, float, float]:
        """欧拉角转四元数"""
        # 转换为弧度
        x = math.radians(x)
        y = math.radians(y)
        z = math.radians(z)
        
        # 计算四元数
        cy = math.cos(z * 0.5)
        sy = math.sin(z * 0.5)
        cp = math.cos(y * 0.5)
        sp = math.sin(y * 0.5)
        cr = math.cos(x * 0.5)
        sr = math.sin(x * 0.5)
        
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        
        return (x, y, z, w)
    
    def play(self):
        """播放动画"""
        self.is_playing = True
        self.current_time = 0.0
        self.stats["play_count"] += 1
        
        self.logger.info(f"开始播放动画: {self.config.name}")
    
    def stop(self):
        """停止动画"""
        self.is_playing = False
        self.logger.info(f"停止播放动画: {self.config.name}")
    
    def pause(self):
        """暂停动画"""
        self.is_playing = False
        self.logger.info(f"暂停播放动画: {self.config.name}")
    
    def update(self, delta_time: float):
        """更新动画状态"""
        if not self.is_playing:
            return
        
        self.current_time += delta_time * self.playback_speed
        
        # 处理循环
        if self.config.loop and self.current_time > self.config.duration:
            self.current_time = 0.0
        
        self.stats["total_play_time"] += delta_time
    
    def get_pose_at_time(self, time: float) -> Dict[str, Dict[str, Tuple]]:
        """获取指定时间的姿势"""
        pose = {}
        
        for bone_name, keyframes in self.keyframes.items():
            if not keyframes:
                continue
            
            # 查找当前时间对应的关键帧
            frame1, frame2 = self._find_keyframes(keyframes, time)
            
            if frame1 and frame2:
                # 线性插值
                t = (time - frame1.time) / (frame2.time - frame1.time)
                
                position = self._lerp_position(frame1.position, frame2.position, t)
                rotation = self._slerp_rotation(frame1.rotation, frame2.rotation, t)
                scale = self._lerp_scale(frame1.scale, frame2.scale, t)
                
                pose[bone_name] = {
                    "position": position,
                    "rotation": rotation,
                    "scale": scale
                }
            elif frame1:
                # 只有一帧
                pose[bone_name] = {
                    "position": frame1.position,
                    "rotation": frame1.rotation,
                    "scale": frame1.scale
                }
        
        return pose
    
    def get_current_pose(self) -> Dict[str, Dict[str, Tuple]]:
        """获取当前姿势"""
        return self.get_pose_at_time(self.current_time)
    
    def _find_keyframes(self, keyframes: List[Keyframe], time: float) -> Tuple[Optional[Keyframe], Optional[Keyframe]]:
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
    
    def _lerp_position(self, pos1: Tuple, pos2: Tuple, t: float) -> Tuple:
        """位置线性插值"""
        return tuple(p1 + (p2 - p1) * t for p1, p2 in zip(pos1, pos2))
    
    def _slerp_rotation(self, rot1: Tuple, rot2: Tuple, t: float) -> Tuple:
        """旋转球面线性插值"""
        # 简化的SLERP实现
        q1 = np.array(rot1)
        q2 = np.array(rot2)
        
        dot = np.dot(q1, q2)
        
        if dot < 0.0:
            q2 = -q2
            dot = -dot
        
        if dot > 0.9995:
            result = q1 + t * (q2 - q1)
            return tuple(result / np.linalg.norm(result))
        
        theta_0 = np.arccos(dot)
        sin_theta_0 = np.sin(theta_0)
        
        theta = theta_0 * t
        sin_theta = np.sin(theta)
        
        s1 = np.cos(theta) - dot * sin_theta / sin_theta_0
        s2 = sin_theta / sin_theta_0
        
        result = s1 * q1 + s2 * q2
        return tuple(result / np.linalg.norm(result))
    
    def _lerp_scale(self, scale1: Tuple, scale2: Tuple, t: float) -> Tuple:
        """缩放线性插值"""
        return self._lerp_position(scale1, scale2, t)
    
    def get_animation_info(self) -> Dict[str, Any]:
        """获取动画信息"""
        bone_count = len(self.keyframes)
        keyframe_count = sum(len(frames) for frames in self.keyframes.values())
        
        return {
            "name": self.config.name,
            "duration": self.config.duration,
            "fps": self.config.fps,
            "loop": self.config.loop,
            "bone_count": bone_count,
            "keyframe_count": keyframe_count,
            "is_loaded": self.is_loaded,
            "is_playing": self.is_playing,
            "current_time": self.current_time,
            "stats": self.stats.copy()
        }
    
    def save_to_file(self, file_path: str) -> bool:
        """保存动画到文件"""
        try:
            self.logger.info(f"保存动画到文件: {file_path}")
            
            data = {
                "name": self.config.name,
                "duration": self.config.duration,
                "fps": self.config.fps,
                "loop": self.config.loop,
                "keyframes": {},
                "bone_mapping": self.bone_mapping
            }
            
            # 转换关键帧数据
            for bone_name, keyframes in self.keyframes.items():
                data["keyframes"][bone_name] = []
                for keyframe in keyframes:
                    data["keyframes"][bone_name].append({
                        "time": keyframe.time,
                        "position": keyframe.position,
                        "rotation": keyframe.rotation,
                        "scale": keyframe.scale
                    })
            
            # 保存为JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"动画保存成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存动画失败: {e}")
            return False

class AnimationManager:
    """动画管理器"""
    
    def __init__(self, animations_dir: str = "./models/3d/animations"):
        self.animations_dir = animations_dir
        self.loaded_animations: Dict[str, AnimationClip] = {}
        self.animation_blends: Dict[str, float] = {}  # 动画混合权重
        
        # 性能统计
        self.stats = {
            "total_animations_loaded": 0,
            "active_animations": 0,
            "total_blend_time": 0.0
        }
        
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger("AnimationManager")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_animation(self, name: str, config: AnimationConfig, file_path: Optional[str] = None) -> Optional[AnimationClip]:
        """加载动画"""
        if name in self.loaded_animations:
            self.logger.info(f"动画已加载: {name}")
            return self.loaded_animations[name]
        
        try:
            # 如果没有提供文件路径，使用默认路径
            if file_path is None:
                file_path = os.path.join(self.animations_dir, f"{name}.json")
            
            # 创建动画片段
            animation = AnimationClip(config)
            success = animation.load_from_file(file_path)
            
            if success:
                self.loaded_animations[name] = animation
                self.stats["total_animations_loaded"] += 1
                self.logger.info(f"动画加载成功: {name}")
                return animation
            else:
                self.logger.error(f"动画加载失败: {name}")
                return None
            
        except Exception as e:
            self.logger.error(f"加载动画时发生错误: {e}")
            return None
    
    def play_animation(self, name: str, blend_time: float = 0.2) -> bool:
        """播放动画"""
        if name not in self.loaded_animations:
            self.logger.error(f"动画未加载: {name}")
            return False
        
        animation = self.loaded_animations[name]
        animation.play()
        
        # 设置混合权重
        self.animation_blends[name] = 0.0
        
        self.logger.info(f"开始播放动画: {name}")
        return True
    
    def stop_animation(self, name: str) -> bool:
        """停止动画"""
        if name not in self.loaded_animations:
            self.logger.error(f"动画未加载: {name}")
            return False
        
        animation = self.loaded_animations[name]
        animation.stop()
        
        # 移除混合权重
        if name in self.animation_blends:
            del self.animation_blends[name]
        
        self.logger.info(f"停止播放动画: {name}")
        return True
    
    def blend_animations(self, animation_weights: Dict[str, float]) -> Dict[str, Dict[str, Tuple]]:
        """混合多个动画"""
        if not animation_weights:
            return {}
        
        # 归一化权重
        total_weight = sum(animation_weights.values())
        if total_weight == 0:
            return {}
        
        normalized_weights = {name: weight / total_weight for name, weight in animation_weights.items()}
        
        # 获取所有动画的当前姿势
        poses = {}
        for name, weight in normalized_weights.items():
            if name in self.loaded_animations and weight > 0:
                animation = self.loaded_animations[name]
                poses[name] = animation.get_current_pose()
        
        if not poses:
            return {}
        
        # 混合姿势
        blended_pose = {}
        reference_pose = next(iter(poses.values()))
        
        for bone_name in reference_pose.keys():
            blended_position = np.zeros(3)
            blended_rotation = np.zeros(4)
            blended_scale = np.zeros(3)
            
            total_bone_weight = 0.0
            
            for anim_name, pose in poses.items():
                if bone_name in pose:
                    weight = normalized_weights[anim_name]
                    bone_data = pose[bone_name]
                    
                    # 累加位置和缩放
                    blended_position += np.array(bone_data["position"]) * weight
                    blended_scale += np.array(bone_data["scale"]) * weight
                    
                    # 累加旋转（使用SLERP）
                    if total_bone_weight == 0:
                        blended_rotation = np.array(bone_data["rotation"])
                    else:
                        blended_rotation = self._slerp_rotations(
                            blended_rotation, 
                            np.array(bone_data["rotation"]), 
                            weight / (total_bone_weight + weight)
                        )
                    
                    total_bone_weight += weight
            
            # 归一化旋转
            if np.linalg.norm(blended_rotation) > 0:
                blended_rotation = blended_rotation / np.linalg.norm(blended_rotation)
            
            blended_pose[bone_name] = {
                "position": tuple(blended_position),
                "rotation": tuple(blended_rotation),
                "scale": tuple(blended_scale)
            }
        
        self.stats["total_blend_time"] += 1
        return blended_pose
    
    def _slerp_rotations(self, q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
        """两个旋转之间的球面线性插值"""
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
    
    def update_animations(self, delta_time: float):
        """更新所有动画"""
        active_count = 0
        
        for animation in self.loaded_animations.values():
            if animation.is_playing:
                animation.update(delta_time)
                active_count += 1
        
        self.stats["active_animations"] = active_count
        
        # 更新混合权重
        for name in list(self.animation_blends.keys()):
            if name in self.loaded_animations:
                animation = self.loaded_animations[name]
                if animation.is_playing:
                    self.animation_blends[name] = min(self.animation_blends[name] + delta_time / 0.2, 1.0)
                else:
                    self.animation_blends[name] = max(self.animation_blends[name] - delta_time / 0.2, 0.0)
                    
                    # 如果权重为0，移除混合
                    if self.animation_blends[name] <= 0:
                        del self.animation_blends[name]
    
    def get_current_blended_pose(self) -> Dict[str, Dict[str, Tuple]]:
        """获取当前混合姿势"""
        return self.blend_animations(self.animation_blends)
    
    def get_animation(self, name: str) -> Optional[AnimationClip]:
        """获取动画"""
        return self.loaded_animations.get(name)
    
    def get_loaded_animations(self) -> List[str]:
        """获取已加载的动画列表"""
        return list(self.loaded_animations.keys())
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        stats = self.stats.copy()
        stats["loaded_animations_count"] = len(self.loaded_animations)
        stats["active_blends"] = len(self.animation_blends)
        
        return stats
    
    def unload_animation(self, name: str) -> bool:
        """卸载动画"""
        if name not in self.loaded_animations:
            self.logger.warning(f"动画未加载: {name}")
            return False
        
        try:
            animation = self.loaded_animations[name]
            animation.stop()
            del self.loaded_animations[name]
            
            # 移除混合权重
            if name in self.animation_blends:
                del self.animation_blends[name]
            
            self.logger.info(f"动画已卸载: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载动画失败: {e}")
            return False
    
    def cleanup(self):
        """清理所有动画"""
        for name in list(self.loaded_animations.keys()):
            self.unload_animation(name)
        
        self.logger.info("动画管理器清理完成")

