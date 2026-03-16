"""
同步引擎：多设备数据同步
负责多设备间的数据同步和状态一致性
"""

import asyncio
import hashlib
import json
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
from cryptography.fernet import Fernet

class SyncOperation(Enum):
    """同步操作枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"
    CONFLICT_RESOLVE = "conflict_resolve"

class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"

@dataclass
class SyncItem:
    """同步项"""
    item_id: str
    data_type: str
    data: Dict[str, Any]
    version: int
    device_id: str
    timestamp: datetime
    operation: SyncOperation
    checksum: str

@dataclass
class SyncConflict:
    """同步冲突"""
    conflict_id: str
    item_id: str
    local_version: SyncItem
    remote_version: SyncItem
    detected_at: datetime
    resolved: bool = False

class SyncEngine:
    """同步引擎"""
    
    def __init__(self):
        self.sync_queue: asyncio.Queue = asyncio.Queue()
        self.sync_history: List[SyncItem] = []
        self.conflicts: Dict[str, SyncConflict] = {}
        self.connected_devices: Set[str] = set()
        self.sync_task: Optional[asyncio.Task] = None
        self.encryption_key: Optional[bytes] = None
        self.fernet: Optional[Fernet] = None
        self.device_id = self._generate_device_id()
        self.initialized = False
        
    def _generate_device_id(self) -> str:
        """生成设备ID"""
        import socket
        hostname = socket.gethostname()
        return hashlib.md5(hostname.encode()).hexdigest()[:8]
    
    async def initialize(self, encryption_key: str = None):
        """初始化同步引擎"""
        if self.initialized:
            return
            
        logging.info("初始化同步引擎...")
        
        # 设置加密
        if encryption_key:
            self.encryption_key = encryption_key.encode()
            self.fernet = Fernet(self.encryption_key)
        else:
            # 生成随机密钥
            self.encryption_key = Fernet.generate_key()
            self.fernet = Fernet(self.encryption_key)
        
        # 启动同步任务
        self.sync_task = asyncio.create_task(self._sync_processor())
        
        self.initialized = True
        logging.info(f"同步引擎初始化完成，设备ID: {self.device_id}")
    
    async def _sync_processor(self):
        """同步处理循环"""
        while True:
            try:
                sync_item = await self.sync_queue.get()
                await self._process_sync_item(sync_item)
                self.sync_queue.task_done()
                
            except Exception as e:
                logging.error(f"同步处理错误: {e}")
    
    async def _process_sync_item(self, item: SyncItem):
        """处理同步项"""
        try:
            logging.debug(f"处理同步项: {item.item_id} - {item.operation.value}")
            
            # 检查冲突
            conflict = await self._detect_conflict(item)
            if conflict:
                await self._handle_conflict(conflict)
                return
            
            # 执行同步操作
            if item.operation == SyncOperation.CREATE:
                await self._create_item(item)
            elif item.operation == SyncOperation.UPDATE:
                await self._update_item(item)
            elif item.operation == SyncOperation.DELETE:
                await self._delete_item(item)
            elif item.operation == SyncOperation.SYNC:
                await self._sync_item(item)
            
            # 记录到历史
            self.sync_history.append(item)
            
            # 限制历史记录大小
            if len(self.sync_history) > 1000:
                self.sync_history.pop(0)
                
            logging.debug(f"同步项处理完成: {item.item_id}")
            
        except Exception as e:
            logging.error(f"同步项处理失败 {item.item_id}: {e}")
            item.operation = SyncOperation.CONFLICT_RESOLVE
    
    async def _detect_conflict(self, new_item: SyncItem) -> Optional[SyncConflict]:
        """检测同步冲突"""
        # 查找相同项的现有版本
        existing_items = [
            item for item in self.sync_history
            if item.item_id == new_item.item_id and item.data_type == new_item.data_type
        ]
        
        if not existing_items:
            return None
        
        latest_item = max(existing_items, key=lambda x: x.version)
        
        # 如果新版本不高于当前版本，检测到冲突
        if new_item.version <= latest_item.version and new_item.device_id != latest_item.device_id:
            conflict = SyncConflict(
                conflict_id=f"conflict_{len(self.conflicts) + 1}",
                item_id=new_item.item_id,
                local_version=latest_item,
                remote_version=new_item,
                detected_at=datetime.now()
            )
            
            self.conflicts[conflict.conflict_id] = conflict
            return conflict
        
        return None
    
    async def _handle_conflict(self, conflict: SyncConflict):
        """处理同步冲突"""
        logging.warning(f"检测到同步冲突: {conflict.item_id}")
        
        # 默认策略：使用最新时间戳的版本
        local_time = conflict.local_version.timestamp
        remote_time = conflict.remote_version.timestamp
        
        if remote_time > local_time:
            winning_item = conflict.remote_version
            logging.info(f"冲突解决: 使用远程版本 (时间戳更新)")
        else:
            winning_item = conflict.local_version
            logging.info(f"冲突解决: 使用本地版本 (时间戳更新)")
        
        # 创建解决项
        resolve_item = SyncItem(
            item_id=winning_item.item_id,
            data_type=winning_item.data_type,
            data=winning_item.data,
            version=winning_item.version + 1,  # 增加版本号
            device_id=self.device_id,
            timestamp=datetime.now(),
            operation=SyncOperation.CONFLICT_RESOLVE,
            checksum=self._calculate_checksum(winning_item.data)
        )
        
        # 重新加入同步队列
        await self.sync_queue.put(resolve_item)
        
        conflict.resolved = True
    
    async def _create_item(self, item: SyncItem):
        """创建数据项"""
        # 在实际实现中，这里会保存到数据库或文件系统
        logging.debug(f"创建数据项: {item.item_id}")
    
    async def _update_item(self, item: SyncItem):
        """更新数据项"""
        logging.debug(f"更新数据项: {item.item_id}")
    
    async def _delete_item(self, item: SyncItem):
        """删除数据项"""
        logging.debug(f"删除数据项: {item.item_id}")
    
    async def _sync_item(self, item: SyncItem):
        """同步数据项"""
        logging.debug(f"同步数据项: {item.item_id}")
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """计算数据校验和"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """加密数据"""
        if not self.fernet:
            return json.dumps(data)
        
        data_str = json.dumps(data)
        encrypted = self.fernet.encrypt(data_str.encode())
        return encrypted.decode()
    
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """解密数据"""
        if not self.fernet:
            return json.loads(encrypted_data)
        
        decrypted = self.fernet.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
    
    async def queue_sync_item(self, data_type: str, data: Dict[str, Any], 
                            operation: SyncOperation, item_id: str = None) -> str:
        """排队同步项"""
        if item_id is None:
            item_id = f"{data_type}_{int(datetime.now().timestamp())}"
        
        # 计算版本号（基于时间戳）
        version = int(datetime.now().timestamp())
        
        sync_item = SyncItem(
            item_id=item_id,
            data_type=data_type,
            data=data,
            version=version,
            device_id=self.device_id,
            timestamp=datetime.now(),
            operation=operation,
            checksum=self._calculate_checksum(data)
        )
        
        await self.sync_queue.put(sync_item)
        logging.debug(f"同步项已排队: {item_id} - {operation.value}")
        
        return item_id
    
    async def sync_with_device(self, device_id: str, sync_data: List[SyncItem]) -> List[SyncItem]:
        """与设备同步数据"""
        logging.info(f"开始与设备同步: {device_id}")
        
        # 添加设备到连接列表
        self.connected_devices.add(device_id)
        
        # 处理传入的同步数据
        for item in sync_data:
            await self.sync_queue.put(item)
        
        # 生成需要发送的同步数据
        outgoing_items = [
            item for item in self.sync_history[-100:]  # 最近100个项
            if item.device_id == self.device_id
        ]
        
        logging.info(f"同步完成: 接收 {len(sync_data)} 项, 发送 {len(outgoing_items)} 项")
        return outgoing_items
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        operation_counts = {}
        for item in self.sync_history:
            op = item.operation.value
            operation_counts[op] = operation_counts.get(op, 0) + 1
        
        unresolved_conflicts = sum(1 for conflict in self.conflicts.values() if not conflict.resolved)
        
        return {
            "device_id": self.device_id,
            "queue_size": self.sync_queue.qsize(),
            "total_sync_items": len(self.sync_history),
            "operation_distribution": operation_counts,
            "connected_devices": list(self.connected_devices),
            "total_conflicts": len(self.conflicts),
            "unresolved_conflicts": unresolved_conflicts
        }
    
    async def wait_for_sync_completion(self, timeout: float = 30.0) -> bool:
        """等待同步完成"""
        try:
            await asyncio.wait_for(self.sync_queue.join(), timeout)
            return True
        except asyncio.TimeoutError:
            logging.warning("同步完成等待超时")
            return False

# 全局同步引擎实例
sync_engine = SyncEngine()