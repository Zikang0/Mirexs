"""
离线支持模块 - Mirexs移动应用程序

提供离线功能支持，包括：
1. 离线数据存储和同步
2. 网络状态监测
3. 操作队列管理
4. 冲突解决
5. 数据一致性保证
"""

import logging
import time
import json
import os
import threading
import sqlite3
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Queue, PriorityQueue
import hashlib

logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    CANCELLED = "cancelled"

class NetworkStatus(Enum):
    """网络状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    WIFI = "wifi"
    CELLULAR = "cellular"
    UNKNOWN = "unknown"

class ConflictResolution(Enum):
    """冲突解决策略枚举"""
    CLIENT_WINS = "client_wins"
    SERVER_WINS = "server_wins"
    MANUAL = "manual"
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"

@dataclass
class SyncOperation:
    """同步操作"""
    id: str
    type: str  # create, update, delete
    entity_type: str
    entity_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: int = 5  # 1-10, 1最高
    retry_count: int = 0
    max_retries: int = 3
    status: SyncStatus = SyncStatus.PENDING
    error: Optional[str] = None
    conflict_data: Optional[Dict[str, Any]] = None

@dataclass
class OfflineQueue:
    """离线队列"""
    id: str
    name: str
    operations: List[SyncOperation] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_sync: Optional[float] = None
    size: int = 0

@dataclass
class OfflineSupportConfig:
    """离线支持配置"""
    # 同步配置
    auto_sync: bool = True
    sync_interval: int = 300  # 秒
    sync_on_wifi_only: bool = False
    batch_size: int = 50
    
    # 队列配置
    max_queue_size: int = 10000
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    
    # 冲突解决
    default_conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    
    # 存储配置
    db_path: str = "data/offline/mirexs_offline.db"
    use_encryption: bool = True
    encryption_key: Optional[str] = None
    
    # 文件路径
    data_dir: str = "data/offline/"

class OfflineSupport:
    """
    离线支持管理器
    
    负责管理应用的离线功能，包括：
    - 网络状态监测
    - 操作队列管理
    - 数据同步
    - 冲突解决
    - 本地存储
    """
    
    def __init__(self, config: Optional[OfflineSupportConfig] = None):
        """
        初始化离线支持管理器
        
        Args:
            config: 离线支持配置
        """
        self.config = config or OfflineSupportConfig()
        
        # 网络状态
        self.network_status = NetworkStatus.UNKNOWN
        self._network_listeners: List[Callable[[NetworkStatus], None]] = []
        
        # 同步队列
        self.sync_queue: PriorityQueue = PriorityQueue()
        self.pending_operations: Dict[str, SyncOperation] = {}
        self.completed_operations: List[SyncOperation] = []
        
        # 同步状态
        self.is_syncing = False
        self.last_sync_time: Optional[float] = None
        self.sync_stats: Dict[str, Any] = {
            "total_synced": 0,
            "total_failed": 0,
            "total_conflicts": 0
        }
        
        # 数据库连接
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # 同步线程
        self.sync_thread: Optional[threading.Thread] = None
        self.stop_sync = threading.Event()
        
        # 回调函数
        self.on_sync_started: Optional[Callable[[], None]] = None
        self.on_sync_completed: Optional[Callable[[int, int], None]] = None  # success, failed
        self.on_operation_completed: Optional[Callable[[SyncOperation], None]] = None
        self.on_conflict_detected: Optional[Callable[[SyncOperation, Dict[str, Any]], ConflictResolution]] = None
        
        # 创建数据目录
        self._ensure_data_directory()
        
        # 初始化数据库
        self._init_database()
        
        # 开始网络监测
        self._start_network_monitoring()
        
        logger.info("OfflineSupport initialized")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.config.db_path), exist_ok=True)
        os.makedirs(self.config.data_dir, exist_ok=True)
    
    def _init_database(self):
        """初始化SQLite数据库"""
        try:
            self.db_connection = sqlite3.connect(self.config.db_path, check_same_thread=False)
            cursor = self.db_connection.cursor()
            
            # 创建操作表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_operations (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    priority INTEGER NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    status TEXT NOT NULL,
                    error TEXT,
                    conflict_data TEXT
                )
            ''')
            
            # 创建实体缓存表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entity_cache (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    last_updated REAL NOT NULL,
                    sync_status TEXT DEFAULT 'synced',
                    PRIMARY KEY (entity_type, entity_id)
                )
            ''')
            
            # 创建同步历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_history (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    operations_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    failed_count INTEGER NOT NULL,
                    duration REAL NOT NULL
                )
            ''')
            
            self.db_connection.commit()
            logger.info("Offline database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def _start_network_monitoring(self):
        """开始网络状态监测"""
        def monitor_network():
            while not self.stop_sync.is_set():
                old_status = self.network_status
                self.network_status = self._check_network_status()
                
                if old_status != self.network_status:
                    logger.info(f"Network status changed: {old_status.value} -> {self.network_status.value}")
                    
                    # 通知监听器
                    for listener in self._network_listeners:
                        try:
                            listener(self.network_status)
                        except Exception as e:
                            logger.error(f"Error in network listener: {e}")
                    
                    # 如果网络恢复，开始同步
                    if self.network_status in [NetworkStatus.ONLINE, NetworkStatus.WIFI] and self.config.auto_sync:
                        self.start_sync()
                
                time.sleep(10)  # 每10秒检查一次
        
        thread = threading.Thread(target=monitor_network, daemon=True)
        thread.start()
        logger.debug("Network monitoring started")
    
    def _check_network_status(self) -> NetworkStatus:
        """
        检查网络状态
        
        Returns:
            网络状态
        """
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            
            # 检查是否是WiFi（移动端通过原生代码获取）
            # 这里简化处理
            return NetworkStatus.ONLINE
        except OSError:
            return NetworkStatus.OFFLINE
    
    def add_operation(self, operation: SyncOperation) -> str:
        """
        添加同步操作到队列
        
        Args:
            operation: 同步操作
        
        Returns:
            操作ID
        """
        # 生成ID（如果未提供）
        if not operation.id:
            import uuid
            operation.id = str(uuid.uuid4())
        
        # 设置状态
        operation.status = SyncStatus.PENDING
        operation.timestamp = time.time()
        
        # 添加到队列
        self.pending_operations[operation.id] = operation
        self.sync_queue.put((operation.priority, operation.timestamp, operation.id))
        
        # 保存到数据库
        self._save_operation_to_db(operation)
        
        logger.debug(f"Operation added to queue: {operation.id} ({operation.type})")
        
        # 如果自动同步开启且网络在线，立即开始同步
        if self.config.auto_sync and self.network_status != NetworkStatus.OFFLINE:
            self.start_sync()
        
        return operation.id
    
    def _save_operation_to_db(self, operation: SyncOperation):
        """保存操作到数据库"""
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sync_operations 
                (id, type, entity_type, entity_id, data, timestamp, priority, 
                 retry_count, max_retries, status, error, conflict_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                operation.id, operation.type, operation.entity_type, operation.entity_id,
                json.dumps(operation.data), operation.timestamp, operation.priority,
                operation.retry_count, operation.max_retries, operation.status.value,
                operation.error, json.dumps(operation.conflict_data) if operation.conflict_data else None
            ))
            self.db_connection.commit()
        except Exception as e:
            logger.error(f"Error saving operation to database: {e}")
    
    def cache_entity(self, entity_type: str, entity_id: str, data: Dict[str, Any]):
        """
        缓存实体数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            data: 实体数据
        """
        try:
            cursor = self.db_connection.cursor()
            
            # 检查是否存在
            cursor.execute('''
                SELECT version FROM entity_cache 
                WHERE entity_type = ? AND entity_id = ?
            ''', (entity_type, entity_id))
            
            result = cursor.fetchone()
            version = 1
            if result:
                version = result[0] + 1
            
            cursor.execute('''
                INSERT OR REPLACE INTO entity_cache 
                (entity_type, entity_id, data, version, last_updated, sync_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                entity_type, entity_id, json.dumps(data), version, 
                time.time(), 'synced'
            ))
            self.db_connection.commit()
            
            logger.debug(f"Entity cached: {entity_type}/{entity_id} (v{version})")
            
        except Exception as e:
            logger.error(f"Error caching entity: {e}")
    
    def get_cached_entity(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的实体数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体ID
        
        Returns:
            实体数据，不存在返回None
        """
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                SELECT data FROM entity_cache 
                WHERE entity_type = ? AND entity_id = ?
            ''', (entity_type, entity_id))
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            
        except Exception as e:
            logger.error(f"Error getting cached entity: {e}")
        
        return None
    
    def get_all_cached(self, entity_type: str) -> List[Dict[str, Any]]:
        """
        获取指定类型的所有缓存实体
        
        Args:
            entity_type: 实体类型
        
        Returns:
            实体列表
        """
        try:
            cursor = self.db_connection.cursor()
            cursor.execute('''
                SELECT entity_id, data FROM entity_cache 
                WHERE entity_type = ?
            ''', (entity_type,))
            
            results = []
            for entity_id, data in cursor.fetchall():
                entity_data = json.loads(data)
                entity_data['id'] = entity_id
                results.append(entity_data)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting cached entities: {e}")
            return []
    
    def start_sync(self):
        """开始同步"""
        if self.is_syncing:
            logger.debug("Sync already in progress")
            return
        
        if self.network_status == NetworkStatus.OFFLINE:
            logger.warning("Cannot sync: device is offline")
            return
        
        if self.config.sync_on_wifi_only and self.network_status != NetworkStatus.WIFI:
            logger.info("Sync deferred: waiting for WiFi")
            return
        
        if self.sync_queue.empty():
            logger.debug("No operations to sync")
            return
        
        self.is_syncing = True
        logger.info("Sync started")
        
        if self.on_sync_started:
            self.on_sync_started()
        
        def sync_worker():
            try:
                success_count = 0
                failed_count = 0
                start_time = time.time()
                
                batch = []
                while not self.sync_queue.empty() and len(batch) < self.config.batch_size:
                    try:
                        priority, timestamp, op_id = self.sync_queue.get_nowait()
                        if op_id in self.pending_operations:
                            batch.append(self.pending_operations[op_id])
                    except:
                        break
                
                for operation in batch:
                    result = self._sync_operation(operation)
                    if result:
                        success_count += 1
                        self.pending_operations.pop(operation.id, None)
                    else:
                        failed_count += 1
                    
                    if operation.retry_count >= operation.max_retries:
                        self.pending_operations.pop(operation.id, None)
                
                duration = time.time() - start_time
                
                # 更新统计
                self.sync_stats["total_synced"] += success_count
                self.sync_stats["total_failed"] += failed_count
                self.last_sync_time = time.time()
                
                logger.info(f"Sync completed: {success_count} succeeded, {failed_count} failed in {duration:.2f}s")
                
                if self.on_sync_completed:
                    self.on_sync_completed(success_count, failed_count)
                
                # 如果有更多操作，继续同步
                if not self.sync_queue.empty():
                    self.start_sync()
                
            except Exception as e:
                logger.error(f"Error during sync: {e}")
            finally:
                self.is_syncing = False
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
    
    def _sync_operation(self, operation: SyncOperation) -> bool:
        """
        同步单个操作
        
        Args:
            operation: 同步操作
        
        Returns:
            是否成功
        """
        logger.debug(f"Syncing operation: {operation.id}")
        
        try:
            operation.status = SyncStatus.SYNCING
            self._save_operation_to_db(operation)
            
            # 这里应该调用实际的API进行同步
            # 简化实现，假设总是成功
            success = self._execute_sync(operation)
            
            if success:
                operation.status = SyncStatus.COMPLETED
                self.completed_operations.append(operation)
                
                if self.on_operation_completed:
                    self.on_operation_completed(operation)
                
                logger.debug(f"Operation synced successfully: {operation.id}")
                return True
            else:
                operation.retry_count += 1
                if operation.retry_count < operation.max_retries:
                    operation.status = SyncStatus.PENDING
                    # 重新加入队列
                    self.sync_queue.put((operation.priority, time.time(), operation.id))
                    logger.debug(f"Operation will be retried: {operation.id} (attempt {operation.retry_count})")
                else:
                    operation.status = SyncStatus.FAILED
                    logger.error(f"Operation failed after {operation.max_retries} attempts: {operation.id}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error syncing operation {operation.id}: {e}")
            operation.error = str(e)
            operation.status = SyncStatus.FAILED
            return False
        finally:
            self._save_operation_to_db(operation)
    
    def _execute_sync(self, operation: SyncOperation) -> bool:
        """
        执行实际同步操作
        
        Args:
            operation: 同步操作
        
        Returns:
            是否成功
        """
        # 这里应该实现实际的API调用
        # 简化实现，模拟网络请求
        import random
        time.sleep(0.5)  # 模拟网络延迟
        return random.random() > 0.1  # 90%成功率
    
    def resolve_conflict(self, operation: SyncOperation, server_data: Dict[str, Any]) -> ConflictResolution:
        """
        解决冲突
        
        Args:
            operation: 本地操作
            server_data: 服务器数据
        
        Returns:
            冲突解决策略
        """
        self.sync_stats["total_conflicts"] += 1
        
        # 如果有自定义冲突处理器
        if self.on_conflict_detected:
            resolution = self.on_conflict_detected(operation, server_data)
            if resolution:
                return resolution
        
        # 使用默认策略
        return self.config.default_conflict_resolution
    
    def get_pending_operations(self) -> List[SyncOperation]:
        """
        获取待处理操作
        
        Returns:
            待处理操作列表
        """
        return list(self.pending_operations.values())
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态
        
        Returns:
            同步状态字典
        """
        return {
            "network_status": self.network_status.value,
            "is_syncing": self.is_syncing,
            "pending_count": len(self.pending_operations),
            "completed_count": len(self.completed_operations),
            "last_sync": self.last_sync_time,
            "stats": self.sync_stats,
            "queue_size": self.sync_queue.qsize()
        }
    
    def add_network_listener(self, listener: Callable[[NetworkStatus], None]):
        """
        添加网络状态监听器
        
        Args:
            listener: 监听函数
        """
        self._network_listeners.append(listener)
    
    def remove_network_listener(self, listener: Callable[[NetworkStatus], None]):
        """
        移除网络状态监听器
        
        Args:
            listener: 监听函数
        """
        if listener in self._network_listeners:
            self._network_listeners.remove(listener)
    
    def clear_queue(self):
        """清空队列"""
        while not self.sync_queue.empty():
            try:
                self.sync_queue.get_nowait()
            except:
                break
        
        self.pending_operations.clear()
        logger.info("Sync queue cleared")
    
    def shutdown(self):
        """关闭离线支持管理器"""
        logger.info("Shutting down OfflineSupport...")
        
        self.stop_sync.set()
        
        # 等待同步完成
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        
        # 关闭数据库连接
        if self.db_connection:
            self.db_connection.close()
        
        logger.info("OfflineSupport shutdown completed")

# 单例模式实现
_offline_support_instance: Optional[OfflineSupport] = None

def get_offline_support(config: Optional[OfflineSupportConfig] = None) -> OfflineSupport:
    """
    获取离线支持管理器单例
    
    Args:
        config: 离线支持配置
    
    Returns:
        离线支持管理器实例
    """
    global _offline_support_instance
    if _offline_support_instance is None:
        _offline_support_instance = OfflineSupport(config)
    return _offline_support_instance

