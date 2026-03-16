"""
角色系统包
包含3D角色模型管理、动画、物理和资源处理功能
"""

from .collision_detector import (
    CollisionDetector, CollisionShape, CollisionShapeType, 
    CollisionContact, CollisionResult, collision_detector
)

from .ragdoll_system import (
    RagdollSystem, RagdollBone, RagdollConstraint, 
    RagdollState, ragdoll_system
)

from .inverse_kinematics import (
    InverseKinematics, IKChain, IKSolution, 
    IKAlgorithm, inverse_kinematics
)

from .character_loader import (
    CharacterLoader, CharacterConfig, CharacterInstance,
    CharacterType, character_loader
)

from .asset_pipeline import (
    AssetPipeline, AssetImportConfig, AssetProcessingStep,
    AssetPipelineResult, AssetType, AssetFormat, asset_pipeline
)

# 导出所有公共类和函数
__all__ = [
    # 碰撞检测
    'CollisionDetector', 'CollisionShape', 'CollisionShapeType',
    'CollisionContact', 'CollisionResult', 'collision_detector',
    
    # 布娃娃系统
    'RagdollSystem', 'RagdollBone', 'RagdollConstraint',
    'RagdollState', 'ragdoll_system',
    
    # 逆向运动学
    'InverseKinematics', 'IKChain', 'IKSolution',
    'IKAlgorithm', 'inverse_kinematics',
    
    # 角色加载器
    'CharacterLoader', 'CharacterConfig', 'CharacterInstance',
    'CharacterType', 'character_loader',
    
    # 资源管道
    'AssetPipeline', 'AssetImportConfig', 'AssetProcessingStep',
    'AssetPipelineResult', 'AssetType', 'AssetFormat', 'asset_pipeline'
]

# 包版本
__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "Mirexs 3D角色系统 - 提供完整的角色管理、动画和物理功能"

# 初始化函数
def initialize_character_system():
    """
    初始化角色系统
    
    返回:
        bool: 初始化是否成功
    """
    try:
        # 这里可以添加系统初始化逻辑
        # 例如：预加载资源、建立连接等
        
        print("角色系统初始化完成")
        return True
        
    except Exception as e:
        print(f"角色系统初始化失败: {e}")
        return False

# 清理函数
def cleanup_character_system():
    """
    清理角色系统资源
    """
    try:
        collision_detector.cleanup()
        ragdoll_system.cleanup()
        inverse_kinematics.cleanup()
        character_loader.cleanup()
        asset_pipeline.cleanup()
        
        print("角色系统清理完成")
        
    except Exception as e:
        print(f"角色系统清理失败: {e}")

# 包导入时的初始化
if __name__ != "__main__":
    # 这里可以添加包导入时的自动初始化
    pass
