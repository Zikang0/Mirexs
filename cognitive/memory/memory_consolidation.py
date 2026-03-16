"""
记忆巩固模块：巩固重要记忆
实现基于睡眠和重复的记忆巩固机制
"""

import datetime
import time
from typing import List, Dict, Any, Optional
import threading
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory

class ConsolidationStrategy(Enum):
    REPETITION = "repetition"
    ELABORATION = "elaboration"
    SLEEP = "sleep"
    SPACING = "spacing"

class MemoryConsolidation:
    """记忆巩固系统 - 巩固重要记忆"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        
        # 巩固配置
        self.consolidation_threshold = self.config.get('consolidation_threshold', 0.7)
        self.consolidation_interval = self.config.get('consolidation_interval', 3600)  # 1小时
        self.max_consolidation_per_session = self.config.get('max_consolidation_per_session', 10)
        
        # 巩固状态
        self.consolidation_queue = []
        self.consolidation_history = []
        self.is_consolidating = False
        
        # 启动后台巩固任务
        self._start_consolidation_scheduler()
        
        self.initialized = True
        self.logger.info("记忆巩固系统初始化成功")
    
    def schedule_consolidation(self, memory_items: List[Dict[str, Any]], strategy: ConsolidationStrategy = None):
        """
        安排记忆巩固
        
        Args:
            memory_items: 需要巩固的记忆项
            strategy: 巩固策略
        """
        strategy = strategy or ConsolidationStrategy.REPETITION
        
        for item in memory_items:
            consolidation_task = {
                'item': item,
                'strategy': strategy,
                'scheduled_time': datetime.datetime.now(),
                'priority': self._calculate_consolidation_priority(item),
                'attempts': 0,
                'last_attempt': None,
                'status': 'scheduled'
            }
            
            self.consolidation_queue.append(consolidation_task)
        
        self.logger.info(f"安排了 {len(memory_items)} 个记忆项的巩固")
    
    def perform_consolidation(self, max_items: int = None) -> Dict[str, Any]:
        """
        执行记忆巩固
        
        Args:
            max_items: 最大处理项数
            
        Returns:
            巩固结果统计
        """
        if self.is_consolidating:
            return {"error": "巩固过程正在进行中"}
        
        self.is_consolidating = True
        max_items = max_items or self.max_consolidation_per_session
        
        try:
            # 获取待巩固项
            pending_tasks = [t for t in self.consolidation_queue if t['status'] == 'scheduled']
            pending_tasks.sort(key=lambda x: x['priority'], reverse=True)
            tasks_to_process = pending_tasks[:max_items]
            
            results = {
                'total_processed': len(tasks_to_process),
                'successful': 0,
                'failed': 0,
                'details': []
            }
            
            for task in tasks_to_process:
                task_result = self._consolidate_single_item(task)
                results['details'].append(task_result)
                
                if task_result['success']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                # 更新任务状态
                task['attempts'] += 1
                task['last_attempt'] = datetime.datetime.now()
                task['status'] = 'completed' if task_result['success'] else 'failed'
            
            # 记录巩固会话
            consolidation_session = {
                'timestamp': datetime.datetime.now().isoformat(),
                'results': results,
                'duration': task_result.get('duration', 0) if results['details'] else 0
            }
            self.consolidation_history.append(consolidation_session)
            
            # 清理已完成的任务
            self._cleanup_completed_tasks()
            
            self.logger.info(f"记忆巩固完成: {results['successful']} 成功, {results['failed']} 失败")
            return results
            
        except Exception as e:
            self.logger.error(f"记忆巩固过程失败: {e}")
            return {"error": str(e)}
        finally:
            self.is_consolidating = False
    
    def _consolidate_single_item(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """巩固单个记忆项"""
        start_time = time.time()
        item = task['item']
        strategy = task['strategy']
        
        try:
            memory_type = item.get('memory_type', 'episodic')
            
            if strategy == ConsolidationStrategy.REPETITION:
                result = self._apply_repetition_consolidation(item, memory_type)
            elif strategy == ConsolidationStrategy.ELABORATION:
                result = self._apply_elaboration_consolidation(item, memory_type)
            elif strategy == ConsolidationStrategy.SLEEP:
                result = self._apply_sleep_consolidation(item, memory_type)
            elif strategy == ConsolidationStrategy.SPACING:
                result = self._apply_spacing_consolidation(item, memory_type)
            else:
                result = {"success": False, "error": f"未知的巩固策略: {strategy}"}
            
            result['duration'] = time.time() - start_time
            return result
            
        except Exception as e:
            self.logger.error(f"单个记忆项巩固失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    def _apply_repetition_consolidation(self, item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """应用重复巩固策略"""
        if memory_type == 'episodic':
            # 增强情景记忆的检索强度
            current_importance = item.get('importance', 0.5)
            new_importance = min(1.0, current_importance * 1.1)  # 提高10%
            
            # 在实际系统中，这里应该更新记忆项的重要性
            return {
                "success": True,
                "strategy": "repetition",
                "memory_type": memory_type,
                "importance_increase": new_importance - current_importance
            }
        
        elif memory_type == 'semantic':
            # 增强语义关系的强度
            return {
                "success": True,
                "strategy": "repetition", 
                "memory_type": memory_type,
                "action": "semantic_strengthening"
            }
        
        return {"success": False, "error": f"不支持的记忆类型: {memory_type}"}
    
    def _apply_elaboration_consolidation(self, item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """应用精细化巩固策略"""
        try:
            if memory_type == 'episodic':
                # 为情景记忆添加语义关联
                event_description = item.get('description', '')
                if event_description:
                    # 提取关键词创建语义关联
                    keywords = self._extract_keywords(event_description)
                    for keyword in keywords[:3]:  # 处理前3个关键词
                        self._create_semantic_association(item, keyword)
                
                return {
                    "success": True,
                    "strategy": "elaboration",
                    "memory_type": memory_type,
                    "associations_created": len(keywords[:3])
                }
            
            elif memory_type == 'semantic':
                # 扩展语义网络
                concept_name = item.get('name', '')
                if concept_name:
                    related_concepts = self._find_related_concepts(concept_name)
                    for related in related_concepts[:2]:
                        self.semantic_memory.create_relationship(
                            concept_name, related, "related_to", confidence=0.7
                        )
                
                return {
                    "success": True,
                    "strategy": "elaboration",
                    "memory_type": memory_type,
                    "relationships_created": len(related_concepts[:2])
                }
            
            return {"success": False, "error": f"不支持的记忆类型: {memory_type}"}
            
        except Exception as e:
            return {"success": False, "error": f"精细化巩固失败: {e}"}
    
    def _apply_sleep_consolidation(self, item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """应用睡眠巩固策略"""
        # 模拟睡眠期间的记忆重组
        # 在实际系统中，这会在系统空闲或睡眠时执行
        
        if memory_type == 'episodic':
            # 睡眠期间的情景记忆重组
            reorganization_score = self._reorganize_episodic_memory(item)
            return {
                "success": True,
                "strategy": "sleep",
                "memory_type": memory_type,
                "reorganization_score": reorganization_score
            }
        
        elif memory_type == 'semantic':
            # 睡眠期间的语义记忆整合
            integration_score = self._integrate_semantic_memory(item)
            return {
                "success": True,
                "strategy": "sleep",
                "memory_type": memory_type,
                "integration_score": integration_score
            }
        
        return {"success": False, "error": f"不支持的记忆类型: {memory_type}"}
    
    def _apply_spacing_consolidation(self, item: Dict[str, Any], memory_type: str) -> Dict[str, Any]:
        """应用间隔巩固策略"""
        # 基于间隔效应安排复习
        current_attempts = item.get('consolidation_attempts', 0)
        next_interval = self._calculate_next_interval(current_attempts)
        
        # 安排下一次巩固
        next_consolidation = {
            'item': item,
            'strategy': ConsolidationStrategy.SPACING,
            'scheduled_time': datetime.datetime.now() + datetime.timedelta(hours=next_interval),
            'priority': item.get('importance', 0.5)
        }
        self.consolidation_queue.append(next_consolidation)
        
        return {
            "success": True,
            "strategy": "spacing",
            "memory_type": memory_type,
            "next_interval_hours": next_interval,
            "current_attempt": current_attempts + 1
        }
    
    def _calculate_consolidation_priority(self, item: Dict[str, Any]) -> float:
        """计算巩固优先级"""
        base_priority = item.get('importance', 0.5)
        
        # 时效性调整
        recency = self._compute_recency_score(item)
        recency_factor = 1.0 - recency  # 越旧的记忆优先级越高
        
        # 访问频率调整
        access_count = item.get('access_count', 0)
        frequency_factor = min(1.0, access_count / 10.0)
        
        # 情感强度调整
        emotional_intensity = abs(item.get('emotional_valence', 0))
        
        priority = (
            base_priority * 0.5 +
            recency_factor * 0.3 +
            frequency_factor * 0.1 +
            emotional_intensity * 0.1
        )
        
        return priority
    
    def _compute_recency_score(self, item: Dict[str, Any]) -> float:
        """计算时效性分数"""
        timestamp = item.get('timestamp') or item.get('last_accessed')
        if not timestamp:
            return 0.5
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return 0.5
        
        now = datetime.datetime.now()
        time_diff = (now - timestamp).total_seconds() / 86400  # 天数
        
        # 指数衰减
        recency = 2.0 ** (-time_diff / 7.0)  # 7天半衰期
        return recency
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化实现）"""
        # 在实际系统中，应使用NLP技术提取关键词
        words = text.lower().split()
        # 过滤停用词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords[:10]  # 返回前10个关键词
    
    def _create_semantic_association(self, episodic_item: Dict[str, Any], keyword: str):
        """创建语义关联"""
        try:
            # 检查是否已存在相关概念
            existing_concepts = self.semantic_memory.query_concepts(query=keyword, limit=1)
            if existing_concepts:
                concept = existing_concepts[0]
            else:
                # 创建新概念
                concept_id = self.semantic_memory.store_concept(
                    name=keyword,
                    concept_type="entity",
                    description=f"Associated with episodic memory {episodic_item.get('id')}"
                )
                concept = self.semantic_memory.query_concepts(concept_id)[0]
            
            # 创建关联
            self.semantic_memory.create_relationship(
                episodic_item.get('id'), concept['id'], "related_to",
                properties={'association_type': 'consolidation'}
            )
            
        except Exception as e:
            self.logger.warning(f"创建语义关联失败: {e}")
    
    def _find_related_concepts(self, concept_name: str) -> List[str]:
        """查找相关概念"""
        try:
            related = self.semantic_memory.get_related_concepts(concept_name, depth=1)
            return [r[0]['name'] for r in related if r[0]['name'] != concept_name]
        except:
            return []
    
    def _reorganize_episodic_memory(self, item: Dict[str, Any]) -> float:
        """重组情景记忆"""
        # 模拟记忆重组过程
        # 在实际系统中，这会涉及记忆的重新组织和连接强化
        return 0.8  # 模拟重组分数
    
    def _integrate_semantic_memory(self, item: Dict[str, Any]) -> float:
        """整合语义记忆"""
        # 模拟语义整合过程
        return 0.7  # 模拟整合分数
    
    def _calculate_next_interval(self, current_attempt: int) -> float:
        """计算下一个间隔时间（小时）"""
        # 基于间隔重复算法（简化版）
        if current_attempt == 0:
            return 1.0  # 1小时后
        elif current_attempt == 1:
            return 24.0  # 1天后
        elif current_attempt == 2:
            return 72.0  # 3天后
        else:
            return 168.0  # 7天后
    
    def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        # 保留最近100个任务记录，移除旧的成功任务
        completed_tasks = [t for t in self.consolidation_queue if t['status'] == 'completed']
        failed_tasks = [t for t in self.consolidation_queue if t['status'] == 'failed']
        scheduled_tasks = [t for t in self.consolidation_queue if t['status'] == 'scheduled']
        
        # 按时间排序已完成任务，保留最新的
        completed_tasks.sort(key=lambda x: x.get('last_attempt', datetime.datetime.min), reverse=True)
        completed_to_keep = completed_tasks[:50]  # 保留50个最新完成的任务
        
        self.consolidation_queue = scheduled_tasks + failed_tasks + completed_to_keep
    
    def _start_consolidation_scheduler(self):
        """启动巩固调度器"""
        def scheduler_loop():
            while True:
                try:
                    # 检查是否有待处理任务
                    pending_count = len([t for t in self.consolidation_queue if t['status'] == 'scheduled'])
                    if pending_count > 0 and not self.is_consolidating:
                        self.logger.info(f"调度器发现 {pending_count} 个待巩固任务")
                        self.perform_consolidation()
                    
                    time.sleep(self.consolidation_interval)
                    
                except Exception as e:
                    self.logger.error(f"巩固调度器错误: {e}")
                    time.sleep(60)  # 错误后等待1分钟
        
        scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_thread.start()
    
    def get_consolidation_queue_status(self) -> Dict[str, Any]:
        """获取巩固队列状态"""
        scheduled = [t for t in self.consolidation_queue if t['status'] == 'scheduled']
        completed = [t for t in self.consolidation_queue if t['status'] == 'completed']
        failed = [t for t in self.consolidation_queue if t['status'] == 'failed']
        
        return {
            'total_tasks': len(self.consolidation_queue),
            'scheduled': len(scheduled),
            'completed': len(completed),
            'failed': len(failed),
            'next_scheduled': min([t['scheduled_time'] for t in scheduled]) if scheduled else None
        }
    
    def get_consolidation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取巩固历史"""
        return self.consolidation_history[-limit:] if limit else self.consolidation_history
    
    def analyze_consolidation_patterns(self) -> Dict[str, Any]:
        """分析巩固模式"""
        if not self.consolidation_history:
            return {"error": "无巩固历史数据"}
        
        total_sessions = len(self.consolidation_history)
        total_items = sum(session['results']['total_processed'] for session in self.consolidation_history)
        success_rate = sum(session['results']['successful'] for session in self.consolidation_history) / total_items if total_items > 0 else 0
        
        # 策略使用统计
        strategy_usage = {}
        for task in self.consolidation_queue:
            strategy = task['strategy'].value
            strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
        
        return {
            "total_consolidation_sessions": total_sessions,
            "total_items_processed": total_items,
            "overall_success_rate": success_rate,
            "strategy_usage": strategy_usage,
            "queue_status": self.get_consolidation_queue_status()
        }
