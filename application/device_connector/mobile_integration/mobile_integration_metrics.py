"""
移动集成指标模块 - Mirexs移动设备集成

收集和报告移动集成的性能指标，包括：
1. 传感器数据指标
2. 通知同步指标
3. 跨设备连续性指标
4. 位置共享指标
5. 远程控制指标
6. 数据同步指标
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class IntegrationType(Enum):
    """集成类型枚举"""
    SENSOR = "sensor"
    NOTIFICATION = "notification"
    CONTINUITY = "continuity"
    LOCATION = "location"
    REMOTE = "remote"
    DATA_SYNC = "data_sync"
    ALL = "all"

@dataclass
class SensorMetrics:
    """传感器指标"""
    readings_per_second: float = 0.0
    active_sensors: int = 0
    total_readings: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0

@dataclass
class NotificationMetrics:
    """通知指标"""
    received_per_hour: float = 0.0
    forwarded_per_hour: float = 0.0
    blocked_per_hour: float = 0.0
    total_received: int = 0
    total_forwarded: int = 0
    total_blocked: int = 0
    errors: int = 0

@dataclass
class ContinuityMetrics:
    """连续性指标"""
    active_sessions: int = 0
    total_sessions: int = 0
    devices_paired: int = 0
    clipboard_syncs: int = 0
    files_transferred: int = 0
    handoffs: int = 0
    errors: int = 0

@dataclass
class LocationMetrics:
    """位置指标"""
    updates_per_hour: float = 0.0
    active_geofences: int = 0
    geofence_events: int = 0
    active_shares: int = 0
    total_shares: int = 0
    tracking_duration: float = 0.0
    errors: int = 0

@dataclass
class RemoteMetrics:
    """远程控制指标"""
    active_connections: int = 0
    total_connections: int = 0
    commands_per_minute: float = 0.0
    total_commands: int = 0
    screen_updates: int = 0
    avg_command_latency_ms: float = 0.0
    errors: int = 0

@dataclass
class DataSyncMetrics:
    """数据同步指标"""
    active_syncs: int = 0
    total_syncs: int = 0
    items_synced: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    conflicts: int = 0
    pending_operations: int = 0
    avg_sync_duration_ms: float = 0.0
    errors: int = 0

@dataclass
class MobileIntegrationStats:
    """移动集成统计"""
    sensor: SensorMetrics = field(default_factory=SensorMetrics)
    notification: NotificationMetrics = field(default_factory=NotificationMetrics)
    continuity: ContinuityMetrics = field(default_factory=ContinuityMetrics)
    location: LocationMetrics = field(default_factory=LocationMetrics)
    remote: RemoteMetrics = field(default_factory=RemoteMetrics)
    data_sync: DataSyncMetrics = field(default_factory=DataSyncMetrics)
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

@dataclass
class MobileIntegrationConfig:
    """移动集成指标配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    history_size: int = 1000
    
    # 阈值配置
    error_rate_threshold: float = 0.05  # 5%
    latency_threshold_ms: float = 1000.0
    
    # 持久化
    save_metrics: bool = True
    metrics_file: str = "mobile_integration_metrics.json"

class MobileIntegrationMetrics:
    """
    移动集成指标收集器
    
    负责收集移动集成的各项性能指标。
    """
    
    def __init__(self, config: Optional[MobileIntegrationConfig] = None):
        """
        初始化移动集成指标收集器
        
        Args:
            config: 指标配置
        """
        self.config = config or MobileIntegrationConfig()
        
        # 统计
        self.stats = MobileIntegrationStats()
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        # 采样计数器
        self._sensor_counter = 0
        self._notification_counter = 0
        self._continuity_counter = 0
        self._location_counter = 0
        self._remote_counter = 0
        self._data_sync_counter = 0
        
        # 采样线程
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # 回调函数
        self.on_metrics_updated: Optional[Callable[[MobileIntegrationStats], None]] = None
        self.on_threshold_exceeded: Optional[Callable[[str, str, float], None]] = None
        
        # 启动采样
        self._start_sampling()
        
        logger.info("MobileIntegrationMetrics initialized")
    
    def _start_sampling(self):
        """启动采样"""
        def sampling_loop():
            while not self._stop_sampling.is_set():
                try:
                    self._update_rates()
                    self._check_thresholds()
                    self._add_to_history()
                    self._stop_sampling.wait(self.config.sample_interval)
                except Exception as e:
                    logger.error(f"Sampling error: {e}")
        
        self._sampling_thread = threading.Thread(target=sampling_loop, daemon=True)
        self._sampling_thread.start()
        logger.debug("Metrics sampling started")
    
    def _update_rates(self):
        """更新速率统计"""
        # 重置计数器
        self._sensor_counter = 0
        self._notification_counter = 0
        self._continuity_counter = 0
        self._location_counter = 0
        self._remote_counter = 0
        self._data_sync_counter = 0
        
        self.stats.last_update = time.time()
        
        if self.on_metrics_updated:
            self.on_metrics_updated(self.stats)
    
    def _check_thresholds(self):
        """检查阈值"""
        # 检查错误率
        if self.stats.sensor.total_readings > 0:
            error_rate = self.stats.sensor.errors / self.stats.sensor.total_readings
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("sensor", "error_rate", error_rate)
        
        if self.stats.notification.total_received > 0:
            error_rate = self.stats.notification.errors / self.stats.notification.total_received
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("notification", "error_rate", error_rate)
        
        if self.stats.continuity.total_sessions > 0:
            error_rate = self.stats.continuity.errors / self.stats.continuity.total_sessions
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("continuity", "error_rate", error_rate)
        
        if self.stats.location.total_shares > 0:
            error_rate = self.stats.location.errors / self.stats.location.total_shares
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("location", "error_rate", error_rate)
        
        if self.stats.remote.total_commands > 0:
            error_rate = self.stats.remote.errors / self.stats.remote.total_commands
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("remote", "error_rate", error_rate)
        
        if self.stats.data_sync.total_syncs > 0:
            error_rate = self.stats.data_sync.errors / self.stats.data_sync.total_syncs
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("data_sync", "error_rate", error_rate)
        
        # 检查延迟
        if self.stats.sensor.avg_latency_ms > self.config.latency_threshold_ms:
            self._trigger_threshold("sensor", "latency", self.stats.sensor.avg_latency_ms)
        
        if self.stats.remote.avg_command_latency_ms > self.config.latency_threshold_ms:
            self._trigger_threshold("remote", "latency", self.stats.remote.avg_command_latency_ms)
        
        if self.stats.data_sync.avg_sync_duration_ms > self.config.latency_threshold_ms * 10:
            self._trigger_threshold("data_sync", "duration", self.stats.data_sync.avg_sync_duration_ms)
    
    def _trigger_threshold(self, integration: str, metric: str, value: float):
        """触发阈值告警"""
        if self.on_threshold_exceeded:
            self.on_threshold_exceeded(integration, metric, value)
    
    def _add_to_history(self):
        """添加到历史"""
        snapshot = {
            "timestamp": time.time(),
            "sensor": {
                "active_sensors": self.stats.sensor.active_sensors,
                "readings_per_second": self.stats.sensor.readings_per_second,
                "errors": self.stats.sensor.errors
            },
            "notification": {
                "received_per_hour": self.stats.notification.received_per_hour,
                "forwarded_per_hour": self.stats.notification.forwarded_per_hour,
                "errors": self.stats.notification.errors
            },
            "continuity": {
                "active_sessions": self.stats.continuity.active_sessions,
                "devices_paired": self.stats.continuity.devices_paired,
                "errors": self.stats.continuity.errors
            },
            "location": {
                "active_geofences": self.stats.location.active_geofences,
                "updates_per_hour": self.stats.location.updates_per_hour,
                "errors": self.stats.location.errors
            },
            "remote": {
                "active_connections": self.stats.remote.active_connections,
                "commands_per_minute": self.stats.remote.commands_per_minute,
                "errors": self.stats.remote.errors
            },
            "data_sync": {
                "active_syncs": self.stats.data_sync.active_syncs,
                "items_synced": self.stats.data_sync.items_synced,
                "errors": self.stats.data_sync.errors
            }
        }
        
        self.history.append(snapshot)
        
        if len(self.history) > self.config.history_size:
            self.history = self.history[-self.config.history_size:]
    
    def record_sensor_reading(self, readings: int = 1, latency_ms: float = 0.0,
                             error: bool = False):
        """
        记录传感器读数
        
        Args:
            readings: 读数数量
            latency_ms: 延迟（毫秒）
            error: 是否错误
        """
        self._sensor_counter += readings
        self.stats.sensor.total_readings += readings
        
        if error:
            self.stats.sensor.errors += 1
        
        # 更新平均延迟
        if latency_ms > 0:
            total = self.stats.sensor.total_readings
            current_avg = self.stats.sensor.avg_latency_ms
            self.stats.sensor.avg_latency_ms = (current_avg * (total - 1) + latency_ms) / total
    
    def record_notification(self, action: str, error: bool = False):
        """
        记录通知操作
        
        Args:
            action: 操作类型 (received, forwarded, blocked)
            error: 是否错误
        """
        if action == "received":
            self.stats.notification.total_received += 1
            self._notification_counter += 1
        elif action == "forwarded":
            self.stats.notification.total_forwarded += 1
        elif action == "blocked":
            self.stats.notification.total_blocked += 1
        
        if error:
            self.stats.notification.errors += 1
    
    def record_continuity_event(self, event_type: str, error: bool = False):
        """
        记录连续性事件
        
        Args:
            event_type: 事件类型
            error: 是否错误
        """
        if event_type == "session":
            self.stats.continuity.total_sessions += 1
        elif event_type == "clipboard":
            self.stats.continuity.clipboard_syncs += 1
        elif event_type == "file":
            self.stats.continuity.files_transferred += 1
        elif event_type == "handoff":
            self.stats.continuity.handoffs += 1
        
        if error:
            self.stats.continuity.errors += 1
    
    def record_location_update(self, error: bool = False):
        """
        记录位置更新
        
        Args:
            error: 是否错误
        """
        self.stats.location.total_shares += 1
        self._location_counter += 1
        
        if error:
            self.stats.location.errors += 1
    
    def record_location_event(self, event_type: str):
        """
        记录位置事件
        
        Args:
            event_type: 事件类型
        """
        if event_type == "geofence":
            self.stats.location.geofence_events += 1
        elif event_type == "share":
            self.stats.location.active_shares += 1
    
    def record_remote_command(self, latency_ms: float = 0.0, error: bool = False):
        """
        记录远程命令
        
        Args:
            latency_ms: 延迟（毫秒）
            error: 是否错误
        """
        self.stats.remote.total_commands += 1
        self._remote_counter += 1
        
        if error:
            self.stats.remote.errors += 1
        
        # 更新平均延迟
        if latency_ms > 0:
            total = self.stats.remote.total_commands
            current_avg = self.stats.remote.avg_command_latency_ms
            self.stats.remote.avg_command_latency_ms = (current_avg * (total - 1) + latency_ms) / total
    
    def record_remote_screen_update(self):
        """记录屏幕更新"""
        self.stats.remote.screen_updates += 1
    
    def record_data_sync(self, sync_type: str, duration_ms: float = 0.0,
                        items: int = 0, error: bool = False):
        """
        记录数据同步
        
        Args:
            sync_type: 同步类型
            duration_ms: 持续时间（毫秒）
            items: 同步项数量
            error: 是否错误
        """
        self.stats.data_sync.total_syncs += 1
        self._data_sync_counter += 1
        
        if items > 0:
            self.stats.data_sync.items_synced += items
        
        if sync_type == "create":
            self.stats.data_sync.items_created += items
        elif sync_type == "update":
            self.stats.data_sync.items_updated += items
        elif sync_type == "delete":
            self.stats.data_sync.items_deleted += items
        elif sync_type == "conflict":
            self.stats.data_sync.conflicts += items
        
        if error:
            self.stats.data_sync.errors += 1
        
        # 更新平均持续时间
        if duration_ms > 0:
            total = self.stats.data_sync.total_syncs
            current_avg = self.stats.data_sync.avg_sync_duration_ms
            self.stats.data_sync.avg_sync_duration_ms = (current_avg * (total - 1) + duration_ms) / total
    
    def set_active_counts(self, integration: IntegrationType, count: int):
        """
        设置活动计数
        
        Args:
            integration: 集成类型
            count: 计数
        """
        if integration == IntegrationType.SENSOR:
            self.stats.sensor.active_sensors = count
        elif integration == IntegrationType.CONTINUITY:
            self.stats.continuity.active_sessions = count
            self.stats.continuity.devices_paired = count
        elif integration == IntegrationType.LOCATION:
            self.stats.location.active_geofences = count
        elif integration == IntegrationType.REMOTE:
            self.stats.remote.active_connections = count
        elif integration == IntegrationType.DATA_SYNC:
            self.stats.data_sync.active_syncs = count
            self.stats.data_sync.pending_operations = count
    
    def get_stats(self, integration: Optional[IntegrationType] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            integration: 集成类型
        
        Returns:
            统计字典
        """
        if integration == IntegrationType.SENSOR:
            return {
                "readings_per_second": self.stats.sensor.readings_per_second,
                "active_sensors": self.stats.sensor.active_sensors,
                "total_readings": self.stats.sensor.total_readings,
                "errors": self.stats.sensor.errors,
                "avg_latency_ms": self.stats.sensor.avg_latency_ms
            }
        elif integration == IntegrationType.NOTIFICATION:
            return {
                "received_per_hour": self.stats.notification.received_per_hour,
                "forwarded_per_hour": self.stats.notification.forwarded_per_hour,
                "blocked_per_hour": self.stats.notification.blocked_per_hour,
                "total_received": self.stats.notification.total_received,
                "total_forwarded": self.stats.notification.total_forwarded,
                "total_blocked": self.stats.notification.total_blocked,
                "errors": self.stats.notification.errors
            }
        elif integration == IntegrationType.CONTINUITY:
            return {
                "active_sessions": self.stats.continuity.active_sessions,
                "total_sessions": self.stats.continuity.total_sessions,
                "devices_paired": self.stats.continuity.devices_paired,
                "clipboard_syncs": self.stats.continuity.clipboard_syncs,
                "files_transferred": self.stats.continuity.files_transferred,
                "handoffs": self.stats.continuity.handoffs,
                "errors": self.stats.continuity.errors
            }
        elif integration == IntegrationType.LOCATION:
            return {
                "updates_per_hour": self.stats.location.updates_per_hour,
                "active_geofences": self.stats.location.active_geofences,
                "geofence_events": self.stats.location.geofence_events,
                "active_shares": self.stats.location.active_shares,
                "total_shares": self.stats.location.total_shares,
                "errors": self.stats.location.errors
            }
        elif integration == IntegrationType.REMOTE:
            return {
                "active_connections": self.stats.remote.active_connections,
                "total_connections": self.stats.remote.total_connections,
                "commands_per_minute": self.stats.remote.commands_per_minute,
                "total_commands": self.stats.remote.total_commands,
                "screen_updates": self.stats.remote.screen_updates,
                "avg_command_latency_ms": self.stats.remote.avg_command_latency_ms,
                "errors": self.stats.remote.errors
            }
        elif integration == IntegrationType.DATA_SYNC:
            return {
                "active_syncs": self.stats.data_sync.active_syncs,
                "total_syncs": self.stats.data_sync.total_syncs,
                "items_synced": self.stats.data_sync.items_synced,
                "items_created": self.stats.data_sync.items_created,
                "items_updated": self.stats.data_sync.items_updated,
                "items_deleted": self.stats.data_sync.items_deleted,
                "conflicts": self.stats.data_sync.conflicts,
                "pending_operations": self.stats.data_sync.pending_operations,
                "avg_sync_duration_ms": self.stats.data_sync.avg_sync_duration_ms,
                "errors": self.stats.data_sync.errors
            }
        else:
            return {
                "sensor": self.get_stats(IntegrationType.SENSOR),
                "notification": self.get_stats(IntegrationType.NOTIFICATION),
                "continuity": self.get_stats(IntegrationType.CONTINUITY),
                "location": self.get_stats(IntegrationType.LOCATION),
                "remote": self.get_stats(IntegrationType.REMOTE),
                "data_sync": self.get_stats(IntegrationType.DATA_SYNC),
                "uptime": time.time() - self.stats.start_time
            }
    
    def get_history(self, integration: Optional[IntegrationType] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            integration: 集成类型
            limit: 返回数量
        
        Returns:
            历史记录
        """
        history = self.history[-limit:]
        
        if integration and integration != IntegrationType.ALL:
            filtered = []
            for entry in history:
                filtered_entry = {
                    "timestamp": entry["timestamp"],
                    integration.value: entry.get(integration.value, {})
                }
                filtered.append(filtered_entry)
            return filtered
        
        return history
    
    def reset_stats(self, integration: Optional[IntegrationType] = None):
        """
        重置统计
        
        Args:
            integration: 集成类型
        """
        if integration == IntegrationType.SENSOR:
            self.stats.sensor = SensorMetrics()
        elif integration == IntegrationType.NOTIFICATION:
            self.stats.notification = NotificationMetrics()
        elif integration == IntegrationType.CONTINUITY:
            self.stats.continuity = ContinuityMetrics()
        elif integration == IntegrationType.LOCATION:
            self.stats.location = LocationMetrics()
        elif integration == IntegrationType.REMOTE:
            self.stats.remote = RemoteMetrics()
        elif integration == IntegrationType.DATA_SYNC:
            self.stats.data_sync = DataSyncMetrics()
        else:
            self.stats = MobileIntegrationStats()
        
        logger.info(f"Stats reset for {integration.value if integration else 'all'}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取指标收集器状态
        
        Returns:
            状态字典
        """
        return {
            "uptime": time.time() - self.stats.start_time,
            "stats": self.get_stats(),
            "history_size": len(self.history),
            "sample_interval": self.config.sample_interval,
            "last_update": self.stats.last_update
        }
    
    def shutdown(self):
        """关闭指标收集器"""
        logger.info("Shutting down MobileIntegrationMetrics...")
        
        self._stop_sampling.set()
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2)
        
        self.history.clear()
        
        logger.info("MobileIntegrationMetrics shutdown completed")

# 单例模式实现
_mobile_integration_metrics_instance: Optional[MobileIntegrationMetrics] = None

def get_mobile_integration_metrics(config: Optional[MobileIntegrationConfig] = None) -> MobileIntegrationMetrics:
    """
    获取移动集成指标收集器单例
    
    Args:
        config: 指标配置
    
    Returns:
        移动集成指标收集器实例
    """
    global _mobile_integration_metrics_instance
    if _mobile_integration_metrics_instance is None:
        _mobile_integration_metrics_instance = MobileIntegrationMetrics(config)
    return _mobile_integration_metrics_instance

