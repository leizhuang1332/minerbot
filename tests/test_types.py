"""类型测试"""
import pytest
from minerbot.types import ExitCode, ChatMessage, SessionInfo


def test_exit_code():
    """测试退出码"""
    assert ExitCode.SUCCESS.value == 0
    assert ExitCode.ERROR.value == 1
    assert ExitCode.KEYBOARD_INTERRUPT.value == 2


def test_chat_message():
    """测试聊天消息"""
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.timestamp is None


def test_session_info():
    """测试会话信息"""
    session = SessionInfo(
        session_id="test-123",
        created_at="2024-01-01T00:00:00"
    )
    assert session.session_id == "test-123"
    assert session.message_count == 0
