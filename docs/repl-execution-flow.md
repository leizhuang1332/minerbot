# REPL 输入执行链路

## 整体流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户输入 "你好"                                  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. REPL (src/app/repl.py)                                                │
│    - input(">>> ") 读取用户输入                                            │
│    - 验证: 非空、非超长、非退出命令                                          │
│    - 调用 service.run(user_input)                                          │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Service.run() (src/app/service.py)                                     │
│                                                                             │
│    if isinstance(input_data, str):                                         │
│        input_data = {"messages": [("user", input_data)]}  ← 格式转换      │
│                                                                             │
│    result = await self._agent.ainvoke(input_data)                         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Agent (src/agents/agent_factory.py)                                     │
│                                                                             │
│    get_agent() → AgentFactory.get_agent()                                  │
│    └── create_deep_agent() 来自 deepagents SDK                             │
│                                                                             │
│    agent.ainvoke({"messages": [("user", "你好")]})                        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. DeepAgents SDK (CompiledStateGraph)                                    │
│                                                                             │
│    ├── 接收 {"messages": [("user", "你好")]}                              │
│    ├── 构建 LangChain LCEL 链                                              │
│    ├── 调用 LLM (ChatAnthropic / MiniMax)                                 │
│    └── 返回结果                                                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. LLM (src/llms/factory.py)                                             │
│                                                                             │
│    get_llm() → LLMFactory.create()                                        │
│    └── provider.create() → ChatAnthropic / ChatMiniMax                    │
│                                                                             │
│    API 调用: anthropic.com / minimaxi.com                                 │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. 返回结果 → REPL → 打印输出                                              │
│                                                                             │
│    print(result)                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 详细代码路径

### Step 1: REPL 接收输入

**文件**: `src/app/repl.py`

```python
async def run(self) -> None:
    while self._running:
        user_input = input(">>> ")  # 读取 "你好"
        
        # 验证
        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("exit", "quit"):
            self._running = False
            continue
        if len(user_input) > self.MAX_INPUT_LENGTH:
            print(f"输入过长，最多支持 {self.MAX_INPUT_LENGTH} 个字符")
            continue
        
        # 调用 Service 处理
        result = await self._service.run(user_input)
        
        # 打印结果
        print(result)
```

### Step 2: Service 格式化输入

**文件**: `src/app/service.py`

```python
async def run(self, input_data: Any, timeout: float | None = None) -> Any:
    # 关键: 将字符串转换为 DeepAgents 期望的 dict 格式
    if isinstance(input_data, str):
        input_data = {"messages": [("user", input_data)]}
    
    # 调用 Agent
    result = await self._agent.ainvoke(input_data)
    return result
```

**输入转换**:
```
"你好"  →  {"messages": [("user", "你好")]}
```

### Step 3: Agent 处理

**文件**: `src/agents/agent_factory.py`

```python
def get_agent(self, config: AgentConfig) -> AgentType:
    # 使用 deepagents SDK 创建 Agent
    agent = create_deep_agent(
        llm=self._resolve_llm(config.llm),
        system_prompt=config.system_prompt,
        model=config.model,
        **config.extra
    )
    return agent
```

### Step 4: DeepAgents 执行

DeepAgents SDK 内部流程:
1. 接收 `{"messages": [("user", "你好")]}`
2. 构建 LangChain Expression Language (LCEL) 链
3. 通过 Middleware 链处理
4. 调用绑定的 LLM
5. 返回结果

### Step 5: LLM API 调用

**文件**: `src/llms/factory.py`

```python
def get_llm(provider: Optional[str] = None, **kwargs: Any) -> BaseChatModel:
    return LLMFactory.create(provider=provider, **kwargs)
```

根据配置调用:
- `minimax` → MiniMax API
- `anthropic` → Anthropic Claude API

---

## 关键数据转换

| 阶段 | 数据格式 |
|------|----------|
| 用户输入 | `"你好"` (str) |
| REPL → Service | `"你好"` (str) |
| Service 格式化 | `{"messages": [("user", "你好")]}` (dict) |
| Agent 处理 | `{"messages": [("user", "你好")]}` (dict) |
| LLM API | `{"messages": [HumanMessage("你好")]}` |

---

## 错误处理

```python
# Service.run() 中的异常处理
try:
    async with asyncio.timeout(timeout):
        result = await self._agent.ainvoke(input_data)
        return result
except asyncio.TimeoutError:
    print(f"请求处理超时（{timeout}秒）")
    raise
except Exception as e:
    print(f"Agent 处理错误: {e}")
    raise
```

---

## 时序图

```
用户          REPL           Service         Agent          LLM           API
 │              │               │               │              │              │
 │   "你好"     │               │               │              │              │
 │─────────────>│               │               │              │              │
 │              │  run("你好")  │               │              │              │
 │              │──────────────>│               │              │              │
 │              │               │ {"messages":  │              │              │
 │              │               │  [("user",    │              │              │
 │              │               │   "你好")]}   │              │              │
 │              │               │──────────────>│              │              │
 │              │               │               │ ainvoke()    │              │
 │              │               │               │─────────────>│              │
 │              │               │               │              │  HTTP Request│
 │              │               │               │              │─────────────>│
 │              │               │               │              │              │
 │              │               │               │              │  HTTP Response
 │              │               │               │              │<─────────────│
 │              │               │               │<─────────────│              │
 │              │               │<──────────────│              │              │
 │              │<──────────────│               │              │              │
 │   输出结果   │               │               │              │              │
 │<─────────────│               │               │              │              │
 │              │               │               │              │              │
```
