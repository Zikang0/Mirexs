"""
macOS平台适配器 - macOS特定功能适配
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class MacOSAdapter:
    """macOS平台特定功能适配器"""
    
    def __init__(self):
        self.platform = "darwin"
        self.version = platform.mac_ver()[0]  # macOS版本
        self.arch = platform.machine()
        self.initialized = False
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化macOS适配器"""
        self.hardware_info = hardware_info
        self.system_info = self._get_system_info()
        self.initialized = True
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取macOS系统详细信息"""
        info = {
            'version': self.version,
            'architecture': self.arch,
            'kernel': platform.release()
        }
        
        try:
            # 获取硬件型号
            model = self._get_hardware_model()
            if model:
                info['hardware_model'] = model
                
            # 获取芯片信息
            chip = self._get_chip_info()
            if chip:
                info['chip'] = chip
                
        except Exception as e:
            print(f"⚠️ 获取macOS系统信息失败: {e}")
            
        return info
    
    def _get_hardware_model(self) -> Optional[str]:
        """获取硬件型号"""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.model"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def _get_chip_info(self) -> Optional[str]:
        """获取芯片信息"""
        try:
            # 检查是Intel还是Apple Silicon
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
                
            # 如果是Apple Silicon
            if self.arch.startswith('arm'):
                return "Apple Silicon"
                
        except:
            pass
        return "Unknown"
    
    def execute_command(self, command: str, use_sudo: bool = False) -> tuple:
        """执行macOS命令"""
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
    
    def get_brew_info(self, package_name: str) -> Optional[Dict[str, str]]:
        """获取Homebrew包信息"""
        try:
            if not shutil.which("brew"):
                return None
                
            returncode, stdout, _ = self.execute_command(f"brew info {package_name}")
            if returncode == 0 and package_name in stdout:
                return {'name': package_name, 'manager': 'brew'}
        except Exception as e:
            print(f"⚠️ 获取brew包信息失败: {e}")
            
        return None
    
    def install_brew_package(self, package_name: str) -> bool:
        """安装Homebrew包"""
        try:
            if not shutil.which("brew"):
                print("❌ Homebrew未安装")
                return False
                
            returncode, _, _ = self.execute_command(f"brew install {package_name}")
            return returncode == 0
        except Exception as e:
            print(f"⚠️ 安装brew包失败: {e}")
            
        return False
    
    def get_macos_features(self) -> Dict[str, bool]:
        """获取macOS功能特性"""
        features = {
            'brew_available': shutil.which("brew") is not None,
            'xcode_available': shutil.which("xcodebuild") is not None,
            'metal_available': self._check_metal_available(),
            'core_ml_available': self._check_core_ml_available(),
            'touch_bar_available': self._check_touch_bar_available(),
            'secure_enclave_available': self._check_secure_enclave()
        }
        return features
    
    def _check_metal_available(self) -> bool:
        """检查Metal图形API是否可用"""
        try:
            # 检查是否有支持Metal的GPU
            returncode, stdout, _ = self.execute_command("system_profiler SPDisplaysDataType")
            return returncode == 0 and "Metal" in stdout
        except:
            return False
    
    def _check_core_ml_available(self) -> bool:
        """检查Core ML是否可用"""
        try:
            # Core ML在macOS 10.13+上可用
            major_version = int(self.version.split('.')[0])
            return major_version >= 10
        except:
            return False
    
    def _check_touch_bar_available(self) -> bool:
        """检查Touch Bar是否可用"""
        try:
            # 检查是否有Touch Bar硬件
            returncode, stdout, _ = self.execute_command(
                "system_profiler SPUSBDataType | grep -i 'touch bar'"
            )
            return returncode == 0
        except:
            return False
    
    def _check_secure_enclave(self) -> bool:
        """检查安全飞地是否可用"""
        try:
            # 检查T1/T2芯片或Apple Silicon
            if self.arch.startswith('arm'):
                return True  # Apple Silicon都有安全飞地
                
            returncode, stdout, _ = self.execute_command(
                "system_profiler SPiBridgeDataType"
            )
            return returncode == 0 and "T2" in stdout
        except:
            return False
    
    def get_special_directories(self) -> Dict[str, str]:
        """获取macOS特殊目录"""
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
                'movies': str(home / "Movies"),
                'applications': str(home / "Applications"),
                'library': str(home / "Library"),
                'application_support': str(home / "Library/Application Support")
            }
            
            for name, path in common_dirs.items():
                if os.path.exists(path):
                    directories[name] = path
                    
        except Exception as e:
            print(f"⚠️ 获取特殊目录失败: {e}")
            
        return directories
    
    def get_applications_folder(self) -> str:
        """获取应用程序文件夹路径"""
        paths = [
            "/Applications",
            str(Path.home() / "Applications")
        ]
        
        for path in paths:
            if os.path.exists(path):
                return path
                
        return "/Applications"