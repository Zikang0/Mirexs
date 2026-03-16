"""
硬件检测器 - 自动检测硬件配置
"""

import os
import sys
import platform
import subprocess
from typing import Dict, Any, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import GPUtil
    GPUINFO_AVAILABLE = True
except ImportError:
    GPUINFO_AVAILABLE = False

class HardwareDetector:
    """硬件检测器 - 自动检测系统硬件配置"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.detection_methods = self._get_detection_methods()
        
    def _get_detection_methods(self) -> List[str]:
        """获取可用的检测方法"""
        methods = ['platform']
        
        if PSUTIL_AVAILABLE:
            methods.append('psutil')
            
        if GPUINFO_AVAILABLE:
            methods.append('gpuinfo')
            
        # 平台特定方法
        if self.platform == "windows":
            methods.extend(['wmi', 'powershell'])
        elif self.platform == "linux":
            methods.extend(['proc', 'lspci', 'lscpu'])
        elif self.platform == "darwin":  # macOS
            methods.extend(['system_profiler', 'ioreg'])
            
        return methods
    
    def detect_all(self) -> Dict[str, Any]:
        """检测所有硬件信息"""
        hardware_info = {
            'system': self.detect_system(),
            'cpu': self.detect_cpu(),
            'memory': self.detect_memory(),
            'gpu': self.detect_gpu(),
            'storage': self.detect_storage(),
            'network': self.detect_network(),
            'sensors': self.detect_sensors(),
            'detection_methods': self.detection_methods
        }
        return hardware_info
    
    def detect_system(self) -> Dict[str, Any]:
        """检测系统信息"""
        system_info = {
            'platform': self.platform,
            'platform_version': platform.version(),
            'platform_release': platform.release(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node()
        }
        
        # 添加更多详细信息
        if self.platform == "windows":
            system_info.update(self._detect_windows_system())
        elif self.platform == "linux":
            system_info.update(self._detect_linux_system())
        elif self.platform == "darwin":
            system_info.update(self._detect_macos_system())
            
        return system_info
    
    def _detect_windows_system(self) -> Dict[str, Any]:
        """检测Windows系统详细信息"""
        info = {}
        try:
            # 使用platform模块获取Windows版本
            info['windows_edition'] = platform.win32_edition()
            info['windows_version'] = platform.win32_ver()
            
            # 尝试使用WMI获取更多信息
            try:
                import wmi
                c = wmi.WMI()
                
                # 获取计算机系统信息
                for computer_system in c.Win32_ComputerSystem():
                    info['manufacturer'] = computer_system.Manufacturer
                    info['model'] = computer_system.Model
                    break
                    
                # 获取操作系统信息
                for os_info in c.Win32_OperatingSystem():
                    info['os_name'] = os_info.Caption
                    info['os_version'] = os_info.Version
                    info['build_number'] = os_info.BuildNumber
                    break
                    
            except ImportError:
                # WMI不可用，使用其他方法
                pass
                
        except Exception as e:
            print(f"⚠️ 检测Windows系统信息失败: {e}")
            
        return info
    
    def _detect_linux_system(self) -> Dict[str, Any]:
        """检测Linux系统详细信息"""
        info = {}
        try:
            # 读取/etc/os-release文件
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("NAME="):
                            info['distribution'] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("VERSION_ID="):
                            info['version_id'] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("PRETTY_NAME="):
                            info['pretty_name'] = line.split("=")[1].strip().strip('"')
            
            # 获取内核信息
            info['kernel'] = platform.release()
            
            # 尝试使用lsb_release命令
            try:
                result = subprocess.run(
                    ["lsb_release", "-a"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if "Description:" in line:
                            info['lsb_description'] = line.split(":")[1].strip()
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ 检测Linux系统信息失败: {e}")
            
        return info
    
    def _detect_macos_system(self) -> Dict[str, Any]:
        """检测macOS系统详细信息"""
        info = {}
        try:
            # 使用system_profiler获取macOS信息
            result = subprocess.run(
                ["system_profiler", "SPSoftwareDataType"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if "System Version:" in line:
                        info['system_version'] = line.split(":")[1].strip()
                    elif "Kernel Version:" in line:
                        info['kernel_version'] = line.split(":")[1].strip()
                    elif "Boot Volume:" in line:
                        info['boot_volume'] = line.split(":")[1].strip()
            
            # 获取硬件型号
            result = subprocess.run(
                ["sysctl", "-n", "hw.model"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info['hardware_model'] = result.stdout.strip()
                
        except Exception as e:
            print(f"⚠️ 检测macOS系统信息失败: {e}")
            
        return info
    
    def detect_cpu(self) -> Dict[str, Any]:
        """检测CPU信息"""
        cpu_info = {
            'name': platform.processor(),
            'architecture': platform.machine(),
            'cores_physical': 1,
            'cores_logical': 1,
            'frequency_max': 0
        }
        
        if PSUTIL_AVAILABLE:
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    cpu_info['frequency_current'] = cpu_freq.current
                    cpu_info['frequency_max'] = cpu_freq.max
                    
                cpu_info['cores_physical'] = psutil.cpu_count(logical=False)
                cpu_info['cores_logical'] = psutil.cpu_count(logical=True)
                
            except Exception as e:
                print(f"⚠️ 使用psutil检测CPU失败: {e}")
        
        # 平台特定的CPU检测
        if self.platform == "linux":
            cpu_info.update(self._detect_linux_cpu())
        elif self.platform == "windows":
            cpu_info.update(self._detect_windows_cpu())
        elif self.platform == "darwin":
            cpu_info.update(self._detect_macos_cpu())
            
        return cpu_info
    
    def _detect_linux_cpu(self) -> Dict[str, Any]:
        """Linux下检测CPU详细信息"""
        info = {}
        try:
            # 读取/proc/cpuinfo
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r") as f:
                    content = f.read()
                    
                # 解析CPU信息
                for line in content.split('\n'):
                    if "model name" in line:
                        info['name'] = line.split(":")[1].strip()
                        break
                    elif "cpu MHz" in line:
                        info['frequency_current'] = float(line.split(":")[1].strip())
                    elif "cache size" in line:
                        info['cache_size'] = line.split(":")[1].strip()
                        
        except Exception as e:
            print(f"⚠️ 检测Linux CPU信息失败: {e}")
            
        return info
    
    def _detect_windows_cpu(self) -> Dict[str, Any]:
        """Windows下检测CPU详细信息"""
        info = {}
        try:
            import wmi
            c = wmi.WMI()
            
            for processor in c.Win32_Processor():
                info['name'] = processor.Name
                info['manufacturer'] = processor.Manufacturer
                info['cores'] = processor.NumberOfCores
                info['threads'] = processor.NumberOfLogicalProcessors
                info['frequency'] = processor.MaxClockSpeed
                break
                
        except ImportError:
            # WMI不可用
            pass
        except Exception as e:
            print(f"⚠️ 检测Windows CPU信息失败: {e}")
            
        return info
    
    def _detect_macos_cpu(self) -> Dict[str, Any]:
        """macOS下检测CPU详细信息"""
        info = {}
        try:
            # 使用sysctl获取CPU信息
            commands = {
                'name': "sysctl -n machdep.cpu.brand_string",
                'cores_physical': "sysctl -n hw.physicalcpu", 
                'cores_logical': "sysctl -n hw.logicalcpu",
                'frequency': "sysctl -n hw.cpufrequency_max"
            }
            
            for key, cmd in commands.items():
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    info[key] = result.stdout.strip()
                    
        except Exception as e:
            print(f"⚠️ 检测macOS CPU信息失败: {e}")
            
        return info
    
    def detect_memory(self) -> Dict[str, Any]:
        """检测内存信息"""
        memory_info = {
            'total': 0,
            'available': 0,
            'used': 0,
            'percent': 0
        }
        
        if PSUTIL_AVAILABLE:
            try:
                virtual_memory = psutil.virtual_memory()
                memory_info.update({
                    'total': virtual_memory.total,
                    'available': virtual_memory.available,
                    'used': virtual_memory.used,
                    'percent': virtual_memory.percent
                })
                
                # 检测交换内存
                swap_memory = psutil.swap_memory()
                memory_info['swap'] = {
                    'total': swap_memory.total,
                    'used': swap_memory.used,
                    'free': swap_memory.free,
                    'percent': swap_memory.percent
                }
                
            except Exception as e:
                print(f"⚠️ 使用psutil检测内存失败: {e}")
        
        return memory_info
    
    def detect_gpu(self) -> Dict[str, Any]:
        """检测GPU信息"""
        gpu_info = {
            'name': 'Unknown',
            'vendor': 'Unknown', 
            'memory_total': 0,
            'driver_version': 'Unknown',
            'count': 0
        }
        
        if GPUINFO_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_info['count'] = len(gpus)
                    
                    # 获取第一个GPU的详细信息
                    first_gpu = gpus[0]
                    gpu_info.update({
                        'name': first_gpu.name,
                        'vendor': self._detect_gpu_vendor(first_gpu.name),
                        'memory_total': first_gpu.memoryTotal,
                        'driver_version': getattr(first_gpu, 'driver', 'Unknown')
                    })
                    
                    # 如果有多个GPU，收集所有信息
                    if len(gpus) > 1:
                        gpu_info['all_gpus'] = []
                        for gpu in gpus:
                            gpu_info['all_gpus'].append({
                                'name': gpu.name,
                                'memory_total': gpu.memoryTotal,
                                'memory_used': gpu.memoryUsed
                            })
                            
            except Exception as e:
                print(f"⚠️ 使用GPUtil检测GPU失败: {e}")
        
        # 平台特定的GPU检测
        if self.platform == "windows":
            gpu_info.update(self._detect_windows_gpu())
        elif self.platform == "linux":
            gpu_info.update(self._detect_linux_gpu())
        elif self.platform == "darwin":
            gpu_info.update(self._detect_macos_gpu())
            
        return gpu_info
    
    def _detect_gpu_vendor(self, gpu_name: str) -> str:
        """检测GPU厂商"""
        gpu_name_lower = gpu_name.lower()
        
        if 'nvidia' in gpu_name_lower:
            return 'NVIDIA'
        elif 'amd' in gpu_name_lower or 'radeon' in gpu_name_lower:
            return 'AMD'
        elif 'intel' in gpu_name_lower:
            return 'Intel'
        elif 'apple' in gpu_name_lower:
            return 'Apple'
        else:
            return 'Unknown'
    
    def _detect_windows_gpu(self) -> Dict[str, Any]:
        """Windows下检测GPU信息"""
        info = {}
        try:
            import wmi
            c = wmi.WMI()
            
            gpus = []
            for gpu in c.Win32_VideoController():
                gpu_data = {
                    'name': gpu.Name,
                    'driver_version': gpu.DriverVersion,
                    'memory': getattr(gpu, 'AdapterRAM', 0)
                }
                gpus.append(gpu_data)
                
            if gpus:
                info['gpus'] = gpus
                info['count'] = len(gpus)
                
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ 检测Windows GPU信息失败: {e}")
            
        return info
    
    def _detect_linux_gpu(self) -> Dict[str, Any]:
        """Linux下检测GPU信息"""
        info = {}
        try:
            # 使用lspci命令检测GPU
            result = subprocess.run(
                ["lspci", "-v"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                gpus = []
                current_gpu = {}
                
                for line in result.stdout.split('\n'):
                    if "VGA compatible controller" in line or "3D controller" in line:
                        if current_gpu:
                            gpus.append(current_gpu)
                        current_gpu = {'description': line.strip()}
                    elif "Kernel driver in use:" in line and current_gpu:
                        current_gpu['driver'] = line.split(":")[1].strip()
                    elif "Memory at" in line and current_gpu:
                        # 提取内存信息
                        pass
                        
                if current_gpu:
                    gpus.append(current_gpu)
                    
                if gpus:
                    info['gpus'] = gpus
                    info['count'] = len(gpus)
                    
        except Exception as e:
            print(f"⚠️ 检测Linux GPU信息失败: {e}")
            
        return info
    
    def _detect_macos_gpu(self) -> Dict[str, Any]:
        """macOS下检测GPU信息"""
        info = {}
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                gpus = []
                current_gpu = {}
                
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if "Chipset Model:" in line:
                        if current_gpu:
                            gpus.append(current_gpu)
                        current_gpu = {'name': line.split(":")[1].strip()}
                    elif "VRAM" in line and current_gpu:
                        current_gpu['memory'] = line.split(":")[1].strip()
                    elif "Metal:" in line and current_gpu:
                        current_gpu['metal_support'] = line.split(":")[1].strip()
                        
                if current_gpu:
                    gpus.append(current_gpu)
                    
                if gpus:
                    info['gpus'] = gpus
                    info['count'] = len(gpus)
                    
        except Exception as e:
            print(f"⚠️ 检测macOS GPU信息失败: {e}")
            
        return info
    
    def detect_storage(self) -> Dict[str, Any]:
        """检测存储设备信息"""
        storage_info = {
            'disks': [],
            'total_space': 0,
            'used_space': 0,
            'free_space': 0
        }
        
        if PSUTIL_AVAILABLE:
            try:
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_info = {
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        }
                        storage_info['disks'].append(disk_info)
                        
                        storage_info['total_space'] += usage.total
                        storage_info['used_space'] += usage.used
                        storage_info['free_space'] += usage.free
                        
                    except PermissionError:
                        # 跳过无权限访问的分区
                        continue
                        
            except Exception as e:
                print(f"⚠️ 使用psutil检测存储失败: {e}")
        
        return storage_info
    
    def detect_network(self) -> Dict[str, Any]:
        """检测网络信息"""
        network_info = {
            'interfaces': [],
            'hostname': platform.node()
        }
        
        if PSUTIL_AVAILABLE:
            try:
                interfaces = psutil.net_if_addrs()
                stats = psutil.net_if_stats()
                
                for interface_name, addresses in interfaces.items():
                    interface_info = {
                        'name': interface_name,
                        'addresses': [],
                        'is_up': False
                    }
                    
                    # 获取接口状态
                    if interface_name in stats:
                        interface_info['is_up'] = stats[interface_name].isup
                        interface_info['speed'] = stats[interface_name].speed
                        interface_info['mtu'] = stats[interface_name].mtu
                    
                    # 获取地址信息
                    for address in addresses:
                        addr_info = {
                            'family': str(address.family),
                            'address': address.address,
                            'netmask': address.netmask,
                            'broadcast': address.broadcast
                        }
                        interface_info['addresses'].append(addr_info)
                    
                    network_info['interfaces'].append(interface_info)
                    
            except Exception as e:
                print(f"⚠️ 使用psutil检测网络失败: {e}")
        
        return network_info
    
    def detect_sensors(self) -> Dict[str, Any]:
        """检测传感器信息"""
        sensors_info = {
            'temperatures': {},
            'fans': {},
            'battery': None
        }
        
        if PSUTIL_AVAILABLE:
            try:
                # 检测温度传感器
                if hasattr(psutil, 'sensors_temperatures'):
                    temps = psutil.sensors_temperatures()
                    if temps:
                        sensors_info['temperatures'] = temps
                
                # 检测风扇
                if hasattr(psutil, 'sensors_fans'):
                    fans = psutil.sensors_fans()
                    if fans:
                        sensors_info['fans'] = fans
                
                # 检测电池
                if hasattr(psutil, 'sensors_battery'):
                    battery = psutil.sensors_battery()
                    if battery:
                        sensors_info['battery'] = {
                            'percent': battery.percent,
                            'secsleft': battery.secsleft,
                            'power_plugged': battery.power_plugged
                        }
                        
            except Exception as e:
                print(f"⚠️ 使用psutil检测传感器失败: {e}")
        
        return sensors_info
    
    def get_hardware_summary(self) -> Dict[str, Any]:
        """获取硬件摘要信息"""
        hardware_info = self.detect_all()
        
        summary = {
            'system': f"{hardware_info['system'].get('pretty_name', hardware_info['system']['platform'])}",
            'cpu': f"{hardware_info['cpu']['name']} ({hardware_info['cpu']['cores_physical']}核心/{hardware_info['cpu']['cores_logical']}线程)",
            'memory': f"{hardware_info['memory']['total'] // (1024**3)} GB",
            'gpu': f"{hardware_info['gpu']['name']}",
            'storage': f"{hardware_info['storage']['total_space'] // (1024**3)} GB 总空间"
        }
        
        return summary