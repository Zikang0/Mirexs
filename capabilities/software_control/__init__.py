"""
软件控制模块
提供应用程序启动、进程管理、文件关联、自动化引擎等功能
"""

from .application_launcher import (
    ApplicationLauncher, 
    ApplicationInfo, 
    ApplicationState,
    get_application_launcher
)

from .process_manager import (
    ProcessManager,
    ProcessInfo,
    ProcessPriority,
    ProcessMonitor,
    ProcessAnalyzer,
    get_process_manager
)

from .file_association import (
    FileAssociationManager,
    FileAssociation,
    get_file_association_manager
)

from .automation_engine import (
    AutomationEngine,
    AutomationTask,
    TaskStatus,
    TaskPriority,
    get_automation_engine
)

from .workflow_integrator import (
    WorkflowIntegrator,
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    TriggerType,
    get_workflow_integrator
)

from .operation_recorder import (
    OperationRecorder,
    OperationRecord,
    OperationType,
    get_operation_recorder
)

from .macro_builder import (
    MacroBuilder,
    Macro,
    MacroAction,
    MacroType,
    get_macro_builder
)

from .ui_automation import (
    UIAutomation,
    UIElement,
    UIElementType,
    get_ui_automation
)

from .api_integration import (
    APIIntegration,
    APIEndpoint,
    APIConfig,
    APIResponse,
    APIAuthType,
    HTTPMethod,
    get_api_integration
)

from .script_executor import (
    ScriptExecutor,
    ScriptExecution,
    ScriptType,
    ExecutionStatus,
    get_script_executor
)

from .automation_validator import (
    AutomationValidator,
    ValidationRule,
    ValidationResult,
    ValidationLevel,
    ValidationStatus,
    get_automation_validator
)

__all__ = [
    # Application Launcher
    'ApplicationLauncher',
    'ApplicationInfo', 
    'ApplicationState',
    'get_application_launcher',
    
    # Process Manager
    'ProcessManager',
    'ProcessInfo',
    'ProcessPriority',
    'ProcessMonitor', 
    'ProcessAnalyzer',
    'get_process_manager',
    
    # File Association
    'FileAssociationManager',
    'FileAssociation',
    'get_file_association_manager',
    
    # Automation Engine
    'AutomationEngine', 
    'AutomationTask',
    'TaskStatus',
    'TaskPriority',
    'get_automation_engine',
    
    # Workflow Integrator
    'WorkflowIntegrator',
    'Workflow',
    'WorkflowStep', 
    'WorkflowStatus',
    'TriggerType',
    'get_workflow_integrator',
    
    # Operation Recorder
    'OperationRecorder',
    'OperationRecord',
    'OperationType',
    'get_operation_recorder',
    
    # Macro Builder
    'MacroBuilder',
    'Macro',
    'MacroAction',
    'MacroType', 
    'get_macro_builder',
    
    # UI Automation
    'UIAutomation',
    'UIElement',
    'UIElementType',
    'get_ui_automation',
    
    # API Integration
    'APIIntegration',
    'APIEndpoint',
    'APIConfig',
    'APIResponse',
    'APIAuthType',
    'HTTPMethod',
    'get_api_integration',
    
    # Script Executor
    'ScriptExecutor',
    'ScriptExecution', 
    'ScriptType',
    'ExecutionStatus',
    'get_script_executor',
    
    # Automation Validator
    'AutomationValidator',
    'ValidationRule',
    'ValidationResult',
    'ValidationLevel',
    'ValidationStatus',
    'get_automation_validator'
]

__version__ = "1.0.0"
__author__ = "Mirexs Team"
__description__ = "软件控制系统模块 - 提供完整的应用程序管理和自动化功能"

def initialize_software_control():
    """
    初始化软件控制模块
    返回所有主要组件的实例
    """
    components = {
        'application_launcher': get_application_launcher(),
        'process_manager': get_process_manager(),
        'file_association': get_file_association_manager(),
        'automation_engine': get_automation_engine(),
        'workflow_integrator': get_workflow_integrator(),
        'operation_recorder': get_operation_recorder(),
        'macro_builder': get_macro_builder(),
        'ui_automation': get_ui_automation(),
        'api_integration': get_api_integration(),
        'script_executor': get_script_executor(),
        'automation_validator': get_automation_validator()
    }
    
    # 启动必要的服务
    components['automation_engine'].start_engine()
    components['script_executor'].start_executor()
    
    return components

def shutdown_software_control():
    """
    关闭软件控制模块
    清理资源并停止服务
    """
    automation_engine = get_automation_engine()
    script_executor = get_script_executor()
    
    automation_engine.stop_engine()
    script_executor.stop_executor()
    
    logger.info("软件控制模块已关闭")
