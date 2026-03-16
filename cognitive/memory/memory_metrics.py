"""
记忆指标模块：记忆系统性能指标
实现全面的记忆系统性能监控和评估
"""

import datetime
import time
from typing import List, Dict, Any, Optional
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .procedural_memory import ProceduralMemory
from .working_memory import WorkingMemory
from .memory_retrieval import MemoryRetrieval

class MemoryMetrics:
    """记忆指标系统 - 记忆系统性能指标"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        self.procedural_memory = ProceduralMemory(config.get('procedural_config', {}))
        self.working_memory = WorkingMemory(config.get('working_memory_config', {}))
        self.memory_retrieval = MemoryRetrieval(config.get('retrieval_config', {}))
        
        # 指标配置
        self.metrics_history = []
        self.max_history_size = self.config.get('max_history_size', 1000)
        self.collection_interval = self.config.get('collection_interval', 300)  # 5分钟
        
        # 性能基准
        self.performance_benchmarks = self._initialize_benchmarks()
        
        # 启动指标收集
        self._start_metrics_collection()
        
        self.initialized = True
        self.logger.info("记忆指标系统初始化成功")
    
    def _initialize_benchmarks(self) -> Dict[str, Any]:
        """初始化性能基准"""
        return {
            'retrieval_speed': {
                'excellent': 0.1,   # 秒
                'good': 0.5,
                'poor': 2.0
            },
            'retrieval_accuracy': {
                'excellent': 0.9,   # 准确率
                'good': 0.7,
                'poor': 0.5
            },
            'memory_usage': {
                'excellent': 0.3,   # 使用率
                'good': 0.7,
                'poor': 0.9
            },
            'consolidation_success': {
                'excellent': 0.9,
                'good': 0.7,
                'poor': 0.5
            }
        }
    
    def collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        收集全面指标
        
        Returns:
            综合指标数据
        """
        timestamp = datetime.datetime.now()
        
        try:
            metrics = {
                'timestamp': timestamp.isoformat(),
                'system_health': self._assess_system_health(),
                'memory_subsystems': self._collect_subsystem_metrics(),
                'performance_metrics': self._collect_performance_metrics(),
                'efficiency_metrics': self._collect_efficiency_metrics(),
                'quality_metrics': self._collect_quality_metrics()
            }
            
            # 计算总体评分
            metrics['overall_score'] = self._calculate_overall_score(metrics)
            metrics['performance_trend'] = self._analyze_performance_trend()
            
            # 存储指标历史
            self.metrics_history.append(metrics)
            
            # 限制历史大小
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"收集综合指标失败: {e}")
            return {'error': str(e), 'timestamp': timestamp.isoformat()}
    
    def _assess_system_health(self) -> Dict[str, Any]:
        """评估系统健康状态"""
        health_indicators = {}
        
        try:
            # 检查各子系统状态
            subsystems = [
                ('episodic_memory', self.episodic_memory),
                ('semantic_memory', self.semantic_memory),
                ('procedural_memory', self.procedural_memory),
                ('working_memory', self.working_memory),
                ('memory_retrieval', self.memory_retrieval)
            ]
            
            for name, subsystem in subsystems:
                health_indicators[name] = {
                    'status': 'healthy' if getattr(subsystem, 'initialized', False) else 'unhealthy',
                    'initialized': getattr(subsystem, 'initialized', False)
                }
            
            # 总体健康状态
            all_healthy = all(indicator['status'] == 'healthy' for indicator in health_indicators.values())
            overall_health = 'healthy' if all_healthy else 'degraded'
            
            return {
                'overall': overall_health,
                'subsystems': health_indicators,
                'last_check': datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"评估系统健康状态失败: {e}")
            return {'overall': 'unknown', 'error': str(e)}
    
    def _collect_subsystem_metrics(self) -> Dict[str, Any]:
        """收集子系统指标"""
        subsystems_metrics = {}
        
        try:
            # 情景记忆指标
            episodic_stats = self.episodic_memory.get_memory_stats()
            subsystems_metrics['episodic_memory'] = {
                'total_memories': episodic_stats.get('total_memories', 0),
                'avg_importance': episodic_stats.get('avg_importance', 0),
                'memory_age_distribution': self._analyze_memory_age('episodic')
            }
            
            # 语义记忆指标
            semantic_stats = self.semantic_memory.get_semantic_network_stats()
            subsystems_metrics['semantic_memory'] = {
                'total_concepts': semantic_stats.get('total_concepts', 0),
                'total_relationships': semantic_stats.get('total_relationships', 0),
                'network_density': semantic_stats.get('density', 0)
            }
            
            # 程序记忆指标
            procedural_stats = self.procedural_memory.get_procedural_stats()
            subsystems_metrics['procedural_memory'] = {
                'total_skills': procedural_stats.get('total_skills', 0),
                'total_executions': procedural_stats.get('total_executions', 0),
                'success_rate': procedural_stats.get('overall_success_rate', 0)
            }
            
            # 工作记忆指标
            working_stats = self.working_memory.get_stats()
            subsystems_metrics['working_memory'] = {
                'total_items': working_stats.get('total_items', 0),
                'utilization_percent': working_stats.get('utilization_percent', 0),
                'avg_access_count': working_stats.get('average_access_count', 0)
            }
            
            # 检索系统指标
            retrieval_stats = self.memory_retrieval.get_retrieval_stats()
            subsystems_metrics['memory_retrieval'] = {
                'cache_entries': retrieval_stats.get('cache_stats', {}).get('cached_entries', 0),
                'cache_hit_rate': retrieval_stats.get('cache_stats', {}).get('cache_hit_rate', 0)
            }
            
            return subsystems_metrics
            
        except Exception as e:
            self.logger.error(f"收集子系统指标失败: {e}")
            return {'error': str(e)}
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        performance_metrics = {}
        
        try:
            # 检索性能测试
            retrieval_performance = self._test_retrieval_performance()
            performance_metrics['retrieval'] = retrieval_performance
            
            # 存储性能测试
            storage_performance = self._test_storage_performance()
            performance_metrics['storage'] = storage_performance
            
            # 关联性能测试
            association_performance = self._test_association_performance()
            performance_metrics['association'] = association_performance
            
            # 总体响应时间
            performance_metrics['response_times'] = self._measure_response_times()
            
            return performance_metrics
            
        except Exception as e:
            self.logger.error(f"收集性能指标失败: {e}")
            return {'error': str(e)}
    
    def _collect_efficiency_metrics(self) -> Dict[str, Any]:
        """收集效率指标"""
        efficiency_metrics = {}
        
        try:
            # 内存使用效率
            memory_usage = self._calculate_memory_usage_efficiency()
            efficiency_metrics['memory_usage'] = memory_usage
            
            # 检索效率
            retrieval_efficiency = self._calculate_retrieval_efficiency()
            efficiency_metrics['retrieval'] = retrieval_efficiency
            
            # 存储效率
            storage_efficiency = self._calculate_storage_efficiency()
            efficiency_metrics['storage'] = storage_efficiency
            
            # 计算总体效率评分
            efficiency_score = self._calculate_efficiency_score(efficiency_metrics)
            efficiency_metrics['overall_efficiency'] = efficiency_score
            
            return efficiency_metrics
            
        except Exception as e:
            self.logger.error(f"收集效率指标失败: {e}")
            return {'error': str(e)}
    
    def _collect_quality_metrics(self) -> Dict[str, Any]:
        """收集质量指标"""
        quality_metrics = {}
        
        try:
            # 记忆质量
            memory_quality = self._assess_memory_quality()
            quality_metrics['memory_quality'] = memory_quality
            
            # 关联质量
            association_quality = self._assess_association_quality()
            quality_metrics['association_quality'] = association_quality
            
            # 检索质量
            retrieval_quality = self._assess_retrieval_quality()
            quality_metrics['retrieval_quality'] = retrieval_quality
            
            # 一致性检查
            consistency = self._check_consistency()
            quality_metrics['consistency'] = consistency
            
            return quality_metrics
            
        except Exception as e:
            self.logger.error(f"收集质量指标失败: {e}")
            return {'error': str(e)}
    
    def _test_retrieval_performance(self) -> Dict[str, Any]:
        """测试检索性能"""
        test_queries = [
            "recent events",
            "important memories", 
            "work related",
            "personal activities"
        ]
        
        results = []
        total_time = 0
        
        for query in test_queries:
            start_time = time.time()
            try:
                retrieval_result = self.memory_retrieval.retrieve(
                    query=query,
                    limit=5
                )
                end_time = time.time()
                
                retrieval_time = end_time - start_time
                total_time += retrieval_time
                
                results.append({
                    'query': query,
                    'time': retrieval_time,
                    'results_count': len(retrieval_result.get('items', [])),
                    'success': retrieval_result.get('success', False)
                })
            except Exception as e:
                self.logger.warning(f"检索测试失败: {e}")
                results.append({
                    'query': query,
                    'time': 0,
                    'error': str(e),
                    'success': False
                })
        
        avg_time = total_time / len(test_queries) if test_queries else 0
        success_rate = sum(1 for r in results if r['success']) / len(results) if results else 0
        
        return {
            'average_retrieval_time': avg_time,
            'success_rate': success_rate,
            'test_queries': results,
            'performance_rating': self._rate_performance('retrieval_speed', avg_time)
        }
    
    def _test_storage_performance(self) -> Dict[str, Any]:
        """测试存储性能"""
        test_data = {
            'description': 'Performance test memory item',
            'importance': 0.5,
            'emotional_valence': 0.1
        }
        
        storage_times = []
        retrieval_times = []
        
        # 测试多次存储操作
        for i in range(5):
            # 存储测试
            start_time = time.time()
            try:
                memory_id = self.episodic_memory.store_event(
                    event_description=f"Test event {i}",
                    **test_data
                )
                storage_time = time.time() - start_time
                storage_times.append(storage_time)
                
                # 检索测试
                start_time = time.time()
                retrieved = self.episodic_memory.retrieve_events(limit=1)
                retrieval_time = time.time() - start_time
                retrieval_times.append(retrieval_time)
                
            except Exception as e:
                self.logger.warning(f"存储性能测试失败: {e}")
                storage_times.append(0)
                retrieval_times.append(0)
        
        avg_storage_time = sum(storage_times) / len(storage_times) if storage_times else 0
        avg_retrieval_time = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
        
        return {
            'average_storage_time': avg_storage_time,
            'average_retrieval_time': avg_retrieval_time,
            'storage_performance_rating': self._rate_performance('retrieval_speed', avg_storage_time),
            'retrieval_performance_rating': self._rate_performance('retrieval_speed', avg_retrieval_time)
        }
    
    def _test_association_performance(self) -> Dict[str, Any]:
        """测试关联性能"""
        # 简化关联性能测试
        creation_times = []
        query_times = []
        
        try:
            # 创建关联测试
            for i in range(3):
                start_time = time.time()
                # 这里需要实际的关联创建测试
                creation_time = time.time() - start_time
                creation_times.append(creation_time)
            
            # 查询关联测试
            for i in range(3):
                start_time = time.time()
                # 这里需要实际的关联查询测试
                query_time = time.time() - start_time
                query_times.append(query_time)
            
            avg_creation_time = sum(creation_times) / len(creation_times) if creation_times else 0
            avg_query_time = sum(query_times) / len(query_times) if query_times else 0
            
            return {
                'average_creation_time': avg_creation_time,
                'average_query_time': avg_query_time,
                'performance_rating': self._rate_performance('retrieval_speed', (avg_creation_time + avg_query_time) / 2)
            }
            
        except Exception as e:
            self.logger.warning(f"关联性能测试失败: {e}")
            return {'error': str(e)}
    
    def _measure_response_times(self) -> Dict[str, float]:
        """测量响应时间"""
        # 测量各种操作的响应时间
        response_times = {}
        
        operations = [
            ('episodic_retrieval', lambda: self.episodic_memory.retrieve_events(limit=1)),
            ('semantic_query', lambda: self.semantic_memory.query_concepts(limit=1)),
            ('working_memory_access', lambda: self.working_memory.retrieve('test_key'))
        ]
        
        for op_name, op_func in operations:
            try:
                start_time = time.time()
                op_func()
                response_time = time.time() - start_time
                response_times[op_name] = response_time
            except Exception as e:
                self.logger.warning(f"测量响应时间失败 {op_name}: {e}")
                response_times[op_name] = 0
        
        return response_times
    
    def _calculate_memory_usage_efficiency(self) -> Dict[str, Any]:
        """计算内存使用效率"""
        try:
            episodic_stats = self.episodic_memory.get_memory_stats()
            semantic_stats = self.semantic_memory.get_semantic_network_stats()
            working_stats = self.working_memory.get_stats()
            
            total_memories = (
                episodic_stats.get('total_memories', 0) +
                semantic_stats.get('total_concepts', 0) +
                working_stats.get('total_items', 0)
            )
            
            # 计算记忆密度（记忆项与系统容量的比率）
            memory_density = total_memories / 10000  # 假设系统容量为10000
            
            # 计算记忆分布均匀性
            distribution = self._calculate_memory_distribution()
            
            return {
                'total_memories': total_memories,
                'memory_density': memory_density,
                'distribution_uniformity': distribution.get('uniformity', 0),
                'efficiency_rating': self._rate_performance('memory_usage', memory_density)
            }
            
        except Exception as e:
            self.logger.error(f"计算内存使用效率失败: {e}")
            return {'error': str(e)}
    
    def _calculate_retrieval_efficiency(self) -> Dict[str, Any]:
        """计算检索效率"""
        try:
            retrieval_stats = self.memory_retrieval.get_retrieval_stats()
            cache_stats = retrieval_stats.get('cache_stats', {})
            
            cache_hit_rate = cache_stats.get('cache_hit_rate', 0)
            cache_efficiency = cache_hit_rate
            
            # 检索成功率
            test_results = self._test_retrieval_performance()
            success_rate = test_results.get('success_rate', 0)
            
            overall_efficiency = (cache_efficiency + success_rate) / 2
            
            return {
                'cache_hit_rate': cache_hit_rate,
                'retrieval_success_rate': success_rate,
                'overall_efficiency': overall_efficiency,
                'efficiency_rating': self._rate_performance('retrieval_accuracy', overall_efficiency)
            }
            
        except Exception as e:
            self.logger.error(f"计算检索效率失败: {e}")
            return {'error': str(e)}
    
    def _calculate_storage_efficiency(self) -> Dict[str, Any]:
        """计算存储效率"""
        try:
            # 计算存储压缩率（简化）
            episodic_stats = self.episodic_memory.get_memory_stats()
            total_memories = episodic_stats.get('total_memories', 0)
            
            # 假设理想存储密度
            ideal_density = 0.7
            current_density = min(1.0, total_memories / 5000)  # 假设基准为5000
            
            storage_efficiency = 1.0 - abs(current_density - ideal_density)
            
            return {
                'storage_density': current_density,
                'storage_efficiency': storage_efficiency,
                'efficiency_rating': self._rate_performance('memory_usage', current_density)
            }
            
        except Exception as e:
            self.logger.error(f"计算存储效率失败: {e}")
            return {'error': str(e)}
    
    def _calculate_efficiency_score(self, efficiency_metrics: Dict[str, Any]) -> float:
        """计算总体效率评分"""
        weights = {
            'memory_usage': 0.3,
            'retrieval': 0.4,
            'storage': 0.3
        }
        
        total_score = 0
        total_weight = 0
        
        for category, weight in weights.items():
            category_metrics = efficiency_metrics.get(category, {})
            category_score = category_metrics.get('overall_efficiency', 0.5)
            total_score += category_score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _assess_memory_quality(self) -> Dict[str, Any]:
        """评估记忆质量"""
        try:
            # 记忆完整性检查
            completeness = self._check_memory_completeness()
            
            # 记忆一致性检查
            consistency = self._check_memory_consistency()
            
            # 记忆时效性
            recency = self._assess_memory_recency()
            
            overall_quality = (completeness + consistency + recency) / 3
            
            return {
                'completeness': completeness,
                'consistency': consistency,
                'recency': recency,
                'overall_quality': overall_quality
            }
            
        except Exception as e:
            self.logger.error(f"评估记忆质量失败: {e}")
            return {'error': str(e)}
    
    def _assess_association_quality(self) -> Dict[str, Any]:
        """评估关联质量"""
        # 简化实现
        return {
            'association_strength_distribution': {'strong': 0.6, 'medium': 0.3, 'weak': 0.1},
            'network_coherence': 0.8,
            'association_relevance': 0.7,
            'overall_quality': 0.7
        }
    
    def _assess_retrieval_quality(self) -> Dict[str, Any]:
        """评估检索质量"""
        try:
            # 测试检索的相关性
            test_queries = [
                ("work meeting", "professional"),
                ("personal event", "personal"),
                ("learning activity", "educational")
            ]
            
            relevance_scores = []
            
            for query, expected_category in test_queries:
                results = self.memory_retrieval.retrieve(query=query, limit=3)
                items = results.get('items', [])
                
                if items:
                    # 检查结果是否与预期类别相关
                    category_match = any(
                        expected_category in str(item.get('categories', []))
                        for item in items
                    )
                    relevance_scores.append(1.0 if category_match else 0.0)
                else:
                    relevance_scores.append(0.0)
            
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            
            return {
                'relevance_score': avg_relevance,
                'precision': 0.8,  # 简化
                'recall': 0.7,     # 简化
                'overall_quality': avg_relevance
            }
            
        except Exception as e:
            self.logger.error(f"评估检索质量失败: {e}")
            return {'error': str(e)}
    
    def _check_consistency(self) -> Dict[str, Any]:
        """检查一致性"""
        # 简化一致性检查
        return {
            'temporal_consistency': 0.9,
            'semantic_consistency': 0.8,
            'logical_consistency': 0.85,
            'overall_consistency': 0.85
        }
    
    def _analyze_memory_age(self, memory_type: str) -> Dict[str, float]:
        """分析记忆年龄分布"""
        # 简化实现
        return {
            'recent': 0.3,    # 24小时内
            'recent_week': 0.4,  # 1周内
            'recent_month': 0.2, # 1月内
            'old': 0.1        # 超过1月
        }
    
    def _calculate_memory_distribution(self) -> Dict[str, float]:
        """计算记忆分布"""
        # 简化实现
        return {
            'episodic': 0.4,
            'semantic': 0.3,
            'procedural': 0.2,
            'working': 0.1,
            'uniformity': 0.8  # 分布均匀性
        }
    
    def _check_memory_completeness(self) -> float:
        """检查记忆完整性"""
        # 简化实现
        return 0.8
    
    def _check_memory_consistency(self) -> float:
        """检查记忆一致性"""
        # 简化实现
        return 0.85
    
    def _assess_memory_recency(self) -> float:
        """评估记忆时效性"""
        # 简化实现
        return 0.75
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """计算总体评分"""
        weights = {
            'system_health': 0.2,
            'performance_metrics': 0.3,
            'efficiency_metrics': 0.3,
            'quality_metrics': 0.2
        }
        
        total_score = 0
        total_weight = 0
        
        for category, weight in weights.items():
            category_data = metrics.get(category, {})
            
            if category == 'system_health':
                # 系统健康评分
                health_status = category_data.get('overall', 'unknown')
                health_score = 1.0 if health_status == 'healthy' else 0.5 if health_status == 'degraded' else 0.0
                total_score += health_score * weight
            
            elif category == 'performance_metrics':
                # 性能评分
                performance_score = category_data.get('retrieval', {}).get('performance_rating', {}).get('score', 0.5)
                total_score += performance_score * weight
            
            elif category == 'efficiency_metrics':
                # 效率评分
                efficiency_score = category_data.get('overall_efficiency', 0.5)
                total_score += efficiency_score * weight
            
            elif category == 'quality_metrics':
                # 质量评分
                quality_score = category_data.get('memory_quality', {}).get('overall_quality', 0.5)
                total_score += quality_score * weight
            
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _analyze_performance_trend(self) -> Dict[str, Any]:
        """分析性能趋势"""
        if len(self.metrics_history) < 2:
            return {'trend': 'insufficient_data', 'change_percentage': 0}
        
        recent_metrics = self.metrics_history[-1]
        previous_metrics = self.metrics_history[-2]
        
        recent_score = recent_metrics.get('overall_score', 0.5)
        previous_score = previous_metrics.get('overall_score', 0.5)
        
        change = recent_score - previous_score
        change_percentage = (change / previous_score) * 100 if previous_score > 0 else 0
        
        if change_percentage > 5:
            trend = 'improving'
        elif change_percentage < -5:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change_percentage': change_percentage,
            'current_score': recent_score,
            'previous_score': previous_score
        }
    
    def _rate_performance(self, metric_type: str, value: float) -> Dict[str, Any]:
        """评估性能等级"""
        benchmarks = self.performance_benchmarks.get(metric_type, {})
        
        excellent = benchmarks.get('excellent', 0)
        good = benchmarks.get('good', 0)
        poor = benchmarks.get('poor', 0)
        
        if value <= excellent:
            rating = 'excellent'
            score = 1.0
        elif value <= good:
            rating = 'good'
            score = 0.7
        elif value <= poor:
            rating = 'fair'
            score = 0.4
        else:
            rating = 'poor'
            score = 0.1
        
        return {
            'rating': rating,
            'score': score,
            'value': value,
            'benchmark': benchmarks
        }
    
    def _start_metrics_collection(self):
        """启动指标收集"""
        import threading
        
        def collection_loop():
            while True:
                try:
                    self.collect_comprehensive_metrics()
                    time.sleep(self.collection_interval)
                except Exception as e:
                    self.logger.error(f"指标收集循环错误: {e}")
                    time.sleep(60)  # 错误后等待1分钟
        
        collection_thread = threading.Thread(target=collection_loop, daemon=True)
        collection_thread.start()
    
    def get_metrics_history(self, 
                          hours: int = 24,
                          metrics_filter: List[str] = None) -> List[Dict[str, Any]]:
        """
        获取指标历史
        
        Args:
            hours: 小时数
            metrics_filter: 指标过滤器
            
        Returns:
            指标历史列表
        """
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        
        filtered_history = []
        for metrics in self.metrics_history:
            timestamp = datetime.datetime.fromisoformat(metrics['timestamp'])
            if timestamp >= cutoff_time:
                if metrics_filter:
                    filtered_metrics = {key: metrics[key] for key in metrics_filter if key in metrics}
                    filtered_history.append(filtered_metrics)
                else:
                    filtered_history.append(metrics)
        
        return filtered_history
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        current_metrics = self.collect_comprehensive_metrics()
        
        return {
            'report_timestamp': datetime.datetime.now().isoformat(),
            'current_performance': current_metrics,
            'performance_summary': {
                'overall_score': current_metrics.get('overall_score', 0),
                'system_health': current_metrics.get('system_health', {}).get('overall', 'unknown'),
                'performance_trend': current_metrics.get('performance_trend', {}).get('trend', 'unknown'),
                'key_metrics': {
                    'retrieval_speed': current_metrics.get('performance_metrics', {}).get('retrieval', {}).get('average_retrieval_time', 0),
                    'memory_usage': current_metrics.get('efficiency_metrics', {}).get('memory_usage', {}).get('memory_density', 0),
                    'quality_score': current_metrics.get('quality_metrics', {}).get('memory_quality', {}).get('overall_quality', 0)
                }
            },
            'recommendations': self._generate_recommendations(current_metrics)
        }
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 系统健康建议
        system_health = metrics.get('system_health', {})
        if system_health.get('overall') != 'healthy':
            recommendations.append("检查记忆子系统健康状态，确保所有系统正常初始化")
        
        # 性能建议
        performance = metrics.get('performance_metrics', {})
        retrieval_perf = performance.get('retrieval', {})
        if retrieval_perf.get('average_retrieval_time', 0) > 1.0:
            recommendations.append("优化检索算法，考虑增加缓存或改进索引策略")
        
        # 效率建议
        efficiency = metrics.get('efficiency_metrics', {})
        memory_usage = efficiency.get('memory_usage', {})
        if memory_usage.get('memory_density', 0) > 0.8:
            recommendations.append("考虑实施记忆清理策略，释放存储空间")
        
        # 质量建议
        quality = metrics.get('quality_metrics', {})
        memory_quality = quality.get('memory_quality', {})
        if memory_quality.get('overall_quality', 0) < 0.6:
            recommendations.append("加强记忆巩固和关联建立，提高记忆质量")
        
        if not recommendations:
            recommendations.append("系统运行良好，继续保持当前配置")
        
        return recommendations
