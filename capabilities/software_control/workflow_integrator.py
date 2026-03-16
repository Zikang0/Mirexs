"""
工作流集成器：集成多个工作流
"""
import json
import yaml
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import networkx as nx
from pathlib import Path

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """工作流状态枚举"""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class TriggerType(Enum):
    """触发器类型枚举"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    API = "api"

@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    action_type: str
    parameters: Dict[str, Any]
    next_step_id: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    timeout: int = 30

@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str
    version: str
    steps: List[WorkflowStep]
    triggers: List[Dict[str, Any]]
    status: WorkflowStatus = WorkflowStatus.INACTIVE
    created_time: Optional[datetime] = None
    updated_time: Optional[datetime] = None
    variables: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}

class WorkflowIntegrator:
    """工作流集成器"""
    
    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}
        self.workflow_graphs: Dict[str, nx.DiGraph] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._setup_logging()
        self._load_builtin_workflows()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_builtin_workflows(self):
        """加载内置工作流"""
        # 文档处理工作流
        document_workflow = Workflow(
            id="document_processing",
            name="文档处理工作流",
            description="自动处理文档的完整工作流",
            version="1.0",
            steps=[
                WorkflowStep(
                    id="step1",
                    name="打开文档",
                    action_type="launch_application",
                    parameters={"application_name": "word", "arguments": ["/q"]}
                ),
                WorkflowStep(
                    id="step2",
                    name="等待加载",
                    action_type="wait",
                    parameters={"duration": 3}
                ),
                WorkflowStep(
                    id="step3",
                    name="处理文档",
                    action_type="execute_script",
                    parameters={"script_path": "scripts/process_document.py"}
                ),
                WorkflowStep(
                    id="step4",
                    name="保存文档",
                    action_type="keyboard_input",
                    parameters={"text": "^s", "interval": 0.1}
                )
            ],
            triggers=[{"type": "manual"}],
            created_time=datetime.now()
        )
        
        self.register_workflow(document_workflow)
    
    def register_workflow(self, workflow: Workflow) -> bool:
        """注册工作流"""
        try:
            # 验证工作流结构
            if not self._validate_workflow(workflow):
                return False
            
            # 创建工作流图
            graph = self._create_workflow_graph(workflow)
            self.workflow_graphs[workflow.id] = graph
            
            # 注册工作流
            self.workflows[workflow.id] = workflow
            
            logger.info(f"成功注册工作流: {workflow.name} (ID: {workflow.id})")
            return True
            
        except Exception as e:
            logger.error(f"注册工作流失败: {str(e)}")
            return False
    
    def _validate_workflow(self, workflow: Workflow) -> bool:
        """验证工作流结构"""
        if not workflow.id or not workflow.name:
            return False
        
        if not workflow.steps:
            return False
        
        # 检查步骤ID唯一性
        step_ids = [step.id for step in workflow.steps]
        if len(step_ids) != len(set(step_ids)):
            return False
        
        return True
    
    def _create_workflow_graph(self, workflow: Workflow) -> nx.DiGraph:
        """创建工作流图"""
        graph = nx.DiGraph()
        
        # 添加节点
        for step in workflow.steps:
            graph.add_node(step.id, step=step)
        
        # 添加边
        for step in workflow.steps:
            if step.next_step_id:
                graph.add_edge(step.id, step.next_step_id)
        
        return graph
    
    def execute_workflow(self, workflow_id: str, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """执行工作流"""
        try:
            if workflow_id not in self.workflows:
                return False, f"工作流不存在: {workflow_id}"
            
            workflow = self.workflows[workflow_id]
            graph = self.workflow_graphs[workflow_id]
            
            # 更新工作流状态
            workflow.status = WorkflowStatus.ACTIVE
            
            # 初始化执行上下文
            if context is None:
                context = {}
            
            execution_context = {
                'workflow_id': workflow_id,
                'start_time': datetime.now(),
                'steps_executed': [],
                'variables': workflow.variables.copy(),
                'results': {},
                'context': context
            }
            
            # 查找起始步骤
            start_steps = [node for node in graph.nodes() if graph.in_degree(node) == 0]
            if not start_steps:
                return False, "未找到起始步骤"
            
            # 执行工作流
            success = self._execute_workflow_steps(workflow, graph, start_steps[0], execution_context)
            
            # 更新工作流状态
            workflow.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.ERROR
            workflow.updated_time = datetime.now()
            
            # 记录执行历史
            self._record_execution_history(workflow_id, execution_context, success)
            
            if success:
                return True, f"工作流执行成功: {workflow.name}"
            else:
                return False, f"工作流执行失败: {workflow.name}"
            
        except Exception as e:
            logger.error(f"执行工作流失败 {workflow_id}: {str(e)}")
            return False, f"执行失败: {str(e)}"
    
    def _execute_workflow_steps(self, workflow: Workflow, graph: nx.DiGraph, 
                              current_step_id: str, context: Dict[str, Any]) -> bool:
        """执行工作流步骤"""
        try:
            step_node = graph.nodes[current_step_id]
            step = step_node['step']
            
            logger.info(f"执行工作流步骤: {step.name} (ID: {step.id})")
            
            # 执行步骤动作
            from .automation_engine import get_automation_engine
            automation_engine = get_automation_engine()
            
            # 创建临时任务执行单个步骤
            task_actions = [{
                'type': step.action_type,
                'params': step.parameters,
                'stop_on_failure': True
            }]
            
            task_id = automation_engine.create_task(
                name=f"Workflow_{workflow.id}_Step_{step.id}",
                description=f"工作流步骤: {step.name}",
                actions=task_actions
            )
            
            automation_engine.execute_task(task_id)
            
            # 等待任务完成
            import time
            timeout = step.timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                task_status = automation_engine.get_task_status(task_id)
                if task_status and task_status['status'] in ['completed', 'failed', 'cancelled']:
                    break
                time.sleep(0.5)
            
            # 检查执行结果
            task_status = automation_engine.get_task_status(task_id)
            if not task_status or task_status['status'] != 'completed':
                logger.error(f"工作流步骤执行失败: {step.name}")
                return False
            
            # 记录执行结果
            context['steps_executed'].append(step.id)
            context['results'][step.id] = task_status.get('result', {})
            
            # 执行下一个步骤
            next_steps = list(graph.successors(current_step_id))
            for next_step_id in next_steps:
                if not self._execute_workflow_steps(workflow, graph, next_step_id, context):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"执行工作流步骤失败 {current_step_id}: {str(e)}")
            return False
    
    def _record_execution_history(self, workflow_id: str, context: Dict[str, Any], success: bool):
        """记录执行历史"""
        execution_record = {
            'workflow_id': workflow_id,
            'execution_id': str(hash(str(context['start_time']))),
            'start_time': context['start_time'].isoformat(),
            'end_time': datetime.now().isoformat(),
            'success': success,
            'steps_executed': context['steps_executed'],
            'results': context['results']
        }
        
        self.execution_history.append(execution_record)
        
        # 只保留最近100条记录
        if len(self.execution_history) > 100:
            self.execution_history.pop(0)
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def get_all_workflows(self) -> List[Workflow]:
        """获取所有工作流"""
        return list(self.workflows.values())
    
    def export_workflow(self, workflow_id: str, file_path: str) -> bool:
        """导出工作流"""
        try:
            if workflow_id not in self.workflows:
                return False
            
            workflow = self.workflows[workflow_id]
            
            # 转换为可序列化的字典
            workflow_dict = {
                'id': workflow.id,
                'name': workflow.name,
                'description': workflow.description,
                'version': workflow.version,
                'steps': [asdict(step) for step in workflow.steps],
                'triggers': workflow.triggers,
                'variables': workflow.variables
            }
            
            file_path = Path(file_path)
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(workflow_dict, f, indent=2, ensure_ascii=False)
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(workflow_dict, f, allow_unicode=True)
            else:
                return False
            
            logger.info(f"成功导出工作流到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出工作流失败: {str(e)}")
            return False
    
    def import_workflow(self, file_path: str) -> bool:
        """导入工作流"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_dict = json.load(f)
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_dict = yaml.safe_load(f)
            else:
                return False
            
            # 转换为Workflow对象
            steps = [WorkflowStep(**step_data) for step_data in workflow_dict['steps']]
            
            workflow = Workflow(
                id=workflow_dict['id'],
                name=workflow_dict['name'],
                description=workflow_dict['description'],
                version=workflow_dict['version'],
                steps=steps,
                triggers=workflow_dict['triggers'],
                variables=workflow_dict.get('variables', {}),
                created_time=datetime.now()
            )
            
            return self.register_workflow(workflow)
            
        except Exception as e:
            logger.error(f"导入工作流失败: {str(e)}")
            return False
    
    def get_execution_history(self, workflow_id: str = None) -> List[Dict[str, Any]]:
        """获取执行历史"""
        if workflow_id:
            return [record for record in self.execution_history if record['workflow_id'] == workflow_id]
        else:
            return self.execution_history
    
    def create_workflow_from_template(self, template_name: str, parameters: Dict[str, Any]) -> Optional[Workflow]:
        """从模板创建工作流"""
        templates = {
            "document_processing": {
                "name": "文档处理工作流",
                "description": "自动处理文档的模板工作流",
                "steps": [
                    {
                        "id": "open_app",
                        "name": "打开应用程序",
                        "action_type": "launch_application",
                        "parameters": {"application_name": parameters.get("app_name", "word")}
                    },
                    {
                        "id": "process_doc",
                        "name": "处理文档",
                        "action_type": "execute_script",
                        "parameters": {"script_path": parameters.get("script_path", "")}
                    }
                ]
            },
            "data_backup": {
                "name": "数据备份工作流",
                "description": "自动数据备份工作流",
                "steps": [
                    {
                        "id": "backup_files",
                        "name": "备份文件",
                        "action_type": "file_operation",
                        "parameters": {
                            "operation": "copy",
                            "source": parameters.get("source_dir", ""),
                            "destination": parameters.get("backup_dir", "")
                        }
                    }
                ]
            }
        }
        
        if template_name not in templates:
            return None
        
        template = templates[template_name]
        import uuid
        
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=template['name'],
            description=template['description'],
            version="1.0",
            steps=[WorkflowStep(**step) for step in template['steps']],
            triggers=[{"type": "manual"}],
            created_time=datetime.now()
        )
        
        if self.register_workflow(workflow):
            return workflow
        
        return None

# 单例实例
_workflow_integrator_instance = None

def get_workflow_integrator() -> WorkflowIntegrator:
    """获取工作流集成器单例"""
    global _workflow_integrator_instance
    if _workflow_integrator_instance is None:
        _workflow_integrator_instance = WorkflowIntegrator()
    return _workflow_integrator_instance

