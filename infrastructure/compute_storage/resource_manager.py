"""
资源管理器：动态管理CPU、GPU、内存等资源
负责系统资源的监控、分配和优化
"""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

class ResourceType(Enum):
    """资源类型枚举"""
    CPU = "cpu"
    GPU = "gpu" 
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"

@dataclass
class ResourceUsage:
    """资源使用情况"""
    resource_type: ResourceType
    used: float
    total: float
    percentage: float
    timestamp: float

@dataclass
class ResourceRequest:
    """资源请求"""
    resource_type: ResourceType
    amount: float
    priority: int = 1
    timeout: int = 30

class ResourceAllocation:
    """资源分配"""
    
    def __init__(self, request: ResourceRequest):
        self.request = request
        self.allocated_amount = 0.0
        self.allocation_time = time.time()
        self.is_active = True
    
    def release(self):
        """释放资源"""
        self.is_active = False

class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.resource_usage: Dict[ResourceType, ResourceUsage] = {}
        self.allocations: List[ResourceAllocation] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.initialized = False
        self.usage_history: List[Dict[ResourceType, ResourceUsage]] = []
        
    async def initialize(self):
        """初始化资源管理器"""
        if self.initialized:
            return
            
        logging.info("初始化资源管理器...")
        
        # 启动资源监控
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        # 初始资源扫描
        await self._scan_resources()
        
        self.initialized = True
        logging.info("资源管理器初始化完成")
    
    async def _monitoring_worker(self):
        """资源监控工作线程"""
        while True:
            try:
                await asyncio.sleep(5)  # 每5秒监控一次
                await self._update_resource_usage()
                
                # 保留最近100次记录
                if len(self.usage_history) > 100:
                    self.usage_history.pop(0)
                    
            except Exception as e:
                logging.error(f"资源监控错误: {e}")
    
    async def _scan_resources(self):
        """扫描系统资源"""
        try:
            # CPU资源
            cpu_count = psutil.cpu_count()
            self.resource_usage[ResourceType.CPU] = ResourceUsage(
                resource_type=ResourceType.CPU,
                used=0,
                total=cpu_count,
                percentage=0,
                timestamp=time.time()
            )
            
            # 内存资源
            memory = psutil.virtual_memory()
            self.resource_usage[ResourceType.MEMORY] = ResourceUsage(
                resource_type=ResourceType.MEMORY,
                used=memory.used,
                total=memory.total,
                percentage=memory.percent,
                timestamp=time.time()
            )
            
            # 磁盘资源
            disk = psutil.disk_usage('/')
            self.resource_usage[ResourceType.DISK] = ResourceUsage(
                resource_type=ResourceType.DISK,
                used=disk.used,
                total=disk.total,
                percentage=(disk.used / disk.total * 100),
                timestamp=time.time()
            )
            
            # GPU资源（如果可用）
            await self._scan_gpu_resources()
            
            logging.info("系统资源扫描完成")
            
        except Exception as e:
            logging.error(f"资源扫描失败: {e}")
    
    async def _scan_gpu_resources(self):
        """扫描GPU资源"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if gpus:
                gpu = gpus[0]  # 使用第一个GPU
                self.resource_usage[ResourceType.GPU] = ResourceUsage(
                    resource_type=ResourceType.GPU,
                    used=gpu.memoryUsed,
                    total=gpu.memoryTotal,
                    percentage=gpu.memoryUtil * 100,
                    timestamp=time.time()
                )
            else:
                # 没有GPU，创建模拟数据
                self.resource_usage[ResourceType.GPU] = ResourceUsage(
                    resource_type=ResourceType.GPU,
                    used=0,
                    total=0,
                    percentage=0,
                    timestamp=time.time()
                )
                
        except ImportError:
            logging.warning("GPUtil未安装，无法监控GPU资源")
            self.resource_usage[ResourceType.GPU] = ResourceUsage(
                resource_type=ResourceType.GPU,
                used=0,
                total=0,
                percentage=0,
                timestamp=time.time()
            )
    
    async def _update_resource_usage(self):
        """更新资源使用情况"""
        current_time = time.time()
        
        # 更新CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.resource_usage[ResourceType.CPU].used = cpu_percent
        self.resource_usage[ResourceType.CPU].percentage = cpu_percent
        self.resource_usage[ResourceType.CPU].timestamp = current_time
        
        # 更新内存使用率
        memory = psutil.virtual_memory()
        self.resource_usage[ResourceType.MEMORY].used = memory.used
        self.resource_usage[ResourceType.MEMORY].percentage = memory.percent
        self.resource_usage[ResourceType.MEMORY].timestamp = current_time
        
        # 更新磁盘使用率
        disk = psutil.disk_usage('/')
        self.resource_usage[ResourceType.DISK].used = disk.used
        self.resource_usage[ResourceType.DISK].percentage = (disk.used / disk.total * 100)
        self.resource_usage[ResourceType.DISK].timestamp = current_time
        
        # 更新GPU使用率
        if ResourceType.GPU in self.resource_usage:
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    self.resource_usage[ResourceType.GPU].used = gpu.memoryUsed
                    self.resource_usage[ResourceType.GPU].percentage = gpu.memoryUtil * 100
                    self.resource_usage[ResourceType.GPU].timestamp = current_time
            except:
                pass
        
        # 保存历史记录
        self.usage_history.append(self.resource_usage.copy())
    
    async def request_resources(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """请求资源分配"""
        if request.resource_type not in self.resource_usage:
            logging.error(f"不支持的资源类型: {request.resource_type}")
            return None
        
        current_usage = self.resource_usage[request.resource_type]
        available = current_usage.total - current_usage.used
        
        if available < request.amount:
            logging.warning(f"资源不足: {request.resource_type}, 请求: {request.amount}, 可用: {available}")
            return None
        
        # 创建资源分配
        allocation = ResourceAllocation(request)
        allocation.allocated_amount = request.amount
        
        # 更新资源使用情况（模拟）
        current_usage.used += request.amount
        current_usage.percentage = (current_usage.used / current_usage.total * 100)
        
        self.allocations.append(allocation)
        
        logging.info(f"资源分配成功: {request.resource_type} - {request.amount}")
        return allocation
    
    async def release_resources(self, allocation: ResourceAllocation):
        """释放资源"""
        if not allocation.is_active:
            return
        
        allocation.release()
        
        # 从分配列表中移除
        if allocation in self.allocations:
            self.allocations.remove(allocation)
        
        # 更新资源使用情况
        if allocation.request.resource_type in self.resource_usage:
            current_usage = self.resource_usage[allocation.request.resource_type]
            current_usage.used = max(0, current_usage.used - allocation.allocated_amount)
            current_usage.percentage = (current_usage.used / current_usage.total * 100)
        
        logging.info(f"资源释放成功: {allocation.request.resource_type} - {allocation.allocated_amount}")
    
    def get_resource_usage(self, resource_type: ResourceType) -> Optional[ResourceUsage]:
        """获取资源使用情况"""
        return self.resource_usage.get(resource_type)
    
    def get_all_resource_usage(self) -> Dict[ResourceType, ResourceUsage]:
        """获取所有资源使用情况"""
        return self.resource_usage.copy()
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        total_allocations = len(self.allocations)
        active_allocations = sum(1 for alloc in self.allocations if alloc.is_active)
        
        stats = {
            "total_allocations": total_allocations,
            "active_allocations": active_allocations,
            "resource_usage": {},
            "history_size": len(self.usage_history)
        }
        
        for resource_type, usage in self.resource_usage.items():
            stats["resource_usage"][resource_type.value] = {
                "used": usage.used,
                "total": usage.total,
                "percentage": usage.percentage
            }
        
        return stats
    
    async def optimize_resources(self):
        """优化资源使用"""
        logging.info("执行资源优化...")
        
        # 清理过期的资源分配
        current_time = time.time()
        expired_allocations = [
            alloc for alloc in self.allocations 
            if alloc.is_active and (current_time - alloc.allocation_time) > alloc.request.timeout
        ]
        
        for allocation in expired_allocations:
            await self.release_resources(allocation)
            logging.info(f"清理过期资源分配: {allocation.request.resource_type}")
        
        # 其他优化策略...
        await self._memory_optimization()
        await self._cpu_optimization()
    
    async def _memory_optimization(self):
        """内存优化"""
        memory_usage = self.get_resource_usage(ResourceType.MEMORY)
        if memory_usage and memory_usage.percentage > 80:
            logging.warning("内存使用率过高，建议清理缓存")
    
    async def _cpu_optimization(self):
        """CPU优化"""
        cpu_usage = self.get_resource_usage(ResourceType.CPU)
        if cpu_usage and cpu_usage.percentage > 90:
            logging.warning("CPU使用率过高，建议调整任务调度")

# 全局资源管理器实例
resource_manager = ResourceManager()