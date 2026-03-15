# Agent Store 升级开发计划

## 概述

将 MinerBot agent 的长期存储从 `InMemoryStore` 升级为 `AsyncSqliteStore`，实现数据的持久化存储。

---

## 当前状态

| 项目 | 状态 |
|------|------|
| Checkpointer | ✅ 已使用 AsyncSqliteSaver + SQLite |
| Store | ❌ 使用 InMemoryStore（内存） |

---

## 改造方案

### 核心策略

**最小化改动 + 统一连接管理**：复用现有的 SessionManager 架构，在 session.py 中同时管理 checkpointer 和 store 的 SQLite 连接。

### 架构变更

```
改造前:
SessionManager ──→ AsyncSqliteSaver (checkpointer)
create_agent ──→ InMemoryStore (store, 内存)

改造后:
SessionManager ──→ AsyncSqliteSaver (checkpointer)
                 ──→ AsyncSqliteStore (store, SQLite)
create_agent ──→ AsyncSqliteStore (store)
```

---

## 开发任务

### 阶段 1：准备

| 任务 | 文件 | 描述 |
|------|------|------|
| T1.1 | - | 确认依赖：`langgraph-checkpoint-sqlite` 已包含 AsyncSqliteStore |

### 阶段 2：配置扩展

| 任务 | 文件 | 描述 |
|------|------|------|
| T2.1 | config.py | 可选：新增 `store_db_path` 配置项（默认复用 `sqlite_db_path`） |

### 阶段 3：SessionManager 改造

| 任务 | 文件 | 描述 |
|------|------|------|
| T3.1 | session.py | 新增 `store: AsyncSqliteStore` 属性 |
| T3.2 | session.py | 修改 `create` 方法：同时初始化 checkpointer 和 store |
| T3.3 | session.py | 修改 `close` 方法：关闭 store 连接 |

### 阶段 4：Factory 改造

| 任务 | 文件 | 描述 |
|------|------|------|
| T4.1 | factory.py | 修改导入：`AsyncSqliteStore` |
| T4.2 | factory.py | 修改 `create_agent`：接受可选 store 参数 |
| T4.3 | factory.py | 修改 `create_agent_with_session`：传递 store 到 agent |

### 阶段 5：测试与验证

| 任务 | 描述 |
|------|------|
| T5.1 | 运行现有功能，确保无回归 |
| T5.2 | 手动测试：存储数据 → 重启 → 验证数据存在 |

---

## 代码改动预览

### session.py 改动

```python
# 新增导入
from langgraph.store.sqlite.aio import AsyncSqliteStore

@dataclass
class SessionManager:
    checkpointer: AsyncSqliteSaver
    store: AsyncSqliteStore  # 新增
    _conn: aiosqlite.Connection
    
    @classmethod
    async def create(cls, config: AppConfig) -> "SessionManager":
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = await aiosqlite.connect(str(db_path))
        checkpointer = AsyncSqliteSaver(conn)
        
        # 新增：初始化 store
        store = AsyncSqliteStore(conn)
        await store.setup()
        
        return cls(checkpointer=checkpointer, store=store, _conn=conn)
    
    async def close(self):
        # 新增：关闭 store（与 checkpointer 共用连接）
        await self._conn.close()
```

### factory.py 改动

```python
# 修改前
from langgraph.store.memory import InMemoryStore

return create_deep_agent(
    ...
    store=InMemoryStore(),
)

# 修改后
from langgraph.store.sqlite.aio import AsyncSqliteStore

def create_agent(..., store: AsyncSqliteStore = None):
    return create_deep_agent(
        ...
        store=store,  # 外部传入或默认 None
    )

async def create_agent_with_session(config: AppConfig):
    session_mgr = await SessionManager.create(config)
    agent = create_agent(config, store=session_mgr.store, 
                        checkpointer=session_mgr.checkpointer)
    return agent, session_mgr
```

---

## 风险与缓解

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| DeepAgents 内部同步调用 store | 高 | 使用同步/异步双接口，或检查 deepagents 版本兼容性 |
| 数据库连接未正确关闭 | 中 | 确保 CLI 的 finally 块正确调用 close |
| 现有功能破坏 | 高 | 保持向后兼容，store 参数可选 |

---

## 验证方法

### 功能验证

```bash
# 1. 启动应用并对话
uv run python -m minerbot

# 2. 存储一些数据（通过对话或 API）

# 3. 关闭应用
exit

# 4. 重启应用，验证之前的数据仍可访问
uv run python -m minerbot
```

### 数据库验证

```bash
# 查看 SQLite 数据库文件
ls -la data/

# 使用 sqlite3 查看表结构
sqlite3 data/minerbot.db ".tables"
```

---

## 实施顺序

1. **T3.1-T3.3**：修改 SessionManager（核心改动）
2. **T4.1-T4.3**：修改 Factory
3. **T2.1**：配置扩展（可选）
4. **T5.1-T5.2**：测试验证

---

## 预计工作量

| 阶段 | 任务数 | 预估时间 |
|------|--------|----------|
| 准备 | 1 | 5 分钟 |
| 配置 | 1 | 10 分钟 |
| SessionManager | 3 | 30 分钟 |
| Factory | 3 | 20 分钟 |
| 测试 | 2 | 30 分钟 |
| **总计** | **10** | **约 2 小时** |
