"""会话管理器"""
import aiosqlite
from pathlib import Path
from dataclasses import dataclass, field

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ..config import AppConfig


@dataclass
class SessionManager:
    """会话管理器"""
    checkpointer: AsyncSqliteSaver = field(repr=False)
    _conn: aiosqlite.Connection = field(repr=False)
    
    @classmethod
    async def create(cls, config: AppConfig) -> "SessionManager":
        """创建会话管理器
        
        Args:
            config: 应用配置
            
        Returns:
            SessionManager 实例
        """
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = await aiosqlite.connect(str(db_path))
        checkpointer = AsyncSqliteSaver(conn)
        
        return cls(checkpointer=checkpointer, _conn=conn)
    
    async def close(self):
        """关闭连接"""
        await self._conn.close()
    
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
