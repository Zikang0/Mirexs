"""
系统管理模块
提供威胁检测、安全扫描、性能监控、维护管理、存储优化、网络管理、更新管理、资源优化、健康检查、诊断工具和恢复管理等功能
"""

from .threat_detector import (
    ThreatDetector,
    ThreatDetection,
    ThreatLevel,
    ThreatType,
    get_threat_detector
)

from .security_scanner import (
    SecurityScanner,
    Vulnerability,
    VulnerabilityLevel,
    VulnerabilityType,
    get_security_scanner
)

from .performance_monitor import (
    PerformanceMonitor,
    PerformanceData,
    PerformanceAlert,
    PerformanceMetric,
    PerformanceLevel,
    get_performance_monitor
)

from .maintenance_manager import (
    MaintenanceManager,
    MaintenanceTask,
    MaintenanceTaskType,
    MaintenanceStatus,
    get_maintenance_manager
)

from .storage_optimizer import (
    StorageOptimizer,
    StorageAnalysis,
    OptimizationResult,
    StorageType,
    OptimizationType,
    get_storage_optimizer
)

from .network_manager import (
    NetworkManager,
    NetworkInterface,
    NetworkConnection,
    NetworkStatus,
    ConnectionType,
    get_network_manager
)

from .update_manager import (
    UpdateManager,
    UpdateInfo,
    UpdateProgress,
    UpdateStatus,
    UpdatePriority,
    get_update_manager
)

from .resource_optimizer import (
    ResourceOptimizer,
    ResourceUsage,
    OptimizationResult,
    ResourceType,
    OptimizationAction,
    get_resource_optimizer
)

from .health_checker import (
    HealthChecker,
    HealthCheck,
    SystemHealth,
    HealthStatus,
    HealthCategory,
    get_health_checker
)

from .diagnostic_tool import (
    DiagnosticTool,
    DiagnosticResult,
    SystemDiagnosis,
    DiagnosticLevel,
    ProblemSeverity,
    get_diagnostic_tool
)

from .recovery_manager import (
    RecoveryManager,
    RecoveryPoint,
    RecoveryOperation,
    RecoveryType,
    RecoveryStatus,
    get_recovery_manager
)

__all__ = [
    # Threat Detector
    'ThreatDetector',
    'ThreatDetection',
    'ThreatLevel',
    'ThreatType',
    'get_threat_detector',
    
    # Security Scanner
    'SecurityScanner',
    'Vulnerability',
    'VulnerabilityLevel',
    'VulnerabilityType',
    'get_security_scanner',
    
    # Performance Monitor
    'PerformanceMonitor',
    'PerformanceData',
    'PerformanceAlert',
    'PerformanceMetric',
    'PerformanceLevel',
    'get_performance_monitor',
    
    # Maintenance Manager
    'MaintenanceManager',
    'MaintenanceTask',
    'MaintenanceTaskType',
    'MaintenanceStatus',
    'get_maintenance_manager',
    
    # Storage Optimizer
    'StorageOptimizer',
    'StorageAnalysis',
    'OptimizationResult',
    'StorageType',
    'OptimizationType',
    'get_storage_optimizer',
    
    # Network Manager
    'NetworkManager',
    'NetworkInterface',
    'NetworkConnection',
    'NetworkStatus',
    'ConnectionType',
    'get_network_manager',
    
    # Update Manager
    'UpdateManager',
    'UpdateInfo',
    'UpdateProgress',
    'UpdateStatus',
    'UpdatePriority',
    'get_update_manager',
    
    # Resource Optimizer
    'ResourceOptimizer',
    'ResourceUsage',
    'OptimizationResult',
    'ResourceType',
    'OptimizationAction',
    'get_resource_optimizer',
    
    # Health Checker
    'HealthChecker',
    'HealthCheck',
    'SystemHealth',
    'HealthStatus',
    'HealthCategory',
    'get_health_checker',
    
    # Diagnostic Tool
    'DiagnosticTool',
    'DiagnosticResult',
    'SystemDiagnosis',
    'DiagnosticLevel',
    'ProblemSeverity',
    'get_diagnostic_tool',
    
    # Recovery Manager
    'RecoveryManager',
    'RecoveryPoint',
    'RecoveryOperation',
    'RecoveryType',
    'RecoveryStatus',
    'get_recovery_manager'
]

__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "系统管理模块 - 提供完整的系统监控、安全、维护和恢复功能"

def initialize_system_management():
    """
    初始化系统管理模块
    返回所有主要组件的实例
    """
    components = {
        'threat_detector': get_threat_detector(),
        'security_scanner': get_security_scanner(),
        'performance_monitor': get_performance_monitor(),
        'maintenance_manager': get_maintenance_manager(),
        'storage_optimizer': get_storage_optimizer(),
        'network_manager': get_network_manager(),
        'update_manager': get_update_manager(),
        'resource_optimizer': get_resource_optimizer(),
        'health_checker': get_health_checker(),
        'diagnostic_tool': get_diagnostic_tool(),
        'recovery_manager': get_recovery_manager()
    }
    
    # 启动必要的服务
    components['performance_monitor'].start_monitoring()
    components['health_checker'].start_health_monitoring()
    
    logger.info("系统管理模块初始化完成")
    return components

def shutdown_system_management():
    """
    关闭系统管理模块
    清理资源并停止服务
    """
    performance_monitor = get_performance_monitor()
    health_checker = get_health_checker()
    threat_detector = get_threat_detector()
    
    performance_monitor.stop_monitoring()
    health_checker.stop_health_monitoring()
    threat_detector.stop_monitoring()
    
    logger.info("系统管理模块已关闭")
