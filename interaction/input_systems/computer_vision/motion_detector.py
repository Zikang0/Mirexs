"""
运动检测器 - 检测运动变化
基于帧差法和背景减除的实时运动检测系统
"""

import cv2
import numpy as np
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
from collections import deque

# 导入依赖
from infrastructure.compute_storage.gpu_accelerator import gpu_accelerator
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.memory.working_memory import WorkingMemory
from capabilities.system_management.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

class MotionType(Enum):
    """运动类型枚举"""
    STATIONARY = "stationary"  # 静止
    SLOW_MOVEMENT = "slow_movement"  # 慢速运动
    FAST_MOVEMENT = "fast_movement"  # 快速运动
    OBJECT_APPEARANCE = "object_appearance"  # 物体出现
    OBJECT_DISAPPEARANCE = "object_disappearance"  # 物体消失

@dataclass
class MotionRegion:
    """运动区域"""
    region_id: int
    bbox: List[int]  # [x, y, width, height]
    centroid: Tuple[int, int]  # 质心坐标
    area: int  # 区域面积
    motion_type: MotionType
    confidence: float
    velocity: Optional[Tuple[float, float]] = None  # 运动速度 (dx, dy)
    trajectory: List[Tuple[int, int]] = None  # 运动轨迹

@dataclass
class MotionEvent:
    """运动事件"""
    event_id: str
    event_type: MotionType
    timestamp: float
    regions: List[MotionRegion]
    overall_motion_level: float  # 整体运动级别 0-1
    frame_difference: np.ndarray  # 帧差图像

class MotionDetector:
    """运动检测器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化工具
        self.opencv_utils = OpenCVUtils()
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 背景建模
        self.background_subtractor = None
        self.background_model = None
        self.background_update_rate = self.config.get('background_update_rate', 0.01)
        
        # 运动检测参数
        self.motion_threshold = self.config.get('motion_threshold', 25)
        self.min_contour_area = self.config.get('min_contour_area', 500)
        self.max_contour_area = self.config.get('max_contour_area', 50000)
        self.dilation_iterations = self.config.get('dilation_iterations', 2)
        
        # 跟踪参数
        self.tracked_regions: Dict[int, MotionRegion] = {}
        self.next_region_id = 0
        self.trajectory_length = self.config.get('trajectory_length', 10)
        
        # 状态变量
        self.previous_frame = None
        self.previous_gray = None
        self.is_initialized = False
        self.frame_count = 0
        
        # 性能统计
        self.stats = {
            'total_frames_processed': 0,
            'motion_detection_count': 0,
            'average_processing_time': 0.0,
            'motion_level_history': deque(maxlen=100)
        }
        
        # 事件记录
        self.motion_events: deque = deque(maxlen=100)
        
        self.logger.info("运动检测器初始化完成")
    
    def initialize(self, frame_shape: Tuple[int, int]) -> bool:
        """初始化运动检测器"""
        try:
            # 创建背景减除器
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,  # 历史帧数
                varThreshold=16,  # 方差阈值
                detectShadows=True  # 检测阴影
            )
            
            # 初始化背景模型
            self.background_model = np.zeros(frame_shape, dtype=np.uint8)
            
            self.is_initialized = True
            self.logger.info(f"运动检测器初始化完成，帧形状: {frame_shape}")
            return True
            
        except Exception as e:
            self.logger.error(f"运动检测器初始化失败: {e}")
            return False
    
    def process_frame(self, frame: np.ndarray) -> Optional[MotionEvent]:
        """处理单帧图像进行运动检测"""
        if not self.is_initialized:
            if not self.initialize(frame.shape[:2]):
                return None
        
        start_time = time.time()
        
        try:
            # 转换为灰度图
            gray = self.opencv_utils.rgb_to_gray(frame)
            
            # 更新背景模型
            fg_mask = self.background_subtractor.apply(gray)
            
            # 后处理前景掩码
            processed_mask = self._postprocess_mask(fg_mask)
            
            # 检测运动区域
            motion_regions = self._detect_motion_regions(processed_mask, gray)
            
            # 跟踪运动区域
            tracked_regions = self._track_regions(motion_regions)
            
            # 计算整体运动级别
            motion_level = self._calculate_motion_level(processed_mask, tracked_regions)
            
            # 创建运动事件
            motion_event = MotionEvent(
                event_id=f"motion_{int(time.time())}_{self.frame_count}",
                event_type=self._classify_motion_type(motion_level, tracked_regions),
                timestamp=time.time(),
                regions=tracked_regions,
                overall_motion_level=motion_level,
                frame_difference=processed_mask
            )
            
            # 保存事件
            self.motion_events.append(motion_event)
            
            # 更新状态
            self.previous_frame = frame.copy()
            self.previous_gray = gray.copy()
            self.frame_count += 1
            
            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_stats(motion_event, processing_time)
            
            # 保存到工作记忆
            self._update_working_memory(motion_event)
            
            self.logger.debug(f"运动检测完成: {len(tracked_regions)} 个运动区域, 运动级别: {motion_level:.3f}")
            
            return motion_event
            
        except Exception as e:
            self.logger.error(f"运动检测处理失败: {e}")
            return None
    
    def _postprocess_mask(self, fg_mask: np.ndarray) -> np.ndarray:
        """后处理前景掩码"""
        # 二值化
        _, binary_mask = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)
        
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
        
        # 膨胀连接断裂区域
        dilated_mask = cv2.dilate(cleaned_mask, kernel, iterations=self.dilation_iterations)
        
        return dilated_mask
    
    def _detect_motion_regions(self, mask: np.ndarray, gray_frame: np.ndarray) -> List[MotionRegion]:
        """检测运动区域"""
        motion_regions = []
        
        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # 计算轮廓面积
            area = cv2.contourArea(contour)
            
            # 过滤太小或太大的区域
            if area < self.min_contour_area or area > self.max_contour_area:
                continue
            
            # 计算边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算质心
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            
            # 计算运动置信度（基于区域面积和形状）
            confidence = min(1.0, area / self.max_contour_area)
            
            # 创建运动区域
            region = MotionRegion(
                region_id=self.next_region_id,
                bbox=[x, y, w, h],
                centroid=(cx, cy),
                area=int(area),
                motion_type=MotionType.SLOW_MOVEMENT,  # 初始分类
                confidence=confidence
            )
            
            motion_regions.append(region)
            self.next_region_id += 1
        
        return motion_regions
    
    def _track_regions(self, current_regions: List[MotionRegion]) -> List[MotionRegion]:
        """跟踪运动区域"""
        if not self.tracked_regions:
            # 第一帧，初始化跟踪
            for region in current_regions:
                self.tracked_regions[region.region_id] = region
            return current_regions
        
        # 计算区域之间的关联
        updated_regions = []
        used_track_ids = set()
        
        for current_region in current_regions:
            best_match_id = None
            best_distance = float('inf')
            
            # 寻找最近的历史区域
            for track_id, tracked_region in self.tracked_regions.items():
                if track_id in used_track_ids:
                    continue
                
                # 计算质心距离
                dist = np.sqrt(
                    (current_region.centroid[0] - tracked_region.centroid[0])**2 +
                    (current_region.centroid[1] - tracked_region.centroid[1])**2
                )
                
                # 考虑区域大小的相似性
                area_similarity = abs(current_region.area - tracked_region.area) / max(current_region.area, tracked_region.area)
                combined_distance = dist + area_similarity * 100
                
                if combined_distance < best_distance and combined_distance < 100:  # 距离阈值
                    best_distance = combined_distance
                    best_match_id = track_id
            
            if best_match_id is not None:
                # 更新现有跟踪区域
                tracked_region = self.tracked_regions[best_match_id]
                
                # 计算速度
                dx = current_region.centroid[0] - tracked_region.centroid[0]
                dy = current_region.centroid[1] - tracked_region.centroid[1]
                velocity = (dx, dy)
                
                # 更新轨迹
                if tracked_region.trajectory is None:
                    tracked_region.trajectory = []
                
                tracked_region.trajectory.append(current_region.centroid)
                if len(tracked_region.trajectory) > self.trajectory_length:
                    tracked_region.trajectory.pop(0)
                
                # 更新区域属性
                tracked_region.bbox = current_region.bbox
                tracked_region.centroid = current_region.centroid
                tracked_region.area = current_region.area
                tracked_region.confidence = current_region.confidence
                tracked_region.velocity = velocity
                tracked_region.motion_type = self._classify_region_motion(tracked_region)
                
                updated_regions.append(tracked_region)
                used_track_ids.add(best_match_id)
                
            else:
                # 新区域
                current_region.trajectory = [current_region.centroid]
                self.tracked_regions[current_region.region_id] = current_region
                updated_regions.append(current_region)
        
        # 清理丢失的跟踪区域（超过一定帧数未更新）
        lost_track_ids = []
        for track_id in self.tracked_regions:
            if track_id not in used_track_ids:
                # 这里可以增加丢失帧数计数，暂时简单处理
                lost_track_ids.append(track_id)
        
        for track_id in lost_track_ids:
            del self.tracked_regions[track_id]
        
        return updated_regions
    
    def _classify_region_motion(self, region: MotionRegion) -> MotionType:
        """分类区域运动类型"""
        if region.velocity is None:
            return MotionType.STATIONARY
        
        # 计算速度大小
        speed = np.sqrt(region.velocity[0]**2 + region.velocity[1]**2)
        
        if speed < 2.0:
            return MotionType.STATIONARY
        elif speed < 10.0:
            return MotionType.SLOW_MOVEMENT
        else:
            return MotionType.FAST_MOVEMENT
    
    def _classify_motion_type(self, motion_level: float, regions: List[MotionRegion]) -> MotionType:
        """分类整体运动类型"""
        if motion_level < 0.1:
            return MotionType.STATIONARY
        
        # 分析区域运动类型分布
        motion_counts = {
            MotionType.STATIONARY: 0,
            MotionType.SLOW_MOVEMENT: 0,
            MotionType.FAST_MOVEMENT: 0
        }
        
        for region in regions:
            motion_counts[region.motion_type] += 1
        
        total_regions = len(regions)
        if total_regions == 0:
            return MotionType.STATIONARY
        
        # 判断主要运动类型
        if motion_counts[MotionType.FAST_MOVEMENT] / total_regions > 0.5:
            return MotionType.FAST_MOVEMENT
        elif motion_counts[MotionType.SLOW_MOVEMENT] / total_regions > 0.5:
            return MotionType.SLOW_MOVEMENT
        else:
            return MotionType.SLOW_MOVEMENT  # 默认
    
    def _calculate_motion_level(self, mask: np.ndarray, regions: List[MotionRegion]) -> float:
        """计算整体运动级别"""
        # 基于前景像素比例
        total_pixels = mask.shape[0] * mask.shape[1]
        motion_pixels = np.count_nonzero(mask)
        pixel_ratio = motion_pixels / total_pixels
        
        # 基于运动区域
        region_ratio = len(regions) / 10.0  # 假设最多10个区域
        
        # 综合运动级别
        motion_level = min(1.0, 0.7 * pixel_ratio + 0.3 * region_ratio)
        
        return motion_level
    
    def _update_stats(self, motion_event: MotionEvent, processing_time: float):
        """更新性能统计"""
        self.stats['total_frames_processed'] += 1
        self.stats['motion_detection_count'] += len(motion_event.regions)
        self.stats['motion_level_history'].append(motion_event.overall_motion_level)
        
        # 更新平均处理时间（指数移动平均）
        alpha = 0.1
        self.stats['average_processing_time'] = (
            alpha * processing_time + 
            (1 - alpha) * self.stats['average_processing_time']
        )
    
    def _update_working_memory(self, motion_event: MotionEvent):
        """更新工作记忆"""
        try:
            # 保存最近的运动事件
            self.working_memory.store(
                key="last_motion_event",
                value=motion_event,
                ttl=300,  # 5分钟
                priority=6
            )
            
            # 保存运动级别历史
            self.working_memory.store(
                key="motion_level_history",
                value=list(self.stats['motion_level_history']),
                ttl=600,  # 10分钟
                priority=5
            )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    def draw_motion_visualization(self, frame: np.ndarray, motion_event: MotionEvent) -> np.ndarray:
        """绘制运动可视化"""
        visualization = frame.copy()
        
        # 绘制运动区域
        for region in motion_event.regions:
            x, y, w, h = region.bbox
            
            # 根据运动类型选择颜色
            color_map = {
                MotionType.STATIONARY: (0, 0, 255),      # 红色
                MotionType.SLOW_MOVEMENT: (0, 255, 255), # 黄色
                MotionType.FAST_MOVEMENT: (0, 255, 0)    # 绿色
            }
            color = color_map.get(region.motion_type, (255, 255, 255))
            
            # 绘制边界框
            cv2.rectangle(visualization, (x, y), (x + w, y + h), color, 2)
            
            # 绘制质心
            cv2.circle(visualization, region.centroid, 5, color, -1)
            
            # 绘制轨迹
            if region.trajectory and len(region.trajectory) > 1:
                for i in range(1, len(region.trajectory)):
                    cv2.line(visualization, 
                            region.trajectory[i-1], 
                            region.trajectory[i], 
                            color, 2)
            
            # 绘制速度向量
            if region.velocity:
                dx, dy = region.velocity
                end_point = (
                    int(region.centroid[0] + dx * 5),
                    int(region.centroid[1] + dy * 5)
                )
                cv2.arrowedLine(visualization, region.centroid, end_point, color, 2)
            
            # 绘制区域信息
            info_text = f"ID:{region.region_id} {region.motion_type.value}"
            cv2.putText(visualization, info_text, 
                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制整体运动级别
        motion_text = f"Motion Level: {motion_event.overall_motion_level:.3f}"
        cv2.putText(visualization, motion_text, 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 绘制运动类型
        type_text = f"Type: {motion_event.event_type.value}"
        cv2.putText(visualization, type_text, 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return visualization
    
    def get_recent_motion_events(self, time_window: float = 60.0) -> List[MotionEvent]:
        """获取最近的运动事件"""
        current_time = time.time()
        recent_events = []
        
        for event in self.motion_events:
            if current_time - event.timestamp <= time_window:
                recent_events.append(event)
        
        return recent_events
    
    def get_motion_statistics(self, time_window: float = 60.0) -> Dict[str, Any]:
        """获取运动统计信息"""
        recent_events = self.get_recent_motion_events(time_window)
        
        if not recent_events:
            return {}
        
        motion_levels = [event.overall_motion_level for event in recent_events]
        region_counts = [len(event.regions) for event in recent_events]
        
        # 运动类型分布
        motion_type_dist = {}
        for event in recent_events:
            motion_type = event.event_type
            motion_type_dist[motion_type] = motion_type_dist.get(motion_type, 0) + 1
        
        return {
            'total_events': len(recent_events),
            'average_motion_level': np.mean(motion_levels) if motion_levels else 0,
            'max_motion_level': np.max(motion_levels) if motion_levels else 0,
            'average_region_count': np.mean(region_counts) if region_counts else 0,
            'motion_type_distribution': {k.value: v for k, v in motion_type_dist.items()},
            'time_window': time_window
        }
    
    def reset_background_model(self):
        """重置背景模型"""
        if self.background_subtractor:
            self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=16,
                detectShadows=True
            )
            self.logger.info("背景模型已重置")
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            'initialized': self.is_initialized,
            'frame_count': self.frame_count,
            'tracked_regions_count': len(self.tracked_regions),
            'stats': self.stats,
            'config': {
                'motion_threshold': self.motion_threshold,
                'min_contour_area': self.min_contour_area,
                'max_contour_area': self.max_contour_area,
                'dilation_iterations': self.dilation_iterations
            }
        }

# 全局运动检测器实例
motion_detector = MotionDetector()

