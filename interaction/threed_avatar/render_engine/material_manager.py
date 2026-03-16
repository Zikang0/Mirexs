"""
材质管理器
负责3D材质的创建、管理和应用
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class MaterialType(Enum):
    """材质类型"""
    PBR = "pbr"           # 基于物理的渲染
    PHONG = "phong"       # Phong光照模型
    LAMBERT = "lambert"   # Lambert漫反射
    UNLIT = "unlit"       # 无光照
    CUSTOM = "custom"     # 自定义着色器

@dataclass
class MaterialProperty:
    """材质属性"""
    name: str
    value: Any
    type: str  # float, color, texture, vector, etc.

@dataclass
class Material:
    """材质类"""
    name: str
    material_type: MaterialType
    properties: Dict[str, MaterialProperty]
    shader: Optional[str] = None
    transparency: float = 1.0
    double_sided: bool = False

class MaterialManager:
    """材质管理器"""
    
    def __init__(self):
        self.materials: Dict[str, Material] = {}
        self.material_library: Dict[str, Any] = {}
        self.shader_cache: Dict[str, Any] = {}
        
        # 加载默认材质
        self._create_default_materials()
        
        logger.info("Material manager initialized")
    
    def _create_default_materials(self):
        """创建默认材质"""
        try:
            # 默认PBR材质
            default_pbr = Material(
                name="default_pbr",
                material_type=MaterialType.PBR,
                properties={
                    "albedo": MaterialProperty("albedo", (0.8, 0.8, 0.8), "color"),
                    "metallic": MaterialProperty("metallic", 0.0, "float"),
                    "roughness": MaterialProperty("roughness", 0.8, "float"),
                    "normal": MaterialProperty("normal", None, "texture"),
                    "emissive": MaterialProperty("emissive", (0, 0, 0), "color")
                },
                shader="shaders/pbr.glsl"
            )
            self.materials["default_pbr"] = default_pbr
            
            # 默认Phong材质
            default_phong = Material(
                name="default_phong",
                material_type=MaterialType.PHONG,
                properties={
                    "diffuse": MaterialProperty("diffuse", (0.8, 0.8, 0.8), "color"),
                    "specular": MaterialProperty("specular", (1.0, 1.0, 1.0), "color"),
                    "shininess": MaterialProperty("shininess", 32.0, "float"),
                    "ambient": MaterialProperty("ambient", (0.2, 0.2, 0.2), "color")
                },
                shader="shaders/phong.glsl"
            )
            self.materials["default_phong"] = default_phong
            
            # 猫咪毛发材质
            cat_fur_material = Material(
                name="cat_fur",
                material_type=MaterialType.PBR,
                properties={
                    "albedo": MaterialProperty("albedo", (0.3, 0.2, 0.1), "color"),
                    "metallic": MaterialProperty("metallic", 0.1, "float"),
                    "roughness": MaterialProperty("roughness", 0.9, "float"),
                    "subsurface": MaterialProperty("subsurface", 0.5, "float"),
                    "sheen": MaterialProperty("sheen", 0.3, "float")
                },
                shader="shaders/pbr_fur.glsl"
            )
            self.materials["cat_fur"] = cat_fur_material
            
            logger.info("Default materials created")
            
        except Exception as e:
            logger.error(f"Failed to create default materials: {e}")
    
    def create_material(self, name: str, material_type: MaterialType, 
                       properties: Dict[str, Any] = None, 
                       shader: str = None) -> Optional[Material]:
        """
        创建新材质
        
        Args:
            name: 材质名称
            material_type: 材质类型
            properties: 材质属性
            shader: 着色器路径
            
        Returns:
            Optional[Material]: 创建的材质对象
        """
        try:
            if name in self.materials:
                logger.warning(f"Material {name} already exists, overwriting")
            
            # 转换属性为MaterialProperty对象
            material_properties = {}
            if properties:
                for prop_name, prop_value in properties.items():
                    prop_type = self._infer_property_type(prop_value)
                    material_properties[prop_name] = MaterialProperty(
                        prop_name, prop_value, prop_type
                    )
            
            material = Material(
                name=name,
                material_type=material_type,
                properties=material_properties,
                shader=shader or self._get_default_shader(material_type)
            )
            
            self.materials[name] = material
            logger.info(f"Created material: {name} ({material_type.value})")
            return material
            
        except Exception as e:
            logger.error(f"Failed to create material {name}: {e}")
            return None
    
    def get_material(self, name: str) -> Optional[Material]:
        """获取材质"""
        return self.materials.get(name)
    
    def update_material_property(self, material_name: str, property_name: str, 
                               value: Any) -> bool:
        """更新材质属性"""
        try:
            if material_name not in self.materials:
                logger.error(f"Material not found: {material_name}")
                return False
            
            material = self.materials[material_name]
            if property_name not in material.properties:
                logger.error(f"Property not found: {property_name}")
                return False
            
            material.properties[property_name].value = value
            logger.debug(f"Updated material property: {material_name}.{property_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update material property: {e}")
            return False
    
    def apply_material_to_model(self, material_name: str, model_data: Any) -> bool:
        """应用材质到模型"""
        try:
            if material_name not in self.materials:
                logger.error(f"Material not found: {material_name}")
                return False
            
            material = self.materials[material_name]
            
            # 这里实现将材质应用到3D模型的逻辑
            # 包括设置着色器参数、纹理等
            
            logger.info(f"Applied material {material_name} to model")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply material {material_name}: {e}")
            return False
    
    def load_material_library(self, file_path: str) -> bool:
        """从文件加载材质库"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                library_data = json.load(f)
            
            for material_name, material_data in library_data.get("materials", {}).items():
                material_type = MaterialType(material_data.get("type", "pbr"))
                properties = material_data.get("properties", {})
                shader = material_data.get("shader")
                
                self.create_material(material_name, material_type, properties, shader)
            
            logger.info(f"Loaded material library from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load material library: {e}")
            return False
    
    def save_material_library(self, file_path: str) -> bool:
        """保存材质库到文件"""
        try:
            library_data = {"materials": {}}
            
            for name, material in self.materials.items():
                material_data = {
                    "type": material.material_type.value,
                    "properties": {},
                    "shader": material.shader
                }
                
                for prop_name, prop in material.properties.items():
                    material_data["properties"][prop_name] = {
                        "value": prop.value,
                        "type": prop.type
                    }
                
                library_data["materials"][name] = material_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(library_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved material library to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save material library: {e}")
            return False
    
    def _infer_property_type(self, value: Any) -> str:
        """推断属性类型"""
        if isinstance(value, (int, float)):
            return "float"
        elif isinstance(value, (tuple, list)) and len(value) == 3:
            return "color"
        elif isinstance(value, str) and value.endswith(('.png', '.jpg', '.jpeg')):
            return "texture"
        elif isinstance(value, (tuple, list)) and len(value) in [2, 3, 4]:
            return "vector"
        else:
            return "unknown"
    
    def _get_default_shader(self, material_type: MaterialType) -> str:
        """获取默认着色器"""
        shader_map = {
            MaterialType.PBR: "shaders/pbr.glsl",
            MaterialType.PHONG: "shaders/phong.glsl",
            MaterialType.LAMBERT: "shaders/lambert.glsl",
            MaterialType.UNLIT: "shaders/unlit.glsl",
            MaterialType.CUSTOM: "shaders/custom.glsl"
        }
        return shader_map.get(material_type, "shaders/default.glsl")
    
    def get_material_properties(self, material_name: str) -> Dict[str, Any]:
        """获取材质的所有属性值"""
        if material_name not in self.materials:
            return {}
        
        material = self.materials[material_name]
        return {name: prop.value for name, prop in material.properties.items()}
    
    def create_material_instance(self, base_material_name: str, 
                               instance_name: str, 
                               overrides: Dict[str, Any] = None) -> Optional[Material]:
        """创建材质实例（基于现有材质）"""
        try:
            base_material = self.get_material(base_material_name)
            if not base_material:
                logger.error(f"Base material not found: {base_material_name}")
                return None
            
            # 复制基础材质属性
            instance_properties = {}
            for prop_name, prop in base_material.properties.items():
                instance_properties[prop_name] = MaterialProperty(
                    prop.name, prop.value, prop.type
                )
            
            # 应用覆盖
            if overrides:
                for prop_name, value in overrides.items():
                    if prop_name in instance_properties:
                        instance_properties[prop_name].value = value
            
            instance_material = Material(
                name=instance_name,
                material_type=base_material.material_type,
                properties=instance_properties,
                shader=base_material.shader,
                transparency=base_material.transparency,
                double_sided=base_material.double_sided
            )
            
            self.materials[instance_name] = instance_material
            logger.info(f"Created material instance: {instance_name} (based on {base_material_name})")
            return instance_material
            
        except Exception as e:
            logger.error(f"Failed to create material instance: {e}")
            return None
    
    def get_available_materials(self) -> List[str]:
        """获取所有可用材质名称"""
        return list(self.materials.keys())
