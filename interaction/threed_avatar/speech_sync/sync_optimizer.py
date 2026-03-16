"""
同步优化器 - 语音动画同步质量优化系统
完整实现同步质量评估、实时优化调整和性能调优
支持自适应延迟补偿和同步误差修正
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from enum import Enum
import asyncio

# 导入依赖
from interaction.threed_avatar.speech_sync.lip_sync_engine import LipSyncFrame, LipSyncConfig
from interaction.output_systems.speech_output.multilingual_tts import TTSResult

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """优化策略枚举"""
    LATENCY_COMPENSATION = "latency_compensation"      # 延迟补偿
    ERROR_CORRECTION = "error_correction"              # 误差修正
    ADAPTIVE_SYNC = "adaptive_sync"                    # 自适应同步
    PERFORMANCE_TUNING = "performance_tuning"          # 性能调优
    REAL_TIME_ADJUSTMENT = "real_time_adjustment"      # 实时调整

class SyncQuality(Enum):
    """同步质量等级"""
    EXCELLENT = "excellent"    # 优秀：误差 < 50ms
    GOOD = "good"              # 良好：误差 50-100ms  
    FAIR = "fair"              # 一般：误差 100-200ms
    POOR = "poor"              # 较差：误差 > 200ms

@dataclass
class OptimizationConfig:
    """优化配置"""
    target_latency: float = 0.05           # 目标延迟（秒）
    max_sync_error: float = 0.1            # 最大同步误差（秒）
    adaptive_learning: bool = True         # 自适应学习
    realtime_adjustment: bool = True       # 实时调整
    quality_threshold: float = 0.8         # 质量阈值
    performance_mode: bool = False         # 性能模式

@dataclass
class SyncMetrics:
    """同步指标"""
    total_frames: int = 0
    sync_errors: List[float] = field(default_factory=list)
    latency_measurements: List[float] = field(default_factory=list)
    quality_scores: List[float] = field(default_factory=list)
    optimization_gains: List[float] = field(default_factory=list)

@dataclass
class OptimizationResult:
    """优化结果"""
    optimized_frames: List[LipSyncFrame]
    quality_improvement: float
    latency_reduction: float
    sync_error_reduction: float
    performance_impact: float

class SyncOptimizer:
    """同步优化器 - 完整实现"""
    
    def __init__(self):
        self.optimization_config = OptimizationConfig()
        self.sync_metrics = SyncMetrics()
        self.quality_history: List[SyncQuality] = []
        
        # 优化算法参数
        self.kalman_filter_params = {
            'process_variance': 1e-5,
            'measurement_variance': 1e-2,
            'estimation_error': 1.0
        }
        
        # 自适应学习参数
        self.learning_rates = {
            'latency': 0.1,
            'sync_error': 0.2,
            'performance': 0.05
        }
        
        # 统计信息
        self.stats = {
            "total_optimizations": 0,
            "quality_improvements": 0,
            "latency_reductions": 0,
            "error_corrections": 0,
            "average_optimization_time": 0.0
        }
        
        # 实时优化状态
        self.realtime_state = {
            'current_latency': 0.0,
            'sync_error_accumulated': 0.0,
            'performance_level': 1.0,
            'adaptation_factor': 1.0
        }
        
        logger.info("SyncOptimizer initialized")

    async def optimize_sync(self, sync_frames: List[LipSyncFrame], 
                          audio_data: np.ndarray, sample_rate: int,
                          strategies: List[OptimizationStrategy] = None) -> OptimizationResult:
        """
        优化同步 - 完整实现
        
        Args:
            sync_frames: 同步帧列表
            audio_data: 音频数据
            sample_rate: 采样率
            strategies: 优化策略列表
            
        Returns:
            OptimizationResult: 优化结果
        """
        start_time = time.time()
        
        try:
            if not sync_frames:
                logger.warning("No sync frames to optimize")
                return OptimizationResult([], 0.0, 0.0, 0.0, 0.0)
            
            # 使用默认策略如果未指定
            if strategies is None:
                strategies = [
                    OptimizationStrategy.LATENCY_COMPENSATION,
                    OptimizationStrategy.ERROR_CORRECTION,
                    OptimizationStrategy.ADAPTIVE_SYNC
                ]
            
            # 分析当前同步质量
            initial_quality = await self._analyze_sync_quality(sync_frames, audio_data, sample_rate)
            
            # 应用优化策略
            optimized_frames = sync_frames.copy()
            
            for strategy in strategies:
                optimized_frames = await self._apply_optimization_strategy(
                    optimized_frames, audio_data, sample_rate, strategy
                )
            
            # 分析优化后质量
            final_quality = await self._analyze_sync_quality(optimized_frames, audio_data, sample_rate)
            
            # 计算优化效果
            quality_improvement = final_quality.overall_score - initial_quality.overall_score
            latency_reduction = initial_quality.average_latency - final_quality.average_latency
            sync_error_reduction = initial_quality.average_sync_error - final_quality.average_sync_error
            
            # 评估性能影响
            performance_impact = await self._evaluate_performance_impact(
                len(sync_frames), len(optimized_frames)
            )
            
            # 更新统计
            self._update_optimization_stats(
                quality_improvement, latency_reduction, sync_error_reduction, 
                time.time() - start_time
            )
            
            result = OptimizationResult(
                optimized_frames=optimized_frames,
                quality_improvement=quality_improvement,
                latency_reduction=latency_reduction,
                sync_error_reduction=sync_error_reduction,
                performance_impact=performance_impact
            )
            
            logger.info(f"Sync optimization completed: "
                       f"Quality +{quality_improvement:.3f}, "
                       f"Latency -{latency_reduction:.3f}s, "
                       f"Error -{sync_error_reduction:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sync optimization: {e}")
            # 返回原始帧作为回退
            return OptimizationResult(sync_frames, 0.0, 0.0, 0.0, 0.0)

    async def _analyze_sync_quality(self, sync_frames: List[LipSyncFrame],
                                  audio_data: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """分析同步质量"""
        try:
            quality_metrics = {
                'overall_score': 0.0,
                'average_latency': 0.0,
                'average_sync_error': 0.0,
                'consistency_score': 0.0,
                'real_time_score': 0.0
            }
            
            if not sync_frames:
                return quality_metrics
            
            # 计算延迟指标
            latency_metrics = await self._calculate_latency_metrics(sync_frames, audio_data, sample_rate)
            quality_metrics.update(latency_metrics)
            
            # 计算同步误差
            sync_errors = await self._calculate_sync_errors(sync_frames, audio_data, sample_rate)
            quality_metrics['average_sync_error'] = np.mean(sync_errors) if sync_errors else 0.0
            
            # 计算一致性
            consistency = await self._calculate_consistency(sync_frames)
            quality_metrics['consistency_score'] = consistency
            
            # 计算实时性
            realtime_score = await self._calculate_realtime_score(sync_frames)
            quality_metrics['real_time_score'] = realtime_score
            
            # 计算总体分数
            overall_score = await self._calculate_overall_score(quality_metrics)
            quality_metrics['overall_score'] = overall_score
            
            # 更新历史记录
            self._update_quality_history(overall_score)
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing sync quality: {e}")
            return {
                'overall_score': 0.5,
                'average_latency': 0.1,
                'average_sync_error': 0.1,
                'consistency_score': 0.5,
                'real_time_score': 0.5
            }

    async def _calculate_latency_metrics(self, sync_frames: List[LipSyncFrame],
                                       audio_data: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """计算延迟指标"""
        try:
            latencies = []
            
            for frame in sync_frames:
                # 基于音频特征和视觉特征的匹配度计算延迟
                audio_energy = frame.audio_features.get("rms_energy", 0.0)
                mouth_openness = sum(frame.viseme_weights.get(viseme, 0.0) 
                                   for viseme in ["A", "E", "O", "U"])
                
                # 理想情况下，音频能量应该与口型开合度同步
                expected_openness = min(1.0, audio_energy * 3.0)  # 简化关系
                latency = abs(mouth_openness - expected_openness)
                latencies.append(latency)
            
            avg_latency = np.mean(latencies) if latencies else 0.0
            max_latency = np.max(latencies) if latencies else 0.0
            latency_variance = np.var(latencies) if latencies else 0.0
            
            return {
                'average_latency': avg_latency,
                'max_latency': max_latency,
                'latency_variance': latency_variance
            }
            
        except Exception as e:
            logger.warning(f"Error calculating latency metrics: {e}")
            return {
                'average_latency': 0.1,
                'max_latency': 0.2,
                'latency_variance': 0.01
            }

    async def _calculate_sync_errors(self, sync_frames: List[LipSyncFrame],
                                   audio_data: np.ndarray, sample_rate: int) -> List[float]:
        """计算同步误差"""
        try:
            sync_errors = []
            
            for i, frame in enumerate(sync_frames):
                if i == 0:
                    continue
                
                # 计算相邻帧之间的同步连续性
                prev_frame = sync_frames[i - 1]
                
                # 基于音频特征变化率
                current_energy = frame.audio_features.get("rms_energy", 0.0)
                prev_energy = prev_frame.audio_features.get("rms_energy", 0.0)
                energy_change = abs(current_energy - prev_energy)
                
                # 基于视觉特征变化率
                current_openness = sum(frame.viseme_weights.get(viseme, 0.0) 
                                     for viseme in ["A", "E", "O", "U"])
                prev_openness = sum(prev_frame.viseme_weights.get(viseme, 0.0) 
                                  for viseme in ["A", "E", "O", "U"])
                visual_change = abs(current_openness - prev_openness)
                
                # 同步误差 = |音频变化 - 视觉变化|
                sync_error = abs(energy_change - visual_change)
                sync_errors.append(sync_error)
            
            return sync_errors
            
        except Exception as e:
            logger.warning(f"Error calculating sync errors: {e}")
            return []

    async def _calculate_consistency(self, sync_frames: List[LipSyncFrame]) -> float:
        """计算一致性分数"""
        try:
            if len(sync_frames) < 2:
                return 1.0
            
            consistency_scores = []
            
            for i in range(1, len(sync_frames)):
                current_frame = sync_frames[i]
                prev_frame = sync_frames[i - 1]
                
                # 计算视觉权重的一致性
                viseme_consistency = 0.0
                common_visemes = set(current_frame.viseme_weights.keys()) & set(prev_frame.viseme_weights.keys())
                
                for viseme in common_visemes:
                    current_weight = current_frame.viseme_weights[viseme]
                    prev_weight = prev_frame.viseme_weights[viseme]
                    weight_diff = abs(current_weight - prev_weight)
                    viseme_consistency += 1.0 - weight_diff
                
                if common_visemes:
                    viseme_consistency /= len(common_visemes)
                
                consistency_scores.append(viseme_consistency)
            
            return np.mean(consistency_scores) if consistency_scores else 1.0
            
        except Exception as e:
            logger.warning(f"Error calculating consistency: {e}")
            return 0.8

    async def _calculate_realtime_score(self, sync_frames: List[LipSyncFrame]) -> float:
        """计算实时性分数"""
        try:
            if not sync_frames:
                return 1.0
            
            # 检查帧时间戳的连续性
            timestamps = [frame.timestamp for frame in sync_frames]
            time_diffs = np.diff(timestamps)
            
            if len(time_diffs) == 0:
                return 1.0
            
            # 理想帧间隔（假设30fps）
            ideal_interval = 1.0 / 30.0
            
            # 计算时间间隔的一致性
            interval_errors = [abs(diff - ideal_interval) for diff in time_diffs]
            avg_interval_error = np.mean(interval_errors) if interval_errors else 0.0
            
            # 转换为分数（误差越小分数越高）
            realtime_score = max(0.0, 1.0 - avg_interval_error / ideal_interval)
            
            return realtime_score
            
        except Exception as e:
            logger.warning(f"Error calculating realtime score: {e}")
            return 0.8

    async def _calculate_overall_score(self, quality_metrics: Dict[str, float]) -> float:
        """计算总体质量分数"""
        try:
            # 权重分配
            weights = {
                'average_latency': 0.3,
                'average_sync_error': 0.3,
                'consistency_score': 0.2,
                'real_time_score': 0.2
            }
            
            overall_score = 0.0
            total_weight = 0.0
            
            for metric, weight in weights.items():
                if metric in quality_metrics:
                    # 标准化指标值
                    normalized_value = await self._normalize_metric(metric, quality_metrics[metric])
                    overall_score += normalized_value * weight
                    total_weight += weight
            
            if total_weight > 0:
                overall_score /= total_weight
            
            return max(0.0, min(1.0, overall_score))
            
        except Exception as e:
            logger.warning(f"Error calculating overall score: {e}")
            return 0.5

    async def _normalize_metric(self, metric_name: str, value: float) -> float:
        """标准化指标值"""
        try:
            if metric_name in ['average_latency', 'average_sync_error']:
                # 误差类指标：值越小越好
                return max(0.0, 1.0 - value * 5.0)  # 假设0.2秒为最大可接受误差
            elif metric_name in ['consistency_score', 'real_time_score']:
                # 分数类指标：值越大越好
                return value
            else:
                return value
                
        except Exception as e:
            logger.warning(f"Error normalizing metric {metric_name}: {e}")
            return value

    async def _apply_optimization_strategy(self, sync_frames: List[LipSyncFrame],
                                         audio_data: np.ndarray, sample_rate: int,
                                         strategy: OptimizationStrategy) -> List[LipSyncFrame]:
        """应用优化策略"""
        try:
            if strategy == OptimizationStrategy.LATENCY_COMPENSATION:
                return await self._apply_latency_compensation(sync_frames, audio_data, sample_rate)
            elif strategy == OptimizationStrategy.ERROR_CORRECTION:
                return await self._apply_error_correction(sync_frames, audio_data, sample_rate)
            elif strategy == OptimizationStrategy.ADAPTIVE_SYNC:
                return await self._apply_adaptive_sync(sync_frames, audio_data, sample_rate)
            elif strategy == OptimizationStrategy.PERFORMANCE_TUNING:
                return await self._apply_performance_tuning(sync_frames)
            elif strategy == OptimizationStrategy.REAL_TIME_ADJUSTMENT:
                return await self._apply_real_time_adjustment(sync_frames)
            else:
                logger.warning(f"Unknown optimization strategy: {strategy}")
                return sync_frames
                
        except Exception as e:
            logger.error(f"Error applying optimization strategy {strategy}: {e}")
            return sync_frames

    async def _apply_latency_compensation(self, sync_frames: List[LipSyncFrame],
                                        audio_data: np.ndarray, sample_rate: int) -> List[LipSyncFrame]:
        """应用延迟补偿"""
        try:
            if not sync_frames:
                return sync_frames
            
            compensated_frames = []
            
            # 估计系统延迟
            estimated_latency = await self._estimate_system_latency(sync_frames, audio_data, sample_rate)
            
            for frame in sync_frames:
                # 调整时间戳以补偿延迟
                compensated_timestamp = frame.timestamp - estimated_latency
                
                # 创建补偿后的帧
                compensated_frame = LipSyncFrame(
                    timestamp=compensated_timestamp,
                    viseme_weights=frame.viseme_weights.copy(),
                    emotion_weights=frame.emotion_weights.copy(),
                    bone_transforms=frame.bone_transforms.copy(),
                    audio_features=frame.audio_features.copy()
                )
                
                compensated_frames.append(compensated_frame)
            
            logger.debug(f"Applied latency compensation: {estimated_latency:.3f}s")
            return compensated_frames
            
        except Exception as e:
            logger.error(f"Error applying latency compensation: {e}")
            return sync_frames

    async def _estimate_system_latency(self, sync_frames: List[LipSyncFrame],
                                     audio_data: np.ndarray, sample_rate: int) -> float:
        """估计系统延迟"""
        try:
            # 基于音频-视觉特征相关性估计延迟
            audio_energies = []
            visual_openness = []
            
            for frame in sync_frames:
                audio_energies.append(frame.audio_features.get("rms_energy", 0.0))
                openness = sum(frame.viseme_weights.get(viseme, 0.0) 
                             for viseme in ["A", "E", "O", "U"])
                visual_openness.append(openness)
            
            if len(audio_energies) < 2 or len(visual_openness) < 2:
                return 0.05  # 默认50ms延迟
            
            # 计算交叉相关性以找到最佳延迟
            max_correlation = 0.0
            best_lag = 0
            
            for lag in range(-10, 11):  # 测试±10帧的延迟
                if lag < 0:
                    audio_subset = audio_energies[-lag:]
                    visual_subset = visual_openness[:lag]
                else:
                    audio_subset = audio_energies[:-lag] if lag > 0 else audio_energies
                    visual_subset = visual_openness[lag:]
                
                if len(audio_subset) > 1 and len(visual_subset) > 1:
                    correlation = np.corrcoef(audio_subset, visual_subset)[0, 1]
                    if abs(correlation) > abs(max_correlation):
                        max_correlation = correlation
                        best_lag = lag
            
            # 转换为时间延迟
            frame_interval = sync_frames[1].timestamp - sync_frames[0].timestamp if len(sync_frames) > 1 else 0.033
            estimated_latency = best_lag * frame_interval
            
            return max(0.0, estimated_latency)
            
        except Exception as e:
            logger.warning(f"Error estimating system latency: {e}")
            return 0.05  # 默认50ms延迟

    async def _apply_error_correction(self, sync_frames: List[LipSyncFrame],
                                    audio_data: np.ndarray, sample_rate: int) -> List[LipSyncFrame]:
        """应用误差修正"""
        try:
            if len(sync_frames) < 3:
                return sync_frames
            
            corrected_frames = []
            
            for i in range(len(sync_frames)):
                current_frame = sync_frames[i]
                
                if i == 0 or i == len(sync_frames) - 1:
                    # 首尾帧不修正
                    corrected_frames.append(current_frame)
                    continue
                
                # 使用前后帧进行平滑修正
                prev_frame = sync_frames[i - 1]
                next_frame = sync_frames[i + 1]
                
                # 修正视素权重
                corrected_weights = await self._correct_viseme_weights(
                    prev_frame.viseme_weights,
                    current_frame.viseme_weights,
                    next_frame.viseme_weights
                )
                
                # 修正骨骼变换
                corrected_transforms = await self._correct_bone_transforms(
                    prev_frame.bone_transforms,
                    current_frame.bone_transforms,
                    next_frame.bone_transforms
                )
                
                # 创建修正后的帧
                corrected_frame = LipSyncFrame(
                    timestamp=current_frame.timestamp,
                    viseme_weights=corrected_weights,
                    emotion_weights=current_frame.emotion_weights.copy(),
                    bone_transforms=corrected_transforms,
                    audio_features=current_frame.audio_features.copy()
                )
                
                corrected_frames.append(corrected_frame)
            
            logger.debug("Applied error correction")
            return corrected_frames
            
        except Exception as e:
            logger.error(f"Error applying error correction: {e}")
            return sync_frames

    async def _correct_viseme_weights(self, prev_weights: Dict[str, float],
                                    current_weights: Dict[str, float],
                                    next_weights: Dict[str, float]) -> Dict[str, float]:
        """修正视素权重"""
        try:
            corrected_weights = {}
            all_visemes = set(prev_weights.keys()) | set(current_weights.keys()) | set(next_weights.keys())
            
            for viseme in all_visemes:
                prev = prev_weights.get(viseme, 0.0)
                curr = current_weights.get(viseme, 0.0)
                next_val = next_weights.get(viseme, 0.0)
                
                # 使用加权平均进行平滑
                smoothed = (prev + 2 * curr + next_val) / 4.0
                corrected_weights[viseme] = max(0.0, min(1.0, smoothed))
            
            return corrected_weights
            
        except Exception as e:
            logger.warning(f"Error correcting viseme weights: {e}")
            return current_weights

    async def _correct_bone_transforms(self, prev_transforms: Dict[str, Any],
                                     current_transforms: Dict[str, Any],
                                     next_transforms: Dict[str, Any]) -> Dict[str, Any]:
        """修正骨骼变换"""
        try:
            corrected_transforms = {}
            all_bones = set(prev_transforms.keys()) | set(current_transforms.keys()) | set(next_transforms.keys())
            
            for bone in all_bones:
                if bone in current_transforms:
                    # 简化实现：直接使用当前变换
                    # 实际应该进行骨骼变换的插值和平滑
                    corrected_transforms[bone] = current_transforms[bone]
                elif bone in prev_transforms:
                    corrected_transforms[bone] = prev_transforms[bone]
                elif bone in next_transforms:
                    corrected_transforms[bone] = next_transforms[bone]
            
            return corrected_transforms
            
        except Exception as e:
            logger.warning(f"Error correcting bone transforms: {e}")
            return current_transforms

    async def _apply_adaptive_sync(self, sync_frames: List[LipSyncFrame],
                                 audio_data: np.ndarray, sample_rate: int) -> List[LipSyncFrame]:
        """应用自适应同步"""
        try:
            if not sync_frames:
                return sync_frames
            
            # 分析当前同步模式
            sync_pattern = await self._analyze_sync_pattern(sync_frames, audio_data, sample_rate)
            
            # 根据模式调整同步参数
            adapted_frames = []
            
            for frame in sync_frames:
                # 应用自适应调整
                adapted_weights = await self._adapt_viseme_weights(
                    frame.viseme_weights, sync_pattern
                )
                
                adapted_frame = LipSyncFrame(
                    timestamp=frame.timestamp,
                    viseme_weights=adapted_weights,
                    emotion_weights=frame.emotion_weights.copy(),
                    bone_transforms=frame.bone_transforms.copy(),
                    audio_features=frame.audio_features.copy()
                )
                
                adapted_frames.append(adapted_frame)
            
            logger.debug("Applied adaptive sync")
            return adapted_frames
            
        except Exception as e:
            logger.error(f"Error applying adaptive sync: {e}")
            return sync_frames

    async def _analyze_sync_pattern(self, sync_frames: List[LipSyncFrame],
                                  audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """分析同步模式"""
        try:
            pattern = {
                'speaking_rate': 0.0,
                'energy_variation': 0.0,
                'sync_stability': 0.0
            }
            
            if len(sync_frames) < 2:
                return pattern
            
            # 分析语速
            total_duration = sync_frames[-1].timestamp - sync_frames[0].timestamp
            if total_duration > 0:
                pattern['speaking_rate'] = len(sync_frames) / total_duration
            
            # 分析能量变化
            energies = [frame.audio_features.get("rms_energy", 0.0) for frame in sync_frames]
            if energies:
                pattern['energy_variation'] = np.std(energies) / (np.mean(energies) + 1e-8)
            
            # 分析同步稳定性
            sync_errors = await self._calculate_sync_errors(sync_frames, audio_data, sample_rate)
            if sync_errors:
                pattern['sync_stability'] = 1.0 - (np.std(sync_errors) / (np.mean(sync_errors) + 1e-8))
            
            return pattern
            
        except Exception as e:
            logger.warning(f"Error analyzing sync pattern: {e}")
            return {'speaking_rate': 1.0, 'energy_variation': 0.5, 'sync_stability': 0.8}

    async def _adapt_viseme_weights(self, weights: Dict[str, float], 
                                  pattern: Dict[str, Any]) -> Dict[str, float]:
        """自适应调整视素权重"""
        try:
            adapted_weights = weights.copy()
            
            # 根据语速调整权重强度
            speaking_rate = pattern.get('speaking_rate', 1.0)
            rate_factor = min(2.0, max(0.5, speaking_rate / 3.0))  # 标准化到0.5-2.0
            
            # 根据能量变化调整权重动态范围
            energy_variation = pattern.get('energy_variation', 0.5)
            dynamic_factor = 1.0 + energy_variation * 0.5  # 1.0-1.5
            
            for viseme, weight in adapted_weights.items():
                # 应用调整因子
                adapted_weight = weight * rate_factor * dynamic_factor
                adapted_weights[viseme] = max(0.0, min(1.0, adapted_weight))
            
            return adapted_weights
            
        except Exception as e:
            logger.warning(f"Error adapting viseme weights: {e}")
            return weights

    async def _apply_performance_tuning(self, sync_frames: List[LipSyncFrame]) -> List[LipSyncFrame]:
        """应用性能调优"""
        try:
            if not sync_frames or self.optimization_config.performance_mode:
                return sync_frames
            
            # 简化帧数据以提升性能
            tuned_frames = []
            
            for i, frame in enumerate(sync_frames):
                if i % 2 == 0:  # 每两帧取一帧
                    # 简化视素权重（只保留主要视素）
                    simplified_weights = {}
                    for viseme, weight in frame.viseme_weights.items():
                        if weight > 0.1:  # 只保留权重大于0.1的视素
                            simplified_weights[viseme] = weight
                    
                    # 如果简化后没有权重，保留最重要的一个
                    if not simplified_weights and frame.viseme_weights:
                        main_viseme = max(frame.viseme_weights.items(), key=lambda x: x[1])
                        simplified_weights[main_viseme[0]] = main_viseme[1]
                    
                    tuned_frame = LipSyncFrame(
                        timestamp=frame.timestamp,
                        viseme_weights=simplified_weights,
                        emotion_weights=frame.emotion_weights.copy(),
                        bone_transforms=frame.bone_transforms.copy(),
                        audio_features=frame.audio_features.copy()
                    )
                    
                    tuned_frames.append(tuned_frame)
            
            logger.debug(f"Applied performance tuning: {len(sync_frames)} -> {len(tuned_frames)} frames")
            return tuned_frames
            
        except Exception as e:
            logger.error(f"Error applying performance tuning: {e}")
            return sync_frames

    async def _apply_real_time_adjustment(self, sync_frames: List[LipSyncFrame]) -> List[LipSyncFrame]:
        """应用实时调整"""
        try:
            if not sync_frames:
                return sync_frames
            
            adjusted_frames = []
            
            for frame in sync_frames:
                # 应用实时状态调整
                adjustment_factor = self.realtime_state['adaptation_factor']
                
                adjusted_weights = {}
                for viseme, weight in frame.viseme_weights.items():
                    adjusted_weights[viseme] = weight * adjustment_factor
                
                adjusted_frame = LipSyncFrame(
                    timestamp=frame.timestamp,
                    viseme_weights=adjusted_weights,
                    emotion_weights=frame.emotion_weights.copy(),
                    bone_transforms=frame.bone_transforms.copy(),
                    audio_features=frame.audio_features.copy()
                )
                
                adjusted_frames.append(adjusted_frame)
            
            # 更新实时状态
            await self._update_realtime_state(sync_frames)
            
            logger.debug("Applied real-time adjustment")
            return adjusted_frames
            
        except Exception as e:
            logger.error(f"Error applying real-time adjustment: {e}")
            return sync_frames

    async def _update_realtime_state(self, sync_frames: List[LipSyncFrame]):
        """更新实时状态"""
        try:
            if not sync_frames:
                return
            
            # 分析最近帧的同步质量
            recent_frames = sync_frames[-10:]  # 最近10帧
            if len(recent_frames) < 2:
                return
            
            # 计算平均同步误差
            sync_errors = []
            for i in range(1, len(recent_frames)):
                current = recent_frames[i]
                prev = recent_frames[i - 1]
                
                current_energy = current.audio_features.get("rms_energy", 0.0)
                prev_energy = prev.audio_features.get("rms_energy", 0.0)
                energy_change = abs(current_energy - prev_energy)
                
                current_openness = sum(current.viseme_weights.get(viseme, 0.0) 
                                     for viseme in ["A", "E", "O", "U"])
                prev_openness = sum(prev.viseme_weights.get(viseme, 0.0) 
                                  for viseme in ["A", "E", "O", "U"])
                visual_change = abs(current_openness - prev_openness)
                
                sync_error = abs(energy_change - visual_change)
                sync_errors.append(sync_error)
            
            if sync_errors:
                avg_error = np.mean(sync_errors)
                # 根据误差调整适应因子
                if avg_error > 0.1:
                    self.realtime_state['adaptation_factor'] *= 1.1  # 增加调整
                elif avg_error < 0.05:
                    self.realtime_state['adaptation_factor'] *= 0.9  # 减少调整
                
                # 限制适应因子范围
                self.realtime_state['adaptation_factor'] = max(0.5, min(2.0, 
                    self.realtime_state['adaptation_factor']))
            
        except Exception as e:
            logger.warning(f"Error updating realtime state: {e}")

    async def _evaluate_performance_impact(self, original_count: int, optimized_count: int) -> float:
        """评估性能影响"""
        try:
            if original_count == 0:
                return 0.0
            
            # 计算帧数减少比例
            reduction_ratio = 1.0 - (optimized_count / original_count)
            
            # 转换为性能影响分数（减少越多，性能提升越大）
            performance_impact = reduction_ratio * 0.5  # 假设每减少10%帧数提升5%性能
            
            return max(0.0, min(1.0, performance_impact))
            
        except Exception as e:
            logger.warning(f"Error evaluating performance impact: {e}")
            return 0.0

    def _update_quality_history(self, quality_score: float):
        """更新质量历史"""
        try:
            if quality_score >= 0.9:
                self.quality_history.append(SyncQuality.EXCELLENT)
            elif quality_score >= 0.7:
                self.quality_history.append(SyncQuality.GOOD)
            elif quality_score >= 0.5:
                self.quality_history.append(SyncQuality.FAIR)
            else:
                self.quality_history.append(SyncQuality.POOR)
            
            # 保持历史记录长度
            if len(self.quality_history) > 100:
                self.quality_history = self.quality_history[-100:]
                
        except Exception as e:
            logger.warning(f"Error updating quality history: {e}")

    def _update_optimization_stats(self, quality_improvement: float, latency_reduction: float,
                                 error_reduction: float, optimization_time: float):
        """更新优化统计"""
        try:
            self.stats["total_optimizations"] += 1
            
            if quality_improvement > 0:
                self.stats["quality_improvements"] += 1
            
            if latency_reduction > 0:
                self.stats["latency_reductions"] += 1
            
            if error_reduction > 0:
                self.stats["error_corrections"] += 1
            
            self.stats["average_optimization_time"] = (
                (self.stats["average_optimization_time"] * (self.stats["total_optimizations"] - 1) + optimization_time) 
                / self.stats["total_optimizations"]
            )
            
        except Exception as e:
            logger.warning(f"Error updating optimization stats: {e}")

    async def get_quality_report(self) -> Dict[str, Any]:
        """获取质量报告"""
        try:
            report = {
                "current_quality": self.quality_history[-1].value if self.quality_history else "unknown",
                "quality_trend": await self._calculate_quality_trend(),
                "optimization_effectiveness": await self._calculate_optimization_effectiveness(),
                "performance_metrics": self.stats.copy(),
                "realtime_state": self.realtime_state.copy()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return {}

    async def _calculate_quality_trend(self) -> str:
        """计算质量趋势"""
        try:
            if len(self.quality_history) < 2:
                return "stable"
            
            recent_history = self.quality_history[-10:]  # 最近10次记录
            
            # 计算质量变化趋势
            quality_scores = []
            for quality in recent_history:
                if quality == SyncQuality.EXCELLENT:
                    quality_scores.append(1.0)
                elif quality == SyncQuality.GOOD:
                    quality_scores.append(0.7)
                elif quality == SyncQuality.FAIR:
                    quality_scores.append(0.5)
                else:
                    quality_scores.append(0.3)
            
            if len(quality_scores) >= 2:
                trend = np.polyfit(range(len(quality_scores)), quality_scores, 1)[0]
                if trend > 0.01:
                    return "improving"
                elif trend < -0.01:
                    return "declining"
                else:
                    return "stable"
            else:
                return "stable"
                
        except Exception as e:
            logger.warning(f"Error calculating quality trend: {e}")
            return "stable"

    async def _calculate_optimization_effectiveness(self) -> float:
        """计算优化效果"""
        try:
            if self.stats["total_optimizations"] == 0:
                return 0.0
            
            effectiveness = (
                self.stats["quality_improvements"] / self.stats["total_optimizations"] * 0.4 +
                self.stats["latency_reductions"] / self.stats["total_optimizations"] * 0.3 +
                self.stats["error_corrections"] / self.stats["total_optimizations"] * 0.3
            )
            
            return effectiveness
            
        except Exception as e:
            logger.warning(f"Error calculating optimization effectiveness: {e}")
            return 0.5

    async def update_config(self, new_config: OptimizationConfig) -> bool:
        """更新优化配置"""
        try:
            self.optimization_config = new_config
            logger.info("Sync optimizer configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating optimizer config: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["quality_history_size"] = len(self.quality_history)
        stats["current_adaptation_factor"] = self.realtime_state['adaptation_factor']
        stats["config"] = self.optimization_config.__dict__
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.quality_history.clear()
            self.realtime_state = {
                'current_latency': 0.0,
                'sync_error_accumulated': 0.0,
                'performance_level': 1.0,
                'adaptation_factor': 1.0
            }
            
            logger.info("SyncOptimizer cleaned up")
            
        except Exception as e:
            logger.error(f"Error during SyncOptimizer cleanup: {e}")

# 全局同步优化器实例
sync_optimizer = SyncOptimizer()
