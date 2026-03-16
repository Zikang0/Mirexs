"""
缓存系统包
提供多级缓存管理，包括内存缓存、磁盘缓存和Redis缓存
"""

from .memory_cache import MemoryCache, memory_cache, CacheEntry, CacheEntryStatus
from .disk_cache import DiskCache, disk_cache, DiskCacheSerialization
from .redis_integration import RedisCache, create_redis_cache, RedisSerialization
from .cache_policy import (
    CachePolicy, CachePolicyManager, create_cache_policy,
    LRUCachePolicy, LFUCachePolicy, FIFOCachePolicy, ARCachePolicy,
    PolicyEvaluator
)
from .cache_validator import (
    CacheValidator, cache_validator, ValidationResult, ValidationRule,
    StandardValidationRules
)

__all__ = [
    # 内存缓存
    'MemoryCache', 'memory_cache', 'CacheEntry', 'CacheEntryStatus',
    
    # 磁盘缓存
    'DiskCache', 'disk_cache', 'DiskCacheSerialization',
    
    # Redis缓存
    'RedisCache', 'create_redis_cache', 'RedisSerialization',
    
    # 缓存策略
    'CachePolicy', 'CachePolicyManager', 'create_cache_policy',
    'LRUCachePolicy', 'LFUCachePolicy', 'FIFOCachePolicy', 'ARCachePolicy',
    'PolicyEvaluator',
    
    # 缓存验证
    'CacheValidator', 'cache_validator', 'ValidationResult', 'ValidationRule',
    'StandardValidationRules'
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Mirexs AI Team'
__description__ = 'Mirexs 多级缓存管理系统'