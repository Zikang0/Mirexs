"""
缓存策略模块 - 缓存替换策略
负责实现各种缓存替换算法和策略
"""

import time
import heapq
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
import math

class CachePolicy(Enum):
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最不经常使用
    FIFO = "fifo"  # 先进先出
    RANDOM = "random"  # 随机替换
    ARC = "arc"  # 自适应替换缓存

@dataclass
class CacheItem:
    key: str
    value: Any
    size: int
    created_at: float
    accessed_at: float
    access_count: int
    frequency: int = 1

class CachePolicyBase:
    """缓存策略基类"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.current_size = 0
        self.items: Dict[str, CacheItem] = {}
    
    def on_get(self, key: str) -> None:
        """访问缓存项时的处理"""
        pass
    
    def on_set(self, key: str, item: CacheItem) -> None:
        """设置缓存项时的处理"""
        pass
    
    def on_delete(self, key: str) -> None:
        """删除缓存项时的处理"""
        pass
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """获取需要淘汰的缓存键"""
        raise NotImplementedError
    
    def should_evict(self, new_item_size: int) -> bool:
        """检查是否需要淘汰"""
        return self.current_size + new_item_size > self.max_size

class LRUCachePolicy(CachePolicyBase):
    """LRU（最近最少使用）缓存策略"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.access_order: List[str] = []
    
    def on_get(self, key: str) -> None:
        """访问时移动到最新位置"""
        if key in self.access_order:
            self.access_order.remove(key)
            self.access_order.append(key)
    
    def on_set(self, key: str, item: CacheItem) -> None:
        """设置时添加到最新位置"""
        if key not in self.access_order:
            self.access_order.append(key)
    
    def on_delete(self, key: str) -> None:
        """删除时从访问顺序中移除"""
        if key in self.access_order:
            self.access_order.remove(key)
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """获取最久未使用的键"""
        return self.access_order[:count]

class LFUCachePolicy(CachePolicyBase):
    """LFU（最不经常使用）缓存策略"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.frequency_heap: List[Tuple[int, float, str]] = []  # (频率, 时间, 键)
        self.key_to_heap_index: Dict[str, int] = {}
        self.counter = 0  # 用于打破平局的时间戳
    
    def on_get(self, key: str) -> None:
        """访问时增加频率"""
        if key in self.items:
            item = self.items[key]
            item.access_count += 1
            item.frequency += 1
            self._update_heap(key, item.frequency)
    
    def on_set(self, key: str, item: CacheItem) -> None:
        """设置时添加到堆中"""
        self._add_to_heap(key, item.frequency)
    
    def on_delete(self, key: str) -> None:
        """删除时从堆中移除"""
        self._remove_from_heap(key)
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """获取频率最低的键"""
        candidates = []
        for i in range(min(count, len(self.frequency_heap))):
            if i < len(self.frequency_heap):
                candidates.append(self.frequency_heap[i][2])
        return candidates
    
    def _add_to_heap(self, key: str, frequency: int):
        """添加到频率堆"""
        self.counter += 1
        entry = (frequency, self.counter, key)
        heapq.heappush(self.frequency_heap, entry)
        self.key_to_heap_index[key] = len(self.frequency_heap) - 1
    
    def _update_heap(self, key: str, new_frequency: int):
        """更新堆中的频率"""
        # 由于堆不支持直接更新，我们标记旧条目为无效并添加新条目
        self._remove_from_heap(key)
        self._add_to_heap(key, new_frequency)
    
    def _remove_from_heap(self, key: str):
        """从堆中移除"""
        if key in self.key_to_heap_index:
            # 标记为已删除（在实际实现中可能需要更复杂的方法）
            # 这里简化处理，在get_eviction_candidates中跳过无效条目
            del self.key_to_heap_index[key]

class FIFOCachePolicy(CachePolicyBase):
    """FIFO（先进先出）缓存策略"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.insertion_order: List[str] = []
    
    def on_set(self, key: str, item: CacheItem) -> None:
        """设置时添加到队列末尾"""
        if key not in self.insertion_order:
            self.insertion_order.append(key)
    
    def on_delete(self, key: str) -> None:
        """删除时从队列中移除"""
        if key in self.insertion_order:
            self.insertion_order.remove(key)
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """获取最早插入的键"""
        return self.insertion_order[:count]

class ARCachePolicy(CachePolicyBase):
    """ARC（自适应替换缓存）策略"""
    
    def __init__(self, max_size: int):
        super().__init__(max_size)
        self.t1 = []  # 最近访问的项
        self.t2 = []  # 频繁访问的项
        self.b1 = []  # 最近被淘汰的项（历史）
        self.b2 = []  # 频繁被淘汰的项（历史）
        self.p = 0  # 目标大小参数
        self.c = max_size  # 缓存容量
    
    def on_get(self, key: str) -> None:
        """ARC访问处理"""
        if key in self.t1:
            # 从t1移动到t2（变为频繁）
            self.t1.remove(key)
            self.t2.append(key)
        elif key in self.t2:
            # 在t2中，移动到末尾（LRU）
            self.t2.remove(key)
            self.t2.append(key)
        elif key in self.b1:
            # 在b1中，调整p并移动到t2
            self._adapt(True)  # 在b1中命中
            self.b1.remove(key)
            self.t2.append(key)
            self._replace(True)
        elif key in self.b2:
            # 在b2中，调整p并移动到t2
            self._adapt(False)  # 在b2中命中
            self.b2.remove(key)
            self.t2.append(key)
            self._replace(True)
    
    def on_set(self, key: str, item: CacheItem) -> None:
        """ARC设置处理"""
        # 新项添加到t1
        self.t1.append(key)
        self._replace(False)
    
    def on_delete(self, key: str) -> None:
        """ARC删除处理"""
        for lst in [self.t1, self.t2, self.b1, self.b2]:
            if key in lst:
                lst.remove(key)
    
    def get_eviction_candidates(self, count: int = 1) -> List[str]:
        """ARC淘汰候选"""
        candidates = []
        
        # ARC的淘汰逻辑在_replace方法中实现
        # 这里返回可能的淘汰候选
        if len(self.t1) + len(self.b1) >= self.c:
            if len(self.t1) < self.c:
                candidates = self.b1[:count]
            else:
                candidates = self.t1[:count]
        else:
            total = len(self.t1) + len(self.t2) + len(self.b1) + len(self.b2)
            if total >= 2 * self.c:
                candidates = self.b2[:count]
        
        return candidates[:count]
    
    def _adapt(self, in_b1: bool):
        """自适应调整参数p"""
        if in_b1:
            # 在b1中命中，增加p
            delta = 1 if len(self.b2) / len(self.b1) >= 1 else len(self.b2) / len(self.b1)
            self.p = min(self.p + delta, self.c)
        else:
            # 在b2中命中，减少p
            delta = 1 if len(self.b1) / len(self.b2) >= 1 else len(self.b1) / len(self.b2)
            self.p = max(self.p - delta, 0)
    
    def _replace(self, in_t2: bool):
        """执行替换"""
        if (len(self.t1) > 0 and 
            (len(self.t1) > self.p or (in_t2 and len(self.t1) == self.p))):
            # 从t1淘汰
            if len(self.t1) > 0:
                victim = self.t1.pop(0)
                self.b1.append(victim)
        else:
            # 从t2淘汰
            if len(self.t2) > 0:
                victim = self.t2.pop(0)
                self.b2.append(victim)

class CachePolicyManager:
    """缓存策略管理器"""
    
    def __init__(self, policy: CachePolicy = CachePolicy.LRU, max_size: int = 100 * 1024 * 1024):
        self.policy_type = policy
        self.max_size = max_size
        
        if policy == CachePolicy.LRU:
            self.policy = LRUCachePolicy(max_size)
        elif policy == CachePolicy.LFU:
            self.policy = LFUCachePolicy(max_size)
        elif policy == CachePolicy.FIFO:
            self.policy = FIFOCachePolicy(max_size)
        elif policy == CachePolicy.ARC:
            self.policy = ARCachePolicy(max_size)
        else:
            self.policy = LRUCachePolicy(max_size)  # 默认LRU
    
    def record_access(self, key: str):
        """记录访问"""
        self.policy.on_get(key)
    
    def record_addition(self, key: str, item: CacheItem):
        """记录添加"""
        self.policy.on_set(key, item)
    
    def record_removal(self, key: str):
        """记录移除"""
        self.policy.on_delete(key)
    
    def get_victims(self, required_space: int, count: int = 5) -> List[str]:
        """获取需要淘汰的键"""
        return self.policy.get_eviction_candidates(count)
    
    def needs_eviction(self, new_item_size: int) -> bool:
        """检查是否需要淘汰"""
        return self.policy.should_evict(new_item_size)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        return {
            "policy": self.policy_type.value,
            "max_size": self.policy.max_size,
            "current_size": self.policy.current_size,
            "item_count": len(self.policy.items),
            "utilization_percent": (self.policy.current_size / self.policy.max_size * 100) 
                                  if self.policy.max_size > 0 else 0
        }

# 策略工厂函数
def create_cache_policy(policy: CachePolicy, max_size: int) -> CachePolicyManager:
    """创建缓存策略"""
    return CachePolicyManager(policy, max_size)

# 策略评估器
class PolicyEvaluator:
    """缓存策略评估器"""
    
    def __init__(self):
        self.access_patterns = []
    
    def record_access_pattern(self, key: str, operation: str, timestamp: float):
        """记录访问模式"""
        self.access_patterns.append({
            "key": key,
            "operation": operation,
            "timestamp": timestamp
        })
    
    def evaluate_policy(self, policy: CachePolicyManager, trace_data: List[Dict]) -> Dict[str, Any]:
        """评估策略性能"""
        hit_count = 0
        miss_count = 0
        total_accesses = len(trace_data)
        
        # 模拟运行访问轨迹
        cache_state = set()
        
        for access in trace_data:
            key = access["key"]
            operation = access["operation"]
            
            if operation == "get":
                if key in cache_state:
                    hit_count += 1
                    policy.record_access(key)
                else:
                    miss_count += 1
                    # 模拟缓存未命中后的加载
                    if len(cache_state) >= policy.policy.max_size // 1024:  # 简化假设
                        victims = policy.get_victims(1024)
                        for victim in victims:
                            if victim in cache_state:
                                cache_state.remove(victim)
                                policy.record_removal(victim)
                    
                    cache_state.add(key)
                    # 创建模拟的缓存项
                    item = CacheItem(key=key, value=None, size=1024, 
                                   created_at=time.time(), accessed_at=time.time(), access_count=1)
                    policy.record_addition(key, item)
            
            elif operation == "set":
                if key not in cache_state:
                    if len(cache_state) >= policy.policy.max_size // 1024:
                        victims = policy.get_victims(1024)
                        for victim in victims:
                            if victim in cache_state:
                                cache_state.remove(victim)
                                policy.record_removal(victim)
                    
                    cache_state.add(key)
                    item = CacheItem(key=key, value=None, size=1024,
                                   created_at=time.time(), accessed_at=time.time(), access_count=0)
                    policy.record_addition(key, item)
        
        hit_rate = (hit_count / total_accesses * 100) if total_accesses > 0 else 0
        
        return {
            "policy": policy.policy_type.value,
            "total_accesses": total_accesses,
            "hit_count": hit_count,
            "miss_count": miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "final_cache_size": len(cache_state)
        }
