# Gateway 实施计划总览

本文档是 Gateway 层实施计划的总览索引。

## 阶段划分

| 阶段 | 文件 | 内容 | 预计工作量 |
|------|------|------|-----------|
| **Phase 1** | `phase-1-gateway-core.md` | Gateway 核心模块（protocol, session, client, router） | 1.5 天 |
| **Phase 2** | `phase-2-protocol-handlers.md` | 协议与 Handler（handlers, server） | 1.5 天 |
| **Phase 3** | `phase-3-channel-adapter.md` | Channel 适配器（base, ws, registry） | 1.5 天 |
| **Phase 4** | `phase-4-feishu-adapter.md` | 飞书适配器 | 1 天 |
| **Phase 5** | `phase-5-dingtalk-adapter.md` | 钉钉适配器 | 1 天 |
| **Phase 6** | `phase-6-config-entry.md` | 配置与入口 | 1 天 |
| **Phase 7** | `phase-7-testing.md` | 测试策略 | 2 天 |

**总预计工作量: 9.5 天**

---

## 阶段依赖关系

```
Phase 1 (核心)
    │
    ├──► Phase 2 (Handler)
    │        │
    │        └──► Phase 3 (Channel)
    │                 │
    │                 ├──► Phase 4 (飞书)
    │                 │
    │                 └──► Phase 5 (钉钉)
    │
    └────────────────────────────► Phase 6 (配置+入口)
                                         │
                                         ▼
                                    Phase 7 (测试)
```

---

## 各阶段交付物

### Phase 1: Gateway 核心模块

- `src/gateway/protocol.py` - 消息帧定义
- `src/gateway/session.py` - 会话管理
- `src/gateway/client.py` - 客户端抽象
- `src/gateway/router.py` - 消息路由

### Phase 2: 协议与 Handler

- `src/gateway/handlers/agent.py` - Agent 调用处理
- `src/gateway/handlers/control.py` - 控制指令处理
- `src/gateway/server.py` - WebSocket 服务器

### Phase 3: Channel 适配器

- `src/gateway/channels/base.py` - Channel 基类
- `src/gateway/channels/ws.py` - WebSocket 通道
- `src/gateway/channels/__init__.py` - Channel 注册表

### Phase 4: 飞书适配器

- `src/gateway/channels/feishu.py` - 飞书通道

### Phase 5: 钉钉适配器

- `src/gateway/channels/dingtalk.py` - 钉钉通道

### Phase 6: 配置与入口

- `config/gateway_config.yaml` - Gateway 配置
- `src/gateway/config.py` - 配置加载
- `src/gateway/__main__.py` - 启动入口
- `src/gateway/__init__.py` - 模块导出

### Phase 7: 测试策略

- `tests/unit/` - 单元测试
- `tests/integration/` - 集成测试
- `tests/e2e/` - 端到端测试

---

## 快速开始

### 按顺序实施

1. **Phase 1-2**: 核心功能（3 天）
2. **Phase 3-5**: 终端适配器（3.5 天）
3. **Phase 6**: 配置集成（1 天）
4. **Phase 7**: 测试完善（2 天）

### 并行实施建议

可以并行实施以下阶段：

- Phase 4 (飞书) 和 Phase 5 (钉钉) 可以并行
- Phase 6 可以在 Phase 3 后开始

---

## 相关文档

- [Gateway 架构设计](../gateway-design.md) - 完整架构文档
- [架构设计](../architecture.md) - 项目整体架构

---

*文档版本: 1.0*
*创建时间: 2026-03-11*
