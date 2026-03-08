# 后台服务生命周期管理

## TL;DR

> **快速摘要**: 实现终端交互式 REPL 后台服务，支持多轮对话，通过 asyncio 异步处理请求，配置通过 YAML 文件管理
> 
> **交付物**:
> - `src/main.py` - 主程序入口
> - `src/app/__init__.py` - app 模块导出
> - `src/app/config.py` - 配置加载和管理
> - `src/app/service.py` - 服务生命周期管理
> - `src/app/repl.py` - REPL 交互逻辑
> - `config/app_config.yaml` - 服务配置文件
> 
> **Estimated Effort**: Short
> **Parallel Execution**: NO - 顺序执行
> **Critical Path**: 配置 → Service → REPL → 入口

---

## Context

### Original Request
用户要求实现后端服务生命周期管理：
1. 启动
2. 初始化组件（创建 agent 实例）
3. 后台服务线程（接收请求 → 调用 agent 处理 → 响应结果）循环
4. 停止服务

代码写在 `src/app/` 目录，主程序入口在 `src/main.py`

### Interview Summary
**Key Discussions**:
- 服务类型: 终端交互式服务 (REPL)，通过终端输入接收请求
- 并发模式: asyncio 异步
- 配置方式: YAML 配置文件
- 交互模式: 交互式 REPL，持续等待用户输入
- 对话支持: 多轮对话，保持上下文
- 运行模式: 前台运行

**Research Findings**:
- 现有 `AgentFactory` 支持全局单例模式 (`get_agent`)，可复用 agent 实例
- `LLMFactory` 支持多种 provider
- 配置加载已有 YAML + 环境变量模式

### Metis Review
**Identified Gaps** (addressed):
- 异常处理策略: 添加超时和错误处理
- 信号处理: 添加 SIGINT/SIGTERM 处理
- 输入验证: 添加空输入和超长输入处理
- Agent 实例管理: 使用单例模式复用

---

## Work Objectives

### Core Objective
实现一个终端交互式后台服务生命周期管理系统：
- 启动时初始化 LLM 和 Agent 实例
- 进入 REPL 交互循环：接收终端输入 → 调用 agent 处理 → 输出结果
- 支持多轮对话（保持上下文）
- 优雅退出

### Concrete Deliverables
- [ ] `src/app/__init__.py` - app 模块初始化
- [ ] `src/app/config.py` - 服务配置加载
- [ ] `src/app/service.py` - 服务生命周期管理类
- [ ] `src/app/repl.py` - REPL 交互实现
- [ ] `src/main.py` - 主程序入口
- [ ] `config/app_config.yaml` - 服务配置示例
- [ ] `config/llm_config.yaml` - LLM 配置（如果不存在）

### Definition of Done
- [ ] `uv run python src/main.py --help` 显示帮助信息
- [ ] 启动后显示欢迎信息并进入 REPL
- [ ] 输入文本后 agent 返回响应
- [ ] 多轮对话保持上下文
- [ ] `exit` 命令正常退出
- [ ] Ctrl+C 优雅退出

### Must Have
- 完整的生命周期管理（启动 → 初始化 → 运行 → 停止）
- 配置通过 YAML 文件管理
- asyncio 异步处理
- 信号处理（SIGINT/SIGTERM）
- 异常处理（超时、错误提示）
- 输入验证（空输入、超长输入）

### Must NOT Have (Guardrails)
- ❌ HTTP API 服务器
- ❌ WebSocket 实时推送
- ❌ 数据库持久化
- ❌ 用户认证/权限系统
- ❌ 复杂 REPL 功能（历史记录、命令别名）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — 验收通过命令行自动执行验证

### Test Strategy
- **Infrastructure exists**: YES (项目已有 pytest)
- **Automated tests**: None (交互式服务，手动验证为主)
- **Framework**: N/A

### Verification Commands
```bash
# 1. 帮助信息
uv run python src/main.py --help
# 预期: 显示帮助信息，退出码 0

# 2. 配置文件缺失
uv run python src/main.py --config config/not_exist.yaml
# 预期: 报错 "配置文件不存在"，退出码 1

# 3. 启动测试（模拟输入）
echo -e "hello\nexit" | uv run python src/main.py --config config/app_config.yaml
# 预期: 显示欢迎信息，接收输入，退出

# 4. 空输入处理
echo -e "\nexit" | uv run python src/main.py --config config/app_config.yaml
# 预期: 忽略空输入，继续等待

# 5. Ctrl+C 处理
timeout 1 uv run python src/main.py --config config/app_config.yaml || true
# 预期: 超时后退出，无崩溃
```

---

## Execution Strategy

### 顺序执行（无并行）

```
Task 1: 创建配置文件 (config/app_config.yaml)
    ↓
Task 2: 创建 app 模块初始化 (src/app/__init__.py)
    ↓
Task 3: 创建配置加载器 (src/app/config.py)
    ↓
Task 4: 创建服务生命周期管理 (src/app/service.py)
    ↓
Task 5: 创建 REPL 交互 (src/app/repl.py)
    ↓
Task 6: 创建主程序入口 (src/main.py)
    ↓
Task 7: 最终验证
```

---

## TODOs

- [x] 1. 创建服务配置文件 `config/app_config.yaml`

  **What to do**:
  - 创建 `config/app_config.yaml` 配置文件
  - 包含服务基本配置（超时、日志级别等）
  - 包含 agent 默认配置

  **Must NOT do**:
  - 不包含 HTTP 服务器配置
  - 不包含数据库配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  - Reason: 简单的配置文件创建

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: N/A (顺序执行)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:
  - `src/llms/config.py` - 参考现有配置加载模式
  - `config/llm_config.yaml` - 如果存在，参考其结构

  **Acceptance Criteria**:
  - [ ] 文件 `config/app_config.yaml` 存在
  - [ ] 包含 `service`, `agent` 配置节
  - [ ] YAML 语法正确

  **QA Scenarios**:
  ```
  Scenario: 配置文件存在性
    Tool: Bash
    Preconditions: 无
    Steps:
      1. ls config/app_config.yaml
    Expected Result: 文件存在，无报错
    Evidence: 终端输出确认文件存在

  Scenario: YAML 语法正确性
    Tool: Bash
    Preconditions: 文件存在
    Steps:
      1. python -c "import yaml; yaml.safe_load(open('config/app_config.yaml'))"
    Expected Result: 无错误，成功解析
    Evidence: 终端无报错
  ```

  **Commit**: YES
  - Message: `feat(app): 添加服务配置文件`
  - Files: `config/app_config.yaml`

---

- [x] 2. 创建 app 模块初始化 `src/app/__init__.py`

  **What to do**:
  - 创建 `src/app/` 目录
  - 创建 `src/app/__init__.py`
  - 导出 Service, REPL, Config 等核心类

  **Must NOT do**:
  - 不包含业务逻辑

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 3-6
  - **Blocked By**: None

  **References**:
  - `src/agents/__init__.py` - 参考模块导出模式
  - `src/llms/__init__.py` - 参考模块导出模式

  **Acceptance Criteria**:
  - [ ] 目录 `src/app/` 存在
  - [ ] 文件 `src/app/__init__.py` 存在
  - [ ] 可以 `from src.app import Service`

  **QA Scenarios**:
  ```
  Scenario: 模块导入
    Tool: Bash
    Preconditions: 文件创建完成
    Steps:
      1. uv run python -c "from src.app import Service, REPL, Config"
    Expected Result: 导入成功，无报错
    Evidence: 终端无 ImportError
  ```

  **Commit**: YES
  - Message: `feat(app): 创建 app 模块`
  - Files: `src/app/__init__.py`

---

- [x] 3. 创建配置加载器 `src/app/config.py`

  **What to do**:
  - 实现 `Config` 类，加载 YAML 配置
  - 支持命令行参数覆盖
  - 提供配置验证

  **Must NOT do**:
  - 不实现 HTTP 配置
  - 不实现数据库配置

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 4, 5
  - **Blocked By**: Task 1, 2

  **References**:
  - `src/llms/config.py` - 参考单例模式
  - `config/app_config.yaml` - 配置文件结构

  **Acceptance Criteria**:
  - [ ] `Config` 类可以加载配置文件
  - [ ] 支持 `--config` 参数
  - [ ] 支持 `--help` 显示配置项

  **QA Scenarios**:
  ```
  Scenario: 加载配置文件
    Tool: Bash
    Preconditions: 配置文件存在
    Steps:
      1. uv run python -c "from src.app import Config; c = Config.load('config/app_config.yaml'); print(c.agent_config)"
    Expected Result: 成功加载配置
    Evidence: 终端输出配置内容

  Scenario: 配置文件不存在
    Tool: Bash
    Preconditions: 无
    Steps:
      1. uv run python -c "from src.app import Config; Config.load('not_exist.yaml')"
    Expected Result: 抛出 FileNotFoundError
    Evidence: 终端显示错误信息
  ```

  **Commit**: YES
  - Message: `feat(app): 实现配置加载器`
  - Files: `src/app/config.py`

---

- [x] 4. 创建服务生命周期管理 `src/app/service.py`

  **What to do**:
  - 实现 `Service` 类
  - 管理生命周期：start(), run(), stop()
  - 初始化 LLM 和 Agent 实例
  - 信号处理（SIGINT/SIGTERM）
  - 异常处理

  **Must NOT do**:
  - 不实现 HTTP 服务器
  - 不实现数据库连接

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 6
  - **Blocked By**: Task 2, 3

  **References**:
  - `src/agents/agent_factory.py` - Agent 创建方式
  - `src/llms/factory.py` - LLM 获取方式

  **Acceptance Criteria**:
  - [ ] `Service` 类可以实例化
  - [ ] `start()` 方法初始化 agent
  - [ ] `stop()` 方法清理资源
  - [ ] SIGINT 信号触发优雅退出
  - [ ] Agent 处理超时有错误提示

  **QA Scenarios**:
  ```
  Scenario: 服务实例化
    Tool: Bash
    Preconditions: 配置存在
    Steps:
      1. uv run python -c "from src.app import Service, Config; c = Config.load('config/app_config.yaml'); s = Service(c); print('OK')"
    Expected Result: 实例化成功
    Evidence: 终端输出 "OK"

  Scenario: 启动和停止
    Tool: Bash
    Preconditions: 服务实例化成功
    Steps:
      1. uv run python -c "
from src.app import Service, Config
import asyncio
async def test():
    c = Config.load('config/app_config.yaml')
    s = Service(c)
    await s.start()
    await s.stop()
asyncio.run(test())
print('OK')
"
    Expected Result: 启动停止成功
    Evidence: 终端输出 "OK"
  ```

  **Commit**: YES
  - Message: `feat(app): 实现服务生命周期管理`
  - Files: `src/app/service.py`

---

- [x] 5. 创建 REPL 交互 `src/app/repl.py`

  **What to do**:
  - 实现 `REPL` 类
  - 读取终端输入
  - 调用 agent 处理请求
  - 输出响应结果
  - 支持 `exit` 命令退出
  - 处理空输入和超长输入

  **Must NOT do**:
  - 不实现命令历史
  - 不实现命令别名

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 6
  - **Blocked By**: Task 2, 3, 4

  **References**:
  - Python `input()` 函数用法

  **Acceptance Criteria**:
  - [ ] `REPL` 类可以接收输入
  - [ ] `exit` 命令退出循环
  - [ ] 空输入被忽略
  - [ ] 超长输入被拒绝

  **QA Scenarios**:
  ```
  Scenario: exit 命令
    Tool: Bash
    Preconditions: 服务启动
    Steps:
      1. echo "exit" | uv run python -c "
import asyncio
from src.app import Service, Config, REPL
async def test():
    c = Config.load('config/app_config.yaml')
    s = Service(c)
    await s.start()
    repl = REPL(s)
    await repl.run()
asyncio.run(test())
"
    Expected Result: 正常退出
    Evidence: 无报错

  Scenario: 空输入处理
    Tool: Bash
    Preconditions: 服务启动
    Steps:
      1. echo -e "\nexit" | uv run python -c "
import asyncio
from src.app import Service, Config, REPL
async def test():
    c = Config.load('config/app_config.yaml')
    s = Service(c)
    await s.start()
    repl = REPL(s)
    await repl.run()
asyncio.run(test())
"
    Expected Result: 忽略空输入，继续运行
    Evidence: 不报错，正常退出
  ```

  **Commit**: YES
  - Message: `feat(app): 实现 REPL 交互`
  - Files: `src/app/repl.py`

---

- [x] 6. 创建主程序入口 `src/main.py`

  **What to do**:
  - 实现 CLI 入口
  - 解析命令行参数
  - 启动服务
  - 异常处理

  **Must NOT do**:
  - 不实现 HTTP 服务器入口

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Task 7
  - **Blocked By**: Task 5

  **References**:
  - Python `argparse` 用法

  **Acceptance Criteria**:
  - [ ] `--help` 显示帮助信息
  - [ ] `--config` 指定配置文件
  - [ ] 启动显示欢迎信息
  - [ ] 退出显示再见信息

  **QA Scenarios**:
  ```
  Scenario: 帮助信息
    Tool: Bash
    Preconditions: 无
    Steps:
      1. uv run python src/main.py --help
    Expected Result: 显示帮助信息
    Evidence: 终端输出帮助文本

  Scenario: 完整流程
    Tool: Bash
    Preconditions: 配置文件存在
    Steps:
      1. echo -e "hello\nexit" | uv run python src/main.py --config config/app_config.yaml
    Expected Result: 欢迎 → 处理输入 → 再见
    Evidence: 终端输出完整流程
  ```

  **Commit**: YES
  - Message: `feat(app): 实现主程序入口`
  - Files: `src/main.py`

---

- [x] 7. 最终验证

  **What to do**:
  - 运行所有验收测试
  - 确保代码质量

  **Must NOT do**:
  - 不修改已有功能

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: None
  - **Blocked By**: Task 6

  **References**:
  - Task 1-6 的验收标准

  **Acceptance Criteria**:
  - [ ] 所有 Task 验收通过
  - [ ] 无代码错误

  **Commit**: NO

---

## Commit Strategy

- **Task 1**: `feat(app): 添加服务配置文件` — config/app_config.yaml
- **Task 2**: `feat(app): 创建 app 模块` — src/app/__init__.py
- **Task 3**: `feat(app): 实现配置加载器` — src/app/config.py
- **Task 4**: `feat(app): 实现服务生命周期管理` — src/app/service.py
- **Task 5**: `feat(app): 实现 REPL 交互` — src/app/repl.py
- **Task 6**: `feat(app): 实现主程序入口` — src/main.py

---

## Success Criteria

### Verification Commands
```bash
# 帮助信息
uv run python src/main.py --help

# 配置文件缺失
uv run python src/main.py --config not_exist.yaml
# 预期: 报错退出

# 完整流程
echo -e "hello\nexit" | uv run python src/main.py --config config/app_config.yaml
# 预期: 欢迎 → 响应 → 再见
```

### Final Checklist
- [ ] 所有 "Must Have" 满足
- [ ] 所有 "Must NOT Have" 排除
- [ ] 服务可正常启动和停止
- [ ] REPL 交互正常工作
- [ ] 多轮对话保持上下文
