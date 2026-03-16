"""
安全扫描器：扫描系统安全漏洞
"""
import os
import platform
import subprocess
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import json
from pathlib import Path
import hashlib
import re

logger = logging.getLogger(__name__)

class VulnerabilityLevel(Enum):
    """漏洞级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class VulnerabilityType(Enum):
    """漏洞类型枚举"""
    SYSTEM = "system"
    SOFTWARE = "software"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    PRIVACY = "privacy"

@dataclass
class Vulnerability:
    """漏洞信息"""
    id: str
    vulnerability_type: VulnerabilityType
    level: VulnerabilityLevel
    title: str
    description: str
    affected_component: str
    detection_time: datetime
    details: Dict[str, Any]
    remediation: str
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['vulnerability_type'] = self.vulnerability_type.value
        data['level'] = self.level.value
        data['detection_time'] = self.detection_time.isoformat()
        return data

class SecurityScanner:
    """安全扫描器"""
    
    def __init__(self):
        self.is_scanning = False
        self.found_vulnerabilities: Dict[str, Vulnerability] = {}
        self.scan_progress: Dict[str, float] = {}
        self.scan_thread: Optional[threading.Thread] = None
        self.vulnerability_database = self._load_vulnerability_database()
        self._setup_logging()
        self._initialize_scanners()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_vulnerability_database(self) -> Dict[str, Any]:
        """加载漏洞数据库"""
        # 这里应该从外部安全数据库加载
        # 简化实现，使用内置规则
        return {
            "weak_passwords": {
                "level": VulnerabilityLevel.HIGH,
                "type": VulnerabilityType.SYSTEM,
                "description": "检测弱密码策略"
            },
            "outdated_software": {
                "level": VulnerabilityLevel.MEDIUM,
                "type": VulnerabilityType.SOFTWARE,
                "description": "检测过时软件"
            },
            "open_ports": {
                "level": VulnerabilityLevel.MEDIUM,
                "type": VulnerabilityType.NETWORK,
                "description": "检测开放的危险端口"
            },
            "insecure_configurations": {
                "level": VulnerabilityLevel.MEDIUM,
                "type": VulnerabilityType.CONFIGURATION,
                "description": "检测不安全配置"
            }
        }
    
    def _initialize_scanners(self):
        """初始化扫描器"""
        self.scanners = {
            "system_scanner": SystemScanner(),
            "software_scanner": SoftwareScanner(),
            "network_scanner": NetworkScanner(),
            "configuration_scanner": ConfigurationScanner(),
            "privacy_scanner": PrivacyScanner()
        }
    
    def start_full_scan(self) -> bool:
        """开始完整安全扫描"""
        if self.is_scanning:
            return False
        
        try:
            self.is_scanning = True
            self.scan_thread = threading.Thread(
                target=self._full_scan_loop,
                daemon=True
            )
            self.scan_thread.start()
            
            logger.info("开始完整安全扫描")
            return True
            
        except Exception as e:
            logger.error(f"启动安全扫描失败: {str(e)}")
            return False
    
    def stop_scan(self) -> bool:
        """停止安全扫描"""
        if not self.is_scanning:
            return False
        
        try:
            self.is_scanning = False
            if self.scan_thread:
                self.scan_thread.join(timeout=30)
            
            logger.info("安全扫描已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止安全扫描失败: {str(e)}")
            return False
    
    def _full_scan_loop(self):
        """完整扫描循环"""
        try:
            # 重置进度
            self.scan_progress = {scanner: 0.0 for scanner in self.scanners}
            
            # 执行各种扫描
            scan_tasks = [
                ("system_scanner", self._scan_system_vulnerabilities),
                ("software_scanner", self._scan_software_vulnerabilities),
                ("network_scanner", self._scan_network_vulnerabilities),
                ("configuration_scanner", self._scan_configuration_vulnerabilities),
                ("privacy_scanner", self._scan_privacy_vulnerabilities)
            ]
            
            total_tasks = len(scan_tasks)
            
            for i, (scanner_name, scan_function) in enumerate(scan_tasks):
                if not self.is_scanning:
                    break
                
                try:
                    # 更新进度
                    self.scan_progress[scanner_name] = 0.0
                    
                    # 执行扫描
                    vulnerabilities = scan_function()
                    
                    # 记录发现的漏洞
                    for vuln_data in vulnerabilities:
                        self._add_vulnerability(vuln_data)
                    
                    # 标记扫描完成
                    self.scan_progress[scanner_name] = 100.0
                    
                except Exception as e:
                    logger.error(f"扫描 {scanner_name} 失败: {str(e)}")
                    self.scan_progress[scanner_name] = -1.0  # 错误状态
            
            self.is_scanning = False
            logger.info("完整安全扫描完成")
            
        except Exception as e:
            logger.error(f"完整扫描循环错误: {str(e)}")
            self.is_scanning = False
    
    def _scan_system_vulnerabilities(self) -> List[Dict[str, Any]]:
        """扫描系统漏洞"""
        vulnerabilities = []
        system_scanner = self.scanners["system_scanner"]
        
        try:
            # 扫描系统更新
            vulns = system_scanner.check_system_updates()
            vulnerabilities.extend(vulns)
            
            # 扫描用户账户
            vulns = system_scanner.check_user_accounts()
            vulnerabilities.extend(vulns)
            
            # 扫描系统配置
            vulns = system_scanner.check_system_configurations()
            vulnerabilities.extend(vulns)
            
        except Exception as e:
            logger.error(f"扫描系统漏洞失败: {str(e)}")
        
        return vulnerabilities
    
    def _scan_software_vulnerabilities(self) -> List[Dict[str, Any]]:
        """扫描软件漏洞"""
        vulnerabilities = []
        software_scanner = self.scanners["software_scanner"]
        
        try:
            # 扫描已安装软件
            vulns = software_scanner.scan_installed_software()
            vulnerabilities.extend(vulns)
            
            # 检查软件更新
            vulns = software_scanner.check_software_updates()
            vulnerabilities.extend(vulns)
            
            # 检查已知漏洞
            vulns = software_scanner.check_known_vulnerabilities()
            vulnerabilities.extend(vulns)
            
        except Exception as e:
            logger.error(f"扫描软件漏洞失败: {str(e)}")
        
        return vulnerabilities
    
    def _scan_network_vulnerabilities(self) -> List[Dict[str, Any]]:
        """扫描网络漏洞"""
        vulnerabilities = []
        network_scanner = self.scanners["network_scanner"]
        
        try:
            # 扫描开放端口
            vulns = network_scanner.scan_open_ports()
            vulnerabilities.extend(vulns)
            
            # 检查网络配置
            vulns = network_scanner.check_network_configurations()
            vulnerabilities.extend(vulns)
            
            # 检查防火墙设置
            vulns = network_scanner.check_firewall_settings()
            vulnerabilities.extend(vulns)
            
        except Exception as e:
            logger.error(f"扫描网络漏洞失败: {str(e)}")
        
        return vulnerabilities
    
    def _scan_configuration_vulnerabilities(self) -> List[Dict[str, Any]]:
        """扫描配置漏洞"""
        vulnerabilities = []
        configuration_scanner = self.scanners["configuration_scanner"]
        
        try:
            # 扫描系统配置
            vulns = configuration_scanner.scan_system_configurations()
            vulnerabilities.extend(vulns)
            
            # 扫描安全策略
            vulns = configuration_scanner.scan_security_policies()
            vulnerabilities.extend(vulns)
            
            # 扫描注册表设置
            vulns = configuration_scanner.scan_registry_settings()
            vulnerabilities.extend(vulns)
            
        except Exception as e:
            logger.error(f"扫描配置漏洞失败: {str(e)}")
        
        return vulnerabilities
    
    def _scan_privacy_vulnerabilities(self) -> List[Dict[str, Any]]:
        """扫描隐私漏洞"""
        vulnerabilities = []
        privacy_scanner = self.scanners["privacy_scanner"]
        
        try:
            # 扫描隐私设置
            vulns = privacy_scanner.scan_privacy_settings()
            vulnerabilities.extend(vulns)
            
            # 扫描数据泄露风险
            vulns = privacy_scanner.scan_data_leakage_risks()
            vulnerabilities.extend(vulns)
            
            # 扫描追踪设置
            vulns = privacy_scanner.scan_tracking_settings()
            vulnerabilities.extend(vulns)
            
        except Exception as e:
            logger.error(f"扫描隐私漏洞失败: {str(e)}")
        
        return vulnerabilities
    
    def _add_vulnerability(self, vuln_data: Dict[str, Any]):
        """添加漏洞"""
        try:
            vulnerability = Vulnerability(
                id=f"vuln_{int(time.time())}_{hash(str(vuln_data))}",
                vulnerability_type=VulnerabilityType(vuln_data['type']),
                level=VulnerabilityLevel(vuln_data['level']),
                title=vuln_data['title'],
                description=vuln_data['description'],
                affected_component=vuln_data.get('affected_component', 'Unknown'),
                detection_time=datetime.now(),
                details=vuln_data.get('details', {}),
                remediation=vuln_data.get('remediation', '暂无修复建议'),
                cve_id=vuln_data.get('cve_id'),
                cvss_score=vuln_data.get('cvss_score')
            )
            
            self.found_vulnerabilities[vulnerability.id] = vulnerability
            logger.warning(f"发现漏洞: {vulnerability.title} (级别: {vulnerability.level.value})")
            
        except Exception as e:
            logger.error(f"添加漏洞失败: {str(e)}")
    
    def get_scan_progress(self) -> Dict[str, float]:
        """获取扫描进度"""
        return self.scan_progress.copy()
    
    def get_found_vulnerabilities(self) -> List[Vulnerability]:
        """获取发现的漏洞"""
        return list(self.found_vulnerabilities.values())
    
    def get_vulnerability_statistics(self) -> Dict[str, Any]:
        """获取漏洞统计信息"""
        vulnerabilities = self.get_found_vulnerabilities()
        
        total_vulnerabilities = len(vulnerabilities)
        
        level_counts = {}
        type_counts = {}
        
        for vuln in vulnerabilities:
            level = vuln.level.value
            vuln_type = vuln.vulnerability_type.value
            
            level_counts[level] = level_counts.get(level, 0) + 1
            type_counts[vuln_type] = type_counts.get(vuln_type, 0) + 1
        
        # 计算风险评分 (0-100, 分数越高风险越高)
        risk_score = 0
        level_weights = {
            'critical': 10,
            'high': 7,
            'medium': 4,
            'low': 1
        }
        
        for level, count in level_counts.items():
            risk_score += count * level_weights.get(level, 1)
        
        risk_score = min(100, risk_score * 2)  # 归一化到0-100
        
        return {
            'total_vulnerabilities': total_vulnerabilities,
            'risk_score': risk_score,
            'vulnerabilities_by_level': level_counts,
            'vulnerabilities_by_type': type_counts
        }
    
    def generate_remediation_plan(self) -> Dict[str, Any]:
        """生成修复计划"""
        vulnerabilities = self.get_found_vulnerabilities()
        
        # 按优先级排序
        priority_order = {
            VulnerabilityLevel.CRITICAL: 0,
            VulnerabilityLevel.HIGH: 1,
            VulnerabilityLevel.MEDIUM: 2,
            VulnerabilityLevel.LOW: 3
        }
        
        sorted_vulnerabilities = sorted(
            vulnerabilities,
            key=lambda v: priority_order[v.level]
        )
        
        remediation_steps = []
        for vuln in sorted_vulnerabilities:
            remediation_steps.append({
                'vulnerability_id': vuln.id,
                'title': vuln.title,
                'level': vuln.level.value,
                'remediation': vuln.remediation,
                'priority': priority_order[vuln.level] + 1
            })
        
        return {
            'generated_time': datetime.now().isoformat(),
            'total_steps': len(remediation_steps),
            'remediation_steps': remediation_steps,
            'estimated_time': f"{len(remediation_steps) * 15} 分钟"  # 预估修复时间
        }
    
    def export_scan_report(self, file_path: str) -> bool:
        """导出扫描报告"""
        try:
            report = {
                'scan_time': datetime.now().isoformat(),
                'statistics': self.get_vulnerability_statistics(),
                'remediation_plan': self.generate_remediation_plan(),
                'vulnerabilities': [vuln.to_dict() for vuln in self.get_found_vulnerabilities()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"安全扫描报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出扫描报告失败: {str(e)}")
            return False

class SystemScanner:
    """系统扫描器"""
    
    def check_system_updates(self) -> List[Dict[str, Any]]:
        """检查系统更新"""
        vulnerabilities = []
        
        try:
            if platform.system() == "Windows":
                # 检查Windows更新状态
                result = subprocess.run(
                    ['wmic', 'qfe', 'list', 'brief'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode != 0:
                    vulnerabilities.append({
                        'type': 'system',
                        'level': 'medium',
                        'title': '系统更新检查失败',
                        'description': '无法检查Windows系统更新状态',
                        'remediation': '手动检查Windows更新或联系系统管理员',
                        'details': {'error': result.stderr}
                    })
            
            # 检查系统版本
            system_version = platform.version()
            if self._is_old_system_version(system_version):
                vulnerabilities.append({
                    'type': 'system',
                    'level': 'high',
                    'title': '系统版本过旧',
                    'description': f'当前系统版本 {system_version} 可能包含已知安全漏洞',
                    'remediation': '升级到最新的系统版本',
                    'details': {'current_version': system_version}
                })
        
        except Exception as e:
            logger.error(f"检查系统更新失败: {str(e)}")
        
        return vulnerabilities
    
    def _is_old_system_version(self, version: str) -> bool:
        """检查系统版本是否过旧"""
        # 简化实现，实际应该根据具体系统版本判断
        return "6.1" in version or "6.2" in version  # Windows 7/8
    
    def check_user_accounts(self) -> List[Dict[str, Any]]:
        """检查用户账户"""
        vulnerabilities = []
        
        try:
            # 检查管理员账户
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['net', 'user'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    users = result.stdout.split('\n')
                    admin_users = [user.strip() for user in users if 'Administrator' in user]
                    
                    if len(admin_users) > 1:
                        vulnerabilities.append({
                            'type': 'system',
                            'level': 'medium',
                            'title': '多个管理员账户',
                            'description': f'发现 {len(admin_users)} 个管理员账户',
                            'remediation': '限制管理员账户数量，仅保留必要的管理员账户',
                            'details': {'admin_users': admin_users}
                        })
        
        except Exception as e:
            logger.error(f"检查用户账户失败: {str(e)}")
        
        return vulnerabilities
    
    def check_system_configurations(self) -> List[Dict[str, Any]]:
        """检查系统配置"""
        vulnerabilities = []
        
        try:
            # 检查UAC设置 (Windows)
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
                    uac_value, _ = winreg.QueryValueEx(key, "EnableLUA")
                    winreg.CloseKey(key)
                    
                    if uac_value == 0:
                        vulnerabilities.append({
                            'type': 'system',
                            'level': 'high',
                            'title': 'UAC已禁用',
                            'description': '用户账户控制(UAC)已被禁用，降低系统安全性',
                            'remediation': '启用UAC以提高系统安全性',
                            'details': {'uac_enabled': False}
                        })
                
                except Exception:
                    vulnerabilities.append({
                        'type': 'system',
                        'level': 'medium',
                        'title': '无法检查UAC设置',
                        'description': '无法读取用户账户控制(UAC)设置',
                        'remediation': '手动检查UAC设置'
                    })
        
        except Exception as e:
            logger.error(f"检查系统配置失败: {str(e)}")
        
        return vulnerabilities

class SoftwareScanner:
    """软件扫描器"""
    
    def scan_installed_software(self) -> List[Dict[str, Any]]:
        """扫描已安装软件"""
        vulnerabilities = []
        
        try:
            if platform.system() == "Windows":
                # 获取已安装软件列表
                result = subprocess.run(
                    ['wmic', 'product', 'get', 'name,version'],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    software_list = []
                    lines = result.stdout.split('\n')
                    for line in lines[1:]:  # 跳过标题行
                        if line.strip():
                            parts = line.split('  ')
                            if len(parts) >= 2:
                                name = parts[0].strip()
                                version = parts[-1].strip()
                                software_list.append({'name': name, 'version': version})
                    
                    # 检查已知有漏洞的软件
                    for software in software_list:
                        vuln_info = self._check_software_vulnerability(software['name'], software['version'])
                        if vuln_info:
                            vulnerabilities.append(vuln_info)
        
        except Exception as e:
            logger.error(f"扫描已安装软件失败: {str(e)}")
        
        return vulnerabilities
    
    def _check_software_vulnerability(self, name: str, version: str) -> Optional[Dict[str, Any]]:
        """检查软件漏洞"""
        # 简化实现，实际应该查询CVE数据库
        vulnerable_software = {
            "Java": {"min_version": "0", "max_version": "8.0.111"},
            "Adobe Flash": {"min_version": "0", "max_version": "32.0.0.171"},
            "Internet Explorer": {"min_version": "0", "max_version": "11.0.9600.16428"}
        }
        
        for software, version_range in vulnerable_software.items():
            if software.lower() in name.lower():
                if self._is_version_in_range(version, version_range["min_version"], version_range["max_version"]):
                    return {
                        'type': 'software',
                        'level': 'high',
                        'title': f'{software} 版本过旧',
                        'description': f'{software} 版本 {version} 包含已知安全漏洞',
                        'affected_component': name,
                        'remediation': f'升级 {software} 到最新版本',
                        'details': {
                            'software_name': name,
                            'current_version': version,
                            'vulnerable_versions': f"{version_range['min_version']} - {version_range['max_version']}"
                        }
                    }
        
        return None
    
    def _is_version_in_range(self, version: str, min_version: str, max_version: str) -> bool:
        """检查版本是否在范围内"""
        try:
            # 简化版本比较
            version_parts = [int(part) for part in version.split('.') if part.isdigit()]
            max_parts = [int(part) for part in max_version.split('.') if part.isdigit()]
            
            # 比较主要版本
            return version_parts[0] <= max_parts[0] if version_parts and max_parts else False
            
        except Exception:
            return False
    
    def check_software_updates(self) -> List[Dict[str, Any]]:
        """检查软件更新"""
        # 实现软件更新检查逻辑
        return []
    
    def check_known_vulnerabilities(self) -> List[Dict[str, Any]]:
        """检查已知漏洞"""
        # 实现已知漏洞检查逻辑
        return []

class NetworkScanner:
    """网络扫描器"""
    
    def scan_open_ports(self) -> List[Dict[str, Any]]:
        """扫描开放端口"""
        vulnerabilities = []
        
        try:
            import socket
            
            # 常见危险端口
            dangerous_ports = [21, 23, 135, 139, 445, 1433, 3389, 5900]
            
            for port in dangerous_ports:
                if self._is_port_open('127.0.0.1', port):
                    vulnerabilities.append({
                        'type': 'network',
                        'level': 'medium',
                        'title': f'危险端口 {port} 开放',
                        'description': f'端口 {port} 对外开放，可能存在安全风险',
                        'remediation': f'关闭不必要的端口 {port} 或配置防火墙规则',
                        'details': {'port': port, 'service': self._get_port_service(port)}
                    })
        
        except Exception as e:
            logger.error(f"扫描开放端口失败: {str(e)}")
        
        return vulnerabilities
    
    def _is_port_open(self, host: str, port: int) -> bool:
        """检查端口是否开放"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def _get_port_service(self, port: int) -> str:
        """获取端口对应服务"""
        port_services = {
            21: "FTP", 23: "Telnet", 135: "RPC", 139: "NetBIOS",
            445: "SMB", 1433: "SQL Server", 3389: "RDP", 5900: "VNC"
        }
        return port_services.get(port, "Unknown")
    
    def check_network_configurations(self) -> List[Dict[str, Any]]:
        """检查网络配置"""
        vulnerabilities = []
        
        try:
            # 检查网络共享
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['net', 'share'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0 and len(result.stdout.strip().split('\n')) > 2:
                    vulnerabilities.append({
                        'type': 'network',
                        'level': 'medium',
                        'title': '发现网络共享',
                        'description': '系统配置了网络共享，可能泄露敏感数据',
                        'remediation': '审查网络共享设置，关闭不必要的共享',
                        'details': {'shares_found': True}
                    })
        
        except Exception as e:
            logger.error(f"检查网络配置失败: {str(e)}")
        
        return vulnerabilities
    
    def check_firewall_settings(self) -> List[Dict[str, Any]]:
        """检查防火墙设置"""
        vulnerabilities = []
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['netsh', 'advfirewall', 'show', 'allprofiles'],
                    capture_output=True, text=True, timeout=30
                )
                
                if "OFF" in result.stdout:
                    vulnerabilities.append({
                        'type': 'network',
                        'level': 'high',
                        'title': '防火墙未启用',
                        'description': 'Windows防火墙未在所有配置文件中启用',
                        'remediation': '启用Windows防火墙以提高网络安全性',
                        'details': {'firewall_status': 'disabled'}
                    })
        
        except Exception as e:
            logger.error(f"检查防火墙设置失败: {str(e)}")
        
        return vulnerabilities

class ConfigurationScanner:
    """配置扫描器"""
    
    def scan_system_configurations(self) -> List[Dict[str, Any]]:
        """扫描系统配置"""
        # 实现系统配置扫描
        return []
    
    def scan_security_policies(self) -> List[Dict[str, Any]]:
        """扫描安全策略"""
        # 实现安全策略扫描
        return []
    
    def scan_registry_settings(self) -> List[Dict[str, Any]]:
        """扫描注册表设置"""
        # 实现注册表设置扫描
        return []

class PrivacyScanner:
    """隐私扫描器"""
    
    def scan_privacy_settings(self) -> List[Dict[str, Any]]:
        """扫描隐私设置"""
        vulnerabilities = []
        
        try:
            # 检查遥测数据收集
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection")
                    allow_telemetry, _ = winreg.QueryValueEx(key, "AllowTelemetry")
                    winreg.CloseKey(key)
                    
                    if allow_telemetry > 0:
                        vulnerabilities.append({
                            'type': 'privacy',
                            'level': 'low',
                            'title': '遥测数据收集已启用',
                            'description': '系统正在收集使用数据并发送给Microsoft',
                            'remediation': '禁用遥测数据收集以保护隐私',
                            'details': {'telemetry_enabled': True, 'level': allow_telemetry}
                        })
                
                except FileNotFoundError:
                    # 注册表项不存在，使用默认设置
                    vulnerabilities.append({
                        'type': 'privacy',
                        'level': 'low',
                        'title': '遥测设置未配置',
                        'description': '遥测数据收集使用系统默认设置',
                        'remediation': '明确配置遥测设置以控制数据收集',
                        'details': {'telemetry_default': True}
                    })
        
        except Exception as e:
            logger.error(f"扫描隐私设置失败: {str(e)}")
        
        return vulnerabilities
    
    def scan_data_leakage_risks(self) -> List[Dict[str, Any]]:
        """扫描数据泄露风险"""
        # 实现数据泄露风险扫描
        return []
    
    def scan_tracking_settings(self) -> List[Dict[str, Any]]:
        """扫描追踪设置"""
        # 实现追踪设置扫描
        return []

# 单例实例
_security_scanner_instance = None

def get_security_scanner() -> SecurityScanner:
    """获取安全扫描器单例"""
    global _security_scanner_instance
    if _security_scanner_instance is None:
        _security_scanner_instance = SecurityScanner()
    return _security_scanner_instance
    

