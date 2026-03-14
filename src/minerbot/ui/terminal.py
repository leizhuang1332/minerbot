"""交互式终端 UI"""
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.style import Style

from langchain_core.messages import AIMessage, ToolMessage


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
    
    def run(self):
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
                
                for event in self.agent.stream(
                    {"messages": [("user", user_input)]},
                    config=self.config,
                ):
                    
                    for _, node_output in event.items():
                        
                        if not isinstance(node_output, dict):
                            continue
                        
                        messages = node_output.get("messages")
                        if not isinstance(messages, list):
                            continue
                            
                        for msg in messages:
                            if isinstance(msg, AIMessage):
                                content = msg.content
                                if content:
                                    for char in content:
                                        if "thinking" in char:
                                            self.console.print(Panel(
                                                char["thinking"],
                                                title="🤔 Thinking",
                                                border_style="dim",
                                                style=Style(color="cyan")
                                            ))
                                        if "text" in char:
                                            full_response.append(char["text"])
                                            self.console.print(char["text"], end="")
                            
                            elif isinstance(msg, ToolMessage):
                                tool_name = msg.name or msg.tool_call_id or "tool"
                                content = msg.content
                                if content:
                                    self.console.print()
                                    self.console.print(Panel(
                                        f"[Tool: {tool_name}]\n{content}",
                                        title="🔧 Tool Result",
                                        border_style="green",
                                        style=Style(color="green")
                                    ))
                                    self.console.print("\n[bold blue]AI:[/bold blue] ", end="")
                
                # 流式输出完成后，如果有待输出的 thinking 内容，用 Panel 显示
                if thinking_buffer:
                    self.console.print()
                    thinking_text = '\n'.join(thinking_buffer)
                    self.console.print(Panel(
                        thinking_text,
                        title="🤔 Thinking",
                        border_style="dim",
                        style=Style(color="cyan")
                    ))
                
                self.console.print()
                
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
