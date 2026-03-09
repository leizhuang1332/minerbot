# DeepAgents Backends 详解

本文档详细说明 DeepAgents 的文件系统后端（Backends）用法，基于官方文档整理。

## 一、Backend 概述

Deep Agents 通过文件系统工具（`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`）与后端交互。后端是可插拔的，可以选择不同的存储方式。

```
Filesystem Tools --> Backend --> Storage
```

## 二、不同 Backend 的区别

| Backend | 说明 | 持久化 | Shell 执行 | 适用场景 |
|---------|------|--------|-----------|---------|
| **StateBackend** | 默认后端，存储在 LangGraph 状态中 | 仅当前线程 | ❌ | 临时工作区、草稿板 |
| **FilesystemBackend** | 本地文件系统 | 永久 | ❌ | 本地项目、CI/CD |
| **LocalShellBackend** | 本地文件系统 + Shell | 永久 | ✅ | 本地开发工具 |
| **StoreBackend** | LangGraph Store (Redis/Postgres) | 跨线程 | ❌ | 长期记忆、多线程 |
| **CompositeBackend** | 路由到多个后端 | 混合 | 视路由而定 | 混合存储需求 |

### 2.1 StateBackend (临时)

```python
from deepagents import create_deep_agent

# 默认使用 StateBackend
agent = create_deep_agent()

# 或显式指定
from deepagents.backends import StateBackend
agent = create_deep_agent(
    backend=(lambda rt: StateBackend(rt))
)
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `runtime` | `ToolRuntime` | **必需** | 运行时对象，由 `create_deep_agent` 自动传入 |

**特点:**
- 文件存储在 LangGraph agent state 中
- 仅在当前线程持久化
- 多轮对话共享，但线程结束后丢失
- 子 agent 写入的文件也会保留在 state 中

### 2.2 FilesystemBackend (本地磁盘)

```python
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir="/path/to/dir", virtual_mode=True)
)
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `root_dir` | `str | Path | None` | `None` | 根目录路径，必须为绝对路径 |
| `virtual_mode` | `bool | None` | `None` | 启用沙箱模式，阻止路径逃逸 |
| `max_file_size_mb` | `int` | `10` | 最大文件大小 (MB) |

**特点:**
- 读写真实本地文件
- `root_dir` 必须为绝对路径
- `virtual_mode=True` 启用沙箱模式，阻止 `..`、`~`、绝对路径逃逸
- 支持图片文件读取 (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`)

**⚠️ 安全警告:**
- 直接文件系统读写权限
- 可能读取敏感文件（API keys, .env）
- 建议启用 Human-in-the-Loop (HITL) 中间件

### 2.3 LocalShellBackend (本地 Shell)

```python
from deepagents.backends import LocalShellBackend

agent = create_deep_agent(
    backend=LocalShellBackend(
        root_dir=".",
        env={"PATH": "/usr/bin:/bin"}
    )
)
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `root_dir` | `str | Path | None` | `None` | 根目录路径，必须为绝对路径 |
| `virtual_mode` | `bool | None` | `None` | 沙箱模式（对 Shell 无效） |
| `timeout` | `int` | `120` | 命令执行超时时间 (秒) |
| `max_output_bytes` | `int` | `100000` | 命令输出最大字节数 |
| `env` | `dict[str, str] | None` | `None` | 环境变量 |
| `inherit_env` | `bool` | `False` | 是否继承当前进程环境变量 |

**特点:**
- 继承 FilesystemBackend 所有功能
- 额外提供 `execute` 工具执行 shell 命令
- 使用 `subprocess.run(shell=True)` 无沙箱执行
- `virtual_mode=True` 对 Shell 无效，命令可访问系统任意路径

**⚠️ 严重安全警告:**
- 可执行任意 shell 命令
- 无限 CPU/内存/磁盘消耗
- **禁止**在生产环境使用

#### FilesystemBackend vs LocalShellBackend 对比

| 对比项 | FilesystemBackend | LocalShellBackend |
|--------|-------------------|-------------------|
| **适用场景** | 本地项目开发、CI/CD、需要文件系统交互 | 信任的本地开发环境、需要执行系统命令 |
| **文件读取** | ✅ 支持 (`read_file`) | ✅ 支持 |
| **文件写入** | ✅ 支持 (`write_file`) | ✅ 支持 |
| **文件编辑** | ✅ 支持 (`edit_file`) | ✅ 支持 |
| **目录列表** | ✅ 支持 (`ls`) | ✅ 支持 |
| **文件搜索** | ✅ 支持 (`grep`, `glob`) | ✅ 支持 |
| **执行 Shell** | ❌ 不支持 | ✅ 支持 (`execute`) |

**LocalShellBackend 可执行的命令类型:**

```python
# LocalShellBackend 额外提供 execute 工具，可以执行：

# 1. 任意 shell 命令
"ls -la"
"git status"
"python script.py"

# 2. 管道和重定向
"cat file.txt | grep pattern > output.txt"

# 3. 环境变量操作
export VAR=value && command

# 4. 脚本执行
"bash script.sh"
"node index.js"
"npm run build"
```

**安全性对比:**

| 安全特性 | FilesystemBackend | LocalShellBackend |
|----------|-------------------|-------------------|
| `virtual_mode` 沙箱 | ✅ 有效 | ❌ 无效 |
| 路径访问限制 | ✅ 可限制 | ❌ 无法限制 |
| 命令执行控制 | ❌ 不适用 | ❌ 无限制 |
| 读取敏感文件风险 | ⚠️ 中（需注意） | 🔴 高 |
| 执行破坏性命令风险 | N/A | 🔴 极高 |

**结论:**
- **FilesystemBackend**: 推荐用于需要文件系统操作的所有场景，配合 `virtual_mode=True` 提供基本安全保障
- **LocalShellBackend**: 仅推荐用于**完全信任的本地开发环境**，agent 可执行任意命令等同于用户亲自操作

### 2.4 StoreBackend (LangGraph Store)

```python
from langgraph.store.memory import InMemoryStore
from deepagents.backends import StoreBackend

agent = create_deep_agent(
    backend=(lambda rt: StoreBackend(rt)),
    store=InMemoryStore()  # 本地开发；生产环境可省略
)
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `runtime` | `ToolRuntime` | **必需** | 运行时对象，由 `create_deep_agent` 自动传入 |
| `namespace` | `Callable | None` | `None` | 命名空间映射函数 |

**特点:**
- 跨线程持久化存储
- 支持 Redis、Postgres、云存储
- 部署到 LangSmith Deployment 时自动配置

### 2.5 CompositeBackend (路由)

```python
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend

composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/memories/": FilesystemBackend(root_dir="/path/to/memories", virtual_mode=True),
    }
)

agent = create_deep_agent(backend=composite_backend)
```

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `default` | `BackendProtocol` | **必需** | 默认后端，用于未匹配路由的路径 |
| `routes` | `dict[str, BackendProtocol]` | **必需** | 路径前缀到后端的映射 |

**特点:**
- 根据路径前缀路由到不同后端
- 长前缀优先匹配
- 支持聚合 `ls`, `glob`, `grep` 结果

---

## 三、问题解答

### 3.1 Local filesystem persistence 是否可以访问该方式指定的目录下的所有文件夹及文件?

**是的**，FilesystemBackend 可以访问 `root_dir` 下的所有文件夹和文件。

```python
from deepagents.backends import FilesystemBackend

# 设置 root_dir 为项目根目录
agent = create_deep_agent(
    backend=FilesystemBackend(root_dir="/Users/Ray/Documents/myproject", virtual_mode=True)
)
```

**访问范围:**
- ✅ 可以读取 `root_dir` 下的所有文件
- ✅ 可以写入新文件到 `root_dir`
- ✅ 可以编辑 `root_dir` 下的现有文件
- ✅ 可以列出目录内容 (`ls`)
- ✅ 可以搜索文件 (`grep`, `glob`)

**安全建议:**
- 使用 `virtual_mode=True` 阻止路径逃逸
- 不要设置 `root_dir` 为敏感目录（如 `/`, `~`, home 目录）
- 排除 `.env`, `.ssh`, `.aws` 等敏感路径

### 3.2 能不能同时指定多个 Backend?

**可以**，使用 `CompositeBackend` 实现多后端路由。

#### 基本语法

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend

# 定义复合后端
composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),  # 默认使用临时存储
    routes={
        "/memories/": FilesystemBackend(root_dir="/path/to/memories", virtual_mode=True),
    }
)

agent = create_deep_agent(backend=composite_backend)
```

#### 完整示例：混合存储

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

# 复合后端配置
def create_composite_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),  # 默认临时存储
        routes={
            "/workspace/": FilesystemBackend(
                root_dir="/Users/Ray/Documents/workspace", 
                virtual_mode=True
            ),
            "/memories/": StoreBackend(runtime),  # 长期记忆
            "/temp/": StateBackend(runtime),  # 显式临时存储
        }
    )

agent = create_deep_agent(
    backend=create_composite_backend,
    store=InMemoryStore()
)
```

#### 路由规则

| 路径 | 路由目标 |
|------|---------|
| `/workspace/file.txt` | FilesystemBackend |
| `/memories/agent.md` | StoreBackend |
| `/temp/cache.txt` | StateBackend |
| `/other/file.txt` | StateBackend (default) |

**注意:**
- 路径必须以 `/` 结尾（目录）或作为文件前缀
- 长前缀优先：`/memories/projects/` 优先于 `/memories/`

---

## 四、后端选择指南

### 4.1 场景对比

| 场景 | 推荐后端 | 原因 |
|------|---------|------|
| 本地开发 CLI | FilesystemBackend | 直接文件系统访问 |
| 需要长期记忆 | StoreBackend | 跨线程持久化 |
| 临时草稿板 | StateBackend | 无需持久化 |
| 混合需求 | CompositeBackend | 灵活路由 |
| 沙箱环境 | Sandbox | 隔离执行 |
| 信任的本地开发 | LocalShellBackend | Shell 执行 |

### 4.2 安全建议

| 后端 | 安全等级 | 建议 |
|------|---------|------|
| StateBackend | 高 | 默认安全 |
| StoreBackend | 高 | 生产环境使用 |
| FilesystemBackend | 中 | virtual_mode=True + HITL |
| LocalShellBackend | 低 | 仅本地开发 |
| Sandbox | 高 | 生产环境首选 |

---

## 五、自定义 Backend

可以通过实现 `BackendProtocol` 创建自定义后端：

```python
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult
from deepagents.backends.utils import FileInfo, GrepMatch

class MyBackend(BackendProtocol):
    def __init__(self, ...):
        ...
    
    def ls_info(self, path: str) -> list[FileInfo]:
        ...
    
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        ...
    
    def grep_raw(self, pattern: str, path: str = None, glob: str = None) -> list[GrepMatch] | str:
        ...
    
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        ...
    
    def write(self, file_path: str, content: str) -> WriteResult:
        ...
    
    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        ...
```

---

## 六、相关资源

- [官方 Backends 文档](https://docs.langchain.com/oss/python/deepagents/backends)
- [Sandboxes 文档](/oss/python/deepagents/sandboxes)
- [Human-in-the-Loop](/oss/python/deepagents/human-in-the-loop)
