"""
传感器数据模块 - Mirexs移动设备集成

提供移动设备传感器数据获取功能，包括：
1. 加速度计
2. 陀螺仪
3. 磁力计
4. 光线传感器
5. 接近传感器
6. 压力传感器
7. 温度传感器
8. 湿度传感器
9. 步数计数器
10. 心率传感器
"""

import logging
import time
import math
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

class SensorDataType(Enum):
    """传感器数据类型枚举"""
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    GRAVITY = "gravity"
    LINEAR_ACCELERATION = "linear_acceleration"
    ROTATION_VECTOR = "rotation_vector"
    LIGHT = "light"
    PROXIMITY = "proximity"
    PRESSURE = "pressure"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    STEP_COUNTER = "step_counter"
    STEP_DETECTOR = "step_detector"
    HEART_RATE = "heart_rate"
    ORIENTATION = "orientation"
    SIGNIFICANT_MOTION = "significant_motion"

class SensorAccuracy(Enum):
    """传感器精度枚举"""
    UNRELIABLE = "unreliable"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class SensorReading:
    """传感器读数"""
    type: SensorDataType
    values: List[float]
    accuracy: SensorAccuracy
    timestamp: float = field(default_factory=time.time)
    sensor_name: Optional[str] = None
    vendor: Optional[str] = None
    
    def magnitude(self) -> float:
        """计算向量大小"""
        return math.sqrt(sum(v * v for v in self.values))

@dataclass
class SensorInfo:
    """传感器信息"""
    type: SensorDataType
    name: str
    vendor: str
    version: int
    resolution: float
    max_range: float
    min_delay: int  # 微秒
    power_consumption: float  # 毫安
    present: bool = True

@dataclass
class SensorConfig:
    """传感器配置"""
    # 采样配置
    sampling_rate: int = 50  # 赫兹
    batch_size: int = 100
    max_history: int = 1000
    
    # 传感器启用
    enable_accelerometer: bool = True
    enable_gyroscope: bool = True
    enable_magnetometer: bool = True
    enable_light: bool = True
    enable_proximity: bool = True
    enable_pressure: bool = False
    enable_temperature: bool = False
    enable_humidity: bool = False
    enable_step_counter: bool = True
    enable_heart_rate: bool = False
    
    # 运动检测
    motion_threshold: float = 1.5
    step_threshold: float = 12.0
    
    # 功耗优化
    adaptive_sampling: bool = True
    low_power_when_inactive: bool = True
    inactivity_timeout: int = 30  # 秒
    
    # 回调配置
    report_interval: int = 100  # 毫秒，0表示实时

class SensorManager:
    """
    传感器管理器
    
    负责移动设备传感器的数据获取和管理。
    """
    
    def __init__(self, config: Optional[SensorConfig] = None):
        """
        初始化传感器管理器
        
        Args:
            config: 传感器配置
        """
        self.config = config or SensorConfig()
        
        # 传感器信息
        self.available_sensors: Dict[SensorDataType, SensorInfo] = {}
        self.active_sensors: Dict[SensorDataType, bool] = {}
        
        # 传感器数据
        self.sensor_data: Dict[SensorDataType, deque] = {}
        self.latest_readings: Dict[SensorDataType, SensorReading] = {}
        
        # 运动状态
        self.is_moving = False
        self.last_motion_time = time.time()
        self.step_count = 0
        
        # 采样线程
        self._sampling_thread: Optional[threading.Thread] = None
        self._stop_sampling = threading.Event()
        
        # 回调函数
        self._listeners: Dict[SensorDataType, List[Callable[[SensorReading], None]]] = {}
        self.on_motion_detected: Optional[Callable[[bool], None]] = None
        self.on_step_detected: Optional[Callable[[int], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "readings_collected": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
        # 检测可用传感器
        self._detect_sensors()
        
        logger.info("SensorManager initialized")
    
    def _detect_sensors(self):
        """检测可用传感器"""
        # 模拟传感器检测
        # 实际实现中会通过原生代码获取真实传感器列表
        
        sensor_info = {
            SensorDataType.ACCELEROMETER: SensorInfo(
                type=SensorDataType.ACCELEROMETER,
                name="Accelerometer",
                vendor="Mirexs",
                version=1,
                resolution=0.01,
                max_range=20.0,
                min_delay=5000,
                power_consumption=0.5
            ),
            SensorDataType.GYROSCOPE: SensorInfo(
                type=SensorDataType.GYROSCOPE,
                name="Gyroscope",
                vendor="Mirexs",
                version=1,
                resolution=0.001,
                max_range=2000.0,
                min_delay=5000,
                power_consumption=0.6
            ),
            SensorDataType.MAGNETOMETER: SensorInfo(
                type=SensorDataType.MAGNETOMETER,
                name="Magnetometer",
                vendor="Mirexs",
                version=1,
                resolution=0.1,
                max_range=1000.0,
                min_delay=10000,
                power_consumption=0.4
            ),
            SensorDataType.LIGHT: SensorInfo(
                type=SensorDataType.LIGHT,
                name="Light Sensor",
                vendor="Mirexs",
                version=1,
                resolution=0.5,
                max_range=40000.0,
                min_delay=100000,
                power_consumption=0.1
            ),
            SensorDataType.PROXIMITY: SensorInfo(
                type=SensorDataType.PROXIMITY,
                name="Proximity",
                vendor="Mirexs",
                version=1,
                resolution=1.0,
                max_range=10.0,
                min_delay=100000,
                power_consumption=0.1
            ),
            SensorDataType.PRESSURE: SensorInfo(
                type=SensorDataType.PRESSURE,
                name="Barometer",
                vendor="Mirexs",
                version=1,
                resolution=0.01,
                max_range=1100.0,
                min_delay=100000,
                power_consumption=0.2
            ),
            SensorDataType.TEMPERATURE: SensorInfo(
                type=SensorDataType.TEMPERATURE,
                name="Temperature",
                vendor="Mirexs",
                version=1,
                resolution=0.1,
                max_range=100.0,
                min_delay=500000,
                power_consumption=0.2
            ),
            SensorDataType.HUMIDITY: SensorInfo(
                type=SensorDataType.HUMIDITY,
                name="Humidity",
                vendor="Mirexs",
                version=1,
                resolution=0.5,
                max_range=100.0,
                min_delay=500000,
                power_consumption=0.2
            ),
            SensorDataType.STEP_COUNTER: SensorInfo(
                type=SensorDataType.STEP_COUNTER,
                name="Step Counter",
                vendor="Mirexs",
                version=1,
                resolution=1.0,
                max_range=1000000.0,
                min_delay=0,
                power_consumption=0.1
            ),
            SensorDataType.HEART_RATE: SensorInfo(
                type=SensorDataType.HEART_RATE,
                name="Heart Rate",
                vendor="Mirexs",
                version=1,
                resolution=1.0,
                max_range=200.0,
                min_delay=100000,
                power_consumption=0.8
            )
        }
        
        # 根据配置启用传感器
        sensor_config_map = {
            SensorDataType.ACCELEROMETER: self.config.enable_accelerometer,
            SensorDataType.GYROSCOPE: self.config.enable_gyroscope,
            SensorDataType.MAGNETOMETER: self.config.enable_magnetometer,
            SensorDataType.LIGHT: self.config.enable_light,
            SensorDataType.PROXIMITY: self.config.enable_proximity,
            SensorDataType.PRESSURE: self.config.enable_pressure,
            SensorDataType.TEMPERATURE: self.config.enable_temperature,
            SensorDataType.HUMIDITY: self.config.enable_humidity,
            SensorDataType.STEP_COUNTER: self.config.enable_step_counter,
            SensorDataType.HEART_RATE: self.config.enable_heart_rate
        }
        
        for sensor_type, enabled in sensor_config_map.items():
            if enabled and sensor_type in sensor_info:
                self.available_sensors[sensor_type] = sensor_info[sensor_type]
                self.sensor_data[sensor_type] = deque(maxlen=self.config.max_history)
                self.active_sensors[sensor_type] = False
        
        logger.info(f"Detected {len(self.available_sensors)} sensors")
    
    def start_sampling(self):
        """开始采样"""
        if self._sampling_thread and self._sampling_thread.is_alive():
            logger.warning("Sampling already started")
            return
        
        self._stop_sampling.clear()
        
        def sampling_loop():
            interval = 1.0 / self.config.sampling_rate
            
            while not self._stop_sampling.is_set():
                try:
                    self._sample_all_sensors()
                    self._stop_sampling.wait(interval)
                except Exception as e:
                    logger.error(f"Sampling error: {e}")
                    self.stats["errors"] += 1
        
        self._sampling_thread = threading.Thread(target=sampling_loop, daemon=True)
        self._sampling_thread.start()
        
        logger.info(f"Sensor sampling started at {self.config.sampling_rate}Hz")
    
    def stop_sampling(self):
        """停止采样"""
        self._stop_sampling.set()
        if self._sampling_thread and self._sampling_thread.is_alive():
            self._sampling_thread.join(timeout=2)
        
        logger.info("Sensor sampling stopped")
    
    def _sample_all_sensors(self):
        """采样所有启用的传感器"""
        for sensor_type in self.active_sensors:
            if self.active_sensors[sensor_type]:
                reading = self._read_sensor(sensor_type)
                if reading:
                    self._process_reading(reading)
    
    def _read_sensor(self, sensor_type: SensorDataType) -> Optional[SensorReading]:
        """读取传感器数据"""
        # 实际实现中会通过原生代码获取真实传感器数据
        # 这里返回模拟数据
        
        import random
        
        if sensor_type == SensorDataType.ACCELEROMETER:
            values = [
                random.uniform(-2, 2),
                random.uniform(-2, 2),
                random.uniform(9, 11)  # 重力加速度
            ]
            accuracy = SensorAccuracy.HIGH
        
        elif sensor_type == SensorDataType.GYROSCOPE:
            values = [
                random.uniform(-10, 10),
                random.uniform(-10, 10),
                random.uniform(-10, 10)
            ]
            accuracy = SensorAccuracy.MEDIUM
        
        elif sensor_type == SensorDataType.MAGNETOMETER:
            values = [
                random.uniform(-50, 50),
                random.uniform(-50, 50),
                random.uniform(-50, 50)
            ]
            accuracy = SensorAccuracy.MEDIUM
        
        elif sensor_type == SensorDataType.LIGHT:
            values = [random.uniform(0, 1000)]
            accuracy = SensorAccuracy.HIGH
        
        elif sensor_type == SensorDataType.PROXIMITY:
            values = [random.uniform(0, 5)]
            accuracy = SensorAccuracy.HIGH
        
        elif sensor_type == SensorDataType.PRESSURE:
            values = [random.uniform(980, 1020)]
            accuracy = SensorAccuracy.MEDIUM
        
        elif sensor_type == SensorDataType.TEMPERATURE:
            values = [random.uniform(20, 30)]
            accuracy = SensorAccuracy.MEDIUM
        
        elif sensor_type == SensorDataType.HUMIDITY:
            values = [random.uniform(30, 70)]
            accuracy = SensorAccuracy.MEDIUM
        
        elif sensor_type == SensorDataType.STEP_COUNTER:
            # 步数计数器是累积的
            if self.step_count == 0:
                self.step_count = random.randint(0, 100)
            else:
                self.step_count += random.randint(0, 2)
            values = [self.step_count]
            accuracy = SensorAccuracy.HIGH
        
        elif sensor_type == SensorDataType.HEART_RATE:
            values = [random.uniform(60, 80)]
            accuracy = SensorAccuracy.MEDIUM
        
        else:
            return None
        
        sensor_info = self.available_sensors.get(sensor_type)
        
        return SensorReading(
            type=sensor_type,
            values=values,
            accuracy=accuracy,
            sensor_name=sensor_info.name if sensor_info else None,
            vendor=sensor_info.vendor if sensor_info else None
        )
    
    def _process_reading(self, reading: SensorReading):
        """处理传感器读数"""
        # 存储数据
        self.sensor_data[reading.type].append(reading)
        self.latest_readings[reading.type] = reading
        self.stats["readings_collected"] += 1
        
        # 运动检测
        if reading.type == SensorDataType.ACCELEROMETER:
            self._detect_motion(reading)
        
        # 步数检测
        if reading.type == SensorDataType.STEP_COUNTER:
            self._detect_step(reading)
        
        # 通知监听器
        if reading.type in self._listeners:
            for listener in self._listeners[reading.type]:
                try:
                    listener(reading)
                except Exception as e:
                    logger.error(f"Error in sensor listener: {e}")
    
    def _detect_motion(self, reading: SensorReading):
        """检测运动状态"""
        magnitude = reading.magnitude()
        moving = abs(magnitude - 9.8) > self.config.motion_threshold
        
        if moving != self.is_moving:
            self.is_moving = moving
            self.last_motion_time = time.time()
            
            if self.on_motion_detected:
                self.on_motion_detected(moving)
            
            logger.debug(f"Motion state changed: {moving}")
    
    def _detect_step(self, reading: SensorReading):
        """检测步数"""
        # 步数计数器传感器直接提供累积值
        if reading.type == SensorDataType.STEP_COUNTER:
            current_steps = int(reading.values[0])
            
            if current_steps > self.step_count:
                self.step_count = current_steps
                if self.on_step_detected:
                    self.on_step_detected(self.step_count)
                logger.debug(f"Step count updated: {self.step_count}")
    
    def enable_sensor(self, sensor_type: SensorDataType, enable: bool = True):
        """
        启用或禁用传感器
        
        Args:
            sensor_type: 传感器类型
            enable: 是否启用
        """
        if sensor_type not in self.available_sensors:
            logger.warning(f"Sensor {sensor_type.value} not available")
            return
        
        self.active_sensors[sensor_type] = enable
        logger.info(f"Sensor {sensor_type.value} {'enabled' if enable else 'disabled'}")
    
    def get_latest_reading(self, sensor_type: SensorDataType) -> Optional[SensorReading]:
        """
        获取最新读数
        
        Args:
            sensor_type: 传感器类型
        
        Returns:
            最新读数
        """
        return self.latest_readings.get(sensor_type)
    
    def get_reading_history(self, sensor_type: SensorDataType, 
                           count: Optional[int] = None) -> List[SensorReading]:
        """
        获取读数历史
        
        Args:
            sensor_type: 传感器类型
            count: 返回数量
        
        Returns:
            读数列表
        """
        if sensor_type not in self.sensor_data:
            return []
        
        data = list(self.sensor_data[sensor_type])
        if count:
            return data[-count:]
        return data
    
    def get_sensor_info(self, sensor_type: SensorDataType) -> Optional[SensorInfo]:
        """
        获取传感器信息
        
        Args:
            sensor_type: 传感器类型
        
        Returns:
            传感器信息
        """
        return self.available_sensors.get(sensor_type)
    
    def get_available_sensors(self) -> List[SensorDataType]:
        """
        获取可用传感器列表
        
        Returns:
            传感器类型列表
        """
        return list(self.available_sensors.keys())
    
    def get_active_sensors(self) -> List[SensorDataType]:
        """
        获取活动传感器列表
        
        Returns:
            传感器类型列表
        """
        return [s for s, active in self.active_sensors.items() if active]
    
    def register_listener(self, sensor_type: SensorDataType, 
                         listener: Callable[[SensorReading], None]):
        """
        注册传感器监听器
        
        Args:
            sensor_type: 传感器类型
            listener: 监听函数
        """
        if sensor_type not in self._listeners:
            self._listeners[sensor_type] = []
        self._listeners[sensor_type].append(listener)
    
    def unregister_listener(self, sensor_type: SensorDataType,
                           listener: Callable[[SensorReading], None]):
        """
        注销传感器监听器
        
        Args:
            sensor_type: 传感器类型
            listener: 监听函数
        """
        if sensor_type in self._listeners and listener in self._listeners[sensor_type]:
            self._listeners[sensor_type].remove(listener)
    
    def is_device_moving(self) -> bool:
        """设备是否在运动"""
        return self.is_moving
    
    def get_step_count(self) -> int:
        """获取步数"""
        return self.step_count
    
    def reset_step_count(self):
        """重置步数"""
        self.step_count = 0
        logger.info("Step count reset")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取传感器管理器状态
        
        Returns:
            状态字典
        """
        return {
            "available_sensors": [s.value for s in self.available_sensors.keys()],
            "active_sensors": [s.value for s in self.get_active_sensors()],
            "is_sampling": self._sampling_thread is not None and self._sampling_thread.is_alive(),
            "sampling_rate": self.config.sampling_rate,
            "is_moving": self.is_moving,
            "step_count": self.step_count,
            "stats": self.stats,
            "data_points": sum(len(d) for d in self.sensor_data.values())
        }
    
    def shutdown(self):
        """关闭传感器管理器"""
        logger.info("Shutting down SensorManager...")
        
        self.stop_sampling()
        
        self.available_sensors.clear()
        self.active_sensors.clear()
        self.sensor_data.clear()
        self.latest_readings.clear()
        self._listeners.clear()
        
        logger.info("SensorManager shutdown completed")

# 单例模式实现
_sensor_manager_instance: Optional[SensorManager] = None

def get_sensor_manager(config: Optional[SensorConfig] = None) -> SensorManager:
    """
    获取传感器管理器单例
    
    Args:
        config: 传感器配置
    
    Returns:
        传感器管理器实例
    """
    global _sensor_manager_instance
    if _sensor_manager_instance is None:
        _sensor_manager_instance = SensorManager(config)
    return _sensor_manager_instance

