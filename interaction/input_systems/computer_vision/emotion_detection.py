"""
情绪检测 - 检测用户情绪状态
完整的情绪识别系统，支持面部情绪分析和情感状态跟踪
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
from data.models.vision.emotion_recognition import EmotionRecognition
from data.models.vision.face_detection import FaceDetection
from data.models.vision.opencv_utils import OpenCVUtils
from cognitive.reasoning.state_tracker import StateTracker
from cognitive.memory.working_memory import WorkingMemory
from capabilities.system_management.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class EmotionResult:
    """情绪检测结果"""
    face_id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    emotion: str
    emotion_zh: str
    confidence: float
    all_emotions: Dict[str, float]
    timestamp: datetime

@dataclass
class EmotionalState:
    """情感状态"""
    dominant_emotion: str
    emotion_intensity: float
    emotion_history: List[str]
    stability_score: float
    mood_trend: str  # improving, stable, declining

class EmotionDetection:
    """情绪检测系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.emotion_model = None
        self.face_detector = None
        self.opencv_utils = OpenCVUtils()
        self.state_tracker = StateTracker()
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 情绪配置
        self.emotion_labels = {
            'angry': '生气',
            'disgust': '厌恶', 
            'fear': '恐惧',
            'happy': '高兴',
            'sad': '悲伤', 
            'surprise': '惊讶',
            'neutral': '中性'
        }
        
        # 情绪跟踪
        self.emotion_history: Dict[int, deque] = {}  # face_id -> emotion history
        self.emotional_states: Dict[int, EmotionalState] = {}
        self.session_emotions: List[str] = []
        
        # 性能配置
        self.history_window = self.config.get('history_window', 30)  # 跟踪最近30个情绪
        self.confidence_threshold = self.config.get('confidence_threshold', 0.6)
        self.stability_threshold = self.config.get('stability_threshold', 0.7)
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'average_confidence': 0.0,
            'emotion_distribution': {emotion: 0 for emotion in self.emotion_labels.keys()},
            'processing_times': [],
            'session_start': datetime.now()
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.current_session_id = None
        
        self.logger.info("情绪检测系统初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化情绪检测系统"""
        try:
            # 初始化GPU加速器
            await gpu_accelerator.initialize()
            
            # 初始化模型服务引擎
            await model_serving_engine.initialize()
            
            # 加载情绪识别模型
            self.emotion_model = EmotionRecognition(use_gpu=True)
            if not self.emotion_model.load():
                self.logger.error("情绪识别模型加载失败")
                return False
            
            # 加载人脸检测模型
            self.face_detector = FaceDetection(use_gpu=True)
            if not self.face_detector.load():
                self.logger.error("人脸检测模型加载失败")
                return False
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            # 创建新会话
            self.current_session_id = f"emotion_detection_{int(time.time())}"
            self.state_tracker.register_task(self.current_session_id, [])
            
            self.is_initialized = True
            self.logger.info("情绪检测系统初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"情绪检测系统初始化失败: {e}")
            return False
    
    async def analyze_frame(self, image: np.ndarray, face_bboxes: List[List[int]] = None) -> Dict[str, Any]:
        """分析单帧图像的情绪"""
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
                current_step="人脸检测"
            )
            
            # 人脸检测（如果未提供边界框）
            if face_bboxes is None:
                detection_result = await self._detect_faces(image)
                if not detection_result["success"]:
                    return detection_result
                face_bboxes = [face["bbox"] for face in detection_result["faces"]]
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.5,
                current_step="情绪分析"
            )
            
            # 情绪分析
            emotion_results = await self._analyze_emotions(image, face_bboxes)
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.8,
                current_step="情感状态跟踪"
            )
            
            # 情感状态跟踪
            emotional_states = await self._update_emotional_states(emotion_results)
            
            # 整合结果
            final_result = self._combine_results(emotion_results, emotional_states, image.shape)
            
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
                current_step="分析完成"
            )
            
            final_result["processing_time"] = processing_time
            final_result["success"] = True
            
            self.logger.info(f"情绪分析完成: 检测到 {len(final_result['emotion_results'])} 个人脸情绪")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"情绪分析失败: {e}")
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "failed", 
                error_message=str(e)
            )
            return self._create_error_result(str(e))
    
    async def _detect_faces(self, image: np.ndarray) -> Dict[str, Any]:
        """人脸检测"""
        try:
            detection_result = self.face_detector.detect(image)
            
            if not detection_result["success"]:
                return self._create_error_result("人脸检测失败")
            
            # 转换为标准格式
            faces = []
            for i, face_data in enumerate(detection_result.get("faces", [])):
                face = {
                    "face_id": i,
                    "bbox": face_data["bbox"],
                    "confidence": face_data.get("confidence", 0.0)
                }
                faces.append(face)
            
            return {
                "success": True,
                "faces": faces,
                "face_count": len(faces),
                "image_size": image.shape[:2]
            }
            
        except Exception as e:
            self.logger.error(f"人脸检测失败: {e}")
            return self._create_error_result(f"人脸检测失败: {e}")
    
    async def _analyze_emotions(self, image: np.ndarray, face_bboxes: List[List[int]]) -> List[EmotionResult]:
        """分析情绪"""
        emotion_results = []
        
        for face_id, bbox in enumerate(face_bboxes):
            try:
                # 提取人脸区域
                face_image = self._extract_face_region(image, bbox)
                if face_image is None or face_image.size == 0:
                    continue
                
                # 情绪识别
                emotion_result = self.emotion_model.recognize(face_image, bbox)
                
                if emotion_result["success"]:
                    emotion_data = EmotionResult(
                        face_id=face_id,
                        bbox=bbox,
                        emotion=emotion_result["emotion"],
                        emotion_zh=emotion_result["emotion_zh"],
                        confidence=emotion_result["confidence"],
                        all_emotions=emotion_result["all_emotions"],
                        timestamp=datetime.now()
                    )
                    emotion_results.append(emotion_data)
                    
                    # 更新情绪历史
                    self._update_emotion_history(face_id, emotion_result["emotion"])
                
            except Exception as e:
                self.logger.error(f"人脸 {face_id} 情绪分析失败: {e}")
                continue
        
        return emotion_results
    
    def _extract_face_region(self, image: np.ndarray, bbox: List[int]) -> Optional[np.ndarray]:
        """提取人脸区域"""
        try:
            x1, y1, x2, y2 = bbox
            
            # 确保坐标在图像范围内
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            face_region = image[y1:y2, x1:x2]
            return face_region
            
        except Exception as e:
            self.logger.error(f"提取人脸区域失败: {e}")
            return None
    
    def _update_emotion_history(self, face_id: int, emotion: str):
        """更新情绪历史"""
        if face_id not in self.emotion_history:
            self.emotion_history[face_id] = deque(maxlen=self.history_window)
        
        self.emotion_history[face_id].append(emotion)
        
        # 更新会话情绪记录
        self.session_emotions.append(emotion)
        if len(self.session_emotions) > 100:  # 限制会话记录大小
            self.session_emotions.pop(0)
    
    async def _update_emotional_states(self, emotion_results: List[EmotionResult]) -> Dict[int, EmotionalState]:
        """更新情感状态"""
        emotional_states = {}
        
        for result in emotion_results:
            face_id = result.face_id
            
            if face_id not in self.emotion_history:
                continue
            
            emotion_list = list(self.emotion_history[face_id])
            if not emotion_list:
                continue
            
            # 计算主导情绪
            emotion_counts = {}
            for emotion in emotion_list:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            
            # 计算情绪强度（基于置信度和稳定性）
            emotion_intensity = result.confidence
            
            # 计算稳定性分数
            stability_score = self._calculate_emotion_stability(emotion_list)
            
            # 判断情绪趋势
            mood_trend = self._analyze_mood_trend(emotion_list)
            
            emotional_state = EmotionalState(
                dominant_emotion=dominant_emotion,
                emotion_intensity=emotion_intensity,
                emotion_history=emotion_list[-10:],  # 最近10次情绪
                stability_score=stability_score,
                mood_trend=mood_trend
            )
            
            emotional_states[face_id] = emotional_state
        
        return emotional_states
    
    def _calculate_emotion_stability(self, emotion_list: List[str]) -> float:
        """计算情绪稳定性"""
        if len(emotion_list) < 2:
            return 1.0
        
        changes = 0
        for i in range(1, len(emotion_list)):
            if emotion_list[i] != emotion_list[i-1]:
                changes += 1
        
        stability = 1.0 - (changes / (len(emotion_list) - 1))
        return stability
    
    def _analyze_mood_trend(self, emotion_list: List[str]) -> str:
        """分析情绪趋势"""
        if len(emotion_list) < 3:
            return "stable"
        
        # 情绪价值映射（正值为积极情绪，负值为消极情绪）
        emotion_values = {
            'happy': 2,
            'surprise': 1,
            'neutral': 0,
            'sad': -1,
            'fear': -1,
            'angry': -2,
            'disgust': -2
        }
        
        # 计算最近的情绪变化
        recent = emotion_list[-5:] if len(emotion_list) >= 5 else emotion_list
        values = [emotion_values.get(emotion, 0) for emotion in recent]
        
        # 计算趋势（简单线性回归）
        n = len(values)
        if n < 2:
            return "stable"
        
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _combine_results(self, emotion_results: List[EmotionResult], 
                        emotional_states: Dict[int, EmotionalState],
                        image_size: Tuple[int, int]) -> Dict[str, Any]:
        """整合结果"""
        return {
            "emotion_results": emotion_results,
            "emotional_states": emotional_states,
            "session_summary": self._get_session_summary(),
            "image_size": image_size,
            "timestamp": datetime.now()
        }
    
    def _get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要"""
        if not self.session_emotions:
            return {}
        
        # 情绪分布
        emotion_dist = {}
        for emotion in self.session_emotions:
            emotion_dist[emotion] = emotion_dist.get(emotion, 0) + 1
        
        total = len(self.session_emotions)
        for emotion in emotion_dist:
            emotion_dist[emotion] = emotion_dist[emotion] / total
        
        # 会话时长
        session_duration = (datetime.now() - self.stats['session_start']).total_seconds()
        
        return {
            "total_emotions_detected": total,
            "emotion_distribution": emotion_dist,
            "session_duration_seconds": session_duration,
            "average_confidence": self.stats['average_confidence']
        }
    
    def _update_stats(self, result: Dict[str, Any], processing_time: float):
        """更新性能统计"""
        emotion_count = len(result['emotion_results'])
        self.stats['total_detections'] += emotion_count
        self.stats['processing_times'].append(processing_time)
        
        # 保持最近100次处理时间
        if len(self.stats['processing_times']) > 100:
            self.stats['processing_times'].pop(0)
        
        # 更新情绪分布
        for emotion_result in result['emotion_results']:
            emotion = emotion_result.emotion
            self.stats['emotion_distribution'][emotion] += 1
        
        # 计算平均置信度
        if emotion_count > 0:
            avg_conf = sum(er.confidence for er in result['emotion_results']) / emotion_count
            self.stats['average_confidence'] = 0.9 * self.stats['average_confidence'] + 0.1 * avg_conf
    
    async def _update_working_memory(self, result: Dict[str, Any]):
        """更新工作记忆"""
        try:
            # 保存情绪分析结果
            await self.working_memory.store(
                key="last_emotion_analysis",
                value=result,
                ttl=300,  # 5分钟
                priority=7
            )
            
            # 保存当前情感状态
            if result['emotional_states']:
                await self.working_memory.store(
                    key="current_emotional_states",
                    value=result['emotional_states'],
                    ttl=600,  # 10分钟
                    priority=6
                )
            
            # 保存会话摘要
            await self.working_memory.store(
                key="emotion_session_summary",
                value=result['session_summary'],
                ttl=1800,  # 30分钟
                priority=5
            )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    async def analyze_video_emotions(self, video_path: str, interval: float = 1.0) -> Dict[str, Any]:
        """分析视频中的情绪变化"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"success": False, "error": "无法打开视频文件"}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * interval)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            emotions_over_time = []
            frame_count = 0
            analysis_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 按间隔处理帧
                if frame_count % frame_interval == 0:
                    analysis_result = await self.analyze_frame(frame)
                    
                    if analysis_result['success']:
                        for emotion_result in analysis_result['emotion_results']:
                            emotions_over_time.append({
                                'frame': frame_count,
                                'time': frame_count / fps,
                                'face_id': emotion_result.face_id,
                                'emotion': emotion_result.emotion,
                                'confidence': emotion_result.confidence,
                                'emotion_zh': emotion_result.emotion_zh
                            })
                        
                        analysis_count += 1
                
                frame_count += 1
            
            cap.release()
            
            # 分析情绪变化趋势
            emotion_trends = self._analyze_emotion_trends(emotions_over_time)
            
            return {
                "success": True,
                "total_frames": frame_count,
                "analyzed_frames": analysis_count,
                "duration": frame_count / fps,
                "emotions_over_time": emotions_over_time,
                "emotion_trends": emotion_trends
            }
            
        except Exception as e:
            self.logger.error(f"视频情绪分析失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_emotion_trends(self, emotions_over_time: List[Dict]) -> Dict[str, Any]:
        """分析情绪变化趋势"""
        if not emotions_over_time:
            return {}
        
        # 按时间窗口分析情绪变化
        time_windows = []
        window_size = 10  # 10个情绪样本一个窗口
        
        for i in range(0, len(emotions_over_time), window_size):
            window = emotions_over_time[i:i+window_size]
            if not window:
                continue
            
            # 计算窗口内的主导情绪
            emotion_counts = {}
            for item in window:
                emotion_counts[item['emotion']] = emotion_counts.get(item['emotion'], 0) + 1
            
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
            
            time_windows.append({
                'start_time': window[0]['time'],
                'end_time': window[-1]['time'],
                'dominant_emotion': dominant_emotion,
                'emotion_distribution': emotion_counts
            })
        
        # 分析情绪转换模式
        emotion_transitions = {}
        for i in range(1, len(emotions_over_time)):
            prev_emotion = emotions_over_time[i-1]['emotion']
            curr_emotion = emotions_over_time[i]['emotion']
            
            if prev_emotion != curr_emotion:
                transition = f"{prev_emotion}->{curr_emotion}"
                emotion_transitions[transition] = emotion_transitions.get(transition, 0) + 1
        
        return {
            "time_windows": time_windows,
            "emotion_transitions": emotion_transitions,
            "total_transitions": sum(emotion_transitions.values())
        }
    
    def get_emotion_insights(self) -> Dict[str, Any]:
        """获取情绪洞察"""
        if not self.session_emotions:
            return {}
        
        # 计算情绪稳定性
        stability = self._calculate_emotion_stability(self.session_emotions)
        
        # 情绪多样性
        unique_emotions = len(set(self.session_emotions))
        emotion_diversity = unique_emotions / len(self.emotion_labels)
        
        # 积极情绪比例
        positive_emotions = ['happy', 'surprise']
        positive_count = sum(1 for emotion in self.session_emotions if emotion in positive_emotions)
        positive_ratio = positive_count / len(self.session_emotions) if self.session_emotions else 0
        
        return {
            "emotion_stability": stability,
            "emotion_diversity": emotion_diversity,
            "positive_emotion_ratio": positive_ratio,
            "most_frequent_emotion": max(set(self.session_emotions), key=self.session_emotions.count) if self.session_emotions else "unknown",
            "session_duration": (datetime.now() - self.stats['session_start']).total_seconds()
        }
    
    def reset_session(self):
        """重置会话"""
        self.session_emotions.clear()
        self.emotion_history.clear()
        self.emotional_states.clear()
        self.stats['session_start'] = datetime.now()
        self.logger.info("情绪检测会话已重置")
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "emotion_results": [],
            "emotional_states": {},
            "session_summary": {},
            "image_size": (0, 0)
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "emotion_labels": self.emotion_labels,
            "confidence_threshold": self.confidence_threshold,
            "history_window": self.history_window,
            "stats": self.stats,
            "session_insights": self.get_emotion_insights()
        }

# 全局情绪检测实例
emotion_detection_system = EmotionDetection()

