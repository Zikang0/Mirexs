"""
存储优化器：优化存储空间使用
"""
import os
import shutil
import psutil
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import subprocess

logger = logging.getLogger(__name__)

class StorageType(Enum):
    """存储类型枚举"""
    HDD = "hdd"
    SSD = "ssd"
    NETWORK = "network"
    CLOUD = "cloud"
    REMOVABLE = "removable"

class OptimizationType(Enum):
    """优化类型枚举"""
    CLEANUP = "cleanup"
    DEFRAGMENTATION = "defragmentation"
    COMPRESSION = "compression"
    DEDUPLICATION = "deduplication"
    ARCHIVING = "archiving"

@dataclass
class StorageAnalysis:
    """存储分析结果"""
    drive: str
    total_size: int
    used_size: int
    free_size: int
    usage_percent: float
    storage_type: StorageType
    analysis_time: datetime
    large_files: List[Dict[str, Any]]
    duplicate_files: List[Dict[str, Any]]
    temporary_files: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['storage_type'] = self.storage_type.value
        data['analysis_time'] = self.analysis_time.isoformat()
        return data

@dataclass
class OptimizationResult:
    """优化结果"""
    optimization_type: OptimizationType
    drive: str
    start_time: datetime
    end_time: datetime
    space_freed: int
    files_processed: int
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['optimization_type'] = self.optimization_type.value
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data

class StorageOptimizer:
    """存储优化器"""
    
    def __init__(self):
        self.is_optimizing = False
        self.optimization_thread: Optional[threading.Thread] = None
        self.storage_analysis: Dict[str, StorageAnalysis] = {}
        self.optimization_history: List[OptimizationResult] = []
        self.optimization_config = self._load_optimization_config()
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_optimization_config(self) -> Dict[str, Any]:
        """加载优化配置"""
        return {
            "cleanup_threshold": 85.0,  # 使用率超过85%时触发清理
            "large_file_threshold": 100 * 1024 * 1024,  # 100MB
            "temp_file_retention_days": 7,
            "analysis_interval": 3600,  # 分析间隔（秒）
            "optimization_schedule": "0 2 * * *"  # 每天凌晨2点
        }
    
    def analyze_storage(self, drive: str = None) -> Dict[str, StorageAnalysis]:
        """分析存储使用情况"""
        analysis_results = {}
        
        try:
            if drive:
                drives = [drive]
            else:
                # 获取所有驱动器
                drives = [partition.mountpoint for partition in psutil.disk_partitions()]
            
            for drive_path in drives:
                try:
                    analysis = self._analyze_drive(drive_path)
                    if analysis:
                        analysis_results[drive_path] = analysis
                        logger.info(f"存储分析完成: {drive_path} - 使用率: {analysis.usage_percent:.1f}%")
                
                except Exception as e:
                    logger.error(f"分析驱动器 {drive_path} 失败: {str(e)}")
            
            self.storage_analysis.update(analysis_results)
            return analysis_results
            
        except Exception as e:
            logger.error(f"存储分析失败: {str(e)}")
            return {}
    
    def _analyze_drive(self, drive_path: str) -> Optional[StorageAnalysis]:
        """分析单个驱动器"""
        try:
            # 获取磁盘使用情况
            usage = shutil.disk_usage(drive_path)
            total_size = usage.total
            used_size = usage.used
            free_size = usage.free
            usage_percent = (used_size / total_size) * 100
            
            # 确定存储类型
            storage_type = self._detect_storage_type(drive_path)
            
            # 分析大文件
            large_files = self._find_large_files(drive_path)
            
            # 分析重复文件
            duplicate_files = self._find_duplicate_files(drive_path)
            
            # 分析临时文件
            temporary_files = self._find_temporary_files(drive_path)
            
            return StorageAnalysis(
                drive=drive_path,
                total_size=total_size,
                used_size=used_size,
                free_size=free_size,
                usage_percent=usage_percent,
                storage_type=storage_type,
                analysis_time=datetime.now(),
                large_files=large_files,
                duplicate_files=duplicate_files,
                temporary_files=temporary_files
            )
            
        except Exception as e:
            logger.error(f"分析驱动器 {drive_path} 失败: {str(e)}")
            return None
    
    def _detect_storage_type(self, drive_path: str) -> StorageType:
        """检测存储类型"""
        try:
            # 简化实现，实际应该使用系统API检测
            if drive_path.startswith('\\\\'):
                return StorageType.NETWORK
            
            # 检查是否为可移动设备
            for partition in psutil.disk_partitions():
                if partition.mountpoint == drive_path and 'removable' in partition.opts:
                    return StorageType.REMOVABLE
            
            # 默认假设为HDD
            return StorageType.HDD
            
        except Exception:
            return StorageType.HDD
    
    def _find_large_files(self, drive_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """查找大文件"""
        large_files = []
        
        try:
            for root, dirs, files in os.walk(drive_path):
                for file in files:
                    if len(large_files) >= limit:
                        break
                    
                    try:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        
                        threshold = self.optimization_config["large_file_threshold"]
                        if file_size > threshold:
                            large_files.append({
                                'path': file_path,
                                'size': file_size,
                                'size_mb': file_size / (1024 * 1024),
                                'modified_time': datetime.fromtimestamp(os.path.getmtime(file_path))
                            })
                    
                    except (OSError, IOError):
                        continue
                
                if len(large_files) >= limit:
                    break
        
        except Exception as e:
            logger.error(f"查找大文件失败 {drive_path}: {str(e)}")
        
        # 按文件大小排序
        large_files.sort(key=lambda x: x['size'], reverse=True)
        return large_files
    
    def _find_duplicate_files(self, drive_path: str) -> List[Dict[str, Any]]:
        """查找重复文件"""
        duplicate_files = []
        
        try:
            file_hashes = {}
            
            for root, dirs, files in os.walk(drive_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        
                        # 只检查大于1KB的文件
                        if file_size > 1024:
                            file_hash = self._calculate_file_hash(file_path)
                            
                            if file_hash in file_hashes:
                                file_hashes[file_hash].append(file_path)
                            else:
                                file_hashes[file_hash] = [file_path]
                    
                    except (OSError, IOError):
                        continue
            
            # 找出重复的文件
            for file_hash, file_paths in file_hashes.items():
                if len(file_paths) > 1:
                    duplicate_files.append({
                        'hash': file_hash,
                        'files': file_paths,
                        'size': os.path.getsize(file_paths[0]) if file_paths else 0,
                        'duplicate_count': len(file_paths)
                    })
        
        except Exception as e:
            logger.error(f"查找重复文件失败 {drive_path}: {str(e)}")
        
        return duplicate_files
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            import hashlib
            
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                # 只读取文件的前1MB来计算哈希（为了性能）
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
                    if f.tell() > 1024 * 1024:  # 1MB
                        break
            
            return hash_md5.hexdigest()
            
        except Exception:
            return "unknown"
    
    def _find_temporary_files(self, drive_path: str) -> List[Dict[str, Any]]:
        """查找临时文件"""
        temporary_files = []
        
        try:
            temp_patterns = ['*.tmp', '*.temp', '~*', '*.log']
            retention_days = self.optimization_config["temp_file_retention_days"]
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            for root, dirs, files in os.walk(drive_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        
                        # 检查文件扩展名
                        if any(file.lower().endswith(pattern.strip('*')) for pattern in temp_patterns):
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            if file_time < cutoff_time:
                                temporary_files.append({
                                    'path': file_path,
                                    'size': os.path.getsize(file_path),
                                    'modified_time': file_time,
                                    'age_days': (datetime.now() - file_time).days
                                })
                    
                    except (OSError, IOError):
                        continue
        
        except Exception as e:
            logger.error(f"查找临时文件失败 {drive_path}: {str(e)}")
        
        return temporary_files
    
    def optimize_storage(self, drive: str, optimization_types: List[OptimizationType] = None) -> bool:
        """优化存储"""
        if self.is_optimizing:
            return False
        
        if optimization_types is None:
            optimization_types = [
                OptimizationType.CLEANUP,
                OptimizationType.DEFRAGMENTATION
            ]
        
        try:
            self.is_optimizing = True
            self.optimization_thread = threading.Thread(
                target=self._optimization_worker,
                args=(drive, optimization_types),
                daemon=True
            )
            self.optimization_thread.start()
            
            logger.info(f"开始存储优化: {drive}")
            return True
            
        except Exception as e:
            logger.error(f"启动存储优化失败: {str(e)}")
            return False
    
    def _optimization_worker(self, drive: str, optimization_types: List[OptimizationType]):
        """优化工作线程"""
        try:
            optimization_results = []
            
            for opt_type in optimization_types:
                if opt_type == OptimizationType.CLEANUP:
                    result = self._perform_cleanup(drive)
                elif opt_type == OptimizationType.DEFRAGMENTATION:
                    result = self._perform_defragmentation(drive)
                elif opt_type == OptimizationType.COMPRESSION:
                    result = self._perform_compression(drive)
                elif opt_type == OptimizationType.DEDUPLICATION:
                    result = self._perform_deduplication(drive)
                else:
                    result = OptimizationResult(
                        optimization_type=opt_type,
                        drive=drive,
                        start_time=datetime.now(),
                        end_time=datetime.now(),
                        space_freed=0,
                        files_processed=0,
                        details={'error': '不支持的优化类型'}
                    )
                
                optimization_results.append(result)
                self.optimization_history.append(result)
            
            self.is_optimizing = False
            logger.info(f"存储优化完成: {drive}")
            
        except Exception as e:
            logger.error(f"存储优化工作线程错误: {str(e)}")
            self.is_optimizing = False
    
    def _perform_cleanup(self, drive: str) -> OptimizationResult:
        """执行清理优化"""
        start_time = datetime.now()
        space_freed = 0
        files_processed = 0
        
        try:
            # 分析临时文件
            analysis = self._analyze_drive(drive)
            if not analysis:
                raise Exception("无法分析驱动器")
            
            # 清理临时文件
            for temp_file in analysis.temporary_files:
                try:
                    file_size = temp_file['size']
                    os.remove(temp_file['path'])
                    space_freed += file_size
                    files_processed += 1
                except Exception as e:
                    logger.warning(f"删除临时文件失败 {temp_file['path']}: {str(e)}")
            
            # 清理回收站（Windows）
            if platform.system() == "Windows":
                try:
                    from win32com.shell import shell, shellcon
                    result = shell.SHEmptyRecycleBin(None, None, shellcon.SHERB_NOCONFIRMATION)
                    if result == 0:
                        logger.info("回收站已清空")
                except ImportError:
                    logger.warning("无法清空回收站，缺少win32com模块")
            
            end_time = datetime.now()
            
            return OptimizationResult(
                optimization_type=OptimizationType.CLEANUP,
                drive=drive,
                start_time=start_time,
                end_time=end_time,
                space_freed=space_freed,
                files_processed=files_processed,
                details={
                    'space_freed_mb': space_freed / (1024 * 1024),
                    'cleaned_temp_files': files_processed
                }
            )
            
        except Exception as e:
            end_time = datetime.now()
            return OptimizationResult(
                optimization_type=OptimizationType.CLEANUP,
                drive=drive,
                start_time=start_time,
                end_time=end_time,
                space_freed=0,
                files_processed=0,
                details={'error': str(e)}
            )
    
    def _perform_defragmentation(self, drive: str) -> OptimizationResult:
        """执行碎片整理"""
        start_time = datetime.now()
        
        try:
            if platform.system() == "Windows":
                # 执行磁盘碎片整理
                result = subprocess.run(
                    ['defrag', drive, '/O'],
                    capture_output=True, text=True, timeout=3600
                )
                
                end_time = datetime.now()
                
                if result.returncode == 0:
                    return OptimizationResult(
                        optimization_type=OptimizationType.DEFRAGMENTATION,
                        drive=drive,
                        start_time=start_time,
                        end_time=end_time,
                        space_freed=0,
                        files_processed=0,
                        details={'output': result.stdout}
                    )
                else:
                    return OptimizationResult(
                        optimization_type=OptimizationType.DEFRAGMENTATION,
                        drive=drive,
                        start_time=start_time,
                        end_time=end_time,
                        space_freed=0,
                        files_processed=0,
                        details={'error': result.stderr}
                    )
            else:
                end_time = datetime.now()
                return OptimizationResult(
                    optimization_type=OptimizationType.DEFRAGMENTATION,
                    drive=drive,
                    start_time=start_time,
                    end_time=end_time,
                    space_freed=0,
                    files_processed=0,
                    details={'error': '不支持的操作系统'}
                )
            
        except Exception as e:
            end_time = datetime.now()
            return OptimizationResult(
                optimization_type=OptimizationType.DEFRAGMENTATION,
                drive=drive,
                start_time=start_time,
                end_time=end_time,
                space_freed=0,
                files_processed=0,
                details={'error': str(e)}
            )
    
    def _perform_compression(self, drive: str) -> OptimizationResult:
        """执行压缩优化"""
        # 实现压缩优化逻辑
        start_time = datetime.now()
        end_time = datetime.now()
        
        return OptimizationResult(
            optimization_type=OptimizationType.COMPRESSION,
            drive=drive,
            start_time=start_time,
            end_time=end_time,
            space_freed=0,
            files_processed=0,
            details={'message': '压缩优化功能待实现'}
        )
    
    def _perform_deduplication(self, drive: str) -> OptimizationResult:
        """执行去重优化"""
        start_time = datetime.now()
        space_freed = 0
        files_processed = 0
        
        try:
            # 分析重复文件
            analysis = self._analyze_drive(drive)
            if not analysis:
                raise Exception("无法分析驱动器")
            
            # 处理重复文件（保留一个副本，删除其他）
            for duplicate_group in analysis.duplicate_files:
                if len(duplicate_group['files']) > 1:
                    # 保留第一个文件，删除其他
                    keep_file = duplicate_group['files'][0]
                    
                    for file_path in duplicate_group['files'][1:]:
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            space_freed += file_size
                            files_processed += 1
                        except Exception as e:
                            logger.warning(f"删除重复文件失败 {file_path}: {str(e)}")
            
            end_time = datetime.now()
            
            return OptimizationResult(
                optimization_type=OptimizationType.DEDUPLICATION,
                drive=drive,
                start_time=start_time,
                end_time=end_time,
                space_freed=space_freed,
                files_processed=files_processed,
                details={
                    'space_freed_mb': space_freed / (1024 * 1024),
                    'duplicate_groups_processed': len(analysis.duplicate_files)
                }
            )
            
        except Exception as e:
            end_time = datetime.now()
            return OptimizationResult(
                optimization_type=OptimizationType.DEDUPLICATION,
                drive=drive,
                start_time=start_time,
                end_time=end_time,
                space_freed=0,
                files_processed=0,
                details={'error': str(e)}
            )
    
    def get_optimization_recommendations(self, drive: str) -> List[Dict[str, Any]]:
        """获取优化建议"""
        recommendations = []
        
        try:
            analysis = self.storage_analysis.get(drive)
            if not analysis:
                analysis = self._analyze_drive(drive)
                if not analysis:
                    return recommendations
            
            # 基于使用率的建议
            if analysis.usage_percent > self.optimization_config["cleanup_threshold"]:
                recommendations.append({
                    'type': 'cleanup',
                    'priority': 'high',
                    'title': '存储空间不足',
                    'description': f'驱动器 {drive} 使用率已达 {analysis.usage_percent:.1f}%',
                    'suggestion': '执行存储清理以释放空间',
                    'estimated_space': analysis.used_size * 0.1  # 预估可释放10%空间
                })
            
            # 基于大文件的建议
            if analysis.large_files:
                total_large_file_size = sum(f['size'] for f in analysis.large_files[:10])
                recommendations.append({
                    'type': 'large_files',
                    'priority': 'medium',
                    'title': '发现大文件',
                    'description': f'发现 {len(analysis.large_files)} 个大文件占用大量空间',
                    'suggestion': '审查并归档或删除不必要的大文件',
                    'estimated_space': total_large_file_size
                })
            
            # 基于重复文件的建议
            if analysis.duplicate_files:
                total_duplicate_size = sum(g['size'] * (g['duplicate_count'] - 1) for g in analysis.duplicate_files)
                recommendations.append({
                    'type': 'duplicates',
                    'priority': 'medium',
                    'title': '发现重复文件',
                    'description': f'发现 {len(analysis.duplicate_files)} 组重复文件',
                    'suggestion': '执行文件去重以释放空间',
                    'estimated_space': total_duplicate_size
                })
            
            # 基于临时文件的建议
            if analysis.temporary_files:
                total_temp_size = sum(f['size'] for f in analysis.temporary_files)
                recommendations.append({
                    'type': 'temp_files',
                    'priority': 'low',
                    'title': '发现临时文件',
                    'description': f'发现 {len(analysis.temporary_files)} 个可清理的临时文件',
                    'suggestion': '清理临时文件以释放空间',
                    'estimated_space': total_temp_size
                })
        
        except Exception as e:
            logger.error(f"获取优化建议失败: {str(e)}")
        
        return recommendations
    
    def get_optimization_history(self, drive: str = None) -> List[OptimizationResult]:
        """获取优化历史"""
        if drive:
            return [result for result in self.optimization_history if result.drive == drive]
        else:
            return self.optimization_history
    
    def export_storage_report(self, file_path: str) -> bool:
        """导出存储报告"""
        try:
            report = {
                'generated_time': datetime.now().isoformat(),
                'storage_analysis': {
                    drive: analysis.to_dict() 
                    for drive, analysis in self.storage_analysis.items()
                },
                'optimization_history': [
                    result.to_dict() for result in self.optimization_history
                ],
                'recommendations': {}
            }
            
            # 为每个驱动器添加建议
            for drive in self.storage_analysis:
                report['recommendations'][drive] = self.get_optimization_recommendations(drive)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"存储报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出存储报告失败: {str(e)}")
            return False

# 单例实例
_storage_optimizer_instance = None

def get_storage_optimizer() -> StorageOptimizer:
    """获取存储优化器单例"""
    global _storage_optimizer_instance
    if _storage_optimizer_instance is None:
        _storage_optimizer_instance = StorageOptimizer()
    return _storage_optimizer_instance

