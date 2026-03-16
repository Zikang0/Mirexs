"""
内存缓存模块 - 内存缓存管理
负责管理内存中的缓存数据，提供快速的数据访问
"""

import time
import threading
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

class CacheEntryStatus(Enum):
    VALID = "valid"
    EXPIRED = "expired"
    STALE = "stale"

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    expires_at: Optional[float]
    access_count: int
    last_accessed: float
    size: int
    tags: List[str]

class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 3600):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.current_size = 0
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "total_sets": 0,
            "total_gets": 0,
            "total_evictions": 0,
            "total_hits": 0,
            "total_misses": 0
        }
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            tags: 缓存标签
            
        Returns:
            bool: 是否设置成功
        """
        with self.lock:
            # 计算值大小
            value_size = self._calculate_size(value)
            
            # 检查是否需要清理空间
            if self.current_size + value_size > self.max_size_bytes:
                if not self._make_space(value_size):
                    return False
            
            # 计算过期时间
            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl
            elif self.default_ttl is not None:
                expires_at = time.time() + self.default_ttl
            
            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                expires_at=expires_at,
                access_count=0,
                last_accessed=time.time(),
                size=value_size,
                tags=tags or []
            )
            
            # 如果键已存在，先移除旧值
            if key in self.cache:
                old_entry = self.cache[key]
                self.current_size -= old_entry.size
            
            # 添加新条目
            self.cache[key] = entry
            self.current_size += value_size
            
            # 更新统计
            self.stats["total_sets"] += 1
            
            return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        with self.lock:
            self.stats["total_gets"] += 1
            
            if key not in self.cache:
                self.miss_count += 1
                self.stats["total_misses"] += 1
                return default
            
            entry = self.cache[key]
            
            # 检查是否过期
            if entry.expires_at and time.time() > entry.expires_at:
                self._remove_entry(key)
                self.miss_count += 1
                self.stats["total_misses"] += 1
                return default
            
            # 更新访问信息
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            self.hit_count += 1
            self.stats["total_hits"] += 1
            
            return entry.value
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self.cache.clear()
            self.current_size = 0
            self.hit_count = 0
            self.miss_count = 0
    
    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self.lock:
            if key not in self.cache:
                return False
            
            entry = self.cache[key]
            if entry.expires_at and time.time() > entry.expires_at:
                self._remove_entry(key)
                return False
            
            return True
    
    def ttl(self, key: str) -> Optional[float]:
        """获取剩余生存时间"""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            if not entry.expires_at:
                return None
            
            remaining = entry.expires_at - time.time()
            return max(0, remaining) if remaining > 0 else None
    
    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def set_multi(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存值"""
        success = True
        for key, value in items.items():
            if not self.set(key, value, ttl):
                success = False
        return success
    
    def delete_by_tags(self, tags: List[str]) -> int:
        """根据标签删除缓存项"""
        with self.lock:
            keys_to_delete = []
            for key, entry in self.cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self._remove_entry(key)
            
            return len(keys_to_delete)
    
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """根据标签获取缓存键"""
        with self.lock:
            return [key for key, entry in self.cache.items() if tag in entry.tags]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            hit_rate = 0
            if self.hit_count + self.miss_count > 0:
                hit_rate = self.hit_count / (self.hit_count + self.miss_count) * 100
            
            return {
                **self.stats,
                "current_size_mb": self.current_size / 1024 / 1024,
                "max_size_mb": self.max_size_bytes / 1024 / 1024,
                "entry_count": len(self.cache),
                "hit_rate_percent": round(hit_rate, 2),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count
            }
    
    def cleanup_expired(self) -> int:
        """清理过期缓存项"""
        with self.lock:
            keys_to_delete = []
            current_time = time.time()
            
            for key, entry in self.cache.items():
                if entry.expires_at and current_time > entry.expires_at:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self._remove_entry(key)
            
            return len(keys_to_delete)
    
    def _make_space(self, required_size: int) -> bool:
        """清理空间以容纳新数据"""
        # 首先清理过期项目
        self.cleanup_expired()
        
        # 如果仍然空间不足，使用LRU策略清理
        if self.current_size + required_size > self.max_size_bytes:
            entries = list(self.cache.values())
            # 按最后访问时间排序（最久未使用的在前）
            entries.sort(key=lambda x: x.last_accessed)
            
            freed_size = 0
            for entry in entries:
                if freed_size >= required_size:
                    break
                
                self._remove_entry(entry.key)
                freed_size += entry.size
                self.stats["total_evictions"] += 1
        
        return self.current_size + required_size <= self.max_size_bytes
    
    def _remove_entry(self, key: str) -> None:
        """移除缓存条目"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size -= entry.size
            del self.cache[key]
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的近似大小"""
        try:
            # 对于简单类型，使用sys.getsizeof
            if isinstance(value, (int, float, str, bool, type(None))):
                import sys
                return sys.getsizeof(value)
            
            # 对于复杂类型，序列化为JSON字符串计算大小
            json_str = json.dumps(value)
            return len(json_str.encode('utf-8'))
            
        except (TypeError, OverflowError):
            # 如果无法序列化，返回默认大小
            return 1024
    
    def get_entries_info(self) -> List[Dict[str, Any]]:
        """获取所有缓存条目的信息"""
        with self.lock:
            entries_info = []
            current_time = time.time()
            
            for key, entry in self.cache.items():
                status = CacheEntryStatus.VALID
                if entry.expires_at and current_time > entry.expires_at:
                    status = CacheEntryStatus.EXPIRED
                elif entry.expires_at and current_time > entry.expires_at - 60:  # 60秒内过期
                    status = CacheEntryStatus.STALE
                
                entries_info.append({
                    "key": key,
                    "created_at": entry.created_at,
                    "expires_at": entry.expires_at,
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed,
                    "size_bytes": entry.size,
                    "tags": entry.tags,
                    "status": status.value
                })
            
            return entries_info

# 全局内存缓存实例
memory_cache = MemoryCache(max_size_mb=100, default_ttl=3600)

