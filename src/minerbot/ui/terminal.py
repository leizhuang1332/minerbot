"""交互式终端 UI"""
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
        welcome = """
# MinerBot

欢迎使用 MinerBot 个人 AI 助手！

- 输入您的消息开始对话
- 输入 `help` 查看帮助
- 输入 `quit` 或 `exit` 退出
        """
        self.console.print(Markdown(welcome))
    
    def print_response(self, response):
        # 处理 MiniMax 返回的结构化响应
        if isinstance(response, list):
            text_parts = []
            for item in response:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'thinking':
                        # 可选：处理 thinking
                        pass
            response = '\n'.join(text_parts)
        
        if not response:
            response = "(无回复)"
        
        self.console.print(Panel(response, title="AI 回复", border_style="blue"))
    
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
                for event in self.agent.stream(
                    {"messages": [("user", user_input)]},
                    config=self.config,
                ):
                    self.console.print(event)
                    if "messages" in event:
                        last_msg = event["messages"][-1]
                        if hasattr(last_msg, 'content'):
                            content = last_msg.content
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get('type') == 'text':
                                            text = item.get('text', '')
                                            self.console.print(text, end="")
                                            full_response.append(text)
                            elif isinstance(content, str):
                                self.console.print(content, end="")
                                full_response.append(content)
                
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
