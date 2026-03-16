"""
Linux平台适配器 - Linux特定功能适配
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class LinuxAdapter:
    """Linux平台特定功能适配器"""
    
    def __init__(self):
        self.platform = "linux"
        self.distribution = self._get_distribution()
        self.version = platform.version()
        self.arch = platform.machine()
        self.initialized = False
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化Linux适配器"""
        self.hardware_info = hardware_info
        self.system_info = self._get_system_info()
        self.initialized = True
        
    def _get_distribution(self) -> str:
        """获取Linux发行版信息"""
        try:
            # 尝试读取/etc/os-release
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("ID="):
                            return line.split("=")[1].strip().strip('"')
            
            # 回退到platform模块
            dist = platform.freedesktop_os_release().get('ID', 'unknown')
            return dist
        except:
            return "unknown"
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取Linux系统详细信息"""
        info = {
            'distribution': self.distribution,
            'version': self.version,
            'architecture': self.arch,
            'kernel': platform.release()
        }
        
        try:
            # 获取桌面环境信息
            desktop = os.getenv('XDG_CURRENT_DESKTOP', '')
            if desktop:
                info['desktop_environment'] = desktop
                
            # 获取包管理器信息
            info['package_manager'] = self._detect_package_manager()
            
        except Exception as e:
            print(f"⚠️ 获取Linux系统信息失败: {e}")
            
        return info
    
    def _detect_package_manager(self) -> str:
        """检测包管理器"""
        package_managers = {
            'apt': ['apt', 'apt-get'],      # Debian/Ubuntu
            'yum': ['yum', 'dnf'],          # RHEL/CentOS/Fedora
            'pacman': ['pacman'],           # Arch Linux
            'zypper': ['zypper'],           # openSUSE
            'emerge': ['emerge'],           # Gentoo
            'apk': ['apk']                  # Alpine
        }
        
        for pm_name, commands in package_managers.items():
            for cmd in commands:
                if shutil.which(cmd):
                    return pm_name
                    
        return "unknown"
    
    def execute_shell(self, command: str, use_sudo: bool = False) -> tuple:
        """执行Shell命令"""
        try:
            if use_sudo and os.geteuid() != 0:
                command = f"sudo {command}"
                
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令执行超时"
        except Exception as e:
            return -1, "", str(e)
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, str]]:
        """获取软件包信息"""
        try:
            if self.system_info.get('package_manager') == 'apt':
                returncode, stdout, _ = self.execute_shell(f"dpkg -l {package_name}")
                if returncode == 0 and package_name in stdout:
                    return {'name': package_name, 'manager': 'apt'}
                    
            elif self.system_info.get('package_manager') == 'yum':
                returncode, stdout, _ = self.execute_shell(f"rpm -q {package_name}")
                if returncode == 0:
                    return {'name': package_name, 'manager': 'yum'}
                    
            elif self.system_info.get('package_manager') == 'pacman':
                returncode, stdout, _ = self.execute_shell(f"pacman -Qi {package_name}")
                if returncode == 0:
                    return {'name': package_name, 'manager': 'pacman'}
                    
        except Exception as e:
            print(f"⚠️ 获取包信息失败: {e}")
            
        return None
    
    def install_package(self, package_name: str) -> bool:
        """安装软件包"""
        try:
            pm = self.system_info.get('package_manager')
            install_commands = {
                'apt': f"apt install -y {package_name}",
                'yum': f"yum install -y {package_name}", 
                'dnf': f"dnf install -y {package_name}",
                'pacman': f"pacman -S --noconfirm {package_name}",
                'zypper': f"zypper install -y {package_name}",
                'apk': f"apk add {package_name}"
            }
            
            if pm in install_commands:
                returncode, _, _ = self.execute_shell(install_commands[pm], use_sudo=True)
                return returncode == 0
                
        except Exception as e:
            print(f"⚠️ 安装包失败: {e}")
            
        return False
    
    def get_systemd_services(self) -> list:
        """获取systemd服务列表"""
        try:
            returncode, stdout, _ = self.execute_shell("systemctl list-units --type=service --no-legend")
            if returncode == 0:
                services = []
                for line in stdout.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            services.append(parts[0])
                return services
        except Exception as e:
            print(f"⚠️ 获取systemd服务失败: {e}")
            
        return []
    
    def check_service_status(self, service_name: str) -> Optional[str]:
        """检查服务状态"""
        try:
            returncode, stdout, _ = self.execute_shell(f"systemctl is-active {service_name}")
            if returncode == 0:
                return stdout.strip()
        except Exception as e:
            print(f"⚠️ 检查服务状态失败: {e}")
            
        return None
    
    def get_linux_features(self) -> Dict[str, bool]:
        """获取Linux功能特性"""
        features = {
            'systemd_available': shutil.which("systemctl") is not None,
            'docker_available': shutil.which("docker") is not None,
            'nvidia_available': self._check_nvidia_available(),
            'wayland_available': 'WAYLAND_DISPLAY' in os.environ,
            'flatpak_available': shutil.which("flatpak") is not None,
            'snap_available': shutil.which("snap") is not None
        }
        return features
    
    def _check_nvidia_available(self) -> bool:
        """检查NVIDIA GPU是否可用"""
        try:
            returncode, stdout, _ = self.execute_shell("lspci | grep -i nvidia")
            return returncode == 0 and "NVIDIA" in stdout
        except:
            return False
    
    def get_special_directories(self) -> Dict[str, str]:
        """获取Linux特殊目录"""
        directories = {}
        try:
            home = Path.home()
            common_dirs = {
                'home': str(home),
                'desktop': str(home / "Desktop"),
                'documents': str(home / "Documents"),
                'downloads': str(home / "Downloads"),
                'pictures': str(home / "Pictures"),
                'music': str(home / "Music"),
                'videos': str(home / "Videos"),
                'config': str(home / ".config"),
                'local_share': str(home / ".local/share"),
                'cache': str(home / ".cache")
            }
            
            for name, path in common_dirs.items():
                if os.path.exists(path):
                    directories[name] = path
                    
        except Exception as e:
            print(f"⚠️ 获取特殊目录失败: {e}")
            
        return directories