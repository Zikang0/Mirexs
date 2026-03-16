"""
缓存管理器：多级缓存系统管理
负责系统各级缓存的管理和优化
"""

import asyncio
import time
import pickle
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import hashlib

class CacheLevel(Enum):
    """缓存级别枚举"""
    L1 = "l1"  # 内存缓存
    L2 = "l2"  # 磁盘缓存  
    L3 = "l3"  # 分布式缓存

class CachePolicy(Enum):
    """缓存策略枚举"""
    LRU = "lru"      # 最近最少使用
    LFU = "lfu"      # 最不经常使用
    FIFO = "fifo"    # 先进先出
    TTL = "ttl"      # 生存时间

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    level: CacheLevel
    size: int
    created_time: float
    last_accessed: float
    access_count: int
    ttl: Optional[int] = None  # 生存时间(秒)

@dataclass
class CacheStats:
    """缓存统计"""
    hits: int
    misses: int
    total_size: int
    entry_count: int

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.cache_stores: Dict[CacheLevel, Dict[str, CacheEntry]] = {
            CacheLevel.L1: {},  # 内存缓存
            CacheLevel.L2: {},  # 磁盘缓存
            CacheLevel.L3: {}   # 分布式缓存
        }
        
        self.cache_stats: Dict[CacheLevel, CacheStats] = {
            level: CacheStats(0, 0, 0, 0) for level in CacheLevel
        }
        
        self.default_ttl = 3600  # 默认生存时间(1小时)
        self.max_memory_size = 100 * 1024 * 1024  # 最大内存缓存大小(100MB)
        self.cleanup_task: Optional[asyncio.Task] = None
        self.initialized = False
        
    async def initialize(self):
        """初始化缓存管理器"""
        if self.initialized:
            return
            
        logging.info("初始化缓存管理器...")
        
        # 启动缓存清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_worker())
        
        # 加载磁盘缓存
        await self._load_disk_cache()
        
        self.initialized = True
        logging.info("缓存管理器初始化完成")
    
    async def _load_disk_cache(self):
        """加载磁盘缓存"""
        try:
            import os
            cache_file = "data/cache/l2_cache.pkl"
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    disk_cache = pickle.load(f)
                
                for key, entry_data in disk_cache.items():
                    entry = CacheEntry(
                        key=key,
                        value=entry_data['value'],
                        level=CacheLevel.L2,
                        size=entry_data['size'],
                        created_time=entry_data['created_time'],
                        last_accessed=entry_data['last_accessed'],
                        access_count=entry_data['access_count'],
                        ttl=entry_data.get('ttl')
                    )
                    self.cache_stores[CacheLevel.L2][key] = entry
                
                logging.info(f"加载了 {len(disk_cache)} 个磁盘缓存条目")
                
        except Exception as e:
            logging.error(f"加载磁盘缓存失败: {e}")
    
    async def set(self, key: str, value: Any, level: CacheLevel = CacheLevel.L1, 
                 ttl: int = None, size: int = None) -> bool:
        """设置缓存"""
        if ttl is None:
            ttl = self.default_ttl
        
        if size is None:
            # 估算大小
            size = self._estimate_size(value)
        
        current_time = time.time()
        entry = CacheEntry(
            key=key,
            value=value,
            level=level,
            size=size,
            created_time=current_time,
            last_accessed=current_time,
            access_count=1,
            ttl=ttl
        )
        
        # 检查缓存级别限制
        if not await self._check_level_capacity(level, size):
            await self._evict_entries(level)
        
        self.cache_stores[level][key] = entry
        
        # 更新统计信息
        self.cache_stats[level].total_size += size
        self.cache_stats[level].entry_count += 1
        
        logging.debug(f"缓存设置成功: {key} -> {level.value}, 大小: {size} bytes")
        return True
    
    async def get(self, key: str, level: CacheLevel = None) -> Any:
        """获取缓存"""
        if level is not None:
            # 在指定级别查找
            return await self._get_from_level(key, level)
        else:
            # 多级缓存查找 (L1 -> L2 -> L3)
            for cache_level in [CacheLevel.L1, CacheLevel.L2, CacheLevel.L3]:
                value = await self._get_from_level(key, cache_level)
                if value is not None:
                    # 提升到更高级别缓存
                    if cache_level != CacheLevel.L1:
                        await self._promote_to_l1(key, value, cache_level)
                    return value
            
            # 缓存未命中
            self._record_miss(CacheLevel.L1)  # 记录在L1的未命中
            return None
    
    async def _get_from_level(self, key: str, level: CacheLevel) -> Any:
        """从指定级别获取缓存"""
        if key not in self.cache_stores[level]:
            self._record_miss(level)
            return None
        
        entry = self.cache_stores[level][key]
        
        # 检查TTL
        if entry.ttl and (time.time() - entry.created_time) > entry.ttl:
            await self.delete(key, level)
            self._record_miss(level)
            return None
        
        # 更新访问信息
        entry.last_accessed = time.time()
        entry.access_count += 1
        
        self._record_hit(level)
        logging.debug(f"缓存命中: {key} -> {level.value}")
        return entry.value
    
    async def _promote_to_l1(self, key: str, value: Any, from_level: CacheLevel):
        """提升到L1缓存"""
        entry = self.cache_stores[from_level][key]
        
        # 复制到L1
        await self.set(key, value, CacheLevel.L1, entry.ttl, entry.size)
        
        logging.debug(f"缓存提升: {key} -> L1")
    
    async def delete(self, key: str, level: CacheLevel = None) -> bool:
        """删除缓存"""
        if level is not None:
            # 删除指定级别
            if key in self.cache_stores[level]:
                entry = self.cache_stores[level][key]
                self.cache_stats[level].total_size -= entry.size
                self.cache_stats[level].entry_count -= 1
                del self.cache_stores[level][key]
                return True
        else:
            # 删除所有级别
            deleted = False
            for level in CacheLevel:
                if key in self.cache_stores[level]:
                    entry = self.cache_stores[level][key]
                    self.cache_stats[level].total_size -= entry.size
                    self.cache_stats[level].entry_count -= 1
                    del self.cache_stores[level][key]
                    deleted = True
            return deleted
        
        return False
    
    async def _check_level_capacity(self, level: CacheLevel, new_size: int) -> bool:
        """检查级别容量"""
        if level == CacheLevel.L1:
            current_size = self.cache_stats[level].total_size
            return (current_size + new_size) <= self.max_memory_size
        else:
            # L2和L3暂时没有大小限制
            return True
    
    async def _evict_entries(self, level: CacheLevel):
        """驱逐缓存条目"""
        if level != CacheLevel.L1:
            return  # 目前只对L1实现驱逐
        
        # 使用LRU策略
        entries = list(self.cache_stores[level].values())
        entries.sort(key=lambda x: x.last_accessed)  # 按最后访问时间排序
        
        # 驱逐最旧的条目直到有足够空间
        target_size = self.max_memory_size * 0.8  # 目标使用80%
        current_size = self.cache_stats[level].total_size
        
        while current_size > target_size and entries:
            oldest_entry = entries.pop(0)
            await self.delete(oldest_entry.key, level)
            current_size = self.cache_stats[level].total_size
            logging.debug(f"缓存驱逐: {oldest_entry.key}")
    
    def _estimate_size(self, value: Any) -> int:
        """估算值的大小"""
        try:
            return len(pickle.dumps(value))
        except:
            return 1024  # 默认1KB
    
    def _record_hit(self, level: CacheLevel):
        """记录缓存命中"""
        self.cache_stats[level].hits += 1
    
    def _record_miss(self, level: CacheLevel):
        """记录缓存未命中"""
        self.cache_stats[level].misses += 1
    
    async def _cleanup_worker(self):
        """缓存清理工作线程"""
        while True:
            try:
                await asyncio.sleep(60)  # 每60秒清理一次
                await self._cleanup_expired_entries()
                
                # 保存磁盘缓存
                await self._save_disk_cache()
                
            except Exception as e:
                logging.error(f"缓存清理错误: {e}")
    
    async def _cleanup_expired_entries(self):
        """清理过期条目"""
        current_time = time.time()
        expired_count = 0
        
        for level in CacheLevel:
            keys_to_remove = []
            
            for key, entry in self.cache_stores[level].items():
                if entry.ttl and (current_time - entry.created_time) > entry.ttl:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                await self.delete(key, level)
                expired_count += 1
        
        if expired_count > 0:
            logging.info(f"清理了 {expired_count} 个过期缓存条目")
    
    async def _save_disk_cache(self):
        """保存磁盘缓存"""
        try:
            import os
            cache_dir = "data/cache"
            os.makedirs(cache_dir, exist_ok=True)
            
            disk_cache = {}
            for key, entry in self.cache_stores[CacheLevel.L2].items():
                disk_cache[key] = {
                    'value': entry.value,
                    'size': entry.size,
                    'created_time': entry.created_time,
                    'last_accessed': entry.last_accessed,
                    'access_count': entry.access_count,
                    'ttl': entry.ttl
                }
            
            cache_file = f"{cache_dir}/l2_cache.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(disk_cache, f)
                
            logging.debug("磁盘缓存已保存")
            
        except Exception as e:
            logging.error(f"保存磁盘缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {}
        
        for level in CacheLevel:
            level_stats = self.cache_stats[level]
            total_requests = level_stats.hits + level_stats.misses
            hit_rate = (level_stats.hits / total_requests * 100) if total_requests > 0 else 0
            
            stats[level.value] = {
                "hits": level_stats.hits,
                "misses": level_stats.misses,
                "hit_rate": hit_rate,
                "total_size": level_stats.total_size,
                "entry_count": level_stats.entry_count
            }
        
        # 总体统计
        total_hits = sum(stats[level.value]["hits"] for level in CacheLevel)
        total_misses = sum(stats[level.value]["misses"] for level in CacheLevel)
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        stats["overall"] = {
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_requests": total_requests,
            "hit_rate": overall_hit_rate
        }
        
        return stats
    
    async def clear_cache(self, level: CacheLevel = None):
        """清空缓存"""
        if level is not None:
            # 清空指定级别
            self.cache_stores[level].clear()
            self.cache_stats[level] = CacheStats(0, 0, 0, 0)
            logging.info(f"清空 {level.value} 缓存")
        else:
            # 清空所有级别
            for level in CacheLevel:
                self.cache_stores[level].clear()
                self.cache_stats[level] = CacheStats(0, 0, 0, 0)
            logging.info("清空所有缓存")
    
    async def preheat_cache(self, key_generator: Callable, value_generator: Callable, count: int):
        """预热缓存"""
        logging.info(f"开始预热缓存，数量: {count}")
        
        preheated_count = 0
        for i in range(count):
            try:
                key = key_generator(i)
                value = value_generator(i)
                await self.set(key, value, CacheLevel.L1)
                preheated_count += 1
            except Exception as e:
                logging.error(f"预热缓存失败 [{i}]: {e}")
        
        logging.info(f"缓存预热完成，成功: {preheated_count}/{count}")

# 全局缓存管理器实例
cache_manager = CacheManager()