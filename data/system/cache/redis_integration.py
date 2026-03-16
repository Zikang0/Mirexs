"""
Redis集成模块 - Redis缓存集成
负责与Redis服务器交互，提供分布式缓存功能
"""

import time
import json
import pickle
from typing import Any, Dict, Optional, List, Union
import threading
from enum import Enum

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Redis Python客户端未安装，Redis功能将不可用")

class RedisSerialization(Enum):
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"

class RedisCache:
    """Redis缓存管理器"""
    
    def __init__(self, 
                 host: str = 'localhost', 
                 port: int = 6379, 
                 db: int = 0,
                 password: Optional[str] = None,
                 default_ttl: int = 3600,
                 serialization: RedisSerialization = RedisSerialization.JSON,
                 connection_pool: Optional[Any] = None):
        
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis Python客户端未安装")
        
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.serialization = serialization
        self.connection_pool = connection_pool
        
        # 连接状态
        self._connected = False
        self._redis_client = None
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "total_sets": 0,
            "total_gets": 0,
            "total_deletes": 0,
            "total_hits": 0,
            "total_misses": 0,
            "connection_errors": 0
        }
        
        # 自动连接
        self._ensure_connected()
    
    def _ensure_connected(self) -> bool:
        """确保Redis连接"""
        with self.lock:
            if self._connected and self._redis_client:
                try:
                    # 测试连接
                    self._redis_client.ping()
                    return True
                except redis.RedisError:
                    self._connected = False
            
            try:
                if self.connection_pool:
                    self._redis_client = redis.Redis(connection_pool=self.connection_pool)
                else:
                    self._redis_client = redis.Redis(
                        host=self.host,
                        port=self.port,
                        db=self.db,
                        password=self.password,
                        decode_responses=False,  # 保持字节数据
                        socket_connect_timeout=5,
                        socket_timeout=5,
                        retry_on_timeout=True
                    )
                
                # 测试连接
                self._redis_client.ping()
                self._connected = True
                return True
                
            except redis.RedisError as e:
                print(f"Redis连接失败: {e}")
                self._connected = False
                self.stats["connection_errors"] += 1
                return False
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置Redis缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        if not self._ensure_connected():
            return False
        
        try:
            # 序列化数据
            serialized_value = self._serialize_value(value)
            
            # 设置TTL
            if ttl is None:
                ttl = self.default_ttl
            
            result = self._redis_client.setex(key, ttl, serialized_value)
            
            if result:
                self.stats["total_sets"] += 1
            
            return bool(result)
            
        except redis.RedisError as e:
            print(f"Redis设置失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取Redis缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        if not self._ensure_connected():
            return default
        
        self.stats["total_gets"] += 1
        
        try:
            serialized_value = self._redis_client.get(key)
            
            if serialized_value is None:
                self.stats["total_misses"] += 1
                return default
            
            value = self._deserialize_value(serialized_value)
            self.stats["total_hits"] += 1
            
            return value
            
        except redis.RedisError as e:
            print(f"Redis获取失败: {e}")
            self.stats["connection_errors"] += 1
            return default
    
    def delete(self, key: str) -> bool:
        """
        删除Redis缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        if not self._ensure_connected():
            return False
        
        try:
            result = self._redis_client.delete(key)
            if result > 0:
                self.stats["total_deletes"] += 1
            return result > 0
            
        except redis.RedisError as e:
            print(f"Redis删除失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._ensure_connected():
            return False
        
        try:
            return bool(self._redis_client.exists(key))
        except redis.RedisError as e:
            print(f"Redis存在性检查失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def ttl(self, key: str) -> Optional[int]:
        """获取剩余生存时间"""
        if not self._ensure_connected():
            return None
        
        try:
            ttl = self._redis_client.ttl(key)
            return ttl if ttl >= 0 else None
        except redis.RedisError as e:
            print(f"Redis TTL获取失败: {e}")
            self.stats["connection_errors"] += 1
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间"""
        if not self._ensure_connected():
            return False
        
        try:
            return bool(self._redis_client.expire(key, ttl))
        except redis.RedisError as e:
            print(f"Redis设置过期时间失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def get_multi(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        if not self._ensure_connected():
            return {}
        
        try:
            values = self._redis_client.mget(keys)
            result = {}
            
            for key, serialized_value in zip(keys, values):
                if serialized_value is not None:
                    result[key] = self._deserialize_value(serialized_value)
                else:
                    self.stats["total_misses"] += 1
            
            self.stats["total_gets"] += len(keys)
            self.stats["total_hits"] += len(result)
            
            return result
            
        except redis.RedisError as e:
            print(f"Redis批量获取失败: {e}")
            self.stats["connection_errors"] += 1
            return {}
    
    def set_multi(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存值"""
        if not self._ensure_connected():
            return False
        
        try:
            pipeline = self._redis_client.pipeline()
            
            for key, value in items.items():
                serialized_value = self._serialize_value(value)
                if ttl is not None:
                    pipeline.setex(key, ttl, serialized_value)
                else:
                    pipeline.set(key, serialized_value)
            
            results = pipeline.execute()
            success = all(results)
            
            if success:
                self.stats["total_sets"] += len(items)
            
            return success
            
        except redis.RedisError as e:
            print(f"Redis批量设置失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def delete_multi(self, keys: List[str]) -> int:
        """批量删除缓存项"""
        if not self._ensure_connected():
            return 0
        
        try:
            result = self._redis_client.delete(*keys)
            self.stats["total_deletes"] += result
            return result
            
        except redis.RedisError as e:
            print(f"Redis批量删除失败: {e}")
            self.stats["connection_errors"] += 1
            return 0
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增数值"""
        if not self._ensure_connected():
            return None
        
        try:
            return self._redis_client.incrby(key, amount)
        except redis.RedisError as e:
            print(f"Redis递增失败: {e}")
            self.stats["connection_errors"] += 1
            return None
    
    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """递减数值"""
        if not self._ensure_connected():
            return None
        
        try:
            return self._redis_client.decrby(key, amount)
        except redis.RedisError as e:
            print(f"Redis递减失败: {e}")
            self.stats["connection_errors"] += 1
            return None
    
    def hset(self, key: str, field: str, value: Any) -> bool:
        """设置哈希字段"""
        if not self._ensure_connected():
            return False
        
        try:
            serialized_value = self._serialize_value(value)
            return bool(self._redis_client.hset(key, field, serialized_value))
        except redis.RedisError as e:
            print(f"Redis哈希设置失败: {e}")
            self.stats["connection_errors"] += 1
            return False
    
    def hget(self, key: str, field: str, default: Any = None) -> Any:
        """获取哈希字段"""
        if not self._ensure_connected():
            return default
        
        try:
            serialized_value = self._redis_client.hget(key, field)
            if serialized_value is None:
                return default
            return self._deserialize_value(serialized_value)
        except redis.RedisError as e:
            print(f"Redis哈希获取失败: {e}")
            self.stats["connection_errors"] += 1
            return default
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        if not self._ensure_connected():
            return {}
        
        try:
            result = self._redis_client.hgetall(key)
            return {field.decode(): self._deserialize_value(value) for field, value in result.items()}
        except redis.RedisError as e:
            print(f"Redis哈希获取全部失败: {e}")
            self.stats["connection_errors"] += 1
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取Redis缓存统计信息"""
        hit_rate = 0
        total_accesses = self.stats["total_hits"] + self.stats["total_misses"]
        if total_accesses > 0:
            hit_rate = self.stats["total_hits"] / total_accesses * 100
        
        redis_info = {}
        if self._ensure_connected():
            try:
                redis_info = self._redis_client.info()
            except redis.RedisError:
                pass
        
        return {
            **self.stats,
            "connected": self._connected,
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "hit_rate_percent": round(hit_rate, 2),
            "redis_info": {
                "used_memory": redis_info.get('used_memory', 0),
                "connected_clients": redis_info.get('connected_clients', 0),
                "keyspace_hits": redis_info.get('keyspace_hits', 0),
                "keyspace_misses": redis_info.get('keyspace_misses', 0)
            } if redis_info else {}
        }
    
    def _serialize_value(self, value: Any) -> bytes:
        """序列化值"""
        if self.serialization == RedisSerialization.JSON:
            try:
                return json.dumps(value).encode('utf-8')
            except (TypeError, ValueError):
                # 如果JSON序列化失败，使用pickle
                return pickle.dumps(value)
        elif self.serialization == RedisSerialization.PICKLE:
            return pickle.dumps(value)
        else:  # STRING
            return str(value).encode('utf-8')
    
    def _deserialize_value(self, serialized_value: bytes) -> Any:
        """反序列化值"""
        try:
            if self.serialization == RedisSerialization.JSON:
                try:
                    return json.loads(serialized_value.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return pickle.loads(serialized_value)
            elif self.serialization == RedisSerialization.PICKLE:
                return pickle.loads(serialized_value)
            else:  # STRING
                return serialized_value.decode('utf-8')
        except Exception as e:
            print(f"Redis值反序列化失败: {e}")
            return None
    
    def close(self):
        """关闭Redis连接"""
        with self.lock:
            if self._redis_client:
                self._redis_client.close()
                self._connected = False
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close()

# 全局Redis缓存实例（需要时创建）
def create_redis_cache(host: str = 'localhost', port: int = 6379, db: int = 0, 
                      password: Optional[str] = None) -> Optional[RedisCache]:
    """创建Redis缓存实例"""
    if not REDIS_AVAILABLE:
        print("警告: Redis Python客户端未安装")
        return None
    
    try:
        return RedisCache(host=host, port=port, db=db, password=password)
    except Exception as e:
        print(f"创建Redis缓存失败: {e}")
        return None
