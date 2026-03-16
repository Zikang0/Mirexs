"""
临时文件管理模块 - 临时文件管理
负责管理临时文件的创建、使用和清理
"""

import os
import tempfile
import shutil
import uuid
import time
from typing import Optional, List, Dict, Any, BinaryIO, TextIO
from pathlib import Path
import threading
from dataclasses import dataclass
from enum import Enum

class TempFileType(Enum):
    TEXT = "text"
    BINARY = "binary"
    JSON = "json"
    PICKLE = "pickle"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MODEL = "model"
    OTHER = "other"

@dataclass
class TempFileInfo:
    file_id: str
    file_path: Path
    file_type: TempFileType
    created_at: float
    expires_at: float
    size: int
    access_count: int
    last_accessed: float
    tags: List[str]
    description: Optional[str] = None

class TempFileManager:
    """临时文件管理器"""
    
    def __init__(self, temp_dir: Optional[str] = None, default_ttl: int = 3600):
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "mirexs"
        self.default_ttl = default_ttl
        
        # 创建临时目录
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件索引
        self.file_index: Dict[str, TempFileInfo] = {}
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "files_created": 0,
            "files_deleted": 0,
            "total_disk_usage": 0,
            "cleanup_cycles": 0
        }
        
        # 加载现有索引
        self._load_index()
    
    def create_temp_file(self, 
                        content: Any = None,
                        file_type: TempFileType = TempFileType.TEXT,
                        filename: Optional[str] = None,
                        ttl: Optional[int] = None,
                        tags: Optional[List[str]] = None,
                        description: Optional[str] = None) -> Optional[str]:
        """
        创建临时文件
        
        Args:
            content: 文件内容
            file_type: 文件类型
            filename: 文件名（可选）
            ttl: 生存时间（秒）
            tags: 文件标签
            description: 文件描述
            
        Returns:
            文件ID或None
        """
        with self.lock:
            try:
                # 生成文件ID和路径
                file_id = str(uuid.uuid4())
                if filename:
                    safe_filename = self._sanitize_filename(filename)
                    file_path = self.temp_dir / f"{file_id}_{safe_filename}"
                else:
                    extension = self._get_extension(file_type)
                    file_path = self.temp_dir / f"{file_id}{extension}"
                
                # 写入内容
                if content is not None:
                    self._write_content(file_path, content, file_type)
                
                # 计算文件大小
                size = file_path.stat().st_size if file_path.exists() else 0
                
                # 计算过期时间
                expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
                
                # 创建文件信息
                file_info = TempFileInfo(
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    created_at=time.time(),
                    expires_at=expires_at,
                    size=size,
                    access_count=0,
                    last_accessed=time.time(),
                    tags=tags or [],
                    description=description
                )
                
                # 更新索引
                self.file_index[file_id] = file_info
                self._save_index()
                
                self.stats["files_created"] += 1
                self.stats["total_disk_usage"] += size
                
                return file_id
                
            except Exception as e:
                print(f"创建临时文件失败: {e}")
                return None
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """获取文件路径"""
        with self.lock:
            if file_id in self.file_index:
                file_info = self.file_index[file_id]
                
                # 检查是否过期
                if time.time() > file_info.expires_at:
                    self.delete_file(file_id)
                    return None
                
                # 更新访问信息
                file_info.access_count += 1
                file_info.last_accessed = time.time()
                self._save_index()
                
                return file_info.file_path
            
            return None
    
    def read_file_content(self, file_id: str, default: Any = None) -> Any:
        """读取文件内容"""
        file_path = self.get_file_path(file_id)
        if not file_path or not file_path.exists():
            return default
        
        try:
            file_info = self.file_index[file_id]
            return self._read_content(file_path, file_info.file_type)
        except Exception as e:
            print(f"读取临时文件失败: {e}")
            return default
    
    def write_file_content(self, file_id: str, content: Any) -> bool:
        """写入文件内容"""
        file_path = self.get_file_path(file_id)
        if not file_path:
            return False
        
        try:
            file_info = self.file_index[file_id]
            self._write_content(file_path, content, file_info.file_type)
            
            # 更新文件大小
            file_info.size = file_path.stat().st_size
            self._save_index()
            
            return True
        except Exception as e:
            print(f"写入临时文件失败: {e}")
            return False
    
    def delete_file(self, file_id: str) -> bool:
        """删除临时文件"""
        with self.lock:
            if file_id not in self.file_index:
                return False
            
            try:
                file_info = self.file_index[file_id]
                
                # 删除物理文件
                if file_info.file_path.exists():
                    file_info.file_path.unlink()
                
                # 更新统计
                self.stats["files_deleted"] += 1
                self.stats["total_disk_usage"] -= file_info.size
                
                # 从索引中移除
                del self.file_index[file_id]
                self._save_index()
                
                return True
                
            except Exception as e:
                print(f"删除临时文件失败: {e}")
                return False
    
    def cleanup_expired(self) -> int:
        """清理过期文件"""
        with self.lock:
            current_time = time.time()
            files_to_delete = []
            
            for file_id, file_info in self.file_index.items():
                if current_time > file_info.expires_at:
                    files_to_delete.append(file_id)
            
            deleted_count = 0
            for file_id in files_to_delete:
                if self.delete_file(file_id):
                    deleted_count += 1
            
            self.stats["cleanup_cycles"] += 1
            return deleted_count
    
    def get_file_info(self, file_id: str) -> Optional[TempFileInfo]:
        """获取文件信息"""
        with self.lock:
            if file_id in self.file_index:
                file_info = self.file_index[file_id]
                
                # 检查是否过期
                if time.time() > file_info.expires_at:
                    self.delete_file(file_id)
                    return None
                
                return file_info
            
            return None
    
    def list_files(self, 
                  file_type: Optional[TempFileType] = None,
                  tags: Optional[List[str]] = None,
                  include_expired: bool = False) -> List[TempFileInfo]:
        """列出文件"""
        with self.lock:
            files = []
            current_time = time.time()
            
            for file_info in self.file_index.values():
                # 检查过期
                if not include_expired and current_time > file_info.expires_at:
                    continue
                
                # 过滤文件类型
                if file_type and file_info.file_type != file_type:
                    continue
                
                # 过滤标签
                if tags and not any(tag in file_info.tags for tag in tags):
                    continue
                
                files.append(file_info)
            
            # 按创建时间排序
            files.sort(key=lambda x: x.created_at, reverse=True)
            return files
    
    def extend_ttl(self, file_id: str, additional_ttl: int) -> bool:
        """延长文件生存时间"""
        with self.lock:
            if file_id not in self.file_index:
                return False
            
            file_info = self.file_index[file_id]
            file_info.expires_at += additional_ttl
            self._save_index()
            
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            total_files = len(self.file_index)
            total_size = sum(info.size for info in self.file_index.values())
            expired_files = sum(1 for info in self.file_index.values() 
                              if time.time() > info.expires_at)
            
            return {
                **self.stats,
                "current_file_count": total_files,
                "expired_file_count": expired_files,
                "total_disk_usage_mb": total_size / 1024 / 1024,
                "temp_directory": str(self.temp_dir)
            }
    
    def _write_content(self, file_path: Path, content: Any, file_type: TempFileType):
        """写入文件内容"""
        if file_type == TempFileType.TEXT:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(content))
        
        elif file_type == TempFileType.JSON:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
        
        elif file_type == TempFileType.PICKLE:
            import pickle
            with open(file_path, 'wb') as f:
                pickle.dump(content, f)
        
        elif file_type == TempFileType.BINARY:
            with open(file_path, 'wb') as f:
                if isinstance(content, (bytes, bytearray)):
                    f.write(content)
                else:
                    f.write(str(content).encode('utf-8'))
        
        else:
            # 默认按文本处理
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(content))
    
    def _read_content(self, file_path: Path, file_type: TempFileType) -> Any:
        """读取文件内容"""
        if not file_path.exists():
            return None
        
        try:
            if file_type == TempFileType.TEXT:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif file_type == TempFileType.JSON:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif file_type == TempFileType.PICKLE:
                import pickle
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            
            elif file_type == TempFileType.BINARY:
                with open(file_path, 'rb') as f:
                    return f.read()
            
            else:
                # 默认按文本处理
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
                    
        except Exception as e:
            print(f"读取文件内容失败: {e}")
            return None
    
    def _get_extension(self, file_type: TempFileType) -> str:
        """获取文件扩展名"""
        extensions = {
            TempFileType.TEXT: ".txt",
            TempFileType.JSON: ".json",
            TempFileType.PICKLE: ".pkl",
            TempFileType.BINARY: ".bin",
            TempFileType.IMAGE: ".img",
            TempFileType.AUDIO: ".audio",
            TempFileType.VIDEO: ".video",
            TempFileType.MODEL: ".model"
        }
        return extensions.get(file_type, ".tmp")
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        # 移除危险字符
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # 限制长度
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:100-len(ext)] + ext
        
        return filename
    
    def _load_index(self):
        """加载文件索引"""
        index_file = self.temp_dir / "file_index.json"
        if not index_file.exists():
            return
        
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                
                for file_id, file_data in data.items():
                    # 转换回TempFileInfo对象
                    file_info = TempFileInfo(
                        file_id=file_data['file_id'],
                        file_path=Path(file_data['file_path']),
                        file_type=TempFileType(file_data['file_type']),
                        created_at=file_data['created_at'],
                        expires_at=file_data['expires_at'],
                        size=file_data['size'],
                        access_count=file_data['access_count'],
                        last_accessed=file_data['last_accessed'],
                        tags=file_data['tags'],
                        description=file_data.get('description')
                    )
                    self.file_index[file_id] = file_info
                    
        except Exception as e:
            print(f"加载文件索引失败: {e}")
    
    def _save_index(self):
        """保存文件索引"""
        index_file = self.temp_dir / "file_index.json"
        try:
            # 转换为可序列化的格式
            index_data = {}
            for file_id, file_info in self.file_index.items():
                index_data[file_id] = {
                    'file_id': file_info.file_id,
                    'file_path': str(file_info.file_path),
                    'file_type': file_info.file_type.value,
                    'created_at': file_info.created_at,
                    'expires_at': file_info.expires_at,
                    'size': file_info.size,
                    'access_count': file_info.access_count,
                    'last_accessed': file_info.last_accessed,
                    'tags': file_info.tags,
                    'description': file_info.description
                }
            
            with open(index_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(index_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存文件索引失败: {e}")
    
    def cleanup_all(self) -> int:
        """清理所有临时文件"""
        with self.lock:
            file_ids = list(self.file_index.keys())
            deleted_count = 0
            
            for file_id in file_ids:
                if self.delete_file(file_id):
                    deleted_count += 1
            
            return deleted_count

# 全局临时文件管理器实例
temp_file_manager = TempFileManager()
