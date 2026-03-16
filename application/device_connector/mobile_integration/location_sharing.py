"""
位置共享模块 - Mirexs移动设备集成

提供位置信息共享功能，包括：
1. 位置获取
2. 位置跟踪
3. 地理围栏
4. 位置共享
5. 位置历史
6. 逆地理编码
"""

import logging
import time
import math
import threading
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class LocationAccuracy(Enum):
    """定位精度枚举"""
    HIGH = "high"          # GPS
    BALANCED = "balanced"  # GPS + WiFi
    LOW = "low"            # 网络
    PASSIVE = "passive"    # 被动接收

class LocationPriority(Enum):
    """定位优先级枚举"""
    HIGH_ACCURACY = "high_accuracy"      # 高精度
    BALANCED_POWER = "balanced_power"    # 平衡功耗
    LOW_POWER = "low_power"              # 低功耗
    NO_POWER = "no_power"                # 不主动定位

class GeofenceEvent(Enum):
    """地理围栏事件枚举"""
    ENTER = "enter"
    EXIT = "exit"
    DWELL = "dwell"

@dataclass
class LocationData:
    """位置数据"""
    id: str
    latitude: float
    longitude: float
    accuracy: float  # 米
    altitude: Optional[float] = None
    speed: Optional[float] = None  # 米/秒
    bearing: Optional[float] = None  # 度
    timestamp: float = field(default_factory=time.time)
    provider: str = "gps"  # gps, network, passive
    address: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    street: Optional[str] = None

@dataclass
class Geofence:
    """地理围栏"""
    id: str
    name: str
    latitude: float
    longitude: float
    radius: float  # 米
    events: List[GeofenceEvent]
    active: bool = True
    enter_time: Optional[float] = None
    exit_time: Optional[float] = None
    dwell_time: Optional[float] = None  # 停留时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LocationShare:
    """位置共享"""
    id: str
    user_id: str
    location: LocationData
    expires_at: Optional[float] = None
    shared_with: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

@dataclass
class LocationConfig:
    """位置配置"""
    # 定位配置
    accuracy: LocationAccuracy = LocationAccuracy.BALANCED
    priority: LocationPriority = LocationPriority.BALANCED_POWER
    update_interval: int = 10  # 秒
    fastest_interval: int = 5  # 秒
    
    # 跟踪配置
    enable_tracking: bool = False
    track_duration: Optional[int] = None  # 秒
    track_distance: float = 10.0  # 米
    
    # 地理围栏配置
    geofence_check_interval: int = 30  # 秒
    max_geofences: int = 20
    
    # 共享配置
    share_interval: int = 30  # 秒
    share_duration: int = 3600  # 秒，默认1小时
    
    # 历史配置
    keep_history: bool = True
    max_history: int = 1000
    
    # 逆地理编码
    enable_reverse_geocoding: bool = True
    geocoding_cache_ttl: int = 3600  # 秒

class LocationSharing:
    """
    位置共享管理器
    
    负责位置信息的获取、跟踪和共享。
    """
    
    def __init__(self, config: Optional[LocationConfig] = None):
        """
        初始化位置共享管理器
        
        Args:
            config: 位置配置
        """
        self.config = config or LocationConfig()
        
        # 当前位置
        self.current_location: Optional[LocationData] = None
        
        # 位置历史
        self.location_history: List[LocationData] = []
        
        # 地理围栏
        self.geofences: Dict[str, Geofence] = {}
        
        # 位置共享
        self.location_shares: Dict[str, LocationShare] = {}
        
        # 跟踪状态
        self.is_tracking = False
        self.track_start_time: Optional[float] = None
        self.track_path: List[LocationData] = []
        
        # 逆地理编码缓存
        self.geocoding_cache: Dict[str, tuple] = {}  # lat,lng -> (address, expiry)
        
        # 更新线程
        self._update_thread: Optional[threading.Thread] = None
        self._stop_updates = threading.Event()
        
        # 回调函数
        self.on_location_updated: Optional[Callable[[LocationData], None]] = None
        self.on_geofence_event: Optional[Callable[[Geofence, GeofenceEvent], None]] = None
        self.on_share_received: Optional[Callable[[LocationShare], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "updates": 0,
            "geofence_events": 0,
            "shares_sent": 0,
            "shares_received": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
        # 启动更新
        self._start_updates()
        
        logger.info("LocationSharing initialized")
    
    def _start_updates(self):
        """启动位置更新"""
        def update_loop():
            while not self._stop_updates.is_set():
                try:
                    # 获取新位置
                    new_location = self._get_current_location()
                    
                    if new_location:
                        self._process_location_update(new_location)
                    
                    # 检查地理围栏
                    self._check_geofences()
                    
                    # 检查共享过期
                    self._check_share_expiry()
                    
                    self._stop_updates.wait(self.config.update_interval)
                    
                except Exception as e:
                    logger.error(f"Update error: {e}")
                    self.stats["errors"] += 1
        
        self._update_thread = threading.Thread(target=update_loop, daemon=True)
        self._update_thread.start()
        logger.debug("Location updates started")
    
    def _get_current_location(self) -> Optional[LocationData]:
        """获取当前位置"""
        # 实际实现中会通过原生代码获取真实位置
        # 这里返回模拟数据
        import random
        
        # 模拟位置（北京市中心附近）
        base_lat = 39.9042
        base_lng = 116.4074
        
        # 添加随机偏移
        lat = base_lat + random.uniform(-0.01, 0.01)
        lng = base_lng + random.uniform(-0.01, 0.01)
        
        location = LocationData(
            id=str(uuid.uuid4()),
            latitude=lat,
            longitude=lng,
            accuracy=random.uniform(5, 20),
            altitude=random.uniform(0, 100),
            speed=random.uniform(0, 5) if self.is_tracking else 0,
            bearing=random.uniform(0, 360) if self.is_tracking else None,
            provider=random.choice(["gps", "network"]),
            timestamp=time.time()
        )
        
        return location
    
    def _process_location_update(self, location: LocationData):
        """处理位置更新"""
        self.current_location = location
        self.stats["updates"] += 1
        
        # 添加到历史
        if self.config.keep_history:
            self.location_history.append(location)
            if len(self.location_history) > self.config.max_history:
                self.location_history = self.location_history[-self.config.max_history:]
        
        # 添加到跟踪路径
        if self.is_tracking:
            self.track_path.append(location)
        
        # 逆地理编码
        if self.config.enable_reverse_geocoding:
            location.address = self._reverse_geocode(location.latitude, location.longitude)
        
        logger.debug(f"Location updated: ({location.latitude:.4f}, {location.longitude:.4f})")
        
        if self.on_location_updated:
            self.on_location_updated(location)
    
    def _reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """逆地理编码"""
        # 检查缓存
        cache_key = f"{latitude:.4f},{longitude:.4f}"
        
        if cache_key in self.geocoding_cache:
            address, expiry = self.geocoding_cache[cache_key]
            if time.time() < expiry:
                return address
        
        # 实际实现中会调用地理编码API
        # 这里返回模拟数据
        address = f"北京市朝阳区某街道 ({latitude:.4f}, {longitude:.4f})"
        
        # 缓存结果
        self.geocoding_cache[cache_key] = (address, time.time() + self.config.geocoding_cache_ttl)
        
        return address
    
    def _check_geofences(self):
        """检查地理围栏"""
        if not self.current_location:
            return
        
        for geofence in self.geofences.values():
            if not geofence.active:
                continue
            
            # 计算距离
            distance = self._calculate_distance(
                self.current_location.latitude,
                self.current_location.longitude,
                geofence.latitude,
                geofence.longitude
            )
            
            was_inside = geofence.enter_time is not None
            is_inside = distance <= geofence.radius
            
            if is_inside and not was_inside:
                # 进入围栏
                geofence.enter_time = time.time()
                geofence.exit_time = None
                
                if GeofenceEvent.ENTER in geofence.events:
                    self.stats["geofence_events"] += 1
                    logger.info(f"Entered geofence: {geofence.name}")
                    
                    if self.on_geofence_event:
                        self.on_geofence_event(geofence, GeofenceEvent.ENTER)
            
            elif not is_inside and was_inside:
                # 计算停留时间
                if geofence.enter_time:
                    geofence.dwell_time = time.time() - geofence.enter_time
                
                geofence.enter_time = None
                geofence.exit_time = time.time()
                
                if GeofenceEvent.EXIT in geofence.events:
                    self.stats["geofence_events"] += 1
                    logger.info(f"Exited geofence: {geofence.name}")
                    
                    if self.on_geofence_event:
                        self.on_geofence_event(geofence, GeofenceEvent.EXIT)
            
            # 检查停留时间
            if is_inside and was_inside and GeofenceEvent.DWELL in geofence.events:
                if geofence.enter_time:
                    dwell = time.time() - geofence.enter_time
                    if geofence.dwell_time is None or dwell > geofence.dwell_time:
                        geofence.dwell_time = dwell
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点间距离（Haversine公式）"""
        R = 6371000  # 地球半径（米）
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _check_share_expiry(self):
        """检查共享过期"""
        current_time = time.time()
        expired_shares = []
        
        for share_id, share in self.location_shares.items():
            if share.expires_at and share.expires_at < current_time:
                expired_shares.append(share_id)
        
        for share_id in expired_shares:
            del self.location_shares[share_id]
            logger.debug(f"Location share expired: {share_id}")
    
    def start_tracking(self):
        """开始位置跟踪"""
        if self.is_tracking:
            logger.warning("Tracking already started")
            return
        
        self.is_tracking = True
        self.track_start_time = time.time()
        self.track_path.clear()
        
        logger.info("Location tracking started")
    
    def stop_tracking(self) -> List[LocationData]:
        """
        停止位置跟踪
        
        Returns:
            跟踪路径
        """
        if not self.is_tracking:
            logger.warning("Tracking not started")
            return []
        
        self.is_tracking = False
        path = self.track_path.copy()
        
        logger.info(f"Location tracking stopped, recorded {len(path)} points")
        
        return path
    
    def add_geofence(self, name: str, latitude: float, longitude: float,
                    radius: float, events: List[GeofenceEvent]) -> str:
        """
        添加地理围栏
        
        Args:
            name: 围栏名称
            latitude: 纬度
            longitude: 经度
            radius: 半径（米）
            events: 要监听的事件
        
        Returns:
            围栏ID
        """
        if len(self.geofences) >= self.config.max_geofences:
            logger.warning(f"Max geofences reached ({self.config.max_geofences})")
            return ""
        
        geofence_id = str(uuid.uuid4())
        
        geofence = Geofence(
            id=geofence_id,
            name=name,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            events=events
        )
        
        self.geofences[geofence_id] = geofence
        
        logger.info(f"Geofence added: {name} ({radius}m)")
        
        return geofence_id
    
    def remove_geofence(self, geofence_id: str) -> bool:
        """
        移除地理围栏
        
        Args:
            geofence_id: 围栏ID
        
        Returns:
            是否成功
        """
        if geofence_id in self.geofences:
            del self.geofences[geofence_id]
            logger.info(f"Geofence removed: {geofence_id}")
            return True
        return False
    
    def share_location(self, user_id: str, duration: Optional[int] = None,
                      shared_with: Optional[List[str]] = None) -> str:
        """
        共享位置
        
        Args:
            user_id: 用户ID
            duration: 共享持续时间（秒）
            shared_with: 共享给的用户列表
        
        Returns:
            共享ID
        """
        if not self.current_location:
            logger.warning("No current location to share")
            return ""
        
        share_duration = duration or self.config.share_duration
        expires_at = time.time() + share_duration if share_duration > 0 else None
        
        share = LocationShare(
            id=str(uuid.uuid4()),
            user_id=user_id,
            location=self.current_location,
            expires_at=expires_at,
            shared_with=shared_with or []
        )
        
        self.location_shares[share.id] = share
        self.stats["shares_sent"] += 1
        
        logger.info(f"Location shared with {len(share.shared_with)} users, expires in {share_duration}s")
        
        return share.id
    
    def receive_share(self, share: LocationShare):
        """
        接收共享位置
        
        Args:
            share: 位置共享
        """
        self.location_shares[share.id] = share
        self.stats["shares_received"] += 1
        
        logger.info(f"Location received from {share.user_id}")
        
        if self.on_share_received:
            self.on_share_received(share)
    
    def stop_sharing(self, share_id: str):
        """
        停止共享
        
        Args:
            share_id: 共享ID
        """
        if share_id in self.location_shares:
            del self.location_shares[share_id]
            logger.info(f"Location sharing stopped: {share_id}")
    
    def get_active_shares(self) -> List[LocationShare]:
        """获取活动共享"""
        return list(self.location_shares.values())
    
    def get_geofences(self) -> List[Geofence]:
        """获取地理围栏"""
        return list(self.geofences.values())
    
    def get_location_history(self, limit: int = 100) -> List[LocationData]:
        """
        获取位置历史
        
        Args:
            limit: 返回数量
        
        Returns:
            位置历史
        """
        return self.location_history[-limit:]
    
    def get_track_path(self) -> List[LocationData]:
        """获取跟踪路径"""
        return self.track_path
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取位置共享管理器状态
        
        Returns:
            状态字典
        """
        return {
            "has_location": self.current_location is not None,
            "current_location": {
                "lat": self.current_location.latitude if self.current_location else None,
                "lng": self.current_location.longitude if self.current_location else None,
                "accuracy": self.current_location.accuracy if self.current_location else None
            } if self.current_location else None,
            "is_tracking": self.is_tracking,
            "track_points": len(self.track_path),
            "geofences": {
                "count": len(self.geofences),
                "max": self.config.max_geofences
            },
            "shares": {
                "active": len(self.location_shares),
                "sent": self.stats["shares_sent"],
                "received": self.stats["shares_received"]
            },
            "history_size": len(self.location_history),
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭位置共享管理器"""
        logger.info("Shutting down LocationSharing...")
        
        self._stop_updates.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2)
        
        self.location_history.clear()
        self.geofences.clear()
        self.location_shares.clear()
        self.track_path.clear()
        self.geocoding_cache.clear()
        
        logger.info("LocationSharing shutdown completed")

# 单例模式实现
_location_sharing_instance: Optional[LocationSharing] = None

def get_location_sharing(config: Optional[LocationConfig] = None) -> LocationSharing:
    """
    获取位置共享管理器单例
    
    Args:
        config: 位置配置
    
    Returns:
        位置共享管理器实例
    """
    global _location_sharing_instance
    if _location_sharing_instance is None:
        _location_sharing_instance = LocationSharing(config)
    return _location_sharing_instance

