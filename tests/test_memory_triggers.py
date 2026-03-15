"""记忆触发器测试"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from minerbot.config import AppConfig
from minerbot.memory.triggers import (
    TriggerManager,
    TriggerResult,
    TriggerType,
    ThreadState,
    SESSION_END_KEYWORDS,
)


@pytest.fixture
def mock_config():
    """创建模拟配置"""
    config = MagicMock(spec=AppConfig)
    config.memory_trigger_message_count = 10
    config.memory_trigger_idle_minutes = 10
    return config


@pytest.fixture
def trigger_manager(mock_config):
    """创建触发管理器实例"""
    return TriggerManager(mock_config)


class TestTriggerResult:
    """测试 TriggerResult 数据类"""

    def test_trigger_result_defaults(self):
        """测试默认触发结果"""
        result = TriggerResult(should_trigger=False)
        
        assert result.should_trigger is False
        assert result.trigger_type is None
        assert result.reason == ""

    def test_trigger_result_with_values(self):
        """测试带值的触发结果"""
        result = TriggerResult(
            should_trigger=True,
            trigger_type=TriggerType.SESSION_END,
            reason="测试原因"
        )
        
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END
        assert result.reason == "测试原因"


class TestThreadState:
    """测试 ThreadState 数据类"""

    def test_thread_state_defaults(self):
        """测试默认线程状态"""
        state = ThreadState(thread_id="test-thread")
        
        assert state.thread_id == "test-thread"
        assert state.message_count == 0
        assert state.is_active is True
        assert isinstance(state.last_activity_time, datetime)

    def test_thread_state_with_values(self):
        """测试带值的线程状态"""
        now = datetime.now()
        state = ThreadState(
            thread_id="test-thread",
            message_count=5,
            last_activity_time=now,
            is_active=False
        )
        
        assert state.thread_id == "test-thread"
        assert state.message_count == 5
        assert state.last_activity_time == now
        assert state.is_active is False


class TestTriggerManager:
    """测试 TriggerManager 触发管理器"""

    def test_init(self, mock_config):
        """测试触发管理器初始化"""
        manager = TriggerManager(mock_config)
        
        assert manager._config == mock_config
        assert manager._thread_states == {}
        assert manager._idle_check_task is None
        assert manager.message_count_threshold == 10
        assert manager.idle_timeout_minutes == 10

    def test_get_or_create_thread_state(self, trigger_manager):
        """测试获取或创建线程状态"""
        state1 = trigger_manager._get_or_create_thread_state("thread-1")
        
        assert isinstance(state1, ThreadState)
        assert state1.thread_id == "thread-1"
        
        # 再次获取应该是同一个对象
        state2 = trigger_manager._get_or_create_thread_state("thread-1")
        assert state1 is state2
        
        # 新线程应该创建新对象
        state3 = trigger_manager._get_or_create_thread_state("thread-2")
        assert state3 is not state1

    def test_session_end_trigger_quit(self, trigger_manager):
        """测试 quit 命令触发会话结束"""
        session_state = {"last_message": "quit"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END
        assert "quit" in result.reason

    def test_session_end_trigger_exit(self, trigger_manager):
        """测试 exit 命令触发会话结束"""
        session_state = {"last_message": "exit"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END

    def test_session_end_trigger_结束(self, trigger_manager):
        """测试中文结束命令"""
        session_state = {"last_message": "结束"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is not None
        assert result.should_trigger is True

    def test_session_end_trigger_with_prefix(self, trigger_manager):
        """测试带前缀的命令"""
        session_state = {"last_message": "quit some text"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is not None
        assert result.should_trigger is True

    def test_session_end_trigger_case_insensitive(self, trigger_manager):
        """测试大小写不敏感"""
        session_state = {"last_message": "QUIT"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is not None
        assert result.should_trigger is True

    def test_session_end_no_trigger(self, trigger_manager):
        """测试非结束命令不触发"""
        session_state = {"last_message": "你好"}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is None

    def test_session_end_empty_message(self, trigger_manager):
        """测试空消息不触发"""
        session_state = {"last_message": ""}
        
        result = trigger_manager._check_session_end(session_state)
        
        assert result is None


class TestMessageCountTrigger:
    """测试消息数触发"""

    def test_message_count_below_threshold(self, trigger_manager):
        """测试消息数未达到阈值不触发"""
        thread_state = ThreadState(thread_id="test", message_count=5)
        
        result = trigger_manager._check_message_count(thread_state)
        
        assert result is None

    def test_message_count_at_threshold(self, trigger_manager):
        """测试消息数达到阈值触发"""
        thread_state = ThreadState(thread_id="test", message_count=10)
        
        result = trigger_manager._check_message_count(thread_state)
        
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.MESSAGE_COUNT
        assert "10/10" in result.reason

    def test_message_count_above_threshold(self, trigger_manager):
        """测试消息数超过阈值触发"""
        thread_state = ThreadState(thread_id="test", message_count=15)
        
        result = trigger_manager._check_message_count(thread_state)
        
        assert result is not None
        assert result.should_trigger is True


class TestIdleTimeoutTrigger:
    """测试空闲超时触发"""

    def test_idle_timeout_not_active(self, trigger_manager):
        """测试非活跃线程不触发"""
        thread_state = ThreadState(thread_id="test", is_active=False)
        
        result = trigger_manager._check_idle_timeout(thread_state)
        
        assert result is None

    def test_idle_timeout_not_exceeded(self, trigger_manager):
        """测试未超过空闲超时不触发"""
        thread_state = ThreadState(
            thread_id="test",
            last_activity_time=datetime.now()
        )
        
        result = trigger_manager._check_idle_timeout(thread_state)
        
        assert result is None

    def test_idle_timeout_exceeded(self, trigger_manager):
        """测试超过空闲超时触发"""
        # 模拟 15 分钟前的最后活动时间
        old_time = datetime.now() - timedelta(minutes=15)
        thread_state = ThreadState(
            thread_id="test",
            last_activity_time=old_time
        )
        
        result = trigger_manager._check_idle_timeout(thread_state)
        
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.IDLE_TIMEOUT
        assert "15.0分钟" in result.reason or "15.0分钟 >=" in result.reason


class TestCheckAndTrigger:
    """测试 check_and_trigger 方法"""

    @pytest.mark.asyncio
    async def test_check_and_trigger_no_trigger(self, trigger_manager):
        """测试无触发条件"""
        session_state = {"last_message": "你好"}
        
        result = await trigger_manager.check_and_trigger("thread-1", session_state)
        
        assert result.should_trigger is False
        assert result.reason == "未满足任何触发条件"

    @pytest.mark.asyncio
    async def test_check_and_trigger_session_end(self, trigger_manager):
        """测试会话结束触发优先于消息数"""
        session_state = {"last_message": "quit"}
        
        result = await trigger_manager.check_and_trigger("thread-1", session_state)
        
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END
        
        # 验证线程状态被设置为非活跃
        thread_state = trigger_manager.get_thread_state("thread-1")
        assert thread_state is not None
        assert thread_state.is_active is False

    @pytest.mark.asyncio
    async def test_check_and_trigger_message_count(self, trigger_manager):
        """测试消息数触发"""
        # 设置消息数达到阈值
        trigger_manager.update_thread_state("thread-1", message_count=10)
        
        session_state = {"last_message": "你好", "message_count": 10}
        
        result = await trigger_manager.check_and_trigger("thread-1", session_state)
        
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.MESSAGE_COUNT

    @pytest.mark.asyncio
    async def test_check_and_trigger_idle_timeout(self, trigger_manager):
        """测试空闲超时触发"""
        # 直接测试 _check_idle_timeout 方法，因为它在 check_and_trigger 中
        # 会在更新 last_activity_time 之后被调用
        old_time = datetime.now() - timedelta(minutes=15)
        thread_state = ThreadState(
            thread_id="thread-1",
            last_activity_time=old_time,
            is_active=True
        )
        
        result = trigger_manager._check_idle_timeout(thread_state)
        
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.IDLE_TIMEOUT


class TestThreadStateManagement:
    """测试线程状态管理"""

    def test_update_thread_state(self, trigger_manager):
        """测试更新线程状态"""
        trigger_manager.update_thread_state("thread-1", message_count=5, is_active=False)
        
        state = trigger_manager.get_thread_state("thread-1")
        assert state is not None
        assert state.message_count == 5
        assert state.is_active is False

    def test_reset_thread_state(self, trigger_manager):
        """测试重置线程状态"""
        # 先更新状态
        trigger_manager.update_thread_state("thread-1", message_count=100, is_active=False)
        
        # 重置
        trigger_manager.reset_thread_state("thread-1")
        
        state = trigger_manager.get_thread_state("thread-1")
        assert state is not None
        assert state.message_count == 0
        assert state.is_active is True

    def test_get_thread_state_not_exists(self, trigger_manager):
        """测试获取不存在的线程状态"""
        state = trigger_manager.get_thread_state("non-existent")
        
        assert state is None


class TestDynamicConfig:
    """测试动态配置"""

    def test_set_message_count_threshold(self, trigger_manager):
        """测试动态设置消息数阈值"""
        trigger_manager.set_message_count_threshold(20)
        
        assert trigger_manager.message_count_threshold == 20

    def test_set_message_count_threshold_min_value(self, trigger_manager):
        """测试消息数阈值最小值为1"""
        trigger_manager.set_message_count_threshold(0)
        
        assert trigger_manager.message_count_threshold == 1

    def test_set_idle_timeout_minutes(self, trigger_manager):
        """测试动态设置空闲超时"""
        trigger_manager.set_idle_timeout_minutes(30)
        
        assert trigger_manager.idle_timeout_minutes == 30

    def test_set_idle_timeout_minutes_min_value(self, trigger_manager):
        """测试空闲超时最小值为1"""
        trigger_manager.set_idle_timeout_minutes(0)
        
        assert trigger_manager.idle_timeout_minutes == 1


class TestSessionEndKeywords:
    """测试会话结束关键词"""

    def test_session_end_keywords(self):
        """测试所有会话结束关键词"""
        expected_keywords = {"quit", "exit", "结束", "q", "再见", "bye"}
        
        assert SESSION_END_KEYWORDS == expected_keywords
