"""
RPC客户端：远程过程调用客户端
负责发起RPC调用和处理响应
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import aiohttp

class RPCStatus(Enum):
    """RPC状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class RPCRequest:
    """RPC请求"""
    request_id: str
    method: str
    params: Dict[str, Any]
    endpoint: str
    timeout: float
    created_at: datetime

@dataclass
class RPCResponse:
    """RPC响应"""
    request_id: str
    result: Any
    error: Optional[str]
    completed_at: datetime

class RPCClient:
    """RPC客户端"""
    
    def __init__(self):
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.pending_requests: Dict[str, RPCRequest] = {}
        self.response_handlers: Dict[str, asyncio.Future] = {}
        self.initialized = False
        
    async def initialize(self):
        """初始化RPC客户端"""
        if self.initialized:
            return
            
        logging.info("初始化RPC客户端...")
        
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        self.initialized = True
        logging.info("RPC客户端初始化完成")
    
    async def call(self, endpoint: str, method: str, params: Dict[str, Any] = None,
                  timeout: float = 30.0) -> Any:
        """发起RPC调用"""
        if not self.initialized or not self.http_session:
            raise RuntimeError("RPC客户端未初始化")
        
        request_id = str(uuid.uuid4())
        
        request = RPCRequest(
            request_id=request_id,
            method=method,
            params=params or {},
            endpoint=endpoint,
            timeout=timeout,
            created_at=datetime.now()
        )
        
        # 创建响应Future
        response_future = asyncio.Future()
        self.response_handlers[request_id] = response_future
        self.pending_requests[request_id] = request
        
        try:
            # 发送RPC请求
            await self._send_request(request)
            
            # 等待响应
            try:
                response = await asyncio.wait_for(response_future, timeout)
                return response.result
                
            except asyncio.TimeoutError:
                logging.error(f"RPC调用超时: {method} -> {endpoint}")
                raise TimeoutError(f"RPC调用超时: {method}")
                
        finally:
            # 清理
            if request_id in self.response_handlers:
                del self.response_handlers[request_id]
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
    
    async def _send_request(self, request: RPCRequest):
        """发送RPC请求"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": request.request_id,
                "method": request.method,
                "params": request.params
            }
            
            async with self.http_session.post(
                request.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    await self._handle_response(result)
                else:
                    error_msg = f"HTTP错误: {response.status}"
                    await self._handle_error(request.request_id, error_msg)
                    
        except Exception as e:
            error_msg = f"RPC请求失败: {str(e)}"
            await self._handle_error(request.request_id, error_msg)
    
    async def _handle_response(self, response_data: Dict[str, Any]):
        """处理RPC响应"""
        request_id = response_data.get("id")
        if not request_id or request_id not in self.response_handlers:
            logging.warning(f"未知的RPC响应ID: {request_id}")
            return
        
        future = self.response_handlers[request_id]
        
        if "error" in response_data:
            error = response_data["error"]
            future.set_exception(RuntimeError(f"RPC错误: {error}"))
        else:
            result = response_data.get("result")
            response = RPCResponse(
                request_id=request_id,
                result=result,
                error=None,
                completed_at=datetime.now()
            )
            future.set_result(response)
    
    async def _handle_error(self, request_id: str, error_msg: str):
        """处理RPC错误"""
        if request_id in self.response_handlers:
            future = self.response_handlers[request_id]
            future.set_exception(RuntimeError(error_msg))
    
    async def batch_call(self, endpoint: str, calls: List[Dict[str, Any]], 
                        timeout: float = 30.0) -> List[Any]:
        """批量RPC调用"""
        if not calls:
            return []
        
        # 为每个调用创建请求
        requests = []
        futures = []
        
        for call in calls:
            request_id = str(uuid.uuid4())
            method = call["method"]
            params = call.get("params", {})
            
            request = RPCRequest(
                request_id=request_id,
                method=method,
                params=params,
                endpoint=endpoint,
                timeout=timeout,
                created_at=datetime.now()
            )
            
            future = asyncio.Future()
            self.response_handlers[request_id] = future
            self.pending_requests[request_id] = request
            
            requests.append(request)
            futures.append(future)
        
        try:
            # 发送批量请求
            await self._send_batch_request(endpoint, requests)
            
            # 等待所有响应
            responses = await asyncio.gather(*futures, return_exceptions=True)
            
            # 处理响应
            results = []
            for response in responses:
                if isinstance(response, Exception):
                    results.append({"error": str(response)})
                else:
                    results.append({"result": response.result})
            
            return results
            
        finally:
            # 清理
            for request in requests:
                if request.request_id in self.response_handlers:
                    del self.response_handlers[request.request_id]
                if request.request_id in self.pending_requests:
                    del self.pending_requests[request.request_id]
    
    async def _send_batch_request(self, endpoint: str, requests: List[RPCRequest]):
        """发送批量RPC请求"""
        try:
            payload = []
            for request in requests:
                payload.append({
                    "jsonrpc": "2.0",
                    "id": request.request_id,
                    "method": request.method,
                    "params": request.params
                })
            
            async with self.http_session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    results = await response.json()
                    for result in results:
                        await self._handle_response(result)
                else:
                    error_msg = f"批量RPC HTTP错误: {response.status}"
                    for request in requests:
                        await self._handle_error(request.request_id, error_msg)
                        
        except Exception as e:
            error_msg = f"批量RPC请求失败: {str(e)}"
            for request in requests:
                await self._handle_error(request.request_id, error_msg)
    
    def get_client_stats(self) -> Dict[str, Any]:
        """获取客户端统计"""
        return {
            "pending_requests": len(self.pending_requests),
            "active_handlers": len(self.response_handlers),
            "requests": [
                {
                    "id": req.request_id,
                    "method": req.method,
                    "endpoint": req.endpoint,
                    "created_at": req.created_at.isoformat()
                }
                for req in self.pending_requests.values()
            ]
        }
    
    async def cleanup(self):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()
        
        # 取消所有待处理的请求
        for future in self.response_handlers.values():
            if not future.done():
                future.set_exception(RuntimeError("RPC客户端关闭"))
        
        self.pending_requests.clear()
        self.response_handlers.clear()

# 全局RPC客户端实例
rpc_client = RPCClient()