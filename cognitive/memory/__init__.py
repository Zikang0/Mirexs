"""
记忆管理系统包
提供完整的记忆管理功能，包括存储、检索、巩固、遗忘和组织
"""

__version__ = "1.0.0"
__author__ = "记忆系统开发团队"
__description__ = "完整的AI记忆管理系统"

from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .procedural_memory import ProceduralMemory
from .working_memory import WorkingMemory
from .attention_mechanism import AttentionMechanism, AttentionType
from .memory_retrieval import MemoryRetrieval, RetrievalStrategy
from .memory_consolidation import MemoryConsolidation, ConsolidationStrategy
from .memory_forgetting import MemoryForgetting, ForgettingStrategy
from .memory_organization import MemoryOrganization, OrganizationStrategy
from .associative_memory import AssociativeMemory, AssociationType
from .memory_metrics import MemoryMetrics

# 记忆系统管理器
class MemorySystem:
    """记忆系统管理器 - 统一管理所有记忆子系统"""
    
    def __init__(self, config: dict = None):
        """
        初始化记忆系统
        
        Args:
            config: 系统配置字典
        """
        self.config = config or {}
        
        # 初始化各记忆子系统
        self.episodic = EpisodicMemory(self.config.get('episodic', {}))
        self.semantic = SemanticMemory(self.config.get('semantic', {}))
        self.procedural = ProceduralMemory(self.config.get('procedural', {}))
        self.working = WorkingMemory(self.config.get('working', {}))
        self.attention = AttentionMechanism(self.config.get('attention', {}))
        self.retrieval = MemoryRetrieval(self.config.get('retrieval', {}))
        self.consolidation = MemoryConsolidation(self.config.get('consolidation', {}))
        self.forgetting = MemoryForgetting(self.config.get('forgetting', {}))
        self.organization = MemoryOrganization(self.config.get('organization', {}))
        self.associative = AssociativeMemory(self.config.get('associative', {}))
        self.metrics = MemoryMetrics(self.config.get('metrics', {}))
        
        # 系统状态
        self.initialized = all([
            self.episodic.initialized,
            self.semantic.initialized,
            self.procedural.initialized,
            self.working.initialized,
            self.attention.initialized,
            self.retrieval.initialized,
            self.consolidation.initialized,
            self.forgetting.initialized,
            self.organization.initialized,
            self.associative.initialized,
            self.metrics.initialized
        ])
    
    def store_memory(self, 
                    memory_type: str,
                    content: dict,
                    **kwargs) -> str:
        """
        存储记忆
        
        Args:
            memory_type: 记忆类型 (episodic, semantic, procedural)
            content: 记忆内容
            **kwargs: 其他参数
            
        Returns:
            记忆ID
        """
        if memory_type == 'episodic':
            return self.episodic.store_event(**content, **kwargs)
        elif memory_type == 'semantic':
            return self.semantic.store_concept(**content, **kwargs)
        elif memory_type == 'procedural':
            return self.procedural.register_skill(**content, **kwargs)
        else:
            raise ValueError(f"不支持的记忆类型: {memory_type}")
    
    def retrieve_memories(self,
                         query: str,
                         memory_types: list = None,
                         **kwargs) -> dict:
        """
        检索记忆
        
        Args:
            query: 查询内容
            memory_types: 记忆类型列表
            **kwargs: 其他参数
            
        Returns:
            检索结果
        """
        memory_types = memory_types or ['episodic', 'semantic', 'procedural']
        return self.retrieval.retrieve(query, memory_types=memory_types, **kwargs)
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            'initialized': self.initialized,
            'subsystems': {
                'episodic_memory': self.episodic.initialized,
                'semantic_memory': self.semantic.initialized,
                'procedural_memory': self.procedural.initialized,
                'working_memory': self.working.initialized,
                'attention_mechanism': self.attention.initialized,
                'memory_retrieval': self.retrieval.initialized,
                'memory_consolidation': self.consolidation.initialized,
                'memory_forgetting': self.forgetting.initialized,
                'memory_organization': self.organization.initialized,
                'associative_memory': self.associative.initialized,
                'memory_metrics': self.metrics.initialized
            },
            'metrics': self.metrics.collect_comprehensive_metrics()
        }
    
    def run_maintenance(self) -> dict:
        """运行系统维护"""
        maintenance_results = {}
        
        # 记忆巩固
        try:
            consolidation_stats = self.consolidation.perform_consolidation()
            maintenance_results['consolidation'] = consolidation_stats
        except Exception as e:
            maintenance_results['consolidation'] = {'error': str(e)}
        
        # 记忆清理
        try:
            cleanup_stats = self.forgetting.auto_cleanup()
            maintenance_results['cleanup'] = cleanup_stats
        except Exception as e:
            maintenance_results['cleanup'] = {'error': str(e)}
        
        # 记忆组织
        try:
            # 获取未组织的记忆进行组织
            unorganized_memories = self.retrieval.retrieve(
                query="recent unorganized",
                limit=10
            )
            if unorganized_memories.get('items'):
                organization_stats = self.organization.batch_organize(
                    unorganized_memories['items']
                )
                maintenance_results['organization'] = organization_stats
        except Exception as e:
            maintenance_results['organization'] = {'error': str(e)}
        
        # 关联发现
        try:
            # 为最近记忆发现关联
            recent_memories = self.episodic.retrieve_events(limit=5)
            for memory in recent_memories:
                self.associative.discover_associations(memory)
            maintenance_results['association_discovery'] = {
                'processed_memories': len(recent_memories)
            }
        except Exception as e:
            maintenance_results['association_discovery'] = {'error': str(e)}
        
        return maintenance_results
    
    def shutdown(self):
        """关闭记忆系统"""
        # 执行最后的维护任务
        self.run_maintenance()
        
        # 收集最终指标
        final_metrics = self.metrics.collect_comprehensive_metrics()
        
        # 记录关闭事件
        shutdown_event = {
            'timestamp': __import__('datetime').datetime.now().isoformat(),
            'type': 'system_shutdown',
            'final_metrics': final_metrics
        }
        
        return shutdown_event

# 导出主要类
__all__ = [
    'MemorySystem',
    'EpisodicMemory',
    'SemanticMemory', 
    'ProceduralMemory',
    'WorkingMemory',
    'AttentionMechanism',
    'AttentionType',
    'MemoryRetrieval',
    'RetrievalStrategy',
    'MemoryConsolidation',
    'ConsolidationStrategy',
    'MemoryForgetting', 
    'ForgettingStrategy',
    'MemoryOrganization',
    'OrganizationStrategy',
    'AssociativeMemory',
    'AssociationType',
    'MemoryMetrics'
]

# 便捷函数
def create_memory_system(config: dict = None) -> MemorySystem:
    """
    创建记忆系统实例
    
    Args:
        config: 系统配置
        
    Returns:
        记忆系统实例
    """
    return MemorySystem(config)

def get_version() -> str:
    """获取系统版本"""
    return __version__
