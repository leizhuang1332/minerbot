# 实现计划：Terminal.py Stream TUI 打印逻辑

## 目标
实现 terminal.py 文件第 55 行位置的 TUI 打印逻辑，正确解析并展示 stream 流式返回的数据。

## 上下文分析

### 当前代码（第 51-55 行）
```python
for event in self.agent.stream(
    {"messages": [("user", user_input)]},
    config=self.config,
):
    pass  # 第 55 行 - 没有任何处理
```

### 现有框架
- 使用 `rich` 库进行 TUI 展示
- 已有 `thinking_buffer` 用于存储 thinking 内容（第 50 行）
- 第 58-66 行已有 thinking 内容展示逻辑

## 实现任务

### 任务 1: 添加必要的导入

**文件**: `src/minerbot/ui/terminal.py`

**导入内容**:
```python
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage, SystemMessage
from rich.live import Live
from rich.text import Text
```

### 任务 2: 实现 Stream 事件处理逻辑

**位置**: 第 51-55 行

**需要处理的场景**:
1. **AIMessageChunk**: AI 响应的流式分块，提取 `.content` 字段
2. **ToolMessage**: 工具调用结果，展示工具名称和结果
3. **消息节点名称**: 常见节点名如 `agent`, `assistant`, `tools` 等

**核心逻辑**:
```python
# 伪代码
for event in agent.stream(...):
    for node_name, node_output in event.items():
        if "messages" in node_output:
            for msg in node_output["messages"]:
                if isinstance(msg, AIMessageChunk):
                    content = msg.content
                    # 实时打印 content
                elif isinstance(msg, ToolMessage):
                    # 展示工具调用结果
```

### 任务 3: 实时打印实现

**方案**: 使用 Rich 的流式打印机制
- 累积打印内容而不是每次新建行
- 处理 Markdown 格式输出
- 保持与现有 thinking 展示逻辑的兼容

## 验收标准

1. Stream 事件能正确解析
2. AI 响应内容实时显示在终端
3. 工具调用结果正确展示
4. 不影响现有 thinking 展示逻辑
5. 代码风格与现有项目一致

## 执行步骤

1. 修改导入部分
2. 重写第 51-55 行的循环逻辑
3. 测试运行
