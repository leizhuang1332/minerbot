# Phase 6: 配置与入口实施计划

## 项目背景

### 背景介绍

在前五个阶段中，我们实现了完整的 Gateway 系统：

- **Phase 1**: 核心骨架（protocol, session, client, router）
- **Phase 2**: 请求处理（handlers, server）
- **Phase 3**: Channel 适配器框架
- **Phase 4**: 飞书适配器
- **Phase 5**: 钉钉适配器

现在需要将所有组件整合到一起，提供统一的配置管理和启动入口。

### 本阶段目标

Phase 6 的目标是完成 Gateway 的最后拼图：

1. **GatewayConfig**: 配置加载与管理
2. **gateway_config.yaml**: 配置文件
3. **gateway/__main__.py**: 启动入口
4. **模块导出**: 统一导出接口

---

## 架构设计

### 配置架构

```
┌─────────────────────────────────────────────────────────────┐
│                   配置文件层                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │            gateway_config.yaml                        │  │
│  │  - server: WebSocket 配置                             │  │
│  │  - channels: 各 Channel 配置                          │  │
│  │  - session: 会话配置                                  │  │
│  │  - rate_limit: 速率限制                               │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   配置加载层                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │            GatewayConfig (单例)                      │  │
│  │  - 从 YAML 加载                                       │  │
│  │  - 环境变量覆盖                                        │  │
│  │  - 类型转换                                            │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   运行时                                      │
│  ┌─────────────────────────────────────────────────────┐  │
│  │            GatewayServer                              │  │
│  │  - 使用配置初始化                                      │  │
│  │  - 启动各组件                                          │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 文件结构

```
minerbot/
├── src/
│   ├── gateway/
│   │   ├── __init__.py          # ★ 模块导出
│   │   ├── config.py            # ★ GatewayConfig
│   │   ├── server.py            # (Phase 2)
│   │   ├── protocol.py          # (Phase 1)
│   │   ├── session.py           # (Phase 1)
│   │   ├── client.py            # (Phase 1)
│   │   ├── router.py            # (Phase 2)
│   │   ├── __main__.py          # ★ 启动入口
│   │   ├── channels/            # (Phase 3-5)
│   │   └── handlers/            # (Phase 2)
│   │
│   └── app/                     # (现有)
│
└── config/
    ├── app_config.yaml          # (现有)
    ├── llm_config.yaml          # (现有)
    ├── agent_config.yaml        # (现有)
    └── gateway_config.yaml     # ★ 本阶段
```

---

## 详细设计

### 1. 配置类设计 (config.py)

#### 1.1 配置结构

```python
class ServerConfig:
    """WebSocket 服务器配置"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.host: str = config.get("host", "0.0.0.0")
        self.port: int = config.get("port", 18789)
        self.ping_interval: float = config.get("ping_interval", 30)
        self.ping_timeout: float = config.get("ping_timeout", 10)
        self.max_message_size: int = config.get("max_message_size", 10 * 1024 * 1024)


class ChannelConfig:
    """Channel 配置"""
    
    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        self.enabled: bool = config.get("enabled", True)
        self.config: Dict[str, Any] = config.get("config", {})


class GatewayConfig:
    """Gateway 配置
    
    加载 gateway_config.yaml，支持环境变量覆盖。
    """
    
    _instance: Optional["GatewayConfig"] = None
    
    def __new__(cls, config_path: Optional[Path] = None) -> "GatewayConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance
```

#### 1.2 加载逻辑

```python
def _load_config(self, config_path: Optional[Path] = None) -> None:
    """加载配置"""
    import os
    
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "gateway_config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    
    # 解析服务配置
    self.server = ServerConfig(config.get("gateway", {}).get("server", {}))
    
    # 解析 Channel 配置
    self.channels: Dict[str, ChannelConfig] = {}
    channel_configs = config.get("gateway", {}).get("channels", {})
    for name, ch_config in channel_configs.items():
        self.channels[name] = ChannelConfig(name, ch_config)
    
    # 环境变量覆盖
    self._apply_env_overrides()
```

#### 1.3 环境变量覆盖

```python
def _apply_env_overrides(self) -> None:
    """应用环境变量覆盖"""
    import os
    
    # Gateway 服务配置
    if host := os.getenv("GATEWAY_HOST"):
        self.server.host = host
    if port := os.getenv("GATEWAY_PORT"):
        self.server.port = int(port)
    
    # 飞书配置
    if app_id := os.getenv("FEISHU_APP_ID"):
        if "feishu" in self.channels:
            self.channels["feishu"].config["app_id"] = app_id
    if app_secret := os.getenv("FEISHU_APP_SECRET"):
        if "feishu" in self.channels:
            self.channels["feishu"].config["app_secret"] = app_secret
    
    # 钉钉配置
    if app_key := os.getenv("DINGTALK_APP_KEY"):
        if "dingtalk" in self.channels:
            self.channels["dingtalk"].config["app_key"] = app_key
    if app_secret := os.getenv("DINGTALK_APP_SECRET"):
        if "dingtalk" in self.channels:
            self.channels["dingtalk"].config["app_secret"] = app_secret
```

---

### 2. 配置文件 (gateway_config.yaml)

```yaml
# MinerBot Gateway 配置

gateway:
  # WebSocket 服务器配置
  server:
    host: "0.0.0.0"
    port: 18789
    ping_interval: 30      # 心跳间隔（秒）
    ping_timeout: 10       # 心跳超时（秒）
    max_message_size: 10485760  # 10MB
  
  # Channel 配置
  channels:
    # WebSocket 通道（CLI/Web UI/TUI）
    ws:
      enabled: true
      config: {}
    
    # 飞书通道 (WebSocket 长连接)
    feishu:
      enabled: false
      config:
        app_id: "${FEISHU_APP_ID}"
        app_secret: "${FEISHU_APP_SECRET}"
        verification_token: "${FEISHU_VERIFICATION_TOKEN}"
    
    # 钉钉通道 (Stream 模式)
    dingtalk:
      enabled: false
      config:
        app_key: "${DINGTALK_APP_KEY}"
        app_secret: "${DINGTALK_APP_SECRET}"
  
  # 会话配置
  session:
    max_history: 100       # 最大历史消息数
    ttl_hours: 24          # 会话 TTL（小时）
    cleanup_interval: 60   # 清理间隔（秒）
  
  # 速率限制
  rate_limit:
    enabled: true
    requests_per_minute: 60  # 每分钟请求数限制
    burst: 10               # 突发限制
```

---

### 3. 入口文件 (__main__.py)

```python
"""Gateway 入口点

Usage:
    python -m src.gateway --config config/gateway_config.yaml
    python -m src.gateway --config config/gateway_config.yaml --with-service
"""

import argparse
import asyncio
import sys

from src.gateway.config import GatewayConfig
from src.gateway.server import GatewayServer


async def main() -> None:
    parser = argparse.ArgumentParser(description="MinerBot Gateway")
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Gateway 配置文件路径"
    )
    parser.add_argument(
        "--with-service",
        action="store_true",
        help="同时启动内置核心服务"
    )
    parser.add_argument(
        "--host",
        type=str,
        help="覆盖配置文件中的 host"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="覆盖配置文件中的 port"
    )    
    args = parser.parse_args()
    
    # 加载配置
    config = GatewayConfig.load(args.config)
    
    # 命令行覆盖
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    
    # 可选：启动内置 Service
    service = None
    if args.with_service:
        print("启动内置核心服务...")
        from src.app.config import Config
        from src.app.service import Service as AppService
        
        app_config = Config.load()
        service = AppService(app_config)
        await service.start()
        
        # 注入到 Handler
        from src.gateway.handlers.agent import AgentInvokeHandler
        AgentInvokeHandler.set_service(service)
    
    # 创建并启动 Gateway
    gateway = GatewayServer(config)
    
    try:
        await gateway.start()
        print(f"\n========== Gateway 已启动 ==========")
        print(f"WebSocket: ws://{config.server.host}:{config.server.port}")
        print(f"====================================\n")
        
        # 等待关闭
        await gateway.wait_for_shutdown()
        
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        # 停止 Gateway
        await gateway.stop()
        
        # 停止 Service
        if service:
            await service.stop()
    
    print("Gateway 已退出")


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4. 模块导出 (__init__.py)

```python
"""MinerBot Gateway

多终端接入网关，支持 WebSocket、飞书、钉钉等终端。
"""

from src.gateway.config import GatewayConfig
from src.gateway.server import GatewayServer
from src.gateway.protocol import MessageFrame, MessageType, ErrorCode
from src.gateway.session import Session, SessionManager
from src.gateway.client import Client
from src.gateway.router import MessageRouter

# 导出主要类
__all__ = [
    "GatewayConfig",
    "GatewayServer",
    "MessageFrame",
    "MessageType",
    "ErrorCode",
    "Session",
    "SessionManager",
    "Client",
    "MessageRouter",
]

# 版本信息
__version__ = "1.0.0"
```

---

## 实施步骤

### Step 1: 创建配置文件

1. 创建 `config/gateway_config.yaml`
2. 定义所有配置项
3. 添加配置说明注释

### Step 2: 实现配置加载

1. 创建 `src/gateway/config.py`
2. 实现 ServerConfig 类
3. 实现 ChannelConfig 类
4. 实现 GatewayConfig 类
5. 添加环境变量覆盖

### Step 3: 创建入口文件

1. 创建 `src/gateway/__main__.py`
2. 实现命令行参数解析
3. 实现 Service 集成
4. 实现生命周期管理

### Step 4: 模块导出

1. 创建 `src/gateway/__init__.py`
2. 导出主要类和函数
3. 添加版本信息

### Step 5: 集成测试

1. 测试配置加载
2. 测试命令行参数
3. 测试环境变量覆盖

---

## 验收标准

### 功能验收

- [ ] 配置文件正确加载
- [ ] 环境变量正确覆盖
- [ ] 命令行参数正确覆盖
- [ ] Service 正确注入
- [ ] 优雅关闭正常工作

### 配置验收

- [ ] Server 配置完整
- [ ] Channel 配置完整
- [ ] Session 配置完整
- [ ] Rate Limit 配置完整

### 代码质量

- [ ] 类型注解完整
- [ ] 单例模式正确实现
- [ ] 错误处理完善

---

## 使用方式

### 基本启动

```bash
# 使用默认配置
python -m src.gateway

# 指定配置文件
python -m src.gateway --config config/gateway_config.yaml
```

### 启动并加载核心服务

```bash
python -m src.gateway --with-service
```

### 覆盖配置

```bash
# 覆盖端口
python -m src.gateway --port 8080

# 覆盖主机
python -m src.gateway --host 127.0.0.1
```

### 环境变量

```bash
# 设置环境变量
export GATEWAY_PORT=8080
export FEISHU_APP_ID=cli_xxxxx
export FEISHU_APP_SECRET=xxxxx
export DINGTALK_APP_KEY=dingxxxxx
export DINGTALK_APP_SECRET=xxxxx

# 启动
python -m src.gateway --with-service
```

---

## 预计工作量

| 模块 | 工作内容 | 预计时间 |
|------|---------|---------|
| gateway_config.yaml | 配置文件 | 0.1 天 |
| config.py | 配置加载 | 0.25 天 |
| __main__.py | 启动入口 | 0.25 天 |
| __init__.py | 模块导出 | 0.1 天 |
| 集成测试 | 端到端测试 | 0.3 天 |
| **合计** | | **1 天** |

---

## 依赖关系

- **本阶段依赖**: Phase 1-5 (所有模块)
- **后续阶段依赖**: 测试 (Phase 7)

---

## 附录: 与现有代码集成

### 配置加载模式

遵循现有 `Config` 类的模式：

```python
# 现有模式 (src/app/config.py)
class Config:
    _instance: Optional["Config"] = None
    
    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# Gateway 模式 (src/gateway/config.py) - 兼容
class GatewayConfig:
    _instance: Optional["GatewayConfig"] = None
    
    def __new__(cls, config_path: Optional[Path] = None) -> "GatewayConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config(config_path)
        return cls._instance
```

### 日志输出

遵循项目现有模式（使用 `print`）：

```python
print(f"正在启动 Gateway ({self._host}:{self._port})...")
print(f"Gateway 启动成功 (ws://{self._host}:{self._port})")
print("Gateway 已停止")
```

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
*所属阶段: Phase 6*
