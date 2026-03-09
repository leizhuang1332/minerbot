# DeepAgents 流式调用 API 文档

本文档基于 MVP 测试结果整理，详细说明 DeepAgents 流式调用的 API 语法、输入输出参数规格。

## 一、基础语法

### 1.1 Agent 创建

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# 创建模型实例
model = ChatAnthropic(
    model="minimax/MiniMax-M2.5",
    api_key="your-api-key",
    base_url="https://api.minimaxi.com/anthropic/"
)

# 创建 Agent
agent = create_deep_agent(
    model=model,
    system_prompt="你是一个简洁的助手",
    tools=[],
    subagents=[],
)
```

### 1.2 流式调用基础

```python
from langchain_core.messages import HumanMessage

# stream_mode: 流式模式
# subgraphs: 是否启用子 Agent 流式

for chunk in agent.stream(
    {"messages": [HumanMessage(content="你好")]},
    stream_mode="messages",
):
    # 处理流式数据
    pass
```

---

## 二、stream_mode 参数详解

| 模式 | 说明 | 返回数据结构 |
|------|------|-------------|
| `"messages"` | 流式传输 token | `(token, metadata)` 元组 |
| `"updates"` | 流式传输节点更新 | 字典 `{node_name: data}` |
| `"custom"` | 流式传输自定义事件 | 自定义数据 |
| `["updates", "messages", "custom"]` | 组合模式 | `(mode, data)` 元组 |

### 2.1 stream_mode="messages"

流式传输 LLM 生成的 token。

```python
for chunk in agent.stream(
    {"messages": [HumanMessage(content="用一句话介绍你自己")]},
    stream_mode="messages",
):
    token, metadata = chunk
    
    # MiniMax 模型返回 thinking + text 结构
    if hasattr(token, 'content') and isinstance(token.content, list):
        for item in token.content:
            if isinstance(item, dict) and 'text' in item:
                print(item['text'], end="", flush=True)
    elif hasattr(token, 'content') and token.content:
        print(token.content, end="", flush=True)
```

**输出示例：**
```
[{'thinking': '用户用', 'type': 'thinking', 'index': 0}]
[{'thinking': '中文问我"用一句话介绍你自己"...', 'type': 'thinking', 'index': 0}]
[{'text': '我是Deep', 'type': 'text', 'index': 1}]
[{'text': ' Agent，一个AI助手...', 'type': 'text', 'index': 1}]
```

**metadata 结构：**
```python
{
    'id': 'lc_run--xxx',
    'response_metadata': {
        'id': 'xxx',
        'model': 'MiniMax-M2.5',
        'stop_reason': 'end_turn',
        'usage': {'input_tokens': 5607, 'output_tokens': 46}
    }
}
```

### 2.2 stream_mode="updates"

流式传输每个执行步骤的完整状态更新。

```python
for chunk in agent.stream(
    {"messages": [HumanMessage(content="你好")]}
):
    # chunk 是字典 {node_name: data}
    for node_name, data in chunk.items():
        print(f"节点: {node_name}")
        print(f"数据: {data}")
```

**输出示例：**
```python
# 更新 1
{
    'PatchToolCallsMiddleware.before_agent': {
        'messages': Overwrite(value=[HumanMessage(content='你好', ...)])
    }
}

# 更新 2
{
    'model': {
        'messages': [AIMessage(content=[...], response_metadata={...})]
    }
}

# 更新 3
{'TodoListMiddleware.after_model': None}
```

### 2.3 stream_mode="custom"

流式传输自定义事件（需要使用 `get_stream_writer`）。

```python
from langgraph.config import get_stream_writer

# 在工具中发射自定义事件
@tool
def my_tool():
    writer = get_stream_writer()
    writer({"status": "starting", "progress": 0})
    writer({"status": "complete", "progress": 100})
    return "结果"
```

---

## 三、subgraphs 参数

### 3.1 启用子 Agent 流式

```python
agent = create_deep_agent(
    model=model,
    system_prompt="你是协调者，将任务委托给研究人员",
    subagents=[
        {
            "name": "researcher",
            "description": "研究人员",
            "system_prompt": "你是一个研究员，提供简洁的研究结果",
        },
    ],
)

# 启用 subgraphs=True
for namespace, chunk in agent.stream(
    {"messages": [HumanMessage(content="研究量子计算")]},
    stream_mode="messages",
    subgraphs=True,  # 关键参数
):
    # namespace 标识来源
    # - () 空元组 = 主 Agent
    # - ("tools:xxx",) = 子 Agent
    is_subagent = any(s.startswith("tools:") for s in namespace)
    source = "subagent" if is_subagent else "main"
    
    token, metadata = chunk
    print(f"[{source}] {token.content}")
```

### 3.2 namespace 规格

| Namespace | 来源 |
|-----------|------|
| `()` | 主 Agent |
| `("tools:abc123",)` | 由 task 工具调用的子 Agent |
| `("tools:abc123", "model_request:def456")` | 子 Agent 内部节点 |

---

## 四、完整示例

### 4.1 基础流式对话

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

# 1. 创建模型
model = ChatAnthropic(
    model="minimax/MiniMax-M2.5",
    api_key="your-key",
    base_url="https://api.minimaxi.com/anthropic/"
)

# 2. 创建 Agent
agent = create_deep_agent(
    model=model,
    system_prompt="你是一个简洁的助手",
    tools=[],
    subagents=[],
)

# 3. 流式对话
for chunk in agent.stream(
    {"messages": [HumanMessage(content="你好")])},
    stream_mode="messages",
):
    token, metadata = chunk
    if hasattr(token, 'content') and isinstance(token.content, list):
        for item in token.content:
            if isinstance(item, dict) and 'text' in item:
                print(item['text'], end="", flush=True)
    elif token.content:
        print(token.content, end="", flush=True)

print()  # 换行
```

### 4.2 带子 Agent 的流式

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

model = ChatAnthropic(
    model="minimax/MiniMax-M2.5",
    api_key="your-key",
    base_url="https://api.minimaxi.com/anthropic/"
)

agent = create_deep_agent(
    model=model,
    system_prompt="你是协调者，将任务委托给研究人员",
    subagents=[
        {
            "name": "researcher",
            "description": "研究人员",
            "system_prompt": "你是一个研究员",
        },
    ],
)

for namespace, chunk in agent.stream(
    {"messages": [HumanMessage(content="研究量子计算")]]},
    stream_mode="messages",
    subgraphs=True,
):
    token, metadata = chunk
    
    # 识别来源
    is_subagent = any(s.startswith("tools:") for s in namespace)
    source = "subagent" if is_subagent else "main"
    
    # 输出内容
    if hasattr(token, 'content') and isinstance(token.content, list):
        for item in token.content:
            if isinstance(item, dict) and 'text' in item:
                print(f"[{source}] {item['text']}", end="", flush=True)
    elif token.content:
        print(f"[{source}] {token.content}", end="", flush=True)

print()
```

---

## 五、参数速查表

### 5.1 agent.stream() 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input` | `dict` | 是 | 输入消息字典 `{"messages": [...]}` |
| `config` | `RunnableConfig` | 否 | 运行配置 |
| `stream_mode` | `str \| list` | 否 | 流式模式: `"messages"`, `"updates"`, `"custom"`, `["updates", "messages", "custom"]` |
| `subgraphs` | `bool` | 否 | 是否启用子 Agent 流式，默认为 `False` |
| `output_keys` | `str \| list` | 否 | 指定输出键 |
| `interrupt_before` | `str \| list` | 否 | 中断前执行节点 |
| `interrupt_after` | `str \| list` | 否 | 中断后执行节点 |
| `debug` | `bool` | 否 | 调试模式 |

### 5.2 输入消息格式

```python
# 方式1: 字典格式
{"messages": [{"role": "user", "content": "你好"}]}

# 方式2: Message 对象
{"messages": [HumanMessage(content="你好")]}
```

### 5.3 流式输出格式

**stream_mode="messages":**
```python
(token: AIMessage, metadata: dict)
```

**stream_mode="updates":**
```python
{node_name: state_data}
```

**组合模式:**
```python
(mode: str, data: Any)
```

---

## 六、MiniMax 模型特殊处理

### 6.1 内容结构

MiniMax M2.5 模型返回的 `AIMessage.content` 是列表格式：

```python
[
    {'thinking': '...', 'type': 'thinking', 'index': 0},
    {'text': 'Hello', 'type': 'text', 'index': 1}
]
```

### 6.2 解析代码

```python
def extract_text(token):
    """从 MiniMax 响应中提取文本"""
    if hasattr(token, 'content') and isinstance(token.content, list):
        texts = []
        for item in token.content:
            if isinstance(item, dict):
                if 'text' in item:
                    texts.append(item['text'])
                elif 'thinking' in item:
                    # 可选：处理 thinking
                    pass
        return ''.join(texts)
    elif token.content:
        return str(token.content)
    return ''
```

---

## 七、相关资源

- [官方流式文档](https://docs.langchain.com/oss/python/deepagents/streaming/overview)
- [子 Agent 文档](https://docs.langchain.com/oss/python/deepagents/subagents)
- [LangChain 流式概述](https://docs.langchain.com/oss/python/langchain/streaming/overview)
