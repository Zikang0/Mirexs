"""
工作记忆模块：临时存储当前任务信息
实现基于时间窗口的工作记忆系统
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional
from collections import deque
import threading
import logging

class WorkingMemory:
    """工作记忆系统 - 临时存储当前任务信息"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.memory_store = {}
        self.access_queue = deque()
        self.lock = threading.RLock()
        
        # 配置参数
        self.max_items = self.config.get('max_items', 100)
        self.default_ttl = self.config.get('default_ttl', 3600)  # 1小时
        self.cleanup_interval = self.config.get('cleanup_interval', 300)  # 5分钟
        
        self.initialized = True
        self._start_cleanup_task()
        self.logger.info("工作记忆系统初始化成功")
    
    def store(self, 
             key: str,
             value: Any,
             ttl: int = None,
             priority: int = 1,
             metadata: Dict[str, Any] = None) -> bool:
        """
        存储信息到工作记忆
        
        Args:
            key: 存储键
            value: 存储值
            ttl: 生存时间（秒）
            priority: 优先级（1-10，越高越重要）
            metadata: 元数据
            
        Returns:
            是否成功
        """
        with self.lock:
            # 检查容量限制
            if len(self.memory_store) >= self.max_items and key not in self.memory_store:
                self._evict_least_important()
            
            ttl = ttl or self.default_ttl
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
            
            memory_item = {
                'value': value,
                'expiry_time': expiry_time,
                'priority': max(1, min(10, priority)),
                'created_at': datetime.datetime.now(),
                'last_accessed': datetime.datetime.now(),
                'access_count': 0,
                'metadata': metadata or {}
            }
            
            self.memory_store[key] = memory_item
            self._update_access_queue(key)
            
            self.logger.debug(f"工作记忆存储: {key}")
            return True
    
    def retrieve(self, key: str, update_access: bool = True) -> Optional[Any]:
        """
        从工作记忆检索信息
        
        Args:
            key: 检索键
            update_access: 是否更新访问时间
            
        Returns:
            存储的值或None
        """
        with self.lock:
            if key not in self.memory_store:
                return None
            
            item = self.memory_store[key]
            
            # 检查是否过期
            if datetime.datetime.now() > item['expiry_time']:
                del self.memory_store[key]
                self._remove_from_queue(key)
                return None
            
            if update_access:
                item['last_accessed'] = datetime.datetime.now()
                item['access_count'] += 1
                self._update_access_queue(key)
            
            return item['value']
    
    def retrieve_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """检索信息及其元数据"""
        with self.lock:
            if key not in self.memory_store:
                return None
            
            item = self.memory_store[key]
            
            if datetime.datetime.now() > item['expiry_time']:
                del self.memory_store[key]
                self._remove_from_queue(key)
                return None
            
            item['last_accessed'] = datetime.datetime.now()
            item['access_count'] += 1
            self._update_access_queue(key)
            
            return {
                'value': item['value'],
                'metadata': item['metadata'],
                'access_count': item['access_count'],
                'created_at': item['created_at'],
                'last_accessed': item['last_accessed'],
                'expiry_time': item['expiry_time']
            }
    
    def exists(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self.lock:
            if key not in self.memory_store:
                return False
            
            item = self.memory_store[key]
            if datetime.datetime.now() > item['expiry_time']:
                del self.memory_store[key]
                self._remove_from_queue(key)
                return False
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除工作记忆中的信息"""
        with self.lock:
            if key in self.memory_store:
                del self.memory_store[key]
                self._remove_from_queue(key)
                self.logger.debug(f"工作记忆删除: {key}")
                return True
            return False
    
    def update_ttl(self, key: str, ttl: int) -> bool:
        """更新信息的生存时间"""
        with self.lock:
            if key not in self.memory_store:
                return False
            
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
            self.memory_store[key]['expiry_time'] = expiry_time
            return True
    
    def update_priority(self, key: str, priority: int) -> bool:
        """更新信息的优先级"""
        with self.lock:
            if key not in self.memory_store:
                return False
            
            self.memory_store[key]['priority'] = max(1, min(10, priority))
            self._update_access_queue(key)
            return True
    
    def _update_access_queue(self, key: str):
        """更新访问队列"""
        # 移除旧位置
        self._remove_from_queue(key)
        
        # 添加到队列开头
        self.access_queue.appendleft(key)
    
    def _remove_from_queue(self, key: str):
        """从队列中移除"""
        if key in self.access_queue:
            self.access_queue.remove(key)
    
    def _evict_least_important(self):
        """驱逐最不重要的项目"""
        if not self.access_queue:
            return
        
        # 找到综合评分最低的项目
        min_score = float('inf')
        candidate_key = None
        
        for key in list(self.memory_store.keys()):
            if key not in self.access_queue:
                continue
                
            item = self.memory_store[key]
            score = self._calculate_eviction_score(item, key)
            
            if score < min_score:
                min_score = score
                candidate_key = key
        
        if candidate_key:
            del self.memory_store[candidate_key]
            self._remove_from_queue(candidate_key)
            self.logger.debug(f"工作记忆驱逐: {candidate_key}")
    
    def _calculate_eviction_score(self, item: Dict[str, Any], key: str) -> float:
        """计算驱逐分数（分数越低越容易被驱逐）"""
        # 基于优先级、访问频率、创建时间计算
        priority_weight = 1.0 / item['priority']  # 优先级越高，分数越低
        recency_weight = self._calculate_recency_weight(item['last_accessed'])
        frequency_weight = 1.0 / max(1, item['access_count'])  # 访问越多，分数越低
        
        return priority_weight + recency_weight + frequency_weight
    
    def _calculate_recency_weight(self, last_accessed: datetime.datetime) -> float:
        """计算时效性权重"""
        time_diff = (datetime.datetime.now() - last_accessed).total_seconds() / 60  # 分钟
        # 最近访问的项目权重更低（更不容易被驱逐）
        return min(1.0, time_diff / 60)  # 1小时内线性增长
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        def cleanup():
            while True:
                import time
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
        
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired(self):
        """清理过期项目"""
        with self.lock:
            current_time = datetime.datetime.now()
            expired_keys = []
            
            for key, item in self.memory_store.items():
                if current_time > item['expiry_time']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_store[key]
                self._remove_from_queue(key)
            
            if expired_keys:
                self.logger.debug(f"清理了 {len(expired_keys)} 个过期工作记忆项目")
    
    def search(self, 
              value_filter: callable = None,
              metadata_filter: Dict[str, Any] = None,
              max_results: int = 10) -> List[Dict[str, Any]]:
        """
        搜索工作记忆
        
        Args:
            value_filter: 值过滤函数
            metadata_filter: 元数据过滤条件
            max_results: 最大结果数
            
        Returns:
            匹配的项目列表
        """
        with self.lock:
            results = []
            
            for key, item in self.memory_store.items():
                # 检查是否过期
                if datetime.datetime.now() > item['expiry_time']:
                    continue
                
                # 应用值过滤器
                if value_filter and not value_filter(item['value']):
                    continue
                
                # 应用元数据过滤器
                if metadata_filter:
                    match = True
                    for meta_key, meta_value in metadata_filter.items():
                        if item['metadata'].get(meta_key) != meta_value:
                            match = False
                            break
                    if not match:
                        continue
                
                results.append({
                    'key': key,
                    'value': item['value'],
                    'metadata': item['metadata'],
                    'access_count': item['access_count'],
                    'priority': item['priority'],
                    'created_at': item['created_at'],
                    'last_accessed': item['last_accessed']
                })
                
                if len(results) >= max_results:
                    break
            
            return results
    
    def get_context_snapshot(self) -> Dict[str, Any]:
        """获取当前工作记忆快照"""
        with self.lock:
            snapshot = {
                'timestamp': datetime.datetime.now().isoformat(),
                'total_items': len(self.memory_store),
                'items': {}
            }
            
            for key, item in self.memory_store.items():
                if datetime.datetime.now() > item['expiry_time']:
                    continue
                
                snapshot['items'][key] = {
                    'value_type': type(item['value']).__name__,
                    'priority': item['priority'],
                    'access_count': item['access_count'],
                    'created_at': item['created_at'].isoformat(),
                    'last_accessed': item['last_accessed'].isoformat(),
                    'expires_in': (item['expiry_time'] - datetime.datetime.now()).total_seconds(),
                    'metadata_keys': list(item['metadata'].keys())
                }
            
            return snapshot
    
    def clear(self):
        """清空工作记忆"""
        with self.lock:
            self.memory_store.clear()
            self.access_queue.clear()
            self.logger.info("工作记忆已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工作记忆统计信息"""
        with self.lock:
            total_items = len(self.memory_store)
            total_size = sum(len(str(item['value'])) for item in self.memory_store.values())
            
            # 优先级分布
            priority_dist = {}
            for item in self.memory_store.values():
                priority = item['priority']
                priority_dist[priority] = priority_dist.get(priority, 0) + 1
            
            # 平均访问次数
            avg_access = 0
            if total_items > 0:
                avg_access = sum(item['access_count'] for item in self.memory_store.values()) / total_items
            
            return {
                'total_items': total_items,
                'total_size_bytes': total_size,
                'average_access_count': avg_access,
                'priority_distribution': priority_dist,
                'max_capacity': self.max_items,
                'utilization_percent': (total_items / self.max_items) * 100
            }

