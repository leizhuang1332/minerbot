# 个人AI助手 (MinerBot) 开发计划

## 项目概述

基于 DeepAgents 框架开发一个功能完整、安全可靠的 CLI 个人 AI 助手，具备自然语言交互能力、对话历史持久化和网络搜索功能。

## 核心需求

| 需求 | 描述 |
|------|------|
| 应用类型 | CLI/TUI 命令行应用 |
| 交互方式 | 自然语言对话 |
| 会话持久化 | SqliteSaver (SQLite) |
| 第三方服务 | Tavily 网络搜索 |
| LLM 提供商 | Anthropic Claude |

---

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    MinerBot CLI                         │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   CLI UI    │  │   Agent     │  │   Tools     │   │
│  │  (Rich/PTK) │──│  (DeepAgent)│──│ (Tavily等)  │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
│                          │                              │
│                   ┌──────┴──────┐                      │
│                   │  Persistence │                      │
│                   │ (SqliteSaver)│                      │
│                   └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

---

## 开发任务列表

### Wave 1: 项目基础架构 (并行)

| 任务 | 描述 | 文件 |
|------|------|------|
| T1 | 项目配置更新 - 添加 Rich/Tavily 依赖 | `pyproject.toml` |
| T2 | 配置管理模块 - 环境变量和设置管理 | `src/minerbot/config.py` |
| T3 | 日志配置模块 - 统一日志管理 | `src/minerbot/logging_config.py` |
| T4 | 类型定义模块 - 共享类型定义 | `src/minerbot/types.py` |
| T5 | 异常处理模块 - 自定义异常类 | `src/minerbot/exceptions.py` |

### Wave 2: 核心 Agent 构建 (串行依赖)

| 任务 | 描述 | 文件 | 依赖 |
|------|------|------|------|
| T6 | Agent 工厂函数 - 创建 DeepAgent 实例 | `src/minerbot/agent/factory.py` | T2,T3 |
| T7 | 工具定义 - Tavily 搜索工具 | `src/minerbot/tools/search.py` | T4 |
| T8 | 会话管理器 - Checkpointer 配置 | `src/minerbot/agent/session.py` | T2,T3 |

### Wave 3: CLI 界面开发 (并行)

| 任务 | 描述 | 文件 |
|------|------|------|
| T9 | 主入口点 - CLI 入口 | `src/minerbot/cli.py` |
| T10 | 交互式终端 - Rich PTK 界面 | `src/minerbot/ui/terminal.py` |
| T11 | 命令处理器 - 处理用户输入 | `src/minerbot/ui/handlers.py` |

### Wave 4: 集成测试 (串行)

| 任务 | 描述 | 文件 | 依赖 |
|------|------|------|------|
| T12 | Agent 集成测试 | `tests/test_agent.py` | T6,T7,T8 |
| T13 | CLI 功能测试 | `tests/test_cli.py` | T9,T10,T11 |
| T14 | 端到端测试 | `tests/test_e2e.py` | All |

### Wave 5: 完善与文档 (并行)

| 任务 | 描述 | 文件 |
|------|------|------|
| T15 | README 文档 | `README.md` |
| T16 | AGENTS.md 配置 | `AGENTS.md` |
| T17 | .env 示例配置 | `.env.example` |

---

## 详细任务规范

### T1: 项目配置更新

**文件**: `pyproject.toml`

```python
# 添加依赖
dependencies = [
    "deepagents>=0.4.7",
    "langchain-core>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "pyyaml>=6.0",
    "rich>=13.0",          # CLI UI
    "prompt-toolkit>=3.0", # 终端交互
    "tavily-python>=0.3.0", # 网络搜索
    "python-dotenv>=1.0",  # 环境变量
]
```

### T2: 配置管理模块

**文件**: `src/minerbot/config.py`

```python
"""配置管理模块"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

@dataclass
class AppConfig:
    """应用配置"""
    anthropic_api_key: str
    tavily_api_key: Optional[str] = None
    model_name: str = "claude-sonnet-4-6"
    temperature: float = 0.7
    max_tokens: int = 4096
    sqlite_db_path: str = "data/minerbot.db"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置"""
        load_dotenv()
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            model_name=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
            sqlite_db_path=os.getenv("SQLITE_DB_PATH", "data/minerbot.db"),
        )
    
    def validate(self) -> None:
        """验证配置有效性"""
        if not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")
```

### T3: 日志配置模块

**文件**: `src/minerbot/logging_config.py`

```python
"""日志配置模块"""
import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """配置日志系统"""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )
```

### T4: 类型定义模块

**文件**: `src/minerbot/types.py`

```python
"""共享类型定义"""
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class ExitCode(Enum):
    """退出码"""
    SUCCESS = 0
    ERROR = 1
    KEYBOARD_INTERRUPT = 2

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    created_at: str
    message_count: int = 0
```

### T5: 异常处理模块

**文件**: `src/minerbot/exceptions.py`

```python
"""自定义异常类"""

class MinerBotError(Exception):
    """基础异常"""
    pass

class ConfigurationError(MinerBotError):
    """配置错误"""
    pass

class AgentError(MinerBotError):
    """Agent 错误"""
    pass

class ToolError(MinerBotError):
    """工具执行错误"""
    pass

class SessionError(MinerBotError):
    """会话错误"""
    pass
```

### T6: Agent 工厂函数

**文件**: `src/minerbot/agent/factory.py`

```python
"""Agent 工厂函数"""
from typing import Optional
from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore
from langchain_core.tools import BaseTool

from ..config import AppConfig
from ..tools.search import create_search_tool

def create_agent(
    config: AppConfig,
    tools: Optional[list[BaseTool]] = None,
    checkpointer: Optional[SqliteSaver] = None,
) -> "CompiledStateGraph":
    """创建 Deep Agent 实例"""
    
    # 初始化模型
    model = ChatAnthropic(
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    
    # 创建工具列表
    all_tools = []
    if config.tavily_api_key:
        all_tools.append(create_search_tool(config.tavily_api_key))
    if tools:
        all_tools.extend(tools)
    
    # 创建 Agent
    return create_deep_agent(
        model=model,
        tools=all_tools if all_tools else None,
        checkpointer=checkpointer,
        store=InMemoryStore(),
        name="MinerBot",
    )
```

### T7: Tavily 搜索工具

**文件**: `src/minerbot/tools/search.py`

```python
"""Tavily 搜索工具"""
from langchain_core.tools import tool
from tavily import TavilyClient

@tool
def search_web(query: str, max_results: int = 5) -> str:
    """搜索互联网信息。
    
    Args:
        query: 搜索关键词
        max_results: 返回结果数量 (默认5)
    
    Returns:
        搜索结果摘要
    """
    client = TavilyClient(api_key="")  # API key 将在运行时传入
    results = client.search(
        query=query,
        max_results=max_results,
        include_answer=True,
        include_raw_content=False,
    )
    
    if not results.get("results"):
        return "未找到相关结果"
    
    output = []
    for i, item in enumerate(results["results"][:max_results], 1):
        output.append(f"{i}. {item.get('title', 'Untitled')}")
        output.append(f"   {item.get('url', '')}")
        output.append(f"   {item.get('content', '')[:200]}...")
        output.append("")
    
    return "\n".join(output)

def create_search_tool(api_key: str) -> search_web:
    """创建搜索工具实例"""
    # 返回配置好 API key 的工具
    return search_web
```

### T8: 会话管理器

**文件**: `src/minerbot/agent/session.py`

```python
"""会话管理器"""
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from langgraph.checkpoint.sqlite import SqliteSaver
from ..config import AppConfig

@dataclass
class SessionManager:
    """会话管理器"""
    checkpointer: SqliteSaver
    
    @classmethod
    def create(cls, config: AppConfig) -> "SessionManager":
        """创建会话管理器"""
        # 确保数据库目录存在
        db_path = Path(config.sqlite_db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建 SQLite 连接
        conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,
        )
        
        checkpointer = SqliteSaver(conn)
        
        return cls(checkpointer=checkpointer)
    
    def get_thread_config(self, thread_id: str, metadata: dict = None):
        """获取线程配置"""
        return {
            "configurable": {
                "thread_id": thread_id,
                "metadata": metadata or {},
            }
        }
```

### T9: CLI 入口

**文件**: `src/minerbot/cli.py`

```python
"""CLI 入口"""
import sys
import typer
from typing import Optional
from rich.console import Console

from .config import AppConfig
from .logging_config import setup_logging
from .exceptions import MinerBotError
from .ui.terminal import TerminalUI
from .agent.factory import create_agent
from .agent.session import SessionManager

app = typer.Typer(help="MinerBot - 个人 AI 助手")
console = Console()

@app.command()
def main(
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="会话ID"),
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
):
    """启动 MinerBot CLI"""
    # 配置日志
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(log_level)
    
    try:
        # 加载配置
        config = AppConfig.from_env()
        config.validate()
        
        # 创建会话管理器
        session_mgr = SessionManager.create(config)
        
        # 创建 Agent
        agent = create_agent(config, checkpointer=session_mgr.checkpointer)
        
        # 获取会话配置
        thread_config = session_mgr.get_thread_config(
            session_id or "default"
        )
        
        # 启动终端 UI
        ui = TerminalUI(agent, thread_config, console)
        ui.run()
        
    except MinerBotError as e:
        console.print(f"[red]错误:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]再见![/yellow]")
        sys.exit(0)

if __name__ == "__main__":
    app()
```

### T10: 交互式终端

**文件**: `src/minerbot/ui/terminal.py`

```python
"""交互式终端 UI"""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

class TerminalUI:
    """终端交互界面"""
    
    def __init__(self, agent, config, console: Console):
        self.agent = agent
        self.config = config
        self.console = console
        self.running = True
    
    def print_welcome(self):
        """打印欢迎信息"""
        welcome = """
# MinerBot

欢迎使用 MinerBot 个人 AI 助手！

- 输入您的消息开始对话
- 输入 `help` 查看帮助
- 输入 `quit` 或 `exit` 退出
        """
        self.console.print(Markdown(welcome))
    
    def print_response(self, response: str):
        """打印 AI 响应"""
        self.console.print(Panel(response, title="AI 回复", border_style="blue"))
    
    def run(self):
        """运行主循环"""
        self.print_welcome()
        
        while self.running:
            try:
                user_input = self.console.input("\n[bold green]你:[/bold green] ")
                
                if not user_input.strip():
                    continue
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    self.running = False
                    self.console.print("[yellow]再见![/yellow]")
                    break
                
                if user_input.lower() == "help":
                    self.print_help()
                    continue
                
                # 调用 Agent
                result = self.agent.invoke(
                    {"messages": [("user", user_input)]},
                    config=self.config,
                )
                
                # 获取响应
                response = result["messages"][-1].content
                self.print_response(response)
                
            except KeyboardInterrupt:
                self.running = False
                self.console.print("\n[yellow]再见![/yellow]")
                break
    
    def print_help(self):
        """打印帮助信息"""
        help_text = """
## 命令帮助

- `help` - 显示此帮助信息
- `quit` / `exit` / `q` - 退出程序
- `clear` - 清除屏幕
        """
        self.console.print(Markdown(help_text))
```

### T11: 命令处理器

**文件**: `src/minerbot/ui/handlers.py`

```python
"""命令处理器"""
from typing import Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

class CommandType(Enum):
    """命令类型"""
    CHAT = "chat"
    QUIT = "quit"
    HELP = "help"
    CLEAR = "clear"
    SYSTEM = "system"

@dataclass
class Command:
    """命令"""
    type: CommandType
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}

class CommandHandler:
    """命令处理器"""
    
    def __init__(self):
        self.commands: dict[str, CommandType] = {
            "quit": CommandType.QUIT,
            "exit": CommandType.QUIT,
            "q": CommandType.QUIT,
            "help": CommandType.HELP,
            "clear": CommandType.CLEAR,
        }
    
    def parse(self, user_input: str) -> Command:
        """解析用户输入"""
        text = user_input.strip()
        
        # 检查是否是命令
        if text.lower() in self.commands:
            return Command(type=self.commands[text.lower()])
        
        # 默认为聊天
        return Command(type=CommandType.CHAT, args=(text,))
    
    async def execute(self, command: Command, context: dict) -> str:
        """执行命令"""
        if command.type == CommandType.CHAT:
            return await self.handle_chat(command, context)
        elif command.type == CommandType.QUIT:
            return "QUIT"
        elif command.type == CommandType.HELP:
            return "HELP"
        elif command.type == CommandType.CLEAR:
            return "CLEAR"
        
        return "UNKNOWN"
    
    async def handle_chat(self, command: Command, context: dict) -> str:
        """处理聊天消息"""
        # 由 Agent 处理
        return "PROCESS_BY_AGENT"
```

---

## 测试策略

### 单元测试

```python
# tests/test_config.py
def test_config_from_env():
    """测试配置加载"""
    # 设置测试环境变量
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    
    config = AppConfig.from_env()
    
    assert config.anthropic_api_key == "test-key"

# tests/test_tools.py
def test_search_tool():
    """测试搜索工具"""
    # Mock Tavily 客户端
    ...
```

### 集成测试

```python
# tests/test_agent.py
def test_agent_creation():
    """测试 Agent 创建"""
    config = AppConfig.from_env()
    session_mgr = SessionManager.create(config)
    agent = create_agent(config, checkpointer=session_mgr.checkpointer)
    
    assert agent is not None

def test_agent_response():
    """测试 Agent 响应"""
    ...
```

### E2E 测试

```python
# tests/test_e2e.py
def test_cli_flow():
    """测试完整 CLI 流程"""
    # 使用 click CliRunner
    ...
```

---

## 代码质量标准

根据文档规范，代码需遵循：

1. **类型注解**: 使用 Python 3.11+ 语法
2. **文档字符串**: Google 风格或 NumPy 风格
3. **错误处理**: 所有异常需捕获并友好提示
4. **日志记录**: 关键操作需记录日志
5. **配置管理**: 敏感信息不硬编码，使用环境变量

---

## 验收标准

- [ ] CLI 可以正常启动
- [ ] 可以与 AI 进行自然语言对话
- [ ] 对话历史可以跨会话持久化 (SQLite)
- [ ] 网络搜索工具可以正常工作
- [ ] 代码符合质量标准
- [ ] 测试覆盖核心功能

---

## 执行顺序

1. Wave 1: 项目基础架构 (并行执行)
2. Wave 2: 核心 Agent 构建 (T6→T7→T8)
3. Wave 3: CLI 界面开发 (并行执行)
4. Wave 4: 集成测试
5. Wave 5: 完善与文档
