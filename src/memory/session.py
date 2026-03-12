"""Session Management Module

提供会话生命周期管理，用于短期记忆的会话标识生成。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Session:
    """会话对象
    
    Attributes:
        id: 会话唯一标识
        client_id: 客户端标识（如钉钉用户ID）
        created_at: 创建时间
        last_active: 最后活跃时间
        metadata: 元数据
    """
    id: str
    client_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """会话管理器
    
    管理用户会话生命周期，支持根据 client_id 获取或创建会话。
    """
    
    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}
    
    def create_session(self, client_id: str, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """创建新会话"""
        session = Session(
            id=str(uuid.uuid4()),
            client_id=client_id,
            metadata=metadata or {}
        )
        self._sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, client_id: str) -> Session:
        """获取或创建会话"""
        for session in self._sessions.values():
            if session.client_id == client_id:
                session.last_active = datetime.now()
                return session
        return self.create_session(client_id)
    
    def update_activity(self, session_id: str) -> None:
        """更新会话活跃时间"""
        if session_id in self._sessions:
            self._sessions[session_id].last_active = datetime.now()
    
    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        self._sessions.pop(session_id, None)
    
    def generate_thread_id(self, client_id: str, conversation_id: Optional[str] = None) -> str:
        """生成 thread_id"""
        if conversation_id:
            return f"{client_id}_{conversation_id}"
        else:
            return f"{client_id}_default"
