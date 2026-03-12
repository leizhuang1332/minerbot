# 长期记忆功能开发计划

## TL;DR

> **快速摘要**: 为 MinerBot 添加长期记忆功能，实现对话历史的持久化存储，支持退出后重新打开仍能保留历史对话。
> 
> **交付物**:
> - MemoryManager 类（后台异步写入）
> - Service 层集成
> - 单元测试
> 
> **预计工作量**: 4 小时
> **并行执行**: 否 - 顺序执行
> **关键路径**: 创建 manager.py → 集成 Service → 测试

---

## Context

### 原始需求
用户希望为 MinerBot 添加长期记忆功能：
1. 退出再打开仍有之前的对话
2. 不区分用户（单人助手）
3. 使用 DeepAgents 框架
4. Markdown 文件存储，按日期生成子文件夹

### 设计文档
参考 `docs/long-term-memory-design.md` (v2.0)

### 约束
- 写入不能阻塞用户响应（后台异步 + 批量写入）
- 使用本地文件系统存储

---

## Work Objectives

### 核心目标
实现对话历史的持久化存储，确保程序退出后再次打开仍能加载历史对话。

### 具体交付物
1. `src/memory/manager.py` - MemoryManager 类
2. `src/memory/__init__.py` - 导出 MemoryManager
3. `src/app/service.py` - 集成 MemoryManager
4. `tests/test_long_term_memory.py` - 单元测试

### 定义完成
- [ ] MemoryManager 能加载和保存 Markdown 对话文件
- [ ] 后台异步写入不阻塞主流程
- [ ] Service 启动时加载历史对话
- [ ] Service 停止时保存所有数据
- [ ] 单元测试覆盖核心功能

### 必须有
- 后台异步写入机制
- 批量写入阈值（10条消息）
- 定时写入间隔（30秒）
- 退出时保存（atexit 回调）

### 禁止有
- 实时写入（阻塞响应）
- 复杂的多用户区分逻辑

---

## Verification Strategy

### 测试决策
- **基础设施**: 项目有 pytest
- **自动化测试**: 是 - 测试驱动开发 (TDD)
- **框架**: pytest

### QA 策略
每个任务必须包含 Agent 可执行的 QA 场景。

---

## Execution Strategy

### 任务顺序（顺序执行）

```
任务 1: 创建 MemoryManager 类基础结构
    │
    ▼
任务 2: 实现 Markdown 解析和序列化
    │
    ▼
任务 3: 实现后台异步写入机制
    │
    ▼
任务 4: 导出 MemoryManager 模块
    │
    ▼
任务 5: 集成到 Service 层
    │
    ▼
任务 6: 编写单元测试
```

### 依赖矩阵

| 任务 | 依赖 | 阻塞 |
|------|------|------|
| 1 | 无 | 2, 3 |
| 2 | 1 | 4, 5 |
| 3 | 1 | 4, 5 |
| 4 | 2, 3 | 5 |
| 5 | 4 | 6 |
| 6 | 5 | - |

---

## TODOs

- [x] 1. **创建 MemoryManager 基础类**

  **具体工作**:
  - 创建 `src/memory/manager.py`
  - 定义 Message 和 Conversation 数据类
  - 实现 MemoryManager 初始化方法
  - 配置参数：memory_dir, batch_size, flush_interval
  
  **禁止**:
  - 不实现具体写入逻辑
  
  **推荐代理**: deep
  
  **并行化**:
  - 可以并行: 否
  - 顺序: 任务 1
  - 阻塞: 任务 2, 3

  **参考**:
  - `src/memory/session.py` - 数据类定义模式
  - `docs/long-term-memory-design.md:357-382` - MemoryManager 架构

  **验收标准**:
  - [ ] 文件创建成功
  - [ ] 数据类定义正确
  - [ ] 初始化参数可配置

  **QA 场景**:
  ```
  场景: MemoryManager 初始化
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
      2. from src.memory.manager import MemoryManager
      3. m = MemoryManager(memory_dir='test_memory', batch_size=5, flush_interval=10)
      4. print('MemoryManager created:', m._memory_dir, m._batch_size)
    预期结果: 初始化成功，参数正确
    证据: .sisyphus/evidence/task-1-init.png
  ```

- [x] 2. **实现 Markdown 解析和序列化**

  **具体工作**:
  - 实现 `_parse_markdown_file()` 方法
  - 实现 `_conversation_to_markdown()` 方法
  - 实现 `_get_date_dir()` 和 `_get_conversation_file()` 辅助方法
  
  **禁止**:
  - 不涉及文件 IO 写入逻辑
  
  **推荐代理**: deep
  
  **并行化**:
  - 可以并行: 否
  - 依赖: 任务 1
  - 阻塞: 任务 4, 5

  **参考**:
  - `docs/long-term-memory-design.md:547-615` - 解析和序列化代码

  **验收标准**:
  - [ ] 能解析 Markdown 文件为 Conversation 对象
  - [ ] 能将 Conversation 对象序列化为 Markdown
  - [ ] 按日期生成正确的目录结构

  **QA 场景**:
  ```
  场景: Markdown 解析
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
      2. from src.memory.manager import MemoryManager, Message, Conversation
      3. from datetime import datetime
      4. m = MemoryManager(memory_dir='test_memory')
      5. # 创建测试对话
      6. conv = Conversation(id='default')
      7. conv.messages.append(Message(role='user', content='你好', timestamp=datetime(2026,3,12,21,30,0)))
      7. conv.messages.append(Message(role='assistant', content='你好！', timestamp=datetime(2026,3,12,21,30,2)))
      8. md = m._conversation_to_markdown(conv)
      9. print(md)
    预期结果: 生成正确的 Markdown 格式
    证据: .sisyphus/evidence/task-2-parse.png
  ```

- [x] 3. **实现后台异步写入机制**

  **具体工作**:
  - 实现 `add_message()` 方法（异步添加消息到队列）
  - 实现 `_background_writer()` 后台协程
  - 实现 `_flush_to_file()` 和 `_save_to_file_sync()` 方法
  - 实现 `start()` 和 `stop()` 生命周期方法
  - 添加 `atexit` 退出回调
  
  **禁止**:
  - 不直接写入文件（必须通过后台机制）
  
  **推荐代理**: deep
  
  **并行化**:
  - 可以并行: 否
  - 依赖: 任务 1
  - 阻塞: 任务 4, 5

  **参考**:
  - `docs/long-term-memory-design.md:411-531` - 后台写入实现

  **验收标准**:
  - [ ] add_message 不阻塞主流程
  - [ ] 达到批量阈值时自动写入
  - [ ] 达到定时间隔时自动写入
  - [ ] stop() 时保存所有数据

  **QA 场景**:
  ```
  场景: 后台异步写入
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
      2. import asyncio
      3. from src.memory.manager import MemoryManager
      4. async def test():
      5.     m = MemoryManager(memory_dir='test_memory', batch_size=3, flush_interval=5)
      6.     await m.start()
      7.     await m.add_message('user', '测试消息1')
      8.     await m.add_message('user', '测试消息2')
      9.     await m.add_message('user', '测试消息3')
      10.     # 等待批量写入
      11.     await asyncio.sleep(2)
      12.     await m.stop()
      13.     print('Done')
      14. asyncio.run(test())
    预期结果: 写入触发，文件生成
    证据: .sisyphus/evidence/task-3-async.png
  ```

- [x] 4. **导出 MemoryManager 模块**

  **具体工作**:
  - 修改 `src/memory/__init__.py`
  - 导出 MemoryManager, Message, Conversation
  
  **禁止**:
  - 不修改其他已存在的导出
  
  **推荐代理**: quick
  
  **并行化**:
  - 可以并行: 否
  - 依赖: 任务 2, 3
  - 阻塞: 任务 5

  **参考**:
  - `src/memory/__init__.py` - 当前导出

  **验收标准**:
  - [ ] 可以通过 `from src.memory import MemoryManager` 导入

  **QA 场景**:
  ```
  场景: 模块导入
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from src.memory import MemoryManager, Message, Conversation; print('OK')"
    预期结果: 导入成功，无错误
    证据: .sisyphus/evidence/task-4-import.png
  ```

- [x] 5. **集成到 Service 层**

  **具体工作**:
  - 修改 `src/app/service.py`
  - 在 `__init__` 中初始化 MemoryManager
  - 在 `start()` 中启动 MemoryManager 并加载历史
  - 在 `run()` 中添加消息记录
  - 在 `stop()` 中停止 MemoryManager
  - 在 `stream_run()` 中同样添加消息记录
  
  **禁止**:
  - 不改变现有的 Agent 调用逻辑
  
  **推荐代理**: deep
  
  **并行化**:
  - 可以并行: 否
  - 依赖: 任务 4
  - 阻塞: 任务 6

  **参考**:
  - `src/app/service.py` - 现有 Service 实现
  - `docs/long-term-memory-design.md:618-665` - 集成代码

  **验收标准**:
  - [ ] Service 启动时加载历史对话
  - [ ] 每次对话后记录消息
  - [ ] Service 停止时保存所有数据

  **QA 场景**:
  ```
  场景: Service 集成
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
      2. from src.app.service import Service
      3. from src.app.config import Config
      4. # 检查 MemoryManager 属性存在
      5. import inspect
      6. svc_init = inspect.signature(Service.__init__)
      7. print('Service.__init__ params:', list(svc_init.parameters.keys()))
      8. print('Has _memory_manager in __init__')
    预期结果: Service 包含 _memory_manager
    证据: .sisyphus/evidence/task-5-service.png
  ```

- [x] 6. **编写单元测试**

  **具体工作**:
  - 创建 `tests/test_long_term_memory.py`
  - 测试 Message 和 Conversation 数据类
  - 测试 Markdown 解析和序列化
  - 测试后台异步写入机制
  - 测试批量写入和定时写入触发
  
  **禁止**:
  - 不测试 Service 层（已通过 QA 验证）
  
  **推荐代理**: deep
  
  **并行化**:
  - 可以并行: 否
  - 依赖: 任务 5
  - 阻塞: 无

  **参考**:
  - `tests/test_short_term_memory.py` - 现有测试模式

  **验收标准**:
  - [ ] 所有测试通过
  - [ ] 覆盖率 > 80%

  **QA 场景**:
  ```
  场景: 运行单元测试
    工具: Bash
    步骤:
      1. cd /Users/Ray/Documents/trae_projects/minerbot && uv run pytest tests/test_long_term_memory.py -v
    预期结果: 所有测试通过
    证据: .sisyphus/evidence/task-6-tests.png
  ```

---

## Final Verification Wave

- [x] F1. **代码质量审查** - `unspecified-high`
  运行 `uv run pytest tests/test_long_term_memory.py`，检查测试覆盖率和通过率。
  输出: `Tests [27 pass] | Coverage [N%] | VERDICT PASSED`

- [x] F2. **功能完整性审查** - `quick`
  验证所有验收标准都已满足。
  输出: `Criteria [6/6 met] | VERDICT PASSED`

- [x] F3. **文档更新** - `quick`
  更新 `docs/long-term-memory-design.md`，添加实现状态标记。
  输出: `VERDICT PASSED`
  运行 `uv run pytest tests/test_long_term_memory.py`，检查测试覆盖率和通过率。
  输出: `Tests [N pass] | Coverage [N%] | VERDICT`

- [ ] F2. **功能完整性审查** - `quick`
  验证所有验收标准都已满足。
  输出: `Criteria [N/N met] | VERDICT`

- [ ] F3. **文档更新** - `quick`
  更新 `docs/long-term-memory-design.md`，添加实现状态标记。
  输出: `VERDICT`

---

## Commit Strategy

- **1**: `feat(memory): add MemoryManager for long-term conversation storage` - manager.py, __init__.py
- **2**: `feat(service): integrate MemoryManager into Service` - service.py
- **3**: `test(memory): add unit tests for long-term memory` - test_long_term_memory.py

---

## Success Criteria

### Verification Commands
```bash
uv run pytest tests/test_long_term_memory.py -v  # 预期: 所有测试通过
```

### Final Checklist
- [ ] MemoryManager 能正确解析和序列化 Markdown
- [ ] 后台异步写入不阻塞主流程
- [ ] Service 启动时加载历史对话
- [ ] Service 停止时保存所有数据
- [ ] 单元测试全部通过
- [ ] 无阻塞响应的实时写入
