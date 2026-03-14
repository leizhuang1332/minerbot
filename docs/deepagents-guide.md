# DeepAgents 框架详解

DeepAgents 是一个基于 LangChain 和 LangGraph 构建的 AI Agent 框架，专为需要工具调用、文件系统操作、子代理管理的高级 AI 助手设计。本文档将详细介绍如何接入不同的 LLM、创建 Agent 以及配置记忆系统。

## 目录

1. [LLM 接入配置](#llm-接入配置)
2. [创建 Agent](#创建-agent)
3. [记忆系统配置](#记忆系统配置)

---

## LLM 接入配置

### 支持的模型提供商

DeepAgents 支持多种 LLM 提供商，通过 LangChain 的 `init_chat_model` 函数进行初始化：

| 提供商 | model_provider | 示例模型名称 |
|--------|----------------|-------------|
| Anthropic | `anthropic` | `claude-3-opus-20240229`, `claude-sonnet-4-6` |
| OpenAI | `openai` | `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo` |
| Google Vertex AI | `google_vertexai` | `gemini-1.5-pro`, `gemini-1.5-flash` |
| Google GenAI | `google_genai` | `gemini-pro` |
| Azure OpenAI | `azure_openai` | `gpt-4o` |
| Ollama | `ollama` | `llama2`, `mistral` |
| Groq | `groq` | `llama3-70b-8192` |
| Cohere | `cohere` | `command-r-plus` |
| Bedrock | `bedrock` | `anthropic.claude-3-sonnet` |

### 安装依赖

```bash
# 核心包
pip install langchain langchain-core

# 各Provider包
pip install langchain-openai      # OpenAI
pip install langchain-anthropic   # Anthropic
pip install langchain-google-vertexai  # Google Vertex AI
pip install langchain-google-genai    # Google GenAI
pip install langchain-ollama      # Ollama
pip install langchain-groq        # Groq
```

### API 密钥配置

#### 方式一：环境变量（推荐）

```bash
# OpenAI
export OPENAI_API_KEY="your-openai-key"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"

# Google
export GOOGLE_API_KEY="your-google-key"
```

#### 方式二：代码中设置

```python
import os
from getpass import getpass

# Anthropic
os.environ["ANTHROPIC_API_KEY"] = getpass()

# OpenAI
os.environ["OPENAI_API_KEY"] = "your-key"
```

#### 方式三：直接在初始化时传入

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    api_key="your-api-key",
    base_url="https://api.openai.com/v1"
)
```

### 基本配置

```python
from deepagents import create_deep_agent

# 使用默认模型 (Claude Sonnet 4.6)
agent = create_deep_agent()

# 使用字符串模型标识符
agent = create_deep_agent(model="openai:gpt-4o")
agent = create_deep_agent(model="claude-sonnet-4-6")

# 直接传入已初始化的模型实例
from langchain.chat_models import init_chat_model

# Anthropic
from langchain_anthropic import ChatAnthropic
anthropic_model = ChatAnthropic(
    model_name="claude-sonnet-4-6",
    temperature=0.7,
    max_tokens=4096,
)

# OpenAI
openai_model = init_chat_model(
    model="gpt-4o",
    temperature=0.7,
)

agent = create_deep_agent(model=anthropic_model)
```

### 完整配置示例

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain.chat_models import init_chat_model
import os

# ==================== Anthropic 配置 ====================
anthropic_agent = create_deep_agent(
    model=ChatAnthropic(
        model_name="claude-sonnet-4-6",  # 模型名称
        temperature=0.7,                   # 创造性控制 (0-1)
        max_tokens=4096,                    # 最大输出 tokens
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    ),
    # 其他参数...
)

# ==================== OpenAI 配置 ====================
openai_agent = create_deep_agent(
    model=init_chat_model(
        model="openai:gpt-4o",              # 使用 provider:model 格式
        temperature=0.7,
        max_tokens=4096,
        # OpenAI 特有参数
        base_url=None,                      # 自定义端点
        api_key=os.getenv("OPENAI_API_KEY"),
    ),
)

# ==================== OpenAI Responses API ====================
# 默认情况下，openai: 前缀使用 Responses API
# 如需使用 Chat Completions API：
chat_completions_agent = create_deep_agent(
    model=init_chat_model(
        model="openai:o1-preview",
        use_responses_api=False,             # 禁用 Responses API
    ),
)

# 禁用数据保留 (Responses API)
secure_agent = create_deep_agent(
    model=init_chat_model(
        model="openai:o1-preview",
        use_responses_api=True,
        store=False,                         # 不存储请求数据
        include=["reasoning.encrypted_content"],
    ),
)
```

### 连接验证

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# 初始化模型
model = ChatAnthropic(model_name="claude-sonnet-4-6")

# 创建 agent
agent = create_deep_agent(model=model)

# 测试连接 - 使用异步调用
import asyncio
from langchain_core.messages import HumanMessage

async def test_connection():
    # 通过 agent 的配置创建配置对象
    config = {"configurable": {"thread_id": "test"}}
    
    # 发送测试消息
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content="Say 'Hello, world!' and nothing else.")]},
        config=config
    )
    
    # 检查响应
    response = result["messages"][-1].content
    print(f"Agent response: {response}")
    return response

# 运行测试
response = asyncio.run(test_connection())

# 同步调用方式
config = {"configurable": {"thread_id": "test_sync"}}
result = agent.invoke(
    {"messages": [("user", "Say 'Hello' and nothing else.")]},
    config=config
)
print(f"Response: {result['messages'][-1].content}")
```

### 动态配置模型参数

DeepAgents 支持在运行时动态修改模型参数：

```python
from langchain.chat_models import init_chat_model

# 创建一个可配置的模型
configurable_model = init_chat_model(
    "openai:gpt-4o",
    configurable_fields="any",  # 允许动态配置任何参数
    temperature=0
)

# 在调用时修改参数
result = configurable_model.invoke(
    "hello",
    config={"configurable": {"temperature": 0.5}}
)
```

---

## 创建 Agent

### 基础 Agent 创建

```python
from deepagents import create_deep_agent

# 最简单的创建方式 - 使用默认配置
agent = create_deep_agent()

# 指定系统提示词
agent = create_deep_agent(
    system_prompt="你是一个专业的 Python 开发者助手。",
)

# 指定名称
agent = create_deep_agent(
    name="DevAssistant",
    system_prompt="你是一个专业的 Python 开发者助手。",
)
```

### 添加自定义工具

```python
from deepagents import create_deep_agent
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic

# 定义自定义工具
@tool
def calculate(expression: str) -> str:
    """执行数学计算。
    
    Args:
        expression: 数学表达式，如 "2+2" 或 "sqrt(16)"
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {"sqrt": lambda x: x**0.5})
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"

@tool  
def get_weather(location: str) -> str:
    """获取指定位置的天气信息。
    
    Args:
        location: 城市名称，如 "Beijing"
    """
    # 实际实现中应该调用天气 API
    return f"{location} 的天气: 晴朗, 25°C"

# 创建带工具的 agent
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    tools=[calculate, get_weather],
)
```

### 配置子代理 (SubAgents)

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# 定义子代理配置
research_agent = {
    "name": "researcher",
    "description": "用于研究和搜索信息的子代理",
    "system_prompt": "你是一个专业的研究助手，擅长搜索和分析信息。",
    "tools": [],  # 可以为子代理添加特定工具
}

code_agent = {
    "name": "coder", 
    "description": "用于编写和调试代码的子代理",
    "system_prompt": "你是一个专业的程序员，擅长编写高质量代码。",
}

# 创建带子代理的 agent
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    subagents=[research_agent, code_agent],
)
```

### 配置中间件

```python
from deepagents import create_deep_agent, MemoryMiddleware
from deepagents.backends import StateBackend, FilesystemBackend, StoreBackend
from langchain.agents.middleware import HumanInTheLoopMiddleware

# 使用 StateBackend (内存存储)
agent = create_deep_agent(
    backend=StateBackend,  # 默认后端
)

# 使用 FilesystemBackend (文件系统存储)
agent = create_deep_agent(
    backend=FilesystemBackend(root_dir="/project"),
)

# 使用 StoreBackend (持久化存储，需配置 store)
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = create_deep_agent(
    backend=lambda rt: StoreBackend(rt, namespace=lambda ctx: ("my_agent",)),
    store=store,
)

# 添加人机交互中间件
agent = create_deep_agent(
    interrupt_on={
        "edit_file": True,           # 编辑前中断
        "bash": True,               # 执行命令前中断
    },
)
```

### 完整配置示例

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
import os

# 环境变量配置
os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

# 自定义工具
@tool
def search_docs(query: str) -> str:
    """搜索文档内容。"""
    return f"关于 '{query}' 的搜索结果..."

# 创建 Checkpointer (会话状态持久化)
checkpointer = MemorySaver()

# 创建 Store (持久化存储)
store = InMemoryStore()

# 创建 Agent
agent = create_deep_agent(
    # 模型配置
    model=ChatAnthropic(
        model_name="claude-sonnet-4-6",
        temperature=0.7,
    ),
    
    # 工具配置
    tools=[search_docs],
    
    # 系统提示词
    system_prompt="你是一个专业的技术文档助手。",
    
    # 子代理配置
    subagents=[],
    
    # 技能配置
    skills=["/skills/user/", "/skills/project/"],
    
    # 记忆配置
    memory=["~/.deepagents/AGENTS.md", "./AGENTS.md"],
    
    # 状态持久化
    checkpointer=checkpointer,
    
    # 持久化存储
    store=store,
    
    # 后端配置
    backend=StateBackend,
    
    # 中断配置
    interrupt_on={
        "bash": True,
    },
    
    # 其他配置
    name="TechAssistant",
    debug=True,
)
```

---

## 记忆系统配置

### 概述

DeepAgents 提供了三种类型的记忆/持久化机制：

1. **Memory (记忆)**: 从 AGENTS.md 文件加载的上下文信息
2. **Checkpointer (检查点)**: 会话状态持久化，支持跨会话恢复
3. **Store (存储)**: 持久化数据存储，用于跨会话数据共享

### Memory 配置

#### 基本使用

```python
from deepagents import create_deep_agent, MemoryMiddleware
from deepagents.backends import StateBackend, FilesystemBackend

# 方式 1: 通过 create_deep_agent 的 memory 参数
agent = create_deep_agent(
    memory=[
        "~/.deepagents/AGENTS.md",      # 用户级别记忆
        "./AGENTS.md",                  # 项目级别记忆
    ],
)

# 方式 2: 手动创建 MemoryMiddleware
backend = FilesystemBackend(root_dir="/")

memory_middleware = MemoryMiddleware(
    backend=backend,
    sources=[
        "~/.deepagents/AGENTS.md",
        "./AGENTS.md",
    ],
)

agent = create_deep_agent(
    middleware=[memory_middleware],
)
```

#### AGENTS.md 文件格式

```markdown
# 我的 AI 助手

## 项目概述
这是一个用于辅助编程的 AI 助手。

## 代码规范
- 使用 4 空格缩进
- 类型注解使用 Python 3.11+ 语法
- 遵循 PEP 8 规范

## 常用命令
- 测试: uv run pytest
- 运行: uv run python main.py

## 用户偏好
- 用户喜欢简洁的回复
- 用户使用中文交流
```

#### MemoryMiddleware 详解

```python
from deepagents import MemoryMiddleware
from deepagents.backends import StateBackend, FilesystemBackend
from langchain.tools import ToolRuntime

# StateBackend (需要通过工厂函数)
def get_backend(rt: ToolRuntime):
    return StateBackend(rt)

memory_middleware = MemoryMiddleware(
    backend=get_backend,  # 工厂函数
    sources=[
        "~/.deepagents/AGENTS.md",
        "./AGENTS.md",
    ],
)

# FilesystemBackend (直接实例)
memory_middleware = MemoryMiddleware(
    backend=FilesystemBackend(root_dir="/"),
    sources=[
        "~/.deepagents/AGENTS.md",
    ],
)
```

### Checkpointer 配置

Checkpointer 用于持久化 Agent 的执行状态，实现会话恢复。

**关键概念**：
- **Checkpointer**：管理单线程内的短期内存（会话级持久化）
- **Store**：管理跨线程、跨会话的长期内存（用户级持久化）

#### MemorySaver / InMemorySaver (内存检查点)

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from langchain_anthropic import ChatAnthropic

# 方式 1: 使用 InMemorySaver
checkpointer = InMemorySaver()

# 方式 2: 使用 MemorySaver (推荐，功能相同)
checkpointer = MemorySaver()

# 创建 Agent
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    checkpointer=checkpointer,
)

# 使用会话 ID 调用
config = {"configurable": {"thread_id": "user_session_123"}}

# 第一次对话
result1 = agent.invoke(
    {"messages": [("user", "我的名字是张三")]},
    config=config
)

# 第二次对话 (自动加载之前的状态)
result2 = agent.invoke(
    {"messages": [("user", "我的名字是什么?")]},
    config=config
)
```

#### SqliteSaver (SQLite 持久化)

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

# 创建 SQLite 检查点
conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)

# 创建 Agent
agent = create_deep_agent(
    checkpointer=checkpointer,
)

# 加密持久化状态 (可选)
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer

serde = EncryptedSerializer.from_pycryptodome_aes()  # 需要设置 LANGGRAPH_AES_KEY 环境变量
checkpointer = SqliteSaver(conn, serde=serde)
```

#### PostgresSaver (PostgreSQL 持久化)

```python
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg2

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

# 方式 1: 上下文管理器
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()  # 首次需要初始化数据库表
    agent = create_deep_agent(checkpointer=checkpointer)

# 方式 2: 直接连接
conn = psycopg2.connect(
    host="localhost",
    database="agent_db",
    user="user",
    password="password"
)
checkpointer = PostgresSaver(conn)
```

#### RedisSaver (Redis 持久化)

```python
from langgraph.checkpoint.redis import RedisSaver

DB_URI = "redis://localhost:6379"

with RedisSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup()
    agent = create_deep_agent(checkpointer=checkpointer)
```

### Store 配置

Store 用于持久化任意数据，支持跨会话数据共享。

**关键概念**：
- **Checkpointer**：管理单线程内的短期内存（会话级持久化）
- **Store**：管理跨线程、跨会话的长期内存（用户级持久化）

#### InMemoryStore (内存存储)

```python
from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore

# 创建内存存储
store = InMemoryStore()

# 配置到 Agent
agent = create_deep_agent(
    store=store,
)

# 使用 store 存储和检索数据
import uuid

async def use_store_example(store):
    # 定义命名空间
    user_id = "user_123"
    namespace = (user_id, "memories")
    
    # 存储数据
    memory_id = str(uuid.uuid4())
    await store.aput(namespace, memory_id, {"content": "用户喜欢蓝色"})
    
    # 检索数据
    items = await store.asearch(namespace, query="用户偏好")
    
    return items
```

#### 启用语义搜索

```python
from langchain.embeddings import init_embeddings
from langgraph.store.memory import InMemoryStore

# 配置嵌入模型以启用语义搜索
store = InMemoryStore(
    index={
        "embed": init_embeddings("openai:text-embedding-3-small"),
        "dims": 1536,  # 嵌入维度
        "fields": ["content", "$"]  # 要索引的字段
    }
)
```

#### PostgreSQL 存储 (生产环境)

```python
from deepagents import create_deep_agent
from langgraph.store.postgres import PostgresStore

DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"

with PostgresStore.from_conn_string(DB_URI) as store:
    store.setup()  # 首次需要初始化数据库表
    agent = create_deep_agent(store=store)
```

#### Redis 存储 (生产环境)

```python
from langgraph.store.redis import RedisStore

DB_URI = "redis://localhost:6379"

with RedisStore.from_conn_string(DB_URI) as store:
    store.setup()
    agent = create_deep_agent(store=store)
```

### StoreBackend 集成

DeepAgents 的 StoreBackend 可以与 LangGraph Store 集成，实现文件系统的持久化：

```python
from deepagents import create_deep_agent
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

# 创建 Store
store = InMemoryStore()

# 定义 namespace 工厂函数
def namespace_factory(ctx):
    """为每个用户创建独立的 namespace"""
    user_id = ctx.runtime.context.get("user_id", "default")
    return ("users", user_id, "files")

# 创建 Agent
agent = create_deep_agent(
    store=store,
    backend=lambda rt: StoreBackend(rt, namespace=namespace_factory),
)
```

### 完整记忆系统配置示例

```python
from deepagents import create_deep_agent, MemoryMiddleware
from deepagents.backends import StateBackend, StoreBackend
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain.tools import ToolRuntime

# ==================== 1. Checkpointer 配置 ====================
# 内存检查点 - 适合开发/测试
checkpointer = MemorySaver()

# SQLite 检查点 - 适合生产环境
# from langgraph.checkpoint.sqlite import SqliteSaver
# import sqlite3
# conn = sqlite3.connect("checkpoints.db")
# checkpointer = SqliteSaver(conn)

# ==================== 2. Store 配置 ====================
# 内存存储 - 适合开发/测试
store = InMemoryStore()

# SQLite 存储 - 适合生产环境
# from langgraph.store.sqlite import SqliteStore
# store = SqliteStore(path="store.db")

# ==================== 3. Backend 配置 ====================
def get_store_backend(rt: ToolRuntime):
    """StoreBackend 工厂函数"""
    return StoreBackend(rt, namespace=lambda ctx: ("agent", "files"))

# ==================== 4. Memory 配置 ====================
memory_middleware = MemoryMiddleware(
    backend=StateBackend,  # 或使用 FilesystemBackend
    sources=[
        "~/.deepagents/AGENTS.md",
        "./AGENTS.md",
    ],
)

# ==================== 5. 创建 Agent ====================
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    
    # 记忆系统
    memory=["~/.deepagents/AGENTS.md"],
    checkpointer=checkpointer,
    store=store,
    
    # 后端
    backend=get_store_backend,
    
    # 自定义中间件
    # middleware=[memory_middleware],
    
    # 其他配置
    name="PersistentAssistant",
)
```

### Checkpointer 对比

| Checkpointer | 用途 | 持久化 | 适用场景 |
|--------------|------|--------|----------|
| `InMemorySaver` | 开发/测试 | ❌ 内存中 | 本地开发 |
| `MemorySaver` | 生产短期 | ✅ 内存级 | 短期会话 |
| `SqliteSaver` | 本地持久化 | ✅ SQLite 文件 | 本地工作流 |
| `PostgresSaver` | 生产环境 | ✅ PostgreSQL | 生产部署 |
| `RedisSaver` | 生产环境 | ✅ Redis | 高并发场景 |

### Store 对比

| Store 类型 | 用途 | 持久化 | 备注 |
|-----------|------|--------|------|
| `InMemoryStore` | 开发/测试 | ❌ 内存中 | 默认选项 |
| `PostgresStore` | 生产环境 | ✅ PostgreSQL | 推荐 |
| `RedisStore` | 生产环境 | ✅ Redis | 支持向量搜索 |

### 调用时必须指定 thread_id

```python
# 所有会话持久化都需要 thread_id
config = {"configurable": {"thread_id": "your-thread-id"}}
graph.invoke(input_data, config=config)

# ==================== 会话管理最佳实践 ====================

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# 全局配置
checkpointer = MemorySaver()
store = InMemoryStore()

# 创建 Agent
agent = create_deep_agent(
    checkpointer=checkpointer,
    store=store,
)

# ==================== 会话管理 ====================

def get_session_config(user_id: str, session_id: str = None):
    """生成会话配置"""
    import uuid
    return {
        "configurable": {
            "thread_id": session_id or str(uuid.uuid4()),
            "checkpoint_id": None,  # 可以指定特定检查点
            "metadata": {
                "user_id": user_id,
                "session_name": f"session_{session_id or 'new'}",
            }
        }
    }

# 示例使用
user_config = get_session_config(user_id="user_123", session_id="session_001")

# 对话 1
response1 = agent.invoke(
    {"messages": [("user", "记住我喜欢蓝色")]},
    config=user_config
)

# 对话 2 (同一会话)
response2 = agent.invoke(
    {"messages": [("user", "我刚才说我喜欢什么颜色?")]},
    config=user_config
)

# 对话 3 (新会话)
new_session_config = get_session_config(user_id="user_123", session_id="session_002")
response3 = agent.invoke(
    {"messages": [("user", "我刚才说我喜欢什么颜色?")]},
    config=new_session_config  # 新会话不会记住之前的对话
)
```

---

## 总结

DeepAgents 框架提供了完整的能力来构建智能 AI 助手：

1. **LLM 接入**: 支持多种提供商，通过字符串标识符或直接传入模型实例
2. **Agent 创建**: 支持自定义工具、子代理、系统提示词和中间件
3. **记忆系统**: 三层记忆机制 (Memory/Checkpointer/Store) 满足不同持久化需求

建议按照以下顺序配置：
1. 选择并配置 LLM
2. 定义自定义工具 (可选)
3. 配置 Checkpointer 实现会话持久化
4. 配置 Store 实现数据持久化
5. 配置 Memory 加载上下文信息
6. 选择合适的后端 (StateBackend/StoreBackend/FilesystemBackend)
