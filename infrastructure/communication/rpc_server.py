"""
RPC服务端：远程过程调用服务端
负责处理RPC请求和执行相应的方法
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
from aiohttp import web

class RPCServerStatus(Enum):
    """RPC服务端状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"

@dataclass
class RPCMethod:
    """RPC方法"""
    name: str
    handler: Callable
    is_async: bool
    description: str = ""

@dataclass
class RPCRequest:
    """RPC请求（服务端视角）"""
    request_id: str
    method: str
    params: Dict[str, Any]
    client_ip: str
    received_at: datetime

@dataclass
class RPCResponse:
    """RPC响应（服务端视角）"""
    request_id: str
    result: Any
    error: Optional[str]
    processed_at: datetime

class RPCServer:
    """RPC服务端"""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.methods: Dict[str, RPCMethod] = {}
        self.server: Optional[web.Server] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self.status = RPCServerStatus.STOPPED
        self.request_stats: Dict[str, int] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化RPC服务端"""
        if self.initialized:
            return
            
        logging.info("初始化RPC服务端...")
        
        # 注册内置方法
        await self._register_builtin_methods()
        
        self.initialized = True
        logging.info("RPC服务端初始化完成")
    
    async def _register_builtin_methods(self):
        """注册内置RPC方法"""
        await self.register_method("ping", self._ping_method, "服务健康检查")
        await self.register_method("list_methods", self._list_methods, "列出所有可用方法")
        await self.register_method("get_stats", self._get_stats, "获取服务端统计")
    
    async def register_method(self, method_name: str, handler: Callable, description: str = ""):
        """注册RPC方法"""
        is_async = asyncio.iscoroutinefunction(handler)
        
        method = RPCMethod(
            name=method_name,
            handler=handler,
            is_async=is_async,
            description=description
        )
        
        self.methods[method_name] = method
        logging.debug(f"RPC方法注册: {method_name}")
    
    async def unregister_method(self, method_name: str):
        """注销RPC方法"""
        if method_name in self.methods:
            del self.methods[method_name]
            logging.debug(f"RPC方法注销: {method_name}")
    
    async def start(self):
        """启动RPC服务端"""
        if self.status == RPCServerStatus.RUNNING:
            logging.warning("RPC服务端已在运行")
            return
        
        logging.info(f"启动RPC服务端: {self.host}:{self.port}")
        self.status = RPCServerStatus.STARTING
        
        # 创建Web应用
        app = web.Application()
        app.router.add_post('/rpc', self._handle_rpc_request)
        app.router.add_get('/health', self._handle_health_check)
        
        # 创建服务器
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        self.status = RPCServerStatus.RUNNING
        logging.info(f"RPC服务端启动成功: {self.host}:{self.port}")
    
    async def stop(self):
        """停止RPC服务端"""
        if self.status != RPCServerStatus.RUNNING:
            return
        
        logging.info("停止RPC服务端...")
        self.status = RPCServerStatus.STOPPING
        
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        
        self.status = RPCServerStatus.STOPPED
        logging.info("RPC服务端已停止")
    
    async def _handle_rpc_request(self, request: web.Request) -> web.Response:
        """处理RPC请求"""
        client_ip = request.remote
        request_time = datetime.now()
        
        try:
            # 解析请求数据
            data = await request.json()
            
            # 处理单个请求或批量请求
            if isinstance(data, list):
                responses = await self._handle_batch_request(data, client_ip, request_time)
            else:
                responses = await self._handle_single_request(data, client_ip, request_time)
            
            return web.json_response(responses)
            
        except json.JSONDecodeError:
            error_response = self._create_error_response(None, -32700, "Parse error")
            return web.json_response(error_response, status=400)
        except Exception as e:
            logging.error(f"RPC请求处理错误: {e}")
            error_response = self._create_error_response(None, -32603, "Internal error")
            return web.json_response(error_response, status=500)
    
    async def _handle_single_request(self, data: Dict[str, Any], client_ip: str, 
                                   request_time: datetime) -> Dict[str, Any]:
        """处理单个RPC请求"""
        request_id = data.get("id")
        method_name = data.get("method")
        params = data.get("params", {})
        
        # 验证请求
        if not method_name:
            return self._create_error_response(request_id, -32600, "Invalid Request")
        
        # 记录请求统计
        self.request_stats[method_name] = self.request_stats.get(method_name, 0) + 1
        
        # 查找方法
        if method_name not in self.methods:
            return self._create_error_response(request_id, -32601, "Method not found")
        
        method = self.methods[method_name]
        
        try:
            # 执行方法
            if method.is_async:
                result = await method.handler(params)
            else:
                result = method.handler(params)
            
            # 创建成功响应
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logging.error(f"RPC方法执行错误 {method_name}: {e}")
            return self._create_error_response(request_id, -32603, f"Internal error: {str(e)}")
    
    async def _handle_batch_request(self, data: List[Dict[str, Any]], client_ip: str,
                                  request_time: datetime) -> List[Dict[str, Any]]:
        """处理批量RPC请求"""
        responses = []
        
        for request_data in data:
            response = await self._handle_single_request(request_data, client_ip, request_time)
            responses.append(response)
        
        return responses
    
    def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """处理健康检查请求"""
        health_status = {
            "status": "healthy",
            "service": "rpc_server",
            "timestamp": datetime.now().isoformat(),
            "methods_registered": len(self.methods),
            "total_requests": sum(self.request_stats.values())
        }
        
        return web.json_response(health_status)
    
    # 内置RPC方法
    async def _ping_method(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Ping方法"""
        return {"message": "pong", "timestamp": datetime.now().isoformat()}
    
    async def _list_methods(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出所有方法"""
        methods_info = []
        for name, method in self.methods.items():
            methods_info.append({
                "name": name,
                "description": method.description,
                "is_async": method.is_async
            })
        
        return {"methods": methods_info}
    
    async def _get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "status": self.status.value,
            "methods_registered": len(self.methods),
            "request_stats": self.request_stats,
            "total_requests": sum(self.request_stats.values())
        }
    
    def get_server_stats(self) -> Dict[str, Any]:
        """获取服务端统计"""
        return {
            "status": self.status.value,
            "host": self.host,
            "port": self.port,
            "methods_registered": len(self.methods),
            "request_stats": self.request_stats,
            "total_requests": sum(self.request_stats.values())
        }

# 全局RPC服务端实例
rpc_server = RPCServer()