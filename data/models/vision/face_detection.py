"""
人脸检测 - 检测和识别人脸
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import time

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class FaceDetection:
    """人脸检测模型"""
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "FaceDetection"
        self.version = "1.0.0"
        self.model = None
        self.is_loaded = False
        self.use_gpu = use_gpu and TORCH_AVAILABLE
        
        # 模型配置
        self.config = {
            'model_type': 'retinaface',  # retinaface, mtcnn, yolov5_face
            'confidence_threshold': 0.7,
            'nms_threshold': 0.4,
            'input_size': (640, 640),
            'max_faces': 50,
            'enable_landmarks': True,
            'enable_pose': False
        }
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'average_confidence': 0.0,
            'average_processing_time': 0.0
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载人脸检测模型"""
        try:
            print("📦 正在加载人脸检测模型...")
            
            # 尝试加载不同的人脸检测模型
            if self.config['model_type'] == 'retinaface':
                success = self._load_retinaface()
            elif self.config['model_type'] == 'mtcnn':
                success = self._load_mtcnn()
            else:
                success = self._load_opencv_dnn()
                
            if success:
                self.is_loaded = True
                print("✅ 人脸检测模型加载成功")
            else:
                print("❌ 人脸检测模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载人脸检测模型失败: {e}")
            return False
    
    def _load_retinaface(self) -> bool:
        """加载RetinaFace模型"""
        try:
            if TORCH_AVAILABLE:
                # 尝试导入RetinaFace
                try:
                    from retinaface import RetinaFace
                    self.model = RetinaFace(quality='normal')
                    return True
                except ImportError:
                    print("❌ RetinaFace未安装，使用OpenCV DNN作为备选")
                    return self._load_opencv_dnn()
            else:
                return self._load_opencv_dnn()
                
        except Exception as e:
            print(f"❌ 加载RetinaFace失败: {e}")
            return self._load_opencv_dnn()
    
    def _load_mtcnn(self) -> bool:
        """加载MTCNN模型"""
        try:
            if TORCH_AVAILABLE:
                try:
                    from facenet_pytorch import MTCNN
                    self.model = MTCNN(
                        keep_all=True,
                        thresholds=[0.6, 0.7, 0.7],
                        min_face_size=20,
                        device='cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
                    )
                    return True
                except ImportError:
                    print("❌ facenet_pytorch未安装，使用OpenCV DNN作为备选")
                    return self._load_opencv_dnn()
            else:
                return self._load_opencv_dnn()
                
        except Exception as e:
            print(f"❌ 加载MTCNN失败: {e}")
            return self._load_opencv_dnn()
    
    def _load_opencv_dnn(self) -> bool:
        """加载OpenCV DNN人脸检测模型"""
        try:
            # 加载OpenCV的DNN人脸检测器
            model_path = "models/face_detection/opencv/"
            os.makedirs(model_path, exist_ok=True)
            
            # 下载或加载预训练模型
            config_file = os.path.join(model_path, "deploy.prototxt")
            model_file = os.path.join(model_path, "res10_300x300_ssd_iter_140000_fp16.caffemodel")
            
            # 如果模型文件不存在，尝试下载（这里模拟加载）
            if not os.path.exists(config_file) or not os.path.exists(model_file):
                print("⚠️  OpenCV DNN模型文件不存在，使用Haar级联分类器作为备选")
                return self._load_haar_cascade()
            
            self.model = cv2.dnn.readNetFromCaffe(config_file, model_file)
            
            if self.use_gpu and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                self.model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                
            return True
            
        except Exception as e:
            print(f"❌ 加载OpenCV DNN失败: {e}")
            return self._load_haar_cascade()
    
    def _load_haar_cascade(self) -> bool:
        """加载Haar级联分类器"""
        try:
            # 加载OpenCV的Haar级联分类器
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.model = cv2.CascadeClassifier(cascade_path)
            return self.model is not None
            
        except Exception as e:
            print(f"❌ 加载Haar级联分类器失败: {e}")
            return False
    
    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """检测图像中的人脸"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"success": False, "faces": [], "error": "模型加载失败"}
        
        try:
            start_time = time.time()
            
            # 验证输入图像
            if image is None or image.size == 0:
                return {"success": False, "faces": [], "error": "输入图像为空"}
            
            # 预处理图像
            processed_image = self._preprocess_image(image)
            original_height, original_width = image.shape[:2]
            processed_height, processed_width = processed_image.shape[:2]
            
            # 执行人脸检测
            if self.config['model_type'] in ['retinaface', 'mtcnn'] and TORCH_AVAILABLE:
                detection_results = self._detect_dlib_mtcnn(processed_image)
            elif hasattr(self.model, 'detectMultiScale'):  # Haar Cascade
                detection_results = self._detect_haar(processed_image)
            else:  # OpenCV DNN
                detection_results = self._detect_dnn(processed_image)
            
            # 后处理结果
            faces = self._postprocess_detections(
                detection_results, 
                original_width, original_height,
                processed_width, processed_height
            )
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_stats(faces, processing_time)
            
            return {
                "success": True,
                "faces": faces,
                "count": len(faces),
                "processing_time": processing_time,
                "image_size": {"width": original_width, "height": original_height}
            }
            
        except Exception as e:
            print(f"❌ 人脸检测失败: {e}")
            return {"success": False, "faces": [], "error": str(e)}
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        # 调整图像大小（如果太大）
        max_dimension = 1280
        height, width = image.shape[:2]
        
        if max(height, width) > max_dimension:
            scale = max_dimension / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height))
        
        # 转换为RGB（如果需要）
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return image
    
    def _detect_dnn(self, image: np.ndarray) -> List[Dict]:
        """使用OpenCV DNN进行人脸检测"""
        blob = cv2.dnn.blobFromImage(
            image, 1.0, (300, 300), [104, 117, 123], 
            swapRB=False, crop=False
        )
        
        self.model.setInput(blob)
        detections = self.model.forward()
        
        results = []
        height, width = image.shape[:2]
        
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.config['confidence_threshold']:
                x1 = int(detections[0, 0, i, 3] * width)
                y1 = int(detections[0, 0, i, 4] * height)
                x2 = int(detections[0, 0, i, 5] * width)
                y2 = int(detections[0, 0, i, 6] * height)
                
                # 确保坐标在图像范围内
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(width, x2), min(height, y2)
                
                if x2 > x1 and y2 > y1:  # 有效的边界框
                    results.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(confidence),
                        'landmarks': []  # DNN不提供关键点
                    })
        
        return results
    
    def _detect_haar(self, image: np.ndarray) -> List[Dict]:
        """使用Haar级联分类器进行人脸检测"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        faces = self.model.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        results = []
        for (x, y, w, h) in faces:
            results.append({
                'bbox': [x, y, x + w, y + h],
                'confidence': 0.8,  # Haar没有置信度，使用默认值
                'landmarks': []
            })
        
        return results
    
    def _detect_dlib_mtcnn(self, image: np.ndarray) -> List[Dict]:
        """使用DLib或MTCNN进行人脸检测（模拟实现）"""
        # 这里模拟高级人脸检测器的输出
        # 实际项目中会调用真实的MTCNN或RetinaFace
        
        height, width = image.shape[:2]
        results = []
        
        # 模拟检测到1-3个人脸
        num_faces = min(self.config['max_faces'], np.random.randint(1, 4))
        
        for i in range(num_faces):
            # 生成随机但合理的人脸位置
            face_width = np.random.randint(50, min(300, width // 2))
            face_height = np.random.randint(50, min(300, height // 2))
            x1 = np.random.randint(0, width - face_width)
            y1 = np.random.randint(0, height - face_height)
            x2 = x1 + face_width
            y2 = y1 + face_height
            
            confidence = np.random.uniform(0.7, 0.98)
            
            # 模拟人脸关键点
            landmarks = []
            if self.config['enable_landmarks']:
                # 5个关键点：左右眼、鼻子、左右嘴角
                landmarks = [
                    [x1 + face_width * 0.3, y1 + face_height * 0.35],  # 左眼
                    [x1 + face_width * 0.7, y1 + face_height * 0.35],  # 右眼
                    [x1 + face_width * 0.5, y1 + face_height * 0.5],   # 鼻子
                    [x1 + face_width * 0.3, y1 + face_height * 0.7],   # 左嘴角
                    [x1 + face_width * 0.7, y1 + face_height * 0.7]    # 右嘴角
                ]
            
            results.append({
                'bbox': [x1, y1, x2, y2],
                'confidence': float(confidence),
                'landmarks': landmarks
            })
        
        return results
    
    def _postprocess_detections(self, detections: List[Dict], 
                              orig_width: int, orig_height: int,
                              proc_width: int, proc_height: int) -> List[Dict]:
        """后处理检测结果"""
        processed_faces = []
        
        # 计算缩放比例
        scale_x = orig_width / proc_width
        scale_y = orig_height / proc_height
        
        for detection in detections:
            # 缩放边界框和关键点
            bbox = detection['bbox']
            scaled_bbox = [
                int(bbox[0] * scale_x),
                int(bbox[1] * scale_y), 
                int(bbox[2] * scale_x),
                int(bbox[3] * scale_y)
            ]
            
            scaled_landmarks = []
            for landmark in detection['landmarks']:
                scaled_landmarks.append([
                    int(landmark[0] * scale_x),
                    int(landmark[1] * scale_y)
                ])
            
            # 计算边界框面积和中心点
            bbox_width = scaled_bbox[2] - scaled_bbox[0]
            bbox_height = scaled_bbox[3] - scaled_bbox[1]
            bbox_area = bbox_width * bbox_height
            bbox_center = [
                scaled_bbox[0] + bbox_width // 2,
                scaled_bbox[1] + bbox_height // 2
            ]
            
            face_data = {
                'bbox': scaled_bbox,
                'confidence': detection['confidence'],
                'landmarks': scaled_landmarks,
                'area': bbox_area,
                'center': bbox_center,
                'width': bbox_width,
                'height': bbox_height
            }
            
            processed_faces.append(face_data)
        
        # 按置信度排序
        processed_faces.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 限制最大人脸数量
        if len(processed_faces) > self.config['max_faces']:
            processed_faces = processed_faces[:self.config['max_faces']]
        
        return processed_faces
    
    def _update_stats(self, faces: List[Dict], processing_time: float):
        """更新性能统计"""
        self.stats['total_detections'] += len(faces)
        
        if faces:
            avg_conf = sum(face['confidence'] for face in faces) / len(faces)
            # 指数移动平均
            alpha = 0.1
            self.stats['average_confidence'] = (
                alpha * avg_conf + (1 - alpha) * self.stats['average_confidence']
            )
        
        # 更新平均处理时间
        alpha = 0.1
        self.stats['average_processing_time'] = (
            alpha * processing_time + 
            (1 - alpha) * self.stats['average_processing_time']
        )
    
    def extract_face_region(self, image: np.ndarray, bbox: List[int], 
                          margin: float = 0.2) -> np.ndarray:
        """提取人脸区域（带边界扩展）"""
        x1, y1, x2, y2 = bbox
        
        # 计算扩展的边界
        width = x2 - x1
        height = y2 - y1
        
        margin_x = int(width * margin)
        margin_y = int(height * margin)
        
        # 扩展边界框
        x1 = max(0, x1 - margin_x)
        y1 = max(0, y1 - margin_y)
        x2 = min(image.shape[1], x2 + margin_x)
        y2 = min(image.shape[0], y2 + margin_y)
        
        # 提取人脸区域
        face_region = image[y1:y2, x1:x2]
        
        return face_region
    
    def draw_detections(self, image: np.ndarray, faces: List[Dict], 
                       draw_landmarks: bool = True) -> np.ndarray:
        """在图像上绘制检测结果"""
        result_image = image.copy()
        
        for i, face in enumerate(faces):
            bbox = face['bbox']
            confidence = face['confidence']
            
            # 绘制边界框
            color = (0, 255, 0)  # 绿色
            thickness = 2
            cv2.rectangle(result_image, 
                         (bbox[0], bbox[1]), 
                         (bbox[2], bbox[3]), 
                         color, thickness)
            
            # 绘制置信度
            label = f"Face {i+1}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(result_image,
                         (bbox[0], bbox[1] - label_size[1] - 10),
                         (bbox[0] + label_size[0], bbox[1]),
                         color, -1)
            cv2.putText(result_image, label,
                       (bbox[0], bbox[1] - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            
            # 绘制关键点
            if draw_landmarks and face['landmarks']:
                for landmark in face['landmarks']:
                    cv2.circle(result_image, 
                              (landmark[0], landmark[1]), 
                              3, (0, 0, 255), -1)
        
        return result_image
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "model_type": self.config['model_type'],
            "use_gpu": self.use_gpu,
            "stats": self.stats,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded
