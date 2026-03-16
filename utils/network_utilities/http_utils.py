"""
HTTP工具模块

提供HTTP请求、响应处理、API调用等功能
"""

import requests
import aiohttp
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
import logging
import time
import json
from urllib.parse import urljoin, urlparse, parse_qs
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import ssl
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTTPSession:
    """HTTP会话管理类"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, 
                 backoff_factor: float = 0.3, session_headers: Optional[Dict[str, str]] = None):
        """
        初始化HTTP会话
        
        Args:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            backoff_factor: 重试退避因子
            session_headers: 会话默认请求头
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session_headers = session_headers or {
            'User-Agent': 'HTTP-Tool/1.0',
            'Accept': 'application/json, text/html, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        # 创建会话
        self.session = requests.Session()
        self.session.headers.update(self.session_headers)
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            backoff_factor=backoff_factor
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
           headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            params: 查询参数
            headers: 请求头
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.get(
                url, 
                params=params, 
                headers=headers, 
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'content_type': response.headers.get('content-type', ''),
                'response_time': round(response_time, 3),
                'size': len(response.content),
                'encoding': response.encoding,
                'is_redirect': response.is_redirect,
                'redirect_history': [r.url for r in response.history],
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GET请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    def post(self, url: str, data: Optional[Union[Dict, str]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            data: 表单数据
            json_data: JSON数据
            headers: 请求头
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.post(
                url,
                data=data,
                json=json_data,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'content_type': response.headers.get('content-type', ''),
                'response_time': round(response_time, 3),
                'size': len(response.content),
                'encoding': response.encoding,
                'is_redirect': response.is_redirect,
                'redirect_history': [r.url for r in response.history],
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"POST请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    def put(self, url: str, data: Optional[Union[Dict, str]] = None,
           headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            data: 请求数据
            headers: 请求头
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.put(
                url,
                data=data,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'content_type': response.headers.get('content-type', ''),
                'response_time': round(response_time, 3),
                'size': len(response.content),
                'encoding': response.encoding,
                'is_redirect': response.is_redirect,
                'redirect_history': [r.url for r in response.history],
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PUT请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            headers: 请求头
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.delete(
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content': response.text,
                'content_type': response.headers.get('content-type', ''),
                'response_time': round(response_time, 3),
                'size': len(response.content),
                'encoding': response.encoding,
                'is_redirect': response.is_redirect,
                'redirect_history': [r.url for r in response.history],
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DELETE请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    def head(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> Dict[str, Any]:
        """
        发送HEAD请求
        
        Args:
            url: 请求URL
            headers: 请求头
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.head(
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': response.url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_time': round(response_time, 3),
                'size': None,  # HEAD请求不返回内容
                'is_redirect': response.is_redirect,
                'redirect_history': [r.url for r in response.history],
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HEAD请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    def download_file(self, url: str, local_path: str, 
                     chunk_size: int = 8192, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        下载文件
        
        Args:
            url: 文件URL
            local_path: 本地保存路径
            chunk_size: 块大小
            progress_callback: 进度回调函数
            
        Returns:
            下载结果字典
        """
        try:
            start_time = time.time()
            
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(progress, downloaded_size, total_size)
            
            download_time = time.time() - start_time
            
            return {
                'url': url,
                'local_path': local_path,
                'file_size': downloaded_size,
                'download_time': round(download_time, 3),
                'average_speed': round(downloaded_size / download_time / 1024, 2) if download_time > 0 else 0,
                'success': True,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"文件下载失败 {url}: {e}")
            return {
                'url': url,
                'local_path': local_path,
                'error': str(e),
                'success': False,
                'timestamp': time.time()
            }
    
    def close(self) -> None:
        """关闭会话"""
        self.session.close()


class AsyncHTTPSession:
    """异步HTTP会话管理类"""
    
    def __init__(self, timeout: int = 30, max_connections: int = 100):
        """
        初始化异步HTTP会话
        
        Args:
            timeout: 请求超时时间（秒）
            max_connections: 最大连接数
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_connections = max_connections
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=30,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
    
    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送异步GET请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            async with aiohttp.ClientSession(
                timeout=self.timeout,
                connector=self.connector
            ) as session:
                start_time = time.time()
                
                async with session.get(url, **kwargs) as response:
                    response_time = time.time() - start_time
                    content = await response.text()
                    
                    return {
                        'url': str(response.url),
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'content': content,
                        'content_type': response.headers.get('content-type', ''),
                        'response_time': round(response_time, 3),
                        'size': len(content.encode('utf-8')),
                        'encoding': response.get_encoding(),
                        'is_redirect': response.is_redirect,
                        'final_url': str(response.url),
                        'timestamp': time.time()
                    }
                    
        except Exception as e:
            logger.error(f"异步GET请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        发送异步POST请求
        
        Args:
            url: 请求URL
            **kwargs: 其他请求参数
            
        Returns:
            响应结果字典
        """
        try:
            async with aiohttp.ClientSession(
                timeout=self.timeout,
                connector=self.connector
            ) as session:
                start_time = time.time()
                
                async with session.post(url, **kwargs) as response:
                    response_time = time.time() - start_time
                    content = await response.text()
                    
                    return {
                        'url': str(response.url),
                        'status_code': response.status,
                        'headers': dict(response.headers),
                        'content': content,
                        'content_type': response.headers.get('content-type', ''),
                        'response_time': round(response_time, 3),
                        'size': len(content.encode('utf-8')),
                        'encoding': response.get_encoding(),
                        'is_redirect': response.is_redirect,
                        'final_url': str(response.url),
                        'timestamp': time.time()
                    }
                    
        except Exception as e:
            logger.error(f"异步POST请求失败 {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'status_code': None,
                'response_time': None,
                'timestamp': time.time()
            }
    
    async def bulk_requests(self, urls: List[str], method: str = 'GET', 
                           max_concurrent: int = 10, **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        批量异步请求
        
        Args:
            urls: URL列表
            method: 请求方法
            max_concurrent: 最大并发数
            **kwargs: 其他请求参数
            
        Returns:
            批量请求结果字典
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def make_request(url):
            async with semaphore:
                if method.upper() == 'GET':
                    return await self.get(url, **kwargs)
                elif method.upper() == 'POST':
                    return await self.post(url, **kwargs)
                else:
                    raise ValueError(f"不支持的请求方法: {method}")
        
        tasks = [make_request(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {url: result for url, result in zip(urls, results)}
    
    async def close(self) -> None:
        """关闭连接器"""
        await self.connector.close()


class APIHelper:
    """API辅助工具类"""
    
    def __init__(self, base_url: str, default_headers: Optional[Dict[str, str]] = None):
        """
        初始化API辅助工具
        
        Args:
            base_url: API基础URL
            default_headers: 默认请求头
        """
        self.base_url = base_url.rstrip('/')
        self.default_headers = default_headers or {'Content-Type': 'application/json'}
        self.session = HTTPSession()
    
    def build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        构建完整URL
        
        Args:
            endpoint: API端点
            params: 查询参数
            
        Returns:
            完整URL
        """
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        if params:
            from urllib.parse import urlencode
            query_string = urlencode(params)
            url += f'?{query_string}'
        
        return url
    
    def api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        API GET请求
        
        Args:
            endpoint: API端点
            params: 查询参数
            
        Returns:
            API响应结果
        """
        url = self.build_url(endpoint, params)
        headers = {'Accept': 'application/json'}
        headers.update(self.default_headers)
        
        return self.session.get(url, headers=headers)
    
    def api_post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        API POST请求
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            API响应结果
        """
        url = self.build_url(endpoint)
        headers = {'Content-Type': 'application/json'}
        headers.update(self.default_headers)
        
        json_data = json.dumps(data) if data else None
        
        return self.session.post(url, data=json_data, headers=headers)
    
    def api_put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        API PUT请求
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            API响应结果
        """
        url = self.build_url(endpoint)
        headers = {'Content-Type': 'application/json'}
        headers.update(self.default_headers)
        
        json_data = json.dumps(data) if data else None
        
        return self.session.put(url, data=json_data, headers=headers)
    
    def api_delete(self, endpoint: str) -> Dict[str, Any]:
        """
        API DELETE请求
        
        Args:
            endpoint: API端点
            
        Returns:
            API响应结果
        """
        url = self.build_url(endpoint)
        headers = {'Accept': 'application/json'}
        headers.update(self.default_headers)
        
        return self.session.delete(url, headers=headers)
    
    def parse_api_response(self, response: Dict[str, Any], expected_status: int = 200) -> Dict[str, Any]:
        """
        解析API响应
        
        Args:
            response: 原始响应
            expected_status: 期望的状态码
            
        Returns:
            解析后的响应
        """
        try:
            # 检查状态码
            if response.get('status_code') != expected_status:
                return {
                    'success': False,
                    'error': f"状态码不匹配: 期望 {expected_status}, 实际 {response.get('status_code')}",
                    'response': response
                }
            
            # 尝试解析JSON
            content_type = response.get('content_type', '').lower()
            if 'application/json' in content_type:
                try:
                    json_data = json.loads(response.get('content', '{}'))
                    return {
                        'success': True,
                        'data': json_data,
                        'status_code': response.get('status_code'),
                        'response_time': response.get('response_time'),
                        'timestamp': response.get('timestamp')
                    }
                except json.JSONDecodeError as e:
                    return {
                        'success': False,
                        'error': f"JSON解析失败: {e}",
                        'response': response
                    }
            else:
                return {
                    'success': True,
                    'data': response.get('content'),
                    'status_code': response.get('status_code'),
                    'response_time': response.get('response_time'),
                    'timestamp': response.get('timestamp')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"响应解析失败: {e}",
                'response': response
            }
    
    def close(self) -> None:
        """关闭会话"""
        self.session.close()


def test_website_speed(urls: List[str], max_workers: int = 5) -> Dict[str, Any]:
    """
    测试网站访问速度
    
    Args:
        urls: 要测试的URL列表
        max_workers: 最大并发数
        
    Returns:
        速度测试结果
    """
    try:
        session = HTTPSession()
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_url = {
                executor.submit(session.get, url): url
                for url in urls
            }
            
            # 收集结果
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results[url] = {
                        'status': 'success' if result.get('status_code') == 200 else 'failed',
                        'status_code': result.get('status_code'),
                        'response_time': result.get('response_time'),
                        'size': result.get('size'),
                        'error': result.get('error')
                    }
                except Exception as e:
                    results[url] = {
                        'status': 'error',
                        'error': str(e)
                    }
        
        session.close()
        
        # 计算统计信息
        successful_tests = [r for r in results.values() if r['status'] == 'success']
        response_times = [r['response_time'] for r in successful_tests if r['response_time']]
        
        summary = {
            'total_urls': len(urls),
            'successful_tests': len(successful_tests),
            'failed_tests': len(urls) - len(successful_tests),
            'success_rate': (len(successful_tests) / len(urls)) * 100,
            'average_response_time': round(sum(response_times) / len(response_times), 3) if response_times else None,
            'fastest_url': min(successful_tests, key=lambda x: x['response_time'])['response_time'] if successful_tests else None,
            'slowest_url': max(successful_tests, key=lambda x: x['response_time'])['response_time'] if successful_tests else None
        }
        
        return {
            'results': results,
            'summary': summary,
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"网站速度测试失败: {e}")
        raise


def check_website_status(urls: List[str]) -> Dict[str, Any]:
    """
    检查网站状态
    
    Args:
        urls: 要检查的URL列表
        
    Returns:
        网站状态检查结果
    """
    try:
        session = HTTPSession()
        results = {}
        
        for url in urls:
            try:
                # 使用HEAD请求检查状态
                result = session.head(url)
                results[url] = {
                    'status': 'online' if result.get('status_code') == 200 else 'offline',
                    'status_code': result.get('status_code'),
                    'response_time': result.get('response_time'),
                    'server': result.get('headers', {}).get('server'),
                    'content_type': result.get('headers', {}).get('content-type'),
                    'last_modified': result.get('headers', {}).get('last-modified')
                }
            except Exception as e:
                results[url] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        session.close()
        
        # 统计状态
        online_count = sum(1 for r in results.values() if r['status'] == 'online')
        offline_count = sum(1 for r in results.values() if r['status'] == 'offline')
        error_count = sum(1 for r in results.values() if r['status'] == 'error')
        
        return {
            'results': results,
            'summary': {
                'total_urls': len(urls),
                'online': online_count,
                'offline': offline_count,
                'error': error_count,
                'availability_rate': (online_count / len(urls)) * 100
            },
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"网站状态检查失败: {e}")
        raise


if __name__ == "__main__":
    # 示例用法
    print("HTTP工具模块")
    
    # 创建HTTP会话
    http_session = HTTPSession()
    
    # GET请求示例
    get_result = http_session.get('https://httpbin.org/get', params={'key': 'value'})
    print(f"GET请求状态码: {get_result['status_code']}")
    print(f"响应时间: {get_result['response_time']}秒")
    
    # POST请求示例
    post_result = http_session.post('https://httpbin.org/post', json_data={'name': 'test', 'value': 123})
    print(f"POST请求状态码: {post_result['status_code']}")
    
    # 网站状态检查
    urls = ['https://google.com', 'https://github.com', 'https://stackoverflow.com']
    status_results = check_website_status(urls)
    print(f"网站可用率: {status_results['summary']['availability_rate']:.1f}%")
    
    # 网站速度测试
    speed_results = test_website_speed(urls)
    print(f"平均响应时间: {speed_results['summary']['average_response_time']}秒")
    
    # API辅助工具示例
    api_helper = APIHelper('https://jsonplaceholder.typicode.com')
    api_result = api_helper.api_get('posts', params={'_limit': 5})
    parsed_result = api_helper.parse_api_response(api_result)
    print(f"API请求成功: {parsed_result['success']}")
    if parsed_result['success']:
        print(f"返回数据条数: {len(parsed_result['data'])}")
    
    # 异步HTTP示例
    async def async_example():
        async_session = AsyncHTTPSession()
        
        # 异步GET请求
        async_result = await async_session.get('https://httpbin.org/delay/1')
        print(f"异步请求状态码: {async_result['status_code']}")
        
        # 批量异步请求
        bulk_results = await async_session.bulk_requests(['https://httpbin.org/get', 'https://httpbin.org/post'], 'GET')
        print(f"批量请求完成: {len(bulk_results)} 个请求")
        
        await async_session.close()
    
    # 运行异步示例
    asyncio.run(async_example())
    
    # 关闭会话
    http_session.close()
    api_helper.close()
    
    print("HTTP工具示例完成")