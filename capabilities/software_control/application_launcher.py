"""
应用启动器：负责启动和管理应用程序
"""
import os
import sys
import subprocess
import psutil
import win32gui
import win32con
import win32process
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ApplicationState(Enum):
    """应用程序状态枚举"""
    NOT_FOUND = "not_found"
    RUNNING = "running"
    STOPPED = "stopped"
    SUSPENDED = "suspended"

@dataclass
class ApplicationInfo:
    """应用程序信息"""
    name: str
    process_name: str
    executable_path: str
    window_title: str
    pid: Optional[int] = None
    state: ApplicationState = ApplicationState.STOPPED

class ApplicationLauncher:
    """应用启动器类"""
    
    def __init__(self):
        self.running_apps: Dict[str, ApplicationInfo] = {}
        self.application_registry: Dict[str, ApplicationInfo] = self._load_application_registry()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_application_registry(self) -> Dict[str, ApplicationInfo]:
        """加载应用程序注册表"""
        registry = {
            "notepad": ApplicationInfo(
                name="记事本",
                process_name="notepad.exe",
                executable_path="notepad.exe",
                window_title="记事本"
            ),
            "calculator": ApplicationInfo(
                name="计算器",
                process_name="Calculator.exe",
                executable_path="calc.exe",
                window_title="计算器"
            ),
            "chrome": ApplicationInfo(
                name="Chrome浏览器",
                process_name="chrome.exe",
                executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                window_title="Google Chrome"
            ),
            "wechat": ApplicationInfo(
                name="微信",
                process_name="WeChat.exe",
                executable_path="C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe",
                window_title="微信"
            )
        }
        return registry
    
    def launch_application(self, app_name: str, arguments: List[str] = None) -> Tuple[bool, str]:
        """启动应用程序"""
        try:
            if app_name not in self.application_registry:
                return False, f"应用程序 '{app_name}' 未在注册表中找到"
            
            app_info = self.application_registry[app_name]
            
            # 检查应用是否已在运行
            if self._is_application_running(app_info.process_name):
                return True, f"应用程序 '{app_name}' 已在运行中"
            
            # 构建启动命令
            cmd = [app_info.executable_path]
            if arguments:
                cmd.extend(arguments)
            
            # 启动应用程序
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True
            )
            
            # 等待进程启动
            import time
            time.sleep(2)
            
            # 更新应用信息
            app_info.pid = process.pid
            app_info.state = ApplicationState.RUNNING
            self.running_apps[app_name] = app_info
            
            logger.info(f"成功启动应用程序: {app_name}, PID: {process.pid}")
            return True, f"应用程序 '{app_name}' 启动成功"
            
        except Exception as e:
            logger.error(f"启动应用程序 '{app_name}' 时发生错误: {str(e)}")
            return False, f"启动失败: {str(e)}"
    
    def close_application(self, app_name: str, force: bool = False) -> Tuple[bool, str]:
        """关闭应用程序"""
        try:
            if app_name not in self.running_apps:
                return False, f"应用程序 '{app_name}' 未在运行"
            
            app_info = self.running_apps[app_name]
            
            if not app_info.pid:
                return False, f"应用程序 '{app_name}' 的PID未找到"
            
            # 查找进程
            try:
                process = psutil.Process(app_info.pid)
                
                if force:
                    process.kill()
                    message = f"强制终止应用程序 '{app_name}'"
                else:
                    process.terminate()
                    message = f"正常关闭应用程序 '{app_name}'"
                
                # 等待进程结束
                process.wait(timeout=10)
                
                # 从运行列表中移除
                del self.running_apps[app_name]
                app_info.state = ApplicationState.STOPPED
                app_info.pid = None
                
                logger.info(message)
                return True, message
                
            except psutil.NoSuchProcess:
                del self.running_apps[app_name]
                return False, f"应用程序 '{app_name}' 的进程不存在"
                
        except Exception as e:
            logger.error(f"关闭应用程序 '{app_name}' 时发生错误: {str(e)}")
            return False, f"关闭失败: {str(e)}"
    
    def _is_application_running(self, process_name: str) -> bool:
        """检查应用程序是否在运行"""
        for process in psutil.process_iter(['name']):
            if process.info['name'].lower() == process_name.lower():
                return True
        return False
    
    def get_running_applications(self) -> List[ApplicationInfo]:
        """获取正在运行的应用程序列表"""
        running_apps = []
        for app_name, app_info in self.running_apps.items():
            if app_info.pid and self._is_process_running(app_info.pid):
                running_apps.append(app_info)
            else:
                # 清理已停止的应用
                del self.running_apps[app_name]
        
        return running_apps
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
    
    def register_application(self, app_info: ApplicationInfo) -> bool:
        """注册新的应用程序"""
        try:
            self.application_registry[app_info.name.lower()] = app_info
            logger.info(f"成功注册应用程序: {app_info.name}")
            return True
        except Exception as e:
            logger.error(f"注册应用程序失败: {str(e)}")
            return False
    
    def bring_to_front(self, app_name: str) -> bool:
        """将应用程序窗口置前"""
        try:
            if app_name not in self.running_apps:
                return False
            
            app_info = self.running_apps[app_name]
            
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd) and app_info.window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                return True
            
            win32gui.EnumWindows(callback, None)
            return True
            
        except Exception as e:
            logger.error(f"置前应用程序窗口失败: {str(e)}")
            return False

# 单例实例
_application_launcher_instance = None

def get_application_launcher() -> ApplicationLauncher:
    """获取应用启动器单例"""
    global _application_launcher_instance
    if _application_launcher_instance is None:
        _application_launcher_instance = ApplicationLauncher()
    return _application_launcher_instance

