"""
Socket工具模块

提供Socket编程、网络通信等功能
"""

import socket
import threading
import time
import ssl
import struct
from typing import Dict, List, Any, Optional, Union, Callable
import logging
import select

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SocketManager:
    """Socket管理器"""
    
    def __init__(self):
        self.connections = {}
        self.listeners = {}
    
    def create_tcp_socket(self, host: str = '', port: int = 0, backlog: int = 5) -> socket.socket:
        """创建TCP Socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(backlog)
        return sock
    
    def create_udp_socket(self, host: str = '', port: int = 0) -> socket.socket:
        """创建UDP Socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, port))
        return sock
    
    def connect_tcp(self, host: str, port: int, timeout: float = 10.0) -> socket.socket:
        """TCP连接"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        return sock
    
    def send_data(self, sock: socket.socket, data: Union[str, bytes]) -> bool:
        """发送数据"""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            total_sent = 0
            while total_sent < len(data):
                sent = sock.send(data[total_sent:])
                if sent == 0:
                    return False
                total_sent += sent
            return True
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            return False
    
    def receive_data(self, sock: socket.socket, buffer_size: int = 4096, timeout: Optional[float] = None) -> Optional[bytes]:
        """接收数据"""
        try:
            if timeout:
                sock.settimeout(timeout)
            
            data = sock.recv(buffer_size)
            return data if data else None
        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"接收数据失败: {e}")
            return None
    
    def close_socket(self, sock: socket.socket) -> None:
        """关闭Socket"""
        try:
            sock.close()
        except:
            pass


class TCPServer:
    """TCP服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.client_handlers = {}
        self.message_handlers = {}
    
    def start(self) -> bool:
        """启动服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            
            logger.info(f"TCP服务器启动: {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"TCP服务器启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 关闭所有客户端连接
        for client_socket in list(self.client_handlers.keys()):
            try:
                client_socket.close()
            except:
                pass
    
    def _accept_connections(self) -> None:
        """接受连接"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()
                
                # 为每个客户端启动处理线程
                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                handler_thread.start()
                
                self.client_handlers[client_socket] = handler_thread
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接错误: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """处理客户端"""
        try:
            logger.info(f"新连接: {client_address}")
            
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # 处理接收到的数据
                response = self._process_message(data, client_address)
                
                if response:
                    client_socket.send(response)
        
        except Exception as e:
            logger.error(f"客户端处理错误 {client_address}: {e}")
        
        finally:
            try:
                client_socket.close()
                if client_socket in self.client_handlers:
                    del self.client_handlers[client_socket]
                logger.info(f"连接关闭: {client_address}")
            except:
                pass
    
    def _process_message(self, data: bytes, client_address: tuple) -> Optional[bytes]:
        """处理消息"""
        try:
            # 默认回显处理
            response = b"Echo: " + data
            
            # 调用自定义消息处理器
            for handler in self.message_handlers.values():
                try:
                    result = handler(data, client_address)
                    if result:
                        response = result
                        break
                except Exception as e:
                    logger.error(f"消息处理器错误: {e}")
            
            return response
        except Exception as e:
            logger.error(f"消息处理错误: {e}")
            return None
    
    def add_message_handler(self, name: str, handler: Callable) -> None:
        """添加消息处理器"""
        self.message_handlers[name] = handler


class UDPServer:
    """UDP服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.udp_socket = None
        self.running = False
        self.message_handlers = {}
    
    def start(self) -> bool:
        """启动UDP服务器"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((self.host, self.port))
            
            self.running = True
            
            logger.info(f"UDP服务器启动: {self.host}:{self.port}")
            
            # 启动接收线程
            receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            receive_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"UDP服务器启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止UDP服务器"""
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
    
    def _receive_messages(self) -> None:
        """接收消息"""
        while self.running:
            try:
                self.udp_socket.settimeout(1.0)
                data, client_address = self.udp_socket.recvfrom(4096)
                
                # 处理消息
                response = self._process_message(data, client_address)
                
                # 发送响应
                if response:
                    self.udp_socket.sendto(response, client_address)
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP消息接收错误: {e}")
    
    def _process_message(self, data: bytes, client_address: tuple) -> Optional[bytes]:
        """处理消息"""
        try:
            # 默认回显处理
            response = b"Echo: " + data
            
            # 调用自定义消息处理器
            for handler in self.message_handlers.values():
                try:
                    result = handler(data, client_address)
                    if result:
                        response = result
                        break
                except Exception as e:
                    logger.error(f"UDP消息处理器错误: {e}")
            
            return response
        except Exception as e:
            logger.error(f"UDP消息处理错误: {e}")
            return None
    
    def add_message_handler(self, name: str, handler: Callable) -> None:
        """添加消息处理器"""
        self.message_handlers[name] = handler


class SocketPool:
    """Socket连接池"""
    
    def __init__(self, max_connections: int = 100):
        self.max_connections = max_connections
        self.connections = {}
        self.available_connections = []
        self.lock = threading.Lock()
    
    def get_connection(self, key: str) -> Optional[socket.socket]:
        """获取连接"""
        with self.lock:
            if key in self.connections:
                return self.connections[key]
            return None
    
    def add_connection(self, key: str, connection: socket.socket) -> bool:
        """添加连接"""
        with self.lock:
            if len(self.connections) >= self.max_connections:
                return False
            
            self.connections[key] = connection
            return True
    
    def remove_connection(self, key: str) -> bool:
        """移除连接"""
        with self.lock:
            if key in self.connections:
                try:
                    self.connections[key].close()
                except:
                    pass
                del self.connections[key]
                return True
            return False
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        with self.lock:
            return {
                'total_connections': len(self.connections),
                'max_connections': self.max_connections,
                'utilization': len(self.connections) / self.max_connections * 100
            }


class SecureSocket:
    """安全Socket包装器"""
    
    def __init__(self, sock: socket.socket, cert_file: Optional[str] = None, 
                 key_file: Optional[str] = None, ca_cert: Optional[str] = None):
        self.sock = sock
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_cert = ca_cert
        self.ssl_sock = None
    
    def wrap_socket(self, server_side: bool = False) -> bool:
        """包装为SSL Socket"""
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            
            if server_side:
                if self.cert_file and self.key_file:
                    context.load_cert_chain(self.cert_file, self.key_file)
            else:
                if self.ca_cert:
                    context.load_verify_locations(self.ca_cert)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            self.ssl_sock = context.wrap_socket(self.sock, server_side=server_side)
            return True
        except Exception as e:
            logger.error(f"SSL包装失败: {e}")
            return False
    
    def send(self, data: Union[str, bytes]) -> bool:
        """安全发送数据"""
        try:
            if self.ssl_sock:
                if isinstance(data, str):
                    data = data.encode('utf-8')
                self.ssl_sock.sendall(data)
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"SSL发送失败: {e}")
            return False
    
    def recv(self, buffer_size: int = 4096) -> Optional[bytes]:
        """安全接收数据"""
        try:
            if self.ssl_sock:
                return self.ssl_sock.recv(buffer_size)
            else:
                return None
        except Exception as e:
            logger.error(f"SSL接收失败: {e}")
            return None
    
    def close(self) -> None:
        """关闭安全连接"""
        try:
            if self.ssl_sock:
                self.ssl_sock.close()
            else:
                self.sock.close()
        except:
            pass


def create_socket_server(host: str = '0.0.0.0', port: int = 8080, 
                        protocol: str = 'tcp') -> Union[TCPServer, UDPServer]:
    """创建Socket服务器"""
    if protocol.lower() == 'tcp':
        return TCPServer(host, port)
    elif protocol.lower() == 'udp':
        return UDPServer(host, port)
    else:
        raise ValueError(f"不支持的协议: {protocol}")


def socket_echo_test(host: str = 'localhost', port: int = 8080, 
                    message: str = "Hello, Socket!", protocol: str = 'tcp') -> bool:
    """Socket回显测试"""
    try:
        if protocol.lower() == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.send(message.encode('utf-8'))
            response = sock.recv(1024).decode('utf-8')
            sock.close()
            return response == f"Echo: {message}"
        
        elif protocol.lower() == 'udp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode('utf-8'), (host, port))
            response, _ = sock.recvfrom(1024)
            sock.close()
            return response.decode('utf-8') == f"Echo: {message}"
        
        else:
            raise ValueError(f"不支持的协议: {protocol}")
    
    except Exception as e:
        logger.error(f"Socket回显测试失败: {e}")
        return False


def port_scan(target: str, ports: List[int], timeout: float = 1.0) -> Dict[str, Any]:
    """端口扫描"""
    open_ports = []
    closed_ports = []
    
    def scan_port(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((target, port))
            sock.close()
            return result == 0
        except:
            return False
    
    # 并发扫描
    threads = []
    results = {}
    
    for port in ports:
        thread = threading.Thread(target=lambda p=port: results.update({p: scan_port(p)}))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    for port, is_open in results.items():
        if is_open:
            open_ports.append(port)
        else:
            closed_ports.append(port)
    
    return {
        'target': target,
        'open_ports': open_ports,
        'closed_ports': closed_ports,
        'scan_time': time.time()
    }


if __name__ == "__main__":
    print("Socket工具模块")
    
    # 创建TCP服务器
    tcp_server = TCPServer('127.0.0.1', 8888)
    
    # 添加自定义消息处理器
    def custom_handler(data: bytes, client_address: tuple) -> bytes:
        return b"Custom response: " + data
    
    tcp_server.add_message_handler('custom', custom_handler)
    
    # 启动服务器（注释掉以避免阻塞）
    # tcp_server.start()
    
    # 创建UDP服务器
    udp_server = UDPServer('127.0.0.1', 8889)
    udp_server.add_message_handler('custom', custom_handler)
    
    # 启动UDP服务器（注释掉以避免阻塞）
    # udp_server.start()
    
    # Socket连接池
    pool = SocketPool(max_connections=10)
    
    # 创建测试连接
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pool.add_connection('test', test_sock)
    
    stats = pool.get_pool_stats()
    print(f"连接池统计: {stats}")
    
    # 安全Socket
    secure_sock = SecureSocket(test_sock)
    # secure_sock.wrap_socket(server_side=True)
    
    # 端口扫描
    scan_result = port_scan('127.0.0.1', [22, 80, 443, 8888])
    print(f"端口扫描结果: 开放端口 {scan_result['open_ports']}")
    
    # 回显测试
    echo_result = socket_echo_test('127.0.0.1', 8888, 'Test message', 'tcp')
    print(f"回显测试: {'成功' if echo_result else '失败'}")
    
    # 清理
    pool.remove_connection('test')
    
    print("Socket工具示例完成")