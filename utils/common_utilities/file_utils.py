"""
文件工具模块

提供各种文件操作的实用工具函数。
"""

import os
import shutil
import glob
import mimetypes
from typing import List, Dict, Optional, Union, Callable, Iterator
from pathlib import Path
import hashlib
import tempfile


class FileUtils:
    """文件工具类"""
    
    @staticmethod
    def read_text(file_path: str, encoding: str = 'utf-8') -> str:
        """读取文本文件
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件内容
        """
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    
    @staticmethod
    def write_text(file_path: str, content: str, 
                  encoding: str = 'utf-8') -> bool:
        """写入文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
            
        Returns:
            是否成功写入
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    @staticmethod
    def read_binary(file_path: str) -> bytes:
        """读取二进制文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容（字节）
        """
        with open(file_path, 'rb') as f:
            return f.read()
    
    @staticmethod
    def write_binary(file_path: str, content: bytes) -> bool:
        """写入二进制文件
        
        Args:
            file_path: 文件路径
            content: 文件内容（字节）
            
        Returns:
            是否成功写入
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(content)
            return True
        except Exception:
            return False
    
    @staticmethod
    def exists(file_path: str) -> bool:
        """检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否存在
        """
        return os.path.exists(file_path)
    
    @staticmethod
    def is_file(file_path: str) -> bool:
        """检查是否为文件
        
        Args:
            file_path: 路径
            
        Returns:
            是否为文件
        """
        return os.path.isfile(file_path)
    
    @staticmethod
    def is_directory(path: str) -> bool:
        """检查是否为目录
        
        Args:
            path: 路径
            
        Returns:
            是否为目录
        """
        return os.path.isdir(path)
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        return os.path.getsize(file_path)
    
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """获取文件扩展名
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件扩展名
        """
        return os.path.splitext(file_path)[1].lower()
    
    @staticmethod
    def get_file_name(file_path: str) -> str:
        """获取文件名（不含扩展名）
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """获取文件MIME类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            MIME类型
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        """复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            是否成功复制
        """
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            return True
        except Exception:
            return False
    
    @staticmethod
    def move_file(src: str, dst: str) -> bool:
        """移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            是否成功移动
        """
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        try:
            os.remove(file_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def create_directory(dir_path: str) -> bool:
        """创建目录
        
        Args:
            dir_path: 目录路径
            
        Returns:
            是否成功创建
        """
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete_directory(dir_path: str, recursive: bool = True) -> bool:
        """删除目录
        
        Args:
            dir_path: 目录路径
            recursive: 是否递归删除
            
        Returns:
            是否成功删除
        """
        try:
            if recursive:
                shutil.rmtree(dir_path)
            else:
                os.rmdir(dir_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def list_files(directory: str, pattern: str = '*', 
                  recursive: bool = False) -> List[str]:
        """列出文件
        
        Args:
            directory: 目录路径
            pattern: 文件模式
            recursive: 是否递归搜索
            
        Returns:
            文件路径列表
        """
        search_pattern = os.path.join(directory, '**', pattern) if recursive else os.path.join(directory, pattern)
        return glob.glob(search_pattern, recursive=recursive)
    
    @staticmethod
    def find_files(directory: str, pattern: str, 
                  recursive: bool = False) -> Iterator[str]:
        """查找文件
        
        Args:
            directory: 目录路径
            pattern: 文件模式
            recursive: 是否递归搜索
            
        Returns:
            文件路径迭代器
        """
        search_pattern = os.path.join(directory, '**', pattern) if recursive else os.path.join(directory, pattern)
        return glob.iglob(search_pattern, recursive=recursive)
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
        """计算文件哈希值
        
        Args:
            file_path: 文件路径
            algorithm: 哈希算法 (md5, sha1, sha256, sha512)
            
        Returns:
            哈希值
        """
        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件信息字典
        """
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified_time': stat.st_mtime,
            'created_time': stat.st_ctime,
            'is_file': os.path.isfile(file_path),
            'is_directory': os.path.isdir(file_path),
            'extension': FileUtils.get_file_extension(file_path),
            'mime_type': FileUtils.get_mime_type(file_path)
        }


class PathUtils:
    """路径工具类"""
    
    @staticmethod
    def join(*paths: str) -> str:
        """连接路径
        
        Args:
            *paths: 路径片段
            
        Returns:
            连接后的路径
        """
        return os.path.join(*paths)
    
    @staticmethod
    def normalize(path: str) -> str:
        """标准化路径
        
        Args:
            path: 路径
            
        Returns:
            标准化后的路径
        """
        return os.path.normpath(path)
    
    @staticmethod
    def absolute(path: str) -> str:
        """获取绝对路径
        
        Args:
            path: 路径
            
        Returns:
            绝对路径
        """
        return os.path.abspath(path)
    
    @staticmethod
    def dirname(path: str) -> str:
        """获取目录名
        
        Args:
            path: 路径
            
        Returns:
            目录名
        """
        return os.path.dirname(path)
    
    @staticmethod
    def basename(path: str) -> str:
        """获取文件名
        
        Args:
            path: 路径
            
        Returns:
            文件名
        """
        return os.path.basename(path)
    
    @staticmethod
    def split_extension(path: str) -> tuple:
        """分割文件名和扩展名
        
        Args:
            path: 文件路径
            
        Returns:
            (文件名, 扩展名) 元组
        """
        return os.path.splitext(path)


def ensure_directory(path: str) -> str:
    """确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        目录路径
    """
    os.makedirs(path, exist_ok=True)
    return path


def create_temp_file(suffix: str = '', prefix: str = 'tmp', 
                    directory: str = None) -> str:
    """创建临时文件
    
    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        directory: 目录
        
    Returns:
        临时文件路径
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    os.close(fd)
    return path


def create_temp_directory(suffix: str = '', prefix: str = 'tmp', 
                         directory: str = None) -> str:
    """创建临时目录
    
    Args:
        suffix: 目录后缀
        prefix: 目录前缀
        directory: 父目录
        
    Returns:
        临时目录路径
    """
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=directory)