"""
OpenCV工具 - 计算机视觉工具函数
"""

import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
import time
import os

class OpenCVUtils:
    """OpenCV工具函数库"""
    
    def __init__(self):
        self.version = "1.0.0"
        
        # 图像处理配置
        self.config = {
            'default_blur_kernel': (5, 5),
            'default_morph_kernel': (3, 3),
            'canny_threshold1': 50,
            'canny_threshold2': 150,
            'harris_block_size': 2,
            'harris_k_size': 3,
            'harris_k': 0.04
        }
    
    # ===== 图像基础操作 =====
    
    def read_image(self, image_path: str, flags: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
        """读取图像文件"""
        try:
            if not os.path.exists(image_path):
                print(f"❌ 图像文件不存在: {image_path}")
                return None
            
            image = cv2.imread(image_path, flags)
            if image is None:
                print(f"❌ 无法读取图像文件: {image_path}")
                return None
            
            print(f"✅ 成功读取图像: {image_path} ({image.shape})")
            return image
            
        except Exception as e:
            print(f"❌ 读取图像失败: {e}")
            return None
    
    def save_image(self, image: np.ndarray, save_path: str, 
                   quality: int = 95) -> bool:
        """保存图像文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 根据文件扩展名选择参数
            ext = os.path.splitext(save_path)[1].lower()
            
            if ext in ['.jpg', '.jpeg']:
                success = cv2.imwrite(save_path, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            elif ext == '.png':
                success = cv2.imwrite(save_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 9 - quality // 10])
            else:
                success = cv2.imwrite(save_path, image)
            
            if success:
                print(f"✅ 图像保存成功: {save_path}")
            else:
                print(f"❌ 图像保存失败: {save_path}")
            
            return success
            
        except Exception as e:
            print(f"❌ 保存图像失败: {e}")
            return False
    
    def resize_image(self, image: np.ndarray, 
                    size: Tuple[int, int],
                    interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
        """调整图像大小"""
        return cv2.resize(image, size, interpolation=interpolation)
    
    def resize_image_by_scale(self, image: np.ndarray, 
                             scale: float,
                             interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
        """按比例调整图像大小"""
        if scale <= 0:
            raise ValueError("缩放比例必须大于0")
        
        new_width = int(image.shape[1] * scale)
        new_height = int(image.shape[0] * scale)
        
        return cv2.resize(image, (new_width, new_height), interpolation=interpolation)
    
    def crop_image(self, image: np.ndarray, 
                  roi: Tuple[int, int, int, int]) -> np.ndarray:
        """裁剪图像区域"""
        x1, y1, x2, y2 = roi
        
        # 确保坐标在图像范围内
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(image.shape[1], x2), min(image.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            raise ValueError("无效的裁剪区域")
        
        return image[y1:y2, x1:x2]
    
    def rotate_image(self, image: np.ndarray, 
                    angle: float,
                    center: Optional[Tuple[int, int]] = None,
                    scale: float = 1.0) -> np.ndarray:
        """旋转图像"""
        height, width = image.shape[:2]
        
        if center is None:
            center = (width // 2, height // 2)
        
        # 计算旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)
        
        # 执行旋转
        rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height))
        
        return rotated_image
    
    # ===== 图像增强和滤波 =====
    
    def adjust_brightness_contrast(self, image: np.ndarray,
                                 brightness: float = 0.0,
                                 contrast: float = 1.0) -> np.ndarray:
        """调整亮度和对比度"""
        # 应用亮度和对比度调整
        adjusted = image.astype(np.float32)
        adjusted = adjusted * contrast + brightness
        adjusted = np.clip(adjusted, 0, 255)
        
        return adjusted.astype(np.uint8)
    
    def apply_gaussian_blur(self, image: np.ndarray,
                          kernel_size: Tuple[int, int] = None,
                          sigma_x: float = 0) -> np.ndarray:
        """应用高斯模糊"""
        if kernel_size is None:
            kernel_size = self.config['default_blur_kernel']
        
        return cv2.GaussianBlur(image, kernel_size, sigma_x)
    
    def apply_median_blur(self, image: np.ndarray,
                        kernel_size: int = 5) -> np.ndarray:
        """应用中值模糊"""
        return cv2.medianBlur(image, kernel_size)
    
    def apply_bilateral_filter(self, image: np.ndarray,
                             d: int = 9,
                             sigma_color: float = 75,
                             sigma_space: float = 75) -> np.ndarray:
        """应用双边滤波"""
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)
    
    def sharpen_image(self, image: np.ndarray,
                     strength: float = 1.0) -> np.ndarray:
        """图像锐化"""
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1],
                          [-1, -1, -1]]) * strength
        
        return cv2.filter2D(image, -1, kernel)
    
    # ===== 颜色空间转换 =====
    
    def convert_color_space(self, image: np.ndarray,
                          conversion: int) -> np.ndarray:
        """转换颜色空间"""
        return cv2.cvtColor(image, conversion)
    
    def rgb_to_hsv(self, image: np.ndarray) -> np.ndarray:
        """RGB转HSV"""
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    def hsv_to_rgb(self, image: np.ndarray) -> np.ndarray:
        """HSV转RGB"""
        return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
    
    def rgb_to_gray(self, image: np.ndarray) -> np.ndarray:
        """RGB转灰度"""
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    def rgb_to_lab(self, image: np.ndarray) -> np.ndarray:
        """RGB转Lab"""
        return cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
    
    # ===== 边缘检测 =====
    
    def detect_edges_canny(self, image: np.ndarray,
                         threshold1: float = None,
                         threshold2: float = None,
                         aperture_size: int = 3) -> np.ndarray:
        """Canny边缘检测"""
        if threshold1 is None:
            threshold1 = self.config['canny_threshold1']
        if threshold2 is None:
            threshold2 = self.config['canny_threshold2']
        
        # 如果是彩色图像，先转换为灰度
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
        else:
            gray = image
        
        return cv2.Canny(gray, threshold1, threshold2, apertureSize=aperture_size)
    
    def detect_edges_sobel(self, image: np.ndarray,
                         dx: int = 1, dy: int = 1,
                         ksize: int = 3) -> np.ndarray:
        """Sobel边缘检测"""
        # 如果是彩色图像，先转换为灰度
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
        else:
            gray = image
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, dx, 0, ksize=ksize)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, dy, ksize=ksize)
        
        # 计算梯度幅值
        magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        magnitude = np.uint8(255 * magnitude / np.max(magnitude))
        
        return magnitude
    
    # ===== 特征检测 =====
    
    def detect_corners_harris(self, image: np.ndarray,
                            block_size: int = None,
                            k_size: int = None,
                            k: float = None) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
        """Harris角点检测"""
        if block_size is None:
            block_size = self.config['harris_block_size']
        if k_size is None:
            k_size = self.config['harris_k_size']
        if k is None:
            k = self.config['harris_k']
        
        # 转换为灰度
        gray = self.rgb_to_gray(image) if len(image.shape) == 3 else image
        
        # Harris角点检测
        corners = cv2.cornerHarris(gray, block_size, k_size, k)
        
        # 寻找角点位置
        corners = cv2.dilate(corners, None)
        corner_positions = np.argwhere(corners > 0.01 * corners.max())
        corner_positions = [(pt[1], pt[0]) for pt in corner_positions]  # (x, y)格式
        
        return corners, corner_positions
    
    def detect_keypoints_orb(self, image: np.ndarray,
                           n_features: int = 500) -> Tuple[Any, Any]:
        """ORB特征点检测"""
        # 转换为灰度
        gray = self.rgb_to_gray(image) if len(image.shape) == 3 else image
        
        # 创建ORB检测器
        orb = cv2.ORB_create(nfeatures=n_features)
        
        # 检测关键点和描述符
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        
        return keypoints, descriptors
    
    def detect_keypoints_sift(self, image: np.ndarray,
                            n_features: int = 0) -> Tuple[Any, Any]:
        """SIFT特征点检测"""
        try:
            # 转换为灰度
            gray = self.rgb_to_gray(image) if len(image.shape) == 3 else image
            
            # 创建SIFT检测器
            sift = cv2.SIFT_create(nfeatures=n_features)
            
            # 检测关键点和描述符
            keypoints, descriptors = sift.detectAndCompute(gray, None)
            
            return keypoints, descriptors
            
        except Exception as e:
            print(f"❌ SIFT特征检测失败: {e}")
            return [], None
    
    # ===== 形态学操作 =====
    
    def apply_morphology(self, image: np.ndarray,
                       operation: int,
                       kernel: np.ndarray = None,
                       iterations: int = 1) -> np.ndarray:
        """应用形态学操作"""
        if kernel is None:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
                                             self.config['default_morph_kernel'])
        
        return cv2.morphologyEx(image, operation, kernel, iterations=iterations)
    
    def erode_image(self, image: np.ndarray,
                   kernel: np.ndarray = None,
                   iterations: int = 1) -> np.ndarray:
        """图像腐蚀"""
        if kernel is None:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
                                             self.config['default_morph_kernel'])
        
        return cv2.erode(image, kernel, iterations=iterations)
    
    def dilate_image(self, image: np.ndarray,
                    kernel: np.ndarray = None,
                    iterations: int = 1) -> np.ndarray:
        """图像膨胀"""
        if kernel is None:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, 
                                             self.config['default_morph_kernel'])
        
        return cv2.dilate(image, kernel, iterations=iterations)
    
    def open_image(self, image: np.ndarray,
                  kernel: np.ndarray = None,
                  iterations: int = 1) -> np.ndarray:
        """开运算（先腐蚀后膨胀）"""
        return self.apply_morphology(image, cv2.MORPH_OPEN, kernel, iterations)
    
    def close_image(self, image: np.ndarray,
                   kernel: np.ndarray = None,
                   iterations: int = 1) -> np.ndarray:
        """闭运算（先膨胀后腐蚀）"""
        return self.apply_morphology(image, cv2.MORPH_CLOSE, kernel, iterations)
    
    # ===== 轮廓检测 =====
    
    def find_contours(self, image: np.ndarray,
                     mode: int = cv2.RETR_EXTERNAL,
                     method: int = cv2.CHAIN_APPROX_SIMPLE) -> Tuple[List[np.ndarray], Any]:
        """查找轮廓"""
        # 确保是二值图像
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        else:
            binary = image
        
        contours, hierarchy = cv2.findContours(binary, mode, method)
        return contours, hierarchy
    
    def draw_contours(self, image: np.ndarray,
                     contours: List[np.ndarray],
                     contour_index: int = -1,
                     color: Tuple[int, int, int] = (0, 255, 0),
                     thickness: int = 2) -> np.ndarray:
        """绘制轮廓"""
        result = image.copy()
        cv2.drawContours(result, contours, contour_index, color, thickness)
        return result
    
    def get_contour_properties(self, contour: np.ndarray) -> Dict[str, Any]:
        """获取轮廓属性"""
        properties = {}
        
        # 面积
        properties['area'] = cv2.contourArea(contour)
        
        # 周长
        properties['perimeter'] = cv2.arcLength(contour, True)
        
        # 边界框
        x, y, w, h = cv2.boundingRect(contour)
        properties['bbox'] = (x, y, w, h)
        
        # 最小外接矩形
        rect = cv2.minAreaRect(contour)
        properties['min_area_rect'] = rect
        properties['min_area_bbox'] = cv2.boxPoints(rect).astype(int)
        
        # 最小外接圆
        (x, y), radius = cv2.minEnclosingCircle(contour)
        properties['min_enclosing_circle'] = ((x, y), radius)
        
        # 轮廓近似
        epsilon = 0.02 * properties['perimeter']
        approx = cv2.approxPolyDP(contour, epsilon, True)
        properties['approx_vertices'] = len(approx)
        
        # 凸包
        hull = cv2.convexHull(contour)
        properties['hull_area'] = cv2.contourArea(hull)
        properties['solidity'] = properties['area'] / properties['hull_area'] if properties['hull_area'] > 0 else 0
        
        # 纵横比
        properties['aspect_ratio'] = w / h if h > 0 else 0
        
        return properties
    
    # ===== 图像分割 =====
    
    def apply_threshold(self, image: np.ndarray,
                       threshold_value: int = 127,
                       max_value: int = 255,
                       method: int = cv2.THRESH_BINARY) -> np.ndarray:
        """应用阈值分割"""
        # 如果是彩色图像，先转换为灰度
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, threshold_value, max_value, method)
        return binary
    
    def apply_adaptive_threshold(self, image: np.ndarray,
                               max_value: int = 255,
                               method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               block_size: int = 11,
                               constant: float = 2) -> np.ndarray:
        """应用自适应阈值分割"""
        # 如果是彩色图像，先转换为灰度
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
        else:
            gray = image
        
        binary = cv2.adaptiveThreshold(gray, max_value, method, 
                                      cv2.THRESH_BINARY, block_size, constant)
        return binary
    
    def apply_otsu_threshold(self, image: np.ndarray,
                           max_value: int = 255) -> np.ndarray:
        """应用Otsu阈值分割"""
        # 如果是彩色图像，先转换为灰度
        if len(image.shape) == 3:
            gray = self.rgb_to_gray(image)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 0, max_value, 
                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    # ===== 图像金字塔 =====
    
    def build_gaussian_pyramid(self, image: np.ndarray,
                             levels: int = 4) -> List[np.ndarray]:
        """构建高斯金字塔"""
        pyramid = [image]
        
        for i in range(levels - 1):
            pyramid.append(cv2.pyrDown(pyramid[-1]))
        
        return pyramid
    
    def build_laplacian_pyramid(self, image: np.ndarray,
                              levels: int = 4) -> List[np.ndarray]:
        """构建拉普拉斯金字塔"""
        gaussian_pyramid = self.build_gaussian_pyramid(image, levels)
        laplacian_pyramid = []
        
        for i in range(levels - 1):
            size = (gaussian_pyramid[i].shape[1], gaussian_pyramid[i].shape[0])
            expanded = cv2.pyrUp(gaussian_pyramid[i + 1], dstsize=size)
            laplacian = cv2.subtract(gaussian_pyramid[i], expanded)
            laplacian_pyramid.append(laplacian)
        
        laplacian_pyramid.append(gaussian_pyramid[-1])
        return laplacian_pyramid
    
    # ===== 工具函数 =====
    
    def create_blank_image(self, width: int, height: int,
                          channels: int = 3,
                          color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """创建空白图像"""
        if channels == 1:
            image = np.zeros((height, width), dtype=np.uint8)
        else:
            image = np.zeros((height, width, channels), dtype=np.uint8)
        
        if color != (0, 0, 0):
            image[:] = color
        
        return image
    
    def blend_images(self, image1: np.ndarray, image2: np.ndarray,
                    alpha: float = 0.5) -> np.ndarray:
        """图像混合"""
        # 确保图像大小相同
        if image1.shape != image2.shape:
            image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))
        
        blended = cv2.addWeighted(image1, alpha, image2, 1 - alpha, 0)
        return blended
    
    def add_text(self, image: np.ndarray, text: str,
                position: Tuple[int, int],
                font: int = cv2.FONT_HERSHEY_SIMPLEX,
                font_scale: float = 1.0,
                color: Tuple[int, int, int] = (255, 255, 255),
                thickness: int = 2) -> np.ndarray:
        """在图像上添加文字"""
        result = image.copy()
        cv2.putText(result, text, position, font, font_scale, color, thickness)
        return result
    
    def add_rectangle(self, image: np.ndarray,
                     pt1: Tuple[int, int], pt2: Tuple[int, int],
                     color: Tuple[int, int, int] = (0, 255, 0),
                     thickness: int = 2) -> np.ndarray:
        """在图像上添加矩形"""
        result = image.copy()
        cv2.rectangle(result, pt1, pt2, color, thickness)
        return result
    
    def add_circle(self, image: np.ndarray,
                  center: Tuple[int, int], radius: int,
                  color: Tuple[int, int, int] = (0, 255, 0),
                  thickness: int = 2) -> np.ndarray:
        """在图像上添加圆形"""
        result = image.copy()
        cv2.circle(result, center, radius, color, thickness)
        return result
    
    def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """获取图像信息"""
        info = {
            'shape': image.shape,
            'size': image.size,
            'dtype': str(image.dtype),
            'min_value': float(np.min(image)),
            'max_value': float(np.max(image)),
            'mean_value': float(np.mean(image)),
            'std_value': float(np.std(image))
        }
        
        if len(image.shape) == 3:
            info['channels'] = image.shape[2]
            info['color_type'] = 'Color'
        else:
            info['channels'] = 1
            info['color_type'] = 'Grayscale'
        
        return info
    
    def compare_images(self, image1: np.ndarray, image2: np.ndarray) -> Dict[str, float]:
        """比较两个图像的相似度"""
        # 确保图像大小相同
        if image1.shape != image2.shape:
            image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))
        
        # 计算MSE（均方误差）
        mse = np.mean((image1.astype(float) - image2.astype(float)) ** 2)
        
        # 计算PSNR（峰值信噪比）
        if mse == 0:
            psnr = float('inf')
        else:
            psnr = 20 * np.log10(255.0 / np.sqrt(mse))
        
        # 计算SSIM（结构相似性）
        from skimage.metrics import structural_similarity as ssim
        if len(image1.shape) == 3:
            ssim_value = ssim(image1, image2, channel_axis=2, data_range=255)
        else:
            ssim_value = ssim(image1, image2, data_range=255)
        
        return {
            'mse': float(mse),
            'psnr': float(psnr),
            'ssim': float(ssim_value)
        }
    
    def get_version_info(self) -> Dict[str, str]:
        """获取版本信息"""
        return {
            'opencv_version': cv2.__version__,
            'numpy_version': np.__version__,
            'utils_version': self.version
        }