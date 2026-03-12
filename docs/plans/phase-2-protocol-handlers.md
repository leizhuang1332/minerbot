# Phase 2: 协议与 Handler 实施计划

## 项目背景

### 背景介绍

在 Phase 1 中，我们已经建立了 Gateway 的核心骨架：

- **protocol.py**: 定义了 WebSocket 通讯的帧格式
- **session.py**: 实现了会话管理
- **client.py**: 抽象了客户端连接
- **router.py**: 实现了消息路由

但是，路由器目前只有占位符 Handler，无法处理实际请求。

### 本阶段目标

Phase 2 的目标是实现真正的请求处理器：

1. **Agent Handler** (`handlers/agent.py`): 处理 Agent 调用请求
2. **Control Handler** (`handlers/control.py`): 处理控制指令（会话、健康检查）
3. **Gateway Server** (`server.py`): WebSocket 服务器入口

这三个模块共同构成了 Gateway 的请求处理核心。

---

## 架构设计

### Handler 在 Gateway 中的位置

```
┌─────────────────────────────────────────────────────────────┐
│                    外部请求                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 GatewayServer (server.py)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. 接受 WebSocket 连接                              │   │
│  │  2. 创建 Client 实例                                 │   │
│  │  3. 启动消息循环                                      │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              MessageRouter (router.py)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  解析消息帧                                          │   │
│  │  根据 method 分发到对应 Handler                      │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Agent       │   │ Control     │   │ (Future)    │
│ Handler     │   │ Handler     │   │ Handler     │
│             │   │             │   │             │
│ - invoke    │   │ - session  │   │             │
│ - stream    │   │ - health   │   │             │
└──────┬──────┘   └──────┬──────┘   └─────────────┘
       │                  │
       ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Session (session.py)                          │
│  - 存储消息历史                                             │
│  - 关联 Client                                             │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│              Service (核心服务)                             │
│              (通过依赖注入)                                  │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
src/gateway/
├── server.py           # ★ 本阶段: WebSocket 服务器
├── router.py           # (Phase 1)
├── protocol.py         # (Phase 1)
├── session.py          # (Phase 1)
├── client.py           # (Phase 1)
│
├── handlers/           # ★ 本阶段: 消息处理器
│   ├── __init__.py
│   ├── agent.py       # ★ Agent 调用处理
│   └── control.py     # ★ 控制指令处理
│
└── channels/           # (Phase 3+)
```

---

## 详细设计

### 1. Agent Handler (handlers/agent.py)

#### 1.1 设计目标

- 处理 `agent.invoke` 请求（非流式）
- 处理 `agent.stream` 请求（流式）
- 与核心 Service 集成

#### 1.2 核心类

```python
class AgentInvokeHandler:
    """Agent 调用处理器"""
    
    # 静态引用（由 Gateway 注入）
    _service: Optional["Service"] = None
    
    @classmethod
    def set_service(cls, service: "Service") -> None:
        """注入 Service 实例
        
        Gateway 启动时调用，将核心服务注入到 Handler。
        """
        cls._service = service
    
    @classmethod
    async def handle(cls, client: Client, frame: MessageFrame) -> None:
        """处理 agent.invoke 请求（非流式）
        
        流程:
        1. 验证 Service 和 Session 存在
        2. 提取请求参数
        3. 调用 Service.run()
        4. 添加助手消息到会话
        5. 发送响应
        """
        ...
    
    @classmethod
    async def handle_stream(
        cls, 
        client: Client, 
        frame: MessageFrame
    ) -> None:
        """处理 agent.stream 请求（流式）
        
        流程:
        1. 验证 Service 和 Session 存在
        2. 提取请求参数
        3. 调用 Service.stream_run() 并注册回调
        4. 回调中发送 agent.stream 事件
        5. 发送完成事件
        """
        ...
```

#### 1.3 请求/响应流程

**非流式调用 (agent.invoke)**:

```
Client                           AgentHandler                    Service
  │                                  │                              │
  │ {req: agent.invoke, message}    │                              │
  │ ─────────────────────────────────►                              │
  │                                  │                              │
  │                                  │      service.run(message)   │
  │                                  │ ───────────────────────────►│
  │                                  │                              │
  │                                  │      response               │
  │                                  │ ◄────────────────────────── │
  │                                  │                              │
  │ {res: ok, payload: {response}}  │                              │
  │ ◄─────────────────────────────────                              │
```

**流式调用 (agent.stream)**:

```
Client                           AgentHandler                    Service
  │                                  │                              │
  │ {req: agent.stream, message}    │                              │
  │ ─────────────────────────────────►                              │
  │                                  │                              │
  │ {res: ok, status: streaming}    │                              │
  │ ◄─────────────────────────────────                              │
  │                                  │                              │
  │                                  │   stream_run(callback)      │
  │                                  │ ───────────────────────────►│
  │                                  │         │                   │
  │                                  │◄─────── │ (chunk 1)        │
  │ {event: agent.stream, chunk}     │         │                   │
  │ ◄─────────────────────────────────         │                   │
  │                                  │         │ (chunk N)        │
  │                                  │◄─────── │                   │
  │                                  │         │                   │
  │ {event: agent.stream, done:true} │         │                   │
  │ ◄─────────────────────────────────         │                   │
```

#### 1.4 实现要点

- 使用静态变量 `_service` 存储 Service 引用（依赖注入模式）
- 流式调用通过回调函数实现每次 token 的推送
- 错误处理统一返回错误响应帧

---

### 2. Control Handler (handlers/control.py)

#### 2.1 设计目标

- 处理 `session.create`: 创建新会话
- 处理 `session.clear`: 清空会话历史
- 处理 `health`: 健康检查

#### 2.2 核心类

```python
class ControlHandler:
    """控制指令处理器"""
    
    @staticmethod
    async def handle_create_session(
        client: Client, 
        frame: MessageFrame
    ) -> None:
        """处理 session.create
        
        创建新会话并关联到客户端。
        """
        session = await client.channel.session_manager.create_session(client.id)
        client.session = session
        
        await client.send_response(
            frame.id,
            ok=True,
            payload={"session_id": session.id}
        )
    
    @staticmethod
    async def handle_clear_session(
        client: Client, 
        frame: MessageFrame
    ) -> None:
        """处理 session.clear
        
        清空会话消息历史，保留会话ID。
        """
        client.session.clear()
        
        await client.send_response(
            frame.id,
            ok=True,
            payload={"status": "cleared"}
        )
    
    @staticmethod
    async def handle_health(
        client: Client, 
        frame: MessageFrame
    ) -> None:
        """处理 health
        
        返回 Gateway 健康状态。
        """
        await client.send_response(
            frame.id,
            ok=True,
            payload={
                "status": "healthy",
                "service": "gateway",
                "version": "1.0.0"
            }
        )
```

#### 2.3 实现要点

- 使用静态方法（无状态）
- SessionManager 通过 Channel 访问
- 健康检查返回固定版本号

---

### 3. Gateway Server (server.py)

#### 3.1 设计目标

- 启动 WebSocket 服务器
- 处理连接生命周期
- 协调各组件工作

#### 3.2 核心类

```python
class GatewayServer:
    """Gateway WebSocket 服务器
    
    管理 WebSocket 连接、Channel 注册、消息路由。
    遵循 Service 层的生命周期模式（start/stop）。
    """
    
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._host = config.server.host
        self._port = config.server.port
        self._running = False
        self._server: Optional[websockets.WebSocketServer] = None
        self._shutdown_event = asyncio.Event()
        
        # 核心组件
        self._session_manager = SessionManager()
        self._router = MessageRouter(self._session_manager)
        self._channel_registry = ChannelRegistry()
        
        self._setup_signal_handlers()
    
    async def start(self) -> None:
        """启动 Gateway 服务器"""
        if self._running:
            raise RuntimeError("Gateway 已经在运行")
        
        print(f"正在启动 Gateway ({self._host}:{self._port})...")
        
        # 启动 WebSocket 服务器
        self._server = await websockets.serve(
            self._handle_connection,
            self._host,
            self._port,
            ping_interval=self._config.server.ping_interval,
            ping_timeout=self._config.server.ping_timeout,
            max_size=self._config.server.max_message_size,
        )
        
        # 启动 Session Manager
        await self._session_manager.start()
        
        # 启动 Channel Registry
        await self._channel_registry.start_all()
        
        self._running = True
        self._shutdown_event.clear()
        print(f"Gateway 启动成功 (ws://{self._host}:{self._port})")
    
    async def _handle_connection(
        self, 
        ws: WebSocketServerProtocol, 
        path: str
    ) -> None:
        """处理 WebSocket 连接
        
        Args:
            ws: WebSocket 连接
            path: 连接路径（用于区分 Channel 类型）
        """
        client_id = self._generate_client_id()
        
        # 根据 path 选择 Channel
        channel = self._channel_registry.get_channel(path)
        
        try:
            # 创建 Client
            client = await channel.handle_connect(ws, client_id)
            
            # 关联到会话
            session = self._session_manager.create_session(client_id)
            client.session = session
            
            # 启动消息处理循环
            await channel.handle_messages(client)
            
        except websockets.exceptions.ConnectionClosed as e:
            print(f"连接关闭: {client_id} (code: {e.code})")
        finally:
            # 清理会话
            self._session_manager.clear_session(client_id)
            await channel.handle_disconnect(client_id)
    
    async def stop(self) -> None:
        """停止 Gateway 服务器"""
        if not self._running:
            return
        
        # 关闭 WebSocket 服务器
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        # 停止各组件
        await self._channel_registry.stop_all()
        await self._session_manager.stop()
        
        self._running = False
        self._shutdown_event.set()
    
    async def wait_for_shutdown(self) -> None:
        """等待关闭事件"""
        await self._shutdown_event.wait()
```

#### 3.3 实现要点

- 遵循 `Service` 类的生命周期模式
- 使用 `websockets` 库提供 WebSocket 服务
- 信号处理支持优雅关闭
- Channel Registry 管理多个 Channel

---

## 实施步骤

### Step 1: 实现 Agent Handler

1. 创建 `src/gateway/handlers/__init__.py`
2. 创建 `src/gateway/handlers/agent.py`
3. 实现 `AgentInvokeHandler.handle()` - 非流式调用
4. 实现 `AgentInvokeHandler.handle_stream()` - 流式调用
5. 添加 Service 依赖注入方法

### Step 2: 实现 Control Handler

1. 创建 `src/gateway/handlers/control.py`
2. 实现 `ControlHandler.handle_create_session()`
3. 实现 `ControlHandler.handle_clear_session()`
4. 实现 `ControlHandler.handle_health()`

### Step 3: 更新 Router 注册

1. 修改 `router.py` 的 `_register_default_handlers()`
2. 导入并注册 Agent Handler
3. 导入并注册 Control Handler

### Step 4: 实现 Gateway Server

1. 创建 `src/gateway/server.py`
2. 实现 `GatewayServer` 类
3. 实现连接处理逻辑
4. 实现生命周期管理（start/stop）

### Step 5: 集成测试

1. 创建集成测试脚本
2. 测试 WebSocket 连接
3. 测试 Agent 调用
4. 测试流式响应

---

## 验收标准

### 功能验收

- [ ] `agent.invoke` 正确调用 Service 并返回响应
- [ ] `agent.stream` 正确实现流式响应（chunked transfer）
- [ ] `session.create` 正确创建会话
- [ ] `session.clear` 正确清空会话历史
- [ ] `health` 正确返回健康状态
- [ ] Gateway Server 正确接受 WebSocket 连接
- [ ] 断开连接时正确清理会话

### 错误处理验收

- [ ] Service 未启动时返回适当错误
- [ ] 会话不存在时返回适当错误
- [ ] 无效请求格式返回解析错误
- [ ] Handler 执行异常返回内部错误

### 代码质量

- [ ] 类型注解完整
- [ ] 错误处理覆盖所有分支
- [ ] 资源正确清理（连接断开、会话清理）

---

## 预计工作量

| 模块 | 工作内容 | 预计时间 |
|------|---------|---------|
| handlers/agent.py | Agent 调用处理 | 0.25 天 |
| handlers/control.py | 控制指令处理 | 0.25 天 |
| server.py | WebSocket 服务器 | 0.5 天 |
| 集成测试 | 端到端测试 | 0.5 天 |
| **合计** | | **1.5 天** |

---

## 依赖关系

- **本阶段依赖**: Phase 1 (protocol, session, client, router)
- **后续阶段依赖**: Phase 3 (Channel 实现)

---

## 附录: 与核心服务集成

### Service 注入方式

```python
# gateway/__main__.py

# 1. 启动核心服务
from src.app.config import Config
from src.app.service import Service as AppService

app_config = Config.load()
service = AppService(app_config)
await service.start()

# 2. 注入到 Handler
from src.gateway.handlers.agent import AgentInvokeHandler
AgentInvokeHandler.set_service(service)

# 3. 启动 Gateway
gateway = GatewayServer(config)
await gateway.start()
```

### Service 接口依赖

Handler 需要 Service 提供以下方法：

```python
class Service(Protocol):
    """Service 协议（Handler 需要的接口）"""
    
    async def run(self, input_data: Any, timeout: float | None = None) -> Any:
        """非流式运行"""
        ...
    
    async def stream_run(
        self,
        input_data: Any,
        callback: Callable[[str], None] | None = None,
        timeout: float | None = None
    ) -> str:
        """流式运行"""
        ...
```

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
*所属阶段: Phase 2*
