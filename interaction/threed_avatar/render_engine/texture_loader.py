"""
纹理加载器
负责纹理的加载、管理和GPU上传
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from PIL import Image
import os

logger = logging.getLogger(__name__)

class TextureFormat(Enum):
    """纹理格式"""
    RGB = "RGB"
    RGBA = "RGBA"
    SRGB = "SRGB"
    SRGBA = "SRGBA"
    DEPTH = "DEPTH"
    STENCIL = "STENCIL"

class TextureFilter(Enum):
    """纹理过滤模式"""
    NEAREST = "nearest"
    LINEAR = "linear"
    LINEAR_MIPMAP_LINEAR = "linear_mipmap_linear"

class TextureWrap(Enum):
    """纹理包裹模式"""
    REPEAT = "repeat"
    CLAMP = "clamp"
    MIRROR = "mirror"

@dataclass
class Texture:
    """纹理类"""
    name: str
    width: int
    height: int
    format: TextureFormat
    data: Optional[np.ndarray] = None
    texture_id: Optional[int] = None
    filter_mode: TextureFilter = TextureFilter.LINEAR
    wrap_mode: TextureWrap = TextureWrap.REPEAT
    mipmaps: bool = True
    mipmap_levels: int = 0

class TextureLoader:
    """纹理加载器"""
    
    def __init__(self, texture_directory: str = "textures"):
        self.texture_directory = texture_directory
        self.textures: Dict[str, Texture] = {}
        self.texture_cache: Dict[str, Texture] = {}
        
        logger.info("Texture loader initialized")
    
    def load_texture(self, name: str, file_path: str, 
                    format: TextureFormat = TextureFormat.RGBA,
                    generate_mipmaps: bool = True) -> Optional[Texture]:
        """
        从文件加载纹理
        
        Args:
            name: 纹理名称
            file_path: 文件路径
            format: 纹理格式
            generate_mipmaps: 是否生成mipmaps
            
        Returns:
            Optional[Texture]: 纹理对象
        """
        try:
            # 检查缓存
            cache_key = f"{file_path}_{format.value}"
            if cache_key in self.texture_cache:
                logger.info(f"Using cached texture: {name}")
                cached_texture = self.texture_cache[cache_key]
                cached_texture.name = name  # 更新名称
                self.textures[name] = cached_texture
                return cached_texture
            
            # 查找文件
            full_path = self._find_texture_file(file_path)
            if full_path is None:
                logger.error(f"Texture file not found: {file_path}")
                return None
            
            # 使用PIL加载图像
            with Image.open(full_path) as img:
                # 转换为目标格式
                if format == TextureFormat.RGBA or format == TextureFormat.SRGBA:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                elif format == TextureFormat.RGB or format == TextureFormat.SRGB:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                
                # 转换为numpy数组
                img_data = np.array(img)
                width, height = img.size
                
                # 确保数据是连续的
                if not img_data.flags['C_CONTIGUOUS']:
                    img_data = np.ascontiguousarray(img_data)
            
            texture = Texture(
                name=name,
                width=width,
                height=height,
                format=format,
                data=img_data,
                mipmaps=generate_mipmaps
            )
            
            self.textures[name] = texture
            self.texture_cache[cache_key] = texture
            
            logger.info(f"Loaded texture: {name} ({width}x{height}, {format.value})")
            return texture
            
        except Exception as e:
            logger.error(f"Failed to load texture {name}: {e}")
            return None
    
    def _find_texture_file(self, file_path: str) -> Optional[str]:
        """查找纹理文件"""
        # 检查绝对路径
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path
        
        # 检查相对路径
        relative_path = os.path.join(self.texture_directory, file_path)
        if os.path.exists(relative_path):
            return relative_path
        
        # 在常见位置查找
        search_paths = [
            file_path,
            relative_path,
            f"assets/{file_path}",
            f"resources/{file_path}",
            f"textures/{file_path}"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def create_texture(self, name: str, width: int, height: int,
                      format: TextureFormat = TextureFormat.RGBA,
                      data: Optional[np.ndarray] = None) -> Optional[Texture]:
        """
        创建空纹理
        
        Args:
            name: 纹理名称
            width: 宽度
            height: 高度
            format: 纹理格式
            data: 纹理数据（可选）
            
        Returns:
            Optional[Texture]: 纹理对象
        """
        try:
            if data is None:
                # 创建空数据
                if format == TextureFormat.RGBA or format == TextureFormat.SRGBA:
                    data = np.zeros((height, width, 4), dtype=np.uint8)
                    # 默认设置为透明
                    data[:, :, 3] = 255
                elif format == TextureFormat.RGB or format == TextureFormat.SRGB:
                    data = np.zeros((height, width, 3), dtype=np.uint8)
                elif format == TextureFormat.DEPTH:
                    data = np.zeros((height, width), dtype=np.float32)
                else:
                    data = np.zeros((height, width), dtype=np.uint8)
            
            texture = Texture(
                name=name,
                width=width,
                height=height,
                format=format,
                data=data
            )
            
            self.textures[name] = texture
            logger.info(f"Created texture: {name} ({width}x{height}, {format.value})")
            return texture
            
        except Exception as e:
            logger.error(f"Failed to create texture {name}: {e}")
            return None
    
    def upload_texture(self, name: str) -> bool:
        """
        上传纹理到GPU
        
        Args:
            name: 纹理名称
            
        Returns:
            bool: 是否上传成功
        """
        try:
            if name not in self.textures:
                logger.error(f"Texture not found: {name}")
                return False
            
            texture = self.textures[name]
            
            if texture.data is None:
                logger.error(f"Texture data is None: {name}")
                return False
            
            # 这里实现纹理上传到GPU的逻辑
            texture_id = self._upload_to_gpu(texture)
            if texture_id is None:
                return False
            
            texture.texture_id = texture_id
            
            # 生成mipmaps
            if texture.mipmaps:
                self._generate_mipmaps(texture)
            
            logger.info(f"Uploaded texture to GPU: {name} (ID: {texture_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload texture {name}: {e}")
            return False
    
    def _upload_to_gpu(self, texture: Texture) -> Optional[int]:
        """上传纹理到GPU（模拟实现）"""
        try:
            # 在实际应用中，这里会调用OpenGL/DirectX/Vulkan API上传纹理
            # 这里返回模拟的纹理ID
            
            # 验证纹理数据
            if texture.data is None:
                return None
            
            # 根据格式验证数据形状
            expected_shape = self._get_expected_shape(texture)
            if texture.data.shape != expected_shape:
                logger.warning(f"Texture data shape mismatch for {texture.name}")
                # 尝试调整数据形状
                texture.data = self._reshape_texture_data(texture.data, expected_shape)
            
            # 生成模拟纹理ID
            import random
            texture_id = random.randint(1000, 9999)
            
            return texture_id
            
        except Exception as e:
            logger.error(f"GPU upload failed for {texture.name}: {e}")
            return None
    
    def _get_expected_shape(self, texture: Texture) -> Tuple[int, ...]:
        """获取预期的纹理数据形状"""
        if texture.format in [TextureFormat.RGB, TextureFormat.SRGB]:
            return (texture.height, texture.width, 3)
        elif texture.format in [TextureFormat.RGBA, TextureFormat.SRGBA]:
            return (texture.height, texture.width, 4)
        elif texture.format == TextureFormat.DEPTH:
            return (texture.height, texture.width)
        else:
            return (texture.height, texture.width)
    
    def _reshape_texture_data(self, data: np.ndarray, target_shape: Tuple[int, ...]) -> np.ndarray:
        """调整纹理数据形状"""
        try:
            if data.shape == target_shape:
                return data
            
            # 简单的形状调整逻辑
            if len(data.shape) == 2 and len(target_shape) == 3:
                # 灰度转RGB
                return np.stack([data] * 3, axis=-1)
            elif len(data.shape) == 3 and len(target_shape) == 2:
                # RGB转灰度
                return np.mean(data, axis=2)
            elif data.shape[0] != target_shape[0] or data.shape[1] != target_shape[1]:
                # 调整尺寸
                from PIL import Image
                img = Image.fromarray(data)
                img = img.resize((target_shape[1], target_shape[0]))
                return np.array(img)
            else:
                # 通道数不匹配
                return data.reshape(target_shape)
                
        except Exception as e:
            logger.error(f"Failed to reshape texture data: {e}")
            return data
    
    def _generate_mipmaps(self, texture: Texture):
        """生成mipmaps"""
        try:
            if texture.data is None:
                return
            
            # 计算mipmap级别
            size = min(texture.width, texture.height)
            mip_levels = int(np.log2(size)) + 1 if texture.mipmaps else 1
            texture.mipmap_levels = mip_levels
            
            logger.info(f"Generated {mip_levels} mipmap levels for {texture.name}")
            
        except Exception as e:
            logger.error(f"Failed to generate mipmaps for {texture.name}: {e}")
    
    def bind_texture(self, name: str, texture_unit: int = 0) -> bool:
        """
        绑定纹理
        
        Args:
            name: 纹理名称
            texture_unit: 纹理单元
            
        Returns:
            bool: 是否绑定成功
        """
        try:
            if name not in self.textures:
                logger.error(f"Texture not found: {name}")
                return False
            
            texture = self.textures[name]
            if texture.texture_id is None:
                logger.error(f"Texture not uploaded to GPU: {name}")
                return False
            
            # 这里实现纹理绑定逻辑
            self._bind_texture_unit(texture.texture_id, texture_unit)
            
            logger.debug(f"Bound texture {name} to unit {texture_unit}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to bind texture {name}: {e}")
            return False
    
    def _bind_texture_unit(self, texture_id: int, texture_unit: int):
        """绑定纹理单元（模拟实现）"""
        # 在实际应用中，这里会调用glActiveTexture和glBindTexture
        pass
    
    def set_texture_parameters(self, name: str, 
                             filter_mode: TextureFilter = None,
                             wrap_mode: TextureWrap = None) -> bool:
        """
        设置纹理参数
        
        Args:
            name: 纹理名称
            filter_mode: 过滤模式
            wrap_mode: 包裹模式
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if name not in self.textures:
                return False
            
            texture = self.textures[name]
            
            if filter_mode is not None:
                texture.filter_mode = filter_mode
            
            if wrap_mode is not None:
                texture.wrap_mode = wrap_mode
            
            # 如果纹理已经上传到GPU，更新参数
            if texture.texture_id is not None:
                self._update_texture_parameters(texture)
            
            logger.debug(f"Set texture parameters for {name}: filter={texture.filter_mode}, wrap={texture.wrap_mode}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set texture parameters for {name}: {e}")
            return False
    
    def _update_texture_parameters(self, texture: Texture):
        """更新纹理参数（模拟实现）"""
        # 在实际应用中，这里会根据设置的参数调用glTexParameteri
        pass
    
    def create_procedural_texture(self, name: str, width: int, height: int,
                                texture_type: str, **kwargs) -> Optional[Texture]:
        """
        创建程序化纹理
        
        Args:
            name: 纹理名称
            width: 宽度
            height: 高度
            texture_type: 纹理类型
            **kwargs: 额外参数
            
        Returns:
            Optional[Texture]: 纹理对象
        """
        try:
            if texture_type == "checkerboard":
                return self._create_checkerboard_texture(name, width, height, **kwargs)
            elif texture_type == "noise":
                return self._create_noise_texture(name, width, height, **kwargs)
            elif texture_type == "gradient":
                return self._create_gradient_texture(name, width, height, **kwargs)
            else:
                logger.error(f"Unknown procedural texture type: {texture_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create procedural texture {name}: {e}")
            return None
    
    def _create_checkerboard_texture(self, name: str, width: int, height: int,
                                   tile_size: int = 32, color1: Tuple = (255, 255, 255),
                                   color2: Tuple = (100, 100, 100)) -> Texture:
        """创建棋盘格纹理"""
        data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            for x in range(width):
                tile_x = x // tile_size
                tile_y = y // tile_size
                
                if (tile_x + tile_y) % 2 == 0:
                    data[y, x] = color1
                else:
                    data[y, x] = color2
        
        return self.create_texture(name, width, height, TextureFormat.RGB, data)
    
    def _create_noise_texture(self, name: str, width: int, height: int,
                            noise_type: str = "perlin", scale: float = 0.1) -> Texture:
        """创建噪声纹理"""
        # 简化实现 - 使用随机噪声
        data = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        return self.create_texture(name, width, height, TextureFormat.RGB, data)
    
    def _create_gradient_texture(self, name: str, width: int, height: int,
                               color_start: Tuple = (255, 0, 0),
                               color_end: Tuple = (0, 0, 255)) -> Texture:
        """创建渐变纹理"""
        data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for y in range(height):
            t = y / (height - 1)
            color = [
                int(color_start[i] * (1 - t) + color_end[i] * t)
                for i in range(3)
            ]
            data[y, :] = color
        
        return self.create_texture(name, width, height, TextureFormat.RGB, data)
    
    def get_texture_info(self, name: str) -> Dict[str, Any]:
        """获取纹理信息"""
        if name not in self.textures:
            return {}
        
        texture = self.textures[name]
        return {
            "name": texture.name,
            "width": texture.width,
            "height": texture.height,
            "format": texture.format.value,
            "uploaded": texture.texture_id is not None,
            "filter_mode": texture.filter_mode.value,
            "wrap_mode": texture.wrap_mode.value,
            "mipmaps": texture.mipmaps,
            "mipmap_levels": texture.mipmap_levels
        }
    
    def resize_texture(self, name: str, new_width: int, new_height: int) -> bool:
        """
        调整纹理尺寸
        
        Args:
            name: 纹理名称
            new_width: 新宽度
            new_height: 新高度
            
        Returns:
            bool: 是否调整成功
        """
        try:
            if name not in self.textures:
                return False
            
            texture = self.textures[name]
            
            if texture.data is None:
                logger.error(f"Texture data is None: {name}")
                return False
            
            # 使用PIL调整尺寸
            from PIL import Image
            img = Image.fromarray(texture.data)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            texture.data = np.array(resized_img)
            texture.width = new_width
            texture.height = new_height
            
            # 如果纹理已经上传到GPU，需要重新上传
            if texture.texture_id is not None:
                self.upload_texture(name)
            
            logger.info(f"Resized texture {name} to {new_width}x{new_height}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resize texture {name}: {e}")
            return False
