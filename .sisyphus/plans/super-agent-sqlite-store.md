# 为 super_agent 添加 SQLite Store

## TL;DR

> **快速摘要**: 使用 LangGraph 官方的 `langgraph.store.sqlite.SqliteStore`，集成到 super_agent，支持用户偏好和长期记忆存储。

> **交付物**:
> - `src/minerbot/agent/store.py` - 使用官方 SqliteStore 的封装
> - `super_agent.py` 集成 store

> **估算工作量**: 短
> **并行执行**: 否 - 顺序执行
> **关键路径**: 创建 store.py → 集成到 super_agent → 验证

---

## Context

### 原始需求
为 super_agent 增加 store，使用 SQLite 存储，基于 create_deep_agent 的 store 参数

### Momus 审查发现（关键）
**LangGraph 官方已提供 SqliteStore！** 不需要自己实现：
- 位置：`langgraph.store.sqlite.SqliteStore`
- 特性：
  - 实现 BaseStore 接口
  - 使用 `check_same_thread=False`（与 checkpointer 一致）
  - 自动表迁移
  - 支持命名空间、键、值、时间戳
  - 生产级测试

### 访谈总结
**关键讨论**:
- 使用 create_deep_agent 的 store 参数（BaseStore 类型）
- 使用 LangGraph 官方的 `langgraph.store.sqlite.SqliteStore`
- 用户偏好 + 长期记忆存储
- 使用同一个数据库文件（data/minerbot.db）
- 仅同步方法

---

## Work Objectives

### 核心目标
为 super_agent 添加持久化 SQLite Store，支持用户偏好和长期记忆存储

### 具体交付物
- `src/minerbot/agent/store.py`: 使用官方 SqliteStore 的封装
- 集成到 `super_agent.py`

### 完成定义
- [ ] store 可实例化
- [ ] super_agent 可正常运行

### 必须有
- 使用官方 `langgraph.store.sqlite.SqliteStore`
- 复用 checkpointer 的数据库路径

### 必须没有（边界）
- 无搜索功能
- 无异步方法
- 无测试文件

---

## Verification Strategy

### 测试决策
- **基础设施存在**: 否
- **自动化测试**: 否
- **框架**: 无

### QA 策略
每个任务必须包含 agent-executed QA 场景：
- 使用 Bash 运行 Python 脚本验证功能
- 验证文件存在和基本运行

---

## Execution Strategy

### 执行顺序

```
Wave 1 (立即开始):
└── Task 1: 创建 store.py 封装

Wave 2 (Task 1 完成后):
└── Task 2: 集成 store 到 super_agent

Wave 3 (Task 2 完成后):
└── Task 3: 验证功能正常
```

### 依赖矩阵
- Task 1: — — 2
- Task 2: 1 — 3
- Task 3: 2 — —

---

## TODOs

- [x] 1. 创建 store.py 封装

  **What to do**:
  - 创建 `src/minerbot/agent/store.py`
  - 导入 `langgraph.store.sqlite.SqliteStore`
  - 添加 `get_store()` 函数，复用 checkpointer 的数据库路径
  - 创建并返回 SqliteStore 实例

  **Must NOT do**:
  - 不破坏现有 checkpointer 功能
  - 不添加搜索功能
  - 不添加异步方法

  **Recommended Agent Profile**:
  > **Category**: `quick`
    - Reason: 简单封装，直接使用官方类
  > **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2
  - **Blocked By**: None

  **References**:
  - `src/minerbot/agent/checkpointer.py` - 数据库路径参考
  - `src/minerbot/agent/super_agent.py` - 现有配置

  **Acceptance Criteria**:
  - [ ] 文件 `src/minerbot/agent/store.py` 创建
  - [ ] get_store() 函数可调用

  **QA Scenarios**:

  Scenario: 验证 store.py 可导入
    Tool: Bash
    Preconditions: store.py 已创建
    Steps:
      1. 运行 `python -c "from minerbot.agent.store import get_store; print('OK')"`
    Expected Result: 输出 OK，无错误
    Evidence: 终端输出

- [x] 2. 集成 store 到 super_agent

  **What to do**:
  - 在 super_agent.py 导入 get_store
  - 创建 store 实例
  - 传递给 create_deep_agent 的 store 参数

  **Must NOT do**:
  - 不修改 checkpointer 配置
  - 不删除现有功能

  **Recommended Agent Profile**:
  > **Category**: `quick`
    - Reason: 简单配置修改
  > **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `src/minerbot/agent/super_agent.py` - 现有配置

  **Acceptance Criteria**:
  - [ ] super_agent.py 导入 get_store
  - [ ] create_deep_agent 传入 store 参数

  **QA Scenarios**:

  Scenario: 验证 super_agent 初始化成功
    Tool: Bash
    Preconditions: super_agent.py 已修改
    Steps:
      1. 运行 `python -c "from minerbot.agent.super_agent import super_agent; print('OK')"`
    Expected Result: 输出 OK，无错误
    Evidence: 终端输出

- [x] 3. 验证功能正常

  **What to do**:
  - 验证 store 基本操作
  - 验证数据持久化

  **Must NOT do**:
  - 不添加新文件

  **Recommended Agent Profile**:
  > **Category**: `quick`
    - Reason: 验证任务
  > **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 2

  **References**:
  - `src/minerbot/agent/super_agent.py` - 运行入口

  **Acceptance Criteria**:
  - [ ] super_agent 可运行

  **QA Scenarios**:

  Scenario: 验证 store 持久化
    Tool: Bash
    Preconditions: super_agent 可运行
    Steps:
      1. 运行 Python 测试 store put/get
      2. 验证数据可持久化
    Expected Result: 数据写入和读取成功
    Evidence: 终端输出

---

## Final Verification Wave

- [x] F1. **代码完整性检查** — `quick`
  检查所有文件存在，导入正确
  Output: `Files [2/2] | Imports [PASS] | VERDICT: APPROVE`

- [x] F2. **功能验证** — `quick`
  运行 super_agent，验证 store 功能
  Output: `Store [WORK] | Agent [WORK] | VERDICT: APPROVE`

---

## Commit Strategy

- **1**: `feat(agent): 添加 store 封装`
  - Files: `src/minerbot/agent/store.py`

- **2**: `feat(agent): 集成 store 到 super_agent`
  - Files: `src/minerbot/agent/super_agent.py`

---

## Success Criteria

### 验证命令
```bash
# 验证模块导入
python -c "from minerbot.agent.store import get_store; print('OK')"

# 验证 super_agent 导入
python -c "from minerbot.agent.super_agent import super_agent; print('OK')"
```

### 最终检查
- [ ] get_store() 工厂函数存在
- [ ] super_agent 集成 store
- [ ] 数据持久化工作
