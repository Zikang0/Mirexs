"""
智能家居指标模块 - Mirexs智能家居集成

收集和报告智能家居集成的性能指标，包括：
1. 设备指标
2. 场景自动化指标
3. 环境感知指标
4. 能源管理指标
5. 安全系统指标
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class SmartHomeComponent(Enum):
    """智能家居组件枚举"""
    DEVICE_MANAGER = "device_manager"
    SCENE_AUTOMATION = "scene_automation"
    ENVIRONMENT = "environment"
    ENERGY = "energy"
    SECURITY = "security"
    ALL = "all"

@dataclass
class DeviceMetrics:
    """设备指标"""
    total_devices: int = 0
    online_devices: int = 0
    offline_devices: int = 0
    devices_by_type: Dict[str, int] = field(default_factory=dict)
    commands_sent: int = 0
    commands_succeeded: int = 0
    commands_failed: int = 0
    avg_response_time_ms: float = 0.0
    errors: int = 0

@dataclass
class SceneMetrics:
    """场景指标"""
    total_scenes: int = 0
    total_rules: int = 0
    active_rules: int = 0
    scenes_activated: int = 0
    rules_triggered: int = 0
    actions_executed: int = 0
    actions_succeeded: int = 0
    actions_failed: int = 0
    avg_execution_time_ms: float = 0.0
    errors: int = 0

@dataclass
class EnvironmentMetrics:
    """环境指标"""
    total_sensors: int = 0
    active_sensors: int = 0
    readings_collected: int = 0
    alerts_triggered: int = 0
    temperature_avg: float = 0.0
    humidity_avg: float = 0.0
    air_quality_avg: float = 0.0
    errors: int = 0

@dataclass
class EnergyMetrics:
    """能源指标"""
    current_power: float = 0.0
    energy_today: float = 0.0
    energy_month: float = 0.0
    energy_year: float = 0.0
    cost_today: float = 0.0
    cost_month: float = 0.0
    peak_power: float = 0.0
    suggestions_generated: int = 0
    errors: int = 0

@dataclass
class SecurityMetrics:
    """安全指标"""
    alarm_status: str = "disarmed"
    total_sensors: int = 0
    triggered_sensors: int = 0
    offline_sensors: int = 0
    bypassed_sensors: int = 0
    events_today: int = 0
    alarms_triggered: int = 0
    false_alarms: int = 0
    cameras_online: int = 0
    cameras_recording: int = 0
    errors: int = 0

@dataclass
class SmartHomeStats:
    """智能家居统计"""
    device: DeviceMetrics = field(default_factory=DeviceMetrics)
    scene: SceneMetrics = field(default_factory=SceneMetrics)
    environment: EnvironmentMetrics = field(default_factory=EnvironmentMetrics)
    energy: EnergyMetrics = field(default_factory=EnergyMetrics)
    security: SecurityMetrics = field(default_factory=SecurityMetrics)
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

@dataclass
class SmartHomeConfig:
    """智能家居指标配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    history_size: int = 1000
    
    # 阈值配置
    error_rate_threshold: float = 0.05  # 5%
    offline_rate_threshold: float = 0.1  # 10%
    
    # 持久化
    save_metrics: bool = True
    metrics_file: str = "smart_home_metrics.json"

class SmartHomeMetrics:
    """
    智能家居指标收集器
    
    负责收集智能家居集成的各项性能指标。
    """
    
    def __init__(self, config: Optional[SmartHomeConfig] = None):
        """
        初始化智能家居指标收集器
        
        Args:
            config: 指标配置
        """
        self.config = config or SmartHomeConfig()
        
        # 统计
        self.stats = SmartHomeStats()
        
        # 历史记录
        self.history: List[Dict[str, Any]] = []
        
        # 采样计数器
        self._device_counter = 0
        self._scene_counter = 0
        self._environment_counter = 0
        self._energy_counter = 0
        self._security_counter = 0
        
        # 采样线程
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # 回调函数
        self.on_metrics_updated: Optional[Callable[[SmartHomeStats], None]] = None
        self.on_threshold_exceeded: Optional[Callable[[str, str, float], None]] = None
        
        # 启动采样
        self._start_sampling()
        
        logger.info("SmartHomeMetrics initialized")
    
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
        self._device_counter = 0
        self._scene_counter = 0
        self._environment_counter = 0
        self._energy_counter = 0
        self._security_counter = 0
        
        self.stats.last_update = time.time()
        
        if self.on_metrics_updated:
            self.on_metrics_updated(self.stats)
    
    def _check_thresholds(self):
        """检查阈值"""
        # 检查设备错误率
        if self.stats.device.commands_sent > 0:
            error_rate = self.stats.device.commands_failed / self.stats.device.commands_sent
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("device", "error_rate", error_rate)
        
        # 检查设备离线率
        if self.stats.device.total_devices > 0:
            offline_rate = self.stats.device.offline_devices / self.stats.device.total_devices
            if offline_rate > self.config.offline_rate_threshold:
                self._trigger_threshold("device", "offline_rate", offline_rate)
        
        # 检查场景错误率
        if self.stats.scene.actions_executed > 0:
            error_rate = self.stats.scene.actions_failed / self.stats.scene.actions_executed
            if error_rate > self.config.error_rate_threshold:
                self._trigger_threshold("scene", "error_rate", error_rate)
        
        # 检查环境错误
        if self.stats.environment.errors > 100:
            self._trigger_threshold("environment", "errors", self.stats.environment.errors)
        
        # 检查能源错误
        if self.stats.energy.errors > 100:
            self._trigger_threshold("energy", "errors", self.stats.energy.errors)
        
        # 检查安全错误
        if self.stats.security.errors > 100:
            self._trigger_threshold("security", "errors", self.stats.security.errors)
    
    def _trigger_threshold(self, component: str, metric: str, value: float):
        """触发阈值告警"""
        if self.on_threshold_exceeded:
            self.on_threshold_exceeded(component, metric, value)
    
    def _add_to_history(self):
        """添加到历史"""
        snapshot = {
            "timestamp": time.time(),
            "device": {
                "total_devices": self.stats.device.total_devices,
                "online_devices": self.stats.device.online_devices,
                "commands_sent": self.stats.device.commands_sent,
                "commands_failed": self.stats.device.commands_failed,
                "errors": self.stats.device.errors
            },
            "scene": {
                "total_scenes": self.stats.scene.total_scenes,
                "active_rules": self.stats.scene.active_rules,
                "scenes_activated": self.stats.scene.scenes_activated,
                "actions_failed": self.stats.scene.actions_failed,
                "errors": self.stats.scene.errors
            },
            "environment": {
                "total_sensors": self.stats.environment.total_sensors,
                "readings_collected": self.stats.environment.readings_collected,
                "alerts_triggered": self.stats.environment.alerts_triggered,
                "errors": self.stats.environment.errors
            },
            "energy": {
                "current_power": self.stats.energy.current_power,
                "energy_today": self.stats.energy.energy_today,
                "peak_power": self.stats.energy.peak_power,
                "errors": self.stats.energy.errors
            },
            "security": {
                "alarm_status": self.stats.security.alarm_status,
                "total_sensors": self.stats.security.total_sensors,
                "triggered_sensors": self.stats.security.triggered_sensors,
                "alarms_triggered": self.stats.security.alarms_triggered,
                "errors": self.stats.security.errors
            }
        }
        
        self.history.append(snapshot)
        
        if len(self.history) > self.config.history_size:
            self.history = self.history[-self.config.history_size:]
    
    def update_device_metrics(self, metrics: Dict[str, Any]):
        """
        更新设备指标
        
        Args:
            metrics: 设备指标
        """
        if "total_devices" in metrics:
            self.stats.device.total_devices = metrics["total_devices"]
        if "online_devices" in metrics:
            self.stats.device.online_devices = metrics["online_devices"]
        if "offline_devices" in metrics:
            self.stats.device.offline_devices = metrics["offline_devices"]
        if "devices_by_type" in metrics:
            self.stats.device.devices_by_type = metrics["devices_by_type"]
        if "commands_sent" in metrics:
            self.stats.device.commands_sent += metrics["commands_sent"]
        if "commands_succeeded" in metrics:
            self.stats.device.commands_succeeded += metrics["commands_succeeded"]
        if "commands_failed" in metrics:
            self.stats.device.commands_failed += metrics["commands_failed"]
        if "errors" in metrics:
            self.stats.device.errors += metrics["errors"]
    
    def update_scene_metrics(self, metrics: Dict[str, Any]):
        """
        更新场景指标
        
        Args:
            metrics: 场景指标
        """
        if "total_scenes" in metrics:
            self.stats.scene.total_scenes = metrics["total_scenes"]
        if "total_rules" in metrics:
            self.stats.scene.total_rules = metrics["total_rules"]
        if "active_rules" in metrics:
            self.stats.scene.active_rules = metrics["active_rules"]
        if "scenes_activated" in metrics:
            self.stats.scene.scenes_activated += metrics["scenes_activated"]
        if "rules_triggered" in metrics:
            self.stats.scene.rules_triggered += metrics["rules_triggered"]
        if "actions_executed" in metrics:
            self.stats.scene.actions_executed += metrics["actions_executed"]
        if "actions_succeeded" in metrics:
            self.stats.scene.actions_succeeded += metrics["actions_succeeded"]
        if "actions_failed" in metrics:
            self.stats.scene.actions_failed += metrics["actions_failed"]
        if "errors" in metrics:
            self.stats.scene.errors += metrics["errors"]
    
    def update_environment_metrics(self, metrics: Dict[str, Any]):
        """
        更新环境指标
        
        Args:
            metrics: 环境指标
        """
        if "total_sensors" in metrics:
            self.stats.environment.total_sensors = metrics["total_sensors"]
        if "active_sensors" in metrics:
            self.stats.environment.active_sensors = metrics["active_sensors"]
        if "readings_collected" in metrics:
            self.stats.environment.readings_collected += metrics["readings_collected"]
        if "alerts_triggered" in metrics:
            self.stats.environment.alerts_triggered += metrics["alerts_triggered"]
        if "temperature_avg" in metrics:
            self.stats.environment.temperature_avg = metrics["temperature_avg"]
        if "humidity_avg" in metrics:
            self.stats.environment.humidity_avg = metrics["humidity_avg"]
        if "air_quality_avg" in metrics:
            self.stats.environment.air_quality_avg = metrics["air_quality_avg"]
        if "errors" in metrics:
            self.stats.environment.errors += metrics["errors"]
    
    def update_energy_metrics(self, metrics: Dict[str, Any]):
        """
        更新能源指标
        
        Args:
            metrics: 能源指标
        """
        if "current_power" in metrics:
            self.stats.energy.current_power = metrics["current_power"]
        if "energy_today" in metrics:
            self.stats.energy.energy_today = metrics["energy_today"]
        if "energy_month" in metrics:
            self.stats.energy.energy_month = metrics["energy_month"]
        if "energy_year" in metrics:
            self.stats.energy.energy_year = metrics["energy_year"]
        if "cost_today" in metrics:
            self.stats.energy.cost_today = metrics["cost_today"]
        if "cost_month" in metrics:
            self.stats.energy.cost_month = metrics["cost_month"]
        if "peak_power" in metrics:
            self.stats.energy.peak_power = max(self.stats.energy.peak_power, metrics["peak_power"])
        if "suggestions_generated" in metrics:
            self.stats.energy.suggestions_generated += metrics["suggestions_generated"]
        if "errors" in metrics:
            self.stats.energy.errors += metrics["errors"]
    
    def update_security_metrics(self, metrics: Dict[str, Any]):
        """
        更新安全指标
        
        Args:
            metrics: 安全指标
        """
        if "alarm_status" in metrics:
            self.stats.security.alarm_status = metrics["alarm_status"]
        if "total_sensors" in metrics:
            self.stats.security.total_sensors = metrics["total_sensors"]
        if "triggered_sensors" in metrics:
            self.stats.security.triggered_sensors = metrics["triggered_sensors"]
        if "offline_sensors" in metrics:
            self.stats.security.offline_sensors = metrics["offline_sensors"]
        if "bypassed_sensors" in metrics:
            self.stats.security.bypassed_sensors = metrics["bypassed_sensors"]
        if "events_today" in metrics:
            self.stats.security.events_today = metrics["events_today"]
        if "alarms_triggered" in metrics:
            self.stats.security.alarms_triggered += metrics["alarms_triggered"]
        if "false_alarms" in metrics:
            self.stats.security.false_alarms += metrics["false_alarms"]
        if "cameras_online" in metrics:
            self.stats.security.cameras_online = metrics["cameras_online"]
        if "cameras_recording" in metrics:
            self.stats.security.cameras_recording = metrics["cameras_recording"]
        if "errors" in metrics:
            self.stats.security.errors += metrics["errors"]
    
    def record_device_command(self, success: bool, response_time_ms: float = 0.0):
        """
        记录设备命令
        
        Args:
            success: 是否成功
            response_time_ms: 响应时间
        """
        self.stats.device.commands_sent += 1
        if success:
            self.stats.device.commands_succeeded += 1
        else:
            self.stats.device.commands_failed += 1
        
        # 更新平均响应时间
        if response_time_ms > 0:
            total = self.stats.device.commands_sent
            current_avg = self.stats.device.avg_response_time_ms
            self.stats.device.avg_response_time_ms = (current_avg * (total - 1) + response_time_ms) / total
    
    def record_scene_action(self, success: bool, execution_time_ms: float = 0.0):
        """
        记录场景动作
        
        Args:
            success: 是否成功
            execution_time_ms: 执行时间
        """
        self.stats.scene.actions_executed += 1
        if success:
            self.stats.scene.actions_succeeded += 1
        else:
            self.stats.scene.actions_failed += 1
        
        # 更新平均执行时间
        if execution_time_ms > 0:
            total = self.stats.scene.actions_executed
            current_avg = self.stats.scene.avg_execution_time_ms
            self.stats.scene.avg_execution_time_ms = (current_avg * (total - 1) + execution_time_ms) / total
    
    def record_environment_reading(self, count: int = 1):
        """记录环境读数"""
        self.stats.environment.readings_collected += count
    
    def record_environment_alert(self):
        """记录环境告警"""
        self.stats.environment.alerts_triggered += 1
    
    def record_energy_reading(self, power: float):
        """记录能源读数"""
        self.stats.energy.current_power = power
        self.stats.energy.peak_power = max(self.stats.energy.peak_power, power)
    
    def record_security_event(self, is_alarm: bool = False):
        """记录安全事件"""
        if is_alarm:
            self.stats.security.alarms_triggered += 1
        self.stats.security.events_today += 1
    
    def record_error(self, component: SmartHomeComponent):
        """记录错误"""
        if component == SmartHomeComponent.DEVICE_MANAGER:
            self.stats.device.errors += 1
        elif component == SmartHomeComponent.SCENE_AUTOMATION:
            self.stats.scene.errors += 1
        elif component == SmartHomeComponent.ENVIRONMENT:
            self.stats.environment.errors += 1
        elif component == SmartHomeComponent.ENERGY:
            self.stats.energy.errors += 1
        elif component == SmartHomeComponent.SECURITY:
            self.stats.security.errors += 1
    
    def get_stats(self, component: Optional[SmartHomeComponent] = None) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            component: 组件类型
        
        Returns:
            统计字典
        """
        if component == SmartHomeComponent.DEVICE_MANAGER:
            return {
                "total_devices": self.stats.device.total_devices,
                "online_devices": self.stats.device.online_devices,
                "offline_devices": self.stats.device.offline_devices,
                "devices_by_type": self.stats.device.devices_by_type,
                "commands_sent": self.stats.device.commands_sent,
                "commands_succeeded": self.stats.device.commands_succeeded,
                "commands_failed": self.stats.device.commands_failed,
                "success_rate": (self.stats.device.commands_succeeded / self.stats.device.commands_sent * 100) if self.stats.device.commands_sent > 0 else 0,
                "avg_response_time_ms": self.stats.device.avg_response_time_ms,
                "errors": self.stats.device.errors
            }
        elif component == SmartHomeComponent.SCENE_AUTOMATION:
            return {
                "total_scenes": self.stats.scene.total_scenes,
                "total_rules": self.stats.scene.total_rules,
                "active_rules": self.stats.scene.active_rules,
                "scenes_activated": self.stats.scene.scenes_activated,
                "rules_triggered": self.stats.scene.rules_triggered,
                "actions_executed": self.stats.scene.actions_executed,
                "actions_succeeded": self.stats.scene.actions_succeeded,
                "actions_failed": self.stats.scene.actions_failed,
                "success_rate": (self.stats.scene.actions_succeeded / self.stats.scene.actions_executed * 100) if self.stats.scene.actions_executed > 0 else 0,
                "avg_execution_time_ms": self.stats.scene.avg_execution_time_ms,
                "errors": self.stats.scene.errors
            }
        elif component == SmartHomeComponent.ENVIRONMENT:
            return {
                "total_sensors": self.stats.environment.total_sensors,
                "active_sensors": self.stats.environment.active_sensors,
                "readings_collected": self.stats.environment.readings_collected,
                "alerts_triggered": self.stats.environment.alerts_triggered,
                "temperature_avg": self.stats.environment.temperature_avg,
                "humidity_avg": self.stats.environment.humidity_avg,
                "air_quality_avg": self.stats.environment.air_quality_avg,
                "errors": self.stats.environment.errors
            }
        elif component == SmartHomeComponent.ENERGY:
            return {
                "current_power": self.stats.energy.current_power,
                "energy_today": self.stats.energy.energy_today,
                "energy_month": self.stats.energy.energy_month,
                "energy_year": self.stats.energy.energy_year,
                "cost_today": self.stats.energy.cost_today,
                "cost_month": self.stats.energy.cost_month,
                "peak_power": self.stats.energy.peak_power,
                "suggestions_generated": self.stats.energy.suggestions_generated,
                "errors": self.stats.energy.errors
            }
        elif component == SmartHomeComponent.SECURITY:
            return {
                "alarm_status": self.stats.security.alarm_status,
                "total_sensors": self.stats.security.total_sensors,
                "triggered_sensors": self.stats.security.triggered_sensors,
                "offline_sensors": self.stats.security.offline_sensors,
                "bypassed_sensors": self.stats.security.bypassed_sensors,
                "events_today": self.stats.security.events_today,
                "alarms_triggered": self.stats.security.alarms_triggered,
                "false_alarms": self.stats.security.false_alarms,
                "cameras_online": self.stats.security.cameras_online,
                "cameras_recording": self.stats.security.cameras_recording,
                "errors": self.stats.security.errors
            }
        else:
            return {
                "device": self.get_stats(SmartHomeComponent.DEVICE_MANAGER),
                "scene": self.get_stats(SmartHomeComponent.SCENE_AUTOMATION),
                "environment": self.get_stats(SmartHomeComponent.ENVIRONMENT),
                "energy": self.get_stats(SmartHomeComponent.ENERGY),
                "security": self.get_stats(SmartHomeComponent.SECURITY),
                "uptime": time.time() - self.stats.start_time
            }
    
    def get_history(self, component: Optional[SmartHomeComponent] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Args:
            component: 组件类型
            limit: 返回数量
        
        Returns:
            历史记录
        """
        history = self.history[-limit:]
        
        if component and component != SmartHomeComponent.ALL:
            filtered = []
            for entry in history:
                filtered_entry = {
                    "timestamp": entry["timestamp"],
                    component.value: entry.get(component.value, {})
                }
                filtered.append(filtered_entry)
            return filtered
        
        return history
    
    def reset_stats(self, component: Optional[SmartHomeComponent] = None):
        """
        重置统计
        
        Args:
            component: 组件类型
        """
        if component == SmartHomeComponent.DEVICE_MANAGER:
            self.stats.device = DeviceMetrics()
        elif component == SmartHomeComponent.SCENE_AUTOMATION:
            self.stats.scene = SceneMetrics()
        elif component == SmartHomeComponent.ENVIRONMENT:
            self.stats.environment = EnvironmentMetrics()
        elif component == SmartHomeComponent.ENERGY:
            self.stats.energy = EnergyMetrics()
        elif component == SmartHomeComponent.SECURITY:
            self.stats.security = SecurityMetrics()
        else:
            self.stats = SmartHomeStats()
        
        logger.info(f"Stats reset for {component.value if component else 'all'}")
    
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
        logger.info("Shutting down SmartHomeMetrics...")
        
        self._stop_sampling.set()
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2)
        
        self.history.clear()
        
        logger.info("SmartHomeMetrics shutdown completed")

# 单例模式实现
_smart_home_metrics_instance: Optional[SmartHomeMetrics] = None

def get_smart_home_metrics(config: Optional[SmartHomeConfig] = None) -> SmartHomeMetrics:
    """
    获取智能家居指标收集器单例
    
    Args:
        config: 指标配置
    
    Returns:
        智能家居指标收集器实例
    """
    global _smart_home_metrics_instance
    if _smart_home_metrics_instance is None:
        _smart_home_metrics_instance = SmartHomeMetrics(config)
    return _smart_home_metrics_instance

