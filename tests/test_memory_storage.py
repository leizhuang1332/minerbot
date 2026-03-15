"""MemoryStorage 测试模块"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from minerbot.memory.storage import MemoryStorage
from minerbot.types import MemoryEntity, SessionSummary, EntityType


@pytest.fixture
def mock_store():
    """创建模拟的 AsyncSqliteStore"""
    store = AsyncMock()
    store.aput = AsyncMock()
    store.aget = AsyncMock()
    store.asearch = AsyncMock()
    return store


@pytest.fixture
def memory_storage(mock_store):
    """创建 MemoryStorage 实例"""
    return MemoryStorage(store=mock_store, namespace_prefix="memory")


@pytest.fixture
def sample_entity():
    """创建测试用的 MemoryEntity"""
    return MemoryEntity(
        id="entity-1",
        entity_type=EntityType.PERSON,
        name="张三",
        description="一个测试用户",
        metadata={"age": 30},
        created_at="2024-01-01T00:00:00"
    )


@pytest.fixture
def sample_summary():
    """创建测试用的 SessionSummary"""
    return SessionSummary(
        thread_id="thread-1",
        topic="测试主题",
        key_points=["要点1", "要点2"],
        decisions=["决定1"],
        action_items=["任务1"],
        created_at="2024-01-01T00:00:00"
    )


class TestMemoryStorageInit:
    """测试 MemoryStorage 初始化"""

    def test_init_default_prefix(self, mock_store):
        """测试默认命名空间前缀"""
        storage = MemoryStorage(store=mock_store)
        assert storage._namespace_prefix == "memory"
        assert storage._store == mock_store

    def test_init_custom_prefix(self, mock_store):
        """测试自定义命名空间前缀"""
        storage = MemoryStorage(store=mock_store, namespace_prefix="custom")
        assert storage._namespace_prefix == "custom"

    def test_entity_namespace(self, memory_storage):
        """测试实体命名空间生成"""
        namespace = memory_storage._entity_namespace("user-123")
        assert namespace == ("memory", "entities", "user-123")

    def test_summary_namespace(self, memory_storage):
        """测试摘要命名空间生成"""
        namespace = memory_storage._summary_namespace("user-123", "thread-456")
        assert namespace == ("memory", "summaries", "user-123", "thread-456")


class TestSaveAndGetEntity:
    """测试 save_entity 和 get_entity 方法"""

    @pytest.mark.asyncio
    async def test_save_entity(self, memory_storage, mock_store, sample_entity):
        """测试保存记忆实体"""
        await memory_storage.save_entity("user-1", sample_entity)

        mock_store.aput.assert_called_once()
        call_args = mock_store.aput.call_args
        assert call_args[0][0] == ("memory", "entities", "user-1")
        assert call_args[0][1] == "entity-1"

    @pytest.mark.asyncio
    async def test_get_entity_exists(self, memory_storage, mock_store, sample_entity):
        """测试获取存在的记忆实体"""
        mock_item = MagicMock()
        mock_item.value = {
            "id": "entity-1",
            "entity_type": EntityType.PERSON,
            "name": "张三",
            "description": "一个测试用户",
            "metadata": {"age": 30},
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.aget = AsyncMock(return_value=mock_item)

        result = await memory_storage.get_entity("user-1", "entity-1")

        assert result is not None
        assert result.id == "entity-1"
        assert result.name == "张三"
        mock_store.aget.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity_not_exists(self, memory_storage, mock_store):
        """测试获取不存在的记忆实体"""
        mock_store.aget = AsyncMock(return_value=None)

        result = await memory_storage.get_entity("user-1", "nonexistent")

        assert result is None


class TestSaveAndGetSummary:
    """测试 save_summary 和 get_summary 方法"""

    @pytest.mark.asyncio
    async def test_save_summary(self, memory_storage, mock_store, sample_summary):
        """测试保存会话摘要"""
        await memory_storage.save_summary("user-1", "thread-1", sample_summary)

        mock_store.aput.assert_called_once()
        call_args = mock_store.aput.call_args
        assert call_args[0][0] == ("memory", "summaries", "user-1", "thread-1")
        assert call_args[0][1] == "thread-1"

    @pytest.mark.asyncio
    async def test_get_summary_exists(self, memory_storage, mock_store, sample_summary):
        """测试获取存在的会话摘要"""
        mock_item = MagicMock()
        mock_item.value = {
            "thread_id": "thread-1",
            "topic": "测试主题",
            "key_points": ["要点1", "要点2"],
            "decisions": ["决定1"],
            "action_items": ["任务1"],
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.aget = AsyncMock(return_value=mock_item)

        result = await memory_storage.get_summary("user-1", "thread-1")

        assert result is not None
        assert result.thread_id == "thread-1"
        assert result.topic == "测试主题"

    @pytest.mark.asyncio
    async def test_get_summary_not_exists(self, memory_storage, mock_store):
        """测试获取不存在的会话摘要"""
        mock_store.aget = AsyncMock(return_value=None)

        result = await memory_storage.get_summary("user-1", "nonexistent")

        assert result is None


class TestSearchEntities:
    """测试 search_entities 方法"""

    @pytest.mark.asyncio
    async def test_search_entities(self, memory_storage, mock_store):
        """测试搜索记忆实体"""
        mock_item1 = MagicMock()
        mock_item1.value = {
            "id": "entity-1",
            "entity_type": EntityType.PERSON,
            "name": "张三",
            "description": "一个测试用户",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00"
        }
        mock_item2 = MagicMock()
        mock_item2.value = {
            "id": "entity-2",
            "entity_type": EntityType.LOCATION,
            "name": "北京",
            "description": "中国的首都",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.asearch = AsyncMock(return_value=[mock_item1, mock_item2])

        results = await memory_storage.search_entities("user-1", "test")

        assert len(results) == 2
        assert results[0].id == "entity-1"
        assert results[1].id == "entity-2"
        mock_store.asearch.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entities_with_limit(self, memory_storage, mock_store):
        """测试搜索记忆实体时指定 limit"""
        mock_store.asearch = AsyncMock(return_value=[])

        await memory_storage.search_entities("user-1", "test", limit=5)

        call_args = mock_store.asearch.call_args
        assert call_args[1]["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_entities_empty(self, memory_storage, mock_store):
        """测试搜索返回空结果"""
        mock_store.asearch = AsyncMock(return_value=[])

        results = await memory_storage.search_entities("user-1", "nonexistent")

        assert results == []


class TestSearchSummaries:
    """测试 search_summaries 方法"""

    @pytest.mark.asyncio
    async def test_search_summaries(self, memory_storage, mock_store):
        """测试搜索会话摘要"""
        mock_item1 = MagicMock()
        mock_item1.value = {
            "thread_id": "thread-1",
            "topic": "主题1",
            "key_points": ["要点1"],
            "decisions": [],
            "action_items": [],
            "created_at": "2024-01-01T00:00:00"
        }
        mock_item2 = MagicMock()
        mock_item2.value = {
            "thread_id": "thread-2",
            "topic": "主题2",
            "key_points": ["要点2"],
            "decisions": [],
            "action_items": [],
            "created_at": "2024-01-01T00:00:00"
        }
        mock_store.asearch = AsyncMock(return_value=[mock_item1, mock_item2])

        results = await memory_storage.search_summaries("user-1", "test")

        assert len(results) == 2
        assert results[0].thread_id == "thread-1"
        assert results[1].thread_id == "thread-2"

    @pytest.mark.asyncio
    async def test_search_summaries_with_limit(self, memory_storage, mock_store):
        """测试搜索会话摘要时指定 limit"""
        mock_store.asearch = AsyncMock(return_value=[])

        await memory_storage.search_summaries("user-1", "test", limit=3)

        call_args = mock_store.asearch.call_args
        assert call_args[1]["limit"] == 3

    @pytest.mark.asyncio
    async def test_search_summaries_empty(self, memory_storage, mock_store):
        """测试搜索返回空结果"""
        mock_store.asearch = AsyncMock(return_value=[])

        results = await memory_storage.search_summaries("user-1", "nonexistent")

        assert results == []
