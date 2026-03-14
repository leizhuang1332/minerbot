"""类型定义模块"""
from dataclasses import dataclass
from enum import Enum


class ExitCode(Enum):
    """退出码"""
    SUCCESS = 0
    ERROR = 1
    KEYBOARD_INTERRUPT = 2


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str
    timestamp: str | None = None


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    created_at: str
    message_count: int = 0
