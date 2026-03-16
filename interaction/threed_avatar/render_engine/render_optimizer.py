"""
渲染优化器 - 优化渲染性能
负责渲染性能分析、优化策略和动态调整
"""

import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """优化策略枚举"""
    LEVEL_OF_DETAIL = "lod"
    FRUSTUM_CULLING = "frustum_culling"
    OCCLUSION_CULLING = "occlusion_culling"
    TEXTURE_STREAMING = "texture_streaming"
    INSTANCED_RENDERING = "instanced_rendering"
    BATCHING = "batching"
    SHADER_LOD = "shader_lod"

@dataclass
class PerformanceMetrics:
    """性能指标"""
    frame_time: float
    fps: float
    draw_calls: int
    triangle_count: int
    texture_memory: int
    gpu_memory: int
    cpu_usage: float
    gpu_usage: float

@dataclass
class OptimizationConfig:
    """优化配置"""
    target_fps: int = 60
    max_draw_calls: int = 1000
    max_triangles: int = 1000000
    lod_bias: float = 1.0
    enable_culling: bool = True
    texture_quality: str = "high"  # low, medium, high, ultra

class RenderOptimizer:
    """渲染优化器"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=60)  # 保存最近60帧的指标
        self.optimization_config = OptimizationConfig()
        self.active_strategies: Dict[OptimizationStrategy, bool] = {}
        self.performance_thresholds = {
            "critical_fps": 30,
            "warning_fps": 45,
            "target_fps": 60
        }
        
        # 初始化所有策略为启用状态
        for strategy in OptimizationStrategy:
            self.active_strategies[strategy] = True
        
        # LOD配置
        self.lod_config = {
            "distances": [10.0, 25.0, 50.0, 100.0],  # LOD切换距离
            "reduction_factors": [1.0, 0.5, 0.25, 0.1],  # 三角形数量减少比例
            "force_lod_level": None  # 强制LOD级别（用于调试）
        }
        
        # 性能统计
        self.stats = {
            "total_frames": 0,
            "average_fps": 0.0,
            "min_fps": float('inf'),
            "max_fps": 0.0,
            "optimizations_applied": 0,
            "culled_objects": 0
        }
        
        # 自适应优化
        self.adaptive_optimization = {
            "enabled": True,
            "aggressiveness": 0.5,  # 0-1, 优化激进程度
            "last_adjustment_time": 0
        }
        
        logger.info("初始化渲染优化器")
    
    def update_metrics(self, metrics: PerformanceMetrics):
        """更新性能指标"""
        self.metrics_history.append(metrics)
        self.stats["total_frames"] += 1
        
        # 更新FPS统计
        fps_values = [m.fps for m in self.metrics_history]
        self.stats["average_fps"] = np.mean(fps_values)
        self.stats["min_fps"] = min(self.stats["min_fps"], metrics.fps)
        self.stats["max_fps"] = max(self.stats["max_fps"], metrics.fps)
        
        # 检查性能问题并应用优化
        self._check_performance_issues(metrics)
        
        # 自适应优化
        if self.adaptive_optimization["enabled"]:
            self._adaptive_optimization(metrics)
    
    def _check_performance_issues(self, metrics: PerformanceMetrics):
        """检查性能问题"""
        current_fps = metrics.fps
        
        if current_fps < self.performance_thresholds["critical_fps"]:
            self._apply_aggressive_optimizations()
            logger.warning(f"性能危急! FPS: {current_fps:.1f}, 应用激进优化")
            
        elif current_fps < self.performance_thresholds["warning_fps"]:
            self._apply_moderate_optimizations()
            logger.info(f"性能警告! FPS: {current_fps:.1f}, 应用中等优化")
            
        elif current_fps >= self.performance_thresholds["target_fps"]:
            # 性能良好，可以适当提高质量
            self._relax_optimizations()
    
    def _apply_aggressive_optimizations(self):
        """应用激进优化"""
        # 降低LOD偏置（更早切换到低细节模型）
        self.optimization_config.lod_bias = 0.5
        
        # 启用所有剔除策略
        self.active_strategies[OptimizationStrategy.FRUSTUM_CULLING] = True
        self.active_strategies[OptimizationStrategy.OCCLUSION_CULLING] = True
        
        # 降低纹理质量
        self.optimization_config.texture_quality = "low"
        
        self.stats["optimizations_applied"] += 1
    
    def _apply_moderate_optimizations(self):
        """应用中等优化"""
        # 适度调整LOD偏置
        self.optimization_config.lod_bias = 0.8
        
        # 确保剔除策略启用
        self.active_strategies[OptimizationStrategy.FRUSTUM_CULLING] = True
        self.active_strategies[OptimizationStrategy.OCCLUSION_CULLING] = True
        
        # 中等纹理质量
        self.optimization_config.texture_quality = "medium"
        
        self.stats["optimizations_applied"] += 1
    
    def _relax_optimizations(self):
        """放松优化（提高质量）"""
        # 恢复LOD偏置
        if self.optimization_config.lod_bias < 1.0:
            self.optimization_config.lod_bias = min(1.0, self.optimization_config.lod_bias + 0.1)
        
        # 提高纹理质量
        quality_levels = ["low", "medium", "high", "ultra"]
        current_index = quality_levels.index(self.optimization_config.texture_quality)
        if current_index < len(quality_levels) - 1:
            self.optimization_config.texture_quality = quality_levels[current_index + 1]
    
    def _adaptive_optimization(self, metrics: PerformanceMetrics):
        """自适应优化"""
        current_time = time.time()
        time_since_last_adjustment = current_time - self.adaptive_optimization["last_adjustment_time"]
        
        # 每5秒调整一次
        if time_since_last_adjustment < 5.0:
            return
        
        target_fps = self.optimization_config.target_fps
        current_fps = metrics.fps
        
        # 计算性能差距
        performance_gap = (current_fps - target_fps) / target_fps
        
        if performance_gap < -0.2:  # 性能低于目标20%
            # 需要更多优化
            self._increase_optimization_aggressiveness()
        elif performance_gap > 0.1:  # 性能高于目标10%
            # 可以放松优化
            self._decrease_optimization_aggressiveness()
        
        self.adaptive_optimization["last_adjustment_time"] = current_time
    
    def _increase_optimization_aggressiveness(self):
        """增加优化激进程度"""
        aggressiveness = self.adaptive_optimization["aggressiveness"]
        new_aggressiveness = min(1.0, aggressiveness + 0.1)
        self.adaptive_optimization["aggressiveness"] = new_aggressiveness
        
        # 根据激进程度调整配置
        self.optimization_config.lod_bias = 1.0 - (new_aggressiveness * 0.5)
        
        logger.debug(f"增加优化激进程度: {new_aggressiveness:.2f}")
    
    def _decrease_optimization_aggressiveness(self):
        """减少优化激进程度"""
        aggressiveness = self.adaptive_optimization["aggressiveness"]
        new_aggressiveness = max(0.0, aggressiveness - 0.05)
        self.adaptive_optimization["aggressiveness"] = new_aggressiveness
        
        # 根据激进程度调整配置
        self.optimization_config.lod_bias = 1.0 - (new_aggressiveness * 0.5)
        
        logger.debug(f"减少优化激进程度: {new_aggressiveness:.2f}")
    
    def calculate_lod_level(self, distance: float, object_complexity: float = 1.0) -> int:
        """计算LOD级别"""
        if self.lod_config["force_lod_level"] is not None:
            return self.lod_config["force_lod_level"]
        
        # 应用LOD偏置
        adjusted_distance = distance * self.optimization_config.lod_bias
        
        # 根据距离和对象复杂度计算LOD级别
        for i, lod_distance in enumerate(self.lod_config["distances"]):
            if adjusted_distance <= lod_distance * object_complexity:
                return i
        
        # 返回最低LOD级别
        return len(self.lod_config["distances"]) - 1
    
    def should_cull_object(self, position: Tuple[float, float, float], 
                          bounding_radius: float, 
                          view_frustum: Any) -> bool:
        """判断对象是否应该被剔除"""
        if not self.active_strategies[OptimizationStrategy.FRUSTUM_CULLING]:
            return False
        
        # 简化的视锥体剔除检查
        # 实际实现应该使用完整的视锥体平面检查
        culled = self._frustum_cull_check(position, bounding_radius, view_frustum)
        
        if culled:
            self.stats["culled_objects"] += 1
        
        return culled
    
    def _frustum_cull_check(self, position: Tuple[float, float, float], 
                           radius: float, view_frustum: Any) -> bool:
        """视锥体剔除检查（简化实现）"""
        # 这里应该实现完整的视锥体剔除算法
        # 简化实现：总是返回不剔除
        return False
    
    def optimize_render_list(self, render_objects: List[Any], 
                           camera_position: Tuple[float, float, float],
                           view_frustum: Any) -> List[Any]:
        """优化渲染列表"""
        optimized_objects = []
        
        for obj in render_objects:
            # 计算距离
            obj_position = getattr(obj, 'position', (0, 0, 0))
            distance = np.linalg.norm(
                np.array(obj_position) - np.array(camera_position)
            )
            
            # 视锥体剔除
            bounding_radius = getattr(obj, 'bounding_radius', 1.0)
            if self.should_cull_object(obj_position, bounding_radius, view_frustum):
                continue
            
            # 计算LOD级别
            complexity = getattr(obj, 'complexity', 1.0)
            lod_level = self.calculate_lod_level(distance, complexity)
            
            # 设置对象的LOD级别
            obj.lod_level = lod_level
            
            optimized_objects.append(obj)
        
        # 按距离排序（从远到近，用于透明对象渲染）
        optimized_objects.sort(key=lambda x: np.linalg.norm(
            np.array(getattr(x, 'position', (0, 0, 0))) - np.array(camera_position)
        ), reverse=True)
        
        logger.debug(f"渲染列表优化: {len(render_objects)} -> {len(optimized_objects)} 个对象")
        
        return optimized_objects
    
    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []
        avg_fps = self.stats["average_fps"]
        
        if avg_fps < self.performance_thresholds["critical_fps"]:
            recommendations.extend([
                "降低渲染分辨率",
                "禁用阴影",
                "使用最低纹理质量",
                "减少视距",
                "禁用后处理效果"
            ])
        elif avg_fps < self.performance_thresholds["warning_fps"]:
            recommendations.extend([
                "降低纹理质量",
                "减少LOD距离",
                "启用遮挡剔除",
                "减少动态光照数量"
            ])
        elif avg_fps > self.performance_thresholds["target_fps"]:
            recommendations.extend([
                "可以提高纹理质量",
                "增加LOD距离",
                "启用更多后处理效果"
            ])
        
        return recommendations
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """获取详细统计信息"""
        if not self.metrics_history:
            return self.stats
        
        latest_metrics = self.metrics_history[-1]
        
        detailed_stats = self.stats.copy()
        detailed_stats.update({
            "current_fps": latest_metrics.fps,
            "current_frame_time": latest_metrics.frame_time,
            "current_draw_calls": latest_metrics.draw_calls,
            "current_triangle_count": latest_metrics.triangle_count,
            "lod_bias": self.optimization_config.lod_bias,
            "texture_quality": self.optimization_config.texture_quality,
            "active_strategies": [s.value for s, active in self.active_strategies.items() if active],
            "optimization_aggressiveness": self.adaptive_optimization["aggressiveness"],
            "recommendations": self.get_optimization_recommendations()
        })
        
        return detailed_stats
    
    def set_force_lod_level(self, level: Optional[int]):
        """强制设置LOD级别（用于调试）"""
        self.lod_config["force_lod_level"] = level
        if level is not None:
            logger.info(f"强制LOD级别: {level}")
        else:
            logger.info("恢复自动LOD级别")
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_frames": 0,
            "average_fps": 0.0,
            "min_fps": float('inf'),
            "max_fps": 0.0,
            "optimizations_applied": 0,
            "culled_objects": 0
        }
        self.metrics_history.clear()
        logger.info("渲染优化器统计已重置")

# 全局渲染优化器实例
render_optimizer = RenderOptimizer()
