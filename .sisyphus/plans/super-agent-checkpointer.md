# 为super_agent添加Checkpointer

## TL;DR

> **快速摘要**: 为super_agent添加checkpointer功能，实现对话历史的自动保存和会话恢复能力。

> **交付物**:
> - Checkpointer初始化模块（使用SqliteSaver）
> - 支持session_id的会话恢复功能
> - 自动状态持久化

> **预估工作量**: 短
> **并行执行**: 否 - 顺序任务
> **关键路径**: 验证API → 实现checkpointer → 集成测试

---

## Context

### 原始请求
为super_agent添加checkpointer，实现会话恢复功能。

### 访谈总结
**关键讨论**:
- 核心功能: 会话恢复（中断后可继续）
- 持久化数据: 对话历史
- 保存时机: 自动保存
- 存储位置: 复用 data/minerbot.db
- 恢复方式: 手动指定session_id
- 失败处理: 静默继续

**研究结论**:
- 项目已有 `langgraph-checkpoint-sqlite>=3.0.3` 依赖但未使用
- 需要通过 `create_deep_agent` 的 `checkpointer` 参数集成
- 使用 `config={"configurable": {"thread_id": session_id}}` 管理会话

### Metis审查
**已识别并处理的问题**:
- DeepAgents框架的checkpointer参数支持（假设支持，需验证）
- 存储位置选择（复用minerbot.db）
- 静默失败策略

---

## Work Objectives

### 核心目标
为super_agent添加checkpointer，使其能够自动保存对话状态并支持通过session_id恢复会话。

### 具体交付物
- `src/minerbot/agent/checkpointer.py` - Checkpointer初始化模块
- 修改 `super_agent.py` 集成checkpointer
- 单元测试

### 完成定义
- [x] Checkpointer可以初始化并创建checkpoint数据库表
- [x] Agent执行后自动保存checkpoint
- [x] 使用相同session_id可以恢复之前的对话
- [x] 保存失败不影响主流程（静默失败）
- [x] 单元测试通过

### 必须有
- 复用现有的data/minerbot.db数据库
- 支持通过session_id参数恢复会话

### 必须没有（护栏）
- 不修改现有Agent的工具逻辑
- 不添加新的CLI命令
- 不添加认证/授权功能

---

## Verification Strategy

### 测试决策
- **基础设施存在**: 是
- **自动化测试**: 否
- **框架**: pytest（项目已有）
- **QA方式**: Agent执行验证

### QA策略
每个任务必须包含agent执行的QA场景验证。

---

## Execution Strategy

### 任务序列

```
Wave 1 (基础任务):
└── Task 1: 验证DeepAgents checkpointer支持 → Task 2 → Task 3

Wave 2 (实现):
└── Task 2: 实现checkpointer初始化 → Task 3

Wave 3 (集成):
└── Task 3: 集成checkpointer到super_agent → Task 4

Wave 4 (测试):
└── Task 4: 验证和测试 → None
```

### 依赖矩阵
- Task 1: — → Task 2
- Task 2: Task 1 → Task 3
- Task 3: Task 2 → Task 4
- Task 4: Task 3 → None

---

## TODOs

- [x] 1. 验证DeepAgents checkpointer支持

  **What to do**:
  - 查阅DeepAgents文档或源码，确认create_deep_agent是否支持checkpointer参数
  - 如果不支持，查找正确的集成方式
  - 创建测试脚本验证checkpointer能否正常工作

  **Must NOT do**:
  - 不要修改现有的agent逻辑
  - 不要创建新的数据库文件

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需要深入研究框架API和源码
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None

  **References**:
  - `src/minerbot/agent/super_agent.py:342-352` - create_deep_agent调用位置
  - `pyproject.toml:16` - langgraph-checkpoint-sqlite依赖

  **Acceptance Criteria**:
  - [ ] 测试脚本能导入并实例化SqliteSaver
  - [ ] 确认create_deep_agent是否接受checkpointer参数

  **QA Scenarios**:

  Scenario: 验证SqliteSaver可以实例化
    Tool: Bash (uv run)
    Preconditions: Python环境正常
    Steps:
      1. 运行: `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from langgraph.checkpoint.sqlite import SqliteSaver; import sqlite3; conn = sqlite3.connect('data/test_checkpoint.db'); saver = SqliteSaver(conn); print('OK')"`
    Expected Result: 输出包含"OK"
    Evidence: .sisyphus/evidence/task-1-saver-init.txt

- [x] 2. 实现checkpointer初始化模块

  **What to do**:
  - 创建 `src/minerbot/agent/checkpointer.py` 模块
  - 实现get_checkpointer()函数，返回配置好的SqliteSaver
  - 复用 `data/minerbot.db` 数据库
  - 添加check_same_thread=False解决线程问题
  - 实现静默失败逻辑（try-except包装）

  **Must NOT do**:
  - 不修改现有数据库的表结构
  - 不影响现有功能

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 标准的模块实现任务
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `src/minerbot/agent/super_agent.py` - 现有agent实现参考
  - `data/minerbot.db` - 目标数据库路径

  **Acceptance Criteria**:
  - [ ] checkpointer.py模块可以正常导入
  - [ ] get_checkpointer()返回SqliteSaver实例

  **QA Scenarios**:

  Scenario: Checkpointer模块导入测试
    Tool: Bash (uv run)
    Preconditions: 模块已创建
    Steps:
      1. 运行: `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.agent.checkpointer import get_checkpointer; cp = get_checkpointer(); print(type(cp))"`
    Expected Result: 输出包含"SqliteSaver"
    Evidence: .sisyphus/evidence/task-2-import.txt

- [x] 3. 集成checkpointer到super_agent

  **What to do**:
  - 修改 `super_agent.py`，导入get_checkpointer
  - 在create_deep_agent调用中添加checkpointer参数
  - 确保不影响现有功能

  **Must NOT do**:
  - 不修改现有的工具定义
  - 不删除注释掉的subagents代码

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 需要修改现有代码文件
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 4
  - **Blocked By**: Task 2

  **References**:
  - `src/minerbot/agent/super_agent.py:342-352` - create_deep_agent位置

  **Acceptance Criteria**:
  - [ ] super_agent可以正常导入
  - [ ] checkpointer被正确传递

  **QA Scenarios**:

  Scenario: Super agent导入测试
    Tool: Bash (uv run)
    Preconditions: checkpointer已集成
    Steps:
      1. 运行: `cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from minerbot.agent.super_agent import super_agent; print('Import OK')"`
    Expected Result: 输出"Import OK"
    Evidence: .sisyphus/evidence/task-3-import.txt

- [x] 4. 功能验证测试

  **What to do**:
  - 测试checkpoint创建
  - 测试会话恢复功能
  - 测试静默失败逻辑
  - 验证不会影响现有功能

  **Must NOT do**:
  - 不修改现有数据

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 功能验证测试
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - N/A

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `src/minerbot/agent/super_agent.py` - 入口文件

  **Acceptance Criteria**:
  - [ ] 可以创建checkpoint
  - [ ] 可以恢复会话

  **QA Scenarios**:

  Scenario: 创建checkpoint测试
    Tool: Bash (uv run)
    Preconditions: 集成完成
    Steps:
      1. 运行测试脚本验证checkpoint创建
    Expected Result: Checkpoint成功创建
    Evidence: .sisyphus/evidence/task-4-create.txt

  Scenario: 会话恢复测试
    Tool: Bash (uv run)
    Preconditions: checkpoint已创建
    Steps:
      1. 使用相同session_id再次调用
    Expected Result: 能获取之前的对话历史
    Evidence: .sisyphus/evidence/task-4-recover.txt

  Scenario: 不存在的session_id测试
    Tool: Bash (uv run)
    Preconditions: 正常的checkpointer配置
    Steps:
      1. 使用一个从未存在过的session_id调用agent
    Expected Result: 正常启动新会话，不报错
    Evidence: .sisyphus/evidence/task-4-nonexistent-session.txt

---

## Final Verification Wave

- [x] F1. **Plan Compliance Audit** — `oracle`
  检查所有Must Have是否存在，Must NOT Have是否满足。
  Output: VERDICT: APPROVE ✅

- [x] F2. **Code Quality Review** — `unspecified-high`
  检查代码质量：导入、语法、风格。
  Output: VERDICT: APPROVE ✅ (无新增错误，仅有已存在的类型警告)

- [x] F3. **功能验证** — `unspecified-high`
  实际运行测试验证checkpointer功能。
  Output: VERDICT: APPROVE ✅

---

## Commit Strategy

- 1: `feat(agent): add checkpointer for session recovery` — checkpointer.py, super_agent.py

---

## Success Criteria

### 验证命令
```bash
uv run python -c "from minerbot.agent.super_agent import super_agent; print('OK')"
```

### 最终检查清单
- [ ] Checkpointer模块可正常导入
- [ ] 可以创建checkpoint
- [ ] 可以通过session_id恢复会话
- [ ] 保存失败时静默继续
- [ ] 不影响现有功能
