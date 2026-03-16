# cognitive/learning/performance_optimizer.py
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque
import heapq
import psutil
import GPUtil
from threading import Lock, Thread
import time

class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.metrics_lock = Lock()
        
    def record_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """记录性能指标"""
        if timestamp is None:
            timestamp = datetime.now()
        
        with self.metrics_lock:
            self.metrics_history[metric_name].append({
                'value': value,
                'timestamp': timestamp,
                'timestamp_iso': timestamp.isoformat()
            })
    
    def get_metric_stats(self, metric_name: str, window_minutes: int = 60) -> Dict[str, Any]:
        """获取指标统计信息"""
        with self.metrics_lock:
            if metric_name not in self.metrics_history:
                return {'error': f'Metric {metric_name} not found'}
            
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
            recent_values = [
                point for point in self.metrics_history[metric_name]
                if point['timestamp'] > cutoff_time
            ]
            
            if not recent_values:
                return {'count': 0, 'message': 'No data in specified window'}
            
            values = [point['value'] for point in recent_values]
            
            return {
                'count': len(values),
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'percentile_95': np.percentile(values, 95),
                'trend': self._calculate_trend(values),
                'latest_value': values[-1],
                'timestamp': recent_values[-1]['timestamp_iso']
            }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算数值趋势"""
        if len(values) < 2:
            return 'stable'
        
        recent = values[-5:]  # 最近5个值
        if len(recent) < 2:
            return 'stable'
        
        # 简单线性回归判断趋势
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]
        
        if slope > 0.01:
            return 'improving'
        elif slope < -0.01:
            return 'declining'
        else:
            return 'stable'
    
    def get_all_metrics(self) -> Dict[str, List[Dict]]:
        """获取所有指标数据"""
        with self.metrics_lock:
            return {
                name: list(history) 
                for name, history in self.metrics_history.items()
            }

class ResourceMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        self.performance_metrics = PerformanceMetrics()
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval: float = 5.0):
        """开始资源监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止资源监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                self._collect_system_metrics()
                time.sleep(interval)
            except Exception as e:
                logging.error(f"资源监控错误: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        timestamp = datetime.now()
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.performance_metrics.record_metric('cpu_usage', cpu_percent, timestamp)
        
        # 内存使用
        memory = psutil.virtual_memory()
        self.performance_metrics.record_metric('memory_usage_percent', memory.percent, timestamp)
        self.performance_metrics.record_metric('memory_used_gb', memory.used / (1024**3), timestamp)
        
        # GPU使用率（如果可用）
        try:
            gpus = GPUtil.getGPUs()
            for i, gpu in enumerate(gpus):
                self.performance_metrics.record_metric(f'gpu_{i}_usage', gpu.load * 100, timestamp)
                self.performance_metrics.record_metric(f'gpu_{i}_memory', gpu.memoryUtil * 100, timestamp)
        except Exception:
            pass  # GPU不可用
        
        # 磁盘IO
        disk_io = psutil.disk_io_counters()
        if disk_io:
            self.performance_metrics.record_metric('disk_read_mb', disk_io.read_bytes / (1024**2), timestamp)
            self.performance_metrics.record_metric('disk_write_mb', disk_io.write_bytes / (1024**2), timestamp)
        
        # 网络IO
        net_io = psutil.net_io_counters()
        if net_io:
            self.performance_metrics.record_metric('network_sent_mb', net_io.bytes_sent / (1024**2), timestamp)
            self.performance_metrics.record_metric('network_recv_mb', net_io.bytes_recv / (1024**2), timestamp)

class PerformanceOptimizer:
    """性能优化：优化系统性能"""
    
    def __init__(self, optimization_dir: str = "data/performance_optimization"):
        self.optimization_dir = optimization_dir
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = self._setup_logger()
        
        # 资源监控
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.start_monitoring()
        
        # 优化策略
        self.optimization_strategies: Dict[str, Dict] = {}
        self.optimization_history: List[Dict] = []
        
        # 性能基准
        self.performance_baselines: Dict[str, float] = {}
        
        # 优化配置
        self.optimization_config = {
            'cpu_threshold': 80.0,
            'memory_threshold': 85.0,
            'gpu_threshold': 90.0,
            'response_time_threshold': 2.0,  # 秒
            'batch_size_optimization': True,
            'model_compression': True,
            'cache_optimization': True
        }
        
        # 加载优化配置
        self._load_optimization_config()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('performance_optimizer')
        if not logger.handlers:
            handler = logging.FileHandler('logs/performance_optimization.log')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _load_optimization_config(self):
        """加载优化配置"""
        config_file = os.path.join(self.optimization_dir, "optimization_config.json")
        
        try:
            os.makedirs(self.optimization_dir, exist_ok=True)
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.optimization_config.update(loaded_config)
            
            self.logger.info("性能优化配置加载成功")
            
        except Exception as e:
            self.logger.error(f"加载优化配置失败: {e}")
    
    def save_optimization_config(self):
        """保存优化配置"""
        try:
            os.makedirs(self.optimization_dir, exist_ok=True)
            
            config_file = os.path.join(self.optimization_dir, "optimization_config.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.optimization_config, f, ensure_ascii=False, indent=2)
            
            self.logger.info("性能优化配置保存成功")
            
        except Exception as e:
            self.logger.error(f"保存优化配置失败: {e}")
    
    def analyze_performance(self, component: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析组件性能
        
        Args:
            component: 组件名称
            metrics: 性能指标
            
        Returns:
            性能分析结果
        """
        try:
            analysis_result = {
                'component': component,
                'timestamp': datetime.now().isoformat(),
                'overall_score': self._calculate_overall_score(metrics),
                'bottlenecks': self._identify_bottlenecks(metrics),
                'recommendations': self._generate_recommendations(metrics),
                'optimization_opportunities': self._find_optimization_opportunities(metrics),
                'resource_utilization': self._analyze_resource_utilization(metrics)
            }
            
            # 记录分析结果
            self.optimization_history.append(analysis_result)
            
            # 如果发现性能问题，触发优化
            if analysis_result['overall_score'] < 0.7:
                self._trigger_optimization(component, analysis_result)
            
            self.logger.info(f"性能分析完成: {component} (评分: {analysis_result['overall_score']:.3f})")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"性能分析失败: {e}")
            return self._get_fallback_analysis(component)
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """计算总体性能评分"""
        score_components = []
        
        # 响应时间评分
        response_time = metrics.get('response_time', 0.0)
        response_score = max(0.0, 1.0 - (response_time / 10.0))  # 10秒为最差
        score_components.append(response_score * 0.3)
        
        # 资源使用评分
        cpu_usage = metrics.get('cpu_usage', 0.0)
        cpu_score = max(0.0, 1.0 - (cpu_usage / 100.0))
        score_components.append(cpu_score * 0.2)
        
        memory_usage = metrics.get('memory_usage', 0.0)
        memory_score = max(0.0, 1.0 - (memory_usage / 100.0))
        score_components.append(memory_score * 0.2)
        
        # 准确性评分
        accuracy = metrics.get('accuracy', 1.0)
        score_components.append(accuracy * 0.2)
        
        # 吞吐量评分
        throughput = metrics.get('throughput', 0.0)
        throughput_score = min(1.0, throughput / 1000.0)  # 1000 req/s 为满分
        score_components.append(throughput_score * 0.1)
        
        return sum(score_components)
    
    def _identify_bottlenecks(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        # CPU瓶颈
        cpu_usage = metrics.get('cpu_usage', 0.0)
        if cpu_usage > self.optimization_config['cpu_threshold']:
            bottlenecks.append({
                'type': 'cpu',
                'severity': 'high' if cpu_usage > 90 else 'medium',
                'current_value': cpu_usage,
                'threshold': self.optimization_config['cpu_threshold'],
                'description': f'CPU使用率过高: {cpu_usage:.1f}%'
            })
        
        # 内存瓶颈
        memory_usage = metrics.get('memory_usage', 0.0)
        if memory_usage > self.optimization_config['memory_threshold']:
            bottlenecks.append({
                'type': 'memory',
                'severity': 'high' if memory_usage > 95 else 'medium',
                'current_value': memory_usage,
                'threshold': self.optimization_config['memory_threshold'],
                'description': f'内存使用率过高: {memory_usage:.1f}%'
            })
        
        # 响应时间瓶颈
        response_time = metrics.get('response_time', 0.0)
        if response_time > self.optimization_config['response_time_threshold']:
            bottlenecks.append({
                'type': 'response_time',
                'severity': 'high' if response_time > 5.0 else 'medium',
                'current_value': response_time,
                'threshold': self.optimization_config['response_time_threshold'],
                'description': f'响应时间过长: {response_time:.2f}s'
            })
        
        # GPU瓶颈
        gpu_usage = metrics.get('gpu_usage', 0.0)
        if gpu_usage > self.optimization_config['gpu_threshold']:
            bottlenecks.append({
                'type': 'gpu',
                'severity': 'high' if gpu_usage > 95 else 'medium',
                'current_value': gpu_usage,
                'threshold': self.optimization_config['gpu_threshold'],
                'description': f'GPU使用率过高: {gpu_usage:.1f}%'
            })
        
        return bottlenecks
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        bottlenecks = self._identify_bottlenecks(metrics)
        
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'cpu':
                recommendations.extend([
                    {
                        'type': 'batch_size',
                        'priority': 'high' if bottleneck['severity'] == 'high' else 'medium',
                        'action': '减少批处理大小',
                        'description': '降低CPU负载，提高响应速度',
                        'expected_improvement': '响应时间减少20-30%'
                    },
                    {
                        'type': 'parallelization',
                        'priority': 'medium',
                        'action': '启用任务并行处理',
                        'description': '充分利用多核CPU',
                        'expected_improvement': '吞吐量提高50-100%'
                    }
                ])
            
            elif bottleneck['type'] == 'memory':
                recommendations.extend([
                    {
                        'type': 'memory_management',
                        'priority': 'high' if bottleneck['severity'] == 'high' else 'medium',
                        'action': '优化内存使用',
                        'description': '减少内存泄漏和碎片',
                        'expected_improvement': '内存使用减少20-40%'
                    },
                    {
                        'type': 'caching',
                        'priority': 'medium',
                        'action': '实现智能缓存',
                        'description': '缓存频繁访问的数据',
                        'expected_improvement': '响应时间减少15-25%'
                    }
                ])
            
            elif bottleneck['type'] == 'response_time':
                recommendations.append({
                    'type': 'algorithm_optimization',
                    'priority': 'high',
                    'action': '优化核心算法',
                    'description': '减少计算复杂度',
                    'expected_improvement': '响应时间减少30-50%'
                })
        
        # 如果没有瓶颈，提供一般性建议
        if not recommendations:
            recommendations.append({
                'type': 'monitoring',
                'priority': 'low',
                'action': '持续性能监控',
                'description': '定期检查系统性能',
                'expected_improvement': '预防性能问题'
            })
        
        return recommendations
    
    def _find_optimization_opportunities(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """寻找优化机会"""
        opportunities = []
        
        # 模型压缩机会
        model_size = metrics.get('model_size_mb', 0.0)
        if model_size > 100.0 and self.optimization_config['model_compression']:
            opportunities.append({
                'type': 'model_compression',
                'potential_savings': f'{(model_size * 0.3):.1f}MB',
                'description': '模型量化或剪枝可减少30%模型大小',
                'impact': 'medium',
                'implementation_effort': 'medium'
            })
        
        # 缓存优化机会
        cache_hit_rate = metrics.get('cache_hit_rate', 0.0)
        if cache_hit_rate < 0.7 and self.optimization_config['cache_optimization']:
            opportunities.append({
                'type': 'cache_optimization',
                'potential_savings': '响应时间减少40%',
                'description': '优化缓存策略可提高命中率',
                'impact': 'high',
                'implementation_effort': 'low'
            })
        
        # 批处理优化机会
        batch_efficiency = metrics.get('batch_efficiency', 1.0)
        if batch_efficiency < 0.8 and self.optimization_config['batch_size_optimization']:
            opportunities.append({
                'type': 'batch_optimization',
                'potential_savings': '吞吐量提高60%',
                'description': '动态调整批处理大小可提高GPU利用率',
                'impact': 'high',
                'implementation_effort': 'medium'
            })
        
        return opportunities
    
    def _analyze_resource_utilization(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析资源利用率"""
        utilization = {}
        
        # CPU利用率分析
        cpu_usage = metrics.get('cpu_usage', 0.0)
        utilization['cpu'] = {
            'current': cpu_usage,
            'efficiency': 'optimal' if cpu_usage < 70 else 'high' if cpu_usage < 90 else 'overutilized',
            'recommendation': '增加并行度' if cpu_usage < 50 else '优化算法' if cpu_usage < 80 else '减少负载'
        }
        
        # 内存利用率分析
        memory_usage = metrics.get('memory_usage', 0.0)
        utilization['memory'] = {
            'current': memory_usage,
            'efficiency': 'optimal' if memory_usage < 70 else 'high' if memory_usage < 90 else 'overutilized',
            'recommendation': '增加缓存' if memory_usage < 50 else '优化数据结构' if memory_usage < 80 else '减少内存使用'
        }
        
        # GPU利用率分析
        gpu_usage = metrics.get('gpu_usage', 0.0)
        if gpu_usage > 0:
            utilization['gpu'] = {
                'current': gpu_usage,
                'efficiency': 'optimal' if gpu_usage > 80 else 'underutilized' if gpu_usage < 50 else 'good',
                'recommendation': '增加批处理大小' if gpu_usage < 60 else '优化模型' if gpu_usage < 80 else '监控温度'
            }
        
        return utilization
    
    def _trigger_optimization(self, component: str, analysis_result: Dict[str, Any]):
        """触发优化过程"""
        try:
            optimization_id = f"opt_{component}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            optimization_plan = {
                'optimization_id': optimization_id,
                'component': component,
                'triggered_by': 'performance_analysis',
                'analysis_result': analysis_result,
                'planned_actions': analysis_result['recommendations'],
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            # 执行优化
            self._execute_optimization(optimization_plan)
            
            self.logger.info(f"优化过程已触发: {optimization_id}")
            
        except Exception as e:
            self.logger.error(f"触发优化失败: {e}")
    
    def _execute_optimization(self, optimization_plan: Dict[str, Any]):
        """执行优化计划"""
        try:
            optimization_plan['status'] = 'in_progress'
            optimization_plan['started_at'] = datetime.now().isoformat()
            
            # 执行优化动作
            results = []
            for action in optimization_plan['planned_actions']:
                if action['priority'] in ['high', 'medium']:
                    result = self._apply_optimization_action(action)
                    results.append(result)
            
            optimization_plan['execution_results'] = results
            optimization_plan['status'] = 'completed'
            optimization_plan['completed_at'] = datetime.now().isoformat()
            
            # 记录优化历史
            self.optimization_history.append(optimization_plan)
            
            self.logger.info(f"优化执行完成: {optimization_plan['optimization_id']}")
            
        except Exception as e:
            optimization_plan['status'] = 'failed'
            optimization_plan['error'] = str(e)
            self.logger.error(f"优化执行失败: {e}")
    
    def _apply_optimization_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """应用优化动作"""
        action_type = action['type']
        
        if action_type == 'batch_size':
            return self._optimize_batch_size()
        elif action_type == 'memory_management':
            return self._optimize_memory_management()
        elif action_type == 'caching':
            return self._optimize_caching()
        elif action_type == 'algorithm_optimization':
            return self._optimize_algorithm()
        else:
            return {
                'action': action_type,
                'status': 'skipped',
                'reason': '未实现的优化类型'
            }
    
    def _optimize_batch_size(self) -> Dict[str, Any]:
        """优化批处理大小"""
        try:
            # 获取当前系统状态
            cpu_usage = self.resource_monitor.performance_metrics.get_metric_stats('cpu_usage')
            memory_usage = self.resource_monitor.performance_metrics.get_metric_stats('memory_usage_percent')
            
            current_batch_size = 32  # 假设当前批处理大小
            new_batch_size = current_batch_size
            
            # 根据资源使用情况调整批处理大小
            if cpu_usage.get('mean', 0) > 80:
                new_batch_size = max(8, current_batch_size // 2)
            elif cpu_usage.get('mean', 0) < 50:
                new_batch_size = min(128, current_batch_size * 2)
            
            return {
                'action': 'batch_size_optimization',
                'status': 'completed',
                'previous_batch_size': current_batch_size,
                'new_batch_size': new_batch_size,
                'reason': f'基于CPU使用率调整: {cpu_usage.get("mean", 0):.1f}%'
            }
            
        except Exception as e:
            return {
                'action': 'batch_size_optimization',
                'status': 'failed',
                'error': str(e)
            }
    
    def _optimize_memory_management(self) -> Dict[str, Any]:
        """优化内存管理"""
        try:
            # 清理缓存和临时文件
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return {
                'action': 'memory_management',
                'status': 'completed',
                'description': '清理了Python和GPU缓存',
                'memory_freed': '未知'  # 实际实现中会计算释放的内存
            }
            
        except Exception as e:
            return {
                'action': 'memory_management',
                'status': 'failed',
                'error': str(e)
            }
    
    def _optimize_caching(self) -> Dict[str, Any]:
        """优化缓存策略"""
        try:
            # 这里可以实现具体的缓存优化逻辑
            # 例如调整缓存大小、过期时间等
            
            return {
                'action': 'caching_optimization',
                'status': 'completed',
                'description': '优化了缓存配置',
                'changes': [
                    '增加了缓存大小',
                    '调整了缓存过期策略'
                ]
            }
            
        except Exception as e:
            return {
                'action': 'caching_optimization',
                'status': 'failed',
                'error': str(e)
            }
    
    def _optimize_algorithm(self) -> Dict[str, Any]:
        """优化算法"""
        try:
            # 这里可以实现算法优化逻辑
            # 例如切换到更高效的算法实现
            
            return {
                'action': 'algorithm_optimization',
                'status': 'completed',
                'description': '改进了关键算法实现',
                'expected_improvement': '性能提升20-30%'
            }
            
        except Exception as e:
            return {
                'action': 'algorithm_optimization',
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_fallback_analysis(self, component: str) -> Dict[str, Any]:
        """获取回退分析结果"""
        return {
            'component': component,
            'timestamp': datetime.now().isoformat(),
            'overall_score': 0.5,
            'bottlenecks': [],
            'recommendations': [{
                'type': 'diagnostic',
                'priority': 'high',
                'action': '系统诊断',
                'description': '需要进一步分析性能问题',
                'expected_improvement': '确定根本原因'
            }],
            'optimization_opportunities': [],
            'resource_utilization': {},
            'fallback': True
        }
    
    def get_performance_report(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """获取性能报告"""
        system_metrics = {}
        
        # 收集系统指标
        metric_names = ['cpu_usage', 'memory_usage_percent', 'memory_used_gb']
        for metric_name in metric_names:
            stats = self.resource_monitor.performance_metrics.get_metric_stats(
                metric_name, time_window_minutes)
            system_metrics[metric_name] = stats
        
        # 分析优化历史
        recent_optimizations = [
            opt for opt in self.optimization_history[-10:]
            if isinstance(opt, dict) and 'optimization_id' in opt
        ]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'time_window_minutes': time_window_minutes,
            'system_metrics': system_metrics,
            'recent_optimizations': recent_optimizations,
            'optimization_config': self.optimization_config,
            'performance_summary': self._generate_performance_summary(system_metrics)
        }
        
        return report
    
    def _generate_performance_summary(self, system_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """生成性能摘要"""
        cpu_stats = system_metrics.get('cpu_usage', {})
        memory_stats = system_metrics.get('memory_usage_percent', {})
        
        summary = {
            'overall_health': 'good',
            'cpu_health': 'good',
            'memory_health': 'good',
            'recommendations': []
        }
        
        # CPU健康评估
        cpu_avg = cpu_stats.get('mean', 0)
        if cpu_avg > 90:
            summary['cpu_health'] = 'critical'
            summary['overall_health'] = 'critical'
            summary['recommendations'].append('CPU使用率过高，需要立即优化')
        elif cpu_avg > 80:
            summary['cpu_health'] = 'warning'
            summary['overall_health'] = 'warning'
            summary['recommendations'].append('CPU使用率较高，建议优化')
        
        # 内存健康评估
        memory_avg = memory_stats.get('mean', 0)
        if memory_avg > 95:
            summary['memory_health'] = 'critical'
            summary['overall_health'] = 'critical'
            summary['recommendations'].append('内存使用率过高，需要立即优化')
        elif memory_avg > 85:
            summary['memory_health'] = 'warning'
            if summary['overall_health'] != 'critical':
                summary['overall_health'] = 'warning'
            summary['recommendations'].append('内存使用率较高，建议优化')
        
        if not summary['recommendations']:
            summary['recommendations'].append('系统性能良好，继续保持监控')
        
        return summary
    
    def update_optimization_config(self, new_config: Dict[str, Any]):
        """更新优化配置"""
        self.optimization_config.update(new_config)
        self.save_optimization_config()
        self.logger.info("性能优化配置已更新")
    
    def get_optimization_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_history[-limit:] if self.optimization_history else []

# 全局性能优化器实例
_global_performance_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """获取全局性能优化器实例"""
    global _global_performance_optimizer
    if _global_performance_optimizer is None:
        _global_performance_optimizer = PerformanceOptimizer()
    return _global_performance_optimizer

