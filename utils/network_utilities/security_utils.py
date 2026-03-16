"""
网络安全工具模块

提供网络安全检测、扫描、监控等功能
"""

import socket
import threading
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Union
import logging
import subprocess
import ssl
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NetworkSecurityScanner:
    """网络安全扫描器"""
    
    def __init__(self):
        self.scan_results = {}
    
    def port_scan(self, target: str, ports: List[int], timeout: float = 1.0) -> Dict[str, Any]:
        """端口扫描"""
        open_ports = []
        closed_ports = []
        
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((target, port))
                sock.close()
                
                if result == 0:
                    open_ports.append(port)
                else:
                    closed_ports.append(port)
            except:
                closed_ports.append(port)
        
        return {
            'target': target,
            'open_ports': open_ports,
            'closed_ports': closed_ports,
            'scan_time': time.time()
        }
    
    def ssl_certificate_check(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """SSL证书检查"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    return {
                        'hostname': hostname,
                        'port': port,
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'version': cert['version'],
                        'serial_number': cert['serialNumber'],
                        'not_before': cert['notBefore'],
                        'not_after': cert['notAfter'],
                        'is_valid': True
                    }
        except Exception as e:
            return {
                'hostname': hostname,
                'port': port,
                'error': str(e),
                'is_valid': False
            }
    
    def vulnerability_scan(self, target: str, ports: List[int]) -> Dict[str, Any]:
        """漏洞扫描"""
        vulnerabilities = []
        
        # 常见漏洞检查
        common_vulns = {
            21: ['ftp_anonymous', 'ftp_bounce'],
            22: ['ssh_brute_force', 'ssh_old_version'],
            23: ['telnet_cleartext'],
            25: ['smtp_open_relay'],
            53: ['dns_zone_transfer'],
            80: ['http_directory_traversal', 'http_sql_injection'],
            110: ['pop3_cleartext'],
            143: ['imap_cleartext'],
            443: ['ssl_weak_cipher', 'ssl_heartbleed'],
            993: ['imap_ssl_cleartext'],
            995: ['pop3_ssl_cleartext'],
            3306: ['mysql_old_version', 'mysql_brute_force'],
            3389: ['rdp_bluekeep'],
            5432: ['postgresql_old_version'],
            5900: ['vnc_weak_auth']
        }
        
        for port in ports:
            if port in common_vulns:
                for vuln in common_vulns[port]:
                    vulnerabilities.append({
                        'port': port,
                        'vulnerability': vuln,
                        'severity': 'high' if 'brute' in vuln or 'heartbleed' in vuln else 'medium',
                        'description': f'Potential {vuln} vulnerability on port {port}'
                    })
        
        return {
            'target': target,
            'vulnerabilities': vulnerabilities,
            'scan_time': time.time()
        }


class NetworkTrafficAnalyzer:
    """网络流量分析器"""
    
    def __init__(self):
        self.traffic_stats = {}
    
    def analyze_packet_size(self, packet_sizes: List[int]) -> Dict[str, Any]:
        """分析数据包大小"""
        if not packet_sizes:
            return {}
        
        return {
            'total_packets': len(packet_sizes),
            'average_size': sum(packet_sizes) / len(packet_sizes),
            'min_size': min(packet_sizes),
            'max_size': max(packet_sizes),
            'suspicious_large_packets': len([s for s in packet_sizes if s > 1500]),
            'suspicious_small_packets': len([s for s in packet_sizes if s < 64])
        }
    
    def detect_anomalies(self, traffic_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测流量异常"""
        anomalies = []
        
        # 简单异常检测
        for i, data in enumerate(traffic_data):
            # 检测大量连接
            if data.get('connections', 0) > 1000:
                anomalies.append({
                    'timestamp': data.get('timestamp'),
                    'type': 'high_connection_count',
                    'value': data['connections'],
                    'severity': 'high'
                })
            
            # 检测异常流量模式
            if data.get('bandwidth_usage', 0) > 1000000:  # 1MB/s
                anomalies.append({
                    'timestamp': data.get('timestamp'),
                    'type': 'high_bandwidth_usage',
                    'value': data['bandwidth_usage'],
                    'severity': 'medium'
                })
        
        return anomalies


class NetworkIntrusionDetector:
    """网络入侵检测器"""
    
    def __init__(self):
        self.detection_rules = []
        self.alerts = []
    
    def add_detection_rule(self, rule: Dict[str, Any]) -> None:
        """添加检测规则"""
        self.detection_rules.append(rule)
    
    def detect_intrusion(self, network_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测入侵"""
        alerts = []
        
        for rule in self.detection_rules:
            rule_type = rule.get('type')
            
            if rule_type == 'port_scan':
                # 检测端口扫描
                connections = network_data.get('connections', [])
                unique_ports = set()
                
                for conn in connections:
                    if conn.get('dest_port'):
                        unique_ports.add(conn['dest_port'])
                
                if len(unique_ports) > rule.get('threshold', 10):
                    alerts.append({
                        'type': 'port_scan_detected',
                        'source': network_data.get('source_ip'),
                        'target_ports': list(unique_ports),
                        'severity': 'high'
                    })
            
            elif rule_type == 'brute_force':
                # 检测暴力破解
                failed_attempts = network_data.get('failed_attempts', 0)
                if failed_attempts > rule.get('threshold', 5):
                    alerts.append({
                        'type': 'brute_force_detected',
                        'source': network_data.get('source_ip'),
                        'failed_attempts': failed_attempts,
                        'severity': 'high'
                    })
        
        return alerts


class NetworkFirewall:
    """网络防火墙"""
    
    def __init__(self):
        self.rules = []
        self.blocked_ips = set()
        self.blocked_ports = set()
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """添加防火墙规则"""
        self.rules.append(rule)
    
    def block_ip(self, ip: str, reason: str = '') -> None:
        """阻止IP"""
        self.blocked_ips.add(ip)
        logger.warning(f"IP {ip} 被阻止: {reason}")
    
    def block_port(self, port: int, protocol: str = 'tcp') -> None:
        """阻止端口"""
        self.blocked_ports.add((port, protocol))
        logger.warning(f"端口 {port}/{protocol} 被阻止")
    
    def check_connection(self, source_ip: str, dest_ip: str, dest_port: int, protocol: str = 'tcp') -> bool:
        """检查连接是否被允许"""
        # 检查IP阻止
        if source_ip in self.blocked_ips:
            return False
        
        # 检查端口阻止
        if (dest_port, protocol) in self.blocked_ports:
            return False
        
        # 检查规则
        for rule in self.rules:
            if self._rule_matches(rule, source_ip, dest_ip, dest_port, protocol):
                return rule.get('action', 'allow') == 'allow'
        
        return True
    
    def _rule_matches(self, rule: Dict[str, Any], source_ip: str, dest_ip: str, dest_port: int, protocol: str) -> bool:
        """检查规则是否匹配"""
        # 简化的规则匹配逻辑
        if 'source_ip' in rule and rule['source_ip'] != source_ip:
            return False
        if 'dest_port' in rule and rule['dest_port'] != dest_port:
            return False
        if 'protocol' in rule and rule['protocol'] != protocol:
            return False
        
        return True


def calculate_network_hash(data: str) -> str:
    """计算网络数据哈希"""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def validate_network_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证网络配置"""
    errors = []
    warnings = []
    
    required_fields = ['interface', 'ip_address', 'subnet_mask']
    for field in required_fields:
        if field not in config:
            errors.append(f"缺少必需字段: {field}")
    
    # 验证IP地址格式
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if 'ip_address' in config and not re.match(ip_pattern, config['ip_address']):
        errors.append("IP地址格式无效")
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


if __name__ == "__main__":
    print("网络安全工具模块")
    
    # 网络安全扫描
    scanner = NetworkSecurityScanner()
    port_scan_result = scanner.port_scan('127.0.0.1', [22, 80, 443, 3389])
    print(f"端口扫描结果: 开放端口 {port_scan_result['open_ports']}")
    
    # SSL证书检查
    ssl_result = scanner.ssl_certificate_check('google.com')
    print(f"SSL证书检查: {'有效' if ssl_result['is_valid'] else '无效'}")
    
    # 流量分析
    analyzer = NetworkTrafficAnalyzer()
    packet_sizes = [64, 128, 256, 512, 1024, 1500, 64, 128, 256]
    size_analysis = analyzer.analyze_packet_size(packet_sizes)
    print(f"包大小分析: 平均 {size_analysis['average_size']:.2f} 字节")
    
    # 入侵检测
    detector = NetworkIntrusionDetector()
    detector.add_detection_rule({
        'type': 'port_scan',
        'threshold': 5
    })
    
    test_data = {
        'source_ip': '192.168.1.100',
        'connections': [
            {'dest_port': 22}, {'dest_port': 80}, {'dest_port': 443},
            {'dest_port': 3389}, {'dest_port': 21}, {'dest_port': 25}
        ]
    }
    
    intrusion_alerts = detector.detect_intrusion(test_data)
    print(f"入侵检测警报: {len(intrusion_alerts)} 个")
    
    # 防火墙
    firewall = NetworkFirewall()
    firewall.add_rule({
        'action': 'deny',
        'protocol': 'tcp',
        'dest_port': 22
    })
    
    connection_allowed = firewall.check_connection('192.168.1.100', '192.168.1.1', 22, 'tcp')
    print(f"连接检查: {'允许' if connection_allowed else '拒绝'}")
    
    # 网络配置验证
    config = {
        'interface': 'eth0',
        'ip_address': '192.168.1.100',
        'subnet_mask': '255.255.255.0'
    }
    
    validation = validate_network_config(config)
    print(f"配置验证: {'有效' if validation['is_valid'] else '无效'}")
    
    print("网络安全工具示例完成")