"""
模板引擎：内容模板管理
支持模板创建、变量替换、条件逻辑、循环等功能
"""

import os
import json
import logging
import re
import jinja2
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class TemplateType(Enum):
    """模板类型枚举"""
    DOCUMENT = "document"
    EMAIL = "email"
    REPORT = "report"
    PRESENTATION = "presentation"
    CODE = "code"
    CUSTOM = "custom"

class TemplateVariable(BaseModel):
    """模板变量"""
    name: str
    type: str  # text, number, date, list, boolean
    description: str
    default_value: Optional[Any] = None
    required: bool = False
    validation_rules: Optional[Dict] = None

class Template(BaseModel):
    """模板定义"""
    template_id: str
    name: str
    type: TemplateType
    content: str
    variables: List[TemplateVariable]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class TemplateEngine:
    """模板引擎"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        
        # 初始化Jinja2环境
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # 添加自定义过滤器
        self._register_custom_filters()
        
        # 模板缓存
        self.template_cache: Dict[str, Template] = {}
        
        # 加载现有模板
        self._load_existing_templates()
        
        logger.info("TemplateEngine initialized")
    
    def _register_custom_filters(self):
        """注册自定义过滤器"""
        # 日期格式化过滤器
        self.jinja_env.filters['date_format'] = self._date_format_filter
        
        # 数字格式化过滤器
        self.jinja_env.filters['number_format'] = self._number_format_filter
        
        # 文本截断过滤器
        self.jinja_env.filters['truncate'] = self._truncate_filter
        
        # 列表连接过滤器
        self.jinja_env.filters['join'] = self._join_filter
    
    def _date_format_filter(self, value, format_str='%Y-%m-%d'):
        """日期格式化过滤器"""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        
        if isinstance(value, datetime):
            return value.strftime(format_str)
        else:
            return value
    
    def _number_format_filter(self, value, precision=2):
        """数字格式化过滤器"""
        try:
            num = float(value)
            return f"{num:.{precision}f}"
        except (ValueError, TypeError):
            return value
    
    def _truncate_filter(self, value, length=100, ellipsis='...'):
        """文本截断过滤器"""
        if not isinstance(value, str):
            value = str(value)
        
        if len(value) <= length:
            return value
        else:
            return value[:length - len(ellipsis)] + ellipsis
    
    def _join_filter(self, value, delimiter=', '):
        """列表连接过滤器"""
        if isinstance(value, list):
            return delimiter.join(str(item) for item in value)
        else:
            return value
    
    def _load_existing_templates(self):
        """加载现有模板"""
        try:
            template_files = list(self.templates_dir.glob("*.json"))
            
            for template_file in template_files:
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = json.load(f)
                    
                    template = Template(**template_data)
                    self.template_cache[template.template_id] = template
                    
                except Exception as e:
                    logger.warning(f"Failed to load template from {template_file}: {e}")
            
            logger.info(f"Loaded {len(self.template_cache)} templates from disk")
            
        except Exception as e:
            logger.error(f"Failed to load existing templates: {e}")
    
    def create_template(self, 
                       name: str,
                       template_type: TemplateType,
                       content: str,
                       variables: List[TemplateVariable],
                       metadata: Optional[Dict] = None) -> Template:
        """
        创建新模板
        
        Args:
            name: 模板名称
            template_type: 模板类型
            content: 模板内容
            variables: 模板变量
            metadata: 元数据
            
        Returns:
            Template: 创建的模板
        """
        try:
            # 生成模板ID
            template_id = self._generate_template_id(name)
            
            # 验证模板语法
            self._validate_template_syntax(content)
            
            # 创建模板对象
            now = datetime.now()
            template = Template(
                template_id=template_id,
                name=name,
                type=template_type,
                content=content,
                variables=variables,
                metadata=metadata or {},
                created_at=now,
                updated_at=now
            )
            
            # 保存到缓存和磁盘
            self.template_cache[template_id] = template
            self._save_template_to_disk(template)
            
            logger.info(f"Created template {template_id}: {name}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise
    
    def _generate_template_id(self, name: str) -> str:
        """生成模板ID"""
        import hashlib
        unique_string = f"{name}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:8]
    
    def _validate_template_syntax(self, content: str):
        """验证模板语法"""
        try:
            # 尝试编译模板来检查语法
            self.jinja_env.from_string(content)
        except jinja2.TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error: {e}")
        except Exception as e:
            raise ValueError(f"Template validation error: {e}")
    
    def _save_template_to_disk(self, template: Template):
        """保存模板到磁盘"""
        try:
            template_file = self.templates_dir / f"{template.template_id}.json"
            
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template.dict(), f, ensure_ascii=False, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Failed to save template to disk: {e}")
            raise
    
    def get_template(self, template_id: str) -> Optional[Template]:
        """获取模板"""
        return self.template_cache.get(template_id)
    
    def get_templates_by_type(self, template_type: TemplateType) -> List[Template]:
        """根据类型获取模板"""
        return [template for template in self.template_cache.values() 
                if template.type == template_type]
    
    def update_template(self, 
                       template_id: str,
                       content: Optional[str] = None,
                       variables: Optional[List[TemplateVariable]] = None,
                       metadata: Optional[Dict] = None) -> Optional[Template]:
        """
        更新模板
        
        Args:
            template_id: 模板ID
            content: 新内容
            variables: 新变量列表
            metadata: 新元数据
            
        Returns:
            Template: 更新后的模板
        """
        try:
            template = self.get_template(template_id)
            if not template:
                return None
            
            # 更新内容
            if content is not None:
                self._validate_template_syntax(content)
                template.content = content
            
            # 更新变量
            if variables is not None:
                template.variables = variables
            
            # 更新元数据
            if metadata is not None:
                template.metadata.update(metadata)
            
            # 更新时间戳
            template.updated_at = datetime.now()
            
            # 保存到磁盘
            self._save_template_to_disk(template)
            
            logger.info(f"Updated template {template_id}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to update template: {e}")
            return None
    
    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        try:
            if template_id not in self.template_cache:
                return False
            
            # 从缓存中移除
            del self.template_cache[template_id]
            
            # 从磁盘删除文件
            template_file = self.templates_dir / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            
            logger.info(f"Deleted template {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template: {e}")
            return False
    
    def render_template(self, 
                       template_id: str, 
                       variables: Dict[str, Any],
                       strict: bool = True) -> Tuple[Optional[str], List[str]]:
        """
        渲染模板
        
        Args:
            template_id: 模板ID
            variables: 变量值
            strict: 是否严格模式（缺少变量时报错）
            
        Returns:
            Tuple: (渲染结果, 警告列表)
        """
        try:
            template = self.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            warnings = []
            
            # 验证变量
            validated_variables = self._validate_variables(template.variables, variables, warnings)
            
            # 渲染模板
            jinja_template = self.jinja_env.from_string(template.content)
            rendered_content = jinja_template.render(**validated_variables)
            
            logger.info(f"Rendered template {template_id}")
            return rendered_content, warnings
            
        except jinja2.TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise ValueError(f"Template rendering failed: {e}")
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise
    
    def _validate_variables(self, 
                          template_variables: List[TemplateVariable],
                          provided_variables: Dict[str, Any],
                          warnings: List[str]) -> Dict[str, Any]:
        """验证变量"""
        validated_vars = {}
        
        for var_def in template_variables:
            var_name = var_def.name
            
            if var_name in provided_variables:
                # 验证变量值
                value = provided_variables[var_name]
                validated_value = self._validate_variable_value(var_def, value, warnings)
                validated_vars[var_name] = validated_value
                
            elif var_def.required:
                if var_def.default_value is not None:
                    validated_vars[var_name] = var_def.default_value
                    warnings.append(f"使用默认值 for required variable '{var_name}'")
                else:
                    raise ValueError(f"Required variable '{var_name}' is missing")
            else:
                if var_def.default_value is not None:
                    validated_vars[var_name] = var_def.default_value
                else:
                    warnings.append(f"Optional variable '{var_name}' is missing")
        
        # 添加额外变量（不在定义中但提供了的变量）
        for var_name, value in provided_variables.items():
            if var_name not in validated_vars:
                validated_vars[var_name] = value
                warnings.append(f"Extra variable '{var_name}' provided")
        
        return validated_vars
    
    def _validate_variable_value(self, 
                               var_def: TemplateVariable, 
                               value: Any,
                               warnings: List[str]) -> Any:
        """验证变量值"""
        # 类型检查
        expected_type = var_def.type
        if expected_type == "number":
            try:
                return float(value)
            except (ValueError, TypeError):
                warnings.append(f"Variable '{var_def.name}' should be a number, got {type(value).__name__}")
                return value
        elif expected_type == "boolean":
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                if value.lower() in ['true', 'yes', '1']:
                    return True
                elif value.lower() in ['false', 'no', '0']:
                    return False
            warnings.append(f"Variable '{var_def.name}' should be a boolean")
            return bool(value)
        else:
            return str(value)
    
    def extract_variables_from_content(self, content: str) -> List[TemplateVariable]:
        """从内容中提取变量"""
        variables = []
        
        # 使用正则表达式查找Jinja2变量
        variable_pattern = r'\{\{\s*(\w+)\s*\}\}'
        matches = re.findall(variable_pattern, content)
        
        for var_name in set(matches):  # 去重
            # 跳过Jinja2内置变量
            if var_name in ['loop', 'super', 'self', 'namespace']:
                continue
            
            variables.append(TemplateVariable(
                name=var_name,
                type="text",  # 默认类型
                description=f"自动提取的变量: {var_name}",
                required=False
            ))
        
        return variables
    
    def create_template_from_content(self, 
                                   name: str,
                                   content: str,
                                   template_type: TemplateType = TemplateType.CUSTOM) -> Template:
        """
        从内容创建模板（自动提取变量）
        
        Args:
            name: 模板名称
            content: 模板内容
            template_type: 模板类型
            
        Returns:
            Template: 创建的模板
        """
        variables = self.extract_variables_from_content(content)
        
        return self.create_template(
            name=name,
            template_type=template_type,
            content=content,
            variables=variables
        )
    
    def batch_render_templates(self, 
                             template_data: List[Tuple[str, Dict[str, Any]]],
                             strict: bool = True) -> List[Tuple[Optional[str], List[str]]]:
        """批量渲染模板"""
        results = []
        
        for template_id, variables in template_data:
            try:
                result, warnings = self.render_template(template_id, variables, strict)
                results.append((result, warnings))
            except Exception as e:
                logger.error(f"Failed to render template {template_id}: {e}")
                results.append((None, [str(e)]))
        
        return results
    
    def export_template(self, template_id: str, output_path: str) -> bool:
        """导出模板"""
        try:
            template = self.get_template(template_id)
            if not template:
                return False
            
            export_data = {
                "template": template.dict(),
                "exported_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Exported template {template_id} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export template: {e}")
            return False
    
    def import_template(self, import_path: str) -> Optional[Template]:
        """导入模板"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            template_data = import_data["template"]
            
            # 转换日期字符串为datetime对象
            template_data["created_at"] = datetime.fromisoformat(template_data["created_at"].replace('Z', '+00:00'))
            template_data["updated_at"] = datetime.fromisoformat(template_data["updated_at"].replace('Z', '+00:00'))
            
            # 创建模板对象
            template = Template(**template_data)
            
            # 保存到系统
            self.template_cache[template.template_id] = template
            self._save_template_to_disk(template)
            
            logger.info(f"Imported template {template.template_id} from {import_path}")
            return template
            
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return None
    
    def search_templates(self, query: str) -> List[Template]:
        """搜索模板"""
        results = []
        query_lower = query.lower()
        
        for template in self.template_cache.values():
            # 在名称、内容和元数据中搜索
            if (query_lower in template.name.lower() or
                query_lower in template.content.lower() or
                any(query_lower in str(value).lower() for value in template.metadata.values())):
                results.append(template)
        
        return results

# 单例实例
_template_engine_instance = None

def get_template_engine() -> TemplateEngine:
    """获取模板引擎单例"""
    global _template_engine_instance
    if _template_engine_instance is None:
        _template_engine_instance = TemplateEngine()
    return _template_engine_instance

