"""
情绪识别 - 识别面部情绪
"""

import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
import time

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class EmotionRecognition:
    """情绪识别模型"""
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "EmotionRecognition"
        self.version = "1.0.0"
        self.model = None
        self.is_loaded = False
        self.use_gpu = use_gpu and TORCH_AVAILABLE
        
        # 情绪类别
        self.emotions = [
            'angry',    # 生气
            'disgust',  # 厌恶  
            'fear',     # 恐惧
            'happy',    # 高兴
            'sad',      # 悲伤
            'surprise', # 惊讶
            'neutral'   # 中性
        ]
        
        # 中文情绪标签
        self.emotion_labels_zh = {
            'angry': '生气',
            'disgust': '厌恶', 
            'fear': '恐惧',
            'happy': '高兴',
            'sad': '悲伤', 
            'surprise': '惊讶',
            'neutral': '中性'
        }
        
        # 模型配置
        self.config = {
            'model_type': 'emotion_net',  # emotion_net, fer2013, affectnet
            'input_size': (48, 48),
            'confidence_threshold': 0.5,
            'enable_grad_cam': False
        }
        
        # 性能统计
        self.stats = {
            'total_predictions': 0,
            'average_confidence': 0.0,
            'emotion_distribution': {emotion: 0 for emotion in self.emotions}
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载情绪识别模型"""
        try:
            print("📦 正在加载情绪识别模型...")
            
            if TORCH_AVAILABLE:
                success = self._load_pytorch_model()
            else:
                success = self._load_opencv_model()
                
            if success:
                self.is_loaded = True
                print("✅ 情绪识别模型加载成功")
            else:
                print("❌ 情绪识别模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载情绪识别模型失败: {e}")
            return False
    
    def _load_pytorch_model(self) -> bool:
        """加载PyTorch情绪识别模型"""
        try:
            # 创建简单的情绪识别CNN模型
            class EmotionNet(nn.Module):
                def __init__(self, num_classes=7):
                    super(EmotionNet, self).__init__()
                    self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
                    self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
                    self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
                    self.pool = nn.MaxPool2d(2, 2)
                    self.dropout = nn.Dropout(0.25)
                    self.fc1 = nn.Linear(128 * 6 * 6, 512)
                    self.fc2 = nn.Linear(512, num_classes)
                    self.relu = nn.ReLU()
                    
                def forward(self, x):
                    x = self.pool(self.relu(self.conv1(x)))
                    x = self.pool(self.relu(self.conv2(x)))
                    x = self.pool(self.relu(self.conv3(x)))
                    x = x.view(-1, 128 * 6 * 6)
                    x = self.dropout(x)
                    x = self.relu(self.fc1(x))
                    x = self.dropout(x)
                    x = self.fc2(x)
                    return x
            
            # 初始化模型
            self.model = EmotionNet(num_classes=len(self.emotions))
            
            # 加载预训练权重（这里模拟加载）
            # 实际项目中会从文件加载训练好的权重
            print("🔧 初始化情绪识别模型权重...")
            
            # 设置设备
            self.device = torch.device('cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            self.model.eval()
            
            return True
            
        except Exception as e:
            print(f"❌ 加载PyTorch模型失败: {e}")
            return self._load_opencv_model()
    
    def _load_opencv_model(self) -> bool:
        """加载OpenCV情绪识别模型"""
        try:
            # 尝试加载OpenCV DNN模型
            model_path = "models/emotion_recognition/"
            os.makedirs(model_path, exist_ok=True)
            
            # 这里模拟模型加载，实际项目中需要真实的模型文件
            print("⚠️  使用模拟情绪识别模型")
            self.model = "opencv_emotion_model"
            return True
            
        except Exception as e:
            print(f"❌ 加载OpenCV模型失败: {e}")
            return False
    
    def recognize(self, image: np.ndarray, face_bbox: Optional[List[int]] = None) -> Dict[str, Any]:
        """识别面部情绪"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 验证输入
            if image is None or image.size == 0:
                return self._get_error_result("输入图像为空")
            
            # 提取人脸区域（如果提供了边界框）
            if face_bbox is not None:
                face_image = self._extract_face(image, face_bbox)
            else:
                face_image = image
            
            # 预处理人脸图像
            processed_face = self._preprocess_face(face_image)
            
            # 进行情绪识别
            if TORCH_AVAILABLE and isinstance(self.model, torch.nn.Module):
                emotion_result = self._recognize_pytorch(processed_face)
            else:
                emotion_result = self._recognize_opencv(processed_face)
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_stats(emotion_result)
            
            emotion_result['processing_time'] = processing_time
            emotion_result['success'] = True
            
            return emotion_result
            
        except Exception as e:
            print(f"❌ 情绪识别失败: {e}")
            return self._get_error_result(str(e))
    
    def _extract_face(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """提取人脸区域"""
        x1, y1, x2, y2 = bbox
        
        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            raise ValueError("无效的人脸边界框")
        
        face_image = image[y1:y2, x1:x2]
        return face_image
    
    def _preprocess_face(self, face_image: np.ndarray) -> np.ndarray:
        """预处理人脸图像"""
        # 转换为灰度图
        if len(face_image.shape) == 3:
            gray_face = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
        else:
            gray_face = face_image
        
        # 调整大小
        input_size = self.config['input_size']
        resized_face = cv2.resize(gray_face, input_size)
        
        # 归一化
        normalized_face = resized_face.astype(np.float32) / 255.0
        
        return normalized_face
    
    def _recognize_pytorch(self, face_image: np.ndarray) -> Dict[str, Any]:
        """使用PyTorch模型进行情绪识别"""
        # 准备输入
        input_tensor = torch.from_numpy(face_image).unsqueeze(0).unsqueeze(0)  # 添加batch和channel维度
        input_tensor = input_tensor.to(self.device)
        
        # 推理
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            confidence = confidence.item()
            predicted_idx = predicted.item()
            emotion = self.emotions[predicted_idx]
            
            # 获取所有情绪的概率
            all_probs = probabilities.cpu().numpy()[0]
            emotion_probs = {self.emotions[i]: float(prob) for i, prob in enumerate(all_probs)}
        
        return {
            'emotion': emotion,
            'emotion_zh': self.emotion_labels_zh[emotion],
            'confidence': confidence,
            'all_emotions': emotion_probs,
            'predicted_index': predicted_idx
        }
    
    def _recognize_opencv(self, face_image: np.ndarray) -> Dict[str, Any]:
        """使用OpenCV模型进行情绪识别（模拟实现）"""
        # 模拟情绪识别结果
        # 实际项目中会调用真实的OpenCV DNN模型
        
        # 生成模拟的概率分布
        base_probs = np.random.dirichlet(np.ones(len(self.emotions)))
        
        # 根据图像特征调整概率（模拟）
        # 这里使用图像的亮度作为简单特征来影响情绪预测
        brightness = np.mean(face_image)
        
        if brightness > 0.7:  # 较亮的图像更可能是高兴
            base_probs[3] += 0.3  # 增加高兴的概率
        elif brightness < 0.3:  # 较暗的图像更可能是悲伤
            base_probs[4] += 0.3  # 增加悲伤的概率
        
        # 归一化概率
        base_probs = base_probs / np.sum(base_probs)
        
        # 找到最大概率的情绪
        predicted_idx = np.argmax(base_probs)
        emotion = self.emotions[predicted_idx]
        confidence = base_probs[predicted_idx]
        
        emotion_probs = {self.emotions[i]: float(prob) for i, prob in enumerate(base_probs)}
        
        return {
            'emotion': emotion,
            'emotion_zh': self.emotion_labels_zh[emotion],
            'confidence': confidence,
            'all_emotions': emotion_probs,
            'predicted_index': predicted_idx
        }
    
    def _update_stats(self, emotion_result: Dict[str, Any]):
        """更新统计信息"""
        self.stats['total_predictions'] += 1
        
        if emotion_result['success']:
            emotion = emotion_result['emotion']
            confidence = emotion_result['confidence']
            
            # 更新情绪分布
            self.stats['emotion_distribution'][emotion] += 1
            
            # 更新平均置信度（指数移动平均）
            alpha = 0.1
            self.stats['average_confidence'] = (
                alpha * confidence + (1 - alpha) * self.stats['average_confidence']
            )
    
    def _get_error_result(self, error_msg: str) -> Dict[str, Any]:
        """生成错误结果"""
        return {
            'success': False,
            'error': error_msg,
            'emotion': 'unknown',
            'emotion_zh': '未知',
            'confidence': 0.0,
            'all_emotions': {emotion: 0.0 for emotion in self.emotions}
        }
    
    def get_emotion_distribution(self) -> Dict[str, float]:
        """获取情绪分布统计"""
        total = self.stats['total_predictions']
        if total == 0:
            return {emotion: 0.0 for emotion in self.emotions}
        
        distribution = {}
        for emotion, count in self.stats['emotion_distribution'].items():
            distribution[emotion] = count / total
            
        return distribution
    
    def analyze_video_emotions(self, video_path: str, interval: float = 1.0) -> Dict[str, Any]:
        """分析视频中的情绪变化"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"success": False, "error": "无法打开视频文件"}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(fps * interval)
            
            emotions_over_time = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 按间隔处理帧
                if frame_count % frame_interval == 0:
                    # 这里需要先进行人脸检测，然后情绪识别
                    # 简化实现：直接识别整个帧的主要情绪
                    emotion_result = self.recognize(frame)
                    
                    if emotion_result['success']:
                        emotions_over_time.append({
                            'frame': frame_count,
                            'time': frame_count / fps,
                            'emotion': emotion_result['emotion'],
                            'confidence': emotion_result['confidence']
                        })
                
                frame_count += 1
            
            cap.release()
            
            return {
                "success": True,
                "total_frames": frame_count,
                "analyzed_frames": len(emotions_over_time),
                "duration": frame_count / fps,
                "emotions_over_time": emotions_over_time
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "emotions": self.emotions,
            "emotion_labels_zh": self.emotion_labels_zh,
            "use_gpu": self.use_gpu,
            "stats": self.stats,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded