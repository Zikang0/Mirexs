"""
批处理器：批量数据处理
负责大规模批量数据的处理、并行计算和资源优化
"""

import asyncio
import multiprocessing as mp
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import concurrent.futures
import pandas as pd
import numpy as np

class ProcessingMode(Enum):
    """处理模式枚举"""
    SEQUENTIAL = "sequential"      # 顺序处理
    PARALLEL = "parallel"          # 并行处理
    DISTRIBUTED = "distributed"    # 分布式处理

class BatchStatus(Enum):
    """批处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int = 1000
    max_workers: int = None
    processing_mode: ProcessingMode = ProcessingMode.PARALLEL
    chunk_size: int = 100
    timeout: int = 3600  # 超时时间（秒）
    retry_attempts: int = 3

@dataclass
class BatchJob:
    """批处理作业"""
    job_id: str
    data: List[Any]
    processing_function: Callable
    config: BatchConfig
    status: BatchStatus
    created_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[Any] = None
    errors: List[str] = None
    progress: float = 0.0

@dataclass
class BatchResult:
    """批处理结果"""
    job_id: str
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    processing_time: float
    results: List[Any]
    summary: Dict[str, Any]

class BatchProcessor:
    """批处理器"""
    
    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self.executor: Optional[concurrent.futures.Executor] = None
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化批处理器"""
        if self.initialized:
            return
            
        logging.info("初始化批处理器...")
        
        # 创建线程池执行器
        max_workers = min(32, (mp.cpu_count() or 1) * 4)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        self.initialized = True
        logging.info(f"批处理器初始化完成，最大工作线程: {max_workers}")
    
    async def submit_job(self, data: List[Any], processing_function: Callable, 
                        config: BatchConfig = None, job_id: str = None) -> str:
        """提交批处理作业"""
        if not self.initialized:
            await self.initialize()
        
        if config is None:
            config = BatchConfig()
        
        if job_id is None:
            job_id = f"batch_{int(datetime.now().timestamp())}"
        
        # 创建批处理作业
        job = BatchJob(
            job_id=job_id,
            data=data,
            processing_function=processing_function,
            config=config,
            status=BatchStatus.PENDING,
            created_time=datetime.now(),
            results=[],
            errors=[]
        )
        
        self.jobs[job_id] = job
        
        # 启动处理任务
        processing_task = asyncio.create_task(self._process_batch_job(job))
        self.processing_tasks[job_id] = processing_task
        
        logging.info(f"批处理作业提交: {job_id}, 数据量: {len(data)}")
        return job_id
    
    async def _process_batch_job(self, job: BatchJob):
        """处理批处理作业"""
        job.status = BatchStatus.PROCESSING
        job.start_time = datetime.now()
        
        try:
            if job.config.processing_mode == ProcessingMode.SEQUENTIAL:
                results = await self._process_sequential(job)
            elif job.config.processing_mode == ProcessingMode.PARALLEL:
                results = await self._process_parallel(job)
            elif job.config.processing_mode == ProcessingMode.DISTRIBUTED:
                results = await self._process_distributed(job)
            else:
                raise ValueError(f"不支持的处理模式: {job.config.processing_mode}")
            
            job.results = results
            job.status = BatchStatus.COMPLETED
            job.progress = 1.0
            
            processing_time = (datetime.now() - job.start_time).total_seconds()
            logging.info(f"批处理作业完成: {job.job_id}, 处理时间: {processing_time:.2f}s")
            
        except Exception as e:
            job.status = BatchStatus.FAILED
            job.errors.append(str(e))
            logging.error(f"批处理作业失败 {job.job_id}: {e}")
        
        finally:
            job.end_time = datetime.now()
            
            # 清理处理任务
            if job.job_id in self.processing_tasks:
                del self.processing_tasks[job.job_id]
    
    async def _process_sequential(self, job: BatchJob) -> List[Any]:
        """顺序处理"""
        results = []
        total_items = len(job.data)
        
        for i, item in enumerate(job.data):
            try:
                # 执行处理函数
                if asyncio.iscoroutinefunction(job.processing_function):
                    result = await job.processing_function(item)
                else:
                    result = job.processing_function(item)
                
                results.append(result)
                job.progress = (i + 1) / total_items
                
                # 定期记录进度
                if (i + 1) % 100 == 0:
                    logging.debug(f"顺序处理进度: {job.job_id} - {i + 1}/{total_items}")
                    
            except Exception as e:
                logging.error(f"顺序处理失败 {job.job_id}[{i}]: {e}")
                results.append({"error": str(e), "item_index": i})
                
                if len(job.errors) < 10:  # 限制错误记录数量
                    job.errors.append(f"Item {i}: {e}")
        
        return results
    
    async def _process_parallel(self, job: BatchJob) -> List[Any]:
        """并行处理"""
        # 将数据分块
        chunks = self._chunk_data(job.data, job.config.chunk_size)
        total_chunks = len(chunks)
        
        results = []
        completed_chunks = 0
        
        # 并行处理每个数据块
        chunk_tasks = []
        for chunk_index, chunk in enumerate(chunks):
            task = asyncio.create_task(
                self._process_chunk(job, chunk, chunk_index)
            )
            chunk_tasks.append(task)
        
        # 等待所有块完成
        chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
        
        # 合并结果
        for chunk_result in chunk_results:
            if isinstance(chunk_result, Exception):
                logging.error(f"数据块处理失败: {chunk_result}")
                job.errors.append(str(chunk_result))
            else:
                results.extend(chunk_result)
                completed_chunks += 1
                job.progress = completed_chunks / total_chunks
        
        return results
    
    async def _process_distributed(self, job: BatchJob) -> List[Any]:
        """分布式处理（简化实现）"""
        # 在实际实现中，这里会使用Dask、Ray或Spark等分布式计算框架
        # 当前实现回退到并行处理
        
        logging.warning("分布式处理模式未完全实现，使用并行处理替代")
        return await self._process_parallel(job)
    
    async def _process_chunk(self, job: BatchJob, chunk: List[Any], chunk_index: int) -> List[Any]:
        """处理数据块"""
        chunk_results = []
        
        # 在线程池中执行处理（避免阻塞事件循环）
        loop = asyncio.get_event_loop()
        
        try:
            # 将处理函数包装为可并行执行的函数
            def process_chunk_sync():
                results = []
                for item in chunk:
                    try:
                        result = job.processing_function(item)
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e), "chunk_index": chunk_index})
                return results
            
            # 在线程池中执行
            chunk_results = await loop.run_in_executor(
                self.executor, 
                process_chunk_sync
            )
            
            logging.debug(f"数据块处理完成: {chunk_index}, 大小: {len(chunk)}")
            
        except Exception as e:
            logging.error(f"数据块处理失败 {chunk_index}: {e}")
            chunk_results = [{"error": str(e), "chunk_index": chunk_index}] * len(chunk)
        
        return chunk_results
    
    def _chunk_data(self, data: List[Any], chunk_size: int) -> List[List[Any]]:
        """将数据分块"""
        if chunk_size <= 0:
            return [data]
        
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        
        return chunks
    
    async def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """获取作业状态"""
        return self.jobs.get(job_id)
    
    async def wait_for_completion(self, job_id: str, timeout: float = None) -> bool:
        """等待作业完成"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
            return True
        
        if job_id in self.processing_tasks:
            try:
                if timeout:
                    await asyncio.wait_for(self.processing_tasks[job_id], timeout)
                else:
                    await self.processing_tasks[job_id]
                return True
            except asyncio.TimeoutError:
                return False
            except Exception:
                return False
        
        return False
    
    async def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status == BatchStatus.PROCESSING and job_id in self.processing_tasks:
            self.processing_tasks[job_id].cancel()
            try:
                await self.processing_tasks[job_id]
            except asyncio.CancelledError:
                pass
        
        job.status = BatchStatus.CANCELLED
        job.end_time = datetime.now()
        
        logging.info(f"批处理作业取消: {job_id}")
        return True
    
    async def get_job_result(self, job_id: str) -> Optional[BatchResult]:
        """获取作业结果"""
        job = await self.get_job_status(job_id)
        if not job or job.status != BatchStatus.COMPLETED:
            return None
        
        # 统计处理结果
        successful_items = sum(1 for result in job.results if not isinstance(result, dict) or "error" not in result)
        failed_items = len(job.results) - successful_items
        
        processing_time = 0.0
        if job.start_time and job.end_time:
            processing_time = (job.end_time - job.start_time).total_seconds()
        
        # 生成摘要统计
        summary = await self._generate_result_summary(job.results)
        
        result = BatchResult(
            job_id=job_id,
            total_items=len(job.data),
            processed_items=len(job.results),
            successful_items=successful_items,
            failed_items=failed_items,
            processing_time=processing_time,
            results=job.results,
            summary=summary
        )
        
        return result
    
    async def _generate_result_summary(self, results: List[Any]) -> Dict[str, Any]:
        """生成结果摘要"""
        if not results:
            return {}
        
        # 分析结果类型和统计
        result_types = {}
        error_count = 0
        numeric_results = []
        
        for result in results:
            result_type = type(result).__name__
            result_types[result_type] = result_types.get(result_type, 0) + 1
            
            if isinstance(result, dict) and "error" in result:
                error_count += 1
            
            if isinstance(result, (int, float)):
                numeric_results.append(result)
        
        summary = {
            "total_results": len(results),
            "result_type_distribution": result_types,
            "error_count": error_count,
            "success_rate": (len(results) - error_count) / len(results) * 100
        }
        
        # 数值结果统计
        if numeric_results:
            summary["numeric_stats"] = {
                "count": len(numeric_results),
                "mean": statistics.mean(numeric_results),
                "std": statistics.stdev(numeric_results) if len(numeric_results) > 1 else 0,
                "min": min(numeric_results),
                "max": max(numeric_results)
            }
        
        return summary
    
    async def process_dataframe(self, df: pd.DataFrame, processing_function: Callable, 
                              config: BatchConfig = None) -> pd.DataFrame:
        """处理DataFrame数据"""
        # 将DataFrame转换为记录列表
        records = df.to_dict('records')
        
        # 提交批处理作业
        job_id = await self.submit_job(records, processing_function, config)
        
        # 等待作业完成
        await self.wait_for_completion(job_id)
        
        # 获取结果
        batch_result = await self.get_job_result(job_id)
        if not batch_result:
            raise RuntimeError(f"批处理作业失败: {job_id}")
        
        # 将结果转换回DataFrame
        result_df = pd.DataFrame(batch_result.results)
        return result_df
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """获取处理器统计"""
        total_jobs = len(self.jobs)
        active_jobs = sum(1 for job in self.jobs.values() if job.status == BatchStatus.PROCESSING)
        completed_jobs = sum(1 for job in self.jobs.values() if job.status == BatchStatus.COMPLETED)
        
        mode_counts = {}
        for job in self.jobs.values():
            mode = job.config.processing_mode.value
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        
        total_items = sum(len(job.data) for job in self.jobs.values())
        total_processing_time = sum(
            (job.end_time - job.start_time).total_seconds() 
            for job in self.jobs.values() 
            if job.start_time and job.end_time
        )
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "processing_mode_distribution": mode_counts,
            "total_items_processed": total_items,
            "total_processing_time": total_processing_time,
            "active_tasks": len(self.processing_tasks)
        }
    
    async def cleanup(self):
        """清理资源"""
        # 取消所有进行中的任务
        for job_id, task in self.processing_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.processing_tasks.clear()
        
        # 关闭执行器
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logging.info("批处理器资源清理完成")

# 全局批处理器实例
batch_processor = BatchProcessor()

# 导入statistics用于数值统计
import statistics