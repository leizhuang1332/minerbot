"""交互式终端 UI"""
from typing import AsyncGenerator, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from langchain_core.messages import AIMessage
from langchain_core.runnables.config import RunnableConfig


class TerminalUI:
    """终端交互界面"""
    
    def __init__(self, agent, config, console: Console):
        self.agent = agent
        self.config = config
        self.console = console
        self.running = True
    
    def print_welcome(self):
        welcome = """
# MinerBot

欢迎使用 MinerBot 个人 AI 助手！

- 输入您的消息开始对话
- 输入 `help` 查看帮助
- 输入 `quit` 或 `exit` 退出
        """
        self.console.print(Markdown(welcome))
    
    async def run(self):
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
                
                self.console.print("\n[bold blue]AI:[/bold blue] ", end="")
                full_response = []
                thinking_buffer = []
                
                async for chunk in self.stream_with_thinking(user_input):
                    if chunk["type"] == "thinking":
                        thinking_buffer.append(chunk["content"])
                        self.console.print(Panel(
                            chunk["content"],
                            title="🤔 Thinking",
                            border_style="dim",
                        ))
                    elif chunk["type"] == "text":
                        full_response.append(chunk["content"])
                        print(chunk["content"], end="", flush=True)
                
                print()
                
            except KeyboardInterrupt:
                self.running = False
                self.console.print("\n[yellow]再见![/yellow]")
                break
    
    def print_help(self):
        help_text = """
## 命令帮助

- `help` - 显示此帮助信息
- `quit` / `exit` / `q` - 退出程序
- `clear` - 清除屏幕
        """
        self.console.print(Markdown(help_text))

    async def stream_with_thinking(
        self,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        config = RunnableConfig(configurable={"thread_id": "terminal-session"})
        
        async for event in self.agent.astream(
            {"messages": [("user", message)]},
            config=config,
        ):
            for node_name, node_output in event.items():
                if not isinstance(node_output, dict):
                    continue
                
                messages = node_output.get("messages")
                if not isinstance(messages, list):
                    continue
                
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        content = msg.content
                        
                        if isinstance(content, str):
                            yield {"type": "text", "content": content}
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict):
                                    if "thinking" in item:
                                        yield {"type": "thinking", "content": item["thinking"]}
                                    if "text" in item:
                                        yield {"type": "text", "content": item["text"]}
