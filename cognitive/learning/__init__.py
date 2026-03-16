# cognitive/learning/__init__.py
"""
学习与适应系统模块

这个模块实现了系统的学习能力，包括元学习、技能获取、经验回放、
模式识别和知识管理等功能，支持系统从交互中持续学习和进化。
"""

import os
import sys
from typing import Dict, List, Any, Optional

# 导入所有学习组件
from .meta_learner import MetaLearner, get_meta_learner
from .skill_acquisition import SkillAcquisitionSystem, get_skill_acquisition_system
from .experience_replayer import ExperienceReplayer, get_experience_replayer
from .pattern_recognizer import PatternRecognizer, get_pattern_recognizer
from .knowledge_curator import KnowledgeCurator, get_knowledge_curator
from .performance_optimizer import PerformanceOptimizer, get_performance_optimizer
from .transfer_learning import TransferLearningSystem, get_transfer_learning_system
from .reinforcement_learner import ReinforcementLearner, get_reinforcement_learner
from .curriculum_learning import CurriculumLearning, get_curriculum_learning
from .adaptation_engine import AdaptationEngine, get_adaptation_engine
from .learning_evaluator import LearningEvaluator, get_learning_evaluator

__all__ = [
    # 元学习
    'MetaLearner',
    'get_meta_learner',
    
    # 技能获取
    'SkillAcquisitionSystem', 
    'get_skill_acquisition_system',
    
    # 经验回放
    'ExperienceReplayer',
    'get_experience_replayer',
    
    # 模式识别
    'PatternRecognizer',
    'get_pattern_recognizer',
    
    # 知识管理
    'KnowledgeCurator',
    'get_knowledge_curator',
    
    # 性能优化
    'PerformanceOptimizer',
    'get_performance_optimizer',
    
    # 迁移学习
    'TransferLearningSystem',
    'get_transfer_learning_system',
    
    # 强化学习
    'ReinforcementLearner',
    'get_reinforcement_learner',
    
    # 课程学习
    'CurriculumLearning',
    'get_curriculum_learning',
    
    # 适应引擎
    'AdaptationEngine',
    'get_adaptation_engine',
    
    # 学习评估
    'LearningEvaluator',
    'get_learning_evaluator'
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'Mirexs AI Team'
__description__ = '认知核心层 - 学习与适应系统'

class LearningSystemCoordinator:
    """学习系统协调器"""
    
    def __init__(self):
        self.components = {}
        self.is_initialized = False
        self.coordination_config = {
            'auto_save_interval': 300,  # 5分钟自动保存
            'performance_monitoring': True,
            'cross_component_learning': True,
            'adaptive_coordination': True
        }
    
    def initialize_all_components(self) -> Dict[str, Any]:
        """初始化所有学习组件"""
        if self.is_initialized:
            return {'status': 'already_initialized'}
        
        initialization_report = {}
        
        try:
            # 初始化元学习器
            meta_learner = get_meta_learner()
            self.components['meta_learner'] = meta_learner
            initialization_report['meta_learner'] = 'success'
        except Exception as e:
            initialization_report['meta_learner'] = f'failed: {str(e)}'
        
        try:
            # 初始化技能获取系统
            skill_system = get_skill_acquisition_system()
            self.components['skill_acquisition'] = skill_system
            initialization_report['skill_acquisition'] = 'success'
        except Exception as e:
            initialization_report['skill_acquisition'] = f'failed: {str(e)}'
        
        try:
            # 初始化经验回放系统
            experience_replayer = get_experience_replayer()
            self.components['experience_replayer'] = experience_replayer
            initialization_report['experience_replayer'] = 'success'
        except Exception as e:
            initialization_report['experience_replayer'] = f'failed: {str(e)}'
        
        try:
            # 初始化模式识别器
            pattern_recognizer = get_pattern_recognizer()
            self.components['pattern_recognizer'] = pattern_recognizer
            initialization_report['pattern_recognizer'] = 'success'
        except Exception as e:
            initialization_report['pattern_recognizer'] = f'failed: {str(e)}'
        
        try:
            # 初始化知识管理系统
            knowledge_curator = get_knowledge_curator()
            self.components['knowledge_curator'] = knowledge_curator
            initialization_report['knowledge_curator'] = 'success'
        except Exception as e:
            initialization_report['knowledge_curator'] = f'failed: {str(e)}'
        
        try:
            # 初始化性能优化器
            performance_optimizer = get_performance_optimizer()
            self.components['performance_optimizer'] = performance_optimizer
            initialization_report['performance_optimizer'] = 'success'
        except Exception as e:
            initialization_report['performance_optimizer'] = f'failed: {str(e)}'
        
        try:
            # 初始化迁移学习系统
            transfer_learning = get_transfer_learning_system()
            self.components['transfer_learning'] = transfer_learning
            initialization_report['transfer_learning'] = 'success'
        except Exception as e:
            initialization_report['transfer_learning'] = f'failed: {str(e)}'
        
        try:
            # 初始化强化学习器
            reinforcement_learner = get_reinforcement_learner()
            self.components['reinforcement_learner'] = reinforcement_learner
            initialization_report['reinforcement_learner'] = 'success'
        except Exception as e:
            initialization_report['reinforcement_learner'] = f'failed: {str(e)}'
        
        try:
            # 初始化课程学习
            curriculum_learning = get_curriculum_learning()
            self.components['curriculum_learning'] = curriculum_learning
            initialization_report['curriculum_learning'] = 'success'
        except Exception as e:
            initialization_report['curriculum_learning'] = f'failed: {str(e)}'
        
        try:
            # 初始化适应引擎
            adaptation_engine = get_adaptation_engine()
            self.components['adaptation_engine'] = adaptation_engine
            initialization_report['adaptation_engine'] = 'success'
        except Exception as e:
            initialization_report['adaptation_engine'] = f'failed: {str(e)}'
        
        try:
            # 初始化学习评估器
            learning_evaluator = get_learning_evaluator()
            self.components['learning_evaluator'] = learning_evaluator
            initialization_report['learning_evaluator'] = 'success'
        except Exception as e:
            initialization_report['learning_evaluator'] = f'failed: {str(e)}'
        
        # 检查初始化状态
        successful_components = [k for k, v in initialization_report.items() if v == 'success']
        if len(successful_components) > 8:  # 超过80%组件成功初始化
            self.is_initialized = True
            initialization_report['overall_status'] = 'success'
        else:
            initialization_report['overall_status'] = 'partial_success'
        
        return initialization_report
    
    def save_all_components(self) -> Dict[str, Any]:
        """保存所有学习组件的数据"""
        if not self.is_initialized:
            return {'error': '系统未初始化'}
        
        save_report = {}
        
        try:
            # 保存元学习器
            if 'meta_learner' in self.components:
                self.components['meta_learner'].save_model()
                save_report['meta_learner'] = 'success'
        except Exception as e:
            save_report['meta_learner'] = f'failed: {str(e)}'
        
        try:
            # 保存技能获取系统
            if 'skill_acquisition' in self.components:
                self.components['skill_acquisition'].save_skills()
                save_report['skill_acquisition'] = 'success'
        except Exception as e:
            save_report['skill_acquisition'] = f'failed: {str(e)}'
        
        try:
            # 保存经验回放系统
            if 'experience_replayer' in self.components:
                self.components['experience_replayer'].save_experiences()
                save_report['experience_replayer'] = 'success'
        except Exception as e:
            save_report['experience_replayer'] = f'failed: {str(e)}'
        
        try:
            # 保存模式识别器
            if 'pattern_recognizer' in self.components:
                self.components['pattern_recognizer'].save_patterns()
                save_report['pattern_recognizer'] = 'success'
        except Exception as e:
            save_report['pattern_recognizer'] = f'failed: {str(e)}'
        
        try:
            # 保存知识管理系统
            if 'knowledge_curator' in self.components:
                self.components['knowledge_curator'].save_knowledge()
                save_report['knowledge_curator'] = 'success'
        except Exception as e:
            save_report['knowledge_curator'] = f'failed: {str(e)}'
        
        try:
            # 保存性能优化器
            if 'performance_optimizer' in self.components:
                self.components['performance_optimizer'].save_optimization_config()
                save_report['performance_optimizer'] = 'success'
        except Exception as e:
            save_report['performance_optimizer'] = f'failed: {str(e)}'
        
        try:
            # 保存迁移学习系统
            if 'transfer_learning' in self.components:
                self.components['transfer_learning'].save_transfer_data()
                save_report['transfer_learning'] = 'success'
        except Exception as e:
            save_report['transfer_learning'] = f'failed: {str(e)}'
        
        try:
            # 保存强化学习器
            if 'reinforcement_learner' in self.components:
                self.components['reinforcement_learner'].save_models()
                save_report['reinforcement_learner'] = 'success'
        except Exception as e:
            save_report['reinforcement_learner'] = f'failed: {str(e)}'
        
        try:
            # 保存课程学习
            if 'curriculum_learning' in self.components:
                self.components['curriculum_learning'].save_curriculum()
                save_report['curriculum_learning'] = 'success'
        except Exception as e:
            save_report['curriculum_learning'] = f'failed: {str(e)}'
        
        try:
            # 保存适应引擎
            if 'adaptation_engine' in self.components:
                self.components['adaptation_engine'].save_adaptation_data()
                save_report['adaptation_engine'] = 'success'
        except Exception as e:
            save_report['adaptation_engine'] = f'failed: {str(e)}'
        
        try:
            # 保存学习评估器
            if 'learning_evaluator' in self.components:
                self.components['learning_evaluator'].save_evaluation_data()
                save_report['learning_evaluator'] = 'success'
        except Exception as e:
            save_report['learning_evaluator'] = f'failed: {str(e)}'
        
        return save_report
    
    def process_learning_episode(self, episode_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理学习回合"""
        if not self.is_initialized:
            return {'error': '系统未初始化'}
        
        processing_report = {}
        
        try:
            # 模式识别
            pattern_analysis = self.components['pattern_recognizer'].analyze_behavior_sequence(episode_data)
            processing_report['pattern_analysis'] = pattern_analysis
            
            # 技能获取
            if episode_data.get('contains_new_skill', False):
                skill_id = self.components['skill_acquisition'].learn_new_skill(episode_data)
                processing_report['skill_acquired'] = skill_id
            
            # 经验存储
            if 'state' in episode_data and 'action' in episode_data:
                self.components['experience_replayer'].add_experience(
                    episode_data['state'],
                    episode_data['action'],
                    episode_data.get('reward', 0.0),
                    episode_data.get('next_state', episode_data['state']),
                    episode_data.get('done', False),
                    episode_data.get('metadata', {})
                )
                processing_report['experience_stored'] = True
            
            # 知识提取
            if episode_data.get('contains_knowledge', False):
                knowledge_id = self.components['knowledge_curator'].add_knowledge(
                    episode_data.get('knowledge_data', {}),
                    source="episode_learning"
                )
                processing_report['knowledge_extracted'] = knowledge_id
            
            # 性能评估
            performance_metrics = {
                'accuracy': episode_data.get('accuracy', 0.0),
                'efficiency': episode_data.get('efficiency', 0.0),
                'learning_speed': episode_data.get('learning_speed', 0.0)
            }
            performance_analysis = self.components['performance_optimizer'].analyze_performance(
                'learning_episode', performance_metrics
            )
            processing_report['performance_analysis'] = performance_analysis
            
            processing_report['status'] = 'success'
            
        except Exception as e:
            processing_report['status'] = 'failed'
            processing_report['error'] = str(e)
        
        return processing_report
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status_report = {
            'initialized': self.is_initialized,
            'components_loaded': list(self.components.keys()),
            'coordination_config': self.coordination_config
        }
        
        if self.is_initialized:
            # 收集各组件状态
            component_status = {}
            
            # 元学习器状态
            if 'meta_learner' in self.components:
                component_status['meta_learner'] = {
                    'learning_episodes': len(self.components['meta_learner'].learning_history)
                }
            
            # 技能获取系统状态
            if 'skill_acquisition' in self.components:
                skill_overview = self.components['skill_acquisition'].get_skill_library_overview()
                component_status['skill_acquisition'] = {
                    'total_skills': skill_overview.get('total_skills', 0)
                }
            
            # 经验回放系统状态
            if 'experience_replayer' in self.components:
                exp_stats = self.components['experience_replayer'].get_statistics()
                component_status['experience_replayer'] = {
                    'total_experiences': exp_stats.get('total_unique_experiences', 0)
                }
            
            # 模式识别器状态
            if 'pattern_recognizer' in self.components:
                pattern_insights = self.components['pattern_recognizer'].get_pattern_insights()
                component_status['pattern_recognizer'] = {
                    'identified_patterns': pattern_insights.get('total_identified_patterns', 0)
                }
            
            # 知识管理系统状态
            if 'knowledge_curator' in self.components:
                knowledge_stats = self.components['knowledge_curator'].get_knowledge_statistics()
                component_status['knowledge_curator'] = {
                    'knowledge_items': knowledge_stats.get('total_knowledge_items', 0)
                }
            
            status_report['component_status'] = component_status
        
        return status_report
    
    def coordinate_cross_component_learning(self, learning_context: Dict[str, Any]) -> Dict[str, Any]:
        """协调跨组件学习"""
        if not self.is_initialized:
            return {'error': '系统未初始化'}
        
        coordination_report = {}
        
        try:
            # 元学习指导
            meta_learning_advice = self.components['meta_learner'].analyze_learning_patterns(learning_context)
            coordination_report['meta_learning_advice'] = meta_learning_advice
            
            # 课程学习推荐
            if 'user_skill_level' in learning_context:
                recommended_item = self.components['curriculum_learning'].get_recommended_item(
                    learning_context['user_skill_level']
                )
                if recommended_item:
                    coordination_report['recommended_learning_item'] = recommended_item.item_id
            
            # 迁移学习机会识别
            similar_tasks = self.components['transfer_learning'].find_similar_tasks(
                learning_context, top_k=3
            )
            if similar_tasks:
                coordination_report['transfer_opportunities'] = [
                    {'task_id': task_id, 'similarity': similarity}
                    for task_id, similarity in similar_tasks
                ]
            
            # 适应策略生成
            environment_analysis = self.components['adaptation_engine'].analyze_environment(learning_context)
            adaptation_strategy = self.components['adaptation_engine'].generate_adaptation_strategy(
                environment_analysis, learning_context.get('current_performance', 0.5)
            )
            coordination_report['adaptation_strategy'] = adaptation_strategy
            
            coordination_report['status'] = 'success'
            
        except Exception as e:
            coordination_report['status'] = 'failed'
            coordination_report['error'] = str(e)
        
        return coordination_report

# 全局学习系统协调器实例
_global_learning_coordinator: Optional[LearningSystemCoordinator] = None

def get_learning_coordinator() -> LearningSystemCoordinator:
    """获取全局学习系统协调器"""
    global _global_learning_coordinator
    if _global_learning_coordinator is None:
        _global_learning_coordinator = LearningSystemCoordinator()
    return _global_learning_coordinator

def initialize_learning_system() -> Dict[str, Any]:
    """
    初始化学习系统
    
    返回:
        dict: 各组件初始化状态
    """
    coordinator = get_learning_coordinator()
    return coordinator.initialize_all_components()

def save_learning_system() -> Dict[str, Any]:
    """
    保存学习系统数据
    
    返回:
        dict: 各组件保存状态
    """
    coordinator = get_learning_coordinator()
    return coordinator.save_all_components()

def get_learning_system_status() -> Dict[str, Any]:
    """
    获取学习系统状态
    
    返回:
        dict: 系统状态信息
    """
    coordinator = get_learning_coordinator()
    return coordinator.get_system_status()

def get_learning_system_overview() -> Dict[str, Any]:
    """
    获取学习系统概览
    
    返回:
        dict: 系统概览信息
    """
    overview = {
        'module_name': '学习与适应系统',
        'version': __version__,
        'description': __description__,
        'components': {
            'meta_learner': {
                'name': '元学习器',
                'description': '学习如何学习，优化学习策略选择',
                'capabilities': ['学习模式分析', '策略推荐', '自适应学习']
            },
            'skill_acquisition': {
                'name': '技能获取系统',
                'description': '从交互中提取和精炼可重用技能',
                'capabilities': ['技能学习', '技能迁移', '技能库管理']
            },
            'experience_replayer': {
                'name': '经验回放系统',
                'description': '重现经验以加强学习',
                'capabilities': ['优先经验回放', '情景记忆', '多级存储']
            },
            'pattern_recognizer': {
                'name': '模式识别器',
                'description': '识别用户行为模式和环境规律',
                'capabilities': ['行为分析', '模式检测', '异常识别']
            },
            'knowledge_curator': {
                'name': '知识管理系统',
                'description': '管理和优化知识库',
                'capabilities': ['知识提取', '质量评估', '知识推荐']
            },
            'performance_optimizer': {
                'name': '性能优化器',
                'description': '优化系统性能和资源使用',
                'capabilities': ['资源监控', '瓶颈识别', '自适应优化']
            },
            'transfer_learning': {
                'name': '迁移学习系统',
                'description': '跨任务和跨领域知识迁移',
                'capabilities': ['知识提取', '相似度匹配', '迁移策略']
            },
            'reinforcement_learner': {
                'name': '强化学习器',
                'description': '基于奖励信号的学习和决策',
                'capabilities': ['策略学习', '价值估计', '探索利用平衡']
            },
            'curriculum_learning': {
                'name': '课程学习系统',
                'description': '渐进式难度调整和学习路径规划',
                'capabilities': ['难度预测', '路径规划', '自适应进度']
            },
            'adaptation_engine': {
                'name': '适应引擎',
                'description': '动态适应环境变化和策略调整',
                'capabilities': ['环境分析', '策略生成', '实时适应']
            },
            'learning_evaluator': {
                'name': '学习评估器',
                'description': '评估学习效果和系统性能',
                'capabilities': ['性能评估', '进度跟踪', '改进建议']
            }
        },
        'system_capabilities': [
            '持续学习能力',
            '环境适应能力',
            '知识迁移能力',
            '性能优化能力',
            '模式识别能力',
            '策略选择能力',
            '自我评估能力',
            '跨领域学习能力'
        ],
        'technical_dependencies': [
            'torch (PyTorch) - 深度学习框架',
            'numpy - 数值计算',
            'scikit-learn - 机器学习工具',
            'networkx - 图数据处理',
            'psutil - 系统资源监控',
            'GPUtil - GPU资源管理'
        ],
        'integration_points': [
            '认知推理层 - 提供学习上下文和目标',
            '记忆管理系统 - 存储和检索学习经验',
            '交互呈现层 - 获取用户反馈和交互数据',
            '能力服务层 - 应用学到的技能和知识'
        ]
    }
    
    return overview

def create_learning_system_report(report_type: str = "comprehensive") -> Dict[str, Any]:
    """
    创建学习系统报告
    
    Args:
        report_type: 报告类型 ('comprehensive', 'summary', 'technical')
        
    Returns:
        dict: 系统报告
    """
    coordinator = get_learning_coordinator()
    
    if not coordinator.is_initialized:
        return {'error': '学习系统未初始化'}
    
    report = {
        'report_type': report_type,
        'generation_timestamp': __import__('datetime').datetime.now().isoformat(),
        'system_version': __version__
    }
    
    # 系统状态
    system_status = coordinator.get_system_status()
    report['system_status'] = system_status
    
    # 组件特定报告
    component_reports = {}
    
    if report_type in ['comprehensive', 'technical']:
        # 知识库状态
        if 'knowledge_curator' in coordinator.components:
            knowledge_stats = coordinator.components['knowledge_curator'].get_knowledge_statistics()
            component_reports['knowledge_base'] = knowledge_stats
        
        # 技能库状态
        if 'skill_acquisition' in coordinator.components:
            skill_overview = coordinator.components['skill_acquisition'].get_skill_library_overview()
            component_reports['skill_library'] = skill_overview
        
        # 学习模式分析
        if 'pattern_recognizer' in coordinator.components:
            pattern_insights = coordinator.components['pattern_recognizer'].get_pattern_insights()
            component_reports['learning_patterns'] = pattern_insights
    
    if report_type == 'comprehensive':
        # 性能分析
        if 'performance_optimizer' in coordinator.components:
            performance_report = coordinator.components['performance_optimizer'].get_performance_report()
            component_reports['performance_analysis'] = performance_report
        
        # 学习评估
        if 'learning_evaluator' in coordinator.components:
            learning_report = coordinator.components['learning_evaluator'].generate_learning_report('comprehensive')
            component_reports['learning_evaluation'] = learning_report
    
    report['component_reports'] = component_reports
    
    # 系统建议
    recommendations = []
    
    # 基于系统状态的建议
    if system_status.get('initialized', False):
        loaded_components = system_status.get('components_loaded', [])
        if len(loaded_components) < 11:  # 不是所有组件都加载
            recommendations.append({
                'priority': 'medium',
                'suggestion': f'部分组件未加载 ({len(loaded_components)}/11)，建议检查初始化日志',
                'area': '系统初始化'
            })
    else:
        recommendations.append({
            'priority': 'high',
            'suggestion': '学习系统未完全初始化，建议重新初始化',
            'area': '系统初始化'
        })
    
    report['recommendations'] = recommendations
    
    return report

# 导出协调器相关函数
__all__.extend([
    'LearningSystemCoordinator',
    'get_learning_coordinator',
    'initialize_learning_system',
    'save_learning_system',
    'get_learning_system_status',
    'get_learning_system_overview',
    'create_learning_system_report'
])

# 自动初始化检查
def _auto_initialize_if_required():
    """如果需要，自动初始化系统"""
    coordinator = get_learning_coordinator()
    if not coordinator.is_initialized:
        # 在生产环境中，可能需要更谨慎的初始化策略
        # 这里我们只是记录信息，不自动初始化
        import logging
        logger = logging.getLogger('learning_system')
        logger.info("学习系统协调器已创建，但未初始化。请调用 initialize_learning_system() 进行初始化。")

# 在模块导入时执行自动初始化检查
_auto_initialize_if_required()
