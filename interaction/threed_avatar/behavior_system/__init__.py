"""
行为系统模块
负责3D虚拟猫咪的行为生成、情感表达和交互管理
"""

from .emotion_engine import EmotionEngine, EmotionalState, EmotionalVector, get_emotion_engine
from .expression_control import ExpressionController, ExpressionType, FacialExpression, get_expression_controller
from .gesture_library import GestureLibrary, GestureDefinition, GestureCategory, get_gesture_library
from .gaze_system import GazeSystem, GazeTarget, GazeBehavior, GazeState, get_gaze_system
from .personality_model import PersonalityModel, PersonalityProfile, PersonalityTrait, get_personality_model
from .behavior_planner import BehaviorPlanner, BehaviorPlan, BehaviorAction, get_behavior_planner
from .state_machine import BehaviorStateMachine, BehaviorState, StatePriority, get_state_machine
from .context_awareness import ContextAwareness, SituationContext, EnvironmentType, get_context_awareness
from .behavior_metrics import BehaviorMetrics, BehaviorMetric, MetricType, get_behavior_metrics

__all__ = [
    # 情感引擎
    'EmotionEngine', 'EmotionalState', 'EmotionalVector', 'get_emotion_engine',
    
    # 表情控制
    'ExpressionController', 'ExpressionType', 'FacialExpression', 'get_expression_controller',
    
    # 手势库
    'GestureLibrary', 'GestureDefinition', 'GestureCategory', 'get_gesture_library',
    
    # 视线系统
    'GazeSystem', 'GazeTarget', 'GazeBehavior', 'GazeState', 'get_gaze_system',
    
    # 性格模型
    'PersonalityModel', 'PersonalityProfile', 'PersonalityTrait', 'get_personality_model',
    
    # 行为规划
    'BehaviorPlanner', 'BehaviorPlan', 'BehaviorAction', 'get_behavior_planner',
    
    # 状态机
    'BehaviorStateMachine', 'BehaviorState', 'StatePriority', 'get_state_machine',
    
    # 情境感知
    'ContextAwareness', 'SituationContext', 'EnvironmentType', 'get_context_awareness',
    
    # 行为指标
    'BehaviorMetrics', 'BehaviorMetric', 'MetricType', 'get_behavior_metrics'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "3D虚拟猫咪行为系统模块"

# 初始化函数
async def initialize_behavior_system(config: dict = None) -> bool:
    """
    初始化行为系统
    
    Args:
        config: 配置参数
        
    Returns:
        是否初始化成功
    """
    try:
        # 初始化各子系统
        emotion_engine = get_emotion_engine()
        await emotion_engine.initialize()
        
        # 其他系统的初始化可以在这里添加
        # ...
        
        return True
        
    except Exception as e:
        import logging
        logger = logging.getLogger("BehaviorSystem")
        logger.error(f"行为系统初始化失败: {e}")
        return False

# 全局行为系统管理器
class BehaviorSystemManager:
    """行为系统管理器"""
    
    def __init__(self):
        self.components = {}
        self.is_initialized = False
    
    async def initialize(self, config: dict = None):
        """初始化行为系统管理器"""
        if self.is_initialized:
            return
        
        try:
            # 初始化所有组件
            self.components['emotion_engine'] = get_emotion_engine()
            self.components['personality_model'] = get_personality_model()
            self.components['gesture_library'] = get_gesture_library()
            self.components['gaze_system'] = get_gaze_system()
            self.components['behavior_planner'] = get_behavior_planner()
            self.components['state_machine'] = get_state_machine()
            self.components['context_awareness'] = get_context_awareness()
            self.components['behavior_metrics'] = get_behavior_metrics()
            
            # 初始化情感引擎
            await self.components['emotion_engine'].initialize()
            
            self.is_initialized = True
            
            import logging
            logger = logging.getLogger("BehaviorSystemManager")
            logger.info("行为系统管理器初始化完成")
            
        except Exception as e:
            import logging
            logger = logging.getLogger("BehaviorSystemManager")
            logger.error(f"行为系统管理器初始化失败: {e}")
            raise
    
    def get_component(self, component_name: str):
        """获取组件实例"""
        return self.components.get(component_name)
    
    async def shutdown(self):
        """关闭行为系统"""
        # 清理资源
        self.components.clear()
        self.is_initialized = False

# 全局行为系统管理器实例
_global_behavior_manager: Optional[BehaviorSystemManager] = None

async def get_behavior_system_manager() -> BehaviorSystemManager:
    """获取全局行为系统管理器"""
    global _global_behavior_manager
    if _global_behavior_manager is None:
        _global_behavior_manager = BehaviorSystemManager()
        await _global_behavior_manager.initialize()
    return _global_behavior_manager
