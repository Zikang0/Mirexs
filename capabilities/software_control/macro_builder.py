"""
宏构建器：构建自动化宏
"""
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MacroType(Enum):
    """宏类型枚举"""
    KEYBOARD_MACRO = "keyboard_macro"
    MOUSE_MACRO = "mouse_macro"
    APPLICATION_MACRO = "application_macro"
    COMPOSITE_MACRO = "composite_macro"

@dataclass
class MacroAction:
    """宏动作"""
    type: str
    parameters: Dict[str, Any]
    delay_before: float = 0.0  # 执行前延迟
    delay_after: float = 0.0   # 执行后延迟

@dataclass
class Macro:
    """宏定义"""
    id: str
    name: str
    description: str
    macro_type: MacroType
    actions: List[MacroAction]
    created_time: datetime
    updated_time: datetime
    version: str = "1.0"
    enabled: bool = True
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class MacroBuilder:
    """宏构建器"""
    
    def __init__(self):
        self.macros: Dict[str, Macro] = {}
        self.macro_templates: Dict[str, Macro] = {}
        self._setup_logging()
        self._load_macro_templates()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_macro_templates(self):
        """加载宏模板"""
        # 文本输入宏模板
        text_input_macro = Macro(
            id="text_input_template",
            name="文本输入模板",
            description="快速文本输入宏模板",
            macro_type=MacroType.KEYBOARD_MACRO,
            actions=[
                MacroAction(
                    type="keyboard_input",
                    parameters={"text": "Hello World!"}
                )
            ],
            created_time=datetime.now(),
            updated_time=datetime.now(),
            tags=["text", "input", "keyboard"]
        )
        
        self.macro_templates[text_input_macro.id] = text_input_macro
        
        # 应用启动宏模板
        app_launch_macro = Macro(
            id="app_launch_template",
            name="应用启动模板",
            description="应用程序启动宏模板",
            macro_type=MacroType.APPLICATION_MACRO,
            actions=[
                MacroAction(
                    type="launch_application",
                    parameters={"application_name": "notepad"}
                )
            ],
            created_time=datetime.now(),
            updated_time=datetime.now(),
            tags=["application", "launch"]
        )
        
        self.macro_templates[app_launch_macro.id] = app_launch_macro
    
    def create_macro(self, name: str, description: str, macro_type: MacroType, 
                    actions: List[MacroAction], tags: List[str] = None) -> Optional[str]:
        """创建宏"""
        try:
            import uuid
            macro_id = str(uuid.uuid4())
            
            macro = Macro(
                id=macro_id,
                name=name,
                description=description,
                macro_type=macro_type,
                actions=actions,
                created_time=datetime.now(),
                updated_time=datetime.now(),
                tags=tags or []
            )
            
            self.macros[macro_id] = macro
            logger.info(f"创建宏: {name} (ID: {macro_id})")
            return macro_id
            
        except Exception as e:
            logger.error(f"创建宏失败: {str(e)}")
            return None
    
    def create_macro_from_template(self, template_id: str, name: str = None, 
                                  parameters: Dict[str, Any] = None) -> Optional[str]:
        """从模板创建宏"""
        try:
            if template_id not in self.macro_templates:
                return None
            
            template = self.macro_templates[template_id]
            
            # 替换模板参数
            customized_actions = self._customize_template_actions(template.actions, parameters or {})
            
            macro_name = name or f"{template.name} - 自定义"
            
            return self.create_macro(
                name=macro_name,
                description=template.description,
                macro_type=template.macro_type,
                actions=customized_actions,
                tags=template.tags.copy()
            )
            
        except Exception as e:
            logger.error(f"从模板创建宏失败: {str(e)}")
            return None
    
    def _customize_template_actions(self, template_actions: List[MacroAction], 
                                  parameters: Dict[str, Any]) -> List[MacroAction]:
        """自定义模板动作"""
        customized_actions = []
        
        for action in template_actions:
            customized_params = action.parameters.copy()
            
            # 替换参数占位符
            for key, value in customized_params.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    param_name = value[2:-1]
                    if param_name in parameters:
                        customized_params[key] = parameters[param_name]
            
            customized_action = MacroAction(
                type=action.type,
                parameters=customized_params,
                delay_before=action.delay_before,
                delay_after=action.delay_after
            )
            customized_actions.append(customized_action)
        
        return customized_actions
    
    def execute_macro(self, macro_id: str, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """执行宏"""
        try:
            if macro_id not in self.macros:
                return False, f"宏不存在: {macro_id}"
            
            macro = self.macros[macro_id]
            if not macro.enabled:
                return False, f"宏已禁用: {macro.name}"
            
            logger.info(f"开始执行宏: {macro.name}")
            
            from .automation_engine import get_automation_engine
            automation_engine = get_automation_engine()
            
            # 将宏动作转换为自动化任务动作
            task_actions = []
            for macro_action in macro.actions:
                task_action = {
                    'type': macro_action.type,
                    'params': macro_action.parameters
                }
                
                # 添加延迟
                if macro_action.delay_before > 0:
                    task_actions.append({
                        'type': 'wait',
                        'params': {'duration': macro_action.delay_before}
                    })
                
                task_actions.append(task_action)
                
                if macro_action.delay_after > 0:
                    task_actions.append({
                        'type': 'wait',
                        'params': {'duration': macro_action.delay_after}
                    })
            
            # 创建并执行任务
            task_id = automation_engine.create_task(
                name=f"Macro_{macro.name}",
                description=f"宏执行: {macro.description}",
                actions=task_actions
            )
            
            success = automation_engine.execute_task(task_id)
            
            if success:
                logger.info(f"宏执行成功: {macro.name}")
                return True, f"宏执行成功: {macro.name}"
            else:
                logger.error(f"宏执行失败: {macro.name}")
                return False, f"宏执行失败: {macro.name}"
            
        except Exception as e:
            logger.error(f"执行宏失败 {macro_id}: {str(e)}")
            return False, f"执行失败: {str(e)}"
    
    def edit_macro(self, macro_id: str, **kwargs) -> bool:
        """编辑宏"""
        try:
            if macro_id not in self.macros:
                return False
            
            macro = self.macros[macro_id]
            
            allowed_fields = ['name', 'description', 'actions', 'enabled', 'tags']
            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(macro, field, value)
            
            macro.updated_time = datetime.now()
            logger.info(f"更新宏: {macro.name}")
            return True
            
        except Exception as e:
            logger.error(f"编辑宏失败: {str(e)}")
            return False
    
    def delete_macro(self, macro_id: str) -> bool:
        """删除宏"""
        try:
            if macro_id in self.macros:
                macro_name = self.macros[macro_id].name
                del self.macros[macro_id]
                logger.info(f"删除宏: {macro_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"删除宏失败: {str(e)}")
            return False
    
    def get_macro(self, macro_id: str) -> Optional[Macro]:
        """获取宏"""
        return self.macros.get(macro_id)
    
    def get_all_macros(self) -> List[Macro]:
        """获取所有宏"""
        return list(self.macros.values())
    
    def search_macros(self, query: str, search_fields: List[str] = None) -> List[Macro]:
        """搜索宏"""
        if search_fields is None:
            search_fields = ['name', 'description', 'tags']
        
        results = []
        query_lower = query.lower()
        
        for macro in self.macros.values():
            for field in search_fields:
                if field == 'tags':
                    for tag in macro.tags:
                        if query_lower in tag.lower():
                            results.append(macro)
                            break
                else:
                    value = getattr(macro, field, '')
                    if query_lower in str(value).lower():
                        results.append(macro)
                        break
        
        return results
    
    def export_macro(self, macro_id: str, file_path: str) -> bool:
        """导出宏"""
        try:
            if macro_id not in self.macros:
                return False
            
            macro = self.macros[macro_id]
            
            macro_data = {
                'id': macro.id,
                'name': macro.name,
                'description': macro.description,
                'macro_type': macro.macro_type.value,
                'actions': [asdict(action) for action in macro.actions],
                'version': macro.version,
                'enabled': macro.enabled,
                'tags': macro.tags,
                'created_time': macro.created_time.isoformat(),
                'updated_time': macro.updated_time.isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(macro_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"成功导出宏到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出宏失败: {str(e)}")
            return False
    
    def import_macro(self, file_path: str) -> bool:
        """导入宏"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                macro_data = json.load(f)
            
            # 转换动作数据
            actions = []
            for action_data in macro_data['actions']:
                action = MacroAction(
                    type=action_data['type'],
                    parameters=action_data['parameters'],
                    delay_before=action_data.get('delay_before', 0.0),
                    delay_after=action_data.get('delay_after', 0.0)
                )
                actions.append(action)
            
            macro = Macro(
                id=macro_data['id'],
                name=macro_data['name'],
                description=macro_data['description'],
                macro_type=MacroType(macro_data['macro_type']),
                actions=actions,
                created_time=datetime.fromisoformat(macro_data['created_time']),
                updated_time=datetime.fromisoformat(macro_data['updated_time']),
                version=macro_data.get('version', '1.0'),
                enabled=macro_data.get('enabled', True),
                tags=macro_data.get('tags', [])
            )
            
            self.macros[macro.id] = macro
            logger.info(f"成功导入宏: {macro.name}")
            return True
            
        except Exception as e:
            logger.error(f"导入宏失败: {str(e)}")
            return False
    
    def create_macro_from_operations(self, operations: List[Dict[str, Any]]) -> Optional[str]:
        """从操作序列创建宏"""
        try:
            macro_actions = []
            
            for operation in operations:
                action = self._convert_operation_to_macro_action(operation)
                if action:
                    macro_actions.append(action)
            
            if not macro_actions:
                return None
            
            import uuid
            macro_id = str(uuid.uuid4())
            
            macro = Macro(
                id=macro_id,
                name="从操作生成的宏",
                description="从用户操作序列自动生成的宏",
                macro_type=MacroType.COMPOSITE_MACRO,
                actions=macro_actions,
                created_time=datetime.now(),
                updated_time=datetime.now()
            )
            
            self.macros[macro_id] = macro
            return macro_id
            
        except Exception as e:
            logger.error(f"从操作创建宏失败: {str(e)}")
            return None
    
    def _convert_operation_to_macro_action(self, operation: Dict[str, Any]) -> Optional[MacroAction]:
        """将操作转换为宏动作"""
        op_type = operation.get('type')
        
        if op_type == 'mouse_click':
            return MacroAction(
                type='mouse_click',
                parameters={
                    'x': operation.get('x'),
                    'y': operation.get('y'),
                    'button': operation.get('button', 'left')
                }
            )
        elif op_type == 'keyboard_input':
            return MacroAction(
                type='keyboard_input',
                parameters={'text': operation.get('key')}
            )
        elif op_type == 'application_launch':
            return MacroAction(
                type='launch_application',
                parameters={'application_name': operation.get('application_name')}
            )
        
        return None
    
    def optimize_macro(self, macro_id: str) -> bool:
        """优化宏"""
        try:
            if macro_id not in self.macros:
                return False
            
            macro = self.macros[macro_id]
            optimized_actions = self._optimize_actions(macro.actions)
            
            macro.actions = optimized_actions
            macro.updated_time = datetime.now()
            
            logger.info(f"优化宏: {macro.name}")
            return True
            
        except Exception as e:
            logger.error(f"优化宏失败: {str(e)}")
            return False
    
    def _optimize_actions(self, actions: List[MacroAction]) -> List[MacroAction]:
        """优化动作序列"""
        optimized = []
        
        i = 0
        while i < len(actions):
            current_action = actions[i]
            
            # 合并连续的键盘输入
            if current_action.type == 'keyboard_input':
                combined_text = current_action.parameters.get('text', '')
                j = i + 1
                
                while j < len(actions) and actions[j].type == 'keyboard_input':
                    combined_text += actions[j].parameters.get('text', '')
                    j += 1
                
                if j > i + 1:
                    # 创建合并后的动作
                    combined_action = MacroAction(
                        type='keyboard_input',
                        parameters={'text': combined_text},
                        delay_before=current_action.delay_before,
                        delay_after=actions[j-1].delay_after
                    )
                    optimized.append(combined_action)
                    i = j
                    continue
            
            optimized.append(current_action)
            i += 1
        
        return optimized

# 单例实例
_macro_builder_instance = None

def get_macro_builder() -> MacroBuilder:
    """获取宏构建器单例"""
    global _macro_builder_instance
    if _macro_builder_instance is None:
        _macro_builder_instance = MacroBuilder()
    return _macro_builder_instance

