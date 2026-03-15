# 从短期记忆到长期记忆的实现流程

## 概述

本文档详细说明如何利用deepagents框架中的checkpointer组件和store组件，实现从短期记忆到长期记忆的完整数据流转流程。该流程涵盖：短期记忆数据的获取、关键信息提取与总结、长期记忆的持久化存储，以及记忆的检索与复用。

---

## 一、短期记忆数据的获取方式及格式

### 1.1 checkpointer组件简介

在deepagents框架中，checkpointer是LangGraph提供的会话级持久化组件，用于存储当前对话线程的状态数据。每个会话（通过thread_id标识）对应一个独立的检查点存储空间。

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# 开发环境：内存检查点
checkpointer = MemorySaver()

# 生产环境：SQLite持久化
checkpointer = SqliteSaver.from_conn_string("./checkpoints.db")
```

### 1.2 获取短期记忆数据

通过agent.checkpointer.get()方法获取当前会话的完整状态：

```python
def get_short_term_memory(agent, thread_id: str) -> dict:
    """从checkpointer获取短期记忆
    
    Args:
        agent: create_deep_agent创建的智能体实例
        thread_id: 会话唯一标识符
    
    Returns:
        包含messages、todos、files等状态的字典
    """
    
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = agent.checkpointer.get(config)
    
    if checkpoint is None:
        return {
            "messages": [],
            "todos": [],
            "files": {},
            "memory_contents": {}
        }
    
    return {
        "messages": checkpoint["channel_values"].get("messages", []),
        "todos": checkpoint["channel_values"].get("todos", []),
        "files": checkpoint["channel_values"].get("files", {}),
        "memory_contents": checkpoint["channel_values"].get("memory_contents", {}),
        "timestamp": checkpoint.get("configurable", {}).get("checkpoint_id")
    }
```

### 1.3 数据格式详解

checkpointer存储的数据具有以下结构：

```python
# 检查点完整结构
checkpoint = {
    "channel_values": {
        # 对话消息列表
        "messages": [
            HumanMessage(content="帮我实现排序算法"),
            AIMessage(content="我来帮你实现快速排序"),
            ToolMessage(content="文件已创建", tool_call_id="xxx")
        ],
        
        # 任务列表
        "todos": [
            {"id": "1", "content": "实现排序算法", "status": "completed"},
            {"id": "2", "content": "添加单元测试", "status": "in_progress"}
        ],
        
        # 文件状态（文件系统后端使用）
        "files": {
            "/workspace/sort.py": {
                "content": ["def quick_sort(arr):", "    ..."],
                "created_at": "2024-01-01T00:00:00Z",
                "modified_at": "2024-01-01T00:00:00Z"
            }
        },
        
        # 记忆内容（memory参数加载）
        "memory_contents": {
            "/memory/AGENTS.md": "# 项目规范\n- 遵循PEP 8"
        },
        
        # 结构化响应
        "structured_response": None
    },
    
    "configurable": {
        "thread_id": "session-001",
        "checkpoint_id": "1ef2a3b4"
    }
}
```

### 1.4 消息格式

对话中的每条消息都有特定的格式：

```python
# HumanMessage（用户消息）
{
    "type": "human",
    "data": {
        "content": "帮我写一个排序算法",
        "additional_kwargs": {},
        "response_metadata": {}
    }
}

# AIMessage（AI回复）
{
    "type": "ai",
    "data": {
        "content": "我来为你实现快速排序算法",
        "tool_calls": [
            {
                "id": "call_abc123",
                "name": "write_file",
                "args": {
                    "file_path": "/workspace/sort.py",
                    "content": "def quick_sort(arr):..."
                }
            }
        ]
    }
}

# ToolMessage（工具返回）
{
    "type": "tool",
    "data": {
        "content": "文件已成功创建",
        "tool_call_id": "call_abc123"
    }
}
```

---

## 二、关键信息提取与总结的算法和方法

### 2.1 deepagents内置的SummarizationMiddleware

deepagents框架已经内置了强大的对话摘要功能——`SummarizationMiddleware`，它可以自动检测对话长度并在必要时触发摘要操作。

```python
from deepagents.middleware.summarization import SummarizationMiddleware

# 配置摘要中间件
middleware = SummarizationMiddleware(
    model="gpt-4o-mini",              # 用于摘要的模型（推荐使用便宜的模型）
    backend=backend,                   # 后端（存储原始对话）
    trigger=("tokens", 100000),        # 触发阈值：100k tokens
    keep=("messages", 10),            # 保留最近10条消息
    summary_prompt=DEFAULT_SUMMARY_PROMPT  # 摘要提示词
)
```

### 2.2 摘要算法流程

```
┌─────────────────────────────────────────────────────────────┐
│                    摘要算法流程                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 触发检测                                                 │
│     ├─ 基于token数量: trigger=("tokens", 100000)           │
│     ├─ 基于消息数量: trigger=("messages", 50)               │
│     └─ 基于使用量元数据: usage_metadata                     │
│                                                              │
│  2. 消息分割                                                 │
│     ├─ 待摘要消息: 早于 cutoff_index 的消息                 │
│     └─ 保留消息: 最近的 keep 条消息                          │
│                                                              │
│  3. LLM摘要生成                                             │
│     ├─ 输入: 待摘要的完整对话历史                            │
│     ├─ 提示词: "请用简洁的语言总结以下对话..."               │
│     └─ 输出: 结构化摘要内容                                  │
│                                                              │
│  4. 存储与替换                                              │
│     ├─ 原始消息 → 后端存储 (Markdown格式)                   │
│     └─ 对话历史 → 摘要消息 + 引用路径                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 自定义摘要提示词

可以通过自定义提示词来控制摘要的内容和格式：

```python
CUSTOM_SUMMARY_PROMPT = """请分析以下对话历史，提取并总结：

1. 用户的主要需求和目标
2. 已完成的关键任务
3. 未解决的问题或待办事项
4. 重要的技术决策或结论
5. 任何需要后续跟进的信息

请用简洁的要点格式返回总结。"""

middleware = SummarizationMiddleware(
    model="gpt-4o-mini",
    backend=backend,
    summary_prompt=CUSTOM_SUMMARY_PROMPT
)
```

### 2.4 自定义关键信息提取

除了使用框架内置的摘要功能，还可以实现自定义的信息提取：

```python
def extract_key_information(messages: list, todos: list = None) -> dict:
    """从消息中提取关键信息
    
    Args:
        messages: 对话消息列表
        todos: 任务列表
    
    Returns:
        包含summary、key_points、entities等结构化信息
    """
    
    if not messages:
        return {
            "summary": "",
            "key_points": [],
            "entities": [],
            "tasks": [],
            "topics": []
        }
    
    # 初始化提取结果
    key_points = []
    entities = set()
    topics = set()
    tasks = todos.copy() if todos else []
    
    # 遍历消息提取信息
    for msg in messages:
        content = msg.content if hasattr(msg, 'content') else str(msg)
        
        # 提取关键主题
        tech_keywords = ['Python', 'JavaScript', 'API', '数据库', '算法']
        for keyword in tech_keywords:
            if keyword.lower() in content.lower():
                topics.add(keyword)
        
        # 提取文件路径
        if '/' in content and ('.' in content.split('/')[-1]):
            for part in content.split():
                if part.startswith('/') or part.startswith('./'):
                    entities.add(part)
    
    # 构建摘要
    first_msg = messages[0].content if messages else ""
    last_msg = messages[-1].content if messages else ""
    
    return {
        "summary": f"会话包含关于{', '.join(topics) if topics else '通用话题'}的讨论",
        "key_points": key_points,
        "entities": list(entities),
        "tasks": tasks,
        "topics": list(topics),
        "message_count": len(messages),
        "first_message_preview": first_msg[:100],
        "last_message_preview": last_msg[:100]
    }
```

---

## 三、利用checkpointer组件实现长期记忆的持久化存储

### 3.1 检查点存储类型选择

根据不同场景选择合适的检查点存储后端：

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres import PostgresSaver

# 开发测试：内存检查点（数据不持久化）
checkpointer = MemorySaver()

# 小规模部署：SQLite（单文件持久化）
checkpointer = SqliteSaver.from_conn_string("./checkpoints.db")

# 大规模部署：PostgreSQL（数据库持久化）
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/checkpoints"
)
```

### 3.2 会话数据的提取与持久化

将checkpointer中的会话数据提取并存储到长期记忆：

```python
def extract_session_for_storage(agent, thread_id: str) -> dict:
    """提取会话数据用于长期存储
    
    Args:
        agent: 智能体实例
        thread_id: 会话ID
    
    Returns:
        可序列化的会话数据字典
    """
    
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = agent.checkpointer.get(config)
    
    if checkpoint is None:
        return {}
    
    channel_values = checkpoint["channel_values"]
    
    # 序列化消息（提取关键字段）
    serialized_messages = []
    for msg in channel_values.get("messages", []):
        msg_dict = {
            "type": type(msg).__name__,
            "content": msg.content if hasattr(msg, 'content') else str(msg)
        }
        
        # 添加tool_calls信息
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "name": tc.get("name"),
                    "args": tc.get("args", {})
                }
                for tc in msg.tool_calls
            ]
        
        serialized_messages.append(msg_dict)
    
    return {
        "thread_id": thread_id,
        "messages": serialized_messages,
        "todos": channel_values.get("todos", []),
        "files": channel_values.get("files", {}),
        "checkpoint_id": checkpoint.get("configurable", {}).get("checkpoint_id"),
        "extracted_at": datetime.now().isoformat()
    }
```

---

## 四、store组件在记忆管理过程中的具体应用

### 4.1 Store的基本操作

LangGraph的BaseStore提供了跨会话、跨线程的持久化存储能力：

```python
from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres import PostgresStore

# 创建store实例（开发测试）
store = InMemoryStore(
    index=("json", ["namespace", "key", "user_id"])
)

# 创建store实例（生产环境）
store = PostgresStore(
    conn_string="postgresql://user:pass@localhost/db",
    index=("json", ["namespace", "key"])
)

# 存储数据：store.put(namespace, key, value)
store.put(
    ("session_summaries", "user-123"),  # namespace: tuple
    "session-001",                        # key: str
    {
        "summary": "用户需要实现排序算法",
        "tasks": ["完成快速排序", "添加单元测试"],
        "topics": ["算法", "Python"]
    }
)

# 检索单个数据
item = store.get(("session_summaries", "user-123"), "session-001")
print(item.value)  # 获取存储的值

# 搜索数据
results = store.search(
    ("session_summaries", "user-123"),  # namespace
    query="排序算法",                    # 自然语言搜索
    limit=5                             # 返回数量限制
)
```

### 4.2 Store命名空间设计

良好的命名空间设计有助于数据的组织和管理：

```python
# 定义命名空间常量
NAMESPACE_SUMMARIES = "session_summaries"     # 会话摘要
NAMESPACE_DETAILS = "session_details"         # 会话详情
NAMESPACE_PREFERENCES = "user_preferences"    # 用户偏好
NAMESPACE_KNOWLEDGE = "knowledge_base"        # 知识库
NAMESPACE_CACHE = "cache"                      # 缓存数据

def save_to_long_term_memory(
    store,
    user_id: str,
    thread_id: str,
    session_data: dict,
    key_info: dict
) -> None:
    """将短期记忆保存到长期记忆
    
    Args:
        store: BaseStore实例
        user_id: 用户ID
        thread_id: 会话ID
        session_data: 从checkpointer提取的会话数据
        key_info: 提取的关键信息
    """
    
    # 1. 存储会话摘要（用于快速检索）
    store.put(
        (NAMESPACE_SUMMARIES, user_id),
        thread_id,
        {
            "thread_id": thread_id,
            "summary": key_info.get("summary", ""),
            "key_points": key_info.get("key_points", []),
            "topics": key_info.get("topics", []),
            "message_count": key_info.get("message_count", 0),
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 1
        }
    )
    
    # 2. 存储会话详情（保留完整信息）
    store.put(
        (NAMESPACE_DETAILS, user_id),
        thread_id,
        {
            "messages": session_data.get("messages", []),
            "todos": session_data.get("todos", []),
            "files": session_data.get("files", {}),
            "extracted_at": datetime.now().isoformat()
        }
    )
```

### 4.3 长期记忆的检索

```python
def retrieve_long_term_memory(
    store,
    user_id: str,
    query: str = None,
    limit: int = 5
) -> list:
    """检索长期记忆
    
    Args:
        store: BaseStore实例
        user_id: 用户ID
        query: 可选的搜索查询
        limit: 返回结果数量限制
    
    Returns:
        匹配的会话摘要列表
    """
    
    results = store.search(
        (NAMESPACE_SUMMARIES, user_id),
        query=query,
        limit=limit
    )
    
    return [
        {
            "thread_id": item.key,
            "summary": item.value.get("summary"),
            "key_points": item.value.get("key_points", []),
            "topics": item.value.get("topics", []),
            "message_count": item.value.get("message_count", 0),
            "created_at": item.value.get("created_at"),
            "last_accessed": item.value.get("last_accessed")
        }
        for item in results
    ]


def update_memory_access(store, user_id: str, thread_id: str) -> None:
    """更新记忆的访问信息"""
    
    item = store.get((NAMESPACE_SUMMARIES, user_id), thread_id)
    if item:
        item.value["last_accessed"] = datetime.now().isoformat()
        item.value["access_count"] = item.value.get("access_count", 0) + 1
        store.put((NAMESPACE_SUMMARIES, user_id), thread_id, item.value)
```

---

## 五、完整的代码实现示例

### 5.1 完整实现流程

```python
"""
从短期记忆到长期记忆的完整实现流程
"""

from typing import TypedDict, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from deepagents import create_deep_agent
from deepagents.backends import StateBackend, FilesystemBackend
from deepagents.middleware.summarization import SummarizationMiddleware


# ============================================================
# 配置组件
# ============================================================

@dataclass
class MemoryConfig:
    """记忆管理配置"""
    checkpointer: Any = field(default_factory=MemorySaver)
    store: Any = field(default_factory=InMemoryStore)
    summary_model: str = "gpt-4o-mini"
    trigger_tokens: int = 80000
    keep_messages: int = 10


class MemoryManager:
    """记忆管理器：负责短期记忆到长期记忆的流转"""
    
    # 命名空间常量
    NAMESPACE_SUMMARIES = "session_summaries"
    NAMESPACE_DETAILS = "session_details"
    NAMESPACE_PREFERENCES = "user_preferences"
    
    def __init__(self, config: MemoryConfig):
        self.checkpointer = config.checkpointer
        self.store = config.store
        self.summary_model = config.summary_model
        self.trigger_tokens = config.trigger_tokens
        self.keep_messages = config.keep_messages
    
    # -------------------- 短期记忆获取 --------------------
    
    def get_short_term_memory(self, thread_id: str) -> dict:
        """从checkpointer获取短期记忆
        
        Args:
            thread_id: 会话ID
        
        Returns:
            包含messages、todos、files的字典
        """
        
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = self.checkpointer.get(config)
        
        if checkpoint is None:
            return {
                "messages": [],
                "todos": [],
                "files": {},
                "timestamp": None
            }
        
        return {
            "messages": checkpoint["channel_values"].get("messages", []),
            "todos": checkpoint["channel_values"].get("todos", []),
            "files": checkpoint["channel_values"].get("files", {}),
            "timestamp": checkpoint.get("configurable", {}).get("checkpoint_id")
        }
    
    # -------------------- 关键信息提取 --------------------
    
    def extract_key_information(
        self,
        messages: list,
        todos: list = None
    ) -> dict:
        """从消息中提取关键信息
        
        Args:
            messages: 消息列表
            todos: 任务列表
        
        Returns:
            结构化的关键信息
        """
        
        if not messages:
            return {
                "summary": "",
                "key_points": [],
                "topics": [],
                "entities": [],
                "tasks": [],
                "message_count": 0
            }
        
        # 提取主题
        topics = set()
        tech_keywords = [
            'python', 'javascript', 'java', 'api', 'database',
            'algorithm', 'web', 'frontend', 'backend', 'docker'
        ]
        
        for msg in messages:
            content = (msg.content if hasattr(msg, 'content') 
                      else str(msg)).lower()
            for keyword in tech_keywords:
                if keyword in content:
                    topics.add(keyword)
        
        # 提取任务
        tasks = []
        if todos:
            tasks = [
                {"content": t.get("content"), "status": t.get("status")}
                for t in todos
            ]
        
        return {
            "summary": f"会话包含关于{', '.join(topics) if topics else '通用话题'}的讨论",
            "key_points": [],
            "topics": list(topics),
            "entities": [],
            "tasks": tasks,
            "message_count": len(messages)
        }
    
    # -------------------- 长期记忆存储 --------------------
    
    def save_to_long_term_memory(
        self,
        user_id: str,
        thread_id: str,
        short_term_data: dict,
        key_info: dict
    ) -> None:
        """将短期记忆保存到长期记忆
        
        Args:
            user_id: 用户ID
            thread_id: 会话ID
            short_term_data: 从checkpointer获取的短期记忆
            key_info: 提取的关键信息
        """
        
        now = datetime.now().isoformat()
        
        # 存储摘要
        self.store.put(
            (self.NAMESPACE_SUMMARIES, user_id),
            thread_id,
            {
                "thread_id": thread_id,
                "summary": key_info.get("summary", ""),
                "key_points": key_info.get("key_points", []),
                "topics": key_info.get("topics", []),
                "message_count": key_info.get("message_count", 0),
                "created_at": now,
                "last_accessed": now,
                "access_count": 1
            }
        )
        
        # 存储详情
        self.store.put(
            (self.NAMESPACE_DETAILS, user_id),
            thread_id,
            {
                "messages": [
                    {
                        "type": type(m).__name__,
                        "content": m.content if hasattr(m, 'content') else str(m)
                    }
                    for m in short_term_data.get("messages", [])
                ],
                "todos": short_term_data.get("todos", []),
                "extracted_at": now
            }
        )
    
    # -------------------- 长期记忆检索 --------------------
    
    def retrieve_long_term_memory(
        self,
        user_id: str,
        query: str = None,
        limit: int = 5
    ) -> list:
        """检索长期记忆
        
        Args:
            user_id: 用户ID
            query: 搜索查询
            limit: 返回数量
        
        Returns:
            匹配的会话摘要列表
        """
        
        results = self.store.search(
            (self.NAMESPACE_SUMMARIES, user_id),
            query=query,
            limit=limit
        )
        
        return [
            {
                "thread_id": item.key,
                "summary": item.value.get("summary"),
                "topics": item.value.get("topics", []),
                "message_count": item.value.get("message_count", 0),
                "last_accessed": item.value.get("last_accessed")
            }
            for item in results
        ]


# ============================================================
# 创建智能体
# ============================================================

def create_agent_with_memory(config: MemoryConfig):
    """创建带有记忆功能的智能体
    
    Args:
        config: 记忆配置
    
    Returns:
        智能体实例和记忆管理器
    """
    
    # 创建后端
    backend = StateBackend()
    
    # 创建摘要中间件
    summarization = SummarizationMiddleware(
        model=config.summary_model,
        backend=backend,
        trigger=("tokens", config.trigger_tokens),
        keep=("messages", config.keep_messages)
    )
    
    # 创建智能体
    agent = create_deep_agent(
        model="claude-sonnet-4-6",
        checkpointer=config.checkpointer,
        store=config.store,
        backend=backend,
        middleware=[summarization]
    )
    
    # 创建记忆管理器
    memory_manager = MemoryManager(config)
    
    return agent, memory_manager


# ============================================================
# 使用示例
# ============================================================

def main():
    """完整使用示例"""
    
    # 1. 配置
    config = MemoryConfig(
        checkpointer=MemorySaver(),
        store=InMemoryStore(),
        summary_model="gpt-4o-mini",
        trigger_tokens=80000,
        keep_messages=10
    )
    
    # 2. 创建智能体
    agent, memory_manager = create_agent_with_memory(config)
    
    # 3. 会话交互
    user_id = "user-123"
    thread_id = "session-001"
    config_dict = {"configurable": {"thread_id": thread_id}}
    
    result = agent.invoke(
        {"messages": [HumanMessage(content="帮我实现一个快速排序算法")]},
        config=config_dict
    )
    
    # 4. 获取短期记忆
    short_term = memory_manager.get_short_term_memory(thread_id)
    print(f"短期记忆消息数: {len(short_term['messages'])}")
    
    # 5. 提取关键信息
    key_info = memory_manager.extract_key_information(
        short_term["messages"],
        short_term["todos"]
    )
    print(f"提取的主题: {key_info['topics']}")
    
    # 6. 保存到长期记忆
    memory_manager.save_to_long_term_memory(
        user_id=user_id,
        thread_id=thread_id,
        short_term_data=short_term,
        key_info=key_info
    )
    print("已保存到长期记忆")
    
    # 7. 检索长期记忆
    memories = memory_manager.retrieve_long_term_memory(
        user_id=user_id,
        query="排序算法"
    )
    print(f"找到 {len(memories)} 条相关记忆")


if __name__ == "__main__":
    main()
```

### 5.2 与智能体集成的完整示例

```python
"""
将记忆管理集成到智能体使用流程中
"""

from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage


class AgentWithMemory:
    """带有记忆管理功能的智能体"""
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        checkpointer=None,
        store=None,
        backend=None
    ):
        self.checkpointer = checkpointer or MemorySaver()
        self.store = store or InMemoryStore()
        self.backend = backend or StateBackend()
        
        self.agent = create_deep_agent(
            model=model,
            checkpointer=self.checkpointer,
            store=self.store,
            backend=self.backend
        )
        
        self.memory_manager = None
    
    def invoke(self, message: str, thread_id: str, user_id: str):
        """调用智能体并自动管理记忆
        
        Args:
            message: 用户消息
            thread_id: 会话ID
            user_id: 用户ID
        
        Returns:
            智能体响应
        """
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 调用智能体
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )
        
        return result
    
    def extract_and_save_memory(self, thread_id: str, user_id: str):
        """提取并保存会话记忆
        
        Args:
            thread_id: 会话ID
            user_id: 用户ID
        """
        
        # 获取短期记忆
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = self.checkpointer.get(config)
        
        if checkpoint is None:
            return
        
        short_term = {
            "messages": checkpoint["channel_values"].get("messages", []),
            "todos": checkpoint["channel_values"].get("todos", []),
            "files": checkpoint["channel_values"].get("files", {})
        }
        
        # 提取关键信息
        key_info = self._extract_key_info(short_term["messages"])
        
        # 保存到长期记忆
        self._save_memory(user_id, thread_id, short_term, key_info)
    
    def _extract_key_info(self, messages: list) -> dict:
        """提取关键信息"""
        
        topics = set()
        for msg in messages:
            content = (msg.content if hasattr(msg, 'content') 
                      else str(msg)).lower()
            if '排序' in content or '算法' in content:
                topics.add('算法')
            if 'python' in content:
                topics.add('Python')
            if 'web' in content or 'http' in content:
                topics.add('Web')
        
        return {
            "summary": f"讨论主题: {', '.join(topics) if topics else '通用'}",
            "topics": list(topics),
            "message_count": len(messages)
        }
    
    def _save_memory(self, user_id, thread_id, short_term, key_info):
        """保存记忆"""
        
        now = __import__('datetime').datetime.now().isoformat()
        
        self.store.put(
            ("session_summaries", user_id),
            thread_id,
            {
                "summary": key_info.get("summary", ""),
                "topics": key_info.get("topics", []),
                "message_count": key_info.get("message_count", 0),
                "saved_at": now
            }
        )
    
    def get_memory_history(self, user_id: str, query: str = None) -> list:
        """获取记忆历史
        
        Args:
            user_id: 用户ID
            query: 搜索查询
        
        Returns:
            记忆列表
        """
        
        results = self.store.search(
            ("session_summaries", user_id),
            query=query,
            limit=10
        )
        
        return [
            {
                "thread_id": item.key,
                "summary": item.value.get("summary"),
                "topics": item.value.get("topics", [])
            }
            for item in results
        ]


# 使用示例
agent_with_memory = AgentWithMemory()

# 对话
agent_with_memory.invoke(
    message="帮我写一个排序算法",
    thread_id="session-001",
    user_id="user-123"
)

# 提取并保存记忆
agent_with_memory.extract_and_save_memory(
    thread_id="session-001",
    user_id="user-123"
)

# 检索记忆
history = agent_with_memory.get_memory_history(
    user_id="user-123",
    query="算法"
)
```

---

## 六、测试验证方法及预期结果

### 6.1 单元测试

```python
import pytest
from unittest.mock import Mock, patch
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver


# 测试短期记忆提取
def test_get_short_term_memory():
    """测试从checkpointer获取短期记忆"""
    
    # 模拟checkpointer
    mock_checkpointer = Mock()
    mock_checkpointer.get.return_value = {
        "channel_values": {
            "messages": [
                Mock(content="测试消息1"),
                Mock(content="测试回复1")
            ],
            "todos": [{"content": "任务1", "status": "completed"}],
            "files": {"/test.py": {"content": ["print('hello')"]}}
        },
        "configurable": {
            "thread_id": "test-thread",
            "checkpoint_id": "abc123"
        }
    }
    
    # 创建MemoryManager实例并测试
    manager = MemoryManager(Mock(checkpointer=mock_checkpointer, store=InMemoryStore()))
    result = manager.get_short_term_memory("test-thread")
    
    # 验证结果
    assert len(result["messages"]) == 2
    assert result["todos"][0]["content"] == "任务1"
    assert "/test.py" in result["files"]


# 测试关键信息提取
def test_extract_key_information():
    """测试从消息中提取关键信息"""
    
    from langchain_core.messages import HumanMessage, AIMessage
    
    messages = [
        HumanMessage(content="帮我实现一个Python排序算法"),
        AIMessage(content="我来帮你实现快速排序"),
    ]
    
    manager = MemoryManager(Mock())
    result = manager.extract_key_information(messages)
    
    assert result["message_count"] == 2
    assert "python" in result["topics"]
    assert "算法" in result["summary"] or "排序" in result["summary"]


# 测试长期记忆存储
def test_save_to_long_term_memory():
    """测试存储到长期记忆"""
    
    store = InMemoryStore()
    mock_config = Mock(checkpointer=Mock(), store=store)
    
    manager = MemoryManager(mock_config)
    
    short_term = {
        "messages": [Mock(content="测试消息")],
        "todos": [{"content": "任务1"}],
        "files": {}
    }
    
    key_info = {
        "summary": "测试会话",
        "key_points": ["要点1", "要点2"],
        "topics": ["Python"],
        "message_count": 1
    }
    
    manager.save_to_long_term_memory(
        user_id="test-user",
        thread_id="test-session",
        short_term_data=short_term,
        key_info=key_info
    )
    
    # 验证存储成功
    item = store.get(("session_summaries", "test-user"), "test-session")
    assert item is not None
    assert item.value["summary"] == "测试会话"
    assert "Python" in item.value["topics"]


# 测试长期记忆检索
def test_retrieve_long_term_memory():
    """测试检索长期记忆"""
    
    store = InMemoryStore()
    
    # 预先存储一些数据
    store.put(
        ("session_summaries", "test-user"),
        "session-1",
        {"summary": "关于Python排序算法的讨论", "topics": ["Python"], "message_count": 5}
    )
    store.put(
        ("session_summaries", "test-user"),
        "session-2",
        {"summary": "关于JavaScript前端的讨论", "topics": ["JavaScript"], "message_count": 3}
    )
    
    mock_config = Mock(checkpointer=Mock(), store=store)
    manager = MemoryManager(mock_config)
    
    # 检索
    results = manager.retrieve_long_term_memory("test-user", query="Python")
    
    assert len(results) > 0
    assert "Python" in results[0]["topics"]
```

### 6.2 集成测试

```python
import pytest
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.messages import HumanMessage


@pytest.fixture
def agent_with_memory():
    """创建带有记忆功能的智能体"""
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    agent = create_deep_agent(
        model="claude-sonnet-4-6",
        checkpointer=checkpointer,
        store=store
    )
    
    return agent, checkpointer, store


def test_session_to_longterm_flow(agent_with_memory):
    """测试：短期记忆 → 长期记忆 完整流程"""
    
    agent, checkpointer, store = agent_with_memory
    thread_id = "test-thread"
    user_id = "test-user"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. 对话交互
    agent.invoke(
        {"messages": [HumanMessage(content="实现一个求和函数")]},
        config=config
    )
    
    # 2. 验证checkpointer存储
    checkpoint = checkpointer.get(config)
    assert checkpoint is not None
    assert "messages" in checkpoint["channel_values"]
    
    # 3. 创建记忆管理器并保存
    manager = MemoryManager(
        Mock(checkpointer=checkpointer, store=store)
    )
    
    short_term = manager.get_short_term_memory(thread_id)
    key_info = manager.extract_key_information(
        short_term["messages"],
        short_term["todos"]
    )
    
    manager.save_to_long_term_memory(
        user_id=user_id,
        thread_id=thread_id,
        short_term_data=short_term,
        key_info=key_info
    )
    
    # 4. 验证长期记忆存储
    item = store.get(("session_summaries", user_id), thread_id)
    assert item is not None
    assert "求和" in item.value["summary"] or "函数" in item.value["summary"]
    
    # 5. 验证可检索
    results = store.search(("session_summaries", user_id), query="求和")
    assert len(results) > 0


def test_memory_retrieval_and_context(agent_with_memory):
    """测试：检索记忆并用于新会话"""
    
    agent, checkpointer, store = agent_with_memory
    user_id = "test-user"
    
    # 1. 预先存储记忆
    store.put(
        ("session_summaries", user_id),
        "old-session",
        {
            "summary": "之前讨论了Python快速排序算法的实现",
            "topics": ["Python", "算法"],
            "message_count": 10
        }
    )
    
    # 2. 检索相关记忆
    manager = MemoryManager(Mock(checkpointer=checkpointer, store=store))
    memories = manager.retrieve_long_term_memory(user_id, query="Python算法")
    
    assert len(memories) > 0
    assert any("Python" in m.get("topics", []) for m in memories)
```

### 6.3 预期结果

| 测试场景 | 预期结果 | 验证方法 |
|----------|----------|----------|
| 短期记忆提取 | 成功获取messages、todos、files等状态 | 断言消息数量和内容 |
| 关键信息提取 | 正确识别主题、任务等结构化信息 | 断言提取的主题列表 |
| 长期记忆存储 | 数据正确存储到指定namespace | store.get()验证 |
| 记忆检索 | 可通过key或自然语言查询检索 | query搜索验证 |
| 完整流程 | 从短期→长期的完整数据流转正常 | 集成测试端到端验证 |

---

## 总结

整个从短期记忆到长期记忆的实现流程可以概括为以下步骤：

```
┌─────────────────────────────────────────────────────────────────┐
│                        完整流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 用户对话                                                      │
│     └─→ agent.invoke() ──→ checkpointer存储                    │
│                           (短期记忆)                             │
│                              │                                   │
│                              ▼                                   │
│  2. 获取短期记忆                                                  │
│     └─→ checkpointer.get(thread_id)                             │
│         └─→ {messages, todos, files, ...}                       │
│                              │                                   │
│                              ▼                                   │
│  3. 关键信息提取                                                  │
│     └─→ extract_key_information()                               │
│         └─→ {summary, key_points, topics, ...}                 │
│                              │                                   │
│                              ▼                                   │
│  4. 长期记忆存储                                                  │
│     └─→ store.put(namespace, key, value)                       │
│         └─→ session_summaries / session_details               │
│                              │                                   │
│                              ▼                                   │
│  5. 长期记忆检索                                                 │
│     └─→ store.search(namespace, query)                          │
│         └─→ [{thread_id, summary, topics}, ...]               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

该方案充分利用了deepagents框架内置的`SummarizationMiddleware`进行对话压缩，并通过`store`实现结构化知识的持久化存储，形成了一套完整的记忆管理解决方案。

---

## 相关文档

- [create_deep_agent 参数详解](./deepagents-parameters-analysis.md)
- [create_deep_agent 函数规范文档](./create-deep-agent-spec.md)
- [Deep Agents API 使用指南](./deepagents-api-usage.md)
