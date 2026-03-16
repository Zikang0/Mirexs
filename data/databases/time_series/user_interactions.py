"""
用户交互模块 - 管理用户交互数据的存储和分析
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from .influxdb_integration import InfluxDBIntegration

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

class UserInteractions:
    """用户交互管理器"""
    
    def __init__(self, influx_client: InfluxDBIntegration, config: Dict[str, Any]):
        """
        初始化用户交互管理器
        
        Args:
            influx_client: InfluxDB客户端
            config: 配置字典
        """
        self.influx_client = influx_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 交互数据配置
        self.interactions_bucket = config.get('interactions_bucket', 'mirexs_interactions')
        self.session_timeout = config.get('session_timeout', 1800)  # 30分钟
        self.enable_analytics = config.get('enable_analytics', True)
        
        # 会话管理
        self._active_sessions = {}
        
    def record_interaction(self,
                         user_id: str,
                         interaction_type: InteractionType,
                         data: Dict[str, Any],
                         session_id: Optional[str] = None,
                         timestamp: Optional[datetime] = None) -> str:
        """
        记录用户交互
        
        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            data: 交互数据
            session_id: 会话ID（可选）
            timestamp: 时间戳（可选）
            
        Returns:
            str: 交互ID
        """
        try:
            # 生成交互ID
            interaction_id = str(uuid.uuid4())
            
            # 管理会话
            if not session_id:
                session_id = self._get_or_create_session(user_id)
            
            # 准备字段数据
            fields = {
                "interaction_id": interaction_id,
                "user_id": user_id,
                "session_id": session_id,
                "interaction_type": interaction_type.value,
                "data": json.dumps(data, ensure_ascii=False)
            }
            
            # 添加交互特定数据
            if 'duration' in data:
                fields["duration"] = data['duration']
            if 'success' in data:
                fields["success"] = data['success']
            if 'confidence' in data:
                fields["confidence"] = data['confidence']
            
            # 标签
            tags = {
                "interaction_type": interaction_type.value,
                "user_id": user_id,
                "session_id": session_id
            }
            
            # 写入交互数据
            success = self.influx_client.write_metric(
                measurement="user_interactions",
                fields=fields,
                tags=tags,
                timestamp=timestamp,
                bucket=self.interactions_bucket
            )
            
            if success:
                self.logger.debug(f"Recorded interaction: {interaction_type.value} for user {user_id}")
                
                # 更新会话活动时间
                self._update_session_activity(session_id)
                
                # 记录分析数据（如果启用）
                if self.enable_analytics:
                    self._record_analytics(user_id, interaction_type, data, session_id)
            else:
                self.logger.error(f"Failed to record interaction for user {user_id}")
            
            return interaction_id
            
        except Exception as e:
            self.logger.error(f"Error recording interaction: {str(e)}")
            return ""
    
    def record_voice_interaction(self,
                               user_id: str,
                               command: str,
                               response: str,
                               duration: float,
                               confidence: float,
                               success: bool = True,
                               session_id: Optional[str] = None) -> str:
        """
        记录语音交互
        
        Args:
            user_id: 用户ID
            command: 语音命令
            response: 系统响应
            duration: 交互时长
            confidence: 识别置信度
            success: 是否成功
            session_id: 会话ID
            
        Returns:
            str: 交互ID
        """
        data = {
            "command": command,
            "response": response,
            "duration": duration,
            "confidence": confidence,
            "success": success,
            "input_modality": "voice"
        }
        
        return self.record_interaction(
            user_id=user_id,
            interaction_type=InteractionType.VOICE_COMMAND,
            data=data,
            session_id=session_id
        )
    
    def record_text_interaction(self,
                              user_id: str,
                              input_text: str,
                              response: str,
                              response_time: float,
                              success: bool = True,
                              session_id: Optional[str] = None) -> str:
        """
        记录文本交互
        
        Args:
            user_id: 用户ID
            input_text: 输入文本
            response: 系统响应
            response_time: 响应时间
            success: 是否成功
            session_id: 会话ID
            
        Returns:
            str: 交互ID
        """
        data = {
            "input_text": input_text,
            "response": response,
            "response_time": response_time,
            "success": success,
            "input_modality": "text"
        }
        
        return self.record_interaction(
            user_id=user_id,
            interaction_type=InteractionType.TEXT_INPUT,
            data=data,
            session_id=session_id
        )
    
    def record_gesture_interaction(self,
                                 user_id: str,
                                 gesture_type: str,
                                 coordinates: Dict[str, float],
                                 duration: float,
                                 success: bool = True,
                                 session_id: Optional[str] = None) -> str:
        """
        记录手势交互
        
        Args:
            user_id: 用户ID
            gesture_type: 手势类型
            coordinates: 坐标信息
            duration: 手势时长
            success: 是否成功识别
            session_id: 会话ID
            
        Returns:
            str: 交互ID
        """
        data = {
            "gesture_type": gesture_type,
            "coordinates": coordinates,
            "duration": duration,
            "success": success,
            "input_modality": "gesture"
        }
        
        return self.record_interaction(
            user_id=user_id,
            interaction_type=InteractionType.GESTURE,
            data=data,
            session_id=session_id
        )
    
    def _get_or_create_session(self, user_id: str) -> str:
        """
        获取或创建用户会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 会话ID
        """
        # 检查是否有活跃会话
        current_time = datetime.utcnow()
        
        for session_id, session_data in self._active_sessions.items():
            if (session_data['user_id'] == user_id and 
                (current_time - session_data['last_activity']).total_seconds() < self.session_timeout):
                return session_id
        
        # 创建新会话
        new_session_id = str(uuid.uuid4())
        self._active_sessions[new_session_id] = {
            'user_id': user_id,
            'start_time': current_time,
            'last_activity': current_time,
            'interaction_count': 0
        }
        
        # 记录会话开始
        self.record_interaction(
            user_id=user_id,
            interaction_type=InteractionType.SYSTEM_EVENT,
            data={"event": "session_start", "session_id": new_session_id},
            session_id=new_session_id
        )
        
        return new_session_id
    
    def _update_session_activity(self, session_id: str):
        """更新会话活动时间"""
        if session_id in self._active_sessions:
            self._active_sessions[session_id]['last_activity'] = datetime.utcnow()
            self._active_sessions[session_id]['interaction_count'] += 1
    
    def end_session(self, session_id: str, user_id: Optional[str] = None) -> bool:
        """
        结束用户会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选，用于验证）
            
        Returns:
            bool: 结束是否成功
        """
        try:
            if session_id not in self._active_sessions:
                self.logger.warning(f"Session {session_id} not found or already ended")
                return False
            
            session_data = self._active_sessions[session_id]
            
            # 验证用户ID
            if user_id and session_data['user_id'] != user_id:
                self.logger.error(f"User ID mismatch for session {session_id}")
                return False
            
            # 记录会话结束
            session_duration = (datetime.utcnow() - session_data['start_time']).total_seconds()
            
            self.record_interaction(
                user_id=session_data['user_id'],
                interaction_type=InteractionType.SYSTEM_EVENT,
                data={
                    "event": "session_end",
                    "session_id": session_id,
                    "duration": session_duration,
                    "interaction_count": session_data['interaction_count']
                },
                session_id=session_id
            )
            
            # 从活跃会话中移除
            del self._active_sessions[session_id]
            
            self.logger.info(f"Ended session {session_id} with {session_data['interaction_count']} interactions")
            return True
            
        except Exception as e:
            self.logger.error(f"Error ending session: {str(e)}")
            return False
    
    def _record_analytics(self, 
                         user_id: str, 
                         interaction_type: InteractionType, 
                         data: Dict[str, Any],
                         session_id: str):
        """记录分析数据"""
        try:
            analytics_data = {
                "user_id": user_id,
                "session_id": session_id,
                "interaction_type": interaction_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 添加交互特定分析数据
            if 'duration' in data:
                analytics_data["duration"] = data['duration']
            if 'success' in data:
                analytics_data["success"] = data['success']
            if 'confidence' in data:
                analytics_data["confidence"] = data['confidence']
            
            # 写入分析数据
            self.influx_client.write_metric(
                measurement="interaction_analytics",
                fields=analytics_data,
                tags={
                    "user_id": user_id,
                    "interaction_type": interaction_type.value
                },
                bucket=self.interactions_bucket
            )
            
        except Exception as e:
            self.logger.debug(f"Error recording analytics: {str(e)}")
    
    def get_user_interactions(self,
                            user_id: str,
                            start_time: str = "-7d",
                            end_time: str = "now()",
                            interaction_type: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        获取用户交互历史
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            interaction_type: 交互类型过滤
            
        Returns:
            List: 交互记录列表
        """
        try:
            query_parts = [
                f'from(bucket: "{self.interactions_bucket}")',
                f'|> range(start: {start_time}, stop: {end_time})',
                '|> filter(fn: (r) => r._measurement == "user_interactions")',
                f'|> filter(fn: (r) => r.user_id == "{user_id}")'
            ]
            
            if interaction_type:
                query_parts.append(f'|> filter(fn: (r) => r.interaction_type == "{interaction_type}")')
            
            query = '\n  '.join(query_parts)
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                interactions = []
                for _, row in df.iterrows():
                    interaction = {
                        "timestamp": row.get('_time', ''),
                        "interaction_id": row.get('interaction_id', ''),
                        "interaction_type": row.get('interaction_type', ''),
                        "session_id": row.get('session_id', ''),
                        "user_id": row.get('user_id', '')
                    }
                    
                    # 解析交互数据
                    if 'data' in row and row['data']:
                        try:
                            interaction["data"] = json.loads(row['data'])
                        except:
                            interaction["data"] = row['data']
                    
                    # 添加数值字段
                    for field in ['duration', 'confidence', 'success']:
                        if field in row:
                            interaction[field] = row[field]
                    
                    interactions.append(interaction)
                
                return sorted(interactions, key=lambda x: x['timestamp'], reverse=True)
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting user interactions: {str(e)}")
            return None
    
    def get_session_analytics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话分析数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 会话分析数据
        """
        try:
            query = f'''
            from(bucket: "{self.interactions_bucket}")
              |> range(start: -24h, stop: now())
              |> filter(fn: (r) => r._measurement == "user_interactions")
              |> filter(fn: (r) => r.session_id == "{session_id}")
            '''
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                analytics = {
                    "session_id": session_id,
                    "total_interactions": len(df),
                    "interaction_types": {},
                    "success_rate": 0,
                    "average_duration": 0,
                    "timeline": []
                }
                
                success_count = 0
                total_duration = 0
                duration_count = 0
                
                for _, row in df.iterrows():
                    # 统计交互类型
                    interaction_type = row.get('interaction_type', 'unknown')
                    analytics["interaction_types"][interaction_type] = \
                        analytics["interaction_types"].get(interaction_type, 0) + 1
                    
                    # 统计成功率
                    if 'success' in row and row['success']:
                        success_count += 1
                    
                    # 统计时长
                    if 'duration' in row:
                        total_duration += row['duration']
                        duration_count += 1
                    
                    # 构建时间线
                    analytics["timeline"].append({
                        "timestamp": row.get('_time', ''),
                        "type": interaction_type,
                        "success": row.get('success', False)
                    })
                
                # 计算统计值
                if analytics["total_interactions"] > 0:
                    analytics["success_rate"] = success_count / analytics["total_interactions"]
                
                if duration_count > 0:
                    analytics["average_duration"] = total_duration / duration_count
                
                return analytics
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting session analytics: {str(e)}")
            return None
    
    def get_user_behavior_patterns(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户行为模式
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户行为模式
        """
        try:
            # 获取最近30天的交互数据
            query = f'''
            from(bucket: "{self.interactions_bucket}")
              |> range(start: -30d, stop: now())
              |> filter(fn: (r) => r._measurement == "user_interactions")
              |> filter(fn: (r) => r.user_id == "{user_id}")
            '''
            
            df = self.influx_client.query_metrics(query)
            
            if df is not None and not df.empty:
                patterns = {
                    "user_id": user_id,
                    "analysis_period": "30d",
                    "preferred_interaction_types": {},
                    "activity_times": {},
                    "success_rates": {},
                    "frequent_commands": {}
                }
                
                # 分析交互类型偏好
                interaction_counts = df['interaction_type'].value_counts().to_dict()
                patterns["preferred_interaction_types"] = interaction_counts
                
                # 分析活跃时间段
                df['hour'] = pd.to_datetime(df['_time']).dt.hour
                hour_counts = df['hour'].value_counts().sort_index().to_dict()
                patterns["activity_times"] = hour_counts
                
                # 分析成功率
                for interaction_type in df['interaction_type'].unique():
                    type_data = df[df['interaction_type'] == interaction_type]
                    if 'success' in type_data.columns:
                        success_rate = type_data['success'].mean()
                        patterns["success_rates"][interaction_type] = success_rate
                
                return patterns
            
            return {"user_id": user_id, "message": "No interaction data found"}
            
        except Exception as e:
            self.logger.error(f"Error analyzing user behavior patterns: {str(e)}")
            return None
    
    def cleanup_old_interactions(self, older_than_days: int = 365) -> bool:
        """
        清理旧的交互数据
        
        Args:
            older_than_days: 清理多少天前的数据
            
        Returns:
            bool: 清理是否成功
        """
        try:
            return self.influx_client.delete_old_data("user_interactions", older_than_days)
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old interactions: {str(e)}")
            return False

