"""记忆系统集成测试

测试完整流程: 对话 → 触发 → 提取 → 存储 → 检索

测试端到端场景:
- 会话结束触发
- 消息数量触发
- 空闲超时触发（模拟时间）
- 记忆检索
"""
import asyncio
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.messages import AIMessage, HumanMessage

from minerbot.config import AppConfig
from minerbot.memory import (
    EntityExtractor,
    MemoryStorage,
    SessionSummarizer,
    TriggerManager,
    TriggerResult,
    TriggerType,
)
from minerbot.memory.storage import MemoryStorage as ActualMemoryStorage
from minerbot.types import EntityType, MemoryEntity, SessionSummary


class TestTriggerManager:
    """触发管理器测试"""

    @pytest.fixture
    def config(self) -> AppConfig:
        """创建测试配置"""
        return AppConfig(
            anthropic_api_key="test-key",
            memory_enabled=True,
            memory_trigger_message_count=5,
            memory_trigger_idle_minutes=10,
        )

    @pytest.fixture
    def trigger_manager(self, config: AppConfig) -> TriggerManager:
        """创建触发管理器实例"""
        return TriggerManager(config)

    @pytest.mark.asyncio
    async def test_session_end_trigger_quit(self, trigger_manager: TriggerManager):
        """测试会话结束触发 - quit 命令"""
        session_state = {"last_message": "quit"}
        result = await trigger_manager.check_and_trigger("thread-1", session_state)

        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END
        assert "quit" in result.reason

    @pytest.mark.asyncio
    async def test_session_end_trigger_exit(self, trigger_manager: TriggerManager):
        """测试会话结束触发 - exit 命令"""
        session_state = {"last_message": "exit"}
        result = await trigger_manager.check_and_trigger("thread-1", session_state)

        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END

    @pytest.mark.asyncio
    async def test_session_end_trigger_chinese(self, trigger_manager: TriggerManager):
        """测试会话结束触发 - 中文命令"""
        for cmd in ["结束", "再见", "bye"]:
            session_state = {"last_message": cmd}
            result = await trigger_manager.check_and_trigger("thread-2", session_state)

            assert result.should_trigger is True
            assert result.trigger_type == TriggerType.SESSION_END

    @pytest.mark.asyncio
    async def test_message_count_trigger(self, trigger_manager: TriggerManager):
        """测试消息数触发"""
        # 设置阈值为 5
        trigger_manager.set_message_count_threshold(5)

        # 发送 4 条消息，不应触发
        for i in range(4):
            session_state = {"last_message": f"消息 {i}", "message_count": i + 1}
            result = await trigger_manager.check_and_trigger("thread-3", session_state)
            assert result.should_trigger is False

        # 发送第 5 条消息，应触发
        session_state = {"last_message": "消息 5", "message_count": 5}
        result = await trigger_manager.check_and_trigger("thread-3", session_state)

        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.MESSAGE_COUNT

    @pytest.mark.asyncio
    async def test_idle_timeout_trigger(self, trigger_manager: TriggerManager):
        """测试空闲超时触发"""
        thread_id = "thread-4"

        # 创建线程状态
        session_state = {"last_message": "初始消息", "message_count": 1}
        await trigger_manager.check_and_trigger(thread_id, session_state)

        # 设置超时为 1 分钟
        trigger_manager.set_idle_timeout_minutes(1)

        # 获取线程状态并手动设置最后活动时间为过去
        thread_state = trigger_manager.get_thread_state(thread_id)

        # 使用 patch 来模拟过去的时间
        with patch('minerbot.memory.triggers.datetime') as mock_datetime:
            mock_now = datetime.now()
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            # 设置最后活动时间为 2 分钟前
            thread_state.last_activity_time = mock_now - timedelta(minutes=2)

        # 直接测试空闲超时检测逻辑
        result = trigger_manager._check_idle_timeout(thread_state)

        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.IDLE_TIMEOUT
        assert "2." in result.reason

    @pytest.mark.asyncio
    async def test_no_trigger_conditions(self, trigger_manager: TriggerManager):
        """测试无触发条件"""
        thread_id = "thread-5"

        # 重置状态
        trigger_manager.reset_thread_state(thread_id)

        # 发送正常消息
        session_state = {"last_message": "你好", "message_count": 1}
        result = await trigger_manager.check_and_trigger(thread_id, session_state)

        assert result.should_trigger is False
        assert result.trigger_type is None
        assert "未满足任何触发条件" in result.reason

    @pytest.mark.asyncio
    async def test_thread_state_management(self, trigger_manager: TriggerManager):
        """测试线程状态管理"""
        thread_id = "thread-6"

        # 先通过发送消息创建线程状态
        session_state = {"last_message": "初始化", "message_count": 1}
        await trigger_manager.check_and_trigger(thread_id, session_state)

        # 获取线程状态
        state = trigger_manager.get_thread_state(thread_id)
        assert state is not None
        assert state.thread_id == thread_id
        assert state.message_count == 1
        assert state.is_active is True

        # 更新线程状态
        trigger_manager.update_thread_state(thread_id, message_count=10, is_active=False)
        state = trigger_manager.get_thread_state(thread_id)
        assert state.message_count == 10
        assert state.is_active is False

        # 重置线程状态
        trigger_manager.reset_thread_state(thread_id)
        state = trigger_manager.get_thread_state(thread_id)
        assert state.message_count == 0
        assert state.is_active is True


class TestEntityExtractor:
    """实体提取器测试"""

    @pytest.fixture
    def mock_model(self):
        """创建模拟的 LLM 模型"""
        mock_model = MagicMock()
        mock_structured_model = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured_model
        return mock_model

    @pytest.mark.asyncio
    async def test_extract_entities(self, mock_model):
        """测试实体提取"""
        from minerbot.memory.extractor import ExtractionResult, ExtractedEntity

        # Mock LLM 返回
        mock_response = ExtractionResult(
            entities=[
                ExtractedEntity(
                    entity_type="person",
                    name="张三",
                    description="用户的朋友",
                    metadata={"age": 30}
                ),
                ExtractedEntity(
                    entity_type="context",
                    name="项目开发",
                    description="正在进行的工作项目",
                    metadata={}
                ),
            ]
        )

        with patch('minerbot.memory.extractor.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_response

            extractor = EntityExtractor(mock_model)

            messages = [
                HumanMessage(content="我的朋友张三在做项目开发"),
                AIMessage(content="这很有意思"),
            ]

            entities = await extractor.extract(messages, user_id="user123")

            assert len(entities) == 2
            assert entities[0].name == "张三"
            assert entities[0].entity_type == EntityType.PERSON
            assert entities[1].name == "项目开发"
            assert entities[1].entity_type == EntityType.CONTEXT

    @pytest.mark.asyncio
    async def test_extract_empty_messages(self, mock_model):
        """测试空消息列表"""
        extractor = EntityExtractor(mock_model)
        entities = await extractor.extract([], user_id="user123")

        assert entities == []

    @pytest.mark.asyncio
    async def test_extract_exception_handling(self, mock_model):
        """测试异常处理"""
        mock_structured = mock_model.with_structured_output.return_value
        mock_structured.invoke = AsyncMock(side_effect=Exception("API Error"))

        extractor = EntityExtractor(mock_model)

        messages = [HumanMessage(content="测试消息")]
        entities = await extractor.extract(messages, user_id="user123")

        assert entities == []


class TestSessionSummarizer:
    """会话摘要器测试"""

    @pytest.fixture
    def mock_model(self):
        """创建模拟的 LLM 模型"""
        mock_model = MagicMock()
        return mock_model

    @pytest.mark.asyncio
    async def test_summarize_success(self, mock_model):
        """测试成功生成摘要"""
        # Mock LLM 返回
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "topic": "项目讨论",
            "key_points": ["讨论了需求", "确定了计划"],
            "decisions": ["采用敏捷开发"],
            "action_items": ["编写文档"]
        })

        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        summarizer = SessionSummarizer(mock_model)

        messages = [
            {"role": "user", "content": "我们讨论一下项目需求"},
            {"role": "assistant", "content": "好的，请说"},
        ]

        summary = await summarizer.summarize(messages, thread_id="thread-1")

        assert summary.topic == "项目讨论"
        assert len(summary.key_points) == 2
        assert "采用敏捷开发" in summary.decisions
        assert "编写文档" in summary.action_items
        assert summary.thread_id == "thread-1"

    @pytest.mark.asyncio
    async def test_summarize_empty_messages(self, mock_model):
        """测试空消息列表"""
        summarizer = SessionSummarizer(mock_model)

        with pytest.raises(ValueError, match="消息列表不能为空"):
            await summarizer.summarize([], thread_id="thread-1")


class TestMemoryStorage:
    """记忆存储测试"""

    @pytest.fixture
    def mock_store(self):
        """创建模拟的存储"""
        mock_store = AsyncMock()
        mock_store.aput = AsyncMock()
        mock_store.asearch = AsyncMock(return_value=[])
        mock_store.aget = AsyncMock(return_value=None)
        return mock_store

    @pytest.mark.asyncio
    async def test_save_and_search_entity(self, mock_store):
        """测试保存和搜索实体"""
        storage = MemoryStorage(mock_store, namespace_prefix="memory")

        entity = MemoryEntity(
            id="entity-1",
            entity_type=EntityType.PERSON,
            name="张三",
            description="测试用户",
            metadata={"user_id": "user123"},
            created_at="2024-01-01T00:00:00Z"
        )

        await storage.save_entity("user123", entity)

        # 验证调用
        mock_store.aput.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entities(self, mock_store):
        """测试搜索实体"""
        # Mock 搜索结果
        mock_item = MagicMock()
        mock_item.value = {
            "id": "entity-1",
            "entity_type": "person",
            "name": "张三",
            "description": "测试用户",
            "metadata": {"user_id": "user123"},
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_store.asearch = AsyncMock(return_value=[mock_item])

        storage = MemoryStorage(mock_store, namespace_prefix="memory")

        results = await storage.search_entities("user123", "张三", limit=10)

        assert len(results) == 1
        assert results[0].name == "张三"

    @pytest.mark.asyncio
    async def test_save_and_get_summary(self, mock_store):
        """测试保存和获取摘要"""
        storage = MemoryStorage(mock_store, namespace_prefix="memory")

        summary = SessionSummary(
            thread_id="thread-1",
            topic="测试主题",
            key_points=["要点1"],
            decisions=["决定1"],
            action_items=["任务1"],
            created_at="2024-01-01T00:00:00Z"
        )

        await storage.save_summary("user123", "thread-1", summary)

        # 验证调用
        mock_store.aput.assert_called_once()


class TestCompleteFlow:
    """完整流程测试 - 端到端场景"""

    @pytest.fixture
    def config(self) -> AppConfig:
        """创建测试配置"""
        return AppConfig(
            anthropic_api_key="test-key",
            memory_enabled=True,
            memory_trigger_message_count=3,
            memory_trigger_idle_minutes=5,
        )

    @pytest.fixture
    def mock_model(self):
        """创建模拟的 LLM 模型"""
        mock_model = MagicMock()

        # Mock 实体提取
        mock_entity_response = MagicMock()
        mock_entity_response.entities = [
            MagicMock(
                entity_type="person",
                name="李四",
                description="项目成员",
                metadata={}
            )
        ]
        mock_structured = MagicMock()
        mock_structured.invoke = AsyncMock(return_value=mock_entity_response)
        mock_model.with_structured_output.return_value = mock_structured

        # Mock 摘要生成
        mock_summary_response = MagicMock()
        mock_summary_response.content = json.dumps({
            "topic": "会议讨论",
            "key_points": ["讨论了项目进度"],
            "decisions": ["继续开发"],
            "action_items": ["完成测试"]
        })
        mock_model.ainvoke = AsyncMock(return_value=mock_summary_response)

        return mock_model

    @pytest.fixture
    def mock_storage(self):
        """创建模拟的存储"""
        mock_store = AsyncMock()
        mock_store.aput = AsyncMock()
        mock_store.asearch = AsyncMock(return_value=[])
        mock_store.aget = AsyncMock(return_value=None)
        return mock_store

    @pytest.mark.asyncio
    async def test_session_end_flow(self, config, mock_model, mock_storage):
        """测试会话结束触发流程"""
        from minerbot.memory.extractor import ExtractionResult, ExtractedEntity

        trigger_manager = TriggerManager(config)
        storage = MemoryStorage(mock_storage)

        # Mock 实体提取结果
        mock_entity_response = ExtractionResult(
            entities=[
                ExtractedEntity(
                    entity_type="person",
                    name="李四",
                    description="项目成员",
                    metadata={}
                )
            ]
        )

        with patch('minerbot.memory.extractor.asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_entity_response

            extractor = EntityExtractor(mock_model)

            # Mock 摘要生成
            mock_summary_response = MagicMock()
            mock_summary_response.content = json.dumps({
                "topic": "会议讨论",
                "key_points": ["讨论了项目进度"],
                "decisions": ["继续开发"],
                "action_items": ["完成测试"]
            })
            mock_model.ainvoke = AsyncMock(return_value=mock_summary_response)

            summarizer = SessionSummarizer(mock_model)

            thread_id = "thread-session-end"
            user_id = "user123"

            # 模拟用户发送退出命令
            session_state = {"last_message": "quit", "message_count": 5}
            result = await trigger_manager.check_and_trigger(thread_id, session_state)

            # 验证触发
            assert result.should_trigger is True
            assert result.trigger_type == TriggerType.SESSION_END

            # 模拟提取实体
            messages = [
                HumanMessage(content="今天和李四讨论了项目"),
                AIMessage(content="好的"),
            ]
            entities = await extractor.extract(messages, user_id)

            # 验证实体提取
            assert len(entities) > 0

            # 模拟生成摘要
            messages_dict = [{"role": "user", "content": "今天和李四讨论了项目"}]
            summary = await summarizer.summarize(messages_dict, thread_id)

            # 验证摘要
            assert summary.topic is not None

            # 模拟存储
            for entity in entities:
                await storage.save_entity(user_id, entity)
            await storage.save_summary(user_id, thread_id, summary)

            # 验证存储调用
            assert mock_storage.aput.call_count >= len(entities) + 1

    @pytest.mark.asyncio
    async def test_message_count_flow(self, config, mock_model, mock_storage):
        """测试消息数触发流程"""
        trigger_manager = TriggerManager(config)
        storage = MemoryStorage(mock_storage)
        extractor = EntityExtractor(mock_model)

        thread_id = "thread-msg-count"
        user_id = "user456"

        # 设置阈值为 3
        trigger_manager.set_message_count_threshold(3)

        # 发送消息直到触发
        for i in range(3):
            session_state = {"last_message": f"消息 {i}", "message_count": i + 1}
            result = await trigger_manager.check_and_trigger(thread_id, session_state)

            if i < 2:
                assert result.should_trigger is False
            else:
                assert result.should_trigger is True
                assert result.trigger_type == TriggerType.MESSAGE_COUNT

                # 触发后执行记忆提取
                messages = [
                    HumanMessage(content=f"消息 {i}"),
                    AIMessage(content="回复"),
                ]
                entities = await extractor.extract(messages, user_id)

                # 验证提取成功
                assert entities is not None

    @pytest.mark.asyncio
    async def test_idle_timeout_flow(self, config, mock_model, mock_storage):
        """测试空闲超时触发流程"""
        trigger_manager = TriggerManager(config)
        storage = MemoryStorage(mock_storage)
        summarizer = SessionSummarizer(mock_model)

        thread_id = "thread-idle"
        user_id = "user789"

        # 创建线程状态
        session_state = {"last_message": "hello", "message_count": 1}
        await trigger_manager.check_and_trigger(thread_id, session_state)

        # 设置超时为 1 分钟
        trigger_manager.set_idle_timeout_minutes(1)

        # 获取线程状态并设置最后活动时间为过去
        thread_state = trigger_manager.get_thread_state(thread_id)
        thread_state.last_activity_time = datetime.now() - timedelta(minutes=2)

        # 检查空闲超时 - 应该触发
        result = trigger_manager._check_idle_timeout(thread_state)

        # 验证触发
        assert result is not None
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.IDLE_TIMEOUT

        # 触发后生成摘要
        messages_dict = [
            {"role": "user", "content": "讨论了项目"},
            {"role": "assistant", "content": "了解了"},
        ]
        summary = await summarizer.summarize(messages_dict, thread_id)

        # 验证摘要
        assert summary.topic is not None

    @pytest.mark.asyncio
    async def test_memory_retrieval_flow(self, config, mock_model, mock_storage):
        """测试记忆检索流程"""
        storage = MemoryStorage(mock_storage)

        # 模拟已有记忆
        mock_item = MagicMock()
        mock_item.value = {
            "id": "entity-retrieval",
            "entity_type": "person",
            "name": "王五",
            "description": "重要联系人",
            "metadata": {"user_id": "user检索"},
            "created_at": "2024-01-01T00:00:00Z"
        }
        mock_storage.asearch = AsyncMock(return_value=[mock_item])

        # 检索记忆
        results = await storage.search_entities("user检索", "王五", limit=10)

        # 验证检索结果
        assert len(results) == 1
        assert results[0].name == "王五"
        assert results[0].entity_type == "person"


class TestIntegrationScenarios:
    """集成场景测试"""

    @pytest.mark.asyncio
    async def test_conversation_to_storage_flow(self):
        """测试从对话到存储的完整流程"""
        # 1. 模拟对话
        messages = [
            HumanMessage(content="我和我的同事赵六在北京讨论了一个重要项目"),
            AIMessage(content="请详细说说"),
            HumanMessage(content="这是一个关于人工智能的项目"),
        ]

        # 2. 模拟触发检查
        config = AppConfig(
            anthropic_api_key="test-key",
            memory_enabled=True,
            memory_trigger_message_count=10,
            memory_trigger_idle_minutes=30,
        )
        trigger_manager = TriggerManager(config)

        session_state = {"last_message": "这是一个关于人工智能的项目", "message_count": 3}
        result = await trigger_manager.check_and_trigger("test-thread", session_state)

        # 验证触发检查完成
        assert result is not None
        assert isinstance(result, TriggerResult)

    @pytest.mark.asyncio
    async def test_multi_trigger_priority(self):
        """测试多触发条件优先级"""
        config = AppConfig(
            anthropic_api_key="test-key",
            memory_enabled=True,
            memory_trigger_message_count=2,
            memory_trigger_idle_minutes=1,
        )
        trigger_manager = TriggerManager(config)

        # 同时满足多个触发条件时，应优先触发会话结束
        # 1. 设置消息数刚好达到阈值
        # 2. 设置退出命令

        session_state = {"last_message": "quit", "message_count": 2}
        result = await trigger_manager.check_and_trigger("priority-thread", session_state)

        # 会话结束应优先触发
        assert result.should_trigger is True
        assert result.trigger_type == TriggerType.SESSION_END

    @pytest.mark.asyncio
    async def test_concurrent_thread_states(self):
        """测试并发线程状态管理"""
        config = AppConfig(
            anthropic_api_key="test-key",
            memory_enabled=True,
            memory_trigger_message_count=5,
            memory_trigger_idle_minutes=10,
        )
        trigger_manager = TriggerManager(config)

        # 并发处理多个线程
        async def process_thread(thread_id: str, message: str, count: int):
            session_state = {"last_message": message, "message_count": count}
            return await trigger_manager.check_and_trigger(thread_id, session_state)

        # 并发执行
        results = await asyncio.gather(
            process_thread("thread-a", "消息1", 1),
            process_thread("thread-b", "消息2", 2),
            process_thread("thread-c", "quit", 1),
        )

        # 验证所有线程独立处理
        assert len(results) == 3
        assert results[2].trigger_type == TriggerType.SESSION_END


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
