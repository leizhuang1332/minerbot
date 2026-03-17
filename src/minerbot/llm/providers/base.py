"""LLM 提供商基类"""
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig


class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    # 提供商名称
    provider_name: str = ""
    
    # 支持的模型列表
    supported_models: list[str] = []
    
    # 默认环境变量
    default_env_var: str = ""
    
    # 默认 base_url
    default_base_url: str | None = None
    
    def __init__(self):
        self._validate_provider()
    
    def _validate_provider(self):
        if not self.provider_name:
            raise ValueError("provider_name 不能为空")
    
    @abstractmethod
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        """创建 LLM 实例"""
        pass
    
    def is_model_supported(self, model_name: str) -> bool:
        """检查模型是否支持"""
        if "*" in self.supported_models:
            return True
        return model_name in self.supported_models
    
    def validate_config(self, _config: LLMConfig) -> None:
        """验证配置（可由子类重写）"""
        # 默认实现不做验证，子类可重写
