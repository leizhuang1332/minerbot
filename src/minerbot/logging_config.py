"""日志配置模块"""
import logging
import sys
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> None:
    effective_level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.root.setLevel(effective_level)
    
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    
    for handler in handlers:
        handler.setLevel(effective_level)
    
    logging.basicConfig(
        level=effective_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )
