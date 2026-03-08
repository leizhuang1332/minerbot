"""LLM Providers
支持的LLM Provider实现
"""
from .minimax import MiniMaxProvider
from ..factory import LLMFactory

# 自动注册所有Provider
LLMFactory.register("minimax", MiniMaxProvider)
