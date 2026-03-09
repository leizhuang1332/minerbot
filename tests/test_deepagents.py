"""DeepAgents MVP 最小化测试

基于 docs/deepagents-research.md 文档创建的基础功能测试
验证 DeepAgents SDK 的核心功能是否正常工作
"""

import sys


def test_imports():
    """测试1: 验证核心模块导入"""
    print("=" * 50)
    print("测试1: 核心模块导入")
    print("=" * 50)
    
    try:
        # 尝试导入 DeepAgents 核心模块
        from deepagents import create_deep_agent
        print("✅ deepagents 核心模块导入成功")
        
        from deepagents.middleware import FilesystemMiddleware, SubAgentMiddleware
        print("✅ Middleware 模块导入成功")
        
        from deepagents.backends import StateBackend, FilesystemBackend, BackendProtocol
        print("✅ Backends 模块导入成功")
        
        print()
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("提示: 请确保已安装 deepagents (pip install deepagents)")
        print()
        return False


def test_agent_creation():
    """测试2: 验证 Agent 创建功能"""
    print("=" * 50)
    print("测试2: Agent 创建功能")
    print("=" * 50)
    
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
        
        # 使用最小配置创建 Agent
        agent = create_deep_agent(
            backend=FilesystemBackend(root_dir=".", virtual_mode=True),
            model="anthropic:claude-sonnet-4-6"
        )
        
        print(f"✅ Agent 创建成功: {type(agent).__name__}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Agent 创建失败: {e}")
        print()
        return False


def test_backend_protocol():
    """测试3: 验证 Backend 协议"""
    print("=" * 50)
    print("测试3: Backend 协议")
    print("=" * 50)
    
    try:
        from deepagents.backends.protocol import BackendProtocol
        from deepagents.backends import FilesystemBackend
        
        # 验证后端类型
        fs_backend = FilesystemBackend(root_dir=".", virtual_mode=True)
        
        print(f"✅ FilesystemBackend: {type(fs_backend).__name__}")
        
        # 验证协议继承
        assert isinstance(fs_backend, BackendProtocol), "FilesystemBackend 未实现 BackendProtocol"
        
        print("✅ BackendProtocol 验证通过")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Backend 协议验证失败: {e}")
        print()
        return False


def test_middleware_system():
    """测试4: 验证中间件系统"""
    print("=" * 50)
    print("测试4: 中间件系统")
    print("=" * 50)
    
    try:
        from deepagents.middleware import (
            FilesystemMiddleware, 
            SubAgentMiddleware,
            MemoryMiddleware,
            SkillsMiddleware,
            SummarizationMiddleware
        )
        
        # 验证中间件类可用
        print(f"✅ FilesystemMiddleware: {FilesystemMiddleware.__name__}")
        print(f"✅ SubAgentMiddleware: {SubAgentMiddleware.__name__}")
        print(f"✅ MemoryMiddleware: {MemoryMiddleware.__name__}")
        print(f"✅ SkillsMiddleware: {SkillsMiddleware.__name__}")
        print(f"✅ SummarizationMiddleware: {SummarizationMiddleware.__name__}")
        
        print("✅ Middleware 系统验证通过")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Middleware 系统验证失败: {e}")
        print()
        return False


def test_subagent_system():
    """测试5: 验证子Agent系统"""
    print("=" * 50)
    print("测试5: 子Agent系统")
    print("=" * 50)
    
    try:
        from deepagents import SubAgent, CompiledSubAgent
        
        print(f"✅ SubAgent: {SubAgent.__name__}")
        print(f"✅ CompiledSubAgent: {CompiledSubAgent.__name__}")
        print("✅ 子Agent系统验证通过")
        print()
        return True
        
    except Exception as e:
        print(f"❌ 子Agent系统验证失败: {e}")
        print()
        return False


def test_graph_module():
    """测试6: 验证 Graph 模块"""
    print("=" * 50)
    print("测试6: Graph 模块")
    print("=" * 50)
    
    try:
        from deepagents import graph
        from deepagents.graph import create_deep_agent
        
        print(f"✅ graph 模块可用")
        print(f"✅ create_deep_agent 函数可用")
        print("✅ Graph 模块验证通过")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Graph 模块验证失败: {e}")
        print()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("🚀 DeepAgents MVP 最小化测试")
    print("基于 docs/deepagents-research.md")
    print("=" * 50 + "\n")
    
    tests = [
        ("核心模块导入", test_imports),
        ("Backend 协议", test_backend_protocol),
        ("中间件系统", test_middleware_system),
        ("子Agent系统", test_subagent_system),
        ("Graph 模块", test_graph_module),
        ("Agent 创建", test_agent_creation),
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
            print(f"❌ 测试异常: {name}")
            print(f"   错误: {e}\n")
            failed += 1
    
    print("=" * 50)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)
    
    if failed == 0:
        print("\n🎉 所有 MVP 测试通过!")
        print("DeepAgents 核心功能验证完成。")
    
    return failed == 0
from langchain.chat_models import init_chat_model

def test_agent_creation():
    """测试7: 验证 Agent 创建"""
    print("=" * 50)
    print("测试7: Agent 创建")
    print("=" * 50)
    
    try:
        from deepagents import create_deep_agent
        from langchain.chat_models import init_chat_model
        from langchain_core.messages import HumanMessage
        from langchain_anthropic import ChatAnthropic

        # model = init_chat_model(
        #     provider="anthropic",
        #     model="MiniMax-M2.5", 
        #     api_key="sk-cp-ZVNwPbRA4EmhTNwSKqE3t30NGw5537tXYpshPkdc39nqJVm4IS7k2OUvzIDujufT_jIGTCHu2adxkBDgx5nu-SS66bI7Kfr0dRLlbhP_QYgtq0USVUgx3KQ",
        #     base_url="https://api.minimaxi.com/anthropic/",
        #     temperature=0.0
        # )
        model = ChatAnthropic(
            model="minimax/MiniMax-M2.5", 
            api_key="sk-cp-ZVNwPbRA4EmhTNwSKqE3t30NGw5537tXYpshPkdc39nqJVm4IS7k2OUvzIDujufT_jIGTCHu2adxkBDgx5nu-SS66bI7Kfr0dRLlbhP_QYgtq0USVUgx3KQ",
            base_url="https://api.minimaxi.com/anthropic/"
        )

        agent = create_deep_agent(
        model=model,
        tools=[],
        system_prompt="你是一个智能助手",
        subagents=[],
        )
        # response = agent.invoke(
        #     {
        #         "messages": [
        #             {
        #                 "role": "user",
        #                 "content": "你好",
        #             }
        #         ],
        #     }, 
        # )
        response = agent.invoke(
            {
                "m": HumanMessage(content="你好"),
            }, 
        )
        print(response)
        
    except Exception as e:
        print(f"❌ Agent 创建验证失败: {e}")

if __name__ == "__main__":
    test_agent_creation()
    # success = main()
    # sys.exit(0 if success else 1)
