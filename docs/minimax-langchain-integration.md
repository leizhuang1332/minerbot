# Minimax M2.5 模型接入 LangChain + DeepAgents 指南

## 概述

本文档介绍如何将 MiniMax M2.5 模型接入 LangChain 和 DeepAgents 框架。

---

## 1. MiniMax M2.5 API 基础信息

### 1.1 API 端点

| 属性 | 值 |
|------|-----|
| 基础 URL | `https://api.minimax.io` |
| 聊天完成端点 | `/v1/chat/completions` |
| API 版本 | v2 |

### 1.2 支持的模型

| 模型名称 | 说明 |
|---------|------|
| `MiniMax-M2.5` | 最新旗舰模型 |
| `MiniMax-M2.5-highspeed` | 高速版本 |
| `MiniMax-M2.1` | M2.1 版本 |
| `MiniMax-M2` | M2 版本 |

### 1.3 认证方式

```python
# 认证格式
Authorization: Bearer YOUR_API_KEY
```

**获取 API Key**: [MiniMax Platform - Account Management](https://platform.minimax.io/user-center/basic-information/interface-key)

---

## 2. 集成方案对比

### 方案对比表

| 方案 | 难度 | 灵活性 | 推荐场景 |
|------|------|--------|----------|
| **方案A: OpenAI 兼容模式** | ⭐ 最简单 | 中 | 快速接入 |
| **方案B: langchain_community 内置** | ⭐⭐ 简单 | 中 | 使用官方集成 |
| **方案C: 自定义 BaseChatModel** | ⭐⭐⭐ 中等 | 高 | 完全控制 |

---

## 3. 方案 A: OpenAI 兼容模式（推荐）

这是最简单的接入方式。MiniMax API 与 OpenAI API 兼容，可以直接使用 OpenAI SDK。

### 3.1 安装依赖

```bash
pip install openai
```

### 3.2 基本用法

```python
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

# 发送请求
response = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)
```

### 3.3 流式输出

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

stream = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[
        {"role": "user", "content": "Write a story about AI."}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### 3.4 推理分离模式（思考过程）

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[
        {"role": "user", "content": "Solve this math problem: 2+2=?"}
    ],
    extra_body={"reasoning_split": True}  # 开启推理分离
)

# 打印思考过程
print(f"Thinking: {response.choices[0].message.reasoning_details[0]['text']}")
# 打印最终答案
print(f"Answer: {response.choices[0].message.content}")
```

---

## 4. 方案 B: langchain_community 内置集成

LangChain 官方已经支持 MiniMax，可以通过 `langchain_community` 包使用。

### 4.1 安装依赖

```bash
pip install langchain langchain-community
```

### 4.2 使用 MiniMax Chat Model

```python
import os
from langchain_community.chat_models import MiniMaxChat

# 设置环境变量
os.environ["MINIMAX_API_KEY"] = "your-api-key"
os.environ["MINIMAX_GROUP_ID"] = "your-group-id"

# 初始化聊天模型
chat = MiniMaxChat(
    model="MiniMax-M2.5",
    temperature=0.7
)

# 使用 LCEL 语法
from langchain_core.messages import HumanMessage

response = chat.invoke([HumanMessage(content="Hello!")])
print(response.content)
```

### 4.3 在 LangChain Agent 中使用

```python
import os
from langchain.agents import create_agent
from langchain_community.chat_models import MiniMaxChat

os.environ["MINIMAX_API_KEY"] = "your-api-key"
os.environ["MINIMAX_GROUP_ID"] = "your-group-id"

# 创建 Agent
agent = create_agent(
    model=MiniMaxChat(model="MiniMax-M2.5"),
    tools=[your_tool],
    system_prompt="You are a helpful assistant."
)

# 运行 Agent
result = agent.invoke({"messages": [{"role": "user", "content": "Your question"}]})
```

---

## 5. 方案 C: 自定义 BaseChatModel

如果需要完全控制或使用最新功能，可以创建自定义 ChatModel。

### 5.1 基础实现

```python
from typing import Any, Dict, List, Optional
import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun

class MiniMaxChatModel(BaseChatModel):
    """自定义 MiniMax Chat Model"""
    
    model_name: str = "MiniMax-M2.5"
    api_key: str
    base_url: str = "https://api.minimax.io/v1"
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    @property
    def _llm_type(self) -> str:
        return "minimax-chat"
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # 将 LangChain 消息转换为 API 格式
        api_messages = self._convert_messages(messages)
        
        # 调用 API
        response = self._call_api(api_messages, **kwargs)
        
        # 解析响应
        content = response["choices"][0]["message"]["content"]
        
        # 返回 ChatResult
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))]
        )
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict]:
        """将 LangChain 消息转换为 API 格式"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                role = "user"  # 默认
            result.append({
                "role": role,
                "content": msg.content
            })
        return result
    
    def _call_api(self, messages: List[Dict], **kwargs) -> Dict:
        """调用 MiniMax API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            **kwargs
        }
        
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise ValueError(f"API Error: {response.text}")
        
        return response.json()
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature
        }
```

### 5.2 使用自定义模型

```python
# 初始化
chat = MiniMaxChatModel(
    api_key="your-api-key",
    model_name="MiniMax-M2.5",
    temperature=0.7
)

# 使用
response = chat.invoke([HumanMessage(content="Hello!")])
print(response.content)
```

### 5.3 添加流式支持

```python
from typing import Any, Dict, List, Optional, Iterator
from langchain_core.outputs import ChatGenerationChunk

class MiniMaxChatModelStreaming(BaseChatModel):
    """支持流式输出的 MiniMax Chat Model"""
    
    model_name: str = "MiniMax-M2.5"
    api_key: str
    base_url: str = "https://api.minimax.io/v1"
    temperature: float = 0.7
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "stream": True,
            "temperature": self.temperature
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60
        )
        
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                if data.startswith('data: '):
                    chunk_data = json.loads(data[6:])
                    if 'choices' in chunk_data and chunk_data['choices']:
                        delta = chunk_data['choices'][0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            yield ChatGenerationChunk(
                                message=AIMessageChunk(content=content)
                            )
```

---

## 6. DeepAgents 集成

DeepAgents 是 LangChain 的新一代 Agent 框架，提供自动压缩长对话、虚拟文件系统等功能。

### 6.1 基本用法

```python
from langchain.agents import create_agent
from langchain_community.chat_models import MiniMaxChat
import os

os.environ["MINIMAX_API_KEY"] = "your-api-key"
os.environ["MINIMAX_GROUP_ID"] = "your-group-id"

# 定义工具
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"The weather in {city} is sunny."

# 创建 Agent
agent = create_agent(
    model=MiniMaxChat(model="MiniMax-M2.5"),
    tools=[get_weather],
    system_prompt="You are a helpful weather assistant."
)

# 运行
result = agent.invoke({
    "messages": [{"role": "user", "content": "What's the weather in Tokyo?"}]
})

print(result)
```

### 6.2 使用 OpenAI 兼容模式

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# 使用 OpenAI 兼容客户端
llm = ChatOpenAI(
    model="MiniMax-M2.5",
    openai_api_key="your-minimax-key",
    openai_api_base="https://api.minimax.io/v1",
    temperature=0.7
)

agent = create_agent(
    model=llm,
    tools=[your_tool],
    system_prompt="Your system prompt"
)

result = agent.invoke({"messages": [{"role": "user", "content": "Your query"}]})
```

---

## 7. 完整示例

### 7.1 最小可用示例

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.5",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### 7.2 LangChain Agent 完整示例

```python
import os
from langchain.agents import create_agent, AgentType
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.chat_models import MiniMaxChat

# 设置 API Key
os.environ["MINIMAX_API_KEY"] = "your-key"

# 创建搜索工具
search = DuckDuckGoSearchRun()

# 创建 Agent
agent = create_agent(
    model=MiniMaxChat(model="MiniMax-M2.5"),
    tools=[search],
    agent_type=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# 运行
agent.invoke({
    "input": "What is the latest news about AI?"
})
```

---

## 8. 常见问题

### Q1: 如何获取 API Key?

访问 [MiniMax Platform](https://platform.minimax.io) -> Account Management -> API Keys

### Q2: 遇到 401 错误?

检查：
1. API Key 是否正确
2. API Key 是否过期
3. Group ID 是否正确（如果使用 langchain_community）

### Q3: 支持哪些参数?

| 参数 | 说明 | 默认值 |
|------|------|--------|
| temperature | 采样温度 | 0.7 |
| max_tokens | 最大生成 token 数 | - |
| top_p | 核采样 | 1.0 |
| stream | 是否流式输出 | false |
| reasoning_split | 是否分离推理过程 | false |

### Q4: 如何处理错误?

```python
from openai import OpenAI

try:
    client = OpenAI(
        api_key="YOUR_KEY",
        base_url="https://api.minimax.io/v1"
    )
    response = client.chat.completions.create(
        model="MiniMax-M2.5",
        messages=[{"role": "user", "content": "Hi"}]
    )
except Exception as e:
    print(f"Error: {e}")
```

---

## 9. 参考资源

- [MiniMax 官方文档](https://platform.minimax.io/docs)
- [LangChain 官方文档](https://python.langchain.com)
- [LangChain Custom Chat Model](https://python.langchain.com/v0.2/docs/how_to/custom_chat_model)
- [OpenAI SDK 兼容性](https://platform.minimax.io/docs/api-reference/text-openai-api)

---

## 10. 总结

| 方案 | 代码量 | 适用场景 |
|------|--------|----------|
| OpenAI 兼容 | 5 行 | 快速原型 |
| langchain_community | 10 行 | 生产使用 |
| 自定义 | 50+ 行 | 特殊需求 |

**推荐**: 优先使用方案 A（OpenAI 兼容），简单稳定。如需更多 LangChain 特性，使用方案 B。
