"""CLI 入口"""
import asyncio
import sys
from typing import Optional

from rich.console import Console
import typer

from .config import AppConfig
from .logging_config import setup_logging
from .exceptions import MinerBotError
from .ui.terminal import TerminalUI
from .agent.factory import create_agent_with_session

app = typer.Typer(help="MinerBot - 个人 AI 助手")
console = Console()


@app.command()
def main(
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="会话ID"),
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
):
    """启动 MinerBot CLI"""
    setup_logging("INFO")
    
    async def run_app():
        config = AppConfig.from_env()
        config.validate()
        
        agent, session_mgr = await create_agent_with_session(config)
        
        thread_config = session_mgr.get_thread_config(
            session_id or "default"
        )
        
        ui = TerminalUI(agent, thread_config, console)
        try:
            await ui.run()
        finally:
            await session_mgr.close()
    
    try:
        asyncio.run(run_app())
        
    except MinerBotError as e:
        console.print(f"[red]错误:[/red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]再见![/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    app()
