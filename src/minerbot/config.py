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
