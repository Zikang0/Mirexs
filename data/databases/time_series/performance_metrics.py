"""
性能指标模块 - 管理系统性能指标的收集和存储
"""

import logging
import time
import psutil
import GPUtil
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from threading import Thread, Event
import json

from .influxdb_integration import InfluxDBIntegration

class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self, influx_client: InfluxDBIntegration, config: Dict[str, Any]):
        """
        初始化性能指标收集器
        
        Args:
            influx_client: InfluxDB客户端
            config: 配置字典
        """
        self.influx_client = influx_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 性能指标配置
        self.metrics_bucket = config.get('metrics_bucket', 'mirexs_performance')
        self.collection_interval = config.get('collection_interval', 60)  # 秒
        self.enable_gpu_metrics = config.get('enable_gpu_metrics', True)
        self.enable_detailed_metrics = config.get('enable_detailed_metrics', False)
        
        # 监控状态
        self._is_monitoring = False
        self._monitor_thread = None
        self._stop_event = Event()
        
        # 自定义指标收集器
        self._custom_collectors = {}
        
    def start_monitoring(self) -> bool:
        """
        开始性能监控
        
        Returns:
            bool: 启动是否成功
        """
        if self._is_monitoring:
            self.logger.warning("Performance monitoring is already running")
            return True
        
        try:
            self._stop_event.clear()
            self._monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
            self._monitor_thread.start()
            self._is_monitoring = True
            
            self.logger.info(f"Started performance monitoring with {self.collection_interval}s interval")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start performance monitoring: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """
        停止性能监控
        
        Returns:
            bool: 停止是否成功
        """
        if not self._is_monitoring:
            self.logger.warning("Performance monitoring is not running")
            return True
        
        try:
            self._stop_event.set()
            if self._monitor_thread:
                self._monitor_thread.join(timeout=10)
            
            self._is_monitoring = False
            self.logger.info("Stopped performance monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop performance monitoring: {str(e)}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                self.collect_system_metrics()
                self.collect_application_metrics()
                
                if self.enable_gpu_metrics:
                    self.collect_gpu_metrics()
                
                # 收集自定义指标
                self._collect_custom_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
            
            # 等待下一个收集周期
            self._stop_event.wait(self.collection_interval)
    
    def collect_system_metrics(self) -> bool:
        """
        收集系统指标
        
        Returns:
            bool: 收集是否成功
        """
        try:
            timestamp = datetime.utcnow()
            metrics = {}
            
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_times = psutil.cpu_times()
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            metrics.update({
                "cpu_percent": cpu_percent,
                "cpu_user": getattr(cpu_times, 'user', 0),
                "cpu_system": getattr(cpu_times, 'system', 0),
                "cpu_idle": getattr(cpu_times, 'idle', 0),
                "load_1min": load_avg[0],
                "load_5min": load_avg[1],
                "load_15min": load_avg[2]
            })
            
            # 内存指标
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.update({
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "memory_percent": memory.percent,
                "swap_used": swap.used,
                "swap_percent": swap.percent
            })
            
            # 磁盘指标
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.update({
                "disk_total": disk_usage.total,
                "disk_used": disk_usage.used,
                "disk_free": disk_usage.free,
                "disk_percent": disk_usage.percent,
                "disk_read_bytes": getattr(disk_io, 'read_bytes', 0),
                "disk_write_bytes": getattr(disk_io, 'write_bytes', 0)
            })
            
            # 网络指标
            net_io = psutil.net_io_counters()
            
            metrics.update({
                "net_bytes_sent": getattr(net_io, 'bytes_sent', 0),
                "net_bytes_recv": getattr(net_io, 'bytes_recv', 0),
                "net_packets_sent": getattr(net_io, 'packets_sent', 0),
                "net_packets_recv": getattr(net_io, 'packets_recv', 0)
            })
            
            # 进程指标
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            metrics.update({
                "process_memory_rss": process_memory.rss,
                "process_memory_vms": process_memory.vms,
                "process_cpu_percent": process_cpu,
                "process_threads": process.num_threads(),
                "process_open_files": len(process.open_files())
            })
            
            # 写入系统指标
            tags = {"metric_type": "system", "host": psutil.users()[0].name if psutil.users() else "unknown"}
            
            success = self.influx_client.write_metric(
                measurement="performance_metrics",
                fields=metrics,
                tags=tags,
                timestamp=timestamp,
                bucket=self.metrics_bucket
            )
            
            if success and self.enable_detailed_metrics:
                self._collect_detailed_metrics(timestamp)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
            return False
    
    def collect_gpu_metrics(self) -> bool:
        """
        收集GPU指标
        
        Returns:
            bool: 收集是否成功
        """
        try:
            gpus = GPUtil.getGPUs()
            timestamp = datetime.utcnow()
            
            for i, gpu in enumerate(gpus):
                metrics = {
                    "gpu_utilization": gpu.load * 100,
                    "gpu_memory_used": gpu.memoryUsed,
                    "gpu_memory_total": gpu.memoryTotal,
                    "gpu_memory_percent": (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    "gpu_temperature": gpu.temperature
                }
                
                tags = {
                    "metric_type": "gpu",
                    "gpu_id": str(i),
                    "gpu_name": gpu.name
                }
                
                success = self.influx_client.write_metric(
                    measurement="performance_metrics",
                    fields=metrics,
                    tags=tags,
                    timestamp=timestamp,
                    bucket=self.metrics_bucket
                )
                
                if not success:
                    self.logger.warning(f"Failed to write GPU metrics for GPU {i}")
            
            return True
            
        except Exception as e:
            self.logger.debug(f"GPU metrics collection failed or no GPU available: {str(e)}")
            return False
    
    def collect_application_metrics(self) -> bool:
        """
        收集应用特定指标
        
        Returns:
            bool: 收集是否成功
        """
        try:
            timestamp = datetime.utcnow()
            metrics = {}
            
            # Python运行时指标
            import gc
            gc_collect = gc.collect()
            gc_stats = gc.get_stats()
            
            metrics.update({
                "python_gc_objects": sum(stat['collected'] for stat in gc_stats),
                "python_gc_uncollectable": sum(stat['uncollectable'] for stat in gc_stats),
                "python_memory_allocated": self._get_python_memory_usage()
            })
            
            # 应用业务指标
            metrics.update(self._get_business_metrics())
            
            tags = {"metric_type": "application"}
            
            success = self.influx_client.write_metric(
                measurement="performance_metrics",
                fields=metrics,
                tags=tags,
                timestamp=timestamp,
                bucket=self.metrics_bucket
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error collecting application metrics: {str(e)}")
            return False
    
    def _collect_detailed_metrics(self, timestamp: datetime):
        """收集详细指标"""
        try:
            # 每个CPU核心的使用率
            cpu_percent_per_core = psutil.cpu_percent(percpu=True)
            for i, percent in enumerate(cpu_percent_per_core):
                metrics = {"cpu_core_percent": percent}
                tags = {"metric_type": "cpu_core", "core_id": str(i)}
                
                self.influx_client.write_metric(
                    measurement="performance_metrics",
                    fields=metrics,
                    tags=tags,
                    timestamp=timestamp,
                    bucket=self.metrics_bucket
                )
            
            # 磁盘分区信息
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    metrics = {
                        "partition_total": usage.total,
                        "partition_used": usage.used,
                        "partition_free": usage.free,
                        "partition_percent": usage.percent
                    }
                    tags = {"metric_type": "disk_partition", "mountpoint": partition.mountpoint}
                    
                    self.influx_client.write_metric(
                        measurement="performance_metrics",
                        fields=metrics,
                        tags=tags,
                        timestamp=timestamp,
                        bucket=self.metrics_bucket
                    )
                except PermissionError:
                    continue
            
        except Exception as e:
            self.logger.debug(f"Error collecting detailed metrics: {str(e)}")
    
    def _get_python_memory_usage(self) -> int:
        """获取Python内存使用量"""
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except (ImportError, AttributeError):
            # 回退方法
            import os
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
    
    def _get_business_metrics(self) -> Dict[str, Any]:
        """获取业务指标"""
        # 这里可以添加应用特定的业务指标
        # 例如：活动用户数、请求处理数、缓存命中率等
        return {
            "active_sessions": 0,  # 示例指标
            "requests_processed": 0,
            "cache_hit_rate": 0.0
        }
    
    def _collect_custom_metrics(self):
        """收集自定义指标"""
        for name, collector in self._custom_collectors.items():
            try:
                metrics = collector()
                if metrics:
                    timestamp = datetime.utcnow()
                    tags = {"metric_type": "custom", "collector_name": name}
                    
                    self.influx_client.write_metric(
                        measurement="performance_metrics",
                        fields=metrics,
                        tags=tags,
                        timestamp=timestamp,
                        bucket=self.metrics_bucket
                    )
            except Exception as e:
                self.logger.error(f"Error in custom collector {name}: {str(e)}")
    
    def register_custom_collector(self, name: str, collector: Callable[[], Dict[str, Any]]):
        """
        注册自定义指标收集器
        
        Args:
            name: 收集器名称
            collector: 收集器函数，返回指标字典
        """
        self._custom_collectors[name] = collector
        self.logger.info(f"Registered custom metrics collector: {name}")
    
    def query_performance_data(self,
                             metric_type: str,
                             start_time: str = "-1h",
                             end_time: str = "now()") -> Optional[Dict[str, Any]]:
        """
        查询性能数据
        
        Args:
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 性能数据摘要
        """
        try:
            df = self.influx_client.query_performance_metrics(metric_type, start_time, end_time)
            
            if df is not None and not df.empty:
                summary = {
                    "metric_type": metric_type,
                    "data_points": len(df),
                    "time_range": f"{start_time} to {end_time}",
                    "metrics": {}
                }
                
                # 计算基本统计信息
                numeric_columns = df.select_dtypes(include=[np.number]).columns
                for col in numeric_columns:
                    summary["metrics"][col] = {
                        "mean": float(df[col].mean()),
                        "max": float(df[col].max()),
                        "min": float(df[col].min()),
                        "std": float(df[col].std())
                    }
                
                return summary
            
            return {"metric_type": metric_type, "data_points": 0, "message": "No data found"}
            
        except Exception as e:
            self.logger.error(f"Error querying performance data: {str(e)}")
            return None
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        获取系统健康状态
        
        Returns:
            Dict: 系统健康状态
        """
        try:
            health = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "healthy",
                "components": {},
                "alerts": []
            }
            
            # 检查CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)
            health["components"]["cpu"] = {
                "usage_percent": cpu_percent,
                "status": "warning" if cpu_percent > 80 else "healthy"
            }
            if cpu_percent > 90:
                health["alerts"].append("CPU usage critically high")
            
            # 检查内存
            memory = psutil.virtual_memory()
            health["components"]["memory"] = {
                "usage_percent": memory.percent,
                "status": "warning" if memory.percent > 85 else "healthy"
            }
            if memory.percent > 95:
                health["alerts"].append("Memory usage critically high")
            
            # 检查磁盘
            disk_usage = psutil.disk_usage('/')
            health["components"]["disk"] = {
                "usage_percent": disk_usage.percent,
                "status": "warning" if disk_usage.percent > 90 else "healthy"
            }
            if disk_usage.percent > 95:
                health["alerts"].append("Disk usage critically high")
            
            # 如果有警报，更新整体状态
            if any("critically" in alert for alert in health["alerts"]):
                health["status"] = "critical"
            elif health["alerts"]:
                health["status"] = "warning"
            
            return health
            
        except Exception as e:
            self.logger.error(f"Error getting system health: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "unknown",
                "error": str(e)
            }

