# MinerBot Memory 模块设计方案

## 一、现状分析

### 1.1 当前 Agent 记忆能力确认

经过源码分析，当前项目的 Agent 助手**确实没有记忆能力**，证据如下：

| 代码位置 | 问题描述 |
|---------|---------|
| `src/memory/__init__.py` | 空模块，只有注释，无任何实现 |
| `src/app/service.py:189-194` | 每次调用 `ainvoke()` 都创建全新的 `HumanMessage`，不传递任何历史消息 |
| `src/agents/agent_factory.py` | 只负责创建 Agent 实例，不管理对话历史 |

**核心问题代码** (`src/app/service.py`)：
```python
# 每次调用都是全新的消息，没有任何历史！
result = await self._agent.ainvoke(
    {
        "messages": [
            HumanMessage(content=input_data)  # ← 无历史
        ]
    }
)
```

### 1.2 DeepAgents 框架能力调研结果

经过调研，DeepAgents 框架提供了以下能力，**本项目应优先复用**：

| 能力类型 | DeepAgents 组件 | 当前状态 | 建议 |
|---------|---------------|---------|------|
| **对话历史** | LangGraph CheckpointSaver | ❌ 未使用 | 启用 |
| **长期记忆** | StoreBackend + LangGraph Store | ❌ 未使用 | 启用 |
| **上下文压缩** | SummarizationMiddleware | ✅ 自动启用 | 确认启用 |
| **任务列表** | TodoListMiddleware | ✅ 自动启用 | 确认启用 |
| **技能系统** | SkillsMiddleware | ❌ 未使用 | 可选启用 |
| **子 Agent** | SubAgentMiddleware | ❌ 未使用 | 可选启用 |
| **人机交互** | HumanInTheLoopMiddleware | ❌ 未使用 | 可选启用 |

---

## 二、缺失的记忆类型分析

### 2.1 记忆类型对照表

根据 DeepAgents 框架能力，完整的 Agent 应具备的记忆类型：

| 记忆类型 | 描述 | DeepAgents 支持方式 | 优先级 |
|---------|------|-------------------|--------|
| **短期记忆** | 当前会话的对话历史 | LangGraph CheckpointSaver | P0 |
| **长期记忆** | 跨会话持久化的用户信息 | StoreBackend + LangGraph Store | P0 |
| **工作记忆** | 当前任务状态和中间结果 | TodoListMiddleware | P1 |
| **情景记忆** | 具体交互事件的记录 | Store (自定义结构) | P2 |
| **语义记忆** | 结构化知识和事实 | Store (自定义结构) | P2 |
| **程序记忆** | 学习到的行为模式 | SkillsMiddleware | P2 |

### 2.2 当前缺失的记忆

| 优先级 | 记忆类型 | 解决方案 |
|-------|---------|---------|
| **P0** | 短期记忆 | 启用 LangGraph CheckpointSaver |
| **P0** | 长期记忆 | 启用 StoreBackend + InMemoryStore |
| **P1** | 工作记忆 | 使用现有的 TodoListMiddleware |

---

## 三、解决方案：复用 DeepAgents 组件

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     MinerBot 应用层                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Service 层                              │ │
│  │  - 请求处理                                                  │ │
│  │  - 会话管理 (Session Manager) ← 需要自建                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  DeepAgents Agent                           │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Middleware (已启用)                     │   │ │
│  │  │  - TodoListMiddleware ✅                           │   │ │
│  │  │  - SummarizationMiddleware ✅                      │   │ │
│  │  │  - MemoryMiddleware ← 需要配置                     │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Backend (已配置)                        │   │ │
│  │  │  - FilesystemBackend (文件操作) ✅                 │   │ │
│  │  │  - StoreBackend (长期记忆) ← 需要配置              │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │           Checkpoint (需要启用)                       │   │ │
│  │  │  - MemorySaver (短期记忆/对话历史)                  │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              LangGraph Store (长期记忆存储)                  │ │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐              │ │
│  │  │InMemory   │  │  SQLite   │  │   Redis   │              │ │
│  │  │  Store    │  │   Store   │  │   Store   │              │ │
│  │  └───────────┘  └───────────┘  └───────────┘              │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 需要自建的模块

由于 DeepAgents 的组件是面向 Agent 内部的，我们仍需要一些**适配层**：

| 模块 | 职责 | 是否复用 DeepAgents |
|-----|------|------------------|
| **SessionManager** | 会话生命周期管理 | 自建 |
| **MessageFormatter** | 消息格式转换 | 自建 |
| **MemoryConfig** | 记忆配置管理 | 自建 |
| **LangGraph Checkpoint** | 对话历史持久化 | 复用 LangGraph |
| **LangGraph Store** | 长期记忆存储 | 复用 LangGraph |
| **MemoryMiddleware** | 记忆检索 | 复用 DeepAgents |

---

## 四、实施方案

### 4.1 修改 AgentFactory

```python
# src/agents/agent_factory.py 修改

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore

class AgentFactory:
    def _create_agent_instance(self, config: AgentConfig) -> AgentType:
        # ... 现有代码 ...
        
        # 启用 Checkpoint (短期记忆)
        checkpointer = MemorySaver()
        
        # 启用 Store (长期记忆)
        store = InMemoryStore()
        
        create_kwargs['checkpointer'] = checkpointer
        create_kwargs['store'] = store
        
        # 启用记忆路径
        create_kwargs['memory'] = [
            "/user_preferences/",  # 用户偏好
            "/conversation_history/",  # 对话历史
        ]
        
        # 创建 Agent
        agent = create_deep_agent(**create_kwargs)
        return agent
```

### 4.2 创建 SessionManager (自建)

```python
# src/memory/session.py

import uuid
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Session:
    """会话对象"""
    id: str
    client_id: str  # 客户端标识（如钉钉用户ID）
    created_at: datetime
    last_active: datetime
    metadata: Dict[str, Any]

class SessionManager:
    """会话管理器 - 管理用户会话生命周期"""
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
    
    def create_session(self, client_id: str, metadata: Optional[Dict] = None) -> Session:
        """创建新会话"""
        session = Session(
            id=str(uuid.uuid4()),
            client_id=client_id,
            created_at=datetime.now(),
            last_active=datetime.now(),
            metadata=metadata or {}
        )
        self._sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def get_or_create_session(self, client_id: str) -> Session:
        """获取或创建会话"""
        # 查找该客户端最近的会话（简化实现）
        for session in self._sessions.values():
            if session.client_id == client_id:
                session.last_active = datetime.now()
                return session
        
        return self.create_session(client_id)
    
    def update_activity(self, session_id: str) -> None:
        """更新会话活跃时间"""
        if session_id in self._sessions:
            self._sessions[session_id].last_active = datetime.now()
    
    def delete_session(self, session_id: str) -> None:
        """删除会话"""
        self._sessions.pop(session_id, None)
```

### 4.3 修改 Service 层集成

```python
# src/app/service.py 修改

from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from src.memory.session import SessionManager

class Service:
    def __init__(self, config: Config) -> None:
        # ... 现有代码 ...
        
        # 初始化 Session Manager
        self._session_manager = SessionManager()
        
        # 初始化 Checkpoint 和 Store
        self._checkpointer = MemorySaver()
        self._store = InMemoryStore()
    
    async def start(self) -> None:
        """启动服务"""
        # ... 现有代码 ...
        
        # 创建 Agent 时传入 checkpointer 和 store
        self._agent = get_agent_func(
            llm=self._llm,
            system_prompt=agent_config.get("system_prompt", "你是一个助手"),
            checkpointer=self._checkpointer,
            store=self._store,
        )
    
    async def run(self, input_data: Any, timeout: float | None = None) -> Any:
        """运行 LLM 处理请求"""
        # 获取或创建会话
        client_id = self._extract_client_id(input_data)
        session = self._session_manager.get_or_create_session(client_id)
        
        # 使用 thread_id 作为会话ID，让 LangGraph 管理历史
        config = {"configurable": {"thread_id": session.id}}
        
        # 调用 Agent（LangGraph 会自动管理对话历史）
        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=input_data)]},
            config=config
        )
        
        # 更新会话活跃时间
        self._session_manager.update_activity(session.id)
        
        return result
    
    def _extract_client_id(self, input_data: Any) -> str:
        """提取客户端ID"""
        # 从请求中提取客户端标识
        if isinstance(input_data, dict):
            return input_data.get("client_id", "default")
        return "default"
```

---

## 五、其他可复用的 DeepAgents 能力

### 5.1 当前已启用（自动）

| 组件 | 状态 | 说明 |
|-----|------|------|
| TodoListMiddleware | ✅ | 任务列表管理 |
| SummarizationMiddleware | ✅ | 上下文自动压缩 |
| FilesystemMiddleware | ✅ | 文件操作工具 |

### 5.2 可选启用

| 组件 | 用途 | 启用方式 |
|-----|------|---------|
| **SkillsMiddleware** | 技能系统 | 配置 `skills` 参数 |
| **HumanInTheLoopMiddleware** | 人机交互审批 | 配置 `interrupt_on` 参数 |
| **SubAgentMiddleware** | 子 Agent | 配置 `subagents` 参数 |

---

## 六、实施计划

### 阶段一：核心记忆功能（P0）

| 任务 | 描述 | 依赖 | 预计工作量 |
|-----|------|-----|----------|
| 修改 AgentFactory | 添加 checkpointer 和 store 支持 | DeepAgents | 0.5 天 |
| 创建 SessionManager | 会话生命周期管理 | 无 | 0.5 天 |
| 修改 Service 层 | 集成 SessionManager 和 thread_id | AgentFactory | 0.5 天 |
| 单元测试 | 记忆功能测试 | 全部 | 0.5 天 |

### 阶段二：长期记忆增强（P1）

| 任务 | 描述 | 依赖 | 预计工作量 |
|-----|------|-----|----------|
| 配置 MemoryMiddleware | 启用记忆检索 | 阶段一 | 0.5 天 |
| 实现用户偏好存储 | Store 结构设计 | 阶段一 | 1 天 |
| SQLite Store 支持 | 生产环境持久化 | 阶段一 | 1 天 |

### 阶段三：高级功能（P2）

| 任务 | 描述 | 依赖 | 预计工作量 |
|-----|------|-----|----------|
| 启用 SkillsMiddleware | 技能系统 | 阶段一 | 1 天 |
| 启用 HumanInTheLoop | 人机交互 | 阶段一 | 1 天 |
| 启用 SubAgent | 子 Agent | 阶段一 | 2 天 |

---

## 七、配置说明

### 7.1 配置文件

```yaml
# config/agent_config.yaml

agent:
  system_prompt: "你是一个助手"
  
  # 记忆配置 (新增)
  memory:
    # 短期记忆 (Checkpoint)
    checkpointer:
      enabled: true
      type: memory  # memory / sqlite
      
    # 长期记忆 (Store)
    store:
      enabled: true
      type: memory  # memory / sqlite / redis
      namespace: "minerbot"
      
    # 记忆路径
    paths:
      - "/user_preferences/"
      - "/conversation_history/"
  
  # 可选功能
  skills: []  # 技能目录列表
  interrupt_on: []  # 需要审批的操作列表
  subagents: []  # 子 Agent 列表
```

### 7.2 环境变量

```bash
# 可选：Redis 配置（生产环境）
export LANGGRAPH_STORE_REDIS_URL="redis://localhost:6379"
export LANGGRAPH_CHECKPOINT_SQLITE_URL="sqlite:///checkpoints.db"
```

---

## 八、总结

### 8.1 修改点汇总

| 文件 | 修改内容 |
|-----|---------|
| `src/agents/agent_factory.py` | 添加 checkpointer/store 支持 |
| `src/memory/__init__.py` | 导出 SessionManager |
| `src/memory/session.py` | 新建会话管理模块 |
| `src/app/service.py` | 集成会话管理和 thread_id |
| `config/agent_config.yaml` | 添加记忆配置 |

### 8.2 DeepAgents 复用总结

**本项目应优先使用 DeepAgents 框架提供的能力：**

- ✅ LangGraph CheckpointSaver — 对话历史（短期记忆）
- ✅ LangGraph Store — 长期记忆存储
- ✅ DeepAgents Backend — 文件系统操作
- ✅ DeepAgents Middleware — 任务管理、上下文压缩

**需要自建的适配层：**

- SessionManager — 会话生命周期管理
- MessageFormatter — 消息格式转换

---

*文档版本: v2.0*  
*更新日期: 2026-03-12*  
*更新内容: 复用 DeepAgents 框架组件，重新设计架构*
