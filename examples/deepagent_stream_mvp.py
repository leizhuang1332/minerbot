"""
DeepAgent Stream MVP
基于 LangChain DeepAgents 的流式输出示例，支持 thinking 输出
"""

import asyncio
import logging
from typing import AsyncGenerator

from langchain_core.messages import AIMessage
from langchain_core.runnables.config import RunnableConfig
from rich.console import Console
from rich.panel import Panel

from minerbot.config import AppConfig
from minerbot.agent.factory import create_agent


console = Console()
logger = logging.getLogger(__name__)


async def stream_with_thinking(
    agent,
    message: str,
    config: RunnableConfig | None = None,
) -> AsyncGenerator[dict, None]:
    """流式输出并处理 thinking 内容"""
    if config is None:
        config = RunnableConfig(configurable={"thread_id": "stream-test"})
    
    async for event in agent.astream(
        {"messages": [("user", message)]},
        config=config,
    ):
        for node_name, node_output in event.items():
            if not isinstance(node_output, dict):
                continue
            
            messages = node_output.get("messages")
            if not isinstance(messages, list):
                continue
            
            for msg in messages:
                if isinstance(msg, AIMessage):
                    content = msg.content
                    
                    if isinstance(content, str):
                        yield {"type": "text", "content": content}
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                if "thinking" in item:
                                    yield {"type": "thinking", "content": item["thinking"]}
                                if "text" in item:
                                    yield {"type": "text", "content": item["text"]}


async def run_demo():
    print("=" * 60)
    print("DeepAgent Stream MVP - 集成测试")
    print("=" * 60)
    
    print("\n[1] 加载配置...")
    config = AppConfig.from_env()
    config.validate()
    print(f"    模型: {config.model_name}")
    print(f"    温度: {config.temperature}")
    print(f"    最大 Tokens: {config.max_tokens}")
    
    print("\n[2] 创建 Agent...")
    agent = create_agent(config)
    print("    Agent 创建成功!")
    
    print("\n[3] 流式输出测试...")
    print("    输入: '你好，请介绍一下你自己'")
    print("\n    输出:\n")
    
    full_response = []
    thinking_buffer = []
    
    async for chunk in stream_with_thinking(agent, "你好，请介绍一下你自己"):
        if chunk["type"] == "thinking":
            thinking_buffer.append(chunk["content"])
            console.print(Panel(
                chunk["content"],
                title="🤔 Thinking",
                border_style="dim",
            ))
        elif chunk["type"] == "text":
            full_response.append(chunk["content"])
            print(chunk["content"], end="", flush=True)
    
    print("\n")
    
    print("\n[4] 测试结果汇总:")
    print(f"    - 总文本长度: {len(''.join(full_response))} 字符")
    print(f"    - Thinking 片段数: {len(thinking_buffer)}")
    
    if thinking_buffer:
        print("\n    Thinking 内容预览:")
        for i, thought in enumerate(thinking_buffer[:2], 1):
            preview = thought[:100] + "..." if len(thought) > 100 else thought
            print(f"      [{i}] {preview}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    return {
        "success": True,
        "response_length": len("".join(full_response)),
        "thinking_count": len(thinking_buffer),
    }


async def run_simple_test():
    config = AppConfig.from_env()
    config.validate()
    
    agent = create_agent(config)
    
    result = []
    async for chunk in stream_with_thinking(agent, "1+1 等于几?"):
        if chunk["type"] == "text":
            result.append(chunk["content"])
    
    return "".join(result)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    result = asyncio.run(run_demo())
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    exit(main())
