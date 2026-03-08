from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# --------------------------
# 1. 基础配置（对接自定义Anthropic风格端点）
# --------------------------
# 初始化ChatAnthropic，适配自定义端点
llm = ChatAnthropic(
    # 必选：模型名称（需与自定义端点支持的模型一致）
    model="minimax/MiniMax-M2.5",
    # 可选：自定义API端点（核心配置，替换默认的Anthropic官方端点）
    base_url="https://api.minimaxi.com/anthropic/",
    # 可选：API密钥（如果自定义端点需要认证）
    api_key="sk-cp-ZVNwPbRA4EmhTNwSKqE3t30NGw5537tXYpshPkdc39nqJVm4IS7k2OUvzIDujufT_jIGTCHu2adxkBDgx5nu-SS66bI7Kfr0dRLlbhP_QYgtq0USVUgx3KQ",
    # 可选：请求超时时间（秒）
    timeout=30,
    # 可选：基础参数调优
    temperature=0.7,  # 随机性，0-1
    max_tokens=1024,  # 最大生成token数
    # 可选：自定义请求头（如果端点需要额外认证/标识）
    default_headers={
        "X-Custom-Header": "your-custom-value",
        "Content-Type": "application/json"
    }
)

# --------------------------
# 2. 基础调用示例（单轮对话）
# --------------------------
def basic_call():
    # 构建消息
    messages = [
        SystemMessage(content="你是一个专业的助手，回答简洁明了"),
        HumanMessage(content="请解释LangChain 1.0对接Anthropic风格LLM的核心要点")
    ]
    
    # 调用模型并解析输出
    response = llm.invoke(messages)
    parser = StrOutputParser()
    output = parser.invoke(response)
    print("基础调用结果：\n", output)

# --------------------------
# 3. 进阶用法（Prompt模板+链式调用）
# --------------------------
def advanced_chain():
    # 定义Prompt模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，仅用{language}回答问题"),
        ("human", "{question}")
    ])
    
    # 构建链式调用
    chain = prompt | llm | StrOutputParser()
    
    # 执行调用
    result = chain.invoke({
        "role": "技术顾问",
        "language": "中文",
        "question": "Anthropic端点风格的核心特征是什么？"
    })
    print("\n链式调用结果：\n", result)

# --------------------------
# 4. 批量调用示例
# --------------------------
def batch_call():
    # 批量构建请求
    requests = [
        {"role": "助手", "language": "中文", "question": "LangChain 1.0的核心改进？"},
        {"role": "助手", "language": "中文", "question": "如何调试自定义Anthropic端点？"}
    ]
    
    # 批量执行
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，仅用{language}回答问题"),
        ("human", "{question}")
    ])
    chain = prompt | llm | StrOutputParser()
    results = chain.batch(requests)
    
    print("\n批量调用结果：")
    for i, res in enumerate(results):
        print(f"第{i+1}个请求结果：\n{res}\n")

# 执行示例
if __name__ == "__main__":
    basic_call()
    advanced_chain()
    batch_call()