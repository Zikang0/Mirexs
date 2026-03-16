"""
速率限制器模块 - Mirexs API网关

提供API调用频率限制功能，包括：
1. 基于IP的限制
2. 基于用户的限制
3. 基于API密钥的限制
4. 滑动窗口算法
5. 令牌桶算法
6. 分布式限流
7. 自定义规则
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import hashlib
import json

logger = logging.getLogger(__name__)

# 尝试导入Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Distributed rate limiting will be limited.")

class LimitStrategy(Enum):
    """限流策略枚举"""
    TOKEN_BUCKET = "token_bucket"      # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"      # 漏桶
    FIXED_WINDOW = "fixed_window"      # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    SLIDING_LOG = "sliding_log"        # 滑动日志

class LimitScope(Enum):
    """限流范围枚举"""
    GLOBAL = "global"          # 全局
    IP = "ip"                  # 基于IP
    USER = "user"              # 基于用户
    API_KEY = "api_key"        # 基于API密钥
    ENDPOINT = "endpoint"      # 基于端点
    CUSTOM = "custom"          # 自定义

@dataclass
class RateLimit:
    """速率限制"""
    key: str
    limit: int                 # 请求数量限制
    window: int                # 时间窗口（秒）
    strategy: LimitStrategy = LimitStrategy.SLIDING_WINDOW
    scope: LimitScope = LimitScope.GLOBAL
    identifier: Optional[str] = None

@dataclass
class RateLimitRule:
    """速率限制规则"""
    id: str
    name: str
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    limits: List[RateLimit] = field(default_factory=list)
    enabled: bool = True

@dataclass
class RateLimitResult:
    """速率限制结果"""
    allowed: bool
    limit: int
    remaining: int
    reset: int
    retry_after: Optional[int] = None

@dataclass
class RateLimiterConfig:
    """速率限制器配置"""
    # 默认限制
    default_limit: int = 100
    default_window: int = 60  # 秒
    
    # Redis配置（用于分布式限流）
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 本地存储配置
    cleanup_interval: int = 60  # 秒
    max_storage: int = 10000  # 最大存储记录数
    
    # 响应头配置
    headers_enabled: bool = True
    limit_header: str = "X-RateLimit-Limit"
    remaining_header: str = "X-RateLimit-Remaining"
    reset_header: str = "X-RateLimit-Reset"

class TokenBucket:
    """令牌桶算法"""
    
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_fill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 计算新增令牌
            elapsed = now - self.last_fill
            new_tokens = elapsed * self.fill_rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_fill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_remaining(self) -> float:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_fill
            new_tokens = elapsed * self.fill_rate
            return min(self.capacity, self.tokens + new_tokens)

class LeakyBucket:
    """漏桶算法"""
    
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.water = 0
        self.last_leak = time.time()
        self.lock = threading.Lock()
    
    def consume(self, water: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 计算漏出的水
            elapsed = now - self.last_leak
            leaked = elapsed * self.leak_rate
            self.water = max(0, self.water - leaked)
            self.last_leak = now
            
            if self.water + water <= self.capacity:
                self.water += water
                return True
            return False
    
    def get_remaining(self) -> float:
        with self.lock:
            return max(0, self.capacity - self.water)

class FixedWindow:
    """固定窗口算法"""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.count = 0
        self.window_start = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            if now - self.window_start >= self.window:
                self.window_start = now
                self.count = 0
            
            if self.count + tokens <= self.limit:
                self.count += tokens
                return True
            return False
    
    def get_remaining(self) -> int:
        with self.lock:
            return max(0, self.limit - self.count)
    
    def get_reset(self) -> int:
        with self.lock:
            return int(self.window_start + self.window)

class SlidingWindow:
    """滑动窗口算法"""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 移除窗口外的请求
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()
            
            if len(self.requests) + tokens <= self.limit:
                for _ in range(tokens):
                    self.requests.append(now)
                return True
            return False
    
    def get_remaining(self) -> int:
        with self.lock:
            now = time.time()
            while self.requests and now - self.requests[0] > self.window:
                self.requests.popleft()
            return max(0, self.limit - len(self.requests))
    
    def get_reset(self) -> int:
        with self.lock:
            if not self.requests:
                return 0
            oldest = self.requests[0]
            return int(oldest + self.window)

class SlidingLog:
    """滑动日志算法"""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.logs = []
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 过滤日志
            self.logs = [t for t in self.logs if now - t <= self.window]
            
            if len(self.logs) + tokens <= self.limit:
                self.logs.extend([now] * tokens)
                return True
            return False
    
    def get_remaining(self) -> int:
        with self.lock:
            now = time.time()
            self.logs = [t for t in self.logs if now - t <= self.window]
            return max(0, self.limit - len(self.logs))
    
    def get_reset(self) -> int:
        with self.lock:
            if not self.logs:
                return 0
            oldest = min(self.logs)
            return int(oldest + self.window)

class RateLimiter:
    """
    速率限制器
    
    负责API调用的频率限制。
    """
    
    def __init__(self, config: Optional[RateLimiterConfig] = None):
        """
        初始化速率限制器
        
        Args:
            config: 速率限制器配置
        """
        self.config = config or RateLimiterConfig()
        
        # 本地限流器存储
        self.limiters: Dict[str, Any] = {}
        self.rules: Dict[str, RateLimitRule] = {}
        
        # Redis客户端（分布式）
        self.redis_client = None
        if REDIS_AVAILABLE:
            self._init_redis()
        
        # 清理线程
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "rules_evaluated": 0
        }
        
        # 添加默认规则
        self._add_default_rule()
        
        # 启动清理
        self._start_cleanup()
        
        logger.info("RateLimiter initialized")
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def _add_default_rule(self):
        """添加默认规则"""
        default_rule = RateLimitRule(
            id="default",
            name="Default Rate Limit",
            limits=[
                RateLimit(
                    key="default",
                    limit=self.config.default_limit,
                    window=self.config.default_window,
                    strategy=LimitStrategy.SLIDING_WINDOW,
                    scope=LimitScope.GLOBAL
                )
            ]
        )
        self.rules["default"] = default_rule
    
    def _start_cleanup(self):
        """启动清理线程"""
        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                try:
                    self._cleanup_old_limiters()
                    self._stop_cleanup.wait(self.config.cleanup_interval)
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.debug("Rate limiter cleanup started")
    
    def _cleanup_old_limiters(self):
        """清理旧的限流器"""
        # 简单的LRU清理
        if len(self.limiters) > self.config.max_storage:
            # 按最后访问时间排序并删除最旧的
            sorted_limiters = sorted(
                self.limiters.items(),
                key=lambda x: getattr(x[1], 'last_access', 0)
            )
            to_remove = len(self.limiters) - self.config.max_storage
            for key, _ in sorted_limiters[:to_remove]:
                del self.limiters[key]
                logger.debug(f"Removed old limiter: {key}")
    
    def _get_limiter_key(self, rule: RateLimitRule, limit: RateLimit,
                        identifier: str) -> str:
        """获取限流器键"""
        components = [
            rule.id,
            limit.key,
            limit.scope.value,
            identifier or "global"
        ]
        return hashlib.md5(":".join(components).encode()).hexdigest()
    
    def _create_limiter(self, limit: RateLimit) -> Any:
        """创建限流器"""
        if limit.strategy == LimitStrategy.TOKEN_BUCKET:
            fill_rate = limit.limit / limit.window
            return TokenBucket(limit.limit, fill_rate)
        elif limit.strategy == LimitStrategy.LEAKY_BUCKET:
            leak_rate = limit.limit / limit.window
            return LeakyBucket(limit.limit, leak_rate)
        elif limit.strategy == LimitStrategy.FIXED_WINDOW:
            return FixedWindow(limit.limit, limit.window)
        elif limit.strategy == LimitStrategy.SLIDING_WINDOW:
            return SlidingWindow(limit.limit, limit.window)
        elif limit.strategy == LimitStrategy.SLIDING_LOG:
            return SlidingLog(limit.limit, limit.window)
        else:
            return SlidingWindow(limit.limit, limit.window)
    
    def _check_redis_limit(self, key: str, limit: RateLimit) -> RateLimitResult:
        """使用Redis检查限制"""
        if not self.redis_client:
            return self._check_local_limit(key, limit)
        
        redis_key = f"ratelimit:{key}"
        now = time.time()
        window_start = now - limit.window
        
        try:
            # 使用Redis事务
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(now): now})
            pipe.expire(redis_key, limit.window)
            results = pipe.execute()
            
            count = results[1]  # zcard结果
            
            if count < limit.limit:
                remaining = limit.limit - count - 1
                reset = int(window_start + limit.window)
                return RateLimitResult(
                    allowed=True,
                    limit=limit.limit,
                    remaining=remaining,
                    reset=reset
                )
            else:
                # 获取最早的请求时间
                oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    reset = int(oldest[0][1] + limit.window)
                else:
                    reset = int(now + limit.window)
                
                return RateLimitResult(
                    allowed=False,
                    limit=limit.limit,
                    remaining=0,
                    reset=reset,
                    retry_after=reset - int(now)
                )
                
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            return self._check_local_limit(key, limit)
    
    def _check_local_limit(self, key: str, limit: RateLimit) -> RateLimitResult:
        """使用本地存储检查限制"""
        if key not in self.limiters:
            self.limiters[key] = self._create_limiter(limit)
        
        limiter = self.limiters[key]
        limiter.last_access = time.time()
        
        allowed = limiter.consume()
        
        if hasattr(limiter, 'get_remaining'):
            remaining = limiter.get_remaining()
        else:
            remaining = 0
        
        if hasattr(limiter, 'get_reset'):
            reset = limiter.get_reset()
        else:
            reset = int(time.time() + limit.window)
        
        return RateLimitResult(
            allowed=allowed,
            limit=limit.limit,
            remaining=remaining,
            reset=reset
        )
    
    def add_rule(self, rule: RateLimitRule) -> str:
        """
        添加限流规则
        
        Args:
            rule: 限流规则
        
        Returns:
            规则ID
        """
        self.rules[rule.id] = rule
        logger.info(f"Rate limit rule added: {rule.name} ({rule.id})")
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        移除限流规则
        
        Args:
            rule_id: 规则ID
        
        Returns:
            是否成功
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Rate limit rule removed: {rule_id}")
            return True
        return False
    
    def check_limit(self, identifier: str, endpoint: Optional[str] = None,
                   method: Optional[str] = None, headers: Optional[Dict] = None) -> RateLimitResult:
        """
        检查速率限制
        
        Args:
            identifier: 标识符（IP、用户ID、API密钥等）
            endpoint: 端点路径
            method: HTTP方法
            headers: 请求头
        
        Returns:
            限制检查结果
        """
        self.stats["total_requests"] += 1
        
        # 收集上下文
        context = {
            "identifier": identifier,
            "endpoint": endpoint,
            "method": method,
            "headers": headers or {}
        }
        
        # 查找匹配的规则
        applicable_rules = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            # 检查条件
            matches = True
            for key, value in rule.conditions.items():
                if key in context and context[key] != value:
                    matches = False
                    break
            
            if matches:
                applicable_rules.append(rule)
        
        # 按优先级排序
        applicable_rules.sort(key=lambda r: r.priority)
        
        # 应用规则
        for rule in applicable_rules:
            self.stats["rules_evaluated"] += 1
            
            for limit in rule.limits:
                # 根据作用域生成键
                if limit.scope == LimitScope.GLOBAL:
                    key = self._get_limiter_key(rule, limit, "global")
                elif limit.scope == LimitScope.IP:
                    key = self._get_limiter_key(rule, limit, identifier)
                elif limit.scope == LimitScope.USER:
                    key = self._get_limiter_key(rule, limit, identifier)
                elif limit.scope == LimitScope.API_KEY:
                    api_key = context.get("headers", {}).get("X-API-Key")
                    key = self._get_limiter_key(rule, limit, api_key or identifier)
                elif limit.scope == LimitScope.ENDPOINT:
                    key = self._get_limiter_key(rule, limit, endpoint or "")
                else:
                    key = self._get_limiter_key(rule, limit, identifier)
                
                # 检查限制
                if self.redis_client and limit.scope != LimitScope.GLOBAL:
                    result = self._check_redis_limit(key, limit)
                else:
                    result = self._check_local_limit(key, limit)
                
                if not result.allowed:
                    self.stats["blocked_requests"] += 1
                    return result
        
        self.stats["allowed_requests"] += 1
        
        # 返回成功结果（使用最后一个限制）
        if applicable_rules:
            last_rule = applicable_rules[-1]
            if last_rule.limits:
                last_limit = last_rule.limits[-1]
                key = self._get_limiter_key(last_rule, last_limit, identifier)
                if self.redis_client:
                    result = self._check_redis_limit(key, last_limit)
                else:
                    result = self._check_local_limit(key, last_limit)
                return result
        
        # 没有规则，使用默认
        default_key = f"default:{identifier}"
        return self._check_local_limit(default_key, RateLimit(
            key="default",
            limit=self.config.default_limit,
            window=self.config.default_window
        ))
    
    def get_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """
        获取速率限制响应头
        
        Args:
            result: 限制检查结果
        
        Returns:
            响应头字典
        """
        if not self.config.headers_enabled:
            return {}
        
        headers = {
            self.config.limit_header: str(result.limit),
            self.config.remaining_header: str(result.remaining),
            self.config.reset_header: str(result.reset)
        }
        
        if result.retry_after:
            headers["Retry-After"] = str(result.retry_after)
        
        return headers
    
    def reset_limit(self, identifier: str, rule_id: Optional[str] = None):
        """
        重置限制
        
        Args:
            identifier: 标识符
            rule_id: 规则ID
        """
        if rule_id:
            rule = self.rules.get(rule_id)
            if rule:
                for limit in rule.limits:
                    key = self._get_limiter_key(rule, limit, identifier)
                    if key in self.limiters:
                        del self.limiters[key]
                    
                    if self.redis_client:
                        redis_key = f"ratelimit:{key}"
                        self.redis_client.delete(redis_key)
        else:
            # 重置所有相关限制
            prefix = f"{identifier}:"
            keys_to_delete = [k for k in self.limiters.keys() if prefix in k]
            for key in keys_to_delete:
                del self.limiters[key]
            
            if self.redis_client:
                for key in keys_to_delete:
                    self.redis_client.delete(f"ratelimit:{key}")
        
        logger.info(f"Rate limit reset for {identifier}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取速率限制器状态
        
        Returns:
            状态字典
        """
        return {
            "rules": {
                "total": len(self.rules),
                "active": len([r for r in self.rules.values() if r.enabled])
            },
            "limiters": {
                "local": len(self.limiters),
                "redis": self.redis_client is not None
            },
            "stats": self.stats,
            "config": {
                "default_limit": self.config.default_limit,
                "default_window": self.config.default_window,
                "redis_enabled": self.redis_client is not None
            }
        }
    
    def shutdown(self):
        """关闭速率限制器"""
        logger.info("Shutting down RateLimiter...")
        
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2)
        
        if self.redis_client:
            self.redis_client.close()
        
        self.limiters.clear()
        self.rules.clear()
        
        logger.info("RateLimiter shutdown completed")

# 单例模式实现
_rate_limiter_instance: Optional[RateLimiter] = None

def get_rate_limiter(config: Optional[RateLimiterConfig] = None) -> RateLimiter:
    """
    获取速率限制器单例
    
    Args:
        config: 速率限制器配置
    
    Returns:
        速率限制器实例
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter(config)
    return _rate_limiter_instance

