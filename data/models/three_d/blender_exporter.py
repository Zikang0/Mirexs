"""
Blender模型导出器
负责将3D模型从Blender导出为项目可用的格式
"""

import os
import json
import bpy
import bmesh
from typing import Dict, List, Optional, Tuple, Any
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

class BlenderExporter:
    """Blender模型导出器"""
    
    def __init__(self, export_path: str = "exports/"):
        self.export_path = Path(export_path)
        self.supported_formats = ['.glb', '.gltf', '.obj', '.fbx', '.dae']
        self.export_settings = {
            'gltf': {
                'format': 'GLTF_SEPARATE',
                'export_textures': True,
                'export_materials': True,
                'export_animations': True
            },
            'obj': {
                'export_normals': True,
                'export_uvs': True,
                'export_materials': True
            },
            'fbx': {
                'use_selection': False,
                'global_scale': 1.0,
                'apply_unit_scale': True
            }
        }
        
        # 确保导出目录存在
        self.export_path.mkdir(parents=True, exist_ok=True)
        
    def check_blender_available(self) -> bool:
        """
        检查Blender是否可用
        
        Returns:
            bool: Blender是否可用
        """
        try:
            import bpy
            return True
        except ImportError:
            logger.warning("Blender not available - running in export-only mode")
            return False
            
    def export_selected_objects(self, file_path: str, 
                              format_type: str = 'gltf') -> bool:
        """
        导出选中的对象
        
        Args:
            file_path: 导出文件路径
            format_type: 导出格式
            
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.check_blender_available():
                return False
                
            if format_type not in self.supported_formats:
                logger.error(f"Unsupported format: {format_type}")
                return False
                
            full_path = self.export_path / file_path
            
            # 根据格式调用不同的导出函数
            if format_type == 'gltf':
                return self._export_gltf(full_path)
            elif format_type == 'obj':
                return self._export_obj(full_path)
            elif format_type == 'fbx':
                return self._export_fbx(full_path)
            else:
                logger.error(f"Export for format {format_type} not implemented")
                return False
                
        except Exception as e:
            logger.error(f"Failed to export selected objects: {str(e)}")
            return False
            
    def export_armature(self, armature_name: str, 
                       file_path: str) -> bool:
        """
        导出骨骼结构
        
        Args:
            armature_name: 骨骼名称
            file_path: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.check_blender_available():
                return False
                
            # 选择指定的骨骼
            if armature_name not in bpy.data.armatures:
                logger.error(f"Armature not found: {armature_name}")
                return False
                
            armature = bpy.data.armatures[armature_name]
            
            # 构建骨骼数据
            armature_data = self._extract_armature_data(armature)
            
            # 保存为JSON
            full_path = self.export_path / file_path
            with open(full_path, 'w') as f:
                json.dump(armature_data, f, indent=2)
                
            logger.info(f"Exported armature {armature_name} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export armature {armature_name}: {str(e)}")
            return False
            
    def export_blend_shapes(self, mesh_name: str, 
                          file_path: str) -> bool:
        """
        导出混合形状数据
        
        Args:
            mesh_name: 网格名称
            file_path: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.check_blender_available():
                return False
                
            if mesh_name not in bpy.data.meshes:
                logger.error(f"Mesh not found: {mesh_name}")
                return False
                
            mesh = bpy.data.meshes[mesh_name]
            
            # 提取混合形状数据
            blend_shape_data = self._extract_blend_shape_data(mesh)
            
            # 保存为JSON
            full_path = self.export_path / file_path
            with open(full_path, 'w') as f:
                json.dump(blend_shape_data, f, indent=2)
                
            logger.info(f"Exported blend shapes for {mesh_name} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export blend shapes for {mesh_name}: {str(e)}")
            return False
            
    def export_material_library(self, file_path: str) -> bool:
        """
        导出材质库
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.check_blender_available():
                return False
                
            materials_data = {}
            
            for material in bpy.data.materials:
                material_data = self._extract_material_data(material)
                materials_data[material.name] = material_data
                
            # 保存为JSON
            full_path = self.export_path / file_path
            with open(full_path, 'w') as f:
                json.dump(materials_data, f, indent=2)
                
            logger.info(f"Exported material library to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export material library: {str(e)}")
            return False
            
    def optimize_mesh(self, mesh_name: str, 
                     decimate_ratio: float = 0.5) -> bool:
        """
        优化网格（减少面数）
        
        Args:
            mesh_name: 网格名称
            decimate_ratio: 简化比例
            
        Returns:
            bool: 是否优化成功
        """
        try:
            if not self.check_blender_available():
                return False
                
            if mesh_name not in bpy.data.meshes:
                logger.error(f"Mesh not found: {mesh_name}")
                return False
                
            mesh = bpy.data.meshes[mesh_name]
            
            # 进入编辑模式
            bpy.context.view_layer.objects.active = mesh
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 选择所有面
            bpy.ops.mesh.select_all(action='SELECT')
            
            # 应用简化修改器
            bpy.ops.mesh.decimate(ratio=decimate_ratio)
            
            # 返回对象模式
            bpy.ops.object.mode_set(mode='OBJECT')
            
            logger.info(f"Optimized mesh {mesh_name} with ratio {decimate_ratio}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize mesh {mesh_name}: {str(e)}")
            return False
            
    def _export_gltf(self, file_path: Path) -> bool:
        """导出为GLTF格式"""
        try:
            bpy.ops.export_scene.gltf(
                filepath=str(file_path),
                export_format='GLTF_SEPARATE',
                export_textures=True,
                export_materials=True,
                export_animations=True,
                use_selection=True
            )
            return True
        except Exception as e:
            logger.error(f"GLTF export failed: {str(e)}")
            return False
            
    def _export_obj(self, file_path: Path) -> bool:
        """导出为OBJ格式"""
        try:
            bpy.ops.export_scene.obj(
                filepath=str(file_path),
                use_normals=True,
                use_uvs=True,
                use_materials=True,
                use_selection=True
            )
            return True
        except Exception as e:
            logger.error(f"OBJ export failed: {str(e)}")
            return False
            
    def _export_fbx(self, file_path: Path) -> bool:
        """导出为FBX格式"""
        try:
            bpy.ops.export_scene.fbx(
                filepath=str(file_path),
                use_selection=True,
                global_scale=1.0,
                apply_unit_scale=True
            )
            return True
        except Exception as e:
            logger.error(f"FBX export failed: {str(e)}")
            return False
            
    def _extract_armature_data(self, armature: Any) -> Dict[str, Any]:
        """提取骨骼数据"""
        armature_data = {
            "name": armature.name,
            "bones": {}
        }
        
        # 这里实现骨骼数据提取逻辑
        # 简化实现
        
        return armature_data
        
    def _extract_blend_shape_data(self, mesh: Any) -> Dict[str, Any]:
        """提取混合形状数据"""
        blend_shape_data = {
            "mesh_name": mesh.name,
            "base_vertices": [],
            "blend_shapes": {}
        }
        
        # 这里实现混合形状数据提取逻辑
        # 简化实现
        
        return blend_shape_data
        
    def _extract_material_data(self, material: Any) -> Dict[str, Any]:
        """提取材质数据"""
        material_data = {
            "name": material.name,
            "diffuse_color": list(material.diffuse_color),
            "specular_intensity": material.specular_intensity,
            "roughness": material.roughness,
            "metallic": material.metallic,
            "textures": {}
        }
        
        # 提取纹理信息
        for tex_slot in material.texture_slots:
            if tex_slot and tex_slot.texture:
                texture = tex_slot.texture
                if hasattr(texture, 'image') and texture.image:
                    material_data["textures"][tex_slot.name] = {
                        "file_path": texture.image.filepath,
                        "type": tex_slot.texture_coords
                    }
                    
        return material_data
        
    def batch_export(self, export_list: List[Dict[str, str]]) -> bool:
        """
        批量导出多个对象
        
        Args:
            export_list: 导出列表，每个元素包含 'name', 'type', 'format'
            
        Returns:
            bool: 是否全部导出成功
        """
        try:
            success_count = 0
            
            for item in export_list:
                name = item.get('name')
                obj_type = item.get('type', 'object')
                format_type = item.get('format', 'gltf')
                
                file_path = f"{name}.{format_type}"
                
                if obj_type == 'armature':
                    success = self.export_armature(name, file_path)
                elif obj_type == 'blend_shapes':
                    success = self.export_blend_shapes(name, file_path)
                else:
                    success = self.export_selected_objects(file_path, format_type)
                    
                if success:
                    success_count += 1
                    
            logger.info(f"Batch export completed: {success_count}/{len(export_list)} successful")
            return success_count == len(export_list)
            
        except Exception as e:
            logger.error(f"Batch export failed: {str(e)}")
            return False
            
    def generate_export_report(self, file_path: str) -> bool:
        """
        生成导出报告
        
        Args:
            file_path: 报告文件路径
            
        Returns:
            bool: 是否生成成功
        """
        try:
            report_data = {
                "export_settings": self.export_settings,
                "supported_formats": self.supported_formats,
                "available_objects": self._get_available_objects()
            }
            
            full_path = self.export_path / file_path
            with open(full_path, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            logger.info(f"Generated export report at {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate export report: {str(e)}")
            return False
            
    def _get_available_objects(self) -> Dict[str, List[str]]:
        """获取可用对象列表"""
        if not self.check_blender_available():
            return {}
            
        return {
            "meshes": [mesh.name for mesh in bpy.data.meshes],
            "armatures": [armature.name for armature in bpy.data.armatures],
            "materials": [material.name for material in bpy.data.materials],
            "textures": [texture.name for texture in bpy.data.textures]
        }

