"""Agent 工厂函数"""
import logging
from typing import TYPE_CHECKING

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langgraph.store.sqlite.aio import AsyncSqliteStore

from ..config import AppConfig
from ..tools.search import create_search_tool
from .session import SessionManager

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.store.sqlite.aio import AsyncSqliteStore


def create_agent(
    config: AppConfig,
    tools: list["BaseTool"] | None = None,
    checkpointer: "AsyncSqliteSaver | None" = None,
    store: "AsyncSqliteStore | None" = None,
):
    """创建 Deep Agent 实例
    
    Args:
        config: 应用配置
        tools: 额外的工具列表
        checkpointer: 检查点保存器
        
    Returns:
        配置好的 Deep Agent
        
    Raises:
        AgentError: 当模型初始化失败时
    """
    logger = logging.getLogger(__name__)
    
    # 根据是否配置 MiniMax API Key 决定使用哪个模型
    try:
        if config.minimax_api_key:
            logger.info(f"使用 MiniMax 模型: {config.minimax_model}")
            model = ChatAnthropic(
                model_name=config.minimax_model,
                base_url=config.minimax_base_url,
                api_key=config.minimax_api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        else:
            logger.info(f"使用 Anthropic 模型: {config.model_name}")
            model = ChatAnthropic(
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
    except Exception as e:
        logger.error(f"模型初始化失败: {e}")
        from ..exceptions import AgentError
        raise AgentError(f"模型初始化失败: {e}") from e
    
    all_tools = []
    if config.tavily_api_key:
        all_tools.append(create_search_tool(config.tavily_api_key))
    if tools:
        all_tools.extend(tools)
    
    return create_deep_agent(
        model=model,
        tools=all_tools if all_tools else None,
        checkpointer=checkpointer,
        store=store,
        name="MinerBot",
    )


async def create_agent_with_session(config: AppConfig):
    """创建带会话管理的 Agent
    
    Args:
        config: 应用配置
        
    Returns:
        (agent, session_manager) 元组
    """
    session_mgr = await SessionManager.create(config)
    agent = create_agent(config, checkpointer=session_mgr.checkpointer, store=session_mgr.store)
    return agent, session_mgr
