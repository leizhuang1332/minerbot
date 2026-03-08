"""MiniMax Provider
使用Anthropic兼容API的MiniMax LLM Provider
"""
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from ..factory import LLMProvider


class MiniMaxProvider(LLMProvider):
    """MiniMax LLM Provider
    
    使用Anthropic兼容API端点对接MiniMax服务
    """
    
    @property
    def name(self) -> str:
        return "minimax"
    
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: int = 30,
        default_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        """初始化MiniMax Provider
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API端点
            temperature: 温度参数
            max_tokens: 最大生成token数
            timeout: 超时时间(秒)
            default_headers: 自定义请求头
        """
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._default_headers = default_headers or {}
        self._extra_kwargs = kwargs
    
    @classmethod
    def from_config(cls, provider_config: Dict[str, Any]) -> "MiniMaxProvider":
        """从配置创建Provider
        
        Args:
            provider_config: Provider配置字典
            
        Returns:
            MiniMaxProvider实例
        """
        return cls(
            model=provider_config.get("model", "minimax/MiniMax-M2.5"),
            api_key=provider_config["api_key"],
            base_url=provider_config.get("base_url", "https://api.minimaxi.com/anthropic/"),
            temperature=provider_config.get("temperature", 0.7),
            max_tokens=provider_config.get("max_tokens", 1024),
            timeout=provider_config.get("timeout", 30),
            default_headers=provider_config.get("default_headers"),
        )
    
    def create(self, **kwargs: Any) -> BaseChatModel:
        """创建LLM实例
        
        Args:
            **kwargs: 覆盖默认参数
            
        Returns:
            ChatAnthropic实例
        """
        # 合并参数
        params: Dict[str, Any] = {
            "model": kwargs.get("model", self._model),
            "api_key": self._api_key,
            "base_url": kwargs.get("base_url", self._base_url),
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "timeout": kwargs.get("timeout", self._timeout),
        }
        
        # 添加默认请求头
        headers = self._default_headers.copy()
        extra_headers = kwargs.get("default_headers")
        if extra_headers:
            headers.update(extra_headers)
        if headers:
            params["default_headers"] = headers
        
        return ChatAnthropic(**params)
    
    def __repr__(self) -> str:
        return f"MiniMaxProvider(model={self._model}, base_url={self._base_url})"
