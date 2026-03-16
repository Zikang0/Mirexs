"""
会话数据模块 - 临时会话数据管理
负责管理用户会话的临时数据存储
"""

import time
import uuid
import json
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from pathlib import Path

class SessionState(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    TERMINATED = "terminated"

@dataclass
class SessionData:
    session_id: str
    user_id: Optional[str]
    created_at: float
    last_accessed: float
    expires_at: float
    state: SessionState
    data: Dict[str, Any]
    metadata: Dict[str, Any]

class SessionManager:
    """会话数据管理器"""
    
    def __init__(self, session_timeout: int = 1800, cleanup_interval: int = 300):
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        self.sessions: Dict[str, SessionData] = {}
        self.lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            "sessions_created": 0,
            "sessions_destroyed": 0,
            "total_active_sessions": 0,
            "data_operations": 0
        }
        
        # 自动清理线程
        self.cleanup_thread = None
        self.running = False
    
    def start_cleanup_daemon(self):
        """启动自动清理守护进程"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def stop_cleanup_daemon(self):
        """停止自动清理守护进程"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
    
    def create_session(self, user_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            data: 初始会话数据
            
        Returns:
            会话ID
        """
        with self.lock:
            session_id = str(uuid.uuid4())
            current_time = time.time()
            
            session_data = SessionData(
                session_id=session_id,
                user_id=user_id,
                created_at=current_time,
                last_accessed=current_time,
                expires_at=current_time + self.session_timeout,
                state=SessionState.ACTIVE,
                data=data or {},
                metadata={
                    "ip_address": None,
                    "user_agent": None,
                    "device_info": {}
                }
            )
            
            self.sessions[session_id] = session_data
            self.stats["sessions_created"] += 1
            self.stats["total_active_sessions"] = len(self.sessions)
            
            return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话数据或None
        """
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            session = self.sessions[session_id]
            
            # 检查会话是否过期
            if time.time() > session.expires_at:
                session.state = SessionState.EXPIRED
                return None
            
            # 更新访问时间
            session.last_accessed = time.time()
            session.expires_at = time.time() + self.session_timeout
            
            return session
    
    def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        设置会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            value: 数据值
            
        Returns:
            是否设置成功
        """
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.data[key] = value
            self.stats["data_operations"] += 1
            return True
    
    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            default: 默认值
            
        Returns:
            数据值或默认值
        """
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return default
            
            self.stats["data_operations"] += 1
            return session.data.get(key, default)
    
    def delete_session_data(self, session_id: str, key: str) -> bool:
        """
        删除会话数据
        
        Args:
            session_id: 会话ID
            key: 数据键
            
        Returns:
            是否删除成功
        """
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return False
            
            if key in session.data:
                del session.data[key]
                self.stats["data_operations"] += 1
                return True
            
            return False
    
    def update_session_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新会话元数据
        
        Args:
            session_id: 会话ID
            metadata: 元数据
            
        Returns:
            是否更新成功
        """
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.metadata.update(metadata)
            return True
    
    def destroy_session(self, session_id: str) -> bool:
        """
        销毁会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否销毁成功
        """
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            session.state = SessionState.TERMINATED
            
            del self.sessions[session_id]
            self.stats["sessions_destroyed"] += 1
            self.stats["total_active_sessions"] = len(self.sessions)
            
            return True
    
    def renew_session(self, session_id: str) -> bool:
        """
        续约会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否续约成功
        """
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return False
            
            session.expires_at = time.time() + self.session_timeout
            return True
    
    def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话列表
        """
        with self.lock:
            user_sessions = []
            current_time = time.time()
            
            for session in self.sessions.values():
                if session.user_id == user_id and session.expires_at > current_time:
                    user_sessions.append(session)
            
            return user_sessions
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        with self.lock:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, session in self.sessions.items():
                if session.expires_at <= current_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self.destroy_session(session_id)
            
            return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        with self.lock:
            current_time = time.time()
            active_sessions = 0
            expired_sessions = 0
            
            for session in self.sessions.values():
                if session.expires_at > current_time:
                    active_sessions += 1
                else:
                    expired_sessions += 1
            
            total_data_size = sum(len(str(data)) for session in self.sessions.values() 
                                for data in session.data.values())
            
            return {
                **self.stats,
                "current_active_sessions": active_sessions,
                "current_expired_sessions": expired_sessions,
                "average_session_duration": self._calculate_average_duration(),
                "total_data_size_kb": total_data_size / 1024,
                "average_data_per_session": total_data_size / len(self.sessions) if self.sessions else 0
            }
    
    def _calculate_average_duration(self) -> float:
        """计算平均会话持续时间"""
        if not self.sessions:
            return 0
        
        total_duration = 0
        current_time = time.time()
        
        for session in self.sessions.values():
            duration = min(session.expires_at, current_time) - session.created_at
            total_duration += duration
        
        return total_duration / len(self.sessions)
    
    def _cleanup_worker(self):
        """清理工作线程"""
        while self.running:
            time.sleep(self.cleanup_interval)
            expired_count = self.cleanup_expired_sessions()
            if expired_count > 0:
                print(f"自动清理了 {expired_count} 个过期会话")
    
    def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """导出会话数据"""
        with self.lock:
            session = self.get_session(session_id)
            if not session:
                return None
            
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "created_at": session.created_at,
                "last_accessed": session.last_accessed,
                "expires_at": session.expires_at,
                "state": session.state.value,
                "data": session.data,
                "metadata": session.metadata
            }
    
    def import_session_data(self, session_data: Dict[str, Any]) -> bool:
        """导入会话数据"""
        with self.lock:
            try:
                session = SessionData(
                    session_id=session_data["session_id"],
                    user_id=session_data["user_id"],
                    created_at=session_data["created_at"],
                    last_accessed=session_data["last_accessed"],
                    expires_at=session_data["expires_at"],
                    state=SessionState(session_data["state"]),
                    data=session_data["data"],
                    metadata=session_data["metadata"]
                )
                
                self.sessions[session.session_id] = session
                return True
                
            except Exception as e:
                print(f"导入会话数据失败: {e}")
                return False

# 全局会话管理器实例
session_manager = SessionManager()

# 启动自动清理
session_manager.start_cleanup_daemon()

