"""Anthropic 提供商"""
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig
from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic 提供商"""
    
    provider_name = "anthropic"
    supported_models = [
        "claude-sonnet-4-20250514",
        "claude-opus-4-5-20250501",
        "claude-sonnet-4-6",
        "claude-3-5-sonnet-20241022",
        "*",  # 支持所有模型
    ]
    default_env_var = "ANTHROPIC_API_KEY"
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        api_key = config.get_api_key(self.default_env_var)
        
        return ChatAnthropic(
            model_name=config.get_model(),
            api_key=api_key,
            base_url=config.base_url or "https://api.anthropic.com",
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
