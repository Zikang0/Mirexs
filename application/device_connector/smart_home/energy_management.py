"""
能源管理模块 - Mirexs智能家居集成

提供能源管理功能，包括：
1. 电力监控
2. 能耗分析
3. 电价管理
4. 节能建议
5. 功率限制
6. 用电报告
"""

import logging
import time
import threading
import math
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class PowerSource(Enum):
    """电源类型枚举"""
    GRID = "grid"              # 市电
    SOLAR = "solar"            # 太阳能
    BATTERY = "battery"        # 电池
    GENERATOR = "generator"     # 发电机
    UNKNOWN = "unknown"

class EnergyPriceType(Enum):
    """电价类型枚举"""
    FIXED = "fixed"            # 固定电价
    TIERED = "tiered"          # 阶梯电价
    TIME_OF_USE = "time_of_use"  # 分时电价
    REAL_TIME = "real_time"    # 实时电价

@dataclass
class PowerMeter:
    """电表"""
    id: str
    name: str
    location: str
    current_power: float = 0.0  # 当前功率（瓦）
    voltage: float = 0.0        # 电压（伏）
    current: float = 0.0        # 电流（安）
    power_factor: float = 1.0    # 功率因数
    frequency: float = 50.0      # 频率（赫兹）
    total_energy: float = 0.0    # 总用电量（千瓦时）
    today_energy: float = 0.0    # 今日用电量
    month_energy: float = 0.0    # 本月用电量

@dataclass
class EnergyPrice:
    """电价"""
    type: EnergyPriceType
    price: float                # 当前价格（元/千瓦时）
    currency: str = "CNY"
    effective_from: float = 0.0
    effective_to: float = 0.0
    tiers: List[Dict[str, Any]] = field(default_factory=list)  # 阶梯电价
    schedule: List[Dict[str, Any]] = field(default_factory=list)  # 分时电价

@dataclass
class EnergyStats:
    """能源统计"""
    timestamp: float = field(default_factory=time.time)
    power: float = 0.0          # 当前功率
    energy_today: float = 0.0    # 今日用电
    energy_week: float = 0.0     # 本周用电
    energy_month: float = 0.0    # 本月用电
    energy_year: float = 0.0     # 今年用电
    cost_today: float = 0.0      # 今日电费
    cost_month: float = 0.0      # 本月电费
    cost_year: float = 0.0       # 今年电费
    peak_power: float = 0.0      # 峰值功率
    average_power: float = 0.0    # 平均功率
    carbon_footprint: float = 0.0  # 碳排放（千克）

@dataclass
class EnergySuggestion:
    """节能建议"""
    id: str
    title: str
    description: str
    potential_saving: float      # 潜在节省（千瓦时/月）
    difficulty: str              # easy, medium, hard
    category: str                # lighting, hvac, appliance, behavior
    actions: List[str] = field(default_factory=list)

@dataclass
class EnergyConfig:
    """能源管理配置"""
    # 监控配置
    monitor_interval: int = 10  # 秒
    history_retention: int = 2592000  # 30天
    
    # 电价配置
    price_type: EnergyPriceType = EnergyPriceType.FIXED
    base_price: float = 0.5  # 元/千瓦时
    currency: str = "CNY"
    
    # 功率限制
    power_limit: Optional[float] = None  # 瓦
    overload_alert: bool = True
    
    # 节能建议
    enable_suggestions: bool = True
    suggestion_interval: int = 86400  # 1天

class EnergyManagement:
    """
    能源管理器
    
    负责能源数据的监控、分析和优化。
    """
    
    def __init__(self, config: Optional[EnergyConfig] = None):
        """
        初始化能源管理器
        
        Args:
            config: 能源管理配置
        """
        self.config = config or EnergyConfig()
        
        # 电表
        self.meters: Dict[str, PowerMeter] = {}
        
        # 电价
        self.price = EnergyPrice(
            type=self.config.price_type,
            price=self.config.base_price,
            currency=self.config.currency
        )
        
        # 能源数据
        self.readings: Dict[str, List[EnergyStats]] = {}
        self.latest_stats: Optional[EnergyStats] = None
        
        # 节能建议
        self.suggestions: List[EnergySuggestion] = []
        self.last_suggestion_time: Optional[float] = None
        
        # 监控线程
        self._monitor_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()
        
        # 回调函数
        self.on_stats_updated: Optional[Callable[[EnergyStats], None]] = None
        self.on_power_limit_exceeded: Optional[Callable[[float, float], None]] = None
        self.on_price_changed: Optional[Callable[[float], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "total_energy": 0.0,
            "total_cost": 0.0,
            "peak_power": 0.0,
            "alerts": 0,
            "errors": 0
        }
        
        # 启动监控
        self._start_monitoring()
        
        logger.info("EnergyManagement initialized")
    
    def _start_monitoring(self):
        """启动监控"""
        def monitor_loop():
            while not self._stop_monitor.is_set():
                try:
                    self._update_stats()
                    self._check_power_limit()
                    self._stop_monitor.wait(self.config.monitor_interval)
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    self.stats["errors"] += 1
        
        def cleanup_loop():
            while not self._stop_monitor.is_set():
                try:
                    self._cleanup_old_data()
                    self._generate_suggestions()
                    self._stop_monitor.wait(3600)  # 每小时
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        logger.debug("Energy monitoring started")
    
    def _update_stats(self):
        """更新统计"""
        total_power = 0.0
        
        for meter in self.meters.values():
            total_power += meter.current_power
        
        # 创建统计对象
        stats = EnergyStats(
            power=total_power,
            energy_today=self._get_energy_for_period("day"),
            energy_week=self._get_energy_for_period("week"),
            energy_month=self._get_energy_for_period("month"),
            energy_year=self._get_energy_for_period("year"),
            cost_today=self._calculate_cost(self._get_energy_for_period("day")),
            cost_month=self._calculate_cost(self._get_energy_for_period("month")),
            cost_year=self._calculate_cost(self._get_energy_for_period("year")),
            peak_power=max(total_power, self.stats["peak_power"]),
            average_power=self._calculate_average_power(),
            carbon_footprint=total_power * 0.0005  # 简化的碳排放计算
        )
        
        self.latest_stats = stats
        
        # 存储历史
        meter_id = "total"
        if meter_id not in self.readings:
            self.readings[meter_id] = []
        self.readings[meter_id].append(stats)
        
        # 更新总统计
        self.stats["total_energy"] += stats.power * self.config.monitor_interval / 3600000  # 转换为千瓦时
        self.stats["total_cost"] += stats.cost_today
        self.stats["peak_power"] = max(self.stats["peak_power"], stats.power)
        
        logger.debug(f"Power: {stats.power:.2f}W, Today: {stats.energy_today:.2f}kWh")
        
        if self.on_stats_updated:
            self.on_stats_updated(stats)
    
    def _get_energy_for_period(self, period: str) -> float:
        """获取指定周期的用电量"""
        if not self.readings.get("total"):
            return 0.0
        
        now = time.time()
        total = 0.0
        
        if period == "day":
            cutoff = now - 86400
        elif period == "week":
            cutoff = now - 604800
        elif period == "month":
            cutoff = now - 2592000
        elif period == "year":
            cutoff = now - 31536000
        else:
            return 0.0
        
        for reading in self.readings["total"]:
            if reading.timestamp >= cutoff:
                # 功率 * 时间间隔 = 能量（需要转换）
                energy = reading.power * self.config.monitor_interval / 3600000
                total += energy
        
        return total
    
    def _calculate_average_power(self) -> float:
        """计算平均功率"""
        if not self.readings.get("total"):
            return 0.0
        
        readings = self.readings["total"][-100:]  # 最近100个读数
        if not readings:
            return 0.0
        
        total_power = sum(r.power for r in readings)
        return total_power / len(readings)
    
    def _calculate_cost(self, energy: float) -> float:
        """计算电费"""
        if self.price.type == EnergyPriceType.FIXED:
            return energy * self.price.price
        elif self.price.type == EnergyPriceType.TIERED:
            return self._calculate_tiered_cost(energy)
        elif self.price.type == EnergyPriceType.TIME_OF_USE:
            return self._calculate_tou_cost(energy)
        else:
            return energy * self.price.price
    
    def _calculate_tiered_cost(self, energy: float) -> float:
        """计算阶梯电价"""
        if not self.price.tiers:
            return energy * self.price.price
        
        remaining = energy
        cost = 0.0
        
        for tier in sorted(self.price.tiers, key=lambda x: x.get("threshold", 0)):
            threshold = tier.get("threshold", float('inf'))
            rate = tier.get("rate", self.price.price)
            
            if remaining <= 0:
                break
            
            if threshold == float('inf'):
                cost += remaining * rate
                remaining = 0
            else:
                tier_energy = min(remaining, threshold)
                cost += tier_energy * rate
                remaining -= tier_energy
        
        return cost
    
    def _calculate_tou_cost(self, energy: float) -> float:
        """计算分时电价"""
        # 简化实现
        return energy * self.price.price
    
    def _check_power_limit(self):
        """检查功率限制"""
        if not self.config.power_limit or not self.latest_stats:
            return
        
        if self.latest_stats.power > self.config.power_limit:
            self.stats["alerts"] += 1
            logger.warning(f"Power limit exceeded: {self.latest_stats.power:.2f}W > {self.config.power_limit}W")
            
            if self.on_power_limit_exceeded:
                self.on_power_limit_exceeded(self.latest_stats.power, self.config.power_limit)
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = time.time() - self.config.history_retention
        
        for meter_id in self.readings:
            self.readings[meter_id] = [
                r for r in self.readings[meter_id]
                if r.timestamp >= cutoff_time
            ]
    
    def _generate_suggestions(self):
        """生成节能建议"""
        if not self.config.enable_suggestions:
            return
        
        # 检查间隔
        if self.last_suggestion_time:
            if time.time() - self.last_suggestion_time < self.config.suggestion_interval:
                return
        
        self.suggestions.clear()
        
        # 添加一些基本建议
        suggestions = [
            EnergySuggestion(
                id="lighting_led",
                title="更换LED灯泡",
                description="将传统灯泡更换为LED灯泡可节省高达80%的照明用电",
                potential_saving=50,
                difficulty="easy",
                category="lighting",
                actions=["购买LED灯泡", "更换灯泡"]
            ),
            EnergySuggestion(
                id="standby_power",
                title="关闭待机设备",
                description="拔掉不使用的电器插头，减少待机功耗",
                potential_saving=30,
                difficulty="easy",
                category="behavior",
                actions=["拔掉充电器", "关闭电源插座"]
            ),
            EnergySuggestion(
                id="ac_temperature",
                title="调整空调温度",
                description="夏季空调温度设置在26℃，冬季设置在20℃",
                potential_saving=100,
                difficulty="easy",
                category="hvac",
                actions=["调整空调设定"]
            ),
            EnergySuggestion(
                id="energy_star",
                title="更换高能效设备",
                description="选择能效等级高的家电产品",
                potential_saving=200,
                difficulty="hard",
                category="appliance",
                actions=["查看能效标识", "计划更换旧设备"]
            )
        ]
        
        self.suggestions = suggestions
        self.last_suggestion_time = time.time()
        
        logger.info(f"Generated {len(suggestions)} energy saving suggestions")
    
    def register_meter(self, meter_id: str, name: str, location: str) -> bool:
        """
        注册电表
        
        Args:
            meter_id: 电表ID
            name: 电表名称
            location: 位置
        
        Returns:
            是否成功
        """
        if meter_id in self.meters:
            logger.warning(f"Meter {meter_id} already exists")
            return False
        
        meter = PowerMeter(
            id=meter_id,
            name=name,
            location=location
        )
        
        self.meters[meter_id] = meter
        self.readings[meter_id] = []
        
        logger.info(f"Meter registered: {name} ({meter_id}) at {location}")
        
        return True
    
    def update_meter_reading(self, meter_id: str, power: float, voltage: float = 0.0,
                            current: float = 0.0, power_factor: float = 1.0):
        """
        更新电表读数
        
        Args:
            meter_id: 电表ID
            power: 功率
            voltage: 电压
            current: 电流
            power_factor: 功率因数
        """
        if meter_id not in self.meters:
            logger.warning(f"Meter {meter_id} not found")
            return
        
        meter = self.meters[meter_id]
        meter.current_power = power
        meter.voltage = voltage
        meter.current = current
        meter.power_factor = power_factor
        
        # 更新累计用电量
        energy_delta = power * self.config.monitor_interval / 3600000  # 转换为千瓦时
        meter.total_energy += energy_delta
        meter.today_energy += energy_delta
        meter.month_energy += energy_delta
    
    def set_price(self, price_type: EnergyPriceType, price: float,
                 tiers: Optional[List[Dict[str, Any]]] = None,
                 schedule: Optional[List[Dict[str, Any]]] = None):
        """
        设置电价
        
        Args:
            price_type: 电价类型
            price: 基础价格
            tiers: 阶梯电价配置
            schedule: 分时电价配置
        """
        self.price.type = price_type
        self.price.price = price
        
        if tiers:
            self.price.tiers = tiers
        
        if schedule:
            self.price.schedule = schedule
        
        logger.info(f"Energy price updated: {price_type.value} - {price} {self.price.currency}/kWh")
        
        if self.on_price_changed:
            self.on_price_changed(price)
    
    def get_current_stats(self) -> Optional[EnergyStats]:
        """
        获取当前统计
        
        Returns:
            能源统计
        """
        return self.latest_stats
    
    def get_meter_stats(self, meter_id: str, hours: int = 24) -> List[EnergyStats]:
        """
        获取电表统计
        
        Args:
            meter_id: 电表ID
            hours: 小时数
        
        Returns:
            统计列表
        """
        if meter_id not in self.readings:
            return []
        
        cutoff_time = time.time() - hours * 3600
        readings = self.readings[meter_id]
        
        return [r for r in readings if r.timestamp >= cutoff_time]
    
    def get_suggestions(self) -> List[EnergySuggestion]:
        """
        获取节能建议
        
        Returns:
            建议列表
        """
        return self.suggestions
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取能源管理器状态
        
        Returns:
            状态字典
        """
        return {
            "meters": {
                "total": len(self.meters),
                "names": [m.name for m in self.meters.values()]
            },
            "current_stats": {
                "power": self.latest_stats.power if self.latest_stats else 0,
                "energy_today": self.latest_stats.energy_today if self.latest_stats else 0,
                "cost_today": self.latest_stats.cost_today if self.latest_stats else 0
            } if self.latest_stats else None,
            "price": {
                "type": self.price.type.value,
                "price": self.price.price,
                "currency": self.price.currency
            },
            "suggestions": len(self.suggestions),
            "stats": self.stats,
            "power_limit": self.config.power_limit
        }
    
    def shutdown(self):
        """关闭能源管理器"""
        logger.info("Shutting down EnergyManagement...")
        
        self._stop_monitor.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2)
        
        self.meters.clear()
        self.readings.clear()
        self.suggestions.clear()
        
        logger.info("EnergyManagement shutdown completed")

# 单例模式实现
_energy_management_instance: Optional[EnergyManagement] = None

def get_energy_management(config: Optional[EnergyConfig] = None) -> EnergyManagement:
    """
    获取能源管理器单例
    
    Args:
        config: 能源管理配置
    
    Returns:
        能源管理器实例
    """
    global _energy_management_instance
    if _energy_management_instance is None:
        _energy_management_instance = EnergyManagement(config)
    return _energy_management_instance

