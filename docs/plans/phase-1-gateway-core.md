# Phase 1: Gateway 核心模块实施计划

## 项目背景

### 背景介绍

当前 MinerBot 采用**紧耦合**架构，用户只能通过本地 CLI/REPL 与系统交互。这种架构存在以下问题：

1. **接入方式单一**: 只能通过本地命令行交互
2. **无法远程访问**: 缺乏远程接入能力
3. **终端受限**: 无法支持 Web UI、TUI、飞书、钉钉等多样化终端

### 改造目标

参考 **OpenClaw Gateway** 设计，新增 **Gateway 层**实现多终端接入：

- 支持 WebSocket 通讯
- 支持飞书、钉钉等 IM 平台的 WebSocket 长连接
- 实现协议解耦，终端协议与核心服务分离

### 本阶段目标

Phase 1 的目标是建立 Gateway 的核心骨架，包括：

1. **消息协议定义** (`protocol.py`): 定义 WebSocket 通讯的帧格式
2. **会话管理** (`session.py`): 管理客户端会话状态
3. **客户端抽象** (`client.py`): 代表一个终端连接
4. **消息路由器** (`router.py`): 将请求分发给对应的 Handler

这四个模块是 Gateway 的基础设施，后续的 Channel 适配器和 Handler 都依赖它们。

---

## 架构设计

### 模块依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                     GatewayServer                          │
│                     (Phase 2)                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  MessageRouter  ◄──────────  SessionManager                │
│       │                    (session.py)                    │
│       │                          │                         │
│       ▼                          ▼                         │
│  ┌─────────┐              ┌─────────────┐                   │
│  │ Handler │              │   Session   │                   │
│  └─────────┘              └─────────────┘                   │
│       │                          │                         │
│       ▼                          ▼                         │
│  ┌─────────────────────────────────────────┐               │
│  │              Client                     │               │
│  │  (client.py)                           │               │
│  └─────────────────────────────────────────┘               │
│                            ▲                               │
│                            │                               │
│                    ┌───────┴───────┐                       │
│                    │  protocol.py   │                       │
│                    │ (消息帧定义)   │                       │
│                    └───────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
src/gateway/
├── protocol.py      # ★ 本阶段: 消息帧定义
├── session.py       # ★ 本阶段: 会话管理
├── client.py       # ★ 本阶段: 客户端抽象
├── router.py       # ★ 本阶段: 消息路由
├── server.py       # (Phase 2)
├── channels/       # (Phase 2+)
└── handlers/       # (Phase 2+)
```

---

## 详细设计

### 1. 协议定义 (protocol.py)

#### 1.1 消息帧格式

采用 JSON over WebSocket，定义三种消息类型：

```json
// 请求帧 (req)
{
  "type": "req",
  "id": "req-001",
  "method": "agent.invoke",
  "params": {
    "message": "你好",
    "stream": true
  }
}

// 响应帧 (res)
{
  "type": "res",
  "id": "req-001",
  "ok": true,
  "payload": {
    "response": "你好！有什么可以帮你的？"
  }
}

// 错误响应
{
  "type": "res",
  "id": "req-001",
  "ok": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误信息"
  }
}

// 事件帧 (event)
{
  "type": "event",
  "event": "agent.stream",
  "payload": {
    "chunk": "你好",
    "done": false
  }
}
```

#### 1.2 核心类

```python
class MessageType(str, Enum):
    REQ = "req"      # 请求
    RES = "res"      # 响应
    EVENT = "event"  # 事件

class ErrorCode(str, Enum):
    # 通用错误 (1xxx)
    INVALID_REQUEST = "INVALID_REQUEST"
    METHOD_NOT_FOUND = "METHOD_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # 会话错误 (2xxx)
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    
    # Agent 错误 (3xxx)
    AGENT_ERROR = "AGENT_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    SERVICE_NOT_RUNNING = "SERVICE_NOT_RUNNING"

@dataclass
class MessageFrame:
    type: MessageType
    id: str
    method: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    ok: Optional[bool] = None
    payload: Optional[dict[str, Any]] = None
    event: Optional[str] = None
    error: Optional[dict[str, Any]] = None
    
    @classmethod
    def from_json(cls, data: str | bytes) -> "MessageFrame": ...
    def to_json(self) -> str: ...
    @classmethod
    def create_response(cls, request_id: str, ok: bool = True, ...) -> "MessageFrame": ...
    @classmethod
    def create_event(cls, event: str, payload: Optional[dict] = None) -> "MessageFrame": ...
    @classmethod
    def create_error(cls, request_id: str, code: ErrorCode, message: str) -> "MessageFrame": ...
```

#### 1.3 实现要点

- 使用 `dataclass` 定义消息帧，简化数据操作
- `id` 字段使用 UUID 便于请求/响应关联
- 提供工厂方法简化响应/事件/错误帧创建
- 支持 `Optional` 字段，兼容不同消息类型

---

### 2. 会话管理 (session.py)

#### 2.1 设计目标

- 管理客户端会话状态
- 维护消息历史
- 支持会话过期自动清理

#### 2.2 核心类

```python
@dataclass
class Message:
    """会话消息"""
    role: str          # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Session:
    """客户端会话"""
    id: str
    client_id: str
    agent: Optional[Any] = None
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # 配置
    max_history: int = 100           # 最大历史消息数
    ttl: timedelta = timedelta(hours=24)  # 会话 TTL
    
    def add_message(self, role: str, content: str) -> None: ...
    def is_expired(self) -> bool: ...
    def clear(self) -> None: ...
    def to_langchain_messages(self) -> list[dict]: ...

class SessionManager:
    """会话管理器"""
    
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def create_session(self, client_id: str) -> Session: ...
    async def get_session(self, client_id: str) -> Optional[Session]: ...
    async def clear_session(self, client_id: str) -> None: ...
    async def clear_all(self) -> None: ...
    async def _cleanup_loop(self) -> None: ...
    async def _cleanup_expired(self) -> None: ...
```

#### 2.3 实现要点

- 使用 `asyncio.Lock` 保证并发安全
- 定期清理过期会话（默认每分钟检查）
- 自动修剪超长历史消息
- 提供 LangChain 消息格式转换，便于后续 Agent 调用

---

### 3. 客户端抽象 (client.py)

#### 3.1 设计目标

- 抽象一个终端连接
- 统一消息发送接口
- 支持发送队列（用于流式响应）

#### 3.2 核心类

```python
@dataclass
class Client:
    """客户端连接"""
    id: str
    channel: "Channel"  # 前向引用
    session: Optional[Session] = None
    send_queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # 连接状态
    connected: bool = True
    
    async def send(self, frame: MessageFrame) -> None: ...
    async def send_response(self, request_id: str, ok: bool = True, payload: Optional[dict] = None) -> None: ...
    async def send_error(self, request_id: str, code: str, message: str) -> None: ...
    async def send_event(self, event: str, payload: Optional[dict] = None) -> None: ...
    async def close(self) -> None: ...
```

#### 3.3 实现要点

- 发送队列解耦消息发送与网络传输
- 提供便捷方法发送响应/错误/事件
- `metadata` 字段存储连接特定信息（如 WebSocket 原始连接）

---

### 4. 消息路由 (router.py)

#### 4.1 设计目标

- 根据消息方法分发到对应 Handler
- 统一错误处理
- 支持 Handler 动态注册

#### 4.2 核心类

```python
# Handler 类型定义
Handler = Callable[[Client, MessageFrame], Awaitable[None]]

class MessageRouter:
    """消息路由器"""
    
    def __init__(self, session_manager: "SessionManager") -> None:
        self._session_manager = session_manager
        self._handlers: dict[str, Handler] = {}
        self._register_default_handlers()
    
    def register_handler(self, method: str, handler: Handler) -> None: ...
    async def route(self, client: Client, frame: MessageFrame) -> None: ...
    async def _handle_request(self, client: Client, frame: MessageFrame) -> None: ...
```

#### 4.3 默认 Handler 注册

```python
def _register_default_handlers(self) -> None:
    # Agent 相关 (Phase 2 实现)
    self.register_handler("agent.invoke", AgentInvokeHandler.handle)
    self.register_handler("agent.stream", AgentInvokeHandler.handle_stream)
    
    # 控制指令 (Phase 2 实现)
    self.register_handler("session.create", ControlHandler.handle_create_session)
    self.register_handler("session.clear", ControlHandler.handle_clear_session)
    self.register_handler("health", ControlHandler.handle_health)
```

#### 4.4 实现要点

- Handler 通过函数引用注册，便于测试
- 统一的错误捕获与响应
- 路由逻辑清晰：REQ → Handler，RES/EVENT 暂不处理

---

## 实施步骤

### Step 1: 创建 protocol.py

1. 创建 `src/gateway/protocol.py`
2. 实现 `MessageType` 枚举
3. 实现 `ErrorCode` 枚举
4. 实现 `MessageFrame` 数据类
5. 单元测试: 消息编解码、错误帧创建

### Step 2: 创建 session.py

1. 创建 `src/gateway/session.py`
2. 实现 `Message` 数据类
3. 实现 `Session` 数据类
4. 实现 `SessionManager` 类
5. 单元测试: 会话创建、过期、清理

### Step 3: 创建 client.py

1. 创建 `src/gateway/client.py`
2. 实现 `Client` 数据类
3. 实现发送方法（send, send_response, send_error, send_event）
4. 单元测试: 消息发送

### Step 4: 创建 router.py

1. 创建 `src/gateway/router.py`
2. 实现 `MessageRouter` 类
3. 注册默认 Handler 占位符
4. 单元测试: 路由分发

---

## 验收标准

### 功能验收

- [ ] `MessageFrame.from_json()` 正确解析请求/响应/事件帧
- [ ] `MessageFrame.to_json()` 正确序列化所有帧类型
- [ ] `MessageFrame.create_error()` 生成正确的错误响应
- [ ] `Session` 支持消息历史添加与自动修剪
- [ ] `Session.is_expired()` 正确判断会话过期
- [ ] `SessionManager` 正确管理会话生命周期
- [ ] `Client.send_queue` 正确实现消息队列
- [ ] `MessageRouter` 正确将请求分发到 Handler

### 代码质量

- [ ] 遵循项目现有代码风格（asyncio、dataclass）
- [ ] 类型注解完整
- [ ] 单元测试覆盖核心逻辑
- [ ] 无 `print` 调试语句（使用项目现有的日志方式）

---

## 预计工作量

| 模块 | 工作内容 | 预计时间 |
|------|---------|---------|
| protocol.py | 消息帧定义、编解码 | 0.25 天 |
| session.py | 会话管理、过期清理 | 0.25 天 |
| client.py | 客户端抽象、发送队列 | 0.25 天 |
| router.py | 消息路由、Handler 注册 | 0.25 天 |
| 单元测试 | 核心逻辑测试 | 0.5 天 |
| **合计** | | **1.5 天** |

---

## 依赖关系

- **本阶段依赖**: 无
- **后续阶段依赖**: Phase 2 (Handler 实现)、Phase 3 (Channel 实现)

---

## 附录: 与现有代码的集成

### 遵循现有代码模式

本阶段实现遵循项目现有代码模式：

1. **异步模式**: 使用 `async def` / `await`，参考 `Service` 类
2. **配置模式**: 使用单例模式（如 `Config` 类）
3. **日志**: 使用 `print()`（项目当前无 logging 模块）
4. **类型注解**: 完整的类型注解

### 后续集成点

```python
# Phase 2: Handler 注入 Service
from src.gateway.handlers.agent import AgentInvokeHandler
AgentInvokeHandler.set_service(service)

# Phase 3: Channel 使用 Client
channel = WebSocketChannel()
client = await channel.handle_connect(ws, client_id)

# Phase 3: Session 关联 Client
session = session_manager.create_session(client_id)
client.session = session
```

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
*所属阶段: Phase 1*
