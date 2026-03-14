"""Agent 工厂函数"""
from typing import TYPE_CHECKING

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.store.memory import InMemoryStore

from ..config import AppConfig
from ..tools.search import create_search_tool
from .session import SessionManager

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool
    from langgraph.checkpoint.sqlite import SqliteSaver


def create_agent(
    config: AppConfig,
    tools: list["BaseTool"] | None = None,
    checkpointer: "SqliteSaver | None" = None,
):
    """创建 Deep Agent 实例
    
    Args:
        config: 应用配置
        tools: 额外的工具列表
        checkpointer: 检查点保存器
        
    Returns:
        配置好的 Deep Agent
    """
    model = ChatAnthropic(
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    
    all_tools = []
    if config.tavily_api_key:
        all_tools.append(create_search_tool(config.tavily_api_key))
    if tools:
        all_tools.extend(tools)
    
    return create_deep_agent(
        model=model,
        tools=all_tools if all_tools else None,
        checkpointer=checkpointer,
        store=InMemoryStore(),
        name="MinerBot",
    )


def create_agent_with_session(config: AppConfig):
    """创建带会话管理的 Agent
    
    Args:
        config: 应用配置
        
    Returns:
        (agent, session_manager) 元组
    """
    session_mgr = SessionManager.create(config)
    agent = create_agent(config, checkpointer=session_mgr.checkpointer)
    return agent, session_mgr
