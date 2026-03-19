"""Store 模块 - 提供 LangGraph 持久化存储功能"""

import os
from sqlite3 import Connection, connect

from langgraph.store.sqlite import SqliteStore


def get_store(db_path: str | None = None) -> SqliteStore | None:
    """获取配置好的 SqliteStore 持久化存储器。
    
    Args:
        db_path: 数据库文件路径，默认从环境变量 SQLITE_DB_PATH 读取，
                 若未设置则使用 "data/minerbot.db"
    
    Returns:
        SqliteStore 实例，初始化失败时返回 None
    """
    try:
        if db_path is None:
            db_path = os.getenv("SQLITE_DB_PATH", "data/minerbot.db")

        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            db_path = os.path.join(base_dir, db_path)

        conn: Connection = connect(db_path, check_same_thread=False)
        store = SqliteStore(conn)

        return store

    except Exception:
        return None
