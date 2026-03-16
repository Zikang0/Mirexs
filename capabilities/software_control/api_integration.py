"""
API集成：第三方API集成
"""
import requests
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from urllib.parse import urlencode
import time

logger = logging.getLogger(__name__)

class APIAuthType(Enum):
    """API认证类型枚举"""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"

class HTTPMethod(Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

@dataclass
class APIEndpoint:
    """API端点定义"""
    name: str
    url: str
    method: HTTPMethod
    headers: Dict[str, str] = None
    parameters: Dict[str, Any] = None
    timeout: int = 30
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}
        if self.parameters is None:
            self.parameters = {}

@dataclass
class APIConfig:
    """API配置"""
    name: str
    base_url: str
    auth_type: APIAuthType
    auth_config: Dict[str, Any]
    endpoints: Dict[str, APIEndpoint]
    rate_limit: int = 100  # 每分钟请求数
    retry_attempts: int = 3
    timeout: int = 30
    
    def __post_init__(self):
        if self.auth_config is None:
            self.auth_config = {}

class APIResponse:
    """API响应"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, 
                 status_code: int = None, headers: Dict[str, str] = None):
        self.success = success
        self.data = data
        self.error = error
        self.status_code = status_code
        self.headers = headers or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'status_code': self.status_code,
            'headers': self.headers
        }

class APIIntegration:
    """API集成类"""
    
    def __init__(self):
        self.api_configs: Dict[str, APIConfig] = {}
        self.request_history: List[Dict[str, Any]] = []
        self.rate_limits: Dict[str, List[float]] = {}
        self._setup_logging()
        self._load_builtin_apis()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_builtin_apis(self):
        """加载内置API配置"""
        # OpenAI API配置
        openai_config = APIConfig(
            name="openai",
            base_url="https://api.openai.com/v1",
            auth_type=APIAuthType.BEARER_TOKEN,
            auth_config={"token": ""},
            endpoints={
                "chat_completion": APIEndpoint(
                    name="chat_completion",
                    url="/chat/completions",
                    method=HTTPMethod.POST,
                    headers={"Content-Type": "application/json"}
                ),
                "completion": APIEndpoint(
                    name="completion",
                    url="/completions",
                    method=HTTPMethod.POST,
                    headers={"Content-Type": "application/json"}
                )
            }
        )
        
        self.register_api(openai_config)
        
        # GitHub API配置
        github_config = APIConfig(
            name="github",
            base_url="https://api.github.com",
            auth_type=APIAuthType.BEARER_TOKEN,
            auth_config={"token": ""},
            endpoints={
                "user_repos": APIEndpoint(
                    name="user_repos",
                    url="/user/repos",
                    method=HTTPMethod.GET,
                    headers={"Accept": "application/vnd.github.v3+json"}
                ),
                "create_repo": APIEndpoint(
                    name="create_repo",
                    url="/user/repos",
                    method=HTTPMethod.POST,
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
            }
        )
        
        self.register_api(github_config)
    
    def register_api(self, api_config: APIConfig) -> bool:
        """注册API配置"""
        try:
            self.api_configs[api_config.name] = api_config
            self.rate_limits[api_config.name] = []
            logger.info(f"注册API: {api_config.name}")
            return True
        except Exception as e:
            logger.error(f"注册API失败: {str(e)}")
            return False
    
    def call_api(self, api_name: str, endpoint_name: str, 
                data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> APIResponse:
        """调用API"""
        try:
            if api_name not in self.api_configs:
                return APIResponse(False, error=f"API未注册: {api_name}")
            
            api_config = self.api_configs[api_name]
            
            if endpoint_name not in api_config.endpoints:
                return APIResponse(False, error=f"端点未找到: {endpoint_name}")
            
            endpoint = api_config.endpoints[endpoint_name]
            
            # 检查速率限制
            if not self._check_rate_limit(api_name, api_config.rate_limit):
                return APIResponse(False, error="速率限制 exceeded")
            
            # 准备请求
            url = api_config.base_url + endpoint.url
            headers = self._prepare_headers(api_config, endpoint)
            request_data = self._prepare_request_data(endpoint, data, params)
            
            # 发送请求（带重试）
            response = self._send_request_with_retry(
                endpoint.method, url, headers, request_data, 
                api_config.timeout, api_config.retry_attempts
            )
            
            # 记录请求历史
            self._record_request_history(api_name, endpoint_name, url, response)
            
            return response
            
        except Exception as e:
            logger.error(f"调用API失败 {api_name}.{endpoint_name}: {str(e)}")
            return APIResponse(False, error=str(e))
    
    def _check_rate_limit(self, api_name: str, rate_limit: int) -> bool:
        """检查速率限制"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # 清理过期的请求记录
        self.rate_limits[api_name] = [
            timestamp for timestamp in self.rate_limits[api_name] 
            if timestamp > one_minute_ago
        ]
        
        # 检查是否超过限制
        if len(self.rate_limits[api_name]) >= rate_limit:
            return False
        
        # 记录当前请求
        self.rate_limits[api_name].append(current_time)
        return True
    
    def _prepare_headers(self, api_config: APIConfig, endpoint: APIEndpoint) -> Dict[str, str]:
        """准备请求头"""
        headers = endpoint.headers.copy()
        
        # 添加认证头
        auth_headers = self._get_auth_headers(api_config)
        headers.update(auth_headers)
        
        return headers
    
    def _get_auth_headers(self, api_config: APIConfig) -> Dict[str, str]:
        """获取认证头"""
        auth_type = api_config.auth_type
        auth_config = api_config.auth_config
        
        if auth_type == APIAuthType.API_KEY:
            return {"X-API-Key": auth_config.get("api_key", "")}
        elif auth_type == APIAuthType.BEARER_TOKEN:
            return {"Authorization": f"Bearer {auth_config.get('token', '')}"}
        elif auth_type == APIAuthType.BASIC_AUTH:
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            return {"Authorization": f"Basic {credentials}"}
        elif auth_type == APIAuthType.OAUTH2:
            # OAuth2实现需要更复杂的逻辑
            return {"Authorization": f"Bearer {auth_config.get('access_token', '')}"}
        else:
            return {}
    
    def _prepare_request_data(self, endpoint: APIEndpoint, 
                            data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """准备请求数据"""
        request_data = {}
        
        # 合并参数
        if endpoint.parameters:
            request_data.update(endpoint.parameters)
        if params:
            request_data.update(params)
        if data:
            request_data.update(data)
        
        return request_data
    
    def _send_request_with_retry(self, method: HTTPMethod, url: str, headers: Dict[str, str],
                               data: Dict[str, Any], timeout: int, retry_attempts: int) -> APIResponse:
        """带重试的请求发送"""
        last_error = None
        
        for attempt in range(retry_attempts):
            try:
                response = self._send_request(method, url, headers, data, timeout)
                
                if response.success or attempt == retry_attempts - 1:
                    return response
                
                # 等待后重试
                time.sleep(2 ** attempt)  # 指数退避
                
            except Exception as e:
                last_error = str(e)
                if attempt == retry_attempts - 1:
                    return APIResponse(False, error=last_error)
                
                time.sleep(2 ** attempt)
        
        return APIResponse(False, error=last_error or "Unknown error")
    
    def _send_request(self, method: HTTPMethod, url: str, headers: Dict[str, str],
                     data: Dict[str, Any], timeout: int) -> APIResponse:
        """发送请求"""
        try:
            if method == HTTPMethod.GET:
                response = requests.get(url, headers=headers, params=data, timeout=timeout)
            elif method == HTTPMethod.POST:
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method == HTTPMethod.PUT:
                response = requests.put(url, headers=headers, json=data, timeout=timeout)
            elif method == HTTPMethod.DELETE:
                response = requests.delete(url, headers=headers, timeout=timeout)
            elif method == HTTPMethod.PATCH:
                response = requests.patch(url, headers=headers, json=data, timeout=timeout)
            else:
                return APIResponse(False, error=f"不支持的HTTP方法: {method}")
            
            # 处理响应
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text
                
                return APIResponse(
                    success=True,
                    data=response_data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            else:
                error_message = f"HTTP {response.status_code}: {response.text}"
                return APIResponse(
                    success=False,
                    error=error_message,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
                
        except requests.exceptions.Timeout:
            return APIResponse(False, error="请求超时")
        except requests.exceptions.ConnectionError:
            return APIResponse(False, error="连接错误")
        except Exception as e:
            return APIResponse(False, error=str(e))
    
    def _record_request_history(self, api_name: str, endpoint_name: str, 
                              url: str, response: APIResponse):
        """记录请求历史"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'api_name': api_name,
            'endpoint_name': endpoint_name,
            'url': url,
            'success': response.success,
            'status_code': response.status_code,
            'error': response.error
        }
        
        self.request_history.append(record)
        
        # 只保留最近1000条记录
        if len(self.request_history) > 1000:
            self.request_history.pop(0)
    
    def set_api_credentials(self, api_name: str, credentials: Dict[str, Any]) -> bool:
        """设置API凭据"""
        try:
            if api_name not in self.api_configs:
                return False
            
            api_config = self.api_configs[api_name]
            api_config.auth_config.update(credentials)
            
            logger.info(f"更新API凭据: {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"设置API凭据失败: {str(e)}")
            return False
    
    def get_request_history(self, api_name: str = None) -> List[Dict[str, Any]]:
        """获取请求历史"""
        if api_name:
            return [record for record in self.request_history if record['api_name'] == api_name]
        else:
            return self.request_history
    
    def test_api_connection(self, api_name: str) -> APIResponse:
        """测试API连接"""
        try:
            if api_name not in self.api_configs:
                return APIResponse(False, error=f"API未注册: {api_name}")
            
            api_config = self.api_configs[api_name]
            
            # 找一个简单的端点进行测试
            test_endpoint = None
            for endpoint in api_config.endpoints.values():
                if endpoint.method == HTTPMethod.GET:
                    test_endpoint = endpoint
                    break
            
            if not test_endpoint:
                return APIResponse(False, error="未找到合适的测试端点")
            
            return self.call_api(api_name, test_endpoint.name)
            
        except Exception as e:
            return APIResponse(False, error=str(e))
    
    def create_custom_endpoint(self, api_name: str, endpoint: APIEndpoint) -> bool:
        """创建自定义端点"""
        try:
            if api_name not in self.api_configs:
                return False
            
            api_config = self.api_configs[api_name]
            api_config.endpoints[endpoint.name] = endpoint
            
            logger.info(f"创建自定义端点: {api_name}.{endpoint.name}")
            return True
            
        except Exception as e:
            logger.error(f"创建自定义端点失败: {str(e)}")
            return False
    
    def batch_api_calls(self, calls: List[Dict[str, Any]]) -> List[APIResponse]:
        """批量API调用"""
        responses = []
        
        for call in calls:
            api_name = call.get('api_name')
            endpoint_name = call.get('endpoint_name')
            data = call.get('data')
            params = call.get('params')
            
            response = self.call_api(api_name, endpoint_name, data, params)
            responses.append(response)
            
            # 添加延迟以避免速率限制
            time.sleep(0.1)
        
        return responses
    
    def get_api_statistics(self, api_name: str = None) -> Dict[str, Any]:
        """获取API统计信息"""
        history = self.get_request_history(api_name)
        
        if not history:
            return {}
        
        total_requests = len(history)
        successful_requests = len([r for r in history if r['success']])
        failed_requests = total_requests - successful_requests
        
        status_codes = {}
        for record in history:
            status_code = record['status_code']
            status_codes[status_code] = status_codes.get(status_code, 0) + 1
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
            'status_codes': status_codes
        }

# 单例实例
_api_integration_instance = None

def get_api_integration() -> APIIntegration:
    """获取API集成单例"""
    global _api_integration_instance
    if _api_integration_instance is None:
        _api_integration_instance = APIIntegration()
    return _api_integration_instance

