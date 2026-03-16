"""
API文档模块 - Mirexs API网关

提供API文档生成功能，包括：
1. OpenAPI规范生成
2. Markdown文档生成
3. HTML文档生成
4. Postman集合生成
5. 文档版本管理
"""

import logging
import time
import json
import os
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class DocFormat(Enum):
    """文档格式枚举"""
    OPENAPI = "openapi"
    MARKDOWN = "markdown"
    HTML = "html"
    POSTMAN = "postman"
    REDOC = "redoc"
    SWAGGER = "swagger"

@dataclass
class OpenAPISpec:
    """OpenAPI规范"""
    openapi: str = "3.0.0"
    info: Dict[str, Any] = field(default_factory=dict)
    servers: List[Dict[str, Any]] = field(default_factory=list)
    paths: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)
    tags: List[Dict[str, Any]] = field(default_factory=list)
    security: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class DocConfig:
    """文档配置"""
    # 基本信息
    title: str = "Mirexs API"
    version: str = "1.0.0"
    description: str = "Mirexs数字生命体API文档"
    
    # 服务器配置
    servers: List[Dict[str, str]] = field(default_factory=lambda: [
        {"url": "https://api.mirexs.com/v1", "description": "Production server"},
        {"url": "https://staging.api.mirexs.com/v1", "description": "Staging server"}
    ])
    
    # 认证配置
    security_schemes: Dict[str, Any] = field(default_factory=lambda: {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    })
    
    # 输出配置
    output_dir: str = "docs/api/"
    include_examples: bool = True
    include_schemas: bool = True

class APIDocumentation:
    """
    API文档管理器
    
    负责API文档的生成和管理。
    """
    
    def __init__(self, config: Optional[DocConfig] = None):
        """
        初始化API文档管理器
        
        Args:
            config: 文档配置
        """
        self.config = config or DocConfig()
        
        # OpenAPI规范
        self.spec = OpenAPISpec(
            info={
                "title": self.config.title,
                "version": self.config.version,
                "description": self.config.description
            },
            servers=self.config.servers
        )
        
        # 路径定义
        self.paths: Dict[str, Any] = {}
        
        # 组件定义
        self.components: Dict[str, Any] = {
            "schemas": {},
            "securitySchemes": self.config.security_schemes
        }
        
        # 标签
        self.tags: List[Dict[str, Any]] = []
        
        # 统计
        self.stats = {
            "documents_generated": 0,
            "paths_documented": 0,
            "schemas_documented": 0
        }
        
        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        logger.info("APIDocumentation initialized")
    
    def add_path(self, path: str, method: str, operation: Dict[str, Any]):
        """
        添加路径定义
        
        Args:
            path: 路径
            method: HTTP方法
            operation: 操作定义
        """
        if path not in self.paths:
            self.paths[path] = {}
        
        self.paths[path][method.lower()] = operation
        self.stats["paths_documented"] += 1
        
        logger.debug(f"Path added: {method} {path}")
    
    def add_schema(self, name: str, schema: Dict[str, Any]):
        """
        添加模式定义
        
        Args:
            name: 模式名称
            schema: 模式定义
        """
        self.components["schemas"][name] = schema
        self.stats["schemas_documented"] += 1
        
        logger.debug(f"Schema added: {name}")
    
    def add_tag(self, name: str, description: str):
        """
        添加标签
        
        Args:
            name: 标签名称
            description: 标签描述
        """
        self.tags.append({
            "name": name,
            "description": description
        })
    
    def generate_openapi(self) -> Dict[str, Any]:
        """
        生成OpenAPI规范
        
        Returns:
            OpenAPI规范字典
        """
        self.spec.paths = self.paths
        self.spec.components = self.components
        self.spec.tags = self.tags
        
        # 添加安全要求
        if self.config.security_schemes:
            self.spec.security = [{"ApiKeyAuth": []}]
        
        result = {
            "openapi": self.spec.openapi,
            "info": self.spec.info,
            "servers": self.spec.servers,
            "paths": self.spec.paths,
            "components": self.spec.components,
            "tags": self.spec.tags,
            "security": self.spec.security
        }
        
        self.stats["documents_generated"] += 1
        
        logger.info(f"OpenAPI specification generated with {len(self.paths)} paths")
        
        return result
    
    def save_openapi(self, filename: str = "openapi.json") -> str:
        """
        保存OpenAPI规范到文件
        
        Args:
            filename: 文件名
        
        Returns:
            文件路径
        """
        filepath = os.path.join(self.config.output_dir, filename)
        
        spec = self.generate_openapi()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        logger.info(f"OpenAPI specification saved to {filepath}")
        
        return filepath
    
    def generate_markdown(self) -> str:
        """
        生成Markdown文档
        
        Returns:
            Markdown内容
        """
        lines = []
        
        # 标题
        lines.append(f"# {self.config.title}")
        lines.append("")
        lines.append(self.config.description)
        lines.append("")
        
        # 服务器信息
        lines.append("## 服务器")
        lines.append("")
        for server in self.config.servers:
            lines.append(f"- **{server.get('description', 'Server')}**: `{server['url']}`")
        lines.append("")
        
        # 认证
        lines.append("## 认证")
        lines.append("")
        for name, scheme in self.config.security_schemes.items():
            lines.append(f"### {name}")
            lines.append(f"- **类型**: {scheme['type']}")
            if scheme['type'] == 'apiKey':
                lines.append(f"- **位置**: {scheme['in']}")
                lines.append(f"- **名称**: {scheme['name']}")
            lines.append("")
        
        # 标签
        if self.tags:
            lines.append("## 标签")
            lines.append("")
            for tag in self.tags:
                lines.append(f"- **{tag['name']}**: {tag.get('description', '')}")
            lines.append("")
        
        # 路径
        lines.append("## 端点")
        lines.append("")
        
        for path, methods in self.paths.items():
            lines.append(f"### `{path}`")
            lines.append("")
            
            for method, operation in methods.items():
                lines.append(f"#### {method.upper()}")
                lines.append("")
                lines.append(operation.get('description', ''))
                lines.append("")
                
                # 参数
                if 'parameters' in operation:
                    lines.append("**参数:**")
                    lines.append("")
                    lines.append("| 名称 | 位置 | 类型 | 必需 | 描述 |")
                    lines.append("|------|------|------|------|------|")
                    for param in operation['parameters']:
                        required = "是" if param.get('required', False) else "否"
                        lines.append(f"| {param['name']} | {param['in']} | {param.get('schema', {}).get('type', 'string')} | {required} | {param.get('description', '')} |")
                    lines.append("")
                
                # 请求体
                if 'requestBody' in operation:
                    lines.append("**请求体:**")
                    lines.append("")
                    content = operation['requestBody'].get('content', {})
                    for content_type, content_spec in content.items():
                        lines.append(f"- **Content-Type**: `{content_type}`")
                        if 'schema' in content_spec:
                            lines.append(f"- **Schema**: `{content_spec['schema'].get('$ref', 'object')}`")
                    lines.append("")
                
                # 响应
                if 'responses' in operation:
                    lines.append("**响应:**")
                    lines.append("")
                    for status, response in operation['responses'].items():
                        lines.append(f"- **{status}**: {response.get('description', '')}")
                    lines.append("")
        
        result = "\n".join(lines)
        
        logger.info("Markdown documentation generated")
        
        return result
    
    def generate_html(self) -> str:
        """
        生成HTML文档
        
        Returns:
            HTML内容
        """
        # 使用Redoc或Swagger UI
        html_template = """<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <redoc spec-url='{spec_url}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
</body>
</html>"""
        
        # 先保存OpenAPI规范
        spec_path = self.save_openapi("openapi.json")
        spec_url = os.path.basename(spec_path)
        
        html = html_template.format(
            title=self.config.title,
            spec_url=spec_url
        )
        
        logger.info("HTML documentation generated")
        
        return html
    
    def generate_postman(self) -> Dict[str, Any]:
        """
        生成Postman集合
        
        Returns:
            Postman集合字典
        """
        collection = {
            "info": {
                "name": self.config.title,
                "description": self.config.description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": []
        }
        
        for path, methods in self.paths.items():
            for method, operation in methods.items():
                item = {
                    "name": f"{method.upper()} {path}",
                    "request": {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": f"{{{{base_url}}}}{path}",
                            "host": ["{{base_url}}"],
                            "path": path.strip('/').split('/')
                        },
                        "description": operation.get('description', '')
                    }
                }
                
                # 添加认证头
                if self.config.security_schemes:
                    item["request"]["header"].append({
                        "key": "X-API-Key",
                        "value": "{{api_key}}",
                        "type": "text"
                    })
                
                collection["item"].append(item)
        
        logger.info(f"Postman collection generated with {len(collection['item'])} items")
        
        return collection
    
    def generate_all(self) -> Dict[str, str]:
        """
        生成所有格式的文档
        
        Returns:
            格式到文件路径的映射
        """
        results = {}
        
        # OpenAPI
        openapi_path = self.save_openapi("openapi.json")
        results['openapi'] = openapi_path
        
        # Markdown
        markdown_path = os.path.join(self.config.output_dir, "api.md")
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_markdown())
        results['markdown'] = markdown_path
        
        # HTML
        html_path = os.path.join(self.config.output_dir, "index.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_html())
        results['html'] = html_path
        
        # Postman
        postman_path = os.path.join(self.config.output_dir, "postman.json")
        with open(postman_path, 'w', encoding='utf-8') as f:
            json.dump(self.generate_postman(), f, indent=2)
        results['postman'] = postman_path
        
        logger.info(f"All documentation generated in {self.config.output_dir}")
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取API文档管理器状态
        
        Returns:
            状态字典
        """
        return {
            "title": self.config.title,
            "version": self.config.version,
            "paths": len(self.paths),
            "schemas": len(self.components.get("schemas", {})),
            "tags": len(self.tags),
            "stats": self.stats,
            "output_dir": self.config.output_dir
        }
    
    def shutdown(self):
        """关闭API文档管理器"""
        logger.info("Shutting down APIDocumentation...")
        
        self.paths.clear()
        self.components.clear()
        self.tags.clear()
        
        logger.info("APIDocumentation shutdown completed")

# 单例模式实现
_api_documentation_instance: Optional[APIDocumentation] = None

def get_api_documentation(config: Optional[DocConfig] = None) -> APIDocumentation:
    """
    获取API文档管理器单例
    
    Args:
        config: 文档配置
    
    Returns:
        API文档管理器实例
    """
    global _api_documentation_instance
    if _api_documentation_instance is None:
        _api_documentation_instance = APIDocumentation(config)
    return _api_documentation_instance

