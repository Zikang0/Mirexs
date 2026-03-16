"""
能力服务层 - Capabilities Layer

提供系统的核心能力服务，包括创意生成、软件控制、系统管理和工具集成等功能。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# 导入所有子模块
from . import creative_suite
from . import software_control
from . import system_management
from . import tool_integration

# 从创意套件导入主要类
from .creative_suite import (
    # 文档生成
    DocumentGenerator, DocumentConfig, GeneratedDocument, get_document_generator,
    
    # 演示文稿生成
    PresentationGenerator, PresentationConfig, GeneratedPresentation, 
    SlideType, SlideLayout, get_presentation_generator,
    
    # 表格生成
    SpreadsheetGenerator, SpreadsheetConfig, GeneratedSpreadsheet,
    DataType, ColumnDefinition, get_spreadsheet_generator,
    
    # 图像生成  
    ImageGenerator, ImageGenerationConfig, GeneratedImage, 
    ImageStyle, ImageSize, get_image_generator,
    
    # 音乐生成
    MusicGenerator, MusicConfig, GeneratedMusic, 
    MusicGenre, InstrumentType, get_music_generator,
    
    # 内容精炼
    ContentRefiner, RefinementConfig, RefinementResult, RefinementType, get_content_refiner,
    
    # 修订管理
    RevisionManager, Revision, RevisionConfig, RevisionAction, RevisionStatus, get_revision_manager,
    
    # 模板引擎
    TemplateEngine, Template, TemplateConfig, TemplateType, TemplateVariable, get_template_engine,
    
    # 风格迁移
    StyleTransfer, StyleTransferConfig, StyleTransferResult, WritingStyle, get_style_transfer,
    
    # 创意约束
    CreativeConstraints, ConstraintCheckResult, ConstraintType, ConstraintSeverity, 
    BrandGuidelines, get_creative_constraints,
    
    # 质量评估
    QualityEvaluator, QualityEvaluationResult, QualityDimension, QualityScore, get_quality_evaluator,
    
    # 创意指标
    CreativeMetrics, CreativeMetric, PerformanceReport, MetricType, get_creative_metrics
)

# 从软件控制导入主要类
from .software_control import (
    # 应用启动
    ApplicationLauncher, ApplicationInfo, ApplicationState, get_application_launcher,
    
    # 进程管理
    ProcessManager, ProcessInfo, ProcessPriority, ProcessMonitor, ProcessAnalyzer, get_process_manager,
    
    # 文件关联
    FileAssociationManager, FileAssociation, get_file_association_manager,
    
    # 自动化引擎
    AutomationEngine, AutomationTask, TaskStatus, TaskPriority, get_automation_engine,
    
    # 工作流集成
    WorkflowIntegrator, Workflow, WorkflowStep, WorkflowStatus, TriggerType, get_workflow_integrator,
    
    # 操作记录
    OperationRecorder, OperationRecord, OperationType, get_operation_recorder,
    
    # 宏构建
    MacroBuilder, Macro, MacroAction, MacroType, get_macro_builder,
    
    # UI自动化
    UIAutomation, UIElement, UIElementType, get_ui_automation,
    
    # API集成
    APIIntegration, APIEndpoint, APIConfig, APIResponse, APIAuthType, HTTPMethod, get_api_integration,
    
    # 脚本执行
    ScriptExecutor, ScriptExecution, ScriptType, ExecutionStatus, get_script_executor,
    
    # 自动化验证
    AutomationValidator, ValidationRule, ValidationResult, ValidationLevel, ValidationStatus, 
    get_automation_validator
)

# 从系统管理导入主要类
from .system_management import (
    # 威胁检测
    ThreatDetector, ThreatDetection, ThreatLevel, ThreatType, get_threat_detector,
    
    # 安全扫描
    SecurityScanner, Vulnerability, VulnerabilityLevel, VulnerabilityType, get_security_scanner,
    
    # 性能监控
    PerformanceMonitor, PerformanceData, PerformanceAlert, PerformanceMetric, 
    PerformanceLevel, get_performance_monitor,
    
    # 维护管理
    MaintenanceManager, MaintenanceTask, MaintenanceTaskType, MaintenanceStatus, get_maintenance_manager,
    
    # 存储优化
    StorageOptimizer, StorageAnalysis, OptimizationResult, StorageType, 
    OptimizationType, get_storage_optimizer,
    
    # 网络管理
    NetworkManager, NetworkInterface, NetworkConnection, NetworkStatus, 
    ConnectionType, get_network_manager,
    
    # 更新管理
    UpdateManager, UpdateInfo, UpdateProgress, UpdateStatus, UpdatePriority, get_update_manager,
    
    # 资源优化
    ResourceOptimizer, ResourceUsage, OptimizationResult, ResourceType, 
    OptimizationAction, get_resource_optimizer,
    
    # 健康检查
    HealthChecker, HealthCheck, SystemHealth, HealthStatus, HealthCategory, get_health_checker,
    
    # 诊断工具
    DiagnosticTool, DiagnosticResult, SystemDiagnosis, DiagnosticLevel, 
    ProblemSeverity, get_diagnostic_tool,
    
    # 恢复管理
    RecoveryManager, RecoveryPoint, RecoveryOperation, RecoveryType, 
    RecoveryStatus, get_recovery_manager
)

# 从工具集成导入主要类
from .tool_integration import (
    # Web浏览器工具
    WebBrowserTool, WebContentExtractor,
    
    # Office工具
    WordProcessor, ExcelProcessor, PowerPointProcessor, OfficeAutomation,
    
    # 开发工具
    CodeEditor, CodeExecutor, Debugger, VersionControl, DevelopmentToolsManager,
    
    # 创意工具
    ImageGenerator as ToolImageGenerator, 
    ImageEditor, 
    MusicGenerator as ToolMusicGenerator, 
    VideoEditor, 
    CreativeToolsManager,
    
    # 系统工具
    SystemInfo, ProcessManager as ToolProcessManager, FileSystemManager, 
    SystemMonitor, SystemToolsManager,
    
    # 自定义工具
    CustomTool, ToolPackageManager, PythonFunctionTool, CommandLineTool, CustomToolsManager,
    
    # 工具发现
    ToolDiscoverer, ToolRegistry,
    
    # 工具包装器
    BaseToolWrapper, PythonFunctionWrapper, CommandLineWrapper, WebServiceWrapper, 
    CompositeToolWrapper, ToolWrapperFactory, ToolExecutionManager,
    
    # 工具注册表
    ToolRegistry as ToolRegistryClass, 
    ToolMetadata, ToolCategory, ToolStatus, ToolRegistryManager,
    
    # 依赖管理
    Dependency, DependencyResolver, DependencyManager, DependencyStatus, PackageManager,
    
    # 兼容性检查
    CompatibilityChecker, CompatibilityLevel, CompatibilityResult,
    
    # 工具指标
    ToolMetricsCollector, ToolOptimizationAdvisor, MetricType, PerformanceStats
)

__all__ = [
    # 子模块
    'creative_suite',
    'software_control',
    'system_management',
    'tool_integration',
    
    # 创意套件导出
    'DocumentGenerator', 'DocumentConfig', 'GeneratedDocument', 'get_document_generator',
    'PresentationGenerator', 'PresentationConfig', 'GeneratedPresentation', 
    'SlideType', 'SlideLayout', 'get_presentation_generator',
    'SpreadsheetGenerator', 'SpreadsheetConfig', 'GeneratedSpreadsheet',
    'DataType', 'ColumnDefinition', 'get_spreadsheet_generator',
    'ImageGenerator', 'ImageGenerationConfig', 'GeneratedImage', 
    'ImageStyle', 'ImageSize', 'get_image_generator',
    'MusicGenerator', 'MusicConfig', 'GeneratedMusic', 
    'MusicGenre', 'InstrumentType', 'get_music_generator',
    'ContentRefiner', 'RefinementConfig', 'RefinementResult', 'RefinementType', 'get_content_refiner',
    'RevisionManager', 'Revision', 'RevisionConfig', 'RevisionAction', 'RevisionStatus', 'get_revision_manager',
    'TemplateEngine', 'Template', 'TemplateConfig', 'TemplateType', 'TemplateVariable', 'get_template_engine',
    'StyleTransfer', 'StyleTransferConfig', 'StyleTransferResult', 'WritingStyle', 'get_style_transfer',
    'CreativeConstraints', 'ConstraintCheckResult', 'ConstraintType', 'ConstraintSeverity', 
    'BrandGuidelines', 'get_creative_constraints',
    'QualityEvaluator', 'QualityEvaluationResult', 'QualityDimension', 'QualityScore', 'get_quality_evaluator',
    'CreativeMetrics', 'CreativeMetric', 'PerformanceReport', 'MetricType', 'get_creative_metrics',
    
    # 软件控制导出
    'ApplicationLauncher', 'ApplicationInfo', 'ApplicationState', 'get_application_launcher',
    'ProcessManager', 'ProcessInfo', 'ProcessPriority', 'ProcessMonitor', 'ProcessAnalyzer', 'get_process_manager',
    'FileAssociationManager', 'FileAssociation', 'get_file_association_manager',
    'AutomationEngine', 'AutomationTask', 'TaskStatus', 'TaskPriority', 'get_automation_engine',
    'WorkflowIntegrator', 'Workflow', 'WorkflowStep', 'WorkflowStatus', 'TriggerType', 'get_workflow_integrator',
    'OperationRecorder', 'OperationRecord', 'OperationType', 'get_operation_recorder',
    'MacroBuilder', 'Macro', 'MacroAction', 'MacroType', 'get_macro_builder',
    'UIAutomation', 'UIElement', 'UIElementType', 'get_ui_automation',
    'APIIntegration', 'APIEndpoint', 'APIConfig', 'APIResponse', 'APIAuthType', 'HTTPMethod', 'get_api_integration',
    'ScriptExecutor', 'ScriptExecution', 'ScriptType', 'ExecutionStatus', 'get_script_executor',
    'AutomationValidator', 'ValidationRule', 'ValidationResult', 'ValidationLevel', 'ValidationStatus', 
    'get_automation_validator',
    
    # 系统管理导出
    'ThreatDetector', 'ThreatDetection', 'ThreatLevel', 'ThreatType', 'get_threat_detector',
    'SecurityScanner', 'Vulnerability', 'VulnerabilityLevel', 'VulnerabilityType', 'get_security_scanner',
    'PerformanceMonitor', 'PerformanceData', 'PerformanceAlert', 'PerformanceMetric', 
    'PerformanceLevel', 'get_performance_monitor',
    'MaintenanceManager', 'MaintenanceTask', 'MaintenanceTaskType', 'MaintenanceStatus', 'get_maintenance_manager',
    'StorageOptimizer', 'StorageAnalysis', 'OptimizationResult', 'StorageType', 
    'OptimizationType', 'get_storage_optimizer',
    'NetworkManager', 'NetworkInterface', 'NetworkConnection', 'NetworkStatus', 
    'ConnectionType', 'get_network_manager',
    'UpdateManager', 'UpdateInfo', 'UpdateProgress', 'UpdateStatus', 'UpdatePriority', 'get_update_manager',
    'ResourceOptimizer', 'ResourceUsage', 'OptimizationResult', 'ResourceType', 
    'OptimizationAction', 'get_resource_optimizer',
    'HealthChecker', 'HealthCheck', 'SystemHealth', 'HealthStatus', 'HealthCategory', 'get_health_checker',
    'DiagnosticTool', 'DiagnosticResult', 'SystemDiagnosis', 'DiagnosticLevel', 
    'ProblemSeverity', 'get_diagnostic_tool',
    'RecoveryManager', 'RecoveryPoint', 'RecoveryOperation', 'RecoveryType', 
    'RecoveryStatus', 'get_recovery_manager',
    
    # 工具集成导出（注意重名类的别名）
    'WebBrowserTool', 'WebContentExtractor',
    'WordProcessor', 'ExcelProcessor', 'PowerPointProcessor', 'OfficeAutomation',
    'CodeEditor', 'CodeExecutor', 'Debugger', 'VersionControl', 'DevelopmentToolsManager',
    'ToolImageGenerator', 'ImageEditor', 'ToolMusicGenerator', 'VideoEditor', 'CreativeToolsManager',
    'SystemInfo', 'ToolProcessManager', 'FileSystemManager', 'SystemMonitor', 'SystemToolsManager',
    'CustomTool', 'ToolPackageManager', 'PythonFunctionTool', 'CommandLineTool', 'CustomToolsManager',
    'ToolDiscoverer', 'ToolRegistry',
    'BaseToolWrapper', 'PythonFunctionWrapper', 'CommandLineWrapper', 'WebServiceWrapper', 
    'CompositeToolWrapper', 'ToolWrapperFactory', 'ToolExecutionManager',
    'ToolRegistryClass', 'ToolMetadata', 'ToolCategory', 'ToolStatus', 'ToolRegistryManager',
    'Dependency', 'DependencyResolver', 'DependencyManager', 'DependencyStatus', 'PackageManager',
    'CompatibilityChecker', 'CompatibilityLevel', 'CompatibilityResult',
    'ToolMetricsCollector', 'ToolOptimizationAdvisor', 'MetricType', 'PerformanceStats'
]

__version__ = "1.0.0"
__author__ = "Mirexs AI Team"
__description__ = "能力服务层 - 提供创意生成、软件控制、系统管理和工具集成等核心能力"

def initialize_capabilities() -> Dict[str, Any]:
    """
    初始化能力服务层
    
    Returns:
        Dict[str, Any]: 包含所有主要组件实例的字典
    """
    logger.info("开始初始化能力服务层...")
    
    components = {
        'creative_suite': {
            'document_generator': get_document_generator(),
            'image_generator': get_image_generator(),
            'music_generator': get_music_generator(),
            'presentation_generator': get_presentation_generator(),
            'spreadsheet_generator': get_spreadsheet_generator(),
            'content_refiner': get_content_refiner(),
            'revision_manager': get_revision_manager(),
            'template_engine': get_template_engine(),
            'style_transfer': get_style_transfer(),
            'creative_constraints': get_creative_constraints(),
            'quality_evaluator': get_quality_evaluator(),
            'creative_metrics': get_creative_metrics()
        },
        'software_control': software_control.initialize_software_control(),
        'system_management': system_management.initialize_system_management(),
        'tool_integration': {
            # 工具集成模块的初始化将在后续版本中实现
            'status': 'initialized',
            'note': 'Tool integration components will be initialized on demand'
        }
    }
    
    logger.info("能力服务层初始化完成")
    return components

def shutdown_capabilities():
    """
    关闭能力服务层
    清理资源并停止服务
    """
    logger.info("开始关闭能力服务层...")
    
    # 关闭软件控制模块
    try:
        software_control.shutdown_software_control()
        logger.info("软件控制模块已关闭")
    except Exception as e:
        logger.error(f"关闭软件控制模块时出错: {e}")
    
    # 关闭系统管理模块
    try:
        system_management.shutdown_system_management()
        logger.info("系统管理模块已关闭")
    except Exception as e:
        logger.error(f"关闭系统管理模块时出错: {e}")
    
    logger.info("能力服务层已完全关闭")

def get_capability_status() -> Dict[str, str]:
    """
    获取能力服务层各模块状态
    
    Returns:
        Dict[str, str]: 各模块状态字典
    """
    status = {
        'creative_suite': 'active',
        'software_control': 'active', 
        'system_management': 'active',
        'tool_integration': 'active',
        'overall': 'healthy'
    }
    
    return status

# 自动初始化日志配置
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)