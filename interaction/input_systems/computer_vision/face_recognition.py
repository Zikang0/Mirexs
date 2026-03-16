"""
人脸识别 - 识别用户身份
完整的人脸识别系统，支持多个人脸检测和身份识别
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

# 导入依赖
from infrastructure.compute_storage.model_serving_engine import model_serving_engine
from infrastructure.compute_storage.gpu_accelerator import gpu_accelerator
from data.models.vision.face_detection import FaceDetection
from data.models.vision.insightface_integration import InsightFaceIntegration
from cognitive.reasoning.state_tracker import StateTracker
from cognitive.memory.working_memory import WorkingMemory
from capabilities.system_management.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

@dataclass
class FaceRecognitionResult:
    """人脸识别结果"""
    face_id: int
    bbox: List[int]  # [x1, y1, x2, y2]
    confidence: float
    identity: str
    identity_confidence: float
    embedding: np.ndarray
    landmarks: List[List[float]]
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None

@dataclass
class FaceDatabaseEntry:
    """人脸数据库条目"""
    name: str
    embedding: np.ndarray
    sample_images: List[np.ndarray]
    registration_time: datetime
    last_seen: datetime
    access_count: int = 0

class FaceRecognition:
    """人脸识别系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.face_detector = None
        self.face_recognizer = None
        self.state_tracker = StateTracker()
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 人脸数据库
        self.face_database: Dict[str, FaceDatabaseEntry] = {}
        self.unknown_faces: Dict[str, List[np.ndarray]] = {}
        
        # 识别配置
        self.recognition_threshold = self.config.get('recognition_threshold', 0.6)
        self.max_faces = self.config.get('max_faces', 10)
        self.enable_age_gender = self.config.get('enable_age_gender', True)
        self.enable_emotion = self.config.get('enable_emotion', True)
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'total_recognitions': 0,
            'average_confidence': 0.0,
            'processing_times': [],
            'database_size': 0
        }
        
        # 状态跟踪
        self.is_initialized = False
        self.current_session_id = None
        
        self.logger.info("人脸识别系统初始化开始...")
    
    async def initialize(self) -> bool:
        """初始化人脸识别系统"""
        try:
            # 初始化GPU加速器
            await gpu_accelerator.initialize()
            
            # 初始化模型服务引擎
            await model_serving_engine.initialize()
            
            # 加载人脸检测模型
            self.face_detector = FaceDetection(use_gpu=True)
            if not self.face_detector.load():
                self.logger.error("人脸检测模型加载失败")
                return False
            
            # 加载人脸识别模型
            self.face_recognizer = InsightFaceIntegration(use_gpu=True)
            if not self.face_recognizer.load():
                self.logger.error("人脸识别模型加载失败")
                return False
            
            # 加载人脸数据库
            await self._load_face_database()
            
            # 启动性能监控
            self.performance_monitor.start_monitoring()
            
            # 创建新会话
            self.current_session_id = f"face_recognition_{int(time.time())}"
            self.state_tracker.register_task(self.current_session_id, [])
            
            self.is_initialized = True
            self.logger.info("人脸识别系统初始化完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"人脸识别系统初始化失败: {e}")
            return False
    
    async def process_frame(self, image: np.ndarray) -> Dict[str, Any]:
        """处理单帧图像进行人脸识别"""
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
                current_step="人脸检测"
            )
            
            # 人脸检测
            detection_result = await self._detect_faces(image)
            if not detection_result["success"]:
                return detection_result
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.6,
                current_step="人脸识别"
            )
            
            # 人脸识别
            recognition_result = await self._recognize_faces(image, detection_result["faces"])
            
            # 更新状态
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "running", 
                progress=0.9,
                current_step="结果整合"
            )
            
            # 整合结果
            final_result = self._combine_results(detection_result, recognition_result)
            
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
            
            self.logger.info(f"人脸识别完成: 检测到 {len(final_result['recognized_faces'])} 个人脸")
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"人脸识别处理失败: {e}")
            self.state_tracker.update_task_state(
                self.current_session_id, 
                "failed", 
                error_message=str(e)
            )
            return self._create_error_result(str(e))
    
    async def _detect_faces(self, image: np.ndarray) -> Dict[str, Any]:
        """人脸检测"""
        try:
            # 使用InsightFace进行人脸检测
            detection_result = self.face_recognizer.detect_faces(image)
            
            if not detection_result["success"]:
                # 回退到基础人脸检测
                detection_result = self.face_detector.detect(image)
            
            # 转换为标准格式
            faces = []
            for i, face_data in enumerate(detection_result.get("faces", [])):
                face = {
                    "face_id": i,
                    "bbox": face_data["bbox"],
                    "confidence": face_data.get("confidence", 0.0),
                    "landmarks": face_data.get("landmarks", []),
                    "embedding": np.array(face_data.get("embedding", [])),
                    "age": face_data.get("age"),
                    "gender": face_data.get("gender")
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
    
    async def _recognize_faces(self, image: np.ndarray, faces: List[Dict]) -> Dict[str, Any]:
        """人脸识别"""
        try:
            recognized_faces = []
            unknown_faces = []
            
            for face in faces:
                embedding = face["embedding"]
                
                if embedding.size == 0:
                    # 如果没有嵌入向量，标记为未知
                    unknown_face = face.copy()
                    unknown_face["identity"] = "unknown"
                    unknown_faces.append(unknown_face)
                    continue
                
                # 在数据库中查找匹配的人脸
                best_match = None
                best_similarity = 0.0
                
                for name, db_entry in self.face_database.items():
                    similarity = self._cosine_similarity(embedding, db_entry.embedding)
                    
                    if similarity > best_similarity and similarity > self.recognition_threshold:
                        best_similarity = similarity
                        best_match = name
                
                if best_match:
                    # 已知人脸
                    recognized_face = face.copy()
                    recognized_face["identity"] = best_match
                    recognized_face["identity_confidence"] = best_similarity
                    
                    # 更新数据库访问记录
                    self.face_database[best_match].last_seen = datetime.now()
                    self.face_database[best_match].access_count += 1
                    
                    recognized_faces.append(recognized_face)
                else:
                    # 未知人脸
                    unknown_face = face.copy()
                    unknown_face["identity"] = "unknown"
                    unknown_faces.append(unknown_face)
                    
                    # 保存未知人脸样本
                    await self._save_unknown_face(unknown_face, image)
            
            return {
                "success": True,
                "recognized_faces": recognized_faces,
                "unknown_faces": unknown_faces
            }
            
        except Exception as e:
            self.logger.error(f"人脸识别失败: {e}")
            return self._create_error_result(f"人脸识别失败: {e}")
    
    def _combine_results(self, detection_result: Dict, recognition_result: Dict) -> Dict[str, Any]:
        """整合检测和识别结果"""
        combined_faces = []
        
        # 处理识别到的人脸
        for rec_face in recognition_result.get("recognized_faces", []):
            combined_face = FaceRecognitionResult(
                face_id=rec_face["face_id"],
                bbox=rec_face["bbox"],
                confidence=rec_face["confidence"],
                identity=rec_face["identity"],
                identity_confidence=rec_face["identity_confidence"],
                embedding=rec_face["embedding"],
                landmarks=rec_face.get("landmarks", []),
                age=rec_face.get("age"),
                gender=rec_face.get("gender")
            )
            combined_faces.append(combined_face)
        
        # 处理未知人脸
        for unknown_face in recognition_result.get("unknown_faces", []):
            combined_face = FaceRecognitionResult(
                face_id=unknown_face["face_id"],
                bbox=unknown_face["bbox"],
                confidence=unknown_face["confidence"],
                identity="unknown",
                identity_confidence=0.0,
                embedding=unknown_face["embedding"],
                landmarks=unknown_face.get("landmarks", []),
                age=unknown_face.get("age"),
                gender=unknown_face.get("gender")
            )
            combined_faces.append(combined_face)
        
        return {
            "faces": combined_faces,
            "recognized_count": len(recognition_result.get("recognized_faces", [])),
            "unknown_count": len(recognition_result.get("unknown_faces", [])),
            "total_faces": len(combined_faces),
            "image_size": detection_result.get("image_size", (0, 0))
        }
    
    async def register_face(self, name: str, image: np.ndarray, face_bbox: List[int] = None) -> Dict[str, Any]:
        """注册新人脸到数据库"""
        try:
            if not self.is_initialized:
                return self._create_error_result("系统未初始化")
            
            # 检测人脸
            detection_result = await self._detect_faces(image)
            if not detection_result["success"] or detection_result["face_count"] == 0:
                return self._create_error_result("未检测到人脸")
            
            # 使用指定的人脸或第一个检测到的人脸
            if face_bbox is None:
                target_face = detection_result["faces"][0]
            else:
                # 查找匹配的人脸
                target_face = None
                for face in detection_result["faces"]:
                    if self._bbox_overlap(face["bbox"], face_bbox) > 0.7:
                        target_face = face
                        break
                
                if target_face is None:
                    return self._create_error_result("未找到指定的人脸")
            
            # 提取人脸嵌入
            embedding = target_face["embedding"]
            if embedding.size == 0:
                return self._create_error_result("无法提取人脸特征")
            
            # 裁剪人脸图像
            x1, y1, x2, y2 = target_face["bbox"]
            face_image = image[y1:y2, x1:x2]
            
            # 保存到数据库
            db_entry = FaceDatabaseEntry(
                name=name,
                embedding=embedding,
                sample_images=[face_image],
                registration_time=datetime.now(),
                last_seen=datetime.now()
            )
            
            self.face_database[name] = db_entry
            self.stats['database_size'] = len(self.face_database)
            
            # 保存数据库
            await self._save_face_database()
            
            self.logger.info(f"新人脸注册成功: {name}")
            
            return {
                "success": True,
                "name": name,
                "embedding_size": len(embedding),
                "face_image_size": face_image.shape[:2],
                "database_size": len(self.face_database)
            }
            
        except Exception as e:
            self.logger.error(f"人脸注册失败: {e}")
            return self._create_error_result(f"人脸注册失败: {e}")
    
    async def _save_unknown_face(self, face_data: Dict, original_image: np.ndarray):
        """保存未知人脸样本"""
        try:
            face_id = f"unknown_{int(time.time())}_{face_data['face_id']}"
            
            # 裁剪人脸区域
            x1, y1, x2, y2 = face_data["bbox"]
            face_image = original_image[y1:y2, x1:x2]
            
            # 保存到工作记忆
            await self.working_memory.store(
                key=f"unknown_face_{face_id}",
                value={
                    "face_data": face_data,
                    "face_image": face_image,
                    "timestamp": datetime.now()
                },
                ttl=3600,  # 1小时
                priority=5
            )
            
            self.logger.debug(f"未知人脸已保存: {face_id}")
            
        except Exception as e:
            self.logger.error(f"保存未知人脸失败: {e}")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _bbox_overlap(self, bbox1: List[int], bbox2: List[int]) -> float:
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
    
    def _update_stats(self, result: Dict[str, Any], processing_time: float):
        """更新性能统计"""
        self.stats['total_detections'] += result['total_faces']
        self.stats['total_recognitions'] += result['recognized_count']
        self.stats['processing_times'].append(processing_time)
        
        # 保持最近100次处理时间
        if len(self.stats['processing_times']) > 100:
            self.stats['processing_times'].pop(0)
        
        # 计算平均置信度
        if result['faces']:
            avg_conf = sum(face.confidence for face in result['faces']) / len(result['faces'])
            self.stats['average_confidence'] = 0.9 * self.stats['average_confidence'] + 0.1 * avg_conf
    
    async def _update_working_memory(self, result: Dict[str, Any]):
        """更新工作记忆"""
        try:
            # 保存识别结果
            await self.working_memory.store(
                key="last_face_recognition",
                value=result,
                ttl=300,  # 5分钟
                priority=8
            )
            
            # 保存已知人脸信息
            known_faces = [face for face in result['faces'] if face.identity != "unknown"]
            if known_faces:
                await self.working_memory.store(
                    key="current_known_faces",
                    value=known_faces,
                    ttl=600,  # 10分钟
                    priority=7
                )
            
        except Exception as e:
            self.logger.error(f"更新工作记忆失败: {e}")
    
    async def _load_face_database(self):
        """加载人脸数据库"""
        try:
            # 这里应该从文件或数据库加载
            # 目前使用空数据库
            self.face_database = {}
            self.stats['database_size'] = 0
            self.logger.info("人脸数据库加载完成")
            
        except Exception as e:
            self.logger.error(f"加载人脸数据库失败: {e}")
    
    async def _save_face_database(self):
        """保存人脸数据库"""
        try:
            # 这里应该保存到文件或数据库
            # 目前仅记录日志
            self.logger.info(f"人脸数据库已更新，当前大小: {len(self.face_database)}")
            
        except Exception as e:
            self.logger.error(f"保存人脸数据库失败: {e}")
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "error": error_message,
            "faces": [],
            "recognized_count": 0,
            "unknown_count": 0,
            "total_faces": 0,
            "image_size": (0, 0)
        }
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        return {
            "total_faces": len(self.face_database),
            "known_identities": list(self.face_database.keys()),
            "database_size": self.stats['database_size'],
            "stats": self.stats
        }
    
    def clear_database(self) -> Dict[str, Any]:
        """清空人脸数据库"""
        count = len(self.face_database)
        self.face_database.clear()
        self.stats['database_size'] = 0
        
        return {
            "success": True,
            "cleared_faces": count,
            "message": f"已清空 {count} 个人脸记录"
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "initialized": self.is_initialized,
            "recognition_threshold": self.recognition_threshold,
            "max_faces": self.max_faces,
            "enable_age_gender": self.enable_age_gender,
            "enable_emotion": self.enable_emotion,
            "stats": self.stats,
            "database_info": self.get_database_info()
        }

# 全局人脸识别实例
face_recognition_system = FaceRecognition()
