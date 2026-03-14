"""命令处理器"""
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
    kwargs: dict | None = None
    
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
        
        if text.lower() in self.commands:
            return Command(type=self.commands[text.lower()])
        
        return Command(type=CommandType.CHAT, args=(text,))
    
    async def execute(self, command: Command, context: dict) -> str:
        """执行命令"""
        if command.type == CommandType.CHAT:
            return "PROCESS_BY_AGENT"
        elif command.type == CommandType.QUIT:
            return "QUIT"
        elif command.type == CommandType.HELP:
            return "HELP"
        elif command.type == CommandType.CLEAR:
            return "CLEAR"
        
        return "UNKNOWN"
