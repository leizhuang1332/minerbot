# LLM 工厂模式初始化方案设计

## 概述

本文档描述了一个基于工厂模式的 LLM 实例初始化方案，支持通过配置文件设置模型参数并根据模型名称自动创建对应实例。该方案专为 minerbot 项目设计（基于 LangChain + DeepAgents 的 CLI AI 助手）。

---

## 1. 架构设计

### 1.1 模块划分

```
src/minerbot/
├── llm/
│   ├── __init__.py           # 导出工厂函数和配置类
│   ├── config.py             # LLM 配置模型（Pydantic）
│   ├── factory.py            # 工厂模式核心实现
│   ├── providers/            # 提供商适配器目录
│   │   ├── __init__.py
│   │   ├── base.py           # BaseLLMProvider 抽象基类
│   │   ├── anthropic.py      # Anthropic 提供商
│   │   ├── openai.py         # OpenAI 提供商
│   │   ├── google.py         # Google 提供商
│   │   └── minimax.py        # MiniMax 提供商
│   └── exceptions.py         # 异常定义
└── agent/
    └── super_agent.py        # 现有代码，改造使用工厂
```

### 1.2 类图

```
┌─────────────────────────────────────────────────────────────┐
│                    LLMConfig (Pydantic)                     │
├─────────────────────────────────────────────────────────────┤
│ - model_name: str          # "anthropic/claude-sonnet-4"    │
│ - api_key: Optional[str]   # 或从环境变量加载               │
│ - base_url: Optional[str] # 自定义端点                     │
│ - temperature: float       # 默认 0.7                       │
│ - max_tokens: Optional[int]                                 │
│ - timeout: Optional[int]                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  BaseLLMProvider (ABC)                       │
├─────────────────────────────────────────────────────────────┤
│ + provider_name: str                                        │
│ + supported_models: List[str]                               │
│ + create_llm(config: LLMConfig) -> BaseChatModel           │
└─────────────────────────────────────────────────────────────┘
           ▲                    ▲                    ▲
           │                    │                    │
    ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
    │AnthropicProv│      │ OpenAIProv  │      │MiniMaxProv  │
    └─────────────┘      └─────────────┘      └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       LLMFactory                            │
├─────────────────────────────────────────────────────────────┤
│ + _providers: Dict[str, BaseLLMProvider]                   │
│ + register_provider(provider: BaseLLMProvider)             │
│ + create_llm_instance(config) -> BaseChatModel              │
│ + get_supported_providers() -> List[str]                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 配置文件设计

### 2.1 配置文件格式 (YAML)

创建文件 `config/llm.yaml`：

```yaml
# LLM 配置文件
model_name: "minimax/MiniMax-M2.5"

# 可选：自定义端点
base_url: ""

# 可选：API Key 环境变量名
api_key: "$MINIMAX_API_KEY"

model_params:
  temperature: 0.7
  max_tokens: 4096
  timeout: 60
```

### 2.2 环境变量配置

在 `.env` 文件中配置 API Key：

```bash
# 必需：根据使用的模型配置对应的 API Key
# 支持多个提供商，只需配置实际使用的

# Anthropic (Claude 系列)
ANTHROPIC_API_KEY=sk-ant-xxx

# OpenAI (GPT 系列)
OPENAI_API_KEY=sk-xxx

# MiniMax
MINIMAX_API_KEY=sk-cp-xxx

# Google (Gemini 系列)
GOOGLE_API_KEY=xxx
```

### 2.3 模型名称格式规范

| 模型名称示例 | 提供商 | 模型名 |
|-------------|--------|--------|
| `anthropic/claude-sonnet-4-6` | anthropic | claude-sonnet-4-6 |
| `anthropic/claude-opus-4-5-20250501` | anthropic | claude-opus-4-5-20250501 |
| `openai/gpt-4o` | openai | gpt-4o |
| `openai/gpt-4o-mini` | openai | gpt-4o-mini |
| `google/gemini-2.0-flash` | google | gemini-2.0-flash |
| `minimax/MiniMax-M2.5` | minimax | MiniMax-M2.5 |

---

## 3. 核心实现

### 3.1 异常定义 (exceptions.py)

```python
"""LLM 模块异常定义"""

class LLMFactoryError(Exception):
    """工厂基础异常"""
    pass

class UnsupportedProviderError(LLMFactoryError):
    """不支持的提供商异常"""
    pass

class InvalidConfigError(LLMFactoryError):
    """无效配置异常"""
    pass

class ModelNotSupportedError(LLMFactoryError):
    """模型不支持异常"""
    pass
```

### 3.2 配置模型 (config.py)

```python
"""LLM 配置模型"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import os


class LLMConfig(BaseModel):
    """LLM 配置模型"""
    
    model_name: str = Field(..., description="格式: provider/model-name")
    api_key: Optional[str] = Field(default=None, description="API Key")
    base_url: Optional[str] = Field(default=None, description="自定义端点")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: Optional[int] = Field(default=60, ge=1)
    
    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证 model_name 格式"""
        if "/" not in v:
            raise ValueError(
                f"model_name 格式错误，应为 'provider/model-name'，当前: {v}"
            )
        return v
    
    def get_provider(self) -> str:
        """从 model_name 自动解析提供商名称"""
        return self.model_name.split("/")[0].lower()
    
    def get_model(self) -> str:
        """从 model_name 提取模型名称"""
        return "/".join(self.model_name.split("/")[1:])
    
    def get_api_key(self, default_env_var: str) -> str:
        """获取 API Key，优先：配置文件值 > 环境变量"""
        if self.api_key:
            # 支持 $ENV_VAR 格式
            if self.api_key.startswith("$"):
                env_name = self.api_key[1:]
                key = os.getenv(env_name)
                if key:
                    return key
                raise ValueError(f"API Key 环境变量 {env_name} 未设置")
            return self.api_key
        # 回退到默认环境变量
        key = os.getenv(default_env_var)
        if key:
            return key
        raise ValueError(f"API Key 未配置，请设置环境变量 {default_env_var}")
    
    class Config:
        frozen = True
```

### 3.3 提供商基类 (providers/base.py)

```python
"""LLM 提供商基类"""
from abc import ABC, abstractmethod
from typing import List, Optional
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig


class BaseLLMProvider(ABC):
    """LLM 提供商抽象基类"""
    
    # 提供商名称
    provider_name: str = ""
    
    # 支持的模型列表
    supported_models: List[str] = []
    
    # 默认环境变量
    default_env_var: str = ""
    
    # 默认 base_url
    default_base_url: Optional[str] = None
    
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
    
    def validate_config(self, config: LLMConfig) -> None:
        """验证配置（可由子类重写）"""
        pass
```

### 3.4 Anthropic 提供商 (providers/anthropic.py)

```python
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
```

### 3.5 MiniMax 提供商 (providers/minimax.py)

```python
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
```

### 3.6 OpenAI 提供商 (providers/openai.py)

```python
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
```

### 3.7 Google 提供商 (providers/google.py)

```python
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
```

### 3.8 工厂类 (factory.py)

```python
"""LLM 工厂类"""
from typing import Dict, List, Optional, Union
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
```

### 3.9 导出模块 (__init__.py)

```python
"""LLM 工厂模块"""
from .config import LLMConfig
from .factory import LLMFactory
from .exceptions import (
    LLMFactoryError,
    UnsupportedProviderError,
    InvalidConfigError,
    ModelNotSupportedError,
)

__all__ = [
    "LLMConfig",
    "LLMFactory",
    "LLMFactoryError",
    "UnsupportedProviderError",
    "InvalidConfigError",
    "ModelNotSupportedError",
]
```

---

## 4. 与现有代码集成

### 4.1 super_agent.py 改造

```python
# src/agent/super_agent.py

import os
from dotenv import load_dotenv

# 新增：导入工厂
from minerbot.llm.factory import LLMFactory

load_dotenv()

# ========== 1. 使用工厂创建 LLM 实例 ==========

# 方式A: 从环境变量读取默认模型
model_name = os.getenv("DEFAULT_MODEL", "minimax/MiniMax-M2.5")
llm = LLMFactory.create_llm_instance(model_name)

# 方式B: 从配置文件加载
# config = LLMFactory.load_config("config/llm.yaml")
# model_name = config.get("model_name", "minimax/MiniMax-M2.5")
# llm = LLMFactory.create_llm_instance(model_name)

# 方式C: 完全自定义配置
# llm = LLMFactory.create_llm_instance({
#     "model_name": "minimax/MiniMax-M2.5",
#     "temperature": 0.5,
#     "base_url": "https://api.minimaxi.com/anthropic/",
# })

# ... 后续代码不变 ...
```

---

## 5. 错误处理

### 5.1 错误类型说明

| 错误类型 | 触发条件 | 示例错误信息 |
|---------|---------|-------------|
| `UnsupportedProviderError` | 提供商不存在 | "不支持的提供商: xxx\n支持的提供商: anthropic, openai, minimax, google" |
| `InvalidConfigError` | 配置验证失败 | "配置验证失败: ..." |
| `ValueError` (config) | model_name 格式错误 | "model_name 格式错误，应为 'provider/model-name'" |
| `ValueError` (api_key) | API Key 未配置 | "API Key 未配置，请设置环境变量 MINIMAX_API_KEY" |

### 5.2 错误处理示例

```python
from minerbot.llm.factory import LLMFactory
from minerbot.llm.exceptions import (
    UnsupportedProviderError,
    InvalidConfigError,
)

try:
    llm = LLMFactory.create_llm_instance("minimax/MiniMax-M2.5")
except UnsupportedProviderError as e:
    print(f"错误: {e}")
    print(f"支持的提供商: {LLMFactory.get_supported_providers()}")
except InvalidConfigError as e:
    print(f"配置错误: {e}")
except ValueError as e:
    print(f"参数错误: {e}")
except Exception as e:
    print(f"未知错误: {type(e).__name__}: {e}")
```

---

## 6. 扩展指南

### 6.1 添加新的 LLM 提供商

假设要添加 Cohere 提供商：

**Step 1: 创建提供商类**

```python
# src/minerbot/llm/providers/cohere.py
from langchain_cohere import ChatCohere
from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig
from .base import BaseLLMProvider


class CohereProvider(BaseLLMProvider):
    """Cohere 提供商"""
    
    provider_name = "cohere"
    supported_models = ["command-r", "command-r-plus", "*"]
    default_env_var = "COHERE_API_KEY"
    
    def create_llm(self, config: LLMConfig) -> BaseChatModel:
        api_key = config.get_api_key(self.default_env_var)
        
        return ChatCohere(
            model=config.get_model(),
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
```

**Step 2: 注册提供商**

```python
# 在 factory.py 的 initialize() 中添加
from .providers.cohere import CohereProvider

cls.register_provider(CohereProvider())
```

**Step 3: 配置使用**

```bash
# .env
COHERE_API_KEY=xxx
```

```yaml
# config/llm.yaml
model_name: "cohere/command-r-plus"
```

### 6.2 提供商注册机制

```python
# 动态注册提供商
from minerbot.llm.factory import LLMFactory

# 方式1: 在代码中注册
LLMFactory.register_provider(CustomProvider())

# 方式2: 通过配置文件自动发现（可选扩展）
# 扫描 providers/ 目录，自动注册所有 Provider 类
```

---

## 7. 测试用例设计

### 7.1 单元测试示例

```python
# tests/test_llm_factory.py
import pytest
from unittest.mock import patch, MagicMock

from minerbot.llm.factory import LLMFactory
from minerbot.llm.config import LLMConfig
from minerbot.llm.exceptions import (
    UnsupportedProviderError,
    InvalidConfigError,
)


class TestLLMConfig:
    """测试配置模型"""
    
    def test_parse_provider_from_model_name(self):
        """测试从 model_name 解析提供商"""
        config = LLMConfig(model_name="anthropic/claude-sonnet-4-6")
        assert config.get_provider() == "anthropic"
        assert config.get_model() == "claude-sonnet-4-6"
    
    def test_invalid_model_name_format(self):
        """测试无效的 model_name 格式"""
        with pytest.raises(ValueError, match="model_name 格式错误"):
            LLMConfig(model_name="invalid-name")
    
    def test_temperature_validation(self):
        """测试温度参数范围"""
        with pytest.raises(ValueError):
            LLMConfig(model_name="test/model", temperature=3.0)


class TestLLMFactory:
    """测试工厂类"""
    
    def test_create_instance_with_string(self):
        """测试使用字符串创建实例"""
        with patch('ChatAnthropic') as mock:
            mock.return_value = MagicMock()
            llm = LLMFactory.create_llm_instance("anthropic/claude-sonnet-4-6")
            assert mock.called
    
    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        with pytest.raises(UnsupportedProviderError) as exc_info:
            LLMFactory.create_llm_instance("unknown/model")
        assert "不支持的提供商" in str(exc_info.value)
        assert "anthropic" in str(exc_info.value)
    
    def test_get_supported_providers(self):
        """测试获取支持的提供商列表"""
        providers = LLMFactory.get_supported_providers()
        assert "anthropic" in providers
        assert "openai" in providers
        assert "minimax" in providers
        assert "google" in providers


class TestProviders:
    """测试各提供商"""
    
    @patch.dict('os.environ', {'MINIMAX_API_KEY': 'test-key'})
    def test_minimax_provider(self):
        """测试 MiniMax 提供商"""
        config = LLMConfig(model_name="minimax/MiniMax-M2.5")
        provider = LLMFactory._providers["minimax"]
        llm = provider.create_llm(config)
        assert llm is not None
```

---

## 8. 实施步骤

| 步骤 | 任务 | 预估时间 |
|-----|------|----------|
| 1 | 创建 `src/minerbot/llm/` 目录结构 | 0.5h |
| 2 | 实现 `exceptions.py` 异常定义 | 0.5h |
| 3 | 实现 `config.py` 配置模型 | 1h |
| 4 | 实现 `providers/base.py` 基类 | 0.5h |
| 5 | 实现各提供商类 (4个) | 2h |
| 6 | 实现 `factory.py` 工厂类 | 1h |
| 7 | 实现 `__init__.py` 导出 | 0.5h |
| 8 | 创建 `config/llm.yaml` 示例 | 0.5h |
| 9 | 更新 `.env.example` | 0.5h |
| 10 | 改造 `super_agent.py` | 1h |
| 11 | 编写单元测试 | 2h |

**预估总工作量**: 约 10 小时

---

## 9. 依赖说明

项目已有依赖（无需新增）：

- `langchain-core` - 核心接口
- `langchain-anthropic` - Anthropic/MiniMax 支持
- `langchain-openai` - OpenAI 支持
- `pyyaml` - 配置文件解析
- `python-dotenv` - 环境变量加载

如需 Google 支持，需添加：

```bash
uv add langchain-google-genai
```

---

## 10. 常见问题

### Q1: 如何切换不同的模型？

修改 `config/llm.yaml` 中的 `model_name` 或设置环境变量 `DEFAULT_MODEL`。

### Q2: 如何使用自定义的模型端点？

```python
llm = LLMFactory.create_llm_instance({
    "model_name": "openai/gpt-4o",
    "base_url": "https://your-custom-endpoint.com/v1",
})
```

### Q3: 如何查看所有支持的提供商？

```python
from minerbot.llm.factory import LLMFactory
print(LLMFactory.get_supported_providers())
```

### Q4: API Key 优先级是怎样的？

1. 传入的 `api_key` 参数
2. 环境变量
3. 抛出异常提示未配置
