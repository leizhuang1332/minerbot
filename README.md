# MinerBot

基于 DeepAgents 框架开发的 CLI 个人 AI 助手。

## 功能特性

- 自然语言对话交互
- 对话历史持久化 (SQLite)
- 网络搜索功能 (Tavily)
- 多模型支持 (Anthropic Claude)

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入您的 API 密钥
```

必需的环境变量:
- `ANTHROPIC_API_KEY`: Anthropic API 密钥

可选的环境变量:
- `TAVILY_API_KEY`: Tavily API 密钥 (用于网络搜索)
- `MODEL_NAME`: 模型名称 (默认: claude-sonnet-4-6)
- `TEMPERATURE`: 温度参数 (默认: 0.7)
- `SQLITE_DB_PATH`: 数据库路径 (默认: data/minerbot.db)

### 3. 启动助手

```bash
# 启动交互式 CLI
minerbot

# 指定会话 ID
minerbot --session my-session

# 调试模式
minerbot --debug
```

## 使用方法

启动后，您可以:
- 输入您的消息与 AI 助手对话
- 输入 `help` 查看帮助
- 输入 `quit` 或 `exit` 退出

## 项目结构

```
minerbot/
├── src/minerbot/
│   ├── agent/          # Agent 核心
│   ├── tools/          # 工具定义
│   ├── ui/             # CLI 界面
│   ├── config.py       # 配置管理
│   ├── types.py        # 类型定义
│   └── exceptions.py   # 异常类
├── tests/              # 测试文件
├── docs/               # 文档
└── pyproject.toml     # 项目配置
```

## 开发

### 运行测试

```bash
uv run pytest
```

### 添加新工具

在 `src/minerbot/tools/` 目录下创建新的工具文件。
