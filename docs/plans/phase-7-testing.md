# Phase 7: 测试策略实施计划

## 项目背景

### 背景介绍

在前六个阶段中，我们实现了完整的 Gateway 系统。现在需要建立完善的测试体系，确保代码质量。

### 测试策略概览

| 测试级别 | 范围 | 工具 | 占比 |
|---------|------|------|------|
| 单元测试 | 独立模块 | pytest | 60% |
| 集成测试 | 模块协作 | pytest + fixtures | 30% |
| 端到端测试 | 完整流程 | pytest + subprocess | 10% |

### 本阶段目标

建立完整的测试体系：

1. **单元测试**: 覆盖核心模块
2. **集成测试**: 验证模块协作
3. **测试工具**: WebSocket 测试客户端

---

## 测试架构

### 测试文件结构

```
minerbot/
├── tests/
│   ├── __init__.py
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_protocol.py      # 协议测试
│   │   ├── test_session.py       # 会话测试
│   │   ├── test_client.py         # 客户端测试
│   │   ├── test_router.py         # 路由测试
│   │   └── test_handlers.py       # Handler 测试
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_channel_ws.py     # WebSocket Channel 测试
│   │   ├── test_gateway.py         # Gateway 集成测试
│   │   └── test_service.py         # Service 集成测试
│   │
│   ├── e2e/
│   │   ├── __init__.py
│   │   └── test_websocket_flow.py  # 端到端测试
│   │
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── websocket.py           # WebSocket fixtures
│   │   └── mocks.py               # Mock 对象
│   │
│   └── conftest.py                # pytest 配置
│
└── pyproject.toml                 # 测试依赖配置
```

---

## 单元测试

### 1. Protocol 测试 (test_protocol.py)

#### 1.1 测试用例

```python
import pytest
from src.gateway.protocol import (
    MessageFrame, 
    MessageType, 
    ErrorCode
)


class TestMessageFrame:
    """MessageFrame 测试"""
    
    def test_from_json_request(self):
        """测试解析请求帧"""
        json_str = '{"type": "req", "id": "test-001", "method": "agent.invoke", "params": {"message": "hello"}}'
        frame = MessageFrame.from_json(json_str)
        
        assert frame.type == MessageType.REQ
        assert frame.id == "test-001"
        assert frame.method == "agent.invoke"
        assert frame.params == {"message": "hello"}
    
    def test_from_json_response(self):
        """测试解析响应帧"""
        json_str = '{"type": "res", "id": "test-001", "ok": true, "payload": {"response": "hello"}}'
        frame = MessageFrame.from_json(json_str)
        
        assert frame.type == MessageType.RES
        assert frame.ok is True
        assert frame.payload == {"response": "hello"}
    
    def test_to_json_request(self):
        """测试序列化请求帧"""
        frame = MessageFrame(
            type=MessageType.REQ,
            id="test-001",
            method="agent.invoke",
            params={"message": "hello"}
        )
        
        json_str = frame.to_json()
        data = json.loads(json_str)
        
        assert data["type"] == "req"
        assert data["id"] == "test-001"
        assert data["method"] == "agent.invoke"
    
    def test_create_response(self):
        """测试创建响应帧"""
        frame = MessageFrame.create_response(
            request_id="test-001",
            ok=True,
            payload={"response": "hello"}
        )
        
        assert frame.type == MessageType.RES
        assert frame.id == "test-001"
        assert frame.ok is True
    
    def test_create_error(self):
        """测试创建错误帧"""
        frame = MessageFrame.create_error(
            request_id="test-001",
            code=ErrorCode.INVALID_REQUEST,
            message="无效请求"
        )
        
        assert frame.ok is False
        assert frame.error["code"] == "INVALID_REQUEST"
        assert frame.error["message"] == "无效请求"
    
    def test_create_event(self):
        """测试创建事件帧"""
        frame = MessageFrame.create_event(
            event="agent.stream",
            payload={"chunk": "hello", "done": False}
        )
        
        assert frame.type == MessageType.EVENT
        assert frame.event == "agent.stream"
        assert frame.payload["chunk"] == "hello"
```

---

### 2. Session 测试 (test_session.py)

#### 2.1 测试用例

```python
import pytest
import asyncio
from datetime import datetime, timedelta
from src.gateway.session import Session, SessionManager, Message


class TestMessage:
    """Message 测试"""
    
    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)


class TestSession:
    """Session 测试"""
    
    def test_session_creation(self):
        """测试会话创建"""
        session = Session(id="sess-001", client_id="client-001")
        
        assert session.id == "sess-001"
        assert session.client_id == "client-001"
        assert len(session.messages) == 0
    
    def test_add_message(self):
        """测试添加消息"""
        session = Session(id="sess-001", client_id="client-001")
        
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi")
        
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
    
    def test_max_history(self):
        """测试历史消息限制"""
        session = Session(id="sess-001", client_id="client-001", max_history=3)
        
        for i in range(5):
            session.add_message("user", f"Message {i}")
        
        assert len(session.messages) == 3
        assert session.messages[0].content == "Message 2"
    
    def test_is_expired(self):
        """测试会话过期"""
        session = Session(id="sess-001", client_id="client-001")
        session.last_active = datetime.now() - timedelta(hours=25)
        
        assert session.is_expired() is True
    
    def test_clear(self):
        """测试清空会话"""
        session = Session(id="sess-001", client_id="client-001")
        session.add_message("user", "Hello")
        
        session.clear()
        
        assert len(session.messages) == 0
        assert session.agent is None


class TestSessionManager:
    """SessionManager 测试"""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """测试创建会话"""
        manager = SessionManager()
        
        session = await manager.create_session("client-001")
        
        assert session.id.startswith("sess-")
        assert session.client_id == "client-001"
    
    @pytest.mark.asyncio
    async def test_get_session(self):
        """测试获取会话"""
        manager = SessionManager()
        
        created = await manager.create_session("client-001")
        retrieved = await manager.get_session("client-001")
        
        assert created.id == retrieved.id
    
    @pytest.mark.asyncio
    async def test_clear_session(self):
        """测试清理会话"""
        manager = SessionManager()
        
        await manager.create_session("client-001")
        await manager.clear_session("client-001")
        
        session = await manager.get_session("client-001")
        assert session is None
```

---

### 3. Router 测试 (test_router.py)

#### 3.1 测试用例

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.gateway.router import MessageRouter
from src.gateway.protocol import MessageFrame, MessageType


class TestMessageRouter:
    """MessageRouter 测试"""
    
    @pytest.mark.asyncio
    async def test_route_to_handler(self):
        """测试路由到 Handler"""
        manager = MagicMock()
        router = MessageRouter(manager)
        
        # 注册 Handler
        handler = AsyncMock()
        router.register_handler("test.method", handler)
        
        # 创建请求
        client = MagicMock()
        frame = MessageFrame(
            type=MessageType.REQ,
            id="test-001",
            method="test.method",
            params={}
        )
        
        # 路由
        await router.route(client, frame)
        
        # 验证 Handler 被调用
        handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_method_not_found(self):
        """测试方法不存在"""
        manager = MagicMock()
        router = MessageRouter(manager)
        
        client = MagicMock()
        frame = MessageFrame(
            type=MessageType.REQ,
            id="test-001",
            method="nonexistent.method",
            params={}
        )
        
        await router.route(client, frame)
        
        # 验证发送错误响应
        client.send_error.assert_called_once()
```

---

## 集成测试

### 1. WebSocket Channel 测试

#### 1.1 测试用例

```python
import pytest
import asyncio
import websockets
from src.gateway.channels.ws import WebSocketChannel
from src.gateway.router import MessageRouter


class TestWebSocketChannel:
    """WebSocket Channel 测试"""
    
    @pytest.mark.asyncio
    async def test_handle_connect(self):
        """测试连接处理"""
        channel = WebSocketChannel()
        await channel.start()
        
        # Mock WebSocket
        ws = AsyncMock()
        client = await channel.handle_connect(ws, "test-client")
        
        assert client.id == "test-client"
        assert client.channel == channel
        assert client.connected is True
        
        await channel.stop()
    
    @pytest.mark.asyncio
    async def test_send_receive(self):
        """测试消息收发"""
        channel = WebSocketChannel()
        router = MessageRouter(MagicMock())
        channel.set_router(router)
        await channel.start()
        
        # Mock WebSocket
        ws = AsyncMock()
        ws.__aiter__ = lambda self: iter([
            '{"type": "req", "id": "test", "method": "health", "params": {}}'
        ])
        
        client = await channel.handle_connect(ws, "test-client")
        
        # 处理消息
        await channel.handle_messages(client)
        
        # 验证响应发送
        # (检查 ws.send 被调用)
        
        await channel.stop()
```

---

### 2. Gateway 集成测试

#### 2.1 测试用例

```python
import pytest
import asyncio
import websockets
from src.gateway.server import GatewayServer
from src.gateway.config import GatewayConfig


class TestGatewayServer:
    """GatewayServer 测试"""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动和停止"""
        # 创建配置
        config = GatewayConfig.load()
        
        # 创建 Gateway
        gateway = GatewayServer(config)
        
        # 启动
        await gateway.start()
        assert gateway.is_running is True
        
        # 停止
        await gateway.stop()
        assert gateway.is_running is False
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """测试 WebSocket 连接"""
        config = GatewayConfig.load()
        gateway = GatewayServer(config)
        
        await gateway.start()
        
        # 连接 WebSocket
        uri = f"ws://localhost:{config.server.port}"
        async with websockets.connect(uri) as ws:
            # 接收连接响应
            response = await ws.recv()
            data = json.loads(response)
            
            assert data["ok"] is True
        
        await gateway.stop()
```

---

## 端到端测试

### 1. 完整流程测试

```python
import pytest
import asyncio
import websockets
import json


class TestWebSocketFlow:
    """WebSocket 完整流程测试"""
    
    @pytest.mark.asyncio
    async def test_invoke_flow(self):
        """测试完整的调用流程"""
        # 1. 启动 Gateway（作为 subprocess 或 fixture）
        
        # 2. 连接
        uri = "ws://localhost:18789"
        async with websockets.connect(uri) as ws:
            # 3. 接收 hello
            hello = await ws.recv()
            assert json.loads(hello)["ok"] is True
            
            # 4. 发送健康检查
            await ws.send(json.dumps({
                "type": "req",
                "id": "test-001",
                "method": "health",
                "params": {}
            }))
            
            # 5. 接收响应
            response = await ws.recv()
            data = json.loads(response)
            
            assert data["ok"] is True
            assert data["payload"]["status"] == "healthy"
```

---

## 测试工具

### WebSocket 测试客户端

```python
class WebSocketTestClient:
    """WebSocket 测试客户端"""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.ws = None
    
    async def connect(self):
        """连接"""
        self.ws = await websockets.connect(self.uri)
        return self
    
    async def receive(self):
        """接收消息"""
        data = await self.ws.recv()
        return json.loads(data)
    
    async def send(self, frame: dict):
        """发送消息"""
        await self.ws.send(json.dumps(frame))
    
    async def close(self):
        """关闭"""
        await self.ws.close()
    
    async def __aenter__(self):
        return await self.connect()
    
    async def __aexit__(self, *args):
        await self.close()
```

---

## 测试运行

### 运行所有测试

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/
```

### 运行指定模块

```bash
# 运行 protocol 测试
pytest tests/unit/test_protocol.py

# 运行 session 测试
pytest tests/unit/test_session.py

# 运行 router 测试
pytest tests/unit/test_router.py
```

### 代码覆盖率

```bash
# 运行测试并生成覆盖率报告
pytest tests/ --cov=src.gateway --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

---

## 预计工作量

| 模块 | 工作内容 | 预计时间 |
|------|---------|---------|
| 测试框架 | pytest 配置、fixtures | 0.25 天 |
| 单元测试 | protocol, session, client, router | 0.5 天 |
| Handler 测试 | agent, control handlers | 0.25 天 |
| 集成测试 | Channel, Gateway | 0.5 天 |
| 端到端测试 | 完整流程 | 0.5 天 |
| **合计** | | **2 天** |

---

## 验收标准

### 测试覆盖

- [ ] protocol.py: 100% 覆盖
- [ ] session.py: 100% 覆盖
- [ ] client.py: 80%+ 覆盖
- [ ] router.py: 80%+ 覆盖
- [ ] handlers/: 80%+ 覆盖

### 测试质量

- [ ] 所有测试通过
- [ ] 测试命名清晰
- [ ] 包含 docstring
- [ ] 使用适当的 fixtures

### CI/CD

- [ ] 测试可在 CI 环境运行
- [ ] 覆盖率报告生成
- [ ] 集成到 GitHub Actions（可选）

---

## 附录: pytest 配置

### conftest.py

```python
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_service():
    """Mock Service"""
    service = AsyncMock()
    service.run = AsyncMock(return_value="Mock response")
    service.stream_run = AsyncMock(return_value="Mock response")
    return service
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
asyncio_mode = "auto"

[tool.coverage.run]
source = ["src/gateway"]
omit = ["tests/*", "*/conftest.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
*所属阶段: Phase 7*
