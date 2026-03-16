"""
访问控制模块 - 提供完整的身份验证和访问控制功能

该模块实现了多层次的访问控制机制，包括：
1. 生物特征认证 (biometric_auth)
2. 多因素认证 (multi_factor_auth)  
3. 权限管理 (permission_manager)
4. 密钥管理 (key_management)
5. 身份验证器 (identity_verifier)
6. 访问日志 (access_logger)
7. 会话管理 (session_manager)
8. 基于角色的访问控制 (role_based_access)
9. 基于属性的访问控制 (attribute_based_access)
10. 访问策略管理 (access_policy)
11. 访问指标收集 (access_metrics)

该模块是Mirexs安全治理层的核心组成部分，遵循"安全内置"的设计原则，
提供企业级的安全防护能力。
"""

import logging
from typing import Dict, Any, List, Optional

# 导入所有子模块
from . import biometric_auth
from . import multi_factor_auth
from . import permission_manager
from . import key_management
from . import identity_verifier
from . import access_logger
from . import session_manager
from . import role_based_access
from . import attribute_based_access
from . import access_policy
from . import access_metrics

# 版本信息
__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "Mirexs Access Control Module - Enterprise-grade authentication and authorization"

# 导出主要类和函数
from .biometric_auth import (
    BiometricAuth,
    BiometricType,
    BiometricAuthLevel,
    BiometricAuthResult,
    get_biometric_auth
)

from .multi_factor_auth import (
    MultiFactorAuth,
    AuthFactorType,
    AuthFactorStatus,
    AuthResult,
    get_multi_factor_auth
)

from .permission_manager import (
    PermissionManager,
    Permission,
    ResourceType,
    AccessType,
    Role,
    PermissionCheckResult,
    get_permission_manager
)

from .key_management import (
    KeyManagement,
    KeyType,
    KeyAlgorithm,
    KeyStatus,
    KeyPurpose,
    KeyMetadata,
    get_key_management
)

from .identity_verifier import (
    IdentityVerifier,
    VerificationMethod,
    VerificationLevel,
    VerificationRequest,
    VerificationResult,
    get_identity_verifier
)

from .access_logger import (
    AccessLogger,
    AccessType as LogAccessType,
    AccessResult,
    AccessLogEntry,
    get_access_logger
)

from .session_manager import (
    SessionManager,
    Session,
    SessionStatus,
    SessionCreateResult,
    get_session_manager
)

from .role_based_access import (
    RoleBasedAccess,
    AccessDecision,
    AccessRequest,
    AccessDecisionResult,
    get_role_based_access
)

from .attribute_based_access import (
    AttributeBasedAccess,
    AttributeType,
    Operator,
    AttributeCondition,
    ABACPolicy,
    AttributeContext,
    get_attribute_based_access
)

from .access_policy import (
    AccessPolicy,
    PolicyType,
    PolicyEffect,
    Policy,
    get_access_policy
)

from .access_metrics import (
    AccessMetrics,
    MetricDefinition,
    MetricPoint,
    get_access_metrics
)

# 配置日志
logger = logging.getLogger(__name__)


def initialize_access_control(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    初始化整个访问控制模块
    
    该函数会初始化所有子模块，建立必要的依赖关系，
    并启动后台任务（如会话清理、指标上报等）。
    
    Args:
        config: 全局配置字典
        
    Returns:
        初始化是否成功
    """
    try:
        logger.info("正在初始化访问控制模块...")
        
        # 获取所有单例实例（自动初始化）
        bio_auth = get_biometric_auth()
        mfa = get_multi_factor_auth()
        perm_mgr = get_permission_manager()
        key_mgr = get_key_management()
        id_verifier = get_identity_verifier()
        access_log = get_access_logger()
        sess_mgr = get_session_manager()
        rbac = get_role_based_access()
        abac = get_attribute_based_access()
        policy = get_access_policy()
        metrics = get_access_metrics()
        
        # 启动后台任务
        import asyncio
        
        # 创建事件循环（如果不存在）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 启动会话清理任务
        loop.create_task(sess_mgr.start_cleanup_task())
        
        # 启动密钥轮换检查
        loop.create_task(key_mgr.start_rotation_checker())
        
        # 启动指标上报
        loop.create_task(metrics.start_reporting())
        
        # 记录审计日志
        access_log.log_security_event(
            user_id="system",
            event_type="ACCESS_CONTROL_INIT",
            severity="info",
            details={"status": "success", "version": __version__}
        )
        
        logger.info("访问控制模块初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"访问控制模块初始化失败: {str(e)}")
        
        # 尝试记录错误日志
        try:
            access_log = get_access_logger()
            access_log.log_security_event(
                user_id="system",
                event_type="ACCESS_CONTROL_INIT",
                severity="critical",
                details={"status": "failed", "error": str(e)}
            )
        except:
            pass
        
        return False


def shutdown_access_control() -> bool:
    """
    关闭访问控制模块，清理资源
    
    Returns:
        是否成功关闭
    """
    try:
        logger.info("正在关闭访问控制模块...")
        
        import asyncio
        
        # 获取所有管理器实例
        sess_mgr = get_session_manager()
        key_mgr = get_key_management()
        metrics = get_access_metrics()
        access_log = get_access_logger()
        
        # 停止后台任务
        try:
            loop = asyncio.get_event_loop()
            
            # 停止会话清理
            loop.create_task(sess_mgr.stop_cleanup_task())
            
            # 停止密钥轮换
            loop.create_task(key_mgr.stop_rotation_checker())
            
            # 停止指标上报
            loop.create_task(metrics.stop_reporting())
            
        except Exception as e:
            logger.warning(f"停止后台任务时出现异常: {str(e)}")
        
        # 记录审计日志
        access_log.log_security_event(
            user_id="system",
            event_type="ACCESS_CONTROL_SHUTDOWN",
            severity="info",
            details={"status": "success"}
        )
        
        # 保存最终指标快照
        metrics.save_snapshot()
        
        logger.info("访问控制模块已关闭")
        return True
        
    except Exception as e:
        logger.error(f"关闭访问控制模块失败: {str(e)}")
        return False


# 导出模块级别的函数
__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    '__description__',
    
    # 初始化/关闭函数
    'initialize_access_control',
    'shutdown_access_control',
    
    # 生物认证
    'BiometricAuth',
    'BiometricType',
    'BiometricAuthLevel',
    'BiometricAuthResult',
    'get_biometric_auth',
    
    # 多因素认证
    'MultiFactorAuth',
    'AuthFactorType',
    'AuthFactorStatus',
    'AuthResult',
    'get_multi_factor_auth',
    
    # 权限管理
    'PermissionManager',
    'Permission',
    'ResourceType',
    'AccessType',
    'Role',
    'PermissionCheckResult',
    'get_permission_manager',
    
    # 密钥管理
    'KeyManagement',
    'KeyType',
    'KeyAlgorithm',
    'KeyStatus',
    'KeyPurpose',
    'KeyMetadata',
    'get_key_management',
    
    # 身份验证器
    'IdentityVerifier',
    'VerificationMethod',
    'VerificationLevel',
    'VerificationRequest',
    'VerificationResult',
    'get_identity_verifier',
    
    # 访问日志
    'AccessLogger',
    'LogAccessType',
    'AccessResult',
    'AccessLogEntry',
    'get_access_logger',
    
    # 会话管理
    'SessionManager',
    'Session',
    'SessionStatus',
    'SessionCreateResult',
    'get_session_manager',
    
    # 基于角色的访问控制
    'RoleBasedAccess',
    'AccessDecision',
    'AccessRequest',
    'AccessDecisionResult',
    'get_role_based_access',
    
    # 基于属性的访问控制
    'AttributeBasedAccess',
    'AttributeType',
    'Operator',
    'AttributeCondition',
    'ABACPolicy',
    'AttributeContext',
    'get_attribute_based_access',
    
    # 访问策略
    'AccessPolicy',
    'PolicyType',
    'PolicyEffect',
    'Policy',
    'get_access_policy',
    
    # 访问指标
    'AccessMetrics',
    'MetricDefinition',
    'MetricPoint',
    'get_access_metrics',
]


# 模块级别的便捷函数
def quick_authenticate(
    user_id: str,
    password: Optional[str] = None,
    voice_data: Optional[bytes] = None,
    face_data: Optional[bytes] = None
) -> Dict[str, Any]:
    """
    快速认证函数 - 支持多种认证方式的组合
    
    Args:
        user_id: 用户ID
        password: 密码
        voice_data: 声纹数据
        face_data: 面部数据
    
    Returns:
        认证结果字典
    """
    import asyncio
    
    id_verifier = get_identity_verifier()
    
    # 确定认证方法
    if password:
        method = VerificationMethod.PASSWORD
        data = {"password": password}
    elif voice_data:
        method = VerificationMethod.BIOMETRIC_VOICE
        data = {"audio": voice_data}
    elif face_data:
        method = VerificationMethod.BIOMETRIC_FACE
        data = {"image": face_data}
    else:
        return {
            "success": False,
            "error": "No authentication data provided"
        }
    
    # 创建验证请求
    request = VerificationRequest(
        user_id=user_id,
        method=method,
        level=VerificationLevel.MEDIUM,
        data=data
    )
    
    # 执行验证
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(id_verifier.verify_identity(request))
        return {
            "success": result.success,
            "user_id": result.user_id,
            "confidence": result.confidence,
            "session_id": result.session_id,
            "token": result.token,
            "expires_at": result.expires_at,
            "failure_reason": result.failure_reason
        }
    finally:
        loop.close()


def check_user_permission(
    user_id: str,
    permission: str,
    resource: Optional[str] = None
) -> bool:
    """
    检查用户是否拥有指定权限
    
    Args:
        user_id: 用户ID
        permission: 权限字符串
        resource: 资源标识
    
    Returns:
        是否拥有权限
    """
    perm_mgr = get_permission_manager()
    
    result = perm_mgr.check_permission(
        user_id=user_id,
        permission=permission,
        resource_id=resource
    )
    
    return result.granted


def get_user_effective_permissions(user_id: str) -> List[str]:
    """
    获取用户的有效权限（包括角色继承）
    
    Args:
        user_id: 用户ID
    
    Returns:
        权限列表
    """
    rbac = get_role_based_access()
    permissions = rbac.get_user_effective_permissions(user_id)
    return list(permissions)


# 模块初始化时的日志
logger.debug(f"访问控制模块 v{__version__} 已加载")
logger.debug(f"模块描述: {__description__}")

