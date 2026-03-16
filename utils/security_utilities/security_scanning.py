"""
安全扫描工具模块

提供安全漏洞扫描、端口扫描、服务识别、漏洞检测等功能
"""

import socket
import ipaddress
import threading
import time
import logging
import ssl
import subprocess
import platform
import json
import re
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScanLevel(Enum):
    """扫描级别枚举"""
    LIGHT = "light"      # 轻量扫描
    NORMAL = "normal"    # 普通扫描
    DEEP = "deep"        # 深度扫描
    FULL = "full"        # 完全扫描


class VulnerabilitySeverity(Enum):
    """漏洞严重性枚举"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PortStatus(Enum):
    """端口状态枚举"""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


class ServiceProtocol(Enum):
    """服务协议枚举"""
    TCP = "tcp"
    UDP = "udp"
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SSH = "ssh"
    TELNET = "telnet"
    SMTP = "smtp"
    DNS = "dns"
    POP3 = "pop3"
    IMAP = "imap"
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    MONGODB = "mongodb"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class PortInfo:
    """端口信息数据类"""
    port: int
    protocol: ServiceProtocol
    status: PortStatus
    service: Optional[str] = None
    version: Optional[str] = None
    banner: Optional[str] = None
    vulnerabilities: List[str] = field(default_factory=list)
    risk_score: float = 0.0


@dataclass
class VulnerabilityInfo:
    """漏洞信息数据类"""
    name: str
    description: str
    severity: VulnerabilitySeverity
    cvss_score: Optional[float] = None
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    affected_versions: Optional[str] = None
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """扫描结果数据类"""
    target: str
    scan_level: ScanLevel
    start_time: datetime
    end_time: datetime
    open_ports: List[PortInfo] = field(default_factory=list)
    vulnerabilities: List[VulnerabilityInfo] = field(default_factory=list)
    services: Dict[str, Any] = field(default_factory=dict)
    os_info: Optional[str] = None
    risk_level: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


class SecurityScanner:
    """安全扫描器"""
    
    def __init__(self, timeout: int = 5, max_workers: int = 50):
        """初始化安全扫描器
        
        Args:
            timeout: 超时时间（秒）
            max_workers: 最大工作线程数
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.common_ports = {
            21: "FTP",
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            111: "RPC",
            135: "RPC",
            139: "NetBIOS",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            993: "IMAPS",
            995: "POP3S",
            1723: "PPTP",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            5900: "VNC",
            6379: "Redis",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
            9200: "Elasticsearch",
            27017: "MongoDB"
        }
        
        self.vulnerability_db: Dict[str, List[VulnerabilityInfo]] = {}
        self._init_vulnerability_db()
        
    def _init_vulnerability_db(self):
        """初始化漏洞数据库"""
        # 常见的漏洞定义
        self.vulnerability_db = {
            "ftp_anonymous": [VulnerabilityInfo(
                name="FTP Anonymous Login",
                description="FTP服务器允许匿名登录，可能泄露敏感信息",
                severity=VulnerabilitySeverity.MEDIUM,
                cve_id="CVE-1999-0497",
                remediation="禁用匿名FTP访问"
            )],
            "ssh_weak_cipher": [VulnerabilityInfo(
                name="SSH Weak Cipher",
                description="SSH服务器使用弱加密算法",
                severity=VulnerabilitySeverity.MEDIUM,
                remediation="禁用弱加密算法，使用更强的加密套件"
            )],
            "http_directory_listing": [VulnerabilityInfo(
                name="HTTP Directory Listing",
                description="Web服务器启用了目录列表，可能泄露敏感文件",
                severity=VulnerabilitySeverity.MEDIUM,
                cwe_id="CWE-548",
                remediation="禁用目录列表功能"
            )],
            "mysql_default_port": [VulnerabilityInfo(
                name="MySQL Default Port",
                description="MySQL运行在默认端口，容易成为攻击目标",
                severity=VulnerabilitySeverity.LOW,
                remediation="更改默认端口"
            )],
            "redis_no_auth": [VulnerabilityInfo(
                name="Redis No Authentication",
                description="Redis未设置认证密码，可能导致数据泄露",
                severity=VulnerabilitySeverity.HIGH,
                remediation="设置Redis认证密码"
            )],
            "elasticsearch_public": [VulnerabilityInfo(
                name="Elasticsearch Public Access",
                description="Elasticsearch未配置访问控制，可能泄露数据",
                severity=VulnerabilitySeverity.HIGH,
                remediation="配置访问控制，使用防火墙限制"
            )],
            "mongodb_public": [VulnerabilityInfo(
                name="MongoDB Public Access",
                description="MongoDB未配置认证，可能泄露数据",
                severity=VulnerabilitySeverity.HIGH,
                remediation="启用认证，配置防火墙"
            )],
            "smb_signing_disabled": [VulnerabilityInfo(
                name="SMB Signing Disabled",
                description="SMB签名未启用，易受中间人攻击",
                severity=VulnerabilitySeverity.MEDIUM,
                remediation="启用SMB签名"
            )],
            "rdp_weak_encryption": [VulnerabilityInfo(
                name="RDP Weak Encryption",
                description="RDP使用弱加密",
                severity=VulnerabilitySeverity.MEDIUM,
                remediation="配置更强的加密"
            )],
            "dns_open_resolver": [VulnerabilityInfo(
                name="DNS Open Resolver",
                description="DNS服务器允许递归查询，易被用于DDoS攻击",
                severity=VulnerabilitySeverity.HIGH,
                remediation="限制递归查询"
            )]
        }
        
    def scan_ports(self, target: str, ports: Optional[List[int]] = None,
                  scan_level: ScanLevel = ScanLevel.NORMAL,
                  protocol: ServiceProtocol = ServiceProtocol.TCP) -> List[PortInfo]:
        """扫描端口
        
        Args:
            target: 目标IP或域名
            ports: 端口列表
            scan_level: 扫描级别
            protocol: 协议类型
            
        Returns:
            List[PortInfo]: 端口信息列表
        """
        if ports is None:
            ports = self._get_ports_by_level(scan_level)
            
        open_ports = []
        port_infos = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_port = {
                executor.submit(self._check_port, target, port, protocol): port
                for port in ports
            }
            
            for future in as_completed(future_to_port):
                port = future_to_port[future]
                try:
                    is_open, banner = future.result()
                    if is_open:
                        port_info = self._identify_service(port, protocol, banner)
                        open_ports.append(port_info)
                        port_infos.append(port_info)
                except Exception as e:
                    logger.debug(f"扫描端口 {port} 失败: {e}")
                    
        logger.info(f"端口扫描完成: 目标 {target}, 发现 {len(open_ports)} 个开放端口")
        return port_infos
        
    def _get_ports_by_level(self, scan_level: ScanLevel) -> List[int]:
        """根据扫描级别获取端口列表
        
        Args:
            scan_level: 扫描级别
            
        Returns:
            List[int]: 端口列表
        """
        if scan_level == ScanLevel.LIGHT:
            return [21, 22, 23, 25, 80, 443, 3306, 3389, 8080]
        elif scan_level == ScanLevel.NORMAL:
            return list(self.common_ports.keys())
        elif scan_level == ScanLevel.DEEP:
            # 前1000个常用端口
            return list(range(1, 1024)) + [3306, 3389, 5432, 6379, 8080, 8443, 9200, 27017]
        else:  # FULL
            # 1-65535所有端口
            return list(range(1, 65536))
            
    def _check_port(self, target: str, port: int, 
                   protocol: ServiceProtocol) -> Tuple[bool, Optional[str]]:
        """检查端口状态
        
        Args:
            target: 目标
            port: 端口
            protocol: 协议
            
        Returns:
            Tuple[bool, Optional[str]]: (是否开放, 服务标识)
        """
        try:
            if protocol == ServiceProtocol.TCP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                
                result = sock.connect_ex((target, port))
                if result == 0:
                    # 尝试获取banner
                    try:
                        if port == 80 or port == 443:
                            sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                        elif port == 21:
                            sock.send(b"HELP\r\n")
                        elif port == 22:
                            banner = sock.recv(1024).decode('utf-8', errors='ignore')
                        else:
                            sock.send(b"\r\n")
                            
                        banner = sock.recv(1024).decode('utf-8', errors='ignore')
                        sock.close()
                        return True, banner
                    except:
                        sock.close()
                        return True, None
                else:
                    sock.close()
                    return False, None
                    
            elif protocol == ServiceProtocol.UDP:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.timeout)
                
                try:
                    sock.sendto(b"", (target, port))
                    data, addr = sock.recvfrom(1024)
                    sock.close()
                    return True, data.decode('utf-8', errors='ignore')
                except socket.timeout:
                    sock.close()
                    return False, None
                    
        except Exception as e:
            logger.debug(f"检查端口 {port} 时出错: {e}")
            return False, None
            
    def _identify_service(self, port: int, protocol: ServiceProtocol,
                         banner: Optional[str] = None) -> PortInfo:
        """识别服务
        
        Args:
            port: 端口
            protocol: 协议
            banner: 服务标识
            
        Returns:
            PortInfo: 端口信息
        """
        service_name = self.common_ports.get(port, "Unknown")
        version = None
        vulnerabilities = []
        risk_score = 0.0
        
        # 从banner中提取版本信息
        if banner:
            # 尝试提取版本号
            version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', banner)
            if version_match:
                version = version_match.group(1)
                
        # 根据端口和服务检查漏洞
        if port == 21 and service_name == "FTP":
            if banner and "anonymous" in banner.lower():
                vulnerabilities.append("ftp_anonymous")
                risk_score += 5.0
                
        elif port == 22 and service_name == "SSH":
            if banner and ("weak" in banner.lower() or "deprecated" in banner.lower()):
                vulnerabilities.append("ssh_weak_cipher")
                risk_score += 3.0
                
        elif port in [80, 8080] and "HTTP" in service_name:
            vulnerabilities.append("http_directory_listing")
            risk_score += 2.0
            
        elif port == 6379 and "Redis" in service_name:
            if not banner or "NOAUTH" in banner:
                vulnerabilities.append("redis_no_auth")
                risk_score += 7.0
                
        elif port == 9200 and "Elasticsearch" in service_name:
            vulnerabilities.append("elasticsearch_public")
            risk_score += 6.0
            
        elif port == 27017 and "MongoDB" in service_name:
            vulnerabilities.append("mongodb_public")
            risk_score += 6.0
            
        return PortInfo(
            port=port,
            protocol=protocol,
            status=PortStatus.OPEN,
            service=service_name,
            version=version,
            banner=banner,
            vulnerabilities=vulnerabilities,
            risk_score=risk_score
        )
        
    def detect_os(self, target: str) -> Optional[str]:
        """检测操作系统
        
        Args:
            target: 目标
            
        Returns:
            Optional[str]: 操作系统信息
        """
        try:
            # 使用TTL值初步判断
            ping_result = subprocess.run(
                ["ping", "-c", "1", target] if platform.system() != "Windows" 
                else ["ping", "-n", "1", target],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if ping_result.returncode == 0:
                # 提取TTL值
                ttl_match = re.search(r'ttl=(\d+)', ping_result.stdout.lower())
                if ttl_match:
                    ttl = int(ttl_match.group(1))
                    if ttl <= 64:
                        return "Linux/Unix (TTL <= 64)"
                    elif ttl <= 128:
                        return "Windows (TTL <= 128)"
                    else:
                        return f"Unknown (TTL={ttl})"
                        
            # 尝试使用nmap风格识别
            return self._os_fingerprint(target)
            
        except Exception as e:
            logger.debug(f"操作系统检测失败: {e}")
            return None
            
    def _os_fingerprint(self, target: str) -> Optional[str]:
        """操作系统指纹识别
        
        Args:
            target: 目标
            
        Returns:
            Optional[str]: 操作系统信息
        """
        # 这里可以实现更复杂的OS指纹识别
        # 例如分析TCP/IP协议栈特征
        return None
        
    def check_vulnerabilities(self, port_info: PortInfo) -> List[VulnerabilityInfo]:
        """检查漏洞
        
        Args:
            port_info: 端口信息
            
        Returns:
            List[VulnerabilityInfo]: 漏洞列表
        """
        vulnerabilities = []
        
        for vuln_id in port_info.vulnerabilities:
            if vuln_id in self.vulnerability_db:
                vulnerabilities.extend(self.vulnerability_db[vuln_id])
                
        return vulnerabilities
        
    def scan_target(self, target: str, scan_level: ScanLevel = ScanLevel.NORMAL,
                   ports: Optional[List[int]] = None) -> ScanResult:
        """扫描目标
        
        Args:
            target: 目标IP或域名
            scan_level: 扫描级别
            ports: 指定端口列表
            
        Returns:
            ScanResult: 扫描结果
        """
        logger.info(f"开始扫描目标: {target}, 级别: {scan_level.value}")
        start_time = datetime.now()
        
        # 解析目标
        try:
            ip = socket.gethostbyname(target)
            logger.info(f"目标IP: {ip}")
        except socket.gaierror:
            logger.error(f"无法解析目标: {target}")
            raise ValueError(f"无法解析目标: {target}")
            
        # 端口扫描
        port_infos = self.scan_ports(target, ports, scan_level)
        
        # 检查漏洞
        all_vulnerabilities = []
        for port_info in port_infos:
            vulnerabilities = self.check_vulnerabilities(port_info)
            all_vulnerabilities.extend(vulnerabilities)
            
        # 操作系统检测
        os_info = self.detect_os(target)
        
        # 计算风险等级
        risk_level = self._calculate_risk_level(port_infos, all_vulnerabilities)
        
        # 生成摘要
        summary = self._generate_summary(port_infos, all_vulnerabilities, risk_level)
        
        end_time = datetime.now()
        
        result = ScanResult(
            target=target,
            scan_level=scan_level,
            start_time=start_time,
            end_time=end_time,
            open_ports=port_infos,
            vulnerabilities=all_vulnerabilities,
            os_info=os_info,
            risk_level=risk_level,
            summary=summary
        )
        
        logger.info(f"扫描完成: 目标 {target}, 耗时 {end_time - start_time}")
        return result
        
    def _calculate_risk_level(self, port_infos: List[PortInfo],
                             vulnerabilities: List[VulnerabilityInfo]) -> str:
        """计算风险等级
        
        Args:
            port_infos: 端口信息列表
            vulnerabilities: 漏洞列表
            
        Returns:
            str: 风险等级
        """
        total_risk_score = sum(p.risk_score for p in port_infos)
        
        for vuln in vulnerabilities:
            if vuln.severity == VulnerabilitySeverity.CRITICAL:
                total_risk_score += 10
            elif vuln.severity == VulnerabilitySeverity.HIGH:
                total_risk_score += 7
            elif vuln.severity == VulnerabilitySeverity.MEDIUM:
                total_risk_score += 4
            elif vuln.severity == VulnerabilitySeverity.LOW:
                total_risk_score += 1
                
        if total_risk_score >= 20:
            return "CRITICAL"
        elif total_risk_score >= 10:
            return "HIGH"
        elif total_risk_score >= 5:
            return "MEDIUM"
        elif total_risk_score >= 1:
            return "LOW"
        else:
            return "INFO"
            
    def _generate_summary(self, port_infos: List[PortInfo],
                         vulnerabilities: List[VulnerabilityInfo],
                         risk_level: str) -> Dict[str, Any]:
        """生成扫描摘要
        
        Args:
            port_infos: 端口信息
            vulnerabilities: 漏洞列表
            risk_level: 风险等级
            
        Returns:
            Dict[str, Any]: 摘要信息
        """
        return {
            'total_open_ports': len(port_infos),
            'total_vulnerabilities': len(vulnerabilities),
            'risk_level': risk_level,
            'vulnerabilities_by_severity': {
                level.value: sum(1 for v in vulnerabilities if v.severity == level)
                for level in VulnerabilitySeverity
            },
            'services_by_port': [
                {'port': p.port, 'service': p.service, 'version': p.version}
                for p in port_infos
            ]
        }
        
    def scan_network(self, network: str, scan_level: ScanLevel = ScanLevel.LIGHT) -> List[ScanResult]:
        """扫描网络
        
        Args:
            network: 网络CIDR（如 192.168.1.0/24）
            scan_level: 扫描级别
            
        Returns:
            List[ScanResult]: 扫描结果列表
        """
        logger.info(f"开始扫描网络: {network}")
        
        try:
            network = ipaddress.ip_network(network, strict=False)
        except ValueError as e:
            logger.error(f"无效的网络地址: {e}")
            raise
            
        results = []
        
        # 先进行存活主机探测
        live_hosts = self._discover_live_hosts(network)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_host = {
                executor.submit(self.scan_target, str(host), scan_level): host
                for host in live_hosts
            }
            
            for future in as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"扫描主机 {host} 失败: {e}")
                    
        logger.info(f"网络扫描完成: 扫描了 {len(results)} 个活跃主机")
        return results
        
    def _discover_live_hosts(self, network: ipaddress.IPv4Network) -> List[ipaddress.IPv4Address]:
        """发现存活主机
        
        Args:
            network: 网络
            
        Returns:
            List[ipaddress.IPv4Address]: 存活主机列表
        """
        live_hosts = []
        
        def ping_host(host):
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", str(host)] if platform.system() != "Windows"
                    else ["ping", "-n", "1", "-w", "1000", str(host)],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return host
            except:
                pass
            return None
            
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(ping_host, host) for host in network.hosts()]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    live_hosts.append(result)
                    
        return live_hosts
        
    def check_ssl_tls(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """检查SSL/TLS配置
        
        Args:
            hostname: 主机名
            port: 端口
            
        Returns:
            Dict[str, Any]: SSL/TLS检查结果
        """
        result = {
            'hostname': hostname,
            'port': port,
            'certificate_valid': False,
            'protocol': None,
            'cipher': None,
            'issuer': None,
            'subject': None,
            'expires': None,
            'issues': []
        }
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    # 获取证书信息
                    cert = ssock.getpeercert()
                    
                    result['certificate_valid'] = True
                    result['protocol'] = ssock.version()
                    result['cipher'] = ssock.cipher()
                    result['issuer'] = dict(x[0] for x in cert['issuer'])
                    result['subject'] = dict(x[0] for x in cert['subject'])
                    result['expires'] = cert['notAfter']
                    
                    # 检查证书过期
                    from datetime import datetime
                    expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    if expiry_date < datetime.now():
                        result['issues'].append("证书已过期")
                    elif (expiry_date - datetime.now()).days < 30:
                        result['issues'].append("证书即将过期")
                        
                    # 检查SSL/TLS版本
                    if ssock.version() in ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']:
                        result['issues'].append(f"使用过时的SSL/TLS版本: {ssock.version()}")
                        
        except Exception as e:
            result['issues'].append(f"SSL/TLS检查失败: {e}")
            
        return result
        
    def generate_report(self, scan_result: ScanResult, format: str = 'text') -> str:
        """生成扫描报告
        
        Args:
            scan_result: 扫描结果
            format: 报告格式（text/json/html）
            
        Returns:
            str: 报告内容
        """
        if format == 'json':
            return self._generate_json_report(scan_result)
        elif format == 'html':
            return self._generate_html_report(scan_result)
        else:
            return self._generate_text_report(scan_result)
            
    def _generate_text_report(self, result: ScanResult) -> str:
        """生成文本报告"""
        report = []
        report.append("=" * 60)
        report.append(f"安全扫描报告 - {result.target}")
        report.append("=" * 60)
        report.append(f"扫描时间: {result.start_time} - {result.end_time}")
        report.append(f"扫描级别: {result.scan_level.value}")
        report.append(f"操作系统: {result.os_info or '未知'}")
        report.append(f"风险等级: {result.risk_level or '未知'}")
        report.append("")
        
        # 端口信息
        report.append("开放端口:")
        report.append("-" * 40)
        for port in result.open_ports:
            status = "✓" if port.status == PortStatus.OPEN else "✗"
            vulns = f" (漏洞: {len(port.vulnerabilities)})" if port.vulnerabilities else ""
            report.append(f"  {status} {port.port}/{port.protocol.value} - {port.service} {port.version or ''}{vulns}")
        report.append("")
        
        # 漏洞信息
        if result.vulnerabilities:
            report.append("发现的漏洞:")
            report.append("-" * 40)
            for vuln in result.vulnerabilities:
                severity_color = {
                    VulnerabilitySeverity.CRITICAL: "[严重]",
                    VulnerabilitySeverity.HIGH: "[高危]",
                    VulnerabilitySeverity.MEDIUM: "[中危]",
                    VulnerabilitySeverity.LOW: "[低危]",
                    VulnerabilitySeverity.INFO: "[信息]"
                }.get(vuln.severity, "[未知]")
                report.append(f"  {severity_color} {vuln.name}")
                report.append(f"     描述: {vuln.description}")
                if vuln.remediation:
                    report.append(f"     修复: {vuln.remediation}")
                report.append("")
                
        # 摘要
        report.append("扫描摘要:")
        report.append("-" * 40)
        report.append(f"  开放端口数: {result.summary.get('total_open_ports', 0)}")
        report.append(f"  漏洞总数: {result.summary.get('total_vulnerabilities', 0)}")
        report.append("")
        
        return "\n".join(report)
        
    def _generate_json_report(self, result: ScanResult) -> str:
        """生成JSON报告"""
        data = {
            'target': result.target,
            'scan_level': result.scan_level.value,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat(),
            'os_info': result.os_info,
            'risk_level': result.risk_level,
            'open_ports': [
                {
                    'port': p.port,
                    'protocol': p.protocol.value,
                    'service': p.service,
                    'version': p.version,
                    'banner': p.banner,
                    'vulnerabilities': p.vulnerabilities,
                    'risk_score': p.risk_score
                }
                for p in result.open_ports
            ],
            'vulnerabilities': [
                {
                    'name': v.name,
                    'description': v.description,
                    'severity': v.severity.value,
                    'cvss_score': v.cvss_score,
                    'cve_id': v.cve_id,
                    'cwe_id': v.cwe_id,
                    'remediation': v.remediation
                }
                for v in result.vulnerabilities
            ],
            'summary': result.summary
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
        
    def _generate_html_report(self, result: ScanResult) -> str:
        """生成HTML报告"""
        html = []
        html.append("<!DOCTYPE html>")
        html.append("<html>")
        html.append("<head>")
        html.append("    <title>安全扫描报告</title>")
        html.append("    <style>")
        html.append("        body { font-family: Arial, sans-serif; margin: 20px; }")
        html.append("        h1 { color: #333; }")
        html.append("        .section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }")
        html.append("        .critical { color: #ff0000; font-weight: bold; }")
        html.append("        .high { color: #ff6600; font-weight: bold; }")
        html.append("        .medium { color: #ffcc00; font-weight: bold; }")
        html.append("        .low { color: #3399ff; font-weight: bold; }")
        html.append("        .info { color: #666666; }")
        html.append("        table { border-collapse: collapse; width: 100%; }")
        html.append("        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
        html.append("        th { background-color: #f2f2f2; }")
        html.append("    </style>")
        html.append("</head>")
        html.append("<body>")
        
        html.append(f"<h1>安全扫描报告 - {result.target}</h1>")
        html.append(f"<p>扫描时间: {result.start_time} - {result.end_time}</p>")
        html.append(f"<p>风险等级: <span class='{result.risk_level.lower() if result.risk_level else 'info'}'>"
                   f"{result.risk_level or '未知'}</span></p>")
        
        # 开放端口
        html.append("<div class='section'>")
        html.append("<h2>开放端口</h2>")
        html.append("<table>")
        html.append("<tr><th>端口</th><th>协议</th><th>服务</th><th>版本</th><th>风险分数</th></tr>")
        for port in result.open_ports:
            html.append(f"<tr>")
            html.append(f"<td>{port.port}</td>")
            html.append(f"<td>{port.protocol.value}</td>")
            html.append(f"<td>{port.service}</td>")
            html.append(f"<td>{port.version or '-'}</td>")
            html.append(f"<td>{port.risk_score}</td>")
            html.append(f"</tr>")
        html.append("</table>")
        html.append("</div>")
        
        # 漏洞列表
        if result.vulnerabilities:
            html.append("<div class='section'>")
            html.append("<h2>发现的漏洞</h2>")
            for vuln in result.vulnerabilities:
                severity_class = vuln.severity.value
                html.append(f"<div class='vulnerability'>")
                html.append(f"<h3 class='{severity_class}'>{vuln.severity.value.upper()}: {vuln.name}</h3>")
                html.append(f"<p><strong>描述:</strong> {vuln.description}</p>")
                if vuln.cve_id:
                    html.append(f"<p><strong>CVE:</strong> {vuln.cve_id}</p>")
                if vuln.remediation:
                    html.append(f"<p><strong>修复建议:</strong> {vuln.remediation}</p>")
                html.append("</div>")
            html.append("</div>")
            
        html.append("</body>")
        html.append("</html>")
        
        return "\n".join(html)


class WebVulnerabilityScanner:
    """Web漏洞扫描器"""
    
    def __init__(self, timeout: int = 10):
        """初始化Web漏洞扫描器
        
        Args:
            timeout: 超时时间
        """
        self.timeout = timeout
        self.common_paths = [
            '/admin', '/login', '/wp-admin', '/wp-login.php',
            '/phpinfo.php', '/info.php', '/test.php',
            '/backup', '/backup.zip', '/backup.tar.gz',
            '/.git', '/.env', '/config.php',
            '/robots.txt', '/sitemap.xml', '/crossdomain.xml'
        ]
        
    def scan_web_vulnerabilities(self, url: str) -> List[VulnerabilityInfo]:
        """扫描Web漏洞
        
        Args:
            url: 目标URL
            
        Returns:
            List[VulnerabilityInfo]: 漏洞列表
        """
        import requests
        vulnerabilities = []
        
        try:
            session = requests.Session()
            session.timeout = self.timeout
            
            # 检查敏感文件
            for path in self.common_paths:
                try:
                    response = session.get(url + path)
                    if response.status_code == 200:
                        vuln = VulnerabilityInfo(
                            name=f"敏感文件泄露: {path}",
                            description=f"发现敏感文件 {path}，可能泄露敏感信息",
                            severity=VulnerabilitySeverity.MEDIUM,
                            remediation=f"删除或保护文件 {path}"
                        )
                        vulnerabilities.append(vuln)
                except:
                    pass
                    
            # 检查目录列表
            try:
                response = session.get(url + '/')
                if 'Index of' in response.text:
                    vuln = VulnerabilityInfo(
                        name="目录列表启用",
                        description="Web服务器启用了目录列表，可能泄露敏感文件",
                        severity=VulnerabilitySeverity.MEDIUM,
                        remediation="禁用目录列表功能"
                    )
                    vulnerabilities.append(vuln)
            except:
                pass
                
            # 检查服务器信息泄露
            try:
                response = session.get(url)
                server = response.headers.get('Server', '')
                if server and ('Apache' in server or 'nginx' in server or 'IIS' in server):
                    vuln = VulnerabilityInfo(
                        name="服务器信息泄露",
                        description=f"服务器泄露了版本信息: {server}",
                        severity=VulnerabilitySeverity.LOW,
                        remediation="配置服务器隐藏版本信息"
                    )
                    vulnerabilities.append(vuln)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Web漏洞扫描失败: {e}")
            
        return vulnerabilities


# 便捷函数
def scan_target(target: str, scan_level: ScanLevel = ScanLevel.NORMAL) -> ScanResult:
    """扫描目标便捷函数"""
    scanner = SecurityScanner()
    return scanner.scan_target(target, scan_level)


def scan_ports(target: str, ports: Optional[List[int]] = None) -> List[PortInfo]:
    """扫描端口便捷函数"""
    scanner = SecurityScanner()
    return scanner.scan_ports(target, ports)


def check_ssl_tls(hostname: str, port: int = 443) -> Dict[str, Any]:
    """检查SSL/TLS便捷函数"""
    scanner = SecurityScanner()
    return scanner.check_ssl_tls(hostname, port)


def scan_network(network: str, scan_level: ScanLevel = ScanLevel.LIGHT) -> List[ScanResult]:
    """扫描网络便捷函数"""
    scanner = SecurityScanner()
    return scanner.scan_network(network, scan_level)


def scan_web_vulnerabilities(url: str) -> List[VulnerabilityInfo]:
    """扫描Web漏洞便捷函数"""
    scanner = WebVulnerabilityScanner()
    return scanner.scan_web_vulnerabilities(url)