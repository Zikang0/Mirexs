"""
程序记忆模块：存储技能和执行流程
实现基于工作流的程序记忆系统
"""

import uuid
import json
import datetime
from typing import List, Dict, Any, Optional, Callable
import yaml
from enum import Enum
import logging

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ActionType(Enum):
    SYSTEM_CALL = "system_call"
    API_CALL = "api_call"
    TOOL_USE = "tool_use"
    DECISION = "decision"
    LOOP = "loop"
    USER_INPUT = "user_input"

class ProceduralMemory:
    """程序记忆系统 - 存储技能和执行流程"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.skills_db = {}
        self.workflows_db = {}
        self.execution_history = {}
        
        # 注册的动作处理器
        self.action_handlers = {}
        self._register_default_handlers()
        
        self.initialized = True
        self.logger.info("程序记忆系统初始化成功")
    
    def _register_default_handlers(self):
        """注册默认的动作处理器"""
        self.action_handlers[ActionType.SYSTEM_CALL] = self._handle_system_call
        self.action_handlers[ActionType.API_CALL] = self._handle_api_call
        self.action_handlers[ActionType.TOOL_USE] = self._handle_tool_use
        self.action_handlers[ActionType.DECISION] = self._handle_decision
        self.action_handlers[ActionType.LOOP] = self._handle_loop
        self.action_handlers[ActionType.USER_INPUT] = self._handle_user_input
    
    def register_skill(self,
                      skill_name: str,
                      description: str,
                      parameters: List[Dict[str, Any]],
                      workflow_definition: Dict[str, Any],
                      category: str = "general",
                      success_rate: float = 1.0,
                      average_duration: float = 0.0) -> str:
        """
        注册新技能
        
        Args:
            skill_name: 技能名称
            description: 技能描述
            parameters: 参数定义
            workflow_definition: 工作流定义
            category: 技能类别
            success_rate: 成功率
            average_duration: 平均执行时间
            
        Returns:
            技能ID
        """
        skill_id = str(uuid.uuid4())
        
        skill_data = {
            "id": skill_id,
            "name": skill_name,
            "description": description,
            "parameters": parameters,
            "workflow": workflow_definition,
            "category": category,
            "success_rate": success_rate,
            "average_duration": average_duration,
            "created_at": datetime.datetime.now().isoformat(),
            "execution_count": 0,
            "last_executed": None
        }
        
        self.skills_db[skill_id] = skill_data
        self.logger.info(f"技能注册成功: {skill_name} ({skill_id})")
        
        return skill_id
    
    def execute_skill(self,
                     skill_identifier: str,
                     parameters: Dict[str, Any] = None,
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_identifier: 技能ID或名称
            parameters: 执行参数
            context: 执行上下文
            
        Returns:
            执行结果
        """
        # 查找技能
        skill = self._find_skill(skill_identifier)
        if not skill:
            return {"success": False, "error": f"技能未找到: {skill_identifier}"}
        
        execution_id = str(uuid.uuid4())
        parameters = parameters or {}
        context = context or {}
        
        # 验证参数
        validation_result = self._validate_parameters(skill['parameters'], parameters)
        if not validation_result['valid']:
            return {"success": False, "error": f"参数验证失败: {validation_result['errors']}"}
        
        # 创建执行记录
        execution_record = {
            "id": execution_id,
            "skill_id": skill['id'],
            "skill_name": skill['name'],
            "parameters": parameters,
            "context": context,
            "start_time": datetime.datetime.now().isoformat(),
            "status": "running",
            "steps": [],
            "results": {}
        }
        
        self.execution_history[execution_id] = execution_record
        
        try:
            # 执行工作流
            workflow_result = self._execute_workflow(
                skill['workflow'], 
                parameters, 
                context,
                execution_id
            )
            
            # 更新执行记录
            execution_record['end_time'] = datetime.datetime.now().isoformat()
            execution_record['status'] = "completed" if workflow_result['success'] else "failed"
            execution_record['results'] = workflow_result.get('results', {})
            
            # 更新技能统计
            self._update_skill_stats(skill['id'], workflow_result['success'])
            
            return {
                "success": workflow_result['success'],
                "execution_id": execution_id,
                "results": workflow_result.get('results', {}),
                "duration": workflow_result.get('duration', 0),
                "steps_executed": len(workflow_result.get('executed_steps', []))
            }
            
        except Exception as e:
            self.logger.error(f"技能执行失败: {e}")
            execution_record['end_time'] = datetime.datetime.now().isoformat()
            execution_record['status'] = 'failed'
            execution_record['error'] = str(e)
            
            return {"success": False, "error": str(e), "execution_id": execution_id}
    
    def _find_skill(self, skill_identifier: str) -> Optional[Dict[str, Any]]:
        """查找技能"""
        # 按ID查找
        if skill_identifier in self.skills_db:
            return self.skills_db[skill_identifier]
        
        # 按名称查找
        for skill in self.skills_db.values():
            if skill['name'] == skill_identifier:
                return skill
        
        return None
    
    def _validate_parameters(self, 
                           parameter_definitions: List[Dict[str, Any]], 
                           provided_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        errors = []
        
        for param_def in parameter_definitions:
            param_name = param_def['name']
            param_required = param_def.get('required', True)
            param_type = param_def.get('type', 'string')
            
            if param_name not in provided_parameters:
                if param_required:
                    errors.append(f"缺少必需参数: {param_name}")
                continue
            
            value = provided_parameters[param_name]
            
            # 类型检查
            if param_type == 'string' and not isinstance(value, str):
                errors.append(f"参数 {param_name} 应该是字符串类型")
            elif param_type == 'number' and not isinstance(value, (int, float)):
                errors.append(f"参数 {param_name} 应该是数字类型")
            elif param_type == 'boolean' and not isinstance(value, bool):
                errors.append(f"参数 {param_name} 应该是布尔类型")
            elif param_type == 'array' and not isinstance(value, list):
                errors.append(f"参数 {param_name} 应该是数组类型")
            elif param_type == 'object' and not isinstance(value, dict):
                errors.append(f"参数 {param_name} 应该是对象类型")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def _execute_workflow(self,
                         workflow: Dict[str, Any],
                         parameters: Dict[str, Any],
                         context: Dict[str, Any],
                         execution_id: str) -> Dict[str, Any]:
        """执行工作流"""
        start_time = datetime.datetime.now()
        executed_steps = []
        results = {}
        
        try:
            steps = workflow.get('steps', [])
            current_context = {**context, **parameters}
            
            for step_index, step_def in enumerate(steps):
                step_id = step_def.get('id', f"step_{step_index}")
                step_name = step_def.get('name', f"Step {step_index}")
                action_type = ActionType(step_def.get('action_type', 'tool_use'))
                
                # 创建步骤记录
                step_record = {
                    "id": step_id,
                    "name": step_name,
                    "action_type": action_type.value,
                    "start_time": datetime.datetime.now().isoformat(),
                    "status": StepStatus.RUNNING.value,
                    "input": current_context
                }
                
                # 执行步骤
                handler = self.action_handlers.get(action_type)
                if not handler:
                    step_record['status'] = StepStatus.FAILED.value
                    step_record['error'] = f"未知的动作类型: {action_type}"
                    executed_steps.append(step_record)
                    raise RuntimeError(step_record['error'])
                
                try:
                    step_result = handler(step_def, current_context)
                    step_record['end_time'] = datetime.datetime.now().isoformat()
                    step_record['status'] = StepStatus.COMPLETED.value
                    step_record['output'] = step_result
                    
                    # 更新上下文
                    if step_result.get('success', False):
                        current_context.update(step_result.get('context_updates', {}))
                        results[step_id] = step_result.get('result')
                    else:
                        step_record['status'] = StepStatus.FAILED.value
                        step_record['error'] = step_result.get('error', '步骤执行失败')
                        executed_steps.append(step_record)
                        raise RuntimeError(step_record['error'])
                    
                except Exception as e:
                    step_record['end_time'] = datetime.datetime.now().isoformat()
                    step_record['status'] = StepStatus.FAILED.value
                    step_record['error'] = str(e)
                    executed_steps.append(step_record)
                    raise
                
                executed_steps.append(step_record)
            
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "duration": duration,
                "executed_steps": executed_steps,
                "results": results
            }
            
        except Exception as e:
            duration = (datetime.datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "duration": duration,
                "executed_steps": executed_steps,
                "error": str(e)
            }
    
    def _handle_system_call(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理系统调用动作"""
        command = self._resolve_template(step_def.get('command', ''), context)
        
        # 在实际系统中，这里会执行系统命令
        # 这里使用模拟实现
        self.logger.info(f"执行系统命令: {command}")
        
        # 模拟执行结果
        return {
            "success": True,
            "result": f"命令执行成功: {command}",
            "context_updates": {
                f"{step_def.get('id')}_result": "success"
            }
        }
    
    def _handle_api_call(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理API调用动作"""
        url = self._resolve_template(step_def.get('url', ''), context)
        method = step_def.get('method', 'GET')
        
        self.logger.info(f"调用API: {method} {url}")
        
        # 模拟API调用结果
        return {
            "success": True,
            "result": {"status": "success", "data": "模拟API响应"},
            "context_updates": {
                f"{step_def.get('id')}_response": {"status": "success", "data": "模拟API响应"}
            }
        }
    
    def _handle_tool_use(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具使用动作"""
        tool_name = step_def.get('tool_name', '')
        tool_params = step_def.get('parameters', {})
        
        # 解析参数模板
        resolved_params = {}
        for key, value in tool_params.items():
            if isinstance(value, str):
                resolved_params[key] = self._resolve_template(value, context)
            else:
                resolved_params[key] = value
        
        self.logger.info(f"使用工具: {tool_name} 参数: {resolved_params}")
        
        # 模拟工具调用结果
        return {
            "success": True,
            "result": f"工具 {tool_name} 执行成功",
            "context_updates": {
                f"{step_def.get('id')}_result": f"工具 {tool_name} 执行成功"
            }
        }
    
    def _handle_decision(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理决策动作"""
        condition = self._resolve_template(step_def.get('condition', ''), context)
        
        # 简化的条件评估
        try:
            # 在实际系统中，这里会使用更复杂的条件解析
            condition_result = eval(condition, {}, context)
        except Exception as e:
            return {
                "success": False,
                "error": f"条件评估失败: {e}"
            }
        
        next_step = step_def.get('true_branch' if condition_result else 'false_branch')
        
        return {
            "success": True,
            "result": condition_result,
            "context_updates": {
                "decision_result": condition_result,
                "next_step": next_step
            }
        }
    
    def _handle_loop(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理循环动作"""
        collection = context.get(step_def.get('collection', ''), [])
        max_iterations = step_def.get('max_iterations', 100)
        
        results = []
        for i, item in enumerate(collection[:max_iterations]):
            loop_context = {**context, 'loop_item': item, 'loop_index': i}
            
            # 执行循环体内的步骤
            loop_steps = step_def.get('steps', [])
            for loop_step in loop_steps:
                action_type = ActionType(loop_step.get('action_type', 'tool_use'))
                handler = self.action_handlers.get(action_type)
                if handler:
                    result = handler(loop_step, loop_context)
                    if not result.get('success', False):
                        return result
                    loop_context.update(result.get('context_updates', {}))
            
            results.append(loop_context.get('loop_result'))
        
        return {
            "success": True,
            "result": results,
            "context_updates": {
                "loop_results": results
            }
        }
    
    def _handle_user_input(self, step_def: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户输入动作"""
        prompt = self._resolve_template(step_def.get('prompt', ''), context)
        
        self.logger.info(f"请求用户输入: {prompt}")
        
        # 在实际系统中，这里会等待用户输入
        # 这里使用模拟输入
        simulated_input = f"模拟用户对 '{prompt}' 的响应"
        
        return {
            "success": True,
            "result": simulated_input,
            "context_updates": {
                "user_input": simulated_input
            }
        }
    
    def _resolve_template(self, template: str, context: Dict[str, Any]) -> str:
        """解析模板字符串"""
        try:
            return template.format(**context)
        except KeyError as e:
            self.logger.warning(f"模板解析缺少变量: {e}")
            return template
        except Exception as e:
            self.logger.error(f"模板解析失败: {e}")
            return template
    
    def _update_skill_stats(self, skill_id: str, success: bool):
        """更新技能统计信息"""
        if skill_id in self.skills_db:
            skill = self.skills_db[skill_id]
            skill['execution_count'] = skill.get('execution_count', 0) + 1
            skill['last_executed'] = datetime.datetime.now().isoformat()
            
            # 更新成功率
            current_rate = skill.get('success_rate', 1.0)
            total_executions = skill['execution_count']
            new_rate = ((current_rate * (total_executions - 1)) + (1 if success else 0)) / total_executions
            skill['success_rate'] = new_rate
    
    def get_skill(self, skill_identifier: str) -> Optional[Dict[str, Any]]:
        """获取技能详情"""
        return self._find_skill(skill_identifier)
    
    def list_skills(self, category: str = None) -> List[Dict[str, Any]]:
        """列出技能"""
        skills = list(self.skills_db.values())
        if category:
            skills = [s for s in skills if s.get('category') == category]
        return skills
    
    def get_execution_history(self, 
                            skill_identifier: str = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """获取执行历史"""
        executions = list(self.execution_history.values())
        
        if skill_identifier:
            skill = self._find_skill(skill_identifier)
            if skill:
                executions = [e for e in executions if e.get('skill_id') == skill['id']]
        
        # 按开始时间排序
        executions.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        return executions[:limit]
    
    def export_skill(self, skill_identifier: str) -> Dict[str, Any]:
        """导出技能定义"""
        skill = self._find_skill(skill_identifier)
        if not skill:
            return {"error": "技能未找到"}
        
        return {
            "skill_definition": skill,
            "export_format": "yaml",
            "exported_at": datetime.datetime.now().isoformat()
        }
    
    def import_skill(self, skill_definition: Dict[str, Any]) -> str:
        """导入技能定义"""
        try:
            skill_id = self.register_skill(
                skill_name=skill_definition['name'],
                description=skill_definition['description'],
                parameters=skill_definition['parameters'],
                workflow_definition=skill_definition['workflow'],
                category=skill_definition.get('category', 'general'),
                success_rate=skill_definition.get('success_rate', 1.0),
                average_duration=skill_definition.get('average_duration', 0.0)
            )
            return skill_id
        except Exception as e:
            self.logger.error(f"技能导入失败: {e}")
            raise
    
    def get_procedural_stats(self) -> Dict[str, Any]:
        """获取程序记忆统计信息"""
        total_skills = len(self.skills_db)
        total_executions = len(self.execution_history)
        
        # 按类别统计
        categories = {}
        for skill in self.skills_db.values():
            category = skill.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        # 成功率统计
        successful_executions = sum(
            1 for e in self.execution_history.values() 
            if e.get('status') == 'completed'
        )
        overall_success_rate = successful_executions / total_executions if total_executions > 0 else 0
        
        return {
            "total_skills": total_skills,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "overall_success_rate": overall_success_rate,
            "skills_by_category": categories,
            "most_executed_skill": self._get_most_executed_skill()
        }
    
    def _get_most_executed_skill(self) -> Optional[Dict[str, Any]]:
        """获取执行次数最多的技能"""
        if not self.skills_db:
            return None
        
        most_executed = max(self.skills_db.values(), 
                          key=lambda x: x.get('execution_count', 0))
        
        return {
            "name": most_executed['name'],
            "execution_count": most_executed.get('execution_count', 0),
            "success_rate": most_executed.get('success_rate', 0)
        }

