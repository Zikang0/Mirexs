"""
手写识别模块：识别手写输入并转换为文本
"""

import os
import time
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Tuple, Optional, Any
import json
import logging
from dataclasses import dataclass, field
from collections import deque

from data.models.vision.handwriting_models import HandwritingModel
from infrastructure.communication.message_bus import MessageBus
from utils.ai_utilities.model_utils import ModelLoader
from config import ConfigManager

logger = logging.getLogger(__name__)


@dataclass
class StrokePoint:
    """笔画点"""
    x: float
    y: float
    pressure: float = 1.0
    timestamp: float = 0.0
    is_end: bool = False


@dataclass
class Stroke:
    """笔画"""
    points: List[StrokePoint] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    
    def add_point(self, point: StrokePoint) -> None:
        """添加点到笔画"""
        self.points.append(point)
        if not self.start_time:
            self.start_time = point.timestamp
        self.end_time = point.timestamp
    
    def to_numpy(self) -> np.ndarray:
        """转换为numpy数组"""
        return np.array([(p.x, p.y, p.pressure) for p in self.points])
    
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """获取边界框"""
        if not self.points:
            return 0, 0, 0, 0
        
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class RecognitionResult:
    """识别结果"""
    text: str
    confidence: float
    alternatives: List[str]
    strokes_used: List[Stroke]
    recognition_time: float
    language: str = "zh-CN"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "alternatives": self.alternatives[:3],  # 只返回前3个备选
            "strokes_count": len(self.strokes_used),
            "recognition_time": self.recognition_time,
            "language": self.language
        }


class HandwritingRecognizer:
    """手写识别器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化手写识别器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        self.model_loader = ModelLoader()
        
        # 初始化参数
        self.is_active = False
        self.current_strokes = []
        self.stroke_history = deque(maxlen=100)  # 保留最近100个笔画
        self.recognition_history = deque(maxlen=50)  # 保留最近50个识别结果
        
        # 识别模型
        self.recognition_models = {}  # language -> model
        self.current_language = "zh-CN"
        
        # 预处理参数
        self.image_size = (256, 256)
        self.smoothing_window = 5
        self.min_stroke_length = 5
        
        # 加载配置
        self.load_config()
        
        # 加载模型
        self.load_models()
        
        logger.info("HandwritingRecognizer initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("handwriting_config", {})
            self.enable_realtime_recognition = config.get("enable_realtime", True)
            self.confidence_threshold = config.get("confidence_threshold", 0.7)
            self.languages = config.get("supported_languages", ["zh-CN", "en-US"])
            self.max_alternatives = config.get("max_alternatives", 5)
            
            # 预处理配置
            preprocessing = config.get("preprocessing", {})
            self.image_size = tuple(preprocessing.get("image_size", [256, 256]))
            self.smoothing_window = preprocessing.get("smoothing_window", 5)
            self.min_stroke_length = preprocessing.get("min_stroke_length", 5)
            
            logger.debug(f"Handwriting config loaded: languages={self.languages}")
        except Exception as e:
            logger.error(f"Failed to load handwriting config: {e}")
    
    def load_models(self) -> None:
        """加载手写识别模型"""
        try:
            for language in self.languages:
                model_path = f"data/models/vision/handwriting/{language}/model.pt"
                
                if os.path.exists(model_path):
                    # 使用自定义的手写识别模型
                    model = HandwritingModel(language=language)
                    model.load_state_dict(torch.load(model_path, map_location='cpu'))
                    model.eval()
                    
                    self.recognition_models[language] = model
                    logger.info(f"Loaded handwriting model for {language}")
                else:
                    # 使用默认模型
                    logger.warning(f"Model for {language} not found at {model_path}, using default")
                    model = self._create_default_model(language)
                    self.recognition_models[language] = model
            
            logger.info(f"Loaded {len(self.recognition_models)} handwriting models")
        except Exception as e:
            logger.error(f"Failed to load handwriting models: {e}")
    
    def _create_default_model(self, language: str) -> nn.Module:
        """创建默认模型（当模型文件不存在时）"""
        # 这是一个简单的CNN模型示例
        class DefaultHandwritingModel(nn.Module):
            def __init__(self, num_classes: int = 1000):
                super().__init__()
                self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)
                self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
                self.pool = nn.MaxPool2d(2, 2)
                self.fc1 = nn.Linear(64 * 64 * 64, 512)
                self.fc2 = nn.Linear(512, num_classes)
                self.dropout = nn.Dropout(0.5)
                
            def forward(self, x):
                x = self.pool(F.relu(self.conv1(x)))
                x = self.pool(F.relu(self.conv2(x)))
                x = torch.flatten(x, 1)
                x = F.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.fc2(x)
                return x
        
        return DefaultHandwritingModel()
    
    def start_recognition(self) -> bool:
        """
        开始手写识别
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_active:
            logger.warning("Handwriting recognition is already active")
            return False
        
        self.is_active = True
        
        # 注册消息处理器
        self.message_bus.subscribe("handwriting_event", self._handle_handwriting_message)
        
        # 清空历史数据
        self.current_strokes.clear()
        
        logger.info("Handwriting recognition started")
        return True
    
    def stop_recognition(self) -> None:
        """停止手写识别"""
        self.is_active = False
        
        # 处理未完成的笔画
        if self.current_strokes:
            self._process_completed_strokes()
        
        self.message_bus.unsubscribe("handwriting_event", self._handle_handwriting_message)
        logger.info("Handwriting recognition stopped")
    
    def add_stroke_point(self, x: float, y: float, pressure: float = 1.0, 
                         is_end: bool = False, timestamp: Optional[float] = None) -> None:
        """
        添加笔画点
        
        Args:
            x: X坐标
            y: Y坐标
            pressure: 压力值 (0.0-1.0)
            is_end: 是否笔画结束
            timestamp: 时间戳（如果为None则使用当前时间）
        """
        if not self.is_active:
            return
        
        if timestamp is None:
            timestamp = time.time()
        
        point = StrokePoint(
            x=x,
            y=y,
            pressure=pressure,
            timestamp=timestamp,
            is_end=is_end
        )
        
        # 添加到当前笔画或创建新笔画
        if not self.current_strokes or self.current_strokes[-1].points[-1].is_end:
            # 创建新笔画
            stroke = Stroke()
            stroke.add_point(point)
            self.current_strokes.append(stroke)
        else:
            # 添加到当前笔画
            self.current_strokes[-1].add_point(point)
        
        # 如果笔画结束，进行处理
        if is_end:
            self._process_completed_strokes()
    
    def _process_completed_strokes(self) -> None:
        """处理已完成的笔画"""
        if not self.current_strokes:
            return
        
        # 获取已完成的笔画（最后一点标记为结束的笔画）
        completed_strokes = []
        for stroke in self.current_strokes:
            if stroke.points and stroke.points[-1].is_end:
                completed_strokes.append(stroke)
        
        if not completed_strokes:
            return
        
        # 添加到历史
        for stroke in completed_strokes:
            self.stroke_history.append(stroke)
        
        # 实时识别（如果启用）
        if self.enable_realtime_recognition:
            recognition_result = self.recognize_strokes(completed_strokes)
            if recognition_result and recognition_result.confidence >= self.confidence_threshold:
                self.recognition_history.append(recognition_result)
                
                # 发布识别结果
                self.message_bus.publish("handwriting_recognition", {
                    "result": recognition_result.to_dict(),
                    "strokes": [s.to_numpy().tolist() for s in completed_strokes],
                    "timestamp": time.time()
                })
        
        # 清空已处理的笔画
        self.current_strokes = [s for s in self.current_strokes if not s.points[-1].is_end]
    
    def recognize_strokes(self, strokes: List[Stroke]) -> Optional[RecognitionResult]:
        """
        识别笔画序列
        
        Args:
            strokes: 笔画列表
            
        Returns:
            RecognitionResult: 识别结果，如果识别失败则返回None
        """
        if not strokes:
            return None
        
        start_time = time.time()
        
        try:
            # 1. 预处理笔画数据
            processed_strokes = self._preprocess_strokes(strokes)
            
            # 2. 转换为图像
            image = self._strokes_to_image(processed_strokes)
            
            # 3. 获取模型
            model = self.recognition_models.get(self.current_language)
            if model is None:
                logger.error(f"No model for language: {self.current_language}")
                return None
            
            # 4. 执行识别
            with torch.no_grad():
                # 准备输入
                input_tensor = torch.from_numpy(image).float().unsqueeze(0).unsqueeze(0)
                
                # 前向传播
                if torch.cuda.is_available():
                    input_tensor = input_tensor.cuda()
                    model = model.cuda()
                
                output = model(input_tensor)
                probs = F.softmax(output, dim=1)
                
                # 获取前N个预测
                top_probs, top_indices = torch.topk(probs, self.max_alternatives, dim=1)
                
                # 转换为文本
                # TODO: 这里需要实际的字符映射表
                char_mapping = self._get_char_mapping(self.current_language)
                
                recognized_text = char_mapping.get(top_indices[0][0].item(), "?")
                alternatives = [char_mapping.get(idx.item(), "?") for idx in top_indices[0]]
                
                confidence = top_probs[0][0].item()
            
            recognition_time = time.time() - start_time
            
            result = RecognitionResult(
                text=recognized_text,
                confidence=confidence,
                alternatives=alternatives,
                strokes_used=strokes,
                recognition_time=recognition_time,
                language=self.current_language
            )
            
            logger.debug(f"Recognized: {recognized_text} (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Recognition failed: {e}")
            return None
    
    def _preprocess_strokes(self, strokes: List[Stroke]) -> List[np.ndarray]:
        """预处理笔画数据"""
        processed = []
        
        for stroke in strokes:
            if len(stroke.points) < self.min_stroke_length:
                continue
            
            # 转换为numpy数组
            points = stroke.to_numpy()
            
            # 平滑处理
            if self.smoothing_window > 1:
                smoothed = []
                for i in range(len(points)):
                    start = max(0, i - self.smoothing_window // 2)
                    end = min(len(points), i + self.smoothing_window // 2 + 1)
                    window = points[start:end]
                    smoothed.append(window.mean(axis=0))
                points = np.array(smoothed)
            
            # 归一化
            x_min, y_min, x_max, y_max = stroke.get_bounding_box()
            if x_max > x_min and y_max > y_min:
                points[:, 0] = (points[:, 0] - x_min) / (x_max - x_min)
                points[:, 1] = (points[:, 1] - y_min) / (y_max - y_min)
            
            processed.append(points)
        
        return processed
    
    def _strokes_to_image(self, strokes: List[np.ndarray]) -> np.ndarray:
        """将笔画转换为图像"""
        # 创建空白图像
        image = np.zeros((self.image_size[1], self.image_size[0]), dtype=np.float32)
        
        for stroke_points in strokes:
            if len(stroke_points) < 2:
                continue
            
            # 将归一化坐标转换为图像坐标
            points = []
            for point in stroke_points:
                x = int(point[0] * (self.image_size[0] - 1))
                y = int(point[1] * (self.image_size[1] - 1))
                pressure = point[2] if len(point) > 2 else 1.0
                points.append((x, y, pressure))
            
            # 绘制笔画（简单的线段连接）
            for i in range(len(points) - 1):
                x1, y1, p1 = points[i]
                x2, y2, p2 = points[i + 1]
                
                # 使用Bresenham算法绘制线段
                line_points = self._bresenham_line(x1, y1, x2, y2)
                for (x, y) in line_points:
                    if 0 <= x < self.image_size[0] and 0 <= y < self.image_size[1]:
                        # 根据压力值设置像素强度
                        intensity = (p1 + p2) / 2.0
                        image[y, x] = max(image[y, x], intensity)
        
        # 归一化到0-1范围
        if image.max() > 0:
            image = image / image.max()
        
        return image
    
    def _bresenham_line(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """Bresenham直线算法"""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
        
        return points
    
    def _get_char_mapping(self, language: str) -> Dict[int, str]:
        """获取字符映射表"""
        # 这里应该从配置文件加载
        if language == "zh-CN":
            # 简单的常用汉字映射
            return {i: chr(0x4E00 + i) for i in range(100)}  # 前100个汉字
        elif language == "en-US":
            # 英文字母和数字
            mapping = {}
            for i in range(26):
                mapping[i] = chr(ord('A') + i)
            for i in range(10):
                mapping[26 + i] = str(i)
            return mapping
        else:
            return {}
    
    def _handle_handwriting_message(self, message: Dict[str, Any]) -> None:
        """处理手写相关消息"""
        action = message.get("action")
        
        if action == "set_language":
            language = message.get("language")
            self.set_language(language)
        elif action == "clear_strokes":
            self.clear_strokes()
        elif action == "get_recognition_history":
            self._send_recognition_history()
    
    def set_language(self, language: str) -> bool:
        """
        设置当前识别语言
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否成功设置
        """
        if language in self.recognition_models:
            self.current_language = language
            logger.info(f"Language set to: {language}")
            
            # 通知其他组件
            self.message_bus.publish("handwriting_language_changed", {
                "language": language,
                "timestamp": time.time()
            })
            
            return True
        else:
            logger.error(f"Unsupported language: {language}")
            return False
    
    def clear_strokes(self) -> None:
        """清空当前笔画"""
        self.current_strokes.clear()
        logger.info("Cleared current strokes")
    
    def _send_recognition_history(self) -> None:
        """发送识别历史"""
        history = [result.to_dict() for result in self.recognition_history]
        
        self.message_bus.publish("handwriting_recognition_history", {
            "history": history,
            "count": len(history),
            "timestamp": time.time()
        })
    
    def recognize_image(self, image_path: str) -> Optional[RecognitionResult]:
        """
        识别手写图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            RecognitionResult: 识别结果
        """
        try:
            # 读取图像
            image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return None
            
            # 预处理图像
            processed_image = self._preprocess_image(image)
            
            # 转换为张量
            input_tensor = torch.from_numpy(processed_image).float().unsqueeze(0).unsqueeze(0)
            
            # 执行识别
            start_time = time.time()
            
            model = self.recognition_models.get(self.current_language)
            if model is None:
                return None
            
            with torch.no_grad():
                if torch.cuda.is_available():
                    input_tensor = input_tensor.cuda()
                    model = model.cuda()
                
                output = model(input_tensor)
                probs = F.softmax(output, dim=1)
                top_prob, top_index = torch.max(probs, dim=1)
            
            recognition_time = time.time() - start_time
            
            # 获取字符映射
            char_mapping = self._get_char_mapping(self.current_language)
            recognized_text = char_mapping.get(top_index.item(), "?")
            
            result = RecognitionResult(
                text=recognized_text,
                confidence=top_prob.item(),
                alternatives=[],
                strokes_used=[],
                recognition_time=recognition_time,
                language=self.current_language
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Image recognition failed: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """预处理图像"""
        # 调整大小
        image = cv2.resize(image, self.image_size)
        
        # 二值化（如果图像不是二值的）
        if len(np.unique(image)) > 2:
            _, image = cv2.threshold(image, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # 归一化
        image = image.astype(np.float32) / 255.0
        
        return image
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取手写识别统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "is_active": self.is_active,
            "current_language": self.current_language,
            "current_strokes_count": len(self.current_strokes),
            "stroke_history_size": len(self.stroke_history),
            "recognition_history_size": len(self.recognition_history),
            "loaded_models": list(self.recognition_models.keys()),
            "confidence_threshold": self.confidence_threshold
        }

