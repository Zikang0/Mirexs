"""
记忆遗忘模块：智能遗忘不重要信息
实现基于重要性和访问模式的记忆遗忘机制
"""

import datetime
from typing import List, Dict, Any, Optional
import logging
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory

class ForgettingStrategy(Enum):
    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based" 
    IMPORTANCE_BASED = "importance_based"
    COMPETITIVE = "competitive"

class MemoryForgetting:
    """记忆遗忘系统 - 智能遗忘不重要信息"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # 初始化记忆系统
        self.episodic_memory = EpisodicMemory(config.get('episodic_config', {}))
        self.semantic_memory = SemanticMemory(config.get('semantic_config', {}))
        
        # 遗忘配置
        self.forgetting_threshold = self.config.get('forgetting_threshold', 0.2)
        self.min_retention_period = self.config.get('min_retention_period', 86400)  # 24小时
        self.max_memory_usage = self.config.get('max_memory_usage', 10000)  # 最大记忆项数
        
        # 遗忘策略权重
        self.strategy_weights = {
            'time_decay': self.config.get('time_decay_weight', 0.4),
            'usage_frequency': self.config.get('usage_frequency_weight', 0.3),
            'importance_level': self.config.get('importance_weight', 0.2),
            'emotional_salience': self.config.get('emotional_weight', 0.1)
        }
        
        # 遗忘历史
        self.forgetting_history = []
        
        self.initialized = True
        self.logger.info("记忆遗忘系统初始化成功")
    
    def evaluate_forgetting_candidates(self, 
                                    memory_type: str = "episodic",
                                    strategy: ForgettingStrategy = None,
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """
        评估遗忘候选
        
        Args:
            memory_type: 记忆类型
            strategy: 遗忘策略
            limit: 评估数量限制
            
        Returns:
            遗忘候选列表
        """
        strategy = strategy or ForgettingStrategy.TIME_BASED
        
        try:
            if memory_type == "episodic":
                candidates = self._get_episodic_candidates(limit)
            elif memory_type == "semantic":
                candidates = self._get_semantic_candidates(limit)
            else:
                return []
            
            # 计算遗忘分数
            scored_candidates = []
            for candidate in candidates:
                forget_score = self._calculate_forget_score(candidate, strategy)
                if forget_score >= self.forgetting_threshold:
                    candidate['forget_score'] = forget_score
                    candidate['forget_reasons'] = self._get_forget_reasons(candidate, forget_score)
                    scored_candidates.append(candidate)
            
            # 按遗忘分数排序
            scored_candidates.sort(key=lambda x: x['forget_score'], reverse=True)
            return scored_candidates
            
        except Exception as e:
            self.logger.error(f"评估遗忘候选失败: {e}")
            return []
    
    def execute_forgetting(self, 
                         candidates: List[Dict[str, Any]],
                         confirm: bool = True) -> Dict[str, Any]:
        """
        执行记忆遗忘
        
        Args:
            candidates: 遗忘候选列表
            confirm: 是否需要确认
            
        Returns:
            遗忘结果统计
        """
        if not candidates:
            return {"error": "无遗忘候选"}
        
        results = {
            'total_candidates': len(candidates),
            'forgotten': 0,
            'retained': 0,
            'errors': 0,
            'details': []
        }
        
        for candidate in candidates:
            try:
                # 检查是否满足最小保留期
                if not self._meets_min_retention(candidate):
                    results['retained'] += 1
                    results['details'].append({
                        'id': candidate.get('id'),
                        'action': 'retained',
                        'reason': 'min_retention_period'
                    })
                    continue
                
                # 执行遗忘
                if not confirm or self._should_forget(candidate):
                    success = self._forget_single_item(candidate)
                    if success:
                        results['forgotten'] += 1
                        results['details'].append({
                            'id': candidate.get('id'),
                            'action': 'forgotten',
                            'score': candidate.get('forget_score'),
                            'reasons': candidate.get('forget_reasons', [])
                        })
                        
                        # 记录遗忘历史
                        self._record_forgetting(candidate)
                    else:
                        results['errors'] += 1
                else:
                    results['retained'] += 1
                    results['details'].append({
                        'id': candidate.get('id'),
                        'action': 'retained', 
                        'reason': 'confirmation_denied'
                    })
                    
            except Exception as e:
                self.logger.error(f"遗忘单个项目失败: {e}")
                results['errors'] += 1
                results['details'].append({
                    'id': candidate.get('id'),
                    'action': 'error',
                    'error': str(e)
                })
        
        # 记录遗忘会话
        forgetting_session = {
            'timestamp': datetime.datetime.now().isoformat(),
            'results': results,
            'strategy_used': candidates[0].get('evaluation_strategy', 'unknown') if candidates else 'unknown'
        }
        self.forgetting_history.append(forgetting_session)
        
        self.logger.info(f"记忆遗忘完成: {results['forgotten']} 遗忘, {results['retained']} 保留, {results['errors']} 错误")
        return results
    
    def _get_episodic_candidates(self, limit: int) -> List[Dict[str, Any]]:
        """获取情景记忆候选"""
        try:
            # 获取所有情景记忆进行评估
            all_events = self.episodic_memory.retrieve_events(limit=limit * 2)
            return all_events[:limit]
        except Exception as e:
            self.logger.error(f"获取情景记忆候选失败: {e}")
            return []
    
    def _get_semantic_candidates(self, limit: int) -> List[Dict[str, Any]]:
        """获取语义记忆候选"""
        try:
            # 获取低重要性概念
            all_concepts = self.semantic_memory.query_concepts(limit=limit * 2)
            # 按重要性排序，取重要性较低的概念
            all_concepts.sort(key=lambda x: x.get('importance', 0.5))
            return all_concepts[:limit]
        except Exception as e:
            self.logger.error(f"获取语义记忆候选失败: {e}")
            return []
    
    def _calculate_forget_score(self, item: Dict[str, Any], strategy: ForgettingStrategy) -> float:
        """计算遗忘分数"""
        if strategy == ForgettingStrategy.TIME_BASED:
            return self._time_based_forget_score(item)
        elif strategy == ForgettingStrategy.USAGE_BASED:
            return self._usage_based_forget_score(item)
        elif strategy == ForgettingStrategy.IMPORTANCE_BASED:
            return self._importance_based_forget_score(item)
        elif strategy == ForgettingStrategy.COMPETITIVE:
            return self._competitive_forget_score(item)
        else:
            return 0.0
    
    def _time_based_forget_score(self, item: Dict[str, Any]) -> float:
        """基于时间的遗忘分数"""
        timestamp = item.get('timestamp') or item.get('created_at')
        if not timestamp:
            return 0.5
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return 0.5
        
        now = datetime.datetime.now()
        age_days = (now - timestamp).total_seconds() / 86400
        
        # 艾宾浩斯遗忘曲线近似
        # 信息在1天后保留约35%，30天后保留约21%
        retention_rate = 0.35 * (30 / (age_days + 1)) ** 0.5
        forget_score = 1.0 - retention_rate
        
        return min(1.0, forget_score)
    
    def _usage_based_forget_score(self, item: Dict[str, Any]) -> float:
        """基于使用频率的遗忘分数"""
        access_count = item.get('access_count', 0)
        last_accessed = item.get('last_accessed')
        
        # 低访问频率惩罚
        frequency_score = 1.0 - min(1.0, access_count / 10.0)
        
        # 长时间未访问惩罚
        recency_penalty = 0.0
        if last_accessed:
            if isinstance(last_accessed, str):
                try:
                    last_accessed = datetime.datetime.fromisoformat(last_accessed)
                except:
                    last_accessed = None
            
            if last_accessed:
                days_since_access = (datetime.datetime.now() - last_accessed).total_seconds() / 86400
                recency_penalty = min(1.0, days_since_access / 30.0)
        
        forget_score = (frequency_score * 0.6 + recency_penalty * 0.4)
        return forget_score
    
    def _importance_based_forget_score(self, item: Dict[str, Any]) -> float:
        """基于重要性的遗忘分数"""
        importance = item.get('importance', 0.5)
        emotional_salience = abs(item.get('emotional_valence', 0))
        
        # 低重要性和低情感显著性导致高遗忘分数
        importance_factor = 1.0 - importance
        emotional_factor = 1.0 - emotional_salience
        
        forget_score = (importance_factor * 0.7 + emotional_factor * 0.3)
        return forget_score
    
    def _competitive_forget_score(self, item: Dict[str, Any]) -> float:
        """基于竞争机制的遗忘分数"""
        # 综合多种因素的竞争性遗忘
        time_score = self._time_based_forget_score(item)
        usage_score = self._usage_based_forget_score(item)
        importance_score = self._importance_based_forget_score(item)
        
        # 加权综合
        forget_score = (
            time_score * self.strategy_weights['time_decay'] +
            usage_score * self.strategy_weights['usage_frequency'] +
            importance_score * self.strategy_weights['importance_level']
        )
        
        return forget_score
    
    def _get_forget_reasons(self, item: Dict[str, Any], forget_score: float) -> List[str]:
        """获取遗忘原因"""
        reasons = []
        
        # 时间相关原因
        if self._time_based_forget_score(item) > 0.6:
            reasons.append("长时间未访问")
        
        # 使用频率原因
        if self._usage_based_forget_score(item) > 0.6:
            reasons.append("低使用频率")
        
        # 重要性原因
        if self._importance_based_forget_score(item) > 0.6:
            reasons.append("低重要性")
        
        # 情感原因
        emotional_salience = abs(item.get('emotional_valence', 0))
        if emotional_salience < 0.2:
            reasons.append("低情感显著性")
        
        return reasons
    
    def _meets_min_retention(self, item: Dict[str, Any]) -> bool:
        """检查是否满足最小保留期"""
        timestamp = item.get('timestamp') or item.get('created_at')
        if not timestamp:
            return True
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp)
            except:
                return True
        
        age_seconds = (datetime.datetime.now() - timestamp).total_seconds()
        return age_seconds >= self.min_retention_period
    
    def _should_forget(self, item: Dict[str, Any]) -> bool:
        """决定是否应该遗忘"""
        # 检查是否有特殊保留标记
        if item.get('never_forget', False):
            return False
        
        # 检查是否为核心知识
        if item.get('is_core_knowledge', False):
            return False
        
        # 检查用户显式标记
        if item.get('user_retention', 'auto') == 'keep':
            return False
        
        return True
    
    def _forget_single_item(self, item: Dict[str, Any]) -> bool:
        """遗忘单个项目"""
        memory_type = item.get('memory_type', 'episodic')
        
        try:
            if memory_type == 'episodic':
                # 从情景记忆中移除
                # 注意：实际实现中需要具体的删除方法
                # 这里使用简化实现
                self.logger.info(f"遗忘情景记忆: {item.get('id')}")
                return True
                
            elif memory_type == 'semantic':
                # 从语义记忆中移除
                # 注意：实际实现中需要具体的删除方法
                self.logger.info(f"遗忘语义概念: {item.get('id')}")
                return True
                
            else:
                self.logger.warning(f"未知的记忆类型: {memory_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"遗忘项目失败: {e}")
            return False
    
    def _record_forgetting(self, item: Dict[str, Any]):
        """记录遗忘历史"""
        forget_record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'item_id': item.get('id'),
            'item_type': item.get('memory_type', 'unknown'),
            'forget_score': item.get('forget_score'),
            'reasons': item.get('forget_reasons', []),
            'description': item.get('description', '')[:100]  # 截断长描述
        }
        
        self.forgetting_history.append(forget_record)
        
        # 限制历史记录大小
        if len(self.forgetting_history) > 1000:
            self.forgetting_history = self.forgetting_history[-1000:]
    
    def get_memory_usage_stats(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        try:
            episodic_stats = self.episodic_memory.get_memory_stats()
            semantic_stats = self.semantic_memory.get_semantic_network_stats()
            
            total_episodic = episodic_stats.get('total_memories', 0)
            total_semantic = semantic_stats.get('total_concepts', 0)
            total_memories = total_episodic + total_semantic
            
            usage_percentage = (total_memories / self.max_memory_usage) * 100 if self.max_memory_usage > 0 else 0
            
            return {
                'total_episodic_memories': total_episodic,
                'total_semantic_concepts': total_semantic,
                'total_memories': total_memories,
                'max_capacity': self.max_memory_usage,
                'usage_percentage': usage_percentage,
                'needs_cleanup': usage_percentage > 80
            }
            
        except Exception as e:
            self.logger.error(f"获取内存使用统计失败: {e}")
            return {"error": str(e)}
    
    def auto_cleanup(self, target_usage: float = 0.7) -> Dict[str, Any]:
        """
        自动清理记忆
        
        Args:
            target_usage: 目标使用率（0-1）
            
        Returns:
            清理结果
        """
        current_stats = self.get_memory_usage_stats()
        if 'error' in current_stats:
            return current_stats
        
        current_usage = current_stats.get('usage_percentage', 0) / 100.0
        if current_usage <= target_usage:
            return {"message": "无需清理，当前使用率正常"}
        
        # 计算需要清理的数量
        excess_memories = int((current_usage - target_usage) * self.max_memory_usage)
        
        # 获取遗忘候选
        episodic_candidates = self.evaluate_forgetting_candidates(
            memory_type="episodic",
            strategy=ForgettingStrategy.COMPETITIVE,
            limit=excess_memories
        )
        
        semantic_candidates = self.evaluate_forgetting_candidates(
            memory_type="semantic", 
            strategy=ForgettingStrategy.COMPETITIVE,
            limit=excess_memories // 2
        )
        
        all_candidates = episodic_candidates + semantic_candidates
        
        # 执行遗忘
        results = self.execute_forgetting(all_candidates, confirm=False)
        
        # 更新统计
        new_stats = self.get_memory_usage_stats()
        results['memory_stats'] = {
            'before': current_stats,
            'after': new_stats
        }
        
        return results
    
    def get_forgetting_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取遗忘历史"""
        return self.forgetting_history[-limit:] if limit else self.forgetting_history
    
    def analyze_forgetting_patterns(self) -> Dict[str, Any]:
        """分析遗忘模式"""
        if not self.forgetting_history:
            return {"error": "无遗忘历史数据"}
        
        total_forgotten = len(self.forgetting_history)
        
        # 按类型统计
        type_distribution = {}
        for record in self.forgetting_history:
            item_type = record.get('item_type', 'unknown')
            type_distribution[item_type] = type_distribution.get(item_type, 0) + 1
        
        # 平均遗忘分数
        avg_score = sum(record.get('forget_score', 0) for record in self.forgetting_history) / total_forgotten
        
        # 常见遗忘原因
        reason_counts = {}
        for record in self.forgetting_history:
            for reason in record.get('reasons', []):
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        return {
            "total_forgotten_items": total_forgotten,
            "type_distribution": type_distribution,
            "average_forget_score": avg_score,
            "common_reasons": reason_counts,
            "current_memory_usage": self.get_memory_usage_stats()
        }

