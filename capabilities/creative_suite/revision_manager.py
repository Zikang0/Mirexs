"""
修订管理器：管理内容修订历史
支持版本控制、变更追踪、协作编辑等功能
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RevisionAction(Enum):
    """修订动作枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    MERGE = "merge"

class RevisionStatus(Enum):
    """修订状态枚举"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"

class Revision(BaseModel):
    """修订记录"""
    revision_id: str
    content_id: str
    version: int
    content: str
    action: RevisionAction
    author: str
    timestamp: datetime
    changes: List[Dict[str, Any]]
    status: RevisionStatus
    comments: List[str]
    metadata: Dict[str, Any]

class RevisionConfig(BaseModel):
    """修订配置"""
    auto_save: bool = True
    max_versions: int = 100
    backup_interval: int = 3600  # 秒
    collaboration_enabled: bool = False

class RevisionManager:
    """修订管理器"""
    
    def __init__(self, db_path: str = "revisions.db"):
        self.db_path = db_path
        self.config = RevisionConfig()
        self._initialize_database()
        
        logger.info("RevisionManager initialized")
    
    def _initialize_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建修订表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    action TEXT NOT NULL,
                    author TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    changes TEXT NOT NULL,
                    status TEXT NOT NULL,
                    comments TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_content_id 
                ON revisions(content_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON revisions(timestamp)
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Revision database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize revision database: {e}")
            raise
    
    def _generate_revision_id(self, content_id: str, version: int) -> str:
        """生成修订ID"""
        unique_string = f"{content_id}_{version}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def create_revision(self, 
                       content_id: str,
                       content: str,
                       author: str,
                       action: RevisionAction = RevisionAction.CREATE,
                       changes: Optional[List[Dict]] = None,
                       comments: Optional[List[str]] = None,
                       metadata: Optional[Dict] = None) -> Revision:
        """
        创建修订记录
        
        Args:
            content_id: 内容ID
            content: 内容
            author: 作者
            action: 修订动作
            changes: 变更列表
            comments: 评论列表
            metadata: 元数据
            
        Returns:
            Revision: 修订记录
        """
        try:
            # 获取下一个版本号
            next_version = self._get_next_version(content_id)
            
            # 生成修订ID
            revision_id = self._generate_revision_id(content_id, next_version)
            
            # 创建修订记录
            revision = Revision(
                revision_id=revision_id,
                content_id=content_id,
                version=next_version,
                content=content,
                action=action,
                author=author,
                timestamp=datetime.now(),
                changes=changes or [],
                status=RevisionStatus.DRAFT,
                comments=comments or [],
                metadata=metadata or {}
            )
            
            # 保存到数据库
            self._save_revision_to_db(revision)
            
            # 检查版本数量限制
            self._enforce_version_limit(content_id)
            
            logger.info(f"Created revision {revision_id} for content {content_id}")
            return revision
            
        except Exception as e:
            logger.error(f"Failed to create revision: {e}")
            raise
    
    def _get_next_version(self, content_id: str) -> int:
        """获取下一个版本号"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT MAX(version) FROM revisions WHERE content_id = ?",
                (content_id,)
            )
            
            result = cursor.fetchone()
            current_version = result[0] if result[0] is not None else 0
            
            conn.close()
            return current_version + 1
            
        except Exception as e:
            logger.error(f"Failed to get next version: {e}")
            return 1
    
    def _save_revision_to_db(self, revision: Revision):
        """保存修订记录到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO revisions 
                (revision_id, content_id, version, content, action, author, 
                 timestamp, changes, status, comments, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                revision.revision_id,
                revision.content_id,
                revision.version,
                revision.content,
                revision.action.value,
                revision.author,
                revision.timestamp.isoformat(),
                json.dumps(revision.changes, ensure_ascii=False),
                revision.status.value,
                json.dumps(revision.comments, ensure_ascii=False),
                json.dumps(revision.metadata, ensure_ascii=False)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save revision to database: {e}")
            raise
    
    def get_revision(self, revision_id: str) -> Optional[Revision]:
        """获取修订记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM revisions WHERE revision_id = ?",
                (revision_id,)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_revision(row)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get revision: {e}")
            return None
    
    def _row_to_revision(self, row) -> Revision:
        """将数据库行转换为修订对象"""
        return Revision(
            revision_id=row[0],
            content_id=row[1],
            version=row[2],
            content=row[3],
            action=RevisionAction(row[4]),
            author=row[5],
            timestamp=datetime.fromisoformat(row[6]),
            changes=json.loads(row[7]),
            status=RevisionStatus(row[8]),
            comments=json.loads(row[9]),
            metadata=json.loads(row[10])
        )
    
    def get_content_revisions(self, content_id: str) -> List[Revision]:
        """获取内容的所有修订记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM revisions WHERE content_id = ? ORDER BY version DESC",
                (content_id,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_revision(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get content revisions: {e}")
            return []
    
    def get_latest_revision(self, content_id: str) -> Optional[Revision]:
        """获取最新修订记录"""
        revisions = self.get_content_revisions(content_id)
        return revisions[0] if revisions else None
    
    def update_revision_status(self, 
                             revision_id: str, 
                             status: RevisionStatus,
                             comment: Optional[str] = None) -> bool:
        """
        更新修订状态
        
        Args:
            revision_id: 修订ID
            status: 新状态
            comment: 状态变更评论
            
        Returns:
            bool: 是否成功
        """
        try:
            revision = self.get_revision(revision_id)
            if not revision:
                return False
            
            # 更新状态
            revision.status = status
            
            # 添加评论
            if comment:
                revision.comments.append(f"状态变更为 {status.value}: {comment}")
            
            # 更新数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE revisions 
                SET status = ?, comments = ?
                WHERE revision_id = ?
            ''', (
                status.value,
                json.dumps(revision.comments, ensure_ascii=False),
                revision_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated revision {revision_id} status to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update revision status: {e}")
            return False
    
    def compare_revisions(self, revision_id1: str, revision_id2: str) -> Dict[str, Any]:
        """
        比较两个修订版本
        
        Args:
            revision_id1: 第一个修订ID
            revision_id2: 第二个修订ID
            
        Returns:
            Dict: 比较结果
        """
        try:
            rev1 = self.get_revision(revision_id1)
            rev2 = self.get_revision(revision_id2)
            
            if not rev1 or not rev2:
                raise ValueError("One or both revisions not found")
            
            if rev1.content_id != rev2.content_id:
                raise ValueError("Revisions are for different content")
            
            # 简单的基于行的比较
            lines1 = rev1.content.split('\n')
            lines2 = rev2.content.split('\n')
            
            added = []
            removed = []
            modified = []
            
            # 找出新增和删除的行
            for i, line in enumerate(lines2):
                if i >= len(lines1) or lines1[i] != line:
                    if i < len(lines1):
                        modified.append({
                            "position": i,
                            "old": lines1[i],
                            "new": line
                        })
                    else:
                        added.append({
                            "position": i,
                            "content": line
                        })
            
            for i, line in enumerate(lines1):
                if i >= len(lines2):
                    removed.append({
                        "position": i,
                        "content": line
                    })
            
            return {
                "revision1": revision_id1,
                "revision2": revision_id2,
                "added_lines": added,
                "removed_lines": removed,
                "modified_lines": modified,
                "total_changes": len(added) + len(removed) + len(modified)
            }
            
        except Exception as e:
            logger.error(f"Failed to compare revisions: {e}")
            return {"error": str(e)}
    
    def restore_revision(self, revision_id: str, author: str) -> Optional[Revision]:
        """
        恢复到指定修订版本
        
        Args:
            revision_id: 要恢复的修订ID
            author: 执行恢复的作者
            
        Returns:
            Revision: 新的修订记录
        """
        try:
            target_revision = self.get_revision(revision_id)
            if not target_revision:
                return None
            
            # 创建恢复修订
            restored_revision = self.create_revision(
                content_id=target_revision.content_id,
                content=target_revision.content,
                author=author,
                action=RevisionAction.RESTORE,
                changes=[{
                    "type": "restore",
                    "from_revision": revision_id,
                    "to_version": target_revision.version
                }],
                comments=[f"恢复到版本 {target_revision.version}"],
                metadata={"restored_from": revision_id}
            )
            
            logger.info(f"Restored content {target_revision.content_id} to revision {revision_id}")
            return restored_revision
            
        except Exception as e:
            logger.error(f"Failed to restore revision: {e}")
            return None
    
    def merge_revisions(self, 
                       base_revision_id: str, 
                       their_revision_id: str,
                       author: str) -> Optional[Revision]:
        """
        合并两个修订版本
        
        Args:
            base_revision_id: 基础修订ID
            their_revision_id: 要合并的修订ID
            author: 执行合并的作者
            
        Returns:
            Revision: 合并后的修订记录
        """
        try:
            base_rev = self.get_revision(base_revision_id)
            their_rev = self.get_revision(their_revision_id)
            
            if not base_rev or not their_rev:
                return None
            
            if base_rev.content_id != their_rev.content_id:
                raise ValueError("Cannot merge revisions for different content")
            
            # 简单的合并策略：以their_rev为基础，应用base_rev的冲突解决
            # 在实际应用中应该实现更复杂的合并算法
            merged_content = their_rev.content
            
            # 记录合并信息
            changes = [{
                "type": "merge",
                "base_revision": base_revision_id,
                "their_revision": their_revision_id,
                "strategy": "theirs_with_conflict_resolution"
            }]
            
            merged_revision = self.create_revision(
                content_id=base_rev.content_id,
                content=merged_content,
                author=author,
                action=RevisionAction.MERGE,
                changes=changes,
                comments=[f"合并版本 {base_rev.version} 和 {their_rev.version}"],
                metadata={
                    "merged_from": [base_revision_id, their_revision_id],
                    "merge_timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Merged revisions {base_revision_id} and {their_revision_id}")
            return merged_revision
            
        except Exception as e:
            logger.error(f"Failed to merge revisions: {e}")
            return None
    
    def _enforce_version_limit(self, content_id: str):
        """强制执行版本数量限制"""
        try:
            revisions = self.get_content_revisions(content_id)
            
            if len(revisions) > self.config.max_versions:
                # 删除最旧的版本
                revisions_to_keep = revisions[:self.config.max_versions]
                revisions_to_delete = revisions[self.config.max_versions:]
                
                for revision in revisions_to_delete:
                    self._delete_revision(revision.revision_id)
                
                logger.info(f"Deleted {len(revisions_to_delete)} old revisions for content {content_id}")
                
        except Exception as e:
            logger.error(f"Failed to enforce version limit: {e}")
    
    def _delete_revision(self, revision_id: str):
        """删除修订记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM revisions WHERE revision_id = ?",
                (revision_id,)
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to delete revision: {e}")
    
    def get_revision_statistics(self, content_id: str) -> Dict[str, Any]:
        """获取修订统计信息"""
        revisions = self.get_content_revisions(content_id)
        
        if not revisions:
            return {}
        
        # 计算各种统计信息
        total_revisions = len(revisions)
        authors = set(rev.author for rev in revisions)
        status_counts = {}
        action_counts = {}
        
        for rev in revisions:
            status_counts[rev.status.value] = status_counts.get(rev.status.value, 0) + 1
            action_counts[rev.action.value] = action_counts.get(rev.action.value, 0) + 1
        
        # 计算修订频率
        if len(revisions) > 1:
            time_spans = []
            for i in range(1, len(revisions)):
                time_diff = revisions[i-1].timestamp - revisions[i].timestamp
                time_spans.append(time_diff.total_seconds())
            
            avg_revision_interval = sum(time_spans) / len(time_spans) if time_spans else 0
        else:
            avg_revision_interval = 0
        
        return {
            "content_id": content_id,
            "total_revisions": total_revisions,
            "unique_authors": len(authors),
            "authors": list(authors),
            "status_distribution": status_counts,
            "action_distribution": action_counts,
            "first_revision": revisions[-1].timestamp.isoformat(),
            "last_revision": revisions[0].timestamp.isoformat(),
            "average_revision_interval_seconds": avg_revision_interval,
            "current_version": revisions[0].version
        }
    
    def export_revision_history(self, content_id: str, output_path: str) -> bool:
        """导出修订历史"""
        try:
            revisions = self.get_content_revisions(content_id)
            statistics = self.get_revision_statistics(content_id)
            
            export_data = {
                "content_id": content_id,
                "exported_at": datetime.now().isoformat(),
                "statistics": statistics,
                "revisions": [rev.dict() for rev in revisions]
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported revision history for {content_id} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export revision history: {e}")
            return False
    
    def cleanup_old_revisions(self, days_old: int = 30) -> int:
        """
        清理旧修订记录
        
        Args:
            days_old: 保留多少天内的记录
            
        Returns:
            int: 删除的记录数量
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM revisions WHERE timestamp < ? AND status != ?",
                (cutoff_date.isoformat(), RevisionStatus.PUBLISHED.value)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old revisions")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old revisions: {e}")
            return 0

# 单例实例
_revision_manager_instance = None

def get_revision_manager() -> RevisionManager:
    """获取修订管理器单例"""
    global _revision_manager_instance
    if _revision_manager_instance is None:
        _revision_manager_instance = RevisionManager()
    return _revision_manager_instance

