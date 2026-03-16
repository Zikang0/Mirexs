"""
物体检测 - 检测场景中的物体
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

class ObjectDetection:
    """物体检测模型"""
    
    def __init__(self, use_gpu: bool = True):
        self.model_name = "ObjectDetection"
        self.version = "1.0.0"
        self.model = None
        self.is_loaded = False
        self.use_gpu = use_gpu and TORCH_AVAILABLE
        
        # COCO数据集类别（常用物体）
        self.coco_classes = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        
        # 中文类别标签
        self.class_labels_zh = {
            'person': '人', 'bicycle': '自行车', 'car': '汽车', 'motorcycle': '摩托车',
            'airplane': '飞机', 'bus': '公交车', 'train': '火车', 'truck': '卡车',
            'boat': '船', 'traffic light': '交通灯', 'fire hydrant': '消防栓',
            'stop sign': '停止标志', 'parking meter': '停车计时器', 'bench': '长椅',
            'bird': '鸟', 'cat': '猫', 'dog': '狗', 'horse': '马', 'sheep': '羊',
            'cow': '牛', 'elephant': '大象', 'bear': '熊', 'zebra': '斑马',
            'giraffe': '长颈鹿', 'backpack': '背包', 'umbrella': '雨伞', 'handbag': '手提包',
            'tie': '领带', 'suitcase': '手提箱', 'frisbee': '飞盘', 'skis': '滑雪板',
            'snowboard': '滑雪板', 'sports ball': '运动球', 'kite': '风筝',
            'baseball bat': '棒球棒', 'baseball glove': '棒球手套', 'skateboard': '滑板',
            'surfboard': '冲浪板', 'tennis racket': '网球拍', 'bottle': '瓶子',
            'wine glass': '酒杯', 'cup': '杯子', 'fork': '叉子', 'knife': '刀',
            'spoon': '勺子', 'bowl': '碗', 'banana': '香蕉', 'apple': '苹果',
            'sandwich': '三明治', 'orange': '橙子', 'broccoli': '西兰花', 'carrot': '胡萝卜',
            'hot dog': '热狗', 'pizza': '披萨', 'donut': '甜甜圈', 'cake': '蛋糕',
            'chair': '椅子', 'couch': '沙发', 'potted plant': '盆栽', 'bed': '床',
            'dining table': '餐桌', 'toilet': '马桶', 'tv': '电视', 'laptop': '笔记本电脑',
            'mouse': '鼠标', 'remote': '遥控器', 'keyboard': '键盘', 'cell phone': '手机',
            'microwave': '微波炉', 'oven': '烤箱', 'toaster': '烤面包机', 'sink': '水槽',
            'refrigerator': '冰箱', 'book': '书', 'clock': '时钟', 'vase': '花瓶',
            'scissors': '剪刀', 'teddy bear': '泰迪熊', 'hair drier': '吹风机',
            'toothbrush': '牙刷'
        }
        
        # 模型配置
        self.config = {
            'model_type': 'yolov5',  # yolov5, faster_rcnn, ssd
            'confidence_threshold': 0.5,
            'nms_threshold': 0.4,
            'input_size': (640, 640),
            'max_detections': 100,
            'enable_segmentation': False
        }
        
        # 性能统计
        self.stats = {
            'total_detections': 0,
            'average_confidence': 0.0,
            'class_distribution': {cls: 0 for cls in self.coco_classes}
        }
        
    def load(self, model_path: Optional[str] = None) -> bool:
        """加载物体检测模型"""
        try:
            print("📦 正在加载物体检测模型...")
            
            if TORCH_AVAILABLE:
                success = self._load_yolov5()
            else:
                success = self._load_opencv_dnn()
                
            if success:
                self.is_loaded = True
                print("✅ 物体检测模型加载成功")
            else:
                print("❌ 物体检测模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载物体检测模型失败: {e}")
            return False
    
    def _load_yolov5(self) -> bool:
        """加载YOLOv5模型"""
        try:
            # 尝试导入YOLOv5
            try:
                import torch.hub
                
                # 加载预训练的YOLOv5模型
                self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                
                # 设置设备
                device = 'cuda' if self.use_gpu and torch.cuda.is_available() else 'cpu'
                self.model.to(device)
                
                # 设置推理参数
                self.model.conf = self.config['confidence_threshold']
                self.model.iou = self.config['nms_threshold']
                
                return True
                
            except ImportError:
                print("❌ YOLOv5未安装，使用OpenCV DNN作为备选")
                return self._load_opencv_dnn()
                
        except Exception as e:
            print(f"❌ 加载YOLOv5失败: {e}")
            return self._load_opencv_dnn()
    
    def _load_opencv_dnn(self) -> bool:
        """加载OpenCV DNN物体检测模型"""
        try:
            # 加载YOLO模型（需要模型文件）
            model_path = "models/object_detection/"
            os.makedirs(model_path, exist_ok=True)
            
            # 这里模拟模型加载，实际项目中需要真实的模型文件
            print("⚠️  使用模拟物体检测模型")
            self.model = "opencv_yolo_model"
            return True
            
        except Exception as e:
            print(f"❌ 加载OpenCV DNN失败: {e}")
            return False
    
    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """检测图像中的物体"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return {"success": False, "objects": [], "error": "模型加载失败"}
        
        try:
            start_time = time.time()
            
            # 验证输入
            if image is None or image.size == 0:
                return {"success": False, "objects": [], "error": "输入图像为空"}
            
            # 预处理图像
            processed_image = self._preprocess_image(image)
            original_height, original_width = image.shape[:2]
            
            # 执行物体检测
            if TORCH_AVAILABLE and hasattr(self.model, 'predict'):
                detection_results = self._detect_yolov5(processed_image)
            else:
                detection_results = self._detect_opencv(processed_image)
            
            # 后处理结果
            objects = self._postprocess_detections(
                detection_results, 
                original_width, original_height
            )
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_stats(objects, processing_time)
            
            return {
                "success": True,
                "objects": objects,
                "count": len(objects),
                "processing_time": processing_time,
                "image_size": {"width": original_width, "height": original_height}
            }
            
        except Exception as e:
            print(f"❌ 物体检测失败: {e}")
            return {"success": False, "objects": [], "error": str(e)}
    
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
        
        return image
    
    def _detect_yolov5(self, image: np.ndarray) -> List[Dict]:
        """使用YOLOv5进行物体检测"""
        # 推理
        results = self.model(image)
        
        # 解析结果
        detections = []
        
        for *xyxy, conf, cls in results.xyxy[0]:
            x1, y1, x2, y2 = map(int, xyxy)
            confidence = conf.item()
            class_id = int(cls.item())
            class_name = self.coco_classes[class_id] if class_id < len(self.coco_classes) else f"class_{class_id}"
            
            detections.append({
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'class_id': class_id,
                'class_name': class_name
            })
        
        return detections
    
    def _detect_opencv(self, image: np.ndarray) -> List[Dict]:
        """使用OpenCV进行物体检测（模拟实现）"""
        # 模拟物体检测结果
        height, width = image.shape[:2]
        detections = []
        
        # 随机生成一些检测结果
        num_detections = min(self.config['max_detections'], np.random.randint(3, 10))
        
        for i in range(num_detections):
            # 随机选择类别
            class_id = np.random.randint(0, len(self.coco_classes))
            class_name = self.coco_classes[class_id]
            
            # 生成随机但合理的边界框
            bbox_width = np.random.randint(50, min(400, width // 2))
            bbox_height = np.random.randint(50, min(400, height // 2))
            x1 = np.random.randint(0, width - bbox_width)
            y1 = np.random.randint(0, height - bbox_height)
            x2 = x1 + bbox_width
            y2 = y1 + bbox_height
            
            # 生成置信度
            confidence = np.random.uniform(0.5, 0.95)
            
            detections.append({
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'class_id': class_id,
                'class_name': class_name
            })
        
        return detections
    
    def _postprocess_detections(self, detections: List[Dict], 
                              orig_width: int, orig_height: int) -> List[Dict]:
        """后处理检测结果"""
        processed_objects = []
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection['class_name']
            class_id = detection['class_id']
            
            # 确保边界框在图像范围内
            x1, y1, x2, y2 = bbox
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_width, x2), min(orig_height, y2)
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            # 计算边界框属性
            bbox_width = x2 - x1
            bbox_height = y2 - y1
            bbox_area = bbox_width * bbox_height
            bbox_center = [x1 + bbox_width // 2, y1 + bbox_height // 2]
            
            # 创建物体数据
            object_data = {
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'class_id': class_id,
                'class_name': class_name,
                'class_name_zh': self.class_labels_zh.get(class_name, class_name),
                'area': bbox_area,
                'center': bbox_center,
                'width': bbox_width,
                'height': bbox_height
            }
            
            processed_objects.append(object_data)
        
        # 按置信度排序
        processed_objects.sort(key=lambda x: x['confidence'], reverse=True)
        
        # 限制最大检测数量
        if len(processed_objects) > self.config['max_detections']:
            processed_objects = processed_objects[:self.config['max_detections']]
        
        return processed_objects
    
    def _update_stats(self, objects: List[Dict], processing_time: float):
        """更新性能统计"""
        self.stats['total_detections'] += len(objects)
        
        if objects:
            avg_conf = sum(obj['confidence'] for obj in objects) / len(objects)
            # 指数移动平均
            alpha = 0.1
            self.stats['average_confidence'] = (
                alpha * avg_conf + (1 - alpha) * self.stats['average_confidence']
            )
            
            # 更新类别分布
            for obj in objects:
                class_name = obj['class_name']
                if class_name in self.stats['class_distribution']:
                    self.stats['class_distribution'][class_name] += 1
    
    def get_class_distribution(self) -> Dict[str, float]:
        """获取类别分布统计"""
        total = self.stats['total_detections']
        if total == 0:
            return {cls: 0.0 for cls in self.coco_classes}
        
        distribution = {}
        for class_name, count in self.stats['class_distribution'].items():
            distribution[class_name] = count / total
            
        return distribution
    
    def draw_detections(self, image: np.ndarray, objects: List[Dict], 
                       show_labels: bool = True) -> np.ndarray:
        """在图像上绘制检测结果"""
        result_image = image.copy()
        
        # 为不同类别生成颜色
        colors = {}
        for class_name in set(obj['class_name'] for obj in objects):
            colors[class_name] = tuple(np.random.randint(0, 255, 3).tolist())
        
        for i, obj in enumerate(objects):
            bbox = obj['bbox']
            class_name = obj['class_name']
            class_name_zh = obj['class_name_zh']
            confidence = obj['confidence']
            
            color = colors.get(class_name, (0, 255, 0))
            thickness = 2
            
            # 绘制边界框
            x1, y1, x2, y2 = bbox
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            if show_labels:
                # 绘制标签
                label = f"{class_name_zh} {confidence:.2f}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                
                # 标签背景
                cv2.rectangle(result_image,
                            (x1, y1 - label_size[1] - 10),
                            (x1 + label_size[0], y1),
                            color, -1)
                
                # 标签文字
                cv2.putText(result_image, label,
                          (x1, y1 - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return result_image
    
    def filter_by_class(self, objects: List[Dict], class_names: List[str]) -> List[Dict]:
        """按类别过滤检测结果"""
        return [obj for obj in objects if obj['class_name'] in class_names]
    
    def filter_by_confidence(self, objects: List[Dict], min_confidence: float) -> List[Dict]:
        """按置信度过滤检测结果"""
        return [obj for obj in objects if obj['confidence'] >= min_confidence]
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "is_loaded": self.is_loaded,
            "num_classes": len(self.coco_classes),
            "use_gpu": self.use_gpu,
            "stats": self.stats,
            "config": self.config
        }
    
    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded
