"""配置管理模块"""
from dataclasses import dataclass
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
    minimax_api_key: Optional[str] = None
    minimax_base_url: str = "https://api.minimaxi.com/anthropic"
    minimax_model: str = "MiniMax-M2.5"
    model_provider: Optional[str] = None
    memory_enabled: bool = True
    memory_trigger_message_count: int = 10
    memory_trigger_idle_minutes: int = 10
    memory_summary_model: str = "claude-sonnet-4-6"
    
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
            minimax_api_key=os.getenv("MINIMAX_API_KEY"),
            minimax_base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
            minimax_model=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5"),
            model_provider=os.getenv("MODEL_PROVIDER"),
            memory_enabled=os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            memory_trigger_message_count=int(os.getenv("MEMORY_TRIGGER_MESSAGE_COUNT", "10")),
            memory_trigger_idle_minutes=int(os.getenv("MEMORY_TRIGGER_IDLE_MINUTES", "10")),
            memory_summary_model=os.getenv("MEMORY_SUMMARY_MODEL", "claude-sonnet-4-6"),
        )
    
    def validate(self) -> None:
        """验证配置有效性"""
        if not self.anthropic_api_key and not self.minimax_api_key:
            raise ValueError("At least one of ANTHROPIC_API_KEY or MINIMAX_API_KEY is required")
