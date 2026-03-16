"""
流处理器：实时数据流处理
负责实时数据流的处理、窗口计算和流式分析
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import json

class WindowType(Enum):
    """窗口类型枚举"""
    TUMBLING = "tumbling"      # 滚动窗口，不重叠
    SLIDING = "sliding"        # 滑动窗口，有重叠
    SESSION = "session"        # 会话窗口，基于活动间隔
    GLOBAL = "global"          # 全局窗口，所有数据

@dataclass
class StreamConfig:
    """流处理配置"""
    window_type: WindowType
    window_size: timedelta
    slide_interval: timedelta = None  # 用于滑动窗口
    session_gap: timedelta = None     # 用于会话窗口
    watermark_delay: timedelta = timedelta(seconds=10)  # 水位线延迟
    max_lateness: timedelta = timedelta(minutes=5)      # 最大延迟容忍

@dataclass
class StreamWindow:
    """流窗口"""
    window_id: str
    start_time: datetime
    end_time: datetime
    data: List[Any]
    watermark: datetime
    is_closed: bool = False

@dataclass
class StreamResult:
    """流处理结果"""
    window_id: str
    processing_time: datetime
    result: Any
    input_count: int
    output_count: int

class StreamProcessor:
    """流处理器"""
    
    def __init__(self):
        self.active_windows: Dict[str, StreamWindow] = {}
        self.watermarks: Dict[str, datetime] = {}
        self.processing_results: List[StreamResult] = {}
        self.processor_tasks: Dict[str, asyncio.Task] = {}
        self.input_streams: Dict[str, asyncio.Queue] = {}
        self.output_streams: Dict[str, asyncio.Queue] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化流处理器"""
        if self.initialized:
            return
            
        logging.info("初始化流处理器...")
        self.initialized = True
        logging.info("流处理器初始化完成")
    
    async def create_stream(self, stream_id: str, config: StreamConfig) -> bool:
        """创建数据流"""
        if stream_id in self.input_streams:
            logging.warning(f"数据流已存在: {stream_id}")
            return False
        
        self.input_streams[stream_id] = asyncio.Queue()
        self.output_streams[stream_id] = asyncio.Queue()
        self.watermarks[stream_id] = datetime.now()
        
        # 启动流处理任务
        processing_task = asyncio.create_task(self._stream_processor(stream_id, config))
        self.processor_tasks[stream_id] = processing_task
        
        logging.info(f"数据流创建成功: {stream_id}")
        return True
    
    async def close_stream(self, stream_id: str):
        """关闭数据流"""
        if stream_id in self.processor_tasks:
            task = self.processor_tasks[stream_id]
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.processor_tasks[stream_id]
        
        if stream_id in self.input_streams:
            del self.input_streams[stream_id]
        if stream_id in self.output_streams:
            del self.output_streams[stream_id]
        if stream_id in self.watermarks:
            del self.watermarks[stream_id]
        
        logging.info(f"数据流关闭: {stream_id}")
    
    async def ingest_data(self, stream_id: str, data: Any, timestamp: datetime = None):
        """摄入流数据"""
        if stream_id not in self.input_streams:
            raise ValueError(f"数据流不存在: {stream_id}")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # 包装数据
        stream_item = {
            "data": data,
            "timestamp": timestamp,
            "ingestion_time": datetime.now()
        }
        
        await self.input_streams[stream_id].put(stream_item)
        
        # 更新水位线
        self._update_watermark(stream_id, timestamp)
        
        logging.debug(f"流数据摄入: {stream_id}, 时间戳: {timestamp}")
    
    def _update_watermark(self, stream_id: str, event_time: datetime):
        """更新水位线"""
        current_watermark = self.watermarks.get(stream_id, datetime.min)
        if event_time > current_watermark:
            self.watermarks[stream_id] = event_time
    
    async def _stream_processor(self, stream_id: str, config: StreamConfig):
        """流处理主循环"""
        try:
            while True:
                # 获取数据
                stream_item = await self.input_streams[stream_id].get()
                
                # 处理数据
                await self._process_stream_item(stream_id, stream_item, config)
                
                # 标记任务完成
                self.input_streams[stream_id].task_done()
                
        except asyncio.CancelledError:
            logging.info(f"流处理任务取消: {stream_id}")
        except Exception as e:
            logging.error(f"流处理错误 {stream_id}: {e}")
    
    async def _process_stream_item(self, stream_id: str, stream_item: Dict[str, Any], config: StreamConfig):
        """处理流数据项"""
        event_time = stream_item["timestamp"]
        data = stream_item["data"]
        
        # 根据窗口类型分配窗口
        windows = await self._assign_to_windows(stream_id, event_time, data, config)
        
        for window in windows:
            # 添加数据到窗口
            window.data.append({
                "data": data,
                "event_time": event_time,
                "processing_time": datetime.now()
            })
            
            # 检查窗口是否应该触发
            if await self._should_trigger_window(window, config):
                await self._trigger_window(stream_id, window, config)
    
    async def _assign_to_windows(self, stream_id: str, event_time: datetime, data: Any, 
                               config: StreamConfig) -> List[StreamWindow]:
        """分配数据到窗口"""
        windows = []
        
        if config.window_type == WindowType.TUMBLING:
            # 滚动窗口
            window_start = self._align_to_window(event_time, config.window_size)
            window_end = window_start + config.window_size
            window_id = f"{stream_id}_tumbling_{window_start.timestamp()}"
            
            window = self.active_windows.get(window_id)
            if not window:
                window = StreamWindow(
                    window_id=window_id,
                    start_time=window_start,
                    end_time=window_end,
                    data=[],
                    watermark=event_time
                )
                self.active_windows[window_id] = window
            
            windows.append(window)
        
        elif config.window_type == WindowType.SLIDING:
            # 滑动窗口
            if not config.slide_interval:
                raise ValueError("滑动窗口需要指定slide_interval")
            
            # 计算所有相关的滑动窗口
            current_start = self._align_to_window(event_time, config.slide_interval)
            while current_start + config.window_size > event_time:
                if current_start <= event_time:
                    window_id = f"{stream_id}_sliding_{current_start.timestamp()}"
                    
                    window = self.active_windows.get(window_id)
                    if not window:
                        window = StreamWindow(
                            window_id=window_id,
                            start_time=current_start,
                            end_time=current_start + config.window_size,
                            data=[],
                            watermark=event_time
                        )
                        self.active_windows[window_id] = window
                    
                    windows.append(window)
                
                current_start -= config.slide_interval
        
        elif config.window_type == WindowType.SESSION:
            # 会话窗口（简化实现）
            # 在实际实现中，需要更复杂的会话检测逻辑
            window_id = f"{stream_id}_session_{int(event_time.timestamp())}"
            
            window = StreamWindow(
                window_id=window_id,
                start_time=event_time,
                end_time=event_time + (config.session_gap or timedelta(minutes=5)),
                data=[],
                watermark=event_time
            )
            
            self.active_windows[window_id] = window
            windows.append(window)
        
        elif config.window_type == WindowType.GLOBAL:
            # 全局窗口
            window_id = f"{stream_id}_global"
            
            window = self.active_windows.get(window_id)
            if not window:
                window = StreamWindow(
                    window_id=window_id,
                    start_time=datetime.min,
                    end_time=datetime.max,
                    data=[],
                    watermark=event_time
                )
                self.active_windows[window_id] = window
            
            windows.append(window)
        
        return windows
    
    def _align_to_window(self, timestamp: datetime, window_size: timedelta) -> datetime:
        """对齐时间到窗口边界"""
        if window_size.total_seconds() == 0:
            return timestamp
        
        epoch_seconds = timestamp.timestamp()
        window_seconds = window_size.total_seconds()
        aligned_seconds = (epoch_seconds // window_seconds) * window_seconds
        
        return datetime.fromtimestamp(aligned_seconds)
    
    async def _should_trigger_window(self, window: StreamWindow, config: StreamConfig) -> bool:
        """检查是否应该触发窗口"""
        current_time = datetime.now()
        watermark = self._get_stream_watermark(window.window_id.split('_')[0])
        
        if config.window_type == WindowType.TUMBLING:
            # 当水位线超过窗口结束时间时触发
            return watermark >= window.end_time
        
        elif config.window_type == WindowType.SLIDING:
            # 简化实现：定期触发
            return len(window.data) >= 100  # 达到一定数据量时触发
        
        elif config.window_type == WindowType.SESSION:
            # 当超过会话间隔时触发
            return current_time >= window.end_time
        
        elif config.window_type == WindowType.GLOBAL:
            # 全局窗口通常需要手动触发或基于特殊条件
            return False
        
        return False
    
    def _get_stream_watermark(self, stream_id: str) -> datetime:
        """获取流的水位线"""
        return self.watermarks.get(stream_id, datetime.now()) - timedelta(seconds=10)
    
    async def _trigger_window(self, stream_id: str, window: StreamWindow, config: StreamConfig):
        """触发窗口计算"""
        if window.is_closed or not window.data:
            return
        
        start_time = datetime.now()
        
        try:
            # 执行窗口计算
            window_result = await self._compute_window(stream_id, window, config)
            
            # 创建处理结果
            result = StreamResult(
                window_id=window.window_id,
                processing_time=datetime.now(),
                result=window_result,
                input_count=len(window.data),
                output_count=1 if window_result is not None else 0
            )
            
            self.processing_results.append(result)
            
            # 发送到输出流
            if stream_id in self.output_streams:
                await self.output_streams[stream_id].put(result)
            
            # 标记窗口为已关闭
            window.is_closed = True
            
            # 从活跃窗口移除
            if window.window_id in self.active_windows:
                del self.active_windows[window.window_id]
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logging.info(f"窗口触发完成: {window.window_id}, 处理时间: {processing_time:.2f}s")
            
        except Exception as e:
            logging.error(f"窗口计算失败 {window.window_id}: {e}")
    
    async def _compute_window(self, stream_id: str, window: StreamWindow, config: StreamConfig) -> Any:
        """计算窗口结果"""
        # 基本的窗口计算实现
        # 在实际应用中，这里会执行更复杂的流式计算逻辑
        
        if not window.data:
            return None
        
        # 简单统计计算
        if all(isinstance(item["data"], (int, float)) for item in window.data):
            values = [item["data"] for item in window.data]
            
            result = {
                "window_start": window.start_time.isoformat(),
                "window_end": window.end_time.isoformat(),
                "count": len(values),
                "sum": sum(values),
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values)
            }
        else:
            # 对于非数值数据，返回计数和样本
            result = {
                "window_start": window.start_time.isoformat(),
                "window_end": window.end_time.isoformat(),
                "count": len(window.data),
                "sample_data": [item["data"] for item in window.data[:5]]  # 前5个样本
            }
        
        return result
    
    async def register_processing_function(self, stream_id: str, processing_func: Callable):
        """注册处理函数"""
        # 这个函数允许用户注册自定义的流处理逻辑
        # 在当前简化实现中，处理逻辑是硬编码的
        # 在实际实现中，这里会存储处理函数并在_compute_window中调用
        logging.info(f"注册处理函数到流: {stream_id}")
    
    async def get_stream_output(self, stream_id: str, timeout: float = None) -> Optional[StreamResult]:
        """获取流输出"""
        if stream_id not in self.output_streams:
            return None
        
        try:
            if timeout:
                result = await asyncio.wait_for(self.output_streams[stream_id].get(), timeout)
            else:
                result = await self.output_streams[stream_id].get()
            
            self.output_streams[stream_id].task_done()
            return result
            
        except asyncio.TimeoutError:
            return None
    
    async def stream_output_generator(self, stream_id: str) -> AsyncGenerator[StreamResult, None]:
        """流输出生成器"""
        if stream_id not in self.output_streams:
            return
        
        while True:
            try:
                result = await self.output_streams[stream_id].get()
                yield result
                self.output_streams[stream_id].task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"流输出生成错误: {e}")
                break
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """获取处理器统计"""
        active_streams = len(self.input_streams)
        active_windows = len(self.active_windows)
        total_results = len(self.processing_results)
        
        window_type_counts = {}
        for window in self.active_windows.values():
            window_type = window.window_id.split('_')[1]  # 提取窗口类型
            window_type_counts[window_type] = window_type_counts.get(window_type, 0) + 1
        
        recent_results = self.processing_results[-10:] if self.processing_results else []
        
        return {
            "active_streams": active_streams,
            "active_windows": active_windows,
            "total_results": total_results,
            "window_type_distribution": window_type_counts,
            "recent_results": [
                {
                    "window_id": result.window_id,
                    "input_count": result.input_count,
                    "processing_time": result.processing_time.isoformat()
                }
                for result in recent_results
            ]
        }

# 全局流处理器实例
stream_processor = StreamProcessor()
