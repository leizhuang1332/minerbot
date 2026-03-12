# 短期记忆实现方案 - 对接规范

## 一、DeepAgents 短期记忆能力调研

### 1.1 结论：DeepAgents 完全支持短期记忆

DeepAgents 基于 LangGraph 构建，**原生支持短期记忆（对话历史持久化）**，通过以下组件实现：

| 组件 | 用途 | DeepAgents 集成方式 |
|-----|------|-------------------|
| **LangGraph CheckpointSaver** | 对话历史自动持久化 | 通过 `checkpointer` 参数 |
| **thread_id** | 会话标识 | 通过 `config` 参数传递 |
| **MemorySaver** | 内存存储（开发用） | LangGraph 内置 |
| **SqliteSaver** | SQLite 持久化（生产用） | LangGraph 提供 |

---

## 二、DeepAgents API 对接规范

### 2.1 `create_deep_agent` 参数

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

# 完整 API 签名
agent = create_deep_agent(
    # 基础参数
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable] | None = None,
    system_prompt: str | SystemMessage | None = None,
    
    # 新增：记忆相关参数
    checkpointer: Checkpointer | None = None,  # ← 对话历史持久化
    store: BaseStore | None = None,           # ← 长期记忆存储
    
    # 其他参数
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    backend: BackendProtocol | None = None,
    interrupt_on: dict | None = None,
)
```

### 2.2 Checkpointer 类型

| Checkpointer | 来源 | 用途 |
|-------------|------|------|
| `MemorySaver` | `langgraph.checkpoint.memory` | 开发/测试 |
| `SqliteSaver` | `langgraph.checkpoint.sqlite` | 单机生产 |
| `PostgresSaver` | `langgraph.checkpoint.postgres` | 生产环境 |
| `RedisSaver` | `langgraph.checkpoint.redis` | 高并发/分布式 |

### 2.3 Agent 调用格式

**关键：使用 `config` 参数传递 `thread_id`**

```python
from langgraph.checkpoint.memory import MemorySaver

# 1. 创建 Agent 时启用 checkpointer
checkpointer = MemorySaver()
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    checkpointer=checkpointer,  # ← 启用对话历史持久化
)

# 2. 调用时传递 thread_id
config = {
    "configurable": {
        "thread_id": "user_123_session_001"  # ← 会话标识
    }
}

# 3. 首次调用（创建会话）
result = agent.invoke(
    {"messages": [{"role": "user", "content": "你好"]},
    config=config
)

# 4. 后续调用（同一 thread_id 会自动加载历史）
result = agent.invoke(
    {"messages": [{"role": "user", "content": "继续"]},
    config=config  # ← LangGraph 自动加载之前的对话历史
)
```

### 2.4 输入格式

```python
# 格式1：字符串（会被自动包装为 HumanMessage）
input_data = "你好"

# 格式2：消息列表（显式指定角色）
input_data = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好，有什么可以帮你的？"},
    {"role": "user", "content": "帮我写个函数"}
]

# 格式3：LangChain Message 对象
from langchain_core.messages import HumanMessage, AIMessage

input_data = [
    HumanMessage(content="你好"),
    AIMessage(content="你好，有什么可以帮你的？"),
    HumanMessage(content="帮我写个函数")
]
```

### 2.5 输出格式

```python
# 返回值结构
result = {
    "messages": [
        HumanMessage(content="用户消息"),
        AIMessage(content="AI响应"),
        # ... 所有历史消息都会保留
    ]
}

# 提取响应内容
response_text = result["messages"][-1].content
```

### 2.6 Config 参数详解

```python
config = {
    "configurable": {
        "thread_id": "session_001",      # ← 必填：会话标识
        "checkpoint_id": "optional_id",  # ← 可选：指定检查点版本
        "recursion_limit": 50,           # ← 可选：最大递归深度
    },
    "metadata": {                        # ← 可选：元数据
        "user_id": "user_123",
        "session_type": "chat"
    }
}
```

---

## 三、当前项目源码分析

### 3.1 当前调用方式（无记忆）

**文件：`src/app/service.py` 第 189-195 行**

```python
# ❌ 当前问题：每次都是全新消息，无历史
result = await self._agent.ainvoke(
    {
        "messages": [
            HumanMessage(content=input_data)  # ← 全新消息
        ]
    }
)
```

### 3.2 AgentFactory 当前实现

**文件：`src/agents/agent_factory.py` 第 171-207 行**

```python
# 当前未支持 checkpointer 参数
create_kwargs: Dict[str, Any] = {}

# 只有这些参数：
create_kwargs['model'] = llm
create_kwargs['system_prompt'] = config.system_prompt
create_kwargs['backend'] = config.backend
create_kwargs['middleware'] = config.middleware
create_kwargs['tools'] = config.tools

# ❌ 缺少 checkpointer
# ❌ 缺少 store
```

### 3.3 AgentConfig 当前定义

**文件：`src/agents/config.py`**

```python
@dataclass
class AgentConfig:
    llm: LLMType = None
    system_prompt: str = "你是一个助手"
    backend: BackendType = None
    middleware: List[MiddlewareType] = field(default_factory=list)
    tools: ToolsType = field(default_factory=list)
    model: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    # ❌ 缺少 checkpointer 字段
    # ❌ 缺少 store 字段
```

---

## 四、需要修改的代码

### 4.1 修改 AgentConfig

```python
# src/agents/config.py 新增

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.checkpoint.base import Checkpointer
    from langgraph.store.base import BaseStore

@dataclass
class AgentConfig:
    # ... 现有字段 ...
    
    # 新增：记忆相关字段
    checkpointer: Optional["Checkpointer"] = None
    store: Optional["BaseStore"] = None
```

### 4.2 修改 AgentFactory

```python
# src/agents/agent_factory.py 修改 _create_agent_instance

def _create_agent_instance(self, config: AgentConfig) -> AgentType:
    # ... 现有代码 ...
    
    # 新增：设置 checkpointer
    if config.checkpointer is not None:
        create_kwargs['checkpointer'] = config.checkpointer
    
    # 新增：设置 store
    if config.store is not None:
        create_kwargs['store'] = config.store
    
    # 创建 Agent
    agent = create_deep_agent(**create_kwargs)
    return agent
```

### 4.3 修改 Service 层

```python
# src/app/service.py 修改

from langgraph.checkpoint.memory import MemorySaver

class Service:
    def __init__(self, config: Config) -> None:
        # ... 现有代码 ...
        
        # 新增：初始化 checkpointer
        self._checkpointer = MemorySaver()
    
    async def start(self) -> None:
        # ... 现有代码 ...
        
        # 新增：创建 Agent 时传入 checkpointer
        self._agent = get_agent_func(
            llm=self._llm,
            system_prompt=agent_config.get("system_prompt", "你是一个助手"),
            checkpointer=self._checkpointer,  # ← 新增
        )
    
    async def run(self, input_data: Any, timeout: float | None = None) -> Any:
        # ... 现有代码 ...
        
        # 新增：提取或生成 session_id
        session_id = self._get_or_create_session_id(input_data)
        
        # 新增：构建 config（关键！）
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        # 修改：传递 config 参数
        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=input_data)]},
            config=config  # ← 关键！让 LangGraph 管理历史
        )
        
        return result
    
    def _get_or_create_session_id(self, input_data: Any) -> str:
        """从输入中提取 session_id 或生成新的"""
        # 从请求中提取 client_id/conversation_id
        if isinstance(input_data, dict):
            client_id = input_data.get("client_id", "")
            conversation_id = input_data.get("conversation_id", "")
            
            if client_id and conversation_id:
                return f"{client_id}_{conversation_id}"
            elif client_id:
                return f"{client_id}_default"
        
        # 默认生成唯一 ID
        import uuid
        return f"default_{uuid.uuid4().hex[:8]}"
```

---

## 五、Session 管理方案

### 5.1 Session 生命周期

```
┌─────────────────────────────────────────────────────────────┐
│                     Session 生命周期                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 用户首次请求                                              │
│     ↓                                                        │
│  2. 提取 client_id（如钉钉用户ID）                             │
│     ↓                                                        │
│  3. 生成 thread_id = f"{client_id}_{conversation_id}"        │
│     ↓                                                        │
│  4. 调用 agent.ainvoke(input, config={thread_id})           │
│     ↓                                                        │
│  5. LangGraph 自动：                                          │
│     - 创建检查点（首次）                                       │
│     - 加载历史（后续）                                         │
│     - 保存新消息                                              │
│     ↓                                                        │
│  6. 返回响应                                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 thread_id 生成规则

```python
def generate_thread_id(client_id: str, conversation_id: str = None) -> str:
    """
    thread_id 生成规则：
    - 格式：{client_id}_{conversation_id}
    - 示例：dingtalk_123456_session_001
    """
    if conversation_id:
        return f"{client_id}_{conversation_id}"
    else:
        return f"{client_id}_default"

def parse_thread_id(thread_id: str) -> tuple[str, str]:
    """解析 thread_id"""
    parts = thread_id.rsplit("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return thread_id, "default"
```

### 5.3 不同客户端的 client_id 来源

| 客户端 | client_id 来源 | 示例 |
|-------|--------------|------|
| 钉钉 | 用户 user_id | `dingtalk_123456` |
| 飞书 | 用户 open_id | `feishu_o123456` |
| Web | Session/Cookie | `web_abc123` |
| CLI | 终端会话 | `cli_local` |

---

## 六、完整示例代码

### 6.1 最小实现

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

# 1. 启用 checkpointer
checkpointer = MemorySaver()

# 2. 创建 Agent
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    checkpointer=checkpointer
)

# 3. 首次对话（创建会话）
config = {"configurable": {"thread_id": "user_001"}}
result = agent.invoke(
    {"messages": [HumanMessage(content="你好")],},
    config=config
)
print(result["messages"][-1].content)  # AI 响应

# 4. 继续对话（自动加载历史）
result = agent.invoke(
    {"messages": [HumanMessage(content="我刚才说了什么？")]},
    config=config  # ← 同一 thread_id
)
# LangGraph 自动加载了 "你好" 这个历史消息！
```

### 6.2 生产环境配置（SQLite）

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.sqlite import SqliteSaver
import psycopg

# 使用 SQLite 持久化
checkpointer = SqliteSaver.from_conn_string("./checkpoints.db")

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    checkpointer=checkpointer,
)
```

### 6.3 生产环境配置（PostgreSQL）

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.postgres import PostgresSaver

# 使用 PostgreSQL
conn = psycopg.connect("postgresql://user:pass@localhost:5432/agent_db")
checkpointer = PostgresSaver(conn)

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    checkpointer=checkpointer,
)
```

---

## 七、总结

### 7.1 DeepAgents 短期记忆实现方式

| 项目 | 说明 |
|-----|------|
| **核心组件** | LangGraph CheckpointSaver |
| **会话标识** | thread_id（通过 config 参数传递） |
| **数据格式** | messages 列表（自动管理） |
| **调用方式** | `agent.ainvoke(input, config={"configurable": {"thread_id": "xxx"}})` |

### 7.2 修改清单

| 文件 | 修改内容 |
|-----|---------|
| `src/agents/config.py` | 添加 checkpointer/store 字段 |
| `src/agents/agent_factory.py` | 传递 checkpointer/store 到 create_deep_agent |
| `src/app/service.py` | 提取 session_id，传递 config 参数 |

### 7.3 关键点

1. **必须传递 config 参数**：否则 LangGraph 不会加载历史
2. **thread_id 唯一性**：相同 thread_id 共享对话历史
3. **Checkpointer 类型选择**：开发用 MemorySaver，生产用 SqliteSaver/PostgresSaver

---

*文档版本: v1.0*  
*创建日期: 2026-03-12*
