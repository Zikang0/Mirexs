"""
磁盘缓存模块 - 磁盘缓存管理
负责管理磁盘上的缓存数据，提供持久化缓存存储
"""

import os
import json
import time
import pickle
import hashlib
import shutil
from typing import Any, Dict, Optional, List
from pathlib import Path
import threading
from enum import Enum

class DiskCacheSerialization(Enum):
    JSON = "json"
    PICKLE = "pickle"

class DiskCache:
    """磁盘缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache/disk", max_size_mb: int = 1000, 
                 default_ttl: int = 86400, serialization: DiskCacheSerialization = DiskCacheSerialization.JSON):
        self.cache_dir = Path(cache_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.serialization = serialization
        self.lock = threading.RLock()
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 统计信息
        self.stats = {
            "total_sets": 0,
            "total_gets": 0,
            "total_deletes": 0,
            "total_hits": 0,
            "total_misses": 0,
            "total_evictions": 0
        }
        
        # 初始化索引
        self.index_file = self.cache_dir / "cache_index.json"
        self.cache_index = self._load_index()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> bool:
        """
        设置磁盘缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            tags: 缓存标签
            
        Returns:
            bool: 是否设置成功
        """
        with self.lock:
            try:
                # 生成文件名
                filename = self._get_filename(key)
                filepath = self.cache_dir / filename
                
                # 检查磁盘空间
                if not self._check_disk_space():
                    if not self._cleanup_old_entries():
                        return False
                
                # 计算过期时间
                expires_at = None
                if ttl is not None:
                    expires_at = time.time() + ttl
                elif self.default_ttl is not None:
                    expires_at = time.time() + self.default_ttl
                
                # 序列化数据
                if self.serialization == DiskCacheSerialization.JSON:
                    try:
                        serialized_data = json.dumps(value).encode('utf-8')
                    except (TypeError, ValueError):
                        # 如果JSON序列化失败，使用pickle
                        serialized_data = pickle.dumps(value)
                else:
                    serialized_data = pickle.dumps(value)
                
                # 写入文件
                with open(filepath, 'wb') as f:
                    f.write(serialized_data)
                
                # 更新索引
                self.cache_index[key] = {
                    "filename": filename,
                    "created_at": time.time(),
                    "expires_at": expires_at,
                    "size": len(serialized_data),
                    "tags": tags or [],
                    "access_count": 0,
                    "last_accessed": time.time()
                }
                
                self._save_index()
                self.stats["total_sets"] += 1
                
                return True
                
            except Exception as e:
                print(f"磁盘缓存设置失败: {e}")
                return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取磁盘缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        with self.lock:
            self.stats["total_gets"] += 1
            
            if key not in self.cache_index:
                self.stats["total_misses"] += 1
                return default
            
            entry = self.cache_index[key]
            
            # 检查是否过期
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                self.delete(key)
                self.stats["total_misses"] += 1
                return default
            
            filepath = self.cache_dir / entry["filename"]
            if not filepath.exists():
                self.delete(key)
                self.stats["total_misses"] += 1
                return default
            
            try:
                # 读取文件
                with open(filepath, 'rb') as f:
                    data = f.read()
                
                # 反序列化数据
                if self.serialization == DiskCacheSerialization.JSON:
                    try:
                        value = json.loads(data.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        value = pickle.loads(data)
                else:
                    value = pickle.loads(data)
                
                # 更新访问信息
                entry["access_count"] += 1
                entry["last_accessed"] = time.time()
                self._save_index()
                
                self.stats["total_hits"] += 1
                return value
                
            except Exception as e:
                print(f"磁盘缓存读取失败: {e}")
                self.delete(key)
                self.stats["total_misses"] += 1
                return default
    
    def delete(self, key: str) -> bool:
        """
        删除磁盘缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        with self.lock:
            if key not in self.cache_index:
                return False
            
            try:
                entry = self.cache_index[key]
                filepath = self.cache_dir / entry["filename"]
                
                # 删除文件
                if filepath.exists():
                    filepath.unlink()
                
                # 从索引中移除
                del self.cache_index[key]
                self._save_index()
                
                self.stats["total_deletes"] += 1
                return True
                
            except Exception as e:
                print(f"磁盘缓存删除失败: {e}")
                return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self.lock:
            if key not in self.cache_index:
                return False
            
            entry = self.cache_index[key]
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                self.delete(key)
                return False
            
            filepath = self.cache_dir / entry["filename"]
            return filepath.exists()
    
    def ttl(self, key: str) -> Optional[float]:
        """获取剩余生存时间"""
        with self.lock:
            if key not in self.cache_index:
                return None
            
            entry = self.cache_index[key]
            if not entry["expires_at"]:
                return None
            
            remaining = entry["expires_at"] - time.time()
            return max(0, remaining) if remaining > 0 else None
    
    def clear(self) -> bool:
        """清空所有磁盘缓存"""
        with self.lock:
            try:
                # 删除所有缓存文件
                for key in list(self.cache_index.keys()):
                    self.delete(key)
                
                # 重新创建空索引
                self.cache_index = {}
                self._save_index()
                
                return True
                
            except Exception as e:
                print(f"清空磁盘缓存失败: {e}")
                return False
    
    def cleanup_expired(self) -> int:
        """清理过期缓存项"""
        with self.lock:
            keys_to_delete = []
            current_time = time.time()
            
            for key, entry in self.cache_index.items():
                if entry["expires_at"] and current_time > entry["expires_at"]:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self.delete(key)
            
            return len(keys_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取磁盘缓存统计信息"""
        with self.lock:
            total_size = sum(entry["size"] for entry in self.cache_index.values())
            hit_rate = 0
            total_accesses = self.stats["total_hits"] + self.stats["total_misses"]
            if total_accesses > 0:
                hit_rate = self.stats["total_hits"] / total_accesses * 100
            
            return {
                **self.stats,
                "cache_dir": str(self.cache_dir),
                "total_size_mb": total_size / 1024 / 1024,
                "max_size_mb": self.max_size_bytes / 1024 / 1024,
                "entry_count": len(self.cache_index),
                "hit_rate_percent": round(hit_rate, 2),
                "disk_usage_percent": (total_size / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0
            }
    
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """根据标签获取缓存键"""
        with self.lock:
            return [key for key, entry in self.cache_index.items() if tag in entry.get("tags", [])]
    
    def delete_by_tags(self, tags: List[str]) -> int:
        """根据标签删除缓存项"""
        with self.lock:
            keys_to_delete = []
            for key, entry in self.cache_index.items():
                if any(tag in entry.get("tags", []) for tag in tags):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                self.delete(key)
            
            return len(keys_to_delete)
    
    def _get_filename(self, key: str) -> str:
        """根据键生成文件名"""
        # 使用哈希避免文件名冲突和特殊字符问题
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{key_hash}.cache"
    
    def _load_index(self) -> Dict[str, Any]:
        """加载缓存索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载缓存索引失败: {e}")
        
        return {}
    
    def _save_index(self) -> bool:
        """保存缓存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存缓存索引失败: {e}")
            return False
    
    def _check_disk_space(self) -> bool:
        """检查磁盘空间"""
        total_size = sum(entry["size"] for entry in self.cache_index.values())
        return total_size < self.max_size_bytes
    
    def _cleanup_old_entries(self) -> bool:
        """清理旧条目以释放空间"""
        with self.lock:
            # 首先清理过期项目
            self.cleanup_expired()
            
            # 如果仍然空间不足，使用LRU策略清理
            total_size = sum(entry["size"] for entry in self.cache_index.values())
            if total_size < self.max_size_bytes:
                return True
            
            # 按最后访问时间排序
            sorted_entries = sorted(
                self.cache_index.items(),
                key=lambda x: x[1]["last_accessed"]
            )
            
            freed_size = 0
            target_free = total_size - self.max_size_bytes * 0.8  # 释放到80%使用率
            
            for key, entry in sorted_entries:
                if freed_size >= target_free:
                    break
                
                self.delete(key)
                freed_size += entry["size"]
                self.stats["total_evictions"] += 1
            
            return freed_size >= target_free
    
    def backup_cache(self, backup_dir: str) -> bool:
        """备份缓存数据"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 复制缓存目录
            shutil.copytree(self.cache_dir, backup_path / "cache", dirs_exist_ok=True)
            
            # 创建备份信息
            backup_info = {
                "backup_time": time.time(),
                "entry_count": len(self.cache_index),
                "total_size": sum(entry["size"] for entry in self.cache_index.values()),
                "cache_stats": self.get_stats()
            }
            
            with open(backup_path / "backup_info.json", 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"缓存备份失败: {e}")
            return False

# 全局磁盘缓存实例
disk_cache = DiskCache(cache_dir="cache/disk", max_size_mb=1000, default_ttl=86400)
