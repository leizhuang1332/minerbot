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


class EntityType(Enum):
    """记忆实体类型"""
    PERSON = "person"
    LOCATION = "location"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    CONTEXT = "context"


@dataclass
class MemoryEntity:
    """记忆实体"""
    id: str
    entity_type: EntityType
    name: str
    description: str
    metadata: dict[str, object]
    created_at: str


@dataclass
class SessionSummary:
    """会话摘要"""
    thread_id: str
    topic: str
    key_points: list[str]
    decisions: list[str]
    action_items: list[str]
    created_at: str


@dataclass
class MemoryRecord:
    """记忆记录"""
    record_id: str
    user_id: str
    thread_id: str
    entities: list[MemoryEntity]
    summary: SessionSummary
    messages: list[ChatMessage]
    created_at: str
