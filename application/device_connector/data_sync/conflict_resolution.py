"""
冲突解决模块 - Mirexs数据同步系统

提供数据冲突解决功能，包括：
1. 冲突检测
2. 冲突策略
3. 自动解决
4. 手动解决
5. 冲突历史
"""

import logging
import time
import json
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)

class ConflictStrategy(Enum):
    """冲突解决策略枚举"""
    CLIENT_WINS = "client_wins"      # 客户端优先
    SERVER_WINS = "server_wins"      # 服务端优先
    LAST_WRITE_WINS = "last_write_wins"  # 最后写入优先
    MANUAL = "manual"                 # 手动解决
    MERGE = "merge"                   # 合并
    IGNORE = "ignore"                 # 忽略

class ConflictType(Enum):
    """冲突类型枚举"""
    CREATE_CREATE = "create_create"    # 双方都创建
    UPDATE_UPDATE = "update_update"    # 双方都更新
    DELETE_UPDATE = "delete_update"    # 一方删除一方更新
    DELETE_DELETE = "delete_delete"    # 双方都删除

class ConflictStatus(Enum):
    """冲突状态枚举"""
    DETECTED = "detected"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    FAILED = "failed"

@dataclass
class ConflictRecord:
    """冲突记录"""
    id: str
    type: ConflictType
    collection: str
    item_id: str
    local_version: int
    remote_version: int
    local_data: Optional[Dict[str, Any]] = None
    remote_data: Optional[Dict[str, Any]] = None
    strategy: Optional[ConflictStrategy] = None
    status: ConflictStatus = ConflictStatus.DETECTED
    resolved_data: Optional[Dict[str, Any]] = None
    detected_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConflictConfig:
    """冲突解决配置"""
    # 默认策略
    default_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS
    
    # 策略映射
    strategy_by_collection: Dict[str, ConflictStrategy] = field(default_factory=dict)
    strategy_by_type: Dict[ConflictType, ConflictStrategy] = field(default_factory=dict)
    
    # 自动解决
    auto_resolve: bool = True
    max_auto_resolve_attempts: int = 3
    
    # 合并配置
    merge_fields: List[str] = field(default_factory=list)  # 指定合并的字段
    prefer_local_fields: List[str] = field(default_factory=list)  # 优先使用本地的字段
    prefer_remote_fields: List[str] = field(default_factory=list)  # 优先使用远程的字段
    
    # 历史记录
    keep_history: bool = True
    max_history: int = 1000

class ConflictResolution:
    """
    冲突解决管理器
    
    负责数据同步中的冲突检测和解决。
    """
    
    def __init__(self, config: Optional[ConflictConfig] = None):
        """
        初始化冲突解决管理器
        
        Args:
            config: 冲突解决配置
        """
        self.config = config or ConflictConfig()
        
        # 冲突记录
        self.conflicts: Dict[str, ConflictRecord] = {}
        self.resolved_conflicts: List[ConflictRecord] = []
        
        # 回调函数
        self.on_conflict_detected: Optional[Callable[[ConflictRecord], None]] = None
        self.on_conflict_resolved: Optional[Callable[[ConflictRecord], None]] = None
        self.on_resolution_failed: Optional[Callable[[str, str], None]] = None
        
        # 统计
        self.stats = {
            "total_conflicts": 0,
            "auto_resolved": 0,
            "manually_resolved": 0,
            "ignored": 0,
            "failed": 0
        }
        
        logger.info("ConflictResolution initialized")
    
    def detect_conflict(self, collection: str, item_id: str,
                       local_version: int, remote_version: int,
                       local_data: Optional[Dict[str, Any]] = None,
                       remote_data: Optional[Dict[str, Any]] = None) -> Optional[ConflictRecord]:
        """
        检测冲突
        
        Args:
            collection: 集合名称
            item_id: 项目ID
            local_version: 本地版本
            remote_version: 远程版本
            local_data: 本地数据
            remote_data: 远程数据
        
        Returns:
            冲突记录
        """
        # 确定冲突类型
        conflict_type = self._determine_conflict_type(
            local_data is not None, remote_data is not None,
            local_data is not None and local_data.get("_deleted", False),
            remote_data is not None and remote_data.get("_deleted", False)
        )
        
        conflict = ConflictRecord(
            id=str(uuid.uuid4()),
            type=conflict_type,
            collection=collection,
            item_id=item_id,
            local_version=local_version,
            remote_version=remote_version,
            local_data=local_data,
            remote_data=remote_data,
            status=ConflictStatus.DETECTED
        )
        
        self.conflicts[conflict.id] = conflict
        self.stats["total_conflicts"] += 1
        
        logger.info(f"Conflict detected: {collection}/{item_id} ({conflict_type.value})")
        
        if self.on_conflict_detected:
            self.on_conflict_detected(conflict)
        
        # 自动解决
        if self.config.auto_resolve:
            self.auto_resolve(conflict.id)
        
        return conflict
    
    def _determine_conflict_type(self, local_exists: bool, remote_exists: bool,
                                 local_deleted: bool, remote_deleted: bool) -> ConflictType:
        """确定冲突类型"""
        if local_exists and remote_exists:
            if local_deleted and remote_deleted:
                return ConflictType.DELETE_DELETE
            elif local_deleted:
                return ConflictType.DELETE_UPDATE
            elif remote_deleted:
                return ConflictType.DELETE_UPDATE
            else:
                return ConflictType.UPDATE_UPDATE
        else:
            return ConflictType.CREATE_CREATE
    
    def auto_resolve(self, conflict_id: str) -> bool:
        """
        自动解决冲突
        
        Args:
            conflict_id: 冲突ID
        
        Returns:
            是否成功
        """
        if conflict_id not in self.conflicts:
            logger.warning(f"Conflict {conflict_id} not found")
            return False
        
        conflict = self.conflicts[conflict_id]
        
        if conflict.status != ConflictStatus.DETECTED:
            logger.warning(f"Conflict {conflict_id} already in state {conflict.status.value}")
            return False
        
        conflict.status = ConflictStatus.RESOLVING
        
        # 获取解决策略
        strategy = self._get_strategy_for_conflict(conflict)
        
        logger.info(f"Auto-resolving conflict {conflict_id} with strategy {strategy.value}")
        
        try:
            # 根据策略解决冲突
            resolved_data = self._apply_strategy(conflict, strategy)
            
            if resolved_data is not None:
                conflict.resolved_data = resolved_data
                conflict.status = ConflictStatus.RESOLVED
                conflict.resolved_at = time.time()
                conflict.resolved_by = "system"
                conflict.strategy = strategy
                
                self.stats["auto_resolved"] += 1
                
                logger.info(f"Conflict {conflict_id} auto-resolved")
                
                # 移到已解决列表
                self.resolved_conflicts.append(conflict)
                del self.conflicts[conflict_id]
                
                if self.on_conflict_resolved:
                    self.on_conflict_resolved(conflict)
                
                return True
            else:
                conflict.status = ConflictStatus.FAILED
                self.stats["failed"] += 1
                
                logger.error(f"Failed to resolve conflict {conflict_id}")
                
                if self.on_resolution_failed:
                    self.on_resolution_failed(conflict_id, "Strategy returned no data")
                
                return False
                
        except Exception as e:
            conflict.status = ConflictStatus.FAILED
            self.stats["failed"] += 1
            
            logger.error(f"Error resolving conflict {conflict_id}: {e}")
            
            if self.on_resolution_failed:
                self.on_resolution_failed(conflict_id, str(e))
            
            return False
    
    def _get_strategy_for_conflict(self, conflict: ConflictRecord) -> ConflictStrategy:
        """获取冲突解决策略"""
        # 按集合特定策略
        if conflict.collection in self.config.strategy_by_collection:
            return self.config.strategy_by_collection[conflict.collection]
        
        # 按冲突类型特定策略
        if conflict.type in self.config.strategy_by_type:
            return self.config.strategy_by_type[conflict.type]
        
        # 默认策略
        return self.config.default_strategy
    
    def _apply_strategy(self, conflict: ConflictRecord, 
                       strategy: ConflictStrategy) -> Optional[Dict[str, Any]]:
        """应用解决策略"""
        if strategy == ConflictStrategy.CLIENT_WINS:
            return self._client_wins(conflict)
        elif strategy == ConflictStrategy.SERVER_WINS:
            return self._server_wins(conflict)
        elif strategy == ConflictStrategy.LAST_WRITE_WINS:
            return self._last_write_wins(conflict)
        elif strategy == ConflictStrategy.MERGE:
            return self._merge(conflict)
        elif strategy == ConflictStrategy.IGNORE:
            return self._ignore(conflict)
        else:
            return None
    
    def _client_wins(self, conflict: ConflictRecord) -> Optional[Dict[str, Any]]:
        """客户端优先"""
        return conflict.local_data
    
    def _server_wins(self, conflict: ConflictRecord) -> Optional[Dict[str, Any]]:
        """服务端优先"""
        return conflict.remote_data
    
    def _last_write_wins(self, conflict: ConflictRecord) -> Optional[Dict[str, Any]]:
        """最后写入优先"""
        local_time = conflict.local_data.get("_timestamp", 0) if conflict.local_data else 0
        remote_time = conflict.remote_data.get("_timestamp", 0) if conflict.remote_data else 0
        
        if local_time >= remote_time:
            return conflict.local_data
        else:
            return conflict.remote_data
    
    def _merge(self, conflict: ConflictRecord) -> Optional[Dict[str, Any]]:
        """合并数据"""
        if not conflict.local_data and not conflict.remote_data:
            return None
        
        if not conflict.local_data:
            return conflict.remote_data
        
        if not conflict.remote_data:
            return conflict.local_data
        
        merged = {}
        
        # 所有字段
        all_fields = set(conflict.local_data.keys()) | set(conflict.remote_data.keys())
        
        for field in all_fields:
            local_value = conflict.local_data.get(field)
            remote_value = conflict.remote_data.get(field)
            
            if local_value == remote_value:
                merged[field] = local_value
            elif field in self.config.merge_fields:
                # 需要合并的字段（如列表）
                merged[field] = self._merge_field(field, local_value, remote_value)
            elif field in self.config.prefer_local_fields:
                merged[field] = local_value
            elif field in self.config.prefer_remote_fields:
                merged[field] = remote_value
            else:
                # 默认使用更新的值
                local_time = conflict.local_data.get("_timestamp", 0)
                remote_time = conflict.remote_data.get("_timestamp", 0)
                merged[field] = local_value if local_time >= remote_time else remote_value
        
        return merged
    
    def _merge_field(self, field: str, local_value: Any, remote_value: Any) -> Any:
        """合并字段值"""
        # 简单实现：如果是列表，合并去重
        if isinstance(local_value, list) and isinstance(remote_value, list):
            merged = list(set(local_value) | set(remote_value))
            return merged
        
        # 如果是字典，递归合并
        if isinstance(local_value, dict) and isinstance(remote_value, dict):
            merged = local_value.copy()
            merged.update(remote_value)
            return merged
        
        # 默认使用更新的值
        return remote_value
    
    def _ignore(self, conflict: ConflictRecord) -> Optional[Dict[str, Any]]:
        """忽略冲突"""
        self.stats["ignored"] += 1
        conflict.status = ConflictStatus.IGNORED
        return conflict.local_data  # 保持原样
    
    def manual_resolve(self, conflict_id: str, resolved_data: Dict[str, Any],
                      resolved_by: str = "user") -> bool:
        """
        手动解决冲突
        
        Args:
            conflict_id: 冲突ID
            resolved_data: 解决后的数据
            resolved_by: 解决者
        
        Returns:
            是否成功
        """
        if conflict_id not in self.conflicts:
            logger.warning(f"Conflict {conflict_id} not found")
            return False
        
        conflict = self.conflicts[conflict_id]
        
        conflict.resolved_data = resolved_data
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolved_at = time.time()
        conflict.resolved_by = resolved_by
        
        self.stats["manually_resolved"] += 1
        
        logger.info(f"Conflict {conflict_id} manually resolved by {resolved_by}")
        
        # 移到已解决列表
        self.resolved_conflicts.append(conflict)
        del self.conflicts[conflict_id]
        
        if self.on_conflict_resolved:
            self.on_conflict_resolved(conflict)
        
        return True
    
    def get_conflict(self, conflict_id: str) -> Optional[ConflictRecord]:
        """
        获取冲突记录
        
        Args:
            conflict_id: 冲突ID
        
        Returns:
            冲突记录
        """
        return self.conflicts.get(conflict_id)
    
    def get_conflicts(self, status: Optional[ConflictStatus] = None) -> List[ConflictRecord]:
        """
        获取冲突列表
        
        Args:
            status: 状态过滤
        
        Returns:
            冲突列表
        """
        conflicts = list(self.conflicts.values())
        
        if status:
            conflicts = [c for c in conflicts if c.status == status]
        
        return conflicts
    
    def get_resolved_history(self, limit: int = 100) -> List[ConflictRecord]:
        """
        获取已解决冲突历史
        
        Args:
            limit: 返回数量
        
        Returns:
            冲突记录列表
        """
        return self.resolved_conflicts[-limit:]
    
    def clear_resolved(self):
        """清除已解决的冲突记录"""
        if self.config.keep_history:
            # 限制历史大小
            if len(self.resolved_conflicts) > self.config.max_history:
                self.resolved_conflicts = self.resolved_conflicts[-self.config.max_history:]
        else:
            self.resolved_conflicts.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取冲突解决管理器状态
        
        Returns:
            状态字典
        """
        return {
            "pending_conflicts": len(self.conflicts),
            "resolved_history": len(self.resolved_conflicts),
            "stats": self.stats,
            "config": {
                "default_strategy": self.config.default_strategy.value,
                "auto_resolve": self.config.auto_resolve
            }
        }
    
    def shutdown(self):
        """关闭冲突解决管理器"""
        logger.info("Shutting down ConflictResolution...")
        
        self.conflicts.clear()
        self.resolved_conflicts.clear()
        
        logger.info("ConflictResolution shutdown completed")

# 单例模式实现
_conflict_resolution_instance: Optional[ConflictResolution] = None

def get_conflict_resolution(config: Optional[ConflictConfig] = None) -> ConflictResolution:
    """
    获取冲突解决管理器单例
    
    Args:
        config: 冲突解决配置
    
    Returns:
        冲突解决管理器实例
    """
    global _conflict_resolution_instance
    if _conflict_resolution_instance is None:
        _conflict_resolution_instance = ConflictResolution(config)
    return _conflict_resolution_instance

