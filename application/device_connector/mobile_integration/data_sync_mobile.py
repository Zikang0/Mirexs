"""
移动数据同步模块 - Mirexs移动设备集成

提供移动端数据同步功能，包括：
1. 联系人同步
2. 日历同步
3. 文件同步
4. 设置同步
5. 应用数据同步
6. 增量同步
"""

import logging
import time
import json
import hashlib
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

class DataType(Enum):
    """数据类型枚举"""
    CONTACTS = "contacts"
    CALENDAR = "calendar"
    FILES = "files"
    SETTINGS = "settings"
    APP_DATA = "app_data"
    MEDIA = "media"
    MESSAGES = "messages"
    CALLS = "calls"

class MobileSyncStatus(Enum):
    """同步状态枚举"""
    IDLE = "idle"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CONFLICT = "conflict"

class SyncDirection(Enum):
    """同步方向枚举"""
    UPLOAD = "upload"
    DOWNLOAD = "download"
    BIDIRECTIONAL = "bidirectional"

@dataclass
class SyncItem:
    """同步项"""
    id: str
    type: DataType
    data: Dict[str, Any]
    version: int = 1
    hash: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    deleted: bool = False

@dataclass
class SyncOperation:
    """同步操作"""
    id: str
    item_id: str
    type: DataType
    operation: str  # create, update, delete
    data: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    status: MobileSyncStatus = MobileSyncStatus.IDLE
    retry_count: int = 0

@dataclass
class MobileSyncConfig:
    """移动同步配置"""
    # 同步配置
    sync_interval: int = 300  # 秒
    batch_size: int = 100
    auto_sync: bool = True
    
    # 数据类型配置
    sync_contacts: bool = True
    sync_calendar: bool = True
    sync_files: bool = False
    sync_settings: bool = True
    sync_app_data: bool = True
    
    # 网络配置
    sync_on_wifi_only: bool = True
    sync_on_metered: bool = False
    sync_on_roaming: bool = False
    
    # 冲突处理
    conflict_resolution: str = "server_wins"  # server_wins, client_wins, manual
    
    # 存储配置
    local_cache_path: str = "data/mobile_sync/"
    max_cache_size: int = 1024 * 1024 * 100  # 100MB
    
    # 历史配置
    keep_history: bool = True
    max_history: int = 1000

class DataSyncMobile:
    """
    移动数据同步管理器
    
    负责移动设备数据的同步管理。
    """
    
    def __init__(self, config: Optional[MobileSyncConfig] = None):
        """
        初始化移动数据同步管理器
        
        Args:
            config: 同步配置
        """
        self.config = config or MobileSyncConfig()
        
        # 同步状态
        self.sync_status: Dict[DataType, MobileSyncStatus] = {}
        self.current_operation: Optional[SyncOperation] = None
        
        # 数据存储
        self.local_data: Dict[DataType, Dict[str, SyncItem]] = {}
        self.remote_data: Dict[DataType, Dict[str, SyncItem]] = {}
        
        # 操作队列
        self.operation_queue: List[SyncOperation] = []
        self.completed_operations: List[SyncOperation] = []
        
        # 冲突记录
        self.conflicts: List[Dict[str, Any]] = []
        
        # 同步线程
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()
        
        # 回调函数
        self.on_sync_started: Optional[Callable[[DataType], None]] = None
        self.on_sync_completed: Optional[Callable[[DataType, int, int], None]] = None
        self.on_item_synced: Optional[Callable[[SyncItem, SyncDirection], None]] = None
        self.on_conflict_detected: Optional[Callable[[SyncItem, SyncItem], str]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "total_syncs": 0,
            "items_synced": 0,
            "items_created": 0,
            "items_updated": 0,
            "items_deleted": 0,
            "conflicts": 0,
            "errors": 0
        }
        
        # 初始化数据存储
        self._init_data_stores()
        
        # 启动自动同步
        if self.config.auto_sync:
            self._start_auto_sync()
        
        logger.info("DataSyncMobile initialized")
    
    def _init_data_stores(self):
        """初始化数据存储"""
        for data_type in DataType:
            self.local_data[data_type] = {}
            self.remote_data[data_type] = {}
            self.sync_status[data_type] = MobileSyncStatus.IDLE
    
    def _start_auto_sync(self):
        """启动自动同步"""
        def sync_loop():
            while not self._stop_sync.is_set():
                try:
                    self.sync_all()
                    self._stop_sync.wait(self.config.sync_interval)
                except Exception as e:
                    logger.error(f"Auto sync error: {e}")
                    self.stats["errors"] += 1
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()
        logger.debug("Auto sync started")
    
    def sync_all(self):
        """同步所有数据类型"""
        for data_type in DataType:
            if self._should_sync_type(data_type):
                self.sync_type(data_type)
    
    def _should_sync_type(self, data_type: DataType) -> bool:
        """检查是否应该同步该类型"""
        type_config = {
            DataType.CONTACTS: self.config.sync_contacts,
            DataType.CALENDAR: self.config.sync_calendar,
            DataType.FILES: self.config.sync_files,
            DataType.SETTINGS: self.config.sync_settings,
            DataType.APP_DATA: self.config.sync_app_data
        }
        return type_config.get(data_type, False)
    
    def sync_type(self, data_type: DataType) -> bool:
        """
        同步指定类型的数据
        
        Args:
            data_type: 数据类型
        
        Returns:
            是否成功启动同步
        """
        if self.sync_status[data_type] == MobileSyncStatus.SYNCING:
            logger.warning(f"Sync already in progress for {data_type.value}")
            return False
        
        logger.info(f"Starting sync for {data_type.value}")
        
        self.sync_status[data_type] = MobileSyncStatus.SYNCING
        self.stats["total_syncs"] += 1
        
        if self.on_sync_started:
            self.on_sync_started(data_type)
        
        def sync_thread():
            try:
                # 获取远程数据
                remote_items = self._fetch_remote_data(data_type)
                self.remote_data[data_type] = remote_items
                
                # 检测变化
                changes = self._detect_changes(data_type)
                
                # 处理变化
                created, updated, deleted = self._process_changes(data_type, changes)
                
                self.sync_status[data_type] = MobileSyncStatus.COMPLETED
                
                logger.info(f"Sync completed for {data_type.value}: "
                          f"{created} created, {updated} updated, {deleted} deleted")
                
                if self.on_sync_completed:
                    self.on_sync_completed(data_type, created + updated, deleted)
                
            except Exception as e:
                logger.error(f"Sync error for {data_type.value}: {e}")
                self.sync_status[data_type] = MobileSyncStatus.FAILED
                self.stats["errors"] += 1
                
                if self.on_error:
                    self.on_error(f"Sync failed for {data_type.value}: {e}")
        
        thread = threading.Thread(target=sync_thread, daemon=True)
        thread.start()
        
        return True
    
    def _fetch_remote_data(self, data_type: DataType) -> Dict[str, SyncItem]:
        """获取远程数据"""
        # 实际实现中会从服务器获取
        # 这里返回空字典
        return {}
    
    def _detect_changes(self, data_type: DataType) -> Dict[str, str]:
        """
        检测数据变化
        
        Returns:
            变化字典 {item_id: change_type}
        """
        changes = {}
        
        local_items = self.local_data[data_type]
        remote_items = self.remote_data[data_type]
        
        # 检查本地新增或更新
        for item_id, local_item in local_items.items():
            if item_id not in remote_items:
                changes[item_id] = "create"
            else:
                remote_item = remote_items[item_id]
                if local_item.version > remote_item.version:
                    changes[item_id] = "update"
        
        # 检查远程新增或更新
        for item_id, remote_item in remote_items.items():
            if item_id not in local_items:
                changes[item_id] = "download"
            elif not remote_item.deleted:
                if remote_item.version > local_items[item_id].version:
                    changes[item_id] = "conflict"
        
        # 检查删除
        for item_id, local_item in local_items.items():
            if local_item.deleted and item_id in remote_items:
                changes[item_id] = "delete"
        
        return changes
    
    def _process_changes(self, data_type: DataType, changes: Dict[str, str]) -> tuple:
        """处理变化"""
        created = 0
        updated = 0
        deleted = 0
        
        for item_id, change_type in changes.items():
            if change_type == "create":
                # 创建新项到远程
                local_item = self.local_data[data_type][item_id]
                self._upload_item(data_type, local_item)
                created += 1
                self.stats["items_created"] += 1
                
            elif change_type == "update":
                # 更新远程项
                local_item = self.local_data[data_type][item_id]
                self._upload_item(data_type, local_item)
                updated += 1
                self.stats["items_updated"] += 1
                
            elif change_type == "download":
                # 下载新项
                remote_item = self.remote_data[data_type][item_id]
                self._download_item(data_type, remote_item)
                created += 1
                self.stats["items_created"] += 1
                
            elif change_type == "delete":
                # 删除远程项
                local_item = self.local_data[data_type][item_id]
                self._delete_remote_item(data_type, local_item)
                deleted += 1
                self.stats["items_deleted"] += 1
                
            elif change_type == "conflict":
                # 处理冲突
                local_item = self.local_data[data_type][item_id]
                remote_item = self.remote_data[data_type][item_id]
                resolution = self._resolve_conflict(local_item, remote_item)
                
                if resolution == "local":
                    self._upload_item(data_type, local_item)
                elif resolution == "remote":
                    self._download_item(data_type, remote_item)
                
                self.stats["conflicts"] += 1
            
            self.stats["items_synced"] += 1
            
            if self.on_item_synced:
                direction = SyncDirection.UPLOAD if change_type in ["create", "update"] else SyncDirection.DOWNLOAD
                self.on_item_synced(self.local_data[data_type][item_id], direction)
        
        return created, updated, deleted
    
    def _upload_item(self, data_type: DataType, item: SyncItem):
        """上传项到远程"""
        # 实际实现中会上传到服务器
        logger.debug(f"Uploading {data_type.value} item: {item.id}")
        
        # 更新远程数据
        self.remote_data[data_type][item.id] = item
    
    def _download_item(self, data_type: DataType, item: SyncItem):
        """下载项到本地"""
        # 实际实现中会保存到本地
        logger.debug(f"Downloading {data_type.value} item: {item.id}")
        
        # 更新本地数据
        self.local_data[data_type][item.id] = item
    
    def _delete_remote_item(self, data_type: DataType, item: SyncItem):
        """删除远程项"""
        # 实际实现中会从服务器删除
        logger.debug(f"Deleting remote {data_type.value} item: {item.id}")
        
        if item.id in self.remote_data[data_type]:
            del self.remote_data[data_type][item.id]
    
    def _resolve_conflict(self, local_item: SyncItem, remote_item: SyncItem) -> str:
        """解决冲突"""
        self.conflicts.append({
            "id": str(uuid.uuid4()),
            "local": local_item,
            "remote": remote_item,
            "timestamp": time.time()
        })
        
        # 调用自定义冲突处理器
        if self.on_conflict_detected:
            resolution = self.on_conflict_detected(local_item, remote_item)
            if resolution in ["local", "remote"]:
                return resolution
        
        # 使用配置的冲突解决策略
        if self.config.conflict_resolution == "server_wins":
            return "remote"
        elif self.config.conflict_resolution == "client_wins":
            return "local"
        else:
            # 手动解决，返回远程作为默认
            return "remote"
    
    def add_item(self, data_type: DataType, data: Dict[str, Any]) -> str:
        """
        添加数据项
        
        Args:
            data_type: 数据类型
            data: 数据内容
        
        Returns:
            项ID
        """
        item_id = str(uuid.uuid4())
        
        item = SyncItem(
            id=item_id,
            type=data_type,
            data=data,
            hash=self._calculate_hash(data)
        )
        
        self.local_data[data_type][item_id] = item
        
        # 添加到操作队列
        operation = SyncOperation(
            id=str(uuid.uuid4()),
            item_id=item_id,
            type=data_type,
            operation="create",
            data=data
        )
        self.operation_queue.append(operation)
        
        logger.debug(f"Item added to {data_type.value}: {item_id}")
        
        return item_id
    
    def update_item(self, data_type: DataType, item_id: str, data: Dict[str, Any]) -> bool:
        """
        更新数据项
        
        Args:
            data_type: 数据类型
            item_id: 项ID
            data: 新数据
        
        Returns:
            是否成功
        """
        if item_id not in self.local_data[data_type]:
            logger.warning(f"Item not found: {item_id}")
            return False
        
        item = self.local_data[data_type][item_id]
        item.data = data
        item.version += 1
        item.hash = self._calculate_hash(data)
        item.timestamp = time.time()
        
        # 添加到操作队列
        operation = SyncOperation(
            id=str(uuid.uuid4()),
            item_id=item_id,
            type=data_type,
            operation="update",
            data=data
        )
        self.operation_queue.append(operation)
        
        logger.debug(f"Item updated in {data_type.value}: {item_id}")
        
        return True
    
    def delete_item(self, data_type: DataType, item_id: str) -> bool:
        """
        删除数据项
        
        Args:
            data_type: 数据类型
            item_id: 项ID
        
        Returns:
            是否成功
        """
        if item_id not in self.local_data[data_type]:
            logger.warning(f"Item not found: {item_id}")
            return False
        
        item = self.local_data[data_type][item_id]
        item.deleted = True
        
        # 添加到操作队列
        operation = SyncOperation(
            id=str(uuid.uuid4()),
            item_id=item_id,
            type=data_type,
            operation="delete"
        )
        self.operation_queue.append(operation)
        
        logger.debug(f"Item deleted from {data_type.value}: {item_id}")
        
        return True
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_item(self, data_type: DataType, item_id: str) -> Optional[SyncItem]:
        """
        获取数据项
        
        Args:
            data_type: 数据类型
            item_id: 项ID
        
        Returns:
            数据项
        """
        return self.local_data[data_type].get(item_id)
    
    def get_all_items(self, data_type: DataType) -> List[SyncItem]:
        """
        获取所有数据项
        
        Args:
            data_type: 数据类型
        
        Returns:
            数据项列表
        """
        return list(self.local_data[data_type].values())
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态
        
        Returns:
            同步状态
        """
        return {
            "sync_status": {dt.value: status.value for dt, status in self.sync_status.items()},
            "current_operation": self.current_operation.id if self.current_operation else None,
            "queues": {
                "pending": len(self.operation_queue),
                "completed": len(self.completed_operations)
            },
            "conflicts": len(self.conflicts),
            "data_counts": {
                dt.value: len(items) for dt, items in self.local_data.items()
            },
            "stats": self.stats
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取数据同步管理器状态
        
        Returns:
            状态字典
        """
        sync_status = self.get_sync_status()
        
        return {
            "config": {
                "auto_sync": self.config.auto_sync,
                "sync_interval": self.config.sync_interval,
                "sync_on_wifi_only": self.config.sync_on_wifi_only
            },
            "sync_status": sync_status["sync_status"],
            "queues": sync_status["queues"],
            "conflicts": sync_status["conflicts"],
            "data_counts": sync_status["data_counts"],
            "stats": sync_status["stats"]
        }
    
    def shutdown(self):
        """关闭数据同步管理器"""
        logger.info("Shutting down DataSyncMobile...")
        
        self._stop_sync.set()
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=2)
        
        self.local_data.clear()
        self.remote_data.clear()
        self.operation_queue.clear()
        self.completed_operations.clear()
        self.conflicts.clear()
        
        logger.info("DataSyncMobile shutdown completed")

# 单例模式实现
_data_sync_mobile_instance: Optional[DataSyncMobile] = None

def get_data_sync_mobile(config: Optional[MobileSyncConfig] = None) -> DataSyncMobile:
    """
    获取移动数据同步管理器单例
    
    Args:
        config: 同步配置
    
    Returns:
        移动数据同步管理器实例
    """
    global _data_sync_mobile_instance
    if _data_sync_mobile_instance is None:
        _data_sync_mobile_instance = DataSyncMobile(config)
    return _data_sync_mobile_instance

