"""
桌面指标收集模块 - Mirexs桌面应用程序

收集和报告桌面应用的性能指标，包括：
1. 启动时间
2. 内存使用
3. CPU使用率
4. 窗口事件统计
5. 用户交互统计
6. 错误和异常统计
"""

import os
import sys
import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import platform

# 尝试导入系统监控库
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available. System metrics will be limited.")

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 时间指标
    start_time: datetime = field(default_factory=datetime.now)
    uptime: timedelta = field(default_factory=timedelta)
    
    # 内存指标
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_percent: float = 0.0
    
    # CPU指标
    cpu_percent: float = 0.0
    cpu_count: int = 0
    thread_count: int = 0
    
    # 窗口指标
    window_count: int = 0
    window_opens: int = 0
    window_closes: int = 0
    window_resizes: int = 0
    window_moves: int = 0
    
    # 交互指标
    user_clicks: int = 0
    key_presses: int = 0
    voice_inputs: int = 0
    commands_processed: int = 0
    
    # 性能指标
    avg_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    frame_rate: float = 0.0
    
    # 错误指标
    error_count: int = 0
    warning_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

@dataclass
class DesktopMetricsConfig:
    """桌面指标收集器配置"""
    collection_interval: float = 5.0  # 收集间隔（秒）
    enable_system_metrics: bool = True
    enable_window_metrics: bool = True
    enable_interaction_metrics: bool = True
    save_history: bool = True
    history_size: int = 1000  # 保留的历史记录数
    metrics_file: str = "desktop_metrics.json"
    history_file: str = "metrics_history.json"
    data_dir: str = "data/desktop_metrics/"

class DesktopMetrics:
    """
    桌面指标收集器类
    
    负责收集桌面应用程序的各种性能指标，并提供报告功能。
    """
    
    def __init__(self, config: Optional[DesktopMetricsConfig] = None):
        """
        初始化桌面指标收集器
        
        Args:
            config: 收集器配置
        """
        self.config = config or DesktopMetricsConfig()
        
        # 当前指标
        self.metrics = PerformanceMetrics()
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        # 进程信息
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        
        # 收集线程
        self.collection_thread: Optional[threading.Thread] = None
        self.is_collecting = False
        self.stop_event = threading.Event()
        
        # 回调函数
        self.on_metrics_updated: Optional[Callable[[PerformanceMetrics], None]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 加载历史数据
        if self.config.save_history:
            self._load_history()
        
        logger.info("DesktopMetrics initialized")
    
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
        if PSUTIL_AVAILABLE and self.config.enable_system_metrics:
            self._collect_system_metrics()
        
        # 更新时间指标
        self.metrics.uptime = datetime.now() - self.metrics.start_time
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # 内存使用
            memory_info = self.process.memory_info()
            self.metrics.memory_usage_mb = memory_info.rss / 1024 / 1024
            if self.metrics.memory_usage_mb > self.metrics.peak_memory_mb:
                self.metrics.peak_memory_mb = self.metrics.memory_usage_mb
            
            # 内存百分比
            self.metrics.memory_percent = self.process.memory_percent()
            
            # CPU使用
            self.metrics.cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # 线程数
            self.metrics.thread_count = self.process.num_threads()
            
            # CPU核心数
            self.metrics.cpu_count = psutil.cpu_count()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _collection_loop(self):
        """指标收集循环"""
        logger.info("Metrics collection started")
        
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
                self.stop_event.wait(1)  # 出错后短暂等待
        
        logger.info("Metrics collection stopped")
    
    def _add_to_history(self):
        """添加当前指标到历史记录"""
        if not self.config.save_history:
            return
        
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'memory_usage_mb': self.metrics.memory_usage_mb,
            'cpu_percent': self.metrics.cpu_percent,
            'uptime_seconds': self.metrics.uptime.total_seconds(),
            'window_count': self.metrics.window_count,
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
        
        logger.info("Metrics collection started")
    
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
        
        logger.info("Metrics collection stopped")
    
    def record_window_open(self):
        """记录窗口打开事件"""
        if self.config.enable_window_metrics:
            self.metrics.window_opens += 1
            self.metrics.window_count += 1
    
    def record_window_close(self):
        """记录窗口关闭事件"""
        if self.config.enable_window_metrics:
            self.metrics.window_closes += 1
            self.metrics.window_count = max(0, self.metrics.window_count - 1)
    
    def record_window_resize(self, width: int, height: int):
        """记录窗口大小改变事件"""
        if self.config.enable_window_metrics:
            self.metrics.window_resizes += 1
    
    def record_window_move(self, x: int, y: int):
        """记录窗口移动事件"""
        if self.config.enable_window_metrics:
            self.metrics.window_moves += 1
    
    def record_user_click(self):
        """记录用户点击事件"""
        if self.config.enable_interaction_metrics:
            self.metrics.user_clicks += 1
    
    def record_key_press(self):
        """记录按键事件"""
        if self.config.enable_interaction_metrics:
            self.metrics.key_presses += 1
    
    def record_voice_input(self):
        """记录语音输入事件"""
        if self.config.enable_interaction_metrics:
            self.metrics.voice_inputs += 1
    
    def record_command(self):
        """记录命令处理事件"""
        if self.config.enable_interaction_metrics:
            self.metrics.commands_processed += 1
    
    def record_response_time(self, response_time_ms: float):
        """记录响应时间"""
        if self.config.enable_interaction_metrics:
            # 更新平均响应时间
            total_responses = self.metrics.commands_processed
            if total_responses > 0:
                current_avg = self.metrics.avg_response_time_ms
                self.metrics.avg_response_time_ms = (
                    (current_avg * (total_responses - 1) + response_time_ms) / total_responses
                )
            
            # 更新最大响应时间
            if response_time_ms > self.metrics.max_response_time_ms:
                self.metrics.max_response_time_ms = response_time_ms
    
    def record_error(self, error: str):
        """记录错误"""
        self.metrics.error_count += 1
        self.metrics.last_error = error
        self.metrics.last_error_time = datetime.now()
        logger.debug(f"Error recorded: {error}")
    
    def record_warning(self, warning: str):
        """记录警告"""
        self.metrics.warning_count += 1
        logger.debug(f"Warning recorded: {warning}")
    
    def get_latest_metrics(self) -> Dict[str, Any]:
        """获取最新指标"""
        self._collect_metrics()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'start_time': self.metrics.start_time.isoformat(),
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
            'window': {
                'count': self.metrics.window_count,
                'opens': self.metrics.window_opens,
                'closes': self.metrics.window_closes,
                'resizes': self.metrics.window_resizes,
                'moves': self.metrics.window_moves
            },
            'interaction': {
                'clicks': self.metrics.user_clicks,
                'key_presses': self.metrics.key_presses,
                'voice_inputs': self.metrics.voice_inputs,
                'commands': self.metrics.commands_processed
            },
            'performance': {
                'avg_response_time_ms': round(self.metrics.avg_response_time_ms, 2),
                'max_response_time_ms': round(self.metrics.max_response_time_ms, 2),
                'frame_rate': round(self.metrics.frame_rate, 2)
            },
            'errors': {
                'count': self.metrics.error_count,
                'warnings': self.metrics.warning_count,
                'last_error': self.metrics.last_error,
                'last_error_time': self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None
            }
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        生成性能报告
        
        Returns:
            性能报告
        """
        # 收集最新数据
        latest = self.get_latest_metrics()
        
        # 计算统计数据
        if self.history:
            memory_values = [h['memory_usage_mb'] for h in self.history]
            cpu_values = [h['cpu_percent'] for h in self.history]
            
            avg_memory = sum(memory_values) / len(memory_values)
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_memory = max(memory_values)
            max_cpu = max(cpu_values)
        else:
            avg_memory = latest['memory']['usage_mb']
            avg_cpu = latest['cpu']['percent']
            max_memory = latest['memory']['peak_mb']
            max_cpu = latest['cpu']['percent']
        
        # 健康评分 (0-100)
        health_score = 100
        
        # 内存使用扣分
        memory_percent = latest['memory']['percent']
        if memory_percent > 80:
            health_score -= 30
        elif memory_percent > 60:
            health_score -= 15
        elif memory_percent > 40:
            health_score -= 5
        
        # CPU使用扣分
        cpu_percent = latest['cpu']['percent']
        if cpu_percent > 80:
            health_score -= 30
        elif cpu_percent > 60:
            health_score -= 15
        elif cpu_percent > 40:
            health_score -= 5
        
        # 错误扣分
        error_count = latest['errors']['count']
        if error_count > 100:
            health_score -= 20
        elif error_count > 50:
            health_score -= 10
        elif error_count > 10:
            health_score -= 5
        
        # 确保分数在0-100之间
        health_score = max(0, min(100, health_score))
        
        return {
            'generated_at': datetime.now().isoformat(),
            'uptime': {
                'seconds': latest['uptime_seconds'],
                'formatted': str(timedelta(seconds=int(latest['uptime_seconds'])))
            },
            'performance': {
                'avg_memory_mb': round(avg_memory, 2),
                'peak_memory_mb': round(max_memory, 2),
                'avg_cpu_percent': round(avg_cpu, 2),
                'peak_cpu_percent': round(max_cpu, 2),
                'avg_response_time_ms': latest['performance']['avg_response_time_ms'],
                'max_response_time_ms': latest['performance']['max_response_time_ms']
            },
            'activity': {
                'window_opens': latest['window']['opens'],
                'commands_processed': latest['interaction']['commands'],
                'voice_inputs': latest['interaction']['voice_inputs']
            },
            'errors': {
                'total': latest['errors']['count'],
                'warnings': latest['errors']['warnings'],
                'last_error': latest['errors']['last_error']
            },
            'health_score': health_score,
            'recommendations': self._generate_recommendations(latest)
        }
    
    def _generate_recommendations(self, latest: Dict[str, Any]) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        if latest['memory']['percent'] > 80:
            recommendations.append("内存使用过高，建议关闭不必要的窗口或重启应用")
        elif latest['memory']['percent'] > 60:
            recommendations.append("内存使用较高，考虑优化内存使用")
        
        if latest['cpu']['percent'] > 80:
            recommendations.append("CPU使用过高，可能存在性能瓶颈")
        
        if latest['errors']['count'] > 10:
            recommendations.append(f"检测到{latest['errors']['count']}个错误，建议查看日志")
        
        if latest['uptime_seconds'] > 86400:  # 超过24小时
            recommendations.append("应用运行时间较长，建议定期重启以释放资源")
        
        return recommendations
    
    def reset(self):
        """重置指标"""
        self.metrics = PerformanceMetrics()
        self.history.clear()
        logger.info("Metrics reset")
    
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
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down DesktopMetrics...")
        
        self.stop_collection()
        
        # 最终保存
        if self.config.save_history:
            self._save_history()
        
        logger.info("DesktopMetrics shutdown completed")

