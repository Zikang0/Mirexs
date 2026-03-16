"""
交互日志模块 - 记录用户交互
负责记录用户与系统的所有交互行为
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class InteractionType(Enum):
    VOICE_INPUT = "voice_input"
    TEXT_INPUT = "text_input"
    GESTURE_INPUT = "gesture_input"
    VISUAL_INPUT = "visual_input"
    VOICE_OUTPUT = "voice_output"
    VISUAL_OUTPUT = "visual_output"
    HAPTIC_OUTPUT = "haptic_output"
    SYSTEM_RESPONSE = "system_response"

class InteractionChannel(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    WEB = "web"
    VOICE_ASSISTANT = "voice_assistant"
    AR_VR = "ar_vr"

@dataclass
class InteractionRecord:
    session_id: str
    interaction_id: str
    user_id: Optional[str]
    interaction_type: InteractionType
    channel: InteractionChannel
    timestamp: datetime
    content: Dict[str, Any]
    response: Optional[Dict[str, Any]]
    duration_ms: Optional[float]

class InteractionLogger:
    """交互日志记录器"""
    
    def __init__(self, log_dir: str = "logs/interaction"):
        self.log_dir = log_dir
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._setup_logging()
    
    def _setup_logging(self):
        """配置交互日志"""
        import os
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 交互日志记录器
        self.logger = logging.getLogger("interaction")
        self.logger.setLevel(logging.INFO)
        
        # 交互日志文件处理器
        log_file = f"{self.log_dir}/interaction.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        
        formatter = logging.Formatter(
            '%(asctime)s - INTERACTION - %(session_id)s - %(interaction_type)s - %(user_id)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def start_session(self, 
                     user_id: Optional[str] = None,
                     channel: InteractionChannel = InteractionChannel.DESKTOP,
                     device_info: Optional[Dict[str, Any]] = None) -> str:
        """开始新的交互会话"""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel.value,
            "start_time": datetime.now().isoformat(),
            "device_info": device_info or {},
            "interaction_count": 0,
            "total_duration_ms": 0
        }
        
        self.sessions[session_id] = session_data
        
        # 记录会话开始
        session_log = {
            "event": "session_start",
            "session_id": session_id,
            "user_id": user_id,
            "channel": channel.value,
            "timestamp": datetime.now().isoformat(),
            "device_info": device_info
        }
        self._write_interaction_log(session_log)
        
        self.logger.info(f"会话开始: {session_id}", extra={
            "session_id": session_id,
            "interaction_type": "session_start",
            "user_id": user_id
        })
        
        return session_id
    
    def end_session(self, session_id: str, reason: str = "user_exit"):
        """结束交互会话"""
        if session_id not in self.sessions:
            return
        
        session_data = self.sessions[session_id]
        session_data["end_time"] = datetime.now().isoformat()
        session_data["end_reason"] = reason
        
        # 记录会话结束
        session_log = {
            "event": "session_end",
            "session_id": session_id,
            "user_id": session_data["user_id"],
            "channel": session_data["channel"],
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": self._calculate_session_duration(session_data),
            "interaction_count": session_data["interaction_count"],
            "reason": reason
        }
        self._write_interaction_log(session_log)
        
        self.logger.info(f"会话结束: {session_id}", extra={
            "session_id": session_id,
            "interaction_type": "session_end",
            "user_id": session_data["user_id"]
        })
        
        # 从活动会话中移除
        del self.sessions[session_id]
    
    def log_interaction(self,
                       session_id: str,
                       interaction_type: InteractionType,
                       content: Dict[str, Any],
                       response: Optional[Dict[str, Any]] = None,
                       duration_ms: Optional[float] = None,
                       user_id: Optional[str] = None) -> str:
        """记录交互事件"""
        
        if session_id not in self.sessions:
            # 如果没有会话，创建一个匿名会话
            session_id = self.start_session(user_id)
        
        interaction_id = str(uuid.uuid4())
        session_data = self.sessions[session_id]
        
        # 更新会话统计
        session_data["interaction_count"] += 1
        if duration_ms:
            session_data["total_duration_ms"] += duration_ms
        
        record = InteractionRecord(
            session_id=session_id,
            interaction_id=interaction_id,
            user_id=user_id or session_data["user_id"],
            interaction_type=interaction_type,
            channel=InteractionChannel(session_data["channel"]),
            timestamp=datetime.now(),
            content=content,
            response=response,
            duration_ms=duration_ms
        )
        
        # 写入结构化日志
        self._write_interaction_record(record)
        
        # 记录到文本日志
        log_message = f"交互记录: {interaction_type.value} - 内容: {json.dumps(content, ensure_ascii=False)[:100]}..."
        extra_info = {
            "session_id": session_id,
            "interaction_type": interaction_type.value,
            "user_id": user_id or session_data["user_id"]
        }
        self.logger.info(log_message, extra=extra_info)
        
        return interaction_id
    
    def log_voice_input(self, 
                       session_id: str,
                       audio_data: Dict[str, Any],
                       transcription: str,
                       confidence: float,
                       duration_ms: float) -> str:
        """记录语音输入"""
        content = {
            "audio_metadata": audio_data,
            "transcription": transcription,
            "confidence": confidence,
            "input_type": "voice"
        }
        
        return self.log_interaction(
            session_id,
            InteractionType.VOICE_INPUT,
            content,
            duration_ms=duration_ms
        )
    
    def log_text_input(self, 
                      session_id: str,
                      text: str,
                      input_method: str,
                      source: str) -> str:
        """记录文本输入"""
        content = {
            "text": text,
            "input_method": input_method,
            "source": source,
            "input_type": "text"
        }
        
        return self.log_interaction(
            session_id,
            InteractionType.TEXT_INPUT,
            content
        )
    
    def log_system_response(self,
                          session_id: str,
                          interaction_id: str,
                          response_type: str,
                          content: Dict[str, Any],
                          processing_time_ms: float) -> str:
        """记录系统响应"""
        response_content = {
            "response_type": response_type,
            "content": content,
            "processing_time_ms": processing_time_ms,
            "related_interaction": interaction_id
        }
        
        return self.log_interaction(
            session_id,
            InteractionType.SYSTEM_RESPONSE,
            {},
            response_content,
            duration_ms=processing_time_ms
        )
    
    def log_3d_avatar_action(self,
                           session_id: str,
                           action_type: str,
                           emotion: str,
                           animation: str,
                           duration_ms: float) -> str:
        """记录3D虚拟形象动作"""
        content = {
            "action_type": action_type,
            "emotion": emotion,
            "animation": animation,
            "target": "3d_avatar"
        }
        
        return self.log_interaction(
            session_id,
            InteractionType.VISUAL_OUTPUT,
            content,
            duration_ms=duration_ms
        )
    
    def _calculate_session_duration(self, session_data: Dict[str, Any]) -> float:
        """计算会话持续时间"""
        start_time = datetime.fromisoformat(session_data["start_time"])
        if "end_time" in session_data:
            end_time = datetime.fromisoformat(session_data["end_time"])
        else:
            end_time = datetime.now()
        
        return (end_time - start_time).total_seconds()
    
    def _write_interaction_log(self, log_data: Dict[str, Any]):
        """写入交互日志"""
        import os
        log_file = f"{self.log_dir}/interaction_sessions.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + '\n')
    
    def _write_interaction_record(self, record: InteractionRecord):
        """写入交互记录"""
        import os
        log_file = f"{self.log_dir}/interaction_details.jsonl"
        
        log_entry = {
            "session_id": record.session_id,
            "interaction_id": record.interaction_id,
            "user_id": record.user_id,
            "interaction_type": record.interaction_type.value,
            "channel": record.channel.value,
            "timestamp": record.timestamp.isoformat(),
            "content": record.content,
            "response": record.response,
            "duration_ms": record.duration_ms
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def get_user_interaction_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取用户交互历史"""
        import os
        interactions = []
        
        log_file = f"{self.log_dir}/interaction_details.jsonl"
        if not os.path.exists(log_file):
            return interactions
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    interaction = json.loads(line.strip())
                    if interaction.get('user_id') == user_id:
                        interactions.append(interaction)
                except json.JSONDecodeError:
                    continue
        
        # 按时间倒序排列并限制数量
        interactions.sort(key=lambda x: x['timestamp'], reverse=True)
        return interactions[:limit]
    
    def analyze_interaction_patterns(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """分析交互模式"""
        import os
        from collections import Counter
        
        if not os.path.exists(f"{self.log_dir}/interaction_details.jsonl"):
            return {}
        
        interaction_types = []
        channels = []
        session_durations = []
        
        # 读取会话数据
        session_file = f"{self.log_dir}/interaction_sessions.jsonl"
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        session = json.loads(line.strip())
                        if session['event'] == 'session_end':
                            if user_id is None or session.get('user_id') == user_id:
                                session_durations.append(session.get('duration_seconds', 0))
                    except json.JSONDecodeError:
                        continue
        
        # 读取交互数据
        with open(f"{self.log_dir}/interaction_details.jsonl", 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    interaction = json.loads(line.strip())
                    if user_id is None or interaction.get('user_id') == user_id:
                        interaction_types.append(interaction['interaction_type'])
                        channels.append(interaction['channel'])
                except json.JSONDecodeError:
                    continue
        
        analysis = {
            "total_interactions": len(interaction_types),
            "interaction_type_distribution": dict(Counter(interaction_types)),
            "channel_distribution": dict(Counter(channels)),
            "average_session_duration": sum(session_durations) / len(session_durations) if session_durations else 0,
            "preferred_channel": max(Counter(channels).items(), key=lambda x: x[1])[0] if channels else None
        }
        
        return analysis

# 全局交互日志实例
interaction_logger = InteractionLogger()

