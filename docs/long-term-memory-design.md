# MinerBot 长期记忆功能设计方案

## 一、现状确认

### 1.1 问题确认

经过源码分析，确认当前项目**没有实现长期记忆功能**：

| 位置 | 当前实现 | 问题 |
|------|----------|------|
| `src/app/service.py:77` | `self._checkpointer = MemorySaver()` | 内存存储，服务重启后丢失 |
| `src/app/service.py:195-198` | 使用 session_id 区分会话 | 只在单次运行期间有效 |
| `src/agents/agent_factory.py:199-204` | 支持 checkpointer 参数 | 未配置持久化后端 |

**核心问题**：虽然代码配置了 `MemorySaver`，但这是内存存储，不是持久化的。

### 1.2 用户需求

| 需求 | 说明 |
|------|------|
| 退出再打开仍有对话 | 需要持久化存储 |
| 不区分用户 | 单人使用场景，简化为单一存储 |
| 使用 DeepAgents 框架 | 优先复用框架组件 |
| Markdown 文件存储 | 按日期生成子文件夹在 memory/ 下 |

---

## 二、短期记忆与长期记忆共存分析

### 2.1 两种记忆的本质区别

| 特性 | 短期记忆 (Checkpointer) | 长期记忆 (Store) |
|------|------------------------|-----------------|
| **作用** | 当前会话的对话历史 | 跨会话的持久化信息 |
| **粒度** | 消息级别 (messages) | 结构化数据 (key-value) |
| **生命周期** | 会话期间 | 永久 |
| **DeepAgents 组件** | `checkpointer` | `store` |
| **数据存储** | 内存/SQLite/Postgres | 内存/SQLite/Redis |

### 2.2 共存架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        MinerBot 应用层                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Service 层                             │   │
│  │  - MemoryManager (新增)                                  │   │
│  │  - SessionManager (现有)                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              DeepAgents Agent                            │   │
│  │                                                              │   │
│  │  ┌─────────────────┐    ┌─────────────────┐             │   │
│  │  │  Checkpointer   │    │     Store      │             │   │
│  │  │  (短期记忆)      │    │   (长期记忆)    │             │   │
│  │  │                 │    │                 │             │   │
│  │  │  - MemorySaver  │    │ - InMemoryStore │             │   │
│  │  │  - SqliteSaver  │    │ - SqliteStore   │             │   │
│  │  └─────────────────┘    └─────────────────┘             │   │
│  │         │                        │                      │   │
│  │         ▼                        ▼                      │   │
│  │  ┌─────────────────┐    ┌─────────────────┐             │   │
│  │  │  thread_id      │    │   namespace/     │             │   │
│  │  │  区分会话       │    │   key 索引      │             │   │
│  │  └─────────────────┘    └─────────────────┘             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              本地文件系统 (memory/)                       │   │
│  │                                                              │   │
│  │  memory/                                                    │   │
│  │  ├── checkpoints.db     # Checkpointer SQLite 存储        │   │
│  │  └── conversations/      # Markdown 对话记录               │   │
│  │      └── 2026-03-12/                                     │   │
│  │          └── conversation_default.md                      │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 共存数据流

```
用户输入 "你好"
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  1. 短期记忆 (Checkpointer)                                   │
│     - 根据 thread_id 加载历史对话                              │
│     - 将新消息添加到历史                                      │
│     - 自动保存到 checkpointer                                 │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  2. Agent 处理                                                │
│     - 接收完整的历史消息 + 新输入                              │
│     - 生成响应                                                │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│  3. 长期记忆 (Store / Markdown)                              │
│     - 后台异步写入 Markdown 文件                               │
│     - 不阻塞用户响应                                          │
└──────────────────────────────────────────────────────────────┘
```

### 2.4 结论

**短期记忆和长期记忆完全可以共存，且各自负责不同的职责：**

| 记忆类型 | 职责 | 存储位置 |
|----------|------|----------|
| **短期记忆** | 当前会话的完整对话历史 | Checkpointer (SQLite/内存) |
| **长期记忆** | 跨会话的对话备份/检索 | Markdown 文件 |

**共存策略**：
1. 短期记忆负责**运行时**的对话上下文管理
2. 长期记忆负责**持久化**的对话备份和跨会话检索
3. 两者互不干扰，独立运作

---

## 三、DeepAgents 长期记忆组件规范

### 3.1 Store 组件概述

DeepAgents 通过 `store` 参数支持长期记忆，功能基于 **LangGraph Store** 实现。

### 3.2 API 签名

```python
from deepagents import create_deep_agent
from langgraph.store.memory import InMemoryStore
from langgraph.store.sqlite import SqliteStore

# 方式1：内存存储（开发用）
store = InMemoryStore()

# 方式2：SQLite 持久化（生产用）
store = SqliteStore.from_path("./memory_store.db")

# 创建 Agent 时传入 store
agent = create_deep_agent(
    model="minimax:abab6.5s",
    store=store,  # ← 长期记忆存储
)
```

### 3.3 入参格式

#### 3.3.1 store.put() - 存储数据

```python
# 签名
store.put(namespace: tuple[str, ...], key: str, value: dict) -> None

# 参数说明
namespace:  # 命名空间，元组形式，用于分类存储
    示例: ("user_preferences",) 
         ("conversation_history", "default")
    
key: str    # 键名，唯一标识
    示例: "preferences"
         "2026-03-12-default"

value: dict # 值，任意字典结构
    示例: {"messages": [...], "created_at": "..."}
         {"preference": "dark_mode", "language": "zh-CN"}

# 示例
store.put(
    namespace=("conversations", "default"),
    key="2026-03-12",
    value={
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮你的？"}
        ],
        "message_count": 2,
        "created_at": "2026-03-12T21:30:00"
    }
)
```

#### 3.3.2 store.get() - 获取数据

```python
# 签名
store.get(namespace: tuple[str, ...], key: str) -> Item | None

# 返回类型
class Item:
    key: str           # 键名
    value: dict        # 存储的值
    namespace: tuple   # 命名空间
    created_at: datetime
    updated_at: datetime

# 示例
result = store.get(
    namespace=("conversations", "default"),
    key="2026-03-12"
)

if result:
    print(result.value)  # {"messages": [...], ...}
```

#### 3.3.3 store.search() - 搜索数据

```python
# 签名
store.search(
    namespace: tuple[str, ...],
    filter: dict | None = None,
    limit: int = 10
) -> list[Item]

# 参数说明
filter:  # 可选的过滤条件
    示例: {"role": "user"}  # 过滤包含特定字段的项
    示例: {"$gt": {"message_count": 10}}  # 数值比较

limit: int  # 返回结果数量限制

# 示例
results = store.search(
    namespace=("conversations", "default"),
    filter=None,
    limit=5
)

for item in results:
    print(f"{item.key}: {item.value}")
```

### 3.4 出参格式

```python
# store.get() / store.search() 返回的 Item 对象

class Item:
    """存储项"""
    key: str                          # 键名
    value: dict                        # 存储的值（Python dict）
    namespace: tuple[str, ...]         # 命名空间
    created_at: datetime              # 创建时间
    updated_at: datetime              # 更新时间

# 访问方式
item.key           # "2026-03-12"
item.value         # {"messages": [...], ...}
item.namespace     # ("conversations", "default")
item.created_at    # datetime(2026, 3, 12, 21, 30, 00)
```

### 3.5 完整使用示例

```python
from deepagents import create_deep_agent
from langgraph.store.sqlite import SqliteStore

# 1. 创建持久化 Store
store = SqliteStore.from_path("./memory_store.db")

# 2. 创建 Agent
agent = create_deep_agent(
    model="minimax:abab6.5s",
    store=store,
)

# 3. 存储对话历史
conversation_data = {
    "messages": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！"}
    ],
    "message_count": 2,
    "last_active": "2026-03-12T21:30:00"
}

store.put(
    namespace=("conversations", "default"),
    key="2026-03-12",
    value=conversation_data
)

# 4. 读取对话历史
item = store.get(
    namespace=("conversations", "default"),
    key="2026-03-12"
)

if item:
    print(item.value["messages"])
```

---

## 四、长期记忆写入策略设计

### 4.1 核心要求

**用户明确要求**：不能实时写入 Markdown 文件，会导致用户问答延迟太高。

### 4.2 写入策略对比

| 策略 | 原理 | 优点 | 缺点 | 推荐 |
|------|------|------|------|------|
| **实时写入** | 每次对话后立即写入文件 | 数据不丢失 | 阻塞响应，体验差 | ❌ |
| **后台异步写入** | 新开协程写入，不阻塞主流程 | 不阻塞响应 | 有丢失风险（异常时） | ✅ |
| **批量写入** | 积累 N 条消息后写入 | 减少 IO 次数 | 实时性较低 | ✅ |
| **定时写入** | 固定时间间隔写入 | 可预测 | 实时性低 | ⚠️ |
| **退出时写入** | 程序退出时保存 | 简单可靠 | 异常退出可能丢失 | ⚠️ |

### 4.3 推荐策略：后台异步 + 批量写入

结合后台异步和批量写入，既保证响应速度，又降低数据丢失风险。

```
用户输入 → Agent 处理 → 返回响应 → 后台任务队列
                                              ↓
                            ┌─────────────────┴─────────────────┐
                            ▼                                   ▼
                     批量缓冲区                        定时检查点
                     (内存队列)                         (定期保存)
                            │                                   │
                            ▼                                   ▼
                     达到阈值写入                      定时触发写入
                     (如 10 条消息)                     (如 30 秒)
```

### 4.4 详细实现设计

#### 4.4.1 MemoryManager 架构

```python
# src/memory/manager.py

import asyncio
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from queue import Queue
import atexit


@dataclass
class Message:
    """单条消息"""
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass 
class Conversation:
    """对话对象"""
    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    dirty: bool = False  # 是否有未保存的修改


class MemoryManager:
    """长期记忆管理器
    
    采用后台异步 + 批量写入策略：
    1. 消息先添加到内存缓冲区
    2. 达到批量阈值或定时触发时写入文件
    3. 程序退出时强制保存
    """
    
    def __init__(
        self, 
        memory_dir: str = "memory",
        batch_size: int = 10,        # 批量写入阈值
        flush_interval: float = 30.0  # 定时刷新间隔（秒）
    ):
        """初始化
        
        Args:
            memory_dir: 记忆存储根目录
            batch_size: 达到此数量的消息后触发写入
            flush_interval: 定时写入间隔（秒）
        """
        self._memory_dir = Path(memory_dir)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        
        self._current_conversation: Optional[Conversation] = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._background_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # 注册退出时保存
        atexit.register(self._sync_flush_on_exit)
    
    # ========== 生命周期管理 ==========
    
    async def start(self) -> None:
        """启动后台写入任务"""
        self._shutdown_event.clear()
        self._background_task = asyncio.create_task(self._background_writer())
    
    async def stop(self) -> None:
        """停止后台任务并保存所有数据"""
        self._shutdown_event.set()
        
        if self._background_task:
            # 先保存当前数据
            await self._flush_to_file()
            # 等待后台任务结束
            await self._background_task
    
    def _sync_flush_on_exit(self) -> None:
        """同步刷新（退出时调用）"""
        # 同步版本的保存逻辑
        if self._current_conversation and self._current_conversation.dirty:
            try:
                self._save_to_file_sync()
            except Exception as e:
                print(f"退出时保存记忆失败: {e}")
    
    # ========== 核心方法 ==========
    
    def load_conversation(self, conversation_id: str = "default") -> Conversation:
        """加载对话历史"""
        file_path = self._get_conversation_file(conversation_id)
        
        if not file_path.exists():
            conversation = Conversation(id=conversation_id)
            self._current_conversation = conversation
            return conversation
        
        conversation = self._parse_markdown_file(file_path)
        conversation.id = conversation_id
        self._current_conversation = conversation
        return conversation
    
    async def add_message(self, role: str, content: str) -> None:
        """添加消息（异步，不阻塞）"""
        if self._current_conversation is None:
            self._current_conversation = Conversation(id="default")
        
        message = Message(role=role, content=content)
        self._current_conversation.messages.append(message)
        self._current_conversation.last_active = datetime.now()
        self._current_conversation.dirty = True
        
        # 不直接写入文件，而是添加到队列
        await self._message_queue.put(message)
    
    def get_messages(self) -> List[Message]:
        """获取当前对话的所有消息"""
        if self._current_conversation is None:
            return []
        return self._current_conversation.messages
    
    # ========== 后台写入逻辑 ==========
    
    async def _background_writer(self) -> None:
        """后台写入协程"""
        last_flush_time = datetime.now()
        pending_messages: List[Message] = []
        
        while not self._shutdown_event.is_set():
            try:
                # 等待新消息，有超时
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=1.0
                    )
                    pending_messages.append(message)
                except asyncio.TimeoutError:
                    pass
                
                # 检查是否需要写入
                now = datetime.now()
                time_since_flush = (now - last_flush_time).total_seconds()
                
                # 达到批量阈值 或 达到定时间隔
                if (len(pending_messages) >= self._batch_size or 
                    time_since_flush >= self._flush_interval):
                    
                    if pending_messages:
                        await self._flush_to_file()
                        pending_messages = []
                        last_flush_time = now
                        
            except Exception as e:
                print(f"后台写入错误: {e}")
                await asyncio.sleep(1)
        
        # 关闭前最后的保存
        if pending_messages:
            await self._flush_to_file()
    
    async def _flush_to_file(self) -> None:
        """将内存数据刷新到文件"""
        if self._current_conversation is None:
            return
            
        if not self._current_conversation.dirty:
            return
        
        # 在线程池中执行文件 IO，避免阻塞事件循环
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_to_file_sync)
        
        self._current_conversation.dirty = False
    
    def _save_to_file_sync(self) -> None:
        """同步保存到文件"""
        if self._current_conversation is None:
            return
            
        file_path = self._get_conversation_file(self._current_conversation.id)
        markdown_content = self._conversation_to_markdown(self._current_conversation)
        file_path.write_text(markdown_content, encoding="utf-8")
    
    # ========== 辅助方法 ==========
    
    def _get_date_dir(self, date: Optional[datetime] = None) -> Path:
        """获取日期目录"""
        date = date or datetime.now()
        date_dir = self._memory_dir / date.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    def _get_conversation_file(self, conversation_id: str = "default") -> Path:
        """获取对话文件路径"""
        date_dir = self._get_date_dir()
        return date_dir / f"conversation_{conversation_id}.md"
    
    def _parse_markdown_file(self, file_path: Path) -> Conversation:
        """解析 Markdown 文件"""
        content = file_path.read_text(encoding="utf-8")
        messages = []
        
        lines = content.split("\n")
        current_role = None
        current_content = []
        current_time = None
        
        for line in lines:
            line = line.rstrip()
            
            if line.startswith("### 用户 ") or line.startswith("### 助手 "):
                if current_role and current_content:
                    messages.append(Message(
                        role=current_role,
                        content="\n".join(current_content),
                        timestamp=current_time or datetime.now()
                    ))
                
                if "用户" in line:
                    current_role = "user"
                else:
                    current_role = "assistant"
                
                try:
                    time_str = line.split("(")[1].split(")")[0]
                    current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                except:
                    current_time = datetime.now()
                
                current_content = []
            elif current_role:
                current_content.append(line)
        
        if current_role and current_content:
            messages.append(Message(
                role=current_role,
                content="\n".join(current_content),
                timestamp=current_time or datetime.now()
            ))
        
        return Conversation(
            id="default",
            messages=messages
        )
    
    def _conversation_to_markdown(self, conversation: Conversation) -> str:
        """将 Conversation 对象转换为 Markdown 格式"""
        lines = ["# 对话记录", ""]
        
        lines.append(f"- **创建时间**: {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **最后活跃**: {conversation.last_active.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **消息数量**: {len(conversation.messages)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 对话历史")
        lines.append("")
        
        for msg in conversation.messages:
            role_label = "用户" if msg.role == "user" else "助手"
            lines.append(f"### {role_label} ({msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")
        
        return "\n".join(lines)
```

#### 4.4.2 Service 层集成

```python
# src/app/service.py 修改方案

from src.memory.manager import MemoryManager

class Service:
    def __init__(self, config: Config) -> None:
        # ... 现有代码 ...
        
        # 初始化长期记忆管理器（后台异步写入）
        self._memory_manager = MemoryManager(
            memory_dir="memory",
            batch_size=10,        # 10 条消息触发写入
            flush_interval=30.0  # 或 30 秒触发写入
        )
    
    async def start(self) -> None:
        # ... 现有代码 ...
        
        # 启动后台写入任务
        await self._memory_manager.start()
        
        # 加载历史对话（启动时加载）
        self._memory_manager.load_conversation("default")
    
    async def run(self, input_data: Any, timeout: float | None = None) -> Any:
        # ... 现有代码 ...
        
        # 添加用户消息到长期记忆（异步，不阻塞）
        await self._memory_manager.add_message("user", input_data)
        
        # 调用 Agent
        result = await self._agent.ainvoke(...)
        
        # 添加助手回复到长期记忆（异步，不阻塞）
        result_content = self._extract_content(result)
        await self._memory_manager.add_message("assistant", result_content)
        
        return result
    
    async def stop(self) -> None:
        # ... 现有代码 ...
        
        # 停止长期记忆管理器（保存所有数据）
        await self._memory_manager.stop()
```

### 4.5 写入时机总结

| 触发条件 | 时机 | 说明 |
|----------|------|------|
| **批量达到** | 积累 10 条消息 | 主要写入时机 |
| **定时触发** | 每 30 秒 | 兜底写入时机 |
| **服务停止** | `stop()` 调用时 | 确保数据不丢失 |
| **程序异常退出** | `atexit` 回调 | 最后保障 |

**数据流程**：
```
用户消息 → 内存缓冲区 → [批量/定时/退出] → Markdown 文件
     │              │
     └──── 响应用户 ← (不等待写入完成)
```

---

## 五、存储格式

### 5.1 目录结构

```
memory/
├── 2026-03-09/
│   └── conversation_default.md
├── 2026-03-10/
│   └── conversation_default.md
├── 2026-03-11/
│   └── conversation_default.md
└── 2026-03-12/
    └── conversation_default.md
```

### 5.2 Markdown 内容格式

```markdown
# 对话记录

- **创建时间**: 2026-03-12 21:30:00
- **最后活跃**: 2026-03-12 22:15:00
- **消息数量**: 6

---

## 对话历史

### 用户 (2026-03-12 21:30:00)
你好，我想让你帮我写一个排序算法

### 助手 (2026-03-12 21:30:02)
好的，我可以帮你实现排序算法。你想要哪种排序算法？快速排序、归并排序还是冒泡排序？

### 用户 (2026-03-12 21:31:00)
帮我写一个快速排序吧

### 助手 (2026-03-12 21:31:03)
好的，这是快速排序的 Python 实现：

```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

### 用户 (2026-03-12 21:32:00)
很好，再帮我写一个归并排序

### 助手 (2026-03-12 21:32:05)
好的，这是归并排序的 Python 实现：
...
```

---

## 六、实施计划

### 6.1 任务分解

| 序号 | 任务 | 文件 | 工作量 |
|------|------|------|--------|
| 1 | 创建 MemoryManager 类（后台异步写入） | `src/memory/manager.py` | 1.5h |
| 2 | 导出 MemoryManager | `src/memory/__init__.py` | 0.5h |
| 3 | 集成到 Service 层 | `src/app/service.py` | 1h |
| 4 | 单元测试 | `tests/test_long_term_memory.py` | 1h |

### 6.2 文件变更

```
修改/新增文件:
├── src/memory/
│   ├── __init__.py          # 修改：导出 MemoryManager
│   ├── manager.py           # 新增：长期记忆管理器（后台异步）
│   └── session.py           # 保留：会话管理（短期）
├── src/app/
│   └── service.py           # 修改：集成 MemoryManager
└── tests/
    └── test_long_term_memory.py  # 新增：长期记忆测试
```

---

## 七、配置说明

### 7.1 可配置项

```python
# src/app/config.py 或 config/agent_config.yaml

memory:
  # 记忆存储目录
  dir: "memory"
  
  # 对话ID（不区分用户时使用 default）
  conversation_id: "default"
  
  # 批量写入阈值（达到此数量消息后写入）
  batch_size: 10
  
  # 定时写入间隔（秒）
  flush_interval: 30
```

---

## 八、注意事项

1. **并发安全**：消息队列和文件写入需要考虑并发问题，上述方案使用 asyncio 队列解决

2. **异常处理**：后台写入失败时不应影响主流程，但需要记录日志

3. **文件增长**：长期运行后 Markdown 文件会很大，可以考虑：
   - 按会话分文件存储
   - 定期归档旧对话
   - 实现对话摘要功能

4. **编码问题**：确保使用 UTF-8 编码读写文件

---

## 九、总结

| 项目 | 说明 |
|------|------|
| 需求确认 | ✅ 确认当前没有长期记忆功能 |
| 短期/长期记忆共存 | ✅ 可共存，各自负责不同职责 |
| 写入时机 | ✅ 后台异步 + 批量写入，不阻塞响应 |
| 技术方案 | 使用本地 Markdown 文件存储 + LangGraph Store |
| 存储位置 | `memory/YYYY-MM-DD/conversation_default.md` |
| 实现复杂度 | 中等，需要修改 Service 层集成 |
| DeepAgents 复用 | 继续使用 checkpointer 管理状态，MemoryManager 处理持久化 |

---

*文档版本: v2.0*  
*更新日期: 2026-03-12*  
*更新内容: 
1. 新增短期记忆与长期记忆共存分析
2. 详细设计后台异步写入策略
3. 补充 DeepAgents Store 组件出入参规范*
