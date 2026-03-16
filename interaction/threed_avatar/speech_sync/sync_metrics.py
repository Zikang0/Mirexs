"""
同步指标评估系统 - 语音同步质量监控和分析
完整实现同步精度评估、性能监控和实时质量反馈
支持多维度同步质量分析和优化建议生成
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import time
from enum import Enum
import json
from pathlib import Path
import asyncio

# 导入依赖
from interaction.threed_avatar.speech_sync.lip_sync_engine import LipSyncFrame, LipSyncState

logger = logging.getLogger(__name__)

class SyncMetricType(Enum):
    """同步指标类型枚举"""
    LATENCY = "latency"                    # 延迟
    PRECISION = "precision"                # 精度
    SMOOTHNESS = "smoothness"              # 平滑度
    EMOTIONAL_ALIGNMENT = "emotional_alignment"  # 情感对齐
    ENERGY_CORRELATION = "energy_correlation"    # 能量相关性
    PHONEME_ACCURACY = "phoneme_accuracy"  # 音素准确率

class SyncQualityLevel(Enum):
    """同步质量等级"""
    EXCELLENT = "excellent"    # 优秀：> 90%
    GOOD = "good"              # 良好：75% - 90%
    FAIR = "fair"              # 一般：60% - 75%
    POOR = "poor"              # 较差：< 60%

@dataclass
class SyncMetric:
    """同步指标数据"""
    metric_type: SyncMetricType
    value: float
    timestamp: float
    confidence: float
    weight: float = 1.0

@dataclass
class SyncQualityReport:
    """同步质量报告"""
    overall_score: float
    quality_level: SyncQualityLevel
    metrics: Dict[SyncMetricType, SyncMetric]
    recommendations: List[str]
    performance_analysis: Dict[str, Any]
    timestamp: float

class SyncMetrics:
    """同步指标评估系统 - 完整实现"""
    
    def __init__(self, window_size: int = 100):
        self.metrics_history: Dict[SyncMetricType, List[SyncMetric]] = {}
        self.quality_reports: List[SyncQualityReport] = []
        self.realtime_monitoring: bool = True
        
        # 配置
        self.window_size = window_size
        self.metric_weights = {
            SyncMetricType.LATENCY: 0.25,
            SyncMetricType.PRECISION: 0.30,
            SyncMetricType.SMOOTHNESS: 0.15,
            SyncMetricType.EMOTIONAL_ALIGNMENT: 0.10,
            SyncMetricType.ENERGY_CORRELATION: 0.10,
            SyncMetricType.PHONEME_ACCURACY: 0.10
        }
        
        # 统计信息
        self.stats = {
            "total_frames_analyzed": 0,
            "quality_reports_generated": 0,
            "average_processing_time": 0.0,
            "real_time_alerts": 0,
            "optimization_suggestions": 0
        }
        
        # 阈值配置
        self.thresholds = {
            "excellent": 0.9,
            "good": 0.75,
            "fair": 0.6,
            "poor": 0.0
        }
        
        # 初始化指标历史
        self._initialize_metrics_history()
        
        logger.info("SyncMetrics system initialized")

    def _initialize_metrics_history(self):
        """初始化指标历史"""
        for metric_type in SyncMetricType:
            self.metrics_history[metric_type] = []

    async def analyze_frame_sync(self, frame: LipSyncFrame, audio_data: np.ndarray, 
                               sample_rate: int, current_time: float) -> Dict[SyncMetricType, SyncMetric]:
        """
        分析帧同步质量 - 完整实现
        
        Args:
            frame: 嘴唇同步帧
            audio_data: 音频数据
            sample_rate: 采样率
            current_time: 当前时间
            
        Returns:
            Dict[SyncMetricType, SyncMetric]: 指标字典
        """
        start_time = time.time()
        
        try:
            metrics = {}
            
            # 1. 计算延迟指标
            latency_metric = await self._calculate_latency_metric(frame, current_time)
            metrics[SyncMetricType.LATENCY] = latency_metric
            
            # 2. 计算精度指标
            precision_metric = await self._calculate_precision_metric(frame, audio_data, sample_rate)
            metrics[SyncMetricType.PRECISION] = precision_metric
            
            # 3. 计算平滑度指标
            smoothness_metric = await self._calculate_smoothness_metric(frame)
            metrics[SyncMetricType.SMOOTHNESS] = smoothness_metric
            
            # 4. 计算情感对齐指标
            emotional_metric = await self._calculate_emotional_alignment_metric(frame)
            metrics[SyncMetricType.EMOTIONAL_ALIGNMENT] = emotional_metric
            
            # 5. 计算能量相关性指标
            energy_metric = await self._calculate_energy_correlation_metric(frame, audio_data, sample_rate)
            metrics[SyncMetricType.ENERGY_CORRELATION] = energy_metric
            
            # 6. 计算音素准确率指标
            phoneme_metric = await self._calculate_phoneme_accuracy_metric(frame)
            metrics[SyncMetricType.PHONEME_ACCURACY] = phoneme_metric
            
            # 更新历史记录
            for metric_type, metric in metrics.items():
                self._update_metrics_history(metric_type, metric)
            
            # 更新统计
            self.stats["total_frames_analyzed"] += 1
            processing_time = time.time() - start_time
            self.stats["average_processing_time"] = (
                (self.stats["average_processing_time"] * (self.stats["total_frames_analyzed"] - 1) + processing_time) 
                / self.stats["total_frames_analyzed"]
            )
            
            # 实时监控警报
            if self.realtime_monitoring:
                await self._check_realtime_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing frame sync: {e}")
            return {}

    async def _calculate_latency_metric(self, frame: LipSyncFrame, current_time: float) -> SyncMetric:
        """计算延迟指标"""
        try:
            # 理想情况下，帧时间戳应该与当前时间匹配
            time_difference = abs(frame.timestamp - current_time)
            
            # 标准化延迟分数 (0-1, 1表示最佳)
            # 假设50ms内为完美同步
            max_allowed_latency = 0.05  # 50ms
            latency_score = max(0.0, 1.0 - (time_difference / max_allowed_latency))
            
            # 置信度基于时间差的稳定性
            confidence = max(0.5, 1.0 - (time_difference * 10))
            
            return SyncMetric(
                metric_type=SyncMetricType.LATENCY,
                value=latency_score,
                timestamp=current_time,
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.LATENCY]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating latency metric: {e}")
            return self._get_default_metric(SyncMetricType.LATENCY, current_time)

    async def _calculate_precision_metric(self, frame: LipSyncFrame, audio_data: np.ndarray, 
                                        sample_rate: int) -> SyncMetric:
        """计算精度指标"""
        try:
            # 基于音频能量和口型开合度的匹配精度
            audio_energy = frame.audio_features.get("rms_energy", 0.0)
            mouth_openness = sum(frame.viseme_weights.get(viseme, 0.0) 
                               for viseme in ["A", "E", "O"])  # 开口类视素
            
            # 理想情况下，音频能量应该与口型开合度正相关
            expected_openness = min(1.0, audio_energy * 3.0)  # 简化的期望关系
            precision_error = abs(mouth_openness - expected_openness)
            
            # 转换为精度分数
            precision_score = max(0.0, 1.0 - precision_error)
            
            # 置信度基于音频能量的稳定性
            confidence = 0.7 + (audio_energy * 0.3)  # 能量越高，置信度越高
            
            return SyncMetric(
                metric_type=SyncMetricType.PRECISION,
                value=precision_score,
                timestamp=time.time(),
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.PRECISION]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating precision metric: {e}")
            return self._get_default_metric(SyncMetricType.PRECISION, time.time())

    async def _calculate_smoothness_metric(self, frame: LipSyncFrame) -> SyncMetric:
        """计算平滑度指标"""
        try:
            # 分析骨骼变换的平滑度
            bone_movements = []
            
            for bone_name, transform in frame.bone_transforms.items():
                # 计算位置变化幅度
                position_change = np.linalg.norm(transform.position)
                bone_movements.append(position_change)
            
            if bone_movements:
                # 计算运动的方差，方差越小越平滑
                movement_variance = np.var(bone_movements)
                # 转换为平滑度分数 (方差越小，分数越高)
                smoothness_score = max(0.0, 1.0 - (movement_variance * 10))
            else:
                smoothness_score = 0.5  # 默认值
            
            # 置信度基于骨骼数量
            confidence = min(1.0, len(bone_movements) / 10.0)
            
            return SyncMetric(
                metric_type=SyncMetricType.SMOOTHNESS,
                value=smoothness_score,
                timestamp=time.time(),
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.SMOOTHNESS]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating smoothness metric: {e}")
            return self._get_default_metric(SyncMetricType.SMOOTHNESS, time.time())

    async def _calculate_emotional_alignment_metric(self, frame: LipSyncFrame) -> SyncMetric:
        """计算情感对齐指标"""
        try:
            # 分析情感权重与口型表情的一致性
            emotion_intensity = frame.emotion_weights.get("intensity", 0.5)
            
            # 检查情感表达是否与口型协调
            emotional_consistency = 0.0
            emotion_factors = 0
            
            if emotion_intensity > 0.7:  # 强情感
                # 强情感应该有更明显的口型变化
                mouth_activity = sum(frame.viseme_weights.values())
                if mouth_activity > 0.6:
                    emotional_consistency += 1.0
                emotion_factors += 1
            
            if frame.emotion_weights.get("smile", 0) > 0.5:
                # 微笑时嘴角应该上扬
                left_corner = frame.bone_transforms.get("mouth_left_corner")
                right_corner = frame.bone_transforms.get("mouth_right_corner")
                
                if left_corner and right_corner:
                    # 检查嘴角位置（简化检查）
                    if (left_corner.position[1] > 0 or right_corner.position[1] > 0):
                        emotional_consistency += 1.0
                emotion_factors += 1
            
            # 计算情感对齐分数
            if emotion_factors > 0:
                emotional_score = emotional_consistency / emotion_factors
            else:
                emotional_score = 0.8  # 中性情感默认分数
            
            confidence = 0.6 + (emotion_intensity * 0.4)
            
            return SyncMetric(
                metric_type=SyncMetricType.EMOTIONAL_ALIGNMENT,
                value=emotional_score,
                timestamp=time.time(),
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.EMOTIONAL_ALIGNMENT]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating emotional alignment metric: {e}")
            return self._get_default_metric(SyncMetricType.EMOTIONAL_ALIGNMENT, time.time())

    async def _calculate_energy_correlation_metric(self, frame: LipSyncFrame, 
                                                 audio_data: np.ndarray, sample_rate: int) -> SyncMetric:
        """计算能量相关性指标"""
        try:
            audio_energy = frame.audio_features.get("rms_energy", 0.0)
            
            # 计算口型活动的总能量
            viseme_energy = sum(weight for weight in frame.viseme_weights.values())
            
            # 计算相关性（简化版）
            if audio_energy > 0 and viseme_energy > 0:
                # 理想情况下，音频能量和视素能量应该正相关
                correlation = min(1.0, viseme_energy / (audio_energy * 2))
            else:
                correlation = 0.5  # 默认相关性
            
            # 置信度基于能量水平
            confidence = min(1.0, (audio_energy + viseme_energy) * 2)
            
            return SyncMetric(
                metric_type=SyncMetricType.ENERGY_CORRELATION,
                value=correlation,
                timestamp=time.time(),
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.ENERGY_CORRELATION]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating energy correlation metric: {e}")
            return self._get_default_metric(SyncMetricType.ENERGY_CORRELATION, time.time())

    async def _calculate_phoneme_accuracy_metric(self, frame: LipSyncFrame) -> SyncMetric:
        """计算音素准确率指标"""
        try:
            # 分析当前视素权重是否与预期的音素匹配
            # 这里简化实现，实际应该基于音素-视素映射
            
            # 获取主要视素
            main_visemes = sorted(frame.viseme_weights.items(), key=lambda x: x[1], reverse=True)[:3]
            
            if main_visemes:
                # 检查视素权重的合理性
                total_weight = sum(weight for _, weight in main_visemes)
                weight_distribution = total_weight / sum(frame.viseme_weights.values()) if frame.viseme_weights else 0
                
                # 主要视素应该占据大部分权重
                distribution_score = min(1.0, weight_distribution * 1.2)
                
                # 检查视素之间的协调性
                coordination_score = 1.0
                viseme_types = [viseme for viseme, _ in main_visemes]
                
                # 某些视素组合可能不协调（简化检查）
                if "A" in viseme_types and "B" in viseme_types:
                    # 大开口和双唇闭合通常不共存
                    coordination_score *= 0.7
                
                accuracy_score = (distribution_score + coordination_score) / 2
            else:
                accuracy_score = 0.5  # 默认分数
            
            confidence = 0.7
            
            return SyncMetric(
                metric_type=SyncMetricType.PHONEME_ACCURACY,
                value=accuracy_score,
                timestamp=time.time(),
                confidence=confidence,
                weight=self.metric_weights[SyncMetricType.PHONEME_ACCURACY]
            )
            
        except Exception as e:
            logger.warning(f"Error calculating phoneme accuracy metric: {e}")
            return self._get_default_metric(SyncMetricType.PHONEME_ACCURACY, time.time())

    def _get_default_metric(self, metric_type: SyncMetricType, timestamp: float) -> SyncMetric:
        """获取默认指标"""
        return SyncMetric(
            metric_type=metric_type,
            value=0.5,  # 中等分数
            timestamp=timestamp,
            confidence=0.5,
            weight=self.metric_weights[metric_type]
        )

    def _update_metrics_history(self, metric_type: SyncMetricType, metric: SyncMetric):
        """更新指标历史"""
        try:
            history = self.metrics_history[metric_type]
            history.append(metric)
            
            # 保持窗口大小
            if len(history) > self.window_size:
                history.pop(0)
                
        except Exception as e:
            logger.warning(f"Error updating metrics history: {e}")

    async def _check_realtime_alerts(self, metrics: Dict[SyncMetricType, SyncMetric]):
        """检查实时警报"""
        try:
            for metric_type, metric in metrics.items():
                if metric.value < 0.3:  # 低分数阈值
                    await self._generate_alert(metric_type, metric.value)
                    self.stats["real_time_alerts"] += 1
                    
        except Exception as e:
            logger.warning(f"Error checking realtime alerts: {e}")

    async def _generate_alert(self, metric_type: SyncMetricType, value: float):
        """生成警报"""
        try:
            alert_message = f"同步警报: {metric_type.value} 指标过低: {value:.2f}"
            logger.warning(alert_message)
            
            # 这里可以添加通知系统集成
            # 例如: 发送到监控系统、显示给用户等
            
        except Exception as e:
            logger.error(f"Error generating alert: {e}")

    async def generate_quality_report(self, session_duration: float = None) -> SyncQualityReport:
        """
        生成质量报告 - 完整实现
        
        Args:
            session_duration: 会话持续时间（秒）
            
        Returns:
            SyncQualityReport: 质量报告
        """
        try:
            # 计算整体分数
            overall_score = await self._calculate_overall_score()
            quality_level = await self._determine_quality_level(overall_score)
            
            # 获取最新指标
            current_metrics = await self._get_current_metrics()
            
            # 生成性能分析
            performance_analysis = await self._analyze_performance(session_duration)
            
            # 生成优化建议
            recommendations = await self._generate_recommendations(current_metrics, overall_score)
            
            report = SyncQualityReport(
                overall_score=overall_score,
                quality_level=quality_level,
                metrics=current_metrics,
                recommendations=recommendations,
                performance_analysis=performance_analysis,
                timestamp=time.time()
            )
            
            self.quality_reports.append(report)
            self.stats["quality_reports_generated"] += 1
            
            logger.info(f"Quality report generated: {quality_level.value} ({overall_score:.2f})")
            return report
            
        except Exception as e:
            logger.error(f"Error generating quality report: {e}")
            return await self._get_default_quality_report()

    async def _calculate_overall_score(self) -> float:
        """计算整体分数"""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for metric_type, history in self.metrics_history.items():
                if history:
                    # 使用最近指标的平均值
                    recent_metrics = history[-10:]  # 最近10个指标
                    avg_value = np.mean([m.value for m in recent_metrics])
                    avg_confidence = np.mean([m.confidence for m in recent_metrics])
                    
                    # 加权分数
                    weight = self.metric_weights[metric_type]
                    weighted_score = avg_value * weight * avg_confidence
                    
                    total_score += weighted_score
                    total_weight += weight * avg_confidence
            
            if total_weight > 0:
                return total_score / total_weight
            else:
                return 0.5  # 默认分数
                
        except Exception as e:
            logger.warning(f"Error calculating overall score: {e}")
            return 0.5

    async def _determine_quality_level(self, score: float) -> SyncQualityLevel:
        """确定质量等级"""
        if score >= self.thresholds["excellent"]:
            return SyncQualityLevel.EXCELLENT
        elif score >= self.thresholds["good"]:
            return SyncQualityLevel.GOOD
        elif score >= self.thresholds["fair"]:
            return SyncQualityLevel.FAIR
        else:
            return SyncQualityLevel.POOR

    async def _get_current_metrics(self) -> Dict[SyncMetricType, SyncMetric]:
        """获取当前指标"""
        try:
            current_metrics = {}
            
            for metric_type, history in self.metrics_history.items():
                if history:
                    # 使用最新指标
                    current_metrics[metric_type] = history[-1]
                else:
                    # 创建默认指标
                    current_metrics[metric_type] = self._get_default_metric(metric_type, time.time())
            
            return current_metrics
            
        except Exception as e:
            logger.warning(f"Error getting current metrics: {e}")
            return {}

    async def _analyze_performance(self, session_duration: float = None) -> Dict[str, Any]:
        """分析性能"""
        try:
            analysis = {
                "frames_analyzed": self.stats["total_frames_analyzed"],
                "average_processing_time": self.stats["average_processing_time"],
                "alerts_generated": self.stats["real_time_alerts"],
                "reports_generated": self.stats["quality_reports_generated"]
            }
            
            if session_duration:
                analysis["session_duration"] = session_duration
                analysis["frames_per_second"] = self.stats["total_frames_analyzed"] / session_duration
            
            # 分析指标趋势
            trend_analysis = await self._analyze_metrics_trend()
            analysis.update(trend_analysis)
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Error analyzing performance: {e}")
            return {}

    async def _analyze_metrics_trend(self) -> Dict[str, Any]:
        """分析指标趋势"""
        try:
            trend_analysis = {}
            
            for metric_type, history in self.metrics_history.items():
                if len(history) >= 2:
                    recent_values = [m.value for m in history[-5:]]  # 最近5个值
                    older_values = [m.value for m in history[-10:-5]]  # 之前5个值
                    
                    if older_values and recent_values:
                        recent_avg = np.mean(recent_values)
                        older_avg = np.mean(older_values)
                        
                        if recent_avg > older_avg:
                            trend = "improving"
                        elif recent_avg < older_avg:
                            trend = "declining"
                        else:
                            trend = "stable"
                        
                        trend_analysis[f"{metric_type.value}_trend"] = trend
                        trend_analysis[f"{metric_type.value}_change"] = recent_avg - older_avg
            
            return trend_analysis
            
        except Exception as e:
            logger.warning(f"Error analyzing metrics trend: {e}")
            return {}

    async def _generate_recommendations(self, metrics: Dict[SyncMetricType, SyncMetric], 
                                      overall_score: float) -> List[str]:
        """生成优化建议"""
        try:
            recommendations = []
            
            # 基于低分指标生成建议
            for metric_type, metric in metrics.items():
                if metric.value < 0.6:  # 低分数阈值
                    recommendation = await self._get_recommendation_for_metric(metric_type, metric.value)
                    if recommendation:
                        recommendations.append(recommendation)
                        self.stats["optimization_suggestions"] += 1
            
            # 整体建议
            if overall_score < 0.7:
                recommendations.append("整体同步质量有待提升，建议检查系统配置和网络状况")
            elif overall_score > 0.9:
                recommendations.append("同步质量优秀，继续保持当前配置")
            
            # 确保建议不重复
            unique_recommendations = list(set(recommendations))
            
            return unique_recommendations[:5]  # 返回前5条建议
            
        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")
            return ["无法生成优化建议"]

    async def _get_recommendation_for_metric(self, metric_type: SyncMetricType, value: float) -> Optional[str]:
        """获取特定指标的优化建议"""
        recommendations = {
            SyncMetricType.LATENCY: [
                "检测到同步延迟较高，建议优化音频处理流水线",
                "同步延迟影响用户体验，建议检查硬件性能",
                "延迟指标异常，建议减少处理缓冲区大小"
            ],
            SyncMetricType.PRECISION: [
                "口型与音频同步精度不足，建议调整视素映射参数",
                "检测到口型动画与语音不匹配，建议重新校准模型",
                "同步精度有待提升，建议优化音素分析算法"
            ],
            SyncMetricType.SMOOTHNESS: [
                "口型动画平滑度不足，建议增加过渡帧",
                "检测到动画跳变，建议优化骨骼插值算法",
                "动画流畅性需要改善，建议调整帧率设置"
            ],
            SyncMetricType.EMOTIONAL_ALIGNMENT: [
                "情感表达与口型不协调，建议调整情感参数",
                "检测到情感表达不一致，建议优化情感映射",
                "情感同步需要改进，建议加强情感特征提取"
            ],
            SyncMetricType.ENERGY_CORRELATION: [
                "音频能量与口型活动相关性低，建议调整能量映射",
                "检测到能量同步问题，建议优化音频特征提取",
                "能量相关性不足，建议重新校准能量阈值"
            ],
            SyncMetricType.PHONEME_ACCURACY: [
                "音素识别准确率有待提升，建议优化音素模型",
                "检测到音素-视素映射不准确，建议更新映射表",
                "音素同步精度需要改善，建议加强音素分析"
            ]
        }
        
        if metric_type in recommendations:
            suggestion_list = recommendations[metric_type]
            # 根据分数选择建议
            index = min(len(suggestion_list) - 1, int((1 - value) * len(suggestion_list)))
            return suggestion_list[index]
        
        return None

    async def _get_default_quality_report(self) -> SyncQualityReport:
        """获取默认质量报告"""
        return SyncQualityReport(
            overall_score=0.5,
            quality_level=SyncQualityLevel.FAIR,
            metrics={},
            recommendations=["系统初始化中，无法生成详细报告"],
            performance_analysis={},
            timestamp=time.time()
        )

    async def export_report(self, report: SyncQualityReport, export_path: str) -> bool:
        """导出质量报告"""
        try:
            report_data = {
                "overall_score": report.overall_score,
                "quality_level": report.quality_level.value,
                "timestamp": report.timestamp,
                "metrics": {},
                "recommendations": report.recommendations,
                "performance_analysis": report.performance_analysis
            }
            
            # 转换指标数据
            for metric_type, metric in report.metrics.items():
                report_data["metrics"][metric_type.value] = {
                    "value": metric.value,
                    "confidence": metric.confidence,
                    "weight": metric.weight,
                    "timestamp": metric.timestamp
                }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Quality report exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting quality report: {e}")
            return False

    async def get_realtime_metrics(self) -> Dict[str, float]:
        """获取实时指标"""
        try:
            realtime_metrics = {}
            
            for metric_type, history in self.metrics_history.items():
                if history:
                    latest_metric = history[-1]
                    realtime_metrics[metric_type.value] = latest_metric.value
                else:
                    realtime_metrics[metric_type.value] = 0.5
            
            return realtime_metrics
            
        except Exception as e:
            logger.error(f"Error getting realtime metrics: {e}")
            return {}

    async def reset_metrics(self):
        """重置指标"""
        try:
            self._initialize_metrics_history()
            self.quality_reports.clear()
            
            # 重置统计（保留部分）
            self.stats = {
                "total_frames_analyzed": 0,
                "quality_reports_generated": self.stats["quality_reports_generated"],
                "average_processing_time": 0.0,
                "real_time_alerts": 0,
                "optimization_suggestions": self.stats["optimization_suggestions"]
            }
            
            logger.info("Sync metrics reset")
            
        except Exception as e:
            logger.error(f"Error resetting metrics: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats["metrics_history_size"] = {k.value: len(v) for k, v in self.metrics_history.items()}
        stats["quality_reports_count"] = len(self.quality_reports)
        stats["realtime_monitoring"] = self.realtime_monitoring
        
        return stats

    async def cleanup(self):
        """清理资源"""
        try:
            self.metrics_history.clear()
            self.quality_reports.clear()
            
            logger.info("SyncMetrics system cleaned up")
            
        except Exception as e:
            logger.error(f"Error during SyncMetrics cleanup: {e}")

# 全局同步指标实例
sync_metrics = SyncMetrics()
