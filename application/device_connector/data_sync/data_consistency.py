"""
数据一致性模块 - Mirexs数据同步系统

提供数据一致性保证功能，包括：
1. 版本向量
2. 一致性检查
3. 数据修复
4. 完整性验证
5. 快照管理
"""

import logging
import time
import json
import hashlib
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)

class ConsistencyLevel(Enum):
    """一致性级别枚举"""
    STRONG = "strong"          # 强一致性
    EVENTUAL = "eventual"       # 最终一致性
    WEAK = "weak"              # 弱一致性

class CheckResult(Enum):
    """检查结果枚举"""
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    MISSING = "missing"
    CORRUPT = "corrupt"
    CONFLICT = "conflict"

@dataclass
class VersionVector:
    """版本向量"""
    versions: Dict[str, int] = field(default_factory=dict)  # device_id -> version
    timestamp: float = field(default_factory=time.time)
    
    def increment(self, device_id: str):
        """增加版本"""
        self.versions[device_id] = self.versions.get(device_id, 0) + 1
        self.timestamp = time.time()
    
    def compare(self, other: 'VersionVector') -> int:
        """
        比较版本向量
        返回: -1 小于, 0 相等, 1 大于, 2 冲突
        """
        if self.versions == other.versions:
            return 0
        
        # 检查是否所有版本都小于等于对方
        self_less_or_equal = all(
            self.versions.get(k, 0) <= other.versions.get(k, 0)
            for k in set(self.versions.keys()) | set(other.versions.keys())
        )
        
        other_less_or_equal = all(
            other.versions.get(k, 0) <= self.versions.get(k, 0)
            for k in set(self.versions.keys()) | set(other.versions.keys())
        )
        
        if self_less_or_equal:
            return -1
        elif other_less_or_equal:
            return 1
        else:
            return 2  # 冲突

@dataclass
class DataItem:
    """数据项"""
    id: str
    collection: str
    data: Dict[str, Any]
    version_vector: VersionVector
    hash: str
    timestamp: float = field(default_factory=time.time)
    deleted: bool = False

@dataclass
class ConsistencyCheck:
    """一致性检查"""
    id: str
    collection: str
    start_time: float
    end_time: Optional[float] = None
    total_items: int = 0
    checked_items: int = 0
    consistent_items: int = 0
    inconsistent_items: int = 0
    missing_items: int = 0
    corrupt_items: int = 0
    conflict_items: int = 0
    status: str = "running"
    results: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class DataConsistencyConfig:
    """数据一致性配置"""
    # 检查配置
    check_interval: int = 3600  # 秒
    auto_check: bool = True
    
    # 修复配置
    auto_repair: bool = False
    repair_strategy: str = "latest"  # latest, majority, manual
    
    # 验证配置
    verify_on_read: bool = True
    verify_on_write: bool = True
    
    # 快照配置
    snapshot_interval: int = 86400  # 秒
    keep_snapshots: int = 7  # 保留天数

class DataConsistency:
    """
    数据一致性管理器
    
    负责保证数据的一致性。
    """
    
    def __init__(self, config: Optional[DataConsistencyConfig] = None):
        """
        初始化数据一致性管理器
        
        Args:
            config: 数据一致性配置
        """
        self.config = config or DataConsistencyConfig()
        
        # 数据存储
        self.data: Dict[str, Dict[str, DataItem]] = defaultdict(dict)  # collection -> {item_id: item}
        
        # 一致性检查
        self.checks: Dict[str, ConsistencyCheck] = {}
        
        # 快照
        self.snapshots: List[Dict[str, Any]] = []
        
        # 检查线程
        self._check_thread: Optional[threading.Thread] = None
        self._snapshot_thread: Optional[threading.Thread] = None
        self._stop_checking = threading.Event()
        
        # 回调函数
        self.on_check_started: Optional[Callable[[str], None]] = None
        self.on_check_completed: Optional[Callable[[ConsistencyCheck], None]] = None
        self.on_inconsistency_detected: Optional[Callable[[str, str, CheckResult], None]] = None
        self.on_data_repaired: Optional[Callable[[str, str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # 统计
        self.stats = {
            "checks_performed": 0,
            "inconsistencies_found": 0,
            "items_repaired": 0,
            "snapshots_created": 0,
            "errors": 0
        }
        
        # 启动检查
        if self.config.auto_check:
            self._start_checking()
        
        logger.info("DataConsistency initialized")
    
    def _start_checking(self):
        """启动一致性检查"""
        def check_loop():
            while not self._stop_checking.is_set():
                try:
                    self.run_consistency_check("system")
                    self._stop_checking.wait(self.config.check_interval)
                except Exception as e:
                    logger.error(f"Check error: {e}")
                    self.stats["errors"] += 1
        
        def snapshot_loop():
            while not self._stop_checking.is_set():
                try:
                    self.create_snapshot()
                    self._stop_checking.wait(self.config.snapshot_interval)
                except Exception as e:
                    logger.error(f"Snapshot error: {e}")
        
        self._check_thread = threading.Thread(target=check_loop, daemon=True)
        self._check_thread.start()
        
        self._snapshot_thread = threading.Thread(target=snapshot_loop, daemon=True)
        self._snapshot_thread.start()
        
        logger.debug("Consistency checking started")
    
    def add_item(self, collection: str, item_id: str, data: Dict[str, Any],
                device_id: str) -> DataItem:
        """
        添加数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            data: 数据
            device_id: 设备ID
        
        Returns:
            数据项
        """
        # 计算哈希
        data_hash = self._calculate_hash(data)
        
        # 创建版本向量
        version_vector = VersionVector()
        version_vector.increment(device_id)
        
        item = DataItem(
            id=item_id,
            collection=collection,
            data=data,
            version_vector=version_vector,
            hash=data_hash
        )
        
        self.data[collection][item_id] = item
        
        logger.debug(f"Item added: {collection}/{item_id}")
        
        return item
    
    def update_item(self, collection: str, item_id: str, data: Dict[str, Any],
                   device_id: str, version_vector: Optional[VersionVector] = None) -> Optional[DataItem]:
        """
        更新数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            data: 新数据
            device_id: 设备ID
            version_vector: 版本向量
        
        Returns:
            更新后的数据项
        """
        if collection not in self.data or item_id not in self.data[collection]:
            logger.warning(f"Item not found: {collection}/{item_id}")
            return None
        
        item = self.data[collection][item_id]
        
        # 验证版本
        if version_vector:
            compare_result = item.version_vector.compare(version_vector)
            
            if compare_result == 2:  # 冲突
                logger.warning(f"Version conflict for {collection}/{item_id}")
                self.stats["inconsistencies_found"] += 1
                
                if self.on_inconsistency_detected:
                    self.on_inconsistency_detected(collection, item_id, CheckResult.CONFLICT)
                
                # 根据策略处理
                if self.config.auto_repair:
                    return self._resolve_conflict(collection, item_id, item, data, device_id)
                else:
                    return None
        
        # 更新数据
        item.data = data
        item.version_vector.increment(device_id)
        item.hash = self._calculate_hash(data)
        item.timestamp = time.time()
        
        logger.debug(f"Item updated: {collection}/{item_id} (v{item.version_vector.versions})")
        
        return item
    
    def delete_item(self, collection: str, item_id: str, device_id: str) -> bool:
        """
        删除数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            device_id: 设备ID
        
        Returns:
            是否成功
        """
        if collection not in self.data or item_id not in self.data[collection]:
            return False
        
        item = self.data[collection][item_id]
        item.deleted = True
        item.version_vector.increment(device_id)
        item.timestamp = time.time()
        
        logger.debug(f"Item deleted: {collection}/{item_id}")
        
        return True
    
    def get_item(self, collection: str, item_id: str,
                verify: bool = True) -> Optional[DataItem]:
        """
        获取数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            verify: 是否验证
        
        Returns:
            数据项
        """
        if collection not in self.data or item_id not in self.data[collection]:
            return None
        
        item = self.data[collection][item_id]
        
        if verify and self.config.verify_on_read:
            if not self.verify_item(collection, item_id):
                logger.warning(f"Item verification failed: {collection}/{item_id}")
                return None
        
        return item if not item.deleted else None
    
    def verify_item(self, collection: str, item_id: str) -> bool:
        """
        验证数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
        
        Returns:
            是否有效
        """
        if collection not in self.data or item_id not in self.data[collection]:
            return False
        
        item = self.data[collection][item_id]
        
        # 验证哈希
        current_hash = self._calculate_hash(item.data)
        if current_hash != item.hash:
            logger.warning(f"Hash mismatch for {collection}/{item_id}")
            return False
        
        return True
    
    def _calculate_hash(self, data: Dict[str, Any]) -> str:
        """计算数据哈希"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _resolve_conflict(self, collection: str, item_id: str,
                         local_item: DataItem, remote_data: Dict[str, Any],
                         device_id: str) -> Optional[DataItem]:
        """解决冲突"""
        strategy = self.config.repair_strategy
        
        if strategy == "latest":
            # 使用时间戳最新的
            if local_item.timestamp >= time.time():
                return local_item
            else:
                return self.update_item(collection, item_id, remote_data, device_id)
        
        elif strategy == "majority":
            # 这里简化处理，返回本地
            return local_item
        
        return None
    
    def run_consistency_check(self, name: str) -> str:
        """
        运行一致性检查
        
        Args:
            name: 检查名称
        
        Returns:
            检查ID
        """
        check_id = f"check_{int(time.time())}_{name}"
        
        check = ConsistencyCheck(
            id=check_id,
            collection="all",
            start_time=time.time()
        )
        
        self.checks[check_id] = check
        self.stats["checks_performed"] += 1
        
        logger.info(f"Starting consistency check: {name}")
        
        if self.on_check_started:
            self.on_check_started(check_id)
        
        # 在后台线程中执行检查
        def run_check():
            try:
                total_items = 0
                checked = 0
                consistent = 0
                inconsistent = 0
                missing = 0
                corrupt = 0
                conflict = 0
                
                for collection, items in self.data.items():
                    for item_id, item in items.items():
                        total_items += 1
                        
                        # 验证项目
                        if self.verify_item(collection, item_id):
                            consistent += 1
                        else:
                            corrupt += 1
                            inconsistent += 1
                            
                            if self.on_inconsistency_detected:
                                self.on_inconsistency_detected(collection, item_id, CheckResult.CORRUPT)
                        
                        checked += 1
                        
                        # 记录结果
                        check.results.append({
                            "collection": collection,
                            "item_id": item_id,
                            "result": CheckResult.CONSISTENT.value if self.verify_item(collection, item_id) else CheckResult.CORRUPT.value
                        })
                
                check.end_time = time.time()
                check.total_items = total_items
                check.checked_items = checked
                check.consistent_items = consistent
                check.corrupt_items = corrupt
                check.inconsistent_items = inconsistent
                check.status = "completed"
                
                self.stats["inconsistencies_found"] += inconsistent
                
                logger.info(f"Consistency check completed: {consistent} consistent, {inconsistent} inconsistent")
                
                if self.on_check_completed:
                    self.on_check_completed(check)
                
            except Exception as e:
                check.status = "failed"
                check.end_time = time.time()
                logger.error(f"Consistency check failed: {e}")
        
        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()
        
        return check_id
    
    def repair_item(self, collection: str, item_id: str,
                   source: str = "latest") -> bool:
        """
        修复数据项
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            source: 修复源
        
        Returns:
            是否成功
        """
        if collection not in self.data or item_id not in self.data[collection]:
            logger.warning(f"Item not found: {collection}/{item_id}")
            return False
        
        item = self.data[collection][item_id]
        
        # 重新计算哈希
        new_hash = self._calculate_hash(item.data)
        item.hash = new_hash
        
        self.stats["items_repaired"] += 1
        
        logger.info(f"Item repaired: {collection}/{item_id}")
        
        if self.on_data_repaired:
            self.on_data_repaired(collection, item_id)
        
        return True
    
    def create_snapshot(self) -> str:
        """
        创建数据快照
        
        Returns:
            快照ID
        """
        snapshot_id = f"snapshot_{int(time.time())}"
        
        snapshot = {
            "id": snapshot_id,
            "timestamp": time.time(),
            "data": {}
        }
        
        # 复制数据
        for collection, items in self.data.items():
            snapshot["data"][collection] = {}
            for item_id, item in items.items():
                snapshot["data"][collection][item_id] = {
                    "id": item.id,
                    "data": item.data,
                    "version_vector": item.version_vector.versions,
                    "hash": item.hash,
                    "timestamp": item.timestamp,
                    "deleted": item.deleted
                }
        
        self.snapshots.append(snapshot)
        self.stats["snapshots_created"] += 1
        
        # 清理旧快照
        if self.config.keep_snapshots > 0:
            cutoff = time.time() - (self.config.keep_snapshots * 86400)
            self.snapshots = [s for s in self.snapshots if s["timestamp"] >= cutoff]
        
        logger.info(f"Snapshot created: {snapshot_id}")
        
        return snapshot_id
    
    def restore_from_snapshot(self, snapshot_id: str) -> bool:
        """
        从快照恢复
        
        Args:
            snapshot_id: 快照ID
        
        Returns:
            是否成功
        """
        for snapshot in self.snapshots:
            if snapshot["id"] == snapshot_id:
                # 恢复数据
                self.data.clear()
                
                for collection, items in snapshot["data"].items():
                    self.data[collection] = {}
                    for item_id, item_data in items.items():
                        version_vector = VersionVector()
                        version_vector.versions = item_data["version_vector"]
                        
                        item = DataItem(
                            id=item_data["id"],
                            collection=collection,
                            data=item_data["data"],
                            version_vector=version_vector,
                            hash=item_data["hash"],
                            timestamp=item_data["timestamp"],
                            deleted=item_data["deleted"]
                        )
                        self.data[collection][item_id] = item
                
                logger.info(f"Restored from snapshot: {snapshot_id}")
                return True
        
        logger.warning(f"Snapshot not found: {snapshot_id}")
        return False
    
    def get_check(self, check_id: str) -> Optional[ConsistencyCheck]:
        """获取检查结果"""
        return self.checks.get(check_id)
    
    def get_snapshots(self) -> List[Dict[str, Any]]:
        """获取快照列表"""
        return self.snapshots
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取数据一致性管理器状态
        
        Returns:
            状态字典
        """
        return {
            "data": {
                "collections": len(self.data),
                "total_items": sum(len(items) for items in self.data.values())
            },
            "checks": {
                "total": len(self.checks),
                "recent": list(self.checks.keys())[-5:]
            },
            "snapshots": len(self.snapshots),
            "stats": self.stats,
            "config": {
                "auto_check": self.config.auto_check,
                "auto_repair": self.config.auto_repair,
                "verify_on_read": self.config.verify_on_read
            }
        }
    
    def shutdown(self):
        """关闭数据一致性管理器"""
        logger.info("Shutting down DataConsistency...")
        
        self._stop_checking.set()
        
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=2)
        
        if self._snapshot_thread and self._snapshot_thread.is_alive():
            self._snapshot_thread.join(timeout=2)
        
        self.data.clear()
        self.checks.clear()
        self.snapshots.clear()
        
        logger.info("DataConsistency shutdown completed")

# 单例模式实现
_data_consistency_instance: Optional[DataConsistency] = None

def get_data_consistency(config: Optional[DataConsistencyConfig] = None) -> DataConsistency:
    """
    获取数据一致性管理器单例
    
    Args:
        config: 数据一致性配置
    
    Returns:
        数据一致性管理器实例
    """
    global _data_consistency_instance
    if _data_consistency_instance is None:
        _data_consistency_instance = DataConsistency(config)
    return _data_consistency_instance

