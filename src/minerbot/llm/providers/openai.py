"""OpenAI 提供商"""
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI 提供商"""
    
    provider_name = "openai"
    supported_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "*",
    ]
    default_env_var = "OPENAI_API_KEY"
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        api_key = config.get_api_key(self.default_env_var)
        
        return ChatOpenAI(
            model=config.get_model(),
            api_key=api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
