"""
性能监控器：监控系统性能指标
"""
import psutil
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
from collections import deque
import statistics

logger = logging.getLogger(__name__)

class PerformanceMetric(Enum):
    """性能指标枚举"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    PROCESS_COUNT = "process_count"

class PerformanceLevel(Enum):
    """性能级别枚举"""
    OPTIMAL = "optimal"
    NORMAL = "normal"
    DEGRADED = "degraded"
    CRITICAL = "critical"

@dataclass
class PerformanceData:
    """性能数据"""
    timestamp: datetime
    metric: PerformanceMetric
    value: float
    unit: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['metric'] = self.metric.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class PerformanceAlert:
    """性能告警"""
    id: str
    metric: PerformanceMetric
    level: PerformanceLevel
    message: str
    threshold: float
    current_value: float
    timestamp: datetime
    resolved: bool = False
    resolved_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['metric'] = self.metric.value
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        data['resolved_time'] = self.resolved_time.isoformat() if self.resolved_time else None
        return data

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.is_monitoring = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.performance_data: Dict[PerformanceMetric, deque] = {}
        self.performance_alerts: Dict[str, PerformanceAlert] = {}
        self.monitoring_config = self._load_monitoring_config()
        self._setup_logging()
        self._initialize_data_structures()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_monitoring_config(self) -> Dict[str, Any]:
        """加载监控配置"""
        return {
            "collection_interval": 5,  # 数据收集间隔（秒）
            "data_retention": 3600,    # 数据保留时间（秒）
            "alert_thresholds": {
                PerformanceMetric.CPU_USAGE: {
                    "warning": 80.0,
                    "critical": 95.0
                },
                PerformanceMetric.MEMORY_USAGE: {
                    "warning": 85.0,
                    "critical": 95.0
                },
                PerformanceMetric.DISK_USAGE: {
                    "warning": 90.0,
                    "critical": 98.0
                }
            }
        }
    
    def _initialize_data_structures(self):
        """初始化数据结构"""
        max_data_points = self.monitoring_config["data_retention"] // self.monitoring_config["collection_interval"]
        
        for metric in PerformanceMetric:
            self.performance_data[metric] = deque(maxlen=max_data_points)
    
    def start_monitoring(self) -> bool:
        """开始性能监控"""
        if self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info("性能监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动性能监控失败: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止性能监控"""
        if not self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            
            logger.info("性能监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止性能监控失败: {str(e)}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        interval = self.monitoring_config["collection_interval"]
        
        while self.is_monitoring:
            try:
                # 收集性能数据
                self._collect_performance_data()
                
                # 检查性能告警
                self._check_performance_alerts()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"性能监控循环错误: {str(e)}")
                time.sleep(interval * 2)
    
    def _collect_performance_data(self):
        """收集性能数据"""
        current_time = datetime.now()
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self._add_performance_data(
                PerformanceMetric.CPU_USAGE, cpu_percent, "%", current_time
            )
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self._add_performance_data(
                PerformanceMetric.MEMORY_USAGE, memory_percent, "%", current_time
            )
            
            # 磁盘使用率
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            self._add_performance_data(
                PerformanceMetric.DISK_USAGE, disk_percent, "%", current_time
            )
            
            # 网络IO
            net_io = psutil.net_io_counters()
            network_usage = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024  # MB
            self._add_performance_data(
                PerformanceMetric.NETWORK_IO, network_usage, "MB", current_time
            )
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            disk_usage = (disk_io.read_bytes + disk_io.write_bytes) / 1024 / 1024  # MB
            self._add_performance_data(
                PerformanceMetric.DISK_IO, disk_usage, "MB", current_time
            )
            
            # 进程数量
            process_count = len(psutil.pids())
            self._add_performance_data(
                PerformanceMetric.PROCESS_COUNT, process_count, "count", current_time
            )
            
        except Exception as e:
            logger.error(f"收集性能数据失败: {str(e)}")
    
    def _add_performance_data(self, metric: PerformanceMetric, value: float, unit: str, timestamp: datetime):
        """添加性能数据"""
        data = PerformanceData(
            timestamp=timestamp,
            metric=metric,
            value=value,
            unit=unit
        )
        self.performance_data[metric].append(data)
    
    def _check_performance_alerts(self):
        """检查性能告警"""
        alert_thresholds = self.monitoring_config["alert_thresholds"]
        
        for metric, thresholds in alert_thresholds.items():
            if not self.performance_data[metric]:
                continue
            
            current_data = self.performance_data[metric][-1]  # 最新数据
            current_value = current_data.value
            
            # 检查临界阈值
            if current_value >= thresholds["critical"]:
                self._create_performance_alert(
                    metric, PerformanceLevel.CRITICAL,
                    current_value, thresholds["critical"]
                )
            # 检查警告阈值
            elif current_value >= thresholds["warning"]:
                self._create_performance_alert(
                    metric, PerformanceLevel.DEGRADED,
                    current_value, thresholds["warning"]
                )
    
    def _create_performance_alert(self, metric: PerformanceMetric, level: PerformanceLevel,
                                current_value: float, threshold: float):
        """创建性能告警"""
        alert_id = f"alert_{metric.value}_{int(time.time())}"
        
        # 检查是否已存在相同告警
        existing_alert = self._find_existing_alert(metric, level)
        if existing_alert:
            return
        
        messages = {
            PerformanceMetric.CPU_USAGE: f"CPU使用率 {current_value:.1f}% 超过阈值 {threshold}%",
            PerformanceMetric.MEMORY_USAGE: f"内存使用率 {current_value:.1f}% 超过阈值 {threshold}%",
            PerformanceMetric.DISK_USAGE: f"磁盘使用率 {current_value:.1f}% 超过阈值 {threshold}%"
        }
        
        alert = PerformanceAlert(
            id=alert_id,
            metric=metric,
            level=level,
            message=messages.get(metric, f"{metric.value} 超过阈值"),
            threshold=threshold,
            current_value=current_value,
            timestamp=datetime.now()
        )
        
        self.performance_alerts[alert_id] = alert
        logger.warning(f"性能告警: {alert.message} (级别: {level.value})")
    
    def _find_existing_alert(self, metric: PerformanceMetric, level: PerformanceLevel) -> Optional[PerformanceAlert]:
        """查找现有告警"""
        for alert in self.performance_alerts.values():
            if (alert.metric == metric and 
                alert.level == level and 
                not alert.resolved):
                return alert
        return None
    
    def get_performance_data(self, metric: PerformanceMetric, 
                           time_range: timedelta = None) -> List[PerformanceData]:
        """获取性能数据"""
        if metric not in self.performance_data:
            return []
        
        data = list(self.performance_data[metric])
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            data = [d for d in data if d.timestamp >= cutoff_time]
        
        return data
    
    def get_current_performance(self) -> Dict[str, Any]:
        """获取当前性能状态"""
        current_data = {}
        
        for metric in PerformanceMetric:
            if self.performance_data[metric]:
                current_data[metric.value] = self.performance_data[metric][-1].to_dict()
        
        return current_data
    
    def get_performance_statistics(self, time_range: timedelta = None) -> Dict[str, Any]:
        """获取性能统计信息"""
        statistics_data = {}
        
        for metric in PerformanceMetric:
            data_points = self.get_performance_data(metric, time_range)
            if not data_points:
                continue
            
            values = [point.value for point in data_points]
            
            statistics_data[metric.value] = {
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'avg': statistics.mean(values) if values else 0,
                'current': values[-1] if values else 0,
                'data_points': len(values)
            }
        
        return statistics_data
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """获取活跃告警"""
        return [alert for alert in self.performance_alerts.values() if not alert.resolved]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id in self.performance_alerts:
            alert = self.performance_alerts[alert_id]
            alert.resolved = True
            alert.resolved_time = datetime.now()
            logger.info(f"告警已解决: {alert.message}")
            return True
        return False
    
    def get_performance_recommendations(self) -> List[Dict[str, Any]]:
        """获取性能优化建议"""
        recommendations = []
        current_stats = self.get_performance_statistics(timedelta(hours=1))
        
        # CPU使用率建议
        cpu_avg = current_stats.get(PerformanceMetric.CPU_USAGE.value, {}).get('avg', 0)
        if cpu_avg > 80:
            recommendations.append({
                'type': 'cpu',
                'priority': 'high',
                'title': 'CPU使用率过高',
                'description': f'平均CPU使用率达到 {cpu_avg:.1f}%',
                'suggestion': '关闭不必要的应用程序或进程，考虑升级CPU'
            })
        
        # 内存使用率建议
        memory_avg = current_stats.get(PerformanceMetric.MEMORY_USAGE.value, {}).get('avg', 0)
        if memory_avg > 85:
            recommendations.append({
                'type': 'memory',
                'priority': 'high',
                'title': '内存使用率过高',
                'description': f'平均内存使用率达到 {memory_avg:.1f}%',
                'suggestion': '关闭内存密集型应用程序，考虑增加物理内存'
            })
        
        # 磁盘使用率建议
        disk_avg = current_stats.get(PerformanceMetric.DISK_USAGE.value, {}).get('avg', 0)
        if disk_avg > 90:
            recommendations.append({
                'type': 'disk',
                'priority': 'medium',
                'title': '磁盘空间不足',
                'description': f'磁盘使用率达到 {disk_avg:.1f}%',
                'suggestion': '清理不必要的文件，考虑增加磁盘空间'
            })
        
        return recommendations
    
    def export_performance_report(self, file_path: str, time_range: timedelta = None) -> bool:
        """导出性能报告"""
        try:
            report = {
                'generated_time': datetime.now().isoformat(),
                'time_range': str(time_range) if time_range else 'all',
                'current_performance': self.get_current_performance(),
                'statistics': self.get_performance_statistics(time_range),
                'active_alerts': [alert.to_dict() for alert in self.get_active_alerts()],
                'recommendations': self.get_performance_recommendations()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"性能报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出性能报告失败: {str(e)}")
            return False

# 单例实例
_performance_monitor_instance = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例"""
    global _performance_monitor_instance
    if _performance_monitor_instance is None:
        _performance_monitor_instance = PerformanceMonitor()
    return _performance_monitor_instance

