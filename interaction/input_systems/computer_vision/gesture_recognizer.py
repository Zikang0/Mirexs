"""
手势识别器 - 识别用户手势
完整的手势识别系统，支持多种手势检测和实时跟踪
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
from collections import deque

# 导入依赖
from infrastructure.compute_storage.model_serving_engine import model_serving_engine
from infrastructure.compute_storage.gpu_accelerator import gpu_accelerator
from data.models.vision.gesture_recognition import GestureRecognition
from data.models.vision.mediapipe_integration import MediaPipeIntegration
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.reasoning.state_tracker import StateTracker
from cognitive.memory.working_memory import WorkingMemory
from capabilities.system_management.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class GestureResult:
    """手势识别结果"""
    hand_id: int
    gesture: str
    gesture_zh: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]
    landmarks: List[List[float]]  # 手部关键点
    handedness: str  # 左手/右手
    all_gestures: Dict[str, float]  # 所有手势的概率分布
    timestamp: datetime

@dataclass
class GestureSequence:
    """手势序列"""
    sequence_id: str
    gestures: List[GestureResult]
    start_time: datetime
    end_time: datetime
    sequence_type: str  # 连续手势类型

class GestureRecognizer:
    """手势识别系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.gesture_model = None
        self.mediapipe_integration = None
        self.opencv_utils = OpenCVUtils()
        self.state_tracker = StateTracker()
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 手势识别配置
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.max_hands = self.config.get('max_hands', 2)
        self.enable_sequence_recognition = self.config.get('enable_sequence_recognition', True)
        self.enable_3d_estimation = self.config.get('enable_3d_estimation', False)
        
        # 手势序列跟踪
        self.gesture_sequences: Dict[int, deque] = {}  # hand_id -> gesture history
        self.sequence_window = self.config.get('sequence_window', 10)  # 序列窗口大小
        self.sequence_timeout = self.config.get('sequence_timeout', 3.0)  # 序列超时时间(秒)
        
        # 预定义手势序列
        self.defined_sequences = {
            "swipe_left": ["open_hand", "pointing", "fist"],
            "swipe_right": ["open_hand", "pointing", "fist"],
            "double_tap": ["fist", "open_hand", "fist"],
            "zoom_in": ["pinch", "open_hand"],
            "zoom_out": ["open_hand", "pinch"]
        }
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'total_gestures': 0,
            'average_confidence': 0.0,
            'processing_times': [],
            'gesture_distribution': {},
            'sequence_count': 0
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.current_session_id = None
        self.last_processing_time = 0
        
        self.logger.info("手势识别系统初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化手势识别系统"""
        try:
            # 初始化GPU加速器
            await gpu_accelerator.initialize()
            
            # 初始化模型服务引擎
            await model_serving_engine.initialize()
            
            # 加载手势识别模型
            self.gesture_model = GestureRecognition(use_gpu=True)
            if not self.gesture_model.load():
                self.logger.error("手势识别模型加载失败")
                return False
            
            # 加载MediaPipe集成
            self.mediapipe_integration = MediaPipeIntegration(use_gpu=False)  # MediaPipe通常使用CPU
            if not self.mediapipe_integration.load():
                self.logger.warning("MediaPipe集成加载失败，使用备用手势识别")
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            # 创建新会话
            self.current_session_id = f"gesture_recognition_{int(time.time())}"
            self.state_tracker.register_task(self.current_session_id, [])
            
            # 初始化手势序列跟踪
            for hand_id in range(self.max_hands):
                self.gesture_sequences[hand_id] = deque(maxlen=self.sequence_window)
            
            self.is_initialized = True
            self.logger.info("手势识别系统初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"手势识别系统初始化失败: {e}")
            return False
    
    async def process_frame(self, image: np.ndarray) -> Dict[str, Any]:
        """处理单帧图像进行手势识别"""
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
                progress=0.2,
                current_step="手部检测"
            )
            
            # 手部检测
            hand_detection_result = await self._detect_hands(image)
            if not hand_detection_result["success"]:
                return hand_detection_result
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.6,
                current_step="手势识别"
            )
            
            # 手势识别
            gesture_results = []
            for hand_data in hand_detection_result["hands"]:
                gesture_result = await self._recognize_gesture(image, hand_data)
                if gesture_result:
                    gesture_results.append(gesture_result)
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.8,
                current_step="序列分析"
            )
            
            # 手势序列分析
            sequence_results = []
            if self.enable_sequence_recognition:
                sequence_results = await self._analyze_gesture_sequences(gesture_results)
            
            # 整合结果
            final_result = self._combine_results(gesture_results, sequence_results, hand_detection_result)
            
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
            
            self.logger.debug(f"手势识别完成: 检测到 {len(final_result['gestures'])} 个手势")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"手势识别处理失败: {e}")
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "failed", 
                error_message=str(e)
            )
            return self._create_error_result(str(e))
    
    async def _detect_hands(self, image: np.ndarray) -> Dict[str, Any]:
        """手部检测"""
        try:
            # 优先使用MediaPipe进行手部检测
            if self.mediapipe_integration and hasattr(self.mediapipe_integration, 'detect_hands'):
                detection_result = self.mediapipe_integration.detect_hands(image)
            else:
                # 回退到手势识别模型的手部检测
                detection_result = self.gesture_model.recognize(image)
            
            if not detection_result.get("success", False):
                return self._create_error_result("手部检测失败")
            
            # 转换为标准格式
            hands = []
            for hand_data in detection_result.get("hands", []):
                hand = {
                    "hand_id": hand_data.get("hand_id", 0),
                    "bbox": hand_data.get("bbox", [0, 0, 0, 0]),
                    "landmarks": hand_data.get("landmarks", []),
                    "handedness": hand_data.get("handedness", "Unknown"),
                    "confidence": hand_data.get("confidence", 0.0)
                }
                hands.append(hand)
            
            return {
                "success": True,
                "hands": hands,
                "hand_count": len(hands),
                "image_size": image.shape[:2]
            }
            
        except Exception as e:
            self.logger.error(f"手部检测失败: {e}")
            return self._create_error_result(f"手部检测失败: {e}")
    
    async def _recognize_gesture(self, image: np.ndarray, hand_data: Dict) -> Optional[GestureResult]:
        """识别单个手部的手势"""
        try:
            # 提取手部区域
            bbox = hand_data["bbox"]
            hand_image = self._extract_hand_region(image, bbox)
            
            if hand_image.size == 0:
                return None
            
            # 使用手势识别模型
            recognition_result = self.gesture_model.recognize(hand_image, bbox)
            
            if not recognition_result.get("success", False):
                return None
            
            # 获取第一个手部结果（通常只有一个）
            hand_results = recognition_result.get("hands", [])
            if not hand_results:
                return None
            
            hand_result = hand_results[0]
            
            # 创建手势结果
            gesture_result = GestureResult(
                hand_id=hand_data["hand_id"],
                gesture=hand_result.get("gesture", "unknown"),
                gesture_zh=hand_result.get("gesture_zh", "未知"),
                confidence=hand_result.get("confidence", 0.0),
                bbox=bbox,
                landmarks=hand_data.get("landmarks", []),
                handedness=hand_data.get("handedness", "Unknown"),
                all_gestures=hand_result.get("all_gestures", {}),
                timestamp=datetime.now()
            )
            
            return gesture_result
            
        except Exception as e:
            self.logger.error(f"手势识别失败: {e}")
            return None
    
    async def _analyze_gesture_sequences(self, current_gestures: List[GestureResult]) -> List[GestureSequence]:
        """分析手势序列"""
        sequences = []
        current_time = datetime.now()
        
        for gesture in current_gestures:
            hand_id = gesture.hand_id
            
            # 清理过时的手势记录
            self._cleanup_old_gestures(hand_id, current_time)
            
            # 添加新手势到序列
            self.gesture_sequences[hand_id].append(gesture)
            
            # 检测手势序列
            sequence_type = self._detect_gesture_sequence(hand_id)
            if sequence_type:
                sequence = GestureSequence(
                    sequence_id=f"sequence_{hand_id}_{int(time.time())}",
                    gestures=list(self.gesture_sequences[hand_id]),
                    start_time=self.gesture_sequences[hand_id][0].timestamp,
                    end_time=current_time,
                    sequence_type=sequence_type
                )
                sequences.append(sequence)
                self.stats['sequence_count'] += 1
                
                # 清空该手部的序列
                self.gesture_sequences[hand_id].clear()
        
        return sequences
    
    def _detect_gesture_sequence(self, hand_id: int) -> Optional[str]:
        """检测预定义的手势序列"""
        gesture_history = self.gesture_sequences[hand_id]
        
        if len(gesture_history) < 2:
            return None
        
        # 将手势序列转换为名称列表
        gesture_names = [gesture.gesture for gesture in gesture_history]
        
        # 检查预定义序列
        for sequence_name, expected_sequence in self.defined_sequences.items():
            if self._matches_sequence(gesture_names, expected_sequence):
                return sequence_name
        
        return None
    
    def _matches_sequence(self, actual: List[str], expected: List[str]) -> bool:
        """检查实际序列是否匹配预期序列"""
        if len(actual) != len(expected):
            return False
        
        return all(actual[i] == expected[i] for i in range(len(actual)))
    
    def _cleanup_old_gestures(self, hand_id: int, current_time: datetime):
        """清理过时的手势记录"""
        gesture_history = self.gesture_sequences[hand_id]
        
        # 移除超过超时时间的手势
        while gesture_history:
            oldest_gesture = gesture_history[0]
            time_diff = (current_time - oldest_gesture.timestamp).total_seconds()
            
            if time_diff > self.sequence_timeout:
                gesture_history.popleft()
            else:
                break
    
    def _extract_hand_region(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """提取手部区域"""
        try:
            x1, y1, x2, y2 = bbox
            
            # 确保坐标在图像范围内
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return np.array([])
            
            hand_image = image[y1:y2, x1:x2]
            return hand_image
            
        except Exception as e:
            self.logger.error(f"提取手部区域失败: {e}")
            return np.array([])
    
    def _combine_results(self, gestures: List[GestureResult], sequences: List[GestureSequence], 
                        detection_result: Dict) -> Dict[str, Any]:
        """整合所有结果"""
        return {
            "gestures": gestures,
            "sequences": sequences,
            "hand_count": detection_result.get("hand_count", 0),
            "image_size": detection_result.get("image_size", (0, 0)),
            "timestamp": datetime.now()
        }
    
    def _update_stats(self, result: Dict[str, Any], processing_time: float):
        """更新性能统计"""
        self.stats['total_detections'] += result['hand_count']
        self.stats['total_gestures'] += len(result['gestures'])
        self.stats['processing_times'].append(processing_time)
        
        # 保持最近100次处理时间
        if len(self.stats['processing_times']) > 100:
            self.stats['processing_times'].pop(0)
        
        # 更新手势分布
        for gesture in result['gestures']:
            gesture_name = gesture.gesture
            self.stats['gesture_distribution'][gesture_name] = \
                self.stats['gesture_distribution'].get(gesture_name, 0) + 1
        
        # 计算平均置信度
        if result['gestures']:
            avg_conf = sum(gesture.confidence for gesture in result['gestures']) / len(result['gestures'])
            self.stats['average_confidence'] = 0.9 * self.stats['average_confidence'] + 0.1 * avg_conf
    
    async def _update_working_memory(self, result: Dict[str, Any]):
        """更新工作记忆"""
        try:
            # 保存识别结果
            await self.working_memory.store(
                key="last_gesture_recognition",
                value=result,
                ttl=300,  # 5分钟
                priority=7
            )
            
            # 保存重要的手势
            important_gestures = [
                gesture for gesture in result['gestures'] 
                if gesture.confidence > 0.8 and gesture.gesture != "unknown"
            ]
            
            if important_gestures:
                await self.working_memory.store(
                    key="current_gestures",
                    value=important_gestures,
                    ttl=600,  # 10分钟
                    priority=6
                )
            
            # 保存手势序列
            if result['sequences']:
                await self.working_memory.store(
                    key="recent_gesture_sequences",
                    value=result['sequences'],
                    ttl=900,  # 15分钟
                    priority=8
                )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    async def register_custom_gesture(self, gesture_name: str, gesture_sequence: List[str]) -> bool:
        """注册自定义手势序列"""
        try:
            if not gesture_name or not gesture_sequence:
                return False
            
            self.defined_sequences[gesture_name] = gesture_sequence
            
            # 保存到工作记忆
            await self.working_memory.store(
                key=f"custom_gesture_{gesture_name}",
                value=gesture_sequence,
                ttl=86400,  # 24小时
                priority=5
            )
            
            self.logger.info(f"自定义手势序列注册成功: {gesture_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"注册自定义手势失败: {e}")
            return False
    
    async def get_gesture_history(self, hand_id: int = None, time_range: float = 60.0) -> List[GestureResult]:
        """获取手势历史记录"""
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=time_range)
            
            all_gestures = []
            
            if hand_id is not None:
                # 获取特定手部的手势历史
                gesture_history = self.gesture_sequences.get(hand_id, deque())
                all_gestures = [
                    gesture for gesture in gesture_history 
                    if gesture.timestamp >= cutoff_time
                ]
            else:
                # 获取所有手部的手势历史
                for hand_gestures in self.gesture_sequences.values():
                    hand_gestures_filtered = [
                        gesture for gesture in hand_gestures 
                        if gesture.timestamp >= cutoff_time
                    ]
                    all_gestures.extend(hand_gestures_filtered)
            
            # 按时间排序
            all_gestures.sort(key=lambda x: x.timestamp)
            
            return all_gestures
            
        except Exception as e:
            self.logger.error(f"获取手势历史失败: {e}")
            return []
    
    def draw_gestures(self, image: np.ndarray, result: Dict[str, Any]) -> np.ndarray:
        """在图像上绘制手势识别结果"""
        try:
            result_image = image.copy()
            
            # 绘制手势边界框和标签
            for gesture in result.get('gestures', []):
                bbox = gesture.bbox
                gesture_name = gesture.gesture_zh
                confidence = gesture.confidence
                handedness = gesture.handedness
                
                # 绘制边界框
                color = (0, 255, 0)  # 绿色
                thickness = 2
                x1, y1, x2, y2 = map(int, bbox)
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
                
                # 绘制手势标签
                label = f"{handedness}: {gesture_name} ({confidence:.2f})"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # 标签背景
                cv2.rectangle(result_image,
                            (x1, y1 - label_size[1] - 10),
                            (x1 + label_size[0], y1),
                            color, -1)
                
                # 标签文字
                cv2.putText(result_image, label,
                          (x1, y1 - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                
                # 绘制手部关键点
                for landmark in gesture.landmarks:
                    if len(landmark) >= 2:
                        x = int(landmark[0] * image.shape[1])
                        y = int(landmark[1] * image.shape[0])
                        cv2.circle(result_image, (x, y), 3, (0, 0, 255), -1)
            
            return result_image
            
        except Exception as e:
            self.logger.error(f"绘制手势结果失败: {e}")
            return image
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "gestures": [],
            "sequences": [],
            "hand_count": 0,
            "image_size": (0, 0),
            "timestamp": datetime.now()
        }
    
    def get_gesture_statistics(self) -> Dict[str, Any]:
        """获取手势统计信息"""
        total_gestures = sum(self.stats['gesture_distribution'].values())
        gesture_percentages = {}
        
        if total_gestures > 0:
            for gesture, count in self.stats['gesture_distribution'].items():
                gesture_percentages[gesture] = (count / total_gestures) * 100
        
        return {
            "total_detections": self.stats['total_detections'],
            "total_gestures": self.stats['total_gestures'],
            "average_confidence": self.stats['average_confidence'],
            "sequence_count": self.stats['sequence_count'],
            "gesture_distribution": gesture_percentages,
            "average_processing_time": np.mean(self.stats['processing_times']) if self.stats['processing_times'] else 0,
            "defined_sequences": list(self.defined_sequences.keys())
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "confidence_threshold": self.confidence_threshold,
            "max_hands": self.max_hands,
            "enable_sequence_recognition": self.enable_sequence_recognition,
            "enable_3d_estimation": self.enable_3d_estimation,
            "sequence_window": self.sequence_window,
            "sequence_timeout": self.sequence_timeout,
            "stats": self.get_gesture_statistics()
        }

# 全局手势识别实例
gesture_recognizer = GestureRecognizer()

