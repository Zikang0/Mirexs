"""
环境感知模块 - Mirexs智能家居集成

提供环境信息感知功能，包括：
1. 温度监测
2. 湿度监测
3. 空气质量监测
4. 光照强度
5. 噪音水平
6. 气压监测
7. 天气信息
"""

import logging
import time
import threading
import math
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class SensorType(Enum):
    """传感器类型枚举"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    AIR_QUALITY = "air_quality"
    LIGHT = "light"
    NOISE = "noise"
    PRESSURE = "pressure"
    WEATHER = "weather"
    UV = "uv"
    WIND = "wind"
    RAIN = "rain"
    CUSTOM = "custom"

class AirQuality(Enum):
    """空气质量等级"""
    GOOD = "good"
    MODERATE = "moderate"
    UNHEALTHY_SENSITIVE = "unhealthy_sensitive"
    UNHEALTHY = "unhealthy"
    VERY_UNHEALTHY = "very_unhealthy"
    HAZARDOUS = "hazardous"
    UNKNOWN = "unknown"

@dataclass
class EnvironmentData:
    """环境数据"""
    id: str
    sensor_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    location: Optional[str] = None
    accuracy: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TemperatureData(EnvironmentData):
    """温度数据"""
    unit: str = "celsius"  # celsius, fahrenheit

@dataclass
class HumidityData(EnvironmentData):
    """湿度数据"""
    unit: str = "percent"

@dataclass
class AirQualityData(EnvironmentData):
    """空气质量数据"""
    unit: str = "aqi"
    quality: AirQuality = AirQuality.UNKNOWN
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    co2: Optional[float] = None
    voc: Optional[float] = None

@dataclass
class LightData(EnvironmentData):
    """光照数据"""
    unit: str = "lux"

@dataclass
class NoiseData(EnvironmentData):
    """噪音数据"""
    unit: str = "db"

@dataclass
class PressureData(EnvironmentData):
    """气压数据"""
    unit: str = "hpa"

@dataclass
class WeatherData(EnvironmentData):
    """天气数据"""
    unit: str = "celsius"
    condition: str = "unknown"
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    uv_index: Optional[int] = None
    visibility: Optional[float] = None

@dataclass
class EnvironmentSensor:
    """环境传感器"""
    id: str
    name: str
    type: SensorType
    location: str
    room: Optional[str] = None
    model: Optional[str] = None
    manufacturer: Optional[str] = None
    battery_level: Optional[int] = None
    status: str = "online"  # online, offline, error
    last_reading: Optional[EnvironmentData] = None
    last_seen: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EnvironmentConfig:
    """环境感知配置"""
    # 采样配置
    sample_interval: int = 60  # 秒
    history_retention: int = 86400  # 秒（1天）
    
    # 阈值配置
    temperature_high: float = 30.0
    temperature_low: float = 16.0
    humidity_high: float = 70.0
    humidity_low: float = 30.0
    air_quality_threshold: int = 100
    
    # 告警配置
    enable_alerts: bool = True
    alert_cooldown: int = 300  # 秒

class EnvironmentSensing:
    """
    环境感知管理器
    
    负责环境数据的采集、存储和分析。
    """
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """
        初始化环境感知管理器
        
        Args:
            config: 环境感知配置
        """
        self.config = config or EnvironmentConfig()
        
        # 传感器存储
        self.sensors: Dict[str, EnvironmentSensor] = {}
        self.sensors_by_location: Dict[str, List[str]] = {}
        self.sensors_by_type: Dict[SensorType, List[str]] = {}
        
        # 环境数据
        self.readings: Dict[str, List[EnvironmentData]] = {}
        self.latest_readings: Dict[str, EnvironmentData] = {}
        
        # 告警状态
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self.last_alert_time: Dict[str, float] = {}
        
        # 采样线程
        self._sampling_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # 回调函数
        self.on_data_received: Optional[Callable[[EnvironmentData], None]] = None
        self.on_threshold_exceeded: Optional[Callable[[str, float, float], None]] = None
        self.on_sensor_status_changed: Optional[Callable[[str, str, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "total_readings": 0,
            "active_sensors": 0,
            "alerts_triggered": 0,
            "errors": 0
        }
        
        # 启动采样
        self._start_sampling()
        
        logger.info("EnvironmentSensing initialized")
    
    def _start_sampling(self):
        """启动采样"""
        def sampling_loop():
            while not self._stop_sampling.is_set():
                try:
                    self._sample_all_sensors()
                    self._check_thresholds()
                    self._stop_sampling.wait(self.config.sample_interval)
                except Exception as e:
                    logger.error(f"Sampling error: {e}")
                    self.stats["errors"] += 1
        
        def cleanup_loop():
            while not self._stop_sampling.is_set():
                try:
                    self._cleanup_old_data()
                    self._stop_sampling.wait(3600)  # 每小时清理一次
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        self._sampling_thread = threading.Thread(target=sampling_loop, daemon=True)
        self._sampling_thread.start()
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        logger.debug("Environment sensing started")
    
    def _sample_all_sensors(self):
        """采样所有传感器"""
        for sensor_id, sensor in self.sensors.items():
            if sensor.status == "online":
                data = self._read_sensor(sensor_id)
                if data:
                    self._process_reading(data)
    
    def _read_sensor(self, sensor_id: str) -> Optional[EnvironmentData]:
        """读取传感器数据"""
        sensor = self.sensors.get(sensor_id)
        if not sensor:
            return None
        
        # 实际实现中会通过硬件接口读取
        # 这里返回模拟数据
        import random
        
        if sensor.type == SensorType.TEMPERATURE:
            value = random.uniform(18, 28)
            return TemperatureData(
                id=str(uuid.uuid4()),
                sensor_id=sensor_id,
                sensor_type=sensor.type,
                value=value,
                unit="celsius",
                location=sensor.location
            )
        elif sensor.type == SensorType.HUMIDITY:
            value = random.uniform(30, 70)
            return HumidityData(
                id=str(uuid.uuid4()),
                sensor_id=sensor_id,
                sensor_type=sensor.type,
                value=value,
                unit="percent",
                location=sensor.location
            )
        elif sensor.type == SensorType.AIR_QUALITY:
            pm25 = random.uniform(0, 100)
            aqi = self._calculate_aqi(pm25)
            quality = self._get_air_quality(aqi)
            return AirQualityData(
                id=str(uuid.uuid4()),
                sensor_id=sensor_id,
                sensor_type=sensor.type,
                value=aqi,
                unit="aqi",
                quality=quality,
                pm25=pm25,
                pm10=pm25 * random.uniform(1.5, 2.0),
                co2=random.uniform(400, 800),
                location=sensor.location
            )
        elif sensor.type == SensorType.LIGHT:
            value = random.uniform(0, 1000)
            return LightData(
                id=str(uuid.uuid4()),
                sensor_id=sensor_id,
                sensor_type=sensor.type,
                value=value,
                unit="lux",
                location=sensor.location
            )
        elif sensor.type == SensorType.NOISE:
            value = random.uniform(30, 80)
            return NoiseData(
                id=str(uuid.uuid4()),
                sensor_id=sensor_id,
                sensor_type=sensor.type,
                value=value,
                unit="db",
                location=sensor.location
            )
        
        return None
    
    def _calculate_aqi(self, pm25: float) -> int:
        """计算空气质量指数"""
        # 简化的AQI计算
        if pm25 <= 12.0:
            return int((50/12) * pm25)
        elif pm25 <= 35.4:
            return int(50 + (50/23.4) * (pm25 - 12.0))
        elif pm25 <= 55.4:
            return int(100 + (50/20) * (pm25 - 35.4))
        elif pm25 <= 150.4:
            return int(150 + (50/95) * (pm25 - 55.4))
        elif pm25 <= 250.4:
            return int(200 + (100/100) * (pm25 - 150.4))
        else:
            return 300
    
    def _get_air_quality(self, aqi: int) -> AirQuality:
        """根据AQI获取空气质量等级"""
        if aqi <= 50:
            return AirQuality.GOOD
        elif aqi <= 100:
            return AirQuality.MODERATE
        elif aqi <= 150:
            return AirQuality.UNHEALTHY_SENSITIVE
        elif aqi <= 200:
            return AirQuality.UNHEALTHY
        elif aqi <= 300:
            return AirQuality.VERY_UNHEALTHY
        else:
            return AirQuality.HAZARDOUS
    
    def _process_reading(self, data: EnvironmentData):
        """处理传感器读数"""
        sensor_id = data.sensor_id
        
        # 存储数据
        if sensor_id not in self.readings:
            self.readings[sensor_id] = []
        
        self.readings[sensor_id].append(data)
        self.latest_readings[sensor_id] = data
        self.stats["total_readings"] += 1
        
        # 更新传感器信息
        if sensor_id in self.sensors:
            sensor = self.sensors[sensor_id]
            sensor.last_reading = data
            sensor.last_seen = time.time()
        
        logger.debug(f"Reading from {sensor_id}: {data.value} {data.unit}")
        
        if self.on_data_received:
            self.on_data_received(data)
    
    def _check_thresholds(self):
        """检查阈值"""
        if not self.config.enable_alerts:
            return
        
        current_time = time.time()
        
        for sensor_id, data in self.latest_readings.items():
            # 检查冷却时间
            if sensor_id in self.last_alert_time:
                if current_time - self.last_alert_time[sensor_id] < self.config.alert_cooldown:
                    continue
            
            alert = None
            
            if data.sensor_type == SensorType.TEMPERATURE:
                if data.value > self.config.temperature_high:
                    alert = ("temperature_high", data.value, self.config.temperature_high)
                elif data.value < self.config.temperature_low:
                    alert = ("temperature_low", data.value, self.config.temperature_low)
            
            elif data.sensor_type == SensorType.HUMIDITY:
                if data.value > self.config.humidity_high:
                    alert = ("humidity_high", data.value, self.config.humidity_high)
                elif data.value < self.config.humidity_low:
                    alert = ("humidity_low", data.value, self.config.humidity_low)
            
            elif data.sensor_type == SensorType.AIR_QUALITY:
                if data.value > self.config.air_quality_threshold:
                    alert = ("air_quality", data.value, self.config.air_quality_threshold)
            
            if alert:
                alert_type, value, threshold = alert
                
                self.alerts[sensor_id] = {
                    "type": alert_type,
                    "value": value,
                    "threshold": threshold,
                    "timestamp": current_time,
                    "data": data
                }
                
                self.last_alert_time[sensor_id] = current_time
                self.stats["alerts_triggered"] += 1
                
                logger.warning(f"Threshold exceeded for {sensor_id}: {value} > {threshold}")
                
                if self.on_threshold_exceeded:
                    self.on_threshold_exceeded(sensor_id, value, threshold)
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        current_time = time.time()
        cutoff_time = current_time - self.config.history_retention
        
        for sensor_id in self.readings:
            self.readings[sensor_id] = [
                r for r in self.readings[sensor_id]
                if r.timestamp >= cutoff_time
            ]
    
    def register_sensor(self, sensor_id: str, name: str, sensor_type: SensorType,
                       location: str, room: Optional[str] = None) -> bool:
        """
        注册传感器
        
        Args:
            sensor_id: 传感器ID
            name: 传感器名称
            sensor_type: 传感器类型
            location: 位置
            room: 房间
        
        Returns:
            是否成功
        """
        if sensor_id in self.sensors:
            logger.warning(f"Sensor {sensor_id} already exists")
            return False
        
        sensor = EnvironmentSensor(
            id=sensor_id,
            name=name,
            type=sensor_type,
            location=location,
            room=room
        )
        
        self.sensors[sensor_id] = sensor
        self.stats["active_sensors"] += 1
        
        # 更新索引
        if location not in self.sensors_by_location:
            self.sensors_by_location[location] = []
        self.sensors_by_location[location].append(sensor_id)
        
        if sensor_type not in self.sensors_by_type:
            self.sensors_by_type[sensor_type] = []
        self.sensors_by_type[sensor_type].append(sensor_id)
        
        logger.info(f"Sensor registered: {name} ({sensor_id}) at {location}")
        
        return True
    
    def update_sensor_status(self, sensor_id: str, status: str):
        """
        更新传感器状态
        
        Args:
            sensor_id: 传感器ID
            status: 新状态
        """
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not found")
            return
        
        old_status = self.sensors[sensor_id].status
        self.sensors[sensor_id].status = status
        
        if old_status != status:
            logger.info(f"Sensor {sensor_id} status changed: {old_status} -> {status}")
            
            if self.on_sensor_status_changed:
                self.on_sensor_status_changed(sensor_id, old_status, status)
    
    def get_latest_reading(self, sensor_id: str) -> Optional[EnvironmentData]:
        """
        获取最新读数
        
        Args:
            sensor_id: 传感器ID
        
        Returns:
            最新读数
        """
        return self.latest_readings.get(sensor_id)
    
    def get_readings(self, sensor_id: str, limit: int = 100) -> List[EnvironmentData]:
        """
        获取读数历史
        
        Args:
            sensor_id: 传感器ID
            limit: 返回数量
        
        Returns:
            读数列表
        """
        if sensor_id not in self.readings:
            return []
        
        return self.readings[sensor_id][-limit:]
    
    def get_readings_by_type(self, sensor_type: SensorType, limit: int = 100) -> List[EnvironmentData]:
        """
        获取指定类型的所有读数
        
        Args:
            sensor_type: 传感器类型
            limit: 每个传感器返回数量
        
        Returns:
            读数列表
        """
        readings = []
        sensor_ids = self.sensors_by_type.get(sensor_type, [])
        
        for sensor_id in sensor_ids:
            sensor_readings = self.get_readings(sensor_id, limit)
            readings.extend(sensor_readings)
        
        return readings
    
    def get_average_by_location(self, sensor_type: SensorType, location: str,
                               duration: int = 3600) -> Optional[float]:
        """
        获取指定位置的平均值
        
        Args:
            sensor_type: 传感器类型
            location: 位置
            duration: 时间范围（秒）
        
        Returns:
            平均值
        """
        cutoff_time = time.time() - duration
        values = []
        
        sensor_ids = self.sensors_by_location.get(location, [])
        
        for sensor_id in sensor_ids:
            sensor = self.sensors.get(sensor_id)
            if sensor and sensor.type == sensor_type:
                readings = self.readings.get(sensor_id, [])
                for reading in readings:
                    if reading.timestamp >= cutoff_time:
                        values.append(reading.value)
        
        if values:
            return sum(values) / len(values)
        
        return None
    
    def get_current_alerts(self) -> List[Dict[str, Any]]:
        """
        获取当前告警
        
        Returns:
            告警列表
        """
        return list(self.alerts.values())
    
    def clear_alert(self, sensor_id: str):
        """
        清除告警
        
        Args:
            sensor_id: 传感器ID
        """
        if sensor_id in self.alerts:
            del self.alerts[sensor_id]
            logger.info(f"Alert cleared for {sensor_id}")
    
    def get_sensors(self, sensor_type: Optional[SensorType] = None,
                   location: Optional[str] = None) -> List[EnvironmentSensor]:
        """
        获取传感器列表
        
        Args:
            sensor_type: 传感器类型
            location: 位置
        
        Returns:
            传感器列表
        """
        sensors = list(self.sensors.values())
        
        if sensor_type:
            sensors = [s for s in sensors if s.type == sensor_type]
        
        if location:
            sensors = [s for s in sensors if s.location == location]
        
        return sensors
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取环境感知管理器状态
        
        Returns:
            状态字典
        """
        return {
            "sensors": {
                "total": len(self.sensors),
                "by_type": {t.value: len(ids) for t, ids in self.sensors_by_type.items()},
                "by_location": {loc: len(ids) for loc, ids in self.sensors_by_location.items()}
            },
            "readings": {
                "total": self.stats["total_readings"],
                "latest_timestamp": max([r.timestamp for r in self.latest_readings.values()]) if self.latest_readings else None
            },
            "alerts": {
                "active": len(self.alerts),
                "total": self.stats["alerts_triggered"]
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭环境感知管理器"""
        logger.info("Shutting down EnvironmentSensing...")
        
        self._stop_sampling.set()
        
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2)
        
        self.sensors.clear()
        self.readings.clear()
        self.latest_readings.clear()
        self.alerts.clear()
        self.sensors_by_location.clear()
        self.sensors_by_type.clear()
        
        logger.info("EnvironmentSensing shutdown completed")

# 单例模式实现
_environment_sensing_instance: Optional[EnvironmentSensing] = None

def get_environment_sensing(config: Optional[EnvironmentConfig] = None) -> EnvironmentSensing:
    """
    获取环境感知管理器单例
    
    Args:
        config: 环境感知配置
    
    Returns:
        环境感知管理器实例
    """
    global _environment_sensing_instance
    if _environment_sensing_instance is None:
        _environment_sensing_instance = EnvironmentSensing(config)
    return _environment_sensing_instance

