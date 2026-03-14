"""会话管理器"""
import sqlite3
from pathlib import Path
from dataclasses import dataclass

from langgraph.checkpoint.sqlite import SqliteSaver

from ..config import AppConfig


@dataclass
class SessionManager:
    """会话管理器"""
    checkpointer: SqliteSaver
    
    @classmethod
    def create(cls, config: AppConfig) -> "SessionManager":
        """创建会话管理器
        
        Args:
            config: 应用配置
            
        Returns:
            SessionManager 实例
        """
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
        )
        
        checkpointer = SqliteSaver(conn)
        
        return cls(checkpointer=checkpointer)
    
    def get_thread_config(self, thread_id: str, metadata: dict | None = None):
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
