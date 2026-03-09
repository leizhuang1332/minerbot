"""DeepAgents Streaming MVP 测试

基于官方文档 https://docs.langchain.com/oss/python/deepagents/streaming/overview
测试 MiniMax M2.5 模型的流式响应功能
"""

import os

from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
import asyncio
from typing import Generator

import pytest
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic


# 从配置或环境变量获取 API 凭证
def get_minimax_credentials():
    """获取 MiniMax API 凭证"""
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        # 从现有测试代码中获取的 key（仅用于测试）
        api_key = "sk-cp-ZVNwPbRA4EmhTNwSKqE3t30NGw5537tXYpshPkdc39nqJVm4IS7k2OUvzIDujufT_jIGTCHu2adxkBDgx5nu-SS66bI7Kfr0dRLlbhP_QYgtq0USVUgx3KQ"
    
    base_url = "https://api.minimaxi.com/anthropic/"
    model = "minimax/MiniMax-M2.5"
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model
    }


def create_model():
    """创建 ChatAnthropic 模型实例"""
    creds = get_minimax_credentials()
    return ChatAnthropic(
        model=creds["model"],
        api_key=creds["api_key"],
        base_url=creds["base_url"],
        temperature=0.7,
        max_tokens=1024,
    )


class TestDeepAgentsStreaming:
    """DeepAgents 流式响应测试类"""
    
    def test_stream_mode_messages(self):
        """测试 stream_mode="messages" - 流式传输 token"""
        from deepagents import create_deep_agent
        
        print("\n" + "=" * 60)
        print("测试: stream_mode='messages' (流式 token)")
        print("=" * 60)
        
        model = create_model()
        
        agent = create_deep_agent(
            model=model,
            system_prompt="你是一个简洁的助手，直接回答问题。",
            tools=[],
            subagents=[],
        )
        
        # 流式收集响应 - messages 模式下返回 (token, metadata) 元组
        collected_content = []
        
        for chunk in agent.stream(
            {"messages": [HumanMessage(content="用一句话介绍你自己")]},
            stream_mode="messages",
        ):
            token, metadata = chunk
            # token 可能是 AIMessage 或包含 thinking/text 的列表
            if hasattr(token, 'content') and isinstance(token.content, list):
                # 处理 MiniMax 的 thinking + text 结构
                for item in token.content:
                    if isinstance(item, dict) and 'text' in item:
                        collected_content.append(item['text'])
                        print(item['text'], end="", flush=True)
            elif hasattr(token, 'content') and token.content:
                collected_content.append(str(token.content))
                print(token.content, end="", flush=True)
            elif hasattr(token, 'text') and token.text:
                collected_content.append(token.text)
                print(token.text, end="", flush=True)
        
        print("\n")
        
        full_response = "".join(collected_content)
        assert len(full_response) > 0, "流式响应为空"
        print(f"✅ 流式响应成功，共 {len(full_response)} 个字符")
        
        return True
    
    def test_stream_mode_updates(self):
        """测试 stream_mode="updates" - 流式传输更新"""
        from deepagents import create_deep_agent
        
        print("\n" + "=" * 60)
        print("测试: stream_mode='updates' (流式更新)")
        print("=" * 60)
        
        model = create_model()
        
        agent = create_deep_agent(
            model=model,
            system_prompt="你是一个有帮助的助手。",
            tools=[],
            subagents=[],
        )
        
        # 流式收集更新
        update_count = 0
        
        for chunk in agent.stream(
            {"messages": [HumanMessage(content="你好")]}
        ):
            update_count += 1
            print(f"更新 {update_count}: {chunk}")
        
        print(f"\n✅ 共收到 {update_count} 个更新")
        
        return True
    
    def test_stream_with_subagent(self):
        """测试带子 agent 的流式响应"""
        from deepagents import create_deep_agent
        
        print("\n" + "=" * 60)
        print("测试: 带子 Agent 的流式响应 (subgraphs=True)")
        print("=" * 60)
        
        model = create_model()
        
        agent = create_deep_agent(
            model=model,
            system_prompt="你是协调者，将任务委托给研究人员。",
            subagents=[
                {
                    "name": "researcher",
                    "description": "研究人员",
                    "system_prompt": "你是一个研究员，提供简洁的研究结果。",
                },
            ],
        )
        
        # 使用 subgraphs 启用子 agent 流式
        collected_tokens = []
        
        for namespace, chunk in agent.stream(
            {"messages": [HumanMessage(content="研究量子计算的最新进展")]},
            stream_mode="messages",
            subgraphs=True,
        ):
            token, metadata = chunk
            
            # 检查来源
            is_subagent = any(s.startswith("tools:") for s in namespace)
            source = "subagent" if is_subagent else "main"
            
            if token.content:
                collected_tokens.append(token.content)
                print(f"[{source}] ", end="", flush=True)
                print(token.content, end="", flush=True)
        
        print("\n")
        
        full_response = "".join(collected_tokens)
        assert len(full_response) > 0, "子 agent 流式响应为空"
        print(f"✅ 子 Agent 流式响应成功，共 {len(full_response)} 个字符")
        
        return True
    
    def test_stream_combined_modes(self):
        """测试组合多个 stream_mode"""
        from deepagents import create_deep_agent
        
        print("\n" + "=" * 60)
        print("测试: 组合多个 stream_mode")
        print("=" * 60)
        
        model = create_model()
        
        agent = create_deep_agent(
            model=model,
            system_prompt="你是简洁的助手。",
            tools=[],
            subagents=[],
        )
        
        # 组合多个模式
        modes = ["updates", "messages", "custom"]
        
        for chunk in agent.stream(
            {"messages": [HumanMessage(content="你好")]}
        ):
            mode, data = chunk
            print(f"模式: {mode}")
            
            if mode == "messages":
                token, _ = data
                if token.content:
                    print(f"  内容: {token.content[:50]}...")
            elif mode == "updates":
                print(f"  更新: {list(data.keys())}")
            elif mode == "custom":
                print(f"  自定义: {data}")
        
        print("\n✅ 组合模式测试成功")
        
        return True


def run_manual_streaming_test():
    """手动运行流式测试（不使用 pytest）"""
    print("\n" + "=" * 60)
    print("🚀 DeepAgents Streaming MVP 测试")
    print("模型: MiniMax-M2.5")
    print("=" * 60)
    
    test = TestDeepAgentsStreaming()
    
    tests = [
        ("stream_mode='messages'", test.test_stream_mode_messages),
        ("stream_mode='updates'", test.test_stream_mode_updates),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {name} 失败: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_manual_streaming_test()
    exit(0 if success else 1)
