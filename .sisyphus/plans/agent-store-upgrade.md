# Agent Store 升级实施计划

## 概述

将 MinerBot agent 的长期存储从 `InMemoryStore` 升级为 `AsyncSqliteStore`，实现数据的持久化存储。

---

## 实施任务

### 阶段 1：依赖确认

- [x] **T1.1** 确认 `langgraph-checkpoint-sqlite` 已包含 `AsyncSqliteStore`

### 阶段 2：配置扩展（可选）

- [ ] **T2.1** config.py - 可选：新增 `store_db_path` 配置项（默认复用 `sqlite_db_path`）

### 阶段 3：SessionManager 改造

- [x] **T3.1** session.py - 新增导入 `AsyncSqliteStore`
- [x] **T3.2** session.py - 新增 `store: AsyncSqliteStore` 属性
- [x] **T3.3** session.py - 修改 `create` 方法：同时初始化 checkpointer 和 store
- [x] **T3.4** session.py - 修改 `close` 方法：关闭 store 连接

### 阶段 4：Factory 改造

- [x] **T4.1** factory.py - 修改导入：`AsyncSqliteStore`（移除 `InMemoryStore`）
- [x] **T4.2** factory.py - 修改 `create_agent`：接受可选 store 参数
- [x] **T4.3** factory.py - 修改 `create_agent_with_session`：传递 store 到 agent

### 阶段 5：测试与验证

- [x] **T5.1** 运行现有功能，确保无回归
- [x] **T5.2** 手动测试：存储数据 → 重启 → 验证数据存在

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
