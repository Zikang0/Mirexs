"""
交互历史模块 - 管理用户交互历史记录和分析
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import defaultdict
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class InteractionType(Enum):
    """交互类型枚举"""
    VOICE_COMMAND = "voice_command"
    TEXT_INPUT = "text_input"
    GESTURE = "gesture"
    TOUCH = "touch"
    GAZE = "gaze"
    SYSTEM_EVENT = "system_event"
    ERROR = "error"
    SUCCESS = "success"

class InteractionStatus(Enum):
    """交互状态枚举"""
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class InteractionContext:
    """交互上下文数据"""
    session_id: str
    device_type: str
    location: Optional[str]
    application: str
    environment: Dict[str, Any]

@dataclass
class InteractionResult:
    """交互结果数据"""
    success: bool
    response_time: float
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    confidence: float
    metadata: Dict[str, Any]

@dataclass
class InteractionRecord:
    """交互记录数据类"""
    interaction_id: str
    user_id: str
    interaction_type: InteractionType
    timestamp: datetime
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    context: InteractionContext
    result: InteractionResult
    status: InteractionStatus
    duration: float
    tags: List[str]
    metadata: Dict[str, Any]

class InteractionHistory:
    """交互历史管理器"""
    
    def __init__(self, db_integration, config: Dict[str, Any]):
        """
        初始化交互历史管理器
        
        Args:
            db_integration: 数据库集成实例
            config: 配置字典
        """
        self.db = db_integration
        self.config = config
        self.logger = logger
        
        # 表名配置
        self.interactions_table = config.get('interactions_table', 'interaction_history')
        self.sessions_table = config.get('sessions_table', 'user_sessions')
        
        # 缓存配置
        self.cache_size = config.get('cache_size', 1000)
        self._recent_interactions = []
        
        # 初始化表结构
        self._initialize_tables()
    
    def _initialize_tables(self):
        """初始化交互历史相关表"""
        try:
            # 交互历史表
            interactions_schema = {
                'interaction_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'interaction_type': 'VARCHAR(50) NOT NULL',
                'timestamp': 'TIMESTAMP NOT NULL',
                'input_data': 'TEXT NOT NULL',
                'output_data': 'TEXT NOT NULL',
                'context': 'TEXT NOT NULL',
                'result': 'TEXT NOT NULL',
                'status': 'VARCHAR(20) NOT NULL',
                'duration': 'FLOAT NOT NULL',
                'tags': 'TEXT NOT NULL',
                'metadata': 'TEXT NOT NULL'
            }
            
            self.db.create_table(self.interactions_table, interactions_schema)
            
            # 用户会话表
            sessions_schema = {
                'session_id': 'VARCHAR(100) PRIMARY KEY',
                'user_id': 'VARCHAR(100) NOT NULL',
                'start_time': 'TIMESTAMP NOT NULL',
                'end_time': 'TIMESTAMP',
                'duration': 'FLOAT',
                'interaction_count': 'INTEGER DEFAULT 0',
                'device_type': 'VARCHAR(50)',
                'application': 'VARCHAR(100)',
                'location': 'VARCHAR(255)',
                'success_rate': 'FLOAT DEFAULT 0.0',
                'average_response_time': 'FLOAT DEFAULT 0.0',
                'metadata': 'TEXT'
            }
            
            self.db.create_table(self.sessions_table, sessions_schema)
            
            # 创建索引
            self.db.create_index(self.interactions_table, 'user_id')
            self.db.create_index(self.interactions_table, 'interaction_type')
            self.db.create_index(self.interactions_table, 'timestamp')
            self.db.create_index(self.interactions_table, 'status')
            self.db.create_index(self.sessions_table, 'user_id')
            self.db.create_index(self.sessions_table, 'start_time')
            
            self.logger.info("Interaction history tables initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize interaction history tables: {str(e)}")
            raise
    
    def record_interaction(self, user_id: str, interaction_type: InteractionType,
                         input_data: Dict[str, Any], output_data: Dict[str, Any],
                         context: Dict[str, Any], result: Dict[str, Any],
                         duration: float, tags: List[str] = None) -> str:
        """
        记录交互历史
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            input_data: 输入数据
            output_data: 输出数据
            context: 上下文信息
            result: 结果数据
            duration: 交互时长
            tags: 标签列表
            
        Returns:
            str: 交互ID
        """
        try:
            interaction_id = str(uuid.uuid4())
            current_time = datetime.now()
            
            # 构建交互记录
            interaction_record = InteractionRecord(
                interaction_id=interaction_id,
                user_id=user_id,
                interaction_type=interaction_type,
                timestamp=current_time,
                input_data=input_data,
                output_data=output_data,
                context=InteractionContext(**context),
                result=InteractionResult(**result),
                status=InteractionStatus.COMPLETED if result.get('success') else InteractionStatus.FAILED,
                duration=duration,
                tags=tags or [],
                metadata={}
            )
            
            # 准备数据库数据
            db_data = {
                'interaction_id': interaction_record.interaction_id,
                'user_id': interaction_record.user_id,
                'interaction_type': interaction_record.interaction_type.value,
                'timestamp': interaction_record.timestamp,
                'input_data': json.dumps(interaction_record.input_data),
                'output_data': json.dumps(interaction_record.output_data),
                'context': json.dumps(asdict(interaction_record.context)),
                'result': json.dumps(asdict(interaction_record.result)),
                'status': interaction_record.status.value,
                'duration': interaction_record.duration,
                'tags': json.dumps(interaction_record.tags),
                'metadata': json.dumps(interaction_record.metadata)
            }
            
            # 插入数据库
            self.db.execute_insert(self.interactions_table, db_data)
            
            # 更新会话信息
            self._update_session_info(user_id, context.get('session_id'), interaction_record)
            
            # 更新缓存
            self._update_cache(interaction_record)
            
            self.logger.debug(f"Interaction recorded: {interaction_id} - {interaction_type.value}")
            return interaction_id
            
        except Exception as e:
            self.logger.error(f"Failed to record interaction: {str(e)}")
            raise
    
    def get_interaction(self, interaction_id: str) -> Optional[InteractionRecord]:
        """
        获取交互记录
        
        Args:
            interaction_id: 交互ID
            
        Returns:
            InteractionRecord: 交互记录，如果不存在返回None
        """
        try:
            # 先检查缓存
            for interaction in self._recent_interactions:
                if interaction.interaction_id == interaction_id:
                    return interaction
            
            query = f"SELECT * FROM {self.interactions_table} WHERE interaction_id = %s"
            results = self.db.execute_query(query, (interaction_id,))
            
            if not results:
                return None
            
            interaction_data = results[0]
            
            # 转换为InteractionRecord对象
            return InteractionRecord(
                interaction_id=interaction_data['interaction_id'],
                user_id=interaction_data['user_id'],
                interaction_type=InteractionType(interaction_data['interaction_type']),
                timestamp=interaction_data['timestamp'],
                input_data=json.loads(interaction_data['input_data']),
                output_data=json.loads(interaction_data['output_data']),
                context=InteractionContext(**json.loads(interaction_data['context'])),
                result=InteractionResult(**json.loads(interaction_data['result'])),
                status=InteractionStatus(interaction_data['status']),
                duration=interaction_data['duration'],
                tags=json.loads(interaction_data['tags']),
                metadata=json.loads(interaction_data['metadata'])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get interaction: {str(e)}")
            return None
    
    def get_user_interactions(self, user_id: str, start_time: datetime = None,
                            end_time: datetime = None, limit: int = 100) -> List[InteractionRecord]:
        """
        获取用户交互历史
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录限制
            
        Returns:
            List[InteractionRecord]: 交互记录列表
        """
        try:
            where_conditions = ["user_id = %s"]
            params = [user_id]
            
            if start_time:
                where_conditions.append("timestamp >= %s")
                params.append(start_time)
            
            if end_time:
                where_conditions.append("timestamp <= %s")
                params.append(end_time)
            
            where_clause = " AND ".join(where_conditions)
            query = f"""
            SELECT * FROM {self.interactions_table} 
            WHERE {where_clause} 
            ORDER BY timestamp DESC 
            LIMIT %s
            """
            params.append(limit)
            
            results = self.db.execute_query(query, tuple(params))
            
            interactions = []
            for row in results:
                interaction = InteractionRecord(
                    interaction_id=row['interaction_id'],
                    user_id=row['user_id'],
                    interaction_type=InteractionType(row['interaction_type']),
                    timestamp=row['timestamp'],
                    input_data=json.loads(row['input_data']),
                    output_data=json.loads(row['output_data']),
                    context=InteractionContext(**json.loads(row['context'])),
                    result=InteractionResult(**json.loads(row['result'])),
                    status=InteractionStatus(row['status']),
                    duration=row['duration'],
                    tags=json.loads(row['tags']),
                    metadata=json.loads(row['metadata'])
                )
                interactions.append(interaction)
            
            return interactions
            
        except Exception as e:
            self.logger.error(f"Failed to get user interactions: {str(e)}")
            return []
    
    def analyze_interaction_patterns(self, user_id: str, 
                                   time_window_days: int = 30) -> Dict[str, Any]:
        """
        分析用户交互模式
        
        Args:
            user_id: 用户ID
            time_window_days: 时间窗口（天）
            
        Returns:
            Dict: 交互模式分析结果
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_window_days)
            
            # 获取交互数据
            interactions = self.get_user_interactions(user_id, start_time, end_time, limit=1000)
            
            if not interactions:
                return {'error': 'No interaction data found'}
            
            analysis = {
                'user_id': user_id,
                'analysis_period': f"{time_window_days} days",
                'total_interactions': len(interactions),
                'interaction_types': {},
                'success_rates': {},
                'response_times': {},
                'time_patterns': {},
                'device_usage': {},
                'application_usage': {},
                'insights': []
            }
            
            # 按类型统计
            type_counts = defaultdict(int)
            type_success = defaultdict(int)
            type_durations = defaultdict(list)
            
            # 时间段统计
            hour_counts = defaultdict(int)
            day_counts = defaultdict(int)
            
            # 设备和应用使用统计
            device_usage = defaultdict(int)
            app_usage = defaultdict(int)
            
            for interaction in interactions:
                # 类型统计
                interaction_type = interaction.interaction_type.value
                type_counts[interaction_type] += 1
                
                if interaction.result.success:
                    type_success[interaction_type] += 1
                
                type_durations[interaction_type].append(interaction.duration)
                
                # 时间段统计
                hour = interaction.timestamp.hour
                hour_counts[hour] += 1
                
                day = interaction.timestamp.strftime('%A')
                day_counts[day] += 1
                
                # 设备和应用统计
                device = interaction.context.device_type
                app = interaction.context.application
                device_usage[device] += 1
                app_usage[app] += 1
            
            # 计算成功率
            for interaction_type, count in type_counts.items():
                success_count = type_success.get(interaction_type, 0)
                analysis['success_rates'][interaction_type] = success_count / count if count > 0 else 0
            
            # 计算平均响应时间
            for interaction_type, durations in type_durations.items():
                if durations:
                    analysis['response_times'][interaction_type] = {
                        'mean': statistics.mean(durations),
                        'median': statistics.median(durations),
                        'min': min(durations),
                        'max': max(durations)
                    }
            
            # 时间模式
            analysis['time_patterns'] = {
                'by_hour': dict(sorted(hour_counts.items())),
                'by_day': dict(sorted(day_counts.items(), 
                                    key=lambda x: ['Monday', 'Tuesday', 'Wednesday', 
                                                 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(x[0])))
            }
            
            # 设备和应用使用
            analysis['device_usage'] = dict(device_usage)
            analysis['application_usage'] = dict(app_usage)
            
            # 生成洞察
            analysis['insights'] = self._generate_interaction_insights(analysis, interactions)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze interaction patterns: {str(e)}")
            return {'error': str(e)}
    
    def create_session(self, user_id: str, device_type: str = "desktop",
                      application: str = "main", location: str = None) -> str:
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            device_type: 设备类型
            application: 应用名称
            location: 位置信息
            
        Returns:
            str: 会话ID
        """
        try:
            session_id = str(uuid.uuid4())
            start_time = datetime.now()
            
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'start_time': start_time,
                'device_type': device_type,
                'application': application,
                'location': location,
                'metadata': json.dumps({'created_by': 'system'})
            }
            
            self.db.execute_insert(self.sessions_table, session_data)
            
            self.logger.info(f"Session created: {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create session: {str(e)}")
            raise
    
    def end_session(self, session_id: str) -> bool:
        """
        结束用户会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 结束是否成功
        """
        try:
            # 获取会话信息
            query = f"SELECT * FROM {self.sessions_table} WHERE session_id = %s"
            results = self.db.execute_query(query, (session_id,))
            
            if not results:
                self.logger.warning(f"Session not found: {session_id}")
                return False
            
            session_data = results[0]
            end_time = datetime.now()
            start_time = session_data['start_time']
            duration = (end_time - start_time).total_seconds()
            
            # 计算会话统计
            interaction_stats = self._calculate_session_stats(session_id)
            
            update_data = {
                'end_time': end_time,
                'duration': duration,
                'interaction_count': interaction_stats['total_interactions'],
                'success_rate': interaction_stats['success_rate'],
                'average_response_time': interaction_stats['average_response_time']
            }
            
            affected = self.db.execute_update(
                self.sessions_table,
                update_data,
                "session_id = %s",
                (session_id,)
            )
            
            if affected > 0:
                self.logger.info(f"Session ended: {session_id}")
                return True
            else:
                self.logger.warning(f"Failed to end session: {session_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to end session: {str(e)}")
            return False
    
    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户会话列表
        
        Args:
            user_id: 用户ID
            limit: 返回记录限制
            
        Returns:
            List[Dict]: 会话列表
        """
        try:
            query = f"""
            SELECT * FROM {self.sessions_table} 
            WHERE user_id = %s 
            ORDER BY start_time DESC 
            LIMIT %s
            """
            
            results = self.db.execute_query(query, (user_id, limit))
            
            sessions = []
            for row in results:
                session = {
                    'session_id': row['session_id'],
                    'user_id': row['user_id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'duration': row['duration'],
                    'interaction_count': row['interaction_count'],
                    'device_type': row['device_type'],
                    'application': row['application'],
                    'location': row['location'],
                    'success_rate': row['success_rate'],
                    'average_response_time': row['average_response_time'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get user sessions: {str(e)}")
            return []
    
    def calculate_user_engagement(self, user_id: str, 
                                time_window_days: int = 30) -> Dict[str, Any]:
        """
        计算用户参与度指标
        
        Args:
            user_id: 用户ID
            time_window_days: 时间窗口（天）
            
        Returns:
            Dict: 参与度指标
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_window_days)
            
            # 获取交互数据
            interactions = self.get_user_interactions(user_id, start_time, end_time, limit=5000)
            
            if not interactions:
                return {'error': 'No interaction data found'}
            
            engagement = {
                'user_id': user_id,
                'time_period': f"{time_window_days} days",
                'total_interactions': len(interactions),
                'active_days': len(set(i.timestamp.date() for i in interactions)),
                'sessions_count': 0,
                'average_session_duration': 0,
                'success_rate': 0,
                'average_response_time': 0,
                'engagement_score': 0
            }
            
            # 计算成功率
            successful_interactions = sum(1 for i in interactions if i.result.success)
            engagement['success_rate'] = successful_interactions / len(interactions) if interactions else 0
            
            # 计算平均响应时间
            response_times = [i.duration for i in interactions]
            engagement['average_response_time'] = statistics.mean(response_times) if response_times else 0
            
            # 获取会话数据
            sessions = self.get_user_sessions(user_id, limit=100)
            engagement['sessions_count'] = len(sessions)
            
            # 计算平均会话时长
            session_durations = [s['duration'] for s in sessions if s['duration']]
            if session_durations:
                engagement['average_session_duration'] = statistics.mean(session_durations)
            
            # 计算参与度分数（综合指标）
            frequency_score = min(engagement['total_interactions'] / 100.0, 1.0) * 0.3
            consistency_score = min(engagement['active_days'] / time_window_days, 1.0) * 0.3
            success_score = engagement['success_rate'] * 0.2
            depth_score = min(engagement['sessions_count'] / 20.0, 1.0) * 0.2
            
            engagement['engagement_score'] = (frequency_score + consistency_score + 
                                            success_score + depth_score) * 100
            
            return engagement
            
        except Exception as e:
            self.logger.error(f"Failed to calculate user engagement: {str(e)}")
            return {'error': str(e)}
    
    def export_interaction_data(self, user_id: str, file_path: str, 
                              start_time: datetime = None, 
                              end_time: datetime = None) -> bool:
        """
        导出交互数据
        
        Args:
            user_id: 用户ID
            file_path: 导出文件路径
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 导出是否成功
        """
        try:
            import csv
            
            # 获取交互数据
            interactions = self.get_user_interactions(user_id, start_time, end_time, limit=10000)
            
            if not interactions:
                self.logger.warning(f"No interaction data found for user: {user_id}")
                return False
            
            # 准备导出数据
            export_data = []
            for interaction in interactions:
                export_record = {
                    'interaction_id': interaction.interaction_id,
                    'timestamp': interaction.timestamp.isoformat(),
                    'interaction_type': interaction.interaction_type.value,
                    'input_data': json.dumps(interaction.input_data, ensure_ascii=False),
                    'output_data': json.dumps(interaction.output_data, ensure_ascii=False),
                    'device_type': interaction.context.device_type,
                    'application': interaction.context.application,
                    'success': interaction.result.success,
                    'response_time': interaction.duration,
                    'confidence': interaction.result.confidence,
                    'tags': ','.join(interaction.tags)
                }
                export_data.append(export_record)
            
            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if export_data:
                    fieldnames = export_data[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(export_data)
            
            self.logger.info(f"Exported {len(export_data)} interactions to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export interaction data: {str(e)}")
            return False
    
    def cleanup_old_data(self, retention_days: int = 365) -> int:
        """
        清理旧数据
        
        Args:
            retention_days: 保留天数
            
        Returns:
            int: 清理的记录数量
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            # 清理交互历史
            query = f"DELETE FROM {self.interactions_table} WHERE timestamp < %s"
            params = (cutoff_time,)
            
            affected_interactions = self.db.execute_update(
                self.interactions_table,
                {},
                "timestamp < %s",
                params
            )
            
            # 清理会话数据
            query = f"DELETE FROM {self.sessions_table} WHERE start_time < %s"
            affected_sessions = self.db.execute_update(
                self.sessions_table,
                {},
                "start_time < %s",
                params
            )
            
            total_affected = affected_interactions + affected_sessions
            
            self.logger.info(f"Cleaned up {total_affected} old records (interactions: {affected_interactions}, sessions: {affected_sessions})")
            return total_affected
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {str(e)}")
            return 0
    
    def _update_session_info(self, user_id: str, session_id: str, 
                           interaction: InteractionRecord):
        """更新会话信息"""
        try:
            if not session_id:
                return
            
            # 检查会话是否存在
            query = f"SELECT * FROM {self.sessions_table} WHERE session_id = %s"
            results = self.db.execute_query(query, (session_id,))
            
            if not results:
                # 创建新会话
                self.create_session(
                    user_id=user_id,
                    device_type=interaction.context.device_type,
                    application=interaction.context.application,
                    location=interaction.context.location
                )
            
        except Exception as e:
            self.logger.debug(f"Failed to update session info: {str(e)}")
    
    def _calculate_session_stats(self, session_id: str) -> Dict[str, Any]:
        """计算会话统计"""
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_interactions,
                AVG(duration) as average_response_time,
                SUM(CASE WHEN result->>'success' = 'true' THEN 1 ELSE 0 END) as successful_interactions
            FROM {self.interactions_table} 
            WHERE context->>'session_id' = %s
            """
            
            results = self.db.execute_query(query, (session_id,))
            
            if results and results[0]['total_interactions']:
                stats = results[0]
                success_rate = stats['successful_interactions'] / stats['total_interactions']
                
                return {
                    'total_interactions': stats['total_interactions'],
                    'average_response_time': stats['average_response_time'] or 0.0,
                    'success_rate': success_rate
                }
            
            return {
                'total_interactions': 0,
                'average_response_time': 0.0,
                'success_rate': 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate session stats: {str(e)}")
            return {
                'total_interactions': 0,
                'average_response_time': 0.0,
                'success_rate': 0.0
            }
    
    def _update_cache(self, interaction: InteractionRecord):
        """更新缓存"""
        self._recent_interactions.append(interaction)
        
        # 保持缓存大小
        if len(self._recent_interactions) > self.cache_size:
            self._recent_interactions = self._recent_interactions[-self.cache_size:]
    
    def _generate_interaction_insights(self, analysis: Dict[str, Any], 
                                     interactions: List[InteractionRecord]) -> List[str]:
        """生成交互洞察"""
        insights = []
        
        # 分析最常用的交互类型
        if analysis['interaction_types']:
            most_common_type = max(analysis['interaction_types'].items(), key=lambda x: x[1])
            insights.append(f"最常用的交互方式: {most_common_type[0]} (使用{most_common_type[1]}次)")
        
        # 分析成功率
        overall_success_rate = analysis.get('success_rate', 0)
        if overall_success_rate > 0.9:
            insights.append("交互成功率很高，系统运行稳定")
        elif overall_success_rate < 0.7:
            insights.append("交互成功率较低，建议检查系统配置")
        
        # 分析响应时间
        response_times = analysis.get('response_times', {})
        if response_times:
            avg_response_time = statistics.mean([rt['mean'] for rt in response_times.values()])
            if avg_response_time > 5.0:
                insights.append(f"平均响应时间较长 ({avg_response_time:.1f}s)，建议优化系统性能")
        
        # 分析使用模式
        time_patterns = analysis.get('time_patterns', {})
        if time_patterns.get('by_hour'):
            peak_hour = max(time_patterns['by_hour'].items(), key=lambda x: x[1])[0]
            insights.append(f"最活跃时段: {peak_hour}时")
        
        return insights

