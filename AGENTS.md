# Development

## Setup
```bash
uv sync
cp .env.example .env
# Edit .env with your API keys
```

## Run Tests
```bash
pytest
```

## Lint & Type Check
```bash
ruff check src/
mypy src/
```

---

# Code Style

- Python 3.11+
- Use type hints
- Follow PEP 8
- 100 char line length

# 全局语言规范

1. **强制简体中文**：无论输入或工具返回何种语言，所有交互回复必须始终使用简体中文。
2. **翻译与保留**：工具或系统输出的英文信息需翻译为中文，代码、链接及技术术语保留原文。