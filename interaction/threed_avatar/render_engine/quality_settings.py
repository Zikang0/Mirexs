"""
质量设置 - 渲染质量配置
负责图形质量设置的统一管理和应用
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class QualityPreset(Enum):
    """质量预设枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"

@dataclass
class GraphicsSettings:
    """图形设置"""
    # 分辨率设置
    resolution_width: int = 1920
    resolution_height: int = 1080
    fullscreen: bool = False
    vsync: bool = True
    
    # 质量设置
    texture_quality: str = "high"  # low, medium, high, ultra
    shadow_quality: str = "high"
    anti_aliasing: str = "fxaa"  # none, fxaa, msaa2x, msaa4x, msaa8x
    anisotropic_filtering: int = 8  # 0, 2, 4, 8, 16
    
    # 高级设置
    view_distance: float = 1000.0
    lod_bias: float = 1.0
    particle_quality: str = "high"
    reflection_quality: str = "medium"
    water_quality: str = "high"
    
    # 后处理效果
    bloom: bool = True
    depth_of_field: bool = False
    motion_blur: bool = False
    chromatic_aberration: bool = False
    film_grain: bool = False
    vignette: bool = True
    
    # 性能设置
    frame_rate_limit: int = 0  # 0 = 无限制
    render_scale: float = 1.0  # 渲染分辨率比例

class QualitySettingsManager:
    """质量设置管理器"""
    
    def __init__(self, config_path: str = "config/graphics_settings.json"):
        self.config_path = Path(config_path)
        self.current_settings = GraphicsSettings()
        self.current_preset = QualityPreset.HIGH
        
        # 预设配置
        self.presets: Dict[QualityPreset, GraphicsSettings] = {
            QualityPreset.LOW: self._create_low_preset(),
            QualityPreset.MEDIUM: self._create_medium_preset(),
            QualityPreset.HIGH: self._create_high_preset(),
            QualityPreset.ULTRA: self._create_ultra_preset()
        }
        
        # 硬件检测结果
        self.hardware_tier = "medium"  # low, medium, high, enthusiast
        
        # 设置变更回调
        self.change_callbacks = []
        
        # 自动保存标记
        self.auto_save = True
        
        logger.info("初始化质量设置管理器")
    
    def _create_low_preset(self) -> GraphicsSettings:
        """创建低质量预设"""
        return GraphicsSettings(
            texture_quality="low",
            shadow_quality="low",
            anti_aliasing="none",
            anisotropic_filtering=0,
            view_distance=500.0,
            lod_bias=0.5,
            particle_quality="low",
            reflection_quality="low",
            water_quality="low",
            bloom=False,
            depth_of_field=False,
            motion_blur=False,
            chromatic_aberration=False,
            film_grain=False,
            vignette=False,
            render_scale=0.75
        )
    
    def _create_medium_preset(self) -> GraphicsSettings:
        """创建中等质量预设"""
        return GraphicsSettings(
            texture_quality="medium",
            shadow_quality="medium",
            anti_aliasing="fxaa",
            anisotropic_filtering=4,
            view_distance=750.0,
            lod_bias=0.8,
            particle_quality="medium",
            reflection_quality="medium",
            water_quality="medium",
            bloom=True,
            depth_of_field=False,
            motion_blur=False,
            chromatic_aberration=False,
            film_grain=False,
            vignette=True,
            render_scale=0.9
        )
    
    def _create_high_preset(self) -> GraphicsSettings:
        """创建高质量预设"""
        return GraphicsSettings(
            texture_quality="high",
            shadow_quality="high",
            anti_aliasing="msaa4x",
            anisotropic_filtering=8,
            view_distance=1000.0,
            lod_bias=1.0,
            particle_quality="high",
            reflection_quality="high",
            water_quality="high",
            bloom=True,
            depth_of_field=False,
            motion_blur=True,
            chromatic_aberration=False,
            film_grain=False,
            vignette=True,
            render_scale=1.0
        )
    
    def _create_ultra_preset(self) -> GraphicsSettings:
        """创建超高质量预设"""
        return GraphicsSettings(
            texture_quality="ultra",
            shadow_quality="ultra",
            anti_aliasing="msaa8x",
            anisotropic_filtering=16,
            view_distance=1500.0,
            lod_bias=1.2,
            particle_quality="ultra",
            reflection_quality="ultra",
            water_quality="ultra",
            bloom=True,
            depth_of_field=True,
            motion_blur=True,
            chromatic_aberration=True,
            film_grain=True,
            vignette=True,
            render_scale=1.0
        )
    
    def detect_hardware_tier(self) -> str:
        """检测硬件等级"""
        try:
            import GPUtil
            
            gpus = GPUtil.getGPUs()
            if not gpus:
                return "low"
            
            # 使用最强大的GPU进行评估
            best_gpu = max(gpus, key=lambda gpu: gpu.memoryTotal)
            
            # 简化的硬件等级评估
            vram_gb = best_gpu.memoryTotal / 1024
            
            if vram_gb < 4:
                return "low"
            elif vram_gb < 8:
                return "medium"
            elif vram_gb < 12:
                return "high"
            else:
                return "enthusiast"
                
        except ImportError:
            logger.warning("GPUtil未安装，使用默认硬件等级: medium")
            return "medium"
        except Exception as e:
            logger.error(f"硬件检测失败: {e}")
            return "medium"
    
    def recommend_preset(self) -> QualityPreset:
        """推荐质量预设"""
        hardware_tier = self.detect_hardware_tier()
        
        recommendation_map = {
            "low": QualityPreset.LOW,
            "medium": QualityPreset.MEDIUM,
            "high": QualityPreset.HIGH,
            "enthusiast": QualityPreset.ULTRA
        }
        
        recommended_preset = recommendation_map.get(hardware_tier, QualityPreset.MEDIUM)
        logger.info(f"硬件等级: {hardware_tier}, 推荐质量预设: {recommended_preset.value}")
        
        return recommended_preset
    
    def apply_preset(self, preset: QualityPreset):
        """应用质量预设"""
        if preset not in self.presets:
            logger.error(f"无效的质量预设: {preset}")
            return False
        
        if preset == QualityPreset.CUSTOM:
            logger.info("切换到自定义设置")
            self.current_preset = preset
            return True
        
        # 应用预设设置
        preset_settings = self.presets[preset]
        self.current_settings = preset_settings
        self.current_preset = preset
        
        logger.info(f"应用质量预设: {preset.value}")
        
        # 触发设置变更回调
        self._notify_setting_changes()
        
        # 自动保存
        if self.auto_save:
            self.save_settings()
        
        return True
    
    def apply_recommended_preset(self):
        """应用推荐的质量预设"""
        recommended = self.recommend_preset()
        return self.apply_preset(recommended)
    
    def update_setting(self, setting_name: str, value: Any):
        """更新单个设置"""
        if not hasattr(self.current_settings, setting_name):
            logger.error(f"无效的设置项: {setting_name}")
            return False
        
        old_value = getattr(self.current_settings, setting_name)
        setattr(self.current_settings, setting_name, value)
        
        # 标记为自定义预设
        self.current_preset = QualityPreset.CUSTOM
        
        logger.debug(f"更新设置: {setting_name} = {value} (原值: {old_value})")
        
        # 触发设置变更回调
        self._notify_setting_changes()
        
        # 自动保存
        if self.auto_save:
            self.save_settings()
        
        return True
    
    def get_setting(self, setting_name: str) -> Any:
        """获取设置值"""
        if hasattr(self.current_settings, setting_name):
            return getattr(self.current_settings, setting_name)
        else:
            logger.error(f"无效的设置项: {setting_name}")
            return None
    
    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        return asdict(self.current_settings)
    
    def register_change_callback(self, callback):
        """注册设置变更回调"""
        if callback not in self.change_callbacks:
            self.change_callbacks.append(callback)
            logger.debug(f"注册设置变更回调: {callback.__name__}")
    
    def unregister_change_callback(self, callback):
        """注销设置变更回调"""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
            logger.debug(f"注销设置变更回调: {callback.__name__}")
    
    def _notify_setting_changes(self):
        """通知设置变更"""
        for callback in self.change_callbacks:
            try:
                callback(self.current_settings)
            except Exception as e:
                logger.error(f"设置变更回调执行失败: {e}")
    
    def load_settings(self) -> bool:
        """加载设置"""
        try:
            if not self.config_path.exists():
                logger.warning(f"设置文件不存在: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # 加载基本设置
            if 'current_settings' in settings_data:
                loaded_settings = GraphicsSettings(**settings_data['current_settings'])
                self.current_settings = loaded_settings
            
            # 加载预设信息
            if 'current_preset' in settings_data:
                preset_name = settings_data['current_preset']
                try:
                    self.current_preset = QualityPreset(preset_name)
                except ValueError:
                    self.current_preset = QualityPreset.CUSTOM
            
            logger.info(f"加载质量设置: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载质量设置失败: {e}")
            return False
    
    def save_settings(self) -> bool:
        """保存设置"""
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            settings_data = {
                'current_settings': asdict(self.current_settings),
                'current_preset': self.current_preset.value,
                'version': '1.0'
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"保存质量设置: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存质量设置失败: {e}")
            return False
    
    def reset_to_defaults(self):
        """重置为默认设置"""
        self.current_settings = GraphicsSettings()
        self.current_preset = QualityPreset.HIGH
        
        logger.info("重置为默认质量设置")
        
        # 触发设置变更回调
        self._notify_setting_changes()
        
        # 自动保存
        if self.auto_save:
            self.save_settings()
    
    def get_preset_comparison(self) -> Dict[str, Dict[str, Any]]:
        """获取预设比较信息"""
        comparison = {}
        
        for preset, settings in self.presets.items():
            comparison[preset.value] = {
                "texture_quality": settings.texture_quality,
                "shadow_quality": settings.shadow_quality,
                "anti_aliasing": settings.anti_aliasing,
                "anisotropic_filtering": settings.anisotropic_filtering,
                "view_distance": settings.view_distance,
                "render_scale": settings.render_scale
            }
        
        return comparison
    
    def get_performance_impact(self, setting_name: str) -> str:
        """获取设置项的性能影响评估"""
        performance_impact = {
            "resolution_width": "high",
            "resolution_height": "high",
            "texture_quality": "medium",
            "shadow_quality": "high",
            "anti_aliasing": "high",
            "anisotropic_filtering": "low",
            "view_distance": "medium",
            "lod_bias": "low",
            "particle_quality": "medium",
            "reflection_quality": "high",
            "water_quality": "medium",
            "bloom": "low",
            "depth_of_field": "medium",
            "motion_blur": "medium",
            "render_scale": "high"
        }
        
        return performance_impact.get(setting_name, "unknown")
    
    def validate_settings(self) -> List[str]:
        """验证设置的有效性"""
        warnings = []
        
        # 检查分辨率合理性
        if self.current_settings.resolution_width < 800 or self.current_settings.resolution_height < 600:
            warnings.append("分辨率过低可能影响视觉体验")
        
        # 检查渲染比例
        if self.current_settings.render_scale < 0.5:
            warnings.append("渲染比例过低可能导致图像模糊")
        
        # 检查视野距离
        if self.current_settings.view_distance < 100:
            warnings.append("视野距离过近可能影响游戏体验")
        
        return warnings

# 全局质量设置管理器实例
quality_settings_manager = QualitySettingsManager()

