# DeepAgents 集成问题记录

## 问题描述

**症状**: 通过 Agent 调用 LLM 时返回 401 认证错误，但直接调用 LLM 正常工作。

```
# 直接调用 - 成功 ✓
llm.invoke('你好')  # 返回正确响应

# 通过 Agent 调用 - 失败 ✗
agent.ainvoke({'messages': [('user', '你好')]})  # 401 invalid x-api-key
```

## 环境配置

- **模型**: minimax/MiniMax-M2.5
- **API 端点**: https://api.minimaxi.com/anthropic/
- **Provider**: MiniMax (Anthropic 兼容 API)

## 根本原因

**deepagents SDK 没有正确传递 LLM 实例的配置**

当传入 `BaseChatModel` 实例给 `create_deep_agent` 时：
1. deepagents 内部的中间件（如 FilesystemMiddleware、SubAgentMiddleware、SummarizationMiddleware）可能会重新创建 LLM
2. 重新创建的 LLM 使用了默认的 Anthropic 端点和认证
3. 导致使用错误的 API Key 访问 MiniMax 端点

## 临时解决方案

修改 `src/app/service.py`，直接使用 LLM 而非通过 Agent：

```python
async def run(self, input_data: Any, timeout: float | None = None) -> Any:
    if not self._running:
        raise RuntimeError("服务未运行，请先调用 start()")
    
    timeout = timeout or self._timeout
    
    try:
        async with asyncio.timeout(timeout):
            # 直接使用 LLM 处理（绕过 deepagents）
            if isinstance(input_data, str):
                result = await self._llm.ainvoke([HumanMessage(content=input_data)])
                if hasattr(result, 'content'):
                    return result.content
                return str(result)
            
            # 如果是 dict 格式，使用 agent
            result = await self._agent.ainvoke(input_data)
            return result
    except Exception as e:
        print(f"LLM 处理错误: {e}")
        raise
```

## 建议的完整解决方案

### 方案 1: 使用 ChatOpenAI 替代 ChatAnthropic

MiniMax 提供的是 OpenAI 兼容 API，应该使用 `ChatOpenAI`:

```python
# src/llms/providers/minimax.py
from langchain_openai import ChatOpenAI

class MiniMaxProvider(LLMProvider):
    def create(self, **kwargs) -> BaseChatModel:
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            # ... 其他参数
        )
```

### 方案 2: 在 deepagents 初始化时传递正确配置

使用 LangChain 的 `init_chat_model`:

```python
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

model = init_chat_model(
    model="openai:minimax/MiniMax-M2.5",
    model_provider="openai",
    base_url="https://api.minimaxi.com/anthropic/",
    api_key=os.environ.get("MINIMAX_API_KEY"),
)

agent = create_deep_agent(model=model)
```

## 相关文件

- `src/app/service.py` - 服务生命周期管理
- `src/llms/providers/minimax.py` - MiniMax Provider 实现
- `src/agents/agent_factory.py` - Agent 工厂
- `config/llm_config.yaml` - LLM 配置

## 状态

- [x] 临时解决方案: 直接调用 LLM
- [ ] 完整解决方案: 修复 deepagents 集成

## 创建时间

2026-03-08

## 问题根因分析

经过代码审查，发现问题出在 `src/agents/agent_factory.py` 的 `_create_agent_instance` 方法中。

### 问题定位

**文件**: `src/agents/agent_factory.py` (第 165-199 行)

```python
def _create_agent_instance(self, config: AgentConfig) -> AgentType:
    # 第 166 行: 正确解析了 LLM 实例 ✓
    llm = self._resolve_llm(config.llm)
    
    create_kwargs: Dict[str, Any] = {}
    
    # 第 172-175 行: 只传了 model 字符串
    if config.model:
        create_kwargs['model'] = config.model
    elif isinstance(config.llm, str):  # 当 llm 是 BaseChatModel 实例时不执行
        create_kwargs['model'] = config.llm
    
    # ❌ 关键问题: resolved_llm 从未被添加到 create_kwargs!
    # 缺失: create_kwargs['llm'] = llm
    
    # 第 177-193 行: 其他参数
    if config.system_prompt:
        create_kwargs['system_prompt'] = config.system_prompt
    # ... backend, middleware, tools
    
    # 第 199 行: 创建 Agent - 没有传递 LLM 实例!
    agent = create_deep_agent(**create_kwargs)
```

### 问题本质

当 `service.py` 传入 `BaseChatModel` 实例时:
1. `config.llm` 包含完整的 `ChatAnthropic` 实例（含正确的 `api_key`, `base_url`）
2. `self._resolve_llm()` 正确解析出该实例
3. **但 `create_deep_agent()` 从未收到这个 LLM 实例**
4. deepagents 内部中间件（FilesystemMiddleware、SubAgentMiddleware 等）会重新创建 LLM
5. 新建的 LLM 使用 SDK 默认配置（Anthropic 官方端点 + 默认 API Key）
6. 导致使用错误的端点和认证访问 MiniMax API → 401 错误

### 为什么直接调用 LLM 正常

`service.py` 的 `run()` 方法在处理字符串输入时绕过 Agent，直接调用 `self._llm.ainvoke()`，因此使用了正确配置的 LLM 实例。

## 修改方案

### 方案 A: 修复 AgentFactory 传递 LLM 实例（推荐）

修改 `src/agents/agent_factory.py`，确保 resolved LLM 实例被正确传递给 deepagents:

```python
def _create_agent_instance(self, config: AgentConfig) -> AgentType:
    # ... 解析 LLM
    llm = self._resolve_llm(config.llm)
    
    create_kwargs: Dict[str, Any] = {}
    
    # 修复: 传递 LLM 实例
    if isinstance(llm, BaseChatModel):
        create_kwargs['model'] = llm  # 传递 LLM 实例而非字符串
    elif config.model:
        create_kwargs['model'] = config.model
    elif isinstance(config.llm, str):
        create_kwargs['model'] = config.llm
    
    # ... 其他参数
    agent = create_deep_agent(**create_kwargs)
```

### 方案 B: 使用 init_chat_model 工厂函数

使用 LangChain 的 `init_chat_model` 创建符合 deepagents 期望的 LLM:

```python
from langchain.chat_models import init_chat_model

# 在 service.py 或 AgentFactory 中
self._llm = init_chat_model(
    model="openai:minimax/MiniMax-M2.5",
    model_provider="openai",
    base_url="https://api.minimaxi.com/anthropic/",
    api_key=os.environ.get("MINIMAX_API_KEY"),
)
```

### 方案 C: 切换到 ChatOpenAI

将 `MiniMaxProvider` 改为使用 `ChatOpenAI` 替代 `ChatAnthropic`:

```python
# src/llms/providers/minimax.py
from langchain_openai import ChatOpenAI

class MiniMaxProvider(LLMProvider):
    def create(self, **kwargs) -> BaseChatModel:
        return ChatOpenAI(
            model=kwargs.get("model", self._model),
            api_key=self._api_key,
            base_url=kwargs.get("base_url", self._base_url),
            temperature=kwargs.get("temperature", self._temperature),
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
            timeout=kwargs.get("timeout", self._timeout),
        )
```

## 修改优先级

1. **优先级 1 (推荐)**: 方案 A - 修复 AgentFactory 的 LLM 传递
   - 改动最小，影响范围可控
   - 保持现有 `ChatAnthropic` 实现

2. **优先级 2**: 方案 B - 使用 `init_chat_model`
   - 依赖 LangChain 内部实现
   - 可能存在版本兼容性问题

3. **优先级 3**: 方案 C - 切换到 ChatOpenAI
   - 需要测试 MiniMax 的 OpenAI 兼容程度
   - 可能需要调整 API 行为

## 验证步骤

修复后应验证:
1. `agent.ainvoke({'messages': [('user', '你好')]})` 返回正常响应
2. 中间件触发的子 Agent 也能正确调用 MiniMax API
3. 多次调用保持认证有效

## 状态更新

- [x] 临时解决方案: 直接调用 LLM
- [ ] 完整解决方案: 修复 deepagents 集成
- [ ] 方案 A: 修复 AgentFactory LLM 传递（推荐）
- [ ] 方案 B: 使用 init_chat_model
- [ ] 方案 C: 切换到 ChatOpenAI

---

**分析完成时间**: 2026-03-09
---

## 确认结果

**经过 deepagents 官方文档验证，原假设需要修正：**

### 官方文档关键信息

根据 `deepagents` 官方 API 文档 (`reference.langchain.com`):

```python
# resolve_model 函数签名
resolve_model(model: str | BaseChatModel) -> BaseChatModel
```

**核心行为**：
- 如果 `model` 已经是 `BaseChatModel` 实例 → **直接返回，不做任何修改**
- 如果 `model` 是字符串 → 使用 `init_chat_model` 解析（使用默认配置）

### 结论

**deepagents SDK 本身完全支持传入 `BaseChatModel` 实例**，会正确保留所有配置（api_key, base_url 等）。

**真正的问题是 `agent_factory.py` 的代码 bug**：

```python
# 当前代码 (第 172-175 行)
if config.model:
    create_kwargs['model'] = config.model  # 只传了字符串
elif isinstance(config.llm, str):
    create_kwargs['model'] = config.llm

# ❌ 缺失: resolved_llm 从未被传递
# 应该是:
# create_kwargs['model'] = llm  # 传递完整的 LLM 实例
```

### 修正后的理解

| 假设 | 实际情况 |
|------|----------|
| 中间件会重新创建 LLM | **错误** - SDK 正确处理 BaseChatModel 实例 |
| 需要使用 init_chat_model | **不一定** - 直接传 BaseChatModel 也可以 |
| 问题出在 deepagents 内部 | **正确** - 问题在于我们没有传 LLM 实例给 deepagents |

### 修复方案修正

根本不需要修改 deepagents 的使用方式，只需要修复 `agent_factory.py` 传递完整的 LLM 实例：

```python
# 修复后的代码
llm = self._resolve_llm(config.llm)
create_kwargs: Dict[str, Any] = {}

# ✅ 正确传递 LLM 实例
if isinstance(llm, BaseChatModel):
    create_kwargs['model'] = llm  # 传递完整实例
elif config.model:
    create_kwargs['model'] = config.model
elif isinstance(config.llm, str):
    create_kwargs['model'] = config.llm

agent = create_deep_agent(**create_kwargs)
```

---

**确认完成时间**: 2026-03-09
---

## 修复实施

**修复时间**: 2026-03-09

### 已实施修复

修改 `src/agents/agent_factory.py` 第 171-177 行：

```python
# 设置模型 - 优先使用 resolved LLM 实例
if isinstance(llm, BaseChatModel):
    create_kwargs['model'] = llm  # 传递完整的 LLM 实例
elif config.model:
    create_kwargs['model'] = config.model
elif isinstance(config.llm, str):
    create_kwargs['model'] = config.llm
```

### 修复效果

- 当传入 `BaseChatModel` 实例时，现在会正确传递给 `create_deep_agent`
- deepagents SDK 的 `resolve_model` 函数会正确处理并保留所有配置（api_key, base_url 等）
- 不再需要绕过 Agent 直接调用 LLM

### 状态

- [x] 临时解决方案: 直接调用 LLM
- [x] 完整解决方案: 修复 deepagents 集成
- [x] 方案 A: 修复 AgentFactory LLM 传递 - **已实施并验证**