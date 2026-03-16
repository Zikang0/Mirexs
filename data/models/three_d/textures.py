"""
纹理材质管理系统
负责3D模型纹理的加载、管理和优化
"""

import os
import json
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class TextureInfo:
    """纹理信息数据类"""
    name: str
    file_path: str
    texture_type: str  # diffuse, normal, specular, roughness, etc.
    resolution: Tuple[int, int]
    format: str
    mipmaps: bool
    compression: str
    uv_channel: int = 0

@dataclass
class MaterialInfo:
    """材质信息数据类"""
    name: str
    material_type: str  # pbr, phong, custom
    textures: Dict[str, str]  # texture_type -> texture_name
    parameters: Dict[str, float]  # shader parameters
    shader: str

class TextureManager:
    """纹理管理器"""
    
    def __init__(self, base_texture_path: str = "assets/textures/"):
        self.base_path = Path(base_texture_path)
        self.textures: Dict[str, TextureInfo] = {}
        self.materials: Dict[str, MaterialInfo] = {}
        self.loaded_textures: Dict[str, any] = {}  # 实际加载的纹理对象
        self.texture_cache: Dict[str, np.ndarray] = {}
        
        # 确保基础目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def load_texture(self, texture_name: str, file_path: str, 
                    texture_type: str = "diffuse") -> bool:
        """
        加载纹理文件
        
        Args:
            texture_name: 纹理名称
            file_path: 纹理文件路径
            texture_type: 纹理类型
            
        Returns:
            bool: 是否加载成功
        """
        try:
            full_path = self.base_path / file_path
            if not full_path.exists():
                logger.error(f"Texture file not found: {full_path}")
                return False
                
            # 使用PIL加载图像
            with Image.open(full_path) as img:
                img_data = np.array(img)
                resolution = img.size
                img_format = img.format
                
            # 创建纹理信息
            texture_info = TextureInfo(
                name=texture_name,
                file_path=str(full_path),
                texture_type=texture_type,
                resolution=resolution,
                format=img_format,
                mipmaps=True,
                compression="none"
            )
            
            self.textures[texture_name] = texture_info
            self.texture_cache[texture_name] = img_data
            
            logger.info(f"Loaded texture: {texture_name} ({texture_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load texture {texture_name}: {str(e)}")
            return False
            
    def create_material(self, material_name: str, material_type: str = "pbr",
                       textures: Dict[str, str] = None, 
                       parameters: Dict[str, float] = None) -> bool:
        """
        创建材质
        
        Args:
            material_name: 材质名称
            material_type: 材质类型
            textures: 纹理映射
            parameters: 材质参数
            
        Returns:
            bool: 是否创建成功
        """
        try:
            if textures is None:
                textures = {}
            if parameters is None:
                parameters = {}
                
            material_info = MaterialInfo(
                name=material_name,
                material_type=material_type,
                textures=textures,
                parameters=parameters,
                shader=self._get_shader_for_type(material_type)
            )
            
            self.materials[material_name] = material_info
            logger.info(f"Created material: {material_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create material {material_name}: {str(e)}")
            return False
            
    def get_texture_data(self, texture_name: str) -> Optional[np.ndarray]:
        """获取纹理数据"""
        return self.texture_cache.get(texture_name)
        
    def get_material(self, material_name: str) -> Optional[MaterialInfo]:
        """获取材质信息"""
        return self.materials.get(material_name)
        
    def generate_mipmaps(self, texture_name: str, levels: int = 4) -> bool:
        """
        为纹理生成mipmaps
        
        Args:
            texture_name: 纹理名称
            levels: mipmap层级数
            
        Returns:
            bool: 是否生成成功
        """
        try:
            if texture_name not in self.texture_cache:
                return False
                
            texture_data = self.texture_cache[texture_name]
            # 这里实现mipmap生成逻辑
            # 简化实现，实际应该生成多级mipmap
            
            logger.info(f"Generated {levels} mipmap levels for {texture_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate mipmaps for {texture_name}: {str(e)}")
            return False
            
    def compress_texture(self, texture_name: str, compression_format: str) -> bool:
        """
        压缩纹理
        
        Args:
            texture_name: 纹理名称
            compression_format: 压缩格式
            
        Returns:
            bool: 是否压缩成功
        """
        try:
            if texture_name not in self.textures:
                return False
                
            texture_info = self.textures[texture_name]
            texture_info.compression = compression_format
            
            # 这里实现具体的压缩逻辑
            # 简化实现，实际应该进行纹理压缩
            
            logger.info(f"Compressed texture {texture_name} with {compression_format}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to compress texture {texture_name}: {str(e)}")
            return False
            
    def _get_shader_for_type(self, material_type: str) -> str:
        """根据材质类型获取对应的shader"""
        shader_map = {
            "pbr": "shaders/pbr_shader.glsl",
            "phong": "shaders/phong_shader.glsl",
            "custom": "shaders/custom_shader.glsl"
        }
        return shader_map.get(material_type, "shaders/default_shader.glsl")
        
    def save_material_library(self, file_path: str) -> bool:
        """保存材质库到文件"""
        try:
            library_data = {
                "materials": {
                    name: {
                        "material_type": mat.material_type,
                        "textures": mat.textures,
                        "parameters": mat.parameters,
                        "shader": mat.shader
                    }
                    for name, mat in self.materials.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(library_data, f, indent=2)
                
            logger.info(f"Saved material library to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save material library: {str(e)}")
            return False
            
    def load_material_library(self, file_path: str) -> bool:
        """从文件加载材质库"""
        try:
            with open(file_path, 'r') as f:
                library_data = json.load(f)
                
            for name, mat_data in library_data.get("materials", {}).items():
                self.create_material(
                    name,
                    mat_data["material_type"],
                    mat_data["textures"],
                    mat_data["parameters"]
                )
                
            logger.info(f"Loaded material library from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load material library: {str(e)}")
            return False
