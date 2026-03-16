"""
用户文档管理模块 - 管理用户创建的文档和文件
"""

import logging
import json
import uuid
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """文档类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    CODE = "code"
    PDF = "pdf"
    OTHER = "other"

class DocumentStatus(Enum):
    """文档状态枚举"""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DELETED = "deleted"

@dataclass
class DocumentMetadata:
    """文档元数据"""
    file_size: int
    file_format: str
    created_by: str
    last_modified_by: str
    checksum: str
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    duration: Optional[float] = None  # 对于音视频文件
    resolution: Optional[str] = None  # 对于图片和视频
    language: str = "zh-CN"

@dataclass
class DocumentVersion:
    """文档版本信息"""
    version_id: str
    version_number: int
    created_at: datetime
    created_by: str
    change_description: str
    file_path: str
    file_size: int
    checksum: str

@dataclass
class DocumentPermissions:
    """文档权限设置"""
    can_view: List[str]  # 用户ID列表
    can_edit: List[str]  # 用户ID列表
    can_share: List[str]  # 用户ID列表
    is_public: bool = False
    encryption_key: Optional[str] = None

@dataclass
class UserDocument:
    """用户文档数据类"""
    document_id: str
    user_id: str
    title: str
    description: Optional[str]
    document_type: DocumentType
    file_path: str
    tags: List[str]
    category: str
    status: DocumentStatus
    metadata: DocumentMetadata
    permissions: DocumentPermissions
    versions: List[DocumentVersion]
    created_at: datetime
    updated_at: datetime
    last_accessed: datetime
    access_count: int
    favorite: bool
    parent_document_id: Optional[str]  # 用于文档版本树
    related_documents: List[str]  # 相关文档ID列表

class UserDocuments:
    """用户文档管理器"""
    
    def __init__(self, db_integration, storage_manager, config: Dict[str, Any]):
        """
        初始化用户文档管理器
        
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
        self.documents_table = config.get('documents_table', 'user_documents')
        self.versions_table = config.get('versions_table', 'document_versions')
        self.access_logs_table = config.get('access_logs_table', 'document_access_logs')
        
        # 存储路径配置
        self.base_storage_path = config.get('storage_path', './user_documents')
        self.max_file_size = config.get('max_file_size', 100 * 1024 * 1024)  # 100MB
        
        # 创建存储目录
        os.makedirs(self.base_storage_path, exist_ok=True)
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化文档管理相关表"""
        try:
            # 用户文档表
            documents_schema = {
                'document_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'title': 'VARCHAR(500) NOT NULL',
                'description': 'TEXT',
                'document_type': 'VARCHAR(50) NOT NULL',
                'file_path': 'VARCHAR(1000) NOT NULL',
                'tags': 'TEXT NOT NULL',
                'category': 'VARCHAR(100) NOT NULL',
                'status': 'VARCHAR(20) NOT NULL',
                'metadata': 'TEXT NOT NULL',
                'permissions': 'TEXT NOT NULL',
                'versions': 'TEXT NOT NULL',
                'created_at': 'TIMESTAMP NOT NULL',
                'updated_at': 'TIMESTAMP NOT NULL',
                'last_accessed': 'TIMESTAMP NOT NULL',
                'access_count': 'INTEGER DEFAULT 0',
                'favorite': 'BOOLEAN DEFAULT FALSE',
                'parent_document_id': 'VARCHAR(100)',
                'related_documents': 'TEXT NOT NULL'
            }
            
            self.db.create_table(self.documents_table, documents_schema)
            
            # 文档版本表
            versions_schema = {
                'version_id': 'VARCHAR(100) PRIMARY KEY',
                'document_id': 'VARCHAR(100) NOT NULL',
                'version_number': 'INTEGER NOT NULL',
                'created_at': 'TIMESTAMP NOT NULL',
                'created_by': 'VARCHAR(100) NOT NULL',
                'change_description': 'TEXT',
                'file_path': 'VARCHAR(1000) NOT NULL',
                'file_size': 'INTEGER NOT NULL',
                'checksum': 'VARCHAR(64) NOT NULL'
            }
            
            constraints = [
                'FOREIGN KEY (document_id) REFERENCES user_documents(document_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.versions_table, versions_schema, constraints)
            
            # 文档访问日志表
            access_logs_schema = {
                'log_id': 'SERIAL PRIMARY KEY',
                'document_id': 'VARCHAR(100) NOT NULL',
                'user_id': 'VARCHAR(100) NOT NULL',
                'access_type': 'VARCHAR(20) NOT NULL',  # view, edit, download, share
                'access_time': 'TIMESTAMP NOT NULL',
                'ip_address': 'VARCHAR(45)',
                'user_agent': 'TEXT',
                'session_id': 'VARCHAR(100)'
            }
            
            constraints = [
                'FOREIGN KEY (document_id) REFERENCES user_documents(document_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.access_logs_table, access_logs_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.documents_table, 'user_id')
            self.db.create_index(self.documents_table, 'document_type')
            self.db.create_index(self.documents_table, 'category')
            self.db.create_index(self.documents_table, 'status')
            self.db.create_index(self.documents_table, 'created_at')
            self.db.create_index(self.versions_table, 'document_id')
            self.db.create_index(self.access_logs_table, 'document_id')
            self.db.create_index(self.access_logs_table, 'user_id')
            self.db.create_index(self.access_logs_table, 'access_time')
            
            self.logger.info("User document tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user document tables: {str(e)}")
            raise
    
    def create_document(self, user_id: str, title: str, document_type: DocumentType,
                      file_content: bytes, description: str = None, tags: List[str] = None,
                      category: str = "general", permissions: Dict[str, Any] = None) -> str:
        """
        创建新文档
        
        Args:
            user_id: 用户ID
            title: 文档标题
            document_type: 文档类型
            file_content: 文件内容
            description: 文档描述
            tags: 标签列表
            category: 文档分类
            permissions: 权限设置
            
        Returns:
            str: 文档ID
        """
        try:
            # 验证文件大小
            if len(file_content) > self.max_file_size:
                raise ValueError(f"File size exceeds maximum limit: {self.max_file_size}")
            
            document_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 生成文件路径
            file_extension = self._get_file_extension(document_type)
            filename = f"{document_id}{file_extension}"
            file_path = os.path.join(self.base_storage_path, user_id, filename)
            
            # 创建用户目录
            user_dir = os.path.dirname(file_path)
            os.makedirs(user_dir, exist_ok=True)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # 计算文件校验和
            checksum = hashlib.sha256(file_content).hexdigest()
            
            # 构建文档元数据
            metadata = DocumentMetadata(
                file_size=len(file_content),
                file_format=file_extension.lstrip('.'),
                created_by=user_id,
                last_modified_by=user_id,
                checksum=checksum,
                word_count=self._calculate_word_count(file_content, document_type),
                page_count=self._calculate_page_count(file_content, document_type),
                language="zh-CN"
            )
            
            # 构建权限设置
            if permissions is None:
                permissions = DocumentPermissions(
                    can_view=[user_id],
                    can_edit=[user_id],
                    can_share=[user_id],
                    is_public=False
                )
            else:
                permissions = DocumentPermissions(**permissions)
            
            # 创建初始版本
            version_id = str(uuid.uuid4())
            version = DocumentVersion(
                version_id=version_id,
                version_number=1,
                created_at=current_time,
                created_by=user_id,
                change_description="Initial version",
                file_path=file_path,
                file_size=len(file_content),
                checksum=checksum
            )
            
            # 构建文档对象
            document = UserDocument(
                document_id=document_id,
                user_id=user_id,
                title=title,
                description=description,
                document_type=document_type,
                file_path=file_path,
                tags=tags or [],
                category=category,
                status=DocumentStatus.DRAFT,
                metadata=metadata,
                permissions=permissions,
                versions=[version],
                created_at=current_time,
                updated_at=current_time,
                last_accessed=current_time,
                access_count=0,
                favorite=False,
                parent_document_id=None,
                related_documents=[]
            )
            
            # 准备数据库数据
            db_data = {
                'document_id': document.document_id,
                'user_id': document.user_id,
                'title': document.title,
                'description': document.description,
                'document_type': document.document_type.value,
                'file_path': document.file_path,
                'tags': json.dumps(document.tags),
                'category': document.category,
                'status': document.status.value,
                'metadata': json.dumps(asdict(document.metadata)),
                'permissions': json.dumps(asdict(document.permissions)),
                'versions': json.dumps([asdict(v) for v in document.versions]),
                'created_at': document.created_at,
                'updated_at': document.updated_at,
                'last_accessed': document.last_accessed,
                'access_count': document.access_count,
                'favorite': document.favorite,
                'parent_document_id': document.parent_document_id,
                'related_documents': json.dumps(document.related_documents)
            }
            
            # 插入数据库
            self.db.execute_insert(self.documents_table, db_data)
            
            # 插入版本记录
            version_data = {
                'version_id': version.version_id,
                'document_id': document_id,
                'version_number': version.version_number,
                'created_at': version.created_at,
                'created_by': version.created_by,
                'change_description': version.change_description,
                'file_path': version.file_path,
                'file_size': version.file_size,
                'checksum': version.checksum
            }
            self.db.execute_insert(self.versions_table, version_data)
            
            self.logger.info(f"Document created: {document_id} - {title}")
            return document_id
            
        except Exception as e:
            self.logger.error(f"Failed to create document: {str(e)}")
            # 清理已创建的文件
            if 'file_path' in locals():
                try:
                    os.remove(file_path)
                except:
                    pass
            raise
    
    def get_document(self, document_id: str, user_id: str = None) -> Optional[UserDocument]:
        """
        获取文档信息
        
        Args:
            document_id: 文档ID
            user_id: 用户ID（用于权限检查）
            
        Returns:
            UserDocument: 文档信息，如果不存在或无权访问返回None
        """
        try:
            query = f"SELECT * FROM {self.documents_table} WHERE document_id = %s"
            results = self.db.execute_query(query, (document_id,))
            
            if not results:
                return None
            
            doc_data = results[0]
            
            # 检查权限
            if user_id:
                permissions = json.loads(doc_data['permissions'])
                if (not permissions['is_public'] and 
                    user_id not in permissions['can_view']):
                    self.logger.warning(f"User {user_id} has no permission to access document {document_id}")
                    return None
            
            # 转换为UserDocument对象
            metadata_dict = json.loads(doc_data['metadata'])
            permissions_dict = json.loads(doc_data['permissions'])
            versions_dict = json.loads(doc_data['versions'])
            
            return UserDocument(
                document_id=doc_data['document_id'],
                user_id=doc_data['user_id'],
                title=doc_data['title'],
                description=doc_data['description'],
                document_type=DocumentType(doc_data['document_type']),
                file_path=doc_data['file_path'],
                tags=json.loads(doc_data['tags']),
                category=doc_data['category'],
                status=DocumentStatus(doc_data['status']),
                metadata=DocumentMetadata(**metadata_dict),
                permissions=DocumentPermissions(**permissions_dict),
                versions=[DocumentVersion(**v) for v in versions_dict],
                created_at=doc_data['created_at'],
                updated_at=doc_data['updated_at'],
                last_accessed=doc_data['last_accessed'],
                access_count=doc_data['access_count'],
                favorite=doc_data['favorite'],
                parent_document_id=doc_data['parent_document_id'],
                related_documents=json.loads(doc_data['related_documents'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get document: {str(e)}")
            return None
    
    def get_document_content(self, document_id: str, user_id: str) -> Optional[bytes]:
        """
        获取文档内容
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            
        Returns:
            bytes: 文档内容，如果无权访问返回None
        """
        try:
            document = self.get_document(document_id, user_id)
            if not document:
                return None
            
            # 记录访问日志
            self._log_document_access(document_id, user_id, 'view')
            
            # 更新访问计数
            self._update_access_count(document_id)
            
            # 读取文件内容
            with open(document.file_path, 'rb') as f:
                content = f.read()
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to get document content: {str(e)}")
            return None
    
    def update_document(self, document_id: str, user_id: str, 
                       updates: Dict[str, Any]) -> bool:
        """
        更新文档信息
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            updates: 更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 检查权限
            document = self.get_document(document_id, user_id)
            if not document:
                return False
            
            permissions = document.permissions
            if user_id not in permissions.can_edit:
                self.logger.warning(f"User {user_id} has no permission to edit document {document_id}")
                return False
            
            # 准备更新数据
            update_data = {
                'updated_at': datetime.now()
            }
            
            # 处理可更新字段
            allowed_fields = ['title', 'description', 'tags', 'category', 'status', 'favorite']
            for field in allowed_fields:
                if field in updates:
                    if field == 'tags':
                        update_data[field] = json.dumps(updates[field])
                    elif field == 'status':
                        update_data[field] = updates[field].value
                    else:
                        update_data[field] = updates[field]
            
            # 执行更新
            affected = self.db.execute_update(
                self.documents_table,
                update_data,
                "document_id = %s",
                (document_id,)
            )
            
            if affected > 0:
                self.logger.info(f"Document updated: {document_id}")
                return True
            else:
                self.logger.warning(f"Document not found for update: {document_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update document: {str(e)}")
            return False
    
    def create_document_version(self, document_id: str, user_id: str,
                              file_content: bytes, change_description: str) -> bool:
        """
        创建文档新版本
        
        Args:
            document_id: 文档ID
            user_id: 用户ID
            file_content: 新版本文件内容
            change_description: 版本变更描述
            
        Returns:
            bool: 创建是否成功
        """
        try:
            # 检查权限
            document = self.get_document(document_id, user_id)
            if not document:
                return False
            
            permissions = document.permissions
            if user_id not in permissions.can_edit:
                self.logger.warning(f"User {user_id} has no permission to edit document {document_id}")
                return False
            
            # 验证文件大小
            if len(file_content) > self.max_file_size:
                raise ValueError(f"File size exceeds maximum limit: {self.max_file_size}")
            
            current_time = datetime.now()
            
            # 生成新版本文件路径
            file_extension = self._get_file_extension(document.document_type)
            version_filename = f"{document_id}_v{len(document.versions) + 1}{file_extension}"
            version_file_path = os.path.join(self.base_storage_path, document.user_id, version_filename)
            
            # 保存新版本文件
            with open(version_file_path, 'wb') as f:
                f.write(file_content)
            
            # 计算文件校验和
            checksum = hashlib.sha256(file_content).hexdigest()
            
            # 创建版本记录
            version_id = str(uuid.uuid4())
            version = DocumentVersion(
                version_id=version_id,
                version_number=len(document.versions) + 1,
                created_at=current_time,
                created_by=user_id,
                change_description=change_description,
                file_path=version_file_path,
                file_size=len(file_content),
                checksum=checksum
            )
            
            # 插入版本记录
            version_data = {
                'version_id': version.version_id,
                'document_id': document_id,
                'version_number': version.version_number,
                'created_at': version.created_at,
                'created_by': version.created_by,
                'change_description': version.change_description,
                'file_path': version.file_path,
                'file_size': version.file_size,
                'checksum': version.checksum
            }
            self.db.execute_insert(self.versions_table, version_data)
            
            # 更新文档的版本列表
            document.versions.append(version)
            update_data = {
                'updated_at': current_time,
                'versions': json.dumps([asdict(v) for v in document.versions])
            }
            
            self.db.execute_update(
                self.documents_table,
                update_data,
                "document_id = %s",
                (document_id,)
            )
            
            # 记录访问日志
            self._log_document_access(document_id, user_id, 'edit')
            
            self.logger.info(f"Document version created: {document_id} - v{version.version_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create document version: {str(e)}")
            return False
    
    def search_documents(self, user_id: str, query: str = None, 
                        document_type: DocumentType = None, category: str = None,
                        tags: List[str] = None, status: DocumentStatus = None,
                        limit: int = 50, offset: int = 0) -> List[UserDocument]:
        """
        搜索用户文档
        
        Args:
            user_id: 用户ID
            query: 搜索关键词
            document_type: 文档类型筛选
            category: 分类筛选
            tags: 标签筛选
            status: 状态筛选
            limit: 返回记录限制
            offset: 偏移量
            
        Returns:
            List[UserDocument]: 文档列表
        """
        try:
            where_conditions = ["user_id = %s"]
            params = [user_id]
            
            if query:
                where_conditions.append("(title LIKE %s OR description LIKE %s)")
                params.extend([f"%{query}%", f"%{query}%"])
            
            if document_type:
                where_conditions.append("document_type = %s")
                params.append(document_type.value)
            
            if category:
                where_conditions.append("category = %s")
                params.append(category)
            
            if tags:
                # 简单的标签搜索（实际项目中可能需要更复杂的JSON查询）
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE %s")
                    params.append(f'%"{tag}"%')
                where_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            if status:
                where_conditions.append("status = %s")
                params.append(status.value)
            
            where_clause = " AND ".join(where_conditions)
            sql = f"""
            SELECT * FROM {self.documents_table} 
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            results = self.db.execute_query(sql, tuple(params))
            
            documents = []
            for row in results:
                try:
                    metadata_dict = json.loads(row['metadata'])
                    permissions_dict = json.loads(row['permissions'])
                    versions_dict = json.loads(row['versions'])
                    
                    document = UserDocument(
                        document_id=row['document_id'],
                        user_id=row['user_id'],
                        title=row['title'],
                        description=row['description'],
                        document_type=DocumentType(row['document_type']),
                        file_path=row['file_path'],
                        tags=json.loads(row['tags']),
                        category=row['category'],
                        status=DocumentStatus(row['status']),
                        metadata=DocumentMetadata(**metadata_dict),
                        permissions=DocumentPermissions(**permissions_dict),
                        versions=[DocumentVersion(**v) for v in versions_dict],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        last_accessed=row['last_accessed'],
                        access_count=row['access_count'],
                        favorite=row['favorite'],
                        parent_document_id=row['parent_document_id'],
                        related_documents=json.loads(row['related_documents'])
                    )
                    documents.append(document)
                except Exception as e:
                    self.logger.error(f"Failed to parse document {row['document_id']}: {str(e)}")
                    continue
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to search documents: {str(e)}")
            return []
    
    def get_document_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户文档统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 统计信息
        """
        try:
            # 文档类型统计
            type_query = f"""
            SELECT document_type, COUNT(*) as count 
            FROM {self.documents_table} 
            WHERE user_id = %s 
            GROUP BY document_type
            """
            type_results = self.db.execute_query(type_query, (user_id,))
            
            # 分类统计
            category_query = f"""
            SELECT category, COUNT(*) as count 
            FROM {self.documents_table} 
            WHERE user_id = %s 
            GROUP BY category
            """
            category_results = self.db.execute_query(category_query, (user_id,))
            
            # 存储空间使用
            storage_query = f"""
            SELECT SUM(metadata->>'file_size') as total_size 
            FROM {self.documents_table} 
            WHERE user_id = %s
            """
            storage_results = self.db.execute_query(storage_query, (user_id,))
            
            # 最近活动
            recent_query = f"""
            SELECT COUNT(*) as recent_count 
            FROM {self.documents_table} 
            WHERE user_id = %s AND updated_at >= %s
            """
            week_ago = datetime.now() - timedelta(days=7)
            recent_results = self.db.execute_query(recent_query, (user_id, week_ago))
            
            statistics = {
                'user_id': user_id,
                'total_documents': sum(row['count'] for row in type_results),
                'document_types': {row['document_type']: row['count'] for row in type_results},
                'categories': {row['category']: row['count'] for row in category_results},
                'total_storage_bytes': storage_results[0]['total_size'] if storage_results and storage_results[0]['total_size'] else 0,
                'recent_activity_count': recent_results[0]['recent_count'] if recent_results else 0,
                'generated_at': datetime.now().isoformat()
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Failed to get document statistics: {str(e)}")
            return {'error': str(e)}
    
    def _get_file_extension(self, document_type: DocumentType) -> str:
        """根据文档类型获取文件扩展名"""
        extensions = {
            DocumentType.TEXT: '.txt',
            DocumentType.IMAGE: '.png',
            DocumentType.AUDIO: '.wav',
            DocumentType.VIDEO: '.mp4',
            DocumentType.PRESENTATION: '.pptx',
            DocumentType.SPREADSHEET: '.xlsx',
            DocumentType.CODE: '.py',
            DocumentType.PDF: '.pdf',
            DocumentType.OTHER: '.bin'
        }
        return extensions.get(document_type, '.bin')
    
    def _calculate_word_count(self, content: bytes, document_type: DocumentType) -> Optional[int]:
        """计算文档字数"""
        try:
            if document_type in [DocumentType.TEXT, DocumentType.CODE]:
                text = content.decode('utf-8', errors='ignore')
                return len(text.split())
            return None
        except:
            return None
    
    def _calculate_page_count(self, content: bytes, document_type: DocumentType) -> Optional[int]:
        """计算文档页数（简化实现）"""
        try:
            if document_type == DocumentType.PDF:
                # 这里应该使用PDF解析库，此处简化处理
                return 1
            elif document_type == DocumentType.TEXT:
                text = content.decode('utf-8', errors='ignore')
                words_per_page = 500  # 假设每页500字
                word_count = len(text.split())
                return max(1, (word_count + words_per_page - 1) // words_per_page)
            return None
        except:
            return None
    
    def _log_document_access(self, document_id: str, user_id: str, access_type: str):
        """记录文档访问日志"""
        try:
            log_data = {
                'document_id': document_id,
                'user_id': user_id,
                'access_type': access_type,
                'access_time': datetime.now(),
                'session_id': str(uuid.uuid4())  # 简化处理
            }
            
            self.db.execute_insert(self.access_logs_table, log_data)
            
        except Exception as e:
            self.logger.debug(f"Failed to log document access: {str(e)}")
    
    def _update_access_count(self, document_id: str):
        """更新文档访问计数"""
        try:
            update_data = {
                'last_accessed': datetime.now(),
                'access_count': 'access_count + 1'
            }
            
            self.db.execute_update(
                self.documents_table,
                update_data,
                "document_id = %s",
                (document_id,),
                raw_fields=['access_count']
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to update access count: {str(e)}")

