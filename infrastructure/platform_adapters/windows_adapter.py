"""
Windows平台适配器 - Windows特定功能适配
"""

import os
import sys
import ctypes
import platform
import winreg
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class WindowsAdapter:
    """Windows平台特定功能适配器"""
    
    def __init__(self):
        self.platform = "windows"
        self.version = platform.version()
        self.edition = platform.win32_edition()
        self.arch = platform.architecture()[0]
        self.initialized = False
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化Windows适配器"""
        self.hardware_info = hardware_info
        self.system_info = self._get_system_info()
        self.initialized = True
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取Windows系统详细信息"""
        try:
            # 获取Windows版本信息
            if hasattr(ctypes, 'windll'):
                kernel32 = ctypes.windll.kernel32
                
                # 获取系统目录
                system_dir = ctypes.create_unicode_buffer(260)
                kernel32.GetSystemDirectoryW(system_dir, 260)
                
                return {
                    'system_directory': system_dir.value,
                    'build_number': platform.release(),
                    'edition': self.edition,
                    'architecture': self.arch,
                    'version': self.version
                }
        except Exception as e:
            print(f"⚠️ 获取Windows系统信息失败: {e}")
            
        return {
            'build_number': platform.release(),
            'edition': self.edition,
            'architecture': self.arch,
            'version': self.version
        }
    
    def get_windows_version(self) -> str:
        """获取Windows版本信息"""
        return f"Windows {self.edition} {self.version} ({self.arch})"
    
    def is_administrator(self) -> bool:
        """检查是否具有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def registry_read(self, key_path: str, value_name: str) -> Optional[str]:
        """读取Windows注册表"""
        try:
            if "HKEY_LOCAL_MACHINE" in key_path:
                root = winreg.HKEY_LOCAL_MACHINE
                key_path = key_path.replace("HKEY_LOCAL_MACHINE\\", "")
            elif "HKEY_CURRENT_USER" in key_path:
                root = winreg.HKEY_CURRENT_USER
                key_path = key_path.replace("HKEY_CURRENT_USER\\", "")
            else:
                return None
                
            with winreg.OpenKey(root, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return value
        except Exception as e:
            print(f"⚠️ 读取注册表失败: {e}")
            return None
    
    def execute_powershell(self, command: str) -> tuple:
        """执行PowerShell命令"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, 
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令执行超时"
        except Exception as e:
            return -1, "", str(e)
    
    def get_special_folders(self) -> Dict[str, str]:
        """获取Windows特殊文件夹路径"""
        folders = {}
        try:
            # 常见特殊文件夹
            special_folders = {
                'desktop': os.path.join(os.path.expanduser("~"), "Desktop"),
                'documents': os.path.join(os.path.expanduser("~"), "Documents"),
                'downloads': os.path.join(os.path.expanduser("~"), "Downloads"),
                'appdata': os.getenv('APPDATA', ''),
                'localappdata': os.getenv('LOCALAPPDATA', ''),
                'temp': os.getenv('TEMP', ''),
                'program_files': os.getenv('ProgramFiles', ''),
                'program_files_x86': os.getenv('ProgramFiles(x86)', '')
            }
            
            for name, path in special_folders.items():
                if path and os.path.exists(path):
                    folders[name] = path
                    
        except Exception as e:
            print(f"⚠️ 获取特殊文件夹失败: {e}")
            
        return folders
    
    def set_process_priority(self, priority: str = "normal") -> bool:
        """设置进程优先级"""
        priority_map = {
            "low": 0x00000040,      # IDLE_PRIORITY_CLASS
            "normal": 0x00000020,   # NORMAL_PRIORITY_CLASS  
            "high": 0x00000080,     # HIGH_PRIORITY_CLASS
            "realtime": 0x00000100  # REALTIME_PRIORITY_CLASS
        }
        
        try:
            if priority in priority_map:
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetCurrentProcess()
                return kernel32.SetPriorityClass(handle, priority_map[priority])
            return False
        except Exception as e:
            print(f"⚠️ 设置进程优先级失败: {e}")
            return False
    
    def get_windows_features(self) -> Dict[str, Any]:
        """获取Windows功能特性"""
        features = {
            'wsl_available': self._check_wsl_available(),
            'hyperv_available': self._check_hyperv_available(),
            'windows_sandbox': self._check_sandbox_available(),
            'gpu_acceleration': self._check_gpu_acceleration()
        }
        return features
    
    def _check_wsl_available(self) -> bool:
        """检查WSL是否可用"""
        try:
            returncode, stdout, _ = self.execute_powershell("wsl --list --quiet")
            return returncode == 0
        except:
            return False
    
    def _check_hyperv_available(self) -> bool:
        """检查Hyper-V是否可用"""
        try:
            result = self.registry_read(
                "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", 
                "InstallationType"
            )
            return "Server" in str(result) if result else False
        except:
            return False
    
    def _check_sandbox_available(self) -> bool:
        """检查Windows沙盒是否可用"""
        try:
            result = self.registry_read(
                "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\WindowsOptionalFeatures",
                "WindowsSandbox"
            )
            return result is not None
        except:
            return False
    
    def _check_gpu_acceleration(self) -> bool:
        """检查GPU加速是否可用"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # 检查是否有支持DirectX的GPU
            d3d = ctypes.windll.d3d9
            return d3d.Direct3DCreate9(32) is not None
        except:
            return False