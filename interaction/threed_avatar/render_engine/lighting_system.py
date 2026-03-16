"""
光照系统 - 管理场景光照效果
负责动态光照、阴影和环境照明的管理
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class LightType(Enum):
    """光照类型枚举"""
    DIRECTIONAL = "directional"  # 方向光
    POINT = "point"             # 点光源
    SPOT = "spot"               # 聚光灯
    AMBIENT = "ambient"         # 环境光
    AREA = "area"               # 区域光

@dataclass
class LightConfig:
    """光照配置"""
    light_type: LightType
    position: Tuple[float, float, float] = (0, 0, 0)
    direction: Tuple[float, float, float] = (0, 0, -1)
    color: Tuple[float, float, float] = (1, 1, 1)
    intensity: float = 1.0
    range: float = 10.0
    inner_angle: float = 30.0  # 聚光灯内角
    outer_angle: float = 45.0  # 聚光灯外角
    cast_shadows: bool = True
    shadow_resolution: int = 1024
    enabled: bool = True

class Light:
    """光照类"""
    
    def __init__(self, name: str, config: LightConfig):
        self.name = name
        self.config = config
        self.light_id = None
        self.shadow_map = None
        self.is_active = True
        
        # 性能统计
        self.stats = {
            "shadow_updates": 0,
            "intensity_changes": 0,
            "color_changes": 0
        }
        
        logger.info(f"创建光照: {name} ({config.light_type.value})")
    
    def update_position(self, new_position: Tuple[float, float, float]):
        """更新光照位置"""
        self.config.position = new_position
        logger.debug(f"更新光照位置: {self.name} -> {new_position}")
    
    def update_direction(self, new_direction: Tuple[float, float, float]):
        """更新光照方向"""
        self.config.direction = new_direction
        logger.debug(f"更新光照方向: {self.name} -> {new_direction}")
    
    def set_intensity(self, intensity: float):
        """设置光照强度"""
        old_intensity = self.config.intensity
        self.config.intensity = max(0.0, intensity)
        self.stats["intensity_changes"] += 1
        logger.debug(f"设置光照强度: {self.name} {old_intensity} -> {intensity}")
    
    def set_color(self, color: Tuple[float, float, float]):
        """设置光照颜色"""
        self.config.color = color
        self.stats["color_changes"] += 1
        logger.debug(f"设置光照颜色: {self.name} -> {color}")
    
    def toggle_shadows(self, enabled: bool):
        """切换阴影投射"""
        self.config.cast_shadows = enabled
        logger.info(f"{'启用' if enabled else '禁用'}阴影: {self.name}")
    
    def get_light_data(self) -> Dict[str, Any]:
        """获取光照数据（用于着色器）"""
        return {
            "type": self.config.light_type.value,
            "position": self.config.position,
            "direction": self.config.direction,
            "color": self.config.color,
            "intensity": self.config.intensity,
            "range": self.config.range,
            "inner_angle": np.radians(self.config.inner_angle),
            "outer_angle": np.radians(self.config.outer_angle),
            "cast_shadows": self.config.cast_shadows
        }

class LightingSystem:
    """光照系统管理器"""
    
    def __init__(self):
        self.lights: Dict[str, Light] = {}
        self.ambient_light = (0.1, 0.1, 0.1)  # 默认环境光
        self.max_lights = 8  # 最大同时激活的光照数量
        self.shadow_quality = "high"
        self.global_illumination = False
        
        # 光照性能设置
        self.performance_settings = {
            "dynamic_shadows": True,
            "soft_shadows": True,
            "shadow_cascades": 4,
            "max_shadow_distance": 100.0
        }
        
        # 统计信息
        self.stats = {
            "total_lights": 0,
            "active_lights": 0,
            "shadow_casting_lights": 0,
            "light_updates_per_frame": 0
        }
        
        logger.info("初始化光照系统")
    
    def create_light(self, name: str, config: LightConfig) -> Optional[Light]:
        """创建新光照"""
        if name in self.lights:
            logger.warning(f"光照已存在: {name}")
            return self.lights[name]
        
        if len(self.lights) >= self.max_lights:
            logger.error(f"达到最大光照数量限制: {self.max_lights}")
            return None
        
        light = Light(name, config)
        self.lights[name] = light
        self.stats["total_lights"] += 1
        self.stats["active_lights"] += 1
        
        if config.cast_shadows:
            self.stats["shadow_casting_lights"] += 1
        
        logger.info(f"创建光照成功: {name}")
        return light
    
    def remove_light(self, name: str) -> bool:
        """移除光照"""
        if name not in self.lights:
            logger.warning(f"光照不存在: {name}")
            return False
        
        light = self.lights[name]
        if light.config.cast_shadows:
            self.stats["shadow_casting_lights"] -= 1
        
        del self.lights[name]
        self.stats["total_lights"] -= 1
        self.stats["active_lights"] -= 1
        
        logger.info(f"移除光照: {name}")
        return True
    
    def get_light(self, name: str) -> Optional[Light]:
        """获取光照"""
        return self.lights.get(name)
    
    def set_ambient_light(self, color: Tuple[float, float, float]):
        """设置环境光"""
        self.ambient_light = color
        logger.info(f"设置环境光: {color}")
    
    def update_lighting(self, delta_time: float):
        """更新光照系统"""
        self.stats["light_updates_per_frame"] = 0
        
        # 更新所有激活的光照
        for light_name, light in self.lights.items():
            if light.is_active:
                self.stats["light_updates_per_frame"] += 1
                # 这里可以添加每帧的光照更新逻辑
                # 例如：动态光照效果、闪烁等
    
    def get_active_lights_data(self) -> List[Dict[str, Any]]:
        """获取激活光照的数据（用于着色器）"""
        active_lights = []
        
        for light in self.lights.values():
            if light.is_active and light.config.enabled:
                light_data = light.get_light_data()
                light_data["name"] = light.name
                active_lights.append(light_data)
                
                # 限制最大光照数量
                if len(active_lights) >= self.max_lights:
                    break
        
        return active_lights
    
    def enable_global_illumination(self, enabled: bool):
        """启用/禁用全局光照"""
        self.global_illumination = enabled
        logger.info(f"{'启用' if enabled else '禁用'}全局光照")
    
    def set_shadow_quality(self, quality: str):
        """设置阴影质量"""
        valid_qualities = ["low", "medium", "high", "ultra"]
        if quality not in valid_qualities:
            logger.warning(f"无效的阴影质量: {quality}, 使用默认值: high")
            quality = "high"
        
        self.shadow_quality = quality
        
        # 根据质量设置调整参数
        quality_settings = {
            "low": {"shadow_resolution": 512, "cascades": 1},
            "medium": {"shadow_resolution": 1024, "cascades": 2},
            "high": {"shadow_resolution": 2048, "cascades": 4},
            "ultra": {"shadow_resolution": 4096, "cascades": 4}
        }
        
        settings = quality_settings[quality]
        self.performance_settings["shadow_cascades"] = settings["cascades"]
        
        # 更新所有阴影投射光的设置
        for light in self.lights.values():
            if light.config.cast_shadows:
                light.config.shadow_resolution = settings["shadow_resolution"]
        
        logger.info(f"设置阴影质量: {quality}")
    
    def create_time_of_day_lighting(self, time_of_day: float):
        """创建基于时间的动态光照（0.0-1.0，0=午夜，0.5=正午）"""
        # 计算太阳角度
        sun_angle = (time_of_day - 0.25) * 2 * np.pi  # 偏移使正午在顶部
        
        # 太阳位置（在天空中的位置）
        sun_height = np.sin(sun_angle)
        sun_intensity = max(0.0, sun_height)
        
        # 创建或更新方向光（太阳）
        sun_config = LightConfig(
            light_type=LightType.DIRECTIONAL,
            direction=(-np.cos(sun_angle), 0, sun_height),
            color=(1.0, 0.9, 0.8),  # 温暖的阳光
            intensity=sun_intensity,
            cast_shadows=True
        )
        
        if "sun" not in self.lights:
            self.create_light("sun", sun_config)
        else:
            sun_light = self.lights["sun"]
            sun_light.config.direction = sun_config.direction
            sun_light.config.intensity = sun_config.intensity
        
        # 根据时间设置环境光
        if time_of_day < 0.25 or time_of_day > 0.75:  # 夜晚
            ambient_color = (0.05, 0.05, 0.1)  # 蓝色调的夜晚
        elif time_of_day < 0.3 or time_of_day > 0.7:  # 黎明/黄昏
            ambient_color = (0.3, 0.2, 0.1)    # 橙色调的黄昏
        else:  # 白天
            ambient_color = (0.3, 0.3, 0.4)    # 明亮的白天
        
        self.set_ambient_light(ambient_color)
        
        logger.debug(f"更新时间光照: {time_of_day:.2f}, 太阳强度: {sun_intensity:.2f}")
    
    def get_lighting_stats(self) -> Dict[str, Any]:
        """获取光照系统统计信息"""
        stats = self.stats.copy()
        stats["ambient_light"] = self.ambient_light
        stats["global_illumination"] = self.global_illumination
        stats["shadow_quality"] = self.shadow_quality
        stats["performance_settings"] = self.performance_settings
        
        return stats
    
    def cleanup(self):
        """清理光照系统"""
        for light_name in list(self.lights.keys()):
            self.remove_light(light_name)
        
        logger.info("光照系统清理完成")

# 全局光照系统实例
lighting_system = LightingSystem()