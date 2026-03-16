"""
输入指标模块：收集和分析输入系统性能指标
"""

import time
import threading
import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from infrastructure.communication.message_bus import MessageBus
from config.system import ConfigManager
from interaction.input_systems.text_input import (
    KeyboardHandler,
    HandwritingRecognizer,
    VoiceTyping,
    PredictiveText,
    AutoCorrection,
    InputMethodManager,
    ShortcutManager
)

logger = logging.getLogger(__name__)


@dataclass
class InputMetrics:
    """输入指标数据类"""
    timestamp: float
    source: str  # keyboard, handwriting, voice, etc.
    metric_type: str  # latency, accuracy, throughput, etc.
    value: float
    unit: str  # ms, percent, count, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "metric_type": self.metric_type,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata
        }


@dataclass
class InputSession:
    """输入会话"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    input_type: str = "mixed"
    metrics: List[InputMetrics] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "input_type": self.input_type,
            "metrics_count": len(self.metrics),
            "duration": (self.end_time or time.time()) - self.start_time
        }


class InputMetricsCollector:
    """输入指标收集器"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化输入指标收集器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        self.message_bus = MessageBus()
        
        # 指标存储
        self.metrics_history = deque(maxlen=10000)  # 最多保存10000个指标
        self.sessions = {}  # session_id -> InputSession
        self.current_session = None
        
        # 实时统计
        self.realtime_stats = {
            "keyboard": defaultdict(list),
            "handwriting": defaultdict(list),
            "voice": defaultdict(list),
            "predictive": defaultdict(list),
            "correction": defaultdict(list),
            "input_method": defaultdict(list),
            "shortcuts": defaultdict(list)
        }
        
        # 配置参数
        self.collection_interval = 60  # 收集间隔（秒）
        self.retention_period = 7 * 24 * 3600  # 保留期（7天）
        self.report_interval = 300  # 报告间隔（秒）
        
        # 性能阈值
        self.latency_thresholds = {
            "keyboard": 50,  # ms
            "handwriting": 500,  # ms
            "voice": 1000,  # ms
            "predictive": 200,  # ms
            "correction": 100  # ms
        }
        
        # 线程控制
        self.is_running = False
        self.collection_thread = None
        self.report_thread = None
        
        # 加载配置
        self.load_config()
        
        # 注册消息处理器
        self._register_message_handlers()
        
        logger.info("InputMetricsCollector initialized")
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            config = self.config_manager.get_config("input_metrics_config")
            
            # 收集配置
            collection = config.get("collection", {})
            self.collection_interval = collection.get("interval", 60)
            self.retention_period = collection.get("retention_period", 7 * 24 * 3600)
            self.max_history_size = collection.get("max_history_size", 10000)
            
            # 报告配置
            reporting = config.get("reporting", {})
            self.report_interval = reporting.get("interval", 300)
            self.enable_realtime_reporting = reporting.get("enable_realtime", True)
            self.enable_daily_reports = reporting.get("enable_daily", True)
            
            # 性能阈值
            thresholds = config.get("thresholds", {})
            self.latency_thresholds.update(thresholds.get("latency", {}))
            self.accuracy_thresholds = thresholds.get("accuracy", {})
            self.throughput_thresholds = thresholds.get("throughput", {})
            
            # 更新deque的最大长度
            self.metrics_history = deque(maxlen=self.max_history_size)
            
            logger.debug("Input metrics config loaded")
        except Exception as e:
            logger.error(f"Failed to load input metrics config: {e}")
    
    def _register_message_handlers(self) -> None:
        """注册消息处理器"""
        # 键盘事件
        self.message_bus.subscribe("keyboard_event", self._handle_keyboard_event)
        
        # 手写识别
        self.message_bus.subscribe("handwriting_recognition", self._handle_handwriting_event)
        
        # 语音打字
        self.message_bus.subscribe("voice_typing_result", self._handle_voice_typing_event)
        
        # 预测文本
        self.message_bus.subscribe("predictive_text_result", self._handle_predictive_text_event)
        
        # 自动校正
        self.message_bus.subscribe("auto_correction_result", self._handle_auto_correction_event)
        
        # 输入法
        self.message_bus.subscribe("ime_candidate_selected", self._handle_input_method_event)
        
        # 快捷键
        self.message_bus.subscribe("shortcut_triggered", self._handle_shortcut_event)
    
    def start_collection(self) -> bool:
        """
        开始收集指标
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_running:
            logger.warning("Metrics collection is already running")
            return False
        
        try:
            self.is_running = True
            
            # 启动收集线程
            self.collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True,
                name="MetricsCollector"
            )
            self.collection_thread.start()
            
            # 启动报告线程
            self.report_thread = threading.Thread(
                target=self._reporting_loop,
                daemon=True,
                name="MetricsReporter"
            )
            self.report_thread.start()
            
            # 开始新会话
            self.start_new_session()
            
            logger.info("Input metrics collection started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start metrics collection: {e}")
            self.is_running = False
            return False
    
    def stop_collection(self) -> None:
        """停止收集指标"""
        self.is_running = False
        
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
        
        if self.report_thread:
            self.report_thread.join(timeout=2.0)
        
        # 结束当前会话
        if self.current_session:
            self.end_current_session()
        
        logger.info("Input metrics collection stopped")
    
    def start_new_session(self, session_type: str = "mixed") -> str:
        """
        开始新的输入会话
        
        Args:
            session_type: 会话类型
            
        Returns:
            str: 会话ID
        """
        session_id = f"session_{int(time.time())}_{hash(str(time.time()))}"
        
        session = InputSession(
            session_id=session_id,
            start_time=time.time(),
            input_type=session_type
        )
        
        self.sessions[session_id] = session
        self.current_session = session
        
        # 发布会话开始事件
        self.message_bus.publish("input_session_started", {
            "session_id": session_id,
            "start_time": session.start_time,
            "input_type": session_type,
            "timestamp": time.time()
        })
        
        logger.info(f"Started new input session: {session_id}")
        return session_id
    
    def end_current_session(self) -> Optional[str]:
        """
        结束当前会话
        
        Returns:
            str: 结束的会话ID，如果没有当前会话则返回None
        """
        if not self.current_session:
            return None
        
        session_id = self.current_session.session_id
        self.current_session.end_time = time.time()
        
        # 发布会话结束事件
        self.message_bus.publish("input_session_ended", {
            "session_id": session_id,
            "start_time": self.current_session.start_time,
            "end_time": self.current_session.end_time,
            "duration": self.current_session.end_time - self.current_session.start_time,
            "metrics_count": len(self.current_session.metrics),
            "timestamp": time.time()
        })
        
        self.current_session = None
        logger.info(f"Ended input session: {session_id}")
        return session_id
    
    def _collection_loop(self) -> None:
        """收集循环"""
        while self.is_running:
            try:
                # 收集系统性能指标
                self._collect_system_metrics()
                
                # 清理过期数据
                self._cleanup_old_data()
                
                # 等待下一个收集周期
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                time.sleep(1)
    
    def _collect_system_metrics(self) -> None:
        """收集系统性能指标"""
        # 收集内存使用情况
        import psutil
        process = psutil.Process()
        
        memory_metric = InputMetrics(
            timestamp=time.time(),
            source="system",
            metric_type="memory_usage",
            value=process.memory_info().rss / 1024 / 1024,  # MB
            unit="MB",
            metadata={"pid": process.pid}
        )
        self._add_metric(memory_metric)
        
        # 收集CPU使用情况
        cpu_metric = InputMetrics(
            timestamp=time.time(),
            source="system",
            metric_type="cpu_usage",
            value=process.cpu_percent(),
            unit="percent",
            metadata={"pid": process.pid}
        )
        self._add_metric(cpu_metric)
    
    def _cleanup_old_data(self) -> None:
        """清理过期数据"""
        current_time = time.time()
        cutoff_time = current_time - self.retention_period
        
        # 清理过期的会话
        expired_sessions = [
            sid for sid, session in self.sessions.items()
            if session.end_time and session.end_time < cutoff_time
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        # 清理实时统计中的旧数据
        for source in self.realtime_stats:
            for metric_type in list(self.realtime_stats[source].keys()):
                # 只保留最近一小时的数据
                recent_data = [
                    (ts, val) for ts, val in self.realtime_stats[source][metric_type]
                    if ts > current_time - 3600
                ]
                self.realtime_stats[source][metric_type] = recent_data
    
    def _reporting_loop(self) -> None:
        """报告循环"""
        while self.is_running:
            try:
                # 生成报告
                report = self.generate_report()
                
                # 发布报告
                self.message_bus.publish("input_metrics_report", report)
                
                # 检查性能问题
                self._check_performance_issues()
                
                # 等待下一个报告周期
                time.sleep(self.report_interval)
                
            except Exception as e:
                logger.error(f"Error in reporting loop: {e}")
                time.sleep(1)
    
    def _check_performance_issues(self) -> None:
        """检查性能问题"""
        # 检查各输入源的延迟
        for source, thresholds in self.latency_thresholds.items():
            recent_latency = self.get_recent_metric_average(
                source=source,
                metric_type="latency",
                time_window=300  # 最近5分钟
            )
            
            if recent_latency and recent_latency > thresholds:
                # 发现性能问题
                issue = {
                    "source": source,
                    "metric_type": "latency",
                    "threshold": thresholds,
                    "actual_value": recent_latency,
                    "timestamp": time.time()
                }
                
                self.message_bus.publish("input_performance_issue", issue)
                logger.warning(f"Performance issue detected: {source} latency = {recent_latency:.1f}ms")
    
    def _handle_keyboard_event(self, message: Dict[str, Any]) -> None:
        """处理键盘事件"""
        # 记录键盘事件指标
        event_time = message.get("timestamp", time.time())
        
        # 计算处理延迟（如果可能）
        if "processed_at" in message:
            processed_at = message["processed_at"]
            latency = (processed_at - event_time) * 1000  # 转换为ms
            
            metric = InputMetrics(
                timestamp=time.time(),
                source="keyboard",
                metric_type="latency",
                value=latency,
                unit="ms",
                metadata={
                    "event_type": message.get("event_type"),
                    "key": message.get("key_name")
                }
            )
            self._add_metric(metric)
        
        # 记录键盘活动
        activity_metric = InputMetrics(
            timestamp=time.time(),
            source="keyboard",
            metric_type="activity",
            value=1,
            unit="count",
            metadata={
                "key": message.get("key_name"),
                "modifiers": message.get("modifiers", [])
            }
        )
        self._add_metric(activity_metric)
    
    def _handle_handwriting_event(self, message: Dict[str, Any]) -> None:
        """处理手写识别事件"""
        result = message.get("result", {})
        
        # 记录识别延迟
        if "recognition_time" in result:
            latency = result["recognition_time"] * 1000  # 转换为ms
            
            metric = InputMetrics(
                timestamp=time.time(),
                source="handwriting",
                metric_type="latency",
                value=latency,
                unit="ms",
                metadata={
                    "confidence": result.get("confidence", 0),
                    "text_length": len(result.get("text", ""))
                }
            )
            self._add_metric(metric)
        
        # 记录识别准确率
        if "confidence" in result:
            accuracy_metric = InputMetrics(
                timestamp=time.time(),
                source="handwriting",
                metric_type="accuracy",
                value=result["confidence"] * 100,  # 转换为百分比
                unit="percent",
                metadata={
                    "text": result.get("text", ""),
                    "language": result.get("language", "")
                }
            )
            self._add_metric(accuracy_metric)
    
    def _handle_voice_typing_event(self, message: Dict[str, Any]) -> None:
        """处理语音打字事件"""
        result = message.get("result", {})
        
        # 记录识别延迟
        if "duration" in result:
            # 计算实时因子（处理时间/音频时长）
            duration = result["duration"]
            if duration > 0:
                realtime_factor = 1.0  # 这里需要实际的处理时间数据
                
                metric = InputMetrics(
                    timestamp=time.time(),
                    source="voice",
                    metric_type="realtime_factor",
                    value=realtime_factor,
                    unit="ratio",
                    metadata={
                        "audio_duration": duration,
                        "confidence": result.get("confidence", 0)
                    }
                )
                self._add_metric(metric)
        
        # 记录识别准确率
        if "confidence" in result:
            accuracy_metric = InputMetrics(
                timestamp=time.time(),
                source="voice",
                metric_type="accuracy",
                value=result["confidence"] * 100,
                unit="percent",
                metadata={
                    "text": result.get("text", ""),
                    "language": result.get("language", "")
                }
            )
            self._add_metric(accuracy_metric)
    
    def _handle_predictive_text_event(self, message: Dict[str, Any]) -> None:
        """处理预测文本事件"""
        # 记录预测延迟
        if "processing_time" in message:
            latency = message["processing_time"] * 1000
            
            metric = InputMetrics(
                timestamp=time.time(),
                source="predictive",
                metric_type="latency",
                value=latency,
                unit="ms",
                metadata={
                    "context_length": message.get("context_length", 0),
                    "candidates_count": len(message.get("candidates", []))
                }
            )
            self._add_metric(metric)
        
        # 记录预测准确率（如果有用户选择信息）
        if "user_selected" in message and "top_candidate" in message:
            is_correct = message["user_selected"] == message["top_candidate"]
            accuracy_value = 100.0 if is_correct else 0.0
            
            accuracy_metric = InputMetrics(
                timestamp=time.time(),
                source="predictive",
                metric_type="accuracy",
                value=accuracy_value,
                unit="percent",
                metadata={
                    "user_selected": message["user_selected"],
                    "top_candidate": message["top_candidate"]
                }
            )
            self._add_metric(accuracy_metric)
    
    def _handle_auto_correction_event(self, message: Dict[str, Any]) -> None:
        """处理自动校正事件"""
        # 记录校正延迟
        if "processing_time" in message:
            latency = message["processing_time"] * 1000
            
            metric = InputMetrics(
                timestamp=time.time(),
                source="correction",
                metric_type="latency",
                value=latency,
                unit="ms",
                metadata={
                    "text_length": len(message.get("text", "")),
                    "corrections_count": len(message.get("corrections", []))
                }
            )
            self._add_metric(metric)
        
        # 记录校正接受率
        if "user_accepted" in message:
            acceptance_rate = 100.0 if message["user_accepted"] else 0.0
            
            acceptance_metric = InputMetrics(
                timestamp=time.time(),
                source="correction",
                metric_type="acceptance_rate",
                value=acceptance_rate,
                unit="percent",
                metadata={
                    "original_text": message.get("original_text", ""),
                    "corrected_text": message.get("corrected_text", "")
                }
            )
            self._add_metric(acceptance_metric)
    
    def _handle_input_method_event(self, message: Dict[str, Any]) -> None:
        """处理输入法事件"""
        # 记录输入法切换时间
        if "processing_time" in message:
            latency = message["processing_time"] * 1000
            
            metric = InputMetrics(
                timestamp=time.time(),
                source="input_method",
                metric_type="switch_latency",
                value=latency,
                unit="ms",
                metadata={
                    "ime_id": message.get("ime_id", ""),
                    "selected_text": message.get("selected_text", "")
                }
            )
            self._add_metric(metric)
        
        # 记录输入法使用统计
        usage_metric = InputMetrics(
            timestamp=time.time(),
            source="input_method",
            metric_type="usage",
            value=1,
            unit="count",
            metadata={
                "ime_id": message.get("ime_id", ""),
                "selected_index": message.get("index", -1)
            }
        )
        self._add_metric(usage_metric)
    
    def _handle_shortcut_event(self, message: Dict[str, Any]) -> None:
        """处理快捷键事件"""
        # 记录快捷键使用
        usage_metric = InputMetrics(
            timestamp=time.time(),
            source="shortcuts",
            metric_type="usage",
            value=1,
            unit="count",
            metadata={
                "shortcut_id": message.get("shortcut_id", ""),
                "shortcut_name": message.get("shortcut_name", ""),
                "context": message.get("context", "")
            }
        )
        self._add_metric(usage_metric)
    
    def _add_metric(self, metric: InputMetrics) -> None:
        """添加指标"""
        # 添加到历史
        self.metrics_history.append(metric)
        
        # 添加到当前会话
        if self.current_session:
            self.current_session.metrics.append(metric)
        
        # 添加到实时统计
        source = metric.source
        metric_type = metric.metric_type
        
        self.realtime_stats[source][metric_type].append((metric.timestamp, metric.value))
        
        # 限制实时统计大小
        if len(self.realtime_stats[source][metric_type]) > 1000:
            self.realtime_stats[source][metric_type] = self.realtime_stats[source][metric_type][-500:]
    
    def get_recent_metrics(self, source: Optional[str] = None, 
                          metric_type: Optional[str] = None,
                          time_window: float = 3600) -> List[InputMetrics]:
        """
        获取最近的指标
        
        Args:
            source: 数据源（可选）
            metric_type: 指标类型（可选）
            time_window: 时间窗口（秒）
            
        Returns:
            List[InputMetrics]: 指标列表
        """
        cutoff_time = time.time() - time_window
        recent_metrics = []
        
        for metric in reversed(self.metrics_history):  # 从最新开始
            if metric.timestamp < cutoff_time:
                break
            
            if source and metric.source != source:
                continue
            
            if metric_type and metric.metric_type != metric_type:
                continue
            
            recent_metrics.append(metric)
        
        # 按时间顺序返回
        return list(reversed(recent_metrics))
    
    def get_recent_metric_average(self, source: str, metric_type: str, 
                                 time_window: float = 3600) -> Optional[float]:
        """
        获取最近指标的平均值
        
        Args:
            source: 数据源
            metric_type: 指标类型
            time_window: 时间窗口（秒）
            
        Returns:
            float: 平均值，如果没有数据则返回None
        """
        recent_metrics = self.get_recent_metrics(source, metric_type, time_window)
        
        if not recent_metrics:
            return None
        
        values = [metric.value for metric in recent_metrics]
        return statistics.mean(values)
    
    def get_metric_statistics(self, source: str, metric_type: str,
                             time_window: float = 3600) -> Dict[str, Any]:
        """
        获取指标统计信息
        
        Args:
            source: 数据源
            metric_type: 指标类型
            time_window: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        recent_metrics = self.get_recent_metrics(source, metric_type, time_window)
        
        if not recent_metrics:
            return {
                "count": 0,
                "average": None,
                "min": None,
                "max": None,
                "stddev": None
            }
        
        values = [metric.value for metric in recent_metrics]
        
        return {
            "count": len(values),
            "average": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "unit": recent_metrics[0].unit
        }
    
    def generate_report(self, time_window: float = 3600) -> Dict[str, Any]:
        """
        生成指标报告
        
        Args:
            time_window: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 报告数据
        """
        report = {
            "timestamp": time.time(),
            "time_window": time_window,
            "sources": {},
            "summary": {},
            "performance_issues": []
        }
        
        # 各数据源的统计
        sources = ["keyboard", "handwriting", "voice", "predictive", "correction", "input_method", "shortcuts"]
        
        for source in sources:
            source_stats = {}
            
            # 获取该数据源的所有指标类型
            metric_types = set()
            for metric in self.get_recent_metrics(source=source, time_window=time_window):
                metric_types.add(metric.metric_type)
            
            # 计算每种指标类型的统计
            for metric_type in metric_types:
                stats = self.get_metric_statistics(source, metric_type, time_window)
                source_stats[metric_type] = stats
            
            if source_stats:
                report["sources"][source] = source_stats
        
        # 总体统计
        total_metrics = len(self.get_recent_metrics(time_window=time_window))
        active_sources = len([s for s, stats in report["sources"].items() if stats])
        
        report["summary"] = {
            "total_metrics": total_metrics,
            "active_sources": active_sources,
            "current_session": self.current_session.to_dict() if self.current_session else None,
            "sessions_count": len(self.sessions)
        }
        
        # 检查性能问题
        for source, threshold in self.latency_thresholds.items():
            if source in report["sources"] and "latency" in report["sources"][source]:
                avg_latency = report["sources"][source]["latency"]["average"]
                if avg_latency and avg_latency > threshold:
                    report["performance_issues"].append({
                        "source": source,
                        "issue": "high_latency",
                        "threshold": threshold,
                        "actual": avg_latency,
                        "unit": "ms"
                    })
        
        return report
    
    def export_metrics(self, file_path: str, 
                      start_time: Optional[float] = None,
                      end_time: Optional[float] = None) -> bool:
        """
        导出指标数据
        
        Args:
            file_path: 导出文件路径
            start_time: 开始时间（Unix时间戳）
            end_time: 结束时间（Unix时间戳）
            
        Returns:
            bool: 是否导出成功
        """
        try:
            # 筛选指标
            metrics_to_export = []
            
            for metric in self.metrics_history:
                if start_time and metric.timestamp < start_time:
                    continue
                if end_time and metric.timestamp > end_time:
                    continue
                
                metrics_to_export.append(metric.to_dict())
            
            # 导出到文件
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_time": time.time(),
                    "start_time": start_time,
                    "end_time": end_time,
                    "metrics_count": len(metrics_to_export),
                    "metrics": metrics_to_export
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(metrics_to_export)} metrics to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False
    
    def import_metrics(self, file_path: str) -> bool:
        """
        导入指标数据
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Import file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            metrics_data = import_data.get("metrics", [])
            imported_count = 0
            
            for metric_data in metrics_data:
                try:
                    metric = InputMetrics(
                        timestamp=metric_data["timestamp"],
                        source=metric_data["source"],
                        metric_type=metric_data["metric_type"],
                        value=metric_data["value"],
                        unit=metric_data["unit"],
                        metadata=metric_data.get("metadata", {})
                    )
                    
                    self.metrics_history.append(metric)
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to import metric: {e}")
            
            logger.info(f"Imported {imported_count} metrics from {file_path}")
            return imported_count > 0
            
        except Exception as e:
            logger.error(f"Failed to import metrics: {e}")
            return False
    
    def clear_metrics(self, before_time: Optional[float] = None) -> int:
        """
        清理指标数据
        
        Args:
            before_time: 清理此时间之前的数据（None则清理所有）
            
        Returns:
            int: 清理的指标数量
        """
        if before_time is None:
            cleared_count = len(self.metrics_history)
            self.metrics_history.clear()
            logger.info(f"Cleared all {cleared_count} metrics")
            return cleared_count
        else:
            # 保留指定时间之后的指标
            kept_metrics = []
            cleared_count = 0
            
            for metric in self.metrics_history:
                if metric.timestamp >= before_time:
                    kept_metrics.append(metric)
                else:
                    cleared_count += 1
            
            self.metrics_history.clear()
            self.metrics_history.extend(kept_metrics)
            
            logger.info(f"Cleared {cleared_count} metrics before {before_time}")
            return cleared_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取输入指标收集器统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 各数据源的指标数量
        source_counts = defaultdict(int)
        for metric in self.metrics_history:
            source_counts[metric.source] += 1
        
        # 最近一小时的活动
        recent_hour = self.get_recent_metrics(time_window=3600)
        recent_counts = defaultdict(int)
        for metric in recent_hour:
            recent_counts[metric.source] += 1
        
        return {
            "is_running": self.is_running,
            "total_metrics": len(self.metrics_history),
            "source_counts": dict(source_counts),
            "recent_hour_activity": dict(recent_counts),
            "current_session": self.current_session.session_id if self.current_session else None,
            "total_sessions": len(self.sessions),
            "collection_interval": self.collection_interval,
            "report_interval": self.report_interval,
            "retention_period": self.retention_period
        }

