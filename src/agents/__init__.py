"""Agents Module

Agent 工厂服务，支持灵活的 LLM 传入和全局单例模式。

Usage:
    # 方式1: 便捷函数 - 直接创建 (每次创建新实例)
    from src.agents import create_agent
    agent = create_agent(
        llm="minimax",  # 或 get_llm() 返回的 LLM 实例
        system_prompt="你是一个助手"
    )

    # 方式2: 便捷函数 - 全局单例 (相同配置返回同一实例)
    from src.agents import get_agent
    agent1 = get_agent(llm="minimax", system_prompt="你是一个助手")
    agent2 = get_agent(llm="minimax", system_prompt="你是一个助手")
    # agent1 is agent2  # True

    # 方式3: 配置对象 + 工厂类
    from src.agents import AgentConfig, AgentFactory
    config = AgentConfig(llm=get_llm(), system_prompt="...")
    factory = AgentFactory()
    agent = factory.get_agent(config)
"""

# 导出配置类
from .config import AgentConfig

# 导出工厂类和便捷函数
from .agent_factory import (
    AgentFactory,
    create_agent,
    get_agent,
    get_or_create,
    get_or_create_agent,
    get_factory,
)

# 导出异常类
from .agent_factory import (
    AgentFactoryError,
    LLMNotAvailableError,
    DeepAgentsNotAvailableError,
)

__all__ = [
    # 配置
    "AgentConfig",
    # 工厂
    "AgentFactory",
    "get_factory",
    # 便捷函数
    "create_agent",
    "get_agent",
    "get_or_create",
    "get_or_create_agent",
    # 异常
    "AgentFactoryError",
    "LLMNotAvailableError",
    "DeepAgentsNotAvailableError",
]
