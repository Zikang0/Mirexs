"""
日志轮转模块 - 日志文件轮转管理
负责管理日志文件的轮转、压缩和清理
"""

import logging
import logging.handlers
import gzip
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

class LogRotator:
    """日志轮转管理器"""
    
    def __init__(self, log_base_dir: str = "logs"):
        self.log_base_dir = log_base_dir
        self.rotation_config = self._load_rotation_config()
    
    def _load_rotation_config(self) -> Dict[str, Any]:
        """加载轮转配置"""
        return {
            "system": {
                "max_size_mb": 100,      # 100MB
                "backup_count": 10,      # 保留10个备份
                "compression": True,     # 启用压缩
                "retention_days": 30     # 保留30天
            },
            "security": {
                "max_size_mb": 50,       # 50MB
                "backup_count": 20,      # 保留20个备份（安全日志更重要）
                "compression": True,
                "retention_days": 90     # 保留90天
            },
            "performance": {
                "max_size_mb": 200,      # 200MB（性能日志可能较大）
                "backup_count": 5,
                "compression": True,
                "retention_days": 7      # 只保留7天
            },
            "interaction": {
                "max_size_mb": 500,      # 500MB（交互日志可能很大）
                "backup_count": 5,
                "compression": True,
                "retention_days": 14     # 保留14天
            },
            "error": {
                "max_size_mb": 100,
                "backup_count": 15,
                "compression": True,
                "retention_days": 60     # 保留60天
            },
            "audit": {
                "max_size_mb": 50,
                "backup_count": 30,      # 审计日志需要长期保留
                "compression": True,
                "retention_days": 365    # 保留1年
            }
        }
    
    def setup_log_rotation(self, logger_name: str, log_file: str):
        """为指定日志设置轮转"""
        if logger_name not in self.rotation_config:
            return None
        
        config = self.rotation_config[logger_name]
        
        # 创建轮转处理器
        handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=config["max_size_mb"] * 1024 * 1024,  # 转换为字节
            backupCount=config["backup_count"],
            encoding='utf-8'
        )
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        return handler
    
    def compress_old_logs(self, log_type: str):
        """压缩旧的日志文件"""
        if log_type not in self.rotation_config:
            return
        
        config = self.rotation_config[log_type]
        if not config["compression"]:
            return
        
        log_dir = f"{self.log_base_dir}/{log_type}"
        if not os.path.exists(log_dir):
            return
        
        # 查找需要压缩的日志文件
        for file_name in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file_name)
            
            # 跳过已经是压缩文件和非日志文件
            if file_name.endswith('.gz') or not file_name.endswith('.log'):
                continue
            
            # 跳过当前活动的日志文件
            if file_name == f"{log_type}.log":
                continue
            
            # 检查文件是否是需要压缩的备份文件
            if file_name.startswith(f"{log_type}.log."):
                self._compress_file(file_path)
    
    def _compress_file(self, file_path: str):
        """压缩单个文件"""
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(f"{file_path}.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 压缩成功后删除原文件
            os.remove(file_path)
            print(f"压缩日志文件: {file_path} -> {file_path}.gz")
            
        except Exception as e:
            print(f"压缩文件失败 {file_path}: {e}")
    
    def cleanup_expired_logs(self, log_type: str):
        """清理过期的日志文件"""
        if log_type not in self.rotation_config:
            return
        
        config = self.rotation_config[log_type]
        retention_days = config["retention_days"]
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        log_dir = f"{self.log_base_dir}/{log_type}"
        if not os.path.exists(log_dir):
            return
        
        deleted_files = 0
        for file_name in os.listdir(log_dir):
            file_path = os.path.join(log_dir, file_name)
            
            # 跳过当前活动的日志文件
            if file_name == f"{log_type}.log":
                continue
            
            # 检查文件创建时间
            try:
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff_time:
                    os.remove(file_path)
                    deleted_files += 1
                    print(f"删除过期日志文件: {file_path}")
            except Exception as e:
                print(f"删除文件失败 {file_path}: {e}")
        
        return deleted_files
    
    def perform_daily_maintenance(self):
        """执行每日维护任务"""
        print("开始日志系统每日维护...")
        
        total_deleted = 0
        for log_type in self.rotation_config.keys():
            print(f"处理 {log_type} 日志...")
            
            # 压缩旧日志
            self.compress_old_logs(log_type)
            
            # 清理过期日志
            deleted = self.cleanup_expired_logs(log_type)
            total_deleted += deleted
            
            print(f"  {log_type}: 删除了 {deleted} 个过期文件")
        
        print(f"日志维护完成，总共删除了 {total_deleted} 个文件")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        stats = {}
        total_size = 0
        total_files = 0
        
        for log_type in self.rotation_config.keys():
            log_dir = f"{self.log_base_dir}/{log_type}"
            if not os.path.exists(log_dir):
                stats[log_type] = {"size_mb": 0, "file_count": 0}
                continue
            
            type_size = 0
            type_files = 0
            
            for file_name in os.listdir(log_dir):
                file_path = os.path.join(log_dir, file_name)
                if os.path.isfile(file_path):
                    type_size += os.path.getsize(file_path)
                    type_files += 1
            
            stats[log_type] = {
                "size_mb": round(type_size / 1024 / 1024, 2),
                "file_count": type_files
            }
            
            total_size += type_size
            total_files += type_files
        
        stats["total"] = {
            "size_mb": round(total_size / 1024 / 1024, 2),
            "file_count": total_files
        }
        
        return stats
    
    def backup_logs(self, backup_dir: str, include_types: Optional[List[str]] = None):
        """备份日志文件"""
        import shutil
        from datetime import datetime
        
        if include_types is None:
            include_types = list(self.rotation_config.keys())
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"logs_backup_{timestamp}")
        
        os.makedirs(backup_path, exist_ok=True)
        
        backed_up_files = 0
        for log_type in include_types:
            if log_type not in self.rotation_config:
                continue
            
            source_dir = f"{self.log_base_dir}/{log_type}"
            if not os.path.exists(source_dir):
                continue
            
            dest_dir = os.path.join(backup_path, log_type)
            os.makedirs(dest_dir, exist_ok=True)
            
            # 复制日志文件
            for file_name in os.listdir(source_dir):
                source_file = os.path.join(source_dir, file_name)
                dest_file = os.path.join(dest_dir, file_name)
                
                if os.path.isfile(source_file):
                    shutil.copy2(source_file, dest_file)
                    backed_up_files += 1
        
        # 创建备份信息文件
        backup_info = {
            "timestamp": datetime.now().isoformat(),
            "backup_path": backup_path,
            "included_types": include_types,
            "file_count": backed_up_files,
            "total_size_mb": self._get_directory_size(backup_path) / 1024 / 1024
        }
        
        info_file = os.path.join(backup_path, "backup_info.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        print(f"日志备份完成: {backup_path} ({backed_up_files} 个文件)")
        return backup_path
    
    def _get_directory_size(self, directory: str) -> int:
        """计算目录大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size
    
    def analyze_log_growth(self, days: int = 7) -> Dict[str, Any]:
        """分析日志增长趋势"""
        # 这里可以实现更复杂的日志增长分析
        # 目前返回基本统计信息
        stats = self.get_log_stats()
        
        analysis = {
            "analysis_period": f"最近{days}天",
            "current_stats": stats,
            "recommendations": self._generate_growth_recommendations(stats)
        }
        
        return analysis
    
    def _generate_growth_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """生成日志增长建议"""
        recommendations = []
        total_size = stats["total"]["size_mb"]
        
        if total_size > 1024:  # 超过1GB
            recommendations.append("日志总大小超过1GB，建议检查日志级别和轮转配置")
        
        for log_type, type_stats in stats.items():
            if log_type == "total":
                continue
            
            size_mb = type_stats["size_mb"]
            if size_mb > 500:
                recommendations.append(f"{log_type}日志过大({size_mb}MB)，建议调整轮转策略")
            
            file_count = type_stats["file_count"]
            if file_count > 50:
                recommendations.append(f"{log_type}日志文件过多({file_count}个)，建议清理旧文件")
        
        if not recommendations:
            recommendations.append("日志大小在正常范围内，继续保持当前配置")
        
        return recommendations

# 全局日志轮转实例
log_rotator = LogRotator()

