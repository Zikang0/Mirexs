"""
资源管理器：动态管理 CPU、GPU、内存、磁盘等资源。

实现目标：
- 构造器兼容 `ResourceManager(config)` 调用方式
- GPU 资源统一按字节统计，避免和调用方的字节单位失配
- 可在缺少 `psutil/GPUtil` 时降级工作，而不是直接导入失败
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None


logger = logging.getLogger(__name__)
MB = 1024 * 1024


class ResourceType(Enum):
    """资源类型枚举。"""

    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class ResourceUsage:
    """资源使用情况。"""

    resource_type: ResourceType
    used: float
    total: float
    percentage: float
    timestamp: float


@dataclass
class ResourceRequest:
    """资源请求。"""

    resource_type: ResourceType
    amount: float
    priority: int = 1
    timeout: int = 30


class ResourceAllocation:
    """资源分配对象。"""

    def __init__(self, request: ResourceRequest):
        self.request = request
        self.allocated_amount = 0.0
        self.allocation_time = time.time()
        self.is_active = True

    def release(self) -> None:
        """释放资源标记。"""
        self.is_active = False


class ResourceManager:
    """资源管理器。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.resource_usage: Dict[ResourceType, ResourceUsage] = {}
        self.allocations: List[ResourceAllocation] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.initialized = False
        self.usage_history: List[Dict[ResourceType, ResourceUsage]] = []
        self.monitor_interval_seconds = float(self.config.get("monitor_interval_seconds", 5.0))
        self.history_limit = int(self.config.get("history_limit", 100))
        self.enable_gpu_monitor = bool(self.config.get("enable_gpu_monitor", True))

    async def initialize(self, hardware_info: Optional[Dict[str, Any]] = None) -> None:
        """初始化资源管理器。"""
        if self.initialized:
            return

        logger.info("初始化资源管理器...")
        await self._scan_resources(hardware_info=hardware_info)
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
        self.initialized = True
        logger.info("资源管理器初始化完成")

    async def shutdown(self) -> None:
        """关闭资源管理器后台监控任务。"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        self.initialized = False

    async def _monitoring_worker(self) -> None:
        """资源监控后台任务。"""
        while True:
            try:
                await asyncio.sleep(self.monitor_interval_seconds)
                await self._update_resource_usage()
                if len(self.usage_history) > self.history_limit:
                    self.usage_history.pop(0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("资源监控错误: %s", exc)

    async def _scan_resources(self, hardware_info: Optional[Dict[str, Any]] = None) -> None:
        """首次扫描系统资源。"""
        current_time = time.time()

        cpu_total = float(self._get_cpu_total(hardware_info))
        cpu_percent = float(self._get_cpu_percent())
        cpu_used = cpu_total * cpu_percent / 100.0 if cpu_total > 0 else 0.0
        self.resource_usage[ResourceType.CPU] = ResourceUsage(
            resource_type=ResourceType.CPU,
            used=cpu_used,
            total=cpu_total,
            percentage=cpu_percent,
            timestamp=current_time,
        )

        memory_total, memory_used, memory_percent = self._get_memory_snapshot(hardware_info)
        self.resource_usage[ResourceType.MEMORY] = ResourceUsage(
            resource_type=ResourceType.MEMORY,
            used=memory_used,
            total=memory_total,
            percentage=memory_percent,
            timestamp=current_time,
        )

        disk_total, disk_used, disk_percent = self._get_disk_snapshot()
        self.resource_usage[ResourceType.DISK] = ResourceUsage(
            resource_type=ResourceType.DISK,
            used=disk_used,
            total=disk_total,
            percentage=disk_percent,
            timestamp=current_time,
        )

        if self.enable_gpu_monitor:
            gpu_total, gpu_used, gpu_percent = await self._get_gpu_snapshot(hardware_info)
        else:
            gpu_total, gpu_used, gpu_percent = 0.0, 0.0, 0.0
        self.resource_usage[ResourceType.GPU] = ResourceUsage(
            resource_type=ResourceType.GPU,
            used=gpu_used,
            total=gpu_total,
            percentage=gpu_percent,
            timestamp=current_time,
        )

        logger.info("系统资源扫描完成")

    async def _update_resource_usage(self) -> None:
        """更新资源使用情况。"""
        current_time = time.time()

        cpu_usage = self.resource_usage.get(ResourceType.CPU)
        if cpu_usage:
            cpu_percent = float(self._get_cpu_percent())
            cpu_usage.used = cpu_usage.total * cpu_percent / 100.0 if cpu_usage.total > 0 else 0.0
            cpu_usage.percentage = cpu_percent
            cpu_usage.timestamp = current_time

        memory_usage = self.resource_usage.get(ResourceType.MEMORY)
        if memory_usage:
            total, used, percent = self._get_memory_snapshot()
            memory_usage.total = total
            memory_usage.used = used
            memory_usage.percentage = percent
            memory_usage.timestamp = current_time

        disk_usage = self.resource_usage.get(ResourceType.DISK)
        if disk_usage:
            total, used, percent = self._get_disk_snapshot()
            disk_usage.total = total
            disk_usage.used = used
            disk_usage.percentage = percent
            disk_usage.timestamp = current_time

        gpu_usage = self.resource_usage.get(ResourceType.GPU)
        if gpu_usage:
            total, used, percent = await self._get_gpu_snapshot()
            gpu_usage.total = total
            gpu_usage.used = used
            gpu_usage.percentage = percent
            gpu_usage.timestamp = current_time

        self.usage_history.append(
            {
                resource_type: ResourceUsage(
                    resource_type=usage.resource_type,
                    used=usage.used,
                    total=usage.total,
                    percentage=usage.percentage,
                    timestamp=usage.timestamp,
                )
                for resource_type, usage in self.resource_usage.items()
            }
        )

    async def request_resources(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """请求资源分配。"""
        if request.resource_type not in self.resource_usage:
            if not self.initialized:
                await self.initialize()
            if request.resource_type not in self.resource_usage:
                logger.error("不支持的资源类型: %s", request.resource_type)
                return None

        current_usage = self.resource_usage[request.resource_type]
        available = max(0.0, current_usage.total - current_usage.used)

        if current_usage.total <= 0 or available < request.amount:
            logger.warning(
                "资源不足: %s, 请求=%s, 可用=%s",
                request.resource_type.value,
                request.amount,
                available,
            )
            return None

        allocation = ResourceAllocation(request)
        allocation.allocated_amount = float(request.amount)

        current_usage.used += allocation.allocated_amount
        current_usage.percentage = self._calculate_percentage(current_usage.used, current_usage.total)
        current_usage.timestamp = time.time()

        self.allocations.append(allocation)
        logger.info("资源分配成功: %s -> %s", request.resource_type.value, request.amount)
        return allocation

    async def release_resources(self, allocation: ResourceAllocation) -> None:
        """释放资源。"""
        if not allocation.is_active:
            return

        allocation.release()
        if allocation in self.allocations:
            self.allocations.remove(allocation)

        usage = self.resource_usage.get(allocation.request.resource_type)
        if usage:
            usage.used = max(0.0, usage.used - allocation.allocated_amount)
            usage.percentage = self._calculate_percentage(usage.used, usage.total)
            usage.timestamp = time.time()

        logger.info(
            "资源释放成功: %s -> %s",
            allocation.request.resource_type.value,
            allocation.allocated_amount,
        )

    def get_resource_usage(self, resource_type: ResourceType) -> Optional[ResourceUsage]:
        """获取某类资源使用情况。"""
        return self.resource_usage.get(resource_type)

    def get_all_resource_usage(self) -> Dict[ResourceType, ResourceUsage]:
        """获取所有资源使用情况。"""
        return self.resource_usage.copy()

    def get_resource_stats(self) -> Dict[str, Any]:
        """获取资源统计信息。"""
        total_allocations = len(self.allocations)
        active_allocations = sum(1 for allocation in self.allocations if allocation.is_active)

        return {
            "total_allocations": total_allocations,
            "active_allocations": active_allocations,
            "resource_usage": {
                resource_type.value: {
                    "used": usage.used,
                    "total": usage.total,
                    "percentage": usage.percentage,
                }
                for resource_type, usage in self.resource_usage.items()
            },
            "history_size": len(self.usage_history),
        }

    async def optimize_resources(self) -> None:
        """执行资源优化。"""
        logger.info("执行资源优化...")

        current_time = time.time()
        expired_allocations = [
            allocation
            for allocation in self.allocations
            if allocation.is_active and (current_time - allocation.allocation_time) > allocation.request.timeout
        ]

        for allocation in expired_allocations:
            await self.release_resources(allocation)
            logger.info("清理过期资源分配: %s", allocation.request.resource_type.value)

        await self._memory_optimization()
        await self._cpu_optimization()

    async def _memory_optimization(self) -> None:
        memory_usage = self.get_resource_usage(ResourceType.MEMORY)
        if memory_usage and memory_usage.percentage > 80:
            logger.warning("内存使用率过高，建议清理缓存")

    async def _cpu_optimization(self) -> None:
        cpu_usage = self.get_resource_usage(ResourceType.CPU)
        if cpu_usage and cpu_usage.percentage > 90:
            logger.warning("CPU 使用率过高，建议调整任务调度")

    def _get_cpu_total(self, hardware_info: Optional[Dict[str, Any]] = None) -> int:
        if hardware_info:
            cpu_info = hardware_info.get("cpu", {})
            if cpu_info.get("cores_logical"):
                return int(cpu_info["cores_logical"])
        if psutil is not None:
            count = psutil.cpu_count(logical=True)
            if count:
                return int(count)
        return max(1, os.cpu_count() or 1)

    def _get_cpu_percent(self) -> float:
        if psutil is None:
            return 0.0
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    def _get_memory_snapshot(
        self,
        hardware_info: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, float, float]:
        if psutil is not None:
            try:
                memory = psutil.virtual_memory()
                return float(memory.total), float(memory.used), float(memory.percent)
            except Exception:
                pass

        if hardware_info:
            memory_info = hardware_info.get("memory", {})
            total = float(memory_info.get("total", 0))
            used = float(memory_info.get("used", 0))
            percent = float(memory_info.get("percent", 0))
            return total, used, percent

        return 0.0, 0.0, 0.0

    def _get_disk_snapshot(self) -> tuple[float, float, float]:
        disk_root = Path.cwd().anchor or os.getcwd()
        if psutil is not None:
            try:
                usage = psutil.disk_usage(disk_root)
                return float(usage.total), float(usage.used), float(usage.percent)
            except Exception:
                pass

        try:
            total, used, free = shutil.disk_usage(disk_root)
            percent = self._calculate_percentage(float(used), float(total))
            return float(total), float(used), percent
        except Exception:
            return 0.0, 0.0, 0.0

    async def _get_gpu_snapshot(
        self,
        hardware_info: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, float, float]:
        try:
            import GPUtil  # type: ignore

            gpus = GPUtil.getGPUs()
            if not gpus:
                return 0.0, 0.0, 0.0

            total = float(sum(gpu.memoryTotal for gpu in gpus) * MB)
            used = float(sum(gpu.memoryUsed for gpu in gpus) * MB)
            percent = self._calculate_percentage(used, total)
            return total, used, percent
        except Exception:
            pass

        if hardware_info:
            gpu_info = hardware_info.get("gpu", {})
            memory_total = float(gpu_info.get("memory_total", 0))
            if memory_total > 0:
                total = memory_total * MB if memory_total < MB else memory_total
                return total, 0.0, 0.0

        return 0.0, 0.0, 0.0

    def _calculate_percentage(self, used: float, total: float) -> float:
        if total <= 0:
            return 0.0
        return min(100.0, max(0.0, used / total * 100.0))


resource_manager = ResourceManager()
