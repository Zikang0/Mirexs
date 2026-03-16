# interaction/input_systems/speech_recognizer/speech_metrics.py
"""
语音指标：语音识别性能指标
负责收集和分析语音识别系统的性能指标
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics

@dataclass
class ASRMetrics:
    """ASR性能指标"""
    timestamp: datetime
    processing_time: float
    confidence: float
    word_error_rate: float
    real_time_factor: float
    memory_usage: int
    cpu_usage: float
    audio_length: float
    language: str
    model_used: str

@dataclass
class SystemMetrics:
    """系统性能指标"""
    timestamp: datetime
    active_streams: int
    total_transcriptions: int
    average_confidence: float
    average_processing_time: float
    error_rate: float
    uptime: float

class SpeechMetricsCollector:
    """语音指标收集器"""
    
    def __init__(self):
        self.asr_metrics: List[ASRMetrics] = []
        self.system_metrics: List[SystemMetrics] = []
        self.is_initialized = False
        self.collection_interval = 60  # 收集间隔（秒）
        self.metrics_window = 3600     # 指标窗口（秒）
        self.collection_task = None
        
        # 集成基础设施组件
        from infrastructure.compute_storage.inference_optimizer import inference_optimizer
        self.inference_optimizer = inference_optimizer
        from infrastructure.communication.message_bus import message_bus
        self.message_bus = message_bus
        
    async def initialize(self):
        """初始化指标收集器"""
        if self.is_initialized:
            return
            
        logging.info("初始化语音指标收集系统...")
        
        try:
            # 初始化基础设施组件
            await self.inference_optimizer.initialize()
            await self.message_bus.initialize()
            
            # 订阅相关消息
            await self._subscribe_to_messages()
            
            # 启动指标收集任务
            self.collection_task = asyncio.create_task(self._metrics_collection_loop())
            
            self.is_initialized = True
            logging.info("语音指标收集系统初始化完成")
            
        except Exception as e:
            logging.error(f"指标收集系统初始化失败: {e}")
            raise
    
    async def _subscribe_to_messages(self):
        """订阅相关消息"""
        # 订阅语音识别结果消息
        self.message_bus.subscribe("AI_RESPONSE", self._handle_ai_response)
        
        # 订阅系统状态消息
        self.message_bus.subscribe("SYSTEM_STARTUP", self._handle_system_startup)
        self.message_bus.subscribe("SYSTEM_SHUTDOWN", self._handle_system_shutdown)
    
    async def _handle_ai_response(self, message):
        """处理AI响应消息"""
        try:
            if message.payload.get("type") == "transcription":
                # 创建ASR指标记录
                asr_metric = ASRMetrics(
                    timestamp=datetime.now(),
                    processing_time=message.payload.get("processing_time", 0.0),
                    confidence=message.payload.get("confidence", 0.0),
                    word_error_rate=await self._calculate_wer(message.payload.get("text", "")),
                    real_time_factor=await self._calculate_rtf(
                        message.payload.get("processing_time", 0.0),
                        message.payload.get("audio_length", 0.0)
                    ),
                    memory_usage=await self._get_memory_usage(),
                    cpu_usage=await self._get_cpu_usage(),
                    audio_length=message.payload.get("audio_length", 0.0),
                    language=message.payload.get("language", "unknown"),
                    model_used=message.payload.get("model", "unknown")
                )
                
                self.asr_metrics.append(asr_metric)
                
                # 清理旧数据
                await self._cleanup_old_metrics()
                
        except Exception as e:
            logging.error(f"处理AI响应消息失败: {e}")
    
    async def _handle_system_startup(self, message):
        """处理系统启动消息"""
        if message.payload.get("component") == "realtime_transcriber":
            # 记录系统启动时间
            self.system_start_time = datetime.now()
    
    async def _handle_system_shutdown(self, message):
        """处理系统关闭消息"""
        pass  # 可以在这里记录系统关闭信息
    
    async def _metrics_collection_loop(self):
        """指标收集循环"""
        while True:
            try:
                await asyncio.sleep(self.collection_interval)
                
                # 收集系统指标
                system_metric = await self._collect_system_metrics()
                self.system_metrics.append(system_metric)
                
                # 发布指标报告
                await self._publish_metrics_report()
                
                # 清理旧数据
                await self._cleanup_old_metrics()
                
            except Exception as e:
                logging.error(f"指标收集循环错误: {e}")
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        current_time = datetime.now()
        
        # 计算窗口内的ASR指标
        recent_asr_metrics = await self._get_recent_asr_metrics(self.collection_interval)
        
        if recent_asr_metrics:
            confidences = [m.confidence for m in recent_asr_metrics]
            processing_times = [m.processing_time for m in recent_asr_metrics]
            
            avg_confidence = statistics.mean(confidences) if confidences else 0.0
            avg_processing_time = statistics.mean(processing_times) if processing_times else 0.0
            error_rate = len([m for m in recent_asr_metrics if m.confidence < 0.5]) / len(recent_asr_metrics)
        else:
            avg_confidence = 0.0
            avg_processing_time = 0.0
            error_rate = 0.0
        
        # 计算运行时间
        uptime = (current_time - getattr(self, 'system_start_time', current_time)).total_seconds()
        
        return SystemMetrics(
            timestamp=current_time,
            active_streams=await self._get_active_streams_count(),
            total_transcriptions=len(recent_asr_metrics),
            average_confidence=avg_confidence,
            average_processing_time=avg_processing_time,
            error_rate=error_rate,
            uptime=uptime
        )
    
    async def _get_recent_asr_metrics(self, time_window: int) -> List[ASRMetrics]:
        """获取最近时间窗口内的ASR指标"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        return [m for m in self.asr_metrics if m.timestamp >= cutoff_time]
    
    async def _get_active_streams_count(self) -> int:
        """获取活跃流数量"""
        # 在实际实现中，这里会查询实时转录器的状态
        # 这里返回模拟值
        return 1
    
    async def _calculate_wer(self, transcription: str) -> float:
        """计算词错误率（简化版本）"""
        # 在实际实现中，这里会将转录与参考文本比较
        # 这里使用基于置信度的估计
        if not transcription.strip():
            return 1.0  # 空转录的错误率为100%
        
        # 模拟WER计算
        words = transcription.split()
        if len(words) == 0:
            return 1.0
        
        # 基于文本长度的简单估计
        base_error = 0.1
        length_penalty = min(0.2, 5.0 / len(words))
        return base_error + length_penalty
    
    async def _calculate_rtf(self, processing_time: float, audio_length: float) -> float:
        """计算实时因子"""
        if audio_length > 0:
            return processing_time / audio_length
        else:
            return 0.0
    
    async def _get_memory_usage(self) -> int:
        """获取内存使用量"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except ImportError:
            return 0
    
    async def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
    
    async def _cleanup_old_metrics(self):
        """清理旧指标数据"""
        cutoff_time = datetime.now() - timedelta(seconds=self.metrics_window)
        
        # 清理ASR指标
        self.asr_metrics = [m for m in self.asr_metrics if m.timestamp >= cutoff_time]
        
        # 清理系统指标
        self.system_metrics = [m for m in self.system_metrics if m.timestamp >= cutoff_time]
    
    async def _publish_metrics_report(self):
        """发布指标报告"""
        try:
            # 生成性能报告
            performance_report = await self.get_performance_report()
            
            # 发布到消息总线
            await self.message_bus.publish(
                topic="SYSTEM_METRICS",
                payload=performance_report,
                source="speech_metrics"
            )
            
        except Exception as e:
            logging.error(f"发布指标报告失败: {e}")
    
    async def get_performance_report(self, time_window: int = 300) -> Dict[str, Any]:
        """获取性能报告"""
        recent_asr_metrics = await self._get_recent_asr_metrics(time_window)
        recent_system_metrics = await self._get_recent_system_metrics(time_window)
        
        if not recent_asr_metrics:
            return {
                "status": "no_data",
                "time_window": time_window,
                "message": "No metrics data available for the specified time window"
            }
        
        # 计算ASR指标统计
        confidences = [m.confidence for m in recent_asr_metrics]
        processing_times = [m.processing_time for m in recent_asr_metrics]
        word_error_rates = [m.word_error_rate for m in recent_asr_metrics]
        real_time_factors = [m.real_time_factor for m in recent_asr_metrics]
        
        # 语言分布
        language_distribution = {}
        for metric in recent_asr_metrics:
            language = metric.language
            language_distribution[language] = language_distribution.get(language, 0) + 1
        
        return {
            "status": "success",
            "time_window": time_window,
            "timestamp": datetime.now().isoformat(),
            "asr_metrics": {
                "total_transcriptions": len(recent_asr_metrics),
                "confidence": {
                    "mean": statistics.mean(confidences) if confidences else 0.0,
                    "median": statistics.median(confidences) if confidences else 0.0,
                    "std": statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
                    "min": min(confidences) if confidences else 0.0,
                    "max": max(confidences) if confidences else 0.0
                },
                "processing_time": {
                    "mean": statistics.mean(processing_times) if processing_times else 0.0,
                    "median": statistics.median(processing_times) if processing_times else 0.0,
                    "std": statistics.stdev(processing_times) if len(processing_times) > 1 else 0.0,
                    "min": min(processing_times) if processing_times else 0.0,
                    "max": max(processing_times) if processing_times else 0.0
                },
                "word_error_rate": {
                    "mean": statistics.mean(word_error_rates) if word_error_rates else 0.0,
                    "median": statistics.median(word_error_rates) if word_error_rates else 0.0,
                    "std": statistics.stdev(word_error_rates) if len(word_error_rates) > 1 else 0.0
                },
                "real_time_factor": {
                    "mean": statistics.mean(real_time_factors) if real_time_factors else 0.0,
                    "median": statistics.median(real_time_factors) if real_time_factors else 0.0,
                    "std": statistics.stdev(real_time_factors) if len(real_time_factors) > 1 else 0.0
                }
            },
            "language_distribution": language_distribution,
            "system_health": {
                "memory_usage_mb": await self._get_memory_usage() // (1024 * 1024),
                "cpu_usage_percent": await self._get_cpu_usage(),
                "active_streams": await self._get_active_streams_count()
            } if recent_system_metrics else {}
        }
    
    async def _get_recent_system_metrics(self, time_window: int) -> List[SystemMetrics]:
        """获取最近时间窗口内的系统指标"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)
        return [m for m in self.system_metrics if m.timestamp >= cutoff_time]
    
    async def get_detailed_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """获取详细指标数据"""
        filtered_asr_metrics = [
            m for m in self.asr_metrics 
            if start_time <= m.timestamp <= end_time
        ]
        
        filtered_system_metrics = [
            m for m in self.system_metrics
            if start_time <= m.timestamp <= end_time
        ]
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "asr_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "processing_time": m.processing_time,
                    "confidence": m.confidence,
                    "word_error_rate": m.word_error_rate,
                    "real_time_factor": m.real_time_factor,
                    "audio_length": m.audio_length,
                    "language": m.language,
                    "model_used": m.model_used
                }
                for m in filtered_asr_metrics
            ],
            "system_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "active_streams": m.active_streams,
                    "total_transcriptions": m.total_transcriptions,
                    "average_confidence": m.average_confidence,
                    "average_processing_time": m.average_processing_time,
                    "error_rate": m.error_rate,
                    "uptime": m.uptime
                }
                for m in filtered_system_metrics
            ]
        }
    
    async def export_metrics(self, file_path: str, format: str = "json"):
        """导出指标数据"""
        try:
            import json
            import csv
            
            if format.lower() == "json":
                data = await self.get_detailed_metrics(
                    datetime.now() - timedelta(hours=24),
                    datetime.now()
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
            elif format.lower() == "csv":
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # 写入ASR指标
                    writer.writerow([
                        'timestamp', 'processing_time', 'confidence', 
                        'word_error_rate', 'real_time_factor', 'audio_length',
                        'language', 'model_used'
                    ])
                    
                    for metric in self.asr_metrics[-1000:]:  # 最近1000条记录
                        writer.writerow([
                            metric.timestamp.isoformat(),
                            metric.processing_time,
                            metric.confidence,
                            metric.word_error_rate,
                            metric.real_time_factor,
                            metric.audio_length,
                            metric.language,
                            metric.model_used
                        ])
            
            logging.info(f"指标数据已导出到: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"导出指标数据失败: {e}")
            return False
    
    def get_collector_info(self) -> Dict[str, Any]:
        """获取收集器信息"""
        return {
            "initialized": self.is_initialized,
            "total_asr_metrics": len(self.asr_metrics),
            "total_system_metrics": len(self.system_metrics),
            "collection_interval": self.collection_interval,
            "metrics_window": self.metrics_window,
            "is_collecting": self.collection_task is not None and not self.collection_task.done()
        }


# 全局指标收集器实例
speech_metrics_collector = SpeechMetricsCollector()
