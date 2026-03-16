"""
离线操作模块 - Mirexs数据同步系统

提供离线操作功能，包括：
1. 操作队列
2. 操作持久化
3. 操作重试
4. 操作回滚
5. 操作优先级
"""

import logging
import time
import json
import threading
import os
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import pickle

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """操作类型枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    CUSTOM = "custom"

class OperationStatus(Enum):
    """操作状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"

@dataclass
class OperationRecord:
    """操作记录"""
    id: str
    type: OperationType
    collection: str
    item_id: str
    data: Optional[Dict[str, Any]] = None
    status: OperationStatus = OperationStatus.PENDING
    priority: int = 5  # 1-10, 1最高
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OfflineQueue:
    """离线队列"""
    id: str
    name: str
    operations: List[OperationRecord] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OfflineConfig:
    """离线操作配置"""
    # 队列配置
    queue_file: str = "data/offline/queue.pkl"
    max_queue_size: int = 10000
    save_interval: int = 60  # 秒
    
    # 重试配置
    max_retries: int = 3
    retry_delay: int = 60  # 秒
    retry_backoff: float = 2.0
    
    # 清理配置
    auto_cleanup: bool = True
    cleanup_interval: int = 86400  # 秒
    max_history: int = 1000

class OfflineOperation:
    """
    离线操作管理器
    
    负责离线操作的管理和执行。
    """
    
    def __init__(self, config: Optional[OfflineConfig] = None):
        """
        初始化离线操作管理器
        
        Args:
            config: 离线操作配置
        """
        self.config = config or OfflineConfig()
        
        # 操作队列
        self.pending_operations: Dict[str, OperationRecord] = {}
        self.completed_operations: List[OperationRecord] = []
        self.failed_operations: List[OperationRecord] = []
        
        # 队列持久化
        self._ensure_data_dir()
        self._load_queue()
        
        # 处理线程
        self._processor_thread: Optional[threading.Thread] = None
        self._saver_thread: Optional[threading.Thread] = None
        self._stop_processing = threading.Event()
        
        # 回调函数
        self.on_operation_added: Optional[Callable[[OperationRecord], None]] = None
        self.on_operation_started: Optional[Callable[[OperationRecord], None]] = None
        self.on_operation_completed: Optional[Callable[[OperationRecord], None]] = None
        self.on_operation_failed: Optional[Callable[[OperationRecord, str], None]] = None
        self.on_queue_processed: Optional[Callable[[int, int], None]] = None
        
        # 统计
        self.stats = {
            "total_operations": 0,
            "completed_operations": 0,
            "failed_operations": 0,
            "cancelled_operations": 0
        }
        
        # 启动处理器
        self._start_processor()
        
        logger.info("OfflineOperation initialized")
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.config.queue_file), exist_ok=True)
    
    def _load_queue(self):
        """加载队列"""
        if os.path.exists(self.config.queue_file):
            try:
                with open(self.config.queue_file, 'rb') as f:
                    data = pickle.load(f)
                    self.pending_operations = data.get("pending", {})
                    self.completed_operations = data.get("completed", [])
                    self.failed_operations = data.get("failed", [])
                    
                    # 更新统计
                    for op in self.pending_operations.values():
                        if op.status == OperationStatus.COMPLETED:
                            self.stats["completed_operations"] += 1
                        elif op.status == OperationStatus.FAILED:
                            self.stats["failed_operations"] += 1
                    
                    self.stats["total_operations"] = len(self.pending_operations) + len(self.completed_operations)
                    
                logger.info(f"Loaded {len(self.pending_operations)} pending operations")
            except Exception as e:
                logger.error(f"Error loading queue: {e}")
    
    def _save_queue(self):
        """保存队列"""
        try:
            data = {
                "pending": self.pending_operations,
                "completed": self.completed_operations[-self.config.max_history:],
                "failed": self.failed_operations[-self.config.max_history:]
            }
            
            with open(self.config.queue_file, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug("Queue saved")
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
    
    def _start_processor(self):
        """启动处理器"""
        def processor_loop():
            while not self._stop_processing.is_set():
                try:
                    self._process_next()
                    self._stop_processing.wait(1)
                except Exception as e:
                    logger.error(f"Processor error: {e}")
        
        def saver_loop():
            while not self._stop_processing.is_set():
                try:
                    self._save_queue()
                    self._stop_processing.wait(self.config.save_interval)
                except Exception as e:
                    logger.error(f"Saver error: {e}")
        
        self._processor_thread = threading.Thread(target=processor_loop, daemon=True)
        self._processor_thread.start()
        
        self._saver_thread = threading.Thread(target=saver_loop, daemon=True)
        self._saver_thread.start()
        
        logger.debug("Offline operation processor started")
    
    def _process_next(self):
        """处理下一个操作"""
        # 按优先级排序
        pending = [op for op in self.pending_operations.values() 
                  if op.status == OperationStatus.PENDING]
        
        if not pending:
            return
        
        # 按优先级排序（数字越小优先级越高）
        pending.sort(key=lambda x: (x.priority, x.created_at))
        
        operation = pending[0]
        
        self._process_operation(operation.id)
    
    def _process_operation(self, operation_id: str):
        """
        处理操作
        
        Args:
            operation_id: 操作ID
        """
        if operation_id not in self.pending_operations:
            return
        
        operation = self.pending_operations[operation_id]
        
        operation.status = OperationStatus.PROCESSING
        operation.updated_at = time.time()
        
        if self.on_operation_started:
            self.on_operation_started(operation)
        
        logger.debug(f"Processing operation: {operation.id}")
        
        # 模拟处理
        success = self._execute_operation(operation)
        
        if success:
            operation.status = OperationStatus.COMPLETED
            operation.completed_at = time.time()
            
            self.stats["completed_operations"] += 1
            
            # 移到已完成列表
            self.completed_operations.append(operation)
            del self.pending_operations[operation_id]
            
            logger.debug(f"Operation completed: {operation.id}")
            
            if self.on_operation_completed:
                self.on_operation_completed(operation)
        else:
            operation.retry_count += 1
            operation.updated_at = time.time()
            
            if operation.retry_count >= operation.max_retries:
                operation.status = OperationStatus.FAILED
                operation.completed_at = time.time()
                
                self.stats["failed_operations"] += 1
                
                # 移到失败列表
                self.failed_operations.append(operation)
                del self.pending_operations[operation_id]
                
                logger.error(f"Operation failed after {operation.retry_count} retries: {operation.id}")
                
                if self.on_operation_failed:
                    self.on_operation_failed(operation, operation.error or "Max retries exceeded")
            else:
                # 等待重试
                operation.status = OperationStatus.PENDING
                logger.debug(f"Operation will be retried: {operation.id} (attempt {operation.retry_count})")
    
    def _execute_operation(self, operation: OperationRecord) -> bool:
        """执行操作"""
        # 实际实现中会执行真正的操作
        # 这里模拟操作
        import random
        
        # 90%成功率
        success = random.random() < 0.9
        
        if not success:
            operation.error = "Simulated failure"
        
        return success
    
    def add_operation(self, operation_type: OperationType, collection: str,
                     item_id: str, data: Optional[Dict[str, Any]] = None,
                     priority: int = 5, max_retries: Optional[int] = None) -> str:
        """
        添加操作
        
        Args:
            operation_type: 操作类型
            collection: 集合名称
            item_id: 项目ID
            data: 操作数据
            priority: 优先级
            max_retries: 最大重试次数
        
        Returns:
            操作ID
        """
        operation_id = str(uuid.uuid4())
        
        operation = OperationRecord(
            id=operation_id,
            type=operation_type,
            collection=collection,
            item_id=item_id,
            data=data,
            priority=priority,
            max_retries=max_retries or self.config.max_retries
        )
        
        self.pending_operations[operation_id] = operation
        self.stats["total_operations"] += 1
        
        logger.debug(f"Operation added: {operation_id} ({operation_type.value})")
        
        if self.on_operation_added:
            self.on_operation_added(operation)
        
        return operation_id
    
    def cancel_operation(self, operation_id: str) -> bool:
        """
        取消操作
        
        Args:
            operation_id: 操作ID
        
        Returns:
            是否成功
        """
        if operation_id not in self.pending_operations:
            logger.warning(f"Operation {operation_id} not found")
            return False
        
        operation = self.pending_operations[operation_id]
        
        if operation.status == OperationStatus.PENDING:
            operation.status = OperationStatus.CANCELLED
            operation.completed_at = time.time()
            
            self.stats["cancelled_operations"] += 1
            
            # 移到已完成列表
            self.completed_operations.append(operation)
            del self.pending_operations[operation_id]
            
            logger.info(f"Operation cancelled: {operation_id}")
            
            return True
        
        return False
    
    def retry_failed(self, operation_id: Optional[str] = None) -> int:
        """
        重试失败的操作
        
        Args:
            operation_id: 操作ID，None表示重试所有失败操作
        
        Returns:
            重试数量
        """
        retry_count = 0
        
        if operation_id:
            # 重试单个操作
            for op in self.failed_operations:
                if op.id == operation_id:
                    self.failed_operations.remove(op)
                    op.status = OperationStatus.PENDING
                    op.retry_count = 0
                    op.error = None
                    self.pending_operations[op.id] = op
                    retry_count = 1
                    logger.info(f"Retrying failed operation: {operation_id}")
                    break
        else:
            # 重试所有失败操作
            for op in self.failed_operations[:]:
                op.status = OperationStatus.PENDING
                op.retry_count = 0
                op.error = None
                self.pending_operations[op.id] = op
                self.failed_operations.remove(op)
                retry_count += 1
            
            logger.info(f"Retrying {retry_count} failed operations")
        
        return retry_count
    
    def clear_completed(self, older_than: Optional[float] = None):
        """
        清除已完成的操作
        
        Args:
            older_than: 清除早于该时间的操作
        """
        if older_than:
            cutoff = time.time() - older_than
            self.completed_operations = [op for op in self.completed_operations 
                                        if op.completed_at and op.completed_at >= cutoff]
            self.failed_operations = [op for op in self.failed_operations 
                                     if op.completed_at and op.completed_at >= cutoff]
        else:
            self.completed_operations.clear()
            self.failed_operations.clear()
        
        logger.debug("Completed operations cleared")
    
    def get_pending_count(self) -> int:
        """获取待处理操作数量"""
        return len([op for op in self.pending_operations.values() 
                   if op.status == OperationStatus.PENDING])
    
    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """
        获取操作
        
        Args:
            operation_id: 操作ID
        
        Returns:
            操作记录
        """
        return self.pending_operations.get(operation_id)
    
    def get_pending_operations(self) -> List[OperationRecord]:
        """获取待处理操作列表"""
        return [op for op in self.pending_operations.values() 
                if op.status == OperationStatus.PENDING]
    
    def get_completed_operations(self, limit: int = 100) -> List[OperationRecord]:
        """
        获取已完成操作列表
        
        Args:
            limit: 返回数量
        
        Returns:
            操作列表
        """
        return self.completed_operations[-limit:]
    
    def get_failed_operations(self, limit: int = 100) -> List[OperationRecord]:
        """
        获取失败操作列表
        
        Args:
            limit: 返回数量
        
        Returns:
            操作列表
        """
        return self.failed_operations[-limit:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取离线操作管理器状态
        
        Returns:
            状态字典
        """
        return {
            "queues": {
                "pending": len(self.pending_operations),
                "processing": len([op for op in self.pending_operations.values() if op.status == OperationStatus.PROCESSING]),
                "completed": len(self.completed_operations),
                "failed": len(self.failed_operations)
            },
            "stats": self.stats,
            "config": {
                "max_retries": self.config.max_retries,
                "max_queue_size": self.config.max_queue_size
            }
        }
    
    def shutdown(self):
        """关闭离线操作管理器"""
        logger.info("Shutting down OfflineOperation...")
        
        self._stop_processing.set()
        
        if self._processor_thread and self._processor_thread.is_alive():
            self._processor_thread.join(timeout=2)
        
        if self._saver_thread and self._saver_thread.is_alive():
            self._saver_thread.join(timeout=2)
        
        # 保存队列
        self._save_queue()
        
        self.pending_operations.clear()
        self.completed_operations.clear()
        self.failed_operations.clear()
        
        logger.info("OfflineOperation shutdown completed")

# 单例模式实现
_offline_operation_instance: Optional[OfflineOperation] = None

def get_offline_operation(config: Optional[OfflineConfig] = None) -> OfflineOperation:
    """
    获取离线操作管理器单例
    
    Args:
        config: 离线操作配置
    
    Returns:
        离线操作管理器实例
    """
    global _offline_operation_instance
    if _offline_operation_instance is None:
        _offline_operation_instance = OfflineOperation(config)
    return _offline_operation_instance

