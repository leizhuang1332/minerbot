"""LLM Factory
统一的LLM工厂服务，支持多种Provider的灵活切换
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from .config import config


class LLMProvider(ABC):
    """LLM Provider基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider名称"""
        pass
    
    @abstractmethod
    def create(self, **kwargs: Any) -> BaseChatModel:
        """创建LLM实例"""
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, provider_config: Dict[str, Any]) -> "LLMProvider":
        """从配置创建Provider"""
        pass


# 类型别名
LLMInstance = Union[Runnable[Any, Any], BaseChatModel]


class LLMFactory:
    """LLM工厂类 - 统一入口"""
    
    _providers: Dict[str, Type[LLMProvider]] = {}
    _current_provider: Optional[str] = None
    _instance: Optional[LLMInstance] = None
    
    @classmethod
    def register(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """注册Provider"""
        cls._providers[name] = provider_class
    
    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> LLMProvider:
        """获取Provider实例"""
        provider_name = name or config.default_provider
        
        if provider_name not in cls._providers:
            raise ValueError(
                f"Provider '{provider_name}' not registered. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[provider_name]
        provider_config = config.get_provider_config(provider_name)
        
        return provider_class.from_config(provider_config)
    
    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> BaseChatModel:
        """创建LLM实例
        
        Args:
            provider: Provider名称，默认为配置中的默认Provider
            model: 模型名称，可覆盖配置中的模型
            **kwargs: 其他参数
            
        Returns:
            LLM实例
        """
        provider_name = provider or config.default_provider
        provider_obj = cls.get_provider(provider_name)
        
        llm = provider_obj.create(**kwargs)
        
        # 可选：覆盖模型名称
        if model:
            llm = llm.bind(model=model)
        
        cls._current_provider = provider_name
        cls._instance = llm
        
        return cast(BaseChatModel, llm)
        cls._instance = llm
        
        return llm
    
    @classmethod
    def get_current(cls) -> Optional[BaseChatModel]:
        """获取当前实例"""
        if cls._instance is None:
            return None
        return cast(BaseChatModel, cls._instance)
    
    @classmethod
    def get_current_provider(cls) -> Optional[str]:
        """获取当前Provider名称"""
        return cls._current_provider
    
    @classmethod
    def switch_provider(cls, provider: str, **kwargs: Any) -> BaseChatModel:
        """切换Provider
        
        Args:
            provider: 新的Provider名称
            **kwargs: 传递给新Provider的参数
            
        Returns:
            新的LLM实例
        """
        cls._instance = None  # 清除缓存
        return cls.create(provider=provider, **kwargs)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有已注册的Provider"""
        return list(cls._providers.keys())


# 便捷函数
def get_llm(provider: Optional[str] = None, **kwargs: Any) -> BaseChatModel:
    """获取LLM实例的便捷函数"""
    return LLMFactory.create(provider=provider, **kwargs)


def switch_llm(provider: str, **kwargs: Any) -> BaseChatModel:
    """切换LLM的便捷函数"""
    return LLMFactory.switch_provider(provider, **kwargs)


def current_llm() -> Optional[BaseChatModel]:
    """获取当前LLM实例"""
    return LLMFactory.get_current()


def list_providers() -> List[str]:
    """列出所有可用的Provider"""
    return LLMFactory.list_providers()
