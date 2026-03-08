"""LLM Module
统一的LLM工厂服务，支持多种Provider的灵活切换

Usage:
    # 方式1: 使用默认Provider
    from src.llms import get_llm
    llm = get_llm()
    
    # 方式2: 指定Provider
    from src.llms import get_llm, switch_llm
    llm = get_llm(provider="minimax")
    
    # 方式3: 切换Provider
    llm = switch_llm("minimax")
    
    # 方式4: 获取当前实例
    from src.llms import current_llm, list_providers
    llm = current_llm()
    print(list_providers())  # ["minimax"]
"""
# 导入Provider模块以自动注册
from . import providers

# 导出工厂接口
from .factory import (
    LLMFactory,
    get_llm,
    switch_llm,
    current_llm,
    list_providers,
)

# 导出配置
from .config import config as llm_config

__all__ = [
    # 工厂接口
    "LLMFactory",
    "get_llm",
    "switch_llm", 
    "current_llm",
    "list_providers",
    # 配置
    "llm_config",
]
