"""
移动指标模块 - Mirexs移动应用程序

收集和报告移动应用的性能指标，包括：
1. 启动时间
2. 内存使用
3. CPU使用率
4. 网络请求统计
5. 页面渲染时间
6. 帧率
7. 错误和崩溃统计
8. 用户行为分析
"""

import logging
import time
import json
import os
import threading
import platform
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

@dataclass
class MobilePerformanceMetrics:
    """移动性能指标"""
    # 应用信息
    app_version: str = "1.0.0"
    platform: str = platform.system().lower()
    
    # 时间指标
    start_time: datetime = field(default_factory=datetime.now)
    uptime: timedelta = field(default_factory=timedelta)
    
    # 内存指标
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_percent: float = 0.0
    java_heap_mb: float = 0.0  # Android
    native_heap_mb: float = 0.0  # Android
    
    # CPU指标
    cpu_percent: float = 0.0
    cpu_count: int = 0
    thread_count: int = 0
    
    # 网络指标
    network_requests: int = 0
    network_errors: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    avg_request_time_ms: float = 0.0
    max_request_time_ms: float = 0.0
    
    # 渲染指标
    frame_rate: float = 0.0
    dropped_frames: int = 0
    jank_count: int = 0  # 卡顿次数
    page_load_times: Dict[str, float] = field(default_factory=dict)
    
    # 电池指标
    battery_level: int = 0
    battery_temperature: float = 0.0
    
    # 存储指标
    storage_used_mb: float = 0.0
    cache_size_mb: float = 0.0
    
    # 错误指标
    error_count: int = 0
    crash_count: int = 0
    anr_count: int = 0  # Application Not Responding (Android)
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    # 用户行为
    screen_views: Dict[str, int] = field(default_factory=dict)
    user_actions: Dict[str, int] = field(default_factory=dict)
    session_count: int = 0
    current_session_duration: float = 0.0

@dataclass
class MobilePerformanceReport:
    """移动性能报告"""
    summary: Dict[str, Any]
    metrics: MobilePerformanceMetrics
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class MobileMetricsConfig:
    """移动指标收集器配置"""
    collection_interval: float = 10.0  # 收集间隔（秒）
    enable_cpu_metrics: bool = True
    enable_memory_metrics: bool = True
    enable_network_metrics: bool = True
    enable_render_metrics: bool = True
    enable_battery_metrics: bool = True
    enable_user_metrics: bool = True
    
    save_history: bool = True
    history_size: int = 1000
    metrics_file: str = "mobile_metrics.json"
    history_file: str = "metrics_history.json"
    data_dir: str = "data/mobile_metrics/"
    
    # 告警阈值
    memory_warning_threshold: float = 80.0  # 百分比
    cpu_warning_threshold: float = 80.0  # 百分比
    fps_warning_threshold: float = 30.0  # 帧率
    request_time_warning_ms: float = 2000.0  # 毫秒

class MobileMetrics:
    """
    移动指标收集器
    
    负责收集移动应用程序的各种性能指标，并提供报告和分析功能。
    """
    
    def __init__(self, config: Optional[MobileMetricsConfig] = None):
        """
        初始化移动指标收集器
        
        Args:
            config: 收集器配置
        """
        self.config = config or MobileMetricsConfig()
        
        # 当前指标
        self.metrics = MobilePerformanceMetrics()
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        # 会话跟踪
        self.session_start_time = time.time()
        self.sessions: List[Dict[str, Any]] = []
        
        # 收集线程
        self.collection_thread: Optional[threading.Thread] = None
        self.is_collecting = False
        self.stop_event = threading.Event()
        
        # 帧率跟踪
        self.frame_times = deque(maxlen=60)
        self.last_frame_time = time.time()
        
        # 网络请求跟踪
        self.request_times = deque(maxlen=100)
        
        # 回调函数
        self.on_metrics_updated: Optional[Callable[[MobilePerformanceMetrics], None]] = None
        self.on_warning: Optional[Callable[[str, Any], None]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载历史数据
        if self.config.save_history:
            self._load_history()
        
        logger.info("MobileMetrics initialized")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _load_history(self):
        """加载历史指标数据"""
        history_path = os.path.join(self.config.data_dir, self.config.history_file)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
                logger.info(f"Loaded {len(self.history)} historical records")
            except Exception as e:
                logger.error(f"Error loading metrics history: {e}")
    
    def _save_history(self):
        """保存历史指标数据"""
        if not self.config.save_history:
            return
        
        history_path = os.path.join(self.config.data_dir, self.config.history_file)
        try:
            # 限制历史记录大小
            if len(self.history) > self.config.history_size:
                self.history = self.history[-self.config.history_size:]
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'history': self.history,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2, default=str)
            
            logger.debug(f"Metrics history saved to {history_path}")
        except Exception as e:
            logger.error(f"Error saving metrics history: {e}")
    
    def _collect_metrics(self):
        """收集当前指标"""
        # 更新时间
        self.metrics.uptime = datetime.now() - self.metrics.start_time
        self.metrics.current_session_duration = time.time() - self.session_start_time
        
        # 这里应该从原生平台获取真实指标
        # 简化实现
        self._collect_system_metrics()
        self._collect_network_metrics()
        self._collect_render_metrics()
        
        # 检查告警阈值
        self._check_warnings()
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        # 这里应该从原生代码获取
        # 简化实现
        import psutil
        import random
        
        if self.config.enable_memory_metrics:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, self.metrics.memory_usage_mb)
            self.metrics.memory_percent = process.memory_percent()
        
        if self.config.enable_cpu_metrics:
            self.metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metrics.cpu_count = psutil.cpu_count()
            self.metrics.thread_count = threading.active_count()
    
    def _collect_network_metrics(self):
        """收集网络指标"""
        # 这里应该从网络层获取
        # 简化实现
        if self.request_times:
            self.metrics.avg_request_time_ms = sum(self.request_times) / len(self.request_times)
            self.metrics.max_request_time_ms = max(self.request_times)
    
    def _collect_render_metrics(self):
        """收集渲染指标"""
        # 计算帧率
        if len(self.frame_times) > 1:
            time_span = self.frame_times[-1] - self.frame_times[0]
            if time_span > 0:
                self.metrics.frame_rate = len(self.frame_times) / time_span
    
    def _check_warnings(self):
        """检查告警阈值"""
        if self.config.memory_warning_threshold and self.metrics.memory_percent > self.config.memory_warning_threshold:
            if self.on_warning:
                self.on_warning("memory_high", self.metrics.memory_percent)
        
        if self.config.cpu_warning_threshold and self.metrics.cpu_percent > self.config.cpu_warning_threshold:
            if self.on_warning:
                self.on_warning("cpu_high", self.metrics.cpu_percent)
        
        if self.config.fps_warning_threshold and self.metrics.frame_rate < self.config.fps_warning_threshold:
            if self.on_warning:
                self.on_warning("fps_low", self.metrics.frame_rate)
        
        if self.config.request_time_warning_ms and self.metrics.avg_request_time_ms > self.config.request_time_warning_ms:
            if self.on_warning:
                self.on_warning("request_slow", self.metrics.avg_request_time_ms)
    
    def _collection_loop(self):
        """指标收集循环"""
        logger.info("Mobile metrics collection started")
        
        while not self.stop_event.is_set():
            try:
                self._collect_metrics()
                
                # 保存到历史
                self._add_to_history()
                
                # 触发回调
                if self.on_metrics_updated:
                    try:
                        self.on_metrics_updated(self.metrics)
                    except Exception as e:
                        logger.error(f"Error in metrics callback: {e}")
                
                # 等待下一个收集间隔
                self.stop_event.wait(self.config.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                self.stop_event.wait(1)
        
        logger.info("Mobile metrics collection stopped")
    
    def _add_to_history(self):
        """添加当前指标到历史记录"""
        if not self.config.save_history:
            return
        
        snapshot = {
            'timestamp': time.time(),
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'cpu_percent': self.metrics.cpu_percent,
            'frame_rate': self.metrics.frame_rate,
            'network_requests': self.metrics.network_requests,
            'battery_level': self.metrics.battery_level,
            'error_count': self.metrics.error_count
        }
        
        self.history.append(snapshot)
        
        # 限制大小
        if len(self.history) > self.config.history_size:
            self.history = self.history[-self.config.history_size:]
    
    def start_collection(self):
        """开始指标收集"""
        if self.is_collecting:
            logger.warning("Metrics collection already running")
            return
        
        self.is_collecting = True
        self.stop_event.clear()
        
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
        
        logger.info("Mobile metrics collection started")
    
    def stop_collection(self):
        """停止指标收集"""
        if not self.is_collecting:
            return
        
        self.stop_event.set()
        
        if self.collection_thread:
            self.collection_thread.join(timeout=2)
        
        self.is_collecting = False
        
        # 保存历史
        if self.config.save_history:
            self._save_history()
        
        logger.info("Mobile metrics collection stopped")
    
    def record_frame(self):
        """记录一帧"""
        current_time = time.time()
        self.frame_times.append(current_time)
        
        # 检测丢帧
        if self.last_frame_time:
            frame_time = current_time - self.last_frame_time
            if frame_time > 0.033:  # 超过33ms（30fps）
                self.metrics.dropped_frames += 1
                if frame_time > 0.1:  # 超过100ms
                    self.metrics.jank_count += 1
        
        self.last_frame_time = current_time
    
    def record_network_request(self, duration_ms: float, bytes_sent: int = 0, 
                              bytes_received: int = 0, success: bool = True):
        """
        记录网络请求
        
        Args:
            duration_ms: 请求耗时（毫秒）
            bytes_sent: 发送字节数
            bytes_received: 接收字节数
            success: 是否成功
        """
        self.metrics.network_requests += 1
        self.metrics.total_bytes_sent += bytes_sent
        self.metrics.total_bytes_received += bytes_received
        
        if not success:
            self.metrics.network_errors += 1
        
        self.request_times.append(duration_ms)
    
    def record_screen_view(self, screen_name: str):
        """
        记录屏幕浏览
        
        Args:
            screen_name: 屏幕名称
        """
        self.metrics.screen_views[screen_name] = self.metrics.screen_views.get(screen_name, 0) + 1
    
    def record_user_action(self, action_name: str):
        """
        记录用户行为
        
        Args:
            action_name: 行为名称
        """
        self.metrics.user_actions[action_name] = self.metrics.user_actions.get(action_name, 0) + 1
    
    def record_page_load(self, page_name: str, load_time_ms: float):
        """
        记录页面加载时间
        
        Args:
            page_name: 页面名称
            load_time_ms: 加载时间（毫秒）
        """
        self.metrics.page_load_times[page_name] = load_time_ms
    
    def record_error(self, error: str, is_crash: bool = False):
        """
        记录错误
        
        Args:
            error: 错误信息
            is_crash: 是否崩溃
        """
        self.metrics.error_count += 1
        
        if is_crash:
            self.metrics.crash_count += 1
        
        self.metrics.last_error = error
        self.metrics.last_error_time = datetime.now()
        
        logger.error(f"Error recorded: {error}")
    
    def record_anr(self):
        """记录ANR（Android）"""
        self.metrics.anr_count += 1
        logger.warning("ANR recorded")
    
    def update_battery_stats(self, level: int, temperature: float):
        """
        更新电池统计
        
        Args:
            level: 电量百分比
            temperature: 温度
        """
        self.metrics.battery_level = level
        self.metrics.battery_temperature = temperature
    
    def start_new_session(self):
        """开始新会话"""
        if self.session_start_time:
            duration = time.time() - self.session_start_time
            self.sessions.append({
                "start_time": self.session_start_time,
                "duration": duration
            })
        
        self.session_start_time = time.time()
        self.metrics.session_count += 1
        
        logger.info(f"New session started (#{self.metrics.session_count})")
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        获取最新指标
        
        Returns:
            指标字典
        """
        self._collect_metrics()
        
        return {
            'timestamp': time.time(),
            'app_version': self.metrics.app_version,
            'platform': self.metrics.platform,
            'uptime_seconds': self.metrics.uptime.total_seconds(),
            'memory': {
                'usage_mb': round(self.metrics.memory_usage_mb, 2),
                'peak_mb': round(self.metrics.peak_memory_mb, 2),
                'percent': round(self.metrics.memory_percent, 2)
            },
            'cpu': {
                'percent': round(self.metrics.cpu_percent, 2),
                'count': self.metrics.cpu_count,
                'threads': self.metrics.thread_count
            },
            'network': {
                'requests': self.metrics.network_requests,
                'errors': self.metrics.network_errors,
                'bytes_sent_mb': round(self.metrics.total_bytes_sent / 1024 / 1024, 2),
                'bytes_received_mb': round(self.metrics.total_bytes_received / 1024 / 1024, 2),
                'avg_request_time_ms': round(self.metrics.avg_request_time_ms, 2)
            },
            'render': {
                'frame_rate': round(self.metrics.frame_rate, 2),
                'dropped_frames': self.metrics.dropped_frames,
                'jank_count': self.metrics.jank_count
            },
            'battery': {
                'level': self.metrics.battery_level,
                'temperature': self.metrics.battery_temperature
            },
            'errors': {
                'total': self.metrics.error_count,
                'crashes': self.metrics.crash_count,
                'anrs': self.metrics.anr_count,
                'last_error': self.metrics.last_error
            },
            'user': {
                'sessions': self.metrics.session_count,
                'session_duration': round(self.metrics.current_session_duration, 2),
                'screen_views': self.metrics.screen_views,
                'user_actions': self.metrics.user_actions
            }
        }
    
    def generate_report(self) -> MobilePerformanceReport:
        """
        生成性能报告
        
        Returns:
            性能报告
        """
        latest = self.get_latest_metrics()
        
        # 计算统计数据
        if self.history:
            memory_values = [h['memory_usage_mb'] for h in self.history]
            cpu_values = [h['cpu_percent'] for h in self.history]
            fps_values = [h['frame_rate'] for h in self.history if h['frame_rate'] > 0]
            
            avg_memory = sum(memory_values) / len(memory_values)
            avg_cpu = sum(cpu_values) / len(cpu_values)
            avg_fps = sum(fps_values) / len(fps_values) if fps_values else 0
            
            max_memory = max(memory_values)
            max_cpu = max(cpu_values)
            min_fps = min(fps_values) if fps_values else 0
        else:
            avg_memory = latest['memory']['usage_mb']
            avg_cpu = latest['cpu']['percent']
            avg_fps = latest['render']['frame_rate']
            max_memory = latest['memory']['peak_mb']
            max_cpu = latest['cpu']['percent']
            min_fps = latest['render']['frame_rate']
        
        # 健康评分 (0-100)
        health_score = 100
        
        # 内存使用扣分
        if latest['memory']['percent'] > 80:
            health_score -= 30
        elif latest['memory']['percent'] > 60:
            health_score -= 15
        elif latest['memory']['percent'] > 40:
            health_score -= 5
        
        # CPU使用扣分
        if latest['cpu']['percent'] > 80:
            health_score -= 30
        elif latest['cpu']['percent'] > 60:
            health_score -= 15
        elif latest['cpu']['percent'] > 40:
            health_score -= 5
        
        # 帧率扣分
        if latest['render']['frame_rate'] < 30:
            health_score -= 20
        elif latest['render']['frame_rate'] < 45:
            health_score -= 10
        elif latest['render']['frame_rate'] < 55:
            health_score -= 5
        
        # 错误扣分
        error_count = latest['errors']['total']
        if error_count > 100:
            health_score -= 20
        elif error_count > 50:
            health_score -= 10
        elif error_count > 10:
            health_score -= 5
        
        health_score = max(0, min(100, health_score))
        
        summary = {
            'health_score': health_score,
            'uptime': str(timedelta(seconds=int(latest['uptime_seconds']))),
            'avg_memory_mb': round(avg_memory, 2),
            'avg_cpu_percent': round(avg_cpu, 2),
            'avg_fps': round(avg_fps, 2),
            'total_requests': latest['network']['requests'],
            'error_count': latest['errors']['total']
        }
        
        recommendations = self._generate_recommendations(latest)
        
        return MobilePerformanceReport(
            summary=summary,
            metrics=self.metrics,
            recommendations=recommendations,
            generated_at=datetime.now()
        )
    
    def _generate_recommendations(self, latest: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if latest['memory']['percent'] > 80:
            recommendations.append("内存使用过高，建议清理后台应用或重启")
        elif latest['memory']['percent'] > 60:
            recommendations.append("内存使用较高，考虑优化内存使用")
        
        if latest['cpu']['percent'] > 80:
            recommendations.append("CPU使用过高，可能存在性能瓶颈")
        
        if latest['render']['frame_rate'] < 30:
            recommendations.append("界面卡顿明显，建议降低动画效果或优化渲染")
        elif latest['render']['frame_rate'] < 45:
            recommendations.append("界面不够流畅，考虑优化")
        
        if latest['network']['errors'] > latest['network']['requests'] * 0.1:
            recommendations.append("网络错误率较高，检查网络连接")
        
        if latest['battery']['level'] < 20:
            recommendations.append("电量较低，建议开启省电模式")
        
        if latest['errors']['total'] > 10:
            recommendations.append(f"检测到{latest['errors']['total']}个错误，建议查看日志")
        
        return recommendations
    
    def export_metrics(self, file_path: str) -> bool:
        """
        导出指标到文件
        
        Args:
            file_path: 导出路径
        
        Returns:
            是否成功
        """
        data = {
            'current': self.get_latest_metrics(),
            'history': self.history,
            'sessions': self.sessions,
            'exported_at': datetime.now().isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return False
    
    def reset(self):
        """重置指标"""
        self.metrics = MobilePerformanceMetrics()
        self.history.clear()
        self.sessions.clear()
        self.frame_times.clear()
        self.request_times.clear()
        self.session_start_time = time.time()
        logger.info("Metrics reset")
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down MobileMetrics...")
        
        self.stop_collection()
        
        # 最终保存
        if self.config.save_history:
            self._save_history()
        
        logger.info("MobileMetrics shutdown completed")

# 单例模式实现
_mobile_metrics_instance: Optional[MobileMetrics] = None

def get_mobile_metrics(config: Optional[MobileMetricsConfig] = None) -> MobileMetrics:
    """
    获取移动指标收集器单例
    
    Args:
        config: 指标收集器配置
    
    Returns:
        移动指标收集器实例
    """
    global _mobile_metrics_instance
    if _mobile_metrics_instance is None:
        _mobile_metrics_instance = MobileMetrics(config)
    return _mobile_metrics_instance

