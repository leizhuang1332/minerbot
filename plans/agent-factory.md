# Agent 创建服务实现计划

## 目标

基于 `tests/test_deepagents.py` 的测试结果，在 `src/agents` 目录下实现一个完整的 Agent 创建服务。

## 需求分析

1. **支持灵活的LLM传入**: 可以传入任意 LangChain 兼容的 LLM 实例
2. **支持灵活的系统提示词**: 可以自定义系统提示词
3. **全局单例模式**: 相同配置(llm + system_prompt)下只返回一个Agent实例

## 实现计划

### 阶段1: 模块结构设计

```
src/agents/
├── __init__.py           # 导出公共接口
├── agent_factory.py      # Agent工厂类 (核心)
└── config.py             # Agent配置
```

### 阶段2: 核心实现

#### 2.1 AgentConfig 数据类
- 定义 Agent 配置结构
- 包含: llm, system_prompt, backend, tools, middleware 等
- 支持配置哈希（用于单例判定）

#### 2.2 AgentFactory (工厂类 + 全局单例)
- 维护全局实例缓存: `Dict[config_hash, agent]`
- `create_agent(config: AgentConfig) -> CompiledStateGraph` - 总是创建新实例
- `get_agent(config: AgentConfig) -> CompiledStateGraph` - 全局单例获取
- `get_or_create(config: AgentConfig) -> CompiledStateGraph` - 相同配置返回缓存
- 支持自定义 backend, middleware, tools
- 提供 `clear_cache()` 方法清除所有缓存

#### 2.3 便捷函数
- `create_agent(llm, system_prompt, ...)` - 直接创建
- `get_agent(llm, system_prompt, ...)` - 全局单例获取

### 阶段3: 与现有模块集成

- 集成 `src.llms` 模块，支持直接传入 provider 名称
- 支持 `src.backends` 配置

### 阶段4: 测试验证

- 扩展 `tests/test_deepagents.py` 添加实际调用测试

## 关键API设计

```python
# 方式1: 直接创建 (每次创建新实例)
from src.agents import create_agent
agent = create_agent(
    llm=get_llm(),  # 或 "minimax" 字符串
    system_prompt="你是一个助手"
)

# 方式2: 全局单例 (相同配置返回同一实例)
from src.agents import get_agent
agent1 = get_agent(llm="minimax", system_prompt="你是一个助手")
agent2 = get_agent(llm="minimax", system_prompt="你是一个助手")
# agent1 is agent2  # True

# 方式3: 配置对象
from src.agents import AgentConfig, AgentFactory
config = AgentConfig(llm=get_llm(), system_prompt="...")
factory = AgentFactory()
agent = factory.get_agent(config)
```

## 单例判定规则

两个配置被认为是"相同"当且仅当:
- `llm` 模型名称相同 (通过 `model` 属性或绑定参数)
- `system_prompt` 完全相同
- `backend` 类型和根目录相同 (可选)
- `tools` 列表相同 (可选)

## 验收标准

- [ ] AgentConfig 支持 llm (BaseChatModel | str | None)
- [ ] AgentConfig 支持 system_prompt (str)
- [ ] 全局单例正常工作 (相同配置返回同一实例)
- [ ] 单元测试通过
- [ ] 与 src.llms 模块集成正常
