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
