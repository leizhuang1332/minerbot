# 长期记忆功能修复开发计划

## TL;DR

> **快速摘要**：修复 Service 层对 MemoryManager 的集成，实现长期记忆功能
> 
> **交付物**：
> - 修复 `src/app/service.py` 中的四处遗漏实现
> - 添加长期记忆配置项
> - 验证功能正常工作
> 
> **预估工作量**：Short
> **并行执行**：NO - 顺序执行
> **关键路径**：Task 1 → Task 2 → Task 3 → Task 4

---

## Context

### 原始请求
根据 `issues/long-term-memory-debug-report.md` 排查报告，修复长期记忆功能未生效的问题。

### 排查结论
- **MemoryManager 类已实现**（`src/memory/manager.py`）- 功能完整，单元测试全部通过（27/27）
- **Service 层集成未完成** - 四个关键位置存在遗漏实现

### 需要修复的问题

| 序号 | 问题 | 位置 | 根本原因 |
|------|------|------|----------|
| 1 | `_init_memory_manager()` 返回 `None` | service.py:78-86 | 方法未实现完整逻辑 |
| 2 | `start()` 未调用 `memory_manager.start()` | service.py:145 | 遗漏实现 |
| 3 | `stop()` 未调用 `memory_manager.stop()` | service.py:302 | 遗漏实现 |
| 4 | `run()` 未调用 `load_conversation()` | service.py:348 | 遗漏实现 |

---

## Work Objectives

### 核心目标
在 Service 层正确集成 MemoryManager，使长期记忆功能生效。

### 具体交付物
- [ ] 修改 `_init_memory_manager()` 方法，返回正确的 MemoryManager 实例
- [ ] 修改 `start()` 方法，启动 MemoryManager 后台任务并加载历史对话
- [ ] 修改 `stop()` 方法，停止 MemoryManager 后台任务
- [ ] 验证功能正常工作

### 完成定义
- [ ] Service 初始化后 `_memory_manager` 不为 `None`
- [ ] 服务启动后调用 `start()` 和 `load_conversation()`
- [ ] 服务停止后调用 `stop()`
- [ ] 长期记忆可以正常写入和读取

### 必须实现
- 正确的 MemoryManager 实例化
- 后台任务的生命周期管理
- 历史对话的加载和保存

### 必须避免
- 破坏现有功能
- 引入新的错误

---

## Verification Strategy

### 测试决策
- **基础设施存在**: YES（pytest）
- **自动化测试**: YES（Tests-after）
- **框架**: pytest

### QA 策略
每个任务必须包含 Agent-Executed QA 场景验证。

---

## Execution Strategy

### 执行顺序

```
顺序执行：
├── Task 1: 修复 _init_memory_manager() 方法
├── Task 2: 修改 start() 方法
├── Task 3: 修改 stop() 方法  
└── Task 4: 验证功能
```

---

## TODOs

- [ ] 1. 修复 `_init_memory_manager()` 方法

  **需要做**：
  - 修改 `src/app/service.py:78-86` 中的 `_init_memory_manager()` 方法
  - 从配置读取记忆存储参数（memory_dir, batch_size, flush_interval）
  - 返回正确的 MemoryManager 实例而非 None
  - 添加类型注解 `MemoryManager | None`

  **禁止做**：
  - 硬编码路径或参数
  - 保留 `return None` 的逻辑

  **推荐 Agent Profile**：
  - **Category**: `quick`
  - **Skills**: []

  **并行化**：
  - **可以并行运行**: NO
  - **分组**: 顺序执行
  - **阻塞**: 无
  - **被阻塞**: Task 2, 3, 4

  **引用**：
  - `src/memory/manager.py:46-84` - MemoryManager 类定义和 __init__ 方法
  - `src/app/config.py` - 配置读取方式

  **验收标准**：
  - [ ] `service._memory_manager` 不为 `None`
  - [ ] `type(service._memory_manager)` 为 `MemoryManager`

  **QA 场景**：

  场景：验证 MemoryManager 实例化
    工具：Bash
    步骤：
      1. 运行：`cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "from src.app.service import Service; from src.app.config import Config; config = Config.load(); service = Service(config); print(f'type: {type(service._memory_manager)}'); print(f'is None: {service._memory_manager is None}')"`
    预期结果：`type: <class 'src.memory.manager.MemoryManager'>` 和 `is None: False`
    证据：`.sisyphus/evidence/task-1-verify.md`

- [ ] 2. 修改 `start()` 方法

  **需要做**：
  - 在 `src/app/service.py` 的 `start()` 方法中（145-181行）
  - 在 LLM 和 Agent 初始化完成后
  - 添加调用 `await self._memory_manager.start()` 启动后台任务
  - 添加调用 `self._memory_manager.load_conversation("default")` 加载历史对话
  - 添加日志输出

  **禁止做**：
  - 在 LLM/Agent 初始化前启动 MemoryManager

  **推荐 Agent Profile**：
  - **Category**: `quick`
  - **Skills**: []

  **并行化**：
  - **可以并行运行**: NO
  - **分组**: 顺序执行
  - **阻塞**: Task 1
  - **被阻塞**: Task 3, 4

  **引用**：
  - `src/app/service.py:145-181` - start() 方法现有实现
  - `src/memory/manager.py:88-91` - start() 方法定义

  **验收标准**：
  - [ ] 服务启动时调用 `memory_manager.start()`
  - [ ] 服务启动时调用 `load_conversation("default")`
  - [ ] 日志正确输出

  **QA 场景**：

  场景：验证 start() 方法正确调用
    工具：Bash
    步骤：
      1. 运行：`cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
import asyncio
from src.app.service import Service
from src.app.config import Config

async def test():
    config = Config.load()
    service = Service(config)
    await service.start()
    print(f'background_task running: {service._memory_manager._background_task is not None}')
    await service.stop()

asyncio.run(test())
"`
    预期结果：`background_task running: True`
    证据：`.sisyphus/evidence/task-2-verify.md`

- [ ] 3. 修改 `stop()` 方法

  **需要做**：
  - 在 `src/app/service.py` 的 `stop()` 方法中（302-317行）
  - 在清理资源之前
  - 添加调用 `await self._memory_manager.stop()` 停止后台任务
  - 添加日志输出

  **禁止做**：
  - 在 LLM/Agent 清理之后才停止 MemoryManager

  **推荐 Agent Profile**：
  - **Category**: `quick`
  - **Skills**: []

  **并行化**：
  - **可以并行运行**: NO
  - **分组**: 顺序执行
  - **阻塞**: Task 2
  - **被阻塞**: Task 4

  **引用**：
  - `src/app/service.py:302-317` - stop() 方法现有实现
  - `src/memory/manager.py:93-101` - stop() 方法定义

  **验收标准**：
  - [ ] 服务停止时调用 `memory_manager.stop()`
  - [ ] 未刷新的数据被保存到文件
  - [ ] 日志正确输出

  **QA 场景**：

  场景：验证 stop() 方法正确保存数据
    工具：Bash
    步骤：
      1. 运行：`cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
import asyncio
from src.app.service import Service
from src.app.config import Config
from pathlib import Path

async def test():
    config = Config.load()
    service = Service(config)
    await service.start()
    await service._memory_manager.add_message('user', '测试消息')
    await service.stop()
    # 检查文件是否生成
    memory_dir = Path('memory')
    files = list(memory_dir.rglob('*.md'))
    print(f'生成文件数: {len(files)}')
    for f in files:
        print(f'文件: {f}')
        print(f.read_text()[:200])

asyncio.run(test())
"`
    预期结果：生成文件且包含"测试消息"
    证据：`.sisyphus/evidence/task-3-verify.md`

- [ ] 4. 验证长期记忆功能

  **需要做**：
  - 运行现有单元测试确保没有破坏
  - 手动验证长期记忆写入和读取功能
  - 清理测试生成的临时文件

  **推荐 Agent Profile**：
  - **Category**: `quick`
  - **Skills**: []

  **并行化**：
  - **可以并行运行**: NO
  - **分组**: 顺序执行
  - **阻塞**: Task 3
  - **被阻塞**: 无

  **引用**：
  - `tests/test_long_term_memory.py` - 单元测试文件

  **验收标准**：
  - [ ] 现有单元测试全部通过
  - [ ] 长期记忆可以正确写入
  - [ ] 长期记忆可以正确读取
  - [ ] 服务重启后历史消息保留

  **QA 场景**：

  场景：验证完整工作流
    工具：Bash
    步骤：
      1. 运行：`cd /Users/Ray/Documents/trae_projects/minerbot && uv run pytest tests/test_long_term_memory.py -v`
    预期结果：27/27 通过

  场景：验证重启后加载历史
    工具：Bash
    步骤：
      1. 运行：`cd /Users/Ray/Documents/trae_projects/minerbot && uv run python -c "
import asyncio
from src.app.service import Service
from src.app.config import Config

async def test():
    config = Config.load()
    service = Service(config)
    await service.start()
    
    # 第一次：添加消息
    await service._memory_manager.add_message('user', '第一条消息')
    await service._memory_manager.add_message('assistant', '第一条回复')
    await service.stop()
    
    # 第二次：重新加载
    service2 = Service(config)
    await service2.start()
    messages = service2._memory_manager.get_messages()
    print(f'加载的消息数: {len(messages)}')
    for msg in messages:
        print(f'{msg.role}: {msg.content}')
    await service2.stop()

asyncio.run(test())
"`
    预期结果：加载的消息数为 2
    证据：`.sisyphus/evidence/task-4-verify.md`

---

## 最终验证

- [ ] F1. 单元测试全部通过：`uv run pytest tests/test_long_term_memory.py -v`
- [ ] F2. 功能验证通过：长期记忆写入和读取正常工作

---

## Commit 策略

- **Task 1**: YES - `fix(memory): 初始化 MemoryManager 实例`
- **Task 2**: YES - `fix(memory): 启动时加载历史对话`
- **Task 3**: YES - `fix(memory): 停止时保存数据`
- **Task 4**: NO - 验证任务无需提交

---

## Success Criteria

### 验证命令
```bash
# 验证 _memory_manager 不为 None
uv run python -c "from src.app.service import Service; from src.app.config import Config; s = Service(Config.load()); print(s._memory_manager is not None)"
# 预期输出: True

# 运行单元测试
uv run pytest tests/test_long_term_memory.py -v
# 预期输出: 27 passed
```

### 最终检查清单
- [ ] `_init_memory_manager()` 返回正确的 MemoryManager 实例
- [ ] `start()` 方法启动 MemoryManager 后台任务
- [ ] `start()` 方法加载历史对话
- [ ] `stop()` 方法停止 MemoryManager 并保存数据
- [ ] 所有单元测试通过
- [ ] 长期记忆功能正常工作
