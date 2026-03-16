"""
备份管理器模块 - 管理用户数据的备份、恢复和版本控制
"""

import logging
import json
import uuid
import os
import shutil
import zipfile
import tempfile
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class BackupType(Enum):
    """备份类型枚举"""
    FULL = "full"  # 完整备份
    INCREMENTAL = "incremental"  # 增量备份
    DIFFERENTIAL = "differential"  # 差异备份
    AUTOMATIC = "automatic"  # 自动备份

class BackupStatus(Enum):
    """备份状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CompressionMethod(Enum):
    """压缩方法枚举"""
    NONE = "none"
    ZIP = "zip"
    GZIP = "gzip"
    LZMA = "lzma"

@dataclass
class BackupMetadata:
    """备份元数据"""
    backup_id: str
    user_id: str
    backup_type: BackupType
    timestamp: datetime
    data_size: int  # 字节
    compressed_size: int  # 字节
    file_count: int
    checksum: str
    encryption_key_hash: str
    compression_method: CompressionMethod
    included_tables: List[str]
    excluded_tables: List[str]
    version: str

@dataclass
class BackupSchedule:
    """备份计划"""
    schedule_id: str
    user_id: str
    backup_type: BackupType
    frequency: str  # daily, weekly, monthly
    time_of_day: str  # HH:MM format
    day_of_week: int  # 0-6 (Monday-Sunday)
    day_of_month: int  # 1-31
    enabled: bool
    retention_days: int
    last_run: Optional[datetime]
    next_run: datetime

@dataclass
class BackupRecord:
    """备份记录"""
    record_id: str
    user_id: str
    backup_id: str
    filename: str
    storage_path: str
    status: BackupStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration: int  # 秒
    error_message: Optional[str]
    verification_hash: Optional[str]

class BackupManager:
    """备份管理器"""
    
    def __init__(self, db_integration, storage_manager, config: Dict[str, Any]):
        """
        初始化备份管理器
        
        Args:
            db_integration: 数据库集成实例
            storage_manager: 存储管理器实例
            config: 配置字典
        """
        self.db = db_integration
        self.storage = storage_manager
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.backup_metadata_table = config.get('backup_metadata_table', 'backup_metadata')
        self.backup_schedules_table = config.get('backup_schedules_table', 'backup_schedules')
        self.backup_records_table = config.get('backup_records_table', 'backup_records')
        
        # 备份配置
        self.backup_storage_path = config.get('backup_storage_path', './backups')
        self.max_backup_size = config.get('max_backup_size', 10 * 1024 * 1024 * 1024)  # 10GB
        self.retention_period = config.get('retention_period', 30)  # 天
        self.encryption_key = self._generate_encryption_key()
        
        # 线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=config.get('backup_workers', 4))
        
        # 创建备份目录
        os.makedirs(self.backup_storage_path, exist_ok=True)
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化备份管理相关表"""
        try:
            # 备份元数据表
            metadata_schema = {
                'backup_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'backup_type': 'VARCHAR(20) NOT NULL',
                'timestamp': 'TIMESTAMP NOT NULL',
                'data_size': 'BIGINT NOT NULL',
                'compressed_size': 'BIGINT NOT NULL',
                'file_count': 'INTEGER NOT NULL',
                'checksum': 'VARCHAR(64) NOT NULL',
                'encryption_key_hash': 'VARCHAR(64) NOT NULL',
                'compression_method': 'VARCHAR(10) NOT NULL',
                'included_tables': 'TEXT NOT NULL',  # JSON格式
                'excluded_tables': 'TEXT NOT NULL',  # JSON格式
                'version': 'VARCHAR(20) NOT NULL'
            }
            
            self.db.create_table(self.backup_metadata_table, metadata_schema)
            
            # 备份计划表
            schedules_schema = {
                'schedule_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'backup_type': 'VARCHAR(20) NOT NULL',
                'frequency': 'VARCHAR(10) NOT NULL',
                'time_of_day': 'VARCHAR(5) NOT NULL',
                'day_of_week': 'INTEGER',
                'day_of_month': 'INTEGER',
                'enabled': 'BOOLEAN DEFAULT TRUE',
                'retention_days': 'INTEGER DEFAULT 30',
                'last_run': 'TIMESTAMP',
                'next_run': 'TIMESTAMP NOT NULL'
            }
            
            self.db.create_table(self.backup_schedules_table, schedules_schema)
            
            # 备份记录表
            records_schema = {
                'record_id': 'SERIAL PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'backup_id': 'VARCHAR(100) NOT NULL',
                'filename': 'VARCHAR(500) NOT NULL',
                'storage_path': 'VARCHAR(1000) NOT NULL',
                'status': 'VARCHAR(20) NOT NULL',
                'start_time': 'TIMESTAMP NOT NULL',
                'end_time': 'TIMESTAMP',
                'duration': 'INTEGER DEFAULT 0',
                'error_message': 'TEXT',
                'verification_hash': 'VARCHAR(64)'
            }
            
            constraints = [
                'FOREIGN KEY (backup_id) REFERENCES backup_metadata(backup_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.backup_records_table, records_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.backup_metadata_table, 'user_id')
            self.db.create_index(self.backup_metadata_table, 'timestamp')
            self.db.create_index(self.backup_metadata_table, 'backup_type')
            self.db.create_index(self.backup_schedules_table, 'user_id')
            self.db.create_index(self.backup_schedules_table, 'enabled')
            self.db.create_index(self.backup_schedules_table, 'next_run')
            self.db.create_index(self.backup_records_table, 'user_id')
            self.db.create_index(self.backup_records_table, 'backup_id')
            self.db.create_index(self.backup_records_table, 'status')
            
            self.logger.info("Backup management tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup management tables: {str(e)}")
            raise
    
    def create_backup(self, user_id: str, backup_type: BackupType = BackupType.FULL,
                     included_tables: List[str] = None, excluded_tables: List[str] = None,
                     compression: CompressionMethod = CompressionMethod.ZIP) -> str:
        """
        创建备份
        
        Args:
            user_id: 用户ID
            backup_type: 备份类型
            included_tables: 包含的表列表
            excluded_tables: 排除的表列表
            compression: 压缩方法
            
        Returns:
            str: 备份ID
        """
        try:
            backup_id = str(uuid.uuid4())
            start_time = datetime.now()
            
            # 创建备份记录
            record_id = self._create_backup_record(user_id, backup_id, BackupStatus.IN_PROGRESS, start_time)
            
            # 执行备份
            backup_success = self._perform_backup(
                user_id, backup_id, backup_type, included_tables, 
                excluded_tables, compression, record_id
            )
            
            if backup_success:
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds())
                
                # 更新备份记录状态
                self._update_backup_record(record_id, BackupStatus.COMPLETED, end_time, duration)
                
                self.logger.info(f"Backup completed: {backup_id} for user {user_id}")
                return backup_id
            else:
                # 更新备份记录状态为失败
                self._update_backup_record(record_id, BackupStatus.FAILED, datetime.now(), 0, "Backup operation failed")
                self.logger.error(f"Backup failed: {backup_id} for user {user_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return None
    
    def _perform_backup(self, user_id: str, backup_id: str, backup_type: BackupType,
                       included_tables: List[str], excluded_tables: List[str],
                       compression: CompressionMethod, record_id: str) -> bool:
        """
        执行备份操作
        
        Args:
            user_id: 用户ID
            backup_id: 备份ID
            backup_type: 备份类型
            included_tables: 包含的表列表
            excluded_tables: 排除的表列表
            compression: 压缩方法
            record_id: 记录ID
            
        Returns:
            bool: 备份是否成功
        """
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            backup_dir = os.path.join(temp_dir, backup_id)
            os.makedirs(backup_dir)
            
            # 导出用户数据
            data_files = self._export_user_data(user_id, backup_dir, included_tables, excluded_tables)
            
            if not data_files:
                self.logger.error(f"No data to backup for user {user_id}")
                return False
            
            # 计算数据大小和校验和
            total_size = sum(os.path.getsize(f) for f in data_files)
            checksum = self._calculate_checksum(data_files)
            
            # 压缩备份文件
            backup_filename = f"{backup_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
            backup_path = os.path.join(self.backup_storage_path, backup_filename)
            
            compressed_size = self._compress_backup(backup_dir, backup_path, compression)
            
            # 加密备份文件
            encrypted_size = self._encrypt_backup(backup_path)
            
            # 创建备份元数据
            metadata = BackupMetadata(
                backup_id=backup_id,
                user_id=user_id,
                backup_type=backup_type,
                timestamp=datetime.now(),
                data_size=total_size,
                compressed_size=compressed_size,
                file_count=len(data_files),
                checksum=checksum,
                encryption_key_hash=self._hash_encryption_key(),
                compression_method=compression,
                included_tables=included_tables or [],
                excluded_tables=excluded_tables or [],
                version="1.0"
            )
            
            # 保存元数据到数据库
            self._save_backup_metadata(metadata)
            
            # 更新备份记录文件信息
            self._update_backup_record_file(record_id, backup_filename, backup_path)
            
            # 验证备份文件
            verification_hash = self._verify_backup(backup_path)
            if verification_hash:
                self._update_backup_record_verification(record_id, verification_hash)
            else:
                self.logger.warning(f"Backup verification failed: {backup_id}")
            
            # 清理临时文件
            shutil.rmtree(temp_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error during backup operation: {str(e)}")
            # 清理临时文件
            try:
                if 'temp_dir' in locals():
                    shutil.rmtree(temp_dir)
            except:
                pass
            return False
    
    def restore_backup(self, user_id: str, backup_id: str, target_tables: List[str] = None) -> bool:
        """
        恢复备份
        
        Args:
            user_id: 用户ID
            backup_id: 备份ID
            target_tables: 要恢复的表列表（为空则恢复所有）
            
        Returns:
            bool: 恢复是否成功
        """
        try:
            # 获取备份元数据
            metadata = self._get_backup_metadata(backup_id)
            if not metadata or metadata.user_id != user_id:
                self.logger.error(f"Backup not found or access denied: {backup_id}")
                return False
            
            # 获取备份记录
            backup_record = self._get_backup_record_by_backup_id(backup_id)
            if not backup_record:
                self.logger.error(f"Backup record not found: {backup_id}")
                return False
            
            backup_path = backup_record['storage_path']
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            start_time = datetime.now()
            
            # 解密备份文件
            decrypted_path = self._decrypt_backup(backup_path)
            if not decrypted_path:
                self.logger.error(f"Failed to decrypt backup: {backup_path}")
                return False
            
            # 解压备份文件
            extract_dir = self._extract_backup(decrypted_path)
            if not extract_dir:
                self.logger.error(f"Failed to extract backup: {decrypted_path}")
                return False
            
            # 导入数据
            restore_success = self._import_user_data(user_id, extract_dir, target_tables)
            
            # 清理临时文件
            try:
                if os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary files: {str(e)}")
            
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds())
            
            if restore_success:
                self.logger.info(f"Backup restored successfully: {backup_id} for user {user_id}")
                # 记录恢复操作
                self._log_restore_operation(user_id, backup_id, True, duration)
                return True
            else:
                self.logger.error(f"Backup restore failed: {backup_id} for user {user_id}")
                # 记录恢复操作
                self._log_restore_operation(user_id, backup_id, False, duration)
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {str(e)}")
            return False
    
    def create_backup_schedule(self, user_id: str, backup_type: BackupType, 
                              frequency: str, time_of_day: str, 
                              retention_days: int = 30, 
                              day_of_week: int = None, 
                              day_of_month: int = None) -> str:
        """
        创建备份计划
        
        Args:
            user_id: 用户ID
            backup_type: 备份类型
            frequency: 频率 (daily, weekly, monthly)
            time_of_day: 时间 (HH:MM)
            retention_days: 保留天数
            day_of_week: 星期几 (0-6, 仅weekly需要)
            day_of_month: 几号 (1-31, 仅monthly需要)
            
        Returns:
            str: 计划ID
        """
        try:
            schedule_id = str(uuid.uuid4())
            
            # 计算下次运行时间
            next_run = self._calculate_next_run(frequency, time_of_day, day_of_week, day_of_month)
            
            schedule = BackupSchedule(
                schedule_id=schedule_id,
                user_id=user_id,
                backup_type=backup_type,
                frequency=frequency,
                time_of_day=time_of_day,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                enabled=True,
                retention_days=retention_days,
                last_run=None,
                next_run=next_run
            )
            
            # 保存到数据库
            schedule_data = {
                'schedule_id': schedule.schedule_id,
                'user_id': schedule.user_id,
                'backup_type': schedule.backup_type.value,
                'frequency': schedule.frequency,
                'time_of_day': schedule.time_of_day,
                'day_of_week': schedule.day_of_week,
                'day_of_month': schedule.day_of_month,
                'enabled': schedule.enabled,
                'retention_days': schedule.retention_days,
                'last_run': schedule.last_run,
                'next_run': schedule.next_run
            }
            
            self.db.execute_insert(self.backup_schedules_table, schedule_data)
            
            self.logger.info(f"Backup schedule created: {schedule_id} for user {user_id}")
            return schedule_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup schedule: {str(e)}")
            return None
    
    def execute_scheduled_backups(self) -> Dict[str, Any]:
        """
        执行计划备份
        
        Returns:
            Dict: 执行结果
        """
        try:
            current_time = datetime.now()
            
            # 查询到期的备份计划
            query = f"""
            SELECT * FROM {self.backup_schedules_table} 
            WHERE enabled = TRUE AND next_run <= %s
            """
            schedules = self.db.execute_query(query, (current_time,))
            
            results = {
                'total_schedules': len(schedules),
                'executed': 0,
                'failed': 0,
                'details': []
            }
            
            for schedule in schedules:
                try:
                    # 执行备份
                    backup_id = self.create_backup(
                        user_id=schedule['user_id'],
                        backup_type=BackupType(schedule['backup_type']),
                        compression=CompressionMethod.ZIP
                    )
                    
                    if backup_id:
                        # 更新计划的下次运行时间
                        next_run = self._calculate_next_run(
                            schedule['frequency'],
                            schedule['time_of_day'],
                            schedule['day_of_week'],
                            schedule['day_of_month']
                        )
                        
                        update_data = {
                            'last_run': current_time,
                            'next_run': next_run
                        }
                        
                        self.db.execute_update(
                            self.backup_schedules_table,
                            update_data,
                            "schedule_id = %s",
                            (schedule['schedule_id'],)
                        )
                        
                        results['executed'] += 1
                        results['details'].append({
                            'schedule_id': schedule['schedule_id'],
                            'user_id': schedule['user_id'],
                            'status': 'success',
                            'backup_id': backup_id
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'schedule_id': schedule['schedule_id'],
                            'user_id': schedule['user_id'],
                            'status': 'failed',
                            'error': 'Backup creation failed'
                        })
                        
                except Exception as e:
                    results['failed'] += 1
                    results['details'].append({
                        'schedule_id': schedule['schedule_id'],
                        'user_id': schedule['user_id'],
                        'status': 'error',
                        'error': str(e)
                    })
                    self.logger.error(f"Error executing backup schedule {schedule['schedule_id']}: {str(e)}")
            
            self.logger.info(f"Scheduled backups executed: {results['executed']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to execute scheduled backups: {str(e)}")
            return {'error': str(e)}
    
    def get_backup_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取备份历史
        
        Args:
            user_id: 用户ID
            limit: 返回记录限制
            
        Returns:
            List[Dict]: 备份历史
        """
        try:
            query = f"""
            SELECT m.*, r.filename, r.status, r.start_time, r.end_time, r.duration
            FROM {self.backup_metadata_table} m
            JOIN {self.backup_records_table} r ON m.backup_id = r.backup_id
            WHERE m.user_id = %s
            ORDER BY m.timestamp DESC
            LIMIT %s
            """
            
            results = self.db.execute_query(query, (user_id, limit))
            
            history = []
            for row in results:
                history.append({
                    'backup_id': row['backup_id'],
                    'backup_type': row['backup_type'],
                    'timestamp': row['timestamp'],
                    'data_size': row['data_size'],
                    'compressed_size': row['compressed_size'],
                    'file_count': row['file_count'],
                    'filename': row['filename'],
                    'status': row['status'],
                    'duration': row['duration'],
                    'compression_method': row['compression_method']
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get backup history: {str(e)}")
            return []
    
    def cleanup_old_backups(self, user_id: str = None) -> Dict[str, Any]:
        """
        清理旧备份
        
        Args:
            user_id: 用户ID（为空则清理所有用户）
            
        Returns:
            Dict: 清理结果
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=self.retention_period)
            
            # 查询过期的备份
            if user_id:
                query = f"""
                SELECT m.backup_id, r.filename, r.storage_path
                FROM {self.backup_metadata_table} m
                JOIN {self.backup_records_table} r ON m.backup_id = r.backup_id
                WHERE m.user_id = %s AND m.timestamp < %s
                """
                params = (user_id, cutoff_time)
            else:
                query = f"""
                SELECT m.backup_id, r.filename, r.storage_path
                FROM {self.backup_metadata_table} m
                JOIN {self.backup_records_table} r ON m.backup_id = r.backup_id
                WHERE m.timestamp < %s
                """
                params = (cutoff_time,)
            
            old_backups = self.db.execute_query(query, params)
            
            cleanup_results = {
                'total_found': len(old_backups),
                'deleted_files': 0,
                'deleted_records': 0,
                'errors': 0,
                'details': []
            }
            
            for backup in old_backups:
                try:
                    # 删除备份文件
                    if os.path.exists(backup['storage_path']):
                        os.remove(backup['storage_path'])
                        cleanup_results['deleted_files'] += 1
                    
                    # 删除数据库记录
                    # 由于外键约束，删除备份元数据会自动删除相关记录
                    delete_query = f"DELETE FROM {self.backup_metadata_table} WHERE backup_id = %s"
                    affected = self.db.execute_update(
                        self.backup_metadata_table,
                        {},
                        "backup_id = %s",
                        (backup['backup_id'],)
                    )
                    
                    if affected > 0:
                        cleanup_results['deleted_records'] += 1
                        cleanup_results['details'].append({
                            'backup_id': backup['backup_id'],
                            'status': 'success'
                        })
                    else:
                        cleanup_results['errors'] += 1
                        cleanup_results['details'].append({
                            'backup_id': backup['backup_id'],
                            'status': 'error',
                            'error': 'Failed to delete database record'
                        })
                        
                except Exception as e:
                    cleanup_results['errors'] += 1
                    cleanup_results['details'].append({
                        'backup_id': backup['backup_id'],
                        'status': 'error',
                        'error': str(e)
                    })
                    self.logger.error(f"Error cleaning up backup {backup['backup_id']}: {str(e)}")
            
            self.logger.info(f"Backup cleanup completed: {cleanup_results['deleted_files']} files deleted, {cleanup_results['errors']} errors")
            return cleanup_results
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {str(e)}")
            return {'error': str(e)}
    
    def verify_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """
        验证备份完整性
        
        Args:
            backup_id: 备份ID
            
        Returns:
            Dict: 验证结果
        """
        try:
            # 获取备份记录
            backup_record = self._get_backup_record_by_backup_id(backup_id)
            if not backup_record:
                return {'error': 'Backup record not found'}
            
            backup_path = backup_record['storage_path']
            if not os.path.exists(backup_path):
                return {'error': 'Backup file not found'}
            
            # 验证文件完整性
            current_hash = self._calculate_file_hash(backup_path)
            stored_hash = backup_record['verification_hash']
            
            integrity_check = current_hash == stored_hash if stored_hash else False
            
            # 验证元数据一致性
            metadata = self._get_backup_metadata(backup_id)
            metadata_consistent = metadata is not None
            
            # 尝试解密和解压（基本验证）
            decrypted_path = None
            extract_dir = None
            operational_check = False
            
            try:
                decrypted_path = self._decrypt_backup(backup_path)
                if decrypted_path:
                    extract_dir = self._extract_backup(decrypted_path)
                    operational_check = extract_dir is not None
            except Exception as e:
                self.logger.warning(f"Operational check failed for backup {backup_id}: {str(e)}")
            finally:
                # 清理临时文件
                if decrypted_path and os.path.exists(decrypted_path):
                    os.remove(decrypted_path)
                if extract_dir and os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
            
            result = {
                'backup_id': backup_id,
                'file_exists': True,
                'file_integrity': integrity_check,
                'metadata_consistent': metadata_consistent,
                'operational': operational_check,
                'overall_status': 'healthy' if (integrity_check and metadata_consistent and operational_check) else 'degraded',
                'verification_time': datetime.now().isoformat()
            }
            
            if not integrity_check:
                result['issues'] = ['File integrity check failed']
            if not metadata_consistent:
                result['issues'] = result.get('issues', []) + ['Metadata inconsistency']
            if not operational_check:
                result['issues'] = result.get('issues', []) + ['Operational check failed']
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup integrity: {str(e)}")
            return {'error': str(e)}
    
    def _export_user_data(self, user_id: str, export_dir: str, 
                         included_tables: List[str], excluded_tables: List[str]) -> List[str]:
        """导出用户数据到文件"""
        try:
            # 获取用户相关的表
            user_tables = self._get_user_related_tables(user_id)
            
            # 应用包含/排除过滤器
            if included_tables:
                user_tables = [table for table in user_tables if table in included_tables]
            if excluded_tables:
                user_tables = [table for table in user_tables if table not in excluded_tables]
            
            exported_files = []
            
            for table_name in user_tables:
                try:
                    # 查询表数据
                    query = f"SELECT * FROM {table_name} WHERE user_id = %s"
                    results = self.db.execute_query(query, (user_id,))
                    
                    if results:
                        # 保存为JSON文件
                        filename = os.path.join(export_dir, f"{table_name}.json")
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
                        
                        exported_files.append(filename)
                        self.logger.debug(f"Exported table {table_name}: {len(results)} records")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to export table {table_name}: {str(e)}")
                    continue
            
            return exported_files
            
        except Exception as e:
            self.logger.error(f"Failed to export user data: {str(e)}")
            return []
    
    def _import_user_data(self, user_id: str, import_dir: str, target_tables: List[str]) -> bool:
        """从文件导入用户数据"""
        try:
            # 获取导入目录中的所有JSON文件
            json_files = [f for f in os.listdir(import_dir) if f.endswith('.json')]
            
            for json_file in json_files:
                table_name = json_file.replace('.json', '')
                
                # 应用目标表过滤器
                if target_tables and table_name not in target_tables:
                    continue
                
                try:
                    file_path = os.path.join(import_dir, json_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if not data:
                        continue
                    
                    # 清空现有数据（谨慎操作，实际项目中可能需要更复杂的合并逻辑）
                    delete_query = f"DELETE FROM {table_name} WHERE user_id = %s"
                    self.db.execute_update(
                        table_name,
                        {},
                        "user_id = %s",
                        (user_id,)
                    )
                    
                    # 插入新数据
                    for record in data:
                        # 确保user_id匹配
                        record['user_id'] = user_id
                        self.db.execute_insert(table_name, record)
                    
                    self.logger.debug(f"Imported table {table_name}: {len(data)} records")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to import table {table_name}: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import user data: {str(e)}")
            return False
    
    def _compress_backup(self, source_dir: str, target_path: str, 
                        compression: CompressionMethod) -> int:
        """压缩备份目录"""
        try:
            if compression == CompressionMethod.ZIP:
                with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source_dir)
                            zipf.write(file_path, arcname)
                
                compressed_size = os.path.getsize(target_path)
                return compressed_size
                
            else:
                # 对于其他压缩方法，这里可以实现相应的逻辑
                # 目前只实现ZIP压缩
                shutil.make_archive(target_path.replace('.backup', ''), 'zip', source_dir)
                compressed_size = os.path.getsize(target_path + '.zip')
                os.rename(target_path + '.zip', target_path)
                return compressed_size
                
        except Exception as e:
            self.logger.error(f"Failed to compress backup: {str(e)}")
            raise
    
    def _encrypt_backup(self, file_path: str) -> int:
        """加密备份文件"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(data)
            
            encrypted_path = file_path + '.encrypted'
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            encrypted_size = os.path.getsize(encrypted_path)
            os.rename(encrypted_path, file_path)
            
            return encrypted_size
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt backup: {str(e)}")
            raise
    
    def _decrypt_backup(self, file_path: str) -> Optional[str]:
        """解密备份文件"""
        try:
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
            
            fernet = Fernet(self.encryption_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            decrypted_path = file_path + '.decrypted'
            with open(decrypted_path, 'wb') as f:
                f.write(decrypted_data)
            
            return decrypted_path
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt backup: {str(e)}")
            return None
    
    def _extract_backup(self, file_path: str) -> Optional[str]:
        """解压备份文件"""
        try:
            extract_dir = tempfile.mkdtemp()
            
            if file_path.endswith('.zip') or file_path.endswith('.backup'):
                with zipfile.ZipFile(file_path, 'r') as zipf:
                    zipf.extractall(extract_dir)
            else:
                # 处理其他压缩格式
                shutil.unpack_archive(file_path, extract_dir)
            
            return extract_dir
            
        except Exception as e:
            self.logger.error(f"Failed to extract backup: {str(e)}")
            return None
    
    def _calculate_checksum(self, files: List[str]) -> str:
        """计算文件列表的校验和"""
        hasher = hashlib.sha256()
        
        for file_path in sorted(files):
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算单个文件的哈希值"""
        hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _verify_backup(self, file_path: str) -> Optional[str]:
        """验证备份文件"""
        try:
            return self._calculate_file_hash(file_path)
        except Exception as e:
            self.logger.error(f"Failed to verify backup: {str(e)}")
            return None
    
    def _generate_encryption_key(self) -> bytes:
        """生成加密密钥"""
        # 在实际项目中，应该从安全的密钥存储中获取
        # 这里使用固定密钥用于演示
        key = b'mirexs_backup_encryption_key_2024!'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'mirexs_backup_salt',
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key))
    
    def _hash_encryption_key(self) -> str:
        """哈希加密密钥"""
        return hashlib.sha256(self.encryption_key).hexdigest()
    
    def _get_user_related_tables(self, user_id: str) -> List[str]:
        """获取与用户相关的表名"""
        # 这里应该从数据库元数据中获取实际的表名
        # 简化实现，返回已知的用户相关表
        return [
            'user_profiles', 'user_preferences', 'user_customization',
            'user_documents', 'user_conversations', 'learning_progress',
            'learning_sessions', 'skill_assessments', 'interaction_history'
        ]
    
    def _calculate_next_run(self, frequency: str, time_of_day: str, 
                           day_of_week: int, day_of_month: int) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()
        hour, minute = map(int, time_of_day.split(':'))
        
        if frequency == 'daily':
            next_run = datetime(now.year, now.month, now.day, hour, minute)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif frequency == 'weekly':
            # 找到下一个指定的星期几
            current_weekday = now.weekday()
            days_ahead = (day_of_week - current_weekday) % 7
            if days_ahead == 0 and (now.hour > hour or (now.hour == hour and now.minute >= minute)):
                days_ahead = 7
            next_run = datetime(now.year, now.month, now.day, hour, minute) + timedelta(days=days_ahead)
            
        elif frequency == 'monthly':
            # 找到下一个指定的日期
            next_month = now.month + 1 if now.day >= day_of_month else now.month
            next_year = now.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            
            try:
                next_run = datetime(next_year, next_month, day_of_month, hour, minute)
            except ValueError:
                # 如果日期无效（如2月30日），使用当月最后一天
                next_run = datetime(next_year, next_month, 1, hour, minute)
                while True:
                    try:
                        next_run = next_run.replace(day=next_run.day)
                        next_run += timedelta(days=1)
                    except ValueError:
                        next_run -= timedelta(days=1)
                        break
        
        return next_run
    
    def _create_backup_record(self, user_id: str, backup_id: str, 
                             status: BackupStatus, start_time: datetime) -> str:
        """创建备份记录"""
        record_id = str(uuid.uuid4())
        
        record_data = {
            'record_id': record_id,
            'user_id': user_id,
            'backup_id': backup_id,
            'filename': '',  # 稍后更新
            'storage_path': '',  # 稍后更新
            'status': status.value,
            'start_time': start_time,
            'end_time': None,
            'duration': 0,
            'error_message': None,
            'verification_hash': None
        }
        
        self.db.execute_insert(self.backup_records_table, record_data)
        return record_id
    
    def _update_backup_record(self, record_id: str, status: BackupStatus, 
                             end_time: datetime, duration: int, 
                             error_message: str = None):
        """更新备份记录"""
        update_data = {
            'status': status.value,
            'end_time': end_time,
            'duration': duration,
            'error_message': error_message
        }
        
        self.db.execute_update(
            self.backup_records_table,
            update_data,
            "record_id = %s",
            (record_id,)
        )
    
    def _update_backup_record_file(self, record_id: str, filename: str, storage_path: str):
        """更新备份记录的文件信息"""
        update_data = {
            'filename': filename,
            'storage_path': storage_path
        }
        
        self.db.execute_update(
            self.backup_records_table,
            update_data,
            "record_id = %s",
            (record_id,)
        )
    
    def _update_backup_record_verification(self, record_id: str, verification_hash: str):
        """更新备份记录的验证哈希"""
        update_data = {
            'verification_hash': verification_hash
        }
        
        self.db.execute_update(
            self.backup_records_table,
            update_data,
            "record_id = %s",
            (record_id,)
        )
    
    def _save_backup_metadata(self, metadata: BackupMetadata):
        """保存备份元数据"""
        metadata_data = {
            'backup_id': metadata.backup_id,
            'user_id': metadata.user_id,
            'backup_type': metadata.backup_type.value,
            'timestamp': metadata.timestamp,
            'data_size': metadata.data_size,
            'compressed_size': metadata.compressed_size,
            'file_count': metadata.file_count,
            'checksum': metadata.checksum,
            'encryption_key_hash': metadata.encryption_key_hash,
            'compression_method': metadata.compression_method.value,
            'included_tables': json.dumps(metadata.included_tables),
            'excluded_tables': json.dumps(metadata.excluded_tables),
            'version': metadata.version
        }
        
        self.db.execute_insert(self.backup_metadata_table, metadata_data)
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """获取备份元数据"""
        query = f"SELECT * FROM {self.backup_metadata_table} WHERE backup_id = %s"
        results = self.db.execute_query(query, (backup_id,))
        
        if not results:
            return None
        
        row = results[0]
        return BackupMetadata(
            backup_id=row['backup_id'],
            user_id=row['user_id'],
            backup_type=BackupType(row['backup_type']),
            timestamp=row['timestamp'],
            data_size=row['data_size'],
            compressed_size=row['compressed_size'],
            file_count=row['file_count'],
            checksum=row['checksum'],
            encryption_key_hash=row['encryption_key_hash'],
            compression_method=CompressionMethod(row['compression_method']),
            included_tables=json.loads(row['included_tables']),
            excluded_tables=json.loads(row['excluded_tables']),
            version=row['version']
        )
    
    def _get_backup_record_by_backup_id(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """根据备份ID获取备份记录"""
        query = f"SELECT * FROM {self.backup_records_table} WHERE backup_id = %s"
        results = self.db.execute_query(query, (backup_id,))
        
        if not results:
            return None
        
        return results[0]
    
    def _log_restore_operation(self, user_id: str, backup_id: str, 
                              success: bool, duration: int):
        """记录恢复操作"""
        # 在实际项目中，应该将恢复操作记录到专门的审计日志表
        self.logger.info(f"Restore operation: user={user_id}, backup={backup_id}, "
                        f"success={success}, duration={duration}s")

