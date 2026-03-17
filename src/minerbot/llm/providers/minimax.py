"""MiniMax 提供商"""
from langchain_anthropic import ChatAnthropic  # MiniMax 兼容 Anthropic API
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig
from .base import BaseLLMProvider


class MiniMaxProvider(BaseLLMProvider):
    """MiniMax 提供商（兼容 Anthropic API）"""
    
    provider_name = "minimax"
    supported_models = [
        "MiniMax-M2.5",
        "MiniMax-Text-01",
        "*",
    ]
    default_env_var = "MINIMAX_API_KEY"
    default_base_url = "https://api.minimaxi.com/anthropic/"
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        api_key = config.get_api_key(self.default_env_var)
        
        return ChatAnthropic(
            model_name=config.get_model(),
            api_key=api_key,
            base_url=config.base_url or self.default_base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
