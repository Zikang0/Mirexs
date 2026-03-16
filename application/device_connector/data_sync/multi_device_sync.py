"""
多设备同步模块 - Mirexs数据同步系统

提供多设备数据同步功能，包括：
1. 设备发现和注册
2. 同步会话管理
3. 增量同步
4. 全量同步
5. 设备状态监控
6. 同步优先级
"""

import logging
import time
import threading
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)

class DevicePlatform(Enum):
    """设备平台枚举"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"
    OTHER = "other"

class DeviceRole(Enum):
    """设备角色枚举"""
    PRIMARY = "primary"      # 主设备
    SECONDARY = "secondary"   # 从设备
    PEER = "peer"            # 对等设备

class SyncStatus(Enum):
    """同步状态枚举"""
    IDLE = "idle"
    SYNCING = "syncing"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SyncMode(Enum):
    """同步模式枚举"""
    FULL = "full"            # 全量同步
    INCREMENTAL = "incremental"  # 增量同步
    MERGE = "merge"          # 合并同步

@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    name: str
    platform: DevicePlatform
    role: DeviceRole
    version: str
    last_seen: float = field(default_factory=time.time)
    ip_address: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    sync_enabled: bool = True
    priority: int = 0  # 同步优先级，越高越优先

@dataclass
class SyncSession:
    """同步会话"""
    id: str
    source_device: str
    target_device: str
    mode: SyncMode
    status: SyncStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    items_synced: int = 0
    total_items: int = 0
    bytes_transferred: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SyncItem:
    """同步项"""
    id: str
    collection: str
    data: Dict[str, Any]
    version: int = 1
    timestamp: float = field(default_factory=time.time)
    hash: Optional[str] = None
    deleted: bool = False
    device_id: Optional[str] = None

@dataclass
class SyncConfig:
    """多设备同步配置"""
    # 设备配置
    device_name: str = "Mirexs Device"
    device_platform: DevicePlatform = DevicePlatform.OTHER
    device_role: DeviceRole = DeviceRole.PEER
    
    # 同步配置
    auto_sync: bool = True
    sync_interval: int = 300  # 秒
    sync_on_connect: bool = True
    max_concurrent_syncs: int = 3
    
    # 网络配置
    discovery_port: int = 9878
    sync_port: int = 9879
    broadcast_interval: int = 30  # 秒
    
    # 存储配置
    data_dir: str = "data/sync/"
    max_history: int = 1000

class MultiDeviceSync:
    """
    多设备同步管理器
    
    负责多设备间的数据同步管理。
    """
    
    def __init__(self, config: Optional[SyncConfig] = None):
        """
        初始化多设备同步管理器
        
        Args:
            config: 同步配置
        """
        self.config = config or SyncConfig()
        
        # 本地设备
        self.local_device = DeviceInfo(
            device_id=str(uuid.uuid4()),
            name=self.config.device_name,
            platform=self.config.device_platform,
            role=self.config.device_role,
            version="1.0.0"
        )
        
        # 设备管理
        self.devices: Dict[str, DeviceInfo] = {
            self.local_device.device_id: self.local_device
        }
        self.trusted_devices: Dict[str, DeviceInfo] = {}
        
        # 同步会话
        self.sessions: Dict[str, SyncSession] = {}
        self.active_sessions: Dict[str, threading.Thread] = {}
        
        # 数据存储
        self.data: Dict[str, Dict[str, SyncItem]] = {}  # collection -> {item_id: item}
        
        # 设备发现线程
        self._discovery_thread: Optional[threading.Thread] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_discovery = threading.Event()
        
        # 回调函数
        self.on_device_discovered: Optional[Callable[[DeviceInfo], None]] = None
        self.on_device_connected: Optional[Callable[[DeviceInfo], None]] = None
        self.on_device_disconnected: Optional[Callable[[str], None]] = None
        self.on_sync_started: Optional[Callable[[SyncSession], None]] = None
        self.on_sync_completed: Optional[Callable[[SyncSession], None]] = None
        self.on_sync_progress: Optional[Callable[[str, int, int], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "devices_discovered": 0,
            "devices_trusted": 0,
            "sync_sessions": 0,
            "items_synced": 0,
            "bytes_transferred": 0,
            "errors": 0
        }
        
        # 启动设备发现
        self._start_discovery()
        
        logger.info(f"MultiDeviceSync initialized for device {self.local_device.device_id}")
    
    def _start_discovery(self):
        """启动设备发现"""
        def discovery_loop():
            while not self._stop_discovery.is_set():
                try:
                    self._broadcast_presence()
                    self._discover_devices()
                    self._cleanup_stale_devices()
                    self._stop_discovery.wait(self.config.broadcast_interval)
                except Exception as e:
                    logger.error(f"Discovery error: {e}")
                    self.stats["errors"] += 1
        
        self._discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
        self._discovery_thread.start()
        logger.debug("Device discovery started")
    
    def _broadcast_presence(self):
        """广播设备存在"""
        # 实际实现中会通过网络广播
        pass
    
    def _discover_devices(self):
        """发现设备"""
        # 实际实现中会监听网络广播
        pass
    
    def _cleanup_stale_devices(self):
        """清理过时设备"""
        current_time = time.time()
        stale_devices = []
        
        for device_id, device in self.devices.items():
            if device_id == self.local_device.device_id:
                continue
            
            if current_time - device.last_seen > 300:  # 5分钟
                stale_devices.append(device_id)
        
        for device_id in stale_devices:
            self._remove_device(device_id)
    
    def _remove_device(self, device_id: str):
        """移除设备"""
        if device_id in self.devices:
            device = self.devices[device_id]
            del self.devices[device_id]
            
            if device_id in self.trusted_devices:
                del self.trusted_devices[device_id]
            
            logger.info(f"Device removed: {device.name} ({device_id})")
            
            if self.on_device_disconnected:
                self.on_device_disconnected(device_id)
    
    def discover_device(self, device_info: DeviceInfo):
        """
        发现设备
        
        Args:
            device_info: 设备信息
        """
        if device_info.device_id == self.local_device.device_id:
            return
        
        if device_info.device_id not in self.devices:
            self.devices[device_info.device_id] = device_info
            self.stats["devices_discovered"] += 1
            
            logger.info(f"Device discovered: {device_info.name} ({device_info.device_id})")
            
            if self.on_device_discovered:
                self.on_device_discovered(device_info)
        else:
            # 更新最后看到时间
            self.devices[device_info.device_id].last_seen = time.time()
    
    def trust_device(self, device_id: str) -> bool:
        """
        信任设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否成功
        """
        if device_id not in self.devices:
            logger.warning(f"Device {device_id} not found")
            return False
        
        device = self.devices[device_id]
        self.trusted_devices[device_id] = device
        self.stats["devices_trusted"] += 1
        
        logger.info(f"Device trusted: {device.name} ({device_id})")
        
        if self.on_device_connected:
            self.on_device_connected(device)
        
        # 自动同步
        if self.config.sync_on_connect:
            self.start_sync(device_id)
        
        return True
    
    def untrust_device(self, device_id: str) -> bool:
        """
        取消信任设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否成功
        """
        if device_id in self.trusted_devices:
            device = self.trusted_devices[device_id]
            del self.trusted_devices[device_id]
            
            logger.info(f"Device untrusted: {device.name} ({device_id})")
            
            if self.on_device_disconnected:
                self.on_device_disconnected(device_id)
            
            return True
        
        return False
    
    def start_sync(self, target_device_id: str, mode: SyncMode = SyncMode.INCREMENTAL) -> Optional[str]:
        """
        开始同步
        
        Args:
            target_device_id: 目标设备ID
            mode: 同步模式
        
        Returns:
            会话ID
        """
        if target_device_id not in self.trusted_devices:
            logger.warning(f"Device {target_device_id} not trusted")
            return None
        
        # 检查是否有正在进行的同步
        for session in self.sessions.values():
            if (session.source_device == self.local_device.device_id and 
                session.target_device == target_device_id and
                session.status == SyncStatus.SYNCING):
                logger.warning(f"Sync already in progress with device {target_device_id}")
                return None
        
        session_id = str(uuid.uuid4())
        
        session = SyncSession(
            id=session_id,
            source_device=self.local_device.device_id,
            target_device=target_device_id,
            mode=mode,
            status=SyncStatus.SYNCING,
            start_time=time.time()
        )
        
        self.sessions[session_id] = session
        self.stats["sync_sessions"] += 1
        
        logger.info(f"Starting sync with {target_device_id} (mode: {mode.value})")
        
        if self.on_sync_started:
            self.on_sync_started(session)
        
        # 在后台线程中执行同步
        def sync_thread():
            try:
                if mode == SyncMode.FULL:
                    self._full_sync(session)
                elif mode == SyncMode.INCREMENTAL:
                    self._incremental_sync(session)
                else:
                    self._merge_sync(session)
                
                session.status = SyncStatus.COMPLETED
                session.end_time = time.time()
                
                logger.info(f"Sync completed: {session_id}, {session.items_synced} items")
                
                if self.on_sync_completed:
                    self.on_sync_completed(session)
                
            except Exception as e:
                session.status = SyncStatus.ERROR
                session.error = str(e)
                session.end_time = time.time()
                
                logger.error(f"Sync error: {e}")
                self.stats["errors"] += 1
                
                if self.on_error:
                    self.on_error(f"Sync failed: {e}")
            
            finally:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
        
        thread = threading.Thread(target=sync_thread, daemon=True)
        self.active_sessions[session_id] = thread
        thread.start()
        
        return session_id
    
    def _full_sync(self, session: SyncSession):
        """全量同步"""
        total_items = 0
        synced_items = 0
        
        # 收集所有数据
        all_items = []
        for collection in self.data:
            all_items.extend(self.data[collection].values())
        
        session.total_items = len(all_items)
        
        for item in all_items:
            if item.deleted:
                continue
            
            # 发送数据到目标设备
            self._send_item(session.target_device, item)
            
            synced_items += 1
            session.items_synced = synced_items
            
            if self.on_sync_progress:
                self.on_sync_progress(session.id, synced_items, session.total_items)
        
        logger.debug(f"Full sync completed: {synced_items} items")
    
    def _incremental_sync(self, session: SyncSession):
        """增量同步"""
        # 获取目标设备的版本信息
        target_versions = self._get_device_versions(session.target_device)
        
        synced_items = 0
        
        for collection in self.data:
            for item_id, item in self.data[collection].items():
                target_version = target_versions.get(collection, {}).get(item_id, 0)
                
                if item.version > target_version:
                    self._send_item(session.target_device, item)
                    synced_items += 1
                    
                    if self.on_sync_progress:
                        self.on_sync_progress(session.id, synced_items, None)
        
        session.items_synced = synced_items
        
        logger.debug(f"Incremental sync completed: {synced_items} items")
    
    def _merge_sync(self, session: SyncSession):
        """合并同步"""
        # 获取目标设备的数据
        target_data = self._get_device_data(session.target_device)
        
        merged_items = 0
        
        for collection in set(self.data.keys()) | set(target_data.keys()):
            local_items = self.data.get(collection, {})
            remote_items = target_data.get(collection, {})
            
            # 合并两个集合
            all_item_ids = set(local_items.keys()) | set(remote_items.keys())
            
            for item_id in all_item_ids:
                local_item = local_items.get(item_id)
                remote_item = remote_items.get(item_id)
                
                if local_item and remote_item:
                    # 两边都有，取版本高的
                    if local_item.version >= remote_item.version:
                        self._send_item(session.target_device, local_item)
                    else:
                        self._receive_item(remote_item)
                elif local_item:
                    self._send_item(session.target_device, local_item)
                elif remote_item:
                    self._receive_item(remote_item)
                
                merged_items += 1
                session.items_synced = merged_items
                
                if self.on_sync_progress:
                    self.on_sync_progress(session.id, merged_items, None)
        
        logger.debug(f"Merge sync completed: {merged_items} items")
    
    def _send_item(self, target_device_id: str, item: SyncItem):
        """发送数据项"""
        # 实际实现中会通过网络发送
        data_size = len(json.dumps(item.data))
        self.stats["bytes_transferred"] += data_size
        session = self._get_session_by_target(target_device_id)
        if session:
            session.bytes_transferred += data_size
        
        self.stats["items_synced"] += 1
    
    def _receive_item(self, item: SyncItem):
        """接收数据项"""
        # 存储到本地
        if item.collection not in self.data:
            self.data[item.collection] = {}
        
        self.data[item.collection][item.id] = item
    
    def _get_device_versions(self, device_id: str) -> Dict[str, Dict[str, int]]:
        """获取设备版本信息"""
        # 实际实现中会从设备查询
        return {}
    
    def _get_device_data(self, device_id: str) -> Dict[str, Dict[str, SyncItem]]:
        """获取设备数据"""
        # 实际实现中会从设备获取
        return {}
    
    def _get_session_by_target(self, target_device_id: str) -> Optional[SyncSession]:
        """根据目标设备获取会话"""
        for session in self.sessions.values():
            if session.target_device == target_device_id and session.status == SyncStatus.SYNCING:
                return session
        return None
    
    def cancel_sync(self, session_id: str) -> bool:
        """
        取消同步
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否成功
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return False
        
        session = self.sessions[session_id]
        
        if session.status == SyncStatus.SYNCING:
            session.status = SyncStatus.CANCELLED
            session.end_time = time.time()
            
            logger.info(f"Sync cancelled: {session_id}")
            
            return True
        
        return False
    
    def add_item(self, collection: str, item_id: str, data: Dict[str, Any]) -> str:
        """
        添加数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            data: 数据
        
        Returns:
            项目ID
        """
        if collection not in self.data:
            self.data[collection] = {}
        
        # 检查是否已存在
        if item_id in self.data[collection]:
            existing = self.data[collection][item_id]
            existing.data = data
            existing.version += 1
            existing.timestamp = time.time()
            existing.hash = self._calculate_hash(data)
            item = existing
        else:
            item = SyncItem(
                id=item_id,
                collection=collection,
                data=data,
                hash=self._calculate_hash(data),
                device_id=self.local_device.device_id
            )
            self.data[collection][item_id] = item
        
        logger.debug(f"Item added: {collection}/{item_id} (v{item.version})")
        
        return item_id
    
    def update_item(self, collection: str, item_id: str, data: Dict[str, Any]) -> bool:
        """
        更新数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            data: 新数据
        
        Returns:
            是否成功
        """
        if collection not in self.data or item_id not in self.data[collection]:
            logger.warning(f"Item not found: {collection}/{item_id}")
            return False
        
        item = self.data[collection][item_id]
        item.data = data
        item.version += 1
        item.timestamp = time.time()
        item.hash = self._calculate_hash(data)
        item.device_id = self.local_device.device_id
        
        logger.debug(f"Item updated: {collection}/{item_id} (v{item.version})")
        
        return True
    
    def delete_item(self, collection: str, item_id: str) -> bool:
        """
        删除数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
        
        Returns:
            是否成功
        """
        if collection not in self.data or item_id not in self.data[collection]:
            logger.warning(f"Item not found: {collection}/{item_id}")
            return False
        
        item = self.data[collection][item_id]
        item.deleted = True
        item.version += 1
        item.timestamp = time.time()
        
        logger.debug(f"Item deleted: {collection}/{item_id}")
        
        return True
    
    def get_item(self, collection: str, item_id: str) -> Optional[SyncItem]:
        """
        获取数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
        
        Returns:
            数据项
        """
        if collection in self.data and item_id in self.data[collection]:
            item = self.data[collection][item_id]
            if not item.deleted:
                return item
        return None
    
    def get_collection(self, collection: str) -> List[SyncItem]:
        """
        获取集合中的所有项
        
        Args:
            collection: 集合名称
        
        Returns:
            数据项列表
        """
        if collection not in self.data:
            return []
        
        return [item for item in self.data[collection].values() if not item.deleted]
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def get_devices(self, trusted_only: bool = False) -> List[DeviceInfo]:
        """
        获取设备列表
        
        Args:
            trusted_only: 是否只返回信任的设备
        
        Returns:
            设备列表
        """
        if trusted_only:
            return list(self.trusted_devices.values())
        return list(self.devices.values())
    
    def get_sessions(self, status: Optional[SyncStatus] = None) -> List[SyncSession]:
        """
        获取会话列表
        
        Args:
            status: 状态过滤
        
        Returns:
            会话列表
        """
        sessions = list(self.sessions.values())
        
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        return sessions
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取多设备同步管理器状态
        
        Returns:
            状态字典
        """
        return {
            "local_device": {
                "id": self.local_device.device_id,
                "name": self.local_device.name,
                "platform": self.local_device.platform.value,
                "role": self.local_device.role.value
            },
            "devices": {
                "total": len(self.devices),
                "trusted": len(self.trusted_devices)
            },
            "sessions": {
                "total": len(self.sessions),
                "active": len([s for s in self.sessions.values() if s.status == SyncStatus.SYNCING]),
                "completed": len([s for s in self.sessions.values() if s.status == SyncStatus.COMPLETED]),
                "error": len([s for s in self.sessions.values() if s.status == SyncStatus.ERROR])
            },
            "data": {
                "collections": len(self.data),
                "total_items": sum(len(items) for items in self.data.values())
            },
            "stats": self.stats
        }
    
    def shutdown(self):
        """关闭多设备同步管理器"""
        logger.info("Shutting down MultiDeviceSync...")
        
        self._stop_discovery.set()
        
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=2)
        
        # 取消所有活动同步
        for session_id in list(self.active_sessions.keys()):
            self.cancel_sync(session_id)
        
        # 等待同步线程结束
        for thread in self.active_sessions.values():
            thread.join(timeout=2)
        
        self.devices.clear()
        self.trusted_devices.clear()
        self.sessions.clear()
        self.data.clear()
        self.active_sessions.clear()
        
        logger.info("MultiDeviceSync shutdown completed")

# 单例模式实现
_multi_device_sync_instance: Optional[MultiDeviceSync] = None

def get_multi_device_sync(config: Optional[SyncConfig] = None) -> MultiDeviceSync:
    """
    获取多设备同步管理器单例
    
    Args:
        config: 同步配置
    
    Returns:
        多设备同步管理器实例
    """
    global _multi_device_sync_instance
    if _multi_device_sync_instance is None:
        _multi_device_sync_instance = MultiDeviceSync(config)
    return _multi_device_sync_instance

