"""
文件系统适配器 - 跨平台文件操作
"""

import os
import sys
import platform
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

class FileSystemAdapter:
    """跨平台文件系统操作适配器"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.path_separator = os.path.sep
        self.temp_dir = tempfile.gettempdir()
        self.initialized = False
        
    def initialize(self, hardware_info: Dict[str, Any]):
        """初始化文件系统适配器"""
        self.hardware_info = hardware_info
        self.file_system_info = self._get_file_system_info()
        self.initialized = True
        
    def _get_file_system_info(self) -> Dict[str, Any]:
        """获取文件系统信息"""
        info = {
            'platform': self.platform,
            'path_separator': self.path_separator,
            'temp_directory': self.temp_dir,
            'home_directory': str(Path.home()),
            'current_working_directory': os.getcwd()
        }
        
        try:
            # 获取磁盘使用情况
            info['disk_usage'] = self.get_disk_usage()
            
            # 获取路径风格
            info['path_style'] = self._get_path_style()
            
        except Exception as e:
            print(f"⚠️ 获取文件系统信息失败: {e}")
            
        return info
    
    def _get_path_style(self) -> str:
        """获取路径风格"""
        if self.platform == "windows":
            return "windows"
        else:
            return "posix"
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """获取磁盘使用情况"""
        try:
            if self.platform == "windows":
                # Windows下使用特定路径
                if path == "/":
                    path = "C:"
                    
            usage = shutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent_used': (usage.used / usage.total) * 100
            }
        except Exception as e:
            print(f"⚠️ 获取磁盘使用情况失败: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percent_used': 0}
    
    def normalize_path(self, path: str) -> str:
        """标准化路径"""
        if self.platform == "windows":
            # Windows下统一使用正斜杠
            path = path.replace('/', '\\')
            # 确保是绝对路径
            if not os.path.isabs(path):
                path = os.path.abspath(path)
        else:
            # Unix-like系统
            path = os.path.expanduser(path)
            if not os.path.isabs(path):
                path = os.path.abspath(path)
                
        return path
    
    def join_path(self, *paths: str) -> str:
        """连接路径"""
        return os.path.join(*paths)
    
    def path_exists(self, path: str) -> bool:
        """检查路径是否存在"""
        return os.path.exists(path)
    
    def is_file(self, path: str) -> bool:
        """检查是否为文件"""
        return os.path.isfile(path)
    
    def is_directory(self, path: str) -> bool:
        """检查是否为目录"""
        return os.path.isdir(path)
    
    def create_directory(self, path: str, parents: bool = True) -> bool:
        """创建目录"""
        try:
            if parents:
                os.makedirs(path, exist_ok=True)
            else:
                os.mkdir(path)
            return True
        except Exception as e:
            print(f"❌ 创建目录失败: {e}")
            return False
    
    def list_directory(self, path: str, show_hidden: bool = False) -> List[str]:
        """列出目录内容"""
        try:
            items = os.listdir(path)
            if not show_hidden:
                items = [item for item in items if not item.startswith('.')]
            return items
        except Exception as e:
            print(f"❌ 列出目录失败: {e}")
            return []
    
    def read_file(self, path: str, mode: str = "r") -> Optional[Union[str, bytes]]:
        """读取文件"""
        try:
            with open(path, mode, encoding='utf-8' if 'b' not in mode else None) as f:
                return f.read()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return None
    
    def write_file(self, path: str, content: Union[str, bytes], mode: str = "w") -> bool:
        """写入文件"""
        try:
            with open(path, mode, encoding='utf-8' if 'b' not in mode else None) as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False
    
    def copy_file(self, source: str, destination: str) -> bool:
        """复制文件"""
        try:
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            print(f"❌ 复制文件失败: {e}")
            return False
    
    def move_file(self, source: str, destination: str) -> bool:
        """移动文件"""
        try:
            shutil.move(source, destination)
            return True
        except Exception as e:
            print(f"❌ 移动文件失败: {e}")
            return False
    
    def delete_file(self, path: str) -> bool:
        """删除文件"""
        try:
            os.remove(path)
            return True
        except Exception as e:
            print(f"❌ 删除文件失败: {e}")
            return False
    
    def delete_directory(self, path: str, recursive: bool = False) -> bool:
        """删除目录"""
        try:
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
            return True
        except Exception as e:
            print(f"❌ 删除目录失败: {e}")
            return False
    
    def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        try:
            stat_info = os.stat(path)
            return {
                'size': stat_info.st_size,
                'created_time': stat_info.st_ctime,
                'modified_time': stat_info.st_mtime,
                'accessed_time': stat_info.st_atime,
                'is_directory': os.path.isdir(path),
                'permissions': stat.S_IMODE(stat_info.st_mode)
            }
        except Exception as e:
            print(f"❌ 获取文件信息失败: {e}")
            return None
    
    def set_permissions(self, path: str, permissions: int) -> bool:
        """设置文件权限"""
        try:
            os.chmod(path, permissions)
            return True
        except Exception as e:
            print(f"❌ 设置权限失败: {e}")
            return False
    
    def create_temp_file(self, suffix: str = "", prefix: str = "mirexs_") -> Optional[str]:
        """创建临时文件"""
        try:
            handle, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(handle)
            return path
        except Exception as e:
            print(f"❌ 创建临时文件失败: {e}")
            return None
    
    def create_temp_directory(self, suffix: str = "", prefix: str = "mirexs_") -> Optional[str]:
        """创建临时目录"""
        try:
            return tempfile.mkdtemp(suffix=suffix, prefix=prefix)
        except Exception as e:
            print(f"❌ 创建临时目录失败: {e}")
            return None
    
    def get_file_size(self, path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(path)
        except:
            return 0
    
    def walk_directory(self, path: str) -> List[tuple]:
        """遍历目录树"""
        try:
            result = []
            for root, dirs, files in os.walk(path):
                result.append((root, dirs, files))
            return result
        except Exception as e:
            print(f"❌ 遍历目录失败: {e}")
            return []
    
    def get_platform_specific_paths(self) -> Dict[str, str]:
        """获取平台特定的路径"""
        paths = {}
        
        if self.platform == "windows":
            paths.update({
                'program_files': os.getenv('ProgramFiles', ''),
                'program_files_x86': os.getenv('ProgramFiles(x86)', ''),
                'appdata': os.getenv('APPDATA', ''),
                'localappdata': os.getenv('LOCALAPPDATA', ''),
                'temp': os.getenv('TEMP', ''),
                'system_root': os.getenv('SystemRoot', '')
            })
        elif self.platform == "darwin":  # macOS
            home = Path.home()
            paths.update({
                'applications': str(home / "Applications"),
                'library': str(home / "Library"),
                'application_support': str(home / "Library/Application Support"),
                'preferences': str(home / "Library/Preferences"),
                'caches': str(home / "Library/Caches")
            })
        else:  # Linux and other Unix-like
            home = Path.home()
            paths.update({
                'config': str(home / ".config"),
                'local_share': str(home / ".local/share"),
                'cache': str(home / ".cache"),
                'desktop': str(home / "Desktop"),
                'documents': str(home / "Documents")
            })
            
        return paths