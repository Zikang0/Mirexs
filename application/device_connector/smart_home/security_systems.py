"""
安全系统模块 - Mirexs智能家居集成

提供家庭安全系统功能，包括：
1. 入侵检测
2. 门窗传感器
3. 运动检测
4. 摄像头监控
5. 报警系统
6. 紧急按钮
7. 安全自动化
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class AlarmStatus(Enum):
    """报警状态枚举"""
    DISARMED = "disarmed"          # 撤防
    ARMED_HOME = "armed_home"      # 在家布防
    ARMED_AWAY = "armed_away"      # 离家布防
    ARMED_NIGHT = "armed_night"    # 夜间布防
    TRIGGERED = "triggered"        # 已触发
    ALERT = "alert"                # 告警中
    DELAY = "delay"                # 延迟中

class SensorType(Enum):
    """传感器类型枚举"""
    DOOR = "door"                  # 门磁
    WINDOW = "window"              # 窗磁
    MOTION = "motion"              # 运动传感器
    GLASS_BREAK = "glass_break"    # 玻璃破碎
    SMOKE = "smoke"                # 烟雾
    CO = "co"                      # 一氧化碳
    GAS = "gas"                    # 燃气
    WATER = "water"                # 漏水
    TEMPERATURE = "temperature"    # 温度
    VIBRATION = "vibration"        # 震动
    TAMPER = "tamper"              # 防拆

class SecurityEvent(Enum):
    """安全事件枚举"""
    INTRUSION = "intrusion"        # 入侵
    DOOR_OPEN = "door_open"        # 开门
    WINDOW_OPEN = "window_open"    # 开窗
    MOTION_DETECTED = "motion_detected"  # 运动检测
    GLASS_BREAK = "glass_break"    # 玻璃破碎
    FIRE = "fire"                  # 火灾
    GAS_LEAK = "gas_leak"          # 燃气泄漏
    WATER_LEAK = "water_leak"      # 漏水
    TAMPER = "tamper"              # 设备被破坏
    LOW_BATTERY = "low_battery"    # 电量低
    SYSTEM_ERROR = "system_error"  # 系统错误
    EMERGENCY = "emergency"        # 紧急事件

@dataclass
class SecuritySensor:
    """安全传感器"""
    id: str
    name: str
    type: SensorType
    location: str
    zone: Optional[str] = None
    battery_level: Optional[int] = None
    status: str = "normal"  # normal, triggered, tampered, offline
    last_triggered: Optional[float] = None
    last_seen: Optional[float] = None
    bypassed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Camera:
    """摄像头"""
    id: str
    name: str
    location: str
    rtsp_url: Optional[str] = None
    snapshot_url: Optional[str] = None
    status: str = "online"
    motion_detection: bool = False
    recording: bool = False
    last_motion: Optional[float] = None
    last_snapshot: Optional[float] = None

@dataclass
class Alarm:
    """报警器"""
    id: str
    name: str
    location: str
    type: str  # siren, strobe, both
    volume: int = 100
    status: str = "off"

@dataclass
class SecurityZone:
    """安全区域"""
    id: str
    name: str
    sensors: List[str]
    cameras: List[str] = field(default_factory=list)
    alarms: List[str] = field(default_factory=list)
    arm_mode: str = "all"  # all, any

@dataclass
class SecurityEventLog:
    """安全事件日志"""
    id: str
    event_type: SecurityEvent
    sensor_id: Optional[str] = None
    zone_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityConfig:
    """安全系统配置"""
    # 布防配置
    exit_delay: int = 30  # 秒
    entry_delay: int = 30  # 秒
    auto_arm: bool = False
    auto_arm_time: Optional[str] = None  # "22:00"
    
    # 报警配置
    alarm_duration: int = 300  # 秒
    siren_enabled: bool = True
    notification_enabled: bool = True
    
    # 监控配置
    monitor_interval: int = 60  # 秒
    offline_timeout: int = 300  # 秒
    
    # 录像配置
    record_on_motion: bool = True
    record_duration: int = 60  # 秒
    snapshot_interval: int = 3600  # 秒

class SecuritySystems:
    """
    安全系统管理器
    
    负责家庭安全系统的监控和管理。
    """
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        初始化安全系统管理器
        
        Args:
            config: 安全系统配置
        """
        self.config = config or SecurityConfig()
        
        # 设备存储
        self.sensors: Dict[str, SecuritySensor] = {}
        self.cameras: Dict[str, Camera] = {}
        self.alarms: Dict[str, Alarm] = {}
        self.zones: Dict[str, SecurityZone] = {}
        
        # 状态
        self.alarm_status = AlarmStatus.DISARMED
        self.exit_until: Optional[float] = None
        self.entry_until: Optional[float] = None
        
        # 事件日志
        self.event_log: List[SecurityEventLog] = []
        
        # 触发状态
        self.triggered_sensors: Dict[str, float] = {}
        self.triggered_zones: Dict[str, float] = {}
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        
        # 回调函数
        self.on_status_changed: Optional[Callable[[AlarmStatus, AlarmStatus], None]] = None
        self.on_sensor_triggered: Optional[Callable[[SecuritySensor], None]] = None
        self.on_event: Optional[Callable[[SecurityEventLog], None]] = None
        self.on_motion_detected: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "events": 0,
            "alarms": 0,
            "false_alarms": 0,
            "errors": 0
        }
        
        # 启动监控
        self._start_monitoring()
        
        logger.info("SecuritySystems initialized")
    
    def _start_monitoring(self):
        """启动监控"""
        def monitor_loop():
            while not self._stop_monitor.is_set():
                try:
                    self._check_sensor_status()
                    self._check_alarm_timers()
                    self._stop_monitor.wait(self.config.monitor_interval)
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    self.stats["errors"] += 1
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("Security monitoring started")
    
    def _check_sensor_status(self):
        """检查传感器状态"""
        current_time = time.time()
        
        for sensor in self.sensors.values():
            # 检查离线
            if sensor.last_seen:
                if current_time - sensor.last_seen > self.config.offline_timeout:
                    if sensor.status != "offline":
                        sensor.status = "offline"
                        self._log_event(SecurityEvent.SYSTEM_ERROR, sensor.id, 
                                       {"error": "sensor_offline"})
    
    def _check_alarm_timers(self):
        """检查报警定时器"""
        current_time = time.time()
        
        # 检查退出延迟
        if self.exit_until and current_time > self.exit_until:
            self.exit_until = None
            logger.info("Exit delay finished")
        
        # 检查进入延迟
        if self.entry_until and current_time > self.entry_until:
            self.entry_until = None
            self._trigger_alarm()
        
        # 检查报警持续时间
        if self.alarm_status == AlarmStatus.TRIGGERED:
            # 检查是否超过报警持续时间
            pass
    
    def arm(self, mode: str = "away") -> bool:
        """
        布防
        
        Args:
            mode: 布防模式 (home, away, night)
        
        Returns:
            是否成功
        """
        if self.alarm_status != AlarmStatus.DISARMED:
            logger.warning(f"Cannot arm: current status is {self.alarm_status.value}")
            return False
        
        new_status = AlarmStatus.ARMED_AWAY
        if mode == "home":
            new_status = AlarmStatus.ARMED_HOME
        elif mode == "night":
            new_status = AlarmStatus.ARMED_NIGHT
        
        old_status = self.alarm_status
        self.alarm_status = new_status
        self.exit_until = time.time() + self.config.exit_delay
        
        logger.info(f"System armed ({mode}) with {self.config.exit_delay}s exit delay")
        
        if self.on_status_changed:
            self.on_status_changed(new_status, old_status)
        
        return True
    
    def disarm(self) -> bool:
        """
        撤防
        
        Returns:
            是否成功
        """
        if self.alarm_status == AlarmStatus.DISARMED:
            logger.warning("Already disarmed")
            return False
        
        old_status = self.alarm_status
        self.alarm_status = AlarmStatus.DISARMED
        self.exit_until = None
        self.entry_until = None
        
        # 清除触发状态
        self.triggered_sensors.clear()
        self.triggered_zones.clear()
        
        # 停止所有报警器
        self._stop_all_alarms()
        
        logger.info("System disarmed")
        
        if self.on_status_changed:
            self.on_status_changed(AlarmStatus.DISARMED, old_status)
        
        return True
    
    def trigger_sensor(self, sensor_id: str) -> bool:
        """
        触发传感器
        
        Args:
            sensor_id: 传感器ID
        
        Returns:
            是否成功
        """
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not found")
            return False
        
        sensor = self.sensors[sensor_id]
        
        if sensor.bypassed:
            logger.debug(f"Sensor {sensor.name} is bypassed")
            return False
        
        sensor.last_triggered = time.time()
        sensor.status = "triggered"
        
        self.triggered_sensors[sensor_id] = time.time()
        
        logger.info(f"Sensor triggered: {sensor.name} ({sensor.type.value})")
        
        if self.on_sensor_triggered:
            self.on_sensor_triggered(sensor)
        
        # 记录事件
        event_type = self._get_event_type(sensor.type)
        self._log_event(event_type, sensor_id)
        
        # 根据布防状态处理
        if self.alarm_status != AlarmStatus.DISARMED:
            self._handle_triggered_sensor(sensor)
        
        return True
    
    def _get_event_type(self, sensor_type: SensorType) -> SecurityEvent:
        """根据传感器类型获取事件类型"""
        mapping = {
            SensorType.DOOR: SecurityEvent.DOOR_OPEN,
            SensorType.WINDOW: SecurityEvent.WINDOW_OPEN,
            SensorType.MOTION: SecurityEvent.MOTION_DETECTED,
            SensorType.GLASS_BREAK: SecurityEvent.GLASS_BREAK,
            SensorType.SMOKE: SecurityEvent.FIRE,
            SensorType.GAS: SecurityEvent.GAS_LEAK,
            SensorType.WATER: SecurityEvent.WATER_LEAK,
            SensorType.TAMPER: SecurityEvent.TAMPER
        }
        return mapping.get(sensor_type, SecurityEvent.INTRUSION)
    
    def _handle_triggered_sensor(self, sensor: SecuritySensor):
        """处理触发的传感器"""
        # 检查是否在进入延迟中
        if self.entry_until:
            logger.debug(f"Sensor triggered during entry delay: {sensor.name}")
            return
        
        # 检查是否在退出延迟中
        if self.exit_until:
            logger.debug(f"Sensor triggered during exit delay: {sensor.name}")
            return
        
        # 检查是否需要进入延迟
        if self.config.entry_delay > 0 and self.alarm_status != AlarmStatus.TRIGGERED:
            if not self.entry_until:
                self.entry_until = time.time() + self.config.entry_delay
                logger.info(f"Entry delay started: {self.config.entry_delay}s")
                
                # 触发进入提示音
                self._play_entry_tone()
                return
        
        # 触发报警
        self._trigger_alarm()
    
    def _trigger_alarm(self):
        """触发报警"""
        if self.alarm_status == AlarmStatus.TRIGGERED:
            return
        
        logger.warning("ALARM TRIGGERED!")
        
        old_status = self.alarm_status
        self.alarm_status = AlarmStatus.TRIGGERED
        self.stats["alarms"] += 1
        
        # 记录事件
        self._log_event(SecurityEvent.INTRUSION)
        
        # 启动报警器
        if self.config.siren_enabled:
            self._activate_alarms()
        
        # 开始录像
        if self.config.record_on_motion:
            self._start_recording()
        
        # 发送通知
        if self.config.notification_enabled:
            self._send_alert_notification()
        
        if self.on_status_changed:
            self.on_status_changed(AlarmStatus.TRIGGERED, old_status)
    
    def _stop_all_alarms(self):
        """停止所有报警器"""
        for alarm in self.alarms.values():
            alarm.status = "off"
    
    def _activate_alarms(self):
        """激活报警器"""
        for alarm in self.alarms.values():
            alarm.status = "on"
    
    def _play_entry_tone(self):
        """播放进入提示音"""
        # 实际实现中会播放提示音
        pass
    
    def _start_recording(self):
        """开始录像"""
        for camera in self.cameras.values():
            if camera.motion_detection:
                camera.recording = True
    
    def _send_alert_notification(self):
        """发送告警通知"""
        # 实际实现中会发送推送通知
        pass
    
    def _log_event(self, event_type: SecurityEvent, sensor_id: Optional[str] = None,
                   details: Optional[Dict[str, Any]] = None):
        """记录事件"""
        event = SecurityEventLog(
            id=str(uuid.uuid4()),
            event_type=event_type,
            sensor_id=sensor_id,
            details=details or {}
        )
        
        self.event_log.append(event)
        self.stats["events"] += 1
        
        # 限制日志大小
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]
        
        if self.on_event:
            self.on_event(event)
    
    def register_sensor(self, sensor_id: str, name: str, type: SensorType,
                       location: str, zone_id: Optional[str] = None) -> bool:
        """
        注册传感器
        
        Args:
            sensor_id: 传感器ID
            name: 传感器名称
            type: 传感器类型
            location: 位置
            zone_id: 区域ID
        
        Returns:
            是否成功
        """
        if sensor_id in self.sensors:
            logger.warning(f"Sensor {sensor_id} already exists")
            return False
        
        sensor = SecuritySensor(
            id=sensor_id,
            name=name,
            type=type,
            location=location,
            zone=zone_id
        )
        
        self.sensors[sensor_id] = sensor
        
        logger.info(f"Sensor registered: {name} ({sensor_id}) at {location}")
        
        return True
    
    def register_camera(self, camera_id: str, name: str, location: str,
                       rtsp_url: Optional[str] = None) -> bool:
        """
        注册摄像头
        
        Args:
            camera_id: 摄像头ID
            name: 摄像头名称
            location: 位置
            rtsp_url: RTSP URL
        
        Returns:
            是否成功
        """
        if camera_id in self.cameras:
            logger.warning(f"Camera {camera_id} already exists")
            return False
        
        camera = Camera(
            id=camera_id,
            name=name,
            location=location,
            rtsp_url=rtsp_url
        )
        
        self.cameras[camera_id] = camera
        
        logger.info(f"Camera registered: {name} ({camera_id}) at {location}")
        
        return True
    
    def register_alarm(self, alarm_id: str, name: str, location: str,
                      type: str = "both") -> bool:
        """
        注册报警器
        
        Args:
            alarm_id: 报警器ID
            name: 报警器名称
            location: 位置
            type: 类型
        
        Returns:
            是否成功
        """
        if alarm_id in self.alarms:
            logger.warning(f"Alarm {alarm_id} already exists")
            return False
        
        alarm = Alarm(
            id=alarm_id,
            name=name,
            location=location,
            type=type
        )
        
        self.alarms[alarm_id] = alarm
        
        logger.info(f"Alarm registered: {name} ({alarm_id}) at {location}")
        
        return True
    
    def create_zone(self, zone_id: str, name: str, sensors: List[str],
                   cameras: Optional[List[str]] = None,
                   alarms: Optional[List[str]] = None) -> bool:
        """
        创建安全区域
        
        Args:
            zone_id: 区域ID
            name: 区域名称
            sensors: 传感器ID列表
            cameras: 摄像头ID列表
            alarms: 报警器ID列表
        
        Returns:
            是否成功
        """
        if zone_id in self.zones:
            logger.warning(f"Zone {zone_id} already exists")
            return False
        
        zone = SecurityZone(
            id=zone_id,
            name=name,
            sensors=sensors,
            cameras=cameras or [],
            alarms=alarms or []
        )
        
        self.zones[zone_id] = zone
        
        logger.info(f"Zone created: {name} ({zone_id}) with {len(sensors)} sensors")
        
        return True
    
    def bypass_sensor(self, sensor_id: str, bypass: bool = True):
        """
        旁路传感器
        
        Args:
            sensor_id: 传感器ID
            bypass: 是否旁路
        """
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not found")
            return
        
        self.sensors[sensor_id].bypassed = bypass
        logger.info(f"Sensor {sensor_id} bypassed: {bypass}")
    
    def camera_motion_detected(self, camera_id: str):
        """
        摄像头检测到运动
        
        Args:
            camera_id: 摄像头ID
        """
        if camera_id not in self.cameras:
            return
        
        camera = self.cameras[camera_id]
        camera.last_motion = time.time()
        
        if self.on_motion_detected:
            self.on_motion_detected(camera_id)
        
        # 如果布防中，触发事件
        if self.alarm_status != AlarmStatus.DISARMED:
            self._log_event(SecurityEvent.MOTION_DETECTED, None, {"camera": camera_id})
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取安全系统状态
        
        Returns:
            状态字典
        """
        return {
            "alarm_status": self.alarm_status.value,
            "exit_remaining": max(0, self.exit_until - time.time()) if self.exit_until else 0,
            "entry_remaining": max(0, self.entry_until - time.time()) if self.entry_until else 0,
            "sensors": {
                "total": len(self.sensors),
                "triggered": len([s for s in self.sensors.values() if s.status == "triggered"]),
                "offline": len([s for s in self.sensors.values() if s.status == "offline"]),
                "bypassed": len([s for s in self.sensors.values() if s.bypassed])
            },
            "cameras": {
                "total": len(self.cameras),
                "online": len([c for c in self.cameras.values() if c.status == "online"]),
                "recording": len([c for c in self.cameras.values() if c.recording])
            },
            "zones": len(self.zones),
            "events_today": len([e for e in self.event_log if e.timestamp > time.time() - 86400]),
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭安全系统"""
        logger.info("Shutting down SecuritySystems...")
        
        self._stop_monitor.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        # 撤防
        if self.alarm_status != AlarmStatus.DISARMED:
            self.disarm()
        
        self.sensors.clear()
        self.cameras.clear()
        self.alarms.clear()
        self.zones.clear()
        self.event_log.clear()
        
        logger.info("SecuritySystems shutdown completed")

# 单例模式实现
_security_systems_instance: Optional[SecuritySystems] = None

def get_security_systems(config: Optional[SecurityConfig] = None) -> SecuritySystems:
    """
    获取安全系统管理器单例
    
    Args:
        config: 安全系统配置
    
    Returns:
        安全系统管理器实例
    """
    global _security_systems_instance
    if _security_systems_instance is None:
        _security_systems_instance = SecuritySystems(config)
    return _security_systems_instance

