# LangGraph 记忆功能技术指南

本文档详细介绍 LangGraph 框架中记忆功能的核心实现机制，包括 Checkpointer（短期记忆）、Store（长期记忆）和 Runtime（运行时访问）等核心组件的工作原理、交互方式及数据流转逻辑。本指南旨在为项目集成长短期记忆功能提供标准化的技术指导和开发依据。

## 目录

1. [记忆功能概述](#1-记忆功能概述)
2. [核心组件详解](#2-核心组件详解)
3. [初始化流程](#3-初始化流程)
4. [核心方法调用顺序](#4-核心方法调用顺序)
5. [常见使用场景](#5-常见使用场景)
6. [注意事项](#6-注意事项)
7. [组件参数格式规范](#7-组件参数格式规范)
8. [完整示例](#8-完整示例)

---

## 1. 记忆功能概述

LangGraph 中的记忆功能分为两大类别：

| 记忆类型 | 组件 | 用途 | 持久化方式 |
|---------|------|------|-----------|
| 短期记忆 | Checkpointer | 维护当前对话状态，支持多轮对话 | 内存/SQLite/PostgreSQL/Redis |
| 长期记忆 | Store | 跨会话存储用户偏好、档案等 | 内存/Redis/PostgreSQL |

### 1.1 短期记忆（Checkpointer）

短期记忆用于保存对话历史，使 Agent 能够记住当前会话中的上下文信息。每次图执行后，Checkpointer 会自动保存完整的状态快照，支持通过 `thread_id` 恢复对话。

### 1.2 长期记忆（Store）

长期记忆用于存储需要跨会话持久化的数据，例如用户档案、偏好设置、业务数据等。Store 使用命名空间（Namespace）来组织数据，支持语义搜索（需要配置嵌入模型）。

---

## 2. 核心组件详解

### 2.1 Checkpointer

Checkpointer 是 LangGraph 的状态持久化组件，负责保存和恢复图执行状态。

#### 可用实现

| 类名 | 数据源 | 适用场景 |
|------|--------|----------|
| `InMemorySaver` | 内存 | 开发/测试环境 |
| `MemorySaver` | 内存 | 同上（同步版本） |
| `AsyncSqliteSaver` | SQLite | 生产环境（异步） |
| `SqliteSaver` | SQLite | 生产环境（同步） |
| `AsyncPostgresSaver` | PostgreSQL | 生产环境（异步） |
| `PostgresSaver` | PostgreSQL | 生产环境（同步） |
| `RedisSaver` | Redis | 高并发场景 |

#### 工作原理

1. 每次图执行（invoke/stream）完成后，Checkpointer 自动保存状态快照
2. 状态快照包含：`values`（状态值）、`next`（下一节点）、`config`（配置）、`metadata`（元信息）
3. 通过 `thread_id` 区分不同会话
4. 可通过 `checkpoint_id` 回溯到任意历史状态

### 2.2 Store

Store 是长期记忆存储组件，提供键值对存储和语义搜索能力。

#### 可用实现

| 类名 | 数据源 | 特点 |
|------|--------|------|
| `InMemoryStore` | 内存 | 简单易用，重启后丢失 |
| `RedisStore` | Redis | 持久化，支持分布式 |
| `PostgresStore` | PostgreSQL | 持久化，支持向量搜索 |

#### 核心概念

- **Namespace（命名空间）**：元组格式 `("user_123", "profile")`，用于组织数据
- **Item（记忆项）**：包含 `key`、`value`、`created_at`、`updated_at` 等属性

### 2.3 Runtime

Runtime 是图执行时的运行时上下文，提供访问 Store 和 Context 的能力。

#### 作用

- 在节点函数中访问当前用户的 Context
- 通过 `runtime.store` 访问长期记忆
- 获取用户标识等上下文信息

---

## 3. 初始化流程

### 3.1 Checkpointer 初始化

```python
# SQLite 异步方式（推荐生产环境）
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

conn = await aiosqlite.connect("data/checkpoint.db")
checkpointer = AsyncSqliteSaver(conn)
await checkpointer.setup()

# SQLite 同步方式
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("data/checkpoint.db")
checkpointer = SqliteSaver(conn)

# 内存方式（开发/测试）
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()
```

### 3.2 Store 初始化

```python
# 内存 Store（无持久化）
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 带语义搜索的内存 Store
from langchain.embeddings import init_embeddings

embeddings = init_embeddings("openai:text-embedding-3-small")
store = InMemoryStore(
    index={
        "embed": embeddings,
        "dims": 1536,
    }
)

# Redis Store
from langgraph.store.redis import RedisStore

store = RedisStore.from_conn_string("redis://localhost:6379")
await store.setup()

# PostgreSQL Store
from langgraph.store.postgres import PostgresStore

store = PostgresStore.from_conn_string("postgresql://user:pass@localhost:5432/db")
await store.setup()
```

### 3.3 Context 定义

```python
from dataclasses import dataclass

@dataclass
class UserContext:
    user_id: str
    user_name: str = "Anonymous"
    metadata: dict = None
```

---

## 4. 核心方法调用顺序

### 4.1 标准初始化顺序

```python
async def initialize_memory_system():
    # 1. 创建 Checkpointer
    conn = await aiosqlite.connect("data/checkpoint.db")
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()
    
    # 2. 创建 Store
    store = InMemoryStore()
    
    # 3. 定义 Context
    @dataclass
    class Context:
        user_id: str
    
    # 4. 构建并编译图
    builder = StateGraph(MessagesState, context_schema=Context)
    builder.add_node(agent_node)
    builder.add_edge(START, "agent")
    
    graph = builder.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    return graph
```

### 4.2 图调用顺序

```python
async def call_graph():
    # 1. 准备配置（必须包含 thread_id）
    config = {
        "configurable": {
            "thread_id": "session_123",
            "metadata": {"source": "cli"}
        }
    }
    
    # 2. 准备上下文
    context = Context(user_id="user_456")
    
    # 3. 调用图
    async for chunk in graph.astream(
        {"messages": [("user", "你好")]},
        config=config,
        context=context
    ):
        process(chunk)
    
    # 4. 获取状态（可选）
    state = graph.get_state(config)
```

---

## 5. 常见使用场景

### 5.1 多轮对话保持上下文

```python
def create_chat_graph(checkpointer, store):
    def chat_node(state: MessagesState, runtime: Runtime[Context]):
        messages = state["messages"]
        
        # 从 Store 获取用户信息
        namespace = (runtime.context.user_id, "profile")
        profiles = runtime.store.search(namespace)
        
        system_msg = build_system_message(profiles)
        
        response = model.invoke([{"role": "system", "content": system_msg}] + messages)
        return {"messages": [response]}
    
    builder = StateGraph(MessagesState, context_schema=Context)
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")
    
    return builder.compile(checkpointer=checkpointer, store=store)

# 调用
config = {"configurable": {"thread_id": "user_session_1"}}
# 第一轮
graph.invoke({"messages": [("user", "我叫Bob")]}, config, context=Context(user_id="u1"))
# 第二轮（自动包含历史）
graph.invoke({"messages": [("user", "我刚才说我叫什么？")]}, config, context=Context(user_id="u1"))
```

### 5.2 长期记忆存储与检索

```python
def create_memory_graph(checkpointer, store):
    def memory_node(state: MessagesState, runtime: Runtime[Context]):
        namespace = (runtime.context.user_id, "memories")
        
        # 存储记忆
        last_msg = state["messages"][-1].content
        if "记住" in last_msg or "remember" in last_msg.lower():
            key = f"mem_{uuid.uuid4().hex[:8]}"
            runtime.store.put(namespace, key, {"text": last_msg})
        
        # 检索记忆
        results = runtime.store.search(namespace, limit=3)
        
        return {"memory_results": results}
    
    builder = StateGraph(MessagesState, context_schema=Context)
    builder.add_node("memory", memory_node)
    builder.add_edge(START, "memory")
    
    return builder.compile(checkpointer=checkpointer, store=store)
```

### 5.3 状态回溯与分叉

```python
# 获取历史状态
history = list(graph.get_state_history(config))
for snapshot in history:
    print(f"Step: {snapshot.metadata.get('step')}")
    print(f"Checkpoint ID: {snapshot.config['configurable']['checkpoint_id']}")

# 回溯到特定检查点
specific_config = {
    "configurable": {
        "thread_id": "session_123",
        "checkpoint_id": "1f029ca3-1f5b-6704-8004-820c16b69a5a"
    }
}
state = graph.get_state(specific_config)

# 分叉执行（从历史状态创建新分支）
fork_config = graph.update_state(
    history[0].config,
    values={"messages": [("user", "新的输入")]},
    as_node="agent"
)
result = graph.invoke(None, fork_config)
```

---

## 6. 注意事项

### 6.1 必填字段

- **Checkpointer**: 无必填参数，但生产环境建议使用持久化实现
- **Store**: 无必填参数
- **Config**: `thread_id` 为必填，用于标识会话
- **Context**: 根据 `context_schema` 定义必填字段

### 6.2 数据库 Setup

使用数据库后端的 Checkpointer 或 Store 时，必须调用 `setup()` 方法初始化表结构：

```python
# 正确
checkpointer = AsyncSqliteSaver(conn)
await checkpointer.setup()

store = RedisStore.from_conn_string(redis_uri)
await store.setup()

# 错误：未调用 setup 可能导致运行时错误
```

### 6.3 资源管理

异步 Checkpointer 使用后需要关闭连接：

```python
async def cleanup():
    await checkpointer.conn.close()
```

### 6.4 线程安全

- 同一 `thread_id` 的并发调用可能导致状态不一致
- 建议使用锁或消息队列保证串行执行

### 6.5 数据序列化

Checkpointer 会自动序列化状态，需确保状态中的对象可序列化：

```python
# 推荐：使用基础类型
{"messages": [("user", "hello")], "count": 1}

# 注意：自定义类可能无法序列化
class CustomType:
    pass

# 如果必须使用，可以配置自定义序列化器
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
serde = EncryptedSerializer.from_pycryptodome_aes()
checkpointer = SqliteSaver(conn, serde=serde)
```

---

## 7. 组件参数格式规范

### 7.1 Checkpointer 参数

#### InMemorySaver

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

无配置参数。

#### SqliteSaver / AsyncSqliteSaver

```python
# 同步版本
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect("checkpoint.db")
checkpointer = SqliteSaver(
    conn,
    serde=None,  # 可选：序列化器，默认使用 JsonSerializer
)

# 异步版本
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

conn = await aiosqlite.connect("checkpoint.db")
checkpointer = AsyncSqliteSaver(
    conn,
    serde=None,
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn | 数据库连接 | 是 | - | SQLite 连接对象 |
| serde | BaseSerializer | 否 | JsonSerializer | 序列化器 |

#### PostgresSaver / AsyncPostgresSaver

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 同步
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@host:port/db?sslmode=disable",
    serde=None,
)

# 异步
checkpointer = AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@host:port/db?sslmode=disable",
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn_string | str | 是 | - | PostgreSQL 连接串 |

#### RedisSaver

```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver.from_conn_string(
    "redis://localhost:6379",
    serde=None,
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn_string | str | 是 | - | Redis 连接串 |

### 7.2 Store 参数

#### InMemoryStore

```python
from langgraph.store.memory import InMemoryStore

# 简单存储
store = InMemoryStore()

# 带语义搜索
from langchain.embeddings import init_embeddings
embeddings = init_embeddings("openai:text-embedding-3-small")

store = InMemoryStore(
    index={
        "embed": embeddings,  # 嵌入模型
        "dims": 1536,       # 嵌入维度
    }
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| index | dict | 否 | None | 语义搜索配置 |

#### RedisStore

```python
from langgraph.store.redis import RedisStore

store = RedisStore.from_conn_string(
    "redis://localhost:6379",
    embedding=None,  # 嵌入模型（可选）
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn_string | str | 是 | - | Redis 连接串 |
| embedding | BaseEmbeddings | 否 | None | 语义搜索用嵌入模型 |

#### PostgresStore

```python
from langgraph.store.postgres import PostgresStore

store = PostgresStore.from_conn_string(
    "postgresql://user:pass@host:port/db",
    embedding=None,
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn_string | str | 是 | - | PostgreSQL 连接串 |
| embedding | BaseEmbeddings | 否 | None | 语义搜索用嵌入模型 |

#### SqliteStore / AsyncSqliteStore

```python
import aiosqlite
from langgraph.store.sqlite import SqliteStore
from langgraph.store.sqlite.aio import AsyncSqliteStore

# 同步
import sqlite3
conn = sqlite3.connect("store.db")
store = SqliteStore(conn)

# 异步
import aiosqlite
conn = await aiosqlite.connect("store.db")
store = AsyncSqliteStore(conn)
await store.setup()
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| conn | 数据库连接 | 是 | - | SQLite 连接对象 |
| index | SqliteIndexConfig | 否 | None | 索引配置（用于向量搜索） |

### 7.3 Runtime 存储操作

#### put - 存储数据

```python
namespace = ("user_123", "profile")
runtime.store.put(
    namespace,           # 命名空间（元组）
    "key_name",         # 键名（字符串）
    {"value": "data"}   # 值（字典）
)
```

#### get - 获取单条

```python
item = runtime.store.get(namespace, "key_name")
# item.value, item.key, item.created_at, item.updated_at
```

#### search - 搜索

```python
# 精确搜索
results = runtime.store.search(namespace)

# 语义搜索（需配置嵌入模型）
results = runtime.store.search(
    namespace,
    query="用户喜欢的食物",
    limit=5
)
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| namespace | tuple | 是 | - | 命名空间 |
| query | str | 否 | None | 语义搜索查询 |
| limit | int | 否 | 10 | 返回结果数量 |

#### delete - 删除

```python
runtime.store.delete(namespace, "key_name")
```

### 7.4 Config 参数

```python
config = {
    "configurable": {
        "thread_id": "session_001",      # 必填：会话标识
        "checkpoint_id": "xxx",           # 可选：指定检查点
        "metadata": {"key": "value"},    # 可选：元数据
    }
}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| thread_id | str | 是 | - | 会话唯一标识 |
| checkpoint_id | str | 否 | 最新 | 回溯用检查点ID |
| metadata | dict | 否 | {} | 自定义元数据 |

---

## 8. 完整示例

```python
import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
from langchain_anthropic import ChatAnthropic

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.runtime import Runtime
from langgraph.store.memory import InMemoryStore


@dataclass
class UserContext:
    user_id: str
    user_name: str


class ChatWithMemory:
    
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self.checkpointer = None
        self.store = None
        self.graph = None
        self.model = ChatAnthropic(model_name="claude-sonnet-4-20250514")
        
    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = await aiosqlite.connect(self.db_path)
        self.checkpointer = AsyncSqliteSaver(conn)
        await self.checkpointer.setup()
        
        self.store = InMemoryStore()
        
    async def build_graph(self):
        
        def chat_node(state: MessagesState, runtime: Runtime[UserContext]):
            user_id = runtime.context.user_id
            
            messages = state.get("messages", [])
            
            namespace = (user_id, "profile")
            profiles = runtime.store.search(namespace, limit=3)
            
            system_msg = "你是一个友好的助手。"
            if profiles:
                system_msg += f"\n用户档案: {profiles}"
            
            response = self.model.invoke(
                [{"role": "system", "content": system_msg}] + messages
            )
            return {"messages": [response]}
        
        builder = StateGraph(MessagesState, context_schema=UserContext)
        builder.add_node("chat", chat_node)
        builder.add_edge(START, "chat")
        
        self.graph = builder.compile(
            checkpointer=self.checkpointer,
            store=self.store
        )
        
    async def chat(self, user_id: str, message: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        context = UserContext(user_id=user_id, user_name="User")
        
        async for chunk in self.graph.astream(
            {"messages": [("user", message)]},
            config=config,
            context=context
        ):
            for node, output in chunk.items():
                if "messages" in output:
                    yield output["messages"][-1].content


async def main():
    chat = ChatWithMemory()
    await chat.initialize()
    await chat.build_graph()
    
    async for response in chat.chat("user_1", "你好，我叫Bob", "session_1"):
        print(f"AI: {response}")
    
    async for response in chat.chat("user_1", "我刚才说我叫什么？", "session_1"):
        print(f"AI: {response}")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 参考资源

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [Context7 LangGraph 文档](https://context7.com)
