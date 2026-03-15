# 长期记忆存储功能开发计划

## TL;DR

> **快速摘要**: 为 MinerBot 实现长期记忆存储功能，自动从会话中提取关键信息（人物、地点、事件、关系）并生成会话摘要。触发条件：会话结束、10条消息或10分钟空闲。使用 LLM 进行智能提取，asyncio.Queue 处理后台异步任务。

> **交付成果**:
> - 实体提取模块 (人物、地点、事件、关系)
> - 会话摘要自动生成模块
> - 异步任务调度器
> - 触发条件检测器
> - 与现有 SessionManager 集成

> **预计工作量**: Medium
> **并行执行**: YES - 3 waves
> **关键路径**: 类型定义 → 存储层 → 提取/摘要 → 调度器 → 集成

---

## 背景

### 原始需求
用户要求实现长期记忆存储功能，需满足：
1. 关键信息自动提取（人物、地点、事件、关系、上下文）
2. 会话摘要自动生成（主题、要点、决策、行动项）
3. 异步处理（不阻塞主线程）
4. 任务队列管理（高并发场景）

### 调研文档
参考 `docs/memory-checkpointer-store-flow.md` 中的实现方案，结合现有项目架构。

### 项目现状
- **Agent 框架**: DeepAgents (基于 LangGraph)
- **现有组件**: 
  - `SessionManager`: 管理 AsyncSqliteSaver (checkpointer) 和 AsyncSqliteStore
  - `create_agent()`: 接受 checkpointer 和 store 参数
- **存储后端**: SQLite (AsyncSqliteStore)
- **模型支持**: Anthropic Claude / MiniMax

---

## 工作目标

### 核心目标
实现从短期记忆（checkpointer）到长期记忆（store）的自动流转，包含：
1. 关键实体信息提取（LLM 驱动）
2. 会话摘要生成（LLM 驱动）
3. 异步非阻塞处理
4. 多触发条件支持

### 具体交付物
- `src/minerbot/memory/` 模块（新增）
- 类型定义扩展（types.py）
- 与 SessionManager 集成
- 单元测试和集成测试

### 定义完成
- [ ] 用户说"结束会话"时触发记忆提取
- [ ] 消息数量达到 10 条时触发
- [ ] 空闲 10 分钟后触发
- [ ] 提取结果存储到指定 namespace
- [ ] 后台任务不阻塞主对话流程

### 必须有
- LLM 驱动的实体提取
- LLM 驱动的会话摘要
- 异步任务队列
- 三种触发条件

### 禁止有
- 同步阻塞主线程
- 未测试的关键路径代码
- 破坏现有 checkpointer/store 功能

---

## 验证策略

### 测试决策
- **基础设施**: 已有 pytest + pytest-asyncio
- **自动化测试**: YES - 任务级 TDD
- **测试框架**: pytest + pytest-asyncio
- **QA 策略**: 每个任务包含 Agent-Executed QA Scenarios

### QA 策略
每个任务必须包含 agent 执行的验证场景：
- **Frontend/UI**: 不适用
- **TUI/CLI**: 使用 interactive_bash 验证 CLI 交互
- **API/Backend**: 使用 Bash (uv run) 运行测试
- **模块测试**: 使用 Bash (uv run pytest) 运行单元测试

---

## 执行策略

### 并行执行 Waves

```
Wave 1 (立即启动 — 基础类型 + 存储层):
├── T1: 内存类型定义 (entities, summary, record)
├── T2: 存储层封装 (MemoryStorage 类)
├── T3: 基础配置添加 (AppConfig 扩展)
└── T4: SessionManager 集成点准备

Wave 2 (Wave 1 后 — 核心功能):
├── T5: LLM 实体提取器 (extract_entities)
├── T6: LLM 会话摘要生成器 (generate_summary)
├── T7: 异步任务调度器 (TaskScheduler)
├── T8: 触发条件检测器 (TriggerManager)
└── T9: 消息序列化辅助函数

Wave 3 (Wave 2 后 — 集成 + 测试):
├── T10: SessionManager 集成 (记忆提取流程)
├── T11: CLI 集成 (触发命令)
├── T12: 单元测试 - 存储层
├── T13: 单元测试 - 提取器 + 摘要器
├── T14: 集成测试 - 完整流程
└── T15: 集成测试 - 触发条件

Wave FINAL (Wave 3 后 — 独立验证):
├── F1: 计划合规审计 (oracle)
├── F2: 代码质量审查 (unspecified-high)
├── F3: 手动 QA (unspecified-high)
└── F4: 范围保真检查 (deep)
```

### 依赖矩阵

- **T1-T4**: — — T5-T9, 1
- **T5-T9**: T1, T2, T3, T4 — T10-T11, 2
- **T10-T11**: T5, T6, T7, T8, T9 — T12-T15, 3
- **T12-T15**: T10, T11 — F1-F4, FINAL
- **F1-F4**: T12, T13, T14, T15 —

### Agent 分配

- **Wave 1**: 4 tasks → `quick` (类型定义、简单封装)
- **Wave 2**: 5 tasks → `unspecified-high` (LLM 调用、异步调度)
- **Wave 3**: 6 tasks → `deep` (集成) + `quick` (测试)
- **FINAL**: 4 tasks → `oracle` + `unspecified-high` + `deep`

---

## 待办事项

- [x] 1. **内存类型定义**

  **要做的**:
  - 在 `src/minerbot/types.py` 中添加长期记忆相关类型：
    - `MemoryEntity`: 实体类型（人物/地点/事件/关系/其他）
    - `EntityType` 枚举: PERSON, LOCATION, EVENT, RELATIONSHIP, CONTEXT
    - `SessionSummary`: 会话摘要（主题、要点、决策、行动项）
    - `MemoryRecord`: 长期记忆记录
  - 创建 `src/minerbot/memory/__init__.py` 导出模块

  **不能做的**:
  - 不修改现有的 ExitCode, ChatMessage, SessionInfo 类型
  - 不破坏现有类型的向后兼容

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 纯类型定义，简单直接
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 1 (与 T2, T3, T4)
  - **阻塞**: T5-T9
  - **被阻塞**: None (可立即开始)

  **引用** (关键 - 必须是详尽的):
  - `src/minerbot/types.py:1-26` - 现有类型定义模式
  - `docs/memory-checkpointer-store-flow.md:227-283` - 实体提取结构参考

  **验收标准**:
  - [ ] 类型文件无语法错误: `uv run python -c "from minerbot.types import *"`
  - [ ] 所有新类型可导入: `from minerbot.types import MemoryEntity, SessionSummary, MemoryRecord`
  - [ ] 类型包含必需字段（参考调研文档）

  **QA 场景**:

  ```
  场景: 验证类型定义可导入
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run python -c "from minerbot.types import MemoryEntity, EntityType, SessionSummary, MemoryRecord; print('OK')"`
    预期: 输出 "OK"，无错误
    失败: ImportError 或语法错误
    证据: .sisyphus/evidence/task-1-types-import.{txt,log}
  ```

  **提交**: YES
  - 信息: `feat(types): 添加长期记忆相关类型定义`
  - 文件: `src/minerbot/types.py`

---

- [x] 2. **存储层封装**

  **要做的**:
  - 创建 `src/minerbot/memory/storage.py`
  - 实现 `MemoryStorage` 类：
    - `__init__(store: AsyncSqliteStore, namespace_prefix: str = "memory")`
    - `save_entity(user_id: str, entity: MemoryEntity)` - 保存实体
    - `save_summary(user_id: str, thread_id: str, summary: SessionSummary)` - 保存摘要
    - `search_entities(user_id: str, query: str, limit: int = 10)` - 搜索实体
    - `search_summaries(user_id: str, query: str, limit: int = 10)` - 搜索摘要
    - `get_entity(user_id: str, entity_id: str)` - 获取单个实体
    - `get_summary(user_id: str, thread_id: str)` - 获取单个摘要
  - 命名空间设计:
    - 实体: `("entities", user_id)`
    - 摘要: `("summaries", user_id)`

  **不能做的**:
  - 不直接操作 checkpointer（只使用 store）
  - 不创建新的数据库连接（复用现有的 store）

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 存储层封装，模式清晰
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 1 (与 T1, T3, T4)
  - **阻塞**: T5-T9
  - **被阻塞**: T1 (类型定义)

  **引用**:
  - `src/minerbot/agent/session.py:1-52` - 现有 SessionManager store 使用模式
  - `docs/memory-checkpointer-store-flow.md:414-466` - Store 命名空间设计参考

  **验收标准**:
  - [ ] MemoryStorage 类可实例化
  - [ ] save_entity 和 save_summary 方法可用
  - [ ] 搜索方法返回正确类型
  - [ ] 单元测试: `uv run pytest tests/test_memory_storage.py -v`

  **QA 场景**:

  ```
  场景: 验证存储层基本功能
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run python -c "
from langgraph.store.memory import InMemoryStore
from minerbot.memory.storage import MemoryStorage
storage = MemoryStorage(InMemoryStore(), 'test')
print('MemoryStorage created OK')
"`
    预期: 输出 "MemoryStorage created OK"
    失败: 导入错误或初始化失败
    证据: .sisyphus/evidence/task-2-storage-init.{txt,log}
  ```

  **提交**: YES
  - 信息: `feat(memory): 实现存储层封装`
  - 文件: `src/minerbot/memory/storage.py`

---

- [x] 3. **基础配置扩展**

  **要做的**:
  - 扩展 `src/minerbot/config.py` 中的 `AppConfig`：
    - 添加 `memory_enabled: bool = True` - 记忆功能开关
    - `memory_trigger_message_count: int = 10` - 消息数量触发阈值
    - `memory_trigger_idle_minutes: int = 10` - 空闲触发阈值
    - `memory_summary_model: str = "claude-sonnet-4-6"` - 摘要模型
  - 添加对应环境变量支持:
    - `MEMORY_ENABLED`
    - `MEMORY_TRIGGER_MESSAGE_COUNT`
    - `MEMORY_TRIGGER_IDLE_MINUTES`
    - `MEMORY_SUMMARY_MODEL`

  **不能做的**:
  - 不修改现有配置项的默认值
  - 不破坏现有配置加载逻辑

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 简单配置扩展
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 1 (与 T1, T2, T4)
  - **阻塞**: T5-T9
  - **被阻塞**: None (可立即开始)

  **引用**:
  - `src/minerbot/config.py:1-41` - 现有配置模式
  - `docs/memory-checkpointer-store-flow.md:550-558` - MemoryConfig 参考

  **验收标准**:
  - [ ] 新配置项可从环境变量加载
  - [ ] 配置验证通过: `AppConfig.from_env().validate()`

  **QA 场景**:

  ```
  场景: 验证配置扩展
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run python -c "
from minerbot.config import AppConfig
config = AppConfig.from_env()
print(f'memory_enabled: {config.memory_enabled}')
print(f'memory_trigger_message_count: {config.memory_trigger_message_count}')
print(f'memory_trigger_idle_minutes: {config.memory_trigger_idle_minutes}')
"`
    预期: 输出配置值，无错误
    失败: 属性不存在错误
    证据: .sisyphus/evidence/task-3-config.{txt,log}
  ```

  **提交**: YES
  - 信息: `feat(config): 添加记忆功能配置选项`
  - 文件: `src/minerbot/config.py`

---

- [x] 4. **SessionManager 集成点准备**

  **要做的**:
  - 扩展 `src/minerbot/agent/session.py` 的 SessionManager：
    - 添加 `memory_storage: MemoryStorage | None = None` 属性
    - 修改 `create()` 方法接收 memory_storage 参数
    - 添加 `get_memory_storage()` 方法返回 memory_storage 实例
  - 修改 `src/minerbot/agent/factory.py`:
    - 在 `create_agent_with_session()` 中初始化 MemoryStorage
    - 传递 store 给 MemoryStorage

  **不能做的**:
  - 不破坏现有的 checkpointer 和 store 功能
  - 不添加新的数据库连接

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 简单的属性添加和方法扩展
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 1 (与 T1, T2, T3)
  - **阻塞**: T10
  - **被阻塞**: T2 (需要 MemoryStorage 类)

  **引用**:
  - `src/minerbot/agent/session.py:1-52` - 现有 SessionManager
  - `src/minerbot/agent/factory.py:78-89` - create_agent_with_session

  **验收标准**:
  - [ ] SessionManager 有 memory_storage 属性
  - [ ] create_agent_with_session 返回 memory_storage
  - [ ] 现有功能不受影响

  **QA 场景**:

  ```
  场景: 验证 SessionManager 集成点
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run python -c "
from minerbot.agent.session import SessionManager
import inspect
members = [m for m in dir(SessionManager) if 'memory' in m.lower()]
print(f'Memory-related members: {members}')
"`
    预期: 输出包含 memory_storage 或 get_memory_storage
    失败: AttributeError
    证据: .sisyphus/evidence/task-4-session.{txt,log}
  ```

  **提交**: YES
  - 信息: `feat(memory): 添加 SessionManager 集成点`
  - 文件: `src/minerbot/agent/session.py`, `src/minerbot/agent/factory.py`

---

- [x] 5. **LLM 实体提取器**
- [x] 6. **LLM 会话摘要生成器**
- [x] 7. **异步任务调度器**
- [x] 8. **触发条件检测器**
- [x] 9. **消息序列化辅助函数**

  **要做的**:
  - 在 `src/minerbot/memory/utils.py` 创建辅助函数：
    - `def serialize_messages(messages: list) -> list[dict]` - 序列化消息为可 JSON 序列化的格式
    - `def deserialize_messages(data: list[dict]) -> list` - 反序列化消息
    - `def get_thread_message_count(checkpointer, thread_id: str) -> int` - 获取线程消息数
    - `def get_thread_last_activity(checkpointer, thread_id: str) -> datetime | None` - 获取最后活动时间
  - 处理 LangGraph 消息类型 (HumanMessage, AIMessage, ToolMessage)
  - 提取关键字段: content, type, tool_calls, response_metadata

  **不能做的**:
  - 不修改原始消息对象
  - 不依赖特定的消息实现细节

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 纯函数，无状态
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 2 (与 T5, T6, T7, T8)
  - **阻塞**: T10
  - **被阻塞**: T1 (需要类型)

  **引用**:
  - `docs/memory-checkpointer-store-flow.md:108-149` - 消息格式参考

  **验收标准**:
  - [ ] 序列化函数返回可 JSON 序列化的数据
  - [ ] 反序列化函数返回正确的消息对象
  - [ ] 消息计数正确

  **QA 场景**:

  ```
  场景: 验证消息序列化
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run python -c "
from minerbot.memory.utils import serialize_messages
from langchain_core.messages import HumanMessage, AIMessage

messages = [
    HumanMessage(content='Hello'),
    AIMessage(content='Hi there')
]
serialized = serialize_messages(messages)
print(f'Serialized count: {len(serialized)}')
print(f'First type: {serialized[0][\"type\"]}')
print('Serialize messages OK')
"`
    预期: 输出序列化结果
    失败: 序列化错误
    证据: .sisyphus/evidence/task-9-utils.{txt,log}
  ```

  **提交**: YES
  - 信息: `feat(memory): 添加消息序列化辅助函数`
  - 文件: `src/minerbot/memory/utils.py`

---

- [x] 10. **SessionManager 集成**
- [x] 11. **CLI 集成**
- [x] 12. **单元测试 - 存储层**
- [x] 13. **单元测试 - 提取器 + 摘要器**
- [x] 14. **集成测试 - 完整流程**
- [x] 15. **集成测试 - 触发条件**

  **要做的**:
  - 创建 `tests/test_memory_triggers.py`:
    - 测试 TriggerManager 初始化
    - 测试会话结束触发
    - 测试消息数量触发
    - 测试空闲超时触发
    - 测试 TriggerResult 正确性
  - 使用 pytest-asyncio

  **不能做的**:
  - 不测试实际的时间等待（使用 mock）
  - 不测试不存在的触发类型

  **推荐 Agent 配置文件**:
  - **类别**: `quick`
    - 理由: 标准单元测试
  - **技能**: []
  - **技能评估但省略**:
    - N/A

  **并行化**:
  - **可以并行运行**: YES
  - **并行组**: Wave 3 (与 T12, T13, T14)
  - **阻塞**: None
  - **被阻塞**: T10, T11

  **引用**:
  - `src/minerbot/memory/triggers.py` - 触发器实现

  **验收标准**:
  - [ ] 触发器测试通过: `uv run pytest tests/test_memory_triggers.py -v`

  **QA 场景**:

  ```
  场景: 运行触发条件测试
    工具: Bash
    前提: 无
    步骤:
      1. 运行: `uv run pytest tests/test_memory_triggers.py -v --tb=short`
    预期: 所有触发条件测试通过
    失败: 测试失败
    证据: .sisyphus/evidence/task-15-triggers-test.{txt,log}
  ```

  **提交**: YES
  - 信息: `test(memory): 添加触发条件测试`
  - 文件: `tests/test_memory_triggers.py`

---

## 最终验证 Wave

> 4 个审查 Agent 并行运行。所有必须批准。拒绝 → 修复 → 重新运行。

- [x] F1. **计划合规审计** — `oracle`
- [x] F2. **代码质量审查** — `unspecified-high`
- [x] F3. **真实手动 QA** — `unspecified-high`
- [x] F4. **范围保真检查** — `deep`
  对于每个任务：读取"要做什么"，读取实际 diff。验证 1:1 — 规范中的所有内容都已构建（无遗漏），超出规范的内容均未构建（无蔓延）。检查"禁止做"合规性。检测跨任务污染：任务 N 触碰任务 M 的文件。标记未计入的更改。
  输出: `任务 [N/N 合规] | 污染 [清洁/N 问题] | 未计入 [清洁/N 文件] | 裁决`

---

## 提交策略

- **1**: `feat(memory): 添加长期记忆存储基础类型` — types.py, memory/entities.py
- **2**: `feat(memory): 实现存储层封装` — memory/storage.py
- **3**: `feat(memory): 实现 LLM 实体提取器` — memory/extractor.py
- **4**: `feat(memory): 实现 LLM 会话摘要生成器` — memory/summarizer.py
- **5**: `feat(memory): 实现异步任务调度器` — memory/scheduler.py
- **6**: `feat(memory): 实现触发条件检测器` — memory/triggers.py
- **7**: `feat(memory): 集成到 SessionManager` — agent/session.py, memory/__init__.py
- **8**: `test(memory): 添加单元测试和集成测试` — tests/

---

## 成功标准

### 验证命令
```bash
uv run pytest tests/ -v  # 所有测试通过
```

### 最终检查清单
- [ ] 所有"必须有"已实现
- [ ] 所有"禁止有"已消除
- [ ] 所有测试通过
- [ ] 异步处理不阻塞主线程
- [ ] 三种触发条件正常工作
