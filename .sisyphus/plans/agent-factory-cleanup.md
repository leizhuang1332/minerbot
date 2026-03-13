# Agent Factory 清理计划

## TL;DR

> **快速摘要**: 清理 `src/agents/agent_factory.py` 中 4 个未使用的函数/方法，保留所有公共 API。
> 
> **交付物**: 清理后的 `agent_factory.py` 文件
> - 删除: `cache_size` 属性, `clear_cache`, `get_cached_agents`, `has_agent` 方法
> - 保留: 所有公共方法、异常类、内部方法
> 
> **预估工作量**: 最小 (Quick)
> **并行执行**: 否 (顺序执行)
> **关键路径**: 验证 → 删除 → 验证

---

## Context

### 原始请求
用户要求对 `src/agents/agent_factory.py` 文件进行全面分析，识别并清理所有未被实际调用的函数。

### 访谈摘要
**关键讨论**:
- 通过 grep 搜索整个代码库，验证无外部引用
- 确认 4 个方法未被导出到 `__init__.py`
- 测试文件 `test_factory.py` 实际测试的是 `src.llms` 模块

**研究发现**:
- `cache_size` 属性: 未在 `__init__.py` 导出，无外部调用
- `clear_cache` 方法: 未导出，无外部调用
- `get_cached_agents` 方法: 未导出，无外部调用
- `has_agent` 方法: 未导出，无外部调用

### Metis Review
**识别的间隙** (已解决):
- 添加具体的验收标准命令
- 设置明确的 scope guardrails 防止范围蔓延

---

## Work Objectives

### 核心目标
删除 `AgentFactory` 类中 4 个未使用的方法/属性，保持其他代码完全不变。

### 具体交付物
- `src/agents/agent_factory.py`: 删除 4 个未使用方法
  - Line 99-102: `cache_size` property
  - Line 382-403: `clear_cache` 方法
  - Line 405-411: `get_cached_agents` 方法
  - Line 413-422: `has_agent` 方法

### 完成定义
- [ ] 4 个方法已删除
- [ ] 代码无语法错误
- [ ] 导入测试通过

### 必须保留 (Guardrails)
- [ ] 异常类: `AgentFactoryError`, `LLMNotAvailableError`, `DeepAgentsNotAvailableError`
- [ ] 公共方法: `create_agent`, `get_agent`, `get_or_create`
- [ ] 内部方法: `_resolve_llm`, `_create_agent_instance`
- [ ] 类变量: `_instance`, `_global_cache`, `_initialized`
- [ ] 模块级函数: `get_factory`, `create_agent`, `get_agent`, `get_or_create_agent`
- [ ] `__init__.py` 导出不变

### 禁止操作 (Scope Lock)
- ❌ 不要删除任何其他方法或类变量
- ❌ 不要修改任何注释或格式化代码
- ❌ 不要添加新功能
- ❌ 不要修改 `__init__.py`

---

## Verification Strategy

### 测试决策
- **Infrastructure exists**: 是 (pytest)
- **Automated tests**: 无专门针对 AgentFactory 的测试
- **Framework**: pytest
- **Agent-Executed QA**: 手动命令验证

### QA Policy
Every task MUST include agent-executed QA scenarios (see TODO template below).
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

---

## Execution Strategy

### 执行流程 (单波次)

```
Task 1: 验证删除前状态
├── 1.1: 语法检查 (py_compile)
├── 1.2: 导入检查
└── 1.3: 验证方法存在

Task 2: 删除未使用方法
├── 2.1: 删除 cache_size property (lines 99-102)
├── 2.2: 删除 clear_cache 方法 (lines 382-403)
├── 2.3: 删除 get_cached_agents 方法 (lines 405-411)
└── 2.4: 删除 has_agent 方法 (lines 413-422)

Task 3: 验证删除后状态
├── 3.1: 语法检查
├── 3.2: 导入检查
├── 3.3: 公共方法可用性检查
└── 3.4: 已删除方法不可访问检查
```

### Agent Dispatch Summary
- **1**: **3** — T1.1 → `quick`, T1.2 → `quick`, T1.3 → `quick`
- **2**: **4** — T2.1 → `quick`, T2.2 → `quick`, T2.3 → `quick`, T2.4 → `quick`
- **3**: **4** — T3.1 → `quick`, T3.2 → `quick`, T3.3 → `quick`, T3.4 → `quick`

---

## TODOs

- [x] 1. 验证删除前状态

  **What to do**:
  - 运行语法检查: `uv run python -m py_compile src/agents/agent_factory.py`
  - 运行导入检查: `uv run python -c "from src.agents import AgentFactory; print('OK')"`
  - 验证方法存在: `uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('cache_size:', hasattr(f, 'cache_size')); print('clear_cache:', hasattr(f, 'clear_cache')); print('get_cached_agents:', hasattr(f, 'get_cached_agents')); print('has_agent:', hasattr(f, 'has_agent'))"`

  **Must NOT do**:
  - 不要修改任何代码

  **Recommended Agent Profile**:
  > - **Category**: `quick`
  >   - Reason: 验证任务，简单的命令执行
  > - **Skills**: []
  > - **Skills Evaluated but Omitted**:
  >   - N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES (3个子任务)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2
  - **Blocked By**: None

  **References**:
  - 文件路径: `src/agents/agent_factory.py`
  - 目标行号: 99-102 (cache_size), 382-403 (clear_cache), 405-411 (get_cached_agents), 413-422 (has_agent)

  **Acceptance Criteria**:
  - [ ] 语法检查无错误
  - [ ] 导入成功，输出 "OK"
  - [ ] 所有 4 个方法都存在 (hasattr 返回 True)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 验证删除前语法正确
    Tool: Bash
    Preconditions: None
    Steps:
      1. 运行: uv run python -m py_compile src/agents/agent_factory.py
    Expected Result: 无输出 = 成功
    Failure Indicators: 语法错误输出
    Evidence: .sisyphus/evidence/task1-syntax-check.txt

  Scenario: 验证导入成功
    Tool: Bash
    Preconditions: None
    Steps:
      1. 运行: uv run python -c "from src.agents import AgentFactory; print('OK')"
    Expected Result: 输出 "OK"
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task1-import-check.txt

  Scenario: 验证方法存在
    Tool: Bash
    Preconditions: None
    Steps:
      1. 运行: uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('cache_size:', hasattr(f, 'cache_size')); print('clear_cache:', hasattr(f, 'clear_cache')); print('get_cached_agents:', hasattr(f, 'get_cached_agents')); print('has_agent:', hasattr(f, 'has_agent'))"
    Expected Result: 所有 hasattr 返回 True
    Failure Indicators: 任何方法不存在
    Evidence: .sisyphus/evidence/task1-methods-exist.txt
  ```

  **Commit**: NO

- [x] 2. 删除未使用方法

  **What to do**:
  - 使用 Edit 工具删除以下 4 个代码块:
    1. `cache_size` property (line 99-102)
    2. `clear_cache` 方法 (line 382-403)
    3. `get_cached_agents` 方法 (line 405-411)
    4. `has_agent` 方法 (line 413-422)
  - 注意: 每个删除都需要重新读取文件以获取最新的 LINE#ID

  **Must NOT do**:
  - 不要删除其他任何代码
  - 不要修改注释
  - 不要改变代码格式

  **Recommended Agent Profile**:
  > - **Category**: `quick`
  >   - Reason: 简单删除操作
  > - **Skills**: []
  > - **Skills Evaluated but Omitted**:
  >   - N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO (需要顺序删除)
  - **Parallel Group**: Wave 2 (sequential)
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `src/agents/agent_factory.py:99-102` - cache_size property
  - `src/agents/agent_factory.py:382-403` - clear_cache 方法
  - `src/agents/agent_factory.py:405-411` - get_cached_agents 方法
  - `src/agents/agent_factory.py:413-422` - has_agent 方法

  **Acceptance Criteria**:
  - [ ] cache_size property 已删除
  - [ ] clear_cache 方法已删除
  - [ ] get_cached_agents 方法已删除
  - [ ] has_agent 方法已删除

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 删除 cache_size property
    Tool: Edit (读取文件确认行号后删除)
    Preconditions: Task 1 完成
    Steps:
      1. 读取 src/agents/agent_factory.py
      2. 定位 cache_size property (约 line 99-102)
      3. 删除该代码块
    Expected Result: property 已删除
    Evidence: .sisyphus/evidence/task2-deletion-log.txt

  Scenario: 删除其他 3 个方法
    Tool: Edit (顺序删除)
    Preconditions: cache_size 已删除
    Steps:
      1. 重新读取文件获取新行号
      2. 删除 clear_cache 方法
      3. 重新读取
      4. 删除 get_cached_agents 方法
      5. 重新读取
      6. 删除 has_agent 方法
    Expected Result: 所有 4 个方法已删除
    Evidence: .sisyphus/evidence/task2-deletion-log.txt
  ```

  **Commit**: NO

- [x] 3. 验证删除后状态

  **What to do**:
  - 运行语法检查: `uv run python -m py_compile src/agents/agent_factory.py`
  - 运行导入检查: `uv run python -c "from src.agents import AgentFactory; print('OK')"`
  - 验证公共方法可用: `uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('create_agent:', hasattr(f, 'create_agent')); print('get_agent:', hasattr(f, 'get_agent')); print('get_or_create:', hasattr(f, 'get_or_create'))"`
  - 验证已删除方法不可访问: `uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('cache_size:', hasattr(f, 'cache_size')); print('clear_cache:', hasattr(f, 'clear_cache')); print('get_cached_agents:', hasattr(f, 'get_cached_agents')); print('has_agent:', hasattr(f, 'has_agent'))"`

  **Must NOT do**:
  - 不要修改任何代码

  **Recommended Agent Profile**:
  > - **Category**: `quick`
  >   - Reason: 验证任务
  > - **Skills**: []
  > - **Skills Evaluated but Omitted**:
  >   - N/A

  **Parallelization**:
  - **Can Run In Parallel**: YES (4个子任务)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 2

  **References**:
  - `src/agents/agent_factory.py` - 验证目标文件

  **Acceptance Criteria**:
  - [ ] 语法检查无错误
  - [ ] 导入成功
  - [ ] 公共方法仍然可用 (create_agent, get_agent, get_or_create)
  - [ ] 已删除方法不可访问 (cache_size, clear_cache, get_cached_agents, has_agent)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 验证删除后语法正确
    Tool: Bash
    Preconditions: Task 2 完成
    Steps:
      1. 运行: uv run python -m py_compile src/agents/agent_factory.py
    Expected Result: 无输出 = 成功
    Failure Indicators: 语法错误
    Evidence: .sisyphus/evidence/task3-syntax-check.txt

  Scenario: 验证导入成功
    Tool: Bash
    Preconditions: Task 2 完成
    Steps:
      1. 运行: uv run python -c "from src.agents import AgentFactory; print('OK')"
    Expected Result: 输出 "OK"
    Failure Indicators: ImportError
    Evidence: .sisyphus/evidence/task3-import-check.txt

  Scenario: 验证公共方法可用
    Tool: Bash
    Preconditions: Task 2 完成
    Steps:
      1. 运行: uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('create_agent:', hasattr(f, 'create_agent')); print('get_agent:', hasattr(f, 'get_agent')); print('get_or_create:', hasattr(f, 'get_or_create'))"
    Expected Result: 所有 hasattr 返回 True
    Failure Indicators: 任何公共方法不存在
    Evidence: .sisyphus/evidence/task3-public-methods.txt

  Scenario: 验证已删除方法不可访问
    Tool: Bash
    Preconditions: Task 2 完成
    Steps:
      1. 运行: uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print('cache_size:', hasattr(f, 'cache_size')); print('clear_cache:', hasattr(f, 'clear_cache')); print('get_cached_agents:', hasattr(f, 'get_cached_agents')); print('has_agent:', hasattr(f, 'has_agent'))"
    Expected Result: 所有 hasattr 返回 False
    Failure Indicators: 任何方法仍然存在
    Evidence: .sisyphus/evidence/task3-deleted-methods.txt
  ```

  **Commit**: NO

---

## Final Verification Wave

> 1 review agent runs to verify the cleanup.

- [x] F1. **清理验证** — `quick`
  读取 agent_factory.py 文件，确认：
  1. 4 个方法已删除
  2. 其他代码未改动
  3. 无语法错误
  Output: `删除验证 [PASS/FAIL] | 代码完整性 [PASS/FAIL] | 语法 [PASS/FAIL] | VERDICT`

---

## Success Criteria

### 验证命令
```bash
# 1. 语法检查
uv run python -m py_compile src/agents/agent_factory.py

# 2. 导入检查
uv run python -c "from src.agents import AgentFactory; print('OK')"

# 3. 公共方法可用
uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print(hasattr(f, 'create_agent'), hasattr(f, 'get_agent'), hasattr(f, 'get_or_create'))"

# 4. 已删除方法不可访问
uv run python -c "from src.agents import AgentFactory; f = AgentFactory(); print(hasattr(f, 'cache_size'), hasattr(f, 'clear_cache'), hasattr(f, 'get_cached_agents'), hasattr(f, 'has_agent'))"
```

### 最终检查清单
- [ ] 4 个未使用方法已删除
- [ ] 语法检查通过
- [ ] 导入检查通过
- [ ] 公共方法仍然可用
- [ ] 代码结构完整
