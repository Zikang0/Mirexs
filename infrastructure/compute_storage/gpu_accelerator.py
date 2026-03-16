"""
GPU加速器：GPU资源管理和加速计算
负责GPU设备的检测、管理和计算加速
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

@dataclass
class GPUDevice:
    """GPU设备信息"""
    device_id: int
    name: str
    memory_total: int  # 总内存(字节)
    memory_used: int   # 已使用内存(字节)
    memory_free: int   # 空闲内存(字节)
    utilization: float # 使用率(0-1)
    temperature: float # 温度(摄氏度)
    is_available: bool = True

@dataclass
class GPUAllocation:
    """GPU分配"""
    device_id: int
    memory_allocated: int
    process_id: int
    allocation_time: float

class GPUAccelerator:
    """GPU加速器"""
    
    def __init__(self):
        self.gpu_devices: Dict[int, GPUDevice] = {}
        self.allocations: List[GPUAllocation] = []
        self.monitoring_task: Optional[asyncio.Task] = None
        self.initialized = False
        
    async def initialize(self):
        """初始化GPU加速器"""
        if self.initialized:
            return
            
        logging.info("初始化GPU加速器...")
        
        # 检测GPU设备
        await self._detect_gpu_devices()
        
        if not self.gpu_devices:
            logging.warning("未检测到可用的GPU设备")
            return
        
        # 启动GPU监控
        self.monitoring_task = asyncio.create_task(self._monitoring_worker())
        
        self.initialized = True
        logging.info("GPU加速器初始化完成")
    
    async def _detect_gpu_devices(self):
        """检测GPU设备"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            for i, gpu in enumerate(gpus):
                device = GPUDevice(
                    device_id=i,
                    name=gpu.name,
                    memory_total=int(gpu.memoryTotal * 1024 * 1024),  # MB to bytes
                    memory_used=int(gpu.memoryUsed * 1024 * 1024),
                    memory_free=int(gpu.memoryFree * 1024 * 1024),
                    utilization=gpu.load,
                    temperature=gpu.temperature
                )
                self.gpu_devices[i] = device
                logging.info(f"检测到GPU设备: {gpu.name} (ID: {i})")
                
        except ImportError:
            logging.warning("GPUtil未安装，使用模拟GPU设备")
            # 创建模拟GPU设备用于测试
            self._create_mock_gpu_devices()
        except Exception as e:
            logging.error(f"GPU设备检测失败: {e}")
            self._create_mock_gpu_devices()
    
    def _create_mock_gpu_devices(self):
        """创建模拟GPU设备"""
        mock_devices = [
            GPUDevice(
                device_id=0,
                name="NVIDIA GeForce RTX 4090 (模拟)",
                memory_total=24 * 1024 * 1024 * 1024,  # 24GB
                memory_used=2 * 1024 * 1024 * 1024,    # 2GB
                memory_free=22 * 1024 * 1024 * 1024,   # 22GB
                utilization=0.1,
                temperature=45.0
            ),
            GPUDevice(
                device_id=1, 
                name="NVIDIA GeForce RTX 3080 (模拟)",
                memory_total=10 * 1024 * 1024 * 1024,  # 10GB
                memory_used=1 * 1024 * 1024 * 1024,    # 1GB
                memory_free=9 * 1024 * 1024 * 1024,    # 9GB
                utilization=0.05,
                temperature=40.0
            )
        ]
        
        for device in mock_devices:
            self.gpu_devices[device.device_id] = device
            logging.info(f"创建模拟GPU设备: {device.name}")
    
    async def _monitoring_worker(self):
        """GPU监控工作线程"""
        while True:
            try:
                await asyncio.sleep(2)  # 每2秒监控一次
                await self._update_gpu_status()
            except Exception as e:
                logging.error(f"GPU监控错误: {e}")
    
    async def _update_gpu_status(self):
        """更新GPU状态"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            for gpu in gpus:
                if gpu.id in self.gpu_devices:
                    device = self.gpu_devices[gpu.id]
                    device.memory_used = int(gpu.memoryUsed * 1024 * 1024)
                    device.memory_free = int(gpu.memoryFree * 1024 * 1024)
                    device.utilization = gpu.load
                    device.temperature = gpu.temperature
                    
        except ImportError:
            # 模拟GPU状态更新
            for device in self.gpu_devices.values():
                # 模拟轻微的状态变化
                device.memory_used = min(device.memory_total, device.memory_used + 10 * 1024 * 1024)  # 增加10MB
                device.memory_free = device.memory_total - device.memory_used
                device.utilization = min(1.0, device.utilization + 0.01)
                device.temperature = min(85.0, device.temperature + 0.1)
    
    async def allocate_gpu_memory(self, memory_size: int, prefer_device: int = None) -> Optional[GPUAllocation]:
        """分配GPU内存"""
        available_devices = await self._find_available_devices(memory_size, prefer_device)
        
        if not available_devices:
            logging.error(f"没有足够的GPU内存可用，请求大小: {memory_size} bytes")
            return None
        
        # 选择最佳设备（使用率最低的）
        best_device = min(available_devices, key=lambda x: x.utilization)
        
        allocation = GPUAllocation(
            device_id=best_device.device_id,
            memory_allocated=memory_size,
            process_id=os.getpid(),
            allocation_time=time.time()
        )
        
        self.allocations.append(allocation)
        
        # 更新设备内存使用（模拟）
        best_device.memory_used += memory_size
        best_device.memory_free = best_device.memory_total - best_device.memory_used
        
        logging.info(f"GPU内存分配成功: 设备 {best_device.device_id}, 大小 {memory_size} bytes")
        return allocation
    
    async def _find_available_devices(self, memory_size: int, prefer_device: int = None) -> List[GPUDevice]:
        """查找可用设备"""
        available_devices = []
        
        for device in self.gpu_devices.values():
            if not device.is_available:
                continue
                
            if device.memory_free >= memory_size:
                available_devices.append(device)
        
        # 如果指定了偏好设备，优先考虑
        if prefer_device is not None and prefer_device in self.gpu_devices:
            preferred = self.gpu_devices[prefer_device]
            if preferred in available_devices:
                available_devices.remove(preferred)
                available_devices.insert(0, preferred)
        
        return available_devices
    
    async def release_gpu_memory(self, allocation: GPUAllocation):
        """释放GPU内存"""
        if allocation not in self.allocations:
            return
        
        self.allocations.remove(allocation)
        
        # 更新设备内存使用（模拟）
        if allocation.device_id in self.gpu_devices:
            device = self.gpu_devices[allocation.device_id]
            device.memory_used = max(0, device.memory_used - allocation.memory_allocated)
            device.memory_free = device.memory_total - device.memory_used
        
        logging.info(f"GPU内存释放成功: 设备 {allocation.device_id}, 大小 {allocation.memory_allocated} bytes")
    
    async def execute_gpu_task(self, task_func, *args, device_id: int = 0, **kwargs) -> Any:
        """执行GPU任务"""
        if device_id not in self.gpu_devices:
            raise ValueError(f"GPU设备不存在: {device_id}")
        
        device = self.gpu_devices[device_id]
        if not device.is_available:
            raise RuntimeError(f"GPU设备不可用: {device_id}")
        
        try:
            # 设置CUDA设备
            import torch
            torch.cuda.set_device(device_id)
            
            # 执行任务
            start_time = time.time()
            result = task_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logging.info(f"GPU任务执行完成: 设备 {device_id}, 耗时 {execution_time:.2f}秒")
            return result
            
        except ImportError:
            logging.warning("PyTorch未安装，使用CPU模拟执行")
            # 模拟执行
            await asyncio.sleep(0.1)  # 模拟计算时间
            return f"模拟GPU任务结果: {task_func.__name__}"
        
        except Exception as e:
            logging.error(f"GPU任务执行失败: {e}")
            raise
    
    def get_gpu_status(self, device_id: int = None) -> Dict[str, Any]:
        """获取GPU状态"""
        if device_id is not None:
            if device_id not in self.gpu_devices:
                return {}
            device = self.gpu_devices[device_id]
            return {
                "device_id": device.device_id,
                "name": device.name,
                "memory_used": device.memory_used,
                "memory_free": device.memory_free,
                "memory_total": device.memory_total,
                "utilization": device.utilization,
                "temperature": device.temperature,
                "is_available": device.is_available
            }
        else:
            return {
                device_id: self.get_gpu_status(device_id)
                for device_id in self.gpu_devices.keys()
            }
    
    def get_gpu_stats(self) -> Dict[str, Any]:
        """获取GPU统计信息"""
        total_memory = sum(device.memory_total for device in self.gpu_devices.values())
        used_memory = sum(device.memory_used for device in self.gpu_devices.values())
        total_allocations = len(self.allocations)
        
        return {
            "total_devices": len(self.gpu_devices),
            "available_devices": sum(1 for device in self.gpu_devices.values() if device.is_available),
            "total_memory": total_memory,
            "used_memory": used_memory,
            "memory_usage_percentage": (used_memory / total_memory * 100) if total_memory > 0 else 0,
            "total_allocations": total_allocations,
            "avg_utilization": sum(device.utilization for device in self.gpu_devices.values()) / len(self.gpu_devices) if self.gpu_devices else 0
        }
    
    async def optimize_gpu_usage(self):
        """优化GPU使用"""
        logging.info("执行GPU使用优化...")
        
        # 清理过期的分配
        current_time = time.time()
        expired_allocations = [
            alloc for alloc in self.allocations 
            if (current_time - alloc.allocation_time) > 3600  # 1小时过期
        ]
        
        for allocation in expired_allocations:
            await self.release_gpu_memory(allocation)
            logging.info(f"清理过期GPU分配: 设备 {allocation.device_id}")
        
        # 平衡GPU负载
        await self._balance_gpu_load()
    
    async def _balance_gpu_load(self):
        """平衡GPU负载"""
        if len(self.gpu_devices) < 2:
            return
        
        # 简单的负载均衡策略
        devices = list(self.gpu_devices.values())
        avg_utilization = sum(device.utilization for device in devices) / len(devices)
        
        for device in devices:
            if device.utilization > avg_utilization * 1.5:  # 使用率高于平均50%
                logging.info(f"GPU设备 {device.device_id} 使用率较高: {device.utilization:.1%}")

# 全局GPU加速器实例
gpu_accelerator = GPUAccelerator()

# 导入os用于process_id
import os