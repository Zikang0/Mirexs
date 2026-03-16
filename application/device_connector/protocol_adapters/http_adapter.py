"""
HTTP适配器模块 - Mirexs协议适配器

提供HTTP协议支持，包括：
1. HTTP客户端
2. 请求管理
3. 响应处理
4. 会话管理
5. 认证支持
6. 重试机制
"""

import logging
import time
import json
import threading
from typing import Optional, Dict, Any, List, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
import uuid
from urllib.parse import urljoin, urlencode

logger = logging.getLogger(__name__)

# 尝试导入HTTP库
try:
    import requests
    from requests.adapters import HTTPAdapter as RequestsHTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests not available. HTTP functionality will be limited.")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp not available. Async HTTP functionality will be limited.")

class HTTPMethod(Enum):
    """HTTP方法枚举"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class HTTPAuthType(Enum):
    """HTTP认证类型枚举"""
    NONE = "none"
    BASIC = "basic"
    DIGEST = "digest"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    CUSTOM = "custom"

class HTTPStatus(Enum):
    """HTTP状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class HTTPRequest:
    """HTTP请求"""
    id: str
    method: HTTPMethod
    url: str
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    data: Any = None
    json: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    timeout: int = 30
    allow_redirects: bool = True
    auth: Optional[tuple] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    verify: bool = True
    cert: Optional[Union[str, tuple]] = None
    created_at: float = field(default_factory=time.time)

@dataclass
class HTTPResponse:
    """HTTP响应"""
    request_id: str
    status_code: int
    headers: Dict[str, str]
    data: Any
    elapsed: float
    success: bool
    error: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    url: Optional[str] = None
    encoding: Optional[str] = None

@dataclass
class HTTPConfig:
    """HTTP配置"""
    # 基础配置
    base_url: str = ""
    default_timeout: int = 30
    max_redirects: int = 10
    
    # 重试配置
    max_retries: int = 3
    retry_backoff: float = 1.0
    retry_status_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
    retry_methods: List[str] = field(default_factory=lambda: ["GET", "HEAD", "OPTIONS"])
    
    # 认证配置
    auth_type: HTTPAuthType = HTTPAuthType.NONE
    auth_credentials: Optional[Dict[str, Any]] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"
    
    # 会话配置
    pool_connections: int = 10
    pool_maxsize: int = 10
    pool_block: bool = False
    
    # 代理配置
    proxies: Dict[str, str] = field(default_factory=dict)
    
    # 默认头部
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mirexs/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    })
    
    # SSL配置
    verify_ssl: bool = True
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    
    # 缓存配置
    cache_enabled: bool = False
    cache_ttl: int = 300  # 秒
    cache_max_size: int = 100

class HTTPAdapter:
    """
    HTTP适配器
    
    负责HTTP协议的请求发送和响应处理。
    """
    
    def __init__(self, config: Optional[HTTPConfig] = None):
        """
        初始化HTTP适配器
        
        Args:
            config: HTTP配置
        """
        self.config = config or HTTPConfig()
        
        # HTTP会话
        self.session: Optional[requests.Session] = None
        self._init_session()
        
        # 请求跟踪
        self.requests: Dict[str, HTTPRequest] = {}
        self.responses: Dict[str, HTTPResponse] = {}
        
        # 缓存
        self.cache: Dict[str, tuple] = {}  # url -> (response, expiry)
        
        # 回调函数
        self.on_request: Optional[Callable[[HTTPRequest], None]] = None
        self.on_response: Optional[Callable[[HTTPResponse], None]] = None
        self.on_error: Optional[Callable[[str, str], None]] = None
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "avg_response_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info("HTTPAdapter initialized")
    
    def _init_session(self):
        """初始化HTTP会话"""
        if not REQUESTS_AVAILABLE:
            logger.warning("requests not available, HTTP session disabled")
            return
        
        try:
            self.session = requests.Session()
            
            # 设置适配器
            adapter = RequestsHTTPAdapter(
                pool_connections=self.config.pool_connections,
                pool_maxsize=self.config.pool_maxsize,
                max_retries=Retry(
                    total=self.config.max_retries,
                    backoff_factor=self.config.retry_backoff,
                    status_forcelist=self.config.retry_status_codes,
                    allowed_methods=self.config.retry_methods
                )
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
            
            # 设置默认头部
            self.session.headers.update(self.config.default_headers)
            
            # 设置代理
            if self.config.proxies:
                self.session.proxies.update(self.config.proxies)
            
            # 设置认证
            self._setup_auth()
            
            logger.debug("HTTP session initialized")
            
        except Exception as e:
            logger.error(f"Error initializing HTTP session: {e}")
            self.session = None
    
    def _setup_auth(self):
        """设置认证"""
        if not self.session:
            return
        
        if self.config.auth_type == HTTPAuthType.BASIC:
            if self.config.auth_credentials:
                username = self.config.auth_credentials.get('username')
                password = self.config.auth_credentials.get('password')
                if username and password:
                    self.session.auth = (username, password)
        
        elif self.config.auth_type == HTTPAuthType.BEARER:
            if self.config.token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.config.token}'
                })
        
        elif self.config.auth_type == HTTPAuthType.API_KEY:
            if self.config.api_key:
                self.session.headers.update({
                    self.config.api_key_header: self.config.api_key
                })
    
    def _get_cache_key(self, method: HTTPMethod, url: str, params: Dict) -> str:
        """获取缓存键"""
        key_parts = [method.value, url, json.dumps(params, sort_keys=True)]
        return hashlib.md5(''.join(key_parts).encode()).hexdigest()
    
    def _check_cache(self, key: str) -> Optional[HTTPResponse]:
        """检查缓存"""
        if not self.config.cache_enabled:
            return None
        
        if key in self.cache:
            response, expiry = self.cache[key]
            if time.time() < expiry:
                self.stats["cache_hits"] += 1
                return response
            else:
                del self.cache[key]
        
        self.stats["cache_misses"] += 1
        return None
    
    def _add_to_cache(self, key: str, response: HTTPResponse):
        """添加到缓存"""
        if not self.config.cache_enabled:
            return
        
        # 只缓存成功的GET请求
        if response.success:
            expiry = time.time() + self.config.cache_ttl
            self.cache[key] = (response, expiry)
            
            # 限制缓存大小
            if len(self.cache) > self.config.cache_max_size:
                # 移除最早的项
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
    
    def request(self, method: HTTPMethod, url: str, **kwargs) -> HTTPResponse:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 请求参数
        
        Returns:
            HTTP响应
        """
        # 构建完整URL
        if self.config.base_url:
            url = urljoin(self.config.base_url, url)
        
        # 创建请求对象
        request_id = str(uuid.uuid4())
        
        request = HTTPRequest(
            id=request_id,
            method=method,
            url=url,
            params=kwargs.get('params', {}),
            headers={**self.session.headers, **kwargs.get('headers', {})} if self.session else kwargs.get('headers', {}),
            data=kwargs.get('data'),
            json=kwargs.get('json'),
            files=kwargs.get('files'),
            timeout=kwargs.get('timeout', self.config.default_timeout),
            allow_redirects=kwargs.get('allow_redirects', True),
            auth=kwargs.get('auth'),
            cookies=kwargs.get('cookies', {}),
            verify=kwargs.get('verify', self.config.verify_ssl),
            cert=kwargs.get('cert', self.config.ssl_cert)
        )
        
        self.requests[request_id] = request
        self.stats["total_requests"] += 1
        
        # 检查缓存
        cache_key = self._get_cache_key(method, url, request.params)
        cached_response = self._check_cache(cache_key)
        if cached_response:
            return cached_response
        
        if self.on_request:
            self.on_request(request)
        
        start_time = time.time()
        
        try:
            if not REQUESTS_AVAILABLE:
                raise Exception("requests library not available")
            
            if not self.session:
                raise Exception("HTTP session not initialized")
            
            # 发送请求
            response = self.session.request(
                method=method.value,
                url=url,
                params=request.params,
                data=request.data,
                json=request.json,
                files=request.files,
                headers=request.headers,
                cookies=request.cookies,
                auth=request.auth,
                timeout=request.timeout,
                allow_redirects=request.allow_redirects,
                verify=request.verify,
                cert=request.cert
            )
            
            elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
            
            # 解析响应
            try:
                data = response.json()
            except:
                data = response.text
            
            http_response = HTTPResponse(
                request_id=request_id,
                status_code=response.status_code,
                headers=dict(response.headers),
                data=data,
                elapsed=elapsed,
                success=200 <= response.status_code < 300,
                cookies=dict(response.cookies),
                url=response.url,
                encoding=response.encoding
            )
            
            self.responses[request_id] = http_response
            
            if http_response.success:
                self.stats["successful_requests"] += 1
                # 添加到缓存
                if method == HTTPMethod.GET:
                    self._add_to_cache(cache_key, http_response)
            else:
                self.stats["failed_requests"] += 1
            
            # 更新统计
            self.stats["avg_response_time"] = (
                (self.stats["avg_response_time"] * (self.stats["total_requests"] - 1) + elapsed) /
                self.stats["total_requests"]
            )
            
            if request.data:
                self.stats["total_bytes_sent"] += len(str(request.data))
            if request.json:
                self.stats["total_bytes_sent"] += len(json.dumps(request.json))
            
            self.stats["total_bytes_received"] += len(str(response.content))
            
            logger.debug(f"Request {request_id} completed in {elapsed:.2f}ms: {response.status_code}")
            
            if self.on_response:
                self.on_response(http_response)
            
            return http_response
            
        except requests.Timeout:
            error_msg = f"Request timeout after {request.timeout}s"
            logger.error(error_msg)
            self.stats["failed_requests"] += 1
            self.stats["errors"] = self.stats.get("errors", 0) + 1
            
            http_response = HTTPResponse(
                request_id=request_id,
                status_code=0,
                headers={},
                data=None,
                elapsed=(time.time() - start_time) * 1000,
                success=False,
                error=error_msg
            )
            
            if self.on_error:
                self.on_error(request_id, error_msg)
            
            return http_response
            
        except requests.ConnectionError as e:
            error_msg = f"Connection error: {e}"
            logger.error(error_msg)
            self.stats["failed_requests"] += 1
            self.stats["errors"] = self.stats.get("errors", 0) + 1
            
            http_response = HTTPResponse(
                request_id=request_id,
                status_code=0,
                headers={},
                data=None,
                elapsed=(time.time() - start_time) * 1000,
                success=False,
                error=error_msg
            )
            
            if self.on_error:
                self.on_error(request_id, error_msg)
            
            return http_response
            
        except Exception as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            self.stats["failed_requests"] += 1
            self.stats["errors"] = self.stats.get("errors", 0) + 1
            
            http_response = HTTPResponse(
                request_id=request_id,
                status_code=0,
                headers={},
                data=None,
                elapsed=(time.time() - start_time) * 1000,
                success=False,
                error=error_msg
            )
            
            if self.on_error:
                self.on_error(request_id, error_msg)
            
            return http_response
    
    def get(self, url: str, **kwargs) -> HTTPResponse:
        """GET请求"""
        return self.request(HTTPMethod.GET, url, **kwargs)
    
    def post(self, url: str, **kwargs) -> HTTPResponse:
        """POST请求"""
        return self.request(HTTPMethod.POST, url, **kwargs)
    
    def put(self, url: str, **kwargs) -> HTTPResponse:
        """PUT请求"""
        return self.request(HTTPMethod.PUT, url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> HTTPResponse:
        """DELETE请求"""
        return self.request(HTTPMethod.DELETE, url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> HTTPResponse:
        """PATCH请求"""
        return self.request(HTTPMethod.PATCH, url, **kwargs)
    
    def head(self, url: str, **kwargs) -> HTTPResponse:
        """HEAD请求"""
        return self.request(HTTPMethod.HEAD, url, **kwargs)
    
    def options(self, url: str, **kwargs) -> HTTPResponse:
        """OPTIONS请求"""
        return self.request(HTTPMethod.OPTIONS, url, **kwargs)
    
    def download(self, url: str, filepath: str, **kwargs) -> bool:
        """
        下载文件
        
        Args:
            url: 文件URL
            filepath: 保存路径
            **kwargs: 请求参数
        
        Returns:
            是否成功
        """
        try:
            if not self.session:
                raise Exception("HTTP session not initialized")
            
            response = self.session.get(url, stream=True, **kwargs)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"File downloaded to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False
    
    def upload(self, url: str, filepath: str, **kwargs) -> HTTPResponse:
        """
        上传文件
        
        Args:
            url: 上传URL
            filepath: 文件路径
            **kwargs: 请求参数
        
        Returns:
            HTTP响应
        """
        try:
            with open(filepath, 'rb') as f:
                files = {'file': (filepath, f)}
                return self.post(url, files=files, **kwargs)
                
        except Exception as e:
            logger.error(f"Upload error: {e}")
            error_response = HTTPResponse(
                request_id=str(uuid.uuid4()),
                status_code=0,
                headers={},
                data=None,
                elapsed=0,
                success=False,
                error=str(e)
            )
            return error_response
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_request(self, request_id: str) -> Optional[HTTPRequest]:
        """获取请求信息"""
        return self.requests.get(request_id)
    
    def get_response(self, request_id: str) -> Optional[HTTPResponse]:
        """获取响应信息"""
        return self.responses.get(request_id)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取HTTP适配器状态
        
        Returns:
            状态字典
        """
        return {
            "available": REQUESTS_AVAILABLE,
            "base_url": self.config.base_url,
            "auth_type": self.config.auth_type.value,
            "stats": self.stats,
            "cache": {
                "enabled": self.config.cache_enabled,
                "size": len(self.cache),
                "max_size": self.config.cache_max_size
            },
            "session": {
                "active": self.session is not None,
                "headers": dict(self.session.headers) if self.session else {}
            }
        }
    
    def shutdown(self):
        """关闭HTTP适配器"""
        logger.info("Shutting down HTTPAdapter...")
        
        if self.session:
            self.session.close()
        
        self.requests.clear()
        self.responses.clear()
        self.cache.clear()
        
        logger.info("HTTPAdapter shutdown completed")

# 单例模式实现
_http_adapter_instance: Optional[HTTPAdapter] = None

def get_http_adapter(config: Optional[HTTPConfig] = None) -> HTTPAdapter:
    """
    获取HTTP适配器单例
    
    Args:
        config: HTTP配置
    
    Returns:
        HTTP适配器实例
    """
    global _http_adapter_instance
    if _http_adapter_instance is None:
        _http_adapter_instance = HTTPAdapter(config)
    return _http_adapter_instance

