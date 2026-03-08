# Draft: 后台服务生命周期管理

## 需求概述
实现后端服务生命周期管理：启动 → 初始化组件 → 后台服务线程循环 → 停止

## 现有代码分析

### 项目结构
- `src/agents/` - Agent 工厂模块（AgentFactory, create_agent, get_agent）
- `src/llms/` - LLM 工厂模块（LLMFactory, get_llm）
- 依赖 `deepagents` SDK
- 配置通过 YAML 文件加载

### Agent 创建方式
```python
from src.agents import create_agent, get_agent
agent = create_agent(llm="minimax", system_prompt="你是一个助手")
```

### LLM 获取方式
```python
from src.llms import get_llm
llm = get_llm()  # 使用默认 provider
```

## 开放问题

### 1. 服务类型
- [ ] HTTP API (FastAPI/Flask)
- [ ] gRPC 服务
- [ ] 纯 Python 线程/进程服务（无网络协议）
- [ ] 其他

### 2. 请求接收方式
- [ ] HTTP REST API
- [ ] gRPC 远程调用
- [ ] 消息队列（RabbitMQ/Kafka）
- [ ] 本地队列（内存队列）

### 3. 请求处理模式
- [ ] 同步处理（收到请求 → 调用 agent → 返回结果）
- [ ] 异步处理（收到请求 → 放入队列 → 立即返回 → 后台处理）
- [ ] 流式处理（Server-Sent Events）

### 4. 并发需求
- [ ] 单线程（一次处理一个请求）
- [ ] 多线程（threading）
- [ ] 异步IO（asyncio）
- [ ] 多进程

### 5. 配置方式
- [ ] YAML 配置文件
- [ ] 环境变量
- [ ] 命令行参数
- [ ] 代码内配置

### 6. 日志需求
- [ ] 标准 logging 模块
- [ ] 结构化日志（JSON）
- [ ] 日志级别配置

### 7. 其他组件
除了 Agent 实例，还需要初始化哪些组件？
- [ ] LLM 实例
- [ ] Memory 存储
- [ ] Tools 工具
- [ ] Middleware 中间件

## 技术决策

### 基于分析的建议
1. **服务类型**: 建议使用 FastAPI 作为 HTTP 服务框架（Python 后端标准选择）
2. **请求处理**: 同步处理最简单，异步处理性能更好
3. **并发**: asyncio + FastAPI 原生支持高并发
4. **配置**: 扩展现有 YAML 配置方式
