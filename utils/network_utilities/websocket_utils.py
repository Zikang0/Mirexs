"""
WebSocket工具模块

提供WebSocket连接、消息处理等功能
"""

import json
import base64
import hashlib
import hmac
import threading
import time
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketFrame:
    """WebSocket帧"""
    
    def __init__(self):
        self.fin = False
        self.opcode = 0
        self.mask = False
        self.payload_length = 0
        self.masking_key = None
        self.payload_data = b''
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'WebSocketFrame':
        """从字节创建帧"""
        frame = cls()
        if len(data) < 2:
            return frame
        
        # 解析第一个字节
        first_byte = data[0]
        frame.fin = bool(first_byte & 0x80)
        frame.opcode = first_byte & 0x0F
        
        # 解析第二个字节
        second_byte = data[1]
        frame.mask = bool(second_byte & 0x80)
        frame.payload_length = second_byte & 0x7F
        
        # 解析负载长度
        offset = 2
        if frame.payload_length == 126:
            frame.payload_length = int.from_bytes(data[offset:offset+2], 'big')
            offset += 2
        elif frame.payload_length == 127:
            frame.payload_length = int.from_bytes(data[offset:offset+8], 'big')
            offset += 8
        
        # 解析掩码密钥
        if frame.mask:
            frame.masking_key = data[offset:offset+4]
            offset += 4
        
        # 解析负载数据
        frame.payload_data = data[offset:offset+frame.payload_length]
        
        # 解掩码
        if frame.mask and frame.masking_key:
            frame.payload_data = cls._unmask_payload(frame.payload_data, frame.masking_key)
        
        return frame
    
    def to_bytes(self) -> bytes:
        """转换为字节"""
        payload = self.payload_data
        
        # 掩码
        if self.mask:
            self.masking_key = self._generate_masking_key()
            payload = self._mask_payload(payload, self.masking_key)
        
        # 构建帧
        first_byte = (0x80 if self.fin else 0x00) | (self.opcode & 0x0F)
        
        second_byte = 0x80 if self.mask else 0x00
        
        # 负载长度
        if len(payload) < 126:
            second_byte |= len(payload)
        elif len(payload) < 65536:
            second_byte |= 126
        else:
            second_byte |= 127
        
        frame_data = bytes([first_byte, second_byte])
        
        # 添加扩展长度
        if len(payload) >= 126 and len(payload) < 65536:
            frame_data += len(payload).to_bytes(2, 'big')
        elif len(payload) >= 65536:
            frame_data += len(payload).to_bytes(8, 'big')
        
        # 添加掩码密钥
        if self.mask and self.masking_key:
            frame_data += self.masking_key
        
        # 添加负载数据
        frame_data += payload
        
        return frame_data
    
    @staticmethod
    def _generate_masking_key() -> bytes:
        """生成掩码密钥"""
        import secrets
        return secrets.token_bytes(4)
    
    @staticmethod
    def _mask_payload(payload: bytes, masking_key: bytes) -> bytes:
        """掩码负载数据"""
        masked = bytearray()
        for i, byte in enumerate(payload):
            masked.append(byte ^ masking_key[i % 4])
        return bytes(masked)
    
    @staticmethod
    def _unmask_payload(payload: bytes, masking_key: bytes) -> bytes:
        """解掩码负载数据"""
        return WebSocketFrame._mask_payload(payload, masking_key)


class WebSocketProtocol:
    """WebSocket协议处理"""
    
    # 操作码
    OPCODE_CONTINUATION = 0x0
    OPCODE_TEXT = 0x1
    OPCODE_BINARY = 0x2
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xA
    
    @staticmethod
    def create_accept_key(key: str) -> str:
        """创建Accept密钥"""
        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_string = key + GUID
        accept_bytes = accept_string.encode('ascii')
        accept_hash = hashlib.sha1(accept_bytes).digest()
        return base64.b64encode(accept_hash).decode('ascii')
    
    @staticmethod
    def validate_accept_key(key: str, accept_key: str) -> bool:
        """验证Accept密钥"""
        expected_key = WebSocketProtocol.create_accept_key(key)
        return expected_key == accept_key
    
    @staticmethod
    def parse_frame(data: bytes) -> Optional[WebSocketFrame]:
        """解析帧"""
        try:
            return WebSocketFrame.from_bytes(data)
        except Exception as e:
            logger.error(f"帧解析失败: {e}")
            return None
    
    @staticmethod
    def create_text_frame(text: str, fin: bool = True) -> WebSocketFrame:
        """创建文本帧"""
        frame = WebSocketFrame()
        frame.fin = fin
        frame.opcode = WebSocketProtocol.OPCODE_TEXT
        frame.payload_data = text.encode('utf-8')
        return frame
    
    @staticmethod
    def create_binary_frame(data: bytes, fin: bool = True) -> WebSocketFrame:
        """创建二进制帧"""
        frame = WebSocketFrame()
        frame.fin = fin
        frame.opcode = WebSocketProtocol.OPCODE_BINARY
        frame.payload_data = data
        return frame
    
    @staticmethod
    def create_close_frame(code: int = 1000, reason: str = "") -> WebSocketFrame:
        """创建关闭帧"""
        frame = WebSocketFrame()
        frame.fin = True
        frame.opcode = WebSocketProtocol.OPCODE_CLOSE
        
        close_data = code.to_bytes(2, 'big') + reason.encode('utf-8')
        frame.payload_data = close_data
        return frame
    
    @staticmethod
    def create_ping_frame(data: bytes = b"") -> WebSocketFrame:
        """创建Ping帧"""
        frame = WebSocketFrame()
        frame.fin = True
        frame.opcode = WebSocketProtocol.OPCODE_PING
        frame.payload_data = data
        return frame
    
    @staticmethod
    def create_pong_frame(data: bytes = b"") -> WebSocketFrame:
        """创建Pong帧"""
        frame = WebSocketFrame()
        frame.fin = True
        frame.opcode = WebSocketProtocol.OPCODE_PONG
        frame.payload_data = data
        return frame


class WebSocketConnection:
    """WebSocket连接"""
    
    def __init__(self, socket_conn, client_address):
        self.socket = socket_conn
        self.client_address = client_address
        self.connected = False
        self.handshake_complete = False
        self.client_key = None
        self.message_handlers = {}
        self.running = False
        self.lock = threading.Lock()
    
    def perform_handshake(self, request_data: bytes) -> bool:
        """执行握手"""
        try:
            request_str = request_data.decode('utf-8')
            
            # 解析请求行
            lines = request_str.split('\r\n')
            request_line = lines[0]
            
            if not request_line.startswith('GET'):
                return False
            
            # 解析头部
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            # 验证WebSocket版本
            if headers.get('upgrade', '').lower() != 'websocket':
                return False
            
            if headers.get('connection', '').lower() != 'upgrade':
                return False
            
            # 获取客户端密钥
            self.client_key = headers.get('sec-websocket-key')
            if not self.client_key:
                return False
            
            # 生成响应
            accept_key = WebSocketProtocol.create_accept_key(self.client_key)
            
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_key}\r\n"
                "\r\n"
            )
            
            # 发送响应
            self.socket.send(response.encode('utf-8'))
            
            self.handshake_complete = True
            self.connected = True
            
            logger.info(f"WebSocket握手成功: {self.client_address}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket握手失败: {e}")
            return False
    
    def send_message(self, message: Union[str, bytes], message_type: str = 'text') -> bool:
        """发送消息"""
        with self.lock:
            if not self.connected:
                return False
            
            try:
                if message_type == 'text':
                    frame = WebSocketProtocol.create_text_frame(message)
                elif message_type == 'binary':
                    frame = WebSocketProtocol.create_binary_frame(message)
                else:
                    return False
                
                frame_data = frame.to_bytes()
                self.socket.send(frame_data)
                return True
                
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
    
    def send_ping(self, data: bytes = b"") -> bool:
        """发送Ping"""
        with self.lock:
            if not self.connected:
                return False
            
            try:
                frame = WebSocketProtocol.create_ping_frame(data)
                frame_data = frame.to_bytes()
                self.socket.send(frame_data)
                return True
            except Exception as e:
                logger.error(f"发送Ping失败: {e}")
                return False
    
    def send_pong(self, data: bytes = b"") -> bool:
        """发送Pong"""
        with self.lock:
            if not self.connected:
                return False
            
            try:
                frame = WebSocketProtocol.create_pong_frame(data)
                frame_data = frame.to_bytes()
                self.socket.send(frame_data)
                return True
            except Exception as e:
                logger.error(f"发送Pong失败: {e}")
                return False
    
    def close(self, code: int = 1000, reason: str = "") -> None:
        """关闭连接"""
        with self.lock:
            if self.connected:
                try:
                    frame = WebSocketProtocol.create_close_frame(code, reason)
                    frame_data = frame.to_bytes()
                    self.socket.send(frame_data)
                except:
                    pass
            
            self.connected = False
            self.handshake_complete = False
        
        try:
            self.socket.close()
        except:
            pass
        
        logger.info(f"WebSocket连接关闭: {self.client_address}")
    
    def start_listening(self) -> None:
        """开始监听消息"""
        self.running = True
        
        while self.running and self.connected:
            try:
                # 接收数据
                data = self.socket.recv(4096)
                if not data:
                    break
                
                # 解析帧
                frame = WebSocketProtocol.parse_frame(data)
                if not frame:
                    continue
                
                # 处理帧
                self._handle_frame(frame)
                
            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
                break
        
        self.close()
    
    def _handle_frame(self, frame: WebSocketFrame) -> None:
        """处理帧"""
        try:
            opcode = frame.opcode
            
            if opcode == WebSocketProtocol.OPCODE_TEXT:
                message = frame.payload_data.decode('utf-8')
                self._trigger_message_handlers('text', message)
            
            elif opcode == WebSocketProtocol.OPCODE_BINARY:
                self._trigger_message_handlers('binary', frame.payload_data)
            
            elif opcode == WebSocketProtocol.OPCODE_PING:
                self.send_pong(frame.payload_data)
            
            elif opcode == WebSocketProtocol.OPCODE_PONG:
                # 处理Pong响应
                pass
            
            elif opcode == WebSocketProtocol.OPCODE_CLOSE:
                code = int.from_bytes(frame.payload_data[:2], 'big') if len(frame.payload_data) >= 2 else 1000
                reason = frame.payload_data[2:].decode('utf-8', errors='ignore')
                self.close(code, reason)
            
        except Exception as e:
            logger.error(f"帧处理错误: {e}")
    
    def add_message_handler(self, message_type: str, handler: Callable) -> None:
        """添加消息处理器"""
        self.message_handlers[message_type] = handler
    
    def _trigger_message_handlers(self, message_type: str, data: Any) -> None:
        """触发消息处理器"""
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type](data, self.client_address)
            except Exception as e:
                logger.error(f"消息处理器错误: {e}")


class WebSocketServer:
    """WebSocket服务器"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.connections = {}
        self.message_handlers = {}
    
    def start(self) -> bool:
        """启动服务器"""
        try:
            import socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            
            logger.info(f"WebSocket服务器启动: {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 关闭所有连接
        for connection in list(self.connections.values()):
            connection.close()
    
    def _accept_connections(self) -> None:
        """接受连接"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, client_address = self.server_socket.accept()
                
                # 创建WebSocket连接
                ws_connection = WebSocketConnection(client_socket, client_address)
                
                # 启动连接处理线程
                connection_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(ws_connection,),
                    daemon=True
                )
                connection_thread.start()
                
                self.connections[client_socket] = ws_connection
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"接受WebSocket连接错误: {e}")
    
    def _handle_connection(self, connection: WebSocketConnection) -> None:
        """处理连接"""
        try:
            # 接收握手请求
            request_data = connection.socket.recv(4096)
            if not request_data:
                return
            
            # 执行握手
            if not connection.perform_handshake(request_data):
                return
            
            # 注册消息处理器
            for message_type, handler in self.message_handlers.items():
                connection.add_message_handler(message_type, handler)
            
            # 开始监听消息
            connection.start_listening()
            
        except Exception as e:
            logger.error(f"WebSocket连接处理错误: {e}")
        finally:
            if connection.socket in self.connections:
                del self.connections[connection.socket]
    
    def broadcast_message(self, message: Union[str, bytes], message_type: str = 'text') -> int:
        """广播消息"""
        sent_count = 0
        
        for connection in list(self.connections.values()):
            if connection.connected:
                if connection.send_message(message, message_type):
                    sent_count += 1
        
        return sent_count
    
    def add_message_handler(self, message_type: str, handler: Callable) -> None:
        """添加消息处理器"""
        self.message_handlers[message_type] = handler
    
    def get_connection_count(self) -> int:
        """获取连接数"""
        return len([c for c in self.connections.values() if c.connected])


class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, url: str):
        self.url = url
        self.parsed_url = urlparse(url)
        self.socket = None
        self.connected = False
        self.message_handlers = {}
        self.running = False
    
    def connect(self) -> bool:
        """连接到服务器"""
        try:
            import socket
            
            # 创建socket连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # 连接到服务器
            host = self.parsed_url.hostname or 'localhost'
            port = self.parsed_url.port or 80
            
            self.socket.connect((host, port))
            
            # 发送握手请求
            if not self._send_handshake():
                return False
            
            self.connected = True
            self.running = True
            
            # 启动消息接收线程
            receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            receive_thread.start()
            
            logger.info(f"WebSocket客户端连接成功: {self.url}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket客户端连接失败: {e}")
            return False
    
    def _send_handshake(self) -> bool:
        """发送握手请求"""
        try:
            import secrets
            
            # 生成WebSocket密钥
            key = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
            
            # 构建握手请求
            request = (
                f"GET {self.parsed_url.path or '/'} HTTP/1.1\r\n"
                f"Host: {self.parsed_url.hostname}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            
            # 发送请求
            self.socket.send(request.encode('utf-8'))
            
            # 接收响应
            response = self.socket.recv(4096).decode('utf-8')
            
            # 解析响应
            lines = response.split('\r\n')
            if not lines[0].startswith('HTTP/1.1 101'):
                return False
            
            # 验证Accept密钥
            for line in lines[1:]:
                if line.lower().startswith('sec-websocket-accept:'):
                    accept_key = line.split(':', 1)[1].strip()
                    if not WebSocketProtocol.validate_accept_key(key, accept_key):
                        return False
                    break
            
            return True
            
        except Exception as e:
            logger.error(f"握手请求失败: {e}")
            return False
    
    def _receive_messages(self) -> None:
        """接收消息"""
        while self.running and self.connected:
            try:
                # 接收数据
                data = self.socket.recv(4096)
                if not data:
                    break
                
                # 解析帧
                frame = WebSocketProtocol.parse_frame(data)
                if not frame:
                    continue
                
                # 处理帧
                self._handle_frame(frame)
                
            except Exception as e:
                logger.error(f"WebSocket客户端消息接收错误: {e}")
                break
        
        self.disconnect()
    
    def _handle_frame(self, frame: WebSocketFrame) -> None:
        """处理帧"""
        try:
            opcode = frame.opcode
            
            if opcode == WebSocketProtocol.OPCODE_TEXT:
                message = frame.payload_data.decode('utf-8')
                self._trigger_message_handlers('text', message)
            
            elif opcode == WebSocketProtocol.OPCODE_BINARY:
                self._trigger_message_handlers('binary', frame.payload_data)
            
            elif opcode == WebSocketProtocol.OPCODE_PING:
                self.send_pong(frame.payload_data)
            
            elif opcode == WebSocketProtocol.OPCODE_PONG:
                # 处理Pong响应
                pass
            
            elif opcode == WebSocketProtocol.OPCODE_CLOSE:
                self.disconnect()
            
        except Exception as e:
            logger.error(f"WebSocket客户端帧处理错误: {e}")
    
    def send_message(self, message: Union[str, bytes], message_type: str = 'text') -> bool:
        """发送消息"""
        if not self.connected:
            return False
        
        try:
            if message_type == 'text':
                frame = WebSocketProtocol.create_text_frame(message)
            elif message_type == 'binary':
                frame = WebSocketProtocol.create_binary_frame(message)
            else:
                return False
            
            frame_data = frame.to_bytes()
            self.socket.send(frame_data)
            return True
            
        except Exception as e:
            logger.error(f"WebSocket客户端发送消息失败: {e}")
            return False
    
    def send_ping(self, data: bytes = b"") -> bool:
        """发送Ping"""
        if not self.connected:
            return False
        
        try:
            frame = WebSocketProtocol.create_ping_frame(data)
            frame_data = frame.to_bytes()
            self.socket.send(frame_data)
            return True
        except Exception as e:
            logger.error(f"WebSocket客户端发送Ping失败: {e}")
            return False
    
    def send_pong(self, data: bytes = b"") -> bool:
        """发送Pong"""
        if not self.connected:
            return False
        
        try:
            frame = WebSocketProtocol.create_pong_frame(data)
            frame_data = frame.to_bytes()
            self.socket.send(frame_data)
            return True
        except Exception as e:
            logger.error(f"WebSocket客户端发送Pong失败: {e}")
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                frame = WebSocketProtocol.create_close_frame()
                frame_data = frame.to_bytes()
                self.socket.send(frame_data)
            except:
                pass
            
            try:
                self.socket.close()
            except:
                pass
        
        logger.info("WebSocket客户端已断开连接")
    
    def add_message_handler(self, message_type: str, handler: Callable) -> None:
        """添加消息处理器"""
        self.message_handlers[message_type] = handler
    
    def _trigger_message_handlers(self, message_type: str, data: Any) -> None:
        """触发消息处理器"""
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type](data)
            except Exception as e:
                logger.error(f"WebSocket客户端消息处理器错误: {e}")


if __name__ == "__main__":
    print("WebSocket工具模块")
    
    # WebSocket协议测试
    test_key = "dGhlIHNhbXBsZSBub25jZQ=="
    accept_key = WebSocketProtocol.create_accept_key(test_key)
    print(f"Accept密钥: {accept_key}")
    
    # 创建测试帧
    text_frame = WebSocketProtocol.create_text_frame("Hello, WebSocket!")
    frame_bytes = text_frame.to_bytes()
    print(f"文本帧大小: {len(frame_bytes)} 字节")
    
    # 解析帧
    parsed_frame = WebSocketProtocol.parse_frame(frame_bytes)
    if parsed_frame:
        print(f"解析后的文本: {parsed_frame.payload_data.decode('utf-8')}")
    
    # WebSocket服务器示例（注释掉以避免阻塞）
    # server = WebSocketServer('127.0.0.1', 8080)
    # 
    # def echo_handler(message, client_address):
    #     print(f"收到消息: {message} 来自: {client_address}")
    #     # 这里需要获取连接对象来发送响应
    # 
    # server.add_message_handler('text', echo_handler)
    # server.start()
    
    # WebSocket客户端示例
    # client = WebSocketClient('ws://127.0.0.1:8080')
    # 
    # def message_handler(message):
    #     print(f"客户端收到消息: {message}")
    # 
    # client.add_message_handler('text', message_handler)
    # 
    # if client.connect():
    #     client.send_message("Hello from client!")
    #     time.sleep(2)
    #     client.disconnect()
    
    print("WebSocket工具示例完成")