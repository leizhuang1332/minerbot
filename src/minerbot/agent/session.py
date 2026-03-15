"""会话管理器"""
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.store.sqlite.aio import AsyncSqliteStore

from ..config import AppConfig


@dataclass
class SessionManager:
    """会话管理器"""
    checkpointer: AsyncSqliteSaver = field(repr=False)
    store: AsyncSqliteStore = field(repr=False)
    _conn: aiosqlite.Connection = field(repr=False)
    
    @classmethod
    async def create(cls, config: AppConfig) -> "SessionManager":
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = await aiosqlite.connect(str(db_path), isolation_level=None)
        checkpointer = AsyncSqliteSaver(conn)
        
        store_conn = await aiosqlite.connect(str(db_path), isolation_level=None)
        store = AsyncSqliteStore(store_conn)
        await store.setup()
        
        return cls(checkpointer=checkpointer, store=store, _conn=conn)
    
    async def close(self):
        await self._conn.close()
        await self.store.conn.close()
    
    def get_thread_config(self, thread_id: str, metadata: dict[str, object] | None = None):
        """获取线程配置
        
        Args:
            thread_id: 线程 ID
            metadata: 额外的元数据
            
        Returns:
            线程配置字典
        """
        return {
            "configurable": {
                "thread_id": thread_id,
                "metadata": metadata or {},
            }
        }
