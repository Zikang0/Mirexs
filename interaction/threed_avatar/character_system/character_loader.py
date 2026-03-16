"""
角色加载器：加载角色模型
负责3D角色模型的加载、配置和管理
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

from .model_manager import CatModel, CatModelManager, CatModelConfig
from ..render_engine.material_manager import MaterialManager, Material
from data.models.three_d.animations import AnimationManager, AnimationConfig

logger = logging.getLogger(__name__)

class CharacterType(Enum):
    """角色类型"""
    MAIN_CAT = "main_cat"          # 主要猫咪角色
    SUPPORT_CAT = "support_cat"    # 辅助猫咪角色
    HUMAN = "human"                # 人类角色
    CREATURE = "creature"          # 生物角色
    OBJECT = "object"              # 物体角色

@dataclass
class CharacterConfig:
    """角色配置"""
    character_id: str
    character_type: CharacterType
    model_config: CatModelConfig
    scale: float = 1.0
    lod_levels: int = 3
    enable_physics: bool = True
    enable_shadows: bool = True
    material_overrides: Dict[str, str] = None  # 材质覆盖
    animation_overrides: Dict[str, str] = None  # 动画覆盖

@dataclass
class CharacterInstance:
    """角色实例"""
    character_id: str
    model: CatModel
    materials: Dict[str, Material]
    animations: Dict[str, Any]
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    is_visible: bool = True
    current_animation: str = None

class CharacterLoader:
    """角色加载器"""
    
    def __init__(self, model_manager: CatModelManager, 
                 material_manager: MaterialManager,
                 animation_manager: AnimationManager):
        self.model_manager = model_manager
        self.material_manager = material_manager
        self.animation_manager = animation_manager
        
        self.characters: Dict[str, CharacterConfig] = {}
        self.character_instances: Dict[str, CharacterInstance] = {}
        self.character_templates: Dict[str, Dict[str, Any]] = {}
        
        # 资源路径
        self.character_base_path = "./assets/characters/"
        self.animation_base_path = "./assets/animations/"
        self.material_base_path = "./assets/materials/"
        
        # 性能统计
        self.stats = {
            "characters_loaded": 0,
            "instances_created": 0,
            "total_memory_used": 0,
            "load_errors": 0
        }
        
        # 创建基础目录
        self._create_directories()
        
        # 加载默认角色配置
        self._load_default_character_configs()
        
        logger.info("角色加载器初始化完成")
    
    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            self.character_base_path,
            self.animation_base_path,
            self.material_base_path,
            f"{self.character_base_path}configs/",
            f"{self.character_base_path}models/",
            f"{self.character_base_path}textures/"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _load_default_character_configs(self):
        """加载默认角色配置"""
        try:
            # 主要猫咪角色配置
            main_cat_config = CharacterConfig(
                character_id="main_cat",
                character_type=CharacterType.MAIN_CAT,
                model_config=CatModelConfig(
                    model_name="main_cat",
                    model_path=f"{self.character_base_path}models/main_cat.gltf",
                    scale=1.0,
                    lod_levels=3,
                    enable_physics=True,
                    enable_shadows=True
                ),
                scale=1.0,
                material_overrides={
                    "body": "cat_fur_material",
                    "eyes": "cat_eyes_material",
                    "nose": "cat_nose_material"
                },
                animation_overrides={
                    "idle": "cat_idle_animation",
                    "walk": "cat_walk_animation",
                    "run": "cat_run_animation"
                }
            )
            
            self.characters["main_cat"] = main_cat_config
            
            # 辅助猫咪角色配置
            support_cat_config = CharacterConfig(
                character_id="support_cat",
                character_type=CharacterType.SUPPORT_CAT,
                model_config=CatModelConfig(
                    model_name="support_cat",
                    model_path=f"{self.character_base_path}models/support_cat.gltf",
                    scale=0.8,
                    lod_levels=2,
                    enable_physics=True,
                    enable_shadows=True
                ),
                scale=0.8,
                material_overrides={
                    "body": "cat_fur_material_light",
                    "eyes": "cat_eyes_material",
                    "nose": "cat_nose_material"
                }
            )
            
            self.characters["support_cat"] = support_cat_config
            
            logger.info("加载默认角色配置完成")
            
        except Exception as e:
            logger.error(f"加载默认角色配置失败: {e}")
            self.stats["load_errors"] += 1
    
    def load_character_config(self, config_file: str) -> bool:
        """从文件加载角色配置"""
        try:
            config_path = f"{self.character_base_path}configs/{config_file}"
            if not os.path.exists(config_path):
                logger.error(f"角色配置文件不存在: {config_path}")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            character_id = config_data.get("character_id")
            if not character_id:
                logger.error("角色配置缺少character_id")
                return False
            
            # 创建角色配置
            character_config = CharacterConfig(
                character_id=character_id,
                character_type=CharacterType(config_data.get("character_type", "main_cat")),
                model_config=CatModelConfig(
                    model_name=config_data.get("model_name", character_id),
                    model_path=config_data.get("model_path", f"{self.character_base_path}models/{character_id}.gltf"),
                    scale=config_data.get("scale", 1.0),
                    lod_levels=config_data.get("lod_levels", 3),
                    enable_physics=config_data.get("enable_physics", True),
                    enable_shadows=config_data.get("enable_shadows", True)
                ),
                scale=config_data.get("scale", 1.0),
                material_overrides=config_data.get("material_overrides", {}),
                animation_overrides=config_data.get("animation_overrides", {})
            )
            
            self.characters[character_id] = character_config
            logger.info(f"加载角色配置: {character_id}")
            return True
            
        except Exception as e:
            logger.error(f"加载角色配置失败 {config_file}: {e}")
            self.stats["load_errors"] += 1
            return False
    
    def create_character_instance(self, character_id: str, instance_id: str,
                                position: Tuple[float, float, float] = (0, 0, 0),
                                rotation: Tuple[float, float, float, float] = (0, 0, 0, 1)) -> Optional[CharacterInstance]:
        """创建角色实例"""
        if character_id not in self.characters:
            logger.error(f"角色配置不存在: {character_id}")
            return None
        
        if instance_id in self.character_instances:
            logger.warning(f"角色实例已存在: {instance_id}")
            return self.character_instances[instance_id]
        
        try:
            character_config = self.characters[character_id]
            
            # 加载模型
            model = self.model_manager.load_model(character_config.model_config.model_name, 
                                                character_config.model_config)
            if not model or not model.is_loaded:
                logger.error(f"加载角色模型失败: {character_config.model_config.model_name}")
                return None
            
            # 加载材质
            materials = self._load_character_materials(character_config)
            
            # 加载动画
            animations = self._load_character_animations(character_config)
            
            # 创建角色实例
            character_instance = CharacterInstance(
                character_id=character_id,
                model=model,
                materials=materials,
                animations=animations,
                position=position,
                rotation=rotation,
                scale=(character_config.scale, character_config.scale, character_config.scale)
            )
            
            self.character_instances[instance_id] = character_instance
            self.stats["instances_created"] += 1
            
            logger.info(f"创建角色实例: {instance_id} ({character_id})")
            return character_instance
            
        except Exception as e:
            logger.error(f"创建角色实例失败 {instance_id}: {e}")
            self.stats["load_errors"] += 1
            return None
    
    def _load_character_materials(self, character_config: CharacterConfig) -> Dict[str, Material]:
        """加载角色材质"""
        materials = {}
        
        try:
            # 加载材质覆盖
            for material_slot, material_name in character_config.material_overrides.items():
                material = self.material_manager.get_material(material_name)
                if material:
                    materials[material_slot] = material
                else:
                    logger.warning(f"材质不存在: {material_name}，使用默认材质")
                    materials[material_slot] = self.material_manager.get_material("default_pbr")
            
            # 如果没有材质覆盖，使用默认材质
            if not materials:
                materials["default"] = self.material_manager.get_material("default_pbr")
            
            return materials
            
        except Exception as e:
            logger.error(f"加载角色材质失败: {e}")
            return {"default": self.material_manager.get_material("default_pbr")}
    
    def _load_character_animations(self, character_config: CharacterConfig) -> Dict[str, Any]:
        """加载角色动画"""
        animations = {}
        
        try:
            # 加载动画覆盖
            for animation_slot, animation_name in character_config.animation_overrides.items():
                # 创建动画配置
                anim_config = AnimationConfig(
                    name=animation_name,
                    duration=2.0,  # 默认时长
                    fps=30,
                    loop=True
                )
                
                # 加载动画
                animation_file = f"{self.animation_base_path}{animation_name}.json"
                animation = self.animation_manager.load_animation(animation_name, anim_config, animation_file)
                if animation:
                    animations[animation_slot] = animation
            
            # 加载默认动画
            default_animations = ["idle", "walk", "run", "jump"]
            for anim_name in default_animations:
                if anim_name not in animations:
                    anim_config = AnimationConfig(
                        name=f"{character_config.character_id}_{anim_name}",
                        duration=2.0,
                        fps=30,
                        loop=True
                    )
                    
                    animation_file = f"{self.animation_base_path}{character_config.character_id}_{anim_name}.json"
                    animation = self.animation_manager.load_animation(
                        f"{character_config.character_id}_{anim_name}", anim_config, animation_file
                    )
                    if animation:
                        animations[anim_name] = animation
            
            return animations
            
        except Exception as e:
            logger.error(f"加载角色动画失败: {e}")
            return {}
    
    def get_character_instance(self, instance_id: str) -> Optional[CharacterInstance]:
        """获取角色实例"""
        return self.character_instances.get(instance_id)
    
    def update_character_position(self, instance_id: str, position: Tuple[float, float, float]):
        """更新角色位置"""
        if instance_id in self.character_instances:
            character = self.character_instances[instance_id]
            character.position = position
    
    def update_character_rotation(self, instance_id: str, rotation: Tuple[float, float, float, float]):
        """更新角色旋转"""
        if instance_id in self.character_instances:
            character = self.character_instances[instance_id]
            character.rotation = rotation
    
    def play_character_animation(self, instance_id: str, animation_name: str, loop: bool = True) -> bool:
        """播放角色动画"""
        if instance_id not in self.character_instances:
            return False
        
        character = self.character_instances[instance_id]
        
        if animation_name in character.animations:
            animation = character.animations[animation_name]
            if hasattr(animation, 'play'):
                animation.play()
                character.current_animation = animation_name
                
                logger.debug(f"播放角色动画: {instance_id} -> {animation_name}")
                return True
        
        return False
    
    def stop_character_animation(self, instance_id: str):
        """停止角色动画"""
        if instance_id not in self.character_instances:
            return
        
        character = self.character_instances[instance_id]
        
        if character.current_animation and character.current_animation in character.animations:
            animation = character.animations[character.current_animation]
            if hasattr(animation, 'stop'):
                animation.stop()
        
        character.current_animation = None
    
    def set_character_visibility(self, instance_id: str, visible: bool):
        """设置角色可见性"""
        if instance_id in self.character_instances:
            character = self.character_instances[instance_id]
            character.is_visible = visible
    
    def apply_character_material(self, instance_id: str, material_slot: str, material_name: str) -> bool:
        """应用材质到角色"""
        if instance_id not in self.character_instances:
            return False
        
        character = self.character_instances[instance_id]
        material = self.material_manager.get_material(material_name)
        
        if material:
            character.materials[material_slot] = material
            
            # 这里应该实现将材质应用到模型的逻辑
            logger.debug(f"应用材质到角色: {instance_id} -> {material_slot}: {material_name}")
            return True
        
        return False
    
    def get_character_bounding_box(self, instance_id: str) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
        """获取角色包围盒"""
        if instance_id not in self.character_instances:
            return None
        
        character = self.character_instances[instance_id]
        model_info = character.model.get_model_info()
        
        # 简化的包围盒计算
        # 实际应该基于模型顶点数据计算
        center = np.array(character.position)
        size = max(model_info.get("vertex_count", 1000) / 1000, 1.0)  # 基于顶点数量的估算
        
        return (
            tuple(center - size),
            tuple(center + size)
        )
    
    def save_character_template(self, template_id: str, character_config: CharacterConfig):
        """保存角色模板"""
        self.character_templates[template_id] = {
            "character_id": character_config.character_id,
            "character_type": character_config.character_type.value,
            "model_config": {
                "model_name": character_config.model_config.model_name,
                "model_path": character_config.model_config.model_path,
                "scale": character_config.model_config.scale,
                "lod_levels": character_config.model_config.lod_levels,
                "enable_physics": character_config.model_config.enable_physics,
                "enable_shadows": character_config.model_config.enable_shadows
            },
            "scale": character_config.scale,
            "material_overrides": character_config.material_overrides,
            "animation_overrides": character_config.animation_overrides
        }
        
        logger.info(f"保存角色模板: {template_id}")
    
    def load_character_from_template(self, template_id: str, instance_id: str,
                                   position: Tuple[float, float, float] = (0, 0, 0),
                                   rotation: Tuple[float, float, float, float] = (0, 0, 0, 1)) -> Optional[CharacterInstance]:
        """从模板加载角色"""
        if template_id not in self.character_templates:
            logger.error(f"角色模板不存在: {template_id}")
            return None
        
        template_data = self.character_templates[template_id]
        
        # 创建角色配置
        character_config = CharacterConfig(
            character_id=template_data["character_id"],
            character_type=CharacterType(template_data["character_type"]),
            model_config=CatModelConfig(
                model_name=template_data["model_config"]["model_name"],
                model_path=template_data["model_config"]["model_path"],
                scale=template_data["model_config"]["scale"],
                lod_levels=template_data["model_config"]["lod_levels"],
                enable_physics=template_data["model_config"]["enable_physics"],
                enable_shadows=template_data["model_config"]["enable_shadows"]
            ),
            scale=template_data["scale"],
            material_overrides=template_data["material_overrides"],
            animation_overrides=template_data["animation_overrides"]
        )
        
        # 创建角色实例
        return self.create_character_instance(
            character_config.character_id, instance_id, position, rotation
        )
    
    def unload_character_instance(self, instance_id: str) -> bool:
        """卸载角色实例"""
        if instance_id not in self.character_instances:
            return False
        
        character = self.character_instances[instance_id]
        
        # 停止动画
        self.stop_character_animation(instance_id)
        
        # 卸载模型
        if hasattr(character.model, 'unload'):
            character.model.unload()
        
        del self.character_instances[instance_id]
        self.stats["instances_created"] -= 1
        
        logger.info(f"卸载角色实例: {instance_id}")
        return True
    
    def get_loader_stats(self) -> Dict[str, Any]:
        """获取加载器统计信息"""
        stats = self.stats.copy()
        stats["character_configs"] = len(self.characters)
        stats["active_instances"] = len(self.character_instances)
        stats["available_templates"] = len(self.character_templates)
        
        return stats
    
    def get_all_character_instances(self) -> List[str]:
        """获取所有角色实例ID"""
        return list(self.character_instances.keys())
    
    def get_character_configs(self) -> List[str]:
        """获取所有角色配置ID"""
        return list(self.characters.keys())
    
    def cleanup(self):
        """清理加载器"""
        # 卸载所有角色实例
        for instance_id in list(self.character_instances.keys()):
            self.unload_character_instance(instance_id)
        
        self.characters.clear()
        self.character_templates.clear()
        
        logger.info("角色加载器清理完成")

# 全局角色加载器实例
character_loader = CharacterLoader(
    model_manager=CatModelManager(),
    material_manager=MaterialManager(),
    animation_manager=AnimationManager()
)

