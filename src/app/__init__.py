"""App Module

应用核心模块，提供服务、REPL 和配置管理。

Usage:
    from src.app import Service, REPL, Config
"""

# 导出核心类 (占位符 - 实际实现后续添加)
from .config import Config
from .repl import REPL
from .service import Service

__all__ = [
    "Service",
    "REPL", 
    "Config",
]
