"""Google 提供商"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig
from .base import BaseLLMProvider


class GoogleProvider(BaseLLMProvider):
    """Google 提供商"""
    
    provider_name = "google"
    supported_models = [
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "*",
    ]
    default_env_var = "GOOGLE_API_KEY"
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        api_key = config.get_api_key(self.default_env_var)
        
        return ChatGoogleGenerativeAI(
            model=config.get_model(),
            google_api_key=api_key,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
        )
