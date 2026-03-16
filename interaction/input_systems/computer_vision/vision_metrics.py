"""
视觉指标 - 视觉系统性能指标
监控和评估计算机视觉系统的性能指标
"""

import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import threading
from collections import deque, defaultdict
import json
import psutil
import cv2

# 导入依赖
from capabilities.system_management.performance_monitor import get_performance_monitor, PerformanceMetric
from cognitive.memory.working_memory import WorkingMemory

logger = logging.getLogger(__name__)

class VisionMetricType(Enum):
    """视觉指标类型"""
    FACE_DETECTION_ACCURACY = "face_detection_accuracy"
    FACE_RECOGNITION_ACCURACY = "face_recognition_accuracy"
    EMOTION_DETECTION_ACCURACY = "emotion_detection_accuracy"
    GESTURE_RECOGNITION_ACCURACY = "gesture_recognition_accuracy"
    POSE_ESTIMATION_ACCURACY = "pose_estimation_accuracy"
    PROCESSING_LATENCY = "processing_latency"
    FRAME_RATE = "frame_rate"
    MEMORY_USAGE = "memory_usage"
    GPU_USAGE = "gpu_usage"
    MODEL_LOAD_TIME = "model_load_time"

@dataclass
class VisionMetric:
    """视觉指标数据点"""
    timestamp: datetime
    metric_type: VisionMetricType
    value: float
    unit: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

@dataclass
class VisionPerformanceReport:
    """视觉性能报告"""
    report_id: str
    timestamp: datetime
    time_range: timedelta
    metrics_summary: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    detailed_metrics: Dict[str, List[VisionMetric]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "time_range": str(self.time_range),
            "metrics_summary": self.metrics_summary,
            "recommendations": self.recommendations,
            "detailed_metrics": {
                metric_type: [metric.to_dict() for metric in metrics]
                for metric_type, metrics in self.detailed_metrics.items()
            }
        }

class VisionMetrics:
    """视觉指标监控系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.working_memory = WorkingMemory()
        self.performance_monitor = get_performance_monitor()
        
        # 指标存储
        self.metrics_data: Dict[VisionMetricType, deque] = {}
        self.metrics_config = self._load_metrics_config()
        
        # 性能基准
        self.performance_benchmarks = self._load_performance_benchmarks()
        
        # 统计信息
        self.stats = {
            'total_metrics_collected': 0,
            'alerts_generated': 0,
            'reports_generated': 0,
            'system_uptime': datetime.now()
        }
        
        # 初始化数据结构
        self._initialize_data_structures()
        
        # 启动监控
        self.is_monitoring = False
        self.monitoring_thread = None
        
        self.logger.info("视觉指标系统初始化完成")
    
    def _load_metrics_config(self) -> Dict[str, Any]:
        """加载指标配置"""
        return {
            "collection_interval": 5,  # 数据收集间隔（秒）
            "data_retention": 3600,    # 数据保留时间（秒）
            "alert_thresholds": {
                VisionMetricType.FACE_DETECTION_ACCURACY: {"warning": 0.8, "critical": 0.6},
                VisionMetricType.FACE_RECOGNITION_ACCURACY: {"warning": 0.7, "critical": 0.5},
                VisionMetricType.EMOTION_DETECTION_ACCURACY: {"warning": 0.6, "critical": 0.4},
                VisionMetricType.GESTURE_RECOGNITION_ACCURACY: {"warning": 0.6, "critical": 0.4},
                VisionMetricType.POSE_ESTIMATION_ACCURACY: {"warning": 0.7, "critical": 0.5},
                VisionMetricType.PROCESSING_LATENCY: {"warning": 1000, "critical": 2000},  # 毫秒
                VisionMetricType.FRAME_RATE: {"warning": 15, "critical": 5},  # FPS
            },
            "evaluation_windows": {
                "short_term": timedelta(minutes=5),
                "medium_term": timedelta(hours=1),
                "long_term": timedelta(hours=24)
            }
        }
    
    def _load_performance_benchmarks(self) -> Dict[str, Any]:
        """加载性能基准"""
        return {
            "optimal": {
                VisionMetricType.FACE_DETECTION_ACCURACY: 0.95,
                VisionMetricType.FACE_RECOGNITION_ACCURACY: 0.90,
                VisionMetricType.EMOTION_DETECTION_ACCURACY: 0.85,
                VisionMetricType.GESTURE_RECOGNITION_ACCURACY: 0.80,
                VisionMetricType.POSE_ESTIMATION_ACCURACY: 0.85,
                VisionMetricType.PROCESSING_LATENCY: 100,  # 毫秒
                VisionMetricType.FRAME_RATE: 30,  # FPS
            },
            "acceptable": {
                VisionMetricType.FACE_DETECTION_ACCURACY: 0.85,
                VisionMetricType.FACE_RECOGNITION_ACCURACY: 0.75,
                VisionMetricType.EMOTION_DETECTION_ACCURACY: 0.70,
                VisionMetricType.GESTURE_RECOGNITION_ACCURACY: 0.65,
                VisionMetricType.POSE_ESTIMATION_ACCURACY: 0.75,
                VisionMetricType.PROCESSING_LATENCY: 500,  # 毫秒
                VisionMetricType.FRAME_RATE: 15,  # FPS
            }
        }
    
    def _initialize_data_structures(self):
        """初始化数据结构"""
        max_data_points = self.metrics_config["data_retention"] // self.metrics_config["collection_interval"]
        
        for metric_type in VisionMetricType:
            self.metrics_data[metric_type] = deque(maxlen=max_data_points)
    
    def start_monitoring(self) -> bool:
        """开始指标监控"""
        if self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            self.logger.info("视觉指标监控已启动")
            return True
            
        except Exception as e:
            self.logger.error(f"启动视觉指标监控失败: {e}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止指标监控"""
        if not self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            
            self.logger.info("视觉指标监控已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止视觉指标监控失败: {e}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        interval = self.metrics_config["collection_interval"]
        
        while self.is_monitoring:
            try:
                # 收集系统性能指标
                self._collect_system_metrics()
                
                # 检查性能告警
                self._check_performance_alerts()
                
                # 保存快照到工作记忆
                self._save_metrics_snapshot()
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"视觉指标监控循环错误: {e}")
                time.sleep(interval * 2)
    
    def _collect_system_metrics(self):
        """收集系统性能指标"""
        current_time = datetime.now()
        
        try:
            # 从性能监控器获取系统指标
            system_metrics = self.performance_monitor.get_current_performance()
            
            # 处理延迟指标（从工作记忆获取）
            processing_latency = self._get_processing_latency()
            if processing_latency is not None:
                self._add_metric(
                    VisionMetricType.PROCESSING_LATENCY,
                    processing_latency,
                    "ms",
                    current_time
                )
            
            # 帧率指标
            frame_rate = self._calculate_frame_rate()
            if frame_rate is not None:
                self._add_metric(
                    VisionMetricType.FRAME_RATE,
                    frame_rate,
                    "fps",
                    current_time
                )
            
            # 内存使用率
            memory_usage = psutil.virtual_memory().percent
            self._add_metric(
                VisionMetricType.MEMORY_USAGE,
                memory_usage,
                "%",
                current_time
            )
            
            # GPU使用率（如果可用）
            gpu_usage = self._get_gpu_usage()
            if gpu_usage is not None:
                self._add_metric(
                    VisionMetricType.GPU_USAGE,
                    gpu_usage,
                    "%",
                    current_time
                )
            
            self.stats['total_metrics_collected'] += 4  # 粗略计数
            
        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
    
    def _get_processing_latency(self) -> Optional[float]:
        """获取处理延迟"""
        try:
            # 从工作记忆获取最近的处理时间
            latency_data = self.working_memory.retrieve("vision_processing_latency")
            if latency_data and isinstance(latency_data, list):
                return sum(latency_data) / len(latency_data)
        except Exception as e:
            self.logger.debug(f"获取处理延迟失败: {e}")
        
        return None
    
    def _calculate_frame_rate(self) -> Optional[float]:
        """计算帧率"""
        try:
            # 从工作记忆获取帧时间戳
            frame_timestamps = self.working_memory.retrieve("frame_timestamps")
            if not frame_timestamps or len(frame_timestamps) < 2:
                return None
            
            # 计算最近帧的平均间隔
            recent_timestamps = frame_timestamps[-10:]  # 最近10帧
            time_diffs = []
            
            for i in range(1, len(recent_timestamps)):
                time_diff = (recent_timestamps[i] - recent_timestamps[i-1]).total_seconds()
                time_diffs.append(time_diff)
            
            if time_diffs:
                avg_interval = sum(time_diffs) / len(time_diffs)
                return 1.0 / avg_interval if avg_interval > 0 else 0
            
        except Exception as e:
            self.logger.debug(f"计算帧率失败: {e}")
        
        return None
    
    def _get_gpu_usage(self) -> Optional[float]:
        """获取GPU使用率"""
        try:
            # 尝试使用nvidia-smi或类似工具
            # 这里使用模拟数据
            import random
            return random.uniform(10, 80)
        except:
            return None
    
    def _add_metric(self, metric_type: VisionMetricType, value: float, unit: str, timestamp: datetime):
        """添加指标数据"""
        metric = VisionMetric(
            timestamp=timestamp,
            metric_type=metric_type,
            value=value,
            unit=unit
        )
        self.metrics_data[metric_type].append(metric)
    
    def record_accuracy_metric(self, metric_type: VisionMetricType, accuracy: float, 
                             confidence: float = 1.0, metadata: Dict[str, Any] = None):
        """记录准确率指标"""
        try:
            metric = VisionMetric(
                timestamp=datetime.now(),
                metric_type=metric_type,
                value=accuracy,
                unit="accuracy",
                confidence=confidence,
                metadata=metadata or {}
            )
            
            self.metrics_data[metric_type].append(metric)
            self.stats['total_metrics_collected'] += 1
            
            self.logger.debug(f"记录准确率指标: {metric_type.value} = {accuracy:.3f}")
            
        except Exception as e:
            self.logger.error(f"记录准确率指标失败: {e}")
    
    def record_processing_time(self, component: str, processing_time: float):
        """记录处理时间"""
        try:
            # 保存到工作记忆供延迟计算使用
            latency_key = f"{component}_processing_time"
            existing_data = self.working_memory.retrieve("vision_processing_latency") or []
            existing_data.append(processing_time * 1000)  # 转换为毫秒
            
            # 保持最近100个数据点
            if len(existing_data) > 100:
                existing_data = existing_data[-100:]
            
            self.working_memory.store(
                "vision_processing_latency",
                existing_data,
                ttl=300  # 5分钟
            )
            
        except Exception as e:
            self.logger.debug(f"记录处理时间失败: {e}")
    
    def record_frame_timestamp(self):
        """记录帧时间戳"""
        try:
            timestamps = self.working_memory.retrieve("frame_timestamps") or []
            timestamps.append(datetime.now())
            
            # 保持最近100个时间戳
            if len(timestamps) > 100:
                timestamps = timestamps[-100:]
            
            self.working_memory.store(
                "frame_timestamps",
                timestamps,
                ttl=300  # 5分钟
            )
            
        except Exception as e:
            self.logger.debug(f"记录帧时间戳失败: {e}")
    
    def _check_performance_alerts(self):
        """检查性能告警"""
        alert_thresholds = self.metrics_config["alert_thresholds"]
        
        for metric_type, thresholds in alert_thresholds.items():
            if not self.metrics_data[metric_type]:
                continue
            
            # 获取最近的数据点
            recent_data = list(self.metrics_data[metric_type])[-10:]  # 最近10个点
            if not recent_data:
                continue
            
            avg_value = sum(d.value for d in recent_data) / len(recent_data)
            
            # 检查临界阈值
            if avg_value <= thresholds["critical"]:
                self._create_performance_alert(metric_type, "critical", avg_value, thresholds["critical"])
            # 检查警告阈值
            elif avg_value <= thresholds["warning"]:
                self._create_performance_alert(metric_type, "warning", avg_value, thresholds["warning"])
    
    def _create_performance_alert(self, metric_type: VisionMetricType, level: str, 
                                current_value: float, threshold: float):
        """创建性能告警"""
        try:
            alert_id = f"vision_alert_{metric_type.value}_{int(time.time())}"
            
            messages = {
                "critical": f"视觉系统性能严重下降: {metric_type.value} = {current_value:.3f} (阈值: {threshold})",
                "warning": f"视觉系统性能下降: {metric_type.value} = {current_value:.3f} (阈值: {threshold})"
            }
            
            alert_data = {
                "alert_id": alert_id,
                "metric_type": metric_type.value,
                "level": level,
                "message": messages.get(level, "性能告警"),
                "current_value": current_value,
                "threshold": threshold,
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存到工作记忆
            self.working_memory.store(
                f"vision_alert_{alert_id}",
                alert_data,
                ttl=3600,  # 1小时
                priority=8 if level == "critical" else 6
            )
            
            self.stats['alerts_generated'] += 1
            logger.warning(f"视觉性能告警: {alert_data['message']}")
            
        except Exception as e:
            self.logger.error(f"创建性能告警失败: {e}")
    
    def _save_metrics_snapshot(self):
        """保存指标快照"""
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "metrics_summary": self.get_metrics_summary(timedelta(minutes=5)),
                "system_stats": self.stats
            }
            
            self.working_memory.store(
                "vision_metrics_snapshot",
                snapshot,
                ttl=600,  # 10分钟
                priority=5
            )
            
        except Exception as e:
            self.logger.debug(f"保存指标快照失败: {e}")
    
    def get_metrics_data(self, metric_type: VisionMetricType, 
                        time_range: timedelta = None) -> List[VisionMetric]:
        """获取指标数据"""
        if metric_type not in self.metrics_data:
            return []
        
        data = list(self.metrics_data[metric_type])
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            data = [d for d in data if d.timestamp >= cutoff_time]
        
        return data
    
    def get_metrics_summary(self, time_range: timedelta = None) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {}
        
        for metric_type in VisionMetricType:
            data_points = self.get_metrics_data(metric_type, time_range)
            if not data_points:
                continue
            
            values = [point.value for point in data_points]
            confidences = [point.confidence for point in data_points]
            
            # 加权平均（基于置信度）
            if sum(confidences) > 0:
                weighted_avg = sum(v * c for v, c in zip(values, confidences)) / sum(confidences)
            else:
                weighted_avg = sum(values) / len(values)
            
            summary[metric_type.value] = {
                'current': values[-1] if values else 0,
                'average': weighted_avg,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'data_points': len(values),
                'trend': self._calculate_trend(values),
                'performance_level': self._evaluate_performance_level(metric_type, weighted_avg)
            }
        
        return summary
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"
        
        # 使用线性回归计算趋势
        x = list(range(len(values)))
        y = values
        
        try:
            # 简单趋势计算
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0
            
            if avg_second > avg_first * 1.05:
                return "improving"
            elif avg_second < avg_first * 0.95:
                return "declining"
            else:
                return "stable"
                
        except:
            return "stable"
    
    def _evaluate_performance_level(self, metric_type: VisionMetricType, value: float) -> str:
        """评估性能级别"""
        optimal_benchmark = self.performance_benchmarks["optimal"].get(metric_type)
        acceptable_benchmark = self.performance_benchmarks["acceptable"].get(metric_type)
        
        if optimal_benchmark is None or acceptable_benchmark is None:
            return "unknown"
        
        # 对于准确率指标，值越高越好
        if "accuracy" in metric_type.value:
            if value >= optimal_benchmark:
                return "optimal"
            elif value >= acceptable_benchmark:
                return "acceptable"
            else:
                return "poor"
        # 对于延迟指标，值越低越好
        elif metric_type == VisionMetricType.PROCESSING_LATENCY:
            if value <= optimal_benchmark:
                return "optimal"
            elif value <= acceptable_benchmark:
                return "acceptable"
            else:
                return "poor"
        # 对于帧率指标，值越高越好
        elif metric_type == VisionMetricType.FRAME_RATE:
            if value >= optimal_benchmark:
                return "optimal"
            elif value >= acceptable_benchmark:
                return "acceptable"
            else:
                return "poor"
        else:
            return "unknown"
    
    def generate_performance_report(self, time_range: timedelta = None) -> VisionPerformanceReport:
        """生成性能报告"""
        try:
            report_id = f"vision_report_{int(time.time())}"
            time_range = time_range or timedelta(hours=1)
            
            metrics_summary = self.get_metrics_summary(time_range)
            detailed_metrics = {
                metric_type.value: self.get_metrics_data(metric_type, time_range)
                for metric_type in VisionMetricType
            }
            
            recommendations = self._generate_recommendations(metrics_summary)
            
            report = VisionPerformanceReport(
                report_id=report_id,
                timestamp=datetime.now(),
                time_range=time_range,
                metrics_summary=metrics_summary,
                recommendations=recommendations,
                detailed_metrics=detailed_metrics
            )
            
            self.stats['reports_generated'] += 1
            
            # 保存报告到工作记忆
            self.working_memory.store(
                f"vision_report_{report_id}",
                report.to_dict(),
                ttl=3600,  # 1小时
                priority=7
            )
            
            self.logger.info(f"视觉性能报告已生成: {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"生成性能报告失败: {e}")
            raise
    
    def _generate_recommendations(self, metrics_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        
        for metric_key, summary in metrics_summary.items():
            performance_level = summary.get('performance_level', 'unknown')
            
            if performance_level == "poor":
                recommendation = self._get_recommendation_for_metric(metric_key, summary)
                if recommendation:
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _get_recommendation_for_metric(self, metric_key: str, summary: Dict[str, Any]) -> Dict[str, Any]:
        """获取特定指标的优化建议"""
        recommendations_map = {
            "face_detection_accuracy": {
                "title": "人脸检测准确率优化",
                "description": f"当前人脸检测准确率较低: {summary['average']:.3f}",
                "suggestions": [
                    "优化光照条件",
                    "调整摄像头角度和距离",
                    "更新人脸检测模型",
                    "增加训练数据多样性"
                ]
            },
            "face_recognition_accuracy": {
                "title": "人脸识别准确率优化", 
                "description": f"当前人脸识别准确率较低: {summary['average']:.3f}",
                "suggestions": [
                    "注册更多角度的人脸样本",
                    "优化人脸对齐算法",
                    "更新人脸识别模型",
                    "调整识别阈值"
                ]
            },
            "processing_latency": {
                "title": "处理延迟优化",
                "description": f"当前处理延迟较高: {summary['average']:.1f}ms",
                "suggestions": [
                    "启用GPU加速",
                    "优化图像预处理",
                    "减少同时处理的帧数",
                    "升级硬件设备"
                ]
            },
            "frame_rate": {
                "title": "帧率优化",
                "description": f"当前帧率较低: {summary['average']:.1f}fps", 
                "suggestions": [
                    "降低图像分辨率",
                    "优化算法复杂度",
                    "启用多线程处理",
                    "检查系统资源使用"
                ]
            }
        }
        
        base_recommendation = recommendations_map.get(metric_key)
        if base_recommendation:
            return {
                "metric": metric_key,
                "priority": "high" if summary['performance_level'] == 'poor' else 'medium',
                **base_recommendation
            }
        
        return None
    
    def export_report(self, file_path: str, time_range: timedelta = None) -> bool:
        """导出性能报告"""
        try:
            report = self.generate_performance_report(time_range)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"视觉性能报告已导出: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出性能报告失败: {e}")
            return False
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        uptime = datetime.now() - self.stats['system_uptime']
        
        return {
            **self.stats,
            "system_uptime_seconds": uptime.total_seconds(),
            "is_monitoring": self.is_monitoring,
            "metrics_config": self.metrics_config
        }

# 全局视觉指标实例
vision_metrics_system = VisionMetrics()

