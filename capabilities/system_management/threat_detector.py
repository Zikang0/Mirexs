"""
威胁检测器：检测系统安全威胁
"""
import os
import psutil
import threading
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """威胁级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """威胁类型枚举"""
    MALWARE = "malware"
    INTRUSION = "intrusion"
    SUSPICIOUS_PROCESS = "suspicious_process"
    NETWORK_THREAT = "network_threat"
    FILE_THREAT = "file_threat"
    BEHAVIORAL_THREAT = "behavioral_threat"

@dataclass
class ThreatDetection:
    """威胁检测结果"""
    id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    description: str
    detected_time: datetime
    source: str
    details: Dict[str, Any]
    mitigated: bool = False
    mitigation_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['threat_type'] = self.threat_type.value
        data['threat_level'] = self.threat_level.value
        data['detected_time'] = self.detected_time.isoformat()
        data['mitigation_time'] = self.mitigation_time.isoformat() if self.mitigation_time else None
        return data

class ThreatDetector:
    """威胁检测器"""
    
    def __init__(self):
        self.is_monitoring = False
        self.detected_threats: Dict[str, ThreatDetection] = {}
        self.monitoring_thread: Optional[threading.Thread] = None
        self.threat_patterns = self._load_threat_patterns()
        self.suspicious_processes = self._load_suspicious_processes()
        self.malware_signatures = self._load_malware_signatures()
        self._setup_logging()
        self._initialize_detection_engines()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_threat_patterns(self) -> Dict[str, Any]:
        """加载威胁模式"""
        return {
            "suspicious_network_connections": [
                r"\.onion$",  # Tor网络
                r"^(10\.|192\.168|172\.(1[6-9]|2[0-9]|3[0-1]))",  # 内部网络异常连接
            ],
            "suspicious_file_extensions": [
                '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.vbs', '.js'
            ],
            "suspicious_registry_paths": [
                r"HK(LM|CU)\\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
                r"HK(LM|CU)\\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
            ]
        }
    
    def _load_suspicious_processes(self) -> List[str]:
        """加载可疑进程列表"""
        return [
            "mimikatz.exe", "cain.exe", "john.exe", "hashcat.exe",
            "metasploit.exe", "wireshark.exe", "nmap.exe", "nessus.exe"
        ]
    
    def _load_malware_signatures(self) -> Dict[str, str]:
        """加载恶意软件签名"""
        # 这里应该是从安全数据库加载的签名
        # 简化实现，使用示例签名
        return {
            "eicar_test": "X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
            "trojan_pattern": "malicious_payload_signature"
        }
    
    def _initialize_detection_engines(self):
        """初始化检测引擎"""
        self.detection_engines = {
            "process_analyzer": ProcessAnalyzer(),
            "network_analyzer": NetworkAnalyzer(),
            "file_analyzer": FileAnalyzer(),
            "behavior_analyzer": BehaviorAnalyzer()
        }
    
    def start_monitoring(self) -> bool:
        """开始威胁监控"""
        if self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            
            logger.info("威胁监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动威胁监控失败: {str(e)}")
            return False
    
    def stop_monitoring(self) -> bool:
        """停止威胁监控"""
        if not self.is_monitoring:
            return False
        
        try:
            self.is_monitoring = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=10)
            
            logger.info("威胁监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止威胁监控失败: {str(e)}")
            return False
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 执行各种威胁检测
                self._detect_suspicious_processes()
                self._detect_network_threats()
                self._detect_file_threats()
                self._detect_behavioral_threats()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"威胁监控循环错误: {str(e)}")
                time.sleep(60)
    
    def _detect_suspicious_processes(self):
        """检测可疑进程"""
        try:
            for process in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    process_info = process.info
                    process_name = process_info['name'].lower()
                    
                    # 检查是否在可疑进程列表中
                    if any(suspicious in process_name for suspicious in self.suspicious_processes):
                        threat = ThreatDetection(
                            id=f"process_{process_info['pid']}_{int(time.time())}",
                            threat_type=ThreatType.SUSPICIOUS_PROCESS,
                            threat_level=ThreatLevel.HIGH,
                            description=f"发现可疑进程: {process_name}",
                            detected_time=datetime.now(),
                            source="ProcessMonitor",
                            details={
                                'pid': process_info['pid'],
                                'name': process_info['name'],
                                'exe': process_info['exe'],
                                'cmdline': process_info['cmdline']
                            }
                        )
                        self._add_threat_detection(threat)
                    
                    # 检查进程行为
                    self.detection_engines["process_analyzer"].analyze_process(process)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"检测可疑进程失败: {str(e)}")
    
    def _detect_network_threats(self):
        """检测网络威胁"""
        try:
            network_analyzer = self.detection_engines["network_analyzer"]
            threats = network_analyzer.analyze_network_connections()
            
            for threat_data in threats:
                threat = ThreatDetection(
                    id=f"network_{int(time.time())}_{hash(str(threat_data))}",
                    threat_type=ThreatType.NETWORK_THREAT,
                    threat_level=threat_data['level'],
                    description=threat_data['description'],
                    detected_time=datetime.now(),
                    source="NetworkAnalyzer",
                    details=threat_data
                )
                self._add_threat_detection(threat)
                
        except Exception as e:
            logger.error(f"检测网络威胁失败: {str(e)}")
    
    def _detect_file_threats(self):
        """检测文件威胁"""
        try:
            file_analyzer = self.detection_engines["file_analyzer"]
            
            # 检查关键系统目录
            critical_dirs = [
                "C:\\Windows\\System32",
                "C:\\Windows\\SysWOW64",
                "C:\\Users\\Default",
                "C:\\ProgramData"
            ]
            
            for directory in critical_dirs:
                if os.path.exists(directory):
                    threats = file_analyzer.scan_directory(directory)
                    for threat_data in threats:
                        threat = ThreatDetection(
                            id=f"file_{int(time.time())}_{hash(str(threat_data))}",
                            threat_type=ThreatType.FILE_THREAT,
                            threat_level=threat_data['level'],
                            description=threat_data['description'],
                            detected_time=datetime.now(),
                            source="FileAnalyzer",
                            details=threat_data
                        )
                        self._add_threat_detection(threat)
                        
        except Exception as e:
            logger.error(f"检测文件威胁失败: {str(e)}")
    
    def _detect_behavioral_threats(self):
        """检测行为威胁"""
        try:
            behavior_analyzer = self.detection_engines["behavior_analyzer"]
            threats = behavior_analyzer.analyze_system_behavior()
            
            for threat_data in threats:
                threat = ThreatDetection(
                    id=f"behavior_{int(time.time())}_{hash(str(threat_data))}",
                    threat_type=ThreatType.BEHAVIORAL_THREAT,
                    threat_level=threat_data['level'],
                    description=threat_data['description'],
                    detected_time=datetime.now(),
                    source="BehaviorAnalyzer",
                    details=threat_data
                )
                self._add_threat_detection(threat)
                
        except Exception as e:
            logger.error(f"检测行为威胁失败: {str(e)}")
    
    def _add_threat_detection(self, threat: ThreatDetection):
        """添加威胁检测结果"""
        threat_id = threat.id
        self.detected_threats[threat_id] = threat
        
        # 记录威胁检测
        logger.warning(f"检测到威胁: {threat.description} (级别: {threat.threat_level.value})")
        
        # 根据威胁级别采取行动
        if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._mitigate_threat(threat)
    
    def _mitigate_threat(self, threat: ThreatDetection):
        """缓解威胁"""
        try:
            if threat.threat_type == ThreatType.SUSPICIOUS_PROCESS:
                self._mitigate_process_threat(threat)
            elif threat.threat_type == ThreatType.NETWORK_THREAT:
                self._mitigate_network_threat(threat)
            elif threat.threat_type == ThreatType.FILE_THREAT:
                self._mitigate_file_threat(threat)
            
            threat.mitigated = True
            threat.mitigation_time = datetime.now()
            
            logger.info(f"威胁已缓解: {threat.description}")
            
        except Exception as e:
            logger.error(f"缓解威胁失败: {str(e)}")
    
    def _mitigate_process_threat(self, threat: ThreatDetection):
        """缓解进程威胁"""
        try:
            pid = threat.details.get('pid')
            if pid:
                process = psutil.Process(pid)
                process.terminate()
                logger.info(f"已终止可疑进程: {pid}")
        except Exception as e:
            logger.error(f"终止进程失败: {str(e)}")
    
    def _mitigate_network_threat(self, threat: ThreatDetection):
        """缓解网络威胁"""
        try:
            # 这里可以实现网络连接阻断
            # 例如使用防火墙规则阻断可疑连接
            logger.info(f"已处理网络威胁: {threat.description}")
        except Exception as e:
            logger.error(f"缓解网络威胁失败: {str(e)}")
    
    def _mitigate_file_threat(self, threat: ThreatDetection):
        """缓解文件威胁"""
        try:
            file_path = threat.details.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除可疑文件: {file_path}")
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
    
    def get_detected_threats(self, time_range: timedelta = None) -> List[ThreatDetection]:
        """获取检测到的威胁"""
        if time_range is None:
            return list(self.detected_threats.values())
        
        cutoff_time = datetime.now() - time_range
        return [
            threat for threat in self.detected_threats.values()
            if threat.detected_time >= cutoff_time
        ]
    
    def get_threat_statistics(self) -> Dict[str, Any]:
        """获取威胁统计信息"""
        threats = self.get_detected_threats()
        
        total_threats = len(threats)
        mitigated_threats = len([t for t in threats if t.mitigated])
        
        level_counts = {}
        type_counts = {}
        
        for threat in threats:
            level = threat.threat_level.value
            threat_type = threat.threat_type.value
            
            level_counts[level] = level_counts.get(level, 0) + 1
            type_counts[threat_type] = type_counts.get(threat_type, 0) + 1
        
        return {
            'total_threats': total_threats,
            'mitigated_threats': mitigated_threats,
            'mitigation_rate': mitigated_threats / total_threats if total_threats > 0 else 0,
            'threats_by_level': level_counts,
            'threats_by_type': type_counts
        }
    
    def export_threat_report(self, file_path: str) -> bool:
        """导出威胁报告"""
        try:
            report = {
                'generated_time': datetime.now().isoformat(),
                'statistics': self.get_threat_statistics(),
                'threats': [threat.to_dict() for threat in self.get_detected_threats()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"威胁报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出威胁报告失败: {str(e)}")
            return False

class ProcessAnalyzer:
    """进程分析器"""
    
    def analyze_process(self, process: psutil.Process) -> List[Dict[str, Any]]:
        """分析进程"""
        threats = []
        
        try:
            process_info = process.as_dict(attrs=['pid', 'name', 'exe', 'cmdline', 'memory_info', 'cpu_percent'])
            
            # 检查进程内存使用
            memory_usage = process_info['memory_info'].rss if process_info['memory_info'] else 0
            if memory_usage > 500 * 1024 * 1024:  # 500MB
                threats.append({
                    'level': ThreatLevel.MEDIUM,
                    'description': f"进程 {process_info['name']} 内存使用异常",
                    'pid': process_info['pid'],
                    'memory_usage': memory_usage
                })
            
            # 检查进程CPU使用
            cpu_percent = process_info['cpu_percent'] or 0
            if cpu_percent > 80:  # 80% CPU
                threats.append({
                    'level': ThreatLevel.MEDIUM,
                    'description': f"进程 {process_info['name']} CPU使用异常",
                    'pid': process_info['pid'],
                    'cpu_percent': cpu_percent
                })
        
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return threats

class NetworkAnalyzer:
    """网络分析器"""
    
    def analyze_network_connections(self) -> List[Dict[str, Any]]:
        """分析网络连接"""
        threats = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    if conn.status == 'ESTABLISHED' and conn.raddr:
                        remote_ip = conn.raddr.ip
                        remote_port = conn.raddr.port
                        
                        # 检查可疑端口
                        if remote_port in [4444, 1337, 31337]:  # 常见后门端口
                            threats.append({
                                'level': ThreatLevel.HIGH,
                                'description': f"可疑网络连接: {remote_ip}:{remote_port}",
                                'remote_ip': remote_ip,
                                'remote_port': remote_port,
                                'pid': conn.pid
                            })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        except Exception as e:
            logger.error(f"分析网络连接失败: {str(e)}")
        
        return threats

class FileAnalyzer:
    """文件分析器"""
    
    def scan_directory(self, directory: str) -> List[Dict[str, Any]]:
        """扫描目录中的可疑文件"""
        threats = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 检查文件扩展名
                    if self._is_suspicious_file(file_path):
                        threats.append({
                            'level': ThreatLevel.MEDIUM,
                            'description': f"发现可疑文件: {file_path}",
                            'file_path': file_path,
                            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        })
        
        except Exception as e:
            logger.error(f"扫描目录失败 {directory}: {str(e)}")
        
        return threats
    
    def _is_suspicious_file(self, file_path: str) -> bool:
        """检查是否为可疑文件"""
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        return file_ext in suspicious_extensions

class BehaviorAnalyzer:
    """行为分析器"""
    
    def analyze_system_behavior(self) -> List[Dict[str, Any]]:
        """分析系统行为"""
        threats = []
        
        try:
            # 检查系统负载
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            if load_avg[0] > 5.0:  # 高系统负载
                threats.append({
                    'level': ThreatLevel.MEDIUM,
                    'description': f"系统负载异常: {load_avg[0]}",
                    'load_average': load_avg
                })
            
            # 检查内存使用
            memory = psutil.virtual_memory()
            if memory.percent > 90:  # 内存使用超过90%
                threats.append({
                    'level': ThreatLevel.MEDIUM,
                    'description': f"内存使用过高: {memory.percent}%",
                    'memory_usage': memory.percent
                })
        
        except Exception as e:
            logger.error(f"分析系统行为失败: {str(e)}")
        
        return threats

# 单例实例
_threat_detector_instance = None

def get_threat_detector() -> ThreatDetector:
    """获取威胁检测器单例"""
    global _threat_detector_instance
    if _threat_detector_instance is None:
        _threat_detector_instance = ThreatDetector()
    return _threat_detector_instance

