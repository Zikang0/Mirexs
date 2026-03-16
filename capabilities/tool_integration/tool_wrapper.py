"""
工具包装器模块
提供统一的工具接口包装，实现工具调用的标准化
"""

import os
import sys
import inspect
import logging
import asyncio
import tempfile
from typing import Dict, List, Any, Optional, Callable, Union, Awaitable
from pathlib import Path
import json
import uuid
import traceback
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ToolType(Enum):
    """工具类型枚举"""
    PYTHON_FUNCTION = "python_function"
    COMMAND_LINE = "command_line"
    WEB_SERVICE = "web_service"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }

class BaseToolWrapper:
    """基础工具包装器"""
    
    def __init__(self, tool_id: str, name: str, description: str, version: str = "1.0.0"):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.version = version
        self.tool_type = ToolType.UNKNOWN
        self.required_parameters: List[str] = []
        self.optional_parameters: Dict[str, Any] = {}
        self.return_type: Any = None
        self.timeout: int = 300  # 默认5分钟超时
        
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # 验证参数
            validation_result = self._validate_parameters(kwargs)
            if not validation_result["success"]:
                return ToolResult(
                    success=False,
                    output=None,
                    error=validation_result["error"]
                )
            
            # 执行工具
            output = await self._execute_internal(**kwargs)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return ToolResult(
                success=True,
                output=output,
                execution_time=execution_time,
                metadata={"tool_id": self.tool_id}
            )
            
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - start_time
            return ToolResult(
                success=False,
                output=None,
                error=f"工具执行超时 ({self.timeout}秒)",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"工具执行失败: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time,
                metadata={"traceback": traceback.format_exc()}
            )
    
    async def _execute_internal(self, **kwargs) -> Any:
        """内部执行方法，由子类实现"""
        raise NotImplementedError("子类必须实现此方法")
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        try:
            # 检查必需参数
            for param in self.required_parameters:
                if param not in parameters:
                    return {
                        "success": False,
                        "error": f"缺少必需参数: {param}"
                    }
            
            # 检查参数类型（简化实现）
            for param, value in parameters.items():
                if param in self.optional_parameters:
                    expected_type = self.optional_parameters[param].get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        return {
                            "success": False,
                            "error": f"参数 {param} 类型不匹配，期望 {expected_type}"
                        }
            
            return {"success": True}
        except Exception as e:
            logger.error(f"参数验证失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型匹配"""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict
        }
        
        if expected_type in type_map:
            return isinstance(value, type_map[expected_type])
        
        return True  # 对于未知类型，不进行严格检查
    
    def get_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tool_type": self.tool_type.value,
            "required_parameters": self.required_parameters,
            "optional_parameters": self.optional_parameters,
            "return_type": str(self.return_type) if self.return_type else None,
            "timeout": self.timeout
        }

class PythonFunctionWrapper(BaseToolWrapper):
    """Python函数包装器"""
    
    def __init__(self, tool_id: str, name: str, description: str, function: Callable):
        super().__init__(tool_id, name, description)
        self.function = function
        self.tool_type = ToolType.PYTHON_FUNCTION
        
        # 分析函数签名
        self._analyze_function()
    
    def _analyze_function(self):
        """分析函数签名"""
        try:
            signature = inspect.signature(self.function)
            
            for param_name, param in signature.parameters.items():
                if param.default == inspect.Parameter.empty:
                    self.required_parameters.append(param_name)
                else:
                    param_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        param_type = self._get_type_name(param.annotation)
                    
                    self.optional_parameters[param_name] = {
                        "type": param_type,
                        "default": param.default
                    }
            
            # 设置返回类型
            if signature.return_annotation != inspect.Parameter.empty:
                self.return_type = signature.return_annotation
        
        except Exception as e:
            logger.warning(f"函数分析失败: {e}")
    
    def _get_type_name(self, type_annotation) -> str:
        """获取类型名称"""
        if hasattr(type_annotation, '__name__'):
            return type_annotation.__name__.lower()
        return str(type_annotation)
    
    async def _execute_internal(self, **kwargs) -> Any:
        """执行Python函数"""
        if inspect.iscoroutinefunction(self.function):
            return await self.function(**kwargs)
        else:
            # 在线程池中执行同步函数，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.function, **kwargs)

class CommandLineWrapper(BaseToolWrapper):
    """命令行工具包装器"""
    
    def __init__(self, tool_id: str, name: str, description: str, command_template: str):
        super().__init__(tool_id, name, description)
        self.command_template = command_template
        self.tool_type = ToolType.COMMAND_LINE
        
        # 从命令模板中提取参数
        self._analyze_command_template()
    
    def _analyze_command_template(self):
        """分析命令模板"""
        import re
        
        # 提取参数占位符
        params = re.findall(r'\{(\w+)\}', self.command_template)
        
        for param in params:
            self.required_parameters.append(param)
    
    async def _execute_internal(self, **kwargs) -> Any:
        """执行命令行工具"""
        # 构建命令
        command = self.command_template.format(**kwargs)
        
        # 执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "command": command
            }
        except asyncio.TimeoutError:
            # 超时，终止进程
            process.terminate()
            await process.wait()
            raise

class WebServiceWrapper(BaseToolWrapper):
    """Web服务包装器"""
    
    def __init__(self, tool_id: str, name: str, description: str, 
                 base_url: str, endpoint: str, method: str = "GET"):
        super().__init__(tool_id, name, description)
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint.lstrip('/')
        self.method = method.upper()
        self.tool_type = ToolType.WEB_SERVICE
        
        # Web服务参数
        self.headers: Dict[str, str] = {}
        self.auth: Optional[tuple] = None
        self.required_parameters = ["data"] if method in ["POST", "PUT", "PATCH"] else []
    
    async def _execute_internal(self, **kwargs) -> Any:
        """调用Web服务"""
        try:
            import aiohttp
            
            url = f"{self.base_url}/{self.endpoint}"
            
            async with aiohttp.ClientSession() as session:
                request_params = {
                    "headers": self.headers,
                    "timeout": aiohttp.ClientTimeout(total=self.timeout)
                }
                
                if self.auth:
                    request_params["auth"] = aiohttp.BasicAuth(*self.auth)
                
                if self.method in ["POST", "PUT", "PATCH"]:
                    # 处理请求数据
                    data = kwargs.get("data", {})
                    request_params["json"] = data
                    
                    async with session.request(self.method, url, **request_params) as response:
                        response_data = await response.json()
                        return {
                            "status_code": response.status,
                            "data": response_data,
                            "headers": dict(response.headers)
                        }
                else:
                    # GET、DELETE等方法
                    params = kwargs.get("params", {})
                    request_params["params"] = params
                    
                    async with session.request(self.method, url, **request_params) as response:
                        response_data = await response.json()
                        return {
                            "status_code": response.status,
                            "data": response_data,
                            "headers": dict(response.headers)
                        }
                        
        except ImportError:
            logger.error("aiohttp未安装，无法调用Web服务")
            raise RuntimeError("aiohttp库未安装")
        except Exception as e:
            logger.error(f"Web服务调用失败: {e}")
            raise

class CompositeToolWrapper(BaseToolWrapper):
    """组合工具包装器"""
    
    def __init__(self, tool_id: str, name: str, description: str):
        super().__init__(tool_id, name, description)
        self.tool_type = ToolType.CUSTOM
        self.steps: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}
    
    def add_step(self, tool_wrapper: BaseToolWrapper, 
                 input_mapping: Dict[str, str],
                 output_variable: Optional[str] = None) -> None:
        """添加执行步骤"""
        step = {
            "tool": tool_wrapper,
            "input_mapping": input_mapping,
            "output_variable": output_variable
        }
        self.steps.append(step)
    
    async def _execute_internal(self, **kwargs) -> Any:
        """执行组合工具"""
        execution_context = kwargs.copy()
        results = []
        
        for i, step in enumerate(self.steps):
            tool_wrapper = step["tool"]
            input_mapping = step["input_mapping"]
            output_variable = step["output_variable"]
            
            # 构建步骤输入参数
            step_inputs = {}
            for param_name, context_key in input_mapping.items():
                if context_key in execution_context:
                    step_inputs[param_name] = execution_context[context_key]
                else:
                    raise ValueError(f"上下文中找不到参数: {context_key}")
            
            # 执行步骤
            logger.info(f"执行步骤 {i+1}: {tool_wrapper.name}")
            result = await tool_wrapper.execute(**step_inputs)
            results.append(result)
            
            # 如果步骤失败，停止执行
            if not result.success:
                return {
                    "success": False,
                    "failed_step": i + 1,
                    "error": result.error,
                    "results": [r.to_dict() for r in results]
                }
            
            # 保存输出到上下文
            if output_variable and result.output is not None:
                execution_context[output_variable] = result.output
        
        return {
            "success": True,
            "results": [r.to_dict() for r in results],
            "final_output": execution_context.get("final_output")
        }

class ToolWrapperFactory:
    """工具包装器工厂"""
    
    @staticmethod
    def create_from_function(function: Callable, 
                           name: Optional[str] = None,
                           description: Optional[str] = None) -> PythonFunctionWrapper:
        """从Python函数创建包装器"""
        tool_id = str(uuid.uuid4())
        tool_name = name or function.__name__
        tool_description = description or function.__doc__ or "无描述"
        
        return PythonFunctionWrapper(
            tool_id=tool_id,
            name=tool_name,
            description=tool_description,
            function=function
        )
    
    @staticmethod
    def create_from_command_line(command_template: str,
                               name: str,
                               description: str) -> CommandLineWrapper:
        """从命令行模板创建包装器"""
        tool_id = str(uuid.uuid4())
        
        return CommandLineWrapper(
            tool_id=tool_id,
            name=name,
            description=description,
            command_template=command_template
        )
    
    @staticmethod
    def create_from_web_service(base_url: str,
                              endpoint: str,
                              name: str,
                              description: str,
                              method: str = "GET") -> WebServiceWrapper:
        """从Web服务创建包装器"""
        tool_id = str(uuid.uuid4())
        
        return WebServiceWrapper(
            tool_id=tool_id,
            name=name,
            description=description,
            base_url=base_url,
            endpoint=endpoint,
            method=method
        )
    
    @staticmethod
    def create_composite_tool(name: str, description: str) -> CompositeToolWrapper:
        """创建组合工具包装器"""
        tool_id = str(uuid.uuid4())
        
        return CompositeToolWrapper(
            tool_id=tool_id,
            name=name,
            description=description
        )

class ToolExecutionManager:
    """工具执行管理器"""
    
    def __init__(self):
        self.wrappers: Dict[str, BaseToolWrapper] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
    
    def register_wrapper(self, wrapper: BaseToolWrapper) -> bool:
        """注册工具包装器"""
        try:
            if wrapper.tool_id in self.wrappers:
                logger.warning(f"工具已注册: {wrapper.tool_id}")
                return False
            
            self.wrappers[wrapper.tool_id] = wrapper
            logger.info(f"工具注册成功: {wrapper.name} ({wrapper.tool_id})")
            return True
        except Exception as e:
            logger.error(f"工具注册失败: {e}")
            return False
    
    def unregister_wrapper(self, tool_id: str) -> bool:
        """取消注册工具包装器"""
        try:
            if tool_id not in self.wrappers:
                return False
            
            del self.wrappers[tool_id]
            logger.info(f"工具取消注册: {tool_id}")
            return True
        except Exception as e:
            logger.error(f"工具取消注册失败: {e}")
            return False
    
    async def execute_tool(self, tool_id: str, **kwargs) -> ToolResult:
        """执行工具"""
        if tool_id not in self.wrappers:
            return ToolResult(
                success=False,
                output=None,
                error=f"工具未找到: {tool_id}"
            )
        
        wrapper = self.wrappers[tool_id]
        
        # 记录执行开始
        execution_id = str(uuid.uuid4())
        execution_record = {
            "execution_id": execution_id,
            "tool_id": tool_id,
            "tool_name": wrapper.name,
            "parameters": kwargs,
            "start_time": asyncio.get_event_loop().time(),
            "status": ExecutionStatus.RUNNING.value
        }
        self.execution_history.append(execution_record)
        
        # 执行工具
        result = await wrapper.execute(**kwargs)
        
        # 更新执行记录
        execution_record.update({
            "end_time": asyncio.get_event_loop().time(),
            "status": ExecutionStatus.COMPLETED.value if result.success else ExecutionStatus.FAILED.value,
            "success": result.success,
            "execution_time": result.execution_time,
            "error": result.error
        })
        
        # 清理历史记录
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size:]
        
        return result
    
    def get_wrapper_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """获取包装器信息"""
        if tool_id not in self.wrappers:
            return None
        
        return self.wrappers[tool_id].get_info()
    
    def list_wrappers(self, tool_type: Optional[ToolType] = None) -> List[Dict[str, Any]]:
        """列出所有包装器"""
        wrappers = []
        
        for wrapper in self.wrappers.values():
            if tool_type is None or wrapper.tool_type == tool_type:
                wrappers.append(wrapper.get_info())
        
        return wrappers
    
    def get_execution_history(self, tool_id: Optional[str] = None, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行历史"""
        history = self.execution_history.copy()
        
        if tool_id:
            history = [record for record in history if record["tool_id"] == tool_id]
        
        return history[-limit:]
    
    def search_wrappers(self, query: str) -> List[Dict[str, Any]]:
        """搜索包装器"""
        matching_wrappers = []
        query_lower = query.lower()
        
        for wrapper in self.wrappers.values():
            info = wrapper.get_info()
            
            # 在名称和描述中搜索
            if (query_lower in info["name"].lower() or 
                query_lower in info["description"].lower()):
                matching_wrappers.append(info)
        
        return matching_wrappers

# 示例工具函数
async def example_async_function(text: str, repeat: int = 1) -> str:
    """示例异步函数"""
    await asyncio.sleep(0.1)  # 模拟异步操作
    return text * repeat

def example_sync_function(number: int) -> Dict[str, Any]:
    """示例同步函数"""
    return {
        "square": number ** 2,
        "cube": number ** 3,
        "is_even": number % 2 == 0
    }

# 使用示例
async def demo():
    """演示工具包装器的使用"""
    factory = ToolWrapperFactory()
    manager = ToolExecutionManager()
    
    # 注册异步函数工具
    async_tool = factory.create_from_function(
        example_async_function,
        name="文本重复器",
        description="将文本重复指定次数"
    )
    manager.register_wrapper(async_tool)
    
    # 注册同步函数工具
    sync_tool = factory.create_from_function(
        example_sync_function,
        name="数字处理器",
        description="计算数字的平方、立方和奇偶性"
    )
    manager.register_wrapper(sync_tool)
    
    # 注册命令行工具
    cli_tool = factory.create_from_command_line(
        command_template="echo {message}",
        name="回声工具",
        description="在命令行中回显消息"
    )
    manager.register_wrapper(cli_tool)
    
    # 执行工具
    result1 = await manager.execute_tool(async_tool.tool_id, text="Hello", repeat=3)
    print("异步函数结果:", result1.to_dict())
    
    result2 = await manager.execute_tool(sync_tool.tool_id, number=5)
    print("同步函数结果:", result2.to_dict())
    
    result3 = await manager.execute_tool(cli_tool.tool_id, message="Hello World")
    print("命令行工具结果:", result3.to_dict())
    
    # 列出所有工具
    tools = manager.list_wrappers()
    print("所有工具:", tools)

if __name__ == "__main__":
    asyncio.run(demo())

