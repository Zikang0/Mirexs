"""
诊断工具：系统问题诊断
"""
import psutil
import platform
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime
import json
from pathlib import Path
import subprocess
import os
import re
import tempfile

logger = logging.getLogger(__name__)

class DiagnosticLevel(Enum):
    """诊断级别枚举"""
    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"

class ProblemSeverity(Enum):
    """问题严重性枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DiagnosticResult:
    """诊断结果"""
    id: str
    category: str
    name: str
    severity: ProblemSeverity
    description: str
    timestamp: datetime
    details: Dict[str, Any]
    solution: str
    confidence: float  # 0-1 置信度
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class SystemDiagnosis:
    """系统诊断"""
    diagnosis_id: str
    level: DiagnosticLevel
    start_time: datetime
    end_time: datetime
    problems_found: int
    results: List[DiagnosticResult]
    summary: str
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['level'] = self.level.value
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        data['results'] = [result.to_dict() for result in self.results]
        return data

class DiagnosticTool:
    """诊断工具"""
    
    def __init__(self):
        self.is_diagnosing = False
        self.diagnosis_history: List[SystemDiagnosis] = []
        self.diagnosis_thread: Optional[threading.Thread] = None
        self.current_progress = 0.0
        self.current_operation = ""
        self._setup_logging()
        self._initialize_diagnostic_tests()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _initialize_diagnostic_tests(self):
        """初始化诊断测试"""
        self.diagnostic_tests = {
            "system": [
                self._test_system_stability,
                self._test_hardware_health,
                self._test_power_management
            ],
            "performance": [
                self._test_performance_bottlenecks,
                self._test_memory_leaks,
                self._test_disk_performance
            ],
            "software": [
                self._test_software_conflicts,
                self._test_driver_issues,
                self._test_service_problems
            ],
            "network": [
                self._test_network_connectivity,
                self._test_dns_issues,
                self._test_firewall_problems
            ],
            "security": [
                self._test_security_vulnerabilities,
                self._test_malware_signs,
                self._test_privacy_issues
            ]
        }
    
    def run_diagnosis(self, level: DiagnosticLevel = DiagnosticLevel.STANDARD) -> bool:
        """运行诊断"""
        if self.is_diagnosing:
            return False
        
        try:
            self.is_diagnosing = True
            self.current_progress = 0.0
            
            # 在单独线程中执行诊断
            self.diagnosis_thread = threading.Thread(
                target=self._diagnosis_worker,
                args=(level,),
                daemon=True
            )
            self.diagnosis_thread.start()
            
            logger.info(f"开始系统诊断: {level.value}")
            return True
            
        except Exception as e:
            logger.error(f"启动系统诊断失败: {str(e)}")
            return False
    
    def _diagnosis_worker(self, level: DiagnosticLevel):
        """诊断工作线程"""
        try:
            diagnosis_id = f"diagnosis_{int(time.time())}"
            start_time = datetime.now()
            
            # 执行诊断测试
            test_results = []
            total_tests = sum(len(tests) for tests in self.diagnostic_tests.values())
            completed_tests = 0
            
            for category, tests in self.diagnostic_tests.items():
                for test_function in tests:
                    if not self.is_diagnosing:
                        break
                    
                    self.current_operation = f"执行 {category} 诊断"
                    
                    try:
                        results = test_function(level)
                        if results:
                            test_results.extend(results)
                    except Exception as e:
                        logger.error(f"诊断测试失败 {test_function.__name__}: {str(e)}")
                    
                    completed_tests += 1
                    self.current_progress = (completed_tests / total_tests) * 100
                    
                    # 根据诊断级别调整延迟
                    if level == DiagnosticLevel.QUICK:
                        time.sleep(0.5)
                    elif level == DiagnosticLevel.STANDARD:
                        time.sleep(1)
                    else:
                        time.sleep(2)
                
                if not self.is_diagnosing:
                    break
            
            end_time = datetime.now()
            
            if self.is_diagnosing:
                # 生成诊断报告
                diagnosis = self._generate_diagnosis_report(
                    diagnosis_id, level, start_time, end_time, test_results
                )
                self.diagnosis_history.append(diagnosis)
                
                logger.info(f"系统诊断完成: 发现 {diagnosis.problems_found} 个问题")
            else:
                logger.warning("系统诊断被取消")
            
            self.is_diagnosing = False
            self.current_progress = 0.0
            self.current_operation = ""
            
        except Exception as e:
            logger.error(f"诊断工作线程错误: {str(e)}")
            self.is_diagnosing = False
            self.current_progress = 0.0
            self.current_operation = ""
    
    def _generate_diagnosis_report(self, diagnosis_id: str, level: DiagnosticLevel,
                                 start_time: datetime, end_time: datetime, 
                                 results: List[DiagnosticResult]) -> SystemDiagnosis:
        """生成诊断报告"""
        # 统计问题数量
        problems_found = len(results)
        
        # 按严重性排序结果
        severity_order = {
            ProblemSeverity.CRITICAL: 0,
            ProblemSeverity.HIGH: 1,
            ProblemSeverity.MEDIUM: 2,
            ProblemSeverity.LOW: 3
        }
        sorted_results = sorted(results, key=lambda r: severity_order[r.severity])
        
        # 生成摘要
        critical_count = len([r for r in results if r.severity == ProblemSeverity.CRITICAL])
        high_count = len([r for r in results if r.severity == ProblemSeverity.HIGH])
        
        if critical_count > 0:
            summary = f"发现 {critical_count} 个严重问题，需要立即处理"
        elif high_count > 0:
            summary = f"发现 {high_count} 个重要问题，建议尽快处理"
        elif problems_found > 0:
            summary = f"发现 {problems_found} 个问题，建议关注"
        else:
            summary = "系统状态良好，未发现明显问题"
        
        # 生成建议
        recommendations = self._generate_recommendations(results)
        
        return SystemDiagnosis(
            diagnosis_id=diagnosis_id,
            level=level,
            start_time=start_time,
            end_time=end_time,
            problems_found=problems_found,
            results=sorted_results,
            summary=summary,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, results: List[DiagnosticResult]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于诊断结果生成建议
        critical_results = [r for r in results if r.severity == ProblemSeverity.CRITICAL]
        high_results = [r for r in results if r.severity == ProblemSeverity.HIGH]
        
        if any(r.category == "performance" for r in critical_results + high_results):
            recommendations.append("优化系统性能，关闭不必要的应用程序")
        
        if any(r.category == "security" for r in critical_results + high_results):
            recommendations.append("加强系统安全配置，更新安全软件")
        
        if any(r.category == "software" for r in critical_results + high_results):
            recommendations.append("更新或重新安装有问题的软件")
        
        if any(r.category == "network" for r in critical_results + high_results):
            recommendations.append("检查网络配置和连接状态")
        
        if not recommendations:
            recommendations.append("系统状态良好，保持当前配置")
        
        return recommendations
    
    # 系统诊断测试方法
    
    def _test_system_stability(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试系统稳定性"""
        results = []
        
        try:
            # 检查系统运行时间
            boot_time = psutil.boot_time()
            uptime_hours = (time.time() - boot_time) / 3600
            
            if uptime_hours > 168:  # 1周
                results.append(DiagnosticResult(
                    id="system_uptime_long",
                    category="system",
                    name="系统运行时间过长",
                    severity=ProblemSeverity.MEDIUM,
                    description=f"系统已连续运行 {uptime_hours:.1f} 小时",
                    timestamp=datetime.now(),
                    details={'uptime_hours': uptime_hours},
                    solution="建议定期重启系统以保持稳定性",
                    confidence=0.8
                ))
            
            # 检查系统错误日志
            error_count = self._check_system_errors()
            if error_count > 10:
                results.append(DiagnosticResult(
                    id="system_errors_high",
                    category="system",
                    name="系统错误较多",
                    severity=ProblemSeverity.HIGH,
                    description=f"检测到 {error_count} 个系统错误",
                    timestamp=datetime.now(),
                    details={'error_count': error_count},
                    solution="检查系统日志并解决相关问题",
                    confidence=0.7
                ))
            
        except Exception as e:
            logger.error(f"系统稳定性测试失败: {str(e)}")
        
        return results
    
    def _test_hardware_health(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试硬件健康"""
        results = []
        
        try:
            # 检查温度
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.critical:
                            temp_ratio = entry.current / entry.critical
                            if temp_ratio > 0.9:
                                results.append(DiagnosticResult(
                                    id="hardware_temperature_high",
                                    category="system",
                                    name="硬件温度过高",
                                    severity=ProblemSeverity.HIGH,
                                    description=f"{name} 温度接近临界值: {entry.current}°C",
                                    timestamp=datetime.now(),
                                    details={
                                        'sensor': name,
                                        'current_temp': entry.current,
                                        'critical_temp': entry.critical
                                    },
                                    solution="改善散热条件，清理灰尘",
                                    confidence=0.9
                                ))
            
            # 检查硬盘健康
            disk_health = self._check_disk_health()
            if not disk_health.get('healthy', True):
                results.append(DiagnosticResult(
                    id="disk_health_poor",
                    category="system",
                    name="磁盘健康状态不佳",
                    severity=ProblemSeverity.CRITICAL,
                    description="检测到磁盘健康问题",
                    timestamp=datetime.now(),
                    details=disk_health,
                    solution="备份重要数据并考虑更换硬盘",
                    confidence=0.6
                ))
            
        except Exception as e:
            logger.error(f"硬件健康测试失败: {str(e)}")
        
        return results
    
    def _test_power_management(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试电源管理"""
        results = []
        
        try:
            battery = psutil.sensors_battery()
            if battery:
                if not battery.power_plugged and battery.percent < 10:
                    results.append(DiagnosticResult(
                        id="battery_low",
                        category="system",
                        name="电池电量严重不足",
                        severity=ProblemSeverity.HIGH,
                        description=f"电池电量仅剩 {battery.percent}%",
                        timestamp=datetime.now(),
                        details={
                            'battery_percent': battery.percent,
                            'power_plugged': battery.power_plugged
                        },
                        solution="立即连接电源适配器",
                        confidence=1.0
                    ))
                
                if battery.power_plugged and battery.percent == 100:
                    results.append(DiagnosticResult(
                        id="battery_overcharged",
                        category="system",
                        name="电池已充满但仍连接电源",
                        severity=ProblemSeverity.LOW,
                        description="电池已充满电，建议拔掉电源适配器",
                        timestamp=datetime.now(),
                        details={'battery_percent': battery.percent},
                        solution="定期使用电池供电以保持电池健康",
                        confidence=0.8
                    ))
            
        except Exception as e:
            logger.error(f"电源管理测试失败: {str(e)}")
        
        return results
    
    # 性能诊断测试方法
    
    def _test_performance_bottlenecks(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试性能瓶颈"""
        results = []
        
        try:
            # 检查CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                results.append(DiagnosticResult(
                    id="cpu_bottleneck",
                    category="performance",
                    name="CPU性能瓶颈",
                    severity=ProblemSeverity.HIGH,
                    description=f"CPU使用率过高: {cpu_percent:.1f}%",
                    timestamp=datetime.now(),
                    details={'cpu_percent': cpu_percent},
                    solution="关闭不必要的应用程序，优化CPU使用",
                    confidence=0.8
                ))
            
            # 检查内存使用率
            memory = psutil.virtual_memory()
            if memory.percent > 95:
                results.append(DiagnosticResult(
                    id="memory_bottleneck",
                    category="performance",
                    name="内存性能瓶颈",
                    severity=ProblemSeverity.CRITICAL,
                    description=f"内存使用率过高: {memory.percent:.1f}%",
                    timestamp=datetime.now(),
                    details={'memory_percent': memory.percent},
                    solution="增加物理内存或关闭内存密集型应用程序",
                    confidence=0.9
                ))
            
            # 检查磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 98:
                results.append(DiagnosticResult(
                    id="disk_space_bottleneck",
                    category="performance",
                    name="磁盘空间不足",
                    severity=ProblemSeverity.CRITICAL,
                    description=f"磁盘空间严重不足: {disk_percent:.1f}% 已使用",
                    timestamp=datetime.now(),
                    details={'disk_percent': disk_percent},
                    solution="立即清理磁盘空间，删除不必要的文件",
                    confidence=1.0
                ))
            
        except Exception as e:
            logger.error(f"性能瓶颈测试失败: {str(e)}")
        
        return results
    
    def _test_memory_leaks(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试内存泄漏"""
        results = []
        
        try:
            # 检查内存使用趋势
            memory_history = []
            for _ in range(5):
                memory = psutil.virtual_memory()
                memory_history.append(memory.percent)
                time.sleep(1)
            
            # 检查内存使用是否持续增长
            if (memory_history[-1] > memory_history[0] + 10 and 
                memory_history[-1] > 80):
                results.append(DiagnosticResult(
                    id="possible_memory_leak",
                    category="performance",
                    name="可能的内存泄漏",
                    severity=ProblemSeverity.MEDIUM,
                    description="检测到内存使用持续增长",
                    timestamp=datetime.now(),
                    details={'memory_trend': memory_history},
                    solution="检查应用程序内存使用，重启有问题的程序",
                    confidence=0.6
                ))
            
        except Exception as e:
            logger.error(f"内存泄漏测试失败: {str(e)}")
        
        return results
    
    def _test_disk_performance(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试磁盘性能"""
        results = []
        
        try:
            # 检查磁盘IO
            disk_io = psutil.disk_io_counters()
            if disk_io:
                # 简化实现，实际应该进行性能基准测试
                read_time = disk_io.read_time / 1000 if disk_io.read_time else 0  # 转换为秒
                write_time = disk_io.write_time / 1000 if disk_io.write_time else 0
                
                if read_time > 1000 or write_time > 1000:  # 如果IO时间过长
                    results.append(DiagnosticResult(
                        id="disk_performance_slow",
                        category="performance",
                        name="磁盘性能较慢",
                        severity=ProblemSeverity.MEDIUM,
                        description="检测到磁盘IO性能问题",
                        timestamp=datetime.now(),
                        details={
                            'read_time': read_time,
                            'write_time': write_time
                        },
                        solution="进行磁盘碎片整理或考虑升级到SSD",
                        confidence=0.5
                    ))
            
        except Exception as e:
            logger.error(f"磁盘性能测试失败: {str(e)}")
        
        return results
    
    # 软件诊断测试方法
    
    def _test_software_conflicts(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试软件冲突"""
        results = []
        
        try:
            # 检查重复的进程
            process_names = {}
            for process in psutil.process_iter(['name']):
                try:
                    process_name = process.info['name']
                    process_names[process_name] = process_names.get(process_name, 0) + 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 查找可能有冲突的重复进程
            for name, count in process_names.items():
                if count > 3 and len(name) > 3:  # 忽略系统进程
                    results.append(DiagnosticResult(
                        id="multiple_process_instances",
                        category="software",
                        name="多个相同进程实例",
                        severity=ProblemSeverity.LOW,
                        description=f"发现 {count} 个 {name} 进程实例",
                        timestamp=datetime.now(),
                        details={'process_name': name, 'instance_count': count},
                        solution="检查是否有不必要的进程重复启动",
                        confidence=0.4
                    ))
            
        except Exception as e:
            logger.error(f"软件冲突测试失败: {str(e)}")
        
        return results
    
    def _test_driver_issues(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试驱动程序问题"""
        results = []
        
        try:
            if platform.system() == "Windows":
                # 检查设备管理器错误
                result = subprocess.run(
                    ['powershell', 'Get-WmiObject -Class Win32_PnPEntity | Where-Object {$_.ConfigManagerErrorCode -ne 0}'],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    error_count = len(result.stdout.strip().split('\n')) - 1
                    if error_count > 0:
                        results.append(DiagnosticResult(
                            id="driver_issues",
                            category="software",
                            name="驱动程序问题",
                            severity=ProblemSeverity.MEDIUM,
                            description=f"发现 {error_count} 个驱动程序问题",
                            timestamp=datetime.now(),
                            details={'driver_errors': error_count},
                            solution="更新或重新安装有问题的驱动程序",
                            confidence=0.7
                        ))
            
        except Exception as e:
            logger.error(f"驱动程序测试失败: {str(e)}")
        
        return results
    
    def _test_service_problems(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试服务问题"""
        results = []
        
        try:
            # 检查关键服务状态
            critical_services = []
            if platform.system() == "Windows":
                critical_services = ["Themes", "AudioSrv", "Netman"]
            
            for service_name in critical_services:
                try:
                    service = psutil.win_service_get(service_name)
                    if service.status() != "running":
                        results.append(DiagnosticResult(
                            id=f"service_{service_name}_stopped",
                            category="software",
                            name="关键服务未运行",
                            severity=ProblemSeverity.HIGH,
                            description=f"关键服务 {service_name} 未运行",
                            timestamp=datetime.now(),
                            details={'service_name': service_name, 'status': service.status()},
                            solution=f"启动 {service_name} 服务",
                            confidence=1.0
                        ))
                except Exception:
                    pass  # 服务不存在或无法访问
            
        except Exception as e:
            logger.error(f"服务问题测试失败: {str(e)}")
        
        return results
    
    # 网络诊断测试方法
    
    def _test_network_connectivity(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试网络连通性"""
        results = []
        
        try:
            import socket
            
            # 测试基本网络连接
            test_targets = [
                ("8.8.8.8", 53, "Google DNS"),
                ("1.1.1.1", 53, "Cloudflare DNS")
            ]
            
            failed_tests = 0
            for target, port, description in test_targets:
                try:
                    socket.create_connection((target, port), timeout=5)
                except Exception:
                    failed_tests += 1
            
            if failed_tests == len(test_targets):
                results.append(DiagnosticResult(
                    id="network_connectivity_failed",
                    category="network",
                    name="网络连接失败",
                    severity=ProblemSeverity.CRITICAL,
                    description="无法连接到互联网",
                    timestamp=datetime.now(),
                    details={'failed_tests': failed_tests},
                    solution="检查网络连接和配置",
                    confidence=0.9
                ))
            
        except Exception as e:
            logger.error(f"网络连通性测试失败: {str(e)}")
        
        return results
    
    def _test_dns_issues(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试DNS问题"""
        results = []
        
        try:
            import socket
            
            # 测试DNS解析
            test_domains = ["google.com", "microsoft.com", "apple.com"]
            failed_resolutions = 0
            
            for domain in test_domains:
                try:
                    socket.gethostbyname(domain)
                except Exception:
                    failed_resolutions += 1
            
            if failed_resolutions > 0:
                results.append(DiagnosticResult(
                    id="dns_resolution_issues",
                    category="network",
                    name="DNS解析问题",
                    severity=ProblemSeverity.MEDIUM,
                    description=f"{failed_resolutions} 个域名解析失败",
                    timestamp=datetime.now(),
                    details={'failed_resolutions': failed_resolutions},
                    solution="检查DNS服务器配置或更换DNS服务器",
                    confidence=0.8
                ))
            
        except Exception as e:
            logger.error(f"DNS问题测试失败: {str(e)}")
        
        return results
    
    def _test_firewall_problems(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试防火墙问题"""
        results = []
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['netsh', 'advfirewall', 'show', 'allprofiles'],
                    capture_output=True, text=True
                )
                
                if "OFF" in result.stdout:
                    results.append(DiagnosticResult(
                        id="firewall_disabled",
                        category="network",
                        name="防火墙未启用",
                        severity=ProblemSeverity.HIGH,
                        description="系统防火墙未启用",
                        timestamp=datetime.now(),
                        details={'firewall_status': 'disabled'},
                        solution="启用Windows防火墙以提高安全性",
                        confidence=1.0
                    ))
            
        except Exception as e:
            logger.error(f"防火墙问题测试失败: {str(e)}")
        
        return results
    
    # 安全诊断测试方法
    
    def _test_security_vulnerabilities(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试安全漏洞"""
        results = []
        
        try:
            # 检查系统更新状态
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['wmic', 'qfe', 'list', 'brief'],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    update_count = len(result.stdout.strip().split('\n')) - 1
                    if update_count == 0:
                        results.append(DiagnosticResult(
                            id="system_updates_missing",
                            category="security",
                            name="系统更新缺失",
                            severity=ProblemSeverity.HIGH,
                            description="系统可能缺少重要的安全更新",
                            timestamp=datetime.now(),
                            details={'update_count': update_count},
                            solution="检查并安装系统更新",
                            confidence=0.7
                        ))
            
        except Exception as e:
            logger.error(f"安全漏洞测试失败: {str(e)}")
        
        return results
    
    def _test_malware_signs(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试恶意软件迹象"""
        results = []
        
        try:
            # 检查可疑进程
            suspicious_processes = []
            for process in psutil.process_iter(['name', 'exe']):
                try:
                    process_info = process.info
                    process_name = process_info['name'].lower()
                    
                    # 检查已知的恶意软件名称模式
                    suspicious_patterns = ['miner', 'bitcoin', 'crypto', 'trojan', 'virus']
                    if any(pattern in process_name for pattern in suspicious_patterns):
                        suspicious_processes.append(process_info['name'])
                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if suspicious_processes:
                results.append(DiagnosticResult(
                    id="suspicious_processes",
                    category="security",
                    name="可疑进程检测",
                    severity=ProblemSeverity.CRITICAL,
                    description=f"发现 {len(suspicious_processes)} 个可疑进程",
                    timestamp=datetime.now(),
                    details={'suspicious_processes': suspicious_processes},
                    solution="立即运行防病毒软件扫描",
                    confidence=0.5
                ))
            
        except Exception as e:
            logger.error(f"恶意软件迹象测试失败: {str(e)}")
        
        return results
    
    def _test_privacy_issues(self, level: DiagnosticLevel) -> List[DiagnosticResult]:
        """测试隐私问题"""
        results = []
        
        try:
            # 检查遥测设置
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                       r"SOFTWARE\Policies\Microsoft\Windows\DataCollection")
                    allow_telemetry, _ = winreg.QueryValueEx(key, "AllowTelemetry")
                    winreg.CloseKey(key)
                    
                    if allow_telemetry > 0:
                        results.append(DiagnosticResult(
                            id="telemetry_enabled",
                            category="security",
                            name="数据收集已启用",
                            severity=ProblemSeverity.LOW,
                            description="系统遥测数据收集已启用",
                            timestamp=datetime.now(),
                            details={'telemetry_level': allow_telemetry},
                            solution="禁用不必要的遥测数据收集以保护隐私",
                            confidence=0.9
                        ))
                
                except FileNotFoundError:
                    # 注册表项不存在，使用默认设置
                    results.append(DiagnosticResult(
                        id="telemetry_default",
                        category="security",
                        name="数据收集使用默认设置",
                        severity=ProblemSeverity.LOW,
                        description="系统遥测数据收集使用默认设置",
                        timestamp=datetime.now(),
                        details={'telemetry_default': True},
                        recommendation="配置隐私设置以控制数据收集",
                        solution="明确配置遥测设置以控制数据收集",
                        confidence=0.7
                    ))
            
        except Exception as e:
            logger.error(f"隐私问题测试失败: {str(e)}")
        
        return results
    
    # 辅助方法
    
    def _check_system_errors(self) -> int:
        """检查系统错误数量"""
        # 简化实现
        return 0
    
    def _check_disk_health(self) -> Dict[str, Any]:
        """检查磁盘健康状态"""
        # 简化实现
        return {'healthy': True}
    
    def get_diagnosis_progress(self) -> Dict[str, Any]:
        """获取诊断进度"""
        return {
            'is_diagnosing': self.is_diagnosing,
            'progress': self.current_progress,
            'current_operation': self.current_operation
        }
    
    def get_recent_diagnosis(self) -> Optional[SystemDiagnosis]:
        """获取最近的诊断结果"""
        if self.diagnosis_history:
            return self.diagnosis_history[-1]
        return None
    
    def get_diagnosis_history(self, limit: int = 10) -> List[SystemDiagnosis]:
        """获取诊断历史"""
        return self.diagnosis_history[-limit:] if limit > 0 else self.diagnosis_history
    
    def cancel_diagnosis(self):
        """取消诊断"""
        self.is_diagnosing = False
        if self.diagnosis_thread and self.diagnosis_thread.is_alive():
            self.diagnosis_thread.join(timeout=5)
        
        logger.info("系统诊断已取消")
    
    def export_diagnosis_report(self, diagnosis_id: str, file_path: str) -> bool:
        """导出诊断报告"""
        try:
            diagnosis = next((d for d in self.diagnosis_history if d.diagnosis_id == diagnosis_id), None)
            if not diagnosis:
                return False
            
            report = diagnosis.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"诊断报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出诊断报告失败: {str(e)}")
            return False

# 单例实例
_diagnostic_tool_instance = None

def get_diagnostic_tool() -> DiagnosticTool:
    """获取诊断工具单例"""
    global _diagnostic_tool_instance
    if _diagnostic_tool_instance is None:
        _diagnostic_tool_instance = DiagnosticTool()
    return _diagnostic_tool_instance

