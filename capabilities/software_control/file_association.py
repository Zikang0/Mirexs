"""
文件关联：管理文件与程序关联
"""
import os
import winreg
import platform
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class FileAssociation:
    """文件关联信息"""
    extension: str
    description: str
    program_path: str
    program_name: str
    icon_path: Optional[str] = None
    mime_type: Optional[str] = None

class FileAssociationManager:
    """文件关联管理器"""
    
    def __init__(self):
        self.system_platform = platform.system()
        self.associations: Dict[str, FileAssociation] = {}
        self._setup_logging()
        self._load_associations()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_associations(self):
        """加载文件关联配置"""
        # 预定义一些常见的文件关联
        default_associations = {
            '.txt': FileAssociation(
                extension='.txt',
                description='文本文档',
                program_path='notepad.exe',
                program_name='记事本'
            ),
            '.pdf': FileAssociation(
                extension='.pdf',
                description='PDF文档',
                program_path='C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat\\Acrobat.exe',
                program_name='Adobe Acrobat'
            ),
            '.docx': FileAssociation(
                extension='.docx',
                description='Word文档',
                program_path='C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE',
                program_name='Microsoft Word'
            ),
            '.xlsx': FileAssociation(
                extension='.xlsx',
                description='Excel文档',
                program_path='C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE',
                program_name='Microsoft Excel'
            )
        }
        
        self.associations.update(default_associations)
    
    def register_association(self, association: FileAssociation) -> bool:
        """注册文件关联"""
        try:
            if self.system_platform == "Windows":
                return self._register_windows_association(association)
            else:
                logger.warning(f"不支持的操作系统: {self.system_platform}")
                return False
        except Exception as e:
            logger.error(f"注册文件关联失败: {str(e)}")
            return False
    
    def _register_windows_association(self, association: FileAssociation) -> bool:
        """在Windows上注册文件关联"""
        try:
            # 创建文件扩展名的注册表项
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{association.extension}") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, association.description)
            
            # 创建文件类型的注册表项
            prog_id = f"{association.program_name}{association.extension}"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{prog_id}") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, association.description)
                
                # 设置默认图标
                if association.icon_path:
                    with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                        winreg.SetValue(icon_key, "", winreg.REG_SZ, association.icon_path)
                
                # 设置打开命令
                with winreg.CreateKey(key, "shell\\open\\command") as command_key:
                    command = f'"{association.program_path}" "%1"'
                    winreg.SetValue(command_key, "", winreg.REG_SZ, command)
            
            # 将扩展名关联到程序ID
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{association.extension}") as key:
                winreg.SetValue(key, "", winreg.REG_SZ, prog_id)
            
            self.associations[association.extension] = association
            logger.info(f"成功注册文件关联: {association.extension} -> {association.program_name}")
            return True
            
        except Exception as e:
            logger.error(f"Windows文件关联注册失败: {str(e)}")
            return False
    
    def unregister_association(self, extension: str) -> bool:
        """取消文件关联"""
        try:
            if self.system_platform == "Windows":
                return self._unregister_windows_association(extension)
            else:
                logger.warning(f"不支持的操作系统: {self.system_platform}")
                return False
        except Exception as e:
            logger.error(f"取消文件关联失败: {str(e)}")
            return False
    
    def _unregister_windows_association(self, extension: str) -> bool:
        """在Windows上取消文件关联"""
        try:
            # 删除扩展名注册表项
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{extension}")
            except FileNotFoundError:
                pass
            
            # 从内存中移除
            if extension in self.associations:
                del self.associations[extension]
            
            logger.info(f"成功取消文件关联: {extension}")
            return True
            
        except Exception as e:
            logger.error(f"Windows文件关联取消失败: {str(e)}")
            return False
    
    def get_association(self, extension: str) -> Optional[FileAssociation]:
        """获取文件关联信息"""
        if extension in self.associations:
            return self.associations[extension]
        
        # 尝试从系统获取
        return self._get_system_association(extension)
    
    def _get_system_association(self, extension: str) -> Optional[FileAssociation]:
        """从系统获取文件关联"""
        try:
            if self.system_platform == "Windows":
                return self._get_windows_system_association(extension)
        except Exception as e:
            logger.error(f"获取系统文件关联失败: {str(e)}")
        
        return None
    
    def _get_windows_system_association(self, extension: str) -> Optional[FileAssociation]:
        """从Windows系统获取文件关联"""
        try:
            # 获取程序ID
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as key:
                prog_id = winreg.QueryValue(key, "")
            
            # 获取程序信息
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{prog_id}\\shell\\open\\command") as key:
                command = winreg.QueryValue(key, "")
            
            # 解析命令
            program_path = self._parse_command_string(command)
            
            if program_path:
                return FileAssociation(
                    extension=extension,
                    description=prog_id,
                    program_path=program_path,
                    program_name=Path(program_path).stem
                )
                
        except Exception:
            pass
        
        return None
    
    def _parse_command_string(self, command: str) -> Optional[str]:
        """解析命令字符串"""
        try:
            # 移除参数和引号
            parts = command.split('"')
            if len(parts) >= 2:
                return parts[1]
            return command.split()[0] if command.split() else None
        except Exception:
            return None
    
    def open_file_with_association(self, file_path: str) -> Tuple[bool, str]:
        """使用关联程序打开文件"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False, f"文件不存在: {file_path}"
            
            extension = file_path.suffix.lower()
            association = self.get_association(extension)
            
            if not association:
                return False, f"未找到文件扩展名 '{extension}' 的关联程序"
            
            # 使用关联程序打开文件
            import subprocess
            subprocess.Popen([association.program_path, str(file_path)])
            
            logger.info(f"使用 {association.program_name} 打开文件: {file_path}")
            return True, f"成功使用 {association.program_name} 打开文件"
            
        except Exception as e:
            logger.error(f"打开文件失败: {str(e)}")
            return False, f"打开文件失败: {str(e)}"
    
    def get_all_associations(self) -> List[FileAssociation]:
        """获取所有文件关联"""
        return list(self.associations.values())
    
    def export_associations(self, file_path: str) -> bool:
        """导出文件关联配置"""
        try:
            data = {
                'associations': {
                    ext: {
                        'description': assoc.description,
                        'program_path': assoc.program_path,
                        'program_name': assoc.program_name,
                        'icon_path': assoc.icon_path,
                        'mime_type': assoc.mime_type
                    }
                    for ext, assoc in self.associations.items()
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"成功导出文件关联配置到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出文件关联配置失败: {str(e)}")
            return False
    
    def import_associations(self, file_path: str) -> bool:
        """导入文件关联配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for ext, assoc_data in data.get('associations', {}).items():
                association = FileAssociation(
                    extension=ext,
                    description=assoc_data['description'],
                    program_path=assoc_data['program_path'],
                    program_name=assoc_data['program_name'],
                    icon_path=assoc_data.get('icon_path'),
                    mime_type=assoc_data.get('mime_type')
                )
                self.associations[ext] = association
            
            logger.info(f"成功从 {file_path} 导入文件关联配置")
            return True
            
        except Exception as e:
            logger.error(f"导入文件关联配置失败: {str(e)}")
            return False

# 单例实例
_file_association_manager_instance = None

def get_file_association_manager() -> FileAssociationManager:
    """获取文件关联管理器单例"""
    global _file_association_manager_instance
    if _file_association_manager_instance is None:
        _file_association_manager_instance = FileAssociationManager()
    return _file_association_manager_instance

