"""
协议工具模块

提供各种网络协议的处理和分析功能
"""

import socket
import struct
import json
import base64
import hashlib
import hmac
import time
from typing import Dict, List, Any, Optional, Union, Tuple, BinaryIO
import logging
from enum import Enum
from dataclasses import dataclass
import binascii

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProtocolType(Enum):
    """协议类型枚举"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SMTP = "smtp"
    DNS = "dns"
    SSH = "ssh"
    TELNET = "telnet"


@dataclass
class PacketInfo:
    """数据包信息"""
    protocol: str
    source_ip: str
    dest_ip: str
    source_port: int
    dest_port: int
    data: bytes
    timestamp: float
    length: int


class ProtocolAnalyzer:
    """协议分析器类"""
    
    def __init__(self):
        """初始化协议分析器"""
        self.protocol_handlers = {
            ProtocolType.TCP: self._handle_tcp,
            ProtocolType.UDP: self._handle_udp,
            ProtocolType.HTTP: self._handle_http,
            ProtocolType.DNS: self._handle_dns,
        }
    
    def analyze_packet(self, packet_data: bytes, protocol: ProtocolType) -> Dict[str, Any]:
        """
        分析数据包
        
        Args:
            packet_data: 数据包内容
            protocol: 协议类型
            
        Returns:
            分析结果字典
        """
        try:
            handler = self.protocol_handlers.get(protocol)
            if handler:
                return handler(packet_data)
            else:
                return self._handle_generic(packet_data, protocol)
        except Exception as e:
            logger.error(f"数据包分析失败: {e}")
            return {
                'error': str(e),
                'protocol': protocol.value,
                'data_length': len(packet_data),
                'timestamp': time.time()
            }
    
    def _handle_tcp(self, packet_data: bytes) -> Dict[str, Any]:
        """处理TCP数据包"""
        try:
            # TCP头部最小20字节
            if len(packet_data) < 20:
                return {'error': 'TCP数据包太短'}
            
            # 解析TCP头部
            header = struct.unpack('!HHLLBBHHH', packet_data[:20])
            
            source_port = header[0]
            dest_port = header[1]
            sequence = header[2]
            acknowledgment = header[3]
            data_offset = (header[4] >> 4) * 4  # 头部长度
            flags = header[5]
            window_size = header[6]
            checksum = header[7]
            urgent_pointer = header[8]
            
            # 解析标志位
            flag_bits = {
                'FIN': bool(flags & 0x01),
                'SYN': bool(flags & 0x02),
                'RST': bool(flags & 0x04),
                'PSH': bool(flags & 0x08),
                'ACK': bool(flags & 0x10),
                'URG': bool(flags & 0x20)
            }
            
            # 提取数据
            payload = packet_data[data_offset:] if len(packet_data) > data_offset else b''
            
            return {
                'protocol': 'TCP',
                'source_port': source_port,
                'dest_port': dest_port,
                'sequence_number': sequence,
                'acknowledgment_number': acknowledgment,
                'header_length': data_offset,
                'flags': flag_bits,
                'window_size': window_size,
                'checksum': checksum,
                'urgent_pointer': urgent_pointer,
                'payload_length': len(payload),
                'payload_preview': payload[:100].hex() if payload else '',
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {'error': f'TCP解析失败: {e}'}
    
    def _handle_udp(self, packet_data: bytes) -> Dict[str, Any]:
        """处理UDP数据包"""
        try:
            # UDP头部8字节
            if len(packet_data) < 8:
                return {'error': 'UDP数据包太短'}
            
            # 解析UDP头部
            header = struct.unpack('!HHHH', packet_data[:8])
            
            source_port = header[0]
            dest_port = header[1]
            length = header[2]
            checksum = header[3]
            
            # 提取数据
            payload = packet_data[8:] if len(packet_data) > 8 else b''
            
            return {
                'protocol': 'UDP',
                'source_port': source_port,
                'dest_port': dest_port,
                'length': length,
                'checksum': checksum,
                'payload_length': len(payload),
                'payload_preview': payload[:100].hex() if payload else '',
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {'error': f'UDP解析失败: {e}'}
    
    def _handle_http(self, packet_data: bytes) -> Dict[str, Any]:
        """处理HTTP数据包"""
        try:
            try:
                http_text = packet_data.decode('utf-8', errors='ignore')
            except:
                http_text = packet_data.decode('latin-1', errors='ignore')
            
            # 解析HTTP请求/响应
            lines = http_text.split('\r\n')
            if not lines:
                return {'error': '无效的HTTP数据'}
            
            first_line = lines[0]
            headers = {}
            
            # 解析首行
            if first_line.startswith('HTTP/'):
                # HTTP响应
                parts = first_line.split(' ', 2)
                if len(parts) >= 2:
                    http_version = parts[0]
                    status_code = parts[1]
                    status_message = parts[2] if len(parts) > 2 else ''
                
                headers['status_line'] = first_line
                headers['http_version'] = http_version
                headers['status_code'] = status_code
                headers['status_message'] = status_message
                
            else:
                # HTTP请求
                parts = first_line.split(' ', 2)
                if len(parts) >= 2:
                    method = parts[0]
                    path = parts[1]
                    http_version = parts[2] if len(parts) > 2 else 'HTTP/1.1'
                
                headers['request_line'] = first_line
                headers['method'] = method
                headers['path'] = path
                headers['http_version'] = http_version
            
            # 解析头部
            i = 1
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    break
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
                
                i += 1
            
            # 提取主体
            body_start = http_text.find('\r\n\r\n')
            body = ''
            if body_start != -1:
                body = http_text[body_start + 4:]
            
            return {
                'protocol': 'HTTP',
                'headers': headers,
                'body_length': len(body),
                'body_preview': body[:500],
                'is_request': 'request_line' in headers,
                'is_response': 'status_line' in headers,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {'error': f'HTTP解析失败: {e}'}
    
    def _handle_dns(self, packet_data: bytes) -> Dict[str, Any]:
        """处理DNS数据包"""
        try:
            if len(packet_data) < 12:
                return {'error': 'DNS数据包太短'}
            
            # 解析DNS头部
            header = struct.unpack('!HHHHHH', packet_data[:12])
            
            transaction_id = header[0]
            flags = header[1]
            questions = header[2]
            answers = header[3]
            authority = header[4]
            additional = header[5]
            
            # 解析标志位
            qr = (flags >> 15) & 1  # 查询/响应
            opcode = (flags >> 11) & 0xF  # 操作码
            aa = (flags >> 10) & 1  # 权威回答
            tc = (flags >> 9) & 1   # 截断
            rd = (flags >> 8) & 1   # 递归期望
            ra = (flags >> 7) & 1   # 递归可用
            rcode = flags & 0xF     # 响应码
            
            result = {
                'protocol': 'DNS',
                'transaction_id': hex(transaction_id),
                'is_query': qr == 0,
                'is_response': qr == 1,
                'opcode': opcode,
                'authoritative_answer': aa == 1,
                'truncated': tc == 1,
                'recursion_desired': rd == 1,
                'recursion_available': ra == 1,
                'response_code': rcode,
                'question_count': questions,
                'answer_count': answers,
                'authority_count': authority,
                'additional_count': additional,
                'timestamp': time.time()
            }
            
            # 解析查询
            if questions > 0:
                offset = 12
                queries = []
                
                for _ in range(questions):
                    query_info = self._parse_dns_query(packet_data, offset)
                    if query_info:
                        queries.append(query_info)
                        offset = query_info['next_offset']
                
                result['queries'] = queries
            
            return result
            
        except Exception as e:
            return {'error': f'DNS解析失败: {e}'}
    
    def _parse_dns_query(self, data: bytes, offset: int) -> Optional[Dict[str, Any]]:
        """解析DNS查询"""
        try:
            start_offset = offset
            domain_parts = []
            
            # 解析域名
            while offset < len(data):
                length = data[offset]
                offset += 1
                
                if length == 0:
                    break
                
                if length > 63:  # 指针
                    pointer = ((length & 0x3F) << 8) | data[offset]
                    offset += 1
                    # 这里简化处理，实际应该递归解析指针
                    domain_parts.append(f"<pointer:{pointer}>")
                    break
                else:
                    if offset + length <= len(data):
                        domain_part = data[offset:offset + length].decode('utf-8', errors='ignore')
                        domain_parts.append(domain_part)
                        offset += length
                    else:
                        break
            
            if not domain_parts:
                return None
            
            domain = '.'.join(domain_parts)
            
            # 解析查询类型和类
            if offset + 4 <= len(data):
                query_type = struct.unpack('!H', data[offset:offset + 2])[0]
                query_class = struct.unpack('!H', data[offset + 2:offset + 4])[0]
                offset += 4
                
                return {
                    'domain': domain,
                    'query_type': query_type,
                    'query_class': query_class,
                    'next_offset': offset
                }
            
            return None
            
        except Exception as e:
            logger.error(f"DNS查询解析失败: {e}")
            return None
    
    def _handle_generic(self, packet_data: bytes, protocol: ProtocolType) -> Dict[str, Any]:
        """处理通用协议"""
        return {
            'protocol': protocol.value.upper(),
            'data_length': len(packet_data),
            'data_preview': packet_data[:100].hex(),
            'timestamp': time.time()
        }


class ProtocolTester:
    """协议测试器类"""
    
    def __init__(self):
        """初始化协议测试器"""
        self.test_results = {}
    
    def test_tcp_connection(self, host: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
        """
        测试TCP连接
        
        Args:
            host: 目标主机
            port: 目标端口
            timeout: 超时时间
            
        Returns:
            连接测试结果
        """
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            result = sock.connect_ex((host, port))
            connection_time = time.time() - start_time
            
            sock.close()
            
            return {
                'host': host,
                'port': port,
                'protocol': 'TCP',
                'success': result == 0,
                'connection_time': connection_time,
                'error': None if result == 0 else socket.error(result).strerror,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'protocol': 'TCP',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def test_udp_connection(self, host: str, port: int, timeout: float = 5.0) -> Dict[str, Any]:
        """
        测试UDP连接
        
        Args:
            host: 目标主机
            port: 目标端口
            timeout: 超时时间
            
        Returns:
            UDP测试结果
        """
        try:
            start_time = time.time()
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            
            # 发送测试数据
            test_message = b"UDP Test"
            sock.sendto(test_message, (host, port))
            
            try:
                # 尝试接收响应
                data, addr = sock.recvfrom(1024)
                response_time = time.time() - start_time
                
                sock.close()
                
                return {
                    'host': host,
                    'port': port,
                    'protocol': 'UDP',
                    'success': True,
                    'response_time': response_time,
                    'response_data': data.decode('utf-8', errors='ignore'),
                    'response_from': f"{addr[0]}:{addr[1]}",
                    'timestamp': time.time()
                }
                
            except socket.timeout:
                sock.close()
                
                return {
                    'host': host,
                    'port': port,
                    'protocol': 'UDP',
                    'success': None,  # UDP无法确定
                    'error': 'No response received (timeout)',
                    'timestamp': time.time()
                }
                
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'protocol': 'UDP',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def test_http_service(self, url: str, method: str = 'GET', 
                         headers: Optional[Dict[str, str]] = None,
                         data: Optional[str] = None) -> Dict[str, Any]:
        """
        测试HTTP服务
        
        Args:
            url: 目标URL
            method: HTTP方法
            headers: 请求头
            data: 请求数据
            
        Returns:
            HTTP测试结果
        """
        try:
            import requests
            
            start_time = time.time()
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                timeout=10,
                allow_redirects=True
            )
            
            response_time = time.time() - start_time
            
            return {
                'url': url,
                'method': method,
                'status_code': response.status_code,
                'response_time': response_time,
                'content_length': len(response.content),
                'content_type': response.headers.get('content-type'),
                'server': response.headers.get('server'),
                'success': 200 <= response.status_code < 300,
                'redirects': len(response.history),
                'final_url': response.url,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'url': url,
                'method': method,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def test_ftp_service(self, host: str, port: int = 21, 
                        username: str = 'anonymous', 
                        password: str = 'anonymous@example.com') -> Dict[str, Any]:
        """
        测试FTP服务
        
        Args:
            host: 目标主机
            port: FTP端口
            username: 用户名
            password: 密码
            
        Returns:
            FTP测试结果
        """
        try:
            import ftplib
            
            start_time = time.time()
            
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=10)
            ftp.login(username, password)
            
            # 获取欢迎信息
            welcome_message = ftp.getwelcome()
            
            # 获取当前目录
            try:
                current_dir = ftp.pwd()
            except:
                current_dir = None
            
            # 获取文件列表（限制数量）
            try:
                file_list = []
                ftp.dir(file_list.append)
                files_count = len(file_list)
            except:
                files_count = 0
            
            ftp.quit()
            connection_time = time.time() - start_time
            
            return {
                'host': host,
                'port': port,
                'protocol': 'FTP',
                'success': True,
                'connection_time': connection_time,
                'welcome_message': welcome_message,
                'current_directory': current_dir,
                'files_count': files_count,
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'protocol': 'FTP',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def test_smtp_service(self, host: str, port: int = 25) -> Dict[str, Any]:
        """
        测试SMTP服务
        
        Args:
            host: 目标主机
            port: SMTP端口
            
        Returns:
            SMTP测试结果
        """
        try:
            import smtplib
            
            start_time = time.time()
            
            server = smtplib.SMTP(host, port, timeout=10)
            server.set_debuglevel(0)
            
            # 获取服务器响应
            response = server.ehlo()
            
            # 检查支持的扩展
            extensions = server.esmtp_features if hasattr(server, 'esmtp_features') else {}
            
            server.quit()
            connection_time = time.time() - start_time
            
            return {
                'host': host,
                'port': port,
                'protocol': 'SMTP',
                'success': True,
                'connection_time': connection_time,
                'server_response': response[1].decode('utf-8', errors='ignore') if response else None,
                'supported_extensions': list(extensions.keys()),
                'timestamp': time.time()
            }
            
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'protocol': 'SMTP',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def test_ssh_service(self, host: str, port: int = 22) -> Dict[str, Any]:
        """
        测试SSH服务
        
        Args:
            host: 目标主机
            port: SSH端口
            
        Returns:
            SSH测试结果
        """
        try:
            import paramiko
            
            start_time = time.time()
            
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 只测试连接，不进行认证
            transport = paramiko.Transport((host, port))
            transport.connect()
            
            # 获取SSH版本信息
            ssh_banner = transport.remote_version if hasattr(transport, 'remote_version') else None
            
            transport.close()
            connection_time = time.time() - start_time
            
            return {
                'host': host,
                'port': port,
                'protocol': 'SSH',
                'success': True,
                'connection_time': connection_time,
                'ssh_banner': ssh_banner,
                'timestamp': time.time()
            }
            
        except ImportError:
            return {
                'host': host,
                'port': port,
                'protocol': 'SSH',
                'success': False,
                'error': 'paramiko library not installed',
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'protocol': 'SSH',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def bulk_protocol_test(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量协议测试
        
        Args:
            targets: 测试目标列表
            
        Returns:
            批量测试结果
        """
        try:
            results = {}
            
            for target in targets:
                host = target.get('host')
                port = target.get('port')
                protocol = target.get('protocol', 'tcp').lower()
                
                if not host or not port:
                    continue
                
                if protocol == 'tcp':
                    result = self.test_tcp_connection(host, port)
                elif protocol == 'udp':
                    result = self.test_udp_connection(host, port)
                elif protocol == 'http':
                    url = target.get('url', f'http://{host}:{port}')
                    result = self.test_http_service(url)
                elif protocol == 'ftp':
                    result = self.test_ftp_service(host, port)
                elif protocol == 'smtp':
                    result = self.test_smtp_service(host, port)
                elif protocol == 'ssh':
                    result = self.test_ssh_service(host, port)
                else:
                    result = {
                        'host': host,
                        'port': port,
                        'protocol': protocol,
                        'success': False,
                        'error': f'Unsupported protocol: {protocol}',
                        'timestamp': time.time()
                    }
                
                results[f"{host}:{port}"] = result
            
            # 计算统计信息
            successful_tests = sum(1 for r in results.values() if r.get('success') is True)
            total_tests = len(results)
            
            return {
                'results': results,
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'failed_tests': total_tests - successful_tests,
                    'success_rate': (successful_tests / total_tests) * 100 if total_tests > 0 else 0
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"批量协议测试失败: {e}")
            raise


class ProtocolUtils:
    """协议工具类"""
    
    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """
        计算校验和
        
        Args:
            data: 输入数据
            
        Returns:
            校验和
        """
        checksum = 0
        # 将数据按16位分组
        for i in range(0, len(data) - 1, 2):
            word = (data[i] << 8) + data[i + 1]
            checksum += word
        
        # 处理最后一个字节
        if len(data) % 2 == 1:
            checksum += data[-1] << 8
        
        # 将进位加到结果中
        while checksum >> 16:
            checksum = (checksum & 0xFFFF) + (checksum >> 16)
        
        # 取反
        checksum = ~checksum & 0xFFFF
        return checksum
    
    @staticmethod
    def create_tcp_packet(source_port: int, dest_port: int, 
                         sequence: int = 0, acknowledgment: int = 0,
                         flags: int = 0, data: bytes = b'') -> bytes:
        """
        创建TCP数据包
        
        Args:
            source_port: 源端口
            dest_port: 目标端口
            sequence: 序列号
            acknowledgment: 确认号
            flags: 标志位
            data: 数据
            
        Returns:
            TCP数据包
        """
        # TCP头部：源端口(2) + 目标端口(2) + 序列号(4) + 确认号(4) + 数据偏移(1) + 保留(1) + 标志位(1) + 窗口大小(2) + 校验和(2) + 紧急指针(2)
        header = struct.pack('!HHLLBBHHH', 
                           source_port, dest_port, sequence, acknowledgment,
                           0x50, flags, 0, 0, 0)  # 数据偏移=5*4=20字节
        
        # 计算校验和（这里简化处理）
        checksum = 0
        
        # 构建伪头部
        pseudo_header = struct.pack('!4s4sHH', 
                                  socket.inet_aton('0.0.0.0'),  # 源IP（简化）
                                  socket.inet_aton('0.0.0.0'),  # 目标IP（简化）
                                  socket.IPPROTO_TCP,
                                  len(header) + len(data))
        
        # 计算校验和
        checksum = ProtocolUtils.calculate_checksum(pseudo_header + header + data)
        
        # 重新打包头部（包含校验和）
        header = struct.pack('!HHLLBBHHH', 
                           source_port, dest_port, sequence, acknowledgment,
                           0x50, flags, 0, checksum, 0)
        
        return header + data
    
    @staticmethod
    def create_udp_packet(source_port: int, dest_port: int, data: bytes = b'') -> bytes:
        """
        创建UDP数据包
        
        Args:
            source_port: 源端口
            dest_port: 目标端口
            data: 数据
            
        Returns:
            UDP数据包
        """
        length = 8 + len(data)
        
        # UDP头部：源端口(2) + 目标端口(2) + 长度(2) + 校验和(2)
        header = struct.pack('!HHHH', source_port, dest_port, length, 0)
        
        # 计算校验和（简化处理）
        checksum = 0
        
        return header + data
    
    @staticmethod
    def encode_base64(data: str) -> str:
        """
        Base64编码
        
        Args:
            data: 要编码的数据
            
        Returns:
            Base64编码结果
        """
        return base64.b64encode(data.encode('utf-8')).decode('ascii')
    
    @staticmethod
    def decode_base64(encoded_data: str) -> str:
        """
        Base64解码
        
        Args:
            encoded_data: Base64编码数据
            
        Returns:
            解码结果
        """
        try:
            return base64.b64decode(encoded_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Base64解码失败: {e}")
            raise
    
    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """
        计算MD5哈希
        
        Args:
            data: 输入数据
            
        Returns:
            MD5哈希值
        """
        return hashlib.md5(data).hexdigest()
    
    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """
        计算SHA256哈希
        
        Args:
            data: 输入数据
            
        Returns:
            SHA256哈希值
        """
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def create_hmac(key: bytes, message: bytes, algorithm: str = 'sha256') -> str:
        """
        创建HMAC
        
        Args:
            key: 密钥
            message: 消息
            algorithm: 算法
            
        Returns:
            HMAC值
        """
        if algorithm == 'md5':
            return hmac.new(key, message, hashlib.md5).hexdigest()
        elif algorithm == 'sha1':
            return hmac.new(key, message, hashlib.sha1).hexdigest()
        else:  # 默认使用sha256
            return hmac.new(key, message, hashlib.sha256).hexdigest()


if __name__ == "__main__":
    # 示例用法
    print("协议工具模块")
    
    # 创建协议分析器
    analyzer = ProtocolAnalyzer()
    
    # 创建TCP数据包示例
    tcp_packet = ProtocolUtils.create_tcp_packet(12345, 80, flags=0x18)  # SYN+ACK
    tcp_analysis = analyzer.analyze_packet(tcp_packet, ProtocolType.TCP)
    print(f"TCP包分析: 源端口 {tcp_analysis.get('source_port')}, 目标端口 {tcp_analysis.get('dest_port')}")
    
    # 创建UDP数据包示例
    udp_packet = ProtocolUtils.create_udp_packet(12345, 53, b"test data")
    udp_analysis = analyzer.analyze_packet(udp_packet, ProtocolType.UDP)
    print(f"UDP包分析: 源端口 {udp_analysis.get('source_port')}, 目标端口 {udp_analysis.get('dest_port')}")
    
    # 创建协议测试器
    tester = ProtocolTester()
    
    # TCP连接测试
    tcp_test = tester.test_tcp_connection('8.8.8.8', 53)
    print(f"TCP连接测试: {'成功' if tcp_test['success'] else '失败'}")
    
    # HTTP服务测试
    http_test = tester.test_http_service('https://httpbin.org/get')
    print(f"HTTP服务测试: 状态码 {http_test.get('status_code')}")
    
    # FTP服务测试
    try:
        ftp_test = tester.test_ftp_service('ftp.debian.org')
        print(f"FTP服务测试: {'成功' if ftp_test['success'] else '失败'}")
    except:
        print("FTP测试需要网络连接")
    
    # SMTP服务测试
    try:
        smtp_test = tester.test_smtp_service('smtp.gmail.com')
        print(f"SMTP服务测试: {'成功' if smtp_test['success'] else '失败'}")
    except:
        print("SMTP测试需要网络连接")
    
    # 批量协议测试
    bulk_targets = [
        {'host': '8.8.8.8', 'port': 53, 'protocol': 'tcp'},
        {'host': '1.1.1.1', 'port': 53, 'protocol': 'tcp'},
        {'url': 'https://httpbin.org/get', 'protocol': 'http'}
    ]
    
    bulk_results = tester.bulk_protocol_test(bulk_targets)
    print(f"批量测试成功率: {bulk_results['summary']['success_rate']:.1f}%")
    
    # 协议工具示例
    test_data = "Hello, Protocol World!"
    encoded = ProtocolUtils.encode_base64(test_data)
    print(f"Base64编码: {encoded}")
    
    decoded = ProtocolUtils.decode_base64(encoded)
    print(f"Base64解码: {decoded}")
    
    md5_hash = ProtocolUtils.calculate_md5(test_data.encode('utf-8'))
    print(f"MD5哈希: {md5_hash}")
    
    sha256_hash = ProtocolUtils.calculate_sha256(test_data.encode('utf-8'))
    print(f"SHA256哈希: {sha256_hash}")
    
    # HMAC示例
    key = b"secret_key"
    hmac_result = ProtocolUtils.create_hmac(key, test_data.encode('utf-8'))
    print(f"HMAC-SHA256: {hmac_result}")
    
    print("协议工具示例完成")