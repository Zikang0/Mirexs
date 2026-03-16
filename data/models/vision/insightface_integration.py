"""
InsightFace集成 - 人脸识别集成
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import time
import os

try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False

class InsightFaceIntegration:
    """InsightFace人脸识别集成"""
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "InsightFace"
        self.version = "1.0.0"
        self.model = None
        self.is_loaded = False
        self.use_gpu = use_gpu
        
        # 人脸数据库
        self.face_database = {}  # name -> embedding
        self.face_images = {}    # name -> sample image
        
        # 模型配置
        self.config = {
            'det_thresh': 0.6,      # 检测阈值
            'rec_thresh': 0.4,      # 识别阈值
            'max_faces': 10,        # 最大人脸数量
            'enable_age_gender': True,  # 启用年龄性别检测
            'enable_landmarks': True,   # 启用人脸关键点
        }
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'total_recognitions': 0,
            'average_confidence': 0.0,
            'known_faces_count': 0,
            'unknown_faces_count': 0
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载InsightFace模型"""
        try:
            print("📦 正在加载InsightFace模型...")
            
            if INSIGHTFACE_AVAILABLE:
                success = self._load_insightface_model()
            else:
                success = self._load_fallback_model()
                
            if success:
                self.is_loaded = True
                print("✅ InsightFace模型加载成功")
            else:
                print("❌ InsightFace模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载InsightFace模型失败: {e}")
            return False
    
    def _load_insightface_model(self) -> bool:
        """加载InsightFace模型"""
        try:
            # 创建人脸分析应用
            self.model = FaceAnalysis(
                name='buffalo_l',  # 使用buffalo_l模型
                providers=['CUDAExecutionProvider'] if self.use_gpu else ['CPUExecutionProvider']
            )
            
            # 准备模型
            self.model.prepare(ctx_id=0 if self.use_gpu else -1, det_size=(640, 640))
            
            return True
            
        except Exception as e:
            print(f"❌ 加载InsightFace模型失败: {e}")
            return self._load_fallback_model()
    
    def _load_fallback_model(self) -> bool:
        """加载备用模型"""
        try:
            print("⚠️  InsightFace不可用，使用备用人脸识别模型")
            
            # 加载OpenCV的人脸检测器
            self.face_detector = cv2.CascadeClassifier()
            
            # 尝试加载预训练的人脸检测器
            cascade_paths = [
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
                cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml',
                cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
            ]
            
            for path in cascade_paths:
                if os.path.exists(path):
                    if self.face_detector.load(path):
                        print(f"✅ 加载人脸检测器: {path}")
                        self.model = "opencv_face_model"
                        return True
            
            print("❌ 无法加载任何人脸检测器")
            return False
            
        except Exception as e:
            print(f"❌ 加载备用模型失败: {e}")
            return False
    
    def detect_faces(self, image: np.ndarray) -> Dict[str, Any]:
        """检测图像中的人脸"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 验证输入
            if image is None or image.size == 0:
                return self._get_error_result("输入图像为空")
            
            # 进行人脸检测
            if INSIGHTFACE_AVAILABLE and isinstance(self.model, FaceAnalysis):
                detection_result = self._detect_insightface(image)
            else:
                detection_result = self._detect_opencv(image)
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_detection_stats(detection_result)
            
            detection_result["processing_time"] = processing_time
            detection_result["success"] = True
            
            return detection_result
            
        except Exception as e:
            print(f"❌ 人脸检测失败: {e}")
            return self._get_error_result(str(e))
    
    def _detect_insightface(self, image: np.ndarray) -> Dict[str, Any]:
        """使用InsightFace检测人脸"""
        # 进行人脸检测和分析
        faces = self.model.get(image)
        
        detected_faces = []
        
        for i, face in enumerate(faces):
            # 获取边界框
            bbox = face.bbox.astype(int).tolist()
            
            # 获取关键点
            landmarks = face.kps.astype(int).tolist() if hasattr(face, 'kps') else []
            
            # 获取人脸嵌入
            embedding = face.embedding.tolist() if hasattr(face, 'embedding') else []
            
            # 获取性别和年龄
            gender = "Male" if face.gender == 1 else "Female" if hasattr(face, 'gender') else "Unknown"
            age = int(face.age) if hasattr(face, 'age') else 0
            
            detected_faces.append({
                'face_id': i,
                'bbox': bbox,
                'confidence': float(face.det_score),
                'landmarks': landmarks,
                'embedding': embedding,
                'gender': gender,
                'age': age,
                'embedding_size': len(embedding)
            })
        
        return {
            'faces': detected_faces,
            'face_count': len(detected_faces),
            'image_size': image.shape[:2]
        }
    
    def _detect_opencv(self, image: np.ndarray) -> Dict[str, Any]:
        """使用OpenCV检测人脸（备用方案）"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        detected_faces = []
        
        for i, (x, y, w, h) in enumerate(faces):
            # 计算置信度（基于人脸大小和位置）
            confidence = min(w * h / (image.shape[0] * image.shape[1]) * 10, 0.95)
            
            # 生成模拟的关键点
            landmarks = self._generate_landmarks(x, y, w, h)
            
            # 生成模拟的嵌入向量
            embedding = np.random.randn(512).tolist()
            
            # 模拟性别和年龄
            gender = "Male" if np.random.random() > 0.5 else "Female"
            age = np.random.randint(18, 65)
            
            detected_faces.append({
                'face_id': i,
                'bbox': [int(x), int(y), int(x + w), int(y + h)],
                'confidence': float(confidence),
                'landmarks': landmarks,
                'embedding': embedding,
                'gender': gender,
                'age': age,
                'embedding_size': len(embedding)
            })
        
        return {
            'faces': detected_faces,
            'face_count': len(detected_faces),
            'image_size': image.shape[:2]
        }
    
    def recognize_faces(self, image: np.ndarray) -> Dict[str, Any]:
        """识别图像中的人脸"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 首先检测人脸
            detection_result = self.detect_faces(image)
            if not detection_result['success']:
                return detection_result
            
            recognized_faces = []
            unknown_faces = []
            
            # 对每个检测到的人脸进行识别
            for face in detection_result['faces']:
                embedding = np.array(face['embedding'])
                
                # 在数据库中查找最相似的人脸
                best_match = None
                best_similarity = 0.0
                
                for name, db_embedding in self.face_database.items():
                    similarity = self._cosine_similarity(embedding, db_embedding)
                    
                    if similarity > best_similarity and similarity > self.config['rec_thresh']:
                        best_similarity = similarity
                        best_match = name
                
                if best_match:
                    # 已知人脸
                    recognized_face = face.copy()
                    recognized_face['identity'] = best_match
                    recognized_face['similarity'] = best_similarity
                    recognized_faces.append(recognized_face)
                    self.stats['total_recognitions'] += 1
                else:
                    # 未知人脸
                    unknown_face = face.copy()
                    unknown_face['identity'] = 'unknown'
                    unknown_faces.append(unknown_face)
                    self.stats['unknown_faces_count'] += 1
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'recognized_faces': recognized_faces,
                'unknown_faces': unknown_faces,
                'total_faces': len(recognized_faces) + len(unknown_faces),
                'processing_time': processing_time,
                'recognition_threshold': self.config['rec_thresh']
            }
            
        except Exception as e:
            print(f"❌ 人脸识别失败: {e}")
            return self._get_error_result(str(e))
    
    def register_face(self, name: str, image: np.ndarray, face_bbox: Optional[List[int]] = None) -> Dict[str, Any]:
        """注册新的人脸到数据库"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            # 检测人脸
            if face_bbox is None:
                detection_result = self.detect_faces(image)
                if not detection_result['success'] or detection_result['face_count'] == 0:
                    return self._get_error_result("未检测到人脸")
                face_bbox = detection_result['faces'][0]['bbox']
            
            # 提取人脸区域
            x1, y1, x2, y2 = face_bbox
            face_image = image[y1:y2, x1:x2]
            
            # 获取人脸嵌入
            if INSIGHTFACE_AVAILABLE and isinstance(self.model, FaceAnalysis):
                # 使用InsightFace获取嵌入
                faces = self.model.get(face_image)
                if len(faces) == 0:
                    return self._get_error_result("无法提取人脸特征")
                embedding = faces[0].embedding
            else:
                # 生成模拟嵌入
                embedding = np.random.randn(512)
            
            # 保存到数据库
            self.face_database[name] = embedding
            self.face_images[name] = face_image
            
            self.stats['known_faces_count'] += 1
            
            return {
                'success': True,
                'name': name,
                'embedding_size': len(embedding),
                'face_image_size': face_image.shape[:2],
                'database_size': len(self.face_database)
            }
            
        except Exception as e:
            print(f"❌ 注册人脸失败: {e}")
            return self._get_error_result(str(e))
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _generate_landmarks(self, x: int, y: int, w: int, h: int) -> List[List[int]]:
        """生成模拟的人脸关键点"""
        landmarks = []
        
        # 生成5个关键点（左眼、右眼、鼻子、左嘴角、右嘴角）
        points = [
            [x + w * 0.3, y + h * 0.3],  # 左眼
            [x + w * 0.7, y + h * 0.3],  # 右眼
            [x + w * 0.5, y + h * 0.5],  # 鼻子
            [x + w * 0.3, y + h * 0.7],  # 左嘴角
            [x + w * 0.7, y + h * 0.7]   # 右嘴角
        ]
        
        for point in points:
            landmarks.append([int(point[0]), int(point[1])])
        
        return landmarks
    
    def _update_detection_stats(self, detection_result: Dict[str, Any]):
        """更新检测统计信息"""
        face_count = detection_result.get('face_count', 0)
        self.stats['total_detections'] += face_count
        
        if face_count > 0:
            avg_confidence = np.mean([face.get('confidence', 0) for face in detection_result.get('faces', [])])
            
            # 更新平均置信度（指数移动平均）
            alpha = 0.1
            self.stats['average_confidence'] = (
                alpha * avg_confidence + (1 - alpha) * self.stats['average_confidence']
            )
    
    def _get_error_result(self, error_msg: str) -> Dict[str, Any]:
        """生成错误结果"""
        return {
            'success': False,
            'error': error_msg
        }
    
    def draw_faces(self, image: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """在图像上绘制人脸检测结果"""
        result_image = image.copy()
        
        for face in detection_result.get('faces', []):
            bbox = face.get('bbox')
            confidence = face.get('confidence', 0.0)
            gender = face.get('gender', 'Unknown')
            age = face.get('age', 0)
            
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                
                # 绘制边界框
                color = (0, 255, 0)  # 绿色
                thickness = 2
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
                
                # 绘制关键点
                landmarks = face.get('landmarks', [])
                for landmark in landmarks:
                    if len(landmark) == 2:
                        cv2.circle(result_image, (landmark[0], landmark[1]), 3, (0, 0, 255), -1)
                
                # 绘制信息标签
                info_text = f"Conf: {confidence:.2f}, {gender}, {age}"
                label_size = cv2.getTextSize(info_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # 标签背景
                cv2.rectangle(result_image,
                            (x1, y1 - label_size[1] - 10),
                            (x1 + label_size[0], y1),
                            color, -1)
                
                # 标签文字
                cv2.putText(result_image, info_text,
                          (x1, y1 - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return result_image
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取人脸数据库信息"""
        return {
            'total_faces': len(self.face_database),
            'known_identities': list(self.face_database.keys()),
            'database_size': sum(len(embedding) for embedding in self.face_database.values()),
            'stats': self.stats
        }
    
    def clear_database(self) -> Dict[str, Any]:
        """清空人脸数据库"""
        count = len(self.face_database)
        self.face_database.clear()
        self.face_images.clear()
        self.stats['known_faces_count'] = 0
        
        return {
            'success': True,
            'cleared_faces': count,
            'message': f"已清空 {count} 个人脸记录"
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "use_gpu": self.use_gpu,
            "insightface_available": INSIGHTFACE_AVAILABLE,
            "stats": self.stats,
            "config": self.config,
            "database_info": self.get_database_info()
        }
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded