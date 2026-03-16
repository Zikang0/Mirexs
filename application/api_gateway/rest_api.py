"""
RESTful API模块 - Mirexs API网关

提供REST API接口功能，包括：
1. 路由管理
2. 请求处理
3. 响应生成
4. 中间件支持
5. 错误处理
6. 版本控制
"""

import logging
import time
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, Awaitable, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import inspect

logger = logging.getLogger(__name__)

# 尝试导入FastAPI
try:
    from fastapi import FastAPI, Request, Response, HTTPException, Depends
    from fastapi.routing import APIRoute
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.warning("FastAPI not available. REST API functionality will be limited.")

class HTTPMethod(Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class APIStatus(Enum):
    """API状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class APIEndpoint:
    """API端点"""
    path: str
    method: HTTPMethod
    handler: Callable
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    auth_required: bool = False
    rate_limit: Optional[str] = None
    response_model: Optional[Any] = None
    deprecated: bool = False

@dataclass
class APIRouter:
    """API路由器"""
    prefix: str
    endpoints: List[APIEndpoint] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    dependencies: List[Callable] = field(default_factory=list)

@dataclass
class APIConfig:
    """API配置"""
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # API配置
    title: str = "Mirexs API"
    version: str = "1.0.0"
    description: str = "Mirexs数字生命体API接口"
    
    # 跨域配置
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # 安全配置
    secret_key: str = "mirexs-secret-key-change-in-production"
    token_expire_minutes: int = 30
    
    # 性能配置
    gzip_enabled: bool = True
    gzip_min_size: int = 1000  # 字节
    
    # 文档配置
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

class RESTAPI:
    """
    REST API管理器
    
    负责REST API的路由、处理和文档生成。
    """
    
    def __init__(self, config: Optional[APIConfig] = None):
        """
        初始化REST API管理器
        
        Args:
            config: API配置
        """
        self.config = config or APIConfig()
        
        # FastAPI应用
        self.app = None
        self._init_app()
        
        # 路由器
        self.routers: Dict[str, APIRouter] = {}
        
        # 中间件
        self.middlewares: List[Callable] = []
        
        # 端点统计
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}
        
        # 服务器实例
        self.server = None
        self.server_task = None
        
        # 状态
        self.status = APIStatus.STOPPED
        
        # 回调函数
        self.on_startup: Optional[Callable] = None
        self.on_shutdown: Optional[Callable] = None
        self.on_request: Optional[Callable] = None
        self.on_response: Optional[Callable] = None
        self.on_error: Optional[Callable[[str, Exception], None]] = None
        
        logger.info(f"RESTAPI initialized for {self.config.title} v{self.config.version}")
    
    def _init_app(self):
        """初始化FastAPI应用"""
        if not FASTAPI_AVAILABLE:
            logger.warning("FastAPI not available, using mock implementation")
            self.app = None
            return
        
        self.app = FastAPI(
            title=self.config.title,
            version=self.config.version,
            description=self.config.description,
            docs_url=self.config.docs_url,
            redoc_url=self.config.redoc_url,
            openapi_url=self.config.openapi_url,
            on_startup=[self._on_startup],
            on_shutdown=[self._on_shutdown]
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_methods=self.config.cors_methods,
            allow_headers=self.config.cors_headers,
            allow_credentials=True
        )
        
        # 添加GZip中间件
        if self.config.gzip_enabled:
            self.app.add_middleware(
                GZipMiddleware,
                minimum_size=self.config.gzip_min_size
            )
        
        # 添加请求中间件
        @self.app.middleware("http")
        async def request_middleware(request: Request, call_next):
            start_time = time.time()
            
            # 记录请求
            if self.on_request:
                await self._call_handler(self.on_request, request)
            
            # 处理请求
            try:
                response = await call_next(request)
                
                # 记录响应时间
                process_time = time.time() - start_time
                response.headers["X-Process-Time"] = str(process_time)
                
                # 更新统计
                self._update_stats(request.url.path, request.method, response.status_code, process_time)
                
                # 记录响应
                if self.on_response:
                    await self._call_handler(self.on_response, request, response, process_time)
                
                return response
                
            except Exception as e:
                logger.error(f"Request error: {e}")
                
                if self.on_error:
                    await self._call_handler(self.on_error, request.url.path, e)
                
                raise
        
        logger.debug("FastAPI app initialized")
    
    async def _call_handler(self, handler: Callable, *args, **kwargs):
        """调用处理器（支持同步和异步）"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        else:
            return handler(*args, **kwargs)
    
    def _on_startup(self):
        """启动回调"""
        logger.info("API server starting up")
        self.status = APIStatus.RUNNING
        
        if self.on_startup:
            self.on_startup()
    
    def _on_shutdown(self):
        """关闭回调"""
        logger.info("API server shutting down")
        self.status = APIStatus.STOPPED
        
        if self.on_shutdown:
            self.on_shutdown()
    
    def _update_stats(self, path: str, method: str, status_code: int, process_time: float):
        """更新端点统计"""
        key = f"{method}:{path}"
        
        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = {
                "path": path,
                "method": method,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "last_request": None
            }
        
        stats = self.endpoint_stats[key]
        stats["total_requests"] += 1
        stats["total_time"] += process_time
        stats["min_time"] = min(stats["min_time"], process_time)
        stats["max_time"] = max(stats["max_time"], process_time)
        stats["last_request"] = datetime.now().isoformat()
        
        if 200 <= status_code < 300:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
    
    def register_router(self, router: APIRouter):
        """
        注册路由器
        
        Args:
            router: API路由器
        """
        if not FASTAPI_AVAILABLE or not self.app:
            logger.warning("FastAPI not available, skipping router registration")
            return
        
        self.routers[router.prefix] = router
        
        # 创建FastAPI路由器
        from fastapi import APIRouter as FastAPIRouter
        
        fastapi_router = FastAPIRouter(
            prefix=router.prefix,
            tags=router.tags,
            dependencies=router.dependencies
        )
        
        # 注册端点
        for endpoint in router.endpoints:
            self._register_endpoint(fastapi_router, endpoint)
        
        # 包含路由器
        self.app.include_router(fastapi_router)
        
        logger.info(f"Router registered: {router.prefix} with {len(router.endpoints)} endpoints")
    
    def _register_endpoint(self, router, endpoint: APIEndpoint):
        """注册端点"""
        method = endpoint.method.value.lower()
        
        # 创建路径操作装饰器参数
        kwargs = {
            "path": endpoint.path,
            "methods": [method],
            "summary": endpoint.summary,
            "description": endpoint.description,
            "tags": endpoint.tags,
            "response_model": endpoint.response_model,
            "deprecated": endpoint.deprecated
        }
        
        # 添加认证依赖
        if endpoint.auth_required:
            # 这里添加认证依赖
            pass
        
        # 注册端点
        router.add_api_route(
            path=endpoint.path,
            endpoint=endpoint.handler,
            **kwargs
        )
        
        logger.debug(f"Endpoint registered: {endpoint.method.value} {endpoint.path}")
    
    def register_endpoint(self, endpoint: APIEndpoint, router_prefix: str = ""):
        """
        注册单个端点
        
        Args:
            endpoint: API端点
            router_prefix: 路由器前缀
        """
        if not FASTAPI_AVAILABLE or not self.app:
            logger.warning("FastAPI not available, skipping endpoint registration")
            return
        
        if router_prefix:
            path = f"{router_prefix}{endpoint.path}"
        else:
            path = endpoint.path
        
        method = endpoint.method.value.lower()
        
        self.app.add_api_route(
            path=path,
            endpoint=endpoint.handler,
            methods=[method],
            summary=endpoint.summary,
            description=endpoint.description,
            tags=endpoint.tags,
            response_model=endpoint.response_model,
            deprecated=endpoint.deprecated
        )
        
        logger.debug(f"Endpoint registered: {endpoint.method.value} {path}")
    
    def create_router(self, prefix: str, tags: Optional[List[str]] = None) -> APIRouter:
        """
        创建路由器
        
        Args:
            prefix: 路由前缀
            tags: 标签列表
        
        Returns:
            API路由器
        """
        router = APIRouter(
            prefix=prefix,
            tags=tags or []
        )
        
        self.register_router(router)
        
        return router
    
    def get(self, path: str, **kwargs):
        """GET方法装饰器"""
        def decorator(func):
            endpoint = APIEndpoint(
                path=path,
                method=HTTPMethod.GET,
                handler=func,
                **kwargs
            )
            self.register_endpoint(endpoint)
            return func
        return decorator
    
    def post(self, path: str, **kwargs):
        """POST方法装饰器"""
        def decorator(func):
            endpoint = APIEndpoint(
                path=path,
                method=HTTPMethod.POST,
                handler=func,
                **kwargs
            )
            self.register_endpoint(endpoint)
            return func
        return decorator
    
    def put(self, path: str, **kwargs):
        """PUT方法装饰器"""
        def decorator(func):
            endpoint = APIEndpoint(
                path=path,
                method=HTTPMethod.PUT,
                handler=func,
                **kwargs
            )
            self.register_endpoint(endpoint)
            return func
        return decorator
    
    def delete(self, path: str, **kwargs):
        """DELETE方法装饰器"""
        def decorator(func):
            endpoint = APIEndpoint(
                path=path,
                method=HTTPMethod.DELETE,
                handler=func,
                **kwargs
            )
            self.register_endpoint(endpoint)
            return func
        return decorator
    
    def patch(self, path: str, **kwargs):
        """PATCH方法装饰器"""
        def decorator(func):
            endpoint = APIEndpoint(
                path=path,
                method=HTTPMethod.PATCH,
                handler=func,
                **kwargs
            )
            self.register_endpoint(endpoint)
            return func
        return decorator
    
    async def start(self):
        """启动API服务器"""
        if self.status == APIStatus.RUNNING:
            logger.warning("API server already running")
            return
        
        if not FASTAPI_AVAILABLE or not self.app:
            logger.error("Cannot start API server: FastAPI not available")
            return
        
        logger.info(f"Starting API server on {self.config.host}:{self.config.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info" if self.config.debug else "warning"
        )
        
        self.server = uvicorn.Server(config)
        self.server_task = asyncio.create_task(self.server.serve())
        
        self.status = APIStatus.RUNNING
    
    async def stop(self):
        """停止API服务器"""
        if self.status != APIStatus.RUNNING:
            return
        
        logger.info("Stopping API server")
        
        if self.server:
            self.server.should_exit = True
            if self.server_task:
                await self.server_task
        
        self.status = APIStatus.STOPPED
    
    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        获取端点统计
        
        Args:
            endpoint: 端点路径
        
        Returns:
            统计信息
        """
        if endpoint:
            return {k: v for k, v in self.endpoint_stats.items() if endpoint in k}
        return self.endpoint_stats
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取API状态
        
        Returns:
            状态字典
        """
        return {
            "status": self.status.value,
            "title": self.config.title,
            "version": self.config.version,
            "host": self.config.host,
            "port": self.config.port,
            "endpoints": {
                "total": sum(len(r.endpoints) for r in self.routers.values()),
                "routers": len(self.routers)
            },
            "stats": {
                "total_requests": sum(s["total_requests"] for s in self.endpoint_stats.values()),
                "endpoints": len(self.endpoint_stats)
            },
            "docs_url": self.config.docs_url,
            "openapi_url": self.config.openapi_url
        }

# 单例模式实现
_rest_api_instance: Optional[RESTAPI] = None

def get_rest_api(config: Optional[APIConfig] = None) -> RESTAPI:
    """
    获取REST API管理器单例
    
    Args:
        config: API配置
    
    Returns:
        REST API管理器实例
    """
    global _rest_api_instance
    if _rest_api_instance is None:
        _rest_api_instance = RESTAPI(config)
    return _rest_api_instance

