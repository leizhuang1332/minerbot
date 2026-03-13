# 项目文档

## 架构设计

- **[docs/architecture.md](docs/architecture.md)**：此文档为项目整体架构说明书，详细阐述了系统的核心组件、模块划分、数据流设计及技术架构选型，供 AI Agent 全面了解项目结构与设计理念。

# 全局语言规范

1. **强制简体中文**：无论输入或工具返回何种语言，所有交互回复必须始终使用简体中文。
2. **翻译与保留**：工具或系统输出的英文信息需翻译为中文，代码、链接及技术术语保留原文。

# 环境规范

本项目使用 **uv** 管理 Python 依赖和虚拟环境。

## 强制规则

1. **所有 Python 命令必须使用 `uv run` 执行**
   - ✅ 正确：`uv run python script.py`
   - ✅ 正确：`uv run pytest`
   - ✅ 正确：`uv run python -m pytest tests/`
   - ❌ 错误：`python script.py`（未激活虚拟环境）

2. **安装依赖必须使用 uv**
   - 添加依赖：`uv add <package>`
   - 添加开发依赖：`uv add <package> --dev`
   - 同步依赖：`uv sync`

3. **禁止直接使用系统 Python 或全局 pip**
   - 禁止：`pip install ...`
   - 禁止：`python -m pip ...`

## 虚拟环境

- 虚拟环境位置：`.venv/`
- Python 版本：3.13（见 pyproject.toml）
- 依赖配置：pyproject.toml

## 激活虚拟环境

如需手动激活虚拟环境（不推荐，推荐使用 `uv run`）：

- Windows PowerShell：`.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate.bat`
- Linux/macOS：`source .venv/bin/activate`