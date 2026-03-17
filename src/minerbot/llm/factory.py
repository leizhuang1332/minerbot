"""LLM 工厂类"""
from typing import Dict, List, Union
import yaml
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from pydantic import ValidationError

from .config import LLMConfig
from .providers.base import BaseLLMProvider
from .providers.anthropic import AnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.minimax import MiniMaxProvider
from .providers.google import GoogleProvider
from .exceptions import (
    LLMFactoryError,
    UnsupportedProviderError,
    InvalidConfigError,
)


class LLMFactory:
    """LLM 工厂类 - 根据配置自动创建 LLM 实例"""
    
    _providers: Dict[str, BaseLLMProvider] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(cls) -> None:
        """初始化工厂，注册默认提供商"""
        if cls._initialized:
            return
        
        # 注册默认提供商
        cls.register_provider(AnthropicProvider())
        cls.register_provider(OpenAIProvider())
        cls.register_provider(MiniMaxProvider())
        cls.register_provider(GoogleProvider())
        
        cls._initialized = True
    
    @classmethod
    def register_provider(cls, provider: BaseLLMProvider) -> None:
        """注册 LLM 提供商"""
        if not isinstance(provider, BaseLLMProvider):
            raise TypeError("provider 必须继承自 BaseLLMProvider")
        
        cls._providers[provider.provider_name] = provider
    
    @classmethod
    def create_llm_instance(
        cls,
        config: Union[LLMConfig, dict, str],
        **override_kwargs
    ) -> BaseChatModel:
        """
        创建 LLM 实例
        
        Args:
            config: LLMConfig 实例、字典或 model_name 字符串
            **override_kwargs: 覆盖配置参数
            
        Returns:
            BaseChatModel 实例
            
        Raises:
            UnsupportedProviderError: 不支持的提供商
            InvalidConfigError: 无效配置
        """
        if not cls._initialized:
            cls.initialize()
        
        # 解析配置
        if isinstance(config, str):
            config = LLMConfig(model_name=config)
        elif isinstance(config, dict):
            config = LLMConfig(**config)
        elif not isinstance(config, LLMConfig):
            raise InvalidConfigError(
                f"config 必须是 LLMConfig、dict 或 str，当前: {type(config)}"
            )
        
        # 应用覆盖参数
        for key, value in override_kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # 获取提供商
        provider_name = config.get_provider()
        
        provider = cls._providers.get(provider_name)
        if not provider:
            supported = cls.get_supported_providers()
            raise UnsupportedProviderError(
                f"不支持的提供商: {provider_name}\n"
                f"支持的提供商: {', '.join(supported)}\n"
                f"支持的模型格式: provider/model-name (如 anthropic/claude-sonnet-4-6)"
            )
        
        # 验证配置
        try:
            provider.validate_config(config)
        except ValidationError as e:
            raise InvalidConfigError(f"配置验证失败: {e}")
        
        # 创建实例
        return provider.create_llm(config)
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """获取支持的提供商列表"""
        return list(cls._providers.keys())
    
    @classmethod
    def load_config(cls, config_path: str) -> dict:
        """加载 YAML 配置文件"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
