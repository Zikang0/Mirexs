"""
内存分配器：智能内存分配和回收
负责系统内存的智能分配、管理和垃圾回收
"""

import gc
import psutil
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import weakref

class MemoryType(Enum):
    """内存类型枚举"""
    MODEL_DATA = "model_data"      # 模型数据
    CACHE_DATA = "cache_data"      # 缓存数据
    WORKING_MEMORY = "working_memory"  # 工作内存
    TEMPORARY = "temporary"        # 临时数据

@dataclass
class MemoryBlock:
    """内存块"""
    block_id: str
    memory_type: MemoryType
    size: int
    allocated_time: float
    last_accessed: float
    data: Any = None
    is_locked: bool = False

@dataclass
class MemoryStats:
    """内存统计"""
    total_allocated: int
    memory_usage: Dict[MemoryType, int]
    allocation_count: int
    gc_collections: int

class MemoryAllocator:
    """内存分配器"""
    
    def __init__(self, max_memory: int = None):
        self.memory_blocks: Dict[str, MemoryBlock] = {}
        self.memory_stats = MemoryStats(0, {}, 0, 0)
        self.max_memory = max_memory or (psutil.virtual_memory().total * 0.8)  # 80%系统内存
        self.cleanup_task: Optional[asyncio.Task] = None
        self.initialized = False
        
        # 初始化内存使用统计
        for mem_type in MemoryType:
            self.memory_stats.memory_usage[mem_type] = 0
    
    async def initialize(self):
        """初始化内存分配器"""
        if self.initialized:
            return
            
        logging.info("初始化内存分配器...")
        
        # 启动内存清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        self.initialized = True
        logging.info(f"内存分配器初始化完成，最大内存: {self.max_memory / 1024 / 1024 / 1024:.1f} GB")
    
    async def allocate_memory(self, size: int, memory_type: MemoryType, 
                            data: Any = None, block_id: str = None) -> str:
        """分配内存"""
        if size <= 0:
            raise ValueError("内存大小必须大于0")
        
        # 检查内存是否足够
        if not await self._check_memory_availability(size):
            # 尝试清理内存
            await self._perform_cleanup()
            
            # 再次检查
            if not await self._check_memory_availability(size):
                raise MemoryError(f"内存不足，请求大小: {size} bytes, 可用: {self._get_available_memory()} bytes")
        
        # 生成块ID
        if block_id is None:
            block_id = f"mem_{int(time.time() * 1000)}_{len(self.memory_blocks)}"
        
        current_time = time.time()
        block = MemoryBlock(
            block_id=block_id,
            memory_type=memory_type,
            size=size,
            allocated_time=current_time,
            last_accessed=current_time,
            data=data
        )
        
        self.memory_blocks[block_id] = block
        
        # 更新统计信息
        self.memory_stats.total_allocated += size
        self.memory_stats.memory_usage[memory_type] += size
        self.memory_stats.allocation_count += 1
        
        logging.debug(f"内存分配成功: {block_id}, 类型: {memory_type.value}, 大小: {size} bytes")
        return block_id
    
    async def _check_memory_availability(self, requested_size: int) -> bool:
        """检查内存可用性"""
        current_usage = self.memory_stats.total_allocated
        available_memory = self.max_memory - current_usage
        
        return available_memory >= requested_size
    
    def _get_available_memory(self) -> int:
        """获取可用内存"""
        return self.max_memory - self.memory_stats.total_allocated
    
    async def access_memory(self, block_id: str) -> Any:
        """访问内存数据"""
        if block_id not in self.memory_blocks:
            raise KeyError(f"内存块不存在: {block_id}")
        
        block = self.memory_blocks[block_id]
        block.last_accessed = time.time()
        
        return block.data
    
    async def update_memory(self, block_id: str, data: Any, new_size: int = None) -> bool:
        """更新内存数据"""
        if block_id not in self.memory_blocks:
            return False
        
        block = self.memory_blocks[block_id]
        
        old_size = block.size
        block.data = data
        block.last_accessed = time.time()
        
        if new_size is not None and new_size != old_size:
            # 更新大小
            size_diff = new_size - old_size
            
            if size_diff > 0 and not await self._check_memory_availability(size_diff):
                return False
            
            block.size = new_size
            self.memory_stats.total_allocated += size_diff
            self.memory_stats.memory_usage[block.memory_type] += size_diff
        
        return True
    
    async def release_memory(self, block_id: str) -> bool:
        """释放内存"""
        if block_id not in self.memory_blocks:
            return False
        
        block = self.memory_blocks[block_id]
        
        # 更新统计信息
        self.memory_stats.total_allocated -= block.size
        self.memory_stats.memory_usage[block.memory_type] -= block.size
        
        # 删除内存块
        del self.memory_blocks[block_id]
        
        # 强制垃圾回收
        if block.data is not None:
            block.data = None
        
        logging.debug(f"内存释放成功: {block_id}, 大小: {block.size} bytes")
        return True
    
    async def lock_memory(self, block_id: str) -> bool:
        """锁定内存块（防止被清理）"""
        if block_id not in self.memory_blocks:
            return False
        
        self.memory_blocks[block_id].is_locked = True
        return True
    
    async def unlock_memory(self, block_id: str) -> bool:
        """解锁内存块"""
        if block_id not in self.memory_blocks:
            return False
        
        self.memory_blocks[block_id].is_locked = False
        return True
    
    async def _cleanup_worker(self):
        """内存清理工作线程"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._perform_cleanup()
            except Exception as e:
                logging.error(f"内存清理错误: {e}")
    
    async def _perform_cleanup(self):
        """执行内存清理"""
        current_time = time.time()
        memory_pressure = self.memory_stats.total_allocated / self.max_memory
        
        # 根据内存压力调整清理策略
        if memory_pressure > 0.8:
            await self._aggressive_cleanup()
        elif memory_pressure > 0.6:
            await self._moderate_cleanup()
        else:
            await self._light_cleanup()
    
    async def _light_cleanup(self):
        """轻度清理"""
        # 清理长时间未访问的临时数据
        await self._cleanup_by_age(MemoryType.TEMPORARY, max_age=300)  # 5分钟
    
    async def _moderate_cleanup(self):
        """中度清理"""
        # 清理临时数据和部分缓存数据
        await self._cleanup_by_age(MemoryType.TEMPORARY, max_age=60)   # 1分钟
        await self._cleanup_by_age(MemoryType.CACHE_DATA, max_age=600) # 10分钟
    
    async def _aggressive_cleanup(self):
        """激进清理"""
        # 清理所有可清理的数据
        await self._cleanup_by_age(MemoryType.TEMPORARY, max_age=30)   # 30秒
        await self._cleanup_by_age(MemoryType.CACHE_DATA, max_age=300) # 5分钟
        await self._cleanup_by_age(MemoryType.WORKING_MEMORY, max_age=1800)  # 30分钟
        
        # 强制垃圾回收
        collected = gc.collect()
        self.memory_stats.gc_collections += collected
        logging.info(f"强制垃圾回收，回收对象: {collected}")
    
    async def _cleanup_by_age(self, memory_type: MemoryType, max_age: int):
        """按年龄清理内存"""
        current_time = time.time()
        blocks_to_remove = []
        
        for block_id, block in self.memory_blocks.items():
            if (block.memory_type == memory_type and 
                not block.is_locked and 
                (current_time - block.last_accessed) > max_age):
                blocks_to_remove.append(block_id)
        
        for block_id in blocks_to_remove:
            await self.release_memory(block_id)
        
        if blocks_to_remove:
            logging.info(f"清理了 {len(blocks_to_remove)} 个 {memory_type.value} 内存块")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        total_system_memory = psutil.virtual_memory().total
        
        return {
            "allocator_stats": {
                "total_allocated": self.memory_stats.total_allocated,
                "max_memory": self.max_memory,
                "available_memory": self._get_available_memory(),
                "usage_percentage": (self.memory_stats.total_allocated / self.max_memory * 100),
                "allocation_count": self.memory_stats.allocation_count,
                "gc_collections": self.memory_stats.gc_collections
            },
            "memory_usage_by_type": {
                mem_type.value: usage 
                for mem_type, usage in self.memory_stats.memory_usage.items()
            },
            "system_memory": {
                "total": total_system_memory,
                "used": psutil.virtual_memory().used,
                "available": psutil.virtual_memory().available,
                "percentage": psutil.virtual_memory().percent
            },
            "block_count": len(self.memory_blocks)
        }
    
    async def optimize_memory(self):
        """优化内存使用"""
        logging.info("执行内存优化...")
        
        # 执行垃圾回收
        before_optimization = self.memory_stats.total_allocated
        collected = gc.collect()
        
        # 清理碎片化内存
        await self._defragment_memory()
        
        after_optimization = self.memory_stats.total_allocated
        memory_saved = before_optimization - after_optimization
        
        logging.info(f"内存优化完成，回收内存: {memory_saved} bytes, 垃圾回收对象: {collected}")
    
    async def _defragment_memory(self):
        """内存碎片整理"""
        # 这里可以实现更复杂的内存整理算法
        # 当前实现是简单的：合并小内存块或重新组织内存布局
        
        # 模拟内存整理
        logging.debug("执行内存碎片整理...")
        
        # 在实际实现中，这里会重新组织内存布局以减少碎片
        # 由于Python的内存管理特性，这主要是概念性的

# 全局内存分配器实例
memory_allocator = MemoryAllocator()