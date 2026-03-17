# LLM 工厂模式快速开始指南

## 1. 环境准备

### 1.1 安装依赖

项目依赖已在 `pyproject.toml` 中声明，确保已安装：

```bash
uv sync
```

### 1.2 配置 API Key

在项目根目录创建或编辑 `.env` 文件：

```bash
# 根据你使用的模型配置对应的 API Key
# MiniMax (当前默认)
MINIMAX_API_KEY=sk-cp-your-key

# 或 Anthropic
# ANTHROPIC_API_KEY=sk-ant-your-key

# 或 OpenAI
# OPENAI_API_KEY=sk-your-key
```

---

## 2. 快速使用

### 2.1 最简使用

```python
from minerbot.llm.factory import LLMFactory

# 直接使用 model_name 字符串
llm = LLMFactory.create_llm_instance("minimax/MiniMax-M2.5")
```

### 2.2 使用配置文件

```python
from minerbot.llm.factory import LLMFactory

# 加载配置文件
config = LLMFactory.load_config("config/llm.yaml")

# 使用默认模型
llm = LLMFactory.create_llm_instance(config["model_name"])
```

### 2.3 自定义参数

```python
from minerbot.llm.factory import LLMFactory

# 方式1: 字典配置
llm = LLMFactory.create_llm_instance({
    "model_name": "minimax/MiniMax-M2.5",
    "temperature": 0.5,
    "max_tokens": 4096,
})

# 方式2: 覆盖默认参数
llm = LLMFactory.create_llm_instance(
    "minimax/MiniMax-M2.5",
    temperature=0.3,
    max_tokens=2048
)
```

---

## 3. 切换模型示例

### 3.1 切换到 Anthropic

```python
# 设置环境变量
import os
os.environ["DEFAULT_MODEL"] = "anthropic/claude-sonnet-4-6"

# 或直接指定
llm = LLMFactory.create_llm_instance("anthropic/claude-sonnet-4-6")
```

### 3.2 切换到 OpenAI

```python
llm = LLMFactory.create_llm_instance("openai/gpt-4o")
```

### 3.3 切换到 Google Gemini

```python
llm = LLMFactory.create_llm_instance("google/gemini-2.0-flash")
```

---

## 4. 在 super_agent.py 中使用

```python
# src/agent/super_agent.py

import os
from dotenv import load_dotenv
from minerbot.llm.factory import LLMFactory

load_dotenv()

# 从环境变量或配置文件读取默认模型
model_name = os.getenv("DEFAULT_MODEL", "minimax/MiniMax-M2.5")
llm = LLMFactory.create_llm_instance(model_name)

# 后续使用方式不变
super_agent = create_deep_agent(
    model=llm,
    # ...
)
```

---

## 5. 错误处理

```python
from minerbot.llm.factory import LLMFactory
from minerbot.llm.exceptions import (
    UnsupportedProviderError,
    InvalidConfigError,
)

try:
    llm = LLMFactory.create_llm_instance("minimax/MiniMax-M2.5")
except UnsupportedProviderError as e:
    print(f"不支持的提供商: {e}")
    print(f"支持的提供商: {LLMFactory.get_supported_providers()}")
except InvalidConfigError as e:
    print(f"配置错误: {e}")
except ValueError as e:
    print(f"参数错误: {e}")
```

---

## 6. 可用的模型列表

| model_name | 提供商 | 环境变量 |
|------------|--------|----------|
| `anthropic/claude-sonnet-4-6` | Anthropic | ANTHROPIC_API_KEY |
| `anthropic/claude-opus-4-5-20250501` | Anthropic | ANTHROPIC_API_KEY |
| `openai/gpt-4o` | OpenAI | OPENAI_API_KEY |
| `openai/gpt-4o-mini` | OpenAI | OPENAI_API_KEY |
| `google/gemini-2.0-flash` | Google | GOOGLE_API_KEY |
| `minimax/MiniMax-M2.5` | MiniMax | MINIMAX_API_KEY |
