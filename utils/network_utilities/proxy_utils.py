"""
代理工具模块

提供代理服务器管理、配置、测试等功能
"""

import socket
import threading
import time
import requests
from typing import Dict, List, Any, Optional, Union, Callable
import logging
import json
import subprocess
import os
from urllib.parse import urlparse
import ssl

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProxyManager:
    """代理管理器类"""
    
    def __init__(self):
        """初始化代理管理器"""
        self.proxy_list = []
        self.active_proxies = {}
        self.test_results = {}
    
    def add_proxy(self, proxy_info: Dict[str, Any]) -> bool:
        """
        添加代理服务器
        
        Args:
            proxy_info: 代理信息字典
            
        Returns:
            是否添加成功
        """
        try:
            required_fields = ['host', 'port', 'protocol']
            for field in required_fields:
                if field not in proxy_info:
                    logger.error(f"缺少必需字段: {field}")
                    return False
            
            # 验证代理信息
            if not self._validate_proxy_info(proxy_info):
                return False
            
            # 检查是否已存在
            proxy_key = f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}"
            for existing_proxy in self.proxy_list:
                existing_key = f"{existing_proxy['protocol']}://{existing_proxy['host']}:{existing_proxy['port']}"
                if proxy_key == existing_key:
                    logger.warning(f"代理已存在: {proxy_key}")
                    return False
            
            # 添加代理
            proxy_info['added_time'] = time.time()
            proxy_info['status'] = 'inactive'
            self.proxy_list.append(proxy_info)
            
            logger.info(f"添加代理成功: {proxy_key}")
            return True
            
        except Exception as e:
            logger.error(f"添加代理失败: {e}")
            return False
    
    def _validate_proxy_info(self, proxy_info: Dict[str, Any]) -> bool:
        """验证代理信息"""
        try:
            # 验证协议
            supported_protocols = ['http', 'https', 'socks4', 'socks5']
            if proxy_info['protocol'] not in supported_protocols:
                logger.error(f"不支持的协议: {proxy_info['protocol']}")
                return False
            
            # 验证端口
            port = proxy_info['port']
            if not isinstance(port, int) or port < 1 or port > 65535:
                logger.error(f"无效的端口号: {port}")
                return False
            
            # 验证主机
            host = proxy_info['host']
            if not isinstance(host, str) or not host.strip():
                logger.error(f"无效的主机地址: {host}")
                return False
            
            # 验证认证信息（如果提供）
            if 'username' in proxy_info and 'password' in proxy_info:
                if not isinstance(proxy_info['username'], str) or not isinstance(proxy_info['password'], str):
                    logger.error("用户名和密码必须是字符串")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"代理信息验证失败: {e}")
            return False
    
    def remove_proxy(self, host: str, port: int, protocol: str) -> bool:
        """
        移除代理服务器
        
        Args:
            host: 代理主机
            port: 代理端口
            protocol: 代理协议
            
        Returns:
            是否移除成功
        """
        try:
            proxy_key = f"{protocol}://{host}:{port}"
            
            for i, proxy in enumerate(self.proxy_list):
                existing_key = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
                if proxy_key == existing_key:
                    removed_proxy = self.proxy_list.pop(i)
                    
                    # 从活动代理中移除
                    if proxy_key in self.active_proxies:
                        del self.active_proxies[proxy_key]
                    
                    logger.info(f"移除代理成功: {proxy_key}")
                    return True
            
            logger.warning(f"代理不存在: {proxy_key}")
            return False
            
        except Exception as e:
            logger.error(f"移除代理失败: {e}")
            return False
    
    def get_proxy_list(self) -> List[Dict[str, Any]]:
        """
        获取代理列表
        
        Returns:
            代理列表
        """
        return self.proxy_list.copy()
    
    def test_proxy(self, proxy_info: Dict[str, Any], 
                  test_url: str = 'http://httpbin.org/ip',
                  timeout: int = 10) -> Dict[str, Any]:
        """
        测试代理服务器
        
        Args:
            proxy_info: 代理信息
            test_url: 测试URL
            timeout: 超时时间
            
        Returns:
            测试结果
        """
        try:
            # 构建代理URL
            proxy_url = self._build_proxy_url(proxy_info)
            
            # 设置代理
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # 测试代理
            start_time = time.time()
            
            try:
                response = requests.get(
                    test_url,
                    proxies=proxies,
                    timeout=timeout,
                    verify=False
                )
                
                response_time = time.time() - start_time
                
                # 解析响应
                if response.status_code == 200:
                    try:
                        ip_info = response.json()
                        proxy_ip = ip_info.get('origin', '')
                    except:
                        proxy_ip = response.text[:100]  # 取前100字符作为IP信息
                else:
                    proxy_ip = None
                
                result = {
                    'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                    'success': True,
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'proxy_ip': proxy_ip,
                    'test_url': test_url,
                    'timestamp': time.time()
                }
                
            except requests.exceptions.ProxyError:
                result = {
                    'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                    'success': False,
                    'error': 'Proxy connection failed',
                    'test_url': test_url,
                    'timestamp': time.time()
                }
                
            except requests.exceptions.Timeout:
                result = {
                    'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                    'success': False,
                    'error': 'Connection timeout',
                    'test_url': test_url,
                    'timestamp': time.time()
                }
                
            except Exception as e:
                result = {
                    'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                    'success': False,
                    'error': str(e),
                    'test_url': test_url,
                    'timestamp': time.time()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"代理测试失败: {e}")
            return {
                'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _build_proxy_url(self, proxy_info: Dict[str, Any]) -> str:
        """构建代理URL"""
        protocol = proxy_info['protocol']
        host = proxy_info['host']
        port = proxy_info['port']
        
        if 'username' in proxy_info and 'password' in proxy_info:
            username = proxy_info['username']
            password = proxy_info['password']
            return f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            return f"{protocol}://{host}:{port}"
    
    def test_all_proxies(self, test_url: str = 'http://httpbin.org/ip',
                        timeout: int = 10, max_workers: int = 5) -> Dict[str, Any]:
        """
        测试所有代理
        
        Args:
            test_url: 测试URL
            timeout: 超时时间
            max_workers: 最大并发数
            
        Returns:
            测试结果汇总
        """
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            results = {}
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交测试任务
                future_to_proxy = {
                    executor.submit(self.test_proxy, proxy, test_url, timeout): proxy
                    for proxy in self.proxy_list
                }
                
                # 收集结果
                for future in as_completed(future_to_proxy):
                    proxy = future_to_proxy[future]
                    try:
                        result = future.result()
                        proxy_key = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
                        results[proxy_key] = result
                        
                        # 更新代理状态
                        proxy['status'] = 'active' if result['success'] else 'inactive'
                        proxy['last_test_time'] = time.time()
                        
                    except Exception as e:
                        logger.error(f"代理测试异常 {proxy}: {e}")
            
            # 计算统计信息
            successful_proxies = sum(1 for r in results.values() if r['success'])
            total_proxies = len(results)
            response_times = [r['response_time'] for r in results.values() 
                            if r['success'] and 'response_time' in r]
            
            summary = {
                'total_proxies': total_proxies,
                'successful_proxies': successful_proxies,
                'failed_proxies': total_proxies - successful_proxies,
                'success_rate': (successful_proxies / total_proxies) * 100 if total_proxies > 0 else 0,
                'average_response_time': sum(response_times) / len(response_times) if response_times else None,
                'fastest_proxy': min(results.values(), key=lambda x: x.get('response_time', float('inf')))['proxy'] if successful_proxies > 0 else None,
                'test_url': test_url
            }
            
            self.test_results['last_test'] = {
                'results': results,
                'summary': summary,
                'timestamp': time.time()
            }
            
            return self.test_results['last_test']
            
        except Exception as e:
            logger.error(f"批量代理测试失败: {e}")
            raise
    
    def get_working_proxies(self) -> List[Dict[str, Any]]:
        """
        获取可用的代理列表
        
        Returns:
            可用代理列表
        """
        working_proxies = []
        
        for proxy in self.proxy_list:
            if proxy.get('status') == 'active':
                working_proxies.append(proxy)
        
        return working_proxies
    
    def rotate_proxy(self, proxy_list: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """
        轮换代理
        
        Args:
            proxy_list: 指定代理列表，None则使用所有可用代理
            
        Returns:
            轮换到的代理
        """
        try:
            if proxy_list is None:
                proxy_list = self.get_working_proxies()
            
            if not proxy_list:
                return None
            
            # 简单轮换策略：返回列表中的下一个代理
            # 这里可以扩展为更复杂的轮换算法
            current_time = int(time.time())
            index = current_time % len(proxy_list)
            
            return proxy_list[index]
            
        except Exception as e:
            logger.error(f"代理轮换失败: {e}")
            return None
    
    def configure_system_proxy(self, proxy_info: Dict[str, Any], 
                              enable: bool = True) -> bool:
        """
        配置系统代理
        
        Args:
            proxy_info: 代理信息
            enable: 是否启用
            
        Returns:
            是否配置成功
        """
        try:
            proxy_url = self._build_proxy_url(proxy_info)
            
            # 根据操作系统设置代理
            system = os.name
            
            if system == 'nt':  # Windows
                if enable:
                    subprocess.run([
                        'reg', 'add', 
                        'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings',
                        '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '1', '/f'
                    ], check=True)
                    
                    subprocess.run([
                        'reg', 'add',
                        'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings',
                        '/v', 'ProxyServer', '/t', 'REG_SZ', '/d', proxy_url, '/f'
                    ], check=True)
                else:
                    subprocess.run([
                        'reg', 'add',
                        'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings',
                        '/v', 'ProxyEnable', '/t', 'REG_DWORD', '/d', '0', '/f'
                    ], check=True)
            
            elif system == 'posix':  # Linux/Mac
                if enable:
                    # 设置环境变量
                    os.environ['http_proxy'] = proxy_url
                    os.environ['https_proxy'] = proxy_url
                    os.environ['HTTP_PROXY'] = proxy_url
                    os.environ['HTTPS_PROXY'] = proxy_url
                else:
                    # 清除环境变量
                    for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
                        os.environ.pop(var, None)
            
            else:
                logger.warning(f"不支持的操作系统: {system}")
                return False
            
            logger.info(f"系统代理配置{'启用' if enable else '禁用'}: {proxy_url}")
            return True
            
        except Exception as e:
            logger.error(f"系统代理配置失败: {e}")
            return False
    
    def create_proxy_pool(self, proxy_list: List[Dict[str, Any]], 
                         max_size: int = 100) -> 'ProxyPool':
        """
        创建代理池
        
        Args:
            proxy_list: 代理列表
            max_size: 最大池大小
            
        Returns:
            代理池实例
        """
        return ProxyPool(proxy_list, max_size)


class ProxyPool:
    """代理池类"""
    
    def __init__(self, proxies: List[Dict[str, Any]], max_size: int = 100):
        """
        初始化代理池
        
        Args:
            proxies: 代理列表
            max_size: 最大池大小
        """
        self.proxies = proxies
        self.max_size = max_size
        self.current_index = 0
        self.working_proxies = []
        self.failed_proxies = []
        self.lock = threading.Lock()
    
    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        获取代理
        
        Returns:
            代理信息或None
        """
        with self.lock:
            if not self.working_proxies:
                return None
            
            proxy = self.working_proxies[self.current_index % len(self.working_proxies)]
            self.current_index = (self.current_index + 1) % len(self.working_proxies)
            return proxy
    
    def mark_proxy_failed(self, proxy: Dict[str, Any]) -> None:
        """
        标记代理失败
        
        Args:
            proxy: 失败的代理
        """
        with self.lock:
            if proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
                self.failed_proxies.append(proxy)
    
    def mark_proxy_success(self, proxy: Dict[str, Any]) -> None:
        """
        标记代理成功
        
        Args:
            proxy: 成功的代理
        """
        with self.lock:
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
                if proxy not in self.working_proxies:
                    self.working_proxies.append(proxy)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取池统计信息
        
        Returns:
            统计信息
        """
        with self.lock:
            return {
                'total_proxies': len(self.proxies),
                'working_proxies': len(self.working_proxies),
                'failed_proxies': len(self.failed_proxies),
                'pool_utilization': len(self.working_proxies) / self.max_size * 100 if self.max_size > 0 else 0
            }


class ProxyChecker:
    """代理检查器类"""
    
    def __init__(self):
        """初始化代理检查器"""
        self.check_results = {}
    
    def check_proxy_anonymity(self, proxy_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查代理匿名性
        
        Args:
            proxy_info: 代理信息
            
        Returns:
            匿名性检查结果
        """
        try:
            from requests import get
            
            proxy_url = self._build_proxy_url(proxy_info)
            proxies = {'http': proxy_url, 'https': proxy_url}
            
            # 测试不同级别的匿名性
            test_urls = {
                'basic': 'http://httpbin.org/ip',
                'headers': 'http://httpbin.org/headers',
                'user_agent': 'http://httpbin.org/user-agent'
            }
            
            results = {}
            
            for test_type, test_url in test_urls.items():
                try:
                    response = get(test_url, proxies=proxies, timeout=10, verify=False)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if test_type == 'basic':
                            proxy_ip = data.get('origin', '')
                            results[test_type] = {
                                'success': True,
                                'proxy_ip': proxy_ip,
                                'is_anonymous': ',' in proxy_ip  # 多个IP表示可能透明代理
                            }
                        
                        elif test_type == 'headers':
                            headers = data.get('headers', {})
                            results[test_type] = {
                                'success': True,
                                'headers': headers,
                                'has_proxy_headers': any('proxy' in key.lower() for key in headers.keys())
                            }
                        
                        elif test_type == 'user_agent':
                            user_agent = data.get('user-agent', '')
                            results[test_type] = {
                                'success': True,
                                'user_agent': user_agent,
                                'is_preserved': 'requests' not in user_agent.lower()
                            }
                    
                    else:
                        results[test_type] = {
                            'success': False,
                            'error': f'HTTP {response.status_code}'
                        }
                
                except Exception as e:
                    results[test_type] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # 综合评估匿名性
            overall_anonymity = self._assess_anonymity(results)
            
            return {
                'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                'anonymity_level': overall_anonymity,
                'test_results': results,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"代理匿名性检查失败: {e}")
            return {
                'proxy': f"{proxy_info['protocol']}://{proxy_info['host']}:{proxy_info['port']}",
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _assess_anonymity(self, test_results: Dict[str, Any]) -> str:
        """评估匿名性等级"""
        try:
            basic_result = test_results.get('basic', {})
            headers_result = test_results.get('headers', {})
            
            if not basic_result.get('success', False):
                return 'unknown'
            
            # 检查是否为透明代理
            if basic_result.get('is_anonymous', True) == False:
                return 'transparent'
            
            # 检查是否泄露代理信息
            if headers_result.get('has_proxy_headers', False):
                return 'transparent'
            
            # 检查是否为高匿名代理
            user_agent_result = test_results.get('user_agent', {})
            if user_agent_result.get('is_preserved', True):
                return 'high_anonymous'
            else:
                return 'anonymous'
                
        except Exception:
            return 'unknown'
    
    def _build_proxy_url(self, proxy_info: Dict[str, Any]) -> str:
        """构建代理URL"""
        protocol = proxy_info['protocol']
        host = proxy_info['host']
        port = proxy_info['port']
        
        if 'username' in proxy_info and 'password' in proxy_info:
            username = proxy_info['username']
            password = proxy_info['password']
            return f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            return f"{protocol}://{host}:{port}"


class ProxyServer:
    """简单的代理服务器类"""
    
    def __init__(self, listen_host: str = '127.0.0.1', listen_port: int = 8080):
        """
        初始化代理服务器
        
        Args:
            listen_host: 监听主机
            listen_port: 监听端口
        """
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.server_socket = None
        self.running = False
        self.client_connections = 0
    
    def start(self) -> bool:
        """
        启动代理服务器
        
        Returns:
            是否启动成功
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.listen_host, self.listen_port))
            self.server_socket.listen(5)
            
            self.running = True
            
            logger.info(f"代理服务器启动: {self.listen_host}:{self.listen_port}")
            
            # 启动主循环
            self._main_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"代理服务器启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止代理服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("代理服务器已停止")
    
    def _main_loop(self) -> None:
        """主循环"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()
                
                self.client_connections += 1
                
                # 为每个客户端连接创建新线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"代理服务器错误: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """
        处理客户端连接
        
        Args:
            client_socket: 客户端socket
            client_address: 客户端地址
        """
        try:
            # 接收HTTP请求
            request = client_socket.recv(4096).decode('utf-8', errors='ignore')
            
            if not request:
                return
            
            # 解析请求
            lines = request.split('\r\n')
            if not lines:
                return
            
            request_line = lines[0]
            parts = request_line.split(' ')
            
            if len(parts) < 3:
                return
            
            method = parts[0]
            url = parts[1]
            version = parts[2]
            
            # 解析目标服务器
            target_url = self._parse_target_url(url)
            if not target_url:
                self._send_error_response(client_socket, 400, "Bad Request")
                return
            
            # 建立到目标服务器的连接
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(10)
            
            try:
                target_socket.connect((target_url['host'], target_url['port']))
                
                # 转发请求
                target_socket.send(request.encode('utf-8'))
                
                # 转发响应
                while True:
                    response_data = target_socket.recv(4096)
                    if not response_data:
                        break
                    
                    client_socket.send(response_data)
                
            except Exception as e:
                logger.error(f"目标服务器连接失败: {e}")
                self._send_error_response(client_socket, 502, "Bad Gateway")
            
            finally:
                target_socket.close()
        
        except Exception as e:
            logger.error(f"客户端处理错误: {e}")
        
        finally:
            client_socket.close()
    
    def _parse_target_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        解析目标URL
        
        Args:
            url: URL字符串
            
        Returns:
            解析结果
        """
        try:
            if url.startswith('http://'):
                parsed = urlparse(url)
                return {
                    'scheme': 'http',
                    'host': parsed.hostname,
                    'port': parsed.port or 80,
                    'path': parsed.path,
                    'query': parsed.query
                }
            else:
                # 假设是相对路径，需要从Host头部获取服务器信息
                return None
                
        except Exception as e:
            logger.error(f"URL解析失败: {e}")
            return None
    
    def _send_error_response(self, client_socket: socket.socket, 
                           status_code: int, message: str) -> None:
        """
        发送错误响应
        
        Args:
            client_socket: 客户端socket
            status_code: 状态码
            message: 错误消息
        """
        try:
            response = f"HTTP/1.1 {status_code} {message}\r\n\r\n"
            client_socket.send(response.encode('utf-8'))
        except Exception as e:
            logger.error(f"发送错误响应失败: {e}")


def load_proxy_list_from_file(filename: str) -> List[Dict[str, Any]]:
    """
    从文件加载代理列表
    
    Args:
        filename: 文件名
        
    Returns:
        代理列表
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        else:
            logger.error("文件格式错误：应为代理列表")
            return []
            
    except Exception as e:
        logger.error(f"加载代理列表失败: {e}")
        return []


def save_proxy_list_to_file(proxies: List[Dict[str, Any]], filename: str) -> bool:
    """
    保存代理列表到文件
    
    Args:
        proxies: 代理列表
        filename: 文件名
        
    Returns:
        是否保存成功
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(proxies, f, indent=2, ensure_ascii=False)
        
        logger.info(f"代理列表已保存到: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"保存代理列表失败: {e}")
        return False


if __name__ == "__main__":
    # 示例用法
    print("代理工具模块")
    
    # 创建代理管理器
    manager = ProxyManager()
    
    # 添加代理
    proxy1 = {
        'host': '127.0.0.1',
        'port': 8080,
        'protocol': 'http'
    }
    
    proxy2 = {
        'host': 'proxy.example.com',
        'port': 1080,
        'protocol': 'socks5',
        'username': 'user',
        'password': 'pass'
    }
    
    manager.add_proxy(proxy1)
    manager.add_proxy(proxy2)
    
    print(f"添加代理数量: {len(manager.get_proxy_list())}")
    
    # 测试代理
    test_result = manager.test_proxy(proxy1)
    print(f"代理测试结果: {'成功' if test_result['success'] else '失败'}")
    
    # 批量测试
    try:
        bulk_results = manager.test_all_proxies()
        print(f"批量测试成功率: {bulk_results['summary']['success_rate']:.1f}%")
    except:
        print("批量测试需要网络连接")
    
    # 创建代理池
    working_proxies = manager.get_working_proxies()
    if working_proxies:
        proxy_pool = manager.create_proxy_pool(working_proxies)
        stats = proxy_pool.get_stats()
        print(f"代理池统计: {stats}")
    
    # 代理匿名性检查
    checker = ProxyChecker()
    try:
        anonymity_result = checker.check_proxy_anonymity(proxy1)
        print(f"代理匿名性: {anonymity_result['anonymity_level']}")
    except:
        print("匿名性检查需要网络连接")
    
    # 简单代理服务器示例
    try:
        proxy_server = ProxyServer('127.0.0.1', 8888)
        print("启动简单代理服务器...")
        # proxy_server.start()  # 注释掉以避免阻塞
    except:
        print("代理服务器启动失败")
    
    # 文件操作示例
    proxies = [proxy1, proxy2]
    save_proxy_list_to_file(proxies, 'proxy_list.json')
    loaded_proxies = load_proxy_list_from_file('proxy_list.json')
    print(f"从文件加载代理数量: {len(loaded_proxies)}")
    
    print("代理工具示例完成")