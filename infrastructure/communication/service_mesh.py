"""
服务网格：微服务之间的通信管理
负责微服务的注册、发现、负载均衡和通信管理
"""

import asyncio
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import aiohttp

class ServiceStatus(Enum):
    """服务状态枚举"""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"

class ServiceType(Enum):
    """服务类型枚举"""
    COGNITIVE = "cognitive"
    INTERACTION = "interaction"
    STORAGE = "storage"
    NETWORK = "network"
    SECURITY = "security"
    MONITORING = "monitoring"

@dataclass
class ServiceEndpoint:
    """服务端点"""
    service_id: str
    service_type: ServiceType
    endpoint: str
    status: ServiceStatus
    health_check_url: str
    load_balancing_weight: int = 1
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = None

class ServiceMesh:
    """服务网格"""
    
    def __init__(self):
        self.services: Dict[str, ServiceEndpoint] = {}
        self.service_registry: Dict[ServiceType, List[str]] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.initialized = False
        
    async def initialize(self):
        """初始化服务网格"""
        if self.initialized:
            return
            
        logging.info("初始化服务网格...")
        
        # 创建HTTP会话
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        
        # 启动健康检查
        self.health_check_task = asyncio.create_task(self._health_check_worker())
        
        self.initialized = True
        logging.info("服务网格初始化完成")
    
    async def register_service(self, service_id: str, service_type: ServiceType,
                             endpoint: str, health_check_url: str = None,
                             metadata: Dict[str, Any] = None) -> bool:
        """注册服务"""
        if service_id in self.services:
            logging.warning(f"服务已存在: {service_id}")
            return False
        
        if health_check_url is None:
            health_check_url = f"{endpoint}/health"
        
        service = ServiceEndpoint(
            service_id=service_id,
            service_type=service_type,
            endpoint=endpoint,
            status=ServiceStatus.STARTING,
            health_check_url=health_check_url,
            metadata=metadata or {}
        )
        
        self.services[service_id] = service
        
        # 更新服务注册表
        if service_type not in self.service_registry:
            self.service_registry[service_type] = []
        self.service_registry[service_type].append(service_id)
        
        logging.info(f"服务注册成功: {service_id} ({service_type.value})")
        return True
    
    async def unregister_service(self, service_id: str):
        """注销服务"""
        if service_id in self.services:
            service = self.services[service_id]
            
            # 从注册表中移除
            if service.service_type in self.service_registry:
                if service_id in self.service_registry[service.service_type]:
                    self.service_registry[service.service_type].remove(service_id)
            
            del self.services[service_id]
            logging.info(f"服务注销成功: {service_id}")
    
    async def discover_services(self, service_type: ServiceType, 
                              healthy_only: bool = True) -> List[ServiceEndpoint]:
        """发现服务"""
        if service_type not in self.service_registry:
            return []
        
        service_ids = self.service_registry[service_type]
        services = [self.services[sid] for sid in service_ids]
        
        if healthy_only:
            services = [s for s in services if s.status == ServiceStatus.HEALTHY]
        
        return services
    
    async def call_service(self, service_type: ServiceType, method: str, path: str,
                         data: Dict = None, headers: Dict = None) -> Dict[str, Any]:
        """调用服务"""
        # 发现可用服务
        available_services = await self.discover_services(service_type, healthy_only=True)
        if not available_services:
            raise RuntimeError(f"没有可用的服务: {service_type.value}")
        
        # 简单的负载均衡：选择第一个健康服务
        service = available_services[0]
        
        try:
            url = f"{service.endpoint}{path}"
            
            async with self.http_session.request(
                method=method,
                url=url,
                json=data,
                headers=headers
            ) as response:
                result = {
                    "status_code": response.status,
                    "service_id": service.service_id,
                    "data": await response.json() if response.content_type == 'application/json' else await response.text()
                }
                return result
                
        except Exception as e:
            logging.error(f"服务调用失败 {service.service_id}: {e}")
            # 标记服务为不健康
            service.status = ServiceStatus.UNHEALTHY
            raise
    
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
        for service in self.services.values():
            task = asyncio.create_task(self._check_service_health(service))
            tasks.append(task)
        
        # 并行执行所有健康检查
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_service_health(self, service: ServiceEndpoint):
        """检查服务健康状态"""
        try:
            async with self.http_session.get(service.health_check_url, timeout=5) as response:
                if response.status == 200:
                    service.status = ServiceStatus.HEALTHY
                else:
                    service.status = ServiceStatus.UNHEALTHY
                
                service.last_health_check = datetime.now()
                
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.last_health_check = datetime.now()
            logging.debug(f"服务健康检查失败 {service.service_id}: {e}")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        status_counts = {}
        type_counts = {}
        
        for service in self.services.values():
            status = service.status.value
            service_type = service.service_type.value
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[service_type] = type_counts.get(service_type, 0) + 1
        
        return {
            "total_services": len(self.services),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "services": [
                {
                    "id": service.service_id,
                    "type": service.service_type.value,
                    "endpoint": service.endpoint,
                    "status": service.status.value,
                    "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None
                }
                for service in self.services.values()
            ]
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

# 全局服务网格实例
service_mesh = ServiceMesh()
