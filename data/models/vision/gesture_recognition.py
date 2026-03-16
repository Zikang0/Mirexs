"""
手势识别 - 识别手势动作
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

class GestureRecognition:
    """手势识别模型"""
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "GestureRecognition"
        self.version = "1.0.0"
        self.model = None
        self.is_loaded = False
        self.use_gpu = use_gpu and TORCH_AVAILABLE
        
        # 支持的手势类型
        self.gestures = [
            'fist',           # 握拳
            'open_hand',      # 张开手
            'thumbs_up',      # 点赞
            'thumbs_down',    # 点踩
            'victory',        # 胜利手势
            'ok',             # OK手势
            'pointing',       # 指向
            'pinch',          # 捏合
            'rock',           # 摇滚手势
            'peace',          # 和平手势
            'call_me',        # 打电话手势
            'stop',           # 停止手势
            'none'            # 无手势
        ]
        
        # 中文手势标签
        self.gesture_labels_zh = {
            'fist': '握拳',
            'open_hand': '张开手', 
            'thumbs_up': '点赞',
            'thumbs_down': '点踩',
            'victory': '胜利手势',
            'ok': 'OK手势',
            'pointing': '指向',
            'pinch': '捏合',
            'rock': '摇滚手势',
            'peace': '和平手势',
            'call_me': '打电话',
            'stop': '停止',
            'none': '无手势'
        }
        
        # 模型配置
        self.config = {
            'model_type': 'gesture_net',
            'input_size': (224, 224),
            'confidence_threshold': 0.6,
            'enable_hand_detection': True,
            'min_hand_size': 0.1,  # 手部最小相对尺寸
            'max_hands': 2,        # 最大手部数量
            'smoothing_window': 5  # 平滑窗口大小
        }
        
        # 手势历史（用于平滑）
        self.gesture_history = []
        
        # 性能统计
        self.stats = {
            'total_predictions': 0,
            'average_confidence': 0.0,
            'gesture_distribution': {gesture: 0 for gesture in self.gestures}
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载手势识别模型"""
        try:
            print("📦 正在加载手势识别模型...")
            
            if TORCH_AVAILABLE:
                success = self._load_pytorch_model()
            else:
                success = self._load_opencv_model()
                
            if success:
                self.is_loaded = True
                print("✅ 手势识别模型加载成功")
            else:
                print("❌ 手势识别模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载手势识别模型失败: {e}")
            return False
    
    def _load_pytorch_model(self) -> bool:
        """加载PyTorch手势识别模型"""
        try:
            import torch.nn as nn
            
            # 创建手势识别CNN模型
            class GestureNet(nn.Module):
                def __init__(self, num_classes=13):
                    super(GestureNet, self).__init__()
                    self.features = nn.Sequential(
                        nn.Conv2d(3, 64, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.MaxPool2d(kernel_size=2, stride=2),
                        
                        nn.Conv2d(64, 128, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.MaxPool2d(kernel_size=2, stride=2),
                        
                        nn.Conv2d(128, 256, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.Conv2d(256, 256, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.MaxPool2d(kernel_size=2, stride=2),
                        
                        nn.Conv2d(256, 512, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.Conv2d(512, 512, kernel_size=3, padding=1),
                        nn.ReLU(inplace=True),
                        nn.MaxPool2d(kernel_size=2, stride=2),
                    )
                    
                    self.classifier = nn.Sequential(
                        nn.Dropout(0.5),
                        nn.Linear(512 * 7 * 7, 1024),
                        nn.ReLU(inplace=True),
                        nn.Dropout(0.5),
                        nn.Linear(1024, 512),
                        nn.ReLU(inplace=True),
                        nn.Linear(512, num_classes)
                    )
                    
                def forward(self, x):
                    x = self.features(x)
                    x = x.view(x.size(0), -1)
                    x = self.classifier(x)
                    return x
            
            # 初始化模型
            self.model = GestureNet(num_classes=len(self.gestures))
            
            # 加载预训练权重（模拟）
            print("🔧 初始化手势识别模型权重...")
            
            # 设置设备
            self.device = torch.device('cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu')
            self.model.to(self.device)
            self.model.eval()
            
            return True
            
        except Exception as e:
            print(f"❌ 加载PyTorch手势模型失败: {e}")
            return self._load_opencv_model()
    
    def _load_opencv_model(self) -> bool:
        """加载OpenCV手势识别模型"""
        try:
            # 模拟OpenCV模型加载
            print("⚠️  使用模拟手势识别模型")
            self.model = "opencv_gesture_model"
            return True
            
        except Exception as e:
            print(f"❌ 加载OpenCV手势模型失败: {e}")
            return False
    
    def recognize(self, image: np.ndarray, hand_bbox: Optional[List[int]] = None) -> Dict[str, Any]:
        """识别手势"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 验证输入
            if image is None or image.size == 0:
                return self._get_error_result("输入图像为空")
            
            # 检测手部区域（如果未提供边界框）
            if hand_bbox is None and self.config['enable_hand_detection']:
                hand_regions = self._detect_hands(image)
            else:
                hand_regions = [hand_bbox] if hand_bbox else []
            
            results = []
            
            # 对每个手部区域进行手势识别
            for i, bbox in enumerate(hand_regions):
                if bbox is None:
                    continue
                    
                # 提取手部区域
                hand_image = self._extract_hand_region(image, bbox)
                
                # 预处理手部图像
                processed_hand = self._preprocess_hand(hand_image)
                
                # 进行手势识别
                if TORCH_AVAILABLE and isinstance(self.model, torch.nn.Module):
                    gesture_result = self._recognize_pytorch(processed_hand)
                else:
                    gesture_result = self._recognize_opencv(processed_hand)
                
                # 添加手部位置信息
                gesture_result['hand_id'] = i
                gesture_result['bbox'] = bbox
                gesture_result['hand_image_size'] = hand_image.shape[:2]
                
                results.append(gesture_result)
            
            # 如果没有检测到手部，返回无手势结果
            if not results:
                results.append(self._get_no_gesture_result())
            
            # 应用时间平滑
            smoothed_results = self._apply_temporal_smoothing(results)
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_stats(smoothed_results)
            
            return {
                "success": True,
                "hands": smoothed_results,
                "hand_count": len(smoothed_results),
                "processing_time": processing_time,
                "image_size": image.shape[:2]
            }
            
        except Exception as e:
            print(f"❌ 手势识别失败: {e}")
            return self._get_error_result(str(e))
    
    def _detect_hands(self, image: np.ndarray) -> List[List[int]]:
        """检测手部区域"""
        # 使用肤色检测和运动检测的简单手部检测
        # 实际项目中可以使用MediaPipe或专用手部检测器
        
        height, width = image.shape[:2]
        hand_regions = []
        
        # 转换为HSV颜色空间进行肤色检测
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 肤色范围（需要根据实际调整）
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # 创建肤色掩码
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 形态学操作改善掩码
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # 过滤小区域
            area = cv2.contourArea(contour)
            min_area = self.config['min_hand_size'] * height * width
            
            if area > min_area:
                # 获取边界框
                x, y, w, h = cv2.boundingRect(contour)
                
                # 扩展边界框
                margin = 0.2
                x_exp = max(0, int(x - w * margin))
                y_exp = max(0, int(y - h * margin))
                w_exp = min(width - x_exp, int(w * (1 + 2 * margin)))
                h_exp = min(height - y_exp, int(h * (1 + 2 * margin)))
                
                hand_regions.append([x_exp, y_exp, x_exp + w_exp, y_exp + h_exp])
                
                # 限制最大手部数量
                if len(hand_regions) >= self.config['max_hands']:
                    break
        
        return hand_regions
    
    def _extract_hand_region(self, image: np.ndarray, bbox: List[int]) -> np.ndarray:
        """提取手部区域"""
        x1, y1, x2, y2 = bbox
        
        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            raise ValueError("无效的手部边界框")
        
        hand_image = image[y1:y2, x1:x2]
        return hand_image
    
    def _preprocess_hand(self, hand_image: np.ndarray) -> np.ndarray:
        """预处理手部图像"""
        # 调整大小
        input_size = self.config['input_size']
        resized_hand = cv2.resize(hand_image, input_size)
        
        # 转换为RGB（如果需要）
        if len(resized_hand.shape) == 3:
            rgb_hand = cv2.cvtColor(resized_hand, cv2.COLOR_BGR2RGB)
        else:
            rgb_hand = resized_hand
            
        # 归一化
        normalized_hand = rgb_hand.astype(np.float32) / 255.0
        
        return normalized_hand
    
    def _recognize_pytorch(self, hand_image: np.ndarray) -> Dict[str, Any]:
        """使用PyTorch模型进行手势识别"""
        # 准备输入
        input_tensor = torch.from_numpy(hand_image).permute(2, 0, 1).unsqueeze(0)  # CHW -> NCHW
        input_tensor = input_tensor.to(self.device)
        
        # 推理
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
            confidence = confidence.item()
            predicted_idx = predicted.item()
            gesture = self.gestures[predicted_idx]
            
            # 获取所有手势的概率
            all_probs = probabilities.cpu().numpy()[0]
            gesture_probs = {self.gestures[i]: float(prob) for i, prob in enumerate(all_probs)}
        
        return {
            'gesture': gesture,
            'gesture_zh': self.gesture_labels_zh[gesture],
            'confidence': confidence,
            'all_gestures': gesture_probs,
            'predicted_index': predicted_idx
        }
    
    def _recognize_opencv(self, hand_image: np.ndarray) -> Dict[str, Any]:
        """使用OpenCV模型进行手势识别（模拟实现）"""
        # 模拟手势识别结果
        # 基于手部图像特征生成合理的概率分布
        
        # 计算手部图像的特征
        gray_hand = cv2.cvtColor((hand_image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        
        # 使用图像矩和轮廓特征
        moments = cv2.moments(gray_hand)
        hu_moments = cv2.HuMoments(moments)
        
        # 基于Hu矩生成模拟概率
        base_probs = np.random.dirichlet(np.ones(len(self.gestures)))
        
        # 根据图像特征调整概率
        if hu_moments[0] > 0.1:  # 形状较复杂，可能是张开手
            base_probs[1] += 0.2  # 增加张开手的概率
        else:  # 形状较简单，可能是握拳
            base_probs[0] += 0.2  # 增加握拳的概率
        
        # 归一化概率
        base_probs = base_probs / np.sum(base_probs)
        
        # 找到最大概率的手势
        predicted_idx = np.argmax(base_probs)
        gesture = self.gestures[predicted_idx]
        confidence = base_probs[predicted_idx]
        
        gesture_probs = {self.gestures[i]: float(prob) for i, prob in enumerate(base_probs)}
        
        return {
            'gesture': gesture,
            'gesture_zh': self.gesture_labels_zh[gesture],
            'confidence': confidence,
            'all_gestures': gesture_probs,
            'predicted_index': predicted_idx
        }
    
    def _apply_temporal_smoothing(self, current_results: List[Dict]) -> List[Dict]:
        """应用时间平滑"""
        # 保存当前结果到历史
        self.gesture_history.append(current_results)
        
        # 保持历史长度
        if len(self.gesture_history) > self.config['smoothing_window']:
            self.gesture_history.pop(0)
        
        # 如果历史不足，直接返回当前结果
        if len(self.gesture_history) < 2:
            return current_results
        
        # 对每个手部应用平滑
        smoothed_results = []
        
        for hand_idx in range(len(current_results)):
            hand_gestures = []
            hand_confidences = []
            
            # 收集该手部在所有历史帧中的结果
            for frame_results in self.gesture_history:
                if hand_idx < len(frame_results):
                    hand_gestures.append(frame_results[hand_idx]['gesture'])
                    hand_confidences.append(frame_results[hand_idx]['confidence'])
            
            # 计算最频繁的手势
            if hand_gestures:
                unique_gestures, counts = np.unique(hand_gestures, return_counts=True)
                most_frequent_idx = np.argmax(counts)
                smoothed_gesture = unique_gestures[most_frequent_idx]
                
                # 计算平均置信度
                avg_confidence = np.mean(hand_confidences)
                
                # 创建平滑后的结果
                smoothed_result = current_results[hand_idx].copy()
                smoothed_result['gesture'] = smoothed_gesture
                smoothed_result['gesture_zh'] = self.gesture_labels_zh[smoothed_gesture]
                smoothed_result['confidence'] = avg_confidence
                smoothed_result['smoothed'] = True
                
                smoothed_results.append(smoothed_result)
            else:
                smoothed_results.append(current_results[hand_idx])
        
        return smoothed_results
    
    def _get_no_gesture_result(self) -> Dict[str, Any]:
        """生成无手势结果"""
        all_gestures = {gesture: 0.0 for gesture in self.gestures}
        all_gestures['none'] = 1.0
        
        return {
            'gesture': 'none',
            'gesture_zh': '无手势',
            'confidence': 1.0,
            'all_gestures': all_gestures,
            'predicted_index': self.gestures.index('none'),
            'bbox': None,
            'hand_image_size': None
        }
    
    def _get_error_result(self, error_msg: str) -> Dict[str, Any]:
        """生成错误结果"""
        return {
            'success': False,
            'error': error_msg,
            'hands': []
        }
    
    def _update_stats(self, results: List[Dict]):
        """更新统计信息"""
        self.stats['total_predictions'] += len(results)
        
        for result in results:
            if 'gesture' in result:
                gesture = result['gesture']
                confidence = result.get('confidence', 0.0)
                
                # 更新手势分布
                self.stats['gesture_distribution'][gesture] += 1
                
                # 更新平均置信度（指数移动平均）
                alpha = 0.1
                self.stats['average_confidence'] = (
                    alpha * confidence + (1 - alpha) * self.stats['average_confidence']
                )
    
    def get_gesture_distribution(self) -> Dict[str, float]:
        """获取手势分布统计"""
        total = self.stats['total_predictions']
        if total == 0:
            return {gesture: 0.0 for gesture in self.gestures}
        
        distribution = {}
        for gesture, count in self.stats['gesture_distribution'].items():
            distribution[gesture] = count / total
            
        return distribution
    
    def draw_gestures(self, image: np.ndarray, results: List[Dict]) -> np.ndarray:
        """在图像上绘制手势识别结果"""
        result_image = image.copy()
        
        for i, result in enumerate(results):
            bbox = result.get('bbox')
            gesture = result.get('gesture', 'unknown')
            confidence = result.get('confidence', 0.0)
            
            # 绘制手部边界框
            if bbox:
                x1, y1, x2, y2 = bbox
                color = (0, 255, 0)  # 绿色
                thickness = 2
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
                
                # 绘制手势标签
                label = f"Hand {i+1}: {gesture} ({confidence:.2f})"
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
        
        return result_image
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "gestures": self.gestures,
            "gesture_labels_zh": self.gesture_labels_zh,
            "use_gpu": self.use_gpu,
            "stats": self.stats,
            "config": self.config
        }
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded