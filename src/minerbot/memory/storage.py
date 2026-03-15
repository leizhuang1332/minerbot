"""记忆存储模块"""
from __future__ import annotations
from dataclasses import asdict
from typing import TYPE_CHECKING

from langgraph.store.sqlite.aio import AsyncSqliteStore

from minerbot.types import MemoryEntity, SessionSummary

if TYPE_CHECKING:
    from langgraph.store.base import SearchItem


class MemoryStorage:
    """记忆存储封装类
    
    封装 AsyncSqliteStore 提供记忆实体的持久化存储和检索功能。
    """
    
    def __init__(
        self,
        store: AsyncSqliteStore,
        namespace_prefix: str = "memory"
    ) -> None:
        """初始化记忆存储
        
        Args:
            store: AsyncSqliteStore 实例
            namespace_prefix: 命名空间前缀，默认 "memory"
        """
        self._store: AsyncSqliteStore = store
        self._namespace_prefix: str = namespace_prefix
    
    def _entity_namespace(self, user_id: str) -> tuple[str, ...]:
        """获取实体命名空间"""
        return (self._namespace_prefix, "entities", user_id)
    
    def _summary_namespace(self, user_id: str, thread_id: str) -> tuple[str, ...]:
        """获取摘要命名空间"""
        return (self._namespace_prefix, "summaries", user_id, thread_id)
    
    async def save_entity(self, user_id: str, entity: MemoryEntity) -> None:
        """保存记忆实体
        
        Args:
            user_id: 用户 ID
            entity: 记忆实体
        """
        namespace = self._entity_namespace(user_id)
        await self._store.aput(
            namespace,
            entity.id,
            asdict(entity)
        )
    
    async def save_summary(
        self,
        user_id: str,
        thread_id: str,
        summary: SessionSummary
    ) -> None:
        """保存会话摘要
        
        Args:
            user_id: 用户 ID
            thread_id: 线程 ID
            summary: 会话摘要
        """
        namespace = self._summary_namespace(user_id, thread_id)
        await self._store.aput(
            namespace,
            thread_id,
            asdict(summary)
        )
    
    async def search_entities(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> list[MemoryEntity]:
        """搜索记忆实体
        
        Args:
            user_id: 用户 ID
            query: 搜索查询
            limit: 返回结果数量限制
        
        Returns:
            记忆实体列表
        """
        namespace = self._entity_namespace(user_id)
        results: list[SearchItem] = await self._store.asearch(
            namespace,
            query=query,
            limit=limit
        )
        return [
            MemoryEntity(
                id=item.value["id"],
                entity_type=item.value["entity_type"],
                name=item.value["name"],
                description=item.value["description"],
                metadata=item.value["metadata"],
                created_at=item.value["created_at"]
            )
            for item in results
        ]
    
    async def search_summaries(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> list[SessionSummary]:
        """搜索会话摘要
        
        Args:
            user_id: 用户 ID
            query: 搜索查询
            limit: 返回结果数量限制
        
        Returns:
            会话摘要列表
        """
        namespace = (self._namespace_prefix, "summaries", user_id)
        results: list[SearchItem] = await self._store.asearch(
            namespace,
            query=query,
            limit=limit
        )
        return [
            SessionSummary(
                thread_id=item.value["thread_id"],
                topic=item.value["topic"],
                key_points=item.value["key_points"],
                decisions=item.value["decisions"],
                action_items=item.value["action_items"],
                created_at=item.value["created_at"]
            )
            for item in results
        ]
    
    async def get_entity(
        self,
        user_id: str,
        entity_id: str
    ) -> MemoryEntity | None:
        """获取单个记忆实体
        
        Args:
            user_id: 用户 ID
            entity_id: 实体 ID
        
        Returns:
            记忆实体，如果不存在则返回 None
        """
        namespace = self._entity_namespace(user_id)
        item = await self._store.aget(namespace, entity_id)
        if item is None:
            return None
        return MemoryEntity(
            id=item.value["id"],
            entity_type=item.value["entity_type"],
            name=item.value["name"],
            description=item.value["description"],
            metadata=item.value["metadata"],
            created_at=item.value["created_at"]
        )
    
    async def get_summary(
        self,
        user_id: str,
        thread_id: str
    ) -> SessionSummary | None:
        """获取单个会话摘要
        
        Args:
            user_id: 用户 ID
            thread_id: 线程 ID
        
        Returns:
            会话摘要，如果不存在则返回 None
        """
        namespace = self._summary_namespace(user_id, thread_id)
        item = await self._store.aget(namespace, thread_id)
        if item is None:
            return None
        return SessionSummary(
            thread_id=item.value["thread_id"],
            topic=item.value["topic"],
            key_points=item.value["key_points"],
            decisions=item.value["decisions"],
            action_items=item.value["action_items"],
            created_at=item.value["created_at"]
        )
