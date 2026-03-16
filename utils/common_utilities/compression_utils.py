"""
压缩工具模块

提供各种数据压缩和解压缩的实用工具函数。
"""

import gzip
import zipfile
import tarfile
import bz2
import lzma
import zlib
from typing import Union, Optional, BinaryIO, Dict, Any
import os
import io


class CompressionUtils:
    """压缩工具类"""
    
    @staticmethod
    def compress_gzip(data: Union[str, bytes], 
                     compresslevel: int = 9) -> bytes:
        """使用gzip压缩数据
        
        Args:
            data: 要压缩的数据
            compresslevel: 压缩级别 (1-9, 9是最高压缩率)
            
        Returns:
            压缩后的字节数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return gzip.compress(data, compresslevel=compresslevel)
    
    @staticmethod
    def decompress_gzip(compressed_data: bytes) -> bytes:
        """使用gzip解压缩数据
        
        Args:
            compressed_data: 压缩后的数据
            
        Returns:
            解压缩后的字节数据
        """
        return gzip.decompress(compressed_data)
    
    @staticmethod
    def compress_bz2(data: Union[str, bytes]) -> bytes:
        """使用bz2压缩数据
        
        Args:
            data: 要压缩的数据
            
        Returns:
            压缩后的字节数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return bz2.compress(data)
    
    @staticmethod
    def decompress_bz2(compressed_data: bytes) -> bytes:
        """使用bz2解压缩数据
        
        Args:
            compressed_data: 压缩后的数据
            
        Returns:
            解压缩后的字节数据
        """
        return bz2.decompress(compressed_data)
    
    @staticmethod
    def compress_lzma(data: Union[str, bytes]) -> bytes:
        """使用lzma压缩数据
        
        Args:
            data: 要压缩的数据
            
        Returns:
            压缩后的字节数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return lzma.compress(data)
    
    @staticmethod
    def decompress_lzma(compressed_data: bytes) -> bytes:
        """使用lzma解压缩数据
        
        Args:
            compressed_data: 压缩后的数据
            
        Returns:
            解压缩后的字节数据
        """
        return lzma.decompress(compressed_data)
    
    @staticmethod
    def compress_zlib(data: Union[str, bytes], level: int = 6) -> bytes:
        """使用zlib压缩数据
        
        Args:
            data: 要压缩的数据
            level: 压缩级别 (1-9)
            
        Returns:
            压缩后的字节数据
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return zlib.compress(data, level=level)
    
    @staticmethod
    def decompress_zlib(compressed_data: bytes) -> bytes:
        """使用zlib解压缩数据
        
        Args:
            compressed_data: 压缩后的数据
            
        Returns:
            解压缩后的字节数据
        """
        return zlib.decompress(compressed_data)


class ArchiveUtils:
    """归档工具类"""
    
    @staticmethod
    def create_zip_archive(files: Dict[str, str], 
                          archive_path: str) -> bool:
        """创建ZIP归档文件
        
        Args:
            files: 文件映射 {内部路径: 外部文件路径}
            archive_path: 归档文件路径
            
        Returns:
            是否成功创建
        """
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for internal_path, file_path in files.items():
                    if os.path.exists(file_path):
                        zipf.write(file_path, internal_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def extract_zip_archive(archive_path: str, 
                           extract_path: str) -> bool:
        """提取ZIP归档文件
        
        Args:
            archive_path: 归档文件路径
            extract_path: 提取路径
            
        Returns:
            是否成功提取
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                zipf.extractall(extract_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def list_zip_contents(archive_path: str) -> list:
        """列出ZIP归档内容
        
        Args:
            archive_path: 归档文件路径
            
        Returns:
            文件列表
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                return zipf.namelist()
        except Exception:
            return []
    
    @staticmethod
    def create_tar_archive(files: Dict[str, str], 
                          archive_path: str, 
                          compression: str = 'gz') -> bool:
        """创建TAR归档文件
        
        Args:
            files: 文件映射 {内部路径: 外部文件路径}
            archive_path: 归档文件路径
            compression: 压缩类型 ('gz', 'bz2', 'xz', None)
            
        Returns:
            是否成功创建
        """
        try:
            mode = 'w'
            if compression == 'gz':
                mode += ':gz'
            elif compression == 'bz2':
                mode += ':bz2'
            elif compression == 'xz':
                mode += ':xz'
            
            with tarfile.open(archive_path, mode) as tarf:
                for internal_path, file_path in files.items():
                    if os.path.exists(file_path):
                        tarf.add(file_path, arcname=internal_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def extract_tar_archive(archive_path: str, 
                           extract_path: str) -> bool:
        """提取TAR归档文件
        
        Args:
            archive_path: 归档文件路径
            extract_path: 提取路径
            
        Returns:
            是否成功提取
        """
        try:
            with tarfile.open(archive_path, 'r:*') as tarf:
                tarf.extractall(extract_path)
            return True
        except Exception:
            return False


def get_compression_ratio(original_size: int, compressed_size: int) -> float:
    """计算压缩比
    
    Args:
        original_size: 原始大小
        compressed_size: 压缩后大小
        
    Returns:
        压缩比 (0-1, 越小压缩率越高)
    """
    if original_size == 0:
        return 0.0
    return compressed_size / original_size


def get_compression_savings(original_size: int, compressed_size: int) -> float:
    """计算压缩节省的空间
    
    Args:
        original_size: 原始大小
        compressed_size: 压缩后大小
        
    Returns:
        节省的字节数
    """
    return original_size - compressed_size


def get_compression_percentage(original_size: int, compressed_size: int) -> float:
    """计算压缩百分比
    
    Args:
        original_size: 原始大小
        compressed_size: 压缩后大小
        
    Returns:
        压缩百分比
    """
    if original_size == 0:
        return 0.0
    return (1 - compressed_size / original_size) * 100


def detect_compression_type(data: bytes) -> Optional[str]:
    """检测压缩类型
    
    Args:
        data: 数据字节
        
    Returns:
        压缩类型 ('gzip', 'bz2', 'lzma', 'zip', 'tar', None)
    """
    # 检查ZIP文件签名
    if data.startswith(b'PK'):
        return 'zip'
    
    # 检查GZIP文件签名
    if data.startswith(b'\x1f\x8b'):
        return 'gzip'
    
    # 检查BZ2文件签名
    if data.startswith(b'BZ'):
        return 'bz2'
    
    # 检查LZMA文件签名
    if data.startswith(b'\xfd7zXZ'):
        return 'lzma'
    
    # 检查TAR文件签名
    if data.startswith(b'ustar') or b'ustar\x00' in data[:512]:
        return 'tar'
    
    return None