"""
移动传感器模块 - Mirexs移动应用程序

提供移动设备传感器集成功能，包括：
1. 加速度计
2. 陀螺仪
3. 磁力计
4. 光传感器
5. 接近传感器
6. 步数计数器
7. 指纹传感器
8. 传感器数据融合
"""

import logging
import time
import math
import threading
from typing import Optional, Dict, Any, List, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

class SensorType(Enum):
    """传感器类型枚举"""
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
    FINGERPRINT = "fingerprint"
    FACE_ID = "face_id"
    IRIS = "iris"

class SensorAccuracy(Enum):
    """传感器精度枚举"""
    UNRELIABLE = "unreliable"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class SensorData:
    """传感器数据"""
    type: SensorType
    values: List[float]
    accuracy: SensorAccuracy
    timestamp: float = field(default_factory=time.time)
    
    # 融合数据
    fused_values: Optional[List[float]] = None
    
    def magnitude(self) -> float:
        """计算向量大小"""
        return math.sqrt(sum(v * v for v in self.values))

@dataclass
class SensorInfo:
    """传感器信息"""
    type: SensorType
    name: str
    vendor: str
    version: int
    resolution: float
    max_range: float
    power_consumption: float  # 毫瓦
    min_delay: int  # 微秒
    max_delay: int  # 微秒

@dataclass
class MobileSensorsConfig:
    """移动传感器配置"""
    # 采样配置
    sampling_rate: int = 50  # 赫兹
    max_history: int = 1000  # 每个传感器保留的最大历史数据点
    
    # 传感器启用
    enable_accelerometer: bool = True
    enable_gyroscope: bool = True
    enable_magnetometer: bool = True
    enable_light: bool = True
    enable_proximity: bool = True
    enable_step_counter: bool = True
    enable_biometric: bool = True
    
    # 数据融合
    enable_sensor_fusion: bool = True
    fusion_interval: int = 10  # 每10个采样融合一次
    
    # 功耗优化
    adaptive_sampling: bool = True
    low_power_when_inactive: bool = True
    inactivity_timeout: int = 60  # 秒

class SensorFusion:
    """
    传感器数据融合器
    
    融合多个传感器的数据，提供更准确的信息：
    - 加速度计 + 陀螺仪 + 磁力计 -> 方向
    - 加速度计 -> 运动检测
    - 步数检测
    """
    
    def __init__(self):
        self.accelerometer_data: deque = deque(maxlen=10)
        self.gyroscope_data: deque = deque(maxlen=10)
        self.magnetometer_data: deque = deque(maxlen=10)
        
        # 融合结果
        self.orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 滚转、俯仰、偏航
        self.linear_acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.gravity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        
        # 滤波器参数
        self.alpha = 0.98  # 互补滤波器系数
    
    def add_accelerometer(self, data: SensorData):
        """添加加速度计数据"""
        self.accelerometer_data.append(data)
    
    def add_gyroscope(self, data: SensorData):
        """添加陀螺仪数据"""
        self.gyroscope_data.append(data)
    
    def add_magnetometer(self, data: SensorData):
        """添加磁力计数据"""
        self.magnetometer_data.append(data)
    
    def update(self) -> Dict[str, Any]:
        """
        更新融合数据
        
        Returns:
            融合结果
        """
        if len(self.accelerometer_data) < 1:
            return {}
        
        # 获取最新数据
        accel = self.accelerometer_data[-1]
        
        # 计算重力方向
        self.gravity = self._compute_gravity(accel)
        
        # 计算线性加速度
        self.linear_acceleration = self._compute_linear_acceleration(accel)
        
        # 如果有陀螺仪数据，计算方向
        if len(self.gyroscope_data) > 0 and len(self.magnetometer_data) > 0:
            gyro = self.gyroscope_data[-1]
            mag = self.magnetometer_data[-1]
            self.orientation = self._compute_orientation(accel, gyro, mag)
        
        return {
            "orientation": self.orientation,
            "linear_acceleration": self.linear_acceleration,
            "gravity": self.gravity
        }
    
    def _compute_gravity(self, accel: SensorData) -> Tuple[float, float, float]:
        """计算重力方向"""
        # 使用低通滤波器提取重力
        if len(self.accelerometer_data) < 2:
            return (accel.values[0], accel.values[1], accel.values[2])
        
        prev = self.accelerometer_data[-2]
        gravity_x = self.alpha * prev.values[0] + (1 - self.alpha) * accel.values[0]
        gravity_y = self.alpha * prev.values[1] + (1 - self.alpha) * accel.values[1]
        gravity_z = self.alpha * prev.values[2] + (1 - self.alpha) * accel.values[2]
        
        return (gravity_x, gravity_y, gravity_z)
    
    def _compute_linear_acceleration(self, accel: SensorData) -> Tuple[float, float, float]:
        """计算线性加速度（去除重力）"""
        return (
            accel.values[0] - self.gravity[0],
            accel.values[1] - self.gravity[1],
            accel.values[2] - self.gravity[2]
        )
    
    def _compute_orientation(self, accel: SensorData, gyro: SensorData, 
                            mag: SensorData) -> Tuple[float, float, float]:
        """计算设备方向"""
        # 简化实现，实际应该使用旋转矩阵和四元数
        # 这里只返回模拟值
        return (0.0, 0.0, 0.0)

class MobileSensors:
    """
    移动传感器管理器
    
    负责管理所有移动设备传感器，包括：
    - 传感器初始化和管理
    - 数据采集和滤波
    - 传感器数据融合
    - 运动检测
    - 生物识别
    """
    
    def __init__(self, config: Optional[MobileSensorsConfig] = None):
        """
        初始化移动传感器管理器
        
        Args:
            config: 传感器配置
        """
        self.config = config or MobileSensorsConfig()
        
        # 传感器列表
        self.available_sensors: Dict[SensorType, SensorInfo] = {}
        self.active_sensors: Dict[SensorType, bool] = {}
        
        # 传感器数据
        self.sensor_data: Dict[SensorType, deque] = {}
        self.last_data_time: Dict[SensorType, float] = {}
        
        # 数据融合
        self.fusion = SensorFusion() if self.config.enable_sensor_fusion else None
        
        # 运动检测
        self.is_moving = False
        self.motion_threshold = 1.5  # 运动阈值
        self.last_motion_time = time.time()
        
        # 步数统计
        self.step_count = 0
        self.last_step_time = 0
        self.step_threshold = 2.0  # 步数检测阈值
        
        # 生物识别
        self.biometric_available = False
        self.biometric_enrolled = False
        
        # 采样控制
        self.is_sampling = False
        self.sampling_thread: Optional[threading.Thread] = None
        self.stop_sampling = threading.Event()
        
        # 监听器
        self._sensor_listeners: Dict[SensorType, List[Callable[[SensorData], None]]] = {}
        
        # 检测可用传感器
        self._detect_sensors()
        
        logger.info("MobileSensors initialized")
    
    def _detect_sensors(self):
        """检测可用传感器（从原生平台获取）"""
        # 这里应该从原生代码获取真实的传感器列表
        # 简化实现，假设所有传感器都可用
        
        sensor_info = {
            SensorType.ACCELEROMETER: SensorInfo(
                type=SensorType.ACCELEROMETER,
                name="Accelerometer",
                vendor="Mirexs",
                version=1,
                resolution=0.01,
                max_range=20.0,
                power_consumption=5.0,
                min_delay=10000,
                max_delay=200000
            ),
            SensorType.GYROSCOPE: SensorInfo(
                type=SensorType.GYROSCOPE,
                name="Gyroscope",
                vendor="Mirexs",
                version=1,
                resolution=0.001,
                max_range=2000.0,
                power_consumption=6.0,
                min_delay=10000,
                max_delay=200000
            ),
            SensorType.MAGNETOMETER: SensorInfo(
                type=SensorType.MAGNETOMETER,
                name="Magnetometer",
                vendor="Mirexs",
                version=1,
                resolution=0.01,
                max_range=1000.0,
                power_consumption=4.0,
                min_delay=10000,
                max_delay=200000
            ),
            SensorType.LIGHT: SensorInfo(
                type=SensorType.LIGHT,
                name="Light Sensor",
                vendor="Mirexs",
                version=1,
                resolution=0.1,
                max_range=40000.0,
                power_consumption=0.5,
                min_delay=100000,
                max_delay=1000000
            ),
            SensorType.PROXIMITY: SensorInfo(
                type=SensorType.PROXIMITY,
                name="Proximity",
                vendor="Mirexs",
                version=1,
                resolution=1.0,
                max_range=10.0,
                power_consumption=0.5,
                min_delay=100000,
                max_delay=1000000
            )
        }
        
        # 根据配置启用
        if self.config.enable_accelerometer:
            self.available_sensors[SensorType.ACCELEROMETER] = sensor_info[SensorType.ACCELEROMETER]
            self.sensor_data[SensorType.ACCELEROMETER] = deque(maxlen=self.config.max_history)
        
        if self.config.enable_gyroscope:
            self.available_sensors[SensorType.GYROSCOPE] = sensor_info[SensorType.GYROSCOPE]
            self.sensor_data[SensorType.GYROSCOPE] = deque(maxlen=self.config.max_history)
        
        if self.config.enable_magnetometer:
            self.available_sensors[SensorType.MAGNETOMETER] = sensor_info[SensorType.MAGNETOMETER]
            self.sensor_data[SensorType.MAGNETOMETER] = deque(maxlen=self.config.max_history)
        
        if self.config.enable_light:
            self.available_sensors[SensorType.LIGHT] = sensor_info[SensorType.LIGHT]
            self.sensor_data[SensorType.LIGHT] = deque(maxlen=self.config.max_history)
        
        if self.config.enable_proximity:
            self.available_sensors[SensorType.PROXIMITY] = sensor_info[SensorType.PROXIMITY]
            self.sensor_data[SensorType.PROXIMITY] = deque(maxlen=self.config.max_history)
        
        logger.info(f"Detected {len(self.available_sensors)} sensors")
    
    def start_sampling(self):
        """开始传感器数据采样"""
        if self.is_sampling:
            logger.warning("Sampling already started")
            return
        
        self.is_sampling = True
        self.stop_sampling.clear()
        
        def sample():
            interval = 1.0 / self.config.sampling_rate
            fusion_counter = 0
            
            while not self.stop_sampling.is_set():
                try:
                    # 采集所有活动传感器的数据
                    for sensor_type in self.active_sensors:
                        if self.active_sensors[sensor_type]:
                            data = self._read_sensor(sensor_type)
                            if data:
                                self._process_sensor_data(data)
                    
                    # 传感器融合
                    if self.fusion and fusion_counter % self.config.fusion_interval == 0:
                        fused = self.fusion.update()
                        if fused:
                            self._process_fusion_data(fused)
                    
                    fusion_counter += 1
                    
                except Exception as e:
                    logger.error(f"Error in sensor sampling: {e}")
                
                self.stop_sampling.wait(interval)
        
        self.sampling_thread = threading.Thread(target=sample, daemon=True)
        self.sampling_thread.start()
        
        logger.info(f"Sensor sampling started at {self.config.sampling_rate}Hz")
    
    def stop_sampling(self):
        """停止传感器数据采样"""
        self.stop_sampling.set()
        if self.sampling_thread and self.sampling_thread.is_alive():
            self.sampling_thread.join(timeout=2)
        
        self.is_sampling = False
        logger.info("Sensor sampling stopped")
    
    def _read_sensor(self, sensor_type: SensorType) -> Optional[SensorData]:
        """读取传感器数据（从原生平台获取）"""
        # 这里应该从原生代码获取真实的传感器数据
        # 简化实现，生成模拟数据
        import random
        
        if sensor_type == SensorType.ACCELEROMETER:
            values = [random.uniform(-2, 2), random.uniform(-2, 2), random.uniform(9, 11)]
            accuracy = SensorAccuracy.HIGH
        elif sensor_type == SensorType.GYROSCOPE:
            values = [random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-10, 10)]
            accuracy = SensorAccuracy.MEDIUM
        elif sensor_type == SensorType.MAGNETOMETER:
            values = [random.uniform(-50, 50), random.uniform(-50, 50), random.uniform(-50, 50)]
            accuracy = SensorAccuracy.MEDIUM
        elif sensor_type == SensorType.LIGHT:
            values = [random.uniform(0, 1000)]
            accuracy = SensorAccuracy.HIGH
        elif sensor_type == SensorType.PROXIMITY:
            values = [random.uniform(0, 5)]
            accuracy = SensorAccuracy.HIGH
        else:
            return None
        
        return SensorData(
            type=sensor_type,
            values=values,
            accuracy=accuracy,
            timestamp=time.time()
        )
    
    def _process_sensor_data(self, data: SensorData):
        """处理传感器数据"""
        # 存储数据
        if data.type in self.sensor_data:
            self.sensor_data[data.type].append(data)
            self.last_data_time[data.type] = data.timestamp
        
        # 添加到融合器
        if self.fusion:
            if data.type == SensorType.ACCELEROMETER:
                self.fusion.add_accelerometer(data)
            elif data.type == SensorType.GYROSCOPE:
                self.fusion.add_gyroscope(data)
            elif data.type == SensorType.MAGNETOMETER:
                self.fusion.add_magnetometer(data)
        
        # 运动检测
        self._detect_motion(data)
        
        # 步数检测
        if data.type == SensorType.ACCELEROMETER:
            self._detect_step(data)
        
        # 通知监听器
        if data.type in self._sensor_listeners:
            for listener in self._sensor_listeners[data.type]:
                try:
                    listener(data)
                except Exception as e:
                    logger.error(f"Error in sensor listener: {e}")
    
    def _process_fusion_data(self, fused: Dict[str, Any]):
        """处理融合数据"""
        # 可以触发融合数据相关的事件
        pass
    
    def _detect_motion(self, data: SensorData):
        """检测设备是否在运动"""
        if data.type != SensorType.ACCELEROMETER:
            return
        
        magnitude = data.magnitude()
        moving = abs(magnitude - 9.8) > self.motion_threshold
        
        if moving != self.is_moving:
            self.is_moving = moving
            self.last_motion_time = time.time()
            logger.debug(f"Motion state changed: {moving}")
    
    def _detect_step(self, data: SensorData):
        """检测步数"""
        # 简化步数检测算法
        magnitude = data.magnitude()
        
        if magnitude > 12.0:  # 步数峰值检测
            current_time = data.timestamp
            if current_time - self.last_step_time > self.step_threshold:
                self.step_count += 1
                self.last_step_time = current_time
                logger.debug(f"Step detected: {self.step_count}")
    
    def enable_sensor(self, sensor_type: SensorType, enable: bool = True):
        """
        启用或禁用传感器
        
        Args:
            sensor_type: 传感器类型
            enable: 是否启用
        """
        if sensor_type not in self.available_sensors:
            logger.warning(f"Sensor not available: {sensor_type.value}")
            return
        
        self.active_sensors[sensor_type] = enable
        
        if enable:
            logger.info(f"Sensor enabled: {sensor_type.value}")
        else:
            logger.info(f"Sensor disabled: {sensor_type.value}")
    
    def get_sensor_data(self, sensor_type: SensorType, count: int = 1) -> List[SensorData]:
        """
        获取传感器数据
        
        Args:
            sensor_type: 传感器类型
            count: 返回的数据点数量
        
        Returns:
            传感器数据列表
        """
        if sensor_type not in self.sensor_data:
            return []
        
        data = list(self.sensor_data[sensor_type])
        return data[-count:]
    
    def get_latest_data(self, sensor_type: SensorType) -> Optional[SensorData]:
        """
        获取最新的传感器数据
        
        Args:
            sensor_type: 传感器类型
        
        Returns:
            最新的传感器数据
        """
        data = self.get_sensor_data(sensor_type, 1)
        return data[0] if data else None
    
    def get_fused_orientation(self) -> Tuple[float, float, float]:
        """
        获取融合后的设备方向
        
        Returns:
            (滚转, 俯仰, 偏航) 角度
        """
        if self.fusion:
            return self.fusion.orientation
        return (0.0, 0.0, 0.0)
    
    def get_linear_acceleration(self) -> Tuple[float, float, float]:
        """
        获取线性加速度（去除重力）
        
        Returns:
            (x, y, z) 线性加速度
        """
        if self.fusion:
            return self.fusion.linear_acceleration
        return (0.0, 0.0, 0.0)
    
    def is_device_moving(self) -> bool:
        """
        设备是否在运动
        
        Returns:
            是否在运动
        """
        return self.is_moving
    
    def get_step_count(self) -> int:
        """
        获取步数计数
        
        Returns:
            步数
        """
        return self.step_count
    
    def reset_step_count(self):
        """重置步数计数"""
        self.step_count = 0
        logger.info("Step count reset")
    
    def authenticate_biometric(self, reason: str) -> bool:
        """
        进行生物识别认证
        
        Args:
            reason: 认证原因
        
        Returns:
            是否认证成功
        """
        if not self.config.enable_biometric:
            logger.warning("Biometric authentication is disabled")
            return False
        
        logger.info(f"Biometric authentication requested: {reason}")
        
        # 这里应该调用原生生物识别API
        # 简化实现，假设总是成功
        return True
    
    def register_sensor_listener(self, sensor_type: SensorType, 
                                 listener: Callable[[SensorData], None]):
        """
        注册传感器监听器
        
        Args:
            sensor_type: 传感器类型
            listener: 监听函数
        """
        if sensor_type not in self._sensor_listeners:
            self._sensor_listeners[sensor_type] = []
        self._sensor_listeners[sensor_type].append(listener)
    
    def unregister_sensor_listener(self, sensor_type: SensorType,
                                   listener: Callable[[SensorData], None]):
        """
        注销传感器监听器
        
        Args:
            sensor_type: 传感器类型
            listener: 监听函数
        """
        if sensor_type in self._sensor_listeners and listener in self._sensor_listeners[sensor_type]:
            self._sensor_listeners[sensor_type].remove(listener)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取传感器管理器状态
        
        Returns:
            状态字典
        """
        return {
            "available_sensors": [s.value for s in self.available_sensors.keys()],
            "active_sensors": [s.value for s, a in self.active_sensors.items() if a],
            "is_sampling": self.is_sampling,
            "sampling_rate": self.config.sampling_rate,
            "is_moving": self.is_moving,
            "step_count": self.step_count,
            "sensor_data_sizes": {
                s.value: len(d) for s, d in self.sensor_data.items()
            },
            "fusion_enabled": self.config.enable_sensor_fusion,
            "biometric_available": self.biometric_available
        }
    
    def shutdown(self):
        """关闭传感器管理器"""
        logger.info("Shutting down MobileSensors...")
        
        self.stop_sampling()
        
        self.active_sensors.clear()
        self.sensor_data.clear()
        self._sensor_listeners.clear()
        
        logger.info("MobileSensors shutdown completed")

# 单例模式实现
_mobile_sensors_instance: Optional[MobileSensors] = None

def get_mobile_sensors(config: Optional[MobileSensorsConfig] = None) -> MobileSensors:
    """
    获取移动传感器管理器单例
    
    Args:
        config: 传感器配置
    
    Returns:
        移动传感器管理器实例
    """
    global _mobile_sensors_instance
    if _mobile_sensors_instance is None:
        _mobile_sensors_instance = MobileSensors(config)
    return _mobile_sensors_instance

