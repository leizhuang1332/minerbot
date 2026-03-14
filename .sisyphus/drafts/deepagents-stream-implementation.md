# DeepAgents Stream API 研究总结

## 核心发现

### 1. Stream 事件格式
- **deepagents 基于 LangGraph**，其 `stream()` 方法返回生成器
- 每个事件是字典格式：`{node_name: node_output}`
- `node_output` 通常包含 `messages` 字段（消息列表）

### 2. 消息类型 (langchain_core.messages)
- `HumanMessage`: 用户输入消息
- `AIMessage` / `AIMessageChunk`: AI 响应（含流式分块）
- `ToolMessage`: 工具调用结果
- `SystemMessage`: 系统消息

### 3. 关键字段
- `content`: 实际文本内容
- `type`: 消息类型标识
- `name`: 消息来源名称（可选）
- `id`: 消息唯一标识（可选）

### 4. Stream 输出示例
```python
# 典型的事件结构
for event in agent.stream({"messages": [("user", "你好")]}, config):
    # event = {"agent": {"messages": [AIMessageChunk(...)]}}
    # 或 {"tools": {"messages": [ToolMessage(...)]}}
    pass
```

## Terminal.py 当前代码分析

### 第 51-55 行现状
```python
for event in self.agent.stream(
    {"messages": [("user", user_input)]},
    config=self.config,
):
    pass  # 第 55 行 - 没有任何处理
```

### 需要实现的功能
1. 解析 stream 事件中的消息
2. 实时打印 AI 响应内容
3. 处理 thinking 过程（如有）
4. 处理工具调用结果
5. 使用 Rich 库展示美观的 TUI

## 实现方案

### 需要导入的模块
- `langchain_core.messages` 的各种消息类型
- `rich.live.Live` 用于实时显示

### 核心逻辑
1. 遍历 stream 事件
2. 检查事件中的 messages 字段
3. 根据消息类型提取 content
4. 使用 Rich 实时打印
