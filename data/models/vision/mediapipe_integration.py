"""
MediaPipe集成 - 手势识别集成
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import time

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

class MediaPipeIntegration:
    """MediaPipe手势识别集成"""
    
    def __init__(self, use_gpu: bool = False):  # MediaPipe通常使用CPU
        self.model_name = "MediaPipe"
        self.version = "1.0.0"
        self.hands = None
        self.pose = None
        self.face_mesh = None
        self.is_loaded = False
        
        # 模型配置
        self.config = {
            'max_hands': 2,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
            'enable_pose_detection': True,
            'enable_face_mesh': True,
            'static_image_mode': False
        }
        
        # 手势定义
        self.gesture_definitions = {
            'fist': [0, 1, 2, 3, 4],  # 所有手指弯曲
            'open_hand': [1, 1, 1, 1, 1],  # 所有手指伸直
            'thumbs_up': [0, 1, 1, 1, 1],  # 拇指伸直，其他手指弯曲
            'thumbs_down': [1, 1, 1, 1, 0],  # 小指伸直，其他手指弯曲
            'victory': [1, 1, 0, 0, 0],  # 食指和中指伸直
            'ok': [0, 0, 1, 1, 1],  # 拇指和食指形成圆圈
            'pointing': [1, 0, 0, 0, 0],  # 食指伸直
            'rock': [1, 1, 0, 0, 1],  # 食指和小指伸直
            'call_me': [0, 0, 0, 0, 1],  # 小指伸直
        }
        
        # 性能统计
        self.stats = {
            'total_hand_detections': 0,
            'total_pose_detections': 0,
            'total_face_detections': 0,
            'average_confidence': 0.0
        }
        
    def load(self) -> bool:
        """加载MediaPipe模型"""
        try:
            print("📦 正在加载MediaPipe模型...")
            
            if MEDIAPIPE_AVAILABLE:
                success = self._load_mediapipe_models()
            else:
                success = self._load_fallback_models()
                
            if success:
                self.is_loaded = True
                print("✅ MediaPipe模型加载成功")
            else:
                print("❌ MediaPipe模型加载失败")
                
            return success
            
        except Exception as e:
            print(f"❌ 加载MediaPipe模型失败: {e}")
            return False
    
    def _load_mediapipe_models(self) -> bool:
        """加载MediaPipe模型"""
        try:
            # 初始化MediaPipe组件
            mp_hands = mp.solutions.hands
            mp_pose = mp.solutions.pose
            mp_face_mesh = mp.solutions.face_mesh
            
            # 创建手部检测器
            self.hands = mp_hands.Hands(
                static_image_mode=self.config['static_image_mode'],
                max_num_hands=self.config['max_hands'],
                min_detection_confidence=self.config['min_detection_confidence'],
                min_tracking_confidence=self.config['min_tracking_confidence']
            )
            
            # 创建姿势检测器
            if self.config['enable_pose_detection']:
                self.pose = mp_pose.Pose(
                    static_image_mode=self.config['static_image_mode'],
                    model_complexity=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            
            # 创建面部网格检测器
            if self.config['enable_face_mesh']:
                self.face_mesh = mp_face_mesh.FaceMesh(
                    static_image_mode=self.config['static_image_mode'],
                    max_num_faces=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            
            return True
            
        except Exception as e:
            print(f"❌ 加载MediaPipe模型失败: {e}")
            return self._load_fallback_models()
    
    def _load_fallback_models(self) -> bool:
        """加载备用模型"""
        try:
            print("⚠️  MediaPipe不可用，使用备用模型")
            self.hands = "fallback_hand_model"
            self.pose = "fallback_pose_model"
            self.face_mesh = "fallback_face_model"
            return True
            
        except Exception as e:
            print(f"❌ 加载备用模型失败: {e}")
            return False
    
    def detect_hands(self, image: np.ndarray) -> Dict[str, Any]:
        """检测手部关键点"""
        if not self.is_loaded:
            success = self.load()
            if not success:
                return self._get_error_result("模型加载失败")
        
        try:
            start_time = time.time()
            
            # 验证输入
            if image is None or image.size == 0:
                return self._get_error_result("输入图像为空")
            
            # 进行手部检测
            if MEDIAPIPE_AVAILABLE and hasattr(self.hands, 'process'):
                detection_result = self._detect_mediapipe_hands(image)
            else:
                detection_result = self._detect_fallback_hands(image)
            
            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_hand_stats(detection_result)
            
            detection_result["processing_time"] = processing_time
            detection_result["success"] = True
            
            return detection_result
            
        except Exception as e:
            print(f"❌ 手部检测失败: {e}")
            return self._get_error_result(str(e))
    
    def _detect_mediapipe_hands(self, image: np.ndarray) -> Dict[str, Any]:
        """使用MediaPipe检测手部"""
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 处理图像
        results = self.hands.process(rgb_image)
        
        detected_hands = []
        
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # 获取手部信息
                handedness = results.multi_handedness[hand_idx].classification[0].label
                confidence = results.multi_handedness[hand_idx].classification[0].score
                
                # 提取关键点坐标
                landmarks = []
                for landmark in hand_landmarks.landmark:
                    landmarks.append({
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    })
                
                # 识别手势
                gesture = self._recognize_gesture(landmarks)
                
                # 计算边界框
                bbox = self._calculate_hand_bbox(landmarks, image.shape)
                
                detected_hands.append({
                    'hand_id': hand_idx,
                    'handedness': handedness,
                    'confidence': confidence,
                    'landmarks': landmarks,
                    'gesture': gesture,
                    'bbox': bbox,
                    'landmark_count': len(landmarks)
                })
        
        return {
            'hands': detected_hands,
            'hand_count': len(detected_hands),
            'image_size': image.shape[:2]
        }
    
    def _detect_fallback_hands(self, image: np.ndarray) -> Dict[str, Any]:
        """使用备用方法检测手部"""
        # 使用肤色检测的简单手部检测
        height, width = image.shape[:2]
        
        # 转换为HSV进行肤色检测
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 肤色范围
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_hands = []
        
        for i, contour in enumerate(contours):
            # 过滤小区域
            area = cv2.contourArea(contour)
            min_area = 0.01 * height * width
            
            if area > min_area and i < self.config['max_hands']:
                # 获取边界框
                x, y, w, h = cv2.boundingRect(contour)
                
                # 扩展边界框
                margin = 0.2
                x_exp = max(0, int(x - w * margin))
                y_exp = max(0, int(y - h * margin))
                w_exp = min(width - x_exp, int(w * (1 + 2 * margin)))
                h_exp = min(height - y_exp, int(h * (1 + 2 * margin)))
                
                bbox = [x_exp, y_exp, x_exp + w_exp, y_exp + h_exp]
                
                # 生成模拟的关键点
                landmarks = self._generate_fallback_landmarks(bbox, image.shape)
                
                # 识别手势
                gesture = self._recognize_gesture(landmarks)
                
                detected_hands.append({
                    'hand_id': i,
                    'handedness': 'Right' if bbox[0] < width / 2 else 'Left',
                    'confidence': min(area / (height * width) * 10, 0.95),
                    'landmarks': landmarks,
                    'gesture': gesture,
                    'bbox': bbox,
                    'landmark_count': len(landmarks)
                })
        
        return {
            'hands': detected_hands,
            'hand_count': len(detected_hands),
            'image_size': image.shape[:2]
        }
    
    def detect_pose(self, image: np.ndarray) -> Dict[str, Any]:
        """检测人体姿势"""
        if not self.is_loaded or not self.config['enable_pose_detection']:
            return self._get_error_result("姿势检测未启用")
        
        try:
            start_time = time.time()
            
            if MEDIAPIPE_AVAILABLE and hasattr(self.pose, 'process'):
                pose_result = self._detect_mediapipe_pose(image)
            else:
                pose_result = self._detect_fallback_pose(image)
            
            processing_time = time.time() - start_time
            self.stats['total_pose_detections'] += 1
            
            pose_result["processing_time"] = processing_time
            pose_result["success"] = True
            
            return pose_result
            
        except Exception as e:
            print(f"❌ 姿势检测失败: {e}")
            return self._get_error_result(str(e))
    
    def _detect_mediapipe_pose(self, image: np.ndarray) -> Dict[str, Any]:
        """使用MediaPipe检测姿势"""
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 处理图像
        results = self.pose.process(rgb_image)
        
        pose_landmarks = []
        
        if results.pose_landmarks:
            for landmark in results.pose_landmarks.landmark:
                pose_landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })
        
        return {
            'pose_landmarks': pose_landmarks,
            'landmark_count': len(pose_landmarks),
            'image_size': image.shape[:2]
        }
    
    def _detect_fallback_pose(self, image: np.ndarray) -> Dict[str, Any]:
        """使用备用方法检测姿势"""
        # 生成模拟的姿势关键点
        height, width = image.shape[:2]
        pose_landmarks = []
        
        # MediaPipe姿势模型的33个关键点
        keypoint_positions = [
            [0.5, 0.1],   # 鼻子
            [0.5, 0.2],   # 右眼
            [0.5, 0.2],   # 左眼
            [0.5, 0.3],   # 右耳
            [0.5, 0.3],   # 左耳
            [0.3, 0.4],   # 右肩
            [0.7, 0.4],   # 左肩
            [0.2, 0.6],   # 右肘
            [0.8, 0.6],   # 左肘
            [0.1, 0.8],   # 右手腕
            [0.9, 0.8],   # 左手腕
            [0.3, 0.9],   # 右髋
            [0.7, 0.9],   # 左髋
            [0.2, 1.1],   # 右膝
            [0.8, 1.1],   # 左膝
            [0.1, 1.3],   # 右脚踝
            [0.9, 1.3],   # 左脚踝
            # ... 其他关键点
        ]
        
        for i, pos in enumerate(keypoint_positions):
            if i >= 33:  # MediaPipe有33个姿势关键点
                break
                
            pose_landmarks.append({
                'x': pos[0],
                'y': min(pos[1], 1.0),  # 确保在图像范围内
                'z': 0.0,
                'visibility': np.random.uniform(0.5, 1.0)
            })
        
        return {
            'pose_landmarks': pose_landmarks,
            'landmark_count': len(pose_landmarks),
            'image_size': image.shape[:2]
        }
    
    def _recognize_gesture(self, landmarks: List[Dict]) -> str:
        """根据关键点识别手势"""
        if len(landmarks) < 21:  # MediaPipe手部模型有21个关键点
            return 'unknown'
        
        # 计算手指状态（0=弯曲, 1=伸直）
        finger_states = []
        
        # 拇指
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_mcp = landmarks[2]
        thumb_state = 1 if thumb_tip['y'] < thumb_ip['y'] else 0
        finger_states.append(thumb_state)
        
        # 其他手指
        finger_tips = [8, 12, 16, 20]  # 食指、中指、无名指、小指指尖
        finger_pips = [6, 10, 14, 18]  # 近端指间关节
        
        for tip_idx, pip_idx in zip(finger_tips, finger_pips):
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            finger_state = 1 if tip['y'] < pip['y'] else 0
            finger_states.append(finger_state)
        
        # 匹配预定义手势
        best_match = 'unknown'
        best_score = 0
        
        for gesture_name, expected_states in self.gesture_definitions.items():
            score = sum(1 for i, state in enumerate(finger_states) 
                       if i < len(expected_states) and state == expected_states[i])
            
            if score > best_score:
                best_score = score
                best_match = gesture_name
        
        return best_match if best_score >= 3 else 'unknown'  # 至少匹配3个手指
    
    def _calculate_hand_bbox(self, landmarks: List[Dict], image_shape: Tuple) -> List[int]:
        """根据关键点计算手部边界框"""
        if not landmarks:
            return [0, 0, 0, 0]
        
        height, width = image_shape[:2]
        
        xs = [lm['x'] for lm in landmarks]
        ys = [lm['y'] for lm in landmarks]
        
        x_min = int(min(xs) * width)
        y_min = int(min(ys) * height)
        x_max = int(max(xs) * width)
        y_max = int(max(ys) * height)
        
        # 添加边距
        margin = 0.1
        x_min = max(0, int(x_min - (x_max - x_min) * margin))
        y_min = max(0, int(y_min - (y_max - y_min) * margin))
        x_max = min(width, int(x_max + (x_max - x_min) * margin))
        y_max = min(height, int(y_max + (y_max - y_min) * margin))
        
        return [x_min, y_min, x_max, y_max]
    
    def _generate_fallback_landmarks(self, bbox: List[int], image_shape: Tuple) -> List[Dict]:
        """生成模拟的手部关键点"""
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        landmarks = []
        
        # MediaPipe手部模型的21个关键点位置（相对坐标）
        relative_positions = [
            [0.5, 0.9],   # 0: 手腕
            [0.5, 0.7],   # 1: 拇指CMC
            [0.4, 0.7],   # 2: 拇指MCP
            [0.3, 0.7],   # 3: 拇指IP
            [0.2, 0.7],   # 4: 拇指指尖
            [0.6, 0.5],   # 5: 食指MCP
            [0.7, 0.4],   # 6: 食指PIP
            [0.8, 0.3],   # 7: 食指DIP
            [0.9, 0.2],   # 8: 食指指尖
            [0.5, 0.5],   # 9: 中指MCP
            [0.5, 0.4],   # 10: 中指PIP
            [0.5, 0.3],   # 11: 中指DIP
            [0.5, 0.2],   # 12: 中指指尖
            [0.4, 0.5],   # 13: 无名指MCP
            [0.3, 0.4],   # 14: 无名指PIP
            [0.2, 0.3],   # 15: 无名指DIP
            [0.1, 0.2],   # 16: 无名指指尖
            [0.3, 0.5],   # 17: 小指MCP
            [0.2, 0.6],   # 18: 小指PIP
            [0.1, 0.7],   # 19: 小指DIP
            [0.0, 0.8]    # 20: 小指指尖
        ]
        
        for pos in relative_positions:
            landmarks.append({
                'x': (x1 + pos[0] * width) / image_shape[1],
                'y': (y1 + pos[1] * height) / image_shape[0],
                'z': np.random.uniform(-0.1, 0.1)
            })
        
        return landmarks
    
    def _update_hand_stats(self, detection_result: Dict[str, Any]):
        """更新手部检测统计"""
        hand_count = detection_result.get('hand_count', 0)
        self.stats['total_hand_detections'] += hand_count
        
        if hand_count > 0:
            avg_confidence = np.mean([hand.get('confidence', 0) for hand in detection_result.get('hands', [])])
            
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
    
    def draw_hands(self, image: np.ndarray, detection_result: Dict[str, Any]) -> np.ndarray:
        """在图像上绘制手部检测结果"""
        result_image = image.copy()
        
        for hand in detection_result.get('hands', []):
            bbox = hand.get('bbox')
            landmarks = hand.get('landmarks', [])
            gesture = hand.get('gesture', 'unknown')
            handedness = hand.get('handedness', 'Unknown')
            confidence = hand.get('confidence', 0.0)
            
            # 绘制边界框
            if bbox and len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                color = (0, 255, 0)  # 绿色
                thickness = 2
                cv2.rectangle(result_image, (x1, y1), (x2, y2), color, thickness)
            
            # 绘制关键点
            for landmark in landmarks:
                x = int(landmark['x'] * image.shape[1])
                y = int(landmark['y'] * image.shape[0])
                cv2.circle(result_image, (x, y), 3, (0, 0, 255), -1)
            
            # 绘制手势标签
            if bbox:
                label = f"{handedness}: {gesture} ({confidence:.2f})"
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
            "mediapipe_available": MEDIAPIPE_AVAILABLE,
            "stats": self.stats,
            "config": self.config,
            "gesture_definitions": list(self.gesture_definitions.keys())
        }
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.is_loaded