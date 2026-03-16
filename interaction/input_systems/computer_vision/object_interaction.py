"""
物体交互 - 检测物体交互行为
检测用户与物体的交互行为，如抓取、放置、操作等
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
from data.models.vision.gesture_recognition import GestureRecognition
from data.models.vision.pose_estimation import PoseEstimation
from data.models.vision.mediapipe_integration import MediaPipeIntegration
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.memory.working_memory import WorkingMemory

logger = logging.getLogger(__name__)

@dataclass
class ObjectBoundingBox:
    """物体边界框"""
    object_id: str
    bbox: List[int]  # [x1, y1, x2, y2]
    class_name: str
    confidence: float
    timestamp: float

@dataclass
class HandObjectInteraction:
    """手部物体交互"""
    interaction_id: str
    hand_id: int
    object_id: str
    interaction_type: str  # grasp, release, touch, hover
    confidence: float
    timestamp: float
    hand_landmarks: List[Tuple[float, float]]
    object_bbox: List[int]

@dataclass
class InteractionEvent:
    """交互事件"""
    event_id: str
    event_type: str  # object_grasped, object_released, object_touched
    hand_id: int
    object_id: str
    timestamp: float
    duration: float  # 对于持续事件
    metadata: Dict[str, Any]

class ObjectInteractionDetector:
    """物体交互检测器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.gesture_recognizer = GestureRecognition(use_gpu=True)
        self.pose_estimator = PoseEstimation(use_gpu=True)
        self.mediapipe = MediaPipeIntegration(use_gpu=False)
        self.opencv_utils = OpenCVUtils()
        self.working_memory = WorkingMemory()
        
        # 交互检测配置
        self.interaction_threshold = self.config.get('interaction_threshold', 0.7)
        self.grasp_distance_threshold = self.config.get('grasp_distance_threshold', 0.1)
        self.touch_distance_threshold = self.config.get('touch_distance_threshold', 0.05)
        self.min_interaction_duration = self.config.get('min_interaction_duration', 0.2)
        
        # 物体跟踪
        self.tracked_objects: Dict[str, ObjectBoundingBox] = {}
        self.object_interactions: Dict[str, HandObjectInteraction] = {}
        self.interaction_history: List[InteractionEvent] = []
        
        # 性能统计
        self.stats = {
            'total_interactions_detected': 0,
            'grasp_events': 0,
            'release_events': 0,
            'touch_events': 0,
            'average_processing_time': 0.0
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.active_interactions: Dict[str, HandObjectInteraction] = {}
        
        self.logger.info("物体交互检测器初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化物体交互检测器"""
        try:
            # 加载手势识别模型
            if not self.gesture_recognizer.load():
                self.logger.error("手势识别模型加载失败")
                return False
            
            # 加载姿态估计模型
            if not self.pose_estimator.load():
                self.logger.error("姿态估计模型加载失败")
                return False
            
            # 加载MediaPipe模型
            if not self.mediapipe.load():
                self.logger.warning("MediaPipe加载失败，使用简化交互检测")
            
            self.is_initialized = True
            self.logger.info("物体交互检测器初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"物体交互检测器初始化失败: {e}")
            return False
    
    async def detect_interactions(self, image: np.ndarray, 
                                objects: List[ObjectBoundingBox],
                                hands_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """检测物体交互"""
        if not self.is_initialized:
            success = await self.initialize()
            if not success:
                return self._create_error_result("系统未初始化")
        
        start_time = time.time()
        
        try:
            # 更新跟踪的物体
            self._update_tracked_objects(objects)
            
            # 检测手部（如果未提供）
            if hands_data is None:
                hands_data = await self._detect_hands(image)
            
            # 检测交互
            interactions = await self._detect_hand_object_interactions(hands_data, image.shape)
            
            # 检测交互事件（开始、持续、结束）
            events = await self._detect_interaction_events(interactions)
            
            # 更新交互状态
            self._update_interaction_state(interactions, events)
            
            # 更新性能统计
            processing_time = time.time() - start_time
            self._update_stats(interactions, events, processing_time)
            
            # 保存到工作记忆
            await self._update_working_memory(interactions, events)
            
            result = {
                "success": True,
                "interactions": interactions,
                "events": events,
                "active_interactions": list(self.active_interactions.values()),
                "processing_time": processing_time,
                "tracked_objects_count": len(self.tracked_objects)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"物体交互检测失败: {e}")
            return self._create_error_result(str(e))
    
    async def _detect_hands(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """检测手部"""
        try:
            # 使用MediaPipe检测手部
            mp_result = self.mediapipe.detect_hands(image)
            
            hands_data = []
            if mp_result["success"]:
                for hand in mp_result.get("hands", []):
                    hand_data = {
                        "hand_id": hand["hand_id"],
                        "landmarks": hand["landmarks"],
                        "bbox": hand["bbox"],
                        "gesture": hand["gesture"],
                        "confidence": hand["confidence"],
                        "handedness": hand["handedness"]
                    }
                    hands_data.append(hand_data)
            
            # 如果MediaPipe失败，使用手势识别器
            if not hands_data:
                gesture_result = self.gesture_recognizer.recognize(image)
                if gesture_result["success"]:
                    for hand in gesture_result.get("hands", []):
                        hand_data = {
                            "hand_id": hand["hand_id"],
                            "landmarks": [],  # 手势识别器可能不提供关键点
                            "bbox": hand["bbox"],
                            "gesture": hand["gesture"],
                            "confidence": hand["confidence"],
                            "handedness": "Unknown"
                        }
                        hands_data.append(hand_data)
            
            return hands_data
            
        except Exception as e:
            self.logger.error(f"手部检测失败: {e}")
            return []
    
    def _update_tracked_objects(self, objects: List[ObjectBoundingBox]):
        """更新跟踪的物体"""
        current_time = time.time()
        
        # 移除过期的物体
        expired_objects = []
        for obj_id, obj in self.tracked_objects.items():
            if current_time - obj.timestamp > 5.0:  # 5秒未更新
                expired_objects.append(obj_id)
        
        for obj_id in expired_objects:
            del self.tracked_objects[obj_id]
        
        # 添加或更新物体
        for obj in objects:
            # 查找匹配的现有物体
            matched_obj_id = self._find_matching_object(obj)
            
            if matched_obj_id:
                # 更新现有物体
                self.tracked_objects[matched_obj_id] = obj
            else:
                # 添加新物体
                self.tracked_objects[obj.object_id] = obj
    
    def _find_matching_object(self, new_obj: ObjectBoundingBox) -> Optional[str]:
        """查找匹配的现有物体"""
        for obj_id, existing_obj in self.tracked_objects.items():
            # 计算边界框重叠度
            overlap = self._calculate_bbox_overlap(existing_obj.bbox, new_obj.bbox)
            
            # 如果重叠度足够高，认为是同一个物体
            if overlap > 0.5 and existing_obj.class_name == new_obj.class_name:
                return obj_id
        
        return None
    
    def _calculate_bbox_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
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
    
    async def _detect_hand_object_interactions(self, hands_data: List[Dict[str, Any]], 
                                             image_shape: Tuple[int, int]) -> List[HandObjectInteraction]:
        """检测手部物体交互"""
        interactions = []
        
        for hand in hands_data:
            hand_id = hand["hand_id"]
            hand_landmarks = hand["landmarks"]
            hand_bbox = hand["bbox"]
            
            # 如果没有关键点，跳过
            if not hand_landmarks:
                continue
            
            # 计算手部关键点（归一化坐标）
            normalized_landmarks = self._normalize_landmarks(hand_landmarks, image_shape)
            
            # 检测与每个物体的交互
            for obj_id, obj in self.tracked_objects.items():
                interaction = await self._detect_single_interaction(
                    hand_id, normalized_landmarks, hand_bbox, obj, image_shape
                )
                
                if interaction:
                    interactions.append(interaction)
        
        return interactions
    
    def _normalize_landmarks(self, landmarks: List[Dict[str, float]], 
                           image_shape: Tuple[int, int]) -> List[Tuple[float, float]]:
        """归一化关键点坐标"""
        normalized = []
        for landmark in landmarks:
            x = landmark['x']  # MediaPipe已经是归一化坐标
            y = landmark['y']
            normalized.append((x, y))
        return normalized
    
    async def _detect_single_interaction(self, hand_id: int, 
                                       hand_landmarks: List[Tuple[float, float]],
                                       hand_bbox: List[int],
                                       obj: ObjectBoundingBox,
                                       image_shape: Tuple[int, int]) -> Optional[HandObjectInteraction]:
        """检测单个手部与物体的交互"""
        try:
            # 计算手部与物体的距离
            min_distance, closest_point = self._calculate_hand_object_distance(
                hand_landmarks, obj.bbox, image_shape
            )
            
            # 检测交互类型
            interaction_type, confidence = self._determine_interaction_type(
                min_distance, hand_landmarks, obj
            )
            
            if interaction_type and confidence > self.interaction_threshold:
                interaction_id = f"interaction_{hand_id}_{obj.object_id}_{int(time.time())}"
                
                interaction = HandObjectInteraction(
                    interaction_id=interaction_id,
                    hand_id=hand_id,
                    object_id=obj.object_id,
                    interaction_type=interaction_type,
                    confidence=confidence,
                    timestamp=time.time(),
                    hand_landmarks=hand_landmarks,
                    object_bbox=obj.bbox
                )
                
                return interaction
            
            return None
            
        except Exception as e:
            self.logger.error(f"单次交互检测失败: {e}")
            return None
    
    def _calculate_hand_object_distance(self, hand_landmarks: List[Tuple[float, float]],
                                      obj_bbox: List[int],
                                      image_shape: Tuple[int, int]) -> Tuple[float, Tuple[float, float]]:
        """计算手部与物体的最小距离"""
        # 将边界框转换为图像坐标
        x1, y1, x2, y2 = obj_bbox
        obj_center = ((x1 + x2) / 2 / image_shape[1], (y1 + y2) / 2 / image_shape[0])
        
        # 计算手部关键点与物体中心的最小距离
        min_distance = float('inf')
        closest_point = (0, 0)
        
        for landmark in hand_landmarks:
            distance = math.sqrt(
                (landmark[0] - obj_center[0])**2 + 
                (landmark[1] - obj_center[1])**2
            )
            
            if distance < min_distance:
                min_distance = distance
                closest_point = landmark
        
        return min_distance, closest_point
    
    def _determine_interaction_type(self, distance: float, 
                                  hand_landmarks: List[Tuple[float, float]],
                                  obj: ObjectBoundingBox) -> Tuple[Optional[str], float]:
        """确定交互类型"""
        # 基于距离和手部姿态判断交互类型
        
        if distance < self.touch_distance_threshold:
            # 接触交互
            return "touch", 0.9
        
        elif distance < self.grasp_distance_threshold:
            # 抓取交互（需要进一步检查手部姿态）
            grasp_confidence = self._estimate_grasp_confidence(hand_landmarks)
            if grasp_confidence > 0.7:
                return "grasp", grasp_confidence
            else:
                return "hover", 0.8
        
        elif distance < self.grasp_distance_threshold * 2:
            # 悬停交互
            return "hover", 0.6
        
        else:
            # 无交互
            return None, 0.0
    
    def _estimate_grasp_confidence(self, hand_landmarks: List[Tuple[float, float]]) -> float:
        """估计抓取置信度"""
        if len(hand_landmarks) < 21:  # 需要完整的手部关键点
            return 0.0
        
        # 简化的抓取检测
        # 实际项目应该使用更复杂的手部姿态分析
        
        # 检查手指是否弯曲（抓取姿态）
        finger_bent_score = self._check_finger_bending(hand_landmarks)
        
        # 检查手掌方向（朝向物体）
        palm_orientation_score = self._check_palm_orientation(hand_landmarks)
        
        # 综合置信度
        confidence = (finger_bent_score + palm_orientation_score) / 2
        
        return confidence
    
    def _check_finger_bending(self, landmarks: List[Tuple[float, float]]) -> float:
        """检查手指弯曲程度"""
        if len(landmarks) < 21:
            return 0.0
        
        # 简化的手指弯曲检测
        # 实际项目应该使用更精确的算法
        
        bending_scores = []
        
        # 检查每个手指的弯曲
        finger_tips = [4, 8, 12, 16, 20]  # 拇指、食指、中指、无名指、小指指尖
        finger_mcps = [2, 5, 9, 13, 17]   # 掌指关节
        
        for tip_idx, mcp_idx in zip(finger_tips, finger_mcps):
            if tip_idx < len(landmarks) and mcp_idx < len(landmarks):
                tip = landmarks[tip_idx]
                mcp = landmarks[mcp_idx]
                
                # 计算指尖与掌指关节的距离（简化）
                distance = math.sqrt((tip[0] - mcp[0])**2 + (tip[1] - mcp[1])**2)
                
                # 距离越小，弯曲程度越高
                bending_score = max(0.0, 1.0 - distance * 5)  # 调整系数
                bending_scores.append(bending_score)
        
        return sum(bending_scores) / len(bending_scores) if bending_scores else 0.0
    
    def _check_palm_orientation(self, landmarks: List[Tuple[float, float]]) -> float:
        """检查手掌方向"""
        if len(landmarks) < 5:
            return 0.0
        
        # 简化的手掌方向检测
        # 实际项目应该使用3D方向估计
        
        # 使用手腕和手指根部计算手掌方向
        wrist = landmarks[0] if len(landmarks) > 0 else (0.5, 0.5)
        middle_mcp = landmarks[9] if len(landmarks) > 9 else (0.5, 0.5)
        
        # 计算方向向量
        dx = middle_mcp[0] - wrist[0]
        dy = middle_mcp[1] - wrist[1]
        
        # 计算方向角度
        angle = math.degrees(math.atan2(dy, dx))
        
        # 手掌朝前（指向屏幕）的置信度
        # 简化实现：假设特定角度范围表示朝前
        if -45 <= angle <= 45:
            return 0.8
        else:
            return 0.3
    
    async def _detect_interaction_events(self, interactions: List[HandObjectInteraction]) -> List[InteractionEvent]:
        """检测交互事件"""
        events = []
        current_time = time.time()
        
        # 检测新开始的交互
        for interaction in interactions:
            interaction_key = f"{interaction.hand_id}_{interaction.object_id}"
            
            if interaction_key not in self.active_interactions:
                # 新交互开始
                event_type = self._map_interaction_to_event(interaction.interaction_type, "start")
                
                event = InteractionEvent(
                    event_id=f"event_{interaction_key}_{int(current_time)}",
                    event_type=event_type,
                    hand_id=interaction.hand_id,
                    object_id=interaction.object_id,
                    timestamp=current_time,
                    duration=0.0,
                    metadata={
                        "interaction_type": interaction.interaction_type,
                        "confidence": interaction.confidence
                    }
                )
                
                events.append(event)
                self.active_interactions[interaction_key] = interaction
            
            else:
                # 更新现有交互
                existing_interaction = self.active_interactions[interaction_key]
                existing_interaction.timestamp = current_time
        
        # 检测结束的交互
        ended_interactions = []
        for interaction_key, interaction in self.active_interactions.items():
            if current_time - interaction.timestamp > self.min_interaction_duration:
                # 交互结束
                event_type = self._map_interaction_to_event(interaction.interaction_type, "end")
                
                event = InteractionEvent(
                    event_id=f"event_{interaction_key}_end_{int(current_time)}",
                    event_type=event_type,
                    hand_id=interaction.hand_id,
                    object_id=interaction.object_id,
                    timestamp=current_time,
                    duration=current_time - interaction.timestamp,
                    metadata={
                        "interaction_type": interaction.interaction_type,
                        "confidence": interaction.confidence
                    }
                )
                
                events.append(event)
                ended_interactions.append(interaction_key)
        
        # 移除结束的交互
        for key in ended_interactions:
            del self.active_interactions[key]
        
        return events
    
    def _map_interaction_to_event(self, interaction_type: str, event_action: str) -> str:
        """映射交互类型到事件类型"""
        mapping = {
            "grasp": {
                "start": "object_grasped",
                "end": "object_released"
            },
            "touch": {
                "start": "object_touched",
                "end": "touch_ended"
            },
            "hover": {
                "start": "hover_started",
                "end": "hover_ended"
            }
        }
        
        return mapping.get(interaction_type, {}).get(event_action, "interaction_unknown")
    
    def _update_interaction_state(self, interactions: List[HandObjectInteraction], 
                                events: List[InteractionEvent]):
        """更新交互状态"""
        # 更新对象交互字典
        for interaction in interactions:
            self.object_interactions[interaction.interaction_id] = interaction
        
        # 添加事件到历史
        self.interaction_history.extend(events)
        
        # 保持历史记录长度
        max_history = 100
        if len(self.interaction_history) > max_history:
            self.interaction_history = self.interaction_history[-max_history:]
    
    def _update_stats(self, interactions: List[HandObjectInteraction], 
                     events: List[InteractionEvent], processing_time: float):
        """更新性能统计"""
        self.stats['total_interactions_detected'] += len(interactions)
        
        # 统计不同类型的事件
        for event in events:
            if "grasp" in event.event_type:
                self.stats['grasp_events'] += 1
            elif "release" in event.event_type:
                self.stats['release_events'] += 1
            elif "touch" in event.event_type:
                self.stats['touch_events'] += 1
        
        # 更新平均处理时间
        alpha = 0.1
        self.stats['average_processing_time'] = (
            alpha * processing_time + 
            (1 - alpha) * self.stats['average_processing_time']
        )
    
    async def _update_working_memory(self, interactions: List[HandObjectInteraction],
                                   events: List[InteractionEvent]):
        """更新工作记忆"""
        try:
            # 保存当前交互状态
            await self.working_memory.store(
                key="current_interactions",
                value={
                    "interactions": interactions,
                    "active_interactions": list(self.active_interactions.values()),
                    "timestamp": time.time()
                },
                ttl=10,  # 10秒
                priority=7
            )
            
            # 保存重要事件
            if events:
                significant_events = [e for e in events if e.duration > 1.0 or "grasp" in e.event_type]
                
                if significant_events:
                    await self.working_memory.store(
                        key="recent_significant_events",
                        value=significant_events,
                        ttl=60,  # 1分钟
                        priority=6
                    )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    def get_interaction_summary(self) -> Dict[str, Any]:
        """获取交互摘要"""
        recent_events = self.interaction_history[-20:]  # 最近20个事件
        
        summary = {
            "total_interactions": self.stats['total_interactions_detected'],
            "active_interactions": len(self.active_interactions),
            "recent_events_count": len(recent_events),
            "event_types": {},
            "most_active_objects": self._get_most_active_objects(),
            "interaction_timeline": self._get_interaction_timeline()
        }
        
        # 统计事件类型
        for event in recent_events:
            event_type = event.event_type
            summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
        
        return summary
    
    def _get_most_active_objects(self) -> List[Dict[str, Any]]:
        """获取最活跃的物体"""
        object_activity = {}
        
        for interaction in self.object_interactions.values():
            obj_id = interaction.object_id
            object_activity[obj_id] = object_activity.get(obj_id, 0) + 1
        
        # 排序并返回前5个
        sorted_objects = sorted(object_activity.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return [
            {
                "object_id": obj_id,
                "interaction_count": count,
                "last_interaction": self._get_last_interaction_time(obj_id)
            }
            for obj_id, count in sorted_objects
        ]
    
    def _get_last_interaction_time(self, object_id: str) -> float:
        """获取物体的最后交互时间"""
        for interaction in reversed(list(self.object_interactions.values())):
            if interaction.object_id == object_id:
                return interaction.timestamp
        return 0.0
    
    def _get_interaction_timeline(self) -> List[Dict[str, Any]]:
        """获取交互时间线"""
        timeline = []
        
        for event in self.interaction_history[-10:]:  # 最近10个事件
            timeline.append({
                "event_type": event.event_type,
                "object_id": event.object_id,
                "hand_id": event.hand_id,
                "timestamp": event.timestamp,
                "duration": event.duration
            })
        
        return timeline
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "interactions": [],
            "events": [],
            "active_interactions": [],
            "processing_time": 0.0,
            "tracked_objects_count": len(self.tracked_objects)
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "tracked_objects": len(self.tracked_objects),
            "active_interactions": len(self.active_interactions),
            "interaction_history": len(self.interaction_history),
            "stats": self.stats,
            "interaction_summary": self.get_interaction_summary()
        }

# 全局物体交互检测器实例
object_interaction_detector = ObjectInteractionDetector()

