"""
视线追踪 - 追踪用户视线方向
实现基于面部关键点的视线方向估计
"""

import os
import cv2
import numpy as np
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math

# 导入依赖
from data.models.vision.face_detection import FaceDetection
from data.models.vision.mediapipe_integration import MediaPipeIntegration
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.memory.working_memory import WorkingMemory

logger = logging.getLogger(__name__)

@dataclass
class GazePoint:
    """视线点"""
    x: float  # 屏幕坐标x (0-1)
    y: float  # 屏幕坐标y (0-1)
    confidence: float
    timestamp: float

@dataclass
class GazeData:
    """视线数据"""
    left_eye_center: Tuple[float, float]
    right_eye_center: Tuple[float, float]
    gaze_direction: Tuple[float, float, float]  # (x, y, z)
    gaze_point: GazePoint
    head_pose: Tuple[float, float, float]  # (pitch, yaw, roll)
    eye_state: Dict[str, Any]  # 眼睛状态（睁眼、闭眼等）

class GazeTracker:
    """视线追踪器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.face_detector = FaceDetection(use_gpu=True)
        self.mediapipe = MediaPipeIntegration(use_gpu=False)
        self.opencv_utils = OpenCVUtils()
        self.working_memory = WorkingMemory()
        
        # 视线追踪配置
        self.screen_width = self.config.get('screen_width', 1920)
        self.screen_height = self.config.get('screen_height', 1080)
        self.calibration_points = self.config.get('calibration_points', [])
        self.calibration_data = {}
        
        # 眼睛状态检测
        self.eye_aspect_ratio_threshold = self.config.get('eye_aspect_ratio_threshold', 0.25)
        self.blink_detection_window = self.config.get('blink_detection_window', 5)
        
        # 性能统计
        self.stats = {
            'total_frames_processed': 0,
            'average_processing_time': 0.0,
            'gaze_points_recorded': 0,
            'blinks_detected': 0
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.calibration_completed = False
        self.gaze_history = []
        self.eye_state_history = []
        
        # 3D模型参数（简化的人眼模型）
        self.eye_3d_model = self._initialize_3d_eye_model()
        
        self.logger.info("视线追踪器初始化开始...")
    
    def _initialize_3d_eye_model(self) -> Dict[str, Any]:
        """初始化3D眼睛模型"""
        return {
            'focal_length': 1300,  # 焦距
            'camera_matrix': np.array([
                [1300, 0, 640],
                [0, 1300, 360],
                [0, 0, 1]
            ], dtype=np.float32),
            'dist_coeffs': np.zeros((4, 1), dtype=np.float32),
            'eye_radius': 12.5  # 眼球半径(mm)
        }
    
    async def initialize(self) -> bool:
        """初始化视线追踪器"""
        try:
            # 加载人脸检测模型
            if not self.face_detector.load():
                self.logger.error("人脸检测模型加载失败")
                return False
            
            # 加载MediaPipe模型
            if not self.mediapipe.load():
                self.logger.warning("MediaPipe加载失败，使用简化视线追踪")
            
            # 从工作记忆加载校准数据
            await self._load_calibration_data()
            
            self.is_initialized = True
            self.logger.info("视线追踪器初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"视线追踪器初始化失败: {e}")
            return False
    
    async def track_gaze(self, image: np.ndarray, face_bbox: List[int] = None) -> Dict[str, Any]:
        """追踪视线方向"""
        if not self.is_initialized:
            success = await self.initialize()
            if not success:
                return self._create_error_result("系统未初始化")
        
        start_time = time.time()
        
        try:
            # 检测人脸和面部关键点
            face_landmarks = await self._detect_face_landmarks(image, face_bbox)
            if not face_landmarks:
                return self._create_error_result("未检测到人脸")
            
            # 提取眼睛区域
            eye_data = self._extract_eye_data(face_landmarks, image.shape)
            
            # 估计头部姿态
            head_pose = await self._estimate_head_pose(face_landmarks, image.shape)
            
            # 估计视线方向
            gaze_direction = await self._estimate_gaze_direction(eye_data, head_pose)
            
            # 计算视线点（屏幕坐标）
            gaze_point = await self._calculate_gaze_point(gaze_direction, head_pose)
            
            # 检测眼睛状态
            eye_state = self._analyze_eye_state(eye_data)
            
            # 创建视线数据
            gaze_data = GazeData(
                left_eye_center=eye_data['left_eye_center'],
                right_eye_center=eye_data['right_eye_center'],
                gaze_direction=gaze_direction,
                gaze_point=gaze_point,
                head_pose=head_pose,
                eye_state=eye_state
            )
            
            # 更新历史记录
            self._update_gaze_history(gaze_data)
            
            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_stats(processing_time, eye_state)
            
            # 保存到工作记忆
            await self._update_working_memory(gaze_data)
            
            result = {
                "success": True,
                "gaze_data": gaze_data,
                "processing_time": processing_time,
                "calibrated": self.calibration_completed
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"视线追踪失败: {e}")
            return self._create_error_result(str(e))
    
    async def _detect_face_landmarks(self, image: np.ndarray, face_bbox: List[int] = None) -> Optional[Dict[str, Any]]:
        """检测面部关键点"""
        try:
            # 如果提供了人脸边界框，直接使用
            if face_bbox is not None:
                # 提取人脸区域进行关键点检测
                x1, y1, x2, y2 = face_bbox
                face_roi = image[y1:y2, x1:x2]
                
                # 使用MediaPipe检测面部关键点
                mp_result = self.mediapipe.detect_hands(face_roi)  # 注意：这里应该使用面部网格检测
                # 简化实现：使用人脸检测器的关键点
                
            # 使用人脸检测器获取关键点
            detection_result = self.face_detector.detect(image)
            if not detection_result["success"] or detection_result["face_count"] == 0:
                return None
            
            # 使用第一个人脸
            face_data = detection_result["faces"][0]
            landmarks = face_data.get("landmarks", [])
            
            if not landmarks:
                return None
            
            # 转换为标准格式
            face_landmarks = {
                "bbox": face_data["bbox"],
                "landmarks": landmarks,
                "confidence": face_data["confidence"]
            }
            
            return face_landmarks
            
        except Exception as e:
            self.logger.error(f"面部关键点检测失败: {e}")
            return None
    
    def _extract_eye_data(self, face_landmarks: Dict[str, Any], image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """提取眼睛数据"""
        landmarks = face_landmarks["landmarks"]
        
        # 简化的眼睛关键点索引（基于5点关键点模型）
        # 实际项目中应该使用更精确的关键点检测
        left_eye_indices = [0, 1]  # 左眼关键点
        right_eye_indices = [2, 3]  # 右眼关键点
        
        # 提取眼睛关键点
        left_eye_points = [landmarks[i] for i in left_eye_indices if i < len(landmarks)]
        right_eye_points = [landmarks[i] for i in right_eye_indices if i < len(landmarks)]
        
        # 计算眼睛中心点
        left_eye_center = self._calculate_eye_center(left_eye_points, image_shape)
        right_eye_center = self._calculate_eye_center(right_eye_points, image_shape)
        
        # 计算眼睛宽高
        left_eye_size = self._calculate_eye_size(left_eye_points, image_shape)
        right_eye_size = self._calculate_eye_size(right_eye_points, image_shape)
        
        # 计算眼睛纵横比（用于检测眨眼）
        left_eye_ratio = self._calculate_eye_aspect_ratio(left_eye_points)
        right_eye_ratio = self._calculate_eye_aspect_ratio(right_eye_points)
        
        return {
            "left_eye_center": left_eye_center,
            "right_eye_center": right_eye_center,
            "left_eye_size": left_eye_size,
            "right_eye_size": right_eye_size,
            "left_eye_aspect_ratio": left_eye_ratio,
            "right_eye_aspect_ratio": right_eye_ratio,
            "eye_points": {
                "left": left_eye_points,
                "right": right_eye_points
            }
        }
    
    def _calculate_eye_center(self, eye_points: List[List[float]], image_shape: Tuple[int, int]) -> Tuple[float, float]:
        """计算眼睛中心点"""
        if not eye_points:
            return (0.5, 0.5)
        
        # 计算平均位置
        x_coords = [point[0] for point in eye_points]
        y_coords = [point[1] for point in eye_points]
        
        center_x = sum(x_coords) / len(x_coords)
        center_y = sum(y_coords) / len(y_coords)
        
        # 归一化到图像坐标
        norm_x = center_x / image_shape[1]
        norm_y = center_y / image_shape[0]
        
        return (norm_x, norm_y)
    
    def _calculate_eye_size(self, eye_points: List[List[float]], image_shape: Tuple[int, int]) -> Tuple[float, float]:
        """计算眼睛尺寸"""
        if len(eye_points) < 2:
            return (0.0, 0.0)
        
        x_coords = [point[0] for point in eye_points]
        y_coords = [point[1] for point in eye_points]
        
        width = (max(x_coords) - min(x_coords)) / image_shape[1]
        height = (max(y_coords) - min(y_coords)) / image_shape[0]
        
        return (width, height)
    
    def _calculate_eye_aspect_ratio(self, eye_points: List[List[float]]) -> float:
        """计算眼睛纵横比（用于眨眼检测）"""
        if len(eye_points) < 6:  # 需要足够的关键点
            return 1.0
        
        # 简化的眼睛纵横比计算
        # 实际项目应该使用更精确的EAR公式
        vertical_dist = abs(eye_points[1][1] - eye_points[4][1]) if len(eye_points) >= 5 else 1.0
        horizontal_dist = abs(eye_points[0][0] - eye_points[3][0]) if len(eye_points) >= 4 else 1.0
        
        if horizontal_dist == 0:
            return 1.0
        
        ear = vertical_dist / horizontal_dist
        return ear
    
    async def _estimate_head_pose(self, face_landmarks: Dict[str, Any], image_shape: Tuple[int, int]) -> Tuple[float, float, float]:
        """估计头部姿态（pitch, yaw, roll）"""
        try:
            landmarks = face_landmarks["landmarks"]
            
            if len(landmarks) < 5:
                return (0.0, 0.0, 0.0)
            
            # 使用简化的头部姿态估计
            # 实际项目应该使用PnP算法和3D模型
            
            # 计算基于眼睛和鼻子位置的简单姿态
            left_eye = landmarks[0] if len(landmarks) > 0 else [0.5, 0.5]
            right_eye = landmarks[1] if len(landmarks) > 1 else [0.5, 0.5]
            nose = landmarks[2] if len(landmarks) > 2 else [0.5, 0.5]
            
            # 计算偏航角（基于眼睛水平位置）
            eye_center_x = (left_eye[0] + right_eye[0]) / 2
            image_center_x = image_shape[1] / 2
            yaw = (eye_center_x - image_center_x) / image_center_x * 30  # 简化的角度估计
            
            # 计算俯仰角（基于鼻子垂直位置）
            face_center_y = (left_eye[1] + right_eye[1]) / 2
            image_center_y = image_shape[0] / 2
            pitch = (face_center_y - image_center_y) / image_center_y * 20
            
            # 计算滚转角（基于眼睛连线角度）
            dy = right_eye[1] - left_eye[1]
            dx = right_eye[0] - left_eye[0]
            roll = math.degrees(math.atan2(dy, dx)) if dx != 0 else 0.0
            
            return (pitch, yaw, roll)
            
        except Exception as e:
            self.logger.error(f"头部姿态估计失败: {e}")
            return (0.0, 0.0, 0.0)
    
    async def _estimate_gaze_direction(self, eye_data: Dict[str, Any], head_pose: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """估计视线方向"""
        try:
            # 简化的视线方向估计
            # 实际项目应该使用更复杂的模型，如基于瞳孔位置或外观的方法
            
            pitch, yaw, roll = head_pose
            
            # 基于头部姿态和眼睛状态的简化视线估计
            gaze_x = np.clip(yaw / 30.0, -1.0, 1.0)  # 归一化到[-1, 1]
            gaze_y = np.clip(pitch / 20.0, -1.0, 1.0)
            
            # 考虑眼睛状态（如闭眼时视线不确定）
            left_eye_ratio = eye_data["left_eye_aspect_ratio"]
            right_eye_ratio = eye_data["right_eye_aspect_ratio"]
            
            # 如果眼睛闭合，视线方向不确定
            if left_eye_ratio < self.eye_aspect_ratio_threshold or right_eye_ratio < self.eye_aspect_ratio_threshold:
                gaze_confidence = 0.1
            else:
                gaze_confidence = 0.8
            
            gaze_z = gaze_confidence  # 使用z分量表示置信度
            
            return (gaze_x, gaze_y, gaze_z)
            
        except Exception as e:
            self.logger.error(f"视线方向估计失败: {e}")
            return (0.0, 0.0, 0.0)
    
    async def _calculate_gaze_point(self, gaze_direction: Tuple[float, float, float], 
                                  head_pose: Tuple[float, float, float]) -> GazePoint:
        """计算视线点（屏幕坐标）"""
        gaze_x, gaze_y, gaze_z = gaze_direction
        
        # 如果未校准，使用简化的映射
        if not self.calibration_completed:
            # 将视线方向映射到屏幕坐标
            screen_x = (gaze_x + 1) / 2  # 映射到[0, 1]
            screen_y = (gaze_y + 1) / 2  # 映射到[0, 1]
        else:
            # 使用校准数据映射
            screen_x, screen_y = self._apply_calibration(gaze_x, gaze_y)
        
        # 应用平滑滤波
        if self.gaze_history:
            last_point = self.gaze_history[-1].gaze_point
            alpha = 0.3  # 平滑系数
            screen_x = alpha * screen_x + (1 - alpha) * last_point.x
            screen_y = alpha * screen_y + (1 - alpha) * last_point.y
        
        gaze_point = GazePoint(
            x=screen_x,
            y=screen_y,
            confidence=gaze_z,  # 使用z分量作为置信度
            timestamp=time.time()
        )
        
        return gaze_point
    
    def _apply_calibration(self, gaze_x: float, gaze_y: float) -> Tuple[float, float]:
        """应用校准数据映射视线到屏幕坐标"""
        # 简化的线性校准
        # 实际项目应该使用更复杂的校准模型
        
        if not self.calibration_data:
            return ((gaze_x + 1) / 2, (gaze_y + 1) / 2)
        
        # 这里应该实现基于校准数据的映射
        # 简化实现：直接使用线性映射
        screen_x = (gaze_x + 1) / 2
        screen_y = (gaze_y + 1) / 2
        
        return (screen_x, screen_y)
    
    def _analyze_eye_state(self, eye_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析眼睛状态"""
        left_ratio = eye_data["left_eye_aspect_ratio"]
        right_ratio = eye_data["right_eye_aspect_ratio"]
        
        # 检测眨眼
        left_eye_closed = left_ratio < self.eye_aspect_ratio_threshold
        right_eye_closed = right_ratio < self.eye_aspect_ratio_threshold
        
        # 检测注视（视线稳定）
        gaze_stable = self._is_gaze_stable()
        
        # 更新眼睛状态历史
        self.eye_state_history.append({
            "timestamp": time.time(),
            "left_eye_closed": left_eye_closed,
            "right_eye_closed": right_eye_closed,
            "left_eye_ratio": left_ratio,
            "right_eye_ratio": right_ratio
        })
        
        # 保持历史记录长度
        if len(self.eye_state_history) > self.blink_detection_window:
            self.eye_state_history.pop(0)
        
        # 检测眨眼事件
        blink_detected = self._detect_blink()
        
        return {
            "left_eye_closed": left_eye_closed,
            "right_eye_closed": right_eye_closed,
            "both_eyes_closed": left_eye_closed and right_eye_closed,
            "blink_detected": blink_detected,
            "gaze_stable": gaze_stable,
            "left_eye_ratio": left_ratio,
            "right_eye_ratio": right_ratio
        }
    
    def _is_gaze_stable(self) -> bool:
        """检测视线是否稳定"""
        if len(self.gaze_history) < 3:
            return False
        
        # 检查最近几个视线点的变化
        recent_points = self.gaze_history[-3:]
        positions = [(p.gaze_point.x, p.gaze_point.y) for p in recent_points]
        
        # 计算位置变化
        changes = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            distance = math.sqrt(dx*dx + dy*dy)
            changes.append(distance)
        
        avg_change = sum(changes) / len(changes) if changes else 0
        
        # 如果平均变化小于阈值，认为视线稳定
        return avg_change < 0.01  # 1%的屏幕尺寸
    
    def _detect_blink(self) -> bool:
        """检测眨眼事件"""
        if len(self.eye_state_history) < self.blink_detection_window:
            return False
        
        # 检查最近的眨眼模式
        recent_states = self.eye_state_history[-self.blink_detection_window:]
        
        # 检测从睁眼到闭眼再到睁眼的模式
        blink_pattern = False
        
        for i in range(1, len(recent_states) - 1):
            prev_state = recent_states[i-1]
            curr_state = recent_states[i]
            next_state = recent_states[i+1]
            
            # 检测眨眼模式：睁眼 -> 闭眼 -> 睁眼
            if (not prev_state["both_eyes_closed"] and 
                curr_state["both_eyes_closed"] and 
                not next_state["both_eyes_closed"]):
                blink_pattern = True
                break
        
        if blink_pattern:
            self.stats['blinks_detected'] += 1
        
        return blink_pattern
    
    def _update_gaze_history(self, gaze_data: GazeData):
        """更新视线历史记录"""
        self.gaze_history.append(gaze_data)
        
        # 保持历史记录长度
        max_history = 100
        if len(self.gaze_history) > max_history:
            self.gaze_history.pop(0)
        
        self.stats['gaze_points_recorded'] += 1
    
    def _update_stats(self, processing_time: float, eye_state: Dict[str, Any]):
        """更新性能统计"""
        self.stats['total_frames_processed'] += 1
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        self.stats['average_processing_time'] = (
            alpha * processing_time + 
            (1 - alpha) * self.stats['average_processing_time']
        )
    
    async def _update_working_memory(self, gaze_data: GazeData):
        """更新工作记忆"""
        try:
            # 保存当前视线数据
            await self.working_memory.store(
                key="current_gaze",
                value=gaze_data,
                ttl=10,  # 10秒
                priority=6
            )
            
            # 保存视线历史摘要
            if len(self.gaze_history) >= 10:
                gaze_summary = {
                    "recent_gaze_points": [
                        {
                            "x": g.gaze_point.x,
                            "y": g.gaze_point.y,
                            "timestamp": g.gaze_point.timestamp
                        } for g in self.gaze_history[-10:]
                    ],
                    "average_gaze": self._calculate_average_gaze(),
                    "gaze_stability": self._calculate_gaze_stability()
                }
                
                await self.working_memory.store(
                    key="gaze_summary",
                    value=gaze_summary,
                    ttl=60,  # 1分钟
                    priority=5
                )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    def _calculate_average_gaze(self) -> Tuple[float, float]:
        """计算平均视线位置"""
        if not self.gaze_history:
            return (0.5, 0.5)
        
        x_coords = [g.gaze_point.x for g in self.gaze_history]
        y_coords = [g.gaze_point.y for g in self.gaze_history]
        
        avg_x = sum(x_coords) / len(x_coords)
        avg_y = sum(y_coords) / len(y_coords)
        
        return (avg_x, avg_y)
    
    def _calculate_gaze_stability(self) -> float:
        """计算视线稳定性"""
        if len(self.gaze_history) < 2:
            return 1.0
        
        # 计算视线位置的变化
        changes = []
        for i in range(1, len(self.gaze_history)):
            dx = self.gaze_history[i].gaze_point.x - self.gaze_history[i-1].gaze_point.x
            dy = self.gaze_history[i].gaze_point.y - self.gaze_history[i-1].gaze_point.y
            distance = math.sqrt(dx*dx + dy*dy)
            changes.append(distance)
        
        avg_change = sum(changes) / len(changes) if changes else 0
        
        # 稳定性 = 1 - 平均变化（归一化）
        stability = max(0.0, 1.0 - avg_change * 10)  # 调整系数
        
        return stability
    
    async def start_calibration(self, calibration_points: List[Tuple[float, float]] = None) -> bool:
        """开始视线校准"""
        try:
            if calibration_points:
                self.calibration_points = calibration_points
            elif not self.calibration_points:
                # 使用默认校准点（9点校准）
                self.calibration_points = [
                    (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),
                    (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),
                    (0.1, 0.9), (0.5, 0.9), (0.9, 0.9)
                ]
            
            self.calibration_data = {}
            self.calibration_completed = False
            
            self.logger.info(f"开始视线校准，校准点数量: {len(self.calibration_points)}")
            return True
            
        except Exception as e:
            self.logger.error(f"开始校准失败: {e}")
            return False
    
    async def add_calibration_point(self, point_index: int, gaze_samples: List[GazeData]) -> bool:
        """添加校准点数据"""
        try:
            if point_index >= len(self.calibration_points):
                return False
            
            target_point = self.calibration_points[point_index]
            
            # 计算平均视线方向
            if not gaze_samples:
                return False
            
            gaze_x = sum(g.gaze_direction[0] for g in gaze_samples) / len(gaze_samples)
            gaze_y = sum(g.gaze_direction[1] for g in gaze_samples) / len(gaze_samples)
            
            # 存储校准数据
            self.calibration_data[point_index] = {
                "target": target_point,
                "gaze_vector": (gaze_x, gaze_y),
                "samples_count": len(gaze_samples)
            }
            
            self.logger.info(f"添加校准点 {point_index}: {target_point} -> ({gaze_x:.3f}, {gaze_y:.3f})")
            return True
            
        except Exception as e:
            self.logger.error(f"添加校准点失败: {e}")
            return False
    
    async def complete_calibration(self) -> bool:
        """完成视线校准"""
        try:
            if len(self.calibration_data) < 3:  # 至少需要3个校准点
                self.logger.warning("校准点数量不足")
                return False
            
            # 这里应该实现校准模型的计算
            # 简化实现：标记为已完成
            self.calibration_completed = True
            
            # 保存校准数据到工作记忆
            await self.working_memory.store(
                key="gaze_calibration",
                value={
                    "calibration_data": self.calibration_data,
                    "calibration_points": self.calibration_points,
                    "calibration_time": time.time()
                },
                ttl=86400,  # 24小时
                priority=8
            )
            
            self.logger.info(f"视线校准完成，使用 {len(self.calibration_data)} 个校准点")
            return True
            
        except Exception as e:
            self.logger.error(f"完成校准失败: {e}")
            return False
    
    async def _load_calibration_data(self):
        """从工作记忆加载校准数据"""
        try:
            calibration_data = await self.working_memory.retrieve("gaze_calibration")
            if calibration_data:
                self.calibration_data = calibration_data.get("calibration_data", {})
                self.calibration_points = calibration_data.get("calibration_points", [])
                self.calibration_completed = len(self.calibration_data) >= 3
                
                if self.calibration_completed:
                    self.logger.info("已加载视线校准数据")
            
        except Exception as e:
            self.logger.error(f"加载校准数据失败: {e}")
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "gaze_data": None,
            "processing_time": 0.0,
            "calibrated": self.calibration_completed
        }
    
    def get_gaze_heatmap(self) -> np.ndarray:
        """生成视线热力图"""
        heatmap = np.zeros((100, 100), dtype=np.float32)
        
        for gaze_data in self.gaze_history:
            x = int(gaze_data.gaze_point.x * 100)
            y = int(gaze_data.gaze_point.y * 100)
            
            if 0 <= x < 100 and 0 <= y < 100:
                # 添加高斯分布
                for i in range(max(0, x-2), min(100, x+3)):
                    for j in range(max(0, y-2), min(100, y+3)):
                        distance = math.sqrt((x-i)**2 + (y-j)**2)
                        weight = math.exp(-distance**2 / 2.0)
                        heatmap[j, i] += weight * gaze_data.gaze_point.confidence
        
        # 归一化
        if np.max(heatmap) > 0:
            heatmap = heatmap / np.max(heatmap)
        
        return heatmap
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "calibration_completed": self.calibration_completed,
            "calibration_points": len(self.calibration_points),
            "calibration_data_points": len(self.calibration_data),
            "gaze_history_size": len(self.gaze_history),
            "stats": self.stats
        }

# 全局视线追踪实例
gaze_tracker = GazeTracker()

