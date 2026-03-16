"""
多智能体系统模块

提供智能体协调、协作、通信、角色特化、任务分配、冲突解决和监控功能。
"""

from .swarm_orchestrator import SwarmOrchestrator, SwarmState, SwarmMember, SwarmTask
from .collaboration_engine import CollaborationEngine, CollaborationPattern, CollaborationSession, CollaborationResult
from .agent_communication import AgentCommunication, MessageType, MessagePriority, AgentMessage, CommunicationChannel
from .role_specializer import RoleSpecializer, RoleType, RoleProfile, SpecializationResult
from .task_allocator import TaskAllocator, AllocationStrategy, TaskPriority, Task, AgentCapacity, AllocationResult
from .conflict_resolver import ConflictResolver, ConflictType, ResolutionStrategy, Conflict, ResolutionProposal, ConflictResolution
from .agent_monitor import AgentMonitor, AgentStatus, HealthStatus, AgentMetrics, HealthCheck, PerformanceAlert

__all__ = [
    # SwarmOrchestrator
    'SwarmOrchestrator', 'SwarmState', 'SwarmMember', 'SwarmTask',
    
    # CollaborationEngine
    'CollaborationEngine', 'CollaborationPattern', 'CollaborationSession', 'CollaborationResult',
    
    # AgentCommunication
    'AgentCommunication', 'MessageType', 'MessagePriority', 'AgentMessage', 'CommunicationChannel',
    
    # RoleSpecializer
    'RoleSpecializer', 'RoleType', 'RoleProfile', 'SpecializationResult',
    
    # TaskAllocator
    'TaskAllocator', 'AllocationStrategy', 'TaskPriority', 'Task', 'AgentCapacity', 'AllocationResult',
    
    # ConflictResolver
    'ConflictResolver', 'ConflictType', 'ResolutionStrategy', 'Conflict', 'ResolutionProposal', 'ConflictResolution',
    
    # AgentMonitor
    'AgentMonitor', 'AgentStatus', 'HealthStatus', 'AgentMetrics', 'HealthCheck', 'PerformanceAlert'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "多智能体协调与协作系统"

def get_agents_module_info():
    """获取多智能体系统模块信息"""
    return {
        "module": "agents",
        "version": __version__,
        "description": __description__,
        "components": {
            "swarm_orchestrator": "群体协调器 - 管理智能体群体的形成、协作和解散",
            "collaboration_engine": "协作引擎 - 促进智能体之间的高效协作和知识共享",
            "agent_communication": "智能体通信 - 实现智能体间的通信协议和消息传递机制",
            "role_specializer": "角色特化器 - 实现智能体角色的动态特化和能力优化",
            "task_allocator": "任务分配器 - 实现智能体任务分配算法和负载均衡",
            "conflict_resolver": "冲突解决器 - 解决智能体间的冲突和资源竞争",
            "agent_monitor": "智能体监控器 - 监控智能体状态和性能"
        }
    }
