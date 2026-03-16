"""
对话记录管理模块 - 管理用户对话历史和上下文
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConversationType(Enum):
    """对话类型枚举"""
    TEXT_CHAT = "text_chat"
    VOICE_CHAT = "voice_chat"
    MULTIMODAL = "multimodal"
    TASK_ORIENTED = "task_oriented"
    LEARNING_SESSION = "learning_session"
    CUSTOMER_SERVICE = "customer_service"

class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    FUNCTION = "function"

class ConversationStatus(Enum):
    """对话状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DELETED = "deleted"

@dataclass
class MessageContent:
    """消息内容数据类"""
    text: Optional[str] = None
    audio_path: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    file_attachments: List[str] = field(default_factory=list)
    emotion: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Message:
    """消息数据类"""
    message_id: str
    conversation_id: str
    role: MessageRole
    content: MessageContent
    timestamp: datetime
    parent_message_id: Optional[str] = None
    response_to: Optional[str] = None
    processing_time: float = 0.0
    tokens_used: int = 0
    sentiment_score: float = 0.0
    user_feedback: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConversationContext:
    """对话上下文数据类"""
    current_topic: str
    topics_history: List[str]
    user_intent: str
    conversation_goal: Optional[str] = None
    user_mood: str = "neutral"
    system_capabilities_used: List[str] = field(default_factory=list)
    context_variables: Dict[str, Any] = field(default_factory=dict)
    memory_references: List[str] = field(default_factory=list)

@dataclass
class Conversation:
    """对话数据类"""
    conversation_id: str
    user_id: str
    title: str
    conversation_type: ConversationType
    status: ConversationStatus
    messages: List[Message]
    context: ConversationContext
    created_at: datetime
    updated_at: datetime
    last_message_time: datetime
    message_count: int
    average_response_time: float
    user_satisfaction_score: float
    tags: List[str]
    metadata: Dict[str, Any]

class ConversationManager:
    """对话管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化对话管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.conversations_table = config.get('conversations_table', 'user_conversations')
        self.messages_table = config.get('messages_table', 'conversation_messages')
        
        # 缓存配置
        self.cache_size = config.get('cache_size', 100)
        self._active_conversations = {}
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化对话管理相关表"""
        try:
            # 对话表
            conversations_schema = {
                'conversation_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'title': 'VARCHAR(500) NOT NULL',
                'conversation_type': 'VARCHAR(50) NOT NULL',
                'status': 'VARCHAR(20) NOT NULL',
                'messages': 'TEXT NOT NULL',  # JSON格式的消息列表
                'context': 'TEXT NOT NULL',  # JSON格式的上下文
                'created_at': 'TIMESTAMP NOT NULL',
                'updated_at': 'TIMESTAMP NOT NULL',
                'last_message_time': 'TIMESTAMP NOT NULL',
                'message_count': 'INTEGER DEFAULT 0',
                'average_response_time': 'FLOAT DEFAULT 0.0',
                'user_satisfaction_score': 'FLOAT DEFAULT 0.0',
                'tags': 'TEXT NOT NULL',  # JSON格式
                'metadata': 'TEXT NOT NULL'  # JSON格式
            }
            
            self.db.create_table(self.conversations_table, conversations_schema)
            
            # 消息表（用于详细消息记录和搜索）
            messages_schema = {
                'message_id': 'VARCHAR(100) PRIMARY KEY',
                'conversation_id': 'VARCHAR(100) NOT NULL',
                'role': 'VARCHAR(20) NOT NULL',
                'content': 'TEXT NOT NULL',  # JSON格式
                'timestamp': 'TIMESTAMP NOT NULL',
                'parent_message_id': 'VARCHAR(100)',
                'response_to': 'VARCHAR(100)',
                'processing_time': 'FLOAT DEFAULT 0.0',
                'tokens_used': 'INTEGER DEFAULT 0',
                'sentiment_score': 'FLOAT DEFAULT 0.0',
                'user_feedback': 'VARCHAR(100)',
                'metadata': 'TEXT'  # JSON格式
            }
            
            constraints = [
                'FOREIGN KEY (conversation_id) REFERENCES user_conversations(conversation_id) ON DELETE CASCADE'
            ]
            
            self.db.create_table(self.messages_table, messages_schema, constraints)
            
            # 创建索引
            self.db.create_index(self.conversations_table, 'user_id')
            self.db.create_index(self.conversations_table, 'conversation_type')
            self.db.create_index(self.conversations_table, 'status')
            self.db.create_index(self.conversations_table, 'created_at')
            self.db.create_index(self.messages_table, 'conversation_id')
            self.db.create_index(self.messages_table, 'role')
            self.db.create_index(self.messages_table, 'timestamp')
            
            self.logger.info("Conversation tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation tables: {str(e)}")
            raise
    
    def create_conversation(self, user_id: str, title: str, 
                          conversation_type: ConversationType = ConversationType.TEXT_CHAT,
                          initial_context: Dict[str, Any] = None) -> str:
        """
        创建新对话
        
        Args:
            user_id: 用户ID
            title: 对话标题
            conversation_type: 对话类型
            initial_context: 初始上下文
            
        Returns:
            str: 对话ID
        """
        try:
            conversation_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 构建对话上下文
            context = ConversationContext(
                current_topic=title,
                topics_history=[title],
                user_intent="general_conversation",
                conversation_goal=initial_context.get('goal') if initial_context else None,
                user_mood=initial_context.get('mood', 'neutral') if initial_context else 'neutral',
                context_variables=initial_context.get('variables', {}) if initial_context else {}
            )
            
            # 构建对话对象
            conversation = Conversation(
                conversation_id=conversation_id,
                user_id=user_id,
                title=title,
                conversation_type=conversation_type,
                status=ConversationStatus.ACTIVE,
                messages=[],
                context=context,
                created_at=current_time,
                updated_at=current_time,
                last_message_time=current_time,
                message_count=0,
                average_response_time=0.0,
                user_satisfaction_score=0.0,
                tags=[],
                metadata={'created_by': 'system'}
            )
            
            # 准备数据库数据
            db_data = {
                'conversation_id': conversation.conversation_id,
                'user_id': conversation.user_id,
                'title': conversation.title,
                'conversation_type': conversation.conversation_type.value,
                'status': conversation.status.value,
                'messages': json.dumps([], default=str),
                'context': json.dumps(asdict(conversation.context)),
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at,
                'last_message_time': conversation.last_message_time,
                'message_count': conversation.message_count,
                'average_response_time': conversation.average_response_time,
                'user_satisfaction_score': conversation.user_satisfaction_score,
                'tags': json.dumps(conversation.tags),
                'metadata': json.dumps(conversation.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.conversations_table, db_data)
            
            # 添加到缓存
            self._active_conversations[conversation_id] = conversation
            
            self.logger.info(f"Conversation created: {conversation_id} - {title}")
            return conversation_id
            
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {str(e)}")
            raise
    
    def add_message(self, conversation_id: str, role: MessageRole, 
                   content: Dict[str, Any], parent_message_id: str = None,
                   processing_time: float = 0.0, tokens_used: int = 0,
                   sentiment_score: float = 0.0) -> str:
        """
        添加消息到对话
        
        Args:
            conversation_id: 对话ID
            role: 消息角色
            content: 消息内容
            parent_message_id: 父消息ID
            processing_time: 处理时间
            tokens_used: 使用的token数量
            sentiment_score: 情感分数
            
        Returns:
            str: 消息ID
        """
        try:
            # 获取对话（从缓存或数据库）
            conversation = self._get_conversation(conversation_id)
            if not conversation:
                self.logger.error(f"Conversation not found: {conversation_id}")
                return None
            
            message_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 构建消息内容
            message_content = MessageContent(**content)
            
            # 确定响应关系
            response_to = None
            if role == MessageRole.ASSISTANT and conversation.messages:
                # 助理消息通常响应用户的最后一条消息
                last_user_msg = next(
                    (msg for msg in reversed(conversation.messages) 
                     if msg.role == MessageRole.USER), 
                    None
                )
                if last_user_msg:
                    response_to = last_user_msg.message_id
            
            # 构建消息对象
            message = Message(
                message_id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=message_content,
                timestamp=current_time,
                parent_message_id=parent_message_id,
                response_to=response_to,
                processing_time=processing_time,
                tokens_used=tokens_used,
                sentiment_score=sentiment_score,
                metadata={'created_at': current_time.isoformat()}
            )
            
            # 添加到对话消息列表
            conversation.messages.append(message)
            
            # 更新对话统计
            conversation.updated_at = current_time
            conversation.last_message_time = current_time
            conversation.message_count = len(conversation.messages)
            
            # 更新平均响应时间
            if role == MessageRole.ASSISTANT and conversation.messages:
                # 计算助理消息的平均响应时间
                assistant_messages = [msg for msg in conversation.messages 
                                    if msg.role == MessageRole.ASSISTANT]
                if assistant_messages:
                    total_processing_time = sum(msg.processing_time for msg in assistant_messages)
                    conversation.average_response_time = total_processing_time / len(assistant_messages)
            
            # 更新数据库
            self._update_conversation_in_db(conversation)
            
            # 单独存储消息记录
            message_data = {
                'message_id': message.message_id,
                'conversation_id': message.conversation_id,
                'role': message.role.value,
                'content': json.dumps(asdict(message.content)),
                'timestamp': message.timestamp,
                'parent_message_id': message.parent_message_id,
                'response_to': message.response_to,
                'processing_time': message.processing_time,
                'tokens_used': message.tokens_used,
                'sentiment_score': message.sentiment_score,
                'user_feedback': message.user_feedback,
                'metadata': json.dumps(message.metadata)
            }
            
            self.db.execute_insert(self.messages_table, message_data)
            
            self.logger.debug(f"Message added to conversation {conversation_id}: {message_id}")
            return message_id
            
        except Exception as e:
            self.logger.error(f"Failed to add message: {str(e)}")
            return None
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        获取对话信息
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Conversation: 对话信息，如果不存在返回None
        """
        return self._get_conversation(conversation_id)
    
    def _get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """内部方法：获取对话（优先从缓存）"""
        # 先检查缓存
        if conversation_id in self._active_conversations:
            return self._active_conversations[conversation_id]
        
        try:
            query = f"SELECT * FROM {self.conversations_table} WHERE conversation_id = %s"
            results = self.db.execute_query(query, (conversation_id,))
            
            if not results:
                return None
            
            conv_data = results[0]
            
            # 解析消息列表
            messages_data = json.loads(conv_data['messages'])
            messages = []
            for msg_data in messages_data:
                content_data = msg_data.get('content', {})
                message = Message(
                    message_id=msg_data['message_id'],
                    conversation_id=msg_data['conversation_id'],
                    role=MessageRole(msg_data['role']),
                    content=MessageContent(**content_data),
                    timestamp=datetime.fromisoformat(msg_data['timestamp']),
                    parent_message_id=msg_data.get('parent_message_id'),
                    response_to=msg_data.get('response_to'),
                    processing_time=msg_data.get('processing_time', 0.0),
                    tokens_used=msg_data.get('tokens_used', 0),
                    sentiment_score=msg_data.get('sentiment_score', 0.0),
                    user_feedback=msg_data.get('user_feedback'),
                    metadata=msg_data.get('metadata', {})
                )
                messages.append(message)
            
            # 解析上下文
            context_data = json.loads(conv_data['context'])
            context = ConversationContext(**context_data)
            
            # 构建对话对象
            conversation = Conversation(
                conversation_id=conv_data['conversation_id'],
                user_id=conv_data['user_id'],
                title=conv_data['title'],
                conversation_type=ConversationType(conv_data['conversation_type']),
                status=ConversationStatus(conv_data['status']),
                messages=messages,
                context=context,
                created_at=conv_data['created_at'],
                updated_at=conv_data['updated_at'],
                last_message_time=conv_data['last_message_time'],
                message_count=conv_data['message_count'],
                average_response_time=conv_data['average_response_time'],
                user_satisfaction_score=conv_data['user_satisfaction_score'],
                tags=json.loads(conv_data['tags']),
                metadata=json.loads(conv_data['metadata'])
            )
            
            # 添加到缓存
            if len(self._active_conversations) >= self.cache_size:
                # 移除最旧的对话
                oldest_id = min(self._active_conversations.keys(), 
                              key=lambda k: self._active_conversations[k].updated_at)
                del self._active_conversations[oldest_id]
            
            self._active_conversations[conversation_id] = conversation
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation: {str(e)}")
            return None
    
    def get_user_conversations(self, user_id: str, status: ConversationStatus = None,
                             limit: int = 50, offset: int = 0) -> List[Conversation]:
        """
        获取用户对话列表
        
        Args:
            user_id: 用户ID
            status: 对话状态筛选
            limit: 返回记录限制
            offset: 偏移量
            
        Returns:
            List[Conversation]: 对话列表
        """
        try:
            where_conditions = ["user_id = %s"]
            params = [user_id]
            
            if status:
                where_conditions.append("status = %s")
                params.append(status.value)
            
            where_clause = " AND ".join(where_conditions)
            query = f"""
            SELECT * FROM {self.conversations_table} 
            WHERE {where_clause} 
            ORDER BY last_message_time DESC 
            LIMIT %s OFFSET %s
            """
            
            params.extend([limit, offset])
            results = self.db.execute_query(query, tuple(params))
            
            conversations = []
            for row in results:
                conversation = self._convert_db_row_to_conversation(row)
                if conversation:
                    conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"Failed to get user conversations: {str(e)}")
            return []
    
    def update_conversation_status(self, conversation_id: str, 
                                 status: ConversationStatus) -> bool:
        """
        更新对话状态
        
        Args:
            conversation_id: 对话ID
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            conversation = self._get_conversation(conversation_id)
            if not conversation:
                return False
            
            conversation.status = status
            conversation.updated_at = datetime.now()
            
            # 更新数据库
            update_data = {
                'status': status.value,
                'updated_at': conversation.updated_at
            }
            
            affected = self.db.execute_update(
                self.conversations_table,
                update_data,
                "conversation_id = %s",
                (conversation_id,)
            )
            
            if affected > 0:
                self.logger.info(f"Conversation status updated: {conversation_id} -> {status.value}")
                return True
            else:
                self.logger.warning(f"Conversation not found for status update: {conversation_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update conversation status: {str(e)}")
            return False
    
    def update_conversation_context(self, conversation_id: str, 
                                  context_updates: Dict[str, Any]) -> bool:
        """
        更新对话上下文
        
        Args:
            conversation_id: 对话ID
            context_updates: 上下文更新数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            conversation = self._get_conversation(conversation_id)
            if not conversation:
                return False
            
            # 更新上下文
            for key, value in context_updates.items():
                if hasattr(conversation.context, key):
                    setattr(conversation.context, key, value)
                else:
                    conversation.context.context_variables[key] = value
            
            conversation.updated_at = datetime.now()
            
            # 更新数据库
            self._update_conversation_in_db(conversation)
            
            self.logger.debug(f"Conversation context updated: {conversation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation context: {str(e)}")
            return False
    
    def search_conversations(self, user_id: str, query: str = None,
                           conversation_type: ConversationType = None,
                           tags: List[str] = None, date_from: datetime = None,
                           date_to: datetime = None, limit: int = 50) -> List[Conversation]:
        """
        搜索对话
        
        Args:
            user_id: 用户ID
            query: 搜索关键词
            conversation_type: 对话类型筛选
            tags: 标签筛选
            date_from: 开始日期
            date_to: 结束日期
            limit: 返回记录限制
            
        Returns:
            List[Conversation]: 对话列表
        """
        try:
            where_conditions = ["user_id = %s"]
            params = [user_id]
            
            if query:
                # 搜索标题和消息内容
                where_conditions.append("""
                (title LIKE %s OR 
                 messages LIKE %s OR 
                 context LIKE %s)
                """)
                search_pattern = f"%{query}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if conversation_type:
                where_conditions.append("conversation_type = %s")
                params.append(conversation_type.value)
            
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE %s")
                    params.append(f'%"{tag}"%')
                where_conditions.append(f"({' OR '.join(tag_conditions)})")
            
            if date_from:
                where_conditions.append("last_message_time >= %s")
                params.append(date_from)
            
            if date_to:
                where_conditions.append("last_message_time <= %s")
                params.append(date_to)
            
            where_clause = " AND ".join(where_conditions)
            sql = f"""
            SELECT * FROM {self.conversations_table} 
            WHERE {where_clause}
            ORDER BY last_message_time DESC
            LIMIT %s
            """
            
            params.append(limit)
            results = self.db.execute_query(sql, tuple(params))
            
            conversations = []
            for row in results:
                conversation = self._convert_db_row_to_conversation(row)
                if conversation:
                    conversations.append(conversation)
            
            return conversations
            
        except Exception as e:
            self.logger.error(f"Failed to search conversations: {str(e)}")
            return []
    
    def get_conversation_analytics(self, user_id: str, 
                                 time_window_days: int = 30) -> Dict[str, Any]:
        """
        获取对话分析数据
        
        Args:
            user_id: 用户ID
            time_window_days: 时间窗口（天）
            
        Returns:
            Dict: 分析数据
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_window_days)
            
            # 获取对话数据
            conversations = self.get_user_conversations(user_id, limit=1000)
            recent_conversations = [
                conv for conv in conversations 
                if conv.last_message_time >= start_time
            ]
            
            if not recent_conversations:
                return {'error': 'No conversation data found'}
            
            analytics = {
                'user_id': user_id,
                'analysis_period': f"{time_window_days} days",
                'total_conversations': len(recent_conversations),
                'conversation_types': {},
                'message_stats': {},
                'time_patterns': {},
                'satisfaction_metrics': {},
                'insights': []
            }
            
            # 按类型统计
            type_counts = {}
            type_message_counts = {}
            
            # 消息统计
            total_messages = 0
            user_messages = 0
            assistant_messages = 0
            total_processing_time = 0.0
            
            # 时间段统计
            hour_counts = {}
            
            for conversation in recent_conversations:
                # 类型统计
                conv_type = conversation.conversation_type.value
                type_counts[conv_type] = type_counts.get(conv_type, 0) + 1
                type_message_counts[conv_type] = type_message_counts.get(conv_type, 0) + conversation.message_count
                
                # 消息统计
                total_messages += conversation.message_count
                user_msg_count = len([msg for msg in conversation.messages if msg.role == MessageRole.USER])
                assistant_msg_count = len([msg for msg in conversation.messages if msg.role == MessageRole.ASSISTANT])
                user_messages += user_msg_count
                assistant_messages += assistant_msg_count
                
                # 处理时间
                total_processing_time += conversation.average_response_time * assistant_msg_count
                
                # 时间段统计
                hour = conversation.last_message_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            analytics['conversation_types'] = {
                'counts': type_counts,
                'average_messages': {k: v / type_counts[k] for k, v in type_message_counts.items()}
            }
            
            analytics['message_stats'] = {
                'total_messages': total_messages,
                'user_messages': user_messages,
                'assistant_messages': assistant_messages,
                'messages_per_conversation': total_messages / len(recent_conversations) if recent_conversations else 0,
                'average_processing_time': total_processing_time / assistant_messages if assistant_messages > 0 else 0
            }
            
            analytics['time_patterns'] = {
                'by_hour': dict(sorted(hour_counts.items()))
            }
            
            # 满意度指标
            satisfaction_scores = [conv.user_satisfaction_score for conv in recent_conversations 
                                 if conv.user_satisfaction_score > 0]
            if satisfaction_scores:
                analytics['satisfaction_metrics'] = {
                    'average_score': sum(satisfaction_scores) / len(satisfaction_scores),
                    'max_score': max(satisfaction_scores),
                    'min_score': min(satisfaction_scores)
                }
            
            # 生成洞察
            analytics['insights'] = self._generate_conversation_insights(analytics, recent_conversations)
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation analytics: {str(e)}")
            return {'error': str(e)}
    
    def export_conversation(self, conversation_id: str, 
                          format_type: str = "json") -> Dict[str, Any]:
        """
        导出对话数据
        
        Args:
            conversation_id: 对话ID
            format_type: 导出格式
            
        Returns:
            Dict: 导出的对话数据
        """
        try:
            conversation = self._get_conversation(conversation_id)
            if not conversation:
                return {'error': 'Conversation not found'}
            
            export_data = {
                'conversation_id': conversation.conversation_id,
                'user_id': conversation.user_id,
                'title': conversation.title,
                'conversation_type': conversation.conversation_type.value,
                'status': conversation.status.value,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat(),
                'last_message_time': conversation.last_message_time.isoformat(),
                'message_count': conversation.message_count,
                'average_response_time': conversation.average_response_time,
                'user_satisfaction_score': conversation.user_satisfaction_score,
                'tags': conversation.tags,
                'context': asdict(conversation.context),
                'messages': [],
                'exported_at': datetime.now().isoformat(),
                'export_format': format_type
            }
            
            # 添加消息数据
            for message in conversation.messages:
                message_data = {
                    'message_id': message.message_id,
                    'role': message.role.value,
                    'content': asdict(message.content),
                    'timestamp': message.timestamp.isoformat(),
                    'parent_message_id': message.parent_message_id,
                    'response_to': message.response_to,
                    'processing_time': message.processing_time,
                    'tokens_used': message.tokens_used,
                    'sentiment_score': message.sentiment_score,
                    'user_feedback': message.user_feedback,
                    'metadata': message.metadata
                }
                export_data['messages'].append(message_data)
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Failed to export conversation: {str(e)}")
            return {'error': str(e)}
    
    def _update_conversation_in_db(self, conversation: Conversation):
        """更新数据库中的对话数据"""
        try:
            update_data = {
                'title': conversation.title,
                'status': conversation.status.value,
                'messages': json.dumps([asdict(msg) for msg in conversation.messages], default=str),
                'context': json.dumps(asdict(conversation.context)),
                'updated_at': conversation.updated_at,
                'last_message_time': conversation.last_message_time,
                'message_count': conversation.message_count,
                'average_response_time': conversation.average_response_time,
                'user_satisfaction_score': conversation.user_satisfaction_score,
                'tags': json.dumps(conversation.tags),
                'metadata': json.dumps(conversation.metadata)
            }
            
            self.db.execute_update(
                self.conversations_table,
                update_data,
                "conversation_id = %s",
                (conversation.conversation_id,)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation in DB: {str(e)}")
            raise
    
    def _convert_db_row_to_conversation(self, row: Dict) -> Optional[Conversation]:
        """将数据库行转换为Conversation对象"""
        try:
            # 解析消息列表
            messages_data = json.loads(row['messages'])
            messages = []
            for msg_data in messages_data:
                content_data = msg_data.get('content', {})
                # 处理时间戳
                timestamp_str = msg_data['timestamp']
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str
                
                message = Message(
                    message_id=msg_data['message_id'],
                    conversation_id=msg_data['conversation_id'],
                    role=MessageRole(msg_data['role']),
                    content=MessageContent(**content_data),
                    timestamp=timestamp,
                    parent_message_id=msg_data.get('parent_message_id'),
                    response_to=msg_data.get('response_to'),
                    processing_time=msg_data.get('processing_time', 0.0),
                    tokens_used=msg_data.get('tokens_used', 0),
                    sentiment_score=msg_data.get('sentiment_score', 0.0),
                    user_feedback=msg_data.get('user_feedback'),
                    metadata=msg_data.get('metadata', {})
                )
                messages.append(message)
            
            # 解析上下文
            context_data = json.loads(row['context'])
            context = ConversationContext(**context_data)
            
            # 构建对话对象
            return Conversation(
                conversation_id=row['conversation_id'],
                user_id=row['user_id'],
                title=row['title'],
                conversation_type=ConversationType(row['conversation_type']),
                status=ConversationStatus(row['status']),
                messages=messages,
                context=context,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                last_message_time=row['last_message_time'],
                message_count=row['message_count'],
                average_response_time=row['average_response_time'],
                user_satisfaction_score=row['user_satisfaction_score'],
                tags=json.loads(row['tags']),
                metadata=json.loads(row['metadata'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert DB row to conversation: {str(e)}")
            return None
    
    def _generate_conversation_insights(self, analytics: Dict[str, Any], 
                                      conversations: List[Conversation]) -> List[str]:
        """生成对话洞察"""
        insights = []
        
        # 分析对话类型分布
        type_counts = analytics.get('conversation_types', {}).get('counts', {})
        if type_counts:
            most_common_type = max(type_counts.items(), key=lambda x: x[1])
            insights.append(f"最常用的对话类型: {most_common_type[0]} ({most_common_type[1]}次)")
        
        # 分析消息模式
        message_stats = analytics.get('message_stats', {})
        if message_stats.get('total_messages', 0) > 0:
            avg_messages = message_stats['messages_per_conversation']
            if avg_messages > 20:
                insights.append("对话深度较深，平均消息数较多")
            elif avg_messages < 5:
                insights.append("对话较为简短，多为快速交互")
        
        # 分析响应时间
        avg_processing_time = message_stats.get('average_processing_time', 0)
        if avg_processing_time > 5.0:
            insights.append(f"平均响应时间较长 ({avg_processing_time:.1f}s)，建议优化系统性能")
        
        return insights

