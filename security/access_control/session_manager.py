"""
会话管理模块 - 管理用户会话
处理会话的创建、验证、刷新和销毁
"""

import asyncio
import logging
import time
import json
import secrets
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from ...utils.security_utilities.token_utils import TokenUtils
from ..security_monitoring.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"  # 活跃
    IDLE = "idle"  # 空闲
    EXPIRED = "expired"  # 过期
    REVOKED = "revoked"  # 吊销
    SUSPENDED = "suspended"  # 挂起


@dataclass
class Session:
    """会话数据模型"""
    session_id: str
    user_id: str
    status: SessionStatus
    created_at: float
    last_accessed_at: float
    expires_at: float
    auth_method: str  # 认证方法
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    refresh_token: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionCreateResult:
    """会话创建结果"""
    session_id: str
    user_id: str
    token: str
    refresh_token: str
    expires_at: float
    created_at: float


class SessionManager:
    """
    会话管理器 - 管理用户会话生命周期
    支持会话创建、验证、刷新、销毁和清理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化会话管理器
        
        Args:
            config: 配置参数
        """
        self.config = config or self._load_default_config()
        
        # 存储会话
        self.sessions: Dict[str, Session] = {}
        
        # 用户会话索引
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        
        # 刷新令牌映射
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> session_id
        
        # 存储路径
        self.storage_path = Path(self.config.get("storage_path", "data/security/sessions"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化依赖
        self.token_utils = TokenUtils()
        self.audit_logger = AuditLogger()
        
        # 加载已有会话
        self._load_sessions()
        
        # 启动清理任务
        self._cleanup_task = None
        
        logger.info(f"会话管理器初始化完成，存储路径: {self.storage_path}")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "storage_path": "data/security/sessions",
            "session_timeout_seconds": 3600,  # 1小时
            "idle_timeout_seconds": 1800,  # 30分钟
            "refresh_token_expiry_days": 7,  # 7天
            "max_sessions_per_user": 10,
            "enable_persistence": True,
            "cleanup_interval_minutes": 60,
            "token_algorithm": "HS256"
        }
    
    def _load_sessions(self) -> None:
        """从存储加载会话"""
        try:
            sessions_file = self.storage_path / "sessions.json"
            if not sessions_file.exists():
                return
            
            with open(sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
            
            for session_id, session_dict in sessions_data.items():
                session_dict["status"] = SessionStatus(session_dict["status"])
                session = Session(**session_dict)
                self.sessions[session_id] = session
                
                # 更新索引
                if session.user_id not in self.user_sessions:
                    self.user_sessions[session.user_id] = []
                self.user_sessions[session.user_id].append(session_id)
                
                if session.refresh_token:
                    self.refresh_tokens[session.refresh_token] = session_id
            
            logger.info(f"加载了 {len(self.sessions)} 个会话")
        except Exception as e:
            logger.error(f"加载会话失败: {str(e)}")
    
    def _save_sessions(self) -> None:
        """保存会话到存储"""
        if not self.config["enable_persistence"]:
            return
        
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                session_dict = session.__dict__.copy()
                session_dict["status"] = session.status.value
                sessions_data[session_id] = session_dict
            
            with open(self.storage_path / "sessions.json", 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"保存了 {len(self.sessions)} 个会话")
        except Exception as e:
            logger.error(f"保存会话失败: {str(e)}")
    
    async def create_session(
        self,
        user_id: str,
        auth_method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_id: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionCreateResult]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            auth_method: 认证方法
            ip_address: IP地址
            user_agent: 用户代理
            device_id: 设备ID
            permissions: 权限列表
            metadata: 元数据
        
        Returns:
            会话创建结果
        """
        try:
            # 检查用户会话数量
            if user_id in self.user_sessions:
                active_sessions = [
                    sid for sid in self.user_sessions[user_id]
                    if sid in self.sessions and self.sessions[sid].status == SessionStatus.ACTIVE
                ]
                
                if len(active_sessions) >= self.config["max_sessions_per_user"]:
                    # 移除最旧的会话
                    oldest_session = min(active_sessions, key=lambda sid: self.sessions[sid].created_at)
                    await self.revoke_session(oldest_session, "max_sessions_reached")
            
            # 生成会话ID和令牌
            session_id = f"sess_{secrets.token_urlsafe(16)}"
            
            # 生成访问令牌
            token = self.token_utils.generate_token(
                user_id=user_id,
                expires_in=self.config["session_timeout_seconds"],
                token_type="access",
                metadata={"session_id": session_id, "auth_method": auth_method}
            )
            
            # 生成刷新令牌
            refresh_token = f"ref_{secrets.token_urlsafe(32)}"
            refresh_expires = time.time() + (self.config["refresh_token_expiry_days"] * 24 * 3600)
            
            # 创建会话
            now = time.time()
            session = Session(
                session_id=session_id,
                user_id=user_id,
                status=SessionStatus.ACTIVE,
                created_at=now,
                last_accessed_at=now,
                expires_at=now + self.config["session_timeout_seconds"],
                auth_method=auth_method,
                ip_address=ip_address,
                user_agent=user_agent,
                device_id=device_id,
                refresh_token=refresh_token,
                permissions=permissions or [],
                metadata=metadata or {}
            )
            
            # 存储会话
            self.sessions[session_id] = session
            
            # 更新索引
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append(session_id)
            
            self.refresh_tokens[refresh_token] = session_id
            
            # 持久化
            self._save_sessions()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="SESSION_CREATE",
                user_id=user_id,
                details={
                    "session_id": session_id,
                    "auth_method": auth_method,
                    "ip_address": ip_address,
                    "device_id": device_id
                },
                severity="INFO"
            )
            
            logger.info(f"为用户 {user_id} 创建会话 {session_id}")
            
            return SessionCreateResult(
                session_id=session_id,
                user_id=user_id,
                token=token,
                refresh_token=refresh_token,
                expires_at=session.expires_at,
                created_at=now
            )
            
        except Exception as e:
            logger.error(f"创建会话失败: {str(e)}")
            return None
    
    async def validate_session(
        self,
        session_id: str,
        update_last_access: bool = True
    ) -> Tuple[bool, Optional[Session]]:
        """
        验证会话是否有效
        
        Args:
            session_id: 会话ID
            update_last_access: 是否更新最后访问时间
        
        Returns:
            (是否有效, 会话对象)
        """
        try:
            if session_id not in self.sessions:
                return False, None
            
            session = self.sessions[session_id]
            now = time.time()
            
            # 检查会话状态
            if session.status != SessionStatus.ACTIVE:
                return False, session
            
            # 检查是否过期
            if session.expires_at < now:
                session.status = SessionStatus.EXPIRED
                self._save_sessions()
                return False, session
            
            # 检查空闲超时
            idle_time = now - session.last_accessed_at
            if idle_time > self.config["idle_timeout_seconds"]:
                session.status = SessionStatus.IDLE
                self._save_sessions()
                return False, session
            
            # 更新最后访问时间
            if update_last_access:
                session.last_accessed_at = now
                self._save_sessions()
            
            return True, session
            
        except Exception as e:
            logger.error(f"验证会话失败: {str(e)}")
            return False, None
    
    async def refresh_session(
        self,
        refresh_token: str
    ) -> Optional[SessionCreateResult]:
        """
        使用刷新令牌刷新会话
        
        Args:
            refresh_token: 刷新令牌
        
        Returns:
            新的会话创建结果
        """
        try:
            if refresh_token not in self.refresh_tokens:
                logger.warning(f"无效的刷新令牌: {refresh_token[:8]}...")
                return None
            
            session_id = self.refresh_tokens[refresh_token]
            if session_id not in self.sessions:
                logger.warning(f"刷新令牌对应的会话不存在: {session_id}")
                return None
            
            old_session = self.sessions[session_id]
            
            # 检查刷新令牌是否过期（简化版，实际应检查存储的过期时间）
            # 这里假设刷新令牌有效期为7天，需要从创建时间判断
            
            # 创建新会话
            result = await self.create_session(
                user_id=old_session.user_id,
                auth_method=f"refresh:{old_session.auth_method}",
                ip_address=old_session.ip_address,
                user_agent=old_session.user_agent,
                device_id=old_session.device_id,
                permissions=old_session.permissions,
                metadata={**old_session.metadata, "refreshed_from": session_id}
            )
            
            if result:
                # 吊销旧会话
                await self.revoke_session(session_id, "refreshed")
                
                logger.info(f"用户 {old_session.user_id} 刷新会话 {session_id} -> {result.session_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"刷新会话失败: {str(e)}")
            return None
    
    async def revoke_session(
        self,
        session_id: str,
        reason: str = "user_request"
    ) -> bool:
        """
        吊销会话
        
        Args:
            session_id: 会话ID
            reason: 吊销原因
        
        Returns:
            是否成功
        """
        try:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            session.status = SessionStatus.REVOKED
            
            # 记录吊销原因
            if "revoked" not in session.metadata:
                session.metadata["revoked"] = []
            session.metadata["revoked"].append({
                "time": time.time(),
                "reason": reason
            })
            
            # 清理刷新令牌
            if session.refresh_token and session.refresh_token in self.refresh_tokens:
                del self.refresh_tokens[session.refresh_token]
                session.refresh_token = None
            
            self._save_sessions()
            
            # 记录审计日志
            self.audit_logger.log_event(
                event_type="SESSION_REVOKE",
                user_id=session.user_id,
                details={
                    "session_id": session_id,
                    "reason": reason
                },
                severity="INFO"
            )
            
            logger.info(f"会话 {session_id} 被吊销: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"吊销会话失败: {str(e)}")
            return False
    
    async def revoke_user_sessions(
        self,
        user_id: str,
        reason: str = "user_request",
        exclude_session_id: Optional[str] = None
    ) -> int:
        """
        吊销用户的所有会话
        
        Args:
            user_id: 用户ID
            reason: 吊销原因
            exclude_session_id: 排除的会话ID
        
        Returns:
            吊销的会话数量
        """
        try:
            if user_id not in self.user_sessions:
                return 0
            
            revoked_count = 0
            session_ids = self.user_sessions[user_id].copy()
            
            for session_id in session_ids:
                if session_id == exclude_session_id:
                    continue
                
                if await self.revoke_session(session_id, reason):
                    revoked_count += 1
            
            logger.info(f"吊销了用户 {user_id} 的 {revoked_count} 个会话")
            return revoked_count
            
        except Exception as e:
            logger.error(f"吊销用户会话失败: {str(e)}")
            return 0
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话信息"""
        return self.sessions.get(session_id)
    
    def get_user_sessions(
        self,
        user_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有会话
        
        Args:
            user_id: 用户ID
            include_inactive: 是否包含非活跃会话
        
        Returns:
            会话信息列表
        """
        if user_id not in self.user_sessions:
            return []
        
        result = []
        for session_id in self.user_sessions[user_id]:
            session = self.sessions.get(session_id)
            if not session:
                continue
            
            if not include_inactive and session.status != SessionStatus.ACTIVE:
                continue
            
            result.append({
                "session_id": session.session_id,
                "status": session.status.value,
                "created_at": session.created_at,
                "last_accessed_at": session.last_accessed_at,
                "expires_at": session.expires_at,
                "auth_method": session.auth_method,
                "ip_address": session.ip_address,
                "device_id": session.device_id,
                "user_agent": session.user_agent
            })
        
        return result
    
    async def cleanup_expired_sessions(self) -> int:
        """
        清理过期的会话
        
        Returns:
            清理的会话数量
        """
        try:
            now = time.time()
            cleaned = 0
            
            for session_id, session in list(self.sessions.items()):
                should_clean = False
                
                # 检查是否过期
                if session.expires_at < now:
                    should_clean = True
                
                # 检查空闲超时
                elif (now - session.last_accessed_at) > self.config["idle_timeout_seconds"] * 2:
                    should_clean = True
                
                # 检查状态
                elif session.status in [SessionStatus.EXPIRED, SessionStatus.REVOKED]:
                    should_clean = True
                
                if should_clean:
                    # 从索引中移除
                    if session.user_id in self.user_sessions:
                        if session_id in self.user_sessions[session.user_id]:
                            self.user_sessions[session.user_id].remove(session_id)
                    
                    # 移除刷新令牌
                    if session.refresh_token and session.refresh_token in self.refresh_tokens:
                        del self.refresh_tokens[session.refresh_token]
                    
                    # 删除会话
                    del self.sessions[session_id]
                    cleaned += 1
            
            if cleaned > 0:
                self._save_sessions()
                logger.info(f"清理了 {cleaned} 个过期会话")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {str(e)}")
            return 0
    
    async def start_cleanup_task(self):
        """启动自动清理任务"""
        if self._cleanup_task:
            return
        
        async def _cleanup_loop():
            interval_minutes = self.config["cleanup_interval_minutes"]
            
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    await self.cleanup_expired_sessions()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"自动清理任务异常: {str(e)}")
        
        self._cleanup_task = asyncio.create_task(_cleanup_loop())
        logger.info(f"自动清理任务已启动，间隔 {interval_minutes} 分钟")
    
    async def stop_cleanup_task(self):
        """停止自动清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("自动清理任务已停止")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        now = time.time()
        active_count = 0
        idle_count = 0
        expired_count = 0
        
        for session in self.sessions.values():
            if session.status == SessionStatus.ACTIVE:
                if (now - session.last_accessed_at) > self.config["idle_timeout_seconds"]:
                    idle_count += 1
                else:
                    active_count += 1
            elif session.status == SessionStatus.EXPIRED:
                expired_count += 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_count,
            "idle_sessions": idle_count,
            "expired_sessions": expired_count,
            "unique_users": len(self.user_sessions),
            "refresh_tokens_count": len(self.refresh_tokens)
        }


# 单例实例
_session_manager_instance = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例实例"""
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance

