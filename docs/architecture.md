# MinerBot 系统架构文档

## 1. 项目概述

### 1.1 项目简介

MinerBot 是一个基于 LangChain DeepAgents 构建的 AI 助手应用，提供交互式 REPL（Read-Eval-Print Loop）命令行界面，支持多种 LLM Provider 的灵活切换。

### 1.2 技术栈

| 类别 | 技术/库 | 版本要求 |
|------|---------|----------|
| **核心框架** | langchain-core | >=0.3.0 |
| **LLM 集成** | langchain-anthropic | >=0.3.0 |
| **Agent 框架** | deepagents | >=0.4.7 |
| **配置管理** | pyyaml | >=6.0 |
| **Python 版本** | Python | >=3.11 |

---

## 2. 系统架构总览

### 2.1 整体架构图

```mermaid
graph TB
    subgraph 用户层
        CLI[CLI 命令行]
        REPL[交互式 REPL]
    end

    subgraph 应用层
        Main[main.py 入口]
        Service[Service 服务生命周期]
        Config[Config 配置管理]
    end

    subgraph 核心层
        subgraph Agents 模块
            AF[AgentFactory 工厂]
            AC[AgentConfig 配置类]
        end

        subgraph LLMs 模块
            Factory[LLMFactory 工厂]
            MP[MiniMax Provider]
            OA[OpenAI Provider 预留]
            AA[Anthropic Provider 预留]
            AZA[Azure OpenAI Provider 预留]
        end

        subgraph 其他模块
            Prompts[prompts]
            Memory[memory]
            Chains[chains]
            Tools[tools]
            Utils[utils]
        end
    end

    subgraph 外部服务
        DeepAgents[DeepAgents SDK]
        MiniMaxAPI[MiniMax API]
        OpenAIAPI[OpenAI API 预留]
        AnthropicAPI[Anthropic API 预留]
    end

    subgraph 配置层
        AppCfg[app_config.yaml]
        LLMCfg[llm_config.yaml]
        AgentCfg[agent_config.yaml]
    end

    CLI --> Main
    REPL --> Service
    Main --> Service
    Service --> Config
    Service --> AF
    Service --> Factory
    AF --> AC
    Factory --> MP
    Factory --> OA
    Factory --> AA
    Factory --> AZA
    AF --> DeepAgents
    MP --> MiniMaxAPI
    OA --> OpenAIAPI
    AA --> AnthropicAPI
    Config --> AppCfg
    Factory --> LLMCfg
    AF --> AgentCfg
```

### 2.2 模块职责

| 模块 | 职责 | 关键类 |
|------|------|--------|
| `src/main.py` | 程序入口，CLI 参数解析 | `main()`, `async_main()` |
| `src/app/service.py` | 服务生命周期管理 | `Service` |
| `src/app/repl.py` | 交互式命令行界面 | `REPL` |
| `src/app/config.py` | 配置加载与管理 | `Config` (单例) |
| `src/agents/agent_factory.py` | Agent 实例创建与缓存 | `AgentFactory`, `get_agent()` |
| `src/agents/config.py` | Agent 配置数据类 | `AgentConfig` |
| `src/llms/factory.py` | LLM Provider 工厂 | `LLMFactory`, `get_llm()` |
| `src/llms/providers/minimax.py` | MiniMax Provider 实现 | `MiniMaxProvider` |

---

## 3. 核心模块详解

### 3.1 应用层 (src/app/)

#### 3.1.1 Service 服务类

```mermaid
classDiagram
    class Service {
        -Config _config
        -BaseChatModel _llm
        -Any _agent
        -bool _running
        -asyncio.Event _shutdown_event
        +start() 异步启动服务
        +stop() 异步停止服务
        +run() 执行单次请求
        +stream_run() 流式执行请求
    }

    class REPL {
        -Service _service
        -bool _running
        -bool _streaming
        +run() 运行交互循环
    }

    class Config {
        -Dict _config
        +service_config 服务配置
        +agent_config Agent配置
        +load() 加载配置
        +reload() 重载配置
    }

    Service --> REPL
    Service --> Config
```

**核心功能：**
- `start()`: 初始化 LLM 和 Agent 实例
- `stop()`: 优雅停止，清理资源
- `run()`: 同步执行 LLM 请求
- `stream_run()`: 流式执行（打字机效果）

#### 3.1.2 REPL 交互界面

```mermaid
sequenceDiagram
    participant User as 用户
    participant REPL as REPL
    participant Service as Service
    participant LLM as LLM/Agent

    User->>REPL: 输入文本
    REPL->>Service: stream_run(input)
    Service->>LLM: 流式调用
    LLM-->>Service: chunk 1
    Service-->>REPL: callback(chunk 1)
    REPL-->>User: 实时显示
    LLM-->>Service: chunk N
    Service-->>REPL: callback(chunk N)
    REPL-->>User: 完成显示
```

### 3.2 Agent 层 (src/agents/)

#### 3.2.1 AgentFactory 工厂模式

```mermaid
classDiagram
    class AgentFactory {
        -Dict _global_cache
        -Dict _local_cache
        +create_agent() 创建新实例
        +get_agent() 获取单例
        +get_or_create() 获取或创建
        +clear_cache() 清除缓存
        -_create_agent_instance() 内部创建
        -_resolve_llm() 解析 LLM
    }

    class AgentConfig {
        +llm: LLMType
        +system_prompt: str
        +backend: BackendType
        +middleware: List
        +tools: List
        +model: str
        +to_hash() 生成哈希
        +with_llm() 链式修改
        +with_system_prompt() 链式修改
    }

    class AgentFactoryError
    class LLMNotAvailableError
    class DeepAgentsNotAvailableError

    AgentFactory --> AgentConfig
    AgentFactory ..> AgentFactoryError
    AgentFactory ..> LLMNotAvailableError
    AgentFactory ..> DeepAgentsNotAvailableError
```

**单例模式规则：**
- 相同 `llm` + `system_prompt` → 返回同一实例
- 缓存键基于配置的 SHA256 哈希值

#### 3.2.2 Agent 创建流程

```mermaid
flowchart TD
    A[get_agent 调用] --> B{配置已缓存?}
    B -->|是| C[返回缓存实例]
    B -->|否| D[解析 LLM]
    D --> E{llm 参数类型}
    E -->|None| F[调用 src.llms.get_llm]
    E -->|str| G[调用 src.llms.get_llm(provider)]
    E -->|BaseChatModel| H[直接使用]
    F --> I[获取 LLM 实例]
    G --> I
    H --> I
    I --> J[调用 DeepAgents create_deep_agent]
    J --> K[返回 Agent 实例]
    K --> L[缓存实例]
    C --> M[返回结果]
    L --> M
```

### 3.3 LLM 层 (src/llms/)

#### 3.3.1 LLMFactory 工厂架构

```mermaid
classDiagram
    class LLMFactory {
        -Dict _providers
        -str _current_provider
        -Runnable _instance
        +register() 注册 Provider
        +get_provider() 获取 Provider
        +create() 创建 LLM 实例
        +switch_provider() 切换 Provider
        +get_current() 获取当前实例
        +list_providers() 列出可用 Provider
    }

    class LLMProvider {
        <<abstract>>
        +name: str
        +create() 创建实例
        +from_config() 从配置创建
    }

    class MiniMaxProvider {
        +name: "minimax"
        +create() 返回 ChatAnthropic
    }

    LLMFactory --> LLMProvider
    LLMProvider <|-- MiniMaxProvider
    LLMFactory ..> get_llm
    LLMFactory ..> switch_llm
```

#### 3.3.2 支持的 Provider

| Provider | 状态 | 实现 | API 兼容 |
|----------|------|------|----------|
| MiniMax | ✅ 已实现 | `MiniMaxProvider` | Anthropic 兼容 |
| OpenAI | 🔄 预留 | - | OpenAI v1 |
| Anthropic | 🔄 预留 | - | Anthropic |
| Azure OpenAI | 🔄 预留 | - | Azure |

#### 3.3.3 MiniMax Provider 配置

```mermaid
flowchart LR
    subgraph 配置层
        LLMCfg[llm_config.yaml]
        Env[环境变量 MINIMAX_API_KEY]
    end

    subgraph Provider
        MMP[MiniMaxProvider]
        CA[ChatAnthropic]
    end

    subgraph API
        MMAPI[MiniMax API<br/>/anthropic/]
    end

    LLMCfg --> MMP
    Env --> MMP
    MMP --> CA
    CA --> MMAPI
```

---

## 4. 数据流

### 4.1 完整请求流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant REPL as REPL
    participant Service as Service
    participant Agent as Agent
    participant LLM as LLM
    participant API as LLM API

    Note over User,API: 完整请求流程

    User->>REPL: "你好，请帮我..."
    REPL->>Service: stream_run(user_input)
    Service->>Agent: agent.stream()
    Agent->>LLM: llm.stream()
    LLM->>API: HTTP streaming 请求
    
    API-->>LLM: chunk 1 (thinking)
    LLM-->>Agent: Token 1
    Agent-->>Service: callback(chunk 1)
    Service-->>REPL: callback(text)
    REPL-->>User: 实时显示 [thinking...]
    
    API-->>LLM: chunk N (text)
    LLM-->>Agent: Token N
    Agent-->>Service: callback(chunk N)
    Service-->>REPL: callback(text)
    REPL-->>User: 实时显示 [完整回复]
    
    Note over User,API: 流程完成
```

### 4.2 流式响应处理

```mermaid
flowchart TD
    A[Agent.stream 调用] --> B[stream_mode='messages']
    B --> C[for chunk in stream]
    C --> D{chunk 类型}
    D -->|token| E[extract_stream_text]
    D -->|metadata| F[跳过元数据]
    E --> G{提取内容}
    G -->|thinking| H[丢弃 thinking]
    G -->|text| I[追加到响应]
    I --> J[调用 callback]
    J --> K[实时打印]
    C -->|完成| L[返回完整响应]
```

---

## 5. 配置系统

### 5.1 配置文件结构

```mermaid
graph TD
    subgraph app_config.yaml
        SVC[service<br/>host, port<br/>timeout, log_level]
        AG[agent<br/>default_provider<br/>system_prompt<br/>defaults]
    end

    subgraph llm_config.yaml
        DEF[default_provider: minimax]
        PROV[providers<br/>minimax<br/>openai<br/>anthropic<br/>azure_openai]
        LOG[logging<br/>level]
    end

    subgraph agent_config.yaml
        TA[tool_agent]
        CA[chat_agent]
        MA[multi_agent]
    end
```

### 5.2 配置加载顺序

```mermaid
flowchart LR
    A[main.py] --> B[Config.load]
    B --> C[app_config.yaml]
    C --> D[Service.start]
    D --> E[get_llm]
    E --> F[llm_config.yaml]
    F --> G[MiniMax Provider]
    D --> H[get_agent]
    H --> I[agent_config.yaml]
    I --> J[DeepAgents]
```

---

## 6. 异常处理

### 6.1 异常层次结构

```mermaid
classDiagram
    class AgentFactoryError {
        <<exception>>
    }

    class LLMNotAvailableError {
        +llm 参数无效
    }

    class DeepAgentsNotAvailableError {
        +DeepAgents 导入失败
    }

    AgentFactoryError <|-- LLMNotAvailableError
    AgentFactoryError <|-- DeepAgentsNotAvailableError
```

### 6.2 服务错误处理

| 错误类型 | 来源 | 处理方式 |
|----------|------|----------|
| `FileNotFoundError` | 配置文件 | 退出并提示 |
| `ValueError` | 配置验证 | 退出并提示 |
| `asyncio.TimeoutError` | LLM 请求 | 超时提示 |
| `RuntimeError` | 服务状态 | 异常抛出 |
| `KeyboardInterrupt` | 用户中断 | 优雅退出 |

---

## 7. 运行模式

### 7.1 启动流程

```mermaid
flowchart TD
    A[python -m src.main] --> B[parse_args]
    B --> C[load_config]
    C --> D[Service(config)]
    D --> E[await service.start]
    E --> F[初始化 LLM]
    E --> G[初始化 Agent]
    F --> H{成功?}
    G --> I{成功?}
    H -->|否| J[抛出异常]
    I -->|否| J
    H -->|是| K[打印欢迎信息]
    I -->|是| K
    K --> L[REPL(service)]
    L --> M[await repl.run]
    M --> N[await service.stop]
    N --> O[打印 goodbye]
```

### 7.2 REPL 交互命令

| 命令 | 说明 |
|------|------|
| `<文本>` | 发送消息给 AI |
| `exit` / `quit` | 退出程序 |
| 空输入 | 跳过 |

---

## 8. 文件结构

```
minerbot/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 程序入口
│   ├── app/                       # 应用层
│   │   ├── __init__.py
│   │   ├── config.py              # 配置加载
│   │   ├── service.py             # 服务生命周期
│   │   └── repl.py                # 交互界面
│   ├── agents/                    # Agent 层
│   │   ├── __init__.py
│   │   ├── agent_factory.py       # Agent 工厂
│   │   └── config.py              # Agent 配置
│   ├── llms/                      # LLM 层
│   │   ├── __init__.py
│   │   ├── factory.py             # LLM 工厂
│   │   ├── config.py              # LLM 配置
│   │   └── providers/
│   │       ├── __init__.py
│   │       └── minimax.py         # MiniMax Provider
│   ├── prompts/                   # 提示词（预留）
│   ├── memory/                    # 记忆（预留）
│   ├── chains/                    # 链（预留）
│   ├── tools/                     # 工具（预留）
│   └── utils/                     # 工具类（预留）
├── config/
│   ├── app_config.yaml            # 应用配置
│   ├── llm_config.yaml           # LLM 配置
│   ├── agent_config.yaml         # Agent 配置
│   └── deepagents_config.yaml    # DeepAgents 配置
├── tests/
│   ├── __init__.py
│   ├── test_factory.py
│   ├── test_minimax.py
│   ├── test_streaming.py
│   └── test_deepagents.py
├── docs/                          # 文档
├── pyproject.toml                 # 项目配置
└── README.md                      # 项目说明
```

---

## 9. 扩展指南

### 9.1 添加新 LLM Provider

```python
# 1. 在 src/llms/providers/ 创建新文件
# 2. 继承 LLMProvider 基类
from src.llms.factory import LLMProvider

class NewProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "newprovider"
    
    def create(self, **kwargs) -> BaseChatModel:
        # 实现创建逻辑
        return ChatOpenAI(...)
    
    @classmethod
    def from_config(cls, provider_config: Dict) -> "LLMProvider":
        return cls(...)

# 3. 在 src/llms/__init__.py 或 factory.py 中注册
LLMFactory.register("newprovider", NewProvider)
```

### 9.2 添加新 Agent 类型

```python
# 在 src/agents/agent_factory.py 中扩展
def _create_agent_instance(self, config: AgentConfig) -> AgentType:
    # 根据 config 添加新的 agent 创建逻辑
    if config.agent_type == "custom":
        return create_custom_agent(...)
    # ... 现有逻辑
```

---

## 10. 总结

MinerBot 采用分层架构设计，核心组件包括：

1. **应用层**: 提供 CLI 和 REPL 交互界面
2. **Agent 层**: 基于 DeepAgents SDK 的 Agent 工厂，支持单例缓存
3. **LLM 层**: 统一的 Provider 工厂，支持多种 LLM 服务商
4. **配置层**: YAML 配置文件驱动

系统设计遵循：
- **单例模式**: AgentFactory 和 Config 使用单例
- **工厂模式**: LLMFactory 和 AgentFactory 抽象创建逻辑
- **异步优先**: 使用 asyncio 处理流式请求
- **配置驱动**: 所有关键参数可配置

---

*文档生成时间: 2026-03-11*
*项目版本: 0.1.0*
