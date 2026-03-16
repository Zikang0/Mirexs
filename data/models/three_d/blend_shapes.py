"""
混合形状（表情）系统
负责面部表情混合形状的管理和动画
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class BlendShape:
    """混合形状数据类"""
    name: str
    vertices: np.ndarray  # 形状的顶点位置
    normals: np.ndarray   # 形状的法线
    weight: float         # 当前权重
    category: str        # 表情分类

@dataclass
class ExpressionPreset:
    """表情预设数据类"""
    name: str
    blend_shapes: Dict[str, float]  # 混合形状名称 -> 权重
    intensity: float

class BlendShapeSystem:
    """混合形状系统"""
    
    def __init__(self, base_vertices: np.ndarray, base_normals: np.ndarray):
        self.base_vertices = base_normals.copy()
        self.base_normals = base_normals.copy()
        self.blend_shapes: Dict[str, BlendShape] = {}
        self.presets: Dict[str, ExpressionPreset] = {}
        self.current_weights: Dict[str, float] = {}
        self.categories: Dict[str, List[str]] = {}
        
    def add_blend_shape(self, name: str, vertices: np.ndarray, 
                       normals: np.ndarray, category: str = "expression") -> bool:
        """
        添加混合形状
        
        Args:
            name: 混合形状名称
            vertices: 顶点位置
            normals: 法线
            category: 分类
            
        Returns:
            bool: 是否添加成功
        """
        try:
            if vertices.shape != self.base_vertices.shape:
                logger.error(f"Blend shape vertices shape mismatch: {vertices.shape} vs {self.base_vertices.shape}")
                return False
                
            blend_shape = BlendShape(
                name=name,
                vertices=vertices,
                normals=normals,
                weight=0.0,
                category=category
            )
            
            self.blend_shapes[name] = blend_shape
            self.current_weights[name] = 0.0
            
            # 更新分类
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(name)
            
            logger.info(f"Added blend shape: {name} (category: {category})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add blend shape {name}: {str(e)}")
            return False
            
    def set_weight(self, blend_shape_name: str, weight: float) -> bool:
        """
        设置混合形状权重
        
        Args:
            blend_shape_name: 混合形状名称
            weight: 权重值 [0, 1]
            
        Returns:
            bool: 是否设置成功
        """
        try:
            if blend_shape_name not in self.blend_shapes:
                logger.error(f"Blend shape not found: {blend_shape_name}")
                return False
                
            # 限制权重范围
            weight = max(0.0, min(1.0, weight))
            
            self.blend_shapes[blend_shape_name].weight = weight
            self.current_weights[blend_shape_name] = weight
            
            logger.debug(f"Set blend shape {blend_shape_name} weight to {weight}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set weight for {blend_shape_name}: {str(e)}")
            return False
            
    def get_deformed_vertices(self) -> np.ndarray:
        """
        获取变形后的顶点位置
        
        Returns:
            np.ndarray: 变形后的顶点
        """
        deformed_vertices = self.base_vertices.copy()
        
        for name, blend_shape in self.blend_shapes.items():
            weight = blend_shape.weight
            if weight > 0:
                # 计算变形偏移
                offset = blend_shape.vertices - self.base_vertices
                deformed_vertices += offset * weight
                
        return deformed_vertices
        
    def get_deformed_normals(self) -> np.ndarray:
        """
        获取变形后的法线
        
        Returns:
            np.ndarray: 变形后的法线
        """
        deformed_normals = self.base_normals.copy()
        
        for name, blend_shape in self.blend_shapes.items():
            weight = blend_shape.weight
            if weight > 0:
                # 计算法线偏移
                normal_offset = blend_shape.normals - self.base_normals
                deformed_normals += normal_offset * weight
                
        # 归一化法线
        norms = np.linalg.norm(deformed_normals, axis=1, keepdims=True)
        deformed_normals = deformed_normals / norms
        
        return deformed_normals
        
    def create_expression_preset(self, name: str, 
                               blend_shape_weights: Dict[str, float],
                               intensity: float = 1.0) -> bool:
        """
        创建表情预设
        
        Args:
            name: 预设名称
            blend_shape_weights: 混合形状权重映射
            intensity: 强度
            
        Returns:
            bool: 是否创建成功
        """
        try:
            preset = ExpressionPreset(
                name=name,
                blend_shapes=blend_shape_weights,
                intensity=intensity
            )
            
            self.presets[name] = preset
            logger.info(f"Created expression preset: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create expression preset {name}: {str(e)}")
            return False
            
    def apply_preset(self, preset_name: str, intensity: float = None) -> bool:
        """
        应用表情预设
        
        Args:
            preset_name: 预设名称
            intensity: 强度（覆盖预设的强度）
            
        Returns:
            bool: 是否应用成功
        """
        try:
            if preset_name not in self.presets:
                logger.error(f"Preset not found: {preset_name}")
                return False
                
            preset = self.presets[preset_name]
            actual_intensity = intensity if intensity is not None else preset.intensity
            
            for blend_shape_name, weight in preset.blend_shapes.items():
                if blend_shape_name in self.blend_shapes:
                    actual_weight = weight * actual_intensity
                    self.set_weight(blend_shape_name, actual_weight)
                    
            logger.info(f"Applied preset: {preset_name} (intensity: {actual_intensity})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply preset {preset_name}: {str(e)}")
            return False
            
    def reset_all_weights(self):
        """重置所有混合形状权重"""
        for name in self.blend_shapes:
            self.set_weight(name, 0.0)
        logger.info("Reset all blend shape weights")
        
    def get_expression_intensity(self, expression_category: str) -> float:
        """
        获取某类表情的总体强度
        
        Args:
            expression_category: 表情分类
            
        Returns:
            float: 强度值
        """
        if expression_category not in self.categories:
            return 0.0
            
        total_weight = 0.0
        count = 0
        
        for blend_shape_name in self.categories[expression_category]:
            if blend_shape_name in self.current_weights:
                total_weight += self.current_weights[blend_shape_name]
                count += 1
                
        return total_weight / count if count > 0 else 0.0
        
    def auto_blink(self, blink_strength: float = 1.0) -> bool:
        """
        自动眨眼功能
        
        Args:
            blink_strength: 眨眼强度
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 查找与眨眼相关的混合形状
            blink_shapes = []
            for name, blend_shape in self.blend_shapes.items():
                if "blink" in name.lower() or "eye_close" in name.lower():
                    blink_shapes.append(name)
                    
            if not blink_shapes:
                logger.warning("No blink-related blend shapes found")
                return False
                
            # 应用眨眼
            for shape_name in blink_shapes:
                self.set_weight(shape_name, blink_strength)
                
            logger.info(f"Applied auto blink with strength {blink_strength}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply auto blink: {str(e)}")
            return False
            
    def save_preset_library(self, file_path: str) -> bool:
        """保存预设库到文件"""
        try:
            preset_data = {
                "presets": {
                    name: {
                        "blend_shapes": preset.blend_shapes,
                        "intensity": preset.intensity
                    }
                    for name, preset in self.presets.items()
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(preset_data, f, indent=2)
                
            logger.info(f"Saved preset library to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preset library: {str(e)}")
            return False
            
    def load_preset_library(self, file_path: str) -> bool:
        """从文件加载预设库"""
        try:
            with open(file_path, 'r') as f:
                preset_data = json.load(f)
                
            for name, data in preset_data.get("presets", {}).items():
                self.create_expression_preset(
                    name,
                    data["blend_shapes"],
                    data["intensity"]
                )
                
            logger.info(f"Loaded preset library from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load preset library: {str(e)}")
            return False
            
    def get_expression_summary(self) -> Dict[str, float]:
        """
        获取当前表情摘要
        
        Returns:
            Dict[str, float]: 分类 -> 强度
        """
        summary = {}
        for category in self.categories:
            summary[category] = self.get_expression_intensity(category)
            
        return summary

