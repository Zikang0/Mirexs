"""
负载均衡器：请求负载均衡
负责请求的负载均衡和流量分发
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from statistics import mean, median

class LoadBalanceStrategy(Enum):
    """负载均衡策略枚举"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"

@dataclass
class BackendServer:
    """后端服务器"""
    server_id: str
    endpoint: str
    weight: int = 1
    max_connections: int = 100
    is_healthy: bool = True
    current_connections: int = 0
    response_times: List[float] = None
    last_health_check: float = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    @property
    def average_response_time(self) -> float:
        """平均响应时间"""
        if not self.response_times:
            return 0.0
        return mean(self.response_times[-100:])  # 最近100次
    
    @property
    def connection_utilization(self) -> float:
        """连接利用率"""
        return self.current_connections / self.max_connections if self.max_connections > 0 else 0

@dataclass
class LoadBalanceStats:
    """负载均衡统计"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    backend_stats: Dict[str, Dict[str, Any]]

class LoadBalancer:
    """负载均衡器"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN):
        self.backend_servers: Dict[str, BackendServer] = {}
        self.strategy = strategy
        self.current_index: int = 0
        self.health_check_task: Optional[asyncio.Task] = None
        self.stats = LoadBalanceStats(0, 0, 0, 0.0, {})
        self.initialized = False
        
    async def initialize(self):
        """初始化负载均衡器"""
        if self.initialized:
            return
            
        logging.info("初始化负载均衡器...")
        
        # 启动健康检查
        self.health_check_task = asyncio.create_task(self._health_check_worker())
        
        self.initialized = True
        logging.info(f"负载均衡器初始化完成，策略: {self.strategy.value}")
    
    async def add_backend(self, server_id: str, endpoint: str, weight: int = 1,
                         max_connections: int = 100) -> bool:
        """添加后端服务器"""
        if server_id in self.backend_servers:
            logging.warning(f"后端服务器已存在: {server_id}")
            return False
        
        server = BackendServer(
            server_id=server_id,
            endpoint=endpoint,
            weight=weight,
            max_connections=max_connections
        )
        
        self.backend_servers[server_id] = server
        self.stats.backend_stats[server_id] = {
            "requests": 0,
            "successful": 0,
            "failed": 0,
            "average_response_time": 0.0
        }
        
        logging.info(f"后端服务器添加成功: {server_id} -> {endpoint}")
        return True
    
    async def remove_backend(self, server_id: str):
        """移除后端服务器"""
        if server_id in self.backend_servers:
            del self.backend_servers[server_id]
            if server_id in self.stats.backend_stats:
                del self.stats.backend_stats[server_id]
            logging.info(f"后端服务器移除成功: {server_id}")
    
    async def select_backend(self, client_ip: str = None) -> Optional[BackendServer]:
        """选择后端服务器"""
        healthy_servers = [
            server for server in self.backend_servers.values() 
            if server.is_healthy and server.current_connections < server.max_connections
        ]
        
        if not healthy_servers:
            logging.warning("没有健康的后端服务器可用")
            return None
        
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_selection(healthy_servers)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_selection(healthy_servers)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_selection(healthy_servers)
        elif self.strategy == LoadBalanceStrategy.IP_HASH:
            return self._ip_hash_selection(healthy_servers, client_ip)
        elif self.strategy == LoadBalanceStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_selection(healthy_servers)
        else:
            return self._round_robin_selection(healthy_servers)
    
    def _round_robin_selection(self, servers: List[BackendServer]) -> BackendServer:
        """轮询选择"""
        if not servers:
            return None
        
        server = servers[self.current_index % len(servers)]
        self.current_index = (self.current_index + 1) % len(servers)
        return server
    
    def _least_connections_selection(self, servers: List[BackendServer]) -> BackendServer:
        """最少连接选择"""
        if not servers:
            return None
        
        return min(servers, key=lambda s: s.current_connections)
    
    def _weighted_round_robin_selection(self, servers: List[BackendServer]) -> BackendServer:
        """加权轮询选择"""
        if not servers:
            return None
        
        # 计算总权重
        total_weight = sum(server.weight for server in servers)
        
        # 选择服务器
        current = self.current_index
        for server in servers:
            if current < server.weight:
                selected = server
                break
            current -= server.weight
        else:
            selected = servers[0]
        
        self.current_index = (self.current_index + 1) % total_weight
        return selected
    
    def _ip_hash_selection(self, servers: List[BackendServer], client_ip: str) -> BackendServer:
        """IP哈希选择"""
        if not servers or not client_ip:
            return self._round_robin_selection(servers)
        
        # 计算IP哈希
        ip_hash = hash(client_ip)
        index = ip_hash % len(servers)
        return servers[index]
    
    def _least_response_time_selection(self, servers: List[BackendServer]) -> BackendServer:
        """最少响应时间选择"""
        if not servers:
            return None
        
        return min(servers, key=lambda s: s.average_response_time)
    
    async def forward_request(self, method: str, path: str, data: Dict = None,
                            headers: Dict = None, client_ip: str = None) -> Dict[str, Any]:
        """转发请求"""
        start_time = time.time()
        
        # 选择后端服务器
        backend = await self.select_backend(client_ip)
        if not backend:
            self.stats.failed_requests += 1
            raise RuntimeError("没有可用的后端服务器")
        
        # 更新连接计数
        backend.current_connections += 1
        self.stats.total_requests += 1
        self.stats.backend_stats[backend.server_id]["requests"] += 1
        
        try:
            # 发送请求（这里使用aiohttp，实际可以根据需要调整）
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{backend.endpoint}{path}"
                
                async with session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers
                ) as response:
                    
                    result = {
                        "status_code": response.status,
                        "backend": backend.server_id,
                        "data": await response.json() if response.content_type == 'application/json' else await response.text()
                    }
                    
                    # 记录成功
                    self.stats.successful_requests += 1
                    self.stats.backend_stats[backend.server_id]["successful"] += 1
                    
                    return result
                    
        except Exception as e:
            # 记录失败
            self.stats.failed_requests += 1
            self.stats.backend_stats[backend.server_id]["failed"] += 1
            logging.error(f"请求转发失败 {backend.server_id}: {e}")
            raise
            
        finally:
            # 更新连接计数和响应时间
            backend.current_connections -= 1
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            backend.response_times.append(response_time)
            
            # 限制响应时间记录数量
            if len(backend.response_times) > 1000:
                backend.response_times.pop(0)
            
            # 更新统计
            self._update_stats()
    
    def _update_stats(self):
        """更新统计信息"""
        all_response_times = []
        for server in self.backend_servers.values():
            all_response_times.extend(server.response_times)
        
        if all_response_times:
            self.stats.average_response_time = mean(all_response_times)
        
        for server_id, server in self.backend_servers.items():
            if server.response_times:
                self.stats.backend_stats[server_id]["average_response_time"] = mean(server.response_times[-100:])
    
    async def _health_check_worker(self):
        """健康检查工作线程"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._perform_health_checks()
            except Exception as e:
                logging.error(f"健康检查错误: {e}")
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        tasks = []
        for server in self.backend_servers.values():
            task = asyncio.create_task(self._check_server_health(server))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_server_health(self, server: BackendServer):
        """检查服务器健康状态"""
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                health_url = f"{server.endpoint}/health"
                async with session.get(health_url) as response:
                    server.is_healthy = (response.status == 200)
                    server.last_health_check = time.time()
                    
        except Exception as e:
            server.is_healthy = False
            server.last_health_check = time.time()
            logging.debug(f"健康检查失败 {server.server_id}: {e}")
    
    def get_balancer_stats(self) -> Dict[str, Any]:
        """获取负载均衡器统计"""
        healthy_servers = sum(1 for server in self.backend_servers.values() if server.is_healthy)
        total_connections = sum(server.current_connections for server in self.backend_servers.values())
        
        return {
            "strategy": self.strategy.value,
            "total_backends": len(self.backend_servers),
            "healthy_backends": healthy_servers,
            "total_connections": total_connections,
            "request_stats": {
                "total": self.stats.total_requests,
                "successful": self.stats.successful_requests,
                "failed": self.stats.failed_requests,
                "success_rate": (self.stats.successful_requests / self.stats.total_requests * 100) if self.stats.total_requests > 0 else 0,
                "average_response_time": self.stats.average_response_time
            },
            "backend_servers": [
                {
                    "id": server.server_id,
                    "endpoint": server.endpoint,
                    "weight": server.weight,
                    "is_healthy": server.is_healthy,
                    "current_connections": server.current_connections,
                    "max_connections": server.max_connections,
                    "utilization": server.connection_utilization,
                    "average_response_time": server.average_response_time,
                    "last_health_check": server.last_health_check
                }
                for server in self.backend_servers.values()
            ]
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

# 全局负载均衡器实例
load_balancer = LoadBalancer()
