# DeepAgents 框架全面深度解析

## 概述

DeepAgents 是由 LangChain 官方团队开发的一个开源 Agent（智能体）框架，定位为"Batteries-Included"（开箱即用）的 Agent 开发套件。该框架基于 LangGraph 运行时构建，集成了规划工具、文件系统操作、子代理管理等核心能力，专为处理复杂的多步骤任务而设计。

### 框架基本信息

| 属性 | 值 |
|------|-----|
| 官方仓库 | https://github.com/langchain-ai/deepagents |
| 最新版本 | 0.4.11 (2026-03-13) |
| Python 版本要求 | >= 3.11 |
| 许可证 | MIT |
| GitHub Stars | 11,000+ |
| 核心依赖 | LangChain, LangGraph |

### 设计理念

DeepAgents 的核心理念是降低构建复杂 AI Agent 的门槛。传统方式下，开发者需要自行集成提示词工程、工具定义、上下文管理、子代理协调等多个组件，而 DeepAgents 将这些能力打包提供，使开发者能够"开箱即用"地获得一个功能完备的 Agent，同时保持高度可定制性。

---

## 完整 API 体系详解

### 核心函数：create_deep_agent

这是 DeepAgents 框架的主要入口函数，用于创建和编译一个完整的 Deep Agent 实例。

#### 函数签名

```python
def create_deep_agent(
    model: Optional[Union[str, BaseMessageGraph]] = None,
    tools: Optional[List[Union[BaseTool, Callable]]] = None,
    system_prompt: Optional[str] = None,
    name: Optional[str] = None,
    subagents: Optional[List[Dict[str, Any]]] = None,
    skills: Optional[List[str]] = None,
    memory: Optional[List[str]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    store: Optional[BaseStore] = None,
    backend: Optional[Union[Callable, BaseBackend]] = None,
    middleware: Optional[List[Any]] = None,
    interrupt_on: Optional[Dict[str, bool]] = None,
    debug: bool = False,
    **kwargs
) -> CompiledStateGraph:
```

#### 参数详解

| 参数名 | 类型 | 默认值 | 必填 | 说明 |
|--------|------|--------|------|------|
| `model` | `str \| BaseMessageGraph` | `None` | 否 | LLM 模型标识符（如 "openai:gpt-4o"）或 LangChain 模型实例 |
| `tools` | `List[BaseTool \| Callable]` | `None` | 否 | 自定义工具列表，扩展 Agent 能力 |
| `system_prompt` | `str` | `None` | 否 | 系统提示词，定义 Agent 行为和角色 |
| `name` | `str` | `None` | 否 | Agent 实例名称，用于调试和标识 |
| `subagents` | `List[Dict]` | `None` | 否 | 子代理配置列表，支持任务委托 |
| `skills` | `List[str]` | `None` | 否 | 技能目录列表，按需加载 |
| `memory` | `List[str]` | `None` | 否 | AGENTS.md 文件路径列表，注入持久上下文 |
| `checkpointer` | `BaseCheckpointSaver` | `None` | 否 | 会话状态持久化检查点 |
| `store` | `BaseStore` | `None` | 否 | 长期数据存储，支持跨会话 |
| `backend` | `Callable \| BaseBackend` | `None` | 否 | 文件系统后端配置 |
| `middleware` | `List[Any]` | `None` | 否 | 自定义中间件列表 |
| `interrupt_on` | `Dict[str, bool]` | `None` | 否 | 工具执行前中断配置 |
| `debug` | `bool` | `False` | 否 | 调试模式开关 |

#### 返回值

返回 `CompiledStateGraph` 对象——一个编译后的 LangGraph 状态图，支持同步和异步调用、Streaming 模式、LangGraph Studio 调试等特性。

#### 使用示例

```python
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic

# 基础用法
agent = create_deep_agent()

# 完整配置
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    tools=[my_tool1, my_tool2],
    system_prompt="你是一个专业的编程助手。",
    name="DevAssistant",
    subagents=[research_agent_config],
    skills=["./skills/"],
    memory=["./AGENTS.md"],
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
)
```

### 内置工具 API

DeepAgents 内置了一系列开箱即用的工具，Agent 自动获得这些能力：

#### 1. 规划工具

| 工具名称 | 函数签名 | 功能描述 |
|----------|----------|----------|
| `write_todos` | `write_todos(todos: List[Dict[str, str]]) -> str` | 任务分解和进度追踪 |

```python
# 使用示例
write_todos([
    {"content": "研究主题 X", "status": "in_progress"},
    {"content": "撰写报告", "status": "pending"},
])
```

#### 2. 文件系统工具

| 工具名称 | 功能描述 |
|----------|----------|
| `ls` | 列出目录内容 |
| `glob` | 模式匹配文件 |
| `grep` | 文件内容搜索 |
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件内容 |
| `edit_file` | 编辑文件内容 |

#### 3. Shell 执行工具

| 工具名称 | 功能描述 |
|----------|----------|
| `execute` / `bash` | 执行 Shell 命令（沙箱环境） |

#### 4. 子代理委托工具

| 工具名称 | 函数签名 | 功能描述 |
|----------|----------|----------|
| `task` | `task(subagent_type: str, description: str) -> str` | 委托任务给子代理 |

```python
# 使用示例
task(
    subagent_type="researcher",
    description="研究 AI 发展趋势，保存到 research/ai-trends.md"
)
```

### 后端系统 API

#### FilesystemBackend

```python
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(
    root_dir="/workspace/project",    # 根目录
    virtual_mode=True,                # 虚拟文件系统模式
)
```

#### StateBackend

```python
from deepagents.backends import StateBackend

# 默认内存后端
agent = create_deep_agent(backend=StateBackend)
```

#### StoreBackend

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

def namespace_factory(ctx):
    user_id = ctx.runtime.context.get("user_id", "default")
    return ("users", user_id, "files")

agent = create_deep_agent(
    store=store,
    backend=lambda rt: StoreBackend(rt, namespace=namespace_factory),
)
```

#### CompositeBackend

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

backend = CompositeBackend(
    default=StateBackend,
    routes={
        "/memories/": StoreBackend,  # 特定路径使用不同后端
    }
)
```

### 中间件系统 API

#### MemoryMiddleware

```python
from deepagents import MemoryMiddleware
from deepagents.backends import FilesystemBackend

memory_middleware = MemoryMiddleware(
    backend=FilesystemBackend(root_dir="/project"),
    sources=[
        "~/.deepagents/AGENTS.md",  # 用户级别记忆
        "./AGENTS.md",              # 项目级别记忆
    ],
)

agent = create_deep_agent(middleware=[memory_middleware])
```

---

## 核心功能深度解析

### 1. 规划能力 (Planning)

DeepAgents 内置的 `write_todos` 工具赋予了 Agent 任务分解和进度追踪的能力。这是"Deep Agent"与传统"Shallow Agent"的核心区别之一。

**工作原理**：
- Agent 收到复杂任务时，可调用 `write_todos` 将任务分解为多个子任务
- 每个子任务有 `status` 属性：`pending`（待处理）、`in_progress`（进行中）、`completed`（已完成）
- Agent 可在执行过程中动态更新任务状态，适应变化

**典型工作流**：
```python
# Agent 自动生成的任务计划示例
write_todos([
    {"content": "保存研究请求到 /research_request.md", "status": "completed"},
    {"content": "使用子代理研究 AI 代理的上下文工程方法", "status": "in_progress"},
    {"content": "综合发现并撰写最终报告到 /final_report.md", "status": "pending"},
    {"content": "根据原始请求验证报告", "status": "pending"},
])
```

### 2. 上下文管理 (Context Management)

传统的 Agent 在处理长对话时面临上下文窗口溢出的问题。DeepAgents 通过文件系统工具解决这一挑战：

**核心机制**：
- Agent 可将大量上下文信息写入文件
- 通过 `read_file` 工具按需读取
- 自动触发上下文压缩（summarization）

**优势**：
- 支持处理任意长度的任务输出
- 避免上下文窗口限制
- 便于结果的持久化和后续检索

### 3. 子代理委托 (Subagent Spawning)

DeepAgents 支持创建专门的子代理来处理特定任务：

**关键特性**：
- **上下文隔离**：子代理在独立的上下文中运行，不污染主代理的上下文
- **并行执行**：可同时生成多个子代理处理独立任务
- **结果合成**：主代理汇总各子代理的发现形成最终答案

**配置结构**：
```python
research_subagent = {
    "name": "research-agent",
    "description": "研究主题并收集信息",
    "system_prompt": """你是一个研究专家。
    - 简单查询使用 2-3 次搜索
    - 复杂主题最多 5 次搜索
    - 每次搜索后使用 think_tool 评估进度
    - 获得足够信息后停止""",
    "tools": [web_search, think_tool],
}

agent = create_deep_agent(subagents=[research_subagent])
```

### 4. 长期记忆 (Long-term Memory)

DeepAgents 提供三层记忆机制：

| 记忆类型 | 作用范围 | 持久化 | 典型用途 |
|----------|----------|--------|----------|
| **Memory** | 当前会话 | 文件/内存 | 加载 AGENTS.md 上下文 |
| **Checkpointer** | 会话级 | 可配置 | 会话状态恢复 |
| **Store** | 跨会话 | 可配置 | 用户偏好持久化 |

### 5. 可插拔后端系统

DeepAgents 的文件系统层采用可插拔架构：

| 后端类型 | 用途 | 持久化 |
|----------|------|--------|
| `StateBackend` | 内存状态（默认） | ❌ |
| `FilesystemBackend` | 本地文件系统 | ✅ |
| `StoreBackend` | LangGraph Store 集成 | ✅ |
| `CompositeBackend` | 混合路由 | 可配置 |

---

## 标准使用流程与最佳实践

### 快速开始流程

```python
# 第 1 步：安装框架
pip install deepagents
# 或
uv add deepagents

# 第 2 步：创建 Agent
from deepagents import create_deep_agent

agent = create_deep_agent()

# 第 3 步：调用 Agent
result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "研究 LangGraph 并撰写摘要"
    }]
})

# 第 4 步：获取结果
print(result["messages"][-1].content)
```

### 进阶配置流程

```python
# 第 1 步：导入依赖
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

# 第 2 步：定义自定义工具
@tool
def search_docs(query: str) -> str:
    """搜索文档内容。"""
    # 实现搜索逻辑
    return f"关于 '{query}' 的搜索结果..."

# 第 3 步：配置持久化
checkpointer = MemorySaver()
store = InMemoryStore()

# 第 4 步：创建 Agent
agent = create_deep_agent(
    model=ChatAnthropic(model_name="claude-sonnet-4-6"),
    tools=[search_docs],
    system_prompt="你是一个专业的研究助手。",
    checkpointer=checkpointer,
    store=store,
)

# 第 5 步：配置会话并调用
config = {"configurable": {"thread_id": "session_001"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "分析 AI 发展趋势"}]},
    config=config
)
```

### 最佳实践

#### 1. 模型选择

- **复杂推理任务**：使用 Claude Sonnet 4 或 GPT-4o
- **简单任务**：使用 Claude Haiku 或 GPT-4o-mini 以降低成本
- **代码生成**：优先选择有代码训练数据的模型

#### 2. 工具设计

```python
# ✅ 好的工具设计：清晰的文档字符串
@tool
def calculate(expression: str) -> str:
    """执行数学计算。
    
    Args:
        expression: 数学表达式，如 "2+2" 或 "sqrt(16)"
    
    Returns:
        计算结果字符串
    """
    return str(eval(expression))

# ❌ 不好的工具设计：缺少文档
@tool
def calc(x):
    return str(eval(x))
```

#### 3. 系统提示词优化

```python
# ✅ 清晰的指令结构
system_prompt = """你是一个专业的研究助手。

工作流程：
1. 理解用户需求
2. 制定研究计划
3. 收集相关信息
4. 撰写报告

约束：
- 使用最多 5 次搜索
- 提供可靠的信息来源
- 保持客观立场"""

# ❌ 模糊的指令
system_prompt = """你是一个研究助手，尽量做好。"""
```

#### 4. 子代理配置

```python
# ✅ 明确的子代理定义
researcher = {
    "name": "researcher",
    "description": "进行网络搜索和信息收集",  # 供主代理决策
    "system_prompt": """你是一个专业研究员。
    - 只搜索可靠来源
    - 保存关键发现到文件
    - 避免重复搜索""",
    "tools": [web_search],
}

# ❌ 不完整的子代理定义
researcher = {"name": "researcher"}
```

#### 5. 错误处理

```python
try:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "任务描述"}]},
        config=config
    )
except Exception as e:
    logger.error(f"Agent 执行失败: {e}")
    # 降级处理或重试逻辑
```

---

## 与 LangChain 1.0、LangGraph 的对比分析

### 技术关系总览

```
┌─────────────────────────────────────────────────────┐
│                    LangChain                        │
│  (核心构建块：LLMs, Prompts, Tools, Memory)         │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                    LangGraph                         │
│  (运行时：状态图、执行引擎、持久化、检查点)           │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                   DeepAgents                        │
│  (Agent Harness：预置工具、子代理、文件系统)         │
└─────────────────────────────────────────────────────┘
```

### DeepAgents vs LangChain 1.0

| 维度 | LangChain 1.0 | DeepAgents |
|------|---------------|------------|
| **架构模式** | Chains（顺序链式）/ Agents（动态工具选择） | Agent Harness（预置能力） |
| **工具系统** | 需手动定义和绑定 | 内置 10+ 工具 |
| **上下文管理** | Memory 类（ConversationSummaryMemory 等） | 文件系统 + 自动压缩 |
| **子代理支持** | 有限 | 原生支持 |
| **上手难度** | 中等（需理解 Components） | 低（开箱即用） |
| **定制化程度** | 高（模块化设计） | 中（预设最佳实践） |

**核心差异说明**：

LangChain 1.0 强调"灵活组装"——开发者可以自由组合 LLM、Prompt、Memory、Tools 等组件构建 Agent。这种设计提供了极大的灵活性，但同时也意味着开发者需要做出更多决策、了解更多概念。

DeepAgents 则采用"Opinionated"（约定优于配置）的设计理念——框架已经为常见场景预设了最佳实践，开发者可以直接使用默认值获得良好体验，同时保留深度定制的能力。

**选择建议**：
- **使用 DeepAgents**：快速构建生产级 Agent、需要文件系统/子代理能力
- **使用 LangChain 1.0**：需要极强定制能力、已有现有架构不便迁移

### DeepAgents vs LangGraph

| 维度 | LangGraph | DeepAgents |
|------|-----------|------------|
| **抽象层级** | 运行时/编排层 | 应用层框架 |
| **核心概念** | StateGraph、Nodes、Edges | Agent、Tools、Memory |
| **持久化** | Checkpointer、Store | 继承 LangGraph 能力 |
| **工具支持** | 需自行构建工具系统 | 内置工具集 |
| **适用场景** | 自定义工作流、复杂编排 | 通用 Agent 开发 |

**技术关系详解**：

LangGraph 是一个"图执行引擎"——它提供了定义状态图、编排节点、执行流程、持久化状态的能力。使用 LangGraph 构建 Agent 需要：
1. 定义状态（State）
2. 定义节点（Nodes）
3. 定义边（Edges）
4. 编译图（compile）

DeepAgents 则是构建在 LangGraph 之上的"应用框架"——它已经完成了上述工作，开发者只需关注业务逻辑（工具、提示词、记忆）。

**重要特性**：DeepAgents 返回的就是编译后的 LangGraph 图，这意味着：
```python
agent = create_deep_agent(...)

# 可以使用所有 LangGraph 特性
# 1. Streaming
for chunk in agent.stream({"messages": [("user", "hello")]}):
    print(chunk)

# 2. LangGraph Studio 调试
# 直接在 LangGraph Studio 中加载

# 3. Checkpointing
config = {"configurable": {"thread_id": "session_001"}}
agent.invoke(..., config=config)

# 4. 任何 LangGraph 特性
```

### 集成可能性

DeepAgents 与 LangGraph 的集成是无缝的：

```python
# 1. 使用 LangGraph 检查点
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

checkpointer = PostgresSaver(conn)
store = PostgresStore.from_conn_string(DB_URI)

agent = create_deep_agent(
    checkpointer=checkpointer,
    store=store,
)

# 2. 扩展 LangGraph 节点
from langgraph.graph import StateGraph

# 获取底层图并扩展
graph = agent.graph  # CompiledStateGraph

# 添加自定义节点
graph.add_node("custom_node", custom_function)

# 3. 自定义工作流
new_graph = StateGraph(AgentState)
new_graph.add_node("agent", agent)
# ... 自定义更多节点
```

### 选择决策指南

```
开始构建 Agent
      │
      ▼
┌─────────────────┐
│ 任务复杂度如何？  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   高        低
    │         │
    ▼         ▼
┌─────────┐ ┌─────────────┐
│ 需要深度 │ │ 简单任务    │
│ 定制？   │ │ 快速原型    │
└────┬────┘ └──────┬──────┘
     │             │
   是  否        是  否
   │   │         │   │
   ▼   ▼         ▼   ▼
 ┌────┐ ┌──────────┐ ┌─────┐
 │Lang│ │DeepAgents │ │Lang │ 
 │Graph│ │(推荐)    │ │Chain│
 └────┘ └──────────┘ └─────┘
```

---

## 常见问题解决方案

### Q1: 如何选择合适的 Checkpointer？

| 场景 | 推荐方案 |
|------|----------|
| 本地开发/测试 | `MemorySaver` |
| 单用户本地工作流 | `SqliteSaver` |
| 生产环境 | `PostgresSaver` 或 `RedisSaver` |

### Q2: 子代理与主代理上下文如何隔离？

子代理在独立的 ephemeral（临时）上下文中运行，主代理的对话历史不会传递给子代理。数据传递通过：
1. **description 参数**：主代理在调用 `task` 时传入详细任务描述
2. **文件系统**：子代理可将结果写入文件，主代理读取

### Q3: 如何处理工具执行危险操作？

使用 `interrupt_on` 配置在执行前中断：

```python
agent = create_deep_agent(
    interrupt_on={
        "bash": True,        # 执行 shell 命令前中断
        "edit_file": True,   # 编辑文件前中断
        "write_file": True,  # 写入文件前中断
    }
)
```

### Q4: 如何实现多租户隔离？

```python
def get_session_config(user_id: str):
    return {
        "configurable": {
            "thread_id": f"user_{user_id}_session",
            "checkpoint_id": None,
        }
    }

# 每个用户使用独立的 thread_id
result = agent.invoke(input, config=get_session_config(user_id))
```

### Q5: Agent 忘记上下文怎么办？

1. **检查是否使用 Checkpointer**：确保配置了 `checkpointer` 并在调用时传入 `config`
2. **检查 thread_id**：不同 `thread_id` 不会共享会话状态
3. **检查 Memory 配置**：确认 AGENTS.md 文件路径正确

### Q6: 工具调用失败如何处理？

DeepAgents 内置了工具调用重试机制。如需自定义处理：

```python
from langchain_core.tools import Tool

def custom_tool(x: str) -> str:
    try:
        # 工具逻辑
        return result
    except Exception as e:
        # 自定义错误处理
        return f"错误: {str(e)}"

tool = Tool(
    name="custom",
    func=custom_tool,
    description="工具描述"
)
```

---

## 总结与展望

DeepAgents 框架代表了 AI Agent 开发的一个重要里程碑——它将原本只有 Claude Code、Deep Research 等顶级 AI 产品才具备的"深度 Agent"能力，以开源库的形式提供给广大开发者。

**核心价值**：
- **开箱即用**：10+ 内置工具、规划能力、子代理支持
- **构建于 LangGraph 之上**：继承所有 LangGraph 特性（持久化、流式、调试）
- **高度可定制**：从工具到提示词、从后端到中间件
- **生产就绪**：MIT 许可、无供应商锁定、社区活跃

**适用场景**：
- 编程助手（如 Claude Code）
- 研究 Agent（如 Deep Research）
- 多步骤自动化工作流
- 需要长期记忆的对话系统

**不适合场景**：
- 极简的单一问答
- 完全定制的工作流（考虑直接使用 LangGraph）
- 对供应商有强约束的情况

随着 AI Agent 技术的快速发展，DeepAgents 正在成为构建下一代 AI 应用的重要基础设施。建议开发者在项目中考虑采用 DeepAgents，以获得持续的功能更新和社区支持。
