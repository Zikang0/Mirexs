"""
姿态估计 - 估计用户身体姿态
完整的身体姿态估计系统，支持多人姿态检测和关键点跟踪
"""

import os
import cv2
import numpy as np
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import threading
from datetime import datetime
import json

# 导入依赖
from infrastructure.compute_storage.model_serving_engine import model_serving_engine
from infrastructure.compute_storage.gpu_accelerator import gpu_accelerator
from data.models.vision.mediapipe_integration import MediaPipeIntegration
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.reasoning.state_tracker import StateTracker
from cognitive.memory.working_memory import WorkingMemory
from capabilities.system_management.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class PoseKeypoint:
    """姿态关键点"""
    index: int
    x: float
    y: float
    z: float
    visibility: float
    confidence: float

@dataclass
class PoseResult:
    """姿态估计结果"""
    person_id: int
    keypoints: List[PoseKeypoint]
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    pose_type: str
    activity: str
    tracking_id: Optional[int] = None

@dataclass
class PoseSkeleton:
    """姿态骨骼连接"""
    connections: List[Tuple[int, int]]
    colors: List[Tuple[int, int, int]]

class PoseEstimation:
    """姿态估计系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.pose_detector = None
        self.opencv_utils = OpenCVUtils()
        self.state_tracker = StateTracker()
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 姿态估计配置
        self.min_confidence = self.config.get('min_confidence', 0.5)
        self.max_people = self.config.get('max_people', 6)
        self.enable_tracking = self.config.get('enable_tracking', True)
        self.smooth_poses = self.config.get('smooth_poses', True)
        
        # 骨骼连接定义 (COCO格式)
        self.skeleton = PoseSkeleton(
            connections=[
                # 身体主干
                (0, 1), (1, 2), (2, 3), (3, 4),  # 头部
                (1, 5), (5, 6), (6, 7), (1, 8), (8, 9), (9, 10),  # 手臂
                (1, 11), (11, 12), (12, 13), (1, 14), (14, 15), (15, 16),  # 腿部
                # 面部 (简化)
                (0, 17), (17, 18), (18, 19), (19, 20),  # 右眉毛
                (0, 21), (21, 22), (22, 23), (23, 24),  # 左眉毛
                (0, 25), (25, 26), (26, 27), (27, 28),  # 鼻子到嘴巴
            ],
            colors=[
                (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
                (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
                (64, 0, 0), (0, 64, 0), (0, 0, 64), (64, 64, 0)
            ]
        )
        
        # 姿态类型定义
        self.pose_types = {
            'standing': '站立',
            'sitting': '坐姿', 
            'walking': '行走',
            'running': '跑步',
            'bending': '弯腰',
            'lying': '躺卧',
            'unknown': '未知'
        }
        
        # 活动识别
        self.activities = {
            'working': '工作',
            'exercising': '运动',
            'relaxing': '休息',
            'eating': '进食',
            'reading': '阅读',
            'unknown': '未知'
        }
        
        # 跟踪状态
        self.tracked_poses: Dict[int, PoseResult] = {}
        self.next_tracking_id = 1
        self.pose_history: Dict[int, List[PoseResult]] = {}
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'average_confidence': 0.0,
            'processing_times': [],
            'tracked_people': 0
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.current_session_id = None
        
        self.logger.info("姿态估计系统初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化姿态估计系统"""
        try:
            # 初始化GPU加速器
            await gpu_accelerator.initialize()
            
            # 初始化模型服务引擎
            await model_serving_engine.initialize()
            
            # 加载姿态估计模型
            self.pose_detector = MediaPipeIntegration(use_gpu=False)  # MediaPipe通常在CPU上运行更好
            if not self.pose_detector.load():
                self.logger.error("姿态估计模型加载失败")
                return False
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            # 创建新会话
            self.current_session_id = f"pose_estimation_{int(time.time())}"
            self.state_tracker.register_task(self.current_session_id, [])
            
            self.is_initialized = True
            self.logger.info("姿态估计系统初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"姿态估计系统初始化失败: {e}")
            return False
    
    async def estimate_poses(self, image: np.ndarray) -> Dict[str, Any]:
        """估计图像中的姿态"""
        if not self.is_initialized:
            success = await self.initialize()
            if not success:
                return self._create_error_result("系统未初始化")
        
        start_time = time.time()
        
        try:
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.3,
                current_step="姿态检测"
            )
            
            # 姿态检测
            detection_result = await self._detect_poses(image)
            if not detection_result["success"]:
                return detection_result
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.6,
                current_step="姿态跟踪"
            )
            
            # 姿态跟踪
            if self.enable_tracking:
                tracking_result = await self._track_poses(detection_result["poses"])
            else:
                tracking_result = detection_result
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.8,
                current_step="姿态分析"
            )
            
            # 姿态分析
            analysis_result = await self._analyze_poses(tracking_result["poses"])
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.9,
                current_step="结果整合"
            )
            
            # 整合结果
            final_result = self._combine_results(tracking_result, analysis_result)
            
            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_stats(final_result, processing_time)
            
            # 保存到工作记忆
            await self._update_working_memory(final_result)
            
            # 完成状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "completed", 
                progress=1.0,
                current_step="处理完成"
            )
            
            final_result["processing_time"] = processing_time
            final_result["success"] = True
            
            self.logger.info(f"姿态估计完成: 检测到 {len(final_result['poses'])} 个人")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"姿态估计处理失败: {e}")
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "failed", 
                error_message=str(e)
            )
            return self._create_error_result(str(e))
    
    async def _detect_poses(self, image: np.ndarray) -> Dict[str, Any]:
        """检测姿态"""
        try:
            # 使用MediaPipe进行姿态检测
            pose_result = self.pose_detector.detect_pose(image)
            
            if not pose_result["success"]:
                return self._create_error_result("姿态检测失败")
            
            # 转换为标准格式
            poses = []
            pose_landmarks = pose_result.get("pose_landmarks", [])
            
            if pose_landmarks:
                # 将单个姿态转换为列表
                pose_data = self._convert_landmarks_to_pose(pose_landmarks, 0, image.shape)
                if pose_data:
                    poses.append(pose_data)
            
            return {
                "success": True,
                "poses": poses,
                "person_count": len(poses),
                "image_size": image.shape[:2]
            }
            
        except Exception as e:
            self.logger.error(f"姿态检测失败: {e}")
            return self._create_error_result(f"姿态检测失败: {e}")
    
    def _convert_landmarks_to_pose(self, landmarks: List[Dict], person_id: int, image_shape: Tuple[int, int]) -> Optional[PoseResult]:
        """将关键点转换为姿态结果"""
        if not landmarks or len(landmarks) < 15:  # 至少需要主要关键点
            return None
        
        keypoints = []
        total_confidence = 0.0
        valid_points = 0
        
        # 转换关键点
        for i, landmark in enumerate(landmarks):
            if i >= 33:  # MediaPipe有33个关键点
                break
                
            confidence = landmark.get('visibility', 0.5)
            keypoint = PoseKeypoint(
                index=i,
                x=landmark['x'] * image_shape[1],  # 转换为像素坐标
                y=landmark['y'] * image_shape[0],
                z=landmark.get('z', 0.0),
                visibility=landmark.get('visibility', 0.5),
                confidence=confidence
            )
            keypoints.append(keypoint)
            
            if confidence > self.min_confidence:
                total_confidence += confidence
                valid_points += 1
        
        if valid_points == 0:
            return None
        
        # 计算边界框
        bbox = self._calculate_pose_bbox(keypoints, image_shape)
        
        # 计算整体置信度
        avg_confidence = total_confidence / valid_points if valid_points > 0 else 0.0
        
        # 识别姿态类型
        pose_type = self._classify_pose_type(keypoints)
        
        # 识别活动
        activity = self._classify_activity(keypoints)
        
        return PoseResult(
            person_id=person_id,
            keypoints=keypoints,
            bbox=bbox,
            confidence=avg_confidence,
            pose_type=pose_type,
            activity=activity
        )
    
    def _calculate_pose_bbox(self, keypoints: List[PoseKeypoint], image_shape: Tuple[int, int]) -> List[float]:
        """计算姿态边界框"""
        if not keypoints:
            return [0, 0, 0, 0]
        
        # 只使用可见的关键点
        visible_keypoints = [kp for kp in keypoints if kp.visibility > self.min_confidence]
        
        if not visible_keypoints:
            # 如果没有可见关键点，使用所有关键点
            visible_keypoints = keypoints
        
        xs = [kp.x for kp in visible_keypoints]
        ys = [kp.y for kp in visible_keypoints]
        
        x_min = max(0, min(xs))
        y_min = max(0, min(ys))
        x_max = min(image_shape[1], max(xs))
        y_max = min(image_shape[0], max(ys))
        
        # 添加边距
        margin = 0.1
        width = x_max - x_min
        height = y_max - y_min
        
        x_min = max(0, x_min - width * margin)
        y_min = max(0, y_min - height * margin)
        x_max = min(image_shape[1], x_max + width * margin)
        y_max = min(image_shape[0], y_max + height * margin)
        
        return [x_min, y_min, x_max, y_max]
    
    def _classify_pose_type(self, keypoints: List[PoseKeypoint]) -> str:
        """分类姿态类型"""
        if len(keypoints) < 25:  # 需要足够的关键点
            return 'unknown'
        
        # 提取主要关键点索引 (MediaPipe姿势模型)
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        LEFT_KNEE = 25
        RIGHT_KNEE = 26
        
        # 获取关键点坐标
        def get_keypoint(index):
            if index < len(keypoints) and keypoints[index].visibility > self.min_confidence:
                return keypoints[index].x, keypoints[index].y
            return None
        
        # 计算关键点之间的角度和距离
        left_shoulder = get_keypoint(LEFT_SHOULDER)
        right_shoulder = get_keypoint(RIGHT_SHOULDER)
        left_hip = get_keypoint(LEFT_HIP)
        right_hip = get_keypoint(RIGHT_HIP)
        left_ankle = get_keypoint(LEFT_ANKLE)
        right_ankle = get_keypoint(RIGHT_ANKLE)
        left_knee = get_keypoint(LEFT_KNEE)
        right_knee = get_keypoint(RIGHT_KNEE)
        
        # 简单的姿态分类逻辑
        if left_ankle and right_ankle and left_hip and right_hip:
            # 计算臀部与脚踝的相对位置
            avg_hip_y = (left_hip[1] + right_hip[1]) / 2
            avg_ankle_y = (left_ankle[1] + right_ankle[1]) / 2
            
            hip_ankle_distance = abs(avg_hip_y - avg_ankle_y)
            
            if hip_ankle_distance < 50:  # 臀部与脚踝很近，可能是坐姿或躺姿
                if left_knee and right_knee:
                    knee_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
                    if knee_angle < 120:  # 膝盖弯曲角度小，可能是坐姿
                        return 'sitting'
                    else:
                        return 'lying'
                return 'sitting'
            else:
                # 站立或行走
                if left_shoulder and right_shoulder:
                    shoulder_movement = abs(left_shoulder[0] - right_shoulder[0])
                    if shoulder_movement > 20:  # 肩膀有较大水平移动，可能是行走
                        return 'walking'
                return 'standing'
        
        return 'unknown'
    
    def _classify_activity(self, keypoints: List[PoseKeypoint]) -> str:
        """分类活动类型"""
        pose_type = self._classify_pose_type(keypoints)
        
        # 基于姿态类型推断活动
        if pose_type == 'sitting':
            return 'working'  # 假设坐姿通常是工作
        elif pose_type == 'standing':
            return 'working'  # 假设站姿也是工作
        elif pose_type == 'walking':
            return 'exercising'
        elif pose_type == 'running':
            return 'exercising'
        elif pose_type == 'lying':
            return 'relaxing'
        else:
            return 'unknown'
    
    def _calculate_angle(self, point1: Tuple[float, float], point2: Tuple[float, float], point3: Tuple[float, float]) -> float:
        """计算三点形成的角度"""
        import math
        
        # 向量1: point2 -> point1
        vec1 = (point1[0] - point2[0], point1[1] - point2[1])
        # 向量2: point2 -> point3
        vec2 = (point3[0] - point2[0], point3[1] - point2[1])
        
        # 计算点积
        dot_product = vec1[0] * vec2[0] + vec1[1] * vec2[1]
        
        # 计算模长
        mag1 = math.sqrt(vec1[0]**2 + vec1[1]**2)
        mag2 = math.sqrt(vec2[0]**2 + vec2[1]**2)
        
        if mag1 * mag2 == 0:
            return 0.0
        
        # 计算角度 (弧度)
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # 确保在有效范围内
        angle_rad = math.acos(cos_angle)
        
        # 转换为角度
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    async def _track_poses(self, poses: List[PoseResult]) -> Dict[str, Any]:
        """跟踪姿态"""
        try:
            if not self.enable_tracking:
                return {"success": True, "poses": poses}
            
            tracked_poses = []
            
            for pose in poses:
                # 寻找最佳匹配的已跟踪姿态
                best_match_id = None
                best_match_score = 0.0
                
                for tracking_id, tracked_pose in self.tracked_poses.items():
                    score = self._calculate_tracking_score(pose, tracked_pose)
                    if score > best_match_score and score > 0.5:  # 匹配阈值
                        best_match_score = score
                        best_match_id = tracking_id
                
                if best_match_id is not None:
                    # 更新已跟踪的姿态
                    pose.tracking_id = best_match_id
                    self.tracked_poses[best_match_id] = pose
                    
                    # 更新历史
                    if best_match_id not in self.pose_history:
                        self.pose_history[best_match_id] = []
                    self.pose_history[best_match_id].append(pose)
                    
                    # 保持历史长度
                    if len(self.pose_history[best_match_id]) > 30:  # 最近30帧
                        self.pose_history[best_match_id].pop(0)
                else:
                    # 新跟踪的姿态
                    tracking_id = self.next_tracking_id
                    self.next_tracking_id += 1
                    pose.tracking_id = tracking_id
                    self.tracked_poses[tracking_id] = pose
                    self.pose_history[tracking_id] = [pose]
                
                tracked_poses.append(pose)
            
            # 清理丢失的跟踪
            self._cleanup_lost_tracks()
            
            return {
                "success": True,
                "poses": tracked_poses,
                "tracked_count": len(tracked_poses)
            }
            
        except Exception as e:
            self.logger.error(f"姿态跟踪失败: {e}")
            return {"success": True, "poses": poses}  # 跟踪失败时返回原始姿态
    
    def _calculate_tracking_score(self, pose1: PoseResult, pose2: PoseResult) -> float:
        """计算姿态跟踪匹配分数"""
        # 基于边界框重叠和关键点相似度
        bbox_overlap = self._calculate_bbox_overlap(pose1.bbox, pose2.bbox)
        
        # 关键点距离
        keypoint_distance = 0.0
        valid_points = 0
        
        for kp1, kp2 in zip(pose1.keypoints, pose2.keypoints):
            if kp1.visibility > self.min_confidence and kp2.visibility > self.min_confidence:
                dx = kp1.x - kp2.x
                dy = kp1.y - kp2.y
                distance = np.sqrt(dx*dx + dy*dy)
                keypoint_distance += distance
                valid_points += 1
        
        if valid_points > 0:
            keypoint_distance /= valid_points
            # 转换为相似度分数 (距离越小分数越高)
            keypoint_similarity = max(0.0, 1.0 - keypoint_distance / 100.0)  # 假设100像素为最大距离
        else:
            keypoint_similarity = 0.0
        
        # 综合分数
        total_score = 0.7 * bbox_overlap + 0.3 * keypoint_similarity
        
        return total_score
    
    def _calculate_bbox_overlap(self, bbox1: List[float], bbox2: List[float]) -> float:
        """计算边界框重叠度"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # 计算交集
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        
        # 计算并集
        bbox1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        bbox2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = bbox1_area + bbox2_area - intersection_area
        
        return intersection_area / union_area if union_area > 0 else 0.0
    
    def _cleanup_lost_tracks(self):
        """清理丢失的跟踪"""
        current_time = time.time()
        tracks_to_remove = []
        
        for tracking_id, pose in self.tracked_poses.items():
            # 这里应该基于时间或其他条件判断是否丢失
            # 简化实现：如果跟踪历史很短，认为可能丢失
            if tracking_id in self.pose_history and len(self.pose_history[tracking_id]) < 3:
                tracks_to_remove.append(tracking_id)
        
        for tracking_id in tracks_to_remove:
            del self.tracked_poses[tracking_id]
            if tracking_id in self.pose_history:
                del self.pose_history[tracking_id]
    
    async def _analyze_poses(self, poses: List[PoseResult]) -> Dict[str, Any]:
        """分析姿态"""
        try:
            analyzed_poses = []
            
            for pose in poses:
                # 这里可以进行更复杂的姿态分析
                # 例如：动作识别、姿态质量评估等
                
                analyzed_poses.append(pose)
            
            return {
                "success": True,
                "poses": analyzed_poses
            }
            
        except Exception as e:
            self.logger.error(f"姿态分析失败: {e}")
            return {"success": True, "poses": poses}
    
    def _combine_results(self, tracking_result: Dict, analysis_result: Dict) -> Dict[str, Any]:
        """整合结果"""
        return {
            "poses": analysis_result["poses"],
            "person_count": len(analysis_result["poses"]),
            "tracked_count": tracking_result.get("tracked_count", 0),
            "image_size": tracking_result.get("image_size", (0, 0))
        }
    
    def _update_stats(self, result: Dict[str, Any], processing_time: float):
        """更新性能统计"""
        self.stats['total_detections'] += result['person_count']
        self.stats['processing_times'].append(processing_time)
        self.stats['tracked_people'] = len(self.tracked_poses)
        
        # 保持最近100次处理时间
        if len(self.stats['processing_times']) > 100:
            self.stats['processing_times'].pop(0)
        
        # 计算平均置信度
        if result['poses']:
            avg_conf = sum(pose.confidence for pose in result['poses']) / len(result['poses'])
            self.stats['average_confidence'] = 0.9 * self.stats['average_confidence'] + 0.1 * avg_conf
    
    async def _update_working_memory(self, result: Dict[str, Any]):
        """更新工作记忆"""
        try:
            # 保存姿态结果
            await self.working_memory.store(
                key="last_pose_estimation",
                value=result,
                ttl=300,  # 5分钟
                priority=7
            )
            
            # 保存跟踪信息
            if self.enable_tracking:
                await self.working_memory.store(
                    key="current_tracked_poses",
                    value={
                        "tracked_count": len(self.tracked_poses),
                        "tracking_ids": list(self.tracked_poses.keys())
                    },
                    ttl=600,  # 10分钟
                    priority=6
                )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    def draw_poses(self, image: np.ndarray, poses: List[PoseResult]) -> np.ndarray:
        """在图像上绘制姿态"""
        result_image = image.copy()
        
        for pose in poses:
            # 绘制关键点
            for keypoint in pose.keypoints:
                if keypoint.visibility > self.min_confidence:
                    x, y = int(keypoint.x), int(keypoint.y)
                    cv2.circle(result_image, (x, y), 4, (0, 255, 0), -1)
            
            # 绘制骨骼连接
            for i, (start_idx, end_idx) in enumerate(self.skeleton.connections):
                if (start_idx < len(pose.keypoints) and end_idx < len(pose.keypoints)):
                    start_kp = pose.keypoints[start_idx]
                    end_kp = pose.keypoints[end_idx]
                    
                    if (start_kp.visibility > self.min_confidence and 
                        end_kp.visibility > self.min_confidence):
                        
                        start_pt = (int(start_kp.x), int(start_kp.y))
                        end_pt = (int(end_kp.x), int(end_kp.y))
                        
                        color = self.skeleton.colors[i % len(self.skeleton.colors)]
                        cv2.line(result_image, start_pt, end_pt, color, 2)
            
            # 绘制边界框和标签
            if pose.bbox:
                x1, y1, x2, y2 = map(int, pose.bbox)
                cv2.rectangle(result_image, (x1, y1), (x2, y2), (255, 0, 0), 2)
                
                # 标签
                label = f"Pose {pose.person_id}"
                if pose.tracking_id:
                    label += f" (Track {pose.tracking_id})"
                label += f" {pose.pose_type} - {pose.activity}"
                
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(result_image, 
                            (x1, y1 - label_size[1] - 10),
                            (x1 + label_size[0], y1),
                            (255, 0, 0), -1)
                cv2.putText(result_image, label,
                          (x1, y1 - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return result_image
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "poses": [],
            "person_count": 0,
            "tracked_count": 0,
            "image_size": (0, 0)
        }
    
    def get_tracking_info(self) -> Dict[str, Any]:
        """获取跟踪信息"""
        return {
            "tracked_people": len(self.tracked_poses),
            "tracking_ids": list(self.tracked_poses.keys()),
            "next_tracking_id": self.next_tracking_id,
            "pose_history_sizes": {tid: len(history) for tid, history in self.pose_history.items()}
        }
    
    def clear_tracking(self) -> Dict[str, Any]:
        """清空跟踪状态"""
        count = len(self.tracked_poses)
        self.tracked_poses.clear()
        self.pose_history.clear()
        self.next_tracking_id = 1
        
        return {
            "success": True,
            "cleared_tracks": count,
            "message": f"已清空 {count} 个跟踪"
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "min_confidence": self.min_confidence,
            "max_people": self.max_people,
            "enable_tracking": self.enable_tracking,
            "smooth_poses": self.smooth_poses,
            "stats": self.stats,
            "tracking_info": self.get_tracking_info()
        }

# 全局姿态估计实例
pose_estimation_system = PoseEstimation()

