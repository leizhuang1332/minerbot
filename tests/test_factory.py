"""LLM Factory 连通性测试
验证LLM工厂服务正常工作
"""
import sys

from src.llms import get_llm, current_llm, list_providers, switch_llm, llm_config


def test_config():
    """测试配置加载"""
    print("=" * 50)
    print("测试1: 配置加载")
    print("=" * 50)
    
    print(f"默认Provider: {llm_config.default_provider}")
    print(f"可用Providers: {llm_config.providers.keys()}")
    print(f"全局默认参数: {llm_config.defaults}")
    print("✅ 配置加载成功\n")
    return True


def test_list_providers():
    """测试Provider列表"""
    print("=" * 50)
    print("测试2: Provider列表")
    print("=" * 50)
    
    providers = list_providers()
    print(f"已注册Providers: {providers}")
    
    assert "minimax" in providers, "minimax provider未注册"
    print("✅ Provider列表正常\n")
    return True


def test_get_llm():
    """测试获取LLM实例"""
    print("=" * 50)
    print("测试3: 获取LLM实例")
    print("=" * 50)
    
    llm = get_llm()
    print(f"LLM类型: {type(llm).__name__}")
    print(f"LLM: {llm}")
    
    current = current_llm()
    assert current is not None, "当前LLM实例为空"
    print("✅ 获取LLM实例成功\n")
    return True


def test_basic_call():
    """测试基础调用"""
    print("=" * 50)
    print("测试4: 基础调用")
    print("=" * 50)
    
    from langchain_core.messages import HumanMessage, SystemMessage
    
    llm = get_llm()
    
    messages = [
        SystemMessage(content="你是一个专业的助手，回答简洁明了"),
        HumanMessage(content="请用一句话介绍你自己")
    ]
    
    response = llm.invoke(messages)
    print(f"响应内容: {response.content[:200]}...")
    print("✅ 基础调用成功\n")
    return True


def test_chain_call():
    """测试链式调用"""
    print("=" * 50)
    print("测试5: 链式调用")
    print("=" * 50)
    
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    llm = get_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，仅用{language}回答问题"),
        ("human", "{question}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    result = chain.invoke({
        "role": "助手",
        "language": "中文",
        "question": "你好，请说一句话"
    })
    
    print(f"链式调用结果: {result[:100]}...")
    print("✅ 链式调用成功\n")
    return True


def test_switch_provider():
    """测试Provider切换"""
    print("=" * 50)
    print("测试6: Provider切换")
    print("=" * 50)
    
    # 切换到minimax
    llm = switch_llm("minimax")
    print(f"切换后LLM: {type(llm).__name__}")
    
    print("✅ Provider切换成功\n")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 50)
    print("🚀 LLM Factory 连通性测试")
    print("=" * 50 + "\n")
    
    tests = [
        ("配置加载", test_config),
        ("Provider列表", test_list_providers),
        ("获取LLM实例", test_get_llm),
        ("基础调用", test_basic_call),
        ("链式调用", test_chain_call),
        ("Provider切换", test_switch_provider),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {name}")
            print(f"   错误: {e}\n")
            failed += 1
    
    print("=" * 50)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
