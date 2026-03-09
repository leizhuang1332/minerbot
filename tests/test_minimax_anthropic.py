from langchain.chat_models import init_chat_model

# 使用Anthropic风格URL配置Minimax M2.5
model = init_chat_model(
    model="minimax/MiniMax-M2.5",  # 模型名称
    model_provider="anthropic",  # 使用Anthropic提供商接口
    base_url="https://api.minimaxi.com/anthropic/",  # Minimax的Anthropic兼容URL
    api_key="sk-cp-ZVNwPbRA4EmhTNwSKqE3t30NGw5537tXYpshPkdc39nqJVm4IS7k2OUvzIDujufT_jIGTCHu2adxkBDgx5nu-SS66bI7Kfr0dRLlbhP_QYgtq0USVUgx3KQ",  # Minimax API密钥
    # 可选参数
    temperature=0.7,  # 温度参数
    max_tokens=2048,  # 最大token数
    thinking=True,  # 启用思考功能
    thinking_budget_tokens=1000  # 思考token预算
)

# 示例调用
response = model.invoke([
    {"role": "system", "content": "你是一个乐于助人的助手。"},
    {"role": "user", "content": "请帮我写一个Python函数，计算斐波那契数列。"}
])
print(response)
# print(f"思考内容：{response[0]['thinking']}")
# print(f"回答内容：{response[0]['text']}")