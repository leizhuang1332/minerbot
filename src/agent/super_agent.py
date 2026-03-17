import os
from dotenv import load_dotenv
from langchain_core.tools import Tool
from pydantic_settings import BaseSettings
from deepagents import create_deep_agent, CompiledSubAgent
from langchain.agents import create_agent
from minerbot.llm.factory import LLMFactory
from langchain_core.language_models import BaseChatModel

# ========== 1. 配置加载（对齐你的架构） ==========
load_dotenv()  # 加载 .env 文件（存放模型/数据库密钥）

class AgentSettings(BaseSettings):
    # LLM 配置
    # DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "minimax/Minimax-2.5")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.1))
    # 数据库/向量库配置
    # QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    # REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SQL_URL: str = os.getenv("SQL_URL", "sqlite:///sales.db")

settings = AgentSettings()

# 从环境变量读取模型名，默认使用 MiniMax-M2.5
model_name = os.getenv("DEFAULT_MODEL", "minimax/MiniMax-M2.5")
LLMFactory.initialize()
llm = LLMFactory.create_llm_instance(model_name)

# ========== 2. 工具定义（每个 Agent 专属工具） ==========
# ---------------- 2.1 Planner Agent 无专属工具（核心是任务拆分） ----------------
# ---------------- 2.2 Tool Agent 工具（WebSearch/File/Shell） ----------------
def web_search_tool(query: str) -> str:
    """Web 搜索工具（示例：可替换为真实搜索引擎 API）"""
    # 实际场景可替换为 SerpAPI/Tavily API
    return f"【Web 搜索结果】关键词：{query}\n内容：模拟 AI 领域最新新闻（2026）：DeepAgents 成为主流 Agent 框架"

def file_read_tool(file_path: str) -> str:
    """文件读取工具"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f"【文件读取成功】{file_path} 内容：\n{f.read()[:1000]}"  # 限制长度
    except Exception as e:
        return f"【文件读取失败】{str(e)}"

def shell_exec_tool(command: str) -> str:
    """Shell 执行工具（生产环境需加权限控制）"""
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=10
        )
        return f"【Shell 执行结果】\nstdout：{result.stdout}\nstderr：{result.stderr}"
    except Exception as e:
        return f"【Shell 执行失败】{str(e)}"

tool_agent_tools = [
    Tool(
        name="web_search",
        func=web_search_tool,
        description="用于网络搜索，获取实时/公开信息（如新闻、数据、文档）",
    ),
    Tool(
        name="file_read",
        func=file_read_tool,
        description="读取本地文件内容（支持 txt/md/csv 等格式），入参为文件绝对路径",
    ),
    Tool(
        name="shell_exec",
        func=shell_exec_tool,
        description="执行 Shell 命令（仅限授权用户使用），入参为合法 Shell 命令",
    ),
]

# ---------------- 2.3 RAG Agent 工具（向量库检索） ----------------
def rag_retrieval_tool(query: str) -> str:
    """RAG 检索工具（基于 Qdrant 向量库）"""
    # from llama_index.core import VectorStoreIndex, Settings
    # from llama_index.vector_stores.qdrant import QdrantVectorStore
    # from qdrant_client import QdrantClient
    # from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    # # 初始化向量库和嵌入模型
    # client = QdrantClient(url=settings.QDRANT_URL)
    # vector_store = QdrantVectorStore(client=client, collection_name="knowledge_base")
    # Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
    
    # # 检索（示例：实际需先构建索引）
    # try:
    #     index = VectorStoreIndex.from_vector_store(vector_store)
    #     retriever = index.as_retriever(similarity_top_k=3)
    #     nodes = retriever.retrieve(query)
    #     context = "\n".join([node.get_content() for node in nodes])
    #     return f"【RAG 检索结果】\n相关上下文：\n{context}"
    # except Exception as e:
    #     return f"【RAG 检索失败】{str(e)}"

    return f"【RAG 检索结果】\n相关上下文：\n{query}"


rag_agent_tools = [
    Tool(
        name="rag_retrieval",
        func=rag_retrieval_tool,
        description="从私有知识库检索相关信息（如文档、企业知识、个人笔记），入参为检索问题",
    ),
]

# ---------------- 2.4 Code Agent 工具（Python 代码生成/执行） ----------------
def python_code_gen_tool(requirement: str) -> str:
    """Python 代码生成工具"""

    prompt = f"""
    请根据需求生成可运行的 Python 代码，要求：
    1. 代码简洁、注释清晰
    2. 处理异常情况
    3. 输出结果可验证
    
    需求：{requirement}
    """
    try:
        text = ""
        response = llm.invoke([{"role": "user", "content": prompt}])
        for item in response.content:
            print("-----------------")
            if ("thinking" in item):
                print(item["thinking"])  # ty:ignore[invalid-argument-type]
            if ("text" in item):
                text = (item["text"])  # ty:ignore[invalid-argument-type]
            print("-----------------")
        return f"【Python 代码生成结果】\n{text}"
    except Exception as e:
        return f"【Python 代码生成失败】{str(e)}"

def python_exec_tool(code: str) -> str:
    """Python 代码执行工具（沙箱环境，生产需加资源限制）"""
    import io
    from contextlib import redirect_stdout

    try:
        # 重定向输出
        f = io.StringIO()
        with redirect_stdout(f):
            # 限制执行时间和内存（示例：实际可用 Docker 沙箱）
            exec(code, {"__name__": "__main__"})
        output = f.getvalue()
        return f"【Python 代码执行结果】\n{output[:1000]}"  # 限制长度
    except Exception as e:
        return f"【Python 代码执行失败】{str(e)}"

code_agent_tools = [
    Tool(
        name="python_code_gen",
        func=python_code_gen_tool,
        description="根据自然语言需求生成 Python 代码，入参为清晰的功能描述",
    ),
    Tool(
        name="python_exec",
        func=python_exec_tool,
        description="执行 Python 代码（仅限安全代码），入参为完整可运行的 Python 代码",
    ),
]

# ---------------- 2.5 Data Agent 工具（NL2SQL/数据分析/图表生成） ----------------
def nl2sql_tool(nl_query: str) -> str:
    """NL2SQL 工具（将自然语言转为 SQL）"""

    prompt = f"""
    请将自然语言查询转为 SQL 语句，数据库类型：SQLite，表名：sales，字段：date（日期）、amount（销售额）、region（地区）。
    要求：SQL 语句合法、无注入风险，仅返回 SQL 语句。
    
    自然语言查询：{nl_query}
    """
    try:
        sql = ""
        response = llm.invoke([{"role": "user", "content": prompt}])
        for item in response.content:
            print("-----------------")
            if ("thinking" in item):
                print(item["thinking"])  # ty:ignore[invalid-argument-type]
            if ("text" in item):
                sql = (item["text"])  # ty:ignore[invalid-argument-type]
            print("-----------------")
        return f"【NL2SQL 结果】\n{sql}"
    except Exception as e:
        return f"【NL2SQL 失败】{str(e)}"

def data_analysis_tool(sql: str) -> str:
    """数据分析工具（执行 SQL 并分析数据）"""
    import pandas as pd
    import sqlite3

    try:
        conn = sqlite3.connect(settings.SQL_URL.split(":///")[-1])
        df = pd.read_sql(sql, conn)
        # 基础分析
        analysis = f"""
        【数据分析结果】
        1. 数据条数：{len(df)}
        2. 销售额总和：{df['amount'].sum() if 'amount' in df.columns else 'N/A'}
        3. 销售额均值：{df['amount'].mean() if 'amount' in df.columns else 'N/A'}
        4. 各地区销售额：{df.groupby('region')['amount'].sum().to_dict() if 'region' in df.columns else 'N/A'}
        """
        return analysis
    except Exception as e:
        return f"【数据分析失败】{str(e)}"

def chart_gen_tool(data_sql: str, chart_type: str = "line") -> str:
    """图表生成工具（基于 SQL 结果生成图表）"""
    import pandas as pd
    import sqlite3
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["SimHei"]  # 支持中文

    try:
        conn = sqlite3.connect(settings.SQL_URL.split(":///")[-1])
        df = pd.read_sql(data_sql, conn)
        
        # 生成图表
        plt.figure(figsize=(10, 6))
        if chart_type == "line":
            df.plot(x="date", y="amount", kind="line", title="销售趋势")
        elif chart_type == "bar":
            df.plot(x="region", y="amount", kind="bar", title="各地区销售额")
        
        # 保存图表
        chart_path = "sales_chart.png"
        plt.savefig(chart_path)
        plt.close()
        return f"【图表生成成功】\n图表已保存至：{os.path.abspath(chart_path)}"
    except Exception as e:
        return f"【图表生成失败】{str(e)}"

data_agent_tools = [
    Tool(
        name="nl2sql",
        func=nl2sql_tool,
        description="将自然语言查询转为 SQL 语句，适配 SQLite 数据库（sales 表）",
    ),
    Tool(
        name="data_analysis",
        func=data_analysis_tool,
        description="执行 SQL 并分析数据（如求和、均值、分组统计），入参为合法 SQL 语句",
    ),
    Tool(
        name="chart_gen",
        func=chart_gen_tool,
        description="生成数据图表（支持折线图/柱状图），入参为 SQL 语句和图表类型（默认 line）",
    ),
]

# ========== 3. 5 个 Agent 的 SubAgentConfig 配置（核心） ==========
# ---------------- 3.1 Planner Agent（任务规划） ----------------
planner_agent = CompiledSubAgent(
    name="planner_agent",
    description="任务规划专家",
    runnable=create_agent(
        model=llm,
        system_prompt="""
        你是超级 AI 助手的任务规划师，核心职责：
        1. 解析用户原始问题，拆分为可执行的子任务列表（每个子任务明确、单一）
        2. 为每个子任务分配对应的执行 Agent（tool_agent/rag_agent/code_agent/data_agent）
        3. 输出格式要求：
        - 子任务列表：[任务1, 任务2, ...]
        - 分配结果：{任务1: Agent名称, 任务2: Agent名称, ...}
        4. 示例：
        用户问题：分析 sales.db 的销售趋势并生成图表
        子任务列表：["从 sales.db 中查询销售数据", "分析销售数据的时间趋势", "生成销售趋势折线图"]
        分配结果：{"从 sales.db 中查询销售数据": "data_agent", "分析销售数据的时间趋势": "data_agent", "生成销售趋势折线图": "data_agent"}
        """,
        tools=[],  # Planner Agent 无需工具，仅做任务拆分
    )
)

# ---------------- 3.2 Tool Agent（工具执行） ----------------
tool_agent = CompiledSubAgent(
    name="tool_agent",
    description="工具执行专家",
    runnable=create_agent(
        model=llm,
        system_prompt="""
        你是超级 AI 助手的工具执行专家，核心职责：
        1. 执行需要调用外部工具的任务（如 Web 搜索、文件读取、Shell 执行）
        2. 严格根据工具描述调用对应工具，确保入参格式正确
        3. 工具执行失败时，返回清晰的错误信息，便于后续重试
        """,
        tools=tool_agent_tools,
    )
)

# ---------------- 3.3 RAG Agent（知识检索） ----------------
rag_agent = CompiledSubAgent(
    name="rag_agent",
    description="知识检索专家",
    runnable=create_agent(
        model=llm,
        system_prompt="""
        你是超级 AI 助手的知识检索专家，核心职责：
        1. 从私有知识库中检索与用户问题相关的上下文信息
        2. 结合检索结果回答用户问题（优先使用知识库内容，避免编造）
        3. 检索结果为空时，明确告知用户并建议补充知识库
        """,
        tools=rag_agent_tools,
    )
)

# ---------------- 3.4 Code Agent（代码执行） ----------------
code_agent = CompiledSubAgent(
    name="code_agent",
    description="代码专家",
    runnable=create_agent(
        model=llm,
        system_prompt="""
        你是超级 AI 助手的代码专家，核心职责：
        1. 根据用户需求生成可运行的 Python 代码
        2. 执行生成的代码并返回结果（含输出/错误）
        3. 代码执行失败时，自动修复代码并重新执行（最多重试 2 次）
        """,
        tools=code_agent_tools,
    )
)

# ---------------- 3.5 Data Agent（数据分析） ----------------
data_agent = CompiledSubAgent(
    name="data_agent",
    description="数据分析专家",
    runnable=create_agent(
        model=llm,
        tools=data_agent_tools,
        system_prompt="""
            你是超级 AI 助手的数据分析专家，核心职责：
            1. 将自然语言转为 SQL 语句，查询数据库中的数据
            2. 对查询结果进行统计分析（如求和、均值、趋势分析）
            3. 根据分析结果生成可视化图表（折线图/柱状图）
            4. 确保 SQL 语句合法、无注入风险，图表生成后返回保存路径
            """
    )
)

# ========== 4. 主 Agent 整合（DeepAgents 入口） ==========

# 主 Agent（整合所有子 Agent）
super_agent = create_deep_agent(
    model=llm,
    system_prompt="""
    你是超级 AI 助手，核心职责：
    1. 接收用户问题后，先调用 planner_agent 拆分任务并分配执行 Agent
    2. 根据 planner_agent 的分配结果，依次调用对应的子 Agent 执行任务
    3. 汇总所有子 Agent 的执行结果，生成最终的回答（清晰、完整、易懂）
    """,
    subagents=[planner_agent, tool_agent, rag_agent, code_agent, data_agent],
    tools=[],  # 主 Agent 不直接调用工具，由子 Agent 执行
)

# ========== 5. 测试运行（验证多 Agent 协作） ==========
if __name__ == "__main__":
    # 测试示例：分析 sales.db 销售趋势并生成图表
    user_query = "帮我分析 sales.db 中的销售趋势，生成折线图并保存到本地"

    # 调用主 Agent
    print("="*50)
    print("用户问题：", user_query)
    try:
        # for chunk in super_agent.stream(
        #     input = {"messages": [{"role": "user", "content": user_query}]},
        #     stream_mode="updates"
        # ):
        #     print("="*50)
        #     for node_name, state_update in chunk.items():
        #         print(node_name)
        #         print(state_update)

        for chunk in super_agent.stream(
            input = {"messages": [{"role": "user", "content": user_query}]},
            stream_mode=[
                "updates",
                "messages",
                "tasks"
            ]
        ):
            print("="*50)
            print(chunk)


    except Exception as e:
        import traceback
        # 打印完整堆栈信息
        traceback.print_exc()
        # 打印具体异常信息
        print(f"核心错误：{type(e).__name__}: {e}")