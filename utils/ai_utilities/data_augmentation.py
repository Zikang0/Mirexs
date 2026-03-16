"""
数据增强模块

提供AI模型训练中的数据增强工具。
"""

import numpy as np
import random
from typing import List, Dict, Any, Optional, Union, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import cv2


class ImageAugmentation:
    """图像增强类"""
    
    @staticmethod
    def random_rotation(image: Image.Image, degrees: float = 30) -> Image.Image:
        """随机旋转图像
        
        Args:
            image: 输入图像
            degrees: 最大旋转角度
            
        Returns:
            旋转后的图像
        """
        angle = random.uniform(-degrees, degrees)
        return image.rotate(angle, expand=True)
    
    @staticmethod
    def random_flip(image: Image.Image, horizontal: bool = True, 
                   vertical: bool = False) -> Image.Image:
        """随机翻转图像
        
        Args:
            image: 输入图像
            horizontal: 是否水平翻转
            vertical: 是否垂直翻转
            
        Returns:
            翻转后的图像
        """
        if horizontal and random.random() > 0.5:
            image = image.transpose(Image.FLIP_LEFT_RIGHT)
        if vertical and random.random() > 0.5:
            image = image.transpose(Image.FLIP_TOP_BOTTOM)
        return image
    
    @staticmethod
    def random_crop(image: Image.Image, crop_ratio: float = 0.8) -> Image.Image:
        """随机裁剪图像
        
        Args:
            image: 输入图像
            crop_ratio: 裁剪比例
            
        Returns:
            裁剪后的图像
        """
        width, height = image.size
        crop_width = int(width * crop_ratio)
        crop_height = int(height * crop_ratio)
        
        left = random.randint(0, width - crop_width)
        top = random.randint(0, height - crop_height)
        right = left + crop_width
        bottom = top + crop_height
        
        return image.crop((left, top, right, bottom))
    
    @staticmethod
    def color_jitter(image: Image.Image, brightness: float = 0.2, 
                    contrast: float = 0.2, saturation: float = 0.2, 
                    hue: float = 0.1) -> Image.Image:
        """颜色抖动
        
        Args:
            image: 输入图像
            brightness: 亮度调整范围
            contrast: 对比度调整范围
            saturation: 饱和度调整范围
            hue: 色相调整范围
            
        Returns:
            调整后的图像
        """
        # 亮度调整
        enhancer = ImageEnhance.Brightness(image)
        factor = random.uniform(1 - brightness, 1 + brightness)
        image = enhancer.enhance(factor)
        
        # 对比度调整
        enhancer = ImageEnhance.Contrast(image)
        factor = random.uniform(1 - contrast, 1 + contrast)
        image = enhancer.enhance(factor)
        
        # 饱和度调整
        enhancer = ImageEnhance.Color(image)
        factor = random.uniform(1 - saturation, 1 + saturation)
        image = enhancer.enhance(factor)
        
        return image
    
    @staticmethod
    def gaussian_blur(image: Image.Image, radius: float = 1.0) -> Image.Image:
        """高斯模糊
        
        Args:
            image: 输入图像
            radius: 模糊半径
            
        Returns:
            模糊后的图像
        """
        radius = random.uniform(0.1, radius)
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    
    @staticmethod
    def add_noise(image: Image.Image, noise_factor: float = 0.1) -> Image.Image:
        """添加噪声
        
        Args:
            image: 输入图像
            noise_factor: 噪声强度
            
        Returns:
            添加噪声后的图像
        """
        img_array = np.array(image)
        noise = np.random.normal(0, noise_factor * 255, img_array.shape)
        noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy_img)


class TextAugmentation:
    """文本增强类"""
    
    @staticmethod
    def synonym_replacement(text: str, synonym_dict: Dict[str, List[str]], 
                          n: int = 1) -> str:
        """同义词替换
        
        Args:
            text: 输入文本
            synonym_dict: 同义词字典
            n: 替换次数
            
        Returns:
            替换后的文本
        """
        words = text.split()
        words_modified = words.copy()
        
        for _ in range(n):
            # 随机选择一个位置
            idx = random.randint(0, len(words_modified) - 1)
            word = words_modified[idx].lower()
            
            # 查找同义词
            if word in synonym_dict:
                synonyms = synonym_dict[word]
                if synonyms:
                    replacement = random.choice(synonyms)
                    words_modified[idx] = replacement
        
        return ' '.join(words_modified)
    
    @staticmethod
    def random_insertion(text: str, synonym_dict: Dict[str, List[str]], 
                        n: int = 1) -> str:
        """随机插入
        
        Args:
            text: 输入文本
            synonym_dict: 同义词字典
            n: 插入次数
            
        Returns:
            插入后的文本
        """
        words = text.split()
        
        for _ in range(n):
            # 随机选择一个词
            word = random.choice(words)
            word_lower = word.lower()
            
            # 查找同义词
            if word_lower in synonym_dict:
                synonyms = synonym_dict[word_lower]
                if synonyms:
                    synonym = random.choice(synonyms)
                    # 随机插入位置
                    insert_pos = random.randint(0, len(words))
                    words.insert(insert_pos, synonym)
        
        return ' '.join(words)
    
    @staticmethod
    def random_swap(text: str, n: int = 1) -> str:
        """随机交换
        
        Args:
            text: 输入文本
            n: 交换次数
            
        Returns:
            交换后的文本
        """
        words = text.split()
        
        for _ in range(n):
            if len(words) < 2:
                break
            
            # 随机选择两个不同位置
            idx1, idx2 = random.sample(range(len(words)), 2)
            words[idx1], words[idx2] = words[idx2], words[idx1]
        
        return ' '.join(words)
    
    @staticmethod
    def random_deletion(text: str, p: float = 0.1) -> str:
        """随机删除
        
        Args:
            text: 输入文本
            p: 删除概率
            
        Returns:
            删除后的文本
        """
        words = text.split()
        words_modified = [word for word in words if random.random() > p]
        
        # 确保至少保留一个词
        if not words_modified:
            words_modified = [random.choice(words)]
        
        return ' '.join(words_modified)


class AudioAugmentation:
    """音频增强类"""
    
    @staticmethod
    def add_noise(audio: np.ndarray, noise_factor: float = 0.01) -> np.ndarray:
        """添加噪声
        
        Args:
            audio: 音频数据
            noise_factor: 噪声强度
            
        Returns:
            添加噪声后的音频
        """
        noise = np.random.normal(0, noise_factor, audio.shape)
        return audio + noise
    
    @staticmethod
    def time_stretch(audio: np.ndarray, rate: float = 1.0) -> np.ndarray:
        """时间拉伸
        
        Args:
            audio: 音频数据
            rate: 拉伸比例
            
        Returns:
            拉伸后的音频
        """
        if rate == 1.0:
            return audio
        
        # 简单的重采样方法
        new_length = int(len(audio) / rate)
        indices = np.linspace(0, len(audio) - 1, new_length)
        return np.interp(indices, np.arange(len(audio)), audio)
    
    @staticmethod
    def pitch_shift(audio: np.ndarray, n_steps: int = 2) -> np.ndarray:
        """音调偏移
        
        Args:
            audio: 音频数据
            n_steps: 偏移步数
            
        Returns:
            偏移后的音频
        """
        # 简单的实现：通过重采样改变音调
        if n_steps == 0:
            return audio
        
        shift_factor = 2 ** (n_steps / 12.0)  # 12步为一个八度
        return AudioAugmentation.time_stretch(audio, 1.0 / shift_factor)


class DataAugmentationPipeline:
    """数据增强流水线"""
    
    def __init__(self, augmentations: List[Dict[str, Any]]):
        """初始化流水线
        
        Args:
            augmentations: 增强配置列表
        """
        self.augmentations = augmentations
    
    def apply_image_augmentations(self, image: Image.Image) -> Image.Image:
        """应用图像增强
        
        Args:
            image: 输入图像
            
        Returns:
            增强后的图像
        """
        augmented_image = image.copy()
        
        for aug_config in self.augmentations:
            if aug_config['type'] == 'rotation':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.random_rotation(
                        augmented_image, aug_config.get('degrees', 30))
            
            elif aug_config['type'] == 'flip':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.random_flip(
                        augmented_image, 
                        aug_config.get('horizontal', True),
                        aug_config.get('vertical', False))
            
            elif aug_config['type'] == 'crop':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.random_crop(
                        augmented_image, aug_config.get('crop_ratio', 0.8))
            
            elif aug_config['type'] == 'color_jitter':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.color_jitter(
                        augmented_image,
                        aug_config.get('brightness', 0.2),
                        aug_config.get('contrast', 0.2),
                        aug_config.get('saturation', 0.2),
                        aug_config.get('hue', 0.1))
            
            elif aug_config['type'] == 'blur':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.gaussian_blur(
                        augmented_image, aug_config.get('radius', 1.0))
            
            elif aug_config['type'] == 'noise':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_image = ImageAugmentation.add_noise(
                        augmented_image, aug_config.get('noise_factor', 0.1))
        
        return augmented_image
    
    def apply_text_augmentations(self, text: str, 
                               synonym_dict: Dict[str, List[str]]) -> str:
        """应用文本增强
        
        Args:
            text: 输入文本
            synonym_dict: 同义词字典
            
        Returns:
            增强后的文本
        """
        augmented_text = text
        
        for aug_config in self.augmentations:
            if aug_config['type'] == 'synonym_replacement':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_text = TextAugmentation.synonym_replacement(
                        augmented_text, synonym_dict, aug_config.get('n', 1))
            
            elif aug_config['type'] == 'random_insertion':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_text = TextAugmentation.random_insertion(
                        augmented_text, synonym_dict, aug_config.get('n', 1))
            
            elif aug_config['type'] == 'random_swap':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_text = TextAugmentation.random_swap(
                        augmented_text, aug_config.get('n', 1))
            
            elif aug_config['type'] == 'random_deletion':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_text = TextAugmentation.random_deletion(
                        augmented_text, aug_config.get('p', 0.1))
        
        return augmented_text
    
    def apply_audio_augmentations(self, audio: np.ndarray) -> np.ndarray:
        """应用音频增强
        
        Args:
            audio: 输入音频
            
        Returns:
            增强后的音频
        """
        augmented_audio = audio.copy()
        
        for aug_config in self.augmentations:
            if aug_config['type'] == 'add_noise':
                if random.random() < aug_config.get('probability', 0.5):
                    augmented_audio = AudioAugmentation.add_noise(
                        augmented_audio, aug_config.get('noise_factor', 0.01))
            
            elif aug_config['type'] == 'time_stretch':
                if random.random() < aug_config.get('probability', 0.5):
                    rate = random.uniform(
                        aug_config.get('min_rate', 0.8),
                        aug_config.get('max_rate', 1.2))
                    augmented_audio = AudioAugmentation.time_stretch(
                        augmented_audio, rate)
            
            elif aug_config['type'] == 'pitch_shift':
                if random.random() < aug_config.get('probability', 0.5):
                    n_steps = random.randint(
                        aug_config.get('min_steps', -2),
                        aug_config.get('max_steps', 2))
                    augmented_audio = AudioAugmentation.pitch_shift(
                        augmented_audio, n_steps)
        
        return augmented_audio