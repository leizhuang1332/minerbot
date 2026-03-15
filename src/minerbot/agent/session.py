"""会话管理器"""
from __future__ import annotations
import aiosqlite
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from langchain_anthropic import ChatAnthropic
from langchain_core.runnables.config import RunnableConfig
from pydantic.types import SecretStr
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

from ..config import AppConfig

if TYPE_CHECKING:
    from ..memory import (
        EntityExtractor,
        MemoryStorage,
        SessionSummarizer,
        TaskScheduler,
        TriggerManager,
        TriggerType,
    )

logger = logging.getLogger(__name__)


@dataclass
class SessionManager:
    checkpointer: AsyncSqliteSaver = field(repr=False)
    store: AsyncSqliteStore = field(repr=False)
    _conn: aiosqlite.Connection = field(repr=False)
    _config: AppConfig = field(repr=False)
    _memory_enabled: bool = field(default=False, repr=False)
    memory_storage: "MemoryStorage | None" = field(default=None, repr=False)
    entity_extractor: "EntityExtractor | None" = field(default=None, repr=False)
    session_summarizer: "SessionSummarizer | None" = field(default=None, repr=False)
    task_scheduler: "TaskScheduler | None" = field(default=None, repr=False)
    trigger_manager: "TriggerManager | None" = field(default=None, repr=False)
    _memory_queue: "asyncio.Queue[tuple[str, str, TriggerType]]" = field(
        default_factory=asyncio.Queue, repr=False
    )
    _memory_queue_task: asyncio.Task[None] | None = field(default=None, repr=False)

    @classmethod
    async def create(cls, config: AppConfig, memory_storage: "MemoryStorage | None" = None) -> "SessionManager":
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(str(db_path), isolation_level=None)
        checkpointer = AsyncSqliteSaver(conn)

        store_conn = await aiosqlite.connect(str(db_path), isolation_level=None)
        store = AsyncSqliteStore(store_conn)
        await store.setup()

        instance = cls(
            checkpointer=checkpointer,
            store=store,
            _conn=conn,
            _config=config,
            memory_storage=memory_storage,
        )

        if config.memory_enabled:
            await instance._init_memory_components(config)

        return instance

    async def _init_memory_components(self, config: AppConfig) -> None:
        from ..memory import (
            EntityExtractor,
            MemoryStorage,
            SessionSummarizer,
            TaskScheduler,
            TriggerManager,
        )

        logger.info("初始化 memory 组件...")

        if self.memory_storage is None:
            self.memory_storage = MemoryStorage(self.store)

        model = ChatAnthropic(
            model_name=config.memory_summary_model,
            api_key=SecretStr(config.anthropic_api_key),
            timeout=None,
            stop=None,
        )

        self.entity_extractor = EntityExtractor(model)
        self.session_summarizer = SessionSummarizer(model)
        self.task_scheduler = TaskScheduler(max_workers=2)
        await self.task_scheduler.start()

        self.trigger_manager = TriggerManager(config)

        self._memory_enabled = True
        logger.info("memory 组件初始化完成")

    async def process_memory_extraction(self, thread_id: str, user_id: str) -> bool:
        if not self._memory_enabled:
            logger.debug("记忆功能未启用，跳过记忆提取")
            return False

        assert self.entity_extractor is not None
        assert self.session_summarizer is not None
        assert self.memory_storage is not None

        try:
            config: RunnableConfig = RunnableConfig(
                configurable={"thread_id": thread_id, "metadata": {}}
            )
            messages = []
            async for msg in self.checkpointer.alist(config, limit=50):
                messages.append(msg)

            if not messages:
                logger.debug("没有消息可供提取")
                return False

            entities = await self.entity_extractor.extract(messages, user_id)
            for entity in entities:
                await self.memory_storage.save_entity(user_id, entity)

            messages_dict = [
                {"role": "user", "content": m.content}
                for m in messages
            ]
            summary = await self.session_summarizer.summarize(messages_dict, thread_id)
            await self.memory_storage.save_summary(user_id, thread_id, summary)

            logger.info(f"记忆提取完成: thread={thread_id}, entities={len(entities)}")
            return True

        except Exception as e:
            logger.error(f"记忆提取失败: {e}")
            return False

    async def trigger_memory_extraction(
        self,
        thread_id: str,
        user_id: str,
        trigger_type: "TriggerType"
    ) -> None:
        if not self._memory_enabled:
            return

        logger.info(f"触发记忆提取: thread={thread_id}, trigger={trigger_type.value}")
        await self._memory_queue.put((thread_id, user_id, trigger_type))

    async def _start_memory_queue_processor(self) -> None:
        if self._memory_queue_task is not None:
            return

        async def process_loop():
            while True:
                try:
                    thread_id, user_id, trigger_type = await self._memory_queue.get()
                    logger.debug(f"从队列处理记忆提取: {thread_id}")

                    await self.process_memory_extraction(thread_id, user_id)

                    self._memory_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"记忆队列处理错误: {e}")

        self._memory_queue_task = asyncio.create_task(process_loop())

    async def close(self):
        if self.task_scheduler and self.task_scheduler.is_running:
            await self.task_scheduler.stop()

        if self.trigger_manager:
            await self.trigger_manager.stop_idle_monitor()

        if self._memory_queue_task:
            self._memory_queue_task.cancel()
            try:
                await self._memory_queue_task
            except asyncio.CancelledError:
                pass

        await self._conn.close()
        await self.store.conn.close()

    def get_thread_config(self, thread_id: str, metadata: dict[str, object] | None = None):
        return {
            "configurable": {
                "thread_id": thread_id,
                "metadata": metadata or {},
            }
        }

    def get_memory_storage(self) -> "MemoryStorage | None":
        return self.memory_storage

    @property
    def is_memory_enabled(self) -> bool:
        return self._memory_enabled
