"""Checkpointer 模块 - 提供 LangGraph 检查点持久化功能"""

import os
from sqlite3 import connect

from langgraph.checkpoint.sqlite import SqliteSaver


def get_checkpointer(db_path: str | None = None) -> SqliteSaver | None:
    """获取配置好的 SqliteSaver 检查点存储器。"""
    try:
        if db_path is None:
            db_path = os.getenv("SQLITE_DB_PATH", "data/minerbot.db")

        if not os.path.isabs(db_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            db_path = os.path.join(base_dir, db_path)

        conn = connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        return checkpointer

    except Exception:
        return None
