# Phase 3: Channel 适配器实施计划

## 项目背景

### 背景介绍

在前两个阶段中，我们实现了：

- **Phase 1**: Gateway 核心骨架（protocol, session, client, router）
- **Phase 2**: 请求处理器（handlers）和 WebSocket 服务器（server）

目前 Gateway 已经具备了处理请求的能力，但是还缺少与具体终端的连接适配。

### 本阶段目标

Phase 3 的目标是实现 **Channel 适配器**，这是 Gateway 连接各种终端的关键抽象：

1. **Channel 基类** (`channels/base.py`): 定义终端适配器的统一接口
2. **WebSocket Channel** (`channels/ws.py`): 标准 WebSocket 通道
3. **Channel Registry** (`channels/__init__.py`): Channel 管理与路由

Channel 适配器将不同的终端协议（如标准 WebSocket、飞书 WebSocket、钉钉 WebSocket）抽象为统一的接口，使得 Gateway 核心逻辑与具体协议解耦。

---

## 架构设计

### Channel 在 Gateway 中的位置

```
┌─────────────────────────────────────────────────────────────┐
│              各种终端                                        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │  CLI    │  │ Web UI  │  │  飞书   │  │  钉钉   │      │
│  │ (ws)    │  │  (ws)   │  │ (ws)    │  │  (ws)   │      │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
│       │            │            │            │             │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Channel 层                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ChannelRegistry                         │   │
│  │   (根据 path 路由到对应的 Channel)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                  │                  │              │
│       ▼                  ▼                  ▼              │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐          │
│  │ WS      │      │ Feishu  │      │ Dingtalk│          │
│  │ Channel │      │ Channel │      │ Channel │          │
│  └────┬────┘      └────┬────┘      └────┬────┘          │
└───────┼─────────────────┼─────────────────┼────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    GatewayServer                           │
│  - 处理连接                                                  │
│  - 消息路由                                                 │
│  - 会话管理                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
src/gateway/
├── server.py              # (Phase 2)
├── protocol.py            # (Phase 1)
├── session.py             # (Phase 1)
├── client.py              # (Phase 1)
├── router.py              # (Phase 2)
│
├── channels/              # ★ 本阶段: Channel 适配器
│   ├── __init__.py       # ★ ChannelRegistry
│   ├── base.py           # ★ Channel 基类
│   ├── ws.py             # ★ WebSocket 通道
│   ├── feishu.py         # (Phase 4)
│   └── dingtalk.py       # (Phase 5)
│
└── handlers/              # (Phase 2)
    ├── agent.py
    └── control.py
```

---

## 详细设计

### 1. Channel 基类 (channels/base.py)

#### 1.1 设计目标

- 定义终端适配器的抽象接口
- 统一生命周期管理（start/stop）
- 统一客户端管理

#### 1.2 核心类

```python
class Channel(ABC):
    """Channel 抽象基类
    
    定义终端适配器的接口。不同终端（WebSocket、飞书、钉钉）
    实现此接口以统一消息收发。
    """
    
    def __init__(self, name: str) -> None:
        """初始化 Channel
        
        Args:
            name: Channel 名称
        """
        self.name = name
        self._running = False
        self._clients: dict[str, Client] = {}
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @abstractmethod
    async def start(self) -> None:
        """启动 Channel
        
        对于需要外部连接的 Channel（如飞书、钉钉），
        在此建立连接。
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止 Channel
        
        关闭所有连接，清理资源。
        """
        pass
    
    @abstractmethod
    async def handle_connect(
        self, 
        connection: Any, 
        client_id: str
    ) -> Client:
        """处理新连接
        
        Args:
            connection: 底层连接对象
            client_id: 客户端 ID
            
        Returns:
            创建的 Client 实例
        """
        pass
    
    @abstractmethod
    async def handle_messages(self, client: Client) -> None:
        """处理消息循环
        
        从底层连接读取消息，转换为 MessageFrame 并路由。
        持续运行直到连接关闭。
        
        Args:
            client: 客户端实例
        """
        pass
    
    @abstractmethod
    async def handle_disconnect(self, client_id: str) -> None:
        """处理连接断开
        
        Args:
            client_id: 客户端 ID
        """
        pass
    
    # 通用方法
    async def send_to_client(
        self, 
        client_id: str, 
        frame: "MessageFrame"
    ) -> bool: ...
    
    async def broadcast(self, frame: "MessageFrame") -> int: ...
    
    def register_client(self, client: Client) -> None: ...
    
    def unregister_client(self, client_id: str) -> None: ...
```

#### 1.3 实现要点

- 使用 ABC 定义抽象方法
- 提供通用实现（send_to_client, broadcast）
- `_clients` 字典管理活跃客户端

---

### 2. WebSocket Channel (channels/ws.py)

#### 2.1 设计目标

- 处理标准 WebSocket 连接
- 支持 CLI、Web UI、TUI 等终端

#### 2.2 核心类

```python
class WebSocketChannel(Channel):
    """WebSocket 通道
    
    处理标准 WebSocket 连接（CLI、Web UI、TUI 等）。
    """
    
    def __init__(self) -> None:
        super().__init__("ws")
        self._router: Optional["MessageRouter"] = None
    
    def set_router(self, router: "MessageRouter") -> None:
        """设置消息路由器"""
        self._router = router
    
    async def start(self) -> None:
        """启动 Channel"""
        self._running = True
        print("WebSocket Channel 已启动")
    
    async def stop(self) -> None:
        """停止 Channel"""
        self._running = False
        
        # 关闭所有客户端连接
        for client in list(self._clients.values()):
            try:
                await client.close()
            except Exception as e:
                print(f"关闭客户端出错: {e}")
        
        self._clients.clear()
        print("WebSocket Channel 已停止")
    
    async def handle_connect(
        self,
        ws: WebSocketServerProtocol,
        client_id: str
    ) -> Client:
        """处理新连接"""
        # 创建 Client
        client = Client(id=client_id, channel=self)
        client.metadata["ws"] = ws  # 保存原始连接
        
        # 启动发送循环
        asyncio.create_task(self._send_loop(client, ws))
        
        # 注册客户端
        self.register_client(client)
        
        # 发送连接确认
        await client.send_response(client_id, ok=True, payload={"type": "hello-ok"})
        
        return client
    
    async def handle_messages(self, client: Client) -> None:
        """处理消息循环"""
        ws = client.metadata.get("ws")
        if not ws:
            return
        
        try:
            async for message in ws:
                if not client.connected:
                    break
                
                try:
                    # 解析消息帧
                    frame = MessageFrame.from_json(message)
                    
                    # 添加用户消息到会话
                    if client.session and frame.method == "agent.invoke":
                        msg_content = frame.params.get("message", "") if frame.params else ""
                        client.session.add_message("user", msg_content)
                    
                    # 路由消息
                    if self._router:
                        await self._router.route(client, frame)
                    
                except Exception as e:
                    print(f"消息解析错误: {e}")
                    await client.send_error(
                        frame.id if 'frame' in locals() else "unknown",
                        ErrorCode.INVALID_REQUEST.value,
                        f"消息格式错误: {e}"
                    )
                    
        except websockets.exceptions.ConnectionClosed:
            pass
    
    async def handle_disconnect(self, client_id: str) -> None:
        """处理连接断开"""
        client = self._clients.get(client_id)
        if client:
            await client.close()
            self.unregister_client(client_id)
    
    async def _send_loop(self, client: Client, ws: WebSocketServerProtocol) -> None:
        """发送循环 - 从队列读取消息并发送"""
        try:
            while client.connected:
                try:
                    message = await asyncio.wait_for(
                        client.send_queue.get(),
                        timeout=30
                    )
                    await ws.send(message)
                except asyncio.TimeoutError:
                    # 发送心跳
                    if ws.open:
                        await ws.ping()
        except asyncio.CancelledError:
            pass
        finally:
            client.connected = False
```

#### 2.3 实现要点

- 发送循环与接收循环分离
- 心跳保活（30秒超时）
- 异常处理确保资源清理

---

### 3. Channel Registry (channels/__init__.py)

#### 3.1 设计目标

- 管理所有 Channel 实例
- 根据路径路由到对应 Channel

#### 3.2 核心类

```python
class ChannelRegistry:
    """Channel 注册表
    
    管理所有 Channel 实例，根据连接路径路由到对应 Channel。
    """
    
    def __init__(self) -> None:
        self._channels: dict[str, Channel] = {}
        self._path_mapping: dict[str, str] = {}  # path -> channel_name
    
    def register(self, path: str, channel: Channel) -> None:
        """注册 Channel
        
        Args:
            path: 连接路径，如 "/ws", "/feishu"
            channel: Channel 实例
        """
        self._channels[channel.name] = channel
        self._path_mapping[path] = channel.name
    
    def get_channel(self, path: str) -> Channel:
        """获取 Channel
        
        Args:
            path: 连接路径
            
        Returns:
            Channel 实例
            
        Raises:
            ValueError: 如果 path 未注册
        """
        channel_name = self._path_mapping.get(path)
        if not channel_name:
            # 默认返回 WebSocket Channel
            return self._channels.get("ws", WebSocketChannel())
        
        channel = self._channels.get(channel_name)
        if not channel:
            raise ValueError(f"Channel not found: {channel_name}")
        
        return channel
    
    async def start_all(self) -> None:
        """启动所有 Channel"""
        for channel in self._channels.values():
            await channel.start()
    
    async def stop_all(self) -> None:
        """停止所有 Channel"""
        for channel in self._channels.values():
            await channel.stop()
```

#### 3.3 路径映射规则

| 路径 | Channel | 用途 |
|------|---------|------|
| `/` | WebSocket | 默认，CLI/Web UI/TUI |
| `/ws` | WebSocket | 显式 WebSocket |
| `/feishu` | Feishu | 飞书长连接 |
| `/dingtalk` | Dingtalk | 钉钉长连接 |

---

## 实施步骤

### Step 1: 创建 Channel 基类

1. 创建 `src/gateway/channels/__init__.py`
2. 创建 `src/gateway/channels/base.py`
3. 实现 `Channel` 抽象基类
4. 单元测试

### Step 2: 创建 WebSocket Channel

1. 创建 `src/gateway/channels/ws.py`
2. 实现 `WebSocketChannel` 类
3. 实现消息收发循环
4. 实现心跳机制
5. 单元测试

### Step 3: 实现 Channel Registry

1. 在 `channels/__init__.py` 中实现 `ChannelRegistry`
2. 实现注册与路由逻辑
3. 集成到 GatewayServer

### Step 4: 集成测试

1. 测试 WebSocket 连接
2. 测试消息收发
3. 测试心跳保活

---

## 验收标准

### 功能验收

- [ ] Channel 基类正确抽象所有接口
- [ ] WebSocket Channel 正确处理连接/断开
- [ ] 消息收发循环正常工作
- [ ] 心跳机制正常工作（30秒超时）
- [ ] Channel Registry 正确路由

### 错误处理验收

- [ ] 连接关闭时正确清理资源
- [ ] 消息解析错误返回错误响应
- [ ] 发送异常正确处理

### 代码质量

- [ ] 类型注解完整
- [ ] 资源正确清理
- [ ] 异常处理覆盖所有分支

---

## 预计工作量

| 模块 | 工作内容 | 预计时间 |
|------|---------|---------|
| channels/base.py | Channel 基类 | 0.25 天 |
| channels/ws.py | WebSocket 通道 | 0.5 天 |
| channels/__init__.py | Channel Registry | 0.25 天 |
| 单元测试 | Channel 测试 | 0.5 天 |
| **合计** | | **1.5 天** |

---

## 依赖关系

- **本阶段依赖**: Phase 1 (client, session), Phase 2 (router, handlers)
- **后续阶段依赖**: Phase 4 (飞书), Phase 5 (钉钉)

---

## 附录: Channel 与 Router 集成

### 初始化时注入 Router

```python
# server.py

async def start(self) -> None:
    # 创建 Channel
    ws_channel = WebSocketChannel()
    
    # 注入 Router
    ws_channel.set_router(self._router)
    
    # 注册 Channel
    self._channel_registry.register("/", ws_channel)
    self._channel_registry.register("/ws", ws_channel)
    
    # 启动
    await self._channel_registry.start_all()
```

### 消息流转

```
WebSocket 连接
    │
    ▼
Channel.handle_connect() 创建 Client
    │
    ▼
Channel.handle_messages() 消息循环
    │
    ├── 解析 MessageFrame
    ├── 添加到 Session
    │
    ▼
Channel._router.route(client, frame)
    │
    ▼
Handler 处理
    │
    ▼
Client.send() 加入发送队列
    │
    ▼
Channel._send_loop() 从队列取出并发送
```

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
*所属阶段: Phase 3*
