# 短期记忆功能开发计划

## TL;DR

> **快速摘要**: 为 MinerBot 添加短期记忆功能，通过 LangGraph CheckpointSaver 实现对话历史自动持久化
> 
> **交付物**: 
> - 修改后的 AgentConfig/AgentFactory/Service 层
> - 新增 Session 管理模块
> - 配置文件更新
> 
> **预计工作量**: 2-3 小时
> **并行执行**: YES - 3 waves
> **关键路径**: 修改 AgentConfig → 修改 AgentFactory → 修改 Service 层

---

## Context

### 原始需求
为当前项目的 Agent 助手添加短期记忆功能，使 Agent 能够记住当前会话的对话历史。

### 设计文档
`docs/short-term-memory-design.md` - 短期记忆实现方案

### 核心思路
- 使用 LangGraph CheckpointSaver 作为对话历史持久化组件
- 通过 config 参数传递 thread_id 来区分不同会话
- DeepAgents 原生支持 checkpointer 参数

---

## Work Objectives

### 核心目标
让 Agent 能够记住同一会话（thread_id）内的对话历史，实现多轮对话。

### 具体交付物
- [ ] `src/agents/config.py` - 添加 checkpointer/store 字段
- [ ] `src/agents/agent_factory.py` - 传递 checkpointer/store 到 create_deep_agent
- [ ] `src/memory/session.py` - 新增 Session 管理模块
- [ ] `src/app/service.py` - 集成 session_id 提取和 config 参数传递
- [ ] `config/agent_config.yaml` - 添加记忆配置
- [ ] 测试用例验证

### 定义完成
- [ ] 同一 thread_id 的多次对话能够记住之前的消息
- [ ] 不同 thread_id 的对话相互隔离
- [ ] 流式调用同样支持历史

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: YES - Tests after implementation
- **Framework**: pytest

### QA Policy
Every task MUST include agent-executed QA scenarios.

**验证场景**:

```
Scenario: 短期记忆正常工作
  Tool: Bash (uv run pytest)
  Preconditions: checkpointer 已配置
  Steps:
    1. 调用 agent.ainvoke("你好", config={thread_id: "test_001"})
    2. 调用 agent.ainvoke("你还记得我刚才说什么吗？", config={thread_id: "test_001"})
  Expected Result: Agent 能回答出 "你好"
  Evidence: test output

Scenario: 不同会话隔离
  Tool: Bash
  Preconditions: 两个不同 thread_id
  Steps:
    1. session_1 说 "我叫张三"
    2. session_2 问 "你还记得我叫什么吗？"
  Expected Result: session_2 回答不知道（因为历史已隔离）
  Evidence: test output
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (基础修改 - 可并行):
├── T1: 修改 AgentConfig 添加 checkpointer/store 字段 [quick]
├── T2: 修改 AgentFactory 传递 checkpointer 到 create_deep_agent [quick]
└── T3: 创建 Session 管理模块 [quick]

Wave 2 (核心集成):
├── T4: 修改 Service 层集成 session_id 和 config 参数 [deep]
└── T5: 更新配置文件 [quick]

Wave 3 (验证):
├── T6: 编写测试用例验证功能 [deep]
└── T7: 运行测试确认功能正常 [quick]
```

### Dependency Matrix

- **T1**: — — T4
- **T2**: T1 — T4
- **T3**: — — T4
- **T4**: T1, T2, T3 — T6
- **T5**: — — T6
- **T6**: T4, T5 — T7
- **T7**: T6 — —

---

## TODOs

---

- [x] 1. 修改 AgentConfig 添加 checkpointer/store 字段

  **What to do**:
  - 在 `src/agents/config.py` 的 AgentConfig 类中添加:
    - `checkpointer: Optional["Checkpointer"] = None`
    - `store: Optional["BaseStore"] = None`
  - 添加 TYPE_CHECKING 导入
  - 更新 `to_hash()` 方法包含新字段（可选）
  - 更新 `to_dict()` 和 `from_dict()` 方法

  **Must NOT do**:
  - 不要修改现有的字段默认值
  - 不要破坏现有的序列化逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 修改简单，不涉及复杂逻辑
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - ultrabrain: 不需要复杂推理

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2, T3)
  - **Blocks**: T4
  - **Blocked By**: None

  **References**:
  - `src/agents/config.py:1-80` - 现有 AgentConfig 定义
  - `docs/short-term-memory-design.md:206-224` - 设计文档中的修改方案

  **Acceptance Criteria**:
  - [ ] AgentConfig 包含 checkpointer 字段
  - [ ] AgentConfig 包含 store 字段
  - [ ] 代码无语法错误

  **QA Scenarios**:

  ```
  Scenario: AgentConfig 新字段可正常赋值
    Tool: Bash
    Preconditions: 修改后的代码
    Steps:
      1. uv run python -c "from src.agents.config import AgentConfig; c = AgentConfig(checkpointer='test'); print(c.checkpointer)"
    Expected Result: 输出 'test'
    Evidence: command output

  Scenario: 序列化/反序列化正常
    Tool: Bash
    Preconditions: 修改后的代码
    Steps:
      1. uv run python -c "from src.agents.config import AgentConfig; c = AgentConfig(); d = c.to_dict(); print('checkpointer' in d)"
    Expected Result: True
    Evidence: command output
  ```

  **Commit**: YES (group with T2, T3)
  - Message: `feat(agent): add checkpointer and store fields to AgentConfig`
  - Files: `src/agents/config.py`

---

- [x] 2. 修改 AgentFactory 传递 checkpointer/store

  **What to do**:
  - 在 `src/agents/agent_factory.py` 的 `_create_agent_instance` 方法中:
    - 添加 checkpointer 参数传递: `if config.checkpointer: create_kwargs['checkpointer'] = config.checkpointer`
    - 添加 store 参数传递: `if config.store: create_kwargs['store'] = config.store`
  - 确保参数正确传递给 `create_deep_agent()`

  **Must NOT do**:
  - 不要修改现有的参数传递逻辑
  - 不要破坏现有的错误处理

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 修改简单，直接添加参数传递
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - ultrabrain: 不需要复杂推理

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T3)
  - **Blocks**: T4
  - **Blocked By**: T1 (依赖 checkpointer 字段定义)

  **References**:
  - `src/agents/agent_factory.py:146-207` - 现有 _create_agent_instance 实现
  - `docs/short-term-memory-design.md:226-245` - 设计文档中的修改方案

  **Acceptance Criteria**:
  - [ ] checkpointer 参数正确传递
  - [ ] store 参数正确传递
  - [ ] 无参数传递错误

  **QA Scenarios**:

  ```
  Scenario: AgentFactory 能正确传递 checkpointer
    Tool: Bash
    Preconditions: T1 已完成
    Steps:
      1. uv run python -c "from src.agents.agent_factory import AgentFactory; print('OK')"
    Expected Result: 无导入错误
    Evidence: command output
  ```

  **Commit**: YES (group with T1, T3)
  - Message: `feat(agent): pass checkpointer and store to create_deep_agent`
  - Files: `src/agents/agent_factory.py`

---

- [x] 3. 创建 Session 管理模块

  **What to do**:
  - 创建 `src/memory/session.py`:
    - 定义 `Session` 数据类 (id, client_id, created_at, last_active, metadata)
    - 定义 `SessionManager` 类:
      - `create_session(client_id, metadata)` - 创建新会话
      - `get_session(session_id)` - 获取会话
      - `get_or_create_session(client_id)` - 获取或创建会话
      - `update_activity(session_id)` - 更新活跃时间
      - `delete_session(session_id)` - 删除会话
  - 更新 `src/memory/__init__.py` 导出 SessionManager
  - 更新 `src/agents/__init__.py` 导出 SessionManager

  **Must NOT do**:
  - 不要引入额外依赖
  - 不要创建持久化存储（先用内存实现）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的数据类和内存管理
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - ultrabrain: 不需要复杂推理

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T1, T2)
  - **Blocks**: T4
  - **Blocked By**: None

  **References**:
  - `src/memory/__init__.py` - 当前空模块
  - `docs/short-term-memory-design.md:311-358` - Session 管理方案

  **Acceptance Criteria**:
  - [ ] SessionManager 可正常创建会话
  - [ ] 可根据 client_id 获取或创建会话
  - [ ] 模块可正常导入

  **QA Scenarios**:

  ```
  Scenario: SessionManager 基本功能
    Tool: Bash
    Preconditions: T3 已完成
    Steps:
      1. uv run python -c "from src.memory.session import SessionManager, Session; sm = SessionManager(); s = sm.create_session('test_client'); print(s.id)"
    Expected Result: 输出 session id
    Evidence: command output

  Scenario: get_or_create_session 功能
    Tool: Bash
    Preconditions: T3 已完成
    Steps:
      1. uv run python -c "from src.memory.session import SessionManager; sm = SessionManager(); s1 = sm.get_or_create_session('client_001'); s2 = sm.get_or_create_session('client_001'); print(s1.id == s2.id)"
    Expected Result: True (同一个 client_id 返回同一会话)
    Evidence: command output
  ```

  **Commit**: YES (group with T1, T2)
  - Message: `feat(memory): add SessionManager for session lifecycle`
  - Files: `src/memory/session.py`, `src/memory/__init__.py`

---

- [x] 4. 修改 Service 层集成 session_id 和 config 参数

  **What to do**:
  - 在 `src/app/service.py`:
    - 导入 SessionManager
    - 在 `__init__` 中初始化 SessionManager 和 MemorySaver
    - 在 `start()` 中创建 Agent 时传入 checkpointer
    - 修改 `run()` 方法:
      - 提取 session_id (从 input_data 或生成新的)
      - 构建 config 参数: `config = {"configurable": {"thread_id": session_id}}`
      - 传递 config 到 ainvoke
    - 修改 `stream_run()` 方法同样传递 config
    - 添加 `_get_or_create_session_id()` 私有方法

  **Must NOT do**:
  - 不要破坏现有的同步/异步逻辑
  - 不要修改现有的错误处理

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 涉及多个方法修改，需要理解现有逻辑
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - playwright: 不涉及 UI

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: T6
  - **Blocked By**: T1, T2, T3

  **References**:
  - `src/app/service.py:167-213` - 现有 run() 方法
  - `src/app/service.py:215-275` - 现有 stream_run() 方法
  - `docs/short-term-memory-design.md:247-307` - 设计文档中的修改方案

  **Acceptance Criteria**:
  - [ ] Service 初始化时创建 checkpointer
  - [ ] run() 方法传递 config 参数
  - [ ] stream_run() 方法传递 config 参数
  - [ ] 能从 input_data 提取 session_id

  **QA Scenarios**:

  ```
  Scenario: Service 初始化 checkpointer
    Tool: Bash
    Preconditions: T4 已完成
    Steps:
      1. uv run python -c "from src.app.service import Service; print('OK')"
    Expected Result: 无导入错误
    Evidence: command output

  Scenario: run 方法接受 config
    Tool: Bash
    Preconditions: T4 已完成，代码可运行
    Steps:
      1. 检查 run 方法签名是否包含 config 参数处理
    Expected Result: 方法能处理 config
    Evidence: code inspection
  ```

  **Commit**: YES (group with T5)
  - Message: `feat(service): integrate session management and config for short-term memory`
  - Files: `src/app/service.py`

---

- [x] 5. 更新配置文件

  **What to do**:
  - 在 `config/agent_config.yaml` 中添加记忆配置:
    ```yaml
    agent:
      # 现有配置...
      
      # 记忆配置
      memory:
        checkpointer:
          enabled: true
          type: memory  # memory / sqlite
        store:
          enabled: false  # 短期记忆不需要
    ```

  **Must NOT do**:
  - 不要删除现有配置
  - 不要破坏 YAML 格式

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 简单的配置添加
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with T4)
  - **Blocks**: T6
  - **Blocked By**: None

  **References**:
  - `config/agent_config.yaml` - 现有配置文件
  - `docs/short-term-memory-design.md:347-365` - 配置方案

  **Acceptance Criteria**:
  - [ ] 配置文件格式正确
  - [ ] 可被正常读取

  **QA Scenarios**:

  ```
  Scenario: 配置文件可正常解析
    Tool: Bash
    Preconditions: T5 已完成
    Steps:
      1. uv run python -c "from src.app.config import Config; c = Config.load(); print(c.agent_config.get('memory'))"
    Expected Result: 输出配置内容（即使为 None）
    Evidence: command output
  ```

  **Commit**: YES (group with T4)
  - Message: `feat(config): add memory configuration`
  - Files: `config/agent_config.yaml`

---

- [x] 6. 编写测试用例验证功能

  **What to do**:
  - 创建 `tests/test_short_term_memory.py`:
    - 测试 AgentConfig 新字段
    - 测试 SessionManager 功能
    - 测试 Service 层集成（集成测试）
    - 测试不同 thread_id 隔离
    - 测试流式调用

  **Must NOT do**:
  - 不要测试 DeepAgents 内部实现
  - 不要创建需要外部服务的测试

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要理解集成逻辑
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: T7
  - **Blocked By**: T4, T5

  **References**:
  - `tests/test_factory.py` - 现有测试模式
  - `docs/short-term-memory-design.md:371-403` - 测试场景参考

  **Acceptance Criteria**:
  - [ ] 测试用例覆盖主要场景
  - [ ] 测试可通过

  **QA Scenarios**:

  ```
  Scenario: 运行测试套件
    Tool: Bash (uv run pytest tests/test_short_term_memory.py -v)
    Preconditions: T6 已完成
    Steps:
      1. uv run pytest tests/test_short_term_memory.py -v
    Expected Result: 测试通过或跳过（如果没有 DeepAgents）
    Evidence: pytest output
  ```

  **Commit**: YES (group with T7)
  - Message: `test(memory): add short-term memory tests`
  - Files: `tests/test_short_term_memory.py`

---

- [x] 7. 运行测试确认功能正常

  **What to do**:
  - 运行所有相关测试
  - 验证短期记忆功能正常
  - 检查是否有回归问题

  **Must NOT do**:
  - 不要修改测试代码来通过测试

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 运行测试验证
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: T6

  **References**:
  - `tests/` - 测试目录

  **Acceptance Criteria**:
  - [ ] 新测试通过或合理跳过
  - [ ] 现有测试无回归

  **QA Scenarios**:

  ```
  Scenario: 完整测试套件
    Tool: Bash (uv run pytest tests/ -v)
    Preconditions: T7 已完成
    Steps:
      1. uv run pytest tests/ -v --tb=short
    Expected Result: 无测试失败
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `test: run full test suite for memory feature`
  - Files: (none - just verification)

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  验证所有交付物符合设计文档
  Output: `Must Have [N/N] | VERDICT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  检查代码风格和潜在问题
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL]`

- [ ] F3. **Integration Test** — `deep`
  端到端验证短期记忆功能
  Output: `Feature [WORKING/NOT_WORKING]`

---

## Commit Strategy

- **Wave 1**: `feat(agents): add memory support - config and session manager`
  - Files: `src/agents/config.py`, `src/agents/agent_factory.py`, `src/memory/session.py`

- **Wave 2**: `feat(service): integrate short-term memory into Service layer`
  - Files: `src/app/service.py`, `config/agent_config.yaml`

- **Wave 3**: `test(memory): add tests for short-term memory feature`
  - Files: `tests/test_short_term_memory.py`

---

## Success Criteria

### Verification Commands
```bash
# 单元测试
uv run pytest tests/test_short_term_memory.py -v

# 完整测试
uv run pytest tests/ -v --tb=short
```

### Final Checklist
- [ ] 同一 thread_id 的对话能记住历史
- [ ] 不同 thread_id 的对话相互隔离
- [ ] 流式调用支持历史
- [ ] 代码无语法错误
- [ ] 测试通过或合理跳过
