"""
恢复管理器：系统故障恢复
"""
import os
import shutil
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import tempfile
import psutil

logger = logging.getLogger(__name__)

class RecoveryType(Enum):
    """恢复类型枚举"""
    SYSTEM_RESTORE = "system_restore"
    FILE_RECOVERY = "file_recovery"
    REGISTRY_RESTORE = "registry_restore"
    DRIVER_ROLLBACK = "driver_rollback"
    APPLICATION_RECOVERY = "application_recovery"
    NETWORK_RESET = "network_reset"

class RecoveryStatus(Enum):
    """恢复状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RecoveryPoint:
    """恢复点"""
    id: str
    name: str
    description: str
    recovery_type: RecoveryType
    created_time: datetime
    size: int
    location: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['recovery_type'] = self.recovery_type.value
        data['created_time'] = self.created_time.isoformat()
        return data

@dataclass
class RecoveryOperation:
    """恢复操作"""
    id: str
    recovery_type: RecoveryType
    target: str
    description: str
    status: RecoveryStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.result is None:
            self.result = {}

class RecoveryManager:
    """恢复管理器"""
    
    def __init__(self):
        self.recovery_points: Dict[str, RecoveryPoint] = {}
        self.recovery_operations: List[RecoveryOperation] = []
        self.is_recovering = False
        self.recovery_thread: Optional[threading.Thread] = None
        self.recovery_config = self._load_recovery_config()
        self._setup_logging()
        self._initialize_recovery_system()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_recovery_config(self) -> Dict[str, Any]:
        """加载恢复配置"""
        return {
            "auto_backup": True,
            "backup_interval": 86400,  # 24小时
            "max_recovery_points": 10,
            "backup_locations": [
                "C:\\Users",
                "C:\\ImportantData"
            ],
            "excluded_paths": [
                "C:\\Windows\\Temp",
                tempfile.gettempdir()
            ]
        }
    
    def _initialize_recovery_system(self):
        """初始化恢复系统"""
        # 创建恢复目录
        recovery_dir = Path("recovery")
        recovery_dir.mkdir(exist_ok=True)
        
        # 加载现有的恢复点
        self._load_existing_recovery_points()
    
    def _load_existing_recovery_points(self):
        """加载现有的恢复点"""
        try:
            recovery_points_file = Path("recovery/recovery_points.json")
            if recovery_points_file.exists():
                with open(recovery_points_file, 'r', encoding='utf-8') as f:
                    points_data = json.load(f)
                
                for point_data in points_data.get('recovery_points', []):
                    point = RecoveryPoint(
                        id=point_data['id'],
                        name=point_data['name'],
                        description=point_data['description'],
                        recovery_type=RecoveryType(point_data['recovery_type']),
                        created_time=datetime.fromisoformat(point_data['created_time']),
                        size=point_data['size'],
                        location=point_data['location'],
                        metadata=point_data['metadata']
                    )
                    self.recovery_points[point.id] = point
                
                logger.info(f"加载了 {len(self.recovery_points)} 个恢复点")
            
        except Exception as e:
            logger.error(f"加载恢复点失败: {str(e)}")
    
    def create_recovery_point(self, name: str, description: str, 
                            recovery_type: RecoveryType = RecoveryType.SYSTEM_RESTORE) -> Optional[str]:
        """创建恢复点"""
        try:
            import uuid
            point_id = str(uuid.uuid4())
            created_time = datetime.now()
            
            # 创建恢复点目录
            point_dir = Path(f"recovery/points/{point_id}")
            point_dir.mkdir(parents=True, exist_ok=True)
            
            # 根据恢复类型执行不同的备份操作
            if recovery_type == RecoveryType.SYSTEM_RESTORE:
                size = self._create_system_restore_point(point_dir, point_id)
            elif recovery_type == RecoveryType.FILE_RECOVERY:
                size = self._create_file_recovery_point(point_dir)
            elif recovery_type == RecoveryType.REGISTRY_RESTORE:
                size = self._create_registry_backup(point_dir)
            else:
                size = 0
            
            # 创建恢复点记录
            recovery_point = RecoveryPoint(
                id=point_id,
                name=name,
                description=description,
                recovery_type=recovery_type,
                created_time=created_time,
                size=size,
                location=str(point_dir),
                metadata={
                    'system_info': self._get_system_info(),
                    'backup_locations': self.recovery_config['backup_locations']
                }
            )
            
            self.recovery_points[point_id] = recovery_point
            self._save_recovery_points()
            
            logger.info(f"创建恢复点: {name} (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"创建恢复点失败: {str(e)}")
            return None
    
    def _create_system_restore_point(self, point_dir: Path, point_id: str) -> int:
        """创建系统还原点"""
        total_size = 0
        
        try:
            # 备份关键系统配置
            config_files = []
            
            if platform.system() == "Windows":
                # 备份注册表关键项
                registry_backup = point_dir / "registry_backup.reg"
                try:
                    result = subprocess.run(
                        ['reg', 'export', 'HKLM', str(registry_backup)],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        config_files.append(registry_backup)
                except Exception as e:
                    logger.warning(f"注册表备份失败: {str(e)}")
            
            # 备份系统配置文件
            system_configs = [
                "C:\\Windows\\System32\\drivers\\etc\\hosts",
                "C:\\Windows\\System32\\drivers\\etc\\services"
            ]
            
            for config_file in system_configs:
                if os.path.exists(config_file):
                    try:
                        shutil.copy2(config_file, point_dir)
                        config_files.append(Path(config_file).name)
                    except Exception as e:
                        logger.warning(f"配置文件备份失败 {config_file}: {str(e)}")
            
            # 计算总大小
            for file_path in point_dir.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            # 创建还原点元数据
            metadata = {
                'config_files': [str(f) for f in config_files],
                'system_state': 'healthy',
                'backup_time': datetime.now().isoformat()
            }
            
            with open(point_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return total_size
            
        except Exception as e:
            logger.error(f"创建系统还原点失败: {str(e)}")
            return total_size
    
    def _create_file_recovery_point(self, point_dir: Path) -> int:
        """创建文件恢复点"""
        total_size = 0
        
        try:
            # 备份重要文件
            backup_locations = self.recovery_config['backup_locations']
            
            for location in backup_locations:
                if os.path.exists(location):
                    try:
                        if os.path.isfile(location):
                            # 备份单个文件
                            shutil.copy2(location, point_dir)
                            total_size += os.path.getsize(location)
                        else:
                            # 备份目录
                            for root, dirs, files in os.walk(location):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        # 检查是否在排除列表中
                                        if any(excluded in file_path for excluded in self.recovery_config['excluded_paths']):
                                            continue
                                        
                                        relative_path = os.path.relpath(file_path, location)
                                        dest_path = point_dir / relative_path
                                        
                                        os.makedirs(dest_path.parent, exist_ok=True)
                                        shutil.copy2(file_path, dest_path)
                                        total_size += os.path.getsize(file_path)
                                    
                                    except Exception as e:
                                        logger.warning(f"文件备份失败 {file_path}: {str(e)}")
                    
                    except Exception as e:
                        logger.warning(f"位置备份失败 {location}: {str(e)}")
            
            return total_size
            
        except Exception as e:
            logger.error(f"创建文件恢复点失败: {str(e)}")
            return total_size
    
    def _create_registry_backup(self, point_dir: Path) -> int:
        """创建注册表备份"""
        total_size = 0
        
        try:
            if platform.system() == "Windows":
                # 备份关键注册表项
                registry_keys = [
                    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
                    "HKLM\\SYSTEM\\CurrentControlSet\\Services",
                    "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"
                ]
                
                for key in registry_keys:
                    try:
                        backup_file = point_dir / f"{key.replace('\\', '_')}.reg"
                        result = subprocess.run(
                            ['reg', 'export', key, str(backup_file)],
                            capture_output=True, text=True
                        )
                        
                        if result.returncode == 0 and backup_file.exists():
                            total_size += backup_file.stat().st_size
                    
                    except Exception as e:
                        logger.warning(f"注册表项备份失败 {key}: {str(e)}")
            
            return total_size
            
        except Exception as e:
            logger.error(f"创建注册表备份失败: {str(e)}")
            return total_size
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def perform_recovery(self, recovery_point_id: str, target: str = None) -> bool:
        """执行恢复"""
        if self.is_recovering:
            return False
        
        try:
            if recovery_point_id not in self.recovery_points:
                logger.error(f"恢复点不存在: {recovery_point_id}")
                return False
            
            recovery_point = self.recovery_points[recovery_point_id]
            
            self.is_recovering = True
            
            # 在单独线程中执行恢复
            self.recovery_thread = threading.Thread(
                target=self._recovery_worker,
                args=(recovery_point, target),
                daemon=True
            )
            self.recovery_thread.start()
            
            logger.info(f"开始恢复操作: {recovery_point.name}")
            return True
            
        except Exception as e:
            logger.error(f"启动恢复操作失败: {str(e)}")
            return False
    
    def _recovery_worker(self, recovery_point: RecoveryPoint, target: str):
        """恢复工作线程"""
        try:
            operation_id = f"recovery_{int(time.time())}"
            start_time = datetime.now()
            
            # 创建恢复操作记录
            operation = RecoveryOperation(
                id=operation_id,
                recovery_type=recovery_point.recovery_type,
                target=target or "system",
                description=f"从恢复点 {recovery_point.name} 恢复",
                status=RecoveryStatus.IN_PROGRESS,
                start_time=start_time
            )
            self.recovery_operations.append(operation)
            
            # 执行恢复操作
            success = False
            error_message = None
            
            if recovery_point.recovery_type == RecoveryType.SYSTEM_RESTORE:
                success, error_message = self._perform_system_restore(recovery_point)
            elif recovery_point.recovery_type == RecoveryType.FILE_RECOVERY:
                success, error_message = self._perform_file_recovery(recovery_point, target)
            elif recovery_point.recovery_type == RecoveryType.REGISTRY_RESTORE:
                success, error_message = self._perform_registry_restore(recovery_point)
            
            # 更新操作状态
            operation.end_time = datetime.now()
            operation.status = RecoveryStatus.COMPLETED if success else RecoveryStatus.FAILED
            operation.error_message = error_message
            operation.result = {
                'success': success,
                'recovery_point_id': recovery_point.id,
                'duration_seconds': (operation.end_time - start_time).total_seconds()
            }
            
            if success:
                logger.info(f"恢复操作完成: {recovery_point.name}")
            else:
                logger.error(f"恢复操作失败: {error_message}")
            
            self.is_recovering = False
            
        except Exception as e:
            logger.error(f"恢复工作线程错误: {str(e)}")
            self.is_recovering = False
    
    def _perform_system_restore(self, recovery_point: RecoveryPoint) -> Tuple[bool, Optional[str]]:
        """执行系统恢复"""
        try:
            point_dir = Path(recovery_point.location)
            
            # 恢复注册表配置
            registry_backup = point_dir / "registry_backup.reg"
            if registry_backup.exists():
                try:
                    result = subprocess.run(
                        ['reg', 'import', str(registry_backup)],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return False, f"注册表恢复失败: {result.stderr}"
                except Exception as e:
                    return False, f"注册表恢复异常: {str(e)}"
            
            # 恢复系统配置文件
            for config_file in point_dir.glob("*"):
                if config_file.name != "registry_backup.reg" and config_file.name != "metadata.json":
                    try:
                        original_path = Path("C:\\Windows\\System32\\drivers\\etc") / config_file.name
                        if original_path.exists():
                            shutil.copy2(config_file, original_path)
                    except Exception as e:
                        logger.warning(f"配置文件恢复失败 {config_file}: {str(e)}")
            
            return True, None
            
        except Exception as e:
            return False, f"系统恢复失败: {str(e)}"
    
    def _perform_file_recovery(self, recovery_point: RecoveryPoint, target: str) -> Tuple[bool, Optional[str]]:
        """执行文件恢复"""
        try:
            point_dir = Path(recovery_point.location)
            
            # 恢复文件
            for file_path in point_dir.rglob("*"):
                if file_path.is_file() and file_path.name != "metadata.json":
                    try:
                        # 确定原始路径
                        if target:
                            # 恢复到指定目标
                            dest_path = Path(target) / file_path.relative_to(point_dir)
                        else:
                            # 恢复到原始位置（从元数据中获取）
                            metadata_file = point_dir / "metadata.json"
                            if metadata_file.exists():
                                with open(metadata_file, 'r') as f:
                                    metadata = json.load(f)
                                
                                # 这里需要根据元数据确定原始路径
                                # 简化实现，使用文件名
                                dest_path = Path("C:\\Recovered") / file_path.relative_to(point_dir)
                            else:
                                dest_path = Path("C:\\Recovered") / file_path.relative_to(point_dir)
                        
                        # 创建目标目录并复制文件
                        os.makedirs(dest_path.parent, exist_ok=True)
                        shutil.copy2(file_path, dest_path)
                        
                    except Exception as e:
                        logger.warning(f"文件恢复失败 {file_path}: {str(e)}")
            
            return True, None
            
        except Exception as e:
            return False, f"文件恢复失败: {str(e)}"
    
    def _perform_registry_restore(self, recovery_point: RecoveryPoint) -> Tuple[bool, Optional[str]]:
        """执行注册表恢复"""
        try:
            point_dir = Path(recovery_point.location)
            
            # 恢复注册表备份
            for reg_file in point_dir.glob("*.reg"):
                try:
                    result = subprocess.run(
                        ['reg', 'import', str(reg_file)],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        logger.warning(f"注册表项恢复失败 {reg_file}: {result.stderr}")
                except Exception as e:
                    logger.warning(f"注册表项恢复异常 {reg_file}: {str(e)}")
            
            return True, None
            
        except Exception as e:
            return False, f"注册表恢复失败: {str(e)}"
    
    def get_recovery_points(self) -> List[RecoveryPoint]:
        """获取恢复点列表"""
        return list(self.recovery_points.values())
    
    def get_recovery_operations(self, limit: int = 20) -> List[RecoveryOperation]:
        """获取恢复操作列表"""
        return self.recovery_operations[-limit:] if limit > 0 else self.recovery_operations
    
    def delete_recovery_point(self, point_id: str) -> bool:
        """删除恢复点"""
        try:
            if point_id in self.recovery_points:
                point = self.recovery_points[point_id]
                
                # 删除恢复点文件
                point_dir = Path(point.location)
                if point_dir.exists():
                    shutil.rmtree(point_dir)
                
                # 从内存中移除
                del self.recovery_points[point_id]
                self._save_recovery_points()
                
                logger.info(f"删除恢复点: {point.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"删除恢复点失败: {str(e)}")
            return False
    
    def _save_recovery_points(self):
        """保存恢复点"""
        try:
            recovery_data = {
                'last_updated': datetime.now().isoformat(),
                'recovery_points': [point.to_dict() for point in self.recovery_points.values()]
            }
            
            with open("recovery/recovery_points.json", 'w', encoding='utf-8') as f:
                json.dump(recovery_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"保存恢复点失败: {str(e)}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        total_points = len(self.recovery_points)
        total_operations = len(self.recovery_operations)
        
        type_counts = {}
        for point in self.recovery_points.values():
            point_type = point.recovery_type.value
            type_counts[point_type] = type_counts.get(point_type, 0) + 1
        
        successful_operations = len([op for op in self.recovery_operations if op.status == RecoveryStatus.COMPLETED])
        failed_operations = len([op for op in self.recovery_operations if op.status == RecoveryStatus.FAILED])
        
        total_backup_size = sum(point.size for point in self.recovery_points.values())
        
        return {
            'total_recovery_points': total_points,
            'total_recovery_operations': total_operations,
            'points_by_type': type_counts,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': successful_operations / total_operations if total_operations > 0 else 0,
            'total_backup_size_mb': total_backup_size / (1024 * 1024)
        }
    
    def cancel_recovery(self):
        """取消恢复操作"""
        self.is_recovering = False
        if self.recovery_thread and self.recovery_thread.is_alive():
            self.recovery_thread.join(timeout=5)
        
        logger.info("恢复操作已取消")
    
    def emergency_recovery(self) -> bool:
        """紧急恢复"""
        try:
            # 查找最新的系统恢复点
            system_points = [
                point for point in self.recovery_points.values() 
                if point.recovery_type == RecoveryType.SYSTEM_RESTORE
            ]
            
            if not system_points:
                logger.error("没有可用的系统恢复点")
                return False
            
            # 使用最新的恢复点
            latest_point = max(system_points, key=lambda p: p.created_time)
            
            return self.perform_recovery(latest_point.id)
            
        except Exception as e:
            logger.error(f"紧急恢复失败: {str(e)}")
            return False
    
    def export_recovery_report(self, file_path: str) -> bool:
        """导出恢复报告"""
        try:
            report = {
                'generated_time': datetime.now().isoformat(),
                'statistics': self.get_recovery_statistics(),
                'recovery_points': [point.to_dict() for point in self.get_recovery_points()],
                'recovery_operations': [
                    {
                        'id': op.id,
                        'type': op.recovery_type.value,
                        'target': op.target,
                        'status': op.status.value,
                        'start_time': op.start_time.isoformat(),
                        'end_time': op.end_time.isoformat() if op.end_time else None,
                        'error_message': op.error_message
                    }
                    for op in self.get_recovery_operations(50)
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"恢复报告已导出: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出恢复报告失败: {str(e)}")
            return False

# 单例实例
_recovery_manager_instance = None

def get_recovery_manager() -> RecoveryManager:
    """获取恢复管理器单例"""
    global _recovery_manager_instance
    if _recovery_manager_instance is None:
        _recovery_manager_instance = RecoveryManager()
    return _recovery_manager_instance

